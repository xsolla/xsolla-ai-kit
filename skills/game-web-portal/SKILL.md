---
name: game-web-portal
description: >-
  Builds or resumes an unpublished Xsolla Game Web Portal for a PC game — a game home with
  Home, News, Rewards, Web Shop, Community, and an optional Launcher section around the
  store — on the site the partner created from the Multi-page web portal template, and
  returns an evidence-backed handoff. Not the entry point for "build me a shop" or "set up
  my portal": that is nocode-shop-setup. It hands off here when the user wants a game
  home, or the existing site has /news, /rewards, and /store. Use for
  "continue my Game Web Portal", "resume my portal without duplicating pages", "add the
  Community section to my portal", or wiring an existing catalog and Login into a portal.
  The agent never publishes, never runs the readiness check, and never generates a preview
  key — those are handed to the human in Publisher Account. PC only; App Store and Google
  Play titles return needs_input. For a store without a game home, use nocode-shop-setup.
  For a shop the user codes and deploys, use shop-setup.
metadata:
  owner: a.pyanzin
  domain: orchestrator
  status: draft
---

# Game Web Portal

Build or resume an unpublished PC Game Web Portal and return an evidence-backed partner
handoff. Honest partial completion is correct; simulated completion is failure.

## When to use

`nocode-shop-setup` hands off here when the partner needs a game home around the store
(news, rewards, community, launcher), not only a store. This skill does not decide that
and does not write it to `.env`.

Entry conditions:

- The user asked for a game home, or the existing site has `/news`, `/rewards`, and
  `/store`. A site without those pages is a store: stop and point at `nocode-shop-setup`.
  Do not read or write `XSOLLA_BUILD_PATH` or `XSOLLA_SITE_KIND`.
- The title ships on PC. A Steam URL is optional and may be skipped.
- If a store URL is supplied, its host must be exactly `store.steampowered.com`.
  Mobile, unknown, invalid, or spoofed supplied URLs return `needs_input`.
