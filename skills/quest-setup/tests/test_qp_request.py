"""Tests for scripts/qp_request.py. Never reaches the network: urlopen is mocked."""
from __future__ import annotations

import base64
import io
import json
import socket
import sys
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import qp_request  # noqa: E402

MERCHANT = "7"
PROJECT = "42"
SENTINEL = "SENTINEL-KEY-7d41c0ffee"
ENV_FULL = {
    "XSOLLA_MERCHANT_ID": MERCHANT,
    "XSOLLA_PROJECT_ID": PROJECT,
    "XSOLLA_PROJECT_API_KEY": SENTINEL,
}
SENTINEL_TOKEN = base64.b64encode(f"{MERCHANT}:{SENTINEL}".encode()).decode()


def fake_response(status: int = 200, body: bytes = b'{"quests": []}') -> mock.MagicMock:
    resp = mock.MagicMock()
    resp.status = status
    resp.read.return_value = body
    return resp


class CliTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        patcher = mock.patch("urllib.request.urlopen")
        self.urlopen = patcher.start()
        self.urlopen.return_value = fake_response()
        self.addCleanup(patcher.stop)
        self.addCleanup(self._tmp.cleanup)

    def run_cli(self, argv, environ=None, cwd=None):
        out, err = io.StringIO(), io.StringIO()
        env = {} if environ is None else environ
        with redirect_stdout(out), redirect_stderr(err):
            code = qp_request.main(argv, environ=env, cwd=str(cwd or self.tmp))
        return code, out.getvalue(), err.getvalue()

    def write_dotenv(self, text: str, folder: Path | None = None) -> None:
        (folder or self.tmp).joinpath(".env").write_text(text, encoding="utf-8")


class CredentialTests(CliTestCase):
    def test_env_credentials_are_used(self) -> None:
        code, out, _ = self.run_cli(["whoami"], environ=dict(ENV_FULL))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), {"ok": True, "merchant_id": MERCHANT, "project_id": PROJECT})

    def test_request_carries_basic_auth_from_env(self) -> None:
        code, _, _ = self.run_cli(["GET", f"/api/v2/merchants/{MERCHANT}/projects/{PROJECT}/quests"],
                                  environ=dict(ENV_FULL))
        self.assertEqual(code, 0)
        req = self.urlopen.call_args.args[0]
        self.assertEqual(req.get_header("Authorization"), "Basic " + SENTINEL_TOKEN)

    def test_dotenv_only_is_read_as_text(self) -> None:
        self.write_dotenv(
            "# comment\n\n"
            "XSOLLA_MERCHANT_ID=\"7\"\n"
            "export XSOLLA_PROJECT_ID='42'\n"
            f"XSOLLA_PROJECT_API_KEY={SENTINEL}\n"
        )
        code, out, _ = self.run_cli(["whoami"], environ={})
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), {"ok": True, "merchant_id": MERCHANT, "project_id": PROJECT})

    def test_incomplete_env_falls_back_to_complete_dotenv_only(self) -> None:
        self.write_dotenv(f"XSOLLA_MERCHANT_ID=99\nXSOLLA_PROJECT_ID=98\nXSOLLA_PROJECT_API_KEY={SENTINEL}\n")
        code, out, _ = self.run_cli(["whoami"], environ={"XSOLLA_MERCHANT_ID": "1"})
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["merchant_id"], "99")

    def test_mixed_incomplete_sources_are_refused(self) -> None:
        self.write_dotenv(f"XSOLLA_PROJECT_API_KEY={SENTINEL}\n")
        environ = {"XSOLLA_MERCHANT_ID": MERCHANT, "XSOLLA_PROJECT_ID": PROJECT}
        code, out, _ = self.run_cli(["GET", "/api/v2/merchants/7/projects/42/quests"], environ=environ)
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(out), {"ok": False, "error": "access_not_configured"})
        self.urlopen.assert_not_called()

    def test_no_credentials_is_access_not_configured(self) -> None:
        code, out, _ = self.run_cli(["whoami"], environ={})
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(out), {"ok": False, "error": "access_not_configured"})

    def test_secret_never_reaches_stdout_or_stderr(self) -> None:
        echoed = f"bad key {SENTINEL} and {SENTINEL_TOKEN}".encode()
        self.urlopen.side_effect = urllib.error.HTTPError(
            "https://quests-platform.xsolla.com", 401, "Unauthorized", {}, io.BytesIO(echoed))
        code, out, err = self.run_cli(["GET", "/api/v2/merchants/7/projects/42/quests"], environ=dict(ENV_FULL))
        self.assertEqual(code, 1)
        self.assertIn("access_denied", out)
        self.assertNotIn(SENTINEL, out + err)
        self.assertNotIn(SENTINEL_TOKEN, out + err)

    def test_secret_absent_from_network_error_detail(self) -> None:
        self.urlopen.side_effect = urllib.error.URLError(f"failed with {SENTINEL} {SENTINEL_TOKEN}")
        code, out, err = self.run_cli(["GET", "/api/v2/merchants/7/projects/42/quests"], environ=dict(ENV_FULL))
        self.assertEqual(code, 1)
        result = json.loads(out)
        self.assertEqual(result["error"], "network")
        self.assertIn("detail", result)
        self.assertNotIn(SENTINEL, out + err)
        self.assertNotIn(SENTINEL_TOKEN, out + err)

    def test_secret_absent_from_whoami_and_refusals(self) -> None:
        for argv in (["whoami"], ["DELETE", "/api/v1/x"], ["GET", "/api/v2/merchants/1/projects/42/quests"]):
            code, out, err = self.run_cli(argv, environ=dict(ENV_FULL))
            self.assertNotIn(SENTINEL, out + err, argv)
            self.assertNotIn(SENTINEL_TOKEN, out + err, argv)


