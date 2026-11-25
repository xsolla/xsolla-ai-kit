from __future__ import annotations

import copy
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import redesigned_blocks  # noqa: E402
import render_plan  # noqa: E402
from validate_shop_brief import VERIFIED_BLOCK_MODULES  # noqa: E402

PREFIX = "_site-builder-classic_"
EXAMPLE_BRIEF = ROOT / "examples" / "mobile-single-page.json"
# A masked export of a real site with `features.redesign` on: the page `add-page` makes
# by default, a page of the `store` type, and a page with a store that `create-block`
# added. tests/mask_site_export.py makes it.
FIXTURE = json.loads(
    (ROOT / "tests" / "fixtures" / "redesigned-site.json").read_text(encoding="utf-8")
)


def redesigned_site(brief: dict, paths: tuple[str, ...] = ("/",)) -> dict:
    """The fixture's site with only the pages at ``paths``, as the brief's project."""
    site = copy.deepcopy(FIXTURE["structure"])
    site["pages"] = [page for page in site["pages"] if render_plan.page_path(page) in paths]
    site["blocks"] = [block["_id"] for page in site["pages"] for block in page["blocks"]]
    site["domain"] = brief["site"]["slug"]
    site["merchantId"] = brief["project"]["merchant_id"]
    site["projectId"] = brief["project"]["project_id"]
    return site


def redesigned_names(page: dict) -> list[str]:
    return [
        module
        for module in (render_plan.effective_module(block) for block in page["blocks"])
        if isinstance(module, str) and module.startswith(PREFIX)
    ]


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


class RedesignedSiteFixtureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.brief = json.loads(EXAMPLE_BRIEF.read_text(encoding="utf-8"))
        self.pages = {
            render_plan.page_path(page): page for page in FIXTURE["structure"]["pages"]
        }

    def test_the_fixture_holds_nothing_from_the_real_site(self) -> None:
        dumped = json.dumps(FIXTURE)
        links = set(re.findall(r"https?://[^\s\"\\]+", dumped))
        self.assertEqual(
            set(), {link for link in links if not link.startswith("https://example.invalid/")}
        )
        self.assertNotIn("@", dumped)
        site = FIXTURE["structure"]
        self.assertEqual(
            ("redesigned-site", "merchant-id", "project-id"),
            (site["domain"], site["merchantId"], site["projectId"]),
        )

    def test_the_site_is_a_redesign_site_with_no_layout(self) -> None:
        site = FIXTURE["structure"]
        self.assertIs(True, site["features"]["redesign"])
        self.assertEqual([], site["layouts"])

    def test_the_default_page_is_seeded_as_add_page_does_today(self) -> None:
        self.assertEqual(
            [
                "header",
                "lead-gs",
                "description",
                "game-packs",
                "game-packs",
                "card-grid",
                "card-grid",
                "card-grid",
                "gallery",
                "game-packs",
                "system-requirements",
                "faq",
                "footer-v3",
            ],
            [name[len(PREFIX) :] for name in redesigned_names(self.pages["/"])],
        )
        self.assertEqual(13, len(self.pages["/"]["blocks"]))

    def test_every_redesigned_block_in_the_fixture_is_in_the_name_table(self) -> None:
        for path, page in self.pages.items():
            for name in redesigned_names(page):
                with self.subTest(page=path, name=name):
                    self.assertNotEqual(name, redesigned_blocks.logical_name(name))

    def test_every_text_reference_finds_its_text(self) -> None:
        for path, page in self.pages.items():
            texts = FIXTURE["localization"]["pages"][page["_id"]]["texts"]
            for block in page["blocks"]:
                resources = block.get("values", {}).get("resources") or {}
                references = [
                    value["texts"]["id"]
                    for value in resources.get("localizedValues", {}).values()
                ] + [
                    action["value"]["text"]["id"]
                    for action in resources.get("components.button-action", {}).values()
                    if isinstance(action["value"].get("text"), dict)
                ]
                for text_id in references:
                    with self.subTest(page=path, block=block["_id"], text=text_id):
                        self.assertIn(text_id, texts)

    def test_the_render_still_stops_on_the_default_page(self) -> None:
        site = redesigned_site(self.brief)
        plan = render_plan.build_plan(self.brief, site)
        with self.assertRaisesRegex(ValueError, "redesigned blocks .*Nothing was written"):
            render_plan.require_header_source(plan["pages"], site)


if __name__ == "__main__":
    unittest.main()
