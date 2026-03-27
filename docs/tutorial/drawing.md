# Drawing

Let users draw markers, lines, and polygons on the map and submit the results.

## Basic drawing

Enable the default drawing tools (polyline, polygon, marker) with a download-on-submit fallback:

```python exec="true" html="true" source="tabbed-right"
from mapyta import Map

m = Map(title="Drawing demo")
m.enable_draw()

m.to_html("custom.html")

print(m.to_html()) # markdown-exec: hide
```

Use the toolbar in the **top-left corner** of the map to draw:

- Click the **polyline**, **polygon**, or **marker** icon to start drawing
- Click on the map to add points; double-click to finish a shape
- Click **Submit** (bottom-right) to download a GeoJSON file with all drawn shapes

## Custom tools

Pick only the tools you need:

```python exec="true" html="true" source="tabbed-right"
from mapyta import Map

m = Map(title="Polygons only")
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
from mapyta import Map
from mapyta import RawJS

m = Map(title="Custom callback, check console (F12)")
m.enable_draw(on_submit=RawJS("function(geojson) { console.log(geojson); }"))

print(m.to_html()) # markdown-exec: hide
```

Click **Submit** and check the browser console (F12) to see the GeoJSON output.

Or call a named function already on the page:

```python
m.enable_draw(on_submit="myGlobalHandler")
```

This generates `window["myGlobalHandler"](geojson)`.

## VIKTOR integration (BETA)

When building apps on [VIKTOR](https://viktor.ai), use `viktor_params` to send drawn geometries back to the Python controller via `viktorSdk.sendParams()`:

```python exec="true" html="true" source="tabbed-right"
from mapyta import Map

m = Map(title="Draw a route")
m.enable_draw(
    tools=["marker", "polyline", "polygon"],
    viktor_params={
        "marker": "geopoint",
        "polyline": "geopolyline",
        "polygon": "geopolygon",
    },
    submit_label="Verzenden",
)

print(m.to_html()) # markdown-exec: hide

```

Each key in `viktor_params` must match a tool in `tools`. The values are the VIKTOR parameter field names. Coordinates are automatically converted from GeoJSON `[lon, lat]` to VIKTOR's `{lat, lon}` format.

!!! note
    The `"circle"` tool is not supported with `viktor_params` because VIKTOR has no matching geometry type.

## DrawConfig reference

| Field | Default | Description |
|-------|---------|-------------|
| `tools` | `["polyline", "polygon", "marker"]` | Active drawing tools |
| `on_submit` | `None` (download) | Callback: `None`, URL, function name, or `RawJS` |
| `viktor_params` | `None` | VIKTOR field mapping (overrides `on_submit`) |
| `position` | `"topleft"` | Toolbar position |
| `submit_label` | `"Submit"` | Submit button text |
| `draw_style` | `None` | `shapeOptions` override |
| `edit` | `True` | Enable edit/delete controls |
