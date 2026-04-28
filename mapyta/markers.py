"""Marker building utilities."""

from typing import Literal

import folium

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


def _absolute_caption_html(
    text: str,
    css: dict[str, str],
    top_px: int,
    element_id: str | None = None,
) -> str:
    """Build a caption pinned to the horizontal center of its parent.

    The caption is rendered as an absolutely-positioned ``<div>`` so its
    own midpoint is anchored at ``left:50%`` of the parent, regardless of
    how wide the caption text grows.  The caller is responsible for
    giving the parent ``position:relative`` and ``overflow:visible``.

    Parameters
    ----------
    text : str
        Caption text.
    css : dict[str, str]
        CSS property overrides merged onto :data:`DEFAULT_CAPTION_CSS`.
    top_px : int
        Vertical offset, in pixels, from the parent's top edge to the
        caption's top edge.  Typically the glyph height plus a small gap.
    element_id : str | None
        Optional DOM ``id`` on the caption ``<div>``, used by
        zoom-dependent visibility JS to target the caption independently
        of its marker.

    Returns
    -------
    str
        HTML ``<div>`` string.
    """
    merged = {
        **DEFAULT_CAPTION_CSS,
        **css,
        "position": "absolute",
        "left": "50%",
        "top": f"{top_px}px",
        "transform": "translateX(-50%)",
    }
    # When zoom-gated (element_id set), start hidden so the caption doesn't
    # flash before the zoom JS runs its first visibility check.
    if element_id:
        merged["display"] = "none"
    id_attr = f' id="{element_id}"' if element_id else ""
    return f'<div{id_attr} style="{css_to_style(merged)}">{text}</div>'


def _marker_wrapper_html(inner_html: str, width: int, height: int) -> str:
    """Build the flex-centred outer wrapper shared by both marker builders.

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
        f'overflow:visible;line-height:1;">{inner_html}</div>'
    )


def build_icon_marker(
    icon: str,
    css: dict[str, str],
    caption: str | None,
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
    caption : str | None
        Optional caption text below the icon.
    caption_css : dict[str, str]
        CSS property overrides for the caption.
    caption_id : str | None
        Optional DOM ``id`` on the caption ``<div>``, used by zoom-dependent
        visibility JS to target the caption independently of its marker.

    Returns
    -------
    folium.DivIcon
    """
    merged = {**DEFAULT_ICON_CSS, **css}
    style_str = css_to_style(merged)
    # Full CSS class string (contains a space) → use as-is
    # Bare name starting with "fa-" → FontAwesome 6 (fa-solid prefix)
    # Other bare name → Glyphicon
    if " " in icon:
        icon_class = icon
    elif icon.startswith("fa-"):
        icon_class = f"fa-solid {icon}"
    else:
        icon_class = f"glyphicon glyphicon-{icon}"
    fs = px_to_int(merged.get("font-size", "20px"), 20)
    glyph_html = f'<i class="{icon_class}" style="{style_str};line-height:1;vertical-align:top;"></i>'
    caption_html = _absolute_caption_html(caption, caption_css, top_px=fs + 2, element_id=caption_id) if caption else ""
    w = fs
    h = fs
    html = _marker_wrapper_html(f"{glyph_html}{caption_html}", w, h)
    return folium.DivIcon(
        html=html,
        icon_size=(w, h),
        icon_anchor=(w // 2, h // 2),
    )


def build_text_marker(
    text: str,
    css: dict[str, str],
    caption: str | None,
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
    caption : str | None
        Optional caption text below the text.
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
    merged = {**DEFAULT_TEXT_CSS, **css}
    style_str = css_to_style(merged) + ";text-align:center;line-height:1"
    fs = px_to_int(merged.get("font-size", "16px"), 16)
    glyph_html = f'<div style="{style_str}">{text}</div>'
    caption_html = _absolute_caption_html(caption, caption_css, top_px=fs + 2, element_id=caption_id) if caption else ""
    w = fs + 10
    h = fs + 10
    html = _marker_wrapper_html(f"{glyph_html}{caption_html}", w, h)
    return folium.DivIcon(
        html=html,
        icon_size=(w, h),
        icon_anchor=(w // 2, h // 2),
    )
