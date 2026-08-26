"""Browser-driven tests for zoom-dependent visibility.

The zoom rules ship as generated JavaScript, so only a real browser can show that a
``min_zoom`` layer and the layer control agree on what belongs on the map.  Every
scenario first proves the zoom controller is live — markers disappearing below
``min_zoom`` can come from nothing else — so a script that never attaches fails the
test instead of passing it by accident.

The module skips when selenium or Chrome is missing.
"""

import time
from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from shapely.geometry import Point

from mapyta import Map, MapConfig
from mapyta.export import _detect_chrome

if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver

webdriver = pytest.importorskip("selenium.webdriver", reason="browser tests need selenium (the 'export' extra)")

pytestmark = pytest.mark.skipif(not _detect_chrome(), reason="browser tests need Chrome")

MAP_VAR = "window[document.querySelector('.folium-map').id]"
COUNT_MARKERS = "return document.querySelectorAll('.leaflet-marker-icon').length;"
COUNT_CAPTIONS = "return Array.from(document.querySelectorAll('[id^=caption_]')).filter(function(e) { return e.style.display !== 'none'; }).length;"
OVERLAY_BOX = "document.querySelector('.leaflet-control-layers-overlays input[type=checkbox]')"
READ_CHECKBOX = f"return {OVERLAY_BOX}.checked;"
CLICK_CHECKBOX = f"{OVERLAY_BOX}.click();"


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


def open_map(browser: "WebDriver", tmp_path: Path, m: Map, name: str) -> None:
    """Render *m* to *name* under *tmp_path* and load it in *browser*."""
    browser.get(Path(m.to_html(tmp_path / name)).resolve().as_uri())


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


def zoom_to(browser: "WebDriver", zoom: int) -> None:
    """Zoom to *zoom* and return once every ``zoomend`` handler has run.

    The one-shot counter registers after the handlers already on the map, and Leaflet
    fires in registration order, so seeing it move means mapyta's visibility update has
    already happened.  Without it a "still hidden" assertion could pass before the zoom
    had a chance to reveal anything.
    """
    browser.execute_script(
        f"var map = {MAP_VAR}; window.__zoomed = false; map.once('zoomend', function() {{ window.__zoomed = true; }}); map.setZoom({zoom});"
    )
    eventually(browser, "return window.__zoomed;", True)


def wait_for_zoom_controller(browser: "WebDriver", *, below: int, above: int, visible: int) -> None:
    """Block until the generated zoom script has taken charge of visibility.

    Dipping under ``min_zoom`` is the proof, since nothing else on the page hides the
    markers.  Scenarios that click the layer control need it: a click landing before the
    script attaches tests the page, not the fix.
    """
    zoom_to(browser, below)
    eventually(browser, COUNT_MARKERS, 0)
    zoom_to(browser, above)
    eventually(browser, COUNT_MARKERS, visible)


def grouped_map() -> Map:
    """Eight points at ``min_zoom=12`` inside a 'Sonderingen' group, switchable in the layer control."""
    m = Map(center=(52.0, 5.0), config=MapConfig(zoom_start=14))
    m.create_feature_group("Sonderingen")
    for i in range(8):
        m.add_point(Point(5.0 + i * 0.001, 52.0 + i * 0.001), marker="📍", min_zoom=12)
    return m.reset_target().add_layer_control()


def named_layer_map() -> Map:
    """The same eight points as one named bulk layer, which is its own entry in the layer control."""
    m = Map(center=(52.0, 5.0), config=MapConfig(zoom_start=14))
    m.add_points([Point(5.0 + i * 0.001, 52.0 + i * 0.001) for i in range(8)], name="Sonderingen", marker="📍", min_zoom=12)
    return m.add_layer_control()


