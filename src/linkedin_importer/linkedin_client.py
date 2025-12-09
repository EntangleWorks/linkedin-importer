"""LinkedIn API client with OAuth 2.0 authentication and rate limiting.

.. deprecated::
    This module is deprecated. The LinkedIn API no longer supports fetching
    arbitrary public profiles. Use :class:`scraper_client.LinkedInScraperClient`
    instead, which uses browser automation to scrape profile data.

    Migration guide: See docs/MIGRATION.md for detailed instructions.
"""

import asyncio
import warnings
from datetime import date, datetime
from typing import Any, Optional
from urllib.parse import urlparse

import httpx

from .config import LinkedInConfig
from .errors import APIError, AuthError
from .logging_config import get_logger
from .models import (
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

logger = get_logger(__name__)


class LinkedInClient:
    """Client for interacting with LinkedIn API.

    .. deprecated::
        This class is deprecated. The LinkedIn API no longer supports fetching
        arbitrary public profiles. Use :class:`scraper_client.LinkedInScraperClient`
        instead.

        To migrate:
        1. Obtain your LinkedIn li_at cookie (see docs/MIGRATION.md)
        2. Use LinkedInScraperClient with cookie authentication
        3. The scraper provides the same LinkedInProfile output format
    """

    def __init__(
        self,
        config: LinkedInConfig,
        request_delay: float = 1.0,
        max_retries: int = 3,
    ):
        """Initialize LinkedIn API client.

        Args:
            config: LinkedIn API configuration
            request_delay: Delay between requests in seconds (default: 1.0)
            max_retries: Maximum number of retry attempts (default: 3)

        .. deprecated::
            Use LinkedInScraperClient instead. See docs/MIGRATION.md.
        """
        warnings.warn(
            "LinkedInClient is deprecated. The LinkedIn API no longer supports "
            "fetching public profiles. Use LinkedInScraperClient with cookie "
            "authentication instead. See docs/MIGRATION.md for migration instructions.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.config = config
        self.request_delay = request_delay
        self.max_retries = max_retries
        self.access_token: Optional[str] = config.access_token
        self.base_url = "https://api.linkedin.com/v2"
        self._client: Optional[httpx.AsyncClient] = None
        self._last_request_time: Optional[float] = None
        self._fetched_data: dict[str, Any] = {}  # Cache for deduplication

    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()

    async def authenticate(self) -> str:
        """Authenticate with LinkedIn API and return access token.

        Returns:
            Access token string

        Raises:
            AuthError: If authentication fails
        """
        if self.access_token:
            logger.info("Using provided access token")
            return self.access_token

        logger.info("Authenticating with LinkedIn API")

        # OAuth 2.0 client credentials flow
        auth_url = "https://www.linkedin.com/oauth/v2/accessToken"
        data = {
            "grant_type": "client_credentials",
            "client_id": self.config.api_key,
            "client_secret": self.config.api_secret,
        }

        try:
            response = await self._make_request(
                "POST",
                auth_url,
                data=data,
                skip_auth=True,
            )
            self.access_token = response.get("access_token")
            if not self.access_token:
                raise AuthError(
                    "Authentication failed: No access token in response",
                    details={"response": response},
                )
            logger.info("Successfully authenticated with LinkedIn API")
            return self.access_token
        except httpx.HTTPStatusError as e:
            raise AuthError(
                f"Authentication failed with status {e.response.status_code}",
                details={
                    "status_code": e.response.status_code,
                    "response": e.response.text,
                },
            ) from e
        except Exception as e:
            raise AuthError(
                f"Authentication failed: {str(e)}",
                details={"error": str(e)},
            ) from e

    async def get_profile(self, profile_url: str) -> LinkedInProfile:
        """Fetch complete LinkedIn profile data.

        Args:
            profile_url: LinkedIn profile URL or username

        Returns:
            Complete LinkedIn profile

        Raises:
            APIError: If profile fetch fails
        """
        logger.info(f"Fetching profile: {profile_url}")

        # Extract profile ID from URL
        profile_id = self._extract_profile_id(profile_url)

        # Ensure authenticated
        if not self.access_token:
            await self.authenticate()

        # Fetch all profile sections
        basic_info = await self.get_profile_basic(profile_id)
        positions = await self.get_profile_experience(profile_id)
        education = await self.get_profile_education(profile_id)
        skills = await self.get_profile_skills(profile_id)

        # Optional sections
        certifications = await self._get_profile_certifications(profile_id)
        publications = await self._get_profile_publications(profile_id)
        volunteer = await self._get_profile_volunteer(profile_id)
        honors = await self._get_profile_honors(profile_id)
        languages = await self._get_profile_languages(profile_id)

        profile = LinkedInProfile(
            profile_id=profile_id,
            first_name=basic_info.get("firstName", ""),
            last_name=basic_info.get("lastName", ""),
            email=basic_info.get("email", ""),
            headline=basic_info.get("headline"),
            summary=basic_info.get("summary"),
            location=basic_info.get("location"),
            industry=basic_info.get("industry"),
            profile_picture_url=basic_info.get("profilePicture"),
            positions=positions,
            education=education,
            skills=skills,
            certifications=certifications,
            publications=publications,
            volunteer=volunteer,
            honors=honors,
            languages=languages,
        )

        logger.info(f"Successfully fetched profile: {profile_id}")
        return profile

    async def get_profile_basic(self, profile_id: str) -> dict[str, Any]:
        """Fetch basic profile information.

        Args:
            profile_id: LinkedIn profile ID

        Returns:
            Dictionary with basic profile data
        """
        cache_key = f"basic_{profile_id}"
        if cache_key in self._fetched_data:
            logger.debug(f"Using cached data for {cache_key}")
            return self._fetched_data[cache_key]

        logger.debug(f"Fetching basic info for profile: {profile_id}")
        url = f"{self.base_url}/me"
        params = {
            "projection": "(id,firstName,lastName,headline,summary,location,industry,profilePicture,emailAddress)"
        }

        response = await self._make_request("GET", url, params=params)
        self._fetched_data[cache_key] = response
        return response

    async def get_profile_experience(self, profile_id: str) -> list[Position]:
        """Fetch work experience.

        Args:
            profile_id: LinkedIn profile ID

        Returns:
            List of Position objects
        """
        cache_key = f"experience_{profile_id}"
        if cache_key in self._fetched_data:
            logger.debug(f"Using cached data for {cache_key}")
            return self._fetched_data[cache_key]

        logger.debug(f"Fetching experience for profile: {profile_id}")
        url = f"{self.base_url}/positions"
        params = {"q": "member", "member": profile_id}

        response = await self._make_request("GET", url, params=params)
        positions = []

        for item in response.get("elements", []):
            position = Position(
                company_name=item.get("companyName", ""),
                title=item.get("title", ""),
                description=item.get("description"),
                responsibilities=item.get("responsibilities"),
                start_date=self._parse_date(item.get("startDate")),
                end_date=self._parse_date(item.get("endDate")),
                location=item.get("location"),
                employment_type=item.get("employmentType"),
                company_url=item.get("companyUrl"),
                company_logo_url=item.get("companyLogoUrl"),
            )
            positions.append(position)

        self._fetched_data[cache_key] = positions
        return positions

    async def get_profile_education(self, profile_id: str) -> list[Education]:
        """Fetch education history.

        Args:
            profile_id: LinkedIn profile ID

        Returns:
            List of Education objects
        """
        cache_key = f"education_{profile_id}"
        if cache_key in self._fetched_data:
            logger.debug(f"Using cached data for {cache_key}")
            return self._fetched_data[cache_key]

        logger.debug(f"Fetching education for profile: {profile_id}")
        url = f"{self.base_url}/educations"
        params = {"q": "member", "member": profile_id}

        response = await self._make_request("GET", url, params=params)
        education_list = []

        for item in response.get("elements", []):
            education = Education(
                school=item.get("schoolName", ""),
                degree=item.get("degreeName"),
                field_of_study=item.get("fieldOfStudy"),
                start_date=self._parse_date(item.get("startDate")),
                end_date=self._parse_date(item.get("endDate")),
                grade=item.get("grade"),
                activities=item.get("activities"),
                description=item.get("description"),
            )
            education_list.append(education)

        self._fetched_data[cache_key] = education_list
        return education_list

    async def get_profile_skills(self, profile_id: str) -> list[Skill]:
        """Fetch skills list.

        Args:
            profile_id: LinkedIn profile ID

        Returns:
            List of Skill objects
        """
        cache_key = f"skills_{profile_id}"
        if cache_key in self._fetched_data:
            logger.debug(f"Using cached data for {cache_key}")
            return self._fetched_data[cache_key]

        logger.debug(f"Fetching skills for profile: {profile_id}")
        url = f"{self.base_url}/skills"
        params = {"q": "member", "member": profile_id}

        response = await self._make_request("GET", url, params=params)
        skills = []

        for item in response.get("elements", []):
            skill = Skill(
                name=item.get("name", ""),
                endorsement_count=item.get("endorsementCount"),
            )
            skills.append(skill)

        self._fetched_data[cache_key] = skills
        return skills

    async def _get_profile_certifications(self, profile_id: str) -> list[Certification]:
        """Fetch certifications."""
        cache_key = f"certifications_{profile_id}"
        if cache_key in self._fetched_data:
            return self._fetched_data[cache_key]

        try:
            url = f"{self.base_url}/certifications"
            params = {"q": "member", "member": profile_id}
            response = await self._make_request("GET", url, params=params)

            certifications = []
            for item in response.get("elements", []):
                cert = Certification(
                    name=item.get("name", ""),
                    authority=item.get("authority", ""),
                    license_number=item.get("licenseNumber"),
                    start_date=self._parse_date(item.get("startDate")),
                    end_date=self._parse_date(item.get("endDate")),
                    url=item.get("url"),
                )
                certifications.append(cert)

            self._fetched_data[cache_key] = certifications
            return certifications
        except APIError:
            logger.warning("Failed to fetch certifications, continuing without them")
            return []

    async def _get_profile_publications(self, profile_id: str) -> list[Publication]:
        """Fetch publications."""
        cache_key = f"publications_{profile_id}"
        if cache_key in self._fetched_data:
            return self._fetched_data[cache_key]

        try:
            url = f"{self.base_url}/publications"
            params = {"q": "member", "member": profile_id}
            response = await self._make_request("GET", url, params=params)

            publications = []
            for item in response.get("elements", []):
                pub = Publication(
                    name=item.get("name", ""),
                    publisher=item.get("publisher"),
                    publication_date=self._parse_date(item.get("date")),
                    url=item.get("url"),
                    description=item.get("description"),
                )
                publications.append(pub)

            self._fetched_data[cache_key] = publications
            return publications
        except APIError:
            logger.warning("Failed to fetch publications, continuing without them")
            return []

    async def _get_profile_volunteer(
        self, profile_id: str
    ) -> list[VolunteerExperience]:
        """Fetch volunteer experience."""
        cache_key = f"volunteer_{profile_id}"
        if cache_key in self._fetched_data:
            return self._fetched_data[cache_key]

        try:
            url = f"{self.base_url}/volunteer"
            params = {"q": "member", "member": profile_id}
            response = await self._make_request("GET", url, params=params)

            volunteer_list = []
            for item in response.get("elements", []):
                vol = VolunteerExperience(
                    organization=item.get("organization", ""),
                    role=item.get("role", ""),
                    cause=item.get("cause"),
                    description=item.get("description"),
                    start_date=self._parse_date(item.get("startDate")),
                    end_date=self._parse_date(item.get("endDate")),
                )
                volunteer_list.append(vol)

            self._fetched_data[cache_key] = volunteer_list
            return volunteer_list
        except APIError:
            logger.warning(
                "Failed to fetch volunteer experience, continuing without it"
            )
            return []

    async def _get_profile_honors(self, profile_id: str) -> list[Honor]:
        """Fetch honors and awards."""
        cache_key = f"honors_{profile_id}"
        if cache_key in self._fetched_data:
            return self._fetched_data[cache_key]

        try:
            url = f"{self.base_url}/honors"
            params = {"q": "member", "member": profile_id}
            response = await self._make_request("GET", url, params=params)

            honors = []
            for item in response.get("elements", []):
                honor = Honor(
                    title=item.get("title", ""),
                    issuer=item.get("issuer"),
                    issue_date=self._parse_date(item.get("issueDate")),
                    description=item.get("description"),
                )
                honors.append(honor)

            self._fetched_data[cache_key] = honors
            return honors
        except APIError:
            logger.warning("Failed to fetch honors, continuing without them")
            return []

    async def _get_profile_languages(self, profile_id: str) -> list[Language]:
        """Fetch languages."""
        cache_key = f"languages_{profile_id}"
        if cache_key in self._fetched_data:
            return self._fetched_data[cache_key]

        try:
            url = f"{self.base_url}/languages"
            params = {"q": "member", "member": profile_id}
            response = await self._make_request("GET", url, params=params)

            languages = []
            for item in response.get("elements", []):
                lang = Language(
                    name=item.get("name", ""),
                    proficiency=item.get("proficiency"),
                )
                languages.append(lang)

            self._fetched_data[cache_key] = languages
            return languages
        except APIError:
            logger.warning("Failed to fetch languages, continuing without them")
            return []

    async def _make_request(
        self,
        method: str,
        url: str,
        params: Optional[dict[str, Any]] = None,
        data: Optional[dict[str, Any]] = None,
        skip_auth: bool = False,
        retry_count: int = 0,
    ) -> dict[str, Any]:
        """Make HTTP request with rate limiting and retry logic.

        Args:
            method: HTTP method
            url: Request URL
            params: Query parameters
            data: Request body data
            skip_auth: Skip authentication header
            retry_count: Current retry attempt

        Returns:
            Response JSON data

        Raises:
            APIError: If request fails after retries
        """
        if not self._client:
            raise APIError("Client not initialized. Use async context manager.")

        # Throttle requests
        await self._throttle_request()

        # Prepare headers
        headers = {}
        if not skip_auth and self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"

        logger.debug(f"{method} {url}")

        try:
            response = await self._client.request(
                method=method,
                url=url,
                params=params,
                data=data,
                headers=headers,
            )

            # Handle rate limiting
            if response.status_code == 429:
                return await self._handle_rate_limit(
                    response, method, url, params, data, skip_auth, retry_count
                )

            # Handle quota exhaustion
            if response.status_code == 403:
                error_data = response.json() if response.text else {}
                if "quota" in str(error_data).lower():
                    raise APIError(
                        "API quota exhausted. Please try again later.",
                        details={
                            "status_code": 403,
                            "response": error_data,
                        },
                    )

            # Handle not found
            if response.status_code == 404:
                raise APIError(
                    "Profile not found",
                    details={
                        "status_code": 404,
                        "url": url,
                    },
                )

            # Raise for other errors
            response.raise_for_status()

            # Log response
            logger.debug(f"Response: {response.status_code}")

            return response.json() if response.text else {}

        except httpx.HTTPStatusError as e:
            # Retry on server errors
            if e.response.status_code >= 500 and retry_count < self.max_retries:
                return await self._retry_with_backoff(
                    retry_count, method, url, params, data, skip_auth
                )

            raise APIError(
                f"HTTP error {e.response.status_code}",
                details={
                    "status_code": e.response.status_code,
                    "response": e.response.text,
                    "url": url,
                },
            ) from e

        except httpx.RequestError as e:
            # Retry on network errors
            if retry_count < self.max_retries:
                return await self._retry_with_backoff(
                    retry_count, method, url, params, data, skip_auth
                )

            raise APIError(
                f"Network error: {str(e)}",
                details={
                    "error": str(e),
                    "url": url,
                },
            ) from e

    async def _handle_rate_limit(
        self,
        response: httpx.Response,
        method: str,
        url: str,
        params: Optional[dict[str, Any]],
        data: Optional[dict[str, Any]],
        skip_auth: bool,
        retry_count: int,
    ) -> dict[str, Any]:
        """Handle rate limit response.

        Args:
            response: Rate limit response
            method: HTTP method
            url: Request URL
            params: Query parameters
            data: Request body
            skip_auth: Skip auth flag
            retry_count: Current retry count

        Returns:
            Response from retry

        Raises:
            APIError: If max retries exceeded
        """
        if retry_count >= self.max_retries:
            raise APIError(
                "Rate limit exceeded and max retries reached",
                details={
                    "status_code": 429,
                    "retry_count": retry_count,
                },
            )

        # Get retry-after header
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                wait_time = int(retry_after)
            except ValueError:
                # Parse as HTTP date
                wait_time = 60  # Default to 60 seconds
        else:
            # Use X-RateLimit-Reset if available
            rate_limit_reset = response.headers.get("X-RateLimit-Reset")
            if rate_limit_reset:
                try:
                    reset_time = int(rate_limit_reset)
                    wait_time = max(0, reset_time - int(datetime.now().timestamp()))
                except ValueError:
                    wait_time = 60
            else:
                wait_time = 60

        logger.warning(f"Rate limited. Waiting {wait_time} seconds before retry.")
        await asyncio.sleep(wait_time)

        return await self._make_request(
            method, url, params, data, skip_auth, retry_count + 1
        )

    async def _retry_with_backoff(
        self,
        retry_count: int,
        method: str,
        url: str,
        params: Optional[dict[str, Any]],
        data: Optional[dict[str, Any]],
        skip_auth: bool,
    ) -> dict[str, Any]:
        """Retry request with exponential backoff.

        Args:
            retry_count: Current retry count
            method: HTTP method
            url: Request URL
            params: Query parameters
            data: Request body
            skip_auth: Skip auth flag

        Returns:
            Response from retry
        """
        wait_time = 2**retry_count  # 1s, 2s, 4s
        logger.warning(
            f"Request failed. Retrying in {wait_time}s (attempt {retry_count + 1}/{self.max_retries})"
        )
        await asyncio.sleep(wait_time)

        return await self._make_request(
            method, url, params, data, skip_auth, retry_count + 1
        )

    async def _throttle_request(self):
        """Throttle requests to respect rate limits."""
        if self._last_request_time is not None:
            elapsed = asyncio.get_event_loop().time() - self._last_request_time
            if elapsed < self.request_delay:
                wait_time = self.request_delay - elapsed
                logger.debug(f"Throttling request: waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)

        self._last_request_time = asyncio.get_event_loop().time()

    def _extract_profile_id(self, profile_url: str) -> str:
        """Extract profile ID from LinkedIn URL.

        Args:
            profile_url: LinkedIn profile URL or username

        Returns:
            Profile ID
        """
        # If it's already just an ID, return it
        if "/" not in profile_url and "." not in profile_url:
            return profile_url

        # Parse URL
        parsed = urlparse(profile_url)
        path_parts = parsed.path.strip("/").split("/")

        # Extract from /in/username format
        if "in" in path_parts:
            idx = path_parts.index("in")
            if idx + 1 < len(path_parts):
                return path_parts[idx + 1]

        # Return last part of path
        if path_parts:
            return path_parts[-1]

        return profile_url

    def _parse_date(self, date_dict: Optional[dict[str, int]]) -> Optional[date]:
        """Parse LinkedIn date format to Python date.

        Args:
            date_dict: Dictionary with year, month, day keys

        Returns:
            Python date object or None
        """
        if not date_dict:
            return None

        try:
            year = date_dict.get("year")
            month = date_dict.get("month", 1)
            day = date_dict.get("day", 1)

            if year:
                return date(year, month, day)
        except (ValueError, TypeError):
            logger.warning(f"Failed to parse date: {date_dict}")

        return None
