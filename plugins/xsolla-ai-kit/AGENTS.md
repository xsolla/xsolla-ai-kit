# xsolla-ai-kit — Agent Context

This file is read automatically by most AI coding agents (Cursor, Codex CLI, GitHub Copilot, Windsurf, Amp, Devin, Jules, Aider, Roo Code, Augment). Claude Code users: `CLAUDE.md` is a symlink to this file.

---

## What this plugin is

`xsolla-ai-kit` is the Xsolla shop toolkit — a collection of `SKILL.md` files (agentskills.io format) that teach AI coding agents how to build an Xsolla game shop end-to-end. There is **one entry point** (`shop-setup`) and **two build paths**:

- **Headless** — the developer writes and hosts a custom storefront in their own site (Store API + Login + Headless Checkout SDK). Skills call **Xsolla REST APIs directly**.
- **Shop Builder** — a hosted, no-code storefront on Xsolla Shop Builder, edited via the `xsolla shopbuilder` CLI.

Both paths share the same foundation (merchant setup, catalog, Login config, webhooks) and diverge only at the storefront layer. `shop-setup` runs the foundation, then asks or infers which path to take.

---

## Skill inventory

**Entry**

| Skill | What it does |
|---|---|
| `shop-setup` | **Single entry point.** Runs the shared foundation, then routes to the headless or Shop Builder path. |

**Shared foundation (both paths)**

| Skill | What it does |
|---|---|
| `merchant-setup` | Creates/configures an Xsolla account + API keys. |
| `catalog-design` | Configures the catalog and the client flow: client catalog, purchase, order confirmation. |
| `login-setup` | Shared, storefront-agnostic Login/NewID setup: Login project, storage, enabled methods, identity model. |
| `webhooks-impl` | Fulfillment backend — webhook handler for order/payment events. |

**Headless branch**

| Skill | What it does |
|---|---|
| `headless-storefront` | Path orchestrator — sequences the headless frontend build (catalog read, cart, login, payment). |
| `headless-login` | Headless Login code: OAuth client, Widget/API/SDK, JWT validation, guest→Bearer cart switch. |
| `login-styling` | Theme/brand the Login widget (API-based CSS deployment); pairs with `headless-login`. |
| `headless-checkout-integration` | Payments via the embedded Headless Checkout SDK — cards, Apple Pay, Google Pay, saved methods (Pay Station fallback). |

**Shop Builder branch**

| Skill | What it does |
|---|---|
| `shopbuilder-storefront` | Path orchestrator — sequences the site→page→blocks→customize hierarchy. |
| `shopbuilder-site` | Level 1 — the landing container: identity, currency model, locales, brand seed theme, domain. |
| `shopbuilder-page` | Level 2 — the page: theme that ships, backdrop, SEO, funnel flow. |
| `shopbuilder-blocks` | Level 3 — blocks: taxonomy, order as sales funnel, hosted modules. |
| `shopbuilder-customize` | Level 4 — block customization: copy, imagery, store sections, per-block theme. |
| `shopbuilder-custom-block` | Advanced escape hatch — author/deploy a custom React block when native blocks can't. |

---

## How to invoke a skill

Skills are loaded automatically when you open this repo in your agent. To run a specific skill, ask your agent naturally:

```
Build me a full Xsolla game shop
→ triggers: shop-setup (which then picks headless vs Shop Builder)

Build a hosted no-code storefront on Shop Builder
→ triggers: shop-setup → shopbuilder-storefront

Embed a custom Xsolla store in my React app
→ triggers: shop-setup → headless-storefront

Configure my Xsolla catalog with items and pricing
→ triggers: catalog-design
```

---

## Environment variables

```bash
XSOLLA_MERCHANT_ID=<your merchant ID>
XSOLLA_PROJECT_ID=<your project ID>
XSOLLA_PROJECT_API_KEY=<your API key>
```
Set up by the `merchant-setup` skill. Login adds `XSOLLA_LOGIN_PROJECT_ID` (shared) and, for the headless path, `XSOLLA_LOGIN_OAUTH_CLIENT_ID` / `_CLIENT_SECRET`. The Shop Builder path also uses `XSOLLA_SHOPBUILDER_SESSION` (the `pa-v4-token` cookie).

---

## Key directories

| Path | Contents |
|------|----------|
| `skills/` | SKILL.md files. One subdirectory per workflow. |
| `skills/<name>/references/` | Long-form reference docs that keep SKILL.md focused. |
| `../../docs/` | (repo root) Architecture, distribution, and skill-gap guides. |
| `../../.github/workflows/` | (repo root) sync-providers.yml — auto-generates Cursor .mdc files from all plugins' SKILL.md |
| `../../.cursor/rules/` | (repo root) Auto-generated Cursor rules, aggregated across plugins (do not edit manually) |

---

## Adding a skill

See [../../CONTRIBUTING-skills.md](../../CONTRIBUTING-skills.md) for the full guide.

Quick rules:
- One `SKILL.md` per `skills/<skill-name>/` directory
- Keep SKILL.md focused; move long-form detail into `references/`
- Description must contain trigger keywords — make it pushy
- No `curl` commands — skills describe intent, not raw HTTP
- PR must include agent test output (exact prompt + one-line result)
