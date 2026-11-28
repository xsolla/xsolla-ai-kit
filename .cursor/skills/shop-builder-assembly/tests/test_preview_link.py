"""The preview link is built from the token `enable-preview` answers with."""

from __future__ import annotations

import base64
import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


preview_link = load_module(
    "preview_link_for_tests", ROOT / "scripts" / "preview_link.py"
)

NOW = 1_800_000_000
HOST = "https://preview.xsollasitebuilder.com"


def token(expires_in: int | None = 3600, tail: str = "sig") -> str:
    """A token shaped like the service's: three dot-separated parts, claims in the middle."""
    claims = {"payload": "{}"}
    if expires_in is not None:
        claims["exp"] = NOW + expires_in
    middle = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    return f"head.{middle}.{tail}"


class FakeCli:
    """Read-only `xsolla` stand-in plus `enable-preview`; any other call fails the test."""

    def __init__(self, site: dict | None = None, answer: object = None, sandbox: bool = False):
        self.site = {"published": None, "publicPreview": {"enabled": False, "lastToken": ""}}
        self.site.update(site or {})
        self.answer = answer
        self.sandbox = sandbox
        self.calls: list[tuple[str, ...]] = []

    def __call__(self, *args: str) -> object:
        self.calls.append(args)
        if args == ("config", "list"):
            return {
                "ok": True,
                "data": {"merchant_id": 12345, "project_id": 67890, "sandbox": self.sandbox},
            }
        if args[:2] == ("shopbuilder", "get-structure"):
            return {"ok": True, "data": self.site}
        if args[:2] == ("shopbuilder", "enable-preview"):
            if isinstance(self.answer, Exception):
                raise self.answer
            return {"ok": True, "data": self.answer}
        raise AssertionError(f"unexpected CLI call: {args}")

    def commands(self) -> list[str]:
        return [call[1] for call in self.calls if call[0] == "shopbuilder"]


