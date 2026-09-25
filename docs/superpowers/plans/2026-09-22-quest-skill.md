# Quest Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `skills/quest-setup/`, a markdown skill that lets an agent create, inspect and edit Xsolla Quest Platform quests conversationally, submit one quest event, and verify the resulting execution.

**Architecture:** Markdown only, no executable code, matching every other skill in this repository. The skill gets routes and the envelope from the services' live OpenAPI documents at runtime, and carries in `references/` only the contract the generator cannot see, because `Node.Parameters` and `IssueRewardParams.Body` are `json.RawMessage`. Delivered as a seven-branch git stack, each branch leaving CI green on its own.

**Tech Stack:** Markdown with YAML frontmatter; `python3 .github/scripts/validate_skills.py` as the gate; `curl` and `python3` for live contract checks against three internal stage services.

**Spec:** `docs/superpowers/specs/2026-09-22-quest-skill-design.md`

## Global Constraints

- Skill directory is `skills/quest-setup/`; frontmatter `name` must equal the directory name.
- `metadata.owner: r.aliyev`, `metadata.domain: quests`, `metadata.status: draft`.
- `description` must be at most 1536 characters, or trailing trigger keywords are silently dropped from the skill listing.
- `SKILL.md` target is around 200 lines. The validator warns above 500 and never blocks.
- No raw `curl` commands in skill text. Describe intent plus the Xsolla API operation.
- Every relative link in any markdown file under the repository must resolve, including files under `docs/`.
- `.cursor/skills/<name>/<file>` must exist and be **byte-identical** to `skills/<name>/<file>`; extra files in the mirror are an error.
- `CLAUDE.md` must be **byte-identical** to `AGENTS.md`.
- The skill name must appear in both `skills/README.md` and `AGENTS.md`.
- Environment variables are exactly `XSOLLA_MERCHANT_ID` and `XSOLLA_PROJECT_API_KEY`. No new variable names, now or later.
- Credential goes in `Authorization: Basic base64(merchant_id:api_key)`. This lane is **not accepted yet**; it lands in QP-2862.
- Hosts, written literally, never in an environment variable:
  - `https://qp-server.nl-k8s-stage.srv.local`
  - `https://qp-events-collector.nl-k8s-stage.srv.local`
  - `https://qp-data.nl-k8s-stage.srv.local`
- All three hosts are internal; they resolve only on the corporate network.
- Never state that a Web3 reward was delivered. The skill may assert that an event was accepted and that a quest executed, and nothing beyond that.

### The sync command

Several tasks regenerate the provider mirror. This is the exact logic from `.github/workflows/sync-providers.yml`, and it is the only correct way to produce those files:

```bash
rm -rf .cursor/skills
mkdir -p .cursor/skills
for skill_dir in skills/*/; do
  skill_name=$(basename "$skill_dir")
  if [ -f "${skill_dir}SKILL.md" ]; then
    cp -R "$skill_dir" ".cursor/skills/${skill_name}"
  fi
done
cp AGENTS.md CLAUDE.md
```

Save it once as a shell function at the start of the work so each task can call it:

```bash
sync_providers() {
  rm -rf .cursor/skills
  mkdir -p .cursor/skills
  for skill_dir in skills/*/; do
    skill_name=$(basename "$skill_dir")
    if [ -f "${skill_dir}SKILL.md" ]; then
      cp -R "$skill_dir" ".cursor/skills/${skill_name}"
    fi
  done
  cp AGENTS.md CLAUDE.md
}
```

## File Structure

| File | Responsibility | Task |
|---|---|---|
| `.github/scripts/validate_skills.py` | add `quests` domain and `r.aliyev` owner; make `check_links` skip fenced code | 1 |
| `CONTRIBUTING-skills.md` | document the domain list truthfully | 1 |
| `.git/info/exclude` | stop excluding a directory that is moving out | 1 |
| `skills/quest-setup/SKILL.md` | when to use, prerequisites, source-of-truth rule, flow, safety stops, errors | 2, 6, 7 |
| `skills/README.md` | registry row | 2 |
| `AGENTS.md` | inventory row plus trigger line | 2 |
| `skills/quest-setup/references/quest-document.md` | the quest graph: fields, nodes, connections, conditional requirements, full PUT | 3 |
| `skills/quest-setup/references/node-subtypes.md` | the 7 accepted subtypes and their `parameters` | 3 |
| `skills/quest-setup/references/conditions.md` | condition grammar: types, operands, operators | 4 |
| `skills/quest-setup/references/rewards.md` | the 9 reward bodies | 5 |
| `skills/quest-setup/references/events.md` | qp-events-collector contract | 6 |
| `skills/quest-setup/references/verification.md` | qp-data execution read-back | 7 |
| `skills/quest-setup/references/auth-and-environment.md` | the single place naming hosts, header and credential | 2 |

`auth-and-environment.md` lands in Task 2 rather than last, because it is the seam: every later file refers to "an authenticated QP request" and must have somewhere to point.

## Branch stack

Each branch targets the one above it. Rebase downward after any change to an earlier branch.

```
main
└─ QP-2888-repo-groundwork          Task 1
   └─ QP-2890-skill-skeleton        Task 2
      └─ QP-2890-quest-document     Task 3
         └─ QP-2890-conditions      Task 4
            └─ QP-2890-rewards      Task 5
               └─ QP-2890-events    Task 6
                  └─ QP-2890-verification   Task 7
```

If the Jira split proposed alongside this plan is applied, rename branches to the new keys before opening MRs. The stack shape does not change.

---

### Task 1: Repository groundwork

Three things the skill needs before it can exist: the `quests` domain, the `r.aliyev` owner, and a validator that reports real failures instead of 145 false ones. Touches nothing under `skills/`, so no provider mirror is involved. Worth merging even if the skill never ships.

**Files:**
- Modify: `.github/scripts/validate_skills.py:161-172` (`check_links`), `:35-43` (VALID_OWNERS), `:44-53` (VALID_DOMAINS)
- Modify: `CONTRIBUTING-skills.md:47` (the `domain:` line in the frontmatter example)
- Modify: `.git/info/exclude` (remove the now-obsolete entry)
- Move: `docs/superpowers/qp-2815/` out of the repository tree

**Interfaces:**
- Consumes: nothing.
- Produces: `VALID_DOMAINS` contains `quests`; `VALID_OWNERS` contains `r.aliyev`; `check_links` ignores fenced code. Task 2 depends on all three, and on the validator reporting 0 errors so that new failures are visible.

- [ ] **Step 1: Record the failing baseline**

```bash
cd /Users/raufaliyev/GolandProjects/xsolla-ai-kit
python3 .github/scripts/validate_skills.py 2>&1 | tail -1
```

Expected: `Checked 8 skills: 145 new error(s), 0 known debt, 0 warning(s).`

All 145 are "broken relative link", from two causes, and both are false:

