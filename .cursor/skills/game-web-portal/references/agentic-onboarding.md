# Xsolla Game Web Portal — Agentic Onboarding Specification

## Requirements

### Input

Collect missing required values in one question:

```yaml
merchant_id:
project_id:
domain:
game_name:
primary_locale:
existing_portal_policy: update | create-new
```

Optional: `store_url` (Steam), approved game description and brand assets,
analytics IDs, and locales. A Steam URL is a reference, not a production
dependency, and may be skipped. Metadata and assets come from the partner either
way, because Steam pages are not imported. Never invent or reuse partner
identifiers, credentials, content, prices, assets, or URLs.

### Acceptance scenarios

1. **Platform:** GIVEN no store URL, WHEN the title is confirmed as PC and
   approved metadata/assets are supplied, THEN continue without Steam parsing.
   GIVEN a store URL, its exact host must be `store.steampowered.com`; Mobile,
   unknown, invalid, or spoofed supplied URLs return `needs_input`.
2. **Existing portal:** GIVEN the domain exists, WHEN onboarding starts, THEN
   inspect and resume without duplicates; ambiguous matches require selection.
3. **Access:** GIVEN a mutation returns `401/403`, WHEN work is partial, THEN
   preserve the ledger, return `needs_access`, reauthenticate, re-read, resume.
4. **Login:** GIVEN sign-in succeeds, WHEN binding fails, THEN Login and
   onboarding remain incomplete until binding is verified.
5. **Publication:** GIVEN the draft is ready, WHEN the run ends, THEN the agent has
   not published, run the readiness check, or generated a preview, and the handoff
   lists those as `needs_human` steps for Publisher Account.
6. **Launcher:** GIVEN a Launcher exists, WHEN build, installer, or download
   evidence is missing, THEN Launcher is incomplete and publish-anyway is
   refused.
7. **Handoff:** GIVEN the run ends, WHEN reporting, THEN repeat merchant ID,
   project ID, domain, locale, and Steam URL only if supplied, with evidence for
   every Completed item.

## Design

### Flow

```mermaid
flowchart LR
  Intake --> Preflight
  Preflight --> Discover
  Discover --> Backup
  Backup --> Confirm
  Confirm --> Draft
  Draft --> Verify
  Verify --> HumanReview
  HumanReview --> Handoff
```

Readiness check, preview, publication, live verification and rollback come after the
handoff and belong to the human, in Publisher Account.

### Status

- `completed` — effect verified.
- `placeholder` — visible and temporary.
- `needs_input` — value or choice missing.
- `needs_access` — authorization invalid.
- `needs_human` — manual action required.
- `blocked_capability` — CLI cannot perform the action.
- `failed` — action failed or cannot be verified.

### Evidence contract

| State | Required evidence | Stop condition |
|---|---|---|
| Preflight | CLI context, PC confirmation, Steam host if supplied, domain search | Missing/ambiguous required input |
| Discover | Existing IDs, supported type and skills | Unsupported structure |
| Backup | Export directory of the existing site, before the first write | Export failed |
| Confirm | Explicit approval of the shown plan | Approval missing |
| Draft | Mutation response and read-back | Read-back mismatch |
| Verify | Structure and localization read back, matching the plan | Pending/failed verification |
| HumanReview | Approval and disclosed gaps | Approval missing |
| Handoff | Full context, statuses, evidence, human next steps | Completed lacks evidence |

### Existing vs desired

Before mutation:

| Existing state | Desired state | Action |
|---|---|---|
| Verified entity ID and values | Requested change | Create, update, ask, or stop |

Never recreate discovered existing entities.

## Run checklist

### 1. Context

- Confirm merchant/project, domain, locale, and create/update policy.
- Confirm PC scope. Validate the exact Steam host only when `store_url` is supplied.
- If `store_url` is omitted, confirm approved metadata and assets are available.
- Resolve ambiguity and disclose unsupported/human gates.

### 2. Existing state

- List websites and read the target structure.
- Capture landing, page, and block IDs.
- Compare existing and desired state.
- Resume at the first incomplete item.

### 3. One change group

Portal structure — creation and landing type, pages, blocks, theme, assets, copy
and localization, analytics — runs through the CLI commands listed in
[portal-api.md](portal-api.md). Use related skills for everything else,
instead of repeating their command recipes:

- `merchant-setup` — merchant/project/API key.
- `catalog-design` — catalog and pricing.
- `login-setup` — Login.
- `headless-checkout-integration` — checkout.

Sections: Home, News, Rewards, Web Shop, Community, optional Launcher.
Placeholders require approval and visible labels. Launcher requires a real
Launcher, uploaded build, generated installer, and verified download.

### 4. Verify

- Read back changed entities and compare them with the confirmed plan.
- Update the ledger.
- Keep unverified items out of **Completed**.

### 5. Draft gate

`draft_ready` requires correct ownership/domain/type/locale, no duplicate
routes, read-back-verified content, disclosed placeholders, and explicit
Login/commerce status.

### 6. Review and hand over

- Present Completed, placeholders, blockers, and failures.
- Hand the human, as `needs_human`: the readiness check, the preview, publication
  (per page, main page first), live verification, and any rollback.
- Never publish, run the readiness check, or generate a preview key.

### 7. After the human publishes

If the partner comes back after publishing, a resumed run may read the public site
and report what it sees. HTTP 200 with stale content is incomplete; the expected
version and routes, working Login and binding, and verified Web Shop/Launcher
outcomes are what the partner is asked to confirm.

### 8. Handoff

```markdown
# Xsolla Game Web Portal onboarding report

Overall status:

## Confirmed context
- Merchant ID:
- Project ID:
- Domain:
- Steam URL (optional; include only if supplied):
- Primary locale:

## Sections
| Section | Page ID | Route | Status | Evidence |
|---|---|---|---|---|

## Completed
- Verified action + evidence

## Placeholders
- Temporary content + label

## Needs input / human action
- Action + owner + value + verification

## Blocked capabilities
- Capability + impact + next step

## Failed
- Action + error + recovery

## Your next steps in Publisher Account
- Run the readiness check and open the preview
- Publish (main page first), then confirm the public URL
- Status: not published by the agent
```

Honest partial completion is correct. Simulated completion is failure.
