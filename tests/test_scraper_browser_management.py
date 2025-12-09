"""Comprehensive tests for LinkedIn scraper browser management.

Tests driver creation, Chrome options configuration, context managers,
screenshot functionality, and error handling for browser operations.

Validates Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 5.5
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, Mock, patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from selenium.common.exceptions import WebDriverException

from linkedin_importer.scraper_client import LinkedInScraperClient
from linkedin_importer.scraper_errors import BrowserError

if TYPE_CHECKING:
    from selenium.webdriver.chrome.options import Options as ChromeOptions


class TestLinkedInScraperClientInitialization:
    """Test client initialization and configuration."""

    def test_default_initialization(self):
        """Client should initialize with sensible defaults."""
        client = LinkedInScraperClient()

        assert client.headless is True
        assert client.chromedriver_path is None
        assert client.page_load_timeout == 30
        assert client.action_delay == 1.0
        assert client.scroll_delay == 0.5
        assert client.user_agent is None
        assert client.screenshot_on_error is False
        assert client.screenshot_dir == "."
        assert client.driver is None
        assert client.authenticated is False

    def test_custom_initialization(self):
        """Client should accept custom configuration."""
        client = LinkedInScraperClient(
            headless=False,
            chromedriver_path="/custom/path/chromedriver",
            page_load_timeout=60,
            action_delay=2.0,
            scroll_delay=1.0,
            user_agent="Custom User Agent",
            screenshot_on_error=True,
            screenshot_dir="/tmp/screenshots",
        )

        assert client.headless is False
        assert client.chromedriver_path == "/custom/path/chromedriver"
        assert client.page_load_timeout == 60
        assert client.action_delay == 2.0
        assert client.scroll_delay == 1.0
        assert client.user_agent == "Custom User Agent"
        assert client.screenshot_on_error is True
        assert client.screenshot_dir == "/tmp/screenshots"

    @given(
        timeout=st.integers(min_value=1, max_value=300),
        action_delay=st.floats(min_value=0.1, max_value=10.0),
        scroll_delay=st.floats(min_value=0.1, max_value=5.0),
    )
    @settings(max_examples=20)
    def test_numeric_config_preserved(
        self, timeout: int, action_delay: float, scroll_delay: float
    ):
        """Property: Numeric configuration values are preserved."""
        client = LinkedInScraperClient(
            page_load_timeout=timeout,
            action_delay=action_delay,
            scroll_delay=scroll_delay,
        )

        assert client.page_load_timeout == timeout
        assert client.action_delay == action_delay
        assert client.scroll_delay == scroll_delay


class TestChromeOptionsConfiguration:
    """Test Chrome options building with anti-detection measures."""

    def test_build_chrome_options_headless(self):
        """Headless mode should add correct arguments (Requirement 3.2)."""
        client = LinkedInScraperClient(headless=True)
        options = client._build_chrome_options()

        arguments = options.arguments
        assert "--headless=new" in arguments

    def test_build_chrome_options_non_headless(self):
        """Non-headless mode should not add headless argument (Requirement 3.3)."""
        client = LinkedInScraperClient(headless=False)
        options = client._build_chrome_options()

        arguments = options.arguments
        assert "--headless=new" not in arguments
        assert "--headless" not in arguments

    def test_anti_detection_flags_present(self):
        """Anti-detection flags should be present in options."""
        client = LinkedInScraperClient()
        options = client._build_chrome_options()

        arguments = options.arguments
        # Check for key anti-detection arguments
        assert "--disable-blink-features=AutomationControlled" in arguments
        assert "--disable-infobars" in arguments
        assert "--no-sandbox" in arguments
        assert "--disable-dev-shm-usage" in arguments
        assert "--window-size=1920,1080" in arguments

    def test_experimental_options_set(self):
        """Experimental options for anti-detection should be set."""
        client = LinkedInScraperClient()
        options = client._build_chrome_options()

        experimental = options.experimental_options
        assert "excludeSwitches" in experimental
        assert "enable-automation" in experimental["excludeSwitches"]
        assert experimental.get("useAutomationExtension") is False

    def test_custom_user_agent_applied(self):
        """Custom user agent should be added to options."""
        custom_ua = "Mozilla/5.0 Custom Agent"
        client = LinkedInScraperClient(user_agent=custom_ua)
        options = client._build_chrome_options()

        arguments = options.arguments
        assert f"--user-agent={custom_ua}" in arguments

    def test_no_user_agent_when_none(self):
        """No user agent argument when user_agent is None."""
        client = LinkedInScraperClient(user_agent=None)
        options = client._build_chrome_options()

        arguments = options.arguments
        user_agent_args = [arg for arg in arguments if "--user-agent" in arg]
        assert len(user_agent_args) == 0


class TestChromedriverService:
    """Test ChromeDriver service configuration and auto-download."""

    def test_custom_chromedriver_path_not_found(self):
        """Should raise BrowserError if custom path doesn't exist (Requirement 3.5)."""
        client = LinkedInScraperClient(chromedriver_path="/nonexistent/chromedriver")

        with pytest.raises(BrowserError) as exc_info:
            client._get_chromedriver_service()

        assert "not found" in str(exc_info.value).lower()
        assert "chromedriver_path" in exc_info.value.details

    def test_custom_chromedriver_path_exists(self):
        """Should use custom path when it exists."""
        with tempfile.NamedTemporaryFile(delete=False, suffix="_chromedriver") as f:
            temp_path = f.name

        try:
            client = LinkedInScraperClient(chromedriver_path=temp_path)
            service = client._get_chromedriver_service()
            # Verify service was created (path would be set)
            assert service is not None
        finally:
            os.unlink(temp_path)

    @patch("linkedin_importer.scraper_client.WEBDRIVER_MANAGER_AVAILABLE", False)
    def test_webdriver_manager_not_available(self):
        """Should raise BrowserError if webdriver-manager not installed."""
        client = LinkedInScraperClient(chromedriver_path=None)

        with pytest.raises(BrowserError) as exc_info:
            client._get_chromedriver_service()

        assert "webdriver-manager" in str(exc_info.value).lower()
        assert "suggestion" in exc_info.value.details

    @patch("linkedin_importer.scraper_client.ChromeDriverManager")
    def test_auto_download_success(self, mock_manager_class):
        """Should auto-download chromedriver when no path specified (Requirement 3.1)."""
        mock_manager = Mock()
        mock_manager.install.return_value = "/tmp/chromedriver"
        mock_manager_class.return_value = mock_manager

        client = LinkedInScraperClient(chromedriver_path=None)

        with patch(
            "linkedin_importer.scraper_client.WEBDRIVER_MANAGER_AVAILABLE", True
        ):
            service = client._get_chromedriver_service()

        mock_manager.install.assert_called_once()
        assert service is not None

    @patch("linkedin_importer.scraper_client.ChromeDriverManager")
    def test_auto_download_failure(self, mock_manager_class):
        """Should raise BrowserError on download failure."""
        mock_manager = Mock()
        mock_manager.install.side_effect = Exception("Network error")
        mock_manager_class.return_value = mock_manager

        client = LinkedInScraperClient(chromedriver_path=None)

        with patch(
            "linkedin_importer.scraper_client.WEBDRIVER_MANAGER_AVAILABLE", True
        ):
            with pytest.raises(BrowserError) as exc_info:
                client._get_chromedriver_service()

        assert "download" in str(exc_info.value).lower()
        assert "suggestion" in exc_info.value.details


