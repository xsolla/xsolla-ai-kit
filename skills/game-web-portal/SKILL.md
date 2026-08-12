---
name: game-web-portal
description: >-
  Set up, create, configure, or resume an Xsolla Game Web Portal for a PC or Steam
  game. Use when onboarding a PC or Steam title, creating or resuming a Game Portal,
  wiring a Web Shop, Launcher, or Login into a portal, generating a preview link, or
  checking readiness and publication status. Covers the Home, News, Rewards, Web Shop,
  Community, and optional Launcher sections plus catalog, theme, localization, preview,
  and publication gates. Invoke for "set up my PC Game Portal", "resume my portal
  without duplicating pages", "give me a verified preview", or "is my portal ready to
  publish". PC and Steam only — App Store and Google Play onboarding is out of scope
  and returns needs_input.
metadata:
  owner: apyanzin-xsolla
  domain: orchestrator
---

# Game Web Portal

Create or resume a verified PC/Steam Game Web Portal and return an evidence-backed
partner handoff. Honest partial completion is correct; simulated completion is failure.

## When to use

Trigger keywords: PC Game Portal, Game Web Portal, Steam onboarding, portal resume,
Web Shop, Launcher, Login binding, preview link, readiness, publication.

Entry conditions:

- The title ships on PC and the store URL host is exactly `store.steampowered.com`.
  Mobile, unknown, invalid, or spoofed hosts return `needs_input`.
- A publisher context is authenticated and a merchant/project pair is confirmed.
- The caller has decided whether an existing portal at the domain should be updated
  or a new one created.

Use `shop-setup` instead for a general zero-to-shop storefront; this skill is the
PC/Steam portal path and delegates catalog, Login, and checkout work to the skills
listed under Steps.

## Prerequisites

- Authenticated publisher context.
- Confirmed merchant ID and project ID — see `merchant-setup`.
- API key for catalog and payment operations where required.
- Shop Builder access for the target project.
- Approved content and brand assets. Never invent or reuse partner identifiers,
  credentials, content, prices, assets, or URLs.
- Required input, collected in a single question rather than one at a time:

```yaml
merchant_id:
project_id:
domain:
game_name:
store_url:
primary_locale:
existing_portal_policy: update | create-new
```

Optional: approved logo, hero, screenshots, colors and fonts; an existing Store
catalog; additional locales; analytics IDs; an existing Launcher and build.

## Steps

The run is a state flow. Every mutation is preceded by an existing-vs-desired-state
check and followed by read-back and ledger update.

```text
Intake → Preflight → Discover → Draft → Verify → Human review →
Publish → Live verification → Handoff
```

1. **Intake** — collect the required input above. Resolve every ambiguity by asking;
   never choose an ambiguous match.
2. **Preflight** — validate the exact Steam host, confirm merchant/project, domain,
   and locale, and disclose any unsupported or human-gated step up front.
3. **Discover** — list existing websites and read the target structure. Capture
   landing, page, and block IDs. Never recreate a discovered existing entity; resume
   at the first incomplete item.
4. **Draft** — apply one change group at a time across Home, News, Rewards, Web Shop,
   Community, and optional Launcher. Delegate rather than duplicating recipes:
   `merchant-setup` for merchant/project/API key, `shop-setup` for pages, blocks,
   theme, localization, and preview, `catalog-design` for catalog and pricing,
   `login-setup` for Login, `headless-checkout-integration` for checkout.
   Placeholders require approval and a visible label.
5. **Verify** — read back every changed entity, refresh the preview, confirm rendered
   output, and update the ledger. Keep unverified items out of **Completed**.
6. **Human review** — present completed items, placeholders, blockers, and failures.
   `draft_ready` requires correct ownership, domain, type, and locale, no duplicate
   routes, verified content, disclosed placeholders, explicit Login and commerce
   status, and no readiness failure.
7. **Publish** — require explicit approval. Use a supported command, or return
   `needs_human` and resume after confirmed manual publication. Never publish
   automatically when no supported command exists.
8. **Live verification** — `published_verified` requires the expected public version
   and routes, working Login and account binding, and verified Web Shop and Launcher
   outcomes.
9. **Handoff** — repeat merchant ID, project ID, domain, Steam URL, and locale, with
   evidence for every completed item.

Status values: `completed`, `placeholder`, `needs_input`, `needs_access`,
`needs_human`, `blocked_capability`, `failed`.

The full specification — `GIVEN / WHEN / THEN` acceptance scenarios, the per-state
evidence contract, and the handoff report template — is in
[references/agentic-onboarding.md](references/agentic-onboarding.md). Load it before
issuing changes.

## Common pitfalls

1. **Duplicate pages and blocks on resume.** Onboarding an existing domain without
   reading the current structure first creates a second Home or Web Shop. Always
   discover and compare existing versus desired state before any mutation.
2. **HTTP 200 read as published.** A live URL can serve an older version. Publication
   stays incomplete until the expected version and routes are confirmed live.
3. **Login sign-in mistaken for Login done.** Sign-in can succeed while account
   binding fails. Both Login and onboarding remain incomplete until binding is
   verified.
4. **Launcher marked complete without a verified download.** A Launcher needs a real
   Launcher on the project, an uploaded build, a generated installer, and a verified
   installer download. Refuse publish-anyway when that evidence is missing.
5. **Access expiry losing progress.** On `401/403` mid-run, preserve the ledger and
   return `needs_access`, then reauthenticate, re-read state, and resume — do not
   restart the portal.
6. **Reporting completion without read-back.** Nothing enters **Completed** while
   read-back, rendered output, or end-to-end verification is pending.
