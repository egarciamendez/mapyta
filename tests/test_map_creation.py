"""BDD-style tests for the map module.

Each test follows the Given-When-Then pattern with a scenario
docstring and Arrange/Act/Assert comments.
"""
# ruff: noqa: SLF001

import folium
from shapely import Point

from mapyta import CircleStyle, FillStyle, HeatmapStyle, Map, MapConfig, StrokeStyle
from mapyta.markers import DEFAULT_CAPTION_CSS, DEFAULT_ICON_CSS, DEFAULT_MARKER_CAPTION_CSS, DEFAULT_TEXT_CSS, css_to_style

# ===================================================================
# Scenarios for creating and configuring a Map.
# ===================================================================


class TestMapCreation:
    """Scenarios for creating and configuring a Map."""

    def test_create_empty_map(self) -> None:
        """
        Scenario: Create a map with no arguments.

        Given: No configuration or data
        When: A Map is instantiated with defaults
        Then: The map has no title, no center, and an empty bounds list
        """
        # Act - When
        m = Map()

        # Assert - Then
        assert m._title is None, "Empty map should have no title"
        assert m._center is None, "Empty map should have no fixed center"
        assert m._bounds == [], "Empty map should have no tracked bounds"
        assert isinstance(m.folium_map, folium.Map), "Should wrap a Folium Map"

    def test_create_map_with_title(self) -> None:
        """
        Scenario: Create a map with a title overlay.

        Given: A title string "Construction Site Alpha"
        When: A Map is created with that title
        Then: The title is stored and rendered in the HTML
        """
        # Arrange - Given
        title = "Construction Site Alpha"

        # Act - When
        m = Map(title=title)

        # Assert - Then
        assert m._title == title, "Title should be stored"
        html = m._repr_html_()
        assert title in html, "Title should appear in rendered HTML"

    def test_create_map_with_fixed_center(self) -> None:
        """
        Scenario: Create a map centered on a specific location.

        Given: Center coordinates for Amsterdam (52.37, 4.90)
        When: A Map is created with that center
        Then: The map uses the fixed center instead of auto-fitting
        """
        # Arrange - Given
        center = (52.37, 4.90)

        # Act - When
        m = Map(center=center)

        # Assert - Then
        assert m._center == center, "Center should be stored as provided"

    def test_create_map_with_custom_config(self) -> None:
        """
        Scenario: Create a map with dark theme and plugins enabled.

        Given: A MapConfig with dark tiles, fullscreen, and minimap
        When: A Map is created with that config
        Then: The config is applied to the underlying map
        """
        # Arrange - Given
        config = MapConfig(
            tile_layer="cartodb_dark",
            zoom_start=14,
            fullscreen=True,
            minimap=True,
            measure_control=True,
            mouse_position=True,
        )

        # Act - When
        m = Map(config=config)

        # Assert - Then
        assert m._config.tile_layer == "cartodb_dark"
        assert m._config.fullscreen is True
        assert m._config.minimap is True
        assert m._config.zoom_start == 14

    def test_create_map_with_min_zoom(self) -> None:
        """
        Scenario: Create a map with min_zoom to restrict zoom-out.

        Given: A MapConfig with min_zoom=5
        When: A Map is created
        Then: The config stores min_zoom and the Folium map respects it
        """
        # Arrange - Given
        config = MapConfig(min_zoom=5)

        # Act - When
        m = Map(config=config)

        # Assert - Then
        assert m._config.min_zoom == 5

    def test_create_map_with_explicit_crs(self) -> None:
        """
        Scenario: Create a map with an explicit source coordinate system.

        Given: A CRS string "EPSG:28992" (Dutch RD New)
        When: A Map is created with that source_crs
        Then: All added geometries are transformed from that CRS
        """
        # Arrange - Given
        crs = "EPSG:28992"

        # Act - When
        m = Map(source_crs=crs)

        # Assert - Then
        assert m._source_crs == crs, "Source CRS should be stored"

    def test_map_repr_shows_metadata(self) -> None:
        """
        Scenario: Inspect a map's string representation.

        Given: A Map with a title and one location added
        When: repr() is called on the map
        Then: The output includes the title and geometry count
        """
        # Arrange - Given
        m = Map(title="Site B")
        m.add_point(Point(4.9, 52.37))

        # Act - When
        result = repr(m)

        # Assert - Then
        assert "Site B" in result, "repr should include the title"
        assert "Map" in result, "repr should include the class name"

    def test_map_with_custom_tile_url(self) -> None:
        """
        Scenario: Create a map with a tile URL not in the TILE_PROVIDERS registry.

        Given: A MapConfig with a raw tile URL and custom attribution
        When: A Map is created
        Then: The custom tile URL is passed to Folium

        """
        # Arrange - Given
        config = MapConfig(
            tile_layer="https://custom.tiles.example/{z}/{x}/{y}.png",
            attribution="Custom Tiles © Example",
        )

        # Act - When
        m = Map(config=config)

        # Assert - Then
        assert m._map is not None, "Map should be created with custom tiles"
        assert m._config.tile_layer.startswith("https://")  # ty: ignore[unresolved-attribute]


