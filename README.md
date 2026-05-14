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

Set environment variables before running any skill:

```bash
export XSOLLA_API_KEY=<your-sandbox-key>
export PROJECT_ID=<your-project-id>
export MERCHANT_ID=<your-merchant-id>
export XSOLLA_ENV=sandbox   # default; set to "production" for prod
```

Sandbox fixture: project ID `173042` — safe for any sandbox testing.

## Skill inventory

| Skill | Domain | Owner | Status |
|-------|--------|-------|--------|
| `shop-setup` | Orchestrator — full zero-to-shop flow | @j.manashti | Draft |
| `project-init` | Project + CLI setup | @j.manashti | Draft |
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
