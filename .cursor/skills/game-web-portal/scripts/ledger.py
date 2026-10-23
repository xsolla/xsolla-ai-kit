#!/usr/bin/env python3
"""Check the onboarding ledger: every step has the contract's shape and only its statuses."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# The onboarding contract's statuses (shop-plan/references/onboarding-contract.md). A step
# that is under way has no status key at all.
STATUSES = ("completed", "placeholder", "needs_input", "needs_access", "needs_human",
            "blocked_capability", "failed")


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path} is not a JSON object")
    return value


def step_name(step: object, index: int) -> str:
    if isinstance(step, dict) and isinstance(step.get("id"), str) and step["id"]:
        return f"step {step['id']!r}"
    return f"steps[{index}]"


def problems(ledger: dict) -> list[str]:
    """Every way the ledger's steps break the contract, each naming its step."""
    steps = ledger.get("steps")
    if not isinstance(steps, list):
        return ["the ledger has no steps list"]
    found = []
    for index, step in enumerate(steps):
        name = step_name(step, index)
        if not isinstance(step, dict):
            found.append(f"{name}: must be an object")
            continue
        if not isinstance(step.get("id"), str) or not step["id"]:
            found.append(f"{name}: needs an id")
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
    print(f"{args.ledger}: {len(ledger['steps'])} steps match the contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
