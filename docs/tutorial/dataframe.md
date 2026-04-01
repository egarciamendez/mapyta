# DataFrames (Pandas & Polars)

If your data lives in a Pandas or Polars DataFrame, you can add it directly to a map with `add_dataframe()`. The DataFrame needs one column with WKT geometry strings; all other columns become properties you can show in hover tooltips.

!!! note "Geometry must be in WGS84"

    The WKT strings in your geometry column must use geographic coordinates (longitude, latitude) in WGS84 (EPSG:4326). If your data is in RD New or another CRS, reproject it first.

## Minimal example

```python exec="true" html="true" source="tabbed-right"
import pandas as pd
from mapyta import Map

df = pd.DataFrame(
    {
        "geometry": [
            "POINT (4.9041 52.3676)",
            "POINT (5.1214 52.0907)",
            "POINT (4.4777 51.9244)",
        ],
        "city": ["Amsterdam", "Utrecht", "Rotterdam"],
        "population": [872_680, 361_924, 651_446],
    }
)

m = Map(title="Dutch Cities")
m.add_dataframe(df, hover_fields=["city", "population"])
m.to_html("cities.html")

print(m.to_html())  # markdown-exec: hide
```

## Polars works the same way

```python exec="true" html="true" source="tabbed-right"
import polars as pl
from mapyta import Map

df = pl.DataFrame(
    {
        "geometry": [
            "POINT (4.9041 52.3676)",
            "POINT (5.1214 52.0907)",
        ],
        "city": ["Amsterdam", "Utrecht"],
    }
)

m = Map(title="Cities")
m.add_dataframe(df, hover_fields=["city"])
m.to_html("cities.html")

print(m.to_html())  # markdown-exec: hide
```

## Polygons and lines

`add_dataframe()` works with any geometry type — not just points. The WKT column can contain `POLYGON`, `LINESTRING`, `MULTIPOLYGON`, or any combination.

```python exec="true" html="true" source="tabbed-right"
import pandas as pd
from mapyta import Map

df = pd.DataFrame(
    {
        "geometry": [
            "POLYGON ((4.85 52.35, 4.95 52.35, 4.95 52.40, 4.85 52.40, 4.85 52.35))",
            "LINESTRING (4.9 52.37, 5.0 52.38, 5.1 52.35)",
        ],
        "label": ["Zone A", "Route 1"],
    }
)

m = Map(title="Shapes")
m.add_dataframe(df, hover_fields=["label"])
m.to_html("shapes.html")

print(m.to_html())  # markdown-exec: hide
```

## Custom geometry column name

If your geometry column is not named `"geometry"`, pass the column name explicitly:

```python
m.add_dataframe(df, geometry_col="wkt_geom", hover_fields=["name"])
```

## Styling

Pass `style` and `highlight` dicts to control appearance — the same kwargs accepted by `add_geojson()`:

```python
m.add_dataframe(
    df,
    hover_fields=["name"],
    style={"color": "#e74c3c", "weight": 2, "fillOpacity": 0.4},
    highlight={"weight": 4, "fillOpacity": 0.7},
)
```

## Parameters

| Parameter | Description |
|-----------|-------------|
| `df` | Pandas or Polars DataFrame |
| `geometry_col` | Column with WKT geometry strings (default: `"geometry"`) |
| `hover_fields` | Columns to show in the hover tooltip |
| `style` | Folium GeoJson style dict (color, weight, fillOpacity, …) |
| `highlight` | Style applied on mouse-over |

## When to use `from_geodataframe()` instead

Use `Map.from_geodataframe()` when you have a **GeoPandas** `GeoDataFrame` with Shapely geometry objects and want features like per-row coloring, automatic CRS reprojection, or click popups with multiple columns. `add_dataframe()` is the right choice when you have a plain Pandas or Polars DataFrame with WKT strings.
