#!/usr/bin/env python3
"""Execute a listing-import plan against a landing.

The only entry point in this skill that writes. Default is a rehearsal:

    apply_plan.py --plan plan.json --slug my-landing            # prints, writes nothing
    apply_plan.py --plan plan.json --slug my-landing --yes      # writes

``--yes`` is the whole gate. Without it every command is assembled and printed
and nothing is invoked, so a forgotten flag costs a paragraph of output rather
than a partner's shop.

Three things it refuses to do, each reported rather than guessed:

* write to a localization id the block does not carry
* invent a block component for the overflow copy
* invoke anything outside ``apply.ALLOWED`` -- no publish, no delete

Exit status: ``0`` everything applied or rehearsed, ``1`` something failed or
was skipped, ``2`` bad invocation or a refused guard.
"""

from __future__ import annotations

import argparse
import json
import sys

from xsolla_listing_import import apply as applier

EXIT_CLEAN = 0
EXIT_PROBLEMS = 1
EXIT_USAGE = 2


def _render(outcome, plan):
    slug = outcome["slug"]
    if not outcome["confirmed"]:
        print("REHEARSAL — nothing was sent. Add --yes to write.")
    else:
        print("Applied to %s" % slug)
        if outcome["backup"]:
            print("  backup: %s" % ", ".join(sorted(outcome["backup"].values())))
    print("")

    if not outcome["confirmed"]:
        print("Commands, in order (%d):" % len(outcome["commands"]))
        for index, cmd in enumerate(outcome["commands"], start=1):
            rendered = " ".join(cmd[:2])
            print("  %2d. xsolla %s" % (index, rendered))
        print("")

    if outcome["performed"]:
        print("Applied (%d):" % len(outcome["performed"]))
        for row in outcome["performed"]:
            label = row.get("field") or row.get("sku")
            print("  %-22s %s" % (label, row.get("verified", "")))
        print("")

    if outcome["skipped"]:
        print("Skipped (%d) — these need a human:" % len(outcome["skipped"]))
        for row in outcome["skipped"]:
            print("  %-22s %s" % (row.get("field"), row["reason"]))
        print("")

    if outcome["failed"]:
        print("Failed (%d):" % len(outcome["failed"]))
        for row in outcome["failed"]:
            label = row.get("field") or row.get("sku")
            print("  %-22s %s" % (label, row["reason"]))
        print("")

    for line in plan.get("catalog_warnings") or []:
        print("note: %s" % line)
    if plan.get("catalog_warnings"):
        print("")

    print("Never publish from here. A human publishes, in Publisher Account.")


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="apply_plan.py",
        description="Execute a listing-import plan. Rehearses unless --yes.",
    )
    parser.add_argument("--plan", required=True, help="output of `listing_import.py plan`")
    parser.add_argument("--slug", required=True, help="the landing to write to")
    parser.add_argument("--locale", default="en-US")
    parser.add_argument("--yes", action="store_true",
                        help="actually write. Without this nothing is sent.")
    parser.add_argument("--backup-dir", help="where to keep the pre-write backup")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        with open(args.plan, "r", encoding="utf-8") as handle:
            document = json.load(handle)
    except (OSError, ValueError) as exc:
        print("could not read the plan: %s" % exc, file=sys.stderr)
        return EXIT_USAGE

    # Accept either the plan itself or the `listing_import.py plan` envelope.
    blockers = document.get("blockers") if isinstance(document, dict) else None
    plan = document.get("plan", document) if isinstance(document, dict) else None
    if not isinstance(plan, dict) or "operations" not in plan:
        print("that file does not look like a plan (no operations)", file=sys.stderr)
        return EXIT_USAGE

    if blockers:
        print("REFUSED — the plan carries %d blocker(s):" % len(blockers))
        for item in blockers:
            print("  %s: expected %s, got %s"
                  % (item.get("path"), item.get("expected"), item.get("got")))
        print("")
        print("Resolve these and re-plan. Nothing was sent.")
        return EXIT_USAGE

    try:
        outcome = applier.apply_plan(plan, args.slug, locale=args.locale,
                                     confirmed=args.yes, backup_dir=args.backup_dir)
    except applier.Refused as exc:
        print("REFUSED — %s" % exc, file=sys.stderr)
        return EXIT_USAGE

    if args.json:
        print(json.dumps(outcome, indent=2))
    else:
        _render(outcome, plan)
    return EXIT_PROBLEMS if (outcome["failed"] or outcome["skipped"]) else EXIT_CLEAN


if __name__ == "__main__":
    sys.exit(main())
