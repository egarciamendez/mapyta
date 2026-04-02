"""BDD-style tests for DataFrame-to-GeoJSON conversion and Map.add_dataframe().

Each test follows the Given-When-Then pattern with a scenario
docstring and Arrange/Act/Assert comments.
"""
# ruff: noqa: SLF001

import json

import numpy as np
import pytest

pandas = pytest.importorskip("pandas")

import pandas as pd  # noqa: E402

from mapyta import Map  # noqa: E402
from mapyta.dataframe import _coerce_value, dataframe_to_geojson  # noqa: E402

try:
    import polars as pl

    HAS_POLARS = True
except ImportError:
    HAS_POLARS = False

skip_if_no_polars = pytest.mark.skipif(not HAS_POLARS, reason="polars not installed")

# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
def point_pandas() -> pd.DataFrame:
    """Pandas DataFrame with two Point WKT rows and a property column."""
    return pd.DataFrame(
        {
            "geometry": ["POINT (4.9 52.37)", "POINT (5.1 52.09)"],
            "name": ["Amsterdam", "Utrecht"],
            "score": [100, 80],
        }
    )


@pytest.fixture
def point_polars() -> "pl.DataFrame":
    """Polars DataFrame with two Point WKT rows and a property column."""
    if not HAS_POLARS:
        pytest.skip("polars not installed")
    return pl.DataFrame(
        {
            "geometry": ["POINT (4.9 52.37)", "POINT (5.1 52.09)"],
            "name": ["Amsterdam", "Utrecht"],
            "score": [100, 80],
        }
    )


@pytest.fixture
def polygon_pandas() -> pd.DataFrame:
    """Pandas DataFrame with a single Polygon WKT row."""
    return pd.DataFrame(
        {
            "geometry": ["POLYGON ((4.85 52.35, 4.95 52.35, 4.95 52.40, 4.85 52.40, 4.85 52.35))"],
            "label": ["Noord-Holland"],
        }
    )


# ===================================================================
# TestDataFrameConversion — unit tests for dataframe_to_geojson()
# ===================================================================


