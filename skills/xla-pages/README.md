# xla-pages

Builds and updates XLA Pages on x.la in Shop Builder from [the manifest](references/manifest.yaml):
the game page, payment provider pages and combined provider + game pages, with `@xla-pages/*`
federated blocks only, pinned to the reference pages' versions and bound to the XLA Pages API.

## Status

Draft. Preflight, plan, validation and the after-write check work. Data connections, bindings
and SEO are written through today's `update-block` and `update-many-localization`, in the shapes
the Site Builder server uses. Creating a page needs what the CLI doesn't have yet: a dynamic
page with a data provider from `add-page`, and a federated block at an exact version
(`scripts/cli_gate.py` lists the commands and flags). With the current CLI a batch that creates a page
stops at the gate with zero writes and reports what is missing. Updates of existing pages are off
until one run on a single test page confirms their write shapes (the manifest's
`writes.updates`; `allow_unverified_updates` in the local config opens that one run).

## Happy path

```bash
python3 -I scripts/preflight_report.py next --pub-dir .xsolla/xla-run/pub
python3 -I scripts/preflight_report.py report --pub-dir .xsolla/xla-run/pub --batch batch.json
python3 -I scripts/backup.py --out-dir .xsolla/xla-run/backup
python3 -I scripts/render_plan.py --batch batch.json --backup-dir .xsolla/xla-run/backup --output .xsolla/xla-run/plan.json
python3 -I scripts/cli_gate.py --plan .xsolla/xla-run/plan.json
python3 -I scripts/apply_pages.py --plan .xsolla/xla-run/plan.json --confirmation-id <id> \
  --backup-dir .xsolla/xla-run/backup --pub-dir .xsolla/xla-run/pub
```

Between `next` and `report` the agent GETs each listed URL and saves it as
[saved /pub responses](references/pub-responses.md) describes. All scripts read the local
`.xsolla/xla-pages.json` for the merchant, project and slug (`--config` to move it).

## Tests

```bash
cd skills/xla-pages && python3 -m unittest discover -s tests -v
```

They run against `tests/stand_in_cli.py`, a stateful stand-in for the CLI, and synthetic
fixtures: the `/pub` responses have the structure of real ones and invented values. Covered: a
block outside the manifest, a theme or style write, typed game data, a row over the limits, the
current CLI at the gate, responses older than 24 hours, an edited plan, a changed site and a
published site each stop with zero writes; so do updates of existing pages until the
local override allows one page; a batch creates every page and passes the check; the
check reports the exact difference; an update keeps the page's bindings identical and runs on
the current CLI; connections and bindings are stored as Site Builder stores them (site-level
`valuesSystem`, `#VC:` values, `usedBy`); a block the server adds at another version than the
pinned one stops the run; the preflight
covers empty `payment_methods`, a capitalized provider id, empty `countries`, a provider listed
twice, more than 20 media, a cover whose info is 404, a title over 60 characters, an empty `faq`,
and a game served by `core-attributes` but missing from the catalog.

## Not verified yet

What the code assumes and a real site still has to confirm:

- **Block fields.** The manifest's field names come from a page-template spec, not block source:
  `title`, `description`, `image`, `tagGameTitle`, `purchaseSku`, `gamesJson`, `providerId`,
  `faqJson`, `mediaJson`, `genresJson`, `platformsJson`, `storeGroupId`, `currencyName`,
  `publisherName`, `developerName`, `co_brand`. The row fields map to `partnerName`,
  `partnerLogoUrl` and `offersJson` by the kit's guess. A plan refuses any field the reference
  page's block doesn't have.
- **Where settings live.** Row content and settings are written to
  `values.internalBlockValues.<field>`, as Site Builder stores federated block values.
- **The CLI's pass-through.** That `update-block --data` passes a `valuesSystem` entity to the
  batch API unchanged, and that the CLI's `get-structure` returns `valuesSystem`, the page `path`
  object with `connectionId`, `dataConnectionId`, and `seo` with its `L:` strings. Read from the
  Site Builder server code, not from a CLI run. Until a read-back has them, a check fails rather
  than passes.
- **Block ids.** That a federated block's `values.blockId` holds the scoped package name
  (`@xla-pages/hero`). The indexed Site Builder code has no `@xla-pages` block.
- **Versions.** The `stable_releases` lists and the hero 0.2.0 sorting warning. The server falls
  back to the latest stable version when the asked one is missing; the skill reads the version
  back and stops.
- **Hiding a federated block** with the `["hidden"]` patch; seen only on other modules.
- **The linked data provider.** The server's add-page hands out `dataConnectionId`; the Editor
  client writes the `ugc-d-data-game-provider-v2` connection. The skill writes it when it is
  missing, with `slug` bound to the route param.
- **A new page's SEO.** That add-page gives a page `L:` strings for its SEO title, description
  and share image; without them the SEO write stops.
- **Bound value types.** That federated blocks bind only strings, numbers and booleans.
- **Page look.** Only `theme` is a known page key; `background` and `layout` are guesses. The
  design values (`#141d1f`, 1640 px, gutters, the 4 px gap) are not checked by the scripts; the
  page look is copied from the reference page instead.
- **The published site.** The user confirmed that edits stay in the draft until a person
  publishes; no test run has shown it. The kit can't pin the one allowed published site in code
  without committing its IDs: the exception is the site in the local config.
- **The API.** The `payment_methods` entry shape (`id`, `payment_method_id`, `countries`) is the
  manifest's; the real response read on 2026-11-07 had an empty list. The `getData` limits
  (300 a minute, 30 s, 2,500 paths, 1,000 list items) are not checked.

Assumptions the manifest leaves open, shown in the plan's `notes` or here:

- The combined page's about-game entry lists no bindings; it takes the game page's for the same
  variant.
- A static page's SEO title and description are `seo_title` / `seo_description`, or else the
  hero title and description.
- `top-up-packages` is on a combined page only when the combined reference page has it.

## Found while building

- The manifest writes a dynamic page's canonical URL with `{slug}`. Site Builder fills `:slug` with
  the page's value when it renders, so the plan writes `https://x.la/game/:slug`.
- Three list items in the original manifest were YAML mappings, not text, because of an unquoted
  `: ` (`game_paths.behavior`, `writes.allowed`, `validation.after_write`). They are quoted now;
  `tests/test_manifest.py` catches it next time.
- The manifest says media `object_metadata` holds width and height for images; the real info for
  an image cover returned `{}`.
- A game in the catalog without a mode, but in neither `buy` nor `top_up`, still gets a path from
  the paths provider, while the preflight check says "no page is generated". The report says both.
- The reference game's real `short_description` is 180 characters, so the 150-character check
  already fails on it.
