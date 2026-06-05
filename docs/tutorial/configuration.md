# Map Configuration

`MapConfig` controls the global look and feel: tile provider, zoom, dimensions, and optional plugins.

```python exec="true" html="true" source="tabbed-right"
from shapely.geometry import Point
from mapyta import Map, MapConfig

config = MapConfig(
    tile_layer="cartodb_dark",
    zoom_start=14,
    fullscreen=True,
    minimap=True,
    measure_control=True,
    mouse_position=True,
)

m = Map(title="Dark Mode", config=config)
m.add_point(Point(5.1213, 52.0908), marker="🌃", tooltip="**Night Utrecht**")

m.to_html("dark_mode.html")

print(m.to_html())  # markdown-exec: hide
```

## MapConfig fields

| Field             | Default              | Description                                                                                                                             |
|-------------------|----------------------|-----------------------------------------------------------------------------------------------------------------------------------------|
| `tile_layer`      | `"cartodb_positron"` | Tile provider key or list of keys                                                                                                       |
| `zoom_start`      | `12`                 | Initial zoom level                                                                                                                      |
| `min_zoom`        | `0`                  | Prevent zooming out beyond this level                                                                                                   |
| `max_zoom`        | `19`                 | Prevent zooming in beyond this level                                                                                                    |
| `max_native_zoom` | `None`               | Highest zoom level the tile provider actually serves. Set this below `max_zoom` to upscale tiles instead of showing blank placeholders. |
| `attribution`     | `None`               | Custom tile attribution                                                                                                                 |
| `width`           | `"100%"`             | Map width                                                                                                                               |
| `height`          | `"100%"`             | Map height                                                                                                                              |
| `control_scale`   | `True`               | Show scale bar                                                                                                                          |
| `fullscreen`      | `False`              | Add fullscreen button                                                                                                                   |
| `minimap`         | `False`              | Add inset minimap                                                                                                                       |
| `measure_control` | `False`              | Add distance/area measurement tool                                                                                                      |
| `mouse_position`  | `True`               | Show cursor coordinates                                                                                                                 |
| `mouse_position_crs` | `None`            | CRS for the cursor readout, e.g. `"EPSG:28992"` for RD New. `None` shows WGS84 lat/lon. Ignored when `mouse_position` is `False`.       |

## Available tile providers

| Key                  | Description                                 |
|----------------------|---------------------------------------------|
| `openstreetmap`      | Default OpenStreetMap                       |
| `cartodb_positron`   | Light, minimal CartoDB (default)            |
| `cartodb_dark`       | Dark CartoDB                                |
| `cartodb_voyager`    | CartoDB Voyager, colourful, detailed        |
| `esri_satellite`     | Esri satellite imagery                      |
| `esri_topo`          | Esri topographic                            |
| `esri_streets`       | Esri street map                             |
| `esri_gray`          | Esri light gray canvas                      |
| `esri_ocean`         | Esri ocean basemap                          |
| `opentopomap`        | OpenTopoMap, topographic with contour lines |
| `stamen_terrain`     | Stamen terrain with hillshading             |
| `stamen_toner`       | Stamen high-contrast B&W                    |
| `stamen_watercolor`  | Stamen watercolor, artistic style           |
| `stadia_alidade`     | Stadia Alidade Smooth, clean, light         |
| `stadia_dark`        | Stadia Alidade Dark, modern dark theme      |
| `kadaster_brt`       | Dutch Kadaster topographic                  |
| `kadaster_luchtfoto` | Dutch Kadaster aerial photos                |
| `kadaster_grijs`     | Dutch Kadaster greyscale                    |

## Zooming beyond native tile resolution

Every tile provider has a maximum zoom level at which it actually serves tiles. OpenStreetMap, for example, caps at zoom
19. If `max_zoom` is set higher than that, Leaflet requests tiles that don't exist and renders blank gray placeholders
instead.

Setting `max_native_zoom` tells Leaflet the highest zoom at which real tiles are available. When the user zooms past
that level, Leaflet upscales the last available tile rather than showing a blank:

