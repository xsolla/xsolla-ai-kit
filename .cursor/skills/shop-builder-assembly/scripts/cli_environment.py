#!/usr/bin/env python3
"""Run every `xsolla` call of a Shop Builder run with CLI sandbox mode off.

Shop Builder has no sandbox. A request to change a Shop Builder site implies the
CLI's sandbox mode is off, so the gate settles it without asking:

1. The active environment already has sandbox off: nothing to do.
2. Another environment in the config file in use has sandbox off and the brief's
   merchant and project (typically `test`): every call gets
   `--environment <name>`. No config file is written.
3. Otherwise preflight runs `xsolla config set sandbox false` in the directory of
   the config file in use, so that file is the one changed.

The xsolla CLI (1.9.4) reads `./.xsolla.json` when the working directory has one,
else `~/.xsolla.json`, and `xsolla config set` writes `./.xsolla.json`, creating a
stub without merchant or project when the working directory has none. Step 3 runs
`config set` with the working directory set to the file in use, never creating a
new config file.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Callable

CONFIG_NAME = ".xsolla.json"
SANDBOX_SWITCHED_OFF = "CLI sandbox mode switched off for Shop Builder"
SANDBOX_STILL_ON = (
    "CLI sandbox mode is on and was not switched off; run preflight again, it "
    "switches sandbox mode off for Shop Builder"
)

# Global flags added to every `xsolla` call of this run, for example
# ["--environment", "test"]. Set by select(); empty means the active environment.
ENVIRONMENT_ARGS: list[str] = []


def command(*args: str) -> list[str]:
    """Return the `xsolla` argv for one call, with the selected environment."""
    return ["xsolla", *ENVIRONMENT_ARGS, *args]


def config_in_use(cwd: Path | None = None, home: Path | None = None) -> Path | None:
    """Return the config file the CLI reads from `cwd`, or None when there is none."""
    local = (cwd or Path.cwd()) / CONFIG_NAME
    if local.is_file():
        return local
    home_file = (home or Path.home()) / CONFIG_NAME
    return home_file if home_file.is_file() else None


def config_data(value: object) -> dict:
    if isinstance(value, dict) and value.get("ok") is True and "data" in value:
        value = value["data"]
    if not isinstance(value, dict):
        raise RuntimeError("xsolla config list returned an unexpected shape")
    return value


def check_ids(config: dict, expected: dict) -> None:
    if config.get("merchant_id") != expected.get("merchant_id"):
        raise RuntimeError("CLI merchant_id does not match the shop brief")
    if config.get("project_id") != expected.get("project_id"):
        raise RuntimeError("CLI project_id does not match the shop brief")


def candidate_environments(path: Path, expected: dict) -> list[str]:
    """Return environments in `path` with sandbox off and the brief's IDs.

    The active one is skipped (it has sandbox on); the brief's environment name
    (`test`) comes first.
    """
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(value, dict) or not isinstance(value.get("environments"), dict):
        return []
    active = value.get("default_environment")
    names = [
        name
        for name, environment in value["environments"].items()
        if isinstance(name, str)
        and name != active
        and isinstance(environment, dict)
        and environment.get("sandbox") is not True
        and environment.get("merchant_id") == expected.get("merchant_id")
        and environment.get("project_id") == expected.get("project_id")
    ]
    preferred = expected.get("environment")
    return sorted(names, key=lambda name: (name != preferred, name))


def select(
    expected: dict,
    run_json: Callable[..., object],
    *,
    switch: bool,
    cwd: Path | None = None,
    home: Path | None = None,
) -> dict:
    """Pick how this run reaches the brief's project with sandbox mode off.

    `run_json(*args)` runs one `xsolla ... --json` call through command().
    `switch` lets preflight change the config; the other scripts only reuse what
    preflight settled. Returns the config list data the run uses and a report.
    """
    ENVIRONMENT_ARGS.clear()
    config = config_data(run_json("config", "list"))
    check_ids(config, expected)
    if config.get("sandbox") is not True:
        return {"config": config, "environment": None, "sandbox_switched_off": False}

    work_dir = cwd or Path.cwd()
    path = config_in_use(work_dir, home)
    if path is None:
        raise RuntimeError("no Xsolla CLI config file is in use; run `xsolla config init`")

    for name in candidate_environments(path, expected):
        try:
            candidate = config_data(run_json("--environment", name, "config", "list"))
        except RuntimeError:
            continue
        if (
            candidate.get("sandbox") is not True
            and candidate.get("merchant_id") == expected.get("merchant_id")
            and candidate.get("project_id") == expected.get("project_id")
        ):
            ENVIRONMENT_ARGS[:] = ["--environment", name]
            return {
                "config": candidate,
                "environment": name,
                "sandbox_switched_off": True,
            }

    if not switch:
        raise RuntimeError(SANDBOX_STILL_ON)

    local = work_dir / CONFIG_NAME
    local_existed = local.exists()
    # `config set` writes ./.xsolla.json, so run it where the file in use lives.
    result = subprocess.run(
        command("config", "set", "sandbox", "false", "--json"),
        cwd=str(path.parent),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if not local_existed and local.exists() and local.resolve() != path.resolve():
        # Defensive: the CLI wrote a new file into the working directory. Remove
        # it so the CLI keeps reading the config it read before.
        os.remove(local)
        raise RuntimeError("switching CLI sandbox mode off created a new config file")
    if result.returncode:
        detail = (
            (result.stderr or "").strip()
            or (result.stdout or "").strip()
            or f"exit code {result.returncode}"
        )
        raise RuntimeError(f"switching CLI sandbox mode off failed: {detail}")
    config = config_data(run_json("config", "list"))
    check_ids(config, expected)
    if config.get("sandbox") is True:
        raise RuntimeError("CLI sandbox mode is still on after switching it off")
    return {"config": config, "environment": None, "sandbox_switched_off": True}
