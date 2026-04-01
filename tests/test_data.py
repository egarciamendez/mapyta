"""BDD-style tests for the map module.

Each test follows the Given-When-Then pattern with a scenario
docstring and Arrange/Act/Assert comments.
"""
# ruff: noqa: SLF001

import contextlib
import json
import shutil
from pathlib import Path
from unittest.mock import patch

import folium
import pytest
from geopandas import GeoDataFrame
from shapely import Point, Polygon

from mapyta import FillStyle, Map, MapConfig, StrokeStyle

# ===================================================================
# Scenarios for creating and configuring a Map.
# ===================================================================


class TestGeoJSON:
    """Scenarios for adding GeoJSON data layers."""

    @pytest.fixture
    def sample_geojson(self) -> dict:
        """A minimal GeoJSON FeatureCollection with two zones."""
        return {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"name": "Zone A", "value": 42.0},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[(4.85, 52.35), (4.95, 52.35), (4.95, 52.40), (4.85, 52.40), (4.85, 52.35)]],
                    },
                },
                {
                    "type": "Feature",
                    "properties": {"name": "Zone B", "value": 78.0},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[(4.95, 52.35), (5.05, 52.35), (5.05, 52.40), (4.95, 52.40), (4.95, 52.35)]],
                    },
                },
            ],
        }

    def test_add_geojson_from_dict(self, sample_geojson: dict) -> None:
        """
        Scenario: Add a GeoJSON layer from a Python dict.

        Given: An empty map and a GeoJSON FeatureCollection dict
        When: add_geojson is called with hover_fields
        Then: The layer is added and the method returns self
        """
        # Arrange - Given
        m = Map()

        # Act - When
        result = m.add_geojson(sample_geojson, hover_fields=["name", "value"])

        # Assert - Then
        assert result is m, "add_geojson should return self"

    def test_add_geojson_from_json_string(self, sample_geojson: dict) -> None:
        """
        Scenario: Add a GeoJSON layer from a JSON string.

        Given: An empty map and a GeoJSON serialized as string
        When: add_geojson is called with the string
        Then: The string is parsed and the layer is added
        """
        # Arrange - Given
        m = Map()
        json_str = json.dumps(sample_geojson)

        # Act - When
        m.add_geojson(json_str)

        # Assert - Then
        assert len(m._bounds) > 0, "Bounds should be tracked from GeoJSON"

    def test_add_geojson_from_file(self, sample_geojson: dict, tmp_path: Path) -> None:
        """
        Scenario: Add a GeoJSON layer from a .geojson file.

        Given: A .geojson file on disk
        When: add_geojson is called with the Path
        Then: The file is read and the layer is added
        """
        # Arrange - Given
        m = Map()
        filepath = tmp_path / "zones.geojson"
        filepath.write_text(json.dumps(sample_geojson))

        # Act - When
        m.add_geojson(filepath)

        # Assert - Then
        assert len(m._bounds) > 0, "Bounds should be tracked from file"

    def test_add_geojson_with_custom_style(self, sample_geojson: dict) -> None:
        """
        Scenario: Add GeoJSON with custom styling and highlight.

        Given: An empty map and GeoJSON data
        When: add_geojson is called with style and highlight dicts
        Then: The layer is added with the custom appearance
        """
        # Arrange - Given
        m = Map()

        # Act - When
        m.add_geojson(
            sample_geojson,
            style={"color": "#e74c3c", "weight": 2, "fillOpacity": 0.1},
            highlight={"weight": 5, "fillOpacity": 0.3},
        )

        # Assert - Then
        assert len(m._bounds) > 0, "Layer should be added with bounds"

    def test_add_geojson_string_path_to_file(self, tmp_path: Path) -> None:
        """
        Scenario: Pass a string file path (not Path object) to add_geojson.

        Given: A .geojson file and its path as a string
        When: add_geojson is called with the string path
        Then: The file is detected and loaded
        """
        # Arrange - Given
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"name": "Test"},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[(4.85, 52.35), (4.95, 52.35), (4.95, 52.40), (4.85, 52.40), (4.85, 52.35)]],
                    },
                }
            ],
        }
        filepath = tmp_path / "test.geojson"
        filepath.write_text(json.dumps(geojson))
        m = Map()

        # Act - When
        m.add_geojson(str(filepath))

        # Assert - Then
        assert len(m._bounds) > 0, "GeoJSON from string path should be loaded"

    def test_add_geojson_no_hover_fields(self) -> None:
        """
        Scenario: Add GeoJSON without tooltip fields (no tooltip).

        Given: A GeoJSON dict
        When: add_geojson is called without hover_fields
        Then: The layer is added without a tooltip
        """
        # Arrange - Given
        m = Map()
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {
                        "type": "Point",
                        "coordinates": [4.9, 52.37],
                    },
                }
            ],
        }

        # Act - When
        result = m.add_geojson(geojson)

        # Assert - Then
        assert result is m

    def test_add_geojson_short_non_file_string(self) -> None:
        """
        Scenario: Pass a short JSON string that doesn't start with '{' and doesn't match any file — falls through to json.loads.

        Given: A short non-path string that is valid JSON (wrapped differently)
        When: add_geojson is called
        Then: It falls through the path check and parses as JSON

        """
        # Arrange - Given
        m = Map()

        # Use a fake short path-like string that doesn't exist
        fake_path = "/tmp/nonexistent_12345.geojson"

        # Act & Assert - When/Then
        # This should raise json.JSONDecodeError because the string isn't valid JSON
        with pytest.raises(json.JSONDecodeError):
            m.add_geojson(fake_path)

    def test_add_geojson_long_json_string(self) -> None:
        """
        Scenario: Pass a long JSON string (>500 chars) starting with '{'.

        Given: A large GeoJSON string (>500 chars)
        When: add_geojson is called
        Then: It skips the path check and parses directly as JSON

        """
        # Arrange - Given
        m = Map()
        # Build a GeoJSON string that exceeds 500 chars
        features = [
            {
                "type": "Feature",
                "properties": {"name": f"Zone {i}", "value": i * 10},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            (4.85 + i * 0.01, 52.35),
                            (4.86 + i * 0.01, 52.35),
                            (4.86 + i * 0.01, 52.36),
                            (4.85 + i * 0.01, 52.36),
                            (4.85 + i * 0.01, 52.35),
                        ]
                    ],
                },
            }
            for i in range(20)
        ]  # 20 features to ensure the string is long enough
        geojson = {"type": "FeatureCollection", "features": features}
        json_str = json.dumps(geojson)
        assert len(json_str) > 500, "String must exceed 500 chars for this test"

        # Act - When
        result = m.add_geojson(json_str)

        # Assert - Then
        assert result is m

    def test_geojson_bounds_exception_is_caught(self) -> None:
        """
        Scenario: GeoJSON layer.get_bounds() raises an exception.

        Given: A Map and a GeoJSON that causes get_bounds to fail
        When: add_geojson is called
        Then: The exception is silently caught and the method returns self

        """
        # Arrange - Given
        m = Map()
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {"type": "Point", "coordinates": [4.9, 52.37]},
                }
            ],
        }

        # Act - When — mock get_bounds to raise
        with patch.object(folium.GeoJson, "get_bounds", side_effect=ValueError("boom")):
            result = m.add_geojson(geojson)

        # Assert - Then
        assert result is m, "Exception should be caught silently"

    def test_choropleth_bounds_exception_is_caught(self) -> None:
        """
        Scenario: Choropleth layer.get_bounds() raises an exception.

        Given: A Map and valid choropleth data
        When: add_choropleth is called and get_bounds fails
        Then: The exception is silently caught

        """
        # Arrange - Given
        m = Map()
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"name": "A", "val": 50},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[(4.85, 52.35), (4.95, 52.35), (4.95, 52.40), (4.85, 52.40), (4.85, 52.35)]],
                    },
                }
            ],
        }

        # Act - When — mock get_bounds to raise
        with patch.object(folium.GeoJson, "get_bounds", side_effect=RuntimeError("fail")):
            result = m.add_choropleth(
                geojson,
                value_column="val",
                key_on="feature.properties.name",
            )

        # Assert - Then
        assert result is m

    def test_add_geojson_single_feature(self) -> None:
        """
        Scenario: Add a single GeoJSON Feature (not a FeatureCollection).

        Given: A single Feature dict
        When: add_geojson is called
        Then: The feature is tracked in _geojson_features
        """
        # Arrange - Given
        m = Map()
        feature = {
            "type": "Feature",
            "properties": {"name": "Zone A"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[(4.85, 52.35), (4.95, 52.35), (4.95, 52.40), (4.85, 52.40), (4.85, 52.35)]],
            },
        }

        # Act - When
        result = m.add_geojson(feature)

        # Assert - Then
        assert result is m
        assert len(m._geojson_features) == 1


