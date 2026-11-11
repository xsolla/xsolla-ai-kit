from __future__ import annotations

import copy
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from block_test_support import block_operations_brief, capture_main, write_json  # noqa: E402

import apply_plan  # noqa: E402
import render_plan  # noqa: E402

QUESTS_MODULE = "_quest-platform_quests-block"
QUESTS_VERSION = "0.2.22"


def candidate_structure() -> dict:
    return {
        "_id": "landing-1",
        "type": "store",
        "domain": "my-test-site",
        "published": False,
        "languages": ["en-US"],
        "pages": [
            {
                "_id": "page-1",
                "path": "/",
                "blocks": [
                    {
                        "_id": "quests-1",
                        "module": "federated",
                        "hidden": False,
                        "values": {
                            "blockId": QUESTS_MODULE,
                            "version": QUESTS_VERSION,
                            "internalBlockValues": {
                                "themeId": "site-builder",
                                "backpackAction": "external",
                                "themeAppearance": {
                                    "custom": {
                                        "version": 1,
                                        "baseThemeId": "site-builder",
                                        "unknownCustomKey": "preserve-me",
                                        "palette": {"accent": "#123456"},
                                    },
                                    "future-theme": {"unknown": True},
                                },
                                "unknownBlockKey": "preserve-me",
                            },
                        },
                    },
                    {"_id": "footer-1", "module": "footer", "values": {}},
                ],
            }
        ],
    }


def operations_brief(operations: list[dict]) -> dict:
    return block_operations_brief(
        operations, merchant_id=12, project_id=34, slug="my-test-site",
    )


def alignment_brief() -> dict:
    return operations_brief([
        {"op": "update", "block_id": "quests-1",
         "values": {"themeAppearance.site-builder.cardAlign": "center"}}
    ])


def apply_fixture_update(args: tuple[str, ...], current: dict, writes: list, *, copy_values: bool) -> dict:
    request = json.loads(args[args.index("--data") + 1])
    change = next(iter(request.values()))
    block = current["pages"][0]["blocks"][0]
    if change["id"] != block["_id"]:
        raise AssertionError(f"unexpected block: {change['id']}")
    patches = change["patches"]
    writes.append(copy.deepcopy(patches))
    for patch in patches:
        node = block
        for part in patch["path"][:-1]:
            node = node.setdefault(part, {})
        if patch["op"] == "remove":
            node.pop(patch["path"][-1], None)
        else:
            node[patch["path"][-1]] = copy.deepcopy(patch["value"]) if copy_values else patch["value"]
    return {"ok": True, "data": {"patches": patches}}


