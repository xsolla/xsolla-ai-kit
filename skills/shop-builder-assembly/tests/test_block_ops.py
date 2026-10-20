from __future__ import annotations

import copy
import importlib.util
import json
import sys
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import block_ops  # noqa: E402
import render_plan  # noqa: E402
import validate_shop_brief  # noqa: E402

QUESTS = "_quest-platform_quests-block"


def quests_block(block_id: str = "q1", internal: dict | None = None) -> dict:
    return {
        "_id": block_id,
        "module": "federated",
        "hidden": False,
        "values": {
            "blockId": QUESTS,
            "internalBlockValues": internal
            if internal is not None
            else {"questIds": [], "maxQuests": 6, "overrides": {}},
        },
    }


def plain_block(block_id: str, module: str) -> dict:
    return {"_id": block_id, "module": module, "values": {}}


def make_structure(extra_quests: bool = True) -> dict:
    blocks = [
        plain_block("h1", "header"),
        plain_block("f1", "faq"),
        plain_block("n1", "newStore"),
        plain_block("d1", "description"),
        plain_block("ft", "footer"),
    ]
    if extra_quests:
        blocks.insert(1, quests_block("q1"))
    return {
        "_id": "landing-1",
        "type": "topup",
        "pages": [{"_id": "page-1", "name": "Main", "path": "/", "blocks": blocks}],
    }


def ops_brief(operations: list[dict]) -> dict:
    return {
        "version": 1,
        "project": {
            "merchant_id": 940463,
            "project_id": 316665,
            "environment": "test",
            "test_project_acknowledged": True,
        },
        "site": {"slug": "qa-quests-spike"},
        "block_operations": operations,
    }


def add_op(**overrides: object) -> dict:
    op = {
        "op": "add",
        "module": QUESTS,
        "page": "/",
        "index": 2,
        "values": {"questIds": ["a", "b"], "maxQuests": 6, "layout.cardAlign": "center"},
    }
    op.update(overrides)
    return op


