"""Shared test base for the quest-setup tests (AC-1, AC-27). Stdlib only.

IsolatedCase: clears XSOLLA_* env, sets HOME and cwd to a fresh temp dir, makes any real socket
and any read of ~/qs-test/.env fail, and records both so tearDown can assert zero of each.
"""
from __future__ import annotations

import builtins
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

SKILL = Path(__file__).resolve().parents[1]
REPO = SKILL.parents[1]
SCRIPTS = SKILL / "scripts"
REFERENCES = SKILL / "references"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

REAL_QS_ENV =Path(os.path.expanduser("~/qs-test/.env")).resolve()
SENTINEL = "SENTINEL-KEY-9c2e7a41beef"
SENTINEL_ENV = {
    "XSOLLA_MERCHANT_ID": "7",
    "XSOLLA_PROJECT_ID": "42",
    "XSOLLA_PROJECT_API_KEY": SENTINEL,
}

_REAL_OPEN = builtins.open


def read_text(path: Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def count_non_get(calls) -> int:
    """AC-27: 'no write' means zero POST/PUT/PATCH/DELETE calls. calls = [(method, ...), ...]."""
    return sum(1 for call in calls if str(call[0]).upper() != "GET")


class RecordingTransport:
    """Mock transport(method, path, body=None) -> (status, json). Records every call."""

    def __init__(self, handler=None):
        self.calls = []
        self.handler = handler or (lambda method, path, body: (200, {}))

    def __call__(self, method, path, body=None):
        self.calls.append((method, path, body))
        return self.handler(method, path, body)

    @property
    def non_get(self) -> int:
        return count_non_get(self.calls)


class IsolatedCase(unittest.TestCase):
    """AC-1 base: no env, temp HOME and cwd, no real sockets, no read of ~/qs-test/.env."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name).resolve()
        self.home = self.tmp / "home"
        self.cwd = self.tmp / "work"
        self.home.mkdir()
        self.cwd.mkdir()
        self.socket_attempts = []
        self.qs_env_reads = []

        env = {k: v for k, v in os.environ.items() if not k.startswith("XSOLLA_")}
        env["HOME"] = str(self.home)
        patcher = mock.patch.dict(os.environ, env, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)

        old_cwd = os.getcwd()
        os.chdir(self.cwd)
        self.addCleanup(os.chdir, old_cwd)

        def guarded_socket(*args, **kwargs):
            self.socket_attempts.append(args)
            raise AssertionError("real socket opened in a test")

        for target in ("socket.socket",):
            p = mock.patch(target, guarded_socket)
            p.start()
            self.addCleanup(p.stop)

        def guarded_open(file, *args, **kwargs):
            try:
                resolved = Path(os.fspath(file)).resolve()
            except TypeError:  # file descriptor
                resolved = None
            if resolved == REAL_QS_ENV:
                self.qs_env_reads.append(str(resolved))
                raise AssertionError("test read ~/qs-test/.env")
            return _REAL_OPEN(file, *args, **kwargs)

        for target in ("builtins.open", "io.open"):
            p = mock.patch(target, guarded_open)
            p.start()
            self.addCleanup(p.stop)

        self.addCleanup(self._assert_no_leaks)

    def _assert_no_leaks(self) -> None:
        self.assertEqual(self.socket_attempts, [], "real socket opened")
        self.assertEqual(self.qs_env_reads, [], "~/qs-test/.env was read")

    def write_env(self, values=None) -> None:
        values = SENTINEL_ENV if values is None else values
        text = "".join(f"{k}={v}\n" for k, v in values.items())
        (self.cwd / ".env").write_text(text, encoding="utf-8")

    def capture(self, fn, *args, **kwargs):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            result = fn(*args, **kwargs)
        return result, out.getvalue(), err.getvalue()

    def tree(self, root: Path):
        return sorted(str(p.relative_to(root)) for p in Path(root).rglob("*"))
