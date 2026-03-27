"""BDD-style tests for the map module.

Each test follows the Given-When-Then pattern with a scenario
docstring and Arrange/Act/Assert comments.
"""
# ruff: noqa: SLF001

from pathlib import Path

from shapely.geometry import LineString, Point, Polygon

from mapyta import Map

# ===================================================================
# Scenarios for combining two maps with the + operator.
# ===================================================================


class TestMapMerge:
    """Scenarios for combining two maps with the + operator."""

    def test_merge_two_maps_preserves_left_title(self) -> None:
        """
        Scenario: Merge two maps using the + operator.

        Given: Map A titled "Sites" with one location, and map B with one polygon
        When: A + B is computed
        Then: The result has A's title and contains both geometries
        """
        # Arrange - Given
        a = Map(title="Sites")
        a.add_point(Point(4.9, 52.37), marker="📍")

        b = Map()
        b.add_polygon(Polygon([(4.85, 52.35), (4.95, 52.35), (4.95, 52.40), (4.85, 52.40)]))

        # Act - When
        combined = a + b

        # Assert - Then
        assert combined._title == "Sites", "Left map's title should be preserved"
        assert len(combined._bounds) == 4, "Both geometries should contribute bounds"

    def test_merge_combines_feature_groups(self) -> None:
        """
        Scenario: Merging maps combines their feature group registries.

        Given: Map A with group "Roads" and map B with group "Buildings"
        When: A + B is computed
        Then: The merged map has both "Roads" and "Buildings"
        """
        # Arrange - Given
        a = Map(title="A")
        a.create_feature_group("Roads")
        a.add_linestring(LineString([(4.9, 52.37), (5.0, 52.38)]))

        b = Map()
        b.create_feature_group("Buildings")
        b.add_polygon(Polygon([(4.85, 52.35), (4.95, 52.35), (4.95, 52.40), (4.85, 52.40)]))

        # Act - When
        combined = a + b

        # Assert - Then
        assert "Roads" in combined._feature_groups
        assert "Buildings" in combined._feature_groups

    def test_merge_combines_colormaps(self) -> None:
        """
        Scenario: Merging maps combines their colormap legends.

        Given: Map A with a choropleth and map B with another choropleth
        When: A + B is computed
        Then: The merged map has both colormaps
        """
        # Arrange - Given
        geojson_a = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"name": "X", "val": 10},
                    "geometry": {"type": "Polygon", "coordinates": [[(4.85, 52.35), (4.90, 52.35), (4.90, 52.38), (4.85, 52.38), (4.85, 52.35)]]},
                }
            ],
        }
        geojson_b = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"name": "Y", "val": 90},
                    "geometry": {"type": "Polygon", "coordinates": [[(4.90, 52.35), (4.95, 52.35), (4.95, 52.38), (4.90, 52.38), (4.90, 52.35)]]},
                }
            ],
        }

        a = Map()
        a.add_choropleth(geojson_a, value_column="val", key_on="feature.properties.name")

        b = Map()
        b.add_choropleth(geojson_b, value_column="val", key_on="feature.properties.name")

        # Act - When
        combined = a + b

        # Assert - Then
        assert len(combined._colormaps) == 2, "Both colormaps should be preserved"

    def test_merge_combines_bounds(self) -> None:
        """
        Scenario: Merging maps combines their bounds for auto-fit.

        Given: Map A with a location in Amsterdam, map B with a location in Rotterdam
        When: A + B is computed
        Then: The bounds cover both cities
        """
        # Arrange - Given
        a = Map()
        a.add_point(Point(4.9, 52.37))  # Amsterdam

        b = Map()
        b.add_point(Point(4.48, 51.92))  # Rotterdam

        # Act - When
        combined = a + b

        # Assert - Then
        assert len(combined._bounds) == 4, "Both points' bounds should be combined"


# ===================================================================
# Scenarios for the fluent API.
# ===================================================================


class TestMethodChaining:
    """Scenarios for the fluent API."""

    def test_full_chain_produces_html(self, tmp_path: Path) -> None:
        """
        Scenario: Build a complete map in a single chained expression.

        Given: Nothing
        When: A map is built using chained add_* calls ending with to_html
        Then: The resulting HTML file exists on disk
        """
        # Act - When
        out = (
            Map(title="Chained")
            .add_point(Point(4.9, 52.37), marker="📍")
            .add_circle(Point(5.1, 52.09), tooltip="Circle")
            .add_linestring(LineString([(4.9, 52.37), (5.1, 52.09)]))
            .add_polygon(Polygon([(4.85, 52.35), (4.95, 52.35), (4.95, 52.40), (4.85, 52.40)]))
            .add_text((52.3, 4.9), "Label")
            .create_feature_group("Layer 1")
            .add_point(Point(4.3, 52.07), marker="🔴")
            .reset_target()
            .add_layer_control()
            .to_html(tmp_path / "chained.html")
        )

        # Assert - Then
        assert out.exists(), "Chained call should produce a valid HTML file"
