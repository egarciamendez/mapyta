"""MkDocs hook that makes the executable documentation examples network-independent.

Several tutorial pages execute live HTTP calls against PDOK and CBS while the site is built. That makes an unrelated pull request fail whenever an
upstream service is slow, unreachable, or has renamed a column. This hook records every response once and replays it on subsequent builds, so a normal
build never touches the network.

Environment variables
---------------------
MAPYTA_DOCS_REFRESH
    When set to ``1``, ignore stored fixtures and re-record every request from the live services. Used by the scheduled workflow that detects upstream
    API drift.
MAPYTA_DOCS_OFFLINE
    When set to ``1``, fail on a cache miss instead of falling back to the network. Used to prove that a build is fully reproducible without
    connectivity.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

import requests
from mkdocs.exceptions import PluginError

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from mkdocs.config.defaults import MkDocsConfig
    from requests import Response, Session

FIXTURE_DIR = Path(__file__).parent.parent / "_fixtures"
INDEX_FILE = FIXTURE_DIR / "index.json"

logger = logging.getLogger("mkdocs.hooks.network_cache")

_original_request: Callable[..., Response] | None = None
_misses: list[str] = []


def _fingerprint(method: str, url: str, params: Mapping[str, str]) -> str:
    """Build a stable cache key for a request.

    Parameters
    ----------
    method
        HTTP method, upper-cased by the caller.
    url
        Request URL without the query string.
    params
        Query parameters, already normalised to strings; empty when there are none.

    Returns
    -------
    str
        Hex digest identifying this request.
    """
    payload = json.dumps([method, url, sorted(params.items())], sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _load_index() -> dict[str, str]:
    """Return the readable mapping of cache keys to the requests they describe.

    Returns
    -------
    dict[str, str]
        Mapping of cache key to a ``METHOD URL`` description, empty when no index exists yet.
    """
    if INDEX_FILE.exists():
        return json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    return {}


def _save_index(index: dict[str, str]) -> None:
    """Write the cache key mapping to disk, sorted so diffs stay readable.

    Parameters
    ----------
    index
        Mapping of cache key to a ``METHOD URL`` description.
    """
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_FILE.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _replay(fixture: Path) -> Response:
    """Rebuild a response object from a stored fixture.

    Parameters
    ----------
    fixture
        Path to the gzipped JSON fixture.

    Returns
    -------
    Response
        A response carrying the recorded status, headers, URL, and body.
    """
    stored = json.loads(gzip.decompress(fixture.read_bytes()).decode("utf-8"))
    response = requests.models.Response()
    response.status_code = stored["status_code"]
    response._content = stored["body"].encode("utf-8")  # noqa: SLF001
    response.headers.update(stored["headers"])
    response.url = stored["url"]
    response.encoding = "utf-8"
    return response


def _record(fixture: Path, response: Response, method: str, url: str, key: str) -> None:
    """Store a live response so later builds can replay it.

    Parameters
    ----------
    fixture
        Path the fixture is written to.
    response
        The live response to store.
    method
        HTTP method, upper-cased.
    url
        Request URL without the query string.
    key
        Cache key for this request.
    """
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "status_code": response.status_code,
        "headers": {"Content-Type": response.headers.get("Content-Type", "")},
        "url": response.url,
        "body": response.text,
    }
    fixture.write_bytes(gzip.compress(json.dumps(payload).encode("utf-8"), 9))

    index = _load_index()
    index[key] = f"{method} {response.url}"
    _save_index(index)

    logger.info("Recorded network fixture %s for %s %s", key, method, url)


def on_config(config: MkDocsConfig) -> MkDocsConfig:
    """Patch ``requests`` so documentation examples replay recorded responses.

    Parameters
    ----------
    config
        The MkDocs configuration, passed through unchanged.

    Returns
    -------
    MkDocsConfig
        The unmodified MkDocs configuration.
    """
    global _original_request  # noqa: PLW0603

    if _original_request is not None:
        return config

    _original_request = requests.sessions.Session.request
    original = _original_request

    refresh = os.environ.get("MAPYTA_DOCS_REFRESH") == "1"
    offline = os.environ.get("MAPYTA_DOCS_OFFLINE") == "1"

    def cached_request(self: Session, method: str, url: str, **kwargs: object) -> Response:
        """Serve a request from the fixture store, recording it on a miss.

        Parameters
        ----------
        self
            The requests session performing the call.
        method
            HTTP method.
        url
            Request URL without the query string.
        **kwargs
            Remaining arguments forwarded to ``requests``.

        Returns
        -------
        Response
            The replayed or freshly recorded response.

        Raises
        ------
        RuntimeError
            When offline mode is active and no fixture exists for this request.
        """
        raw_params = kwargs.get("params")
        params: dict[str, str] = {str(name): str(value) for name, value in raw_params.items()} if isinstance(raw_params, dict) else {}
        upper = method.upper()
        key = _fingerprint(upper, url, params)
        fixture = FIXTURE_DIR / f"{key}.json.gz"

        if fixture.exists() and not refresh:
            return _replay(fixture)

        if offline:
            descriptor = f"{upper} {url} (key {key})"
            _misses.append(descriptor)
            msg = f"No recorded response for {descriptor}. Re-record with MAPYTA_DOCS_REFRESH=1."
            raise RuntimeError(msg)

        response = original(self, method, url, **kwargs)
        response.raise_for_status()
        _record(fixture, response, upper, url, key)
        return response

    requests.sessions.Session.request = cached_request  # ty: ignore[invalid-assignment]
    mode = "refresh" if refresh else ("offline" if offline else "replay")
    logger.info("Network fixture cache active (%s mode, %s)", mode, FIXTURE_DIR)
    return config


def on_post_build(config: MkDocsConfig) -> None:
    """Fail the build when a documented request could not be replayed.

    ``markdown-exec`` swallows exceptions raised inside a code block and renders them as output, so without this gate a missing fixture would silently
    drop a map from the page while the build still reported success.

    Parameters
    ----------
    config
        The MkDocs configuration; unused.

    Raises
    ------
    PluginError
        When one or more requests had no recorded response.
    """
    del config

    if not _misses:
        return

    listed = "\n  - ".join(_misses)
    msg = f"{len(_misses)} documented request(s) had no recorded response:\n  - {listed}"
    raise PluginError(msg)
