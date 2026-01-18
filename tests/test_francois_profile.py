"""Test script to simulate LinkedIn profile import for Francois Van Wyk.

This test uses the profile data provided to verify the mapper and identify issues
with the current importer implementation.
"""

import json
from datetime import date, datetime
from pathlib import Path

import pytest

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


def create_francois_profile() -> LinkedInProfile:
    """Create a LinkedInProfile object matching Francois Van Wyk's data."""

    positions = [
        Position(
            company_name="Komodo",
            title="Frontend Developer",
            description="Maintaining and creating new features in the cross-platform Flutter code base using clean architecture (Flutter Bloc), SOLID principles, and design patterns",
            responsibilities="""- Redundant APIs with failover, graceful degradation, and exponential backoff as the default for all 3rd party services (onramp, market data)
- Maintaining, and integrating a new SDK with a gradual deprecation and migration of existing functionality
- Creation and maintenance of a CLI tool for summarising dependency changes between branches or commits for security review purposes
- Maintenance, redesign, and fault-tolerance improvements of on-ramp payment portals
- WalletConnect integration
- Hardware wallet (Trezor) support & integration
- Automated trading bot integration
- Cross-platform FFI interface with embedded Rust backend layer
- Cross-platform testing via Virtual Machines maintained through Proxmox
- LLM Agent assisted spec-driven development alongside automated testing and reporting
- Custom token import, storage, and injection into runtime
- Bespoke asset activation pipeline with configuration file downloads
- Configuring, maintaining, and securing a decentralized network node on dedicated hardware with Yubikey SSH authentication
- Maintaining and creating CI pipelines for cross platform and containerised builds (Docker)
- Maintaining and creating automated tests (unit and integration tests)""",
            start_date=date(2023, 12, 1),
            end_date=None,
            location="Gauteng, South Africa",
            employment_type="Full-time",
            company_url="https://komodoplatform.com",
            company_logo_url=None,
        ),
        Position(
            company_name="Docwize- H&M Information Management Services",
            title="Software Engineer",
            description="Maintain .NET C# web services and full-stack development using React and Python",
            responsibilities="""- Migrate features from C# web services to Python API (FastAPI)
- Full-stack development of new features using React and Python
- Create and maintain data ingestion pipelines, primarily for email archives (Lotus Notes and PST)""",
            start_date=date(2022, 6, 1),
            end_date=date(2023, 12, 1),
            location="City of Johannesburg, Gauteng, South Africa",
            employment_type="Full-time",
            company_url=None,
            company_logo_url=None,
        ),
        Position(
            company_name="Docwize- H&M Information Management Services",
            title="Data Engineer",
            description="Create and maintain data ingestion pipelines using Python and C# with Aspose",
            responsibilities="""- Create and maintain dashboards for analytics and machine learning workflows
- Assist with full-stack development before transitioning to full-time backend development""",
            start_date=date(2021, 11, 1),
            end_date=date(2022, 5, 1),
            location="City of Johannesburg, Gauteng, South Africa",
            employment_type="Full-time",
            company_url=None,
            company_logo_url=None,
        ),
        Position(
            company_name="PSG Wealth",
            title="Graduate Data Scientist",
            description="Create and maintain Power BI reports and automate data capture, analysis, and reporting",
            responsibilities="""- Automate data capture, analysis, and reporting using Python and Microsoft Excel
- Research data science department best practices, roles and applications
- Agile environment with related ceremonies (standup, planning, backlog refinement, etc.)""",
            start_date=date(2021, 1, 1),
            end_date=date(2021, 10, 1),
            location="Midrand, Gauteng, South Africa",
            employment_type="Full-time",
            company_url=None,
            company_logo_url=None,
        ),
    ]

    education = [
        Education(
            school="University of Pretoria/Universiteit van Pretoria",
            degree="Bachelor of Engineering - BE",
            field_of_study="Computer Engineering",
            start_date=date(2017, 1, 1),
            end_date=date(2020, 12, 31),
            grade=None,
            activities=None,
            description=None,
        ),
        Education(
            school="Pretoria Boys Highschool",
            degree="Matric Certificate",
            field_of_study=None,
            start_date=date(2012, 1, 1),
            end_date=date(2016, 12, 31),
            grade=None,
            activities=None,
            description=None,
        ),
    ]

    skills = [
        Skill(name="Design Patterns", endorsement_count=None),
        Skill(name="Front-End Development", endorsement_count=None),
        Skill(name="SOLID Design Principles", endorsement_count=None),
    ]

    certifications = [
        Certification(
            name="Rust Fundamentals",
            authority="Unknown",  # Not provided in the PDF
            license_number=None,
            start_date=None,
            end_date=None,
            url=None,
        ),
        Certification(
            name="Protection of Personal Information Act",
            authority="Unknown",
            license_number=None,
            start_date=None,
            end_date=None,
            url=None,
        ),
        Certification(
            name="Data Engineering with Rust",
            authority="Unknown",
            license_number=None,
            start_date=None,
            end_date=None,
            url=None,
        ),
        Certification(
            name="Kubernetes for the Absolute Beginners - Hands-on",
            authority="Unknown",
            license_number=None,
            start_date=None,
            end_date=None,
            url=None,
        ),
        Certification(
            name="Completed Course: Learn Parallel Programming with C# and .NET",
            authority="Unknown",
            license_number=None,
            start_date=None,
            end_date=None,
            url=None,
        ),
    ]

    return LinkedInProfile(
        profile_id="francois-van-wyk",
        first_name="Francois",
        last_name="Van Wyk",
        email="francoisvw@protonmail.com",
        headline="Software Engineer at Komodo Platform",
        summary="WIP",
        location="Pretoria, Gauteng, South Africa",
        industry="Technology",
        profile_picture_url=None,
        positions=positions,
        education=education,
        skills=skills,
        certifications=certifications,
        publications=[],
        volunteer=[],
        honors=[],
        languages=[],
    )


