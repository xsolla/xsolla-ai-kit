---
name: nocode-shop-setup
description: >-
  A shop the user creates on Xsolla's side, without writing code, renting
  servers, or deploying. Use for "build me a shop" when the user has not said
  how, and for "I don't want to write code or run my own servers". With no
  local repo, or when the user says they don't code, the shop is on Xsolla's
  side: say so and continue. Ask only when a repo with storefront code exists
  and the user has not said. If the user will write and deploy the code, open
  shop-setup.
metadata:
  owner: a.pyanzin
  domain: store
---

# No-code shop setup

Build a site in Shop Builder. The agent sends commands; the site is created there.
The user arranges blocks, configures them, and publishes. Payments use Pay Station.
Custom blocks are possible, and that code still runs on Xsolla's side.

The user acts three times: the build request, one batch of answers (only when a value
is still missing), and one yes. Everything else runs without them. Never stop to ask
"should I continue?".

## Which side

- The user will write and deploy the code → stop and open `shop-setup`.
- Otherwise, no local repo, or the user says they don't code or don't want to run
  servers → Xsolla's side. Say so in one line and continue; don't ask.
- A local repo with storefront code and no stated preference → put the question in the
  batch below, with **Shop Builder** as the recommended answer when the user has not
  said they will maintain the code. **Shop building paths** in `AGENTS.md` explains the
  two options.

## Check what can be built, before any question

Run these read-only checks first, so a blocker shows up in the first message, not after
the catalog is built.

1. **The CLI can make a site that opens.** A new store site gets its common layout only
   from a CLI with `xsolla shopbuilder create-block`. Run
   `xsolla shopbuilder create-block --help`. If the usage line doesn't name
   `create-block`, say in the first message: a new site this CLI creates won't open in
   the Editor, Publish or private preview until a newer CLI ships. Put "build the
   structure anyway, or wait" in the batch. A game home is not affected: the partner
   creates its site from a template.
2. **The project is an approved test project.** Shop Builder writes need the project on
   the approved test-project allowlist, with its approver and approval reference. The
   format is in [shop brief](../shop-builder-assembly/references/shop-brief.md); the
   file lives outside the repository, at `$XSOLLA_APPROVED_TEST_PROJECTS`, by default
   `~/.config/xsolla/approved-test-projects.json`. If this project isn't listed, ask in
   the batch who approved it as a dedicated test project (a mentor or tech lead) and a
   link to that approval. Record exactly what the user gives. Never fill in the approver
   or the reference yourself, and never use this chat as the approval reference.
3. **The platform.** Read the user's store listing link, if they gave one, for the
   platforms.

## Store or game home

- A **game home** is a Game Web Portal: a PC game home around the store, with news,
  rewards, community, and an optional launcher. It is **PC only**. When the game ships
  only on the App Store or Google Play, don't offer it: build a store and say why in one
  line.
- An existing site with pages `/news`, `/rewards`, and `/store` is a game home. The
  partner created it from the Multi-page web portal template. A site without those
  pages is a store.
- Otherwise, unless the request already says, put **store or game home** in the batch,
  with **store** as the recommended answer.

Do not write the answer to `.env`.

## One batch of questions

Ask everything still missing in **one** message, each question with a recommended
answer, so a reply such as "all recommended" settles it:

- which side, only when the rule above says to ask;
- store or game home, only for a PC game;
- the test-project approver and approval link, only when the project isn't listed;
- build without the common layout or wait, only when the CLI lacks `create-block`;
- what `merchant-setup`, `catalog-design` and the storefront skill still need after
  reading the ledger, the project, and the store listing.

Ask in plain words, with one filled-in example per answer. Never send a template with
placeholders such as `<name>` or `<link>` for the user to fill in.

## Before the site

Run these before the storefront. Do not run Headless Checkout or the headless login
widget: this site renders its own checkout and login.

1. `merchant-setup` — Publisher Account, project, and API key. With no local repo, follow
   that skill's rule for a key pasted into chat.
2. `catalog-design` — the items the site will sell. If the project already has that
   catalog, do not rebuild it. Its proposal waits for the one yes below.
3. `login-setup` — how the player signs in.

## What to run

- Store, and the only input is a description → `description-to-shop`. It writes the
  brief and then calls `shop-builder-assembly`.
- Store, and a validated brief already exists → `shop-builder-assembly`.
- Game home → `game-web-portal`.

Do not start `description-to-shop` or `shop-builder-assembly` for a game home.
Do not start `game-web-portal` for a store.

## One approval

Show the catalog proposal and the storefront skill's plan **in one message** and ask for
**one yes**. That yes lets `catalog-design` create the catalog and the storefront skill
apply its plan, in that order. The storefront skill still runs its own preflight and
backup, and asks again only for what its plan didn't show. When the catalog already
exists, the plan alone is the message.

Game name, platforms, description, store listing, domain, and locales are asked by the
storefront skill, which reuses [the onboarding ledger](references/onboarding-contract.md)
when a project directory exists. Do not ask them twice. With no project directory, the
answers stay in the conversation. Do not store the store-or-game-home choice in `.env`.

## After the site

Run `webhooks-impl` so a paid order can be delivered to the game. Skip it only when the
user says purchases are not delivered to a game server.

Do not run `production` here. Leaving sandbox on a shop the user deploys is `shop-setup`.