class TestDriverCreation:
    """Test WebDriver creation and initialization."""

    @patch.object(LinkedInScraperClient, "_get_chromedriver_service")
    @patch("linkedin_importer.scraper_client.webdriver.Chrome")
    def test_create_driver_success(self, mock_chrome, mock_service):
        """Should create driver with correct options (Requirement 3.1)."""
        mock_driver = MagicMock()
        mock_driver.capabilities = {
            "browserVersion": "120.0.0",
            "chrome": {"chromedriverVersion": "120.0.0"},
        }
        mock_chrome.return_value = mock_driver
        mock_service.return_value = Mock()

        client = LinkedInScraperClient(headless=True, page_load_timeout=45)
        driver = client._create_driver()

        assert driver is mock_driver
        mock_driver.set_page_load_timeout.assert_called_once_with(45)
        mock_driver.execute_cdp_cmd.assert_called_once()

    @patch.object(LinkedInScraperClient, "_get_chromedriver_service")
    @patch("linkedin_importer.scraper_client.webdriver.Chrome")
    def test_create_driver_stores_version_info(self, mock_chrome, mock_service):
        """Should store browser and driver version info."""
        mock_driver = MagicMock()
        mock_driver.capabilities = {
            "browserVersion": "121.0.6167.85",
            "chrome": {"chromedriverVersion": "121.0.6167.85"},
        }
        mock_chrome.return_value = mock_driver
        mock_service.return_value = Mock()

        client = LinkedInScraperClient()
        client._create_driver()

        assert client._browser_version == "121.0.6167.85"
        assert client._driver_version == "121.0.6167.85"

    @patch.object(LinkedInScraperClient, "_get_chromedriver_service")
    @patch("linkedin_importer.scraper_client.webdriver.Chrome")
    def test_create_driver_webdriver_exception(self, mock_chrome, mock_service):
        """Should raise BrowserError on WebDriverException."""
        mock_chrome.side_effect = WebDriverException("Chrome not found")
        mock_service.return_value = Mock()

        client = LinkedInScraperClient()

        with pytest.raises(BrowserError) as exc_info:
            client._create_driver()

        assert "Chrome" in str(exc_info.value)
        assert exc_info.value.details["headless"] is True

    @patch.object(LinkedInScraperClient, "_get_chromedriver_service")
    @patch("linkedin_importer.scraper_client.webdriver.Chrome")
    def test_create_driver_cdp_anti_detection(self, mock_chrome, mock_service):
        """Should execute CDP command for navigator.webdriver removal."""
        mock_driver = MagicMock()
        mock_driver.capabilities = {"browserVersion": "120.0.0", "chrome": {}}
        mock_chrome.return_value = mock_driver
        mock_service.return_value = Mock()

        client = LinkedInScraperClient()
        client._create_driver()

        # Verify CDP command was called
        mock_driver.execute_cdp_cmd.assert_called_once()
        call_args = mock_driver.execute_cdp_cmd.call_args
        assert call_args[0][0] == "Page.addScriptToEvaluateOnNewDocument"
        assert "navigator" in call_args[0][1]["source"]
        assert "webdriver" in call_args[0][1]["source"]