class PreviewLinkTests(unittest.TestCase):
    def run_script(self, cli: FakeCli, *argv: str) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with (
            mock.patch.object(sys, "argv", ["preview_link.py", *argv]),
            mock.patch.object(preview_link, "run_json", side_effect=cli),
            mock.patch.object(preview_link.time, "time", return_value=NOW),
            # No config file on disk: only the active CLI environment counts.
            mock.patch.object(preview_link.cli_environment, "config_in_use", return_value=None),
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            code = preview_link.main()
        return code, stdout.getvalue(), stderr.getvalue()

    def plan_file(self, directory: str, slug: str = "space-shop") -> str:
        path = Path(directory) / "approved-plan.json"
        plan = {"target": {"merchant_id": 12345, "project_id": 67890, "slug": slug}}
        path.write_text(json.dumps(plan), encoding="utf-8")
        return str(path)

    def test_the_link_is_the_host_the_slug_and_the_token(self) -> None:
        fresh = token()
        cli = FakeCli(answer={"enabled": True, "lastToken": fresh})
        with tempfile.TemporaryDirectory() as directory:
            code, stdout, stderr = self.run_script(cli, "--plan", self.plan_file(directory))
        self.assertEqual(0, code, stderr)
        report = json.loads(stdout)
        self.assertEqual(f"{HOST}/space-shop?publicToken={fresh}", report["preview_url"])
        self.assertEqual("space-shop", report["slug"])
        self.assertIs(False, report["reused"])
        self.assertEqual("anyone with the link", report["access"])
        self.assertEqual(
            "xsolla shopbuilder disable-preview --slug space-shop", report["switch_off"]
        )
        self.assertEqual(["get-structure", "enable-preview"], cli.commands())
        self.assertIn(
            ("shopbuilder", "enable-preview", "--slug", "space-shop"), cli.calls
        )

    def test_the_answer_may_be_the_whole_site(self) -> None:
        fresh = token()
        cli = FakeCli(answer={"publicPreview": {"enabled": True, "lastToken": fresh}})
        code, stdout, stderr = self.run_script(cli, "--slug", "space-shop")
        self.assertEqual(0, code, stderr)
        self.assertEqual(
            f"{HOST}/space-shop?publicToken={fresh}", json.loads(stdout)["preview_url"]
        )

    def test_a_preview_that_is_on_is_reused(self) -> None:
        # A link already handed over keeps working: no new token is asked for.
        current = token(expires_in=7200)
        cli = FakeCli(site={"publicPreview": {"enabled": True, "lastToken": current}})
        code, stdout, stderr = self.run_script(cli, "--slug", "space-shop")
        self.assertEqual(0, code, stderr)
        report = json.loads(stdout)
        self.assertEqual(f"{HOST}/space-shop?publicToken={current}", report["preview_url"])
        self.assertIs(True, report["reused"])
        self.assertEqual("2027-01-15T10:00:00Z", report["expires"])
        self.assertEqual(["get-structure"], cli.commands())

    def test_a_token_about_to_expire_is_replaced(self) -> None:
        fresh = token(tail="new")
        for expires_in in (-60, 60):
            with self.subTest(expires_in=expires_in):
                stale = token(expires_in=expires_in)
                cli = FakeCli(
                    site={"publicPreview": {"enabled": True, "lastToken": stale}},
                    answer={"enabled": True, "lastToken": fresh},
                )
                code, stdout, stderr = self.run_script(cli, "--slug", "space-shop")
                self.assertEqual(0, code, stderr)
                report = json.loads(stdout)
                self.assertTrue(report["preview_url"].endswith(fresh))
                self.assertIs(False, report["reused"])
                self.assertEqual(["get-structure", "enable-preview"], cli.commands())

    def test_a_preview_switched_off_is_not_reused(self) -> None:
        fresh = token(tail="new")
        cli = FakeCli(
            site={"publicPreview": {"enabled": False, "lastToken": token()}},
            answer={"enabled": True, "lastToken": fresh},
        )
        code, stdout, _ = self.run_script(cli, "--slug", "space-shop")
        self.assertEqual(0, code)
        self.assertTrue(json.loads(stdout)["preview_url"].endswith(fresh))

    def test_new_asks_for_a_new_token(self) -> None:
        fresh = token(tail="new")
        cli = FakeCli(
            site={"publicPreview": {"enabled": True, "lastToken": token()}},
            answer={"enabled": True, "lastToken": fresh},
        )
        code, stdout, _ = self.run_script(cli, "--slug", "space-shop", "--new")
        self.assertEqual(0, code)
        self.assertTrue(json.loads(stdout)["preview_url"].endswith(fresh))
        self.assertEqual(["get-structure", "enable-preview"], cli.commands())

    def test_a_token_with_no_readable_expiry_is_kept(self) -> None:
        opaque = "not-a-jwt"
        cli = FakeCli(site={"publicPreview": {"enabled": True, "lastToken": opaque}})
        code, stdout, _ = self.run_script(cli, "--slug", "space-shop")
        self.assertEqual(0, code)
        report = json.loads(stdout)
        self.assertIsNone(report["expires"])
        self.assertIs(True, report["reused"])

    def test_the_slug_and_the_token_are_escaped_in_the_link(self) -> None:
        cli = FakeCli(answer={"enabled": True, "lastToken": "a+b/c=d&e"})
        code, stdout, _ = self.run_script(cli, "--slug", "my shop")
        self.assertEqual(0, code)
        self.assertEqual(
            f"{HOST}/my%20shop?publicToken=a%2Bb%2Fc%3Dd%26e",
            json.loads(stdout)["preview_url"],
        )

    def test_a_published_site_is_refused_before_any_write(self) -> None:
        cli = FakeCli(site={"published": True})
        code, stdout, stderr = self.run_script(cli, "--slug", "space-shop")
        self.assertEqual(1, code)
        self.assertEqual("", stdout)
        self.assertIn("the site is published", stderr)
        self.assertEqual(["get-structure"], cli.commands())

    def test_a_refusal_by_the_service_names_the_browser_way(self) -> None:
        cli = FakeCli(
            answer=RuntimeError(
                "shopbuilder enable-preview --slug space-shop failed: HTTP 403 "
                "admin_privileges_requred"
            )
        )
        code, stdout, stderr = self.run_script(cli, "--slug", "space-shop")
        self.assertEqual(1, code)
        self.assertEqual("", stdout)
        self.assertIn("admin_privileges_requred", stderr)
        self.assertIn("open the preview in the browser", stderr)

    def test_an_answer_without_a_token_is_an_error(self) -> None:
        for answer in ({"enabled": True, "lastToken": ""}, {"enabled": True}, [], None):
            with self.subTest(answer=answer):
                code, stdout, stderr = self.run_script(
                    FakeCli(answer=answer), "--slug", "space-shop"
                )
                self.assertEqual(1, code)
                self.assertEqual("", stdout)
                self.assertIn("enable-preview returned no preview token", stderr)

    def test_sandbox_mode_stops_before_the_site_is_read(self) -> None:
        cli = FakeCli(sandbox=True)
        code, stdout, stderr = self.run_script(cli, "--slug", "space-shop")
        self.assertEqual(1, code)
        self.assertEqual("", stdout)
        self.assertIn("CLI sandbox mode is on", stderr)
        self.assertEqual([], cli.commands())

    def test_a_plan_of_another_project_stops_before_the_site_is_read(self) -> None:
        cli = FakeCli()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plan.json"
            path.write_text(
                json.dumps({"target": {"merchant_id": 1, "project_id": 2, "slug": "x"}}),
                encoding="utf-8",
            )
            code, _, stderr = self.run_script(cli, "--plan", str(path))
        self.assertEqual(1, code)
        self.assertIn("does not match", stderr)
        self.assertEqual([], cli.commands())

    def test_a_blank_slug_is_refused(self) -> None:
        cli = FakeCli()
        code, _, stderr = self.run_script(cli, "--slug", "  ")
        self.assertEqual(1, code)
        self.assertIn("no site slug", stderr)
        self.assertEqual([], cli.calls)

    def test_no_cli_is_a_message_not_a_traceback(self) -> None:
        stdout, stderr = io.StringIO(), io.StringIO()
        with (
            mock.patch.object(sys, "argv", ["preview_link.py", "--slug", "space-shop"]),
            mock.patch.object(
                preview_link, "run_json", side_effect=FileNotFoundError("xsolla")
            ),
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            code = preview_link.main()
        self.assertEqual(1, code)
        self.assertIn("xsolla", stderr.getvalue())


class TokenExpiryTests(unittest.TestCase):
    def test_the_expiry_is_read_from_the_tokens_claims(self) -> None:
        self.assertEqual(NOW + 3600, preview_link.token_expiry(token(expires_in=3600)))

    def test_anything_else_has_no_expiry(self) -> None:
        for value in ("", "abc", "a.b.c", "a.!!!.c", token(expires_in=None), "a.e30.c"):
            with self.subTest(value=value):
                self.assertIsNone(preview_link.token_expiry(value))


if __name__ == "__main__":
    unittest.main()
