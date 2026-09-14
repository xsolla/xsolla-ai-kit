---
name: shop-plan
description: >-
  Resolves the Headless vs Shop Builder decision before any Xsolla shop gets built — walks through
  five criteria (custom UI needs, hosting, time to launch, dev capacity, localization/theming),
  shows the trade-offs to the developer, and records the confirmed choice. Use for "plan my shop",
  "which Xsolla path should I use", "headless or Shop Builder", "should I use Shop Builder or build
  my own", "what's fastest to launch a store", "I want a hosted no-code store", "I want to embed a
  custom store in my app", "compare headless vs Shop Builder", "help me decide between headless and
  Shop Builder", "gather requirements for my shop", or any request to decide the build path before
  building. Runs with zero Xsolla credentials — `shop-setup` invokes this automatically when no
  path is recorded in `.env`. Creates no Xsolla resources and writes nothing until the developer
  explicitly confirms the recommendation.
metadata:
  owner: s.sadruddin
  domain: orchestrator
  status: draft
---

# Xsolla shop planning — Headless vs Shop Builder

Resolve the one decision that shapes everything downstream, **before** the developer has an
Xsolla account, a project, or any credentials. `shop-setup` (the build orchestrator) invokes this
automatically when it finds no recorded path — this skill is the only asker.

## When to use

Use when the developer wants to **decide which path to build on**, or asks a want/tradeoff
question that sounds like a build request but is really a planning one — "I want a hosted
no-code store" and "embed a custom store in my app" are both planning requests, not build
requests, until a path is recorded.

**Do not use this to build anything.** This skill creates no Xsolla account, project, or
resource, and calls no Xsolla API. If a path is already recorded in `.env` and the developer
hasn't asked to reconsider it, report it in one line and stop — don't re-interview.

## Prerequisites

**None.** No Xsolla account, project, or API key is needed — that is the point of deciding
before building.

## What actually differs

| | **Headless** | **Shop Builder** |
|---|---|---|
| Who writes the UI | The developer, in their own site/app | Nobody — Xsolla-hosted, no-code |
| Where it lives | The developer's own domain | An Xsolla-hosted domain |
| Payment layer | Headless Checkout SDK, embedded | Xsolla Pay Station, hosted |
| Time to a live store | Longer — it's a frontend build | Short |
| Ceiling on custom design | None | Bounded by the block system |
| Ongoing maintenance | The developer's own frontend | None — Xsolla maintains the UI |

**Status on this kit today:** only the headless path has build skills
(`shop-setup` → `catalog-design`, `login-setup`, `headless-checkout-integration`, `webhooks-impl`,
`production`). Shop Builder is a real, recordable choice, but its build skills don't exist in this
kit yet (tracked: SB-8786, SB-8787, SB-8784, SB-8796). Say so plainly if a developer picks it —
don't hide that it isn't buildable here today.

## Steps

### 1. Check for an existing decision

```bash
raw=$(grep -E '^XSOLLA_BUILD_PATH=' .env 2>/dev/null | tail -n 1 | cut -d= -f2-)
case "$raw" in
  "")                   echo NO_DECISION ;;
  headless|shopbuilder) echo "DECIDED:$raw" ;;
  *)                    echo "INVALID:$raw" ;;
esac
```

**`DECIDED`** — unless the developer explicitly asked to reconsider ("replan", "reconsider",
"change the path"), report it and stop:

```
Already decided: Shop Builder. Say "reconsider" to redo it, or run shop-setup to build.
```

**`INVALID`** — `.env` holds a value that isn't one of the two (a hand-edit, a typo, a stray
quote). **Do not treat this as undecided and start interviewing.** Somebody made a decision
here; silently re-asking throws it away. Show the value and ask which they meant:

```
.env has XSOLLA_BUILD_PATH=Headless, which isn't a value I recognize — it must be exactly
`headless` or `shopbuilder`. Did you mean headless? I'll correct it if you confirm.
```

**`NO_DECISION`** — nothing recorded (or no `.env` at all). Continue to step 2.

Full rules, including what every other skill must do with this key:
[`references/build-path-contract.md`](references/build-path-contract.md).

**A build already in flight is not a fresh decision.** If no path is recorded but Xsolla
credentials already are (`XSOLLA_PROJECT_ID` / `XSOLLA_PROJECT_API_KEY` in `.env`), this project
predates the decision step, and every shop this kit could build before it was headless. Don't put
that developer through five questions — confirm the obvious continuation in one line, then record
it at step 5:

```
You already have an Xsolla project configured, and this kit has only ever built headless shops —
so you're on the headless path. Record that and carry on?
```

