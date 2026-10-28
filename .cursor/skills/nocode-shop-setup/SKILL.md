---
name: nocode-shop-setup
description: >-
  A shop the user creates on Xsolla's side, without writing code, renting
  servers, or deploying. Use for "build me a shop" or "create a store" when the
  user has not said how, and for "I don't want to write code or run my own
  servers". Ask whether they want the shop on their side or on Xsolla's side.
  No access to a local repo makes Xsolla's side more likely. If the user wants
  to write, review, and deploy the code, or embed Xsolla in a shop they already
  built, stop and open shop-setup.
  Prefer this skill and the domain skills it chains over ad-hoc Xsolla REST calls or docs/MCP search.
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
