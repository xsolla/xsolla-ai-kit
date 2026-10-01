# Xsolla Game Web Portal — Shop Builder reference

The portal itself (sites, pages, blocks, theme, copy) is Shop Builder. This file lists the
calls the agent makes for Steps 3–8 of `SKILL.md`, and the steps it hands to the partner.
Catalog, Login, and checkout stay delegated — see `SKILL.md`.

## Context

- **Base URL:** `https://sitebuilder.xsolla.com/api`
- **Auth:** the Publisher Account session from `xsolla auth login` — the only source.
  Every `xsolla shopbuilder` command derives the session from that login, and
  `scripts/portal_template.py` derives it the same way. A session or token is never
  passed by hand or copied out of a browser. A missing, stale, or unauthorized session
  returns `401/403` → `needs_access`: run `xsolla auth login` again and resume. This is
  *not* `XSOLLA_PROJECT_API_KEY`.
- **Safe target:** before the first write, `scripts/preflight.py` must pass — the CLI points
  at the intended merchant and project, and that project is a sandbox or is listed in the
  approved test-project allowlist. `portal_template.py` runs the same check itself.
- **Path shorthand below:** `{M}` = `/merchant/{merchantId}/project/{projectId}`

### Two different keys — the top cause of hard failures

| Key | What it is | Used by |
|---|---|---|
| `domain` | the site's domain label, e.g. `voidwall` → `voidwall.xsolla.site` (the CLI's `--slug`) | `landing/{domain}/…`, localization |
| `landingId` | the landing's `_id` (top-level `_id` in `get-structure`) | blocks, assets, theme patches |

Sending a domain where a `landingId` is required returns **500**. Resolve `landingId` once
during Discover and reuse it.

## Discover

| Intent | Command |
|---|---|
| List sites in the project | `xsolla shopbuilder list-websites` |
| Read one site (incl. `_id` = `landingId`) | `get-landing` |
| Read full structure — pages, blocks, IDs, ordering | `get-structure` |
| List pages / read one page | `list-pages` / `get-page` |
| Partner's projects | `xsolla publisher list-projects` |
| Licensing agreements (reported, not acted on) | `list-agreements` |

Discover is mandatory before any mutation: it supplies `landingId`, page IDs, block IDs,
and current ordering, and it is how resume avoids building a duplicate portal.

## Draft — bootstrap the portal

| Step | How | Call |
|---|---|---|
| Create the site | `create-website` | `POST {M}/landing/{domain}` |
| Initialize a portal template | `portal_template.py portal` | `POST {M}/landing/{domain}/portal` — `{ "IsSinglePage", "TargetUrl", "LauncherId", "GameDescription" }` |
| Add a block-set template | `portal_template.py template` | `POST {M}/landing/{domain}/template` — `{ "type": "steam", "template": "home" \| "store" \| "news" }` |
| Finalize the landing type | `set-landing-type` | `PUT {M}/landing/{domain}/admin/change-landing-type` |

- Run `create-website`, then `portal` on that new landing. `portal` only works on a landing
  with **no type assigned** and returns **409** once a portal structure exists — on resume,
  read the structure instead of re-initializing. `create-website` asks for type `topup`; if
  the new landing comes back already typed, `portal` returns 409 on a site that has no portal
  yet — report `failed` with the response and build the pages with `add-page` and `add-block`.
- The `portal` body has four fields, all required and capitalized exactly like this:
  `IsSinglePage` (`--single-page` / `--hub`), `TargetUrl` (`--store-url`), `LauncherId`
  (`--launcher-id`) and `GameDescription` (`--game-description`). Lower-case keys are
  ignored and rejected with a `400`.
- **With an empty store URL and launcher, `portal` returns `500`** and creates nothing
  (seen live, for both layouts). Report the step `failed` with the response and build the
  pages with `add-page` and `add-block` instead. Never put another game's store URL in the
  request, and never guess further fields.
- Page templates in the Publisher Account builder include `Blank`, `Store`, `Rewards`,
  `News`, `Loyalty shop`, `Promocodes`, `Single game`, `Games catalog`, and `Items store`.
  There is **no Community template** — that section needs a Blank page and explicit blocks,
  so treat it as `needs_input` rather than guessing a layout.

## Draft — pages and blocks

| Intent | Command |
|---|---|
| Add a page | `add-page` — `--name` (1–80 chars), `--path` (lowercase `a–z`, `0–9`, hyphen, slash; max 80) |
| Add / move / delete / duplicate a block | `add-block` / `move-block` / `delete-block` / `duplicate-block` |
| Patch a block, page, or site value — including the theme | `update-block` |

