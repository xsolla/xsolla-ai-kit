# xsolla-ai-kit

Agent skills for Xsolla — works with Claude Code, GitHub Copilot, Cursor, Codex CLI, Windsurf, Roo Code, Augment, and more.

Install the kit in your AI coding tool and you get guided, Xsolla-specific workflows — from setting up a project and configuring a catalog to integrating Pay Station, implementing webhooks, and launching a full game shop.

## What's inside

| Directory | Purpose |
|-----------|---------|
| `skills/` | SKILL.md files — one per Xsolla domain |
| `AGENTS.md` | Universal context loaded automatically by most agents |
| `.github/copilot-instructions.md` | GitHub Copilot-specific context |
| `.cursor/rules/` | Auto-generated Cursor .mdc rules |
| `docs/` | Architecture, distribution, and skill-gap guides |

## Quick start

Use the kit as a plugin in your preferred coding agent:

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

### Cursor

Search **Xsolla AI Kit** in Cursor's plugin marketplace and click Install.

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
| `payments-config` | Pay Station / headless checkout | @v.malykh | Planned |
| `webhooks-impl` | Webhook handler generation | @e.chernykh | Planned |
| `store-build` | WebShop / Site Builder / headless FE | @sergei_vasiuk | Planned |
| `shop-design` | Theme, branding, LLM-assisted design | @k.zatsepin | Planned |

## Contributing

See [CONTRIBUTING-skills.md](CONTRIBUTING-skills.md) for the full guide on writing a skill.

## License

© 2026 Xsolla Inc. All rights reserved.
