#!/usr/bin/env python3
"""The write gate: does the installed CLI's --help list every command and flag the plan needs?

It reads `xsolla <command> --help` only. The CLI version number is never checked. The commands
and flags are the ones specified in references/cli-gaps.md; until the CLI ships them, the gate
fails and nothing is written.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import xla_common as common  # noqa: E402

# capability -> (command, flags its --help must list). Keep in step with references/cli-gaps.md.
CAPABILITIES = {
    "add-page": (("shopbuilder", "add-page"), ("--slug", "--name", "--path")),
    "add-page-dynamic": (("shopbuilder", "add-page"), ("--paths-provider", "--provider-input")),
    "add-block-pinned": (
        ("shopbuilder", "add-block"),
        ("--landing-id", "--page-id", "--block", "--package", "--version", "--index"),
    ),
    "update-block": (("shopbuilder", "update-block"), ("--landing-id", "--data")),
    "add-data-connection": (
        ("shopbuilder", "add-data-connection"),
        ("--landing-id", "--page-id", "--provider", "--input"),
    ),
    "bind-block-field": (
        ("shopbuilder", "bind-block-field"),
        ("--landing-id", "--block-id", "--field", "--connection-id", "--output"),
    ),
    "set-page-seo": (
        ("shopbuilder", "set-page-seo"),
        ("--landing-id", "--page-id", "--field", "--value", "--connection-id", "--output"),
    ),
}
# Used when present: a new page without the blocks add-page seeds (the plan deletes them otherwise).
OPTIONAL = {"add-page-empty": (("shopbuilder", "add-page"), ("--empty",))}


def needed(plan: dict) -> list[str]:
    """The capabilities the plan's writes need, in a stable order."""
    names: set[str] = set()
    for page in plan.get("pages") or []:
        for op in page.get("ops") or []:
            kind = op.get("op")
            if kind == "create_page":
                names |= {"add-page", "update-block"}
                if op.get("kind") == "dynamic":
                    names.add("add-page-dynamic")
            elif kind == "add_block":
                names.add("add-block-pinned")
            elif kind in ("set_block_field", "hide_block", "set_page_look"):
                names.add("update-block")
            elif kind == "add_data_connection":
                names.add("add-data-connection")
            elif kind == "bind_field":
                names.add("bind-block-field")
            elif kind == "set_page_seo":
                names.add("set-page-seo")
    return [name for name in CAPABILITIES if name in names]


def check(names: list[str], table: dict = CAPABILITIES) -> list[dict]:
    """Every capability in `names` that --help doesn't list, with what is missing."""
    help_cache: dict[tuple, str] = {}
    missing = []
    for name in names:
        command, flags = table[name]
        if command not in help_cache:
            help_cache[command] = common.execute_help(command)
        text = help_cache[command]
        if not common.has_command(text, command):
            missing.append({"capability": name, "command": "xsolla " + " ".join(command), "missing": ["the command"]})
            continue
        absent = [flag for flag in flags if not common.has_flag(text, flag)]
        if absent:
            missing.append({"capability": name, "command": "xsolla " + " ".join(command), "missing": absent})
    return missing


def has(name: str) -> bool:
    table = {**CAPABILITIES, **OPTIONAL}
    return not check([name], table)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--plan", type=Path, help="check what this plan's writes need")
    group.add_argument("--all", action="store_true", help="check every capability in references/cli-gaps.md")
    args = parser.parse_args(argv)
    try:
        names = list(CAPABILITIES) if args.all else needed(common.load_json(args.plan, "plan"))
    except (OSError, ValueError) as exc:
        print(f"Gate failed: {exc}", file=sys.stderr)
        return 1
    missing = check(names)
    print(json.dumps({"ok": not missing, "needed": names, "missing": missing}, indent=2))
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
