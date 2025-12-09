"""CLI entry point for LinkedIn Profile Importer."""

import asyncio
import os
import sys

import click
from dotenv import load_dotenv
from pydantic import ValidationError

from linkedin_importer.config import (
    AuthConfig,
    AuthMethod,
    Config,
    DatabaseConfig,
    LinkedInConfig,
    ScraperConfig,
)
from linkedin_importer.logging_config import get_logger, setup_logging
from linkedin_importer.orchestrator import import_profile


def load_config(
    profile_url: str,
    # Database options
    db_url: str | None,
    db_host: str | None,
    db_port: int | None,
    db_name: str | None,
    db_user: str | None,
    db_password: str | None,
    # Legacy LinkedIn API options (deprecated)
    linkedin_api_key: str | None,
    linkedin_api_secret: str | None,
    # New scraper authentication options
    linkedin_cookie: str | None,
    linkedin_email: str | None,
    linkedin_password: str | None,
    profile_email: str | None,
    # Browser configuration options
    headless: bool,
    chromedriver_path: str | None,
    action_delay: float,
    scroll_delay: float,
    page_load_timeout: int,
    max_retries: int,
    screenshot_on_error: bool,
    # General options
    verbose: bool,
) -> Config:
    """Load configuration from CLI arguments and environment variables.

    CLI arguments take precedence over environment variables.

    Args:
        profile_url: LinkedIn profile URL or username
        db_url: Database connection URL
        db_host: Database host
        db_port: Database port
        db_name: Database name
        db_user: Database user
        db_password: Database password
        linkedin_api_key: LinkedIn API key (deprecated)
        linkedin_api_secret: LinkedIn API secret (deprecated)
        linkedin_cookie: LinkedIn li_at session cookie (preferred auth)
        linkedin_email: LinkedIn email (fallback auth)
        linkedin_password: LinkedIn password (fallback auth)
        profile_email: Email for the imported profile
        headless: Run browser in headless mode
        chromedriver_path: Path to chromedriver executable
        action_delay: Delay between actions in seconds
        scroll_delay: Delay between scroll actions in seconds
        page_load_timeout: Maximum page load timeout in seconds
        max_retries: Maximum retry attempts
        screenshot_on_error: Capture screenshot on errors
        verbose: Enable verbose logging

    Returns:
        Validated Config object

    Raises:
        SystemExit: If configuration validation fails
    """
    # Load environment variables from .env file if it exists
    load_dotenv()

    # Database configuration with CLI args taking precedence over env vars
    db_config_dict = {
        "url": db_url or os.getenv("DATABASE_URL"),
        "host": db_host or os.getenv("DB_HOST", "localhost"),
        "port": db_port or int(os.getenv("DB_PORT", "5432")),
        "name": db_name or os.getenv("DB_NAME", ""),
        "user": db_user or os.getenv("DB_USER", ""),
        "password": db_password or os.getenv("DB_PASSWORD", ""),
    }

    # Legacy LinkedIn configuration (deprecated, kept for backward compatibility)
    linkedin_config_dict = {
        "api_key": linkedin_api_key or os.getenv("LINKEDIN_API_KEY", ""),
        "api_secret": linkedin_api_secret or os.getenv("LINKEDIN_API_SECRET", ""),
        "access_token": os.getenv("LINKEDIN_ACCESS_TOKEN"),
    }

    # New scraper authentication configuration
    # CLI args take precedence over environment variables
    auth_cookie = linkedin_cookie or os.getenv("LINKEDIN_COOKIE")
    auth_email = linkedin_email or os.getenv("LINKEDIN_EMAIL")
    auth_password = linkedin_password or os.getenv("LINKEDIN_PASSWORD")

    # Profile email for the imported profile
    resolved_profile_email = profile_email or os.getenv("PROFILE_EMAIL")

    # Browser/scraper configuration
    # For headless, check env var if CLI didn't explicitly set it
    # CLI flag is a boolean that defaults to False (--no-headless is default)
    env_headless = os.getenv("HEADLESS", "").lower() in ("true", "1", "yes")
    resolved_headless = headless or env_headless

    resolved_chromedriver_path = chromedriver_path or os.getenv("CHROMEDRIVER_PATH")

    # Delay values from env if not provided via CLI
    env_action_delay = float(os.getenv("ACTION_DELAY", "1.0"))
    resolved_action_delay = action_delay if action_delay != 1.0 else env_action_delay

    env_scroll_delay = float(os.getenv("SCROLL_DELAY", "0.5"))
    resolved_scroll_delay = scroll_delay if scroll_delay != 0.5 else env_scroll_delay

    env_page_load_timeout = int(os.getenv("PAGE_LOAD_TIMEOUT", "30"))
    resolved_page_load_timeout = (
        page_load_timeout if page_load_timeout != 30 else env_page_load_timeout
    )

    env_max_retries = int(os.getenv("MAX_RETRIES", "3"))
    resolved_max_retries = max_retries if max_retries != 3 else env_max_retries

    env_screenshot_on_error = os.getenv("SCREENSHOT_ON_ERROR", "").lower() in (
        "true",
        "1",
        "yes",
    )
    resolved_screenshot_on_error = screenshot_on_error or env_screenshot_on_error

    try:
        database_config = DatabaseConfig(**db_config_dict)
        linkedin_config = LinkedInConfig(**linkedin_config_dict)

        # Build auth config if any auth credentials are provided
        auth_config = None
        if auth_cookie or (auth_email and auth_password):
            auth_config_dict = {
                "cookie": auth_cookie,
                "email": auth_email,
                "password": auth_password,
            }
            auth_config = AuthConfig(**auth_config_dict)

        # Build scraper config
        scraper_config = ScraperConfig(
            headless=resolved_headless,
            chromedriver_path=resolved_chromedriver_path,
            action_delay=resolved_action_delay,
            scroll_delay=resolved_scroll_delay,
            page_load_timeout=resolved_page_load_timeout,
            max_retries=resolved_max_retries,
            screenshot_on_error=resolved_screenshot_on_error,
        )

        config = Config(
            database=database_config,
            linkedin=linkedin_config,
            auth=auth_config,
            scraper=scraper_config,
            profile_url=profile_url,
            profile_email=resolved_profile_email,
            verbose=verbose,
        )

        return config
    except ValidationError as e:
        click.echo(f"Configuration error: {e}", err=True)
        sys.exit(1)


