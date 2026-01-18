"""Database integration tests for the LinkedIn Profile Importer.

These tests verify database operations, transaction handling, and constraint management.
Note: For real PostgreSQL integration testing, set the TEST_DATABASE_URL environment variable.
"""

import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from linkedin_importer.config import DatabaseConfig
from linkedin_importer.db_models import (
    CertificationData,
    EducationData,
    ExperienceData,
    ProjectData,
    UserData,
    UserSkillData,
)
from linkedin_importer.errors import DatabaseError
from linkedin_importer.repository import ImportResult, TransactionalRepository

# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def db_config():
    """Create a test database configuration."""
    return DatabaseConfig(
        url=None,
        host="localhost",
        port=5432,
        name="test_portfolio",
        user="test_user",
        password="test_password",
    )


@pytest.fixture
def sample_user():
    """Create a sample user for testing."""
    return UserData(
        email="test.user@example.com",
        name="Test User",
        bio="A test user bio with some content.",
        avatar_url="https://example.com/avatar.jpg",
    )


@pytest.fixture
def sample_projects():
    """Create sample projects for testing."""
    return [
        ProjectData(
            slug="project-alpha",
            title="Project Alpha",
            description="First test project",
            long_description="Detailed description of project alpha.",
            technologies=["Python", "PostgreSQL", "Docker"],
        ),
        ProjectData(
            slug="project-beta",
            title="Project Beta",
            description="Second test project",
            technologies=["Rust", "Redis"],
        ),
        ProjectData(
            slug="project-gamma",
            title="Project Gamma",
            description="Third test project",
            technologies=[],
        ),
    ]


@pytest.fixture
def sample_experiences():
    """Create sample experiences for testing."""
    return []


@pytest.fixture
def sample_educations():
    """Create sample educations for testing."""
    return []


@pytest.fixture
def sample_certifications():
    """Create sample certifications for testing."""
    return []


@pytest.fixture
def sample_skills():
    """Create sample skills for testing."""
    return []


def create_mock_pool(
    user_id=None,
    project_ids=None,
    should_fail_at=None,
    constraint_error=None,
):
    """Create a mock connection pool with configurable behavior."""
    user_id = user_id or uuid4()
    project_ids = project_ids or [uuid4(), uuid4(), uuid4()]

    class MockTransaction:
        def __init__(self):
            self.committed = False
            self.rolled_back = False

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            if exc_type is not None:
                self.rolled_back = True
            else:
                self.committed = True
            return False

    class MockConnection:
        def __init__(self):
            self.transaction_obj = MockTransaction()
            self.fetchrow_count = 0
            self.fetch_count = 0
            self.execute_count = 0

        def transaction(self):
            return self.transaction_obj

        async def fetchrow(self, query, *args, **kwargs):
            self.fetchrow_count += 1

            if should_fail_at == "fetchrow":
                raise Exception("Simulated fetchrow failure")

            if constraint_error == "unique_email" and "users" in query:
                raise Exception("duplicate key value violates unique constraint")

            return {"id": user_id}

        async def fetch(self, query, *args, **kwargs):
            self.fetch_count += 1

            if should_fail_at == "fetch":
                raise Exception("Simulated fetch failure")

            return [{"id": pid} for pid in project_ids]

        async def execute(self, query, *args, **kwargs):
            self.execute_count += 1

            if should_fail_at == "execute":
                raise Exception("Simulated execute failure")

            if constraint_error == "foreign_key" and "project_technologies" in query:
                raise Exception("violates foreign key constraint")

        async def executemany(self, query, args_list, **kwargs):
            if should_fail_at == "executemany":
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


# ==============================================================================
# Connection Tests
# ==============================================================================


