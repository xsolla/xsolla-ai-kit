"""Tests for scripts/env_credentials.py. Temp folders only; the key never reaches the output."""
from __future__ import annotations

import io
import os
import stat
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import env_credentials  # noqa: E402

KEY = "SENTINEL-KEY-31f0aa"


class EnvCredentialsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.folder = Path(self._tmp.name)
        self.env = self.folder / ".env"

    def run_main(self, argv, stdin=""):
        out = io.StringIO()
        with redirect_stdout(out), mock.patch.object(sys, "stdin", io.StringIO(stdin)):
            code = env_credentials.main(argv, folder=self.folder)
        return code, out.getvalue()

    def test_check_shows_ids_and_hides_the_key(self) -> None:
        self.env.write_text(f'export XSOLLA_MERCHANT_ID="7"\nXSOLLA_PROJECT_ID=42\nXSOLLA_PROJECT_API_KEY={KEY}\n')
        code, out = self.run_main(["check"])
        self.assertEqual(code, 0)
        self.assertIn("XSOLLA_MERCHANT_ID: 7", out)
        self.assertIn("XSOLLA_PROJECT_ID: 42", out)
        self.assertIn("XSOLLA_PROJECT_API_KEY: set", out)
        self.assertNotIn(KEY, out)

    def test_check_reports_missing(self) -> None:
        code, out = self.run_main(["check"])
        self.assertEqual(code, 1)
        self.assertEqual(out.count("missing"), 3)

    def test_write_updates_in_place_keeps_other_lines_and_sets_mode(self) -> None:
        self.env.write_text("OTHER=1\nexport XSOLLA_PROJECT_ID=1\n# XSOLLA_MERCHANT_ID=commented\n"
                            "XSOLLA_PROJECT_ID=2\nTAIL=x\n")
        code, out = self.run_main(["write", "--merchant-id", "7", "--project-id", "42", "--key-stdin"], KEY + "\n")
        self.assertEqual(code, 0)
        self.assertNotIn(KEY, out)
        lines = self.env.read_text().splitlines()
        self.assertIn("OTHER=1", lines)
        self.assertIn("TAIL=x", lines)
        self.assertIn("# XSOLLA_MERCHANT_ID=commented", lines)
        self.assertIn("export XSOLLA_PROJECT_ID=42", lines)
        self.assertEqual(sum(l.endswith("XSOLLA_PROJECT_ID=42") for l in lines), 1)
        self.assertNotIn("XSOLLA_PROJECT_ID=2", lines)
        self.assertIn("XSOLLA_MERCHANT_ID=7", lines)
        self.assertIn(f"XSOLLA_PROJECT_API_KEY={KEY}", lines)
        self.assertEqual(stat.S_IMODE(os.stat(self.env).st_mode), 0o600)
        self.assertIn(".env", (self.folder / ".gitignore").read_text().splitlines())

    def test_write_without_key_keeps_the_existing_key(self) -> None:
        self.env.write_text(f"XSOLLA_PROJECT_API_KEY={KEY}\n")
        code, _ = self.run_main(["write", "--merchant-id", "7", "--project-id", "42"])
        self.assertEqual(code, 0)
        self.assertIn(f"XSOLLA_PROJECT_API_KEY={KEY}", self.env.read_text())

    def test_key_from_json_and_prompt(self) -> None:
        code, _ = self.run_main(["write", "--merchant-id", "7", "--project-id", "42", "--key-stdin"],
                                '{"api_key": "%s", "name": "x"}' % KEY)
        self.assertEqual(code, 0)
        self.assertIn(f"XSOLLA_PROJECT_API_KEY={KEY}", self.env.read_text())
        with mock.patch("getpass.getpass", return_value="OTHER-KEY"):
            code, out = self.run_main(["write", "--merchant-id", "7", "--project-id", "42", "--key-prompt"])
        self.assertEqual(code, 0)
        self.assertNotIn("OTHER-KEY", out)
        self.assertIn("XSOLLA_PROJECT_API_KEY=OTHER-KEY", self.env.read_text())

    def test_invalid_input_writes_nothing(self) -> None:
        for argv, stdin in ((["write", "--merchant-id", "abc", "--project-id", "42"], ""),
                            (["write", "--merchant-id", "7", "--project-id", "42", "--key-stdin"], "   \n"),
                            (["write", "--merchant-id", "7", "--project-id", "42", "--key-stdin"], "two words\n")):
            with self.subTest(argv=argv, stdin=stdin):
                code, _ = self.run_main(argv, stdin)
                self.assertEqual(code, 2)
                self.assertFalse(self.env.exists())
                self.assertFalse((self.folder / ".gitignore").exists())


if __name__ == "__main__":
    unittest.main()
