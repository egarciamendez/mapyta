# Tutorial

This tutorial walks you through mapyta from the absolute minimum to advanced features. Each page introduces exactly one concept on top of the previous one.

## Prerequisites

- Python 3.12 or later
- mapyta installed:

```bash
uv add mapyta
# or
pip install mapyta
```

## What you'll learn

| Page | Concept |
|------|---------|
| [Your First Map](first-map.md) | Create a map with a single point and export to HTML |
| [Lines & Polygons](geometries.md) | Add linestrings, polygons, and multi-geometries |
| [Markers](markers.md) | Emoji, Font Awesome, and circle markers |
| [Tooltips & Popups](tooltips-popups.md) | Markdown tooltips, click popups, and raw HTML |
| [Feature Groups](layers.md) | Toggleable layers with layer control |
| [Choropleth Maps](choropleth.md) | Color-code areas by numeric value |
| [Heatmaps](heatmaps.md) | Visualize point density |
| [Marker Clusters](clusters.md) | Group hundreds of markers at low zoom |
| [GeoPandas Integration](geodataframe.md) | Build a map directly from a GeoDataFrame |
| [DataFrames (Pandas & Polars)](dataframe.md) | Add any DataFrame with a WKT geometry column |
| [Open data (CBS & PDOK)](open-data.md) | Real Dutch datasets: provinces, population density, BAG buildings |
| [Coordinate Detection](coordinates.md) | Automatic RD New → WGS84 transformation |
| [Map Configuration](configuration.md) | Tile providers, zoom, and optional plugins |
| [Text Annotations](text-annotations.md) | Floating labels and site plan markers |
| [Export](export.md) | HTML, PNG, SVG, GeoJSON, download button, async, BytesIO |
| [Drawing Tools](drawing.md) | Let users draw on the map and capture their input |
| [Animated Layers](animated.md) | Ant paths, heatmap-with-time, timestamped GeoJSON |
| [Advanced](advanced.md) | Merge maps, GeoJSON layers, escape hatch |
| [Zoom-dependent Visibility](min-zoom.md) | Hide layers until the user zooms in |
| [FAQ](faq.md) | Common questions and answers |
