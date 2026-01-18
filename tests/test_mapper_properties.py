"""Property-based tests for LinkedIn to database mapping.

Feature: linkedin-profile-importer, Property 3: Database storage round-trip
Validates: Requirements 1.3, 4.1, 4.2, 4.4
"""

from datetime import date

from hypothesis import given, settings
from hypothesis import strategies as st

from linkedin_importer.mapper import map_profile_to_database
from linkedin_importer.models import (
    Certification,
    Education,
    Honor,
    Language,
    LinkedInProfile,
    Position,
    Publication,
    Skill,
    VolunteerExperience,
)


# Strategies for generating LinkedIn profile data
@st.composite
def position_strategy(draw):
    """Generate a valid Position."""
    company_name = draw(st.text(min_size=1, max_size=100))
    title = draw(st.text(min_size=1, max_size=100))
    description = draw(st.none() | st.text(max_size=500))
    responsibilities = draw(st.none() | st.text(max_size=1000))

    # Generate valid dates
    start_date = draw(
        st.none() | st.dates(min_value=date(1950, 1, 1), max_value=date(2024, 12, 31))
    )
    end_date = draw(
        st.none() | st.dates(min_value=date(1950, 1, 1), max_value=date(2024, 12, 31))
    )

    # Ensure end_date is after start_date if both exist
    if start_date and end_date and end_date < start_date:
        end_date = None

    location = draw(st.none() | st.text(max_size=100))
    employment_type = draw(
        st.none()
        | st.sampled_from(
            ["Full-time", "Part-time", "Contract", "Freelance", "Internship"]
        )
    )
    company_url = draw(st.none() | st.text(max_size=200))
    company_logo_url = draw(st.none() | st.text(max_size=200))

    return Position(
        company_name=company_name,
        title=title,
        description=description,
        responsibilities=responsibilities,
        start_date=start_date,
        end_date=end_date,
        location=location,
        employment_type=employment_type,
        company_url=company_url,
        company_logo_url=company_logo_url,
    )


@st.composite
def education_strategy(draw):
    """Generate a valid Education."""
    school = draw(st.text(min_size=1, max_size=100))
    degree = draw(st.none() | st.text(max_size=100))
    field_of_study = draw(st.none() | st.text(max_size=100))
    start_date = draw(
        st.none() | st.dates(min_value=date(1950, 1, 1), max_value=date(2024, 12, 31))
    )
    end_date = draw(
        st.none() | st.dates(min_value=date(1950, 1, 1), max_value=date(2024, 12, 31))
    )
    grade = draw(st.none() | st.text(max_size=50))
    activities = draw(st.none() | st.text(max_size=200))
    description = draw(st.none() | st.text(max_size=500))

    return Education(
        school=school,
        degree=degree,
        field_of_study=field_of_study,
        start_date=start_date,
        end_date=end_date,
        grade=grade,
        activities=activities,
        description=description,
    )


@st.composite
def skill_strategy(draw):
    """Generate a valid Skill."""
    name = draw(st.text(min_size=1, max_size=50))
    endorsement_count = draw(st.none() | st.integers(min_value=0, max_value=1000))

    return Skill(name=name, endorsement_count=endorsement_count)


@st.composite
def certification_strategy(draw):
    """Generate a valid Certification."""
    name = draw(st.text(min_size=1, max_size=100))
    authority = draw(st.text(min_size=1, max_size=100))
    license_number = draw(st.none() | st.text(max_size=50))
    start_date = draw(
        st.none() | st.dates(min_value=date(1950, 1, 1), max_value=date(2024, 12, 31))
    )
    end_date = draw(
        st.none() | st.dates(min_value=date(1950, 1, 1), max_value=date(2024, 12, 31))
    )
    url = draw(st.none() | st.text(max_size=200))

    return Certification(
        name=name,
        authority=authority,
        license_number=license_number,
        start_date=start_date,
        end_date=end_date,
        url=url,
    )


@st.composite
def publication_strategy(draw):
    """Generate a valid Publication."""
    name = draw(st.text(min_size=1, max_size=100))
    publisher = draw(st.none() | st.text(max_size=100))
    publication_date = draw(
        st.none() | st.dates(min_value=date(1950, 1, 1), max_value=date(2024, 12, 31))
    )
    url = draw(st.none() | st.text(max_size=200))
    description = draw(st.none() | st.text(max_size=500))

    return Publication(
        name=name,
        publisher=publisher,
        publication_date=publication_date,
        url=url,
        description=description,
    )


@st.composite
def volunteer_strategy(draw):
    """Generate a valid VolunteerExperience."""
    organization = draw(st.text(min_size=1, max_size=100))
    role = draw(st.text(min_size=1, max_size=100))
    cause = draw(st.none() | st.text(max_size=100))
    description = draw(st.none() | st.text(max_size=500))
    start_date = draw(
        st.none() | st.dates(min_value=date(1950, 1, 1), max_value=date(2024, 12, 31))
    )
    end_date = draw(
        st.none() | st.dates(min_value=date(1950, 1, 1), max_value=date(2024, 12, 31))
    )

    return VolunteerExperience(
        organization=organization,
        role=role,
        cause=cause,
        description=description,
        start_date=start_date,
        end_date=end_date,
    )


