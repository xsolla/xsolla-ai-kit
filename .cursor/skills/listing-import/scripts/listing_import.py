#!/usr/bin/env python3
"""Command line entry point for the listing-to-shop mapping.

Exit status is the shell convention the rest of this kit's scripts use, so
several can be chained in one command: ``0`` clean, ``1`` something to fix,
``2`` bad invocation.

Subcommands:

``fetch``     what to fetch for a store URL, and how
``extract``   a store response or page into a listing.json
``validate``  the agent's listing.json against the schema
``coverage``  the field-coverage metric, split three ways
``preview``   the extracted-to-shop mapping, for the confirmation step
``plan``      the same mapping as ordered operations, for execution
``catalog``   the CLI commands that create the in-app items
``bbcode``    Steam BBCode to Shop Builder HTML, on its own

The only module that prints.  Everything it renders comes from the library,
which returns data -- so a report can be re-rendered differently without
touching a rule.
"""

from __future__ import annotations

import argparse
import json
import sys

from xsolla_listing_import import catalog as catalog_plan
from xsolla_listing_import import coverage as coverage_metric
from xsolla_listing_import import extract as extractor
from xsolla_listing_import import fields as field_model
from xsolla_listing_import import mapping, plan as planner
from xsolla_listing_import.bbcode import to_html
from xsolla_listing_import.listing_schema import validate as validate_listing

EXIT_CLEAN = 0
EXIT_ERRORS = 1
EXIT_USAGE = 2


