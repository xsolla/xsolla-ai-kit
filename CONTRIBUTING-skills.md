# Contributing Skills

This is the Xsolla guide for writing agent skills for `xsolla/xsolla-ai-kit`.

> The full guide is being finalized in `xsolla/xsolla-cli` PR #233. It will be copied here on merge.
> In the meantime, follow the quick rules below.

---

## Quick rules

1. **One skill per directory** — `skills/<skill-name>/SKILL.md`
2. **Under ~500 lines is a good sign** — a soft warning, not a hard rule; some domains
   genuinely need the space. If it's ballooning past that, consider whether part of it
   belongs in `skills/<skill-name>/references/*.md`
3. **YAML frontmatter required** — see format below
4. **Pushy description** — cover every trigger scenario; agents use this to decide when
   to invoke. Keep it under **1,536 characters**: Claude Code truncates the skill listing
   at that point, so trailing trigger keywords are silently dropped. Key use case first.
5. **No raw `curl` commands** — describe intent + Xsolla API endpoint, not raw HTTP
6. **PR must include agent test** — exact prompt you used + one-line result
7. **Update both registries** — add a row to `skills/README.md` and an entry plus a
   trigger line to `AGENTS.md`, or agents can't discover the skill
8. **Commit the generated files** — `.cursor/skills/**` and `CLAUDE.md` are derived from
   `skills/**` and `AGENTS.md`; CI fails on drift
9. **Cross-references must be real** — if you write "→ `shop-setup`" for something, check
   that `shop-setup` actually covers it. A pointer to guidance that doesn't exist
   dead-ends the agent at the exact moment it needs help.

Check all of the above locally before opening a PR:

```bash
python3 .github/scripts/validate_skills.py
```

## SKILL.md frontmatter

```yaml
---
name: <skill-name>
description: >-
  One pushy paragraph covering all trigger scenarios and keywords.
  Use when [trigger]. Covers [domains]. Invoke for [actions].
metadata:
  owner: <github-username>
  domain: catalog|payments|login|webhooks|store|design|orchestrator
---
```

## Structure

There's no mandated section layout — a skill is free text, and what reads best depends
on the material: a decision tree, a reference table, a linear procedure. The part CI
does check is `description` + `metadata`, since that's what an agent actually reads to
decide whether to invoke the skill at all; how you present the content past that point
is your call. A few things worth covering somewhere in the file regardless of shape:
when to use it, prerequisites (env vars, existing Xsolla resources), the steps
themselves, and common pitfalls.

## Contribution tiers

| Who | What they own |
|-----|--------------|
| Feature/surface owner (domain SME) | Authors the SKILL.md for their surface |
| Tech lead | Reviews for technical accuracy |
| @j.manashti | Final review against this guide; merges to main |
