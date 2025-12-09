"""Orchestration logic for LinkedIn profile import pipeline."""

from typing import Optional

from .config import AuthMethod, Config
from .errors import APIError, AuthError, DatabaseError, ValidationError
from .linkedin_client import LinkedInClient
from .logging_config import get_logger, log_error_with_details, log_progress
from .mapper import map_profile_to_database
from .repository import ImportResult, TransactionalRepository
from .scraper_adapter import convert_person_to_profile
from .scraper_client import LinkedInScraperClient
from .scraper_errors import (
    CookieExpired,
    ProfileNotFound,
    ScraperError,
    ScrapingBlocked,
    TwoFactorRequired,
)

logger = get_logger(__name__)


async def import_profile_scraper(config: Config) -> ImportResult:
    """Execute the LinkedIn profile import pipeline using web scraping.

    This orchestrates the scraper-based import flow:
    1. Initialize LinkedInScraperClient with browser settings
    2. Authenticate with LinkedIn (cookie or credentials)
    3. Scrape profile data from LinkedIn
    4. Convert scraped data to LinkedInProfile model
    5. Map LinkedIn profile to database models
    6. Connect to database
    7. Execute transactional import

    Args:
        config: Configuration containing LinkedIn auth credentials,
                browser settings, database connection info, and profile URL

    Returns:
        ImportResult with success status, imported data summary, or error details

    Raises:
        Does not raise exceptions - all errors are caught and returned in ImportResult
    """
    logger.info(
        "Starting LinkedIn profile import (scraper mode) for %s", config.profile_url
    )

    # Validate profile email is provided (required for scraper mode)
    if not config.profile_email:
        error_msg = "profile_email is required for scraper mode. Set PROFILE_EMAIL in your environment."
        logger.error(error_msg)
        return ImportResult(
            success=False,
            error=error_msg,
        )

    # Validate auth config is provided
    if config.auth is None:
        error_msg = (
            "Authentication configuration is required for scraper mode. "
            "Set LINKEDIN_COOKIE (preferred) or LINKEDIN_EMAIL and LINKEDIN_PASSWORD."
        )
        logger.error(error_msg)
        return ImportResult(
            success=False,
            error=error_msg,
        )

    # Initialize scraper client
    scraper: Optional[LinkedInScraperClient] = None
    try:
        log_progress(logger, "Initializing LinkedIn scraper client")
        scraper = LinkedInScraperClient(
            headless=config.scraper.headless,
            chromedriver_path=config.scraper.chromedriver_path,
            page_load_timeout=config.scraper.page_load_timeout,
            action_delay=config.scraper.action_delay,
            scroll_delay=config.scraper.scroll_delay,
            max_retries=config.scraper.max_retries,
            screenshot_on_error=config.scraper.screenshot_on_error,
        )

        driver_info = scraper.get_driver_info()
        log_progress(
            logger,
            "Scraper client initialized",
            details={
                "headless": config.scraper.headless,
                "chrome_version": driver_info.get("chrome_version"),
            },
        )

    except Exception as e:
        error_msg = f"Failed to initialize scraper client: {e}"
        logger.error(error_msg, extra={"profile_url": config.profile_url})
        return ImportResult(
            success=False,
            error=error_msg,
        )

    # Scrape profile data
    profile = None
    try:
        # Step 2: Authenticate with LinkedIn
        log_progress(
            logger,
            f"Authenticating with LinkedIn ({config.auth.method.value} method)",
        )

        if config.auth.method == AuthMethod.COOKIE:
            scraper.authenticate(cookie=config.auth.cookie)
        else:
            scraper.authenticate(
                email=config.auth.email,
                password=config.auth.password,
                handle_2fa=True,
            )

        log_progress(logger, "Successfully authenticated with LinkedIn")

        # Step 3: Scrape profile data
        log_progress(logger, f"Scraping profile from {config.profile_url}")
        person = scraper.get_profile(config.profile_url)

        log_progress(
            logger,
            f"Successfully scraped profile: {person.name}",
            details={
                "name": person.name,
                "experiences_count": len(getattr(person, "experiences", []) or []),
                "educations_count": len(getattr(person, "educations", []) or []),
            },
        )

        # Step 4: Convert scraped data to LinkedInProfile
        log_progress(logger, "Converting scraped data to profile model")
        profile = convert_person_to_profile(person, config.profile_email)

        log_progress(
            logger,
            f"Converted profile for {profile.first_name} {profile.last_name}",
            details={
                "positions_count": len(profile.positions),
                "education_count": len(profile.education),
                "skills_count": len(profile.skills),
            },
        )

    except CookieExpired as e:
        error_msg = f"LinkedIn session cookie has expired: {e.message}"
        log_error_with_details(logger, e, context={"auth_method": "cookie"})
        return ImportResult(
            success=False,
            error=error_msg,
        )

    except TwoFactorRequired as e:
        error_msg = f"Two-factor authentication required: {e.message}"
        log_error_with_details(logger, e, context={"auth_method": "credentials"})
        return ImportResult(
            success=False,
            error=error_msg,
        )

    except ProfileNotFound as e:
        error_msg = f"Profile not found: {e.message}"
        log_error_with_details(logger, e, context={"profile_url": config.profile_url})
        return ImportResult(
            success=False,
            error=error_msg,
        )

    except ScrapingBlocked as e:
        error_msg = f"LinkedIn blocked scraping: {e.message}"
        log_error_with_details(
            logger,
            e,
            context={
                "profile_url": config.profile_url,
                "retry_after": e.retry_after,
            },
        )
        return ImportResult(
            success=False,
            error=error_msg,
        )

    except ScraperError as e:
        error_msg = f"Scraping failed: {e.message}"
        log_error_with_details(logger, e, context=e.details)
        return ImportResult(
            success=False,
            error=error_msg,
        )

    except Exception as e:
        error_msg = f"Unexpected error during scraping: {e}"
        log_error_with_details(logger, e, context={"profile_url": config.profile_url})
        return ImportResult(
            success=False,
            error=error_msg,
        )

    finally:
        # Always close the browser to clean up resources
        if scraper is not None:
            try:
                log_progress(logger, "Closing browser")
                scraper.close()
                logger.debug("Browser closed successfully")
            except Exception as e:
                logger.warning("Error closing browser: %s", e)

    # Step 5: Validate profile data (implicitly done by Pydantic models)
    if not profile:
        error_msg = "Profile data is empty after scraping"
        logger.error(error_msg)
        return ImportResult(
            success=False,
            error=error_msg,
        )

    if not profile.email:
        error_msg = "Profile is missing required field: email"
        logger.error(error_msg, extra={"profile_url": config.profile_url})
        return ImportResult(
            success=False,
            error=error_msg,
        )

    # Step 6: Map LinkedIn profile to database models
    try:
        log_progress(logger, "Mapping profile data to database models")
        user_data, projects_data = map_profile_to_database(profile)

        log_progress(
            logger,
            f"Mapped {len(projects_data)} projects for user {user_data.email}",
            details={"projects_count": len(projects_data)},
        )

    except ValidationError as e:
        error_msg = f"Data validation failed: {e.message}"
        log_error_with_details(logger, e, context=e.details)
        return ImportResult(
            success=False,
            error=error_msg,
        )

    except Exception as e:
        error_msg = f"Failed to map profile data: {e}"
        log_error_with_details(logger, e, context={"profile_url": config.profile_url})
        return ImportResult(
            success=False,
            error=error_msg,
        )

    # Step 7: Connect to database
    repository = TransactionalRepository(config.database)
    try:
        log_progress(logger, "Connecting to database")
        await repository.connect(max_retries=3)
        log_progress(logger, "Database connection established")

    except DatabaseError as e:
        error_msg = f"Database connection failed: {e.message}"
        log_error_with_details(logger, e, context=e.details)
        return ImportResult(
            success=False,
            error=error_msg,
        )

    except Exception as e:
        error_msg = f"Unexpected error during database connection: {e}"
        log_error_with_details(
            logger,
            e,
            context={
                "host": config.database.host,
                "port": config.database.port,
                "database": config.database.name,
            },
        )
        return ImportResult(
            success=False,
            error=error_msg,
        )

    # Step 8: Execute transactional import
    try:
        log_progress(logger, "Executing database import")
        result = await repository.execute_import(user_data, projects_data)

        if result.success:
            log_progress(
                logger,
                "Import completed successfully",
                details={
                    "user_id": str(result.user_id) if result.user_id else None,
                    "projects_count": result.projects_count,
                    "technologies_count": result.technologies_count,
                },
            )
        else:
            logger.error("Import failed", extra={"error": result.error})

        return result

    except DatabaseError as e:
        error_msg = f"Database import failed: {e.message}"
        log_error_with_details(logger, e, context=e.details)
        return ImportResult(
            success=False,
            error=error_msg,
        )

    except Exception as e:
        error_msg = f"Unexpected error during import: {e}"
        log_error_with_details(
            logger,
            e,
            context={
                "email": user_data.email,
                "projects_count": len(projects_data),
            },
        )
        return ImportResult(
            success=False,
            error=error_msg,
        )

    finally:
        # Close database connection
        if repository._pool:
            await repository._pool.close()
            logger.debug("Database connection closed")


