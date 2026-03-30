"""Live-reload HTTP server for interactive map preview."""

import http.server
import json
import socketserver
import threading

_POLL_JS = (
    "<script>\n"
    "(function(){\n"
    "  var _v = null;\n"
    "  setInterval(function(){\n"
    "    fetch('/_mapyta_version')\n"
    "      .then(function(r){ return r.json(); })\n"
    "      .then(function(d){\n"
    "        if(_v === null){ _v = d.version; return; }\n"
    "        if(d.version !== _v){ window.location.reload(); }\n"
    "      })\n"
    "      .catch(function(){});\n"
    "  }, 1000);\n"
    "})();\n"
    "</script>"
)


class _ReuseAddrTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


class _MapServer:
    """Local HTTP server that serves a map and supports live-reload via version polling."""

    def __init__(self, host: str = "localhost", port: int = 0) -> None:
        self.host = host
        self._html = ""
        self._version = 0
        self._lock = threading.Lock()

        handler = self._make_handler()
        self._server = _ReuseAddrTCPServer((host, port), handler)
        self.port: int = self._server.server_address[1]

    def _make_handler(self) -> type:
        instance = self

        class _Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                if self.path == "/_mapyta_version":
                    with instance._lock:  # noqa: SLF001
                        body = json.dumps({"version": instance._version}).encode("utf-8")  # noqa: SLF001
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                else:
                    with instance._lock:  # noqa: SLF001
                        html = instance._html  # noqa: SLF001
                    if "</body>" in html:
                        html = html.replace("</body>", f"{_POLL_JS}\n</body>", 1)
                    body = html.encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)

            def log_message(self, format: str, *args: object) -> None:  # noqa: A002
                pass

        return _Handler

    def start(self) -> None:
        """Start the HTTP server in a background daemon thread."""
        thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        thread.start()

    def update(self, html: str) -> None:
        """Replace the served HTML and increment the version counter."""
        with self._lock:
            self._html = html
            self._version += 1

    def url(self) -> str:
        """Return the URL at which the map is served."""
        display_host = "localhost" if self.host in ("0.0.0.0", "") else self.host
        return f"http://{display_host}:{self.port}/"