class TestZoomVisibilityInBrowser:
    """Scenarios where min_zoom and the layer control both decide what is visible."""

    def test_zoom_hides_and_restores_markers(self, browser: "WebDriver", tmp_path: Path) -> None:
        """
        Scenario: min_zoom alone governs visibility while the control is untouched.

        Given: A map of eight min_zoom=12 markers opened at zoom 14
        When: The map zooms below and back above that level
        Then: The markers disappear and come back
        """
        open_map(browser, tmp_path, grouped_map(), "baseline.html")
        eventually(browser, COUNT_MARKERS, 8)

        zoom_to(browser, 10)
        eventually(browser, COUNT_MARKERS, 0)

        zoom_to(browser, 14)
        eventually(browser, COUNT_MARKERS, 8)

    def test_zooming_does_not_revive_a_group_switched_off(self, browser: "WebDriver", tmp_path: Path) -> None:
        """
        Scenario: A feature group the user unchecked stays off across a zoom.

        Given: A map whose 'Sonderingen' group holds min_zoom=12 markers
        When: The group is unchecked and the map zooms out and back in
        Then: The markers stay gone and the checkbox keeps telling the truth
        """
        open_map(browser, tmp_path, grouped_map(), "group.html")
        wait_for_zoom_controller(browser, below=10, above=14, visible=8)

        browser.execute_script(CLICK_CHECKBOX)
        eventually(browser, COUNT_MARKERS, 0)

        zoom_to(browser, 13)
        eventually(browser, COUNT_MARKERS, 0)
        zoom_to(browser, 14)
        eventually(browser, COUNT_MARKERS, 0)
        assert browser.execute_script(READ_CHECKBOX) is False

    def test_zooming_does_not_revive_a_named_layer_switched_off(self, browser: "WebDriver", tmp_path: Path) -> None:
        """
        Scenario: A named bulk layer the user unchecked stays off across a zoom.

        Given: A map with a min_zoom=12 'Sonderingen' layer of its own in the control
        When: The layer is unchecked and the map zooms out and back in
        Then: The markers stay gone and the checkbox stays unchecked
        """
        open_map(browser, tmp_path, named_layer_map(), "named.html")
        wait_for_zoom_controller(browser, below=10, above=14, visible=8)

        browser.execute_script(CLICK_CHECKBOX)
        eventually(browser, COUNT_MARKERS, 0)

        zoom_to(browser, 13)
        eventually(browser, COUNT_MARKERS, 0)
        zoom_to(browser, 14)
        eventually(browser, COUNT_MARKERS, 0)
        assert browser.execute_script(READ_CHECKBOX) is False

    def test_switching_a_group_back_on_below_min_zoom_keeps_it_hidden(self, browser: "WebDriver", tmp_path: Path) -> None:
        """
        Scenario: Re-checking a group below min_zoom does not smuggle its markers in.

        Given: A map zoomed to 10, below the markers' min_zoom of 12
        When: The 'Sonderingen' group is unchecked and checked again
        Then: The markers stay hidden until the zoom allows them
        """
        open_map(browser, tmp_path, grouped_map(), "recheck.html")
        eventually(browser, COUNT_MARKERS, 8)

        zoom_to(browser, 10)
        eventually(browser, COUNT_MARKERS, 0)

        browser.execute_script(CLICK_CHECKBOX)
        eventually(browser, COUNT_MARKERS, 0)
        browser.execute_script(CLICK_CHECKBOX)
        eventually(browser, COUNT_MARKERS, 0)

        zoom_to(browser, 14)
        eventually(browser, COUNT_MARKERS, 8)

    def test_layer_dropdown_group_respects_min_zoom(self, browser: "WebDriver", tmp_path: Path) -> None:
        """
        Scenario: The dropdown switches groups without overriding min_zoom.

        Given: Two groups of min_zoom=12 markers behind the single-select dropdown
        When: The selection changes while the map sits below that zoom
        Then: The newly selected group stays hidden until the map zooms back in
        """
        m = Map(center=(52.0, 5.0), config=MapConfig(zoom_start=14))
        m.create_feature_group("A")
        for i in range(3):
            m.add_point(Point(5.0 + i * 0.002, 52.0), marker="📍", min_zoom=12)
        m.create_feature_group("B")
        for i in range(5):
            m.add_point(Point(5.0 + i * 0.002, 52.01), marker="📍", min_zoom=12)
        open_map(browser, tmp_path, m.reset_target().add_layer_dropdown(), "dropdown.html")
        wait_for_zoom_controller(browser, below=10, above=14, visible=3)

        select_b = "var s = document.querySelector('.leaflet-bar select'); s.value = 'B'; s.onchange();"
        browser.execute_script(select_b)
        eventually(browser, COUNT_MARKERS, 5)

        zoom_to(browser, 10)
        eventually(browser, COUNT_MARKERS, 0)

        browser.execute_script("var s = document.querySelector('.leaflet-bar select'); s.value = 'A'; s.onchange();")
        eventually(browser, COUNT_MARKERS, 0)

        zoom_to(browser, 14)
        eventually(browser, COUNT_MARKERS, 3)

    def test_captions_follow_their_own_min_zoom(self, browser: "WebDriver", tmp_path: Path) -> None:
        """
        Scenario: A caption appears later than the marker it belongs to.

        Given: Four markers at min_zoom=12 whose captions start at zoom 15
        When: The map moves between zoom 11, 13 and 15
        Then: Marker and caption each follow their own threshold
        """
        m = Map(center=(52.0, 5.0), config=MapConfig(zoom_start=13))
        for i in range(4):
            m.add_point(Point(5.0 + i * 0.002, 52.0 + i * 0.002), marker="📍", caption=f"P{i}", min_zoom=12, min_zoom_caption=15)
        open_map(browser, tmp_path, m, "captions.html")
        eventually(browser, COUNT_MARKERS, 4)
        eventually(browser, COUNT_CAPTIONS, 0)

        zoom_to(browser, 15)
        eventually(browser, COUNT_MARKERS, 4)
        eventually(browser, COUNT_CAPTIONS, 4)

        zoom_to(browser, 11)
        eventually(browser, COUNT_MARKERS, 0)
        eventually(browser, COUNT_CAPTIONS, 0)
