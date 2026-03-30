# Export

## Open in browser (live reload)

```python
m.open()
```

Starts a local HTTP server in the background and opens the map in your default browser. Every subsequent call to `open()` updates the map in place, the browser reloads automatically within one second, without a manual refresh.

```python
m = Map(title="Utrecht")
m.add_point(Point(5.121, 52.091), marker="📍")
m.open()                           # browser opens

m.add_polygon(my_polygon)
m.open()                           # browser reloads with the new polygon
```

!!! tip "Running from a script?"

    The server thread is a daemon: it lives only as long as the Python process does. When running a `.py` file (as opposed to a REPL or notebook), pass `block=True` to keep the process alive until `Ctrl+C`:

    ```python
    m.open(block=True)
    ```

By default the OS picks a free port. Pass `port=8080` to pin it:

```python
m.open(port=8080)
```

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

!!! note "Raster, not vector"

    `to_svg()` captures a PNG screenshot and wraps it in an SVG container. Text and shapes are **rasterized** — the output does not contain editable vector paths. This is a Leaflet limitation: it renders to an HTML canvas that cannot be serialized to vector geometry.

    For high-resolution output, increase `width` and `height`. For a true vector workflow, export to HTML and use a dedicated conversion tool.

## Async variants

For web frameworks (FastAPI, Starlette, etc.) that run an async event loop:

```python
png_bytes = await m.to_image_async()
svg_string = await m.to_svg_async()
```

These run the Selenium capture in a thread executor so they don't block the event loop.
