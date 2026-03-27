# Heatmaps

For dense point data — sensor readings, incidents, GPS traces — a heatmap shows intensity patterns better than individual markers.

```python exec="true" html="true" source="tabbed-right"
import random
from shapely.geometry import Point
from mapyta import Map, HeatmapStyle

random.seed(42)
points = [
    Point(4.85 + random.gauss(0, 0.03), 52.35 + random.gauss(0, 0.015))
    for _ in range(200)
]

m = Map(title="Activity Heatmap")
m.add_heatmap(
    points=points,
    style=HeatmapStyle(radius=20, blur=15, min_opacity=0.4),
)

m.to_html("heatmap.html")

print(m.to_html()) # markdown-exec: hide
```

## How it works

**`add_heatmap()`** accepts:

- A list of Shapely `Point` objects
- Raw `(lat, lon)` tuples
- `(lat, lon, intensity)` tuples to weight certain points more heavily

**`HeatmapStyle`** fields:

| Field | Default | Description |
|-------|---------|-------------|
| `radius` | 15 | Spread radius per point in pixels |
| `blur` | 10 | Blur radius in pixels |
| `min_opacity` | 0.3 | Minimum heatmap opacity |
| `max_zoom` | 18 | Zoom at which points reach full intensity |
| `gradient` | None | Custom gradient `{0.4: "blue", 0.6: "lime", 1.0: "red"}` |