# ===================================================================
# Scenarios for colour-coded choropleth layers.
# ===================================================================


class TestChoropleth:
    """Scenarios for colour-coded choropleth layers."""

    @pytest.fixture
    def scored_geojson(self) -> dict:
        """GeoJSON with a numeric 'score' property."""
        return {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"name": "Centrum", "score": 92},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[(4.88, 52.36), (4.92, 52.36), (4.92, 52.38), (4.88, 52.38), (4.88, 52.36)]],
                    },
                },
                {
                    "type": "Feature",
                    "properties": {"name": "West", "score": 74},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[(4.84, 52.36), (4.88, 52.36), (4.88, 52.38), (4.84, 52.38), (4.84, 52.36)]],
                    },
                },
            ],
        }

    def test_choropleth_from_properties(self, scored_geojson: dict) -> None:
        """
        Scenario: Create a choropleth that reads values from GeoJSON properties.

        Given: An empty map and GeoJSON with a "score" property per feature
        When: add_choropleth is called with value_column="score"
        Then: A colormap is created and added as a legend
        """
        # Arrange - Given
        m = Map()

        # Act - When
        result = m.add_choropleth(
            geojson_data=scored_geojson,
            value_column="score",
            key_on="feature.properties.name",
            legend_name="Liveability Score",
            hover_fields=["name", "score"],
        )

        # Assert - Then
        assert result is m, "add_choropleth should return self"
        assert len(m._colormaps) == 1, "One colormap should be registered"

    def test_choropleth_with_explicit_values(self, scored_geojson: dict) -> None:
        """
        Scenario: Create a choropleth with externally provided values.

        Given: GeoJSON data and a separate dict mapping names to values
        When: add_choropleth is called with the values dict
        Then: The explicit values override the GeoJSON properties
        """
        # Arrange - Given
        m = Map()
        values = {"Centrum": 100.0, "West": 25.0}

        # Act - When
        m.add_choropleth(
            geojson_data=scored_geojson,
            value_column="score",
            key_on="feature.properties.name",
            values=values,
            vmin=0,
            vmax=100,
        )

        # Assert - Then
        assert len(m._colormaps) == 1, "Colormap should still be created"

    def test_choropleth_from_file_path(self, scored_geojson: dict, tmp_path: Path) -> None:
        """
        Scenario: Create a choropleth from a GeoJSON file on disk.

        Given: A .geojson file with scored features
        When: add_choropleth is called with a Path object
        Then: The file is loaded and the choropleth is created
        """
        # Arrange - Given
        m = Map()
        filepath = tmp_path / "scores.geojson"
        filepath.write_text(json.dumps(scored_geojson))

        # Act - When
        m.add_choropleth(
            geojson_data=filepath,
            value_column="score",
            key_on="feature.properties.name",
        )

        # Assert - Then
        assert len(m._colormaps) == 1

    def test_choropleth_nan_features_get_fill_color(self, scored_geojson: dict) -> None:
        """
        Scenario: Features with missing values use the nan_fill_color.

        Given: GeoJSON where one feature has score=None
        When: add_choropleth is called with nan_fill_color="#999999"
        Then: The choropleth is created without errors
        """
        # Arrange - Given
        m = Map()

        # Act - When
        result = m.add_choropleth(
            geojson_data=scored_geojson,
            value_column="score",
            key_on="feature.properties.name",
            nan_fill_color="#999999",
            nan_fill_opacity=0.3,
        )

        # Assert - Then
        assert result is m, "Choropleth with NaN values should not error"

    def test_choropleth_from_json_string(self, scored_geojson: dict) -> None:
        """
        Scenario: Create a choropleth from a JSON string.

        Given: GeoJSON serialized as a string
        When: add_choropleth is called with the string
        Then: The string is parsed and the choropleth is created
        """
        # Arrange - Given
        m = Map()
        json_str = json.dumps(scored_geojson)

        # Act - When
        m.add_choropleth(
            geojson_data=json_str,
            value_column="score",
            key_on="feature.properties.name",
        )

        # Assert - Then
        assert len(m._colormaps) == 1

    def test_choropleth_short_string_path(self, tmp_path: Path) -> None:
        """
        Scenario: Pass a short string file path to add_choropleth.

        Given: A .geojson file and its path as a short string
        When: add_choropleth is called with the string path
        Then: The file is detected and loaded

        """
        # Arrange - Given
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"name": "A", "val": 50},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[(4.85, 52.35), (4.95, 52.35), (4.95, 52.40), (4.85, 52.40), (4.85, 52.35)]],
                    },
                }
            ],
        }
        filepath = tmp_path / "choropleth.geojson"
        filepath.write_text(json.dumps(geojson))
        m = Map()

        # Act - When
        m.add_choropleth(
            geojson_data=str(filepath),
            value_column="val",
            key_on="feature.properties.name",
        )

        # Assert - Then
        assert len(m._colormaps) == 1

    def test_choropleth_short_nonexistent_path_falls_to_json(self) -> None:
        """
        Scenario: Pass a short string that isn't a valid file and isn't valid JSON.

        Given: A short non-path, non-JSON string
        When: add_choropleth is called
        Then: json.loads fails with JSONDecodeError

        """
        # Arrange - Given
        m = Map()

        # Act & Assert - When/Then
        with pytest.raises(json.JSONDecodeError):
            m.add_choropleth(
                geojson_data="/tmp/nonexistent_xyz.geojson",
                value_column="val",
                key_on="feature.properties.name",
            )

    def test_choropleth_long_json_string(self) -> None:
        """
        Scenario: Pass a long JSON string (>500 chars) to add_choropleth.

        Given: A large GeoJSON string
        When: add_choropleth is called
        Then: It parses directly as JSON, skipping the path check

        """
        # Arrange - Given
        m = Map()
        features = [
            {
                "type": "Feature",
                "properties": {"name": f"Z{i}", "val": float(i * 5)},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            (4.85 + i * 0.01, 52.35),
                            (4.86 + i * 0.01, 52.35),
                            (4.86 + i * 0.01, 52.36),
                            (4.85 + i * 0.01, 52.36),
                            (4.85 + i * 0.01, 52.35),
                        ]
                    ],
                },
            }
            for i in range(20)
        ]
        geojson = {"type": "FeatureCollection", "features": features}
        json_str = json.dumps(geojson)
        assert len(json_str) > 500

        # Act - When
        m.add_choropleth(
            geojson_data=json_str,
            value_column="val",
            key_on="feature.properties.name",
        )

        # Assert - Then
        assert len(m._colormaps) == 1

    def test_choropleth_style_fn_nan_branch(self) -> None:
        """
        Scenario: A choropleth feature has no matching value in the values dict.

        Given: GeoJSON with two features but values dict only has one key
        When: add_choropleth is called and Folium renders both features
        Then: The missing feature uses nan_fill_color

        """
        # Arrange - Given
        m = Map()
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"name": "Known", "val": 50},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[(4.85, 52.35), (4.90, 52.35), (4.90, 52.38), (4.85, 52.38), (4.85, 52.35)]],
                    },
                },
                {
                    "type": "Feature",
                    "properties": {"name": "Unknown", "val": None},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[(4.90, 52.35), (4.95, 52.35), (4.95, 52.38), (4.90, 52.38), (4.90, 52.35)]],
                    },
                },
            ],
        }

        # Act - When
        m.add_choropleth(
            geojson_data=geojson,
            value_column="val",
            key_on="feature.properties.name",
            values={"Known": 50.0},  # "Unknown" not in values
            nan_fill_color="#aaaaaa",
            vmin=0,
            vmax=100,
        )

        # Force Folium to render which triggers style_fn for each feature
        html = m._repr_html_()

        # Assert - Then
        assert len(m._colormaps) == 1
        assert "#aaaaaa" in html, "nan_fill_color should appear in rendered output"

    def test_choropleth_single_feature_input(self) -> None:
        """
        Scenario: add_choropleth accepts a single Feature (not FeatureCollection).

        Given: A single Feature dict with a numeric property
        When: add_choropleth is called
        Then: The feature is tracked in _geojson_features and the method returns self
        """
        # Arrange - Given
        m = Map()
        feature = {
            "type": "Feature",
            "properties": {"name": "Centrum", "score": 80},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[(4.88, 52.36), (4.92, 52.36), (4.92, 52.38), (4.88, 52.38), (4.88, 52.36)]],
            },
        }

        # Act - When
        result = m.add_choropleth(feature, value_column="score", key_on="feature.properties.name")

        # Assert - Then
        assert result is m
        assert len(m._geojson_features) == 1


