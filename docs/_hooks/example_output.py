"""MkDocs hook that keeps files written by documentation examples out of the repository.

The tutorial examples end with calls like ``m.to_html("provincies.html")`` because that is exactly what a reader would write. Executed during the
build, those calls dropped dozens of stray HTML files into the working tree. This hook redirects every *relative* export path into a temporary
directory that is removed when the build finishes, so the examples keep showing realistic code while the repository stays clean.

Absolute paths are left untouched: passing one is a deliberate choice by whoever wrote the example.
"""

from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

import mapyta

if TYPE_CHECKING:
    from collections.abc import Callable

    from mkdocs.config.defaults import MkDocsConfig

#: Export methods whose first positional parameter is an output path.
EXPORT_METHODS = ("to_html", "to_geojson", "to_image")

logger = logging.getLogger("mkdocs.hooks.example_output")

_originals: dict[str, Callable[..., Any]] = {}
_scratch_dir: Path | None = None


def _redirect(path: str | Path) -> Path:
    """Map a relative export path into the scratch directory.

    Parameters
    ----------
    path
        The path an example asked to write to.

    Returns
    -------
    Path
        The original path when absolute, otherwise the same file name inside the scratch directory.
    """
    candidate = Path(path)
    if candidate.is_absolute() or _scratch_dir is None:
        return candidate
    target = _scratch_dir / candidate.name
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def _wrap(original: Callable[..., Any]) -> Callable[..., Any]:
    """Wrap an export method so relative paths land in the scratch directory.

    Parameters
    ----------
    original
        The unbound export method being replaced.

    Returns
    -------
    Callable[..., Any]
        A replacement method that rewrites its path argument.
    """

    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
        if args and args[0] is not None:
            return original(self, _redirect(args[0]), *args[1:], **kwargs)
        if kwargs.get("path") is not None:
            return original(self, *args, **{**kwargs, "path": _redirect(kwargs["path"])})
        return original(self, *args, **kwargs)

    return wrapper


def on_config(config: MkDocsConfig) -> MkDocsConfig:
    """Redirect example file exports into a temporary directory.

    Parameters
    ----------
    config
        The MkDocs configuration, passed through unchanged.

    Returns
    -------
    MkDocsConfig
        The unmodified MkDocs configuration.
    """
    global _scratch_dir  # noqa: PLW0603

    if _originals:
        return config

    _scratch_dir = Path(tempfile.mkdtemp(prefix="mapyta-docs-"))

    for name in EXPORT_METHODS:
        original = getattr(mapyta.Map, name, None)
        if original is None:
            continue
        _originals[name] = original
        setattr(mapyta.Map, name, _wrap(original))

    logger.info("Example exports redirected to %s", _scratch_dir)
    return config


def on_post_build(config: MkDocsConfig) -> None:
    """Restore the original export methods and remove the scratch directory.

    Parameters
    ----------
    config
        The MkDocs configuration; unused.
    """
    del config

    global _scratch_dir  # noqa: PLW0603

    for name, original in _originals.items():
        setattr(mapyta.Map, name, original)
    _originals.clear()

    if _scratch_dir is not None:
        shutil.rmtree(_scratch_dir, ignore_errors=True)
        _scratch_dir = None
