"""Adapter for converting linkedin_scraper data to LinkedInProfile models.

This module provides functions to convert the Person object from the
linkedin_scraper library into the LinkedInProfile model used by the
existing mapper and database repository.
"""

from __future__ import annotations

import logging
import re
from datetime import date
from typing import TYPE_CHECKING, Optional

from .models import Education, LinkedInProfile, Position, Skill

if TYPE_CHECKING:
    from linkedin_scraper import Person

logger = logging.getLogger(__name__)


def convert_person_to_profile(person: "Person", email: str) -> LinkedInProfile:
    """Convert a linkedin_scraper Person object to a LinkedInProfile.

    Args:
        person: Person object from linkedin_scraper
        email: Email address for the profile (required, not scraped from LinkedIn)

    Returns:
        LinkedInProfile compatible with the existing mapper
    """
    logger.debug("Converting Person to LinkedInProfile: %s", person.name)

    # Extract profile ID from URL
    profile_id = _extract_profile_id(person.linkedin_url)

    # Parse name into first and last
    first_name, last_name = _parse_name(person.name)

    # Convert experiences to positions
    positions = _convert_experiences(person.experiences)

    # Convert education
    education = _convert_education_list(person.educations)

    # Extract skills (linkedin_scraper may have interests as skills)
    skills = _extract_skills(person)

    profile = LinkedInProfile(
        profile_id=profile_id,
        first_name=first_name,
        last_name=last_name,
        email=email,
        headline=getattr(person, "job_title", None) or "",
        summary=getattr(person, "about", None) or "",
        industry=None,  # Not available from scraper
        location=getattr(person, "location", None),
        profile_picture_url=None,  # Not reliably scraped
        positions=positions,
        education=education,
        skills=skills,
        certifications=[],  # Would need separate scraping
        publications=[],  # Would need separate scraping
        volunteer=[],  # Would need separate scraping
        honors=[],  # Would need separate scraping
        languages=[],  # Would need separate scraping
    )

    logger.info(
        "Converted profile: %s %s (%d positions, %d education, %d skills)",
        first_name,
        last_name,
        len(positions),
        len(education),
        len(skills),
    )

    return profile


def _extract_profile_id(linkedin_url: str) -> str:
    """Extract the profile ID from a LinkedIn URL.

    Args:
        linkedin_url: Full LinkedIn profile URL

    Returns:
        Profile ID/username
    """
    # Pattern: https://www.linkedin.com/in/username/
    match = re.search(r"linkedin\.com/in/([^/]+)/?", linkedin_url)
    if match:
        return match.group(1)

    # Fallback: use the last path segment
    parts = linkedin_url.rstrip("/").split("/")
    return parts[-1] if parts else "unknown"


def _parse_name(full_name: Optional[str]) -> tuple[str, str]:
    """Parse a full name into first and last name.

    Args:
        full_name: Full name string

    Returns:
        Tuple of (first_name, last_name)
    """
    if not full_name:
        return ("", "")

    parts = full_name.strip().split()
    if len(parts) == 0:
        return ("", "")
    if len(parts) == 1:
        return (parts[0], "")

    # First word is first name, rest is last name
    return (parts[0], " ".join(parts[1:]))


