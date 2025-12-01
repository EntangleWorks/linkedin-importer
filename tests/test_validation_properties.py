"""Property-based tests for data validation."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from linkedin_importer.errors import ValidationError
from linkedin_importer.models import LinkedInProfile
from linkedin_importer.validation import (
    validate_profile_urls,
    validate_required_fields,
)


# Feature: linkedin-profile-importer, Property 2: Required field validation
# Validates: Requirements 1.2
@given(
    first_name=st.one_of(
        st.just(""),  # Empty string
        st.from_regex(r"^\s+$", fullmatch=True),  # Whitespace only
        st.none(),  # None value
    ),
    last_name=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
    email=st.emails(),
)
def test_missing_first_name_validation(first_name, last_name: str, email: str) -> None:
    """For any profile with missing or empty first_name, validation should fail."""
    profile = LinkedInProfile(
        profile_id="test123",
        first_name=first_name,
        last_name=last_name,
        email=email,
    )

    with pytest.raises(ValidationError) as exc_info:
        validate_required_fields(profile)

    # Verify error message mentions first_name
    error = exc_info.value
    assert error.error_type == "validation"
    assert "first_name" in str(error.details).lower()


# Feature: linkedin-profile-importer, Property 2: Required field validation
# Validates: Requirements 1.2
@given(
    first_name=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
    last_name=st.one_of(
        st.just(""),  # Empty string
        st.from_regex(r"^\s+$", fullmatch=True),  # Whitespace only
        st.none(),  # None value
    ),
    email=st.emails(),
)
def test_missing_last_name_validation(first_name: str, last_name, email: str) -> None:
    """For any profile with missing or empty last_name, validation should fail."""
    profile = LinkedInProfile(
        profile_id="test123",
        first_name=first_name,
        last_name=last_name,
        email=email,
    )

    with pytest.raises(ValidationError) as exc_info:
        validate_required_fields(profile)

    # Verify error message mentions last_name
    error = exc_info.value
    assert error.error_type == "validation"
    assert "last_name" in str(error.details).lower()


# Feature: linkedin-profile-importer, Property 2: Required field validation
# Validates: Requirements 1.2
@given(
    first_name=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
    last_name=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
    email=st.one_of(
        st.just(""),  # Empty string
        st.from_regex(r"^\s+$", fullmatch=True),  # Whitespace only
        st.none(),  # None value
    ),
)
def test_missing_email_validation(first_name: str, last_name: str, email) -> None:
    """For any profile with missing or empty email, validation should fail."""
    profile = LinkedInProfile(
        profile_id="test123",
        first_name=first_name,
        last_name=last_name,
        email=email,
    )

    with pytest.raises(ValidationError) as exc_info:
        validate_required_fields(profile)

    # Verify error message mentions email
    error = exc_info.value
    assert error.error_type == "validation"
    assert "email" in str(error.details).lower()


# Feature: linkedin-profile-importer, Property 2: Required field validation
# Validates: Requirements 1.2
@given(
    first_name=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
    last_name=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
    # Generate invalid email formats
    email=st.one_of(
        st.text(min_size=1, max_size=20).filter(lambda x: "@" not in x),  # No @ symbol
        st.from_regex(r"^[^@]+@$", fullmatch=True),  # Missing domain
        st.from_regex(r"^@[^@]+$", fullmatch=True),  # Missing local part
        st.just("test@"),  # Ends with @
        st.just("@test"),  # Starts with @
        st.just("test@@test.com"),  # Double @
        st.just("test test@test.com"),  # Space in local part
    ),
)
def test_invalid_email_format_validation(
    first_name: str, last_name: str, email: str
) -> None:
    """For any profile with improperly formatted email, validation should fail."""
    profile = LinkedInProfile(
        profile_id="test123",
        first_name=first_name,
        last_name=last_name,
        email=email,
    )

    with pytest.raises(ValidationError) as exc_info:
        validate_required_fields(profile)

    # Verify error message mentions email validation
    error = exc_info.value
    assert error.error_type == "validation"
    assert "email" in str(error.details).lower()


# Feature: linkedin-profile-importer, Property 2: Required field validation
# Validates: Requirements 1.2
@given(
    first_name=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
    last_name=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
    email=st.emails(),
)
def test_valid_required_fields(first_name: str, last_name: str, email: str) -> None:
    """For any profile with all required fields properly formatted, validation should pass."""
    profile = LinkedInProfile(
        profile_id="test123",
        first_name=first_name,
        last_name=last_name,
        email=email,
    )

    # Should not raise any exception
    validate_required_fields(profile)


# Feature: linkedin-profile-importer, Property 11: URL validation
# Validates: Requirements 4.5
@given(
    profile_picture_url=st.one_of(
        st.just("http://example.com/image.jpg"),
        st.just("https://example.com/image.jpg"),
        st.none(),  # None is valid (optional field)
    ),
)
def test_valid_profile_picture_url(profile_picture_url) -> None:
    """For any valid HTTP/HTTPS URL or None, URL validation should pass."""
    profile = LinkedInProfile(
        profile_id="test123",
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        profile_picture_url=profile_picture_url,
    )

    # Should not raise any exception
    validate_profile_urls(profile)


# Feature: linkedin-profile-importer, Property 11: URL validation
# Validates: Requirements 4.5
@given(
    # Generate invalid URLs
    invalid_url=st.one_of(
        st.just("ftp://example.com"),  # Wrong scheme
        st.just("not-a-url"),  # No scheme
        st.just("http://"),  # Missing netloc
        st.just("https://"),  # Missing netloc
        st.just("javascript:alert(1)"),  # Invalid scheme
        st.just("file:///etc/passwd"),  # File scheme
        st.text(min_size=1, max_size=20).filter(
            lambda x: "://" not in x
        ),  # No scheme separator
    ),
)
def test_invalid_profile_picture_url(invalid_url: str) -> None:
    """For any invalid URL in profile_picture_url, validation should fail."""
    profile = LinkedInProfile(
        profile_id="test123",
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        profile_picture_url=invalid_url,
    )

    with pytest.raises(ValidationError) as exc_info:
        validate_profile_urls(profile)

    # Verify error message mentions URL validation
    error = exc_info.value
    assert error.error_type == "validation"
    assert "url" in str(error.details).lower()


# Feature: linkedin-profile-importer, Property 11: URL validation
# Validates: Requirements 4.5
@given(
    # Generate valid HTTP/HTTPS URLs
    company_url=st.one_of(
        st.from_regex(r"^https?://[a-z0-9]+\.[a-z]{2,}(/.*)?$", fullmatch=True),
        st.none(),  # None is valid (optional field)
    ),
)
def test_valid_position_company_url(company_url) -> None:
    """For any valid HTTP/HTTPS URL or None in position, URL validation should pass."""
    from linkedin_importer.models import Position

    profile = LinkedInProfile(
        profile_id="test123",
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        positions=[
            Position(
                company_name="Test Company",
                title="Engineer",
                company_url=company_url,
            )
        ],
    )

    # Should not raise any exception
    validate_profile_urls(profile)


# Feature: linkedin-profile-importer, Property 11: URL validation
# Validates: Requirements 4.5
@given(
    # Generate invalid URLs
    invalid_url=st.one_of(
        st.just("ftp://example.com"),  # Wrong scheme
        st.just("not-a-url"),  # No scheme
        st.just("http://"),  # Missing netloc
        st.text(min_size=1, max_size=20).filter(
            lambda x: "://" not in x and x.strip()
        ),  # No scheme
    ),
)
def test_invalid_position_company_url(invalid_url: str) -> None:
    """For any invalid URL in position company_url, validation should fail."""
    from linkedin_importer.models import Position

    profile = LinkedInProfile(
        profile_id="test123",
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        positions=[
            Position(
                company_name="Test Company",
                title="Engineer",
                company_url=invalid_url,
            )
        ],
    )

    with pytest.raises(ValidationError) as exc_info:
        validate_profile_urls(profile)

    # Verify error message mentions URL validation
    error = exc_info.value
    assert error.error_type == "validation"
    assert "url" in str(error.details).lower()


# Feature: linkedin-profile-importer, Property 11: URL validation
# Validates: Requirements 4.5
@given(
    # Generate invalid URLs for certification
    invalid_url=st.one_of(
        st.just("ftp://example.com"),
        st.just("not-a-url"),
        st.just("http://"),
        st.text(min_size=1, max_size=20).filter(lambda x: "://" not in x and x.strip()),
    ),
)
def test_invalid_certification_url(invalid_url: str) -> None:
    """For any invalid URL in certification, validation should fail."""
    from linkedin_importer.models import Certification

    profile = LinkedInProfile(
        profile_id="test123",
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        certifications=[
            Certification(
                name="Test Cert",
                authority="Test Authority",
                url=invalid_url,
            )
        ],
    )

    with pytest.raises(ValidationError) as exc_info:
        validate_profile_urls(profile)

    # Verify error message mentions URL validation
    error = exc_info.value
    assert error.error_type == "validation"
    assert "url" in str(error.details).lower()


# Feature: linkedin-profile-importer, Property 11: URL validation
# Validates: Requirements 4.5
@given(
    # Generate invalid URLs for publication
    invalid_url=st.one_of(
        st.just("ftp://example.com"),
        st.just("not-a-url"),
        st.just("http://"),
        st.text(min_size=1, max_size=20).filter(lambda x: "://" not in x and x.strip()),
    ),
)
def test_invalid_publication_url(invalid_url: str) -> None:
    """For any invalid URL in publication, validation should fail."""
    from linkedin_importer.models import Publication

    profile = LinkedInProfile(
        profile_id="test123",
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        publications=[
            Publication(
                name="Test Publication",
                url=invalid_url,
            )
        ],
    )

    with pytest.raises(ValidationError) as exc_info:
        validate_profile_urls(profile)

    # Verify error message mentions URL validation
    error = exc_info.value
    assert error.error_type == "validation"
    assert "url" in str(error.details).lower()
