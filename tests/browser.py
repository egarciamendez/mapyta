"""Shared harness for the browser-driven test modules.

Zoom rules, the layer dropdown and the marker filter all ship as generated JavaScript, so
only a real browser can show that they run.  The helpers live here rather than in each
module because the ``browser`` fixture is session-scoped and pytest caches such a fixture
per definition, not per name: a copy per module would start a second headless Chrome and
pay its cold start again.
"""

import time
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from mapyta import Map
from mapyta.export import _detect_chrome

if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver

requires_chrome = pytest.mark.skipif(not _detect_chrome(), reason="browser tests need Chrome")

COUNT_MARKERS = "return document.querySelectorAll('.leaflet-marker-icon').length;"


def eventually(browser: "WebDriver", script: str, expected: object, timeout: float = 15.0) -> None:
    """Poll *script* until it returns *expected*, reporting the last value seen on failure."""
    deadline = time.monotonic() + timeout
    actual = None
    while time.monotonic() < deadline:
        actual = browser.execute_script(script)
        if actual == expected:
            return
        time.sleep(0.05)
    pytest.fail(f"expected {expected!r}, last saw {actual!r}")


def open_map(browser: "WebDriver", tmp_path: Path, m: Map, name: str, ready: str | None = None) -> None:
    """Render *m* to *name* under *tmp_path* and load it in *browser*.

    *ready* is polled until it returns ``True``, for a page carrying a control the scenario
    has to wait for before it can act on it.
    """
    browser.get(Path(m.to_html(tmp_path / name)).resolve().as_uri())
    if ready is not None:
        eventually(browser, ready, True)
