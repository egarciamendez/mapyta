---
hide:
  - navigation
---

# Showcase

**One import. A few method calls. A full interactive map.**

This page is the whole of mapyta on a single scroll. Every map below is
**real** — rendered live in your browser from the exact code shown. Skim it
top to bottom to see what mapyta can do, then follow the
*→ Full tutorial* link under any section for the details.

New to mapyta? Install it and you're ready:

```bash
uv add mapyta
# or
pip install mapyta
```

<div class="grid cards" markdown>

- :material-map-marker: **[Your first map](#your-first-map)**
- :material-vector-polyline: **[Geometries](#shapely-native-geometry)**
- :material-map-marker-star: **[Markers](#markers-your-way)**
- :material-comment-text: **[Tooltips & popups](#markdown-tooltips-popups)**
- :material-palette: **[Choropleth](#choropleth)**
- :material-fire: **[Heatmap](#heatmap)**
- :material-group: **[Clusters](#marker-clusters)**
- :material-table: **[DataFrame](#dataframe-in-one-line)**
- :material-magnify: **[Search](#search-box)**
- :material-draw: **[Drawing](#let-users-draw)**
- :material-motion-play: **[Animation](#animation)**
- :material-export: **[Export](#export-anywhere)**

</div>

---

## Your first map

The smallest complete map: one point, a hover tooltip, and a click popup.

```python exec="true" html="true" source="tabbed-right"
from shapely.geometry import Point
from mapyta import Map

m = Map(title="Hello Utrecht")
m.add_point(
    point=Point(5.121311, 52.090648),
    tooltip="**Utrecht**",
    popup="**Utrecht**\nCity in the Netherlands\nPopulation: ~350k",
    caption="UTR",
)

print(m.to_html())  # markdown-exec: hide
```

[:octicons-arrow-right-24: Full tutorial: Your First Map](tutorial/first-map.md)

---

## Shapely-native geometry

Pass `Point`, `LineString`, and `Polygon` straight from Shapely — no
conversion, no wrappers. Style each with plain dicts.

```python exec="true" html="true" source="tabbed-right"
from shapely.geometry import Point, LineString, Polygon
from mapyta import Map

m = Map(title="Geometries")
m.add_polygon(
    polygon=Polygon([(5.10, 52.08), (5.14, 52.08), (5.14, 52.10), (5.10, 52.10)]),
    tooltip="**Binnenstad**",
    stroke={"color": "green", "weight": 2},
    fill={"color": "blue", "opacity": 0.15},
)
m.add_linestring(
    line=LineString([(5.108, 52.089), (5.117, 52.086), (5.127, 52.084)]),
    tooltip="**Tram route**",
    stroke={"color": "red", "weight": 4, "dash_array": "10 6"},
)
m.add_point(Point(5.121, 52.091), marker="📍", tooltip="**Dom Tower**")
m.set_bounds(padding=0.005)

print(m.to_html())  # markdown-exec: hide
```

[:octicons-arrow-right-24: Full tutorial: Lines & Polygons](tutorial/geometries.md)

---

## Markers your way

Emoji, [Font Awesome](https://fontawesome.com/) icons, or fixed-size circle
markers — mix them freely, styled with CSS dicts.

```python exec="true" html="true" source="tabbed-right"
from shapely.geometry import Point
from mapyta import Map, CircleStyle, StrokeStyle, FillStyle

m = Map(title="Marker Styles")
m.add_point(Point(5.1213, 52.0908), marker="🏛️", tooltip="**Dom Tower** (emoji)")
m.add_point(
    point=Point(5.1178, 52.0865),
    marker="fa-house",
    tooltip="**Centraal Museum** (Font Awesome)",
    marker_style={"font-size": "24px", "color": "green"},
)
m.add_circle(
    point=Point(5.1378, 52.0871),
    tooltip="**Rietveld House** (circle)",
    style=CircleStyle(radius=12, stroke=StrokeStyle(color="#8e44ad", weight=2), fill=FillStyle(color="#8e44ad", opacity=0.5)),
)
m.set_bounds(padding=0.005)

print(m.to_html())  # markdown-exec: hide
```

[:octicons-arrow-right-24: Full tutorial: Markers](tutorial/markers.md)

---

## Markdown tooltips & popups

Tooltips and popups take **Markdown** — bold, italic, links, lists, and code —
so hover and click text stays readable without hand-written HTML.

```python exec="true" html="true" source="tabbed-right"
from shapely.geometry import Point
from mapyta import Map

m = Map(title="Rich Text")
m.add_point(
    point=Point(5.1213, 52.0908),
    marker="📖",
    tooltip="**Dom Tower**\n*tallest church tower in NL*",
    popup="### Dom Tower\n\n- Built: **1382**\n- Height: `112.5 m`\n- [Wikipedia](https://en.wikipedia.org/wiki/Dom_Tower,_Utrecht)",
    popup_style={"width": 280, "height": 150},
)

print(m.to_html())  # markdown-exec: hide
```

[:octicons-arrow-right-24: Full tutorial: Tooltips & Popups](tutorial/tooltips-popups.md)

---

## Choropleth

Shade regions by a numeric value and get a color legend automatically.

```python exec="true" html="true" source="tabbed-right"
from mapyta import Map

geojson = {
    "type": "FeatureCollection",
    "features": [
        {"type": "Feature", "properties": {"name": "Binnenstad", "score": 92},
         "geometry": {"type": "Polygon", "coordinates": [[[5.10, 52.08], [5.14, 52.08], [5.14, 52.10], [5.10, 52.10], [5.10, 52.08]]]}},
        {"type": "Feature", "properties": {"name": "West", "score": 74},
         "geometry": {"type": "Polygon", "coordinates": [[[5.06, 52.08], [5.10, 52.08], [5.10, 52.10], [5.06, 52.10], [5.06, 52.08]]]}},
        {"type": "Feature", "properties": {"name": "Oost", "score": 85},
         "geometry": {"type": "Polygon", "coordinates": [[[5.14, 52.08], [5.18, 52.08], [5.18, 52.10], [5.14, 52.10], [5.14, 52.08]]]}},
    ],
}

m = Map(title="Neighbourhood Scores")
m.add_choropleth(
    geojson_data=geojson,
    value_column="score",
    key_on="feature.properties.name",
    legend_name="Liveability Score",
    hover_fields=["name", "score"],
    fill_opacity=0.7,
)

print(m.to_html())  # markdown-exec: hide
```

[:octicons-arrow-right-24: Full tutorial: Choropleth Maps](tutorial/choropleth.md)

---

## Heatmap

For dense point data, a heatmap shows intensity patterns at a glance.

```python exec="true" html="true" source="tabbed-right"
import random
from shapely.geometry import Point
from mapyta import Map, HeatmapStyle

random.seed(42)
points = [Point(5.12 + random.gauss(0, 0.03), 52.09 + random.gauss(0, 0.015)) for _ in range(200)]

m = Map(title="Activity Heatmap")
m.add_heatmap(points=points, style=HeatmapStyle(radius=20, blur=15, min_opacity=0.4))

print(m.to_html())  # markdown-exec: hide
```

[:octicons-arrow-right-24: Full tutorial: Heatmaps](tutorial/heatmaps.md)

---

## Marker clusters

Hundreds of markers stay readable — nearby points group into numbered bubbles
that expand as you zoom in.

```python exec="true" html="true" source="tabbed-right"
import random
from shapely.geometry import Point
from mapyta import Map

random.seed(42)
cafes = [Point(5.12 + random.uniform(-0.02, 0.02), 52.09 + random.uniform(-0.01, 0.01)) for _ in range(50)]

m = Map(title="Utrecht Cafés")
m.add_marker_cluster(
    points=cafes,
    labels=["☕"] * 50,
    tooltips=[f"**Café #{i + 1}**" for i in range(50)],
    name="Cafés",
)

print(m.to_html())  # markdown-exec: hide
```

[:octicons-arrow-right-24: Full tutorial: Marker Clusters](tutorial/clusters.md)

---

## DataFrame in one line

Already have your data in Pandas or Polars? Point `add_dataframe()` at a WKT
geometry column and every other column becomes a hover field.

```python exec="true" html="true" source="tabbed-right"
import pandas as pd
from mapyta import Map

df = pd.DataFrame({
    "geometry": ["POINT (4.9041 52.3676)", "POINT (5.1214 52.0907)", "POINT (4.4777 51.9244)"],
    "city": ["Amsterdam", "Utrecht", "Rotterdam"],
    "population": [872_680, 361_924, 651_446],
})

m = Map(title="Dutch Cities")
m.add_dataframe(df, hover_fields=["city", "population"])

print(m.to_html())  # markdown-exec: hide
```

[:octicons-arrow-right-24: Full tutorial: DataFrames](tutorial/dataframe.md) ·
[GeoPandas](tutorial/geodataframe.md)

---

## Search box

`add_search_control()` drops in a search box that centers the map on the
matching feature — labels are inferred automatically.

```python exec="true" html="true" source="tabbed-right"
from shapely.geometry import Point
from mapyta import Map

m = Map(title="City Finder")
m.add_point(Point(4.9003, 52.3728), marker="🏙️", caption="Amsterdam")
m.add_point(Point(5.1214, 52.0907), marker="🏙️", caption="Utrecht")
m.add_point(Point(4.4777, 51.9244), marker="🏙️", caption="Rotterdam")
m.add_point(Point(4.3007, 52.0705), marker="🏙️", caption="Den Haag")
m.add_point(Point(5.4697, 51.4416), marker="🏙️", caption="Eindhoven")
m.add_search_control(placeholder="Find city...")

print(m.to_html())  # markdown-exec: hide
```

[:octicons-arrow-right-24: Full tutorial: Search Control](tutorial/search.md)

---

## Let users draw

Turn on drawing tools and let users sketch markers, lines, and polygons —
then capture what they drew.

```python exec="true" html="true" source="tabbed-right"
from mapyta import Map, MapConfig

m = Map(title="Drawing demo", center=(52.0907, 5.1214), config=MapConfig(zoom_start=13))
m.enable_draw()

print(m.to_html())  # markdown-exec: hide
```

Use the toolbar in the map's top-left corner to draw a shape.

[:octicons-arrow-right-24: Full tutorial: Drawing Tools](tutorial/drawing.md)

---

## Animation

Ant paths trace a route with marching-ants motion, making direction of travel
obvious at a glance.

```python exec="true" html="true" source="tabbed-right"
from shapely.geometry import LineString
from mapyta import Map

m = Map(title="Tram route 9 — Utrecht")
route = LineString([(5.1085, 52.0893), (5.1130, 52.0877), (5.1178, 52.0865), (5.1213, 52.0851), (5.1268, 52.0838)])
m.add_ant_path(route, tooltip="**Tram 9** — richting Maliebaan", color="#e74c3c", pulse_color="#ffffff", weight=5, delay=300)

print(m.to_html())  # markdown-exec: hide
```

[:octicons-arrow-right-24: Full tutorial: Animated Layers](tutorial/animated.md)

---

## Export anywhere

The same map exports to HTML, PNG (file, raw bytes, or an in-memory buffer),
and GeoJSON — sync or async.

```python
# HTML — always works, no extra dependencies
m.to_html("map.html")               # write a standalone file
html_string = m.to_html()           # or get it as a string

# PNG — needs mapyta[export] and a Chromium-based browser
m.to_image("map.png", scale=2.0)    # high-DPI file
png_bytes = m.to_image()            # raw PNG bytes in memory
buf = m.to_bytesio()                # io.BytesIO, for Flask/FastAPI/Django responses
png_bytes = await m.to_image_async()  # async variant

# GeoJSON — every feature you added, back out as a FeatureCollection
fc = m.to_geojson()                 # a dict
m.to_geojson("map.geojson")         # or a file
```

[:octicons-arrow-right-24: Full tutorial: Export](tutorial/export.md)

---

## Where to next

<div class="grid cards" markdown>

- :material-school: **[Tutorial](tutorial/index.md)** — learn mapyta from zero, one concept per page.
- :material-api: **[API reference](API%20reference/index.md)** — every class, method, and parameter.
- :material-github: **[GitHub](https://github.com/egarciamendez/mapyta)** — source, issues, and releases.

</div>