class TestDataFrameConversion:
    """Scenarios for converting DataFrames to GeoJSON FeatureCollections."""

    def test_pandas_points_produce_feature_collection(self, point_pandas: pd.DataFrame) -> None:
        """
        Scenario: Convert a pandas DataFrame with Point WKT to a FeatureCollection.

        Given: A pandas DataFrame with two Point rows
        When: dataframe_to_geojson is called
        Then: The result is a FeatureCollection with two features
        """
        # Act
        result = dataframe_to_geojson(point_pandas)

        # Assert
        assert result["type"] == "FeatureCollection"
        assert len(result["features"]) == 2
        assert result["features"][0]["type"] == "Feature"

    @skip_if_no_polars
    def test_polars_points_produce_feature_collection(self, point_polars: "pl.DataFrame") -> None:
        """
        Scenario: Convert a polars DataFrame with Point WKT to a FeatureCollection.

        Given: A polars DataFrame with two Point rows
        When: dataframe_to_geojson is called
        Then: The result is a FeatureCollection with two features
        """
        # Act
        result = dataframe_to_geojson(point_polars)

        # Assert
        assert result["type"] == "FeatureCollection"
        assert len(result["features"]) == 2

    def test_properties_from_other_columns_are_preserved(self, point_pandas: pd.DataFrame) -> None:
        """
        Scenario: Non-geometry columns appear as Feature properties.

        Given: A DataFrame with geometry, name, and score columns
        When: dataframe_to_geojson is called
        Then: name and score appear in each Feature's properties
        """
        # Act
        result = dataframe_to_geojson(point_pandas)

        # Assert
        props = result["features"][0]["properties"]
        assert "name" in props
        assert "score" in props
        assert props["name"] == "Amsterdam"

    def test_geometry_column_not_in_properties(self, point_pandas: pd.DataFrame) -> None:
        """
        Scenario: The WKT geometry column is removed from Feature properties.

        Given: A DataFrame with a geometry column
        When: dataframe_to_geojson is called
        Then: The geometry key does not appear in Feature properties
        """
        # Act
        result = dataframe_to_geojson(point_pandas)

        # Assert
        assert "geometry" not in result["features"][0]["properties"]

    def test_custom_geometry_column_name(self) -> None:
        """
        Scenario: Use a non-default geometry column name.

        Given: A DataFrame with a column named 'wkt' instead of 'geometry'
        When: dataframe_to_geojson is called with geometry_col='wkt'
        Then: Two features are produced without error
        """
        # Arrange
        data = pd.DataFrame({"wkt": ["POINT (4.9 52.37)", "POINT (5.1 52.09)"], "id": [1, 2]})

        # Act
        result = dataframe_to_geojson(data, geometry_col="wkt")

        # Assert
        assert len(result["features"]) == 2
        assert "wkt" not in result["features"][0]["properties"]

    def test_polygon_wkt_produces_polygon_geometry(self, polygon_pandas: pd.DataFrame) -> None:
        """
        Scenario: A Polygon WKT row produces a GeoJSON Polygon feature.

        Given: A DataFrame with a Polygon WKT row
        When: dataframe_to_geojson is called
        Then: The feature geometry type is 'Polygon'
        """
        # Act
        result = dataframe_to_geojson(polygon_pandas)

        # Assert
        assert result["features"][0]["geometry"]["type"] == "Polygon"

    def test_linestring_wkt_produces_linestring_geometry(self) -> None:
        """
        Scenario: A LineString WKT row produces a GeoJSON LineString feature.

        Given: A DataFrame with a LineString WKT row
        When: dataframe_to_geojson is called
        Then: The feature geometry type is 'LineString'
        """
        # Arrange
        data = pd.DataFrame({"geometry": ["LINESTRING (4.9 52.37, 5.1 52.09)"]})

        # Act
        result = dataframe_to_geojson(data)

        # Assert
        assert result["features"][0]["geometry"]["type"] == "LineString"

    def test_mixed_geometry_types_all_converted(self) -> None:
        """
        Scenario: A DataFrame with mixed geometry types is fully converted.

        Given: A DataFrame with a Point and a Polygon row
        When: dataframe_to_geojson is called
        Then: Both features are created without error
        """
        # Arrange
        data = pd.DataFrame(
            {
                "geometry": [
                    "POINT (4.9 52.37)",
                    "POLYGON ((4.85 52.35, 4.95 52.35, 4.95 52.40, 4.85 52.40, 4.85 52.35))",
                ]
            }
        )

        # Act
        result = dataframe_to_geojson(data)

        # Assert
        assert len(result["features"]) == 2
        assert result["features"][0]["geometry"]["type"] == "Point"
        assert result["features"][1]["geometry"]["type"] == "Polygon"

    def test_none_geometry_row_is_skipped_with_warning(self) -> None:
        """
        Scenario: A row with a None geometry value is skipped.

        Given: A DataFrame where one geometry cell is None
        When: dataframe_to_geojson is called
        Then: That row is skipped, a UserWarning is emitted, and only one feature is returned
        """
        # Arrange
        data = pd.DataFrame({"geometry": ["POINT (4.9 52.37)", None], "name": ["A", "B"]})

        # Act / Assert
        with pytest.warns(UserWarning, match="Row 1"):
            result = dataframe_to_geojson(data)

        assert len(result["features"]) == 1

    def test_empty_string_geometry_row_is_skipped_with_warning(self) -> None:
        """
        Scenario: A row with an empty string geometry value is skipped.

        Given: A DataFrame where one geometry cell is an empty string
        When: dataframe_to_geojson is called
        Then: That row is skipped, a UserWarning is emitted
        """
        # Arrange
        data = pd.DataFrame({"geometry": ["POINT (4.9 52.37)", ""]})

        # Act / Assert
        with pytest.warns(UserWarning, match="Row 1"):
            result = dataframe_to_geojson(data)

        assert len(result["features"]) == 1

    def test_invalid_wkt_raises_value_error_with_row_index(self) -> None:
        """
        Scenario: A cell with invalid WKT raises a ValueError with context.

        Given: A DataFrame where one geometry cell contains invalid WKT
        When: dataframe_to_geojson is called
        Then: ValueError is raised and the message includes the row index
        """
        # Arrange
        data = pd.DataFrame({"geometry": ["NOT VALID WKT"]})

        # Act / Assert
        with pytest.raises(ValueError, match="Row 0"):
            dataframe_to_geojson(data)

    def test_missing_geometry_column_raises_value_error(self, point_pandas: pd.DataFrame) -> None:
        """
        Scenario: Passing a wrong geometry column name raises ValueError.

        Given: A DataFrame without a column named 'geom'
        When: dataframe_to_geojson is called with geometry_col='geom'
        Then: ValueError is raised and the message names the missing column
        """
        # Act / Assert
        with pytest.raises(ValueError, match="'geom'"):
            dataframe_to_geojson(point_pandas, geometry_col="geom")

    def test_empty_dataframe_raises_value_error(self) -> None:
        """
        Scenario: Passing an empty DataFrame raises ValueError.

        Given: A pandas DataFrame with zero rows
        When: dataframe_to_geojson is called
        Then: ValueError is raised with a message about emptiness
        """
        # Arrange
        data = pd.DataFrame({"geometry": pd.Series([], dtype=str)})

        # Act / Assert
        with pytest.raises(ValueError, match="empty"):
            dataframe_to_geojson(data)

    def test_wrong_input_type_raises_type_error(self) -> None:
        """
        Scenario: Passing something that is not a DataFrame raises TypeError.

        Given: A plain Python list
        When: dataframe_to_geojson is called
        Then: TypeError is raised
        """
        # Act / Assert
        with pytest.raises(TypeError):
            dataframe_to_geojson([{"geometry": "POINT (4.9 52.37)"}])

    def test_pandas_numpy_scalars_are_json_serialisable(self) -> None:
        """
        Scenario: pandas integer/float columns (numpy scalars) survive JSON serialisation.

        Given: A pandas DataFrame with int and float property columns
        When: dataframe_to_geojson is called and the result is passed to json.dumps
        Then: No TypeError is raised
        """
        # Arrange — pandas stores int/float columns as numpy dtypes
        data = pd.DataFrame({"geometry": ["POINT (4.9 52.37)"], "count": [42], "ratio": [0.75]})

        # Act
        result = dataframe_to_geojson(data)

        # Assert — must not raise
        serialised = json.dumps(result)
        assert "42" in serialised

    def test_coerce_value_converts_numpy_scalar_to_python_native(self) -> None:
        """
        Scenario: _coerce_value converts numpy scalars to plain Python types.

        Given: A numpy int64 scalar (which has an .item() method)
        When: _coerce_value is called
        Then: A plain Python int is returned, not a numpy type

        Also: plain Python values pass through unchanged.
        """
        # Numpy scalar → Python native
        result = _coerce_value(np.int64(42))
        assert result == 42
        assert type(result) is int

        # Plain Python value → unchanged
        assert _coerce_value("text") == "text"
        assert _coerce_value(3.14) == 3.14


