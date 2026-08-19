# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run all tests
uv run pytest

# Run a single test file
uv run pytest tests/test_map_creation.py

# Run a single test by name
uv run pytest tests/test_map_creation.py -k "test_name"

# Lint
uv run ruff check .

# Format
uv run ruff format .

# Type check
uv run ty check

# Docs preview (live reload)
uv run --group docs properdocs serve

# Docs production build
uv run --group docs properdocs build --clean

# Re-record the PDOK/CBS responses used by the tutorial examples
MAPYTA_DOCS_REFRESH=1 uv run --group docs properdocs build --clean --strict

# Build the way CI does: fail instead of falling back to the network
MAPYTA_DOCS_OFFLINE=1 uv run --group docs properdocs build --clean --strict
```

## Architecture

`mapyta` is a high-level interactive map builder wrapping [Folium](https://python-visualization.github.io/folium/) (
which wraps Leaflet.js). The public API is a single `Map` class; everything else is internal.

### Module responsibilities

| Module           | Role                                                                                                                                                               |
|------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `map.py`         | `Map` class — the entire public API for building and exporting maps                                                                                                |
| `config.py`      | Dataclasses for configuration: `MapConfig`, `StrokeStyle`, `FillStyle`, `CircleStyle`, `HeatmapStyle`, `PopupStyle`, `TooltipStyle`                                |
| `coordinates.py` | CRS detection and transformation to WGS84 via `pyproj`; auto-detects Dutch RD New (EPSG:28992) from coordinate ranges                                              |
| `markers.py`     | Builds Folium `DivIcon` markers from emoji, text, or plain strings                                                                                                 |
| `tiles.py`       | `TILE_PROVIDERS` dict mapping shorthand keys (e.g. `"cartodb_positron"`, `"kadaster_brt"`) to tile URLs and attributions                                           |
| `geojson.py`     | Loads GeoJSON from dicts, file paths, or strings                                                                                                                   |
| `markdown.py`    | Converts Markdown to HTML for tooltips/popups; `RawHTML` wrapper bypasses conversion                                                                               |
| `style.py`       | `resolve_style()` helper that coerces `dict                                                                                                                        | dataclass | None` to a typed dataclass |
| `export.py`      | PNG/SVG export via headless Chrome (Selenium); guarded by `check_selenium()` which raises `ImportError` if the `export` optional dependency group is not installed |

### Documentation network fixtures

The tutorial pages under `docs/tutorial/open-data.md` execute live PDOK and CBS calls. `docs/_hooks/network_cache.py` records
each response once into `docs/_fixtures/` and replays it on every later build, so CI never depends on an upstream service being
reachable or stable. A missing fixture fails the build rather than silently dropping a map from the page.

The weekly `docs-upstream-check` workflow re-records against the live services and fails when a response changed — that is the
signal to refresh the fixtures and update the affected example.

`docs/_hooks/example_output.py` redirects the `to_html()` / `to_geojson()` / `to_image()` calls in the examples to a temporary
directory. The examples keep showing realistic paths like `m.to_html("provincies.html")` without littering the working tree.
Absolute paths are left alone.

### Key design patterns

- **Fluent chaining**: all `add_*` and configuration methods return `Self`.
- **Feature groups**: `create_feature_group(name)` targets subsequent `add_*` calls to a named Folium `FeatureGroup`;
  `reset_target()` returns to the base map.
- **CRS transparency**: geometries in any CRS are passed directly; `coordinates.py` handles transformation. Explicit
  override via `source_crs` on `Map.__init__` or per call.
- **Optional Selenium**: image export is behind the `export` optional dependency (`pip install mapyta[export]`). The
  guard in `export.py` provides a clear install message on `ImportError`.

### Style conventions

- Docstrings follow NumPy convention (enforced by ruff `pydocstyle`).
- Line length: 150 characters.
- Quote style: double quotes.
- `T20` (no `print`) is enforced everywhere except `docs/`.
