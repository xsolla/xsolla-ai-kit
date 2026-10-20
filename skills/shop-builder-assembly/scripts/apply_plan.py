#!/usr/bin/env python3
"""Apply a confirmed Shop Builder plan without publishing the landing."""

from __future__ import annotations

import argparse
import copy
import hashlib
import html
import json
import subprocess
import sys
import time
import urllib.request
import uuid
from pathlib import Path

from render_plan import (
    CUSTOM_CODE_WARNING,
    build_plan,
    effective_module,
    page_path,
    structure_data,
    structure_hash,
)
from block_ops import (
    BLOCK_VALUES_ROOT,
    QUESTS_DEV_NAME,
    QUESTS_MODULE,
    QUESTS_VERSION,
    find_block,
    has_object,
    has_leaf,
    quests_host,
)
from verify_structure import landing_leftovers, verify_block_operations
from validate_shop_brief import VERIFIED_BLOCK_MODULES, load_brief, validate

BACKUP_FILE_NAMES = {
    "config.json",
    "websites.json",
    "landing.json",
    "structure.json",
    "localization.json",
    "assets.json",
    "versions.json",
}
SESSION_BOOTSTRAP_RETRY_DELAYS = (5, 10, 20)
LOGIN_SETTLE_SECONDS = 2
LOGIN_TIMEOUT_SECONDS = 45
LOGIN_RETRY_DELAY_SECONDS = 5
# `xsolla` exits with 10 when the API answers HTTP 401 or 403.
CLI_EXIT_AUTH = 10
AUTH_FAILURE_MARKERS = (
    "authentication required",
    "publisher session bootstrap did not yield",
    "auto-bootstrapping publisher session",
)
# A run logs in at most once, and only after the CLI reports an auth failure.
# `context` is the merchant, project and sandbox setting that main() verified;
# `xsolla auth login` can write token claims into the CLI config, so it is
# re-checked after the login.
RUN_AUTH: dict = {"logged_in": False, "context": None}


