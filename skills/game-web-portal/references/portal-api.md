# Xsolla Game Web Portal — Shop Builder reference

The portal itself (sites, pages, blocks, theme, copy) is Shop Builder. This file lists the
calls the agent makes for Steps 3–8 of `SKILL.md`, and the steps it hands to the partner.
Catalog, Login, and checkout stay delegated — see `SKILL.md`.

## Context

- **Auth:** the Publisher Account session from `xsolla auth login` — the only source.
  Every `xsolla shopbuilder` command derives the session from that login. A session or
  token is never passed by hand or copied out of a browser. A missing, stale, or
  unauthorized session returns `401/403` → `needs_access`: run `xsolla auth login` again
  and resume. This is *not* `XSOLLA_PROJECT_API_KEY`.
- **Safe target:** before the first write, `scripts/preflight.py` must pass — the CLI points
  at the intended merchant and project, and that project is a sandbox or is listed in the
  approved test-project allowlist.

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

## Draft — create the portal

| Step | Command |
|---|---|
| Create the site | `create-website` |
| Finalize the landing type | `set-landing-type --type topup` |
| Add each section's page | `add-page` |
| Add each section's block after the `header` | `add-block --index 1` |
| Remove the seeded blocks the section doesn't keep | `delete-block --force` |

Portal and block-set templates are not used: they have no CLI command, and `portal` returned 500.

### Portal layout

On a `topup` landing, `add-page` seeds every page with the same game-sales scaffold: `header`,
`leadGameSales`, `description`, `packs` ×3, `bento-grid` ×3, `gallery`, `requirements`, `faq`,
`footer`. Each section gets its own block right after the `header` (`add-block --index 1`), then
`delete-block` removes the seeded blocks the section doesn't keep. Module names come from the
`shop-builder-assembly` [block catalog](../../shop-builder-assembly/references/block-catalog.md).

| Section | Path | Section block | Final page |
|---|---|---|---|
| Home | `/main` | none | the seeded scaffold, kept whole as the game page |
| News | `/news` | `news` | `header`, `news`, `footer` |
| Rewards | `/rewards` | `rewards` | `header`, `rewards`, `footer` |
| Web Shop | `/store` | `newStore` | `header`, `newStore`, `faq`, `footer` |
| Community | `/community` | `embed` | `header`, `embed`, `footer` |
| Launcher (optional) | `/launcher` | only with a real Launcher (see below) | — |

The News block shows Launcher news articles only.

Remove seeded blocks only on a page the agent created: in this run, or in an earlier run that the
ledger records for the same merchant, project and environment. Re-read the page first; if it holds
anything that isn't from the seed or the confirmed plan, stop and ask. Remove only as the confirmed
plan lists: for each such page, the seeded modules it drops. `delete-block` takes each block's
`_id` (`--blockid`), read from `get-structure`; pass `--force`, since the confirmed plan is the
confirmation and the CLI's own prompt refuses without a terminal. Never delete a block on any other
page.

On resume, compare `get-structure` with this layout and add only what is missing; never add a
page whose path already exists.

## Draft — pages and blocks

| Intent | Command |
|---|---|
| Add a page | `add-page` — `--name` (1–80 chars), `--path` (lowercase `a–z`, `0–9`, hyphen, slash; max 80) |
| Add / move / delete / duplicate a block | `add-block` / `move-block` / `delete-block` / `duplicate-block` |
| Patch a block, page, or site value — including the theme | `update-block` |

`add-block` takes a **module template name** (`--block`), not a block ID, plus the landing
`_id`, the page `_id`, and always `--index`: without it the block goes to the top of the page,
above the `header`. Use only the modules in the layout above.

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
- Save a version, apply one, or roll back to one.
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
| `500` with a `domain` where a `landingId` belongs | — | wrong key: fix and retry; not a capability block |
| `429` while the CLI bootstraps the session | — | rate limited: wait a minute and retry; never set a session by hand |
| Launcher build / installer / download | `blocked_capability` | not reachable from here |
