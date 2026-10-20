#!/usr/bin/env python3
"""Back up a project's Store catalog before the first write, and compare against it later.

Read-only: every call is a `xsolla catalog` list command. The Store key comes from the
CLI's keychain and the IDs from `.xsolla.json`, so this script never sees a credential.

    backup_catalog.py                      # write xsolla-backups/catalog-<project>-<time>.json
    backup_catalog.py --compare <backup>   # exit 0 if the catalog still matches, 1 if not
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# `xsolla` exits with 10 when the API answers HTTP 401 or 403.
CLI_EXIT_AUTH = 10
CLI_TIMEOUT_SECONDS = 120

# Entity type -> (list command, key that identifies one entity).
SOURCES = {
    "currencies": (["admin-list-currency", "--all"], "sku"),
    "currency_packages": (["admin-list-currency-packages", "--all"], "sku"),
    "items": (["list-items", "--all"], "sku"),
    "bundles": (["list-bundles", "--all"], "sku"),
    "groups": (["list-item-groups"], "external_id"),
}


class CatalogError(RuntimeError):
    pass


def run_cli(args: list[str]) -> object:
    """Run one read-only `xsolla` command and return its `data` payload."""
    try:
        result = subprocess.run(
            ["xsolla", *args, "--json"],
            capture_output=True,
            # The CLI writes UTF-8; don't let Windows decode it with the ANSI code page.
            encoding="utf-8",
            errors="replace",
            timeout=CLI_TIMEOUT_SECONDS,
            check=False,
        )
    except FileNotFoundError:
        raise CatalogError("xsolla is not installed: run the merchant-setup skill") from None
    except subprocess.TimeoutExpired:
        raise CatalogError(f"`xsolla {' '.join(args)}` timed out") from None
    if result.returncode == CLI_EXIT_AUTH:
        raise CatalogError(
            "the Store key was rejected (exit 10): run the merchant-setup skill; "
            "don't paste a key"
        )
    if result.returncode != 0:
        # With --json a failure leaves stdout empty and prints the error on stderr.
        detail = (result.stderr or result.stdout).strip()[:500]
        raise CatalogError(f"`xsolla {' '.join(args)}` exited {result.returncode}: {detail}")
    try:
        envelope = json.loads(result.stdout)
    except json.JSONDecodeError:
        raise CatalogError(f"`xsolla {' '.join(args)}` did not print JSON") from None
    if not isinstance(envelope, dict) or envelope.get("ok") is not True:
        raise CatalogError(f"`xsolla {' '.join(args)}` returned an unexpected shape")
    return envelope.get("data")


def flatten_groups(groups: list) -> list:
    """Item groups come back as a tree; return every group, children included."""
    flat = []
    for group in groups:
        if not isinstance(group, dict):
            continue
        flat.append({k: v for k, v in group.items() if k != "children"})
        flat.extend(flatten_groups(group.get("children") or []))
    return flat


def entities(kind: str, data: object) -> list:
    if kind == "groups":
        groups = data.get("groups") if isinstance(data, dict) else data
        return flatten_groups(groups or [])
    if not isinstance(data, list):
        raise CatalogError(f"{kind}: expected a list from the CLI")
    return data


def read_context() -> dict:
    config = run_cli(["config", "list"])
    if not isinstance(config, dict):
        raise CatalogError("xsolla config list returned an unexpected shape")
    context = {
        "merchant_id": config.get("merchant_id"),
        "project_id": config.get("project_id"),
        "sandbox": config.get("sandbox") is True,
    }
    if not context["merchant_id"] or not context["project_id"]:
        raise CatalogError("merchant_id or project_id is not set: run the merchant-setup skill")
    return context


def read_catalog() -> dict:
    catalog = {}
    for kind, (command, _key) in SOURCES.items():
        catalog[kind] = entities(kind, run_cli(["catalog", *command]))
    return catalog


def keys(catalog: dict) -> dict:
    """The identifying key of every entity, per type, sorted."""
    return {
        kind: sorted(str(entity.get(key)) for entity in catalog.get(kind, []) if isinstance(entity, dict))
        for kind, (_command, key) in SOURCES.items()
    }


def diff(before: dict, after: dict) -> dict:
    """Per type: keys added since the backup and keys that are gone."""
    old, new = keys(before), keys(after)
    changes = {}
    for kind in SOURCES:
        added = sorted(set(new[kind]) - set(old[kind]))
        removed = sorted(set(old[kind]) - set(new[kind]))
        if added or removed:
            changes[kind] = {"added": added, "removed": removed}
    return changes


def backup(out_dir: Path) -> Path:
    context = read_context()
    catalog = read_catalog()
    stamp = datetime.now(timezone.utc)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"catalog-{context['project_id']}-{stamp.strftime('%Y%m%dT%H%M%SZ')}.json"
    document = {"taken_at": stamp.isoformat(), "context": context, "catalog": catalog}
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    counts = ", ".join(f"{len(catalog[kind])} {kind}" for kind in SOURCES)
    print(f"Backed up project {context['project_id']} (sandbox={context['sandbox']}): {counts}")
    print(path)
    return path


def compare(backup_path: Path) -> int:
    try:
        document = json.loads(backup_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CatalogError(f"cannot read backup {backup_path}: {exc}") from None
    context = read_context()
    saved = document.get("context", {})
    if saved.get("project_id") != context["project_id"]:
        raise CatalogError(
            f"backup is for project {saved.get('project_id')}, "
            f"but the CLI is set to {context['project_id']}"
        )
    changes = diff(document.get("catalog", {}), read_catalog())
    if not changes:
        print(f"Catalog matches the backup taken at {document.get('taken_at')}.")
        return 0
    print(json.dumps(changes, ensure_ascii=False, indent=2))
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-dir", type=Path, default=Path("xsolla-backups"),
                        help="where to write the backup (default: ./xsolla-backups)")
    parser.add_argument("--compare", type=Path, metavar="BACKUP",
                        help="compare the live catalog with this backup instead of writing one")
    args = parser.parse_args(argv)
    try:
        if args.compare:
            return compare(args.compare)
        backup(args.out_dir)
        return 0
    except CatalogError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