@st.composite
def honor_strategy(draw):
    """Generate a valid Honor."""
    title = draw(st.text(min_size=1, max_size=100))
    issuer = draw(st.none() | st.text(max_size=100))
    issue_date = draw(
        st.none() | st.dates(min_value=date(1950, 1, 1), max_value=date(2024, 12, 31))
    )
    description = draw(st.none() | st.text(max_size=500))

    return Honor(
        title=title, issuer=issuer, issue_date=issue_date, description=description
    )


@st.composite
def language_strategy(draw):
    """Generate a valid Language."""
    name = draw(st.text(min_size=1, max_size=50))
    proficiency = draw(
        st.none()
        | st.sampled_from(
            [
                "Elementary",
                "Limited Working",
                "Professional Working",
                "Full Professional",
                "Native",
            ]
        )
    )

    return Language(name=name, proficiency=proficiency)


@st.composite
def linkedin_profile_strategy(draw):
    """Generate a valid LinkedInProfile."""
    profile_id = draw(st.text(min_size=1, max_size=50))
    first_name = draw(st.text(min_size=1, max_size=50))
    last_name = draw(st.text(min_size=1, max_size=50))
    email = draw(
        st.emails()
        | st.text(min_size=3, max_size=100).filter(lambda x: "@" in x and "." in x)
    )
    headline = draw(st.none() | st.text(max_size=200))
    summary = draw(st.none() | st.text(max_size=1000))
    location = draw(st.none() | st.text(max_size=100))
    industry = draw(st.none() | st.text(max_size=100))
    profile_picture_url = draw(st.none() | st.text(max_size=200))

    positions = draw(st.lists(position_strategy(), max_size=5))
    education = draw(st.lists(education_strategy(), max_size=3))
    skills = draw(st.lists(skill_strategy(), max_size=10))
    certifications = draw(st.lists(certification_strategy(), max_size=3))
    publications = draw(st.lists(publication_strategy(), max_size=3))
    volunteer = draw(st.lists(volunteer_strategy(), max_size=3))
    honors = draw(st.lists(honor_strategy(), max_size=3))
    languages = draw(st.lists(language_strategy(), max_size=5))

    return LinkedInProfile(
        profile_id=profile_id,
        first_name=first_name,
        last_name=last_name,
        email=email,
        headline=headline,
        summary=summary,
        location=location,
        industry=industry,
        profile_picture_url=profile_picture_url,
        positions=positions,
        education=education,
        skills=skills,
        certifications=certifications,
        publications=publications,
        volunteer=volunteer,
        honors=honors,
        languages=languages,
    )


@settings(max_examples=100)
@given(profile=linkedin_profile_strategy())
def test_profile_mapping_preserves_essential_information(profile):
    """
    Feature: linkedin-profile-importer, Property 3: Database storage round-trip
    Validates: Requirements 1.3, 4.1, 4.2, 4.4

    For any valid LinkedIn profile data, after mapping to database models,
    the essential information (name, email, bio, projects, technologies)
    should be preserved according to the schema mapping.
    """
    # Map profile to database models
    (
        user_data,
        projects,
        experiences,
        educations,
        certifications,
        skills,
    ) = map_profile_to_database(profile)

    # Verify user data preservation
    assert user_data.email == profile.email
    assert user_data.name == f"{profile.first_name} {profile.last_name}"
    assert user_data.avatar_url == profile.profile_picture_url

    # Verify bio contains key information
    if profile.headline:
        assert profile.headline in user_data.bio
    if profile.summary:
        assert profile.summary in user_data.bio
    if profile.location:
        assert profile.location in user_data.bio
    if profile.industry:
        assert profile.industry in user_data.bio

    # Verify education entries are mapped
    assert len(educations) == len(profile.education)

    # Verify languages are in bio
    for lang in profile.languages:
        assert lang.name in user_data.bio

    # Verify honors are in bio
    for honor in profile.honors:
        assert honor.title in user_data.bio

    # Verify experiences are mapped from positions
    assert len(experiences) == len(profile.positions)

    # Verify certifications are mapped
    assert len(certifications) == len(profile.certifications)

    # Verify skills are mapped
    assert len(skills) == len(profile.skills)

    # Verify experience data is preserved
    for i, position in enumerate(profile.positions):
        if i < len(experiences):
            exp = experiences[i]
            assert exp.company == position.company_name
            assert exp.position == position.title

    # Verify education data is preserved
    for i, edu in enumerate(profile.education):
        if i < len(educations):
            ed = educations[i]
            assert ed.school == edu.school

    # Verify certification data is preserved
    for i, cert in enumerate(profile.certifications):
        if i < len(certifications):
            c = certifications[i]
            assert c.name == cert.name

    # Verify skill data is preserved
    for i, skill in enumerate(profile.skills):
        if i < len(skills):
            s = skills[i]
            assert s.name == skill.name
