"""Database repository for LinkedIn profile import operations."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

import asyncpg
from asyncpg.pool import Pool

from .config import DatabaseConfig
from .db_models import ProjectData, UserData
from .errors import DatabaseError
from .logging_config import get_logger, log_error_with_details

logger = get_logger(__name__)


class DatabaseRepository:
    """Repository for database operations with connection pooling."""

    def __init__(self, config: DatabaseConfig):
        """Initialize repository with database configuration.

        Args:
            config: Database configuration
        """
        self.config = config
        self._pool: Optional[Pool] = None

    async def connect(self, max_retries: int = 3) -> None:
        """Establish database connection pool with retry logic.

        Args:
            max_retries: Maximum number of connection attempts

        Raises:
            DatabaseError: If connection fails after all retries
        """
        retry_count = 0
        last_error = None
        logger.info(
            f"Connecting to database: {self.config.host}:{self.config.port}/{self.config.name}"
        )

        while retry_count < max_retries:
            try:
                # Build connection string
                if self.config.url:
                    dsn = self.config.url
                else:
                    dsn = (
                        f"postgresql://{self.config.user}:{self.config.password}"
                        f"@{self.config.host}:{self.config.port}/{self.config.name}"
                    )

                # Create connection pool
                self._pool = await asyncpg.create_pool(
                    dsn=dsn,
                    min_size=1,
                    max_size=10,
                    command_timeout=60,
                )

                # Test connection
                async with self._pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")

                return

            except Exception as e:
                last_error = e
                retry_count += 1
                if retry_count < max_retries:
                    # Wait before retry (exponential backoff)
                    import asyncio

                    await asyncio.sleep(2**retry_count)

        # All retries failed
        error = DatabaseError(
            f"Failed to connect to database after {max_retries} attempts",
            details={"error": str(last_error)},
        )
        log_error_with_details(logger, error)
        raise error

    async def close(self) -> None:
        """Close database connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def upsert_user(self, user_data: UserData) -> UUID:
        """Insert or update user record by email.

        Args:
            user_data: User data to insert or update

        Returns:
            UUID of the inserted or updated user

        Raises:
            DatabaseError: If database operation fails
        """
        if not self._pool:
            raise DatabaseError(
                message="Database connection not established",
                details={"operation": "upsert_user"},
            )

        try:
            async with self._pool.acquire() as conn:
                # Generate UUID if not provided
                user_id = user_data.id or uuid4()
                now = datetime.utcnow()

                # Upsert user (insert or update on conflict)
                query = """
                    INSERT INTO users (id, email, password_hash, name, bio, avatar_url, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (email)
                    DO UPDATE SET
                        name = EXCLUDED.name,
                        bio = EXCLUDED.bio,
                        avatar_url = EXCLUDED.avatar_url,
                        updated_at = EXCLUDED.updated_at
                    RETURNING id
                """

                result = await conn.fetchval(
                    query,
                    user_id,
                    user_data.email,
                    user_data.password_hash,
                    user_data.name,
                    user_data.bio,
                    user_data.avatar_url,
                    now,
                    now,
                )

                return result

        except Exception as e:
            raise DatabaseError(
                message="Failed to upsert user",
                details={"email": user_data.email, "error": str(e)},
            )

    def _generate_slug(self, title: str) -> str:
        """Generate URL-friendly slug from title.

        Args:
            title: Project title

        Returns:
            URL-friendly slug
        """
        import re

        # Convert to lowercase
        slug = title.lower()

        # Replace spaces and special characters with hyphens
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[-\s]+", "-", slug)

        # Remove leading/trailing hyphens
        slug = slug.strip("-")

        # Limit length
        return slug[:255]

    async def _ensure_unique_slug(self, conn, base_slug: str) -> str:
        """Ensure slug is unique by appending number if needed.

        Args:
            conn: Database connection
            base_slug: Base slug to check

        Returns:
            Unique slug
        """
        slug = base_slug
        counter = 1

        while True:
            # Check if slug exists
            exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM projects WHERE slug = $1)",
                slug,
            )

            if not exists:
                return slug

            # Try next variant
            slug = f"{base_slug}-{counter}"
            counter += 1

    async def insert_projects(self, projects: list[ProjectData]) -> list[UUID]:
        """Insert multiple project records.

        Args:
            projects: List of project data to insert

        Returns:
            List of UUIDs for inserted projects

        Raises:
            DatabaseError: If database operation fails
        """
        if not self._pool:
            raise DatabaseError(
                message="Database connection not established",
                details={"operation": "insert_projects"},
            )

        try:
            async with self._pool.acquire() as conn:
                project_ids = []

                for project in projects:
                    # Generate unique slug
                    base_slug = self._generate_slug(project.slug or project.title)
                    unique_slug = await self._ensure_unique_slug(conn, base_slug)

                    # Generate UUID if not provided
                    project_id = project.id or uuid4()
                    now = datetime.utcnow()

                    # Use provided timestamps or default to now
                    created_at = project.created_at or now
                    updated_at = project.updated_at or now

                    # Insert project
                    query = """
                        INSERT INTO projects (
                            id, slug, title, description, long_description,
                            image_url, live_url, github_url, featured,
                            created_at, updated_at
                        )
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                        RETURNING id
                    """

                    result = await conn.fetchval(
                        query,
                        project_id,
                        unique_slug,
                        project.title,
                        project.description,
                        project.long_description,
                        project.image_url,
                        project.live_url,
                        project.github_url,
                        project.featured,
                        created_at,
                        updated_at,
                    )

                    project_ids.append(result)

                return project_ids

        except Exception as e:
            raise DatabaseError(
                message="Failed to insert projects",
                details={"count": len(projects), "error": str(e)},
            )

    def _normalize_technology(self, tech: str) -> str:
        """Normalize technology name.

        Args:
            tech: Technology name

        Returns:
            Normalized technology name
        """
        # Trim whitespace and convert to title case
        normalized = tech.strip()

        # Limit length to match database constraint
        return normalized[:100]

    async def link_technologies(
        self, project_id: UUID, technologies: list[str]
    ) -> None:
        """Link technologies to a project.

        Args:
            project_id: Project UUID
            technologies: List of technology names

        Raises:
            DatabaseError: If database operation fails
        """
        if not self._pool:
            raise DatabaseError(
                message="Database connection not established",
                details={"operation": "link_technologies"},
            )

        if not technologies:
            return

        try:
            async with self._pool.acquire() as conn:
                # Normalize and deduplicate technologies
                normalized_techs = list(
                    set(
                        self._normalize_technology(tech)
                        for tech in technologies
                        if tech and tech.strip()
                    )
                )

                # Insert technology links
                query = """
                    INSERT INTO project_technologies (project_id, technology)
                    VALUES ($1, $2)
                    ON CONFLICT (project_id, technology) DO NOTHING
                """

                for tech in normalized_techs:
                    await conn.execute(query, project_id, tech)

        except Exception as e:
            raise DatabaseError(
                message="Failed to link technologies",
                details={"project_id": str(project_id), "error": str(e)},
            )


