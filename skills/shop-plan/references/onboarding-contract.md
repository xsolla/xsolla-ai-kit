# The onboarding contract

One set of statuses, one ledger, one handoff report for the Shop Builder part of onboarding.
`shop-plan` asks the intake and starts the ledger; the storefront skills that follow this
contract — `game-web-portal` — record their steps and render the handoff report.
`description-to-shop` and `shop-builder-assembly` don't follow it yet: on the shop path they ask
for what they need themselves. `shop-setup` and the skills it runs are not changed by this
contract: what they did is read back from the project when a storefront skill starts.

Honest partial completion is correct. Simulated completion is failure.

## The flow

```text
shop-plan (intake, path, site kind)
→ shop-setup: merchant-setup → catalog-design → login-setup
→ storefront: description-to-shop / shop-builder-assembly, or game-web-portal for a portal
→ verify → human review → handoff report
→ shop-setup continues: webhooks-impl → production
```

The path and the site kind are defined in [the build-path contract](build-path-contract.md).
The headless path has no ledger: nothing on it reads one.

## Intake

The values the Shop Builder part needs are asked **once, in one message**: `shop-plan`'s first
message, together with its criteria. Skip what the developer already stated, and show inferred
values back instead of assuming them.

| Group | Values | Used by |
|---|---|---|
| Plan | `shop-plan`'s criteria: the path, and on Shop Builder the site kind | `shop-plan` |
| Game | name, platforms, an approved short description, store URL (optional), brand assets (optional) | the storefront skills |
| Site | the site's domain — for a portal, the site the partner creates from the Multi-page web portal template — and the primary and other locales | the storefront skills |

The account, catalog, sign-in methods and webhooks are not part of this intake:
`merchant-setup`, `catalog-design`, `login-setup` and `webhooks-impl` ask for them themselves.

Values are written to the ledger when the developer confirms the plan, in the same step that
records the path and the site kind. After that, the storefront skills read them from the ledger
and ask again only for a value that is missing, that conflicts with what a step finds, that a
destructive change needs, or that is an approval.

## Statuses

Every step carries exactly one:

| Status | Meaning |
|---|---|
| `completed` | The effect is verified and its evidence is recorded |
| `placeholder` | Visible, temporary content the developer approved |
| `needs_input` | A value or choice is missing |
| `needs_access` | Authorization is missing, invalid, or expired |
| `needs_human` | A manual action is required — the developer's, in Publisher Account or their own systems |
| `blocked_capability` | No CLI command or supported API can do it; the gap is reported |
| `failed` | The action failed or cannot be verified |

A step is `completed` only when its evidence below has been observed in this run or
re-read on resume. A mutation response is a receipt, not evidence. Anything not yet
verified stays out of `completed`.

## Steps and their evidence

| Step | Done by | `completed` when | Re-read on resume |
|---|---|---|---|
| `intake` | `shop-plan` | Every required intake value is in the ledger | The ledger |
| `plan` | `shop-plan` | `XSOLLA_BUILD_PATH` is `shopbuilder` and `XSOLLA_SITE_KIND` is valid | The build-path contract's checks |
| `merchant` | `merchant-setup` | `XSOLLA_MERCHANT_ID`, `XSOLLA_PROJECT_ID`, `XSOLLA_PROJECT_API_KEY` are in `.env` and the project answers an authenticated read | The same read |
| `catalog` | `catalog-design` | Every catalog group the site uses reads back from the project | Read each group |
| `login` | `login-setup` | `XSOLLA_LOGIN_PROJECT_ID` is set and the Login project reads back | Read the Login project |
| `storefront` | the storefront skill | Its read-back matches the confirmed plan | The same read-back |
| `verify` | the storefront skill | The site was exported to a new local directory before its first write, and read back after the last write | The export directory and a fresh read-back |
| `review` | the developer | The developer approved the draft, with every placeholder and gap disclosed | The ledger |
| `handoff` | the storefront skill | The report below was rendered from the ledger | — |

`merchant`, `catalog` and `login` are done by `shop-setup`'s skills, which don't write the
ledger. The storefront skill records them when it starts, from the project's actual state
(Resume, rule 4).

