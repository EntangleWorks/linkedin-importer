"""Data validation for LinkedIn profile data."""

import re
from datetime import date
from typing import Optional
from urllib.parse import urlparse

from linkedin_importer.errors import ValidationError
from linkedin_importer.models import LinkedInProfile

# RFC 5322 simplified email regex
EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
)

# Valid employment types
VALID_EMPLOYMENT_TYPES = {
    "full-time",
    "part-time",
    "contract",
    "freelance",
    "internship",
    "temporary",
    "volunteer",
    "self-employed",
}

# Valid language proficiency levels
VALID_PROFICIENCY_LEVELS = {
    "elementary",
    "limited working",
    "professional working",
    "full professional",
    "native",
}


def validate_email(email: str) -> bool:
    """
    Validate email format according to RFC 5322.

    Args:
        email: Email address to validate

    Returns:
        True if email is valid, False otherwise
    """
    if not email or not isinstance(email, str):
        return False
    return EMAIL_REGEX.match(email.strip()) is not None


def validate_url(url: str) -> bool:
    """
    Validate URL format (HTTP or HTTPS).

    Args:
        url: URL to validate

    Returns:
        True if URL is valid HTTP/HTTPS, False otherwise
    """
    if not url or not isinstance(url, str):
        return False

    try:
        parsed = urlparse(url.strip())
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def normalize_skill_name(skill_name: str) -> str:
    """
    Normalize skill name (trim whitespace, title case).

    Args:
        skill_name: Skill name to normalize

    Returns:
        Normalized skill name
    """
    if not skill_name or not isinstance(skill_name, str):
        return ""

    # Trim whitespace and convert to title case
    normalized = skill_name.strip().title()
    return normalized


def normalize_employment_type(employment_type: str) -> Optional[str]:
    """
    Normalize employment type to standard values.

    Args:
        employment_type: Employment type to normalize

    Returns:
        Normalized employment type or None if invalid
    """
    if not employment_type or not isinstance(employment_type, str):
        return None

    # Convert to lowercase and check against valid types
    normalized = employment_type.strip().lower()

    # Handle common variations
    type_mapping = {
        "full time": "full-time",
        "fulltime": "full-time",
        "part time": "part-time",
        "parttime": "part-time",
        "contractor": "contract",
        "consulting": "contract",
        "intern": "internship",
        "temp": "temporary",
    }

    normalized = type_mapping.get(normalized, normalized)

    return normalized if normalized in VALID_EMPLOYMENT_TYPES else None


def normalize_proficiency_level(proficiency: str) -> Optional[str]:
    """
    Normalize language proficiency level to standard values.

    Args:
        proficiency: Proficiency level to normalize

    Returns:
        Normalized proficiency level or None if invalid
    """
    if not proficiency or not isinstance(proficiency, str):
        return None

    normalized = proficiency.strip().lower()
    return normalized if normalized in VALID_PROFICIENCY_LEVELS else None


def parse_date(date_str: str) -> Optional[date]:
    """
    Parse date string to date object.

    Supports ISO 8601 format (YYYY-MM-DD) and common variations.

    Args:
        date_str: Date string to parse

    Returns:
        Parsed date object or None if parsing fails
    """
    if not date_str or not isinstance(date_str, str):
        return None

    date_str = date_str.strip()

    # Try ISO 8601 format (YYYY-MM-DD)
    try:
        parts = date_str.split("-")
        if len(parts) == 3:
            year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
            return date(year, month, day)
    except (ValueError, IndexError):
        # Invalid format or values, try next format
        pass

    # Try YYYY/MM/DD format
    try:
        parts = date_str.split("/")
        if len(parts) == 3:
            year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
            return date(year, month, day)
    except (ValueError, IndexError):
        # Invalid format or values, return None below
        pass

    return None


def validate_required_fields(profile: LinkedInProfile) -> None:
    """
    Validate that required fields are present and properly formatted.

    Args:
        profile: LinkedIn profile to validate

    Raises:
        ValidationError: If required fields are missing or invalid
    """
    errors = []

    # Validate name fields
    if not profile.first_name or not profile.first_name.strip():
        errors.append("first_name is required and cannot be empty")

    if not profile.last_name or not profile.last_name.strip():
        errors.append("last_name is required and cannot be empty")

    # Validate email
    if not profile.email or not profile.email.strip():
        errors.append("email is required and cannot be empty")
    elif not validate_email(profile.email):
        errors.append(f"email '{profile.email}' is not a valid email format")

    if errors:
        raise ValidationError(
            message="Profile validation failed", details={"validation_errors": errors}
        )


def validate_profile_urls(profile: LinkedInProfile) -> None:
    """
    Validate all URL fields in the profile.

    Args:
        profile: LinkedIn profile to validate

    Raises:
        ValidationError: If any URLs are invalid
    """
    errors = []

    # Validate profile picture URL
    if profile.profile_picture_url and not validate_url(profile.profile_picture_url):
        errors.append(
            f"profile_picture_url '{profile.profile_picture_url}' is not a valid URL"
        )

    # Validate position URLs
    for i, position in enumerate(profile.positions):
        if position.company_url and not validate_url(position.company_url):
            errors.append(
                f"positions[{i}].company_url '{position.company_url}' is not a valid URL"
            )
        if position.company_logo_url and not validate_url(position.company_logo_url):
            errors.append(
                f"positions[{i}].company_logo_url '{position.company_logo_url}' is not a valid URL"
            )

    # Validate certification URLs
    for i, cert in enumerate(profile.certifications):
        if cert.url and not validate_url(cert.url):
            errors.append(f"certifications[{i}].url '{cert.url}' is not a valid URL")

    # Validate publication URLs
    for i, pub in enumerate(profile.publications):
        if pub.url and not validate_url(pub.url):
            errors.append(f"publications[{i}].url '{pub.url}' is not a valid URL")

    if errors:
        raise ValidationError(
            message="URL validation failed", details={"validation_errors": errors}
        )


def validate_and_normalize_profile(profile: LinkedInProfile) -> LinkedInProfile:
    """
    Validate and normalize a LinkedIn profile.

    This function validates required fields, email format, URLs, and normalizes
    skill names and employment types.

    Args:
        profile: LinkedIn profile to validate and normalize

    Returns:
        Validated and normalized profile

    Raises:
        ValidationError: If validation fails
    """
    # Validate required fields
    validate_required_fields(profile)

    # Validate URLs
    validate_profile_urls(profile)

    # Normalize skill names
    for skill in profile.skills:
        skill.name = normalize_skill_name(skill.name)

    # Normalize employment types
    for position in profile.positions:
        if position.employment_type:
            position.employment_type = normalize_employment_type(
                position.employment_type
            )
    # Normalize language proficiency levels
    for language in profile.languages:
        if language.proficiency:
            language.proficiency = normalize_proficiency_level(language.proficiency)

    return profile
