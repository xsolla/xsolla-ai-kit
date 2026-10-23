# Contract lab (Web Portal topup export)

Maintainer reference. Not used by any preset; the agent does not read it.

## Multi-page Web Portal contract lab

The September 11 export covers every previously palette-only official module. The
complete sanitized field/type inventory is committed as
[`exported-block-contracts-topup.json`](../../skills/shop-builder-assembly/tests/fixtures/exported-block-contracts-topup.json). The
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
| Quests | `_quest-platform_quests-block` | `federated` | package `0.1.0-qp-3126.2` | `questIds`, `maxQuests`, `overrides`, `layout`, `editorPreview`, and `translations` (heading is `translations.heading`); every field sits under `values.internalBlockValues.*` |

The same export also proves that this Web Portal template uses `lead`, while the
earlier store landing uses `leadGameSales`. It stores Offerwall, Daily rewards, Offer
chain, and Social quests as `federated` wrappers whose effective identities are in
`values.blockId`. Do not patch the wrapper wholesale.
## Remaining contract gap

Subscriptions is the only official inventory entry not observed in either the Add
block palette or these exports. Do not guess its template or field paths; keep it
blocked; the inventory reconciliation is still open.
