#!/usr/bin/env python3
"""Run every `xsolla` call of a Shop Builder run with CLI sandbox mode off.

Shop Builder has no sandbox. A request to change a Shop Builder site implies the
CLI's sandbox mode is off, so the gate settles it without asking:

1. The active environment already has sandbox off: nothing to do.
2. Another environment in the config file in use has sandbox off and the brief's
   merchant and project (typically `test`): every call gets
   `--environment <name>`. No config file is written.
3. Otherwise preflight stops and asks the user to confirm first (it raises
   SandboxConfirmationNeeded, which names the exact command). Only a preflight run
   with the user's confirmation runs `xsolla config set sandbox false` in the
   directory of the config file in use, so that file is the one changed. It records
   the switch in a restore record in the home folder. restore() puts sandbox back
   on and removes the record; the last step of every run calls it.

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
# Restore record for a switch this run made. It lives in the home folder, not in the
# folder of the config in use, so no project folder gets an extra file.
RESTORE_NAME = ".shop-builder-sandbox.json"
SWITCH_COMMAND = "xsolla config set sandbox false"
SANDBOX_SWITCHED_OFF = (
    "CLI sandbox mode switched off for Shop Builder; it is switched back on when the run ends"
)
ENVIRONMENT_NOTE = "Using the CLI {name} environment (sandbox off)"
SANDBOX_STILL_ON = (
    "CLI sandbox mode is on and was not switched off; run preflight again, it asks the "
    "user to confirm switching sandbox mode off for Shop Builder"
)

# Global flags added to every `xsolla` call of this run, for example
# ["--environment", "test"]. Set by select(); empty means the active environment.
ENVIRONMENT_ARGS: list[str] = []


class SandboxConfirmationNeeded(RuntimeError):
    """Sandbox mode is on and the user has not confirmed switching it off."""

    def __init__(self, directory: Path) -> None:
        super().__init__(
            "CLI sandbox mode is on and Shop Builder needs it off. Ask the user to confirm "
            f"running `{SWITCH_COMMAND}` in {directory}; the run switches it back on when it "
            "ends. After a yes, run preflight again with --confirm-sandbox-off."
        )
        self.directory = directory


def command(*args: str) -> list[str]:
    """Return the `xsolla` argv for one call, with the selected environment."""
    return ["xsolla", *ENVIRONMENT_ARGS, *args]


def restore_path(home: Path | None = None) -> Path:
    return (home or Path.home()) / RESTORE_NAME


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


def plan_notes(report: dict) -> list[str]:
    """Return the plan line that says how this run reached sandbox off, if any.

    Each path gets its own line: reusing another environment writes no config,
    so it must not claim sandbox mode was switched off.
    """
    if report.get("environment"):
        return [ENVIRONMENT_NOTE.format(name=report["environment"])]
    if report.get("sandbox_switched_off"):
        return [SANDBOX_SWITCHED_OFF]
    return []


def select(
    expected: dict,
    run_json: Callable[..., object],
    *,
    switch: bool,
    confirmed: bool = False,
    cwd: Path | None = None,
    home: Path | None = None,
) -> dict:
    """Pick how this run reaches the brief's project with sandbox mode off.

    `run_json(*args)` runs one `xsolla ... --json` call through command().
    `switch` lets preflight change the config; the other scripts only reuse what
    preflight settled. A change also needs `confirmed`, the user's yes to the exact
    command; without it nothing is written and SandboxConfirmationNeeded is raised.
    Returns the config list data the run uses and a report.
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
            # No config is changed on this path, so sandbox is not "switched off".
            return {
                "config": candidate,
                "environment": name,
                "sandbox_switched_off": False,
            }

    if not switch:
        raise RuntimeError(SANDBOX_STILL_ON)
    if not confirmed:
        raise SandboxConfirmationNeeded(path.parent)

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
    # Record the switch before the checks below, so restore() also covers a run that
    # then fails. The sandbox value was on (checked above), so restoring sets it on.
    write_restore_record(path.parent, home)
    config = config_data(run_json("config", "list"))
    check_ids(config, expected)
    if config.get("sandbox") is True:
        raise RuntimeError("CLI sandbox mode is still on after switching it off")
    return {"config": config, "environment": None, "sandbox_switched_off": True}


def write_restore_record(directory: Path, home: Path | None = None) -> None:
    """Record that this run switched sandbox mode off in the config under `directory`."""
    record = {"directory": str(directory), "previous_sandbox": True}
    restore_path(home).write_text(json.dumps(record, indent=2), encoding="utf-8")


def restore(home: Path | None = None) -> dict:
    """Put back the sandbox value that a switch in this run changed, then drop the record.

    Does nothing when no record exists, so the last step of every run can call it.
    The record is kept when the restore fails, so the next call can retry.
    """
    record_file = restore_path(home)
    if not record_file.is_file():
        return {"restored": False}
    try:
        record = json.loads(record_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot read the sandbox restore record: {exc}") from exc
    if (
        not isinstance(record, dict)
        or not isinstance(record.get("directory"), str)
        or record.get("previous_sandbox") is not True
    ):
        raise RuntimeError("the sandbox restore record has an unexpected shape")
    directory = Path(record["directory"])
    result = subprocess.run(
        ["xsolla", "config", "set", "sandbox", "true", "--json"],
        cwd=str(directory),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if result.returncode:
        detail = (
            (result.stderr or "").strip()
            or (result.stdout or "").strip()
            or f"exit code {result.returncode}"
        )
        raise RuntimeError(f"restoring CLI sandbox mode failed: {detail}")
    listed = subprocess.run(
        ["xsolla", "config", "list", "--json"],
        cwd=str(directory),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if listed.returncode:
        raise RuntimeError("restoring CLI sandbox mode could not be checked; the record is kept")
    config = config_data(json.loads(listed.stdout))
    if config.get("sandbox") is not True:
        raise RuntimeError("CLI sandbox mode is still off after restoring it; the record is kept")
    record_file.unlink()
    return {"restored": True, "directory": str(directory)}
