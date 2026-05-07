# FAQ

Common questions and answers for mapyta.

---

## Map creation

**How do I set the initial center and zoom level?**

```python
from mapyta import Map, MapConfig

m = Map(
    center=(52.37, 4.9),
    config=MapConfig(zoom_start=14),
)
```

If you omit `center`, mapyta auto-fits the view to all your geometries after the first render.

---

**How do I change the tile provider (background map)?**

Pass a provider key to `MapConfig`:

```python
from mapyta import Map, MapConfig

m = Map(config=MapConfig(tile_layer="esri_satellite"))
```

Built-in keys: `openstreetmap`, `cartodb_positron`, `cartodb_dark`, `esri_satellite`, `esri_topo`, `stamen_terrain`, `stamen_toner`, `kadaster_brt`, `kadaster_luchtfoto`, `kadaster_grijs`, `cartodb_voyager`, `esri_streets`, `esri_gray`, `esri_ocean`, `opentopomap`, `stamen_watercolor`, `stadia_alidade`, `stadia_dark`.

Pass a raw XYZ URL for a provider not in the list:

```python
m = Map(config=MapConfig(tile_layer="https://my-tiles.example.com/{z}/{x}/{y}.png"))
```

---

**How do I show multiple base layers with a toggle?**

```python
from mapyta import Map, MapConfig

m = Map(config=MapConfig(tile_layer=["cartodb_positron", "esri_satellite"]))
m.add_layer_control()
```

---

## Geometries

**What geometry types are supported?**

All standard Shapely types: `Point`, `LineString`, `Polygon`, `MultiPoint`, `MultiLineString`, `MultiPolygon`. Pass any of these to the corresponding `add_*` method, or use `add_geometry()` to dispatch automatically.

---

**How do I hide a layer until the user zooms in?**

Use the `min_zoom` parameter. It works on points, circles, lines, polygons, clusters, and text annotations:

```python
from shapely.geometry import Point, LineString, Polygon
from mapyta import Map

m = Map()
m.add_point(Point(4.9, 52.37), marker="📍", min_zoom=13)
m.add_linestring(LineString([(4.9, 52.37), (4.91, 52.38)]), min_zoom=13)
m.add_polygon(Polygon([(4.9, 52.3), (5.0, 52.3), (5.0, 52.4), (4.9, 52.4)]), min_zoom=11)
```

The layer is hidden at zoom levels below `min_zoom` and shown at `min_zoom` and above.

---

**My coordinates are in Dutch RD New (EPSG:28992). Do I need to convert them first?**

No. Mapyta auto-detects RD New coordinates and reprojects them to WGS84:

```python
from shapely.geometry import Point
from mapyta import Map

m = Map()
m.add_point(Point(121_000, 487_000))  # RD New — converted automatically
```

To force a specific CRS, pass `source_crs`:

```python
m = Map(source_crs="EPSG:28992")
```

---

## Styling

**How do I style a line or polygon?**

Use `StrokeStyle` for borders and lines, `FillStyle` for polygon fills:

```python
from shapely.geometry import Polygon
from mapyta import Map, StrokeStyle, FillStyle

m = Map()
m.add_polygon(
    Polygon([(4.9, 52.3), (5.0, 52.3), (5.0, 52.4), (4.9, 52.4)]),
    stroke=StrokeStyle(color="#e74c3c", weight=2),
    fill=FillStyle(color="#e74c3c", opacity=0.15),
)
```

You can also pass plain dicts as a shorthand:

```python
m.add_polygon(poly, stroke={"color": "#e74c3c", "weight": 2})
```

---

**How do I change the marker icon?**

