"""BDD-style tests for the map module.

Each test follows the Given-When-Then pattern with a scenario
docstring and Arrange/Act/Assert comments.
"""
# ruff: noqa: SLF001

import asyncio
import contextlib
import io
from collections.abc import Callable, Generator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from shapely import Point

from mapyta import Map
from mapyta.export import (
    _detect_chrome,
    _detect_edge,
    _select_backend,
    capture_screenshot,
    check_selenium,
)

# ===================================================================
# Scenarios for creating and configuring a Map.
# ===================================================================


class TestExport:
    """Scenarios for export methods: HTML, PNG, SVG, BytesIO, and async variants."""

    def test_export_to_html_file(self, tmp_path: Path) -> None:
        """
        Scenario: Export a map as a standalone HTML file.

        Given: A map with one location
        When: to_html is called with a file path
        Then: The file exists and contains Leaflet references
        """
        # Arrange - Given
        m = Map(title="Export Test")
        m.add_point(Point(4.9, 52.37), marker="📍")

        # Act - When
        out = m.to_html(tmp_path / "test.html")

        # Assert - Then
        assert out.exists(), "HTML file should be created"
        content = out.read_text()
        assert "leaflet" in content.lower(), "HTML should reference Leaflet"

    def test_export_to_html_with_open(self, tmp_path: Path) -> None:
        """
        Scenario: Export HTML and open in browser.

        Given: A map with one location
        When: to_html is called with open_in_browser=True
        Then: The file is created and webbrowser.open is called with the file URI
        """
        m = Map()
        m.add_point(Point(4.9, 52.37))

        with patch("webbrowser.open") as mock_open:
            out = m.to_html(tmp_path / "open_test.html", open_in_browser=True)

        assert out.exists()
        mock_open.assert_called_once_with(out.resolve().as_uri())

    def test_export_to_html_open_ignored_without_path(self) -> None:
        """
        Scenario: open_in_browser=True is ignored when path is None.

        Given: A map with one location
        When: to_html is called with path=None and open_in_browser=True
        Then: An HTML string is returned; webbrowser is never called
        """
        m = Map()
        m.add_point(Point(4.9, 52.37))

        with patch("webbrowser.open") as mock_open:
            result = m.to_html(path=None, open_in_browser=True)

        assert isinstance(result, str)
        mock_open.assert_not_called()

    def test_export_auto_fits_bounds(self, tmp_path: Path) -> None:
        """
        Scenario: A map without a center auto-fits to its geometries.

        Given: A map with no center and two distant points
        When: to_html is called
        Then: The file is created (fit_bounds was called internally)
        """
        # Arrange - Given
        m = Map()
        m.add_point(Point(4.9, 52.37))
        m.add_point(Point(5.5, 51.44))

        # Act - When
        out = m.to_html(tmp_path / "autofit.html")

        # Assert - Then
        assert out.exists(), "HTML should be created even without explicit center"

    def test_repr_html_for_jupyter(self) -> None:
        """
        Scenario: Map renders inline in a Jupyter notebook.

        Given: A map with a location
        When: _repr_html_ is called
        Then: A non-empty HTML string is returned
        """
        # Arrange - Given
        m = Map()
        m.add_point(Point(4.9, 52.37))

        # Act - When
        html = m._repr_html_()

        # Assert - Then
        assert isinstance(html, str), "Should return a string"
        assert len(html) > 100, "Should contain substantial HTML"

    def test_image_export_without_selenium_fails_gracefully(self) -> None:
        """
        Scenario: PNG export without Selenium gives a clear error.

        Given: A map with a location (Selenium may not be installed)
        When: to_image is called
        Then: An ImportError or RuntimeError is raised (not a crash)
        """
        # Arrange - Given
        m = Map()
        m.add_point(Point(4.9, 52.37))

        # Act & Assert - When/Then
        with contextlib.suppress(ImportError, RuntimeError):
            # Expected — clear error message
            m.to_image()

    def test_to_html_with_center_skips_fit_bounds(self, tmp_path: Path) -> None:
        """
        Scenario: A map with an explicit center does not auto-fit.

        Given: A map created with center=(52.37, 4.90)
        When: to_html is called
        Then: The file is created (fit_bounds is skipped)
        """
        # Arrange - Given
        m = Map(center=(52.37, 4.90))

        # Act - When
        out = m.to_html(tmp_path / "centered.html")

        # Assert - Then
        assert out.exists()

    def test_to_html_returns_string_when_path_is_none(self) -> None:
        """
        Scenario: Get the full HTML document as a string without writing to disk.

        Given: A map with a location
        When: to_html is called with path=None
        Then: A string containing the full HTML document is returned
        """
        # Arrange - Given
        m = Map(title="String Export")
        m.add_point(Point(4.9, 52.37), marker="📍")

        # Act - When
        result = m.to_html()

        # Assert - Then
        assert isinstance(result, str), "Should return a string when path is None"
        assert "leaflet" in result.lower(), "HTML should contain Leaflet"
        assert len(result) > 100, "Should be a full HTML document"

    def test_to_html_default_returns_string(self) -> None:
        """
        Scenario: Calling to_html() with no arguments returns a string.

        Given: An empty map
        When: to_html is called with no arguments
        Then: A non-empty HTML string is returned
        """
        # Arrange - Given
        m = Map()

        # Act - When
        result = m.to_html()

        # Assert - Then
        assert isinstance(result, str)

    def test_to_html_empty_map(self, tmp_path: Path) -> None:
        """
        Scenario: Export an empty map with no geometries.

        Given: A map with nothing added
        When: to_html is called
        Then: A valid HTML file is still created
        """
        # Arrange - Given
        m = Map()

        # Act - When
        out = m.to_html(tmp_path / "empty.html")

        # Assert - Then
        assert out.exists()
        assert out.stat().st_size > 0

    def test_get_html_returns_string(self) -> None:
        """
        Scenario: _get_html renders the map to an HTML string.

        Given: A map with a location
        When: _get_html is called
        Then: An HTML string is returned
        """
        # Arrange - Given
        m = Map()
        m.add_point(Point(4.9, 52.37))

        # Act - When
        html = m._get_html()

        # Assert - Then
        assert isinstance(html, str)
        assert "leaflet" in html.lower()

    def test_fit_bounds_with_no_bounds_does_nothing(self) -> None:
        """
        Scenario: Calling _fit_bounds on an empty map has no side effects.

        Given: A map with no geometries (empty bounds)
        When: _fit_bounds is called
        Then: No error is raised
        """
        # Arrange - Given
        m = Map()

        # Act - When — should not raise
        m._fit_bounds()

        # Assert - Then
        assert m._bounds == [], "Bounds should still be empty"

    def test_check_selenium_missing_selenium_raises_import_error(self) -> None:
        """
        Scenario: selenium is not installed.

        Given: selenium cannot be imported
        When: _check_selenium is called
        Then: An ImportError is raised with install instructions
        """
        with patch.dict("sys.modules", {"selenium": None, "selenium.webdriver": None}), pytest.raises(ImportError, match="selenium"):
            check_selenium()

    def test_check_selenium_no_browser_raises_runtime_error(self) -> None:
        """
        Scenario: selenium is installed but no supported browser is found.

        Given: selenium is importable, no Chrome/Chromium/Edge binary on PATH, non-Windows/non-macOS
        When: check_selenium is called
        Then: A RuntimeError mentions Chrome, Chromium, and Edge install paths
        """
        with (
            patch("shutil.which", return_value=None),
            patch("mapyta.export.sys.platform", "linux"),
            patch.dict("sys.modules", {"selenium": MagicMock(), "selenium.webdriver": MagicMock()}),
            pytest.raises(RuntimeError, match="No supported browser"),
        ):
            check_selenium()


