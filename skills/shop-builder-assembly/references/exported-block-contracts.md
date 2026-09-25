# Exported block contracts

These are sanitized structural observations from approved SB-8796 test-project
exports: a UI-created `store` landing on September 10, 2026 and an unpublished,
UI-created multi-page `topup` portal on September 11, 2026. No IDs, localized copy,
account data, or asset URLs are retained. Regenerate a machine-readable summary with:

```bash
python3 scripts/extract_block_contracts.py <ui-export.json> \
  --source-label "approved test project; UI-created export; YYYY-MM-DD" \
  --output references/exported-block-contracts-<landing-type>.json
```

`blockValues` below means the exported block's top-level `values` object. It is an
observed shape, not permission to replace the entire object. Use narrow Immer patches;
localized `L:` content must be updated through localization commands.

| Module | Version | Observed instances | `blockValues` fields (`name:type`) | `components[]` item fields |
|---|---:|---:|---|---|
| `header` | 3 | 1 | `background:object`, `components:object`, `fixedComponents:array`, `fixedWidth:boolean`, `headerFixed:object`, `isOverlap:boolean`, `leftComponents:array`, `rightComponents:array`, `script:object` | — |
| `leadGameSales` | field absent | 1 | `align:string`, `background:object`, `buttons:array`, `enable:boolean`, `platforms:object`, `script:object`, `subtitle:object`, `tags:object`, `title:object` | — |
| `description` | 2 | 1 | `align:string`, `background:object`, `components:object`, `componentsIds:array`, `hideFullDescription:boolean`, `readMoreButton:object`, `showLessButton:object`, `template:string`, `title:object` | — |
| `packs` | 2 | 3 | `background:object`, `bigClickArea:boolean`, `description:object`, `horizontalScroll:boolean`, `layout:string`, `packs:array`, `title:object` | — |
| `bento-grid` | field absent | 3 | `background:object`, `description:object`, `grid:object`, `gridComponents:object`, `sliderOnMobile:boolean`, `title:object` | — |
| `gallery` | 2 | 1 | `background:object`, `description:object`, `duplicateArrows:boolean`, `sliderLoop:boolean`, `slides:array`, `slidesPreview:boolean`, `title:object` | — |
| `requirements` | 2 | 1 | `background:object`, `layout:string`, `title:object` | `_id`, `enable`, `type`, `value` |
| `faq` | 2 | 1 | `background:object`, `enable:boolean`, `questionMode:boolean`, `script:object`, `template:string`, `title:object` | `_id`, `answer`, `enable`, `question`, `type`, `value` |
| `footer` | 2 | 1 | `background:object`, `description:object`, `layout:string`, `logo:object`, `script:object` | `_id`, `enable`, `type`, `value` |
| `newStore` | field absent | 1 | `alignment:string`, `background:object`, `description:object`, `enable:boolean`, `loginButton:object`, `script:object`, `tabs:object`, `title:object` | `_id`, `card`, `enable`, `section`, `type` |

The site-level `cart` object contains `enable:boolean`, `isRequiredAuth:boolean`, and
`showPromocodeField:boolean`. Page and site theme source fields are documented in
[cli-operations.md](cli-operations.md); computed theme fields are not patch inputs.

## Multi-page Web Portal contract lab

The September 11 export covers every previously palette-only official module. The
complete sanitized field/type inventory is committed as
[`exported-block-contracts-topup.json`](exported-block-contracts-topup.json). The
contract extractor resolves federated blocks by `values.blockId` and reports their
package version without retaining host URLs or block IDs.

| UI block | Effective module | Runtime transport | Version | Observed contract highlights |
|---|---|---|---|---|
| Sidebar | `sidebar` | native | field absent | `background`, `description`, `logo`, `menu`, `platforms`, `socials`, `storeButtonIds`, `storeButtons`, `title` |
| Call-to-action | `hero` | native | field absent | `affiliate`, `background`, `description`, `enable`, `logo`, `template`, `title`; component action fields |
| Fast Login | `fast-login` | native | field absent | background, deep-link, login-button, placeholder, script, title/description, and instruction-link objects |
| News | `news` | native | 2 | categories, launcher ID, tabs, scroll/display flags, title, background, and view-more action |
| Promo slider | `promoSlider` | native | field absent | description, enable, logo, slide arrow, loop configuration; slide component fields |
| Promo codes | `promocodes` | native | 2 | background, description, placeholder, redeem button, script, and title |
| Reward system | `rewards` | native | field absent | chains, script, and tabs |
| Offer chain | `sb-offer-chain` | `federated` | package `0.12.4` | chain settings, nullable offer-chain ID, step settings, and translations |
| Social media widgets | `embed` | native | field absent | background, enable, template, and title |
| Custom code | `html` | native | 2 | CSS, enable, HTML, and JavaScript strings; the observed default is empty and hidden |
| Social quests | `social-quests` | `federated` | package `5.0.0` | quest enable/order flags, URLs, translations, success/error modal fields, and media/dimension fields |

The same export also proves that this Web Portal template uses `lead`, while the
earlier store landing uses `leadGameSales`. It stores Offerwall, Daily rewards, Offer
chain, and Social quests as `federated` wrappers whose effective identities are in
`values.blockId`. Do not patch the wrapper wholesale.

## Remaining contract gap

Subscriptions is the only official inventory entry not observed in either the Add
block palette or these exports. Do not guess its template or field paths; keep it
blocked under [SB-8990](https://xsolla.atlassian.net/browse/SB-8990).
