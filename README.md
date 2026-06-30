# Xsolla AI Toolkit

Agent skills for Xsolla — works with Claude Code, GitHub Copilot, Codex CLI, Windsurf, Roo Code, Augment, and more.

Install the kit in your AI coding tool and your agent can integrate Xsolla's APIs directly into your game, or build a fully functional headless web shop you own and host with full control of the frontend. It works with the AI coding tools you already use, with no engine lock-in and no proprietary assistant. Instead of generating code that looks right but breaks in production, your agent follows validated, production-ready logic encoding the correct integration paths, so the first AI-assisted attempt is the right one, with validation built in. From setting up a project and configuring a catalog to integrating Pay Station and implementing webhooks, the kit takes you from zero to a working integration.

## What's inside

| Directory | Purpose |
|-----------|---------|
| `skills/` | SKILL.md files — one per Xsolla domain |
| `AGENTS.md` | Universal context loaded automatically by most agents |
| `.github/copilot-instructions.md` | GitHub Copilot-specific context |
| `.cursor/rules/` | Auto-generated Cursor .mdc rules |
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
| `shop-setup` | Orchestrator — full zero-to-shop flow | @y.klochikhin | Done    |
| `merchant-setup` | Merchant and Project setup  | @y.klochikhin | Done    |
| `catalog-design` | Items, pricing, virtual currency, bundles | @p.sanachev | Planned |
| `login-setup` | Login / NewID / auth | @mohammed_abujalala | Planned |
| `headless-checkout-integration` | Payments via Headless Checkout | @y.klochikhin | Draft |
| `webhooks-impl` | Webhook handler generation | @e.chernykh | Planned |

## Contributing

See [CONTRIBUTING-skills.md](CONTRIBUTING-skills.md) for the full guide on writing a skill.

## License

© 2026 Xsolla Inc. All rights reserved.
