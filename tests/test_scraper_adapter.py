"""Property-based and integration tests for LinkedIn scraper adapter.

Feature: linkedin-scraper, Data Adapter
Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5
"""

from datetime import date
from typing import Optional
from unittest.mock import MagicMock

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from linkedin_importer.mapper import map_profile_to_database
from linkedin_importer.models import (
    Education,
    LinkedInProfile,
    Position,
    Skill,
)
from linkedin_importer.scraper_adapter import (
    _convert_education_list,
    _convert_experiences,
    _extract_profile_id,
    _extract_skills,
    _parse_date,
    _parse_name,
    convert_person_to_profile,
)

# =============================================================================
# Unit Tests for _extract_profile_id
# =============================================================================


class TestExtractProfileId:
    """Unit tests for profile ID extraction from LinkedIn URLs."""

    def test_extract_from_standard_url(self):
        """Extract profile ID from standard LinkedIn URL."""
        url = "https://www.linkedin.com/in/john-doe"
        assert _extract_profile_id(url) == "john-doe"

    def test_extract_from_url_with_trailing_slash(self):
        """Extract profile ID from URL with trailing slash."""
        url = "https://www.linkedin.com/in/john-doe/"
        assert _extract_profile_id(url) == "john-doe"

    def test_extract_from_url_without_www(self):
        """Extract profile ID from URL without www."""
        url = "https://linkedin.com/in/jane-smith"
        assert _extract_profile_id(url) == "jane-smith"

    def test_extract_from_url_with_query_params(self):
        """Extract profile ID from URL with query parameters."""
        url = "https://www.linkedin.com/in/john-doe/?originalSubdomain=ca"
        # The regex captures up to ? or /
        result = _extract_profile_id(url)
        # Should get john-doe (the regex stops at /)
        assert "john-doe" in result

    def test_fallback_for_non_matching_url(self):
        """Fallback to last path segment for non-matching URLs."""
        url = "https://example.com/profiles/johndoe"
        assert _extract_profile_id(url) == "johndoe"

    def test_handle_empty_url(self):
        """Handle empty URL gracefully."""
        url = ""
        result = _extract_profile_id(url)
        # Should return empty or last segment
        assert result == ""


# =============================================================================
# Unit Tests for _parse_name
# =============================================================================


class TestParseName:
    """Unit tests for name parsing."""

    def test_parse_full_name(self):
        """Parse a standard first and last name."""
        first, last = _parse_name("John Doe")
        assert first == "John"
        assert last == "Doe"

    def test_parse_single_name(self):
        """Parse a single name (first name only)."""
        first, last = _parse_name("Madonna")
        assert first == "Madonna"
        assert last == ""

    def test_parse_multiple_names(self):
        """Parse name with multiple parts (middle names)."""
        first, last = _parse_name("John Paul Jones Smith")
        assert first == "John"
        assert last == "Paul Jones Smith"

    def test_parse_empty_string(self):
        """Parse empty string returns empty tuple."""
        first, last = _parse_name("")
        assert first == ""
        assert last == ""

    def test_parse_none(self):
        """Parse None returns empty tuple."""
        first, last = _parse_name(None)
        assert first == ""
        assert last == ""

    def test_parse_whitespace_only(self):
        """Parse whitespace-only string returns empty tuple."""
        first, last = _parse_name("   ")
        assert first == ""
        assert last == ""

    def test_parse_name_with_extra_spaces(self):
        """Parse name with extra whitespace."""
        first, last = _parse_name("  John   Doe  ")
        assert first == "John"
        assert last == "Doe"


# =============================================================================
# Property Tests for _parse_name
# =============================================================================


@settings(max_examples=100, deadline=None)
@given(
    first=st.text(
        alphabet=st.characters(
            whitelist_categories=("L",), min_codepoint=65, max_codepoint=122
        ),
        min_size=1,
        max_size=20,
    ).filter(lambda x: x.strip()),
    last=st.text(
        alphabet=st.characters(
            whitelist_categories=("L",), min_codepoint=65, max_codepoint=122
        ),
        min_size=1,
        max_size=20,
    ).filter(lambda x: x.strip()),
)
def test_property_name_split_correctly(first: str, last: str):
    """
    Property: Name correctly split into first/last.
    Validates: Requirement 4.1

    For any valid first and last name, when combined with a space and parsed,
    the result should correctly separate into first and last name components.
    """
    full_name = f"{first} {last}"
    parsed_first, parsed_last = _parse_name(full_name)

    assert parsed_first == first
    assert parsed_last == last


