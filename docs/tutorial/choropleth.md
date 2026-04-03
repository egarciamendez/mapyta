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

If your values are string categories (land use type, municipality class, etc.), set `categorical=True` or pass string values and mapyta auto-detects them. Each unique category gets a distinct color from the palette:

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
