"""BDD-style tests for the map module.

Each test follows the Given-When-Then pattern with a scenario
docstring and Arrange/Act/Assert comments.
"""
# ruff: noqa: SLF001


import pytest

from mapyta import HeatmapStyle, Map

try:
    from geopandas import GeoDataFrame
except ImportError:
    GeoDataFrame = None  # type: ignore[assignment,misc]
from shapely.geometry import (
    Point,
)

# ===================================================================
# Scenarios for creating and configuring a Map.
# ===================================================================


class TestFeatureGroups:
    """Scenarios for organising layers into toggleable groups."""

    def test_create_feature_group(self) -> None:
        """
        Scenario: Organize museum markers in a named layer.

        Given: An empty map
        When: A feature group "Museums" is created
        Then: The group is registered and becomes the active target
        """
        # Arrange - Given
        m = Map()

        # Act - When
        result = m.create_feature_group("Museums")

        # Assert - Then
        assert result is m, "create_feature_group should return self"
        assert "Museums" in m._feature_groups, "Group should be registered"
        assert m._active_group is m._feature_groups["Museums"], "Group should be active"

    def test_features_go_to_active_group(self) -> None:
        """
        Scenario: Points are added to the currently active group.

        Given: A map with an active feature group "Parks"
        When: A location is added
        Then: The location exists inside the feature group, not the base map
        """
        # Arrange - Given
        m = Map()
        m.create_feature_group("Parks")

        # Act - When
        m.add_point(Point(4.8765, 52.3579), marker="🌳", tooltip="**Vondelpark**")

        # Assert - Then
        fg = m._feature_groups["Parks"]
        assert len(fg._children) > 0, "Point should be added to the active group"

    def test_switch_between_groups(self) -> None:
        """
        Scenario: Switch from one layer group to another.

        Given: A map with two feature groups "Museums" and "Parks"
        When: set_feature_group("Museums") is called
        Then: The active target switches to Museums
        """
        # Arrange - Given
        m = Map()
        m.create_feature_group("Museums")
        m.create_feature_group("Parks")

        # Act - When
        m.set_feature_group("Museums")

        # Assert - Then
        assert m._active_group is m._feature_groups["Museums"]

    def test_reset_target_to_base_map(self) -> None:
        """
        Scenario: Return to adding features directly to the base map.

        Given: A map with an active feature group
        When: reset_target() is called
        Then: Subsequent features go to the base map
        """
        # Arrange - Given
        m = Map()
        m.create_feature_group("Temp Layer")

        # Act - When
        m.reset_target()

        # Assert - Then
        assert m._active_group is m._map, "Active target should be the base map"

    def test_set_nonexistent_group_raises(self) -> None:
        """
        Scenario: Attempt to switch to a group that doesn't exist.

        Given: A map with no feature groups
        When: set_feature_group("Ghost") is called
        Then: A KeyError is raised with the group name
        """
        # Arrange - Given
        m = Map()

        # Act & Assert - When/Then
        with pytest.raises(KeyError, match="Ghost"):
            m.set_feature_group("Ghost")

    def test_add_layer_control(self) -> None:
        """
        Scenario: Add a layer toggle widget after creating groups.

        Given: A map with two feature groups and some points
        When: add_layer_control() is called
        Then: The control is added and the method returns self
        """
        # Arrange - Given
        m = Map()
        m.create_feature_group("A").add_point(Point(4.9, 52.37))
        m.create_feature_group("B").add_point(Point(5.1, 52.09))

        # Act - When
        result = m.add_layer_control(collapsed=False)

        # Assert - Then
        assert result is m, "add_layer_control should return self"

    def test_create_hidden_feature_group(self) -> None:
        """
        Scenario: Create a feature group that is hidden by default.

        Given: An empty map
        When: create_feature_group is called with show=False
        Then: The group is registered but not visible initially
        """
        # Arrange - Given
        m = Map()

        # Act - When
        m.create_feature_group("Hidden Layer", show=False)

        # Assert - Then
        assert "Hidden Layer" in m._feature_groups
        fg = m._feature_groups["Hidden Layer"]
        assert fg.show is False, "Feature group should be hidden"

    def test_add_layer_control_with_position(self) -> None:
        """
        Scenario: Place the layer control at a specific position.

        Given: A map with feature groups
        When: add_layer_control is called with position="bottomleft"
        Then: The control is added (no error raised)
        """
        # Arrange - Given
        m = Map()
        m.create_feature_group("A")

        # Act - When
        result = m.add_layer_control(collapsed=True, position="bottomleft")

        # Assert - Then
        assert result is m


# ===================================================================
# Scenarios for adding GeoJSON data layers.
# ===================================================================


