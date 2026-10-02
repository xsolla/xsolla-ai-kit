# The onboarding contract

One flow, one set of statuses, one ledger, one handoff report — for every storefront
path. `shop-setup` runs the flow; each step's skill does the work; this file defines what
counts as done, what is recorded, and how an interrupted run resumes. Skills are not
rewritten to follow it: `shop-setup` maps each skill's outcome onto it.

Honest partial completion is correct. Simulated completion is failure.

## The flow

```text
Intake → shop-plan → merchant-setup → catalog-design → login-setup → storefront
→ webhooks-impl → verify → human review → production checklist → handoff
```

The storefront step depends on the recorded build path (see
[the build-path contract](../../shop-plan/references/build-path-contract.md)).

## Intake

Every value the flow needs is asked **once, in one message**, at the start of a fresh project:
`shop-plan`'s first message, together with its criteria, so planning asks nothing new. Skip what
the developer already stated, and show inferred values back instead of assuming them.

| Group | Values | Used by |
|---|---|---|
| Game | name, platforms, an approved short description, store URL (optional), brand assets (optional) | catalog-design, storefront |
| Account | merchant ID and project ID, or "no account yet" | merchant-setup |
| Build path | `shop-plan`'s criteria | shop-plan |
| Storefront | site slug or domain, primary locale and other locales, `update` or `create-new` for an existing site | storefront |
| Catalog | what the game sells, or where the catalog is described | catalog-design |
| Login | sign-in methods | login-setup |
| Webhooks | the listener URL, or "none yet", and how goods are granted in the game | webhooks-impl |

Values are written to the ledger when the developer confirms the plan, in the same step that
records the build path. After that, every step reads them from the ledger. Ask again only for a
value that is missing, that conflicts with what a step finds, that a destructive change needs,
or that is an approval. A skill that asks for a value the ledger already holds gets it from the
ledger, not from the developer.

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

| Step | Run by | `completed` when | Re-read on resume |
|---|---|---|---|
| `intake` | `shop-setup` | Every required intake value is in the ledger | The ledger |
| `plan` | `shop-plan` | `XSOLLA_BUILD_PATH` holds a valid path | The build-path check |
| `merchant` | `merchant-setup` | `XSOLLA_MERCHANT_ID`, `XSOLLA_PROJECT_ID`, `XSOLLA_PROJECT_API_KEY` are in `.env` and the project answers an authenticated read | The same read |
| `catalog` | `catalog-design` | Every planned SKU and group reads back from the project | Read each SKU |
| `login` | `login-setup` | `XSOLLA_LOGIN_PROJECT_ID` is set and the Login project reads back with the planned methods enabled | Read the Login project |
| `storefront` | per path | `headless`: the **Validate** line of each of Phases 1–5 in `shop-setup` holds · `shopbuilder`: `shop-builder-assembly`'s structure check passes against the confirmed plan · `portal`: `game-web-portal`'s read-back matches the confirmed plan | The same checks |
| `webhooks` | `webhooks-impl` | Fixture replay passes: a tampered body is rejected, `user_validation` answers, a replayed order grants once | Replay the fixtures |
| `verify` | `shop-setup` | Shop Builder and portal: an existing site was backed up with `shop-builder-assembly`'s `backup_shop.py` before its first write (a new site has nothing to back up), and the site was read back after the last write. Headless: the storefront evidence above | The backup directory, if any, and a fresh read-back |
| `review` | the developer | The developer approved the draft, with every placeholder and gap disclosed | The ledger |
| `production` | the developer | Never set by the agent — the `production` checklist is handed over and the step stays `needs_human` until the developer confirms it | The ledger |
| `handoff` | `shop-setup` | The report below was rendered from the ledger | — |

## The ledger

| | |
|---|---|
| **File** | `.xsolla/onboarding.json` in the project root |
| **Git** | Ignored: add `.xsolla/` to the project's `.gitignore` before the first write |
| **Written by** | `shop-setup` only — first when the developer confirms the plan, which records the intake with it |
| **Holds** | The intake values, the build path, and one entry per step. Never a secret — API keys, the webhook secret, and session values stay in `.env` and are referred to by name |

```json
{
  "version": 1,
  "path": "portal",
  "intake": { "game_name": "…", "primary_locale": "en-US" },
  "steps": [
    {
      "id": "merchant",
      "status": "completed",
      "evidence": ["XSOLLA_PROJECT_ID set in .env", "project read: 200"],
      "ids": { "merchant_id": 0, "project_id": 0, "environment": "test" },
      "updated_at": "2026-01-01T00:00:00Z"
    }
  ]
}
```

Update the step's entry after every step, including a `failed` or `needs_*` one, with the
reason in `evidence`. `ids` holds what later steps and a resume need: project, Login
project, SKUs, site slug and landing `_id`, page IDs, and which of those pages the agent
created. The `merchant` step records the merchant, project and environment (`sandbox` or
`test`); together they let a resumed run tell its own pages from the partner's, as
`game-web-portal` requires before it removes seeded blocks.

## Resume

On every start, before any write:

1. **Read the ledger.** If its `path` differs from `XSOLLA_BUILD_PATH`, stop and show both —
   never pick one.
2. **Re-read every `completed` step** using the last column of the evidence table. If the
   evidence no longer holds, downgrade the step to `failed` (or `needs_access` on
   `401/403`) and say why.
3. **Continue from the first step that is not `completed`.** Never repeat a completed step's
   writes.
4. **No ledger, but Xsolla state exists** (credentials in `.env`, an existing site at the
   slug): discover it, record each step whose evidence verifies, then continue as in 3.

### No duplicates

Before any create, look the entity up by its natural key and reuse what is there:

| Entity | Natural key |
|---|---|
| Project | `XSOLLA_PROJECT_ID` |
| Catalog item, bundle, package | SKU |
| Item group | external ID |
| Site | slug / domain |
| Page | path |
| Block | module and position on its page |

A match that is ambiguous is `needs_input`, never a guess.

## Hard stops

The agent never:

- publishes a site, page, article, or widget;
- switches a project, token, or SDK to production — the `production` step is a handoff;
- runs the Shop Builder readiness check (`verify-website`) or enables or generates a
  preview;
- applies a saved site version;
- writes before the developer explicitly confirmed the plan for that write;
- targets a project that is not sandbox or a dedicated test project.

## Handoff report

Rendered from the ledger at the end of every run, including a partial one:

```markdown
# Xsolla onboarding report

Overall status:
Build path:

## Confirmed context
- Merchant ID:
- Project ID:
- Login project ID:
- Site slug / domain (Shop Builder and portal):
- Locales:

## Steps
| Step | Status | Evidence |
|---|---|---|

## Storefront
Path-specific detail — for the portal, its section table.

## Placeholders
- Temporary content + label

## Needs input / your action
- Action + owner + value + how to verify

## Blocked capabilities
- Capability + impact + next step

## Failed
- Action + error + recovery

## Your next steps
- Review and publish in Publisher Account (Shop Builder and portal)
- Go live with the `production` checklist
```
