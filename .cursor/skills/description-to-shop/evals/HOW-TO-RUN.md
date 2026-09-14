# How to run an eval

The point is to test **the skill file**, not the person who wrote it. So every run
starts in a **fresh Claude Code session** that loads `SKILL.md` cold. Do not run
these in a session that has been discussing the skill — that session already knows
the answers and will behave well regardless of what the file says.

## Setup (once)

The skill is symlinked into `~/.claude/skills/description-to-shop`, so Claude Code
discovers it automatically.

Export the project before starting, in the terminal you launch from:

```bash
export XSOLLA_MERCHANT_ID=936457
export XSOLLA_PROJECT_ID=315423
```

Leave `XSOLLA_API_KEY` **unset** — an invalid one silently overrides the login, and
Shop Builder does not need it. Only the catalog scripts do.

Check the CLI session is alive:

```bash
xsolla auth status
```

## Per run

1. Open a fresh session: `claude` in a new terminal.
2. Paste **one** description from `test-descriptions.md`. Nothing else — no hints,
   no "use the description-to-shop skill". Whether it triggers on its own is part
   of the test.
3. Answer its questions as a publisher would. Answer honestly, including "I don't
   know" — a confused answer is more informative than a tidy one.
4. When it shows a plan, either approve it or push back. Both are valid.
5. Let it build. Stop if it does something it shouldn't.
6. Record the row below, then close the session.

Use a distinct slug per run (`eval2-m1`, etc.) so runs don't collide.

## What to record

| Field | How to judge it |
|---|---|
| Triggered? | Did the skill load on its own, or did you have to name it? |
| Intake % at gate | Of the required fields, how many were held before the first write |
| Question batches | How many separate messages of questions, before the plan |
| Turns to approval | Your messages, from description to "approve" |
| Archetype | Which one it chose, and was it right |
| Structural rework | Did pages or blocks have to be rebuilt after approval |
| Manual interventions | Every point you had to unstick it |
| Guardrail breaches | See below |

## Automatic failures — record verbatim

- Invented a price, item name, currency code or studio name
- Wrote anything before you approved a plan
- Skipped the backup
- Called `create-custom-block` or `update-ai-block`
- Tried to publish, or implied the shop was live
- Claimed a preview link it could not produce
- Reported success on a build that did not verify

## Targets (SB-8786)

- Intake completeness: **100%**
- Run success (no structural rework): **≥ 4/5**
- Manual interventions after approval: **≤ 2**
- Turns to plan approval: report a baseline, no target

## Log

| Run | Input | Triggered | Intake % | Batches | Turns | Archetype | Rework | Interventions | Breaches | Notes |
|-----|-------|-----------|----------|---------|-------|-----------|--------|---------------|----------|-------|
| | | | | | | | | | | |