def _load(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _print_errors(errors):
    for error in errors:
        line = "  %s: expected %s, got %s" % (
            error["path"], error["expected"], error["got"])
        print(line)


def _render_pct(ratio):
    if ratio["pct"] is None:
        return "n/a (nothing expected)"
    return "%5.1f%%  (%d/%d)" % (ratio["pct"], ratio["filled"], ratio["total"])


def cmd_validate(args):
    document = _load(args.listing)
    errors = validate_listing(document)
    if args.json:
        print(json.dumps({"ok": not errors, "errors": errors}, indent=2))
        return EXIT_ERRORS if errors else EXIT_CLEAN
    if not errors:
        print("listing.json is valid.")
        return EXIT_CLEAN
    print("%d problem(s) in %s:" % (len(errors), args.listing))
    _print_errors(errors)
    return EXIT_ERRORS


def cmd_coverage(args):
    document = _load(args.listing)
    report = coverage_metric.measure(document)
    if args.json:
        print(json.dumps(report, indent=2))
        return EXIT_CLEAN
    print("Field coverage — %s" % report["source_label"])
    print("")
    print("  extraction  %s  of the fields this source publishes"
          % _render_pct(report["extraction"]))
    print("  mapping     %s  of those, with somewhere native to go"
          % _render_pct(report["mapping"]))
    print("  delivered   %s  of the full target list, on the page"
          % _render_pct(report["delivered"]))
    print("")
    print("  The mapping ceiling for any run is %s — %s have no native block"
          % (_render_pct(report["mapping_ceiling"]),
             ", ".join(mapping.unmapped_fields())))
    if report["undeclared_missing"]:
        print("")
        print("  Missing, and not declared in not_found (look again, or declare):")
        for name in report["undeclared_missing"]:
            print("    - %s (%s publishes it: %s)"
                  % (name, report["source_label"],
                     field_model.availability(name, report["source"])))
    if report["manual_follow_up"]:
        print("")
        print("  Extracted, needs a human: %s" % ", ".join(report["manual_follow_up"]))
    return EXIT_CLEAN


def _preview_human(plan, blockers):
    print("Listing → shop mapping — %s" % plan["source_label"])
    print("  %s" % plan["source_url"])
    print("")
    if blockers:
        print("BLOCKED — nothing may be written until these clear:")
        _print_errors(blockers)
        print("")
    counts = plan["counts"]
    print("  %d localization write(s), %d overflow component(s), %d asset "
          "upload(s), %d companion patch(es), %d catalog item(s)"
          % (counts["localization"], counts["overflow"], counts["asset"],
             counts["patch"], counts["catalog"]))
    print("")
    # Deletes are listed separately and last, because they are the only
    # irreversible thing in a plan and a reader approving it has to see them as
    # their own decision rather than as line 34 of a long list.
    deletes = [op for op in plan["operations"] if op["kind"] == "delete"]
    for op in [o for o in plan["operations"] if o["kind"] != "delete"]:
        path = ".".join(str(segment) for segment in op["path"] or [])
        flag = "" if op["confidence"] == mapping.CONFIRMED else "  [path unconfirmed]"
        print("  %2d. %-17s %-14s %s%s"
              % (op["step"], op["field"], op["module"], path, flag))
        if op["kind"] == "asset":
            print("      fetch %s → upload-asset → patch the CDN url"
                  % op["source_url"])
        elif op.get("value") is not None:
            # A companion patch's value is a bool, not copy -- str() first.
            preview = str(op["value"]).replace("\n", " ")
            if len(preview) > 68:
                preview = preview[:65] + "..."
            print("      %s" % preview)
        for item in op.get("dropped") or []:
            print("      dropped: %s" % item)
    if deletes:
        print("")
        print("  REMOVES %d block(s) — the listing publishes nothing they can"
              % len(deletes))
        print("  show. Recoverable only from the backup taken before the first")
        print("  write:")
        for op in deletes:
            print("    - %-16s %s" % (op["module"], op["block_id"]))
    if plan["catalog_operations"]:
        print("")
        print("  Catalog — in-app items, created as priced virtual items:")
        for op in plan["catalog_operations"]:
            price = op["prices"][0] if op["prices"] else None
            shown = ("%s %s" % (price["amount"], price["currency"])) if price \
                else "no price"
            print("    - %-46s %s" % (op["sku"], shown))
        for warning in plan["catalog_warnings"]:
            print("      note: %s" % warning)
    if plan["unresolved"]:
        print("")
        print("  Not placed:")
        for item in plan["unresolved"]:
            # The plan records why; print that rather than a stock phrase. The
            # earlier version said "wants a <module> block" for every entry,
            # which reported a full gallery as a missing one.
            print("    - %-13s %s" % (item["field"], item["reason"]))
    if plan["manual_follow_up"]:
        print("")
        print("  Manual follow-up — extracted, but no block field exists:")
        for item in plan["manual_follow_up"]:
            print("    - %-13s %s" % (item["field"], item["note"]))
    if plan["unverified"]:
        print("")
        print("  Unverified by this run:")
        for item in plan["unverified"]:
            print("    - %s" % item)
    print("")
    if blockers:
        print("Resolve the blockers, re-run, then ask for confirmation.")
    else:
        print("Show this to the user and get explicit confirmation before writing.")


def cmd_preview(args):
    document = _load(args.listing)
    schema_errors = validate_listing(document)
    if schema_errors:
        print("listing.json is not valid; fix it before previewing a write:")
        _print_errors(schema_errors)
        return EXIT_ERRORS
    localization = _load(args.localization) if args.localization else None
    plan, blockers = planner.build(document, _load(args.structure), localization)
    if args.json:
        print(json.dumps({"ok": not blockers, "blockers": blockers, "plan": plan},
                         indent=2))
        return EXIT_ERRORS if blockers else EXIT_CLEAN
    _preview_human(plan, blockers)
    return EXIT_ERRORS if blockers else EXIT_CLEAN


def cmd_plan(args):
    document = _load(args.listing)
    schema_errors = validate_listing(document)
    if schema_errors:
        print(json.dumps({"ok": False, "errors": schema_errors}, indent=2))
        return EXIT_ERRORS
    localization = _load(args.localization) if args.localization else None
    plan, blockers = planner.build(document, _load(args.structure), localization)
    print(json.dumps({"ok": not blockers, "blockers": blockers, "plan": plan},
                     indent=2))
    return EXIT_ERRORS if blockers else EXIT_CLEAN


def cmd_fetch(args):
    source, url, kind = extractor.fetch_hint(args.url)
    if args.json:
        print(json.dumps({"source": source, "fetch_url": url, "kind": kind},
                         indent=2))
        return EXIT_CLEAN
    print("source:    %s" % field_model.SOURCE_LABELS.get(source, source))
    print("fetch:     %s" % url)
    print("as:        %s" % kind)
    if source == field_model.APP_STORE:
        print("")
        print("Also fetch the store page itself for the in-app purchase list —")
        print("Apple's API does not publish one. Pass it with --iap.")
    return EXIT_CLEAN


def cmd_extract(args):
    with open(args.input, "r", encoding="utf-8") as handle:
        raw = handle.read()
    iap_items = _load(args.iap) if args.iap else None
    dlc = _load(args.dlc) if args.dlc else None
    document = extractor.to_listing(raw, args.url, iap_items=iap_items,
                                    dlc_details=dlc)
    errors = validate_listing(document)
    if errors:
        print("extraction produced an invalid document:", file=sys.stderr)
        for error in errors:
            print("  %s: expected %s, got %s"
                  % (error["path"], error["expected"], error["got"]),
                  file=sys.stderr)
        return EXIT_ERRORS
    print(json.dumps(document, indent=2, ensure_ascii=False))
    print("", file=sys.stderr)
    print("rights_confirmed is false. Ask the partner whether this is their own "
          "game's listing, and set it only on a yes.", file=sys.stderr)
    return EXIT_CLEAN


def cmd_catalog(args):
    document = _load(args.listing)
    items = (document.get("fields") or {}).get("iap_items") or []
    if not items:
        print("No in-app items in this listing; nothing to create.")
        return EXIT_CLEAN
    operations, warnings = catalog_plan.build_operations(items, document.get("source"))
    if args.json:
        print(json.dumps({"operations": operations, "warnings": warnings}, indent=2))
        return EXIT_CLEAN
    print(catalog_plan.render_commands(operations))
    print("")
    for warning in warnings:
        print("# %s" % warning)
    return EXIT_CLEAN


def cmd_bbcode(args):
    with open(args.file, "r", encoding="utf-8") as handle:
        source = handle.read()
    html, dropped = to_html(source)
    if args.json:
        print(json.dumps({"html": html, "dropped": dropped}, indent=2))
        return EXIT_CLEAN
    print(html)
    if dropped:
        print("", file=sys.stderr)
        print("dropped: %s" % ", ".join(dropped), file=sys.stderr)
    return EXIT_CLEAN


def build_parser():
    parser = argparse.ArgumentParser(
        prog="listing_import.py",
        description="Map a store listing onto a Shop Builder landing.",
    )
    subparsers = parser.add_subparsers(dest="command")

    validate = subparsers.add_parser("validate", help="check listing.json")
    validate.add_argument("--listing", required=True)
    validate.add_argument("--json", action="store_true")
    validate.set_defaults(handler=cmd_validate)

    cov = subparsers.add_parser("coverage", help="the field-coverage metric")
    cov.add_argument("--listing", required=True)
    cov.add_argument("--json", action="store_true")
    cov.set_defaults(handler=cmd_coverage)

    preview = subparsers.add_parser("preview",
                                    help="the mapping, for the confirmation step")
    preview.add_argument("--listing", required=True)
    preview.add_argument("--structure", required=True)
    preview.add_argument("--localization")
    preview.add_argument("--json", action="store_true")
    preview.set_defaults(handler=cmd_preview)

    plan_cmd = subparsers.add_parser("plan", help="ordered operations, as JSON")
    plan_cmd.add_argument("--listing", required=True)
    plan_cmd.add_argument("--structure", required=True)
    plan_cmd.add_argument("--localization")
    plan_cmd.set_defaults(handler=cmd_plan)

    fetch = subparsers.add_parser("fetch", help="what to fetch for a store URL")
    fetch.add_argument("--url", required=True)
    fetch.add_argument("--json", action="store_true")
    fetch.set_defaults(handler=cmd_fetch)

    ext = subparsers.add_parser("extract", help="store response/page to listing.json")
    ext.add_argument("--input", required=True,
                     help="the already-fetched JSON body or page HTML")
    ext.add_argument("--url", required=True, help="the public store page URL")
    ext.add_argument("--iap", help="JSON array of in-app items (App Store only)")
    ext.add_argument("--dlc", help="JSON array of Steam appdetails responses for "
                                   "the ids in dlc[] — without these the edition "
                                   "list is only the page's buy options")
    ext.set_defaults(handler=cmd_extract)

    cat = subparsers.add_parser("catalog", help="commands to create the in-app items")
    cat.add_argument("--listing", required=True)
    cat.add_argument("--json", action="store_true")
    cat.set_defaults(handler=cmd_catalog)

    bbcode_cmd = subparsers.add_parser("bbcode", help="Steam BBCode to HTML")
    bbcode_cmd.add_argument("--file", required=True)
    bbcode_cmd.add_argument("--json", action="store_true")
    bbcode_cmd.set_defaults(handler=cmd_bbcode)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "handler", None):
        parser.print_help()
        return EXIT_USAGE
    try:
        return args.handler(args)
    except (OSError, ValueError) as exc:
        print("could not read input: %s" % exc, file=sys.stderr)
        return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
