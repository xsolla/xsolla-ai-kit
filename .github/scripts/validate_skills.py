#!/usr/bin/env python3
"""Validate the skills tree, the generated provider files, and the registries.

Run locally before opening a PR:

    python3 .github/scripts/validate_skills.py

Exit code 0 = clean, 1 = at least one error. Warnings never fail the build.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import skill_table  # noqa: E402  (sibling script; generates the AGENTS.md skill table)

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / "skills"
BASELINE = ROOT / ".github" / "skills-baseline.json"

# CONTRIBUTING-skills.md: soft target. Reported as a warning, never blocks a merge.
SOFT_LINE_LIMIT = 500

# Agents load every skill's description up front. Claude Code gives the whole
# skill list about 1% of the context window (~8,000 characters on a 200k model)
# and drops descriptions past that budget, so each skill gets a share, not the
# 1,536-character per-skill cap. 400 keeps the full list inside the budget with
# room for new skills. Put the key trigger phrase first.
DESCRIPTION_LIMIT = 400

# Internal LDAP-style owner ids currently in use, in whatever format that person's
# SKILL.md already uses (the repo has never enforced one — see CODEOWNERS note).
# Add a new person here in the same PR that adds their first `metadata.owner` line,
# so a typo in either place still fails validation instead of silently routing to no one.
VALID_OWNERS = {
    "mohammed_abujalala",
    "y.klochikhin",
    "y-klochikhin",
    "p.sanachev",
    "elnur_khalilov",
    "e.chernykh",
    # SB AI skills (integration/sb-ai)
    "a.pyanzin",
    "k.shah",
    "n.budhwani",
    "r.addoumie",
    "s.hossain",
    "s.sadruddin",
}

VALID_DOMAINS = {
    "catalog",
    "payments",
    "login",
    "webhooks",
    "store",
    "design",
    "orchestrator",
    "go-live",
}

errors: list[str] = []
warnings: list[str] = []


def error(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def parse_frontmatter(text: str) -> dict | None:
    """Minimal YAML frontmatter reader — avoids a PyYAML dependency in CI."""
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 3)
    if end == -1:
        return None
    block = text[4 : end + 1]

    data: dict = {}
    current_key: str | None = None
    for raw in block.split("\n"):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw.startswith(("  ", "\t")):
            # nested mapping (metadata:) or a folded-scalar continuation line
            if current_key == "description":
                data["description"] = (data.get("description", "") + " " + raw.strip()).strip()
            elif current_key and isinstance(data.get(current_key), dict):
                if ":" in raw:
                    k, _, v = raw.strip().partition(":")
                    data[current_key][k.strip()] = v.strip()
            continue
        if ":" not in raw:
            continue
        key, _, value = raw.partition(":")
        key, value = key.strip(), value.strip()
        current_key = key
        if value in {">-", ">", "|", "|-", ""}:
            data[key] = {} if value == "" else ""
        else:
            data[key] = value
    return data


def check_skill(skill_dir: Path) -> None:
    name = skill_dir.name
    skill_md = skill_dir / "SKILL.md"
    rel = skill_md.relative_to(ROOT)

    if not skill_md.is_file():
        error(f"{name}: missing SKILL.md")
        return

    text = skill_md.read_text(encoding="utf-8")
    fm = parse_frontmatter(text)

    if fm is None:
        error(f"{rel}: missing or malformed YAML frontmatter (must start with '---')")
        return

    if fm.get("name") != name:
        error(f"{rel}: frontmatter name '{fm.get('name')}' does not match directory '{name}'")

    description = fm.get("description")
    if not isinstance(description, str) or not description.strip():
        error(f"{rel}: frontmatter is missing a non-empty 'description'")
    elif len(description) > DESCRIPTION_LIMIT:
        error(
            f"{rel}: description is {len(description)} chars, over the "
            f"{DESCRIPTION_LIMIT}-char limit. Agents share one small budget for every "
            f"skill's description; put the key trigger phrase first and trim the rest "
            f"(detail belongs in the SKILL.md body)."
        )

    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name):
        error(f"{rel}: directory name '{name}' must be lowercase kebab-case")

    metadata = fm.get("metadata")
    if not isinstance(metadata, dict):
        error(f"{rel}: frontmatter is missing a 'metadata:' block")
    else:
        owner = metadata.get("owner")
        if not owner:
            error(f"{rel}: metadata is missing 'owner'")
        elif owner not in VALID_OWNERS:
            error(
                f"{rel}: metadata owner '{owner}' is not in the known-owners list "
                f"({', '.join(sorted(VALID_OWNERS))}) — typo, or a new person who "
                f"needs adding to VALID_OWNERS in this script"
            )
        domain = metadata.get("domain")
        if not domain:
            error(f"{rel}: metadata is missing 'domain'")
        elif domain not in VALID_DOMAINS:
            error(
                f"{rel}: metadata domain '{domain}' is not one of "
                f"{', '.join(sorted(VALID_DOMAINS))}"
            )

    line_count = len(text.splitlines())
    if line_count > SOFT_LINE_LIMIT:
        warn(f"{rel}: {line_count} lines, over the {SOFT_LINE_LIMIT}-line target — consider splitting into references/")


def check_links() -> None:
    """Every relative Markdown link must resolve on disk."""
    pattern = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
    for md in ROOT.rglob("*.md"):
        if any(part in {".git", "node_modules"} for part in md.parts):
            continue
        for target in pattern.findall(md.read_text(encoding="utf-8")):
            target = target.split("#")[0].split(" ")[0].strip()
            if not target or target.startswith(("http://", "https://", "mailto:", "<")):
                continue
            if not (md.parent / target).exists():
                error(f"{md.relative_to(ROOT)}: broken relative link '{target}'")


def check_json() -> None:
    for jf in ROOT.rglob("*.json"):
        if any(part in {".git", "node_modules"} for part in jf.parts):
            continue
        try:
            json.loads(jf.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            error(f"{jf.relative_to(ROOT)}: invalid JSON — {exc}")


def check_entry_phrases(skill_names: list[str]) -> None:
    """A quoted phrase in a description is a trigger: the request that should open
    that skill. If two skills quote the same phrase, agents can't tell which one to
    open, so each trigger phrase must belong to exactly one skill."""
    seen: dict[str, str] = {}
    for name, description in skill_table.skills():
        if name not in skill_names:
            continue
        for phrase in re.findall(r'"([^"]+)"', description):
            key = " ".join(phrase.lower().split())
            if key in seen and seen[key] != name:
                error(
                    f"skills/{name}/SKILL.md: trigger phrase \"{phrase}\" is also in "
                    f"skills/{seen[key]}/SKILL.md. Give each request to one skill; "
                    f"name the other skill instead of quoting its phrase"
                )
            seen.setdefault(key, name)


def check_skill_table() -> None:
    """AGENTS.md and copilot-instructions.md carry a skill table generated from the
    skills' frontmatter, so agents always see every skill with its real description."""
    for path in skill_table.stale_files():
        error(
            f"{path.relative_to(ROOT)}: skill table is out of date. "
            f"Run `python3 .github/scripts/skill_table.py` and commit the result"
        )


