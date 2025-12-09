"""Map LinkedIn profile data to database models."""

import re
from datetime import datetime
from uuid import UUID

from .db_models import (
    CertificationData,
    EducationData,
    ExperienceData,
    ProjectData,
    UserData,
    UserSkillData,
)
from .models import LinkedInProfile


def _generate_slug(text: str, suffix: str = "") -> str:
    """Generate a URL-friendly slug from text.

    Args:
        text: Text to convert to slug
        suffix: Optional suffix to append for uniqueness

    Returns:
        Lowercase slug with hyphens
    """
    # Convert to lowercase and replace spaces/special chars with hyphens
    slug = text.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[-\s]+", "-", slug)
    slug = slug.strip("-")

    # Add suffix if provided
    if suffix:
        slug = f"{slug}-{suffix}"

    return slug


def _format_bio(profile: LinkedInProfile) -> str:
    """Format user bio from LinkedIn profile data.

    Combines headline, summary, location, industry, languages, and honors
    into a structured bio text.

    Args:
        profile: LinkedIn profile data

    Returns:
        Formatted bio text
    """
    bio_parts = []

    # Add headline
    if profile.headline:
        bio_parts.append(profile.headline)

    # Add summary
    if profile.summary:
        bio_parts.append(profile.summary)

    # Add location and industry
    metadata = []
    if profile.location:
        metadata.append(f"Location: {profile.location}")
    if profile.industry:
        metadata.append(f"Industry: {profile.industry}")
    if metadata:
        bio_parts.append("\n".join(metadata))

    # Add languages section
    if profile.languages:
        bio_parts.append("\nLANGUAGES\n" + "-" * 9)
        lang_strs = []
        for lang in profile.languages:
            if lang.proficiency:
                lang_strs.append(f"{lang.name} ({lang.proficiency})")
            else:
                lang_strs.append(lang.name)
        bio_parts.append(", ".join(lang_strs))

    # Add honors section
    if profile.honors:
        bio_parts.append("\nHONORS & AWARDS\n" + "-" * 15)
        for honor in profile.honors:
            honor_parts = [honor.title]
            if honor.issuer:
                honor_parts.append(f"- {honor.issuer}")
            if honor.issue_date:
                honor_parts.append(f"({honor.issue_date.year})")
            bio_parts.append(" ".join(honor_parts))
            if honor.description:
                bio_parts.append(honor.description)

    return "\n\n".join(bio_parts)


def _map_position_to_experience(position, user_id: UUID) -> ExperienceData:
    """Map a LinkedIn position to an experience entry.

    Args:
        position: LinkedIn position data
        user_id: UUID of the user

    Returns:
        ExperienceData instance
    """
    # Combine description and responsibilities
    desc_parts = []
    if position.description:
        desc_parts.append(position.description)
    if position.responsibilities:
        desc_parts.append(position.responsibilities)

    description = "\n\n".join(desc_parts) if desc_parts else None

    return ExperienceData(
        user_id=user_id,
        company=position.company_name,
        position=position.title,
        location=position.location,
        description=description,
        start_date=position.start_date,
        end_date=position.end_date,
        is_current=position.end_date is None,
    )


def _map_education_to_education(edu, user_id: UUID) -> EducationData:
    """Map a LinkedIn education entry to an education record.

    Args:
        edu: LinkedIn education data
        user_id: UUID of the user

    Returns:
        EducationData instance
    """
    # Combine activities and description
    desc_parts = []
    if edu.description:
        desc_parts.append(edu.description)
    if edu.activities:
        desc_parts.append(f"Activities: {edu.activities}")

    description = "\n\n".join(desc_parts) if desc_parts else None

    return EducationData(
        user_id=user_id,
        school=edu.school,
        degree=edu.degree,
        field_of_study=edu.field_of_study,
        start_date=edu.start_date,
        end_date=edu.end_date,
        description=description,
        grade=edu.grade,
    )


def _map_certification_to_certification(cert, user_id: UUID) -> CertificationData:
    """Map a LinkedIn certification to a certification record.

    Args:
        cert: LinkedIn certification data
        user_id: UUID of the user

    Returns:
        CertificationData instance
    """
    return CertificationData(
        user_id=user_id,
        name=cert.name,
        issuer=cert.authority,
        url=cert.url,
        issue_date=cert.start_date,
        expiration_date=cert.end_date,
        credential_id=cert.license_number,
    )


def _map_skill_to_user_skill(skill, user_id: UUID) -> UserSkillData:
    """Map a LinkedIn skill to a user skill record.

    Args:
        skill: LinkedIn skill data
        user_id: UUID of the user

    Returns:
        UserSkillData instance
    """
    return UserSkillData(
        user_id=user_id,
        name=skill.name,
        category=None,  # LinkedIn scraper doesn't provide category currently
        proficiency_level=skill.endorsement_count,
    )


def map_profile_to_database(
    profile: LinkedInProfile,
) -> tuple[
    UserData,
    list[ProjectData],
    list[ExperienceData],
    list[EducationData],
    list[CertificationData],
    list[UserSkillData],
]:
    """Map LinkedIn profile to database models.

    Args:
        profile: LinkedIn profile data

    Returns:
        Tuple of (UserData, projects, experiences, educations, certifications, skills)
    """
    # Map user data
    user_data = UserData(
        email=profile.email,
        name=f"{profile.first_name} {profile.last_name}",
        bio=_format_bio(profile),
        avatar_url=profile.profile_picture_url,
    )

    # Placeholder UUID for linking children (will be updated by repository)
    placeholder_id = UUID(int=0)

    # Map positions to experiences
    experiences = [
        _map_position_to_experience(pos, placeholder_id) for pos in profile.positions
    ]

    # Map education
    educations = [
        _map_education_to_education(edu, placeholder_id) for edu in profile.education
    ]

    # Map certifications
    certifications = [
        _map_certification_to_certification(cert, placeholder_id)
        for cert in profile.certifications
    ]

    # Map skills
    skills = [
        _map_skill_to_user_skill(skill, placeholder_id) for skill in profile.skills
    ]

    # Projects list is empty for now as we don't want to overload it with non-project data.
    # Real portfolio projects should be added manually or via a specific "Projects" section import in the future.
    projects = []

    return user_data, projects, experiences, educations, certifications, skills