# ===================================================================
# Scenarios for adding location markers and circles.
# ===================================================================


class TestStyleDataclasses:
    """Scenarios for style dataclass defaults and MapConfig."""

    def test_stroke_style_defaults(self) -> None:
        """
        Scenario: StrokeStyle has sensible defaults.

        Given: No arguments
        When: A StrokeStyle is created
        Then: It uses blue color, 3px weight, full opacity, no dash
        """
        s = StrokeStyle()
        assert s.color == "#3388ff"
        assert s.weight == 3.0
        assert s.opacity == 1.0
        assert s.dash_array is None

    def test_fill_style_defaults(self) -> None:
        """
        Scenario: FillStyle defaults to low opacity for overlapping shapes.

        Given: No arguments
        When: A FillStyle is created
        Then: It uses 20% opacity
        """
        f = FillStyle()
        assert f.opacity == 0.2

    def test_default_icon_css(self) -> None:
        """
        Scenario: _DEFAULT_ICON_CSS has sensible defaults.

        Given: The module-level constant
        When: Inspected
        Then: font-size is 20px, color is #002855
        """
        assert DEFAULT_ICON_CSS["font-size"] == "20px"
        assert DEFAULT_ICON_CSS["color"] == "#002855"

    def test_default_text_css(self) -> None:
        """
        Scenario: _DEFAULT_TEXT_CSS has sensible defaults.

        Given: The module-level constant
        When: Inspected
        Then: font-size is 16px, color is black
        """
        assert DEFAULT_TEXT_CSS["font-size"] == "16px"
        assert DEFAULT_TEXT_CSS["color"] == "black"

    def test_default_marker_caption_css(self) -> None:
        """
        Scenario: _DEFAULT_MARKER_CAPTION_CSS has transparent background and no border.

        Given: The module-level constant
        When: Inspected
        Then: background-color is transparent, border is none
        """
        assert DEFAULT_MARKER_CAPTION_CSS["background-color"] == "transparent"
        assert DEFAULT_MARKER_CAPTION_CSS["border"] == "none"

    def test_heatmap_style_defaults(self) -> None:
        """
        Scenario: HeatmapStyle defaults to reasonable visualization values.

        Given: No arguments
        When: A HeatmapStyle is created
        Then: radius=15, no custom gradient
        """
        hs = HeatmapStyle()
        assert hs.radius == 15
        assert hs.blur == 10
        assert hs.gradient is None

    def test_mapconfig_default_dimensions(self) -> None:
        """
        Scenario: MapConfig defaults to 100% width and height.

        Given: No arguments
        When: A MapConfig is created
        Then: width="100%" and height="100%"
        """
        cfg = MapConfig()
        assert cfg.width == "100%"
        assert cfg.height == "100%"
        assert cfg.max_zoom == 19
        assert cfg.control_scale is True

    def test_mapconfig_custom_dimensions(self) -> None:
        """
        Scenario: MapConfig accepts pixel dimensions.

        Given: width=800 and height=600
        When: A MapConfig is created
        Then: The dimensions are stored as integers
        """
        cfg = MapConfig(width=800, height=600)
        assert cfg.width == 800
        assert cfg.height == 600

    def test_stroke_style_custom_values(self) -> None:
        """
        Scenario: Create a StrokeStyle with all custom values.

        Given: Custom color, weight, opacity, and dash_array
        When: A StrokeStyle is created
        Then: All values are stored correctly
        """
        s = StrokeStyle(color="#ff0000", weight=5.0, opacity=0.8, dash_array="5 10")
        assert s.color == "#ff0000"
        assert s.weight == 5.0
        assert s.opacity == 0.8
        assert s.dash_array == "5 10"

    def test_circle_style_nested_defaults(self) -> None:
        """
        Scenario: CircleStyle creates default StrokeStyle and FillStyle.

        Given: No arguments
        When: A CircleStyle is created
        Then: It contains properly initialized nested styles
        """
        cs = CircleStyle()
        assert isinstance(cs.stroke, StrokeStyle)
        assert isinstance(cs.fill, FillStyle)
        assert cs.stroke.color == "#3388ff"
        assert cs.fill.opacity == 0.2

    def test_default_caption_css(self) -> None:
        """
        Scenario: _DEFAULT_CAPTION_CSS has all expected defaults.

        Given: The module-level constant
        When: Inspected
        Then: All expected CSS properties are present
        """
        assert DEFAULT_CAPTION_CSS["font-size"] == "12px"
        assert DEFAULT_CAPTION_CSS["font-family"] == "Arial, sans-serif"
        assert DEFAULT_CAPTION_CSS["color"] == "#333333"
        assert DEFAULT_CAPTION_CSS["font-weight"] == "bold"
        assert DEFAULT_CAPTION_CSS["background-color"] == "rgba(255,255,255,0.8)"
        assert DEFAULT_CAPTION_CSS["border"] == "1px solid #cccccc"
        assert DEFAULT_CAPTION_CSS["padding"] == "2px 6px"

    def test_css_to_style_helper(self) -> None:
        """
        Scenario: css_to_style converts a dict to inline CSS string.

        Given: A CSS property dict
        When: _css_to_style is called
        Then: A semicolon-separated string is returned
        """
        result = css_to_style({"font-size": "14px", "color": "red"})
        assert "font-size:14px" in result
        assert "color:red" in result

    def test_fill_style_custom_values(self) -> None:
        """
        Scenario: Create a FillStyle with full opacity.

        Given: color="#00ff00" and opacity=1.0
        When: A FillStyle is created
        Then: The values are stored
        """
        f = FillStyle(color="#00ff00", opacity=1.0)
        assert f.color == "#00ff00"
        assert f.opacity == 1.0

    def test_css_dict_overrides_defaults(self) -> None:
        """
        Scenario: User CSS dict overrides default values.

        Given: A default CSS dict and user overrides
        When: Merged together
        Then: User values override defaults
        """
        merged = {**DEFAULT_ICON_CSS, "font-size": "30px", "color": "red"}
        assert merged["font-size"] == "30px"
        assert merged["color"] == "red"

    def test_heatmap_style_with_gradient(self) -> None:
        """
        Scenario: Create a HeatmapStyle with a custom gradient.

        Given: A gradient dict mapping stops to colors
        When: A HeatmapStyle is created
        Then: The gradient is stored
        """
        gradient = {0.2: "blue", 0.5: "lime", 1.0: "red"}
        hs = HeatmapStyle(gradient=gradient)
        assert hs.gradient == gradient