@settings(max_examples=50, deadline=None)
@given(
    name=st.text(
        alphabet=st.characters(
            whitelist_categories=("L",), min_codepoint=65, max_codepoint=122
        ),
        min_size=1,
        max_size=20,
    ).filter(lambda x: x.strip() and " " not in x),
)
def test_property_single_name_first_only(name: str):
    """
    Property: Single name becomes first name with empty last name.
    Validates: Requirement 4.1
    """
    parsed_first, parsed_last = _parse_name(name)

    assert parsed_first == name
    assert parsed_last == ""


@settings(max_examples=50, deadline=None)
@given(
    empty_ish=st.sampled_from(["", "   ", "\t", "\n", None]),
)
def test_property_empty_names_return_empty_tuple(empty_ish):
    """
    Property: Empty/None names return empty strings.
    Validates: Requirement 4.1
    """
    parsed_first, parsed_last = _parse_name(empty_ish)

    assert parsed_first == ""
    assert parsed_last == ""


# =============================================================================
# Unit Tests for _parse_date
# =============================================================================


class TestParseDate:
    """Unit tests for date parsing."""

    def test_parse_abbreviated_month_year(self):
        """Parse 'Jan 2023' format."""
        result = _parse_date("Jan 2023")
        assert result == date(2023, 1, 1)

    def test_parse_full_month_year(self):
        """Parse 'January 2023' format."""
        result = _parse_date("January 2023")
        assert result == date(2023, 1, 1)

    def test_parse_year_only(self):
        """Parse year-only format '2023'."""
        result = _parse_date("2023")
        assert result == date(2023, 1, 1)

    def test_parse_present(self):
        """Parse 'Present' returns None (current position)."""
        result = _parse_date("Present")
        assert result is None

    def test_parse_current(self):
        """Parse 'Current' returns None."""
        result = _parse_date("Current")
        assert result is None

    def test_parse_now(self):
        """Parse 'Now' returns None."""
        result = _parse_date("Now")
        assert result is None

    def test_parse_empty_string(self):
        """Parse empty string returns None."""
        result = _parse_date("")
        assert result is None

    def test_parse_none(self):
        """Parse None returns None."""
        result = _parse_date(None)
        assert result is None

    def test_parse_all_months_abbreviated(self):
        """Parse all abbreviated month names."""
        months = [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ]
        for i, month in enumerate(months, 1):
            result = _parse_date(f"{month} 2020")
            assert result == date(2020, i, 1), f"Failed for {month}"

    def test_parse_all_months_full(self):
        """Parse all full month names."""
        months = [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ]
        for i, month in enumerate(months, 1):
            result = _parse_date(f"{month} 2020")
            assert result == date(2020, i, 1), f"Failed for {month}"

    def test_parse_case_insensitive(self):
        """Parse is case insensitive."""
        assert _parse_date("JANUARY 2020") == date(2020, 1, 1)
        assert _parse_date("january 2020") == date(2020, 1, 1)
        assert _parse_date("JAN 2020") == date(2020, 1, 1)

    def test_parse_invalid_format_returns_none(self):
        """Invalid date format returns None."""
        result = _parse_date("Invalid Date")
        assert result is None

    def test_parse_with_extra_whitespace(self):
        """Parse handles extra whitespace."""
        result = _parse_date("  Jan 2023  ")
        assert result == date(2023, 1, 1)

    def test_parse_september_short_forms(self):
        """Parse both Sep and Sept abbreviations."""
        assert _parse_date("Sep 2020") == date(2020, 9, 1)
        assert _parse_date("Sept 2020") == date(2020, 9, 1)


# =============================================================================
# Property Tests for _parse_date
# =============================================================================


@settings(max_examples=100, deadline=None)
@given(
    month=st.sampled_from(
        [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ]
    ),
    year=st.integers(min_value=1950, max_value=2030),
)
def test_property_abbreviated_month_year_parsed(month: str, year: int):
    """
    Property: Abbreviated month + year format is correctly parsed.
    Validates: Requirement 4.2
    """
    date_str = f"{month} {year}"
    result = _parse_date(date_str)

    assert result is not None
    assert result.year == year
    assert result.day == 1


