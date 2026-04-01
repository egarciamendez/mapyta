# Zoom-dependent visibility

Sometimes a layer only makes sense when the user is zoomed in far enough. Street-level labels clutter a country-wide view; building outlines are invisible at national scale. The `min_zoom` parameter lets you attach a zoom threshold to any geometry: the layer is hidden below that zoom level and appears when the user crosses it.

```python exec="true" html="true" source="tabbed-right"
from shapely.geometry import Point, LineString, Polygon
from mapyta import Map, StrokeStyle, FillStyle, MapConfig

m = Map(
    center=(52.090, 5.120),
    title="Zoom in to see more detail",
    config=MapConfig(zoom_start=12),
)

# Always visible — neighbourhood outline
m.add_polygon(
    Polygon([(5.108, 52.083), (5.135, 52.083), (5.135, 52.098), (5.108, 52.098)]),
    tooltip="**Binnenstad Utrecht**",
    stroke=StrokeStyle(color="#2c3e50", weight=2),
    fill=FillStyle(color="#ecf0f1", opacity=0.4),
)

# Visible from zoom 14 — main street
m.add_linestring(
    LineString([(5.115, 52.090), (5.122, 52.093)]),
    tooltip="Oudegracht",
    stroke=StrokeStyle(color="#e67e22", weight=3),
    min_zoom=14,
)

# Visible from zoom 15 — individual points of interest
m.add_point(Point(5.1213, 52.0908), marker="🏛️", tooltip="**Dom Tower**", min_zoom=15)
m.add_point(Point(5.1178, 52.0865), marker="🖼️", tooltip="**Centraal Museum**", min_zoom=15)
m.add_point(Point(5.1152, 52.0932), marker="📚", tooltip="**University Library**", min_zoom=15)

m.to_html("min_zoom.html")

print(m.to_html())  # markdown-exec: hide
```

Zoom in on the map to see the street appear at zoom 14, then the individual markers at zoom 15.

## How it works

Mapyta injects a small JavaScript block into the exported HTML. On every `zoomend` event, Leaflet checks each registered layer against its threshold and calls `addTo(map)` or `removeLayer()` accordingly:

```
zoom < min_zoom  →  layer hidden
zoom ≥ min_zoom  →  layer visible
```

The check also runs once on load, so layers start hidden if the initial zoom is below their threshold.

## Supported geometry types

`min_zoom` is available on every `add_*` method that places a layer:

| Method | Notes |
|--------|-------|
| `add_point()` | Hides the marker icon |
| `add_circle()` | Hides the circle marker |
| `add_linestring()` | Hides the polyline |
| `add_polygon()` | Hides the polygon |
| `add_multilinestring()` | Applies the threshold to each sub-line |
| `add_multipolygon()` | Applies the threshold to each sub-polygon |
| `add_multipoint()` | Applies the threshold to each sub-point |
| `add_marker_cluster()` | Hides the entire cluster group |
| `add_text()` | Hides the text annotation |
| `add_geometry()` | Dispatches to the correct method above |

## Parameters

| Value | Behaviour |
|-------|-----------|
| `None` (default) | Always visible |
| `0` | Always visible (treated the same as `None`) |
| `13` | Hidden below zoom 13, visible at 13 and above |

## Combining with feature groups

`min_zoom` and feature groups are independent. A layer can belong to a group *and* have a zoom threshold. The group toggle controls whether the layer is in the map at all; `min_zoom` controls whether it is rendered at the current zoom within that group.

```python
from shapely.geometry import Point
from mapyta import Map

m = Map()

m.create_feature_group("🏛️ Museums")
m.add_point(Point(5.1213, 52.0908), marker="🏛️", tooltip="Dom Tower", min_zoom=14)
m.add_point(Point(5.1178, 52.0865), marker="🖼️", tooltip="Centraal Museum", min_zoom=14)

m.reset_target()
m.add_layer_control()
```

## Using add_geometry()

`add_geometry()` dispatches to the right method automatically, so you can use it with any Shapely type and still set `min_zoom`:

```python
from shapely.geometry import Point, LineString, Polygon
from mapyta import Map

m = Map()

for geom in [Point(5.12, 52.09), LineString([(5.11, 52.09), (5.13, 52.09)])]:
    m.add_geometry(geom, hover="Zoom in to see me", min_zoom=14)
```
