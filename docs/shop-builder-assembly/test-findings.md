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
  authentication or Publisher-session bootstrap failure, at most once per run, and
  re-check the CLI merchant, project, and sandbox setting after that login. They retry
  Publisher-session bootstrap rate limits and avoid redundant writes when pages,
  navigation, locales, or catalog links already match.

## CLI gaps found

1. Cookie-auth commands bootstrap a new Publisher session for every CLI process. A
   valid `xsolla auth login` token can stop yielding a cookie after one or more
   commands. `xsolla auth login` opens a browser tab every time it runs, even with a
   valid session, so logging in before every command opened dozens of tabs per run and
   eventually caused HTTP 429; the scripts now log in only after such a failure, once
   per run. A login can also write merchant and project claims from the token into
   `.xsolla.json` in the working directory, so the scripts stop if the CLI context
   changes after a login. The CLI needs a secure cached Shop Builder session or
   another non-manual multi-command flow. Still open.
2. `verify-website --slug ...` returned HTTP 400 because the generated request omitted
   required `draftPagesIds`. Still open.
3. `enable-preview` and `preview-link` returned `admin_privileges_requred` for a
   Publisher Account project owner, while the same user could open Preview in the
   Publisher Account editor. Still open.

Do not work around these gaps by copying `pa-v4-token` from browser storage. Continue
to use `xsolla auth login`; the CLI gaps above are filed and still open.
