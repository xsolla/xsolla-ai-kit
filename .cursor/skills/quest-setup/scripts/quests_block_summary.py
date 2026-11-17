#!/usr/bin/env python3
"""Read-only summary of the Quests block(s) on one Shop Builder site.

Runs `xsolla shopbuilder get-structure` and `get-localization` (both read-only), finds every
Quests block, resolves its heading and card override texts, and, when the Quest Platform
credential in the working folder belongs to the site's project, the quest names. Never writes.

Usage:
    python3 quests_block_summary.py --slug <slug> [--environment <name>]
    python3 quests_block_summary.py [--environment <name>]

Without --slug it lists the sites and reads each structure. `sites` gives every site with
its count of visible Quests blocks; when exactly one site has a visible Quests block, `site`
is that site and the output also carries its full summary (else `site` is null).

Output: one JSON object on stdout. The ids (merchant, project, block, quest) are for a
block_operations brief only, never for a reply. The summary also includes page module ids
and an allowlisted, normalized saved appearance readback; unknown open-map values
are omitted. Exit codes: 0 read ok, 1 a site read failed.
Python 3.9+, standard library only.
"""
from __future__ import annotations

import argparse
import base64
import html
import http.client
import json
import math
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, NamedTuple, Optional
from urllib.parse import urlparse

sys.dont_write_bytecode = True  # keep the installed skill folder clean

QP_BASE = "https://quests-platform.xsolla.com"
TIMEOUT_SECONDS = 20
MAX_RESPONSE_BYTES = 5 * 1024 * 1024
CREDENTIAL_NAMES = ("XSOLLA_MERCHANT_ID", "XSOLLA_PROJECT_ID", "XSOLLA_PROJECT_API_KEY")
ID_PATTERN = re.compile(r"[0-9]+")

BLOCK_ID = "_quest-platform_quests-block"
TAG = re.compile(r"<[^>]+>")
QUEST_PAGES = 5
QUEST_PAGE_SIZE = 50
THEME_IDS = {"site-builder", "xsolla-pages", "custom"}
PRESET_FIELDS = {
    "cardAlign": {"start", "center", "end"},
    "blockBackground": {"transparent", "primary", "secondary"},
    "cardBackground": {"transparent", "primary", "secondary"},
    "buttonStyle": {"primary", "secondary", "tertiary", "theme-default"},
}
PALETTE_FIELDS = {
    "accent", "sectionBackground", "cardBackground", "primaryText",
    "secondaryText", "border", "actionText",
}
FONT_FIELDS = {"bodyFont", "headingFont", "buttonFont"}
WEIGHT_FIELDS = {"headingWeight", "bodyWeight", "buttonWeight"}
LINE_HEIGHT_FIELDS = {
    "headingLineHeight", "bodyLineHeight", "buttonLineHeight",
}
SIZE_FIELDS = {"headingSize", "bodySize", "buttonSize"}
GEOMETRY_FIELDS = {
    "maxWidth", "gutter", "mobileGutter", "sectionPadding", "cardPadding",
    "gap", "radius", "buttonRadius", "buttonHeight", "columns", "railInset",
}
FONT_TOKENS = {"host-body", "host-heading", "host-button"}
SAFE_FONT = re.compile(r"(?=.*[A-Za-z0-9])[A-Za-z0-9 _-]{1,64}\Z")
HEX6 = re.compile(r"#[0-9a-fA-F]{6}\Z")
VERSION = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9][A-Za-z0-9.-]*)?\Z")


class QuestLookup(NamedTuple):
    quests: Dict[str, Dict[str, Any]]
    complete: bool


Runner = Callable[[List[str]], Dict[str, Any]]
QuestFetcher = Callable[[str, str], Optional[QuestLookup]]


