---
name: xla-pages
description: >-
  Creates and updates XLA Pages on x.la in Shop Builder and keeps the current XLA Pages design:
  the game page (/game/:slug), payment provider pages (/payment/{provider}) and combined
  provider + game pages (/payment/{provider}/:slug), built only from the @xla-pages federated
  blocks, pinned to the versions on the reference pages, and bound to the XLA Pages API through
  Shop Builder data providers. Use for "create pages for x.la", "generate XLA game pages", "add a
  Klarna payment page on x.la", "update the PayPal page on x.la", "check the x.la pages against
  the manifest", or an XLA Pages batch file. It reports the /pub preflight from saved responses,
  renders one plan per batch, asks for one yes, backs up the site structure, writes only to the
  site's draft, and checks every page against the manifest afterwards. It never publishes, never
  writes to the catalog or the XLA Pages API, and never puts standard Shop Builder blocks, Custom
  Blocks or custom code on these pages. For any other Shop Builder site, use nocode-shop-setup.
metadata:
  owner: a.pyanzin
  domain: store
  status: draft
---

# XLA Pages

Build and update XLA Pages on x.la in Shop Builder. [The manifest](references/manifest.yaml) is
the spec: page types, blocks, bindings, writes and checks. Anything it doesn't list is not
allowed. The general Shop Builder rules (standard blocks first, Custom Blocks where needed,
theme and copy from a brief) don't apply to these pages.

The scripts do the checking; follow their output and never work around a refusal. Data
connections, bindings and SEO go through commands the CLI has today (`update-block`,
`update-many-localization`), stored the way Site Builder stores them. Today's CLI can't create
a dynamic page or add a block at a pinned version, so a batch that creates a page stops at the
gate with zero writes; an update of an existing page runs. Hand the user
[the CLI command spec](references/cli-gaps.md) and the gate's report.

## Before anything

- **The site.** One Shop Builder site, written in its draft only. Its merchant, project and slug
  live in the user's `.xsolla/xla-pages.json`, never in this repository (it's public):

  ```json
  {"merchant_id": 0, "project_id": 0, "site_slug": "<slug>", "write_to_published_site": true}
  ```

  Add `.xsolla/` to the project's `.gitignore` before the first file goes there. The site is
  live: `write_to_published_site: true` is the one exception to "never write to a published
  site", and only for that configured site. Ask the user for these values if the file is missing.
- **The CLI.** Signed in (`xsolla auth login`, in the user's own terminal) and pointing at that
  merchant and project with sandbox mode off (`xsolla config list --json`). If it points
  elsewhere, switch it (`xsolla config set merchant-id`, `project-id`, `sandbox false`) and say
  so, with the undo.
- **The batch.** One row per payment provider page, as the manifest's `batch.row_example` shows:
  `provider` (lowercase URL segment), `partner_name`, optional `partner_logo_url`, `hero_title` (at
  most 60 characters), `hero_description` (at most 150), `hero_image`, `faq`, optional `offers`,
  and optional `seo_title` / `seo_description` (default: the hero title and description). The
  rows are `{"providers": [...]}`. Game data never goes in the batch: it is bound, never typed.

## Steps

All scripts are in `scripts/` and run with `python3 -I`. Keep each run's files in a new
`.xsolla/xla-<UTC time>/` folder.

1. **Preflight.** Run `preflight_report.py next --pub-dir <run>/pub`. GET each URL it prints and
   save the response as is, with the time of the request, in the format
   [saved /pub responses](references/pub-responses.md) gives. Only GET, only
   `https://xla-pages.xsolla.com/pub/*`, no credentials. Repeat until it prints none, then run
   `preflight_report.py report --pub-dir <run>/pub --batch <batch.json>`.
2. **Backup.** `backup.py --out-dir <run>/backup` saves the skill's own `get-structure` and
   `get-localization` snapshot. It is the backup: Shop Builder's version history isn't, because restoring a version
   currently drops the data-provider connections.
3. **Plan.** `render_plan.py --batch <batch.json> --backup-dir <run>/backup --output
   <run>/plan.json`. It pins every block to the version on its page type's reference page and
   refuses a row over the limits, a field the reference block doesn't have, or anything the
   manifest doesn't list. Then `cli_gate.py --plan <run>/plan.json` says whether the CLI can
   apply it.
4. **One approval.** Show, in one message:
   - every page that appears or changes: create, update or unchanged, its route and type, its
     blocks with versions in order, its bindings, the row text word for word, SEO and page look;
   - for each existing page, what differs from the manifest now (`differences_now`), and the
     plan's `notes`;
   - the preflight: its lines, the redirect list per provider, and the request times;
   - the gate's result: which writes the CLI can make today;
   - that the Pages team publishes this site themselves, and their next publication ships these
     draft changes to x.la.

   Ask for one explicit yes. A request to "create the pages" is not that yes. When
   `cli_gate.py` reports missing commands, show the plan and the gate's report, say that
   nothing can be written until the CLI has them, and don't ask for the yes.
5. **Apply.** `apply_pages.py --plan <run>/plan.json --confirmation-id <its confirmation_id>
   --backup-dir <run>/backup --pub-dir <run>/pub`. Before the first write it stops, with zero
   writes, on: an edited plan, another backup, any manifest violation, /pub responses older than
   24 hours or incomplete, the wrong CLI target, a missing command or flag in `--help`
   (`blocked_capability`), another or a published site the config doesn't allow, or a site that
   changed since the backup. It deletes the blocks `add-page` seeds on a page it created in the
   same run (deleted, not hidden), and sets a page's look only to the reference page's values.
6. **Check and hand off.** Apply reads every page back and prints the per-page result: pass, or
   the exact difference, plus the manifest's acceptance numbers. For an update it checks that the
   page's data bindings are identical before and after. `verify_pages.py --plan --structure
   --localization --backup-dir` runs the same check on any export. Report every page, the numbers, and that nothing
   was published: a person publishes, all pages of the site at once.

## When something changes

- **Responses older than 24 hours:** request them again (step 1); the plan stays valid. Quote
  the report's `fresh_until` time; don't work it out.
- **The site changed after the backup** (the Pages team edits it too): back up again, render
  again, show the new plan, and ask again.
- **A run that stopped partway** prints what it created. Back up, render (created pages now show
  as updates), show the plan and ask again. Never retry blindly.
- **An existing page that differs from the manifest:** an update writes only row content,
  settings, an empty optional block's hidden flag, static SEO text and the page look. Missing
  bound blocks, extra blocks, wrong versions and bindings are listed for a person; blocks that
  were on a page before the run are never deleted or moved.

## Hard stops

- Never publish, enable a preview, run `verify-website`, or apply or restore a site version.
- Never write to the catalog, LiveOps or the XLA Pages API; the preflight only reads `/pub`.
- Never add a standard Shop Builder block, a Custom Block, a Custom code block, a block script,
  styles, fonts, iframes or trackers; never type game data into a block.
- Never pass `--force`; never call a command outside `scripts/xla_common.py`'s list.
- Never write to a site other than the configured one, or to a copy of it.
- Never commit `.xsolla/`, a plan, a backup or saved responses: they hold real IDs.

## Known limits

The manifest's block field names, the `@xla-pages` blocks' ids in the blocks service, and the
published-site semantics are not verified against a real site yet; [README.md](README.md) lists every
unverified item. Read-back shapes the CLI doesn't return yet make the check fail, not pass.
