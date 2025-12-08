"""Property-based tests for scraper configuration models.

These tests validate:
- AuthConfig validation and auto-detection of authentication method
- ScraperConfig value ranges and validation
- Configuration error messages are helpful
"""

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from linkedin_importer.config import (
    AuthConfig,
    AuthMethod,
    ScraperConfig,
)


class TestAuthConfigProperties:
    """Property tests for AuthConfig validation."""

    def test_cookie_method_requires_cookie(self):
        """Cookie auth method requires a cookie to be set."""
        with pytest.raises(ValueError) as exc_info:
            AuthConfig(method=AuthMethod.COOKIE, cookie=None)
        assert "LINKEDIN_COOKIE" in str(exc_info.value)

    def test_cookie_method_with_valid_cookie_succeeds(self):
        """Cookie auth method succeeds when cookie is provided."""
        config = AuthConfig(method=AuthMethod.COOKIE, cookie="valid_cookie_value")
        assert config.method == AuthMethod.COOKIE
        assert config.cookie == "valid_cookie_value"

    def test_credentials_method_requires_email(self):
        """Credentials auth method requires email to be set."""
        with pytest.raises(ValueError) as exc_info:
            AuthConfig(
                method=AuthMethod.CREDENTIALS,
                email=None,
                password="password123",
            )
        assert "LINKEDIN_EMAIL" in str(exc_info.value)

    def test_credentials_method_requires_password(self):
        """Credentials auth method requires password to be set."""
        with pytest.raises(ValueError) as exc_info:
            AuthConfig(
                method=AuthMethod.CREDENTIALS,
                email="user@example.com",
                password=None,
            )
        assert "LINKEDIN_PASSWORD" in str(exc_info.value)

    def test_credentials_method_with_valid_credentials_succeeds(self):
        """Credentials auth method succeeds when both email and password provided."""
        config = AuthConfig(
            method=AuthMethod.CREDENTIALS,
            email="user@example.com",
            password="password123",
        )
        assert config.method == AuthMethod.CREDENTIALS
        assert config.email == "user@example.com"
        assert config.password == "password123"

    def test_auto_detect_cookie_method(self):
        """Method is auto-detected as COOKIE when cookie is provided."""
        config = AuthConfig(cookie="auto_detected_cookie")
        assert config.method == AuthMethod.COOKIE
        assert config.cookie == "auto_detected_cookie"

    def test_auto_detect_credentials_method(self):
        """Method is auto-detected as CREDENTIALS when email/password provided."""
        config = AuthConfig(
            email="user@example.com",
            password="password123",
        )
        assert config.method == AuthMethod.CREDENTIALS

    def test_auto_detect_cookie_takes_priority(self):
        """Cookie method takes priority when both cookie and credentials provided."""
        config = AuthConfig(
            cookie="cookie_value",
            email="user@example.com",
            password="password123",
        )
        assert config.method == AuthMethod.COOKIE

    def test_no_credentials_raises_error(self):
        """Error is raised when no authentication credentials are provided."""
        with pytest.raises(ValueError) as exc_info:
            AuthConfig()
        error_msg = str(exc_info.value)
        assert "LINKEDIN_COOKIE" in error_msg or "authentication" in error_msg.lower()

    def test_empty_cookie_treated_as_none(self):
        """Empty or whitespace-only cookie is treated as None."""
        with pytest.raises(ValueError):
            AuthConfig(cookie="   ")

    def test_invalid_email_format_rejected(self):
        """Invalid email format is rejected."""
        with pytest.raises(ValueError) as exc_info:
            AuthConfig(
                method=AuthMethod.CREDENTIALS,
                email="not_an_email",
                password="password123",
            )
        assert "email" in str(exc_info.value).lower()

    @given(st.text(min_size=1).filter(lambda x: x.strip()))
    def test_any_non_empty_cookie_is_valid(self, cookie: str):
        """Any non-empty, non-whitespace string is a valid cookie."""
        assume(cookie.strip())  # Ensure it's not just whitespace
        config = AuthConfig(cookie=cookie)
        assert config.method == AuthMethod.COOKIE
        assert config.cookie == cookie.strip()

    @given(
        email=st.emails(),
        password=st.text(min_size=1).filter(lambda x: x.strip()),
    )
    def test_valid_email_and_password_accepted(self, email: str, password: str):
        """Valid email and password combinations are accepted."""
        assume(password.strip())
        config = AuthConfig(email=email, password=password)
        assert config.method == AuthMethod.CREDENTIALS
        assert config.email == email
        assert config.password == password


