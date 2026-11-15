"""Every script starts under `python3 -I`, which leaves the script's own folder off sys.path."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
COMMANDS = ("apply_pages.py", "backup.py", "cli_gate.py", "plan_checks.py", "preflight_report.py",
            "render_plan.py", "verify_pages.py")


class IsolatedModeTest(unittest.TestCase):
    def test_scripts_start_under_python_isolated_mode(self) -> None:
        with tempfile.TemporaryDirectory() as cwd:
            for name in COMMANDS:
                with self.subTest(script=name):
                    result = subprocess.run(
                        [sys.executable, "-I", str(SCRIPTS / name), "--help"],
                        cwd=cwd, capture_output=True, text=True, check=False,
                    )
                    self.assertEqual(0, result.returncode, result.stderr)
                    self.assertNotIn("ModuleNotFoundError", result.stderr)

    def test_scripts_use_the_standard_library_and_make_no_http_calls(self) -> None:
        for path in SCRIPTS.glob("*.py"):
            with self.subTest(script=path.name):
                text = path.read_text(encoding="utf-8")
                for forbidden in ("urllib.request", "http.client", "import requests", "urlopen", "socket"):
                    self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
