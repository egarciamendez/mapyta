# Choropleth Maps

A "choropleth" is a map where areas are shaded by a numeric value, think population density, liveability scores, or soil classifications. Map builds one from a GeoJSON FeatureCollection and a value column.

```python exec="true" html="true" source="tabbed-right"
from mapyta import Map

geojson = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"name": "Centrum", "score": 92},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[4.88, 52.36], [4.92, 52.36], [4.92, 52.38], [4.88, 52.38], [4.88, 52.36]]],
            },
        },
        {
            "type": "Feature",
            "properties": {"name": "West", "score": 74},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[4.84, 52.36], [4.88, 52.36], [4.88, 52.38], [4.84, 52.38], [4.84, 52.36]]],
            },
        },
        {
            "type": "Feature",
            "properties": {"name": "Oost", "score": 85},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[4.92, 52.36], [4.96, 52.36], [4.96, 52.38], [4.92, 52.38], [4.92, 52.36]]],
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
