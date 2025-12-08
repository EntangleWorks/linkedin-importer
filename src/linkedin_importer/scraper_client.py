"""LinkedIn Scraper Client for browser-based profile scraping.

This module provides a Selenium-based client for scraping LinkedIn profiles
using the linkedin_scraper library. It supports cookie-based authentication
(preferred) and email/password authentication (fallback).
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

try:
    from webdriver_manager.chrome import ChromeDriverManager

    WEBDRIVER_MANAGER_AVAILABLE = True
except ImportError:
    WEBDRIVER_MANAGER_AVAILABLE = False
    ChromeDriverManager = None  # type: ignore

from .scraper_errors import (
    AuthError,
    BrowserError,
    CookieExpired,
    ProfileNotFound,
    ScrapingBlocked,
    TwoFactorRequired,
)

if TYPE_CHECKING:
    from linkedin_scraper import Person

logger = logging.getLogger(__name__)


class AuthMethod(Enum):
    """Authentication method for LinkedIn scraper."""

    COOKIE = "cookie"
    CREDENTIALS = "credentials"


class LinkedInScraperClient:
    """Client for scraping LinkedIn profiles using Selenium.

    This client manages the browser lifecycle and provides methods for
    authenticating with LinkedIn and scraping profile data.

    Attributes:
        driver: The Selenium WebDriver instance
        authenticated: Whether the client is currently authenticated
    """

    LINKEDIN_BASE_URL = "https://www.linkedin.com"
    LINKEDIN_LOGIN_URL = "https://www.linkedin.com/login"
    LINKEDIN_FEED_URL = "https://www.linkedin.com/feed/"

    def __init__(
        self,
        headless: bool = True,
        chromedriver_path: Optional[str] = None,
        page_load_timeout: int = 30,
        action_delay: float = 1.0,
        scroll_delay: float = 0.5,
        user_agent: Optional[str] = None,
        screenshot_on_error: bool = False,
        screenshot_dir: Optional[str] = None,
    ):
        """Initialize the LinkedIn scraper client.

        Args:
            headless: Whether to run Chrome in headless mode
            chromedriver_path: Path to ChromeDriver executable (auto-downloads if None)
            page_load_timeout: Maximum time to wait for page loads in seconds
            action_delay: Delay between actions in seconds
            scroll_delay: Delay between scroll actions in seconds
            user_agent: Custom user agent string (uses Chrome default if None)
            screenshot_on_error: Whether to capture screenshots when errors occur
            screenshot_dir: Directory to save screenshots (defaults to current directory)
        """
        self.headless = headless
        self.chromedriver_path = chromedriver_path
        self.page_load_timeout = page_load_timeout
        self.action_delay = action_delay
        self.scroll_delay = scroll_delay
        self.user_agent = user_agent
        self.screenshot_on_error = screenshot_on_error
        self.screenshot_dir = screenshot_dir or "."

        self.driver: Optional[webdriver.Chrome] = None
        self.authenticated: bool = False
        self._driver_version: Optional[str] = None
        self._browser_version: Optional[str] = None

        logger.debug(
            "LinkedInScraperClient initialized: headless=%s, timeout=%ds, screenshot_on_error=%s",
            headless,
            page_load_timeout,
            screenshot_on_error,
        )

    def _create_driver(self) -> webdriver.Chrome:
        """Create and configure the Chrome WebDriver.

        Returns:
            Configured Chrome WebDriver instance

        Raises:
            BrowserError: If the browser fails to start
        """
        options = self._build_chrome_options()
        service = self._get_chromedriver_service()

        try:
            driver = webdriver.Chrome(service=service, options=options)
            driver.set_page_load_timeout(self.page_load_timeout)

            # Additional anti-detection via CDP
            driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {
                    "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    })
                """
                },
            )

            # Store version info for debugging
            self._browser_version = driver.capabilities.get("browserVersion", "unknown")
            self._driver_version = driver.capabilities.get("chrome", {}).get(
                "chromedriverVersion", "unknown"
            )

            logger.info(
                "Chrome WebDriver started: headless=%s, browser_version=%s, driver_version=%s",
                self.headless,
                self._browser_version,
                self._driver_version,
            )

            return driver

        except WebDriverException as e:
            raise BrowserError(
                f"Failed to start Chrome browser: {e}",
                details={
                    "headless": self.headless,
                    "chromedriver_path": self.chromedriver_path,
                    "error": str(e),
                    "suggestion": "Ensure Chrome browser is installed and chromedriver version matches",
                },
            ) from e

    def _build_chrome_options(self) -> ChromeOptions:
        """Build Chrome options with anti-detection measures.

        Returns:
            Configured ChromeOptions instance
        """
        options = ChromeOptions()

        if self.headless:
            options.add_argument("--headless=new")

        # Anti-detection measures
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")

        if self.user_agent:
            options.add_argument(f"--user-agent={self.user_agent}")

        # Exclude automation switches
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        return options

    def _get_chromedriver_service(self) -> ChromeService:
        """Get ChromeDriver service, auto-downloading if needed.

        Returns:
            Configured ChromeService instance

        Raises:
            BrowserError: If chromedriver cannot be found or downloaded
        """
        if self.chromedriver_path:
            # Use custom path
            if not os.path.exists(self.chromedriver_path):
                raise BrowserError(
                    f"ChromeDriver not found at specified path: {self.chromedriver_path}",
                    details={
                        "chromedriver_path": self.chromedriver_path,
                        "suggestion": "Verify the path is correct or remove CHROMEDRIVER_PATH to auto-download",
                    },
                )
            logger.debug("Using custom chromedriver: %s", self.chromedriver_path)
            return ChromeService(executable_path=self.chromedriver_path)

        # Auto-download ChromeDriver
        if not WEBDRIVER_MANAGER_AVAILABLE:
            raise BrowserError(
                "webdriver-manager not installed and no CHROMEDRIVER_PATH provided",
                details={
                    "suggestion": "Install webdriver-manager: pip install webdriver-manager, or set CHROMEDRIVER_PATH",
                },
            )

        try:
            driver_path = ChromeDriverManager().install()
            logger.debug("Auto-downloaded chromedriver: %s", driver_path)
            return ChromeService(executable_path=driver_path)
        except Exception as e:
            raise BrowserError(
                f"Failed to auto-download ChromeDriver: {e}",
                details={
                    "error": str(e),
                    "suggestion": "Check internet connection or manually download chromedriver and set CHROMEDRIVER_PATH",
                },
            ) from e

    def take_screenshot(self, name: str = "error") -> Optional[str]:
        """Take a screenshot of the current browser state.

        Args:
            name: Name prefix for the screenshot file

        Returns:
            Path to the saved screenshot, or None if failed
        """
        if self.driver is None:
            logger.warning("Cannot take screenshot: driver not initialized")
            return None

        try:
            # Create screenshot directory if it doesn't exist
            screenshot_path = Path(self.screenshot_dir)
            screenshot_path.mkdir(parents=True, exist_ok=True)

            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{name}_{timestamp}.png"
            filepath = screenshot_path / filename

            self.driver.save_screenshot(str(filepath))
            logger.info("Screenshot saved: %s", filepath)
            return str(filepath)

        except Exception as e:
            logger.warning("Failed to take screenshot: %s", e)
            return None

    def _capture_error_screenshot(self, error_name: str) -> Optional[str]:
        """Capture screenshot if screenshot_on_error is enabled.

        Args:
            error_name: Name to use for the screenshot

        Returns:
            Path to screenshot if captured, None otherwise
        """
        if not self.screenshot_on_error:
            return None
        return self.take_screenshot(error_name)

    def get_driver_info(self) -> dict:
        """Get information about the current driver and browser.

        Returns:
            Dictionary with driver and browser version info
        """
        return {
            "browser_version": self._browser_version,
            "driver_version": self._driver_version,
            "headless": self.headless,
            "page_load_timeout": self.page_load_timeout,
            "driver_active": self.driver is not None,
            "authenticated": self.authenticated,
        }

    def _ensure_driver(self) -> webdriver.Chrome:
        """Ensure the WebDriver is initialized.

        Returns:
            The WebDriver instance

        Raises:
            BrowserError: If the driver cannot be created
        """
        if self.driver is None:
            self.driver = self._create_driver()
        return self.driver

    def authenticate_with_cookie(self, cookie: str) -> bool:
        """Authenticate with LinkedIn using the li_at session cookie.

        This is the preferred authentication method as it bypasses 2FA
        and CAPTCHA challenges.

        Args:
            cookie: The li_at session cookie value

        Returns:
            True if authentication was successful

        Raises:
            AuthError: If authentication fails
            CookieExpired: If the cookie is no longer valid
        """
        driver = self._ensure_driver()

        try:
            # Navigate to LinkedIn to set the domain for cookies
            logger.debug("Navigating to LinkedIn to set cookie domain")
            driver.get(self.LINKEDIN_BASE_URL)
            time.sleep(self.action_delay)

            # Delete existing cookies and set the li_at cookie
            driver.delete_all_cookies()
            driver.add_cookie(
                {
                    "name": "li_at",
                    "value": cookie,
                    "domain": ".linkedin.com",
                    "path": "/",
                    "secure": True,
                    "httpOnly": True,
                }
            )

            logger.debug("Cookie set, verifying authentication")

            # Navigate to feed to verify authentication
            driver.get(self.LINKEDIN_FEED_URL)
            time.sleep(self.action_delay)

            # Check if we're logged in
            if self._is_logged_in():
                self.authenticated = True
                logger.info("Successfully authenticated with cookie")
                return True

            # If we're redirected to login, cookie is invalid/expired
            if "/login" in driver.current_url or "/checkpoint" in driver.current_url:
                raise CookieExpired(
                    "LinkedIn session cookie has expired or is invalid",
                    details={"redirect_url": driver.current_url},
                )

            raise AuthError(
                "Failed to authenticate with cookie: unexpected state",
                details={"current_url": driver.current_url},
            )

        except (CookieExpired, AuthError):
            raise
        except Exception as e:
            raise AuthError(
                f"Cookie authentication failed: {e}",
                details={"error": str(e)},
            ) from e

    def authenticate_with_credentials(self, email: str, password: str) -> bool:
        """Authenticate with LinkedIn using email and password.

        Note: This method may trigger 2FA verification.

        Args:
            email: LinkedIn account email
            password: LinkedIn account password

        Returns:
            True if authentication was successful

        Raises:
            AuthError: If authentication fails
            TwoFactorRequired: If 2FA verification is required
        """
        driver = self._ensure_driver()

        try:
            logger.debug("Navigating to LinkedIn login page")
            driver.get(self.LINKEDIN_LOGIN_URL)
            time.sleep(self.action_delay)

            # Find and fill the login form
            wait = WebDriverWait(driver, self.page_load_timeout)

            email_field = wait.until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            password_field = driver.find_element(By.ID, "password")

            logger.debug("Entering credentials")
            email_field.clear()
            email_field.send_keys(email)
            time.sleep(self.action_delay / 2)

            password_field.clear()
            password_field.send_keys(password)
            time.sleep(self.action_delay / 2)

            # Submit the form
            submit_button = driver.find_element(
                By.CSS_SELECTOR, "button[type='submit']"
            )
            submit_button.click()
            time.sleep(self.action_delay * 2)

            # Check for 2FA challenge
            if self._is_2fa_challenge():
                raise TwoFactorRequired(
                    "LinkedIn requires two-factor authentication. "
                    "Please complete verification in the browser.",
                    details={"current_url": driver.current_url},
                )

            # Check for login error
            if self._has_login_error():
                raise AuthError(
                    "Login failed: invalid email or password",
                    details={"current_url": driver.current_url},
                )

            # Verify we're logged in
            if self._is_logged_in():
                self.authenticated = True
                logger.info("Successfully authenticated with credentials")
                return True

            raise AuthError(
                "Failed to authenticate: unexpected state after login",
                details={"current_url": driver.current_url},
            )

        except (TwoFactorRequired, AuthError):
            raise
        except TimeoutException as e:
            raise AuthError(
                "Login page timed out",
                details={"error": str(e)},
            ) from e
        except Exception as e:
            raise AuthError(
                f"Credential authentication failed: {e}",
                details={"error": str(e)},
            ) from e

    def wait_for_2fa_completion(self, timeout: int = 120) -> bool:
        """Wait for the user to complete 2FA verification manually.

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if 2FA was completed successfully

        Raises:
            TwoFactorRequired: If timeout is reached without completion
        """
        driver = self._ensure_driver()

        logger.info(
            "Waiting for manual 2FA completion (timeout: %ds)...",
            timeout,
        )

        start_time = time.time()
        while time.time() - start_time < timeout:
            if self._is_logged_in():
                self.authenticated = True
                logger.info("2FA completed successfully")
                return True
            time.sleep(2)

        raise TwoFactorRequired(
            f"2FA verification not completed within {timeout} seconds",
            details={"waited_seconds": timeout},
        )

    def _is_logged_in(self) -> bool:
        """Check if currently logged in to LinkedIn.

        Returns:
            True if logged in
        """
        if self.driver is None:
            return False

        try:
            # Check for elements that only appear when logged in
            # The feed page has a global nav when logged in
            self.driver.find_element(By.ID, "global-nav")
            return True
        except NoSuchElementException:
            pass

        try:
            # Alternative: check for profile menu
            self.driver.find_element(
                By.CSS_SELECTOR, ".global-nav__me-photo, .feed-identity-module"
            )
            return True
        except NoSuchElementException:
            pass

        return False

    def _is_2fa_challenge(self) -> bool:
        """Check if LinkedIn is presenting a 2FA challenge.

        Returns:
            True if 2FA is required
        """
        if self.driver is None:
            return False

        current_url = self.driver.current_url.lower()

        # Check URL patterns for 2FA/verification pages
        if any(
            pattern in current_url
            for pattern in ["checkpoint", "challenge", "two-step-verification"]
        ):
            return True

        try:
            # Check for 2FA input elements
            self.driver.find_element(By.ID, "input__phone_verification_pin")
            return True
        except NoSuchElementException:
            pass

        try:
            # Check for verification code input
            self.driver.find_element(
                By.CSS_SELECTOR,
                "input[name='pin'], input[aria-label*='verification']",
            )
            return True
        except NoSuchElementException:
            pass

        return False

    def _has_login_error(self) -> bool:
        """Check if the login page is showing an error.

        Returns:
            True if there's a login error
        """
        if self.driver is None:
            return False

        try:
            # Check for error alert
            error_element = self.driver.find_element(
                By.CSS_SELECTOR,
                ".form__input--error, .alert-content, #error-for-password",
            )
            return error_element is not None
        except NoSuchElementException:
            return False

    def get_profile(self, profile_url: str) -> "Person":
        """Scrape a LinkedIn profile.

        Args:
            profile_url: LinkedIn profile URL

        Returns:
            Person object from linkedin_scraper

        Raises:
            AuthError: If not authenticated
            ProfileNotFound: If the profile doesn't exist
            ScrapingBlocked: If LinkedIn blocks the scraping attempt
        """
        if not self.authenticated:
            raise AuthError("Must authenticate before scraping profiles")

        # Import here to avoid circular imports and ensure driver is set
        from linkedin_scraper import Person

        driver = self._ensure_driver()

        # Normalize the profile URL
        normalized_url = self._normalize_profile_url(profile_url)
        logger.info("Scraping profile: %s", normalized_url)

        try:
            # Use linkedin_scraper's Person class
            person = Person(
                linkedin_url=normalized_url,
                driver=driver,
                scrape=True,
                close_on_complete=False,
            )

            logger.info("Successfully scraped profile: %s", person.name)
            return person

        except Exception as e:
            error_str = str(e).lower()

            if "404" in error_str or "not found" in error_str:
                raise ProfileNotFound(
                    normalized_url,
                    details={"error": str(e)},
                ) from e

            if "blocked" in error_str or "restricted" in error_str:
                raise ScrapingBlocked(
                    "LinkedIn has blocked this scraping attempt",
                    details={"profile_url": normalized_url, "error": str(e)},
                ) from e

            # Re-raise as generic error with context
            raise ScrapingBlocked(
                f"Failed to scrape profile: {e}",
                details={"profile_url": normalized_url, "error": str(e)},
            ) from e

    def _normalize_profile_url(self, url: str) -> str:
        """Normalize a LinkedIn profile URL.

        Args:
            url: LinkedIn profile URL or username

        Returns:
            Normalized full profile URL
        """
        url = url.strip()

        # If it's just a username, construct the full URL
        if not url.startswith("http"):
            # Remove leading slash or 'in/' if present
            url = url.lstrip("/")
            if url.startswith("in/"):
                url = url[3:]
            return f"{self.LINKEDIN_BASE_URL}/in/{url}"

        # Ensure it's using https
        url = url.replace("http://", "https://")

        # Remove trailing slash
        url = url.rstrip("/")

        return url

    def close(self) -> None:
        """Close the browser and clean up resources.

        This method is safe to call multiple times. It will only attempt
        to close the driver if it exists, and will reset the driver
        reference to None afterwards.
        """
        if self.driver is not None:
            try:
                logger.debug("Closing Chrome WebDriver")
                self.driver.quit()
                logger.info("Chrome WebDriver closed successfully")
            except WebDriverException as e:
                # Driver may already be closed or crashed
                logger.warning("WebDriverException while closing: %s", e)
            except Exception as e:
                logger.warning("Unexpected error closing WebDriver: %s", e)
            finally:
                self.driver = None
                self.authenticated = False
                self._browser_version = None
                self._driver_version = None

    def __enter__(self) -> "LinkedInScraperClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - ensures browser cleanup."""
        self.close()

    async def __aenter__(self) -> "LinkedInScraperClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit - ensures browser cleanup."""
        self.close()
