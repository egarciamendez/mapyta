# Drawing

Let users draw markers, lines, and polygons on the map and submit the results.

## Basic drawing

Enable the default drawing tools (polyline, polygon, marker) with a download-on-submit fallback:

```python exec="true" html="true" source="tabbed-right"
from mapyta import Map, MapConfig

m = Map(title="Drawing demo", center=(52.0907, 5.1214), config=MapConfig(zoom_start=13))
m.enable_draw()

m.to_html("custom.html")

print(m.to_html()) # markdown-exec: hide
```

Use the toolbar in the **top-left corner** of the map to draw:

- Click the **polyline**, **polygon**, or **marker** icon to start drawing
- Click on the map to add points; double-click to finish a shape
- Click **Submit** (bottom-right) to download a GeoJSON file with all drawn shapes

When editing is enabled (the default, `edit=True`), there is **no global edit/delete toolbar** — editing and deleting both happen per shape, in place:

- **Edit:** click any drawn shape to edit its vertices in place — drag the vertices to reshape it, drag a midpoint marker to add one. Click empty map space to stop editing.
- **Delete:** while a shape is being edited, a **trashbin icon** appears at its last point. Click it and confirm in the small in-map popup to delete that single shape. Or, as a shortcut, press the **Delete** key to remove the shape you're editing immediately (no confirmation).

Set `edit=False` to make drawn shapes inert (no in-place editing, no trashbin). The confirmation popup text is configurable via `delete_confirm_message`, `delete_confirm_yes`, and `delete_confirm_no` (English by default) — pass your own strings for other languages.

## Custom tools

Pick only the tools you need:

```python exec="true" html="true" source="tabbed-right"
from mapyta import Map, MapConfig

m = Map(title="Polygons only", center=(52.0907, 5.1214), config=MapConfig(zoom_start=13))
m.enable_draw(tools=["polygon", "rectangle"])

print(m.to_html()) # markdown-exec: hide
```

Valid tools: `"marker"`, `"polyline"`, `"polygon"`, `"rectangle"`, `"circle"`.

## Submit to a URL

Post drawn geometries to an API endpoint:

```python
m.enable_draw(on_submit="https://api.example.com/shapes")
```

This sends a `POST` request with the GeoJSON FeatureCollection as the body.

## Custom JavaScript callback

For full control, pass a `RawJS` function expression:

```python exec="true" html="true" source="tabbed-right"
from mapyta import Map, MapConfig, RawJS

m = Map(title="Custom callback, check console (F12)", center=(52.0907, 5.1214), config=MapConfig(zoom_start=13))
m.enable_draw(on_submit=RawJS("function(geojson) { console.log(geojson); }"))

print(m.to_html()) # markdown-exec: hide
```

Click **Submit** and check the browser console (F12) to see the GeoJSON output.

Or call a named function already on the page:

```python
m.enable_draw(on_submit="myGlobalHandler")
```

This generates `window["myGlobalHandler"](geojson)`.

## DrawConfig reference

| Field | Default | Description |
|-------|---------|-------------|
| `tools` | `["polyline", "polygon", "marker"]` | Active drawing tools |
| `on_submit` | `None` (download) | Callback: `None`, URL, function name, or `RawJS` |
| `position` | `"topleft"` | Toolbar position |
| `submit_label` | `"Submit"` | Submit button text |
| `draw_style` | `None` | `shapeOptions` override |
| `edit` | `True` | Per-shape in-place editing + trashbin delete (no global toolbar) |
| `delete_confirm_message` | `"Delete this shape?"` | Text in the delete confirmation popup |
| `delete_confirm_yes` | `"Delete"` | Confirm (delete) button label |
| `delete_confirm_no` | `"Cancel"` | Cancel button label |
