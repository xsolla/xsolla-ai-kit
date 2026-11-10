"""Saved appearance readback checks for the synthetic agent scenarios."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "appearance"

import sys

sys.path.insert(0, str(SCRIPTS))
import quests_block_summary as qbs  # noqa: E402


class AppearanceFixturesTest(unittest.TestCase):
    def test_every_scenario_includes_saved_readback(self) -> None:
        paths = sorted(FIXTURES.glob("*.json"))
        self.assertEqual(len(paths), 5)
        for path in paths:
            with self.subTest(case=path.stem):
                fixture = json.loads(path.read_text(encoding="utf-8"))
                self.assertTrue(fixture["fixture_only"])
                self.assertTrue(fixture["whole_page_result"])
                block = fixture["saved_after"]
                structure = {
                    "pages": [{
                        "_id": "fixture-page",
                        "name": fixture["site_evidence"]["page"],
                        "blocks": [block],
                    }]
                }
                [summary] = qbs.summarize(structure, {}, None)
                self.assertEqual(summary["appearance"], fixture["expected_readback"])



if __name__ == "__main__":
    unittest.main()
