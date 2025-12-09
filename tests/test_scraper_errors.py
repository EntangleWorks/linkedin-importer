"""Comprehensive tests for scraper-specific error classes.

Tests error message formatting, details propagation, inheritance hierarchy,
and recoverable flag behavior for all scraper error classes.

Validates Requirements: 8.1, 8.2, 8.4, 8.5
"""

from datetime import datetime
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from linkedin_importer.errors import ImportError
from linkedin_importer.scraper_errors import (
    AuthError,
    BrowserError,
    CookieExpired,
    ElementNotFound,
    PageLoadTimeout,
    ProfileNotFound,
    ScraperAuthError,
    ScraperError,
    ScrapingBlocked,
    TwoFactorRequired,
)

# Hypothesis strategies
error_messages = st.text(min_size=1, max_size=200).filter(lambda x: x.strip())
error_details = st.dictionaries(
    keys=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
    values=st.one_of(
        st.text(max_size=100),
        st.integers(),
        st.booleans(),
        st.none(),
    ),
    min_size=0,
    max_size=5,
)
profile_urls = st.text(min_size=5, max_size=200).map(
    lambda x: f"https://linkedin.com/in/{x.replace('/', '-')}"
)
element_names = st.text(min_size=1, max_size=50).filter(lambda x: x.strip())
selectors = st.text(min_size=1, max_size=100).filter(lambda x: x.strip())
timeout_values = st.integers(min_value=1, max_value=300)
retry_after_values = st.integers(min_value=1, max_value=3600)


class TestScraperErrorHierarchy:
    """Test the inheritance hierarchy of scraper error classes."""

    def test_scraper_error_extends_import_error(self):
        """ScraperError should extend ImportError."""
        error = ScraperError("test message")
        assert isinstance(error, ImportError)
        assert isinstance(error, Exception)

    def test_browser_error_extends_scraper_error(self):
        """BrowserError should extend ScraperError."""
        error = BrowserError("test message")
        assert isinstance(error, ScraperError)
        assert isinstance(error, ImportError)

    def test_scraper_auth_error_extends_scraper_error(self):
        """ScraperAuthError should extend ScraperError."""
        error = ScraperAuthError("test message")
        assert isinstance(error, ScraperError)
        assert isinstance(error, ImportError)

    def test_two_factor_required_extends_scraper_auth_error(self):
        """TwoFactorRequired should extend ScraperAuthError (Requirement 8.2)."""
        error = TwoFactorRequired()
        assert isinstance(error, ScraperAuthError)
        assert isinstance(error, ScraperError)
        assert isinstance(error, ImportError)

    def test_cookie_expired_extends_scraper_auth_error(self):
        """CookieExpired should extend ScraperAuthError (Requirements 8.1, 8.2)."""
        error = CookieExpired()
        assert isinstance(error, ScraperAuthError)
        assert isinstance(error, ScraperError)
        assert isinstance(error, ImportError)

    def test_profile_not_found_extends_scraper_error(self):
        """ProfileNotFound should extend ScraperError (Requirement 8.1)."""
        error = ProfileNotFound("https://linkedin.com/in/test")
        assert isinstance(error, ScraperError)
        assert isinstance(error, ImportError)

    def test_scraping_blocked_extends_scraper_error(self):
        """ScrapingBlocked should extend ScraperError (Requirement 8.5)."""
        error = ScrapingBlocked()
        assert isinstance(error, ScraperError)
        assert isinstance(error, ImportError)

    def test_element_not_found_extends_scraper_error(self):
        """ElementNotFound should extend ScraperError (Requirement 8.4)."""
        error = ElementNotFound("profile-name")
        assert isinstance(error, ScraperError)
        assert isinstance(error, ImportError)

    def test_page_load_timeout_extends_scraper_error(self):
        """PageLoadTimeout should extend ScraperError."""
        error = PageLoadTimeout("https://linkedin.com", 30)
        assert isinstance(error, ScraperError)
        assert isinstance(error, ImportError)

    def test_auth_error_alias_is_scraper_auth_error(self):
        """AuthError should be an alias for ScraperAuthError."""
        assert AuthError is ScraperAuthError


