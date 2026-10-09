"""CI entry point. validate.yml discovers skills/*/tests and runs unittest."""
import subprocess
import unittest
from pathlib import Path


class SmokeTest(unittest.TestCase):
    def test_smoke_script(self):
        root = Path(__file__).resolve().parents[1]
        completed = subprocess.run(
            ["bash", str(root / "scripts" / "smoke-test.sh")],
            cwd=root,
            check=False,
        )
        self.assertEqual(completed.returncode, 0)