class TestBackendSelection:
    """Scenarios for picking between Chrome and Edge."""

    @staticmethod
    def _which_factory(*available: str) -> Callable[[str], str | None]:
        """Build a shutil.which mock that returns paths only for ``available`` binaries."""

        def fake_which(name: str) -> str | None:
            return f"/usr/bin/{name}" if name in available else None

        return fake_which

    def test_prefers_chrome_when_both_present(self) -> None:
        """
        Scenario: With both Chrome and Edge installed, Chrome wins.

        Given: shutil.which returns paths for both google-chrome and microsoft-edge
        When: _select_backend is called
        Then: 'chrome' is returned (preserves historical default)
        """
        which_mock = self._which_factory("google-chrome", "microsoft-edge")
        with patch("shutil.which", side_effect=which_mock), patch("mapyta.export.sys.platform", "linux"):
            assert _select_backend() == "chrome"

    def test_picks_edge_when_only_edge(self) -> None:
        """
        Scenario: Edge is the only browser available.

        Given: shutil.which returns a path only for microsoft-edge
        When: _select_backend is called
        Then: 'edge' is returned
        """
        with patch("shutil.which", side_effect=self._which_factory("microsoft-edge")), patch("mapyta.export.sys.platform", "linux"):
            assert _select_backend() == "edge"

    def test_neither_browser_raises_with_install_hints(self) -> None:
        """
        Scenario: No Chromium browser is installed.

        Given: shutil.which returns None for every binary, non-Windows/non-macOS platform
        When: _select_backend is called
        Then: RuntimeError mentions Chrome and Edge with install URLs
        """
        with (
            patch("shutil.which", return_value=None),
            patch("mapyta.export.sys.platform", "linux"),
            pytest.raises(RuntimeError, match=r"(?s)Chrome.*Edge"),
        ):
            _select_backend()

    def test_detect_chrome_via_path(self) -> None:
        """Detection finds Chrome via shutil.which when binary is on PATH."""
        with patch("shutil.which", side_effect=self._which_factory("chromium")), patch("mapyta.export.sys.platform", "linux"):
            assert _detect_chrome() is True
        with patch("shutil.which", return_value=None), patch("mapyta.export.sys.platform", "linux"):
            assert _detect_chrome() is False

    def test_detect_edge_via_path(self) -> None:
        """Detection finds Edge via shutil.which when binary is on PATH."""
        with patch("shutil.which", side_effect=self._which_factory("msedge")), patch("mapyta.export.sys.platform", "linux"):
            assert _detect_edge() is True
        with patch("shutil.which", return_value=None), patch("mapyta.export.sys.platform", "linux"):
            assert _detect_edge() is False

    def test_detect_edge_via_windows_install_path(self) -> None:
        """On Windows, Edge is detected via its standard install path even when not on PATH.

        Why: Edge ships with every Windows install but is not on PATH by default,
        so PATH lookup alone misses it.
        """
        edge_install = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
        original_exists = Path.exists

        def fake_exists(self: Path) -> bool:
            return str(self) == edge_install or original_exists(self)

        with (
            patch("shutil.which", return_value=None),
            patch("mapyta.export.sys.platform", "win32"),
            patch.object(Path, "exists", fake_exists),
        ):
            assert _detect_edge() is True

    def test_detect_chrome_via_windows_install_path(self) -> None:
        """On Windows, Chrome is detected via its standard install path even when not on PATH."""
        chrome_install = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        original_exists = Path.exists

        def fake_exists(self: Path) -> bool:
            return str(self) == chrome_install or original_exists(self)

        with (
            patch("shutil.which", return_value=None),
            patch("mapyta.export.sys.platform", "win32"),
            patch.object(Path, "exists", fake_exists),
        ):
            assert _detect_chrome() is True

    def test_capture_screenshot_returns_png_bytes(self, tmp_path: Path) -> None:
        """
        Scenario: Capture a screenshot of an HTML file.

        Given: A valid HTML file and a mocked Chrome WebDriver
        When: _capture_screenshot is called
        Then: PNG bytes are returned and the driver is quit
        """
        # Arrange - Given
        html_file = tmp_path / "test.html"
        html_file.write_text("<html><body>Hello</body></html>")

        fake_png = b"\x89PNG_fake_image_bytes"

        mock_driver = MagicMock()
        mock_driver.get_screenshot_as_png.return_value = fake_png

        mock_options_instance = MagicMock()

        mock_selenium = MagicMock()
        mock_selenium.webdriver.Chrome.return_value = mock_driver
        mock_selenium.webdriver.chrome.options.Options.return_value = mock_options_instance

        # Act - When: patch the lazy imports inside _capture_screenshot
        with (
            patch("mapyta.export.check_selenium"),
            patch("mapyta.export._select_backend", return_value="chrome"),
            patch.dict(
                "sys.modules",
                {
                    "selenium": mock_selenium,
                    "selenium.webdriver": mock_selenium.webdriver,
                    "selenium.webdriver.chrome": mock_selenium.webdriver.chrome,
                    "selenium.webdriver.chrome.options": mock_selenium.webdriver.chrome.options,
                },
            ),
        ):
            result = capture_screenshot(str(html_file), 800, 600, 0.1)

        # Assert - Then
        assert result == fake_png, "Should return the PNG bytes from the driver"
        mock_driver.get_screenshot_as_png.assert_called_once()
        mock_driver.quit.assert_called_once()
        mock_driver.set_window_size.assert_called_once_with(800, 600)
        assert mock_options_instance.add_argument.call_count == 5

    def test_capture_screenshot_scale_2x(self, tmp_path: Path) -> None:
        """
        Scenario: Capture a high-DPI screenshot with scale=2.0.

        Given: A valid HTML file and a mocked Chrome WebDriver
        When: capture_screenshot is called with scale=2.0
        Then: --force-device-scale-factor=2.0 is added and window size stays at original dimensions
        """
        # Arrange - Given
        html_file = tmp_path / "test.html"
        html_file.write_text("<html><body>Hello</body></html>")

        fake_png = b"\x89PNG_fake_image_bytes"

        mock_driver = MagicMock()
        mock_driver.get_screenshot_as_png.return_value = fake_png

        mock_options_instance = MagicMock()

        mock_selenium = MagicMock()
        mock_selenium.webdriver.Chrome.return_value = mock_driver
        mock_selenium.webdriver.chrome.options.Options.return_value = mock_options_instance

        # Act - When
        with (
            patch("mapyta.export.check_selenium"),
            patch("mapyta.export._select_backend", return_value="chrome"),
            patch.dict(
                "sys.modules",
                {
                    "selenium": mock_selenium,
                    "selenium.webdriver": mock_selenium.webdriver,
                    "selenium.webdriver.chrome": mock_selenium.webdriver.chrome,
                    "selenium.webdriver.chrome.options": mock_selenium.webdriver.chrome.options,
                },
            ),
        ):
            result = capture_screenshot(str(html_file), 800, 600, 0.1, scale=2.0)

        # Assert - Then
        assert result == fake_png
        mock_driver.set_window_size.assert_called_once_with(800, 600)
        # 5 base args + 1 --force-device-scale-factor
        assert mock_options_instance.add_argument.call_count == 6
        scale_call = [c for c in mock_options_instance.add_argument.call_args_list if "force-device-scale-factor" in str(c)]
        assert len(scale_call) == 1
        assert "2.0" in str(scale_call[0])

    def test_capture_screenshot_uses_edge_when_selected(self, tmp_path: Path) -> None:
        """
        Scenario: With Edge selected as backend, webdriver.Edge is built with the same flags as Chrome.

        Given: _select_backend returns 'edge' and Edge WebDriver is mocked
        When: capture_screenshot is called
        Then: webdriver.Edge is invoked (not Chrome) with identical option flags
        """
        html_file = tmp_path / "test.html"
        html_file.write_text("<html><body>Hello</body></html>")

        fake_png = b"\x89PNG_edge_bytes"
        mock_driver = MagicMock()
        mock_driver.get_screenshot_as_png.return_value = fake_png
        mock_options_instance = MagicMock()

        mock_selenium = MagicMock()
        mock_selenium.webdriver.Edge.return_value = mock_driver
        mock_selenium.webdriver.edge.options.Options.return_value = mock_options_instance

        with (
            patch("mapyta.export.check_selenium"),
            patch("mapyta.export._select_backend", return_value="edge"),
            patch.dict(
                "sys.modules",
                {
                    "selenium": mock_selenium,
                    "selenium.webdriver": mock_selenium.webdriver,
                    "selenium.webdriver.edge": mock_selenium.webdriver.edge,
                    "selenium.webdriver.edge.options": mock_selenium.webdriver.edge.options,
                },
            ),
        ):
            result = capture_screenshot(str(html_file), 800, 600, 0.1, scale=2.0)

        assert result == fake_png
        mock_selenium.webdriver.Edge.assert_called_once()
        mock_selenium.webdriver.Chrome.assert_not_called()
        mock_driver.set_window_size.assert_called_once_with(800, 600)
        mock_driver.quit.assert_called_once()
        # 5 base args + 1 scale arg, same as Chrome
        assert mock_options_instance.add_argument.call_count == 6
        scale_call = [c for c in mock_options_instance.add_argument.call_args_list if "force-device-scale-factor" in str(c)]
        assert len(scale_call) == 1

    def test_capture_screenshot_invalid_scale_raises(self, tmp_path: Path) -> None:
        """
        Scenario: capture_screenshot raises ValueError for scale <= 0.

        Given: An HTML file
        When: capture_screenshot is called with scale=0 or negative
        Then: A ValueError is raised before Chrome is invoked
        """
        html_file = tmp_path / "test.html"
        html_file.write_text("<html><body>Hello</body></html>")
        with pytest.raises(ValueError, match="scale must be greater than 0"):
            capture_screenshot(str(html_file), scale=0)
        with pytest.raises(ValueError, match="scale must be greater than 0"):
            capture_screenshot(str(html_file), scale=-1.0)

    @pytest.fixture
    def map_with_point(self) -> Map:
        """A map with one location for export tests."""
        m = Map(title="Export")
        m.add_point(Point(4.9, 52.37), marker="📍")
        return m

    @pytest.fixture
    def mock_to_image(self) -> Generator[MagicMock | AsyncMock, Any, None]:
        """Patch to_image to return fake PNG bytes."""
        fake_png = b"\x89PNG\r\n\x1a\n_fake_image_data_1234567890"
        with patch.object(Map, "to_image", return_value=fake_png) as mock:
            mock.fake_png = fake_png
            yield mock

    def test_to_image_returns_bytes(self, map_with_point: Map) -> None:
        """
        Scenario: to_image with path=None returns raw PNG bytes.

        Given: A map with a location
        When: to_image is called with path=None
        Then: PNG bytes are returned

        """
        # Arrange - Given
        fake_png = b"\x89PNG_fake"

        # Act - When
        with patch("mapyta.map.capture_screenshot", return_value=fake_png):
            result = map_with_point.to_image(path=None)

        # Assert - Then
        assert result == fake_png

    def test_to_image_saves_to_file(self, map_with_point: Map, tmp_path: Path) -> None:
        """
        Scenario: to_image with a path saves PNG to disk.

        Given: A map with a location and an output path
        When: to_image is called with a file path
        Then: The file is written and the Path is returned

        """
        # Arrange - Given
        fake_png = b"\x89PNG_fake_data"
        out_path = tmp_path / "map.png"

        # Act - When
        with patch("mapyta.map.capture_screenshot", return_value=fake_png):
            result = map_with_point.to_image(path=out_path)

        # Assert - Then
        assert result == out_path
        assert out_path.exists()
        assert out_path.read_bytes() == fake_png

    def test_to_bytesio_returns_buffer(self, map_with_point: Map, mock_to_image: Generator[MagicMock | AsyncMock, Any, None]) -> None:
        """
        Scenario: to_bytesio returns an in-memory PNG buffer.

        Given: A map with a location
        When: to_bytesio is called
        Then: A BytesIO buffer at position 0 is returned

        """
        # Act - When
        result = map_with_point.to_bytesio(width=800, height=600, delay=0.1)

        # Assert - Then
        assert isinstance(result, io.BytesIO)
        assert result.tell() == 0, "Buffer should be at position 0"
        content = result.read()
        assert content == mock_to_image.fake_png  # ty: ignore[unresolved-attribute]

    def test_to_image_async(self, map_with_point: Map, mock_to_image: Generator[MagicMock | AsyncMock, Any, None]) -> None:
        """
        Scenario: Async PNG export delegates to to_image in an executor.

        Given: A map with a location
        When: to_image_async is awaited
        Then: PNG bytes are returned

        """
        # Act - When
        result = asyncio.run(map_with_point.to_image_async(path=None, width=800, height=600, delay=0.1))

        # Assert - Then
        assert result == mock_to_image.fake_png  # ty: ignore[unresolved-attribute]


