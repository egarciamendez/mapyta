# Choropleth Maps

A "choropleth" is a map where areas are shaded by a numeric value, think population density, liveability scores, or soil classifications. Map builds one from a GeoJSON FeatureCollection and a value column.

```python exec="true" html="true" source="tabbed-right"
from mapyta import Map

geojson = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"name": "Binnenstad", "score": 92},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[5.10, 52.08], [5.14, 52.08], [5.14, 52.10], [5.10, 52.10], [5.10, 52.08]]],
            },
        },
        {
            "type": "Feature",
            "properties": {"name": "West", "score": 74},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[5.06, 52.08], [5.10, 52.08], [5.10, 52.10], [5.06, 52.10], [5.06, 52.08]]],
            },
        },
        {
            "type": "Feature",
            "properties": {"name": "Oost", "score": 85},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[5.14, 52.08], [5.18, 52.08], [5.18, 52.10], [5.14, 52.10], [5.14, 52.08]]],
            },
        },
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

m.to_html("choropleth.html")

print(m.to_html()) # markdown-exec: hide
```

## How it works

**`value_column`** tells Map which GeoJSON property holds the numeric value.

**`key_on`** is the dot-path to the join key inside each feature (Folium convention). For properties it's always `"feature.properties.<key>"`.

If you don't pass `values` explicitly, Map reads them straight from the GeoJSON properties, which is usually what you want.

**`hover_fields`** turns property keys into a tooltip table on mouse-over.

!!! tip "Multiple ways to pass GeoJSON"

    `geojson_data` accepts a dict, a JSON string, or a `Path` to a `.geojson` file, Map handles all three.

## Custom color palettes

By default choropleths use a yellow-to-red gradient (`"ylrd"`). Pass a named palette or a list of hex colors to the `colors` parameter:

```python exec="true" html="true" source="tabbed-right"
from mapyta import Map

geojson = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"name": "Binnenstad", "score": 92},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[5.10, 52.08], [5.14, 52.08], [5.14, 52.10], [5.10, 52.10], [5.10, 52.08]]],
            },
        },
        {
            "type": "Feature",
            "properties": {"name": "West", "score": 74},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[5.06, 52.08], [5.10, 52.08], [5.10, 52.10], [5.06, 52.10], [5.06, 52.08]]],
            },
        },
        {
            "type": "Feature",
            "properties": {"name": "Oost", "score": 85},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[5.14, 52.08], [5.18, 52.08], [5.18, 52.10], [5.14, 52.10], [5.14, 52.08]]],
            },
        },
    ],
}

m = Map(title="Neighbourhood Scores — Blues palette")
m.add_choropleth(
    geojson_data=geojson,
    value_column="score",
    key_on="feature.properties.name",
    legend_name="Liveability Score",
    hover_fields=["name", "score"],
    fill_opacity=0.7,
    colors="blues",
)

print(m.to_html())  # markdown-exec: hide
```

You can also pass a custom list of hex colors (ordered from low to high values):

```python exec="true" html="true" source="tabbed-right"
from mapyta import Map

geojson = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"name": "Binnenstad", "score": 92},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[5.10, 52.08], [5.14, 52.08], [5.14, 52.10], [5.10, 52.10], [5.10, 52.08]]],
            },
        },
        {
            "type": "Feature",
            "properties": {"name": "West", "score": 74},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[5.06, 52.08], [5.10, 52.08], [5.10, 52.10], [5.06, 52.10], [5.06, 52.08]]],
            },
        },
        {
            "type": "Feature",
            "properties": {"name": "Oost", "score": 85},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[5.14, 52.08], [5.18, 52.08], [5.18, 52.10], [5.14, 52.10], [5.14, 52.08]]],
            },
        },
    ],
}

m = Map(title="Neighbourhood Scores — Custom colors")
m.add_choropleth(
    geojson_data=geojson,
    value_column="score",
    key_on="feature.properties.name",
    legend_name="Liveability Score",
    hover_fields=["name", "score"],
    fill_opacity=0.7,
    colors=["#f7fbff", "#6baed6", "#084594"],
)

print(m.to_html())  # markdown-exec: hide
```

All available palette names are exposed in `mapyta.PALETTES`:

```python exec="true" result="ansi" source="tabbed-right"
from mapyta import PALETTES

print(list(PALETTES.keys()))
```

The same `colors` parameter works on `Map.from_geodataframe()` when using `color_column`.

## Categorical data