class TestFrancoisProfileMapping:
    """Test suite for verifying profile mapping with Francois Van Wyk's data."""

    def test_profile_creation(self):
        """Test that the profile can be created successfully."""
        profile = create_francois_profile()

        assert profile.first_name == "Francois"
        assert profile.last_name == "Van Wyk"
        assert profile.email == "francoisvw@protonmail.com"
        assert len(profile.positions) == 4
        assert len(profile.education) == 2
        assert len(profile.skills) == 3
        assert len(profile.certifications) == 5

    def test_mapping_produces_user_data(self):
        """Test that mapping produces correct user data."""
        profile = create_francois_profile()
        (
            user_data,
            projects_data,
            experiences_data,
            educations_data,
            certifications_data,
            skills_data,
        ) = map_profile_to_database(profile)

        assert user_data.email == "francoisvw@protonmail.com"
        assert user_data.name == "Francois Van Wyk"
        assert "Software Engineer at Komodo Platform" in user_data.bio
        assert user_data.avatar_url is None

    def test_mapping_produces_correct_number_of_projects(self):
        """Test that mapping produces correct counts of experiences and certifications."""
        profile = create_francois_profile()
        (
            user_data,
            projects_data,
            experiences_data,
            educations_data,
            certifications_data,
            skills_data,
        ) = map_profile_to_database(profile)

        # 4 positions become 4 experiences
        assert len(experiences_data) == 4, (
            f"Expected 4 experiences, got {len(experiences_data)}"
        )
        # 5 certifications
        assert len(certifications_data) == 5, (
            f"Expected 5 certifications, got {len(certifications_data)}"
        )

    def test_position_mapping(self):
        """Test that positions are correctly mapped to experiences."""
        profile = create_francois_profile()
        (
            user_data,
            projects_data,
            experiences_data,
            educations_data,
            certifications_data,
            skills_data,
        ) = map_profile_to_database(profile)

        assert len(experiences_data) == 4

        # Check Komodo position
        komodo_exp = next((e for e in experiences_data if "Komodo" in e.company), None)
        assert komodo_exp is not None, "Komodo experience not found"
        assert "Frontend Developer" in komodo_exp.position

    def test_certification_mapping(self):
        """Test that certifications are correctly mapped."""
        profile = create_francois_profile()
        (
            user_data,
            projects_data,
            experiences_data,
            educations_data,
            certifications_data,
            skills_data,
        ) = map_profile_to_database(profile)

        assert len(certifications_data) == 5

        # Check specific certifications
        rust_cert = next((c for c in certifications_data if "Rust" in c.name), None)
        assert rust_cert is not None, "Rust Fundamentals certification not found"

    def test_skills_mapped(self):
        """Test that skills are correctly mapped."""
        profile = create_francois_profile()
        (
            user_data,
            projects_data,
            experiences_data,
            educations_data,
            certifications_data,
            skills_data,
        ) = map_profile_to_database(profile)

        # Verify skills are mapped
        assert len(skills_data) == 3, f"Expected 3 skills, got {len(skills_data)}"

        # Verify skill names
        skill_names = [s.name for s in skills_data]
        assert "Design Patterns" in skill_names, "Design Patterns skill not found"
        assert "Front-End Development" in skill_names, (
            "Front-End Development skill not found"
        )
        assert "SOLID Design Principles" in skill_names, (
            "SOLID Design Principles skill not found"
        )

    def test_experience_has_company_names(self):
        """Test that experiences have proper company names."""
        profile = create_francois_profile()
        (
            user_data,
            projects_data,
            experiences_data,
            educations_data,
            certifications_data,
            skills_data,
        ) = map_profile_to_database(profile)

        # Each experience should have a company name
        for exp in experiences_data:
            assert exp.company is not None, "Experience should have a company"
            assert len(exp.company) > 0, "Company name should not be empty"

    def test_bio_formatting(self):
        """Test that bio is correctly formatted from profile data."""
        profile = create_francois_profile()
        (
            user_data,
            projects_data,
            experiences_data,
            educations_data,
            certifications_data,
            skills_data,
        ) = map_profile_to_database(profile)

        bio = user_data.bio

        # Should contain headline
        assert "Software Engineer at Komodo Platform" in bio

        # Should contain summary
        assert "WIP" in bio

        # Should contain location
        assert "Pretoria" in bio

        # Should contain industry
        assert "Technology" in bio

    def test_date_handling(self):
        """Test that dates are correctly handled."""
        profile = create_francois_profile()
        (
            user_data,
            projects_data,
            experiences_data,
            educations_data,
            certifications_data,
            skills_data,
        ) = map_profile_to_database(profile)

        # Get Komodo experience (most recent, should have no end_date -> is_current)
        komodo_exp = next(
            (
                e
                for e in experiences_data
                if "Komodo" in e.company and "Frontend Developer" in e.position
            ),
            None,
        )
        assert komodo_exp is not None, "Komodo experience not found"
        assert komodo_exp.is_current is True, "Komodo should be current position"
        assert komodo_exp.start_date is not None, "Komodo should have start date"


