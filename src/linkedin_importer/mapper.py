"""Map LinkedIn profile data to database models."""

import re
from datetime import datetime

from .db_models import ProjectData, UserData
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

    Combines headline, summary, location, industry, education, languages, and honors
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

    # Add education section
    if profile.education:
        bio_parts.append("\nEDUCATION\n" + "-" * 9)
        for edu in profile.education:
            edu_lines = []

            # Format degree line
            degree_parts = []
            if edu.degree:
                degree_parts.append(edu.degree)
            if edu.field_of_study:
                degree_parts.append(f"in {edu.field_of_study}")
            if degree_parts:
                degree_parts.append(f"from {edu.school}")
            else:
                degree_parts.append(edu.school)

            # Add date range
            if edu.start_date or edu.end_date:
                start_year = edu.start_date.year if edu.start_date else "?"
                end_year = edu.end_date.year if edu.end_date else "Present"
                degree_parts.append(f"({start_year} - {end_year})")

            edu_lines.append(" ".join(degree_parts))

            # Add grade if available
            if edu.grade:
                edu_lines.append(edu.grade)

            # Add activities if available
            if edu.activities:
                edu_lines.append(edu.activities)

            bio_parts.append("\n".join(edu_lines))

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


def _map_position_to_project(position, profile: LinkedInProfile) -> ProjectData:
    """Map a LinkedIn position to a project entry.

    Args:
        position: LinkedIn position data
        profile: Full LinkedIn profile (for linking skills)

    Returns:
        ProjectData instance
    """
    # Format title as "Title at Company"
    title = f"{position.title} at {position.company_name}"

    # Generate slug from title
    slug = _generate_slug(title)

    # Use description as short description
    description = position.description or ""

    # Build long description with location, employment type, and responsibilities
    long_desc_parts = []
    if position.location:
        long_desc_parts.append(f"Location: {position.location}")
    if position.employment_type:
        long_desc_parts.append(f"Employment Type: {position.employment_type}")
    if position.responsibilities:
        long_desc_parts.append(position.responsibilities)

    long_description = "\n\n".join(long_desc_parts) if long_desc_parts else None

    # Convert dates to datetime
    created_at = (
        datetime.combine(position.start_date, datetime.min.time())
        if position.start_date
        else None
    )
    updated_at = (
        datetime.combine(position.end_date, datetime.min.time())
        if position.end_date
        else datetime.now()
    )

    return ProjectData(
        slug=slug,
        title=title,
        description=description,
        long_description=long_description,
        image_url=position.company_logo_url,
        live_url=position.company_url,
        github_url=None,
        featured=False,
        created_at=created_at,
        updated_at=updated_at,
        technologies=[],  # Will be populated later
    )


def _map_certification_to_project(cert) -> ProjectData:
    """Map a LinkedIn certification to a project entry.

    Args:
        cert: LinkedIn certification data

    Returns:
        ProjectData instance
    """
    title = f"Certification: {cert.name}"
    slug = _generate_slug(title)
    description = cert.authority

    # Build long description with license number
    long_desc_parts = []
    if cert.license_number:
        long_desc_parts.append(f"License Number: {cert.license_number}")

    long_description = "\n\n".join(long_desc_parts) if long_desc_parts else None

    # Use start date as created_at
    created_at = (
        datetime.combine(cert.start_date, datetime.min.time())
        if cert.start_date
        else None
    )
    updated_at = (
        datetime.combine(cert.end_date, datetime.min.time())
        if cert.end_date
        else created_at
    )

    return ProjectData(
        slug=slug,
        title=title,
        description=description,
        long_description=long_description,
        image_url=None,
        live_url=cert.url,
        github_url=None,
        featured=False,
        created_at=created_at,
        updated_at=updated_at,
        technologies=[],
    )


def _map_publication_to_project(pub) -> ProjectData:
    """Map a LinkedIn publication to a project entry.

    Args:
        pub: LinkedIn publication data

    Returns:
        ProjectData instance
    """
    title = f"Publication: {pub.name}"
    slug = _generate_slug(title)
    description = pub.publisher or ""
    long_description = pub.description

    created_at = (
        datetime.combine(pub.publication_date, datetime.min.time())
        if pub.publication_date
        else None
    )

    return ProjectData(
        slug=slug,
        title=title,
        description=description,
        long_description=long_description,
        image_url=None,
        live_url=pub.url,
        github_url=None,
        featured=False,
        created_at=created_at,
        updated_at=created_at,
        technologies=[],
    )


