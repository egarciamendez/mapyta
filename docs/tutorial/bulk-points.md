# Bulk Points

`add_points()` draws a whole set of markers as a single GeoJSON layer instead of one Leaflet marker per point. Reach for it when a loop over `add_point()` would turn hundreds of points into an HTML file that takes seconds to open.

```python exec="true" html="true" source="tabbed-right"
import random
from shapely.geometry import Point
from mapyta import Map

random.seed(7)
STATUS = [("#1a9850", "Approved"), ("#fee08b", "In review"), ("#d73027", "Rejected")]

points, captions, colors, tooltips = [], [], [], []
for i in range(150):
    color, label = random.choice(STATUS)
    points.append(Point(5.12 + random.uniform(-0.03, 0.03), 52.09 + random.uniform(-0.015, 0.015)))
    captions.append(f"CPT-{i + 1:03d}")
    colors.append(color)
    tooltips.append(f"**CPT-{i + 1:03d}**\n\nStatus: {label}")

m = Map(title="Cone penetration tests")
m.add_points(
    points=points,
    marker="triangle-bottom",
    captions=captions,
    colors=colors,
    tooltips=tooltips,
    name="CPTs",
    min_zoom_caption=15,
)
m.add_legend(entries=STATUS, title="Status")

m.to_html("bulk-points.html")

print(m.to_html()) # markdown-exec: hide
```

Zoom past level 15 and the captions appear; the markers themselves stay visible at every zoom.

## How it works

The coordinates and the per-point text are written once as GeoJSON, and every icon is built in the browser from one shared factory. That factory carries the marker markup and the caption CSS a single time, so adding a point costs a set of coordinates and its own text — not another copy of the styling.

What you give up is a per-point symbol. Some arguments describe the layer, the rest describe one point:

| Per layer | Per point |
|-----------|-----------|
| `marker` — the symbol every point uses | `captions` — text below the marker |
| `marker_style` — CSS for the symbol | `colors` — CSS colour, overriding `marker_style` |
| `caption_style` — CSS for the captions | `tooltips` — hover text, Markdown supported |
| `tooltip_style`, `popup_style` | `popups` — click text, Markdown supported |

The per-point sequences are optional, but any you pass must be exactly as long as `points`; a mismatch raises `ValueError` rather than silently dropping markers. Captions and colours are HTML-escaped, so values read straight from a data source are shown literally.

`name` labels the layer in the layer control, and `min_zoom` / `min_zoom_caption` gate the whole layer and its captions by zoom level, exactly as described under [Zoom-dependent Visibility](min-zoom.md).

!!! tip "Which method for which job"

    - **[`add_point()`](markers.md)** — each marker needs its own symbol, or there are few enough that the file size does not matter.
    - **`add_points()`** — many markers sharing one symbol, and the file has to stay small.
    - **[`add_marker_cluster()`](clusters.md)** — the goal is grouping overlapping markers at low zoom rather than a smaller file.

One difference from `add_point()`: `popup_style.use_iframe` has no effect here. Popup content always goes straight into the popup, because a base64 `data:` URL per point is a large part of what makes the one-marker-per-point output big.
