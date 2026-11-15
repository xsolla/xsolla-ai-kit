#!/usr/bin/env python3
"""Copy the published Quest Platform AI skill page into the quest-setup skill.

Run by hand from the repository root after the Quest Platform docs change (see AGENTS.md,
"Quest Platform docs copy"), then commit both files and their .cursor mirror in one pull request.

The page holds two fenced blocks: the assistant instructions and the whole documentation.
Each becomes one generated file under skills/quest-setup/references/. Nothing is written
unless the page looks complete, so a broken or truncated page never replaces a good copy.

Usage:
    python3 .github/scripts/sync_quest_platform_docs.py [--source FILE] [--check]

--source reads a saved page instead of fetching it. --check writes nothing and exits 1 when
the committed files differ from the page. Python 3.9+, standard library only.
"""
from __future__ import annotations

import argparse
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import List, Tuple

SITE = "https://developers.xsolla.com"
PAGE_URL = SITE + "/api/quests/ai-skill.md"
REFERENCES = Path("skills/quest-setup/references")
SKILL_FILE = REFERENCES / "quest-platform.md"
DOCS_FILE = REFERENCES / "quest-platform-docs.md"
MIRROR = Path(".cursor") / REFERENCES

HEADER = (
    "<!-- Generated from {url} by .github/scripts/sync_quest_platform_docs.py."
    " Do not edit: run that script to update it. -->\n\n"
)
SKILL_TITLE = "# Quest Platform skill for publishers"
MIN_SKILL_BYTES = 8_000
MIN_DOCS_BYTES = 60_000
MAX_PAGE_BYTES = 2_000_000
# The docs site can answer 202 while it builds the page, or a transient 429/5xx.
RETRY_STATUSES = {202, 429, 500, 502, 503, 504}
ATTEMPTS = 5
USER_AGENT = "xsolla-ai-kit-docs-sync (+https://github.com/xsolla/xsolla-ai-kit)"
FENCE = re.compile(r"^(`{4,})markdown\s*$")


class PageError(Exception):
    pass


def fetch_once(url: str) -> tuple[int, bytes]:
    request = urllib.request.Request(
        url, headers={"Accept": "text/markdown, text/plain", "User-Agent": USER_AGENT}
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310 - fixed https URL
            if response.geturl() != url:
                raise PageError("the page redirected")
            return response.status, response.read(MAX_PAGE_BYTES + 1)
    except urllib.error.HTTPError as exc:
        return exc.code, b""


def fetch(url: str, sleep=time.sleep) -> str:
    for attempt in range(1, ATTEMPTS + 1):
        status, data = fetch_once(url)
        if status == 200:
            if len(data) > MAX_PAGE_BYTES:
                raise PageError("the page is larger than expected")
            return data.decode("utf-8")
        if status not in RETRY_STATUSES or attempt == ATTEMPTS:
            raise PageError(f"the page answered {status}")
        sleep(10 * attempt)
    raise PageError("unreachable")


def fenced_blocks(page: str) -> List[str]:
    """The contents of every ````markdown block, in order."""
    blocks: List[str] = []
    lines = page.split("\n")
    i = 0
    while i < len(lines):
        match = FENCE.match(lines[i])
        if not match:
            i += 1
            continue
        fence = match.group(1)
        end = next((j for j in range(i + 1, len(lines)) if lines[j] == fence), None)
        if end is None:
            raise PageError("a code block is not closed")
        blocks.append("\n".join(lines[i + 1 : end]))
        i = end + 1
    return blocks


def unindent_headings(text: str) -> str:
    """The public site puts one space before lines starting with '#'; take it off."""
    return re.sub(r"^ #", "#", text, flags=re.MULTILINE)


def absolute_links(text: str) -> str:
    """Links on the page are relative to the docs site; a copy elsewhere needs the full address."""
    return re.sub(r"\]\((/api/quests[^)\s]*)\)", lambda m: f"]({SITE}{m.group(1)})", text)


def split_page(page: str) -> Tuple[str, str]:
    blocks = fenced_blocks(page)
    if len(blocks) != 2:
        raise PageError(f"expected 2 blocks on the page, found {len(blocks)}")
    skill, docs = (absolute_links(unindent_headings(block)).strip("\n") + "\n" for block in blocks)
    if not skill.startswith(SKILL_TITLE):
        raise PageError("the first block is not the publisher skill")
    if len(skill.encode()) < MIN_SKILL_BYTES or len(docs.encode()) < MIN_DOCS_BYTES:
        raise PageError("a block is far smaller than expected")
    return skill, docs


def render(page: str, url: str = PAGE_URL) -> Tuple[str, str]:
    skill, docs = split_page(page)
    header = HEADER.format(url=url)
    return header + skill, header + docs


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--source", help="read the page from this file instead of fetching it")
    parser.add_argument("--check", action="store_true", help="write nothing; exit 1 on a difference")
    args = parser.parse_args(argv)
    try:
        page = Path(args.source).read_text(encoding="utf-8") if args.source else fetch(PAGE_URL)
        skill, docs = render(page)
    except (PageError, OSError) as exc:
        print(f"sync_quest_platform_docs: nothing written: {exc}", file=sys.stderr)
        return 2
    changed = [
        path
        for path, text in ((SKILL_FILE, skill), (DOCS_FILE, docs))
        if not path.exists() or path.read_text(encoding="utf-8") != text
    ]
    if args.check:
        for path in changed:
            print(f"out of date: {path}")
        return 1 if changed else 0
    MIRROR.mkdir(parents=True, exist_ok=True)
    for path, text in ((SKILL_FILE, skill), (DOCS_FILE, docs)):
        path.write_text(text, encoding="utf-8")
        (MIRROR / path.name).write_text(text, encoding="utf-8")
    print("updated: " + ", ".join(str(p) for p in changed) if changed else "already up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
