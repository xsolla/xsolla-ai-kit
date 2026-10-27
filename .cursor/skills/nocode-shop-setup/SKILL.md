---
name: nocode-shop-setup
description: >-
  Entry for a no-code Shop Builder site. Use for "build a Shop Builder shop",
  "no-code store", "I don't want to code or deploy the storefront", "hosted shop",
  or "game home with news and rewards around the store". Asks whether the user
  needs only a store or a PC game home, then calls description-to-shop,
  shop-builder-assembly, or game-web-portal. If a site already exists, tell a
  store from a game home by its pages. Not for a shop the user codes and deploys
  — that is shop-setup.
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
