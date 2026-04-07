"""BDD-style tests for the map module.

Each test follows the Given-When-Then pattern with a scenario
docstring and Arrange/Act/Assert comments.
"""
# ruff: noqa: SLF001

import folium
import pytest
from shapely import GeometryCollection, LinearRing, LineString, MultiLineString, MultiPoint, MultiPolygon, Point, Polygon

from mapyta import Map, MapConfig, PopupStyle, StrokeStyle
from mapyta.coordinates import detect_and_transform_coords, transform_geometry
from mapyta.markdown import RawHTML, markdown_to_html, sanitize_href
from mapyta.style import resolve_style
from mapyta.tiles import TILE_PROVIDERS

# ===================================================================
# Scenarios for creating and configuring a Map.
# ===================================================================


class TestCoordinateTransformation:
    """Scenarios for CRS detection and transformation."""

    def test_wgs84_coordinates_pass_through(self) -> None:
        """
        Scenario: WGS84 coordinates are left unchanged.

        Given: Coordinates already in WGS84 (small lon/lat values)
        When: _detect_and_transform_coords is called without source_crs
        Then: The coordinates are returned unchanged
        """
        # Arrange - Given
        coords = [(4.9, 52.37), (5.1, 52.09)]

        # Act - When
        result = detect_and_transform_coords(coords)  # ty: ignore[invalid-argument-type]

        # Assert - Then
        assert result == coords, "WGS84 coords should pass through unchanged"

    def test_rd_new_auto_detection(self) -> None:
        """
        Scenario: RD New coordinates are auto-detected and transformed.

        Given: Coordinates in the RD New range (x: 0-300k, y: 300k-625k)
        When: _detect_and_transform_coords is called without source_crs
        Then: The coordinates are transformed to WGS84 (near Amsterdam)
        """
        # Arrange - Given
        coords_rd = [(121_000, 487_000)]

        # Act - When
        result = detect_and_transform_coords(coords_rd)  # ty: ignore[invalid-argument-type]

        # Assert - Then
        lon, lat = result[0]
        assert 4.5 < lon < 5.5, f"Longitude {lon} should be near Amsterdam"
        assert 52.0 < lat < 53.0, f"Latitude {lat} should be near Amsterdam"

    def test_explicit_crs_transforms_correctly(self) -> None:
        """
        Scenario: Explicit EPSG:28992 CRS forces transformation.

        Given: Coordinates and an explicit source_crs="EPSG:28992"
        When: _detect_and_transform_coords is called
        Then: The coordinates are transformed to WGS84
        """
        # Arrange - Given
        coords = [(155_000, 463_000)]

        # Act - When
        result = detect_and_transform_coords(coords, source_crs="EPSG:28992")  # ty: ignore[invalid-argument-type]

        # Assert - Then
        lon, lat = result[0]
        assert 5.0 < lon < 6.0, "Should be in the Netherlands"
        assert 51.5 < lat < 53.0, "Should be in the Netherlands"

    def test_transform_point_geometry(self) -> None:
        """
        Scenario: Transform a Shapely Point from RD New to WGS84.

        Given: A Point in RD New coordinates
        When: _transform_geometry is called with EPSG:28992
        Then: The returned Point has WGS84 coordinates
        """
        # Arrange - Given
        pt = Point(155_000, 463_000)

        # Act - When
        result = transform_geometry(pt, "EPSG:28992")

        # Assert - Then
        assert isinstance(result, Point), "Should return a Point"
        assert 5.0 < result.x < 6.0, "Longitude should be in NL range"
        assert 51.5 < result.y < 53.0, "Latitude should be in NL range"

    def test_transform_polygon_geometry(self) -> None:
        """
        Scenario: Transform a Polygon from RD New to WGS84.

        Given: A rectangular Polygon in RD New coordinates
        When: _transform_geometry is called
        Then: The centroid of the result is in the Netherlands
        """
        # Arrange - Given
        poly = Polygon(
            [
                (155_000, 463_000),
                (156_000, 463_000),
                (156_000, 464_000),
                (155_000, 464_000),
            ]
        )

        # Act - When
        result = transform_geometry(poly, "EPSG:28992")

        # Assert - Then
        cx, cy = result.centroid.x, result.centroid.y
        assert 3.0 < cx < 8.0, "Centroid longitude should be in NL"
        assert 50.0 < cy < 54.0, "Centroid latitude should be in NL"

    def test_empty_coords_returns_empty(self) -> None:
        """
        Scenario: Transform an empty coordinate list.

        Given: An empty list of coordinates
        When: _detect_and_transform_coords is called
        Then: An empty list is returned
        """
        # Act & Assert
        assert detect_and_transform_coords([]) == []

    def test_rd_point_on_geomap_lands_in_netherlands(self) -> None:
        """
        Scenario: Add an RD New location to a map and verify placement.

        Given: A Map and a Point in RD New coordinates (Amsterdam)
        When: The location is added to the map
        Then: The tracked bounds are in the WGS84 Netherlands range
        """
        # Arrange - Given
        m = Map()
        rd_point = Point(121_000, 487_000)

        # Act - When
        m.add_point(rd_point, marker="📍")

        # Assert - Then
        lat, lon = m._bounds[0]
        assert 50.0 < lat < 54.0, "Latitude should be in the Netherlands"
        assert 3.0 < lon < 8.0, "Longitude should be in the Netherlands"

    def test_explicit_wgs84_passes_through(self) -> None:
        """
        Scenario: Explicitly passing EPSG:4326 does not transform.

        Given: WGS84 coordinates and source_crs="EPSG:4326"
        When: _detect_and_transform_coords is called
        Then: The coordinates are returned unchanged
        """
        # Arrange - Given
        coords = [(4.9, 52.37)]

        # Act - When
        result = detect_and_transform_coords(coords, source_crs="EPSG:4326")  # ty: ignore[invalid-argument-type]

        # Assert - Then
        assert result == coords, "EPSG:4326 should pass through unchanged"

    def test_transform_linestring_geometry(self) -> None:
        """
        Scenario: Transform a LineString from RD New to WGS84.

        Given: A LineString in RD New coordinates
        When: _transform_geometry is called with EPSG:28992
        Then: The returned LineString has WGS84 coordinates
        """
        # Arrange - Given
        line = LineString([(155_000, 463_000), (156_000, 464_000)])

        # Act - When
        result = transform_geometry(line, "EPSG:28992")

        # Assert - Then
        assert isinstance(result, LineString), "Should return a LineString"
        coords = list(result.coords)
        assert 3.0 < coords[0][0] < 8.0, "Longitude should be in NL"

    def test_transform_multilinestring_geometry(self) -> None:
        """
        Scenario: Transform a MultiLineString from RD New to WGS84.

        Given: A MultiLineString in RD New coordinates
        When: _transform_geometry is called
        Then: All constituent lines are transformed
        """
        # Arrange - Given
        ml = MultiLineString(
            [
                [(155_000, 463_000), (156_000, 464_000)],
                [(157_000, 465_000), (158_000, 466_000)],
            ]
        )

        # Act - When
        result = transform_geometry(ml, "EPSG:28992")

        # Assert - Then
        assert isinstance(result, MultiLineString)
        assert len(list(result.geoms)) == 2

    def test_transform_multipolygon_geometry(self) -> None:
        """
        Scenario: Transform a MultiPolygon from RD New to WGS84.

        Given: A MultiPolygon with two rectangles in RD New
        When: _transform_geometry is called
        Then: Both polygons have WGS84 coordinates
        """
        # Arrange - Given
        mp = MultiPolygon(
            [
                Polygon([(155_000, 463_000), (156_000, 463_000), (156_000, 464_000), (155_000, 464_000)]),
                Polygon([(160_000, 465_000), (161_000, 465_000), (161_000, 466_000), (160_000, 466_000)]),
            ]
        )

        # Act - When
        result = transform_geometry(mp, "EPSG:28992")

        # Assert - Then
        assert isinstance(result, MultiPolygon)
        for poly in result.geoms:
            cx = poly.centroid.x
            assert 3.0 < cx < 8.0, f"Centroid lon {cx} should be in NL"

    def test_transform_linearring_geometry(self) -> None:
        """
        Scenario: Transform a LinearRing from RD New to WGS84.

        Given: A LinearRing in RD New coordinates
        When: _transform_geometry is called
        Then: The result has WGS84 coordinates (may degrade to LineString
              due to floating-location rounding in the transform)
        """
        # Arrange - Given
        ring = LinearRing(
            [
                (155_000, 463_000),
                (156_000, 463_000),
                (156_000, 464_000),
                (155_000, 464_000),
            ]
        )

        # Act - When
        result = transform_geometry(ring, "EPSG:28992")

        # Assert - Then
        assert isinstance(result, LinearRing | LineString), "Should be ring or line"
        coords = list(result.coords)
        assert 3.0 < coords[0][0] < 8.0, "Longitude should be in NL range"

    def test_transform_polygon_with_hole(self) -> None:
        """
        Scenario: Transform a polygon that has an interior ring (hole).

        Given: A Polygon in RD New with one hole
        When: _transform_geometry is called
        Then: Both exterior and interior rings are transformed
        """
        # Arrange - Given
        exterior = [(155_000, 463_000), (157_000, 463_000), (157_000, 465_000), (155_000, 465_000)]
        hole = [(155_500, 463_500), (156_500, 463_500), (156_500, 464_500), (155_500, 464_500)]
        poly = Polygon(exterior, [hole])

        # Act - When
        result = transform_geometry(poly, "EPSG:28992")

        # Assert - Then
        assert isinstance(result, Polygon)
        assert len(list(result.interiors)) == 1, "Hole should be preserved"
        hole_coords = list(result.interiors[0].coords)
        assert 3.0 < hole_coords[0][0] < 8.0, "Hole should also be transformed"

    def test_unsupported_geometry_returns_unchanged(self) -> None:
        """
        Scenario: An unrecognized geometry type passes through unchanged.

        Given: A geometry-like object that isn't a standard Shapely type
        When: _transform_geometry is called
        Then: The same object is returned (no error, no transformation)
        """
        # Arrange - Given
        gc = GeometryCollection([Point(4.9, 52.37)])

        # Act - When
        result = transform_geometry(gc, "EPSG:28992")

        # Assert - Then
        assert result is gc, "Unsupported type should be returned unchanged"

    def test_transform_multipoint_with_rd_coords(self) -> None:
        """
        Scenario: Transform a MultiPoint from RD New to WGS84.

        Given: A MultiPoint with coordinates in the RD New range
        When: _transform_geometry is called with EPSG:28992
        Then: Each constituent location is individually transformed

        """
        # Arrange - Given
        mp = MultiPoint([(121_000, 487_000), (155_000, 463_000)])

        # Act - When
        result = transform_geometry(mp, "EPSG:28992")

        # Assert - Then
        assert isinstance(result, MultiPoint)
        points = list(result.geoms)
        assert len(points) == 2
        # First location near Amsterdam
        assert 4.0 < points[0].x < 6.0
        assert 52.0 < points[0].y < 53.0

    def test_transform_linearring_with_rd_coords(self) -> None:
        """
        Scenario: Transform a LinearRing from RD New where the ring stays closed.

        Given: A LinearRing with 5 points (closing location matches first)
        When: _transform_geometry is called with EPSG:28992
        Then: The result is a LinearRing with WGS84 coordinates

        """
        # Arrange - Given
        ring = LinearRing(
            [
                (155_000, 463_000),
                (156_000, 463_000),
                (156_000, 464_000),
                (155_000, 464_000),
                (155_000, 463_000),
            ]
        )

        # Act - When
        result = transform_geometry(ring, "EPSG:28992")

        # Assert - Then
        assert isinstance(result, LinearRing), "Should return a LinearRing now"
        coords = list(result.coords)
        assert len(coords) >= 4
        assert 3.0 < coords[0][0] < 8.0, "Should be in NL longitude range"