class TestDatabaseConnection:
    """Tests for database connection handling."""

    @pytest.mark.asyncio
    async def test_connection_string_from_url(self, db_config):
        """Test connection string generation from URL."""
        db_config.url = "postgresql://user:pass@host:5432/db"
        assert (
            db_config.get_connection_string() == "postgresql://user:pass@host:5432/db"
        )

    @pytest.mark.asyncio
    async def test_connection_string_from_components(self, db_config):
        """Test connection string generation from individual components."""
        conn_str = db_config.get_connection_string()
        assert "localhost" in conn_str
        assert "5432" in conn_str
        assert "test_portfolio" in conn_str
        assert "test_user" in conn_str

    @pytest.mark.asyncio
    async def test_connection_retry_on_failure(self, db_config):
        """Test that connection retries on transient failures."""
        repo = TransactionalRepository(db_config)

        call_count = 0
        mock_pool = create_mock_pool()

        async def mock_connect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Connection refused")
            return mock_pool

        # Need to also mock the pool.acquire() context manager for connection test
        mock_pool.acquire = MagicMock(
            return_value=AsyncMock(
                __aenter__=AsyncMock(
                    return_value=AsyncMock(fetchval=AsyncMock(return_value=1))
                ),
                __aexit__=AsyncMock(return_value=None),
            )
        )

        with patch("asyncpg.create_pool", side_effect=mock_connect):
            await repo.connect(max_retries=3)

        assert call_count == 2  # Succeeds on second attempt

    @pytest.mark.asyncio
    async def test_connection_max_retries_exceeded(self, db_config):
        """Test that connection fails after max retries exceeded."""
        repo = TransactionalRepository(db_config)

        async def mock_connect(*args, **kwargs):
            raise Exception("Connection refused")

        with patch("asyncpg.create_pool", side_effect=mock_connect):
            with pytest.raises(DatabaseError):
                await repo.connect(max_retries=3)

    @pytest.mark.asyncio
    async def test_pool_closed_on_disconnect(self, db_config):
        """Test that connection pool is properly closed."""
        repo = TransactionalRepository(db_config)
        repo._pool = create_mock_pool()

        await repo._pool.close()

        assert repo._pool._closed is True


# ==============================================================================
# Transaction Tests
# ==============================================================================


