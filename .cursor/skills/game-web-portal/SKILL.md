---
name: game-web-portal
description: >-
  Builds or resumes an unpublished Game Web Portal for a PC or mobile game: Home, News,
  Rewards, Web Shop, Community and an optional Launcher, on a site made from the Multi-
  page web portal template. Reached through nocode-shop-setup. Use for "continue my Game
  Web Portal" or "add the Community section". Never publishes; that stays with the
  human.
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
- The title ships on PC, the App Store or Google Play. A store URL is optional.
- Check a supplied store URL with `scripts/store_url.py`: only the exact Steam, App Store and
  Google Play hosts pass; anything else, or a look-alike, returns `needs_input`.
- The partner's store page is a source of art and facts
  ([store content](references/portal-api.md#store-content)); the plan shows what comes from
  it, and its yes covers using it. Never invent missing content.
- The merchant and project are known, from the request's link or the CLI, and the plan
  names them. Shop Builder has no sandbox: every write reaches the project itself, on the
  unpublished site.
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
- Content and brand assets: the partner's own, or from their store page. Never invent
  content; the plan shows where each piece comes from.
- Required input, collected in a single question rather than one at a time. Read what is
  already known instead of asking again: intake from the ledger or the conversation, the
  merchant and project from `xsolla config list --json`:

```yaml
merchant_id:
project_id:
domain:
game_name:
primary_locale:
```

Optional: `store_url`; the partner's own
description, logo, hero, screenshots, colors and fonts; an existing Store catalog;
additional locales; analytics IDs; for a PC title, an existing Launcher and build.

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

1. **Intake** — once the Entry conditions hold (site kind from the ledger or the chat), the
   first message, before any question, tells the partner to create the site first if they
   haven't (Storefronts → Websites → Multi-page web portal → Manual), and
   [what the run can change](references/portal-api.md#what-the-run-can-change) and what stays
   an Editor step for them. It asks only the required input `nocode-shop-setup`'s batch
   didn't.
   Resolve every ambiguity by asking; never choose an ambiguous match.
2. **Preflight** — confirm the platform, domain, and locale, then run
   [`scripts/preflight.py`](scripts/preflight.py) with `--merchant-id` and `--project-id`.
   It checks that the CLI points at that merchant and project with its sandbox mode off.
   If it fails, stop before any write. If `store_url` is supplied, check it with `scripts/store_url.py`
   and read the listing as store content says.
3. **Discover** — find the partner's site at `domain` and read its structure
   (`xsolla shopbuilder list-websites`, `get-landing`, `get-structure`). Capture the landing
   `_id`, page IDs, and block IDs before any mutation — block and theme calls are keyed by
   landing `_id`, not the domain. Confirm the template's `/news`, `/rewards` and `/store`
   pages, and read its catalog groups (a test or demo group means sample items) and sign-in
   ([Discover](references/portal-api.md#discover)).
   Never recreate a discovered existing entity; resume at the first incomplete item.
4. **Back up** — before the first write, export the site: `get-landing`,
   `get-structure` and `get-localization` for the slug, and `list-assets` for the
   landing `_id`, saved to a new `.xsolla/backup-<timestamp>/` directory. Add `.xsolla/` to
   `.gitignore` first if it isn't there: a site export can hold a preview token. A failed
   export stops the run before any write.
5. **Plan and confirm** — show the ordered change groups (sections, pages, blocks, theme, copy
   word for word, images by source), the seeded blocks it will hide for the partner to delete,
   and, as Editor steps for the partner, binding the Web Shop and Rewards to the new catalog
   and LiveOps. Put any pending `catalog-design` proposal in the same message; wait for one
   explicit yes to both. "Set up my portal" is not that yes. Re-confirm if the plan changes.
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
   partner's, PC only. `nocode-shop-setup` runs the surrounding products before this skill;
   don't repeat their recipes: `merchant-setup`, `catalog-design` (it creates the catalog
   after the yes in step 5) and `login-setup`. Checkout is the Web Shop's hosted Pay Station,
   so there is nothing to integrate. The plan lists each placeholder; it carries a visible label.
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
9. **Handoff** — repeat merchant ID, project ID, domain, locale, and store URL only
   when one was supplied, with evidence for every completed item.

Statuses, the ledger, resume, and the handoff report follow the
[onboarding contract](../nocode-shop-setup/references/onboarding-contract.md). Two more references,
both loaded before issuing changes:

- [references/agentic-onboarding.md](references/agentic-onboarding.md) — the portal
  specification: `GIVEN / WHEN / THEN` acceptance scenarios, the portal's per-state
  evidence, its section of the handoff report, and the common pitfalls and known
  limitations.
- [references/portal-api.md](references/portal-api.md) — the CLI commands the agent runs
  for Steps 3–8, the portal layout, the domain vs landing `_id` split, the localization
  payload shape, the steps handed to the partner, and the response → status mapping.

## Hard stops

This skill runs only the commands listed in
[references/portal-api.md](references/portal-api.md), and `--help` on them or on the CLI itself
(`xsolla --help`), even when the partner asks for another. `catalog-design` runs its own.
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

## Pitfalls and limitations

Read them in [agentic-onboarding.md](references/agentic-onboarding.md#common-pitfalls)
before the first change: duplicates on resume, a portal reported as live, sign-in taken
for binding, an unverified Launcher, expired access, completion without read-back; Community
needs the partner's channel, and they create the site.
