# Feature Groups

When your map has multiple categories of data, you want users to toggle them on and off. That's what "feature groups" are for, think of them as named folders. Everything you add while a group is active goes into that folder.

```python exec="true" html="true" source="tabbed-right"
from shapely.geometry import Point
from mapyta import Map

m = Map(title="Utrecht POI")

# Group 1: Museums
m.create_feature_group("🏛️ Museums")
m.add_point(point=Point(5.1178, 52.0865), marker="🖼️", tooltip="**Centraal Museum**")
m.add_point(point=Point(5.1197, 52.0820), marker="🚂", tooltip="**Spoorwegmuseum**")

# Group 2: Parks
m.create_feature_group("🌳 Parks")
m.add_point(point=Point(5.1248, 52.0855), marker="🌳", tooltip="**Wilhelminapark**")
m.add_point(point=Point(5.1367, 52.0945), marker="🌿", tooltip="**Griftpark**")

m.add_layer_control(collapsed=False)

m.to_html("poi_layers.html")

print(m.to_html()) # markdown-exec: hide
```

## How it works

**`create_feature_group("name")`** creates a new group and immediately activates it. All subsequent `add_*` calls go into this group until you:

- Call `create_feature_group()` again to create and switch to a new group
- Call `set_feature_group("name")` to switch to an existing group
- Call `reset_target()` to go back to the base map

**`add_layer_control()`** adds the toggle widget in the corner. Set `collapsed=False` to show it expanded by default.

!!! tip "Hiding groups by default"

    Pass `show=False` to `create_feature_group()` to have a layer hidden when the map loads:

    ```python
    m.create_feature_group("🔵 Boreholes", show=False)
    ```

## Search control

`add_search_control()` adds a search box that lets users find a feature in a feature group by one of its properties:

```python exec="true" html="true" source="tabbed-right"
from mapyta import Map

geojson = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"name": "Binnenstad", "score": 92},
            "geometry": {"type": "Polygon", "coordinates": [[[5.10, 52.08], [5.14, 52.08], [5.14, 52.10], [5.10, 52.10], [5.10, 52.08]]]},
        },
        {
            "type": "Feature",
            "properties": {"name": "West", "score": 74},
            "geometry": {"type": "Polygon", "coordinates": [[[5.06, 52.08], [5.10, 52.08], [5.10, 52.10], [5.06, 52.10], [5.06, 52.08]]]},
        },
        {
            "type": "Feature",
            "properties": {"name": "Oost", "score": 85},
            "geometry": {"type": "Polygon", "coordinates": [[[5.14, 52.08], [5.18, 52.08], [5.18, 52.10], [5.14, 52.10], [5.14, 52.08]]]},
        },
    ],
}

m = Map(title="Neighbourhood Finder")

# Add the choropleth to a named feature group so it can be searched
m.create_feature_group("Neighbourhoods")
m.add_choropleth(
    geojson_data=geojson,
    value_column="score",
    key_on="feature.properties.name",
    legend_name="Liveability Score",
    hover_fields=["name", "score"],
)
m.reset_target()

m.add_search_control(
    layer_name="Neighbourhoods",
    property_name="name",          # GeoJSON property to match against
    placeholder="Find neighbourhood...",
    zoom=14,                       # zoom level when a result is selected
    geom_type="Polygon",           # use "Polygon" for area features
)

print(m.to_html())  # markdown-exec: hide
```

**`layer_name`** must match the name used in `create_feature_group()`. **`property_name`** is the GeoJSON property to search on — it must exist on your features. Use `geom_type="Polygon"` when searching polygon or choropleth layers. The control uses `folium.plugins.Search` internally.

!!! note

    `add_search_control()` searches the GeoJSON properties of features in the given feature group. The feature group must contain a GeoJSON layer (e.g. added via `add_choropleth`) so that property-based search works correctly.
