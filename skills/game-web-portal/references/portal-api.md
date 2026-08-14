# Xsolla Game Web Portal — Shop Builder API reference

The portal itself (sites, pages, blocks, theme, copy, domain, preview, publication)
is Shop Builder. This file is the API surface for Steps 3–8. Catalog, Login, and
checkout stay delegated — see `SKILL.md`.

## Context

- **Base URL:** `https://sitebuilder.xsolla.com/api`
- **Auth:** `Authorization` header carrying the Publisher Account admin token.
  A missing, stale, or unauthorized token returns `401/403` → `needs_access`.
  (The Xsolla CLI drives the same service with a publisher session cookie
  `pa-v4-token` instead; either way, this is *not* `XSOLLA_PROJECT_API_KEY`.)
- **Path shorthand below:** `{M}` = `/merchant/{merchantId}/project/{projectId}`

### Two different keys — the top cause of hard failures

| Key | What it is | Used by |
|---|---|---|
| `domain` | the site's domain label, e.g. `voidwall` → `voidwall.xsolla.site` | `landing/{domain}/…`, localization, preview, publication, versions |
| `landingId` | the landing's Mongo `_id` (top-level `_id` in `structure`) | `ui/{landing}/…` (blocks, store, settings), `assets/{collectionId}/…` |

Sending a domain into a `ui/*` path makes the backend parse it as an ObjectId and
return **500**. Resolve `landingId` once during Discover and reuse it.

## Discover

| Intent | Call |
|---|---|
| List sites in the project | `GET {M}/landings` |
| Read one site (incl. `_id` = `landingId`) | `GET {M}/landing/{domain}` |
| Read full structure — pages, blocks, IDs, ordering | `GET {M}/landing/{domain}/structure` |
| List pages | `GET {M}/landing/{domain}/pages` |
| Read one page | `GET {M}/landing/{domain}/pages/{pageId}` |
| Partner's projects | `GET /merchant/{merchantId}/projects/list` |
| Licensing agreements (publication gate) | `GET /merchant/merchants/{merchantId}/agreements` |

Discover is mandatory before any mutation: it supplies `landingId`, page IDs, block
IDs, and current ordering, and it is how resume avoids building a duplicate portal.

## Preflight — read the Steam title

| Intent | Call | Body |
|---|---|---|
| Pull game info from the store URL | `GET {M}/landing/{domain}/parsing` | `{ "type": "steam" \| "gplay" \| "topup" \| "sellingpage", "target": "https://store.steampowered.com/app/…" }` |

Use this to confirm the title before drafting; PC/Steam only per the skill's entry
conditions. Never substitute invented game metadata when parsing fails — return
`needs_input`.

## Draft — bootstrap the portal

Prefer the generated bootstrap over hand-assembling pages and blocks.

| Step | Call | Body |
|---|---|---|
| Create the site | `POST {M}/landing/{domain}` | `{ "name": "<Name>", "type": "topup", "colorScheme"?, "theme"? }` |
| Generate structure from the store URL | `POST {M}/landing/{domain}/structure` | `{ "type": "steam", "target": "<Steam URL>" }` |
| Or initialize a portal template | `POST {M}/landing/{domain}/portal` | single-page vs hub (multi-page) layout; theme derived from the game icon |
| Add a block-set template | `POST {M}/landing/{domain}/template` | `{ "type": "steam", "template": "home" \| "store" \| "news" }` |
| Finalize the landing type | `PUT {M}/landing/{domain}/admin/change-landing-type` | `{ "type": "topup" \| "store" \| "sellingpage" }` |

Page templates available when adding a page (from the Publisher Account builder):
`Blank`, `Store`, `Rewards` (daily rewards and reward-system blocks), `News`,
`Loyalty shop`, `Promocodes`, `Single game` (accepts a Steam link and generates the
description, images, and styling from it), `Games catalog`, `Items store`. The
portal's Rewards and News sections map onto the templates of those names; there is
**no Community template** — that section needs a Blank page and explicit blocks, so
treat it as `needs_input` rather than guessing a layout.

