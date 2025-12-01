"""End-to-end integration tests for the LinkedIn Profile Importer.

These tests verify the complete import flow using mock services.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from linkedin_importer.config import Config, DatabaseConfig, LinkedInConfig
from linkedin_importer.errors import APIError, AuthError, DatabaseError
from linkedin_importer.mapper import map_profile_to_database
from linkedin_importer.models import (
    Certification,
    Education,
    LinkedInProfile,
    Position,
    Publication,
    Skill,
    VolunteerExperience,
)
from linkedin_importer.orchestrator import import_profile
from linkedin_importer.repository import ImportResult, TransactionalRepository

from .mock_linkedin_api import MockLinkedInAPIServer

# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def mock_api_server():
    """Create a mock LinkedIn API server."""
    return MockLinkedInAPIServer()


@pytest.fixture
def test_config():
    """Create a test configuration."""
    return Config(
        database=DatabaseConfig(
            url=None,
            host="localhost",
            port=5432,
            name="test_db",
            user="test_user",
            password="test_password",
        ),
        linkedin=LinkedInConfig(
            api_key="test-api-key",
            api_secret="test-api-secret",
        ),
        profile_url="https://www.linkedin.com/in/johndoe",
        verbose=True,
    )


@pytest.fixture
def complete_profile():
    """Create a complete LinkedIn profile for testing."""
    return LinkedInProfile(
        profile_id="johndoe",
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        headline="Senior Software Engineer",
        summary="Experienced software engineer...",
        location="San Francisco, CA",
        industry="Technology",
        profile_picture_url="https://example.com/photo.jpg",
        positions=[
            Position(
                company_name="TechCorp",
                title="Senior Engineer",
                description="Building great software",
                start_date=datetime(2020, 1, 1).date(),
                end_date=None,
                location="San Francisco",
                employment_type="Full-time",
            ),
            Position(
                company_name="StartupXYZ",
                title="Software Engineer",
                description="Full-stack development",
                start_date=datetime(2017, 6, 1).date(),
                end_date=datetime(2019, 12, 31).date(),
                location="New York",
                employment_type="Full-time",
            ),
        ],
        education=[
            Education(
                school="MIT",
                degree="Master of Science",
                field_of_study="Computer Science",
                start_date=datetime(2015, 9, 1).date(),
                end_date=datetime(2017, 5, 31).date(),
            ),
        ],
        skills=[
            Skill(name="Python", endorsement_count=99),
            Skill(name="Rust", endorsement_count=45),
            Skill(name="PostgreSQL", endorsement_count=67),
        ],
        certifications=[
            Certification(
                name="AWS Solutions Architect",
                authority="Amazon Web Services",
                start_date=datetime(2021, 3, 1).date(),
            ),
        ],
        publications=[
            Publication(
                name="Scaling Microservices",
                publisher="Tech Blog",
                publication_date=datetime(2022, 6, 15).date(),
            ),
        ],
        volunteer=[
            VolunteerExperience(
                organization="Code.org",
                role="Volunteer Instructor",
                cause="Education",
                start_date=datetime(2019, 1, 1).date(),
            ),
        ],
    )


# ==============================================================================
# Mock API Server Tests
# ==============================================================================


class TestMockAPIServer:
    """Tests for the mock API server itself."""

    @pytest.mark.asyncio
    async def test_mock_server_authentication(self, mock_api_server):
        """Test that mock server can authenticate."""
        result = await mock_api_server.authenticate("key", "secret")
        assert result["status_code"] == 200
        assert "access_token" in result

    @pytest.mark.asyncio
    async def test_mock_server_auth_failure_simulation(self, mock_api_server):
        """Test that mock server can simulate auth failure."""
        mock_api_server.config.simulate_auth_failure = True
        result = await mock_api_server.authenticate("key", "secret")
        assert result["status_code"] == 401
        assert "error" in result

    @pytest.mark.asyncio
    async def test_mock_server_rate_limit_simulation(self, mock_api_server):
        """Test that mock server can simulate rate limiting."""
        mock_api_server.config.simulate_rate_limit = True
        result = await mock_api_server.get_profile_basic("johndoe")
        assert result["status_code"] == 429
        assert "Retry-After" in result["headers"]

    @pytest.mark.asyncio
    async def test_mock_server_profile_not_found(self, mock_api_server):
        """Test 404 response for unknown profile."""
        result = await mock_api_server.get_profile_basic("nonexistent")
        assert result["status_code"] == 404

    @pytest.mark.asyncio
    async def test_mock_server_complete_profile(self, mock_api_server):
        """Test fetching complete profile data."""
        result = await mock_api_server.get_profile_basic("johndoe")
        assert result["status_code"] == 200
        assert result["data"]["firstName"]["localized"]["en_US"] == "John"

    @pytest.mark.asyncio
    async def test_mock_server_tracks_requests(self, mock_api_server):
        """Test that mock server tracks all requests."""
        await mock_api_server.get_profile_basic("johndoe")
        await mock_api_server.get_profile_skills("johndoe")

        assert mock_api_server.config.request_count == 2
        assert len(mock_api_server.config.request_history) == 2


# ==============================================================================
# Data Mapper Integration Tests
# ==============================================================================


class TestDataMapperIntegration:
    """Integration tests for data mapping."""

    def test_complete_profile_mapping(self, complete_profile):
        """Test mapping a complete profile to database models."""
        user_data, projects = map_profile_to_database(complete_profile)

        # Verify user data
        assert user_data.email == "john.doe@example.com"
        assert user_data.name == "John Doe"
        assert "Senior Software Engineer" in user_data.bio
        assert user_data.avatar_url == "https://example.com/photo.jpg"

        # Verify projects were created from positions, certs, pubs, volunteer
        # 2 positions + 1 cert + 1 pub + 1 volunteer = 5 projects
        assert len(projects) == 5

    def test_skills_linked_to_recent_projects(self, complete_profile):
        """Test that skills are linked to most recent projects."""
        user_data, projects = map_profile_to_database(complete_profile)

        # Skills should be linked to up to 3 most recent projects
        projects_with_skills = [p for p in projects if p.technologies]
        assert len(projects_with_skills) <= 3

        # Verify skills are sorted by endorsement count
        for project in projects_with_skills:
            assert "Python" in project.technologies  # Highest endorsement count

    def test_unique_slugs_generated(self, complete_profile):
        """Test that unique slugs are generated for all projects."""
        user_data, projects = map_profile_to_database(complete_profile)

        slugs = [p.slug for p in projects]
        assert len(slugs) == len(set(slugs)), "All slugs should be unique"

    def test_bio_contains_education(self, complete_profile):
        """Test that bio contains education information."""
        user_data, projects = map_profile_to_database(complete_profile)

        assert "EDUCATION" in user_data.bio
        assert "MIT" in user_data.bio
        assert "Computer Science" in user_data.bio

    def test_position_dates_preserved(self, complete_profile):
        """Test that position dates are correctly mapped."""
        user_data, projects = map_profile_to_database(complete_profile)

        # Find the position projects
        position_projects = [
            p
            for p in projects
            if "at TechCorp" in p.title or "at StartupXYZ" in p.title
        ]
        assert len(position_projects) == 2

        # Check that dates are set
        for project in position_projects:
            assert project.created_at is not None


# ==============================================================================
# Repository Integration Tests
# ==============================================================================


class TestRepositoryIntegration:
    """Integration tests for database repository."""

    def _create_mock_pool(
        self, user_id=None, project_ids=None, should_fail=False, fail_at=None
    ):
        """Create a mock connection pool."""
        user_id = user_id or uuid4()
        project_ids = project_ids or [uuid4()]

        class MockTransaction:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return False

        class MockConnection:
            def __init__(self):
                self.execute_count = 0

            def transaction(self):
                return MockTransaction()

            async def fetchrow(self, *args, **kwargs):
                if should_fail and fail_at == "fetchrow":
                    raise Exception("Simulated fetchrow failure")
                return {"id": user_id}

            async def fetch(self, *args, **kwargs):
                if should_fail and fail_at == "fetch":
                    raise Exception("Simulated fetch failure")
                return [{"id": pid} for pid in project_ids]

            async def execute(self, *args, **kwargs):
                self.execute_count += 1
                if should_fail and fail_at == "execute":
                    raise Exception("Simulated execute failure")

            async def executemany(self, *args, **kwargs):
                if should_fail and fail_at == "executemany":
                    raise Exception("Simulated executemany failure")

        class MockPoolAcquire:
            def __init__(self, conn):
                self.conn = conn

            async def __aenter__(self):
                return self.conn

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return False

        class MockPool:
            def __init__(self):
                self.conn = MockConnection()
                self._closed = False

            def acquire(self):
                return MockPoolAcquire(self.conn)

            async def close(self):
                self._closed = True

        return MockPool()

    @pytest.mark.asyncio
    async def test_successful_import(self, test_config, complete_profile):
        """Test successful database import."""
        user_data, projects = map_profile_to_database(complete_profile)

        repo = TransactionalRepository(test_config.database)
        user_id = uuid4()
        project_ids = [uuid4() for _ in projects]
        repo._pool = self._create_mock_pool(user_id, project_ids)

        # Patch internal methods
        with patch.object(repo, "_upsert_user_in_transaction", return_value=user_id):
            with patch.object(
                repo, "_insert_projects_in_transaction", return_value=project_ids
            ):
                with patch.object(
                    repo, "_link_technologies_in_transaction", return_value=None
                ):
                    result = await repo.execute_import(user_data, projects)

        assert result.success is True
        assert result.user_id == user_id
        assert result.projects_count == len(projects)

    @pytest.mark.asyncio
    async def test_rollback_on_project_insert_failure(
        self, test_config, complete_profile
    ):
        """Test that transaction rolls back when project insertion fails."""
        user_data, projects = map_profile_to_database(complete_profile)

        repo = TransactionalRepository(test_config.database)
        repo._pool = self._create_mock_pool(should_fail=True, fail_at="fetch")

        async def mock_upsert(*args, **kwargs):
            return uuid4()

        async def mock_insert(*args, **kwargs):
            raise Exception("Simulated project insert failure")

        with patch.object(repo, "_upsert_user_in_transaction", side_effect=mock_upsert):
            with patch.object(
                repo, "_insert_projects_in_transaction", side_effect=mock_insert
            ):
                result = await repo.execute_import(user_data, projects)

        assert result.success is False
        assert "project insert failure" in result.error

    @pytest.mark.asyncio
    async def test_rollback_on_technology_link_failure(
        self, test_config, complete_profile
    ):
        """Test that transaction rolls back when technology linking fails."""
        user_data, projects = map_profile_to_database(complete_profile)

        repo = TransactionalRepository(test_config.database)
        user_id = uuid4()
        project_ids = [uuid4() for _ in projects]
        repo._pool = self._create_mock_pool(user_id, project_ids)

        async def mock_link(*args, **kwargs):
            raise Exception("Simulated technology link failure")

        with patch.object(repo, "_upsert_user_in_transaction", return_value=user_id):
            with patch.object(
                repo, "_insert_projects_in_transaction", return_value=project_ids
            ):
                with patch.object(
                    repo, "_link_technologies_in_transaction", side_effect=mock_link
                ):
                    result = await repo.execute_import(user_data, projects)

        assert result.success is False
        assert "technology link failure" in result.error


# ==============================================================================
# End-to-End Orchestration Tests
# ==============================================================================


class TestEndToEndOrchestration:
    """End-to-end tests for the full import orchestration."""

    @pytest.mark.asyncio
    async def test_successful_import_flow(self, test_config, complete_profile):
        """Test the complete successful import flow."""
        user_id = uuid4()
        project_count = 5  # 2 positions + 1 cert + 1 pub + 1 volunteer

        # Mock the LinkedInClient
        mock_client = AsyncMock()
        mock_client.authenticate = AsyncMock()
        mock_client.get_profile = AsyncMock(return_value=complete_profile)

        # Create mock context manager
        async def mock_aenter(*args):
            return mock_client

        async def mock_aexit(*args):
            pass

        mock_client.__aenter__ = mock_aenter
        mock_client.__aexit__ = mock_aexit

        # Mock the repository
        mock_result = ImportResult(
            success=True,
            user_id=user_id,
            projects_count=project_count,
            technologies_count=3,
        )

        with patch("linkedin_importer.orchestrator.LinkedInClient") as MockClient:
            MockClient.return_value = mock_client
            mock_client.__aenter__ = mock_aenter
            mock_client.__aexit__ = mock_aexit

            with patch(
                "linkedin_importer.orchestrator.TransactionalRepository"
            ) as MockRepo:
                mock_repo = AsyncMock()
                mock_repo.connect = AsyncMock()
                mock_repo.execute_import = AsyncMock(return_value=mock_result)
                mock_repo._pool = MagicMock()
                mock_repo._pool.close = AsyncMock()
                MockRepo.return_value = mock_repo

                result = await import_profile(test_config)

        assert result.success is True
        assert result.user_id == user_id
        assert result.projects_count == project_count

    @pytest.mark.asyncio
    async def test_auth_failure_handled(self, test_config):
        """Test that authentication failure is handled gracefully."""
        mock_client = AsyncMock()
        mock_client.authenticate = AsyncMock(
            side_effect=AuthError(
                "Authentication failed", {"reason": "invalid_credentials"}
            )
        )

        async def mock_aenter(*args):
            return mock_client

        async def mock_aexit(*args):
            pass

        mock_client.__aenter__ = mock_aenter
        mock_client.__aexit__ = mock_aexit

        with patch("linkedin_importer.orchestrator.LinkedInClient") as MockClient:
            MockClient.return_value = mock_client

            result = await import_profile(test_config)

        assert result.success is False
        assert "authentication failed" in result.error.lower()

    @pytest.mark.asyncio
    async def test_api_error_handled(self, test_config):
        """Test that API errors are handled gracefully."""
        mock_client = AsyncMock()
        mock_client.authenticate = AsyncMock()
        mock_client.get_profile = AsyncMock(
            side_effect=APIError("Profile not found", {"status_code": 404})
        )

        async def mock_aenter(*args):
            return mock_client

        async def mock_aexit(*args):
            pass

        mock_client.__aenter__ = mock_aenter
        mock_client.__aexit__ = mock_aexit

        with patch("linkedin_importer.orchestrator.LinkedInClient") as MockClient:
            MockClient.return_value = mock_client

            result = await import_profile(test_config)

        assert result.success is False
        assert "api" in result.error.lower() or "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_database_error_handled(self, test_config, complete_profile):
        """Test that database errors are handled gracefully."""
        mock_client = AsyncMock()
        mock_client.authenticate = AsyncMock()
        mock_client.get_profile = AsyncMock(return_value=complete_profile)

        async def mock_aenter(*args):
            return mock_client

        async def mock_aexit(*args):
            pass

        mock_client.__aenter__ = mock_aenter
        mock_client.__aexit__ = mock_aexit

        with patch("linkedin_importer.orchestrator.LinkedInClient") as MockClient:
            MockClient.return_value = mock_client

            with patch(
                "linkedin_importer.orchestrator.TransactionalRepository"
            ) as MockRepo:
                mock_repo = AsyncMock()
                mock_repo.connect = AsyncMock(
                    side_effect=DatabaseError(
                        "Connection refused", {"host": "localhost"}
                    )
                )
                MockRepo.return_value = mock_repo

                result = await import_profile(test_config)

        assert result.success is False
        assert (
            "database" in result.error.lower() or "connection" in result.error.lower()
        )

    @pytest.mark.asyncio
    async def test_profile_without_email_rejected(self, test_config):
        """Test that profile without email is rejected."""
        profile_without_email = LinkedInProfile(
            profile_id="noemail",
            first_name="No",
            last_name="Email",
            email="",  # Empty email
        )

        mock_client = AsyncMock()
        mock_client.authenticate = AsyncMock()
        mock_client.get_profile = AsyncMock(return_value=profile_without_email)

        async def mock_aenter(*args):
            return mock_client

        async def mock_aexit(*args):
            pass

        mock_client.__aenter__ = mock_aenter
        mock_client.__aexit__ = mock_aexit

        with patch("linkedin_importer.orchestrator.LinkedInClient") as MockClient:
            MockClient.return_value = mock_client

            result = await import_profile(test_config)

        assert result.success is False
        assert "email" in result.error.lower()


# ==============================================================================
# Error Scenario Tests
# ==============================================================================


class TestErrorScenarios:
    """Tests for various error scenarios."""

    @pytest.mark.asyncio
    async def test_network_error_during_profile_fetch(self, test_config):
        """Test handling of network errors during profile fetch."""
        mock_client = AsyncMock()
        mock_client.authenticate = AsyncMock()
        mock_client.get_profile = AsyncMock(
            side_effect=ConnectionError("Network unreachable")
        )

        async def mock_aenter(*args):
            return mock_client

        async def mock_aexit(*args):
            pass

        mock_client.__aenter__ = mock_aenter
        mock_client.__aexit__ = mock_aexit

        with patch("linkedin_importer.orchestrator.LinkedInClient") as MockClient:
            MockClient.return_value = mock_client

            result = await import_profile(test_config)

        assert result.success is False

    @pytest.mark.asyncio
    async def test_empty_profile_sections(self, test_config):
        """Test import with empty profile sections."""
        minimal_profile = LinkedInProfile(
            profile_id="minimal",
            first_name="Minimal",
            last_name="User",
            email="minimal@example.com",
            # All other fields are empty
        )

        mock_client = AsyncMock()
        mock_client.authenticate = AsyncMock()
        mock_client.get_profile = AsyncMock(return_value=minimal_profile)

        async def mock_aenter(*args):
            return mock_client

        async def mock_aexit(*args):
            pass

        mock_client.__aenter__ = mock_aenter
        mock_client.__aexit__ = mock_aexit

        mock_result = ImportResult(
            success=True,
            user_id=uuid4(),
            projects_count=0,
            technologies_count=0,
        )

        with patch("linkedin_importer.orchestrator.LinkedInClient") as MockClient:
            MockClient.return_value = mock_client

            with patch(
                "linkedin_importer.orchestrator.TransactionalRepository"
            ) as MockRepo:
                mock_repo = AsyncMock()
                mock_repo.connect = AsyncMock()
                mock_repo.execute_import = AsyncMock(return_value=mock_result)
                mock_repo._pool = MagicMock()
                mock_repo._pool.close = AsyncMock()
                MockRepo.return_value = mock_repo

                result = await import_profile(test_config)

        assert result.success is True
        assert result.projects_count == 0


# ==============================================================================
# Constraint Handling Tests
# ==============================================================================


class TestConstraintHandling:
    """Tests for database constraint handling."""

    @pytest.mark.asyncio
    async def test_unique_email_constraint(self, test_config, complete_profile):
        """Test handling of unique email constraint violations."""
        # In reality, the upsert should handle this, but test the error case
        mock_client = AsyncMock()
        mock_client.authenticate = AsyncMock()
        mock_client.get_profile = AsyncMock(return_value=complete_profile)

        async def mock_aenter(*args):
            return mock_client

        async def mock_aexit(*args):
            pass

        mock_client.__aenter__ = mock_aenter
        mock_client.__aexit__ = mock_aexit

        # Simulate unique constraint violation
        mock_result = ImportResult(
            success=False,
            error="Unique constraint violation: email already exists",
        )

        with patch("linkedin_importer.orchestrator.LinkedInClient") as MockClient:
            MockClient.return_value = mock_client

            with patch(
                "linkedin_importer.orchestrator.TransactionalRepository"
            ) as MockRepo:
                mock_repo = AsyncMock()
                mock_repo.connect = AsyncMock()
                mock_repo.execute_import = AsyncMock(return_value=mock_result)
                mock_repo._pool = MagicMock()
                mock_repo._pool.close = AsyncMock()
                MockRepo.return_value = mock_repo

                result = await import_profile(test_config)

        assert result.success is False
        assert "constraint" in result.error.lower() or "email" in result.error.lower()

    @pytest.mark.asyncio
    async def test_duplicate_slug_handling(self, test_config):
        """Test that duplicate slugs are handled by generating unique ones."""
        # Create a profile with positions that would generate same slug
        profile = LinkedInProfile(
            profile_id="duplicate",
            first_name="Test",
            last_name="User",
            email="test@example.com",
            positions=[
                Position(
                    company_name="TechCorp",
                    title="Engineer",
                    start_date=datetime(2020, 1, 1).date(),
                ),
                Position(
                    company_name="TechCorp",
                    title="Engineer",  # Same title, same company
                    start_date=datetime(2018, 1, 1).date(),
                ),
            ],
        )

        user_data, projects = map_profile_to_database(profile)

        # Verify slugs are unique
        slugs = [p.slug for p in projects]
        assert len(slugs) == len(set(slugs)), "Slugs should be unique"


# ==============================================================================
# Integration Test with Mock API Server
# ==============================================================================


class TestWithMockAPIServer:
    """Integration tests using the mock API server."""

    @pytest.mark.asyncio
    async def test_fetch_complete_profile_from_mock_server(self, mock_api_server):
        """Test fetching a complete profile from the mock server."""
        # Authenticate first
        auth_result = await mock_api_server.authenticate("key", "secret")
        assert auth_result["status_code"] == 200

        # Fetch profile data
        basic = await mock_api_server.get_profile_basic("johndoe")
        experience = await mock_api_server.get_profile_experience("johndoe")
        education = await mock_api_server.get_profile_education("johndoe")
        skills = await mock_api_server.get_profile_skills("johndoe")

        # Verify all data was fetched
        assert basic["status_code"] == 200
        assert experience["status_code"] == 200
        assert education["status_code"] == 200
        assert skills["status_code"] == 200

        # Verify data content
        assert basic["data"]["firstName"]["localized"]["en_US"] == "John"
        assert len(experience["data"]["elements"]) > 0
        assert len(skills["data"]["elements"]) > 0

    @pytest.mark.asyncio
    async def test_rate_limit_handling_with_mock_server(self, mock_api_server):
        """Test rate limit handling with the mock server."""
        mock_api_server.config.simulate_rate_limit = True

        result = await mock_api_server.get_profile_basic("johndoe")

        assert result["status_code"] == 429
        assert "Retry-After" in result["headers"]

        # Clear the rate limit
        mock_api_server.reset()

        # Now should succeed
        result = await mock_api_server.get_profile_basic("johndoe")
        assert result["status_code"] == 200

    @pytest.mark.asyncio
    async def test_quota_exhaustion_with_mock_server(self, mock_api_server):
        """Test quota exhaustion handling with the mock server."""
        mock_api_server.config.simulate_quota_exhausted = True

        result = await mock_api_server.get_profile_basic("johndoe")

        assert result["status_code"] == 403
        assert "quota_exhausted" in result.get("error", "")

    @pytest.mark.asyncio
    async def test_server_reset_clears_state(self, mock_api_server):
        """Test that server reset clears all state."""
        # Make some requests
        await mock_api_server.get_profile_basic("johndoe")
        await mock_api_server.get_profile_skills("johndoe")

        assert mock_api_server.config.request_count == 2

        # Reset
        mock_api_server.reset()

        assert mock_api_server.config.request_count == 0
        assert len(mock_api_server.config.request_history) == 0
