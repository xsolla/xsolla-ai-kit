# Xsolla Game Web Portal — Shop Builder API reference

The portal itself (sites, pages, blocks, theme, copy) is Shop Builder. This file maps
every Shop Builder call the portal touches to how the agent makes it, for Steps 3–8 of
`SKILL.md`. Catalog, Login, and checkout stay delegated — see `SKILL.md`.

## Context

- **Base URL:** `https://sitebuilder.xsolla.com/api`
- **Auth:** the Publisher Account session from `xsolla auth login` — the only source.
  Every `xsolla shopbuilder` command derives the session from that login, and
  `scripts/portal_template.py` derives it the same way. A session or token is never
  passed by hand or copied out of a browser. A missing, stale, or unauthorized session
  returns `401/403` → `needs_access`: run `xsolla auth login` again and resume. This is
  *not* `XSOLLA_PROJECT_API_KEY`.
- **Path shorthand below:** `{M}` = `/merchant/{merchantId}/project/{projectId}`

### How each call is made

| How | Meaning |
|---|---|
| `command` | An `xsolla shopbuilder` command (or the named `xsolla` command) |
| `portal_template.py` | No CLI command yet; the pre-written script, with the same login |
| `needs_human` | No CLI command and no script: the agent tells the partner what to do in Publisher Account and records the step |
| **human only** | The agent never makes this call, even where a command exists |
| not used | Not part of the portal flow |

### Two different keys — the top cause of hard failures

| Key | What it is | Used by |
|---|---|---|
| `domain` | the site's domain label, e.g. `voidwall` → `voidwall.xsolla.site` (the CLI's `--slug`) | `landing/{domain}/…`, localization |
| `landingId` | the landing's Mongo `_id` (top-level `_id` in `structure`) | `ui/{landing}/…` (blocks, store, settings), `assets/{landingId}/…` |

Sending a domain into a `ui/*` path makes the backend parse it as an ObjectId and
return **500**. Resolve `landingId` once during Discover and reuse it.

## Discover

| Intent | Call | How |
|---|---|---|
| List sites in the project | `GET {M}/landings` | `list-websites` |
| Read one site (incl. `_id` = `landingId`) | `GET {M}/landing/{domain}` | `get-landing` |
| Read full structure — pages, blocks, IDs, ordering | `GET {M}/landing/{domain}/structure` | `get-structure` |
| List pages | `GET {M}/landing/{domain}/pages` | `list-pages` |
| Read one page | `GET {M}/landing/{domain}/pages/{pageId}` | `get-page` |
| Partner's projects | `GET /merchant/{merchantId}/projects/list` | `xsolla publisher list-projects` |
| Licensing agreements (reported, not acted on) | `GET /merchant/merchants/{merchantId}/agreements` | `list-agreements` |

Discover is mandatory before any mutation: it supplies `landingId`, page IDs, block
IDs, and current ordering, and it is how resume avoids building a duplicate portal.

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
| Duplicate the site | `POST {M}/landing/{domain}/duplicate` | not used | — |
| Rename the domain | `PATCH {M}/landing/{domain}` | `needs_human` | — |
| Move the site to another merchant or project | `PUT {M}/landing/{domain}/admin/change-merchant` / `change-project` | `needs_human` | — |
| Delete the site | `DELETE {M}/landing/{domain}` | **human only** | — |
| Read game info from a store page | `GET {M}/landing/{domain}/parsing` | not used — rejects Steam and Google Play links in live tests | — |
| Generate structure from a store page | `POST {M}/landing/{domain}/structure` | not used — depends on the same parsing | — |

The `portal` call's request body is not in the published API contract: only that it
chooses a single-page or hub layout. `portal_template.py` sends that choice as
`isSinglePage`. If the call returns `400`, report `failed` with the response and build
the pages with `add-page` and `add-block` instead — never guess further fields.

Page templates available when adding a page (from the Publisher Account builder):
`Blank`, `Store`, `Rewards` (daily rewards and reward-system blocks), `News`,
`Loyalty shop`, `Promocodes`, `Single game`, `Games catalog`, `Items store`. The
portal's Rewards and News sections map onto the templates of those names; there is
**no Community template** — that section needs a Blank page and explicit blocks, so
treat it as `needs_input` rather than guessing a layout.

- `POST .../portal` only works on a landing with **no type assigned** — it returns
  **409** once a portal structure exists. On resume, read the structure instead of
  re-initializing.
- Without a finalized landing type the editor gates on a domain prompt.

## Draft — pages, navigation, features

| Intent | Call | How | Body |
|---|---|---|---|
| Add page | `POST {M}/landing/{domain}/pages` | `add-page` | `{ "name": "<1–80 chars>", "path": "/main" }` |
| Update page | `PATCH {M}/landing/{domain}/pages/{pageId}` | `needs_human` | page fields |
| Duplicate page | `POST {M}/landing/{domain}/pages/{pageId}` | `needs_human` | — |
| Delete page | `DELETE {M}/landing/{domain}/pages/{pageId}` | `needs_human` | — |
| Link a page under a parent (nav) | `POST {M}/landing/{domain}/linking` | `needs_human` | `{ "parent": "<docId>", "path": "link-example" }` |
| Remove a link | `DELETE {M}/landing/{domain}/linking` | `needs_human` | — |
| Toggle site features | `PATCH {M}/landing/{domain}/features` | `needs_human` | feature list |
| Page settings | `PUT {M}/ui/{landing}/page/{pageId}/savepagesettings` | `needs_human` | — |
| Site settings | `PUT {M}/ui/{landing}/savelandingsettings` | `needs_human` | — |