class TestHeatmap:
    """Scenarios for heatmap layers."""

    def test_heatmap_from_shapely_points(self) -> None:
        """
        Scenario: Create a heatmap from Shapely Point objects.

        Given: An empty map and a list of 10 Points
        When: add_heatmap is called with the points
        Then: A heatmap layer is added and bounds are tracked
        """
        # Arrange - Given
        m = Map()
        points = [Point(4.85 + i * 0.01, 52.35 + i * 0.005) for i in range(10)]

        # Act - When
        result = m.add_heatmap(points)

        # Assert - Then
        assert result is m, "add_heatmap should return self"
        assert len(m._bounds) == 20, "Each location should add 2 bound entries"

    def test_heatmap_from_tuples(self) -> None:
        """
        Scenario: Create a heatmap from (lat, lon) tuples.

        Given: An empty map and raw coordinate tuples
        When: add_heatmap is called with the tuples
        Then: The heatmap is created from the tuple coordinates
        """
        # Arrange - Given
        m = Map()
        tuples = [(52.37, 4.9), (52.38, 4.95), (52.36, 4.85)]

        # Act - When
        m.add_heatmap(tuples)

        # Assert - Then
        assert len(m._bounds) == 3, "Each tuple should add 1 bound entry"

    def test_heatmap_with_intensity_weights(self) -> None:
        """
        Scenario: Create a heatmap with weighted intensities.

        Given: An empty map and (lat, lon, intensity) triples
        When: add_heatmap is called with the weighted data
        Then: The heatmap uses the intensity values
        """
        # Arrange - Given
        m = Map()
        weighted = [(52.37, 4.9, 1.0), (52.38, 4.95, 0.3), (52.36, 4.85, 0.7)]

        # Act - When
        m.add_heatmap(weighted)

        # Assert - Then
        assert len(m._bounds) == 3, "Weighted triples should track bounds"

    def test_heatmap_with_custom_style(self) -> None:
        """
        Scenario: Configure heatmap appearance with custom gradient.

        Given: An empty map and a HeatmapStyle with a blue-to-red gradient
        When: add_heatmap is called with the style
        Then: The heatmap uses the custom configuration
        """
        # Arrange - Given
        m = Map()
        style = HeatmapStyle(
            radius=25,
            blur=20,
            gradient={0.4: "blue", 0.65: "lime", 1.0: "red"},
        )
        points = [Point(4.9, 52.37)]

        # Act - When
        m.add_heatmap(points, style=style)

        # Assert - Then
        assert len(m._bounds) == 2, "Heatmap location should be tracked"

    def test_heatmap_with_layer_name(self) -> None:
        """
        Scenario: Create a named heatmap layer for layer control.

        Given: An empty map and some points
        When: add_heatmap is called with name="Activity"
        Then: The heatmap layer is named and can be toggled
        """
        # Arrange - Given
        m = Map()
        points = [Point(4.9, 52.37), Point(4.95, 52.38)]

        # Act - When
        result = m.add_heatmap(points, name="Activity")

        # Assert - Then
        assert result is m


# ===================================================================
# Scenarios for clustered markers.
# ===================================================================


