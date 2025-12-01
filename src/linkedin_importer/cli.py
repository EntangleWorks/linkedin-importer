"""CLI entry point for LinkedIn Profile Importer."""

import asyncio
import os
import sys

import click
from dotenv import load_dotenv
from pydantic import ValidationError

from linkedin_importer.config import Config, DatabaseConfig, LinkedInConfig
from linkedin_importer.logging_config import get_logger, setup_logging
from linkedin_importer.orchestrator import import_profile


def load_config(
    profile_url: str,
    db_url: str | None,
    db_host: str | None,
    db_port: int | None,
    db_name: str | None,
    db_user: str | None,
    db_password: str | None,
    linkedin_api_key: str | None,
    linkedin_api_secret: str | None,
    verbose: bool,
) -> Config:
    """Load configuration from CLI arguments and environment variables.

    CLI arguments take precedence over environment variables.
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

    # LinkedIn configuration with CLI args taking precedence over env vars
    linkedin_config_dict = {
        "api_key": linkedin_api_key or os.getenv("LINKEDIN_API_KEY", ""),
        "api_secret": linkedin_api_secret or os.getenv("LINKEDIN_API_SECRET", ""),
        "access_token": os.getenv("LINKEDIN_ACCESS_TOKEN"),
    }

    try:
        database_config = DatabaseConfig(**db_config_dict)
        linkedin_config = LinkedInConfig(**linkedin_config_dict)

        config = Config(
            database=database_config,
            linkedin=linkedin_config,
            profile_url=profile_url,
            verbose=verbose,
        )

        return config
    except ValidationError as e:
        click.echo(f"Configuration error: {e}", err=True)
        sys.exit(1)


@click.command()
@click.argument("profile_url")
@click.option("--db-url", help="Database connection URL")
@click.option("--db-host", help="Database host")
@click.option("--db-port", type=int, help="Database port")
@click.option("--db-name", help="Database name")
@click.option("--db-user", help="Database user")
@click.option("--db-password", help="Database password")
@click.option("--linkedin-api-key", help="LinkedIn API key")
@click.option("--linkedin-api-secret", help="LinkedIn API secret")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def main(
    profile_url: str,
    db_url: str | None,
    db_host: str | None,
    db_port: int | None,
    db_name: str | None,
    db_user: str | None,
    db_password: str | None,
    linkedin_api_key: str | None,
    linkedin_api_secret: str | None,
    verbose: bool,
) -> int:
    """Import LinkedIn profile data to PostgreSQL database.

    PROFILE_URL: LinkedIn profile URL or username to import

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
        verbose=verbose,
    )

    logger.debug("Configuration loaded successfully")
    logger.debug(
        f"Database: {config.database.host}:{config.database.port}/{config.database.name}"
    )

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