`path` accepts lowercase `a–z`, `0–9`, hyphen and slash only, max 80 chars.

## Draft — blocks

Keyed by `landingId`.

| Intent | Call | How | Body |
|---|---|---|---|
| Add block | `POST {M}/ui/{landing}/page/{pageId}/block` | `add-block` | `{ "block": "<module>", "index"?: <0-based> }` |
| Move block | `PUT {M}/ui/{landing}/page/{pageId}/block` | `move-block` | source/destination indices, 0-based |
| Delete block | `DELETE {M}/ui/{landing}/page/{pageId}/block` | `delete-block` | block `_id` |
| Duplicate block | `POST {M}/ui/{landing}/page/{pageId}/block/duplicate` | `duplicate-block` | `{ "blockId": "<_id>", "index"?: <n> }` |
| Batch patch blocks / pages / site | `PATCH {M}/ui/{landing}/batch` | `update-block` | see below |
| Update a block (legacy save) | `PUT {M}/ui/{landing}/saveblock` | not used — `update-block` covers it | block payload |
| List available components | `GET {M}/ui/{landing}/components` | not used — read modules from `get-structure` | — |

`block` is a **module template name**, not a block ID. Read what the project
actually offers from `get-structure` before adding — do not guess module names for
News, Rewards, or Community. Known modules include `lead` (hero), `newStore` (catalog
grid), `federated`, `faq`, and the default page scaffold (header, lead, description,
packs, bento, gallery, requirements, faq, footer).

The batch endpoint is the call the editor itself makes, and it is what `update-block`
sends. Body is a map of `requestId → change`:

```json
{"r1": {"type": "block", "id": "<blockId>",
        "patches": [{"op": "replace", "path": ["hidden"], "value": true}]}}
```

- `type` is `block` | `page` | `site`; `id` is the block `_id`, page `_id`, or the
  `landingId` (site-level).
- `path` is an Immer segment array. `op` is `add` | `remove` | `replace`.
- Protected, un-patchable: `_id`, `module`, `blockVersion`.
- `POST {M}/ui/{landing}/page/{pageId}/block/changeVersion` is an internal UI
  endpoint — never call it.

## Draft — Web Shop wiring

Catalog contents stay with `catalog-design`, which verifies the SKUs it creates; these
calls only bind an existing catalog into the portal.

| Intent | Call | How |
|---|---|---|
| Toggle a "Show in Store" component | `PUT {M}/ui/{landing}/toggleStoreComponent` — `{ "componentName": "subscriptions" }` | `needs_human` |
| Store API retry policy | `PUT {M}/landing/{domain}/store-api-retry` | `needs_human` |
| Virtual item groups, goods in a group, currencies and packages, game keys, subscription plans, configured SKUs | `GET {M}/ui/{landing}/store/…`, `…/subscriptionPlans`, `…/sku` | not used — `catalog-design` reads the catalog |

## Draft — Launcher

| Intent | Call | How |
|---|---|---|
| Launchers available to the project | `GET {M}/ui/{landing}/launcherList` → `[{ id, name }]` | `needs_human` |
| Create, update, or delete a news item | `POST` / `PUT` / `DELETE /launcher/{launcherId}/merchant/{merchantId}/landing/{landingId}/constructor/news[/{newsId}]` | `needs_human` |
| List or read news | `GET /launcher/{launcherId}/constructor/news[/{newsId}]` | `needs_human` |
| Public news feed | `GET /public/launcher/{launcherId}/project/{projectId}/news` | not used |

News articles are Launcher content, not page content: they live in Publisher Account
under **Distribution → Launcher → Content tiles** as content groups plus articles of
type `News`, each created in `Draft` and only visible once switched to `Publish`.
A launcher must exist before articles can be published — but it needs no games and
no Login configured for this purpose. A News section whose articles are still `Draft`
is `placeholder`, not `completed`; switching an article to `Publish` is the partner's.

Launcher **builds, installers, and downloads are not in this API.** A Launcher is
only `completed` with a real Launcher on the project, an uploaded build, a generated
installer, and a verified installer download — evidence that must come from the
Launcher product itself. Missing it means `blocked_capability`, never `completed`.

## Draft — theme and assets

Theme is a `site` patch through `update-block`:

```json
{"t": {"type": "site", "id": "<landingId>",
       "patches": [{"op": "replace",
                    "path": ["theme", "mainColors", "accentColor"],
                    "value": "rgba(53,224,255,1)"}]}}
```