class TestEnsureDriver:
    """Test driver initialization lazy loading."""

    @patch.object(LinkedInScraperClient, "_create_driver")
    def test_ensure_driver_creates_when_none(self, mock_create):
        """Should create driver when none exists."""
        mock_driver = MagicMock()
        mock_create.return_value = mock_driver

        client = LinkedInScraperClient()
        assert client.driver is None

        result = client._ensure_driver()

        mock_create.assert_called_once()
        assert result is mock_driver
        assert client.driver is mock_driver

    @patch.object(LinkedInScraperClient, "_create_driver")
    def test_ensure_driver_reuses_existing(self, mock_create):
        """Should reuse existing driver."""
        existing_driver = MagicMock()

        client = LinkedInScraperClient()
        client.driver = existing_driver

        result = client._ensure_driver()

        mock_create.assert_not_called()
        assert result is existing_driver


class TestDriverClose:
    """Test driver cleanup and close functionality."""

    def test_close_when_driver_none(self):
        """Should safely handle close when driver is None (Requirement 3.4)."""
        client = LinkedInScraperClient()
        assert client.driver is None

        # Should not raise
        client.close()

        assert client.driver is None
        assert client.authenticated is False

    def test_close_calls_quit(self):
        """Should call driver.quit() on close (Requirement 3.4)."""
        mock_driver = MagicMock()

        client = LinkedInScraperClient()
        client.driver = mock_driver
        client.authenticated = True
        client._browser_version = "120.0.0"
        client._driver_version = "120.0.0"

        client.close()

        mock_driver.quit.assert_called_once()
        assert client.driver is None
        assert client.authenticated is False
        assert client._browser_version is None
        assert client._driver_version is None

    def test_close_handles_quit_exception(self):
        """Should handle exception during quit gracefully."""
        mock_driver = MagicMock()
        mock_driver.quit.side_effect = WebDriverException("Already closed")

        client = LinkedInScraperClient()
        client.driver = mock_driver
        client.authenticated = True

        # Should not raise
        client.close()

        assert client.driver is None
        assert client.authenticated is False

    def test_close_handles_generic_exception(self):
        """Should handle generic exception during quit gracefully."""
        mock_driver = MagicMock()
        mock_driver.quit.side_effect = RuntimeError("Unexpected error")

        client = LinkedInScraperClient()
        client.driver = mock_driver

        # Should not raise
        client.close()

        assert client.driver is None