`add-block` takes a **module template name**, not a block ID. Read what the project
actually uses from `get-structure` before adding — do not guess module names for News,
Rewards, or Community. Known modules include `lead` (hero), `newStore` (catalog grid),
`federated`, `faq`, and the default page scaffold (header, lead, description, packs, bento,
gallery, requirements, faq, footer).

`update-block` sends a map of `requestId → change`:

```json
{"r1": {"type": "block", "id": "<blockId>",
        "patches": [{"op": "replace", "path": ["hidden"], "value": true}]}}
```

- `type` is `block` | `page` | `site`; `id` is the block `_id`, page `_id`, or the
  `landingId` (site-level).
- `path` is a segment array. `op` is `add` | `remove` | `replace`.
- Protected, never patched: `_id`, `module`, `blockVersion`.
- **Never patch block text.** Patching a text value such as `["values","title"]` deletes the
  string and all its translations, and still returns `200`. Copy goes through
  `update-localization` — see below.

The theme is a `site` patch:

```json
{"t": {"type": "site", "id": "<landingId>",
       "patches": [{"op": "replace",
                    "path": ["theme", "mainColors", "accentColor"],
                    "value": "rgba(53,224,255,1)"}]}}
```

## Draft — assets

| Intent | Command |
|---|---|
| List assets | `list-assets` |
| Upload an asset | `upload-asset` |
| Delete an asset | `delete-asset` |

Upload only partner-approved assets.

## Draft — copy and localization

Block text lives in the localization store, not on the block: blocks reference an `L:` id.

| Intent | Command | Body |
|---|---|---|
| Read the whole store | `get-localization` | — |
| Set one string | `update-localization` | `{ "pageId", "id": "L:<uuid>", "locale": "en-US", "value": "<p>…</p>" }` |
| Set many for one locale | `update-many-localization` | `{ "locale", "perScopeValues": { "<pageId>": { "L:<id>": { "translation": "<p>…</p>" } } } }` |
| Add / remove a locale | `add-language` / `delete-language` | `{ "language": "en-US" }` |

- Page strings live under `pages.<pageId>.texts."L:<id>"`, shared strings under
  `common."L:<id>"` (pass `common` as the scope key). Keep the `L:` prefix.
- In `update-many-localization` the per-id value **must** be `{ "translation": "<html>" }`.
  Any other shape returns 200 and writes an **empty** string for that locale — destructive.
  Other locales on the same string are preserved.

## Analytics and access

| Intent | Command |
|---|---|
| Analytics connector (`gtm` or `ga`) | `add-connector` / `delete-connector` |
| Access restrictions | `update-restrictions` / `delete-restrictions` |

Login itself — the project, auth methods, JWT validation, account binding, and widget
styling — stays with `login-setup` and `login-styling`. Sign-in succeeding is not binding
succeeding; both must be verified.

## Verify — read-back only

Re-read the structure (`get-structure`) and localization (`get-localization`) after every
change group and compare them with the confirmed plan; a mutation response alone is not
evidence. That read-back is the agent's whole Verify step.

## Done by the partner in Publisher Account

The agent never does these. Each one is reported as `needs_human`, with what to do.

**Human only — never the agent:**

- Run the readiness check and open the preview.
- Publish. Publication is per page: the main page must already be published or be in the
  same selection, no section may be empty, and the Xsolla licensing agreement must be
  signed. A successful publication is a receipt, not proof — the partner confirms the public
  URL serves the expected version and routes, and that Login and the Web Shop work.
- Apply or roll back to a saved version.
- Delete a site.
- Attach, change, or verify an external domain.
- Publish Login widget settings, and publish News articles (switch them from `Draft`).

**Not yet available from the CLI — the partner does them in the builder:**

- Rename, duplicate, or delete a page; link a page under a parent in the navigation.
- Page and site settings, and site feature toggles.
- Show a store component (such as subscriptions) on the Web Shop.
- Launcher news articles. The News section is `placeholder` while its articles are `Draft`.
- Update an existing asset; rename the domain; move the site to another project.

## Launcher

A Launcher is only `completed` with a real Launcher on the project, an uploaded build, a
generated installer, and a verified installer download — evidence that must come from the
Launcher product itself. Builds, installers, and downloads are not reachable from here, so
a missing piece is `blocked_capability`, never `completed`.

## Failure → status mapping

| Response | Status | Action |
|---|---|---|
| `401` / `403` | `needs_access` | preserve the ledger, run `xsolla auth login`, re-read state, resume |
| `404` on create | `needs_human` | Shop Builder is not enabled for the project; the partner enables it in Publisher Account |
| `409` from `portal` | — | the portal is already initialized: read the structure and resume instead of recreating |
| `500` with a `domain` where a `landingId` belongs | — | wrong key: fix and retry; not a capability block |
| Launcher build / installer / download | `blocked_capability` | not reachable from here |
