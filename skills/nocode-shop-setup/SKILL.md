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
  Also the first-run setup for Shop Builder: it installs the Xsolla CLI this path
  runs on and has the user sign in. If the user will write and deploy the code, open
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
is still missing), and one yes. When the Xsolla CLI isn't signed in yet, signing in, in
their own terminal, comes before the batch. Everything else runs without them. Never
stop to ask "should I continue?".

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

1. **The CLI: installed, signed in, current.** This path runs only through the Xsolla
   CLI. If `xsolla --version` fails, say so in one line and install it now; on Windows,
   too. Then the user runs `xsolla auth login` in their own terminal: it opens a browser
   and doesn't complete from the agent's shell. Steps per platform:
   [CLI setup](references/cli-setup.md). Never ask for a pasted API key, or for a
   Publisher Account link to make one, instead. Then run `xsolla update --check`; when it
   can't tell (it has reported "not published") and the CLI came from Homebrew, run
   `brew upgrade xsolla`. Refresh the kit with
   `xsolla skills install --global --source ai-kit`. Name both versions in the first
   message. The checks below are read-only, except the CLI switch in check 2.
2. **The project and sandbox mode.** Take the merchant and project from the Publisher
   Account link in the request, else from `xsolla config list --json`, and don't ask to
   confirm it: the plan names the project. With neither, ask for the project link in the
   batch. Shop Builder needs CLI sandbox mode off, and the backup and preflight refuse
   sandbox mode, so this can't wait for the plan. When the CLI points at another project
   or has sandbox on, switch it yourself (`xsolla config set merchant-id <id>`,
   `xsolla config set project-id <id>`, `xsolla config set sandbox false`). Say in the
   first message that the CLI config keeps it, so every later `xsolla` command, in this
   session and others, reaches the live project, payments and refunds included, and give
   the undo: `xsolla config set sandbox true` and the previous merchant and project, by
   ID. Nothing is written to the project before the plan's yes.
3. **The CLI can make a site that opens.** A new store site gets its common layout only
   from a CLI with `xsolla shopbuilder create-block`. Run
   `xsolla shopbuilder create-block --help`. If the usage line doesn't name
   `create-block`, say in the first message: a new site this CLI creates won't open in
   the Editor, Publish or private preview until a newer CLI ships. Put the choice in the
   batch. Recommended: the developer creates the site in Publisher Account (Storefronts →
   Websites, from the Single-page shop template) and gives its address; assembly builds on
   it, with more pages when the preset has them, and it opens in the Editor and preview.
   The other answers: build the structure anyway, or wait. A game home is built on the
   partner's template site; see **Store or game home**.
4. **The game.** Read the user's store listing link, if they gave one: name, platforms,
   developer, description, icon and screenshots.
5. **The catalog, LiveOps and Login projects.** Read the project's catalog groups,
   items, bundles and LiveOps with the read-only `xsolla catalog` and `xsolla liveops`
   list commands, and its Login projects. Draft `catalog-design`'s proposal now, so its
   questions go in the batch instead of a second round.
6. **Browser and design tools in this session.** Find the browser that is signed in to
   Publisher Account (a built-in browser, Claude in Chrome, or another extension) and use
   it for every browser step; don't ask which one. Check that the mockup's design tool,
   such as Figma, is available in this session: a setup log from an earlier session is not
   proof. When one is missing, say in the first message what that changes: no visual
   review without a signed-in browser, an HTML mockup instead of Figma.

## Store or game home

- A **game home** is a Game Web Portal: a home around the store, with news, rewards and
  community, for a game on PC, the App Store or Google Play. Only a PC game gets the
  optional launcher section.
- An existing site with pages `/news`, `/rewards`, and `/store` is a game home. The
  partner created it from the Multi-page web portal template. A site without those
  pages is a store.
- Otherwise, unless the request already says, put **store or game home** in the batch,
  with **store** as the recommended answer.
