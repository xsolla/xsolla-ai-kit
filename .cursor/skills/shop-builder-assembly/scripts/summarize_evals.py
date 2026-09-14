#!/usr/bin/env python3
"""Validate and summarize Shop Builder assembly JSONL evaluation runs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PRESETS = {"mobile-single-page", "pc-multi-page", "live-service-events"}
RESULTS = {"success", "failure"}


def load_runs(path: Path) -> list[dict]:
    runs: list[dict] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ValueError(f"cannot read eval log: {exc}") from exc
    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"line {line_number} is invalid JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"line {line_number} must be an object")
        runs.append(value)
    return runs


def summarize(runs: list[dict]) -> dict:
    errors: list[str] = []
    seen: set[str] = set()
    for index, run in enumerate(runs, 1):
        run_id = run.get("run_id")
        if not isinstance(run_id, str) or not run_id.strip():
            errors.append(f"run {index}: run_id is required")
        elif run_id in seen:
            errors.append(f"run {index}: duplicate run_id {run_id}")
        else:
            seen.add(run_id)
        if run.get("preset") not in PRESETS:
            errors.append(f"run {index}: invalid preset")
        if run.get("result") not in RESULTS:
            errors.append(f"run {index}: result must be success or failure")
        interventions = run.get("manual_interventions")
        if (
            isinstance(interventions, bool)
            or not isinstance(interventions, int)
            or interventions < 0
        ):
            errors.append(
                f"run {index}: manual_interventions must be a non-negative integer"
            )
        if run.get("result") == "failure" and not run.get("failure"):
            errors.append(f"run {index}: failure details are required for a failed run")

    successes = sum(run.get("result") == "success" for run in runs)
    over_target = sum(
        isinstance(run.get("manual_interventions"), int)
        and not isinstance(run.get("manual_interventions"), bool)
        and run["manual_interventions"] > 2
        for run in runs
    )
    success_rate = successes / len(runs) if runs else 0.0
    return {
        "runs": len(runs),
        "successes": successes,
        "success_rate": round(success_rate, 3),
        "runs_over_intervention_target": over_target,
        "validation_errors": errors,
        "targets": {
            "minimum_runs": len(runs) >= 10,
            "success_rate_at_least_0_8": success_rate >= 0.8,
            "manual_interventions_at_most_2_per_run": over_target == 0,
        },
    }


def passes(summary: dict) -> bool:
    return not summary["validation_errors"] and all(summary["targets"].values())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("eval_log", type=Path)
    args = parser.parse_args()
    try:
        summary = summarize(load_runs(args.eval_log))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    summary["passes"] = passes(summary)
    print(json.dumps(summary, indent=2))
    return 0 if summary["passes"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
