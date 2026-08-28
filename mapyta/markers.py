"""Marker building utilities."""

import json
from typing import Literal, NamedTuple

import folium

from mapyta.config import PopupStyle, TooltipStyle
from mapyta.markdown import RawHTML, escape_text

# Default CSS for marker styles
DEFAULT_ICON_CSS: dict[str, str] = {
    "font-size": "20px",
    "color": "#002855",
}

DEFAULT_TEXT_CSS: dict[str, str] = {
    "font-size": "16px",
    "color": "black",
}

DEFAULT_CAPTION_CSS: dict[str, str] = {
    "font-size": "12px",
    "font-family": "Arial, sans-serif",
    "color": "#333333",
    "font-weight": "bold",
    "background-color": "rgba(255,255,255,0.8)",
    "border": "1px solid #cccccc",
    "padding": "2px 6px",
    "white-space": "nowrap",
    "text-align": "center",
}

# Caption style when used under a marker (transparent background, no border)
DEFAULT_MARKER_CAPTION_CSS: dict[str, str] = {
    **DEFAULT_CAPTION_CSS,
    "background-color": "transparent",
    "border": "none",
}


def css_to_style(css: dict[str, str]) -> str:
    """Convert a CSS property dict to an inline style string."""
    return ";".join(f"{k}:{v}" for k, v in css.items())


def px_to_int(value: str, default: int) -> int:
    """Convert a CSS length string like ``"12px"`` or ``"12.5px"`` to an int.

    Falls back to ``default`` for non-``px`` units (``"1em"``, ``"medium"``)
    and malformed values so icon size estimation never raises.
    """
    try:
        return int(float(value.strip().removesuffix("px")))
    except (ValueError, AttributeError):
        return default


def classify_marker(s: str) -> Literal["emoji", "icon_class", "icon_name"]:
    """Classify a marker string.

    Returns
    -------
    "emoji"
        Non-ASCII content (emojis, unicode symbols) → render as text.
    "icon_class"
        Full CSS class string containing a space (e.g. ``"fa fa-home"``) → use as-is.
    "icon_name"
        Bare icon name (e.g. ``"home"``, ``"fa-arrow-right"``) → auto-prefix.
    """
    if not s or not all(c.isascii() for c in s):
        return "emoji"
    if " " in s:
        return "icon_class"
    return "icon_name"


def resolve_icon_class(icon: str) -> str:
    """Resolve a marker icon name to its full CSS class.

    A string containing a space is already a class list and is used as-is; a bare
    ``"fa-"`` name gets the FontAwesome 6 ``fa-solid`` prefix, anything else Glyphicon's.
    """
    if " " in icon:
        return icon
    if icon.startswith("fa-"):
        return f"fa-solid {icon}"
    return f"glyphicon glyphicon-{icon}"


class MarkerGlyph(NamedTuple):
    """A marker glyph's HTML, split at the end of its caller-supplied ``style`` value.

    :meth:`Map.add_points` splices a per-point colour between the two halves — a later
    declaration wins in an inline style attribute — so its JavaScript factory carries the
    shared markup once instead of once per point.
    """

    open_html: str
    close_html: str
    box_size: int
    caption_top: int


def icon_glyph(icon: str, css: dict[str, str]) -> MarkerGlyph:
    """Build the ``<i>`` glyph for an icon marker."""
    merged = {**DEFAULT_ICON_CSS, **css}
    fs = px_to_int(merged.get("font-size", "20px"), 20)
    return MarkerGlyph(
        f'<i class="{resolve_icon_class(icon)}" style="{css_to_style(merged)}',
        ';line-height:1;vertical-align:top;"></i>',
        box_size=fs,
        caption_top=fs + 2,
    )


def text_glyph(text: str, css: dict[str, str]) -> MarkerGlyph:
    """Build the ``<div>`` glyph for a text or emoji marker."""
    merged = {**DEFAULT_TEXT_CSS, **css}
    fs = px_to_int(merged.get("font-size", "16px"), 16)
    return MarkerGlyph(
        f'<div style="{css_to_style(merged)};text-align:center;line-height:1',
        f'">{text}</div>',
        box_size=fs + 10,
        caption_top=fs + 2,
    )


