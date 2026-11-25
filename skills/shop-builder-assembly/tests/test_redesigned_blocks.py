from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import redesigned_blocks  # noqa: E402
import render_plan  # noqa: E402
from validate_shop_brief import VERIFIED_BLOCK_MODULES  # noqa: E402

PREFIX = "_site-builder-classic_"


class RedesignedBlockNamesTests(unittest.TestCase):
    def test_each_redesigned_block_stands_for_one_native_module(self) -> None:
        expected = {
            "header": "header",
            "lead": "lead",
            "lead-gs": "leadGameSales",
            "store": "newStore",
            "promocode": "promocodes",
            "faq": "faq",
            "footer-v3": "footer",
            "game-packs": "packs",
            "description": "description",
            "card-grid": "bento-grid",
            "gallery": "gallery",
            "system-requirements": "requirements",
            "news": "news",
            "reward-chains": "rewards",
            "sidebar": "sidebar",
            "sb-offer-chain": "sb-offer-chain",
            "sb-daily-reward": "sb-daily-reward",
            "offerwall": "offerwall-block",
        }
        self.assertEqual(expected, redesigned_blocks.NATIVE_MODULES)
        for name, native in expected.items():
            with self.subTest(name=name):
                self.assertEqual(native, redesigned_blocks.logical_name(PREFIX + name))
        natives = list(expected.values())
        self.assertEqual(len(natives), len(set(natives)), "two blocks share a native module")

    def test_mapped_names_are_modules_the_brief_knows(self) -> None:
        # The brief and the presets keep native names, so a redesigned block must map to
        # a name they can use. These four come with a site template and no preset adds
        # them.
        template_only = {"lead", "sidebar", "sb-daily-reward", "offerwall-block"}
        self.assertEqual(
            set(),
            set(redesigned_blocks.NATIVE_MODULES.values())
            - VERIFIED_BLOCK_MODULES
            - template_only,
        )

    def test_other_names_stay_as_they_are(self) -> None:
        for name in (
            "header",
            "newStore",
            "federated",
            "sb-offer-chain",
            "social-quests",
            "_quest-platform_quests-block",
            PREFIX + "not-a-known-block",
            PREFIX,
            "",
            None,
            7,
        ):
            with self.subTest(name=name):
                self.assertEqual(name, redesigned_blocks.logical_name(name))

    def test_the_render_stop_uses_the_same_prefix(self) -> None:
        self.assertEqual(PREFIX, redesigned_blocks.PREFIX)
        self.assertIs(redesigned_blocks.PREFIX, render_plan.REDESIGNED_BLOCK_PREFIX)


if __name__ == "__main__":
    unittest.main()
