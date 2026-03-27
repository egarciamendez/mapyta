# Markers

The default marker is a down-arrow pin, but you can swap it for emojis, Font Awesome icons, or fixed-size circles. Marker styling uses plain CSS dicts — no special imports needed.

```python exec="true" html="true" source="tabbed-right"
from shapely.geometry import Point
from mapyta import Map, CircleStyle, StrokeStyle, FillStyle

m = Map(title="Marker Styles")

# Emoji marker
m.add_point(
    point=Point(4.9041, 52.3676),
    marker="🏛️",
    tooltip="**Royal Palace** (emoji marker)",
)

# Font Awesome icon marker with custom CSS
m.add_point(
    point=Point(4.8834, 52.3667),
    marker="fa-house",
    tooltip="**Anne Frank House** (Font Awesome marker)",
    marker_style={"font-size": "24px", "color": "green"},
)

# Circle marker (fixed pixel size, doesn't scale with zoom)
m.add_circle(
    point=Point(4.8795, 52.3600),
    tooltip="**Rijksmuseum** (circle marker)",
    style=CircleStyle(
        radius=12,
        stroke=StrokeStyle(color="#8e44ad", weight=2),
        fill=FillStyle(color="#8e44ad", opacity=0.5),
    ),
)

m.to_html("markers.html")

print(m.to_html())
```

## How it works

**`marker`** controls what's displayed at the point:

- Bare names like `"home"` → Glyphicon prefix added
- Names starting with `"fa-"` → `"fa-solid"` prefix added automatically
- Full CSS class strings like `"fa-solid fa-house"` → used as-is
- Non-ASCII text (emojis, any unicode) → rendered as a text `DivIcon`

**`marker_style`** is a plain CSS dict. Any CSS property works: `font-size`, `color`, `text-shadow`, etc.

**`add_circle()`** draws a `CircleMarker` — a circle that stays the same pixel size at every zoom level. Useful when you don't want markers overlapping at low zoom.

!!! tip "Captions below markers"

    The `caption` parameter places a text label just below any marker:

    ```python
    m.add_point(pt, marker="fa-location-dot", caption="CPT-01")
    m.add_point(pt, marker="📍", caption="Site office", caption_style={"font-size": "14px"})
    ```

    For marker and caption styling, pass a CSS dict — any CSS property is valid.

**Next:** [Tooltips & Popups](tooltips-popups.md) — markdown content, custom popup sizes, and raw HTML.
