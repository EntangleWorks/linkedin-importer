"""Property-based tests for configuration precedence."""

import os
from unittest.mock import patch

from hypothesis import given, settings
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
@settings(deadline=None)
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
        config = _call_load_config(db_name=cli_value)

        # CLI value should be used, not env value
        assert config.database.name == cli_value


# Feature: linkedin-profile-importer, Property 6: Configuration loading precedence
# Validates: Requirements 2.1, 2.2, 3.1, 3.2
@settings(deadline=None)
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
        config = _call_load_config(db_port=cli_port)

        # CLI value should be used, not env value
        assert config.database.port == cli_port


# Feature: linkedin-profile-importer, Property 6: Configuration loading precedence
# Validates: Requirements 2.1, 2.2, 3.1, 3.2
@settings(deadline=None)
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
        config = _call_load_config()

        # Env value should be used as fallback
        assert config.database.name == env_value


# =============================================================================
# NEW: Scraper-specific configuration precedence tests
# =============================================================================


# Feature: linkedin-scraper, Property: CLI args override env vars
# Validates: Requirements 7.3, 7.4
def test_cli_precedence_over_env_linkedin_cookie() -> None:
    """For LinkedIn cookie, CLI value should take precedence over env var."""
    cli_cookie = "cli_cookie_value_from_command_line"
    env_cookie = "env_cookie_value_from_environment"

    with patch.dict(
        os.environ,
        {
            "LINKEDIN_COOKIE": env_cookie,
            "DB_NAME": "testdb",
            "DB_USER": "testuser",
            "DB_PASSWORD": "testpass",
            "PROFILE_EMAIL": "test@example.com",
        },
    ):
        config = _call_load_config(
            linkedin_cookie=cli_cookie,
            profile_email="test@example.com",
        )

        # CLI value should be used, not env value
        assert config.auth is not None
        assert config.auth.cookie == cli_cookie


# Feature: linkedin-scraper, Property: CLI args override env vars
# Validates: Requirements 7.3, 7.4
@settings(deadline=None)
@given(
    cli_email=st.emails(),
    env_email=st.emails(),
)
def test_cli_precedence_over_env_profile_email(cli_email: str, env_email: str) -> None:
    """For profile email, CLI value should take precedence over env var."""
    with patch.dict(
        os.environ,
        {
            "PROFILE_EMAIL": env_email,
            "LINKEDIN_COOKIE": "test_cookie_value",
            "DB_NAME": "testdb",
            "DB_USER": "testuser",
            "DB_PASSWORD": "testpass",
        },
    ):
        config = _call_load_config(
            linkedin_cookie="test_cookie_value",
            profile_email=cli_email,
        )

        # CLI value should be used, not env value
        assert config.profile_email == cli_email


# Feature: linkedin-scraper, Property: CLI args override env vars
# Validates: Requirements 7.3, 7.4
def test_cli_precedence_over_env_action_delay() -> None:
    """For action delay, CLI value (when != default) should take precedence over env var.

    Note: Due to Click's limitation, we can't distinguish between CLI providing
    the default value vs. not providing the value at all. So CLI only takes
    precedence when the value differs from the default (1.0).
    """
    cli_delay = 2.5  # Different from default (1.0)
    env_delay = 0.5

    with patch.dict(
        os.environ,
        {
            "ACTION_DELAY": str(env_delay),
            "DB_NAME": "testdb",
            "DB_USER": "testuser",
            "DB_PASSWORD": "testpass",
        },
    ):
        config = _call_load_config(action_delay=cli_delay)

        # CLI value should be used, not env value
        assert config.scraper.action_delay == cli_delay


# Feature: linkedin-scraper, Property: CLI args override env vars
# Validates: Requirements 7.3, 7.4
def test_cli_headless_overrides_env() -> None:
    """CLI --headless flag should override env var."""
    with patch.dict(
        os.environ,
        {
            "HEADLESS": "false",
            "DB_NAME": "testdb",
            "DB_USER": "testuser",
            "DB_PASSWORD": "testpass",
        },
    ):
        config = _call_load_config(headless=True)

        # CLI value (True) should be used
        assert config.scraper.headless is True


# Feature: linkedin-scraper, Property: CLI args override env vars
# Validates: Requirements 7.3, 7.4
def test_env_headless_used_when_cli_false() -> None:
    """When CLI headless is False (default), env var should be used."""
    with patch.dict(
        os.environ,
        {
            "HEADLESS": "true",
            "DB_NAME": "testdb",
            "DB_USER": "testuser",
            "DB_PASSWORD": "testpass",
        },
    ):
        config = _call_load_config(headless=False)

        # Env value (true) should be used since CLI is False (default)
        assert config.scraper.headless is True


# Feature: linkedin-scraper, Property: CLI args override env vars
# Validates: Requirements 7.3, 7.4
def test_cli_precedence_over_env_max_retries() -> None:
    """For max retries, CLI value (when != default) should take precedence over env var.

    Note: Due to Click's limitation, we can't distinguish between CLI providing
    the default value vs. not providing the value at all. So CLI only takes
    precedence when the value differs from the default (3).
    """
    cli_retries = 5  # Different from default (3)
    env_retries = 1

    with patch.dict(
        os.environ,
        {
            "MAX_RETRIES": str(env_retries),
            "DB_NAME": "testdb",
            "DB_USER": "testuser",
            "DB_PASSWORD": "testpass",
        },
    ):
        config = _call_load_config(max_retries=cli_retries)

        # CLI value should be used, not env value
        assert config.scraper.max_retries == cli_retries


