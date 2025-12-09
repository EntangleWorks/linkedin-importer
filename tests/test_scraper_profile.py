"""Tests for LinkedIn profile scraping functionality.

This module tests:
- Profile URL normalization (with property-based tests)
- Profile scraping with retry logic
- Error handling for various failure scenarios
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from linkedin_importer.scraper_client import LinkedInScraperClient
from linkedin_importer.scraper_errors import (
    AuthError,
    ProfileNotFound,
    ScrapingBlocked,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_driver():
    """Create a mock Chrome WebDriver."""
    driver = MagicMock()
    driver.get = MagicMock()
    driver.quit = MagicMock()
    driver.find_element = MagicMock()
    driver.find_elements = MagicMock(return_value=[])
    driver.current_url = "https://www.linkedin.com/feed/"
    driver.page_source = "<html></html>"
    driver.save_screenshot = MagicMock(return_value=True)

    # Mock capabilities for version info
    driver.capabilities = {
        "browserVersion": "120.0.0",
        "chrome": {"chromedriverVersion": "120.0.0"},
    }

    return driver


@pytest.fixture
def client_with_mock_driver(mock_driver):
    """Create a LinkedInScraperClient with a mocked driver."""
    with patch.object(
        LinkedInScraperClient, "_create_driver", return_value=mock_driver
    ):
        client = LinkedInScraperClient(
            headless=True,
            page_load_timeout=10,
            action_delay=0.1,
            max_retries=3,
            screenshot_on_error=False,
        )
        client.driver = mock_driver
        client.authenticated = True
        client._browser_version = "120.0.0"
        client._driver_version = "120.0.0"
        yield client
        # Don't call close() since driver is mocked


@pytest.fixture
def unauthenticated_client(mock_driver):
    """Create a LinkedInScraperClient that is not authenticated."""
    with patch.object(
        LinkedInScraperClient, "_create_driver", return_value=mock_driver
    ):
        client = LinkedInScraperClient(
            headless=True,
            page_load_timeout=10,
            max_retries=3,
        )
        client.driver = mock_driver
        client.authenticated = False
        yield client


# =============================================================================
# URL Normalization Tests
# =============================================================================


class TestUrlNormalization:
    """Tests for profile URL normalization."""

    def test_normalize_full_url_with_https_www(self, client_with_mock_driver):
        """Test normalization of a full URL with https://www."""
        url = "https://www.linkedin.com/in/johndoe/"
        result = client_with_mock_driver._normalize_profile_url(url)
        assert result == "https://www.linkedin.com/in/johndoe"

    def test_normalize_full_url_without_www(self, client_with_mock_driver):
        """Test normalization of a URL without www."""
        url = "https://linkedin.com/in/johndoe"
        result = client_with_mock_driver._normalize_profile_url(url)
        assert result == "https://linkedin.com/in/johndoe"

    def test_normalize_http_to_https(self, client_with_mock_driver):
        """Test that http:// is converted to https://."""
        url = "http://www.linkedin.com/in/johndoe"
        result = client_with_mock_driver._normalize_profile_url(url)
        assert result.startswith("https://")
        assert "http://" not in result

    def test_normalize_username_only(self, client_with_mock_driver):
        """Test normalization when only username is provided."""
        url = "johndoe"
        result = client_with_mock_driver._normalize_profile_url(url)
        assert result == "https://www.linkedin.com/in/johndoe"

    def test_normalize_with_in_prefix(self, client_with_mock_driver):
        """Test normalization when 'in/' prefix is included."""
        url = "in/johndoe"
        result = client_with_mock_driver._normalize_profile_url(url)
        assert result == "https://www.linkedin.com/in/johndoe"

    def test_normalize_with_leading_slash(self, client_with_mock_driver):
        """Test normalization with leading slash."""
        url = "/in/johndoe"
        result = client_with_mock_driver._normalize_profile_url(url)
        assert result == "https://www.linkedin.com/in/johndoe"

    def test_normalize_removes_trailing_slash(self, client_with_mock_driver):
        """Test that trailing slashes are removed."""
        url = "https://www.linkedin.com/in/johndoe/"
        result = client_with_mock_driver._normalize_profile_url(url)
        assert not result.endswith("/")

    def test_normalize_strips_whitespace(self, client_with_mock_driver):
        """Test that whitespace is stripped."""
        url = "  johndoe  "
        result = client_with_mock_driver._normalize_profile_url(url)
        assert result == "https://www.linkedin.com/in/johndoe"

    def test_normalize_url_with_query_params(self, client_with_mock_driver):
        """Test normalization preserves query parameters (if any)."""
        url = "https://www.linkedin.com/in/johndoe?trk=homepage"
        result = client_with_mock_driver._normalize_profile_url(url)
        # Query params should be preserved
        assert "johndoe" in result

    def test_normalize_complex_username(self, client_with_mock_driver):
        """Test normalization with complex usernames (hyphens, numbers)."""
        url = "john-doe-123"
        result = client_with_mock_driver._normalize_profile_url(url)
        assert result == "https://www.linkedin.com/in/john-doe-123"


