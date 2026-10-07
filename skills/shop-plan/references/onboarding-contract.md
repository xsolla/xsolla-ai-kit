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
→ game-web-portal only: verify → human review → handoff report
→ shop-setup continues: webhooks-impl → production
```

The path and the site kind are defined in [the build-path contract](build-path-contract.md).
The headless path has no ledger: nothing on it reads one.

## Intake

The values the Shop Builder part needs are asked in one message: `shop-plan`'s first message,
together with its criteria. For a portal, nothing in it is asked again; on the shop path,
`description-to-shop` still asks for what it needs. Skip what the developer already stated, and
show inferred values back instead of assuming them.

| Group | Ledger keys | Used by |
|---|---|---|
| Plan | `shop-plan`'s criteria: the path, and on Shop Builder the site kind | `shop-plan` |
| Game | `game_name`, `platforms`, `description` (approved), `store_url` (optional), `brand_assets` (optional) | `game-web-portal` |
| Site | `domain` (optional: the site the partner creates from the Multi-page web portal template may not exist yet), `primary_locale`, `locales` | `game-web-portal` |

The account, catalog, sign-in methods and webhooks are not part of this intake:
`merchant-setup`, `catalog-design`, `login-setup` and `webhooks-impl` ask for them themselves.

`shop-plan` shows the values with its recommendation, and writes them to the ledger when the
developer confirms, in the same step that records the path and the site kind. After that,
`game-web-portal` reads them from the ledger and asks again only for a value that is missing
(such as a domain that didn't exist yet), that conflicts with what a step finds, that a
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
verified stays out of `completed`. A step that is under way has no status yet; its `ids` may
already hold what it created.

## Steps and their evidence

| Step | Done by | `completed` when | Re-read on resume |
|---|---|---|---|
| `intake` | `shop-plan` | Every required intake value is in the ledger | The ledger |
| `plan` | `shop-plan` | `XSOLLA_BUILD_PATH` is `shopbuilder` and `XSOLLA_SITE_KIND` is valid | The build-path contract's checks |
| `merchant` | `merchant-setup` | `XSOLLA_MERCHANT_ID`, `XSOLLA_PROJECT_ID`, `XSOLLA_PROJECT_API_KEY` are in `.env` and the project answers an authenticated read | The same read |
| `catalog` | `catalog-design` | Every catalog group the site uses reads back from the project | Read each group |
| `login` | `login-setup` | `XSOLLA_LOGIN_PROJECT_ID` is set and the Login project reads back | Read the Login project |
| `storefront` | the storefront skill | Its read-back matches the confirmed plan | The same read-back |
| `verify` | the storefront skill | The site was exported to a new `.xsolla/backup-<timestamp>/` directory before its first write, and read back after the last write | The export directory and a fresh read-back |
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
  "intake": { "game_name": "…", "domain": "my-game", "primary_locale": "en-US" },
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
        "merchant_id": 0,
        "project_id": 0,
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
project, catalog groups, and on the storefront step the merchant, project, site domain and
landing `_id` it worked on, with every page the agent created. `game-web-portal` records each
page — its path and seeded blocks — with
[`scripts/seeded_blocks.py record`](../../game-web-portal/scripts/seeded_blocks.py) right after
it creates it, and updates the entry after each removal.

## Resume

On every start of a storefront skill that follows this contract, before any write:

1. **Read the ledger.** If its `path` or `site_kind` differs from `.env`, stop, show both, and
   ask the developer to rerun `shop-plan` — never pick one.
2. **Re-read every `completed` step** using the last column of the evidence table. If the
   evidence no longer holds, downgrade the step to `failed` (or `needs_access` on
   `401/403`) and say why.
3. **Continue from the first step that is not `completed`.** Never repeat a completed step's
   writes.
4. **A step with no entry, but Xsolla state that shows it** (credentials in `.env`, a Login
   project, an existing site at the domain): discover it, record the step if its evidence
   verifies, then continue as in 3.
5. **A seeded block is removed** only on a page the agent created and recorded, only when the
   storefront step's merchant, project and landing equal the preflight-confirmed target, and
   only when `seeded_blocks.py check`, on reads taken right before the removal, reports it
   `untouched`. A `changed` block stays and is listed for the partner as `needs_human`; a
   `gone` one needs nothing. A page at a planned path with no record is never trimmed: it is
   reported, with its blocks, as `needs_human`.

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
- delete a block other than a recorded seeded block that rule 5 allows;
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
