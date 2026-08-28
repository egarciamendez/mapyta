"""Browser-driven tests that a glyphicon marker actually paints.

A marker class the icon font does not define still renders: the ``<i>`` is in the DOM,
Leaflet positions it, and every assertion on generated HTML passes while the map shows
nothing.  Only a browser can tell the two apart, by measuring the box the glyph paints.
That is how ``triangle-bottom`` — added in Bootstrap 3.3.0, absent from the 3.0.0 sheet
Folium pins — went unnoticed across the docs and the suite.

The module skips when selenium or Chrome is missing.
"""

from pathlib import Path
from typing import TYPE_CHECKING

from shapely.geometry import Point

from mapyta import Map, MapConfig
from tests.browser import COUNT_MARKERS, eventually, open_map, requires_chrome

if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver

pytestmark = requires_chrome

COUNT_PAINTED = (
    "return Array.from(document.querySelectorAll('.leaflet-marker-icon i.glyphicon'))"
    ".filter(function(e) { return e.getBoundingClientRect().width > 0; }).length;"
)
MEASURE_UNDEFINED_ICON = (
    "var probe = document.createElement('i');"
    " probe.className = 'glyphicon glyphicon-not-an-icon';"
    " document.body.appendChild(probe);"
    " var width = probe.getBoundingClientRect().width;"
    " probe.remove();"
    " return width;"
)


def _points(n: int) -> list[Point]:
    """Return *n* RD New points spread far enough apart to stay separate markers."""
    return [Point(135_000 + (i % 5) * 2_000, 455_000 + (i // 5) * 2_000) for i in range(n)]


class TestGlyphiconMarkersInTheBrowser:
    """Scenarios for whether a glyphicon marker paints a glyph or an empty box."""

    def test_a_glyphicon_the_font_lacks_paints_nothing(self, browser: "WebDriver", tmp_path: Path) -> None:
        """
        Scenario: The measurement can tell a missing icon from a present one.

        Given: A map carrying the glyphicon stylesheet
        When: An ``<i>`` with an undefined glyphicon class is measured
        Then: It comes out zero-width, so the width assertions below can fail
        """
        # Arrange - Given
        m = Map(config=MapConfig(zoom_start=10))
        m.add_point(Point(135_000, 455_000), marker="triangle-bottom")
        open_map(browser, tmp_path, m, "control.html")
        eventually(browser, COUNT_MARKERS, 1)

        # Assert - Then
        assert browser.execute_script(MEASURE_UNDEFINED_ICON) == 0

    def test_a_triangle_marker_paints_a_glyph(self, browser: "WebDriver", tmp_path: Path) -> None:
        """
        Scenario: A Bootstrap 3.3 glyphicon renders on a single marker.

        Given: One point marked with "triangle-bottom"
        When: The map is opened
        Then: Its glyph paints a box of its own
        """
        # Arrange - Given
        m = Map(config=MapConfig(zoom_start=10))
        m.add_point(Point(135_000, 455_000), marker="triangle-bottom")

        # Act - When
        open_map(browser, tmp_path, m, "single.html")

        # Assert - Then
        eventually(browser, COUNT_PAINTED, 1)

    def test_a_bulk_layer_paints_every_glyph(self, browser: "WebDriver", tmp_path: Path) -> None:
        """
        Scenario: The browser-built icons of a bulk layer render the same glyph.

        Given: Six points in one add_points layer marked with "triangle-bottom"
        When: The map is opened
        Then: All six glyphs paint, not just the markers that hold them
        """
        # Arrange - Given
        m = Map(config=MapConfig(zoom_start=10))
        m.add_points(_points(6), marker="triangle-bottom", captions=[f"CPT-{i:03d}" for i in range(6)])

        # Act - When
        open_map(browser, tmp_path, m, "bulk.html")

        # Assert - Then
        eventually(browser, COUNT_MARKERS, 6)
        eventually(browser, COUNT_PAINTED, 6)
