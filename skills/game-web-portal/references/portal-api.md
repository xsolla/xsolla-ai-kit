# Xsolla Game Web Portal — Shop Builder reference

The portal itself (sites, pages, blocks, theme, copy) is Shop Builder. This file lists the
calls the agent makes for Steps 3–8 of `SKILL.md`, and the steps it hands to the partner.
Catalog and Login stay delegated, and checkout is the Web Shop's hosted Pay Station — see
`SKILL.md`.

## Context

- **Auth:** the Publisher Account session from `xsolla auth login` — the only source.
  Every `xsolla shopbuilder` command derives the session from that login. A session or
  token is never passed by hand or copied out of a browser. A missing, stale, or
  unauthorized session returns `401/403` → `needs_access`: run `xsolla auth login` again
  and resume. This is *not* `XSOLLA_PROJECT_API_KEY`.
- **Safe target:** before the first write, `scripts/preflight.py` must pass — the CLI points
  at the intended merchant and project, and that project is listed in the approved
  test-project allowlist.
- **No sandbox:** Shop Builder writes always reach the project itself, and `--sandbox` gives
  no isolation. Never pass it.

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

## Draft — build on the partner's site

The partner creates the site in Publisher Account from the **Multi-page web portal** template.
The agent never creates one: `create-website` makes a site with no layout, which the Editor,
publication and preview can't open. The template creates the layout (the sidebar, header and
footer) and most sections.

| Step | Command |
|---|---|
| Add each missing section's page | `add-page --slug <domain> --name <name> --path <path>` |
| Add its blocks at the top of the page | `add-block --landing-id <landingId> --page-id <pageId> --block <module> --index 0`, then `--index 1` |
| Remove a seeded block the section doesn't keep | `delete-block --landing-id <landingId> --page-id <pageId> --blockid <blockId> --force` |

### Portal layout

| Section | Path | From | Final page |
|---|---|---|---|
| Home | `/` | the template | as the template made it |
| News | `/news` | the template | as the template made it (`lead`, `news`, `lead`) |
| Rewards | `/rewards` | the template | as the template made it |
| Web Shop | `/store` | the template | as the template made it |
| Community | `/community` | added by the agent | `lead`, `embed` |
| Launcher (optional) | — | the partner (see below) | — |

The template's other pages (Loyalty shop, Promocodes) stay as they are. The News block shows
Launcher news articles only. If `/news`, `/rewards` or `/store` is missing, the site wasn't made
from this template: stop with `needs_input` instead of building those sections.

On this template, `add-page` seeds a new page with 11 game-sales blocks — `leadGameSales`,
`description`, `packs` ×3, `bento-grid` ×3, `gallery`, `requirements`, `faq` — and no header or
footer, which come from the site layout. The page gets no page type and no sidebar link. For
Community, add `lead` (`--index 0`) and `embed` (`--index 1`), then remove the 11 seeded blocks.
Module names come from the `shop-builder-assembly` [block
catalog](../../shop-builder-assembly/references/block-catalog.md).

Remove seeded blocks only on a page the agent created in this run. Re-read the page first; if it
holds anything that isn't from the seed or the confirmed plan, stop and ask. Remove only as the
confirmed plan lists: for each such page, the seeded modules it drops. `delete-block` takes each
block's `_id` (`--blockid`), read from `get-structure`; pass `--force`, since the confirmed plan is
the confirmation and the CLI's own prompt refuses without a terminal. Never delete a block on any
other page.

On resume, compare `get-structure` with this layout and add only what is missing; never add a
page whose path already exists. Seeded blocks left on a page from an earlier run are not
removed: list them for the partner to remove, as `needs_human`.

## Draft — pages and blocks

| Intent | Command |
|---|---|
| Add a page | `add-page` — `--name` (1–80 chars), `--path` (lowercase `a–z`, `0–9`, hyphen, slash; max 80) |
| Add / move / delete a block | `add-block` / `move-block` / `delete-block` |
| Hide or show a block, or patch the site theme | `update-block` |

