"""Test helpers: a backup, a rendered plan and an apply run against the stand-in CLI."""

from __future__ import annotations

import contextlib
import copy
import io
import json
import sys
from pathlib import Path
from unittest import mock

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS.parent / "scripts"))
sys.path.insert(0, str(TESTS))

import apply_pages  # noqa: E402
import backup  # noqa: E402
import render_plan  # noqa: E402
import stand_in_cli  # noqa: E402
import xla_common as common  # noqa: E402

FIXTURES = TESTS / "fixtures"
CONFIG = FIXTURES / "config.json"
PUB = FIXTURES / "pub"
NOW = "2026-11-07T11:00:00Z"  # the fixtures were requested at 08:55-09:00Z


def load_batch() -> dict:
    return json.loads((FIXTURES / "batch.json").read_text(encoding="utf-8"))


def patched(cli: stand_in_cli.StandInCli):
    stack = contextlib.ExitStack()
    stack.enter_context(mock.patch.object(common, "execute", cli))
    stack.enter_context(mock.patch.object(common, "execute_help", cli.help))
    return stack


def write_config(directory: Path, **changes) -> Path:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    config.update(changes)
    path = Path(directory) / "config.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    return path


def prepare(directory: Path, cli: stand_in_cli.StandInCli, batch: dict | None = None,
            config_path: Path = CONFIG, name: str = "backup") -> tuple[dict, list[str], Path, Path]:
    """Back up the stand-in site, render the plan and save it. Returns (plan, errors, plan, backup)."""
    config = common.load_config(config_path)
    backup_dir = Path(directory) / name
    with patched(cli):
        backup.take(config, backup_dir)
    structure = backup.load(backup_dir, config)
    localization = backup.load_localization(backup_dir, config)
    plan, errors = render_plan.build_plan(common.load_manifest(), config, structure, batch or load_batch(),
                                          localization)
    plan_path = Path(directory) / f"{name}-plan.json"
    common.write_json(plan_path, plan)
    return plan, errors, plan_path, backup_dir


def save_plan(path: Path, plan: dict) -> dict:
    """Re-sign an edited plan, as if a person approved the edited version."""
    plan = copy.deepcopy(plan)
    plan["confirmation_id"] = common.confirmation_id(plan)
    common.write_json(path, plan)
    return plan


def apply(cli: stand_in_cli.StandInCli, plan_path: Path, backup_dir: Path, confirmation: str | None = None,
          config_path: Path = CONFIG, now: str = NOW, pub: Path = PUB) -> tuple[int, dict]:
    plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))
    out = io.StringIO()
    with patched(cli), contextlib.redirect_stdout(out):
        code = apply_pages.main([
            "--plan", str(plan_path), "--confirmation-id", confirmation or plan["confirmation_id"],
            "--backup-dir", str(backup_dir), "--pub-dir", str(pub), "--config", str(config_path), "--now", now,
        ])
    return code, json.loads(out.getvalue())
