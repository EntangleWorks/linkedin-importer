"""Logging configuration for LinkedIn Profile Importer."""

import logging
import sys
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """Custom formatter with color support for console output."""

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"
    BOLD = "\033[1m"

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        # Add color to level name
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[levelname]}{self.BOLD}{levelname}{self.RESET}"
            )

        # Format the message
        formatted = super().format(record)

        # Reset levelname for subsequent formatters
        record.levelname = levelname

        return formatted


def setup_logging(verbose: bool = False, use_colors: bool = True) -> None:
    """Configure logging for the application.

    Args:
        verbose: Enable DEBUG level logging if True, otherwise INFO level
        use_colors: Use colored output for console if True

    Logging Levels:
        ERROR: All failures and exceptions
        WARNING: Rate limiting, retries, validation warnings
        INFO: Progress milestones (start, fetch, validation, import complete)
        DEBUG: Detailed API responses, SQL queries, data transformations
    """
    # Determine log level
    level = logging.DEBUG if verbose else logging.INFO

    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    # Create formatter
    if use_colors and sys.stdout.isatty():
        formatter = ColoredFormatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Set specific log levels for noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("asyncpg").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module.

    Args:
        name: Name of the logger (usually __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class LogContext:
    """Context manager for temporary log level changes."""

    def __init__(self, logger: logging.Logger, level: int):
        """Initialize log context.

        Args:
            logger: Logger to modify
            level: New log level
        """
        self.logger = logger
        self.new_level = level
        self.old_level: Optional[int] = None

    def __enter__(self) -> "LogContext":
        """Enter context and change log level."""
        self.old_level = self.logger.level
        self.logger.setLevel(self.new_level)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context and restore log level."""
        if self.old_level is not None:
            self.logger.setLevel(self.old_level)


def log_error_with_details(
    logger: logging.Logger,
    error: Exception,
    context: Optional[dict] = None,
) -> None:
    """Log an error with detailed information.

    Args:
        logger: Logger instance
        error: Exception to log
        context: Additional context information
    """
    error_msg = str(error)

    # Check if it's our custom ImportError with details
    if hasattr(error, "error_type") and hasattr(error, "details"):
        logger.error(
            f"[{error.error_type}] {error_msg}",
            extra={"error_details": error.details, "context": context or {}},
        )
    else:
        logger.error(error_msg, extra={"context": context or {}}, exc_info=True)


def log_progress(
    logger: logging.Logger,
    stage: str,
    details: Optional[dict] = None,
) -> None:
    """Log progress information at a specific stage.

    Args:
        logger: Logger instance
        stage: Name of the current stage
        details: Additional stage details
    """
    msg = f"Progress: {stage}"
    if details:
        detail_str = ", ".join(f"{k}={v}" for k, v in details.items())
        msg = f"{msg} ({detail_str})"

    logger.info(msg)