| Intent | Call | How |
|---|---|---|
| Theme | `PATCH {M}/ui/{landing}/batch` (`site` patch) | `update-block` |
| Theme as a CSS file | `GET {M}/landing/{domain}/theme` | not used — read the theme from `get-structure` |
| List assets | `GET {M}/assets/{landingId}/site` | `list-assets` |
| Upload asset (`multipart/form-data`, part `file`) | `POST {M}/assets/{landingId}/site` | `upload-asset` |
| Delete asset | `DELETE {M}/assets/{landingId}/{assetId}` | `delete-asset` |
| Update asset | `PATCH {M}/assets/{landingId}/{assetId}` | `needs_human` |

Upload only partner-approved assets.

## Draft — copy and localization

**Block text does not live on the block.** Blocks reference an `L:` id and the text
lives in the localization store, so patching `["values","title"]` does nothing.

| Intent | Call | How | Body |
|---|---|---|---|
| Read the whole store | `GET /localization/extract/{domain}` | `get-localization` | — |
| Set one string | `POST /localization/update/{domain}` | `update-localization` | `{ "pageId", "id": "L:<uuid>", "locale": "en-US", "value": "<p>…</p>" }` |
| Set many for one locale | `POST /localization/update-many/{domain}` | `update-many-localization` | `{ "locale", "perScopeValues": { "<pageId>": { "L:<id>": { "translation": "<p>…</p>" } } } }` |
| Add / remove a locale | `POST` / `DELETE {M}/landing/{domain}/language` | `add-language` / `delete-language` | `{ "language": "en-US" }` |
| Read one locale of one page | `GET /localization/{domain}/{locale}/{pageId}` | not used — `get-localization` reads it all | — |
| Replace the whole store | `POST /localization/load/{domain}` | not used — overwrites every string | full common + pages |

- Page strings live under `pages.<pageId>.texts."L:<id>"`, shared strings under
  `common."L:<id>"` (pass `common` as the scope key). Keep the `L:` prefix.
- In `update-many` the per-id value **must** be `{ "translation": "<html>" }`. Any
  other shape returns 200 and writes an **empty** string for that locale —
  destructive. Other locales on the same string are preserved.

## Analytics, access, Login

| Intent | Call | How | Body |
|---|---|---|---|
| Analytics connector | `PUT` / `DELETE {M}/landing/{domain}/applications` | `add-connector` / `delete-connector` | `{ "type": "gtm" \| "ga", "value": "<id>" }` |
| Access restrictions | `PATCH` / `DELETE {M}/landing/{domain}/restrictions` | `update-restrictions` / `delete-restrictions` | restriction set |
| Create a Login project, read its config, edit widget settings | `/login/projects`, `/login/configuration/{loginId}`, `/login/widget-customization/{loginId}` | delegated — `login-setup` and `login-styling` | — |

Login *behaviour* — auth methods, JWT validation, account binding — stays with
`login-setup`. Sign-in succeeding is not binding succeeding; both must be verified.

## Verify — read-back only

Re-read `structure` (`get-structure`) and localization (`get-localization`) after every
change group and compare them with the confirmed plan; a mutation response alone is not
evidence. That read-back is the agent's whole Verify step.

## Human only

The agent never makes these calls, even where a CLI command exists. They are listed so
the handoff can tell the partner what to do in Publisher Account, and so their
responses can be read if the partner shares them.

| Intent | Call |
|---|---|
| Readiness check before publish | `{M}/landing/{domain}/check` |
| Enable / disable public preview, get the preview link | `/landing/{domain}/public-preview/…` |
| Render one page directly | `GET /preview/{domain}/{page}/{locale}` |
| Publish | `POST {M}/landing/{domain}/publication` |
| List archived versions | `GET {M}/landing/{domain}/versions` |
| Apply an archived version (rollback) | `PUT {M}/landing/{domain}/version/{versionId}` |
| Delete the site | `DELETE {M}/landing/{domain}` |
| Attach, change, remove, or verify an external domain | `{M}/landing/{domain}/domains`, `…/domains/lookup` |
| Publish Login widget settings | `POST /login/widget-customization/{loginId}/publish` |

What the handoff tells the partner about publication:

- Publication is **per page**. The main page must already be published or be in the
  same selection — child pages cannot go live before it.
- No section may be empty, and the Xsolla licensing agreement must be signed.
- A successful publication is a receipt, not proof: the partner confirms the public
  URL serves the expected version and routes, and that Login and the Web Shop work.

Open questions about these endpoints — the exact meaning of the page-selection field
(`draftPagesIds`), whether the readiness check is a `GET` or a `POST` with a body, and
how a non-admin user gets a preview — are for the Shop Builder team. They do not affect
the agent, which calls none of them.

## Failure → status mapping

| Response | Status | Action |
|---|---|---|
| `401` / `403` | `needs_access` | preserve the ledger, run `xsolla auth login`, re-read state, resume |
| `404` on create | `needs_human` | Shop Builder is not enabled for the project; the partner enables it in Publisher Account |
| `409` from `POST .../portal` | — | the portal is already initialized: read the structure and resume instead of recreating |
| `500` from a `ui/*` path | — | wrong key: a domain was sent where `landingId` is required. Fix and retry; not a capability block |
| Launcher build / installer / download | `blocked_capability` | not exposed by this API |