class TestContextManagers:
    """Test synchronous and async context managers."""

    def test_sync_context_manager_entry(self):
        """Sync context manager should return client on entry."""
        client = LinkedInScraperClient()

        with client as ctx:
            assert ctx is client

    def test_sync_context_manager_calls_close(self):
        """Sync context manager should call close on exit (Requirement 3.4)."""
        client = LinkedInScraperClient()
        mock_driver = MagicMock()
        client.driver = mock_driver

        with client:
            pass

        mock_driver.quit.assert_called_once()
        assert client.driver is None

    def test_sync_context_manager_closes_on_exception(self):
        """Sync context manager should close on exception (Requirement 5.5)."""
        client = LinkedInScraperClient()
        mock_driver = MagicMock()
        client.driver = mock_driver

        with pytest.raises(ValueError):
            with client:
                raise ValueError("Test error")

        mock_driver.quit.assert_called_once()
        assert client.driver is None

    @pytest.mark.asyncio
    async def test_async_context_manager_entry(self):
        """Async context manager should return client on entry."""
        client = LinkedInScraperClient()

        async with client as ctx:
            assert ctx is client

    @pytest.mark.asyncio
    async def test_async_context_manager_calls_close(self):
        """Async context manager should call close on exit (Requirement 3.4)."""
        client = LinkedInScraperClient()
        mock_driver = MagicMock()
        client.driver = mock_driver

        async with client:
            pass

        mock_driver.quit.assert_called_once()
        assert client.driver is None

    @pytest.mark.asyncio
    async def test_async_context_manager_closes_on_exception(self):
        """Async context manager should close on exception (Requirement 5.5)."""
        client = LinkedInScraperClient()
        mock_driver = MagicMock()
        client.driver = mock_driver

        with pytest.raises(ValueError):
            async with client:
                raise ValueError("Test error")

        mock_driver.quit.assert_called_once()
        assert client.driver is None


