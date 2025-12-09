"""Tests for LinkedIn Scraper Client authentication functionality.

This module tests:
- Cookie-based authentication (preferred method)
- Credential-based authentication (fallback)
- 2FA detection and handling
- Unified authenticate() method
- Login verification

Property-based tests validate:
- Cookie properties are correctly set
- Login status correctly detected
- 2FA challenge correctly detected
- Correct auth method selected based on config
"""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import MagicMock, Mock, PropertyMock, patch

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from linkedin_importer.errors import ConfigError
from linkedin_importer.scraper_client import (
    AuthMethod,
    LinkedInScraperClient,
)
from linkedin_importer.scraper_errors import (
    AuthError,
    CookieExpired,
    TwoFactorRequired,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_driver():
    """Create a mock WebDriver instance."""
    driver = MagicMock()
    driver.current_url = "https://www.linkedin.com/feed/"
    driver.capabilities = {
        "browserVersion": "120.0.0",
        "chrome": {"chromedriverVersion": "120.0.0"},
    }
    return driver


@pytest.fixture
def client():
    """Create a LinkedInScraperClient instance without starting a browser."""
    return LinkedInScraperClient(headless=True)


@pytest.fixture
def client_with_mock_driver(client, mock_driver):
    """Create a client with a mocked driver already attached."""
    client.driver = mock_driver
    return client


# =============================================================================
# Cookie Authentication Tests
# =============================================================================


class TestCookieAuthentication:
    """Tests for cookie-based authentication."""

    def test_authenticate_with_cookie_navigates_to_linkedin(
        self, client_with_mock_driver, mock_driver
    ):
        """Cookie auth should navigate to LinkedIn first."""
        mock_driver.find_element = MagicMock(return_value=MagicMock())

        client_with_mock_driver.authenticate_with_cookie("test_cookie_value")

        mock_driver.get.assert_any_call("https://www.linkedin.com")

    def test_authenticate_with_cookie_deletes_existing_cookies(
        self, client_with_mock_driver, mock_driver
    ):
        """Cookie auth should delete existing cookies before setting new one."""
        mock_driver.find_element = MagicMock(return_value=MagicMock())

        client_with_mock_driver.authenticate_with_cookie("test_cookie_value")

        mock_driver.delete_all_cookies.assert_called_once()

    def test_authenticate_with_cookie_sets_correct_properties(
        self, client_with_mock_driver, mock_driver
    ):
        """Cookie auth should set li_at cookie with correct properties."""
        mock_driver.find_element = MagicMock(return_value=MagicMock())

        client_with_mock_driver.authenticate_with_cookie("test_cookie_value")

        mock_driver.add_cookie.assert_called_once()
        cookie_arg = mock_driver.add_cookie.call_args[0][0]

        assert cookie_arg["name"] == "li_at"
        assert cookie_arg["value"] == "test_cookie_value"
        assert cookie_arg["domain"] == ".linkedin.com"
        assert cookie_arg["path"] == "/"
        assert cookie_arg["secure"] is True
        assert cookie_arg["httpOnly"] is True

    def test_authenticate_with_cookie_verifies_login(
        self, client_with_mock_driver, mock_driver
    ):
        """Cookie auth should verify login after setting cookie."""
        mock_driver.find_element = MagicMock(return_value=MagicMock())

        result = client_with_mock_driver.authenticate_with_cookie("test_cookie_value")

        assert result is True
        assert client_with_mock_driver.authenticated is True

    def test_authenticate_with_cookie_navigates_to_feed(
        self, client_with_mock_driver, mock_driver
    ):
        """Cookie auth should navigate to feed to verify authentication."""
        mock_driver.find_element = MagicMock(return_value=MagicMock())

        client_with_mock_driver.authenticate_with_cookie("test_cookie_value")

        mock_driver.get.assert_any_call("https://www.linkedin.com/feed/")

    def test_authenticate_with_cookie_expired_redirect_to_login(
        self, client_with_mock_driver, mock_driver
    ):
        """Cookie auth should raise CookieExpired when redirected to login."""
        from selenium.common.exceptions import NoSuchElementException

        mock_driver.current_url = "https://www.linkedin.com/login"
        mock_driver.find_element = MagicMock(side_effect=NoSuchElementException())

        with pytest.raises(CookieExpired) as exc_info:
            client_with_mock_driver.authenticate_with_cookie("expired_cookie")

        assert (
            "expired" in str(exc_info.value).lower()
            or "invalid" in str(exc_info.value).lower()
        )

    def test_authenticate_with_cookie_expired_checkpoint(
        self, client_with_mock_driver, mock_driver
    ):
        """Cookie auth should raise CookieExpired when redirected to checkpoint."""
        from selenium.common.exceptions import NoSuchElementException

        mock_driver.current_url = "https://www.linkedin.com/checkpoint"
        mock_driver.find_element = MagicMock(side_effect=NoSuchElementException())

        with pytest.raises(CookieExpired):
            client_with_mock_driver.authenticate_with_cookie("invalid_cookie")

    def test_authenticate_with_cookie_exception_raises_auth_error(
        self, client_with_mock_driver, mock_driver
    ):
        """Cookie auth should wrap unexpected exceptions in AuthError."""
        mock_driver.get = MagicMock(side_effect=Exception("Network error"))

        with pytest.raises(AuthError) as exc_info:
            client_with_mock_driver.authenticate_with_cookie("test_cookie")

        assert (
            "Network error" in str(exc_info.value)
            or "failed" in str(exc_info.value).lower()
        )


class TestCookieAuthenticationPropertyBased:
    """Property-based tests for cookie authentication."""

    @given(cookie_value=st.text(min_size=10, max_size=500))
    @settings(
        max_examples=25,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_cookie_value_preserved(self, cookie_value, client, mock_driver):
        """Property: Cookie value should be preserved exactly."""
        client.driver = mock_driver
        mock_driver.find_element = MagicMock(return_value=MagicMock())

        with patch("linkedin_importer.scraper_client.time.sleep"):
            client.authenticate_with_cookie(cookie_value)

        cookie_arg = mock_driver.add_cookie.call_args[0][0]
        assert cookie_arg["value"] == cookie_value

    @given(cookie_value=st.text(min_size=10, max_size=100))
    @settings(
        max_examples=25,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_cookie_always_secure(self, cookie_value, client, mock_driver):
        """Property: Cookie should always be marked as secure."""
        client.driver = mock_driver
        mock_driver.find_element = MagicMock(return_value=MagicMock())

        with patch("linkedin_importer.scraper_client.time.sleep"):
            client.authenticate_with_cookie(cookie_value)

        cookie_arg = mock_driver.add_cookie.call_args[0][0]
        assert cookie_arg["secure"] is True

    @given(cookie_value=st.text(min_size=10, max_size=100))
    @settings(
        max_examples=25,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_cookie_domain_is_linkedin(self, cookie_value, client, mock_driver):
        """Property: Cookie domain should always be .linkedin.com."""
        client.driver = mock_driver
        mock_driver.find_element = MagicMock(return_value=MagicMock())

        with patch("linkedin_importer.scraper_client.time.sleep"):
            client.authenticate_with_cookie(cookie_value)

        cookie_arg = mock_driver.add_cookie.call_args[0][0]
        assert cookie_arg["domain"] == ".linkedin.com"


# =============================================================================
# Credential Authentication Tests
# =============================================================================


class TestCredentialAuthentication:
    """Tests for email/password authentication."""

    def test_authenticate_with_credentials_navigates_to_login(
        self, client_with_mock_driver, mock_driver
    ):
        """Credential auth should navigate to login page."""
        from selenium.webdriver.support.ui import WebDriverWait

        mock_driver.find_element = MagicMock(return_value=MagicMock())

        with (
            patch.object(client_with_mock_driver, "_is_logged_in", return_value=True),
            patch.object(
                client_with_mock_driver, "_is_2fa_challenge", return_value=False
            ),
            patch.object(
                client_with_mock_driver, "_has_login_error", return_value=False
            ),
            patch("linkedin_importer.scraper_client.WebDriverWait") as mock_wait,
        ):
            mock_wait.return_value.until.return_value = MagicMock()

            client_with_mock_driver.authenticate_with_credentials(
                "test@example.com", "password123"
            )

            mock_driver.get.assert_called_with("https://www.linkedin.com/login")

    def test_authenticate_with_credentials_fills_form(
        self, client_with_mock_driver, mock_driver
    ):
        """Credential auth should fill in email and password fields."""
        email_field = MagicMock()
        password_field = MagicMock()
        submit_button = MagicMock()

        def find_element_side_effect(by, value):
            if value == "username":
                return email_field
            if value == "password":
                return password_field
            if value == "button[type='submit']":
                return submit_button
            raise Exception(f"Unexpected selector: {value}")

        mock_driver.find_element = MagicMock(side_effect=find_element_side_effect)

        with (
            patch.object(client_with_mock_driver, "_is_logged_in", return_value=True),
            patch.object(
                client_with_mock_driver, "_is_2fa_challenge", return_value=False
            ),
            patch.object(
                client_with_mock_driver, "_has_login_error", return_value=False
            ),
            patch("linkedin_importer.scraper_client.WebDriverWait") as mock_wait,
        ):
            mock_wait.return_value.until.return_value = email_field

            client_with_mock_driver.authenticate_with_credentials(
                "test@example.com", "password123"
            )

            email_field.send_keys.assert_called_with("test@example.com")
            password_field.send_keys.assert_called_with("password123")

    def test_authenticate_with_credentials_clicks_submit(
        self, client_with_mock_driver, mock_driver
    ):
        """Credential auth should click submit button."""
        submit_button = MagicMock()
        mock_driver.find_element = MagicMock(return_value=submit_button)

        with (
            patch.object(client_with_mock_driver, "_is_logged_in", return_value=True),
            patch.object(
                client_with_mock_driver, "_is_2fa_challenge", return_value=False
            ),
            patch.object(
                client_with_mock_driver, "_has_login_error", return_value=False
            ),
            patch("linkedin_importer.scraper_client.WebDriverWait") as mock_wait,
        ):
            mock_wait.return_value.until.return_value = MagicMock()

            client_with_mock_driver.authenticate_with_credentials(
                "test@example.com", "password123"
            )

            submit_button.click.assert_called()

    def test_authenticate_with_credentials_sets_authenticated(
        self, client_with_mock_driver, mock_driver
    ):
        """Credential auth should set authenticated flag on success."""
        mock_driver.find_element = MagicMock(return_value=MagicMock())

        with (
            patch.object(client_with_mock_driver, "_is_logged_in", return_value=True),
            patch.object(
                client_with_mock_driver, "_is_2fa_challenge", return_value=False
            ),
            patch.object(
                client_with_mock_driver, "_has_login_error", return_value=False
            ),
            patch("linkedin_importer.scraper_client.WebDriverWait") as mock_wait,
        ):
            mock_wait.return_value.until.return_value = MagicMock()

            result = client_with_mock_driver.authenticate_with_credentials(
                "test@example.com", "password123"
            )

            assert result is True
            assert client_with_mock_driver.authenticated is True

    def test_authenticate_with_credentials_detects_2fa(
        self, client_with_mock_driver, mock_driver
    ):
        """Credential auth should raise TwoFactorRequired when 2FA detected."""
        mock_driver.find_element = MagicMock(return_value=MagicMock())

        with (
            patch.object(
                client_with_mock_driver, "_is_2fa_challenge", return_value=True
            ),
            patch("linkedin_importer.scraper_client.WebDriverWait") as mock_wait,
        ):
            mock_wait.return_value.until.return_value = MagicMock()

            with pytest.raises(TwoFactorRequired):
                client_with_mock_driver.authenticate_with_credentials(
                    "test@example.com", "password123"
                )

    def test_authenticate_with_credentials_detects_login_error(
        self, client_with_mock_driver, mock_driver
    ):
        """Credential auth should raise AuthError on login failure."""
        mock_driver.find_element = MagicMock(return_value=MagicMock())

        with (
            patch.object(
                client_with_mock_driver, "_is_2fa_challenge", return_value=False
            ),
            patch.object(
                client_with_mock_driver, "_has_login_error", return_value=True
            ),
            patch("linkedin_importer.scraper_client.WebDriverWait") as mock_wait,
        ):
            mock_wait.return_value.until.return_value = MagicMock()

            with pytest.raises(AuthError) as exc_info:
                client_with_mock_driver.authenticate_with_credentials(
                    "test@example.com", "wrong_password"
                )

            assert "invalid" in str(exc_info.value).lower()


# =============================================================================
# Login Verification Tests
# =============================================================================


class TestLoginVerification:
    """Tests for _is_logged_in method."""

    def test_is_logged_in_returns_false_when_no_driver(self, client):
        """_is_logged_in should return False when driver is None."""
        assert client.driver is None
        assert client._is_logged_in() is False

    def test_is_logged_in_finds_global_nav(self, client_with_mock_driver, mock_driver):
        """_is_logged_in should return True when global-nav element found."""
        mock_driver.find_element = MagicMock(return_value=MagicMock())

        result = client_with_mock_driver._is_logged_in()

        assert result is True

    def test_is_logged_in_finds_profile_menu(
        self, client_with_mock_driver, mock_driver
    ):
        """_is_logged_in should return True when profile menu found."""
        from selenium.common.exceptions import NoSuchElementException

        call_count = 0

        def find_element_side_effect(by, value):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise NoSuchElementException()
            return MagicMock()

        mock_driver.find_element = MagicMock(side_effect=find_element_side_effect)

        result = client_with_mock_driver._is_logged_in()

        assert result is True

    def test_is_logged_in_returns_false_when_no_elements_found(
        self, client_with_mock_driver, mock_driver
    ):
        """_is_logged_in should return False when no login indicators found."""
        from selenium.common.exceptions import NoSuchElementException

        mock_driver.find_element = MagicMock(side_effect=NoSuchElementException())

        result = client_with_mock_driver._is_logged_in()

        assert result is False


class TestLoginVerificationPropertyBased:
    """Property-based tests for login verification."""

    @given(
        has_global_nav=st.booleans(),
        has_profile_menu=st.booleans(),
    )
    @settings(
        max_examples=10,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_logged_in_when_any_indicator_present(
        self, has_global_nav, has_profile_menu, client, mock_driver
    ):
        """Property: Should be logged in if any indicator is present."""
        from selenium.common.exceptions import NoSuchElementException

        client.driver = mock_driver
        call_count = 0

        def find_element_side_effect(by, value):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                if has_global_nav:
                    return MagicMock()
                raise NoSuchElementException()
            if has_profile_menu:
                return MagicMock()
            raise NoSuchElementException()

        mock_driver.find_element = MagicMock(side_effect=find_element_side_effect)

        result = client._is_logged_in()

        assert result == (has_global_nav or has_profile_menu)


# =============================================================================
# 2FA Detection Tests
# =============================================================================


class TestTwoFactorDetection:
    """Tests for _is_2fa_challenge method."""

    def test_is_2fa_challenge_returns_false_when_no_driver(self, client):
        """_is_2fa_challenge should return False when driver is None."""
        assert client.driver is None
        assert client._is_2fa_challenge() is False

    @pytest.mark.parametrize(
        "url",
        [
            "https://www.linkedin.com/checkpoint/challenge/123",
            "https://www.linkedin.com/checkpoint/challengesV2/123",
            "https://www.linkedin.com/two-step-verification/verify",
        ],
    )
    def test_is_2fa_challenge_detects_url_patterns(
        self, url, client_with_mock_driver, mock_driver
    ):
        """_is_2fa_challenge should detect 2FA from URL patterns."""
        from selenium.common.exceptions import NoSuchElementException

        mock_driver.current_url = url
        mock_driver.find_element = MagicMock(side_effect=NoSuchElementException())

        result = client_with_mock_driver._is_2fa_challenge()

        assert result is True

    def test_is_2fa_challenge_detects_pin_input(
        self, client_with_mock_driver, mock_driver
    ):
        """_is_2fa_challenge should detect 2FA from pin input element."""
        from selenium.common.exceptions import NoSuchElementException

        mock_driver.current_url = "https://www.linkedin.com/verify"
        call_count = 0

        def find_element_side_effect(by, value):
            nonlocal call_count
            call_count += 1
            if call_count == 1 and "phone_verification_pin" in value:
                return MagicMock()
            raise NoSuchElementException()

        mock_driver.find_element = MagicMock(side_effect=find_element_side_effect)

        result = client_with_mock_driver._is_2fa_challenge()

        assert result is True

    def test_is_2fa_challenge_returns_false_for_normal_pages(
        self, client_with_mock_driver, mock_driver
    ):
        """_is_2fa_challenge should return False for normal pages."""
        from selenium.common.exceptions import NoSuchElementException

        mock_driver.current_url = "https://www.linkedin.com/feed/"
        mock_driver.find_element = MagicMock(side_effect=NoSuchElementException())

        result = client_with_mock_driver._is_2fa_challenge()

        assert result is False


class TestTwoFactorDetectionPropertyBased:
    """Property-based tests for 2FA detection."""

    @given(
        url_segment=st.sampled_from(
            ["checkpoint", "challenge", "two-step-verification"]
        ),
    )
    @settings(
        max_examples=10,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_2fa_detected_for_known_patterns(self, url_segment, client, mock_driver):
        """Property: 2FA should be detected for known URL patterns."""
        from selenium.common.exceptions import NoSuchElementException

        client.driver = mock_driver
        mock_driver.current_url = f"https://www.linkedin.com/{url_segment}/123"
        mock_driver.find_element = MagicMock(side_effect=NoSuchElementException())

        result = client._is_2fa_challenge()

        assert result is True


# =============================================================================
# 2FA Handling Tests
# =============================================================================


class TestTwoFactorHandling:
    """Tests for handle_2fa_challenge method."""

    def test_handle_2fa_logs_instructions(
        self, client_with_mock_driver, mock_driver, caplog
    ):
        """handle_2fa_challenge should log clear instructions."""
        mock_driver.find_element = MagicMock(return_value=MagicMock())

        import logging

        with caplog.at_level(logging.WARNING):
            with patch("builtins.input", return_value=""):
                with patch.object(
                    client_with_mock_driver, "_is_logged_in", return_value=True
                ):
                    client_with_mock_driver.handle_2fa_challenge()

        # Check that key instructions are logged
        log_text = caplog.text
        assert "2FA VERIFICATION REQUIRED" in log_text
        assert "li_at" in log_text or "cookie" in log_text.lower()

    def test_handle_2fa_waits_for_user_input(
        self, client_with_mock_driver, mock_driver
    ):
        """handle_2fa_challenge should wait for user input."""
        mock_driver.find_element = MagicMock(return_value=MagicMock())

        with patch("builtins.input") as mock_input:
            with patch.object(
                client_with_mock_driver, "_is_logged_in", return_value=True
            ):
                client_with_mock_driver.handle_2fa_challenge()

            mock_input.assert_called_once()

    def test_handle_2fa_verifies_login_after_input(
        self, client_with_mock_driver, mock_driver
    ):
        """handle_2fa_challenge should verify login after user input."""
        with patch("builtins.input", return_value=""):
            with patch.object(
                client_with_mock_driver, "_is_logged_in", return_value=True
            ) as mock_is_logged_in:
                client_with_mock_driver.handle_2fa_challenge()

                mock_is_logged_in.assert_called()

    def test_handle_2fa_sets_authenticated_on_success(
        self, client_with_mock_driver, mock_driver
    ):
        """handle_2fa_challenge should set authenticated flag on success."""
        with patch("builtins.input", return_value=""):
            with patch.object(
                client_with_mock_driver, "_is_logged_in", return_value=True
            ):
                result = client_with_mock_driver.handle_2fa_challenge()

                assert result is True
                assert client_with_mock_driver.authenticated is True

    def test_handle_2fa_raises_on_failure(self, client_with_mock_driver, mock_driver):
        """handle_2fa_challenge should raise TwoFactorRequired on failure."""
        mock_driver.current_url = "https://www.linkedin.com/verify"

        with patch("builtins.input", return_value=""):
            with patch.object(
                client_with_mock_driver, "_is_logged_in", return_value=False
            ):
                with pytest.raises(TwoFactorRequired):
                    client_with_mock_driver.handle_2fa_challenge()

    def test_handle_2fa_handles_eof_in_non_interactive_mode(
        self, client_with_mock_driver, mock_driver
    ):
        """handle_2fa_challenge should handle EOFError in non-interactive mode."""
        with patch("builtins.input", side_effect=EOFError()):
            with patch.object(
                client_with_mock_driver, "wait_for_2fa_completion", return_value=True
            ) as mock_wait:
                result = client_with_mock_driver.handle_2fa_challenge(timeout=60)

                mock_wait.assert_called_once_with(60)
                assert result is True


class TestWaitFor2FACompletion:
    """Tests for wait_for_2fa_completion method."""

    def test_wait_for_2fa_returns_true_when_logged_in(
        self, client_with_mock_driver, mock_driver
    ):
        """wait_for_2fa_completion should return True when login detected."""
        with patch.object(client_with_mock_driver, "_is_logged_in", return_value=True):
            result = client_with_mock_driver.wait_for_2fa_completion(timeout=10)

            assert result is True
            assert client_with_mock_driver.authenticated is True

    def test_wait_for_2fa_raises_on_timeout(self, client_with_mock_driver, mock_driver):
        """wait_for_2fa_completion should raise TwoFactorRequired on timeout."""
        with patch.object(client_with_mock_driver, "_is_logged_in", return_value=False):
            with pytest.raises(TwoFactorRequired) as exc_info:
                client_with_mock_driver.wait_for_2fa_completion(timeout=1)

            assert "1 seconds" in str(exc_info.value)


# =============================================================================
# Unified Authenticate Method Tests
# =============================================================================


class TestUnifiedAuthenticate:
    """Tests for the unified authenticate() method."""

    def test_authenticate_uses_cookie_when_provided(
        self, client_with_mock_driver, mock_driver
    ):
        """authenticate() should use cookie auth when cookie is provided."""
        with patch.object(
            client_with_mock_driver, "authenticate_with_cookie", return_value=True
        ) as mock_cookie_auth:
            result = client_with_mock_driver.authenticate(cookie="test_cookie")

            mock_cookie_auth.assert_called_once_with("test_cookie")
            assert result is True

    def test_authenticate_uses_credentials_when_no_cookie(
        self, client_with_mock_driver, mock_driver
    ):
        """authenticate() should use credential auth when email/password provided."""
        with patch.object(
            client_with_mock_driver, "authenticate_with_credentials", return_value=True
        ) as mock_cred_auth:
            result = client_with_mock_driver.authenticate(
                email="test@example.com", password="password123"
            )

            mock_cred_auth.assert_called_once_with("test@example.com", "password123")
            assert result is True

    def test_authenticate_prefers_cookie_over_credentials(
        self, client_with_mock_driver, mock_driver
    ):
        """authenticate() should prefer cookie auth when both provided."""
        with (
            patch.object(
                client_with_mock_driver, "authenticate_with_cookie", return_value=True
            ) as mock_cookie_auth,
            patch.object(
                client_with_mock_driver, "authenticate_with_credentials"
            ) as mock_cred_auth,
        ):
            client_with_mock_driver.authenticate(
                cookie="test_cookie", email="test@example.com", password="password123"
            )

            mock_cookie_auth.assert_called_once()
            mock_cred_auth.assert_not_called()

    def test_authenticate_raises_config_error_when_no_credentials(
        self, client_with_mock_driver
    ):
        """authenticate() should raise ConfigError when no credentials provided."""
        with pytest.raises(ConfigError) as exc_info:
            client_with_mock_driver.authenticate()

        assert "No authentication credentials" in str(exc_info.value)

    def test_authenticate_raises_config_error_with_only_email(
        self, client_with_mock_driver
    ):
        """authenticate() should raise ConfigError when only email provided."""
        with pytest.raises(ConfigError):
            client_with_mock_driver.authenticate(email="test@example.com")

    def test_authenticate_raises_config_error_with_only_password(
        self, client_with_mock_driver
    ):
        """authenticate() should raise ConfigError when only password provided."""
        with pytest.raises(ConfigError):
            client_with_mock_driver.authenticate(password="password123")

    def test_authenticate_handles_2fa_interactively_by_default(
        self, client_with_mock_driver, mock_driver
    ):
        """authenticate() should handle 2FA interactively by default."""
        with (
            patch.object(
                client_with_mock_driver,
                "authenticate_with_credentials",
                side_effect=TwoFactorRequired(),
            ),
            patch.object(
                client_with_mock_driver, "handle_2fa_challenge", return_value=True
            ) as mock_2fa_handler,
        ):
            result = client_with_mock_driver.authenticate(
                email="test@example.com", password="password123"
            )

            mock_2fa_handler.assert_called_once()
            assert result is True

    def test_authenticate_propagates_2fa_when_handle_2fa_false(
        self, client_with_mock_driver, mock_driver
    ):
        """authenticate() should propagate TwoFactorRequired when handle_2fa=False."""
        with patch.object(
            client_with_mock_driver,
            "authenticate_with_credentials",
            side_effect=TwoFactorRequired(),
        ):
            with pytest.raises(TwoFactorRequired):
                client_with_mock_driver.authenticate(
                    email="test@example.com", password="password123", handle_2fa=False
                )

    def test_authenticate_propagates_cookie_expired(
        self, client_with_mock_driver, mock_driver
    ):
        """authenticate() should propagate CookieExpired error."""
        with patch.object(
            client_with_mock_driver,
            "authenticate_with_cookie",
            side_effect=CookieExpired(),
        ):
            with pytest.raises(CookieExpired):
                client_with_mock_driver.authenticate(cookie="expired_cookie")

    def test_authenticate_propagates_auth_error(
        self, client_with_mock_driver, mock_driver
    ):
        """authenticate() should propagate AuthError."""
        with patch.object(
            client_with_mock_driver,
            "authenticate_with_credentials",
            side_effect=AuthError("Invalid credentials"),
        ):
            with pytest.raises(AuthError):
                client_with_mock_driver.authenticate(
                    email="test@example.com", password="wrong"
                )

    def test_authenticate_takes_screenshot_on_error_when_enabled(
        self, client_with_mock_driver, mock_driver
    ):
        """authenticate() should capture screenshot on auth failure."""
        client_with_mock_driver.screenshot_on_error = True

        with (
            patch.object(
                client_with_mock_driver,
                "authenticate_with_cookie",
                side_effect=AuthError("Test error"),
            ),
            patch.object(
                client_with_mock_driver, "_capture_error_screenshot"
            ) as mock_screenshot,
        ):
            with pytest.raises(AuthError):
                client_with_mock_driver.authenticate(cookie="test")

            mock_screenshot.assert_called()

    def test_authenticate_passes_2fa_timeout(
        self, client_with_mock_driver, mock_driver
    ):
        """authenticate() should pass twofa_timeout to handle_2fa_challenge."""
        with (
            patch.object(
                client_with_mock_driver,
                "authenticate_with_credentials",
                side_effect=TwoFactorRequired(),
            ),
            patch.object(
                client_with_mock_driver, "handle_2fa_challenge", return_value=True
            ) as mock_2fa_handler,
        ):
            client_with_mock_driver.authenticate(
                email="test@example.com", password="password123", twofa_timeout=300
            )

            mock_2fa_handler.assert_called_once_with(300)


class TestUnifiedAuthenticatePropertyBased:
    """Property-based tests for unified authenticate method."""

    @given(cookie=st.text(min_size=10, max_size=100))
    @settings(
        max_examples=15,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_cookie_auth_always_preferred(self, cookie, client, mock_driver):
        """Property: Cookie auth should always be preferred when provided."""
        client.driver = mock_driver

        with (
            patch.object(
                client, "authenticate_with_cookie", return_value=True
            ) as mock_cookie_auth,
            patch.object(client, "authenticate_with_credentials") as mock_cred_auth,
        ):
            client.authenticate(
                cookie=cookie, email="email@test.com", password="password"
            )

            mock_cookie_auth.assert_called_once()
            mock_cred_auth.assert_not_called()

    @given(
        email=st.emails(),
        password=st.text(min_size=1, max_size=50),
    )
    @settings(
        max_examples=15,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_credentials_used_when_no_cookie(
        self, email, password, client, mock_driver
    ):
        """Property: Credentials should be used when no cookie provided."""
        client.driver = mock_driver

        with patch.object(
            client, "authenticate_with_credentials", return_value=True
        ) as mock_cred_auth:
            client.authenticate(email=email, password=password)

            mock_cred_auth.assert_called_once_with(email, password)


# =============================================================================
# Login Error Detection Tests
# =============================================================================


class TestLoginErrorDetection:
    """Tests for _has_login_error method."""

    def test_has_login_error_returns_false_when_no_driver(self, client):
        """_has_login_error should return False when driver is None."""
        assert client.driver is None
        assert client._has_login_error() is False

    def test_has_login_error_detects_error_element(
        self, client_with_mock_driver, mock_driver
    ):
        """_has_login_error should return True when error element found."""
        mock_driver.find_element = MagicMock(return_value=MagicMock())

        result = client_with_mock_driver._has_login_error()

        assert result is True

    def test_has_login_error_returns_false_when_no_error(
        self, client_with_mock_driver, mock_driver
    ):
        """_has_login_error should return False when no error element found."""
        from selenium.common.exceptions import NoSuchElementException

        mock_driver.find_element = MagicMock(side_effect=NoSuchElementException())

        result = client_with_mock_driver._has_login_error()

        assert result is False


# =============================================================================
# Integration Test Scenarios
# =============================================================================


class TestAuthenticationIntegration:
    """Integration-style tests for authentication flows."""

    def test_full_cookie_auth_flow(self, client, mock_driver):
        """Test complete cookie authentication flow."""
        client.driver = mock_driver
        mock_driver.find_element = MagicMock(return_value=MagicMock())

        result = client.authenticate(cookie="valid_session_cookie")

        assert result is True
        assert client.authenticated is True
        mock_driver.add_cookie.assert_called_once()

    def test_full_credential_auth_flow_success(self, client, mock_driver):
        """Test complete credential authentication flow with success."""
        client.driver = mock_driver
        mock_driver.find_element = MagicMock(return_value=MagicMock())

        with (
            patch.object(client, "_is_logged_in", return_value=True),
            patch.object(client, "_is_2fa_challenge", return_value=False),
            patch.object(client, "_has_login_error", return_value=False),
            patch("linkedin_importer.scraper_client.WebDriverWait") as mock_wait,
        ):
            mock_wait.return_value.until.return_value = MagicMock()

            result = client.authenticate(
                email="test@example.com", password="password123"
            )

            assert result is True
            assert client.authenticated is True

    def test_credential_auth_with_2fa_interactive(self, client, mock_driver):
        """Test credential auth with interactive 2FA handling."""
        client.driver = mock_driver
        mock_driver.find_element = MagicMock(return_value=MagicMock())

        with (
            patch.object(
                client,
                "authenticate_with_credentials",
                side_effect=TwoFactorRequired("2FA required"),
            ),
            patch("builtins.input", return_value=""),
            patch.object(client, "_is_logged_in", return_value=True),
        ):
            result = client.authenticate(
                email="test@example.com", password="password123"
            )

            assert result is True
            assert client.authenticated is True

    def test_auth_method_logged_correctly(self, client, mock_driver, caplog):
        """Test that authentication method is logged correctly."""
        import logging

        client.driver = mock_driver

        with (
            patch.object(client, "authenticate_with_cookie", return_value=True),
            caplog.at_level(logging.INFO),
        ):
            client.authenticate(cookie="test_cookie")

        assert "cookie" in caplog.text.lower()

        caplog.clear()

        with (
            patch.object(client, "authenticate_with_credentials", return_value=True),
            caplog.at_level(logging.INFO),
        ):
            client.authenticate(email="test@example.com", password="password")

        assert "email" in caplog.text.lower() or "credential" in caplog.text.lower()
