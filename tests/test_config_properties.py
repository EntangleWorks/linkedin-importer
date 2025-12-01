"""Property-based tests for configuration validation."""

import pytest
from hypothesis import given, strategies as st
from pydantic import ValidationError

from linkedin_importer.config import DatabaseConfig, LinkedInConfig, Config


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
    api_key=st.one_of(
        st.just(""),  # Empty string
        st.from_regex(r"^\s+$", fullmatch=True),  # Whitespace only
    )
)
def test_invalid_api_key_detection(api_key: str) -> None:
    """For any empty or whitespace-only API key, validation should fail with specific error."""
    with pytest.raises(ValidationError) as exc_info:
        LinkedInConfig(
            api_key=api_key,
            api_secret="valid_secret",
        )
    
    # Verify error message mentions the field
    error_str = str(exc_info.value)
    assert "api_key" in error_str.lower() or "empty" in error_str.lower()


# Feature: linkedin-profile-importer, Property 8: Invalid configuration detection
# Validates: Requirements 2.4
@given(
    api_secret=st.one_of(
        st.just(""),  # Empty string
        st.from_regex(r"^\s+$", fullmatch=True),  # Whitespace only
    )
)
def test_invalid_api_secret_detection(api_secret: str) -> None:
    """For any empty or whitespace-only API secret, validation should fail with specific error."""
    with pytest.raises(ValidationError) as exc_info:
        LinkedInConfig(
            api_key="valid_key",
            api_secret=api_secret,
        )
    
    # Verify error message mentions the field
    error_str = str(exc_info.value)
    assert "api_secret" in error_str.lower() or "empty" in error_str.lower()


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
            linkedin=LinkedInConfig(
                api_key="valid_key",
                api_secret="valid_secret",
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