```python exec="true" html="true" source="tabbed-right"
from shapely.geometry import Point
from mapyta import Map, MapConfig

m = Map(
    center=(52.090, 5.121),
    title="Zooming beyond native resolution",
    config=MapConfig(
        tile_layer="openstreetmap",
        zoom_start=18,
        max_zoom=21,
        max_native_zoom=19,
    ),
)
m.add_point(Point(5.1213, 52.0908), marker="📍", tooltip="**Dom Tower**")

m.to_html("max_native_zoom.html")
print(m.to_html())  # markdown-exec: hide
```

Zoom in past level 19, the tiles blur slightly rather than going blank. `max_native_zoom` is only needed when you raise
`max_zoom` above the provider's native cap. With the default `max_zoom=19`, OpenStreetMap's tiles cover the full range
and no blanks appear. When `max_native_zoom` is left as `None`, `_create_base_map` passes `max_zoom` directly as the
native zoom limit, so Leaflet does not upscale, which is fine as long as `max_zoom` stays within what the provider
serves.

## Multiple tile layers

Pass a list to `tile_layer` and add a layer control so users can switch between base maps:

```python exec="true" html="true" source="tabbed-right"
from shapely.geometry import Point
from mapyta import Map, MapConfig

m = Map(
    title="Multiple Tile Layers",
    config=MapConfig(
        tile_layer=["cartodb_positron", "cartodb_dark", "kadaster_brt"],
    ),
)
m.add_point(Point(5.1213, 52.0908), marker="📍", tooltip="**Utrecht**")
m.add_layer_control(collapsed=False)

print(m.to_html())  # markdown-exec: hide
```

The first layer in the list is shown by default. You can also add layers after construction with `add_tile_layer()`:

```python
m = Map(title="Multiple Tile Layers")
m.add_tile_layer(name="esri_satellite")
m.add_tile_layer(name="cartodb_dark")
m.add_layer_control(collapsed=False)
```

## Reset-view button

A map opens at a fixed view: either the `center` and `zoom_start` you pass, or the bounds Mapyta auto-fits to your
data. Once the user pans and zooms away, `add_home_button()` gives them a one-click way back to that opening view.

```python exec="true" html="true" source="tabbed-right"
from shapely.geometry import Point
from mapyta import Map, MapConfig

m = Map(
    center=(52.090, 5.121),
    title="Reset view",
    config=MapConfig(zoom_start=14),
)
m.add_point(Point(5.1213, 52.0908), marker="📍", tooltip="**Dom Tower**")
m.add_home_button(position="topleft")

m.to_html("home_button.html")
print(m.to_html())  # markdown-exec: hide
```

The ⌂ button captures the opening view in the browser after the map loads, so a single button works whether the view
came from an explicit `center` or from auto-fitted data bounds. Clicking it restores that center and zoom. Place it with
`position` (`"topleft"`, `"topright"`, `"bottomleft"`, `"bottomright"`) and set the hover tooltip with `title`.

## Cursor coordinates in a projected CRS

By default the bottom-left readout shows the cursor position as WGS84 latitude/longitude. Set `mouse_position_crs` to
display the coordinates in a projected CRS instead, such as Dutch RD New (EPSG:28992):

```python exec="true" html="true" source="tabbed-right"
from shapely.geometry import Point
from mapyta import Map, MapConfig

m = Map(
    center=(52.090, 5.121),
    title="RD New cursor readout",
    config=MapConfig(mouse_position_crs="EPSG:28992"),
)
m.add_point(Point(5.1213, 52.0908), marker="📍", tooltip="**Dom Tower**")

print(m.to_html())  # markdown-exec: hide
```

Hover over the map: the readout now shows RD New `X | Y` in metres (near the Dom tower, roughly `136150 | 455900`)
instead of lat/lon. Any CRS that `pyproj` recognises is accepted. The number of decimals is picked automatically — `0`
for projected CRSs (metres), `6` for geographic ones.

!!! note "Accuracy"
    The transform runs client-side with [proj4js](http://proj4js.org/), which only supports the 7-parameter Helmert
    datum shift rather than the official RDNAPTRANS™ correction grid used by [rdinfo.nl](https://www.rdinfo.nl/). For
    RD New this means the readout can differ from the authoritative value by up to ~25 cm across the Netherlands —
    negligible for a hover readout, but don't use it as a source of survey-grade coordinates.