class QuestsSettingsIntegrationTests(unittest.TestCase):
    def main_inputs(self, directory: str, brief: dict, approved: dict) -> tuple[Path, list[str]]:
        brief_path = Path(directory) / "brief.json"
        approved_path = Path(directory) / "approved-plan.json"
        write_json(brief_path, brief)
        write_json(approved_path, approved)
        return brief_path, [
            "apply_plan.py", str(brief_path), "--confirmation-id", approved["confirmation_id"],
            "--approved-plan", str(approved_path),
        ]

    def test_current_plan_entrypoint_builds_a_reviewable_candidate_settings_plan(self):
        current = candidate_structure()
        brief = alignment_brief()

        plan = render_plan.build_plan(brief, current)

        self.assertEqual("block_operations", plan["mode"])
        self.assertEqual("my-test-site", plan["target"]["slug"])
        self.assertEqual(
            {"quests-1": QUESTS_VERSION}, plan["target"]["quests_versions"]
        )
        self.assertTrue(plan["requires_confirmation"])
        self.assertEqual("themeAppearance.site-builder.cardAlign", plan["block_operations"][0]["patches"][0]["key"])

    def test_current_apply_entrypoint_writes_only_reviewed_leaves_and_reads_them_back(self):
        current = candidate_structure()
        brief = alignment_brief()
        plan = render_plan.build_plan(brief, current)
        writes: list[list[dict]] = []

        def fake_run_json(*args: str) -> object:
            if args[:2] == ("shopbuilder", "get-localization"):
                return {"ok": True, "data": {"common": {"texts": {}}, "pages": {}}}
            if args[:2] != ("shopbuilder", "update-block"):
                raise AssertionError(f"unexpected command: {args}")
            return apply_fixture_update(args, current, writes, copy_values=False)

        with (
            mock.patch.object(apply_plan, "structure", side_effect=lambda _slug: copy.deepcopy(current)),
            mock.patch.object(apply_plan, "run_json", side_effect=fake_run_json),
        ):
            applied, _ = apply_plan.run_block_operations("my-test-site", "landing-1", plan)

        self.assertEqual(1, len(applied))
        self.assertEqual(2, len(writes))  # missing parents are created before leaf patches
        internal = current["pages"][0]["blocks"][0]["values"]["internalBlockValues"]
        self.assertEqual("center", internal["themeAppearance"]["site-builder"]["cardAlign"])
        self.assertEqual("external", internal["backpackAction"])
        self.assertEqual("preserve-me", internal["unknownBlockKey"])
        self.assertEqual("preserve-me", internal["themeAppearance"]["custom"]["unknownCustomKey"])
        self.assertEqual({"unknown": True}, internal["themeAppearance"]["future-theme"])

    def test_invalid_or_unsupported_settings_make_zero_mutating_calls(self):
        cases = [
            ("previous candidate", "0.2.5-qp-3256.0", {"themeId": "custom"}),
            ("older candidate", "0.2.4-qp-3256.0", {"themeId": "custom"}),
            ("previous candidate", "0.2.3-qp-3256.0", {"themeId": "custom"}),
            ("previous candidate", "0.2.2-qp-3256.0", {"themeId": "custom"}),
            ("unsupported version", "0.2.1-qp-3256.1", {"themeId": "custom"}),
            ("invalid color", QUESTS_VERSION, {"themeAppearance.custom.palette.accent": "red"}),
            ("obsolete action leaf", QUESTS_VERSION, {"backpackAction": "overlay"}),
        ]
        for label, version, values in cases:
            with self.subTest(label=label):
                current = candidate_structure()
                current["pages"][0]["blocks"][0]["values"]["version"] = version
                brief = operations_brief(
                    [{"op": "update", "block_id": "quests-1", "values": values}]
                )
                cli = mock.Mock()
                with (
                    mock.patch.object(apply_plan, "run_json", cli),
                    self.assertRaises(ValueError),
                ):
                    render_plan.build_plan(brief, current)
                self.assertEqual([], cli.call_args_list)

    def test_stale_target_is_rejected_before_mutating_callback(self):
        backup = candidate_structure()
        brief = alignment_brief()
        plan = render_plan.build_plan(brief, backup)
        live = copy.deepcopy(backup)
        live["pages"][0]["blocks"][1]["hidden"] = True
        calls: list[list[dict]] = []

        with (
            mock.patch.object(apply_plan, "structure", side_effect=lambda _slug: copy.deepcopy(live)),
            mock.patch.object(apply_plan, "run_json", side_effect=lambda *args: calls.append(args)),
            self.assertRaisesRegex(RuntimeError, "changed after backup"),
        ):
            apply_plan.apply_block_operations("my-test-site", "landing-1", plan)
        self.assertEqual([], calls)

    def test_current_main_apply_plan_routes_candidate_settings_through_confirmation_and_auth(self):
        current = candidate_structure()
        brief = alignment_brief()
        approved = render_plan.build_plan(brief, current)
        writes: list[list[dict]] = []

        def cli(*args: str) -> object:
            if args[:2] == ("config", "list"):
                return {
                    "ok": True,
                    "data": {
                        "merchant_id": brief["project"]["merchant_id"],
                        "project_id": brief["project"]["project_id"],
                        "sandbox": False,
                    },
                }
            if args[:2] == ("shopbuilder", "list-websites"):
                return {"ok": True, "data": [{"domain": "my-test-site", "_id": "landing-1"}]}
            if args[:2] == ("shopbuilder", "get-structure"):
                return {"ok": True, "data": copy.deepcopy(current)}
            if args[:2] == ("shopbuilder", "get-localization"):
                return {"ok": True, "data": {"common": {"texts": {}}, "pages": {}}}
            if args[:2] == ("shopbuilder", "update-block"):
                return apply_fixture_update(args, current, writes, copy_values=True)
            raise AssertionError(f"unexpected command: {args}")

        with tempfile.TemporaryDirectory() as directory:
            _, argv = self.main_inputs(directory, brief, approved)
            argv.extend(["--backup-dir", directory])
            with (
                mock.patch.object(apply_plan, "run_preflight"),
                mock.patch.object(apply_plan, "verified_backup", return_value=True),
                mock.patch.object(apply_plan, "backup_structure", return_value=copy.deepcopy(current)),
                mock.patch.object(apply_plan, "run_json", side_effect=cli),
            ):
                code, stdout, _ = capture_main(apply_plan.main, argv)
                self.assertEqual(0, code)

        report = json.loads(stdout)
        self.assertEqual("block-operations-applied", report["status"])
        self.assertEqual(approved["confirmation_id"], report["approved_confirmation_id"])
        self.assertEqual(
            [{"op_index": 0, "type": "block_values", "block_id": "quests-1",
              "checked": ["each leaf reads back equal"],
              "keys": ["themeAppearance.site-builder.cardAlign"]}],
            report["verified"],
        )
        self.assertEqual(
            "https://publisher.xsolla.com/12/projects/34/site-builder/my-test-site/editor",
            report["editor_url"],
        )
        self.assertEqual(2, len(writes))
        internal = current["pages"][0]["blocks"][0]["values"]["internalBlockValues"]
        self.assertEqual("center", internal["themeAppearance"]["site-builder"]["cardAlign"])
        self.assertEqual("external", internal["backpackAction"])

    def test_editor_url_rejects_unverified_ids_and_bad_slugs(self):
        for merchant_id, project_id, slug in (
            ("12", 34, "my-test-site"),
            (12, 0, "my-test-site"),
            (True, 34, "my-test-site"),
            (12, 34, ""),
            (12, 34, "bad/site"),
            (12, 34, None),
        ):
            with self.subTest(merchant_id=merchant_id, project_id=project_id, slug=slug):
                with self.assertRaises(ValueError):
                    apply_plan.editor_url(merchant_id, project_id, slug)

    def test_missing_or_mismatched_approval_stops_before_preflight_and_cli_reads(self):
        current = candidate_structure()
        brief = alignment_brief()
        approved = render_plan.build_plan(brief, current)
        cli = mock.Mock()
        preflight = mock.Mock()
        with tempfile.TemporaryDirectory() as directory:
            brief_path, argv = self.main_inputs(directory, brief, approved)
            report_path = Path(directory) / "run-report.json"
            write_json(report_path, {
                "operation_succeeded": True, "approved_confirmation_id": "sha256:wrong"
            })

            with (
                mock.patch.object(sys, "argv", ["apply_plan.py", str(brief_path), "--confirmation-id", "unused"]),
                mock.patch.object(apply_plan, "run_json", cli),
                mock.patch.object(apply_plan, "run_preflight", preflight),
                contextlib.redirect_stderr(io.StringIO()),
                self.assertRaises(SystemExit),
            ):
                apply_plan.main()
            self.assertEqual([], cli.call_args_list)
            self.assertEqual([], preflight.call_args_list)

            wrong_confirmation = argv.copy()
            wrong_confirmation[wrong_confirmation.index("--confirmation-id") + 1] = "sha256:wrong"
            cases = [
                ("wrong-confirmation", wrong_confirmation),
                ("wrong-report-approval", [*argv, "--run-report", str(report_path)]),
            ]
            for label, rejected_argv in cases:
                with self.subTest(label=label):
                    with (
                        mock.patch.object(apply_plan, "run_json", cli),
                        mock.patch.object(apply_plan, "run_preflight", preflight),
                    ):
                        code, _, _ = capture_main(apply_plan.main, rejected_argv)
                        self.assertEqual(1, code)
                    self.assertEqual([], cli.call_args_list)
                    self.assertEqual([], preflight.call_args_list)

    def test_invalid_slug_is_rejected_before_any_cli_read_or_write(self):
        current = candidate_structure()
        brief = alignment_brief()
        approved = render_plan.build_plan(brief, current)
        brief["site"]["slug"] = "invalid/site"
        cli = mock.Mock()
        preflight = mock.Mock()
        with tempfile.TemporaryDirectory() as directory:
            _, argv = self.main_inputs(directory, brief, approved)
            with (
                mock.patch.object(apply_plan, "run_json", cli),
                mock.patch.object(apply_plan, "run_preflight", preflight),
            ):
                code, _, _ = capture_main(apply_plan.main, argv)
                self.assertEqual(1, code)
        self.assertEqual([], cli.call_args_list)
        self.assertEqual([], preflight.call_args_list)


if __name__ == "__main__":
    unittest.main()