def check_generated_files(skill_names: list[str]) -> None:
    """.cursor/skills and CLAUDE.md are generated — fail on drift, don't silently fix."""
    if (ROOT / "AGENTS.md").read_text(encoding="utf-8") != (ROOT / "CLAUDE.md").read_text(encoding="utf-8"):
        error("CLAUDE.md is out of sync with AGENTS.md (it is generated by `cp AGENTS.md CLAUDE.md`)")

    mirror_root = ROOT / ".cursor" / "skills"
    mirrored = {p.name for p in mirror_root.iterdir() if p.is_dir()} if mirror_root.is_dir() else set()
    if mirrored != set(skill_names):
        for missing in sorted(set(skill_names) - mirrored):
            error(f".cursor/skills/{missing} is missing — run the provider sync")
        for extra in sorted(mirrored - set(skill_names)):
            error(f".cursor/skills/{extra} has no matching skills/{extra} — stale generated file")

    for name in skill_names:
        for src in (SKILLS / name).rglob("*"):
            if not src.is_file():
                continue
            mirror = mirror_root / name / src.relative_to(SKILLS / name)
            if not mirror.is_file():
                error(f".cursor/skills/{name}/{src.relative_to(SKILLS / name)} is missing — run the provider sync")
            elif mirror.read_bytes() != src.read_bytes():
                error(f".cursor/skills/{name}/{src.relative_to(SKILLS / name)} differs from its source — run the provider sync")


def check_secrets() -> None:
    """Catch credentials pasted into docs before they reach a public branch."""
    patterns = [
        (re.compile(r"\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\."), "JWT"),
        (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}"), "GitHub token"),
        (re.compile(r"\bsk-[A-Za-z0-9]{32,}"), "API secret key"),
        (re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"), "private key"),
    ]
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.split()
    for rel in tracked:
        path = ROOT / rel
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for pattern, label in patterns:
            if pattern.search(content):
                error(f"{rel}: possible committed {label} — remove it and rotate the credential")


def main() -> int:
    if not SKILLS.is_dir():
        print("skills/ directory not found", file=sys.stderr)
        return 1

    skill_names = sorted(p.name for p in SKILLS.iterdir() if p.is_dir())
    if not skill_names:
        error("skills/ contains no skill directories")

    for name in skill_names:
        check_skill(SKILLS / name)

    check_links()
    check_json()
    check_entry_phrases(skill_names)
    check_skill_table()
    check_generated_files(skill_names)
    check_secrets()

    # Pre-existing violations live in the baseline so this check can be enforcing
    # from day one without blocking unrelated work. Never add to the baseline to
    # get a PR green — fix the finding instead. Removing entries is always welcome.
    if "--update-baseline" in sys.argv:
        BASELINE.write_text(json.dumps({"known_violations": sorted(errors)}, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {len(errors)} known violation(s) to {BASELINE.relative_to(ROOT)}")
        return 0

    baseline: list[str] = []
    if BASELINE.is_file():
        baseline = json.loads(BASELINE.read_text(encoding="utf-8")).get("known_violations", [])

    new_errors = [e for e in errors if e not in baseline]
    grandfathered = [e for e in errors if e in baseline]
    fixed = [b for b in baseline if b not in errors]

    for w in warnings:
        print(f"::warning::{w}")
    for g in grandfathered:
        print(f"::warning::[known debt] {g}")
    for e in new_errors:
        print(f"::error::{e}")

    if fixed:
        print(f"\n{len(fixed)} baselined violation(s) are now fixed — please drop them from "
              f"{BASELINE.relative_to(ROOT)} (`python3 .github/scripts/validate_skills.py --update-baseline`):")
        for f in fixed:
            print(f"  - {f}")

    print(
        f"\nChecked {len(skill_names)} skills: {len(new_errors)} new error(s), "
        f"{len(grandfathered)} known debt, {len(warnings)} warning(s)."
    )
    return 1 if new_errors else 0


if __name__ == "__main__":
    sys.exit(main())
