#!/usr/bin/env python3
"""Check the ledger steps this skill writes: the contract's shape and only its statuses."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# The onboarding contract's statuses (nocode-shop-setup/references/onboarding-contract.md). A step
# that is under way has no status key at all.
STATUSES = ("completed", "placeholder", "needs_input", "needs_access", "needs_human",
            "blocked_capability", "failed")

# The contract's steps ("Steps and their evidence"). A gap goes in a step's evidence, never in
# a step of its own.
STEPS = ("intake", "plan", "merchant", "catalog", "login", "storefront", "verify", "review",
         "handoff")

# Steps nocode-shop-setup writes (the same table, "Done by"). They are not this skill's to fix, so the
# check skips them.
SKIPPED = ("intake", "plan")


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path} is not a JSON object")
    return value


def step_name(step: object, index: int) -> str:
    if isinstance(step, dict) and isinstance(step.get("id"), str) and step["id"]:
        return f"step {step['id']!r}"
    return f"steps[{index}]"


def checked_steps(ledger: dict) -> list[tuple[int, object]]:
    """The steps with their indexes, without the ones nocode-shop-setup writes."""
    return [(index, step) for index, step in enumerate(ledger["steps"])
            if not (isinstance(step, dict) and step.get("id") in SKIPPED)]


def problems(ledger: dict) -> list[str]:
    """Every way the steps this skill writes break the contract, each naming its step."""
    if not isinstance(ledger.get("steps"), list):
        return ["the ledger has no steps list"]
    found = []
    first: dict[str, int] = {}
    for index, step in checked_steps(ledger):
        name = step_name(step, index)
        if not isinstance(step, dict):
            found.append(f"{name}: must be an object")
            continue
        if not isinstance(step.get("id"), str) or not step["id"]:
            found.append(f"{name}: needs an id")
        elif step["id"] not in STEPS:
            found.append(
                f"{name}: is not a contract step ({', '.join(STEPS)}); put a gap in the "
                f"evidence of the contract step it belongs to"
            )
        elif step["id"] in first:
            # The contract's ledger holds one entry per step; a resume reads only one of them
            found.append(
                f"{name}: is in the ledger more than once (steps[{first[step['id']]}] and "
                f"steps[{index}]); update the existing entry instead of adding another"
            )
        else:
            first[step["id"]] = index
        if "status" in step and step["status"] not in STATUSES:
            found.append(
                f"{name}: status {json.dumps(step['status'])} is not a contract status "
                f"({', '.join(STATUSES)}); a step still under way has no status key"
            )
        if not isinstance(step.get("evidence"), list):
            found.append(f"{name}: evidence must be a list")
        if not isinstance(step.get("ids"), dict):
            found.append(f"{name}: ids must be an object")
        if not isinstance(step.get("updated_at"), str) or not step["updated_at"]:
            found.append(f"{name}: needs updated_at")
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check",))
    parser.add_argument("--ledger", required=True, type=Path, help=".xsolla/onboarding.json")
    args = parser.parse_args(argv)
    try:
        ledger = load(args.ledger)
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    found = problems(ledger)
    if found:
        print("\n".join(found), file=sys.stderr)
        return 1
    print(f"{args.ledger}: {len(checked_steps(ledger))} steps match the contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