async def import_profile(config: Config) -> ImportResult:
    """Execute the complete LinkedIn profile import pipeline.

    This function automatically selects the appropriate import method:
    - If auth config is provided, uses the scraper-based approach (recommended)
    - If linkedin config is provided, uses the legacy API approach (deprecated)

    The scraper-based approach is preferred as it:
    - Uses real browser automation to scrape profile data
    - Supports cookie authentication to bypass 2FA
    - Works with any public LinkedIn profile

    Args:
        config: Configuration containing LinkedIn credentials,
                database connection info, and profile URL

    Returns:
        ImportResult with success status, imported data summary, or error details

    Raises:
        Does not raise exceptions - all errors are caught and returned in ImportResult
    """
    # Determine which import method to use
    # Prefer scraper mode if auth config is provided
    if config.auth is not None:
        logger.info("Using scraper-based import (recommended)")
        return await import_profile_scraper(config)

    # Fall back to legacy API mode if linkedin config is provided
    if config.linkedin is not None:
        logger.warning(
            "Using legacy API-based import (deprecated). "
            "Please migrate to scraper-based import by setting LINKEDIN_COOKIE."
        )
        return await _import_profile_legacy(config)

    # No valid configuration
    error_msg = (
        "No authentication configured. "
        "Set LINKEDIN_COOKIE (preferred) or LINKEDIN_EMAIL and LINKEDIN_PASSWORD for scraper mode."
    )
    logger.error(error_msg)
    return ImportResult(
        success=False,
        error=error_msg,
    )


