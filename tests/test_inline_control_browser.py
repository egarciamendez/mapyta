"""Browser-driven tests for where an inline corner control lands.

``inline=True`` drops the clear that stacks a Leaflet control below its neighbour and moves
it behind the corner's first one.  Both are layout rather than markup, so only a real browser
can tell a control that ends up beside the zoom buttons from one that merely carries the
script saying it should.

The module skips when selenium or Chrome is missing.
"""

from pathlib import Path
from typing import TYPE_CHECKING

from shapely.geometry import Point

from mapyta import Map
from tests.browser import eventually, open_map, requires_chrome

if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver

pytestmark = requires_chrome

#: The two widgets that can be placed inline, each found by what it puts in the control.
DROPDOWN = ".leaflet-control select"
FILTER_BOX = ".leaflet-control input[type=text]"

#: Leaflet's gap between two controls, and so between an inline control and the one it shares the row with.
CONTROL_GAP = 10


def _corner_of(widget: str) -> str:
    """JavaScript resolving *widget*'s control box and the zoom buttons it is measured against."""
    return (
        f"var box = document.querySelector('{widget}').closest('.leaflet-control').getBoundingClientRect();"
        "var zoom = document.querySelector('.leaflet-control-zoom').getBoundingClientRect();"
    )


def _row_offset(widget: str) -> str:
    """Pixels between the top of *widget*'s control and the top of the zoom buttons: zero on a shared row."""
    return f"{_corner_of(widget)}return Math.round(box.top - zoom.top);"


def _gap_beside_the_zoom(widget: str) -> str:
    """Pixels between the right edge of the zoom buttons and the left edge of *widget*'s control."""
    return f"{_corner_of(widget)}return Math.round(box.left - zoom.right);"


def _gap_below_the_zoom(widget: str) -> str:
    """Pixels between the bottom of the zoom buttons and the top of *widget*'s control."""
    return f"{_corner_of(widget)}return Math.round(box.top - zoom.bottom);"


def _dropdown_map() -> Map:
    """A map with the two feature groups the dropdown switches between."""
    m = Map()
    m.create_feature_group("Sonderingen").add_point(Point(4.9, 52.37))
    m.create_feature_group("Boringen").add_point(Point(4.91, 52.38))
    return m.reset_target()


def _filter_map() -> Map:
    """A map with the points the filter box acts on."""
    return Map().add_points([Point(4.9, 52.37), Point(4.91, 52.38)])


class TestInlineControlsInTheBrowser:
    """Scenarios for where an inline control lands relative to its corner's first control."""

    def test_an_inline_dropdown_shares_the_row_with_the_zoom_buttons(self, browser: "WebDriver", tmp_path: Path) -> None:
        """
        Scenario: The dropdown is placed beside the corner's first control.

        Given: A map with feature groups and an inline dropdown in the top-left corner
        When: The page is loaded
        Then: The dropdown starts at the zoom buttons' own top, one control gap to their right
        """
        # Arrange - Given
        m = _dropdown_map().add_layer_dropdown(inline=True)

        # Act - When
        open_map(browser, tmp_path, m, "inline-dropdown.html", ready=f"return document.querySelector('{DROPDOWN}') !== null;")

        # Assert - Then
        eventually(browser, _row_offset(DROPDOWN), 0)
        eventually(browser, _gap_beside_the_zoom(DROPDOWN), CONTROL_GAP)

    def test_an_inline_filter_box_shares_the_row_with_the_zoom_buttons(self, browser: "WebDriver", tmp_path: Path) -> None:
        """
        Scenario: The filter box is placed beside the corner's first control.

        Given: A map with points and an inline filter box in the top-left corner
        When: The page is loaded
        Then: The box starts at the zoom buttons' own top, one control gap to their right
        """
        # Arrange - Given
        m = _filter_map().add_filter_control(inline=True)

        # Act - When
        open_map(browser, tmp_path, m, "inline-filter.html", ready=f"return document.querySelector('{FILTER_BOX}') !== null;")

        # Assert - Then
        eventually(browser, _row_offset(FILTER_BOX), 0)
        eventually(browser, _gap_beside_the_zoom(FILTER_BOX), CONTROL_GAP)

    def test_without_inline_the_dropdown_keeps_its_own_row(self, browser: "WebDriver", tmp_path: Path) -> None:
        """
        Scenario: The default placement is the row below.

        Given: The same map with the dropdown added without inline
        When: The page is loaded
        Then: The dropdown starts one control gap below the zoom buttons instead of beside them

        The contrast is what makes the two scenarios above mean something: the same measurement
        tells a shared row from a stacked one.
        """
        # Arrange - Given
        m = _dropdown_map().add_layer_dropdown()

        # Act - When
        open_map(browser, tmp_path, m, "stacked-dropdown.html", ready=f"return document.querySelector('{DROPDOWN}') !== null;")

        # Assert - Then
        eventually(browser, _gap_below_the_zoom(DROPDOWN), CONTROL_GAP)
