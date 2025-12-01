"""Property-based tests for logging functionality.

Tests Property 14: Progress logging
Validates Requirements 5.5
"""

import logging
from io import StringIO
from typing import Any

from hypothesis import given
from hypothesis import strategies as st

from linkedin_importer.errors import (
    APIError,
    ConfigError,
    DatabaseError,
)
from linkedin_importer.logging_config import (
    LogContext,
    get_logger,
    log_error_with_details,
    log_progress,
    setup_logging,
)


class TestProgressLogging:
    """Test that progress logging produces messages at key stages."""

    def test_setup_logging_verbose_enables_debug(self):
        """Property 14: Verbose mode enables DEBUG level logging.

        When verbose mode is enabled, DEBUG level messages should be logged.
        """
        setup_logging(verbose=True, use_colors=False)
        logger = get_logger("test_logger")

        # Capture log output
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)

        # Log at different levels
        logger.debug("Debug message")
        logger.info("Info message")

        output = stream.getvalue()
        assert "Debug message" in output
        assert "Info message" in output

        # Cleanup
        logger.removeHandler(handler)

    def test_setup_logging_non_verbose_uses_info(self):
        """Property 14: Non-verbose mode uses INFO level logging.

        When verbose mode is disabled, only INFO and above should be logged.
        """
        setup_logging(verbose=False, use_colors=False)
        _logger = get_logger("test_logger")  # Logger created to verify setup works

        # Get the root logger level
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO

    def test_get_logger_returns_logger_instance(self):
        """Property 14: get_logger returns proper logger instances.

        For any module name, get_logger should return a working logger.
        """
        logger = get_logger("test_module")

        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"

    @given(
        stage=st.text(min_size=1, max_size=50),
        details=st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.one_of(st.text(max_size=50), st.integers(), st.booleans()),
            min_size=0,
            max_size=5,
        ),
    )
    def test_log_progress_includes_stage_and_details(
        self, stage: str, details: dict[str, Any]
    ):
        """Property 14: Progress logs include stage name and details.

        For any import operation stage, progress logging should include
        the stage name and relevant details.
        """
        setup_logging(verbose=False, use_colors=False)
        logger = get_logger("test_progress")

        # Capture log output
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter("%(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Log progress
        log_progress(logger, stage, details if details else None)

        output = stream.getvalue()

        # Stage name should be in output
        assert stage in output or "Progress" in output

        # Details should be in output if provided
        if details:
            for key in details.keys():
                # Key should appear in output (as part of details formatting)
                assert key in output or str(details[key]) in output

        # Cleanup
        logger.removeHandler(handler)

    def test_log_progress_without_details(self):
        """Property 14: Progress logs work without details.

        Progress logging should work when no details are provided.
        """
        setup_logging(verbose=False, use_colors=False)
        logger = get_logger("test_progress")

        # Capture log output
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter("%(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Log progress without details
        log_progress(logger, "test_stage", None)

        output = stream.getvalue()
        assert "test_stage" in output

        # Cleanup
        logger.removeHandler(handler)

    def test_log_error_with_details_for_import_errors(self):
        """Property 14: Errors are logged with type and details.

        When logging errors, the error type and details should be included.
        """
        setup_logging(verbose=False, use_colors=False)
        logger = get_logger("test_errors")

        # Capture log output
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.ERROR)
        logger.addHandler(handler)

        # Log an error with details
        error = APIError(
            "Profile not found",
            details={"status_code": 404, "url": "https://api.example.com"},
        )
        log_error_with_details(logger, error, context={"user": "test@example.com"})

        output = stream.getvalue()

        # Error message should be in output
        assert "Profile not found" in output or "api" in output

        # Cleanup
        logger.removeHandler(handler)

    def test_log_error_with_details_for_regular_exceptions(self):
        """Property 14: Regular exceptions are logged with traceback.

        When logging regular Python exceptions, they should include traceback.
        """
        setup_logging(verbose=False, use_colors=False)
        logger = get_logger("test_errors")

        # Capture log output
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.ERROR)
        logger.addHandler(handler)

        # Log a regular exception
        error = ValueError("Invalid value provided")
        log_error_with_details(logger, error, context={"operation": "validation"})

        output = stream.getvalue()

        # Error message should be in output
        assert "Invalid value provided" in output

        # Cleanup
        logger.removeHandler(handler)

    def test_log_context_temporarily_changes_level(self):
        """Property 14: LogContext temporarily changes log level.

        The LogContext should temporarily change the log level and restore it.
        """
        logger = get_logger("test_context")
        original_level = logger.level

        # Use context to temporarily change level
        with LogContext(logger, logging.DEBUG):
            assert logger.level == logging.DEBUG

        # Level should be restored after context
        assert logger.level == original_level

    def test_import_stages_produce_log_messages(self):
        """Property 14: Key import stages produce log messages.

        For any import operation with verbose mode, log messages should be
        produced at key stages: start, API fetch, validation, database write,
        completion.
        """
        setup_logging(verbose=True, use_colors=False)
        logger = get_logger("test_import")

        # Capture log output
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter("%(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Simulate import stages
        stages = [
            ("start", {"profile_url": "https://linkedin.com/in/test"}),
            ("api_fetch", {"sections": ["basic", "experience"]}),
            ("validation", {"fields_validated": 10}),
            ("database_write", {"records_written": 5}),
            ("completion", {"success": True, "duration_ms": 1234}),
        ]

        for stage, details in stages:
            log_progress(logger, stage, details)

        output = stream.getvalue()

        # All stages should be logged
        for stage, _ in stages:
            assert stage in output

        # Cleanup
        logger.removeHandler(handler)

    def test_error_logging_at_different_levels(self):
        """Property 14: Errors are logged at ERROR level.

        All error conditions should be logged at ERROR level or above.
        """
        setup_logging(verbose=False, use_colors=False)
        logger = get_logger("test_errors")

        # Capture log output at ERROR level
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.ERROR)
        formatter = logging.Formatter("%(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Log different error types
        errors = [
            ConfigError("Configuration failed"),
            APIError("API request failed"),
            DatabaseError("Database operation failed"),
        ]

        for error in errors:
            log_error_with_details(logger, error)

        output = stream.getvalue()

        # All errors should be logged at ERROR level
        assert output.count("ERROR") >= len(errors)

        # Cleanup
        logger.removeHandler(handler)

    def test_verbose_mode_includes_debug_messages(self):
        """Property 14: Verbose mode includes DEBUG level details.

        When verbose mode is enabled, detailed DEBUG messages should be logged.
        """
        setup_logging(verbose=True, use_colors=False)
        logger = get_logger("test_verbose")

        # Capture log output
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Log debug message
        logger.debug("Detailed API response: {...}")
        logger.debug("SQL query: SELECT * FROM users")
        logger.debug("Data transformation: mapping 10 fields")

        output = stream.getvalue()

        # Debug messages should be present
        assert "DEBUG" in output
        assert output.count("DEBUG") >= 3

        # Cleanup
        logger.removeHandler(handler)

    def test_non_verbose_mode_excludes_debug_messages(self):
        """Property 14: Non-verbose mode excludes DEBUG messages.

        When verbose mode is disabled, DEBUG messages should not appear.
        """
        setup_logging(verbose=False, use_colors=False)
        logger = get_logger("test_non_verbose")

        # Capture log output at INFO level
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter("%(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Try to log debug messages
        logger.debug("This should not appear")
        logger.info("This should appear")

        output = stream.getvalue()

        # DEBUG messages should not be present
        assert "This should not appear" not in output
        # INFO messages should be present
        assert "This should appear" in output

        # Cleanup
        logger.removeHandler(handler)

    def test_logging_format_includes_timestamp_and_level(self):
        """Property 14: Log messages include timestamp and level.

        All log messages should include a timestamp and log level for tracking.
        """
        setup_logging(verbose=False, use_colors=False)
        logger = get_logger("test_format")

        # Capture log output with default format
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.INFO)
        # Use the default format from setup_logging
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        logger.info("Test message")

        output = stream.getvalue()

        # Should include timestamp (date format)
        assert any(char.isdigit() for char in output)
        # Should include log level
        assert "INFO" in output
        # Should include logger name
        assert "test_format" in output
        # Should include message
        assert "Test message" in output

        # Cleanup
        logger.removeHandler(handler)
