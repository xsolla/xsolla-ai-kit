"""AC-33..AC-37: live-run artifact contract, validator, size and mirror equality.

AC-33..35 are live-run ACs. Here only the report contract file is checked.
Note: AC-36 `unittest discover` itself is run by the orchestrator, not recursively from here.
"""
from __future__ import annotations

import filecmp
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

import qs_base
from qs_base import IsolatedCase, read_text

SCHEMA = qs_base.FIXTURES / "live-case-report.schema.md"
FIELDS = ("case", "result", "tool_calls", "readback", "transcript_path")


def _files(root: Path):
    out = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if "__pycache__" in rel.parts or path.suffix == ".pyc" or not path.is_file():
            continue
        out[str(rel)] = path
    return out


class LiveReportContractTests(IsolatedCase):
    def test_ac_33_schema_file_lists_the_report_fields(self) -> None:
        self.assertTrue(SCHEMA.is_file())
        text = read_text(SCHEMA)
        for name in FIELDS:
            with self.subTest(field=name):
                self.assertRegex(text, re.compile(rf"\b{name}\b"))
        self.assertIn("PASS", text)
        self.assertIn("FAIL", text)

    def test_ac_34_schema_requires_transcript_confirmation_and_readback(self) -> None:
        text = read_text(SCHEMA)
        self.assertRegex(text, re.compile(r"missing transcript[^.\n]{0,60}FAIL", re.I))
        self.assertRegex(text, re.compile(r"confirmation", re.I))
        self.assertRegex(text, re.compile(r"read.?back", re.I))

    def test_ac_35_schema_says_fail_blocks_sign_off(self) -> None:
        text = read_text(SCHEMA)
        self.assertRegex(text, re.compile(r"FAIL[^.\n]{0,80}blocks? sign-?off", re.I))


class RepoChecksTests(IsolatedCase):
    def test_ac_36_validator_exits_zero(self) -> None:
        env = dict(qs_base.REAL_ENV)  # git (used by the validator) needs the real HOME and config
        proc = subprocess.run([sys.executable, "-I", ".github/scripts/validate_skills.py"], cwd=qs_base.REPO,
                              env=env, capture_output=True, text=True, timeout=120)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_ac_36_agents_md_is_below_32768_bytes(self) -> None:
        self.assertLess((qs_base.REPO / "AGENTS.md").stat().st_size, 32768)

    def test_ac_37_mirror_equals_skill_dir(self) -> None:
        source = _files(qs_base.SKILL)
        mirror = _files(qs_base.REPO / ".cursor" / "skills" / "quest-setup")
        self.assertEqual(sorted(source), sorted(mirror))
        for rel, path in source.items():
            with self.subTest(file=rel):
                self.assertTrue(filecmp.cmp(path, mirror[rel], shallow=False))

    def test_ac_37_new_files_are_in_the_mirror(self) -> None:
        mirror = _files(qs_base.REPO / ".cursor" / "skills" / "quest-setup")
        for rel in ("scripts/qp_docs.py", "scripts/qp_preflight.py", "references/block-versions.md"):
            with self.subTest(file=rel):
                self.assertIn(rel, mirror)


if __name__ == "__main__":
    unittest.main()