- **136 from `docs/superpowers/qp-2815/*.md`** — research notes citing source locations as absolute paths like `/Users/.../web3_api.go:175`, which the regex reads as relative links. The validator walks the filesystem, not the git index, so the `.git/info/exclude` entry does not hide them.
- **9 from `docs/superpowers/plans/2026-09-22-quest-skill.md`** — this plan, quoting the lines you are about to paste into `SKILL.md`. Those links resolve from `skills/quest-setup/`, just not from the directory the plan lives in.

- [ ] **Step 2: Fix the fenced-code false positive in `check_links`**

`check_links` runs one regex over the whole file with no idea that fenced code exists, so any markdown that *documents* a link fails. That is a repository-wide bug: it punishes exactly the skill author who shows a contributor which line to paste. Fix it here, because this task already opens the file.

Replace the head of `check_links`. Find:

```python
    pattern = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
    for md in ROOT.rglob("*.md"):
        if any(part in {".git", "node_modules"} for part in md.parts):
            continue
        for target in pattern.findall(md.read_text(encoding="utf-8")):
```

Replace with:

```python
    pattern = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
    # Strip fenced code blocks first. A file that *documents* a link — showing an
    # author which line to paste into some other file — is not itself linking, and
    # resolving those targets against the wrong directory is a false failure.
    fence = re.compile(r"^(`{3,}|~{3,})", re.MULTILINE)
    for md in ROOT.rglob("*.md"):
        if any(part in {".git", "node_modules"} for part in md.parts):
            continue
        text = md.read_text(encoding="utf-8")
        out, marker = [], None
        for line in text.splitlines():
            m = fence.match(line)
            if marker is None:
                if m:
                    marker = m.group(1)
                else:
                    out.append(line)
            elif m and line.startswith(marker):
                marker = None
        text = "\n".join(out)
        for target in pattern.findall(text):
