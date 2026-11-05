from __future__ import annotations

import contextlib
import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import preflight  # noqa: E402

CONFIG = {"merchant_id": 11, "project_id": 22}


class CheckProjectTest(unittest.TestCase):
    def test_matching_project_passes(self):
        self.assertIsNone(preflight.check_project(11, 22, config=CONFIG))

    def test_cli_sandbox_mode_stops(self):
        with self.assertRaisesRegex(RuntimeError, "sandbox mode is on"):
            preflight.check_project(11, 22, config={**CONFIG, "sandbox": True})

    def test_cli_sandbox_off_or_missing_passes(self):
        for config in (CONFIG, {**CONFIG, "sandbox": False}):
            with self.subTest(config=config):
                self.assertIsNone(preflight.check_project(11, 22, config=config))

    def test_cli_pointing_at_another_project_stops(self):
        with self.assertRaisesRegex(RuntimeError, "does not match the target"):
            preflight.check_project(11, 22, config={**CONFIG, "project_id": 99})


class CliConfigTest(unittest.TestCase):
    def test_unwraps_the_cli_envelope(self):
        done = mock.Mock(stdout=json.dumps({"ok": True, "data": CONFIG}))
        with mock.patch.object(preflight.subprocess, "run", return_value=done):
            self.assertEqual(preflight.cli_config(), CONFIG)

    def test_cli_error_is_reported(self):
        done = mock.Mock(stdout=json.dumps({"ok": False, "error": "not logged in"}))
        with mock.patch.object(preflight.subprocess, "run", return_value=done):
            with self.assertRaisesRegex(RuntimeError, "not logged in"):
                preflight.cli_config()

    def test_missing_config_names_the_fix(self):
        done = mock.Mock(stdout="Config file .xsolla.json not found in current or home directory")
        with mock.patch.object(preflight.subprocess, "run", return_value=done):
            with self.assertRaisesRegex(RuntimeError, "xsolla config init"):
                preflight.cli_config()

    def test_cli_output_is_read_as_strict_utf8(self):
        done = mock.Mock(stdout=json.dumps({"ok": True, "data": CONFIG}))
        with mock.patch.object(preflight.subprocess, "run", return_value=done) as run:
            preflight.cli_config()
        self.assertEqual(run.call_args.kwargs["encoding"], "utf-8")
        self.assertNotIn("errors", run.call_args.kwargs)

    def test_missing_stdout_is_a_runtime_error(self):
        done = mock.Mock(stdout=None)
        with mock.patch.object(preflight.subprocess, "run", return_value=done):
            with self.assertRaisesRegex(RuntimeError, "xsolla config init"):
                preflight.cli_config()


class MainTest(unittest.TestCase):
    def run_main(self, *argv: str) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.object(preflight, "cli_config", return_value=CONFIG), \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = preflight.main(["--merchant-id", "11", "--project-id", "22", *argv])
        return code, stdout.getvalue(), stderr.getvalue()

    def test_ids_are_required(self):
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            preflight.main([])

    def test_refusal_exits_one_on_stderr(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.object(preflight, "cli_config", return_value={**CONFIG, "project_id": 99}), \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = preflight.main(["--merchant-id", "11", "--project-id", "22"])
        self.assertEqual((code, stdout.getvalue()), (1, ""))
        self.assertIn("does not match the target", stderr.getvalue())

    def test_pass_prints_the_project(self):
        code, stdout, _ = self.run_main()
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout), {"ok": True, "merchant_id": 11, "project_id": 22})


if __name__ == "__main__":
    unittest.main()
