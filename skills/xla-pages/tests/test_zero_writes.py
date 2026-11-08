"""Every pre-write failure stops the batch with zero writes."""

from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import harness  # noqa: E402
from harness import common, stand_in_cli  # noqa: E402


class ZeroWriteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.cli = stand_in_cli.StandInCli(capabilities="proposed")
        self.plan, errors, self.plan_path, self.backup = harness.prepare(self.dir, self.cli)
        self.assertEqual([], errors)
        self.cli.calls.clear()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def edited(self, change) -> Path:
        plan = copy.deepcopy(self.plan)
        change(plan)
        path = self.dir / "edited-plan.json"
        harness.save_plan(path, plan)
        return path

    def page(self, plan: dict, route: str) -> dict:
        return next(page for page in plan["pages"] if page["route"] == route)

    def assert_refused(self, code: int, report: dict, category: str | None = None) -> None:
        self.assertEqual(1, code)
        self.assertEqual(0, report["writes"])
        self.assertEqual([], self.cli.writes())
        if category:
            self.assertIn(category, [e["category"] for e in report["details"]], report["details"])

    def test_a_block_outside_the_manifest_stops_with_zero_writes(self) -> None:
        def add_outside(plan: dict) -> None:
            self.page(plan, "/payment/klarna")["ops"].append({
                "op": "add_block", "route": "/payment/klarna", "key": "payment-methods",
                "package": "@xla-pages/payment-methods", "version": "0.0.1", "index": 7,
            })
        code, report = harness.apply(self.cli, self.edited(add_outside), self.backup)
        self.assert_refused(code, report, "outside_manifest")
        self.assertIn("@xla-pages/payment-methods is not a block the manifest lists", str(report["details"]))

    def test_a_standard_block_stops_with_zero_writes(self) -> None:
        def add_standard(plan: dict) -> None:
            self.page(plan, "/payment/toss")["ops"].insert(3, {
                "op": "add_block", "route": "/payment/toss", "key": "newStore",
                "package": None, "version": None, "index": 0,
            })
        code, report = harness.apply(self.cli, self.edited(add_standard), self.backup)
        self.assert_refused(code, report, "outside_manifest")

    def test_a_theme_patch_stops_with_zero_writes(self) -> None:
        def theme(plan: dict) -> None:
            self.page(plan, "/payment/klarna")["ops"].append({
                "op": "set_page_look", "route": "/payment/klarna", "key": "theme",
                "value": {"enabled": True, "input": {"bg": "#ff0000"}},
            })
        code, report = harness.apply(self.cli, self.edited(theme), self.backup)
        self.assert_refused(code, report, "style")

    def test_a_site_theme_or_block_style_op_stops_with_zero_writes(self) -> None:
        def style(plan: dict) -> None:
            ops = self.page(plan, "/payment/klarna")["ops"]
            ops.append({"op": "set_site_theme", "route": "/payment/klarna", "value": {"primary": "#ff0000"}})
            ops.append({"op": "set_block_field", "route": "/payment/klarna", "key": "hero",
                        "field": "background", "value": "#ff0000"})
        code, report = harness.apply(self.cli, self.edited(style), self.backup)
        self.assert_refused(code, report, "style")
        self.assertEqual(2, [e["category"] for e in report["details"]].count("style"))

    def test_typed_game_data_stops_with_zero_writes(self) -> None:
        def typed(plan: dict) -> None:
            self.page(plan, "/payment/klarna/:slug")["ops"].append({
                "op": "set_block_field", "route": "/payment/klarna/:slug", "key": "hero",
                "field": "title", "value": "Star Forge",
            })
        code, report = harness.apply(self.cli, self.edited(typed), self.backup)
        self.assert_refused(code, report, "hand_typed")

    def test_a_row_over_the_character_limit_is_refused(self) -> None:
        batch = harness.load_batch()
        batch["providers"][0]["hero_title"] = "T" * 61
        _, errors, _, _ = harness.prepare(self.dir, self.cli, batch=batch, name="long")
        self.assertIn("providers[0].hero_title is 61 characters (max 60)", errors)

        def long_row(plan: dict) -> None:
            plan["rows"][1]["hero_description"] = "D" * 151
        code, report = harness.apply(self.cli, self.edited(long_row), self.backup)
        self.assert_refused(code, report, "row")

    def test_the_current_cli_is_blocked_by_the_gate_with_zero_writes(self) -> None:
        cli = stand_in_cli.StandInCli(capabilities="current")
        code, report = harness.apply(cli, self.plan_path, self.backup)
        self.assertEqual(1, code)
        self.assertEqual("blocked_capability", report["status"])
        self.assertEqual([], cli.writes())
        missing = {item["capability"]: item["missing"] for item in report["details"]}
        # Everything else (connections, bindings, SEO) goes through commands the CLI has today.
        self.assertEqual({
            "add-page-dynamic": ["--provider-id", "--provider-input"],
            "add-block-pinned": ["--package", "--version"],
        }, missing)

    def test_responses_older_than_24_hours_stop_with_zero_writes(self) -> None:
        code, report = harness.apply(self.cli, self.plan_path, self.backup, now="2026-11-08T09:00:00Z")
        self.assertEqual(1, code)
        self.assertIn("GET them again", report["reason"])
        self.assertEqual([], self.cli.writes())

    def test_an_edited_plan_without_a_new_yes_is_refused(self) -> None:
        plan = copy.deepcopy(self.plan)
        self.page(plan, "/payment/klarna")["ops"].pop()
        common.write_json(self.plan_path, plan)
        code, report = harness.apply(self.cli, self.plan_path, self.backup)
        self.assertEqual("the plan file was changed after it was rendered", report["reason"])
        self.assertEqual([], self.cli.writes())

    def test_another_confirmation_id_is_refused(self) -> None:
        code, report = harness.apply(self.cli, self.plan_path, self.backup, confirmation="sha256:000000000000")
        self.assertEqual("the confirmation ID is not the approved plan's", report["reason"])
        self.assertEqual([], self.cli.writes())

    def test_a_site_changed_after_the_backup_is_refused(self) -> None:
        self.cli.site["pages"][0]["name"] = "Edited by the Pages team"
        code, report = harness.apply(self.cli, self.plan_path, self.backup)
        self.assertIn("the site changed after the backup", report["reason"])
        self.assertEqual([], self.cli.writes())

    def test_a_published_site_needs_the_local_exception(self) -> None:
        config = harness.write_config(self.dir, write_to_published_site=False)
        _, errors, _, _ = harness.prepare(self.dir, self.cli, config_path=config, name="no-exception")
        self.assertTrue(any("the site is published" in e for e in errors), errors)
        code, report = harness.apply(self.cli, self.plan_path, self.backup, config_path=config)
        self.assertEqual(1, code)
        self.assertEqual([], self.cli.writes())

    def test_any_other_site_is_refused(self) -> None:
        site = stand_in_cli.load_site()
        site["domain"] = "another-live-site"
        with self.assertRaisesRegex(common.CliError, "not the one in the local config"):
            common.check_target(site, common.load_config(harness.CONFIG))

    def test_the_cli_wrapper_refuses_catalog_publish_and_force(self) -> None:
        with harness.patched(self.cli):
            for args in (
                ("catalog", "create-item", "--sku", "x"),
                ("liveops", "create-promo-code"),
                ("shopbuilder", "publish", "--slug", "x"),
                ("shopbuilder", "enable-preview", "--slug", "x"),
                ("shopbuilder", "delete-block", "--blockid", "x"),
                ("shopbuilder", "duplicate-block", "--blockid", "x"),
                ("shopbuilder", "update-block", "--force"),
            ):
                with self.subTest(args=args), self.assertRaises(common.CliError):
                    common.run_json(*args)
        self.assertEqual([], self.cli.calls)


if __name__ == "__main__":
    unittest.main()
