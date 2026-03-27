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

Writes a standalone HTML file. No server needed — just open in any browser. Useful for sharing with clients or embedding in reports.

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

## SVG

```python
# Raster-wrapped SVG (PNG embedded in SVG container)
m.to_svg("map.svg")

# Get the SVG string
svg_string = m.to_svg()
```

!!! note

    Leaflet's SVG export is a raster capture embedded in an SVG wrapper, not a true vector graphic. It won't scale infinitely, but it's useful for some workflows.

## Async variants

For web frameworks (FastAPI, Starlette, etc.) that run an async event loop:

```python
png_bytes = await m.to_image_async()
svg_string = await m.to_svg_async()
```

These run the Selenium capture in a thread executor so they don't block the event loop.

**Next:** [Advanced](advanced.md) — merge maps, add raw GeoJSON layers, and access the underlying Folium object.
