from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location(
    "portal_template", ROOT / "scripts" / "portal_template.py"
)
portal_template = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(portal_template)

BASE = "https://sitebuilder.xsolla.com/api/merchant/11/project/22/landing"
TARGET = ["--merchant-id", "11", "--project-id", "22", "--environment", "sandbox"]


class FakeResponse:
    def __init__(self, status: int, body: bytes):
        self.status = status
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def run_main(argv: list[str]) -> tuple[int, str, str]:
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = portal_template.main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


class ParseArgsTest(unittest.TestCase):
    def test_portal_requires_a_layout(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            portal_template.parse_args(["portal", *TARGET, "--domain", "d"])

    def test_requires_an_environment(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            portal_template.parse_args(
                ["portal", "--merchant-id", "11", "--project-id", "22", "--domain", "d", "--hub"]
            )

    def test_rejects_non_positive_ids(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            portal_template.parse_args(
                ["portal", "--merchant-id", "0", "--project-id", "22", "--environment", "sandbox",
                 "--domain", "d", "--hub"]
            )

    def test_rejects_unknown_template(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            portal_template.parse_args(
                ["template", *TARGET, "--domain", "d", "--template", "community"]
            )


class BuildRequestTest(unittest.TestCase):
    def test_portal_hub(self):
        args = portal_template.parse_args(["portal", *TARGET, "--domain", "voidwall", "--hub"])
        self.assertEqual(
            portal_template.build_request(args),
            (f"{BASE}/voidwall/portal", {"isSinglePage": False}),
        )

    def test_portal_single_page(self):
        args = portal_template.parse_args(
            ["portal", *TARGET, "--domain", "voidwall", "--single-page"]
        )
        self.assertEqual(portal_template.build_request(args)[1], {"isSinglePage": True})

    def test_template_defaults_to_steam(self):
        args = portal_template.parse_args(
            ["template", *TARGET, "--domain", "voidwall", "--template", "news"]
        )
        self.assertEqual(
            portal_template.build_request(args),
            (f"{BASE}/voidwall/template", {"type": "steam", "template": "news"}),
        )

    def test_domain_cannot_escape_the_path(self):
        args = portal_template.parse_args(["portal", *TARGET, "--domain", "a/../b", "--hub"])
        self.assertEqual(portal_template.build_request(args)[0], f"{BASE}/a%2F..%2Fb/portal")


class SessionTest(unittest.TestCase):
    def test_a_session_passed_by_hand_is_ignored(self):
        get_cookies = mock.Mock(return_value={"pa-v4-token": "from-login"})
        with mock.patch.dict(os.environ, {"XSOLLA_SHOPBUILDER_SESSION": "pa-v4-token=by-hand"}):
            header = portal_template.session_header(
                11, 22, get_token=lambda: "jwt", get_cookies=get_cookies
            )
        self.assertIn("pa-v4-token=from-login", header)
        self.assertNotIn("by-hand", header)

    def test_bootstraps_from_cli_login(self):
        get_cookies = mock.Mock(return_value={"pa-v4-token": "abc"})
        header = portal_template.session_header(
            11, 22, get_token=lambda: "jwt", get_cookies=get_cookies
        )
        get_cookies.assert_called_once_with("jwt")
        self.assertEqual(
            header,
            "pa-merchant-id=11; pa-v4-token=abc; sb-pa-merchant-id=11; sb-pa-project-id=22",
        )

    def test_cookie_header_drops_empty_values(self):
        self.assertNotIn("empty", portal_template.cookie_header({"empty": ""}, 1, 2))

    def test_missing_login_is_a_clear_error(self):
        failed = mock.Mock(returncode=1, stdout="")
        with mock.patch.object(portal_template.subprocess, "run", return_value=failed):
            with self.assertRaisesRegex(RuntimeError, "xsolla auth login"):
                portal_template.publisher_token()


class SendTest(unittest.TestCase):
    def test_sends_json_with_session_headers(self):
        urlopen = mock.Mock(return_value=FakeResponse(200, b'{"domain": "voidwall"}'))
        status, body = portal_template.send(
            f"{BASE}/voidwall/portal", {"isSinglePage": False}, "pa-v4-token=abc", 11, 22, urlopen
        )
        request = urlopen.call_args.args[0]
        self.assertEqual((status, body), (200, {"domain": "voidwall"}))
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(json.loads(request.data), {"isSinglePage": False})
        self.assertEqual(request.get_header("Cookie"), "pa-v4-token=abc")
        self.assertEqual(
            request.get_header("Referer"),
            "https://publisher.xsolla.com/11/projects/22/site-builder",
        )

    def test_http_error_returns_status_and_body(self):
        url = f"{BASE}/voidwall/portal"
        error = urllib.error.HTTPError(
            url, 409, "Conflict", {}, io.BytesIO(b"landing already has a type")
        )
        urlopen = mock.Mock(side_effect=error)
        self.assertEqual(
            portal_template.send(url, {}, "c", 11, 22, urlopen),
            (409, "landing already has a type"),
        )


class OutcomeTest(unittest.TestCase):
    def test_success(self):
        result = portal_template.outcome("portal", 200, {"domain": "voidwall"})
        self.assertEqual((result["ok"], result["status"]), (True, "applied"))

    def test_portal_conflict_means_resume(self):
        result = portal_template.outcome("portal", 409, None)
        self.assertEqual((result["ok"], result["status"]), (True, "already_initialized"))

    def test_template_conflict_is_a_failure(self):
        result = portal_template.outcome("template", 409, None)
        self.assertEqual((result["ok"], result["status"]), (False, "failed"))

    def test_status_mapping(self):
        for http_status, expected in ((401, "needs_access"), (403, "needs_access"),
                                      (404, "needs_human"), (400, "failed"), (500, "failed")):
            with self.subTest(http_status=http_status):
                self.assertEqual(portal_template.outcome("portal", http_status, None)["status"],
                                 expected)


class MainTest(unittest.TestCase):
    ARGS = ["portal", *TARGET, "--domain", "voidwall", "--hub"]

    def test_dry_run_makes_no_calls(self):
        with mock.patch.object(portal_template, "check_project",
                               side_effect=AssertionError("dry run must not check the project")), \
                mock.patch.object(portal_template, "session_header",
                                  side_effect=AssertionError("dry run must not authenticate")):
            code, out, _ = run_main([*self.ARGS, "--dry-run"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["url"], f"{BASE}/voidwall/portal")

    def test_an_unapproved_project_stops_before_login_and_write(self):
        with mock.patch.object(portal_template, "check_project",
                               side_effect=RuntimeError("not in the test-project allowlist")), \
                mock.patch.object(portal_template, "session_header",
                                  side_effect=AssertionError("must not authenticate")), \
                mock.patch.object(portal_template, "send",
                                  side_effect=AssertionError("must not write")):
            code, out, err = run_main(self.ARGS)
        self.assertEqual((code, out), (1, ""))
        self.assertIn("allowlist", err)

    def test_checks_the_target_it_writes_to(self):
        check = mock.Mock(return_value=None)
        with mock.patch.object(portal_template, "check_project", check), \
                mock.patch.object(portal_template, "session_header", return_value="c"), \
                mock.patch.object(portal_template, "send", return_value=(200, {})):
            code, _, _ = run_main(self.ARGS)
        self.assertEqual(code, 0)
        check.assert_called_once_with(11, 22, "sandbox", None)

    def test_failure_exits_one(self):
        with mock.patch.object(portal_template, "check_project", return_value=None), \
                mock.patch.object(portal_template, "session_header", return_value="c"), \
                mock.patch.object(portal_template, "send", return_value=(403, None)):
            code, out, _ = run_main(self.ARGS)
        self.assertEqual((code, json.loads(out)["status"]), (1, "needs_access"))

    def test_auth_error_goes_to_stderr_without_the_token(self):
        with mock.patch.object(portal_template, "check_project", return_value=None), \
                mock.patch.object(portal_template, "session_header",
                                  side_effect=RuntimeError("session bootstrap failed (HTTP 401)")):
            code, out, err = run_main(self.ARGS)
        self.assertEqual((code, out), (1, ""))
        self.assertIn("HTTP 401", err)


if __name__ == "__main__":
    unittest.main()
