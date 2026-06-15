# xsolla-ai-kit

Agent skills for Xsolla — works with Claude Code, GitHub Copilot, Cursor, Codex CLI, Windsurf, Roo Code, Augment, and more.

Open this repo in your AI coding tool and you immediately get guided, Xsolla-specific workflows: from setting up a project, configuring a catalog, integrating Pay Station, implementing webhooks, to launching a full game shop.

## What's inside

| Directory | Purpose |
|-----------|---------|
| `skills/` | SKILL.md files — one per Xsolla domain |
| `AGENTS.md` | Universal context loaded automatically by most agents |
| `.github/copilot-instructions.md` | GitHub Copilot-specific context |
| `.cursor/rules/` | Auto-generated Cursor .mdc rules |
| `docs/` | Architecture, distribution, and skill-gap guides |

## Quick start

No installation required. Just open this repo in your agent:

```bash
# Claude Code
claude --add-dir /path/to/xsolla-ai-kit

# Cursor
# Add this repo as a workspace folder

# GitHub Copilot
# Clone and open in VS Code — copilot-instructions.md loads automatically
```

### Claude Code: install once, use everywhere

Install the plugin from a terminal — it's user-scoped, so the skills are then available in **every** project you open:

```bash
claude plugin marketplace add xsolla/xsolla-ai-kit && claude plugin install xsolla-ai-kit@xsolla-ai-kit
```

Already inside a Claude Code session? Run the two slash commands instead (`&&` won't work there):

```text
/plugin marketplace add xsolla/xsolla-ai-kit
/plugin install xsolla-ai-kit@xsolla-ai-kit
```

Update later with `claude plugin marketplace update xsolla-ai-kit`.

### Codex: install as a plugin

Add the marketplace from a terminal, then install from the plugin directory:

```bash
codex plugin marketplace add xsolla/xsolla-ai-kit
```

Restart Codex, open the plugin directory, choose the **Xsolla AI Kit** marketplace, and install the `xsolla-ai-kit` plugin. Refresh later with `codex plugin marketplace upgrade xsolla-ai-kit`.

> Opening this repo in Codex also picks the plugin up automatically — the repo ships a marketplace at `.agents/plugins/marketplace.json`.

### Gemini CLI: install as an extension

Gemini has no marketplace — the repo *is* the extension. Install it directly from a terminal:

```bash
gemini extensions install https://github.com/xsolla/xsolla-ai-kit
```

Restart Gemini CLI to load the skills. Pull updates later with `gemini extensions update xsolla-ai-kit`.

Set environment variables or use `merchant-setup` skill:

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
