"""Apply and verify Quests block operations against a fake `xsolla` CLI."""

from __future__ import annotations

import contextlib
import copy
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import render_plan  # noqa: E402
import verify_structure  # noqa: E402
from block_ops import OPERATIONS, QUESTS_MODULE, QUESTS_VERSION  # noqa: E402


def load_apply_plan():
    spec = importlib.util.spec_from_file_location(
        "apply_plan_for_block_ops", ROOT / "scripts" / "apply_plan.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


apply_plan = load_apply_plan()

SLUG = "my-test-site"
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

    def __init__(self) -> None:
        self.blocks = [
            plain_block("h1", "header"),
            quests_block("q1"),
            plain_block("f1", "faq"),
            plain_block("n1", "newStore"),
            plain_block("ft", "footer"),
        ]
        self.landing_blocks = [block["_id"] for block in self.blocks]
        self.texts = {HEADING_TEXT_ID: {"description": "heading", "translations": {"en-US": "Quests"}}}
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
        raise AssertionError(f"no script deletes a block: {options}")

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
            "merchant_id": 1,
            "project_id": 2,
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

    def test_duplicate_to_the_end_of_the_page_verifies(self) -> None:
        # The copy's final index may equal the block count before the copy.
        plan, refs = self.apply([{"op": "duplicate", "block_id": "q1", "index": 5}])
        ids = self.page_ids()
        self.assertEqual(6, len(ids))
        self.assertTrue(ids[5].startswith("copy-"), ids)
        self.assertEqual([], self.verify(plan, refs))

    def test_duplicate_past_the_end_is_rejected_before_any_write(self) -> None:
        with self.assertRaisesRegex(ValueError, "past the end"):
            self.plan_for([{"op": "duplicate", "block_id": "q1", "index": 99}])
        self.assertEqual([], [call for call in self.site.calls if call[1] != "get-structure"])

    def test_apply_still_refuses_a_locale_the_site_lacks(self) -> None:
        # Planning rejects it first; apply keeps the live check as a backstop.
        plan = self.plan_for(
            [{"op": "update", "block_id": "q1", "translations": {"en-US": {"heading": "Hi"}}}]
        )
        plan["block_operations"][0]["translations"] = {"de-DE": {"heading": "Hallo"}}
        with self.assertRaisesRegex(RuntimeError, "locale de-DE is not enabled"):
            apply_plan.apply_block_operations(SLUG, LANDING, plan, {})
        self.assertFalse(
            [call for call in self.site.calls if call[1] == "update-many-localization"]
        )

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


class RealRunJsonGuardTests(unittest.TestCase):
    """Every op goes through the real `run_json`; only the `xsolla` binary is faked.

    `run_json` keeps the #68 guard: it refuses `--force` before starting the CLI.
    These tests prove that the guard is still there and that no op ever needs it.
    """

    def setUp(self) -> None:
        self.site = FakeSite()
        self.argvs: list[list[str]] = []
        patches = [
            mock.patch.object(apply_plan.subprocess, "run", side_effect=self.fake_cli),
            mock.patch.object(
                apply_plan, "fetch_quests_defaults", return_value=copy.deepcopy(CDN_DEFAULTS)
            ),
        ]
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)

    def fake_cli(self, command: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        self.argvs.append(list(command))
        self.assertEqual("xsolla", command[0])
        self.assertEqual("--json", command[-1])
        try:
            payload = self.site.run_json(*command[1:-1])
        except RuntimeError as exc:
            return subprocess.CompletedProcess(command, 1, "", str(exc))
        return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")

    def test_force_guard_refuses_before_the_cli_starts(self) -> None:
        for flag in ("--force", "--force=true"):
            with self.assertRaisesRegex(RuntimeError, "--force is prohibited"):
                apply_plan.run_json(
                    "shopbuilder", "delete-block", "--landing-id", LANDING,
                    "--page-id", PAGE, "--blockid", "q1", flag,
                )
        self.assertEqual([], self.argvs)

    def test_every_op_applies_and_verifies_without_force(self) -> None:
        operations = [
            dict(BlockAddTests.ADD),
            {
                "op": "update",
                "block_id": "q1",
                "values": {"maxQuests": 4, f"overrides.{QUEST_A}.title": "Daily quest"},
                "translations": {"en-US": {"heading": "Daily quests"}},
            },
            {"op": "reset", "block_id": "q1", "paths": ["questIds"]},
            {"op": "move", "block_id": "q1", "index": 3},
            {"op": "duplicate", "block_id": "q1", "index": 4},
            {"op": "hide", "block_id": "q1"},
            {"op": "show", "block_id": "q1"},
        ]
        # Every op the brief accepts is exercised here.
        self.assertEqual(set(OPERATIONS), {operation["op"] for operation in operations})
        plan = render_plan.build_plan(ops_brief(operations), self.site.structure_value())
        refs: dict = {}
        applied, _ = apply_plan.run_block_operations(SLUG, LANDING, plan, refs)
        self.assertEqual(len(plan["block_operations"]), len(applied))
        commands = {argv[2] for argv in self.argvs}
        self.assertTrue(
            {"add-block", "update-block", "move-block", "duplicate-block",
             "update-many-localization"} <= commands,
            commands,
        )
        self.assertNotIn("delete-block", commands)
        for argv in self.argvs:
            self.assertFalse(
                any(arg == "--force" or arg.startswith("--force=") for arg in argv), argv
            )
        self.assertFalse(self.site.find("q1")["hidden"])


NO_OWN_HEADER = (
    "Page / has no header block of its own. Sites created from a Publisher Account "
    "template keep the header in the common layout, and assembly can't build on them "
    "yet. Nothing was written."
)


class PublisherTemplateSiteTests(unittest.TestCase):
    """A block-operations brief on a Publisher Account template site stops like a build.

    Such a site keeps its header in the common layout, so the Quests block's page has
    no header block of its own. Render refuses the plan, and apply stops after the
    backup and confirmation checks, before its first write.
    """

    OPERATIONS = [{"op": "update", "block_id": "q1", "values": {"maxQuests": 4}}]

    def site(self, own_header: bool) -> FakeSite:
        site = FakeSite()
        if not own_header:
            site.blocks = [b for b in site.blocks if b["module"] not in ("header", "footer")]
            site.landing_blocks = [b["_id"] for b in site.blocks] + ["layout-header"]
        return site

    def run_render(self, site: FakeSite) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with tempfile.TemporaryDirectory() as directory:
            brief_path = Path(directory) / "brief.json"
            brief_path.write_text(json.dumps(ops_brief(self.OPERATIONS)), encoding="utf-8")
            structure_path = Path(directory) / "structure.json"
            structure_path.write_text(
                json.dumps({"ok": True, "data": site.structure_value()}), encoding="utf-8"
            )
            argv = ["render_plan.py", str(brief_path), "--structure", str(structure_path)]
            with (
                mock.patch.object(sys, "argv", argv),
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                code = render_plan.main()
        return code, stdout.getvalue(), stderr.getvalue()

    def run_apply(self, site: FakeSite) -> tuple[int, str, str, mock.Mock]:
        brief = ops_brief(self.OPERATIONS)
        saved = site.structure_value()
        confirmation_id = render_plan.build_plan(brief, saved)["confirmation_id"]

        def cli(*args: str) -> object:
            if args[:2] == ("config", "list"):
                site.calls.append(args)
                project = brief["project"]
                return {
                    "ok": True,
                    "data": {
                        "merchant_id": project["merchant_id"],
                        "project_id": project["project_id"],
                        "sandbox": False,
                    },
                }
            if args[:2] == ("shopbuilder", "list-websites"):
                site.calls.append(args)
                return {"ok": True, "data": [{"domain": SLUG, "_id": LANDING}]}
            return site.run_json(*args)

        stdout, stderr = io.StringIO(), io.StringIO()
        with tempfile.TemporaryDirectory() as directory:
            brief_path = Path(directory) / "brief.json"
            brief_path.write_text(json.dumps(brief), encoding="utf-8")
            argv = [
                "apply_plan.py",
                str(brief_path),
                "--confirmation-id",
                confirmation_id,
                "--backup-dir",
                directory,
            ]
            with (
                mock.patch.dict(apply_plan.RUN_AUTH, {"logged_in": False, "context": None}),
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(apply_plan, "run_preflight"),
                mock.patch.object(apply_plan, "run_json", side_effect=cli),
                mock.patch.object(apply_plan, "verified_backup", return_value=True),
                mock.patch.object(apply_plan, "backup_structure", return_value=saved),
                mock.patch.object(
                    apply_plan, "fetch_quests_defaults", return_value=copy.deepcopy(CDN_DEFAULTS)
                ) as defaults,
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                code = apply_plan.main()
        return code, stdout.getvalue(), stderr.getvalue(), defaults

    def writes(self, site: FakeSite) -> list[tuple[str, ...]]:
        reads = {"list", "list-websites", "get-structure", "get-localization", "get-block"}
        return [call for call in site.calls if call[1] not in reads]

    def test_render_refuses_an_ops_brief_on_a_template_site(self) -> None:
        code, stdout, stderr = self.run_render(self.site(own_header=False))
        self.assertEqual(1, code)
        self.assertEqual("", stdout)
        self.assertEqual(NO_OWN_HEADER + "\n", stderr)

    def test_apply_stops_an_ops_brief_on_a_template_site_before_any_write(self) -> None:
        site = self.site(own_header=False)
        before = copy.deepcopy(site.blocks)
        code, stdout, stderr, defaults = self.run_apply(site)
        self.assertEqual(1, code)
        self.assertEqual("", stdout)
        self.assertEqual(f"Apply failed: {NO_OWN_HEADER}\n", stderr)
        self.assertIn(("shopbuilder", "get-structure", "--slug", SLUG), site.calls)
        self.assertEqual([], self.writes(site))
        self.assertEqual(before, site.blocks)
        defaults.assert_not_called()

    def test_ops_brief_on_a_page_with_its_own_header_renders_and_applies(self) -> None:
        site = self.site(own_header=True)
        code, stdout, stderr = self.run_render(site)
        self.assertEqual(0, code, stderr)
        self.assertEqual("block_operations", json.loads(stdout)["mode"])
        code, stdout, stderr, _ = self.run_apply(site)
        self.assertEqual(0, code, stderr)
        result = json.loads(stdout)
        self.assertEqual("block-operations-applied", result["status"])
        self.assertEqual(
            f"https://publisher.xsolla.com/1/projects/2/site-builder/{SLUG}/editor",
            result["editor_url"],
        )
        self.assertEqual(4, site.find("q1")["values"]["internalBlockValues"]["maxQuests"])

    def test_only_pages_the_ops_touch_are_checked(self) -> None:
        site = self.site(own_header=False)
        structure = site.structure_value()
        structure["pages"].append(
            {"_id": "page-2", "name": "Other", "path": "/other", "blocks": []}
        )
        plan = render_plan.build_plan(ops_brief(self.OPERATIONS), self.site(True).structure_value())
        self.assertEqual(
            [{"path": "/"}], render_plan.header_check_pages(plan, structure)
        )


if __name__ == "__main__":
    unittest.main()
