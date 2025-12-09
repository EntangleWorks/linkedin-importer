"""Integration tests for the orchestrator module.

These tests verify the orchestrator correctly integrates the scraper client,
adapter, mapper, and repository components. They use mocks to avoid requiring
real browser/database connections.
"""

from dataclasses import dataclass
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from linkedin_importer.config import (
    AuthConfig,
    AuthMethod,
    Config,
    DatabaseConfig,
    ScraperConfig,
)
from linkedin_importer.orchestrator import (
    import_profile,
    import_profile_scraper,
)
from linkedin_importer.repository import ImportResult
from linkedin_importer.scraper_errors import (
    CookieExpired,
    ProfileNotFound,
    ScrapingBlocked,
    TwoFactorRequired,
)


@dataclass
class MockExperience:
    """Mock linkedin_scraper Experience object."""

    institution_name: str = "Test Company"
    position_title: str = "Software Engineer"
    from_date: str = "Jan 2020"
    to_date: str = "Present"
    duration: Optional[str] = "3 years"
    location: Optional[str] = "San Francisco, CA"
    description: Optional[str] = "Building great software"


@dataclass
class MockEducation:
    """Mock linkedin_scraper Education object."""

    institution_name: str = "Test University"
    degree: str = "Bachelor of Science"
    from_date: str = "2015"
    to_date: str = "2019"
    description: Optional[str] = "Computer Science"


@dataclass
class MockPerson:
    """Mock linkedin_scraper Person object."""

    name: str = "John Doe"
    linkedin_url: str = "https://www.linkedin.com/in/johndoe"
    job_title: Optional[str] = "Senior Software Engineer"
    about: Optional[str] = "Passionate developer"
    location: Optional[str] = "San Francisco, CA"
    experiences: Optional[list] = None
    educations: Optional[list] = None
    skills: Optional[list] = None
    interests: Optional[list] = None

    def __post_init__(self):
        if self.experiences is None:
            self.experiences = [MockExperience()]
        if self.educations is None:
            self.educations = [MockEducation()]
        if self.skills is None:
            self.skills = ["Python", "JavaScript", "Docker"]


def create_test_config(
    auth_method: AuthMethod = AuthMethod.COOKIE,
    cookie: str = "test_cookie_value",
    email: Optional[str] = None,
    password: Optional[str] = None,
    profile_url: str = "https://www.linkedin.com/in/johndoe",
    profile_email: str = "john.doe@example.com",
    headless: bool = True,
) -> Config:
    """Create a test configuration for the orchestrator."""
    auth_kwargs: dict[str, Any] = {"method": auth_method}
    if auth_method == AuthMethod.COOKIE:
        auth_kwargs["cookie"] = cookie
    else:
        auth_kwargs["email"] = email or "test@example.com"
        auth_kwargs["password"] = password or "testpass123"

    return Config(
        database=DatabaseConfig(
            name="testdb",
            user="testuser",
            password="testpass",
            host="localhost",
            port=5432,
        ),
        auth=AuthConfig(**auth_kwargs),
        scraper=ScraperConfig(headless=headless),
        profile_url=profile_url,
        profile_email=profile_email,
    )


