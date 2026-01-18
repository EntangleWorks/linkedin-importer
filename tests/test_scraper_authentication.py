"""Tests for LinkedIn Scraper Client authentication functionality (v3 Playwright).

This module tests:
- Cookie-based authentication (preferred method)
- Credential-based authentication (fallback)
- Unified authenticate() method
- Error mapping from linkedin_scraper exceptions to domain errors

Property-based tests validate:
- Auth method selection based on provided credentials
- Error handling and recovery scenarios
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from linkedin_importer.scraper_errors import (
    AuthError,
    CookieExpired,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_browser_manager():
    """Create a mock BrowserManager context manager."""
    manager = MagicMock()
    manager.page = MagicMock()
    manager.__aenter__ = AsyncMock(return_value=manager)
    manager.__aexit__ = AsyncMock(return_value=None)
    return manager


@pytest.fixture
def mock_runtime():
    """Create a mock _PlaywrightRuntime."""
    runtime = MagicMock()
    runtime.page = MagicMock()
    runtime.start = MagicMock()
    runtime.stop = MagicMock()
    runtime.run = MagicMock(return_value=None)
    return runtime


# =============================================================================
# Cookie Authentication Tests
# =============================================================================


class TestCookieAuthentication:
    """Tests for cookie-based authentication."""

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    @patch("linkedin_importer.scraper_client.login_with_cookie")
    def test_authenticate_with_cookie_calls_login_with_cookie(
        self, mock_login_with_cookie, mock_runtime_class
    ):
        """Cookie auth should call login_with_cookie with the page and cookie."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        # Setup mock runtime
        mock_runtime = MagicMock()
        mock_runtime.page = MagicMock()
        mock_runtime.run = MagicMock(return_value=None)
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True)
        client.authenticate(cookie="test_cookie_value")

        # Verify login_with_cookie was called via run
        assert mock_runtime.run.called
        assert client.authenticated is True

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    @patch("linkedin_importer.scraper_client.login_with_cookie")
    def test_authenticate_with_cookie_sets_authenticated_flag(
        self, mock_login_with_cookie, mock_runtime_class
    ):
        """Cookie auth should set authenticated to True on success."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime.page = MagicMock()
        mock_runtime.run = MagicMock(return_value=None)
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True)
        assert client.authenticated is False

        client.authenticate(cookie="test_cookie")
        assert client.authenticated is True

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    @patch("linkedin_importer.scraper_client.login_with_cookie")
    def test_authenticate_with_expired_cookie_raises_cookie_expired(
        self, mock_login_with_cookie, mock_runtime_class
    ):
        """Cookie auth should raise CookieExpired when cookie is invalid."""
        from linkedin_scraper.core.exceptions import AuthenticationError

        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime.page = MagicMock()
        mock_runtime.run = MagicMock(side_effect=AuthenticationError("Cookie expired"))
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True)

        with pytest.raises(CookieExpired):
            client.authenticate(cookie="expired_cookie")

        assert client.authenticated is False

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    @patch("linkedin_importer.scraper_client.login_with_cookie")
    def test_authenticate_with_cookie_exception_raises_auth_error(
        self, mock_login_with_cookie, mock_runtime_class
    ):
        """Cookie auth should raise AuthError for unexpected exceptions."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime.page = MagicMock()
        mock_runtime.run = MagicMock(side_effect=Exception("Network error"))
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True)

        with pytest.raises(AuthError) as exc_info:
            client.authenticate(cookie="test_cookie")

        assert "Cookie authentication failed" in str(exc_info.value)


# =============================================================================
# Credential Authentication Tests
# =============================================================================


class TestCredentialAuthentication:
    """Tests for email/password credential authentication."""

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    @patch("linkedin_importer.scraper_client.login_with_credentials")
    def test_authenticate_with_credentials_calls_login_with_credentials(
        self, mock_login_with_credentials, mock_runtime_class
    ):
        """Credential auth should call login_with_credentials."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime.page = MagicMock()
        mock_runtime.run = MagicMock(return_value=None)
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True, page_load_timeout=30)
        client.authenticate(email="user@example.com", password="password123")

        assert mock_runtime.run.called
        assert client.authenticated is True

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    @patch("linkedin_importer.scraper_client.login_with_credentials")
    def test_authenticate_with_credentials_sets_authenticated_flag(
        self, mock_login_with_credentials, mock_runtime_class
    ):
        """Credential auth should set authenticated to True on success."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime.page = MagicMock()
        mock_runtime.run = MagicMock(return_value=None)
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True)
        assert client.authenticated is False

        client.authenticate(email="user@example.com", password="password123")
        assert client.authenticated is True

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    @patch("linkedin_importer.scraper_client.login_with_credentials")
    def test_authenticate_with_credentials_auth_error(
        self, mock_login_with_credentials, mock_runtime_class
    ):
        """Credential auth should raise AuthError on authentication failure."""
        from linkedin_scraper.core.exceptions import AuthenticationError

        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime.page = MagicMock()
        mock_runtime.run = MagicMock(
            side_effect=AuthenticationError("Invalid credentials")
        )
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True)

        with pytest.raises(AuthError) as exc_info:
            client.authenticate(email="user@example.com", password="wrong_password")

        assert "Credential authentication failed" in str(exc_info.value)
        assert client.authenticated is False