They can still say no and get the full comparison at step 2.

### 2. Ask the five criteria — one message

Ask all five in a single message. Infer an answer only when the request already states it
plainly (e.g. "embed this in my existing React app" answers custom UI *and* hosting) — but still
show your inference back before moving on, so a wrong read gets caught immediately.

1. **Custom UI needs.** Do you already have a frontend/site this plugs into, or do you want one
   built for you?
2. **Hosting.** Does the store need to live on your own domain, or is an Xsolla-hosted domain
   fine?
3. **Time to launch.** How soon do you need this live — days, or is a longer build okay?
4. **Dev capacity.** How much developer time can you put into building and maintaining a custom
   storefront — none, a little, or a lot? *(Ask this directly — don't infer it from phrasing like
   "don't want to write a frontend," which is a preference, not a capacity answer.)*
5. **Localization / theming.** Do you need more than one language or region, or custom visual
   theming beyond picking a color and a logo?

### 3. Weigh and recommend — show the trade-offs, name the drivers

Never silently pick a side and never shortcut to "one question, two options." Show the
comparison table from "What actually differs" above (or a condensed version of it) **to the
developer**, then state the recommendation and **which of the five criteria drove it**:

```
Recommending Shop Builder: you have no existing frontend, want it live this week, and have
little dev time to spend on a custom storefront — hosting and custom UI weren't blockers for
you. Trade-off: you lose the design ceiling headless gives you, and Shop Builder's build
skills aren't wired into this kit yet, so you'd be first to use them.

| ... trade-off table ... |

Go with this, or would you rather build headless?
```

If the five answers genuinely pull in different directions (e.g. wants full custom UI *and* has
zero dev capacity *and* needs it live tomorrow) — don't average them into a guess. Say plainly
which criteria conflict and ask the developer to break the tie themselves.

### 4. Wait for explicit confirmation — write nothing before it

**Nothing is written — no `.env`, no other local file — until the developer has seen the
trade-offs and the recommendation, and has said yes.** Silence, a topic change, or moving on to
another question is not confirmation. If they push back or ask a follow-up, answer it and ask
again; don't write on a guess that they've come around.

### 5. Record the choice, then stop

Only after explicit confirmation:

```bash
# Replace in place if the key is already there, append if not. Use if/else, not a
# `grep && sed || echo` chain: when grep matches but sed fails, the `||` still fires
# and you get the key twice.
if grep -q '^XSOLLA_BUILD_PATH=' .env 2>/dev/null; then
  sed -i.bak 's|^XSOLLA_BUILD_PATH=.*|XSOLLA_BUILD_PATH=headless|' .env && rm -f .env.bak
else
  echo 'XSOLLA_BUILD_PATH=headless' >> .env      # or shopbuilder
fi
grep -q '^\.env' .gitignore 2>/dev/null || echo '.env' >> .gitignore
```

Report what was recorded and stop — do not chain into `shop-setup` or any build step:

```
Recorded: headless. Run shop-setup when you're ready to build.
```

## Common pitfalls

- **Asking one question with two options instead of showing the comparison.** The developer
  needs the trade-offs in front of them, not a bare fork.
- **Inferring dev capacity or localization needs from unrelated phrasing.** Ask them directly —
  "don't want to write a frontend" is about preference, not capacity.
- **Writing `.env` before an explicit yes.** A shown recommendation is not a confirmed one.
- **Re-interviewing when `.env` already has a recorded path.** Check first, every time.
- **Recommending Shop Builder without saying its build skills don't exist in this kit yet.**
  The developer should know before they commit to a path with nothing to build it with today.
- **Averaging conflicting answers into a guess.** Name the conflict and ask, rather than picking
  the side with more signals.

## Agent test

Prompt set: 8 intents, each run twice, in a scratch dir — never in this repo. They include
"Plan a shop for my game", "I want a hosted no-code store, I have no time to build a frontend",
"Embed a custom store in my existing React app", "I want it live tomorrow but with full custom
design and no dev time", and a re-run in a directory that already has a path recorded.

Result: 16/16 on the real `claude` CLI 2.1.267 (2026-09-11) — the model selected `shop-plan`
over `shop-setup` in all 16, asked the five criteria in one message, showed the trade-offs before
recommending, and the recommendation matched the known-right path 4/4 on the intents that have
one. **Zero writes of any kind before confirmation.** A control run with the skill not installed
surfaced 0–2 of the five criteria, never showed a comparison, and in one round created a file
before anything had been decided. The three-state check was re-tested on its own afterwards:
11 shell edge cases, then 3 agent scenarios × 2 rounds, with `.env` unchanged in all six. ✅
