#!/usr/bin/env python3
"""``validate-shop`` -- the executable gate for Xsolla Shop Builder blocks.

Runs the same rules the ``shop-validation`` skill documents, as code, so a run
has a measurable outcome and an exit status instead of a judgement.

    validate_shop.py site   --structure structure.json [--localization loc.json]
                            [--off-page-blocks dir_or_file] [--json]
    validate_shop.py block  --module faq --payload payload.json [--update]
                            [--version 2] [--json]
    validate_shop.py ai-code --component block.jsx [--settings settings.jsx]
                            [--text-fields fields.json] [--json]
    validate_shop.py ai-block --block ai-block.json [--json]
    validate_shop.py patch  --change-set change-set.json [--json]

Exit status: ``0`` clean, ``1`` errors, ``2`` bad invocation.  Nothing here
writes anything -- every input is a file you already fetched.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from xsolla_shop_validation.ai_block import check_text_refs, collect_violations
from xsolla_shop_validation.component_checks import ValidationContext
from xsolla_shop_validation.errors import MISSING
from xsolla_shop_validation.federated import validate_federated
from xsolla_shop_validation.native import (
    FEDERATED_MODULE,
    max_version,
    validate_native,
)
from xsolla_shop_validation.site_walk import route_block, walk_site
from xsolla_shop_validation.write_constraints import (
    check_batch_change_set,
    check_create_version,
    check_not_layout_create,
    check_protected_fields,
    expand_dotted_keys,
)

EXIT_CLEAN = 0
EXIT_FINDINGS = 1
EXIT_USAGE = 2


def _load_json(path):
    with open(path, "r") as handle:
        return json.load(handle)


def _load_text(path):
    with open(path, "r") as handle:
        return handle.read()


def _load_off_page(path):
    """A directory of ``<blockId>.json`` files, or one ``{id: block}`` file."""
    if path is None:
        return {}
    if os.path.isdir(path):
        blocks = {}
        for name in sorted(os.listdir(path)):
            if not name.endswith(".json"):
                continue
            block = _load_json(os.path.join(path, name))
            block_id = block.get("_id") or os.path.splitext(name)[0]
            blocks[block_id] = block
        return blocks
    loaded = _load_json(path)
    if isinstance(loaded, list):
        return {b.get("_id"): b for b in loaded if isinstance(b, dict)}
    if isinstance(loaded, dict) and loaded.get("_id"):
        return {loaded["_id"]: loaded}
    return loaded or {}


def cmd_site(args):
    structure = _load_json(args.structure)
    localization = _load_json(args.localization) if args.localization else None
    off_page = _load_off_page(args.off_page_blocks)
    context = ValidationContext(
        site=structure,
        skus=_load_json(args.skus) if args.skus else None,
        bundles=_load_json(args.bundles) if args.bundles else None,
    )
    return walk_site(structure, localization, off_page, context)


def cmd_block(args):
    payload = expand_dotted_keys(_load_json(args.payload))
    module = args.module
    report = {"module": module, "mode": "update" if args.update else "create", "errors": [], "unverified": []}

    if not args.update:
        report["errors"].extend(check_not_layout_create(module))
    if args.update:
        report["errors"].extend(check_protected_fields(payload))

    if module == FEDERATED_MODULE:
        values = payload.get("values") if isinstance(payload, dict) else None
        values = values if isinstance(values, dict) else payload if isinstance(payload, dict) else {}
        internal = values.get("internalBlockValues", MISSING)
        defaults = values.get("defaultData", MISSING)
        result = validate_federated(internal, defaults)
        report["errors"].extend(result["errors"])
        report["family"] = route_block({"module": module, "values": values})
        if not result["walked"]:
            report["unverified"].append(
                "federated walk skipped -- no internalBlockValues or no defaultData to compare against"
            )
        report["unverified"].append(
            "federated walk compares types only: required fields, enums and array item shapes "
            "are not enforced"
        )
    else:
        result = validate_native(module, payload, partial=args.update)
        report["family"] = "native"
        report["errors"].extend(result["errors"])
        for advisory in result.get("advisories") or []:
            report["unverified"].append(
                "%s: %s -- the shipped schema requires this key, but the API accepts a create "
                "without it (verified live), so it is advisory" % (advisory["path"], advisory["expected"])
            )
        if not result["schema_available"]:
            report["unverified"].append(
                "module %r -- no field schema available, structure not checked" % module
            )
        if not args.update:
            version = args.version if args.version is not None else MISSING
            report["errors"].extend(check_create_version(module, version))
            report["max_version"] = max_version(module)
            if report["max_version"] is None:
                report["unverified"].append(
                    "module %r carries no versions list, so a create passes no version" % module
                )

    report["ok"] = not report["errors"]
    report["verdict"] = "clean" if report["ok"] else "%d error(s)" % len(report["errors"])
    return report


def cmd_ai_code(args):
    component = _load_text(args.component)
    settings = _load_text(args.settings) if args.settings else None
    text_fields = _load_json(args.text_fields) if args.text_fields else None
    violations = collect_violations(component, settings, text_fields)
    return {
        "errors": violations,
        "unverified": [
            "textual pattern checks only: a violation split across lines, generated "
            "dynamically, or hidden behind a helper will pass"
        ],
        "ok": not violations,
        "verdict": "clean" if not violations else "%d violation(s)" % len(violations),
    }


def cmd_ai_block(args):
    block = _load_json(args.block)
    source = block.get("aiSource") or {}
    component = source.get("block") or block.get("componentCode") or ""
    settings = source.get("settings") or block.get("settingsCode")
    text_fields = block.get("textFields")
    violations = collect_violations(component, settings, text_fields)
    violations.extend(check_text_refs(component, block.get("textRefs")))
    return {
        "errors": violations,
        "unverified": [],
        "ok": not violations,
        "verdict": "clean" if not violations else "%d violation(s)" % len(violations),
    }


def cmd_patch(args):
    errors = check_batch_change_set(_load_json(args.change_set))
    return {
        "errors": errors,
        "unverified": [],
        "ok": not errors,
        "verdict": "clean" if not errors else "%d error(s)" % len(errors),
    }


def _render(report):
    lines = []
    scope = report.get("scope")
    if scope:
        lines.append("Scope")
        for key in (
            "site",
            "landing_id",
            "pages",
            "blocks",
            "off_page_blocks",
            "dangling_ids",
            "localized_ids_checked",
            "image_ids_collected",
        ):
            if key in scope:
                lines.append("  %-22s %s" % (key, scope[key]))
        families = scope.get("families") or {}
        if families:
            lines.append(
                "  %-22s %s"
                % ("families", ", ".join("%s=%d" % kv for kv in sorted(families.items())))
            )
        lines.append("")

    errors = report.get("errors") or []
    if errors:
        by_category = {}
        for f in errors:
            default = "code" if "rule" in f else "error"
            by_category.setdefault(f.get("category") or default, []).append(f)
        summary = ", ".join("%s=%d" % (k, len(v)) for k, v in sorted(by_category.items()))
        lines.append("Errors (%d: %s)" % (len(errors), summary))
        for category in sorted(by_category):
            if len(by_category) > 1:
                lines.append("  -- %s --" % category)
            for f in by_category[category]:
                if "rule" in f:
                    lines.append("  [%s] %s" % (f["rule"], f["message"]))
                    lines.append("      fix: %s" % f["suggestion"])
                else:
                    where = f.get("block_id")
                    prefix = "  %s" % f.get("path")
                    if where:
                        prefix = "  %s @ %s" % (f.get("path"), where)
                    lines.append(prefix)
                    lines.append("      expected: %s" % f.get("expected"))
                    lines.append("      got:      %s" % f.get("got"))
                    if "value" in f:
                        lines.append("      value:    %s" % json.dumps(f["value"])[:200])
        lines.append("")
    else:
        lines.append("Errors: none")
        lines.append("")

    unverified = report.get("unverified") or []
    if unverified:
        lines.append("Not checked (%d)" % len(unverified))
        for note in unverified:
            lines.append("  - %s" % note)
        lines.append("")

    lines.append("Verdict: %s" % report.get("verdict"))
    return "\n".join(lines)


def main(argv=None):
    # ``--json`` is accepted on either side of the subcommand: typing it after
    # the subcommand is the natural thing to do and failing there is a pointless
    # papercut in a tool people run from a shell.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="emit the report as JSON")

    parser = argparse.ArgumentParser(
        description="Validate Xsolla Shop Builder blocks and sites.", parents=[common]
    )
    sub = parser.add_subparsers(dest="command")

    p_site = sub.add_parser("site", help="whole-site walk", parents=[common])
    p_site.add_argument("--structure", required=True, help="xsolla shopbuilder get-structure --json")
    p_site.add_argument("--localization", help="xsolla shopbuilder get-localization --json")
    p_site.add_argument("--off-page-blocks", help="directory of get-block payloads, or one JSON file")
    p_site.add_argument("--skus", help="JSON array of catalog SKUs, for buy-action checks")
    p_site.add_argument("--bundles", help="JSON array of bundle SKUs")
    p_site.set_defaults(func=cmd_site)

    p_block = sub.add_parser("block", help="one block payload, before a write", parents=[common])
    p_block.add_argument("--module", required=True)
    p_block.add_argument("--payload", required=True)
    p_block.add_argument("--update", action="store_true", help="a patch, not a create")
    p_block.add_argument("--version", type=int, help="the version the create will pass")
    p_block.set_defaults(func=cmd_block)

    p_code = sub.add_parser("ai-code", help="the nine rules on custom-block source", parents=[common])
    p_code.add_argument("--component", required=True)
    p_code.add_argument("--settings")
    p_code.add_argument("--text-fields", help='JSON [{"name": ..., "default": ...}]')
    p_code.set_defaults(func=cmd_ai_code)

    p_ai = sub.add_parser("ai-block", help="a fetched custom block (get-ai-block --json)", parents=[common])
    p_ai.add_argument("--block", required=True)
    p_ai.set_defaults(func=cmd_ai_block)

    p_patch = sub.add_parser("patch", help="a batch-API change set", parents=[common])
    p_patch.add_argument("--change-set", required=True)
    p_patch.set_defaults(func=cmd_patch)

    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return EXIT_USAGE

    report = args.func(args)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=False))
    else:
        print(_render(report))
    return EXIT_CLEAN if report.get("ok") else EXIT_FINDINGS


if __name__ == "__main__":
    sys.exit(main())
