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


def caption_html(text: str, css: dict[str, str]) -> str:
    """Build an HTML snippet for a caption below a marker icon.

    Parameters
    ----------
    text : str
        Caption text.
    css : dict[str, str]
        CSS property dict merged with appropriate defaults by the caller.

    Returns
    -------
    str
        HTML ``<div>`` string.
    """
    merged = {**DEFAULT_CAPTION_CSS, **css}
    return f'<div style="{css_to_style(merged)}">{text}</div>'


def build_icon_marker(
    icon: str,
    css: dict[str, str],
    caption: str | None,
    caption_css: dict[str, str],
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

    Returns
    -------
    folium.DivIcon
    """
    merged = {**DEFAULT_ICON_CSS, **css}
    style_str = css_to_style(merged)
    caption_suffix = caption_html(caption, caption_css) if caption else ""
    # Full CSS class string (contains a space) → use as-is
    # Bare name starting with "fa-" → FontAwesome 6 (fa-solid prefix)
    # Other bare name → Glyphicon
    if " " in icon:
        icon_class = icon
    elif icon.startswith("fa-"):
        icon_class = f"fa-solid {icon}"
    else:
        icon_class = f"glyphicon glyphicon-{icon}"
    fs = int(merged.get("font-size", "20px").replace("px", ""))
    icon_html = (
        f'<div style="text-align:center;line-height:1;height:{fs}px;">'
        f'<i class="{icon_class}" style="{style_str};line-height:1;vertical-align:top;"></i>'
        f"</div>"
        f"{caption_suffix}"
    )
    h_icon = fs
    w = max(fs, 100 if caption else fs)
    h = h_icon + (20 if caption else 0)
    return folium.DivIcon(
        html=icon_html,
        icon_size=(w, h),
        icon_anchor=(w // 2, h_icon // 2),
    )


def build_text_marker(
    text: str,
    css: dict[str, str],
    caption: str | None,
    caption_css: dict[str, str],
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

    Returns
    -------
    folium.DivIcon
        A DivIcon rendering the text and optional caption.
    """
    merged = {**DEFAULT_TEXT_CSS, **css}
    style_str = css_to_style(merged) + ";text-align:center"
    caption_suffix = caption_html(caption, caption_css) if caption else ""
    inner = f'<div style="{style_str}">{text}</div>'
    html = f'<div style="text-align:center;">{inner}{caption_suffix}</div>'
    # size estimation for icon_size/anchor from font-size
    fs = int(merged.get("font-size", "16px").replace("px", ""))
    w = max(fs + 10, 100 if caption else 0)
    h = fs + 10 + (20 if caption else 0)
    return folium.DivIcon(
        html=html,
        icon_size=(w, h),
        icon_anchor=(w // 2, (fs + 10) // 2),
    )
