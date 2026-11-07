"""The write path against the stand-in CLI's proposed commands, and the after-write check."""

from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import harness  # noqa: E402
from harness import common, stand_in_cli  # noqa: E402

import verify_pages  # noqa: E402


def page(structure: dict, route: str) -> dict:
    return common.find_page(structure, route)


def block(page_: dict, package: str) -> dict:
    return next(b for b in page_["blocks"] if common.block_identity(b)[0] == package)


class ApplyAndVerifyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.cli = stand_in_cli.StandInCli(capabilities="proposed")
        self.manifest = common.load_manifest()
        self.config = common.load_config(harness.CONFIG)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_batch(self, batch: dict | None = None, name: str = "backup") -> tuple[dict, dict, Path]:
        plan, errors, plan_path, backup_dir = harness.prepare(self.dir, self.cli, batch=batch, name=name)
        self.assertEqual([], errors)
        code, report = harness.apply(self.cli, plan_path, backup_dir)
        self.assertEqual(0, code, report)
        return plan, report, backup_dir

    def test_a_batch_creates_every_page_and_matches_the_manifest(self) -> None:
        plan, report, _ = self.run_batch()
        self.assertEqual("applied", report["status"])
        self.assertEqual(
            {
                "blocks_outside_manifest": 0,
                "theme_or_style_patches": 0,
                "custom_code_items": 0,
                "hand_typed_game_data_fields": 0,
                "pages_matching_manifest": "100%",
            },
            report["verification"]["acceptance"],
        )
        self.assertEqual(
            ["/payment/klarna", "/payment/klarna/:slug", "/payment/toss", "/payment/toss/:slug"],
            report["created_pages"],
        )
        site = self.cli.site
        klarna = page(site, "/payment/klarna")
        self.assertEqual(
            ["@xla-pages/top-navigation", "@xla-pages/hero", "@xla-pages/top-up", "@xla-pages/games",
             "@xla-pages/special-offers", "@xla-pages/faq", "@xla-pages/footer"],
            [common.block_identity(b)[0] for b in klarna["blocks"]],
        )
        self.assertEqual("0.4.1-next.3", common.block_identity(block(klarna, "@xla-pages/hero"))[1])
        self.assertEqual("klarna", common.block_fields(block(klarna, "@xla-pages/top-up"))["providerId"])
        self.assertEqual({"enabled": False, "input": {"bg": "#141d1f"}}, klarna["theme"])
        # Toss has no offers: its page has no special-offers block at all.
        self.assertNotIn("@xla-pages/special-offers",
                         [common.block_identity(b)[0] for b in page(site, "/payment/toss")["blocks"]])
        # The seeded blocks were deleted, not hidden.
        for route in report["created_pages"]:
            self.assertTrue(all(b["module"] == "federated" for b in page(site, route)["blocks"]))
        commands = {call[:2] for call in self.cli.writes()}
        self.assertLessEqual(commands, set(common.WRITE_COMMANDS))
        self.assertFalse(any("publish" in call[1] or "preview" in call[1] for call in self.cli.calls))

    def test_add_page_empty_is_used_when_the_cli_has_it(self) -> None:
        self.cli = stand_in_cli.StandInCli(capabilities="proposed", seed_empty_flag=True)
        self.run_batch()
        add_pages = [call for call in self.cli.writes() if call[1] == "add-page"]
        self.assertTrue(all("--empty" in call for call in add_pages))
        self.assertFalse(any('"op":"remove"' in " ".join(call) for call in self.cli.writes()))

    def test_the_after_write_check_reports_the_exact_difference(self) -> None:
        plan, report, backup_dir = self.run_batch()
        after = copy.deepcopy(self.cli.site)
        klarna = page(after, "/payment/klarna")
        block(klarna, "@xla-pages/hero")["values"]["version"] = "0.2.0"
        del block(klarna, "@xla-pages/top-up")["bindings"]["gamesJson"]
        klarna["blocks"].insert(2, {"_id": "x-store", "module": "newStore", "values": {}})
        block(klarna, "@xla-pages/footer")["hidden"] = True
        combined = page(after, "/payment/toss/:slug")
        hero = block(combined, "@xla-pages/hero")
        del hero["bindings"]["title"]
        hero["values"]["internalBlockValues"]["title"] = "Star Forge"
        combined["blocks"].append({"_id": "x-html", "module": "html", "values": {}})
        result = verify_pages.verify(plan, after, common.load_json(backup_dir / "structure.json", "s"),
                                     self.manifest, self.config)
        pages = {p["route"]: p for p in result["pages"]}
        self.assertEqual([
            "block 3 (newStore) is outside the manifest",
            "@xla-pages/hero: expected version 0.4.1-next.3, got 0.2.0",
            "@xla-pages/top-up field gamesJson: expected binding catalog_top_up.gamesJson, got none",
            "@xla-pages/footer: expected visible, got hidden",
        ], pages["/payment/klarna"]["differences"])
        self.assertIn("block 7 (html) is custom code", pages["/payment/toss/:slug"]["differences"])
        self.assertIn("@xla-pages/hero field title: holds a typed value instead of game_data.title",
                      pages["/payment/toss/:slug"]["differences"])
        self.assertTrue(pages["/payment/toss"]["ok"])
        self.assertEqual({
            "blocks_outside_manifest": 2,
            "theme_or_style_patches": 0,
            "custom_code_items": 1,
            "hand_typed_game_data_fields": 1,
            "pages_matching_manifest": "60%",
        }, result["acceptance"])
        self.assertFalse(result["ok"])

    def test_an_update_keeps_the_page_bindings_identical(self) -> None:
        self.run_batch()
        batch = harness.load_batch()
        batch["providers"][0]["hero_title"] = "Pay later with Klarna"
        batch["providers"][0].pop("offers")
        plan, errors, plan_path, backup_dir = harness.prepare(self.dir, self.cli, batch=batch, name="second")
        self.assertEqual([], errors)
        actions = {p["route"]: p["action"] for p in plan["pages"]}
        self.assertEqual("update", actions["/payment/klarna"])
        self.assertEqual("unchanged", actions["/payment/klarna/:slug"])
        ops = [op for p in plan["pages"] for op in p["ops"]]
        self.assertEqual(
            [("set_block_field", "title"), ("hide_block", None), ("set_page_seo", "title")],
            [(op["op"], op.get("field")) for op in ops],
        )
        before = verify_pages.binding_set(page(self.cli.site, "/payment/klarna"))
        code, report = harness.apply(self.cli, plan_path, backup_dir)
        self.assertEqual(0, code, report)
        self.assertEqual(before, verify_pages.binding_set(page(self.cli.site, "/payment/klarna")))
        self.assertTrue(block(page(self.cli.site, "/payment/klarna"), "@xla-pages/special-offers")["hidden"])

        after = copy.deepcopy(self.cli.site)
        del block(page(after, "/payment/klarna"), "@xla-pages/games")["bindings"]["gamesJson"]
        result = verify_pages.verify(plan, after, common.load_json(backup_dir / "structure.json", "s"),
                                     self.manifest, self.config)
        differences = {p["route"]: p["differences"] for p in result["pages"]}["/payment/klarna"]
        self.assertIn(
            "the page's data bindings changed: removed [('@xla-pages/games', 'gamesJson', "
            "'ugc-d-catalog-games-provider-v2 {\"mode\": \"buy\", \"publisherProjectId\": \"200002\"}', "
            "'gamesJson')], added []",
            differences,
        )

    def test_an_update_never_adds_bindings(self) -> None:
        self.run_batch()
        site = self.cli.site
        klarna = page(site, "/payment/klarna")
        klarna["blocks"] = [b for b in klarna["blocks"] if common.block_identity(b)[0] != "@xla-pages/top-up"]
        plan, errors, _, _ = harness.prepare(self.dir, self.cli, name="missing-top-up")
        self.assertEqual([], errors)
        klarna_plan = next(p for p in plan["pages"] if p["route"] == "/payment/klarna")
        self.assertFalse([op for op in klarna_plan["ops"] if op["op"] in ("add_block", "bind_field")])
        self.assertIn("missing block @xla-pages/top-up@0.0.9", klarna_plan["differences_now"])

    def test_a_field_missing_on_the_reference_block_stops_the_plan(self) -> None:
        reference = page(self.cli.site, "/payment/paysafecard")
        del block(reference, "@xla-pages/hero")["values"]["internalBlockValues"]["partnerName"]
        _, errors, _, _ = harness.prepare(self.dir, self.cli)
        self.assertTrue(any("has no field 'partnerName'" in e for e in errors), errors)

    def test_a_reference_block_without_a_readable_package_stops_the_plan(self) -> None:
        reference = page(self.cli.site, "/payment/paysafecard")
        del block(reference, "@xla-pages/faq")["values"]["package"]
        _, errors, _, _ = harness.prepare(self.dir, self.cli)
        self.assertTrue(any("no readable package" in e for e in errors), errors)

    def test_the_combined_about_game_takes_the_game_page_bindings(self) -> None:
        plan, _, _, _ = harness.prepare(self.dir, self.cli)
        self.assertEqual(
            ["combined about-game-carousel takes the game page's bindings for the same variant; "
             "the manifest lists none for it"],
            plan["notes"],
        )


if __name__ == "__main__":
    unittest.main()
