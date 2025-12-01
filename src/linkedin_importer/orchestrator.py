"""Orchestration logic for LinkedIn profile import pipeline."""

from .config import Config
from .errors import APIError, AuthError, DatabaseError, ValidationError
from .linkedin_client import LinkedInClient
from .logging_config import get_logger, log_error_with_details, log_progress
from .mapper import map_profile_to_database
from .repository import ImportResult, TransactionalRepository

logger = get_logger(__name__)


async def import_profile(config: Config) -> ImportResult:
    """Execute the complete LinkedIn profile import pipeline.

    This orchestrates the full import flow:
    1. Initialize and authenticate LinkedIn API client
    2. Fetch profile data from LinkedIn
    3. Validate profile data (via Pydantic models)
    4. Map LinkedIn profile to database models
    5. Connect to database
    6. Execute transactional import

    Args:
        config: Configuration containing LinkedIn API credentials,
                database connection info, and profile URL

    Returns:
        ImportResult with success status, imported data summary, or error details

    Raises:
        Does not raise exceptions - all errors are caught and returned in ImportResult
    """
    logger.info(f"Starting LinkedIn profile import for {config.profile_url}")

    # Step 1: Initialize LinkedIn client
    try:
        log_progress(logger, "Initializing LinkedIn API client")
        client = LinkedInClient(
            config=config.linkedin,
            request_delay=1.0,
            max_retries=3,
        )
    except Exception as e:
        error_msg = f"Failed to initialize LinkedIn client: {str(e)}"
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
        error_msg = f"Unexpected error during profile fetch: {str(e)}"
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
        error_msg = f"Failed to map profile data: {str(e)}"
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
        error_msg = f"Unexpected error during database connection: {str(e)}"
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
        error_msg = f"Unexpected error during import: {str(e)}"
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