@settings(max_examples=100, deadline=None)
@given(
    month=st.sampled_from(
        [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ]
    ),
    year=st.integers(min_value=1950, max_value=2030),
)
def test_property_full_month_year_parsed(month: str, year: int):
    """
    Property: Full month name + year format is correctly parsed.
    Validates: Requirement 4.2
    """
    date_str = f"{month} {year}"
    result = _parse_date(date_str)

    assert result is not None
    assert result.year == year
    assert result.day == 1


@settings(max_examples=50, deadline=None)
@given(year=st.integers(min_value=1950, max_value=2030))
def test_property_year_only_parsed(year: int):
    """
    Property: Year-only format is correctly parsed to January 1st.
    Validates: Requirement 4.2
    """
    date_str = str(year)
    result = _parse_date(date_str)

    assert result is not None
    assert result.year == year
    assert result.month == 1
    assert result.day == 1


@settings(max_examples=20, deadline=None)
@given(
    present_variant=st.sampled_from(
        ["Present", "present", "PRESENT", "Current", "current", "Now", "now"]
    ),
)
def test_property_present_returns_none(present_variant: str):
    """
    Property: 'Present' variants return None (indicating current).
    Validates: Requirement 4.2
    """
    result = _parse_date(present_variant)
    assert result is None


# =============================================================================
# Unit Tests for _convert_experiences
# =============================================================================


class TestConvertExperiences:
    """Unit tests for experience conversion."""

    def test_convert_empty_list(self):
        """Convert empty experience list."""
        result = _convert_experiences([])
        assert result == []

    def test_convert_none(self):
        """Convert None experience list."""
        result = _convert_experiences(None)
        assert result == []

    def test_convert_single_experience(self):
        """Convert a single experience."""
        exp = MagicMock()
        exp.institution_name = "Acme Corp"
        exp.position_title = "Software Engineer"
        exp.description = "Built amazing things"
        exp.location = "San Francisco, CA"
        exp.from_date = "Jan 2020"
        exp.to_date = "Dec 2022"

        result = _convert_experiences([exp])

        assert len(result) == 1
        position = result[0]
        assert position.company_name == "Acme Corp"
        assert position.title == "Software Engineer"
        assert position.description == "Built amazing things"
        assert position.location == "San Francisco, CA"
        assert position.start_date == date(2020, 1, 1)
        assert position.end_date == date(2022, 12, 1)

    def test_convert_experience_with_present(self):
        """Convert experience with 'Present' end date."""
        exp = MagicMock()
        exp.institution_name = "Current Company"
        exp.position_title = "Lead Developer"
        exp.description = "Leading development"
        exp.location = "Remote"
        exp.from_date = "Jun 2023"
        exp.to_date = "Present"

        result = _convert_experiences([exp])

        assert len(result) == 1
        position = result[0]
        assert position.end_date is None

    def test_convert_experience_with_missing_fields(self):
        """Convert experience with missing optional fields."""
        exp = MagicMock()
        exp.institution_name = "Company"
        exp.position_title = "Title"
        exp.description = None
        exp.location = None
        exp.from_date = None
        exp.to_date = None

        result = _convert_experiences([exp])

        assert len(result) == 1
        position = result[0]
        assert position.company_name == "Company"
        assert position.title == "Title"
        assert position.description is None
        assert position.location is None
        assert position.start_date is None
        assert position.end_date is None


# =============================================================================
# Unit Tests for _convert_education_list
# =============================================================================