- For a game home, the first message says to create the site in Publisher Account if it
  doesn't exist yet: Storefronts → Websites → Multi-page web portal → Manual.

Do not write the answer to `.env`.

## A Figma design

When a Shop Builder site, new or existing, has to look like a Figma design, follow
[Matching a Figma design in Shop Builder](references/figma-design.md): standard blocks
first; a Custom Block (`xsolla shopbuilder create-custom-block`) for each section a
standard block can't match one to one, named in the plan by its purpose with the reason;
never custom code, and never touch custom code already on the site; prices, timers,
items, cart and login stay live; never publish; check at 1440, 1024 and 390 px against
the Figma frames, and list what neither can match.

## One batch of questions

Ask everything still missing in **one** message, each question with a recommended
answer, so a reply such as "all recommended" settles it:

- which side, only when the rule above says to ask;
- the project link, only when neither the request nor the CLI names a project;
- store or game home;
- build without the common layout or wait, only when the CLI lacks `create-block`;
- the storefront intake the listing didn't answer: game name, platforms, a short
  description, the site's address, and its languages (recommended: the primary language only; more go in
  later with `shopbuilder-translate`, which shows its own preview). The storefront
  skills read these answers and don't ask them again;
- `catalog-design`'s questions: the archetype, what to do with test or demo entries
  already in the project (recommended: leave them and show only the new groups on the
  site; disabling one changes the live catalog at once), and any commercial value it
  can't infer;
- item delivery: whether a game server should receive paid orders. Recommended: not now;
  purchases still work, but items reach the game only once the developer deploys webhook
  handler code on their own server;
- what `merchant-setup` still needs after reading the project.

Ask in plain words, with one filled-in example per answer. Never send a template with
placeholders such as `<name>` or `<link>` for the user to fill in.

## Before the site

Run these before the storefront. Do not run Headless Checkout or the headless login
widget: this site renders its own checkout and login.

1. `merchant-setup` — Publisher Account, project, and API key. The CLI signed in at
   check 1 holds the project key: don't ask the user for one, in the batch or later, and
   don't take that skill's pasted-key route: this path has none. Creating a project key
   is a write: never before the yes. If the CLI's key fails a read, put creating one in
   the batch.
2. `catalog-design` — the items, packs, bundles and LiveOps the site will sell, through
   the CLI's `catalog` and `liveops` commands. Only its catalog steps: the archetype, the
   proposal and pricing. No client catalog, purchase code or checkout: the site has its
   own. If the project already has that catalog, do not rebuild it. Its proposal waits
   for the one yes below.
3. `login-setup` — only for the Login project the site signs players in with. Before the
   yes, only read the existing ones. Creating or linking one is a write: put it in the one
   approval's proposal, or list it as a Publisher Account step. No Login Widget code and
   no `login-styling`.

## What to run

- Store, and the input is a description or a store listing link →
  `description-to-shop`. It writes the brief and then calls `shop-builder-assembly`.
- Store, and a validated brief already exists → `shop-builder-assembly`.
- Game home → `game-web-portal`.

Do not start `description-to-shop` or `shop-builder-assembly` for a game home.
Do not start `game-web-portal` for a store.

## One approval

Show the catalog proposal and the storefront skill's plan in **one message**, with a
desktop and mobile mockup for a store (a game home shows `game-web-portal`'s plan), and
ask for **one yes**. That yes lets `catalog-design` create
the catalog and the storefront skill apply its plan, in that order. The storefront skill
still runs its own preflight and backup, and asks again only for what its plan didn't
show. When the catalog already exists, the plan alone is the message. When the proposal
writes to the catalog, the plan says so: the project is live, and catalog changes reach
the store and game clients at once, with no publish step.

Before showing the proposal, check it against the limits in `catalog-design`'s LiveOps
reference: each offer chain or reward chain step takes one item, and offer chain steps
only items and bundles. Include every value the catalog API requires, such as the virtual
currency's own unit price, so none has to be invented later. After the yes, if something can't be created exactly as proposed,
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