def refresh_supported_login() -> None:
    for attempt in range(2):
        try:
            # Login messages go to stderr so stdout stays the JSON report.
            result = subprocess.run(
                ["xsolla", "auth", "login"],
                check=False,
                stdout=sys.stderr,
                timeout=LOGIN_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            if attempt == 0:
                time.sleep(LOGIN_RETRY_DELAY_SECONDS)
                continue
            raise RuntimeError("supported Publisher login refresh timed out") from None
        if result.returncode == 0:
            time.sleep(LOGIN_SETTLE_SECONDS)
            return
        if attempt == 0:
            time.sleep(LOGIN_RETRY_DELAY_SECONDS)
    raise RuntimeError("supported Publisher login refresh failed")


def auth_failure(returncode: int, detail: str) -> bool:
    """Return whether a CLI failure is one that a fresh supported login can fix."""
    if "HTTP 429" in detail:
        return False
    return returncode == CLI_EXIT_AUTH or any(
        marker in detail for marker in AUTH_FAILURE_MARKERS
    )


def cli_context(config: object) -> dict:
    value = data(config)
    if not isinstance(value, dict):
        raise RuntimeError("xsolla config list returned an unexpected shape")
    return {
        "merchant_id": value.get("merchant_id"),
        "project_id": value.get("project_id"),
        "sandbox": value.get("sandbox") is True,
    }


def login_once(detail: str) -> None:
    if RUN_AUTH["logged_in"]:
        raise RuntimeError(
            "authentication still fails after this run's one `xsolla auth login`. "
            "The failed command made no change, so it is safe to rerun. CLI error: "
            + detail
        )
    approved = RUN_AUTH["context"]
    if approved is None:
        raise RuntimeError(
            "authentication failed before the CLI context was verified: " + detail
        )
    RUN_AUTH["logged_in"] = True
    refresh_supported_login()
    current = cli_context(run_json("config", "list"))
    changed = [
        f"{key} {approved[key]!r} -> {current[key]!r}"
        for key in approved
        if current[key] != approved[key]
    ]
    if changed:
        raise RuntimeError(
            "CLI context changed after `xsolla auth login` ("
            + ", ".join(changed)
            + "). The command was not retried and made no change, so it is safe to "
            "rerun: check .xsolla.json in the working directory, then run preflight "
            "again"
        )


def run_json(*args: str) -> object:
    command = ["xsolla", *args, "--json"]
    rate_limit_attempt = 0
    while True:
        # The CLI writes UTF-8; without an explicit encoding Windows decodes with
        # the ANSI code page and loses the output.
        result = subprocess.run(
            command, capture_output=True, text=True, encoding="utf-8", check=False
        )
        if not result.returncode:
            break
        detail = (
            (result.stderr or "").strip()
            or (result.stdout or "").strip()
            or f"exit code {result.returncode}"
        )
        retryable_bootstrap_limit = (
            "publisher session bootstrap" in detail and "HTTP 429" in detail
        )
        if retryable_bootstrap_limit and rate_limit_attempt < len(
            SESSION_BOOTSTRAP_RETRY_DELAYS
        ):
            time.sleep(SESSION_BOOTSTRAP_RETRY_DELAYS[rate_limit_attempt])
            rate_limit_attempt += 1
            continue
        if auth_failure(result.returncode, detail):
            login_once(detail)
            continue
        if "publisher session bootstrap" in detail:
            detail += (
                "; refresh the supported Publisher login with `xsolla auth login` "
                "and rerun—never copy a browser PA token"
            )
        raise RuntimeError(f"{' '.join(args)} failed: {detail}")
    stdout = result.stdout or ""
    stderr = (result.stderr or "").strip() or "no stderr output"
    if not stdout.strip():
        raise RuntimeError(f"{' '.join(args)} returned no output: {stderr}")
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{' '.join(args)} returned invalid JSON: {stderr}") from exc


def data(value: object) -> object:
    if isinstance(value, dict) and value.get("ok") is True and "data" in value:
        return value["data"]
    return value


def website_exists(value: object, slug: str) -> bool:
    payload = data(value)
    if isinstance(payload, dict):
        payload = payload.get("items", payload.get("landings", payload))
    if isinstance(payload, list):
        return any(
            isinstance(item, dict)
            and (item.get("domain") == slug or item.get("slug") == slug)
            for item in payload
        )
    text = json.dumps(payload, sort_keys=True)
    return f'"{slug}"' in text


def structure(slug: str) -> dict:
    value = data(run_json("shopbuilder", "get-structure", "--slug", slug))
    if not isinstance(value, dict) or not isinstance(value.get("pages"), list):
        raise RuntimeError("get-structure returned an unexpected shape")
    return value


def page_for_path(value: dict, path: str) -> dict | None:
    for page in value["pages"]:
        if page_path(page) == path:
            return page
    return None


def verified_backup(path: Path, expected: dict, slug: str) -> bool:
    manifest_path = path / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if (
            manifest.get("slug") != slug
            or manifest.get("merchant_id") != expected["merchant_id"]
            or manifest.get("project_id") != expected["project_id"]
            or manifest.get("environment") != expected["environment"]
            or manifest.get("read_only") is not True
        ):
            return False
        files = manifest.get("files")
        digests = manifest.get("sha256")
        if (
            not isinstance(files, list)
            or not files
            or any(
                not isinstance(name, str) or Path(name).name != name for name in files
            )
            or len(files) != len(set(files))
            or set(files) != BACKUP_FILE_NAMES
            or not isinstance(digests, dict)
            or set(files) != set(digests)
        ):
            return False
        for name in files:
            digest = digests[name]
            if not isinstance(digest, str):
                return False
            file_path = path / name
            if hashlib.sha256(file_path.read_bytes()).hexdigest() != digest:
                return False
        return True
    except (OSError, TypeError, json.JSONDecodeError):
        return False


def backup_structure(path: Path) -> object:
    try:
        value = json.loads((path / "structure.json").read_text(encoding="utf-8"))
        return structure_data(value)
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot read backup structure: {exc}") from exc


def run_preflight(brief_path: Path, approved_test_projects: Path | None) -> None:
    # `-X utf8` makes the child write UTF-8 to the pipe; on Windows it would
    # otherwise write the ANSI code page.
    command = [
        sys.executable,
        "-X",
        "utf8",
        str(Path(__file__).with_name("preflight.py")),
        str(brief_path),
    ]
    if approved_test_projects is not None:
        command.extend(["--approved-test-projects", str(approved_test_projects)])
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if result.returncode:
        raise RuntimeError(
            (result.stderr or "").strip()
            or (result.stdout or "").strip()
            or "preflight failed"
        )


def reconcile_page(slug: str, landing_id: str, page_plan: dict) -> dict:
    current = structure(slug)
    page = page_for_path(current, page_plan["path"])
    if page is None:
        raise RuntimeError(
            f"page {page_plan['path']} must be created in the page phase before reconciliation"
        )
    if not isinstance(page.get("_id"), str):
        raise RuntimeError(f"could not resolve page {page_plan['path']}")

    page_id = page["_id"]
    desired = page_plan["blocks"]
    unverified = sorted(set(desired) - VERIFIED_BLOCK_MODULES)
    if unverified:
        raise RuntimeError(
            "plan contains unverified block modules: " + ", ".join(unverified)
        )
    kept: set[str] = set()
    removals: list[dict] = []
    blocks = page.get("blocks", [])
    if not isinstance(blocks, list) or any(
        not isinstance(block, dict) for block in blocks
    ):
        raise RuntimeError("pages[].blocks must contain full block objects")
    for block in blocks:
        module = effective_module(block)
        if module in desired and module not in kept:
            kept.add(module)
        else:
            removals.append(block)
    approved_removals = {
        removal["block_id"]: removal["module"]
        for removal in page_plan.get("removals", [])
    }
    unapproved = [
        block
        for block in removals
        if approved_removals.get(block.get("_id")) != effective_module(block)
    ]
    if unapproved:
        details = ", ".join(
            f"{effective_module(block)}:{block.get('_id')}" for block in unapproved
        )
        raise RuntimeError(
            "current page requires unconfirmed block removals; back up, re-render, "
            f"and reconfirm the plan ({details})"
        )
    current_modules = [effective_module(block) for block in blocks]
    if not removals and current_modules == desired:
        return {
            "path": page_plan["path"],
            "page_id": page_id,
            "blocks": current_modules,
            "removed_blocks": 0,
            "hidden_custom_code": [],
        }
    if removals:
        removal_ids = {block["_id"] for block in removals}
        removal_indexes = sorted(
            (
                index
                for index, block in enumerate(blocks)
                if block.get("_id") in removal_ids
            ),
            reverse=True,
        )
        removal_payload = {
            "removeBlocks": {
                "type": "page",
                "id": page_id,
                "patches": [
                    {"op": "remove", "path": ["blocks", index]}
                    for index in removal_indexes
                ],
            }
        }
        run_json(
            "shopbuilder",
            "update-block",
            "--landing-id",
            landing_id,
            "--data",
            json.dumps(removal_payload, sort_keys=True, separators=(",", ":")),
        )

    page = page_for_path(structure(slug), page_plan["path"])
    if page is None:
        raise RuntimeError(
            f"page disappeared during reconciliation: {page_plan['path']}"
        )
    existing = [effective_module(block) for block in page.get("blocks", [])]
    known_block_ids = {block.get("_id") for block in page.get("blocks", [])}
    for module in desired:
        if module not in existing:
            run_json(
                "shopbuilder",
                "add-block",
                "--landing-id",
                landing_id,
                "--page-id",
                page_id,
                "--block",
                module,
            )
            existing.append(module)
    hidden_custom_code = (
        hide_added_custom_code(slug, landing_id, page_plan["path"], known_block_ids)
        if "html" in desired
        else []
    )

    for destination, module in enumerate(desired):
        page = page_for_path(structure(slug), page_plan["path"])
        if page is None:
            raise RuntimeError(f"page disappeared during ordering: {page_plan['path']}")
        modules = [effective_module(block) for block in page.get("blocks", [])]
        source = modules.index(module)
        if source != destination:
            run_json(
                "shopbuilder",
                "move-block",
                "--landing-id",
                landing_id,
                "--page-id",
                page_id,
                "--source",
                str(source),
                "--destination",
                str(destination),
            )

    final_page = page_for_path(structure(slug), page_plan["path"])
    if final_page is None:
        raise RuntimeError(f"could not read final page {page_plan['path']}")
    final_modules = [effective_module(block) for block in final_page.get("blocks", [])]
    if final_modules != desired:
        raise RuntimeError(
            f"block reconciliation failed for {page_plan['path']}: {final_modules}"
        )
    still_visible = [
        block.get("_id")
        for block in final_page.get("blocks", [])
        if block.get("_id") in hidden_custom_code and block.get("hidden") is not True
    ]
    if still_visible:
        raise RuntimeError(
            f"could not hide the new Custom code block on {page_plan['path']}: "
            + ", ".join(still_visible)
        )
    return {
        "path": page_plan["path"],
        "page_id": page_id,
        "blocks": final_modules,
        "removed_blocks": len(removals),
        "hidden_custom_code": hidden_custom_code,
    }


# Ops-mode executor. Every CLI shape below is documented in `xsolla shopbuilder <cmd>
# --help` (1.9.4) and, where noted, exercised on a test site (spike-cli.md, 2026-10-20).
OPS_APPLY_SUPPORTED = {
    "block_add",
    "block_values",
    "block_reset",
    "block_move",
    "block_duplicate",
    "block_visibility",
    "block_delete",
    "block_localization",
}
CDN_TIMEOUT_SECONDS = 20


class ApplyContext:
    """What one run of block operations needs: the target and the confirmed plan.

    ``refs`` maps "op:N" to the id of the block an add op created and "dup:N" to the
    id of a duplicate's copy.
    """

    def __init__(
        self, slug: str, landing_id: str, plan: dict, refs: dict | None = None
    ) -> None:
        self.slug = slug
        self.landing_id = landing_id
        self.plan = plan
        self.refs = refs if refs is not None else {}


def block_patch_payload(
    block_id: str, patches: list[dict], request_id: str = "r1"
) -> str:
    """Batch body for `update-block --data`: a map of requestId -> change (see --help)."""
    clean = [
        {key: value for key, value in patch.items() if key in ("op", "path", "value")}
        for patch in patches
    ]
    payload = {request_id: {"type": "block", "id": block_id, "patches": clean}}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def patch_block(
    landing_id: str, block_id: str, patches: list[dict], request_id: str = "r1"
) -> None:
    response = data(
        run_json(
            "shopbuilder",
            "update-block",
            "--landing-id",
            landing_id,
            "--data",
            block_patch_payload(block_id, patches, request_id),
        )
    )
    # The batch API answers 200 with `{"patches": []}` when it ignored every patch
    # (for example a leaf under a missing parent object). Never treat that as applied.
    if (
        patches
        and isinstance(response, dict)
        and isinstance(response.get("patches"), list)
        and not response["patches"]
    ):
        raise RuntimeError(
            f"update-block on {block_id} was accepted but applied no patch: "
            + ", ".join("/".join(str(part) for part in patch["path"]) for patch in patches)
        )


def set_block_hidden(
    block_id: str, hidden: bool, *, landing_id: str, request_id: str = "r1"
) -> None:
    """Hide or show a block. Shared by block operations and Custom code hiding."""
    patch_block(
        landing_id,
        block_id,
        [{"op": "replace", "path": ["hidden"], "value": hidden}],
        request_id,
    )


def fetch_quests_defaults(version: str) -> dict:
    """Read the public default-data.json the CDN serves for a Quests block version."""
    url = quests_host(version) + "default-data.json"
    try:
        with urllib.request.urlopen(url, timeout=CDN_TIMEOUT_SECONDS) as response:
            value = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError) as exc:
        raise RuntimeError(f"cannot read the Quests block defaults at {url}: {exc}") from exc
    resources = value.get("resources") if isinstance(value, dict) else None
    if (
        not isinstance(value, dict)
        or not isinstance(value.get("defaultData"), dict)
        or not isinstance(resources, dict)
        or not isinstance(resources.get("localizedValues"), dict)
    ):
        raise RuntimeError(f"unexpected default-data.json shape at {url}")
    return value