class TargetTests(CliTestCase):
    def assert_refused(self, argv, error, code=2, environ=None):
        result_code, out, err = self.run_cli(argv, environ=dict(ENV_FULL) if environ is None else environ)
        self.assertEqual(result_code, code, argv)
        self.assertEqual(json.loads(out), {"ok": False, "error": error}, argv)
        self.urlopen.assert_not_called()

    def test_disallowed_quest_platform_paths(self) -> None:
        for path in ("/api/v1/quests", "/api/v2/../admin", "//evil.example/api/v2/x",
                     "https://evil.example/api/v2/x", "/api/v2/x?x=1", "api/v2/quests",
                     "/api/v2/quests%2e%2e/x", "/api/v2/quests/a b"):
            with self.subTest(path=path):
                self.assert_refused(["GET", path], "target_not_allowed")

    def test_disallowed_methods_and_store_routes(self) -> None:
        self.assert_refused(["HEAD", "/api/v2/merchants/7/projects/42/quests"], "target_not_allowed")
        self.assert_refused(["POST", "/api/v2/project/42/admin/items/virtual_items", "--store"],
                            "target_not_allowed")
        self.assert_refused(["DELETE", "/api/v2/project/42/admin/items/virtual_items/sku/A", "--store"],
                            "target_not_allowed")
        self.assert_refused(["GET", "/api/v2/project/42/admin/items/other", "--store"], "target_not_allowed")
        self.assert_refused(["GET", "/api/v2/project/42/admin/items/virtual_items/sku/../x", "--store"],
                            "target_not_allowed")

    def test_scope_mismatch_on_merchant_or_project_segment(self) -> None:
        self.assert_refused(["GET", "/api/v2/merchants/999/projects/42/quests"], "scope_mismatch")
        self.assert_refused(["GET", "/api/v2/merchants/7/projects/999/quests"], "scope_mismatch")
        self.assert_refused(["GET", "/api/v2/project/999/admin/items/virtual_items", "--store"], "scope_mismatch")

    def test_quest_platform_url_and_query(self) -> None:
        code, out, _ = self.run_cli(
            ["GET", "/api/v2/merchants/7/projects/42/quests", "--query", "page=1", "--query", "limit=50"],
            environ=dict(ENV_FULL))
        self.assertEqual(code, 0)
        req = self.urlopen.call_args.args[0]
        self.assertEqual(req.full_url,
                         "https://quests-platform.xsolla.com/api/v2/merchants/7/projects/42/quests?page=1&limit=50")
        self.assertEqual(req.get_method(), "GET")
        self.assertEqual(json.loads(out), {"ok": True, "status": 200, "body": {"quests": []}})

    def test_store_list_url(self) -> None:
        code, _, _ = self.run_cli(
            ["GET", "/api/v2/project/{project_id}/admin/items/virtual_items", "--store",
             "--query", "limit=50", "--query", "offset=0"], environ=dict(ENV_FULL))
        self.assertEqual(code, 0)
        req = self.urlopen.call_args.args[0]
        self.assertEqual(req.full_url,
                         "https://store.xsolla.com/api/v2/project/42/admin/items/virtual_items?limit=50&offset=0")
        self.assertEqual(req.get_header("Authorization"), "Basic " + SENTINEL_TOKEN)

    def test_store_sku_url(self) -> None:
        code, _, _ = self.run_cli(
            ["GET", "/api/v2/project/42/admin/items/virtual_items/sku/FIRE_SWORD_01", "--store"],
            environ=dict(ENV_FULL))
        self.assertEqual(code, 0)
        self.assertEqual(self.urlopen.call_args.args[0].full_url,
                         "https://store.xsolla.com/api/v2/project/42/admin/items/virtual_items/sku/FIRE_SWORD_01")

    def test_urlopen_gets_timeout(self) -> None:
        self.run_cli(["GET", "/api/v2/merchants/7/projects/42/quests"], environ=dict(ENV_FULL))
        self.assertEqual(self.urlopen.call_args.kwargs.get("timeout"), 20)


