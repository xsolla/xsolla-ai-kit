#!/usr/bin/env python3
"""Shared helpers for the xla-pages scripts: the manifest, the local config, CLI calls, readers.

Standard library only. Every script runs under `python3 -I`.

Shapes marked VERIFIED were seen in Shop Builder exports (shop-builder-assembly's references).
Shapes marked SITE BUILDER come from the Site Builder server and Editor code, read 2026-11-08.
Shapes marked PROPOSED are what the skill needs the CLI to return. A real read-back that lacks a shape fails
verification instead of passing it.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

SCRIPTS_DIR = Path(__file__).resolve().parent
MANIFEST_PATH = SCRIPTS_DIR / "manifest.json"
DEFAULT_CONFIG = Path(".xsolla") / "xla-pages.json"

SLUG_RE = re.compile(r"^[a-z0-9-]+$")
SITE_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PLACEHOLDER = re.compile(r"\$\{(merchant_id|project_id|site_slug)\}")
PACKAGE_SCOPE = "@xla-pages/"

# Page-level keys the plan may set, and only to the reference page's value. `theme` is
# VERIFIED (pages carry their own theme copy); `background` and `layout` are PROPOSED names.
PAGE_LOOK_KEYS = ("theme", "background", "layout")

# SITE BUILDER: data connections live on the site, in valuesSystem.dataProviderConnections, as
# {id, dataProviderId, input, usedBy: ["page:<id>" | "block:<id>"]}. A bound value is the string
# "#VC:<connection id>:<output>". A dynamic page's slug reaches its data connection through the
# built-in route-params connection.
VC_PREFIX = "#VC:"
VC_VALUE = re.compile(r"#VC:[^<>\"'\s:]+:[^<>\"'\s]+")
ROUTE_PARAMS_CONN_ID = "conn-route-params"
ROUTE_PARAMS_PROVIDER_ID = "route-params-provider"
VALUES_SYSTEM_ID = "current-values-system"
# The manifest's SEO field -> its `L:` string in page.seo (VERIFIED: title, description and
# ogImage hold localization IDs). canonical is a plain page.seo.canonicalUrl (SITE BUILDER).
SEO_STRINGS = {"title": "title", "description": "description", "image": "ogImage"}

# The commands any script may run. Everything else (catalog, liveops, publish, preview,
# verify-website, versions, delete-block, duplicate-block, create-website, create-block,
# custom blocks) is refused before the CLI runs.
READ_COMMANDS = frozenset(
    {
        ("config", "list"),
        ("shopbuilder", "list-websites"),
        ("shopbuilder", "get-landing"),
        ("shopbuilder", "get-structure"),
        ("shopbuilder", "get-block"),
        ("shopbuilder", "get-localization"),
    }
)
WRITE_COMMANDS = frozenset(
    {
        ("shopbuilder", "add-page"),
        ("shopbuilder", "add-block"),
        ("shopbuilder", "update-block"),
        ("shopbuilder", "update-many-localization"),
    }
)


class CliError(RuntimeError):
    """The CLI failed, or a command outside the allowlist was asked for."""


# --------------------------------------------------------------------------- files


def load_json(path: Path, label: str) -> object:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read {label} {path}: {exc}") from None


def load_manifest(path: Path = MANIFEST_PATH) -> dict:
    manifest = load_json(path, "manifest")
    if not isinstance(manifest, dict) or manifest.get("manifest_version") != 1:
        raise ValueError(f"{path} is not an xla-pages manifest (manifest_version 1)")
    return manifest


def load_config(path: Path) -> dict:
    """The user's local .xsolla/xla-pages.json: the one site this skill writes to.

    It holds the real merchant, project and slug, so it is never committed.
    """
    config = load_json(path, "local config")
    if not isinstance(config, dict):
        raise ValueError(f"{path} must hold a JSON object")
    errors = []
    for key in ("merchant_id", "project_id"):
        value = config.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            errors.append(f"{key} must be a positive integer")
    slug = config.get("site_slug")
    if not isinstance(slug, str) or not SITE_SLUG_RE.fullmatch(slug):
        errors.append("site_slug must be the site's lowercase slug")
    published = config.get("write_to_published_site", False)
    if not isinstance(published, bool):
        errors.append("write_to_published_site must be true or false")
    unverified = config.get("allow_unverified_updates", False)
    if not isinstance(unverified, bool):
        errors.append("allow_unverified_updates must be true or false")
    unknown = sorted(set(config) - {"merchant_id", "project_id", "site_slug", "write_to_published_site",
                                    "allow_unverified_updates"})
    if unknown:
        errors.append("unknown keys: " + ", ".join(unknown))
    if errors:
        raise ValueError(f"{path}: " + "; ".join(errors))
    return {**config, "write_to_published_site": published, "allow_unverified_updates": unverified}


def updates_verified(manifest: dict) -> bool:
    return (((manifest.get("writes") or {}).get("updates") or {}).get("verified")) is True


def updates_blocked(pages: list, manifest: dict, config: dict) -> str | None:
    """Why this plan's updates of existing pages can't run yet, or None.

    Until the manifest's writes.updates.verified is true, updates are off. The local config's
    allow_unverified_updates opens them for the one run that verifies them: one updated page, no
    created ones.
    """
    updated = [p.get("route") for p in pages if p.get("action") == "update"]
    if not updated or updates_verified(manifest):
        return None
    if not config.get("allow_unverified_updates"):
        return ("updates of existing pages are off until one run on a test page confirms the write "
                "shapes (manifest writes.updates); this plan updates " + ", ".join(updated))
    created = [p.get("route") for p in pages if p.get("action") == "create"]
    if len(updated) > 1 or created:
        return ("allow_unverified_updates allows a plan that updates one page and creates none; this plan "
                f"updates {', '.join(updated)}" + (f" and creates {', '.join(created)}" if created else ""))
    return None


def resolve(value: object, config: dict) -> object:
    """Replace ${merchant_id}, ${project_id} and ${site_slug} with the local config's values."""
    if isinstance(value, str):
        return PLACEHOLDER.sub(lambda match: str(config[match.group(1)]), value)
    if isinstance(value, list):
        return [resolve(item, config) for item in value]
    if isinstance(value, dict):
        return {key: resolve(item, config) for key, item in value.items()}
    return value


