"""Comprehensive tests for LinkedIn scraper browser management (v3 Playwright).

Tests Playwright runtime lifecycle, BrowserManager configuration,
context managers, and error handling for browser operations.

Validates Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 5.5
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st


class TestLinkedInScraperClientInitialization:
    """Test client initialization and configuration."""

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    def test_default_initialization(self, mock_runtime_class):
        """Client should initialize with sensible defaults."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient()

        assert client.headless is True
        assert client.user_agent is None
        assert client.page_load_timeout == 30
        assert client.action_delay == 1.0
        assert client.scroll_delay == 0.5
        assert client.screenshot_on_error is False
        assert client.screenshot_dir == "."
        assert client.authenticated is False
        assert client.max_retries == 3

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    def test_custom_initialization(self, mock_runtime_class):
        """Client should accept custom configuration."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(
            headless=False,
            chromedriver_path="/custom/path/chromedriver",  # Ignored but accepted
            page_load_timeout=60,
            action_delay=2.0,
            scroll_delay=1.0,
            user_agent="Custom User Agent",
            screenshot_on_error=True,
            screenshot_dir="/tmp/screenshots",
            max_retries=5,
        )

        assert client.headless is False
        assert client.page_load_timeout == 60
        assert client.action_delay == 2.0
        assert client.scroll_delay == 1.0
        assert client.user_agent == "Custom User Agent"
        assert client.screenshot_on_error is True
        assert client.screenshot_dir == "/tmp/screenshots"
        assert client.max_retries == 5

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    def test_headless_defaults_to_true(self, mock_runtime_class):
        """Headless should default to True when not specified."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient()

        assert client.headless is True

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    def test_headless_none_becomes_true(self, mock_runtime_class):
        """Headless=None should default to True."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=None)

        assert client.headless is True

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    def test_chromedriver_path_accepted_but_ignored(self, mock_runtime_class):
        """chromedriver_path should be accepted for backward compatibility but ignored."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime_class.return_value = mock_runtime

        # Should not raise error
        client = LinkedInScraperClient(chromedriver_path="/some/path/chromedriver")

        # The client should be created successfully
        assert client is not None


class TestPlaywrightRuntimeLifecycle:
    """Test Playwright runtime initialization and cleanup."""

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    def test_runtime_started_on_init(self, mock_runtime_class):
        """Runtime should be started during client initialization."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime_class.return_value = mock_runtime

        LinkedInScraperClient(headless=True)

        mock_runtime.start.assert_called_once()

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    def test_runtime_receives_headless_config(self, mock_runtime_class):
        """Runtime should be configured with headless setting."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime_class.return_value = mock_runtime

        LinkedInScraperClient(headless=False)

        mock_runtime_class.assert_called_once_with(headless=False, user_agent=None)

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    def test_runtime_receives_user_agent(self, mock_runtime_class):
        """Runtime should be configured with user agent if provided."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime_class.return_value = mock_runtime

        LinkedInScraperClient(headless=True, user_agent="Custom Agent/1.0")

        mock_runtime_class.assert_called_once_with(
            headless=True, user_agent="Custom Agent/1.0"
        )

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    def test_runtime_stopped_on_close(self, mock_runtime_class):
        """Runtime should be stopped when client is closed."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True)
        client.close()

        mock_runtime.stop.assert_called_once()

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    def test_close_resets_authenticated(self, mock_runtime_class):
        """close() should reset authenticated flag."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True)
        client.authenticated = True

        client.close()

        assert client.authenticated is False

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    def test_close_is_idempotent(self, mock_runtime_class):
        """close() should be safe to call multiple times."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True)

        # Call close multiple times - should not raise
        client.close()
        client.close()
        client.close()

        # authenticated should remain False
        assert client.authenticated is False


class TestContextManager:
    """Test context manager functionality."""

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    def test_sync_context_manager_enter_returns_client(self, mock_runtime_class):
        """__enter__ should return the client instance."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True)
        result = client.__enter__()

        assert result is client

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    def test_sync_context_manager_exit_closes(self, mock_runtime_class):
        """__exit__ should close the client."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True)
        client.__exit__(None, None, None)

        mock_runtime.stop.assert_called()

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    def test_with_statement_usage(self, mock_runtime_class):
        """Client should work with 'with' statement."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime_class.return_value = mock_runtime

        with LinkedInScraperClient(headless=True) as client:
            assert client is not None
            assert isinstance(client, LinkedInScraperClient)

        mock_runtime.stop.assert_called()

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    @pytest.mark.asyncio
    async def test_async_context_manager_enter_returns_client(self, mock_runtime_class):
        """__aenter__ should return the client instance."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True)
        result = await client.__aenter__()

        assert result is client

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    @pytest.mark.asyncio
    async def test_async_context_manager_exit_closes(self, mock_runtime_class):
        """__aexit__ should close the client."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True)
        await client.__aexit__(None, None, None)

        mock_runtime.stop.assert_called()


class TestDriverInfo:
    """Test driver info functionality."""

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    def test_get_driver_info_returns_dict(self, mock_runtime_class):
        """get_driver_info should return a dictionary."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True)
        info = client.get_driver_info()

        assert isinstance(info, dict)

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    def test_get_driver_info_contains_chrome_version(self, mock_runtime_class):
        """get_driver_info should contain chrome_version."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True)
        info = client.get_driver_info()

        assert "chrome_version" in info
        assert info["chrome_version"] == "playwright-chromium"

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    def test_get_driver_info_contains_driver_version(self, mock_runtime_class):
        """get_driver_info should contain driver_version."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True)
        info = client.get_driver_info()

        assert "driver_version" in info
        assert info["driver_version"] == "playwright"


