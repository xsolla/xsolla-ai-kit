#!/usr/bin/env python3
"""Run every `xsolla` call of a Shop Builder run with CLI sandbox mode off.

Shop Builder has no sandbox. A Shop Builder run requires CLI sandbox mode off. This
gate never switches it:

1. The active environment already has sandbox off: nothing to do.
2. Another environment in the config file in use has sandbox off and the brief's
   merchant and project: every call gets `--environment <name>`. No config file is
   written.
3. Otherwise preflight stops (SANDBOX_STILL_ON). `nocode-shop-setup` switches sandbox
   off at its first check, as part of the one yes the publisher gives in the batch,
   and the first message says the change persists and gives the undo. Then preflight
   runs again.

The xsolla CLI (1.9.4) reads `./.xsolla.json` when the working directory has one,
else `~/.xsolla.json`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

CONFIG_NAME = ".xsolla.json"
SWITCH_COMMAND = "xsolla config set sandbox false"
ENVIRONMENT_NOTE = "Using the CLI {name} environment (sandbox off)"
SANDBOX_STILL_ON = (
    "CLI sandbox mode is on and Shop Builder needs it off. nocode-shop-setup switches it "
    f"off at its first check (`{SWITCH_COMMAND}`) after the publisher's yes; then run "
    "preflight again"
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

    The active one is skipped (it has sandbox on). Names are sorted for a stable order.
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
    return sorted(names)


def plan_notes(report: dict) -> list[str]:
    """Return the plan line that says which CLI environment this run uses, if any."""
    if report.get("environment"):
        return [ENVIRONMENT_NOTE.format(name=report["environment"])]
    return []


def select(
    expected: dict,
    run_json: Callable[..., object],
    *,
    cwd: Path | None = None,
    home: Path | None = None,
) -> dict:
    """Pick how this run reaches the brief's project with sandbox mode off.

    `run_json(*args)` runs one `xsolla ... --json` call through command(). Returns the
    config list data the run uses and the named environment in use, if any. Raises
    RuntimeError(SANDBOX_STILL_ON) when sandbox is on and no environment in the config
    file has sandbox off for the brief's project.
    """
    ENVIRONMENT_ARGS.clear()
    config = config_data(run_json("config", "list"))
    check_ids(config, expected)
    if config.get("sandbox") is not True:
        return {"config": config, "environment": None}

    path = config_in_use(cwd or Path.cwd(), home)
    for name in candidate_environments(path, expected) if path is not None else []:
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
            return {"config": candidate, "environment": name}

    raise RuntimeError(SANDBOX_STILL_ON)
