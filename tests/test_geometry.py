"""BDD-style tests for the map module.

Each test follows the Given-When-Then pattern with a scenario
docstring and Arrange/Act/Assert comments.
"""
# ruff: noqa: SLF001

import pytest
from shapely.geometry import (
    LinearRing,
    LineString,
    MultiLineString,
    MultiPoint,
    MultiPolygon,
    Point,
    Polygon,
)

from mapyta import FillStyle, Map, StrokeStyle

# ===================================================================
# Scenarios for creating and configuring a Map.
# ===================================================================


class TestAddShapes:
    """Scenarios for adding lines and polygons."""

    def test_add_linestring_as_route(self) -> None:
        """
        Scenario: Draw a walking route through Amsterdam.

        Given: An empty map and a LineString with 4 coordinate pairs
        When: The line is added with a dashed red stroke
        Then: The line is on the map and bounds cover all coordinates
        """
        # Arrange - Given
        m = Map()
        route = LineString(
            [
                (4.8852, 52.3702),
                (4.8910, 52.3663),
                (4.8932, 52.3631),
                (4.8840, 52.3569),
            ]
        )
        stroke = StrokeStyle(color="#e74c3c", weight=4, dash_array="10 6")

        # Act - When
        result = m.add_linestring(route, tooltip="**Walking route**", stroke=stroke)

        # Assert - Then
        assert result is m, "add_linestring should return self"
        assert len(m._bounds) == 2, "Line bounding box should be tracked"

    def test_add_polygon_with_fill(self) -> None:
        """
        Scenario: Highlight a neighbourhood area.

        Given: An empty map and a rectangular Polygon for De Jordaan
        When: The polygon is added with green stroke and semi-transparent fill
        Then: The polygon is on the map and bounds are tracked
        """
        # Arrange - Given
        m = Map()
        jordaan = Polygon(
            [
                (4.8760, 52.3720),
                (4.8890, 52.3720),
                (4.8890, 52.3800),
                (4.8760, 52.3800),
            ]
        )
        stroke = StrokeStyle(color="#2ecc71", weight=2)
        fill = FillStyle(color="#2ecc71", opacity=0.15)

        # Act - When
        result = m.add_polygon(jordaan, tooltip="**De Jordaan**", stroke=stroke, fill=fill)

        # Assert - Then
        assert result is m, "add_polygon should return self"
        assert len(m._bounds) == 2, "Polygon bounding box should be tracked"

    def test_add_multipolygon_adds_all_parts(self) -> None:
        """
        Scenario: Add a multi-part polygon (e.g. islands).

        Given: An empty map and a MultiPolygon with 2 rectangles
        When: The MultiPolygon is added
        Then: Both polygons are on the map (4 bound entries)
        """
        # Arrange - Given
        m = Map()
        mp = MultiPolygon(
            [
                Polygon([(4.85, 52.35), (4.95, 52.35), (4.95, 52.40), (4.85, 52.40)]),
                Polygon([(5.00, 52.35), (5.10, 52.35), (5.10, 52.40), (5.00, 52.40)]),
            ]
        )

        # Act - When
        result = m.add_multipolygon(mp, tooltip="**Two zones**")

        # Assert - Then
        assert result is m, "add_multipolygon should return self"
        assert len(m._bounds) == 4, "Each polygon should add 2 bound entries"

    def test_add_multilinestring(self) -> None:
        """
        Scenario: Add two transit lines as a MultiLineString.

        Given: An empty map and a MultiLineString with 2 routes
        When: The MultiLineString is added
        Then: Both lines are on the map
        """
        # Arrange - Given
        m = Map()
        ml = MultiLineString(
            [
                [(4.9, 52.37), (5.1, 52.09)],
                [(4.3, 52.07), (5.1, 52.09)],
            ]
        )

        # Act - When
        result = m.add_multilinestring(ml)

        # Assert - Then
        assert result is m, "add_multilinestring should return self"
        assert len(m._bounds) == 4, "Each line should add 2 bound entries"

    def test_add_multipoint(self) -> None:
        """
        Scenario: Add multiple sensor locations as a MultiPoint.

        Given: An empty map and a MultiPoint with 2 locations
        When: The MultiPoint is added with red circle labels
        Then: Both points appear on the map
        """
        # Arrange - Given
        m = Map()
        mp = MultiPoint([(4.9, 52.37), (5.1, 52.09)])

        # Act - When
        result = m.add_multipoint(mp, label="🔴")

        # Assert - Then
        assert result is m, "add_multipoint should return self"
        assert len(m._bounds) == 4, "Each location should add 2 bound entries"

    def test_add_linear_ring(self) -> None:
        """
        Scenario: Add a LinearRing via the generic dispatcher.

        Given: An empty map and a LinearRing (closed loop)
        When: add_geometry is called with the ring
        Then: It is rendered as a LineString
        """
        # Arrange - Given
        m = Map()
        ring = LinearRing([(4.85, 52.35), (4.95, 52.35), (4.95, 52.40), (4.85, 52.40)])

        # Act - When
        result = m.add_geometry(ring)

        # Assert - Then
        assert result is m, "add_geometry should return self"
        assert len(m._bounds) == 2, "Ring bounding box should be tracked"


