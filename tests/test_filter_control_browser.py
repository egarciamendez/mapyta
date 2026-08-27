"""Browser-driven tests for the marker filter.

The filter ships as generated JavaScript, so only a real browser can show that typing
into the box takes markers off the map and that emptying it brings them back.  Each
scenario counts what Leaflet actually put in the DOM rather than reading the script,
which is the only way to tell a filter that runs from one that merely rendered.

The module skips when selenium or Chrome is missing.
"""

import time
from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from shapely.geometry import Point

from mapyta import ClusterStyle, Map, MapConfig
from mapyta.export import _detect_chrome

if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver

webdriver = pytest.importorskip("selenium.webdriver", reason="browser tests need selenium (the 'export' extra)")

pytestmark = pytest.mark.skipif(not _detect_chrome(), reason="browser tests need Chrome")

COUNT_MARKERS = "return document.querySelectorAll('.leaflet-marker-icon').length;"
COUNT_BUBBLED = (
    "return Array.from(document.querySelectorAll('.marker-cluster')).reduce(function(total, el) { return total + Number(el.textContent); }, 0);"
)
FILTER_BOX = "document.querySelector('.leaflet-control input[type=text]')"


@pytest.fixture(scope="session")
def browser() -> Generator["WebDriver", None, None]:
    """A headless Chrome session shared by every scenario in this module."""
    options = webdriver.ChromeOptions()
    for flag in ("--headless=new", "--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage", "--window-size=1200,900"):
        options.add_argument(flag)
    try:
        driver = webdriver.Chrome(options=options)
    except Exception as exc:  # a browser that will not start is a skip, not a mapyta failure
        pytest.skip(f"could not start Chrome: {exc}")
    yield driver
    driver.quit()


def eventually(browser: "WebDriver", script: str, expected: object, timeout: float = 15.0) -> None:
    """Poll *script* until it returns *expected*, reporting the last value seen on failure."""
    deadline = time.monotonic() + timeout
    actual = None
    while time.monotonic() < deadline:
        actual = browser.execute_script(script)
        if actual == expected:
            return
        time.sleep(0.05)
    pytest.fail(f"expected {expected!r}, last saw {actual!r}")


def type_into_filter(browser: "WebDriver", text: str) -> None:
    """Put *text* in the filter box the way a reader would, and let it act on the map."""
    browser.execute_script(f"var box = {FILTER_BOX}; box.value = {text!r}; box.dispatchEvent(new Event('input'));")


def open_map(browser: "WebDriver", tmp_path: Path, m: Map, name: str) -> None:
    """Render *m* to *name* under *tmp_path* and load it in *browser*."""
    browser.get(Path(m.to_html(tmp_path / name)).resolve().as_uri())
    eventually(browser, f"return {FILTER_BOX} !== null;", True)


def _points(n: int) -> list[Point]:
    """Return *n* RD New points spread far enough apart to stay separate markers."""
    return [Point(135_000 + (i % 5) * 2_000, 455_000 + (i // 5) * 2_000) for i in range(n)]


class TestFilterControlInTheBrowser:
    """Scenarios for what typing in the filter box does to the map."""

    def test_typing_takes_the_map_down_to_the_matches(self, browser: "WebDriver", tmp_path: Path) -> None:
        """
        Scenario: The map keeps only what matches.

        Given: Six markers on the map
        When: One of them is typed into the filter box
        Then: It is the only one left, a term matching nothing empties the map, and an
              empty box brings all six back
        """
        # Arrange - Given
        captions = ["CPT-001", "CPT-002", "CPT-003", "CPT-004", "CPT-005", "CPT-006"]
        m = Map(config=MapConfig(zoom_start=10))
        m.add_points(_points(6), marker="triangle-bottom", captions=captions).add_filter_control()

        # Act - When
        open_map(browser, tmp_path, m, "filter.html")
        eventually(browser, COUNT_MARKERS, 6)
        type_into_filter(browser, "cpt-004")

        # Assert - Then
        eventually(browser, COUNT_MARKERS, 1)
        type_into_filter(browser, "CPT-999")
        eventually(browser, COUNT_MARKERS, 0)
        type_into_filter(browser, "")
        eventually(browser, COUNT_MARKERS, 6)

    def test_a_point_is_found_by_what_the_map_never_shows(self, browser: "WebDriver", tmp_path: Path) -> None:
        """
        Scenario: The filter reaches past the caption.

        Given: Markers captioned by sounding name, whose search text also names their project
        When: The project is typed in
        Then: Its two soundings survive, though neither caption mentions it
        """
        # Arrange - Given
        captions = ["CPT-001", "CPT-002", "CPT-003", "CPT-004"]
        projects = ["Zuidasdok", "Zuidasdok", "Afsluitdijk", "Afsluitdijk"]
        m = Map(config=MapConfig(zoom_start=10))
        m.add_points(
            _points(4),
            marker="triangle-bottom",
            captions=captions,
            search_texts=[f"{caption} {project}" for caption, project in zip(captions, projects, strict=True)],
        ).add_filter_control()

        # Act - When
        open_map(browser, tmp_path, m, "search_texts.html")
        eventually(browser, COUNT_MARKERS, 4)
        type_into_filter(browser, "zuidasdok")

        # Assert - Then
        eventually(browser, COUNT_MARKERS, 2)

    def test_a_cluster_recounts_to_what_is_left_of_it(self, browser: "WebDriver", tmp_path: Path) -> None:
        """
        Scenario: Filtering a clustered layer is not a lie about how many there are.

        Given: Ten markers sharing one bubble, three of them from one project
        When: That project is typed in
        Then: The bubble reports three, so the count follows the filter rather than the data
        """
        # Arrange - Given
        captions = [f"CPT-{i:03d}" for i in range(10)]
        # An explicit centre, because fitting to the data would zoom until the points
        # stand apart in pixels and stop bubbling, whatever their spacing on the ground.
        m = Map(center=(52.05, 4.9), config=MapConfig(zoom_start=9))
        m.add_points(
            _points(10),
            marker="triangle-bottom",
            captions=captions,
            search_texts=[f"{caption} {'Zuidasdok' if i < 3 else 'Afsluitdijk'}" for i, caption in enumerate(captions)],
            cluster=ClusterStyle(),
        ).add_filter_control()

        # Act - When
        open_map(browser, tmp_path, m, "clustered_filter.html")
        eventually(browser, COUNT_BUBBLED, 10)
        type_into_filter(browser, "Zuidasdok")

        # Assert - Then
        eventually(browser, COUNT_BUBBLED, 3)