class TestIssueIdentification:
    """Tests to identify and document issues with the current importer."""

    def test_api_vs_scraper_issue(self):
        """Document the fundamental issue: API limitations vs scraping approach."""
        # This test documents the issue rather than testing functionality

        issues = {
            "issue_1": {
                "title": "LinkedIn API Access Limitations",
                "description": "The current implementation uses LinkedIn's official API (api.linkedin.com/v2), which has significant restrictions",
                "details": [
                    "The /me endpoint only works for the authenticated user",
                    "You cannot fetch arbitrary public profiles using OAuth client credentials",
                    "Endpoints like /positions, /educations, /skills with q=member are not public APIs",
                    "Most profile data endpoints require LinkedIn partner approval",
                ],
                "impact": "The importer cannot actually fetch profile data for arbitrary LinkedIn profiles",
            },
            "issue_2": {
                "title": "Authentication Flow Mismatch",
                "description": "Client credentials flow is used, but it doesn't grant access to profile data",
                "details": [
                    "Client credentials flow only works for specific partner APIs",
                    "Profile data access requires user authorization (3-legged OAuth)",
                    "Without user consent, you cannot access their profile data",
                ],
                "impact": "Authentication will fail or return empty/unauthorized responses",
            },
            "issue_3": {
                "title": "API Endpoints Don't Exist",
                "description": "Several endpoints used in linkedin_client.py don't exist in LinkedIn's public API",
                "details": [
                    "https://api.linkedin.com/v2/positions - Not a public endpoint",
                    "https://api.linkedin.com/v2/educations - Not a public endpoint",
                    "https://api.linkedin.com/v2/skills - Not a public endpoint",
                    "https://api.linkedin.com/v2/certifications - Not a public endpoint",
                ],
                "impact": "All API calls will return 404 or 403 errors",
            },
            "issue_4": {
                "title": "Alternative: Web Scraping Required",
                "description": "To fetch arbitrary LinkedIn profile data, web scraping is necessary",
                "details": [
                    "The linkedin_scraper library uses Selenium to scrape LinkedIn pages",
                    "Requires a logged-in LinkedIn session",
                    "Extracts data from HTML rather than API responses",
                    "This is how the alternative library works",
                ],
                "impact": "A complete rewrite using the scraping approach is needed",
            },
        }

        # This assertion always passes - it's here to make the test framework happy
        # The real value is in the documented issues
        assert len(issues) == 4

    def test_generate_report_data(self):
        """Generate data for the debugging report."""
        profile = create_francois_profile()
        (
            user_data,
            projects_data,
            experiences_data,
            educations_data,
            certifications_data,
            skills_data,
        ) = map_profile_to_database(profile)

        report = {
            "profile_summary": {
                "name": f"{profile.first_name} {profile.last_name}",
                "email": profile.email,
                "headline": profile.headline,
                "location": profile.location,
                "positions_count": len(profile.positions),
                "education_count": len(profile.education),
                "skills_count": len(profile.skills),
                "certifications_count": len(profile.certifications),
            },
            "database_mapping": {
                "user": {
                    "email": user_data.email,
                    "name": user_data.name,
                    "bio_length": len(user_data.bio),
                    "avatar_url": user_data.avatar_url,
                },
                "experiences_count": len(experiences_data),
                "educations_count": len(educations_data),
                "certifications_count": len(certifications_data),
                "skills_count": len(skills_data),
                "experiences": [
                    {
                        "company": e.company,
                        "position": e.position,
                        "has_description": bool(e.description),
                        "is_current": e.is_current,
                        "start_date": e.start_date.isoformat()
                        if e.start_date
                        else None,
                        "end_date": e.end_date.isoformat() if e.end_date else None,
                    }
                    for e in experiences_data
                ],
            },
        }

        # Print report data (visible when running pytest -v)
        print("\n" + "=" * 60)
        print("PROFILE IMPORT REPORT")
        print("=" * 60)
        print(json.dumps(report, indent=2, default=str))
        print("=" * 60)

        assert report is not None


