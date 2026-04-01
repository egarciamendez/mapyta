# Export

## HTML (always works)

```python
# Write to file
m.to_html("map.html")

# Get HTML as a string
html_string = m.to_html()

# Write and open immediately in the browser
m.to_html("map.html", open_in_browser=True)
```

Writes a standalone HTML file. No server needed, just open in any browser. Useful for sharing with clients or embedding in reports.

## PNG image

!!! warning "Requires the `export` optional dependency"

    PNG and SVG export use Selenium with headless Chrome. Install the extra:

    ```bash
    pip install mapyta[export]
    # or
    uv add mapyta[export]
    ```

    Chrome or Chromium must also be installed. `chromedriver-autoinstaller` will attempt to install `chromedriver` automatically if it's not found on your PATH.

```python
# Save to file
m.to_image("map.png", width=1600, height=1000, delay=3.0)

# Get raw PNG bytes
png_bytes = m.to_image()

# Get a BytesIO buffer (useful for Django/Flask/FastAPI responses)
buf = m.to_bytesio(width=1200, height=800)
```

The `delay` parameter (seconds) controls how long Map waits for tiles to load before taking the screenshot. Increase it on slow connections.

## GeoJSON

Export all features added to the map as a GeoJSON `FeatureCollection`:

```python
# Return a dict
fc = m.to_geojson()

# Write to file
m.to_geojson("map.geojson")
```

Each feature in the collection carries the geometry (in WGS84) and the properties passed when it was added, tooltip text, popup text, marker name, style values, and so on:

```python exec="true" html="true" source="tabbed-right" result="ansi"
from shapely.geometry import Point, LineString
from mapyta import Map, StrokeStyle

m = (
    Map()
    .add_point(Point(5.121, 52.091), marker="📍", tooltip="Dom Tower")
    .add_linestring(
        LineString([(5.109, 52.089), (5.121, 52.091)]),
        tooltip="Route",
        stroke=StrokeStyle(color="#e74c3c", weight=3),
    )
)

fc = m.to_geojson()

print(fc)  # markdown-exec: hide

```

The output is standard [RFC 7946](https://datatracker.ietf.org/doc/html/rfc7946) GeoJSON, compatible with QGIS, ArcGIS, Mapbox, and any other GIS tool. GitHub and GitLab automatically render `.geojson` files as interactive maps.

## Download button

`add_export_button()` adds a button to the map UI that lets users download the current features as a GeoJSON file, no back-end required:

```python
m.add_export_button()
```

The button embeds the GeoJSON data directly in the HTML and triggers a browser download on click. The default label is `Download GeoJSON` and the file is saved as `export.geojson`.

Customise via keyword arguments:

```python
m.add_export_button(
    label="Download GeoJSON",
    filename="my_map.geojson",
    position="bottomleft",   # topleft | topright | bottomleft | bottomright
)
```

Like all `add_*` and configuration methods, `add_export_button()` is chainable:

```python
m = (
    Map()
    .add_point(Point(5.121, 52.091), marker="📍")
    .add_export_button()
)
```

!!! note "Snapshot at render time"

    The GeoJSON embedded in the button is captured when the map is first rendered (on the first call to `to_html()` or `open()`). Features added *after* rendering are not included. Call `to_geojson()` directly if you need the data on the Python side.

## Async variants

For web frameworks (FastAPI, Starlette, etc.) that run an async event loop:

```python
png_bytes = await m.to_image_async()
```

This runs the Selenium capture in a thread executor so it doesn't block the event loop.
