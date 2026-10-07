#!/usr/bin/env python3
"""Record a new page's seeded blocks, and check later which of them are still untouched."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(value, dict) and value.get("ok") is False:
        raise RuntimeError(f"{path} holds a failed CLI call: {value.get('error', value)}")
    if isinstance(value, dict) and value.get("ok") is True and "data" in value:
        value = value["data"]
    if not isinstance(value, dict):
        raise RuntimeError(f"{path} is not a JSON object")
    return value


def find_page(structure: dict, page_id: str) -> dict | None:
    return next((p for p in structure.get("pages") or [] if p.get("_id") == page_id), None)


def string_ids(value: object) -> list[str]:
    if isinstance(value, str):
        return [value] if value.startswith("L:") else []
    if isinstance(value, dict):
        return [i for v in value.values() for i in string_ids(v)]
    if isinstance(value, list):
        return [i for v in value for i in string_ids(v)]
    return []


def block_hash(block: dict, localization: dict, page_id: str) -> str:
    """Hash what a partner can change: values, components and every string they reference.

    Component `_id`s are left out: the server regenerates them on every read.
    """
    content = {key: block.get(key) for key in ("module", "hidden", "values")}
    content["components"] = [
        {k: v for k, v in c.items() if k != "_id"} if isinstance(c, dict) else c
        for c in block.get("components") or []
    ]
    page_texts = ((localization.get("pages") or {}).get(page_id) or {}).get("texts") or {}
    common = localization.get("common") or {}
    content["strings"] = {
        i: page_texts.get(i, common.get(i)) for i in sorted(set(string_ids(content)))
    }
    canonical = json.dumps(content, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def record(structure: dict, localization: dict, page_id: str) -> dict:
    """The ledger entry for a page the agent just created: every block on it is seeded."""
    page = find_page(structure, page_id)
    if page is None:
        raise RuntimeError(f"page {page_id} is not in the structure")
    return {
        "page_id": page_id,
        "path": page.get("path"),
        "seeded_blocks": [
            {"_id": b["_id"], "module": b.get("module"),
             "hash": block_hash(b, localization, page_id)}
            for b in page.get("blocks", [])
        ],
    }


def ledger_entry(ledger: dict, page_id: str) -> dict:
    for step in ledger.get("steps") or []:
        if step.get("id") != "storefront":
            continue
        for entry in (step.get("ids") or {}).get("created_pages") or []:
            if entry.get("page_id") == page_id:
                blocks = entry.get("seeded_blocks")
                if not isinstance(blocks, list) or any(
                    not isinstance(b, dict) or not all(k in b for k in ("_id", "module", "hash"))
                    for b in blocks
                ):
                    raise RuntimeError(
                        f"page {page_id}: seeded_blocks must list _id, module and hash"
                    )
                return entry
    raise RuntimeError(f"page {page_id} has no ledger record: never trim it")


def check(structure: dict, localization: dict, entry: dict) -> dict:
    """Split recorded seeded blocks into untouched (removable), changed, and gone."""
    page_id = entry["page_id"]
    page = find_page(structure, page_id)
    current = {b["_id"]: b for b in (page or {}).get("blocks", [])}
    result: dict = {"page_id": page_id, "untouched": [], "changed": [], "gone": []}
    for seeded in entry["seeded_blocks"]:
        block = current.get(seeded["_id"])
        if block is None:
            status = "gone"
        elif block_hash(block, localization, page_id) == seeded["hash"]:
            status = "untouched"
        else:
            status = "changed"
        result[status].append({"_id": seeded["_id"], "module": seeded["module"]})
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("record", "check"))
    parser.add_argument("--structure", required=True, type=Path, help="get-structure output")
    parser.add_argument("--localization", required=True, type=Path,
                        help="get-localization output")
    parser.add_argument("--page-id", required=True, help="the page the agent created")
    parser.add_argument("--ledger", type=Path, help="check: .xsolla/onboarding.json")
    args = parser.parse_args(argv)
    try:
        structure, localization = load(args.structure), load(args.localization)
        if args.action == "record":
            output = record(structure, localization, args.page_id)
        else:
            if not args.ledger:
                raise RuntimeError("check needs --ledger")
            entry = ledger_entry(load(args.ledger), args.page_id)
            output = check(structure, localization, entry)
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
