"""A stateful stand-in for the `xsolla` CLI, for the xla-pages tests. It never touches a network.

`capabilities="current"` answers --help like CLI 1.9.4: no data connections, bindings, page
SEO, dynamic pages or pinned add-block. `capabilities="proposed"` also answers with the commands
and flags references/cli-gaps.md specifies, in the read-back shapes that file proposes, so the
write path can run end to end in tests. Every call is logged; any other command fails the test.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

TESTS = Path(__file__).resolve().parent
FIXTURES = TESTS / "fixtures"
sys.path.insert(0, str(TESTS.parent / "scripts"))

import xla_common as common  # noqa: E402

CURRENT = {
    ("shopbuilder", "add-page"): ["--slug", "--name", "--path"],
    ("shopbuilder", "add-block"): ["--landing-id", "--page-id", "--block", "--index"],
    ("shopbuilder", "update-block"): ["--landing-id", "--data"],
    ("shopbuilder", "get-structure"): ["--slug"],
}
PROPOSED = {
    **CURRENT,
    ("shopbuilder", "add-page"): ["--slug", "--name", "--path", "--paths-provider", "--provider-input", "--empty"],
    ("shopbuilder", "add-block"): ["--landing-id", "--page-id", "--block", "--package", "--version", "--index"],
    ("shopbuilder", "add-data-connection"): ["--landing-id", "--page-id", "--provider", "--input"],
    ("shopbuilder", "bind-block-field"): ["--landing-id", "--block-id", "--field", "--connection-id", "--output"],
    ("shopbuilder", "set-page-seo"): [
        "--landing-id", "--page-id", "--field", "--value", "--connection-id", "--output",
    ],
}
# What add-page seeds on a new page (native blocks, as CLI 1.9.4 does on a store landing).
SEEDED = ["header", "leadGameSales", "description", "faq", "footer"]


def load_site() -> dict:
    return common.data(json.loads((FIXTURES / "site" / "structure.json").read_text(encoding="utf-8")))


class StandInCli:
    def __init__(self, site: dict | None = None, capabilities: str = "proposed", seed_empty_flag: bool = False,
                 sandbox: bool = False) -> None:
        self.site = copy.deepcopy(site if site is not None else load_site())
        self.table = dict(PROPOSED if capabilities == "proposed" else CURRENT)
        if capabilities == "proposed" and not seed_empty_flag:
            self.table[("shopbuilder", "add-page")] = [f for f in self.table[("shopbuilder", "add-page")] if f != "--empty"]
        self.sandbox = sandbox
        self.calls: list[tuple[str, ...]] = []
        self.counter = 0
        # Default internal values per package and version, taken from the reference blocks.
        self.defaults = {}
        for page in self.site["pages"]:
            for block in page.get("blocks", []):
                package, version = common.block_identity(block)
                if package:
                    self.defaults[(package, version)] = {
                        key: (False if isinstance(value, bool) else "")
                        for key, value in common.block_fields(block).items()
                    }

    # ---------------------------------------------------------------- plumbing

    def writes(self) -> list[tuple[str, ...]]:
        return [call for call in self.calls if common.is_write(call)]

    def next_id(self, prefix: str) -> str:
        self.counter += 1
        return f"{prefix}-{self.counter}"

    def help(self, command: tuple[str, ...]) -> str:
        flags = self.table.get(tuple(command))
        if flags is None:
            return "Usage:\n  xsolla shopbuilder [command]\n\nAvailable Commands:\n  add-block\n  add-page\n"
        lines = [f"Usage:\n  xsolla {' '.join(command)} [flags]\n", "Flags:"]
        lines += [f"      {flag} string   synthetic help" for flag in flags]
        return "\n".join(lines) + "\n"

    def __call__(self, args: list[str]) -> object:
        args = tuple(args)
        self.calls.append(args)
        options, flags, rest = {}, set(), list(args[2:])
        while rest:
            token = rest.pop(0)
            if not token.startswith("--"):
                raise AssertionError(f"stray argument {token!r} in {args}")
            flags.add(token)
            if rest and not rest[0].startswith("--"):
                options[token] = rest.pop(0)
        if args[:2] == ("config", "list"):
            return {"ok": True, "data": {"merchant_id": self.site["merchantId"], "project_id": self.site["projectId"],
                                         "sandbox": self.sandbox}}
        command = args[:2]
        if command not in self.table and command != ("shopbuilder", "get-structure"):
            raise AssertionError(f"the stand-in CLI has no {' '.join(command)}")
        allowed = set(self.table.get(command, [])) | {"--json"}
        unknown = sorted(f for f in flags if f.startswith("--") and f not in allowed)
        if unknown:
            raise common.CliError(f"unknown flag {unknown[0]}")
        handler = getattr(self, "cmd_" + command[1].replace("-", "_"))
        return handler(options, flags)

    def page(self, page_id: str) -> dict:
        return next(p for p in self.site["pages"] if p["_id"] == page_id)

    def block(self, block_id: str) -> dict:
        return next(b for p in self.site["pages"] for b in p.get("blocks", []) if b["_id"] == block_id)

    # ---------------------------------------------------------------- commands

    def cmd_get_structure(self, options: dict, flags: set) -> object:
        if options["--slug"] != self.site["domain"]:
            raise common.CliError("landing not found")
        return {"ok": True, "data": copy.deepcopy(self.site)}

    def cmd_add_page(self, options: dict, flags: set) -> object:
        path = options["--path"]
        page = {
            "_id": self.next_id("page"),
            "name": options["--name"],
            "path": {"pathSegment": path, "type": "dynamic" if ":" in path else "static"},
            "theme": {"enabled": True, "input": {"bg": "#000000"}},
            "blocks": [] if "--empty" in flags else [
                {"_id": self.next_id("seed"), "module": module, "values": {}} for module in SEEDED
            ],
            "seo": {},
            "dataConnections": [],
        }
        if "--paths-provider" in options:
            given = json.loads(options["--provider-input"])
            page["dataConnections"] = [
                {"_id": self.next_id("conn"), "provider": options["--paths-provider"], "kind": "path", "input": given},
                {"_id": self.next_id("conn"), "provider": "ugc-d-data-game-provider-v2", "kind": "value",
                 "input": {"slug": "{path}", "publisherProjectId": given["publisherProjectId"]}},
            ]
        self.site["pages"].append(page)
        return {"ok": True, "data": {"_id": page["_id"]}}

    def cmd_add_block(self, options: dict, flags: set) -> object:
        page = self.page(options["--page-id"])
        if "--package" not in options:
            block = {"_id": self.next_id("block"), "module": options["--block"], "values": {}}
        else:
            key = (options["--package"], options["--version"])
            if key not in self.defaults:
                raise common.CliError(f"{key[0]}@{key[1]} is not published")
            block = {
                "_id": self.next_id("block"), "module": "federated", "hidden": False,
                "values": {"blockId": key[0].split("/")[-1], "package": key[0], "version": key[1],
                           "internalBlockValues": copy.deepcopy(self.defaults[key])},
                "bindings": {},
            }
        index = int(options.get("--index", len(page["blocks"])))
        page["blocks"].insert(index, block)
        return {"ok": True, "data": {"_id": block["_id"]}}

    def cmd_update_block(self, options: dict, flags: set) -> object:
        for change in json.loads(options["--data"]).values():
            if change["type"] == "page":
                target = self.page(change["id"])
            elif change["type"] == "block":
                target = self.block(change["id"])
            else:
                target = self.site
            for patch in change["patches"]:
                parent = target
                for segment in patch["path"][:-1]:
                    parent = parent[segment]
                last = patch["path"][-1]
                if patch["op"] == "remove":
                    del parent[last]
                elif patch["op"] == "add" and isinstance(parent, list):
                    parent.insert(last, patch["value"])
                else:
                    parent[last] = patch["value"]
        return {"ok": True}

    def cmd_add_data_connection(self, options: dict, flags: set) -> object:
        connection = {"_id": self.next_id("conn"), "provider": options["--provider"], "kind": "value",
                      "input": json.loads(options["--input"])}
        self.page(options["--page-id"]).setdefault("dataConnections", []).append(connection)
        return {"ok": True, "data": {"_id": connection["_id"]}}

    def cmd_bind_block_field(self, options: dict, flags: set) -> object:
        block = self.block(options["--block-id"])
        block.setdefault("bindings", {})[options["--field"]] = {
            "connection": options["--connection-id"], "output": options["--output"],
        }
        return {"ok": True}

    def cmd_set_page_seo(self, options: dict, flags: set) -> object:
        page = self.page(options["--page-id"])
        if "--value" in options:
            page.setdefault("seo", {})[options["--field"]] = {"value": options["--value"]}
        else:
            page.setdefault("seo", {})[options["--field"]] = {
                "connection": options["--connection-id"], "output": options["--output"],
            }
        return {"ok": True}
