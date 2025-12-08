"""Property-based tests for configuration precedence.

Note: Tests for api_key and api_secret are marked as skipped because the
API-based approach has been deprecated in favor of web scraping.
"""

import os
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


# Strategy for generating valid environment variable values
# Excludes null bytes and surrogate characters that can't be encoded
valid_text = st.text(
    min_size=1,
    max_size=50,
    alphabet=st.characters(
        blacklist_characters="\x00",
        blacklist_categories=("Cs",),  # Exclude surrogate characters
    ),
).filter(lambda x: x.strip() != "")


# Feature: linkedin-profile-importer, Property 6: Configuration loading precedence
# Validates: Requirements 2.1, 2.2, 3.1, 3.2
@given(
    cli_value=valid_text,
    env_value=valid_text,
)
def test_cli_precedence_over_env_db_name(cli_value: str, env_value: str) -> None:
    """For any database name provided via CLI and env, CLI value should take precedence."""
    with patch.dict(
        os.environ,
        {
            "DB_NAME": env_value,
            "DB_USER": "testuser",
            "DB_PASSWORD": "testpass",
        },
    ):
        config = load_config(
            profile_url="https://linkedin.com/in/test",
            db_url=None,
            db_host=None,
            db_port=None,
            db_name=cli_value,  # CLI value provided
            db_user=None,
            db_password=None,
            linkedin_api_key=None,
            linkedin_api_secret=None,
            verbose=False,
        )

        # CLI value should be used, not env value
        assert config.database.name == cli_value


# Feature: linkedin-profile-importer, Property 6: Configuration loading precedence
# Validates: Requirements 2.1, 2.2, 3.1, 3.2
@pytest.mark.skip(reason=DEPRECATED_API_REASON)
@given(
    cli_value=valid_text,
    env_value=valid_text,
)
def test_cli_precedence_over_env_api_key(cli_value: str, env_value: str) -> None:
    """For any API key provided via CLI and env, CLI value should take precedence."""
    with patch.dict(
        os.environ,
        {
            "LINKEDIN_API_KEY": env_value,
            "LINKEDIN_API_SECRET": "test_secret",
            "DB_NAME": "testdb",
            "DB_USER": "testuser",
            "DB_PASSWORD": "testpass",
        },
    ):
        config = load_config(
            profile_url="https://linkedin.com/in/test",
            db_url=None,
            db_host=None,
            db_port=None,
            db_name=None,
            db_user=None,
            db_password=None,
            linkedin_api_key=cli_value,  # CLI value provided
            linkedin_api_secret=None,
            verbose=False,
        )

        # CLI value should be used (after stripping), not env value
        assert config.linkedin.api_key == cli_value.strip()


# Feature: linkedin-profile-importer, Property 6: Configuration loading precedence
# Validates: Requirements 2.1, 2.2, 3.1, 3.2
@given(
    cli_port=st.integers(min_value=1, max_value=65535),
    env_port=st.integers(min_value=1, max_value=65535),
)
def test_cli_precedence_over_env_port(cli_port: int, env_port: int) -> None:
    """For any port provided via CLI and env, CLI value should take precedence."""
    with patch.dict(
        os.environ,
        {
            "DB_PORT": str(env_port),
            "DB_NAME": "testdb",
            "DB_USER": "testuser",
            "DB_PASSWORD": "testpass",
        },
    ):
        config = load_config(
            profile_url="https://linkedin.com/in/test",
            db_url=None,
            db_host=None,
            db_port=cli_port,  # CLI value provided
            db_name=None,
            db_user=None,
            db_password=None,
            linkedin_api_key=None,
            linkedin_api_secret=None,
            verbose=False,
        )

        # CLI value should be used, not env value
        assert config.database.port == cli_port


# Feature: linkedin-profile-importer, Property 6: Configuration loading precedence
# Validates: Requirements 2.1, 2.2, 3.1, 3.2
@given(
    env_value=valid_text,
)
def test_env_fallback_when_cli_not_provided(env_value: str) -> None:
    """For any config parameter, when CLI arg is not provided, env var should be used."""
    with patch.dict(
        os.environ,
        {
            "DB_NAME": env_value,
            "DB_USER": "testuser",
            "DB_PASSWORD": "testpass",
        },
    ):
        config = load_config(
            profile_url="https://linkedin.com/in/test",
            db_url=None,
            db_host=None,
            db_port=None,
            db_name=None,  # CLI value NOT provided
            db_user=None,
            db_password=None,
            linkedin_api_key=None,
            linkedin_api_secret=None,
            verbose=False,
        )

        # Env value should be used as fallback
        assert config.database.name == env_value
