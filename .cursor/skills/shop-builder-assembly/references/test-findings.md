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
- The post-write export proves Offer chain and Social quests use the `federated`
  transport with effective identities `sb-offer-chain` and `social-quests`. The
  sanitizer now extracts their internal field/type contracts without retaining IDs,
  content, or host URLs.
- The authenticated Publisher Account preview rendered the unpublished Home page with
  Fast Login, Promo slider, Call-to-action, Social media widgets, and Social quests.
  Empty Custom code remained hidden and the unconfigured Offer chain produced no live
  offer content, as expected. No publication action was taken.
- The formal evaluation matrix completed 10 dedicated-project runs across all three
  presets. Nine runs passed exact post-state verification and fresh authenticated
  Chrome previews; the preserved first run failed the CLI readiness/preview criteria.
  The resulting success rate is 90%, with no run above two manual interventions.
- Final exports verified the mobile single-page layout and the PC/live-service
  three-page layouts, their internal navigation, requested locale, catalog sections,
  and unpublished status. The main demonstration shop was independently exported and
  verified after assembly as well.
- The backup and apply scripts refresh authentication only through `xsolla auth login`,
  bound login attempts, retry Publisher-session bootstrap rate limits, and avoid
  redundant writes when pages, navigation, locales, or catalog links already match.

## CLI gaps found

1. Cookie-auth commands bootstrap a new Publisher session for every CLI process. A
   valid `xsolla auth login` token can stop yielding a cookie after one or more
   commands, and repeated supported logins eventually caused HTTP 429. The CLI needs
   a secure cached Shop Builder session or another non-manual multi-command flow.
   Tracked in [SB-8960](https://xsolla.atlassian.net/browse/SB-8960).
2. `verify-website --slug ...` returned HTTP 400 because the generated request omitted
   required `draftPagesIds` (request ID `6ac16aca0642a5f39b62dfb9045c4d77`).
   Tracked in [SB-8961](https://xsolla.atlassian.net/browse/SB-8961).
3. `enable-preview` and `preview-link` returned `admin_privileges_requred` for a
   Publisher Account project owner, while the same user could open Preview in the
   Publisher Account editor. Request IDs: `a361329b109800eaed7a48856185fe7b`
   and `146f3c9438cacf66102e1031434f5033`. Tracked in
   [SB-8962](https://xsolla.atlassian.net/browse/SB-8962).

Do not work around these gaps by copying `pa-v4-token` from browser storage. Continue
to use `xsolla auth login` and link the CLI tickets to SB-8796.