def generate_database_inspection_data() -> dict:
    """Generate simulated database entries for inspection."""
    profile = create_francois_profile()
    (
        user_data,
        projects_data,
        experiences_data,
        educations_data,
        certifications_data,
        skills_data,
    ) = map_profile_to_database(profile)

    # Simulate UUID generation
    import uuid

    user_id = uuid.uuid4()

    # Simulate users table entry
    users_table = {
        "id": str(user_id),
        "email": user_data.email,
        "password_hash": "",  # Empty for LinkedIn imports
        "name": user_data.name,
        "bio": user_data.bio,
        "avatar_url": user_data.avatar_url,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }

    # Simulate projects table entries
    projects_table = []
    project_technologies_table = []

    for p in projects_data:
        project_id = uuid.uuid4()
        projects_table.append(
            {
                "id": str(project_id),
                "slug": p.slug,
                "title": p.title,
                "description": p.description,
                "long_description": p.long_description,
                "image_url": p.image_url,
                "live_url": p.live_url,
                "github_url": p.github_url,
                "featured": p.featured,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            }
        )

        # Add technology links
        for tech in p.technologies:
            project_technologies_table.append(
                {
                    "project_id": str(project_id),
                    "technology": tech,
                }
            )

    return {
        "users": [users_table],
        "projects": projects_table,
        "project_technologies": project_technologies_table,
    }


