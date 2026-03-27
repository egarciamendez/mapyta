"""BDD-style tests for the map module.

Each test follows the Given-When-Then pattern with a scenario
docstring and Arrange/Act/Assert comments.
"""
# ruff: noqa: SLF001

from pathlib import Path

from shapely import Point, Polygon

from mapyta import CircleStyle, FillStyle, Map, StrokeStyle
from mapyta.markers import classify_marker

# ===================================================================
# Scenarios for creating and configuring a Map.
# ===================================================================


class TestAddPoints:
    """Scenarios for adding location markers and circles."""

    def test_add_point_with_emoji_label(self) -> None:
        """
        Scenario: Add a construction site marker with an emoji.

        Given: An empty map and a Point at Amsterdam Centraal
        When: A location is added with a 🏗️ emoji marker and tooltip text
        Then: The bounds are tracked and the method returns self
        """
        # Arrange - Given
        m = Map()
        point = Point(4.8952, 52.3702)

        # Act - When
        result = m.add_point(point, marker="🏗️", tooltip="**Amsterdam Centraal**")

        # Assert - Then
        assert result is m, "add_point should return self for chaining"
        assert len(m._bounds) == 2, "One location should create 2 bound entries (min/max)"

    def test_add_point_with_icon_marker(self) -> None:
        """
        Scenario: Add a location with a Font Awesome icon.

        Given: An empty map and a CSS dict for the marker
        When: A location is added with that style
        Then: The location is added without errors
        """
        # Arrange - Given
        m = Map()
        point = Point(4.8834, 52.3667)

        # Act - When
        m.add_point(point, marker="home", tooltip="**Anne Frank House**", marker_style={"color": "green"})

        # Assert - Then
        assert len(m._bounds) == 2, "Point should be tracked in bounds"

    def test_add_point_with_popup(self) -> None:
        """
        Scenario: Add a location that shows a popup on click.

        Given: An empty map and a Point
        When: A location is added with both tooltip and popup text
        Then: Both interactions are configured
        """
        # Arrange - Given
        m = Map()
        point = Point(4.9041, 52.3676)

        # Act - When
        m.add_point(
            point,
            tooltip="**Hover** text",
            popup="# Popup\nWith *markdown* support",
        )

        # Assert - Then
        assert len(m._bounds) == 2, "Point should be tracked in bounds"

    def test_add_circle_marker(self) -> None:
        """
        Scenario: Add a fixed-size circle marker for data visualization.

        Given: An empty map and a custom CircleStyle
        When: A circle is added at the Rijksmuseum location
        Then: The circle is placed on the map with the configured style
        """
        # Arrange - Given
        m = Map()
        point = Point(4.8795, 52.3600)
        style = CircleStyle(
            radius=12,
            stroke=StrokeStyle(color="#8e44ad", weight=2),
            fill=FillStyle(color="#8e44ad", opacity=0.5),
        )

        # Act - When
        result = m.add_circle(point, tooltip="**Rijksmuseum**", style=style)

        # Assert - Then
        assert result is m, "add_circle should return self"
        assert len(m._bounds) == 2, "Circle center should be tracked"

    def test_add_point_default_marker(self) -> None:
        """
        Scenario: Add a location with no marker, no emoji, default marker.

        Given: An empty map and a Point
        When: add_point is called with only the location (no marker or style)
        Then: A default blue pin marker is placed
        """
        # Arrange - Given
        m = Map()

        # Act - When
        m.add_point(Point(4.9, 52.37))

        # Assert - Then
        assert len(m._bounds) == 2, "Point should be tracked"

    def test_add_polygon_all_defaults(self) -> None:
        """
        Scenario: Add a polygon with no custom styling.

        Given: An empty map and a Polygon
        When: add_polygon is called with only the polygon
        Then: Default blue stroke and 20% blue fill are used
        """
        # Arrange - Given
        m = Map()
        poly = Polygon([(4.85, 52.35), (4.95, 52.35), (4.95, 52.40), (4.85, 52.40)])

        # Act - When
        m.add_polygon(poly)

        # Assert - Then
        assert len(m._bounds) == 2, "Polygon should be tracked"

    def test_add_point_with_only_hover(self) -> None:
        """
        Scenario: Add a location with tooltip but no marker (icon marker).

        Given: An empty map
        When: add_point is called with tooltip text but no marker
        Then: A default icon marker with tooltip tooltip is placed
        """
        # Arrange - Given
        m = Map()

        # Act - When
        m.add_point(Point(4.9, 52.37), tooltip="**Info only**")

        # Assert - Then
        assert len(m._bounds) == 2


