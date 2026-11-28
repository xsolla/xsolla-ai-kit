# Test-project findings

Evidence below comes from a dedicated Publisher Account test project; it is not a
partner project. The website remains unpublished. Project identifiers are omitted
from committed evidence.

## Verified behavior

- `create-website`, `set-landing-type --type store`, `add-page`, `add-block`,
  `delete-block`, `move-block`, `update-block`, and `update-many-localization` wrote
  successfully through Xsolla CLI 1.9.4.
- A new store page is scaffolded with `header`, `leadGameSales`, `description`,
  `packs`, `bento-grid`, `gallery`, `requirements`, `faq`, and `footer` modules.
- `add-block --block newStore` succeeds and creates Shop Builder test-catalog
  sections in a blank project.
- The final mobile preset rendered in Publisher Account and its review preview with
  `header → leadGameSales → newStore → faq → footer`.
- Captured `get-structure` output places full block objects in `pages[].blocks[]` and
  landing-level block IDs in the top-level `blocks[]` array. This shape is covered by
  a regression test because earlier draft documentation described it in reverse.
- A second unpublished Web Portal template supplied six UI-created pages and exported
  contracts for every previously palette-only official block: Sidebar, Call-to-action,
  Fast Login, News, Promo slider, Promo codes, Reward system, Offer chain, Social media
  widgets, Custom code, and Social quests.
- The contract-lab run backed up before writes, stopped and rebound after the UI chose
  a different target slug, obtained a second explicit confirmation, and then added
  seven default blocks. Publisher Account reported every write saved. Custom code was
  left empty, Offer chain stayed in its safe no-chain state, and the site was never
  published.
- `add-block --block html` through the CLI creates the Custom code block empty but
  visible (`hidden: false`), unlike the hidden default in UI-created exports.
  `apply_plan.py` hides each Custom code block it adds with a `["hidden"]` block patch
  and leaves a Custom code block that was already on the page as the user set it.
- The post-write export proves Offer chain and Social quests use the `federated`
  transport with effective identities `sb-offer-chain` and `social-quests`. The
  sanitizer now extracts their internal field/type contracts without retaining IDs,
  content, or host URLs.
- The authenticated Publisher Account preview rendered the unpublished Home page with
  Fast Login, Promo slider, Call-to-action, Social media widgets, and Social quests.
  Empty Custom code remained hidden and the unconfigured Offer chain produced no live
  offer content, as expected. No publication action was taken.
- Ten dedicated-project runs across all three presets: nine passed exact post-state
  verification and fresh authenticated Chrome previews; the preserved first run failed
  the CLI readiness/preview criteria. No run needed more than two manual interventions.
- Final exports verified the mobile single-page layout and the PC/live-service
  three-page layouts, their internal navigation, requested locale, catalog sections,
  and unpublished status. The main demonstration shop was independently exported and
  verified after assembly as well.
- The backup and apply scripts run `xsolla auth login` only after the CLI reports an
  authentication failure, at most once per run, and re-check the CLI merchant, project,
  and sandbox setting after that login. They retry a Publisher-session bootstrap failure
  with backoff and never start a login for it, and avoid redundant writes when pages,
  navigation, locales, or catalog links already match.

## CLI gaps found

1. Cookie-auth commands bootstrap a new Publisher session for every CLI process. A
   valid `xsolla auth login` token can stop yielding a cookie after one or more
   commands. `xsolla auth login` opens a browser tab every time it runs, even with a
   valid session, so logging in before every command opened dozens of tabs per run and
   eventually caused HTTP 429; the scripts now retry such a failure with backoff and
   never log in for it. They log in only after an authentication failure, once per
   run. A login can also write merchant and project claims from the token into
   `.xsolla.json` in the working directory, so the scripts stop if the CLI context
   changes after a login. The CLI needs a secure cached Shop Builder session or
   another non-manual multi-command flow. Still open.
2. `verify-website --slug ...` returned HTTP 400 because the generated request omitted
   required `draftPagesIds`. Fixed in CLI 1.10.0: `--draft-pages-ids` is a required flag
   that takes a JSON array of page IDs.
3. `enable-preview` and `preview-link` returned `admin_privileges_requred` for a
   Publisher Account project owner, while the same user could open Preview in the
   Publisher Account editor. CLI 1.10.0 removed `preview-link`; `enable-preview` is
   still open. `enable-preview` answers with a token, and the link is the preview host,
   the slug and that token: `https://preview.xsollasitebuilder.com/<slug>?publicToken=<token>`,
   as Publisher Account's own public preview switch builds it. `scripts/preview_link.py`
   builds it the same way. Checked on 2026-11-28 on an unpublished test site: the script
   switched the preview on and a second run gave the same link without a write; a client
   with no cookies got the page by the link (HTTP 200) and "Preview session expired"
   without the token (HTTP 401); after `disable-preview` the same link answered 401.

First-time user runs (2026-10-29 to 2026-11-02, CLI 1.9.4) found two more:

