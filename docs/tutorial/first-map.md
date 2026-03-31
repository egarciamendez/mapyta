# Your First Map

Let's start with the absolute minimum, a single point on a map, exported to HTML.

```python exec="true" html="true" source="tabbed-right"
from shapely.geometry import Point
from mapyta import Map

m = Map(title="Hello Utrecht")
m.add_point(
    point=Point(5.121311, 52.090648),
    tooltip="**Utrecht**",
    popup="**Utrecht**\n THe most beatiful Dutch city :-)\nPopulation: ~350k",
    caption="UTR",
)

m.to_html("hello.html")

print(m.to_html()) # markdown-exec: hide
```

Open `hello.html` and you'll see an interactive OpenStreetMap centered on Amsterdam. Hover over the marker and you get a bold "Amsterdam" tooltip. Click it and a popup appears.

## How it works

**`Map(title="Hello Amsterdam")`** creates a new map. The `title` shows as a floating label at the top. You didn't pass a `center`, that's fine. Map auto-fits the viewport to whatever geometries you add.

**`add_point()`** takes a Shapely `Point(longitude, latitude)`. The `tooltip` parameter accepts Markdown, so `**Amsterdam**` renders as bold text.

**`caption`** places a small text label just below the marker.

**`to_html()`** writes a standalone HTML file. No server needed, just open it in a browser. Call it without a path to get the HTML as a string instead.

!!! tip "Fluent chaining"

    Every `add_*` method returns `self`, so you can chain calls:

    ```python exec="true" html="true" source="tabbed-left"
    from shapely.geometry import Point
    from mapyta import Map

    m = Map(title="Chained")
    m.add_point(Point(5.1218, 52.09334), marker="📍").add_point(Point(5.1, 52.09), marker="🏠").to_html("chained.html")

    print(m.to_html()) # markdown-exec: hide
    ```
