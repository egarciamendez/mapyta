"""Style configuration dataclasses for Mapyta."""

from dataclasses import dataclass, field
from typing import Any, Literal

from mapyta.tiles import TileProviderKey

DrawTool = Literal["marker", "polyline", "polygon", "rectangle", "circle"]
"""Valid drawing tool names for :meth:`~mapyta.map.Map.enable_draw`."""


@dataclass
class StrokeStyle:
    """Style for lines and polygon borders.

    Parameters
    ----------
    color : str
        CSS color string.
    weight : float
        Stroke width in pixels.
    opacity : float
        Stroke opacity, 0.0 - 1.0.
    dash_array : str | None
        SVG dash-array, e.g. ``"5 10"``.
    """

    color: str = "#3388ff"
    weight: float = 3.0
    opacity: float = 1.0
    dash_array: str | None = None


@dataclass
class FillStyle:
    """Style for polygon fills.

    Parameters
    ----------
    color : str
        Fill CSS color.
    opacity : float
        Fill opacity, 0.0 - 1.0.
    """

    color: str = "#3388ff"
    opacity: float = 0.2


@dataclass
class PopupStyle:
    """Popup appearance configuration.

    Parameters
    ----------
    width : int
        IFrame width in pixels.
    height : int
        IFrame height in pixels.
    max_width : int
        Maximum popup width in pixels.
    """

    width: int = 300
    height: int = 150
    max_width: int = 300


@dataclass
class TooltipStyle:
    """Tooltip appearance configuration.

    Parameters
    ----------
    sticky : bool
        Whether the tooltip follows the mouse cursor.
    style : str | None
        Inline CSS style string for the tooltip container.
        Example: ``"font-size:14px; background-color:#fff;"``
    """

    sticky: bool = True
    style: str | None = None


@dataclass
class CircleStyle:
    """Style for circle markers (fixed pixel size).

    Parameters
    ----------
    radius : float
        Circle radius in pixels.
    stroke : StrokeStyle
        Border stroke style.
    fill : FillStyle
        Fill style.
    """

    radius: float = 8.0
    stroke: StrokeStyle = field(default_factory=StrokeStyle)
    fill: FillStyle = field(default_factory=FillStyle)


@dataclass
class HeatmapStyle:
    """Configuration for heatmap layers.

    Parameters
    ----------
    radius : int
        Radius of each location in pixels.
    blur : int
        Blur radius in pixels.
    min_opacity : float
        Minimum heatmap opacity.
    max_zoom : int
        Zoom at which points reach full intensity.
    gradient : dict[float, str] | None
        Custom gradient ``{stop: color}``.
    """

    radius: int = 15
    blur: int = 10
    min_opacity: float = 0.3
    max_zoom: int = 18
    gradient: dict[float, str] | None = None


@dataclass
class MapConfig:
    """Global map configuration.

    Parameters
    ----------
    tile_layer : TileProviderKey | str | list[TileProviderKey | str]
        Built-in provider key (e.g. ``"cartodb_positron"``) or a raw tile
        URL string.  Pass a list to add multiple base layers (use
        :meth:`Map.add_layer_control` to toggle between them).
        Built-in keys are auto-completed by IDEs; arbitrary URLs are also
        accepted as an escape hatch.
    zoom_start : int
        Initial zoom level.
    min_zoom : int
        Minimum zoom level, preventing users from zooming out beyond this
        level.  Lower values allow viewing larger areas like continents.
        Useful for bounding maps to specific regions.
    max_zoom : int
        Maximum zoom level, limiting how far users can zoom in.  Higher
        values enable more detailed views, but effectiveness depends on
        the tile provider (e.g. OpenStreetMap maxes at 19).  Exceeding
        the provider's limit may show blank tiles unless
        ``max_native_zoom`` is also set.
    max_native_zoom : int | None
        Highest zoom level at which the tile provider actually serves
        tiles.  When set below ``max_zoom``, Leaflet keeps the last
        native-resolution tile visible (upscaled, so it blurs) instead
        of rendering blank placeholders.  ``None`` (default) means
        Leaflet will request tiles at every zoom level up to
        ``max_zoom``, which can produce blank or gray tiles if the
        provider does not serve them.
    attribution : str | None
        Custom tile attribution.
    width : str | int
        Map width.
    height : str | int
        Map height.
    control_scale : bool
        Show scale bar.
    fullscreen : bool
        Add fullscreen button.
    minimap : bool
        Add minimap inset.
    measure_control : bool
        Add measure tool.
    mouse_position : bool
        Show cursor coordinates.
    mouse_position_crs : str | None
        EPSG code for the CRS displayed in the mouse-position control,
        e.g. ``"EPSG:28992"`` for Dutch RD New. ``None`` shows WGS84 lat/lng.
    mouse_position_proj4_def : str | None
        Proj4 definition string for *mouse_position_crs*. Only required
        for CRS codes not in the built-in registry. Ignored when
        *mouse_position_crs* is ``None``.
    """

    tile_layer: TileProviderKey | str | list[TileProviderKey | str] = "cartodb_positron"
    zoom_start: int = 12
    min_zoom: int = 0
    max_zoom: int = 19
    max_native_zoom: int | None = None
    attribution: str | None = None
    width: str | int = "100%"
    height: str | int = "100%"
    control_scale: bool = True
    fullscreen: bool = False
    minimap: bool = False
    measure_control: bool = False
    mouse_position: bool = True
    mouse_position_crs: str | None = None
    mouse_position_proj4_def: str | None = None


class RawJS:
    """Marker for raw JavaScript that should not be escaped.

    Parameters
    ----------
    js : str
        JavaScript function expression that accepts one argument
        (a GeoJSON FeatureCollection).
    """

    def __init__(self, js: str) -> None:
        self.js = js

    def __repr__(self) -> str:  # noqa: D105
        return f"RawJS({self.js[:50]!r}{'...' if len(self.js) > 50 else ''})"


@dataclass
class DrawConfig:
    """Configuration for Leaflet.draw drawing controls.

    Parameters
    ----------
    tools : list[DrawTool]
        Active drawing tools: ``"marker"``, ``"polyline"``, ``"polygon"``,
        ``"rectangle"``, ``"circle"``.
    on_submit : str | RawJS | None
        Callback on submit. ``None`` = download, URL = fetch,
        string = function name, ``RawJS`` = inline JS.
    position : str
        Toolbar position.
    submit_label : str
        Submit button text.
    draw_style : dict[str, Any] | None
        ``shapeOptions`` override for drawn shapes.
    edit : bool
        Whether edit/delete controls are active.
    """

    tools: list[DrawTool] = field(default_factory=lambda: ["polyline", "polygon", "marker"])
    on_submit: str | RawJS | None = None
    position: str = "topleft"
    submit_label: str = "Submit"
    draw_style: dict[str, Any] | None = None
    edit: bool = True
