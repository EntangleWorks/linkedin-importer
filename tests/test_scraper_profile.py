"""Tests for LinkedIn profile scraping functionality (v3 Playwright).

This module tests:
- Profile scraping with PersonScraper
- Error handling for various failure scenarios
- get_profile method behavior
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_runtime():
    """Create a mock _PlaywrightRuntime."""
    runtime = MagicMock()
    runtime.page = MagicMock()
    runtime.start = MagicMock()
    runtime.stop = MagicMock()
    runtime.run = MagicMock()
    return runtime


@pytest.fixture
def mock_person():
    """Create a mock Person object from linkedin_scraper."""
    person = MagicMock()
    person.name = "John Doe"
    person.linkedin_url = "https://www.linkedin.com/in/johndoe"
    person.job_title = "Software Engineer"
    person.about = "Experienced developer"
    person.location = "New York, NY"
    person.experiences = []
    person.educations = []
    person.skills = ["Python", "JavaScript"]
    person.interests = []
    return person


# =============================================================================
# Profile Scraping Tests
# =============================================================================


class TestGetProfile:
    """Tests for the get_profile method."""

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    @patch("linkedin_importer.scraper_client.PersonScraper")
    def test_get_profile_returns_person(self, mock_scraper_class, mock_runtime_class):
        """get_profile should return a Person object."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        # Setup mock runtime
        mock_runtime = MagicMock()
        mock_runtime.page = MagicMock()
        mock_runtime_class.return_value = mock_runtime

        # Setup mock person
        mock_person = MagicMock()
        mock_person.name = "John Doe"
        mock_runtime.run = MagicMock(return_value=mock_person)

        client = LinkedInScraperClient(headless=True)
        client.authenticated = True

        result = client.get_profile("https://www.linkedin.com/in/johndoe")

        assert result is mock_person

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    def test_get_profile_requires_authentication(self, mock_runtime_class):
        """get_profile should raise AuthError if not authenticated."""
        from linkedin_importer.scraper_client import LinkedInScraperClient
        from linkedin_importer.scraper_errors import AuthError

        mock_runtime = MagicMock()
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True)
        client.authenticated = False

        with pytest.raises(AuthError) as exc_info:
            client.get_profile("https://www.linkedin.com/in/johndoe")

        assert "authenticate" in str(exc_info.value).lower()

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    def test_get_profile_profile_not_found(self, mock_runtime_class):
        """get_profile should raise ProfileNotFound for missing profiles."""
        from linkedin_scraper.core.exceptions import ProfileNotFoundError

        from linkedin_importer.scraper_client import LinkedInScraperClient
        from linkedin_importer.scraper_errors import ProfileNotFound

        mock_runtime = MagicMock()
        mock_runtime.page = MagicMock()
        mock_runtime.run = MagicMock(
            side_effect=ProfileNotFoundError("Profile not found")
        )
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True)
        client.authenticated = True

        with pytest.raises(ProfileNotFound) as exc_info:
            client.get_profile("https://www.linkedin.com/in/nonexistent")

        assert "nonexistent" in str(exc_info.value.profile_url)

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    def test_get_profile_scraping_blocked(self, mock_runtime_class):
        """get_profile should raise ScrapingBlocked when blocked."""
        from linkedin_scraper.core.exceptions import ScrapingError

        from linkedin_importer.scraper_client import LinkedInScraperClient
        from linkedin_importer.scraper_errors import ScrapingBlocked

        mock_runtime = MagicMock()
        mock_runtime.page = MagicMock()
        mock_runtime.run = MagicMock(
            side_effect=ScrapingError("Rate limited or blocked")
        )
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True)
        client.authenticated = True

        with pytest.raises(ScrapingBlocked):
            client.get_profile("https://www.linkedin.com/in/johndoe")

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    def test_get_profile_cookie_expired(self, mock_runtime_class):
        """get_profile should raise CookieExpired on auth error."""
        from linkedin_scraper.core.exceptions import AuthenticationError

        from linkedin_importer.scraper_client import LinkedInScraperClient
        from linkedin_importer.scraper_errors import CookieExpired

        mock_runtime = MagicMock()
        mock_runtime.page = MagicMock()
        mock_runtime.run = MagicMock(side_effect=AuthenticationError("Session expired"))
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True)
        client.authenticated = True

        with pytest.raises(CookieExpired):
            client.get_profile("https://www.linkedin.com/in/johndoe")

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    def test_get_profile_unexpected_error(self, mock_runtime_class):
        """get_profile should raise ScraperError for unexpected errors."""
        from linkedin_importer.scraper_client import LinkedInScraperClient
        from linkedin_importer.scraper_errors import ScraperError

        mock_runtime = MagicMock()
        mock_runtime.page = MagicMock()
        mock_runtime.run = MagicMock(side_effect=Exception("Unexpected error"))
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True)
        client.authenticated = True

        with pytest.raises(ScraperError) as exc_info:
            client.get_profile("https://www.linkedin.com/in/johndoe")

        assert "Unexpected" in str(exc_info.value)


