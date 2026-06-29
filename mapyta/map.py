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
import copy
import io
import json
import math
import tempfile
import uuid
import warnings
import webbrowser
from collections.abc import Mapping
from html import escape as html_escape
from pathlib import Path
from typing import Any, Self, cast, overload

import branca.colormap as cm
import folium
import folium.features
import folium.plugins
from branca.element import MacroElement
from folium.template import Template
from shapely.geometry import (
    LinearRing,
    LineString,
    MultiLineString,
    MultiPoint,
    MultiPolygon,
    Point,
    Polygon,
)
from shapely.geometry import (
    mapping as geom_to_geojson,
)
from shapely.geometry.base import BaseGeometry

from mapyta.config import CircleStyle, DrawConfig, DrawTool, FillStyle, HeatmapStyle, MapConfig, PopupStyle, RawJS, StrokeStyle, TooltipStyle
from mapyta.coordinates import transform_geometry
from mapyta.export import capture_screenshot
from mapyta.geojson import load_geojson_input
from mapyta.markdown import RawHTML, markdown_to_html
from mapyta.markers import (
    DEFAULT_CAPTION_CSS,
    DEFAULT_MARKER_CAPTION_CSS,
    build_icon_marker,
    build_text_marker,
    classify_marker,
    css_to_style,
    px_to_int,
)
from mapyta.mouse_position import MousePositionProjected
from mapyta.style import PALETTES, resolve_style
from mapyta.tiles import TILE_PROVIDERS

LEAFLET_DRAW_CSS = "https://cdnjs.cloudflare.com/ajax/libs/leaflet.draw/1.0.4/leaflet.draw.css"
LEAFLET_DRAW_JS = "https://cdnjs.cloudflare.com/ajax/libs/leaflet.draw/1.0.4/leaflet.draw.js"
VALID_DRAW_TOOLS = frozenset({"marker", "polyline", "polygon", "rectangle", "circle"})

# Normalise the size of every corner control button. Leaflet renders the layer
# and measure toggles at 36px (44px on touch), while the zoom, draw, home and
# fullscreen buttons sit at 26px (30px on touch). Shrink the two odd ones out so
# every control button matches. ``!important`` is required because the plugin
# rules ship from CDNs at equal-or-higher specificity.
#
# The measure plugin's toggle is also styled differently: it paints a multi-icon
# sprite (``rulers.png``) that, once force-scaled to 16px, collapses into a dark
# block. Swap in a clean single line-art ruler on a white background so it matches
# the zoom/draw/home/fullscreen icons.
_MEASURE_TOGGLE_ICON = (
    'url("data:image/svg+xml,'
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' "
    "stroke='%23333' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>"
    "<rect x='2' y='7' width='20' height='10' rx='1'/>"
    "<path d='M7 7v4M12 7v5M17 7v4'/></svg>\")"
)
CONTROL_SIZE_CSS = (
    "<style>"
    ".leaflet-control-layers-toggle,"
    ".leaflet-control-measure .leaflet-control-measure-toggle{"
    "width:26px!important;height:26px!important;background-size:16px 16px!important;}"
    ".leaflet-touch .leaflet-control-layers-toggle,"
    ".leaflet-touch .leaflet-control-measure .leaflet-control-measure-toggle{"
    "width:30px!important;height:30px!important;background-size:18px 18px!important;}"
    ".leaflet-control-measure .leaflet-control-measure-toggle{"
    f"background-color:#fff!important;background-image:{_MEASURE_TOGGLE_ICON}!important;}}"
    # Box parity with the layers control (``.leaflet-control-layers``), which has the same
    # shape (an icon toggle in a rounded container) and which renders correctly. Mirror its
    # shadow/radius and, crucially, its touch styling: drop the shadow and use the crisp 2px
    # grey border, otherwise the measure box keeps a faint shadow halo instead of a sharp
    # border like the other controls.
    ".leaflet-control-measure{box-shadow:0 1px 5px rgba(0,0,0,0.4)!important;border-radius:5px!important;background:#fff!important;}"
    ".leaflet-control-measure .leaflet-control-measure-toggle{border-radius:5px!important;}"
    ".leaflet-touch .leaflet-control-measure{box-shadow:none!important;border:2px solid rgba(0,0,0,0.2)!important;"
    "background-clip:padding-box!important;}"
    "</style>"
)