If your values are string categories (land use type, municipality class, etc.), set `categorical=True` or pass string values and mapyta auto-detects them. Each unique category gets a distinct color from the palette, and the legend is a [swatch per category](#categorical-legend) rather than a colorbar, so it names the categories instead of numbering them:

```python exec="true" html="true" source="tabbed-right"
from mapyta import Map

geojson = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"name": "Binnenstad", "type": "urban"},
            "geometry": {"type": "Polygon", "coordinates": [[[5.10, 52.08], [5.14, 52.08], [5.14, 52.10], [5.10, 52.10], [5.10, 52.08]]]},
        },
        {
            "type": "Feature",
            "properties": {"name": "West", "type": "suburban"},
            "geometry": {"type": "Polygon", "coordinates": [[[5.06, 52.08], [5.10, 52.08], [5.10, 52.10], [5.06, 52.10], [5.06, 52.08]]]},
        },
        {
            "type": "Feature",
            "properties": {"name": "Oost", "type": "urban"},
            "geometry": {"type": "Polygon", "coordinates": [[[5.14, 52.08], [5.18, 52.08], [5.18, 52.10], [5.14, 52.10], [5.14, 52.08]]]},
        },
    ],
}

m = Map(title="Area Types")
m.add_choropleth(
    geojson_data=geojson,
    value_column="type",
    key_on="feature.properties.name",
    legend_name="Area type",
    colors="spectral",
    hover_fields=["name", "type"],
)

print(m.to_html())  # markdown-exec: hide
```

## Standalone colorbar legend

`add_choropleth` draws its own legend, but sometimes you colour features by hand, for example `add_circle` or `add_point` markers whose fill comes from a per-feature value, and still want a shared color scale. `add_colorbar()` adds that legend on its own.

Unlike the other `add_*` methods, it returns the **colormap** rather than the map. The colormap is callable: `colormap(value)` gives back the hex color for that value, so your markers stay consistent with the legend without you rebuilding the scale.

```python exec="true" html="true" source="tabbed-right"
from shapely.geometry import Point
from mapyta import Map, CircleStyle, StrokeStyle, FillStyle

# Air-quality sensors, each placed by hand and coloured from a shared 0–100 scale.
readings = [
    (5.10, 52.090, 12),
    (5.12, 52.100, 45),
    (5.14, 52.085, 78),
    (5.16, 52.105, 95),
]

m = Map(title="Air quality sensors")

# Returns the colormap (not the map). Call it to colour each marker.
colormap = m.add_colorbar(colors="blues", vmin=0, vmax=100, legend_name="PM2.5 (µg/m³)")

for lon, lat, value in readings:
    m.add_circle(
        point=Point(lon, lat),
        tooltip=f"{value} µg/m³",
        style=CircleStyle(
            radius=12,
            stroke=StrokeStyle(color="#333", weight=1),
            fill=FillStyle(color=colormap(value), opacity=0.9),
        ),
    )

m.to_html("colorbar.html")

print(m.to_html())  # markdown-exec: hide
```

### How it works

**`colors`**, **`vmin`**, **`vmax`** define the scale exactly like `add_choropleth`: a [palette name](#custom-color-palettes), a list of hex colors (low → high), or `None` for the default `"ylrd"` ramp, mapped across the `vmin`–`vmax` range.

**`legend_name`** is the caption above the bar. Plain strings are HTML-escaped and shown literally; wrap the text in `RawHTML` to render inline markup such as `<sub>` or `<sup>`:

```python
from mapyta import RawHTML

m.add_colorbar(colors="viridis", vmin=0, vmax=50, legend_name=RawHTML("R<sub>c;cal</sub>"))
```

The legend is a vertical gradient bar pinned to the right edge of the map, with five evenly spaced ticks running high → low. Ticks show a plain integer when whole, otherwise two decimals. `add_choropleth` and `from_geodataframe` draw the same bar for their continuous scales, so every legend on a map matches — and because it is plain HTML rather than a Leaflet control, it survives `to_image()`, which hides the map controls by default.

!!! tip "Reuse the same scale everywhere"

    Because `colormap` is just a callable, you can pass `colormap(value)` to any styled feature, circles, polygons (`add_polygon`), or DataFrame rows, so every layer on the map reads against one legend.

## Categorical legend

`add_colorbar()` explains a continuous scale. When features fall into named classes instead, a status, a material, an owner, `add_legend()` draws one colour swatch per class. A [categorical choropleth](#categorical-data) draws this legend for you; call `add_legend()` yourself when you coloured the features by hand:

```python exec="true" html="true" source="tabbed-right"
from shapely.geometry import Point
from mapyta import Map, CircleStyle, StrokeStyle, FillStyle

STATUSES = [
    ("#1a9850", "Geclassificeerd"),
    ("#fee08b", "Deels geclassificeerd"),
    ("#d73027", "Niet geclassificeerd"),
    ("#999999", "Onbekend"),
]

# Each site carries the index of its status.
sites = [(5.10, 52.090, 0), (5.12, 52.100, 1), (5.14, 52.085, 2), (5.16, 52.105, 3), (5.11, 52.078, 0)]

m = Map(title="Classification status")

for lon, lat, status in sites:
    color, label = STATUSES[status]
    m.add_circle(
        point=Point(lon, lat),
        tooltip=label,
        style=CircleStyle(
            radius=10,
            stroke=StrokeStyle(color="#333", weight=1),
            fill=FillStyle(color=color, opacity=1.0),
        ),
    )

m.add_legend(entries=STATUSES, title="Status")

print(m.to_html())  # markdown-exec: hide
```

### How it works

**`entries`** is a list of `(color, label)` pairs, drawn top to bottom in the order you give them. Nothing links them to the features on the map, so pass the same colors you used to style those features. Plain-string labels are HTML-escaped and shown literally; wrap one in `RawHTML` to render inline markup such as `<sub>`.

**`title`** is the heading above the swatches, escaped the same way. Leave it out for an unlabelled legend.

**`position`** pins the card to `"topleft"`, `"topright"`, `"bottomleft"` or `"bottomright"`. The default `"bottomright"` stays clear of the map title, the top-right controls and the bottom-left coordinate readout. The legend never intercepts mouse events, so panning and zooming still work over it.

!!! tip "Filtering as well as explaining"

    A legend explains the colors but cannot switch classes off. Put each class in its own [feature group](layers.md) and add `add_layer_control()` alongside the legend: readers then get both the color key and a "show only unclassified" filter.