# ===================================================================
# Scenarios for marker classification and full icon class strings.
# ===================================================================


class TestClassifyMarker:
    """Scenarios for the _classify_marker helper function."""

    def test_classify_bare_icon_name(self) -> None:
        """
        Scenario: A bare icon name is classified as "icon_name".

        Given: A single-word ASCII string like "home"
        When: _classify_marker is called
        Then: It returns "icon_name"
        """
        assert classify_marker("home") == "icon_name"
        assert classify_marker("arrow-down") == "icon_name"
        assert classify_marker("info-sign") == "icon_name"
        assert classify_marker("fa-arrow-right") == "icon_name"
        assert classify_marker("fa-house") == "icon_name"

    def test_classify_emoji(self) -> None:
        """
        Scenario: Emoji / unicode strings are classified as "emoji".

        Given: A string containing non-ASCII characters
        When: _classify_marker is called
        Then: It returns "emoji"
        """
        assert classify_marker("\U0001f4cd") == "emoji"
        assert classify_marker("\U0001f3d7\ufe0f") == "emoji"
        assert classify_marker("\u2600") == "emoji"

    def test_classify_full_icon_class(self) -> None:
        """
        Scenario: A full CSS class string is classified as "icon_class".

        Given: An ASCII string with spaces (e.g. "fa fa-home")
        When: _classify_marker is called
        Then: It returns "icon_class"
        """
        assert classify_marker("fa fa-home") == "icon_class"
        assert classify_marker("fa-solid fa-house") == "icon_class"
        assert classify_marker("fa-regular fa-arrow-right") == "icon_class"
        assert classify_marker("glyphicon glyphicon-home") == "icon_class"

    def test_classify_empty_string(self) -> None:
        """
        Scenario: An empty string is classified as "emoji" (falsy).

        Given: An empty string
        When: _classify_marker is called
        Then: It returns "emoji"
        """
        assert classify_marker("") == "emoji"


