#!/usr/bin/env python3
"""Check and write the Xsolla credentials in the project's `.env`, without ever printing the key.

Usage (run from the folder that holds, or will hold, `.env`):
    python3 env_credentials.py check
    python3 env_credentials.py write --merchant-id N --project-id N [--key-prompt | --key-stdin]

`check` prints the merchant and project ids (they are not secrets, and they show which project
is configured) and only `set` or `missing` for the API key.

`write` makes sure `.env` is ignored by Git first, then sets the three names in place: an existing
assignment (also `export NAME=`) is updated, duplicates are dropped, every other line is kept, and
the file ends with mode 600. The key is never taken from the command line:
  --key-prompt  asks for it with hidden input; the user runs this in their own terminal;
  --key-stdin   reads it from a pipe (a raw key, or a JSON object with `key` or `api_key`);
  neither       keeps the key already in `.env`.
Nothing is written when an argument is invalid. `.env` is parsed as text, never sourced.
Python 3.9+, standard library only.
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

MERCHANT, PROJECT, KEY = "XSOLLA_MERCHANT_ID", "XSOLLA_PROJECT_ID", "XSOLLA_PROJECT_API_KEY"
NAMES = (MERCHANT, PROJECT, KEY)
ID = re.compile(r"[0-9]{1,20}")
ASSIGNMENT = re.compile(r"^\s*(export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$")


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def read_values(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        match = ASSIGNMENT.match(line)
        if match and match.group(2) in NAMES and not line.lstrip().startswith("#"):
            values[match.group(2)] = _unquote(match.group(3))
    return values


def check(folder: Path) -> int:
    values = read_values(folder / ".env")
    print(f"{MERCHANT}: {values.get(MERCHANT) or 'missing'}")
    print(f"{PROJECT}: {values.get(PROJECT) or 'missing'}")
    print(f"{KEY}: {'set' if values.get(KEY) else 'missing'}")
    return 0 if all(values.get(name) for name in NAMES) else 1


def ensure_ignored(folder: Path) -> None:
    """Make `.env` ignored by Git before anything is written to it."""
    try:
        ignored = subprocess.run(["git", "check-ignore", "-q", ".env"], cwd=folder,
                                 capture_output=True).returncode == 0
    except OSError:
        ignored = False
    if ignored:
        return
    gitignore = folder / ".gitignore"
    text = gitignore.read_text(encoding="utf-8") if gitignore.is_file() else ""
    if ".env" not in (line.strip() for line in text.splitlines()):
        with gitignore.open("a", encoding="utf-8") as fh:
            fh.write(("" if not text or text.endswith("\n") else "\n") + ".env\n")


def merged_lines(existing: List[str], updates: Dict[str, str]) -> List[str]:
    out: List[str] = []
    done = set()
    for line in existing:
        match = ASSIGNMENT.match(line)
        name = match.group(2) if match and not line.lstrip().startswith("#") else None
        if name in updates:
            if name in done:
                continue  # a duplicate assignment: drop it
            out.append(f"{match.group(1) or ''}{name}={updates[name]}")
            done.add(name)
        else:
            out.append(line)
    missing = [name for name in NAMES if name in updates and name not in done]
    if missing:
        if out and out[-1].strip():
            out.append("")
        out.append("# Xsolla credentials")
        out.extend(f"{name}={updates[name]}" for name in missing)
    return out


def key_from_stdin(raw: str) -> Optional[str]:
    raw = raw.strip()
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except ValueError:
        parsed = None
    if isinstance(parsed, dict):
        value = parsed.get("key") or parsed.get("api_key")
        return value.strip() if isinstance(value, str) and value.strip() else None
    first = raw.splitlines()[0].strip()
    return first if first and not any(c.isspace() for c in first) else None


def write(folder: Path, merchant_id: str, project_id: str, key: Optional[str]) -> int:
    path = folder / ".env"
    ensure_ignored(folder)
    updates = {MERCHANT: merchant_id, PROJECT: project_id}
    if key is not None:
        updates[KEY] = key
    existing = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    text = "\n".join(merged_lines(existing, updates)) + "\n"
    tmp = folder / ".env.tmp-xsolla"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)
    return check(folder)


def main(argv: Optional[List[str]] = None, folder: Optional[Path] = None) -> int:
    parser = argparse.ArgumentParser(prog="env_credentials.py")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check")
    w = sub.add_parser("write")
    w.add_argument("--merchant-id", required=True)
    w.add_argument("--project-id", required=True)
    source = w.add_mutually_exclusive_group()
    source.add_argument("--key-prompt", action="store_true")
    source.add_argument("--key-stdin", action="store_true")
    args = parser.parse_args(argv)
    folder = folder or Path.cwd()
    if args.command == "check":
        return check(folder)
    if not ID.fullmatch(args.merchant_id) or not ID.fullmatch(args.project_id):
        print("error: merchant and project ids must be numbers; nothing was written")
        return 2
    key = None
    if args.key_prompt:
        key = getpass.getpass("Project API key (input hidden): ").strip() or None
    elif args.key_stdin:
        key = key_from_stdin(sys.stdin.read())
    if (args.key_prompt or args.key_stdin) and key is None:
        print("error: no API key was given; nothing was written")
        return 2
    return write(folder, args.merchant_id, args.project_id, key)


if __name__ == "__main__":
    sys.exit(main())