# ===================================================================
# Scenarios for GeoJSON export.
# ===================================================================


class TestToGeoJSON:
    """Scenarios for exporting map features as GeoJSON."""

    def test_to_geojson_returns_dict_without_path(self) -> None:
        """
        Scenario: to_geojson with no path returns a FeatureCollection dict.

        Given: A map with a point
        When: to_geojson is called without a path
        Then: A FeatureCollection dict is returned
        """
        # Arrange - Given
        m = Map()
        m.add_point(Point(4.9, 52.37), tooltip="Dom")

        # Act - When
        result = m.to_geojson()

        # Assert - Then
        assert isinstance(result, dict)
        assert result["type"] == "FeatureCollection"

    def test_to_geojson_saves_to_file(self, tmp_path: Path) -> None:
        """
        Scenario: to_geojson with a path writes GeoJSON to disk.

        Given: A map with a point and an output path
        When: to_geojson is called with a path
        Then: The file is written and the Path is returned
        """
        # Arrange - Given
        m = Map()
        m.add_point(Point(4.9, 52.37), tooltip="Dom")
        out = tmp_path / "features.geojson"

        # Act - When
        result = m.to_geojson(out)

        # Assert - Then
        assert result == out
        assert out.exists()
        data = json.loads(out.read_text())
        assert data["type"] == "FeatureCollection"