# ===================================================================
# Scenarios for Markdown-to-HTML conversion and tooltip/popup helpers.
# ===================================================================


class TestMarkdownToHtml:
    """Scenarios for Markdown-to-HTML conversion and tooltip/popup helpers."""

    def test_bold_text(self) -> None:
        """
        Scenario: Bold markdown renders as <strong>.

        Given: A markdown string with **bold** text
        When: _markdown_to_html is called
        Then: The output contains <strong> tags
        """
        assert "<strong>Amsterdam</strong>" in markdown_to_html("**Amsterdam**")

    def test_italic_text(self) -> None:
        """
        Scenario: Italic markdown renders as <em>.

        Given: A markdown string with *italic* text
        When: _markdown_to_html is called
        Then: The output contains <em> tags
        """
        assert "<em>historic</em>" in markdown_to_html("*historic*")

    def test_inline_code(self) -> None:
        """
        Scenario: Backtick code renders as <code>.

        Given: A markdown string with `code`
        When: markdown_to_html is called
        Then: The output contains <code> tags
        """
        assert "<code>EPSG:4326</code>" in markdown_to_html("`EPSG:4326`")

    def test_link(self) -> None:
        """
        Scenario: Markdown link renders as clickable <a> tag.

        Given: A markdown link [text](url)
        When: _markdown_to_html is called
        Then: The output contains an <a> tag with href and target
        """
        result = markdown_to_html("[Wiki](https://example.com)")
        assert 'href="https://example.com"' in result
        assert 'target="_blank"' in result

    def test_unordered_list(self) -> None:
        """
        Scenario: Markdown list items render as <ul>/<li>.

        Given: Markdown with dash-prefixed list items
        When: _markdown_to_html is called
        Then: The output contains <ul> and <li> tags
        """
        result = markdown_to_html("- apples\n- oranges")
        assert "<ul>" in result
        assert "<li>apples</li>" in result
        assert "<li>oranges</li>" in result

    def test_xss_is_escaped(self) -> None:
        """
        Scenario: HTML injection is escaped in tooltips.

        Given: A markdown string containing a <script> tag
        When: _markdown_to_html is called
        Then: The angle brackets are escaped as HTML entities
        """
        result = markdown_to_html("<script>alert('xss')</script>")
        assert "<script>" not in result, "Raw script tags must be escaped"
        assert "&lt;script&gt;" in result

    def test_combined_formatting(self) -> None:
        """
        Scenario: Multiple markdown features in one tooltip.

        Given: Markdown combining bold, italic, code, and a link
        When: _markdown_to_html is called
        Then: All features render correctly
        """
        # Arrange - Given
        md = "**Bold** and *italic* with `code` and [link](http://x.com)"

        # Act - When
        result = markdown_to_html(md)

        # Assert - Then
        assert "<strong>Bold</strong>" in result
        assert "<em>italic</em>" in result
        assert "<code>code</code>" in result
        assert 'href="http://x.com"' in result

    def test_h1_header_renders(self) -> None:
        """
        Scenario: A single-hash header renders as <h2>.

        Given: Markdown text "# Site Overview"
        When: _markdown_to_html is called
        Then: The output contains <h2>Site Overview</h2>
        """
        # Act - When
        result = markdown_to_html("# Site Overview")

        # Assert - Then
        assert "<h2>Site Overview</h2>" in result

    def test_h2_header_renders(self) -> None:
        """
        Scenario: A double-hash header renders as <h3>.

        Given: Markdown text "## Details"
        When: _markdown_to_html is called
        Then: The output contains <h3>Details</h3>
        """
        result = markdown_to_html("## Details")
        assert "<h3>Details</h3>" in result

    def test_h3_header_renders(self) -> None:
        """
        Scenario: A triple-hash header renders as <h4>.

        Given: Markdown text "### Notes"
        When: _markdown_to_html is called
        Then: The output contains <h4>Notes</h4>
        """
        result = markdown_to_html("### Notes")
        assert "<h4>Notes</h4>" in result

    def test_newline_between_text_becomes_br(self) -> None:
        r"""
        Scenario: A newline between two text lines inserts a <br>.

        Given: Markdown with "line1\\nline2"
        When: _markdown_to_html is called
        Then: A <br> tag appears between the lines
        """
        result = markdown_to_html("line1\nline2")
        assert "<br>" in result
        assert "line1" in result
        assert "line2" in result

    def test_ampersand_is_escaped(self) -> None:
        """
        Scenario: Ampersands in text are HTML-escaped.

        Given: Markdown containing "Tom & Jerry"
        When: _markdown_to_html is called
        Then: The & is escaped to &amp;
        """
        result = markdown_to_html("Tom & Jerry")
        assert "&amp;" in result
        assert "Tom &amp; Jerry" in result

    def test_empty_string_returns_empty(self) -> None:
        """
        Scenario: An empty markdown string returns an empty HTML string.

        Given: An empty string ""
        When: _markdown_to_html is called
        Then: The result is an empty string
        """
        result = markdown_to_html("")
        assert result == ""

    def test_plain_text_passes_through(self) -> None:
        """
        Scenario: Plain text with no markdown formatting passes through.

        Given: "Just a simple marker"
        When: _markdown_to_html is called
        Then: The text is returned unchanged (no tags added)
        """
        result = markdown_to_html("Just a simple marker")
        assert result == "Just a simple marker"

    def test_sanitize_href_blocks_unsafe_scheme(self) -> None:
        """
        Scenario: Unsafe URL schemes are replaced with '#'.

        Given: A URL with a javascript: scheme
        When: _sanitize_href is called
        Then: '#' is returned instead of the unsafe URL
        """
        assert sanitize_href("javascript:alert('xss')") == "#"

    def test_make_tooltip_returns_none_for_none(self) -> None:
        """
        Scenario: No tooltip text means no tooltip.

        Given: A Map instance
        When: _make_tooltip is called with None
        Then: None is returned
        """
        # Arrange - Given
        m = Map()

        # Act - When
        result = m._make_tooltip(None)

        # Assert - Then
        assert result is None, "None input should produce None tooltip"

    def test_make_tooltip_returns_none_for_empty_string(self) -> None:
        """
        Scenario: Empty tooltip text means no tooltip.

        Given: A Map instance
        When: _make_tooltip is called with ""
        Then: None is returned (empty string is falsy)
        """
        m = Map()
        result = m._make_tooltip("")
        assert result is None

    def test_make_tooltip_returns_folium_tooltip(self) -> None:
        """
        Scenario: Valid markdown tooltip text produces a Folium Tooltip.

        Given: A Map instance and markdown text
        When: _make_tooltip is called
        Then: A folium.Tooltip is returned
        """
        # Arrange - Given
        m = Map()

        # Act - When
        result = m._make_tooltip("**Bold tooltip**")

        # Assert - Then
        assert isinstance(result, folium.Tooltip)

    def test_make_popup_returns_none_for_none(self) -> None:
        """
        Scenario: No popup text means no popup.

        Given: A Map instance
        When: _make_popup is called with None
        Then: None is returned
        """
        m = Map()
        result = m._make_popup(None)
        assert result is None

    def test_make_popup_returns_folium_popup(self) -> None:
        """
        Scenario: Valid markdown popup text produces a Folium Popup.

        Given: A Map instance and markdown text
        When: _make_popup is called
        Then: A folium.Popup is returned
        """
        m = Map()
        result = m._make_popup("# Title\nSome content")
        assert isinstance(result, folium.Popup)