def write_json(path: Path, value: object) -> None:
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- hashing


def canonical_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def stable_structure(value: object) -> object:
    """Drop the `_id`s Shop Builder regenerates on every read inside `components` arrays."""
    if isinstance(value, list):
        return [stable_structure(item) for item in value]
    if not isinstance(value, dict):
        return value
    out = {}
    for key, item in value.items():
        if key == "components" and isinstance(item, list):
            out[key] = [
                stable_structure({k: v for k, v in c.items() if k != "_id"})
                if isinstance(c, dict)
                else stable_structure(c)
                for c in item
            ]
        else:
            out[key] = stable_structure(item)
    return out


def structure_hash(value: object) -> str:
    return canonical_hash(stable_structure(value))


def confirmation_id(plan: dict) -> str:
    body = {key: value for key, value in plan.items() if key != "confirmation_id"}
    return "sha256:" + canonical_hash(body)[:12]


# --------------------------------------------------------------------------- CLI


def data(value: object) -> object:
    if isinstance(value, dict) and value.get("ok") is True and "data" in value:
        return value["data"]
    return value


def execute(args: list[str]) -> object:
    """Run `xsolla <args> --json` and parse its output. Tests replace this function."""
    result = subprocess.run(
        ["xsolla", *args, "--json"], capture_output=True, text=True, encoding="utf-8", check=False
    )
    if result.returncode:
        detail = (result.stderr or "").strip() or (result.stdout or "").strip()
        raise CliError(f"xsolla {' '.join(args[:2])} failed: {detail or result.returncode}")
    try:
        return json.loads(result.stdout or "")
    except json.JSONDecodeError:
        raise CliError(f"xsolla {' '.join(args[:2])} returned no JSON") from None


def execute_help(command: tuple[str, ...]) -> str:
    """Run `xsolla <command> --help` and return its text. Tests replace this function."""
    try:
        result = subprocess.run(
            ["xsolla", *command, "--help"], capture_output=True, text=True, encoding="utf-8", check=False
        )
    except OSError:
        return ""
    return (result.stdout or "") + (result.stderr or "")


def run_json(*args: str) -> object:
    """Run an allowlisted CLI command. Anything else stops before the CLI runs."""
    if any(arg == "--force" or arg.startswith("--force=") for arg in args):
        raise CliError("--force is never passed")
    if tuple(args[:2]) not in READ_COMMANDS | WRITE_COMMANDS:
        raise CliError(f"xsolla {' '.join(args[:2])} is not a command this skill runs")
    return execute(list(args))


def is_write(args: tuple[str, ...] | list[str]) -> bool:
    return tuple(args[:2]) in WRITE_COMMANDS


