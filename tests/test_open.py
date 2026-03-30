"""BDD-style tests for Map.open() live-reload server.

Each test follows the Given-When-Then pattern with a scenario
docstring and Arrange/Act/Assert comments.
"""
# ruff: noqa: SLF001

import json
import socket
import urllib.request
from collections.abc import Generator
from unittest.mock import patch

import pytest
from shapely import Point

from mapyta import Map
from mapyta.server import _MapServer


@pytest.fixture
def simple_map() -> Map:
    """A minimal Map with one point."""
    m = Map()
    m.add_point(Point(5.1, 52.1))
    return m


@pytest.fixture
def live_server(simple_map: Map) -> Generator[_MapServer, None, None]:
    """A real _MapServer started on a free port, torn down after the test."""
    server = _MapServer(host="localhost", port=0)
    server.update(simple_map._get_standalone_html())
    server.start()
    yield server
    server._server.shutdown()
    server._server.server_close()


class TestMapOpen:
    """Scenarios for Map.open() live-reload server."""

    def test_first_call_opens_browser(self, simple_map: Map) -> None:
        """Opening a map for the first time should start a server and open the browser."""
        # Given: a map with one point
        # When: .open() is called for the first time
        with patch("webbrowser.open") as mock_open:
            simple_map.open()

        # Then: the browser was opened exactly once with a localhost URL
        mock_open.assert_called_once()
        url: str = mock_open.call_args[0][0]
        assert url.startswith("http://localhost:")

    def test_second_call_does_not_reopen_browser(self, simple_map: Map) -> None:
        """Calling .open() a second time should update the map but not reopen the browser."""
        # Given: a map whose server has already been started
        with patch("webbrowser.open") as mock_open:
            simple_map.open()
            simple_map.add_circle(Point(5.0, 52.0))
            simple_map.open()

        # Then: the browser was opened only once
        mock_open.assert_called_once()

    def test_version_increments_on_each_call(self, simple_map: Map) -> None:
        """Each call to .open() should bump the server version counter."""
        # Given: a map; browser opening is suppressed
        with patch("webbrowser.open"):
            simple_map.open()
            simple_map.open()
            simple_map.open()

        # Then: version equals the number of .open() calls
        assert simple_map._server is not None
        assert simple_map._server._version == 3

    def test_returns_self_for_chaining(self, simple_map: Map) -> None:
        """open() should return the map instance for fluent chaining."""
        with patch("webbrowser.open"):
            result = simple_map.open()

        assert result is simple_map

    def test_version_endpoint_returns_json(self, live_server: _MapServer) -> None:
        """The /_mapyta_version endpoint should return valid JSON with a 'version' key."""
        # When: the version endpoint is fetched
        with urllib.request.urlopen(f"{live_server.url()}_mapyta_version") as resp:
            data = json.loads(resp.read())

        # Then: the response contains an integer version
        assert "version" in data
        assert isinstance(data["version"], int)

    def test_root_endpoint_returns_html(self, live_server: _MapServer) -> None:
        """The root URL should return HTML containing Leaflet content."""
        with urllib.request.urlopen(live_server.url()) as resp:
            body = resp.read().decode("utf-8")

        assert "leaflet" in body.lower() or "</html>" in body.lower()

    def test_root_contains_poll_script(self, live_server: _MapServer) -> None:
        """The served HTML should contain the auto-reload polling script."""
        with urllib.request.urlopen(live_server.url()) as resp:
            body = resp.read().decode("utf-8")

        assert "/_mapyta_version" in body

    def test_merged_map_has_no_server(self, simple_map: Map) -> None:
        """A map produced by + should have no live-reload server."""
        # Given: map A with a running server; map B plain
        other = Map()
        other.add_circle(Point(5.0, 52.0))

        with patch("webbrowser.open"):
            simple_map.open()

        # When: the maps are merged
        combined = simple_map + other

        # Then: the merged map has no server
        assert combined._server is None

    def test_explicit_port_is_used(self, simple_map: Map) -> None:
        """Passing an explicit port should bind to that port."""
        # Find a free port first
        with socket.socket() as sock:
            sock.bind(("localhost", 0))
            free_port = sock.getsockname()[1]

        with patch("webbrowser.open") as mock_open:
            simple_map.open(port=free_port)

        url: str = mock_open.call_args[0][0]
        assert str(free_port) in url

        # Teardown: stop the server so the port is released
        assert simple_map._server is not None
        simple_map._server._server.shutdown()
        simple_map._server._server.server_close()

    def test_original_map_server_preserved_after_add(self, simple_map: Map) -> None:
        """The original map's server should still be set after merging with +."""
        other = Map()

        with patch("webbrowser.open"):
            simple_map.open()

        original_server = simple_map._server
        _ = simple_map + other

        # The original map's _server should be unchanged
        assert simple_map._server is original_server

    def test_block_true_returns_after_keyboard_interrupt(self, simple_map: Map) -> None:
        """open(block=True) should block until KeyboardInterrupt, then return self."""
        with patch("webbrowser.open"), patch("time.sleep", side_effect=[None, KeyboardInterrupt]):
            result = simple_map.open(block=True)

        assert result is simple_map
