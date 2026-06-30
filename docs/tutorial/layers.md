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

## Single-select dropdown

`add_layer_control()` lists every group as a checkbox, so users can show any combination at once. When the groups are mutually exclusive, one band of a graduated layer, one scenario, one year, that gets noisy and lets users tick contradictory combinations. `add_layer_dropdown()` replaces the checkboxes with a single `<select>`: exactly one group is visible at a time, and the dropdown shows which one.

```python exec="true" html="true" source="tabbed-right"
from shapely.geometry import Point
from mapyta import Map

m = Map(title="Noise levels by scenario")

m.create_feature_group("2020 baseline")
m.add_point(point=Point(5.1213, 52.0908), marker="🔇", tooltip="**42 dB**")

m.create_feature_group("2030 growth")
m.add_point(point=Point(5.1213, 52.0908), marker="🔉", tooltip="**51 dB**")

m.create_feature_group("2030 + screen")
m.add_point(point=Point(5.1213, 52.0908), marker="🔈", tooltip="**47 dB**")

m.add_layer_dropdown(label="Scenario")

m.to_html("layer_dropdown.html")

print(m.to_html()) # markdown-exec: hide
```

### How it works

**`names`** picks which groups appear, in display order. Leave it out (the default) to include every feature group in creation order. Unknown names are ignored; if none match, the call does nothing.

**`label`** is an optional caption above the dropdown. **`position`** takes any Leaflet corner (`"topleft"`, `"topright"`, `"bottomleft"`, `"bottomright"`).

On load, only the first group is shown. Selecting an option hides the others.

!!! note "Mixing with `add_layer_control()`"

    A group handled by the dropdown is automatically removed from `add_layer_control()`'s checkbox list, so it never appears in both. Base/tile layers are untouched, so you can combine the two: keep radio-button tile layers in `add_layer_control()` while a dropdown switches the overlay groups.

## Search control

Add a search box to any map with `add_search_control()`. See the [Search Control](search.md) tutorial for full details and examples.
