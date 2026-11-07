#!/usr/bin/env python3
"""Check a plan against the manifest before any write. Any error stops the batch with zero writes.

The page models are derived again from the manifest, the backup's structure and the batch rows
the plan carries, so a plan can't widen what the manifest allows. Each error has a category:
outside_manifest, style, custom_code, hand_typed, binding, row, incomplete or other.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import plan_model  # noqa: E402
import xla_common as common  # noqa: E402

OPS = (
    "create_page",
    "add_data_connection",
    "add_block",
    "set_block_field",
    "bind_field",
    "hide_block",
    "set_page_seo",
    "set_page_look",
)
STYLE = re.compile(r"theme|style|css|font|colou?r|radius|spacing|padding|margin|background|gap|width|look", re.I)
CUSTOM = re.compile(r"html|script|custom|iframe|tracker|bundle", re.I)
PAGE_TYPES = ("game", "payment_provider", "combined")


def error(category: str, message: str) -> dict:
    return {"category": category, "message": message}


def unknown_op(op: dict) -> dict:
    text = json.dumps(op, sort_keys=True)
    name = op.get("op")
    if STYLE.search(str(name)) or (STYLE.search(text) and not CUSTOM.search(str(name))):
        return error("style", f"{name!r} is a theme or style write, which the manifest forbids")
    if CUSTOM.search(text):
        return error("custom_code", f"{name!r} adds custom code, which the manifest forbids")
    return error("other", f"{name!r} is not a write this skill makes")


def check_page(manifest: dict, config: dict, structure: dict, planned: dict, rows: dict) -> list[dict]:
    errors: list[dict] = []
    type_name = planned.get("page_type")
    route = planned.get("route")
    if type_name not in PAGE_TYPES:
        return [error("other", f"{route}: {type_name!r} is not a page type in the manifest")]
    provider = planned.get("provider")
    row = rows.get(provider) if provider else None
    if type_name != "game" and row is None:
        return [error("row", f"{route}: the batch has no row for provider {provider!r}")]
    if route != common.route_for(manifest, type_name, provider):
        return [error("other", f"{route} is not the {type_name} route for {provider!r}")]
    existing = common.find_page(structure, route)
    expected, model_errors, _ = plan_model.desired_page(manifest, config, structure, type_name, row, existing)
    errors += [error("other", f"{route}: {message}") for message in model_errors]
    if planned.get("expected") != expected:
        errors.append(error("other", f"{route}: the plan's page model is not the manifest's page"))
    action = planned.get("action")
    if (action == "create") != (existing is None):
        errors.append(error("other", f"{route}: action {action!r} doesn't match the site"))

    blocks = {block["key"]: block for block in expected["blocks"]}
    by_package = {block["package"]: block for block in expected["blocks"]}
    connections = {conn["key"]: conn for conn in expected["connections"]}
    existing_packages = {common.block_identity(b)[0] for b in (existing or {}).get("blocks") or []}
    added: list[str] = []
    bound: set[tuple[str, str]] = set()
    connected: set[str] = set()
    for op in planned.get("ops") or []:
        name = op.get("op") if isinstance(op, dict) else None
        if name not in OPS:
            errors.append(unknown_op(op if isinstance(op, dict) else {"op": op}))
            continue
        if op.get("route") != route:
            errors.append(error("other", f"{route}: a {name} op names route {op.get('route')!r}"))
            continue
        key = op.get("key")
        if name == "create_page":
            paths = next((c for c in expected["connections"] if c["kind"] == "path"), None)
            want = {"provider": paths["provider"], "input": paths["input"]} if paths else None
            if action != "create" or op.get("kind") != expected["kind"] or op.get("paths") != want:
                errors.append(error("other", f"{route}: create_page doesn't match the manifest's {type_name} page"))
        elif name == "add_block":
            package = op.get("package")
            want = blocks.get(key)
            if want is None or package != want["package"] or package not in by_package:
                errors.append(error(
                    "outside_manifest",
                    f"{route}: {package or key} is not a block the manifest lists for {type_name} pages",
                ))
                continue
            if package in added or package in existing_packages:
                errors.append(error("outside_manifest", f"{route}: {package} would be on the page twice"))
                continue
            if op.get("version") != want["version"]:
                errors.append(error(
                    "other", f"{route}: {package}@{op.get('version')} is not the reference page's {want['version']}"
                ))
            if action != "create" and want["bindings"]:
                errors.append(error(
                    "binding", f"{route}: adding {package} on an existing page would change its data bindings"
                ))
            added.append(package)
        elif name == "set_block_field":
            field = op.get("field")
            want = blocks.get(key)
            if want is None:
                errors.append(error("outside_manifest", f"{route}: {key!r} is not a block on {type_name} pages"))
            elif field in want["bindings"]:
                errors.append(error(
                    "hand_typed", f"{route}: {key}.{field} must be bound, not typed (game data comes from the API)"
                ))
            elif field not in want["fields"]:
                category = "style" if STYLE.search(str(field)) else "custom_code" if CUSTOM.search(str(field)) else "other"
                errors.append(error(category, f"{route}: {key}.{field} is not a field the manifest lets the plan write"))
            elif op.get("value") != want["fields"][field]:
                errors.append(error("row", f"{route}: {key}.{field} is not the value the row and manifest give"))
        elif name == "bind_field":
            want = blocks.get(key)
            field = op.get("field")
            bind = (want or {}).get("bindings", {}).get(field)
            if action != "create":
                errors.append(error("binding", f"{route}: a binding on an existing page would change its bindings"))
            elif bind is None or (op.get("source"), op.get("output")) != (bind["source"], bind["output"]):
                errors.append(error("binding", f"{route}: {key}.{field} binding is not the manifest's"))
            else:
                bound.add((key, field))
        elif name == "hide_block":
            want = blocks.get(key)
            if want is None or want["required"] or not want["hidden"]:
                errors.append(error("other", f"{route}: only an optional block with no content is hidden ({key})"))
        elif name == "set_page_seo":
            field = op.get("field")
            want = expected["seo"].get(field)
            given = {k: op[k] for k in ("value", "source", "output") if k in op}
            if type_name == "payment_provider" and "source" in op:
                errors.append(error("binding", f"{route}: a static page's SEO must not reference a data provider"))
            elif want is None or given != want:
                errors.append(error("other", f"{route}: seo {field} is not the manifest's"))
        elif name == "set_page_look":
            if key not in common.PAGE_LOOK_KEYS or key not in expected["look"] or op.get("value") != expected["look"][key]:
                errors.append(error(
                    "style", f"{route}: page {key} may only be set to the reference page's value"
                ))
        elif name == "add_data_connection":
            want = connections.get(key)
            given = {k: op.get(k) for k in ("provider", "kind", "input")}
            if action != "create":
                errors.append(error("binding", f"{route}: a new data connection would change an existing page"))
            elif want is None or want["linked"] or given != {k: want[k] for k in ("provider", "kind", "input")}:
                errors.append(error("binding", f"{route}: data connection {key!r} is not the manifest's"))
            else:
                connected.add(key)

    if action == "create":
        if [p for p in added] != [block["package"] for block in expected["blocks"]]:
            errors.append(error(
                "incomplete", f"{route}: the plan must add {[b['package'] for b in expected['blocks']]} in that order"
            ))
        missing = [
            f"{block['key']}.{field}" for block in expected["blocks"]
            for field in block["bindings"] if (block["key"], field) not in bound
        ]
        if missing:
            errors.append(error("incomplete", f"{route}: bindings missing from the plan: {', '.join(missing)}"))
        unconnected = [k for k, c in connections.items() if c["kind"] == "value" and not c["linked"] and k not in connected]
        if unconnected:
            errors.append(error("incomplete", f"{route}: data connections missing from the plan: {', '.join(unconnected)}"))
    return errors


def validate(plan: dict, manifest: dict, config: dict, structure: dict) -> list[dict]:
    structure = common.data(structure)
    if not isinstance(plan, dict) or not isinstance(plan.get("pages"), list):
        return [error("other", "the plan has no pages")]
    rows, row_errors = plan_model.batch_rows({"providers": plan.get("rows")})
    errors = [error("row", message) for message in row_errors]
    by_provider = {row.get("provider"): row for row in rows if isinstance(row, dict)}
    routes = [page.get("route") for page in plan["pages"]]
    for route in sorted({r for r in routes if routes.count(r) > 1}):
        errors.append(error("other", f"{route} is in the plan twice"))
    for planned in plan["pages"]:
        if not isinstance(planned, dict):
            errors.append(error("other", "a plan page must be an object"))
            continue
        errors += check_page(manifest, config, structure, planned, by_provider)
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--structure", required=True, type=Path, help="the backup's structure.json")
    parser.add_argument("--config", type=Path, default=common.DEFAULT_CONFIG)
    args = parser.parse_args(argv)
    try:
        errors = validate(
            common.load_json(args.plan, "plan"),
            common.load_manifest(),
            common.load_config(args.config),
            common.load_json(args.structure, "structure"),
        )
    except (OSError, ValueError) as exc:
        print(f"Validation failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"ok": not errors, "errors": errors}, indent=2, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
