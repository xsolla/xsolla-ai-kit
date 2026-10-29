# The onboarding contract

One set of statuses, one ledger, one handoff report for the shop created on Xsolla's side.
`nocode-shop-setup` confirms that path and whether the site is a store or a game home, and
starts the ledger when a project directory exists. The storefront skills that follow this
contract — `game-web-portal` — record their steps and render the handoff report.
`description-to-shop` reads the confirmed intake on the store path and asks only for missing
data or conflicts. It does not write ledger steps; `shop-builder-assembly` does not yet
write the ledger or render its handoff report. `shop-setup`, the shop the user codes, has no
ledger: what those skills did is read back from the project when a storefront skill starts.

Honest partial completion is correct. Simulated completion is failure.

## The flow

```text
nocode-shop-setup (store or game home)
→ merchant-setup → catalog-design → login-setup
→ storefront: description-to-shop / shop-builder-assembly, or game-web-portal for a game home
→ game-web-portal only: verify → human review → handoff report
→ webhooks-impl
```

`site_kind` is `shop` or `portal`. It lives in the ledger when a project directory exists.
It is not written to `.env`. The shop the user codes (`shop-setup`) has no ledger.

## Intake

The values the Xsolla-hosted shop needs are asked once. `game-web-portal` and
`description-to-shop` reuse the recorded answers, asking only for missing data or conflicts.
Skip what the developer already stated or their own store listing states, and show inferred
values back instead of assuming them.

| Group | Ledger keys | Used by |
|---|---|---|
| Plan | `site_kind`: `shop` or `portal`. Not a build path in `.env` | `nocode-shop-setup` |
| Game | `game_name`, `platforms`, `description` (approved), `store_url` (optional: the developer's own App Store, Google Play or Steam listing, read for the other game values; never found by searching the name), `brand_assets` (optional) | `game-web-portal`, `description-to-shop` |
| Site | `domain` (optional: the target site may not exist yet), `primary_locale`, `locales` | `game-web-portal`, `description-to-shop` |

The account, catalog, sign-in methods and webhooks are not part of this intake:
`merchant-setup`, `catalog-design`, `login-setup` and `webhooks-impl` ask for them themselves.

`nocode-shop-setup` records `site_kind` and any intake already known when a project directory
exists, and only after the user confirms the shop is on Xsolla's side. With no project
directory, the answers stay in the conversation. After that,
`game-web-portal` and `description-to-shop` read them from the ledger and ask again only for a value that is missing
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
verified stays out of `completed`. A step that is under way has no `status` key yet, not
`partial`, `in_progress` or any other word; its `ids` may already hold what it created.

## Steps and their evidence

| Step | Done by | `completed` when | Re-read on resume |
|---|---|---|---|
| `intake` | `nocode-shop-setup` | Every required intake value is in the ledger, or was given in the conversation when there is no project directory | The ledger, or the conversation |
| `plan` | `nocode-shop-setup` | The user confirmed the shop is created on Xsolla's side, and `site_kind` is `shop` or `portal` | The ledger when it exists; otherwise the conversation |
| `merchant` | `merchant-setup` | Merchant id, project id, and project API key are known — in `.env` for a shop the user codes, or in the chat for a shop with no repo — and the project answers an authenticated read | The same read |
| `catalog` | `catalog-design` | Every catalog group the site uses reads back from the project | Read each group |
| `login` | `login-setup` | `XSOLLA_LOGIN_PROJECT_ID` is set and the Login project reads back | Read the Login project |
| `storefront` | the storefront skill | Its read-back matches the confirmed plan | The same read-back |
| `verify` | the storefront skill | The site was exported to a new `.xsolla/backup-<timestamp>/` directory before its first write, and read back after the last write | The export directory and a fresh read-back |
| `review` | the developer | The developer approved the draft, with every placeholder and gap disclosed | The ledger |
| `handoff` | the storefront skill | The report below was rendered from the ledger | — |

`merchant`, `catalog` and `login` are done by the skills `nocode-shop-setup` runs, which don't
write the ledger. The storefront skill records them when it starts, from the project's actual
state (Resume, rule 4).

## The ledger

| | |
|---|---|
| **File** | `.xsolla/onboarding.json` in the project root |
| **Git** | Ignored: add `.xsolla/` to the project's `.gitignore` before the first write |
| **Written by** | `nocode-shop-setup` first, when a project directory exists — `site_kind` and intake, after the user confirms — then the storefront skills, for their steps and the steps they discover |
| **Holds** | The intake values, the site kind, and one entry per step. Never a secret, and never the build path. API keys stay in `.env` when the shop has a repo, or in the chat when it does not |

```json
{
  "version": 1,
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

Every step has an `id`, an `evidence` list, an `ids` object (`{}` when the step created
nothing) and `updated_at`, and gets a `status` when it finishes. Update a step's entry after
every step, including a `failed` or `needs_*` one, with the reason in `evidence`. `ids` holds
what later steps and a resume need: project, Login project, catalog groups, and on the
storefront step the merchant, project, site domain and landing `_id` it worked on, with every
page the agent created. `game-web-portal` records each page — its path and seeded blocks — with
[`scripts/seeded_blocks.py record`](../../game-web-portal/scripts/seeded_blocks.py) right after
it creates it, and updates the entry after hiding its seeded blocks.

## Resume

On every start of a storefront skill that follows this contract, before any write:

1. **Read the ledger.** `site_kind` comes from the ledger, not from `.env`. If the user now
   wants the other kind, stop and ask — `nocode-shop-setup` confirms it. Never pick one.
2. **Re-read every `completed` step** using the last column of the evidence table. If the
   evidence no longer holds, downgrade the step to `failed` (or `needs_access` on
   `401/403`) and say why.
3. **Continue from the first step that is not `completed`.** Never repeat a completed step's
   writes.
4. **A step with no entry, but Xsolla state that shows it** (credentials in `.env` or given in this chat, a Login
   project, an existing site at the domain): discover it, record the step if its evidence
   verifies, then continue as in 3.
5. **A seeded block is hidden, never deleted,** only on a page the agent created and
   recorded, only when the storefront step's merchant, project and landing equal the
   preflight-confirmed target, and only when `seeded_blocks.py check`, on reads taken right
   before hiding, reports it `untouched`. A `changed` block stays as it is and is listed for
   the partner as `needs_human`; a `gone` one needs nothing. Hiding changes the block, so a
   recorded seeded block that reads `hidden: true` reads as `changed` and counts as done. The
   partner deletes the hidden blocks in the builder (`needs_human`). A page at a planned path
   with no record is never trimmed: it is reported, with its blocks, as `needs_human`.

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
- delete a block, or hide a block other than a recorded seeded block that rule 5 allows;
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