def current_block(ctx: ApplyContext, block_id: str) -> tuple[dict, int, dict]:
    found = find_block(structure(ctx.slug), block_id)
    if found is None:
        raise RuntimeError(f"block {block_id} is no longer on the site")
    return found


def item_block_id(item: dict, ctx: ApplyContext) -> str:
    if item.get("block_id"):
        return item["block_id"]
    ref = item.get("block_ref")
    if ref not in ctx.refs:
        raise RuntimeError(f"no block was created for {ref}")
    return ctx.refs[ref]


def move_to(ctx: ApplyContext, page_id: str, block_id: str, index: int) -> None:
    position = current_block(ctx, block_id)[1]
    if position != index:
        run_json(
            "shopbuilder",
            "move-block",
            "--landing-id",
            ctx.landing_id,
            "--page-id",
            page_id,
            "--source",
            str(position),
            "--destination",
            str(index),
        )


def new_block_on_page(ctx: ApplyContext, page_id: str, before: set) -> dict:
    page = page_for_id(structure(ctx.slug), page_id)
    created = [block for block in page.get("blocks", []) if block.get("_id") not in before]
    if len(created) != 1:
        raise RuntimeError(
            f"expected one new block on page {page_id}, found {len(created)}"
        )
    return created[0]


def block_ids_on_page(ctx: ApplyContext, page_id: str) -> set:
    return {
        block.get("_id") for block in page_for_id(structure(ctx.slug), page_id)["blocks"]
    }