class TestPlaywrightRuntimeInternal:
    """Test _PlaywrightRuntime class directly."""

    def test_runtime_creates_event_loop(self):
        """Runtime should create its own event loop."""
        from linkedin_importer.scraper_client import _PlaywrightRuntime

        runtime = _PlaywrightRuntime(headless=True)

        assert runtime._loop is not None
        assert runtime._thread is not None

    def test_runtime_stores_config(self):
        """Runtime should store headless and user_agent config."""
        from linkedin_importer.scraper_client import _PlaywrightRuntime

        runtime = _PlaywrightRuntime(headless=False, user_agent="Test Agent")

        assert runtime.headless is False
        assert runtime.user_agent == "Test Agent"

    def test_runtime_page_initially_none(self):
        """Runtime page should be None before start."""
        from linkedin_importer.scraper_client import _PlaywrightRuntime

        runtime = _PlaywrightRuntime(headless=True)

        assert runtime._page is None


class TestPropertyBasedConfiguration:
    """Property-based tests for configuration."""

    @given(headless=st.booleans())
    @settings(
        max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    def test_headless_preserved(self, mock_runtime_class, headless):
        """Headless setting should be preserved."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=headless)

        assert client.headless == headless

    @given(timeout=st.integers(min_value=5, max_value=120))
    @settings(
        max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    def test_timeout_preserved(self, mock_runtime_class, timeout):
        """Page load timeout should be preserved."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True, page_load_timeout=timeout)

        assert client.page_load_timeout == timeout

    @given(user_agent=st.text(min_size=1, max_size=200))
    @settings(
        max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    def test_user_agent_preserved(self, mock_runtime_class, user_agent):
        """User agent should be preserved."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True, user_agent=user_agent)

        assert client.user_agent == user_agent

    @given(max_retries=st.integers(min_value=1, max_value=10))
    @settings(
        max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    def test_max_retries_preserved(self, mock_runtime_class, max_retries):
        """Max retries should be preserved."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True, max_retries=max_retries)

        assert client.max_retries == max_retries

    @given(action_delay=st.floats(min_value=0.5, max_value=10.0))
    @settings(
        max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    def test_action_delay_preserved(self, mock_runtime_class, action_delay):
        """Action delay should be preserved."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True, action_delay=action_delay)

        assert client.action_delay == action_delay

    @given(scroll_delay=st.floats(min_value=0.1, max_value=5.0))
    @settings(
        max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    def test_scroll_delay_preserved(self, mock_runtime_class, scroll_delay):
        """Scroll delay should be preserved."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True, scroll_delay=scroll_delay)

        assert client.scroll_delay == scroll_delay


class TestAuthenticatedState:
    """Test authenticated state management."""

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    def test_initially_not_authenticated(self, mock_runtime_class):
        """Client should not be authenticated initially."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True)

        assert client.authenticated is False

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    @patch("linkedin_importer.scraper_client.login_with_cookie")
    def test_authenticated_after_cookie_login(
        self, mock_login_with_cookie, mock_runtime_class
    ):
        """Client should be authenticated after successful cookie login."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime.run = MagicMock(return_value=None)
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True)
        client.authenticate(cookie="test_cookie")

        assert client.authenticated is True

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    @patch("linkedin_importer.scraper_client.login_with_credentials")
    def test_authenticated_after_credentials_login(
        self, mock_login_with_credentials, mock_runtime_class
    ):
        """Client should be authenticated after successful credentials login."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime.run = MagicMock(return_value=None)
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True)
        client.authenticate(email="user@example.com", password="password123")

        assert client.authenticated is True

    @patch("linkedin_importer.scraper_client._PlaywrightRuntime")
    @patch("linkedin_importer.scraper_client.login_with_cookie")
    def test_close_resets_authenticated_state(
        self, mock_login_with_cookie, mock_runtime_class
    ):
        """close() should reset authenticated state."""
        from linkedin_importer.scraper_client import LinkedInScraperClient

        mock_runtime = MagicMock()
        mock_runtime.run = MagicMock(return_value=None)
        mock_runtime_class.return_value = mock_runtime

        client = LinkedInScraperClient(headless=True)
        client.authenticate(cookie="test_cookie")

        assert client.authenticated is True

        client.close()

        assert client.authenticated is False
