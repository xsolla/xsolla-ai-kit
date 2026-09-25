#!/usr/bin/env python3
"""Create a balanced, non-mutating nine-brief matrix for runs 002 through 010."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

from validate_shop_brief import load_brief, validate

MATRIX = (
    "mobile-single-page",
    "pc-multi-page",
    "live-service-events",
    "mobile-single-page",
    "pc-multi-page",
    "live-service-events",
    "mobile-single-page",
    "pc-multi-page",
    "live-service-events",
)


def fixture_content(preset: str, run_id: str) -> dict:
    common = {
        "faq": [{"question": "Evaluation question", "answer": "Evaluation answer"}]
    }
    if preset == "pc-multi-page":
        return {
            **common,
            "description": {
                "text": f"Synthetic PC shop content for {run_id}",
                "status": "approved-test-fixture",
            },
            "requirements": {
                "platform": "pc",
                "status": "approved-test-fixture",
            },
        }
    if preset == "live-service-events":
        return {
            **common,
            "events": [
                {
                    "name": f"Synthetic evaluation event {run_id}",
                    "status": "approved-test-fixture",
                }
            ],
        }
    return common


def prepare(base: dict) -> list[tuple[str, dict]]:
    errors = validate(base)
    if errors:
        raise ValueError("invalid base brief: " + "; ".join(errors))
    briefs = []
    base_slug = base["site"]["slug"]
    base_name = base["site"]["name"]
    for run_number, preset in enumerate(MATRIX, start=2):
        run_id = f"run-{run_number:03d}"
        brief = copy.deepcopy(base)
        brief["site"]["slug"] = f"{base_slug}-r{run_number:02d}"
        brief["site"]["name"] = f"{base_name} {run_id}"
        brief["site"]["preset"] = preset
        brief["game"]["platforms"] = (
            ["pc"] if preset == "pc-multi-page" else ["mobile"]
        )
        brief["game"]["lifecycle"] = (
            "live-service" if preset == "live-service-events" else "launch"
        )
        brief["content"] = fixture_content(preset, run_id)
        brief["sources"] = [
            *brief["sources"],
            {
                "kind": "evaluation_fixture",
                "note": f"Synthetic dedicated-test-project input for {run_id}",
            },
        ]
        generated_errors = validate(brief)
        if generated_errors:
            raise ValueError(
                f"generated {run_id} is invalid: " + "; ".join(generated_errors)
            )
        briefs.append((run_id, brief))
    return briefs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-brief", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        briefs = prepare(load_brief(args.base_brief))
        args.output_dir.mkdir(parents=True, exist_ok=False)
        for run_id, brief in briefs:
            (args.output_dir / f"{run_id}.json").write_text(
                json.dumps(brief, indent=2) + "\n", encoding="utf-8"
            )
    except (OSError, ValueError) as exc:
        print(f"Evaluation brief preparation failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"ok": True, "runs": [run_id for run_id, _ in briefs]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