def has_command(help_text: str, command: tuple[str, ...]) -> bool:
    """For an unknown subcommand the CLI prints its parent's help; only the usage line tells."""
    usage = " ".join(("xsolla", *command))
    return any(
        line.strip() == usage or line.strip().startswith(usage + " ")
        for line in help_text.splitlines()
    )


def has_flag(help_text: str, flag: str) -> bool:
    return re.search(r"(?<![\w-])" + re.escape(flag) + r"(?![\w-])", help_text) is not None


def cli_context() -> dict:
    config = data(run_json("config", "list"))
    if not isinstance(config, dict):
        raise CliError("xsolla config list returned an unexpected shape")
    return config


def check_cli_context(config: dict) -> None:
    """The CLI must point at the configured merchant and project, with sandbox mode off."""
    cli = cli_context()
    if cli.get("merchant_id") != config["merchant_id"] or cli.get("project_id") != config["project_id"]:
        raise CliError("the CLI's merchant and project are not the ones in the local config")
    if cli.get("sandbox") is True:
        raise CliError("the CLI's sandbox mode is on; Shop Builder has no sandbox")


def get_structure(slug: str) -> dict:
    value = data(run_json("shopbuilder", "get-structure", "--slug", slug))
    if not isinstance(value, dict) or not isinstance(value.get("pages"), list):
        raise CliError("get-structure returned an unexpected shape")
    return value


def get_localization(slug: str) -> dict:
    value = data(run_json("shopbuilder", "get-localization", "--slug", slug))
    if not isinstance(value, dict):
        raise CliError("get-localization returned an unexpected shape")
    return value


def site_locale(manifest: dict) -> str:
    return str((manifest.get("site") or {}).get("default_locale") or "en-US")


# --------------------------------------------------------------------------- target


def same_id(actual: object, expected: object) -> bool:
    return isinstance(actual, (str, int)) and not isinstance(actual, bool) and str(actual) == str(expected)


def is_published(structure: dict) -> bool:
    return structure.get("published") not in (None, False)


def check_target(structure: dict, config: dict, for_write: bool = True) -> None:
    """Stop unless the structure is the configured site, and refuse any other published site.

    A published site is allowed only when it is the configured site and the config says
    `write_to_published_site: true`. Real IDs never live in this public repo, so the one
    exception is pinned by the local config.
    """
    problems = []
    if structure.get("domain") != config["site_slug"]:
        problems.append("the site slug")
    if not same_id(structure.get("merchantId"), config["merchant_id"]):
        problems.append("the merchant")
    if not same_id(structure.get("projectId"), config["project_id"]):
        problems.append("the project")
    if problems:
        raise CliError("the site is not the one in the local config: " + ", ".join(problems) + " differ")
    if for_write and is_published(structure) and not config.get("write_to_published_site"):
        raise CliError(
            "the site is published, and this skill never writes to a published site unless the "
            "local config names it with write_to_published_site: true"
        )


# --------------------------------------------------------------------------- readers


def page_route(page: object) -> str | None:
    """VERIFIED for static pages: `path` is "/x" or {"pathSegment": "/x", "type": "static"}.
    SITE BUILDER for dynamic pages: {"type": "dynamic", "pathSegment": "/game/:slug",
    "connectionId": <the paths connection>}."""
    if not isinstance(page, dict):
        return None
    path = page.get("path")
    if isinstance(path, str):
        return path
    if isinstance(path, dict) and isinstance(path.get("pathSegment"), str):
        return path["pathSegment"]
    return None


def find_page(structure: dict, route: str) -> dict | None:
    matches = [page for page in structure.get("pages", []) if page_route(page) == route]
    if len(matches) > 1:
        raise ValueError(f"the site has {len(matches)} pages at {route}")
    return matches[0] if matches else None


def block_identity(block: dict) -> tuple[str | None, str | None]:
    """(package, version) of a federated block.

    VERIFIED: `module: "federated"`, the blocks-service id in `values.blockId` and the version
    in `values.version`. The package is read from `values.blockId` when it is the scoped name
    (`@xla-pages/hero`), else from a PROPOSED `values.package`. An unscoped id such as `hero`
    is not enough to tell `@xla-pages/hero` from another hero.
    """
    if not isinstance(block, dict) or block.get("module") != "federated":
        return None, None
    values = block.get("values") if isinstance(block.get("values"), dict) else {}
    package = values.get("package") or values.get("packageName")
    if not package:
        block_id = values.get("blockId")
        package = block_id if isinstance(block_id, str) and block_id.startswith("@") else None
    version = values.get("version")
    return (package if isinstance(package, str) else None, version if isinstance(version, str) else None)