# ===================================================================
# Scenarios for the GeoJSON export button.
# ===================================================================


class TestExportButton:
    """Scenarios for add_export_button and _inject_export_button."""

    def test_add_export_button_returns_self(self) -> None:
        """
        Scenario: add_export_button returns the map for chaining.

        Given: An empty map
        When: add_export_button is called
        Then: The map is returned and _export_button_config is set
        """
        # Arrange - Given
        m = Map()

        # Act - When
        result = m.add_export_button()

        # Assert - Then
        assert result is m
        assert m._export_button_config is not None

    def test_export_button_script_injected_on_render(self) -> None:
        """
        Scenario: Rendering a map with add_export_button injects the download script.

        Given: A map with a point and an export button
        When: to_html is called
        Then: The rendered HTML contains the download button script
        """
        # Arrange - Given
        m = Map()
        m.add_point(Point(4.9, 52.37))
        m.add_export_button(label="Download GeoJSON", filename="export.geojson")

        # Act - When
        html = m.to_html()

        # Assert - Then
        assert "Download GeoJSON" in html
        assert "export.geojson" in html
        assert "exportControl" in html

    def test_export_button_not_injected_twice(self) -> None:
        """
        Scenario: Calling to_html twice does not inject the button script twice.

        Given: A map with an export button
        When: to_html is called twice
        Then: The script appears exactly once
        """
        # Arrange - Given
        m = Map()
        m.add_point(Point(4.9, 52.37))
        m.add_export_button()

        # Act - When
        html1 = m.to_html()
        html2 = m.to_html()

        # Assert - Then — script injected once, same count on re-render
        assert html1.count("exportControl.addTo") == 1
        assert html2.count("exportControl.addTo") == 1


