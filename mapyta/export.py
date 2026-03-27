"""Map export functionality (HTML, PNG, SVG)."""

import shutil
import time


def check_selenium() -> None:
    """Verify Selenium and Chrome driver availability.

    Raises
    ------
    ImportError
        If selenium is not installed.
    RuntimeError
        If Chrome/chromedriver is not found.
    """
    try:
        from selenium import webdriver  # noqa: PLC0415, F401
    except ImportError:
        raise ImportError(
            "Image export requires selenium. Install it with:\n  "
            "pip install selenium chromedriver-autoinstaller\n"
            "or\n"
            "uv add selenium chromedriver-autoinstaller"
        ) from None

    chrome_paths = [
        shutil.which("google-chrome"),
        shutil.which("google-chrome-stable"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        shutil.which("chrome"),
        shutil.which("googlechrome"),
        shutil.which("chromium.exe"),
        shutil.which("chrome_proxy.exe"),
        shutil.which("chromedriver"),
    ]
    if not any(chrome_paths):
        try:
            import chromedriver_autoinstaller  # noqa: PLC0415

            chromedriver_autoinstaller.install()
        except (ImportError, ModuleNotFoundError, ValueError):
            pass  # Will be caught by the chromedriver check below

    if not shutil.which("chromedriver"):
        raise RuntimeError(
            "Chrome or Chromium not found. Image export requires Chrome.\n"
            "  Ubuntu/Debian: sudo apt install chromium-browser\n"
            "  macOS:         brew install --cask google-chrome\n"
            "  Windows:       Download from https://www.google.com/chrome/\n"
            "chromedriver not found on PATH.\n"
            "  pip install chromedriver-autoinstaller\n"
            "  Or download: https://googlechromelabs.github.io/chrome-for-testing/"
        )


def capture_screenshot(
    html_path: str,
    width: int = 1200,
    height: int = 800,
    delay: float = 2.0,
) -> bytes:
    """Capture a screenshot of an HTML file using headless Chrome.

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

    Returns
    -------
    bytes
        PNG image bytes.
    """
    check_selenium()

    from selenium import webdriver  # noqa: PLC0415
    from selenium.webdriver.chrome.options import Options  # noqa: PLC0415

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument(f"--window-size={width},{height}")

    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        driver.set_window_size(width, height)
        driver.get(f"file://{html_path}")
        time.sleep(delay)
        return driver.get_screenshot_as_png()
    finally:
        if driver:
            driver.quit()