4. `create-website` with a slug that another site already uses creates the site under a
   generated slug (the requested one plus a suffix). The next command on the requested
   slug returned HTTP 404; `apply_plan.py` now reads `list-websites` after creating and
   stops with the slug Shop Builder used. Still open.
5. A site created through the CLI can sign players in through a Login project that isn't
   linked to its store project: `get-landing` showed an `auth.loginId` of an unrelated
   Login project in two runs. Assembly reads it back and reports a mismatch. Still open.

A first-time user build on CLI 1.10.0 (2026-11-25) found two more:

6. `create-block` takes the module by `--module` and a `--page-id`, and refuses layout
   modules: `list-block-modules` lists `common-layout` under `cannotCreate`, as
   auto-created with every site. A site from `create-website` still has `layouts: []`.
   The scripts read that list first: while `common-layout` is on it they build the site
   without the layout and warn, and once it is off they run `create-block --module
   common-layout`. Still open.
7. On a new site, `add-page` seeds federated blocks of the redesigned set
   (`_site-builder-classic_header`, `_site-builder-classic_lead-gs` and others) instead
   of native modules. Their values have another shape. Assembly now builds on them in
   part: it makes a store page with `add-page --type topup`, orders and removes blocks,
   and sets the store's catalog sections. Still open: header links, texts, images and
   FAQ, which it reports under `needs_human`.

The live check of the redesigned blocks (below) found two more:

8. `add-page --type empty` returns HTTP 400 (`sourceOfCreation must be a string`): the
   command has no flag for that field. Still open.
9. `get-block-schema` rejects every `_site-builder-classic_…` name as an unknown module,
   and `create-block` takes such a name only with `--block-version`, which pins the
   block to that version. Still open.

Do not work around these gaps by copying `pa-v4-token` from browser storage. Continue
to use `xsolla auth login`. Gaps 1–3 are filed; 4 to 9 still need a ticket.

## Redesigned blocks, checked live

Checked on a new unpublished site in the dedicated test project (2026-11-25, CLI
1.10.0). `tests/fixtures/redesigned-site.json` is a masked export of that site, made
by `tests/mask_site_export.py`.

- A new site has `features.redesign: true`. Sites the same project made a month
  earlier have it false and still get native blocks. The switch is per site and is set
  when the site is created.
- `add-page` with no `--type` makes a `sellingpage` page of 13 redesigned blocks:
  header, lead-gs, description, game-packs, card-grid, gallery, system-requirements,
  faq and footer-v3, some of them more than once. It has no store.
- `--type store` seeds header, game-packs, store, card-grid, faq, news and footer-v3.
  `--type topup` seeds 16 blocks, among them five stores and the LiveOps blocks.
  `--type blank` seeds a header and a footer.
- Blocks on one page can have different versions: 6.0.13 and 6.0.14 sat side by side.
- Two reads of an unchanged site are identical, and a write to one block changes no
  other block. Only a native block's component `_id`s differ between reads, as before.
- Every seeded text is already saved, as plain text, in the page's localization scope.
  `common` is empty.
- `create-block --module _site-builder-classic_store` is refused as an unknown module.
  With `--block-version 6.0.13` it creates the block with its defaults and texts, puts
  it at `--position`, and pins it (`lockVersion: true`). Its three sections each show
  every virtual item.
- `create-block --module faq --version 2` and the older `add-block --block header` both
  create native blocks on a redesign site.
- Patches through `update-block` read back as written: a section's `store-group`
  resource and its `layout`, a shorter `storeSections`, an image as the whole
  `mediaValues` object, a header button's action in `components.button-action`, and a
  shorter `leftComponents`. The answer's `patches` list is empty even then, so read the
  block back instead.
- `update-many-localization` with a text's ID in the page scope changes that locale
  only.
- The header has three left buttons on the default page and four on a `store` page.
  Each scrolls to a block on the page.
- Replacing `theme.input.primary` changes the input but not the calculated theme:
  `get-theme` returns the same tokens. The palette needs another route on these sites.
- `get-rendered-block-html` returns the page's CSS class names, not its text, so it
  can't confirm what a block shows.

A full build of the mobile preset on a second new site, through the scripts (same day):

- Both runs went through under one yes: run 1 made the site and its page with
  `add-page --type topup`; the second render said "Covered by the approved plan"; run 2
  removed 12 seeded blocks, left header, hero, store and footer, and linked the store.
  `verify_structure.py` passed, with the two warnings about the layout and the header.
- A rerun on that site with another catalog group changed only the store's section.
- `enable-preview` returned a token, and the site opened in the public preview at
  desktop and phone widths, although it has no common layout. The store showed the
  group's items with images and prices. With a group type the project has no items of,
  it showed "No items to display".
- The header kept its four default links. Three of them scroll to blocks the trim
  removed, so they lead nowhere until the header is linked.
- The hero and the store kept Shop Builder's placeholder texts.