class TestScraperErrorRecoverableFlag:
    """Test the recoverable flag for each error type."""

    def test_scraper_error_default_recoverable_is_false(self):
        """ScraperError default recoverable should be False."""
        error = ScraperError("test")
        assert error.recoverable is False

    def test_scraper_error_recoverable_can_be_set(self):
        """ScraperError recoverable can be set to True."""
        error = ScraperError("test", recoverable=True)
        assert error.recoverable is True

    def test_browser_error_is_recoverable(self):
        """BrowserError should be recoverable (can restart browser)."""
        error = BrowserError("test")
        assert error.recoverable is True

    def test_scraper_auth_error_is_not_recoverable(self):
        """ScraperAuthError should not be recoverable by default."""
        error = ScraperAuthError("test")
        assert error.recoverable is False

    def test_two_factor_required_is_recoverable(self):
        """TwoFactorRequired should be recoverable (user can complete 2FA)."""
        error = TwoFactorRequired()
        assert error.recoverable is True

    def test_cookie_expired_is_not_recoverable(self):
        """CookieExpired should not be recoverable (needs manual refresh)."""
        error = CookieExpired()
        assert error.recoverable is False

    def test_profile_not_found_is_not_recoverable(self):
        """ProfileNotFound should not be recoverable."""
        error = ProfileNotFound("https://linkedin.com/in/test")
        assert error.recoverable is False

    def test_scraping_blocked_is_recoverable(self):
        """ScrapingBlocked should be recoverable (can wait and retry)."""
        error = ScrapingBlocked()
        assert error.recoverable is True

    def test_element_not_found_is_recoverable(self):
        """ElementNotFound should be recoverable (may succeed on retry)."""
        error = ElementNotFound("profile-name")
        assert error.recoverable is True

    def test_page_load_timeout_is_recoverable(self):
        """PageLoadTimeout should be recoverable (can retry with longer timeout)."""
        error = PageLoadTimeout("https://linkedin.com", 30)
        assert error.recoverable is True


class TestScraperErrorMessages:
    """Test error message formatting and content."""

    def test_scraper_error_message_includes_error_type(self):
        """ScraperError string representation should include error type."""
        error = ScraperError("test message")
        assert "scraper" in str(error)
        assert "test message" in str(error)

    def test_browser_error_includes_driver_info_suggestion(self):
        """BrowserError should include driver info when provided (Requirement 8.5)."""
        details = {"driver_info": "chromedriver 114.0.5735.90"}
        error = BrowserError(
            "Failed to initialize browser: chromedriver not found", details
        )
        assert (
            "chromedriver" in str(error).lower()
            or "chromedriver" in error.message.lower()
        )
        assert error.details["driver_info"] == "chromedriver 114.0.5735.90"

    def test_two_factor_required_default_message(self):
        """TwoFactorRequired should have a descriptive default message."""
        error = TwoFactorRequired()
        assert "two-factor" in error.message.lower() or "2fa" in error.message.lower()
        assert (
            "complete" in error.message.lower() or "challenge" in error.message.lower()
        )

    def test_cookie_expired_default_message_includes_refresh_suggestion(self):
        """CookieExpired message should suggest refreshing cookie (Requirement 8.1)."""
        error = CookieExpired()
        assert "expired" in error.message.lower()
        assert "fresh" in error.message.lower() or "obtain" in error.message.lower()
        assert "li_at" in error.message or "cookie" in error.message.lower()

    def test_profile_not_found_includes_url(self):
        """ProfileNotFound message should include the profile URL (Requirement 8.1)."""
        url = "https://linkedin.com/in/nonexistent-user"
        error = ProfileNotFound(url)
        assert url in error.message
        assert error.profile_url == url

    def test_scraping_blocked_default_message(self):
        """ScrapingBlocked should have a descriptive default message."""
        error = ScrapingBlocked()
        assert "blocked" in error.message.lower()
        assert "try again" in error.message.lower() or "later" in error.message.lower()

    def test_scraping_blocked_with_retry_after(self):
        """ScrapingBlocked with retry_after should include wait time."""
        error = ScrapingBlocked(retry_after=300)
        assert error.retry_after == 300
        assert "300" in error.message or error.details.get("retry_after_seconds") == 300

    def test_element_not_found_includes_element_name(self):
        """ElementNotFound should include element name (Requirement 8.4)."""
        error = ElementNotFound("profile-headline")
        assert "profile-headline" in error.message
        assert error.element_name == "profile-headline"

    def test_element_not_found_suggests_layout_change(self):
        """ElementNotFound should suggest possible layout change (Requirement 8.4)."""
        error = ElementNotFound("profile-name")
        assert "layout" in error.message.lower() or "changed" in error.message.lower()

    def test_element_not_found_includes_selector_in_details(self):
        """ElementNotFound should include selector in details when provided."""
        error = ElementNotFound("profile-name", selector="div.pv-top-card--title")
        assert error.details["selector"] == "div.pv-top-card--title"
        assert error.selector == "div.pv-top-card--title"

    def test_page_load_timeout_includes_url_and_timeout(self):
        """PageLoadTimeout should include URL and timeout value."""
        error = PageLoadTimeout("https://linkedin.com/in/test", 30)
        assert (
            "https://linkedin.com/in/test" in error.message
            or error.url == "https://linkedin.com/in/test"
        )
        assert "30" in error.message or error.timeout_seconds == 30


