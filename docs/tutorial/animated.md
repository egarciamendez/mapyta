# Animated Layers

Three plugins turn static maps into animated ones: ant paths trace routes with marching-ants animation, heatmaps-with-time show how density shifts across time steps, and timestamped GeoJSON animates arbitrary features along a timeline.

---

## Ant paths

An ant path is a polyline with a moving dash pattern — the gaps appear to travel forward along the route, making direction of travel immediately obvious.

```python exec="true" html="true" source="tabbed-right"
from shapely.geometry import LineString
from mapyta import Map

m = Map(title="Tram route 9 — Utrecht")

route = LineString([
    (5.1085, 52.0893),  # Centraal Station
    (5.1130, 52.0877),
    (5.1178, 52.0865),
    (5.1213, 52.0851),
    (5.1268, 52.0838),  # Maliebaan
])

m.add_ant_path(
    route,
    tooltip="**Tram 9** — richting Maliebaan",
    color="#e74c3c",
    pulse_color="#ffffff",
    weight=5,
    delay=300,
)

m.to_html("ant_path.html")

print(m.to_html())  # markdown-exec: hide
```

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `line` | — | `LineString` or `list[Point]` — the route geometry |
| `tooltip` | `None` | Markdown tooltip |
| `popup` | `None` | Markdown popup |
| `color` | `"#0000FF"` | Line colour |
| `pulse_color` | `"#FFFFFF"` | Colour of the travelling gap |
| `weight` | `5` | Line width in pixels |
| `delay` | `400` | Animation step interval in milliseconds — lower is faster |
| `dash_array` | `None` | `[dash, gap]` pattern in pixels; defaults to `[10, 20]` |
| `paused` | `False` | Start the animation paused |
| `reverse` | `False` | Reverse the direction of travel |

---

## Heatmap with time

`add_heatmap_with_time()` displays a heatmap that changes over time. A playback slider is injected into the map so users can step through or scrub between time steps.

```python exec="true" html="true" source="tabbed-right"
import random
from shapely.geometry import Point
from mapyta import Map

random.seed(0)

months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]

# Simulate a hotspot that drifts north-east over time
data = [
    [Point(5.10 + i * 0.004 + random.gauss(0, 0.02), 52.07 + i * 0.003 + random.gauss(0, 0.01))
     for _ in range(60)]
    for i in range(len(months))
]

m = Map(title="Monthly activity — H1 2024")
m.add_heatmap_with_time(
    data=data,
    index=months,
    radius=18,
    max_opacity=0.7,
    auto_play=True,
)

m.to_html("heatmap_with_time.html")

print(m.to_html())  # markdown-exec: hide
```

Each entry in `data` is one time step and must be the same length as `index`. Points can be Shapely `Point` objects (longitude, latitude) or raw `(lat, lon)` or `(lat, lon, intensity)` tuples.

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `data` | — | List of per-timestep point lists |
| `index` | — | Label for each time step shown in the slider |
| `radius` | `15` | Point radius in pixels |
| `blur` | `0.8` | Blur amount (0–1) |
| `max_opacity` | `0.6` | Maximum opacity (0–1) |
| `min_opacity` | `0.0` | Minimum opacity (0–1) |
| `gradient` | `None` | Custom colour gradient e.g. `{0.0: "blue", 0.5: "yellow", 1.0: "red"}` |
| `auto_play` | `False` | Start playback automatically on load |
| `display_index` | `True` | Show the current time step label |
| `position` | `"bottomleft"` | Control position on the map |

`data` and `index` must have the same length — a `ValueError` is raised otherwise.

---

## Timestamped GeoJSON

`add_timestamped_geojson()` animates a GeoJSON `FeatureCollection` over time. Each feature must have a `times` property — an array of ISO 8601 timestamps, one per coordinate.

```python exec="true" html="true" source="tabbed-right"
from mapyta import Map

geojson = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [5.108, 52.090],
                    [5.115, 52.093],
                    [5.122, 52.096],
                    [5.130, 52.098],
                ],
            },
            "properties": {
                "times": [
                    "2024-06-01T08:00:00",
                    "2024-06-01T08:15:00",
                    "2024-06-01T08:30:00",
                    "2024-06-01T08:45:00",
                ],
                "style": {"color": "#e67e22", "weight": 4},
                "icon": "circle",
                "iconstyle": {
                    "fillColor": "#e67e22",
                    "fillOpacity": 1,
                    "stroke": True,
                    "radius": 6,
                    "color": "#fff",
                    "weight": 2,
                },
                "popup": "Morning commute",
            },
        }
    ],
}

m = Map(title="GPS trace replay")
m.add_timestamped_geojson(
    geojson,
    auto_play=True,
    loop=False,
    transition_time=500,
    period="PT15M",
    date_options="HH:mm",
)
m.to_html("gps_replay.html")

print(m.to_html())  # markdown-exec: hide
```

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `data` | — | GeoJSON `FeatureCollection` as a `dict`, JSON string, or file path |
| `auto_play` | `True` | Start playback when the map loads |
| `loop` | `True` | Loop the animation continuously |
| `transition_time` | `200` | Frame transition duration in milliseconds |
| `period` | `"P1D"` | ISO 8601 duration per slider step — `"P1D"` = 1 day, `"PT1H"` = 1 hour, `"PT1M"` = 1 minute |
| `date_options` | `"YYYY-MM-DD HH:mm:ss"` | [moment.js](https://momentjs.com/docs/#/displaying/) format string for the displayed timestamp |
| `duration` | `None` | How long each feature stays visible after its timestamp; `None` = stays visible forever |

### GeoJSON feature format

```python
{
    "type": "Feature",
    "geometry": {
        "type": "LineString",
        "coordinates": [[lon, lat], [lon, lat], ...],  # one pair per timestamp
    },
    "properties": {
        "times": ["2024-01-01T00:00:00", "2024-01-01T01:00:00", ...],
        "style": {"color": "#e74c3c", "weight": 3},
        # Use "circle" to show a dot at the current animated position.
        # Without this, a default Leaflet pin marker appears instead.
        "icon": "circle",
        "iconstyle": {
            "fillColor": "#e74c3c",
            "fillOpacity": 1,
            "stroke": True,
            "radius": 6,
            "color": "#fff",
            "weight": 2,
        },
        "popup": "Optional popup text",
    },
}
```

The `times` array must have exactly one entry per coordinate. Supported geometry types: `LineString`, `MultiPoint`, `MultiLineString`, `Polygon`, `MultiPolygon`.
