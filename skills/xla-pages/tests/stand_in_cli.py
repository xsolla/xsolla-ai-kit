"""A stateful stand-in for the `xsolla` CLI, for the xla-pages tests. It never touches a network.

It keeps a Site Builder site in the shapes the Site Builder server code uses:
site-level data connections in `valuesSystem.dataProviderConnections`, "#VC:" bound values in
federated blocks, SEO texts in the localization, and the batch patch API behind `update-block`
(entities block, page, site and valuesSystem).

`capabilities="current"` answers --help like CLI 1.9.4. `capabilities="proposed"` also lists the
flags scripts/cli_gate.py waits for (add-page --provider-id/--provider-input, add-block
--package/--version), so the write path can run end to end in tests. Like the server,
add-block falls back to the latest published version of a package when the asked one is missing.
Every call is logged; any other command fails the test.
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
    ("shopbuilder", "update-many-localization"): ["--slug", "--data"],
    ("shopbuilder", "get-structure"): ["--slug"],
    ("shopbuilder", "get-localization"): ["--slug"],
}
PROPOSED = {
    **CURRENT,
    ("shopbuilder", "add-page"): ["--slug", "--name", "--path", "--provider-id", "--provider-input"],
    ("shopbuilder", "add-block"): ["--landing-id", "--page-id", "--block", "--package", "--version", "--index"],
}
# What add-page seeds on a new page (native blocks, as CLI 1.9.4 does on a store landing).
SEEDED = ["header", "leadGameSales", "description", "faq", "footer"]


def load_fixture(name: str) -> dict:
    return common.data(json.loads((FIXTURES / "site" / name).read_text(encoding="utf-8")))


def load_site() -> dict:
    return load_fixture("structure.json")


def load_localization() -> dict:
    return load_fixture("localization.json")


def version_key(version: str) -> tuple:
    main, _, pre = version.partition("-")
    return tuple(int(part) for part in main.split(".")), pre == "", pre


class StandInCli:
    def __init__(self, site: dict | None = None, capabilities: str = "proposed", blank_flag: bool = False,
                 sandbox: bool = False, localization: dict | None = None) -> None:
        self.site = copy.deepcopy(site if site is not None else load_site())
        self.localization = copy.deepcopy(localization if localization is not None else load_localization())
        self.table = dict(PROPOSED if capabilities == "proposed" else CURRENT)
        if blank_flag:
            key = ("shopbuilder", "add-page")
            self.table[key] = [*self.table[key], "--type"]
        self.sandbox = sandbox
        self.calls: list[tuple[str, ...]] = []
        self.counter = 0
        # Published versions per package, with their default values, from the reference blocks.
        self.defaults: dict[tuple[str, str], dict] = {}
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
        if command not in self.table:
            raise AssertionError(f"the stand-in CLI has no {' '.join(command)}")
        allowed = set(self.table[command]) | {"--json"}
        unknown = sorted(f for f in flags if f not in allowed)
        if unknown:
            raise common.CliError(f"unknown flag {unknown[0]}")
        return getattr(self, "cmd_" + command[1].replace("-", "_"))(options, flags)

    def page(self, page_id: str) -> dict:
        return next(p for p in self.site["pages"] if p["_id"] == page_id)

    def block(self, block_id: str) -> dict:
        return next(b for p in self.site["pages"] for b in p.get("blocks", []) if b["_id"] == block_id)

    def connections(self) -> dict:
        return self.site.setdefault("valuesSystem", {}).setdefault("dataProviderConnections", {})

    # ---------------------------------------------------------------- reads

    def cmd_get_structure(self, options: dict, flags: set) -> object:
        if options["--slug"] != self.site["domain"]:
            raise common.CliError("landing not found")
        return {"ok": True, "data": copy.deepcopy(self.site)}

    def cmd_get_localization(self, options: dict, flags: set) -> object:
        return {"ok": True, "data": copy.deepcopy(self.localization)}

    # ---------------------------------------------------------------- writes

    def cmd_add_page(self, options: dict, flags: set) -> object:
        path = options["--path"]
        page_id = self.next_id("page")
        blank = options.get("--type") == "blank"
        page = {
            "_id": page_id,
            "name": options["--name"],
            "path": {"type": "static", "pathSegment": path},
            "theme": {"enabled": False} if blank else {"enabled": True, "input": {"bg": "#000000"}},
            "blocks": [] if blank and self.site.get("layouts") else [
                {"_id": self.next_id("seed"), "module": module, "values": {}} for module in SEEDED
            ],
            "seo": {},
        }
        texts = self.localization.setdefault("pages", {}).setdefault(page_id, {"texts": {}})["texts"]
        for slot in ("title", "description", "ogImage"):
            lid = f"L:{page_id}-seo-{slot}"
            page["seo"][slot] = lid
            texts[lid] = {"description": "", "translations": {}}
        if "--provider-id" in options:
            # As the server's add-page: reuse a paths connection with the same provider and input,
            # add the route-params usage, and hand out the id of the linked data connection,
            # which the client writes.
            given = json.loads(options["--provider-input"])
            conns = self.connections()
            reuse = next((c for c in conns.values() if c["dataProviderId"] == options["--provider-id"]
                          and c["input"] == given), None)
            if reuse is None:
                reuse = {"id": self.next_id("conn"), "dataProviderId": options["--provider-id"],
                         "input": given, "usedBy": []}
                conns[reuse["id"]] = reuse
            reuse["usedBy"].append(common.page_usage(page_id))
            route_params = conns.setdefault(common.ROUTE_PARAMS_CONN_ID, {
                "id": common.ROUTE_PARAMS_CONN_ID, "dataProviderId": common.ROUTE_PARAMS_PROVIDER_ID,
                "input": {}, "usedBy": []})
            route_params["usedBy"].append(common.page_usage(page_id))
            page["path"] = {"type": "dynamic", "pathSegment": path, "connectionId": reuse["id"]}
            page["dataConnectionId"] = self.next_id("dataconn")
        self.site["pages"].append(page)
        return {"ok": True, "data": copy.deepcopy(page)}

    def cmd_add_block(self, options: dict, flags: set) -> object:
        page = self.page(options["--page-id"])
        if "--package" not in options:
            block = {"_id": self.next_id("block"), "module": options["--block"], "values": {}}
        else:
            package, version = options["--package"], options["--version"]
            versions = sorted((v for p, v in self.defaults if p == package), key=version_key)
            if not versions:
                raise common.CliError(f"{package} is not in the blocks service")
            if version not in versions:
                version = versions[-1]  # the server's "falling back to latest stable version"
            block = {
                "_id": self.next_id("block"), "module": "federated", "hidden": False,
                "values": {"host": "https://blocks.example.invalid/", "blockId": package, "version": version,
                           "internalBlockValues": copy.deepcopy(self.defaults[(package, version)]),
                           "resources": {"localizedValues": {}, "media": {}}},
            }
        index = int(options.get("--index", len(page["blocks"])))
        page["blocks"].insert(index, block)
        return {"ok": True, "data": {"_id": block["_id"]}}

    def cmd_update_block(self, options: dict, flags: set) -> object:
        for change in json.loads(options["--data"]).values():
            kind = change["type"]
            if kind == "page":
                target = self.page(change["id"])
            elif kind == "block":
                target = self.block(change["id"])
            elif kind == "valuesSystem":
                if change["id"] != common.VALUES_SYSTEM_ID:
                    raise common.CliError("valuesSystem not found")
                target = self.site.setdefault("valuesSystem", {})
            else:
                target = self.site
            for patch in change["patches"]:
                parent = target
                for segment in patch["path"][:-1]:
                    if isinstance(parent, dict) and segment not in parent:
                        parent[segment] = {}  # as patch-values-system: create intermediates
                    parent = parent[segment]
                last = patch["path"][-1]
                if patch["op"] == "remove":
                    del parent[last]
                elif patch["op"] == "add" and isinstance(parent, list):
                    parent.insert(last, patch["value"])
                else:
                    parent[last] = patch["value"]
        return {"ok": True}

    def cmd_update_many_localization(self, options: dict, flags: set) -> object:
        body = json.loads(options["--data"])
        for scope, values in body["perScopeValues"].items():
            texts = (self.localization.setdefault("common", {}) if scope == "common"
                     else self.localization.setdefault("pages", {}).setdefault(scope, {"texts": {}})["texts"])
            for lid, value in values.items():
                entry = texts.setdefault(lid, {"description": "", "translations": {}})
                entry["description"] = value["description"]
                entry.setdefault("translations", {})[body["locale"]] = value["translation"]
        return {"ok": True}