def marker_glyph(marker: str | None, css: dict[str, str]) -> MarkerGlyph:
    """Classify *marker* and build its glyph, falling back to the ``arrow-down`` icon."""
    if marker and classify_marker(marker) == "emoji":
        return text_glyph(marker, css)
    return icon_glyph(marker or "arrow-down", css)


def caption_open_tag(
    css: dict[str, str],
    top_px: int,
    element_id: str | None = None,
    class_name: str | None = None,
) -> str:
    """Open a caption ``<div>`` pinned to the horizontal center of its parent.

    Anchoring the div's own midpoint at ``left:50%`` keeps it centred however wide the
    text grows; the caller must give the parent ``position:relative`` and
    ``overflow:visible``.  ``element_id`` targets one caption from the zoom-visibility
    JS, ``class_name`` a whole bulk layer's captions at once; either makes the caption
    zoom-gated, so it starts hidden rather than flashing before that JS first runs.

    Parameters
    ----------
    css : dict[str, str]
        CSS property overrides merged onto :data:`DEFAULT_CAPTION_CSS`.
    top_px : int
        Vertical offset, in pixels, from the parent's top edge to the caption's top
        edge.  Typically the glyph height plus a small gap.
    element_id, class_name : str | None
        DOM ``id`` / ``class`` for zoom-dependent visibility. Mutually exclusive.

    Returns
    -------
    str
        The opening ``<div ...>`` tag; the caller supplies the text and ``</div>``.
    """
    merged = {
        **DEFAULT_CAPTION_CSS,
        **css,
        "position": "absolute",
        "left": "50%",
        "top": f"{top_px}px",
        "transform": "translateX(-50%)",
    }
    if element_id or class_name:
        merged["display"] = "none"
    attr = f' id="{element_id}"' if element_id else (f' class="{class_name}"' if class_name else "")
    return f'<div{attr} style="{css_to_style(merged)}">'


def marker_wrapper_open(width: int, height: int) -> str:
    """Open the flex-centred outer wrapper shared by every marker path.

    Sized to match the DivIcon's ``icon_size`` and uses flex centring so the
    glyph's visual centre coincides with ``icon_anchor`` regardless of the
    FontAwesome viewBox aspect ratio (e.g. ``fa-xmark`` is 0.75em wide).
    Captions are nested inside this wrapper (not siblings) so click/hover
    events bubble up to the Leaflet marker even though they render outside
    ``icon_size`` via ``overflow:visible``.
    """
    return (
        f'<div style="position:relative;display:flex;align-items:center;'
        f"justify-content:center;width:{width}px;height:{height}px;"
        f'overflow:visible;line-height:1;">'
    )