def block_label(block: dict) -> str:
    package, version = block_identity(block)
    if package:
        return f"{package}@{version or '?'}"
    module = block.get("module") if isinstance(block, dict) else None
    if module == "federated":
        values = block.get("values") or {}
        return f"federated:{values.get('blockId', '?')}@{values.get('version', '?')}"
    return str(module)


def block_fields(block: dict) -> dict:
    """VERIFIED shape for federated blocks: settings live in `values.internalBlockValues`."""
    values = block.get("values") if isinstance(block, dict) else None
    fields = values.get("internalBlockValues") if isinstance(values, dict) else None
    return fields if isinstance(fields, dict) else {}


def parse_vc(value: object) -> tuple[str, str] | None:
    """(connection id, output) of a whole bound value "#VC:<connection>:<output>", else None."""
    if not isinstance(value, str) or not VC_VALUE.fullmatch(value):
        return None
    _, connection, output = value.split(":", 2)
    return connection, output


def vc(connection_id: str, output: str) -> str:
    return f"{VC_PREFIX}{connection_id}:{output}"


def page_usage(page_id: object) -> str:
    return f"page:{page_id}"


def block_usage(block_id: object) -> str:
    return f"block:{block_id}"


def stable_id(*parts: object) -> str:
    """A 24-hex id derived from its parts, so a rerun writes the same connection id."""
    return hashlib.sha256(":".join(map(str, parts)).encode("utf-8")).hexdigest()[:24]


def block_bindings(block: dict) -> dict:
    """SITE BUILDER: a bound federated field holds "#VC:<connection>:<output>" in
    `values.internalBlockValues.<field>` (the value it had moves to `values.preBindValues`)."""
    return {
        field: {"connection": parsed[0], "output": parsed[1]}
        for field, value in block_fields(block).items()
        if (parsed := parse_vc(value))
    }


def site_connections(structure: dict) -> dict | None:
    """SITE BUILDER: `valuesSystem.dataProviderConnections` by id; None when get-structure
    doesn't return it, which the plan and the check treat as a stop."""
    values = structure.get("valuesSystem") if isinstance(structure, dict) else None
    connections = values.get("dataProviderConnections") if isinstance(values, dict) else None
    if not isinstance(connections, dict):
        return None
    return {key: value for key, value in connections.items() if isinstance(value, dict)}


def normalize_input(value: object) -> object:
    """A connection input as the manifest writes it: a route-params reference reads "{path}"."""
    if isinstance(value, dict):
        return {key: normalize_input(item) for key, item in value.items()}
    parsed = parse_vc(value)
    if parsed and parsed[0] == ROUTE_PARAMS_CONN_ID:
        return "{path}"
    return value


def connection_view(connection_id: str, connection: dict) -> dict:
    return {
        "_id": connection.get("id", connection_id),
        "provider": connection.get("dataProviderId"),
        "input": normalize_input(connection.get("input") or {}),
        "usedBy": list(connection.get("usedBy") or []),
    }


def all_connections(structure: dict) -> dict:
    return {key: connection_view(key, value) for key, value in (site_connections(structure) or {}).items()}


def page_connections(structure: dict, page: dict) -> list[dict]:
    """The connections the page or one of its blocks uses, without the built-in route-params one."""
    if not isinstance(page, dict):
        return []
    path = page.get("path") if isinstance(page.get("path"), dict) else {}
    direct = {path.get("connectionId"), page.get("dataConnectionId")}
    usages = {page_usage(page.get("_id"))} | {
        block_usage(block.get("_id")) for block in page.get("blocks") or [] if isinstance(block, dict)
    }
    return [
        view
        for key, view in all_connections(structure).items()
        if view["provider"] != ROUTE_PARAMS_PROVIDER_ID
        and key != ROUTE_PARAMS_CONN_ID
        and (key in direct or usages & set(view["usedBy"]))
    ]


def localization_text(localization: dict, page_id: object, lid: str, locale: str) -> tuple[str, str, object]:
    """(scope, description, text in locale) of an `L:` string: the page's texts or `common`.
    VERIFIED get-localization shape: pages.<page>.texts.<L:id>.{description, translations}."""
    localization = localization if isinstance(localization, dict) else {}
    page_texts = ((localization.get("pages") or {}).get(str(page_id)) or {}).get("texts") or {}
    for scope, texts in ((str(page_id), page_texts), ("common", localization.get("common") or {})):
        entry = texts.get(lid) if isinstance(texts, dict) else None
        if isinstance(entry, dict):
            translations = entry.get("translations") if isinstance(entry.get("translations"), dict) else {}
            text = translations.get(locale, translations.get(locale.split("-")[0]))
            description = entry.get("description")
            return scope, description if isinstance(description, str) else "", text
    return str(page_id), "", None


