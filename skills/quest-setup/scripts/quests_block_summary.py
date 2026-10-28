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
block_operations brief only, never for a reply. Exit codes: 0 read ok, 1 a site read failed.
Python 3.9+, standard library only.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

sys.dont_write_bytecode = True  # keep the installed skill folder clean
sys.path.insert(0, str(Path(__file__).resolve().parent))

import qp_request  # noqa: E402

BLOCK_ID = "_quest-platform_quests-block"
TAG = re.compile(r"<[^>]+>")
QUEST_PAGES = 5
QUEST_PAGE_SIZE = 50

Runner = Callable[[List[str]], Dict[str, Any]]
QuestFetcher = Callable[[str, str], Optional[Dict[str, Dict[str, Any]]]]


def run_cli(args: List[str]) -> Dict[str, Any]:
    proc = subprocess.run(["xsolla", "shopbuilder", *args], capture_output=True, text=True)
    if proc.returncode != 0:
        return {"ok": False}
    try:
        return json.loads(proc.stdout)
    except ValueError:
        return {"ok": False}


def fetch_quests(merchant: str, project: str) -> Optional[Dict[str, Dict[str, Any]]]:
    """Quest id -> quest, or None when the credential is missing, for another project, or fails."""
    try:
        creds = qp_request.resolve_credentials(qp_request.os.environ, Path.cwd())
    except qp_request.Refusal:
        return None
    if (creds.merchant_id, creds.project_id) != (str(merchant), str(project)):
        return None
    quests: Dict[str, Dict[str, Any]] = {}
    path = f"/api/v2/merchants/{merchant}/projects/{project}/quests"
    for page in range(1, QUEST_PAGES + 1):
        url = qp_request.build_url(path, False, creds) + f"?page={page}&limit={QUEST_PAGE_SIZE}"
        result = qp_request.send("GET", url, creds, None)
        body = result.get("body")
        if not result.get("ok") or not isinstance(body, dict):
            return None
        for quest in body.get("data") or []:
            quests[str(quest.get("id"))] = quest
        if page * QUEST_PAGE_SIZE >= int(body.get("total") or 0):
            break
    return quests


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


def summarize(structure: Dict[str, Any], localization: Dict[str, Any],
              quests: Optional[Dict[str, Dict[str, Any]]]) -> List[Dict[str, Any]]:
    common = localization.get("common") or {}
    loc_pages = localization.get("pages") or {}
    blocks_out: List[Dict[str, Any]] = []
    for page in structure.get("pages") or []:
        page_texts = (loc_pages.get(page.get("_id")) or {}).get("texts") or {}
        blocks = page.get("blocks") or []
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
                if quests is not None:
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
                "hidden": bool(block.get("hidden")),
                "max_quests": ibv.get("maxQuests"),
                "heading": text(heading_ref) if heading_ref else None,
                "show_heading": layout.get("showHeading", True),
                "quests": cards,
            })
    return blocks_out


def site_summary(runner: Runner, fetcher: QuestFetcher, slug: str, env: List[str],
                 structure: Dict[str, Any]) -> Dict[str, Any]:
    localization = runner(["get-localization", "--slug", slug, "--json", *env])
    site = structure.get("data") or {}
    quests = fetcher(str(site.get("merchantId")), str(site.get("projectId")))
    return {
        "ok": True,
        "site": slug,
        "merchant_id": str(site.get("merchantId")),
        "project_id": str(site.get("projectId")),
        "quest_names": "resolved" if quests is not None else "unavailable",
        "blocks": summarize(site, localization.get("data") or {} if localization.get("ok") else {}, quests),
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