# ===================================================================
# Scenarios for style dataclass defaults and MapConfig.
# ===================================================================


class TestTileProviders:
    """Scenarios for the tile provider registry and tile layer management."""

    def test_all_providers_have_required_fields(self) -> None:
        """
        Scenario: Every registered tile provider is properly configured.

        Given: The TILE_PROVIDERS registry
        When: All entries are inspected
        Then: Each has both "tiles" and "attr" keys
        """
        for name, provider in TILE_PROVIDERS.items():
            assert "tiles" in provider, f"{name} missing 'tiles' key"
            assert "attr" in provider, f"{name} missing 'attr' key"

    def test_kadaster_providers_available(self) -> None:
        """
        Scenario: Dutch Kadaster tile providers are registered.

        Given: The TILE_PROVIDERS registry
        When: Checked for Kadaster keys
        Then: brt, luchtfoto, and grijs are all present
        """
        assert "kadaster_brt" in TILE_PROVIDERS
        assert "kadaster_luchtfoto" in TILE_PROVIDERS
        assert "kadaster_grijs" in TILE_PROVIDERS

    def test_create_map_with_each_provider(self) -> None:
        """
        Scenario: A map can be created with every registered provider.

        Given: Each tile provider name
        When: A Map is created with that provider
        Then: No errors are raised
        """
        for name in TILE_PROVIDERS:
            m = Map(config=MapConfig(tile_layer=name))
            assert m._map is not None, f"Map creation failed for provider '{name}'"

    def test_add_tile_layer_by_provider_name(self) -> None:
        """
        Scenario: Add a Kadaster aerial photo layer by name.

        Given: An empty map
        When: add_tile_layer("kadaster_luchtfoto") is called
        Then: The layer is added and the method returns self
        """
        # Arrange - Given
        m = Map()

        # Act - When
        result = m.add_tile_layer("kadaster_luchtfoto")

        # Assert - Then
        assert result is m, "add_tile_layer should return self"

    def test_add_custom_tile_layer(self) -> None:
        """
        Scenario: Add a custom XYZ tile layer with a URL.

        Given: An empty map and a custom tile URL
        When: add_tile_layer is called with a URL and attribution
        Then: The custom tile layer is added
        """
        # Arrange - Given
        m = Map()

        # Act - When
        result = m.add_tile_layer(
            "Custom Tiles",
            tiles="https://example.com/tiles/{z}/{x}/{y}.png",
            attribution="My Tiles",
        )

        # Assert - Then
        assert result is m, "Custom tile layer should be added"

    def test_add_tile_layer_as_overlay(self) -> None:
        """
        Scenario: Add a tile layer as an overlay (not base layer).

        Given: An empty map
        When: add_tile_layer is called with overlay=True and attribution
        Then: The tile layer is added as an overlay
        """
        # Arrange - Given
        m = Map()

        # Act - When
        result = m.add_tile_layer(
            "Satellite",
            tiles="https://example.com/{z}/{x}/{y}.png",
            attribution="Example Tiles",
            overlay=True,
        )

        # Assert - Then
        assert result is m

    def test_tile_layer_list_adds_multiple_layers(self) -> None:
        """
        Scenario: Pass a list of tile providers to MapConfig.

        Given: A MapConfig with tile_layer as a list of known providers
        When: A Map is created
        Then: The folium map contains TileLayer children with display names
        """
        m = Map(config=MapConfig(tile_layer=["cartodb_positron", "openstreetmap", "cartodb_dark"]))
        tile_names = [c.tile_name for c in m._map._children.values() if isinstance(c, folium.TileLayer)]
        assert "CartoDB Positron" in tile_names
        assert "OpenStreetMap" in tile_names
        assert "CartoDB Dark" in tile_names

    def test_tile_layer_list_with_custom_url(self) -> None:
        """
        Scenario: Pass a list mixing known providers and a custom tile URL.

        Given: A MapConfig with a known provider and a custom URL with attribution
        When: A Map is created
        Then: Both the known provider and custom URL tile layers are present
        """
        custom_url = "https://example.com/tiles/{z}/{x}/{y}.png"
        m = Map(
            config=MapConfig(
                tile_layer=["cartodb_positron", custom_url],
                attribution="Custom Tiles",
            )
        )
        tile_names = [c.tile_name for c in m._map._children.values() if isinstance(c, folium.TileLayer)]
        assert "CartoDB Positron" in tile_names
        assert custom_url in tile_names

    def test_tile_layer_list_with_center(self) -> None:
        """
        Scenario: Multiple tile layers with an explicit center.

        Given: A MapConfig with multiple tile layers and a center coordinate
        When: A Map is created
        Then: The map contains all tile layers
        """
        m = Map(
            center=(52.37, 4.90),
            config=MapConfig(tile_layer=["cartodb_positron", "esri_satellite"]),
        )
        tile_names = [c.tile_name for c in m._map._children.values() if isinstance(c, folium.TileLayer)]
        assert "CartoDB Positron" in tile_names
        assert "Esri Satellite" in tile_names

    def test_tile_layer_list_first_shown_by_default(self) -> None:
        """
        Scenario: The first tile layer in a list is shown by default.

        Given: A MapConfig with two tile layers
        When: A Map is created
        Then: Only the first TileLayer has show=True
        """
        m = Map(config=MapConfig(tile_layer=["cartodb_dark", "openstreetmap"]))
        tiles = [c for c in m._map._children.values() if isinstance(c, folium.TileLayer)]
        assert tiles[0].tile_name == "CartoDB Dark"
        assert tiles[0].show is True
        assert tiles[1].show is False

    def test_all_providers_have_display_name(self) -> None:
        """
        Scenario: Every registered tile provider has a display name.

        Given: The TILE_PROVIDERS registry
        When: All entries are inspected
        Then: Each has a "name" key
        """
        for key, provider in TILE_PROVIDERS.items():
            assert "name" in provider, f"{key} missing 'name' key"