# ===================================================================
# TestAddDataFrame — integration tests for Map.add_dataframe()
# ===================================================================


class TestAddDataFrame:
    """Scenarios for Map.add_dataframe() end-to-end."""

    def test_returns_self_for_fluent_chaining(self, point_pandas: pd.DataFrame) -> None:
        """
        Scenario: add_dataframe returns the Map instance.

        Given: An empty map and a valid DataFrame
        When: add_dataframe is called
        Then: The return value is the same Map object
        """
        # Arrange
        m = Map()

        # Act
        result = m.add_dataframe(point_pandas)

        # Assert
        assert result is m

    def test_bounds_are_updated_after_adding_dataframe(self, point_pandas: pd.DataFrame) -> None:
        """
        Scenario: Map bounds include the added DataFrame geometries.

        Given: An empty map with no bounds
        When: add_dataframe is called with a two-point DataFrame
        Then: The map's internal bounds list is non-empty
        """
        # Arrange
        m = Map()
        assert len(m._bounds) == 0

        # Act
        m.add_dataframe(point_pandas)

        # Assert
        assert len(m._bounds) > 0

    def test_hover_fields_appear_in_rendered_html(self, point_pandas: pd.DataFrame) -> None:
        """
        Scenario: hover_fields are forwarded to the GeoJSON tooltip.

        Given: A DataFrame with a 'name' column
        When: add_dataframe is called with hover_fields=['name']
        Then: The rendered HTML contains 'name'
        """
        # Arrange
        m = Map()

        # Act
        m.add_dataframe(point_pandas, hover_fields=["name"])
        html = m.to_html()

        # Assert
        assert "name" in html

    def test_style_is_accepted_without_error(self, point_pandas: pd.DataFrame) -> None:
        """
        Scenario: A custom style dict is forwarded without raising.

        Given: A DataFrame and a style dict
        When: add_dataframe is called with style={'color': '#ff0000'}
        Then: No exception is raised and self is returned
        """
        # Arrange
        m = Map()

        # Act — should not raise
        result = m.add_dataframe(point_pandas, style={"color": "#ff0000"})

        # Assert
        assert result is m

    def test_fluent_chain_two_dataframes(self, point_pandas: pd.DataFrame) -> None:
        """
        Scenario: Two DataFrames are added via method chaining.

        Given: Two DataFrames
        When: add_dataframe is chained twice
        Then: No exception is raised and the final result is the Map
        """
        # Arrange
        m = Map()

        # Act
        result = m.add_dataframe(point_pandas).add_dataframe(point_pandas)

        # Assert
        assert result is m

    def test_invalid_wkt_propagates_as_value_error(self) -> None:
        """
        Scenario: Invalid WKT in a DataFrame propagates out of add_dataframe.

        Given: A DataFrame with invalid WKT
        When: add_dataframe is called
        Then: ValueError propagates to the caller
        """
        # Arrange
        data = pd.DataFrame({"geometry": ["INVALID WKT"]})
        m = Map()

        # Act / Assert
        with pytest.raises(ValueError):
            m.add_dataframe(data)

    def test_wrong_type_propagates_as_type_error(self) -> None:
        """
        Scenario: Passing a dict instead of a DataFrame propagates TypeError.

        Given: A plain Python dict
        When: add_dataframe is called
        Then: TypeError propagates to the caller
        """
        # Arrange
        m = Map()

        # Act / Assert
        with pytest.raises(TypeError):
            m.add_dataframe({"geometry": "POINT (4.9 52.37)"})
