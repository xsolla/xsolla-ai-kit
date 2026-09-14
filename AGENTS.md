# xsolla-ai-kit — Agent Context

This file is read automatically by most AI coding agents (Cursor, Codex CLI, GitHub Copilot, Windsurf, Amp, Devin, Jules, Aider, Roo Code, Augment). Claude Code users: `CLAUDE.md` is a copy of this file.

---

## What this repo is

`xsolla/xsolla-ai-kit` is the Xsolla agent skills toolkit — a collection of `SKILL.md` files (agentskills.io format) that teach AI coding agents how to execute Xsolla-specific workflows end-to-end, without requiring the Xsolla CLI as a dependency.

Skills call **Xsolla REST APIs directly**. The CLI (`xsolla/xsolla-cli`) is an optional shortcut once it ships to production.

---

## Skill inventory

| Skill                           | What it does                                                                             |
|---------------------------------|------------------------------------------------------------------------------------------|
| `shop-plan`                     | **Decides the build path** — headless vs Shop Builder, before any account or build work  |
| `shop-setup`                    | **Orchestrator** — coordinates the full zero-to-shop flow, chaining all domain skills    |
| `merchant-setup`                | Creates and configures an Xsolla account + get API key                                   |
| `catalog-design`                | Configures the catalog and the client flow: client catalog, purchase, order confirmation |
| `login-setup`                   | Integrates Xsolla Login / NewID authentication                                           |
| `login-styling`                 | Applies a custom visual style / theme / brand to the Login UI (pairs with `login-setup`) |
| `headless-checkout-integration` | Payments via Headless Checkout                                                           |
| `webhooks-impl`                 | Generates webhook handler code for order/payment events                                  |
| `production`                    | Sandbox → live: contract, flip flags, deploy, developer live-payment checklist           |

---

## How to invoke a skill

Skills are loaded automatically when you open this repo in your agent. To run a specific skill, ask your agent naturally:

```
Should I use Shop Builder or build a headless shop?
→ triggers: shop-plan (weighs five criteria, shows the trade-offs, records the choice)

Set up a full Xsolla game shop for my project
→ triggers: shop-setup — which delegates to shop-plan first if no path is recorded

Configure my Xsolla catalog with items and pricing
→ triggers: catalog-design

Integrate payments into my game
→ triggers: headless-checkout-integration

Go live / leave sandbox
→ triggers: production
```

---

## Environment variables

```bash
XSOLLA_MERCHANT_ID=<your merchant ID>
XSOLLA_PROJECT_ID=<your project ID>
XSOLLA_PROJECT_API_KEY=<your API key>
```
Setup by `merchant-setup` skill.

```bash
XSOLLA_BUILD_PATH=headless|shopbuilder
```
Recorded by `shop-plan` once the developer confirms the build path, and read by `shop-setup`
before it builds anything. One path per shop — `shop-plan` is the only skill that writes it.

If you are adding a skill that behaves differently per path, implement against
[the build-path contract](skills/shop-plan/references/build-path-contract.md) rather than
copying a check out of another skill. It covers the allowed values, the three states a reader
must handle (absent, decided, invalid), and the rule that a skill writing to `.env` must scope
its deletes to its own keys.

---

## Key directories

| Path | Contents |
|------|----------|
| `skills/` | SKILL.md files. One subdirectory per workflow. |
| `skills/<name>/references/` | Long-form reference docs. Keeps SKILL.md under 200 lines. |
| `docs/` | Architecture, distribution, and skill-gap guides. |
| `.cursor/skills/` | Cursor-native skills (synced copy of `skills/`; do not edit manually) |
| `.cursor/rules/` | Short always-on Cursor pointer rule |

---

## Adding a skill

See [CONTRIBUTING-skills.md](CONTRIBUTING-skills.md) for the full guide.

Quick rules:
- One `SKILL.md` per `skills/<skill-name>/` directory
- Under 200 lines; split into `references/` if it grows past that
- Description must contain trigger keywords — make it pushy
- No `curl` commands — skills describe intent, not raw HTTP
- PR must include agent test output (exact prompt + one-line result)