class TestImportProfileScraper:
    """Tests for import_profile_scraper function."""

    @pytest.mark.asyncio
    async def test_successful_import_with_cookie_auth(self):
        """Test successful profile import using cookie authentication."""
        config = create_test_config()
        mock_person = MockPerson()

        with (
            patch(
                "linkedin_importer.orchestrator.LinkedInScraperClient"
            ) as mock_client_class,
            patch(
                "linkedin_importer.orchestrator.TransactionalRepository"
            ) as mock_repo_class,
        ):
            # Setup mock scraper client
            mock_client = MagicMock()
            mock_client.get_driver_info.return_value = {"chrome_version": "120.0.0"}
            mock_client.authenticate.return_value = True
            mock_client.get_profile.return_value = mock_person
            mock_client.close.return_value = None
            mock_client_class.return_value = mock_client

            # Setup mock repository
            mock_repo = AsyncMock()
            mock_repo.connect = AsyncMock()
            mock_repo.execute_import = AsyncMock(
                return_value=ImportResult(
                    success=True,
                    user_id=UUID("12345678-1234-5678-1234-567812345678"),
                    projects_count=1,
                    technologies_count=3,
                )
            )
            mock_repo._pool = MagicMock()
            mock_repo._pool.close = AsyncMock()
            mock_repo_class.return_value = mock_repo

            result = await import_profile_scraper(config)

            assert result.success is True
            assert result.projects_count == 1
            assert result.technologies_count == 3
            assert result.user_id is not None

            # Verify scraper was called correctly
            mock_client.authenticate.assert_called_once_with(cookie=config.auth.cookie)
            mock_client.get_profile.assert_called_once_with(config.profile_url)
            mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_successful_import_with_credentials_auth(self):
        """Test successful profile import using email/password authentication."""
        config = create_test_config(
            auth_method=AuthMethod.CREDENTIALS,
            email="test@example.com",
            password="password123",
        )
        mock_person = MockPerson()

        with (
            patch(
                "linkedin_importer.orchestrator.LinkedInScraperClient"
            ) as mock_client_class,
            patch(
                "linkedin_importer.orchestrator.TransactionalRepository"
            ) as mock_repo_class,
        ):
            mock_client = MagicMock()
            mock_client.get_driver_info.return_value = {"chrome_version": "120.0.0"}
            mock_client.authenticate.return_value = True
            mock_client.get_profile.return_value = mock_person
            mock_client.close.return_value = None
            mock_client_class.return_value = mock_client

            mock_repo = AsyncMock()
            mock_repo.connect = AsyncMock()
            mock_repo.execute_import = AsyncMock(
                return_value=ImportResult(
                    success=True,
                    user_id=UUID("12345678-1234-5678-1234-567812345678"),
                    projects_count=1,
                    technologies_count=3,
                )
            )
            mock_repo._pool = MagicMock()
            mock_repo._pool.close = AsyncMock()
            mock_repo_class.return_value = mock_repo

            result = await import_profile_scraper(config)

            assert result.success is True

            # Verify credentials auth was used
            mock_client.authenticate.assert_called_once_with(
                email=config.auth.email,
                password=config.auth.password,
                handle_2fa=True,
            )

    @pytest.mark.asyncio
    async def test_missing_profile_email_returns_error(self):
        """Test that missing profile_email returns an error."""
        # Create config without auth first (to bypass validation),
        # then manually set auth and leave profile_email as None
        config = Config(
            database=DatabaseConfig(
                name="testdb",
                user="testuser",
                password="testpass",
            ),
            auth=None,  # Set to None initially to bypass validation
            profile_url="https://www.linkedin.com/in/johndoe",
            profile_email=None,
        )
        # Now manually set auth (bypassing Pydantic validation)
        object.__setattr__(config, "auth", AuthConfig(cookie="test_cookie"))

        result = await import_profile_scraper(config)

        assert result.success is False
        assert "profile_email" in result.error.lower()

    @pytest.mark.asyncio
    async def test_missing_auth_config_returns_error(self):
        """Test that missing auth config returns an error."""
        # Create config without auth
        config = Config(
            database=DatabaseConfig(
                name="testdb",
                user="testuser",
                password="testpass",
            ),
            auth=None,  # Missing auth config
            profile_url="https://www.linkedin.com/in/johndoe",
            profile_email="john@example.com",
        )

        result = await import_profile_scraper(config)

        assert result.success is False
        assert "authentication" in result.error.lower()

    @pytest.mark.asyncio
    async def test_cookie_expired_error_handled(self):
        """Test that CookieExpired error is handled correctly."""
        config = create_test_config()

        with patch(
            "linkedin_importer.orchestrator.LinkedInScraperClient"
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_driver_info.return_value = {"chrome_version": "120.0.0"}
            mock_client.authenticate.side_effect = CookieExpired(
                "Session cookie has expired"
            )
            mock_client.close.return_value = None
            mock_client_class.return_value = mock_client

            result = await import_profile_scraper(config)

            assert result.success is False
            assert "expired" in result.error.lower()
            mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_two_factor_required_error_handled(self):
        """Test that TwoFactorRequired error is handled correctly."""
        config = create_test_config(
            auth_method=AuthMethod.CREDENTIALS,
            email="test@example.com",
            password="password123",
        )

        with patch(
            "linkedin_importer.orchestrator.LinkedInScraperClient"
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_driver_info.return_value = {"chrome_version": "120.0.0"}
            mock_client.authenticate.side_effect = TwoFactorRequired(
                "2FA verification required"
            )
            mock_client.close.return_value = None
            mock_client_class.return_value = mock_client

            result = await import_profile_scraper(config)

            assert result.success is False
            assert "two-factor" in result.error.lower() or "2fa" in result.error.lower()
            mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_profile_not_found_error_handled(self):
        """Test that ProfileNotFound error is handled correctly."""
        config = create_test_config()

        with patch(
            "linkedin_importer.orchestrator.LinkedInScraperClient"
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_driver_info.return_value = {"chrome_version": "120.0.0"}
            mock_client.authenticate.return_value = True
            mock_client.get_profile.side_effect = ProfileNotFound(
                profile_url=config.profile_url,
                message="Profile does not exist",
            )
            mock_client.close.return_value = None
            mock_client_class.return_value = mock_client

            result = await import_profile_scraper(config)

            assert result.success is False
            assert "not found" in result.error.lower()
            mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_scraping_blocked_error_handled(self):
        """Test that ScrapingBlocked error is handled correctly."""
        config = create_test_config()

        with patch(
            "linkedin_importer.orchestrator.LinkedInScraperClient"
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_driver_info.return_value = {"chrome_version": "120.0.0"}
            mock_client.authenticate.return_value = True
            mock_client.get_profile.side_effect = ScrapingBlocked(
                "LinkedIn has blocked this attempt",
                retry_after=300,
            )
            mock_client.close.return_value = None
            mock_client_class.return_value = mock_client

            result = await import_profile_scraper(config)

            assert result.success is False
            assert "blocked" in result.error.lower()
            mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_browser_closed_on_exception(self):
        """Test that browser is always closed even when exceptions occur."""
        config = create_test_config()

        with patch(
            "linkedin_importer.orchestrator.LinkedInScraperClient"
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_driver_info.return_value = {"chrome_version": "120.0.0"}
            mock_client.authenticate.side_effect = Exception("Unexpected error")
            mock_client.close.return_value = None
            mock_client_class.return_value = mock_client

            result = await import_profile_scraper(config)

            assert result.success is False
            # Verify browser was closed despite exception
            mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_database_connection_failure_handled(self):
        """Test that database connection failures are handled."""
        config = create_test_config()
        mock_person = MockPerson()

        with (
            patch(
                "linkedin_importer.orchestrator.LinkedInScraperClient"
            ) as mock_client_class,
            patch(
                "linkedin_importer.orchestrator.TransactionalRepository"
            ) as mock_repo_class,
        ):
            mock_client = MagicMock()
            mock_client.get_driver_info.return_value = {"chrome_version": "120.0.0"}
            mock_client.authenticate.return_value = True
            mock_client.get_profile.return_value = mock_person
            mock_client.close.return_value = None
            mock_client_class.return_value = mock_client

            mock_repo = AsyncMock()
            mock_repo.connect = AsyncMock(side_effect=Exception("Connection refused"))
            mock_repo._pool = None
            mock_repo_class.return_value = mock_repo

            result = await import_profile_scraper(config)

            assert result.success is False
            assert (
                "connection" in result.error.lower()
                or "database" in result.error.lower()
            )

    @pytest.mark.asyncio
    async def test_profile_with_no_experiences(self):
        """Test importing a profile with no work experience."""
        config = create_test_config()
        mock_person = MockPerson(
            name="New Graduate",
            experiences=[],
            educations=[MockEducation()],
        )

        with (
            patch(
                "linkedin_importer.orchestrator.LinkedInScraperClient"
            ) as mock_client_class,
            patch(
                "linkedin_importer.orchestrator.TransactionalRepository"
            ) as mock_repo_class,
        ):
            mock_client = MagicMock()
            mock_client.get_driver_info.return_value = {"chrome_version": "120.0.0"}
            mock_client.authenticate.return_value = True
            mock_client.get_profile.return_value = mock_person
            mock_client.close.return_value = None
            mock_client_class.return_value = mock_client

            mock_repo = AsyncMock()
            mock_repo.connect = AsyncMock()
            mock_repo.execute_import = AsyncMock(
                return_value=ImportResult(
                    success=True,
                    user_id=UUID("12345678-1234-5678-1234-567812345678"),
                    projects_count=0,
                    technologies_count=0,
                )
            )
            mock_repo._pool = MagicMock()
            mock_repo._pool.close = AsyncMock()
            mock_repo_class.return_value = mock_repo

            result = await import_profile_scraper(config)

            assert result.success is True
            assert result.projects_count == 0


class TestImportProfileDispatch:
    """Tests for import_profile dispatch function."""

    @pytest.mark.asyncio
    async def test_dispatches_to_scraper_when_auth_config_present(self):
        """Test that import_profile uses scraper when auth config is present."""
        config = create_test_config()

        with patch(
            "linkedin_importer.orchestrator.import_profile_scraper"
        ) as mock_scraper:
            mock_scraper.return_value = ImportResult(success=True)

            await import_profile(config)

            mock_scraper.assert_called_once_with(config)

    @pytest.mark.asyncio
    async def test_returns_error_when_no_auth_configured(self):
        """Test that error is returned when neither auth nor linkedin config exists."""
        config = Config(
            database=DatabaseConfig(
                name="testdb",
                user="testuser",
                password="testpass",
            ),
            auth=None,
            linkedin=None,
            profile_url="https://www.linkedin.com/in/johndoe",
        )

        result = await import_profile(config)

        assert result.success is False
        assert (
            "authentication" in result.error.lower()
            or "configured" in result.error.lower()
        )


class TestScraperClientInitialization:
    """Tests for scraper client initialization in orchestrator."""

    @pytest.mark.asyncio
    async def test_scraper_config_passed_to_client(self):
        """Test that scraper config values are passed to the client."""
        config = Config(
            database=DatabaseConfig(
                name="testdb",
                user="testuser",
                password="testpass",
            ),
            auth=AuthConfig(cookie="test_cookie"),
            scraper=ScraperConfig(
                headless=False,
                page_load_timeout=60,
                action_delay=2.5,
                scroll_delay=1.5,
                max_retries=5,
                screenshot_on_error=True,
            ),
            profile_url="https://www.linkedin.com/in/johndoe",
            profile_email="john@example.com",
        )

        with patch(
            "linkedin_importer.orchestrator.LinkedInScraperClient"
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_driver_info.return_value = {"chrome_version": "120.0.0"}
            mock_client.authenticate.side_effect = Exception("Test exception")
            mock_client.close.return_value = None
            mock_client_class.return_value = mock_client

            await import_profile_scraper(config)

            # Verify client was initialized with scraper config values
            mock_client_class.assert_called_once_with(
                headless=False,
                chromedriver_path=None,
                page_load_timeout=60,
                action_delay=2.5,
                scroll_delay=1.5,
                max_retries=5,
                screenshot_on_error=True,
            )


class TestEndToEndFlow:
    """End-to-end tests for the complete import flow with mocks."""

    @pytest.mark.asyncio
    async def test_complete_flow_with_multiple_experiences(self):
        """Test complete import flow with a profile containing multiple experiences."""
        config = create_test_config()

        experiences = [
            MockExperience(
                institution_name="Company A",
                position_title="Senior Developer",
                from_date="Jan 2022",
                to_date="Present",
            ),
            MockExperience(
                institution_name="Company B",
                position_title="Developer",
                from_date="Jun 2019",
                to_date="Dec 2021",
            ),
            MockExperience(
                institution_name="Company C",
                position_title="Junior Developer",
                from_date="Jan 2017",
                to_date="May 2019",
            ),
        ]

        mock_person = MockPerson(
            name="Experienced Developer",
            experiences=experiences,
            skills=["Python", "JavaScript", "Docker", "Kubernetes", "AWS"],
        )

        with (
            patch(
                "linkedin_importer.orchestrator.LinkedInScraperClient"
            ) as mock_client_class,
            patch(
                "linkedin_importer.orchestrator.TransactionalRepository"
            ) as mock_repo_class,
        ):
            mock_client = MagicMock()
            mock_client.get_driver_info.return_value = {"chrome_version": "120.0.0"}
            mock_client.authenticate.return_value = True
            mock_client.get_profile.return_value = mock_person
            mock_client.close.return_value = None
            mock_client_class.return_value = mock_client

            mock_repo = AsyncMock()
            mock_repo.connect = AsyncMock()
            mock_repo.execute_import = AsyncMock(
                return_value=ImportResult(
                    success=True,
                    user_id=UUID("12345678-1234-5678-1234-567812345678"),
                    projects_count=3,
                    technologies_count=5,
                )
            )
            mock_repo._pool = MagicMock()
            mock_repo._pool.close = AsyncMock()
            mock_repo_class.return_value = mock_repo

            result = await import_profile_scraper(config)

            assert result.success is True
            assert result.projects_count == 3
            assert result.technologies_count == 5

            # Verify execute_import was called with mapped data
            mock_repo.execute_import.assert_called_once()
            call_args = mock_repo.execute_import.call_args
            user_data, projects_data = call_args[0]

            assert user_data.email == config.profile_email
            assert "Experienced Developer" in user_data.name
            assert len(projects_data) == 3

    @pytest.mark.asyncio
    async def test_profile_with_special_characters(self):
        """Test importing a profile with special characters in the name."""
        config = create_test_config(profile_email="jose@example.com")

        mock_person = MockPerson(
            name="José María García-López",
            linkedin_url="https://www.linkedin.com/in/josemgarcia",
            job_title="Développeur Senior",
            location="São Paulo, Brasil",
        )

        with (
            patch(
                "linkedin_importer.orchestrator.LinkedInScraperClient"
            ) as mock_client_class,
            patch(
                "linkedin_importer.orchestrator.TransactionalRepository"
            ) as mock_repo_class,
        ):
            mock_client = MagicMock()
            mock_client.get_driver_info.return_value = {"chrome_version": "120.0.0"}
            mock_client.authenticate.return_value = True
            mock_client.get_profile.return_value = mock_person
            mock_client.close.return_value = None
            mock_client_class.return_value = mock_client

            mock_repo = AsyncMock()
            mock_repo.connect = AsyncMock()
            mock_repo.execute_import = AsyncMock(
                return_value=ImportResult(
                    success=True,
                    user_id=UUID("12345678-1234-5678-1234-567812345678"),
                    projects_count=1,
                    technologies_count=3,
                )
            )
            mock_repo._pool = MagicMock()
            mock_repo._pool.close = AsyncMock()
            mock_repo_class.return_value = mock_repo

            result = await import_profile_scraper(config)

            assert result.success is True

            # Verify special characters were preserved
            call_args = mock_repo.execute_import.call_args
            user_data, _ = call_args[0]
            assert "José" in user_data.name or "Garcia" in user_data.name