# ===================================================================
# Scenarios for combining two maps with the + operator.
# ===================================================================


class TestHideControls:
    """Scenarios for clean image export with hidden controls."""

    def test_hide_controls_true_injects_css(self) -> None:
        """
        Scenario: hide_controls=True injects CSS to hide controls.

        Given: A Map with a location
        When: to_image is called with hide_controls=True
        Then: The screenshot function is called (CSS was injected)
        """
        m = Map()
        m.add_point(Point(4.9, 52.37))

        fake_png = b"\x89PNG_fake"
        with patch("mapyta.map.capture_screenshot", return_value=fake_png) as mock_cap:
            m.to_image(path=None, hide_controls=True)
            assert mock_cap.called

    def test_hide_controls_false_no_css(self) -> None:
        """
        Scenario: hide_controls=False does not inject CSS.

        Given: A Map with a location
        When: to_image is called with hide_controls=False
        Then: The temporary HTML does not contain hide CSS
        """
        m = Map()
        m.add_point(Point(4.9, 52.37))

        captured_html: dict[str, str] = {}

        def mock_screenshot(html_path: str, *_args: object, **_kwargs: object) -> bytes:
            captured_html["content"] = Path(html_path).read_text(encoding="utf-8")
            return b"\x89PNG_fake"

        with patch("mapyta.map.capture_screenshot", side_effect=mock_screenshot):
            m.to_image(path=None, hide_controls=False)

        assert ".leaflet-control{display:none" not in captured_html["content"]

    def test_hide_controls_true_content(self) -> None:
        """
        Scenario: Verify CSS injection content.

        Given: A Map with a location
        When: to_image is called with hide_controls=True
        Then: The HTML sent to screenshot contains leaflet-control hide CSS
        """
        m = Map()
        m.add_point(Point(4.9, 52.37))

        captured_html: dict[str, str] = {}

        def mock_screenshot(html_path: str, *_args: object, **_kwargs: object) -> bytes:
            captured_html["content"] = Path(html_path).read_text(encoding="utf-8")
            return b"\x89PNG_fake"

        with patch("mapyta.map.capture_screenshot", side_effect=mock_screenshot):
            m.to_image(path=None, hide_controls=True)

        assert ".leaflet-control{display:none !important;}" in captured_html["content"]

    def test_hide_controls_propagates_to_bytesio(self) -> None:
        """
        Scenario: to_bytesio passes hide_controls to to_image.

        Given: A Map with a location
        When: to_bytesio is called with hide_controls=False
        Then: to_image receives hide_controls=False
        """
        m = Map()
        m.add_point(Point(4.9, 52.37))

        fake_png = b"\x89PNG_fake_data_for_bytesio"
        with patch.object(Map, "to_image", return_value=fake_png) as mock_img:
            m.to_bytesio(hide_controls=False)
            mock_img.assert_called_once_with(path=None, width=1200, height=800, delay=2.0, hide_controls=False, scale=1.0)


# ===================================================================
# Scenarios for RawHTML bypass.
# ===================================================================
