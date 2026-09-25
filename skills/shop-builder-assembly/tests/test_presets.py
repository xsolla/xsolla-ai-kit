from __future__ import annotations

import importlib.util
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def load_render_plan():
    path = ROOT / "scripts" / "render_plan.py"
    spec = importlib.util.spec_from_file_location("render_plan_for_presets", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


render_plan = load_render_plan()


class PresetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.brief = json.loads(
            (ROOT / "examples" / "mobile-single-page.json").read_text(encoding="utf-8")
        )

    def test_all_presets_require_confirmation_and_forbid_publication(self) -> None:
        for preset in render_plan.PRESET_PAGES:
            with self.subTest(preset=preset):
                self.brief["site"]["preset"] = preset
                plan = render_plan.build_plan(self.brief)
                self.assertIs(plan["requires_confirmation"], True)
                self.assertEqual("forbidden", plan["publication"])
                self.assertRegex(plan["confirmation_id"], r"^sha256:[0-9a-f]{12}$")

    def test_page_paths_are_unique_and_bounded_by_header_footer(self) -> None:
        for preset, pages in render_plan.PRESET_PAGES.items():
            with self.subTest(preset=preset):
                paths = [page["path"] for page in pages]
                self.assertEqual(len(paths), len(set(paths)))
                for page in pages:
                    self.assertEqual("header", page["blocks"][0])
                    self.assertEqual("footer", page["blocks"][-1])

    def test_every_preset_module_is_in_the_catalog(self) -> None:
        catalog = (ROOT / "references" / "block-catalog.md").read_text(encoding="utf-8")
        official_table = catalog.split("## Official inventory mapping", 1)[1].split(
            "## Current palette", 1
        )[0]
        module_cells = re.findall(
            r"^\| [^|]+ \| ([^|]+) \|", official_table, flags=re.MULTILINE
        )
        documented = {
            module for cell in module_cells for module in re.findall(r"`([^`]+)`", cell)
        }
        used = {
            module
            for pages in render_plan.PRESET_PAGES.values()
            for page in pages
            for module in page["blocks"]
        }
        self.assertEqual(set(), used - documented)

    def test_catalog_covers_every_official_documented_block(self) -> None:
        expected = {
            "Header",
            "Sidebar",
            "Lead — Single game page",
            "Lead — Web Shop",
            "Call-to-action",
            "Fast Login",
            "Gallery",
            "News",
            "Cards",
            "Promo slider",
            "Description",
            "Promo codes",
            "Game editions",
            "Store",
            "Reward system",
            "Offer chain",
            "Social media widgets",
            "FAQs",
            "Custom code",
            "Cart settings",
            "System requirements",
            "Subscriptions",
            "Social quests",
            "Footer",
        }
        catalog = (ROOT / "references" / "block-catalog.md").read_text(encoding="utf-8")
        official_table = catalog.split("## Official inventory mapping", 1)[1].split(
            "## Current palette", 1
        )[0]
        names = set(
            re.findall(r"^\| ([^|]+?) \| [^|]+ \|", official_table, flags=re.MULTILINE)
        )
        names.discard("Official block")
        self.assertEqual(expected, names)

    def test_confirmation_id_changes_with_target(self) -> None:
        first = render_plan.build_plan(self.brief)["confirmation_id"]
        self.brief["site"]["slug"] = "another-shop"
        second = render_plan.build_plan(self.brief)["confirmation_id"]
        self.assertNotEqual(first, second)

    def test_confirmation_covers_write_affecting_inputs(self) -> None:
        first = render_plan.build_plan(self.brief)["confirmation_id"]
        self.brief["brand"]["logo"] = "https://cdn.example/logo.png"
        second = render_plan.build_plan(self.brief)["confirmation_id"]
        self.assertNotEqual(first, second)
        self.brief["catalog"]["featured_skus"].append("founder-pack")
        third = render_plan.build_plan(self.brief)["confirmation_id"]
        self.assertNotEqual(second, third)

    def test_empty_catalog_omits_store_block(self) -> None:
        self.brief["catalog"]["groups"] = []
        plan = render_plan.build_plan(self.brief)
        self.assertNotIn("newStore", plan["pages"][0]["blocks"])
        self.assertIn("newStore", {item["module"] for item in plan["omissions"]})

    def test_catalog_sections_receive_deterministic_layouts(self) -> None:
        self.brief["catalog"]["groups"] = [
            {"external_id": "featured", "type": "bundle", "placement": "featured"},
            {"external_id": "main", "type": "virtual_good", "placement": "primary"},
            {"external_id": "more", "type": "virtual_good", "placement": "secondary"},
        ]
        plan = render_plan.build_plan(self.brief)
        self.assertEqual(
            ["featured", "vertical", "horizontal"],
            [section["layout"] for section in plan["catalog_sections"]],
        )
        self.assertIn("catalog_links", plan["implemented_phases"])
        self.assertNotIn("catalog_links", plan["unsupported_phases"])

    def test_existing_block_without_replacement_data_is_preserved(self) -> None:
        self.brief["content"].pop("faq", None)
        structure = {
            "_id": "landing",
            "pages": [
                {
                    "_id": "home",
                    "name": "Home",
                    "path": "/",
                    "blocks": [
                        {"_id": "header", "module": "header"},
                        {"_id": "hero", "module": "leadGameSales"},
                        {"_id": "store", "module": "newStore"},
                        {"_id": "existing-faq", "module": "faq"},
                        {"_id": "footer", "module": "footer"},
                    ],
                }
            ],
        }
        plan = render_plan.build_plan(self.brief, structure)
        self.assertEqual(
            ["header", "leadGameSales", "newStore", "faq", "footer"],
            plan["pages"][0]["blocks"],
        )
        self.assertEqual([], plan["pages"][0]["removals"])
        self.assertEqual(
            [
                {
                    "block_id": "existing-faq",
                    "module": "faq",
                    "reason": "no approved FAQ supplied",
                }
            ],
            plan["pages"][0]["preserved_blocks"],
        )
        faq = next(item for item in plan["omissions"] if item["module"] == "faq")
        self.assertEqual("preserve-existing", faq["action"])
        self.assertEqual("existing-faq", faq["block_id"])

    def test_page_overrides_replace_preset_pages(self) -> None:
        self.brief["content"]["page_overrides"] = [
            {
                "name": "Shop",
                "path": "/shop",
                "blocks": ["header", "newStore", "footer"],
            }
        ]
        plan = render_plan.build_plan(self.brief)
        self.assertEqual(["/shop"], [page["path"] for page in plan["pages"]])

    def test_target_state_binds_exact_block_removals(self) -> None:
        structure = {
            "ok": True,
            "data": {
                "_id": "landing",
                "pages": [
                    {
                        "_id": "home",
                        "name": "Home",
                        "path": "/",
                        "blocks": [
                            {"_id": "keep", "module": "header"},
                            {"_id": "remove", "module": "gallery"},
                        ],
                    }
                ],
            },
        }
        plan = render_plan.build_plan(self.brief, structure)
        self.assertEqual(
            [
                {
                    "block_id": "remove",
                    "module": "gallery",
                    "reason": "not in confirmed page plan",
                }
            ],
            plan["pages"][0]["removals"],
        )
        self.assertEqual("reconcile", plan["current_state"]["application_mode"])


if __name__ == "__main__":
    unittest.main()