def run_cli(args: List[str]) -> Dict[str, Any]:
    proc = subprocess.run(
        ["xsolla", "shopbuilder", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        return {"ok": False}
    try:
        return json.loads(proc.stdout)
    except ValueError:
        return {"ok": False}


class Credentials:
    """Publisher credential set. repr() never shows the key."""

    def __init__(self, merchant_id: str, project_id: str, api_key: str) -> None:
        self.merchant_id = merchant_id
        self.project_id = project_id
        self._api_key = api_key

    def basic_token(self) -> str:
        return base64.b64encode(f"{self.merchant_id}:{self._api_key}".encode("utf-8")).decode("ascii")

    def __repr__(self) -> str:
        return "Credentials(<redacted>)"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Never follow redirects: the Basic credential must not reach another host."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        return None


def read_dotenv(path: Path) -> Dict[str, str]:
    """Parse KEY=VALUE lines as text. Never executed or sourced."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}
    values: Dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        values[key.strip()] = value
    return values


def _complete_set(values: Mapping[str, str]) -> Optional[Credentials]:
    merchant, project, key = (str(values.get(name, "")).strip() for name in CREDENTIAL_NAMES)
    if not key or not ID_PATTERN.fullmatch(merchant) or not ID_PATTERN.fullmatch(project):
        return None
    return Credentials(merchant, project, key)


def resolve_credentials(environ: Mapping[str, str], cwd: Path) -> Optional[Credentials]:
    """All-or-nothing: the process environment, else ./.env. Never mixed. None when not set up."""
    return _complete_set(environ) or _complete_set(read_dotenv(cwd / ".env"))


def get_quests_page(creds: Credentials, page: int) -> Optional[Dict[str, Any]]:
    """One page of the configured project's quests, or None on any failure. Read-only."""
    url = (
        f"{QP_BASE}/api/v2/merchants/{creds.merchant_id}/projects/{creds.project_id}/quests"
        f"?page={page}&limit={QUEST_PAGE_SIZE}"
    )
    request = urllib.request.Request(
        url, method="GET",
        headers={"Accept": "application/json", "Authorization": "Basic " + creds.basic_token()},
    )
    try:
        response = urllib.request.build_opener(_NoRedirect).open(request, timeout=TIMEOUT_SECONDS)
        try:
            if int(response.status) != 200:
                return None
            raw = response.read(MAX_RESPONSE_BYTES)
        finally:
            response.close()
        body = json.loads(raw.decode("utf-8", errors="replace"))
    except (OSError, ValueError, http.client.HTTPException):
        return None
    return body if isinstance(body, dict) else None


def fetch_quests(merchant: str, project: str) -> Optional[QuestLookup]:
    """Bounded quest lookup, or None when access is missing, mismatched or fails."""
    creds = resolve_credentials(os.environ, Path.cwd())
    if creds is None or (creds.merchant_id, creds.project_id) != (str(merchant), str(project)):
        return None
    quests: Dict[str, Dict[str, Any]] = {}
    for page in range(1, QUEST_PAGES + 1):
        body = get_quests_page(creds, page)
        if body is None:
            return None
        for quest in body.get("data") or []:
            quests[str(quest.get("id"))] = quest
        try:
            total = int(body.get("total") or 0)
        except (TypeError, ValueError):
            return None
        if page * QUEST_PAGE_SIZE >= total:
            return QuestLookup(quests, True)
    return QuestLookup(quests, False)


def _plain(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    return html.unescape(TAG.sub("", text)).strip()


def _is_quests_block(block: Dict[str, Any]) -> bool:
    values = block.get("values") or {}
    host = values.get("host")
    if host:
        return BLOCK_ID in str(host)
    return block.get("module") == BLOCK_ID or values.get("blockId") == BLOCK_ID


def _module_id(block: Dict[str, Any]) -> Optional[str]:
    """Return an observed module id, never the host URL or arbitrary block data."""
    module = block.get("module")
    if (
        isinstance(module, str)
        and module not in {"federated", "custom"}
        and re.fullmatch(r"[A-Za-z0-9._-]{1,128}", module)
    ):
        return module
    values = block.get("values") or {}
    block_id = values.get("blockId")
    if isinstance(block_id, str) and re.fullmatch(r"[A-Za-z0-9._-]{1,128}", block_id):
        return block_id
    host = values.get("host")
    if isinstance(host, str):
        parts = [part for part in urlparse(host).path.split("/") if part]
        if "site-builder-modules" in parts:
            index = parts.index("site-builder-modules") + 1
            if index < len(parts) and re.fullmatch(r"[A-Za-z0-9._-]{1,128}", parts[index]):
                return parts[index]
    return None


def _summary_appearance(values: Dict[str, Any], internal: Dict[str, Any]) -> Dict[str, Any]:
    """Return recognized saved appearance fields without exposing open-map data."""
    saved_theme = internal.get("themeId")
    theme_status = (
        "missing" if "themeId" not in internal
        else "known" if isinstance(saved_theme, str) and saved_theme in THEME_IDS
        else "unsupported"
    )
    appearance = internal.get("themeAppearance")
    invalid: list[str] = []
    if not isinstance(appearance, dict):
        if "themeAppearance" in internal:
            invalid.append("themeAppearance")
        appearance = {}

    unknown = set(appearance) - {"site-builder", "xsolla-pages", "custom"}
    saved_version = values.get("version")
    version_status = (
        "missing" if "version" not in values
        else "present" if isinstance(saved_version, str) and VERSION.fullmatch(saved_version)
        else "invalid"
    )
    result: Dict[str, Any] = {
        "module_id": BLOCK_ID,
        "version": saved_version if version_status == "present" else None,
        "version_status": version_status,
        "theme_id": saved_theme if theme_status == "known" else None,
        "theme_id_status": theme_status,
        "presets": {},
        "custom": {},
    }

    def safe_preset(theme: str) -> Dict[str, Any]:
        raw = appearance.get(theme)
        if not isinstance(raw, dict):
            if theme in appearance:
                invalid.append(f"themeAppearance.{theme}")
            return {}
        out = {}
        unknown.update(set(raw) - set(PRESET_FIELDS))
        for field, allowed in PRESET_FIELDS.items():
            if field not in raw:
                continue
            if isinstance(raw[field], str) and raw[field] in allowed:
                out[field] = raw[field]
            else:
                invalid.append(f"themeAppearance.{theme}.{field}")
        return out

    result["presets"] = {
        "site-builder": safe_preset("site-builder"),
        "xsolla-pages": safe_preset("xsolla-pages"),
    }

    raw_custom = appearance.get("custom")
    if isinstance(raw_custom, dict):
        custom: Dict[str, Any] = {}
        allowed_top = {"version", "baseThemeId", "palette", "typography", "geometry"}
        unknown.update(set(raw_custom) - allowed_top)
        if "version" in raw_custom:
            if type(raw_custom["version"]) is int and raw_custom["version"] == 1:
                custom["version"] = 1
            else:
                invalid.append("themeAppearance.custom.version")
        if "baseThemeId" in raw_custom:
            if (
                isinstance(raw_custom["baseThemeId"], str)
                and raw_custom["baseThemeId"] in {"site-builder", "xsolla-pages"}
            ):
                custom["baseThemeId"] = raw_custom["baseThemeId"]
            else:
                invalid.append("themeAppearance.custom.baseThemeId")

        raw_palette = raw_custom.get("palette")
        if isinstance(raw_palette, dict):
            palette = {}
            unknown.update(set(raw_palette) - PALETTE_FIELDS)
            for field in PALETTE_FIELDS:
                if field not in raw_palette:
                    continue
                value = raw_palette[field]
                if isinstance(value, str) and HEX6.fullmatch(value):
                    palette[field] = value
                else:
                    invalid.append(f"themeAppearance.custom.palette.{field}")
            if palette:
                custom["palette"] = palette
        elif "palette" in raw_custom:
            invalid.append("themeAppearance.custom.palette")

        raw_type = raw_custom.get("typography")
        if isinstance(raw_type, dict):
            typography = {}
            allowed_type = FONT_FIELDS | WEIGHT_FIELDS | LINE_HEIGHT_FIELDS | SIZE_FIELDS
            unknown.update(set(raw_type) - allowed_type)
            for field in FONT_FIELDS:
                if field not in raw_type:
                    continue
                value = raw_type[field]
                if isinstance(value, str) and value in FONT_TOKENS:
                    typography[field] = value
                elif (
                    isinstance(value, dict)
                    and set(value) == {"loadedFont"}
                    and isinstance(value["loadedFont"], str)
                    and SAFE_FONT.fullmatch(value["loadedFont"])
                ):
                    typography[field] = {"loadedFont": value["loadedFont"]}
                else:
                    invalid.append(f"themeAppearance.custom.typography.{field}")
            for field in WEIGHT_FIELDS:
                if field not in raw_type:
                    continue
                value = raw_type[field]
                if type(value) is int and value in {400, 500, 600, 700}:
                    typography[field] = value
                else:
                    invalid.append(f"themeAppearance.custom.typography.{field}")
            for field in SIZE_FIELDS:
                if field not in raw_type:
                    continue
                value = raw_type[field]
                bounds = (16, 64) if field == "headingSize" else (12, 24)
                if type(value) is int and bounds[0] <= value <= bounds[1]:
                    typography[field] = value
                else:
                    invalid.append(f"themeAppearance.custom.typography.{field}")
            for field in LINE_HEIGHT_FIELDS:
                if field not in raw_type:
                    continue
                value = raw_type[field]
                if type(value) in {int, float} and 1 <= value <= 2 and math.isfinite(value):
                    typography[field] = math.floor(value * 100 + 0.5) / 100
                else:
                    invalid.append(f"themeAppearance.custom.typography.{field}")
            if typography:
                custom["typography"] = typography
        elif "typography" in raw_custom:
            invalid.append("themeAppearance.custom.typography")

        raw_geometry = raw_custom.get("geometry")
        if isinstance(raw_geometry, dict):
            geometry = {}
            unknown.update(set(raw_geometry) - GEOMETRY_FIELDS)
            bounds = {
                "maxWidth": (640, 1920), "gutter": (0, 64),
                "mobileGutter": (0, 64), "sectionPadding": (0, 128),
                "cardPadding": (8, 64), "gap": (8, 48), "radius": (0, 32),
                "buttonRadius": (0, 32), "buttonHeight": (32, 64),
                "railInset": (0, 20),
            }
            for field in GEOMETRY_FIELDS:
                if field not in raw_geometry:
                    continue
                value = raw_geometry[field]
                if field == "columns":
                    valid = type(value) is int and value in {1, 2, 3, 4}
                else:
                    low, high = bounds[field]
                    valid = type(value) is int and low <= value <= high
                if valid:
                    geometry[field] = value
                else:
                    invalid.append(f"themeAppearance.custom.geometry.{field}")
            if geometry:
                custom["geometry"] = geometry
        elif "geometry" in raw_custom:
            invalid.append("themeAppearance.custom.geometry")
        result["custom"] = custom
    elif "custom" in appearance:
        invalid.append("themeAppearance.custom")

    if unknown:
        result["unrecognized_saved_fields_present"] = True
    if invalid:
        result["invalid_saved_fields"] = sorted(invalid)
    return result


def summarize(structure: Dict[str, Any], localization: Dict[str, Any],
              quests: Optional[Dict[str, Dict[str, Any]]], *,
              quests_complete: bool = True) -> List[Dict[str, Any]]:
    common = localization.get("common") or {}
    loc_pages = localization.get("pages") or {}
    blocks_out: List[Dict[str, Any]] = []
    for page in structure.get("pages") or []:
        page_texts = (loc_pages.get(page.get("_id")) or {}).get("texts") or {}
        blocks = page.get("blocks") or []
        page_modules = [
            {
                "position": module_index,
                "module_id": _module_id(candidate),
                "is_quests": _is_quests_block(candidate),
            }
            for module_index, candidate in enumerate(blocks, 1)
        ]
        for index, block in enumerate(blocks, 1):
            if not _is_quests_block(block):
                continue
            values = block.get("values") or {}
            ibv = values.get("internalBlockValues") or {}
            localized = (values.get("resources") or {}).get("localizedValues") or {}

            def text(ref: Optional[str]) -> Optional[str]:
                entry = localized.get(ref) or {}
                text_id = (entry.get("texts") or {}).get("id") or ref
                found = page_texts.get(text_id) or common.get(text_id) or {}
                return _plain((found.get("translations") or {}).get("en-US"))

            overrides = ibv.get("overrides") or {}
            cards = []
            for position, quest_id in enumerate(ibv.get("questIds") or [], 1):
                override = overrides.get(quest_id) or {}
                quest = (quests or {}).get(quest_id)
                card = {
                    "position": position,
                    "quest_id": quest_id,
                    "quest_name": quest.get("name") if quest else None,
                    "card_title": text(override.get("titleRef")) if override.get("titleRef") else None,
                    "overridden": sorted(k[:-3] if k.endswith("Ref") else k for k in override),
                }
                if quests is not None and (quest is not None or quests_complete):
                    card["public"] = bool(quest and quest.get("is_public"))
                    card["found"] = quest is not None
                cards.append(card)
            layout = ibv.get("layout") or {}
            heading_ref = (ibv.get("translations") or {}).get("heading")
            blocks_out.append({
                "block_id": block.get("_id"),
                "page": page.get("name"),
                "position": index,
                "blocks_on_page": len(blocks),
                "page_modules": page_modules,
                "hidden": bool(block.get("hidden")),
                "max_quests": ibv.get("maxQuests"),
                "heading": text(heading_ref) if heading_ref else None,
                "show_heading": layout.get("showHeading", True),
                "appearance": _summary_appearance(values, ibv),
                "quests": cards,
            })
    return blocks_out


def site_summary(runner: Runner, fetcher: QuestFetcher, slug: str, env: List[str],
                 structure: Dict[str, Any]) -> Dict[str, Any]:
    localization = runner(["get-localization", "--slug", slug, "--json", *env])
    site = structure.get("data") or {}
    lookup = fetcher(str(site.get("merchantId")), str(site.get("projectId")))
    return {
        "ok": True,
        "site": slug,
        "merchant_id": str(site.get("merchantId")),
        "project_id": str(site.get("projectId")),
        # get-structure's own flag, the same one the gate refuses block writes on.
        "published": site.get("published") not in (None, False),
        "quest_names": (
            "unavailable" if lookup is None else "resolved" if lookup.complete else "partial"
        ),
        "blocks": summarize(
            site, localization.get("data") or {} if localization.get("ok") else {},
            lookup.quests if lookup is not None else None,
            quests_complete=lookup.complete if lookup is not None else False,
        ),
    }


def find_site(runner: Runner, fetcher: QuestFetcher, env: List[str]) -> Dict[str, Any]:
    """Pick the one site with a visible Quests block, reading every site's structure."""
    listing = runner(["list-websites", "--json", *env])
    if not listing.get("ok"):
        return {"ok": False, "error": "site_list_failed"}
    sites, structures = [], {}
    for entry in listing.get("data") or []:
        slug = entry.get("domain")
        if not slug:
            continue
        structure = runner(["get-structure", "--slug", slug, "--json", *env])
        visible = None
        if structure.get("ok"):
            blocks = summarize(structure.get("data") or {}, {}, None)
            visible = sum(1 for block in blocks if not block["hidden"])
            structures[slug] = structure
        sites.append({"site": slug, "visible_quests_blocks": visible})
    with_block = [s["site"] for s in sites if s["visible_quests_blocks"]]
    if len(with_block) != 1:
        return {"ok": True, "site": None, "sites": sites}
    result = site_summary(runner, fetcher, with_block[0], env, structures[with_block[0]])
    result["sites"] = sites
    return result


def main(argv: Optional[List[str]] = None, runner: Runner = run_cli,
         fetcher: QuestFetcher = fetch_quests) -> int:
    parser = argparse.ArgumentParser(prog="quests_block_summary.py")
    parser.add_argument("--slug", default=None)
    parser.add_argument("--environment", default=None)
    args = parser.parse_args(argv)
    env = ["--environment", args.environment] if args.environment else []

    if args.slug is None:
        result = find_site(runner, fetcher, env)
        print(json.dumps(result, ensure_ascii=False, indent=1))
        return 0 if result["ok"] else 1
    structure = runner(["get-structure", "--slug", args.slug, "--json", *env])
    if not structure.get("ok"):
        print(json.dumps({"ok": False, "error": "structure_read_failed"}))
        return 1
    result = site_summary(runner, fetcher, args.slug, env, structure)
    print(json.dumps(result, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
