"""Tests for scripts/qp_request.py. Never reaches the network: the opener or the HTTPS handler is mocked."""
from __future__ import annotations

import base64
import email.message
import http.client
import io
import json
import socket
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
import urllib.response
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
QUESTS = "/api/v2/merchants/7/projects/42/quests"


def fake_response(status: int = 200, body: bytes = b'{"quests": []}') -> mock.MagicMock:
    resp = mock.MagicMock()
    resp.status = status
    resp.read.return_value = body
    return resp


class CliTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        # Patched on the class, so the mock is called without `self`: args[0] is the Request.
        patcher = mock.patch.object(urllib.request.OpenerDirector, "open")
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
    def test_named_credential_sources(self) -> None:
        quoted = ("# comment\n\nXSOLLA_MERCHANT_ID=\"7\"\nexport XSOLLA_PROJECT_ID='42'\n"
                  f"XSOLLA_PROJECT_API_KEY={SENTINEL}\n")
        exported = ("export XSOLLA_MERCHANT_ID='7'\nexport XSOLLA_PROJECT_ID=\"42\"\n"
                    f"export XSOLLA_PROJECT_API_KEY = \"{SENTINEL}\"\n")
        rows = [
            ("env_whoami", dict(ENV_FULL), None, ["whoami"], ("7", "42")),
            ("env_request", dict(ENV_FULL), None, ["GET", QUESTS], ("7", "42")),
            ("quoted_dotenv", {}, quoted, ["whoami"], ("7", "42")),
            ("incomplete_env_complete_dotenv", {"XSOLLA_MERCHANT_ID": "1"},
             f"XSOLLA_MERCHANT_ID=99\nXSOLLA_PROJECT_ID=98\nXSOLLA_PROJECT_API_KEY={SENTINEL}\n",
             ["whoami"], ("99", "98")),
            ("mixed_incomplete_sources", {"XSOLLA_MERCHANT_ID": "7", "XSOLLA_PROJECT_ID": "42"},
             f"XSOLLA_PROJECT_API_KEY={SENTINEL}\n", ["GET", QUESTS], None),
            ("exported_quoted_request", {}, exported, ["GET", QUESTS], ("7", "42")),
            ("no_credentials", {}, None, ["whoami"], None),
        ]
        for merchant, project in (("abc", "42"), ("7", "4x2"), ("7", "-42"), ("1e3", "42")):
            rows.append((f"invalid_ids_{merchant}_{project}", {},
                         f"XSOLLA_MERCHANT_ID={merchant}\nXSOLLA_PROJECT_ID={project}\n"
                         f"XSOLLA_PROJECT_API_KEY={SENTINEL}\n", ["GET", QUESTS], None))
        for case, environ, dotenv, argv, ids in rows:
            with self.subTest(case=case):
                self.urlopen.reset_mock(return_value=True, side_effect=True)
                self.urlopen.return_value = fake_response()
                (self.tmp / ".env").unlink(missing_ok=True)
                if dotenv is not None:
                    self.write_dotenv(dotenv)
                code, out, err = self.run_cli(argv, environ=dict(environ))
                self.assertEqual(err, "")
                self.assertNotIn(SENTINEL, out + err)
                if ids is None:
                    self.assertEqual(code, 2)
                    self.assertEqual(json.loads(out), {"ok": False, "error": "access_not_configured"})
                    self.urlopen.assert_not_called()
                else:
                    self.assertEqual(code, 0)
                    if argv == ["whoami"]:
                        self.assertEqual(json.loads(out), {"ok": True, "merchant_id": ids[0], "project_id": ids[1]})
                        self.urlopen.assert_not_called()
                    else:
                        self.urlopen.assert_called_once()
                        self.assertEqual(self.urlopen.call_args.args[0].get_header("Authorization"),
                                         "Basic " + SENTINEL_TOKEN)

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
            with self.subTest(argv=argv):
                code, out, err = self.run_cli(argv, environ=dict(ENV_FULL))
                self.assertNotIn(SENTINEL, out + err, argv)
                self.assertNotIn(SENTINEL_TOKEN, out + err, argv)


