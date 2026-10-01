from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import preflight  # noqa: E402

SANDBOX = {"merchant_id": 11, "project_id": 22, "sandbox": True}
TEST = {"merchant_id": 11, "project_id": 22, "sandbox": False}
APPROVAL = {"merchant_id": 11, "project_id": 22, "approved_by": "Product owner",
            "approval_reference": "approval thread"}


def allowlist(*projects: dict, version: int = 1) -> Path:
    fh = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    json.dump({"version": version, "projects": list(projects)}, fh)
    fh.close()
    return Path(fh.name)


class CheckProjectTest(unittest.TestCase):
    def test_sandbox_needs_no_allowlist(self):
        self.assertIsNone(preflight.check_project(11, 22, "sandbox", config=SANDBOX))

    def test_listed_test_project_passes(self):
        approval = preflight.check_project(11, 22, "test", allowlist(APPROVAL), config=TEST)
        self.assertEqual(approval["approved_by"], "Product owner")

    def test_test_project_without_allowlist_stops(self):
        with self.assertRaisesRegex(RuntimeError, "--approved-test-projects is required"):
            preflight.check_project(11, 22, "test", config=TEST)

    def test_unlisted_test_project_stops(self):
        other = {**APPROVAL, "project_id": 99}
        with self.assertRaisesRegex(RuntimeError, "not in the approved test-project allowlist"):
            preflight.check_project(11, 22, "test", allowlist(other), config=TEST)

    def test_cli_pointing_at_another_project_stops(self):
        with self.assertRaisesRegex(RuntimeError, "does not match the target"):
            preflight.check_project(11, 22, "sandbox", config={**SANDBOX, "project_id": 99})

    def test_sandbox_flag_must_match_the_environment(self):
        with self.assertRaisesRegex(RuntimeError, "sandbox setting"):
            preflight.check_project(11, 22, "sandbox", config=TEST)
        with self.assertRaisesRegex(RuntimeError, "sandbox setting"):
            preflight.check_project(11, 22, "test", allowlist(APPROVAL), config=SANDBOX)

    def test_approval_fields_are_required(self):
        for field in ("approved_by", "approval_reference"):
            with self.subTest(field=field):
                with self.assertRaisesRegex(RuntimeError, field):
                    preflight.check_project(11, 22, "test", allowlist({**APPROVAL, field: " "}),
                                            config=TEST)

    def test_malformed_allowlist_stops(self):
        with self.assertRaisesRegex(RuntimeError, "version 1"):
            preflight.check_project(11, 22, "test", allowlist(APPROVAL, version=2), config=TEST)
        with self.assertRaisesRegex(RuntimeError, "integer IDs"):
            preflight.check_project(11, 22, "test", allowlist({**APPROVAL, "project_id": "22"}),
                                    config=TEST)


class CliConfigTest(unittest.TestCase):
    def test_unwraps_the_cli_envelope(self):
        done = mock.Mock(stdout=json.dumps({"ok": True, "data": SANDBOX}))
        with mock.patch.object(preflight.subprocess, "run", return_value=done):
            self.assertEqual(preflight.cli_config(), SANDBOX)

    def test_missing_config_names_the_fix(self):
        done = mock.Mock(stdout="Config file .xsolla.json not found in current or home directory")
        with mock.patch.object(preflight.subprocess, "run", return_value=done):
            with self.assertRaisesRegex(RuntimeError, "xsolla config init"):
                preflight.cli_config()


class MainTest(unittest.TestCase):
    def test_refusal_exits_one_on_stderr(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.object(preflight, "cli_config", return_value=TEST), \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = preflight.main(
                ["--merchant-id", "11", "--project-id", "22", "--environment", "test"]
            )
        self.assertEqual((code, stdout.getvalue()), (1, ""))
        self.assertIn("--approved-test-projects", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
