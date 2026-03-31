"""Coordinate system detection and transformation utilities."""

from typing import cast

from pyproj import Transformer
from shapely.geometry import (
    LinearRing,
    LineString,
    MultiLineString,
    MultiPoint,
    MultiPolygon,
    Point,
    Polygon,
)
from shapely.geometry.base import BaseGeometry


def detect_and_transform_coords(
    coords: list[tuple[float, ...]],
    source_crs: str | None = None,
) -> list[tuple[float, float]]:
    """Detect coordinate system and transform to WGS84 if necessary.

    Auto-detects RD New (EPSG:28992) based on coordinate ranges.

    Parameters
    ----------
    coords : list[tuple[float, ...]]
        Input coordinate tuples as ``(x, y)``.
    source_crs : str | None
        Explicit source CRS (e.g. ``"EPSG:28992"``). Auto-detects if ``None``.

    Returns
    -------
    list[tuple[float, float]]
        Coordinates in WGS84 ``(longitude, latitude)``.
    """
    if not coords:
        return []

    sample_x, sample_y = coords[0][0], coords[0][1]

    if source_crs is None:
        # Auto-detect RD New: x ~ 0-300k, y ~ 300k-625k
        if 0 < sample_x < 300_000 and 300_000 < sample_y < 625_000:
            source_crs = "EPSG:28992"
        else:
            return [(c[0], c[1]) for c in coords]

    if source_crs and source_crs != "EPSG:4326":
        transformer = Transformer.from_crs(source_crs, "EPSG:4326", always_xy=True)
        return [transformer.transform(c[0], c[1]) for c in coords]

    return [(c[0], c[1]) for c in coords]


def transform_geometry(geom: BaseGeometry, source_crs: str | None = None) -> BaseGeometry:  # noqa: PLR0911
    """Transform a Shapely geometry to WGS84.

    Parameters
    ----------
    geom : BaseGeometry
        Input geometry in any supported CRS.
    source_crs : str | None
        Source CRS. If ``None``, auto-detection is attempted.

    Returns
    -------
    BaseGeometry
        Geometry in WGS84 coordinates.
    """
    if isinstance(geom, Point):
        coords = detect_and_transform_coords([(geom.x, geom.y)], source_crs)
        return Point(coords[0])
    if isinstance(geom, LinearRing):
        # LinearRing is a subclass of LineString, check first
        coords = detect_and_transform_coords(list(geom.coords), source_crs)
        return LinearRing(coords)
    if isinstance(geom, LineString):
        coords = detect_and_transform_coords(list(geom.coords), source_crs)
        return LineString(coords)
    if isinstance(geom, Polygon):
        ext = detect_and_transform_coords(list(geom.exterior.coords), source_crs)
        holes = [detect_and_transform_coords(list(r.coords), source_crs) for r in geom.interiors]
        return Polygon(ext, holes)
    if isinstance(geom, MultiPoint):
        return MultiPoint([cast(Point, transform_geometry(g, source_crs)) for g in geom.geoms])
    if isinstance(geom, MultiPolygon):
        return MultiPolygon([cast(Polygon, transform_geometry(g, source_crs)) for g in geom.geoms])
    if isinstance(geom, MultiLineString):
        return MultiLineString([cast(LineString, transform_geometry(g, source_crs)) for g in geom.geoms])
    return geom