if __name__ == "__main__":
    """Run tests and generate inspection data when executed directly."""
    print("\n" + "=" * 80)
    print("LINKEDIN IMPORTER TEST - FRANCOIS VAN WYK PROFILE")
    print("=" * 80)

    # Create profile
    profile = create_francois_profile()
    print(f"\n✓ Created profile for {profile.first_name} {profile.last_name}")
    print(f"  Email: {profile.email}")
    print(f"  Headline: {profile.headline}")
    print(f"  Location: {profile.location}")
    print(f"  Positions: {len(profile.positions)}")
    print(f"  Education: {len(profile.education)}")
    print(f"  Skills: {len(profile.skills)}")
    print(f"  Certifications: {len(profile.certifications)}")

    # Map to database
    (
        user_data,
        projects_data,
        experiences_data,
        educations_data,
        certifications_data,
        skills_data,
    ) = map_profile_to_database(profile)
    print(f"\n✓ Mapped to database models")
    print(f"  User: {user_data.name} <{user_data.email}>")
    print(f"  Experiences: {len(experiences_data)}")
    print(f"  Educations: {len(educations_data)}")
    print(f"  Certifications: {len(certifications_data)}")
    print(f"  Skills: {len(skills_data)}")

    # Show projects
    print(f"\n{'=' * 80}")
    print("PROJECTS THAT WOULD BE CREATED")
    print("=" * 80)
    for i, p in enumerate(projects_data, 1):
        print(f"\n{i}. {p.title}")
        print(f"   Slug: {p.slug}")
        print(
            f"   Description: {p.description[:50]}..."
            if p.description
            else "   Description: N/A"
        )
        print(
            f"   Technologies: {', '.join(p.technologies) if p.technologies else 'None'}"
        )
        print(f"   Created: {p.created_at}")

    # Generate database data
    db_data = generate_database_inspection_data()
    print(f"\n{'=' * 80}")
    print("SIMULATED DATABASE ENTRIES")
    print("=" * 80)
    print(f"\nUsers table: {len(db_data['users'])} entries")
    print(f"Projects table: {len(db_data['projects'])} entries")
    print(f"Project technologies table: {len(db_data['project_technologies'])} entries")

    # Identify issues
    print(f"\n{'=' * 80}")
    print("IDENTIFIED ISSUES")
    print("=" * 80)
    print("""
1. LINKEDIN API ACCESS LIMITATIONS
   The current implementation uses LinkedIn's official API which requires:
   - Partner program approval for most endpoints
   - User authorization (3-legged OAuth) for profile access
   - Cannot fetch arbitrary public profiles with client credentials

2. NON-EXISTENT API ENDPOINTS
   The following endpoints used in linkedin_client.py don't exist:
   - /v2/positions
   - /v2/educations
   - /v2/skills
   - /v2/certifications
   These will return 404/403 errors.

3. AUTHENTICATION FLOW MISMATCH
   Client credentials flow doesn't grant access to profile data.
   Profile access requires user consent through browser-based OAuth flow.

4. SOLUTION: USE WEB SCRAPING
   The alternative linkedin_scraper library uses Selenium to scrape profiles.
   This requires:
   - Chrome browser + chromedriver
   - Logged-in LinkedIn session
   - HTML parsing instead of API calls
""")
