# Xsolla Game Web Portal — Shop Builder reference

The portal itself (sites, pages, blocks, theme, copy) is Shop Builder. This file lists the
calls the agent makes for Steps 3–8 of `SKILL.md`, and the steps it hands to the partner.
Catalog and Login stay delegated, and checkout is the Web Shop's hosted Pay Station — see
`SKILL.md`.

## The only commands the agent runs

- `xsolla auth login`, `xsolla config list` (through `scripts/preflight.py`) and
  `xsolla publisher list-projects`.
- `xsolla config set sandbox false`, only when preflight stops on sandbox mode and the
  partner says yes to it.
- Read: `xsolla shopbuilder` `list-websites`, `get-landing`, `get-structure`, `list-pages`,
  `get-page`, `get-localization`, `list-assets`, `list-agreements`.
- Write: `xsolla shopbuilder` `add-page`, `add-block`, `move-block`, `update-block`,
  `upload-asset`, `add-language`, `update-localization`, `update-many-localization`,
  `add-connector`, `update-restrictions`.
- `--help` on any listed command, to check its flags, and `xsolla --help` (help on the CLI
  itself).

Every other command is out of bounds, even when the partner asks for it: among them
`delete-block`, `delete-domain`, `change-domain`, `delete-ai-block`, `delete-website`,
`create-website`, `verify-website` and `enable-preview`. A step that needs one is
`needs_human` — see [Done by the partner](#done-by-the-partner-in-publisher-account).

## Context

- **Auth:** the Publisher Account session from `xsolla auth login` — the only source.
  Every `xsolla shopbuilder` command derives the session from that login. A session or
  token is never passed by hand or copied out of a browser. A missing, stale, or
  unauthorized session returns `401/403` → `needs_access`: run `xsolla auth login` again
  and resume. This is *not* `XSOLLA_PROJECT_API_KEY`.
- **Safe target:** before the first write, `scripts/preflight.py` must pass — the CLI points
  at the intended merchant and project with its sandbox mode off, and that project is listed in
  the approved test-project allowlist.
- **No sandbox:** Shop Builder writes always reach the project itself, and `--sandbox` gives
  no isolation. Never pass it. A new CLI config starts with sandbox mode on, and preflight
  refuses it. Show the partner the exact command, `xsolla config set sandbox false`, and say
  that every later `xsolla` command with this config then reaches live, payments and refunds
  included. Run it only on a yes, then rerun preflight. The handoff says it is off and that
  `xsolla config set sandbox true` turns it back on.
- **No `--force`:** never pass, offer or suggest it, even if the partner changes the plan.
  Seeded blocks the CLI won't remove go to the partner as `needs_human`.

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

Discover also reads what the template already set up, and the plan reports it:

- **The Web Shop's catalog.** Each `newStore` block shows a group:
  `components[].section.item.group`. A test or demo group, such as `__test__/virtual_good` or a
  group starting with `demo`, means the Web Shop shows sample items. Say so, and leave the catalog
  to `catalog-design`.
- **Sign-in.** `auth` in `get-structure` says how the site signs buyers in. With
  `auth.type: "user-id"`, buyers already sign in with a user ID and can buy; say that before
  proposing any Login work, which stays with `login-setup`.

## Show the partner the site

The public URL, `https://<domain>.xsolla.site`, doesn't load until the first publish; say so
whenever the partner might open it. Link the Editor instead, in every progress message and in
the handoff:

- Main page: `https://publisher.xsolla.com/<merchant_id>/projects/<project_id>/site-builder/<domain>/editor`
- Another page: `…/site-builder/<domain>/<path without the leading slash>/editor`, for example
  `…/<domain>/community/editor`

The Editor doesn't refresh after CLI writes: reload it before looking.

## What the run can change

Tell the partner this in the first message, before any work:

| Change | How |
|---|---|
| Pages, blocks (add, move, hide), copy and locales | The agent, through the CLI |
| Images in blocks, on/off switches, store buttons | The agent, with `update-block` (see the table below) |
| Theme colors | The agent sets them; the partner recalculates them in the Editor ([Theme](#theme)) |
| The sidebar (logo, menu, store badges, social links) and the footer | The partner, in the Editor ([Layout](#the-layout-sidebar-and-footer)) |
| Deleting the seeded blocks the agent hid | The partner, in the Editor |

Without art from the partner or approved Steam content, the draft keeps the template's art.

## Steam content

A Steam URL is a source of content only after the partner confirms it is their own game's page
and approves using its art and text (`steam_assets_approved: yes`). Then read Steam's public app
details for the app ID in the URL: `https://store.steampowered.com/api/appdetails?appids=<appId>`.
It needs no key and no parser; Shop Builder's own store-page parser, which rejects Steam links, is
a different thing. Under `<appId>.data`:

| Field | Use |
|---|---|
| `header_image` | lead and hero art |
| `background_raw` | page and section backgrounds |
| `screenshots[].path_full` | gallery, card and description images (1920×1080) |
| `short_description`, `genres`, `developers` | facts for the copy |

Download only the images the plan uses, upload each with `upload-asset`, and put the CDN URL it
returns in the block; never point a block at Steam's own image host. Copy written from these
facts is new copy: show it word for word in the plan, so the partner's yes covers it. With
`steam_assets_approved: no`, or no answer, nothing from the page is used, and the intake says the
draft keeps the template's art and text unless the partner supplies their own.

## Draft — build on the partner's site

The partner creates the site in Publisher Account from the **Multi-page web portal** template.
The agent never creates one: `create-website` makes a site with no layout, which the Editor,
publication and preview can't open. The template creates the layout (the sidebar, header and
footer) and most sections.

| Step | Command |
|---|---|
| Add each missing section's page | `add-page --slug <domain> --name <name> --path <path>` |
| Add its blocks at the top of the page | `add-block --landing-id <landingId> --page-id <pageId> --block <module> --index 0`, then `--index 1` |
| Hide the seeded blocks it doesn't keep | `update-block --landing-id <landingId> --data <map>` |

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
footer, which come from the site layout. The page gets no page type and no sidebar link, and it
starts with its own theme ("Use global theme" off): set `["theme","enabled"]` to `false` on it
(see the table below). For Community, add `lead` (`--index 0`) and `embed` (`--index 1`), then
hide the 11 seeded blocks; the partner deletes them in the builder.

Added blocks bring content of their own. Read each one after adding it:

- `lead` comes with four store feature cards ("Official store", "Secure payments", "Fast
  delivery", "Exclusive offers") and an empty logo placeholder. Switch off what the plan doesn't
  keep where it has an `enable` flag; list the rest for the partner.
- `embed` shows a channel that only the Editor sets: the partner adds it, as `needs_human`, with
  the channel URL they supplied.
Module names come from the `shop-builder-assembly` [block
catalog](../../shop-builder-assembly/references/block-catalog.md).

Right after `add-page`, read `get-structure` and `get-localization`, and record the new page — its
path and seeded blocks — in the ledger with `scripts/seeded_blocks.py record`, passing both reads as
`--structure` and `--localization` and the new page as `--page-id`.

Hide a seeded block only on a page the agent created and recorded, only as the confirmed plan
lists, and only on the merchant, project and landing the ledger's storefront step records. Right
before hiding, read `get-structure` and `get-localization` again and run `seeded_blocks.py check`
with them, `--page-id`, `--ledger .xsolla/onboarding.json`, the `--merchant-id` and `--project-id`
preflight passed, and the `--landing-id` read in Discover. It refuses when the ledger's storefront
step records another target; otherwise hide only the blocks it reports `untouched`, in one
`update-block` call with a `hidden: true` patch per block `_id`. A `changed` block is left as it
is and listed for the partner as `needs_human`; a `gone` one needs nothing. Hide before any copy or
locale change: a changed string marks its block `changed`. Hiding changes the block too, so a later
`check` reports a hidden seeded block as `changed`; on resume, a recorded seeded block that reads
`hidden: true` is already done. Update the page's ledger entry after hiding. Never hide a block on
any other page, and never pass `--force`.

The agent never deletes a block: `delete-block` asks for a confirmation that only `--force`
skips. The plan says upfront that the hidden seeded blocks stay on the
page for the partner to delete in the builder, and the handoff lists them, by page and module, as
`needs_human`. Hidden blocks don't show on the site, so the draft is reviewable before they go.

On resume, compare `get-structure` with this layout and add only what is missing; never add a page
whose path already exists. A page at a planned path with no ledger record is never trimmed: report
it, with its blocks, as `needs_human`.

## Draft — pages and blocks

| Intent | Command |
|---|---|
| Add a page | `add-page` — `--name` (1–80 chars), `--path` (lowercase `a–z`, `0–9`, hyphen, slash; max 80) |
| Add / move a block | `add-block` / `move-block` |
| Hide a block, set its images, switches and store buttons, or patch the theme | `update-block` |

`add-block` takes a **module template name** (`--block`), not a block ID, plus the landing
`_id`, the page `_id`, and always `--index`: without it the block is appended to the end of the
page (CLI 1.9.4), not placed where the layout needs it. Use only the modules in the layout above.

`update-block` sends a map of `requestId → change`:

```json
{"r1": {"type": "block", "id": "<blockId>",
        "patches": [{"op": "replace", "path": ["hidden"], "value": true}]}}
```

- `type` is `block`, `page` or `site`; `id` is the block `_id`, the page `_id` or the
  `landingId`.
- `path` is a segment array, and a list index works as a segment (`["components",0,…]`).
  `op` is `add` | `remove` | `replace`.
- Protected, never patched: `_id`, `module`, `blockVersion`.

The agent patches only these. Read the block first and use `replace` on a leaf that exists:

| Target | Path | Value |
|---|---|---|
| A block | `["hidden"]` | `true`, for a seeded block (see above) |
| A block | a path ending in `img` or `src`, for example `["values","background","img"]`, `["values","grid","<cellId>","background","img"]`, `["values","components","<compId>","value","img"]`, `["components",0,"section","background","img"]`, `["values","chains",0,"background","img"]`, `["values","logo","img"]` | a CDN URL `upload-asset` returned for this site |
| A block | a path ending in `enable`, for example `["values","background","enable"]` | `true` or `false` |
| A block | `["values","platforms","items"]` | the store buttons: the list read from the block, sent back whole with each item's `{enable, id, platform, url}`; `platform` is a store such as `steam`, `epic`, `microsoft`, `playstation`, `xbox`, `app_store` or `google` |
| A page the agent added | `["theme","enabled"]` | `false`: the page uses the site theme |
| The site | `["theme","input",<key>]` | see [Theme](#theme) |

- **Never patch block text.** Patching a text value such as `["values","title"]` deletes the
  string and all its translations, and still returns `200`. Copy goes through
  `update-localization` — see below.
- Never replace a federated block's wrapper (one whose `values.blockId` names the module it
  shows) as a whole, and don't patch a `src` inside it.
- Read `get-localization` before and after each `update-block` call. If it changed, a patch hit a
  string: stop and report it.

### Theme

Read the site's `theme` in `get-structure` before patching it. On the Multi-page web portal
template, the colors are in `theme.input` — `bg`, `overlay`, `border`, `primary`, `secondary`,
`text`, `isDark`, `isWCAG` — with `calculationType: "xds-theme"`. There is no `mainColors` there.
Patch only keys that exist, in the format their current value has:

```json
{"t": {"type": "site", "id": "<landingId>",
       "patches": [{"op": "replace", "path": ["theme", "input", "primary"],
                    "value": "<same format as the current value>"}]}}
```

- The patch is stored, but `theme.calculatedTheme`, which the pages render from, isn't
  recalculated (CLI 1.9.4). The site keeps its old colors until the partner recalculates them.
- Every page has its own copy of the theme with an `enabled` flag. `true` means the page uses its
  own copy ("Use global theme" is off) and ignores the site theme. Switching "Use global theme"
  recalculates nothing. Changing a font in the Editor turns it off for that page.
- What the partner does in the Editor, handed over as `needs_human` with the Editor link and the
  colors: change one color by one step and back, click **Save as global theme**, then turn
  **Use global theme** back on. Warn them: with "Use global theme" off, **Save as global theme**
  saves the page's own copy over the site theme, old colors included, so they check the colors in
  the panel before saving.
- Afterwards, read `get-structure` again: `calculatedTheme` has changed, and every page has
  `theme.enabled == false`. List any page still at `true` for the partner.

## Draft — assets

| Intent | Command |
|---|---|
| List assets | `list-assets --landing-id <landingId>` |
| Upload an asset | `upload-asset` |

Upload only partner-approved assets, including approved [Steam content](#steam-content). The
Editor's media picker caches the asset list: a CLI upload shows up there after an Editor reload.

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

### Which string a block shows

A block can reference strings the template's layout doesn't show. On this template's Card grid
(`bento-grid`), the visible text is each cell's `values.gridComponents.<id>.text.id` and its
button labels; the grid's own title and description aren't shown. For any other block, find the
shown string before writing: the text the Editor shows appears in `get-localization`, under the
`L:` id to write. After a copy change, look at the page in the Editor.

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
evidence.

A read-back shows what is stored, not what renders: the theme and some block text can read back
right and still look wrong. Before calling a section done, look at its page in the Editor (reload
it first) and compare it with the plan. Use the Editor only to look: a synthetic click inside the
page can fire the page's own handlers, such as copying text to the clipboard. Without a browser,
the visual check goes to the partner as `needs_human`, with the Editor link.

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
- Delete the seeded blocks the agent hid on a page it added (Community has 11), in the builder.
- Attach, change, or verify an external domain.
- Publish Login widget settings, and publish News articles (switch them from `Draft`).

**Not yet available from the CLI — the partner does them in the builder:**

- Rename, duplicate, or delete a page; link a page under a parent in the navigation.
- Everything in the layout: see below.
- Page and site settings, and site feature toggles, except the global-theme switch on a page the
  agent added.
- Recalculate the theme ([Theme](#theme)).
- Show a store component (such as subscriptions) on the Web Shop.
- Launcher news articles. The News section is `placeholder` while its articles are `Draft`.
- Update an existing asset; rename the domain; move the site to another project.

### The layout: sidebar and footer

`get-structure` and `get-landing` list layouts by ID only, so the agent can't read or change
them. Much of what makes the portal look like the game is there. Give the partner these steps,
with the Editor link:

- **Sidebar → Layout → Logo image:** the game's logo.
- **Sidebar → Menu:** switch items on or off; **Add menu item** (pick the page, enter a name) for
  each page the agent added, such as Community.
- **Sidebar → Store buttons:** on a PC portal, switch off App Store and Google Play.
- **Sidebar → Social networks:** each network needs its URL; the Editor checks it per network.
- **Footer:** the "Use social network settings from sidebar" switch, and the Game icon image.
- **Images:** click the current thumbnail to open the site's asset library. **Add new asset**
  opens the computer's file picker.

## Launcher

A Launcher is only `completed` with a real Launcher on the project, an uploaded build, a
generated installer, and a verified installer download — evidence that must come from the
Launcher product itself. Builds, installers, and downloads are not reachable from here, so
the agent adds no Launcher page: the section is the partner's, and a missing piece is
`blocked_capability`, never `completed`.

## Failure → status mapping

| Response | Status | Action |
|---|---|---|
| `401` / `403` | `needs_access` | preserve the ledger, run `xsolla auth login`, re-read state, resume |
| No site at `domain` | `needs_human` | the partner creates it from the Multi-page web portal template, or enables Shop Builder for the project |
| No `/news`, `/rewards` or `/store` page | `needs_input` | the site wasn't made from the template: the partner confirms the site or creates one from it |
| `500` with a `domain` where a `landingId` belongs | — | wrong key: fix and retry; not a capability block |
| `429` while the CLI bootstraps the session | — | rate limited: wait a minute and retry; never set a session by hand |
| Launcher build / installer / download | `blocked_capability` | not reachable from here |