class TestFullIconClass:
    """Scenarios for passing full CSS icon class strings as marker."""

    def test_add_point_with_full_icon_class(self, tmp_path: Path) -> None:
        """
        Scenario: A full CSS class string is used as-is in the icon markup.

        Given: An empty map
        When: add_point is called with marker="fa-solid fa-house"
        Then: The HTML contains "fa-solid fa-house" verbatim (no prefix prepended)
        """
        m = Map()
        m.add_point(Point(5.0, 52.38), marker="fa-solid fa-house")
        out = tmp_path / "full_class.html"
        m.to_html(out)
        html = out.read_text(encoding="utf-8")
        assert "fa-solid fa-house" in html

    def test_add_point_bare_name_prepends_prefix(self, tmp_path: Path) -> None:
        """
        Scenario: A bare icon name gets prefix prepended as before.

        Given: An empty map
        When: add_point is called with marker="home" (bare name)
        Then: The HTML contains "glyphicon glyphicon-home" (default prefix)
        """
        m = Map()
        m.add_point(Point(4.9, 52.37), marker="home")
        out = tmp_path / "bare_name.html"
        m.to_html(out)
        html = out.read_text(encoding="utf-8")
        assert "glyphicon glyphicon-home" in html

    def test_add_point_bare_fa_name_gets_fa_solid_prefix(self, tmp_path: Path) -> None:
        """
        Scenario: A bare FontAwesome icon name gets "fa-solid" prefix.

        Given: An empty map
        When: add_point is called with marker="fa-arrow-right" (bare FA name)
        Then: The HTML contains "fa-solid fa-arrow-right"
        """
        m = Map()
        m.add_point(Point(4.9, 52.37), marker="fa-arrow-right", caption="AMS")
        out = tmp_path / "bare_fa.html"
        m.to_html(out)
        html = out.read_text(encoding="utf-8")
        assert "fa-solid fa-arrow-right" in html
        assert "AMS" in html

    def test_add_point_emoji_still_renders_as_text(self, tmp_path: Path) -> None:
        """
        Scenario: Emoji markers still render as text DivIcons.

        Given: An empty map
        When: add_point is called with an emoji marker
        Then: The HTML contains font-size styling (_DEFAULT_TEXT_CSS default)
        """
        m = Map()
        m.add_point(Point(5.1, 52.39), marker="\U0001f4cd")
        out = tmp_path / "emoji.html"
        m.to_html(out)
        html = out.read_text(encoding="utf-8")
        assert "font-size:16px" in html

    def test_marker_cluster_with_full_icon_class(self, tmp_path: Path) -> None:
        """
        Scenario: Full icon class strings work in marker clusters.

        Given: An empty map and points with full CSS class labels
        When: add_marker_cluster is called with full class labels
        Then: The HTML contains the full class strings verbatim
        """
        m = Map()
        points = [Point(4.9, 52.37), Point(5.0, 52.38)]
        labels = ["fa-solid fa-house", "fa-regular fa-star"]
        m.add_marker_cluster(points, labels=labels)
        out = tmp_path / "cluster_full_class.html"
        m.to_html(out)
        html = out.read_text(encoding="utf-8")
        assert "fa-solid fa-house" in html
        assert "fa-regular fa-star" in html

    def test_marker_cluster_with_mixed_labels(self, tmp_path: Path) -> None:
        """
        Scenario: Cluster with a mix of bare icon names and full class strings.

        Given: An empty map and points with mixed label types
        When: add_marker_cluster is called
        Then: Bare names get prefix prepended, full class strings are used as-is
        """
        m = Map()
        points = [Point(4.9, 52.37), Point(5.0, 52.38), Point(5.1, 52.39)]
        labels = ["home", "fa-solid fa-house", "\U0001f4cd"]
        m.add_marker_cluster(points, labels=labels)
        out = tmp_path / "cluster_mixed.html"
        m.to_html(out)
        html = out.read_text(encoding="utf-8")
        assert "glyphicon glyphicon-home" in html
        assert "fa-solid fa-house" in html
        assert "font-size:16px" in html


# ===================================================================
# Scenarios for adding lines and polygons.
# ===================================================================


class TestCaption:
    """Scenarios for the caption parameter on add_point."""

    def test_caption_with_emoji_marker(self, tmp_path: Path) -> None:
        """
        Scenario: Emoji marker with a caption below.

        Given: A location with marker="📍" and caption="Amsterdam"
        When: add_point is called
        Then: The HTML contains the caption text
        """
        m = Map()
        m.add_point(Point(4.9, 52.37), marker="\U0001f4cd", caption="Amsterdam")
        out = tmp_path / "emoji_label.html"
        m.to_html(out)
        html = out.read_text(encoding="utf-8")
        assert "Amsterdam" in html

    def test_caption_with_icon_marker(self, tmp_path: Path) -> None:
        """
        Scenario: Default icon marker with a caption below.

        Given: A location with no marker and caption="Station"
        When: add_point is called
        Then: The HTML contains the caption text and the default icon glyph
        """
        m = Map()
        m.add_point(Point(4.9, 52.37), caption="Station")
        out = tmp_path / "icon_label.html"
        m.to_html(out)
        html = out.read_text(encoding="utf-8")
        assert "Station" in html
        assert "glyphicon glyphicon-arrow-down" in html

    def test_caption_with_custom_caption_style(self, tmp_path: Path) -> None:
        """
        Scenario: Caption with custom CSS styling.

        Given: A marker with caption and a custom CSS dict
        When: add_point is called
        Then: The HTML contains the custom style properties
        """
        m = Map()
        m.add_point(
            Point(4.9, 52.37),
            marker="home",
            caption="S-001",
            caption_style={"font-size": "14px", "color": "red"},
        )
        out = tmp_path / "styled_label.html"
        m.to_html(out)
        html = out.read_text(encoding="utf-8")
        assert "S-001" in html
        assert "font-size:14px" in html
        assert "color:red" in html

    def test_caption_none_adds_no_extra_marker(self) -> None:
        """
        Scenario: No caption means no extra marker.

        Given: An icon marker without caption
        When: add_point is called
        Then: Same number of children as with caption (both use DivIcon)
        """
        m = Map()
        m.add_point(Point(4.9, 52.37))
        children_without = len(m._map._children)

        m2 = Map()
        m2.add_point(Point(4.9, 52.37), caption="X")
        children_with = len(m2._map._children)

        assert children_with == children_without, "caption should not add an extra marker"

    def test_caption_default_style_has_no_background(self, tmp_path: Path) -> None:
        """
        Scenario: Default caption_style for caption has no background/border.

        Given: A caption without explicit caption_style
        When: add_point is called
        Then: The caption uses _DEFAULT_MARKER_CAPTION_CSS (transparent bg, no border)
        """
        m = Map()
        m.add_point(Point(4.9, 52.37), marker="home", caption="Test")
        out = tmp_path / "default_style.html"
        m.to_html(out)
        html = out.read_text(encoding="utf-8")
        assert "Test" in html
        assert "background-color:transparent" in html

    def test_caption_with_min_zoom_single_marker(self) -> None:
        """
        Scenario: min_zoom tracks the combined marker (icon + caption in one DivIcon).

        Given: An icon marker with caption and min_zoom=10
        When: add_point is called
        Then: One entry is added to _zoom_controlled_markers
        """
        m = Map()
        m.add_point(
            Point(4.9, 52.37),
            marker="home",
            caption="CPT-01",
            min_zoom=10,
        )
        assert len(m._zoom_controlled_markers) == 1, "Combined marker should be a single entry"
        assert m._zoom_controlled_markers[0]["min_zoom"] == 10


