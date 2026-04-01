"""Convert Pandas or Polars DataFrames to GeoJSON FeatureCollections."""

from __future__ import annotations

import math
import warnings
from typing import Any

from shapely import wkt as shapely_wkt
from shapely.geometry import mapping


def _coerce_value(v: Any) -> Any:  # noqa: ANN401
    """Convert numpy scalar types to plain Python scalars.

    Parameters
    ----------
    v : Any
        Value from a DataFrame cell.

    Returns
    -------
    Any
        Plain Python scalar when the input is a numpy scalar; otherwise the original value.
    """
    if hasattr(v, "item"):
        return v.item()
    return v


def dataframe_to_geojson(df: Any, geometry_col: str = "geometry") -> dict:  # noqa: ANN401
    """Convert a Pandas or Polars DataFrame with a WKT geometry column to a GeoJSON FeatureCollection dict.

    Parameters
    ----------
    df : pandas.DataFrame | polars.DataFrame
        Input DataFrame. The geometry column must contain WKT strings in WGS84 (EPSG:4326).
        GeoPandas GeoDataFrames are not supported; use :meth:`Map.from_geodataframe` instead.
    geometry_col : str
        Name of the column that contains WKT geometry strings. Defaults to ``"geometry"``.

    Returns
    -------
    dict
        A GeoJSON FeatureCollection dict ready for :meth:`Map.add_geojson`.

    Raises
    ------
    TypeError
        If ``df`` is not a recognised Pandas or Polars DataFrame.
    ValueError
        If ``geometry_col`` is not present in the DataFrame columns.
    ValueError
        If the DataFrame is empty (zero rows).
    ValueError
        If a WKT string in the geometry column cannot be parsed.

    Warns
    -----
    UserWarning
        When a row contains a ``None`` or empty geometry value; that row is skipped.

    Examples
    --------
    >>> import pandas as pd
    >>> df = pd.DataFrame({"geometry": ["POINT (4.9 52.37)"], "name": ["Amsterdam"]})
    >>> fc = dataframe_to_geojson(df)
    >>> fc["type"]
    'FeatureCollection'
    >>> len(fc["features"])
    1
    """
    # --- Detect library and extract columns ---
    if hasattr(df, "to_dicts"):
        # Polars: columns is a list of strings
        columns = df.columns
    elif hasattr(df, "to_dict"):
        # Pandas: columns is an Index, convert for consistent membership testing
        columns = list(df.columns)
    else:
        raise TypeError(f"df must be a pandas or polars DataFrame, got {type(df).__name__!r}")

    # --- Validate geometry column ---
    if geometry_col not in columns:
        raise ValueError(f"geometry column {geometry_col!r} not found. Available columns: {list(columns)}")

    # --- Validate non-empty ---
    if len(df) == 0:
        raise ValueError("DataFrame is empty — nothing to add to the map.")

    # --- Normalise to list[dict] ---
    if hasattr(df, "to_dicts"):
        records: list[dict] = df.to_dicts()
    else:
        records = df.to_dict(orient="records")

    # --- Build GeoJSON features ---
    features = []
    for i, row in enumerate(records):
        wkt_value = row.pop(geometry_col)

        # Skip null / empty geometry rows (pandas converts None to float NaN in mixed columns)
        if wkt_value is None or wkt_value == "" or (isinstance(wkt_value, float) and math.isnan(wkt_value)):
            warnings.warn(f"Row {i}: geometry is null/empty — skipped.", UserWarning, stacklevel=2)
            continue

        # Parse WKT
        try:
            geom = shapely_wkt.loads(str(wkt_value))
        except Exception as exc:
            raise ValueError(f"Row {i}: invalid WKT {wkt_value!r} — {exc}") from exc

        # Coerce numpy scalars in properties (pandas DataFrames may produce them)
        props = {k: _coerce_value(v) for k, v in row.items()}

        features.append({"type": "Feature", "geometry": mapping(geom), "properties": props})

    return {"type": "FeatureCollection", "features": features}