# ===================================================================
# Scenarios for the tile provider registry and tile layer management.
# ===================================================================


def _tile_layers(fmap: folium.Map) -> list[folium.TileLayer]:
    """Return all TileLayer children attached to a Folium map."""
    return [child for child in fmap._children.values() if isinstance(child, folium.TileLayer)]


class TestTileLayerZoom:
    """Regression scenarios for max_zoom / max_native_zoom wiring on TileLayers."""

    def test_single_layer_defaults_native_zoom_to_max_zoom(self) -> None:
        """
        Scenario: Single tile layer with no explicit max_native_zoom.

        Given: A MapConfig using defaults (max_zoom=19, max_native_zoom=None)
        When: A Map is created
        Then: The single TileLayer's options expose max_zoom=19 and
              max_native_zoom=19 (native falls back to max_zoom)
        """
        # Act - When
        m = Map()

        # Assert - Then
        layers = _tile_layers(m.folium_map)
        assert len(layers) == 1, "Single-layer config should produce exactly one TileLayer"
        opts = layers[0].options
        assert opts["max_zoom"] == 19
        assert opts["max_native_zoom"] == 19

    def test_single_layer_respects_max_native_zoom(self) -> None:
        """
        Scenario: Single tile layer with max_native_zoom below max_zoom.

        Given: A MapConfig with max_zoom=22 and max_native_zoom=19
        When: A Map is created
        Then: The TileLayer's options carry max_zoom=22 and
              max_native_zoom=19 so Leaflet upscales instead of showing
              gray placeholder tiles beyond zoom 19
        """
        # Arrange - Given
        config = MapConfig(max_zoom=22, max_native_zoom=19)

        # Act - When
        m = Map(config=config)

        # Assert - Then
        layers = _tile_layers(m.folium_map)
        assert len(layers) == 1
        opts = layers[0].options
        assert opts["max_zoom"] == 22
        assert opts["max_native_zoom"] == 19

    def test_multi_layer_propagates_max_native_zoom(self) -> None:
        """
        Scenario: Multiple tile layers all receive max_native_zoom.

        Given: A MapConfig with two providers, max_zoom=22, max_native_zoom=19
        When: A Map is created
        Then: Every TileLayer exposes the same max_zoom/max_native_zoom
              options (so toggling layers never regresses to gray tiles)
        """
        # Arrange - Given
        config = MapConfig(
            tile_layer=["openstreetmap", "cartodb_dark"],
            max_zoom=22,
            max_native_zoom=19,
        )

        # Act - When
        m = Map(config=config)

        # Assert - Then
        layers = _tile_layers(m.folium_map)
        assert len(layers) == 2, "Each listed provider should be added as a TileLayer"
        for layer in layers:
            assert layer.options["max_zoom"] == 22
            assert layer.options["max_native_zoom"] == 19

    def test_custom_tile_url_respects_max_native_zoom(self) -> None:
        """
        Scenario: Raw tile URL (not in TILE_PROVIDERS) with max_native_zoom.

        Given: A MapConfig with a custom URL and max_native_zoom=19
        When: A Map is created
        Then: The TileLayer built from the custom URL still carries
              max_zoom=22 and max_native_zoom=19
        """
        # Arrange - Given
        config = MapConfig(
            tile_layer="https://custom.tiles.example/{z}/{x}/{y}.png",
            attribution="Custom Tiles © Example",
            max_zoom=22,
            max_native_zoom=19,
        )

        # Act - When
        m = Map(config=config)

        # Assert - Then
        layers = _tile_layers(m.folium_map)
        assert len(layers) == 1
        opts = layers[0].options
        assert opts["max_zoom"] == 22
        assert opts["max_native_zoom"] == 19

    def test_add_tile_layer_propagates_max_native_zoom(self) -> None:
        """
        Scenario: Layers added post-construction inherit the zoom config.

        Given: A Map with max_zoom=22 and max_native_zoom=19
        When: add_tile_layer is called with an additional provider
        Then: The newly added TileLayer carries the same
              max_zoom/max_native_zoom options as the base layer, so
              toggling to it never regresses to blank tiles beyond zoom 19
        """
        # Arrange - Given
        config = MapConfig(max_zoom=22, max_native_zoom=19)
        m = Map(config=config)

        # Act - When
        m.add_tile_layer("cartodb_dark")

        # Assert - Then
        layers = _tile_layers(m.folium_map)
        assert len(layers) == 2, "Base layer + added layer should both be present"
        for layer in layers:
            assert layer.options["max_zoom"] == 22
            assert layer.options["max_native_zoom"] == 19