class TestConvertEducationList:
    """Unit tests for education conversion."""

    def test_convert_empty_list(self):
        """Convert empty education list."""
        result = _convert_education_list([])
        assert result == []

    def test_convert_none(self):
        """Convert None education list."""
        result = _convert_education_list(None)
        assert result == []

    def test_convert_single_education(self):
        """Convert a single education entry."""
        edu = MagicMock()
        edu.institution_name = "MIT"
        edu.degree = "Bachelor of Science in Computer Science"
        edu.description = "Focus on AI and ML"
        edu.from_date = "Sep 2015"
        edu.to_date = "May 2019"

        result = _convert_education_list([edu])

        assert len(result) == 1
        education = result[0]
        assert education.school == "MIT"
        assert education.degree == "Bachelor of Science in Computer Science"
        assert education.description == "Focus on AI and ML"
        assert education.start_date == date(2015, 9, 1)
        assert education.end_date == date(2019, 5, 1)

    def test_convert_education_with_missing_fields(self):
        """Convert education with missing optional fields."""
        edu = MagicMock()
        edu.institution_name = "University"
        edu.degree = None
        edu.description = None
        edu.from_date = None
        edu.to_date = None

        result = _convert_education_list([edu])

        assert len(result) == 1
        education = result[0]
        assert education.school == "University"
        assert education.degree is None
        assert education.description is None


# =============================================================================
# Unit Tests for _extract_skills
# =============================================================================


class TestExtractSkills:
    """Unit tests for skill extraction."""

    def test_extract_from_skills_list_strings(self):
        """Extract skills from a list of strings."""
        person = MagicMock()
        person.skills = ["Python", "JavaScript", "React"]
        person.interests = []

        result = _extract_skills(person)

        skill_names = {s.name for s in result}
        assert "Python" in skill_names
        assert "JavaScript" in skill_names
        assert "React" in skill_names

    def test_extract_from_skills_list_objects(self):
        """Extract skills from a list of objects with name attribute."""
        skill1 = MagicMock()
        skill1.name = "Python"
        skill2 = MagicMock()
        skill2.name = "JavaScript"

        person = MagicMock()
        person.skills = [skill1, skill2]
        person.interests = []

        result = _extract_skills(person)

        skill_names = {s.name for s in result}
        assert "Python" in skill_names
        assert "JavaScript" in skill_names

    def test_extract_from_interests(self):
        """Extract skills from interests list."""
        person = MagicMock()
        person.skills = []
        person.interests = ["Machine Learning", "Cloud Computing"]

        result = _extract_skills(person)

        skill_names = {s.name for s in result}
        assert "Machine Learning" in skill_names
        assert "Cloud Computing" in skill_names

    def test_combine_skills_and_interests(self):
        """Combine skills and interests, deduplicating."""
        person = MagicMock()
        person.skills = ["Python", "JavaScript"]
        person.interests = ["Python", "AI"]  # Python is duplicate

        result = _extract_skills(person)

        skill_names = [s.name for s in result]
        # Should have Python only once
        assert skill_names.count("Python") == 1
        assert "JavaScript" in skill_names
        assert "AI" in skill_names

    def test_extract_empty_skills(self):
        """Extract from empty skills and interests."""
        person = MagicMock()
        person.skills = []
        person.interests = []

        result = _extract_skills(person)

        assert result == []

    def test_extract_none_skills(self):
        """Handle None skills and interests."""
        person = MagicMock()
        person.skills = None
        person.interests = None

        result = _extract_skills(person)

        assert result == []

    def test_filter_empty_skill_names(self):
        """Filter out empty skill names."""
        person = MagicMock()
        person.skills = ["Python", "", "  ", "JavaScript"]
        person.interests = []

        result = _extract_skills(person)

        skill_names = {s.name for s in result}
        # Empty strings should be filtered
        assert "" not in skill_names
        assert "Python" in skill_names
        assert "JavaScript" in skill_names


# =============================================================================
# Unit Tests for convert_person_to_profile
# =============================================================================


