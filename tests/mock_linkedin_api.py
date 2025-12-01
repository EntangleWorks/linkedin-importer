"""Mock LinkedIn API server for integration testing.

This module provides a mock LinkedIn API server that can be used for
integration testing without requiring actual LinkedIn API credentials.
"""

import asyncio
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4


@dataclass
class MockAPIConfig:
    """Configuration for the mock API server."""

    # Rate limiting
    rate_limit_remaining: int = 100
    rate_limit_reset_seconds: int = 60

    # Error simulation
    simulate_rate_limit: bool = False
    simulate_quota_exhausted: bool = False
    simulate_auth_failure: bool = False
    simulate_network_error: bool = False
    simulate_server_error: bool = False

    # Latency simulation (in seconds)
    min_latency: float = 0.01
    max_latency: float = 0.1

    # Request tracking
    request_count: int = 0
    request_history: list = field(default_factory=list)


@dataclass
class MockProfile:
    """A mock LinkedIn profile for testing."""

    profile_id: str
    first_name: str
    last_name: str
    email: str
    headline: Optional[str] = None
    summary: Optional[str] = None
    location: Optional[str] = None
    industry: Optional[str] = None
    profile_picture_url: Optional[str] = None

    # Lists of profile data
    positions: list = field(default_factory=list)
    education: list = field(default_factory=list)
    skills: list = field(default_factory=list)
    certifications: list = field(default_factory=list)
    publications: list = field(default_factory=list)
    volunteer: list = field(default_factory=list)
    honors: list = field(default_factory=list)
    languages: list = field(default_factory=list)