# Feature: linkedin-scraper, Property: Environment variable fallback
# Validates: Requirements 7.1, 7.3
def test_env_fallback_for_linkedin_cookie() -> None:
    """When CLI cookie is not provided, env var should be used."""
    with patch.dict(
        os.environ,
        {
            "LINKEDIN_COOKIE": "env_cookie_value",
            "PROFILE_EMAIL": "test@example.com",
            "DB_NAME": "testdb",
            "DB_USER": "testuser",
            "DB_PASSWORD": "testpass",
        },
    ):
        config = _call_load_config(profile_email="test@example.com")

        # Env value should be used as fallback
        assert config.auth is not None
        assert config.auth.cookie == "env_cookie_value"


# Feature: linkedin-scraper, Property: Environment variable fallback
# Validates: Requirements 7.1, 7.3
def test_env_fallback_for_chromedriver_path() -> None:
    """When CLI chromedriver path is not provided, env var should be used."""
    with patch.dict(
        os.environ,
        {
            "CHROMEDRIVER_PATH": "/usr/local/bin/chromedriver",
            "DB_NAME": "testdb",
            "DB_USER": "testuser",
            "DB_PASSWORD": "testpass",
        },
    ):
        config = _call_load_config()

        # Env value should be used as fallback
        assert config.scraper.chromedriver_path == "/usr/local/bin/chromedriver"


# Feature: linkedin-scraper, Property: Authentication method auto-detection
# Validates: Requirements 7.1, 7.3
def test_cookie_auth_method_auto_detected() -> None:
    """When cookie is provided, auth method should be auto-detected as COOKIE."""
    from linkedin_importer.config import AuthMethod

    with patch.dict(
        os.environ,
        {
            "DB_NAME": "testdb",
            "DB_USER": "testuser",
            "DB_PASSWORD": "testpass",
        },
    ):
        config = _call_load_config(
            linkedin_cookie="test_cookie_value",
            profile_email="test@example.com",
        )

        assert config.auth is not None
        assert config.auth.method == AuthMethod.COOKIE


# Feature: linkedin-scraper, Property: Authentication method auto-detection
# Validates: Requirements 7.1, 7.3
def test_credentials_auth_method_auto_detected() -> None:
    """When email/password is provided, auth method should be auto-detected as CREDENTIALS."""
    from linkedin_importer.config import AuthMethod

    with patch.dict(
        os.environ,
        {
            "DB_NAME": "testdb",
            "DB_USER": "testuser",
            "DB_PASSWORD": "testpass",
        },
    ):
        config = _call_load_config(
            linkedin_email="user@example.com",
            linkedin_password="password123",
            profile_email="test@example.com",
        )

        assert config.auth is not None
        assert config.auth.method == AuthMethod.CREDENTIALS


# Feature: linkedin-scraper, Property: Cookie takes precedence over credentials
# Validates: Requirements 7.1
def test_cookie_takes_precedence_over_credentials() -> None:
    """When both cookie and credentials are provided, cookie should be used."""
    from linkedin_importer.config import AuthMethod

    with patch.dict(
        os.environ,
        {
            "DB_NAME": "testdb",
            "DB_USER": "testuser",
            "DB_PASSWORD": "testpass",
        },
    ):
        config = _call_load_config(
            linkedin_cookie="test_cookie_value",
            linkedin_email="user@example.com",
            linkedin_password="password123",
            profile_email="test@example.com",
        )

        assert config.auth is not None
        assert config.auth.method == AuthMethod.COOKIE
        assert config.auth.cookie == "test_cookie_value"


# Feature: linkedin-scraper, Property: No auth config when no credentials
# Validates: Requirements 7.1
def test_no_auth_config_when_no_credentials() -> None:
    """When no auth credentials are provided, auth config should be None."""
    with patch.dict(
        os.environ,
        {
            "DB_NAME": "testdb",
            "DB_USER": "testuser",
            "DB_PASSWORD": "testpass",
        },
    ):
        config = _call_load_config()

        # No auth credentials provided, so auth should be None
        assert config.auth is None


# Feature: linkedin-scraper, Property: Screenshot on error flag
# Validates: Requirements 7.3
def test_screenshot_on_error_flag() -> None:
    """Screenshot on error CLI flag should work correctly."""
    with patch.dict(
        os.environ,
        {
            "DB_NAME": "testdb",
            "DB_USER": "testuser",
            "DB_PASSWORD": "testpass",
        },
    ):
        config = _call_load_config(screenshot_on_error=True)

        assert config.scraper.screenshot_on_error is True


# Feature: linkedin-scraper, Property: Screenshot on error env fallback
# Validates: Requirements 7.3
def test_screenshot_on_error_env_fallback() -> None:
    """Screenshot on error env var should work as fallback."""
    with patch.dict(
        os.environ,
        {
            "SCREENSHOT_ON_ERROR": "true",
            "DB_NAME": "testdb",
            "DB_USER": "testuser",
            "DB_PASSWORD": "testpass",
        },
    ):
        config = _call_load_config()

        assert config.scraper.screenshot_on_error is True
