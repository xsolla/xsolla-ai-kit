"""Embedded Python reads and writes the CLI's UTF-8, not the Windows ANSI code page."""
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
UNICODE_TEXT = "<h1>Космос — Café</h1>"


class Utf8Test(unittest.TestCase):
    def test_every_embedded_python_runs_in_utf8_mode(self):
        for script in sorted(SCRIPTS.glob("*.sh")):
            lines = script.read_text(encoding="utf-8").splitlines()
            for number, line in enumerate(lines, 1):
                if re.search(r"(^|[\s|;&(])python3 (-|<<)", line):
                    with self.subTest(f"{script.name}:{number}"):
                        self.assertIn("python3 -X utf8 ", line)

    def test_cli_output_is_read_as_strict_utf8(self):
        for script in sorted(SCRIPTS.glob("*.sh")):
            text = script.read_text(encoding="utf-8")
            for match in re.finditer(r"subprocess\.run\((?:[^()]|\([^()]*\))*\)", text):
                call = match.group(0)
                if "text=True" in call:
                    with self.subTest(f"{script.name}: {call[:60]}"):
                        self.assertRegex(call, r"encoding=['\"]utf-8['\"]")
                        self.assertNotIn("errors=", call)

    def test_extract_keeps_cyrillic_and_accented_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            backup = Path(tmp) / "l10n" / "backup" / "fixture"
            backup.mkdir(parents=True)
            for fixture in (SCRIPTS / "fixtures" / "baseline").glob("*.json"):
                shutil.copy(fixture, backup)
            localization = json.loads((backup / "localization.json").read_text(encoding="utf-8"))
            texts = localization["data"]["pages"]["page1"]["texts"]
            texts["L:t1"]["translations"]["en-US"] = UNICODE_TEXT
            (backup / "localization.json").write_text(
                json.dumps(localization, ensure_ascii=False), encoding="utf-8"
            )
            subprocess.run(
                ["bash", str(SCRIPTS / "extract.sh"), "en-US", "de-DE", "l10n/backup/fixture"],
                cwd=tmp,
                check=True,
                capture_output=True,
            )
            out = Path(tmp) / "l10n" / "work" / "de-DE" / "translatable.json"
            units = json.loads(out.read_text(encoding="utf-8"))["units"]
            self.assertEqual(
                UNICODE_TEXT, next(u for u in units if u.get("lid") == "L:t1")["source"]
            )


if __name__ == "__main__":
    unittest.main()
