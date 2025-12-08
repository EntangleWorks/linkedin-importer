"""Configuration management for LinkedIn Profile Importer.

This module provides Pydantic models for configuring the LinkedIn scraper,
including authentication, browser settings, and database connections.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class DatabaseConfig(BaseModel):
    """Database connection configuration."""

    url: Optional[str] = Field(
        default=None, description="Full PostgreSQL connection URL"
    )
    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, ge=1, le=65535, description="Database port")
    name: str = Field(default="", description="Database name")
    user: str = Field(default="", description="Database user")
    password: str = Field(default="", description="Database password")

    @field_validator("port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validate port is in valid range."""
        if not 1 <= v <= 65535:
            raise ValueError(f"Port must be between 1 and 65535, got {v}")
        return v

    @model_validator(mode="after")
    def validate_config(self) -> "DatabaseConfig":
        """Validate that either url or individual components are provided."""
        if not self.url and not all([self.name, self.user, self.password]):
            raise ValueError(
                "Either database URL or all of (name, user, password) must be provided"
            )
        return self

    def get_connection_string(self) -> str:
        """Get PostgreSQL connection string."""
        if self.url:
            return self.url
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class AuthMethod(str, Enum):
    """Authentication method for LinkedIn scraper.

    COOKIE: Direct cookie injection using the li_at session cookie.
            This is the PREFERRED method as it bypasses 2FA and CAPTCHA.

    CREDENTIALS: Email and password authentication via login form.
                 This is the FALLBACK method and may trigger 2FA.
    """

    COOKIE = "cookie"
    CREDENTIALS = "credentials"


class AuthConfig(BaseModel):
    """LinkedIn authentication configuration.

    Priority order for authentication:
    1. If cookie is provided, use cookie auth (bypasses 2FA)
    2. If email/password provided, use credentials auth
    3. If neither, raise configuration error

    Cookie authentication is strongly preferred as it:
    - Bypasses 2FA challenges
    - Avoids CAPTCHA prompts
    - Is more reliable and faster
    """

    method: Optional[AuthMethod] = Field(
        default=None,
        description="Authentication method (auto-detected if not specified)",
    )
    cookie: Optional[str] = Field(
        default=None,
        description="LinkedIn li_at session cookie (preferred method)",
    )
    email: Optional[str] = Field(
        default=None,
        description="LinkedIn email address (fallback method)",
    )
    password: Optional[str] = Field(
        default=None,
        description="LinkedIn password (fallback method)",
    )

    @model_validator(mode="after")
    def validate_auth_config(self) -> "AuthConfig":
        """Validate and auto-detect authentication method.

        If method is not specified:
        - Use COOKIE if cookie is provided
        - Use CREDENTIALS if email and password are provided
        - Raise error if neither is available
        """
        # Auto-detect method if not specified
        if self.method is None:
            if self.cookie:
                object.__setattr__(self, "method", AuthMethod.COOKIE)
            elif self.email and self.password:
                object.__setattr__(self, "method", AuthMethod.CREDENTIALS)
            else:
                raise ValueError(
                    "Authentication requires either LINKEDIN_COOKIE (preferred) "
                    "or both LINKEDIN_EMAIL and LINKEDIN_PASSWORD"
                )

        # Validate credentials for the selected method
        if self.method == AuthMethod.COOKIE:
            if not self.cookie:
                raise ValueError(
                    "Cookie authentication requires LINKEDIN_COOKIE to be set. "
                    "See .env.example for instructions on obtaining the li_at cookie."
                )
        elif self.method == AuthMethod.CREDENTIALS:
            if not self.email:
                raise ValueError(
                    "Credentials authentication requires LINKEDIN_EMAIL to be set"
                )
            if not self.password:
                raise ValueError(
                    "Credentials authentication requires LINKEDIN_PASSWORD to be set"
                )

        return self

    @field_validator("cookie")
    @classmethod
    def validate_cookie(cls, v: Optional[str]) -> Optional[str]:
        """Validate and clean the cookie value."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """Validate and clean the email value."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
            # Basic email format check
            if "@" not in v:
                raise ValueError("Invalid email format")
        return v


