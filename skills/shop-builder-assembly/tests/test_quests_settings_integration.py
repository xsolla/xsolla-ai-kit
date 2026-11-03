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

import apply_plan  # noqa: E402
import render_plan  # noqa: E402

QUESTS_MODULE = "_quest-platform_quests-block"
QUESTS_VERSION = "0.2.7-qp-3256.0"


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
    return {
        "version": 1,
        "project": {
            "merchant_id": 12,
            "project_id": 34,
            "environment": "test",
        },
        "site": {"slug": "my-test-site"},
        "block_operations": operations,
    }


class QuestsSettingsIntegrationTests(unittest.TestCase):
    def test_current_plan_entrypoint_builds_a_reviewable_candidate_settings_plan(self):
        current = candidate_structure()
        brief = operations_brief(
            [
                {
                    "op": "update",
                    "block_id": "quests-1",
                    "values": {
                        "themeAppearance.site-builder.cardAlign": "center",
                    },
                }
            ]
        )

        plan = render_plan.build_plan(brief, current)

        self.assertEqual("block_operations", plan["mode"])
        self.assertEqual("my-test-site", plan["target"]["slug"])
        self.assertEqual(
            {"quests-1": "0.2.7-qp-3256.0"}, plan["target"]["quests_versions"]
        )
        self.assertTrue(
            any(
                "candidate build" in warning
                and "0.2.7-qp-3256.0" in warning
                for warning in plan["warnings"]
            ),
            plan["warnings"],
        )
        self.assertTrue(plan["requires_confirmation"])
        self.assertEqual("themeAppearance.site-builder.cardAlign", plan["block_operations"][0]["patches"][0]["key"])

    def test_current_apply_entrypoint_writes_only_reviewed_leaves_and_reads_them_back(self):
        current = candidate_structure()
        brief = operations_brief(
            [
                {
                    "op": "update",
                    "block_id": "quests-1",
                    "values": {
                        "themeAppearance.site-builder.cardAlign": "center",
                    },
                }
            ]
        )
        plan = render_plan.build_plan(brief, current)
        writes: list[list[dict]] = []

        def fake_run_json(*args: str) -> object:
            if args[:2] == ("shopbuilder", "get-localization"):
                return {"ok": True, "data": {"common": {"texts": {}}, "pages": {}}}
            if args[:2] != ("shopbuilder", "update-block"):
                raise AssertionError(f"unexpected command: {args}")
            request = json.loads(args[args.index("--data") + 1])
            patches = next(iter(request.values()))["patches"]
            writes.append(copy.deepcopy(patches))
            internal = current["pages"][0]["blocks"][0]["values"]["internalBlockValues"]
            for patch in patches:
                node = current["pages"][0]["blocks"][0]
                for part in patch["path"][:-1]:
                    node = node.setdefault(part, {})
                if patch["op"] == "remove":
                    node.pop(patch["path"][-1], None)
                else:
                    node[patch["path"][-1]] = patch["value"]
            return {"ok": True, "data": {"patches": patches}}

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
        brief = operations_brief(
            [{"op": "update", "block_id": "quests-1", "values": {"themeAppearance.site-builder.cardAlign": "center"}}]
        )
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
        brief = operations_brief(
            [
                {
                    "op": "update",
                    "block_id": "quests-1",
                    "values": {
                        "themeAppearance.site-builder.cardAlign": "center",
                    },
                }
            ]
        )
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
                envelope = json.loads(args[args.index("--data") + 1])
                change = next(iter(envelope.values()))
                block_id = change["id"]
                block = current["pages"][0]["blocks"][0]
                self.assertEqual(block_id, block["_id"])
                patches = change["patches"]
                writes.append(copy.deepcopy(patches))
                for patch in patches:
                    node = block
                    for segment in patch["path"][:-1]:
                        node = node.setdefault(segment, {})
                    if patch["op"] == "remove":
                        node.pop(patch["path"][-1], None)
                    else:
                        node[patch["path"][-1]] = copy.deepcopy(patch["value"])
                return {"ok": True, "data": {"patches": patches}}
            raise AssertionError(f"unexpected command: {args}")

        stdout = io.StringIO()
        with tempfile.TemporaryDirectory() as directory:
            brief_path = Path(directory) / "brief.json"
            brief_path.write_text(json.dumps(brief), encoding="utf-8")
            approved_path = Path(directory) / "approved-plan.json"
            approved_path.write_text(json.dumps(approved), encoding="utf-8")
            argv = [
                "apply_plan.py",
                str(brief_path),
                "--confirmation-id",
                approved["confirmation_id"],
                "--approved-plan",
                str(approved_path),
                "--backup-dir",
                directory,
            ]
            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(apply_plan, "run_preflight"),
                mock.patch.object(apply_plan, "verified_backup", return_value=True),
                mock.patch.object(apply_plan, "backup_structure", return_value=copy.deepcopy(current)),
                mock.patch.object(apply_plan, "run_json", side_effect=cli),
                contextlib.redirect_stdout(stdout),
            ):
                self.assertEqual(0, apply_plan.main())

        report = json.loads(stdout.getvalue())
        self.assertEqual("block-operations-applied", report["status"])
        self.assertEqual(approved["confirmation_id"], report["approved_confirmation_id"])
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
        brief = operations_brief(
            [{"op": "update", "block_id": "quests-1", "values": {"themeAppearance.site-builder.cardAlign": "center"}}]
        )
        approved = render_plan.build_plan(brief, current)
        cli = mock.Mock()
        preflight = mock.Mock()
        with tempfile.TemporaryDirectory() as directory:
            brief_path = Path(directory) / "brief.json"
            brief_path.write_text(json.dumps(brief), encoding="utf-8")
            approved_path = Path(directory) / "approved-plan.json"
            approved_path.write_text(json.dumps(approved), encoding="utf-8")
            report_path = Path(directory) / "run-report.json"
            report_path.write_text(
                json.dumps(
                    {"operation_succeeded": True, "approved_confirmation_id": "sha256:wrong"}
                ),
                encoding="utf-8",
            )

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

            for tail in (
                ["--confirmation-id", "sha256:wrong", "--approved-plan", str(approved_path)],
                [
                    "--confirmation-id",
                    approved["confirmation_id"],
                    "--approved-plan",
                    str(approved_path),
                    "--run-report",
                    str(report_path),
                ],
            ):
                argv = ["apply_plan.py", str(brief_path), *tail]
                stderr = io.StringIO()
                with (
                    mock.patch.object(sys, "argv", argv),
                    mock.patch.object(apply_plan, "run_json", cli),
                    mock.patch.object(apply_plan, "run_preflight", preflight),
                    contextlib.redirect_stderr(stderr),
                ):
                    self.assertEqual(1, apply_plan.main())
                self.assertEqual([], cli.call_args_list)
                self.assertEqual([], preflight.call_args_list)

    def test_invalid_slug_is_rejected_before_any_cli_read_or_write(self):
        current = candidate_structure()
        brief = operations_brief(
            [{"op": "update", "block_id": "quests-1", "values": {"themeAppearance.site-builder.cardAlign": "center"}}]
        )
        approved = render_plan.build_plan(brief, current)
        brief["site"]["slug"] = "invalid/site"
        cli = mock.Mock()
        preflight = mock.Mock()
        with tempfile.TemporaryDirectory() as directory:
            brief_path = Path(directory) / "brief.json"
            brief_path.write_text(json.dumps(brief), encoding="utf-8")
            approved_path = Path(directory) / "approved-plan.json"
            approved_path.write_text(json.dumps(approved), encoding="utf-8")
            argv = [
                "apply_plan.py",
                str(brief_path),
                "--confirmation-id",
                approved["confirmation_id"],
                "--approved-plan",
                str(approved_path),
            ]
            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(apply_plan, "run_json", cli),
                mock.patch.object(apply_plan, "run_preflight", preflight),
                contextlib.redirect_stderr(io.StringIO()),
            ):
                self.assertEqual(1, apply_plan.main())
        self.assertEqual([], cli.call_args_list)
        self.assertEqual([], preflight.call_args_list)


if __name__ == "__main__":
    unittest.main()
