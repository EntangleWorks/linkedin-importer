"""Property-based tests for error handling.

Tests Property 5: Error message descriptiveness
Validates Requirements 1.5, 5.1, 5.4
"""

from datetime import datetime
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from linkedin_importer.errors import (
    APIError,
    AuthError,
    ConfigError,
    DatabaseError,
    ImportError,
    ValidationError,
)

# Strategy for generating error messages
error_messages = st.text(min_size=1, max_size=200)

# Strategy for generating error details
error_details = st.dictionaries(
    keys=st.text(min_size=1, max_size=50),
    values=st.one_of(
        st.text(max_size=100),
        st.integers(),
        st.booleans(),
        st.none(),
    ),
    min_size=0,
    max_size=10,
)


class TestErrorMessageDescriptiveness:
    """Test that error messages are descriptive and include necessary details."""

    @given(message=error_messages, details=error_details)
    def test_base_import_error_includes_type_and_message(
        self, message: str, details: dict[str, Any]
    ):
        """Property 5: Base ImportError includes error type and message.

        For any error condition, the error message should include
        the error type and specific details about what failed.
        """
        error_type = "test_error"
        error = ImportError(error_type=error_type, message=message, details=details)

        # Error should have all required attributes
        assert error.error_type == error_type
        assert error.message == message
        assert error.details == details
        assert isinstance(error.timestamp, datetime)

        # String representation should include error type
        error_str = str(error)
        assert error_type in error_str
        assert message in error_str

    @given(message=error_messages, details=error_details)
    def test_config_error_has_descriptive_type(
        self, message: str, details: dict[str, Any]
    ):
        """Property 5: ConfigError has descriptive error type.

        Configuration errors should be clearly identifiable by type.
        """
        error = ConfigError(message=message, details=details)

        assert error.error_type == "config"
        assert error.message == message
        assert error.details == details
        assert isinstance(error.timestamp, datetime)

        error_str = str(error)
        assert "config" in error_str
        assert message in error_str

    @given(message=error_messages, details=error_details)
    def test_auth_error_has_descriptive_type(
        self, message: str, details: dict[str, Any]
    ):
        """Property 5: AuthError has descriptive error type.

        Authentication errors should be clearly identifiable by type.
        """
        error = AuthError(message=message, details=details)

        assert error.error_type == "auth"
        assert error.message == message
        assert error.details == details
        assert isinstance(error.timestamp, datetime)

        error_str = str(error)
        assert "auth" in error_str
        assert message in error_str

    @given(message=error_messages, details=error_details)
    def test_api_error_has_descriptive_type(
        self, message: str, details: dict[str, Any]
    ):
        """Property 5: APIError has descriptive error type.

        API errors should be clearly identifiable by type.
        """
        error = APIError(message=message, details=details)

        assert error.error_type == "api"
        assert error.message == message
        assert error.details == details
        assert isinstance(error.timestamp, datetime)

        error_str = str(error)
        assert "api" in error_str
        assert message in error_str

    @given(message=error_messages, details=error_details)
    def test_validation_error_has_descriptive_type(
        self, message: str, details: dict[str, Any]
    ):
        """Property 5: ValidationError has descriptive error type.

        Validation errors should be clearly identifiable by type.
        """
        error = ValidationError(message=message, details=details)

        assert error.error_type == "validation"
        assert error.message == message
        assert error.details == details
        assert isinstance(error.timestamp, datetime)

        error_str = str(error)
        assert "validation" in error_str
        assert message in error_str

    @given(message=error_messages, details=error_details)
    def test_database_error_has_descriptive_type(
        self, message: str, details: dict[str, Any]
    ):
        """Property 5: DatabaseError has descriptive error type.

        Database errors should be clearly identifiable by type.
        """
        error = DatabaseError(message=message, details=details)

        assert error.error_type == "database"
        assert error.message == message
        assert error.details == details
        assert isinstance(error.timestamp, datetime)

        error_str = str(error)
        assert "database" in error_str
        assert message in error_str

    def test_error_details_are_preserved(self):
        """Property 5: Error details are preserved and accessible.

        For any error with details, those details should be accessible
        for debugging and logging purposes.
        """
        details = {
            "status_code": 404,
            "url": "https://api.linkedin.com/v2/me",
            "response": "Profile not found",
        }
        error = APIError(message="Failed to fetch profile", details=details)

        assert error.details["status_code"] == 404
        assert error.details["url"] == "https://api.linkedin.com/v2/me"
        assert error.details["response"] == "Profile not found"

    def test_error_without_details_has_empty_dict(self):
        """Property 5: Errors without details have empty dict.

        When no details are provided, the error should have an empty
        details dictionary (not None) for consistent access patterns.
        """
        error = ConfigError(message="Missing required configuration")

        assert error.details is not None
        assert isinstance(error.details, dict)
        assert len(error.details) == 0

    def test_error_timestamp_is_recent(self):
        """Property 5: Error timestamp reflects creation time.

        Error timestamps should be set when the error is created,
        allowing for temporal tracking of errors.
        """
        before = datetime.now()
        error = DatabaseError(message="Connection failed")
        after = datetime.now()

        assert before <= error.timestamp <= after

    @given(message=error_messages)
    def test_all_error_types_are_exceptions(self, message: str):
        """Property 5: All error types are proper exceptions.

        All error classes should be proper Exception subclasses
        that can be raised and caught.
        """
        errors = [
            ConfigError(message),
            AuthError(message),
            APIError(message),
            ValidationError(message),
            DatabaseError(message),
        ]

        for error in errors:
            assert isinstance(error, Exception)
            assert isinstance(error, ImportError)

            # Should be raisable and catchable
            with pytest.raises(ImportError):
                raise error

    def test_config_error_examples(self):
        """Property 5: ConfigError examples are descriptive.

        Real-world configuration error messages should be clear
        and actionable.
        """
        examples = [
            ConfigError(
                "Missing required environment variable: DATABASE_URL",
                {"variable": "DATABASE_URL"},
            ),
            ConfigError(
                "Invalid database port: must be between 1 and 65535",
                {"provided_port": 99999},
            ),
            ConfigError(
                "Invalid API endpoint URL format",
                {"url": "not-a-valid-url", "error": "Missing scheme"},
            ),
        ]

        for error in examples:
            # Each error should have meaningful message
            assert len(error.message) > 10
            # Error type should be identifiable
            assert error.error_type == "config"
            # Details should provide context
            assert len(error.details) > 0

    def test_api_error_examples(self):
        """Property 5: APIError examples are descriptive.

        Real-world API error messages should include response details.
        """
        examples = [
            APIError(
                "Profile not found",
                {
                    "status_code": 404,
                    "url": "https://api.linkedin.com/v2/me",
                },
            ),
            APIError(
                "Rate limit exceeded",
                {
                    "status_code": 429,
                    "retry_after": 60,
                    "remaining": 0,
                },
            ),
            APIError(
                "API quota exhausted",
                {
                    "status_code": 403,
                    "quota_type": "daily",
                    "reset_time": "2024-01-01T00:00:00Z",
                },
            ),
        ]

        for error in examples:
            # Each error should have meaningful message
            assert len(error.message) > 5
            # Error type should be identifiable
            assert error.error_type == "api"
            # Details should include status code
            assert "status_code" in error.details

    def test_database_error_examples(self):
        """Property 5: DatabaseError examples are descriptive.

        Real-world database error messages should include operation context.
        """
        examples = [
            DatabaseError(
                "Failed to connect to database",
                {
                    "host": "localhost",
                    "port": 5432,
                    "error": "Connection refused",
                },
            ),
            DatabaseError(
                "Transaction rollback failed",
                {
                    "operation": "import_profile",
                    "user_id": "123e4567-e89b-12d3-a456-426614174000",
                },
            ),
            DatabaseError(
                "Unique constraint violation",
                {
                    "constraint": "users_email_key",
                    "value": "test@example.com",
                },
            ),
        ]

        for error in examples:
            # Each error should have meaningful message
            assert len(error.message) > 10
            # Error type should be identifiable
            assert error.error_type == "database"
            # Details should provide context
            assert len(error.details) > 0

    def test_validation_error_examples(self):
        """Property 5: ValidationError examples are descriptive.

        Real-world validation error messages should specify what failed.
        """
        examples = [
            ValidationError(
                "Missing required field: email",
                {"field": "email", "provided": None},
            ),
            ValidationError(
                "Invalid email format",
                {"field": "email", "value": "not-an-email"},
            ),
            ValidationError(
                "Invalid date range: end_date before start_date",
                {"start_date": "2024-01-01", "end_date": "2023-01-01"},
            ),
        ]

        for error in examples:
            # Each error should have meaningful message
            assert len(error.message) > 10
            # Error type should be identifiable
            assert error.error_type == "validation"
            # Details should specify what failed
            assert len(error.details) > 0