@dataclass
class ImportResult:
    """Result of a profile import operation."""

    success: bool
    user_id: Optional[UUID] = None
    projects_count: int = 0
    technologies_count: int = 0
    error: Optional[str] = None


class TransactionalRepository(DatabaseRepository):
    """Repository with transactional import support."""

    async def execute_import(
        self, user_data: UserData, projects: list[ProjectData]
    ) -> ImportResult:
        """Execute full import in a transaction.

        All operations are wrapped in a transaction. If any operation fails,
        all changes are rolled back.

        Args:
            user_data: User data to import
            projects: List of projects to import

        Returns:
            ImportResult with success status and summary

        Raises:
            DatabaseError: If database operation fails
        """
        if not self._pool:
            raise DatabaseError(
                message="Database connection not established",
                details={"operation": "execute_import"},
            )

        try:
            async with self._pool.acquire() as conn:
                # Start transaction
                async with conn.transaction():
                    # 1. Upsert user
                    user_id = await self._upsert_user_in_transaction(conn, user_data)

                    # 2. Insert projects
                    project_ids = await self._insert_projects_in_transaction(
                        conn, projects
                    )

                    # 3. Link technologies to projects
                    total_techs = 0
                    for project, project_id in zip(projects, project_ids):
                        if project.technologies:
                            await self._link_technologies_in_transaction(
                                conn, project_id, project.technologies
                            )
                            total_techs += len(set(project.technologies))

                    # Transaction commits automatically if no exception
                    return ImportResult(
                        success=True,
                        user_id=user_id,
                        projects_count=len(project_ids),
                        technologies_count=total_techs,
                    )

        except Exception as e:
            # Transaction automatically rolls back on exception
            return ImportResult(
                success=False,
                error=str(e),
            )

    async def _upsert_user_in_transaction(self, conn, user_data: UserData) -> UUID:
        """Upsert user within a transaction."""
        user_id = user_data.id or uuid4()
        now = datetime.utcnow()

        query = """
            INSERT INTO users (id, email, password_hash, name, bio, avatar_url, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (email)
            DO UPDATE SET
                name = EXCLUDED.name,
                bio = EXCLUDED.bio,
                avatar_url = EXCLUDED.avatar_url,
                updated_at = EXCLUDED.updated_at
            RETURNING id
        """

        return await conn.fetchval(
            query,
            user_id,
            user_data.email,
            user_data.password_hash,
            user_data.name,
            user_data.bio,
            user_data.avatar_url,
            now,
            now,
        )

    async def _insert_projects_in_transaction(
        self, conn, projects: list[ProjectData]
    ) -> list[UUID]:
        """Insert projects within a transaction."""
        project_ids = []

        for project in projects:
            # Generate unique slug
            base_slug = self._generate_slug(project.slug or project.title)
            unique_slug = await self._ensure_unique_slug(conn, base_slug)

            # Generate UUID if not provided
            project_id = project.id or uuid4()
            now = datetime.utcnow()

            # Use provided timestamps or default to now
            created_at = project.created_at or now
            updated_at = project.updated_at or now

            # Insert project
            query = """
                INSERT INTO projects (
                    id, slug, title, description, long_description,
                    image_url, live_url, github_url, featured,
                    created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                RETURNING id
            """

            result = await conn.fetchval(
                query,
                project_id,
                unique_slug,
                project.title,
                project.description,
                project.long_description,
                project.image_url,
                project.live_url,
                project.github_url,
                project.featured,
                created_at,
                updated_at,
            )

            project_ids.append(result)

        return project_ids

    async def _link_technologies_in_transaction(
        self, conn, project_id: UUID, technologies: list[str]
    ) -> None:
        """Link technologies within a transaction."""
        if not technologies:
            return

        # Normalize and deduplicate technologies
        normalized_techs = list(
            set(
                self._normalize_technology(tech)
                for tech in technologies
                if tech and tech.strip()
            )
        )

        # Insert technology links
        query = """
            INSERT INTO project_technologies (project_id, technology)
            VALUES ($1, $2)
            ON CONFLICT (project_id, technology) DO NOTHING
        """

        for tech in normalized_techs:
            await conn.execute(query, project_id, tech)
