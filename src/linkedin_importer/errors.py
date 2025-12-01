"""Error classes for LinkedIn Profile Importer."""

from datetime import datetime
from typing import Any, Optional


class ImportError(Exception):
    """Base error for import operations."""

    def __init__(
        self,
        error_type: str,
        message: str,
        details: Optional[dict[str, Any]] = None,
    ):
        """Initialize import error."""
        self.error_type = error_type
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now()
        super().__init__(message)

    def __str__(self) -> str:
        """String representation of error."""
        return f"[{self.error_type}] {self.message}"


class ConfigError(ImportError):
    """Configuration error."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        """Initialize config error."""
        super().__init__("config", message, details)


class AuthError(ImportError):
    """Authentication error."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        """Initialize auth error."""
        super().__init__("auth", message, details)


class APIError(ImportError):
    """API error."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        """Initialize API error."""
        super().__init__("api", message, details)


class ValidationError(ImportError):
    """Validation error."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        """Initialize validation error."""
        super().__init__("validation", message, details)


class DatabaseError(ImportError):
    """Database error."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        """Initialize database error."""
        super().__init__("database", message, details)
