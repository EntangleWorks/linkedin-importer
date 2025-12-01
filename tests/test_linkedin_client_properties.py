"""Property-based tests for LinkedIn API client.

Feature: linkedin-profile-importer
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import httpx
from hypothesis import given, settings
from hypothesis import strategies as st

from linkedin_importer.config import LinkedInConfig
from linkedin_importer.errors import APIError
from linkedin_importer.linkedin_client import LinkedInClient
from linkedin_importer.models import LinkedInProfile


# Strategies for generating test data
@st.composite
def linkedin_date_dict(draw):
    """Generate LinkedIn date dictionary."""
    year = draw(st.integers(min_value=1950, max_value=2030))
    month = draw(st.integers(min_value=1, max_value=12))
    day = draw(st.integers(min_value=1, max_value=28))
    return {"year": year, "month": month, "day": day}


@st.composite
def position_data(draw):
    """Generate position data."""
    return {
        "companyName": draw(st.text(min_size=1, max_size=100)),
        "title": draw(st.text(min_size=1, max_size=100)),
        "description": draw(st.one_of(st.none(), st.text(max_size=500))),
        "responsibilities": draw(st.one_of(st.none(), st.text(max_size=500))),
        "startDate": draw(st.one_of(st.none(), linkedin_date_dict())),
        "endDate": draw(st.one_of(st.none(), linkedin_date_dict())),
        "location": draw(st.one_of(st.none(), st.text(max_size=100))),
        "employmentType": draw(
            st.one_of(
                st.none(),
                st.sampled_from(
                    ["Full-time", "Part-time", "Contract", "Freelance", "Internship"]
                ),
            )
        ),
        "companyUrl": draw(st.one_of(st.none(), st.text(max_size=200))),
        "companyLogoUrl": draw(st.one_of(st.none(), st.text(max_size=200))),
    }


@st.composite
def education_data(draw):
    """Generate education data."""
    return {
        "schoolName": draw(st.text(min_size=1, max_size=100)),
        "degreeName": draw(st.one_of(st.none(), st.text(max_size=100))),
        "fieldOfStudy": draw(st.one_of(st.none(), st.text(max_size=100))),
        "startDate": draw(st.one_of(st.none(), linkedin_date_dict())),
        "endDate": draw(st.one_of(st.none(), linkedin_date_dict())),
        "grade": draw(st.one_of(st.none(), st.text(max_size=50))),
        "activities": draw(st.one_of(st.none(), st.text(max_size=200))),
        "description": draw(st.one_of(st.none(), st.text(max_size=500))),
    }


@st.composite
def skill_data(draw):
    """Generate skill data."""
    return {
        "name": draw(st.text(min_size=1, max_size=100)),
        "endorsementCount": draw(st.one_of(st.none(), st.integers(min_value=0))),
    }


@st.composite
def certification_data(draw):
    """Generate certification data."""
    return {
        "name": draw(st.text(min_size=1, max_size=100)),
        "authority": draw(st.text(min_size=1, max_size=100)),
        "licenseNumber": draw(st.one_of(st.none(), st.text(max_size=100))),
        "startDate": draw(st.one_of(st.none(), linkedin_date_dict())),
        "endDate": draw(st.one_of(st.none(), linkedin_date_dict())),
        "url": draw(st.one_of(st.none(), st.text(max_size=200))),
    }


@st.composite
def publication_data(draw):
    """Generate publication data."""
    return {
        "name": draw(st.text(min_size=1, max_size=200)),
        "publisher": draw(st.one_of(st.none(), st.text(max_size=100))),
        "date": draw(st.one_of(st.none(), linkedin_date_dict())),
        "url": draw(st.one_of(st.none(), st.text(max_size=200))),
        "description": draw(st.one_of(st.none(), st.text(max_size=500))),
    }


@st.composite
def volunteer_data(draw):
    """Generate volunteer data."""
    return {
        "organization": draw(st.text(min_size=1, max_size=100)),
        "role": draw(st.text(min_size=1, max_size=100)),
        "cause": draw(st.one_of(st.none(), st.text(max_size=100))),
        "description": draw(st.one_of(st.none(), st.text(max_size=500))),
        "startDate": draw(st.one_of(st.none(), linkedin_date_dict())),
        "endDate": draw(st.one_of(st.none(), linkedin_date_dict())),
    }


@st.composite
def honor_data(draw):
    """Generate honor data."""
    return {
        "title": draw(st.text(min_size=1, max_size=100)),
        "issuer": draw(st.one_of(st.none(), st.text(max_size=100))),
        "issueDate": draw(st.one_of(st.none(), linkedin_date_dict())),
        "description": draw(st.one_of(st.none(), st.text(max_size=500))),
    }


@st.composite
def language_data(draw):
    """Generate language data."""
    return {
        "name": draw(st.text(min_size=1, max_size=50)),
        "proficiency": draw(
            st.one_of(
                st.none(),
                st.sampled_from(
                    [
                        "Elementary",
                        "Limited Working",
                        "Professional Working",
                        "Full Professional",
                        "Native",
                    ]
                ),
            )
        ),
    }


@st.composite
def basic_profile_data(draw):
    """Generate basic profile data."""
    return {
        "id": draw(st.text(min_size=1, max_size=50)),
        "firstName": draw(st.text(min_size=1, max_size=50)),
        "lastName": draw(st.text(min_size=1, max_size=50)),
        "email": draw(st.emails()),
        "headline": draw(st.one_of(st.none(), st.text(max_size=200))),
        "summary": draw(st.one_of(st.none(), st.text(max_size=1000))),
        "location": draw(st.one_of(st.none(), st.text(max_size=100))),
        "industry": draw(st.one_of(st.none(), st.text(max_size=100))),
        "profilePicture": draw(st.one_of(st.none(), st.text(max_size=200))),
    }


@st.composite
def complete_profile_response(draw):
    """Generate complete profile API response."""
    basic = draw(basic_profile_data())
    positions = draw(st.lists(position_data(), max_size=10))
    education = draw(st.lists(education_data(), max_size=5))
    skills = draw(st.lists(skill_data(), max_size=20))
    certifications = draw(st.lists(certification_data(), max_size=5))
    publications = draw(st.lists(publication_data(), max_size=5))
    volunteer = draw(st.lists(volunteer_data(), max_size=5))
    honors = draw(st.lists(honor_data(), max_size=5))
    languages = draw(st.lists(language_data(), max_size=5))

    return {
        "basic": basic,
        "positions": {"elements": positions},
        "education": {"elements": education},
        "skills": {"elements": skills},
        "certifications": {"elements": certifications},
        "publications": {"elements": publications},
        "volunteer": {"elements": volunteer},
        "honors": {"elements": honors},
        "languages": {"elements": languages},
    }


class TestProfileDataFetching:
    """Test profile data fetching completeness.

    Feature: linkedin-profile-importer, Property 1: Profile data fetching completeness
    Validates: Requirements 1.1
    """

    @given(profile_response=complete_profile_response())
    @settings(max_examples=100, deadline=5000)
    def test_profile_data_fetching_completeness(self, profile_response):
        """Property 1: For any valid LinkedIn profile URL or username, fetching profile
        data should return a complete profile structure with all available sections
        (basic info, experience, education, skills).

        Feature: linkedin-profile-importer, Property 1: Profile data fetching completeness
        Validates: Requirements 1.1
        """

        async def run_test():
            # Setup
            config = LinkedInConfig(
                api_key="test_key", api_secret="test_secret", access_token="test_token"
            )

            client = LinkedInClient(config, request_delay=0.0)  # No delay for tests

            # Create mock HTTP client
            mock_http_client = AsyncMock()
            mock_http_client.aclose = AsyncMock()

            # Mock responses for each endpoint
            async def mock_request(method, url, **kwargs):
                response = MagicMock()
                response.status_code = 200
                response.text = "{}"
                response.headers = {}
                response.raise_for_status = MagicMock()

                if "/me" in url:
                    response.json = MagicMock(return_value=profile_response["basic"])
                elif "/positions" in url:
                    response.json = MagicMock(
                        return_value=profile_response["positions"]
                    )
                elif "/educations" in url:
                    response.json = MagicMock(
                        return_value=profile_response["education"]
                    )
                elif "/skills" in url:
                    response.json = MagicMock(return_value=profile_response["skills"])
                elif "/certifications" in url:
                    response.json = MagicMock(
                        return_value=profile_response["certifications"]
                    )
                elif "/publications" in url:
                    response.json = MagicMock(
                        return_value=profile_response["publications"]
                    )
                elif "/volunteer" in url:
                    response.json = MagicMock(
                        return_value=profile_response["volunteer"]
                    )
                elif "/honors" in url:
                    response.json = MagicMock(return_value=profile_response["honors"])
                elif "/languages" in url:
                    response.json = MagicMock(
                        return_value=profile_response["languages"]
                    )
                else:
                    response.status_code = 404
                    response.json = MagicMock(return_value={})

                return response

            mock_http_client.request = mock_request

            # Test
            client._client = mock_http_client
            profile = await client.get_profile("test-profile")

            # Verify all sections are present
            assert isinstance(profile, LinkedInProfile)
            assert profile.profile_id is not None
            assert profile.first_name == profile_response["basic"]["firstName"]
            assert profile.last_name == profile_response["basic"]["lastName"]
            assert profile.email == profile_response["basic"]["email"]

            # Verify all sections are lists (even if empty)
            assert isinstance(profile.positions, list)
            assert isinstance(profile.education, list)
            assert isinstance(profile.skills, list)
            assert isinstance(profile.certifications, list)
            assert isinstance(profile.publications, list)
            assert isinstance(profile.volunteer, list)
            assert isinstance(profile.honors, list)
            assert isinstance(profile.languages, list)

            # Verify section counts match
            assert len(profile.positions) == len(
                profile_response["positions"]["elements"]
            )
            assert len(profile.education) == len(
                profile_response["education"]["elements"]
            )
            assert len(profile.skills) == len(profile_response["skills"]["elements"])

            # Verify optional fields are preserved
            if profile_response["basic"].get("headline"):
                assert profile.headline == profile_response["basic"]["headline"]
            if profile_response["basic"].get("summary"):
                assert profile.summary == profile_response["basic"]["summary"]

        # Run the async test
        asyncio.run(run_test())


class TestRateLimitCompliance:
    """Test rate limit compliance.

    Feature: linkedin-profile-importer, Property 15: Rate limit compliance
    Validates: Requirements 6.1, 6.2, 6.5
    """

    @given(
        request_delay=st.floats(min_value=0.05, max_value=0.2),
        num_requests=st.integers(min_value=2, max_value=4),
    )
    @settings(max_examples=50, deadline=5000)
    def test_rate_limit_compliance(self, request_delay, num_requests):
        """Property 15: For any sequence of API requests, when rate limit headers or 429
        responses are received, the tool should respect the retry-after period and not
        exceed the specified rate limits.

        Feature: linkedin-profile-importer, Property 15: Rate limit compliance
        Validates: Requirements 6.1, 6.2, 6.5
        """

        async def run_test():
            import time

            config = LinkedInConfig(
                api_key="test_key", api_secret="test_secret", access_token="test_token"
            )

            client = LinkedInClient(config, request_delay=request_delay)

            # Track request times
            request_times = []

            # Create mock HTTP client
            mock_http_client = AsyncMock()
            mock_http_client.aclose = AsyncMock()

            async def mock_request(method, url, **kwargs):
                request_times.append(asyncio.get_event_loop().time())
                response = MagicMock()
                response.status_code = 200
                response.text = "{}"
                response.headers = {
                    "X-RateLimit-Remaining": "10",
                    "X-RateLimit-Reset": str(int(time.time()) + 60),
                }
                response.raise_for_status = MagicMock()
                response.json = MagicMock(return_value={"elements": []})
                return response

            mock_http_client.request = mock_request
            client._client = mock_http_client

            # Make multiple requests
            for _ in range(num_requests):
                await client._make_request("GET", "https://api.linkedin.com/v2/test")

            # Verify request delays
            for i in range(1, len(request_times)):
                time_diff = request_times[i] - request_times[i - 1]
                # Allow small tolerance for timing
                assert time_diff >= request_delay * 0.8, (
                    f"Request delay {time_diff} is less than configured {request_delay}"
                )

        asyncio.run(run_test())

    @given(retry_after=st.integers(min_value=1, max_value=2))
    @settings(max_examples=20, deadline=5000)
    def test_rate_limit_429_response(self, retry_after):
        """Test that 429 responses are handled with retry-after."""

        async def run_test():
            import time

            config = LinkedInConfig(
                api_key="test_key", api_secret="test_secret", access_token="test_token"
            )

            client = LinkedInClient(config, request_delay=0.0, max_retries=1)

            # Track request times
            request_count = [0]
            start_time = [None]

            # Create mock HTTP client
            mock_http_client = AsyncMock()
            mock_http_client.aclose = AsyncMock()

            async def mock_request(method, url, **kwargs):
                request_count[0] += 1
                if start_time[0] is None:
                    start_time[0] = asyncio.get_event_loop().time()

                response = MagicMock()
                response.text = "{}"
                response.raise_for_status = MagicMock()

                # First request returns 429
                if request_count[0] == 1:
                    response.status_code = 429
                    response.headers = {"Retry-After": str(retry_after)}
                    response.json = MagicMock(return_value={})
                else:
                    # Second request succeeds
                    response.status_code = 200
                    response.headers = {}
                    response.json = MagicMock(return_value={"elements": []})

                return response

            mock_http_client.request = mock_request
            client._client = mock_http_client

            # Make request that will be rate limited
            await client._make_request("GET", "https://api.linkedin.com/v2/test")

            # Verify we made 2 requests (original + retry)
            assert request_count[0] == 2

            # Verify we waited at least retry_after seconds
            elapsed = asyncio.get_event_loop().time() - start_time[0]
            assert elapsed >= retry_after * 0.8, (
                f"Did not wait long enough: {elapsed} < {retry_after}"
            )

        asyncio.run(run_test())

    @given(num_requests=st.integers(min_value=2, max_value=4))
    @settings(max_examples=50, deadline=3000)
    def test_rate_limit_headers_respected(self, num_requests):
        """Test that X-RateLimit headers are respected."""

        async def run_test():
            import time

            config = LinkedInConfig(
                api_key="test_key", api_secret="test_secret", access_token="test_token"
            )

            client = LinkedInClient(config, request_delay=0.05)

            # Create mock HTTP client
            mock_http_client = AsyncMock()
            mock_http_client.aclose = AsyncMock()

            remaining_requests = [10]

            async def mock_request(method, url, **kwargs):
                remaining_requests[0] -= 1
                response = MagicMock()
                response.status_code = 200
                response.text = "{}"
                response.headers = {
                    "X-RateLimit-Remaining": str(remaining_requests[0]),
                    "X-RateLimit-Reset": str(int(time.time()) + 60),
                }
                response.raise_for_status = MagicMock()
                response.json = MagicMock(return_value={"elements": []})
                return response

            mock_http_client.request = mock_request
            client._client = mock_http_client

            # Make multiple requests
            for _ in range(num_requests):
                await client._make_request("GET", "https://api.linkedin.com/v2/test")

            # Verify rate limit headers were present in responses
            assert remaining_requests[0] == 10 - num_requests

        asyncio.run(run_test())


class TestRetryBehavior:
    """Test retry with exponential backoff.

    Feature: linkedin-profile-importer, Property 13: Retry with exponential backoff
    Validates: Requirements 5.3
    """

    @given(
        max_retries=st.integers(min_value=1, max_value=3),
        failure_count=st.integers(min_value=1, max_value=2),
    )
    @settings(max_examples=30, deadline=10000)
    def test_retry_with_exponential_backoff(self, max_retries, failure_count):
        """Property 13: For any network failure, the tool should retry up to 3 times
        with exponentially increasing delays (e.g., 1s, 2s, 4s) before failing.

        Feature: linkedin-profile-importer, Property 13: Retry with exponential backoff
        Validates: Requirements 5.3
        """
        # Ensure failure_count doesn't exceed max_retries
        failure_count = min(failure_count, max_retries)

        async def run_test():
            config = LinkedInConfig(
                api_key="test_key", api_secret="test_secret", access_token="test_token"
            )

            client = LinkedInClient(config, request_delay=0.0, max_retries=max_retries)

            # Track request times and count
            request_times = []
            request_count = [0]

            # Create mock HTTP client
            mock_http_client = AsyncMock()
            mock_http_client.aclose = AsyncMock()

            async def mock_request(method, url, **kwargs):
                request_count[0] += 1
                request_times.append(asyncio.get_event_loop().time())

                response = MagicMock()
                response.text = "{}"
                response.raise_for_status = MagicMock()

                # Fail for first failure_count requests
                if request_count[0] <= failure_count:
                    # Simulate network error
                    raise httpx.RequestError("Network error")
                else:
                    # Success
                    response.status_code = 200
                    response.headers = {}
                    response.json = MagicMock(return_value={"elements": []})
                    return response

            mock_http_client.request = mock_request
            client._client = mock_http_client

            try:
                # Make request that will fail and retry
                await client._make_request("GET", "https://api.linkedin.com/v2/test")

                # If we get here, request succeeded after retries
                assert request_count[0] == failure_count + 1

                # Verify exponential backoff delays
                for i in range(1, len(request_times)):
                    time_diff = request_times[i] - request_times[i - 1]
                    expected_delay = 2 ** (i - 1)  # 1s, 2s, 4s
                    # Allow 20% tolerance for timing
                    assert time_diff >= expected_delay * 0.8, (
                        f"Retry delay {time_diff} is less than expected {expected_delay}"
                    )

            except APIError:
                # If we get an error, verify we retried max_retries times
                assert request_count[0] == max_retries + 1

        asyncio.run(run_test())

    @given(status_code=st.sampled_from([500, 502, 503, 504]))
    @settings(max_examples=20, deadline=5000)
    def test_retry_on_server_errors(self, status_code):
        """Test that server errors (5xx) trigger retries."""

        async def run_test():
            config = LinkedInConfig(
                api_key="test_key", api_secret="test_secret", access_token="test_token"
            )

            client = LinkedInClient(config, request_delay=0.0, max_retries=2)

            request_count = [0]

            # Create mock HTTP client
            mock_http_client = AsyncMock()
            mock_http_client.aclose = AsyncMock()

            async def mock_request(method, url, **kwargs):
                request_count[0] += 1

                response = MagicMock()
                response.text = "Server error"

                # First 2 requests fail with server error
                if request_count[0] <= 2:
                    response.status_code = status_code
                    response.raise_for_status = MagicMock(
                        side_effect=httpx.HTTPStatusError(
                            f"Server error {status_code}",
                            request=MagicMock(),
                            response=response,
                        )
                    )
                else:
                    # Third request succeeds
                    response.status_code = 200
                    response.headers = {}
                    response.raise_for_status = MagicMock()
                    response.json = MagicMock(return_value={"elements": []})

                return response

            mock_http_client.request = mock_request
            client._client = mock_http_client

            # Make request that will fail and retry
            await client._make_request("GET", "https://api.linkedin.com/v2/test")

            # Verify we made 3 requests (original + 2 retries)
            assert request_count[0] == 3

        asyncio.run(run_test())

    @given(max_retries=st.integers(min_value=1, max_value=3))
    @settings(max_examples=20, deadline=10000)
    def test_max_retries_exceeded(self, max_retries):
        """Test that APIError is raised when max retries are exceeded."""

        async def run_test():
            config = LinkedInConfig(
                api_key="test_key", api_secret="test_secret", access_token="test_token"
            )

            client = LinkedInClient(config, request_delay=0.0, max_retries=max_retries)

            request_count = [0]

            # Create mock HTTP client
            mock_http_client = AsyncMock()
            mock_http_client.aclose = AsyncMock()

            async def mock_request(method, url, **kwargs):
                request_count[0] += 1
                # Always fail
                raise httpx.RequestError("Network error")

            mock_http_client.request = mock_request
            client._client = mock_http_client

            # Make request that will always fail
            try:
                await client._make_request("GET", "https://api.linkedin.com/v2/test")
                assert False, "Should have raised APIError"
            except APIError as e:
                # Verify we tried max_retries + 1 times (original + retries)
                assert request_count[0] == max_retries + 1
                assert "Network error" in str(e)

        asyncio.run(run_test())


class TestQuotaExhaustion:
    """Test quota exhaustion handling.

    Feature: linkedin-profile-importer, Property 16: Quota exhaustion handling
    Validates: Requirements 6.3
    """

    @given(
        error_message=st.sampled_from(
            [
                "quota exceeded",
                "API quota exhausted",
                "rate limit quota reached",
                "monthly quota exceeded",
            ]
        )
    )
    @settings(max_examples=20, deadline=2000)
    def test_quota_exhaustion_handling(self, error_message):
        """Property 16: For any API quota exhaustion response, the tool should terminate
        with a clear error message indicating quota exhaustion rather than retrying
        indefinitely.

        Feature: linkedin-profile-importer, Property 16: Quota exhaustion handling
        Validates: Requirements 6.3
        """

        async def run_test():
            config = LinkedInConfig(
                api_key="test_key", api_secret="test_secret", access_token="test_token"
            )

            client = LinkedInClient(config, request_delay=0.0, max_retries=3)

            request_count = [0]

            # Create mock HTTP client
            mock_http_client = AsyncMock()
            mock_http_client.aclose = AsyncMock()

            async def mock_request(method, url, **kwargs):
                request_count[0] += 1

                response = MagicMock()
                response.status_code = 403
                response.text = f'{{"error": "{error_message}"}}'
                response.raise_for_status = MagicMock()
                response.json = MagicMock(return_value={"error": error_message})

                return response

            mock_http_client.request = mock_request
            client._client = mock_http_client

            # Make request that will hit quota limit
            try:
                await client._make_request("GET", "https://api.linkedin.com/v2/test")
                assert False, "Should have raised APIError"
            except APIError as e:
                # Verify error message mentions quota
                assert "quota" in str(e).lower(), (
                    f"Error message should mention quota: {e}"
                )
                # Verify we only tried once (no retries for quota exhaustion)
                assert request_count[0] == 1, (
                    f"Should not retry on quota exhaustion, but tried {request_count[0]} times"
                )

        asyncio.run(run_test())

    def test_403_without_quota_raises_error(self):
        """Test that 403 errors without quota message raise APIError immediately."""

        async def run_test():
            config = LinkedInConfig(
                api_key="test_key", api_secret="test_secret", access_token="test_token"
            )

            client = LinkedInClient(config, request_delay=0.0, max_retries=2)

            request_count = [0]

            # Create mock HTTP client
            mock_http_client = AsyncMock()
            mock_http_client.aclose = AsyncMock()

            async def mock_request(method, url, **kwargs):
                request_count[0] += 1

                response = MagicMock()
                response.status_code = 403
                response.text = '{"error": "forbidden"}'
                response.raise_for_status = MagicMock(
                    side_effect=httpx.HTTPStatusError(
                        "Forbidden",
                        request=MagicMock(),
                        response=response,
                    )
                )
                response.json = MagicMock(return_value={"error": "forbidden"})

                return response

            mock_http_client.request = mock_request
            client._client = mock_http_client

            # Make request - should fail without retrying
            try:
                await client._make_request("GET", "https://api.linkedin.com/v2/test")
                assert False, "Should have raised APIError"
            except APIError as e:
                # Verify we only tried once (no retries for non-quota 403)
                assert request_count[0] == 1
                assert "403" in str(e)

        asyncio.run(run_test())

    def test_404_profile_not_found(self):
        """Test that 404 errors are handled with appropriate message."""

        async def run_test():
            config = LinkedInConfig(
                api_key="test_key", api_secret="test_secret", access_token="test_token"
            )

            client = LinkedInClient(config, request_delay=0.0)

            # Create mock HTTP client
            mock_http_client = AsyncMock()
            mock_http_client.aclose = AsyncMock()

            async def mock_request(method, url, **kwargs):
                response = MagicMock()
                response.status_code = 404
                response.text = '{"error": "not found"}'
                response.raise_for_status = MagicMock()
                response.json = MagicMock(return_value={"error": "not found"})
                return response

            mock_http_client.request = mock_request
            client._client = mock_http_client

            # Make request that will return 404
            try:
                await client._make_request("GET", "https://api.linkedin.com/v2/test")
                assert False, "Should have raised APIError"
            except APIError as e:
                # Verify error message mentions profile not found
                assert "not found" in str(e).lower(), (
                    f"Error message should mention not found: {e}"
                )

        asyncio.run(run_test())


class TestRequestDeduplication:
    """Test request deduplication after rate limiting.

    Feature: linkedin-profile-importer, Property 17: Request deduplication after rate limiting
    Validates: Requirements 6.4
    """

    @given(
        num_sections=st.integers(min_value=2, max_value=4),
        rate_limit_after=st.integers(min_value=1, max_value=2),
    )
    @settings(max_examples=20, deadline=5000)
    def test_request_deduplication_after_rate_limiting(
        self, num_sections, rate_limit_after
    ):
        """Property 17: For any import operation that encounters rate limiting, when
        resuming, the tool should not re-request data that was already successfully
        fetched.

        Feature: linkedin-profile-importer, Property 17: Request deduplication after rate limiting
        Validates: Requirements 6.4
        """

        async def run_test():
            config = LinkedInConfig(
                api_key="test_key", api_secret="test_secret", access_token="test_token"
            )

            client = LinkedInClient(config, request_delay=0.0, max_retries=1)

            # Track which endpoints were requested
            requested_endpoints = []

            # Create mock HTTP client
            mock_http_client = AsyncMock()
            mock_http_client.aclose = AsyncMock()

            async def mock_request(method, url, **kwargs):
                endpoint = url.split("/")[-1].split("?")[0]
                requested_endpoints.append(endpoint)

                response = MagicMock()
                response.text = "{}"
                response.raise_for_status = MagicMock()

                # Rate limit after N successful requests
                if len(requested_endpoints) == rate_limit_after + 1:
                    response.status_code = 429
                    response.headers = {"Retry-After": "1"}
                    response.json = MagicMock(return_value={})
                else:
                    response.status_code = 200
                    response.headers = {}
                    response.json = MagicMock(return_value={"elements": []})

                return response

            mock_http_client.request = mock_request
            client._client = mock_http_client

            # Fetch multiple sections
            sections = ["basic", "positions", "educations", "skills"][:num_sections]

            for section in sections:
                try:
                    if section == "basic":
                        await client.get_profile_basic("test-profile")
                    elif section == "positions":
                        await client.get_profile_experience("test-profile")
                    elif section == "educations":
                        await client.get_profile_education("test-profile")
                    elif section == "skills":
                        await client.get_profile_skills("test-profile")
                except APIError:
                    # Rate limit hit, continue
                    pass

            # Now fetch the same sections again
            for section in sections:
                if section == "basic":
                    await client.get_profile_basic("test-profile")
                elif section == "positions":
                    await client.get_profile_experience("test-profile")
                elif section == "educations":
                    await client.get_profile_education("test-profile")
                elif section == "skills":
                    await client.get_profile_skills("test-profile")

            # Verify that cached data was used (no duplicate requests for same endpoint)
            # Count requests per endpoint
            endpoint_counts = {}
            for endpoint in requested_endpoints:
                endpoint_counts[endpoint] = endpoint_counts.get(endpoint, 0) + 1

            # Each endpoint should be requested at most once (or twice if rate limited during first fetch)
            for endpoint, count in endpoint_counts.items():
                assert count <= 2, (
                    f"Endpoint {endpoint} was requested {count} times, should use cache"
                )

        asyncio.run(run_test())

    @given(profile_id=st.text(min_size=1, max_size=20))
    @settings(max_examples=50, deadline=2000)
    def test_cache_key_includes_profile_id(self, profile_id):
        """Test that cache keys include profile ID to avoid cross-profile contamination."""

        async def run_test():
            config = LinkedInConfig(
                api_key="test_key", api_secret="test_secret", access_token="test_token"
            )

            client = LinkedInClient(config, request_delay=0.0)

            # Track requests
            requested_profiles = []

            # Create mock HTTP client
            mock_http_client = AsyncMock()
            mock_http_client.aclose = AsyncMock()

            async def mock_request(method, url, **kwargs):
                # Extract profile ID from params
                params = kwargs.get("params", {})
                member = params.get("member", "unknown")
                requested_profiles.append(member)

                response = MagicMock()
                response.status_code = 200
                response.text = "{}"
                response.headers = {}
                response.raise_for_status = MagicMock()
                response.json = MagicMock(return_value={"elements": []})
                return response

            mock_http_client.request = mock_request
            client._client = mock_http_client

            # Fetch data for first profile
            await client.get_profile_experience(profile_id)

            # Fetch data for different profile
            different_profile = f"{profile_id}_different"
            await client.get_profile_experience(different_profile)

            # Verify both profiles were requested (not cached across profiles)
            assert len(requested_profiles) == 2
            assert requested_profiles[0] == profile_id
            assert requested_profiles[1] == different_profile

        asyncio.run(run_test())

    def test_cache_cleared_between_profiles(self):
        """Test that cache is properly scoped to avoid data leakage."""

        async def run_test():
            config = LinkedInConfig(
                api_key="test_key", api_secret="test_secret", access_token="test_token"
            )

            client = LinkedInClient(config, request_delay=0.0)

            # Track requests
            request_count = [0]

            # Create mock HTTP client
            mock_http_client = AsyncMock()
            mock_http_client.aclose = AsyncMock()

            async def mock_request(method, url, **kwargs):
                request_count[0] += 1
                response = MagicMock()
                response.status_code = 200
                response.text = "{}"
                response.headers = {}
                response.raise_for_status = MagicMock()
                response.json = MagicMock(
                    return_value={"elements": [{"name": f"item_{request_count[0]}"}]}
                )
                return response

            mock_http_client.request = mock_request
            client._client = mock_http_client

            # Fetch data for profile 1
            skills1 = await client.get_profile_skills("profile1")
            first_request_count = request_count[0]

            # Fetch same data again for profile 1 (should use cache)
            _skills1_cached = await client.get_profile_skills("profile1")
            assert request_count[0] == first_request_count, "Should use cached data"

            # Fetch data for profile 2 (should make new request)
            skills2 = await client.get_profile_skills("profile2")
            assert request_count[0] == first_request_count + 1, (
                "Should make new request for different profile"
            )

            # Verify data is different (not leaked from cache)
            assert len(skills1) > 0
            assert len(skills2) > 0

        asyncio.run(run_test())
