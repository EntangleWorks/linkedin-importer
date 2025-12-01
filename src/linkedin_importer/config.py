"""Configuration management for LinkedIn Profile Importer."""

from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class DatabaseConfig(BaseModel):
    """Database connection configuration."""

    url: Optional[str] = Field(
        default=None, description="Full PostgreSQL connection URL"
    )
    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, ge=1, le=65535, description="Database port")
    name: str = Field(description="Database name")
    user: str = Field(description="Database user")
    password: str = Field(description="Database password")

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


class LinkedInConfig(BaseModel):
    """LinkedIn API configuration."""

    api_key: str = Field(description="LinkedIn API key")
    api_secret: str = Field(description="LinkedIn API secret")
    access_token: Optional[str] = Field(
        default=None, description="OAuth access token (optional)"
    )

    @field_validator("api_key", "api_secret")
    @classmethod
    def validate_not_empty(cls, v: str, info) -> str:
        """Validate that API credentials are not empty."""
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} cannot be empty")
        return v.strip()


class Config(BaseModel):
    """Main configuration for LinkedIn Profile Importer."""

    database: DatabaseConfig = Field(description="Database configuration")
    linkedin: LinkedInConfig = Field(description="LinkedIn API configuration")
    profile_url: str = Field(description="LinkedIn profile URL or username")
    verbose: bool = Field(default=False, description="Enable verbose logging")

    @field_validator("profile_url")
    @classmethod
    def validate_profile_url(cls, v: str) -> str:
        """Validate profile URL is not empty."""
        if not v or not v.strip():
            raise ValueError("Profile URL cannot be empty")
        return v.strip()