# ===================================================================
# Scenarios for zoom-dependent marker visibility.
# ===================================================================


class TestCSSMarkerStyle:
    """Scenarios for CSS dict marker style parameters."""

    def test_marker_style_none_uses_defaults(self, tmp_path: Path) -> None:
        """
        Scenario: None marker_style uses default CSS.

        Given: An empty map
        When: add_point is called with marker_style=None
        Then: The HTML contains default icon CSS values
        """
        m = Map()
        m.add_point(Point(4.9, 52.37), marker="home")
        out = tmp_path / "default.html"
        m.to_html(out)
        html = out.read_text(encoding="utf-8")
        assert "font-size:20px" in html
        assert "color:#002855" in html

    def test_marker_style_dict_overrides_defaults(self, tmp_path: Path) -> None:
        """
        Scenario: CSS dict overrides default values.

        Given: An empty map and a marker_style dict
        When: add_point is called with custom CSS
        Then: The HTML contains the overridden values
        """
        m = Map()
        m.add_point(Point(4.9, 52.37), marker="home", marker_style={"font-size": "30px", "color": "red"})
        out = tmp_path / "override.html"
        m.to_html(out)
        html = out.read_text(encoding="utf-8")
        assert "font-size:30px" in html
        assert "color:red" in html

    def test_marker_style_adds_custom_css(self, tmp_path: Path) -> None:
        """
        Scenario: CSS dict can add properties not in defaults.

        Given: An empty map and a marker_style with text-shadow
        When: add_point is called
        Then: The HTML contains the extra CSS property
        """
        m = Map()
        m.add_point(Point(4.9, 52.37), marker="home", marker_style={"text-shadow": "1px 1px 2px black"})
        out = tmp_path / "extra_css.html"
        m.to_html(out)
        html = out.read_text(encoding="utf-8")
        assert "text-shadow:1px 1px 2px black" in html

    def test_empty_dict_uses_defaults(self, tmp_path: Path) -> None:
        """
        Scenario: Empty dict uses default CSS (same as None).

        Given: An empty map
        When: add_point is called with marker_style={}
        Then: The HTML contains default CSS values
        """
        m = Map()
        m.add_point(Point(4.9, 52.37), marker="home", marker_style={})
        out = tmp_path / "empty.html"
        m.to_html(out)
        html = out.read_text(encoding="utf-8")
        assert "font-size:20px" in html
