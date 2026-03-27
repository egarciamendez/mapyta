# Lines & Polygons

Points are useful, but maps really come alive with shapes. Let's draw a walking route and highlight a neighbourhood.

```python exec="true" html="true" source="tabbed-right"
from shapely.geometry import LineString, Polygon
from mapyta import Map, StrokeStyle, FillStyle

m = Map(title="Amsterdam Walk")

route = LineString([
    (4.8852, 52.3702),  # Centraal Station
    (4.8910, 52.3663),  # Damrak
    (4.8932, 52.3631),  # Dam Square
    (4.8840, 52.3569),  # Leidseplein
])
m.add_linestring(
    line=route,
    tooltip="**Walking route**\n*Centraal → Leidseplein*",
    stroke=StrokeStyle(color="#e74c3c", weight=4, dash_array="10 6"),
)

jordaan = Polygon([
    (4.8760, 52.3720), (4.8890, 52.3720),
    (4.8890, 52.3800), (4.8760, 52.3800),
])
m.add_polygon(
    polygon=jordaan,
    tooltip="**De Jordaan**\nHistoric neighbourhood",
    stroke=StrokeStyle(color="#2ecc71", weight=2),
    fill=FillStyle(color="#2ecc71", opacity=0.15),
)

m.to_html("amsterdam_walk.html")

print(m.to_html())
```

## How it works

**Coordinates are always `(longitude, latitude)`** — that's the Shapely convention (x, y). Map handles the flip to Leaflet's `(lat, lon)` internally.

**`StrokeStyle`** controls borders and lines. Fields: `color`, `weight` (pixels), `opacity`, and `dash_array` (SVG pattern like `"10 6"` for dashes).

**`FillStyle`** controls polygon fills: `color` and `opacity`. Skip it for the default blue at 20% opacity.

**Markdown in tooltips** supports `**bold**`, `*italic*`, `` `code` ``, `[links](url)`, `# headers`, and `- list items`. Use `\n` for line breaks.

!!! info "All geometry types"

    Map handles every Shapely geometry: `Point`, `LineString`, `Polygon`, `MultiPoint`, `MultiLineString`, `MultiPolygon`, and `LinearRing`. Use specific methods or **`add_geometry()`** which auto-dispatches by type:

    ```python
    m.add_geometry(some_shapely_object, tooltip="Works for any type")
    ```

!!! info "Style with dicts or dataclass objects"

    `StrokeStyle`, `FillStyle`, and `CircleStyle` accept either a dataclass instance or a plain dict with the same keys:

    ```python exec="true" html="true" source="tabbed-left"
    from shapely.geometry import Polygon
    from mapyta import Map

    m = Map(title="Quick styling")
    poly = Polygon([(4.9, 52.3), (5.0, 52.3), (5.0, 52.4), (4.9, 52.4)])

    m.add_polygon(
        poly,
        stroke={"color": "red", "weight": 4},
        fill={"color": "red", "opacity": 0.15},
    )

    print(m.to_html())
    ```

    Use dataclass objects when you want IDE autocomplete or want to reuse a style across multiple geometries:

    ```python exec="true" html="true" source="tabbed-left"
    from shapely.geometry import Polygon
    from mapyta import Map, StrokeStyle

    m = Map(title="Reusable styles")
    my_stroke = StrokeStyle(color="red", weight=4)

    poly1 = Polygon([(4.9, 52.3), (5.0, 52.3), (5.0, 52.4), (4.9, 52.4)])
    poly2 = Polygon([(4.85, 52.35), (4.95, 52.35), (4.95, 52.45), (4.85, 52.45)])
    m.add_polygon(poly1, stroke=my_stroke)
    m.add_polygon(poly2, stroke=my_stroke)

    print(m.to_html())
    ```

!!! tip "Polygons with holes"

    Pass interior rings as the second argument to `Polygon` — they render as cutouts:

    ```python
    vondelpark = Polygon(
        [(4.858, 52.353), (4.883, 52.353), (4.883, 52.362), (4.858, 52.362)],
        [[(4.865, 52.356), (4.875, 52.356), (4.875, 52.360), (4.865, 52.360)]],
    )
    m.add_polygon(vondelpark, tooltip="**Vondelpark** — the hole is the pond!")
    ```

**Next:** [Markers](markers.md) — swap the default arrow for emojis, icons, or circles.