# ===================================================================
# Scenarios for export methods: HTML, PNG, SVG, BytesIO, and async variants.
# ===================================================================


class TestRawHTML:
    """Scenarios for the RawHTML wrapper class."""

    def test_raw_html_is_str_subclass(self) -> None:
        """
        Scenario: RawHTML is a string subclass usable anywhere str is expected.

        Given: A RawHTML instance
        When: isinstance check is performed
        Then: It is an instance of str
        """
        html = RawHTML("<b>bold</b>")
        assert isinstance(html, str)

    def test_raw_html_tooltip_bypasses_markdown(self) -> None:
        """
        Scenario: RawHTML in tooltip bypasses markdown-to-HTML conversion.

        Given: A Map and a RawHTML string with raw HTML tags
        When: _make_tooltip is called with RawHTML
        Then: The HTML passes through unescaped
        """
        m = Map()
        raw = RawHTML("<b>bold</b> and <em>italic</em>")
        tooltip = m._make_tooltip(raw)

        assert isinstance(tooltip, folium.Tooltip)
        # The raw HTML should be present unescaped in the tooltip text
        assert "<b>bold</b>" in tooltip.text

    def test_raw_html_popup_bypasses_markdown(self) -> None:
        """
        Scenario: RawHTML in popup bypasses markdown-to-HTML conversion.

        Given: A Map and a RawHTML string with a table
        When: _make_popup is called with RawHTML
        Then: The table HTML passes through unescaped
        """
        m = Map()
        raw = RawHTML("<table><tr><td>Cell</td></tr></table>")
        popup = m._make_popup(raw)

        assert isinstance(popup, folium.Popup)

    def test_plain_string_tooltip_gets_markdown_converted(self) -> None:
        """
        Scenario: Plain strings still get markdown conversion.

        Given: A Map and a plain markdown string
        When: _make_tooltip is called
        Then: Markdown is converted to HTML (bold tags appear)
        """
        m = Map()
        tooltip = m._make_tooltip("**Bold**")

        assert isinstance(tooltip, folium.Tooltip)
        assert "<strong>Bold</strong>" in tooltip.text

    def test_plain_string_popup_gets_markdown_converted(self) -> None:
        """
        Scenario: Plain strings still get markdown conversion in popups.

        Given: A Map and a plain markdown string
        When: _make_popup is called
        Then: Markdown is converted to HTML
        """
        m = Map()
        popup = m._make_popup("**Bold**")
        assert isinstance(popup, folium.Popup)

    def test_empty_raw_html_returns_none_tooltip(self) -> None:
        """
        Scenario: Empty RawHTML is treated as falsy (no tooltip created).

        Given: A Map and an empty RawHTML
        When: _make_tooltip is called
        Then: None is returned
        """
        m = Map()
        result = m._make_tooltip(RawHTML(""))
        assert result is None

    def test_empty_raw_html_returns_none_popup(self) -> None:
        """
        Scenario: Empty RawHTML is treated as falsy (no popup created).

        Given: A Map and an empty RawHTML
        When: _make_popup is called
        Then: None is returned
        """
        m = Map()
        result = m._make_popup(RawHTML(""))
        assert result is None

    def test_raw_html_on_add_point(self) -> None:
        """
        Scenario: RawHTML works end-to-end on add_point.

        Given: A Map and RawHTML for both tooltip and popup
        When: add_point is called
        Then: The location is added without error
        """
        m = Map()
        result = m.add_point(
            Point(4.9, 52.37),
            tooltip=RawHTML("<b>Hover</b>"),
            popup=RawHTML("<i>Popup</i>"),
        )
        assert result is m


