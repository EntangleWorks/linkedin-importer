"""Playwright-based LinkedIn scraper client (compatible with linkedin-scraper v3).

This client provides a synchronous facade over the async Playwright API exposed by
`linkedin-scraper` v3 so that the existing orchestrator can continue to call
`.authenticate()` and `.get_profile()` without `await`.

Architecture
------------
- Spins up a dedicated asyncio event loop in a background thread.
- Manages a single Playwright browser/page via `BrowserManager`.
- Exposes synchronous methods that marshal work onto the background loop.
- Uses `linkedin_scraper`'s PersonScraper to collect profile data.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from concurrent.futures import Future
from typing import Optional

from linkedin_scraper import (
    BrowserManager,
    PersonScraper,
    ProgressCallback,
    login_with_cookie,
    login_with_credentials,
)
from linkedin_scraper.callbacks import ConsoleCallback
from linkedin_scraper.core.exceptions import (
    AuthenticationError,
    ProfileNotFoundError,
    ScrapingError,
)

from .scraper_errors import (
    AuthError,
    CookieExpired,
    ProfileNotFound,
    ScraperError,
    ScrapingBlocked,
)

logger = logging.getLogger(__name__)


class _LoggingCallback(ProgressCallback):
    """Bridge linkedin_scraper progress callbacks into our logger."""

    def __init__(self) -> None:
        self._console = ConsoleCallback()

    async def on_start(self, scraper_type: str, url: str):
        logger.info("Scraper start: %s (%s)", scraper_type, url)
        await self._console.on_start(scraper_type, url)

    async def on_progress(self, message: str, percent: int):
        logger.info("Progress %3d%% - %s", percent, message)
        await self._console.on_progress(message, percent)

    async def on_complete(self, scraper_type: str, url: str | object = None):
        logger.info("Scraper complete: %s", scraper_type)
        await self._console.on_complete(scraper_type, url)

    async def on_error(self, error: Exception):
        logger.error("Scraper error: %s", error)
        await self._console.on_error(error)


class _PlaywrightRuntime:
    """Owns the event loop and BrowserManager in a background thread."""

    def __init__(self, headless: bool = True, user_agent: Optional[str] = None):
        self.headless = headless
        self.user_agent = user_agent
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._loop.run_forever, name="linkedin-scraper-loop", daemon=True
        )
        self._loop_started = threading.Event()
        self._browser: Optional[BrowserManager] = None
        self._page = None

    def start(self):
        self._thread.start()
        self._loop_started.set()
        self.run(self._init_browser())

    def run(self, coro) -> object:
        """Synchronously run a coroutine on the background loop."""
        if not self._loop_started.is_set():
            raise RuntimeError("Playwright runtime not started")
        future: Future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result()

    def stop(self):
        try:
            if self._browser:
                self.run(self._close_browser())
        finally:
            self._loop.call_soon_threadsafe(self._loop.stop)
            self._thread.join(timeout=5)

    async def _init_browser(self):
        bm = BrowserManager(headless=self.headless, user_agent=self.user_agent)
        await bm.__aenter__()
        self._browser = bm
        self._page = bm.page

    async def _close_browser(self):
        if self._browser:
            await self._browser.__aexit__(None, None, None)
            self._browser = None
            self._page = None

    @property
    def page(self):
        return self._page


class LinkedInScraperClient:
    """Synchronous facade over the async Playwright linkedin-scraper API."""

    LINKEDIN_BASE_URL = "https://www.linkedin.com"
    LINKEDIN_LOGIN_URL = "https://www.linkedin.com/login"
    LINKEDIN_FEED_URL = "https://www.linkedin.com/feed/"

    def __init__(
        self,
        headless: Optional[bool] = None,
        chromedriver_path: Optional[str] = None,  # kept for API compatibility; unused
        page_load_timeout: int = 30,
        action_delay: float = 1.0,
        scroll_delay: float = 0.5,
        user_agent: Optional[str] = None,
        screenshot_on_error: bool = False,
        screenshot_dir: Optional[str] = None,
        max_retries: int = 3,
    ):
        env_default_headless = True
        self.headless = headless if headless is not None else env_default_headless
        self.user_agent = user_agent
        self.page_load_timeout = page_load_timeout
        self.action_delay = action_delay
        self.scroll_delay = scroll_delay
        self.screenshot_on_error = screenshot_on_error
        self.screenshot_dir = screenshot_dir or "."
        self.max_retries = max_retries

        self.authenticated: bool = False
        self._runtime = _PlaywrightRuntime(
            headless=self.headless, user_agent=self.user_agent
        )
        self._runtime.start()

        logger.debug(
            "LinkedInScraperClient initialized (headless=%s, max_retries=%d)",
            self.headless,
            self.max_retries,
        )

    def authenticate(
        self,
        *,
        cookie: Optional[str] = None,
        email: Optional[str] = None,
        password: Optional[str] = None,
        handle_2fa: bool = True,
    ):
        """Authenticate via cookie (preferred) or credentials."""
        if cookie:
            try:
                self._runtime.run(login_with_cookie(self._runtime.page, cookie))
                self.authenticated = True
                logger.info("Authenticated with cookie")
                return
            except AuthenticationError as exc:
                raise CookieExpired(str(exc))
            except Exception as exc:
                raise AuthError(f"Cookie authentication failed: {exc}")

        if email and password:
            try:
                self._runtime.run(
                    login_with_credentials(
                        self._runtime.page,
                        email=email,
                        password=password,
                        timeout=self.page_load_timeout * 1000,
                        warm_up=True,
                    )
                )
                self.authenticated = True
                logger.info("Authenticated with credentials")
                return
            except AuthenticationError as exc:
                raise AuthError(f"Credential authentication failed: {exc}")
        raise AuthError(
            "Authentication requires either a valid LINKEDIN_COOKIE or email/password"
        )

    def get_profile(self, profile_url: str):
        """Scrape a LinkedIn profile synchronously and return linkedin_scraper.models.Person."""
        if not self.authenticated:
            raise AuthError("Must authenticate before scraping profiles")

        def _scrape():
            return self._scrape_profile(profile_url)

        try:
            return self._runtime.run(_scrape())
        except ProfileNotFoundError as exc:
            raise ProfileNotFound(profile_url, details={"error": str(exc)})
        except AuthenticationError as exc:
            raise CookieExpired(str(exc))
        except ScrapingError as exc:
            # Treat scraping blocks as recoverable
            raise ScrapingBlocked(str(exc))
        except Exception as exc:
            raise ScraperError(f"Unexpected scraping error: {exc}")

    async def _scrape_profile(self, profile_url: str):
        callback = _LoggingCallback()
        scraper = PersonScraper(self._runtime.page, callback=callback)
        return await scraper.scrape(profile_url)

    def get_driver_info(self) -> dict:
        """Return browser info stub (maintains compatibility with orchestrator logging)."""
        return {"chrome_version": "playwright-chromium", "driver_version": "playwright"}

    def close(self):
        """Tear down the Playwright browser and event loop."""
        self._runtime.stop()
        self.authenticated = False

    def __enter__(self) -> "LinkedInScraperClient":
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    async def __aenter__(self) -> "LinkedInScraperClient":
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self.close()


__all__ = ["LinkedInScraperClient"]
