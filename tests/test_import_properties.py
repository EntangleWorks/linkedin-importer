"""Property-based tests for import orchestration."""

import asyncio
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from linkedin_importer.config import AuthConfig, Config, DatabaseConfig
from linkedin_importer.db_models import ProjectData, UserData
from linkedin_importer.models import LinkedInProfile
from linkedin_importer.orchestrator import import_profile
from linkedin_importer.repository import ImportResult


# Property 4: Success status completeness
# For any successful import, the returned status SHALL include:
# user_id, email, projects_count, technologies_count
@given(
    first_name=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
    last_name=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
    email=st.emails(),
    projects_count=st.integers(min_value=0, max_value=10),
    technologies_count=st.integers(min_value=0, max_value=20),
)
@settings(max_examples=20, deadline=None)
def test_success_status_completeness(
    first_name: str,
    last_name: str,
    email: str,
    projects_count: int,
    technologies_count: int,
):
    """Property 4: Success status completeness.

    For any successful import, the returned ImportResult SHALL include:
    - success = True
    - user_id (non-None UUID)
    - projects_count (number of projects imported)
    - technologies_count (number of technologies linked)
    - error = None

    This validates Requirements 1.4 (return success status with summary).
    """
    # Arrange: Create mock config with scraper auth
    config = Config(
        database=DatabaseConfig(
            host="localhost",
            port=5432,
            name="testdb",
            user="testuser",
            password="testpass",
        ),
        auth=AuthConfig(
            cookie="test_li_at_cookie",
        ),
        profile_url="https://www.linkedin.com/in/testuser",
        profile_email=email,
        verbose=False,
    )

    # Mock user_id
    mock_user_id = uuid4()

    # Create mock profile
    mock_profile = MagicMock(spec=LinkedInProfile)
    mock_profile.first_name = first_name
    mock_profile.last_name = last_name
    mock_profile.email = email
    mock_profile.headline = "Test Headline"
    mock_profile.summary = "Test Summary"
    mock_profile.positions = []
    mock_profile.education = []
    mock_profile.skills = []

    # Mock user and project data
    mock_user_data = UserData(
        email=email,
        name=f"{first_name} {last_name}",
        avatar_url=None,
        bio=None,
    )

    mock_projects = [
        ProjectData(
            title=f"Project {i}",
            description=f"Description {i}",
            slug=f"project-{i}",
        )
        for i in range(projects_count)
    ]

    # Mock successful import result
    mock_import_result = ImportResult(
        success=True,
        user_id=mock_user_id,
        projects_count=projects_count,
        technologies_count=technologies_count,
        error=None,
    )

    # Act: Run import with mocks
    with (
        patch(
            "linkedin_importer.orchestrator.LinkedInScraperClient"
        ) as MockScraperClient,
        patch(
            "linkedin_importer.orchestrator.convert_person_to_profile"
        ) as mock_convert,
        patch("linkedin_importer.orchestrator.map_profile_to_database") as mock_mapper,
        patch(
            "linkedin_importer.orchestrator.TransactionalRepository"
        ) as MockRepository,
    ):
        # Configure scraper client mock
        mock_scraper_instance = MagicMock()
        mock_scraper_instance.get_driver_info.return_value = {"chrome_version": "120"}
        mock_scraper_instance.authenticate.return_value = True
        mock_scraper_instance.get_profile.return_value = (
            MagicMock()
        )  # linkedin_scraper Person
        mock_scraper_instance.close.return_value = None
        MockScraperClient.return_value = mock_scraper_instance

        # Configure conversion mock
        mock_convert.return_value = mock_profile

        # Configure mapper mock - returns 6 values now
        mock_mapper.return_value = (mock_user_data, mock_projects, [], [], [], [])

        # Configure repository mock
        mock_repo_instance = AsyncMock()
        mock_repo_instance.connect = AsyncMock()
        mock_repo_instance.execute_import = AsyncMock(return_value=mock_import_result)
        mock_repo_instance._pool = None
        MockRepository.return_value = mock_repo_instance

        # Execute import
        result = asyncio.run(import_profile(config))

    # Assert: Verify success status completeness
    assert result.success is True, "Success status must be True for successful imports"
    assert result.user_id is not None, "User ID must be present in success result"
    assert isinstance(result.user_id, type(mock_user_id)), "User ID must be a UUID"
    assert result.projects_count == projects_count, (
        f"Projects count must match imported count: expected {projects_count}, got {result.projects_count}"
    )
    assert result.technologies_count == technologies_count, (
        f"Technologies count must match: expected {technologies_count}, got {result.technologies_count}"
    )
    assert result.error is None, "Error must be None for successful imports"


