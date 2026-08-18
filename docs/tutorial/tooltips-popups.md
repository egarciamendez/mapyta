# Tooltips & Popups

Tooltips appear on hover; popups appear on click. Both accept Markdown, raw HTML, or nothing at all.

## Markdown content

```python exec="true" html="true" source="tabbed-right"
from shapely.geometry import Point
from mapyta import Map, PopupStyle

m = Map(title="Custom Popups")

m.add_point(
    point=Point(5.1213, 52.0908),
    marker="📋",
    tooltip="**Utrecht**\n*Hover tooltip*",
    popup="**Utrecht**\n\nPopulation: 361,924\nProvince: Utrecht\nFounded: 47 AD",
    popup_style=PopupStyle(width=300, height=150),
)

print(m.to_html()) # markdown-exec: hide
```

**`popup_style`** controls popup size. `PopupStyle` has four fields: `width` (IFrame width in px), `height` (IFrame height in px), `max_width`, and `use_iframe`. You can also pass a plain dict: `popup_style={"width": 300, "height": 150}`.

## Links out of a popup

Popup content lives in its own IFrame by default, which keeps the page CSS out of it and gives it a
fixed `width` x `height`. That IFrame is loaded from a `data:` URL, and browsers do not let such a
document navigate the page around it: a link with `target="_top"` renders but does nothing on click.

Set `use_iframe=False` to put the content straight into the popup. The link then works, and the
popup sizes itself to its content instead of to `width` x `height`.

```python
m.add_point(
    Point(5.1213, 52.0908),
    popup=RawHTML('<a href="/somewhere" target="_top">Open the detail page</a>'),
    popup_style=PopupStyle(use_iframe=False),
)
```

Only do this for content you trust, since it is no longer shielded from the surrounding page.

## Raw HTML

When Markdown isn't enough, styled tables, colored text, embedded images, wrap your string in `RawHTML` to bypass conversion entirely.

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
  <tr><td style="padding:4px;">Name</td><td style="padding:4px;">Utrecht</td></tr>
  <tr style="background:#f0f0f0;"><td style="padding:4px;">Population</td><td style="padding:4px;">361,924</td></tr>
  <tr><td style="padding:4px;">Province</td><td style="padding:4px;">Utrecht</td></tr>
</table>
""")

m.add_point(
    Point(5.1213, 52.0908),
    marker="📊",
    tooltip=RawHTML("<b>Utrecht</b><br>click for details"),
    popup=table_html,
    popup_style=PopupStyle(width=320, height=160),
)

print(m.to_html()) # markdown-exec: hide
```

**`RawHTML`** is a `str` subclass, it works anywhere a regular string does. The difference is that Map skips the Markdown-to-HTML conversion step, so your `<table>`, `<img>`, and `<style>` tags pass through untouched.

!!! tip

    `RawHTML` works on both `tooltip` and `popup` parameters across all `add_*` methods.

## Tooltip style

`TooltipStyle` controls the appearance of the tooltip box. Pass it to any `add_*` geometry method:

```python
from shapely.geometry import LineString, Polygon, Point
from mapyta import Map, TooltipStyle

m = Map()

m.add_point(
    Point(4.9, 52.37),
    tooltip="**Amsterdam**",
    tooltip_style=TooltipStyle(sticky=False, style="font-size: 14px; font-weight: bold;"),
)

m.add_linestring(
    LineString([(4.9, 52.37), (5.0, 52.38)]),
    tooltip="Route A → B",
    tooltip_style=TooltipStyle(sticky=True),
)

m.add_polygon(
    Polygon([(4.9, 52.3), (5.0, 52.3), (5.0, 52.4), (4.9, 52.4)]),
    tooltip="Zone",
    tooltip_style={"sticky": False, "style": "color: red;"},
)
```

`sticky=True` (default) means the tooltip follows the cursor. `sticky=False` pins the tooltip to the feature. The `style` field takes a raw CSS string applied to the tooltip container.