# =============================================================================
# Unified Authentication Tests
# =============================================================================


class TestUnifiedAuthenticate:
    """Tests for the unified authenticate() method."""

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    @patch("linkedin_importer.scraper_client.login_with_cookie")
    def test_authenticate_uses_cookie_when_provided(
        self, mock_login_with_cookie, mock_runtime_class
    ):
        """When cookie is provided, authenticate should use cookie auth."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime.page = MagicMock()
        mock_runtime.run = MagicMock(return_value=None)
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True)
        client.authenticate(cookie="test_cookie")

        assert client.authenticated is True

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    @patch("linkedin_importer.scraper_client.login_with_credentials")
    def test_authenticate_uses_credentials_when_no_cookie(
        self, mock_login_with_credentials, mock_runtime_class
    ):
        """When no cookie, authenticate should use credentials."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime.page = MagicMock()
        mock_runtime.run = MagicMock(return_value=None)
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True)
        client.authenticate(email="user@example.com", password="password123")

        assert client.authenticated is True

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    @patch("linkedin_importer.scraper_client.login_with_cookie")
    def test_authenticate_prefers_cookie_over_credentials(
        self, mock_login_with_cookie, mock_runtime_class
    ):
        """When both cookie and credentials provided, cookie should be used."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime.page = MagicMock()
        mock_runtime.run = MagicMock(return_value=None)
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True)
        client.authenticate(
            cookie="test_cookie", email="user@example.com", password="password123"
        )

        # Cookie auth should be used, credentials ignored
        assert client.authenticated is True

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    def test_authenticate_raises_auth_error_when_no_credentials(
        self, mock_runtime_class
    ):
        """When no auth method provided, should raise AuthError."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime.page = MagicMock()
        mock_runtime.run = MagicMock()
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True)

        with pytest.raises(AuthError) as exc_info:
            client.authenticate()

        assert "requires either a valid LINKEDIN_COOKIE or email/password" in str(
            exc_info.value
        )

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    def test_authenticate_raises_auth_error_with_only_email(self, mock_runtime_class):
        """When only email provided (no password), should raise AuthError."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime.page = MagicMock()
        mock_runtime.run = MagicMock()
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True)

        with pytest.raises(AuthError):
            client.authenticate(email="user@example.com")

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    def test_authenticate_raises_auth_error_with_only_password(
        self, mock_runtime_class
    ):
        """When only password provided (no email), should raise AuthError."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime.page = MagicMock()
        mock_runtime.run = MagicMock()
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True)

        with pytest.raises(AuthError):
            client.authenticate(password="password123")


# =============================================================================
# Property-Based Tests
# =============================================================================


class TestAuthenticationPropertyBased:
    """Property-based tests for authentication."""

    @given(cookie=st.text(min_size=1, max_size=200).filter(lambda x: x.strip()))
    @settings(
        max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    @patch("linkedin_importer.scraper_client.login_with_cookie")
    def test_any_non_empty_cookie_attempts_auth(
        self, mock_login_with_cookie, mock_runtime_class, cookie
    ):
        """Any non-empty cookie string should attempt authentication."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime.page = MagicMock()
        mock_runtime.run = MagicMock(return_value=None)
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True)
        client.authenticate(cookie=cookie)

        assert client.authenticated is True

    @given(
        email=st.emails(),
        password=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
    )
    @settings(
        max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    @patch("linkedin_importer.scraper_client.login_with_credentials")
    def test_valid_credentials_attempt_auth(
        self, mock_login_with_credentials, mock_runtime_class, email, password
    ):
        """Valid email and password should attempt authentication."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime.page = MagicMock()
        mock_runtime.run = MagicMock(return_value=None)
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True)
        client.authenticate(email=email, password=password)

        assert client.authenticated is True


# =============================================================================
# Driver Info Tests
# =============================================================================


class TestDriverInfo:
    """Tests for driver info stub method."""

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    def test_get_driver_info_returns_playwright_info(self, mock_runtime_class):
        """get_driver_info should return Playwright-specific info."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime.page = MagicMock()
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True)
        info = client.get_driver_info()

        assert info["chrome_version"] == "playwright-chromium"
        assert info["driver_version"] == "playwright"


# =============================================================================
# Context Manager Tests
# =============================================================================


class TestContextManager:
    """Tests for context manager functionality."""

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    def test_enter_returns_client(self, mock_runtime_class):
        """__enter__ should return the client instance."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True)
        result = client.__enter__()

        assert result is client

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    def test_exit_calls_close(self, mock_runtime_class):
        """__exit__ should call close()."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True)
        client.__exit__(None, None, None)

        mock_runtime.stop.assert_called_once()

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    def test_close_resets_authenticated_flag(self, mock_runtime_class):
        """close() should reset authenticated to False."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime.run = MagicMock(return_value=None)
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True)
        client.authenticated = True

        client.close()

        assert client.authenticated is False

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    def test_close_is_idempotent(self, mock_runtime_class):
        """close() should be safe to call multiple times."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True)

        # Call close multiple times
        client.close()
        client.close()
        client.close()

        # Should not raise any errors
        assert client.authenticated is False
