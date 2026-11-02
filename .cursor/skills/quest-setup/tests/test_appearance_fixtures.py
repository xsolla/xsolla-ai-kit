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
                self.assertEqual(fixture["saved_before"]["_id"], fixture["saved_after"]["_id"])
                self.assertIn("saved_after", fixture)
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

                before = fixture["saved_before"]["values"]["internalBlockValues"]
                after = fixture["saved_after"]["values"]["internalBlockValues"]
                for key in ("backpackAction", "questIds", "layout", "overrides", "resources", "translations"):
                    if key in before:
                        self.assertEqual(after.get(key), before[key])
                before_themes = before.get("themeAppearance") or {}
                after_themes = after.get("themeAppearance") or {}
                for theme, saved in before_themes.items():
                    self.assertEqual(after_themes.get(theme), saved)
                self.assertEqual(
                    fixture["saved_after"]["values"]["version"],
                    fixture["saved_before"]["values"]["version"],
                )

    def test_rejected_and_noop_fixtures_are_unchanged(self) -> None:
        for name in ("native-dark-site", "explicit-site-builder", "unsupported-old-version"):
            with self.subTest(case=name):
                fixture = json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
                self.assertEqual(fixture["saved_after"], fixture["saved_before"])

    def test_pages_recommendation_preserves_external_action(self) -> None:
        fixture = json.loads((FIXTURES / "pages-composition.json").read_text(encoding="utf-8"))
        self.assertEqual(fixture["saved_after"]["values"]["internalBlockValues"]["themeId"], "xsolla-pages")
        self.assertEqual(fixture["saved_after"]["values"]["internalBlockValues"]["backpackAction"], "external")

    def test_mixed_custom_inherits_unverified_font_and_preserves_overlay_action(self) -> None:
        fixture = json.loads((FIXTURES / "mixed-custom.json").read_text(encoding="utf-8"))
        after = fixture["saved_after"]["values"]["internalBlockValues"]
        self.assertEqual(after["backpackAction"], "overlay")
        self.assertEqual(after["themeAppearance"]["custom"]["typography"]["headingFont"], "host-heading")
        self.assertNotIn("actionText", after["themeAppearance"]["custom"].get("palette", {}))

    def test_mixed_custom_recommendation_converts_measured_units(self) -> None:
        fixture = json.loads((FIXTURES / "mixed-custom.json").read_text(encoding="utf-8"))
        evidence = fixture["site_evidence"]
        heading = next(
            item for item in evidence["neighbors"]
            if item["semantic_role"] == "section-heading"
        )
        content = next(
            item for item in evidence["neighbors"]
            if item["semantic_role"] == "regular-card-description"
        )
        values = fixture["recommendation"]["operation"]["values"]

        measured_line_height = heading["line_height_px"] / heading["size_px"]
        self.assertEqual(
            values["themeAppearance.custom.typography.headingLineHeight"],
            measured_line_height,
        )

        measured_border_box = content["content_width_px"] + 2 * content["gutter_px"]
        self.assertEqual(
            values["themeAppearance.custom.geometry.maxWidth"],
            measured_border_box,
        )
        self.assertEqual(
            values["themeAppearance.custom.geometry.gutter"],
            content["gutter_px"],
        )


if __name__ == "__main__":
    unittest.main()
