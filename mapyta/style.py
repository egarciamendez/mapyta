"""Style resolution utilities."""

from typing import Any

from mapyta.config import CircleStyle, FillStyle, StrokeStyle

#: Named color palettes for choropleths and GeoDataFrame color columns.
#: Each palette is a list of hex color strings ordered from low to high values.
PALETTES: dict[str, list[str]] = {
    "ylrd": ["#ffffb2", "#fecc5c", "#fd8d3c", "#f03b20", "#bd0026"],
    "blues": ["#eff3ff", "#bdd7e7", "#6baed6", "#2171b5", "#084594"],
    "greens": ["#edf8e9", "#bae4b3", "#74c476", "#31a354", "#006d2c"],
    "reds": ["#fee5d9", "#fcae91", "#fb6a4a", "#de2d26", "#a50f15"],
    "purples": ["#f2f0f7", "#cbc9e2", "#9e9ac8", "#756bb1", "#54278f"],
    "oranges": ["#feedde", "#fdbe85", "#fd8d3c", "#e6550d", "#a63603"],
    "viridis": ["#440154", "#31688e", "#35b779", "#fde725", "#fde725"],
    "plasma": ["#0d0887", "#7e03a8", "#cc4778", "#f89540", "#f0f921"],
    "spectral": ["#d7191c", "#fdae61", "#ffffbf", "#abdda4", "#2b83ba"],
    "rdylgn": ["#d7191c", "#fdae61", "#ffffbf", "#a6d96a", "#1a9641"],
}


def resolve_style(value: Any, cls: type) -> Any:  # noqa: ANN401
    """Convert a dict to a style dataclass instance, or return as-is.

    Supports nested dicts for composite styles like ``CircleStyle``.

    Parameters
    ----------
    value : Any
        ``None``, a style dataclass instance, or a ``dict`` of keyword arguments.
    cls : type
        The target style dataclass (e.g. ``StrokeStyle``, ``CircleStyle``).

    Returns
    -------
    Any
        ``None`` if *value* is ``None``, the original instance if already the
        correct type, or a newly constructed ``cls(**value)`` from a dict.
    """
    if value is None or isinstance(value, cls):
        return value
    if isinstance(value, dict):
        kwargs = dict(value)
        if cls is CircleStyle:
            if isinstance(kwargs.get("stroke"), dict):
                kwargs["stroke"] = StrokeStyle(**kwargs["stroke"])
            if isinstance(kwargs.get("fill"), dict):
                kwargs["fill"] = FillStyle(**kwargs["fill"])
        return cls(**kwargs)
    return value