def add_quests_block(item: dict, ctx: ApplyContext) -> dict:
    """federated_patch: bare `federated` wrapper, then one update-block retarget."""
    page_id = item["page_id"]
    version = item.get("version") or QUESTS_VERSION
    # Read the CDN first so a network failure cannot leave an empty wrapper behind.
    defaults = fetch_quests_defaults(version)
    before = block_ids_on_page(ctx, page_id)
    command = [
        "shopbuilder",
        "add-block",
        "--landing-id",
        ctx.landing_id,
        "--page-id",
        page_id,
        "--block",
        "federated",
    ]
    # The CLI drops `--index 0`, and the API then places the block first.
    if item["index"] > 0:
        command += ["--index", str(item["index"])]
    run_json(*command)
    block_id = new_block_on_page(ctx, page_id, before)["_id"]
    ctx.refs[item["block_ref"]] = block_id
    try:
        patch_block(
            ctx.landing_id,
            block_id,
            [
                {"op": "replace", "path": ["values", "host"], "value": quests_host(version)},
                {"op": "replace", "path": ["values", "blockId"], "value": QUESTS_MODULE},
                {"op": "replace", "path": ["values", "version"], "value": version},
                {"op": "replace", "path": ["values", "useAsNativeBlock"], "value": False},
                {
                    "op": "replace",
                    "path": ["values", "internalBlockValues"],
                    "value": defaults["defaultData"],
                },
                {
                    "op": "replace",
                    "path": ["values", "resources", "localizedValues"],
                    "value": defaults["resources"]["localizedValues"],
                },
            ],
        )
        # A separate change keeps a rejected label from undoing the retarget.
        patch_block(
            ctx.landing_id,
            block_id,
            [{"op": "add", "path": ["devName"], "value": QUESTS_DEV_NAME}],
            request_id="r2",
        )
        move_to(ctx, page_id, block_id, item["index"])
        values = current_block(ctx, block_id)[2].get("values") or {}
        if values.get("blockId") != QUESTS_MODULE or values.get("version") != version:
            raise RuntimeError("the new block was not retargeted to the Quests module")
    except RuntimeError as exc:
        raise RuntimeError(
            f"{exc}. The new block {block_id} is on page {page_id}; remove it with a "
            "confirmed delete op before retrying"
        ) from exc
    return {"block_id": block_id}


def apply_values(item: dict, ctx: ApplyContext) -> dict:
    block_id = item_block_id(item, ctx)
    block = current_block(ctx, block_id)[2]
    internal = (block.get("values") or {}).get("internalBlockValues")
    # An `add` of {} over an existing object would wipe it, so create only absent parents.
    missing = [
        parent
        for parent in item["create_parents"]
        if not has_object(internal, tuple(parent["path"][len(BLOCK_VALUES_ROOT) :]))
    ]
    if missing:
        patch_block(ctx.landing_id, block_id, missing)
    patch_block(ctx.landing_id, block_id, item["patches"])
    return {"block_id": block_id}


def apply_reset(item: dict, ctx: ApplyContext) -> dict:
    block_id = item["block_id"]
    internal = (current_block(ctx, block_id)[2].get("values") or {}).get("internalBlockValues")
    patches = [
        patch
        for patch in item["patches"]
        if has_leaf(internal, tuple(patch["path"][len(BLOCK_VALUES_ROOT) :]))
    ]
    if patches:
        patch_block(ctx.landing_id, block_id, patches)
    return {"block_id": block_id}


def apply_move(item: dict, ctx: ApplyContext) -> dict:
    # The plan's source_index comes from the backup; the live index decides.
    move_to(ctx, item["page_id"], item["block_id"], item["index"])
    return {"block_id": item["block_id"]}


def apply_duplicate(item: dict, ctx: ApplyContext) -> dict:
    page_id = item["page_id"]
    block_id = item["block_id"]
    current_block(ctx, block_id)
    before = block_ids_on_page(ctx, page_id)
    command = [
        "shopbuilder",
        "duplicate-block",
        "--landing-id",
        ctx.landing_id,
        "--page-id",
        page_id,
        "--blockid",
        block_id,
    ]
    if item["index"] > 0:
        command += ["--index", str(item["index"])]
    run_json(*command)
    copy_id = new_block_on_page(ctx, page_id, before)["_id"]
    ctx.refs[f"dup:{item['op_index']}"] = copy_id
    move_to(ctx, page_id, copy_id, item["index"])
    return {"block_id": block_id, "copy_id": copy_id}


def apply_delete(item: dict, ctx: ApplyContext) -> dict:
    block_id = item["block_id"]
    page_id = item["page_id"]
    # User-approved exception to the never-`--force` rule: only for blocks the
    # confirmed plan lists as removals, and only while the block is still on its page.
    # A page `removeBlocks` patch would orphan it (delete then fails with HTTP 404).
    if not any(
        removal.get("block_id") == block_id and removal.get("page_id") == page_id
        for removal in ctx.plan.get("removals", [])
    ):
        raise RuntimeError(f"block {block_id} is not in the confirmed plan removals")
    page, _, block = current_block(ctx, block_id)
    if page.get("_id") != page_id:
        raise RuntimeError(f"block {block_id} is not on page {page_id}")
    if effective_module(block) != QUESTS_MODULE:
        raise RuntimeError(f"block {block_id} is not a Quests block; refusing to delete it")
    run_json(
        "shopbuilder",
        "delete-block",
        "--landing-id",
        ctx.landing_id,
        "--page-id",
        page_id,
        "--blockid",
        block_id,
        "--force",
    )
    return {"block_id": block_id}


def text_localization_id(block: dict, key: str) -> str:
    """The `L:` id behind ``internalBlockValues.translations.<key>``.

    ``translations.<key>`` holds a block-local `L:` key; the block's
    ``resources.localizedValues`` entry for it names the localization id that
    `get-localization` and `update-many-localization` use.
    """
    values = block.get("values") or {}
    short = ((values.get("internalBlockValues") or {}).get("translations") or {}).get(key)
    texts = (((values.get("resources") or {}).get("localizedValues") or {}).get(short) or {}).get(
        "texts"
    )
    text_id = texts.get("id") if isinstance(texts, dict) else None
    if not isinstance(text_id, str) or not text_id.startswith("L:"):
        raise RuntimeError(f"block {block.get('_id')} has no localization id for {key}")
    return text_id


