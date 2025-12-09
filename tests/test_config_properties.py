"""Property-based tests for configuration validation."""

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from linkedin_importer.config import AuthConfig, Config, DatabaseConfig


# Feature: linkedin-profile-importer, Property 8: Invalid configuration detection
# Validates: Requirements 2.4
@given(
    port=st.one_of(
        st.integers(max_value=0),  # Below valid range
        st.integers(min_value=65536),  # Above valid range
    )
)
def test_invalid_port_detection(port: int) -> None:
    """For any port outside valid range (1-65535), validation should fail with specific error."""
    with pytest.raises(ValidationError) as exc_info:
        DatabaseConfig(
            name="testdb",
            user="testuser",
            password="testpass",
            port=port,
        )

    # Verify error message mentions port validation
    error_str = str(exc_info.value)
    assert "port" in error_str.lower()


# Feature: linkedin-profile-importer, Property 8: Invalid configuration detection
# Validates: Requirements 2.4
@given(
    profile_url=st.one_of(
        st.just(""),  # Empty string
        st.from_regex(r"^\s+$", fullmatch=True),  # Whitespace only
    )
)
def test_invalid_profile_url_detection(profile_url: str) -> None:
    """For any empty or whitespace-only profile URL, validation should fail with specific error."""
    with pytest.raises(ValidationError) as exc_info:
        Config(
            database=DatabaseConfig(
                name="testdb",
                user="testuser",
                password="testpass",
            ),
            profile_url=profile_url,
        )

    # Verify error message mentions profile URL
    error_str = str(exc_info.value)
    assert "profile_url" in error_str.lower() or "empty" in error_str.lower()


# Feature: linkedin-profile-importer, Property 8: Invalid configuration detection
# Validates: Requirements 2.4
def test_missing_database_credentials() -> None:
    """When database URL is not provided and credentials are incomplete, validation should fail."""
    with pytest.raises(ValidationError) as exc_info:
        DatabaseConfig(
            name="testdb",
            user="testuser",
            password="",  # Missing password
        )

    # Verify error indicates missing required field
    error_str = str(exc_info.value)
    assert "password" in error_str.lower() or "required" in error_str.lower()


# Feature: linkedin-scraper, Property: Auth config validation
# Validates: Requirements 2.1, 2.2
def test_auth_config_requires_cookie_or_credentials() -> None:
    """AuthConfig should require either cookie or email/password."""
    with pytest.raises(ValidationError) as exc_info:
        AuthConfig()  # No authentication provided

    error_str = str(exc_info.value)
    assert "authentication" in error_str.lower() or "cookie" in error_str.lower()


def test_auth_config_accepts_cookie() -> None:
    """AuthConfig should accept cookie authentication."""
    auth = AuthConfig(cookie="valid_li_at_cookie")
    assert auth.cookie == "valid_li_at_cookie"
    assert auth.method.value == "cookie"


def test_auth_config_accepts_credentials() -> None:
    """AuthConfig should accept email/password authentication."""
    auth = AuthConfig(email="test@example.com", password="testpass")
    assert auth.email == "test@example.com"
    assert auth.password == "testpass"
    assert auth.method.value == "credentials"


def test_auth_config_credentials_requires_both_email_and_password() -> None:
    """AuthConfig with credentials should require both email and password."""
    with pytest.raises(ValidationError):
        AuthConfig(email="test@example.com")  # Missing password

    with pytest.raises(ValidationError):
        AuthConfig(password="testpass")  # Missing email