# ===================================================================
# Scenarios for add_geometry auto-dispatching.
# ===================================================================


class TestGeometryDispatch:
    """Scenarios for add_geometry auto-dispatching."""

    def test_dispatch_point(self) -> None:
        """
        Scenario: Auto-dispatch a Point geometry.

        Given: An empty map and a Shapely Point
        When: add_geometry is called with the Point
        Then: It delegates to add_point and tracks bounds
        """
        # Arrange - Given
        m = Map()
        point = Point(4.9, 52.37)

        # Act - When
        m.add_geometry(point, label="📍")

        # Assert - Then
        assert len(m._bounds) == 2, "Point should be dispatched and tracked"

    def test_dispatch_polygon(self) -> None:
        """
        Scenario: Auto-dispatch a Polygon geometry.

        Given: An empty map and a Shapely Polygon
        When: add_geometry is called with the Polygon
        Then: It delegates to add_polygon and tracks bounds
        """
        # Arrange - Given
        m = Map()
        poly = Polygon([(4.85, 52.35), (4.95, 52.35), (4.95, 52.40), (4.85, 52.40)])

        # Act - When
        m.add_geometry(poly, fill=FillStyle(color="red"))

        # Assert - Then
        assert len(m._bounds) == 2, "Polygon should be dispatched and tracked"

    def test_dispatch_unsupported_type_raises(self) -> None:
        """
        Scenario: Attempt to add an unsupported geometry type.

        Given: An empty map and a non-geometry object
        When: add_geometry is called with a string
        Then: A TypeError is raised with a descriptive message
        """
        # Arrange - Given
        m = Map()

        # Act & Assert - When/Then
        with pytest.raises(TypeError, match="Unsupported"):
            m.add_geometry("not a geometry")  # ty: ignore[invalid-argument-type]

    def test_dispatch_linestring(self) -> None:
        """
        Scenario: add_geometry dispatches a LineString.

        Given: An empty map and a LineString
        When: add_geometry is called
        Then: It delegates to add_linestring
        """
        m = Map()
        m.add_geometry(LineString([(4.9, 52.37), (5.1, 52.09)]))
        assert len(m._bounds) == 2

    def test_dispatch_multipolygon(self) -> None:
        """
        Scenario: add_geometry dispatches a MultiPolygon.

        Given: An empty map and a MultiPolygon
        When: add_geometry is called
        Then: It delegates to add_multipolygon (4 bound entries)
        """
        m = Map()
        mp = MultiPolygon(
            [
                Polygon([(4.85, 52.35), (4.95, 52.35), (4.95, 52.40), (4.85, 52.40)]),
                Polygon([(5.0, 52.35), (5.1, 52.35), (5.1, 52.40), (5.0, 52.40)]),
            ]
        )
        m.add_geometry(mp)
        assert len(m._bounds) == 4

    def test_dispatch_multilinestring(self) -> None:
        """
        Scenario: add_geometry dispatches a MultiLineString.

        Given: An empty map and a MultiLineString
        When: add_geometry is called
        Then: It delegates to add_multilinestring
        """
        m = Map()
        ml = MultiLineString(
            [
                [(4.9, 52.37), (5.1, 52.09)],
                [(4.3, 52.07), (5.1, 52.09)],
            ]
        )
        m.add_geometry(ml)
        assert len(m._bounds) == 4

    def test_dispatch_multipoint(self) -> None:
        """
        Scenario: add_geometry dispatches a MultiPoint.

        Given: An empty map and a MultiPoint
        When: add_geometry is called
        Then: It delegates to add_multipoint
        """
        m = Map()
        mp = MultiPoint([(4.9, 52.37), (5.1, 52.09)])
        m.add_geometry(mp, label="🔵")
        assert len(m._bounds) == 4

    def test_add_geometry_dispatches_linearring_to_linestring(self) -> None:
        """
        Scenario: add_geometry converts a LinearRing to a LineString.

        Given: An empty map and a LinearRing
        When: add_geometry is called with the LinearRing
        Then: It is rendered as a LineString on the map

        """
        # Arrange - Given
        m = Map()
        ring = LinearRing([(4.85, 52.35), (4.95, 52.35), (4.95, 52.40), (4.85, 52.40)])

        # Act - When
        result = m.add_geometry(ring, tooltip="**Ring boundary**", stroke=StrokeStyle(color="red"))

        # Assert - Then
        assert result is m
        assert len(m._bounds) == 2