class TestScraperConfigProperties:
    """Property tests for ScraperConfig validation."""

    def test_default_config_is_valid(self):
        """Default ScraperConfig is valid."""
        config = ScraperConfig()
        assert config.headless is True
        assert config.page_load_timeout == 30
        assert config.action_delay == 1.0
        assert config.scroll_delay == 0.5
        assert config.max_retries == 3
        assert config.screenshot_on_error is False
        assert config.chromedriver_path is None
        assert config.user_agent is None

    @given(st.integers(min_value=5, max_value=120))
    def test_valid_timeout_range(self, timeout: int):
        """Timeout values between 5 and 120 are valid."""
        config = ScraperConfig(page_load_timeout=timeout)
        assert config.page_load_timeout == timeout

    @given(st.integers(max_value=4))
    def test_timeout_too_low_rejected(self, timeout: int):
        """Timeout values below 5 are rejected."""
        with pytest.raises(ValueError):
            ScraperConfig(page_load_timeout=timeout)

    @given(st.integers(min_value=121))
    def test_timeout_too_high_rejected(self, timeout: int):
        """Timeout values above 120 are rejected."""
        with pytest.raises(ValueError):
            ScraperConfig(page_load_timeout=timeout)

    @given(st.floats(min_value=0.5, max_value=10.0))
    def test_valid_action_delay_range(self, delay: float):
        """Action delay values between 0.5 and 10.0 are valid."""
        config = ScraperConfig(action_delay=delay)
        assert config.action_delay == delay

    @given(st.floats(max_value=0.49, allow_nan=False, allow_infinity=False))
    def test_action_delay_too_low_rejected(self, delay: float):
        """Action delay values below 0.5 are rejected."""
        with pytest.raises(ValueError):
            ScraperConfig(action_delay=delay)

    @given(
        st.floats(min_value=10.1, allow_nan=False, allow_infinity=False, max_value=100)
    )
    def test_action_delay_too_high_rejected(self, delay: float):
        """Action delay values above 10.0 are rejected."""
        with pytest.raises(ValueError):
            ScraperConfig(action_delay=delay)

    @given(st.floats(min_value=0.1, max_value=5.0))
    def test_valid_scroll_delay_range(self, delay: float):
        """Scroll delay values between 0.1 and 5.0 are valid."""
        config = ScraperConfig(scroll_delay=delay)
        assert config.scroll_delay == delay

    @given(st.integers(min_value=1, max_value=10))
    def test_valid_max_retries_range(self, retries: int):
        """Max retries values between 1 and 10 are valid."""
        config = ScraperConfig(max_retries=retries)
        assert config.max_retries == retries

    @given(st.integers(max_value=0))
    def test_max_retries_too_low_rejected(self, retries: int):
        """Max retries values below 1 are rejected."""
        with pytest.raises(ValueError):
            ScraperConfig(max_retries=retries)

    @given(st.integers(min_value=11))
    def test_max_retries_too_high_rejected(self, retries: int):
        """Max retries values above 10 are rejected."""
        with pytest.raises(ValueError):
            ScraperConfig(max_retries=retries)

    @given(st.booleans())
    def test_headless_accepts_any_bool(self, headless: bool):
        """Headless mode accepts any boolean value."""
        config = ScraperConfig(headless=headless)
        assert config.headless == headless

    @given(st.booleans())
    def test_screenshot_on_error_accepts_any_bool(self, screenshot: bool):
        """Screenshot on error accepts any boolean value."""
        config = ScraperConfig(screenshot_on_error=screenshot)
        assert config.screenshot_on_error == screenshot

    @given(st.text())
    def test_chromedriver_path_accepts_any_string(self, path: str):
        """ChromeDriver path accepts any string."""
        config = ScraperConfig(chromedriver_path=path)
        assert config.chromedriver_path == path

    @given(st.text())
    def test_user_agent_accepts_any_string(self, ua: str):
        """User agent accepts any string."""
        config = ScraperConfig(user_agent=ua)
        assert config.user_agent == ua


class TestAuthMethodEnum:
    """Tests for AuthMethod enum values."""

    def test_cookie_value(self):
        """COOKIE enum has correct string value."""
        assert AuthMethod.COOKIE.value == "cookie"

    def test_credentials_value(self):
        """CREDENTIALS enum has correct string value."""
        assert AuthMethod.CREDENTIALS.value == "credentials"

    def test_enum_from_string(self):
        """AuthMethod can be constructed from string values."""
        assert AuthMethod("cookie") == AuthMethod.COOKIE
        assert AuthMethod("credentials") == AuthMethod.CREDENTIALS

    def test_invalid_method_rejected(self):
        """Invalid method string raises ValueError."""
        with pytest.raises(ValueError):
            AuthMethod("invalid_method")
