"""Scraper-specific error classes for LinkedIn Profile Importer.

This module defines error classes for handling scraping-specific failures
when using Selenium and the linkedin_scraper library.
"""

from typing import Any, Optional

from .errors import ImportError


class ScraperError(ImportError):
    """Base error for scraping operations."""

    def __init__(
        self,
        message: str,
        details: Optional[dict[str, Any]] = None,
        recoverable: bool = False,
    ):
        """Initialize scraper error.

        Args:
            message: Human-readable error message
            details: Additional error context
            recoverable: Whether the error can be recovered from with retry
        """
        super().__init__("scraper", message, details)
        self.recoverable = recoverable


class BrowserError(ScraperError):
    """Error related to browser/WebDriver operations."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        """Initialize browser error.

        Examples:
            - ChromeDriver not found
            - Browser failed to start
            - Browser crashed during operation
        """
        super().__init__(message, details, recoverable=True)


class ScraperAuthError(ScraperError):
    """Error related to LinkedIn authentication during scraping.

    This is the scraper-specific auth error class, distinct from the
    generic AuthError in errors.py. Use this for scraper authentication
    failures like invalid cookies, expired sessions, etc.
    """

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        """Initialize scraper auth error.

        Examples:
            - Invalid credentials
            - Missing cookie
            - Session expired
        """
        super().__init__(message, details, recoverable=False)


class TwoFactorRequired(ScraperAuthError):
    """Error indicating 2FA verification is required.

    This error is raised when LinkedIn requires two-factor authentication
    during login. The user must complete the verification manually.
    """

    def __init__(
        self,
        message: str = "Two-factor authentication required. Complete the challenge in the browser and press Enter.",
        details: Optional[dict[str, Any]] = None,
    ):
        """Initialize 2FA required error.

        This error is raised when LinkedIn requires 2FA verification
        during login. The user must complete the verification manually.
        """
        super().__init__(message, details)
        # Override recoverable since user can complete 2FA manually
        self.recoverable = True


class CookieExpired(ScraperAuthError):
    """Error indicating the LinkedIn session cookie has expired.

    This error is raised when the li_at cookie is no longer valid
    and the user needs to obtain a fresh cookie from their browser.
    """

    def __init__(
        self,
        message: str = "LinkedIn session cookie has expired. Please obtain a fresh li_at cookie from LinkedIn.",
        details: Optional[dict[str, Any]] = None,
    ):
        """Initialize cookie expired error.

        This error is raised when the li_at cookie is no longer valid
        and the user needs to obtain a fresh cookie.
        """
        super().__init__(message, details)
        # Not recoverable - user must manually refresh cookie
        self.recoverable = False


class ProfileNotFound(ScraperError):
    """Error indicating the LinkedIn profile was not found.

    This error is raised when navigating to a profile URL returns
    a 404 or the profile does not exist.
    """

    def __init__(
        self,
        profile_url: str,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        """Initialize profile not found error.

        Args:
            profile_url: The URL that was requested
            message: Optional custom message
            details: Additional error context
        """
        error_message = (
            message
            or f"Profile not found: {profile_url}. Verify the profile exists and is publicly accessible."
        )
        error_details = details or {}
        error_details["profile_url"] = profile_url
        super().__init__(error_message, error_details, recoverable=False)
        self.profile_url = profile_url


class ScrapingBlocked(ScraperError):
    """Error indicating LinkedIn has blocked scraping activity.

    This error is raised when LinkedIn detects automated activity
    and blocks further requests. The user should wait before retrying
    or use a different account.
    """

    def __init__(
        self,
        message: str = "LinkedIn has blocked this scraping attempt. Try again later or use a different account.",
        details: Optional[dict[str, Any]] = None,
        retry_after: Optional[int] = None,
    ):
        """Initialize scraping blocked error.

        Args:
            message: Human-readable error message
            details: Additional error context
            retry_after: Suggested wait time in seconds before retrying
        """
        error_details = details or {}
        if retry_after:
            error_details["retry_after_seconds"] = retry_after
            message = f"{message} Suggested wait time: {retry_after} seconds."
        super().__init__(message, error_details, recoverable=True)
        self.retry_after = retry_after


class ElementNotFound(ScraperError):
    """Error indicating a required page element was not found.

    This error is raised when expected HTML elements cannot be found
    on the page. This may indicate LinkedIn has changed their page layout.
    """

    def __init__(
        self,
        element_name: str,
        selector: Optional[str] = None,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        """Initialize element not found error.

        Args:
            element_name: Human-readable name of the element
            selector: CSS/XPath selector that was used
            message: Optional custom message
            details: Additional error context
        """
        error_message = (
            message
            or f"Page element not found: {element_name}. LinkedIn may have changed their page layout."
        )
        error_details = details or {}
        error_details["element_name"] = element_name
        if selector:
            error_details["selector"] = selector
        super().__init__(error_message, error_details, recoverable=True)
        self.element_name = element_name
        self.selector = selector


class PageLoadTimeout(ScraperError):
    """Error indicating a page failed to load within the timeout period.

    This error is raised when page navigation or element loading exceeds
    the configured timeout. The operation can be retried with increased timeout.
    """

    def __init__(
        self,
        url: str,
        timeout_seconds: int,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        """Initialize page load timeout error.

        Args:
            url: The URL that timed out
            timeout_seconds: The timeout value that was exceeded
            message: Optional custom message
            details: Additional error context
        """
        error_message = (
            message or f"Page load timed out after {timeout_seconds}s: {url}"
        )
        error_details = details or {}
        error_details["url"] = url
        error_details["timeout_seconds"] = timeout_seconds
        super().__init__(error_message, error_details, recoverable=True)
        self.url = url
        self.timeout_seconds = timeout_seconds


# Backwards compatibility alias - deprecated, use ScraperAuthError instead
AuthError = ScraperAuthError
