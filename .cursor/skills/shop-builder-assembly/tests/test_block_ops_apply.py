"""Apply and verify Quests block operations against a fake `xsolla` CLI."""

from __future__ import annotations

import contextlib
import copy
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import render_plan  # noqa: E402
import preflight  # noqa: E402
import verify_structure  # noqa: E402
import backup_shop  # noqa: E402
import cli_environment  # noqa: E402
from block_ops import (  # noqa: E402
    OPERATIONS,
    QUESTS_CANDIDATE_VERSION,
    QUESTS_MODULE,
    QUESTS_VERSION,
)


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
        self.languages = ["en-US"]

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
            "languages": list(self.languages),
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
    def run_main_preflight(
        self, operations: list[dict], *, set_candidate_version: bool = True
    ) -> tuple[int, str, mock.Mock]:
        block = self.site.find("q1")
        if set_candidate_version:
            block["values"]["version"] = QUESTS_CANDIDATE_VERSION
        brief = ops_brief(operations)
        saved = self.site.structure_value()
        stderr = io.StringIO()
        run_json = mock.Mock()
        with tempfile.TemporaryDirectory() as directory:
            brief_path = Path(directory) / "brief.json"
            brief_path.write_text(json.dumps(brief), encoding="utf-8")
            approved_path = Path(directory) / "approved-plan.json"
            empty_plan = {}
            empty_plan["confirmation_id"] = "sha256:" + render_plan.canonical_hash(empty_plan)[:12]
            approved_path.write_text(json.dumps(empty_plan), encoding="utf-8")
            argv = [
                "apply_plan.py",
                str(brief_path),
                "--confirmation-id",
                empty_plan["confirmation_id"],
                "--approved-plan",
                str(approved_path),
                "--backup-dir",
                directory,
            ]
            def cli(*args: str) -> object:
                if args[:2] == ("config", "list"):
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
                    return {"ok": True, "data": [{"domain": SLUG, "_id": LANDING}]}
                return {"ok": True, "data": {}}
            run_json.side_effect = cli
            with (
                mock.patch.dict(apply_plan.RUN_AUTH, {"logged_in": False, "context": None}),
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(apply_plan, "run_preflight"),
                mock.patch.object(apply_plan, "website_exists", return_value=True),
                mock.patch.object(apply_plan, "verified_backup", return_value=True),
                mock.patch.object(apply_plan, "backup_structure", return_value=saved),
                mock.patch.object(apply_plan, "run_json", side_effect=run_json),
                contextlib.redirect_stderr(stderr),
            ):
                code = apply_plan.main()
        return code, stderr.getvalue(), run_json

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

    def test_candidate_custom_patch_applies_and_reads_back_normalized_leaves(self) -> None:
        block = self.site.find("q1")
        block["values"]["version"] = QUESTS_CANDIDATE_VERSION
        block["values"]["host"] = f"https://cdn.xsolla.net/site-builder-modules/{QUESTS_MODULE}/{QUESTS_CANDIDATE_VERSION}/"
        block["values"]["internalBlockValues"].update({
            "themeId": "site-builder",
            "backpackAction": "overlay",
            "futureField": {"preserve": True},
        })
        operations = [{
            "op": "update", "block_id": "q1", "values": {
                "themeId": "custom",
                "themeAppearance.custom.version": 1,
                "themeAppearance.custom.baseThemeId": "xsolla-pages",
                "themeAppearance.custom.palette.accent": "#123456",
                "themeAppearance.custom.typography.headingLineHeight": 1.239,
                "themeAppearance.custom.geometry.railInset": 0,
            },
        }]
        plan, refs = self.apply(operations)
        saved = self.site.find("q1")["values"]["internalBlockValues"]
        self.assertEqual(1, saved["themeAppearance"]["custom"]["version"])
        self.assertEqual("xsolla-pages", saved["themeAppearance"]["custom"]["baseThemeId"])
        self.assertEqual(1.24, saved["themeAppearance"]["custom"]["typography"]["headingLineHeight"])
        self.assertEqual("overlay", saved["backpackAction"])
        self.assertEqual({"preserve": True}, saved["futureField"])
        self.assertEqual([], self.verify(plan, refs))

    def test_candidate_preset_leaves_apply_and_read_back_for_both_themes(self) -> None:
        block = self.site.find("q1")
        block["values"]["version"] = QUESTS_CANDIDATE_VERSION
        block["values"]["internalBlockValues"].update({
            "themeAppearance": {
                "custom": {"version": 1, "baseThemeId": "site-builder"},
                "future-theme": {"keep": True},
            },
        })
        operations = [{
            "op": "update",
            "block_id": "q1",
            "values": {
                "themeAppearance.site-builder.cardAlign": "center",
                "themeAppearance.xsolla-pages.buttonStyle": "theme-default",
            },
        }]
        plan, refs = self.apply(operations)
        saved = self.site.find("q1")["values"]["internalBlockValues"]
        self.assertEqual(
            {"cardAlign": "center"}, saved["themeAppearance"]["site-builder"]
        )
        self.assertEqual(
            {"buttonStyle": "theme-default"}, saved["themeAppearance"]["xsolla-pages"]
        )
        self.assertEqual({"keep": True}, saved["themeAppearance"]["future-theme"])
        self.assertEqual([], self.verify(plan, refs))

    def test_candidate_custom_reset_preserves_version_unknown_fields_and_other_themes(self) -> None:
        block = self.site.find("q1")
        block["values"]["version"] = QUESTS_CANDIDATE_VERSION
        block["values"]["internalBlockValues"].update({
            "themeId": "custom",
            "backpackAction": "overlay",
            "themeAppearance": {
                "custom": {"version": 1, "baseThemeId": "site-builder", "future": {"keep": 1}, "palette": {"accent": "#112233", "futureColor": "keep"}},
                "xsolla-pages": {"cardAlign": "center"},
            },
        })
        plan, refs = self.apply([{
            "op": "reset", "block_id": "q1",
            "paths": ["themeAppearance.custom.palette.accent"],
        }])
        saved = self.site.find("q1")["values"]["internalBlockValues"]
        self.assertNotIn("accent", saved["themeAppearance"]["custom"]["palette"])
        self.assertEqual({"version": 1, "baseThemeId": "site-builder", "future": {"keep": 1}, "palette": {"futureColor": "keep"}}, saved["themeAppearance"]["custom"])
        self.assertEqual({"cardAlign": "center"}, saved["themeAppearance"]["xsolla-pages"])
        self.assertEqual("overlay", saved["backpackAction"])
        self.assertEqual([], self.verify(plan, refs))

    def test_reset_of_absent_custom_leaf_is_a_noop(self) -> None:
        block = self.site.find("q1")
        block["values"]["version"] = QUESTS_CANDIDATE_VERSION
        plan, refs = self.apply([{
            "op": "reset", "block_id": "q1",
            "paths": ["themeAppearance.custom.palette.accent"],
        }])
        self.assertEqual([], self.site.write_calls())
        self.assertEqual([], self.verify(plan, refs))

    def test_invalid_candidate_preflight_makes_zero_mutating_calls(self) -> None:
        for unsupported_version in (
            "0.2.5-qp-3256.0",
            "0.2.4-qp-3256.0",
            "0.2.3-qp-3256.0",
            "0.2.2-qp-3256.0",
            "0.2.1-qp-3256.1",
            "0.2.0-qp-3256.5",
            "0.2.0-qp-3256.4",
        ):
            with self.subTest(version=unsupported_version):
                block = self.site.find("q1")
                block["values"]["version"] = unsupported_version
                code, stderr, cli = self.run_main_preflight(
                    [{"op": "update", "block_id": "q1", "values": {"themeId": "custom"}}],
                    set_candidate_version=False,
                )
                self.assertEqual(1, code, stderr)
                self.assertIn("unsupported Quests version", stderr)
                reads = {
                    "list", "list-websites", "get-structure", "get-localization", "get-block"
                }
                mutations = [
                    call
                    for call in cli.call_args_list
                    if call.args
                    and call.args[0] == "shopbuilder"
                    and call.args[1] not in reads
                ]
                self.assertEqual([], mutations)

    def test_custom_value_and_contrast_preflight_failures_make_zero_mutating_calls(self) -> None:
        prefix = "themeAppearance.custom."
        base = {
            prefix + "version": 1,
            prefix + "baseThemeId": "site-builder",
        }
        rejected_values = [
            {
                **base,
                prefix + "palette.accent": "red",
            },
            {
                **base,
                prefix + "typography.bodyFont": {"loadedFont": "bad; font"},
            },
            {
                **base,
                prefix + "typography.headingWeight": True,
            },
            {
                **base,
                prefix + "typography.bodyLineHeight": 2.01,
            },
            {
                **base,
                prefix + "geometry.railInset": 0,
            },
            {
                **base,
                prefix + "geometry.columns": 5,
            },
            {
                **base,
                prefix + "palette.accent": "#ffffff",
                prefix + "palette.actionText": "#ffffff",
            },
            {
                **base,
                prefix + "version": 2,
                prefix + "typography.bodySize": 16,
            },
        ]
        expected_errors = [
            "six-digit hex",
            "loadedFont",
            "weight 400",
            "finite number",
            "railInset requires",
            "integer from 1 to 4",
            "contrast",
            "version must be 1",
        ]
        for index, values in enumerate(rejected_values):
            with self.subTest(index=index, values=values):
                code, stderr, cli = self.run_main_preflight(
                    [{"op": "update", "block_id": "q1", "values": values}]
                )
                self.assertEqual(1, code, stderr)
                self.assertIn(expected_errors[index], stderr)
                mutating_calls = [
                    call
                    for call in cli.call_args_list
                    if len(call.args) > 1
                    and call.args[0] == "shopbuilder"
                    and call.args[1]
                    not in {"list-websites", "get-structure", "get-localization", "get-block"}
                ]
                self.assertEqual([], mutating_calls)

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

    def test_custom_code_visibility_and_quests_visibility_keep_separate_block_scopes(self) -> None:
        plan, refs = self.apply([{"op": "hide", "block_id": "q1"}])
        self.assertTrue(self.site.find("q1")["hidden"])
        self.assertEqual([], self.verify(plan, refs))

        page = {
            "_id": PAGE,
            "path": "/",
            "blocks": [{"_id": "new-html", "module": "html", "hidden": False}],
        }
        with (
            mock.patch.object(apply_plan, "structure", return_value={"pages": [page]}),
            mock.patch.object(apply_plan, "run_json") as cli,
        ):
            self.assertEqual(["new-html"], apply_plan.hide_added_custom_code("s", LANDING, "/", set()))

        command = cli.call_args.args
        self.assertEqual(("shopbuilder", "update-block"), command[:2])
        payload = json.loads(command[command.index("--data") + 1])
        patch = payload["hideCustomCode"]["patches"][0]
        self.assertEqual({"op": "replace", "path": ["hidden"], "value": True}, patch)


