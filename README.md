<p align="center">
    <a href="https://egarciamendez.github.io/mapyta">
    <picture>
        <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/egarciamendez/mapyta/main/docs/_overrides/assets/images/mapyta-logo-dark-mode.png">
        <img src="https://raw.githubusercontent.com/egarciamendez/mapyta/main/docs/_overrides/assets/images/mapyta-logo-light-mode.png" alt="Mapyta" width="320">
    </picture>
    </a>
</p>

<p align="center">
    <em>One import. A few method calls. A full interactive map.</em>
</p>

<p align="center">
    <a href="https://pypi.org/project/mapyta/"><img src="https://img.shields.io/pypi/v/mapyta.svg" alt="PyPI version"></a>
    <a href="https://pypi.org/project/mapyta/"><img src="https://img.shields.io/pypi/pyversions/mapyta.svg" alt="Supported Python versions"></a>
    <a href="https://github.com/egarciamendez/mapyta/actions/workflows/tests.yml"><img src="https://github.com/egarciamendez/mapyta/actions/workflows/tests.yml/badge.svg" alt="Tests"></a>
    <a href="https://egarciamendez.github.io/mapyta"><img src="https://img.shields.io/badge/docs-mkdocs--material-blue.svg" alt="Documentation"></a>
    <a href="https://github.com/egarciamendez/mapyta/blob/main/LICENSE"><img src="https://img.shields.io/pypi/l/mapyta.svg" alt="License: MIT"></a>
</p>

---

**Documentation**: [https://egarciamendez.github.io/mapyta](https://egarciamendez.github.io/mapyta)

**Source Code**: [https://github.com/egarciamendez/mapyta](https://github.com/egarciamendez/mapyta)

---

Build OpenStreetMap visualizations with hover tooltips, choropleths, heatmaps, and export to HTML or PNG all from Shapely geometries.

Perfect for geotechnical site plans, infrastructure overviews, or any spatial data visualization where you want more control than static images but don't need the full power of a GIS.

*Mapyta is standing on the shoulders of giants like Folium and Leaflet, but it's designed to be more intuitive and
Pythonic for users who are already familiar with Shapely and GeoPandas. It's not trying to replace a full GIS,
but rather to provide a simple way to create interactive maps without needing to learn a whole new set of tools.*

<p align="center">
    <a href="https://egarciamendez.github.io/mapyta/showcase/">
    <img src="https://egarciamendez.github.io/mapyta/assets/images/hero-map.png" alt="A mapyta map of Amsterdam with markers, areas, and a walking route" width="820">
    </a>
</p>

👉 **[See the Showcase](https://egarciamendez.github.io/mapyta/showcase/)** — every feature as a live, interactive map on a single page.

---

## Key features

- 🗺️ **[Shapely-native](https://egarciamendez.github.io/mapyta/tutorial/geometries/)** — pass `Point`, `Polygon`, `LineString` directly, including multi-geometries
- 📝 **[Markdown/HTML hover and popup text](https://egarciamendez.github.io/mapyta/tutorial/tooltips-popups/)** — bold, italic, links, lists, and code in tooltips
- 📌 **[Emoji & icon markers](https://egarciamendez.github.io/mapyta/tutorial/markers/)** — any text or Font Awesome icons as markers
- 🎨 **[Choropleth & heatmaps](https://egarciamendez.github.io/mapyta/tutorial/choropleth/)** — color-coded maps from numeric data
- 📊 **[GeoPandas integration](https://egarciamendez.github.io/mapyta/tutorial/geodataframe/)** — `Map.from_geodataframe()` one-liner
- 🗂️ **[DataFrame support](https://egarciamendez.github.io/mapyta/tutorial/dataframe/)** — `add_dataframe()` works with any Pandas or Polars DataFrame with a WKT geometry column
- 🌐 **[Auto CRS detection](https://egarciamendez.github.io/mapyta/tutorial/coordinates/)** — RD New (EPSG:28992) coordinates transform automatically
- 📤 **[Export anywhere](https://egarciamendez.github.io/mapyta/tutorial/export/)** — HTML, PNG, SVG, GeoJSON, async variants, and `BytesIO` buffers
- 🧩 **[Feature groups](https://egarciamendez.github.io/mapyta/tutorial/layers/)** — toggleable layers with a built-in layer control
- 🔌 **[Set of tile providers](https://egarciamendez.github.io/mapyta/tutorial/configuration/)** — OpenStreetMap, CartoDB, Esri, Stamen, and Kadaster

---

## Installation

Mapyta requires **Python 3.12+**.

```bash
uv add mapyta
# or
pip install mapyta
```

Exporting maps to **PNG/SVG images** additionally needs a headless browser (Chrome,
Chromium, or Edge) and the `export` extra:

```bash
uv add "mapyta[export]"
# or
pip install "mapyta[export]"
```

## Quickstart

Create your first map:

```python
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
```

Open `hello.html` in any browser and you're done.

Want the map as an image instead? Get raw PNG bytes or a buffer, no file needed:

```python
png_bytes = m.to_image()   # bytes, for an HTTP response or an email attachment
buf = m.to_bytesio()       # io.BytesIO, e.g. for Flask/FastAPI/Django
```

See the **[Showcase](https://egarciamendez.github.io/mapyta/showcase/)** for choropleths,
heatmaps, clusters, drawing tools, and more — each as a live, interactive map — or work
through the **[Tutorial](https://egarciamendez.github.io/mapyta/tutorial/)** one concept
at a time.

## Contributing

Issues and pull requests are welcome. To set up a local development environment:

```bash
git clone https://github.com/egarciamendez/mapyta
cd mapyta
uv sync --all-extras --all-groups
uv run pytest
```

Please open an [issue](https://github.com/egarciamendez/mapyta/issues) to discuss
substantial changes before starting.

## License

This project is licensed under the terms of the MIT license.
