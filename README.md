# Xsolla AI Toolkit

Agent skills for Xsolla — works with Claude Code, GitHub Copilot, Codex CLI, Windsurf, Roo Code, Augment, and more.

Install the kit in your AI coding tool and your agent can integrate Xsolla's APIs directly into your game, or build a fully functional headless web shop you own and host with full control of the frontend. It works with the AI coding tools you already use, with no engine lock-in and no proprietary assistant. Instead of generating code that looks right but breaks in production, your agent follows validated, production-ready logic encoding the correct integration paths, so the first AI-assisted attempt is the right one, with validation built in. From setting up a project and configuring a catalog to integrating Pay Station and implementing webhooks, the kit takes you from zero to a working integration.

## What's inside

This repo is a **marketplace of plugins**. Each plugin lives under `plugins/` and is self-contained.

| Plugin | Directory | Purpose |
|--------|-----------|---------|
| `xsolla-ai-kit` | `plugins/xsolla-ai-kit/` | Build any Xsolla game shop — one entry point (`shop-setup`) runs a shared foundation, then routes to the **headless** path (custom self-hosted storefront) or the **Shop Builder** path (hosted, no-code storefront) |

| Directory | Purpose |
|-----------|---------|
| `plugins/<name>/skills/` | SKILL.md files — one per Xsolla domain |
| `plugins/<name>/AGENTS.md` | Per-plugin context loaded automatically by most agents |
| `AGENTS.md` | Repo-level context / marketplace overview |
| `.github/copilot-instructions.md` | GitHub Copilot-specific context |
| `.cursor/rules/` | Auto-generated Cursor .mdc rules (aggregated across plugins) |
| `docs/` | Architecture, distribution, and skill-gap guides |

## Quick start

Install the kit as a plugin in your preferred coding agent, or copy it into your project for any tool that follows the [AGENTS.md](https://agents.md) convention:

### Claude Code

```bash
claude plugin marketplace add xsolla/xsolla-ai-kit && claude plugin install xsolla-ai-kit@xsolla-ai-kit
```

Or in a session:

```text
/plugin marketplace add xsolla/xsolla-ai-kit
/plugin install xsolla-ai-kit@xsolla-ai-kit
```

### Codex

```bash
codex plugin marketplace add xsolla/xsolla-ai-kit
```

### Gemini CLI

```bash
gemini extensions install https://github.com/xsolla/xsolla-ai-kit
```

### Other tools (Windsurf, Roo Code, Augment, Amp, Copilot, …)

For tools with no official plugin system, use a plugin by copying its `AGENTS.md` and `skills/` directory into your project root. Any tool that follows the [AGENTS.md](https://agents.md) convention will pick the skills up automatically the next time you open the project:

```bash
git clone https://github.com/xsolla/xsolla-ai-kit
cp -r xsolla-ai-kit/plugins/xsolla-ai-kit/AGENTS.md xsolla-ai-kit/plugins/xsolla-ai-kit/skills your-game-project/
```

Then set environment variables or run the `merchant-setup` skill:

```bash
XSOLLA_MERCHANT_ID=<your merchant ID>
XSOLLA_PROJECT_ID=<your project ID>
XSOLLA_PROJECT_API_KEY=<your API key>
```

## Skill inventory

One entry point runs the shared foundation, then routes to one of two build paths.

| Skill | Tier | Domain | Owner |
|-------|------|--------|-------|
| `shop-setup` | Entry | Single entry point — foundation + path router | @y.klochikhin |
| `merchant-setup` | Shared | Merchant and Project setup | @y.klochikhin |
| `catalog-design` | Shared | Items, pricing, virtual currency, bundles | @p.sanachev |
| `login-setup` | Shared | Shared Login / NewID project config | @mohammed_abujalala |
| `webhooks-impl` | Shared | Webhook handler generation | @e.chernykh |
| `headless-storefront` | Headless | Headless path orchestrator | @y.klochikhin |
| `headless-login` | Headless | Headless Login code integration | @mohammed_abujalala |
| `login-styling` | Headless | Theme/brand the Login widget (API CSS) | @elnur_khalilov |
| `headless-checkout-integration` | Headless | Payments via Headless Checkout (cards, Apple/Google Pay, saved methods) | @y.klochikhin |
| `shopbuilder-storefront` | Shop Builder | Shop Builder path orchestrator | — |
| `shopbuilder-site` / `-page` / `-blocks` / `-customize` | Shop Builder | The site→page→blocks→customize hierarchy | — |
| `shopbuilder-custom-block` | Shop Builder | Advanced escape hatch (custom React block) | — |

## Invoking a skill

Skills load automatically once the plugin is installed — the agent picks the
right one from your request (e.g. "build me a shop" → `shop-setup`). To force a
specific skill:

| Agent        | Explicit invocation                                             |
|--------------|-----------------------------------------------------------------|
| Claude Code  | `/shop-setup` (slash command; `/xsolla-ai-kit:shop-setup` if names clash) |
| Cursor       | `@shop-setup` via the Rules picker — or just describe the task  |
| Codex CLI    | No per-skill command — describe the task; Codex routes via AGENTS.md |
| Others       | Natural language; skills load from SKILL.md / generated rules   |

`shop-setup` is the single entry point — it runs the shared foundation
(`merchant-setup`, `catalog-design`, `login-setup`, `webhooks-impl`), then asks
or infers the build path and hands off to `headless-storefront` or
`shopbuilder-storefront`.

## Contributing

See [CONTRIBUTING-skills.md](CONTRIBUTING-skills.md) for the full guide on writing a skill.

## License

© 2026 Xsolla Inc. All rights reserved.
