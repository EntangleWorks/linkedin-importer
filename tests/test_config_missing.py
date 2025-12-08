"""Property-based tests for missing configuration detection.

Note: Tests for api_key and api_secret are marked as skipped because the
API-based approach has been deprecated in favor of web scraping.
"""

import os
from io import StringIO
from unittest.mock import patch

import pytest
from hypothesis import given
from hypothesis import strategies as st

from linkedin_importer.cli import load_config

# Skip reason for deprecated API tests
DEPRECATED_API_REASON = (
    "LinkedIn API configuration (api_key/api_secret) is deprecated. "
    "The scraper now uses cookie-based or credentials-based authentication."
)


# Feature: linkedin-profile-importer, Property 7: Missing configuration detection
# Validates: Requirements 2.3
@pytest.mark.skip(reason=DEPRECATED_API_REASON)
def test_missing_api_key() -> None:
    """When API key is missing from both CLI and env, should fail with error naming the parameter."""
    with patch.dict(
        os.environ,
        {
            "DB_NAME": "testdb",
            "DB_USER": "testuser",
            "DB_PASSWORD": "testpass",
            "LINKEDIN_API_SECRET": "test_secret",
            # LINKEDIN_API_KEY is missing
        },
        clear=True,
    ):
        with pytest.raises(SystemExit) as exc_info:
            # Capture stderr to check error message
            with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                load_config(
                    profile_url="https://linkedin.com/in/test",
                    db_url=None,
                    db_host=None,
                    db_port=None,
                    db_name=None,
                    db_user=None,
                    db_password=None,
                    linkedin_api_key=None,  # Not provided via CLI
                    linkedin_api_secret=None,
                    verbose=False,
                )

        # Should exit with error code
        assert exc_info.value.code == 1


# Feature: linkedin-profile-importer, Property 7: Missing configuration detection
# Validates: Requirements 2.3
@pytest.mark.skip(reason=DEPRECATED_API_REASON)
def test_missing_api_secret() -> None:
    """When API secret is missing from both CLI and env, should fail with error naming the parameter."""
    with patch.dict(
        os.environ,
        {
            "DB_NAME": "testdb",
            "DB_USER": "testuser",
            "DB_PASSWORD": "testpass",
            "LINKEDIN_API_KEY": "test_key",
            # LINKEDIN_API_SECRET is missing
        },
        clear=True,
    ):
        with pytest.raises(SystemExit) as exc_info:
            load_config(
                profile_url="https://linkedin.com/in/test",
                db_url=None,
                db_host=None,
                db_port=None,
                db_name=None,
                db_user=None,
                db_password=None,
                linkedin_api_key=None,
                linkedin_api_secret=None,  # Not provided via CLI
                verbose=False,
            )

        # Should exit with error code
        assert exc_info.value.code == 1


# Feature: linkedin-profile-importer, Property 7: Missing configuration detection
# Validates: Requirements 2.3
def test_missing_database_name() -> None:
    """When database name is missing from both CLI and env, should fail with error naming the parameter."""
    with patch.dict(
        os.environ,
        {
            "DB_USER": "testuser",
            "DB_PASSWORD": "testpass",
            "LINKEDIN_API_KEY": "test_key",
            "LINKEDIN_API_SECRET": "test_secret",
            # DB_NAME is missing
        },
        clear=True,
    ):
        with pytest.raises(SystemExit) as exc_info:
            load_config(
                profile_url="https://linkedin.com/in/test",
                db_url=None,
                db_host=None,
                db_port=None,
                db_name=None,  # Not provided via CLI
                db_user=None,
                db_password=None,
                linkedin_api_key=None,
                linkedin_api_secret=None,
                verbose=False,
            )

        # Should exit with error code
        assert exc_info.value.code == 1


# Feature: linkedin-profile-importer, Property 7: Missing configuration detection
# Validates: Requirements 2.3
def test_missing_database_user() -> None:
    """When database user is missing from both CLI and env, should fail with error naming the parameter."""
    with patch.dict(
        os.environ,
        {
            "DB_NAME": "testdb",
            "DB_PASSWORD": "testpass",
            "LINKEDIN_API_KEY": "test_key",
            "LINKEDIN_API_SECRET": "test_secret",
            # DB_USER is missing
        },
        clear=True,
    ):
        with pytest.raises(SystemExit) as exc_info:
            load_config(
                profile_url="https://linkedin.com/in/test",
                db_url=None,
                db_host=None,
                db_port=None,
                db_name=None,
                db_user=None,  # Not provided via CLI
                db_password=None,
                linkedin_api_key=None,
                linkedin_api_secret=None,
                verbose=False,
            )

        # Should exit with error code
        assert exc_info.value.code == 1


# Feature: linkedin-profile-importer, Property 7: Missing configuration detection
# Validates: Requirements 2.3
def test_missing_database_password() -> None:
    """When database password is missing from both CLI and env, should fail with error naming the parameter."""
    with patch.dict(
        os.environ,
        {
            "DB_NAME": "testdb",
            "DB_USER": "testuser",
            "LINKEDIN_API_KEY": "test_key",
            "LINKEDIN_API_SECRET": "test_secret",
            # DB_PASSWORD is missing
        },
        clear=True,
    ):
        with pytest.raises(SystemExit) as exc_info:
            load_config(
                profile_url="https://linkedin.com/in/test",
                db_url=None,
                db_host=None,
                db_port=None,
                db_name=None,
                db_user=None,
                db_password=None,  # Not provided via CLI
                linkedin_api_key=None,
                linkedin_api_secret=None,
                verbose=False,
            )

        # Should exit with error code
        assert exc_info.value.code == 1


# Feature: linkedin-profile-importer, Property 7: Missing configuration detection
# Validates: Requirements 2.3
@given(
    missing_param=st.sampled_from(
        [
            # api_key and api_secret removed - deprecated API approach
            "db_name",
            "db_user",
            "db_password",
        ]
    )
)
def test_any_missing_required_param_causes_failure(missing_param: str) -> None:
    """For any required configuration parameter, when missing, the tool should fail with exit code 1."""
    # Set up base environment with all required params
    # Note: LINKEDIN_API_KEY and LINKEDIN_API_SECRET are deprecated
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
            load_config(
                profile_url="https://linkedin.com/in/test",
                db_url=None,
                db_host=None,
                db_port=None,
                db_name=None,
                db_user=None,
                db_password=None,
                linkedin_api_key=None,
                linkedin_api_secret=None,
                verbose=False,
            )

        # Should exit with error code
        assert exc_info.value.code == 1