class TestMarkerCluster:
    """Scenarios for clustered markers."""

    def test_cluster_groups_nearby_markers(self) -> None:
        """
        Scenario: Cluster 50 café markers that expand on zoom.

        Given: An empty map and 50 Points near Amsterdam center
        When: add_marker_cluster is called with labels and hovers
        Then: All points are added and the cluster layer is on the map
        """
        # Arrange - Given
        m = Map()
        cafes = [Point(4.88 + i * 0.001, 52.36 + i * 0.0005) for i in range(50)]
        labels = ["☕"] * 50
        hovers = [f"**Café #{i + 1}**" for i in range(50)]

        # Act - When
        result = m.add_marker_cluster(cafes, labels=labels, hovers=hovers, name="Cafés")

        # Assert - Then
        assert result is m, "add_marker_cluster should return self"
        assert len(m._bounds) == 100, "50 points x 2 bound entries each"

    def test_cluster_without_labels(self) -> None:
        """
        Scenario: Create a cluster with default icon markers.

        Given: An empty map and a list of Points with no labels
        When: add_marker_cluster is called without labels
        Then: Default Folium icons are used
        """
        # Arrange - Given
        m = Map()
        points = [Point(4.9 + i * 0.01, 52.37) for i in range(5)]

        # Act - When
        m.add_marker_cluster(points)

        # Assert - Then
        assert len(m._bounds) == 10, "5 points should track 10 bound entries"

    def test_cluster_with_popups(self) -> None:
        """
        Scenario: Clustered markers with click popups.

        Given: An empty map and points with popup text
        When: add_marker_cluster is called with popups
        Then: All markers have popups configured
        """
        # Arrange - Given
        m = Map()
        points = [Point(4.9, 52.37), Point(4.95, 52.38)]
        popups = ["# Popup A\nDetails A", "# Popup B\nDetails B"]

        # Act - When
        result = m.add_marker_cluster(points, popups=popups)

        # Assert - Then
        assert result is m
        assert len(m._bounds) == 4

    def test_cluster_with_named_layer(self) -> None:
        """
        Scenario: Cluster with a named layer for the layer control.

        Given: An empty map
        When: add_marker_cluster is called with name="Sensors"
        Then: The cluster layer is named
        """
        # Arrange - Given
        m = Map()
        points = [Point(4.9, 52.37)]

        # Act - When
        m.add_marker_cluster(points, name="Sensors")

        # Assert - Then
        assert len(m._bounds) == 2

    def test_cluster_with_captions_and_default_icons(self) -> None:
        """
        Scenario: Marker cluster with captions but no emoji labels.

        Given: An empty map and points with captions only (no labels/emoji)
        When: add_marker_cluster is called with captions but without labels
        Then: A single DivIcon marker per location combines the icon glyph and marker
        """
        # Arrange - Given
        m = Map()
        points = [Point(4.9, 52.37), Point(4.95, 52.38)]

        # Act - When
        result = m.add_marker_cluster(points, captions=["S-01", "S-02"])

        # Assert - Then
        assert result is m
        html = m.to_html()
        assert "S-01" in html, "Text marker should appear in the HTML output"
        assert "S-02" in html, "Text marker should appear in the HTML output"
        # Verify the icon glyph is rendered inline (single DivIcon, not folium.Icon)
        assert "glyphicon glyphicon-arrow-down" in html, "Icon glyph should be rendered as HTML"


# ===================================================================
# Scenarios for placing text labels on the map.
# ===================================================================


class TestTextAnnotation:
    """Scenarios for placing text labels on the map."""

    def test_add_text_from_shapely_point(self) -> None:
        """
        Scenario: Place a neighbourhood marker using a Shapely Point.

        Given: An empty map and a Point for the marker location
        When: add_text is called with a CSS style dict
        Then: The text appears at the coordinate and bounds are tracked
        """
        # Arrange - Given
        m = Map()
        location = Point(4.9041, 52.3676)
        style = {"font-size": "16px", "color": "#2c3e50"}

        # Act - When
        result = m.add_text(location, "Amsterdam Centrum", style=style)

        # Assert - Then
        assert result is m, "add_text should return self"
        assert len(m._bounds) == 2, "Text location should be tracked"

    def test_add_text_from_tuple(self) -> None:
        """
        Scenario: Place a text marker using a (lat, lon) tuple.

        Given: An empty map and a (lat, lon) tuple
        When: add_text is called with the tuple
        Then: The marker is placed at the correct location
        """
        # Arrange - Given
        m = Map()

        # Act - When
        m.add_text((52.37, 4.9), "Label here")

        # Assert - Then
        assert (52.37, 4.9) in m._bounds, "Tuple location should be tracked directly"

    def test_add_text_with_transparent_background(self) -> None:
        """
        Scenario: Place floating text without a background box.

        Given: An empty map and a CSS dict with no background or border
        When: add_text is called with that style
        Then: The text appears without visual chrome
        """
        # Arrange - Given
        m = Map()
        style = {
            "font-size": "14px",
            "color": "red",
            "background-color": "transparent",
            "border": "none",
        }

        # Act - When
        m.add_text((52.37, 4.9), "Floating", style=style)

        # Assert - Then
        assert len(m._bounds) == 1, "One tuple adds one bound entry"

    def test_add_text_with_hover(self) -> None:
        """
        Scenario: A text marker with an additional tooltip tooltip.

        Given: An empty map
        When: add_text is called with both text and tooltip
        Then: The marker has text visible and tooltip on mouse-over
        """
        # Arrange - Given
        m = Map()

        # Act - When
        result = m.add_text(
            Point(4.9, 52.37),
            "Station A",
            hover="**Click for details**",
        )

        # Assert - Then
        assert result is m
        assert len(m._bounds) == 2


# ===================================================================
# Scenarios for CRS detection and transformation.
# ===================================================================


