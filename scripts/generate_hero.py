"""Generate the README hero image.

Renders the "Amsterdam Overview" example to a PNG and writes it to
``docs/_overrides/assets/images/hero-map.png`` — the path the README points at.

Requires a machine with internet access (so the map tiles load) and the
``export`` extra, which brings in Selenium and drives a headless
Chromium-based browser:

    uv run --extra export python scripts/generate_hero.py
    # or, with pip:
    pip install "mapyta[export]"
    python scripts/generate_hero.py

After running, commit the generated PNG and uncomment the hero block in
``README.md``.
"""

from pathlib import Path

from shapely.geometry import LineString, Point, Polygon

from mapyta import Map, MapConfig

OUTPUT = Path(__file__).resolve().parents[1] / "docs" / "_overrides" / "assets" / "images" / "hero-map.png"


def build_map() -> Map:
    """Build the Amsterdam overview map shown on the docs home page."""
    m = Map(
        title="Amsterdam Overview",
        config=MapConfig(tile_layer="cartodb_positron"),
    )

    m.create_feature_group("🏛️ Landmarks")
    m.add_point(Point(4.9041, 52.3676), marker="🏛️", tooltip="**Royal Palace**")
    m.add_point(Point(4.8834, 52.3667), marker="📖", tooltip="**Anne Frank House**")
    m.add_point(
        Point(4.8795, 52.3600),
        marker="fa-landmark",
        tooltip="**Rijksmuseum**",
        marker_style={"font-size": "24px", "color": "green"},
    )

    m.create_feature_group("📍 Areas of Interest")
    m.add_polygon(
        Polygon([(4.876, 52.372), (4.889, 52.372), (4.889, 52.380), (4.876, 52.380)]),
        tooltip="**De Jordaan**",
        stroke={"color": "green", "weight": 2},
        fill={"color": "blue", "opacity": 0.15},
    )
    m.add_linestring(
        LineString([(4.8852, 52.3702), (4.8910, 52.3663), (4.8932, 52.3631), (4.884, 52.3569)]),
        tooltip="**Walking route**",
        stroke={"color": "red", "weight": 4, "dash_array": "10 6"},
    )

    m.reset_target()
    m.add_circle(
        Point(4.8812, 52.3584),
        tooltip="**Van Gogh Museum**",
        style={"radius": 12, "stroke": {"color": "green", "weight": 2}, "fill": {"color": "orange", "opacity": 0.5}},
    )
    m.set_bounds(padding=0.005)
    return m


def main() -> None:
    """Render the hero map and write it to the assets directory."""
    m = build_map()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    m.to_image(OUTPUT, width=1200, height=700, delay=3.0, scale=2.0)
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