async def _import_profile_legacy(config: Config) -> ImportResult:
    """Execute the LinkedIn profile import using the legacy API approach.

    DEPRECATED: This method uses the LinkedIn API which does not support
    fetching arbitrary public profiles. Use import_profile_scraper instead.

    Args:
        config: Configuration containing LinkedIn API credentials,
                database connection info, and profile URL

    Returns:
        ImportResult with success status, imported data summary, or error details
    """
    logger.info(
        "Starting LinkedIn profile import (legacy API mode) for %s", config.profile_url
    )

    # Step 1: Initialize LinkedIn client
    try:
        log_progress(logger, "Initializing LinkedIn API client")
        client = LinkedInClient(
            config=config.linkedin,
            request_delay=1.0,
            max_retries=3,
        )
    except Exception as e:
        error_msg = f"Failed to initialize LinkedIn client: {e}"
        logger.error(error_msg, extra={"profile_url": config.profile_url})
        return ImportResult(
            success=False,
            error=error_msg,
        )

    # Step 2: Authenticate and fetch profile data
    profile = None
    try:
        async with client:
            log_progress(logger, "Authenticating with LinkedIn API")
            await client.authenticate()

            log_progress(logger, f"Fetching profile data from {config.profile_url}")
            profile = await client.get_profile(config.profile_url)

            log_progress(
                logger,
                f"Successfully fetched profile for {profile.first_name} {profile.last_name}",
                details={
                    "name": f"{profile.first_name} {profile.last_name}",
                    "email": profile.email,
                },
            )

    except AuthError as e:
        error_msg = f"LinkedIn authentication failed: {e.message}"
        log_error_with_details(logger, e, context=e.details)
        return ImportResult(
            success=False,
            error=error_msg,
        )

    except APIError as e:
        error_msg = f"LinkedIn API request failed: {e.message}"
        log_error_with_details(logger, e, context=e.details)
        return ImportResult(
            success=False,
            error=error_msg,
        )

    except Exception as e:
        error_msg = f"Unexpected error during profile fetch: {e}"
        log_error_with_details(logger, e, context={"profile_url": config.profile_url})
        return ImportResult(
            success=False,
            error=error_msg,
        )

    # Step 3: Validate profile data (implicitly done by Pydantic models)
    if not profile:
        error_msg = "Profile data is empty after fetch"
        logger.error(error_msg)
        return ImportResult(
            success=False,
            error=error_msg,
        )

    if not profile.email:
        error_msg = "Profile is missing required field: email"
        logger.error(error_msg, extra={"profile_url": config.profile_url})
        return ImportResult(
            success=False,
            error=error_msg,
        )

    # Step 4: Map LinkedIn profile to database models
    try:
        log_progress(logger, "Mapping profile data to database models")
        user_data, projects_data = map_profile_to_database(profile)

        log_progress(
            logger,
            f"Mapped {len(projects_data)} projects for user {user_data.email}",
            details={"projects_count": len(projects_data)},
        )

    except ValidationError as e:
        error_msg = f"Data validation failed: {e.message}"
        log_error_with_details(logger, e, context=e.details)
        return ImportResult(
            success=False,
            error=error_msg,
        )

    except Exception as e:
        error_msg = f"Failed to map profile data: {e}"
        log_error_with_details(logger, e, context={"profile_url": config.profile_url})
        return ImportResult(
            success=False,
            error=error_msg,
        )

    # Step 5: Connect to database
    repository = TransactionalRepository(config.database)
    try:
        log_progress(logger, "Connecting to database")
        await repository.connect(max_retries=3)
        log_progress(logger, "Database connection established")

    except DatabaseError as e:
        error_msg = f"Database connection failed: {e.message}"
        log_error_with_details(logger, e, context=e.details)
        return ImportResult(
            success=False,
            error=error_msg,
        )

    except Exception as e:
        error_msg = f"Unexpected error during database connection: {e}"
        log_error_with_details(
            logger,
            e,
            context={
                "host": config.database.host,
                "port": config.database.port,
                "database": config.database.name,
            },
        )
        return ImportResult(
            success=False,
            error=error_msg,
        )

    # Step 6: Execute transactional import
    try:
        log_progress(logger, "Executing database import")
        result = await repository.execute_import(user_data, projects_data)

        if result.success:
            log_progress(
                logger,
                "Import completed successfully",
                details={
                    "user_id": str(result.user_id) if result.user_id else None,
                    "projects_count": result.projects_count,
                    "technologies_count": result.technologies_count,
                },
            )
        else:
            logger.error("Import failed", extra={"error": result.error})

        return result

    except DatabaseError as e:
        error_msg = f"Database import failed: {e.message}"
        log_error_with_details(logger, e, context=e.details)
        return ImportResult(
            success=False,
            error=error_msg,
        )

    except Exception as e:
        error_msg = f"Unexpected error during import: {e}"
        log_error_with_details(
            logger,
            e,
            context={
                "email": user_data.email,
                "projects_count": len(projects_data),
            },
        )
        return ImportResult(
            success=False,
            error=error_msg,
        )

    finally:
        # Close database connection
        if repository._pool:
            await repository._pool.close()
            logger.debug("Database connection closed")
