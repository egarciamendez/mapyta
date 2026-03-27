# Advanced

## Merge maps

Combine two `Map` instances with `+`. The left map's title and config are preserved; the right map's geometries and layers are added on top.

```python exec="true" html="true" source="tabbed-right"
from shapely.geometry import Point, Polygon
from mapyta import Map

museums = Map(title="Combined")
museums.add_point(point=Point(4.8795, 52.3600), marker="🖼️", tooltip="**Rijksmuseum**")

parks = Map()
parks.add_polygon(
    polygon=Polygon([(4.8580, 52.3530), (4.8830, 52.3530), (4.8830, 52.3620), (4.8580, 52.3620)]),
    tooltip="**Vondelpark**",
)

combined = museums + parks
combined.to_html("merged.html")

print(combined.to_html())
```

You can chain as many maps together as you like — `a + b + c` — and all geometries and layers combine.

## GeoJSON layers

Add raw GeoJSON as a styled layer with hover tooltips, useful when you already have `.geojson` files and don't need choropleth coloring.

```python exec="true" html="true" source="tabbed-right"
from mapyta import Map

geojson = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"name": "Zone A", "type": "residential"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[4.88, 52.36], [4.90, 52.36], [4.90, 52.37], [4.88, 52.37], [4.88, 52.36]]],
            },
        },
    ],
}

m = Map(title="GeoJSON Layer")
m.add_geojson(
    geojson,
    hover_fields=["name", "type"],
    style={"color": "#e74c3c", "weight": 2, "fillOpacity": 0.1},
    highlight={"weight": 5, "fillOpacity": 0.3},
)

m.to_html("geojson_layer.html")

print(m.to_html())
```

**`hover_fields`** picks properties to show on mouse-over. **`highlight`** defines the style change on hover. `data` can be a dict, a JSON string, or a file `Path`.

## Escape hatch

Need something mapyta doesn't wrap? The underlying Folium `Map` object is always accessible via the `folium_map` property.

```python exec="true" html="true" source="tabbed-right"
import folium
from mapyta import Map

m = Map(title="Custom Folium")
folium_map = m.folium_map

# Add anything Folium supports directly
folium.CircleMarker([52.37, 4.90], radius=50, color="red").add_to(folium_map)

m.to_html("custom.html")

print(m.to_html())
```

This gives you full access to Folium's API for plugins, custom JavaScript, or anything else not yet exposed by mapyta.