- `POST .../portal` only works on a landing with **no type assigned** — it returns
  **409** once a portal structure exists. On resume, read the structure instead of
  re-initializing.
- `structure` accepts `sellingpage`, `gplay`, `steam`, `store`, `topup`, `rfppage`,
  `free2play`. Omit `target` for `sellingpage`.
- Without a finalized landing type the editor gates on a domain prompt and the
  preview 404s.
- Other site-level calls: `POST {M}/landing/{domain}/duplicate`,
  `PATCH {M}/landing/{domain}` (domain rename), `DELETE {M}/landing/{domain}`
  (destructive — never without explicit approval),
  `PUT {M}/landing/{domain}/admin/change-merchant` / `change-project`.

## Draft — pages, navigation, features

| Intent | Call | Body |
|---|---|---|
| Add page | `POST {M}/landing/{domain}/pages` | `{ "name": "<1–80 chars>", "path": "/main" }` |
| Update page | `PATCH {M}/landing/{domain}/pages/{pageId}` | page fields |
| Duplicate page | `POST {M}/landing/{domain}/pages/{pageId}` | — |
| Delete page | `DELETE {M}/landing/{domain}/pages/{pageId}` | — |
| Link a page under a parent (nav) | `POST {M}/landing/{domain}/linking` | `{ "parent": "<docId>", "path": "link-example" }` |
| Remove a link | `DELETE {M}/landing/{domain}/linking` | — |
| Toggle site features | `PATCH {M}/landing/{domain}/features` | feature list |
| Page settings | `PUT {M}/ui/{landing}/page/{pageId}/savepagesettings` | — |
| Site settings | `PUT {M}/ui/{landing}/savelandingsettings` | — |

`path` accepts lowercase `a–z`, `0–9`, hyphen and slash only, max 80 chars.

## Draft — blocks

Keyed by `landingId`.

| Intent | Call | Body |
|---|---|---|
| Add block | `POST {M}/ui/{landing}/page/{pageId}/block` | `{ "block": "<module>", "index"?: <0-based> }` |
| Move block | `PUT {M}/ui/{landing}/page/{pageId}/block` | source/destination indices, 0-based |
| Delete block | `DELETE {M}/ui/{landing}/page/{pageId}/block` | block `_id` |
| Duplicate block | `POST {M}/ui/{landing}/page/{pageId}/block/duplicate` | `{ "blockId": "<_id>", "index"?: <n> }` |
| Update a block | `PUT {M}/ui/{landing}/saveblock` | block payload |
| List available components | `GET {M}/ui/{landing}/components` | — |
| Batch patch blocks / pages / site | `PATCH {M}/ui/{landing}/batch` | see below |

`block` is a **module template name**, not a block ID. Read what the project
actually offers from `GET {M}/ui/{landing}/components` or from `structure` before
adding — do not guess module names for News, Rewards, or Community. Known modules
include `lead` (hero), `newStore` (catalog grid), `federated`, `faq`, and the
default page scaffold (header, lead, description, packs, bento, gallery,
requirements, faq, footer).

The batch endpoint is the call the editor itself makes (verified live; it is not in
the published catalog). Body is a map of `requestId → change`:

```json
{"r1": {"type": "block", "id": "<blockId>",
        "patches": [{"op": "replace", "path": ["hidden"], "value": true}]}}
```

- `type` is `block` | `page` | `site`; `id` is the block `_id`, page `_id`, or the
  `landingId` (site-level).
- `path` is an Immer segment array. `op` is `add` | `remove` | `replace`.
- Protected, un-patchable: `_id`, `module`, `blockVersion`.
- `POST {M}/ui/{landing}/page/{pageId}/block/changeVersion` is an internal UI
  endpoint — do not call it.

## Draft — Web Shop wiring

