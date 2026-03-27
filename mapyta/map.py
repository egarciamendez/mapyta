"""Use Mapyta to generate beatiful interactive maps.

We are standing on the shoulders of giants by using Folium as the underlying mapping library, which provides a Python
interface to Leaflet.js and OpenStreetMap tiles.

Provides a high-level API for creating interactive OpenStreetMap visualizations
with support for Shapely geometries, GeoPandas DataFrames, emoji/icon markers,
text annotations, markdown tooltip text, choropleth coloring, heatmaps,
and export to HTML, PNG, and SVG formats.

Examples
--------
>>> from shapely.geometry import Point, Polygon
>>> from mapyta import Map
>>> m = Map(title="My Map")
>>> m.add_point(Point(4.9, 52.37), marker="\U0001f4cd", tooltip="**Amsterdam**")
>>> m.add_polygon(Polygon([(4.9, 52.3), (5.0, 52.3), (5.0, 52.4), (4.9, 52.4)]))
>>> m.to_html("map.html")
"""

import asyncio
import base64
import copy
import io
import math
import tempfile
import webbrowser
from pathlib import Path
from typing import Any, Self, cast

import branca.colormap as cm
import folium
import folium.features
import folium.plugins
from shapely.geometry import (
    LinearRing,
    LineString,
    MultiLineString,
    MultiPoint,
    MultiPolygon,
    Point,
    Polygon,
)
from shapely.geometry.base import BaseGeometry

from mapyta.config import CircleStyle, DrawConfig, FillStyle, HeatmapStyle, MapConfig, PopupStyle, RawJS, StrokeStyle, TooltipStyle
from mapyta.coordinates import transform_geometry
from mapyta.export import capture_screenshot
from mapyta.geojson import load_geojson_input
from mapyta.markdown import RawHTML, markdown_to_html
from mapyta.markers import DEFAULT_CAPTION_CSS, DEFAULT_MARKER_CAPTION_CSS, build_icon_marker, build_text_marker, classify_marker, css_to_style
from mapyta.style import resolve_style
from mapyta.tiles import TILE_PROVIDERS

LEAFLET_DRAW_CSS = "https://cdnjs.cloudflare.com/ajax/libs/leaflet.draw/1.0.4/leaflet.draw.css"
LEAFLET_DRAW_JS = "https://cdnjs.cloudflare.com/ajax/libs/leaflet.draw/1.0.4/leaflet.draw.js"
VALID_DRAW_TOOLS = frozenset({"marker", "polyline", "polygon", "rectangle", "circle"})


