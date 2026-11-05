"""AC-16: credentials come from ./.env of the cwd when no XSOLLA_* variable is set."""
from __future__ import annotations

import base64
import json
import os
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

import qp_request
from qs_base import SENTINEL, SENTINEL_ENV, IsolatedCase


class CwdDotenvTests(IsolatedCase):
    def setUp(self) -> None:
        super().setUp()
        self.write_env()
        resp = mock.MagicMock()
        resp.status = 200
        resp.read.return_value = b'{"quests": []}'
        patcher = mock.patch.object(urllib.request.OpenerDirector, "open", return_value=resp)
        self.opener = patcher.start()
        self.addCleanup(patcher.stop)

    def test_ac_16_process_env_is_really_empty(self) -> None:
        self.assertFalse([k for k in os.environ if k.startswith("XSOLLA_")])
        self.assertEqual(Path.cwd().resolve(), self.cwd)

    def test_ac_16_request_completes_from_cwd_dotenv_with_default_env_and_cwd(self) -> None:
        # environ=None and cwd=None: the real process environment and the real cwd are used.
        code, out, err = self.capture(qp_request.main, ["GET", "/api/v2/merchants/7/projects/42/quests"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), {"ok": True, "status": 200, "body": {"quests": []}})
        request = self.opener.call_args.args[0]
        expected = base64.b64encode(f"7:{SENTINEL}".encode()).decode()
        self.assertEqual(request.get_header("Authorization"), "Basic " + expected)
        self.assertNotIn(SENTINEL, out + err)

    def test_ac_16_whoami_from_cwd_dotenv(self) -> None:
        code, out, _ = self.capture(qp_request.main, ["whoami"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["project_id"], SENTINEL_ENV["XSOLLA_PROJECT_ID"])

    def test_ac_16_loader_reads_cwd_dotenv_text(self) -> None:
        values = qp_request.read_dotenv(self.cwd / ".env")
        self.assertEqual(values["XSOLLA_PROJECT_API_KEY"], SENTINEL)
        creds = qp_request.resolve_credentials({}, self.cwd)
        self.assertEqual((creds.merchant_id, creds.project_id), ("7", "42"))
        self.assertNotIn(SENTINEL, repr(creds))

    def test_ac_16_other_cwd_without_dotenv_is_refused(self) -> None:
        empty = self.tmp / "empty"
        empty.mkdir()
        code, out, _ = self.capture(qp_request.main, ["whoami"], cwd=str(empty))
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(out), {"ok": False, "error": "access_not_configured"})


if __name__ == "__main__":
    unittest.main()
