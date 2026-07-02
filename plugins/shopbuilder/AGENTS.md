# xsolla-shopbuilder — Agent Context

This file is read automatically by most AI coding agents (Cursor, Codex CLI, GitHub Copilot, Windsurf, Amp, Devin, Jules, Aider, Roo Code, Augment). Claude Code users: `CLAUDE.md` is a symlink to this file.

---

## What this plugin is

`xsolla-shopbuilder` is the Xsolla **Shop Builder** toolkit — a set of `SKILL.md` files (agentskills.io format) that teach AI coding agents how to build a hosted, no-code game storefront on Xsolla Shop Builder, end-to-end.

Unlike the `xsolla-headless-shop` plugin (which assembles a custom storefront from Login + Store API + Headless Checkout SDK), Shop Builder is a **hosted, no-code storefront** edited through the **`xsolla shopbuilder` CLI**. This plugin is intentionally self-contained and separate from the headless kit.

The storefront is a four-level hierarchy — **site → page → blocks → block customization** — built and reviewed top-down, orchestrated by `shopbuilder-storefront`.

---

## Skill inventory

| Skill                    | Level          | What it does                                                                                      |
|--------------------------|----------------|---------------------------------------------------------------------------------------------------|
| `shopbuilder-storefront` | Orchestrator   | Entry point — sets scope, order, and rules; sequences the four level skills below                 |
| `shopbuilder-site`       | 1 — Site       | The container: identity, currency model, locales, brand seed theme, domain                        |
| `shopbuilder-page`       | 2 — Page       | One scroll as a funnel: mood, the page theme that overrides the site theme, backdrop, SEO         |
| `shopbuilder-blocks`     | 3 — Blocks     | Merchandising: which blocks, in what order, incl. hosted modules (offer chain, daily reward, offerwall) |
| `shopbuilder-customize`  | 4 — Customize  | Conversion: copy, imagery, store sections, per-block theme via the `update-block` patch model     |

**Prerequisites (own skills, out of scope here):** merchant account and keys, project creation, catalog, login, payments, webhooks. The store block renders the project catalog, so build the catalog first.

---

## Environment variables

```bash
XSOLLA_MERCHANT_ID=<your merchant ID>
XSOLLA_PROJECT_ID=<your project ID>
XSOLLA_PROJECT_API_KEY=<your API key>
XSOLLA_SHOPBUILDER_SESSION=<pa-v4-token cookie value>   # required by the `xsolla shopbuilder` CLI; expires — re-copy on 403
```

---

## Adding a skill

See [../../CONTRIBUTING-skills.md](../../CONTRIBUTING-skills.md) for the full guide.

Quick rules:
- One `SKILL.md` per `skills/<skill-name>/` directory
- Under 200 lines; split into `references/` if it grows past that
- Description must contain trigger keywords — make it pushy
