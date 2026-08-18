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

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / "skills"
BASELINE = ROOT / ".github" / "skills-baseline.json"

# CONTRIBUTING-skills.md: soft target. Existing skills already exceed it, so this
# is reported as a warning and never blocks a merge.
SOFT_LINE_LIMIT = 200

# Claude Code truncates the combined description + when_to_use text at 1,536
# characters in the skill listing. Past that, trigger keywords are silently lost,
# so the skill stops matching the requests it was written for.
DESCRIPTION_LIMIT = 1536

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
            f"{DESCRIPTION_LIMIT}-char skill-listing cap — trailing trigger keywords "
            f"will be truncated. Put the key use case first and trim."
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

    # CONTRIBUTING-skills.md required sections
    for section in ("## When to use", "## Prerequisites", "## Steps", "## Common pitfalls"):
        if section not in text:
            error(f"{rel}: missing required section '{section}'")

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


def check_registries(skill_names: list[str]) -> None:
    """Every skill must appear in both inventories, or agents cannot discover it."""
    readme = (SKILLS / "README.md").read_text(encoding="utf-8")
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    for name in skill_names:
        if f"`{name}`" not in readme:
            error(f"skills/README.md: no row for skill '{name}'")
        if f"`{name}`" not in agents:
            error(f"AGENTS.md: no entry for skill '{name}'")


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
    check_registries(skill_names)
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
