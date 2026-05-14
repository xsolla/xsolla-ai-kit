# Contributing Skills

This is the Xsolla guide for writing agent skills for `xsolla/xsolla-ai-kit`.

> The full guide is being finalized in `xsolla/xsolla-cli` PR #233. It will be copied here on merge.
> In the meantime, follow the quick rules below.

---

## Quick rules

1. **One skill per directory** — `skills/<skill-name>/SKILL.md`
2. **Under 200 lines** — split overflow into `skills/<skill-name>/references/*.md`
3. **YAML frontmatter required** — see format below
4. **Pushy description** — cover every trigger scenario; agents use this to decide when to invoke
5. **No raw `curl` commands** — describe intent + Xsolla API endpoint, not raw HTTP
6. **PR must include agent test** — exact prompt you used + one-line result

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

## Required sections

1. `## When to use` — trigger keywords + entry conditions
2. `## Prerequisites` — env vars, existing Xsolla resources required
3. `## Steps` — numbered steps with API calls or CLI commands
4. `## Common pitfalls` — top 3–5 failure modes + fixes

## Contribution tiers

| Who | What they own |
|-----|--------------|
| Feature/surface owner (domain SME) | Authors the SKILL.md for their surface |
| Tech lead | Reviews for technical accuracy |
| @j.manashti | Final review against this guide; merges to main |