# ===================================================================
# Scenarios for PopupStyle configuration.
# ===================================================================


class TestPopupStyle:
    """Scenarios for the PopupStyle dataclass."""

    def test_default_popup_style_values(self) -> None:
        """
        Scenario: PopupStyle defaults match previous hardcoded values.

        Given: No arguments
        When: A PopupStyle is created
        Then: width=300, height=150, max_width=300
        """
        ps = PopupStyle()
        assert ps.width == 300
        assert ps.height == 150
        assert ps.max_width == 300

    def test_custom_popup_style_dimensions(self) -> None:
        """
        Scenario: Custom PopupStyle changes popup dimensions.

        Given: A PopupStyle with larger dimensions
        When: _make_popup is called with that style
        Then: The IFrame uses the custom dimensions
        """
        m = Map()
        ps = PopupStyle(width=500, height=300, max_width=600)
        popup = m._make_popup("Some content", popup_style=ps)

        assert isinstance(popup, folium.Popup)
        assert popup.options["max_width"] == 600

    def test_popup_style_none_uses_defaults(self) -> None:
        """
        Scenario: popup_style=None uses default PopupStyle values.

        Given: A Map
        When: _make_popup is called without popup_style
        Then: The popup uses default dimensions (300x150, max_width=300)
        """
        m = Map()
        popup = m._make_popup("Content")
        assert isinstance(popup, folium.Popup)
        assert popup.options["max_width"] == 300

    def test_popup_style_on_add_point(self) -> None:
        """
        Scenario: popup_style parameter on add_point works.

        Given: A Map and a custom PopupStyle
        When: add_point is called with popup and popup_style
        Then: The location is added without error
        """
        m = Map()
        ps = PopupStyle(width=400, height=250)
        result = m.add_point(
            Point(4.9, 52.37),
            popup="**Details**",
            popup_style=ps,
        )
        assert result is m

    def test_popup_style_on_add_circle(self) -> None:
        """
        Scenario: popup_style parameter on add_circle works.

        Given: A Map and a custom PopupStyle
        When: add_circle is called with popup and popup_style
        Then: The circle is added without error
        """
        m = Map()
        result = m.add_circle(
            Point(4.9, 52.37),
            popup="Circle info",
            popup_style=PopupStyle(width=400, height=200),
        )
        assert result is m

    def test_popup_style_on_add_linestring(self) -> None:
        """
        Scenario: popup_style parameter on add_linestring works.

        Given: A Map and a custom PopupStyle
        When: add_linestring is called with popup and popup_style
        Then: The line is added without error
        """
        m = Map()
        line = LineString([(4.9, 52.37), (5.0, 52.38)])
        result = m.add_linestring(
            line,
            popup="Line info",
            popup_style=PopupStyle(width=350, height=200),
        )
        assert result is m

    def test_popup_style_on_add_polygon(self) -> None:
        """
        Scenario: popup_style parameter on add_polygon works.

        Given: A Map and a custom PopupStyle
        When: add_polygon is called with popup and popup_style
        Then: The polygon is added without error
        """
        m = Map()
        poly = Polygon([(4.9, 52.3), (5.0, 52.3), (5.0, 52.4), (4.9, 52.4)])
        result = m.add_polygon(
            poly,
            popup="Polygon info",
            popup_style=PopupStyle(width=400, height=300),
        )
        assert result is m

    def test_popup_style_on_add_multipolygon(self) -> None:
        """
        Scenario: popup_style propagates through add_multipolygon.

        Given: A Map and a MultiPolygon with popup_style
        When: add_multipolygon is called
        Then: The multi polygon is added without error
        """
        m = Map()
        mp = MultiPolygon(
            [
                Polygon([(4.9, 52.3), (5.0, 52.3), (5.0, 52.4), (4.9, 52.4)]),
                Polygon([(5.0, 52.3), (5.1, 52.3), (5.1, 52.4), (5.0, 52.4)]),
            ]
        )
        result = m.add_multipolygon(mp, popup="MP info", popup_style=PopupStyle(width=400))
        assert result is m

    def test_popup_style_on_add_multilinestring(self) -> None:
        """
        Scenario: popup_style propagates through add_multilinestring.

        Given: A Map and a MultiLineString with popup_style
        When: add_multilinestring is called
        Then: The multi linestring is added without error
        """
        m = Map()
        ml = MultiLineString(
            [
                [(4.9, 52.3), (5.0, 52.4)],
                [(5.0, 52.3), (5.1, 52.4)],
            ]
        )
        result = m.add_multilinestring(ml, popup="ML info", popup_style=PopupStyle(height=200))
        assert result is m

    def test_popup_style_on_add_multipoint(self) -> None:
        """
        Scenario: popup_style propagates through add_multipoint.

        Given: A Map and a MultiPoint with popup_style
        When: add_multipoint is called
        Then: The multi location is added without error
        """
        m = Map()
        mp = MultiPoint([Point(4.9, 52.37), Point(5.0, 52.38)])
        result = m.add_multipoint(mp, popup="MP info", popup_style=PopupStyle(width=350))
        assert result is m

    def test_popup_style_on_add_marker_cluster(self) -> None:
        """
        Scenario: popup_style on add_marker_cluster works.

        Given: A Map with points and popup_style
        When: add_marker_cluster is called
        Then: The cluster is added without error
        """
        m = Map()
        points = [Point(4.9, 52.37), Point(5.0, 52.38)]
        result = m.add_marker_cluster(
            points,
            popups=["Info 1", "Info 2"],
            popup_style=PopupStyle(width=400, height=250),
        )
        assert result is m

    def test_popup_style_with_raw_html_combo(self) -> None:
        """
        Scenario: PopupStyle works together with RawHTML.

        Given: A Map, a RawHTML popup, and a custom PopupStyle
        When: _make_popup is called with both
        Then: A popup is created with custom dimensions and raw HTML
        """
        m = Map()
        ps = PopupStyle(width=500, height=400, max_width=600)
        popup = m._make_popup(RawHTML("<h1>Title</h1>"), popup_style=ps)

        assert isinstance(popup, folium.Popup)
        assert popup.options["max_width"] == 600

    def test_popup_style_on_add_geometry(self) -> None:
        """
        Scenario: popup_style propagates through add_geometry.

        Given: A Map and a Point geometry
        When: add_geometry is called with popup_style
        Then: The geometry is added without error
        """
        m = Map()
        result = m.add_geometry(
            Point(4.9, 52.37),
            popup="Info",
            popup_style=PopupStyle(width=400),
        )
        assert result is m