@click.command()
@click.argument("profile_url")
# Database options (existing)
@click.option("--db-url", envvar="DATABASE_URL", help="Database connection URL")
@click.option("--db-host", envvar="DB_HOST", help="Database host")
@click.option("--db-port", envvar="DB_PORT", type=int, help="Database port")
@click.option("--db-name", envvar="DB_NAME", help="Database name")
@click.option("--db-user", envvar="DB_USER", help="Database user")
@click.option("--db-password", envvar="DB_PASSWORD", help="Database password")
# Legacy LinkedIn API options (deprecated)
@click.option(
    "--linkedin-api-key",
    envvar="LINKEDIN_API_KEY",
    help="LinkedIn API key (deprecated)",
)
@click.option(
    "--linkedin-api-secret",
    envvar="LINKEDIN_API_SECRET",
    help="LinkedIn API secret (deprecated)",
)
# Authentication options (NEW)
@click.option(
    "--linkedin-cookie",
    envvar="LINKEDIN_COOKIE",
    help="LinkedIn li_at session cookie (preferred auth method, bypasses 2FA)",
)
@click.option(
    "--linkedin-email",
    envvar="LINKEDIN_EMAIL",
    help="LinkedIn email (fallback auth, may trigger 2FA)",
)
@click.option(
    "--linkedin-password",
    envvar="LINKEDIN_PASSWORD",
    help="LinkedIn password (fallback auth)",
)
@click.option(
    "--profile-email",
    envvar="PROFILE_EMAIL",
    help="Email address for the imported profile (LinkedIn doesn't expose emails)",
)
# Browser configuration options (NEW)
@click.option(
    "--headless/--no-headless",
    default=False,
    help="Run browser in headless mode (default: visible browser for debugging)",
)
@click.option(
    "--chromedriver-path",
    envvar="CHROMEDRIVER_PATH",
    help="Path to chromedriver executable (auto-downloads if not specified)",
)
@click.option(
    "--action-delay",
    type=float,
    default=1.0,
    help="Delay between actions in seconds (default: 1.0)",
)
@click.option(
    "--scroll-delay",
    type=float,
    default=0.5,
    help="Delay between scroll actions in seconds (default: 0.5)",
)
@click.option(
    "--page-load-timeout",
    type=int,
    default=30,
    help="Maximum page load timeout in seconds (default: 30)",
)
@click.option(
    "--max-retries",
    type=int,
    default=3,
    help="Maximum retry attempts for failed operations (default: 3)",
)
@click.option(
    "--screenshot-on-error",
    is_flag=True,
    default=False,
    help="Capture screenshot when errors occur (for debugging)",
)
# General options
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def main(
    profile_url: str,
    # Database options
    db_url: str | None,
    db_host: str | None,
    db_port: int | None,
    db_name: str | None,
    db_user: str | None,
    db_password: str | None,
    # Legacy LinkedIn API options
    linkedin_api_key: str | None,
    linkedin_api_secret: str | None,
    # Authentication options
    linkedin_cookie: str | None,
    linkedin_email: str | None,
    linkedin_password: str | None,
    profile_email: str | None,
    # Browser configuration
    headless: bool,
    chromedriver_path: str | None,
    action_delay: float,
    scroll_delay: float,
    page_load_timeout: int,
    max_retries: int,
    screenshot_on_error: bool,
    # General options
    verbose: bool,
) -> int:
    """Import LinkedIn profile data to PostgreSQL database using web scraping.

    PROFILE_URL: LinkedIn profile URL to import (e.g., https://linkedin.com/in/username)

    \b
    AUTHENTICATION:
    ---------------
    The recommended authentication method is cookie-based:

    \b
    1. Log into LinkedIn in your browser
    2. Open DevTools (F12) → Application → Cookies → linkedin.com
    3. Copy the value of the 'li_at' cookie
    4. Set LINKEDIN_COOKIE environment variable or use --linkedin-cookie

    This method bypasses 2FA and is more reliable than email/password login.

    \b
    Alternatively, use email/password authentication (may trigger 2FA):
    - Set LINKEDIN_EMAIL and LINKEDIN_PASSWORD environment variables
    - Or use --linkedin-email and --linkedin-password options

    \b
    PROFILE EMAIL:
    --------------
    LinkedIn does not expose email addresses publicly, so you must provide
    an email address for the imported profile using --profile-email or
    the PROFILE_EMAIL environment variable.

    \b
    EXAMPLES:
    ---------
    # Using cookie authentication (recommended)
    export LINKEDIN_COOKIE="AQEDAQNv..."
    linkedin-importer https://linkedin.com/in/johndoe --profile-email john@example.com

    \b
    # Using email/password authentication
    linkedin-importer https://linkedin.com/in/johndoe \\
        --linkedin-email user@example.com \\
        --linkedin-password mypassword \\
        --profile-email john@example.com

    \b
    # Running in headless mode with custom delays
    linkedin-importer https://linkedin.com/in/johndoe \\
        --profile-email john@example.com \\
        --headless \\
        --action-delay 2.0

    Returns:
        Exit code: 0 for success, 1 for failure
    """
    setup_logging(verbose)
    logger = get_logger(__name__)

    logger.info(
        f"LinkedIn Profile Importer v{__import__('linkedin_importer').__version__}"
    )
    logger.info(f"Profile URL: {profile_url}")

    # Load and validate configuration
    config = load_config(
        profile_url=profile_url,
        db_url=db_url,
        db_host=db_host,
        db_port=db_port,
        db_name=db_name,
        db_user=db_user,
        db_password=db_password,
        linkedin_api_key=linkedin_api_key,
        linkedin_api_secret=linkedin_api_secret,
        linkedin_cookie=linkedin_cookie,
        linkedin_email=linkedin_email,
        linkedin_password=linkedin_password,
        profile_email=profile_email,
        headless=headless,
        chromedriver_path=chromedriver_path,
        action_delay=action_delay,
        scroll_delay=scroll_delay,
        page_load_timeout=page_load_timeout,
        max_retries=max_retries,
        screenshot_on_error=screenshot_on_error,
        verbose=verbose,
    )

    logger.debug("Configuration loaded successfully")
    logger.debug(
        f"Database: {config.database.host}:{config.database.port}/{config.database.name}"
    )

    # Log authentication method
    if config.auth:
        auth_method = (
            "cookie (li_at)"
            if config.auth.method == AuthMethod.COOKIE
            else "email/password"
        )
        logger.info(f"Authentication method: {auth_method}")
    else:
        logger.warning("No authentication configured - scraping may fail")

    # Log scraper settings
    logger.debug(f"Headless mode: {config.scraper.headless}")
    logger.debug(f"Action delay: {config.scraper.action_delay}s")
    logger.debug(f"Max retries: {config.scraper.max_retries}")

    # Execute import pipeline
    try:
        result = asyncio.run(import_profile(config))

        if result.success:
            logger.info("=" * 60)
            logger.info("Import completed successfully!")
            logger.info(f"  User ID: {result.user_id}")
            logger.info(f"  Projects imported: {result.projects_count}")
            logger.info(f"  Technologies linked: {result.technologies_count}")
            logger.info("=" * 60)
            return 0
        else:
            logger.error("=" * 60)
            logger.error("Import failed!")
            logger.error(f"  Error: {result.error}")
            logger.error("=" * 60)
            return 1

    except KeyboardInterrupt:
        logger.warning("\nImport interrupted by user")
        return 1

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.exception("Full traceback:")
        return 1


if __name__ == "__main__":
    sys.exit(main())