class Map:
    """Interactive map builder backed by Folium and OpenStreetMap tiles.

    Parameters
    ----------
    center : tuple[float, float] | None
        Map center ``(latitude, longitude)``. Auto-fits if ``None``.
    title : str | None
        Title rendered at the top of the map.
    config : MapConfig | None
        Global map configuration.
    source_crs : str | None
        Default source CRS (e.g. ``"EPSG:28992"``). Auto-detects if ``None``.

    Examples
    --------
    >>> m = Map(title="Demo")
    >>> m.add_point(Point(5.0, 52.0), tooltip="**Hello**")
    >>> m.to_html("demo.html")
    """

    def __init__(
        self,
        center: tuple[float, float] | None = None,
        title: str | None = None,
        config: MapConfig | None = None,
        source_crs: str | None = None,
    ) -> None:
        self._config = config or MapConfig()
        self._center = center
        self._title = title
        self._source_crs = source_crs
        self._map = self._create_base_map()
        self._bounds: list[tuple[float, float]] = []
        self._feature_groups: dict[str, folium.FeatureGroup] = {}
        self._active_group: folium.FeatureGroup | folium.Map = self._map
        self._colormaps: list[cm.LinearColormap] = []
        self._zoom_controlled_markers: list[dict[str, Any]] = []
        self._zoom_js_injected: bool = False
        self._draw_config: DrawConfig | None = None
        self._draw_injected: bool = False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _create_base_map(self) -> folium.Map:  # noqa: PLR0912, C901
        """Create the base Folium Map object.

        Returns
        -------
        folium.Map
        """
        cfg = self._config

        # Normalise tile_layer to a list
        layers = cfg.tile_layer if isinstance(cfg.tile_layer, list) else [cfg.tile_layer]
        multiple = len(layers) > 1

        if multiple:
            # Multiple layers: create map without tiles, add all as TileLayer
            kwargs: dict[str, Any] = {
                "tiles": None,
                "zoom_start": cfg.zoom_start,
                "min_zoom": cfg.min_zoom,
                "max_zoom": cfg.max_zoom,
                "width": cfg.width,
                "height": cfg.height,
                "control_scale": cfg.control_scale,
            }
            if self._center:
                kwargs["location"] = list(self._center)
            fmap = folium.Map(**kwargs)

            for i, layer_key in enumerate(layers):
                p = TILE_PROVIDERS.get(layer_key.lower())
                if p:
                    folium.TileLayer(
                        tiles=p["tiles"],
                        name=p.get("name", layer_key),
                        attr=p.get("attr"),
                        show=i == 0,
                    ).add_to(fmap)
                else:
                    folium.TileLayer(
                        tiles=layer_key,
                        name=layer_key,
                        attr=cfg.attribution,
                        show=i == 0,
                    ).add_to(fmap)
        else:
            # Single layer: pass directly to folium.Map (original behaviour)
            provider = TILE_PROVIDERS.get(layers[0].lower())
            if provider:
                tiles = provider["tiles"]
                attr = provider.get("attr")
            else:
                tiles = layers[0]
                attr = cfg.attribution

            kwargs: dict[str, Any] = {
                "tiles": tiles,
                "zoom_start": cfg.zoom_start,
                "min_zoom": cfg.min_zoom,
                "max_zoom": cfg.max_zoom,
                "width": cfg.width,
                "height": cfg.height,
                "control_scale": cfg.control_scale,
            }
            if self._center:
                kwargs["location"] = list(self._center)
            if attr:
                kwargs["attr"] = attr
            fmap = folium.Map(**kwargs)

        # Title overlay
        if self._title:
            title_html = (
                '<div style="position:fixed;top:10px;left:50%;transform:translateX(-50%);'
                "z-index:1000;background:rgba(255,255,255,0.9);padding:8px 20px;"
                "border-radius:6px;font-family:Arial,sans-serif;font-size:16px;"
                f'font-weight:bold;box-shadow:0 2px 6px rgba(0,0,0,0.3);pointer-events:none;">'
                f"{self._title}</div>"
            )
            fmap.get_root().html.add_child(folium.Element(title_html))  # type: ignore[union-attr]

        # Optional plugins
        if cfg.fullscreen:
            folium.plugins.Fullscreen().add_to(fmap)
        if cfg.minimap:
            folium.plugins.MiniMap(toggle_display=True).add_to(fmap)
        if cfg.measure_control:
            folium.plugins.MeasureControl(primary_length_unit="meters", primary_area_unit="sqmeters").add_to(fmap)
        if cfg.mouse_position:
            folium.plugins.MousePosition(position="bottomleft", separator=" | ", num_digits=6).add_to(fmap)
        return fmap

    def _transform(self, geom: BaseGeometry) -> BaseGeometry:
        """Transform geometry to WGS84."""
        return transform_geometry(geom, self._source_crs)

    def _extend_bounds(self, geom: BaseGeometry) -> None:
        """Track geometry bounds for auto-fit."""
        b = geom.bounds  # (minx, miny, maxx, maxy) = (lon, lat, lon, lat)
        self._bounds.append((b[1], b[0]))
        self._bounds.append((b[3], b[2]))

    def _make_tooltip(
        self,
        hover: str | RawHTML | None,
        tooltip_style: TooltipStyle | dict[str, Any] | None = None,
    ) -> folium.Tooltip | None:
        """Create Tooltip from markdown or raw HTML."""
        if not hover:
            return None
        ts = resolve_style(tooltip_style, TooltipStyle) or TooltipStyle()
        html = hover if isinstance(hover, RawHTML) else markdown_to_html(hover)
        return folium.Tooltip(html, sticky=ts.sticky, style=ts.style)

    def _make_popup(self, popup: str | RawHTML | None, popup_style: PopupStyle | dict[str, Any] | None = None) -> folium.Popup | None:
        """Create Popup from markdown or raw HTML."""
        if not popup:
            return None
        ps = resolve_style(popup_style, PopupStyle) or PopupStyle()
        html = popup if isinstance(popup, RawHTML) else markdown_to_html(popup)
        iframe = folium.IFrame(html, width=ps.width, height=ps.height)  # type: ignore[arg-type]
        return folium.Popup(iframe, max_width=ps.max_width)

    def _target(self) -> folium.FeatureGroup | folium.Map:
        """Current target layer."""
        return self._active_group

    def _fit_bounds(self) -> None:
        """Fit map view to tracked bounds."""
        if self._bounds:
            self._map.fit_bounds(self._bounds)

    def set_bounds(self, padding: float = 0.0, restrict: bool = False) -> Self:
        """Fit map view to tracked bounds with optional padding and restriction.

        Parameters
        ----------
        padding : float
            Padding in degrees around the data bounds.
        restrict : bool
            If ``True``, prevent the user from panning/zooming beyond the
            data bounds (sets ``maxBounds`` and ``maxBoundsViscosity``).

        Returns
        -------
        Map
            Self, for chaining.
        """
        if not self._bounds:
            return self

        lats = [b[0] for b in self._bounds]
        lons = [b[1] for b in self._bounds]
        bounds = [
            [min(lats) - padding, min(lons) - padding],
            [max(lats) + padding, max(lons) + padding],
        ]
        self._map.fit_bounds(bounds)

        if restrict:
            self._map.options["maxBounds"] = bounds
            self._map.options["maxBoundsViscosity"] = 1.0

        return self

    # ------------------------------------------------------------------
    # Feature groups / layers
    # ------------------------------------------------------------------

    def create_feature_group(self, name: str, show: bool = True) -> Self:
        """Create a named feature group for layer toggling.

        Subsequent ``add_*`` calls target this group until changed.

        To stop targeting a group and return to the base map, call ``reset_target()``.

        Parameters
        ----------
        name : str
            Display name for layer control.
        show : bool
            Visible by default.

        Returns
        -------
        Map
            Self, for chaining.
        """
        fg = folium.FeatureGroup(name=name, show=show)
        fg.add_to(self._map)
        self._feature_groups[name] = fg
        self._active_group = fg
        return self

    def set_feature_group(self, name: str) -> Self:
        """Activate an existing feature group.

        Parameters
        ----------
        name : str
            Feature group name.

        Returns
        -------
        Map

        Raises
        ------
        KeyError
            If group does not exist.
        """
        if name not in self._feature_groups:
            raise KeyError(f"Feature group '{name}' not found. Available: {list(self._feature_groups.keys())}")
        self._active_group = self._feature_groups[name]
        return self

    def reset_target(self) -> Self:
        """Reset target to base map (no feature group).

        Returns
        -------
        Map
        """
        self._active_group = self._map
        return self

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def enable_draw(
        self,
        tools: list[str] | None = None,
        on_submit: str | RawJS | None = None,
        viktor_params: dict[str, str] | None = None,
        position: str = "topleft",
        submit_label: str = "Submit",
        draw_style: dict[str, Any] | None = None,
        edit: bool = True,
    ) -> Self:
        """Enable drawing controls on the map.

        Parameters
        ----------
        tools : list[str] | None
            Active drawing tools.  Valid values: ``"marker"``,
            ``"polyline"``, ``"polygon"``, ``"rectangle"``, ``"circle"``.
            Defaults to ``["polyline", "polygon", "marker"]``.
        on_submit : str | RawJS | None
            Callback when the user clicks Submit.  ``None`` downloads a
            GeoJSON file; a URL string sends a ``POST`` request; a plain
            string calls ``window["name"](geojson)``; a :class:`RawJS`
            instance is inlined verbatim.
        viktor_params : dict[str, str] | None
            VIKTOR field-name mapping.  Keys must be draw-tool names
            present in *tools*; values are VIKTOR parameter field names.
            When set, overrides *on_submit* and sends drawn geometries
            via ``viktorSdk.sendParams()``.  ``"circle"`` is not
            supported with VIKTOR.
        position : str
            Leaflet control position.
        submit_label : str
            Label for the submit button.
        draw_style : dict[str, Any] | None
            ``shapeOptions`` override for drawn shapes.
        edit : bool
            Whether edit/delete controls are active.

        Returns
        -------
        Map

        Raises
        ------
        ValueError
            If *tools* contains an invalid tool name, if ``"circle"`` is
            used with *viktor_params*, or if a *viktor_params* key is
            not in *tools*.
        """
        if tools is None:
            tools = ["polyline", "polygon", "marker"]

        invalid = set(tools) - VALID_DRAW_TOOLS
        if invalid:
            msg = f"Invalid draw tool(s): {', '.join(sorted(invalid))}. Valid: {', '.join(sorted(VALID_DRAW_TOOLS))}"
            raise ValueError(msg)

        if viktor_params:
            if "circle" in tools:
                msg = "Circle tool is not supported with viktor_params (no VIKTOR geometry type for circles)"
                raise ValueError(msg)
            invalid_keys = set(viktor_params.keys()) - set(tools)
            if invalid_keys:
                msg = f"viktor_params key(s) {', '.join(sorted(invalid_keys))} not in tools {tools}"
                raise ValueError(msg)

        self._draw_config = DrawConfig(
            tools=tools,
            on_submit=on_submit,
            viktor_params=viktor_params,
            position=position,
            submit_label=submit_label,
            draw_style=draw_style,
            edit=edit,
        )
        self._draw_injected = False
        return self

    def _inject_draw_plugin(self) -> None:
        """Inject Leaflet.draw CSS, JS, and control script (idempotent)."""
        if self._draw_injected:
            return
        cfg = self._draw_config
        assert cfg is not None

        # Build draw_options: disabled tools → False; active with style → shapeOptions dict.
        all_tools = ["polyline", "polygon", "marker", "rectangle", "circle"]
        draw_options: dict[str, Any] = {"circlemarker": False}
        for tool in all_tools:
            if tool not in cfg.tools:
                draw_options[tool] = False
            elif cfg.draw_style:
                draw_options[tool] = {"shapeOptions": cfg.draw_style}

        edit_options: dict[str, Any] = {"remove": cfg.edit}

        # Folium's built-in Draw plugin loads leaflet.draw CSS/JS via JSCSSMixin
        # (placed in <head>), guaranteeing correct load order in both standalone
        # HTML and embeddable iframe / srcdoc rendering modes.
        draw_plugin = folium.plugins.Draw(
            export=False,
            show_geometry_on_click=False,
            position=cfg.position,
            draw_options=draw_options,
            edit_options=edit_options,
        )
        draw_plugin.add_to(self._map)

        if cfg.viktor_params:
            self._map.get_root().html.add_child(  # type: ignore[union-attr]
                folium.Element("<script src=VIKTOR_JS_SDK></script>")
            )

        # Submit button: IIFE in body polls for _leaflet_map (set after L.map init).
        drawn_items_var = f"drawnItems_{draw_plugin.get_name()}"
        self._map.get_root().html.add_child(  # type: ignore[union-attr]
            folium.Element(self._build_draw_script(drawn_items_var))
        )
        self._draw_injected = True

    def _build_draw_script(self, drawn_items_var: str) -> str:
        """Build the submit button ``<script>`` block (IIFE, polls for map init)."""
        cfg = self._draw_config
        assert cfg is not None

        callback_js = self._build_draw_callback_js()

        return (
            "<script>\n"
            "(function() {\n"
            "    var attempts = 0;\n"
            "    var checkInterval = setInterval(function() {\n"
            "        if (++attempts > 100) { clearInterval(checkInterval); return; }\n"
            "        var mapContainer = document.querySelector('.folium-map');\n"
            "        if (!mapContainer || !mapContainer._leaflet_map) return;\n"
            "        clearInterval(checkInterval);\n"
            "        var map = mapContainer._leaflet_map;\n"
            "\n"
            "        var submitControl = L.control({position: 'bottomright'});\n"
            "        submitControl.onAdd = function() {\n"
            "            var div = L.DomUtil.create('div', 'leaflet-bar');\n"
            "            var btn = L.DomUtil.create('a', '', div);\n"
            "            btn.href = '#';\n"
            f"            btn.innerHTML = '{cfg.submit_label}';\n"
            "            btn.style.cssText = 'padding:8px 20px;background:#1e90ff;color:#fff;' +\n"
            "                'text-decoration:none;font-weight:bold;border-radius:4px;' +\n"
            "                'display:inline-block;font-size:14px;cursor:pointer;';\n"
            "            btn.onclick = function(e) {\n"
            "                e.preventDefault();\n"
            "                e.stopPropagation();\n"
            f"                var geojson = {drawn_items_var}.toGeoJSON();\n"
            f"                {callback_js}\n"
            "            };\n"
            "            L.DomEvent.disableClickPropagation(div);\n"
            "            return div;\n"
            "        };\n"
            "        submitControl.addTo(map);\n"
            "    }, 100);\n"
            "})();\n"
            "</script>"
        )

    def _build_draw_callback_js(self) -> str:
        """Build the JavaScript callback for the submit button."""
        cfg = self._draw_config
        assert cfg is not None

        # Priority 1: VIKTOR
        if cfg.viktor_params:
            return self._build_viktor_callback_js()

        # Priority 2: RawJS
        if isinstance(cfg.on_submit, RawJS):
            return f"({cfg.on_submit.js})(geojson);"

        # Priority 3: URL (fetch)
        if isinstance(cfg.on_submit, str) and cfg.on_submit.startswith("http"):
            return f"fetch(\"{cfg.on_submit}\", {{method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify(geojson)}});"

        # Priority 4: Function name
        if isinstance(cfg.on_submit, str):
            return (
                f'if (typeof window["{cfg.on_submit}"] === "function") {{ '
                f'window["{cfg.on_submit}"](geojson); '
                "} else { "
                f'console.error("Function " + "{cfg.on_submit}" + " not found"); '
                "}"
            )

        # Priority 5: Download
        return (
            "var blob = new Blob([JSON.stringify(geojson, null, 2)], {type: 'application/json'});\n"
            "                var url = URL.createObjectURL(blob);\n"
            "                var a = document.createElement('a');\n"
            "                a.href = url; a.download = 'drawn_features.geojson';\n"
            "                a.click(); URL.revokeObjectURL(url);"
        )

    def _build_viktor_callback_js(self) -> str:
        """Build JavaScript for VIKTOR ``sendParams()`` with coordinate conversion."""
        cfg = self._draw_config
        assert cfg is not None
        assert cfg.viktor_params is not None

        lines = ["var params = {};"]
        lines.append("geojson.features.forEach(function(feature) {")
        lines.append("    var geom = feature.geometry;")

        for tool, field_name in cfg.viktor_params.items():
            if tool == "marker":
                lines.append('    if (geom.type === "Point") {')
                lines.append(f'        params["{field_name}"] = {{lat: geom.coordinates[1], lon: geom.coordinates[0]}};')
                lines.append("    }")
            elif tool == "polyline":
                lines.append('    if (geom.type === "LineString") {')
                lines.append(f'        params["{field_name}"] = geom.coordinates.map(function(c) {{')
                lines.append("            return {lat: c[1], lon: c[0]};")
                lines.append("        });")
                lines.append("    }")
            elif tool in ("polygon", "rectangle"):
                lines.append('    if (geom.type === "Polygon") {')
                lines.append(f'        params["{field_name}"] = geom.coordinates[0].map(function(c) {{')
                lines.append("            return {lat: c[1], lon: c[0]};")
                lines.append("        });")
                lines.append("    }")

        lines.append("});")
        lines.append('if (typeof viktorSdk !== "undefined") {')
        lines.append("    viktorSdk.sendParams(params, true);")
        lines.append("} else {")
        lines.append('    console.warn("viktorSdk not available. Params:", JSON.stringify(params, null, 2));')
        lines.append("}")

        return "\n                ".join(lines)

    # ------------------------------------------------------------------
    # Adding geometries
    # ------------------------------------------------------------------

    def add_point(
        self,
        point: Point,
        marker: str | None = None,
        caption: str | None = None,
        tooltip: str | RawHTML | None = None,
        popup: str | RawHTML | None = None,
        marker_style: dict[str, str] | None = None,
        caption_style: dict[str, str] | None = None,
        tooltip_style: TooltipStyle | dict[str, Any] | None = None,
        popup_style: PopupStyle | dict[str, Any] | None = None,
        min_zoom: int | None = None,
    ) -> Self:
        """Add a location marker.

        Parameters
        ----------
        point : Point
            Shapely Point ``(x, y)`` in source CRS.
        marker : str | None
            Desired marker symbol.  Rendering path is auto-detected:

            - Bare icon name (e.g. ``"home"``) → Glyphicon prefix.
            - Bare FA name (e.g. ``"fa-arrow-right"``) → ``fa-solid`` prefix.
            - Full CSS class (e.g. ``"fa-solid fa-house"``) → used as-is.
            - Emoji / unicode text → rendered as text DivIcon.
            - ``None`` → default ``"arrow-down"`` icon.
        caption : str | None
            Text annotation placed below the marker.  Works with any marker
            type (emoji, icon).  Can be styled via ``caption_style``.
        tooltip : str | RawHTML | None
            Information shown on mouse tooltip.  Markdown supported for
            strings, or use ``RawHTML`` for pre-formatted HTML.
        popup : str | RawHTML | None
            Information shown on click.  Markdown supported for strings,
            or use ``RawHTML`` for pre-formatted HTML.
        marker_style : dict[str, str] | None
            CSS property overrides for the marker element.
        caption_style : dict[str, str] | None
            CSS property overrides for the caption.
        tooltip_style : TooltipStyle | dict[str, Any] | None
            Tooltip appearance.
        popup_style : PopupStyle | dict[str, Any] | None
            Popup dimensions.
        min_zoom : int | None
            Minimum zoom level at which the marker is visible.
            ``None`` or ``0`` means always visible.

        Returns
        -------
        Map
        """
        point = cast(Point, self._transform(point))
        self._extend_bounds(point)
        lat, lon = point.y, point.x

        css = marker_style or {}
        cap_css = {**DEFAULT_MARKER_CAPTION_CSS, **(caption_style or {})}

        kind = classify_marker(marker) if marker else "icon_name"
        if kind == "emoji":
            assert marker is not None  # guarded by classify_marker above
            icon = build_text_marker(marker, css, caption, cap_css)
        else:
            icon_name = marker or "arrow-down"
            icon = build_icon_marker(icon_name, css, caption, cap_css)

        m = folium.Marker(
            location=[lat, lon],
            icon=icon,
            tooltip=self._make_tooltip(tooltip, tooltip_style),
            popup=self._make_popup(popup, popup_style),
        )
        m.add_to(self._target())

        if min_zoom is not None and min_zoom > 0:
            self._zoom_controlled_markers.append(
                {
                    "var_name": m.get_name(),
                    "min_zoom": min_zoom,
                }
            )

        return self

    def add_circle(
        self,
        point: Point,
        tooltip: str | RawHTML | None = None,
        popup: str | RawHTML | None = None,
        style: CircleStyle | dict[str, Any] | None = None,
        min_zoom: int | None = None,
        popup_style: PopupStyle | dict[str, Any] | None = None,
    ) -> Self:
        """Add a circle marker (fixed pixel size).

        Parameters
        ----------
        point : Point
            Shapely Point.
        tooltip : str | RawHTML | None
            Markdown tooltip, or ``RawHTML`` for pre-formatted HTML.
        popup : str | RawHTML | None
            Markdown popup, or ``RawHTML`` for pre-formatted HTML.
        style : CircleStyle | dict[str, Any] | None
            Circle appearance.
        min_zoom : int | None
            Minimum zoom level at which the marker is visible.
        popup_style : PopupStyle | dict[str, Any] | None
            Popup dimensions.

        Returns
        -------
        Map
        """
        point = cast(Point, self._transform(point))
        self._extend_bounds(point)
        cs = resolve_style(style, CircleStyle) or CircleStyle()
        marker = folium.CircleMarker(
            location=[point.y, point.x],
            radius=cs.radius,
            color=cs.stroke.color,
            weight=cs.stroke.weight,
            opacity=cs.stroke.opacity,
            fill=True,
            fill_color=cs.fill.color,
            fill_opacity=cs.fill.opacity,
            tooltip=self._make_tooltip(tooltip),
            popup=self._make_popup(popup, popup_style),
            dash_array=cs.stroke.dash_array,
        )
        marker.add_to(self._target())
        if min_zoom is not None and min_zoom > 0:
            self._zoom_controlled_markers.append(
                {
                    "var_name": marker.get_name(),
                    "min_zoom": min_zoom,
                }
            )
        return self

    def add_linestring(
        self,
        line: LineString,
        tooltip: str | RawHTML | None = None,
        popup: str | RawHTML | None = None,
        stroke: StrokeStyle | dict[str, Any] | None = None,
        popup_style: PopupStyle | dict[str, Any] | None = None,
    ) -> Self:
        """Add a LineString.

        Parameters
        ----------
        line : LineString
            Shapely LineString.
        tooltip : str | RawHTML | None
            Markdown tooltip, or ``RawHTML`` for pre-formatted HTML.
        popup : str | RawHTML | None
            Markdown popup, or ``RawHTML`` for pre-formatted HTML.
        stroke : StrokeStyle | dict[str, Any] | None
            Line style.
        popup_style : PopupStyle | dict[str, Any] | None
            Popup dimensions.

        Returns
        -------
        Map
        """
        line = cast(LineString, self._transform(line))
        self._extend_bounds(line)
        s = resolve_style(stroke, StrokeStyle) or StrokeStyle()
        locations = [(c[1], c[0]) for c in line.coords]
        folium.PolyLine(
            locations=locations,
            color=s.color,
            weight=s.weight,
            opacity=s.opacity,
            dash_array=s.dash_array,
            tooltip=self._make_tooltip(tooltip),
            popup=self._make_popup(popup, popup_style),
        ).add_to(self._target())
        return self

    def add_polygon(
        self,
        polygon: Polygon,
        tooltip: str | RawHTML | None = None,
        popup: str | RawHTML | None = None,
        stroke: StrokeStyle | dict[str, Any] | None = None,
        fill: FillStyle | dict[str, Any] | None = None,
        popup_style: PopupStyle | dict[str, Any] | None = None,
    ) -> Self:
        """Add a Polygon.

        Parameters
        ----------
        polygon : Polygon
            Shapely Polygon.
        tooltip : str | RawHTML | None
            Markdown tooltip, or ``RawHTML`` for pre-formatted HTML.
        popup : str | RawHTML | None
            Markdown popup, or ``RawHTML`` for pre-formatted HTML.
        stroke : StrokeStyle | dict[str, Any] | None
            Border style.
        fill : FillStyle | dict[str, Any] | None
            Fill style.
        popup_style : PopupStyle | dict[str, Any] | None
            Popup dimensions.

        Returns
        -------
        Map
        """
        polygon = cast(Polygon, self._transform(polygon))
        self._extend_bounds(polygon)
        s = resolve_style(stroke, StrokeStyle) or StrokeStyle()
        f = resolve_style(fill, FillStyle) or FillStyle()
        exterior = [(c[1], c[0]) for c in polygon.exterior.coords]
        locations: list[list[tuple[float, float]]] = [exterior] + [[(c[1], c[0]) for c in interior.coords] for interior in polygon.interiors]
        folium.Polygon(
            locations=locations,
            color=s.color,
            weight=s.weight,
            opacity=s.opacity,
            dash_array=s.dash_array,
            fill=True,
            fill_color=f.color,
            fill_opacity=f.opacity,
            tooltip=self._make_tooltip(tooltip),
            popup=self._make_popup(popup, popup_style),
        ).add_to(self._target())
        return self

    def add_multipolygon(
        self,
        mp: MultiPolygon,
        hover: str | RawHTML | None = None,
        popup: str | RawHTML | None = None,
        stroke: StrokeStyle | dict[str, Any] | None = None,
        fill: FillStyle | dict[str, Any] | None = None,
        popup_style: PopupStyle | dict[str, Any] | None = None,
    ) -> Self:
        """Add a MultiPolygon.

        Parameters
        ----------
        mp : MultiPolygon
            Shapely MultiPolygon.
        hover, popup, stroke, fill, popup_style
            See ``add_polygon``.

        Returns
        -------
        Map
        """
        for poly in mp.geoms:
            self.add_polygon(poly, tooltip=hover, popup=popup, stroke=stroke, fill=fill, popup_style=popup_style)
        return self

    def add_multilinestring(
        self,
        ml: MultiLineString,
        hover: str | RawHTML | None = None,
        popup: str | RawHTML | None = None,
        stroke: StrokeStyle | dict[str, Any] | None = None,
        popup_style: PopupStyle | dict[str, Any] | None = None,
    ) -> Self:
        """Add a MultiLineString.

        Parameters
        ----------
        ml : MultiLineString
            Shapely MultiLineString.
        hover, popup, stroke, popup_style
            See ``add_linestring``.

        Returns
        -------
        Map
        """
        for line in ml.geoms:
            self.add_linestring(line, tooltip=hover, popup=popup, stroke=stroke, popup_style=popup_style)
        return self

    def add_multipoint(
        self,
        mp: MultiPoint,
        hover: str | RawHTML | None = None,
        popup: str | RawHTML | None = None,
        label: str | None = None,
        marker_style: dict[str, str] | None = None,
        popup_style: PopupStyle | dict[str, Any] | None = None,
    ) -> Self:
        """Add a MultiPoint.

        Parameters
        ----------
        mp : MultiPoint
            Shapely MultiPoint.
        hover, popup, label, marker_style, popup_style
            See ``add_point``.

        Returns
        -------
        Map
        """
        for pt in mp.geoms:
            self.add_point(pt, tooltip=hover, popup=popup, marker=label, marker_style=marker_style, popup_style=popup_style)
        return self

    def add_geometry(
        self,
        geom: BaseGeometry,
        hover: str | RawHTML | None = None,
        popup: str | RawHTML | None = None,
        label: str | None = None,
        stroke: StrokeStyle | dict[str, Any] | None = None,
        fill: FillStyle | dict[str, Any] | None = None,
        marker_style: dict[str, str] | None = None,
        popup_style: PopupStyle | dict[str, Any] | None = None,
    ) -> Self:
        """Add any Shapely geometry (auto-dispatches by type).

        Parameters
        ----------
        geom : BaseGeometry
            Any supported Shapely geometry.
        hover, popup, label, stroke, fill, marker_style, popup_style
            Style and interaction parameters.

        Returns
        -------
        Map

        Raises
        ------
        TypeError
            If geometry type is unsupported.
        """
        if isinstance(geom, Point):
            self.add_point(geom, tooltip=hover, popup=popup, marker=label, marker_style=marker_style, popup_style=popup_style)
        elif isinstance(geom, LinearRing):
            # LinearRing is a subclass of LineString — check first
            self.add_linestring(LineString(geom.coords), tooltip=hover, popup=popup, stroke=stroke, popup_style=popup_style)
        elif isinstance(geom, LineString):
            self.add_linestring(geom, tooltip=hover, popup=popup, stroke=stroke, popup_style=popup_style)
        elif isinstance(geom, Polygon):
            self.add_polygon(geom, tooltip=hover, popup=popup, stroke=stroke, fill=fill, popup_style=popup_style)
        elif isinstance(geom, MultiPolygon):
            self.add_multipolygon(geom, hover=hover, popup=popup, stroke=stroke, fill=fill, popup_style=popup_style)
        elif isinstance(geom, MultiLineString):
            self.add_multilinestring(geom, hover=hover, popup=popup, stroke=stroke, popup_style=popup_style)
        elif isinstance(geom, MultiPoint):
            self.add_multipoint(geom, hover=hover, popup=popup, label=label, marker_style=marker_style, popup_style=popup_style)
        else:
            raise TypeError(f"Unsupported geometry type: {type(geom).__name__}")
        return self

    # ------------------------------------------------------------------
    # GeoJSON
    # ------------------------------------------------------------------

    def add_geojson(
        self,
        data: dict | str | Path,
        hover_fields: list[str] | None = None,
        style: dict[str, Any] | None = None,
        highlight: dict[str, Any] | None = None,
    ) -> Self:
        """Add a GeoJSON layer.

        Parameters
        ----------
        data : dict | str | Path
            GeoJSON as dict, JSON string, or file path.
        hover_fields : list[str] | None
            Property fields for the tooltip.
        style : dict[str, Any] | None
            Style kwargs.
        highlight : dict[str, Any] | None
            Highlight kwargs for mouse-over.

        Returns
        -------
        Map
        """
        data = load_geojson_input(data)

        ds = {"color": "#3388ff", "weight": 2, "fillOpacity": 0.2}
        if style:
            ds.update(style)
        dh = {"weight": 5, "fillOpacity": 0.4}
        if highlight:
            dh.update(highlight)

        tooltip = folium.GeoJsonTooltip(fields=hover_fields, localize=True) if hover_fields else None

        layer = folium.GeoJson(
            data,
            style_function=lambda _: ds,
            highlight_function=lambda _: dh,
            tooltip=tooltip,
        )
        layer.add_to(self._target())
        try:
            layer_bounds = layer.get_bounds()
            if layer_bounds:
                self._bounds.extend(cast(list[tuple[float, float]], layer_bounds))
        except Exception:
            pass
        return self

    # ------------------------------------------------------------------
    # Choropleth / colormap
    # ------------------------------------------------------------------

    def add_choropleth(  # noqa: C901, PLR0913
        self,
        geojson_data: dict | str | Path,
        value_column: str,
        key_on: str,
        values: dict[str, float] | None = None,
        vmin: float | None = None,
        vmax: float | None = None,
        legend_name: str | None = None,
        nan_fill_color: str = "#cccccc",
        nan_fill_opacity: float = 0.4,
        line_weight: float = 1.0,
        line_opacity: float = 0.5,
        fill_opacity: float = 0.7,
        hover_fields: list[str] | None = None,
    ) -> Self:
        """Add a choropleth (color-coded) layer.

        Parameters
        ----------
        geojson_data : dict | str | Path
            GeoJSON FeatureCollection.
        value_column : str
            Property name with numeric values.
        key_on : str
            Join key, e.g. ``"feature.properties.id"``.
        values : dict[str, float] | None
            Key -> value mapping. Reads from properties if ``None``.
        vmin, vmax : float | None
            Color scale range. Auto-calculated if ``None``.
        legend_name : str | None
            Legend marker.
        nan_fill_color : str
            Color for missing values.
        nan_fill_opacity : float
            Opacity for missing values.
        line_weight, line_opacity, fill_opacity : float
            Styling parameters.
        hover_fields : list[str] | None
            Tooltip property fields.

        Returns
        -------
        Map
        """
        geojson_data = load_geojson_input(geojson_data)

        # Extract values if not provided
        if values is None:
            values = {}
            key_parts = key_on.split(".")
            for feat in geojson_data.get("features", []):
                obj = feat
                for part in key_parts[1:]:
                    obj = obj.get(part, {})
                key = obj if isinstance(obj, str) else str(obj)
                val = feat.get("properties", {}).get(value_column)
                if val is not None:
                    values[key] = float(val)

        # Min/max
        vals = list(values.values())
        if vals:
            vmin = vmin if vmin is not None else min(vals)
            vmax = vmax if vmax is not None else max(vals)

        # Build colormap
        colormap = cm.LinearColormap(
            colors=["#ffffb2", "#fecc5c", "#fd8d3c", "#f03b20", "#bd0026"],
            vmin=vmin if vmin is not None else 0,
            vmax=vmax if vmax is not None else 1,
            caption=legend_name or value_column,
        )

        # Capture in closure
        _vals, _cmap = values, colormap

        def style_fn(feature: dict) -> dict:
            obj = feature
            for part in key_on.split(".")[1:]:
                obj = obj.get(part, {})
            key = obj if isinstance(obj, str) else str(obj)
            val = _vals.get(key)
            if val is not None:
                return {"fillColor": _cmap(val), "color": "#333", "weight": line_weight, "fillOpacity": fill_opacity, "opacity": line_opacity}
            return {"fillColor": nan_fill_color, "color": "#333", "weight": line_weight, "fillOpacity": nan_fill_opacity, "opacity": line_opacity}

        tooltip = folium.GeoJsonTooltip(fields=hover_fields, localize=True) if hover_fields else None
        layer = folium.GeoJson(
            geojson_data,
            style_function=style_fn,
            highlight_function=lambda _: {"weight": 3, "fillOpacity": min(fill_opacity + 0.15, 1.0)},
            tooltip=tooltip,
        )
        layer.add_to(self._target())
        colormap.add_to(self._map)
        self._colormaps.append(colormap)

        try:
            layer_bounds = layer.get_bounds()
            if layer_bounds:
                self._bounds.extend(cast(list[tuple[float, float]], layer_bounds))
        except Exception:
            pass
        return self

    # ------------------------------------------------------------------
    # Heatmap
    # ------------------------------------------------------------------

    def add_heatmap(
        self,
        points: list[Point] | list[tuple[float, float]] | list[tuple[float, float, float]],
        style: HeatmapStyle | dict[str, Any] | None = None,
        name: str | None = None,
    ) -> Self:
        """Add a heatmap layer.

        Parameters
        ----------
        points : list[Point] | list[tuple]
            Shapely Points ``(lon, lat)`` or tuples ``(lat, lon[, intensity])``.
        style : HeatmapStyle | dict[str, Any] | None
            Heatmap appearance.
        name : str | None
            Layer name.

        Returns
        -------
        Map
        """
        hs = resolve_style(style, HeatmapStyle) or HeatmapStyle()
        heat_data: list[list[float]] = []
        for p in points:
            if isinstance(p, Point):
                pt = cast(Point, self._transform(p))
                heat_data.append([pt.y, pt.x])
                self._extend_bounds(pt)
            elif len(p) == 2:
                heat_data.append([p[0], p[1]])
                self._bounds.append((p[0], p[1]))
            else:
                heat_data.append(list(p[:3]))
                self._bounds.append((p[0], p[1]))

        kwargs: dict[str, Any] = {
            "radius": hs.radius,
            "blur": hs.blur,
            "min_opacity": hs.min_opacity,
            "max_zoom": hs.max_zoom,
        }
        if hs.gradient:
            kwargs["gradient"] = hs.gradient

        folium.plugins.HeatMap(heat_data, name=name, **kwargs).add_to(self._target())
        return self

    # ------------------------------------------------------------------
    # Marker cluster
    # ------------------------------------------------------------------

    def add_marker_cluster(
        self,
        points: list[Point],
        labels: list[str] | None = None,
        hovers: list[str] | None = None,
        popups: list[str] | None = None,
        marker_style: dict[str, str] | None = None,
        name: str | None = None,
        min_zoom: int | None = None,
        popup_style: PopupStyle | dict[str, Any] | None = None,
        captions: list[str] | None = None,
        caption_style: dict[str, str] | None = None,
    ) -> Self:
        """Add clustered markers that group at low zoom.

        Parameters
        ----------
        points : list[Point]
            Shapely Points.
        labels : list[str] | None
            Per-location marker content (icon names or emoji/text).
        hovers : list[str] | None
            Per-location markdown tooltips.
        popups : list[str] | None
            Per-location markdown popups.
        marker_style : dict[str, str] | None
            CSS property overrides for each marker.
        name : str | None
            Layer name.
        min_zoom : int | None
            Minimum zoom level at which the cluster is visible.
        popup_style : PopupStyle | dict[str, Any] | None
            Popup dimensions.
        captions : list[str] | None
            Per-location text annotations placed below each marker.
        caption_style : dict[str, str] | None
            CSS property overrides for ``captions``.

        Returns
        -------
        Map
        """
        css = marker_style or {}
        cap_css = {**DEFAULT_MARKER_CAPTION_CSS, **(caption_style or {})}
        cluster = folium.plugins.MarkerCluster(name=name)

        for i, point in enumerate(points):
            pt = cast(Point, self._transform(point))
            self._extend_bounds(pt)
            lat, lon = pt.y, pt.x

            label = labels[i] if labels and i < len(labels) else None
            hover = hovers[i] if hovers and i < len(hovers) else None
            popup = popups[i] if popups and i < len(popups) else None
            txt = captions[i] if captions and i < len(captions) else None

            kind = classify_marker(label) if label else "icon_name"
            if kind == "emoji":
                assert label is not None  # guarded by classify_marker above
                icon = build_text_marker(label, css, txt, cap_css)
            else:
                icon_name = label or "arrow-down"
                icon = build_icon_marker(icon_name, css, txt, cap_css)

            folium.Marker(
                location=[lat, lon],
                icon=icon,
                tooltip=self._make_tooltip(hover),
                popup=self._make_popup(popup, popup_style),
            ).add_to(cluster)

        cluster.add_to(self._target())
        if min_zoom is not None and min_zoom > 0:
            self._zoom_controlled_markers.append(
                {
                    "var_name": cluster.get_name(),
                    "min_zoom": min_zoom,
                }
            )
        return self

    # ------------------------------------------------------------------
    # Text annotations
    # ------------------------------------------------------------------

    def add_text(
        self,
        point: tuple[float, float] | Point,
        text: str,
        style: dict[str, str] | None = None,
        hover: str | RawHTML | None = None,
        popup: str | RawHTML | None = None,
        popup_style: PopupStyle | dict[str, Any] | None = None,
        min_zoom: int | None = None,
    ) -> Self:
        """Add a text marker at a location.

        Parameters
        ----------
        point : tuple[float, float] | Point
            ``(lat, lon)`` tuple or Shapely Point ``(lon, lat)``.
        text : str
            Label text.
        style : dict[str, str] | None
            CSS property overrides.
        hover : str | RawHTML | None
            Markdown tooltip, or ``RawHTML`` for pre-formatted HTML.
        popup : str | RawHTML | None
            Markdown popup, or ``RawHTML`` for pre-formatted HTML.
        popup_style : PopupStyle | dict[str, Any] | None
            Popup dimensions.
        min_zoom : int | None
            Minimum zoom level at which the text is visible.

        Returns
        -------
        Map
        """
        merged = {**DEFAULT_CAPTION_CSS, "border-radius": "3px", "overflow-wrap": "break-word", **(style or {})}
        if isinstance(point, Point):
            loc = cast(Point, self._transform(point))
            lat, lon = loc.y, loc.x
            self._extend_bounds(loc)
        else:
            lat, lon = point
            self._bounds.append((lat, lon))

        css_str = css_to_style(merged)
        # Estimate icon size from text length and font size so the anchor
        # centers the marker on the coordinate and Leaflet doesn't render a
        # phantom shadow from a zero-sized container.
        fs = int(merged.get("font-size", "12px").replace("px", ""))
        est_w = max(len(text) * fs * 0.65 + 16, 20)
        est_h = fs + 12
        icon = folium.DivIcon(
            html=f'<div style="{css_str}">{text}</div>',
            icon_size="100%",  # type: ignore[arg-type]  # Let CSS control sizing
            icon_anchor=(int(est_w // 2), int(est_h // 2)),
            class_name="",
        )
        marker = folium.Marker(
            location=[lat, lon],
            icon=icon,
            tooltip=self._make_tooltip(hover),
            popup=self._make_popup(popup, popup_style),
        )
        marker.add_to(self._target())
        if min_zoom is not None and min_zoom > 0:
            self._zoom_controlled_markers.append(
                {
                    "var_name": marker.get_name(),
                    "min_zoom": min_zoom,
                }
            )
        return self

    # ------------------------------------------------------------------
    # GeoDataFrame integration
    # ------------------------------------------------------------------

    @classmethod
    def from_geodataframe(  # noqa: PLR0913, C901
        cls,
        gdf: Any,  # noqa: ANN401
        hover_columns: list[str] | None = None,
        popup_columns: list[str] | None = None,
        label_column: str | None = None,
        color_column: str | None = None,
        stroke: StrokeStyle | dict[str, Any] | None = None,
        fill: FillStyle | dict[str, Any] | None = None,
        marker_style: dict[str, str] | None = None,
        title: str | None = None,
        config: MapConfig | None = None,
        legend_name: str | None = None,
    ) -> Self:
        """Create a GeoMap from a GeoPandas GeoDataFrame.

        Parameters
        ----------
        gdf : geopandas.GeoDataFrame
            GeoDataFrame with a geometry column.
        hover_columns : list[str] | None
            Columns for tooltip.
        popup_columns : list[str] | None
            Columns for click popup.
        label_column : str | None
            Column with emoji/text labels for points.
        color_column : str | None
            Numeric column for choropleth coloring.
        stroke : StrokeStyle | None
            Default border style.
        fill : FillStyle | None
            Default fill style.
        marker_style : dict[str, str] | None
            CSS property overrides for location markers.
        title : str | None
            Map title.
        config : MapConfig | None
            Map configuration.
        legend_name : str | None
            Color scale marker.

        Returns
        -------
        Map

        Raises
        ------
        ImportError
            If geopandas is not installed.
        """
        try:
            import geopandas  # noqa: PLC0415, F401
        except ImportError:
            raise ImportError("from_geodataframe() requires geopandas. Install it with:\n  pip install geopandas") from None

        # Reproject to WGS84 if needed
        if gdf.crs and str(gdf.crs) != "EPSG:4326":
            gdf = gdf.to_crs("EPSG:4326")

        m = cls(title=title, config=config)

        # Build colormap
        colormap = None
        if color_column and color_column in gdf.columns:
            vals = gdf[color_column].dropna()
            if len(vals) > 0:
                vmin, vmax = float(vals.min()), float(vals.max())
                colormap = cm.LinearColormap(
                    colors=["#ffffb2", "#fecc5c", "#fd8d3c", "#f03b20", "#bd0026"],
                    vmin=vmin,
                    vmax=vmax,
                    caption=legend_name or color_column,
                )
                colormap.add_to(m._map)
                m._colormaps.append(colormap)

        # Iterate rows
        for idx, row in gdf.iterrows():
            geom = row.geometry

            if not isinstance(geom, BaseGeometry):
                continue

            if geom is None or geom.is_empty:
                continue

            # Build tooltip/popup text
            hover = None
            if hover_columns:
                parts = [f"**{c}**: {row[c]}" for c in hover_columns if c in row.index]
                hover = "\n".join(parts) if parts else None

            popup = None
            if popup_columns:
                parts = [f"**{c}**: {row[c]}" for c in popup_columns if c in row.index]
                popup = "\n".join(parts) if parts else None

            lbl = str(row[label_column]) if label_column and label_column in row.index else None

            # Resolve color
            cur_fill, cur_stroke = fill, stroke
            if colormap and color_column and color_column in row.index:
                val = row[color_column]
                if val is not None and not (isinstance(val, float) and math.isnan(val)):
                    c = colormap(float(val))
                    cur_fill = FillStyle(color=c, opacity=(fill or FillStyle()).opacity)
                    cur_stroke = StrokeStyle(
                        color=c,
                        weight=(stroke or StrokeStyle()).weight,
                        opacity=(stroke or StrokeStyle()).opacity,
                    )

            m.add_geometry(
                geom=geom,
                hover=hover,
                popup=popup,
                label=lbl,
                stroke=cur_stroke,
                fill=cur_fill,
                marker_style=marker_style,
            )

        return m

    # ------------------------------------------------------------------
    # Layer management
    # ------------------------------------------------------------------

    def add_layer_control(self, collapsed: bool = True, position: str = "topright") -> Self:
        """Add a layer control toggle.

        Parameters
        ----------
        collapsed : bool
            Start collapsed.
        position : str
            Control position.

        Returns
        -------
        Map
        """
        folium.LayerControl(collapsed=collapsed, position=position).add_to(self._map)
        return self

    def add_tile_layer(
        self,
        name: str,
        tiles: str | None = None,
        attribution: str | None = None,
        overlay: bool = False,
    ) -> Self:
        """Add an additional tile layer.

        Parameters
        ----------
        name : str
            Display name or ``TILE_PROVIDERS`` key.
        tiles : str | None
            Tile URL. Looks up ``name`` in providers if ``None``.
        attribution : str | None
            Tile attribution.
        overlay : bool
            Add as overlay vs base layer.

        Returns
        -------
        Map
        """
        provider = TILE_PROVIDERS.get(name.lower())
        display_name = name
        if provider and tiles is None:
            tiles = provider["tiles"]
            attribution = attribution or provider.get("attr")
            display_name = provider.get("name", name)
        folium.TileLayer(
            tiles=tiles or name,
            name=display_name,
            attr=attribution,
            overlay=overlay,
        ).add_to(self._map)
        return self

    # ------------------------------------------------------------------
    # Map combination
    # ------------------------------------------------------------------

    def __add__(self, other: Self) -> Self:
        """Merge two Maps into a new instance. Left map config/title is preserved.

        Parameters
        ----------
        other : Map
            Another map instance.

        Returns
        -------
        Map
            A new map combining both maps' features.
        """
        result = copy.deepcopy(self)
        for child in other._map._children.values():
            child.add_to(result._map)
        result._bounds.extend(other._bounds)
        result._feature_groups.update(other._feature_groups)
        result._colormaps.extend(other._colormaps)
        result._zoom_controlled_markers.extend(other._zoom_controlled_markers)
        return result

    # ------------------------------------------------------------------
    # Export methods
    # ------------------------------------------------------------------

    @property
    def folium_map(self) -> folium.Map:
        """Access the underlying Folium Map for advanced customization."""
        return self._map

    def _generate_zoom_javascript(self) -> str:
        """Generate JavaScript for zoom-dependent marker visibility.

        Returns
        -------
        str
            A ``<script>`` block that toggles marker visibility based on zoom.
        """
        marker_config = ", ".join(f'{{id: "{m["var_name"]}", minZoom: {m["min_zoom"]}}}' for m in self._zoom_controlled_markers)
        return (
            "<script>\n"
            "document.addEventListener('DOMContentLoaded', function() {\n"
            "    var checkInterval = setInterval(function() {\n"
            "        var mapContainer = document.querySelector('.folium-map');\n"
            "        if (mapContainer && mapContainer._leaflet_map) {\n"
            "            clearInterval(checkInterval);\n"
            "            var map = mapContainer._leaflet_map;\n"
            "            var configs = [" + marker_config + "];\n"
            "            function update() {\n"
            "                var z = map.getZoom();\n"
            "                configs.forEach(function(c) {\n"
            "                    var el = eval(c.id);\n"
            "                    if (z >= c.minZoom) { el.addTo(map); }\n"
            "                    else { map.removeLayer(el); }\n"
            "                });\n"
            "            }\n"
            "            map.on('zoomend', update);\n"
            "            update();\n"
            "        }\n"
            "    }, 100);\n"
            "});\n"
            "</script>"
        )

    def _ensure_rendered(self) -> None:
        """Fit bounds and inject zoom JS / draw plugin (idempotent)."""
        if not self._center:
            self._fit_bounds()
        if self._zoom_controlled_markers and not self._zoom_js_injected:
            self._map.get_root().html.add_child(folium.Element(self._generate_zoom_javascript()))  # type: ignore[union-attr]
            self._zoom_js_injected = True
        if self._draw_config and not self._draw_injected:
            self._inject_draw_plugin()

    def _get_html(self) -> str:
        """Render map to an embeddable HTML string (Jupyter/inline)."""
        self._ensure_rendered()
        return self._map._repr_html_()

    def _get_standalone_html(self) -> str:
        """Render map to a full standalone HTML document."""
        self._ensure_rendered()
        return self._map.get_root().render()

    def to_html(self, path: str | Path | None = None, open_in_browser: bool = False) -> str | Path:
        """Export as standalone HTML.

        Parameters
        ----------
        path : str | Path | None
            Output file path.  When ``None``, the full HTML document is
            returned as a string instead of being written to disk.
        open_in_browser : bool
            If ``True`` and *path* is given, open the file in the default
            browser after saving.  Ignored when *path* is ``None``.

        Returns
        -------
        str | Path
            HTML string when *path* is ``None``, otherwise the resolved
            output :class:`~pathlib.Path`.
        """
        if path is None:
            return self._get_html()
        out = Path(path)
        out.write_text(self._get_standalone_html(), encoding="utf-8")
        if open_in_browser:
            webbrowser.open(out.resolve().as_uri())
        return out

    def to_image(
        self,
        path: str | Path | None = None,
        width: int = 1200,
        height: int = 800,
        delay: float = 0.50,
        hide_controls: bool = True,
    ) -> bytes | Path:
        """Save the map as a PNG image.

        Parameters
        ----------
        path : str | Path | None
            Output path. Returns bytes if ``None``.
        width : int
            Viewport width in px.
        height : int
            Viewport height in px.
        delay : float
            Seconds to wait for tiles.
        hide_controls : bool
            If ``True``, inject CSS to hide Leaflet UI controls in the
            exported image.

        Returns
        -------
        bytes | Path

        Raises
        ------
        ImportError
            If selenium not installed.
        RuntimeError
            If Chrome/chromedriver not found.
        """
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
            self.to_html(tmp.name)
            tmp_path = tmp.name
        try:
            if hide_controls:
                content = Path(tmp_path).read_text(encoding="utf-8")
                hide_css = "<style>.leaflet-control{display:none !important;}</style>"
                content = content.replace("</head>", f"{hide_css}\n</head>", 1)
                Path(tmp_path).write_text(content, encoding="utf-8")
            png_bytes = capture_screenshot(
                html_path=tmp_path,
                width=width,
                height=height,
                delay=delay,
            )
        finally:
            Path(tmp_path).unlink(missing_ok=True)

        if path is None:
            return png_bytes
        out = Path(path)
        out.write_bytes(png_bytes)
        return out

    def to_bytesio(
        self,
        width: int = 1200,
        height: int = 800,
        delay: float = 2.0,
        hide_controls: bool = True,
    ) -> io.BytesIO:
        """Export as PNG in a BytesIO buffer.

        Parameters
        ----------
        width : int
            Viewport width.
        height : int
            Viewport height.
        delay : float
            Tile loading wait time.
        hide_controls : bool
            If ``True``, hide Leaflet UI controls.

        Returns
        -------
        io.BytesIO
            Buffer at position 0.
        """
        png = cast(bytes, self.to_image(path=None, width=width, height=height, delay=delay, hide_controls=hide_controls))
        buf = io.BytesIO(png)
        buf.seek(0)
        return buf

    def to_svg(
        self,
        path: str | Path | None = None,
        width: int = 1200,
        height: int = 800,
        delay: float = 2.0,
        hide_controls: bool = True,
    ) -> str | Path:
        """Export as SVG with an embedded raster image.

        This captures a PNG screenshot and wraps it in an SVG container.
        The result is **not** a true vector SVG — text and shapes are
        rasterized.  This approach is used because Leaflet renders to
        an HTML canvas, which cannot be serialized to vector paths.

        For a true vector workflow, export to HTML and use a dedicated
        tool to convert the map to vector format.

        Parameters
        ----------
        path : str | Path | None
            Output path. Returns SVG string if ``None``.
        width, height : int
            Viewport dimensions.
        delay : float
            Tile loading wait time.
        hide_controls : bool
            If ``True``, hide Leaflet UI controls.

        Returns
        -------
        str | Path
        """
        png_bytes = cast(bytes, self.to_image(path=None, width=width, height=height, delay=delay, hide_controls=hide_controls))
        b64 = base64.b64encode(png_bytes).decode("ascii")
        svg = (
            f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{width}" height="{height}" viewBox="0 0 {width} {height}">\n'
            f'  <image width="{width}" height="{height}" '
            f'xlink:href="data:image/png;base64,{b64}"/>\n'
            f"</svg>"
        )
        if path is None:
            return svg
        out = Path(path)
        out.write_text(svg, encoding="utf-8")
        return out

    async def to_image_async(
        self,
        path: str | Path | None = None,
        width: int = 1200,
        height: int = 800,
        delay: float = 2.0,
        hide_controls: bool = True,
    ) -> bytes | Path:
        """Async PNG export (runs Selenium in executor).

        Parameters
        ----------
        path, width, height, delay
            See ``to_image``.
        hide_controls : bool
            If ``True``, hide Leaflet UI controls.

        Returns
        -------
        bytes | Path
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.to_image(
                path=path,
                width=width,
                height=height,
                delay=delay,
                hide_controls=hide_controls,
            ),
        )

    async def to_svg_async(
        self,
        path: str | Path | None = None,
        width: int = 1200,
        height: int = 800,
        delay: float = 2.0,
        hide_controls: bool = True,
    ) -> str | Path:
        """Async SVG export.

        Parameters
        ----------
        path, width, height, delay
            See ``to_svg``.
        hide_controls : bool
            If ``True``, hide Leaflet UI controls.

        Returns
        -------
        str | Path
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.to_svg(
                path=path,
                width=width,
                height=height,
                delay=delay,
                hide_controls=hide_controls,
            ),
        )

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        """String representation."""
        n = len(self._bounds) // 2
        groups = list(self._feature_groups.keys())
        return f"Map(title={self._title!r}, geometries~{n}, feature_groups={groups})"

    def _repr_html_(self) -> str:
        """Jupyter notebook display."""
        return self._get_html()