def page_seo(page: dict, localization: dict, locale: str) -> dict:
    """{field: {"value": text} | {"connection": id, "output": name}} for title, description,
    image (localized `L:` strings, a bound one holds "#VC:…") and canonical (page.seo.canonicalUrl)."""
    seo = page.get("seo") if isinstance(page, dict) and isinstance(page.get("seo"), dict) else {}
    found: dict = {}
    for field, slot in SEO_STRINGS.items():
        lid = seo.get(slot)
        if not (isinstance(lid, str) and lid.startswith("L:")):
            continue
        _, _, text = localization_text(localization, page.get("_id"), lid, locale)
        if not isinstance(text, str) or not text:
            continue
        parsed = parse_vc(text)
        found[field] = {"connection": parsed[0], "output": parsed[1]} if parsed else {"value": text}
    canonical = seo.get("canonicalUrl")
    if isinstance(canonical, str) and canonical:
        found["canonical"] = {"value": canonical}
    return found


def has_custom_code(block: dict) -> bool:
    if not isinstance(block, dict):
        return False
    if block.get("module") == "html":
        return True
    script = (block.get("values") or {}).get("script") if isinstance(block.get("values"), dict) else None
    if isinstance(script, dict):
        script = script.get("value") or script.get("code")
    return isinstance(script, str) and bool(script.strip())


# --------------------------------------------------------------------------- manifest model


def page_type(manifest: dict, name: str) -> dict:
    types = manifest.get("page_types") or {}
    if name not in types:
        raise ValueError(f"unknown page type {name!r}")
    return types[name]


def block_keys(entry: dict) -> list[str]:
    return [key.strip() for key in str(entry.get("block", "")).split("|") if key.strip()]


def package_of(manifest: dict, key: str) -> str:
    package = ((manifest.get("blocks") or {}).get("packages") or {}).get(key, {}).get("package")
    if not isinstance(package, str) or not package.startswith(PACKAGE_SCOPE):
        raise ValueError(f"block {key!r} has no @xla-pages package in the manifest")
    return package


def key_of_package(manifest: dict) -> dict[str, str]:
    return {
        spec["package"]: key
        for key, spec in ((manifest.get("blocks") or {}).get("packages") or {}).items()
        if isinstance(spec, dict) and isinstance(spec.get("package"), str)
    }


def split_source(reference: str) -> tuple[str, str]:
    """"game_data.title" -> ("game_data", "title")."""
    source, _, output = reference.partition(".")
    if not source or not output:
        raise ValueError(f"{reference!r} is not a <source>.<output> reference")
    return source, output


def provider_spec(manifest: dict, source: str, config: dict) -> dict:
    spec = (manifest.get("data_providers") or {}).get(source)
    if not isinstance(spec, dict) or not isinstance(spec.get("id"), str):
        raise ValueError(f"{source!r} is not a data provider in the manifest")
    return {"key": source, "provider": spec["id"], "kind": spec.get("kind"), "input": resolve(spec.get("input"), config)}


def provider_outputs(manifest: dict, source: str) -> set[str]:
    spec = (manifest.get("data_providers") or {}).get(source) or {}
    outputs = spec.get("outputs") or {}
    return set(outputs) if isinstance(outputs, dict) else set()


def reference_provider(manifest: dict) -> str:
    """The provider of the payment_provider reference page, e.g. "paysafecard"."""
    url = page_type(manifest, "payment_provider").get("reference_page", "")
    return urlsplit(url).path.rstrip("/").rsplit("/", 1)[-1]


def route_for(manifest: dict, type_name: str, provider: str | None = None) -> str:
    route = str(page_type(manifest, type_name)["route"])
    if "{provider}" in route:
        if not provider:
            raise ValueError(f"{type_name} routes need a provider")
        route = route.replace("{provider}", provider)
    return route


def reference_route(manifest: dict, type_name: str) -> str:
    spec = page_type(manifest, type_name)
    if spec.get("kind") == "dynamic":
        return route_for(manifest, type_name, reference_provider(manifest) if "{provider}" in spec["route"] else None)
    return urlsplit(spec.get("reference_page", "")).path


def deep_copy(value: object) -> object:
    return copy.deepcopy(value)
