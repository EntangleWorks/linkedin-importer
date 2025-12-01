"""Data models for LinkedIn profile data."""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class Position:
    """LinkedIn work position."""

    company_name: str
    title: str
    description: Optional[str] = None
    responsibilities: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    location: Optional[str] = None
    employment_type: Optional[str] = None
    company_url: Optional[str] = None
    company_logo_url: Optional[str] = None


@dataclass
class Education:
    """LinkedIn education entry."""

    school: str
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    grade: Optional[str] = None
    activities: Optional[str] = None
    description: Optional[str] = None


@dataclass
class Skill:
    """LinkedIn skill."""

    name: str
    endorsement_count: Optional[int] = None


@dataclass
class Certification:
    """LinkedIn certification."""

    name: str
    authority: str
    license_number: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    url: Optional[str] = None


@dataclass
class Publication:
    """LinkedIn publication."""

    name: str
    publisher: Optional[str] = None
    publication_date: Optional[date] = None
    url: Optional[str] = None
    description: Optional[str] = None


@dataclass
class VolunteerExperience:
    """LinkedIn volunteer experience."""

    organization: str
    role: str
    cause: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


@dataclass
class Honor:
    """LinkedIn honor or award."""

    title: str
    issuer: Optional[str] = None
    issue_date: Optional[date] = None
    description: Optional[str] = None


@dataclass
class Language:
    """LinkedIn language proficiency."""

    name: str
    proficiency: Optional[str] = None


@dataclass
class LinkedInProfile:
    """Complete LinkedIn profile data."""

    profile_id: str
    first_name: str
    last_name: str
    email: str
    headline: Optional[str] = None
    summary: Optional[str] = None
    location: Optional[str] = None
    industry: Optional[str] = None
    profile_picture_url: Optional[str] = None
    positions: list[Position] = None
    education: list[Education] = None
    skills: list[Skill] = None
    certifications: list[Certification] = None
    publications: list[Publication] = None
    volunteer: list[VolunteerExperience] = None
    honors: list[Honor] = None
    languages: list[Language] = None

    def __post_init__(self):
        """Initialize empty lists for None values."""
        if self.positions is None:
            self.positions = []
        if self.education is None:
            self.education = []
        if self.skills is None:
            self.skills = []
        if self.certifications is None:
            self.certifications = []
        if self.publications is None:
            self.publications = []
        if self.volunteer is None:
            self.volunteer = []
        if self.honors is None:
            self.honors = []
        if self.languages is None:
            self.languages = []