TITLE_TEXT_ID = "L:00000000-0000-0000-0000-0000000000a1"


class FakeApplySubprocessBoundary:
    """Fake only the external CLI/process boundary; keep the real apply flow."""

    def __init__(self, site: FakeSite, *, default_sandbox: bool = True) -> None:
        self.site = site
        self.default_sandbox = default_sandbox
        self.calls: list[dict] = []

    def __call__(self, command: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        if command and command[0] == sys.executable:
            # Execute the actual preflight entrypoint in-process; only its CLI
            # subprocess boundary is fake, so its allowlist/context guards run.
            script = next(
                (index for index, item in enumerate(command) if Path(item).name == "preflight.py"),
                None,
            )
            if script is None:
                raise AssertionError(f"unexpected Python subprocess: {command}")
            stdout, stderr = io.StringIO(), io.StringIO()
            child_argv = [command[script], *command[script + 1 :]]
            with (
                mock.patch.object(sys, "argv", child_argv),
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                code = preflight.main()
            return subprocess.CompletedProcess(command, code, stdout.getvalue(), stderr.getvalue())
        if not command or command[0] != "xsolla":
            raise AssertionError(f"unexpected subprocess: {command}")
        argv = list(command[1:])
        environment = "dev"
        explicit_environment = False
        if "--environment" in argv:
            index = argv.index("--environment")
            environment = argv[index + 1]
            explicit_environment = True
            del argv[index : index + 2]
        argv = [arg for arg in argv if arg != "--json"]
        self.calls.append({
            "environment": environment,
            "explicit_environment": explicit_environment,
            "command": tuple(argv),
        })
        if argv == ["config", "list"]:
            config = {
                "merchant_id": 1,
                "project_id": 2,
                "sandbox": self.default_sandbox if environment == "dev" else False,
            }
            return subprocess.CompletedProcess(
                command, 0, json.dumps({"ok": True, "data": config}), ""
            )
        if argv == ["auth", "list-account"]:
            result = {"ok": True, "data": {"accounts": [{
                "context": "publisher", "active": True, "expired": False
            }]}}
        elif argv[:2] == ["shopbuilder", "list-websites"]:
            result = {"ok": True, "data": [{
                "domain": SLUG, "_id": LANDING, "merchantId": 1, "projectId": 2
            }]}
        elif argv[:2] == ["shopbuilder", "get-landing"]:
            result = {"ok": True, "data": {
                "domain": SLUG, "_id": LANDING, "merchantId": 1, "projectId": 2
            }}
        elif argv[:2] == ["shopbuilder", "list-assets"]:
            result = {"ok": True, "data": []}
        elif argv[:2] == ["shopbuilder", "list-versions"]:
            result = {"ok": True, "data": []}
        elif argv[:2] == ["catalog", "list-item-groups"]:
            result = {"ok": True, "data": {"groups": []}}
        elif argv == ["shopbuilder", "create-block", "--help"]:
            return subprocess.CompletedProcess(
                command, 0, "Usage:\n  xsolla shopbuilder create-block [flags]\n", ""
            )
        else:
            result = self.site.run_json(*argv)
            if argv[:2] == ["shopbuilder", "get-structure"]:
                data = result.get("data") if isinstance(result, dict) else None
                if isinstance(data, dict):
                    data.setdefault("layouts", [])
        return subprocess.CompletedProcess(command, 0, json.dumps(result), "")


class ApplyNamedEnvironmentIntegrationTests(unittest.TestCase):
    """Exercise apply_plan.main across a fake CLI subprocess boundary."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.project_dir = self.root / "project"
        self.project_dir.mkdir()
        self.bin = self.root / "bin"
        self.bin.mkdir()
        fake_xsolla = self.bin / "xsolla"
        fake_xsolla.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        fake_xsolla.chmod(0o755)
        self.config_path = self.home / ".xsolla.json"
        self.config = {
            "version": "1",
            "default_environment": "dev",
            "environments": {
                "dev": {"merchant_id": 1, "project_id": 2, "sandbox": True},
                "test": {"merchant_id": 1, "project_id": 2, "sandbox": False},
            },
        }
        self.config_path.write_text(json.dumps(self.config, indent=2), encoding="utf-8")
        self.config_before = self.config_path.read_bytes()
        self.site = FakeSite()
        target = self.site.find("q1")
        target["values"]["version"] = QUESTS_CANDIDATE_VERSION
        target["values"]["host"] = (
            f"https://cdn.xsolla.net/site-builder-modules/{QUESTS_MODULE}/"
            f"{QUESTS_CANDIDATE_VERSION}/"
        )
        self.brief = ops_brief(
            [{
                "op": "update",
                "block_id": "q1",
                "values": {"themeAppearance.site-builder.cardAlign": "center"},
            }]
        )
        self.brief_path = self.root / "brief.json"
        self.brief_path.write_text(json.dumps(self.brief, indent=2), encoding="utf-8")
        self.allowlist = self.root / "approved-test-projects.json"
        self.allowlist.write_text(
            json.dumps({
                "version": 1,
                "projects": [{
                    "merchant_id": 1,
                    "project_id": 2,
                    "approved_by": "test fixture",
                    "approval_reference": "test fixture",
                }],
            }),
            encoding="utf-8",
        )
        self.boundary = FakeApplySubprocessBoundary(self.site)

    def configure_default(self, *, sandbox: bool, include_named_test: bool) -> None:
        self.config["environments"]["dev"]["sandbox"] = sandbox
        if include_named_test:
            self.config["environments"]["test"] = {
                "merchant_id": 1,
                "project_id": 2,
                "sandbox": False,
            }
        else:
            self.config["environments"].pop("test", None)
        self.config_path.write_text(json.dumps(self.config, indent=2), encoding="utf-8")
        self.config_before = self.config_path.read_bytes()
        self.boundary = FakeApplySubprocessBoundary(self.site, default_sandbox=sandbox)

    def fake_subprocess(self, command: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        return self.boundary(command, **kwargs)

    def invoke(self, argv: list[str]) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with (
            contextlib.chdir(self.project_dir),
            mock.patch.dict(
                os.environ,
                {"HOME": str(self.home), "PATH": f"{self.bin}:{os.environ.get('PATH', '')}"},
            ),
            mock.patch("subprocess.run", side_effect=self.fake_subprocess),
            mock.patch.dict(apply_plan.RUN_AUTH, {"logged_in": False, "context": None}),
            mock.patch.object(sys, "argv", argv),
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            code = apply_plan.main()
        return code, stdout.getvalue(), stderr.getvalue()

    def make_real_backup_and_approved_plan(self) -> tuple[Path, Path, dict]:
        backup_dir = self.root / "backup"
        with (
            contextlib.chdir(self.project_dir),
            mock.patch.dict(
                os.environ,
                {"HOME": str(self.home), "PATH": f"{self.bin}:{os.environ.get('PATH', '')}"},
            ),
            mock.patch("subprocess.run", side_effect=self.fake_subprocess),
            mock.patch.object(backup_shop.shutil, "which", return_value=str(self.bin / "xsolla")),
            mock.patch.object(backup_shop, "RUN_AUTH", {"logged_in": False, "context": None}),
            mock.patch.object(
                sys,
                "argv",
                [
                    "backup_shop.py",
                    "--brief",
                    str(self.brief_path),
                    "--slug",
                    SLUG,
                    "--output-dir",
                    str(backup_dir),
                ],
            ),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            self.assertEqual(0, backup_shop.main())
        approved = render_plan.build_plan(self.brief, apply_plan.backup_structure(backup_dir))
        approved_path = self.root / "approved-plan.json"
        approved_path.write_text(json.dumps(approved, indent=2), encoding="utf-8")
        return backup_dir, approved_path, approved

    def test_apply_main_selects_named_test_environment_and_reads_back(self) -> None:
        backup_dir, approved_path, approved = self.make_real_backup_and_approved_plan()
        argv = [
            "apply_plan.py",
            str(self.brief_path),
            "--approved-test-projects",
            str(self.allowlist),
            "--approved-plan",
            str(approved_path),
            "--confirmation-id",
            approved["confirmation_id"],
            "--backup-dir",
            str(backup_dir),
        ]
        code, output, error = self.invoke(argv)
        self.assertEqual(0, code, error)
        report = json.loads(output)
        saved = self.site.find("q1")["values"]["internalBlockValues"]
        self.assertEqual("center", saved["themeAppearance"]["site-builder"]["cardAlign"])
        self.assertEqual("block-operations-applied", report["status"])
        self.assertEqual("test", report["context"]["cli_environment"])
        targeted = [call for call in self.boundary.calls if call["command"] != ("config", "list")]
        self.assertTrue(targeted)
        self.assertTrue(all(call["environment"] == "test" for call in targeted), targeted)
        self.assertTrue(all(
            call["explicit_environment"]
            or (call["environment"] == "dev" and call["command"] == ("config", "list"))
            for call in self.boundary.calls
        ))
        self.assertFalse(any(call["command"][:2] == ("config", "set") for call in self.boundary.calls))
        self.assertEqual(self.config_before, self.config_path.read_bytes())

    def test_active_sandbox_still_stops_without_a_matching_named_environment(self) -> None:
        self.configure_default(sandbox=True, include_named_test=False)
        approved = render_plan.build_plan(self.brief, self.site.structure_value())
        approved_path = self.root / "approved-plan.json"
        approved_path.write_text(json.dumps(approved, indent=2), encoding="utf-8")
        code, _, error = self.invoke([
            "apply_plan.py",
            str(self.brief_path),
            "--approved-test-projects",
            str(self.allowlist),
            "--approved-plan",
            str(approved_path),
            "--confirmation-id",
            approved["confirmation_id"],
        ])
        self.assertEqual(1, code)
        self.assertIn("CLI sandbox mode is on", error)
        self.assertEqual([], self.site.write_calls())
        self.assertTrue(all(
            call["command"][:2] == ("config", "list") for call in self.boundary.calls
        ))
        self.assertEqual(self.config_before, self.config_path.read_bytes())

    def test_default_sandbox_off_keeps_using_the_active_cli_context(self) -> None:
        self.configure_default(sandbox=False, include_named_test=False)
        backup_dir, approved_path, approved = self.make_real_backup_and_approved_plan()
        code, output, error = self.invoke([
            "apply_plan.py",
            str(self.brief_path),
            "--approved-test-projects",
            str(self.allowlist),
            "--approved-plan",
            str(approved_path),
            "--confirmation-id",
            approved["confirmation_id"],
            "--backup-dir",
            str(backup_dir),
        ])
        self.assertEqual(0, code, error)
        report = json.loads(output)
        self.assertIsNone(report["context"]["cli_environment"])
        targeted = [call for call in self.boundary.calls if call["command"] != ("config", "list")]
        self.assertTrue(targeted)
        self.assertTrue(all(not call["explicit_environment"] for call in targeted), targeted)
        self.assertFalse(any(call["command"][:2] == ("config", "set") for call in self.boundary.calls))
        self.assertEqual(self.config_before, self.config_path.read_bytes())

    def test_tampered_run_report_environment_is_rejected_before_site_reads_or_writes(self) -> None:
        backup_dir, approved_path, approved = self.make_real_backup_and_approved_plan()
        code, output, error = self.invoke([
            "apply_plan.py",
            str(self.brief_path),
            "--approved-test-projects",
            str(self.allowlist),
            "--approved-plan",
            str(approved_path),
            "--confirmation-id",
            approved["confirmation_id"],
            "--backup-dir",
            str(backup_dir),
        ])
        self.assertEqual(0, code, error)
        report = json.loads(output)
        self.assertEqual("test", report["context"]["cli_environment"])
        report["context"]["cli_environment"] = "staging"
        report_path = self.root / "run-report.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

        self.boundary.calls.clear()
        self.site.calls.clear()
        code, _, error = self.invoke([
            "apply_plan.py",
            str(self.brief_path),
            "--approved-test-projects",
            str(self.allowlist),
            "--approved-plan",
            str(approved_path),
            "--confirmation-id",
            approved["confirmation_id"],
            "--run-report",
            str(report_path),
        ])
        self.assertEqual(1, code)
        self.assertIn("differs from the earlier run report", error)
        self.assertEqual([], self.site.write_calls())
        self.assertFalse(any(
            call["command"][:2] == ("config", "set") for call in self.boundary.calls
        ))


class CardTextRefTests(BlockOpsApplyBase):
    """A ref the editor seeded wins over the plain field, so an update rewrites it too."""

    def seed_title_ref(self, text_id: str | None = TITLE_TEXT_ID) -> None:
        values = self.site.find("q1")["values"]
        values["internalBlockValues"]["overrides"] = {
            QUEST_A: {"title": "Old plain", "titleRef": "L:card-title"}
        }
        texts = {"enable": True, "id": text_id} if text_id else {
            "__type": "localized-value-descriptor",
            "localizedString": {"en-US": "Seeded"},
            "enable": True,
            "tag": "quest-title",
        }
        values["resources"]["localizedValues"]["L:card-title"] = {"texts": texts}
        if text_id:
            self.site.texts[text_id] = {
                "description": "quest-title",
                "translations": {locale: "Editor title" for locale in self.site.languages},
            }

    UPDATE = [{"op": "update", "block_id": "q1", "values": {f"overrides.{QUEST_A}.title": "New title"}}]

    def localization_writes(self) -> list[dict]:
        return [
            json.loads(call[call.index("--data") + 1])
            for call in self.site.write_calls()
            if call[1] == "update-many-localization"
        ]

    def test_update_with_a_ref_writes_the_ref_text_and_the_plain_field(self) -> None:
        self.site.languages = ["en-US", "de-DE"]
        self.seed_title_ref()
        plan = self.plan_for(self.UPDATE)
        self.assertEqual(
            ["block_values", "block_card_text"], [item["type"] for item in plan["block_operations"]]
        )
        self.assertTrue(any("Site Builder editor" in warning for warning in plan["warnings"]))
        plan, refs = self.apply(self.UPDATE, plan)
        overrides = self.site.find("q1")["values"]["internalBlockValues"]["overrides"]
        self.assertEqual("New title", overrides[QUEST_A]["title"])
        self.assertEqual("L:card-title", overrides[QUEST_A]["titleRef"])
        self.assertEqual(
            [
                {"locale": locale, "perScopeValues": {PAGE: {TITLE_TEXT_ID: {"translation": "New title"}}}}
                for locale in ("en-US", "de-DE")
            ],
            self.localization_writes(),
        )
        self.assertEqual(
            {"en-US": "New title", "de-DE": "New title"},
            self.site.texts[TITLE_TEXT_ID]["translations"],
        )
        self.assertEqual([], self.verify(plan, refs))

    def test_update_without_a_ref_writes_only_the_plain_field(self) -> None:
        plan, refs = self.apply(self.UPDATE)
        self.assertEqual(["block_values"], [item["type"] for item in plan["block_operations"]])
        self.assertEqual([], plan["warnings"])
        self.assertEqual([], self.localization_writes())
        overrides = self.site.find("q1")["values"]["internalBlockValues"]["overrides"]
        self.assertEqual({QUEST_A: {"title": "New title"}}, overrides)
        self.assertEqual([], self.verify(plan, refs))

    def test_a_dangling_ref_is_ignored_like_the_block_does(self) -> None:
        self.seed_title_ref()
        del self.site.find("q1")["values"]["resources"]["localizedValues"]["L:card-title"]
        plan = self.plan_for(self.UPDATE)
        self.assertEqual(["block_values"], [item["type"] for item in plan["block_operations"]])

    def test_verify_fails_when_the_ref_text_did_not_change(self) -> None:
        self.seed_title_ref()
        plan, refs = self.apply(self.UPDATE)
        self.site.texts[TITLE_TEXT_ID]["translations"]["en-US"] = "Editor title"
        errors = self.verify(plan, refs)
        self.assertTrue(
            any("titleRef" in error and "Editor title" in error for error in errors), errors
        )

    def test_a_ref_without_a_localization_id_is_rejected_before_any_write(self) -> None:
        self.seed_title_ref(text_id=None)
        with self.assertRaisesRegex(ValueError, "not saved on the site yet"):
            self.plan_for(self.UPDATE)
        self.assertEqual([], self.site.write_calls())

    def test_reset_title_also_removes_the_ref(self) -> None:
        self.seed_title_ref()
        self.site.find("q1")["values"]["internalBlockValues"]["overrides"][QUEST_A][
            "imageUrl"
        ] = "https://example.com/a.png"
        reset = [{"op": "reset", "block_id": "q1", "paths": [f"overrides.{QUEST_A}.title"]}]
        plan, refs = self.apply(reset)
        overrides = self.site.find("q1")["values"]["internalBlockValues"]["overrides"]
        self.assertEqual({QUEST_A: {"imageUrl": "https://example.com/a.png"}}, overrides)
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
    """A block-operations brief on a Publisher Account template site goes ahead.

    Such a site keeps its header in the common layout, so the Quests block's page has
    no header block of its own. Block operations never touch the header, so the
    template-header stop that guards a build does not apply to them.
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
            approved_path = Path(directory) / "approved-plan.json"
            approved_path.write_text(
                json.dumps(render_plan.build_plan(brief, saved)), encoding="utf-8"
            )
            argv = [
                "apply_plan.py",
                str(brief_path),
                "--confirmation-id",
                confirmation_id,
                "--approved-plan",
                str(approved_path),
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

    def test_render_accepts_an_ops_brief_on_a_template_site(self) -> None:
        code, stdout, stderr = self.run_render(self.site(own_header=False))
        self.assertEqual(0, code, stderr)
        self.assertEqual("block_operations", json.loads(stdout)["mode"])

    def test_apply_runs_an_ops_brief_on_a_template_site(self) -> None:
        site = self.site(own_header=False)
        code, stdout, stderr, _ = self.run_apply(site)
        self.assertEqual(0, code, stderr)
        self.assertEqual("block-operations-applied", json.loads(stdout)["status"])
        self.assertEqual(4, site.find("q1")["values"]["internalBlockValues"]["maxQuests"])
        self.assertFalse(
            any(b["module"] in ("header", "footer") for b in site.blocks),
            "block operations must not add a header or footer to a template site",
        )

    def test_apply_block_ops_never_calls_the_template_header_check(self) -> None:
        site = self.site(own_header=False)
        with mock.patch.object(
            apply_plan, "require_own_header", wraps=apply_plan.require_own_header
        ) as check:
            code, stdout, stderr, _ = self.run_apply(site)
        self.assertEqual(0, code, stderr)
        self.assertEqual("block-operations-applied", json.loads(stdout)["status"])
        check.assert_not_called()

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

    def test_ops_plans_check_no_pages_for_a_header(self) -> None:
        structure = self.site(own_header=False).structure_value()
        plan = render_plan.build_plan(ops_brief(self.OPERATIONS), self.site(True).structure_value())
        self.assertEqual([], render_plan.header_check_pages(plan, structure))


if __name__ == "__main__":
    unittest.main()
