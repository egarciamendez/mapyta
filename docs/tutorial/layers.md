# Feature Groups

When your map has multiple categories of data, you want users to toggle them on and off. That's what "feature groups" are for, think of them as named folders. Everything you add while a group is active goes into that folder.

```python exec="true" html="true" source="tabbed-right"
from shapely.geometry import Point
from mapyta import Map

m = Map(title="Amsterdam POI")

# Group 1: Museums
m.create_feature_group("🏛️ Museums")
m.add_point(point=Point(4.8795, 52.3600), marker="🖼️", tooltip="**Rijksmuseum**")
m.add_point(point=Point(4.8812, 52.3584), marker="🌻", tooltip="**Van Gogh Museum**")

# Group 2: Parks
m.create_feature_group("🌳 Parks")
m.add_point(point=Point(4.8765, 52.3579), marker="🌳", tooltip="**Vondelpark**")
m.add_point(point=Point(4.9125, 52.3597), marker="🌿", tooltip="**Oosterpark**")

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