# ===================================================================
# Scenarios for popup on add_text.
# ===================================================================


class TestTextPopup:
    """Scenarios for popup support on add_text."""

    def test_add_text_with_popup(self) -> None:
        """
        Scenario: add_text with popup creates a clickable text marker.

        Given: A Map
        When: add_text is called with popup text
        Then: The text marker is added and returns self
        """
        m = Map()
        result = m.add_text(
            Point(4.9, 52.37),
            "Label",
            popup="**Click info**",
        )
        assert result is m

    def test_add_text_with_popup_and_tooltip(self) -> None:
        """
        Scenario: add_text with both popup and tooltip.

        Given: A Map
        When: add_text is called with both tooltip and popup
        Then: The text marker has both tooltip and popup
        """
        m = Map()
        result = m.add_text(
            Point(4.9, 52.37),
            "Label",
            tooltip="**Hover text**",
            popup="**Popup text**",
        )
        assert result is m

    def test_add_text_with_popup_style(self) -> None:
        """
        Scenario: add_text with popup_style customizes popup dimensions.

        Given: A Map and a custom PopupStyle
        When: add_text is called with popup and popup_style
        Then: The text marker is added without error
        """
        m = Map()
        result = m.add_text(
            (52.37, 4.9),
            "Label",
            popup="Content",
            popup_style=PopupStyle(width=400, height=250),
        )
        assert result is m


