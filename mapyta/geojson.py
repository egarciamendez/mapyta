"""GeoJSON input loading utilities."""

import json
from pathlib import Path


def load_geojson_input(data: dict | str | Path) -> dict:
    """Parse a GeoJSON input to a dict.

    Accepts a ``dict`` (returned as-is), a ``Path``, or a ``str`` that is
    either a file path or a raw JSON string.

    Parameters
    ----------
    data : dict | str | Path
        GeoJSON as dict, JSON string, or file path.

    Returns
    -------
    dict
        Parsed GeoJSON dict.
    """
    if isinstance(data, dict):
        return data
    if isinstance(data, Path):
        return json.loads(data.read_text("utf-8"))
    # str: try as file path first (only short strings), otherwise parse as JSON
    if len(data) < 500 and not data.lstrip().startswith(("{", "[")):
        path = Path(data)
        return json.loads(path.read_text("utf-8")) if path.exists() else json.loads(data)
    return json.loads(data)
