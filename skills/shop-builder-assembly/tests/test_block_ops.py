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
QUEST_A = "11111111-1111-4111-8111-111111111111"
QUEST_B = "22222222-2222-4222-8222-222222222222"


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
        "languages": ["en-US"],
        "pages": [{"_id": "page-1", "name": "Main", "path": "/", "blocks": blocks}],
    }


def ops_brief(operations: list[dict]) -> dict:
    return {
        "version": 1,
        "project": {
            "merchant_id": 1,
            "project_id": 2,
            "environment": "test",
            "test_project_acknowledged": True,
        },
        "site": {"slug": "my-test-site"},
        "block_operations": operations,
    }


def add_op(**overrides: object) -> dict:
    op = {
        "op": "add",
        "module": QUESTS,
        "page": "/",
        "index": 2,
        "values": {"questIds": [QUEST_A, QUEST_B], "maxQuests": 6, "layout.cardAlign": "center"},
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
        too_many = [f"{i:08x}-1111-4111-8111-111111111111" for i in range(25)]
        self.assertTrue(self.errors(add_op(values={"questIds": too_many})))
        self.assertTrue(self.errors(add_op(values={"questIds": [QUEST_A, QUEST_A]})))
        for bad in (0, 25, 1.5, True, "6"):
            self.assertTrue(self.errors(add_op(values={"maxQuests": bad})), bad)
        for good in (1, 24):
            self.assertEqual([], self.errors(add_op(values={"maxQuests": good})))

        self.assertEqual(
            [], self.errors(add_op(values={"questIds": [f"{i:08x}-1111-4111-8111-111111111111" for i in range(24)]}))
        )
        self.assertTrue(self.errors(add_op(values={f"overrides.{QUEST_A}.title": "x" * 121})))
        self.assertTrue(
            self.errors(add_op(values={f"overrides.{QUEST_A}.description": "x" * 401}))
        )
        self.assertTrue(self.errors(add_op(values={"layout.cardAlign": "left"})))

    def test_rejects_quest_ids_that_are_not_uuids(self) -> None:
        for bad in ("does-not-exist", "q1", QUEST_A.replace("-", ""), QUEST_A + "0"):
            errors = self.errors(add_op(values={"questIds": [QUEST_A, bad]}))
            self.assertTrue(any("questIds" in e and "UUID" in e for e in errors), (bad, errors))
            errors = self.errors(add_op(values={f"overrides.{bad}.title": "Hi"}))
            self.assertTrue(any("UUID" in e for e in errors), (bad, errors))
            reset = {"op": "reset", "block_id": "q1", "paths": [f"overrides.{bad}"]}
            errors = self.errors(reset)
            self.assertTrue(any("UUID" in e for e in errors), (bad, errors))
        self.assertEqual([], self.errors(add_op(values={"questIds": [QUEST_A.upper()]})))

    def test_rejects_http_image(self) -> None:
        self.assertTrue(
            self.errors(add_op(values={f"overrides.{QUEST_A}.imageUrl": "http://x.test/a.png"}))
        )
        self.assertEqual(
            [],
            self.errors(
                add_op(values={f"overrides.{QUEST_A}.imageUrl": "https://x.test/a.png"})
            ),
        )

    def test_reward_fields_are_read_only_on_add_and_update(self) -> None:
        for field, value in (
            ("rewardText", "Gold badge"),
            ("rewardImageUrl", "https://x.test/reward.png"),
        ):
            key = f"overrides.{QUEST_A}.{field}"
            for op in (
                add_op(values={key: value}),
                {"op": "update", "block_id": "q1", "values": {key: value}},
            ):
                errors = self.errors(op, structure=make_structure())
                self.assertTrue(errors, (field, op["op"]))
                self.assertTrue(
                    any("come from the quest and can't be changed" in e for e in errors),
                    errors,
                )

    def test_reward_fields_are_not_patchable_leaves(self) -> None:
        for field in ("rewardText", "rewardImageUrl"):
            key = f"overrides.{QUEST_A}.{field}"
            self.assertIsNone(block_ops.split_key(key))
            self.assertNotIn(f"overrides.<questId>.{field}", block_ops.QUESTS_PATCHABLE_LEAVES)

    def test_reset_of_reward_fields_is_rejected(self) -> None:
        paths = [f"overrides.{QUEST_A}.rewardText", f"overrides.{QUEST_A}.rewardImageUrl"]
        reset = {"op": "reset", "block_id": "q1", "paths": paths}
        errors = self.errors(reset, structure=make_structure())
        self.assertEqual(2, len(errors), errors)
        self.assertTrue(
            all("come from the quest and can't be changed" in e for e in errors), errors
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

    def test_delete_is_refused_with_needs_human_guidance(self) -> None:
        structure = make_structure()
        brief = ops_brief([{"op": "delete", "block_id": "q1"}])
        for errors in (
            block_ops.validate_block_operations(brief, structure),
            block_ops.validate_block_operations(brief),
            validate_shop_brief.validate(brief),
        ):
            self.assertEqual(1, len(errors), errors)
            message = errors[0]
            self.assertIn("block_operations[0].op delete is not supported", message)
            self.assertIn("needs_human", message)
            self.assertIn("Site Builder editor", message)
            self.assertIn("op hide", message)
        with self.assertRaisesRegex(ValueError, "needs_human"):
            render_plan.build_plan(brief, structure)
        self.assertNotIn("delete", block_ops.OPERATIONS)

    def test_ops_mode_requires_a_test_environment(self) -> None:
        brief = ops_brief([add_op()])
        brief["project"]["environment"] = "sandbox"
        errors = validate_shop_brief.validate(brief)
        self.assertTrue(any("environment" in e and "test" in e for e in errors), errors)
        brief["project"]["environment"] = "test"
        self.assertEqual([], validate_shop_brief.validate(brief))

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
        missing = self.errors({"op": "hide", "block_id": "zzz"}, structure=structure)
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
                            f"overrides.{QUEST_A}.title": "Hi",
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
                ["values", "internalBlockValues", "overrides", QUEST_A],
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
                {"questIds": [], "layout": {"cardAlign": "start"}, "overrides": {QUEST_A: {}}},
            ),
        )
        plan = render_plan.build_plan(
            ops_brief(
                [
                    {
                        "op": "update",
                        "block_id": "q2",
                        "values": {"layout.cardAlign": "end", f"overrides.{QUEST_A}.title": "Hi"},
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
                    {"op": "reset", "block_id": "q1", "paths": [f"overrides.{QUEST_A}.imageUrl"]},
                    {"op": "move", "block_id": "q1", "index": 0},
                    {"op": "duplicate", "block_id": "q1", "index": 3},
                    {"op": "hide", "block_id": "q1"},
                    {"op": "show", "block_id": "q1"},
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
            ],
            [item["type"] for item in plan["block_operations"]],
        )
        self.assertEqual([], plan["removals"])
        add = plan["block_operations"][0]
        self.assertEqual("federated_patch", add["strategy"])
        self.assertEqual("page-1", add["page_id"])
        values = plan["block_operations"][1]
        self.assertEqual("op:0", values["block_ref"])
        self.assertEqual(
            [["values", "internalBlockValues", "layout"]],
            [parent["path"] for parent in values["create_parents"]],
        )


    def test_apply_refuses_an_unknown_item_type_before_any_write(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "apply_plan_ops", ROOT / "scripts" / "apply_plan.py"
        )
        apply_plan = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(apply_plan)
        plan = render_plan.build_plan(
            ops_brief([{"op": "hide", "block_id": "q1"}]), make_structure()
        )
        plan["block_operations"][0]["type"] = "block_teleport"
        with mock.patch.object(apply_plan, "run_json") as run_json:
            with self.assertRaisesRegex(RuntimeError, "block_teleport"):
                apply_plan.apply_block_operations("s", "landing-1", plan)
        run_json.assert_not_called()


class ReviewValidationTests(unittest.TestCase):
    """Rules that stop a brief before confirmation instead of failing at apply or verify."""

    def errors(self, *operations: dict, structure: dict | None = None) -> list[str]:
        return block_ops.validate_block_operations(ops_brief(list(operations)), structure)

    def test_locale_must_be_enabled_on_the_site_at_plan_time(self) -> None:
        op = {"op": "update", "block_id": "q1", "translations": {"de-DE": {"heading": "Quests"}}}
        # Without a structure the locale cannot be checked (preflight stage).
        self.assertEqual([], self.errors(op))
        errors = self.errors(op, structure=make_structure())
        self.assertEqual(1, len(errors), errors)
        self.assertIn("de-DE is not enabled", errors[0])
        self.assertIn("en-US", errors[0])
        with self.assertRaisesRegex(ValueError, "de-DE is not enabled"):
            render_plan.build_plan(ops_brief([op]), make_structure())
        ok = {"op": "update", "block_id": "q1", "translations": {"en-US": {"heading": "Quests"}}}
        self.assertEqual([], self.errors(ok, structure=make_structure()))

    def test_duplicate_index_is_bounded_by_the_page(self) -> None:
        structure = make_structure()  # 6 blocks on the page
        for good in (0, 3, 6):
            op = {"op": "duplicate", "block_id": "q1", "index": good}
            self.assertEqual([], self.errors(op, structure=structure), good)
        for bad in (7, 99):
            op = {"op": "duplicate", "block_id": "q1", "index": bad}
            errors = self.errors(op, structure=structure)
            self.assertTrue(any("past the end" in e for e in errors), (bad, errors))
            with self.assertRaisesRegex(ValueError, "past the end"):
                render_plan.build_plan(ops_brief([op]), structure)

    def test_bounds_count_blocks_added_earlier_on_the_page(self) -> None:
        structure = make_structure()  # 6 blocks; after one add there are 7
        self.assertEqual(
            [],
            self.errors(
                add_op(index=6),
                {"op": "duplicate", "block_id": "q1", "index": 7},
                structure=structure,
            ),
        )
        errors = self.errors(
            add_op(index=6),
            {"op": "duplicate", "block_id": "q1", "index": 8},
            structure=structure,
        )
        self.assertTrue(any("block_operations[1].index 8 is past the end" in e for e in errors), errors)
        self.assertTrue(self.errors(add_op(index=7), structure=structure))
        self.assertEqual([], self.errors(add_op(index=6), structure=structure))
        # A move stays inside the page: 0 .. count - 1, with earlier adds counted.
        self.assertTrue(self.errors({"op": "move", "block_id": "q1", "index": 6}, structure=structure))
        self.assertEqual(
            [], self.errors({"op": "move", "block_id": "q1", "index": 5}, structure=structure)
        )
        self.assertEqual(
            [],
            self.errors(add_op(), {"op": "move", "block_id": "q1", "index": 6}, structure=structure),
        )

    def test_duplicate_needs_an_index_next_to_another_order_change(self) -> None:
        structure = make_structure()
        dup = {"op": "duplicate", "block_id": "q1"}
        self.assertEqual([], self.errors(dup, structure=structure))
        # Ops that do not move blocks leave the default index valid.
        self.assertEqual(
            [], self.errors(dup, {"op": "hide", "block_id": "q1"}, structure=structure)
        )
        for other in (add_op(), {"op": "move", "block_id": "q1", "index": 4}, dict(dup, index=2)):
            errors = self.errors(other, dup, structure=structure)
            self.assertTrue(any("needs an explicit index" in e for e in errors), (other, errors))
        self.assertEqual(
            [],
            self.errors(
                {"op": "move", "block_id": "q1", "index": 4},
                dict(dup, index=5),
                structure=structure,
            ),
        )

    def test_conflicting_ops_on_one_leaf_are_rejected(self) -> None:
        title = f"overrides.{QUEST_A}.title"
        update = {"op": "update", "block_id": "q1", "values": {title: "A"}}
        cases = [
            (update, {"op": "reset", "block_id": "q1", "paths": [title]}),
            ({"op": "reset", "block_id": "q1", "paths": [title]}, update),
            (update, {"op": "reset", "block_id": "q1", "paths": [f"overrides.{QUEST_A}"]}),
            (update, {"op": "update", "block_id": "q1", "values": {title: "B"}}),
            (
                {"op": "update", "block_id": "q1", "translations": {"en-US": {"heading": "A"}}},
                {"op": "update", "block_id": "q1", "translations": {"en-US": {"heading": "B"}}},
            ),
        ]
        for first, second in cases:
            errors = self.errors(first, second)
            self.assertEqual(1, len(errors), (first, second, errors))
            self.assertIn("block_operations[0] and block_operations[1] conflict on q1", errors[0])
            with self.assertRaisesRegex(ValueError, "conflict on q1"):
                render_plan.build_plan(ops_brief([first, second]), make_structure())
        # Same value twice, different leaves, or different blocks are fine.
        self.assertEqual([], self.errors(update, dict(update)))
        self.assertEqual(
            [],
            self.errors(update, {"op": "reset", "block_id": "q1", "paths": [f"overrides.{QUEST_A}.imageUrl"]}),
        )
        self.assertEqual(
            [], self.errors(update, {"op": "reset", "block_id": "q2", "paths": [title]})
        )

    def test_unhashable_editor_preview_is_an_error_not_a_crash(self) -> None:
        for bad in (["live"], {"a": 1}, 5, None):
            errors = self.errors(add_op(values={"editorPreview": bad}))
            self.assertTrue(any("editorPreview must use" in e for e in errors), (bad, errors))
        self.assertEqual([], self.errors(add_op(values={"editorPreview": "live"})))

    def test_image_urls_reject_userinfo(self) -> None:
        for field in ("imageUrl",):
            key = f"overrides.{QUEST_A}.{field}"
            for bad in ("https://user:pw@x.test/a.png", "https://user@x.test/a.png", "https://@x.test/a.png"):
                errors = self.errors(add_op(values={key: bad}))
                self.assertTrue(errors, bad)
            self.assertEqual([], self.errors(add_op(values={key: "https://x.test/a.png?a=b@c"})))

    def test_ops_brief_rejects_keys_it_would_ignore(self) -> None:
        self.assertEqual([], validate_shop_brief.validate(ops_brief([add_op()])))
        for mutate, needle in (
            (lambda b: b.update(catalog={"groups": []}), "catalog is not allowed"),
            (lambda b: b.update(content={"events": []}), "content is not allowed"),
            (lambda b: b.update(game={"name": "G"}), "game is not allowed"),
            (lambda b: b["site"].update(pages=[]), "site.pages is not allowed"),
            (lambda b: b["site"].update(name="Shop"), "site.name is not allowed"),
            (lambda b: b["project"].update(region="eu"), "project.region is not allowed"),
        ):
            brief = ops_brief([add_op()])
            mutate(brief)
            errors = validate_shop_brief.validate(brief)
            self.assertTrue(any(needle in e for e in errors), (needle, errors))


if __name__ == "__main__":
    unittest.main()