class TestScreenshotFunctionality:
    """Test screenshot capture functionality."""

    def test_take_screenshot_no_driver(self):
        """Should return None if driver not initialized."""
        client = LinkedInScraperClient()
        assert client.driver is None

        result = client.take_screenshot("test")

        assert result is None

    def test_take_screenshot_success(self):
        """Should save screenshot and return path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_driver = MagicMock()

            client = LinkedInScraperClient(screenshot_dir=tmpdir)
            client.driver = mock_driver

            result = client.take_screenshot("test_error")

            assert result is not None
            assert "test_error_" in result
            assert result.endswith(".png")
            mock_driver.save_screenshot.assert_called_once()

    def test_take_screenshot_creates_directory(self):
        """Should create screenshot directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_dir = Path(tmpdir) / "nested" / "screenshots"
            mock_driver = MagicMock()

            client = LinkedInScraperClient(screenshot_dir=str(nested_dir))
            client.driver = mock_driver

            result = client.take_screenshot("test")

            assert result is not None
            assert nested_dir.exists()

    def test_take_screenshot_handles_exception(self):
        """Should return None on exception."""
        mock_driver = MagicMock()
        mock_driver.save_screenshot.side_effect = Exception("Screenshot failed")

        client = LinkedInScraperClient(screenshot_dir="/tmp")
        client.driver = mock_driver

        result = client.take_screenshot("test")

        assert result is None

    def test_capture_error_screenshot_disabled(self):
        """Should return None when screenshot_on_error is False."""
        client = LinkedInScraperClient(screenshot_on_error=False)
        client.driver = MagicMock()

        result = client._capture_error_screenshot("test")

        assert result is None

    def test_capture_error_screenshot_enabled(self):
        """Should take screenshot when screenshot_on_error is True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_driver = MagicMock()

            client = LinkedInScraperClient(
                screenshot_on_error=True, screenshot_dir=tmpdir
            )
            client.driver = mock_driver

            result = client._capture_error_screenshot("auth_error")

            assert result is not None
            assert "auth_error_" in result


class TestDriverInfo:
    """Test driver info retrieval."""

    def test_get_driver_info_no_driver(self):
        """Should return info with None values when no driver."""
        client = LinkedInScraperClient(headless=True, page_load_timeout=30)

        info = client.get_driver_info()

        assert info["browser_version"] is None
        assert info["driver_version"] is None
        assert info["headless"] is True
        assert info["page_load_timeout"] == 30
        assert info["driver_active"] is False
        assert info["authenticated"] is False

    def test_get_driver_info_with_driver(self):
        """Should return complete info with driver."""
        mock_driver = MagicMock()

        client = LinkedInScraperClient(headless=False, page_load_timeout=60)
        client.driver = mock_driver
        client.authenticated = True
        client._browser_version = "121.0.0"
        client._driver_version = "121.0.0"

        info = client.get_driver_info()

        assert info["browser_version"] == "121.0.0"
        assert info["driver_version"] == "121.0.0"
        assert info["headless"] is False
        assert info["page_load_timeout"] == 60
        assert info["driver_active"] is True
        assert info["authenticated"] is True


class TestBrowserErrorDetails:
    """Test error details include helpful information."""

    def test_browser_error_includes_chromedriver_path(self):
        """BrowserError should include chromedriver path in details."""
        client = LinkedInScraperClient(chromedriver_path="/custom/path")

        with pytest.raises(BrowserError) as exc_info:
            client._get_chromedriver_service()

        assert "chromedriver_path" in exc_info.value.details
        assert exc_info.value.details["chromedriver_path"] == "/custom/path"

    @patch.object(LinkedInScraperClient, "_get_chromedriver_service")
    @patch("linkedin_importer.scraper_client.webdriver.Chrome")
    def test_browser_error_includes_suggestion(self, mock_chrome, mock_service):
        """BrowserError should include helpful suggestion."""
        mock_chrome.side_effect = WebDriverException("Version mismatch")
        mock_service.return_value = Mock()

        client = LinkedInScraperClient()

        with pytest.raises(BrowserError) as exc_info:
            client._create_driver()

        assert "suggestion" in exc_info.value.details


class TestPropertyBasedBrowserTests:
    """Property-based tests for browser configuration."""

    @given(headless=st.booleans())
    @settings(max_examples=10)
    def test_headless_option_matches_config(self, headless: bool):
        """Property: Headless option matches configuration."""
        client = LinkedInScraperClient(headless=headless)
        options = client._build_chrome_options()

        has_headless = "--headless=new" in options.arguments

        assert has_headless == headless

    @given(user_agent=st.text(min_size=1, max_size=200).filter(lambda x: x.strip()))
    @settings(max_examples=20)
    def test_user_agent_preserved(self, user_agent: str):
        """Property: User agent is preserved in options."""
        client = LinkedInScraperClient(user_agent=user_agent)
        options = client._build_chrome_options()

        expected_arg = f"--user-agent={user_agent}"
        assert expected_arg in options.arguments

    @given(screenshot_dir=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()))
    @settings(max_examples=10)
    def test_screenshot_dir_preserved(self, screenshot_dir: str):
        """Property: Screenshot directory is preserved."""
        client = LinkedInScraperClient(screenshot_dir=screenshot_dir)
        assert client.screenshot_dir == screenshot_dir