def _map_volunteer_to_project(vol) -> ProjectData:
    """Map a LinkedIn volunteer experience to a project entry.

    Args:
        vol: LinkedIn volunteer experience data

    Returns:
        ProjectData instance
    """
    title = f"Volunteer: {vol.role} at {vol.organization}"
    slug = _generate_slug(title)
    description = vol.description or ""

    # Build long description with cause
    long_desc_parts = []
    if vol.cause:
        long_desc_parts.append(f"Cause: {vol.cause}")
    if vol.description:
        long_desc_parts.append(vol.description)

    long_description = "\n\n".join(long_desc_parts) if long_desc_parts else None

    created_at = (
        datetime.combine(vol.start_date, datetime.min.time())
        if vol.start_date
        else None
    )
    updated_at = (
        datetime.combine(vol.end_date, datetime.min.time())
        if vol.end_date
        else datetime.now()
    )

    return ProjectData(
        slug=slug,
        title=title,
        description=description,
        long_description=long_description,
        image_url=None,
        live_url=None,
        github_url=None,
        featured=False,
        created_at=created_at,
        updated_at=updated_at,
        technologies=[],
    )


def _link_skills_to_projects(
    projects: list[ProjectData], skills: list, max_recent_projects: int = 3
) -> None:
    """Link skills to the most recent projects.

    Modifies projects in-place to add skills as technologies.
    Prioritizes skills with high endorsement counts.

    Args:
        projects: List of project data (sorted by date, most recent first)
        skills: List of LinkedIn skills
        max_recent_projects: Number of recent projects to link skills to
    """
    if not skills or not projects:
        return

    # Sort skills by endorsement count (highest first)
    sorted_skills = sorted(skills, key=lambda s: s.endorsement_count or 0, reverse=True)

    # Get skill names
    skill_names = [skill.name for skill in sorted_skills]

    # Link to most recent projects
    for project in projects[:max_recent_projects]:
        project.technologies = skill_names.copy()


def map_profile_to_database(
    profile: LinkedInProfile,
) -> tuple[UserData, list[ProjectData]]:
    """Map LinkedIn profile to database models.

    Args:
        profile: LinkedIn profile data

    Returns:
        Tuple of (UserData, list of ProjectData)
    """
    # Map user data
    user_data = UserData(
        email=profile.email,
        name=f"{profile.first_name} {profile.last_name}",
        bio=_format_bio(profile),
        avatar_url=profile.profile_picture_url,
    )

    # Map all positions to projects
    projects = []
    slug_counts = {}  # Track slug usage for uniqueness

    for position in profile.positions:
        project = _map_position_to_project(position, profile)
        # Ensure unique slug
        base_slug = project.slug
        if base_slug in slug_counts:
            slug_counts[base_slug] += 1
            project.slug = f"{base_slug}-{slug_counts[base_slug]}"
        else:
            slug_counts[base_slug] = 0
        projects.append(project)

    # Map certifications to projects
    for cert in profile.certifications:
        project = _map_certification_to_project(cert)
        # Ensure unique slug
        base_slug = project.slug
        if base_slug in slug_counts:
            slug_counts[base_slug] += 1
            project.slug = f"{base_slug}-{slug_counts[base_slug]}"
        else:
            slug_counts[base_slug] = 0
        projects.append(project)

    # Map publications to projects
    for pub in profile.publications:
        project = _map_publication_to_project(pub)
        # Ensure unique slug
        base_slug = project.slug
        if base_slug in slug_counts:
            slug_counts[base_slug] += 1
            project.slug = f"{base_slug}-{slug_counts[base_slug]}"
        else:
            slug_counts[base_slug] = 0
        projects.append(project)

    # Map volunteer experiences to projects
    for vol in profile.volunteer:
        project = _map_volunteer_to_project(vol)
        # Ensure unique slug
        base_slug = project.slug
        if base_slug in slug_counts:
            slug_counts[base_slug] += 1
            project.slug = f"{base_slug}-{slug_counts[base_slug]}"
        else:
            slug_counts[base_slug] = 0
        projects.append(project)

    # Sort projects by date (most recent first)
    projects.sort(
        key=lambda p: p.created_at or datetime.min,
        reverse=True,
    )

    # Link skills to recent projects
    _link_skills_to_projects(projects, profile.skills)

    return user_data, projects
