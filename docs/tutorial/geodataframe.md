# GeoPandas Integration

If you're working with a `GeoDataFrame`, you don't need to loop through rows yourself. The `from_geodataframe()` classmethod handles everything: CRS reprojection, per-row coloring, tooltips, and labels.

!!! warning "Optional dependency"

    GeoPandas is not installed with mapyta by default. Install it separately:

    ```bash
    pip install geopandas
    # or
    uv add geopandas
    ```

```python
import geopandas as gpd
from shapely.geometry import Point
from mapyta import Map

gdf = gpd.GeoDataFrame(
    {
        "name": ["Amsterdam", "Rotterdam", "Utrecht"],
        "population": [872_680, 651_446, 361_924],
        "geometry": [Point(4.9041, 52.3676), Point(4.4777, 51.9244), Point(5.1214, 52.0907)],
    },
    crs="EPSG:4326",
)

m = Map.from_geodataframe(
    gdf=gdf,
    hover_columns=["name", "population"],
    color_column="population",
    legend_name="Population",
    title="Dutch Cities",
)

m.to_html("cities.html")
```

## How it works

**`color_column`** activates choropleth coloring. Each geometry gets a color from a linear colormap based on its numeric value. A legend is added automatically.

**`hover_columns`** builds a Markdown tooltip from the specified columns. Each column shows as `**column**: value`.

## Parameters

| Parameter | Description |
|-----------|-------------|
| `gdf` | A GeoPandas `GeoDataFrame` |
| `hover_columns` | Columns to include in the hover tooltip |
| `popup_columns` | Columns to include in the click popup |
| `label_column` | Column to use as marker text |
| `color_column` | Numeric column for choropleth coloring |
| `stroke` | `StrokeStyle` or dict for borders |
| `fill` | `FillStyle` or dict for fills |
| `marker_style` | CSS dict for point markers |
| `title` | Map title |
| `config` | `MapConfig` for tile provider, zoom, etc. |
| `legend_name` | Legend label when `color_column` is set |

**Next:** [Coordinate Detection](coordinates.md) — pass Dutch RD New coordinates directly, no reprojection needed.
