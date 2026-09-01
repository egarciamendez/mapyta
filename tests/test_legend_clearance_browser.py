"""Browser-driven tests for the room a legend card leaves the controls in its corner.

The offset is measured in the browser, from the height of the Leaflet corner the card shares,
so only a real browser can show what a reader ends up looking at: a card below the controls
that are actually there, whichever call put them there and in whatever order, and a card that
takes the height back once :meth:`Map.to_image` hides them.

The module skips when selenium or Chrome is missing.
"""
# ruff: noqa: SLF001

from pathlib import Path
from typing import TYPE_CHECKING

from mapyta import Map, MapConfig
from tests.browser import eventually, open_map, requires_chrome

if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver

pytestmark = requires_chrome

#: Pixels between the bottom of the top-right control stack and the top of the legend card.
GAP_BELOW_THE_STACK = (
    "var card = document.querySelector('[data-mapyta-top]').getBoundingClientRect();"
    "var stack = document.querySelector('.leaflet-top.leaflet-right').getBoundingClientRect();"
    "return Math.round(card.top - stack.bottom);"
)

#: How far the card sits from the 5% inset its own CSS asks for.
OFFSET_FROM_THE_CSS_INSET = (
    "var card = document.querySelector('[data-mapyta-top]').getBoundingClientRect();return Math.round(card.top - window.innerHeight * 0.05);"
)

STACK_HEIGHT = "return document.querySelector('.leaflet-top.leaflet-right').offsetHeight;"


def _colorbar_map(config: MapConfig | None = None) -> Map:
    """A map carrying the colorbar every scenario measures."""
    m = Map(config=config)
    m.add_colorbar(colors=["#d73027", "#1a9850"], vmin=0.0, vmax=100.0, legend_name="R_c;net;d [kN]")
    return m


class TestLegendClearanceInTheBrowser:
    """Scenarios for where a legend card lands relative to the controls above it."""

    def test_the_card_starts_below_the_controls_that_are_there(self, browser: "WebDriver", tmp_path: Path) -> None:
        """
        Scenario: Two stacked controls push the legend down two rows.

        Given: A map with a reset-view button, a measure control and a colorbar
        When: The page is loaded
        Then: The card starts a fixed gap below the bottom of the stack, not on top of it
        """
        # Arrange - Given
        m = _colorbar_map(MapConfig(home_button=True, measure_control=True))

        # Act - When
        open_map(browser, tmp_path, m, "stacked.html")

        # Assert - Then
        eventually(browser, GAP_BELOW_THE_STACK, 10)

    def test_a_control_added_after_the_colorbar_is_cleared_too(self, browser: "WebDriver", tmp_path: Path) -> None:
        """
        Scenario: The corner fills up after the legend was asked for.

        Given: A colorbar, and only then the layer control that shares its corner
        When: The page is loaded
        Then: The card still clears the whole stack, since nothing is counted in Python

        A count taken at ``add_colorbar`` time could never get this right: the second control
        did not exist yet.
        """
        # Arrange - Given
        m = _colorbar_map(MapConfig(home_button=True)).create_feature_group("Sonderingen")
        m.reset_target().add_layer_control()

        # Act - When
        open_map(browser, tmp_path, m, "added-after.html")

        # Assert - Then
        eventually(browser, GAP_BELOW_THE_STACK, 10)

    def test_a_top_right_swatch_legend_clears_the_same_stack(self, browser: "WebDriver", tmp_path: Path) -> None:
        """
        Scenario: The categorical legend shares the corner with the controls.

        Given: A map with a reset-view button and an ``add_legend`` card in the top-right corner
        When: The page is loaded
        Then: The card starts below the button rather than behind it
        """
        # Arrange - Given
        m = Map(config=MapConfig(home_button=True))
        m.add_legend([("#1a9850", "Geclassificeerd"), ("#d73027", "Afgekeurd")], title="Status", position="topright")

        # Act - When
        open_map(browser, tmp_path, m, "swatch-topright.html")

        # Assert - Then
        eventually(browser, GAP_BELOW_THE_STACK, 10)

    def test_an_empty_corner_leaves_the_card_where_the_css_put_it(self, browser: "WebDriver", tmp_path: Path) -> None:
        """
        Scenario: Nothing occupies the top-right corner.

        Given: A map with a colorbar and no control in that corner
        When: The page is loaded
        Then: The card keeps the 5% inset it shares with its bottom edge
        """
        # Arrange - Given
        m = _colorbar_map()

        # Act - When
        open_map(browser, tmp_path, m, "empty-corner.html")

        # Assert - Then
        eventually(browser, OFFSET_FROM_THE_CSS_INSET, 0)

    def test_hiding_the_controls_gives_the_height_back(self, browser: "WebDriver", tmp_path: Path) -> None:
        """
        Scenario: The map is exported without its controls.

        Given: The page to_image renders: a two-control map whose controls are hidden
        When: The page is loaded
        Then: The stack measures nothing and the card keeps its 5%, leaving no gap where the
              controls used to be
        """
        # Arrange - Given
        m = _colorbar_map(MapConfig(home_button=True, measure_control=True))
        page = tmp_path / "exported.html"
        page.write_text(m._with_controls_hidden(m.get_standalone_html()), encoding="utf-8")

        # Act - When
        browser.get(page.resolve().as_uri())

        # Assert - Then
        eventually(browser, STACK_HEIGHT, 0)
        eventually(browser, OFFSET_FROM_THE_CSS_INSET, 0)
