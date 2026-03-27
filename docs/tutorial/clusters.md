# Marker Clusters

When you have hundreds of markers, the map becomes unreadable at low zoom. Marker clusters group nearby points into numbered bubbles that expand as you zoom in.

```python exec="true" html="true" source="tabbed-right"
import random
from shapely.geometry import Point
from mapyta import Map

random.seed(42)
cafes = [Point(4.88 + random.uniform(-0.02, 0.02), 52.36 + random.uniform(-0.01, 0.01)) for _ in range(50)]
labels = ["☕"] * 50
hovers = [f"**Café #{i + 1}**" for i in range(50)]

m = Map(title="Amsterdam Cafés")
m.add_marker_cluster(points=cafes, labels=labels, hovers=hovers, name="Cafés")

m.to_html("clusters.html")

print(m.to_html()) # markdown-exec: hide
```

At low zoom you'll see cluster bubbles with counts. Zoom in and they split into individual ☕ markers.

## Parameters

| Parameter | Description |
|-----------|-------------|
| `points` | List of Shapely `Point` objects |
| `labels` | Marker text per point (emoji, text, or FA icon name) |
| `hovers` | Markdown tooltip per point |
| `popups` | Markdown popup per point |
| `captions` | Text label below each marker |
| `marker_style` | CSS dict applied to all markers |
| `caption_style` | CSS dict for captions |
| `name` | Cluster group name |
| `min_zoom` | Zoom level at which markers appear individually |
| `popup_style` | `PopupStyle` or dict for popup dimensions |

**Next:** [GeoPandas Integration](geodataframe.md) — build a map directly from a GeoDataFrame.
