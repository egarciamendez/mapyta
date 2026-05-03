# Search Control

`add_search_control()` adds a search box that lets users type a name and zoom straight to the matching feature. It works on markers, GeoJSON layers, choropleth regions, and clusters — no setup required.

```python exec="true" html="true" source="tabbed-right"
from shapely.geometry import Point
from mapyta import Map

m = Map(title="City Finder")
m.add_point(Point(4.9003, 52.3728), marker="🏙️", caption="Amsterdam")
m.add_point(Point(5.1214, 52.0907), marker="🏙️", caption="Utrecht")
m.add_point(Point(4.4777, 51.9244), marker="🏙️", caption="Rotterdam")
m.add_point(Point(4.3007, 52.0705), marker="🏙️", caption="Den Haag")
m.add_point(Point(5.4697, 51.4416), marker="🏙️", caption="Eindhoven")

m.add_search_control(placeholder="Find city...")

m.to_html("cities.html")

print(m.to_html())  # markdown-exec: hide
```

Type a city name and press Enter — the map zooms to the matching marker.

## How it works

Calling `add_search_control()` with no arguments tells mapyta to search **all features** added so far. The search label is inferred automatically from each feature's properties in this priority order:

`caption` → `label` → `text` → `name` → `naam` → `title` → first string property found

So for `add_point(..., caption="Amsterdam")` the caption is picked up automatically. For GeoJSON features with a `"name"` or `"naam"` property, those are used. If no known key matches, the first non-empty string value in the properties dict is used as a fallback.

!!! tip "Override the inferred label"

    Pass `property_name` to tell mapyta exactly which property to use:

    ```python
    m.add_search_control(property_name="gemeente")
    ```

## Searching GeoJSON features

When your features come from `add_geojson()`, `add_search_control()` still works with no arguments — it picks up `"name"`, `"naam"`, or whatever string property is present:

```python exec="true" html="true" source="tabbed-right"
from mapyta import Map

geojson = {
    "type": "FeatureCollection",
    "features": [
        {"type": "Feature", "properties": {"naam": "Amsterdam", "code": "0363"}, "geometry": {"type": "Point", "coordinates": [4.9003, 52.3728]}},
        {"type": "Feature", "properties": {"naam": "Utrecht", "code": "0344"}, "geometry": {"type": "Point", "coordinates": [5.1214, 52.0907]}},
        {"type": "Feature", "properties": {"naam": "Rotterdam", "code": "0599"}, "geometry": {"type": "Point", "coordinates": [4.4777, 51.9244]}},
        {"type": "Feature", "properties": {"naam": "Den Haag", "code": "0518"}, "geometry": {"type": "Point", "coordinates": [4.3007, 52.0705]}},
    ],
}

m = Map(title="Gemeenten")
m.add_geojson(geojson, hover_fields=["naam", "code"])
m.add_search_control(placeholder="Zoek gemeente...")

print(m.to_html())  # markdown-exec: hide
```

## Searching a choropleth

For polygon layers like choropleths, put the layer in a named feature group, then pass `layer_name`, `property_name`, and `geom_type="Polygon"` so the map fits the polygon bounds on match:

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
    property_name="name",
    placeholder="Find neighbourhood...",
    zoom=14,
    geom_type="Polygon",
)

print(m.to_html())  # markdown-exec: hide
```

`layer_name` must match the name passed to `create_feature_group()`. Use `geom_type="Polygon"` whenever the features are polygons — it makes the view fit to the polygon bounds rather than zooming to a single point.

## Searching by tooltip or popup

When your markers have descriptive tooltips but no captions, pass `property_name="tooltip"` (or `"popup"`) to search that field directly:

```python exec="true" html="true" source="tabbed-right"
from shapely.geometry import Point
from mapyta import Map

m = Map(title="Amsterdam Attractions")
m.add_point(Point(4.8852, 52.3600), marker="🏛️", tooltip="Rijksmuseum — Dutch Golden Age paintings and applied arts")
m.add_point(Point(4.8783, 52.3584), marker="🎨", tooltip="Van Gogh Museum — world's largest Van Gogh collection")
m.add_point(Point(4.8799, 52.3748), marker="📖", tooltip="Anne Frank House — wartime hiding place and museum")
m.add_point(Point(4.9009, 52.3731), marker="🏙️", tooltip="Royal Palace Amsterdam — official residence of the King")
m.add_point(Point(4.9041, 52.3667), marker="⛪", tooltip="Westerkerk — tallest church tower in Amsterdam")

m.add_search_control(property_name="tooltip", placeholder="Search attractions...")

print(m.to_html())  # markdown-exec: hide
```

The search runs against the raw tooltip string. Because matching is substring-based, typing `"museum"` already narrows the list before you finish typing.

!!! note

    The tooltip value stored internally is the raw string you pass — including any Markdown syntax. So `tooltip="**Rijksmuseum**"` is stored as `"**Rijksmuseum**"`. Substring search still works, but the stars will appear as literal characters in the dropdown suggestions.

## Multiple matches

When more than one feature matches what you typed, the search control shows a dropdown of all results. The user picks the one they want and the map zooms to it.

This works automatically — no extra configuration needed. Here's an example where typing `"park"` returns five results at once:

```python exec="true" html="true" source="tabbed-right"
from shapely.geometry import Point
from mapyta import Map

m = Map(title="Amsterdam Parks")
m.add_point(Point(4.8783, 52.3618), marker="🌳", caption="Vondelpark")
m.add_point(Point(4.8595, 52.3577), marker="🌳", caption="Rembrandt Park")
m.add_point(Point(4.9024, 52.3575), marker="🌳", caption="Oosterpark")
m.add_point(Point(4.9280, 52.3648), marker="🌳", caption="Flevopark")
m.add_point(Point(4.8639, 52.3722), marker="🌳", caption="Westerpark")

m.add_search_control(placeholder="Find a park...")

print(m.to_html())  # markdown-exec: hide
```

Type `"park"` in the search box — a dropdown lists all five matches. Select one to zoom to it.

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `layer_name` | `None` | Feature group to search. `None` searches all features on the map. |
| `property_name` | `None` | GeoJSON property to use as the search label. Auto-inferred when `None`. |
| `placeholder` | `"Search..."` | Placeholder text in the search input box. |
| `position` | `"topright"` | Control position: `"topleft"`, `"topright"`, `"bottomleft"`, `"bottomright"`. |
| `zoom` | `None` | Zoom level when a result is selected. Uses the map's current zoom if `None`. |
| `geom_type` | `"Point"` | `"Point"` for markers and point features; `"Polygon"` for area features. |