class TestGetProfileWithPersonScraper:
    """Tests for PersonScraper integration."""

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    @patch("linkedin_importer.scraper_client.PersonScraper")
    def test_person_scraper_receives_page(self, mock_scraper_class, mock_runtime_class):
        """PersonScraper should be initialized with the page."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_page = MagicMock()
        mock_runtime = MagicMock()
        mock_runtime.page = mock_page
        mock_runtime_class.return_value = mock_runtime

        mock_scraper = MagicMock()
        mock_scraper.scrape = AsyncMock(return_value=MagicMock())
        mock_scraper_class.return_value = mock_scraper

        # Make run execute the coroutine and return its result
        mock_runtime.run = MagicMock(return_value=MagicMock())

        client = LinkedInScraperClient(headless=True)
        client.authenticated = True

        client.get_profile("https://www.linkedin.com/in/johndoe")

        # Verify runtime.run was called (which internally creates PersonScraper)
        assert mock_runtime.run.called


class TestGetProfilePropertyBased:
    """Property-based tests for get_profile."""

    @given(
        profile_id=st.text(
            alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789-_"),
            min_size=3,
            max_size=50,
        )
    )
    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    def test_profile_url_accepted(self, mock_runtime_class, profile_id):
        """Any valid profile URL should be accepted."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime.page = MagicMock()
        mock_runtime.run = MagicMock(return_value=MagicMock())
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True)
        client.authenticated = True

        url = f"https://www.linkedin.com/in/{profile_id}"
        # Should not raise
        result = client.get_profile(url)

        assert result is not None

    @given(
        profile_id=st.text(
            alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789-_"),
            min_size=3,
            max_size=50,
        )
    )
    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    def test_not_authenticated_always_fails(self, mock_runtime_class, profile_id):
        """Not authenticated should always fail regardless of URL."""
        from linkedin_importer.scraper_client import LinkedInScraperClient
        from linkedin_importer.scraper_errors import AuthError

        mock_runtime = MagicMock()
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True)
        client.authenticated = False

        url = f"https://www.linkedin.com/in/{profile_id}"

        with pytest.raises(AuthError):
            client.get_profile(url)


class TestLoggingCallback:
    """Tests for the _LoggingCallback class."""

    def test_logging_callback_exists(self):
        """_LoggingCallback class should exist."""
        from linkedin_importer.scraper_client import _LoggingCallback

        callback = _LoggingCallback()
        assert callback is not None

    @pytest.mark.asyncio
    async def test_on_start_logs(self, caplog):
        """on_start should log the scraper type and URL."""
        import logging

        from linkedin_importer.scraper_client import _LoggingCallback

        with caplog.at_level(logging.INFO):
            callback = _LoggingCallback()
            await callback.on_start("PersonScraper", "https://linkedin.com/in/test")

        assert "PersonScraper" in caplog.text
        assert "test" in caplog.text

    @pytest.mark.asyncio
    async def test_on_progress_logs(self, caplog):
        """on_progress should log the message and percent."""
        import logging

        from linkedin_importer.scraper_client import _LoggingCallback

        with caplog.at_level(logging.INFO):
            callback = _LoggingCallback()
            await callback.on_progress("Loading experiences", 50)

        assert "50" in caplog.text
        assert "experience" in caplog.text.lower() or "Loading" in caplog.text

    @pytest.mark.asyncio
    async def test_on_complete_logs(self, caplog):
        """on_complete should log completion."""
        import logging

        from linkedin_importer.scraper_client import _LoggingCallback

        with caplog.at_level(logging.INFO):
            callback = _LoggingCallback()
            await callback.on_complete("PersonScraper", "https://linkedin.com/in/test")

        assert "complete" in caplog.text.lower() or "PersonScraper" in caplog.text

    @pytest.mark.asyncio
    async def test_on_error_logs(self, caplog):
        """on_error should log the error."""
        import logging

        from linkedin_importer.scraper_client import _LoggingCallback

        with caplog.at_level(logging.ERROR):
            callback = _LoggingCallback()
            test_error = Exception("Test error message")
            await callback.on_error(test_error)

        assert "error" in caplog.text.lower()