class MockLinkedInAPIServer:
    """Mock LinkedIn API server for testing.

    This class simulates LinkedIn API responses for various endpoints,
    including support for rate limiting, error simulation, and
    realistic response data.
    """

    def __init__(self, config: Optional[MockAPIConfig] = None):
        """Initialize the mock server.

        Args:
            config: Optional configuration for the mock server
        """
        self.config = config or MockAPIConfig()
        self.profiles: dict[str, MockProfile] = {}
        self._authenticated = False
        self._access_token: Optional[str] = None
        self._rate_limit_reset_time: Optional[datetime] = None

        # Add some default profiles
        self._add_default_profiles()

    def _add_default_profiles(self) -> None:
        """Add default test profiles."""
        # Complete profile with all sections
        complete_profile = MockProfile(
            profile_id="johndoe",
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            headline="Senior Software Engineer | Python & Rust Expert",
            summary="Experienced software engineer with 10+ years of experience...",
            location="San Francisco, CA",
            industry="Technology",
            profile_picture_url="https://example.com/photos/johndoe.jpg",
            positions=[
                {
                    "company_name": "TechCorp Inc.",
                    "title": "Senior Software Engineer",
                    "description": "Leading backend development team...",
                    "responsibilities": "Architecting microservices, mentoring junior developers...",
                    "start_date": {"year": 2020, "month": 1},
                    "end_date": None,
                    "location": "San Francisco, CA",
                    "employment_type": "Full-time",
                    "company_url": "https://techcorp.example.com",
                    "company_logo_url": "https://example.com/logos/techcorp.png",
                },
                {
                    "company_name": "StartupXYZ",
                    "title": "Software Engineer",
                    "description": "Full-stack development using Python and React...",
                    "responsibilities": "Building web applications, implementing CI/CD...",
                    "start_date": {"year": 2017, "month": 6},
                    "end_date": {"year": 2019, "month": 12},
                    "location": "New York, NY",
                    "employment_type": "Full-time",
                    "company_url": "https://startupxyz.example.com",
                    "company_logo_url": None,
                },
            ],
            education=[
                {
                    "school": "MIT",
                    "degree": "Master of Science",
                    "field_of_study": "Computer Science",
                    "start_date": {"year": 2015},
                    "end_date": {"year": 2017},
                    "grade": "3.9 GPA",
                    "activities": "AI Research Lab, Robotics Club",
                    "description": "Focused on machine learning and distributed systems.",
                },
                {
                    "school": "UC Berkeley",
                    "degree": "Bachelor of Science",
                    "field_of_study": "Computer Science",
                    "start_date": {"year": 2011},
                    "end_date": {"year": 2015},
                    "grade": "3.8 GPA",
                    "activities": "ACM, Open Source Club",
                    "description": None,
                },
            ],
            skills=[
                {"name": "Python", "endorsement_count": 99},
                {"name": "Rust", "endorsement_count": 45},
                {"name": "PostgreSQL", "endorsement_count": 67},
                {"name": "Docker", "endorsement_count": 52},
                {"name": "Kubernetes", "endorsement_count": 38},
                {"name": "React", "endorsement_count": 41},
            ],
            certifications=[
                {
                    "name": "AWS Solutions Architect",
                    "authority": "Amazon Web Services",
                    "license_number": "AWS-SA-12345",
                    "start_date": {"year": 2021, "month": 3},
                    "end_date": {"year": 2024, "month": 3},
                    "url": "https://aws.amazon.com/certification/verify/12345",
                },
            ],
            publications=[
                {
                    "name": "Scaling Microservices in Production",
                    "publisher": "Tech Blog Inc.",
                    "publication_date": {"year": 2022, "month": 6},
                    "url": "https://techblog.example.com/scaling-microservices",
                    "description": "A comprehensive guide to scaling microservices...",
                },
            ],
            volunteer=[
                {
                    "organization": "Code.org",
                    "role": "Volunteer Instructor",
                    "cause": "Education",
                    "description": "Teaching programming to underrepresented youth...",
                    "start_date": {"year": 2019, "month": 1},
                    "end_date": None,
                },
            ],
            honors=[
                {
                    "title": "Employee of the Year",
                    "issuer": "TechCorp Inc.",
                    "issue_date": {"year": 2021, "month": 12},
                    "description": "Awarded for exceptional contributions to the platform team.",
                },
            ],
            languages=[
                {"name": "English", "proficiency": "Native"},
                {"name": "Spanish", "proficiency": "Professional"},
            ],
        )
        self.profiles["johndoe"] = complete_profile

        # Minimal profile with only required fields
        minimal_profile = MockProfile(
            profile_id="janedoe",
            first_name="Jane",
            last_name="Doe",
            email="jane.doe@example.com",
        )
        self.profiles["janedoe"] = minimal_profile

        # Profile for testing edge cases
        edge_case_profile = MockProfile(
            profile_id="edgecase",
            first_name="Edge",
            last_name="Case",
            email="edge.case@example.com",
            headline="Testing Edge Cases | Special Characters: <>&\"'",
            summary="Summary with\nnewlines\nand\ttabs",
            positions=[
                {
                    "company_name": "Company with Unicode: 日本語",
                    "title": "役割 (Role)",
                    "description": "Description with émojis 🚀 and spëcial çharacters",
                    "start_date": {"year": 2023, "month": 1},
                    "end_date": None,
                    "location": None,
                    "employment_type": None,
                },
            ],
        )
        self.profiles["edgecase"] = edge_case_profile

    def add_profile(self, profile: MockProfile) -> None:
        """Add a profile to the mock server.

        Args:
            profile: The profile to add
        """
        self.profiles[profile.profile_id] = profile

    async def _simulate_latency(self) -> None:
        """Simulate network latency."""
        latency = random.uniform(self.config.min_latency, self.config.max_latency)
        await asyncio.sleep(latency)

    def _track_request(self, endpoint: str, method: str = "GET") -> None:
        """Track a request for testing.

        Args:
            endpoint: The endpoint being called
            method: HTTP method
        """
        self.config.request_count += 1
        self.config.request_history.append(
            {
                "endpoint": endpoint,
                "method": method,
                "timestamp": datetime.now().isoformat(),
            }
        )

    def _check_rate_limit(self) -> tuple[bool, dict]:
        """Check if rate limit is exceeded.

        Returns:
            Tuple of (is_limited, headers)
        """
        if self.config.simulate_rate_limit:
            if self._rate_limit_reset_time is None:
                self._rate_limit_reset_time = datetime.now() + timedelta(
                    seconds=self.config.rate_limit_reset_seconds
                )

            reset_timestamp = int(self._rate_limit_reset_time.timestamp())
            return True, {
                "X-RateLimit-Limit": "100",
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset_timestamp),
                "Retry-After": str(self.config.rate_limit_reset_seconds),
            }

        remaining = max(0, self.config.rate_limit_remaining - self.config.request_count)
        reset_time = datetime.now() + timedelta(
            seconds=self.config.rate_limit_reset_seconds
        )

        return False, {
            "X-RateLimit-Limit": str(self.config.rate_limit_remaining),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(int(reset_time.timestamp())),
        }

    async def authenticate(self, api_key: str, api_secret: str) -> dict:
        """Simulate OAuth authentication.

        Args:
            api_key: LinkedIn API key
            api_secret: LinkedIn API secret

        Returns:
            Authentication response
        """
        await self._simulate_latency()
        self._track_request("/oauth/accessToken", "POST")

        if self.config.simulate_auth_failure:
            return {
                "status_code": 401,
                "error": "invalid_client",
                "error_description": "Invalid API credentials",
            }

        if self.config.simulate_network_error:
            raise ConnectionError("Network connection failed")

        self._access_token = f"mock_token_{uuid4().hex[:8]}"
        self._authenticated = True

        return {
            "status_code": 200,
            "access_token": self._access_token,
            "expires_in": 3600,
            "token_type": "Bearer",
        }

    async def get_profile_basic(self, profile_id: str) -> dict:
        """Get basic profile information.

        Args:
            profile_id: LinkedIn profile ID or URL

        Returns:
            Profile basic info response
        """
        await self._simulate_latency()
        self._track_request(f"/v2/me?profile_id={profile_id}")

        is_limited, headers = self._check_rate_limit()
        if is_limited:
            return {"status_code": 429, "headers": headers}

        if self.config.simulate_quota_exhausted:
            return {
                "status_code": 403,
                "error": "quota_exhausted",
                "error_description": "API quota has been exhausted",
                "headers": headers,
            }

        if self.config.simulate_server_error:
            return {"status_code": 500, "error": "Internal server error"}

        # Extract profile ID from URL if needed
        clean_id = profile_id.split("/")[-1] if "/" in profile_id else profile_id

        profile = self.profiles.get(clean_id)
        if not profile:
            return {"status_code": 404, "error": "Profile not found"}

        return {
            "status_code": 200,
            "headers": headers,
            "data": {
                "id": profile.profile_id,
                "firstName": {"localized": {"en_US": profile.first_name}},
                "lastName": {"localized": {"en_US": profile.last_name}},
                "emailAddress": profile.email,
                "headline": profile.headline,
                "summary": profile.summary,
                "location": {"name": profile.location} if profile.location else None,
                "industry": profile.industry,
                "profilePicture": {"displayImage": profile.profile_picture_url}
                if profile.profile_picture_url
                else None,
            },
        }

    async def get_profile_experience(self, profile_id: str) -> dict:
        """Get work experience.

        Args:
            profile_id: LinkedIn profile ID

        Returns:
            Experience data response
        """
        await self._simulate_latency()
        self._track_request(f"/v2/positions?profile_id={profile_id}")

        is_limited, headers = self._check_rate_limit()
        if is_limited:
            return {"status_code": 429, "headers": headers}

        clean_id = profile_id.split("/")[-1] if "/" in profile_id else profile_id
        profile = self.profiles.get(clean_id)

        if not profile:
            return {"status_code": 404, "error": "Profile not found"}

        return {
            "status_code": 200,
            "headers": headers,
            "data": {"elements": profile.positions},
        }

    async def get_profile_education(self, profile_id: str) -> dict:
        """Get education history.

        Args:
            profile_id: LinkedIn profile ID

        Returns:
            Education data response
        """
        await self._simulate_latency()
        self._track_request(f"/v2/educations?profile_id={profile_id}")

        is_limited, headers = self._check_rate_limit()
        if is_limited:
            return {"status_code": 429, "headers": headers}

        clean_id = profile_id.split("/")[-1] if "/" in profile_id else profile_id
        profile = self.profiles.get(clean_id)

        if not profile:
            return {"status_code": 404, "error": "Profile not found"}

        return {
            "status_code": 200,
            "headers": headers,
            "data": {"elements": profile.education},
        }

    async def get_profile_skills(self, profile_id: str) -> dict:
        """Get skills.

        Args:
            profile_id: LinkedIn profile ID

        Returns:
            Skills data response
        """
        await self._simulate_latency()
        self._track_request(f"/v2/skills?profile_id={profile_id}")

        is_limited, headers = self._check_rate_limit()
        if is_limited:
            return {"status_code": 429, "headers": headers}

        clean_id = profile_id.split("/")[-1] if "/" in profile_id else profile_id
        profile = self.profiles.get(clean_id)

        if not profile:
            return {"status_code": 404, "error": "Profile not found"}

        return {
            "status_code": 200,
            "headers": headers,
            "data": {"elements": profile.skills},
        }

    async def get_profile_certifications(self, profile_id: str) -> dict:
        """Get certifications.

        Args:
            profile_id: LinkedIn profile ID

        Returns:
            Certifications data response
        """
        await self._simulate_latency()
        self._track_request(f"/v2/certifications?profile_id={profile_id}")

        is_limited, headers = self._check_rate_limit()
        if is_limited:
            return {"status_code": 429, "headers": headers}

        clean_id = profile_id.split("/")[-1] if "/" in profile_id else profile_id
        profile = self.profiles.get(clean_id)

        if not profile:
            return {"status_code": 404, "error": "Profile not found"}

        return {
            "status_code": 200,
            "headers": headers,
            "data": {"elements": profile.certifications},
        }

    async def get_profile_publications(self, profile_id: str) -> dict:
        """Get publications.

        Args:
            profile_id: LinkedIn profile ID

        Returns:
            Publications data response
        """
        await self._simulate_latency()
        self._track_request(f"/v2/publications?profile_id={profile_id}")

        is_limited, headers = self._check_rate_limit()
        if is_limited:
            return {"status_code": 429, "headers": headers}

        clean_id = profile_id.split("/")[-1] if "/" in profile_id else profile_id
        profile = self.profiles.get(clean_id)

        if not profile:
            return {"status_code": 404, "error": "Profile not found"}

        return {
            "status_code": 200,
            "headers": headers,
            "data": {"elements": profile.publications},
        }

    async def get_profile_volunteer(self, profile_id: str) -> dict:
        """Get volunteer experience.

        Args:
            profile_id: LinkedIn profile ID

        Returns:
            Volunteer data response
        """
        await self._simulate_latency()
        self._track_request(f"/v2/volunteerExperiences?profile_id={profile_id}")

        is_limited, headers = self._check_rate_limit()
        if is_limited:
            return {"status_code": 429, "headers": headers}

        clean_id = profile_id.split("/")[-1] if "/" in profile_id else profile_id
        profile = self.profiles.get(clean_id)

        if not profile:
            return {"status_code": 404, "error": "Profile not found"}

        return {
            "status_code": 200,
            "headers": headers,
            "data": {"elements": profile.volunteer},
        }

    async def get_profile_honors(self, profile_id: str) -> dict:
        """Get honors and awards.

        Args:
            profile_id: LinkedIn profile ID

        Returns:
            Honors data response
        """
        await self._simulate_latency()
        self._track_request(f"/v2/honors?profile_id={profile_id}")

        is_limited, headers = self._check_rate_limit()
        if is_limited:
            return {"status_code": 429, "headers": headers}

        clean_id = profile_id.split("/")[-1] if "/" in profile_id else profile_id
        profile = self.profiles.get(clean_id)

        if not profile:
            return {"status_code": 404, "error": "Profile not found"}

        return {
            "status_code": 200,
            "headers": headers,
            "data": {"elements": profile.honors},
        }

    async def get_profile_languages(self, profile_id: str) -> dict:
        """Get language proficiencies.

        Args:
            profile_id: LinkedIn profile ID

        Returns:
            Languages data response
        """
        await self._simulate_latency()
        self._track_request(f"/v2/languages?profile_id={profile_id}")

        is_limited, headers = self._check_rate_limit()
        if is_limited:
            return {"status_code": 429, "headers": headers}

        clean_id = profile_id.split("/")[-1] if "/" in profile_id else profile_id
        profile = self.profiles.get(clean_id)

        if not profile:
            return {"status_code": 404, "error": "Profile not found"}

        return {
            "status_code": 200,
            "headers": headers,
            "data": {"elements": profile.languages},
        }

    def reset(self) -> None:
        """Reset the server state for a new test."""
        self.config.request_count = 0
        self.config.request_history = []
        self.config.simulate_rate_limit = False
        self.config.simulate_quota_exhausted = False
        self.config.simulate_auth_failure = False
        self.config.simulate_network_error = False
        self.config.simulate_server_error = False
        self._authenticated = False
        self._access_token = None
        self._rate_limit_reset_time = None


