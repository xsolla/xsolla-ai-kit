---
name: game-web-portal
description: >-
  Builds or resumes an unpublished Xsolla Game Web Portal for a PC game — a game home
  with Home, News, Rewards, Web Shop, Community, and an optional Launcher section
  around the store — and returns an evidence-backed handoff. Not the entry point for
  "build me a shop" or "set up my portal": that is shop-setup, which routes here once
  the recorded build path is portal. Use for "continue my Game Web Portal", "resume my
  portal without duplicating pages", "add the News / Rewards / Web Shop section to my
  portal", or wiring an existing catalog and Login into a portal. The agent never
  publishes, never runs the readiness check, and never generates a preview key — those
  are handed to the human in Publisher Account. PC only; App Store and Google Play
  titles return needs_input. For a store without a game home, use shop-setup, which
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

`shop-setup` routes here when the recorded build path is `portal` — the partner needs a
game home around the store (news, rewards, community, launcher), not only a store. The
path is recorded by `shop-plan`; this skill never decides it and never writes it.

Entry conditions:

- `XSOLLA_BUILD_PATH=portal` is recorded in `.env` (see
  [the build-path contract](../shop-plan/references/build-path-contract.md)). If it is
  absent, hand back to `shop-setup`; if it records another path, stop and say so.
- The title ships on PC. A Steam URL is optional and may be skipped.
- If a store URL is supplied, its host must be exactly `store.steampowered.com`.
  Mobile, unknown, invalid, or spoofed supplied URLs return `needs_input`.
- Without a Steam URL, continue using the supplied `game_name` and partner-approved
  metadata, copy, and assets. Never invent missing content.
- A merchant/project pair is confirmed and the target is a sandbox or dedicated test
  project — never a partner's live project.
- The caller has decided whether an existing portal at the domain should be updated
  or a new one created.

## Prerequisites

- Confirmed merchant ID and project ID — see `merchant-setup`.
- Publisher login through `xsolla auth login` — the only source of the session. Portal
  commands authenticate with that Publisher Account session, not the project API key.
  Never pass a session or token by hand, and never ask the partner to copy one out of
  the browser. Treat `401/403` as `needs_access`, never as a capability block.
- Shop Builder enabled for the target project.
- Approved content and brand assets. Never invent or reuse partner identifiers,
  credentials, content, prices, assets, or URLs.
- Required input, collected in a single question rather than one at a time (when
  `shop-setup` ran the intake, these are already recorded — do not ask again):

```yaml
merchant_id:
project_id:
domain:
game_name:
primary_locale:
existing_portal_policy: update | create-new
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
   [`scripts/preflight.py`](scripts/preflight.py)
   `--merchant-id --project-id --environment sandbox|test`, adding
   `--approved-test-projects <file>` for a test project. It checks that the CLI points at
   that merchant and project, and that the project is a sandbox or is listed in the
   approved test-project allowlist (the same check and file format as
   `shop-builder-assembly`). If it fails, stop before any write. If `store_url` is
   supplied, validate the exact Steam host. Use only partner-approved metadata and
   assets; never substitute invented game metadata.
3. **Discover** — list existing sites and read the target structure
   (`xsolla shopbuilder list-websites`, `get-landing`, `get-structure`). Capture the
   landing `_id`, page IDs, and block IDs before any mutation — block and theme calls
   are keyed by landing `_id`, not the domain. Never recreate a discovered existing
   entity; resume at the first incomplete item.
4. **Back up** — before the first write to an existing site (an update or a resume),
   export it: `get-landing`, `get-structure`, `get-localization`, and `list-assets` for
   the slug, saved to a new local directory. A failed export stops the run before any
   write. A brand-new site has nothing to back up.
5. **Plan and confirm** — show the ordered change groups (sections, pages, blocks,
   theme, copy, catalog links) and the exact removals, then wait for an explicit yes.
   Earlier permission to "set up my portal" is not confirmation of a plan. Re-confirm
   if the plan changes.
6. **Draft** — for a new portal, run `create-website`, then initialize the portal
   template on that landing with [`scripts/portal_template.py`](scripts/portal_template.py)
   `portal` (`409` means already initialized — resume, don't recreate), then add
   block-set templates with its `template` command. Both take the same target options as
   the preflight and refuse to write if it fails. Everything else uses CLI commands:
   `add-page`, `add-block`, `move-block`, `update-block` (block, page, and site theme
   patches), `upload-asset`, `add-language`, `update-localization`,
   `update-many-localization`. A change with no CLI command and no script is
   `needs_human`: say what to do in Publisher Account and record it. Apply one change
   group at a time across Home, News, Rewards, Web Shop, Community, and optional
   Launcher. Every call and how it is made:
   [references/portal-api.md](references/portal-api.md).
   Delegate the surrounding products rather than duplicating their recipes:
   `merchant-setup` for merchant/project/API key, `catalog-design` for catalog and
   pricing, `login-setup` for Login, `headless-checkout-integration` for checkout.
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

Status values: `completed`, `placeholder`, `needs_input`, `needs_access`,
`needs_human`, `blocked_capability`, `failed`.

Two references, both loaded before issuing changes:

- [references/agentic-onboarding.md](references/agentic-onboarding.md) — the
  specification: `GIVEN / WHEN / THEN` acceptance scenarios, the per-state evidence
  contract, and the handoff report template.
- [references/portal-api.md](references/portal-api.md) — the calls the agent makes for
  Steps 3–8 (CLI commands and the template script), the domain vs landing `_id` split,
  the localization payload shape, the steps handed to the partner, and the response →
  status mapping.

## Hard stops

The agent never publishes (sites, pages, news articles, or Login widget settings), never
runs the readiness check (`/check`, `verify-website`), never enables or generates a
preview, never reads or applies saved versions, never deletes a site, never attaches a
domain, never patches block text (it deletes the string and every translation), and never
switches the project to production. It never writes before an explicit confirmation of
the plan or before the preflight passes, and never targets a partner's live project.

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
5. **Access expiry losing progress.** On `401/403` mid-run, preserve the ledger and
   return `needs_access`, then re-run `xsolla auth login`, re-read state, and resume —
   do not restart the portal.
6. **Reporting completion without read-back.** Nothing enters **Completed** while
   read-back is pending.

## Known limitations

- **PC only.** App Store and Google Play titles return `needs_input` until the mobile
  path ships.
- **No Steam import.** The store-page parsing endpoint rejects Steam links in live
  tests, so metadata and assets come from the partner, not the Steam page.
- **The portal template call's layout flag is undocumented.** `portal_template.py`
  sends the single-page/hub choice under the name in the reference; a `400` there is
  reported as `failed` with the response, and the portal is built from `add-page` and
  `add-block` instead.
- **No Community page template.** That section needs a blank page and explicit blocks,
  so it returns `needs_input` rather than a guessed layout.
