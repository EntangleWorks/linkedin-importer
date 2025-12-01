"""Property-based tests for environment file loading."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from dotenv import load_dotenv
from hypothesis import given, strategies as st

from linkedin_importer.config import Config, DatabaseConfig, LinkedInConfig


# Strategy for generating valid environment variable values
# Use alphanumeric + common safe characters to avoid .env parsing issues
valid_text = st.text(
    min_size=1,
    max_size=50,
    alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Nd"),  # Letters and digits only
    )
).filter(lambda x: len(x) > 0)


# Feature: linkedin-profile-importer, Property 9: Environment file loading
# Validates: Requirements 2.5
@given(
    db_name=valid_text,
    db_user=valid_text,
    db_password=valid_text,
    api_key=valid_text,
    api_secret=valid_text,
)
def test_env_file_loading(
    db_name: str,
    db_user: str,
    db_password: str,
    api_key: str,
    api_secret: str,
) -> None:
    """For any valid environment file, all configuration parameters should be loaded."""
    # Create a temporary .env file
    with tempfile.TemporaryDirectory() as tmpdir:
        env_file = Path(tmpdir) / ".env"
        env_content = f"""DB_NAME={db_name}
DB_USER={db_user}
DB_PASSWORD={db_password}
LINKEDIN_API_KEY={api_key}
LINKEDIN_API_SECRET={api_secret}
"""
        env_file.write_text(env_content)
        
        # Load the .env file and verify values are accessible
        with patch.dict(os.environ, {}, clear=True):
            # Load from the specific file
            load_dotenv(env_file)
            
            # Verify environment variables were loaded
            assert os.getenv("DB_NAME") == db_name
            assert os.getenv("DB_USER") == db_user
            assert os.getenv("DB_PASSWORD") == db_password
            assert os.getenv("LINKEDIN_API_KEY") == api_key
            assert os.getenv("LINKEDIN_API_SECRET") == api_secret
            
            # Now create config using these loaded values
            config = Config(
                database=DatabaseConfig(
                    url=None,
                    host="localhost",
                    port=5432,
                    name=os.getenv("DB_NAME", ""),
                    user=os.getenv("DB_USER", ""),
                    password=os.getenv("DB_PASSWORD", ""),
                ),
                linkedin=LinkedInConfig(
                    api_key=os.getenv("LINKEDIN_API_KEY", ""),
                    api_secret=os.getenv("LINKEDIN_API_SECRET", ""),
                ),
                profile_url="https://linkedin.com/in/test",
                verbose=False,
            )
            
            # All values from .env file should be loaded
            assert config.database.name == db_name
            assert config.database.user == db_user
            assert config.database.password == db_password
            assert config.linkedin.api_key == api_key
            assert config.linkedin.api_secret == api_secret


# Feature: linkedin-profile-importer, Property 9: Environment file loading
# Validates: Requirements 2.5
@given(
    db_host=valid_text,
    db_port=st.integers(min_value=1, max_value=65535),
)
def test_env_file_with_optional_params(db_host: str, db_port: int) -> None:
    """For any valid environment file with optional parameters, they should be loaded correctly."""
    # Create a temporary .env file with optional parameters
    with tempfile.TemporaryDirectory() as tmpdir:
        env_file = Path(tmpdir) / ".env"
        env_content = f"""DB_NAME=testdb
DB_USER=testuser
DB_PASSWORD=testpass
DB_HOST={db_host}
DB_PORT={db_port}
LINKEDIN_API_KEY=test_key
LINKEDIN_API_SECRET=test_secret
"""
        env_file.write_text(env_content)
        
        # Load the .env file and verify values are accessible
        with patch.dict(os.environ, {}, clear=True):
            load_dotenv(env_file)
            
            # Verify optional environment variables were loaded
            assert os.getenv("DB_HOST") == db_host
            assert os.getenv("DB_PORT") == str(db_port)
            
            # Create config using these loaded values
            config = Config(
                database=DatabaseConfig(
                    url=None,
                    host=os.getenv("DB_HOST", "localhost"),
                    port=int(os.getenv("DB_PORT", "5432")),
                    name=os.getenv("DB_NAME", ""),
                    user=os.getenv("DB_USER", ""),
                    password=os.getenv("DB_PASSWORD", ""),
                ),
                linkedin=LinkedInConfig(
                    api_key=os.getenv("LINKEDIN_API_KEY", ""),
                    api_secret=os.getenv("LINKEDIN_API_SECRET", ""),
                ),
                profile_url="https://linkedin.com/in/test",
                verbose=False,
            )
            
            # Optional values from .env file should be loaded
            assert config.database.host == db_host
            assert config.database.port == db_port


# Feature: linkedin-profile-importer, Property 9: Environment file loading
# Validates: Requirements 2.5
def test_env_file_with_database_url() -> None:
    """When environment file contains DATABASE_URL, it should be loaded and used."""
    db_url = "postgresql://user:pass@host:5432/dbname"
    
    # Create a temporary .env file
    with tempfile.TemporaryDirectory() as tmpdir:
        env_file = Path(tmpdir) / ".env"
        env_content = f"""DATABASE_URL={db_url}
LINKEDIN_API_KEY=test_key
LINKEDIN_API_SECRET=test_secret
"""
        env_file.write_text(env_content)
        
        # Load the .env file and verify values are accessible
        with patch.dict(os.environ, {}, clear=True):
            load_dotenv(env_file)
            
            # Verify DATABASE_URL was loaded
            assert os.getenv("DATABASE_URL") == db_url
            
            # Create config using the loaded DATABASE_URL
            config = Config(
                database=DatabaseConfig(
                    url=os.getenv("DATABASE_URL"),
                    host="localhost",
                    port=5432,
                    name="dummy",  # Not used when URL is provided
                    user="dummy",
                    password="dummy",
                ),
                linkedin=LinkedInConfig(
                    api_key=os.getenv("LINKEDIN_API_KEY", ""),
                    api_secret=os.getenv("LINKEDIN_API_SECRET", ""),
                ),
                profile_url="https://linkedin.com/in/test",
                verbose=False,
            )
            
            # DATABASE_URL should be loaded
            assert config.database.url == db_url
