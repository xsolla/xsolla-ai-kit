# How to run an eval

Tests **the skill file**, not its author. Every run starts in a **fresh Claude Code
session** that loads `SKILL.md` cold — a session that has been discussing the skill
already knows the answers and behaves well regardless of what the file says.

## Setup

The skill is discovered from `~/.claude/skills/description-to-shop`. Export the project
in the terminal you launch from:

```bash
export XSOLLA_MERCHANT_ID=936457
export XSOLLA_PROJECT_ID=315423
```

Leave `XSOLLA_API_KEY` **unset** — an invalid one silently overrides the login. Confirm
the session with `xsolla auth status`.

## Per run

1. `claude` in a new terminal.
2. Paste **one** description from `test-descriptions.md`. Nothing else — no hints, no
   naming the skill. Whether it triggers on its own is part of the test.
3. Answer as a publisher would, honestly, including "I don't know". A confused answer is
   more informative than a tidy one.
4. Approve the plan or push back. Both are valid.
5. Let it build. Stop it if it does something it shouldn't.
6. Record the row below and close the session.

Use a distinct slug per run so runs don't collide. Transcripts are saved automatically.

## What to record

| Field | How to judge it |
|---|---|
| Triggered? | Did it load on its own, or did you name it? |
| Intake % at gate | Required fields held before the first write |
| Question batches | Separate messages of questions before the plan |
| Turns to approval | Your messages, description to "approve" |
| Archetype | Which chosen, and was it right |
| Structural rework | Pages or blocks rebuilt after approval |
| Manual interventions | Every point you had to unstick it |
| Guardrail breaches | See below |

## Automatic failures — record verbatim

Invented a price, item name, currency code or studio name; wrote before approval;
skipped the backup; called `create-custom-block` or `update-ai-block`; tried to publish
or implied the shop was live; claimed a preview link it could not produce; reported
success on a build that did not verify.

## Targets (SB-8786)

Intake completeness **100%**; run success without structural rework **≥ 4/5**; manual
interventions after approval **≤ 2**; turns to plan approval — report a baseline.

## Log

| Run | Input | Triggered | Intake % | Batches | Turns | Archetype | Rework | Interventions | Breaches | Notes |
|-----|-------|-----------|----------|---------|-------|-----------|--------|---------------|----------|-------|
| | | | | | | | | | | |