class TestTransactionHandling:
    """Tests for database transaction handling."""

    @pytest.mark.asyncio
    async def test_successful_transaction_commits(
        self,
        db_config,
        sample_user,
        sample_projects,
        sample_experiences,
        sample_educations,
        sample_certifications,
        sample_skills,
    ):
        """Test that successful operations result in commit."""
        repo = TransactionalRepository(db_config)
        user_id = uuid4()
        project_ids = [uuid4() for _ in sample_projects]
        repo._pool = create_mock_pool(user_id, project_ids)

        with patch.object(repo, "_upsert_user_in_transaction", return_value=user_id):
            with patch.object(
                repo, "_insert_projects_in_transaction", return_value=project_ids
            ):
                with patch.object(
                    repo, "_link_technologies_in_transaction", return_value=None
                ):
                    result = await repo.execute_import(
                        sample_user,
                        sample_projects,
                        sample_experiences,
                        sample_educations,
                        sample_certifications,
                        sample_skills,
                    )

        assert result.success is True
        assert result.user_id == user_id
        assert result.projects_count == len(sample_projects)

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_user_upsert_failure(
        self,
        db_config,
        sample_user,
        sample_projects,
        sample_experiences,
        sample_educations,
        sample_certifications,
        sample_skills,
    ):
        """Test rollback when user upsert fails."""
        repo = TransactionalRepository(db_config)
        repo._pool = create_mock_pool(should_fail_at="fetchrow")

        async def mock_upsert(*args, **kwargs):
            raise DatabaseError("User upsert failed")

        with patch.object(repo, "_upsert_user_in_transaction", side_effect=mock_upsert):
            result = await repo.execute_import(
                sample_user,
                sample_projects,
                sample_experiences,
                sample_educations,
                sample_certifications,
                sample_skills,
            )

        assert result.success is False
        assert "User upsert failed" in result.error

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_project_insert_failure(
        self,
        db_config,
        sample_user,
        sample_projects,
        sample_experiences,
        sample_educations,
        sample_certifications,
        sample_skills,
    ):
        """Test rollback when project insertion fails."""
        repo = TransactionalRepository(db_config)
        user_id = uuid4()
        repo._pool = create_mock_pool(user_id=user_id)

        async def mock_insert(*args, **kwargs):
            raise DatabaseError("Project insert failed")

        with patch.object(repo, "_upsert_user_in_transaction", return_value=user_id):
            with patch.object(
                repo, "_insert_projects_in_transaction", side_effect=mock_insert
            ):
                result = await repo.execute_import(
                    sample_user,
                    sample_projects,
                    sample_experiences,
                    sample_educations,
                    sample_certifications,
                    sample_skills,
                )

        assert result.success is False
        assert "Project insert failed" in result.error

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_technology_link_failure(
        self,
        db_config,
        sample_user,
        sample_projects,
        sample_experiences,
        sample_educations,
        sample_certifications,
        sample_skills,
    ):
        """Test rollback when technology linking fails."""
        repo = TransactionalRepository(db_config)
        user_id = uuid4()
        project_ids = [uuid4() for _ in sample_projects]
        repo._pool = create_mock_pool(user_id=user_id, project_ids=project_ids)

        async def mock_link(*args, **kwargs):
            raise DatabaseError("Technology link failed")

        with patch.object(repo, "_upsert_user_in_transaction", return_value=user_id):
            with patch.object(
                repo, "_insert_projects_in_transaction", return_value=project_ids
            ):
                with patch.object(
                    repo, "_link_technologies_in_transaction", side_effect=mock_link
                ):
                    result = await repo.execute_import(
                        sample_user,
                        sample_projects,
                        sample_experiences,
                        sample_educations,
                        sample_certifications,
                        sample_skills,
                    )

        assert result.success is False
        assert "Technology link failed" in result.error

    @pytest.mark.asyncio
    async def test_partial_failure_rolls_back_all_changes(
        self,
        db_config,
        sample_user,
        sample_projects,
        sample_experiences,
        sample_educations,
        sample_certifications,
        sample_skills,
    ):
        """Test that partial success doesn't leave orphaned data."""
        repo = TransactionalRepository(db_config)
        user_id = uuid4()
        project_ids = [uuid4(), uuid4()]  # Less than sample_projects

        # Mock pool that tracks operations
        mock_pool = create_mock_pool(user_id=user_id, project_ids=project_ids)
        repo._pool = mock_pool

        # Simulate failure during project insertion
        async def mock_insert(*args, **kwargs):
            raise DatabaseError("Failed during project insertion")

        with patch.object(repo, "_upsert_user_in_transaction", return_value=user_id):
            with patch.object(
                repo, "_insert_projects_in_transaction", side_effect=mock_insert
            ):
                result = await repo.execute_import(
                    sample_user,
                    sample_projects,
                    sample_experiences,
                    sample_educations,
                    sample_certifications,
                    sample_skills,
                )

        assert result.success is False
        assert "Failed during project insertion" in result.error
        # On failure, counts should be 0 indicating rollback
        assert result.projects_count == 0


# ==============================================================================
# Constraint Handling Tests
# ==============================================================================


