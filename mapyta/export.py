"""Map export functionality (HTML, PNG, SVG)."""

import shutil
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from selenium.webdriver import Chrome, Edge  # ty: ignore[unresolved-import]

Backend = Literal["chrome", "edge"]

_CHROME_PATH_NAMES: tuple[str, ...] = (
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
    "chrome",
    "googlechrome",
)
_EDGE_PATH_NAMES: tuple[str, ...] = (
    "microsoft-edge",
    "microsoft-edge-stable",
    "msedge",
)
_WINDOWS_CHROME_INSTALL_PATHS: tuple[str, ...] = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
)
_WINDOWS_EDGE_INSTALL_PATHS: tuple[str, ...] = (
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
)
_MACOS_CHROME_INSTALL_PATHS: tuple[str, ...] = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
)
_MACOS_EDGE_INSTALL_PATHS: tuple[str, ...] = ("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",)


def _detect_chrome() -> bool:
    if any(shutil.which(name) for name in _CHROME_PATH_NAMES):
        return True
    if sys.platform == "win32":
        return any(Path(p).exists() for p in _WINDOWS_CHROME_INSTALL_PATHS)
    if sys.platform == "darwin":
        return any(Path(p).exists() for p in _MACOS_CHROME_INSTALL_PATHS)
    return False


def _detect_edge() -> bool:
    if any(shutil.which(name) for name in _EDGE_PATH_NAMES):
        return True
    if sys.platform == "win32":
        return any(Path(p).exists() for p in _WINDOWS_EDGE_INSTALL_PATHS)
    if sys.platform == "darwin":
        return any(Path(p).exists() for p in _MACOS_EDGE_INSTALL_PATHS)
    return False


def _select_backend() -> Backend:
    """Pick a browser backend without launching one.

    Prefers Chrome to preserve historical behavior; falls back to Edge.

    Raises
    ------
    RuntimeError
        If no supported browser is installed.
    """
    if _detect_chrome():
        return "chrome"
    if _detect_edge():
        return "edge"
    raise RuntimeError(
        "No supported browser found. Image export needs a Chromium-based browser.\n"
        "  Chrome:    https://www.google.com/chrome/  (Linux: apt install chromium)\n"
        "  Edge:      https://www.microsoft.com/edge\n"
        "Selenium >=4.6 fetches the matching driver automatically."
    )


def check_selenium() -> None:
    """Verify Selenium and a supported browser are available.

    Raises
    ------
    ImportError
        If selenium is not installed.
    RuntimeError
        If no Chromium-based browser (Chrome, Chromium, or Edge) is installed.
    """
    try:
        from selenium import webdriver  # noqa: PLC0415, F401  # ty: ignore[unresolved-import]
    except ImportError:
        raise ImportError(
            "Image export requires selenium>=4.6. Install it with:\n  pip install 'selenium>=4.6'\nor\n  uv add 'selenium>=4.6'"
        ) from None

    _select_backend()


def _build_chrome_driver(width: int, height: int, scale: float) -> "Chrome":
    from selenium import webdriver  # noqa: PLC0415  # ty: ignore[unresolved-import]
    from selenium.webdriver.chrome.options import Options  # noqa: PLC0415  # ty: ignore[unresolved-import]

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument(f"--window-size={width},{height}")
    if scale != 1.0:
        options.add_argument(f"--force-device-scale-factor={scale}")
    return webdriver.Chrome(options=options)


def _build_edge_driver(width: int, height: int, scale: float) -> "Edge":
    from selenium import webdriver  # noqa: PLC0415  # ty: ignore[unresolved-import]
    from selenium.webdriver.edge.options import Options  # noqa: PLC0415  # ty: ignore[unresolved-import]

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument(f"--window-size={width},{height}")
    if scale != 1.0:
        options.add_argument(f"--force-device-scale-factor={scale}")
    return webdriver.Edge(options=options)


def capture_screenshot(
    html_path: str,
    width: int = 1200,
    height: int = 800,
    delay: float = 2.0,
    scale: float = 1.0,
) -> bytes:
    """Capture a screenshot of an HTML file using a headless browser.

    Uses Chrome/Chromium if available, otherwise falls back to Microsoft Edge.

    Parameters
    ----------
    html_path : str
        Path to the HTML file.
    width : int
        Viewport width in pixels.
    height : int
        Viewport height in pixels.
    delay : float
        Seconds to wait for tile loading.
    scale : float
        Device pixel ratio. ``scale=2.0`` renders at 2× pixel density (Retina),
        producing a ``width * 2`` × ``height * 2`` pixel image while keeping the
        map layout identical to ``scale=1.0``.

    Returns
    -------
    bytes
        PNG image bytes.
    """
    if scale <= 0:
        raise ValueError(f"scale must be greater than 0, got {scale!r}")

    check_selenium()
    backend = _select_backend()
    builder = _build_chrome_driver if backend == "chrome" else _build_edge_driver

    driver = None
    try:
        driver = builder(width, height, scale)
        driver.set_window_size(width, height)
        driver.get(f"file://{html_path}")
        time.sleep(delay)
        return driver.get_screenshot_as_png()
    finally:
        if driver:
            driver.quit()
