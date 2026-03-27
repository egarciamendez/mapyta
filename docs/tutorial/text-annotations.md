# Text Annotations

Sometimes you need a floating label on the map — not tied to a marker, just text at a location.

```python exec="true" html="true" source="tabbed-right"
from shapely.geometry import Point
from mapyta import Map

m = Map(title="Annotations")

m.add_text(
    point=Point(4.9041, 52.3676),
    text="Amsterdam Centrum",
    style={
        "font-size": "16px",
        "color": "black",
        "background-color": "white",
        "padding": "2px 4px",
        "border-radius": "4px",
        "border": "1px solid #ccc",
    },
)

print(m.to_html()) # markdown-exec: hide
```

**`add_text()`** accepts a Shapely `Point(lon, lat)` or a plain `(lat, lon)` tuple. The `style` parameter is a CSS dict — any CSS property works.

## Site plans with icon markers

For geotechnical or infrastructure projects you often need a site plan with survey markers, borehole locations, or measurement points.

```python exec="true" html="true" source="tabbed-right"
from shapely.geometry import Point
from mapyta import Map, MapConfig

surveys = [
    {"lon": 4.6820, "lat": 52.3680, "name": "1123-25N-S13", "x_rd": 107650, "y_rd": 411350},
    {"lon": 4.6835, "lat": 52.3655, "name": "1123-25N-S12", "x_rd": 107680, "y_rd": 411280},
    {"lon": 4.6850, "lat": 52.3630, "name": "1123-25N-S11", "x_rd": 107710, "y_rd": 411240},
    {"lon": 4.6880, "lat": 52.3628, "name": "1123-25N-S14", "x_rd": 107750, "y_rd": 411235},
    {"lon": 4.6950, "lat": 52.3690, "name": "23248_S013",   "x_rd": 107850, "y_rd": 411380},
    {"lon": 4.6990, "lat": 52.3685, "name": "23248_S019",   "x_rd": 107890, "y_rd": 411370},
    {"lon": 4.6980, "lat": 52.3640, "name": "23248_S005",   "x_rd": 107880, "y_rd": 411260},
]

m = Map(
    title="CPT Survey Locations",
    config=MapConfig(tile_layer="openstreetmap", zoom_start=15),
)

for s in surveys:
    m.add_point(
        point=Point(s["lon"], s["lat"]),
        marker="fa-location-dot",
        tooltip=f'**Naam:** {s["name"]}\n\nx [m RD] = {s["x_rd"]}\n\ny [m RD] = {s["y_rd"]}',
        marker_style={"color": "black"},
        caption=s["name"],
    )

m.to_html("site_plan.html")

print(m.to_html()) # markdown-exec: hide
```

**`marker`** supports bare FontAwesome names (`"fa-location-dot"`) — the `"fa-solid"` prefix is added automatically. You can also use emoji (`"📍"`) or full CSS class strings.

**`caption`** works with any marker type. By default it has a transparent background; pass a `caption_style` CSS dict to override.

!!! tip "Mix marker types on the same map"

    ```python
    m.add_point(pt, marker="fa-location-dot", marker_style={"color": "red"}, caption="CPT-01")
    m.add_point(pt, marker="🏗️", caption="Site office")
    ```