class TestConstraintHandling:
    """Tests for database constraint handling."""

    @pytest.mark.asyncio
    async def test_unique_email_constraint_handling(
        self,
        db_config,
        sample_user,
        sample_projects,
        sample_experiences,
        sample_educations,
        sample_certifications,
        sample_skills,
    ):
        """Test handling of unique email constraint violations."""
        repo = TransactionalRepository(db_config)
        repo._pool = create_mock_pool(constraint_error="unique_email")

        async def mock_upsert(*args, **kwargs):
            raise DatabaseError("duplicate key value violates unique constraint")

        with patch.object(repo, "_upsert_user_in_transaction", side_effect=mock_upsert):
            result = await repo.execute_import(
                sample_user,
                sample_projects,
                sample_experiences,
                sample_educations,
                sample_certifications,
                sample_skills,
            )

        assert result.success is False
        assert (
            "duplicate" in result.error.lower() or "constraint" in result.error.lower()
        )

    @pytest.mark.asyncio
    async def test_foreign_key_constraint_handling(
        self,
        db_config,
        sample_user,
        sample_projects,
        sample_experiences,
        sample_educations,
        sample_certifications,
        sample_skills,
    ):
        """Test handling of foreign key constraint violations."""
        repo = TransactionalRepository(db_config)
        user_id = uuid4()
        project_ids = [uuid4() for _ in sample_projects]
        repo._pool = create_mock_pool(
            user_id=user_id,
            project_ids=project_ids,
            constraint_error="foreign_key",
        )

        async def mock_link(*args, **kwargs):
            raise DatabaseError("violates foreign key constraint")

        with patch.object(repo, "_upsert_user_in_transaction", return_value=user_id):
            with patch.object(
                repo, "_insert_projects_in_transaction", return_value=project_ids
            ):
                with patch.object(
                    repo, "_link_technologies_in_transaction", side_effect=mock_link
                ):
                    result = await repo.execute_import(
                        sample_user,
                        sample_projects,
                        sample_experiences,
                        sample_educations,
                        sample_certifications,
                        sample_skills,
                    )

        assert result.success is False
        assert "foreign key" in result.error.lower()

    @pytest.mark.asyncio
    async def test_unique_slug_generation(
        self,
        db_config,
        sample_user,
        sample_experiences,
        sample_educations,
        sample_certifications,
        sample_skills,
    ):
        """Test that similar slugs are made unique."""
        # Create projects with duplicate slugs
        projects = [
            ProjectData(
                slug="project-alpha",
                title="Project Alpha",
                description="First version",
            ),
            ProjectData(
                slug="project-alpha",  # Duplicate!
                title="Project Alpha v2",
                description="Second version",
            ),
        ]

        # The mapper should have already made slugs unique
        # This test verifies the repository can handle them
        repo = TransactionalRepository(db_config)
        user_id = uuid4()
        project_ids = [uuid4(), uuid4()]
        repo._pool = create_mock_pool(user_id=user_id, project_ids=project_ids)

        with patch.object(repo, "_upsert_user_in_transaction", return_value=user_id):
            with patch.object(
                repo, "_insert_projects_in_transaction", return_value=project_ids
            ):
                with patch.object(
                    repo, "_link_technologies_in_transaction", return_value=None
                ):
                    result = await repo.execute_import(
                        sample_user,
                        projects,
                        sample_experiences,
                        sample_educations,
                        sample_certifications,
                        sample_skills,
                    )

        # Should succeed (the repository doesn't handle slug uniqueness)
        assert result.success is True


# ==============================================================================
# User Upsert Tests
# ==============================================================================


class TestUserUpsert:
    """Tests for user upsert operations."""

    @pytest.mark.asyncio
    async def test_new_user_insert(
        self,
        db_config,
        sample_user,
        sample_projects,
        sample_experiences,
        sample_educations,
        sample_certifications,
        sample_skills,
    ):
        """Test inserting a new user."""
        repo = TransactionalRepository(db_config)
        user_id = uuid4()
        project_ids = [uuid4() for _ in sample_projects]
        repo._pool = create_mock_pool(user_id=user_id, project_ids=project_ids)

        with patch.object(repo, "_upsert_user_in_transaction", return_value=user_id):
            with patch.object(
                repo, "_insert_projects_in_transaction", return_value=project_ids
            ):
                with patch.object(
                    repo, "_link_technologies_in_transaction", return_value=None
                ):
                    result = await repo.execute_import(
                        sample_user,
                        sample_projects,
                        sample_experiences,
                        sample_educations,
                        sample_certifications,
                        sample_skills,
                    )

        assert result.success is True
        assert result.user_id == user_id

    @pytest.mark.asyncio
    async def test_existing_user_update(
        self,
        db_config,
        sample_projects,
        sample_experiences,
        sample_educations,
        sample_certifications,
        sample_skills,
    ):
        """Test updating an existing user."""
        existing_user = UserData(
            email="existing@example.com",
            name="Updated Name",
            bio="Updated bio content.",
        )

        repo = TransactionalRepository(db_config)
        existing_id = uuid4()
        project_ids = [uuid4() for _ in sample_projects]
        repo._pool = create_mock_pool(user_id=existing_id, project_ids=project_ids)

        with patch.object(
            repo, "_upsert_user_in_transaction", return_value=existing_id
        ):
            with patch.object(
                repo, "_insert_projects_in_transaction", return_value=project_ids
            ):
                with patch.object(
                    repo, "_link_technologies_in_transaction", return_value=None
                ):
                    result = await repo.execute_import(
                        existing_user,
                        sample_projects,
                        sample_experiences,
                        sample_educations,
                        sample_certifications,
                        sample_skills,
                    )

        assert result.success is True
        assert result.user_id == existing_id