class ScraperConfig(BaseModel):
    """Browser and scraping behavior configuration.

    These settings control the Selenium WebDriver and scraping behavior
    to avoid detection and handle various edge cases.
    """

    headless: bool = Field(
        default=True,
        description="Run Chrome in headless mode (no visible window). "
        "Set to False for debugging.",
    )
    chromedriver_path: Optional[str] = Field(
        default=None,
        description="Path to ChromeDriver executable. "
        "If not set, webdriver-manager will auto-download.",
    )
    page_load_timeout: int = Field(
        default=30,
        ge=5,
        le=120,
        description="Maximum time to wait for page loads in seconds",
    )
    action_delay: float = Field(
        default=1.0,
        ge=0.5,
        le=10.0,
        description="Delay between actions (clicks, typing) in seconds. "
        "Higher values reduce detection risk.",
    )
    scroll_delay: float = Field(
        default=0.5,
        ge=0.1,
        le=5.0,
        description="Delay between scroll actions in seconds",
    )
    max_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retry attempts for failed operations",
    )
    screenshot_on_error: bool = Field(
        default=False,
        description="Capture screenshot when errors occur (for debugging)",
    )
    user_agent: Optional[str] = Field(
        default=None,
        description="Custom user agent string. Uses Chrome default if not set.",
    )

    @field_validator("page_load_timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        """Validate timeout is within acceptable range."""
        if not 5 <= v <= 120:
            raise ValueError(
                f"page_load_timeout must be between 5 and 120 seconds, got {v}"
            )
        return v

    @field_validator("action_delay", "scroll_delay")
    @classmethod
    def validate_delay(cls, v: float, info) -> float:
        """Validate delay values are positive."""
        if v < 0:
            raise ValueError(f"{info.field_name} must be positive, got {v}")
        return v


# Legacy configuration - kept for backward compatibility
class LinkedInConfig(BaseModel):
    """LinkedIn API configuration (DEPRECATED).

    This configuration was used for the API-based approach which is no longer
    functional. Kept for backward compatibility during migration.
    """

    api_key: str = Field(default="", description="LinkedIn API key (deprecated)")
    api_secret: str = Field(default="", description="LinkedIn API secret (deprecated)")
    access_token: Optional[str] = Field(
        default=None, description="OAuth access token (deprecated)"
    )


class Config(BaseModel):
    """Main configuration for LinkedIn Profile Importer.

    This configuration supports both the new scraper-based approach
    and the legacy API-based approach for backward compatibility.
    """

    # Database configuration (required)
    database: DatabaseConfig = Field(description="Database configuration")

    # New scraper configuration
    auth: Optional[AuthConfig] = Field(
        default=None,
        description="LinkedIn authentication configuration for web scraping",
    )
    scraper: ScraperConfig = Field(
        default_factory=ScraperConfig,
        description="Browser and scraping behavior configuration",
    )

    # Profile information
    profile_url: str = Field(description="LinkedIn profile URL or username")
    profile_email: Optional[str] = Field(
        default=None,
        description="Email to associate with the imported profile (required for scraping)",
    )

    # General settings
    verbose: bool = Field(default=False, description="Enable verbose logging")

    # Legacy configuration (deprecated)
    linkedin: Optional[LinkedInConfig] = Field(
        default=None,
        description="LinkedIn API configuration (deprecated - use auth instead)",
    )

    @field_validator("profile_url")
    @classmethod
    def validate_profile_url(cls, v: str) -> str:
        """Validate profile URL is not empty."""
        if not v or not v.strip():
            raise ValueError("Profile URL cannot be empty")
        return v.strip()

    @field_validator("profile_email")
    @classmethod
    def validate_profile_email(cls, v: Optional[str]) -> Optional[str]:
        """Validate profile email format if provided."""
        if v is not None:
            v = v.strip()
            if v and "@" not in v:
                raise ValueError("Invalid profile email format")
        return v

    @model_validator(mode="after")
    def validate_config(self) -> "Config":
        """Validate configuration completeness."""
        # If using the new scraper approach, auth must be configured
        if self.auth is not None and self.profile_email is None:
            raise ValueError(
                "profile_email is required when using the scraper. "
                "Set PROFILE_EMAIL in your environment."
            )
        return self