Pass an emoji or a [Font Awesome 6](https://fontawesome.com/icons) icon name to `marker`:

```python
m.add_point(Point(4.9, 52.37), marker="📍")         # emoji
m.add_point(Point(4.9, 52.37), marker="location-dot")  # Font Awesome
```

---

## Tooltips & popups

**How do I add a tooltip with formatted text?**

Pass a Markdown string to `tooltip`:

```python
m.add_point(Point(4.9, 52.37), tooltip="**Amsterdam** — population 872 680")
```

For full HTML control, wrap the string in `RawHTML`:

```python
from mapyta import RawHTML

m.add_point(Point(4.9, 52.37), tooltip=RawHTML("<b>Amsterdam</b><br>Pop: 872 680"))
```

---

## Layers

**How do I create toggleable layers?**

```python
from shapely.geometry import Point, Polygon
from mapyta import Map

m = Map()

m.create_feature_group("Museums")
m.add_point(Point(4.9, 52.37), marker="🏛️", tooltip="Rijksmuseum")

m.create_feature_group("Parks")
m.add_polygon(Polygon([(4.88, 52.35), (4.92, 52.35), (4.92, 52.38), (4.88, 52.38)]))

m.reset_target()
m.add_layer_control()
```

---

## Choropleth & colors

**How do I customise the colors of a choropleth?**

Pass a palette name or a list of hex colors to the `colors` parameter:

```python
# Named palette (see mapyta.PALETTES for all options)
m.add_choropleth(geojson, value_column="score", key_on="feature.properties.id", colors="blues")

# Custom colors (low → high)
m.add_choropleth(geojson, value_column="score", key_on="feature.properties.id", colors=["#eef", "#44f", "#004"])
```

The same `colors` parameter works on `Map.from_geodataframe(color_column=...)`.

---

**How do I create a choropleth with categorical (non-numeric) data?**

Just use string values. Mapyta auto-detects them and assigns a distinct color per category:

```python
# String values → auto-detected as categorical
m.add_choropleth(geojson, value_column="land_use", key_on="feature.properties.id")

# Force categorical mode explicitly
m.add_choropleth(geojson, value_column="score", key_on="feature.properties.id", categorical=True)
```

---

## Search

**How do I add a search box to the map?**

Call `add_search_control()` with no arguments — it searches all features on the map automatically, inferring the label from `caption`, `name`, `naam`, or the first string property it finds:

```python
from shapely.geometry import Point
from mapyta import Map

m = Map()
m.add_point(Point(4.9, 52.37), caption="Amsterdam")
m.add_point(Point(5.12, 52.09), caption="Utrecht")

m.add_search_control()  # searches captions automatically
```

For a choropleth or GeoJSON layer in a named feature group, pass `layer_name` and `property_name` to target that layer explicitly:

```python
m.create_feature_group("Places")
m.add_choropleth(geojson, value_column="score", key_on="feature.properties.name")
m.reset_target()

m.add_search_control(layer_name="Places", property_name="name", zoom=14)
```

---

## Export

**How do I save the map to an HTML file?**

```python
m.to_html("map.html")
```

Pass `open_in_browser=True` to open it immediately:

```python
m.to_html("map.html", open_in_browser=True)
```

---

**How do I export to PNG?**

Install the optional export dependency first:

```bash
pip install mapyta[export]
```

Then:

```python
m.to_image("map.png", width=1600, height=900)
```

Chrome or Chromium must be installed.

---

**How do I export a higher-resolution PNG for print or presentations?**

Use the `scale` parameter:

```python
# 2× resolution (2400 × 1600 px from a 1200 × 800 layout)
m.to_image("map_print.png", width=1200, height=800, scale=2.0)
```

`scale=2.0` doubles the pixel dimensions without changing the map layout.

---

**How do I export the map features as GeoJSON?**

```python
# Return a dict
fc = m.to_geojson()

# Write to file
m.to_geojson("features.geojson")
```

---

**How do I use mapyta in FastAPI or another async web framework?**

Use the async variants so Selenium doesn't block the event loop:

```python
png_bytes = await m.to_image_async()
```

For HTML or GeoJSON (which don't use Selenium), call the synchronous methods directly — they are non-blocking.

---

## GeoPandas

**How do I build a map directly from a GeoDataFrame?**

```python
import geopandas as gpd
from mapyta import Map

gdf = gpd.read_file("municipalities.geojson")
m = Map.from_geodataframe(gdf, hover_columns=["name"])
```

---

**I get a warning about missing columns. What does it mean?**

If a column name passed to `hover_columns`, `popup_columns`, `label_column`, or `color_column` does not exist in the GeoDataFrame, mapyta emits a `UserWarning`:

```
UserWarning: from_geodataframe(): hover_columns contains column(s) not found
in the GeoDataFrame: ['nonexistent']. Available columns: ['name', 'geometry']
```

Check the column names with `gdf.columns` and correct the argument.

---

## Drawing tools

**How do I let users draw shapes on the map?**

```python
m.enable_draw(tools=["polygon", "marker"])
```

Valid tools: `"marker"`, `"polyline"`, `"polygon"`, `"rectangle"`, `"circle"`.

When the user clicks Submit, the drawn shapes are downloaded as a GeoJSON file by default. Pass `on_submit` to send the data to a URL or call a JavaScript function instead.

---

## Escape hatch

**How do I access the underlying Folium map object?**

```python
import folium
m = Map()
# ... add geometries ...
folium_map = m.folium_map  # the underlying folium.Map instance
```

This gives you access to every Folium and Leaflet feature not exposed by mapyta.
