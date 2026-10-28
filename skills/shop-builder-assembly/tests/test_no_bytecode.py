"""Entry scripts must not leave `__pycache__` in the skill folder.

The installed plugin runs the scripts straight from its source folder, and a
stray `__pycache__` there breaks skill validation after the next install.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
ENTRY_SCRIPTS = (
    "apply_plan.py",
    "backup_shop.py",
    "preflight.py",
    "render_plan.py",
    "validate_shop_brief.py",
    "verify_structure.py",
)


class NoBytecodeTest(unittest.TestCase):
    def test_entry_scripts_write_no_pycache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "scripts"
            shutil.copytree(SCRIPTS, copy, ignore=shutil.ignore_patterns("__pycache__"))
            env = {k: v for k, v in os.environ.items() if k != "PYTHONDONTWRITEBYTECODE"}
            for name in ENTRY_SCRIPTS:
                with self.subTest(script=name):
                    result = subprocess.run(
                        [sys.executable, str(copy / name), "--help"],
                        cwd=tmp,
                        env=env,
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertFalse((copy / "__pycache__").exists(), name)


if __name__ == "__main__":
    unittest.main()