# Property 10: Standalone operation
# The tool SHALL run without dependencies on the main portfolio application
@pytest.mark.skipif(
    os.getenv("SKIP_STANDALONE_TEST") == "1",
    reason="Standalone test disabled via environment variable",
)
def test_standalone_operation():
    """Property 10: Standalone operation.

    The tool SHALL:
    - Run as a standalone CLI application
    - Not require the main portfolio application to be running
    - Be executable via command line with proper arguments
    - Return appropriate exit codes (0 for success, non-zero for failure)

    This validates Requirements 3.5 (standalone CLI tool).
    """
    # Arrange: Find the CLI script path
    project_root = Path(__file__).parent.parent
    cli_script = project_root / "src" / "linkedin_importer" / "cli.py"

    assert cli_script.exists(), f"CLI script not found at {cli_script}"

    # Test 1: CLI should be executable via Python
    result = subprocess.run(
        [sys.executable, "-m", "linkedin_importer.cli", "--help"],
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=10,
    )

    # Assert: Help command should succeed
    assert result.returncode == 0, (
        f"CLI help command failed with exit code {result.returncode}\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    assert "PROFILE_URL" in result.stdout or "profile" in result.stdout.lower(), (
        "Help output should mention PROFILE_URL argument"
    )

    # Test 2: CLI should fail gracefully with missing arguments
    result_no_args = subprocess.run(
        [sys.executable, "-m", "linkedin_importer.cli"],
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=10,
    )

    # Assert: Should fail with non-zero exit code when missing required args
    assert result_no_args.returncode != 0, (
        "CLI should fail when required arguments are missing"
    )

    # Test 3: CLI should be importable without main app context
    result_import = subprocess.run(
        [
            sys.executable,
            "-c",
            "import linkedin_importer.cli; import linkedin_importer.orchestrator; print('SUCCESS')",
        ],
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=10,
    )

    # Assert: Import should succeed
    assert result_import.returncode == 0, (
        f"CLI modules should be importable without main app\n"
        f"stdout: {result_import.stdout}\n"
        f"stderr: {result_import.stderr}"
    )
    assert "SUCCESS" in result_import.stdout, "Import test should print SUCCESS"


# Test: Missing auth config returns error
def test_missing_auth_config_returns_error():
    """When no auth config is provided, import should return an error."""
    # Arrange: Create config without auth
    config = Config(
        database=DatabaseConfig(
            host="localhost",
            port=5432,
            name="testdb",
            user="testuser",
            password="testpass",
        ),
        profile_url="https://www.linkedin.com/in/testuser",
        verbose=False,
    )

    # Act: Execute import
    result = asyncio.run(import_profile(config))

    # Assert: Should fail with appropriate error
    assert result.success is False
    assert result.error is not None
    assert "authentication" in result.error.lower() or "cookie" in result.error.lower()


# Test: Missing profile email returns error
def test_missing_profile_email_returns_error():
    """When profile_email is not provided with auth, import should return an error."""
    # Arrange: Create config with auth but without profile_email
    # Note: We need to bypass Pydantic validation to test orchestrator behavior
    config = Config(
        database=DatabaseConfig(
            host="localhost",
            port=5432,
            name="testdb",
            user="testuser",
            password="testpass",
        ),
        auth=AuthConfig(
            cookie="test_cookie",
        ),
        profile_url="https://www.linkedin.com/in/testuser",
        profile_email="test@example.com",  # Required by Pydantic
        verbose=False,
    )
    # Manually set profile_email to None to test orchestrator validation
    object.__setattr__(config, "profile_email", None)

    # Act: Execute import
    result = asyncio.run(import_profile(config))

    # Assert: Should fail with appropriate error
    assert result.success is False
    assert result.error is not None
    assert "profile_email" in result.error.lower() or "email" in result.error.lower()


# Additional test: Verify error cases return proper ImportResult
@given(
    error_type=st.sampled_from(
        ["scraper", "auth", "database", "validation", "unknown"]
    ),
    error_message=st.text(min_size=10, max_size=100),
)
@settings(max_examples=10, deadline=None)
def test_error_cases_return_proper_result(error_type: str, error_message: str):
    """Property: Error cases return proper ImportResult.

    For any error during import, the returned ImportResult SHALL include:
    - success = False
    - error (descriptive error message)
    - user_id = None
    - projects_count = 0
    - technologies_count = 0

    This validates Requirements 1.5 (descriptive error messages).
    """
    # Arrange: Create mock config with scraper auth
    config = Config(
        database=DatabaseConfig(
            host="localhost",
            port=5432,
            name="testdb",
            user="testuser",
            password="testpass",
        ),
        auth=AuthConfig(
            cookie="test_cookie",
        ),
        profile_url="https://www.linkedin.com/in/testuser",
        profile_email="test@example.com",
        verbose=False,
    )

    # Act: Simulate error based on type
    with patch(
        "linkedin_importer.orchestrator.LinkedInScraperClient"
    ) as MockScraperClient:
        # Configure scraper mock to raise appropriate error
        mock_scraper_instance = MagicMock()
        mock_scraper_instance.get_driver_info.return_value = {"chrome_version": "120"}

        if error_type == "auth":
            from linkedin_importer.scraper_errors import ScraperAuthError

            mock_scraper_instance.authenticate.side_effect = ScraperAuthError(
                message=error_message
            )
        elif error_type == "scraper":
            from linkedin_importer.scraper_errors import ScraperError

            mock_scraper_instance.authenticate.return_value = True
            mock_scraper_instance.get_profile.side_effect = ScraperError(
                message=error_message
            )
        elif error_type in ["database", "validation", "unknown"]:
            # For these, we'll simulate generic exception during scraping
            mock_scraper_instance.authenticate.return_value = True
            mock_scraper_instance.get_profile.side_effect = Exception(error_message)

        mock_scraper_instance.close.return_value = None
        MockScraperClient.return_value = mock_scraper_instance

        # Execute import
        result = asyncio.run(import_profile(config))

    # Assert: Verify error result structure
    assert result.success is False, "Success must be False for error cases"
    assert result.error is not None, "Error message must be present"
    assert isinstance(result.error, str), "Error must be a string"
    assert len(result.error) > 0, "Error message must not be empty"
    assert result.user_id is None, "User ID must be None for failed imports"
    assert result.projects_count == 0, "Projects count must be 0 for failed imports"
    assert result.technologies_count == 0, (
        "Technologies count must be 0 for failed imports"
    )