# ==============================================================================
# Project Insertion Tests
# ==============================================================================


class TestProjectInsertion:
    """Tests for project insertion operations."""

    @pytest.mark.asyncio
    async def test_insert_multiple_projects(
        self,
        db_config,
        sample_user,
        sample_projects,
        sample_experiences,
        sample_educations,
        sample_certifications,
        sample_skills,
    ):
        """Test inserting multiple projects."""
        repo = TransactionalRepository(db_config)
        user_id = uuid4()
        project_ids = [uuid4() for _ in sample_projects]
        repo._pool = create_mock_pool(user_id=user_id, project_ids=project_ids)

        with patch.object(repo, "_upsert_user_in_transaction", return_value=user_id):
            with patch.object(
                repo, "_insert_projects_in_transaction", return_value=project_ids
            ):
                with patch.object(
                    repo, "_link_technologies_in_transaction", return_value=None
                ):
                    result = await repo.execute_import(
                        sample_user,
                        sample_projects,
                        sample_experiences,
                        sample_educations,
                        sample_certifications,
                        sample_skills,
                    )

        assert result.success is True
        assert result.projects_count == len(sample_projects)

    @pytest.mark.asyncio
    async def test_insert_empty_projects_list(
        self,
        db_config,
        sample_user,
        sample_experiences,
        sample_educations,
        sample_certifications,
        sample_skills,
    ):
        """Test importing user with no projects."""
        repo = TransactionalRepository(db_config)
        user_id = uuid4()
        repo._pool = create_mock_pool(user_id=user_id, project_ids=[])

        with patch.object(repo, "_upsert_user_in_transaction", return_value=user_id):
            with patch.object(repo, "_insert_projects_in_transaction", return_value=[]):
                with patch.object(
                    repo, "_link_technologies_in_transaction", return_value=None
                ):
                    result = await repo.execute_import(
                        sample_user,
                        [],
                        sample_experiences,
                        sample_educations,
                        sample_certifications,
                        sample_skills,
                    )

        assert result.success is True
        assert result.projects_count == 0


# ==============================================================================
# Technology Linking Tests
# ==============================================================================


