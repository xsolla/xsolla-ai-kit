"""AC-4..AC-9: the live docs fetcher (scripts/qp_docs.py). Network is always a mock transport.

Assumptions documented for the implementer:
- `now` is epoch seconds (int or float). The fetch timestamp is stored in a cache file as epoch
  seconds (integer part) or as an ISO-8601 UTC string of the same instant.
- main() takes the base URL from `--base-url URL`; with no args it uses DEFAULT_BASE_URL.
- On success main() prints the cache path (the cache dir or a path inside it) to stdout.
"""
from __future__ import annotations

import datetime
import os
import re
import stat
import unittest
from pathlib import Path

import qs_base
from qs_base import SENTINEL, IsolatedCase

import qp_docs

NOW = 1_800_000_000
OTHER_HOST = "https://docs.example.test"


class FakeDocs:
    """transport(url) -> (status, text). Records every URL."""

    def __init__(self, status=200):
        self.urls = []
        self.status = status

    def __call__(self, url):
        self.urls.append(url)
        if self.status != 200:
            return self.status, "failure"
        return 200, f"# page for {url}\n"


def cache_files(cache: Path):
    return [p for p in cache.rglob("*") if p.is_file()]


class DocsFetcherTests(IsolatedCase):
    def cache_dir(self) -> Path:
        return self.home / ".cache" / qp_docs.CACHE_DIR_NAME

    def fetch(self, transport, **kwargs):
        kwargs.setdefault("now", NOW)
        return qp_docs.fetch_docs(home=str(self.home), transport=transport, **kwargs)

    def test_ac_04_constants_and_default_host(self) -> None:
        self.assertEqual(qp_docs.DEFAULT_BASE_URL, "https://xsolla--e401f7.preview.redocly.app")
        self.assertEqual(qp_docs.CACHE_DIR_NAME, "quest-setup-docs")
        self.assertIsInstance(qp_docs.TTL_SECONDS, int)
        self.assertGreater(qp_docs.TTL_SECONDS, 0)

    def test_ac_04_no_cache_fetches_index_and_specs_and_writes_cache(self) -> None:
        transport = FakeDocs()
        result = self.fetch(transport)
        self.assertEqual(result["status"], "fresh")
        self.assertIsNone(result["error"])
        self.assertGreaterEqual(len(transport.urls), 1)
        self.assertTrue(all(u.startswith(qp_docs.DEFAULT_BASE_URL) for u in transport.urls))
        self.assertTrue(result["pages"])
        files = cache_files(self.cache_dir())
        self.assertTrue(files)
        blob = "\n".join(p.read_text(errors="replace") for p in files)
        iso = datetime.datetime.fromtimestamp(NOW, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M")
        self.assertTrue(str(NOW) in blob or iso in blob, "fetch timestamp not stored in cache")

    def test_ac_04_main_prints_cache_path(self) -> None:
        code, out, _ = self.capture(qp_docs.main, [], transport=FakeDocs(), home=str(self.home))
        self.assertEqual(code, 0)
        self.assertIn(str(self.cache_dir()), out)

    def test_ac_05_young_cache_makes_zero_network_calls(self) -> None:
        self.fetch(FakeDocs())
        second = FakeDocs()
        result = self.fetch(second, now=NOW + qp_docs.TTL_SECONDS - 1)
        self.assertEqual(result["status"], "cached")
        self.assertEqual(second.urls, [])
        self.assertTrue(result["pages"])

    def test_ac_05_ttl_is_a_single_constant_used_as_default(self) -> None:
        import inspect
        default = inspect.signature(qp_docs.fetch_docs).parameters["ttl"].default
        self.assertEqual(default, qp_docs.TTL_SECONDS)

    def test_ac_06_old_cache_and_failing_fetch_returns_stale(self) -> None:
        self.fetch(FakeDocs())
        failing = FakeDocs(status=503)
        result = self.fetch(failing, now=NOW + qp_docs.TTL_SECONDS + 1)
        self.assertEqual(result["status"], "STALE")
        self.assertTrue(failing.urls)
        self.assertTrue(result["pages"])

    def test_ac_06_stale_is_marked_in_main_output(self) -> None:
        self.capture(qp_docs.main, [], transport=FakeDocs(), home=str(self.home))
        # main has no clock argument, so force staleness by backdating the cache files.
        for p in cache_files(self.cache_dir()):
            os.utime(p, (NOW - 10 * qp_docs.TTL_SECONDS,) * 2)
        _, out, _ = self.capture(qp_docs.main, [], transport=FakeDocs(status=500), home=str(self.home))
        self.assertIn("STALE", out)

    def test_ac_06_no_cache_and_failing_fetch_exits_nonzero_and_prints_url(self) -> None:
        failing = FakeDocs(status=500)
        code, out, _ = self.capture(qp_docs.main, [], transport=failing, home=str(self.home))
        self.assertNotEqual(code, 0)
        self.assertTrue(failing.urls)
        self.assertIn(failing.urls[0], out)

    def test_ac_06_no_cache_failing_fetch_reports_error(self) -> None:
        result = self.fetch(FakeDocs(status=500))
        self.assertEqual(result["status"], "error")
        self.assertTrue(result["error"])
        self.assertNotEqual(result["error"], "not implemented")

    def test_ac_07_override_host_only_and_no_credentials_sent(self) -> None:
        self.write_env()
        transport = FakeDocs()
        code, out, err = self.capture(qp_docs.main, ["--base-url", OTHER_HOST], transport=transport,
                                      home=str(self.home))
        self.assertEqual(code, 0)
        self.assertTrue(transport.urls)
        self.assertTrue(all(u.startswith(OTHER_HOST) for u in transport.urls), transport.urls)
        self.assertIn("docs.example.test", out)
        blob = "\n".join(transport.urls) + out + err
        for secret in (SENTINEL, "XSOLLA_"):
            self.assertNotIn(secret, blob)

    def test_ac_07_fetch_docs_result_host_matches_override(self) -> None:
        result = self.fetch(FakeDocs(), base_url=OTHER_HOST)
        self.assertEqual(result["status"], "fresh")
        self.assertEqual(result["host"], "docs.example.test")

    def test_ac_07_source_never_touches_credentials(self) -> None:
        source = qs_base.read_text(qs_base.SCRIPTS / "qp_docs.py")
        self.assertIsNotNone(re.search(r"def fetch_docs", source))
        self.assertNotIn("XSOLLA_", source)
        self.assertNotIn("Authorization", source)
        self.assertNotIn(".env", source)

    def test_ac_08_non_https_is_refused_without_a_request(self) -> None:
        transport = FakeDocs()
        result = self.fetch(transport, base_url="http://docs.example.test")
        self.assertEqual(transport.urls, [])
        self.assertEqual(result["status"], "error")
        self.assertIn("https only", str(result["error"]))

    def test_ac_08_main_refuses_http_with_message(self) -> None:
        transport = FakeDocs()
        code, out, err = self.capture(qp_docs.main, ["--base-url", "http://docs.example.test"],
                                      transport=transport, home=str(self.home))
        self.assertNotEqual(code, 0)
        self.assertEqual(transport.urls, [])
        self.assertIn("https only", out + err)

    def test_ac_09_cache_location_and_modes(self) -> None:
        result = self.fetch(FakeDocs())
        cache = self.cache_dir()
        self.assertEqual(result["status"], "fresh")
        self.assertTrue(str(result["cache_path"]).startswith(str(cache)))
        self.assertEqual(stat.S_IMODE(cache.stat().st_mode), 0o700)
        files = cache_files(cache)
        self.assertTrue(files)
        for p in files:
            with self.subTest(file=p.name):
                self.assertEqual(stat.S_IMODE(p.stat().st_mode), 0o600)

    def test_ac_09_cache_never_inside_repo_or_worktree(self) -> None:
        result = self.fetch(FakeDocs())
        self.assertEqual(result["status"], "fresh")
        resolved = Path(result["cache_path"]).resolve()
        self.assertNotIn(str(qs_base.REPO), str(resolved))
        self.assertFalse(list((self.cwd).rglob("*")), "nothing may be written into the cwd")


if __name__ == "__main__":
    unittest.main()
