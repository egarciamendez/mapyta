<p align="center">
    <a href="https://egarciamendez.github.io/mapyta">
    <img src="https://egarciamendez.github.io/mapyta/_overrides/assets/images/mapyta-logo-light-mode.svg" alt="Mapyta">
    </a>
</p>

---

**Documentation**: [https://egarciamendez.github.io/mapyta](https://egarciamendez.github.io/mapyta)

**Source Code**: [https://github.com/egarciamendez/mapyta](https://github.com/egarciamendez/mapyta)

---


**One import. A few method calls. A full interactive map.**

Build OpenStreetMap visualizations with hover tooltips, choropleths, heatmaps, and export to HTML or PNG all from Shapely geometries.

Perfect for geotechnical site plans, infrastructure overviews, or any spatial data visualization where you want more control than static images but don't need the full power of a GIS.

*Mapyta is standing on the shoulders of giants like Folium and Leaflet, but it's designed to be more intuitive and 
Pythonic for users who are already familiar with Shapely and GeoPandas. It's not trying to replace a full GIS, 
but rather to provide a simple way to create interactive maps without needing to learn a whole new set of tools.*

---

**Key features:**

- 🗺️ **Shapely-native** — pass `Point`, `Polygon`, `LineString` directly, including multi-geometries
- 📝 **Markdown/HTML hover and popup text** — bold, italic, links, lists, and code in tooltips
- 📌 **Emoji & icon markers** — any text or Font Awesome icons as markers
- 🎨 **Choropleth & heatmaps** — color-coded maps from numeric data
- 📊 **GeoPandas integration** — `Map.from_geodataframe()` one-liner
- 🌐 **Auto CRS detection** — RD New (EPSG:28992) coordinates transform automatically
- 📤 **Export anywhere** — HTML, PNG, SVG, GeoJSON, async variants, and `BytesIO` buffers
- 🧩 **Feature groups** — toggleable layers with a built-in layer control
- 🔌 **Set of tile providers** — OpenStreetMap, CartoDB, Esri, Stamen, and Kadaster

---

??? example "Full example for power users"

    Complete map with points, lines, polygons, popups, feature groups, layer control, and HTML export in one block.
    Everything below this fold explains each piece step by step.

    ```python exec="true" html="true" source="tabbed-right"
    from shapely.geometry import Point, LineString, Polygon
    from mapyta import Map, MapConfig

    m = Map(
        title="Amsterdam Overview",
        config=MapConfig(
            tile_layer=["cartodb_positron", "cartodb_dark"],
            fullscreen=True,
            minimap=True,
            measure_control=True,
            mouse_position=True,
        ),
    )

    # Feature group: landmarks
    m.create_feature_group("🏛️ Landmarks")
    m.add_point(
        point=Point(4.9041, 52.3676),
        marker="🏛️",
        tooltip="**Royal Palace**",
        popup="**Royal Palace**\nDam Square, Amsterdam\nBuilt: 1665",
        popup_style={"width": 300, "height": 120},
    )
    m.add_point(
        point=Point(4.8834, 52.3667),
        marker="📖",
        tooltip="**Anne Frank House**",
        popup="**Anne Frank House**\nPrinsengracht 263\nVisitors/year: ~1.3 million",
        popup_style={"width": 300, "height": 120},
    )
    m.add_point(
        point=Point(4.8795, 52.3600),
        marker="fa-landmark",
        tooltip="**Rijksmuseum**",
        popup="**Rijksmuseum**\nDutch art and history since 1800",
        marker_style={"font-size": "24px", "color": "green"},
    )

    # Feature group: areas
    m.create_feature_group("📍 Areas of Interest")
    m.add_polygon(
        polygon=Polygon([(4.876, 52.372), (4.889, 52.372), (4.889, 52.380), (4.876, 52.380)]),
        tooltip="**De Jordaan**\nHistoric neighbourhood",
        popup="**De Jordaan**\n\n- Narrow streets\n- Independent galleries\n- Brown cafés",
        stroke={"color": "green", "weight": 2},
        fill={"color": "blue", "opacity": 0.15},
        popup_style={"width": 300, "height": 180},
    )
    m.add_linestring(
        line=LineString([(4.8852, 52.3702), (4.8910, 52.3663), (4.8932, 52.3631), (4.884, 52.3569)]),
        tooltip="**Walking route**\n*Centraal → Leidseplein*",
        stroke={"color": "red", "weight": 4, "dash_array": "10 6"},
    )

    m.reset_target()
    m.add_circle(
        point=Point(4.8812, 52.3584),
        tooltip="**Van Gogh Museum**",
        style={"radius": 12, "stroke": {"color": "green", "weight": 2}, "fill": {"color": "orange", "opacity": 0.5}},
    )

    m.add_layer_control(collapsed=False)
    m.set_bounds(padding=0.005)

    print(m.to_html()) # markdown-exec: hide
    ```

## Quickstart

Install mapyta:

```bash
uv add mapyta
# or
pip install mapyta
```

Create your first map:

```python exec="true" html="true" source="tabbed-right"
from shapely.geometry import Point
from mapyta import Map

m = Map(title="Hello Utrecht")
m.add_point(
    point=Point(5.121311, 52.090648),
    tooltip="**Utrecht**",
    popup="**Utrecht**\nCity in the Netherlands\nPopulation: ~350k",
    caption="UTR",
)
m.to_html("hello.html")

print(m.to_html()) # markdown-exec: hide
```

Open `hello.html` in any browser and you're done.

## License

This project is licensed under the terms of the MIT license.