```

The closing-fence test is `line.startswith(marker)` rather than equality, so a block opened with ```` ``` ```` is not closed by an inner ```` ```python ````, and a four-backtick block correctly survives three-backtick blocks nested inside it. This plan relies on that nesting.

- [ ] **Step 3: Confirm only the research-note errors remain**

```bash
python3 .github/scripts/validate_skills.py 2>&1 | tail -1
python3 .github/scripts/validate_skills.py 2>&1 | grep -c "plans/2026-09-22-quest-skill.md"
```

Expected: `Checked 8 skills: 136 new error(s), 0 known debt, 0 warning(s).` and then `0`.

- [ ] **Step 4: Move the research notes out of the tree**

They are local-only notes, they are never published, and their only effect inside the tree is to mask real errors. Changing a shared validator to tolerate private drafts would be the wrong fix; Step 2 fixed a real bug, this is just cleanup.

```bash
mkdir -p /Users/raufaliyev/GolandProjects/qp-2815-research
mv docs/superpowers/qp-2815/* /Users/raufaliyev/GolandProjects/qp-2815-research/
rmdir docs/superpowers/qp-2815
```

- [ ] **Step 5: Drop the obsolete exclude entry**

The last line of `.git/info/exclude` is `/docs/superpowers/qp-2815/` and now points at nothing.

```bash
python3 - <<'PY'
from pathlib import Path
p = Path(".git/info/exclude")
lines = [l for l in p.read_text().splitlines(keepends=True)
         if l.strip() != "/docs/superpowers/qp-2815/"]
p.write_text("".join(lines))
PY
```

- [ ] **Step 6: Run the validator to confirm it is clean**

```bash
python3 .github/scripts/validate_skills.py 2>&1 | tail -1
```

Expected: `Checked 8 skills: 0 new error(s), 0 known debt, 0 warning(s).`

If the count is not 0, the remaining errors are real and must be read before continuing. Do not proceed with a non-zero count.

- [ ] **Step 7: Add the owner and the domain**

In `.github/scripts/validate_skills.py`, add one entry to each set, keeping the existing style.

```python
VALID_OWNERS = {
    "mohammed_abujalala",
    "y.klochikhin",
    "y-klochikhin",
    "p.sanachev",
    "elnur_khalilov",
    "e.chernykh",
    "r.aliyev",
}

VALID_DOMAINS = {
    "catalog",
    "payments",
    "login",
    "webhooks",
    "store",
    "design",
    "orchestrator",
    "go-live",
    "quests",
}
```

- [ ] **Step 8: Fix the stale domain list in the contribution guide**

`CONTRIBUTING-skills.md` documents the domain enum and is already wrong: it omits `go-live`, which the validator has accepted for some time. Replace the `domain:` line in the frontmatter example.

Find:

```
  domain: catalog|payments|login|webhooks|store|design|orchestrator
```

Replace with:

```
  domain: catalog|payments|login|webhooks|store|design|orchestrator|go-live|quests
```

- [ ] **Step 9: Prove the new values are actually accepted**

A set literal is easy to get wrong in a way the validator will not notice until Task 2. Check directly.

```bash
python3 -c "
import importlib.util
spec = importlib.util.spec_from_file_location('v', '.github/scripts/validate_skills.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
assert 'quests' in m.VALID_DOMAINS, 'quests missing from VALID_DOMAINS'
assert 'r.aliyev' in m.VALID_OWNERS, 'r.aliyev missing from VALID_OWNERS'
print('ok: quests and r.aliyev accepted')
"
```

Expected: `ok: quests and r.aliyev accepted`

- [ ] **Step 10: Run the validator again**

```bash
python3 .github/scripts/validate_skills.py 2>&1 | tail -1
```

Expected: `Checked 8 skills: 0 new error(s), 0 known debt, 0 warning(s).`

- [ ] **Step 11: Commit**

```bash
git checkout -b QP-2888-repo-groundwork
git add .github/scripts/validate_skills.py CONTRIBUTING-skills.md docs/superpowers
git commit -m "chore: add quests domain and r.aliyev owner, skip fenced code in link check

check_links ran one regex over whole files, so any markdown documenting a
relative link failed against the wrong directory. Strip fenced blocks first.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

`.git/info/exclude` is local git metadata and is not committed. The moved research notes were never tracked.

---

### Task 2: Skill skeleton, registries and the auth seam

Creates the skill with everything that does not depend on a reference file, and performs the stack's **only** edit to `AGENTS.md`, `CLAUDE.md` and `skills/README.md`. Later tasks must not touch those three files, or every rebase in the stack will conflict on them.

`SKILL.md` deliberately contains **no links to `references/`** in this task. A link to a file that does not exist yet is a validator error, so each later task adds its file and its pointer together.

**Files:**
- Create: `skills/quest-setup/SKILL.md`
- Create: `skills/quest-setup/references/auth-and-environment.md`
- Modify: `skills/README.md` (one table row)
- Modify: `AGENTS.md` (one inventory row, one trigger block)
- Generate: `.cursor/skills/quest-setup/**`, `CLAUDE.md`

**Interfaces:**
- Consumes: `quests` in `VALID_DOMAINS` and `r.aliyev` in `VALID_OWNERS` from Task 1.
- Produces: a `## Reference material` section in `SKILL.md` that Tasks 3 to 7 each append one bullet to; `references/auth-and-environment.md` as the single file naming hosts, header and credential, which every later file points at instead of restating.

- [ ] **Step 1: Branch**

```bash
git checkout -b QP-2890-skill-skeleton
```

- [ ] **Step 2: Write the skill file**

Create `skills/quest-setup/SKILL.md`. The description below is 1,024 characters, inside the 1,536 cap, with the primary use case first.

````markdown
---
name: quest-setup
description: >-
  Creates, inspects and edits Xsolla Quest Platform quests conversationally,
  submits a quest event, and verifies that the event actually made the quest
  execute. Covers the whole quest document: the node graph and its connections,
  the seven node subtypes, the condition grammar, activation limits, and all
  nine reward types including web3_item and web3_token ERC-20 payouts. Use when
  setting up a quest, adding a trigger or a condition, attaching a reward,
  editing or activating an existing quest, firing a test event, or working out
  why a quest did not fire — including "create a quest", "add a Web3 reward to
  my quest", "make a quest that pays USDC", "trigger my quest", "send a quest
  event", "why didn't my quest complete", "list my quests", "activate a quest",
  "quest platform API".
metadata:
  owner: r.aliyev
  domain: quests
  status: draft
---

## Status

This skill is a **draft**. The credential lane it targets is not deployed yet;
see Prerequisites.

## When to use

Use this skill when the developer wants to manage quests on the Xsolla Quest
Platform:

- Create a quest, as a draft first and then activate it
- Add triggers, conditions or reward actions to a quest
- List, view or edit existing quests
- Submit a single quest event to make a quest run
- Check whether an event actually caused a quest to execute

Out of scope: wallet balances, transaction hashes and Backpack display. This
skill configures a Web3 reward and reports that a quest executed. It never
states that a token was delivered.

## Prerequisites

```bash
export XSOLLA_MERCHANT_ID=<your merchant ID>
export XSOLLA_PROJECT_API_KEY=<your API key>
```

Sent as `Authorization: Basic base64(merchant_id:api_key)`.

**This credential lane is not accepted yet.** Quest Platform implements it in
QP-2862, inside QP-2858 Phase 3, which depends on Phases 1 and 2. Until it
lands, every call to qp-server returns 401. Say exactly that, naming the
ticket, rather than reporting a generic authentication failure. The execution
read-back is unaffected and needs no credential.

All Quest Platform hosts are internal and resolve only on the corporate
network. See `references/auth-and-environment.md`.

## Source of truth

Follow this order. It is the rule the rest of the skill depends on.

1. **Routes, path parameters, envelope field names and types, and the
   top-level `required` list** come from the service's **live OpenAPI
   document**. Fetch it once at the start of the session.
2. **Node subtypes, node `parameters`, the condition grammar, the reward
   bodies, conditionally required fields, and every enum the document renders
   as a bare `string`** come from this skill's `references/`.
3. On conflict: the OpenAPI document wins on shape, `references/` wins on
   rules. Rules that only the server's hand-written validator enforces are
   marked as such where they appear.
4. If neither source answers the question, **ask the developer**. Do not infer
   a field by analogy with another Xsolla API.

If a host is unreachable, which usually means no corporate network, say so and
offer to continue on `references/` alone, noting that the envelope may have
drifted. Never continue silently.

## Reference material

- [`references/auth-and-environment.md`](references/auth-and-environment.md) — hosts, credential, scope, and the incoming auth changes

## Safety stops

- Read back and show the resolved scope before the first write, and get
  confirmation.
- Ask for separate, explicit confirmation before activating a quest that
  contains an `issue_reward` node. Activation means real payouts.
- Ask for confirmation before submitting an event.
- After an uncertain event response, such as a timeout, **do not resend** —
  neither with the same idempotency key nor with a new one. A timeout is not a
  failure. Report "result unknown" and stop.
- Never claim a reward was delivered.

## Errors

Branch on the HTTP status only. The API has no stable machine-readable error
codes.

| Status | What to tell the developer |
|---|---|
| 401 | Missing or invalid credential. If Basic was sent, name QP-2862. |
| 403 | The key lacks the required `questconfig:*` capability. |
| 404 | "Not found, or no access, or the project is not onboarded to Quest Platform." Never say the quest does not exist. |
| 409 | Conflict. |
| 422 | Validation failed. Show `detail` verbatim. |
| 5xx | Server error. Retry reads only. |

Two body shapes exist. Middleware failures return `{"error": "..."}`. Handler
failures return RFC 7807 `application/problem+json`. On 422 the `errors[]`
array is **not** filled in: per-field messages are flattened into one `detail`
string joined with `"; "`. Those `location: message` pairs may be shown to a
human, never parsed for control flow.

`ID 0` is a valid merchant ID and a valid project ID. Never treat it as an
absent value.
````

- [ ] **Step 3: Write the auth and environment reference**

Create `skills/quest-setup/references/auth-and-environment.md`.

````markdown
# Authentication and environment

Written against the contract deployed on stage as of 2026-09-22.

This is the **only** file that names the hosts, the header or the credential.
Everywhere else says "an authenticated Quest Platform request". Keep it that
way: the credential lane is being replaced, and this file is the seam.

## Services

Three services, three jobs. Sending a request to the wrong one is the most
common mistake.

| Service | Job | Stage host |
|---|---|---|
| qp-server | quest CRUD | `https://qp-server.nl-k8s-stage.srv.local` |
| qp-events-collector | event ingestion | `https://qp-events-collector.nl-k8s-stage.srv.local` |
| qp-data | read-only execution and metrics | `https://qp-data.nl-k8s-stage.srv.local` |

All three are internal. They resolve only on the corporate network. There is no
environment variable for them; this table is the source.

Each service publishes its own OpenAPI document at `/openapi.json`, without a
credential, on stage. qp-server blocks those paths in production.

## Credential

```bash
export XSOLLA_MERCHANT_ID=<your merchant ID>
export XSOLLA_PROJECT_API_KEY=<your API key>
```

Sent as `Authorization: Basic base64(merchant_id:api_key)`.

**Not accepted yet.** On the deployed build, qp-server recognises only
`Authorization: Bearer` and an internal `X-REQUEST-APIKEY`, so a Basic
credential is rejected as if no credential were sent. On the in-flight auth
branch a merchant-key verifier exists but is a stub that always denies.

The implementation is QP-2862, inside QP-2858 Phase 3, which depends on Phase 1
(QP-2851) and Phase 2 (QP-2852).

qp-data currently needs no credential at all.

## Scope

Use the scopeless quest routes and let the scope come from the credential.
Before the first write, list quests and show the developer the `account_id`,
`publisher_id` and `project_id` that come back, then ask them to confirm that
is the right place. Do not guess a scope, and do not silently accept whichever
scope the credential happens to carry.

The account-scoped route family, `/api/v2/accounts/{account_id}/quests`, is
available when the developer names an account explicitly.

## Route families this skill does not drive

They exist on the platform. They are listed so that you neither pretend they
are missing nor wander into them.

- `/api/v2/quests/{publisher_id}/{id}` — a publisher-scoped update, delete and
  get. No create and no list, so it cannot carry the flow. Use it only if a
  developer asks for it by name.
- `GET /api/v2/quests/find-quests` and `GET /api/v2/quests/find-quests-triggers`
  — internal processing endpoints behind a legacy master-role check, not
  authoring.
- `GET /api/v2/quests/personalization/{user_id}` — a personalization read path,
  not quest management.

## Incoming changes

These are open and unmerged. Re-read the deployed contract before assuming any
of it; do not implement against the tickets.

- QP-2851 Phase 1, service identities and machine identity groundwork. Changes
  how a service principal's scope is resolved, and can resolve to a workspace
  rather than an account.
- QP-2852 Phase 2, a second human issuer, Xsolla Publisher Account.
- QP-2858 Phase 3, Xsolla scope mapping and the publisher machine lane.
  QP-2860 may add project-scoped publisher-facing routes, in which case the
  scopeless choice above should be revisited.
- QP-2862, the Basic lane this skill targets.

Phase 3 makes unknown, un-onboarded and unauthorized projects return
byte-identical 404s deliberately, so that the endpoint cannot be used to
enumerate which projects use Quest Platform. Report a 404 accordingly.
````

- [ ] **Step 4: Run the validator and watch it fail on the registries**

```bash
python3 .github/scripts/validate_skills.py 2>&1 | tail -6
```

Expected: errors naming `skills/README.md: no row for skill 'quest-setup'`, `AGENTS.md: no entry for skill 'quest-setup'`, and `.cursor/skills/quest-setup is missing — run the provider sync`.

This is the gate working. If instead it complains about the frontmatter, Task 1 did not take effect.

- [ ] **Step 5: Add the registry row**

In `skills/README.md`, add a row to the status table, after the `webhooks-impl` row:

```markdown
| [`quest-setup`](quest-setup/SKILL.md)                                     | Quests: CRUD, events, rewards          | @r.aliyev           | Draft  |
```

- [ ] **Step 6: Add the AGENTS.md entry and trigger**

In `AGENTS.md`, add a row to the skill inventory table after the `webhooks-impl` row:

```markdown
| `quest-setup`                   | Creates and manages Quest Platform quests, events and rewards                            |
```

And add a trigger block inside the existing fenced block under "How to invoke a skill", after the `production` entry:

```
Create a quest that rewards players
→ triggers: quest-setup
```

- [ ] **Step 7: Generate the provider mirror**

```bash
sync_providers
```

- [ ] **Step 8: Run the validator to green**

```bash
python3 .github/scripts/validate_skills.py 2>&1 | tail -1
```

Expected: `Checked 9 skills: 0 new error(s), 0 known debt, 0 warning(s).`

Note the count is now 9, not 8.

- [ ] **Step 9: Verify the description length**

```bash
python3 -c "
import re, pathlib
t = pathlib.Path('skills/quest-setup/SKILL.md').read_text()
fm = t.split('---')[1]
d = re.search(r'description: >-\n((?:  .*\n)+)', fm).group(1)
d = ' '.join(l.strip() for l in d.splitlines())
print(len(d), 'chars')
assert len(d) <= 1536
"
```

Expected: a number at or below 1536, printed with `chars`.

- [ ] **Step 10: Commit**

```bash
git add skills/quest-setup AGENTS.md CLAUDE.md skills/README.md .cursor/skills
git commit -m "feat(quest-setup): skill skeleton, registries and auth seam

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: The quest document and node subtypes

Encodes the part of the contract the OpenAPI document cannot express: that a quest is a graph, what is conditionally required, and which node subtypes the server actually accepts.

**Files:**
- Create: `skills/quest-setup/references/quest-document.md`
- Create: `skills/quest-setup/references/node-subtypes.md`
- Modify: `skills/quest-setup/SKILL.md` (two bullets under `## Reference material`, and a new `## Flow` section)
- Generate: `.cursor/skills/quest-setup/**`

**Interfaces:**
- Consumes: the `## Reference material` section created in Task 2.
- Produces: the `## Flow` section in `SKILL.md`, which Tasks 6 and 7 append steps 6 and 7 to; the documented node shape that Tasks 4 and 5 attach `parameters` schemas to.

- [ ] **Step 1: Branch**

```bash
git checkout -b QP-2890-quest-document
```

- [ ] **Step 2: Confirm the envelope against the live document before writing it down**

Never transcribe a contract from memory. Fetch it.

```bash
curl -s https://qp-server.nl-k8s-stage.srv.local/openapi.json -o /tmp/qps.json
python3 -c "
import json; s = json.load(open('/tmp/qps.json'))['components']['schemas']
print('Quest.required =', s['Quest']['required'])
print('Node.required  =', s['Node']['required'])
print('Node.subtype   =', s['Node']['properties']['subtype'])
"
```

Expected:

```
Quest.required = ['name', 'type', 'status', 'created_by']
Node.required  = ['id', 'name', 'type', 'subtype']
Node.subtype   = {'type': 'string'}
```

The bare `string` on `subtype` is exactly why `node-subtypes.md` has to exist. If any of these three lines differs, the contract moved and the spec's section 4.3 table needs revisiting before you continue.

- [ ] **Step 3: Write the quest document reference**

Create `skills/quest-setup/references/quest-document.md`.

````markdown
# The quest document

Written against the contract deployed on stage as of 2026-09-22.

A quest is a **graph**, not a flat record. This one fact drives everything else
in this skill.

## Fields

`POST` and `PUT` take the whole quest object.

| Field | Type | Required | Notes |
|---|---|---|---|
| `name` | string | yes | 1 to 255 characters |
| `type` | string | yes | `liveops`, `ads`, `xsolla_app`, `social_quest` |
| `status` | string | yes | `active` or `inactive` on write. `deleted` exists as a value but is rejected on write |
| `created_by` | string | yes | 1 to 255 characters |
| `description` | string | no | if present, 5 to 1000 characters |
| `publisher_id` | string | no | 1 to 255 characters |
| `project_id` | string | no | 1 to 255 characters |
| `start_date` | RFC3339 | **only when `active`** | not earlier than one day ago |
| `end_date` | RFC3339 | **only when `active`** | not in the past, and at or after `start_date` |
| `nodes` | array | **at least 2 when `active`** | optional and may be empty when `inactive` |
| `connections` | object | required unless `inactive` and empty | see below |
| `activation_limits` | array | no | see below |
| `metadata` | object | no | nesting depth at most 2 |
| `id`, `created_at`, `updated_at`, `version_id` | — | server-assigned | ignored on create |
| `has_personalization` | bool | — | server-derived from the nodes; do not set it |
| `sample_data` | any | no | accepted, not validated, **not persisted** |

The conditional requirements are enforced only by the server's hand-written
validator. They do not appear in the OpenAPI document.

## Draft first, then activate

Because an `inactive` quest needs only four fields, build the quest as a draft,
fill it in while talking to the developer, and activate it as a separate,
explicitly confirmed step. Do not try to assemble a whole valid graph before
the first call.

## Nodes and connections

```json
{
  "nodes": [
    {"id": "<uuid>", "name": "<3-255 chars>", "type": "trigger", "subtype": "dynamic_event", "parameters": {}},
    {"id": "<uuid>", "name": "<3-255 chars>", "type": "action",  "subtype": "issue_reward",  "parameters": {}}
  ],
  "connections": {
    "<source node uuid>": [{"nodeId": "<target node uuid>", "on": "ticket_issued"}]
  }
}
```

- `type` is `trigger`, `action` or `condition`.
- `id` must be a valid, non-zero UUID.
- `on` is optional. When present it must be `ticket_issued`, `no_ticket` or
  `daily_cap_reached`.
- Every edge must reference a node that exists in `nodes`, and the graph must
  be acyclic.

The smallest quest that can be activated is two nodes and one edge: a trigger
and an action.

## Activation limits

```json
{"activation_limits": [{"type": "per_user", "count": 1, "time_window": {"duration_unit": "day"}}]}
```

`type` is `global` or `per_user`. `count` must be at least 1.
`time_window.duration_unit`, when present, is `day`, `week` or `month`.

## Editing

There is **no PATCH**. Update is a full-document `PUT`: read the quest, change
what you need, and send the whole object back. Tell the developer this before
editing, because a partial body silently drops everything it omits.

`version_id` is server-assigned and changes on every write.
````

- [ ] **Step 4: Write the node subtypes reference**

Create `skills/quest-setup/references/node-subtypes.md`.

````markdown
# Node subtypes

Written against the contract deployed on stage as of 2026-09-22.

The OpenAPI document types `subtype` as a bare `string`. The real list lives in
the server's validator, and it is shorter than the constants suggest.

## Accepted

| `subtype` | Used with `type` | `parameters` |
|---|---|---|
| `date_and_time` | trigger | not validated on write |
| `dynamic_event` | trigger | `{"event_name": "<non-empty string>"}` |
| `custom_attributes_check` | condition | see `conditions.md` |
| `issue_reward` | action | see `rewards.md` |
| `send_xsolla_app_notification` | action | notification parameters |
| `send_http_webhook` | action | webhook parameters |
| `webshop_personalization` | action | personalization parameters |

## Rejected, despite existing

`event_check` is declared as a constant in the platform's models but is **not**
in the accepted list. A node using it fails validation. Do not offer it, and if
a developer asks for it, say it is not accepted by the API.

## Choosing a trigger

For a quest that should run when something happens, use `dynamic_event` and set
`event_name` to the name the event will carry. That name is what ties the quest
to the event submitted later; see `events.md`.

For a quest that should run on a schedule, use `date_and_time`. Its parameters
are not checked on write, so mistakes there surface at runtime rather than at
create time. Say so when you use it.
````

- [ ] **Step 5: Add the pointers and the flow to SKILL.md**

Append two bullets to `## Reference material`, so the section reads:

```markdown
## Reference material

- [`references/auth-and-environment.md`](references/auth-and-environment.md) — hosts, credential, scope, and the incoming auth changes
- [`references/quest-document.md`](references/quest-document.md) — the quest graph, conditional requirements, full-document PUT
- [`references/node-subtypes.md`](references/node-subtypes.md) — the seven accepted node subtypes and their parameters
```

And insert a `## Flow` section immediately before `## Safety stops`:

```markdown
## Flow

1. **Bring-up.** Fetch the OpenAPI documents. Check the credential is set. List
   quests, show the resolved scope, and get confirmation.
2. **Draft.** Create the quest as `inactive` with the four required fields.
3. **Fill in.** Add nodes and edges one at a time, asking for each missing
   required value. Show the assembled document before sending it.
4. **Activate.** A separate step: move to `active` with dates, after checking
   there are at least two nodes and the graph is acyclic.
5. **Edit.** Read, change, full `PUT`. Warn that `PUT` replaces the whole
   document.
```

- [ ] **Step 6: Sync, then run the validator**

```bash
sync_providers
python3 .github/scripts/validate_skills.py 2>&1 | tail -1
```

Expected: `Checked 9 skills: 0 new error(s), 0 known debt, 0 warning(s).`

A "differs from its source" error means `sync_providers` was not run after the last edit.

- [ ] **Step 7: Commit**

```bash
git add skills/quest-setup .cursor/skills
git commit -m "docs(quest-setup): quest document and node subtypes

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: Conditions

**Files:**
- Create: `skills/quest-setup/references/conditions.md`
- Modify: `skills/quest-setup/SKILL.md` (one bullet under `## Reference material`)
- Generate: `.cursor/skills/quest-setup/**`

**Interfaces:**
- Consumes: the node shape from Task 3; this file documents the `parameters` of a `custom_attributes_check` node.
- Produces: nothing later tasks depend on.

- [ ] **Step 1: Branch**

```bash
git checkout -b QP-2890-conditions
```

- [ ] **Step 2: Confirm the OpenAPI document really is silent here**

The whole justification for writing this by hand is that the generator cannot see inside `json.RawMessage`.

```bash
curl -s https://qp-server.nl-k8s-stage.srv.local/openapi.json -o /tmp/qps.json
python3 -c "
import json; s = json.load(open('/tmp/qps.json'))['components']['schemas']
hits = [k for k in s if 'Condition' in k or 'Operand' in k]
print('condition schemas:', hits)
assert hits == [], 'the document now describes conditions — prefer it over this file'
"
```

Expected: `condition schemas: []`

If this assertion fails, the platform started publishing condition schemas. Stop and revise the spec's source-of-truth table rather than hand-writing a second copy.

- [ ] **Step 3: Write the conditions reference**

Create `skills/quest-setup/references/conditions.md`.

````markdown
# Conditions

Written against the contract deployed on stage as of 2026-09-22.

These are the `parameters` of a node with `type: condition` and
`subtype: custom_attributes_check`. The OpenAPI document does not describe
them at all.

## Shape

```json
{
  "type": "comparison",
  "operator": {"type": "numeric", "operation": "gte"},
  "left":  {"type": "attribute", "value": "user.level"},
  "right": {"type": "value", "value": 10}
}
```

`type` is `and`, `or` or `comparison`.

- `and` and `or` need a non-empty `conditions` array of nested condition
  objects, and ignore `left`, `right` and `operator`.
- `comparison` needs `operator`, `left` and `right`.

## Operands

`left` and `right` are operands. Each has a `type`:

| Operand `type` | `value` | Extra |
|---|---|---|
| `value` | a literal | — |
| `attribute` | a non-empty string path, for example `user.level` | — |
| `event` | a non-empty string, the event name | **must** carry `time_window.duration_unit`, one of `day`, `week`, `month` |

An `event` operand supports numeric comparison only, and the threshold it is
compared against must be a whole number.

## Operators

`operator.type` constrains `operator.operation`:

| `type` | allowed `operation` |
|---|---|
| `numeric` | `eq`, `neq`, `gt`, `lt`, `gte`, `lte`, `mod` |
| `string` | `eq`, `neq`, `contains` |
| `boolean` | `eq`, `neq` |
| `string_array` | `in`, `not_in`, `intersects` |

For `mod`, the divisor must be greater than zero.

## Counting events

To express "did this at least three times this week":

```json
{
  "type": "comparison",
  "operator": {"type": "numeric", "operation": "gte"},
  "left":  {"type": "event", "value": "level.completed", "time_window": {"duration_unit": "week"}},
  "right": {"type": "value", "value": 3}
}
```

Leaving out `time_window` on an `event` operand is the most common mistake
here, and the error comes back as a flattened 422 string rather than a field
error.
````

- [ ] **Step 4: Add the pointer to SKILL.md**

Append to `## Reference material`:

```markdown
- [`references/conditions.md`](references/conditions.md) — condition grammar: types, operands, operators, event counting
```

- [ ] **Step 5: Sync, then run the validator**

```bash
sync_providers
python3 .github/scripts/validate_skills.py 2>&1 | tail -1
```

Expected: `Checked 9 skills: 0 new error(s), 0 known debt, 0 warning(s).`

- [ ] **Step 6: Commit**

```bash
git add skills/quest-setup .cursor/skills
git commit -m "docs(quest-setup): condition grammar

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: Rewards

**Files:**
- Create: `skills/quest-setup/references/rewards.md`
- Modify: `skills/quest-setup/SKILL.md` (one bullet under `## Reference material`)
- Generate: `.cursor/skills/quest-setup/**`

**Interfaces:**
- Consumes: the node shape from Task 3; this file documents the `parameters` of an `issue_reward` node.
- Produces: nothing later tasks depend on.

- [ ] **Step 1: Branch**

```bash
git checkout -b QP-2890-rewards
```

- [ ] **Step 2: Write the rewards reference**

Create `skills/quest-setup/references/rewards.md`.

````markdown
# Rewards

Written against the contract deployed on stage as of 2026-09-22.

These are the `parameters` of a node with `type: action` and
`subtype: issue_reward`. The OpenAPI document does not describe them, because
the body is carried as raw JSON.

## Wrapper

```json
{"type": "<reward type>", "purpose": "<string>", "body": { }}
```

`type`, `purpose` and a non-empty `body` are all required. An unrecognised
`type` is rejected.

## Bodies

| `type` | `body` | Rules |
|---|---|---|
| `xsolla_points` | `{"amount": <number>}` plus optional `campaign_name`, `campaign_image`, `event_name`, `reason_quest_id`, `app_name`, `app_icon_url` | `amount` greater than 0 |
| `virtual_currency` | `{"amount": <number>}` | `amount` greater than 0 |
| `loyalty_points` | `{"amount": <number>, "loyalty_points_id": "<string>"}` | both required |
| `lootbox` | `{"item_sku": "<string>", "quantity": <int>}` | `quantity` 1 to 100 |
| `custom` | `{"amount": <number>, "currency_ticker": "<string>"}` | `amount` greater than 0 |
| `inventory_item` | `{"xsolla_item": <bool>, "items": [{"sku": "<string>", "quantity": <int>}]}` | `quantity` 0 to 100 |
| `vc_wallet_ticket` | `{"quantity": <int>, "currency_ticker": "<string>"}` plus optional `playtime` | `quantity` greater than 0 |
| `web3_item` | `{"xsolla_item": <bool>, "item_sku": <string or array>, "quantity": <int>}` | `quantity` at least 0, read back as 1 when absent |
| `web3_token` | `{"item_sku": "<string>", "amount": <number>}` | both required, `amount` greater than 0 |

The optional `playtime` object on `vc_wallet_ticket` is
`{"earn_rate_minutes": <greater than 0>, "daily_cap_minutes": <greater than 0>, "timezone": "<non-empty>"}`.

## web3_token

An ERC-20 payout, for example USDC.

```json
{
  "type": "web3_token",
  "purpose": "quest_completion",
  "body": {"item_sku": "XLA-000-001", "amount": 0.01}
}
```

`amount` is in whole tokens, not base units. `item_sku` selects the ERC-20
within the minting service's configured project.

**Settlement is asynchronous and happens outside this skill.** Configuring this
reward, activating the quest and submitting an event are three things this
skill does. Delivery to a wallet is not. A successful event response says
nothing about whether a token moved, so never report one as if it did. Say that
the quest executed and the reward action completed, and stop there.

Attaching this reward to a quest that you then activate means real payouts. Ask
for explicit confirmation before activating.
````

- [ ] **Step 3: Add the pointer to SKILL.md**

Append to `## Reference material`:

```markdown
- [`references/rewards.md`](references/rewards.md) — the nine reward types and their bodies, including web3_token
```

- [ ] **Step 4: Sync, then run the validator**

```bash
sync_providers
python3 .github/scripts/validate_skills.py 2>&1 | tail -1
```

Expected: `Checked 9 skills: 0 new error(s), 0 known debt, 0 warning(s).`

- [ ] **Step 5: Commit**

```bash
git add skills/quest-setup .cursor/skills
git commit -m "docs(quest-setup): the nine reward bodies

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 6: Events

**Files:**
- Create: `skills/quest-setup/references/events.md`
- Modify: `skills/quest-setup/SKILL.md` (one bullet under `## Reference material`, step 6 under `## Flow`)
- Generate: `.cursor/skills/quest-setup/**`

**Interfaces:**
- Consumes: the `## Flow` section from Task 3, and `dynamic_event`'s `event_name` from `node-subtypes.md`.
- Produces: `## Flow` step 6, which Task 7 follows with step 7.

- [ ] **Step 1: Branch**

```bash
git checkout -b QP-2890-events
```

- [ ] **Step 2: Confirm the event contract against the live document**

This is a different service from qp-server, with its own document.

```bash
curl -s https://qp-events-collector.nl-k8s-stage.srv.local/openapi.json -o /tmp/ec.json
python3 -c "
import json; s = json.load(open('/tmp/ec.json'))['components']['schemas']
print('EventPayload.required =', s['EventPayload']['required'])
print('scope =', s['EventPayload']['properties']['scope'])
"
```

Expected:

```
EventPayload.required = ['idempotency_key', 'name', 'user_ids', 'client_timestamp']
scope = {'default': 'private', 'type': 'string'}
```

`scope` arriving as a bare `string` with no enum is the divergence the reference file has to record.

- [ ] **Step 3: Write the events reference**

Create `skills/quest-setup/references/events.md`.

````markdown
# Events

Written against the contract deployed on stage as of 2026-09-22.

Events go to **qp-events-collector**, not to qp-server. Sending an event to
qp-server produces a 404 that looks like a missing quest.

`POST /api/v2/events`

## Payload

```json
{
  "idempotency_key": "<uuid>",
  "name": "web3.token_test",
  "client_timestamp": "2026-09-22T10:30:00Z",
  "user_ids": [{"identifier_type": "xsolla_id", "value": "<uuid>"}],
  "quest_id": "<uuid>",
  "scope": "private",
  "publisher": {"publisher_id": "<string>", "project_id": "<string>"},
  "properties": {"any": "string values only"}
}
```

| Field | Required | Rules |
|---|---|---|
| `idempotency_key` | yes | a valid, non-zero UUID. Any version is accepted despite the schema hinting at v4 |
| `name` | yes | must match the `event_name` on the quest's `dynamic_event` trigger |
| `client_timestamp` | yes | RFC3339 |
| `user_ids` | yes | at least one entry |
| `quest_id` | no | a valid UUID when present |
| `scope` | no | `global`, `private`, `within_project`, `within_quest`, `within_publisher`. Defaults to `private`. The published schema shows a bare string and the older struct hint lists only three values; the server accepts all five |
| `publisher` | no | if the object is present and non-empty, `publisher.publisher_id` is required |
| `properties` | no | string values only |

`user_ids[].identifier_type` is `xsolla_id`, `gamer_id`, `guest_id` or `email`.
An `xsolla_id` value must parse as a UUID; an `email` value must contain `@`;
`gamer_id` and `guest_id` need only be non-empty.

The account is **not** in the body. It comes from the credential.

A 200 returns `{"idempotency_key": "...", "event_id": "<uuid>"}`.

## Idempotency

There are two separate mechanisms and they are easy to confuse:

- the body field `idempotency_key`, which the platform uses as the message key
- a generic HTTP `X-Idempotency-Key` header handled by middleware, which must
  be exactly 36 characters

Use the body field. Generate a fresh UUID per event.

## After an uncertain response

If the request times out or the outcome is otherwise unknown, **stop**. Do not
resend, not with the same key and not with a new one. A timeout is not a
failure: the event may have been accepted and the quest may already be paying
out. Report "result unknown", and use the execution read-back to find out what
really happened.
````

- [ ] **Step 4: Add the pointer and flow step to SKILL.md**

Append to `## Reference material`:

```markdown
- [`references/events.md`](references/events.md) — submitting a quest event to qp-events-collector
```

Append to `## Flow`, after step 5:

```markdown
6. **Event.** Build the payload, generate a fresh UUID `idempotency_key`, set
   an RFC3339 `client_timestamp`, confirm with the developer, and submit to
   qp-events-collector.
```

- [ ] **Step 5: Sync, then run the validator**

```bash
sync_providers
python3 .github/scripts/validate_skills.py 2>&1 | tail -1
```

Expected: `Checked 9 skills: 0 new error(s), 0 known debt, 0 warning(s).`

- [ ] **Step 6: Commit**

```bash
git add skills/quest-setup .cursor/skills
git commit -m "docs(quest-setup): event submission contract

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 7: Verification, and the live agent test

Closes the loop, and produces the only live evidence available before QP-2862, because qp-data needs no credential.

**Files:**
- Create: `skills/quest-setup/references/verification.md`
- Modify: `skills/quest-setup/SKILL.md` (one bullet under `## Reference material`, step 7 under `## Flow`)
- Generate: `.cursor/skills/quest-setup/**`

**Interfaces:**
- Consumes: `## Flow` step 6 from Task 6.
- Produces: the completed skill.

- [ ] **Step 1: Branch**

```bash
git checkout -b QP-2890-verification
```

- [ ] **Step 2: Confirm the read-back works and needs no credential**

```bash
curl -s -o /dev/null -w "%{http_code}\n" \
  "https://qp-data.nl-k8s-stage.srv.local/api/v1/quest-executions?questId=44193275-5376-498b-9e14-e91fbe9085c9&size=2"
```

Expected: `200`

That quest is `WEB3 Token ERC-20 Stage Test`, the reference two-node shape from the spec's section 6.1. If this returns 401 or 403, qp-data has gained authentication and `verification.md` must say so.

- [ ] **Step 3: Write the verification reference**

Create `skills/quest-setup/references/verification.md`.

````markdown
# Verifying that a quest ran

Written against the contract deployed on stage as of 2026-09-22.

Read-back lives on **qp-data**, a separate, read-only service. On stage it
currently needs no credential, so this is the one part of the skill that works
before the Basic lane ships.

`GET /api/v1/quest-executions`

| Query parameter | Use |
|---|---|
| `questId` | the quest you just triggered |
| `userId` | the user the event named |
| `accountId`, `publisherId` | narrow to a scope |
| `status` | filter by execution status |
| `includeNotTriggered` | also show quests that did not fire |
| `latestPerUser` | one row per user |
| `includeEventBody` | include the originating event |
| `page`, `size` | paging |

## What comes back

Each item carries the execution `status`, the originating `eventId` and
`eventName`, the `quest` with the event names it `listensFor`, the `account`,
the `conditionEvals`, and an `actions` array giving **each action node's own
status**.

## Three separate claims

Keep these apart when reporting, because conflating them is how a demo ends up
claiming something untrue.

1. **The event was accepted.** Evidence: a 200 from qp-events-collector with an
   `event_id`.
2. **The quest executed and its reward action completed.** Evidence: an item
   here with `status: COMPLETED` and the `issue_reward` action also
   `COMPLETED`.
3. **The token reached the wallet.** **This skill has no evidence for this and
   must not claim it.** Settlement is asynchronous and happens in a service
   this skill never calls.

Report 1 and 2 from evidence. For 3, say that settlement happens separately and
has to be checked in the wallet.

## When nothing comes back

An empty result after submitting an event usually means one of:

- the event `name` does not match the trigger's `event_name`
- the quest is `inactive`
- the user identifier does not match the one the event carried
- an activation limit already consumed the user's allowance
- the execution has not been ingested yet, so retry the read before concluding
  anything

Reading again is safe. Re-sending the event is not.
````

- [ ] **Step 4: Add the pointer and flow step to SKILL.md**

Append to `## Reference material`:

```markdown
- [`references/verification.md`](references/verification.md) — reading execution results back from qp-data
```

Append to `## Flow`, after step 6:

```markdown
7. **Verify.** Read the execution back from qp-data and report what actually
   happened: whether the quest ran and which action nodes completed. Do not
   report a reward as delivered.
```

- [ ] **Step 5: Sync, then run the validator**

```bash
sync_providers
python3 .github/scripts/validate_skills.py 2>&1 | tail -1
```

Expected: `Checked 9 skills: 0 new error(s), 0 known debt, 0 warning(s).`

- [ ] **Step 6: Run the offline contract conformance check**

The write path cannot be exercised against the server until QP-2862, so check
its *content* instead: have an agent assemble a quest document and an event
payload by following the skill, save them, and verify them against the live
schema and the validator-only rules **without sending anything**.

Give a fresh agent this prompt:

```
Using the quest-setup skill, assemble — but do not send — two JSON documents:
an active quest named "Conformance Probe" of type liveops, created_by
"conformance", with a dynamic_event trigger listening for "probe.fired" and an
issue_reward action paying 0.01 of item_sku XLA-000-001 as web3_token; and the
event payload that would trigger it for xsolla_id
e89866ee-954a-4aa2-8581-fbcd23f6e209. Write them to /tmp/probe-quest.json and
/tmp/probe-event.json.
```

Then check them:

```bash
curl -s https://qp-server.nl-k8s-stage.srv.local/openapi.json -o /tmp/qps.json
curl -s https://qp-events-collector.nl-k8s-stage.srv.local/openapi.json -o /tmp/ec.json
python3 - <<'PY'
import json, uuid, datetime

qs = json.load(open('/tmp/qps.json'))['components']['schemas']
es = json.load(open('/tmp/ec.json'))['components']['schemas']
q  = json.load(open('/tmp/probe-quest.json'))
ev = json.load(open('/tmp/probe-event.json'))
fail = []

def need(doc, keys, where):
    for k in keys:
        if k not in doc or doc[k] in (None, "", []):
            fail.append(f"{where}: missing required '{k}'")

# envelope, straight from the live documents
need(q,  qs['Quest']['required'],        'quest')
need(ev, es['EventPayload']['required'], 'event')

# validator-only rules the documents cannot express
if q.get('status') == 'active':
    for k in ('start_date', 'end_date'):
        if not q.get(k):
            fail.append(f"quest: '{k}' is required when status is active")
    if len(q.get('nodes') or []) < 2:
        fail.append('quest: active quests need at least 2 nodes')

ACCEPTED = {'date_and_time', 'dynamic_event', 'custom_attributes_check',
            'issue_reward', 'send_xsolla_app_notification', 'send_http_webhook',
            'webshop_personalization'}
ids = set()
for i, n in enumerate(q.get('nodes') or []):
    need(n, qs['Node']['required'], f'quest.nodes[{i}]')
    if n.get('subtype') not in ACCEPTED:
        fail.append(f"quest.nodes[{i}]: subtype {n.get('subtype')!r} is not accepted")
    ids.add(n.get('id'))
    if n.get('subtype') == 'issue_reward':
        p = n.get('parameters') or {}
        need(p, ('type', 'purpose', 'body'), f'quest.nodes[{i}].parameters')
        if p.get('type') == 'web3_token':
            b = p.get('body') or {}
            if not b.get('item_sku'):
                fail.append(f'quest.nodes[{i}]: web3_token needs item_sku')
            if not (isinstance(b.get('amount'), (int, float)) and b['amount'] > 0):
                fail.append(f'quest.nodes[{i}]: web3_token amount must be > 0')

for src, edges in (q.get('connections') or {}).items():
    if src not in ids:
        fail.append(f'quest.connections: source {src} is not a node')
    for e in edges:
        if e.get('nodeId') not in ids:
            fail.append(f"quest.connections: target {e.get('nodeId')} is not a node")
        if e.get('on') and e['on'] not in ('ticket_issued', 'no_ticket', 'daily_cap_reached'):
            fail.append(f"quest.connections: bad edge label {e['on']!r}")

try:
    assert uuid.UUID(ev['idempotency_key']).int != 0
except Exception:
    fail.append('event: idempotency_key must be a valid non-zero UUID')
try:
    datetime.datetime.fromisoformat(ev['client_timestamp'].replace('Z', '+00:00'))
except Exception:
    fail.append('event: client_timestamp must be RFC3339')
if not (ev.get('user_ids') or []):
    fail.append('event: user_ids needs at least one entry')

trigger_names = {(n.get('parameters') or {}).get('event_name')
                 for n in (q.get('nodes') or []) if n.get('subtype') == 'dynamic_event'}
if ev.get('name') not in trigger_names:
    fail.append(f"event: name {ev.get('name')!r} matches no trigger in {trigger_names}")

print('\n'.join(fail) if fail else 'conformance: ok')
raise SystemExit(1 if fail else 0)
PY
```

Expected: `conformance: ok` and exit status 0.

Any failure is a defect in the skill's wording, not in the probe. Fix the
reference file the agent got wrong and re-run.

- [ ] **Step 7: Run the live agent test the PR must include**

Start a fresh agent session in this repository, on this branch, with no extra context, and give it exactly this prompt:

```
Find the quest "WEB3 Token ERC-20 Stage Test" on Quest Platform stage and tell me
whether it has ever actually run, what reward it pays, and whether the reward
reached anyone's wallet.
```

The run passes when the agent:

- invokes `quest-setup` without being told to
- reaches qp-data rather than trying to authenticate against qp-server
- reports the two `COMPLETED` executions
- reports the reward as `web3_token`, `XLA-000-001`, `0.01`
- **declines to say the token reached a wallet**, and explains that settlement
  is asynchronous and outside the skill

The last point is the one that matters. If the agent claims delivery, the
wording in `rewards.md` and `verification.md` is not strong enough. Fix it and
re-run before committing.

Record the exact prompt and a one-line result in the MR description, as
`CONTRIBUTING-skills.md` requires.

- [ ] **Step 8: Check the skill file has not outgrown its target**

```bash
wc -l skills/quest-setup/SKILL.md
```

Expected: at or below roughly 200 lines. The validator only warns above 500, but the repository's own guidance is 200, and anything longer belongs in `references/`.

- [ ] **Step 9: Commit**

```bash
git add skills/quest-setup .cursor/skills
git commit -m "docs(quest-setup): execution verification via qp-data

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Deferred until QP-2862 lands

Not tasks in this plan. They cannot start until the Basic credential lane is deployed.

- Re-read the deployed auth contract and reconcile the skill, including whether QP-2860 introduced project-scoped publisher-facing routes. If it did, switch the flow onto them and pick up `XSOLLA_PROJECT_ID`, which is an existing repository variable.
- Run one live write test: draft, fill, activate, event, verify.
- Validate the ERC-20 reward end to end on stage with a fresh rehearsal. The confirmed fixture last executed on 2026-08-24.
- Record the installation-to-Backpack demo.

## Merge preconditions

Before the stack can go to the public repository:

- Review the internal `.srv.local` hostnames in `references/auth-and-environment.md`. Publishing internal topology is a decision to take deliberately, not to discover at review.
- QP-2862 must have landed, or the skill cannot work for anyone outside.
- The `quests` domain addition needs the repository owner's sign-off.
