# Text Annotations

Sometimes you need a floating label on the map, not tied to a marker, just text at a location.

```python exec="true" html="true" source="tabbed-right"
from shapely.geometry import Point
from mapyta import Map

m = Map(title="Annotations")

m.add_text(
    point=Point(5.1213, 52.0908),
    text="Utrecht Centrum",
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

**`add_text()`** accepts a Shapely `Point(lon, lat)` or a plain `(lat, lon)` tuple. The `style` parameter is a CSS dict, any CSS property works.

## Site plans with icon markers

For geotechnical or infrastructure projects you often need a site plan with survey markers, borehole locations, or measurement points.

```python exec="true" html="true" source="tabbed-right"
from shapely.geometry import Point
from mapyta import Map, MapConfig

surveys = [
    {"lon": 5.0420, "lat": 52.0900, "name": "1123-25N-S13", "x_rd": 128650, "y_rd": 454350},
    {"lon": 5.0435, "lat": 52.0875, "name": "1123-25N-S12", "x_rd": 128680, "y_rd": 454280},
    {"lon": 5.0450, "lat": 52.0850, "name": "1123-25N-S11", "x_rd": 128710, "y_rd": 454210},
    {"lon": 5.0480, "lat": 52.0848, "name": "1123-25N-S14", "x_rd": 128750, "y_rd": 454205},
    {"lon": 5.0550, "lat": 52.0910, "name": "23248_S013",   "x_rd": 128850, "y_rd": 454380},
    {"lon": 5.0590, "lat": 52.0905, "name": "23248_S019",   "x_rd": 128890, "y_rd": 454370},
    {"lon": 5.0580, "lat": 52.0860, "name": "23248_S005",   "x_rd": 128880, "y_rd": 454240},
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

**`marker`** supports bare FontAwesome names (`"fa-location-dot"`), the `"fa-solid"` prefix is added automatically. You can also use emoji (`"📍"`) or full CSS class strings.

**`caption`** works with any marker type. By default it has a transparent background; pass a `caption_style` CSS dict to override.

!!! tip "Mix marker types on the same map"

    ```python
    m.add_point(pt, marker="fa-location-dot", marker_style={"color": "red"}, caption="CPT-01")
    m.add_point(pt, marker="🏗️", caption="Site office")
    ```