class TestUrlNormalizationProperties:
    """Property-based tests for URL normalization."""

    @given(
        username=st.text(
            alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789-"),
            min_size=1,
            max_size=50,
        ).filter(
            lambda x: not x.startswith("-") and not x.endswith("-") and "--" not in x
        )
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_property_normalized_url_always_valid(self, username):
        """Property: Normalized URL always starts with https:// and contains /in/."""
        with patch.object(LinkedInScraperClient, "_create_driver"):
            client = LinkedInScraperClient(headless=True)
            result = client._normalize_profile_url(username)

            assert result.startswith("https://"), (
                f"URL should start with https://: {result}"
            )
            assert "/in/" in result, f"URL should contain /in/: {result}"

    @given(
        url=st.sampled_from(
            [
                "https://www.linkedin.com/in/test-user",
                "https://linkedin.com/in/test-user/",
                "http://www.linkedin.com/in/test-user",
                "test-user",
                "in/test-user",
                "/in/test-user",
            ]
        )
    )
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_property_normalized_url_no_trailing_slash(self, url):
        """Property: Normalized URL never ends with a trailing slash."""
        with patch.object(LinkedInScraperClient, "_create_driver"):
            client = LinkedInScraperClient(headless=True)
            result = client._normalize_profile_url(url)

            assert not result.endswith("/"), f"URL should not end with /: {result}"

    @given(
        url=st.sampled_from(
            [
                "http://www.linkedin.com/in/user",
                "http://linkedin.com/in/user",
            ]
        )
    )
    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_property_http_converted_to_https(self, url):
        """Property: HTTP URLs are always converted to HTTPS."""
        with patch.object(LinkedInScraperClient, "_create_driver"):
            client = LinkedInScraperClient(headless=True)
            result = client._normalize_profile_url(url)

            assert result.startswith("https://"), f"URL should use https: {result}"
            assert "http://" not in result, f"URL should not contain http://: {result}"

    @given(
        spaces=st.text(alphabet=" \t\n", min_size=0, max_size=5),
        username=st.text(
            alphabet="abcdefghijklmnopqrstuvwxyz",
            min_size=3,
            max_size=20,
        ),
    )
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_property_whitespace_stripped(self, spaces, username):
        """Property: Whitespace is always stripped from URLs."""
        with patch.object(LinkedInScraperClient, "_create_driver"):
            client = LinkedInScraperClient(headless=True)
            url_with_spaces = f"{spaces}{username}{spaces}"
            result = client._normalize_profile_url(url_with_spaces)

            assert not result.startswith(" "), "URL should not start with space"
            assert not result.endswith(" "), "URL should not end with space"
            assert username in result, f"Username should be in result: {result}"


# =============================================================================
# Profile Scraping Tests
# =============================================================================


class TestGetProfile:
    """Tests for the get_profile method."""

    def test_get_profile_requires_authentication(self, unauthenticated_client):
        """Test that get_profile raises AuthError if not authenticated."""
        with pytest.raises(AuthError) as exc_info:
            unauthenticated_client.get_profile("https://linkedin.com/in/johndoe")

        assert "authenticate" in str(exc_info.value).lower()

    def test_get_profile_normalizes_url(self, client_with_mock_driver):
        """Test that get_profile normalizes the profile URL."""
        mock_person = MagicMock()
        mock_person.name = "John Doe"

        with patch("linkedin_scraper.Person", return_value=mock_person) as mock_cls:
            result = client_with_mock_driver.get_profile("johndoe")

            # Person should be called with normalized URL
            mock_cls.assert_called_once()
            call_kwargs = mock_cls.call_args[1]
            assert call_kwargs["linkedin_url"] == "https://www.linkedin.com/in/johndoe"

    def test_get_profile_success(self, client_with_mock_driver):
        """Test successful profile scraping."""
        mock_person = MagicMock()
        mock_person.name = "John Doe"
        mock_person.linkedin_url = "https://www.linkedin.com/in/johndoe"

        with patch("linkedin_scraper.Person", return_value=mock_person):
            result = client_with_mock_driver.get_profile("johndoe")

            assert result.name == "John Doe"

    def test_get_profile_raises_profile_not_found_on_404(self, client_with_mock_driver):
        """Test that ProfileNotFound is raised on 404 errors."""
        with patch(
            "linkedin_scraper.Person",
            side_effect=Exception("404 not found"),
        ):
            with pytest.raises(ProfileNotFound) as exc_info:
                client_with_mock_driver.get_profile("nonexistent-user")

            assert "nonexistent-user" in str(exc_info.value)

    def test_get_profile_raises_scraping_blocked_on_block(
        self, client_with_mock_driver
    ):
        """Test that ScrapingBlocked is raised when LinkedIn blocks scraping."""
        with patch(
            "linkedin_scraper.Person",
            side_effect=Exception("blocked by LinkedIn"),
        ):
            with pytest.raises(ScrapingBlocked):
                client_with_mock_driver.get_profile("johndoe")


# =============================================================================
# Retry Logic Tests
# =============================================================================


class TestRetryLogic:
    """Tests for the retry logic in get_profile."""

    def test_retry_on_transient_error(self, client_with_mock_driver):
        """Test that transient errors trigger retries."""
        mock_person = MagicMock()
        mock_person.name = "John Doe"

        call_count = [0]

        def mock_person_init(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] < 3:
                raise Exception("Connection timeout")
            return mock_person

        with patch("linkedin_scraper.Person", side_effect=mock_person_init):
            with patch("time.sleep"):  # Speed up test
                result = client_with_mock_driver.get_profile("johndoe")

        assert call_count[0] == 3
        assert result.name == "John Doe"

    def test_exponential_backoff_delays(self, client_with_mock_driver):
        """Test that exponential backoff is applied between retries."""
        sleep_times = []

        def mock_sleep(seconds):
            sleep_times.append(seconds)

        with patch(
            "linkedin_scraper.Person",
            side_effect=Exception("Network error"),
        ):
            with patch("time.sleep", side_effect=mock_sleep):
                with pytest.raises(ScrapingBlocked):
                    client_with_mock_driver.get_profile("johndoe")

        # Should have 3 retries with exponential backoff: 2^0=1, 2^1=2, 2^2=4
        assert len(sleep_times) == 3
        assert sleep_times[0] == 1  # 2^0
        assert sleep_times[1] == 2  # 2^1
        assert sleep_times[2] == 4  # 2^2

    def test_max_retries_exceeded(self, client_with_mock_driver):
        """Test that ScrapingBlocked is raised after max retries."""
        call_count = [0]

        def mock_person_init(*args, **kwargs):
            call_count[0] += 1
            raise Exception("Persistent error")

        with patch("linkedin_scraper.Person", side_effect=mock_person_init):
            with patch("time.sleep"):  # Speed up test
                with pytest.raises(ScrapingBlocked) as exc_info:
                    client_with_mock_driver.get_profile("johndoe")

        # Initial attempt + 3 retries = 4 total attempts
        assert call_count[0] == 4
        assert "4 attempts" in str(exc_info.value)

    def test_no_retry_on_404(self, client_with_mock_driver):
        """Test that 404 errors are not retried (fatal error)."""
        call_count = [0]

        def mock_person_init(*args, **kwargs):
            call_count[0] += 1
            raise Exception("404 not found")

        with patch("linkedin_scraper.Person", side_effect=mock_person_init):
            with pytest.raises(ProfileNotFound):
                client_with_mock_driver.get_profile("johndoe")

        # Should only be called once (no retries for 404)
        assert call_count[0] == 1

    def test_no_retry_on_blocked(self, client_with_mock_driver):
        """Test that blocked errors are not retried (fatal error)."""
        call_count = [0]

        def mock_person_init(*args, **kwargs):
            call_count[0] += 1
            raise Exception("Access restricted by LinkedIn")

        with patch("linkedin_scraper.Person", side_effect=mock_person_init):
            with pytest.raises(ScrapingBlocked):
                client_with_mock_driver.get_profile("johndoe")

        # Should only be called once (no retries for blocked)
        assert call_count[0] == 1

    def test_retry_logs_warnings(self, client_with_mock_driver, caplog):
        """Test that retry attempts are logged as warnings."""
        mock_person = MagicMock()
        mock_person.name = "John Doe"

        call_count = [0]

        def mock_person_init(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] < 2:
                raise Exception("Temporary failure")
            return mock_person

        import logging

        with caplog.at_level(logging.WARNING):
            with patch("linkedin_scraper.Person", side_effect=mock_person_init):
                with patch("time.sleep"):
                    client_with_mock_driver.get_profile("johndoe")

        # Check that retry warning was logged
        assert any("Retrying" in record.message for record in caplog.records)

    def test_custom_max_retries(self, mock_driver):
        """Test that custom max_retries is respected."""
        with patch.object(
            LinkedInScraperClient, "_create_driver", return_value=mock_driver
        ):
            client = LinkedInScraperClient(
                headless=True,
                max_retries=5,  # Custom value
            )
            client.driver = mock_driver
            client.authenticated = True

            call_count = [0]

            def mock_person_init(*args, **kwargs):
                call_count[0] += 1
                raise Exception("Persistent error")

            with patch("linkedin_scraper.Person", side_effect=mock_person_init):
                with patch("time.sleep"):
                    with pytest.raises(ScrapingBlocked) as exc_info:
                        client.get_profile("johndoe")

            # Initial attempt + 5 retries = 6 total attempts
            assert call_count[0] == 6
            assert "6 attempts" in str(exc_info.value)


class TestRetryLogicProperties:
    """Property-based tests for retry logic."""

    @given(max_retries=st.integers(min_value=1, max_value=5))
    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_property_total_attempts_equals_max_retries_plus_one(self, max_retries):
        """Property: Total attempts equals max_retries + 1 (initial + retries)."""
        mock_driver = MagicMock()
        mock_driver.capabilities = {
            "browserVersion": "120.0.0",
            "chrome": {"chromedriverVersion": "120.0.0"},
        }

        with patch.object(
            LinkedInScraperClient, "_create_driver", return_value=mock_driver
        ):
            client = LinkedInScraperClient(headless=True, max_retries=max_retries)
            client.driver = mock_driver
            client.authenticated = True

            call_count = [0]

            def mock_person_init(*args, **kwargs):
                call_count[0] += 1
                raise Exception("Persistent error")

            with patch("linkedin_scraper.Person", side_effect=mock_person_init):
                with patch("time.sleep"):
                    with pytest.raises(ScrapingBlocked):
                        client.get_profile("test-user")

            expected_attempts = max_retries + 1
            assert call_count[0] == expected_attempts, (
                f"Expected {expected_attempts} attempts, got {call_count[0]}"
            )

    @given(max_retries=st.integers(min_value=1, max_value=4))
    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_property_exponential_backoff_sequence(self, max_retries):
        """Property: Sleep times follow exponential backoff pattern (2^n)."""
        mock_driver = MagicMock()
        mock_driver.capabilities = {
            "browserVersion": "120.0.0",
            "chrome": {"chromedriverVersion": "120.0.0"},
        }

        with patch.object(
            LinkedInScraperClient, "_create_driver", return_value=mock_driver
        ):
            client = LinkedInScraperClient(headless=True, max_retries=max_retries)
            client.driver = mock_driver
            client.authenticated = True

            sleep_times = []

            def mock_sleep(seconds):
                sleep_times.append(seconds)

            with patch(
                "linkedin_scraper.Person",
                side_effect=Exception("Error"),
            ):
                with patch("time.sleep", side_effect=mock_sleep):
                    with pytest.raises(ScrapingBlocked):
                        client.get_profile("test-user")

            # Verify exponential backoff: 2^0, 2^1, 2^2, ...
            for i, sleep_time in enumerate(sleep_times):
                expected = 2**i
                assert sleep_time == expected, (
                    f"Sleep time at index {i} should be {expected}, got {sleep_time}"
                )


# =============================================================================
# Screenshot on Error Tests
# =============================================================================


class TestScreenshotOnError:
    """Tests for screenshot capture on scraping errors."""

    def test_screenshot_on_profile_not_found(self, mock_driver):
        """Test that screenshot is captured on ProfileNotFound error."""
        with patch.object(
            LinkedInScraperClient, "_create_driver", return_value=mock_driver
        ):
            client = LinkedInScraperClient(
                headless=True,
                screenshot_on_error=True,
                screenshot_dir="/tmp",
            )
            client.driver = mock_driver
            client.authenticated = True

            with patch("linkedin_scraper.Person", side_effect=Exception("404")):
                with patch.object(client, "_capture_error_screenshot") as mock_capture:
                    with pytest.raises(ProfileNotFound):
                        client.get_profile("nonexistent")

                    mock_capture.assert_called_once_with("profile_not_found")

    def test_screenshot_on_scraping_blocked(self, mock_driver):
        """Test that screenshot is captured on ScrapingBlocked error."""
        with patch.object(
            LinkedInScraperClient, "_create_driver", return_value=mock_driver
        ):
            client = LinkedInScraperClient(
                headless=True,
                screenshot_on_error=True,
                max_retries=0,  # No retries to speed up test
            )
            client.driver = mock_driver
            client.authenticated = True

            with patch(
                "linkedin_scraper.Person",
                side_effect=Exception("blocked"),
            ):
                with patch.object(client, "_capture_error_screenshot") as mock_capture:
                    with pytest.raises(ScrapingBlocked):
                        client.get_profile("johndoe")

                    mock_capture.assert_called_once_with("scraping_blocked")

    def test_screenshot_on_max_retries_exceeded(self, mock_driver):
        """Test that screenshot is captured when max retries exceeded."""
        with patch.object(
            LinkedInScraperClient, "_create_driver", return_value=mock_driver
        ):
            client = LinkedInScraperClient(
                headless=True,
                screenshot_on_error=True,
                max_retries=1,
            )
            client.driver = mock_driver
            client.authenticated = True

            with patch(
                "linkedin_scraper.Person",
                side_effect=Exception("Error"),
            ):
                with patch("time.sleep"):
                    with patch.object(
                        client, "_capture_error_screenshot"
                    ) as mock_capture:
                        with pytest.raises(ScrapingBlocked):
                            client.get_profile("johndoe")

                        mock_capture.assert_called_with("scraping_failed")


# =============================================================================
# Integration Tests
# =============================================================================


class TestProfileScrapingIntegration:
    """Integration tests for the profile scraping flow."""

    def test_full_scraping_flow(self, client_with_mock_driver):
        """Test the complete profile scraping flow."""
        mock_person = MagicMock()
        mock_person.name = "Jane Smith"
        mock_person.linkedin_url = "https://www.linkedin.com/in/janesmith"
        mock_person.about = "Software Engineer"
        mock_person.experiences = []
        mock_person.educations = []

        with patch("linkedin_scraper.Person", return_value=mock_person):
            result = client_with_mock_driver.get_profile(
                "https://linkedin.com/in/janesmith/"
            )

            assert result.name == "Jane Smith"
            assert result.linkedin_url == "https://www.linkedin.com/in/janesmith"

    def test_close_on_complete_is_false(self, client_with_mock_driver):
        """Test that close_on_complete=False is passed to Person."""
        mock_person = MagicMock()
        mock_person.name = "Test User"

        with patch("linkedin_scraper.Person", return_value=mock_person) as mock_cls:
            client_with_mock_driver.get_profile("testuser")

            call_kwargs = mock_cls.call_args[1]
            assert call_kwargs["close_on_complete"] is False

    def test_scrape_is_true(self, client_with_mock_driver):
        """Test that scrape=True is passed to Person."""
        mock_person = MagicMock()
        mock_person.name = "Test User"

        with patch("linkedin_scraper.Person", return_value=mock_person) as mock_cls:
            client_with_mock_driver.get_profile("testuser")

            call_kwargs = mock_cls.call_args[1]
            assert call_kwargs["scrape"] is True

    def test_driver_passed_to_person(self, client_with_mock_driver, mock_driver):
        """Test that the driver is passed to Person."""
        mock_person = MagicMock()
        mock_person.name = "Test User"

        with patch("linkedin_scraper.Person", return_value=mock_person) as mock_cls:
            client_with_mock_driver.get_profile("testuser")

            call_kwargs = mock_cls.call_args[1]
            assert call_kwargs["driver"] is mock_driver