# ===================================================================
# Scenarios for heatmap layers.
# ===================================================================


@pytest.mark.skipif(GeoDataFrame is None, reason="geopandas not installed")
class TestGeoDataFrame:
    """Scenarios for creating maps from GeoPandas GeoDataFrames."""

    @pytest.fixture
    def cities_gdf(self) -> GeoDataFrame:
        """GeoDataFrame with 3 Dutch cities."""
        return GeoDataFrame(
            data={
                "name": ["Amsterdam", "Rotterdam", "Utrecht"],
                "population": [872_680, 651_446, 361_924],
                "geometry": [
                    Point(4.9041, 52.3676),
                    Point(4.4777, 51.9244),
                    Point(5.1214, 52.0907),
                ],
            },
            crs="EPSG:4326",
        )

    @pytest.fixture
    def rd_gdf(self) -> GeoDataFrame:
        """GeoDataFrame in RD New CRS."""
        return GeoDataFrame(
            data={"name": ["AMS"], "geometry": [Point(121_000, 487_000)]},
            crs="EPSG:28992",
        )

    def test_create_map_from_geodataframe(self, cities_gdf: GeoDataFrame) -> None:
        """
        Scenario: Create a map from a GeoDataFrame with tooltip columns.

        Given: A GeoDataFrame with 3 cities and their populations
        When: from_geodataframe is called with hover_columns
        Then: All 3 points are on the map with tooltips
        """
        # Act - When
        m = Map.from_geodataframe(cities_gdf, hover_columns=["name", "population"])

        # Assert - Then
        assert len(m._bounds) == 6, "3 points x 2 bound entries each"

    def test_geodataframe_with_color_column(self, cities_gdf: GeoDataFrame) -> None:
        """
        Scenario: Color-code cities by population.

        Given: A GeoDataFrame with a numeric "population" column
        When: from_geodataframe is called with color_column="population"
        Then: A colormap is created and added as legend
        """
        # Act - When
        m = Map.from_geodataframe(
            cities_gdf,
            color_column="population",
            legend_name="Population",
        )

        # Assert - Then
        assert len(m._colormaps) == 1, "One colormap should be registered"

    def test_geodataframe_with_label_column(self, cities_gdf: GeoDataFrame) -> None:
        """
        Scenario: Use city names as marker labels.

        Given: A GeoDataFrame with a "name" column
        When: from_geodataframe is called with label_column="name"
        Then: All points are added with text labels
        """
        # Act - When
        m = Map.from_geodataframe(cities_gdf, label_column="name")

        # Assert - Then
        assert len(m._bounds) == 6, "All cities should be on the map"

    def test_geodataframe_auto_reprojects_rd(self, rd_gdf: GeoDataFrame) -> None:
        """
        Scenario: A GeoDataFrame in RD New is auto-reprojected to WGS84.

        Given: A GeoDataFrame with CRS EPSG:28992
        When: from_geodataframe is called
        Then: The resulting map bounds are in WGS84 range
        """
        # Act - When
        m = Map.from_geodataframe(rd_gdf, hover_columns=["name"])

        # Assert - Then
        lat, lon = m._bounds[0]
        assert 50.0 < lat < 54.0, f"Latitude {lat} should be in NL"
        assert 3.0 < lon < 8.0, f"Longitude {lon} should be in NL"

    def test_missing_geopandas_raises_import_error(self) -> None:
        """
        Scenario: Calling from_geodataframe without geopandas installed.

        Given: geopandas is not available (mocked)
        When: from_geodataframe is called
        Then: An ImportError is raised with install instructions
        """
        # Act & Assert - When/Then
        with patch.dict("sys.modules", {"geopandas": None}), contextlib.suppress(ImportError, AttributeError):
            # Expected
            Map.from_geodataframe(None)

    @pytest.fixture
    def _check_geopandas(self) -> None:
        """Skip if geopandas is not installed."""
        try:
            shutil.which("geopandas")
        except ImportError:
            pytest.skip("geopandas not installed")

    def test_geodataframe_skips_null_geometries(self) -> None:
        """
        Scenario: Rows with null or empty geometries are silently skipped.

        Given: A GeoDataFrame where one row has geometry=None
        When: from_geodataframe is called
        Then: Only the valid rows appear on the map
        """
        # Arrange - Given
        gdf = GeoDataFrame(
            data={
                "name": ["Valid", "Null", "Empty"],
                "geometry": [Point(4.9, 52.37), None, Point(5.1, 52.09).buffer(0).boundary],
            },
            crs="EPSG:4326",
        )
        # Replace the third geometry with an actually empty one
        gdf.loc[2, "geometry"] = Point()

        # Act - When
        m = Map.from_geodataframe(gdf, hover_columns=["name"])

        # Assert - Then
        # Only the first valid location should contribute bounds
        assert len(m._bounds) >= 2, "At least one valid location should be on the map"

    def test_geodataframe_with_popup_columns(self) -> None:
        """
        Scenario: Create a map with click popups from DataFrame columns.

        Given: A GeoDataFrame with name and population columns
        When: from_geodataframe is called with popup_columns
        Then: Popups are configured for each row
        """
        # Arrange - Given
        gdf = GeoDataFrame(
            {
                "name": ["Amsterdam", "Rotterdam"],
                "population": [872_680, 651_446],
                "geometry": [Point(4.9, 52.37), Point(4.48, 51.92)],
            },
            crs="EPSG:4326",
        )

        # Act - When
        m = Map.from_geodataframe(
            gdf,
            popup_columns=["name", "population"],
        )

        # Assert - Then
        assert len(m._bounds) == 4, "Both cities should be on the map"

    def test_geodataframe_with_nan_in_color_column(self) -> None:
        """
        Scenario: GeoDataFrame with NaN in the color column..

        Given: A GeoDataFrame where one row has NaN population
        When: from_geodataframe is called with color_column="population"
        Then: The map is created without errors (NaN row uses default style)
        """
        # Arrange - Given
        gdf = GeoDataFrame(
            {
                "name": ["Amsterdam", "Unknown"],
                "population": [872_680, float("nan")],
                "geometry": [Point(4.9, 52.37), Point(5.1, 52.09)],
            },
            crs="EPSG:4326",
        )

        # Act - When
        m = Map.from_geodataframe(gdf, color_column="population")

        # Assert - Then
        assert len(m._bounds) == 4, "Both points should be on the map"
        assert len(m._colormaps) == 1, "Colormap should still be created"

    def test_geodataframe_with_custom_stroke_and_fill(self) -> None:
        """
        Scenario: Override default styling for a GeoDataFrame..

        Given: A GeoDataFrame and custom stroke/fill styles
        When: from_geodataframe is called with those styles
        Then: The map uses the custom styles
        """
        # Arrange - Given
        gdf = GeoDataFrame(
            data={
                "name": ["Zone"],
                "geometry": [Polygon([(4.85, 52.35), (4.95, 52.35), (4.95, 52.40), (4.85, 52.40)])],
            },
            crs="EPSG:4326",
        )
        stroke = StrokeStyle(color="red", weight=5)
        fill = FillStyle(color="red", opacity=0.5)

        # Act - When
        m = Map.from_geodataframe(gdf, stroke=stroke, fill=fill)

        # Assert - Then
        assert len(m._bounds) == 2

    def test_geodataframe_with_custom_config(self) -> None:
        """
        Scenario: Create a map from GeoDataFrame with custom MapConfig..

        Given: A GeoDataFrame and a dark-theme MapConfig
        When: from_geodataframe is called with the config
        Then: The map uses the custom configuration
        """
        # Arrange - Given
        gdf = GeoDataFrame(
            {"name": ["AMS"], "geometry": [Point(4.9, 52.37)]},
            crs="EPSG:4326",
        )
        config = MapConfig(tile_layer="cartodb_dark", fullscreen=True)

        # Act - When
        m = Map.from_geodataframe(gdf, config=config, title="Dark Cities")

        # Assert - Then
        assert m._config.tile_layer == "cartodb_dark"
        assert m._title == "Dark Cities"

    def test_geodataframe_with_polygon_geometries(self) -> None:
        """
        Scenario: Create a map from a GeoDataFrame with polygon geometries..

        Given: A GeoDataFrame with Polygon geometry (not points)
        When: from_geodataframe is called
        Then: The polygons are dispatched correctly
        """
        # Arrange - Given
        gdf = GeoDataFrame(
            {
                "name": ["Centrum", "West"],
                "geometry": [
                    Polygon([(4.88, 52.36), (4.92, 52.36), (4.92, 52.38), (4.88, 52.38)]),
                    Polygon([(4.84, 52.36), (4.88, 52.36), (4.88, 52.38), (4.84, 52.38)]),
                ],
            },
            crs="EPSG:4326",
        )

        # Act - When
        m = Map.from_geodataframe(gdf, hover_columns=["name"])

        # Assert - Then -
        assert len(m._bounds) == 4, "Two polygons x 2 bound entries each"


# ===================================================================
# Scenarios for caption on add_point.
# ===================================================================
