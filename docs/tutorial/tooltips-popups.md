# Tooltips & Popups

Tooltips appear on hover; popups appear on click. Both accept Markdown, raw HTML, or nothing at all.

## Markdown content

```python exec="true" html="true" source="tabbed-right"
from shapely.geometry import Point
from mapyta import Map, PopupStyle

m = Map(title="Custom Popups")

m.add_point(
    point=Point(4.9041, 52.3676),
    marker="📋",
    tooltip="**Amsterdam**\n*Hover tooltip*",
    popup="**Amsterdam**\n\nPopulation: 872,680\nProvince: North Holland\nFounded: 1275",
    popup_style=PopupStyle(width=300, height=150),
)

print(m.to_html()) # markdown-exec: hide
```

**`popup_style`** controls popup size. `PopupStyle` has three fields: `width` (IFrame width in px), `height` (IFrame height in px), and `max_width`. You can also pass a plain dict: `popup_style={"width": 300, "height": 150}`.

## Raw HTML

When Markdown isn't enough — styled tables, colored text, embedded images — wrap your string in `RawHTML` to bypass conversion entirely.

```python exec="true" html="true" source="tabbed-right"
from shapely.geometry import Point
from mapyta import Map, RawHTML, PopupStyle

m = Map(title="Raw HTML Popup")

table_html = RawHTML("""
<table style="border-collapse:collapse;width:100%;">
  <tr style="background:#3498db;color:white;">
    <th style="padding:6px;">Property</th>
    <th style="padding:6px;">Value</th>
  </tr>
  <tr><td style="padding:4px;">Name</td><td style="padding:4px;">Amsterdam</td></tr>
  <tr style="background:#f0f0f0;"><td style="padding:4px;">Population</td><td style="padding:4px;">872,680</td></tr>
  <tr><td style="padding:4px;">Province</td><td style="padding:4px;">North Holland</td></tr>
</table>
""")

m.add_point(
    Point(4.9041, 52.3676),
    marker="📊",
    tooltip=RawHTML("<b>Amsterdam</b><br>click for details"),
    popup=table_html,
    popup_style=PopupStyle(width=320, height=160),
)

print(m.to_html()) # markdown-exec: hide
```

**`RawHTML`** is a `str` subclass — it works anywhere a regular string does. The difference is that Map skips the Markdown-to-HTML conversion step, so your `<table>`, `<img>`, and `<style>` tags pass through untouched.

!!! tip

    `RawHTML` works on both `tooltip` and `popup` parameters across all `add_*` methods.
