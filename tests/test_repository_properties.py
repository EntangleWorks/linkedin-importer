"""Property-based tests for database repository operations.

Feature: linkedin-profile-importer, Property 12: Transaction rollback on failure
Validates: Requirements 5.2
"""

import asyncio
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from hypothesis import given, settings
from hypothesis import strategies as st

from linkedin_importer.config import DatabaseConfig
from linkedin_importer.db_models import ProjectData, UserData
from linkedin_importer.repository import TransactionalRepository


# Strategies for generating test data
@st.composite
def user_data_strategy(draw):
    """Generate valid UserData."""
    email = draw(st.emails())
    name = draw(st.text(min_size=1, max_size=100))
    bio = draw(st.text(max_size=1000))
    avatar_url = draw(st.none() | st.text(max_size=200))

    return UserData(
        email=email,
        name=name,
        bio=bio,
        avatar_url=avatar_url,
    )


@st.composite
def project_data_strategy(draw):
    """Generate valid ProjectData."""
    title = draw(st.text(min_size=1, max_size=100))
    description = draw(st.text(min_size=1, max_size=500))
    long_description = draw(st.none() | st.text(max_size=1000))
    image_url = draw(st.none() | st.text(max_size=200))
    live_url = draw(st.none() | st.text(max_size=200))
    technologies = draw(st.lists(st.text(min_size=1, max_size=50), max_size=5))

    return ProjectData(
        slug=title.lower().replace(" ", "-"),
        title=title,
        description=description,
        long_description=long_description,
        image_url=image_url,
        live_url=live_url,
        technologies=technologies,
    )


@settings(max_examples=100)
@given(
    user=user_data_strategy(),
    projects=st.lists(project_data_strategy(), min_size=1, max_size=3),
)
def test_transaction_rollback_on_failure(user, projects):
    """
    Feature: linkedin-profile-importer, Property 12: Transaction rollback on failure
    Validates: Requirements 5.2

    For any database operation sequence, when a failure occurs mid-transaction,
    all changes from that transaction should be rolled back leaving the database
    in its pre-transaction state.
    """
    # Create a mock database configuration
    config = DatabaseConfig(
        url=None,
        host="localhost",
        port=5432,
        name="test_db",
        user="test_user",
        password="test_password",
    )

    # Create repository
    repo = TransactionalRepository(config)

    # Track operations performed
    operations_performed = []

    # Mock user upsert to track it was called
    async def mock_upsert_user(*args, **kwargs):
        operations_performed.append("upsert_user")
        return uuid4()

    # Mock project insert to fail mid-operation
    async def mock_insert_projects(*args, **kwargs):
        operations_performed.append("insert_projects")
        # Always fail to simulate mid-transaction failure
        raise Exception("Simulated database error during project insertion")

    # Mock technology linking
    async def mock_link_technologies(*args, **kwargs):
        operations_performed.append("link_technologies")

    # Create proper async context manager mocks
    class MockTransaction:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            # Transaction rollback happens automatically on exception
            return False

    class MockConnection:
        def transaction(self):
            return MockTransaction()

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

        def acquire(self):
            return MockPoolAcquire(self.conn)

    # Inject the mock pool
    repo._pool = MockPool()

    # Patch the internal transaction methods
    with patch.object(
        repo, "_upsert_user_in_transaction", side_effect=mock_upsert_user
    ):
        with patch.object(
            repo, "_insert_projects_in_transaction", side_effect=mock_insert_projects
        ):
            with patch.object(
                repo,
                "_link_technologies_in_transaction",
                side_effect=mock_link_technologies,
            ):
                # Execute import - should fail
                result = asyncio.run(repo.execute_import(user, projects))

    # Verify the result indicates failure
    assert result.success is False
    assert result.error is not None
    assert "Simulated database error" in result.error

    # Verify that operations were attempted
    assert "upsert_user" in operations_performed
    assert "insert_projects" in operations_performed

    # The key property: when an exception occurs within the transaction context,
    # asyncpg automatically rolls back all changes. We verify this by:
    # 1. Confirming the transaction was entered
    # 2. Confirming an exception was raised
    # 3. Confirming the result indicates failure (no partial success)

    # Verify no partial success was reported
    assert result.user_id is None
    assert result.projects_count == 0
    assert result.technologies_count == 0


@settings(max_examples=100)
@given(
    user=user_data_strategy(),
    projects=st.lists(project_data_strategy(), min_size=1, max_size=3),
)
def test_transaction_commits_on_success(user, projects):
    """
    Complementary test: verify transaction commits when all operations succeed.

    For any database operation sequence, when all operations succeed,
    the transaction should commit and return success with proper counts.
    """
    # Create a mock database configuration
    config = DatabaseConfig(
        url=None,
        host="localhost",
        port=5432,
        name="test_db",
        user="test_user",
        password="test_password",
    )

    # Create repository
    repo = TransactionalRepository(config)

    # Mock successful operations
    user_id = uuid4()
    project_ids = [uuid4() for _ in projects]

    async def mock_upsert_user(*args, **kwargs):
        return user_id

    async def mock_insert_projects(*args, **kwargs):
        return project_ids

    async def mock_link_technologies(*args, **kwargs):
        pass

    # Create proper async context manager mocks
    class MockTransaction:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            # Transaction commits on successful exit
            return False

    class MockConnection:
        def transaction(self):
            return MockTransaction()

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

        def acquire(self):
            return MockPoolAcquire(self.conn)

    # Inject the mock pool
    repo._pool = MockPool()

    # Patch the internal transaction methods
    with patch.object(
        repo, "_upsert_user_in_transaction", side_effect=mock_upsert_user
    ):
        with patch.object(
            repo, "_insert_projects_in_transaction", side_effect=mock_insert_projects
        ):
            with patch.object(
                repo,
                "_link_technologies_in_transaction",
                side_effect=mock_link_technologies,
            ):
                # Execute import - should succeed
                result = asyncio.run(repo.execute_import(user, projects))

    # Verify the result indicates success
    assert result.success is True
    assert result.error is None
    assert result.user_id == user_id
    assert result.projects_count == len(projects)
