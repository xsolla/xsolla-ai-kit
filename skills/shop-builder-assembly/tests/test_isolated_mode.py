from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"

# Scripts that import a sibling module. Agents often run downloaded scripts with
# `python3 -I`, which leaves the script's own folder off sys.path.
SCRIPTS_WITH_SIBLING_IMPORTS = (
    "apply_plan.py",
    "backup_shop.py",
    "patch_backgrounds.py",
    "preflight.py",
    "render_plan.py",
    "verify_structure.py",
)


class IsolatedModeTest(unittest.TestCase):
    def test_scripts_start_under_python_isolated_mode(self) -> None:
        with tempfile.TemporaryDirectory() as cwd:
            for name in SCRIPTS_WITH_SIBLING_IMPORTS:
                with self.subTest(script=name):
                    result = subprocess.run(
                        [sys.executable, "-I", str(SCRIPTS / name), "--help"],
                        cwd=cwd,
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertNotIn("ModuleNotFoundError", result.stderr)


if __name__ == "__main__":
    unittest.main()
