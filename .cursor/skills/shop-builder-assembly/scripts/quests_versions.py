"""Quests block versions, read from what the CDN serves. Nothing here pins a release.

Every published release has a public ``default-data.json`` under its version folder. That file
is the source of truth for two questions:

* which versions exist: a version is known when its defaults are served;
* what a version supports: theme settings exist when its defaults carry ``themeId``.

The newest stable release is found by walking version numbers upward from the first release,
ten patch numbers per round, until a round finds nothing. Release numbering has gaps (a minor
line can start above .0), which the ten-wide round covers. Results are cached for the life of
the process. Python 3.9+, standard library only.
"""
from __future__ import annotations

import http.client
import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
from typing import Callable, Dict, Optional, Tuple

CDN_ROOT = "https://cdn.xsolla.net/site-builder-modules/"
MODULE = "_quest-platform_quests-block"
TIMEOUT_SECONDS = 10
# Where the walk starts: the first release of the block. Not a pin; the walk only goes up.
FIRST_RELEASE = (0, 1, 0)
PROBE_WINDOW = 10  # patch numbers probed per round; a round with no release ends a minor line
STABLE = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\Z")
PRERELEASE = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)-[A-Za-z0-9][A-Za-z0-9.-]*\Z")

Fetcher = Callable[[str], Optional[dict]]


def host(version: str) -> str:
    """CDN folder the federated wrapper's ``values.host`` points at."""
    return f"{CDN_ROOT}{MODULE}/{version}/"


def is_version(value: object) -> bool:
    return isinstance(value, str) and bool(STABLE.fullmatch(value) or PRERELEASE.fullmatch(value))


def is_prerelease(value: object) -> bool:
    return isinstance(value, str) and bool(PRERELEASE.fullmatch(value))


_local = threading.local()


def _connection() -> http.client.HTTPSConnection:
    """One kept-alive connection per worker thread: the TLS handshake dominates a probe."""
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = http.client.HTTPSConnection(urlparse(CDN_ROOT).hostname, timeout=TIMEOUT_SECONDS)
        _local.conn = conn
    return conn


def _cdn_fetch(version: str) -> Optional[dict]:
    """The version's defaults, or None when the CDN does not serve them."""
    path = urlparse(host(version)).path + "default-data.json"
    for _ in range(2):  # a kept-alive connection the server closed is reopened once
        conn = _connection()
        try:
            conn.request("GET", path)
            resp = conn.getresponse()
            raw = resp.read()
        except (OSError, http.client.HTTPException):
            conn.close()
            _local.conn = None
            continue
        if resp.status != 200:
            return None
        try:
            value = json.loads(raw.decode("utf-8"))
        except ValueError:
            return None
        return value if isinstance(value, dict) and isinstance(value.get("defaultData"), dict) else None
    return None


_fetcher: Fetcher = _cdn_fetch
_defaults: Dict[str, Optional[dict]] = {}
_latest: Optional[str] = None


def use_fetcher(fetcher: Fetcher) -> None:
    """Replace the CDN reader (tests) and forget everything read so far."""
    global _fetcher, _latest
    _fetcher = fetcher
    _defaults.clear()
    _latest = None


def defaults(version: str) -> Optional[dict]:
    if not is_version(version):
        return None
    if version not in _defaults:
        _defaults[version] = _fetcher(version)
    return _defaults[version]


_executor: Optional[ThreadPoolExecutor] = None


def _pool() -> ThreadPoolExecutor:
    """Kept for the process, so worker threads keep their CDN connections between rounds."""
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=PROBE_WINDOW)
    return _executor


def _exists(versions: Tuple[str, ...]) -> Dict[str, bool]:
    missing = [v for v in versions if v not in _defaults]
    if missing:
        for version, value in zip(missing, _pool().map(_fetcher, missing)):
            _defaults[version] = value
    return {v: _defaults[v] is not None for v in versions}


def _walk_line(major: int, minor: int, start: int) -> Optional[int]:
    """Highest served patch of major.minor from ``start``, or None when none is served."""
    best = None
    patch = start
    while True:
        batch = tuple(f"{major}.{minor}.{p}" for p in range(patch, patch + PROBE_WINDOW))
        found = [p for p, ok in zip(range(patch, patch + PROBE_WINDOW), _exists(batch).values()) if ok]
        if not found:
            return best
        best = max(found)
        patch = best + 1


def latest_stable() -> Optional[str]:
    """The newest stable release the CDN serves, or None when it cannot be read."""
    global _latest
    if _latest is not None:
        return _latest
    best: Optional[Tuple[int, int, int]] = None
    major, minor = FIRST_RELEASE[0], FIRST_RELEASE[1]
    empty_lines = 0
    while True:
        top = _walk_line(major, minor, 0)
        if top is not None:
            best, empty_lines = (major, minor, top), 0
            minor += 1
            continue
        empty_lines += 1
        if empty_lines < 2:
            minor += 1
            continue
        # Two empty minor lines in a row: open the next major, unless this one had nothing.
        if best is None or best[0] < major:
            break
        major, minor, empty_lines = major + 1, 0, 0
    _latest = "%d.%d.%d" % best if best else None
    return _latest


def supports(version: str, capability: str) -> bool:
    """Whether a served version supports a capability ("appearance": theme settings)."""
    value = defaults(version)
    if value is None:
        return False
    data = value.get("defaultData") or {}
    if capability == "appearance":
        return "themeId" in data
    return False
