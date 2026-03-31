# Coordinate Detection

Working with Dutch RD New coordinates (EPSG:28992)? Just pass them in. Map detects the coordinate range and transforms to WGS84 automatically.

```python exec="true" html="true" source="tabbed-right"
from shapely.geometry import Point
from mapyta import Map

# These are RD New coordinates (x: 0–300k, y: 300k–625k)
m = Map(title="RD New Auto-Detection")
m.add_point(
    point=Point(121_000, 487_000),
    marker="📍",
    tooltip="**Amsterdam** (from RD New coordinates)",
)

m.to_html("rd_new.html")

print(m.to_html()) # markdown-exec: hide
```

## How it works

Map checks whether the x-coordinate is between 0–300,000 and y is between 300,000–625,000. If so, it assumes EPSG:28992 (RD New) and transforms to WGS84 via pyproj.

For coordinates outside that range, nothing happens, they're assumed to be WGS84 already.

You can also set the CRS explicitly on the constructor:

```python
m = Map(title="Explicit CRS", source_crs="EPSG:28992")
```

!!! info "Mixing CRS systems"

    Auto-detection runs on the first coordinate of each geometry. This means you can't mix RD New and WGS84 geometries on the same map without setting `source_crs` explicitly on the constructor, doing so will force all geometries through the same transformation.
