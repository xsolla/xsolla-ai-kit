#!/usr/bin/env python3
"""Make `fixtures/redesigned-site.json` from exports of a real, unpublished test site.

    xsolla shopbuilder get-structure --slug <slug> --json > structure.json
    xsolla shopbuilder get-localization --slug <slug> --json > localization.json
    python3 tests/mask_site_export.py structure.json localization.json / /store \
        > tests/fixtures/redesigned-site.json

The paths name the pages to keep. Block order, modules, `values` and every reference
inside them stay as exported. IDs, links, text and account data are replaced, the same
way everywhere, so a reference still finds its target. Run it again when Shop Builder
ships a block version with another shape.
"""

from __future__ import annotations

import json
import re
import sys

sys.dont_write_bytecode = True

HEX_ID = re.compile(r"[0-9a-f]{24,}")
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
URL = re.compile(r"https?://[^\s\"'<>)]+")
TAG = re.compile(r"\s*<(\w+)")
I18N_KEY = re.compile(r"[A-Za-z0-9_.\-]*")
SITE_KEYS = ("_id", "type", "published", "languages", "layouts")
PAGE_KEYS = ("_id", "name", "path", "type", "seo")
DROPPED_BLOCK_KEYS = ("metadata", "icon")
SAFE_HOST = "https://example.invalid/"


class Masker:
    def __init__(self) -> None:
        self.ids: dict[str, str] = {}
        self.uuids: dict[str, str] = {}
        self.urls: dict[str, str] = {}

    def _id(self, match: re.Match) -> str:
        found = match.group(0)
        if found not in self.ids:
            self.ids[found] = f"{len(self.ids) + 1:0{len(found)}x}"
        return self.ids[found]

    def _uuid(self, match: re.Match) -> str:
        found = match.group(0)
        if found not in self.uuids:
            self.uuids[found] = f"00000000-0000-4000-8000-{len(self.uuids) + 1:012x}"
        return self.uuids[found]

    def _url(self, match: re.Match) -> str:
        found = match.group(0)
        if found not in self.urls:
            self.urls[found] = f"{SAFE_HOST}file-{len(self.urls) + 1}"
        return self.urls[found]

    def text(self, value: str) -> str:
        # Links first: an ID inside a link goes with the link.
        return HEX_ID.sub(self._id, UUID.sub(self._uuid, URL.sub(self._url, value)))

    def value(self, value: object) -> object:
        if isinstance(value, dict):
            return {self.text(key): self.value(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self.value(item) for item in value]
        return self.text(value) if isinstance(value, str) else value


def page_path(page: dict) -> str:
    path = page["path"]
    return path["pathSegment"] if isinstance(path, dict) else path


def without(value: object, key: str) -> object:
    return {k: v for k, v in value.items() if k != key} if isinstance(value, dict) else value


def mask_block(masker: Masker, block: dict) -> dict:
    kept = {key: item for key, item in block.items() if key not in DROPPED_BLOCK_KEYS}
    masked = masker.value(kept)
    values = masked.get("values")
    if isinstance(values, dict) and isinstance(values.get("host"), str):
        values["host"] = f"{SAFE_HOST}{values.get('blockId')}/{values.get('version')}/"
    return masked


def mask_texts(masker: Masker, texts: dict) -> dict:
    """Keep every text ID and its note; replace the text itself, in one locale."""
    masked = {}
    for number, (text_id, row) in enumerate(texts.items(), start=1):
        text = f"Text {number}"
        english = (row.get("translations") or {}).get("en-US") or ""
        tag = TAG.match(english)
        if tag:
            text = f"<{tag.group(1)}>{text}</{tag.group(1)}>"
        note = row.get("description")
        masked[masker.text(text_id)] = {
            "description": note if isinstance(note, str) and I18N_KEY.fullmatch(note) else "",
            "translations": {"en-US": text},
        }
    return masked


def mask(structure: dict, localization: dict, paths: list[str]) -> dict:
    masker = Masker()
    pages = [page for page in structure["pages"] if page_path(page) in paths]
    missing = sorted(set(paths) - {page_path(page) for page in pages})
    if missing:
        raise ValueError(f"no such page in the structure: {', '.join(missing)}")
    site = {key: masker.value(structure[key]) for key in SITE_KEYS if key in structure}
    site["domain"] = "redesigned-site"
    site["merchantId"] = "merchant-id"
    site["projectId"] = "project-id"
    site["features"] = {"redesign": (structure.get("features") or {}).get("redesign")}
    site["theme"] = masker.value(without(structure.get("theme"), "calculatedTheme"))
    site["pages"] = []
    texts = {}
    for page in pages:
        masked = {key: masker.value(page[key]) for key in PAGE_KEYS if key in page}
        masked["theme"] = masker.value(without(page.get("theme"), "calculatedTheme"))
        masked["blocks"] = [mask_block(masker, block) for block in page["blocks"]]
        site["pages"].append(masked)
        scope = (localization.get("pages") or {}).get(page["_id"]) or {}
        texts[masked["_id"]] = {"texts": mask_texts(masker, scope.get("texts", scope))}
    site["blocks"] = [block["_id"] for page in site["pages"] for block in page["blocks"]]
    site["blocks"] += site.get("layouts", [])
    fixture = {
        "about": (
            "Masked export of an unpublished test site with features.redesign on. Made "
            "by tests/mask_site_export.py; don't edit by hand."
        ),
        "structure": site,
        "localization": {
            "common": mask_texts(masker, localization.get("common") or {}),
            "pages": texts,
        },
    }
    leaks = find_leaks(fixture, structure)
    if leaks:
        raise ValueError("the masked fixture still holds: " + "; ".join(leaks[:5]))
    return fixture


def find_leaks(fixture: dict, structure: dict) -> list[str]:
    """Anything from the real site that must not reach the repository."""
    dumped = json.dumps(fixture)
    secrets = [str(structure.get(key)) for key in ("merchantId", "projectId", "domain", "_id")]
    leaks = [f"the site's {secret!r}" for secret in secrets if secret and secret in dumped]
    leaks += [f"link {url}" for url in URL.findall(dumped) if not url.startswith(SAFE_HOST)]
    if "@" in dumped:
        leaks.append("an @, as in an email address")
    return leaks


def data(value: dict) -> dict:
    return value["data"] if value.get("ok") is True and "data" in value else value


def main() -> int:
    if len(sys.argv) < 4:
        print(__doc__, file=sys.stderr)
        return 2
    with open(sys.argv[1], encoding="utf-8") as handle:
        structure = data(json.load(handle))
    with open(sys.argv[2], encoding="utf-8") as handle:
        localization = data(json.load(handle))
    try:
        fixture = mask(structure, localization, sys.argv[3:])
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    # One line: the file is large and nobody edits it. `python3 -m json.tool` shows it.
    json.dump(fixture, sys.stdout, ensure_ascii=False, separators=(",", ":"))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
