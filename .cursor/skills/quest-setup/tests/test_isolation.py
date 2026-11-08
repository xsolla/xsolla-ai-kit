"""AC-1..AC-3: isolation harness and the sentinel-secret scan. Never touches the network."""
from __future__ import annotations

import json
import os
import socket
import unittest
import urllib.request
from unittest import mock

import qs_base
from qs_base import SENTINEL, IsolatedCase

import qp_docs
import qp_request


def _all_text(*parts) -> str:
    return "\n".join(str(p) for p in parts)


class IsolationHarnessTests(IsolatedCase):
    def test_ac_01_env_home_cwd_are_clean(self) -> None:
        self.assertFalse([k for k in os.environ if k.startswith("XSOLLA_")])
        self.assertEqual(os.environ["HOME"], str(self.home))
        self.assertEqual(os.path.realpath(os.getcwd()), str(self.cwd))
        self.assertEqual(os.path.expanduser("~"), str(self.home))

    def test_ac_01_real_socket_is_refused_and_recorded(self) -> None:
        with self.assertRaises(AssertionError):
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.assertEqual(len(self.socket_attempts), 1)
        self.socket_attempts.clear()  # expected here, so tearDown stays green

    def test_ac_01_qs_test_env_read_is_refused_and_recorded(self) -> None:
        with self.assertRaises(AssertionError):
            open(qs_base.REAL_QS_ENV)
        with self.assertRaises(AssertionError):
            qs_base.REAL_QS_ENV.read_text()
        self.assertEqual(len(self.qs_env_reads), 2)
        self.qs_env_reads.clear()

    def test_ac_01_default_transport_is_never_used_without_injection_in_tests(self) -> None:
        # The default (real) network path must be reachable only when transport is None.
        # Under the guard it would raise AssertionError or return an error status, never "fresh".
        with mock.patch.object(urllib.request, "urlopen", side_effect=AssertionError("real urlopen")):
            try:
                result = qp_docs.fetch_docs(home=str(self.home), transport=None, now=1_800_000_000)
            except AssertionError:
                result = {"status": "error"}
        self.assertNotEqual(result["status"], "fresh")
        self.socket_attempts.clear()


class SentinelScanTests(IsolatedCase):
    INSTALL_DOCS = False

    """AC-3: a sentinel secret in .env must not show up anywhere observable."""

    def setUp(self) -> None:
        super().setUp()
        self.write_env()
        self.recorded = []

    def test_named_docs_sentinel_outcomes(self) -> None:
        for case, status in (("success_200", 200), ("failure_500", 500)):
            with self.subTest(case=case):
                home = self.home / case
                recorded = []

                def transport(url):
                    recorded.append(url)
                    return (200, "# docs page") if status == 200 else (500, "boom")

                code, out, err = self.capture(qp_docs.main, [], transport=transport, home=str(home))
                self.assertTrue(recorded)
                self.assertEqual(self.socket_attempts, [])
                observed = _all_text(out, err, recorded)
                if status == 200:
                    self.assertEqual(code, 0)
                    cache = home / ".cache" / qp_docs.CACHE_DIR_NAME
                    self.assertTrue(cache.is_dir())
                    files_text = _all_text(*[p.read_text(errors="replace") for p in cache.rglob("*") if p.is_file()])
                    self.assertTrue(files_text)
                    observed += files_text
                else:
                    self.assertNotEqual(code, 0)
                self.assertNotIn(SENTINEL, observed)

    def test_ac_03_traceback_path_no_sentinel(self) -> None:
        def transport(url):
            self.recorded.append(url)
            raise RuntimeError("transport exploded")

        try:
            result, out, err = self.capture(qp_docs.fetch_docs, home=str(self.home), transport=transport)
        except RuntimeError as exc:
            import traceback
            out, err, result = "", traceback.format_exc(), {"status": "raised"}
            self.assertNotIn(SENTINEL, str(exc))
        self.assertTrue(self.recorded)
        self.assertEqual(result["status"] in ("error", "raised"), True)
        self.assertNotIn(SENTINEL, _all_text(out, err, self.recorded, result))

    def test_ac_03_qp_request_success_and_error_paths(self) -> None:
        path = "/api/v2/merchants/7/projects/42/quests"
        for status, body in ((200, b'{"quests": []}'), (401, SENTINEL.encode())):
            with self.subTest(status=status):
                resp = mock.MagicMock()
                resp.status = status
                resp.read.return_value = body
                with mock.patch.object(urllib.request.OpenerDirector, "open", return_value=resp):
                    code, out, err = self.capture(qp_request.main, ["GET", path])
                self.assertNotIn(SENTINEL, out + err)
                self.assertTrue(json.loads(out))


if __name__ == "__main__":
    unittest.main()
