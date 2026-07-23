# xsolla-ai-kit — Agent Context

This file is read automatically by most AI coding agents (Cursor, Codex CLI, GitHub Copilot, Windsurf, Amp, Devin, Jules, Aider, Roo Code, Augment). Claude Code users: `CLAUDE.md` is a symlink to this file.

---

## What this repo is

`xsolla/xsolla-ai-kit` is a **marketplace of Xsolla agent-skill plugins** — collections of `SKILL.md` files (agentskills.io format) that teach AI coding agents how to execute Xsolla-specific workflows end-to-end. Skills call **Xsolla REST APIs directly**; the CLI is an optional shortcut.

Each plugin is self-contained under `plugins/`. The marketplace manifest (`.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json`) lists them.

---

## Plugins

| Plugin | Directory | What it does |
|--------|-----------|--------------|
| `xsolla-ai-kit` | [`plugins/xsolla-ai-kit/`](plugins/xsolla-ai-kit/) | **Build any Xsolla game shop.** One entry point (`shop-setup`) runs a shared foundation (merchant-setup, catalog-design, login-setup, webhooks-impl) then routes to a build path: **headless** (headless-storefront, headless-login, headless-checkout-integration — a custom self-hosted store) or **Shop Builder** (shopbuilder-storefront + site/page/blocks/customize/custom-block — a hosted, no-code store). |

The plugin has its own `AGENTS.md` with the detailed skill inventory and the two-path flow.

---

## Repo layout

| Path | Contents |
|------|----------|
| `plugins/<name>/` | One self-contained plugin: skills + per-ecosystem configs (`.claude-plugin/`, `.codex-plugin/`, `.cursor-plugin/`, `gemini-extension.json`). |
| `.claude-plugin/marketplace.json` | Marketplace manifest (Claude Code). Lists all plugins. |
| `.agents/plugins/marketplace.json` | Marketplace manifest (agents ecosystem). |
| `.cursor/rules/` | Auto-generated Cursor rules, aggregated across all plugins (do not edit manually). |
| `docs/` | Architecture, distribution, and skill-gap guides. |
| `.github/workflows/` | sync-providers.yml — regenerates `.cursor/rules/` from every plugin's SKILL.md. |

---

## Environment variables

```bash
XSOLLA_MERCHANT_ID=<your merchant ID>
XSOLLA_PROJECT_ID=<your project ID>
XSOLLA_PROJECT_API_KEY=<your API key>
```
Set up by the `merchant-setup` skill.

---

## Adding a skill or plugin

See [CONTRIBUTING-skills.md](CONTRIBUTING-skills.md) for the full guide.

Quick rules:
- One `SKILL.md` per `plugins/<plugin>/skills/<skill-name>/` directory
- Keep SKILL.md focused; move long-form detail into `references/`
- Description must contain trigger keywords — make it pushy
- No `curl` commands — skills describe intent, not raw HTTP
- PR must include agent test output (exact prompt + one-line result)