def localization_scope(localization: object, text_id: str, default_scope: str) -> str:
    """Namespace (page id or `common`) that holds ``text_id``."""
    value = data(localization)
    if isinstance(value, dict):
        for page_id, namespace in (value.get("pages") or {}).items():
            if text_id in (namespace.get("texts") or {}):
                return page_id
        if text_id in ((value.get("common") or {}).get("texts") or {}):
            return "common"
    return default_scope


def apply_localization(item: dict, ctx: ApplyContext) -> dict:
    block_id = item_block_id(item, ctx)
    current = structure(ctx.slug)
    found = find_block(current, block_id)
    if found is None:
        raise RuntimeError(f"block {block_id} is no longer on the site")
    page, _, block = found
    languages = current.get("languages") or []
    localization = run_json("shopbuilder", "get-localization", "--slug", ctx.slug)
    for locale, texts in item["translations"].items():
        if locale not in languages:
            raise RuntimeError(f"locale {locale} is not enabled on {ctx.slug}")
        values = {}
        scope = None
        for key, text in texts.items():
            text_id = text_localization_id(block, key)
            text_scope = localization_scope(localization, text_id, page["_id"])
            if scope not in (None, text_scope):
                raise RuntimeError(f"{block_id} texts span more than one localization scope")
            scope = text_scope
            values[text_id] = {"translation": text}
        payload = {"locale": locale, "perScopeValues": {scope: values}}
        run_json(
            "shopbuilder",
            "update-many-localization",
            "--slug",
            ctx.slug,
            "--data",
            json.dumps(payload, sort_keys=True, separators=(",", ":")),
        )
    return {"block_id": block_id}


def apply_block_operation(item: dict, ctx: ApplyContext) -> dict:
    """Run one confirmed plan item against the CLI and report what it touched."""
    kind = item["type"]
    if kind == "block_add":
        done = add_quests_block(item, ctx)
    elif kind == "block_values":
        done = apply_values(item, ctx)
    elif kind == "block_reset":
        done = apply_reset(item, ctx)
    elif kind == "block_move":
        done = apply_move(item, ctx)
    elif kind == "block_duplicate":
        done = apply_duplicate(item, ctx)
    elif kind == "block_visibility":
        current_block(ctx, item["block_id"])
        set_block_hidden(item["block_id"], item["hidden"], landing_id=ctx.landing_id)
        done = {"block_id": item["block_id"]}
    elif kind == "block_delete":
        done = apply_delete(item, ctx)
    elif kind == "block_localization":
        done = apply_localization(item, ctx)
    else:
        raise RuntimeError(f"unknown block operation {kind}")
    return {"type": kind, "op_index": item["op_index"], **done}


def apply_block_operations(
    slug: str, landing_id: str, plan: dict, refs: dict | None = None
) -> list[dict]:
    """Run only the confirmed block operation items; touch nothing else.

    ``refs`` receives the ids of blocks the run created, for verification.
    """
    items = plan["block_operations"]
    unsupported = sorted(
        {item["type"] for item in items if item["type"] not in OPS_APPLY_SUPPORTED}
    )
    if unsupported:
        raise RuntimeError(
            "plan contains block operations apply cannot run: " + ", ".join(unsupported)
        )
    expected = plan.get("current_state", {}).get("structure_sha256")
    if not isinstance(expected, str):
        raise RuntimeError(
            "plan has no current_state.structure_sha256; re-render it from a backup"
        )
    if structure_hash(structure(slug)) != expected:
        raise RuntimeError(
            "target structure changed after backup; back up, re-render, and reconfirm"
        )
    ctx = ApplyContext(slug, landing_id, plan, refs)
    return [apply_block_operation(item, ctx) for item in items]


def page_for_id(value: dict, page_id: str) -> dict:
    for page in value["pages"]:
        if page.get("_id") == page_id:
            return page
    raise RuntimeError(f"page {page_id} is no longer on the site")


def hide_added_custom_code(
    slug: str, landing_id: str, path: str, known_block_ids: set
) -> list[str]:
    """Hide each Custom code block this run added; `add-block` creates it visible.

    Blocks that were on the page before this run are left as the user set them.
    """
    page = page_for_path(structure(slug), path)
    if page is None:
        raise RuntimeError(f"page disappeared during reconciliation: {path}")
    hidden: list[str] = []
    for block in page.get("blocks", []):
        block_id = block.get("_id")
        if effective_module(block) != "html" or block_id in known_block_ids:
            continue
        if not isinstance(block_id, str):
            raise RuntimeError(f"new Custom code block on {path} has no _id")
        if block.get("hidden") is not True:
            set_block_hidden(
                block_id, True, landing_id=landing_id, request_id="hideCustomCode"
            )
        hidden.append(block_id)
    return hidden


def add_missing_pages(slug: str, page_plans: list[dict]) -> list[str]:
    created: list[str] = []
    current = structure(slug)
    for page_plan in page_plans:
        if page_for_path(current, page_plan["path"]) is not None:
            continue
        run_json(
            "shopbuilder",
            "add-page",
            "--slug",
            slug,
            "--name",
            page_plan["name"],
            "--path",
            page_plan["path"],
        )
        created.append(page_plan["path"])
        current = structure(slug)
        if page_for_path(current, page_plan["path"]) is None:
            raise RuntimeError(f"could not resolve created page {page_plan['path']}")
    return created


def ensure_locales(slug: str, desired: list[str]) -> dict:
    current = structure(slug)
    languages = current.get("languages")
    if not isinstance(languages, list) or any(
        not isinstance(language, str) for language in languages
    ):
        raise RuntimeError("get-structure returned an invalid languages list")
    added: list[str] = []
    for locale in desired:
        if locale in languages:
            continue
        run_json("shopbuilder", "add-language", "--slug", slug, "--language", locale)
        added.append(locale)
        languages.append(locale)
    if not added:
        return {
            "requested": desired,
            "added": [],
            "preserved_extra": sorted(set(languages) - set(desired)),
        }
    refreshed = structure(slug)
    final_languages = refreshed.get("languages")
    if (
        not isinstance(final_languages, list)
        or any(not isinstance(language, str) for language in final_languages)
        or any(locale not in final_languages for locale in desired)
    ):
        raise RuntimeError("locale reconciliation did not produce every requested locale")
    return {
        "requested": desired,
        "added": added,
        "preserved_extra": sorted(set(final_languages) - set(desired)),
    }