class TestZoomDependentVisibility:
    """Scenarios for min_zoom marker visibility control."""

    def test_add_point_with_min_zoom(self) -> None:
        """
        Scenario: Point with min_zoom is tracked.

        Given: A Map
        When: add_point is called with min_zoom=10
        Then: The marker is tracked in _zoom_controlled_markers
        """
        m = Map()
        m.add_point(Point(4.9, 52.37), min_zoom=10)
        assert len(m._zoom_controlled_markers) == 1
        assert m._zoom_controlled_markers[0]["min_zoom"] == 10

    def test_add_point_without_min_zoom(self) -> None:
        """
        Scenario: Point without min_zoom is not tracked.

        Given: A Map
        When: add_point is called without min_zoom
        Then: _zoom_controlled_markers is empty
        """
        m = Map()
        m.add_point(Point(4.9, 52.37))
        assert len(m._zoom_controlled_markers) == 0

    def test_min_zoom_zero_ignored(self) -> None:
        """
        Scenario: min_zoom=0 is treated as "always visible".

        Given: A Map
        When: add_point is called with min_zoom=0
        Then: The marker is NOT tracked
        """
        m = Map()
        m.add_point(Point(4.9, 52.37), min_zoom=0)
        assert len(m._zoom_controlled_markers) == 0

    def test_min_zoom_none_ignored(self) -> None:
        """
        Scenario: min_zoom=None is treated as "always visible".

        Given: A Map
        When: add_point is called with min_zoom=None
        Then: The marker is NOT tracked
        """
        m = Map()
        m.add_point(Point(4.9, 52.37), min_zoom=None)
        assert len(m._zoom_controlled_markers) == 0

    def test_add_circle_with_min_zoom(self) -> None:
        """
        Scenario: Circle with min_zoom is tracked.

        Given: A Map
        When: add_circle is called with min_zoom=12
        Then: The marker is tracked
        """
        m = Map()
        m.add_circle(Point(4.9, 52.37), min_zoom=12)
        assert len(m._zoom_controlled_markers) == 1
        assert m._zoom_controlled_markers[0]["min_zoom"] == 12

    def test_add_text_with_min_zoom(self) -> None:
        """
        Scenario: Text with min_zoom is tracked.

        Given: A Map
        When: add_text is called with min_zoom=8
        Then: The marker is tracked
        """
        m = Map()
        m.add_text((52.37, 4.9), "Hello", min_zoom=8)
        assert len(m._zoom_controlled_markers) == 1
        assert m._zoom_controlled_markers[0]["min_zoom"] == 8

    def test_add_marker_cluster_with_min_zoom(self) -> None:
        """
        Scenario: Marker cluster with min_zoom is tracked.

        Given: A Map
        When: add_marker_cluster is called with min_zoom=5
        Then: The cluster is tracked
        """
        m = Map()
        m.add_marker_cluster([Point(4.9, 52.37), Point(5.0, 52.38)], min_zoom=5)
        assert len(m._zoom_controlled_markers) == 1
        assert m._zoom_controlled_markers[0]["min_zoom"] == 5

    def test_zoom_js_present_in_html(self) -> None:
        """
        Scenario: Zoom JS is injected when min_zoom markers exist.

        Given: A Map with a min_zoom marker
        When: _get_html is called
        Then: The HTML contains the zoom JavaScript
        """
        m = Map()
        m.add_point(Point(4.9, 52.37), min_zoom=10)
        html = m._get_html()
        assert "zoomend" in html
        assert "minZoom" in html

    def test_zoom_js_absent_when_not_used(self) -> None:
        """
        Scenario: No zoom JS when no min_zoom markers.

        Given: A Map with no min_zoom markers
        When: _get_html is called
        Then: The HTML does NOT contain the zoom JavaScript
        """
        m = Map()
        m.add_point(Point(4.9, 52.37))
        html = m._get_html()
        assert "zoomend" not in html

    def test_zoom_js_injected_only_once(self) -> None:
        """
        Scenario: Repeated _get_html calls inject JS only once.

        Given: A Map with a min_zoom marker
        When: _get_html is called twice
        Then: The flag _zoom_js_injected is True and JS appears only once
        """
        m = Map()
        m.add_point(Point(4.9, 52.37), min_zoom=10)
        html1 = m._get_html()
        html2 = m._get_html()
        assert m._zoom_js_injected is True
        assert html1.count("zoomend") == html2.count("zoomend")

    def test_merge_combines_zoom_markers(self) -> None:
        """
        Scenario: Merging maps combines zoom-controlled markers.

        Given: Map A with 1 zoom marker and Map B with 1 zoom marker
        When: A + B
        Then: Combined has 2 zoom markers
        """
        a = Map()
        a.add_point(Point(4.9, 52.37), min_zoom=10)

        b = Map()
        b.add_point(Point(5.0, 52.38), min_zoom=12)

        combined = a + b
        assert len(combined._zoom_controlled_markers) == 2


# ===================================================================
# Scenarios for set_bounds.
# ===================================================================
