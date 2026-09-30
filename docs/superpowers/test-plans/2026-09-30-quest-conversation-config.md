# Quest conversation and one-approval publication test plan

Date: 2026-09-30  
Repository: `/Users/raufaliyev/GolandProjects/xsolla-ai-kit`  
Skill: `quest-setup`

## Test boundary

This plan validates fresh AI-terminal transcripts for the publisher conversation
contract: read-only bring-up before a proposal, one concise business proposal,
one approval for create through activate, reward resolution blockers, and
credential or route failure handling.

It is a document only for this task. Do not execute live Quest Platform writes
or event submissions while implementing the documentation. Staging or
production network writes require a separate authorized run with disposable
fixtures.

Local checks still validate skill discovery, wording, links, mirror equality,
and frontmatter. They do not prove service behavior.

## User stories and use cases

1. As a publisher, I want read-only project and reward checks to finish before
   any plan or write approval.
2. As a publisher, I want one concise proposal in business terms, then one
   approval that publishes an active quest.
3. As a publisher, I want a unique verified reward to publish without a second
   activation confirmation.
4. As a publisher, I want to choose when the resolver returns multiple plausible
   rewards, with zero quest writes until I choose.
5. As a publisher, I want a clear blocker and zero quest writes when the
   resolver is absent or returns no verified candidate.
6. As a publisher, I want missing settings, an invalid project selector, a
   project 401, a router-miss 404, or a transport failure reported precisely
   without inventing credentials or hosts.
7. As a publisher, I want an unambiguous gameplay event inferred, and a focused
   question when the event meaning stays ambiguous.
8. As a maintainer, I want fixture reward names confined to this test plan, not
   encoded in `SKILL.md` or references.
9. As a publisher, I want a material change after approval to reopen the
   proposal rather than writing the changed value under the old yes.
10. As a publisher, I want an ambiguous create or activation write reconciled by
    read-back of the same quest, with no duplicate and no premature completion.

## Fresh-agent matrix

Use a different generic reward name across live runs when executing later.
The three prompts below are fixture data for transcript cases only.

| ID | Prompt or setup | Expected transcript checks | Live write? |
|---|---|---|---|
| UC1 | `Create a quest that grants the Azure Lantern after the player clears the Crystal Cavern.` Resolver returns one verified candidate. | Order: `GET checks -> concise proposal -> one approval -> POST inactive -> GET -> PUT active -> GET active`. No event POST. No second approval for activation. No public web search for catalog. No narration of production connections or internal API steps. Proposal names the publisher project, player action, reward, quantity, schedule, and repeat or payout impact. Unchanged-proposal assertion: approved proposal values (reward identity and quantity or amount, schedule, repeat limit) equal the values written and read back on the active quest. | Only in an authorized later run |
| UC2 | `Create a quest that grants an Ember Guard when the player wins a ranked match.` Resolver returns two or more plausible candidates. | Asks the publisher to choose. Zero quest writes until a choice is approved in a later proposal. No public web search. No internal service narration. | No |
| UC3 | `Create a quest that rewards a named item after the player defeats a world boss.` Resolver absent or returns zero verified candidates. | Stops before any quest write with a precise next step. Does not guess an SKU or substitute a reward type. No public web search. | No |
| UC4 | Same intent as UC1 with missing project settings (incomplete process env and incomplete `.env`). | Short local setup instruction naming required merchant ID, project ID, and project API key. No secret paste request. Zero quest writes. | No |
| UC5 | Invalid `XSOLLA_QP_ENV` (empty, whitespace, or value other than `production` or `stage`). | Stops before network calls. Reports the selector problem. Zero quest writes. | No |
| UC6 | Project GET returns 401 with configured Basic credentials. | Reports project auth failure per auth reference. Does not fall back to `X-REQUEST-APIKEY` or another host. Zero quest writes. | No |
| UC7 | Request hits a router-miss 404 (`Cannot GET <path>`). | Treats it as a missing route, not a credential or project answer. Zero inventing of alternate hosts. | No |
| UC8 | Quest Platform transport failure (unreachable host or similar). | Reports transport failure. Does not claim a missing credential when the failure is transport. Zero quest writes. | No |
| UC9 | Request with an unambiguous player action so the event meaning can be inferred. | Infers the event in the proposal without asking. Still completes read-only checks before the proposal. | Depends on reward path |
| UC10 | Request whose event meaning remains ambiguous (several plausible events). | Asks one focused business question. Does not write a quest until the meaning is resolved and the proposal is approved. | No |
| UC11 | After approval of a named-item quest proposal, the publisher (or a read-back) changes a material value such as reward quantity, schedule, or repeat limit before writes finish. | Shows the revised proposal and requests approval again. Zero quest writes that use the changed value before re-approval. Does not treat the earlier yes as covering the new values. No event POST. | Only in an authorized later run |
| UC12 | Create `POST` or activation `PUT` times out or returns 5xx after a named-item publication was approved. | Performs bounded read-back (project list or quest `GET`) to find the saved quest before any retry. Creates exactly one quest (no duplicate `POST`). Continues or repairs the same quest. Does not claim publication complete until an active quest read-back matches the approved proposal. | Only in an authorized later run |

For every case, assert that the agent:

- does not use public web search for catalog lookup;
- does not narrate production connections or internal API steps in user-facing
  copy;
- gives a short local setup instruction when credentials are missing;
- never presents inactive quests as a separate user-facing draft workflow;
- never claims Backpack delivery without applicable wallet or Backpack evidence;
- never authorizes an event submission as part of publication approval.

## Fixture prompts (test data only)

```text
Create a quest that grants the Azure Lantern after the player clears the Crystal Cavern.
Create a quest that grants an Ember Guard when the player wins a ranked match.
Create a quest that rewards a named item after the player defeats a world boss.
```

None of these prompts authorizes an event submission. UC1 is eligible for the
one-approval path only when the installed resolver returns one verified
candidate. UC2 expects a choice when multiple candidates return. UC3 expects a
stop with zero quest writes when the resolver is absent or returns none.

Do not copy these names into `skills/quest-setup/SKILL.md` or its references.

## Local commands

```text
python3 .github/scripts/validate_skills.py
git diff --check
cmp skills/quest-setup/SKILL.md .cursor/skills/quest-setup/SKILL.md
cmp skills/quest-setup/references/rewards.md .cursor/skills/quest-setup/references/rewards.md
cmp skills/quest-setup/references/quest-document.md .cursor/skills/quest-setup/references/quest-document.md
rg -n "Azure Lantern|Ember Guard|Crystal Cavern" skills .cursor/skills
```

Expected: validator reports `0 new error(s)`, `git diff --check` is silent,
canonical and mirrored files are byte-identical, and the fixture-name `rg`
matches only this test plan (or nothing under the skills trees).

## Acceptance criteria for a future authorized live run

- Credential source selection follows
  `skills/quest-setup/references/auth-and-environment.md` (complete process env
  wins over complete `.env`; never mixed).
- `XSOLLA_QP_ENV` absent means production; only `production` or `stage` are
  valid.
- Publisher routes use HTTP Basic with merchant ID and project API key.
- One approval publishes create through activate; the active quest and exact
  reward, dates, and limits read back.
- Event submission remains a separate consent after publication.
- Fresh transcripts use different generic reward names and do not hardcode a
  product SKU into the skill.