## The ledger

| | |
|---|---|
| **File** | `.xsolla/onboarding.json` in the project root |
| **Git** | Ignored: add `.xsolla/` to the project's `.gitignore` before the first write |
| **Written by** | `shop-plan` first — the intake, path and site kind, when the developer confirms the plan — then the storefront skills, for their steps and the steps they discover |
| **Holds** | The intake values, the path, the site kind, and one entry per step. Never a secret — API keys, the webhook secret, and session values stay in `.env` and are referred to by name |

```json
{
  "version": 1,
  "path": "shopbuilder",
  "site_kind": "portal",
  "intake": { "game_name": "…", "primary_locale": "en-US" },
  "steps": [
    {
      "id": "merchant",
      "status": "completed",
      "evidence": ["XSOLLA_PROJECT_ID set in .env", "project read: 200"],
      "ids": { "merchant_id": 0, "project_id": 0 },
      "updated_at": "2026-01-01T00:00:00Z"
    },
    {
      "id": "storefront",
      "status": "completed",
      "evidence": ["/community read back as planned"],
      "ids": {
        "site": "my-game",
        "landing_id": "…",
        "created_pages": [
          {
            "page_id": "…",
            "path": "/community",
            "seeded_blocks": [{ "_id": "…", "module": "faq", "hash": "…" }]
          }
        ]
      },
      "updated_at": "2026-01-01T00:00:00Z"
    }
  ]
}
```

Update a step's entry after every step, including a `failed` or `needs_*` one, with the
reason in `evidence`. `ids` holds what later steps and a resume need: project, Login
project, catalog groups, site domain and landing `_id`, and every page the agent created,
with the seeded blocks it found there. `game-web-portal` records those with
[`scripts/seeded_blocks.py record`](../../game-web-portal/scripts/seeded_blocks.py) right after
it creates the page. The `merchant` step records the merchant and project; a resumed run
uses them, with the recorded pages, to tell its own pages from the partner's.

## Resume

On every start of a storefront skill that follows this contract, before any write:

1. **Read the ledger.** If its `path` or `site_kind` differs from `.env`, stop and show both —
   never pick one.
2. **Re-read every `completed` step** using the last column of the evidence table. If the
   evidence no longer holds, downgrade the step to `failed` (or `needs_access` on
   `401/403`) and say why.
3. **Continue from the first step that is not `completed`.** Never repeat a completed step's
   writes.
4. **A step with no entry, but Xsolla state that shows it** (credentials in `.env`, a Login
   project, an existing site at the domain): discover it, record the step if its evidence
   verifies, then continue as in 3.
5. **Seeded blocks on a page an earlier run created** are removed only on the same merchant
   and project, and only while `seeded_blocks.py check` reports them untouched. A changed or
   gone block stays, and is listed for the partner as `needs_human`.

### No duplicates

Before any create, a storefront skill looks the entity up by its natural key and reuses what
is there:

| Entity | Natural key |
|---|---|
| Site | domain |
| Page | path |
| Block | module and position on its page |

A match that is ambiguous is `needs_input`, never a guess.

## Hard stops

The storefront skills that follow this contract never:

- publish a site, page, article, or widget;
- switch a project, token, or SDK to production;
- run the Shop Builder readiness check (`verify-website`) or enable or generate a preview;
- save or apply a site version;
- write to the project before the developer explicitly confirmed the plan for that write;
- target a project that is not on the approved test-project allowlist.

## Handoff report

Rendered from the ledger by the storefront skill at the end of its part, including a partial
run:

```markdown
# Xsolla onboarding report

Overall status:
Site kind:

## Confirmed context
- Merchant ID:
- Project ID:
- Login project ID:
- Site domain:
- Locales:

## Steps
| Step | Status | Evidence |
|---|---|---|

## Storefront
Site-kind detail — for a portal, its section table.

## Placeholders
- Temporary content + label

## Needs input / your action
- Action + owner + value + how to verify

## Blocked capabilities
- Capability + impact + next step

## Failed
- Action + error + recovery

## Your next steps
- Review and publish in Publisher Account
- Continue with `shop-setup`: `webhooks-impl`, then `production`
```