class TestConvertPersonToProfile:
    """Unit tests for full Person to LinkedInProfile conversion."""

    def test_convert_complete_person(self):
        """Convert a fully populated Person object."""
        # Create mock experiences
        exp = MagicMock()
        exp.institution_name = "Tech Corp"
        exp.position_title = "Senior Developer"
        exp.description = "Led a team of 5"
        exp.location = "NYC"
        exp.from_date = "Jan 2020"
        exp.to_date = "Present"

        # Create mock education
        edu = MagicMock()
        edu.institution_name = "Stanford University"
        edu.degree = "M.S. Computer Science"
        edu.description = None
        edu.from_date = "Sep 2016"
        edu.to_date = "Jun 2018"

        # Create mock person
        person = MagicMock()
        person.name = "John Doe"
        person.linkedin_url = "https://www.linkedin.com/in/johndoe"
        person.job_title = "Senior Developer at Tech Corp"
        person.about = "Passionate developer with 10+ years experience"
        person.location = "New York, NY"
        person.experiences = [exp]
        person.educations = [edu]
        person.skills = ["Python", "Go", "Kubernetes"]
        person.interests = []

        result = convert_person_to_profile(person, "john@example.com")

        assert isinstance(result, LinkedInProfile)
        assert result.profile_id == "johndoe"
        assert result.first_name == "John"
        assert result.last_name == "Doe"
        assert result.email == "john@example.com"
        assert result.headline == "Senior Developer at Tech Corp"
        assert result.summary == "Passionate developer with 10+ years experience"
        assert result.location == "New York, NY"

        assert len(result.positions) == 1
        assert result.positions[0].company_name == "Tech Corp"
        assert result.positions[0].title == "Senior Developer"

        assert len(result.education) == 1
        assert result.education[0].school == "Stanford University"

        skill_names = {s.name for s in result.skills}
        assert "Python" in skill_names
        assert "Go" in skill_names
        assert "Kubernetes" in skill_names

    def test_convert_minimal_person(self):
        """Convert a Person with minimal data."""
        person = MagicMock()
        person.name = "Jane"
        person.linkedin_url = "https://linkedin.com/in/jane"
        person.job_title = None
        person.about = None
        person.location = None
        person.experiences = []
        person.educations = []
        person.skills = []
        person.interests = []

        result = convert_person_to_profile(person, "jane@example.com")

        assert result.profile_id == "jane"
        assert result.first_name == "Jane"
        assert result.last_name == ""
        assert result.email == "jane@example.com"
        assert result.headline == ""
        assert result.summary == ""
        assert result.positions == []
        assert result.education == []
        assert result.skills == []

    def test_convert_person_with_no_name(self):
        """Convert a Person with no name."""
        person = MagicMock()
        person.name = None
        person.linkedin_url = "https://linkedin.com/in/unknown"
        person.job_title = "Developer"
        person.about = "About me"
        person.location = None
        person.experiences = []
        person.educations = []
        person.skills = []
        person.interests = []

        result = convert_person_to_profile(person, "unknown@example.com")

        assert result.first_name == ""
        assert result.last_name == ""


# =============================================================================
# Integration Tests: Adapter Output Compatible with Mapper
# =============================================================================