class ResponseTests(CliTestCase):
    def test_401_and_403_are_access_denied(self) -> None:
        for status in (401, 403):
            with self.subTest(status=status):
                self.urlopen.side_effect = urllib.error.HTTPError(
                    "https://quests-platform.xsolla.com", status, "x", {}, io.BytesIO(b"Invalid credentials"))
                code, out, _ = self.run_cli(["GET", "/api/v2/merchants/7/projects/42/quests"],
                                            environ=dict(ENV_FULL))
                self.assertEqual(code, 1)
                result = json.loads(out)
                self.assertEqual(result, {"ok": False, "status": status, "body": "Invalid credentials",
                                          "error": "access_denied"})

    def test_other_error_status_has_no_access_denied(self) -> None:
        self.urlopen.side_effect = urllib.error.HTTPError(
            "https://quests-platform.xsolla.com", 500, "x", {}, io.BytesIO(b'{"detail": "boom"}'))
        code, out, _ = self.run_cli(["GET", "/api/v2/merchants/7/projects/42/quests"], environ=dict(ENV_FULL))
        self.assertEqual(code, 1)
        result = json.loads(out)
        self.assertEqual(result, {"ok": False, "status": 500, "body": {"detail": "boom"}})

    def test_non_json_text_is_truncated(self) -> None:
        self.urlopen.return_value = fake_response(200, b"a" * 25000)
        code, out, _ = self.run_cli(["GET", "/api/v2/merchants/7/projects/42/quests"], environ=dict(ENV_FULL))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["body"], "a" * 20000)

    def test_timeout_and_connection_errors_are_network(self) -> None:
        for exc in (socket.timeout("timed out"), urllib.error.URLError("no route")):
            with self.subTest(exc=type(exc).__name__):
                self.urlopen.side_effect = exc
                code, out, _ = self.run_cli(["GET", "/api/v2/merchants/7/projects/42/quests"],
                                            environ=dict(ENV_FULL))
                self.assertEqual(code, 1)
                result = json.loads(out)
                self.assertFalse(result["ok"])
                self.assertEqual(result["error"], "network")
                self.assertIn("detail", result)


class BodyTests(CliTestCase):
    def test_body_file_sent_as_json(self) -> None:
        body_path = self.tmp / "quest.json"
        body_path.write_text('{"name": "Hello"}', encoding="utf-8")
        code, _, _ = self.run_cli(
            ["POST", "/api/v2/merchants/7/projects/42/quests", "--body-file", str(body_path)],
            environ=dict(ENV_FULL))
        self.assertEqual(code, 0)
        req = self.urlopen.call_args.args[0]
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(req.data, b'{"name": "Hello"}')
        self.assertEqual(req.get_header("Content-type"), "application/json")
        self.assertEqual(req.get_header("Authorization"), "Basic " + SENTINEL_TOKEN)

    def test_invalid_body_file_is_refused(self) -> None:
        body_path = self.tmp / "bad.json"
        body_path.write_text("{not json", encoding="utf-8")
        code, out, _ = self.run_cli(
            ["POST", "/api/v2/merchants/7/projects/42/quests", "--body-file", str(body_path)],
            environ=dict(ENV_FULL))
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(out), {"ok": False, "error": "invalid_body"})
        self.urlopen.assert_not_called()

    def test_get_with_body_file_is_refused(self) -> None:
        body_path = self.tmp / "b.json"
        body_path.write_text("{}", encoding="utf-8")
        code, out, _ = self.run_cli(
            ["GET", "/api/v2/merchants/7/projects/42/quests", "--body-file", str(body_path)],
            environ=dict(ENV_FULL))
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(out), {"ok": False, "error": "invalid_body"})
        self.urlopen.assert_not_called()


class WhoamiTests(CliTestCase):
    def test_whoami_prints_ids_only(self) -> None:
        code, out, _ = self.run_cli(["whoami"], environ=dict(ENV_FULL))
        self.assertEqual(code, 0)
        self.assertEqual(set(json.loads(out)), {"ok", "merchant_id", "project_id"})
        self.urlopen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
