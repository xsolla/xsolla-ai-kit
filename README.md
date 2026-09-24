# Xsolla AI Toolkit

Agent skills for Xsolla — works with Claude Code, GitHub Copilot, Codex CLI, Windsurf, Roo Code, Augment, and more.

Install the kit in your AI coding tool and your agent can integrate Xsolla's APIs directly into your game, or build a fully functional headless web shop you own and host with full control of the frontend. It works with the AI coding tools you already use, with no engine lock-in and no proprietary assistant. Instead of generating code that looks right but breaks in production, your agent follows validated, production-ready logic encoding the correct integration paths, so the first AI-assisted attempt is the right one, with validation built in. From setting up a project and configuring a catalog to integrating Pay Station and implementing webhooks, the kit takes you from zero to a working integration.

## What's inside

| Directory | Purpose |
|-----------|---------|
| `skills/` | SKILL.md files — one per Xsolla domain |
| `AGENTS.md` | Universal context loaded automatically by most agents |
| `.github/copilot-instructions.md` | GitHub Copilot-specific context |
| `.cursor/skills/` | Cursor-native skills (synced from `skills/`) |
| `.cursor/rules/` | Short always-on Cursor pointer rule |
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

### Cursor

Add this repo as a workspace folder (or open it as the project), then use natural language — Cursor loads skills from `.cursor/skills/`.

```text
# Example
Integrate Xsolla Headless Checkout and let me pay with a credit card in sandbox
```

For an end-to-end shop, start with `shop-setup`. A short always-on rule in `.cursor/rules/xsolla-ai-kit.mdc` points the agent at those skills.

### Codex

```bash
codex plugin marketplace add xsolla/xsolla-ai-kit
```

### Gemini CLI

```bash
gemini extensions install https://github.com/xsolla/xsolla-ai-kit
```

### Other tools (Windsurf, Roo Code, Augment, Amp, Copilot, …)

For tools with no official plugin system, use the kit by copying `AGENTS.md` and the `skills/` directory into your project root. Any tool that follows the [AGENTS.md](https://agents.md) convention will pick the skills up automatically the next time you open the project:

```bash
git clone https://github.com/xsolla/xsolla-ai-kit
cp -r xsolla-ai-kit/AGENTS.md xsolla-ai-kit/skills your-game-project/
```

Then set environment variables or run the `merchant-setup` skill:

```bash
XSOLLA_MERCHANT_ID=<your merchant ID>
XSOLLA_PROJECT_ID=<your project ID>
XSOLLA_PROJECT_API_KEY=<your API key>
```

## Skill inventory

| Skill | Domain | Owner | Status  |
|-------|--------|-------|---------|
| `shop-plan` | Orchestrator — build-path decision | @s.sadruddin | Draft   |
| `shop-setup` | Orchestrator — full zero-to-shop flow | @y.klochikhin | Done    |
| `shopbuilder-storefront` | Store — Shop Builder orchestrator | @s.sadruddin | Draft   |
| `shopbuilder-site` | Store — Shop Builder site | @s.sadruddin | Draft   |
| `shopbuilder-page` | Store — Shop Builder page | @s.sadruddin | Draft   |
| `shopbuilder-blocks` | Store — Shop Builder blocks | @s.sadruddin | Draft   |
| `shopbuilder-customize` | Store — block customization | @s.sadruddin | Draft   |
| `shopbuilder-custom-block` | Store — custom React block | @s.sadruddin | Draft   |
| `merchant-setup` | Merchant and Project setup  | @y.klochikhin | Done    |
| `catalog-design` | Items, pricing, virtual currency, bundles | @p.sanachev | Planned |
| `login-setup` | Login / NewID / auth | @mohammed_abujalala | Planned |
| `headless-checkout-integration` | Payments via Headless Checkout | @y.klochikhin | Done |
| `webhooks-impl` | Webhook handler generation | @e.chernykh | Done |
| `production` | Sandbox → live / go-live | @y.klochikhin | Done |

## Invoking a skill

Skills load automatically once the plugin is installed — the agent picks the
right one from your request (e.g. "build me a shop" → `shop-setup`). To force a
specific skill:

| Agent        | Explicit invocation                                             |
|--------------|-----------------------------------------------------------------|
| Claude Code  | `/shop-setup` (slash command; `/xsolla-ai-kit:shop-setup` if names clash) |
| Cursor       | Describe the task (skills under `.cursor/skills/`) — or `@` a skill by name |
| Codex CLI    | No per-skill command — describe the task; Codex routes via AGENTS.md |
| Others       | Natural language; skills load from SKILL.md / generated rules   |

`shop-plan` comes first — it settles headless vs Shop Builder with the developer
and records the choice. `shop-setup` is the build entry point: it reads that
choice (delegating to `shop-plan` if none is recorded), then chains the domain
skills: `catalog-design` and `login-setup` either way, then
`headless-checkout-integration` for a headless build or `shopbuilder-storefront`
for a hosted Shop Builder one, and `webhooks-impl` and `production` for both.

## Contributing

See [CONTRIBUTING-skills.md](CONTRIBUTING-skills.md) for the full guide on writing a skill.

## License

© 2026 Xsolla Inc. All rights reserved.
