"""Markdown to HTML conversion and RawHTML utilities."""

import re


def sanitize_href(url: str) -> str:
    """Allow only safe URL schemes (http, https, mailto). Returns ``#`` otherwise."""
    stripped = url.strip()
    if re.match(r"^https?://", stripped, re.IGNORECASE) or re.match(r"^mailto:", stripped, re.IGNORECASE):
        return stripped
    return "#"


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
    text = re.sub(r"^### (.+)$", r"<h4>\1</h4>", text, flags=re.MULTILINE)
    text = re.sub(r"^## (.+)$", r"<h3>\1</h3>", text, flags=re.MULTILINE)
    text = re.sub(r"^# (.+)$", r"<h2>\1</h2>", text, flags=re.MULTILINE)

    # Bold, italic, code
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)

    # Links
    text = re.sub(r"\[(.+?)\]\((.+?)\)", lambda m: f'<a href="{sanitize_href(m.group(2))}" target="_blank">{m.group(1)}</a>', text)

    # Lists
    text = re.sub(r"^- (.+)$", r"<li>\1</li>", text, flags=re.MULTILINE)
    if "<li>" in text:
        text = re.sub(r"((?:<li>.*?</li>\s*)+)", r"<ul>\1</ul>", text, flags=re.DOTALL)

    # Newlines (not after block elements)
    return re.sub(r"(?<!>)\n(?!<)", "<br>", text)


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
