"""Style resolution utilities."""

from typing import Any

from mapyta.config import CircleStyle, FillStyle, StrokeStyle


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
