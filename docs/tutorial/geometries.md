# Lines & Polygons

Points are useful, but maps really come alive with shapes. Let's draw a walking route and highlight a neighbourhood in Utrecht.

```python exec="true" html="true" source="tabbed-right"
from shapely.geometry import LineString, Polygon
from mapyta import Map, StrokeStyle, FillStyle

m = Map(title="Utrecht Walk")

route = LineString([
    (5.1097, 52.0894),  # Centraal Station
    (5.1133, 52.0934),  # Vredenburg
    (5.1197, 52.0919),  # Neude
    (5.1213, 52.0908),  # Dom Tower
])
m.add_linestring(
    line=route,
    tooltip="**Walking route**\n*Centraal → Dom Tower*",
    stroke=StrokeStyle(color="#e74c3c", weight=4, dash_array="10 6"),
)

wittevrouwen = Polygon([
    (5.1195, 52.0915),  # SW near Dom Tower
    (5.1242, 52.0897),  # S along Drift
    (5.1298, 52.0893),  # SE bend
    (5.1362, 52.0908),  # E along Singel (south)
    (5.1378, 52.0948),  # NE corner
    (5.1318, 52.0975),  # N Wittevrouwensingel
    (5.1252, 52.0970),  # NW notch
    (5.1208, 52.0952),  # W back toward Dom
])
m.add_polygon(
    polygon=wittevrouwen,
    tooltip="**Wittevrouwen**\nHistoric neighbourhood",
    stroke=StrokeStyle(color="#2ecc71", weight=2),
    fill=FillStyle(color="#2ecc71", opacity=0.15),
)

m.to_html("utrecht_walk.html")

print(m.to_html()) # markdown-exec: hide # markdown-exec: hide
```

## How it works

**Coordinates are always `(longitude, latitude)`**, that's the Shapely convention (x, y). Map handles the flip to Leaflet's `(lat, lon)` internally.

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
    poly = Polygon([
        (5.100, 52.080), (5.120, 52.076), (5.138, 52.083),
        (5.133, 52.095), (5.114, 52.099), (5.101, 52.090),
    ])

    m.add_polygon(
        poly,
        stroke={"color": "red", "weight": 4},
        fill={"color": "red", "opacity": 0.15},
    )

    print(m.to_html()) # markdown-exec: hide # markdown-exec: hide
    ```

    Use dataclass objects when you want IDE autocomplete or want to reuse a style across multiple geometries:

    ```python exec="true" html="true" source="tabbed-left"
    from shapely.geometry import Polygon
    from mapyta import Map, StrokeStyle

    m = Map(title="Reusable styles")
    my_stroke = StrokeStyle(color="red", weight=4)

    poly1 = Polygon([
        (5.100, 52.080), (5.120, 52.076), (5.138, 52.083),
        (5.133, 52.095), (5.114, 52.099), (5.101, 52.090),
    ])
    poly2 = Polygon([
        (5.082, 52.088), (5.098, 52.083), (5.108, 52.091),
        (5.102, 52.101), (5.083, 52.098), (5.076, 52.093),
    ])
    m.add_polygon(poly1, stroke=my_stroke)
    m.add_polygon(poly2, stroke=my_stroke)

    print(m.to_html()) # markdown-exec: hide # markdown-exec: hide
    ```

!!! tip "Polygons with holes"

    Pass interior rings as the second argument to `Polygon`, they render as cutouts:

    ```python exec="true" html="true" source="tabbed-left"
    from shapely.geometry import Polygon
    from mapyta import Map

    m = Map(title="Wilhelminapark")
    wilhelminapark = Polygon(
        [
            (5.1215, 52.0835), (5.1252, 52.0828), (5.1278, 52.0838),
            (5.1282, 52.0863), (5.1262, 52.0880), (5.1232, 52.0881),
            (5.1203, 52.0868), (5.1198, 52.0848),
        ],
        [[
            (5.1228, 52.0848), (5.1255, 52.0845), (5.1260, 52.0860),
            (5.1242, 52.0867), (5.1222, 52.0859),
        ]],
    )
    m.add_polygon(wilhelminapark, tooltip="**Wilhelminapark**, the hole is the pond!")

    print(m.to_html()) # markdown-exec: hide
    ```