`add-block` takes a **module template name** (`--block`), not a block ID, plus the landing
`_id`, the page `_id`, and always `--index`: without it the block goes to position 0, not to
the end. Use only the modules in the layout above.

`update-block` sends a map of `requestId → change`:

```json
{"r1": {"type": "block", "id": "<blockId>",
        "patches": [{"op": "replace", "path": ["hidden"], "value": true}]}}
```

- `type` is `block` (its `hidden` flag) or `site` (the theme); `id` is the block `_id` or
  the `landingId`. Page and site settings are the partner's.
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
| List assets | `list-assets --landing-id <landingId>` |
| Upload an asset | `upload-asset` |

Upload only partner-approved assets.

## Draft — copy and localization

Block text lives in the localization store, not on the block: blocks reference an `L:` id.

| Intent | Command | Body |
|---|---|---|
| Read the whole store | `get-localization` | — |
| Set one string | `update-localization` | `{ "pageId", "id": "L:<uuid>", "locale": "en-US", "value": "<p>…</p>" }` |
| Set many for one locale | `update-many-localization` | `{ "locale", "perScopeValues": { "<pageId>": { "L:<id>": { "description": "<existing>", "translation": "<p>…</p>" } } } }` |
| Add a locale | `add-language` | `{ "language": "en-US" }` |

- Page strings live under `pages.<pageId>.texts."L:<id>"`, shared strings under
  `common."L:<id>"` (pass `common` as the scope key). Keep the `L:` prefix.
- In `update-many-localization` the per-id value **must** be
  `{ "description": "<existing>", "translation": "<html>" }`. A missing `description` is
  cleared, so send the string's current one from `get-localization` (`""` for a new string).
  A missing `translation` writes an **empty** string for that locale — destructive. Other
  locales on the same string are preserved.

## Analytics and access

| Intent | Command |
|---|---|
| Analytics connector (`gtm` or `ga`) | `add-connector` |
| Access restrictions | `update-restrictions` |

Use these only when the confirmed plan lists them.

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
- Delete a site, an asset, a language, an analytics connector, or access restrictions.
- Attach, change, or verify an external domain.
- Publish Login widget settings, and publish News articles (switch them from `Draft`).

**Not yet available from the CLI — the partner does them in the builder:**

- Rename, duplicate, or delete a page; link a page under a parent in the navigation.
- Add each page the agent added (such as Community) to the sidebar menu.
- On a PC portal, hide the template's App Store and Google Play badges in the sidebar.
- Page and site settings, and site feature toggles.
- Show a store component (such as subscriptions) on the Web Shop.
- Launcher news articles. The News section is `placeholder` while its articles are `Draft`.
- Update an existing asset; rename the domain; move the site to another project.

## Launcher

A Launcher is only `completed` with a real Launcher on the project, an uploaded build, a
generated installer, and a verified installer download — evidence that must come from the
Launcher product itself. Builds, installers, and downloads are not reachable from here, so
the agent adds no Launcher page: the section is the partner's, and a missing piece is
`blocked_capability`, never `completed`.

## Failure → status mapping

| Response | Status | Action |
|---|---|---|
| `401` / `403` | `needs_access` | run `xsolla auth login`, re-read state, resume |
| No site at `domain` | `needs_human` | the partner creates it from the Multi-page web portal template, or enables Shop Builder for the project |
| No `/news`, `/rewards` or `/store` page | `needs_input` | the site wasn't made from the template: the partner confirms the site or creates one from it |
| `500` with a `domain` where a `landingId` belongs | — | wrong key: fix and retry; not a capability block |
| `429` while the CLI bootstraps the session | — | rate limited: wait a minute and retry; never set a session by hand |
| Launcher build / installer / download | `blocked_capability` | not reachable from here |