class TestScraperErrorDetails:
    """Test error details propagation and accessibility."""

    @given(message=error_messages, details=error_details)
    def test_scraper_error_preserves_details(
        self, message: str, details: dict[str, Any]
    ):
        """ScraperError should preserve all provided details."""
        error = ScraperError(message, details)
        for key, value in details.items():
            assert error.details[key] == value

    def test_scraper_error_has_timestamp(self):
        """ScraperError should have a timestamp."""
        before = datetime.now()
        error = ScraperError("test")
        after = datetime.now()
        assert before <= error.timestamp <= after

    def test_browser_error_details_include_driver_info(self):
        """BrowserError details should support driver info."""
        details = {
            "driver_info": "chromedriver 114.0.5735.90",
            "chrome_version": "114.0.5735.90",
            "platform": "linux64",
        }
        error = BrowserError("Failed to start browser", details)
        assert error.details["driver_info"] == "chromedriver 114.0.5735.90"
        assert error.details["chrome_version"] == "114.0.5735.90"

    def test_profile_not_found_auto_includes_url_in_details(self):
        """ProfileNotFound should automatically include URL in details."""
        url = "https://linkedin.com/in/test-user"
        error = ProfileNotFound(url)
        assert error.details["profile_url"] == url

    def test_scraping_blocked_includes_retry_after_in_details(self):
        """ScrapingBlocked should include retry_after in details when provided."""
        error = ScrapingBlocked(retry_after=600)
        assert error.details["retry_after_seconds"] == 600

    def test_element_not_found_includes_element_and_selector_in_details(self):
        """ElementNotFound should include element name and selector in details."""
        error = ElementNotFound("name-field", selector="h1.text-heading-xlarge")
        assert error.details["element_name"] == "name-field"
        assert error.details["selector"] == "h1.text-heading-xlarge"

    def test_page_load_timeout_includes_url_and_timeout_in_details(self):
        """PageLoadTimeout should include URL and timeout in details."""
        error = PageLoadTimeout("https://linkedin.com", 45)
        assert error.details["url"] == "https://linkedin.com"
        assert error.details["timeout_seconds"] == 45


class TestScraperErrorProperties:
    """Property-based tests for scraper errors."""

    @given(message=error_messages, details=error_details)
    def test_scraper_error_message_preserved(
        self, message: str, details: dict[str, Any]
    ):
        """Property: Error message is always preserved."""
        error = ScraperError(message, details)
        assert error.message == message
        assert message in str(error)

    @given(message=error_messages)
    def test_browser_error_always_recoverable(self, message: str):
        """Property: BrowserError is always recoverable."""
        error = BrowserError(message)
        assert error.recoverable is True

    @given(message=error_messages)
    def test_scraper_auth_error_always_not_recoverable(self, message: str):
        """Property: ScraperAuthError is never recoverable by default."""
        error = ScraperAuthError(message)
        assert error.recoverable is False

    @given(url=profile_urls)
    def test_profile_not_found_always_includes_url(self, url: str):
        """Property: ProfileNotFound always includes URL in message and details."""
        error = ProfileNotFound(url)
        assert url in error.message or error.profile_url == url
        assert error.details["profile_url"] == url

    @given(retry_after=retry_after_values)
    def test_scraping_blocked_retry_after_in_details(self, retry_after: int):
        """Property: ScrapingBlocked retry_after is always in details when provided."""
        error = ScrapingBlocked(retry_after=retry_after)
        assert error.details["retry_after_seconds"] == retry_after
        assert error.retry_after == retry_after

    @given(element=element_names, selector=selectors)
    def test_element_not_found_preserves_element_and_selector(
        self, element: str, selector: str
    ):
        """Property: ElementNotFound preserves element name and selector."""
        error = ElementNotFound(element, selector=selector)
        assert error.element_name == element
        assert error.selector == selector
        assert error.details["element_name"] == element
        assert error.details["selector"] == selector

    @given(url=profile_urls, timeout=timeout_values)
    def test_page_load_timeout_preserves_url_and_timeout(self, url: str, timeout: int):
        """Property: PageLoadTimeout preserves URL and timeout."""
        error = PageLoadTimeout(url, timeout)
        assert error.url == url
        assert error.timeout_seconds == timeout
        assert error.details["url"] == url
        assert error.details["timeout_seconds"] == timeout