class TestAdapterMapperIntegration:
    """Integration tests verifying adapter output works with the mapper."""

    def test_converted_profile_compatible_with_mapper(self):
        """
        Integration test: Converted profile is compatible with map_profile_to_database.
        Validates: Requirements 4.1, 4.2, 4.3, 4.5

        This test verifies the complete flow from Person → LinkedInProfile → Database models.
        """
        # Create a realistic mock Person
        exp1 = MagicMock()
        exp1.institution_name = "Google"
        exp1.position_title = "Software Engineer"
        exp1.description = "Worked on Search infrastructure"
        exp1.location = "Mountain View, CA"
        exp1.from_date = "Jun 2018"
        exp1.to_date = "Present"

        exp2 = MagicMock()
        exp2.institution_name = "Facebook"
        exp2.position_title = "Junior Developer"
        exp2.description = "Built features for Messenger"
        exp2.location = "Menlo Park, CA"
        exp2.from_date = "Jan 2016"
        exp2.to_date = "May 2018"

        edu = MagicMock()
        edu.institution_name = "UC Berkeley"
        edu.degree = "B.S. Computer Science"
        edu.description = "Graduated with honors"
        edu.from_date = "Aug 2012"
        edu.to_date = "May 2016"

        person = MagicMock()
        person.name = "Alex Johnson"
        person.linkedin_url = "https://www.linkedin.com/in/alexjohnson"
        person.job_title = "Software Engineer at Google"
        person.about = (
            "Experienced software engineer passionate about building scalable systems."
        )
        person.location = "San Francisco Bay Area"
        person.experiences = [exp1, exp2]
        person.educations = [edu]
        person.skills = ["Python", "Java", "Distributed Systems", "Kubernetes"]
        person.interests = ["Open Source", "Machine Learning"]

        # Convert Person to LinkedInProfile using the adapter
        profile = convert_person_to_profile(person, "alex.johnson@email.com")

        # Verify the profile is well-formed
        assert profile.profile_id == "alexjohnson"
        assert profile.first_name == "Alex"
        assert profile.last_name == "Johnson"
        assert profile.email == "alex.johnson@email.com"
        assert len(profile.positions) == 2
        assert len(profile.education) == 1
        assert len(profile.skills) >= 4  # At least the 4 skills

        # Pass to mapper - this should NOT raise any exceptions
        (
            user_data,
            projects,
            experiences,
            educations,
            certifications,
            skills,
        ) = map_profile_to_database(profile)

        # Verify user data
        assert user_data.email == "alex.johnson@email.com"
        assert user_data.name == "Alex Johnson"
        assert "Software Engineer at Google" in user_data.bio

        # Verify experiences (positions become experiences)
        assert len(experiences) == 2

        # Find the Google experience
        google_experiences = [e for e in experiences if "Google" in e.company]
        assert len(google_experiences) == 1
        assert "Software Engineer" in google_experiences[0].position

        # Verify education
        assert len(educations) == 1
        assert "UC Berkeley" in educations[0].school

        # Verify skills
        assert len(skills) >= 4

    def test_empty_profile_compatible_with_mapper(self):
        """
        Integration test: Empty profile still works with mapper.
        Validates: Requirement 4.5
        """
        person = MagicMock()
        person.name = "Empty Profile"
        person.linkedin_url = "https://linkedin.com/in/empty"
        person.job_title = None
        person.about = None
        person.location = None
        person.experiences = []
        person.educations = []
        person.skills = []
        person.interests = []

        profile = convert_person_to_profile(person, "empty@example.com")

        # Should not raise
        (
            user_data,
            projects,
            experiences,
            educations,
            certifications,
            skills,
        ) = map_profile_to_database(profile)

        assert user_data.email == "empty@example.com"
        assert user_data.name == "Empty Profile"
        assert projects == []
        assert experiences == []
        assert educations == []

    def test_profile_with_special_characters(self):
        """
        Integration test: Profile with special characters in names.
        Validates: Requirement 4.1
        """
        person = MagicMock()
        person.name = "José García-López"
        person.linkedin_url = "https://linkedin.com/in/jose-garcia"
        person.job_title = "Développeur Senior"
        person.about = "Développement de logiciels pour l'industrie"
        person.location = "Paris, France"
        person.experiences = []
        person.educations = []
        person.skills = ["C++", "Python"]
        person.interests = []

        profile = convert_person_to_profile(person, "jose@example.com")

        assert profile.first_name == "José"
        assert profile.last_name == "García-López"

        # Should work with mapper
        (
            user_data,
            projects,
            experiences,
            educations,
            certifications,
            skills,
        ) = map_profile_to_database(profile)

        assert "José García-López" in user_data.name
        assert "Développeur Senior" in user_data.bio


# =============================================================================
# Property Tests for Full Conversion
# =============================================================================


def _create_mock_person(
    name: str,
    url: str,
    job_title: Optional[str] = None,
    about: Optional[str] = None,
    location: Optional[str] = None,
    experiences: Optional[list] = None,
    educations: Optional[list] = None,
    skills: Optional[list] = None,
    interests: Optional[list] = None,
) -> MagicMock:
    """Helper to create mock Person objects."""
    person = MagicMock()
    person.name = name
    person.linkedin_url = url
    person.job_title = job_title
    person.about = about
    person.location = location
    person.experiences = experiences or []
    person.educations = educations or []
    person.skills = skills or []
    person.interests = interests or []
    return person


