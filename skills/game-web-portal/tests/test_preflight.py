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

CONFIG = {"merchant_id": 11, "project_id": 22}
ENTRY = {"merchant_id": 11, "project_id": 22}


TMP = tempfile.TemporaryDirectory()


def tearDownModule() -> None:
    TMP.cleanup()


def allowlist(*projects: dict, version: int = 1) -> Path:
    fh = tempfile.NamedTemporaryFile(
        "w", suffix=".json", dir=TMP.name, delete=False, encoding="utf-8"
    )
    with fh:
        json.dump({"version": version, "projects": list(projects)}, fh)
    return Path(fh.name)


class CheckProjectTest(unittest.TestCase):
    def test_listed_project_passes(self):
        entry = preflight.check_project(11, 22, allowlist(ENTRY), config=CONFIG)
        self.assertEqual(entry, ENTRY)

    def test_unlisted_project_stops(self):
        other = {**ENTRY, "project_id": 99}
        with self.assertRaisesRegex(RuntimeError, "not on the test-project list"):
            preflight.check_project(11, 22, allowlist(other), config=CONFIG)

    def test_cli_sandbox_mode_stops(self):
        with self.assertRaisesRegex(RuntimeError, "sandbox mode is on"):
            preflight.check_project(11, 22, allowlist(ENTRY), config={**CONFIG, "sandbox": True})

    def test_cli_sandbox_off_or_missing_passes(self):
        for config in (CONFIG, {**CONFIG, "sandbox": False}):
            with self.subTest(config=config):
                entry = preflight.check_project(11, 22, allowlist(ENTRY), config=config)
                self.assertEqual(entry, ENTRY)

    def test_cli_pointing_at_another_project_stops(self):
        with self.assertRaisesRegex(RuntimeError, "does not match the target"):
            preflight.check_project(11, 22, allowlist(ENTRY),
                                    config={**CONFIG, "project_id": 99})

    def test_unreadable_allowlist_stops(self):
        with self.assertRaisesRegex(RuntimeError, "cannot read the test-project list"):
            preflight.check_project(11, 22, Path("/nonexistent/allowlist.json"), config=CONFIG)

    def test_ids_alone_are_enough(self):
        entry = {**ENTRY, "note": "dedicated test project, confirmed in chat"}
        self.assertEqual(
            preflight.check_project(11, 22, allowlist(entry), config=CONFIG), entry
        )

    def test_malformed_allowlist_stops(self):
        with self.assertRaisesRegex(RuntimeError, "version 1"):
            preflight.check_project(11, 22, allowlist(ENTRY, version=2), config=CONFIG)
        with self.assertRaisesRegex(RuntimeError, "integer IDs"):
            preflight.check_project(11, 22, allowlist({**ENTRY, "project_id": "22"}),
                                    config=CONFIG)


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

    def test_allowlist_is_required(self):
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            self.run_main()

    def test_refusal_exits_one_on_stderr(self):
        code, stdout, stderr = self.run_main("--approved-test-projects", str(allowlist()))
        self.assertEqual((code, stdout), (1, ""))
        self.assertIn("not on the test-project list", stderr)

    def test_pass_prints_the_list_entry(self):
        code, stdout, _ = self.run_main("--approved-test-projects", str(allowlist(ENTRY)))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout)["test_project"], ENTRY)


if __name__ == "__main__":
    unittest.main()