class TargetTests(CliTestCase):
    def assert_refused(self, argv, error, code=2, environ=None):
        self.urlopen.reset_mock(return_value=True, side_effect=True)
        result_code, out, err = self.run_cli(argv, environ=dict(ENV_FULL) if environ is None else environ)
        self.assertEqual(result_code, code, argv)
        self.assertEqual(err, "", argv)
        self.assertEqual(json.loads(out), {"ok": False, "error": error}, argv)
        self.urlopen.assert_not_called()

    def test_disallowed_quest_platform_paths(self) -> None:
        for path in ("/api/v1/quests", "/api/v2/../admin", "//evil.example/api/v2/x",
                     "https://evil.example/api/v2/x", "/api/v2/x?x=1", "api/v2/quests",
                     "/api/v2/quests%2e%2e/x", "/api/v2/quests/a b"):
            with self.subTest(path=path):
                self.assert_refused(["GET", path], "target_not_allowed")

    def test_disallowed_methods_and_store_routes(self) -> None:
        rows = (
            ("qp_head", ["HEAD", QUESTS]),
            ("store_post", ["POST", "/api/v2/project/42/admin/items/virtual_items", "--store"]),
            ("store_delete", ["DELETE", "/api/v2/project/42/admin/items/virtual_items/sku/A", "--store"]),
            ("store_other_kind", ["GET", "/api/v2/project/42/admin/items/other", "--store"]),
            ("store_sku_traversal", ["GET", "/api/v2/project/42/admin/items/virtual_items/sku/../x", "--store"]),
        )
        for case, argv in rows:
            with self.subTest(case=case):
                self.assert_refused(argv, "target_not_allowed")

    def test_public_quest_list_is_get_only_and_sends_no_credential(self) -> None:
        public = "/api/v2/public/merchants/7/projects/42/quests"
        code, out, _ = self.run_cli(["GET", public, "--public"], environ=dict(ENV_FULL))
        self.assertEqual(code, 0, out)
        request = self.urlopen.call_args.args[0]
        self.assertEqual("https://quests-platform.xsolla.com" + public, request.full_url)
        self.assertIsNone(request.get_header("Authorization"))
        for case, argv, error in (
            ("post", ["POST", public, "--public"], "target_not_allowed"),
            ("without_flag", ["GET", public], "target_not_allowed"),
            ("other_public", ["GET", "/api/v2/public/accounts/x/quests", "--public"], "target_not_allowed"),
            ("with_store", ["GET", public, "--public", "--store"], "target_not_allowed"),
            ("other_project", ["GET", "/api/v2/public/merchants/7/projects/999/quests", "--public"], "scope_mismatch"),
        ):
            with self.subTest(case=case):
                self.assert_refused(argv, error)

    def test_onboard_route_is_refused_outside_preflight(self) -> None:
        self.assert_refused(["POST", "/api/v2/merchants/7/projects/42/onboard"], "target_not_allowed")

    def test_scope_mismatch_on_merchant_or_project_segment(self) -> None:
        rows = (
            ("merchant", ["GET", "/api/v2/merchants/999/projects/42/quests"]),
            ("qp_project", ["GET", "/api/v2/merchants/7/projects/999/quests"]),
            ("store_project", ["GET", "/api/v2/project/999/admin/items/virtual_items", "--store"]),
        )
        for case, argv in rows:
            with self.subTest(case=case):
                self.assert_refused(argv, "scope_mismatch")

    def test_named_allowed_urls(self) -> None:
        rows = (
            ("qp_query", ["GET", QUESTS, "--query", "page=1", "--query", "limit=50"],
             "https://quests-platform.xsolla.com/api/v2/merchants/7/projects/42/quests?page=1&limit=50"),
            ("store_placeholder_list", ["GET", "/api/v2/project/{project_id}/admin/items/virtual_items", "--store",
                                        "--query", "limit=50", "--query", "offset=0"],
             "https://store.xsolla.com/api/v2/project/42/admin/items/virtual_items?limit=50&offset=0"),
            ("store_concrete_sku", ["GET", "/api/v2/project/42/admin/items/virtual_items/sku/FIRE_SWORD_01", "--store"],
             "https://store.xsolla.com/api/v2/project/42/admin/items/virtual_items/sku/FIRE_SWORD_01"),
        )
        for case, argv, url in rows:
            with self.subTest(case=case):
                self.urlopen.reset_mock(return_value=True, side_effect=True)
                self.urlopen.return_value = fake_response()
                code, out, err = self.run_cli(argv, environ=dict(ENV_FULL))
                self.assertEqual(code, 0)
                self.assertEqual(err, "")
                self.assertEqual(json.loads(out), {"ok": True, "status": 200, "body": {"quests": []}})
                self.urlopen.assert_called_once()
                req = self.urlopen.call_args.args[0]
                self.assertEqual(req.full_url, url)
                self.assertEqual(req.get_method(), "GET")
                self.assertEqual(req.get_header("Authorization"), "Basic " + SENTINEL_TOKEN)

    def test_invalid_query_key_is_refused(self) -> None:
        for pair in ("a b=1", "page", "=1", "k&x=1", "k?=1"):
            with self.subTest(pair=pair):
                self.assert_refused(["GET", "/api/v2/merchants/7/projects/42/quests", "--query", pair],
                                    "invalid_query")

    def test_global_opener_is_not_installed(self) -> None:
        with mock.patch("urllib.request.install_opener") as install:
            code, _, _ = self.run_cli(["GET", "/api/v2/merchants/7/projects/42/quests"], environ=dict(ENV_FULL))
        self.assertEqual(code, 0)
        install.assert_not_called()

    def test_urlopen_gets_timeout(self) -> None:
        self.run_cli(["GET", "/api/v2/merchants/7/projects/42/quests"], environ=dict(ENV_FULL))
        self.assertEqual(self.urlopen.call_args.kwargs.get("timeout"), 20)


