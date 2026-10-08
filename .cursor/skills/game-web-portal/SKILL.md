---
name: game-web-portal
description: >-
  Builds or resumes an unpublished Xsolla Game Web Portal for a PC game — a game home with
  Home, News, Rewards, Web Shop, Community, and an optional Launcher section around the
  store — on the site the partner created from the Multi-page web portal template, and
  returns an evidence-backed handoff. Not the entry point for "build me a shop" or "set up
  my portal": that is shop-setup. On the Shop Builder path, description-to-shop or
  shop-builder-assembly hands off here when the recorded site kind is portal. Use for
  "continue my Game Web Portal", "resume my portal without duplicating pages", "add the
  Community section to my portal", or wiring an existing catalog and Login into a portal.
  The agent never publishes, never runs the readiness check, and never generates a preview
  key — those are handed to the human in Publisher Account. PC only; App Store and Google
  Play titles return needs_input. For a store without a game home, use shop-setup, which
  routes to the Shop Builder or headless path instead.
metadata:
  owner: a.pyanzin
  domain: orchestrator
  status: draft
---

# Game Web Portal

Build or resume an unpublished PC Game Web Portal and return an evidence-backed partner
handoff. Honest partial completion is correct; simulated completion is failure.

## When to use

On the Shop Builder path, `description-to-shop` or `shop-builder-assembly` hands off here
when the recorded site kind is `portal` — the partner needs a game home around the store
(news, rewards, community, launcher), not only a store. The site kind is recorded by
`shop-plan`; this skill never decides it and never writes it.

Entry conditions:

- `XSOLLA_BUILD_PATH=shopbuilder` and `XSOLLA_SITE_KIND=portal` are recorded in `.env` (see
  [the build-path contract](../shop-plan/references/build-path-contract.md)). With no path
  recorded, hand back to `shop-setup`. With the site kind absent or `shop`, the recorded site
  is a shop: stop and say so, since only `shop-plan` changes it. Any other path or kind:
  stop and say so.
- The title ships on PC. A Steam URL is optional and may be skipped.
- If a store URL is supplied, its host must be exactly `store.steampowered.com`.
  Mobile, unknown, invalid, or spoofed supplied URLs return `needs_input`.
- Without a Steam URL, continue using the supplied `game_name` and partner-approved
  metadata, copy, and assets. Never invent missing content.
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
- Approved content and brand assets. Never invent or reuse partner identifiers,
  credentials, content, prices, assets, or URLs.
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

Optional: `store_url` (Steam), approved description, logo, hero, screenshots,
colors and fonts; an existing Store catalog; additional locales; analytics IDs;
an existing Launcher and build. The Steam URL is a reference, not a production
dependency.

## Steps

The run is a state flow. Every mutation is preceded by an existing-vs-desired-state
check and followed by read-back and a ledger update.

```text
Intake → Preflight → Discover → Back up → Plan and confirm → Draft →
Verify (read-back) → Human review → Handoff
```

1. **Intake** — collect the required input above. Resolve every ambiguity by asking;
   never choose an ambiguous match.
2. **Preflight** — confirm PC scope, domain, and locale, then run
   [`scripts/preflight.py`](scripts/preflight.py) with `--merchant-id`, `--project-id` and
   `--approved-test-projects <file>`. It checks that the CLI points at that merchant and
   project with its sandbox mode off, and that the project is listed in the approved
   test-project allowlist (the same file format as `shop-builder-assembly`). If it fails,
   stop before any write. If `store_url` is supplied, validate the exact Steam host. Use
   only partner-approved metadata and assets; never substitute invented game metadata.
3. **Discover** — find the partner's site at `domain` and read its structure
   (`xsolla shopbuilder list-websites`, `get-landing`, `get-structure`). Capture the
   landing `_id`, page IDs, and block IDs before any mutation — block and theme calls
   are keyed by landing `_id`, not the domain. Confirm the site has the template's `/news`,
   `/rewards` and `/store` pages. Never recreate a discovered existing entity; resume at
   the first incomplete item.