| Intent | Call |
|---|---|
| Toggle a "Show in Store" component | `PUT {M}/ui/{landing}/toggleStoreComponent` — `{ "componentName": "subscriptions" }` |
| Virtual item groups | `GET {M}/ui/{landing}/store/virtualItems` |
| Goods in one group | `GET {M}/ui/{landing}/store/{groupId}` |
| Virtual currencies / packages | `GET {M}/ui/{landing}/store/virtual_currency`, `…/virtual_currency/package` |
| Game keys | `GET {M}/ui/{landing}/store/games` |
| Subscription plans | `GET {M}/ui/{landing}/subscriptionPlans` |
| Configured SKUs from PA | `GET {M}/ui/{landing}/sku` |
| Store API retry policy | `PUT {M}/landing/{domain}/store-api-retry` |

Catalog contents themselves stay with `catalog-design`; these endpoints only bind an
existing catalog into the portal.

## Draft — Launcher

| Intent | Call |
|---|---|
| Launchers available to the project | `GET {M}/ui/{landing}/launcherList` → `[{ id, name }]` |
| Create a news item | `POST /launcher/{launcherId}/merchant/{merchantId}/landing/{landingId}/constructor/news` |
| Update / delete a news item | `PUT` / `DELETE …/constructor/news/{newsId}` |
| List news (constructor) | `GET /launcher/{launcherId}/constructor/news?offset=&limit=` |
| Read one news item | `GET /launcher/{launcherId}/constructor/news/{newsId}` |
| Public news feed | `GET /public/launcher/{launcherId}/project/{projectId}/news` |

News articles are Launcher content, not page content: they live in Publisher Account
under **Distribution → Launcher → Content tiles** as content groups plus articles of
type `News`, each created in `Draft` and only visible once switched to `Publish`.
A launcher must exist before articles can be published — but it needs no games and
no Login configured for this purpose. A News section whose articles are still
`Draft` is `placeholder`, not `completed`.

Launcher **builds, installers, and downloads are not in this API.** A Launcher is
only `completed` with a real Launcher on the project, an uploaded build, a generated
installer, and a verified installer download — evidence that must come from the
Launcher product itself. Missing it means `blocked_capability`, never `completed`.

## Draft — theme and assets

Theme is a `site` patch through the batch call:

```json
{"t": {"type": "site", "id": "<landingId>",
       "patches": [{"op": "replace",
                    "path": ["theme", "mainColors", "accentColor"],
                    "value": "rgba(53,224,255,1)"}]}}
```

| Intent | Call |
|---|---|
| Theme as a CSS file | `GET {M}/landing/{domain}/theme` |
| List assets | `GET {M}/assets/{collectionId}/{collectionName}` |
| Upload asset (`multipart/form-data`, part `file`) | `POST {M}/assets/{collectionId}/{collectionName}` |
| Update / delete asset | `PATCH` / `DELETE {M}/assets/{collectionId}/{assetId}` |

`collectionId` equals the `landingId`. Upload only partner-approved assets.

## Draft — copy and localization

**Block text does not live on the block.** Blocks reference an `L:` id and the text
lives in the localization store, so patching `["values","title"]` does nothing.

| Intent | Call | Body |
|---|---|---|
| Read the whole store | `GET /localization/extract/{domain}` | — |
| Read one locale of one page | `GET /localization/{domain}/{locale}/{pageId}` | — |
| Set one string | `POST /localization/update/{domain}` | `{ "pageId", "id": "L:<uuid>", "locale": "en-US", "value": "<p>…</p>" }` |
| Set many for one locale | `POST /localization/update-many/{domain}` | `{ "locale", "perScopeValues": { "<pageId>": { "L:<id>": { "translation": "<p>…</p>" } } } }` |
| Replace the whole store | `POST /localization/load/{domain}` | full common + pages |
| Add / remove a locale | `POST` / `DELETE {M}/landing/{domain}/language` | `{ "language": "en-US" }` |

- Page strings live under `pages.<pageId>.texts."L:<id>"`, shared strings under
  `common."L:<id>"` (pass `common` as the scope key). Keep the `L:` prefix.
- In `update-many` the per-id value **must** be `{ "translation": "<html>" }`. Any
  other shape returns 200 and writes an **empty** string for that locale —
  destructive. Other locales on the same string are preserved.

## Domain, analytics, access, Login

