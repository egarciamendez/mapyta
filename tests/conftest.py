"""Shared pytest fixtures and configuration for mapyta tests."""

from collections.abc import Generator
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from shapely.geometry import Point

from mapyta import Map

if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver


@pytest.fixture
def sample_geojson() -> dict:
    """A minimal GeoJSON FeatureCollection with two zones."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "Zone A", "value": 42.0},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[(4.85, 52.35), (4.95, 52.35), (4.95, 52.40), (4.85, 52.40), (4.85, 52.35)]],
                },
            },
            {
                "type": "Feature",
                "properties": {"name": "Zone B", "value": 78.0},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[(4.95, 52.35), (5.05, 52.35), (5.05, 52.40), (4.95, 52.40), (4.95, 52.35)]],
                },
            },
        ],
    }


@pytest.fixture
def scored_geojson() -> dict:
    """GeoJSON with a numeric 'score' property."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "Centrum", "score": 92},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[(4.88, 52.36), (4.92, 52.36), (4.92, 52.38), (4.88, 52.38), (4.88, 52.36)]],
                },
            },
            {
                "type": "Feature",
                "properties": {"name": "West", "score": 74},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[(4.84, 52.36), (4.88, 52.36), (4.88, 52.38), (4.84, 52.38), (4.84, 52.36)]],
                },
            },
        ],
    }


@pytest.fixture
def map_with_point() -> Map:
    """A map with one location for export tests."""
    m = Map(title="Export")
    m.add_point(Point(4.9, 52.37), marker="📍")
    return m


@pytest.fixture(scope="session")
def browser() -> Generator["WebDriver", None, None]:
    """A headless Chrome session shared by every browser-driven scenario in the suite."""
    webdriver = pytest.importorskip("selenium.webdriver", reason="browser tests need selenium (the 'export' extra)")
    options = webdriver.ChromeOptions()
    for flag in ("--headless=new", "--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage", "--window-size=1200,900"):
        options.add_argument(flag)
    try:
        driver = webdriver.Chrome(options=options)
    except Exception as exc:  # a browser that will not start is a skip, not a mapyta failure
        pytest.skip(f"could not start Chrome: {exc}")
    yield driver
    driver.quit()


@pytest.fixture
def mock_to_image() -> Generator[MagicMock | AsyncMock, Any, None]:
    """Patch to_image to return fake PNG bytes."""
    fake_png = b"\x89PNG\r\n\x1a\n_fake_image_data_1234567890"
    with patch.object(Map, "to_image", return_value=fake_png) as mock:
        mock.fake_png = fake_png
        yield mock