def stable_component_id(landing_id: str, page_id: str, target_path: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{landing_id}:{page_id}:{target_path}"))


def stable_localization_id(component_id: str) -> str:
    return "L:" + str(uuid.uuid5(uuid.NAMESPACE_URL, component_id + ":label"))


def header_navigation_patches(
    header: dict, landing_id: str, page_id: str, navigation: list[dict]
) -> tuple[list[dict], dict[str, str]]:
    values = header.get("values")
    if not isinstance(values, dict):
        raise RuntimeError("header values must be an object")
    components = values.get("components")
    if not isinstance(components, dict):
        raise RuntimeError("header values.components must be an object")

    existing_buttons = sorted(
        key
        for key, component in components.items()
        if isinstance(key, str)
        and isinstance(component, dict)
        and component.get("type") == "button"
    )
    button_ids: list[str] = []
    labels: dict[str, str] = {}
    patches: list[dict] = []
    for index, target in enumerate(navigation):
        target_page_id = target.get("page_id")
        if not isinstance(target_page_id, str):
            raise RuntimeError("navigation target page IDs require a target-bound plan")
        component_id = (
            existing_buttons[index]
            if index < len(existing_buttons)
            else stable_component_id(landing_id, page_id, target["path"])
        )
        button_ids.append(component_id)
        existing = components.get(component_id)
        action = (
            existing.get("button", {}).get("action", {})
            if isinstance(existing, dict)
            else {}
        )
        text = action.get("text") if isinstance(action, dict) else None
        localization_id = text.get("id") if isinstance(text, dict) else None
        if not isinstance(localization_id, str) or not localization_id.startswith("L:"):
            localization_id = stable_localization_id(component_id)
        labels[localization_id] = target["name"]
        new_action = {
            "__type": "action",
            "action": "page",
            "landingId": landing_id,
            "openNewTab": False,
            "pageId": target_page_id,
            "text": {"enable": True, "id": localization_id},
        }
        if existing is None:
            patches.append(
                {
                    "op": "add",
                    "path": ["values", "components", component_id],
                    "value": {
                        "id": component_id,
                        "type": "button",
                        "button": {
                            "action": new_action,
                            "variant": {"type": "extra", "value": "header-button"},
                        },
                    },
                }
            )
        else:
            patches.append(
                {
                    "op": "replace",
                    "path": ["values", "components", component_id, "button", "action"],
                    "value": new_action,
                }
            )

    for component_id in existing_buttons[len(navigation) :]:
        patches.append(
            {"op": "remove", "path": ["values", "components", component_id]}
        )

    for area in ("fixedComponents", "leftComponents", "rightComponents"):
        current = values.get(area)
        if not isinstance(current, list):
            raise RuntimeError(f"header values.{area} must be a list")
        retained = [item for item in current if item not in existing_buttons]
        if area == "rightComponents":
            retained.extend(button_ids)
        patches.append(
            {"op": "replace", "path": ["values", area], "value": retained}
        )
    return patches, labels


def update_localized_label_scopes(
    slug: str, labels_by_page: dict[str, dict[str, str]], locales: list[str]
) -> None:
    for locale in locales:
        per_scope = {
            page_id: {
                localization_id: {
                    "translation": f"<span>{html.escape(label)}</span>"
                }
                for localization_id, label in labels.items()
            }
            for page_id, labels in labels_by_page.items()
        }
        run_json(
            "shopbuilder",
            "update-many-localization",
            "--slug",
            slug,
            "--data",
            json.dumps(
                {"locale": locale, "perScopeValues": per_scope},
                separators=(",", ":"),
            ),
        )


def apply_navigation(slug: str, landing_id: str, plan: dict) -> list[dict]:
    current = structure(slug)
    results: list[dict] = []
    operations: list[dict] = []
    labels_by_page: dict[str, dict[str, str]] = {}
    expected_page_ids = [target["page_id"] for target in plan["navigation"]]
    for page_plan in plan["pages"]:
        page = page_for_path(current, page_plan["path"])
        if page is None or not isinstance(page.get("_id"), str):
            raise RuntimeError(f"missing page during navigation: {page_plan['path']}")
        header = next(
            (
                block
                for block in page.get("blocks", [])
                if effective_module(block) == "header"
            ),
            None,
        )
        if not isinstance(header, dict) or not isinstance(header.get("_id"), str):
            raise RuntimeError(f"page {page_plan['path']} has no header block")
        components = header.get("values", {}).get("components", {})
        right = header.get("values", {}).get("rightComponents", [])
        actual_page_ids = [
            components[component_id].get("button", {}).get("action", {}).get("pageId")
            for component_id in right
            if isinstance(components.get(component_id), dict)
            and components[component_id].get("type") == "button"
            and components[component_id]
            .get("button", {})
            .get("action", {})
            .get("action")
            == "page"
        ]
        results.append(
            {
                "path": page_plan["path"],
                "header_id": header["_id"],
                "target_page_ids": expected_page_ids,
            }
        )
        if actual_page_ids == expected_page_ids:
            continue
        patches, labels = header_navigation_patches(
            header, landing_id, page["_id"], plan["navigation"]
        )
        labels_by_page[page["_id"]] = labels
        operations.append(
            {"path": page_plan["path"], "header_id": header["_id"], "patches": patches}
        )

    if labels_by_page:
        update_localized_label_scopes(slug, labels_by_page, plan["locales"])
    for operation in operations:
        run_json(
            "shopbuilder",
            "update-block",
            "--landing-id",
            landing_id,
            "--data",
            json.dumps(
                {
                    "navigation": {
                        "type": "block",
                        "id": operation["header_id"],
                        "patches": operation["patches"],
                    }
                },
                separators=(",", ":"),
            ),
        )

    refreshed = structure(slug)
    for result in results:
        page = page_for_path(refreshed, result["path"])
        header = next(
            (
                block
                for block in page.get("blocks", [])
                if block.get("_id") == result["header_id"]
            ),
            None,
        ) if page else None
        if not isinstance(header, dict):
            raise RuntimeError("header disappeared during navigation verification")
        components = header.get("values", {}).get("components", {})
        right = header.get("values", {}).get("rightComponents", [])
        actual_page_ids = [
            components[component_id].get("button", {}).get("action", {}).get("pageId")
            for component_id in right
            if isinstance(components.get(component_id), dict)
            and components[component_id].get("type") == "button"
            and components[component_id]
            .get("button", {})
            .get("action", {})
            .get("action")
            == "page"
        ]
        if actual_page_ids != expected_page_ids:
            raise RuntimeError(
                f"navigation reconciliation failed on {result['path']}: {actual_page_ids}"
            )
    return results


def store_section_identity(component: object) -> tuple[object, object, object, object]:
    if not isinstance(component, dict):
        return (None, None, None, None)
    section = component.get("section")
    card = component.get("card")
    item = section.get("item") if isinstance(section, dict) else None
    return (
        item.get("group") if isinstance(item, dict) else None,
        item.get("type") if isinstance(item, dict) else None,
        card.get("selectedLayoutType") if isinstance(card, dict) else None,
        component.get("enable"),
    )


def catalog_patches(components: object, sections: list[dict]) -> list[dict]:
    """Create targeted Immer patches without replacing the components array."""
    if not isinstance(components, list) or not components:
        raise RuntimeError("newStore has no component template")
    if any(not isinstance(component, dict) for component in components):
        raise RuntimeError("newStore components must be objects")

    patches: list[dict] = []
    shared = min(len(components), len(sections))
    for index in range(shared):
        section = sections[index]
        patches.extend(
            [
                {
                    "op": "replace",
                    "path": ["components", index, "enable"],
                    "value": True,
                },
                {
                    "op": "replace",
                    "path": ["components", index, "section", "item", "autoSelected"],
                    "value": False,
                },
                {
                    "op": "replace",
                    "path": ["components", index, "section", "item", "group"],
                    "value": section["external_id"],
                },
                {
                    "op": "replace",
                    "path": ["components", index, "section", "item", "type"],
                    "value": section["type"],
                },
                {
                    "op": "replace",
                    "path": ["components", index, "card", "selectedLayoutType"],
                    "value": section["layout"],
                },
                {
                    "op": "replace",
                    "path": ["components", index, "section", "title", "enable"],
                    "value": section["title_enabled"],
                },
            ]
        )

    template = components[0]
    for index in range(shared, len(sections)):
        section = sections[index]
        component = copy.deepcopy(template)
        component.pop("_id", None)
        component["enable"] = True
        component.setdefault("section", {}).setdefault("item", {}).update(
            {
                "autoSelected": False,
                "group": section["external_id"],
                "type": section["type"],
            }
        )
        component.setdefault("section", {}).setdefault("title", {})[
            "enable"
        ] = section["title_enabled"]
        component.setdefault("card", {})["selectedLayoutType"] = section["layout"]
        patches.append(
            {"op": "add", "path": ["components", index], "value": component}
        )

    for index in range(len(components) - 1, len(sections) - 1, -1):
        patches.append({"op": "remove", "path": ["components", index]})
    return patches


def wire_catalog_sections(slug: str, landing_id: str, plan: dict) -> list[dict]:
    if not plan["catalog_sections"]:
        return []
    desired = [
        (
            section["external_id"],
            section["type"],
            section["layout"],
            True,
        )
        for section in plan["catalog_sections"]
    ]
    current = structure(slug)
    results: list[dict] = []
    for page_plan in plan["pages"]:
        page = page_for_path(current, page_plan["path"])
        if page is None:
            raise RuntimeError(f"missing page during catalog wiring: {page_plan['path']}")
        for block in page.get("blocks", []):
            if effective_module(block) != "newStore":
                continue
            block_id = block.get("_id")
            if not isinstance(block_id, str):
                raise RuntimeError("newStore block has no _id")
            patches = catalog_patches(block.get("components"), plan["catalog_sections"])
            actual = [
                store_section_identity(component)
                for component in block.get("components", [])
            ]
            if actual == desired:
                patches = []
            if patches:
                run_json(
                    "shopbuilder",
                    "update-block",
                    "--landing-id",
                    landing_id,
                    "--data",
                    json.dumps(
                        {
                            "catalog": {
                                "type": "block",
                                "id": block_id,
                                "patches": patches,
                            }
                        },
                        separators=(",", ":"),
                    ),
                )
            results.append(
                {"path": page_plan["path"], "block_id": block_id, "sections": desired}
            )

    refreshed = structure(slug)
    for result in results:
        page = page_for_path(refreshed, result["path"])
        block = next(
            (
                candidate
                for candidate in page.get("blocks", [])
                if candidate.get("_id") == result["block_id"]
            ),
            None,
        ) if page else None
        if block is None:
            raise RuntimeError("newStore block disappeared during catalog verification")
        actual = [
            store_section_identity(component) for component in block.get("components", [])
        ]
        if actual != desired:
            raise RuntimeError(
                f"catalog reconciliation failed on {result['path']}: {actual}"
            )
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("brief", type=Path)
    parser.add_argument("--confirmation-id", required=True)
    parser.add_argument("--backup-dir", type=Path)
    parser.add_argument("--approved-test-projects", type=Path)
    args = parser.parse_args()
    try:
        brief = load_brief(args.brief)
        errors = validate(brief)
        if errors:
            raise RuntimeError("invalid shop brief: " + "; ".join(errors))
        run_preflight(args.brief, args.approved_test_projects)

        expected = brief["project"]
        config = data(run_json("config", "list"))
        if not isinstance(config, dict):
            raise RuntimeError("xsolla config list returned an unexpected shape")
        if config.get("merchant_id") != expected["merchant_id"]:
            raise RuntimeError("CLI merchant_id does not match the shop brief")
        if config.get("project_id") != expected["project_id"]:
            raise RuntimeError("CLI project_id does not match the shop brief")
        if (config.get("sandbox") is True) != (expected["environment"] == "sandbox"):
            raise RuntimeError("CLI sandbox setting does not match the shop brief")
        RUN_AUTH["context"] = cli_context(config)

        slug = brief["site"]["slug"]
        ops_mode = "block_operations" in brief
        existed = website_exists(run_json("shopbuilder", "list-websites"), slug)
        if ops_mode and not existed:
            raise RuntimeError("block operations need an existing site")
        if existed:
            if args.backup_dir is None:
                raise RuntimeError("--backup-dir is required for an existing target")
            if not verified_backup(args.backup_dir, expected, slug):
                raise RuntimeError(
                    "a complete verified backup created before confirmation is required"
                )
            saved_structure = backup_structure(args.backup_dir)
            plan = build_plan(brief, saved_structure)
        else:
            plan = build_plan(brief)

        if args.confirmation_id != plan["confirmation_id"]:
            raise RuntimeError("confirmation ID does not match the current plan")

        if existed:
            current = structure(slug)
            if structure_hash(current) != structure_hash(saved_structure):
                raise RuntimeError(
                    "target structure changed after backup; back up, re-render, and reconfirm"
                )
            if ops_mode:
                landing_id = current.get("_id")
                if not isinstance(landing_id, str):
                    raise RuntimeError("landing has no _id")
                refs: dict = {}
                try:
                    applied = apply_block_operations(slug, landing_id, plan, refs)
                    after = structure(slug)
                    problems = verify_block_operations(
                        plan,
                        after,
                        data(run_json("shopbuilder", "get-localization", "--slug", slug)),
                        refs,
                    )
                    if problems:
                        raise RuntimeError("verification failed: " + "; ".join(problems))
                except RuntimeError as exc:
                    raise RuntimeError(
                        "block operations may be partly applied, so do not rerun this "
                        "plan: back up again, inspect the site and re-render. Created "
                        f"blocks: {refs or 'none'}. Cause: {exc}"
                    ) from exc
                warnings = [
                    f"deleted block {block_id} is still listed in the landing blocks[]; "
                    "the CLI cannot clear it"
                    for block_id in landing_leftovers(plan, after)
                ]
                print(
                    json.dumps(
                        {
                            "operation_succeeded": True,
                            "assembly_complete": True,
                            "status": "block-operations-applied",
                            "confirmation_id": plan["confirmation_id"],
                            "slug": slug,
                            "landing_id": landing_id,
                            "operations": applied,
                            "created_blocks": refs,
                            "verified": True,
                            "warnings": warnings,
                            "published": False,
                        },
                        indent=2,
                    )
                )
                return 0
            extra_pages = plan["current_state"]["extra_pages"]
            if extra_pages:
                paths = ", ".join(page["path"] for page in extra_pages)
                raise RuntimeError(
                    "target contains pages outside the confirmed plan and the CLI cannot "
                    f"delete pages safely: {paths}"
                )
        else:
            run_json(
                "shopbuilder",
                "create-website",
                "--name",
                brief["site"]["name"],
                "--slug",
                slug,
                "--type",
                "topup",
            )

        current = structure(slug)
        if current.get("type") is None:
            run_json(
                "shopbuilder", "set-landing-type", "--slug", slug, "--type", "store"
            )
            current = structure(slug)
        if current.get("type") != "store":
            raise RuntimeError(
                f"target landing type is {current.get('type')!r}, expected 'store'"
            )
        landing_id = current.get("_id")
        if not isinstance(landing_id, str):
            raise RuntimeError("landing has no _id")

        created_pages = add_missing_pages(slug, plan["pages"])
        locales = ensure_locales(slug, plan["locales"])
        if not existed:
            print(
                json.dumps(
                    {
                        "operation_succeeded": True,
                        "assembly_complete": False,
                        "status": "bootstrap-complete",
                        "confirmation_id": plan["confirmation_id"],
                        "slug": slug,
                        "landing_id": landing_id,
                        "created_pages": created_pages,
                        "locales": locales,
                        "next_action": (
                            "Back up the generated site, render a target-bound plan, "
                            "and explicitly confirm its exact removals before reconciliation."
                        ),
                        "published": False,
                    },
                    indent=2,
                )
            )
            return 0

        if created_pages:
            print(
                json.dumps(
                    {
                        "operation_succeeded": True,
                        "assembly_complete": False,
                        "status": "page-phase-complete",
                        "confirmation_id": plan["confirmation_id"],
                        "slug": slug,
                        "landing_id": landing_id,
                        "created_pages": created_pages,
                        "locales": locales,
                        "next_action": (
                            "Back up the changed site, re-render its generated block IDs, "
                            "and explicitly confirm before block reconciliation."
                        ),
                        "published": False,
                    },
                    indent=2,
                )
            )
            return 0

        pages = [reconcile_page(slug, landing_id, page) for page in plan["pages"]]
        navigation = apply_navigation(slug, landing_id, plan)
        catalog_links = wire_catalog_sections(slug, landing_id, plan)
        print(
            json.dumps(
                {
                    "operation_succeeded": True,
                    "assembly_complete": not plan["unsupported_phases"],
                    "status": "implemented-phases-applied",
                    "confirmation_id": plan["confirmation_id"],
                    "slug": slug,
                    "landing_id": landing_id,
                    "site_existed": existed,
                    "pages": pages,
                    "navigation": navigation,
                    "catalog_links": catalog_links,
                    "locales": locales,
                    "completed_phases": plan["implemented_phases"],
                    "pending_phases": plan["unsupported_phases"],
                    "warnings": (
                        [CUSTOM_CODE_WARNING]
                        if any(page.get("hidden_custom_code") for page in pages)
                        else []
                    ),
                    "published": False,
                },
                indent=2,
            )
        )
        return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Apply failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