@settings(max_examples=50, deadline=None)
@given(
    first=st.text(
        alphabet=st.characters(
            whitelist_categories=("L",), min_codepoint=65, max_codepoint=122
        ),
        min_size=1,
        max_size=15,
    ).filter(lambda x: x.strip()),
    last=st.text(
        alphabet=st.characters(
            whitelist_categories=("L",), min_codepoint=65, max_codepoint=122
        ),
        min_size=1,
        max_size=15,
    ).filter(lambda x: x.strip()),
    username=st.text(
        alphabet=st.characters(
            whitelist_categories=("L", "N"), min_codepoint=48, max_codepoint=122
        ),
        min_size=3,
        max_size=20,
    ).filter(lambda x: x.strip() and x.isalnum()),
    email=st.emails(),
)
def test_property_conversion_preserves_identity(
    first: str, last: str, username: str, email: str
):
    """
    Property: Conversion preserves name, email, and profile ID.
    Validates: Requirement 4.1
    """
    full_name = f"{first} {last}"
    url = f"https://linkedin.com/in/{username}"

    person = _create_mock_person(name=full_name, url=url)
    profile = convert_person_to_profile(person, email)

    assert profile.first_name == first
    assert profile.last_name == last
    assert profile.email == email
    assert profile.profile_id == username


@settings(max_examples=30, deadline=None)
@given(
    num_experiences=st.integers(min_value=0, max_value=5),
    num_educations=st.integers(min_value=0, max_value=3),
)
def test_property_conversion_preserves_counts(
    num_experiences: int, num_educations: int
):
    """
    Property: Conversion preserves the count of experiences and educations.
    Validates: Requirements 4.2, 4.3
    """
    experiences = []
    for i in range(num_experiences):
        exp = MagicMock()
        exp.institution_name = f"Company{i}"
        exp.position_title = f"Title{i}"
        exp.description = None
        exp.location = None
        exp.from_date = None
        exp.to_date = None
        experiences.append(exp)

    educations = []
    for i in range(num_educations):
        edu = MagicMock()
        edu.institution_name = f"School{i}"
        edu.degree = f"Degree{i}"
        edu.description = None
        edu.from_date = None
        edu.to_date = None
        educations.append(edu)

    person = _create_mock_person(
        name="Test User",
        url="https://linkedin.com/in/testuser",
        experiences=experiences,
        educations=educations,
    )

    profile = convert_person_to_profile(person, "test@example.com")

    assert len(profile.positions) == num_experiences
    assert len(profile.education) == num_educations


@settings(max_examples=30, deadline=None)
@given(
    skills=st.lists(
        st.text(
            alphabet=st.characters(
                whitelist_categories=("L",), min_codepoint=65, max_codepoint=122
            ),
            min_size=2,
            max_size=20,
        ).filter(lambda x: x.strip()),
        min_size=0,
        max_size=10,
        unique=True,
    ),
)
def test_property_skills_preserved(skills: list):
    """
    Property: All unique skills are preserved in conversion.
    Validates: Requirement 4.4
    """
    person = _create_mock_person(
        name="Skill Person",
        url="https://linkedin.com/in/skillperson",
        skills=skills,
    )

    profile = convert_person_to_profile(person, "skills@example.com")

    profile_skill_names = {s.name for s in profile.skills}
    input_skill_names = {s for s in skills if s.strip()}

    assert profile_skill_names == input_skill_names


@settings(max_examples=20, deadline=None)
@given(
    first=st.text(
        alphabet=st.characters(
            whitelist_categories=("L",), min_codepoint=65, max_codepoint=90
        ),
        min_size=1,
        max_size=10,
    ).filter(lambda x: x.strip()),
    last=st.text(
        alphabet=st.characters(
            whitelist_categories=("L",), min_codepoint=65, max_codepoint=90
        ),
        min_size=1,
        max_size=10,
    ).filter(lambda x: x.strip()),
)
def test_property_converted_profile_works_with_mapper(first: str, last: str):
    """
    Property: Converted profile can be passed to map_profile_to_database without error.
    Validates: Requirement 4.5
    """
    full_name = f"{first} {last}"

    person = _create_mock_person(
        name=full_name,
        url=f"https://linkedin.com/in/{first.lower()}{last.lower()}",
        job_title="Developer",
        about="About text",
    )

    profile = convert_person_to_profile(person, f"{first.lower()}@example.com")

    # This should not raise any exception
    (
        user_data,
        projects,
        experiences,
        educations,
        certifications,
        skills,
    ) = map_profile_to_database(profile)

    assert user_data is not None
    assert isinstance(projects, list)
    assert isinstance(experiences, list)
    assert isinstance(educations, list)
    assert isinstance(certifications, list)
    assert isinstance(skills, list)
    assert f"{first} {last}" in user_data.name