def _build_marker(glyph: MarkerGlyph, caption: str | RawHTML | None, caption_css: dict[str, str], caption_id: str | None) -> folium.DivIcon:
    """Assemble a glyph and its optional caption into a square DivIcon.

    The caption goes into the DivIcon's HTML, so a plain string is escaped: a label taken
    from a data source would otherwise become active markup. ``RawHTML`` opts back in.
    """
    caption_html = f"{caption_open_tag(caption_css, glyph.caption_top, element_id=caption_id)}{escape_text(caption)}</div>" if caption else ""
    size = glyph.box_size
    return folium.DivIcon(
        html=f"{marker_wrapper_open(size, size)}{glyph.open_html}{glyph.close_html}{caption_html}</div>",
        icon_size=(size, size),
        icon_anchor=(size // 2, size // 2),
    )


def build_marker(
    marker: str | None,
    css: dict[str, str],
    caption: str | RawHTML | None,
    caption_css: dict[str, str],
    caption_id: str | None = None,
) -> folium.DivIcon:
    """Build the DivIcon for *marker*, classified as icon or text/emoji by :func:`marker_glyph`.

    Parameters
    ----------
    marker : str | None
        Icon name, full CSS class string, or emoji/text.  ``None`` falls back to the
        default ``arrow-down`` icon.
    css : dict[str, str]
        CSS property overrides for the glyph element.
    caption : str | RawHTML | None
        Optional caption text below the glyph.  Escaped as on :func:`build_icon_marker`.
    caption_css : dict[str, str]
        CSS property overrides for the caption.
    caption_id : str | None
        Optional DOM ``id`` on the caption ``<div>``, used by zoom-dependent
        visibility JS to target the caption independently of its marker.

    Returns
    -------
    folium.DivIcon
    """
    return _build_marker(marker_glyph(marker, css), caption, caption_css, caption_id)


def point_layer_js(
    marker: str | None,
    marker_css: dict[str, str],
    caption_css: dict[str, str],
    caption_class: str | None,
    tooltip: TooltipStyle,
    popup: PopupStyle,
) -> str:
    """Build the browser-side ``onEachFeature`` factory used by :meth:`Map.add_points`.

    The JavaScript counterpart of :func:`build_marker`: same wrapper, same glyph, same
    caption nested inside, assembled per point in the browser instead of per point in
    Python.  Both live here so the two renderings of one marker cannot drift apart.

    Every constant — the wrapper div, the glyph markup, the caption CSS — is written into
    the function once, so a feature carries only what genuinely differs between points.
    Styling through Folium's ``style_function`` instead would defeat that: it compiles to a
    ``switch`` with one case per distinct style, putting the output back at O(n) bytes.
    """
    glyph = marker_glyph(marker, marker_css)
    size = glyph.box_size
    caption_open = caption_open_tag(caption_css, glyph.caption_top, class_name=caption_class)
    wrapper_open = marker_wrapper_open(size, size)
    tooltip_open = f'<div style="{tooltip.style}">' if tooltip.style else "<div>"

    return (
        "function(feature, layer) {"
        " var p = feature.properties;"
        " var color = p.color ? ';color:' + p.color : '';"
        f" var caption = p.caption ? {json.dumps(caption_open)} + p.caption + '</div>' : '';"
        f" layer.setIcon(L.divIcon({{html: {json.dumps(wrapper_open)} + {json.dumps(glyph.open_html)} + color"
        f" + {json.dumps(glyph.close_html)} + caption + '</div>', iconSize: [{size}, {size}],"
        f" iconAnchor: [{size // 2}, {size // 2}], className: 'empty'}}));"
        f" if (p.tooltip) {{ layer.bindTooltip({json.dumps(tooltip_open)} + p.tooltip + '</div>',"
        f" {{sticky: {json.dumps(tooltip.sticky)}}}); }}"
        f" if (p.popup) {{ layer.bindPopup(p.popup, {{maxWidth: {popup.max_width}}}); }}"
        "}"
    )


def build_icon_marker(
    icon: str,
    css: dict[str, str],
    caption: str | RawHTML | None,
    caption_css: dict[str, str],
    caption_id: str | None = None,
) -> folium.DivIcon:
    """Build an icon-based DivIcon marker with optional caption.

    Parameters
    ----------
    icon : str
        Icon name or full CSS class string.  Strings containing a space
        (e.g. ``"fa-solid fa-house"``) are used verbatim.  Bare names
        starting with ``"fa-"`` get an ``"fa-solid"`` prefix; other bare
        names (e.g. ``"home"``) get a ``"glyphicon"`` prefix.
    css : dict[str, str]
        CSS property overrides for the icon element.
    caption : str | RawHTML | None
        Optional caption text below the icon.  Plain strings are HTML-escaped
        and shown literally; wrap in :class:`~mapyta.markdown.RawHTML` to render
        inline markup such as ``<sub>``.
    caption_css : dict[str, str]
        CSS property overrides for the caption.
    caption_id : str | None
        Optional DOM ``id`` on the caption ``<div>``, used by zoom-dependent
        visibility JS to target the caption independently of its marker.

    Returns
    -------
    folium.DivIcon
    """
    return _build_marker(icon_glyph(icon, css), caption, caption_css, caption_id)


def build_text_marker(
    text: str,
    css: dict[str, str],
    caption: str | RawHTML | None,
    caption_css: dict[str, str],
    caption_id: str | None = None,
) -> folium.DivIcon:
    """Build a text/emoji DivIcon marker with optional caption.

    Parameters
    ----------
    text : str
        The actual text/emoji to render.
    css : dict[str, str]
        CSS property overrides for the text element.
    caption : str | RawHTML | None
        Optional caption text below the text.  Escaped as on
        :func:`build_icon_marker`.
    caption_css : dict[str, str]
        CSS property overrides for the caption.
    caption_id : str | None
        Optional DOM ``id`` on the caption ``<div>``, used by zoom-dependent
        visibility JS to target the caption independently of its marker.

    Returns
    -------
    folium.DivIcon
        A DivIcon rendering the text and optional caption.
    """
    return _build_marker(text_glyph(text, css), caption, caption_css, caption_id)