- A Steam page is a source of art and facts only with `steam_assets_approved: yes`
  ([Steam content](references/portal-api.md#steam-content)). Otherwise use only `game_name`
  and partner-approved metadata, copy, and assets. Never invent missing content.
- A merchant/project pair is confirmed and the target is a dedicated test project on the
  approved test-project allowlist — never a partner's live project. Shop Builder has no
  sandbox: every write reaches the project itself.
- The partner has created the site in Publisher Account from the **Multi-page web portal**
  template (Storefronts → Websites → Multi-page web portal → Manual). The agent never
  creates a site: one created through the CLI has no layout, so the Editor, publication
  and preview can't open it. Without the partner's site, the run stops at `needs_human`
  with that instruction; a site without `/news`, `/rewards` or `/store` wasn't made from
  the template, and the run stops at `needs_input`.

## Prerequisites

- Confirmed merchant ID and project ID — see `merchant-setup`.
- Publisher login through `xsolla auth login` — the only source of the session. Portal
  commands authenticate with that Publisher Account session, not the project API key.
  Never pass a session or token by hand, and never ask the partner to copy one out of
  the browser. Treat `401/403` as `needs_access`, never as a capability block.
- Shop Builder enabled for the target project.
- Approved content and brand assets: the partner's own, or approved Steam content. Never
  invent content or use anything the partner hasn't approved.
- Required input, collected in a single question rather than one at a time. Read what is
  already known instead of asking again: `shop-plan`'s intake from the ledger, the merchant
  and project from `.env`:

```yaml
merchant_id:
project_id:
domain:
game_name:
primary_locale:
```

Optional: `store_url` (Steam) with `steam_assets_approved` (yes or no), approved
description, logo, hero, screenshots, colors and fonts; an existing Store catalog;
additional locales; analytics IDs; an existing Launcher and build.

## Steps

The run is a state flow. Every mutation is preceded by an existing-vs-desired-state
check and followed by read-back and a ledger update.

After every write to `.xsolla/onboarding.json`, run [`scripts/ledger.py`](scripts/ledger.py)
`check --ledger .xsolla/onboarding.json`; if it fails, fix the step it names before going on.
A step still under way has no `status` key (never `partial`, `in_progress` or another word)
until it ends with one of the contract's seven statuses.

```text
Intake → Preflight → Discover → Back up → Plan and confirm → Draft →
Verify (read-back) → Human review → Handoff
```

1. **Intake** — once `.env` passes the path and site-kind check in Entry conditions, the
   first message, before any question, tells the partner to create the site first if they
   haven't (Storefronts → Websites → Multi-page web portal → Manual), and
   [what the run can change](references/portal-api.md#what-the-run-can-change) and what stays
   an Editor step for them. The same message collects the required input above; with a
   Steam URL, it asks whether the page is theirs and its art and text may be used. Resolve
   every ambiguity by asking; never choose an ambiguous match.
2. **Preflight** — confirm PC scope, domain, and locale, then run
   [`scripts/preflight.py`](scripts/preflight.py) with `--merchant-id`, `--project-id` and
   `--approved-test-projects <file>`. It checks that the CLI points at that merchant and
   project with its sandbox mode off, and that the project is listed in the approved
   test-project allowlist (the same file format as `shop-builder-assembly`). If it fails,
   stop before any write. If `store_url` is supplied, validate the exact Steam host, and
   with `steam_assets_approved: yes` read its app details.
3. **Discover** — find the partner's site at `domain` and read its structure
   (`xsolla shopbuilder list-websites`, `get-landing`, `get-structure`). Capture the landing
   `_id`, page IDs, and block IDs before any mutation — block and theme calls are keyed by
   landing `_id`, not the domain. Confirm the template's `/news`, `/rewards` and `/store`
   pages, and read its catalog groups and sign-in ([Discover](references/portal-api.md#discover)).
   Never recreate a discovered existing entity; resume at the first incomplete item.
4. **Back up** — before the first write, export the site: `get-landing`,
   `get-structure` and `get-localization` for the slug, and `list-assets` for the
   landing `_id`, saved to a new `.xsolla/backup-<timestamp>/` directory. Add `.xsolla/` to
   `.gitignore` first if it isn't there: a site export can hold a preview token. A failed
   export stops the run before any write.
5. **Plan and confirm** — show the ordered change groups (sections, pages, blocks, theme, copy
   word for word, images by source, catalog links) and the seeded blocks it will hide, which
   the partner then deletes in the builder; wait for an explicit yes. Earlier permission to
   "set up my portal" is not confirmation of a plan. Re-confirm if the plan changes.
6. **Draft** — map each section to the template's page by path, then build only the missing
   ones: `add-page`, its blocks with `add-block --index`, and `update-block` to hide the
   seeded blocks it doesn't keep, following the portal layout in
   [references/portal-api.md](references/portal-api.md). The template's own pages keep their
   blocks. Right after `add-page`, record the new page with
   [`scripts/seeded_blocks.py`](scripts/seeded_blocks.py) `record`. Hide a seeded block
   only on a page the agent created and recorded, only as the confirmed plan lists, and only
   when `seeded_blocks.py check`, on reads taken right before hiding and the target
   preflight passed, reports it `untouched`; hide before any copy or locale change, which
   would mark its block `changed`. The agent never deletes a block: the hidden seeded blocks
   go to the partner to delete, as `needs_human`. Everything else uses CLI commands too:
   `move-block`, `update-block` (only the patches portal-api.md lists), `upload-asset`,
   `add-language`, `update-localization`, `update-many-localization`, and `add-connector` or
   `update-restrictions` when the plan lists them. A change with no CLI command is
   `needs_human`: say what to do in Publisher Account and record it. Apply one change group
   at a time across Home, News, Rewards, Web Shop, and Community; the Launcher section is the
   partner's. Delegate the surrounding products rather than duplicating their recipes:
   `merchant-setup` for merchant/project/API key, `catalog-design` for the catalog and
   pricing the Web Shop sells, `login-setup` for Login. Checkout is the Web Shop's hosted Pay
   Station, so there is nothing to integrate. Placeholders require approval and a visible
   label.
7. **Verify (read-back)** — read back every changed entity (`get-structure`,
   `get-localization`, page and block reads) and compare it with the confirmed plan.
   A mutation response is not evidence, and a read-back isn't what renders: look at each
   changed page in the Editor too. `storefront` is `completed` only when every planned
   change reads back; one that didn't land (no CLI field, a failed write) makes it
   `needs_human`, `needs_input`, `blocked_capability` or `failed`, with the gap in its `evidence`.
   Every progress message links the Editor and says the public URL loads only after the first
   publish ([Show the partner the site](references/portal-api.md#show-the-partner-the-site)).
8. **Human review** — present completed items, placeholders, blockers, and failures.
   The draft is ready for review only with correct ownership, domain, type, and locale,
   no duplicate routes, read-back-verified content, disclosed placeholders, and explicit
   Login and commerce status. Then hand over, as `needs_human`, the steps the agent never runs:
   the readiness check, the preview, publication (per page — the main page first),
   live verification, and any rollback to a saved version — all in Publisher Account.
9. **Handoff** — repeat merchant ID, project ID, domain, locale, and Steam URL only
   when one was supplied, with evidence for every completed item.

Statuses, the ledger, resume, and the handoff report follow the
[onboarding contract](../shop-plan/references/onboarding-contract.md). Two more references,
both loaded before issuing changes:

- [references/agentic-onboarding.md](references/agentic-onboarding.md) — the portal
  specification: `GIVEN / WHEN / THEN` acceptance scenarios, the portal's per-state
  evidence, and its section of the handoff report.
- [references/portal-api.md](references/portal-api.md) — the CLI commands the agent runs
  for Steps 3–8, the portal layout, the domain vs landing `_id` split, the localization
  payload shape, the steps handed to the partner, and the response → status mapping.

## Hard stops

The agent runs only the commands listed in
[references/portal-api.md](references/portal-api.md), and `--help` on them or on the CLI itself
(`xsolla --help`), even when the partner asks for another.
Every other `xsolla` command is out of bounds, including `delete-block`, `delete-domain`,
`change-domain` and `delete-ai-block`; what a run needs beyond the list is `needs_human`.

The agent never publishes (sites, pages, news articles, or Login widget settings), never
runs the readiness check (`/check`, `verify-website`), never enables or generates a
preview, never creates a site, never saves or applies a site version, never deletes a site,
an asset, a language, an analytics connector, access restrictions, or a block, never
attaches a domain, never patches block text (it deletes the string and every translation),
and never switches the project to production. It never writes
to the project before an explicit confirmation of the plan or before the preflight passes,
never passes `--sandbox`, and never targets a partner's live project. It never passes, offers
or suggests `--force`, even if the partner changes the plan: seeded blocks the CLI won't remove
go to the partner as `needs_human`.

## Common pitfalls

1. **Duplicate pages and blocks on resume.** Onboarding an existing domain without
   reading the current structure first creates a second Home or Web Shop. Always
   discover and compare existing versus desired state before any mutation.
2. **Reporting the portal as live.** The agent stops at an unpublished draft. Publication
   and live verification are the human's, and the handoff says so.
3. **Login sign-in mistaken for Login done.** Sign-in can succeed while account
   binding fails. Both Login and onboarding remain incomplete until binding is
   verified.
4. **Launcher marked complete without a verified download.** A Launcher needs a real
   Launcher on the project, an uploaded build, a generated installer, and a verified
   installer download. Refuse publish-anyway when that evidence is missing.
5. **Access expiry losing progress.** On `401/403` mid-run, preserve the ledger and return
   `needs_access`, then re-run `xsolla auth login`, re-read state, and resume — do not
   restart the portal.
6. **Reporting completion without read-back.** Nothing enters **Completed** while
   read-back is pending.

## Known limitations

- **PC only.** App Store and Google Play titles return `needs_input` until the mobile
  path ships.
- **Steam content needs the partner's yes.** Shop Builder's store-page parser rejects Steam
  links, so the agent reads Steam's app details itself, only with `steam_assets_approved: yes`.
- **Community needs the partner's channel.** Its `embed` block shows a social channel the
  partner supplies; without one the section is `needs_input`, not a guessed layout.
- **The partner creates the site.** Until a site created through the CLI gets a layout,
  the portal is built on the partner's template site, and a page the agent adds has no
  page type and no link in the sidebar menu; the partner adds the link.
- **Deprecated block endpoints.** `add-block` and `move-block` call Shop Builder
  endpoints marked deprecated for future removal. They work today; the skill moves
  with the CLI when those commands switch to the newer routes.