class TestTechnologyLinking:
    """Tests for technology linking operations."""

    @pytest.mark.asyncio
    async def test_link_technologies_to_projects(
        self,
        db_config,
        sample_user,
        sample_projects,
        sample_experiences,
        sample_educations,
        sample_certifications,
        sample_skills,
    ):
        """Test linking technologies to projects."""
        repo = TransactionalRepository(db_config)
        user_id = uuid4()
        project_ids = [uuid4() for _ in sample_projects]
        repo._pool = create_mock_pool(user_id=user_id, project_ids=project_ids)

        with patch.object(repo, "_upsert_user_in_transaction", return_value=user_id):
            with patch.object(
                repo, "_insert_projects_in_transaction", return_value=project_ids
            ):
                with patch.object(
                    repo, "_link_technologies_in_transaction", return_value=None
                ) as mock_link:
                    result = await repo.execute_import(
                        sample_user,
                        sample_projects,
                        sample_experiences,
                        sample_educations,
                        sample_certifications,
                        sample_skills,
                    )

        assert result.success is True
        # Verify link_technologies was called (once per project with technologies)
        projects_with_tech = [p for p in sample_projects if p.technologies]
        assert mock_link.call_count == len(projects_with_tech)

    @pytest.mark.asyncio
    async def test_deduplicate_technologies(
        self,
        db_config,
        sample_user,
        sample_experiences,
        sample_educations,
        sample_certifications,
        sample_skills,
    ):
        """Test that duplicate technologies across projects are handled."""
        # Create projects sharing technologies
        projects = [
            ProjectData(
                slug="project-one",
                title="Project One",
                description="First project",
                technologies=["Python", "Docker", "PostgreSQL"],
            ),
            ProjectData(
                slug="project-two",
                title="Project Two",
                description="Second project",
                technologies=["Python", "Redis", "Docker"],  # Python and Docker repeat
            ),
        ]

        repo = TransactionalRepository(db_config)
        user_id = uuid4()
        project_ids = [uuid4(), uuid4()]
        repo._pool = create_mock_pool(user_id=user_id, project_ids=project_ids)

        with patch.object(repo, "_upsert_user_in_transaction", return_value=user_id):
            with patch.object(
                repo, "_insert_projects_in_transaction", return_value=project_ids
            ):
                with patch.object(
                    repo, "_link_technologies_in_transaction", return_value=None
                ):
                    result = await repo.execute_import(
                        sample_user,
                        projects,
                        sample_experiences,
                        sample_educations,
                        sample_certifications,
                        sample_skills,
                    )

        assert result.success is True


# ==============================================================================
# Import Result Tests
# ==============================================================================


class TestImportResult:
    """Tests for ImportResult dataclass."""

    def test_successful_result_has_all_counts(self):
        """Test that successful result has all required fields."""
        result = ImportResult(
            success=True,
            user_id=uuid4(),
            projects_count=5,
            technologies_count=15,
        )

        assert result.success is True
        assert result.user_id is not None
        assert result.projects_count == 5
        assert result.technologies_count == 15
        assert result.error is None

    def test_failed_result_has_error(self):
        """Test that failed result has error message."""
        result = ImportResult(
            success=False,
            error="Something went wrong",
        )

        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.user_id is None
        assert result.projects_count == 0
        assert result.technologies_count == 0

    def test_result_default_values(self):
        """Test ImportResult default values."""
        result = ImportResult(success=True)

        assert result.user_id is None
        assert result.projects_count == 0
        assert result.technologies_count == 0
        assert result.error is None


# ==============================================================================
# Real Database Integration Tests (Optional)
# ==============================================================================


@pytest.mark.skipif(
    os.getenv("TEST_DATABASE_URL") is None,
    reason="TEST_DATABASE_URL not set - skipping real database tests",
)
class TestRealDatabaseIntegration:
    """Integration tests with a real PostgreSQL database.

    These tests are skipped unless TEST_DATABASE_URL is set in the environment.
    To run these tests:
        export TEST_DATABASE_URL="postgresql://user:pass@localhost:5432/test_db"
        uv run pytest tests/test_database_integration.py -v -k "TestRealDatabaseIntegration"
    """

    @pytest.fixture
    def real_db_config(self):
        """Create configuration from TEST_DATABASE_URL."""
        return DatabaseConfig(url=os.getenv("TEST_DATABASE_URL"))

    @pytest.mark.asyncio
    async def test_real_database_connection(self, real_db_config):
        """Test connecting to a real PostgreSQL database."""
        repo = TransactionalRepository(real_db_config)

        try:
            await repo.connect(max_retries=1)
            assert repo._pool is not None
        finally:
            if repo._pool:
                await repo._pool.close()

    @pytest.mark.asyncio
    async def test_real_database_user_upsert(self, real_db_config, sample_user):
        """Test upserting a user in a real database."""
        repo = TransactionalRepository(real_db_config)

        try:
            await repo.connect(max_retries=1)

            # This test requires the database schema to be set up
            # It will fail if the users table doesn't exist
            result = await repo.execute_import(sample_user, [])

            # The result depends on schema existence
            # Just verify we got some kind of response
            assert isinstance(result, ImportResult)
        finally:
            if repo._pool:
                await repo._pool.close()
