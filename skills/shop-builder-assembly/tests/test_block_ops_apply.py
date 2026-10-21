"""Apply and verify Quests block operations against a fake `xsolla` CLI."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import render_plan  # noqa: E402
import verify_structure  # noqa: E402
from block_ops import QUESTS_MODULE, QUESTS_VERSION  # noqa: E402


def load_apply_plan():
    spec = importlib.util.spec_from_file_location(
        "apply_plan_for_block_ops", ROOT / "scripts" / "apply_plan.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


apply_plan = load_apply_plan()

SLUG = "qa-quests-spike"
LANDING = "landing-1"
PAGE = "page-1"
HEADING_TEXT_ID = "L:00000000-0000-0000-0000-000000000001"
QUEST_A = "11111111-1111-4111-8111-111111111111"

CDN_DEFAULTS = {
    "defaultData": {
        "translations": {"heading": "L:short-heading"},
        "questIds": [],
        "maxQuests": 6,
        "overrides": {},
        "layout": {"cardAlign": "center", "showHeading": True},
        "editorPreview": "live",
    },
    "resources": {
        "localizedValues": {
            "L:short-heading": {
                "texts": {
                    "__type": "localized-value-descriptor",
                    "localizedString": {"en-US": "Quests"},
                    "enable": True,
                    "tag": "heading",
                }
            }
        }
    },
}


def quests_block(block_id: str = "q1", internal: dict | None = None) -> dict:
    return {
        "_id": block_id,
        "module": "federated",
        "hidden": False,
        "components": [],
        "parent": {"id": PAGE, "type": "page"},
        "values": {
            "blockId": QUESTS_MODULE,
            "version": QUESTS_VERSION,
            "host": "https://cdn.example/quests/",
            "useAsNativeBlock": False,
            "internalBlockValues": internal
            if internal is not None
            else {
                "questIds": [],
                "maxQuests": 3,
                "overrides": {},
                "translations": {"heading": "L:short-heading"},
            },
            "resources": {
                "localizedValues": {
                    "L:short-heading": {"texts": {"enable": True, "id": HEADING_TEXT_ID}}
                }
            },
        },
    }


def plain_block(block_id: str, module: str) -> dict:
    return {
        "_id": block_id,
        "module": module,
        "hidden": False,
        "components": [{"_id": "volatile", "title": block_id}],
        "values": {"title": block_id},
    }


class FakeSite:
    """A landing that answers the `xsolla shopbuilder` commands the executor uses."""

    def __init__(self, clears_landing_list: bool = False) -> None:
        self.blocks = [
            plain_block("h1", "header"),
            quests_block("q1"),
            plain_block("f1", "faq"),
            plain_block("n1", "newStore"),
            plain_block("ft", "footer"),
        ]
        self.landing_blocks = [block["_id"] for block in self.blocks]
        self.texts = {HEADING_TEXT_ID: {"description": "heading", "translations": {"en-US": "Quests"}}}
        self.clears_landing_list = clears_landing_list
        self.calls: list[tuple[str, ...]] = []
        self.counter = 0
        self.noop_patches = 0
        self.fail_update = False
        self.double_add = False

    # --- reads -----------------------------------------------------------------
    def structure_value(self) -> dict:
        blocks = copy.deepcopy(self.blocks)
        for block in blocks:
            for component in block.get("components", []):
                component["_id"] = f"volatile-{self.counter}"
        self.counter += 1
        return {
            "_id": LANDING,
            "domain": SLUG,
            "type": "topup",
            "languages": ["en-US"],
            "blocks": list(self.landing_blocks),
            "pages": [{"_id": PAGE, "name": "Main", "path": "/", "blocks": blocks}],
        }

    def localization_value(self) -> dict:
        return {"common": {"texts": {}}, "pages": {PAGE: {"texts": copy.deepcopy(self.texts)}}}

    def find(self, block_id: str) -> dict | None:
        return next((b for b in self.blocks if b["_id"] == block_id), None)

    # --- the CLI ---------------------------------------------------------------
    def run_json(self, *args: str) -> object:
        self.calls.append(args)
        assert args[0] == "shopbuilder", args
        command = args[1]
        options: dict[str, object] = {}
        rest = list(args[2:])
        while rest:
            token = rest.pop(0)
            assert token.startswith("--"), args
            if rest and not rest[0].startswith("--"):
                options[token] = rest.pop(0)
            else:
                options[token] = True
        handler = getattr(self, "cmd_" + command.replace("-", "_"))
        return handler(options)

    def cmd_get_structure(self, options: dict) -> object:
        return {"ok": True, "data": self.structure_value()}

    def cmd_get_localization(self, options: dict) -> object:
        return {"ok": True, "data": self.localization_value()}

    def cmd_add_block(self, options: dict) -> object:
        assert options["--block"] == "federated"
        self.counter += 1
        block = {
            "_id": f"new-{self.counter}",
            "module": "federated",
            "hidden": False,
            "components": [],
            "parent": {"id": PAGE, "type": "page"},
            "values": {
                "blockId": "",
                "host": "",
                "version": "",
                "useAsNativeBlock": False,
                "internalBlockValues": {},
                "resources": {"localizedValues": {}, "mediaValues": {}},
            },
        }
        self.blocks.insert(int(options.get("--index", 0)), block)
        self.landing_blocks.append(block["_id"])
        if self.double_add:  # an auth-retried add-block that had already applied
            self.double_add = False
            self.cmd_add_block(options)
        return {"ok": True}

    def cmd_move_block(self, options: dict) -> object:
        block = self.blocks.pop(int(options["--source"]))
        self.blocks.insert(int(options["--destination"]), block)
        return {"ok": True}

    def cmd_duplicate_block(self, options: dict) -> object:
        source = self.find(options["--blockid"])
        position = self.blocks.index(source)
        self.counter += 1
        copy_block = copy.deepcopy(source)
        copy_block["_id"] = f"copy-{self.counter}"
        self.blocks.insert(int(options.get("--index", position + 1)), copy_block)
        self.landing_blocks.append(copy_block["_id"])
        return {"ok": True}

    def cmd_delete_block(self, options: dict) -> object:
        if options.get("--force") is not True:
            raise RuntimeError("confirmation required: re-run with --force")
        block = self.find(options["--blockid"])
        if block is None:
            raise RuntimeError("http_404 block_is_not_presented_on_page")
        self.blocks.remove(block)
        if self.clears_landing_list:
            self.landing_blocks.remove(block["_id"])
        return {"ok": True}

    def cmd_update_block(self, options: dict) -> object:
        if self.fail_update:
            raise RuntimeError("update-block failed: boom")
        payload = json.loads(options["--data"])
        applied = []
        for change in payload.values():
            assert change["type"] == "block", change
            block = self.find(change["id"])
            for patch in change["patches"]:
                if self.apply_patch(block, patch):
                    applied.append(patch)
                else:
                    self.noop_patches += 1
        return {"ok": True, "data": {"patches": applied}}

    def apply_patch(self, block: dict, patch: dict) -> bool:
        path = patch["path"]
        node = block
        for segment in path[:-1]:
            if not isinstance(node, dict) or segment not in node:
                return False  # the real API answers 200 and ignores the patch
            node = node[segment]
        leaf = path[-1]
        if patch["op"] == "remove":
            if leaf not in node:
                return False
            del node[leaf]
            return True
        node[leaf] = copy.deepcopy(patch["value"])
        if path == ["values", "resources", "localizedValues"]:
            self.mint_texts(node[leaf])
        return True

    def mint_texts(self, descriptors: dict) -> None:
        for key, descriptor in list(descriptors.items()):
            self.counter += 1
            text_id = f"L:minted-{self.counter}"
            strings = descriptor["texts"].get("localizedString", {})
            self.texts[text_id] = {"description": key, "translations": dict(strings)}
            descriptors[key] = {"texts": {"enable": True, "id": text_id}}

    def cmd_update_many_localization(self, options: dict) -> object:
        payload = json.loads(options["--data"])
        for scope, values in payload["perScopeValues"].items():
            assert scope == PAGE
            for text_id, value in values.items():
                self.texts[text_id]["translations"][payload["locale"]] = value["translation"]
        return {"ok": True}

    def write_calls(self) -> list[tuple[str, ...]]:
        reads = {"get-structure", "get-localization"}
        return [call for call in self.calls if call[1] not in reads]


def ops_brief(operations: list[dict]) -> dict:
    return {
        "version": 1,
        "project": {
            "merchant_id": 940463,
            "project_id": 316665,
            "environment": "test",
            "test_project_acknowledged": True,
        },
        "site": {"slug": SLUG},
        "block_operations": operations,
    }


class BlockOpsApplyBase(unittest.TestCase):
    def setUp(self) -> None:
        self.site = FakeSite()
        patches = [
            mock.patch.object(apply_plan, "run_json", side_effect=self.site.run_json),
            mock.patch.object(
                apply_plan, "fetch_quests_defaults", return_value=copy.deepcopy(CDN_DEFAULTS)
            ),
        ]
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)

    def plan_for(self, operations: list[dict]) -> dict:
        return render_plan.build_plan(ops_brief(operations), self.site.structure_value())

    def apply(self, operations: list[dict], plan: dict | None = None) -> tuple[dict, dict]:
        plan = plan or self.plan_for(operations)
        refs: dict = {}
        apply_plan.apply_block_operations(SLUG, LANDING, plan, refs)
        return plan, refs

    def verify(self, plan: dict, refs: dict | None = None) -> list[str]:
        return verify_structure.verify_block_operations(
            plan, self.site.structure_value(), self.site.localization_value(), refs
        )

    def page_ids(self) -> list[str]:
        return [block["_id"] for block in self.site.blocks]


class BlockOpsApplyTests(BlockOpsApplyBase):
    def test_values_use_leaf_patches_only(self) -> None:
        operations = [
            {
                "op": "update",
                "block_id": "q1",
                "values": {
                    "maxQuests": 4,
                    "layout.cardAlign": "end",
                    f"overrides.{QUEST_A}.title": "Daily quest",
                },
            }
        ]
        plan, refs = self.apply(operations)
        changes = []
        for call in self.site.calls:
            if call[1] == "update-block":
                changes.extend(json.loads(call[call.index("--data") + 1]).values())
        self.assertTrue(changes)
        root = ["values", "internalBlockValues"]
        for change in changes:
            for patch in change["patches"]:
                self.assertEqual(root, patch["path"][:2])
                self.assertGreaterEqual(len(patch["path"]), 3, patch)
                if patch["op"] == "add":
                    self.assertEqual({}, patch["value"])
                else:
                    self.assertIn(patch["op"], ("replace", "remove"))
        internal = self.site.find("q1")["values"]["internalBlockValues"]
        self.assertEqual(4, internal["maxQuests"])
        self.assertEqual("end", internal["layout"]["cardAlign"])
        self.assertEqual("Daily quest", internal["overrides"][QUEST_A]["title"])
        self.assertEqual(0, self.site.noop_patches)
        self.assertEqual([], self.verify(plan, refs))

    def test_duplicate_keeps_both_instances(self) -> None:
        plan, refs = self.apply([{"op": "duplicate", "block_id": "q1"}])
        ids = self.page_ids()
        self.assertEqual(["h1", "q1"], ids[:2])
        self.assertTrue(ids[2].startswith("copy-"), ids)
        self.assertEqual(5 + 1, len(ids))
        self.assertEqual(self.site.find("q1")["values"], self.site.find(ids[2])["values"])
        self.assertEqual([], self.verify(plan, refs))

    def test_delete_requires_planned_removal(self) -> None:
        plan = self.plan_for([{"op": "delete", "block_id": "q1"}])
        plan["removals"] = []
        with self.assertRaisesRegex(RuntimeError, "not in the confirmed plan removals"):
            apply_plan.apply_block_operations(SLUG, LANDING, plan, {})
        self.assertEqual([], self.site.write_calls())
        self.assertIsNotNone(self.site.find("q1"))

    def test_delete_uses_force_delete_while_on_page(self) -> None:
        plan, refs = self.apply([{"op": "delete", "block_id": "q1"}])
        writes = self.site.write_calls()
        self.assertEqual(["delete-block"], [call[1] for call in writes])
        command = writes[0]
        self.assertIn("--force", command)
        self.assertEqual("q1", command[command.index("--blockid") + 1])
        self.assertEqual(PAGE, command[command.index("--page-id") + 1])
        self.assertEqual(LANDING, command[command.index("--landing-id") + 1])
        self.assertNotIn("q1", self.page_ids())
        self.assertEqual([], self.verify(plan, refs))

    def test_delete_refuses_a_block_that_is_not_a_quests_block(self) -> None:
        plan = self.plan_for([{"op": "delete", "block_id": "q1"}])
        self.site.find("q1")["values"]["blockId"] = "other"
        plan["current_state"]["structure_sha256"] = render_plan.structure_hash(
            self.site.structure_value()
        )
        with self.assertRaisesRegex(RuntimeError, "not a Quests block"):
            apply_plan.apply_block_operations(SLUG, LANDING, plan, {})
        self.assertEqual([], self.site.write_calls())

    def test_landing_level_leftover_is_a_warning_not_a_failure(self) -> None:
        plan, refs = self.apply([{"op": "delete", "block_id": "q1"}])
        self.assertIn("q1", self.site.landing_blocks)  # observed CLI behaviour
        self.assertEqual([], self.verify(plan, refs))
        self.assertEqual(
            ["q1"], verify_structure.landing_leftovers(plan, self.site.structure_value())
        )
        self.site.landing_blocks.remove("q1")
        self.assertEqual([], verify_structure.landing_leftovers(plan, self.site.structure_value()))

    def test_move_resolves_index_from_block_id(self) -> None:
        plan = self.plan_for([{"op": "move", "block_id": "q1", "index": 3}])
        plan["block_operations"][0]["source_index"] = 99
        apply_plan.apply_block_operations(SLUG, LANDING, plan, {})
        moves = [call for call in self.site.calls if call[1] == "move-block"]
        self.assertEqual(1, len(moves))
        self.assertEqual("1", moves[0][moves[0].index("--source") + 1])
        self.assertEqual("3", moves[0][moves[0].index("--destination") + 1])
        self.assertEqual(["h1", "f1", "n1", "q1", "ft"], self.page_ids())
        self.assertEqual([], self.verify(plan))

    def test_hide_show_round_trip(self) -> None:
        plan, refs = self.apply(
            [{"op": "hide", "block_id": "q1"}, {"op": "show", "block_id": "q1"}]
        )
        sent = []
        for call in self.site.write_calls():
            self.assertEqual("update-block", call[1])
            change = next(iter(json.loads(call[call.index("--data") + 1]).values()))
            sent.append((change["id"], change["patches"]))
        self.assertEqual(
            [
                ("q1", [{"op": "replace", "path": ["hidden"], "value": True}]),
                ("q1", [{"op": "replace", "path": ["hidden"], "value": False}]),
            ],
            sent,
        )
        self.assertFalse(self.site.find("q1")["hidden"])
        self.assertEqual([], self.verify(plan, refs))

    def test_both_visibility_paths_share_set_block_hidden(self) -> None:
        with mock.patch.object(apply_plan, "set_block_hidden") as helper:
            self.apply([{"op": "hide", "block_id": "q1"}])
        helper.assert_called_once_with("q1", True, landing_id=LANDING)
        site_html = {"_id": "h", "module": "html", "hidden": False}
        page = {"_id": PAGE, "path": "/", "blocks": [site_html]}
        with (
            mock.patch.object(apply_plan, "structure", return_value={"pages": [page]}),
            mock.patch.object(apply_plan, "set_block_hidden") as helper,
        ):
            apply_plan.hide_added_custom_code("s", "landing", "/", set())
        helper.assert_called_once()
        self.assertEqual(("h", True), helper.call_args.args)

    def test_heading_uses_translation_shape(self) -> None:
        plan, refs = self.apply(
            [
                {
                    "op": "update",
                    "block_id": "q1",
                    "translations": {"en-US": {"heading": "Weekly quests"}},
                }
            ]
        )
        writes = self.site.write_calls()
        self.assertEqual(["update-many-localization"], [call[1] for call in writes])
        command = writes[0]
        self.assertEqual(SLUG, command[command.index("--slug") + 1])
        self.assertEqual(
            {
                "locale": "en-US",
                "perScopeValues": {PAGE: {HEADING_TEXT_ID: {"translation": "Weekly quests"}}},
            },
            json.loads(command[command.index("--data") + 1]),
        )
        self.assertEqual([], self.verify(plan, refs))

    def test_verify_flags_collateral_change(self) -> None:
        plan, refs = self.apply([{"op": "update", "block_id": "q1", "values": {"maxQuests": 5}}])
        self.assertEqual([], self.verify(plan, refs))
        self.site.find("f1")["values"]["title"] = "changed behind our back"
        errors = self.verify(plan, refs)
        self.assertTrue(any("f1" in error and "changed" in error for error in errors), errors)
        self.site.find("q1")["values"]["internalBlockValues"]["maxQuests"] = 9
        errors = self.verify(plan, refs)
        self.assertTrue(any("maxQuests" in error for error in errors), errors)

    def test_apply_rejects_changed_structure(self) -> None:
        plan = self.plan_for([{"op": "update", "block_id": "q1", "values": {"maxQuests": 5}}])
        self.site.find("f1")["values"]["title"] = "edited after the backup"
        with self.assertRaisesRegex(RuntimeError, "structure changed after backup"):
            apply_plan.apply_block_operations(SLUG, LANDING, plan, {})
        self.assertEqual([], self.site.write_calls())

    def test_apply_requires_the_plan_structure_fingerprint(self) -> None:
        plan = self.plan_for([{"op": "hide", "block_id": "q1"}])
        del plan["current_state"]["structure_sha256"]
        with self.assertRaisesRegex(RuntimeError, "structure_sha256"):
            apply_plan.apply_block_operations(SLUG, LANDING, plan, {})
        self.assertEqual([], self.site.write_calls())

    def test_apply_ignores_volatile_component_ids(self) -> None:
        plan = self.plan_for([{"op": "hide", "block_id": "q1"}])
        self.site.structure_value()  # a second read renumbers component ids
        apply_plan.apply_block_operations(SLUG, LANDING, plan, {})
        self.assertTrue(self.site.find("q1")["hidden"])

    def test_reset_removes_only_present_leaves(self) -> None:
        self.site.find("q1")["values"]["internalBlockValues"]["overrides"] = {
            QUEST_A: {"title": "T", "imageUrl": "https://example.com/a.png"}
        }
        plan = self.plan_for(
            [
                {
                    "op": "reset",
                    "block_id": "q1",
                    "paths": [f"overrides.{QUEST_A}.imageUrl", f"overrides.{QUEST_A}.description"],
                }
            ]
        )
        refs: dict = {}
        apply_plan.apply_block_operations(SLUG, LANDING, plan, refs)
        overrides = self.site.find("q1")["values"]["internalBlockValues"]["overrides"]
        self.assertEqual({QUEST_A: {"title": "T"}}, overrides)
        self.assertEqual(0, self.site.noop_patches)
        self.assertEqual([], self.verify(plan, refs))


class BlockAddTests(BlockOpsApplyBase):
    ADD = {
        "op": "add",
        "module": QUESTS_MODULE,
        "page": "/",
        "index": 2,
        "values": {"maxQuests": 4, "layout.cardAlign": "end"},
        "translations": {"en-US": {"heading": "Smoke quests"}},
    }

    def test_add_retargets_a_federated_wrapper_then_patches_values(self) -> None:
        plan, refs = self.apply([self.ADD])
        calls = [(call[1]) for call in self.site.write_calls()]
        self.assertEqual(
            [
                "add-block",
                "update-block",  # retarget the wrapper
                "update-block",  # devName
                "update-block",  # leaf values
                "update-many-localization",
            ],
            calls,
        )
        add = self.site.write_calls()[0]
        self.assertEqual("federated", add[add.index("--block") + 1])
        self.assertEqual("2", add[add.index("--index") + 1])
        new_id = refs["op:0"]
        self.assertEqual(new_id, self.page_ids()[2])
        values = self.site.find(new_id)["values"]
        self.assertEqual(QUESTS_MODULE, values["blockId"])
        self.assertEqual(QUESTS_VERSION, values["version"])
        self.assertIs(False, values["useAsNativeBlock"])
        self.assertTrue(values["host"].endswith(f"{QUESTS_MODULE}/{QUESTS_VERSION}/"))
        self.assertEqual(4, values["internalBlockValues"]["maxQuests"])
        self.assertEqual("end", values["internalBlockValues"]["layout"]["cardAlign"])
        self.assertEqual("Quests", self.site.find(new_id)["devName"])
        self.assertEqual(0, self.site.noop_patches)
        self.assertEqual([], self.verify(plan, refs))

    def test_add_at_index_zero_omits_index_and_corrects_position(self) -> None:
        operations = [dict(self.ADD, index=0)]
        plan, refs = self.apply(operations)
        add = self.site.write_calls()[0]
        self.assertNotIn("--index", add)
        self.assertEqual(refs["op:0"], self.page_ids()[0])
        self.assertEqual([], self.verify(plan, refs))

    def test_add_fetches_defaults_before_changing_the_site(self) -> None:
        plan = self.plan_for([self.ADD])
        with mock.patch.object(
            apply_plan, "fetch_quests_defaults", side_effect=RuntimeError("cdn down")
        ):
            with self.assertRaisesRegex(RuntimeError, "cdn down"):
                apply_plan.apply_block_operations(SLUG, LANDING, plan, {})
        self.assertEqual([], self.site.write_calls())

    def test_add_then_delete_the_new_block_leaves_the_site_as_before(self) -> None:
        before = self.site.structure_value()
        plan, refs = self.apply([self.ADD])
        new_id = refs["op:0"]
        second = self.plan_for([{"op": "delete", "block_id": new_id}])
        apply_plan.apply_block_operations(SLUG, LANDING, second, {})
        after = self.site.structure_value()
        self.assertEqual(
            [block["_id"] for block in before["pages"][0]["blocks"]],
            [block["_id"] for block in after["pages"][0]["blocks"]],
        )


class AddFailureRecoveryTests(BlockOpsApplyBase):
    def new_ids(self) -> list[str]:
        return [i for i in self.page_ids() if i.startswith("new-")]

    def test_failed_retarget_reports_the_bare_wrapper_and_points_to_the_editor(self) -> None:
        plan = self.plan_for([BlockAddTests.ADD])
        self.site.fail_update = True
        with self.assertRaises(RuntimeError) as caught:
            apply_plan.apply_block_operations(SLUG, LANDING, plan, {})
        message = str(caught.exception)
        (leftover,) = self.new_ids()
        self.assertIn(leftover, message)
        self.assertIn("editor", message)
        self.assertNotIn("delete op", message)
        self.assertEqual("", self.site.find(leftover)["values"]["blockId"])

    def test_two_wrappers_are_both_reported(self) -> None:
        plan = self.plan_for([BlockAddTests.ADD])
        self.site.double_add = True
        refs: dict = {}
        with self.assertRaises(RuntimeError) as caught:
            apply_plan.apply_block_operations(SLUG, LANDING, plan, refs)
        ids = self.new_ids()
        self.assertEqual(2, len(ids))
        for block_id in ids:
            self.assertIn(block_id, str(caught.exception))

    def test_unexpected_errors_in_a_run_are_wrapped_with_created_ids(self) -> None:
        plan = self.plan_for([BlockAddTests.ADD])
        with mock.patch.object(apply_plan, "patch_block", side_effect=KeyError("x")):
            with self.assertRaises(RuntimeError) as caught:
                apply_plan.run_block_operations(SLUG, LANDING, plan)
        message = str(caught.exception)
        self.assertIn("do not rerun", message)
        (leftover,) = self.new_ids()
        self.assertIn(leftover, message)

    def test_partial_failure_after_login_does_not_say_safe_to_rerun(self) -> None:
        plan = self.plan_for([{"op": "hide", "block_id": "q1"}])
        failure = RuntimeError(
            "authentication still fails after this run's one `xsolla auth login`. "
            "The failed command made no change, so it is safe to rerun."
        )
        with mock.patch.object(apply_plan, "apply_block_operations", side_effect=failure):
            with self.assertRaises(RuntimeError) as caught:
                apply_plan.run_block_operations(SLUG, LANDING, plan)
        self.assertIn("do not rerun", str(caught.exception))
        self.assertNotIn("safe to rerun", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