# ===================================================================
# Scenarios for dict-based style shortcuts.
# ===================================================================


class TestDictStyleShortcuts:
    """Scenarios for passing dicts instead of style dataclass instances."""

    def test_add_polygon_with_stroke_and_fill_dicts(self) -> None:
        """
        Scenario: Pass stroke and fill as plain dicts to add_polygon.

        Given: A Map and a Polygon
        When: add_polygon is called with stroke=dict and fill=dict
        Then: The polygon is added with the specified styling
        """
        m = Map()
        poly = Polygon([(4.9, 52.3), (5.0, 52.3), (5.0, 52.4), (4.9, 52.4)])
        result = m.add_polygon(
            poly,
            stroke={"color": "red", "weight": 4},
            fill={"color": "red", "opacity": 0.3},
        )
        assert result is m
        assert len(m._bounds) > 0

    def test_add_linestring_with_stroke_dict(self) -> None:
        """
        Scenario: Pass stroke as a dict to add_linestring.

        Given: A Map and a LineString
        When: add_linestring is called with stroke=dict
        Then: The line is added with the specified styling
        """
        m = Map()
        line = LineString([(4.9, 52.3), (5.0, 52.4)])
        result = m.add_linestring(line, stroke={"color": "#e74c3c", "dash_array": "5 10"})
        assert result is m

    def test_add_point_with_marker_style_dict(self) -> None:
        """
        Scenario: Pass marker_style as a CSS dict to add_point.

        Given: A Map and a Point
        When: add_point is called with marker_style=dict
        Then: The marker is added using the dict values
        """
        m = Map()
        result = m.add_point(
            Point(4.9, 52.37),
            marker="home",
            marker_style={"font-size": "24px", "color": "green"},
        )
        assert result is m

    def test_add_circle_with_flat_style_dict(self) -> None:
        """
        Scenario: Pass a flat CircleStyle dict (no nested stroke/fill).

        Given: A Map and a Point
        When: add_circle is called with style={"radius": 15}
        Then: The circle is added with default stroke/fill and custom radius
        """
        m = Map()
        result = m.add_circle(Point(4.9, 52.37), style={"radius": 15})
        assert result is m

    def test_add_circle_with_nested_style_dicts(self) -> None:
        """
        Scenario: Pass a CircleStyle dict with nested stroke/fill dicts.

        Given: A Map and a Point
        When: add_circle is called with nested stroke and fill dicts inside the style dict
        Then: The nested dicts are resolved into StrokeStyle/FillStyle instances
        """
        m = Map()
        result = m.add_circle(
            Point(4.9, 52.37),
            style={
                "radius": 12,
                "stroke": {"color": "#8e44ad", "weight": 2},
                "fill": {"color": "#8e44ad", "opacity": 0.5},
            },
        )
        assert result is m

    def test_add_text_with_label_style_dict(self) -> None:
        """
        Scenario: Pass a CSS dict to add_text.

        Given: A Map and a location
        When: add_text is called with style=dict
        Then: The text is rendered with the dict-based style
        """
        m = Map()
        result = m.add_text(
            Point(4.9, 52.37),
            "Test Label",
            style={"font-size": "18px", "color": "#ff0000"},
        )
        assert result is m

    def test_add_heatmap_with_style_dict(self) -> None:
        """
        Scenario: Pass a HeatmapStyle dict to add_heatmap.

        Given: A Map and a list of points
        When: add_heatmap is called with style=dict
        Then: The heatmap layer is added
        """
        m = Map()
        points = [Point(4.9 + i * 0.01, 52.37) for i in range(5)]
        result = m.add_heatmap(points, style={"radius": 20, "blur": 15})
        assert result is m

    def test_make_popup_with_popup_style_dict(self) -> None:
        """
        Scenario: _make_popup resolves a PopupStyle dict.

        Given: A Map, popup text, and a PopupStyle dict
        When: _make_popup is called with the dict
        Then: A Popup is created with the dict-based dimensions
        """
        m = Map()
        popup = m._make_popup("**Hello**", popup_style={"width": 400, "height": 200})
        assert popup is not None

    def test_add_marker_cluster_with_marker_style_dict(self) -> None:
        """
        Scenario: Pass marker_style as a CSS dict to add_marker_cluster.

        Given: A Map and a list of Points
        When: add_marker_cluster is called with marker_style=dict
        Then: The cluster is added using the dict values
        """
        m = Map()
        points = [Point(4.9 + i * 0.01, 52.37) for i in range(3)]
        result = m.add_marker_cluster(points, marker_style={"font-size": "20px", "color": "red"})
        assert result is m

    def test_resolve_style_none_returns_none(self) -> None:
        """
        Scenario: _resolve_style with None input.

        Given: None as value
        When: _resolve_style is called
        Then: None is returned
        """
        assert resolve_style(None, StrokeStyle) is None

    def test_resolve_style_dataclass_passthrough(self) -> None:
        """
        Scenario: _resolve_style with an existing dataclass instance.

        Given: A StrokeStyle instance
        When: _resolve_style is called with the instance
        Then: The same instance is returned unchanged
        """
        s = StrokeStyle(color="red")
        assert resolve_style(s, StrokeStyle) is s

    def test_resolve_style_invalid_key_raises_type_error(self) -> None:
        """
        Scenario: _resolve_style with an invalid dict key.

        Given: A dict with a key that doesn't match any dataclass field
        When: _resolve_style is called
        Then: A TypeError is raised by the dataclass constructor
        """
        with pytest.raises(TypeError):
            resolve_style({"nonexistent_field": 42}, StrokeStyle)

    def test_resolve_style_non_dict_non_instance_passthrough(self) -> None:
        """
        Scenario: _resolve_style with an unsupported type (not None, not dict, not instance).

        Given: An integer value
        When: resolve_style is called
        Then: The value is returned as-is (caller/dataclass will handle the error)
        """
        result = resolve_style(42, StrokeStyle)
        assert result == 42

    def test_dict_and_dataclass_backward_compatible(self) -> None:
        """
        Scenario: Passing a dataclass instance still works (backward compat).

        Given: A Map and a StrokeStyle object
        When: add_polygon is called with the object
        Then: The polygon is added exactly as before
        """
        m = Map()
        poly = Polygon([(4.9, 52.3), (5.0, 52.3), (5.0, 52.4), (4.9, 52.4)])
        style = StrokeStyle(color="blue", weight=5)
        result = m.add_polygon(poly, stroke=style)
        assert result is m

    def test_add_point_with_caption_style_dict_for_caption(self) -> None:
        """
        Scenario: Pass caption_style as a CSS dict to add_point for caption styling.

        Given: A Map and a Point with a caption
        When: add_point is called with caption_style=dict
        Then: The caption is rendered with the dict-based style
        """
        m = Map()
        result = m.add_point(
            Point(4.9, 52.37),
            marker="📍",
            caption="Test",
            caption_style={"font-size": "16px", "color": "#000000"},
        )
        assert result is m

    def test_add_polygon_with_popup_style_dict(self) -> None:
        """
        Scenario: Pass popup_style as a dict to add_polygon.

        Given: A Map and a Polygon with popup text
        When: add_polygon is called with popup_style=dict
        Then: The polygon popup uses the dict-based dimensions
        """
        m = Map()
        poly = Polygon([(4.9, 52.3), (5.0, 52.3), (5.0, 52.4), (4.9, 52.4)])
        result = m.add_polygon(poly, popup="**Info**", popup_style={"width": 500, "height": 300})
        assert result is m


# ===================================================================
# Scenarios for CSS dict marker style resolution.
# ===================================================================
