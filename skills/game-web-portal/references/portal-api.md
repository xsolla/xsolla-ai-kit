# Xsolla Game Web Portal — Shop Builder API reference

The portal itself (sites, pages, blocks, theme, copy, domain) is Shop Builder. This
file is the Shop Builder surface for Steps 3–8 of `SKILL.md`. Catalog, Login, and
checkout stay delegated — see `SKILL.md`.

## Context

- **Base URL:** `https://sitebuilder.xsolla.com/api`
- **Auth:** the Publisher Account session. `xsolla auth login` once; the CLI derives
  the session from that login for every `xsolla shopbuilder` command, and
  `scripts/portal_template.py` derives it the same way. `XSOLLA_SHOPBUILDER_SESSION`
  overrides it when set. A missing, stale, or unauthorized session returns
  `401/403` → `needs_access`. This is *not* `XSOLLA_PROJECT_API_KEY`, and it is never
  copied out of a browser.
- **Path shorthand below:** `{M}` = `/merchant/{merchantId}/project/{projectId}`

## Who calls what

| Intent | How |
|---|---|
| Read sites, structure, pages, localization, assets, versions | `xsolla shopbuilder list-websites`, `get-landing`, `get-structure`, `list-pages`, `get-page`, `get-localization`, `list-assets`, `list-versions` |
| Create the site, set its type | `create-website`, `set-landing-type` |
| Initialize the portal template, add a block-set template | `scripts/portal_template.py portal` / `template` — no CLI command yet |
| Pages, blocks, block order | `add-page`, `add-block`, `move-block`, `delete-block`, `duplicate-block` |
| Block, page, and site patches, including the theme | `update-block` (the batch patch below) |
| Assets | `upload-asset`, `delete-asset` |
| Locales and copy | `add-language`, `update-localization`, `update-many-localization` |
| Readiness check, preview, publication, rollback | **The human, in Publisher Account.** The agent never calls these |

Everything below documents the endpoints behind those commands, so read-backs and
error responses can be interpreted.

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

## Store-page parsing — not used

`GET {M}/landing/{domain}/parsing` takes `{ "type": "steam" | "gplay" | "topup" |
"sellingpage", "target": "<store URL>" }`, but in live tests it rejects `steam` and
`gplay` and returns only title, developer, and icon for `sellingpage`. The portal
therefore takes its metadata and assets from the partner. A supplied Steam URL is
recorded as a reference; it never substitutes for approved content.

## Draft — bootstrap the portal

Create the site, initialize the portal template on it while it has no type, then add
the required pages and blocks and populate them only with partner-approved metadata
and assets.

| Step | Call | How | Body |
|---|---|---|---|
| Create the site | `POST {M}/landing/{domain}` | `create-website` | `{ "name": "<Name>", "type": "topup", "colorScheme"?, "theme"? }` |
| Initialize a portal template | `POST {M}/landing/{domain}/portal` | `portal_template.py portal` | single-page vs hub (multi-page) layout; theme derived from the game icon |
| Add a block-set template | `POST {M}/landing/{domain}/template` | `portal_template.py template` | `{ "type": "steam", "template": "home" \| "store" \| "news" }` |
| Finalize the landing type | `PUT {M}/landing/{domain}/admin/change-landing-type` | `set-landing-type` | `{ "type": "topup" \| "store" \| "sellingpage" }` |

The `portal` call's request body is not in the published API contract: only that it
chooses a single-page or hub layout. `portal_template.py` sends that choice as
`isSinglePage`. If the call returns `400`, report `failed` with the response and build
the pages with `add-page` and `add-block` instead — never guess further fields.

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
the published catalog), and it is what `xsolla shopbuilder update-block` sends. Body is
a map of `requestId → change`:

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
`Draft` is `placeholder`, not `completed`. Switching an article to `Publish` makes it
public, so that is the partner's step: the agent creates articles in `Draft` only.

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
| Attach / change / remove external domain — **human only**, part of going live | `POST` / `PATCH` / `DELETE {M}/landing/{domain}/domains` | `{ "domain": "shop.example.com" }` |
| Verify DNS — human only | `GET {M}/landing/{domain}/domains/lookup` | — |
| Analytics connector | `PUT` / `DELETE {M}/landing/{domain}/applications` | `{ "type": "gtm" \| "ga", "value": "<id>" }` |
| Access restrictions | `PATCH` / `DELETE {M}/landing/{domain}/restrictions` | restriction set |
| Create a Login project | `POST /login/projects?merchantId=` | — |
| Read Login config | `GET /login/configuration/{loginId}` | — |
| Login widget settings | `POST` / `GET` / `PUT /login/widget-customization/{loginId}` | — |
| Publish widget settings — owned by `login-styling`, not called here | `POST /login/widget-customization/{loginId}/publish` | — |

Login *behaviour* — auth methods, JWT validation, account binding — stays with
`login-setup`. Sign-in succeeding is not binding succeeding; both must be verified.

## Verify — read-back only

Re-read `structure` (`get-structure`) and localization (`get-localization`) after every
change group and compare them with the confirmed plan; a mutation response alone is not
evidence. That read-back is the agent's whole Verify step.

## Human only — readiness, preview, publication, rollback

The agent never calls these. They are listed so the handoff can tell the partner what
to do in Publisher Account, and so their responses can be read if the partner shares
them.

| Intent | Endpoint |
|---|---|
| Readiness check before publish | `{M}/landing/{domain}/check` |
| Enable / disable public preview, get the preview link | `/landing/{domain}/public-preview/…` |
| Render one page directly | `GET /preview/{domain}/{page}/{locale}` |
| Publish | `POST {M}/landing/{domain}/publication` |
| List archived versions | `GET {M}/landing/{domain}/versions` (the agent may read this for the backup) |
| Apply an archived version (rollback) | `PUT {M}/landing/{domain}/versions/{versionId}` |

What the handoff tells the partner about publication:

- Publication is **per page**. The main page must already be published or be in the
  same selection — child pages cannot go live before it.
- No section may be empty, and the Xsolla licensing agreement must be signed
  (`GET /merchant/merchants/{merchantId}/agreements` — a read the agent may make to
  report it).
- A successful publication is a receipt, not proof: the partner confirms the public
  URL serves the expected version and routes, and that Login and the Web Shop work.

Open questions about these endpoints — the exact meaning of the page-selection field
(`draftPagesIds`), whether the readiness check is a `GET` or a `POST` with a body, and
how a non-admin user gets a preview — are for the Shop Builder team. They do not affect
the agent, which calls none of them.

## Failure → status mapping

| Response | Status | Action |
|---|---|---|
| `401` / `403` | `needs_access` | preserve the ledger, reauthenticate, re-read state, resume |
| `404` on create | `needs_human` | Shop Builder is not enabled for the project; the partner enables it in Publisher Account |
| `409` from `POST .../portal` | — | the portal is already initialized: read the structure and resume instead of recreating |
| `500` from a `ui/*` path | — | wrong key: a domain was sent where `landingId` is required. Fix and retry; not a capability block |
| Launcher build / installer / download | `blocked_capability` | not exposed by this API |