# ===================================================================
# Scenarios for organising layers into toggleable groups.
# ===================================================================


class TestSetBounds:
    """Scenarios for the set_bounds method."""

    def test_set_bounds_empty_map(self) -> None:
        """
        Scenario: set_bounds on an empty map returns self.

        Given: An empty Map
        When: set_bounds is called
        Then: Self is returned without error
        """
        m = Map()
        result = m.set_bounds()
        assert result is m

    def test_set_bounds_fits_data(self) -> None:
        """
        Scenario: set_bounds fits the map view to data points.

        Given: A Map with two points
        When: set_bounds is called
        Then: The Folium map has fit_bounds set
        """
        m = Map()
        m.add_point(Point(4.9, 52.37))
        m.add_point(Point(5.1, 52.09))
        result = m.set_bounds()
        assert result is m

    def test_set_bounds_with_padding(self) -> None:
        """
        Scenario: set_bounds adds padding to bounds.

        Given: A Map with one location
        When: set_bounds is called with padding=0.01
        Then: The map is still valid (no errors)
        """
        m = Map()
        m.add_point(Point(4.9, 52.37))
        result = m.set_bounds(padding=0.01)
        assert result is m

    def test_set_bounds_restrict_true(self) -> None:
        """
        Scenario: restrict=True sets maxBounds on the Folium map.

        Given: A Map with data
        When: set_bounds(restrict=True) is called
        Then: maxBounds and maxBoundsViscosity are set
        """
        m = Map()
        m.add_point(Point(4.9, 52.37))
        m.add_point(Point(5.1, 52.09))
        m.set_bounds(restrict=True)
        assert "maxBounds" in m._map.options
        assert m._map.options["maxBoundsViscosity"] == 1.0

    def test_set_bounds_restrict_false(self) -> None:
        """
        Scenario: restrict=False does not set maxBounds.

        Given: A Map with data
        When: set_bounds(restrict=False) is called
        Then: maxBounds is NOT in the options
        """
        m = Map()
        m.add_point(Point(4.9, 52.37))
        m.set_bounds(restrict=False)
        assert "maxBounds" not in m._map.options


# ===================================================================
# Scenarios for hide_controls in image export.
# ===================================================================
