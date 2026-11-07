#!/usr/bin/env python3
"""Apply an approved plan to the site's draft, then read every page back. Never publishes.

Before the first write, in this order, any failure stops the batch with zero writes:
  1. the plan file is the one rendered (its confirmation_id) and the one the user approved;
  2. the backup is intact and is the structure the plan was rendered from;
  3. the plan passes plan_checks against the manifest;
  4. the saved /pub responses are complete and at most 24 hours old;
  5. the CLI points at the configured merchant and project, with sandbox mode off;
  6. the CLI's --help lists every command and flag the plan needs (cli_gate.py);
  7. the site is the configured one (a published site only if the config allows it);
  8. the site still equals the backup.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import backup  # noqa: E402
import cli_gate  # noqa: E402
import plan_checks  # noqa: E402
import preflight_report  # noqa: E402
import verify_pages  # noqa: E402
import xla_common as common  # noqa: E402


class Stop(RuntimeError):
    """A check failed before any write; `details` goes in the report."""

    def __init__(self, status: str, message: str, details: object = None) -> None:
        super().__init__(message)
        self.status = status
        self.details = details


def preconditions(args: argparse.Namespace, now: datetime) -> tuple[dict, dict, dict, dict, dict]:
    manifest = common.load_manifest()
    config = common.load_config(args.config)
    plan = common.load_json(args.plan, "plan")
    if not isinstance(plan, dict) or plan.get("confirmation_id") != common.confirmation_id(plan):
        raise Stop("refused", "the plan file was changed after it was rendered")
    if args.confirmation_id != plan["confirmation_id"]:
        raise Stop("refused", "the confirmation ID is not the approved plan's")
    target = plan.get("target") or {}
    if any(target.get(key) != config[key] for key in ("merchant_id", "project_id", "site_slug")):
        raise Stop("refused", "the plan is for another site than the local config's")
    structure = backup.load(args.backup_dir, config)
    if plan.get("structure_sha256") != common.structure_hash(structure):
        raise Stop("refused", "the plan was rendered from another backup")
    errors = plan_checks.validate(plan, manifest, config, structure)
    if errors:
        raise Stop("refused", "the plan breaks the manifest", errors)
    providers = [row["provider"] for row in plan.get("rows") or []]
    preflight = preflight_report.build_report(args.pub_dir, config, providers, now, manifest)
    if not preflight["complete"]:
        raise Stop("refused", "the saved /pub responses are incomplete", {
            "errors": preflight["errors"], "missing": preflight["missing"],
        })
    if not preflight["fresh_for_write"]:
        raise Stop("refused", (
            f"the oldest /pub response was requested at {preflight['requested_at']['oldest']}, "
            f"{preflight['age_hours']} h ago; GET them again (max {preflight['max_age_hours']:g} h)"
        ))
    common.check_cli_context(config)
    if plan.get("capabilities") != cli_gate.needed(plan):
        raise Stop("refused", "the plan's capability list doesn't match its writes")
    missing = cli_gate.check(plan["capabilities"])
    if missing:
        raise Stop("blocked_capability", "the CLI lacks commands or flags this plan needs", missing)
    current = common.get_structure(config["site_slug"])
    common.check_target(current, config)
    if common.structure_hash(current) != common.structure_hash(structure):
        raise Stop("refused", (
            "the site changed after the backup (the Pages team may have edited it): back up "
            "again, render again and show the new plan"
        ))
    return manifest, config, plan, structure, preflight


class Run:
    def __init__(self, config: dict, landing_id: str, progress: dict) -> None:
        self.slug = config["site_slug"]
        self.landing = landing_id
        self.progress = progress

    def page(self, route: str) -> dict:
        page = common.find_page(common.get_structure(self.slug), route)
        if page is None:
            raise common.CliError(f"{route} is not on the site")
        return page

    def write(self, *args: str) -> object:
        self.progress["writes"] += 1
        return common.run_json(*args)

    def patch(self, kind: str, target: str, patches: list[dict]) -> None:
        payload = {"xla": {"type": kind, "id": target, "patches": patches}}
        self.write("shopbuilder", "update-block", "--landing-id", self.landing,
                   "--data", json.dumps(payload, separators=(",", ":"), ensure_ascii=False))

    def apply_page(self, planned: dict) -> None:
        route = planned["route"]
        expected = planned["expected"]
        state = {"page_id": planned.get("page_id"), "blocks": {}, "connections": {}}
        if state["page_id"]:
            self.map_existing(route, expected, state)
        for op in planned["ops"]:
            getattr(self, "op_" + op["op"])(route, expected, state, op)

    def map_existing(self, route: str, expected: dict, state: dict) -> None:
        page = self.page(route)
        keys = {block["package"]: block["key"] for block in expected["blocks"]}
        for block in page.get("blocks") or []:
            package = common.block_identity(block)[0]
            if package in keys and keys[package] not in state["blocks"]:
                state["blocks"][keys[package]] = block["_id"]
        self.map_connections(page, expected, state)

    def map_connections(self, page: dict, expected: dict, state: dict) -> None:
        for conn in common.page_connections(page):
            for want in expected["connections"]:
                if verify_pages.connection_identity(conn) == verify_pages.connection_identity(want):
                    state["connections"].setdefault(want["key"], conn.get("_id"))

    def op_create_page(self, route: str, expected: dict, state: dict, op: dict) -> None:
        args = ["shopbuilder", "add-page", "--slug", self.slug, "--name", op["name"], "--path", route]
        if op["kind"] == "dynamic":
            args += ["--paths-provider", op["paths"]["provider"],
                     "--provider-input", json.dumps(op["paths"]["input"], separators=(",", ":"))]
        if cli_gate.has("add-page-empty"):
            args.append("--empty")
        self.write(*args)
        page = self.page(route)
        state["page_id"] = page["_id"]
        self.progress["created_pages"].append(route)
        seeded = [(index, block.get("_id")) for index, block in enumerate(page.get("blocks") or [])]
        if seeded:
            # Delete, not hide: a hidden block stays in the structure. Only the blocks add-page
            # seeded on this page, in this run, read right after it was created.
            self.patch("page", page["_id"], [
                {"op": "remove", "path": ["blocks", index]} for index, _ in sorted(seeded, reverse=True)
            ])
            left = {b.get("_id") for b in self.page(route).get("blocks") or []}
            if left & {block_id for _, block_id in seeded}:
                raise common.CliError(f"the blocks add-page seeded on {route} were not deleted")
        self.map_connections(self.page(route), expected, state)
        for conn in expected["connections"]:
            if conn["kind"] == "path" or conn["linked"]:
                if conn["key"] not in state["connections"]:
                    raise common.CliError(f"{route} has no {conn['key']} data connection after add-page")

    def op_add_data_connection(self, route: str, expected: dict, state: dict, op: dict) -> None:
        created = common.data(self.write(
            "shopbuilder", "add-data-connection", "--landing-id", self.landing, "--page-id", state["page_id"],
            "--provider", op["provider"], "--input", json.dumps(op["input"], separators=(",", ":")),
        ))
        connection_id = created.get("_id") if isinstance(created, dict) else None
        if not isinstance(connection_id, str):
            raise common.CliError("add-data-connection returned no _id")
        state["connections"][op["key"]] = connection_id

    def op_add_block(self, route: str, expected: dict, state: dict, op: dict) -> None:
        known = {b.get("_id") for b in self.page(route).get("blocks") or []}
        self.write(
            "shopbuilder", "add-block", "--landing-id", self.landing, "--page-id", state["page_id"],
            "--block", "federated", "--package", op["package"], "--version", op["version"],
            "--index", str(op["index"]),
        )
        new = [b for b in self.page(route).get("blocks") or [] if b.get("_id") not in known]
        if len(new) != 1:
            raise common.CliError(f"add-block left {len(new)} new blocks on {route}")
        package, version = common.block_identity(new[0])
        if (package, version) != (op["package"], op["version"]):
            raise common.CliError(
                f"add-block added {package}@{version}, not the pinned {op['package']}@{op['version']}"
            )
        state["blocks"][op["key"]] = new[0]["_id"]
        self.progress["created_blocks"].append(new[0]["_id"])

    def op_set_block_field(self, route: str, expected: dict, state: dict, op: dict) -> None:
        block_id = state["blocks"][op["key"]]
        block = next(b for b in self.page(route).get("blocks") or [] if b.get("_id") == block_id)
        verb = "replace" if op["field"] in common.block_fields(block) else "add"
        self.patch("block", block_id, [
            {"op": verb, "path": ["values", "internalBlockValues", op["field"]], "value": op["value"]}
        ])

    def op_hide_block(self, route: str, expected: dict, state: dict, op: dict) -> None:
        self.patch("block", state["blocks"][op["key"]], [{"op": "replace", "path": ["hidden"], "value": True}])

    def op_bind_field(self, route: str, expected: dict, state: dict, op: dict) -> None:
        self.write(
            "shopbuilder", "bind-block-field", "--landing-id", self.landing,
            "--block-id", state["blocks"][op["key"]], "--field", op["field"],
            "--connection-id", state["connections"][op["source"]], "--output", op["output"],
        )

    def op_set_page_seo(self, route: str, expected: dict, state: dict, op: dict) -> None:
        args = ["shopbuilder", "set-page-seo", "--landing-id", self.landing, "--page-id", state["page_id"],
                "--field", op["field"]]
        if "value" in op:
            args += ["--value", str(op["value"])]
        else:
            args += ["--connection-id", state["connections"][op["source"]], "--output", op["output"]]
        self.write(*args)

    def op_set_page_look(self, route: str, expected: dict, state: dict, op: dict) -> None:
        page = self.page(route)
        if page.get(op["key"]) == op["value"]:
            return
        verb = "replace" if op["key"] in page else "add"
        self.patch("page", state["page_id"], [{"op": verb, "path": [op["key"]], "value": op["value"]}])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--confirmation-id", required=True)
    parser.add_argument("--backup-dir", required=True, type=Path)
    parser.add_argument("--pub-dir", required=True, type=Path, help="the saved /pub responses")
    parser.add_argument("--config", type=Path, default=common.DEFAULT_CONFIG)
    parser.add_argument("--now", help="ISO time for the 24-hour check (tests); default: now")
    args = parser.parse_args(argv)
    now = preflight_report.parse_time(args.now) if args.now else datetime.now(timezone.utc)
    progress = {"writes": 0, "created_pages": [], "created_blocks": []}
    try:
        if now is None:
            raise Stop("refused", "--now must be an ISO time with a timezone")
        manifest, config, plan, structure, preflight = preconditions(args, now)
        run = Run(config, plan["target"]["landing_id"], progress)
        for planned in plan["pages"]:
            run.apply_page(planned)
        after = common.get_structure(config["site_slug"])
        result = verify_pages.verify(plan, after, structure, manifest, config)
    except Stop as exc:
        print(json.dumps({"status": exc.status, "writes": progress["writes"], "reason": str(exc),
                          "details": exc.details}, indent=2, ensure_ascii=False))
        return 1
    except (OSError, ValueError, KeyError, common.CliError) as exc:
        print(json.dumps({
            "status": "stopped-partway" if progress["writes"] else "refused",
            "reason": str(exc),
            **progress,
            "next": "back up again, render again from the new backup, and show the plan" if progress["writes"] else None,
        }, indent=2, ensure_ascii=False))
        return 1
    print(json.dumps({
        "status": "applied" if result["ok"] else "applied-with-differences",
        **progress,
        "preflight_requested_at": preflight["requested_at"],
        "verification": result,
        "published_by_this_run": False,
    }, indent=2, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