class TestScraperErrorExceptions:
    """Test that errors can be raised and caught properly."""

    def test_scraper_error_can_be_raised_and_caught(self):
        """ScraperError should be raisable and catchable."""
        with pytest.raises(ScraperError) as exc_info:
            raise ScraperError("test error")
        assert "test error" in str(exc_info.value)

    def test_catch_browser_error_as_scraper_error(self):
        """BrowserError should be catchable as ScraperError."""
        with pytest.raises(ScraperError):
            raise BrowserError("browser failed")

    def test_catch_two_factor_as_scraper_auth_error(self):
        """TwoFactorRequired should be catchable as ScraperAuthError."""
        with pytest.raises(ScraperAuthError):
            raise TwoFactorRequired()

    def test_catch_cookie_expired_as_scraper_auth_error(self):
        """CookieExpired should be catchable as ScraperAuthError."""
        with pytest.raises(ScraperAuthError):
            raise CookieExpired()

    def test_catch_all_scraper_errors_as_import_error(self):
        """All scraper errors should be catchable as ImportError."""
        errors = [
            ScraperError("test"),
            BrowserError("test"),
            ScraperAuthError("test"),
            TwoFactorRequired(),
            CookieExpired(),
            ProfileNotFound("https://linkedin.com/in/test"),
            ScrapingBlocked(),
            ElementNotFound("element"),
            PageLoadTimeout("https://linkedin.com", 30),
        ]
        for error in errors:
            with pytest.raises(ImportError):
                raise error


class TestScraperErrorRealWorldScenarios:
    """Test real-world error scenarios."""

    def test_browser_initialization_failure(self):
        """Test browser initialization failure scenario."""
        error = BrowserError(
            "Failed to initialize browser: chromedriver not found",
            {
                "driver_info": None,
                "error": "ChromeDriver executable not found",
                "suggestion": "Install chromedriver or set CHROMEDRIVER_PATH",
            },
        )
        assert error.recoverable is True
        assert "chromedriver" in error.message.lower()

    def test_session_expired_scenario(self):
        """Test session expired during scraping."""
        error = CookieExpired(
            details={
                "cookie_age_hours": 72,
                "last_valid_check": "2024-01-01T00:00:00Z",
            }
        )
        assert error.recoverable is False
        assert "expired" in error.message.lower()

    def test_two_factor_challenge_scenario(self):
        """Test 2FA challenge scenario."""
        error = TwoFactorRequired(
            details={
                "challenge_type": "sms",
                "phone_hint": "+1 ***-***-1234",
            }
        )
        assert error.recoverable is True
        assert "2fa" in error.message.lower() or "two-factor" in error.message.lower()

    def test_profile_does_not_exist(self):
        """Test profile not found scenario."""
        error = ProfileNotFound(
            "https://linkedin.com/in/deleted-user-12345",
            details={"http_status": 404},
        )
        assert error.recoverable is False
        assert "deleted-user-12345" in error.message

    def test_rate_limit_block(self):
        """Test rate limiting scenario."""
        error = ScrapingBlocked(
            message="Too many requests",
            retry_after=3600,
            details={"blocked_reason": "rate_limit"},
        )
        assert error.recoverable is True
        assert error.retry_after == 3600

    def test_linkedin_layout_change(self):
        """Test LinkedIn layout change scenario."""
        error = ElementNotFound(
            "experience-section",
            selector="section.experience",
            details={
                "page_url": "https://linkedin.com/in/test",
                "expected_structure": "section.experience",
                "suggestion": "LinkedIn may have updated their UI",
            },
        )
        assert error.recoverable is True
        assert "layout" in error.message.lower()

    def test_slow_network_timeout(self):
        """Test page load timeout scenario."""
        error = PageLoadTimeout(
            "https://linkedin.com/in/test",
            30,
            details={
                "network_type": "slow_3g",
                "partial_load": True,
            },
        )
        assert error.recoverable is True
        assert error.timeout_seconds == 30


class TestScraperErrorCustomMessages:
    """Test custom message support for errors."""

    def test_profile_not_found_custom_message(self):
        """ProfileNotFound should support custom messages."""
        custom_msg = "This LinkedIn profile has been removed"
        error = ProfileNotFound(
            "https://linkedin.com/in/test",
            message=custom_msg,
        )
        assert error.message == custom_msg

    def test_element_not_found_custom_message(self):
        """ElementNotFound should support custom messages."""
        custom_msg = "Could not find the skills section after page update"
        error = ElementNotFound(
            "skills-section",
            message=custom_msg,
        )
        assert error.message == custom_msg

    def test_page_load_timeout_custom_message(self):
        """PageLoadTimeout should support custom messages."""
        custom_msg = "LinkedIn is experiencing high traffic"
        error = PageLoadTimeout(
            "https://linkedin.com",
            60,
            message=custom_msg,
        )
        assert error.message == custom_msg
