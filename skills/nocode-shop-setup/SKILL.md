---
name: nocode-shop-setup
description: >-
  A shop the user creates on Xsolla's side, without writing code, renting
  servers, or deploying: a web shop, webshop, storefront or Shop Builder site
  for a game, with its catalog and LiveOps. Use for "build me a shop" or
  "create a web shop for my game" with an App Store, Google Play or Steam
  link, when the user has not said they will code it, and for "I don't want
  to write code or run my own servers". With no local repo, or when the user
  says they don't code, the shop is on Xsolla's side: say so and continue.
  Ask only when a repo with storefront code exists and the user has not said.
  If the user will write and deploy the code, open shop-setup.
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

Run these first, so a blocker shows up in the first message, not after the catalog is
built.

1. **The latest CLI and kit.** Run `xsolla update --check`; when it can't tell (it has
   reported "not published") and the CLI came from Homebrew, run `brew upgrade xsolla`.
   Then refresh the kit with `xsolla skills install --global --source ai-kit`. Name both
   versions in the first message. The checks below are read-only.
2. **The project and sandbox mode.** Take the merchant and project from the Publisher
   Account link in the request, else from `xsolla config list --json`; with neither, ask
   for the project link in the batch. Shop Builder needs CLI sandbox mode off. When the
   CLI points at another project or has sandbox on, put "switch the CLI to this project,
   sandbox off" in the batch as the recommended answer. Never switch it without that yes.
3. **The CLI can make a site that opens.** A new store site gets its common layout only
   from a CLI with `xsolla shopbuilder create-block`. Run
   `xsolla shopbuilder create-block --help`. If the usage line doesn't name
   `create-block`, say in the first message: a new site this CLI creates won't open in
   the Editor, Publish or private preview until a newer CLI ships. Put "build the
   structure anyway, or wait" in the batch. A game home is built on the partner's
   template site instead; see **Store or game home**.
4. **The project is an approved test project.** Shop Builder writes need the project on
   the approved test-project allowlist, with its approver and approval reference. The
   format is in [shop brief](../shop-builder-assembly/references/shop-brief.md); the
   file lives outside the repository, at `$XSOLLA_APPROVED_TEST_PROJECTS`, by default
   `~/.config/xsolla/approved-test-projects.json`. If this project isn't listed, ask in
   the batch who approved it as a dedicated test project (a mentor or tech lead) and a
   link to that approval. When both answers arrive, add the entry to that file with
   exactly what the user gave. Never fill in the approver or the reference yourself, and
   never use this chat as the approval reference. Pass the file to the assembly scripts as
   `--approved-test-projects`; `shopbuilder-translate` reads only the variable.
5. **The game.** Read the user's store listing link, if they gave one: name, platforms,
   developer, description, icon and screenshots.
6. **Browser and design tools in this session.** Find the browser that is signed in to
   Publisher Account (a built-in browser, Claude in Chrome, or another extension) and use
   it for every browser step; don't ask which one. Check that the mockup's design tool,
   such as Figma, is available in this session: a setup log from an earlier session is not
   proof. When one is missing, say in the first message what that changes: no visual
   review without a signed-in browser, an HTML mockup instead of Figma.

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
- For a game home, the first message says to create the site in Publisher Account if it
  doesn't exist yet: Storefronts → Websites → Multi-page web portal → Manual.

Do not write the answer to `.env`.

## One batch of questions

Ask everything still missing in **one** message, each question with a recommended
answer, so a reply such as "all recommended" settles it:

- which side, only when the rule above says to ask;
- the project link, or switching the CLI to it with sandbox off, only when check 2 says;
- store or game home, only for a PC game;
- the test-project approver and approval link, only when the project isn't listed. This
  question has **no** recommended answer: only the user can give it;
- build without the common layout or wait, only when the CLI lacks `create-block`;
- the storefront intake the listing didn't answer: game name, platforms, a short
  description, whether the listing is theirs and its art and text may be used, the
  site's address, and its languages. The storefront skills read these answers and don't
  ask them again;
- item delivery: whether a game server should receive paid orders. Recommended: say it
  means webhook handler code the developer deploys on their own server;
- what `merchant-setup` and `catalog-design` still need after reading the project.

Ask in plain words, with one filled-in example per answer. Never send a template with
placeholders such as `<name>` or `<link>` for the user to fill in.

## Before the site

Run these before the storefront. Do not run Headless Checkout or the headless login
widget: this site renders its own checkout and login.

1. `merchant-setup` — Publisher Account, project, and API key. When the Xsolla CLI is
   signed in (`xsolla auth login`), it holds the project key: don't ask the user for one,
   in the batch or later. Only without the CLI, follow that skill's rule for a key pasted
   into chat.
2. `catalog-design` — the items, packs, bundles and LiveOps the site will sell, through
   the CLI's `catalog` and `liveops` commands. Only its catalog steps: the archetype, the
   proposal and pricing. No client catalog, purchase code or checkout: the site has its
   own. If the project already has that catalog, do not rebuild it. Its proposal waits
   for the one yes below.
3. `login-setup` — only to create or confirm the Login project the site signs players in
   with. No Login Widget code and no `login-styling`.

## What to run

- Store, and the input is a description or a store listing link →
  `description-to-shop`. It writes the brief and then calls `shop-builder-assembly`.
- Store, and a validated brief already exists → `shop-builder-assembly`.
- Game home → `game-web-portal`.

Do not start `description-to-shop` or `shop-builder-assembly` for a game home.
Do not start `game-web-portal` for a store.

## One approval

Show the catalog proposal and the storefront skill's plan, with its desktop and mobile
mockup, **in one message** and ask for **one yes**. That yes lets `catalog-design` create
the catalog and the storefront skill apply its plan, in that order. The storefront skill
still runs its own preflight and backup, and asks again only for what its plan didn't
show. When the catalog already exists, the plan alone is the message.

Before showing the proposal, check it against the limits in `catalog-design`'s LiveOps
reference: each offer chain or reward chain step takes one item, and offer chain steps
only items and bundles. After the yes, if something can't be created exactly as proposed,
create the rest, then show what differs and ask before substituting anything: an extra
bundle or a changed step is a change the yes didn't cover.

The batch above asks the storefront intake. With a project directory, record the answers
in [the onboarding ledger](references/onboarding-contract.md); without one, they stay in
the conversation. The storefront skills read them and ask only about a conflict. Do not
store the store-or-game-home choice in `.env`.

## After the site

When the batch said a game server receives paid orders, run `webhooks-impl`. It writes
handler code the developer deploys on their own server; say so. Otherwise skip it and
list item delivery as not connected in the handoff.

Do not run `production` here. Leaving sandbox on a shop the user deploys is `shop-setup`.
