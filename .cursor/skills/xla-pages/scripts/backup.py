#!/usr/bin/env python3
"""Save the site before the first write: the skill's own get-structure snapshot, and its
get-localization (page SEO texts live there).

Shop Builder's version history is not the backup: restoring a version currently drops the
data-provider connections. The snapshot is also what the plan is rendered from, and apply
refuses to write when the site no longer matches it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import xla_common as common  # noqa: E402

STRUCTURE = "structure.json"
LOCALIZATION = "localization.json"
RECORD = "backup.json"


def take(config: dict, out_dir: Path) -> dict:
    out_dir = Path(out_dir)
    if out_dir.exists() and (not out_dir.is_dir() or any(out_dir.iterdir())):
        raise ValueError(f"{out_dir} must be absent or empty")
    common.check_cli_context(config)
    raw = common.run_json("shopbuilder", "get-structure", "--slug", config["site_slug"])
    structure = common.data(raw)
    if not isinstance(structure, dict) or not isinstance(structure.get("pages"), list):
        raise common.CliError("get-structure returned an unexpected shape")
    common.check_target(structure, config, for_write=False)
    raw_localization = common.run_json("shopbuilder", "get-localization", "--slug", config["site_slug"])
    if not isinstance(common.data(raw_localization), dict):
        raise common.CliError("get-localization returned an unexpected shape")
    out_dir.mkdir(parents=True, exist_ok=True)
    common.write_json(out_dir / STRUCTURE, raw)
    common.write_json(out_dir / LOCALIZATION, raw_localization)
    record = {
        "merchant_id": config["merchant_id"],
        "project_id": config["project_id"],
        "site_slug": config["site_slug"],
        "taken_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "read_only": True,
        "published": common.is_published(structure),
        "sha256": {
            name: hashlib.sha256((out_dir / name).read_bytes()).hexdigest() for name in (STRUCTURE, LOCALIZATION)
        },
        "structure_sha256": common.structure_hash(structure),
    }
    common.write_json(out_dir / RECORD, record)
    return record


def _read(backup_dir: Path, config: dict, name: str) -> dict:
    backup_dir = Path(backup_dir)
    record = common.load_json(backup_dir / RECORD, "backup record")
    if not isinstance(record, dict) or record.get("read_only") is not True:
        raise ValueError(f"{backup_dir} is not a backup made by backup.py")
    for key in ("merchant_id", "project_id", "site_slug"):
        if record.get(key) != config[key]:
            raise ValueError(f"{backup_dir} is a backup of another site ({key} differs)")
    path = backup_dir / name
    try:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise ValueError(f"cannot read {path}: {exc}") from None
    if digest != (record.get("sha256") or {}).get(name):
        raise ValueError(f"{path} changed after the backup was taken")
    value = common.data(common.load_json(path, name))
    if not isinstance(value, dict):
        raise ValueError(f"{path} holds no object")
    return value


def load(backup_dir: Path, config: dict) -> dict:
    """The backed-up structure, after checking the record and the file's checksum."""
    return _read(backup_dir, config, STRUCTURE)


def load_localization(backup_dir: Path, config: dict) -> dict:
    """The backed-up get-localization, checked the same way."""
    return _read(backup_dir, config, LOCALIZATION)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=common.DEFAULT_CONFIG)
    parser.add_argument("--out-dir", required=True, type=Path, help="a new folder under .xsolla/")
    args = parser.parse_args(argv)
    try:
        record = take(common.load_config(args.config), args.out_dir)
    except (OSError, ValueError, common.CliError) as exc:
        print(f"Backup failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"backup_dir": str(args.out_dir.resolve()), **record}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
