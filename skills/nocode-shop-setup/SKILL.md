---
name: nocode-shop-setup
description: >-
  A shop the user creates on Xsolla's side, without writing code, renting
  servers, or deploying. Use for "build me a shop" when the user has not said
  how, and for "I don't want to write code or run my own servers". Ask whether
  the shop should live on their side or on Xsolla's side. No local repo makes
  Xsolla's side more likely. If they will write and deploy the code, open
  shop-setup.
metadata:
  owner: a.pyanzin
  domain: store
---

# No-code shop setup

Build a site in Shop Builder. The agent sends commands; the site is created there.
The user arranges blocks, configures them, and publishes. Payments use Pay Station.
Custom blocks are possible, and that code still runs on Xsolla's side.

If the user wants to write the shop and embed Xsolla in their own code, stop and open `shop-setup`.
If the user has not said which they want, show **Shop building paths** in `AGENTS.md`
and ask.

## Before the site

Run these before the storefront. Do not run Headless Checkout or the headless login
widget: this site renders its own checkout and login.

1. `merchant-setup` — Publisher Account, project, and API key. With no local repo, follow
   that skill's rule for a key pasted into chat.
2. `catalog-design` — the items the site will sell. If the project already has that
   catalog, do not rebuild it.
3. `login-setup` — how the player signs in.

## Store or game home

Ask once, unless the request already says:

- **Store** — a shop made of blocks.
- **Game home** — a PC game home around the store: news, rewards, community, and an
  optional launcher. That is a Game Web Portal.

When a site already exists, read it. Do not write the answer to `.env`.

- Pages `/news`, `/rewards`, and `/store` mean a game home. The partner created it
  from the Multi-page web portal template.
- A site without those pages is a store.

## What to run

- Store, and the only input is a description → `description-to-shop`. It writes the
  brief and then calls `shop-builder-assembly`.
- Store, and a validated brief already exists → `shop-builder-assembly`.
- Game home → `game-web-portal`.

Do not start `description-to-shop` or `shop-builder-assembly` for a game home.
Do not start `game-web-portal` for a store.

Game name, platforms, description, store listing, domain, and locales are asked by the
storefront skill, which reuses [the onboarding ledger](references/onboarding-contract.md)
when a project directory exists. Do not ask them twice. With no project directory, the
answers stay in the conversation. Do not store the store-or-game-home choice in `.env`.

## After the site

Run `webhooks-impl` so a paid order can be delivered to the game. Skip it only when the
user says purchases are not delivered to a game server.

Do not run `production` here. Leaving sandbox on a shop the user deploys is `shop-setup`.