def _parse_date(date_str: Optional[str]) -> Optional[date]:
    """Parse a date string from LinkedIn into a date object.

    LinkedIn dates can be in various formats:
    - "Jan 2020"
    - "January 2020"
    - "2020"
    - "Present"

    Args:
        date_str: Date string from LinkedIn

    Returns:
        Parsed date or None
    """
    if not date_str:
        return None

    date_str = date_str.strip()

    # Handle "Present" or empty
    if date_str.lower() in ("present", "current", "now", ""):
        return None

    # Try full month name: "January 2020"
    month_names = {
        "january": 1,
        "jan": 1,
        "february": 2,
        "feb": 2,
        "march": 3,
        "mar": 3,
        "april": 4,
        "apr": 4,
        "may": 5,
        "june": 6,
        "jun": 6,
        "july": 7,
        "jul": 7,
        "august": 8,
        "aug": 8,
        "september": 9,
        "sep": 9,
        "sept": 9,
        "october": 10,
        "oct": 10,
        "november": 11,
        "nov": 11,
        "december": 12,
        "dec": 12,
    }

    # Pattern: "Month Year" or "Mon Year"
    match = re.match(r"(\w+)\s+(\d{4})", date_str, re.IGNORECASE)
    if match:
        month_str = match.group(1).lower()
        year = int(match.group(2))
        month = month_names.get(month_str)
        if month:
            return date(year, month, 1)

    # Pattern: just year "2020"
    match = re.match(r"^(\d{4})$", date_str)
    if match:
        year = int(match.group(1))
        return date(year, 1, 1)

    logger.warning("Could not parse date: %s", date_str)
    return None


def _convert_experiences(experiences: list) -> list[Position]:
    """Convert linkedin_scraper experiences to Position objects.

    Args:
        experiences: List of Experience objects from linkedin_scraper

    Returns:
        List of Position objects
    """
    positions = []

    for exp in experiences or []:
        # linkedin_scraper Experience has: institution_name, position_title,
        # from_date, to_date, duration, location, description
        position = Position(
            company_name=getattr(exp, "institution_name", None) or "",
            title=getattr(exp, "position_title", None) or "",
            description=getattr(exp, "description", None),
            location=getattr(exp, "location", None),
            start_date=_parse_date(getattr(exp, "from_date", None)),
            end_date=_parse_date(getattr(exp, "to_date", None)),
        )
        positions.append(position)

    return positions


def _is_current_position(experience) -> bool:
    """Determine if an experience is a current position.

    Args:
        experience: Experience object from linkedin_scraper

    Returns:
        True if this is a current position
    """
    to_date = getattr(experience, "to_date", None)
    if not to_date:
        return True

    to_date_str = str(to_date).lower().strip()
    return to_date_str in ("present", "current", "now", "")


def _convert_education_list(educations: list) -> list[Education]:
    """Convert linkedin_scraper educations to Education objects.

    Args:
        educations: List of Education objects from linkedin_scraper

    Returns:
        List of Education objects
    """
    education_list = []

    for edu in educations or []:
        # linkedin_scraper Education has: institution_name, degree,
        # from_date, to_date, description
        education = Education(
            school=getattr(edu, "institution_name", None) or "",
            degree=getattr(edu, "degree", None),
            field_of_study=None,  # Not always available separately
            start_date=_parse_date(getattr(edu, "from_date", None)),
            end_date=_parse_date(getattr(edu, "to_date", None)),
            description=getattr(edu, "description", None),
        )
        education_list.append(education)

    return education_list


def _extract_skills(person: "Person") -> list[Skill]:
    """Extract skills from a Person object.

    Note: linkedin_scraper may store skills in different attributes
    depending on the version and what's available on the profile.

    Args:
        person: Person object from linkedin_scraper

    Returns:
        List of Skill objects
    """
    skills = []

    # Try to get skills from various possible attributes
    skill_list = getattr(person, "skills", None) or []

    # linkedin_scraper might also have interests
    interests = getattr(person, "interests", None) or []

    # Combine and deduplicate
    all_skills = set()
    for skill in skill_list:
        if isinstance(skill, str):
            all_skills.add(skill)
        elif hasattr(skill, "name"):
            all_skills.add(skill.name)

    for interest in interests:
        if isinstance(interest, str):
            all_skills.add(interest)
        elif hasattr(interest, "name"):
            all_skills.add(interest.name)

    # Convert to Skill objects
    for skill_name in all_skills:
        if skill_name:
            skills.append(Skill(name=skill_name, endorsement_count=None))

    return skills