def create_realistic_profile(
    profile_id: str,
    num_positions: int = 3,
    num_skills: int = 10,
    num_education: int = 2,
) -> MockProfile:
    """Create a realistic mock profile with generated data.

    Args:
        profile_id: Unique profile ID
        num_positions: Number of work positions to generate
        num_skills: Number of skills to generate
        num_education: Number of education entries to generate

    Returns:
        A MockProfile with generated data
    """
    companies = [
        "Google",
        "Meta",
        "Amazon",
        "Apple",
        "Microsoft",
        "Netflix",
        "Spotify",
        "Stripe",
        "Airbnb",
        "Uber",
    ]

    titles = [
        "Software Engineer",
        "Senior Software Engineer",
        "Staff Engineer",
        "Principal Engineer",
        "Engineering Manager",
        "Tech Lead",
    ]

    skills_list = [
        "Python",
        "JavaScript",
        "TypeScript",
        "Rust",
        "Go",
        "PostgreSQL",
        "MongoDB",
        "Redis",
        "Docker",
        "Kubernetes",
        "AWS",
        "GCP",
        "Azure",
        "React",
        "Node.js",
    ]

    schools = [
        "MIT",
        "Stanford",
        "UC Berkeley",
        "CMU",
        "Harvard",
        "Yale",
        "Princeton",
        "Caltech",
    ]

    # Generate positions
    positions = []
    current_year = 2024
    for i in range(num_positions):
        start_year = current_year - (i * 2) - 1
        end_year = current_year - (i * 2) if i > 0 else None

        positions.append(
            {
                "company_name": random.choice(companies),
                "title": random.choice(titles),
                "description": f"Working on exciting projects at this company...",
                "start_date": {"year": start_year, "month": random.randint(1, 12)},
                "end_date": {"year": end_year, "month": random.randint(1, 12)}
                if end_year
                else None,
                "location": "San Francisco, CA",
                "employment_type": "Full-time",
            }
        )

    # Generate skills
    selected_skills = random.sample(skills_list, min(num_skills, len(skills_list)))
    skills = [
        {"name": skill, "endorsement_count": random.randint(5, 99)}
        for skill in selected_skills
    ]

    # Generate education
    education = []
    for i in range(num_education):
        grad_year = 2015 - (i * 4)
        education.append(
            {
                "school": random.choice(schools),
                "degree": "Bachelor of Science" if i > 0 else "Master of Science",
                "field_of_study": "Computer Science",
                "start_date": {"year": grad_year - 4},
                "end_date": {"year": grad_year},
            }
        )

    return MockProfile(
        profile_id=profile_id,
        first_name="Test",
        last_name=f"User{profile_id.upper()}",
        email=f"{profile_id}@example.com",
        headline=f"{titles[0]} with expertise in {', '.join(selected_skills[:3])}",
        summary="Experienced engineer passionate about building great software.",
        location="San Francisco, CA",
        industry="Technology",
        positions=positions,
        education=education,
        skills=skills,
    )