class ResponseTests(CliTestCase):
    def test_named_http_errors(self) -> None:
        rows = (
            ("unauthorized", 401, b"Invalid credentials",
             {"ok": False, "status": 401, "body": "Invalid credentials", "error": "access_denied"}),
            ("forbidden", 403, b"Invalid credentials",
             {"ok": False, "status": 403, "body": "Invalid credentials", "error": "access_denied"}),
            ("server_error", 500, b'{"detail": "boom"}',
             {"ok": False, "status": 500, "body": {"detail": "boom"}}),
        )
        for case, status, body, expected in rows:
            with self.subTest(case=case):
                self.urlopen.reset_mock(return_value=True, side_effect=True)
                self.urlopen.side_effect = urllib.error.HTTPError(
                    "https://quests-platform.xsolla.com", status, "x", {}, io.BytesIO(body))
                code, out, err = self.run_cli(["GET", QUESTS], environ=dict(ENV_FULL))
                self.assertEqual(code, 1)
                self.assertEqual(err, "")
                self.assertEqual(json.loads(out), expected)

    def test_non_json_text_is_truncated(self) -> None:
        self.urlopen.return_value = fake_response(200, b"a" * 25000)
        code, out, _ = self.run_cli(["GET", "/api/v2/merchants/7/projects/42/quests"], environ=dict(ENV_FULL))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["body"], "a" * 20000)

    def test_named_network_failures(self) -> None:
        rows = (
            ("timeout_at_open", lambda: socket.timeout("timed out"), False, None),
            ("urlerror_at_open", lambda: urllib.error.URLError("no route"), False, None),
            ("incomplete_at_open", lambda: http.client.IncompleteRead(b""), False, "IncompleteRead"),
            ("incomplete_at_read", lambda: http.client.IncompleteRead(b"partial"), True, "IncompleteRead"),
        )
        for case, error_factory, at_read, detail_prefix in rows:
            with self.subTest(case=case):
                self.urlopen.reset_mock(return_value=True, side_effect=True)
                self.urlopen.return_value = fake_response()
                if at_read:
                    self.urlopen.return_value.read.side_effect = error_factory()
                else:
                    self.urlopen.side_effect = error_factory()
                code, out, err = self.run_cli(["GET", QUESTS], environ=dict(ENV_FULL))
                self.assertEqual(code, 1)
                self.assertEqual(err, "")
                result = json.loads(out)
                self.assertEqual(result["ok"], False)
                self.assertEqual(result["error"], "network")
                self.assertIn("detail", result)
                if detail_prefix:
                    self.assertTrue(result["detail"].startswith(detail_prefix))


class RedirectTests(unittest.TestCase):
    """Uses the real opener; only the HTTPS handler is replaced, so redirect handling is exercised."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def test_3xx_is_not_followed(self) -> None:
        for status in (301, 302, 303, 307, 308):
            with self.subTest(status=status):
                seen = []

                def https_open(handler, req, status=status, seen=seen):
                    seen.append((req.full_url, req.get_header("Authorization")))
                    headers = email.message.Message()
                    headers["Location"] = "https://evil.example/steal"
                    resp = urllib.response.addinfourl(io.BytesIO(b"moved"), headers, req.full_url, code=status)
                    resp.msg = "Moved"
                    return resp

                out = io.StringIO()
                with mock.patch.object(urllib.request.HTTPSHandler, "https_open", https_open), \
                        redirect_stdout(out), redirect_stderr(io.StringIO()):
                    code = qp_request.main(["GET", "/api/v2/merchants/7/projects/42/quests"],
                                           environ=dict(ENV_FULL), cwd=self._tmp.name)
                self.assertEqual(code, 1)
                result = json.loads(out.getvalue())
                self.assertEqual(result["ok"], False)
                self.assertEqual(result["status"], status)
                self.assertEqual(len(seen), 1)
                self.assertEqual(seen[0][0],
                                 "https://quests-platform.xsolla.com/api/v2/merchants/7/projects/42/quests")
                self.assertNotIn("evil.example", out.getvalue().replace("moved", ""))


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

    def test_named_invalid_bodies(self) -> None:
        rows = (
            ("malformed_json", "POST", "{not json"),
            ("oversized_json", "POST", '"' + "a" * qp_request.MAX_BODY_FILE_BYTES + '"'),
            ("get_with_body", "GET", "{}"),
        )
        for case, method, body in rows:
            with self.subTest(case=case):
                self.urlopen.reset_mock(return_value=True, side_effect=True)
                body_path = self.tmp / f"{case}.json"
                body_path.write_text(body, encoding="utf-8")
                code, out, err = self.run_cli([method, QUESTS, "--body-file", str(body_path)],
                                             environ=dict(ENV_FULL))
                self.assertEqual(code, 2)
                self.assertEqual(err, "")
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