class BlockOpsTests(unittest.TestCase):
    def errors(self, *operations: dict, structure: dict | None = None) -> list[str]:
        return block_ops.validate_block_operations(
            ops_brief(list(operations)), structure
        )

    def test_rejects_non_quests_module(self) -> None:
        errors = self.errors(add_op(module="faq"))
        self.assertTrue(any("module" in e for e in errors), errors)

    def test_rejects_unknown_leaf(self) -> None:
        errors = self.errors(
            add_op(values={"layout.nope": 1}), add_op(values={"hidden": True})
        )
        self.assertEqual(2, sum("not a patchable leaf" in e for e in errors), errors)

    def test_limits_questids_and_maxquests(self) -> None:
        too_many = [f"q{i}" for i in range(25)]
        self.assertTrue(self.errors(add_op(values={"questIds": too_many})))
        self.assertTrue(self.errors(add_op(values={"questIds": ["a", "a"]})))
        for bad in (0, 25, 1.5, True, "6"):
            self.assertTrue(self.errors(add_op(values={"maxQuests": bad})), bad)
        for good in (1, 24):
            self.assertEqual([], self.errors(add_op(values={"maxQuests": good})))
        self.assertEqual(
            [], self.errors(add_op(values={"questIds": [f"q{i}" for i in range(24)]}))
        )
        self.assertTrue(self.errors(add_op(values={"overrides.a.title": "x" * 121})))
        self.assertTrue(
            self.errors(add_op(values={"overrides.a.description": "x" * 401}))
        )
        self.assertTrue(self.errors(add_op(values={"layout.cardAlign": "left"})))

    def test_rejects_http_image(self) -> None:
        self.assertTrue(
            self.errors(add_op(values={"overrides.a.imageUrl": "http://x.test/a.png"}))
        )
        self.assertEqual(
            [],
            self.errors(
                add_op(values={"overrides.a.imageUrl": "https://x.test/a.png"})
            ),
        )

    def test_rejects_ops_with_page_overrides(self) -> None:
        brief = ops_brief([add_op()])
        brief["content"] = {
            "page_overrides": [{"name": "Home", "path": "/", "blocks": ["header"]}]
        }
        errors = validate_shop_brief.validate(brief)
        self.assertTrue(any("page_overrides" in e for e in errors), errors)

    def test_ops_mode_never_removes_unlisted_blocks(self) -> None:
        structure = make_structure(extra_quests=False)
        plan = render_plan.build_plan(ops_brief([add_op()]), structure)
        self.assertEqual([], plan["removals"])
        self.assertEqual("block_add", plan["block_operations"][0]["type"])
        for page in plan["pages"]:
            self.assertEqual([], page["removals"])

    def test_ops_mode_skips_site_wide_phases(self) -> None:
        plan = render_plan.build_plan(ops_brief([add_op()]), make_structure(False))
        self.assertEqual("block_operations", plan["mode"])
        self.assertEqual(["block_operations"], plan["implemented_phases"])
        self.assertEqual([], plan["pages"])
        self.assertEqual([], plan["navigation"])
        self.assertEqual([], plan["locales"])
        self.assertEqual([], plan["catalog_sections"])
        self.assertEqual([], plan["current_state"]["extra_pages"])
        self.assertNotIn("catalog_links", plan["order"])
        self.assertNotIn("pages", plan["order"])
        self.assertNotIn("navigation", plan["order"])

    def test_ops_mode_minimal_brief_is_valid(self) -> None:
        brief = ops_brief([add_op()])
        self.assertEqual([], validate_shop_brief.validate(brief))
        for path in (("project", "environment"), ("project", "merchant_id"),
                     ("project", "project_id"), ("site", "slug")):
            broken = copy.deepcopy(brief)
            del broken[path[0]][path[1]]
            self.assertTrue(validate_shop_brief.validate(broken), path)
        broken = copy.deepcopy(brief)
        broken["block_operations"] = []
        self.assertTrue(validate_shop_brief.validate(broken))
        broken = copy.deepcopy(brief)
        broken["block_operations"] = [add_op(module="faq")]
        self.assertTrue(validate_shop_brief.validate(broken))

    def test_confirmation_id_changes_with_ops(self) -> None:
        structure = make_structure(False)
        first = render_plan.build_plan(ops_brief([add_op()]), structure)
        second = render_plan.build_plan(
            ops_brief([add_op(values={"maxQuests": 4})]), structure
        )
        again = render_plan.build_plan(ops_brief([add_op()]), structure)
        self.assertNotEqual(first["confirmation_id"], second["confirmation_id"])
        self.assertEqual(first["confirmation_id"], again["confirmation_id"])

    def test_block_id_must_be_quests_block(self) -> None:
        structure = make_structure()
        self.assertEqual(
            [], self.errors({"op": "hide", "block_id": "q1"}, structure=structure)
        )
        wrong_module = self.errors({"op": "hide", "block_id": "h1"}, structure=structure)
        self.assertTrue(any("Quests block" in e for e in wrong_module), wrong_module)
        missing = self.errors({"op": "delete", "block_id": "zzz"}, structure=structure)
        self.assertTrue(any("not in the backup structure" in e for e in missing), missing)
        with self.assertRaises(ValueError):
            render_plan.build_plan(
                ops_brief([{"op": "hide", "block_id": "h1"}]), structure
            )

    def test_short_keys_map_to_full_paths_and_report_missing_parents(self) -> None:
        self.assertEqual(
            ["values", "internalBlockValues", "layout", "cardAlign"],
            block_ops.full_path("layout.cardAlign"),
        )
        self.assertEqual(
            ["values", "internalBlockValues", "overrides", "a.b", "title"],
            block_ops.full_path("overrides.a.b.title"),
        )
        structure = make_structure()
        plan = render_plan.build_plan(
            ops_brief(
                [
                    {
                        "op": "update",
                        "block_id": "q1",
                        "values": {
                            "maxQuests": 3,
                            "layout.cardAlign": "end",
                            "overrides.a.title": "Hi",
                        },
                    }
                ]
            ),
            structure,
        )
        item = plan["block_operations"][0]
        self.assertEqual("block_values", item["type"])
        self.assertEqual(
            [
                ["values", "internalBlockValues", "layout"],
                ["values", "internalBlockValues", "overrides", "a"],
            ],
            [parent["path"] for parent in item["create_parents"]],
        )
        self.assertEqual({}, item["create_parents"][0]["value"])
        self.assertEqual(
            ["values", "internalBlockValues", "maxQuests"], item["patches"][0]["path"]
        )

    def test_existing_parent_is_not_recreated(self) -> None:
        structure = make_structure(extra_quests=False)
        structure["pages"][0]["blocks"].insert(
            1,
            quests_block(
                "q2",
                {"questIds": [], "layout": {"cardAlign": "start"}, "overrides": {"a": {}}},
            ),
        )
        plan = render_plan.build_plan(
            ops_brief(
                [
                    {
                        "op": "update",
                        "block_id": "q2",
                        "values": {"layout.cardAlign": "end", "overrides.a.title": "Hi"},
                    }
                ]
            ),
            structure,
        )
        self.assertEqual([], plan["block_operations"][0]["create_parents"])

    def test_plan_items_follow_brief_order_and_types(self) -> None:
        plan = render_plan.build_plan(
            ops_brief(
                [
                    add_op(translations={"en-US": {"heading": "Quests"}}),
                    {"op": "reset", "block_id": "q1", "paths": ["overrides.a.imageUrl"]},
                    {"op": "move", "block_id": "q1", "index": 0},
                    {"op": "duplicate", "block_id": "q1", "index": 3},
                    {"op": "hide", "block_id": "q1"},
                    {"op": "show", "block_id": "q1"},
                    {"op": "delete", "block_id": "q1"},
                ]
            ),
            make_structure(),
        )
        self.assertEqual(
            [
                "block_add",
                "block_values",
                "block_localization",
                "block_reset",
                "block_move",
                "block_duplicate",
                "block_visibility",
                "block_visibility",
                "block_delete",
            ],
            [item["type"] for item in plan["block_operations"]],
        )
        self.assertEqual(
            [{"block_id": "q1", "page_id": "page-1", "reason": "explicit delete op"}],
            plan["removals"],
        )
        add = plan["block_operations"][0]
        self.assertEqual("federated_patch", add["strategy"])
        self.assertEqual("page-1", add["page_id"])
        values = plan["block_operations"][1]
        self.assertEqual("op:0", values["block_ref"])
        self.assertEqual(
            [["values", "internalBlockValues", "layout"]],
            [parent["path"] for parent in values["create_parents"]],
        )


    def test_apply_runs_only_block_items_and_refuses_unsupported(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "apply_plan_ops", ROOT / "scripts" / "apply_plan.py"
        )
        apply_plan = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(apply_plan)
        structure = make_structure()
        plan = render_plan.build_plan(
            ops_brief(
                [
                    {
                        "op": "update",
                        "block_id": "q1",
                        "values": {"layout.cardAlign": "end"},
                    },
                    {"op": "hide", "block_id": "q1"},
                ]
            ),
            structure,
        )
        with mock.patch.object(apply_plan, "run_json") as run_json:
            apply_plan.apply_block_operations("qa-quests-spike", "landing-1", plan)
        commands = [call.args[:2] for call in run_json.call_args_list]
        self.assertEqual([("shopbuilder", "update-block")] * 3, commands)
        first = json.loads(run_json.call_args_list[0].args[-1])
        self.assertEqual("add", first["blockOps"]["patches"][0]["op"])
        self.assertEqual({}, first["blockOps"]["patches"][0]["value"])
        unsupported = render_plan.build_plan(ops_brief([add_op()]), make_structure(False))
        with mock.patch.object(apply_plan, "run_json") as run_json:
            with self.assertRaisesRegex(RuntimeError, "block_add"):
                apply_plan.apply_block_operations("s", "landing-1", unsupported)
        run_json.assert_not_called()


if __name__ == "__main__":
    unittest.main()
