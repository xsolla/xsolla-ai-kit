# xsolla-ai-kit — Agent Context

This file is read automatically by most AI coding agents (Cursor, Codex CLI, GitHub Copilot, Windsurf, Amp, Devin, Jules, Aider, Roo Code, Augment). Claude Code users: `CLAUDE.md` is a symlink to this file.

---

## What this repo is

`xsolla/xsolla-ai-kit` is the Xsolla agent skills toolkit — a collection of `SKILL.md` files (agentskills.io format) that teach AI coding agents how to execute Xsolla-specific workflows end-to-end, without requiring the Xsolla CLI as a dependency.

Skills call **Xsolla REST APIs directly**. The CLI (`xsolla/xsolla-cli`) is an optional shortcut once it ships to production.

---

## Skill inventory

| Skill | What it does |
|-------|-------------|
| `shop-setup` | **Orchestrator** — coordinates the full zero-to-shop flow, chaining all domain skills |
| `project-init` | Creates and configures an Xsolla project + merchant settings |
| `catalog-design` | Configures virtual catalog: items, pricing, virtual currency, bundles |
| `login-setup` | Integrates Xsolla Login / NewID authentication |
| `payments-config` | Integrates Pay Station + configures payment methods |
| `webhooks-impl` | Generates webhook handler code for order/payment events |
| `store-build` | Deploys WebShop or headless storefront |
| `shop-design` | Applies branding, theme tokens, LLM-assisted visual design |

---

## How to invoke a skill

Skills are loaded automatically when you open this repo in your agent. To run a specific skill, ask your agent naturally:

```
Set up a full Xsolla game shop for my project
→ triggers: shop-setup orchestrator

Configure my Xsolla catalog with items and pricing
→ triggers: catalog-design

Integrate Pay Station checkout into my game
→ triggers: payments-config
```

---

## Environment variables

```bash
XSOLLA_API_KEY=<your sandbox key>
PROJECT_ID=<your project ID>
MERCHANT_ID=<your merchant ID>
XSOLLA_ENV=sandbox   # default; set to "production" for prod
```

Use `xsolla config set merchant_id <id>` (if CLI is available) to persist locally instead of exporting each session.

Sandbox fixture project: `173042` — safe for any sandbox testing. Ask @j.manashti for the API key.

---

## Key directories

| Path | Contents |
|------|----------|
| `skills/` | SKILL.md files. One subdirectory per workflow. |
| `skills/<name>/references/` | Long-form reference docs. Keeps SKILL.md under 200 lines. |
| `docs/` | Architecture, distribution, and skill-gap guides. |
| `.github/workflows/` | sync-providers.yml — auto-generates Cursor .mdc files from SKILL.md |
| `.cursor/rules/` | Auto-generated Cursor rules (do not edit manually) |

---

## Adding a skill

See [CONTRIBUTING-skills.md](CONTRIBUTING-skills.md) for the full guide.

Quick rules:
- One `SKILL.md` per `skills/<skill-name>/` directory
- Under 200 lines; split into `references/` if it grows past that
- Description must contain trigger keywords — make it pushy
- No `curl` commands — skills describe intent, not raw HTTP
- PR must include agent test output (exact prompt + one-line result)
