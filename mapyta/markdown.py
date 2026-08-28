"""Markdown to HTML conversion and RawHTML utilities."""

import re
from html import escape

# Compiled once at import: :meth:`Map.add_points` renders one tooltip and one popup per
# point, so re's pattern-cache lookup on every substitution shows up in a bulk call.
_SAFE_SCHEME = re.compile(r"^(https?://|mailto:)", re.IGNORECASE)
_H4 = re.compile(r"^### (.+)$", re.MULTILINE)
_H3 = re.compile(r"^## (.+)$", re.MULTILINE)
_H2 = re.compile(r"^# (.+)$", re.MULTILINE)
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_ITALIC = re.compile(r"\*(.+?)\*")
_CODE = re.compile(r"`(.+?)`")
_LINK = re.compile(r"\[(.+?)\]\((.+?)\)")
_LIST_ITEM = re.compile(r"^- (.+)$", re.MULTILINE)
_LIST_BLOCK = re.compile(r"((?:<li>.*?</li>\s*)+)", re.DOTALL)
_LOOSE_NEWLINE = re.compile(r"(?<!>)\n(?!<)")


def sanitize_href(url: str) -> str:
    """Allow only safe URL schemes (http, https, mailto). Returns ``#`` otherwise."""
    stripped = url.strip()
    return stripped if _SAFE_SCHEME.match(stripped) else "#"


def markdown_to_html(md_text: str) -> str:
    """Convert a subset of Markdown to HTML for popups/tooltips.

    Supports ``**bold**``, ``*italic*``, backtick code, ``[links](url)``,
    headers (``#`` - ``###``), and unordered lists (``- item``).

    Parameters
    ----------
    md_text : str
        Markdown-formatted string.

    Returns
    -------
    str
        HTML string.
    """
    text = md_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # Headers
    text = _H4.sub(r"<h4>\1</h4>", text)
    text = _H3.sub(r"<h3>\1</h3>", text)
    text = _H2.sub(r"<h2>\1</h2>", text)

    # Bold, italic, code
    text = _BOLD.sub(r"<strong>\1</strong>", text)
    text = _ITALIC.sub(r"<em>\1</em>", text)
    text = _CODE.sub(r"<code>\1</code>", text)

    # Links
    text = _LINK.sub(lambda m: f'<a href="{sanitize_href(m.group(2))}" target="_blank">{m.group(1)}</a>', text)

    # Lists
    text = _LIST_ITEM.sub(r"<li>\1</li>", text)
    if "<li>" in text:
        text = _LIST_BLOCK.sub(r"<ul>\1</ul>", text)

    # Newlines (not after block elements)
    return _LOOSE_NEWLINE.sub("<br>", text)


class RawHTML(str):
    """String subclass that bypasses markdown-to-HTML conversion.

    Use this to pass pre-formatted HTML directly to ``tooltip`` or ``popup``
    parameters on any ``add_*`` method.

    Examples
    --------
    >>> from mapyta.markdown import RawHTML
    >>> html = RawHTML("<b>Bold</b> and <em>italic</em>")
    >>> m.add_point(Point(4.9, 52.37), tooltip=html)
    """

    __slots__ = ()


def render_text(value: str | RawHTML) -> str:
    """Convert a plain string from Markdown, or pass :class:`RawHTML` through verbatim."""
    return value if isinstance(value, RawHTML) else markdown_to_html(value)


def escape_text(value: str | RawHTML) -> str:
    """Escape a plain string, or pass :class:`RawHTML` through verbatim.

    The counterpart to :func:`render_text` for labels that take no Markdown — legend
    captions and swatch labels. Escaping keeps untrusted text from becoming active
    markup while :class:`RawHTML` still opts into inline markup such as ``<sub>``.
    """
    return value if isinstance(value, RawHTML) else escape(value)
