# xsolla-ai-kit — Agent Context

This file is read automatically by most AI coding agents (Cursor, Codex CLI, GitHub Copilot, Windsurf, Amp, Devin, Jules, Aider, Roo Code, Augment). Claude Code users: `CLAUDE.md` is a copy of this file.

---

## What this repo is

`xsolla/xsolla-ai-kit` is the Xsolla agent skills toolkit — a collection of `SKILL.md` files (agentskills.io format) that teach AI coding agents how to execute Xsolla-specific workflows end-to-end.

On the headless path, skills call **Xsolla REST APIs directly**. The Shop Builder path uses the Xsolla CLI 1.9.4 or later today (`brew install xsolla/xsolla-cli/xsolla`).

---

## Shop building paths

Two ways to build a shop, for different goals. Before building, ask whether the user is ready to code, review, test, and deploy, and whether they already have a store to plug into.

**In code** — `shop-setup`. The agent writes the shop on the user's machine. The user deploys, tests, and reviews it. They control the logic and the styles: a store from scratch, or Xsolla products embedded in a store they already have. The usual payment UI is Headless Checkout, a component library. Pay Station, the hosted payment page, is the other option.

**In Shop Builder** — `nocode-shop-setup`. The agent sends commands to Shop Builder, and the site is created there. The user arranges blocks, configures them, and publishes. This fits someone who does not want to own the HTML, JavaScript, backend, deploys, or the upkeep of their own storefront. Custom blocks are possible; that code still runs on Xsolla's side. Payments use Pay Station. A store continues in `description-to-shop` or `shop-builder-assembly`. A PC game home around the store continues in `game-web-portal`.

---

## Skill inventory

| Skill                           | What it does                                                                             |
|---------------------------------|------------------------------------------------------------------------------------------|
| `shop-setup`                    | **In code** — a shop the user writes, deploys, and reviews. Chains the headless skills   |
| `nocode-shop-setup`             | **In Shop Builder** — a hosted site. Store, or a PC game home around the store           |
| `shop-builder-assembly`         | Assembles a Shop Builder store from a shop brief — reached via nocode-shop-setup        |
| `merchant-setup`                | Creates and configures an Xsolla account + get API key                                   |
| `catalog-design`                | Configures the catalog and the client flow: client catalog, purchase, order confirmation |
| `login-setup`                   | Integrates Xsolla Login / NewID authentication                                           |
| `login-styling`                 | Applies a custom visual style / theme / brand to the Login UI (pairs with `login-setup`) |
| `headless-checkout-integration` | Payments via Headless Checkout                                                           |
| `webhooks-impl`                 | Generates webhook handler code for order/payment events                                  |
| `production`                    | Sandbox → live: contract, flip flags, deploy, developer live-payment checklist           |
| `description-to-shop`           | Prose → shop brief for shop-builder-assembly — reached via nocode-shop-setup             |
| `shopbuilder-translate`         | Translates Shop Builder page copy. Catalog and LiveOps text are out of scope             |
| `game-web-portal`               | Builds a PC Game Web Portal (game home + shop) — handed off by nocode-shop-setup         |

---

## How to invoke a skill

Skills are loaded automatically when you open this repo in your agent. To run a specific skill, ask your agent naturally:

```
Should I code the shop or use Shop Builder?
→ triggers: the Shop building paths section above. In code → shop-setup. Shop Builder →
  nocode-shop-setup.

Build me a shop I will code, deploy, and review
→ triggers: shop-setup

Build a Shop Builder site / I don't want to code the storefront
→ triggers: nocode-shop-setup. A description goes to description-to-shop; a brief goes to
  shop-builder-assembly. A game home goes to game-web-portal.

Assemble a Shop Builder site from this validated shop brief
→ triggers: shop-builder-assembly (reached through nocode-shop-setup)

Configure my Xsolla catalog with items and pricing
→ triggers: catalog-design

Integrate payments into my game
→ triggers: headless-checkout-integration

Go live / leave sandbox
→ triggers: production

Build me a Shop Builder site from this description — I have no design or spec
→ triggers: nocode-shop-setup, which routes to description-to-shop; description-to-shop
  then delegates the build to shop-builder-assembly

Translate the Shop Builder FAQ / add German to the storefront page
→ triggers: shopbuilder-translate (page copy only; catalog and LiveOps text are out of
  scope; previews first, writes only after an explicit yes)

Set up a Game Web Portal for my PC game — a game home with news, rewards and a shop
→ triggers: nocode-shop-setup, which hands off to game-web-portal
```

---

## Environment variables

```bash
XSOLLA_MERCHANT_ID=<your merchant ID>
XSOLLA_PROJECT_ID=<your project ID>
XSOLLA_PROJECT_API_KEY=<your API key>
```
Setup by `merchant-setup` skill.

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