4. **Back up** — before the first write, export the site: `get-landing`,
   `get-structure` and `get-localization` for the slug, and `list-assets` for the
   landing `_id`, saved to a new `.xsolla/backup-<timestamp>/` directory, which git
   ignores. A failed export stops the run before any write.
5. **Plan and confirm** — show the ordered change groups (sections, pages, blocks,
   theme, copy, catalog links) and the exact removals, then wait for an explicit yes.
   Earlier permission to "set up my portal" is not confirmation of a plan. Re-confirm
   if the plan changes.
6. **Draft** — map each section to the template's page by path, then build only the missing
   ones: `add-page`, its blocks with `add-block --index`, and `delete-block` for the seeded
   blocks it doesn't keep, following the portal layout in
   [references/portal-api.md](references/portal-api.md). The template's own pages keep their
   blocks. Right after `add-page`, record the new page with
   [`scripts/seeded_blocks.py`](scripts/seeded_blocks.py) `record`. Remove a seeded block
   only on a page the agent created and recorded, only as the confirmed plan lists, and only
   when `seeded_blocks.py check` on reads taken right before the removal reports it
   `untouched`; do removals before any copy or locale change, which would mark its block
   `changed`. Everything else uses CLI commands too: `move-block`, `update-block` (a block's
   `hidden` flag and the site theme), `upload-asset`, `add-language`, `update-localization`,
   `update-many-localization`, and `add-connector` or `update-restrictions` when the plan
   lists them. A change with no CLI command is `needs_human`: say what to do in Publisher
   Account and record it. Apply one change group at a time across Home, News, Rewards, Web
   Shop, and Community; the Launcher section is the partner's. Delegate the surrounding
   products rather than duplicating their recipes: `merchant-setup` for merchant/project/API
   key, `catalog-design` for the catalog and pricing the Web Shop sells, `login-setup` for
   Login. Checkout is the Web Shop's hosted Pay Station, so there is nothing to integrate.
   Placeholders require approval and a visible label.
7. **Verify (read-back)** — read back every changed entity (`get-structure`,
   `get-localization`, page and block reads) and compare it with the confirmed plan.
   A mutation response is not evidence. Keep unverified items out of **Completed**.
8. **Human review** — present completed items, placeholders, blockers, and failures.
   `draft_ready` requires correct ownership, domain, type, and locale, no duplicate
   routes, read-back-verified content, disclosed placeholders, and explicit Login and
   commerce status. Then hand over, as `needs_human`, the steps the agent never runs:
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

The agent never publishes (sites, pages, news articles, or Login widget settings), never
runs the readiness check (`/check`, `verify-website`), never enables or generates a
preview, never creates a site, never saves or applies a site version, never deletes a site,
an asset, a language, an analytics connector, access restrictions, or a block the removal
rule above doesn't allow, never attaches a domain, never patches block text (it deletes the
string and every translation), and never switches the project to production. It never writes
to the project before an explicit confirmation of the plan or before the preflight passes,
never passes `--sandbox`, and never targets a partner's live project.

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
- **No Steam import.** The store-page parsing endpoint rejects Steam links in live
  tests, so metadata and assets come from the partner, not the Steam page.
- **Community needs the partner's channel.** Its `embed` block shows a social channel the
  partner supplies; without one the section is `needs_input`, not a guessed layout.
- **The partner creates the site.** Until a site created through the CLI gets a layout,
  the portal is built on the partner's template site, and a page the agent adds has no
  page type and no link in the sidebar menu; the partner adds the link.
- **Deprecated block endpoints.** `add-block`, `move-block` and `delete-block` call Shop
  Builder endpoints marked deprecated for future removal. They work today; the skill moves
  with the CLI when those commands switch to the newer routes.