class _HomeButtonControl(MacroElement):
    """A reset-view button rendered in the map's main script block.

    Unlike a post-construction injected ``<script>``, this control's
    ``addTo`` runs inline with Folium's map setup. Adding it to the map
    *before* the other plugin controls means Leaflet stacks it on top of
    its corner (e.g. above the measure control), with no DOM reordering.

    The opening view is captured on ``DOMContentLoaded`` — after Folium's
    synchronous ``fitBounds`` / ``setView`` has run — and stashed on the map
    as ``_mapytaHome``, so a single button restores the correct view whether
    it came from an explicit ``center`` or from auto-fitted data bounds.
    """

    _template = Template(
        "{% macro script(this, kwargs) %}\n"
        "    var {{ this.get_name() }} = L.control({position: {{ this.position|tojson }}});\n"
        "    {{ this.get_name() }}.onAdd = function() {\n"
        "        var div = L.DomUtil.create('div', 'leaflet-bar');\n"
        "        var btn = L.DomUtil.create('a', '', div);\n"
        "        btn.href = '#';\n"
        "        btn.title = {{ this.title|tojson }};\n"
        "        btn.innerHTML = '\\u2302';\n"
        "        btn.style.cssText = 'font-size:18px;text-align:center;line-height:26px;cursor:pointer;';\n"
        "        btn.onclick = function(e) {\n"
        "            e.preventDefault();\n"
        "            e.stopPropagation();\n"
        "            var home = {{ this._parent.get_name() }}._mapytaHome;\n"
        "            if (home) { {{ this._parent.get_name() }}.setView(home.center, home.zoom); }\n"
        "        };\n"
        "        L.DomEvent.disableClickPropagation(div);\n"
        "        return div;\n"
        "    };\n"
        "    {{ this.get_name() }}.addTo({{ this._parent.get_name() }});\n"
        "    document.addEventListener('DOMContentLoaded', function() {\n"
        "        {{ this._parent.get_name() }}._mapytaHome = {\n"
        "            center: {{ this._parent.get_name() }}.getCenter(),\n"
        "            zoom: {{ this._parent.get_name() }}.getZoom()\n"
        "        };\n"
        "    });\n"
        "{% endmacro %}"
    )

    def __init__(self, position: str = "topright", title: str = "Reset view") -> None:
        super().__init__()
        self._name = "HomeButtonControl"
        self.position = position
        self.title = title


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
        self._colormaps: list[cm.LinearColormap | cm.StepColormap] = []
        self._zoom_controlled_markers: list[dict[str, Any]] = []
        self._zoom_controlled_captions: list[dict[str, Any]] = []
        self._zoom_js_injected: bool = False
        self._draw_config: DrawConfig | None = None
        self._draw_injected: bool = False
        self._geojson_features: list[dict] = []
        self._export_button_config: dict[str, Any] | None = None
        self._export_button_injected: bool = False
        self._layer_dropdown_config: dict[str, Any] | None = None
        self._layer_dropdown_injected: bool = False

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

        max_native_zoom = cfg.max_native_zoom if cfg.max_native_zoom is not None else cfg.max_zoom

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
                        max_zoom=cfg.max_zoom,
                        max_native_zoom=max_native_zoom,
                        show=i == 0,
                    ).add_to(fmap)
                else:
                    folium.TileLayer(
                        tiles=layer_key,
                        name=layer_key,
                        attr=cfg.attribution,
                        max_zoom=cfg.max_zoom,
                        max_native_zoom=max_native_zoom,
                        show=i == 0,
                    ).add_to(fmap)
        else:
            # Single layer: build the map without tiles, then add a TileLayer
            # explicitly so max_native_zoom can be set (folium.Map(tiles=...)
            # does not expose it).
            provider = TILE_PROVIDERS.get(layers[0].lower())
            if provider:
                tiles = provider["tiles"]
                attr = provider.get("attr")
                name = provider.get("name", layers[0])
            else:
                tiles = layers[0]
                attr = cfg.attribution
                name = layers[0]

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
            folium.TileLayer(
                tiles=tiles,
                name=name,
                attr=attr,
                max_zoom=cfg.max_zoom,
                max_native_zoom=max_native_zoom,
            ).add_to(fmap)

        fmap.get_root().header.add_child(folium.Element('<meta name="referrer" content="origin">'))  # ty: ignore[unresolved-attribute]
        fmap.get_root().header.add_child(folium.Element(CONTROL_SIZE_CSS))  # ty: ignore[unresolved-attribute]

        # Title overlay
        if self._title:
            title_html = (
                '<div style="position:fixed;top:10px;left:50%;transform:translateX(-50%);'
                "z-index:1000;background:rgba(255,255,255,0.9);padding:8px 20px;"
                "border-radius:6px;font-family:Arial,sans-serif;font-size:16px;"
                f'font-weight:bold;box-shadow:0 2px 6px rgba(0,0,0,0.3);pointer-events:none;">'
                f"{self._title}</div>"
            )
            fmap.get_root().html.add_child(folium.Element(title_html))  # ty: ignore[unresolved-attribute]

        # Optional plugins
        # Added first so its control sits at the top of its corner — Leaflet stacks
        # same-corner controls in add order, so this lands above the measure control.
        if cfg.home_button:
            _HomeButtonControl(position="topright", title="Reset view").add_to(fmap)
        if cfg.fullscreen:
            folium.plugins.Fullscreen().add_to(fmap)
        if cfg.minimap:
            folium.plugins.MiniMap(toggle_display=True).add_to(fmap)
        if cfg.measure_control:
            folium.plugins.MeasureControl(primary_length_unit="meters", primary_area_unit="sqmeters").add_to(fmap)
        if cfg.mouse_position:
            if cfg.mouse_position_crs:
                MousePositionProjected(crs=cfg.mouse_position_crs, position="bottomleft").add_to(fmap)
            else:
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
        iframe = folium.IFrame(html, width=ps.width, height=ps.height)  # ty: ignore[invalid-argument-type]
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
        tools: list[DrawTool] | None = None,
        on_submit: str | RawJS | None = None,
        position: str = "topleft",
        submit_label: str = "Submit",
        draw_style: dict[str, Any] | None = None,
        edit: bool = True,
        delete_confirm_message: str = "Delete this shape?",
        delete_confirm_yes: str = "Delete",
        delete_confirm_no: str = "Cancel",
    ) -> Self:
        """Enable drawing controls on the map.

        Parameters
        ----------
        tools : list[DrawTool] | None
            Active drawing tools.  Valid values: ``"marker"``,
            ``"polyline"``, ``"polygon"``, ``"rectangle"``, ``"circle"``.
            Defaults to ``["polyline", "polygon", "marker"]``.
        on_submit : str | RawJS | None
            Callback when the user clicks Submit.  ``None`` downloads a
            GeoJSON file; a URL string sends a ``POST`` request; a plain
            string calls ``window["name"](geojson)``; a :class:`RawJS`
            instance is inlined verbatim.
        position : str
            Leaflet control position.
        submit_label : str
            Label for the submit button.
        draw_style : dict[str, Any] | None
            ``shapeOptions`` override for drawn shapes.
        edit : bool
            Whether per-shape editing/deletion is active. When ``True``,
            clicking a drawn shape makes its vertices editable in place (click
            empty map space to stop editing) and shows a trashbin at its last
            vertex; clicking the trashbin and confirming deletes that shape.
            No global edit/delete toolbar buttons are rendered. When ``False``,
            clicking a shape stays inert.
        delete_confirm_message : str
            Text shown in the in-map deletion confirmation popup.
        delete_confirm_yes : str
            Label of the confirm (delete) button in that popup.
        delete_confirm_no : str
            Label of the cancel button in that popup.

        Returns
        -------
        Map

        Raises
        ------
        ValueError
            If *tools* contains an invalid tool name.
        """
        if tools is None:
            tools = ["polyline", "polygon", "marker"]

        invalid = set(tools) - VALID_DRAW_TOOLS
        if invalid:
            msg = f"Invalid draw tool(s): {', '.join(sorted(invalid))}. Valid: {', '.join(sorted(VALID_DRAW_TOOLS))}"
            raise ValueError(msg)

        self._draw_config = DrawConfig(
            tools=tools,
            on_submit=on_submit,
            position=position,
            submit_label=submit_label,
            draw_style=draw_style,
            edit=edit,
            delete_confirm_message=delete_confirm_message,
            delete_confirm_yes=delete_confirm_yes,
            delete_confirm_no=delete_confirm_no,
        )
        self._draw_injected = False
        return self

    def _inject_draw_plugin(self) -> None:
        """Inject Leaflet.draw CSS, JS, and control script (idempotent)."""
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

        # Disable both edit-toolbar modes explicitly. Leaflet.draw's EditToolbar
        # prototype defaults ``edit`` to a truthy object, so omitting the key would
        # still render the pencil button — only an explicit ``false`` shadows it.
        # With both modes off, ``L.Toolbar.addToolbar`` early-returns (no buttons),
        # so no edit/delete toolbar appears. folium still wires
        # ``options.edit.featureGroup = drawnItems`` and adds drawn shapes via
        # ``draw:created``, so click-to-edit (and the per-shape trashbin) stays
        # intact. Per-shape editing/deletion replaces the global toolbar buttons.
        edit_options: dict[str, Any] = {"edit": False, "remove": False}

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

        # Submit button: runs after DOMContentLoaded (after Folium's <script> block).
        map_var = self._map.get_name()
        drawn_items_var = f"drawnItems_{draw_plugin.get_name()}"
        self._map.get_root().html.add_child(  # ty: ignore[unresolved-attribute]
            folium.Element(self._build_draw_script(map_var, drawn_items_var))
        )
        self._draw_injected = True

    def _build_draw_script(self, map_var: str, drawn_items_var: str) -> str:
        """Build the submit button ``<script>`` block.

        Uses ``DOMContentLoaded`` so both Folium variables (``map_var`` and
        ``drawn_items_var``) are guaranteed to be defined, Folium's ``<script>``
        block runs synchronously before that event fires.
        """
        cfg = self._draw_config
        assert cfg is not None

        callback_js = self._build_draw_callback_js()
        click_edit_js = self._build_click_to_edit_js() if cfg.edit else ""

        return (
            "<script>\n"
            "document.addEventListener('DOMContentLoaded', function() {\n"
            f"    var map = window['{map_var}'];\n"
            f"    var drawnItems = window['{drawn_items_var}'];\n"
            "    if (!map || !drawnItems) return;\n"
            "\n"
            f"{click_edit_js}"
            "    var submitControl = L.control({position: 'bottomright'});\n"
            "    submitControl.onAdd = function() {\n"
            "        var div = L.DomUtil.create('div', 'leaflet-bar');\n"
            "        var btn = L.DomUtil.create('a', '', div);\n"
            "        btn.href = '#';\n"
            f"        btn.innerHTML = '{cfg.submit_label}';\n"
            "        btn.style.cssText = 'display:block;padding:5px 12px;background:#1e90ff;color:#fff;' +\n"
            "            'text-decoration:none;font-weight:bold;font-size:13px;cursor:pointer;' +\n"
            "            'width:auto;height:auto;line-height:normal;white-space:nowrap;';\n"
            "        btn.onclick = function(e) {\n"
            "            e.preventDefault();\n"
            "            e.stopPropagation();\n"
            "            var geojson = drawnItems.toGeoJSON();\n"
            f"            {callback_js}\n"
            "        };\n"
            "        L.DomEvent.disableClickPropagation(div);\n"
            "        return div;\n"
            "    };\n"
            "    submitControl.addTo(map);\n"
            "});\n"
            "</script>"
        )

    def _build_click_to_edit_js(self) -> str:
        """Build the click-to-edit + per-shape trashbin ``<script>`` fragment.

        Leaflet.draw only exposes vertex editing through the toolbar pencil,
        which toggles *every* shape at once and needs an explicit Save, and
        deletion through a global trashcan button. mapyta hides both (see
        ``_inject_draw_plugin``) in favour of per-shape, in-place interaction:

        - **Edit:** drawn shapes are interactive (the cursor turns into a
          pointer on hover), so users reasonably expect clicking one to edit
          it. ``ddEnableClickEdit`` binds a per-layer ``click`` handler that
          calls the layer's Leaflet.draw ``editing.enable()`` so a single shape
          becomes editable in place (drag vertices, add midpoints); clicking
          empty map space disables editing again. It is wired to every layer
          already in ``drawnItems`` and, via ``layeradd``, to any added later —
          whether drawn by the user or pre-seeded programmatically.
        - **Delete:** while a shape is being edited, ``ddAddTrash`` drops a small
          trashbin marker at its last vertex. Clicking it opens an in-map
          Leaflet popup (``ddConfirmDelete``) with Delete/Cancel buttons;
          confirming calls ``ddDeleteLine`` which removes that single shape. A
          DOM popup is used rather than ``window.confirm()`` because the latter
          is silently dropped inside sandboxed iframe embeds. As a shortcut,
          pressing the keyboard **Delete** key removes the shape currently being
          edited immediately, without the confirmation popup (ignored while a
          form field is focused).

        Only emitted when ``edit`` is enabled; if the caller turned edit
        controls off, clicking a shape stays inert and no trashbin appears.

        Leaflet.draw's vertex-edit ``addHooks`` reads ``layer.options.editing``
        and ``layer.options.original`` unconditionally; its own edit toolbar
        seeds both in ``_enableLayerEdit`` before calling ``editing.enable()``.
        We enable editing directly (bypassing that toolbar), so we must seed
        them ourselves — otherwise ``addHooks`` throws
        ``Cannot read properties of undefined (reading 'className')`` on the SVG
        renderer and no vertex handles appear. Seeded in the same order
        Leaflet.draw uses (``original`` snapshots the live style first).

        User-facing strings (the confirm message and button labels) are encoded
        with :func:`json.dumps` so they become safe JS string literals.
        """
        cfg = self._draw_config
        assert cfg is not None

        # Inline SVG trash glyph (no font dependency), inside a white rounded
        # badge for contrast against any basemap. json.dumps turns the whole
        # markup into a safe JS string literal for L.divIcon's ``html`` option.
        trash_html = (
            '<div style="background:#fff;border:1px solid #ccc;border-radius:4px;'
            "width:22px;height:22px;display:flex;align-items:center;justify-content:center;"
            'box-shadow:0 1px 4px rgba(0,0,0,0.3);color:#d11;cursor:pointer;">'
            "<svg xmlns='http://www.w3.org/2000/svg' width='14' height='14' viewBox='0 0 24 24' "
            "fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' "
            "stroke-linejoin='round'><polyline points='3 6 5 6 21 6'></polyline>"
            "<path d='M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2'></path>"
            "<line x1='10' y1='11' x2='10' y2='17'></line>"
            "<line x1='14' y1='11' x2='14' y2='17'></line></svg></div>"
        )
        trash_html_js = json.dumps(trash_html)
        confirm_msg_js = json.dumps(cfg.delete_confirm_message)
        confirm_yes_js = json.dumps(cfg.delete_confirm_yes)
        confirm_no_js = json.dumps(cfg.delete_confirm_no)

        return (
            f"    var ddTrashHtml = {trash_html_js};\n"
            f"    var ddDeleteMsg = {confirm_msg_js};\n"
            f"    var ddDeleteYes = {confirm_yes_js};\n"
            f"    var ddDeleteNo = {confirm_no_js};\n"
            # Most recently focused (clicked-to-edit) layer; target of the
            # keyboard Delete shortcut. Cleared when editing stops or it is
            # deleted.
            "    var ddActiveLayer = null;\n"
            # Last vertex of a shape, or null for layers we don't support
            # (markers have no getLatLngs; polygons/rectangles nest one ring).
            "    function ddLastVertex(layer) {\n"
            "        if (!layer.getLatLngs) return null;\n"
            "        var lls = layer.getLatLngs();\n"
            "        if (!lls || !lls.length) return null;\n"
            "        var last = lls[lls.length - 1];\n"
            "        if (Array.isArray(last)) {\n"
            "            if (!last.length) return null;\n"
            "            last = last[last.length - 1];\n"
            "        }\n"
            "        if (!last || typeof last.lat !== 'number') return null;\n"
            "        return last;\n"
            "    }\n"
            "    function ddRemoveTrash(layer) {\n"
            "        if (layer._ddTrash) { map.removeLayer(layer._ddTrash); layer._ddTrash = null; }\n"
            "    }\n"
            "    function ddAddTrash(layer) {\n"
            "        if (layer._ddTrash) return;\n"
            "        var last = ddLastVertex(layer);\n"
            "        if (!last) return;\n"
            "        var trash = L.marker(last, {\n"
            "            icon: L.divIcon({className: 'dd-trash-icon', html: ddTrashHtml, iconSize: [22, 22], iconAnchor: [-6, 28]}),\n"
            "            interactive: true, keyboard: false, zIndexOffset: 1000\n"
            "        }).addTo(map);\n"
            "        layer._ddTrash = trash;\n"
            "        trash.on('click', function(e) {\n"
            "            L.DomEvent.stopPropagation(e);\n"
            "            ddConfirmDelete(layer, trash.getLatLng());\n"
            "        });\n"
            # Keep the trashbin pinned to the last vertex while it moves. The
            # layer fires 'edit' on each vertex drag-end (PolyVerticesEdit
            # ._fireEdit); 'editdrag' is bound too in case the build re-fires it.
            # Bind once per layer: ddAddTrash runs again on every re-edit and
            # this handler outlives the trash marker (it null-checks
            # layer._ddTrash), so re-binding would stack duplicate listeners.
            "        if (!layer._ddPinBound) {\n"
            "            layer._ddPinBound = true;\n"
            "            layer.on('edit editdrag', function() {\n"
            "                var nl = ddLastVertex(layer);\n"
            "                if (nl && layer._ddTrash) { layer._ddTrash.setLatLng(nl); }\n"
            "            });\n"
            "        }\n"
            "    }\n"
            "    function ddConfirmDelete(layer, latlng) {\n"
            "        var box = L.DomUtil.create('div', 'dd-delete-confirm');\n"
            "        var msg = L.DomUtil.create('div', '', box);\n"
            "        msg.innerHTML = ddDeleteMsg;\n"
            "        msg.style.cssText = 'margin-bottom:8px;font-size:13px;';\n"
            "        var del = L.DomUtil.create('a', '', box);\n"
            "        del.href = '#'; del.innerHTML = ddDeleteYes;\n"
            "        del.style.cssText = 'display:inline-block;padding:4px 10px;margin-right:6px;background:#d11;' +\n"
            "            'color:#fff;text-decoration:none;font-weight:bold;font-size:12px;border-radius:3px;cursor:pointer;';\n"
            "        var cancel = L.DomUtil.create('a', '', box);\n"
            "        cancel.href = '#'; cancel.innerHTML = ddDeleteNo;\n"
            "        cancel.style.cssText = 'display:inline-block;padding:4px 10px;background:#eee;color:#333;' +\n"
            "            'text-decoration:none;font-size:12px;border-radius:3px;cursor:pointer;';\n"
            "        L.DomEvent.disableClickPropagation(box);\n"
            "        del.onclick = function(e) { e.preventDefault(); ddDeleteLine(layer); map.closePopup(); };\n"
            "        cancel.onclick = function(e) { e.preventDefault(); map.closePopup(); };\n"
            "        L.popup({closeButton: false, className: 'dd-delete-confirm'}).setLatLng(latlng).setContent(box).openOn(map);\n"
            "    }\n"
            "    function ddDeleteLine(layer) {\n"
            "        if (layer.editing && layer.editing.enabled()) { layer.editing.disable(); }\n"
            "        ddRemoveTrash(layer);\n"
            "        drawnItems.removeLayer(layer);\n"
            "        if (ddActiveLayer === layer) { ddActiveLayer = null; }\n"
            "    }\n"
            "    function ddEnableClickEdit(layer) {\n"
            "        if (!layer || !layer.editing) return;\n"
            "        layer.on('click', function(e) {\n"
            "            L.DomEvent.stopPropagation(e);\n"
            "            if (!layer.editing.enabled()) {\n"
            "                if (layer.options) {\n"
            "                    if (!layer.options.original) { layer.options.original = L.extend({}, layer.options); }\n"
            "                    if (!layer.options.editing) { layer.options.editing = {}; }\n"
            "                }\n"
            "                layer.editing.enable();\n"
            "                ddAddTrash(layer);\n"
            "            }\n"
            "            ddActiveLayer = layer;\n"
            "        });\n"
            "    }\n"
            "    drawnItems.eachLayer(ddEnableClickEdit);\n"
            "    drawnItems.on('layeradd', function(e) { ddEnableClickEdit(e.layer); });\n"
            "    map.on('click', function() {\n"
            "        drawnItems.eachLayer(function(layer) {\n"
            "            if (layer.editing && layer.editing.enabled()) {\n"
            "                layer.editing.disable();\n"
            "                ddRemoveTrash(layer);\n"
            "            }\n"
            "        });\n"
            "        ddActiveLayer = null;\n"
            "    });\n"
            # Keyboard shortcut: pressing Delete while a shape is being edited
            # removes it immediately, bypassing the trashbin's confirmation
            # popup. Ignored while typing in a form field. Other interactions
            # (click-to-edit, trashbin + confirm) are unaffected.
            "    document.addEventListener('keydown', function(e) {\n"
            "        if (e.key !== 'Delete') return;\n"
            "        var t = e.target;\n"
            "        if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return;\n"
            "        if (ddActiveLayer && ddActiveLayer.editing && ddActiveLayer.editing.enabled()) {\n"
            "            ddDeleteLine(ddActiveLayer);\n"
            "        }\n"
            "    });\n"
            "\n"
        )

    def _build_draw_callback_js(self) -> str:
        """Build the JavaScript callback for the submit button."""
        cfg = self._draw_config
        assert cfg is not None

        # Priority 1: RawJS
        if isinstance(cfg.on_submit, RawJS):
            return f"({cfg.on_submit.js})(geojson);"

        # Priority 3: URL (fetch)
        if isinstance(cfg.on_submit, str) and cfg.on_submit.startswith("http"):
            return f"fetch(\"{cfg.on_submit}\", {{method: 'POST', body: JSON.stringify(geojson)}});"

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

    # ------------------------------------------------------------------
    # GeoJSON feature tracking
    # ------------------------------------------------------------------

    @staticmethod
    def _raw_text(val: str | RawHTML | None) -> str | None:
        """Extract plain text from a tooltip/popup value (RawHTML is a str subclass)."""
        if val is None:
            return None
        return str(val)

    def _record_feature(self, geom: BaseGeometry, props: dict[str, Any]) -> None:
        """Append a GeoJSON Feature to the internal tracking list."""
        self._geojson_features.append(
            {
                "type": "Feature",
                "geometry": dict(geom_to_geojson(geom)),
                "properties": {k: v for k, v in props.items() if v is not None},
            }
        )

    def _build_geojson_collection(self) -> dict:
        """Return a GeoJSON FeatureCollection of all tracked features."""
        return {"type": "FeatureCollection", "features": self._geojson_features}

    # ------------------------------------------------------------------
    # Adding geometries
    # ------------------------------------------------------------------

    def add_point(  # noqa: PLR0913
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
        min_zoom_caption: int | None = None,
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
        min_zoom_caption : int | None
            Minimum zoom level at which the caption is visible. Works like
            ``min_zoom`` but applies only to the caption text — the marker
            icon itself remains visible. ``None`` or ``0`` means always
            visible. Ignored when ``caption`` is not set. Note: caption
            visibility is also bounded below by ``min_zoom`` — the caption
            lives inside the marker's DivIcon DOM, which is removed when
            the marker is hidden, so setting ``min_zoom_caption`` lower
            than ``min_zoom`` does not reveal the caption at those zooms.

        Returns
        -------
        Map
        """
        point = cast(Point, self._transform(point))
        self._extend_bounds(point)
        lat, lon = point.y, point.x

        css = marker_style or {}
        cap_css = {**DEFAULT_MARKER_CAPTION_CSS, **(caption_style or {})}

        caption_id: str | None = None
        if caption is not None and min_zoom_caption is not None and min_zoom_caption > 0:
            caption_id = f"caption_{uuid.uuid4().hex[:15]}"

        kind = classify_marker(marker) if marker else "icon_name"
        if kind == "emoji":
            assert marker is not None  # guarded by classify_marker above
            icon = build_text_marker(marker, css, caption, cap_css, caption_id)
        else:
            icon_name = marker or "arrow-down"
            icon = build_icon_marker(icon_name, css, caption, cap_css, caption_id)

        m = folium.Marker(
            location=[lat, lon],
            icon=icon,
            tooltip=self._make_tooltip(tooltip, tooltip_style),
            popup=self._make_popup(popup, popup_style),
        )
        m.add_to(self._target())
        self._record_feature(
            point,
            {
                "marker": marker,
                "caption": caption,
                "tooltip": self._raw_text(tooltip),
                "popup": self._raw_text(popup),
                "min_zoom": min_zoom,
                "min_zoom_caption": min_zoom_caption,
            },
        )

        if min_zoom is not None and min_zoom > 0:
            self._zoom_controlled_markers.append(
                {
                    "var_name": m.get_name(),
                    "min_zoom": min_zoom,
                }
            )

        if caption_id is not None:
            assert min_zoom_caption is not None  # guarded above
            self._zoom_controlled_captions.append(
                {
                    "caption_id": caption_id,
                    "min_zoom": min_zoom_caption,
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
        tooltip_style: TooltipStyle | dict[str, Any] | None = None,
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
        tooltip_style : TooltipStyle | dict[str, Any] | None
            Tooltip appearance.

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
            tooltip=self._make_tooltip(tooltip, tooltip_style),
            popup=self._make_popup(popup, popup_style),
            dash_array=cs.stroke.dash_array,
        )
        marker.add_to(self._target())
        self._record_feature(
            point,
            {
                "radius": cs.radius,
                "stroke_color": cs.stroke.color,
                "stroke_weight": cs.stroke.weight,
                "stroke_opacity": cs.stroke.opacity,
                "stroke_dash_array": cs.stroke.dash_array,
                "fill_color": cs.fill.color,
                "fill_opacity": cs.fill.opacity,
                "tooltip": self._raw_text(tooltip),
                "popup": self._raw_text(popup),
                "min_zoom": min_zoom,
            },
        )
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
        min_zoom: int | None = None,
        tooltip_style: TooltipStyle | dict[str, Any] | None = None,
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
        min_zoom : int | None
            Minimum zoom level at which the line is visible.
        tooltip_style : TooltipStyle | dict[str, Any] | None
            Tooltip appearance.

        Returns
        -------
        Map
        """
        line = cast(LineString, self._transform(line))
        self._extend_bounds(line)
        s = resolve_style(stroke, StrokeStyle) or StrokeStyle()
        locations = [(c[1], c[0]) for c in line.coords]
        layer = folium.PolyLine(
            locations=locations,
            color=s.color,
            weight=s.weight,
            opacity=s.opacity,
            dash_array=s.dash_array,
            tooltip=self._make_tooltip(tooltip, tooltip_style),
            popup=self._make_popup(popup, popup_style),
        )
        layer.add_to(self._target())
        self._record_feature(
            line,
            {
                "stroke_color": s.color,
                "stroke_weight": s.weight,
                "stroke_opacity": s.opacity,
                "stroke_dash_array": s.dash_array,
                "tooltip": self._raw_text(tooltip),
                "popup": self._raw_text(popup),
                "min_zoom": min_zoom,
            },
        )
        if min_zoom is not None and min_zoom > 0:
            self._zoom_controlled_markers.append({"var_name": layer.get_name(), "min_zoom": min_zoom})
        return self

    def add_polygon(
        self,
        polygon: Polygon,
        tooltip: str | RawHTML | None = None,
        popup: str | RawHTML | None = None,
        stroke: StrokeStyle | dict[str, Any] | None = None,
        fill: FillStyle | dict[str, Any] | None = None,
        popup_style: PopupStyle | dict[str, Any] | None = None,
        min_zoom: int | None = None,
        tooltip_style: TooltipStyle | dict[str, Any] | None = None,
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
        min_zoom : int | None
            Minimum zoom level at which the polygon is visible.
        tooltip_style : TooltipStyle | dict[str, Any] | None
            Tooltip appearance.

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
        layer = folium.Polygon(
            locations=locations,
            color=s.color,
            weight=s.weight,
            opacity=s.opacity,
            dash_array=s.dash_array,
            fill=True,
            fill_color=f.color,
            fill_opacity=f.opacity,
            tooltip=self._make_tooltip(tooltip, tooltip_style),
            popup=self._make_popup(popup, popup_style),
        )
        layer.add_to(self._target())
        self._record_feature(
            polygon,
            {
                "stroke_color": s.color,
                "stroke_weight": s.weight,
                "stroke_opacity": s.opacity,
                "stroke_dash_array": s.dash_array,
                "fill_color": f.color,
                "fill_opacity": f.opacity,
                "tooltip": self._raw_text(tooltip),
                "popup": self._raw_text(popup),
                "min_zoom": min_zoom,
            },
        )
        if min_zoom is not None and min_zoom > 0:
            self._zoom_controlled_markers.append({"var_name": layer.get_name(), "min_zoom": min_zoom})
        return self

    def add_multipolygon(
        self,
        mp: MultiPolygon,
        tooltip: str | RawHTML | None = None,
        popup: str | RawHTML | None = None,
        stroke: StrokeStyle | dict[str, Any] | None = None,
        fill: FillStyle | dict[str, Any] | None = None,
        popup_style: PopupStyle | dict[str, Any] | None = None,
        min_zoom: int | None = None,
        tooltip_style: TooltipStyle | dict[str, Any] | None = None,
    ) -> Self:
        """Add a MultiPolygon.

        Parameters
        ----------
        mp : MultiPolygon
            Shapely MultiPolygon.
        tooltip, popup, stroke, fill, popup_style, tooltip_style
            See ``add_polygon``.
        min_zoom : int | None
            Minimum zoom level at which each polygon is visible.

        Returns
        -------
        Map
        """
        for poly in mp.geoms:
            self.add_polygon(
                poly, tooltip=tooltip, popup=popup, stroke=stroke, fill=fill, popup_style=popup_style, min_zoom=min_zoom, tooltip_style=tooltip_style
            )
        return self

    def add_multilinestring(
        self,
        ml: MultiLineString,
        tooltip: str | RawHTML | None = None,
        popup: str | RawHTML | None = None,
        stroke: StrokeStyle | dict[str, Any] | None = None,
        popup_style: PopupStyle | dict[str, Any] | None = None,
        min_zoom: int | None = None,
        tooltip_style: TooltipStyle | dict[str, Any] | None = None,
    ) -> Self:
        """Add a MultiLineString.

        Parameters
        ----------
        ml : MultiLineString
            Shapely MultiLineString.
        tooltip, popup, stroke, popup_style, tooltip_style
            See ``add_linestring``.
        min_zoom : int | None
            Minimum zoom level at which each line is visible.

        Returns
        -------
        Map
        """
        for line in ml.geoms:
            self.add_linestring(
                line, tooltip=tooltip, popup=popup, stroke=stroke, popup_style=popup_style, min_zoom=min_zoom, tooltip_style=tooltip_style
            )
        return self

    def add_multipoint(
        self,
        mp: MultiPoint,
        tooltip: str | RawHTML | None = None,
        popup: str | RawHTML | None = None,
        label: str | None = None,
        marker_style: dict[str, str] | None = None,
        popup_style: PopupStyle | dict[str, Any] | None = None,
        min_zoom: int | None = None,
        tooltip_style: TooltipStyle | dict[str, Any] | None = None,
    ) -> Self:
        """Add a MultiPoint.

        Parameters
        ----------
        mp : MultiPoint
            Shapely MultiPoint.
        tooltip, popup, label, marker_style, popup_style, tooltip_style
            See ``add_point``.
        min_zoom : int | None
            Minimum zoom level at which each point is visible.

        Returns
        -------
        Map
        """
        for pt in mp.geoms:
            self.add_point(
                pt,
                tooltip=tooltip,
                popup=popup,
                marker=label,
                marker_style=marker_style,
                popup_style=popup_style,
                min_zoom=min_zoom,
                tooltip_style=tooltip_style,
            )
        return self

    def add_geometry(
        self,
        geom: BaseGeometry,
        tooltip: str | RawHTML | None = None,
        popup: str | RawHTML | None = None,
        label: str | None = None,
        stroke: StrokeStyle | dict[str, Any] | None = None,
        fill: FillStyle | dict[str, Any] | None = None,
        marker_style: dict[str, str] | None = None,
        popup_style: PopupStyle | dict[str, Any] | None = None,
        min_zoom: int | None = None,
        tooltip_style: TooltipStyle | dict[str, Any] | None = None,
    ) -> Self:
        """Add any Shapely geometry (auto-dispatches by type).

        Parameters
        ----------
        geom : BaseGeometry
            Any supported Shapely geometry.
        tooltip, popup, label, stroke, fill, marker_style, popup_style, tooltip_style
            Style and interaction parameters.
        min_zoom : int | None
            Minimum zoom level at which the geometry is visible.

        Returns
        -------
        Map

        Raises
        ------
        TypeError
            If geometry type is unsupported.
        """
        tip = tooltip
        ts = tooltip_style
        if isinstance(geom, Point):
            self.add_point(
                geom, tooltip=tip, popup=popup, marker=label, marker_style=marker_style, popup_style=popup_style, min_zoom=min_zoom, tooltip_style=ts
            )
        elif isinstance(geom, LinearRing):
            # LinearRing is a subclass of LineString, check first
            self.add_linestring(
                LineString(geom.coords), tooltip=tip, popup=popup, stroke=stroke, popup_style=popup_style, min_zoom=min_zoom, tooltip_style=ts
            )
        elif isinstance(geom, LineString):
            self.add_linestring(geom, tooltip=tip, popup=popup, stroke=stroke, popup_style=popup_style, min_zoom=min_zoom, tooltip_style=ts)
        elif isinstance(geom, Polygon):
            self.add_polygon(geom, tooltip=tip, popup=popup, stroke=stroke, fill=fill, popup_style=popup_style, min_zoom=min_zoom, tooltip_style=ts)
        elif isinstance(geom, MultiPolygon):
            self.add_multipolygon(
                geom, tooltip=tip, popup=popup, stroke=stroke, fill=fill, popup_style=popup_style, min_zoom=min_zoom, tooltip_style=ts
            )
        elif isinstance(geom, MultiLineString):
            self.add_multilinestring(geom, tooltip=tip, popup=popup, stroke=stroke, popup_style=popup_style, min_zoom=min_zoom, tooltip_style=ts)
        elif isinstance(geom, MultiPoint):
            self.add_multipoint(
                geom, tooltip=tip, popup=popup, label=label, marker_style=marker_style, popup_style=popup_style, min_zoom=min_zoom, tooltip_style=ts
            )
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
        if data.get("type") == "FeatureCollection":
            self._geojson_features.extend(data.get("features", []))
        elif data.get("type") == "Feature":
            self._geojson_features.append(data)

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

    def add_dataframe(
        self,
        df: Any,  # noqa: ANN401
        geometry_col: str = "geometry",
        hover_fields: list[str] | None = None,
        style: dict[str, Any] | None = None,
        highlight: dict[str, Any] | None = None,
    ) -> Self:
        """Add a Pandas or Polars DataFrame as a GeoJSON layer.

        The DataFrame must contain WKT geometry strings in WGS84 (EPSG:4326) in ``geometry_col``.
        All other columns become GeoJSON Feature properties and are accessible via ``hover_fields``.

        Parameters
        ----------
        df : pandas.DataFrame | polars.DataFrame
            Input DataFrame. GeoPandas GeoDataFrames are not supported; use
            :meth:`from_geodataframe` instead.
        geometry_col : str
            Column name that holds WKT geometry strings. Default ``"geometry"``.
        hover_fields : list[str] | None
            Property fields to show in the hover tooltip.
        style : dict[str, Any] | None
            Style kwargs forwarded to Folium GeoJson (e.g. ``color``, ``weight``).
        highlight : dict[str, Any] | None
            Highlight kwargs for mouse-over.

        Returns
        -------
        Map

        Raises
        ------
        TypeError
            If ``df`` is not a pandas or polars DataFrame.
        ValueError
            If ``geometry_col`` is missing, the DataFrame is empty, or a WKT string cannot be parsed.

        Examples
        --------
        >>> import pandas as pd
        >>> from mapyta import Map
        >>> df = pd.DataFrame({"geometry": ["POINT (4.9 52.37)"], "name": ["Amsterdam"]})
        >>> m = Map().add_dataframe(df, hover_fields=["name"])
        """
        from mapyta.dataframe import dataframe_to_geojson  # noqa: PLC0415

        fc = dataframe_to_geojson(df, geometry_col=geometry_col)
        return self.add_geojson(fc, hover_fields=hover_fields, style=style, highlight=highlight)

    # ------------------------------------------------------------------
    # Choropleth / colormap
    # ------------------------------------------------------------------

    def _build_colormap(
        self,
        colors: list[str] | str | None,
        vmin: float,
        vmax: float,
        caption: str,
    ) -> cm.LinearColormap:
        """Build a LinearColormap from a palette name, color list, or the default palette.

        Parameters
        ----------
        colors : list[str] | str | None
            Palette name (e.g. ``"blues"``), list of hex colors, or ``None`` for default.
        vmin, vmax : float
            Color scale range.
        caption : str
            Legend label.

        Returns
        -------
        branca.colormap.LinearColormap
        """
        return cm.LinearColormap(colors=self._resolve_colors(colors), vmin=vmin, vmax=vmax, caption=caption)

    def _resolve_colors(self, colors: list[str] | str | None) -> list[str]:
        """Resolve a palette name, explicit color list, or ``None`` to a concrete low→high ramp.

        Parameters
        ----------
        colors : list[str] | str | None
            Palette name (e.g. ``"blues"``), list of hex colors, or ``None`` for the
            default palette.

        Returns
        -------
        list[str]
            The resolved low→high color ramp.

        Raises
        ------
        ValueError
            If ``colors`` names an unknown palette or is an empty list.
        """
        if isinstance(colors, str):
            palette = PALETTES.get(colors)
            if palette is None:
                valid = ", ".join(f'"{k}"' for k in sorted(PALETTES))
                raise ValueError(f"Unknown palette {colors!r}. Available palettes: {valid}")
            return palette
        if colors is not None:
            if not colors:
                raise ValueError("colors list must not be empty")
            return colors
        return PALETTES["ylrd"]

    def _register_colormap(self, colormap: cm.LinearColormap | cm.StepColormap) -> None:
        """Add ``colormap`` to the folium map and track it so legends merge correctly."""
        colormap.add_to(self._map)
        self._colormaps.append(colormap)

    def add_colorbar(
        self,
        colors: list[str] | str | None,
        vmin: float,
        vmax: float,
        legend_name: str | RawHTML,
    ) -> cm.LinearColormap:
        """Add a standalone color-scale legend (colorbar) to the map.

        Unlike :meth:`add_choropleth` and :meth:`from_geodataframe`, this adds a
        legend on its own — for maps whose features are coloured by hand (e.g.
        :meth:`add_circle` / :meth:`add_point` with per-feature styles). The
        returned colormap is callable: ``colormap(value)`` yields the hex colour
        for ``value``, so callers colour their own features consistently with
        the legend without rebuilding the scale.

        The legend is a readable HTML ``<div>`` pinned to the right edge of the
        map, spanning ~90% of its height (5% clear at top and bottom): a vertical
        gradient bar with the ``legend_name`` above and evenly spaced value ticks
        alongside, high at the top, rather than branca's default SVG colorbar. The
        legend sits clear of the top-centre :paramref:`title` instead of
        overlapping it.

        Parameters
        ----------
        colors : list[str] | str | None
            Palette name (e.g. ``"blues"``), list of hex colors, or ``None`` for
            the default palette. Same handling as :meth:`add_choropleth`.
        vmin, vmax : float
            Color scale range.
        legend_name : str | RawHTML
            Legend label. Plain strings are HTML-escaped and shown literally; wrap
            in :class:`~mapyta.markdown.RawHTML` to render inline markup such as
            ``<sub>``/``<sup>`` (e.g. ``RawHTML("R<sub>c;cal</sub>")``).

        Returns
        -------
        branca.colormap.LinearColormap
            The colormap added to the map. Call it with a value to get a colour.
        """
        color_list = self._resolve_colors(colors)
        # Build the colormap from the already-resolved ramp (don't route back through
        # ``_build_colormap``, which would resolve a second time).
        colormap = cm.LinearColormap(colors=color_list, vmin=vmin, vmax=vmax, caption=legend_name)
        # Track the colormap in ``self._colormaps`` for consistency with the other
        # colormap methods, but skip ``_register_colormap``: it calls ``colormap.add_to``,
        # which would emit branca's SVG colorbar. We render our own HTML legend instead.
        self._colormaps.append(colormap)
        self._add_html_colorbar(colors=color_list, vmin=vmin, vmax=vmax, legend_name=legend_name)
        return colormap

    @staticmethod
    def _format_legend_value(value: float) -> str:
        """Format a colorbar tick: a plain integer when whole, else two decimals (no thousands separator)."""
        rounded = round(value, 2)
        if rounded.is_integer():
            return f"{int(rounded)}"
        return f"{rounded:.2f}"

    def _add_html_colorbar(self, colors: list[str], vmin: float, vmax: float, legend_name: str | RawHTML) -> None:
        """Render the HTML colorbar legend (gradient bar + caption + ticks) vertically on the right.

        Parameters
        ----------
        colors : list[str]
            The resolved low→high color ramp. Always holds at least two colours
            (branca's ``LinearColormap`` rejects fewer in :meth:`add_colorbar`).
        vmin, vmax : float
            Color scale range, used for the five evenly spaced value ticks.
        legend_name : str | RawHTML
            Legend label. Plain strings are HTML-escaped before being injected
            into the legend; only :class:`~mapyta.markdown.RawHTML` is rendered
            verbatim (e.g. ``<sub>``). This keeps untrusted text from becoming
            active markup, matching how tooltips/popups treat their text.
        """
        # Escape plain strings so untrusted captions can't inject markup; ``RawHTML``
        # (a ``str`` subclass) opts into verbatim rendering, mirroring tooltips/popups.
        caption = legend_name if isinstance(legend_name, RawHTML) else html_escape(legend_name)
        # ``to top`` puts the first colour (low) at the bottom and the last (high) at the top,
        # so the vertical bar reads low→high bottom-up like Plotly's colorbar.
        gradient = f"linear-gradient(to top, {', '.join(colors)})"
        tick_count = 5
        span = vmax - vmin
        # Ticks run high→low top-to-bottom to line up with the bottom-up gradient.
        tick_values = [vmin + span * step / (tick_count - 1) for step in reversed(range(tick_count))]
        ticks = "".join(f"<span>{self._format_legend_value(v)}</span>" for v in tick_values)
        # ``top:5%;bottom:5%`` makes the card span 90% of the map height (5% clear at each end)
        # regardless of map size; the bar row flex-fills whatever remains below the caption.
        legend_html = (
            '<div style="position:fixed;top:5%;bottom:5%;right:14px;'
            "z-index:1000;background:rgba(255,255,255,0.92);padding:8px 12px;border-radius:6px;"
            "box-shadow:0 2px 6px rgba(0,0,0,0.3);font-family:Arial,sans-serif;font-size:12px;"
            'color:#333;pointer-events:none;display:flex;flex-direction:column;">'
            f'<div style="text-align:center;font-weight:bold;margin-bottom:6px;">{caption}</div>'
            '<div style="display:flex;flex-direction:row;align-items:stretch;flex:1;min-height:0;">'
            f'<div style="width:14px;border-radius:2px;background:{gradient};"></div>'
            f'<div style="display:flex;flex-direction:column;justify-content:space-between;margin-left:6px;">{ticks}</div>'
            "</div>"
            "</div>"
        )
        self._map.get_root().html.add_child(folium.Element(legend_html))  # ty: ignore[unresolved-attribute]

    def add_choropleth(  # noqa: C901, PLR0913, PLR0912, PLR0915
        self,
        geojson_data: dict | str | Path,
        value_column: str,
        key_on: str,
        values: Mapping[str, float | str] | None = None,
        vmin: float | None = None,
        vmax: float | None = None,
        legend_name: str | None = None,
        nan_fill_color: str = "#cccccc",
        nan_fill_opacity: float = 0.4,
        line_weight: float = 1.0,
        line_opacity: float = 0.5,
        fill_opacity: float = 0.7,
        hover_fields: list[str] | None = None,
        colors: list[str] | str | None = None,
        categorical: bool | None = None,
    ) -> Self:
        """Add a choropleth (color-coded) layer.

        Parameters
        ----------
        geojson_data : dict | str | Path
            GeoJSON FeatureCollection.
        value_column : str
            Property name with numeric or categorical values.
        key_on : str
            Join key, e.g. ``"feature.properties.id"``.
        values : dict[str, float | str] | None
            Key -> value mapping. Reads from properties if ``None``.
        vmin, vmax : float | None
            Color scale range for numeric data. Auto-calculated if ``None``.
        legend_name : str | None
            Legend label.
        nan_fill_color : str
            Color for missing values.
        nan_fill_opacity : float
            Opacity for missing values.
        line_weight, line_opacity, fill_opacity : float
            Styling parameters.
        hover_fields : list[str] | None
            Tooltip property fields.
        colors : list[str] | str | None
            Color palette. Pass a palette name (e.g. ``"blues"``, ``"viridis"``) or
            a list of hex color strings. See ``mapyta.PALETTES`` for available names.
            Defaults to ``"ylrd"`` (yellow → red).
        categorical : bool | None
            Force categorical mode (``True``), numeric mode (``False``), or auto-detect
            from values (``None``). In categorical mode, each unique value gets a
            distinct color from the palette.

        Returns
        -------
        Map
        """
        geojson_data = load_geojson_input(geojson_data)
        if geojson_data.get("type") == "FeatureCollection":
            self._geojson_features.extend(geojson_data.get("features", []))
        elif geojson_data.get("type") == "Feature":
            self._geojson_features.append(geojson_data)

        # Extract values if not provided
        if values is None:
            extracted: dict[str, float | str] = {}
            key_parts = key_on.split(".")
            for feat in geojson_data.get("features", []):
                obj = feat
                for part in key_parts[1:]:
                    obj = obj.get(part, {})
                key = obj if isinstance(obj, str) else str(obj)
                raw_val = feat.get("properties", {}).get(value_column)
                if raw_val is not None:
                    extracted[key] = raw_val
            values = extracted

        # Determine if categorical
        raw_vals = list(values.values())
        is_categorical = categorical if categorical is not None else any(isinstance(v, str) for v in raw_vals)

        caption = legend_name or value_column

        if is_categorical:
            # Build discrete color mapping per unique category
            categories = list(dict.fromkeys(str(v) for v in raw_vals))
            palette_colors = self._resolve_colors(colors)
            # Cycle colors if more categories than palette entries
            cat_color_map: dict[str, str] = {cat: palette_colors[i % len(palette_colors)] for i, cat in enumerate(categories)}

            # Use the actual cycled colors per category so the legend matches the map
            legend_colors = [cat_color_map[cat] for cat in categories] if categories else palette_colors[:1]
            colormap = cm.StepColormap(
                colors=legend_colors,
                vmin=0,
                vmax=max(len(categories) - 1, 1),
                caption=caption,
            )

            _str_vals = {k: str(v) for k, v in values.items()}
            _cat_map = cat_color_map

            def style_fn(feature: dict) -> dict:
                obj = feature
                for part in key_on.split(".")[1:]:
                    obj = obj.get(part, {})
                key = obj if isinstance(obj, str) else str(obj)
                val_str = _str_vals.get(key)
                fill_color = _cat_map.get(val_str, nan_fill_color) if val_str is not None else nan_fill_color
                return {"fillColor": fill_color, "color": "#333", "weight": line_weight, "fillOpacity": fill_opacity, "opacity": line_opacity}

        else:
            # Numeric mode
            num_vals: list[float] = []
            for v in raw_vals:
                if isinstance(v, str):
                    continue
                try:
                    num_vals.append(float(v))
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"Non-numeric value {v!r} in choropleth values cannot be converted to float") from exc
            if num_vals:
                vmin = vmin if vmin is not None else min(num_vals)
                vmax = vmax if vmax is not None else max(num_vals)

            colormap = self._build_colormap(
                colors=colors,
                vmin=vmin if vmin is not None else 0,
                vmax=vmax if vmax is not None else 1,
                caption=caption,
            )

            _num_vals = {k: float(v) for k, v in values.items() if not isinstance(v, str)}
            _cmap = colormap

            def style_fn(feature: dict) -> dict:
                obj = feature
                for part in key_on.split(".")[1:]:
                    obj = obj.get(part, {})
                key = obj if isinstance(obj, str) else str(obj)
                val = _num_vals.get(key)
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
        self._register_colormap(colormap)

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
                self._record_feature(pt, {})
            elif len(p) == 2:
                heat_data.append([p[0], p[1]])
                self._bounds.append((p[0], p[1]))
                self._record_feature(Point(p[1], p[0]), {})
            else:
                heat_data.append(list(p[:3]))
                self._bounds.append((p[0], p[1]))
                self._record_feature(Point(p[1], p[0]), {"intensity": p[2]})  # ty: ignore[index-out-of-bounds]

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
    # Animated / time-based layers
    # ------------------------------------------------------------------

    def add_ant_path(  # noqa: PLR0913
        self,
        line: LineString | list[Point],
        tooltip: str | RawHTML | None = None,
        popup: str | RawHTML | None = None,
        color: str = "#0000FF",
        pulse_color: str = "#FFFFFF",
        weight: int = 5,
        delay: int = 400,
        dash_array: list[int] | None = None,
        paused: bool = False,
        reverse: bool = False,
        popup_style: PopupStyle | dict[str, Any] | None = None,
    ) -> Self:
        """Add an animated dashed line (ant path) along a route.

        The path is drawn as a marching-ants animation: a dashed line
        whose gaps appear to travel in the direction of travel.

        Parameters
        ----------
        line : LineString | list[Point]
            Route geometry.  Pass a Shapely ``LineString`` or a list of
            Shapely ``Point`` objects as waypoints.
        tooltip : str | RawHTML | None
            Markdown tooltip, or ``RawHTML`` for pre-formatted HTML.
        popup : str | RawHTML | None
            Markdown popup, or ``RawHTML`` for pre-formatted HTML.
        color : str
            Line colour (CSS hex or name).
        pulse_color : str
            Colour of the travelling pulse / gap fill.
        weight : int
            Line width in pixels.
        delay : int
            Animation step interval in milliseconds.  Lower = faster.
        dash_array : list[int] | None
            ``[dash_length, gap_length]`` pattern in pixels.
            Defaults to ``[10, 20]`` when ``None``.
        paused : bool
            Start the animation paused.
        reverse : bool
            Reverse the direction of travel.
        popup_style : PopupStyle | dict[str, Any] | None
            Popup dimensions.

        Returns
        -------
        Map
        """
        if isinstance(line, LineString):
            transformed = cast(LineString, self._transform(line))
            self._extend_bounds(transformed)
            locations = [(c[1], c[0]) for c in transformed.coords]
            self._record_feature(
                transformed,
                {"color": color, "tooltip": self._raw_text(tooltip), "popup": self._raw_text(popup)},
            )
        else:
            locations = []
            for pt in line:
                t = cast(Point, self._transform(pt))
                self._extend_bounds(t)
                locations.append((t.y, t.x))
                self._record_feature(t, {"color": color})

        kwargs: dict[str, Any] = {
            "color": color,
            "pulseColor": pulse_color,
            "weight": weight,
            "delay": delay,
            "paused": paused,
            "reverse": reverse,
        }
        if dash_array is not None:
            kwargs["dashArray"] = dash_array

        folium.plugins.AntPath(
            locations=locations,
            tooltip=self._make_tooltip(tooltip),
            popup=self._make_popup(popup, popup_style),
            **kwargs,
        ).add_to(self._target())
        return self

    def add_heatmap_with_time(
        self,
        data: list[list[Point] | list[tuple[float, float]] | list[tuple[float, float, float]]],
        index: list[str],
        radius: int = 15,
        blur: float = 0.8,
        max_opacity: float = 0.6,
        min_opacity: float = 0.0,
        gradient: dict[float, str] | None = None,
        auto_play: bool = False,
        display_index: bool = True,
        position: str = "bottomleft",
    ) -> Self:
        """Add a heatmap with a time slider.

        Displays a heatmap that changes over time.  A playback control
        lets users step or scrub through the time steps.

        Parameters
        ----------
        data : list of timestep point lists
            Outer list corresponds to time steps (must match *index*
            length).  Each inner list is a collection of points for that
            step, in the same format accepted by :meth:`add_heatmap`:
            Shapely ``Point`` objects or ``(lat, lon[, intensity])``
            tuples.
        index : list[str]
            Labels for each time step shown in the slider (e.g. dates:
            ``["2024-01", "2024-02", ...]``).
        radius : int
            Heatmap point radius in pixels.
        blur : float
            Blur amount (0–1).
        max_opacity : float
            Maximum heatmap opacity (0–1).
        min_opacity : float
            Minimum heatmap opacity (0–1).
        gradient : dict[float, str] | None
            Colour gradient mapping density values (0–1) to CSS colours,
            e.g. ``{0.0: "blue", 0.5: "yellow", 1.0: "red"}``.
        auto_play : bool
            Start playback automatically when the map loads.
        display_index : bool
            Show the current time step label in the control.
        position : str
            Control position: ``"bottomleft"``, ``"bottomright"``,
            ``"topleft"``, or ``"topright"``.

        Returns
        -------
        Map

        Raises
        ------
        ValueError
            If the length of *data* does not match the length of *index*.
        """
        if len(data) != len(index):
            msg = f"add_heatmap_with_time(): data has {len(data)} time step(s) but index has {len(index)} label(s). They must be equal."
            raise ValueError(msg)

        time_data: list[list[list[float]]] = []
        for timestep in data:
            step_points: list[list[float]] = []
            for p in timestep:
                if isinstance(p, Point):
                    pt = cast(Point, self._transform(p))
                    self._extend_bounds(pt)
                    step_points.append([pt.y, pt.x])
                elif len(p) == 3:
                    self._bounds.append((p[0], p[1]))
                    step_points.append([p[0], p[1], p[2]])  # ty: ignore[index-out-of-bounds]
                else:
                    self._bounds.append((p[0], p[1]))
                    step_points.append([p[0], p[1]])
            time_data.append(step_points)

        kwargs: dict[str, Any] = {
            "radius": radius,
            "blur": blur,
            "max_opacity": max_opacity,
            "min_opacity": min_opacity,
            "auto_play": auto_play,
            "display_index": display_index,
            "position": position,
        }
        if gradient:
            kwargs["gradient"] = gradient

        folium.plugins.HeatMapWithTime(time_data, index=index, **kwargs).add_to(self._target())
        return self

    def add_timestamped_geojson(
        self,
        data: dict | str | Path,
        auto_play: bool = True,
        loop: bool = True,
        transition_time: int = 200,
        period: str = "P1D",
        date_options: str = "YYYY-MM-DD HH:mm:ss",
        duration: str | None = None,
    ) -> Self:
        """Add a GeoJSON layer animated over time.

        Each feature in *data* must carry a ``times`` property — an array
        of timestamps (ISO 8601 strings or milliseconds since epoch) with
        one entry per coordinate in the geometry.  A playback control is
        injected into the map automatically.

        Parameters
        ----------
        data : dict | str | Path
            GeoJSON ``FeatureCollection`` as a Python dict, a JSON
            string, or a file path.  Every feature must have a ``times``
            property whose length matches its coordinate count.
        auto_play : bool
            Start playback when the map loads.
        loop : bool
            Loop animation continuously.
        transition_time : int
            Duration of each frame transition in milliseconds.
        period : str
            ISO 8601 duration string controlling the slider step
            (e.g. ``"P1D"`` = 1 day, ``"PT1H"`` = 1 hour,
            ``"PT1M"`` = 1 minute).
        date_options : str
            `moment.js <https://momentjs.com/docs/#/displaying/>`_ format
            string for the displayed timestamp label.
        duration : str | None
            ISO 8601 duration for how long each feature remains visible
            after its timestamp.  ``None`` means it stays visible forever
            once shown.

        Returns
        -------
        Map

        Notes
        -----
        Supported geometry types: ``LineString``, ``MultiPoint``,
        ``MultiLineString``, ``Polygon``, ``MultiPolygon``.

        Example GeoJSON feature with timestamps::

            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [4.90, 52.37],
                        [4.91, 52.38],
                        [4.92, 52.39],
                    ],
                },
                "properties": {
                    "times": ["2024-01-01", "2024-01-02", "2024-01-03"],
                    "tooltip": "Route segment",
                },
            }
        """
        if isinstance(data, Path):
            raw: dict | str = data.read_text(encoding="utf-8")
        else:
            raw = data

        layer = folium.plugins.TimestampedGeoJson(
            data=raw,
            auto_play=auto_play,
            loop=loop,
            transition_time=transition_time,
            period=period,
            date_options=date_options,
            duration=duration,
        )
        layer.add_to(self._target())

        try:
            bounds = layer.get_bounds()
            if bounds:
                self._bounds.extend(cast(list[tuple[float, float]], bounds))
        except Exception:
            pass

        return self

    # ------------------------------------------------------------------
    # Marker cluster
    # ------------------------------------------------------------------

    def add_marker_cluster(  # noqa: PLR0913
        self,
        points: list[Point],
        labels: list[str] | None = None,
        tooltips: list[str] | None = None,
        popups: list[str] | None = None,
        marker_style: dict[str, str] | None = None,
        name: str | None = None,
        min_zoom: int | None = None,
        popup_style: PopupStyle | dict[str, Any] | None = None,
        captions: list[str] | None = None,
        caption_style: dict[str, str] | None = None,
        tooltip_style: TooltipStyle | dict[str, Any] | None = None,
        min_zoom_caption: int | None = None,
    ) -> Self:
        """Add clustered markers that group at low zoom.

        Parameters
        ----------
        points : list[Point]
            Shapely Points.
        labels : list[str] | None
            Per-location marker content (icon names or emoji/text).
        tooltips : list[str] | None
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
        tooltip_style : TooltipStyle | dict[str, Any] | None
            Tooltip appearance (font size, width, etc.).
        min_zoom_caption : int | None
            Minimum zoom level at which captions are visible. Applies only
            to the caption text — the marker icons remain visible. ``None``
            or ``0`` means always visible. Ignored for entries without a
            caption. Note: caption visibility is also bounded below by
            each entry's ``min_zoom`` — the caption lives inside the
            marker's DivIcon DOM, which is removed when the marker is
            hidden, so setting ``min_zoom_caption`` lower than ``min_zoom``
            does not reveal the caption at those zooms.

        Returns
        -------
        Map
        """
        css = marker_style or {}
        cap_css = {**DEFAULT_MARKER_CAPTION_CSS, **(caption_style or {})}
        cluster = folium.plugins.MarkerCluster(name=name)
        track_captions = min_zoom_caption is not None and min_zoom_caption > 0

        for i, point in enumerate(points):
            pt = cast(Point, self._transform(point))
            self._extend_bounds(pt)
            lat, lon = pt.y, pt.x

            label = labels[i] if labels and i < len(labels) else None
            tip = tooltips[i] if tooltips and i < len(tooltips) else None
            popup = popups[i] if popups and i < len(popups) else None
            txt = captions[i] if captions and i < len(captions) else None

            caption_id: str | None = None
            if txt is not None and track_captions:
                caption_id = f"caption_{uuid.uuid4().hex[:15]}"

            kind = classify_marker(label) if label else "icon_name"
            if kind == "emoji":
                assert label is not None  # guarded by classify_marker above
                icon = build_text_marker(label, css, txt, cap_css, caption_id)
            else:
                icon_name = label or "arrow-down"
                icon = build_icon_marker(icon_name, css, txt, cap_css, caption_id)

            folium.Marker(
                location=[lat, lon],
                icon=icon,
                tooltip=self._make_tooltip(tip, tooltip_style),
                popup=self._make_popup(popup, popup_style),
            ).add_to(cluster)
            self._record_feature(
                pt,
                {
                    "marker": label,
                    "caption": txt,
                    "tooltip": tip,
                    "popup": popup,
                    "min_zoom": min_zoom,
                    "min_zoom_caption": min_zoom_caption,
                },
            )

            if caption_id is not None:
                assert min_zoom_caption is not None  # guarded by track_captions above
                self._zoom_controlled_captions.append(
                    {
                        "caption_id": caption_id,
                        "min_zoom": min_zoom_caption,
                    }
                )

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
        tooltip: str | RawHTML | None = None,
        popup: str | RawHTML | None = None,
        popup_style: PopupStyle | dict[str, Any] | None = None,
        min_zoom: int | None = None,
        tooltip_style: TooltipStyle | dict[str, Any] | None = None,
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
        tooltip : str | RawHTML | None
            Markdown tooltip, or ``RawHTML`` for pre-formatted HTML.
        popup : str | RawHTML | None
            Markdown popup, or ``RawHTML`` for pre-formatted HTML.
        popup_style : PopupStyle | dict[str, Any] | None
            Popup dimensions.
        tooltip_style : TooltipStyle | dict[str, Any] | None
            Tooltip appearance.
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
        # icon_size is a small fixed box around the anchor (depends on
        # font-size only, not on text length). The text is absolutely
        # centered on the anchor and overflows via overflow:visible, so
        # long labels render fully without widening the Leaflet icon box.
        fs = px_to_int(merged.get("font-size", "12px"), 12)
        w = fs + 10
        h = fs + 10
        html = (
            f'<div style="position:relative;width:{w}px;height:{h}px;overflow:visible;">'
            f'<div style="position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);'
            f'white-space:nowrap;{css_str}">{text}</div>'
            f"</div>"
        )
        icon = folium.DivIcon(
            html=html,
            icon_size=(w, h),
            icon_anchor=(w // 2, h // 2),
            class_name="",
        )
        marker = folium.Marker(
            location=[lat, lon],
            icon=icon,
            tooltip=self._make_tooltip(tooltip, tooltip_style),
            popup=self._make_popup(popup, popup_style),
        )
        marker.add_to(self._target())
        self._record_feature(
            Point(lon, lat), {"text": text, "tooltip": self._raw_text(tooltip), "popup": self._raw_text(popup), "min_zoom": min_zoom}
        )
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
    def from_geodataframe(  # noqa: PLR0913, C901, PLR0912
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
        colors: list[str] | str | None = None,
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
            Color scale label.
        colors : list[str] | str | None
            Color palette for ``color_column``. Pass a palette name (e.g. ``"blues"``)
            or a list of hex color strings. See ``mapyta.PALETTES`` for available names.
            Defaults to ``"ylrd"`` (yellow → red).

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

        # Validate column references
        available = list(gdf.columns)
        for param_name, cols in [("hover_columns", hover_columns or []), ("popup_columns", popup_columns or [])]:
            missing = [c for c in cols if c not in gdf.columns]
            if missing:
                warnings.warn(
                    f"from_geodataframe(): {param_name} contains column(s) not found in the GeoDataFrame: {missing}. Available columns: {available}",
                    UserWarning,
                    stacklevel=2,
                )
        for param_name, col in [("label_column", label_column), ("color_column", color_column)]:
            if col is not None and col not in gdf.columns:
                warnings.warn(
                    f"from_geodataframe(): {param_name}={col!r} not found in the GeoDataFrame. Available columns: {available}",
                    UserWarning,
                    stacklevel=2,
                )

        m = cls(title=title, config=config)

        # Build colormap
        colormap = None
        if color_column and color_column in gdf.columns:
            vals = gdf[color_column].dropna()
            if len(vals) > 0:
                vmin, vmax = float(vals.min()), float(vals.max())
                colormap = m._build_colormap(
                    colors=colors,
                    vmin=vmin,
                    vmax=vmax,
                    caption=legend_name or color_column,
                )
                m._register_colormap(colormap)

        # Iterate rows
        for idx, row in gdf.iterrows():
            geom = row.geometry

            if not isinstance(geom, BaseGeometry):
                continue

            if geom is None or geom.is_empty:
                continue

            # Build tooltip/popup text
            tooltip = None
            if hover_columns:
                parts = [f"**{c}**: {row[c]}" for c in hover_columns if c in row.index]
                tooltip = "\n".join(parts) if parts else None

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
                    _fill_base = fill if isinstance(fill, FillStyle) else FillStyle()
                    _stroke_base = stroke if isinstance(stroke, StrokeStyle) else StrokeStyle()
                    cur_fill = FillStyle(color=c, opacity=_fill_base.opacity)
                    cur_stroke = StrokeStyle(
                        color=c,
                        weight=_stroke_base.weight,
                        opacity=_stroke_base.opacity,
                    )

            m.add_geometry(
                geom=geom,
                tooltip=tooltip,
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

    def add_layer_dropdown(
        self,
        names: list[str] | None = None,
        position: str = "topleft",
        label: str | None = None,
    ) -> Self:
        """Add a single-select dropdown that switches between feature groups.

        Where :meth:`add_layer_control` lists feature groups as checkboxes (any
        number visible at once), this renders a single ``<select>`` whose options
        are feature groups: choosing one shows that group and hides the others, so
        exactly one is visible and the dropdown displays the active group's name.

        The chosen groups are removed from :meth:`add_layer_control`'s overlay
        list (their ``control`` flag is cleared at render time), so a group shows
        up in either the dropdown or the checkbox control, never both. Base/tile
        layers are untouched and keep their radio control. Use the two together to
        get radio tile layers plus a single-select overlay switcher.

        Parameters
        ----------
        names : list[str] | None
            Feature group names to include, in display order. ``None`` (the
            default) uses every feature group created so far, in creation order.
            Unknown names are ignored; if none match, the call is a no-op.
        position : str
            Leaflet control position: ``"topleft"``, ``"topright"``,
            ``"bottomleft"``, or ``"bottomright"``.
        label : str | None
            Optional caption rendered above the dropdown.

        Returns
        -------
        Map
        """
        self._layer_dropdown_config = {"names": names, "position": position, "label": label}
        self._layer_dropdown_injected = False
        return self

    def _inject_layer_dropdown(self) -> None:
        """Inject the single-select feature-group dropdown as a Leaflet control.

        Runs from :meth:`_ensure_rendered`, i.e. before ``folium.LayerControl``
        renders, so clearing each managed group's ``control`` flag here is what
        keeps those groups out of the checkbox control.
        """
        cfg = self._layer_dropdown_config
        assert cfg is not None
        requested: list[str] | None = cfg["names"]
        names = requested if requested is not None else list(self._feature_groups)
        pairs = [(name, self._feature_groups[name]) for name in names if name in self._feature_groups]
        if not pairs:
            return
        # [[display_name, leaflet_var], ...], preserving the requested order. In the same pass,
        # clear each group's ``control`` flag so the checkbox LayerControl (rendered after this)
        # leaves the dropdown-owned groups out and lists only base/tile layers.
        options = []
        for name, group in pairs:
            group.control = False
            options.append([name, group.get_name()])
        options_json = json.dumps(options)

        map_var = self._map.get_name()
        position = cfg["position"]
        label = cfg["label"]
        if label:
            label_js = (
                "        var lbl = L.DomUtil.create('div', '', div);\n"
                f"        lbl.innerHTML = {json.dumps(label)};\n"
                "        lbl.style.cssText = 'font-size:11px;font-weight:bold;margin-bottom:3px;color:#333;';\n"
            )
        else:
            label_js = ""

        # DOMContentLoaded so the map and feature-group variables (declared at the
        # top of Folium's synchronous script block) are defined, mirroring the
        # export button. The groups are added to the map at creation, so the initial
        # ``showOnly`` removes all but the first to enforce single-select.
        script = (
            "<script>\n"
            "document.addEventListener('DOMContentLoaded', function() {\n"
            f"    var map = window['{map_var}'];\n"
            "    if (!map) return;\n"
            f"    var _ddOpts = {options_json};\n"
            "    var groups = _ddOpts.map(function(o) { return {name: o[0], layer: window[o[1]]}; })\n"
            "        .filter(function(g) { return g.layer; });\n"
            "    if (!groups.length) return;\n"
            "    function showOnly(name) {\n"
            "        groups.forEach(function(g) {\n"
            "            if (g.name === name) { if (!map.hasLayer(g.layer)) { map.addLayer(g.layer); } }\n"
            "            else if (map.hasLayer(g.layer)) { map.removeLayer(g.layer); }\n"
            "        });\n"
            "    }\n"
            f"    var ddControl = L.control({{position: '{position}'}});\n"
            "    ddControl.onAdd = function() {\n"
            "        var div = L.DomUtil.create('div', 'leaflet-bar');\n"
            "        div.style.cssText = 'background:#fff;padding:4px 6px;border-radius:5px;';\n"
            f"{label_js}"
            "        var select = L.DomUtil.create('select', '', div);\n"
            "        select.style.cssText = 'border:none;background:#fff;font-size:13px;cursor:pointer;max-width:220px;';\n"
            "        groups.forEach(function(g) {\n"
            "            var opt = document.createElement('option');\n"
            "            opt.value = g.name; opt.text = g.name;\n"
            "            select.appendChild(opt);\n"
            "        });\n"
            "        select.onchange = function() { showOnly(this.value); };\n"
            "        L.DomEvent.disableClickPropagation(div);\n"
            "        L.DomEvent.disableScrollPropagation(div);\n"
            "        return div;\n"
            "    };\n"
            "    ddControl.addTo(map);\n"
            "    showOnly(groups[0].name);\n"
            "});\n"
            "</script>\n"
        )
        self._map.get_root().html.add_child(folium.Element(script))  # ty: ignore[unresolved-attribute]

    _SEARCH_LABEL_PRIORITY = ("caption", "label", "text", "name", "naam", "title")

    def _infer_search_label(self, props: dict[str, Any]) -> str:
        """Return the best human-readable label for a feature's properties dict.

        Parameters
        ----------
        props : dict[str, Any]
            The GeoJSON feature's ``properties`` dict.

        Returns
        -------
        str
            The inferred label, or an empty string if no suitable value is found.
        """
        for key in self._SEARCH_LABEL_PRIORITY:
            val = props.get(key)
            if val is not None and str(val).strip():
                return str(val).strip()
        for val in props.values():
            if val is not None and str(val).strip():
                return str(val).strip()
        return ""

    def _build_hidden_search_layer(self, property_name: str | None) -> folium.GeoJson:
        """Build an invisible GeoJson layer with a ``_search_label`` property on each feature.

        Parameters
        ----------
        property_name : str | None
            If provided, use this GeoJSON property value directly as the search label.
            If ``None``, the label is inferred via :meth:`_infer_search_label`.

        Returns
        -------
        folium.GeoJson
            An invisible layer suitable for use with ``folium.plugins.Search``.
        """
        features = []
        for raw in self._geojson_features:
            feature_copy = {**raw}
            props_copy = dict(raw.get("properties") or {})
            if property_name is not None:
                value = props_copy.get(property_name)
                label = str(value) if value is not None else ""
            else:
                label = self._infer_search_label(props_copy)
            props_copy["_search_label"] = label
            feature_copy["properties"] = props_copy
            features.append(feature_copy)
        collection = {"type": "FeatureCollection", "features": features}
        return folium.GeoJson(
            collection,
            style_function=lambda _: {"opacity": 0, "fillOpacity": 0, "weight": 0},
            show=True,
        )

    def add_search_control(
        self,
        layer_name: str | None = None,
        property_name: str | None = None,
        placeholder: str = "Search...",
        position: str = "topright",
        zoom: int | None = None,
        geom_type: str = "Point",
    ) -> Self:
        """Add a search control to find features by property value.

        Users can type in the search box to locate and zoom to a matching feature.

        When ``layer_name`` is ``None`` (the default), the search runs over **all** features
        added to the map — markers, GeoJSON, choropleth, and cluster layers — without
        requiring a feature group. Labels are inferred automatically from the feature's
        properties (``caption``, ``name``, ``naam``, etc.), or taken from ``property_name``
        if supplied. If no features have been added yet, the call is a silent no-op.

        When ``layer_name`` is provided, the search targets only that named feature group,
        preserving the original behaviour.

        Parameters
        ----------
        layer_name : str | None
            Name of the feature group to search (as passed to ``create_feature_group``).
            Pass ``None`` (the default) to search all features on the map automatically.
        property_name : str | None
            GeoJSON property name to use as the search label (e.g. ``"name"``, ``"gemeente"``).
            When ``None`` and ``layer_name`` is also ``None``, the label is inferred from
            common property names (``caption``, ``label``, ``text``, ``name``, ``naam``, ``title``).
        placeholder : str
            Placeholder text in the search input box.
        position : str
            Control position: ``"topleft"``, ``"topright"``, ``"bottomleft"``, ``"bottomright"``.
        zoom : int | None
            Zoom level to use when a result is selected. Uses the map's current zoom if ``None``.
        geom_type : str
            Geometry type of the features being searched: ``"Point"`` or ``"Polygon"``.
            Use ``"Polygon"`` when searching choropleth or polygon layers.

        Returns
        -------
        Map

        Raises
        ------
        KeyError
            If ``layer_name`` is provided but not found in the map's feature groups.
        """
        if layer_name is not None:
            if layer_name not in self._feature_groups:
                available = ", ".join(f'"{n}"' for n in self._feature_groups) or "(none)"
                raise KeyError(f"Feature group {layer_name!r} not found. Available groups: {available}")
            layer: folium.FeatureGroup | folium.GeoJson = self._feature_groups[layer_name]
            search_label = property_name
        else:
            if not self._geojson_features:
                return self
            layer = self._build_hidden_search_layer(property_name)
            layer.add_to(self._map)
            search_label = "_search_label"
        search_kwargs: dict[str, Any] = {
            "layer": layer,
            "geom_type": geom_type,
            "placeholder": placeholder,
            "collapsed": False,
            "search_label": search_label,
            "position": position,
        }
        if zoom is not None:
            search_kwargs["search_zoom"] = zoom
        folium.plugins.Search(**search_kwargs).add_to(self._map)
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
        cfg = self._config
        max_native_zoom = cfg.max_native_zoom if cfg.max_native_zoom is not None else cfg.max_zoom
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
            max_zoom=cfg.max_zoom,
            max_native_zoom=max_native_zoom,
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
        result._zoom_controlled_captions.extend(other._zoom_controlled_captions)
        return result

    # ------------------------------------------------------------------
    # Export methods
    # ------------------------------------------------------------------

    @property
    def folium_map(self) -> folium.Map:
        """Access the underlying Folium Map for advanced customization."""
        return self._map

    def _generate_zoom_javascript(self) -> str:
        """Generate JavaScript for zoom-dependent marker and caption visibility.

        Returns
        -------
        str
            A ``<script>`` block that toggles marker and caption visibility
            based on the current zoom level.
        """
        ids = ", ".join(f'"{m["var_name"]}"' for m in self._zoom_controlled_markers)
        marker_config = ", ".join(f'{{id: "{m["var_name"]}", minZoom: {m["min_zoom"]}}}' for m in self._zoom_controlled_markers)
        caption_config = ", ".join(f'{{id: "{c["caption_id"]}", minZoom: {c["min_zoom"]}}}' for c in self._zoom_controlled_captions)
        return (
            "<script>\n"
            "document.addEventListener('DOMContentLoaded', function() {\n"
            # Build registry using window[id] — avoids eval and scope issues.
            # By DOMContentLoaded all Folium layer vars (declared with `var` after </body>) are in window.
            "    var registry = {};\n"
            "    [" + ids + "].forEach(function(id) { registry[id] = window[id]; });\n"
            "    var checkInterval = setInterval(function() {\n"
            "        var mapContainer = document.querySelector('.folium-map');\n"
            # Folium names the map variable identically to the container id (e.g. map_abc123).
            # window[mapContainer.id] is the Leaflet map object once the Folium init script has run.
            "        if (mapContainer && window[mapContainer.id] && window[mapContainer.id].getZoom) {\n"
            "            clearInterval(checkInterval);\n"
            "            var map = window[mapContainer.id];\n"
            "            var configs = [" + marker_config + "];\n"
            "            var captions = [" + caption_config + "];\n"
            "            function update() {\n"
            "                var z = map.getZoom();\n"
            "                configs.forEach(function(c) {\n"
            "                    var el = registry[c.id];\n"
            "                    if (!el) { return; }\n"
            "                    if (z >= c.minZoom) { el.addTo(map); }\n"
            "                    else { map.removeLayer(el); }\n"
            "                });\n"
            # Re-query captions on each update — the DivIcon DOM is recreated when
            # a marker is re-added to the map, so any prior display toggle is lost.
            "                captions.forEach(function(c) {\n"
            "                    var el = document.getElementById(c.id);\n"
            "                    if (!el) { return; }\n"
            "                    el.style.display = z >= c.minZoom ? '' : 'none';\n"
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
        """Fit bounds and inject zoom JS / draw plugin / layer dropdown / export button (idempotent)."""
        if not self._center:
            self._fit_bounds()
        if (self._zoom_controlled_markers or self._zoom_controlled_captions) and not self._zoom_js_injected:
            self._map.get_root().html.add_child(folium.Element(self._generate_zoom_javascript()))  # ty: ignore[unresolved-attribute]
            self._zoom_js_injected = True
        if self._draw_config and not self._draw_injected:
            self._inject_draw_plugin()
        # Before the export button (irrelevant) but, crucially, before the final render:
        # clearing the managed groups' ``control`` flag here is what drops them from
        # the checkbox LayerControl.
        if self._layer_dropdown_config and not self._layer_dropdown_injected:
            self._inject_layer_dropdown()
            self._layer_dropdown_injected = True
        if self._export_button_config and not self._export_button_injected:
            self._inject_export_button()
            self._export_button_injected = True

    def _get_html(self) -> str:
        """Render map to an embeddable HTML string (Jupyter/inline)."""
        self._ensure_rendered()
        return self._map._repr_html_()

    def get_standalone_html(self) -> str:
        """Render map to a full standalone HTML document."""
        self._ensure_rendered()
        return self._map.get_root().render()

    @overload
    def to_html(self, path: None = None, open_in_browser: bool = False) -> str: ...

    @overload
    def to_html(self, path: str | Path, open_in_browser: bool = False) -> Path: ...

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
        out.write_text(self.get_standalone_html(), encoding="utf-8")
        if open_in_browser:
            webbrowser.open(out.resolve().as_uri())
        return out

    @overload
    def to_geojson(self, path: None = None) -> dict: ...

    @overload
    def to_geojson(self, path: str | Path) -> Path: ...

    def to_geojson(self, path: str | Path | None = None) -> dict | Path:
        """Export tracked features as a GeoJSON FeatureCollection.

        Parameters
        ----------
        path : str | Path | None
            Output file path.  When ``None``, the FeatureCollection dict is
            returned instead of being written to disk.

        Returns
        -------
        dict | Path
            FeatureCollection dict when *path* is ``None``, otherwise the
            resolved output :class:`~pathlib.Path`.
        """
        fc = self._build_geojson_collection()
        if path is None:
            return fc
        out = Path(path)
        out.write_text(json.dumps(fc, indent=2, ensure_ascii=False), encoding="utf-8")
        return out

    def add_export_button(
        self,
        label: str = "Download GeoJSON",
        filename: str = "export.geojson",
        position: str = "topright",
    ) -> Self:
        """Add a download button to the map that exports all features as a GeoJSON file.

        When clicked, the button triggers a browser download of a GeoJSON
        ``FeatureCollection`` containing all features added to the map.

        Parameters
        ----------
        label : str
            Button label text.
        filename : str
            Default filename for the downloaded file.
        position : str
            Leaflet control position: ``"topleft"``, ``"topright"``,
            ``"bottomleft"``, or ``"bottomright"``.

        Returns
        -------
        Map
        """
        self._export_button_config = {"label": label, "filename": filename, "position": position}
        return self

    def _inject_export_button(self) -> None:
        """Inject the GeoJSON export button as a Leaflet control."""
        cfg = self._export_button_config
        assert cfg is not None
        map_var = self._map.get_name()
        geojson_str = json.dumps(self._build_geojson_collection())
        label = cfg["label"]
        filename = cfg["filename"]
        position = cfg["position"]

        script = (
            "<script>\n"
            "document.addEventListener('DOMContentLoaded', function() {\n"
            f"    var map = window['{map_var}'];\n"
            "    if (!map) return;\n"
            f"    var _exportData = {geojson_str};\n"
            f"    var exportControl = L.control({{position: '{position}'}});\n"
            "    exportControl.onAdd = function() {\n"
            "        var div = L.DomUtil.create('div', 'leaflet-bar');\n"
            "        var btn = L.DomUtil.create('a', '', div);\n"
            f"        btn.innerHTML = '{label}';\n"
            "        btn.href = '#';\n"
            "        btn.style.cssText = 'display:block;padding:5px 12px;background:#1e90ff;color:#fff;' +\n"
            "            'text-decoration:none;font-weight:bold;font-size:13px;cursor:pointer;' +\n"
            "            'width:auto;height:auto;line-height:normal;white-space:nowrap;';\n"
            "        btn.onclick = function(e) {\n"
            "            e.preventDefault();\n"
            "            e.stopPropagation();\n"
            "            var blob = new Blob([JSON.stringify(_exportData, null, 2)], {type: 'application/json'});\n"
            "            var url = URL.createObjectURL(blob);\n"
            "            var a = document.createElement('a');\n"
            "            a.href = url;\n"
            f"            a.download = '{filename}';\n"
            "            a.click();\n"
            "            URL.revokeObjectURL(url);\n"
            "        };\n"
            "        L.DomEvent.disableClickPropagation(div);\n"
            "        return div;\n"
            "    };\n"
            "    exportControl.addTo(map);\n"
            "});\n"
            "</script>\n"
        )
        self._map.get_root().html.add_child(folium.Element(script))  # ty: ignore[unresolved-attribute]

    @overload
    def to_image(
        self, path: None = None, width: int = 1200, height: int = 800, delay: float = 0.50, hide_controls: bool = True, scale: float = 1.0
    ) -> bytes: ...

    @overload
    def to_image(
        self, path: str | Path, width: int = 1200, height: int = 800, delay: float = 0.50, hide_controls: bool = True, scale: float = 1.0
    ) -> Path: ...

    def to_image(
        self,
        path: str | Path | None = None,
        width: int = 1200,
        height: int = 800,
        delay: float = 0.50,
        hide_controls: bool = True,
        scale: float = 1.0,
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
        scale : float
            Output resolution multiplier. ``scale=2.0`` produces a 2× (high-DPI)
            image at ``width * 2`` × ``height * 2`` pixels. Defaults to ``1.0``.

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
                scale=scale,
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
        scale: float = 1.0,
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
        scale : float
            Output resolution multiplier. ``scale=2.0`` produces a 2× (high-DPI) image.

        Returns
        -------
        io.BytesIO
            Buffer at position 0.
        """
        png = self.to_image(path=None, width=width, height=height, delay=delay, hide_controls=hide_controls, scale=scale)
        buf = io.BytesIO(png)
        buf.seek(0)
        return buf

    async def to_image_async(
        self,
        path: str | Path | None = None,
        width: int = 1200,
        height: int = 800,
        delay: float = 2.0,
        hide_controls: bool = True,
        scale: float = 1.0,
    ) -> bytes | Path:
        """Async PNG export (runs Selenium in executor).

        Parameters
        ----------
        path, width, height, delay, hide_controls, scale
            See ``to_image``.

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
                scale=scale,
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