| Intent | Call | Body |
|---|---|---|
| Attach / change / remove external domain | `POST` / `PATCH` / `DELETE {M}/landing/{domain}/domains` | `{ "domain": "shop.example.com" }` |
| Verify DNS | `GET {M}/landing/{domain}/domains/lookup` | — |
| Analytics connector | `PUT` / `DELETE {M}/landing/{domain}/applications` | `{ "type": "gtm" \| "ga", "value": "<id>" }` |
| Access restrictions | `PATCH` / `DELETE {M}/landing/{domain}/restrictions` | restriction set |
| Create a Login project | `POST /login/projects?merchantId=` | — |
| Read Login config | `GET /login/configuration/{loginId}` | — |
| Login widget settings | `POST` / `GET` / `PUT /login/widget-customization/{loginId}` | — |
| Publish widget settings | `POST /login/widget-customization/{loginId}/publish` | — |

Login *behaviour* — auth methods, JWT validation, account binding — stays with
`login-setup`. Sign-in succeeding is not binding succeeding; both must be verified.

## Verify and preview

| Intent | Call |
|---|---|
| Enable public preview (returns the token) | `GET /landing/{domain}/public-preview/enable-preview` |
| Get the public preview link | `GET /landing/{domain}/public-preview/public-preview-link` |
| Disable public preview | `GET /landing/{domain}/public-preview/disable-preview` |
| Render one page directly | `GET /preview/{domain}/{page}/{locale}` (optional `?version=`) |
| Readiness check before publish | `GET {M}/landing/{domain}/check` → `{ "checkSku": true }` |

Re-read `structure` after every change group; a mutation response alone is not
evidence. `check` gates on required fields such as a non-empty SKU.

## Publish and rollback

| Intent | Call |
|---|---|
| Publish the site | `POST {M}/landing/{domain}/publication` |
| List archived versions | `GET {M}/landing/{domain}/versions` |
| Apply an archived version (rollback) | `PUT {M}/landing/{domain}/versions/{versionId}` |

**Publication is per-page, not whole-site.** The builder publishes a *selection* of
pages — which is what the deployed `check` and `publication` calls mean by
`draftPagesIds`. Resolve the page IDs from `structure` and pass the ones being
published; publishing "the portal" without a selection is what produces a `400`.

Preconditions, all checkable before the call:

- No empty sections anywhere in the builder.
- The Xsolla licensing agreement is signed — `GET /merchant/merchants/{merchantId}/agreements`.
- The main page is already published, or included in this same selection. **Child
  pages cannot be published before the main page**, so order the selection
  accordingly or the call fails.

Publication returns `domain`, `languages`, `last_published`, and `user_published`.
Publishing still requires explicit partner approval, and `published_verified` still
requires the public URL to serve the expected version and routes — a `200` from
`publication` is a receipt, not proof the live site is correct.

## Known API issues

Confirmed against a live portal, 2026-08-14:

- The public preview URL can return **403** while the token response reports the
  preview as enabled. The CLI reads `public-preview/public-preview-last-token`,
  which is not part of the published API; use `public-preview-link` and fall back to
  a structure read-back as Verify evidence. Report a persistent 403 as `failed` with
  the response — never as `completed`.
- The readiness check returns **400** when `draftPagesIds` is missing. This is not a
  capability gap: the parameter is the page selection described under Publish, and
  the published contract simply omits it. Send the selected page IDs. The exact
  field shape is **unverified** — it is in no spec available here, only in the
  deployed endpoint and the builder UI — so confirm it against a live call before
  relying on it, and treat a still-failing check as `failed`, not `completed`.

## Failure → status mapping

| Response | Status | Action |
|---|---|---|
| `401` / `403` | `needs_access` | preserve the ledger, reauthenticate, re-read state, resume |
| `404` on create | `needs_human` | Shop Builder is not enabled for the project; the partner enables it in Publisher Account |
| `409` from `POST .../portal` | — | the portal is already initialized: read the structure and resume instead of recreating |
| `500` from a `ui/*` path | — | wrong key: a domain was sent where `landingId` is required. Fix and retry; not a capability block |
| Launcher build / installer / download | `blocked_capability` | not exposed by this API |
