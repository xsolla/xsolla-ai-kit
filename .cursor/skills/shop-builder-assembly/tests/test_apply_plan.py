from __future__ import annotations

import contextlib
import copy
import hashlib
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


def load_apply_plan():
    path = ROOT / "scripts" / "apply_plan.py"
    spec = importlib.util.spec_from_file_location("apply_plan_for_tests", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


apply_plan = load_apply_plan()


def load_verify_structure():
    path = ROOT / "scripts" / "verify_structure.py"
    spec = importlib.util.spec_from_file_location("verify_structure_for_tests", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


verify_structure = load_verify_structure()

APPROVED_CONTEXT = {"merchant_id": 100, "project_id": 200, "sandbox": False}


def fresh_run_auth(logged_in: bool = False) -> dict:
    return {"logged_in": logged_in, "context": dict(APPROVED_CONTEXT)}


def config_result(**overrides: object) -> mock.Mock:
    config = {"merchant_id": 100, "project_id": 200, **overrides}
    return mock.Mock(
        returncode=0, stderr="", stdout=json.dumps({"ok": True, "data": config})
    )


class ApplyPlanTests(unittest.TestCase):
    def test_backup_structure_unwraps_cli_envelope(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            expected = {"_id": "landing", "pages": []}
            (root / "structure.json").write_text(
                json.dumps({"ok": True, "data": expected}), encoding="utf-8"
            )
            self.assertEqual(expected, apply_plan.backup_structure(root))

    def test_structure_hash_ignores_volatile_component_ids(self) -> None:
        first = {
            "pages": [
                {
                    "_id": "page-id",
                    "blocks": [
                        {
                            "_id": "block-id",
                            "values": {
                                "components": [
                                    {"_id": "generated-one", "external_id": "group-1"}
                                ]
                            },
                        }
                    ],
                }
            ]
        }
        second = copy.deepcopy(first)
        second["pages"][0]["blocks"][0]["values"]["components"][0]["_id"] = (
            "generated-two"
        )
        self.assertEqual(
            apply_plan.structure_hash(first), apply_plan.structure_hash(second)
        )

    def test_structure_hash_keeps_page_block_and_component_values(self) -> None:
        original = {
            "pages": [
                {
                    "_id": "page-id",
                    "blocks": [
                        {
                            "_id": "block-id",
                            "values": {
                                "components": [
                                    {"_id": "generated", "external_id": "group-1"}
                                ]
                            },
                        }
                    ],
                }
            ]
        }
        for path, replacement in (
            (("pages", 0, "_id"), "other-page"),
            (("pages", 0, "blocks", 0, "_id"), "other-block"),
            (
                (
                    "pages",
                    0,
                    "blocks",
                    0,
                    "values",
                    "components",
                    0,
                    "external_id",
                ),
                "group-2",
            ),
        ):
            changed = copy.deepcopy(original)
            target = changed
            for segment in path[:-1]:
                target = target[segment]
            target[path[-1]] = replacement
            self.assertNotEqual(
                apply_plan.structure_hash(original), apply_plan.structure_hash(changed)
            )

    def test_website_exists_handles_wrapped_lists(self) -> None:
        response = {
            "ok": True,
            "data": {"items": [{"domain": "one-shop"}, {"slug": "two-shop"}]},
        }
        self.assertTrue(apply_plan.website_exists(response, "two-shop"))
        self.assertFalse(apply_plan.website_exists(response, "missing-shop"))

    def test_page_for_path_finds_only_exact_path(self) -> None:
        structure = {"pages": [{"path": "/", "_id": "home"}]}
        self.assertEqual("home", apply_plan.page_for_path(structure, "/")["_id"])
        self.assertIsNone(apply_plan.page_for_path(structure, "/store"))

    def test_verified_backup_requires_identity_and_matching_checksums(self) -> None:
        expected = {
            "merchant_id": 100,
            "project_id": 200,
            "environment": "test",
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in apply_plan.BACKUP_FILE_NAMES:
                (root / name).write_bytes(b"{}\n")
            structure = root / "structure.json"
            manifest = {
                "slug": "test-shop",
                **expected,
                "read_only": True,
                "files": sorted(apply_plan.BACKUP_FILE_NAMES),
                "sha256": {
                    name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                    for name in apply_plan.BACKUP_FILE_NAMES
                },
            }
            (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            self.assertTrue(apply_plan.verified_backup(root, expected, "test-shop"))
            structure.write_bytes(b"changed\n")
            self.assertFalse(apply_plan.verified_backup(root, expected, "test-shop"))

    def test_verified_backup_rejects_partial_digest_manifest(self) -> None:
        expected = {"merchant_id": 100, "project_id": 200, "environment": "test"}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("structure.json", "landing.json"):
                (root / name).write_bytes(b"{}\n")
            manifest = {
                "slug": "test-shop",
                **expected,
                "read_only": True,
                "files": sorted(apply_plan.BACKUP_FILE_NAMES),
                "sha256": {
                    "structure.json": hashlib.sha256(
                        (root / "structure.json").read_bytes()
                    ).hexdigest()
                },
            }
            (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            self.assertFalse(apply_plan.verified_backup(root, expected, "test-shop"))

    def test_real_cli_shape_keeps_full_blocks_on_pages(self) -> None:
        structure = {
            "_id": "landing",
            "blocks": ["site-block-id"],
            "pages": [
                {
                    "_id": "home",
                    "path": "/",
                    "blocks": [{"_id": "block-1", "module": "header"}],
                }
            ],
        }
        page = apply_plan.page_for_path(structure, "/")
        self.assertEqual("header", page["blocks"][0]["module"])

    def test_reconciliation_refuses_unconfirmed_removal_before_write(self) -> None:
        current = {
            "_id": "landing",
            "pages": [
                {
                    "_id": "home",
                    "path": "/",
                    "blocks": [
                        {"_id": "header-id", "module": "header"},
                        {"_id": "custom-id", "module": "gallery"},
                    ],
                }
            ],
        }
        plan = {
            "name": "Home",
            "path": "/",
            "blocks": ["header"],
            "removals": [],
        }
        with (
            mock.patch.object(apply_plan, "structure", return_value=current),
            mock.patch.object(apply_plan, "run_json") as run_json,
        ):
            with self.assertRaisesRegex(RuntimeError, "unconfirmed block removals"):
                apply_plan.reconcile_page("shop", "landing", plan)
            run_json.assert_not_called()

    def test_reconciliation_returns_immediately_for_exact_page(self) -> None:
        current = {
            "pages": [
                {
                    "_id": "home",
                    "path": "/",
                    "blocks": [
                        {"_id": "header", "module": "header"},
                        {"_id": "footer", "module": "footer"},
                    ],
                }
            ]
        }
        plan = {
            "name": "Home",
            "path": "/",
            "blocks": ["header", "footer"],
            "removals": [],
        }
        with (
            mock.patch.object(apply_plan, "structure", return_value=current) as structure,
            mock.patch.object(apply_plan, "run_json") as run_json,
        ):
            result = apply_plan.reconcile_page("shop", "landing", plan)
        structure.assert_called_once_with("shop")
        run_json.assert_not_called()
        self.assertEqual(["header", "footer"], result["blocks"])

    def test_reconciliation_batches_confirmed_removals_in_descending_order(self) -> None:
        current = {
            "_id": "landing",
            "pages": [
                {
                    "_id": "home",
                    "path": "/",
                    "blocks": [
                        {"_id": "header", "module": "header"},
                        {"_id": "remove-one", "module": "packs"},
                        {"_id": "remove-two", "module": "gallery"},
                        {"_id": "footer", "module": "footer"},
                    ],
                }
            ],
        }
        final = {
            "_id": "landing",
            "pages": [
                {
                    "_id": "home",
                    "path": "/",
                    "blocks": [
                        {"_id": "header", "module": "header"},
                        {"_id": "footer", "module": "footer"},
                    ],
                }
            ],
        }
        plan = {
            "name": "Home",
            "path": "/",
            "blocks": ["header", "footer"],
            "removals": [
                {"block_id": "remove-one", "module": "packs"},
                {"block_id": "remove-two", "module": "gallery"},
            ],
        }
        with (
            mock.patch.object(
                apply_plan,
                "structure",
                side_effect=[current, final, final, final, final],
            ),
            mock.patch.object(apply_plan, "run_json") as run_json,
        ):
            result = apply_plan.reconcile_page("shop", "landing", plan)
        run_json.assert_called_once()
        args = run_json.call_args.args
        self.assertEqual("update-block", args[1])
        payload = json.loads(args[-1])
        self.assertEqual(
            [
                {"op": "remove", "path": ["blocks", 2]},
                {"op": "remove", "path": ["blocks", 1]},
            ],
            payload["removeBlocks"]["patches"],
        )
        self.assertEqual(2, result["removed_blocks"])

    def test_reconciliation_preserves_federated_effective_module(self) -> None:
        current = {
            "_id": "landing",
            "pages": [
                {
                    "_id": "home",
                    "path": "/",
                    "blocks": [
                        {
                            "_id": "offer-chain",
                            "module": "federated",
                            "values": {"blockId": "sb-offer-chain"},
                        }
                    ],
                }
            ],
        }
        plan = {
            "name": "Home",
            "path": "/",
            "blocks": ["sb-offer-chain"],
            "removals": [],
        }
        with (
            mock.patch.object(apply_plan, "structure", return_value=current),
            mock.patch.object(apply_plan, "run_json") as run_json,
        ):
            result = apply_plan.reconcile_page("shop", "landing", plan)
        run_json.assert_not_called()
        self.assertEqual(["sb-offer-chain"], result["blocks"])

    def test_run_preflight_propagates_failure(self) -> None:
        failed = mock.Mock(
            returncode=1, stderr="Preflight failed: wrong project", stdout=""
        )
        with mock.patch.object(apply_plan.subprocess, "run", return_value=failed):
            with self.assertRaisesRegex(RuntimeError, "wrong project"):
                apply_plan.run_preflight(Path("brief.json"), None)

    def test_run_json_refuses_force_before_login_or_write(self) -> None:
        with mock.patch.object(apply_plan.subprocess, "run") as run:
            with self.assertRaisesRegex(RuntimeError, "--force is prohibited"):
                apply_plan.run_json("shopbuilder", "delete-block", "--force")
            run.assert_not_called()

    def test_run_json_retries_pre_request_session_bootstrap_rate_limit(self) -> None:
        limited = mock.Mock(
            returncode=1,
            stderr="publisher session bootstrap failed (HTTP 429)",
            stdout="",
        )
        succeeded = mock.Mock(returncode=0, stderr="", stdout='{"ok":true}')
        with (
            mock.patch.object(
                apply_plan.subprocess, "run", side_effect=[limited, limited, succeeded]
            ) as run,
            mock.patch.object(apply_plan.time, "sleep") as sleep,
        ):
            self.assertEqual({"ok": True}, apply_plan.run_json("config", "list"))
        self.assertEqual(3, run.call_count)
        self.assertEqual([mock.call(5), mock.call(10)], sleep.call_args_list)

    def test_run_json_does_not_retry_ambiguous_operation_failure(self) -> None:
        failed = mock.Mock(returncode=1, stderr="request failed (HTTP 429)", stdout="")
        with (
            mock.patch.dict(apply_plan.RUN_AUTH, fresh_run_auth()),
            mock.patch.object(apply_plan.subprocess, "run", side_effect=[failed]) as run,
            mock.patch.object(apply_plan.time, "sleep") as sleep,
        ):
            with self.assertRaisesRegex(RuntimeError, "HTTP 429"):
                apply_plan.run_json("shopbuilder", "update-block")
        run.assert_called_once()
        sleep.assert_not_called()

    def test_run_json_does_not_log_in_when_commands_succeed(self) -> None:
        succeeded = mock.Mock(returncode=0, stderr="", stdout='{"ok":true}')
        with (
            mock.patch.dict(apply_plan.RUN_AUTH, fresh_run_auth()),
            mock.patch.object(
                apply_plan.subprocess, "run", side_effect=[succeeded, succeeded]
            ) as run,
            mock.patch.object(apply_plan.time, "sleep") as sleep,
        ):
            apply_plan.run_json("shopbuilder", "list-websites")
            apply_plan.run_json("shopbuilder", "get-structure", "--slug", "shop")
            self.assertFalse(apply_plan.RUN_AUTH["logged_in"])
        self.assertEqual(
            [
                ["xsolla", "shopbuilder", "list-websites", "--json"],
                ["xsolla", "shopbuilder", "get-structure", "--slug", "shop", "--json"],
            ],
            [call.args[0] for call in run.call_args_list],
        )
        sleep.assert_not_called()

    def test_run_json_logs_in_once_and_retries_after_auth_failure(self) -> None:
        failures = {
            "missing bootstrap cookie": (
                1,
                "auto-bootstrapping publisher session from stored token: publisher "
                "session bootstrap did not yield a pa-v4-token or ps2[user_session] cookie",
            ),
            "no usable token": (1, "authentication required for this command."),
            "API 401": (10, '{"ok": false, "error": {"code": "http_401"}}'),
        }
        login_succeeded = mock.Mock(returncode=0, stderr="", stdout="Login successful")
        succeeded = mock.Mock(returncode=0, stderr="", stdout='{"ok":true}')
        for name, (returncode, stderr) in failures.items():
            failed = mock.Mock(returncode=returncode, stderr=stderr, stdout="")
            with self.subTest(name):
                with (
                    mock.patch.dict(apply_plan.RUN_AUTH, fresh_run_auth()),
                    mock.patch.object(
                        apply_plan.subprocess,
                        "run",
                        side_effect=[failed, login_succeeded, config_result(), succeeded],
                    ) as run,
                    mock.patch.object(apply_plan.time, "sleep") as sleep,
                ):
                    self.assertEqual(
                        {"ok": True}, apply_plan.run_json("shopbuilder", "get-structure")
                    )
                    self.assertTrue(apply_plan.RUN_AUTH["logged_in"])
                self.assertEqual(
                    [
                        ["xsolla", "shopbuilder", "get-structure", "--json"],
                        ["xsolla", "auth", "login"],
                        ["xsolla", "config", "list", "--json"],
                        ["xsolla", "shopbuilder", "get-structure", "--json"],
                    ],
                    [call.args[0] for call in run.call_args_list],
                )
                sleep.assert_called_once_with(apply_plan.LOGIN_SETTLE_SECONDS)

    def test_run_json_never_logs_in_twice_in_one_run(self) -> None:
        missing_cookie = mock.Mock(
            returncode=1,
            stderr="publisher session bootstrap did not yield a pa-v4-token cookie",
            stdout="",
        )
        login_succeeded = mock.Mock(returncode=0, stderr="", stdout="Login successful")
        with (
            mock.patch.dict(apply_plan.RUN_AUTH, fresh_run_auth()),
            mock.patch.object(
                apply_plan.subprocess,
                "run",
                side_effect=[missing_cookie, login_succeeded, config_result(), missing_cookie],
            ) as run,
            mock.patch.object(apply_plan.time, "sleep"),
        ):
            with self.assertRaisesRegex(
                RuntimeError, "still fails after this run's one `xsolla auth login`"
            ):
                apply_plan.run_json("shopbuilder", "get-structure")
        self.assertEqual(
            1,
            [call.args[0] for call in run.call_args_list].count(["xsolla", "auth", "login"]),
        )

        with (
            mock.patch.dict(apply_plan.RUN_AUTH, fresh_run_auth(logged_in=True)),
            mock.patch.object(
                apply_plan.subprocess, "run", side_effect=[missing_cookie]
            ) as run,
        ):
            with self.assertRaisesRegex(RuntimeError, "still fails"):
                apply_plan.run_json("shopbuilder", "list-websites")
        run.assert_called_once()

    def test_run_json_aborts_when_login_changes_cli_context(self) -> None:
        missing_cookie = mock.Mock(
            returncode=1,
            stderr="publisher session bootstrap did not yield a pa-v4-token cookie",
            stdout="",
        )
        login_succeeded = mock.Mock(returncode=0, stderr="", stdout="Login successful")
        for drift, message in (
            ({"project_id": 300}, r"\(project_id 200 -> 300\)"),
            ({"merchant_id": 101}, r"\(merchant_id 100 -> 101\)"),
            ({"sandbox": True}, r"\(sandbox False -> True\)"),
        ):
            with self.subTest(drift=drift):
                with (
                    mock.patch.dict(apply_plan.RUN_AUTH, fresh_run_auth()),
                    mock.patch.object(
                        apply_plan.subprocess,
                        "run",
                        side_effect=[missing_cookie, login_succeeded, config_result(**drift)],
                    ) as run,
                    mock.patch.object(apply_plan.time, "sleep"),
                ):
                    with self.assertRaisesRegex(
                        RuntimeError, "CLI context changed after `xsolla auth login` " + message
                    ):
                        apply_plan.run_json("shopbuilder", "update-block")
                self.assertEqual(3, run.call_count)

    def test_run_json_does_not_log_in_for_exhausted_bootstrap_rate_limit(self) -> None:
        limited = mock.Mock(
            returncode=1,
            stderr="auto-bootstrapping publisher session from stored token: "
            "publisher session bootstrap failed (HTTP 429)",
            stdout="",
        )
        with (
            mock.patch.dict(apply_plan.RUN_AUTH, fresh_run_auth()),
            mock.patch.object(
                apply_plan.subprocess, "run", side_effect=[limited] * 4
            ) as run,
            mock.patch.object(apply_plan.time, "sleep"),
        ):
            with self.assertRaisesRegex(RuntimeError, "HTTP 429"):
                apply_plan.run_json("shopbuilder", "list-websites")
        self.assertEqual(4, run.call_count)
        self.assertNotIn(
            ["xsolla", "auth", "login"], [call.args[0] for call in run.call_args_list]
        )

    def test_supported_login_times_out_after_one_retry(self) -> None:
        timeout = subprocess.TimeoutExpired(["xsolla", "auth", "login"], 45)
        with (
            mock.patch.object(
                apply_plan.subprocess, "run", side_effect=[timeout, timeout]
            ) as run,
            mock.patch.object(apply_plan.time, "sleep") as sleep,
        ):
            with self.assertRaisesRegex(RuntimeError, "timed out"):
                apply_plan.refresh_supported_login()
        self.assertEqual(2, run.call_count)
        sleep.assert_called_once_with(apply_plan.LOGIN_RETRY_DELAY_SECONDS)

    def test_ensure_locales_adds_only_missing_languages(self) -> None:
        before = {"languages": ["en-US"]}
        after = {"languages": ["en-US", "de-DE"]}
        with (
            mock.patch.object(apply_plan, "structure", side_effect=[before, after]),
            mock.patch.object(apply_plan, "run_json") as run_json,
        ):
            result = apply_plan.ensure_locales("shop", ["en-US", "de-DE"])
        run_json.assert_called_once_with(
            "shopbuilder", "add-language", "--slug", "shop", "--language", "de-DE"
        )
        self.assertEqual(["de-DE"], result["added"])

    def test_ensure_locales_is_idempotent_when_languages_exist(self) -> None:
        structure = {"languages": ["en-US", "de-DE"]}
        with (
            mock.patch.object(
                apply_plan, "structure", side_effect=[structure, structure]
            ),
            mock.patch.object(apply_plan, "run_json") as run_json,
        ):
            result = apply_plan.ensure_locales("shop", ["en-US", "de-DE"])
        run_json.assert_not_called()
        self.assertEqual([], result["added"])

    def test_ensure_locales_rejects_malformed_refreshed_languages(self) -> None:
        with (
            mock.patch.object(
                apply_plan,
                "structure",
                side_effect=[{"languages": ["en-US"]}, {"languages": ["en-US", {}]}],
            ),
            mock.patch.object(apply_plan, "run_json"),
        ):
            with self.assertRaisesRegex(RuntimeError, "locale reconciliation"):
                apply_plan.ensure_locales("shop", ["en-US", "de-DE"])

    def test_header_navigation_reuses_buttons_and_targets_pages(self) -> None:
        header = {
            "values": {
                "components": {
                    "button-a": {
                        "id": "button-a",
                        "type": "button",
                        "button": {
                            "action": {
                                "action": "scroll",
                                "targetId": "old",
                                "text": {"enable": True, "id": "L:existing"},
                            },
                            "variant": {"type": "extra", "value": "header-button"},
                        },
                    },
                    "locale": {"id": "locale", "type": "locale-select"},
                },
                "fixedComponents": [],
                "leftComponents": ["button-a"],
                "rightComponents": ["locale"],
            }
        }
        patches, labels = apply_plan.header_navigation_patches(
            header,
            "landing",
            "home",
            [
                {"name": "Home", "path": "/", "page_id": "home"},
                {"name": "Store", "path": "/store", "page_id": "store"},
            ],
        )
        action_patch = next(
            patch
            for patch in patches
            if patch["path"]
            == ["values", "components", "button-a", "button", "action"]
        )
        self.assertEqual("page", action_patch["value"]["action"])
        self.assertEqual("home", action_patch["value"]["pageId"])
        self.assertEqual("Home", labels["L:existing"])
        addition = next(
            patch
            for patch in patches
            if patch["op"] == "add" and patch["path"][:2] == ["values", "components"]
        )
        self.assertEqual("store", addition["value"]["button"]["action"]["pageId"])
        right_patch = next(
            patch for patch in patches if patch["path"] == ["values", "rightComponents"]
        )
        self.assertEqual("locale", right_patch["value"][0])
        self.assertEqual(3, len(right_patch["value"]))

    def test_navigation_component_ids_are_stable(self) -> None:
        first = apply_plan.stable_component_id("landing", "home", "/store")
        second = apply_plan.stable_component_id("landing", "home", "/store")
        self.assertEqual(first, second)

    def test_catalog_patches_are_targeted_and_remove_stale_sections(self) -> None:
        components = [
            {
                "_id": "first",
                "enable": True,
                "section": {
                    "item": {"autoSelected": True, "group": "old", "type": "bundle"},
                    "title": {"enable": True, "id": "L:old"},
                },
                "card": {"selectedLayoutType": "featured"},
            },
            {
                "_id": "stale",
                "enable": True,
                "section": {
                    "item": {"autoSelected": False, "group": "stale", "type": "bundle"},
                    "title": {"enable": True, "id": "L:stale"},
                },
                "card": {"selectedLayoutType": "featured"},
            },
        ]
        patches = apply_plan.catalog_patches(
            components,
            [
                {
                    "external_id": "__all__",
                    "type": "virtual_currency",
                    "layout": "vertical",
                    "title_enabled": False,
                }
            ],
        )
        self.assertFalse(any(patch["path"] == ["components"] for patch in patches))
        self.assertIn(
            {"op": "remove", "path": ["components", 1]},
            patches,
        )
        self.assertIn(
            {
                "op": "replace",
                "path": ["components", 0, "section", "item", "group"],
                "value": "__all__",
            },
            patches,
        )

    def test_catalog_patches_add_from_sanitized_template(self) -> None:
        components = [
            {
                "_id": "template-id",
                "enable": True,
                "section": {
                    "item": {"autoSelected": True, "group": "old", "type": "bundle"},
                    "title": {"enable": True, "id": "L:old"},
                },
                "card": {"selectedLayoutType": "featured"},
            }
        ]
        sections = [
            {"external_id": "one", "type": "bundle", "layout": "featured", "title_enabled": False},
            {"external_id": "two", "type": "virtual_good", "layout": "vertical", "title_enabled": False},
        ]
        patches = apply_plan.catalog_patches(components, sections)
        addition = next(patch for patch in patches if patch["op"] == "add")
        self.assertNotIn("_id", addition["value"])
        self.assertEqual("two", addition["value"]["section"]["item"]["group"])

    def test_wire_catalog_sections_verifies_result(self) -> None:
        before = {
            "pages": [
                {
                    "path": "/",
                    "blocks": [
                        {
                            "_id": "store",
                            "module": "newStore",
                            "components": [
                                {
                                    "enable": True,
                                    "section": {
                                        "item": {"autoSelected": True, "group": "old", "type": "bundle"},
                                        "title": {"enable": True},
                                    },
                                    "card": {"selectedLayoutType": "featured"},
                                }
                            ],
                        }
                    ],
                }
            ]
        }
        after = copy.deepcopy(before)
        component = after["pages"][0]["blocks"][0]["components"][0]
        component["section"]["item"] = {
            "autoSelected": False,
            "group": "__all__",
            "type": "virtual_currency",
        }
        component["section"]["title"]["enable"] = False
        component["card"]["selectedLayoutType"] = "vertical"
        plan = {
            "pages": [{"path": "/"}],
            "catalog_sections": [
                {
                    "external_id": "__all__",
                    "type": "virtual_currency",
                    "layout": "vertical",
                    "title_enabled": False,
                }
            ],
        }
        with (
            mock.patch.object(apply_plan, "structure", side_effect=[before, after]),
            mock.patch.object(apply_plan, "run_json") as run_json,
        ):
            result = apply_plan.wire_catalog_sections("shop", "landing", plan)
        run_json.assert_called_once()
        self.assertEqual("store", result[0]["block_id"])

    def test_empty_catalog_preserves_existing_store_configuration(self) -> None:
        with (
            mock.patch.object(apply_plan, "structure") as structure,
            mock.patch.object(apply_plan, "run_json") as run_json,
        ):
            result = apply_plan.wire_catalog_sections(
                "shop", "landing", {"catalog_sections": [], "pages": []}
            )
        self.assertEqual([], result)
        structure.assert_not_called()
        run_json.assert_not_called()

    def test_structure_verifier_accepts_matching_unpublished_site(self) -> None:
        plan = {
            "confirmation_id": "sha256:test",
            "target": {"merchant_id": 100, "project_id": 200, "slug": "shop"},
            "locales": ["en-US"],
            "catalog_sections": [],
            "pages": [
                {
                    "path": "/",
                    "blocks": ["header", "footer"],
                    "preserved_blocks": [],
                    "removals": [],
                }
            ],
        }
        structure = {
            "ok": True,
            "data": {
                "merchantId": "100",
                "projectId": "200",
                "domain": "shop",
                "type": "store",
                "published": None,
                "languages": ["en-US"],
                "pages": [
                    {
                        "path": "/",
                        "blocks": [
                            {"_id": "header", "module": "header"},
                            {"_id": "footer", "module": "footer"},
                        ],
                    }
                ],
            },
        }
        result = verify_structure.verify(plan, structure)
        self.assertTrue(result["ok"])
        self.assertFalse(result["published"])

    def test_structure_verifier_checks_catalog_sections(self) -> None:
        plan = {
            "target": {"merchant_id": 100, "project_id": 200, "slug": "shop"},
            "locales": ["en-US"],
            "catalog_sections": [
                {
                    "external_id": "__all__",
                    "type": "virtual_currency",
                    "layout": "vertical",
                }
            ],
            "pages": [{"path": "/", "blocks": ["newStore"]}],
        }
        structure = {
            "merchantId": 100,
            "projectId": 200,
            "domain": "shop",
            "type": "store",
            "published": None,
            "languages": ["en-US"],
            "pages": [
                {
                    "path": "/",
                    "blocks": [
                        {
                            "_id": "store",
                            "module": "newStore",
                            "components": [
                                {
                                    "enable": True,
                                    "section": {"item": {"group": "wrong", "type": "bundle"}},
                                    "card": {"selectedLayoutType": "featured"},
                                }
                            ],
                        }
                    ],
                }
            ],
        }
        result = verify_structure.verify(plan, structure)
        self.assertFalse(result["ok"])
        self.assertTrue(any("catalog sections differ" in error for error in result["errors"]))

    def test_structure_verifier_checks_internal_navigation(self) -> None:
        plan = {
            "target": {"merchant_id": 100, "project_id": 200, "slug": "shop"},
            "locales": ["en-US"],
            "catalog_sections": [],
            "navigation": [{"name": "Home", "path": "/", "page_id": "home"}],
            "pages": [{"path": "/", "blocks": ["header"]}],
        }
        structure = {
            "merchantId": 100,
            "projectId": 200,
            "domain": "shop",
            "type": "store",
            "published": None,
            "languages": ["en-US"],
            "pages": [
                {
                    "_id": "home",
                    "path": "/",
                    "blocks": [
                        {
                            "_id": "header",
                            "module": "header",
                            "values": {
                                "rightComponents": ["home-link"],
                                "components": {
                                    "home-link": {
                                        "type": "button",
                                        "button": {
                                            "action": {"action": "page", "pageId": "wrong"}
                                        },
                                    }
                                },
                            },
                        }
                    ],
                }
            ],
        }
        result = verify_structure.verify(plan, structure)
        self.assertFalse(result["ok"])
        self.assertTrue(any("navigation differs" in error for error in result["errors"]))

    def test_structure_verifier_reports_order_and_publication(self) -> None:
        plan = {
            "target": {"merchant_id": 100, "project_id": 200, "slug": "shop"},
            "locales": ["en-US"],
            "pages": [{"path": "/", "blocks": ["header", "footer"]}],
        }
        structure = {
            "merchantId": 100,
            "projectId": 200,
            "domain": "shop",
            "type": "store",
            "published": 1,
            "languages": ["en-US"],
            "pages": [
                {
                    "path": "/",
                    "blocks": [
                        {"_id": "footer", "module": "footer"},
                        {"_id": "header", "module": "header"},
                    ],
                }
            ],
        }
        result = verify_structure.verify(plan, structure)
        self.assertFalse(result["ok"])
        self.assertTrue(result["published"])
        self.assertTrue(
            any("block order differs" in error for error in result["errors"])
        )

    def test_structure_verifier_resolves_federated_effective_module(self) -> None:
        plan = {
            "target": {"merchant_id": 100, "project_id": 200, "slug": "shop"},
            "locales": ["en-US"],
            "pages": [{"path": "/", "blocks": ["sb-offer-chain"]}],
        }
        structure = {
            "merchantId": 100,
            "projectId": 200,
            "domain": "shop",
            "type": "store",
            "published": None,
            "languages": ["en-US"],
            "pages": [
                {
                    "path": "/",
                    "blocks": [
                        {
                            "_id": "offer-chain",
                            "module": "federated",
                            "values": {"blockId": "sb-offer-chain"},
                        }
                    ],
                }
            ],
        }
        result = verify_structure.verify(plan, structure)
        self.assertTrue(result["ok"])
        self.assertEqual(["sb-offer-chain"], result["pages"][0]["blocks"])


EXAMPLE_BRIEF = ROOT / "examples" / "mobile-single-page.json"


def object_path(path: str) -> dict:
    return {"pathSegment": path, "type": "static"}


class FakeShopBuilderCli:
    """In-memory `xsolla` stand-in whose get-structure returns object page paths."""

    def __init__(self, brief: dict) -> None:
        self.project = brief["project"]
        self.landing: dict | None = None
        self.calls: list[tuple[str, ...]] = []

    def __call__(self, *args: str) -> object:
        self.calls.append(args)
        if args == ("config", "list"):
            return {
                "ok": True,
                "data": {
                    "merchant_id": self.project["merchant_id"],
                    "project_id": self.project["project_id"],
                    "sandbox": self.project["environment"] == "sandbox",
                },
            }
        command = args[1]
        options = dict(zip(args[2::2], args[3::2]))
        if command == "list-websites":
            return {"ok": True, "data": [self.landing] if self.landing else []}
        if command == "create-website":
            self.landing = {
                "_id": "landing-1",
                "domain": options["--slug"],
                "merchantId": self.project["merchant_id"],
                "projectId": self.project["project_id"],
                "type": None,
                "published": None,
                "languages": ["en-US"],
                "pages": [],
            }
            return {"ok": True, "data": copy.deepcopy(self.landing)}
        if command == "get-structure":
            return {"ok": True, "data": copy.deepcopy(self.landing)}
        if command == "set-landing-type":
            self.landing["type"] = options["--type"]
            return {"ok": True}
        if command == "add-page":
            if not isinstance(options["--path"], str):
                raise AssertionError("add-page must receive a string path")
            self.landing["pages"].append(
                {
                    "_id": f"page-{len(self.landing['pages']) + 1}",
                    "name": options["--name"],
                    "path": object_path(options["--path"]),
                    "blocks": [
                        {"_id": "scaffold-header", "module": "header"},
                        {"_id": "scaffold-footer", "module": "footer"},
                    ],
                }
            )
            return {"ok": True}
        if command == "add-language":
            self.landing["languages"].append(options["--language"])
            return {"ok": True}
        raise AssertionError(f"unexpected CLI call: {args}")


def reconciled_landing(landing: dict, plan: dict) -> dict:
    """Return the landing as block reconciliation leaves it, keeping object paths."""
    final = copy.deepcopy(landing)
    page_ids = [target["page_id"] for target in plan["navigation"]]
    for page_plan in plan["pages"]:
        page = apply_plan.page_for_path(final, page_plan["path"])
        blocks = []
        for module in page_plan["blocks"]:
            block = {"_id": f"{page['_id']}-{module}", "module": module}
            if module == "header":
                buttons = {f"nav-{index}": page_id for index, page_id in enumerate(page_ids)}
                block["values"] = {
                    "rightComponents": list(buttons),
                    "components": {
                        button: {
                            "type": "button",
                            "button": {"action": {"action": "page", "pageId": page_id}},
                        }
                        for button, page_id in buttons.items()
                    },
                }
            if module == "newStore":
                block["components"] = [
                    {
                        "enable": True,
                        "section": {
                            "item": {"group": section["external_id"], "type": section["type"]}
                        },
                        "card": {"selectedLayoutType": section["layout"]},
                    }
                    for section in plan["catalog_sections"]
                ]
            blocks.append(block)
        page["blocks"] = blocks
    return final


class ObjectPagePathTests(unittest.TestCase):
    def setUp(self) -> None:
        self.brief = json.loads(EXAMPLE_BRIEF.read_text(encoding="utf-8"))

    def run_apply(self, cli: FakeShopBuilderCli, confirmation_id: str) -> tuple[int, str, str]:
        argv = ["apply_plan.py", str(EXAMPLE_BRIEF), "--confirmation-id", confirmation_id]
        stdout, stderr = io.StringIO(), io.StringIO()
        with (
            mock.patch.dict(apply_plan.RUN_AUTH, {"logged_in": False, "context": None}),
            mock.patch.object(sys, "argv", argv),
            mock.patch.object(apply_plan, "run_preflight"),
            mock.patch.object(apply_plan, "run_json", side_effect=cli),
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            code = apply_plan.main()
            self.recorded_context = apply_plan.RUN_AUTH["context"]
        return code, stdout.getvalue(), stderr.getvalue()

    def test_page_path_accepts_string_and_object_shapes(self) -> None:
        self.assertEqual("/", apply_plan.page_path({"path": "/"}))
        self.assertEqual("/news", apply_plan.page_path({"path": object_path("/news")}))
        for page in (
            {"path": {"type": "static"}},
            {"path": {"pathSegment": 1}},
            {"path": None},
            {},
            "/",
            None,
        ):
            with self.subTest(page=page):
                self.assertIsNone(apply_plan.page_path(page))

    def test_page_for_path_resolves_mixed_path_shapes(self) -> None:
        structure = {
            "pages": [
                {"_id": "home", "path": "/"},
                {"_id": "store", "path": object_path("/store")},
                {"_id": "unreadable", "path": {"type": "static"}},
            ]
        }
        self.assertEqual("home", apply_plan.page_for_path(structure, "/")["_id"])
        self.assertEqual("store", apply_plan.page_for_path(structure, "/store")["_id"])
        self.assertIsNone(apply_plan.page_for_path(structure, "/about"))

    def test_plan_binds_object_paths_and_reports_string_extra_pages(self) -> None:
        structure = {
            "_id": "landing",
            "pages": [
                {"_id": "home", "path": object_path("/"), "blocks": []},
                {"_id": "legacy", "name": "Legacy", "path": "/legacy", "blocks": []},
            ],
        }
        plan = apply_plan.build_plan(self.brief, structure)
        self.assertEqual("home", plan["pages"][0]["page_id"])
        self.assertEqual(
            [{"page_id": "legacy", "name": "Legacy", "path": "/legacy"}],
            plan["current_state"]["extra_pages"],
        )

    def test_plan_rejects_the_same_path_in_both_shapes(self) -> None:
        structure = {
            "pages": [
                {"_id": "one", "path": "/", "blocks": []},
                {"_id": "two", "path": object_path("/"), "blocks": []},
            ]
        }
        with self.assertRaisesRegex(ValueError, "duplicate path /"):
            apply_plan.build_plan(self.brief, structure)

    def test_plan_rejects_a_page_without_a_readable_path(self) -> None:
        structure = {"pages": [{"_id": "one", "path": {"type": "static"}, "blocks": []}]}
        with self.assertRaisesRegex(ValueError, "object with a path"):
            apply_plan.build_plan(self.brief, structure)

    def test_new_landing_resolves_object_path_after_add_page(self) -> None:
        cli = FakeShopBuilderCli(self.brief)
        code, stdout, stderr = self.run_apply(
            cli, apply_plan.build_plan(self.brief)["confirmation_id"]
        )
        self.assertEqual(0, code, stderr)
        report = json.loads(stdout)
        self.assertEqual("bootstrap-complete", report["status"])
        self.assertEqual(["/"], report["created_pages"])
        self.assertEqual(object_path("/"), cli.landing["pages"][0]["path"])
        add_page = next(call for call in cli.calls if call[1] == "add-page")
        self.assertEqual("/", add_page[add_page.index("--path") + 1])
        project = self.brief["project"]
        self.assertEqual(
            {
                "merchant_id": project["merchant_id"],
                "project_id": project["project_id"],
                "sandbox": project["environment"] == "sandbox",
            },
            self.recorded_context,
        )

    def test_rerun_on_object_path_landing_passes_plan_and_verify(self) -> None:
        cli = FakeShopBuilderCli(self.brief)
        code, _, stderr = self.run_apply(
            cli, apply_plan.build_plan(self.brief)["confirmation_id"]
        )
        self.assertEqual(0, code, stderr)

        plan = apply_plan.build_plan(self.brief, {"ok": True, "data": cli.landing})
        self.assertEqual("page-1", plan["pages"][0]["page_id"])
        self.assertEqual([], plan["current_state"]["extra_pages"])

        final = reconciled_landing(cli.landing, plan)
        self.assertEqual(object_path("/"), final["pages"][0]["path"])
        result = verify_structure.verify(plan, {"ok": True, "data": final})
        self.assertTrue(result["ok"], result["errors"])

    def test_structure_verifier_reports_missing_object_path_page(self) -> None:
        plan = {
            "target": {"merchant_id": 100, "project_id": 200, "slug": "shop"},
            "locales": ["en-US"],
            "pages": [
                {"path": "/", "blocks": ["header"]},
                {"path": "/store", "blocks": ["header"]},
            ],
        }
        structure = {
            "merchantId": 100,
            "projectId": 200,
            "domain": "shop",
            "type": "store",
            "published": None,
            "languages": ["en-US"],
            "pages": [
                {"path": object_path("/"), "blocks": [{"_id": "h", "module": "header"}]},
                {"path": object_path("/about"), "blocks": [{"_id": "a", "module": "header"}]},
            ],
        }
        result = verify_structure.verify(plan, structure)
        self.assertIn(
            "page paths differ: expected ['/', '/store'], got ['/', '/about']",
            result["errors"],
        )


class CustomCodeReportTests(unittest.TestCase):
    def apply_to_existing_site(self, blocks: list[str]) -> dict:
        brief = json.loads(EXAMPLE_BRIEF.read_text(encoding="utf-8"))
        brief["content"]["page_overrides"] = [
            {"name": "Home", "path": "/", "blocks": blocks}
        ]
        slug = brief["site"]["slug"]
        cli = FakeShopBuilderCli(brief)
        cli("shopbuilder", "create-website", "--name", "Shop", "--slug", slug, "--type", "topup")
        cli("shopbuilder", "set-landing-type", "--slug", slug, "--type", "store")
        cli("shopbuilder", "add-page", "--slug", slug, "--name", "Home", "--path", "/")
        saved = copy.deepcopy(cli.landing)
        confirmation_id = apply_plan.build_plan(brief, saved)["confirmation_id"]

        def reconciled(slug: str, landing_id: str, page: dict) -> dict:
            return {
                "path": page["path"],
                "page_id": page["page_id"],
                "blocks": page["blocks"],
                "removed_blocks": 0,
            }

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
                mock.patch.object(apply_plan, "reconcile_page", side_effect=reconciled),
                mock.patch.object(apply_plan, "apply_navigation", return_value=[]),
                mock.patch.object(apply_plan, "wire_catalog_sections", return_value=[]),
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                code = apply_plan.main()
        self.assertEqual(0, code, stderr.getvalue())
        return json.loads(stdout.getvalue())

    def test_final_report_tells_the_user_to_fill_custom_code(self) -> None:
        report = self.apply_to_existing_site(["header", "html", "footer"])
        self.assertEqual("implemented-phases-applied", report["status"])
        self.assertEqual(
            [
                "The Custom code block is added empty and hidden; paste your code and "
                "make the block visible in the Site Builder editor."
            ],
            report["warnings"],
        )

    def test_final_report_has_no_custom_code_line_without_the_block(self) -> None:
        report = self.apply_to_existing_site(["header", "footer"])
        self.assertEqual([], report["warnings"])


if __name__ == "__main__":
    unittest.main()
