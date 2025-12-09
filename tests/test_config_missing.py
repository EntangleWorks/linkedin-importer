"""Property-based tests for missing configuration detection."""

import os
from unittest.mock import patch

import pytest
from hypothesis import given
from hypothesis import strategies as st

from linkedin_importer.cli import load_config


def _call_load_config(**kwargs):
    """Helper to call load_config with default values for all parameters."""
    defaults = {
        "profile_url": "https://linkedin.com/in/test",
        "db_url": None,
        "db_host": None,
        "db_port": None,
        "db_name": None,
        "db_user": None,
        "db_password": None,
        "linkedin_cookie": None,
        "linkedin_email": None,
        "linkedin_password": None,
        "profile_email": None,
        "headless": False,
        "chromedriver_path": None,
        "action_delay": 1.0,
        "scroll_delay": 0.5,
        "page_load_timeout": 30,
        "max_retries": 3,
        "screenshot_on_error": False,
        "verbose": False,
    }
    defaults.update(kwargs)
    return load_config(**defaults)


# Feature: linkedin-profile-importer, Property 7: Missing configuration detection
# Validates: Requirements 2.3
def test_missing_database_name() -> None:
    """When database name is missing from both CLI and env, should fail with error."""
    with patch.dict(
        os.environ,
        {
            "DB_USER": "testuser",
            "DB_PASSWORD": "testpass",
            # DB_NAME is missing
        },
        clear=True,
    ):
        with pytest.raises(SystemExit) as exc_info:
            _call_load_config()

        # Should exit with error code
        assert exc_info.value.code == 1


# Feature: linkedin-profile-importer, Property 7: Missing configuration detection
# Validates: Requirements 2.3
def test_missing_database_user() -> None:
    """When database user is missing from both CLI and env, should fail with error."""
    with patch.dict(
        os.environ,
        {
            "DB_NAME": "testdb",
            "DB_PASSWORD": "testpass",
            # DB_USER is missing
        },
        clear=True,
    ):
        with pytest.raises(SystemExit) as exc_info:
            _call_load_config()

        # Should exit with error code
        assert exc_info.value.code == 1


# Feature: linkedin-profile-importer, Property 7: Missing configuration detection
# Validates: Requirements 2.3
def test_missing_database_password() -> None:
    """When database password is missing from both CLI and env, should fail with error."""
    with patch.dict(
        os.environ,
        {
            "DB_NAME": "testdb",
            "DB_USER": "testuser",
            # DB_PASSWORD is missing
        },
        clear=True,
    ):
        with pytest.raises(SystemExit) as exc_info:
            _call_load_config()

        # Should exit with error code
        assert exc_info.value.code == 1


# Feature: linkedin-profile-importer, Property 7: Missing configuration detection
# Validates: Requirements 2.3
@given(
    missing_param=st.sampled_from(
        [
            "db_name",
            "db_user",
            "db_password",
        ]
    )
)
def test_any_missing_required_param_causes_failure(missing_param: str) -> None:
    """For any required configuration parameter, when missing, the tool should fail with exit code 1."""
    # Set up base environment with all required params
    env = {
        "DB_NAME": "testdb",
        "DB_USER": "testuser",
        "DB_PASSWORD": "testpass",
    }

    # Remove the parameter we're testing
    param_to_env_map = {
        "db_name": "DB_NAME",
        "db_user": "DB_USER",
        "db_password": "DB_PASSWORD",
    }

    del env[param_to_env_map[missing_param]]

    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(SystemExit) as exc_info:
            _call_load_config()

        # Should exit with error code
        assert exc_info.value.code == 1


# Feature: linkedin-scraper, Test: Config with cookie auth succeeds
def test_config_with_cookie_auth_succeeds() -> None:
    """Config should succeed when cookie authentication is provided."""
    with patch.dict(
        os.environ,
        {
            "DB_NAME": "testdb",
            "DB_USER": "testuser",
            "DB_PASSWORD": "testpass",
            "LINKEDIN_COOKIE": "valid_li_at_cookie",
            "PROFILE_EMAIL": "test@example.com",
        },
        clear=True,
    ):
        config = _call_load_config()
        assert config.auth is not None
        assert config.auth.cookie == "valid_li_at_cookie"
        assert config.profile_email == "test@example.com"


# Feature: linkedin-scraper, Test: Config with email/password auth succeeds
def test_config_with_credentials_auth_succeeds() -> None:
    """Config should succeed when email/password authentication is provided."""
    with patch.dict(
        os.environ,
        {
            "DB_NAME": "testdb",
            "DB_USER": "testuser",
            "DB_PASSWORD": "testpass",
            "LINKEDIN_EMAIL": "user@example.com",
            "LINKEDIN_PASSWORD": "linkedinpass",
            "PROFILE_EMAIL": "test@example.com",
        },
        clear=True,
    ):
        config = _call_load_config()
        assert config.auth is not None
        assert config.auth.email == "user@example.com"
        assert config.auth.password == "linkedinpass"