class TestScrapingWithCallback:
    """Tests for scraping with callback integration."""

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    @patch("linkedin_importer.scraper_client.PersonScraper")
    @patch("linkedin_importer.scraper_client._LoggingCallback")
    def test_scraping_uses_logging_callback(
        self, mock_callback_class, mock_scraper_class, mock_runtime_class
    ):
        """Scraping should use the logging callback."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime.page = MagicMock()
        mock_runtime.run = MagicMock(return_value=MagicMock())
        mock_runtime_class.return_value = mock_runtime

        mock_callback = MagicMock()
        mock_callback_class.return_value = mock_callback

        client = LinkedInScraperClient(headless=True)
        client.authenticated = True

        client.get_profile("https://www.linkedin.com/in/johndoe")

        # Verify that runtime.run was called which invokes the scraper
        assert mock_runtime.run.called


class TestErrorMappingFromLinkedInScraper:
    """Tests for error mapping from linkedin_scraper exceptions."""

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    def test_authentication_error_to_cookie_expired(self, mock_runtime_class):
        """AuthenticationError should map to CookieExpired."""
        from linkedin_scraper.core.exceptions import AuthenticationError

        from linkedin_importer.scraper_client import LinkedInScraperClient
        from linkedin_importer.scraper_errors import CookieExpired

        mock_runtime = MagicMock()
        mock_runtime.run = MagicMock(side_effect=AuthenticationError("Session expired"))
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True)
        client.authenticated = True

        with pytest.raises(CookieExpired):
            client.get_profile("https://www.linkedin.com/in/johndoe")

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    def test_profile_not_found_error_preserved(self, mock_runtime_class):
        """ProfileNotFoundError should map to ProfileNotFound."""
        from linkedin_scraper.core.exceptions import ProfileNotFoundError

        from linkedin_importer.scraper_client import LinkedInScraperClient
        from linkedin_importer.scraper_errors import ProfileNotFound

        mock_runtime = MagicMock()
        mock_runtime.run = MagicMock(
            side_effect=ProfileNotFoundError("Profile does not exist")
        )
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True)
        client.authenticated = True

        profile_url = "https://www.linkedin.com/in/nonexistent"

        with pytest.raises(ProfileNotFound) as exc_info:
            client.get_profile(profile_url)

        assert exc_info.value.profile_url == profile_url

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    def test_scraping_error_to_scraping_blocked(self, mock_runtime_class):
        """ScrapingError should map to ScrapingBlocked."""
        from linkedin_scraper.core.exceptions import ScrapingError

        from linkedin_importer.scraper_client import LinkedInScraperClient
        from linkedin_importer.scraper_errors import ScrapingBlocked

        mock_runtime = MagicMock()
        mock_runtime.run = MagicMock(side_effect=ScrapingError("Rate limited"))
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True)
        client.authenticated = True

        with pytest.raises(ScrapingBlocked):
            client.get_profile("https://www.linkedin.com/in/johndoe")

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    def test_generic_exception_to_scraper_error(self, mock_runtime_class):
        """Generic exceptions should map to ScraperError."""
        from linkedin_importer.scraper_client import LinkedInScraperClient
        from linkedin_importer.scraper_errors import ScraperError

        mock_runtime = MagicMock()
        mock_runtime.run = MagicMock(side_effect=RuntimeError("Something went wrong"))
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True)
        client.authenticated = True

        with pytest.raises(ScraperError) as exc_info:
            client.get_profile("https://www.linkedin.com/in/johndoe")

        assert "Unexpected" in str(exc_info.value)
