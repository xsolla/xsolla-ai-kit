---
name: shop-plan
description: >-
  Resolves the build path — headless, Shop Builder, or Game Web Portal — before any Xsolla shop
  gets built. Walks through six criteria (custom UI needs, hosting, time to launch, dev capacity,
  localization/theming, and whether the game needs a home around the store), shows the trade-offs
  to the developer, and records the confirmed choice. Use for "plan my shop", "which Xsolla path
  should I use", "headless or Shop Builder", "should I use Shop Builder or build my own", "what's
  fastest to launch a store", "I want a hosted no-code store", "I want to embed a custom store in
  my app", "compare headless vs Shop Builder", "do I need a Game Web Portal or just a shop",
  "gather requirements for my shop", or any request to decide the build path before building.
  Runs with zero Xsolla credentials — `shop-setup` invokes this automatically when no path is
  recorded in `.env`. Creates no Xsolla resources and writes nothing until the developer
  explicitly confirms the recommendation.
metadata:
  owner: s.sadruddin
  domain: orchestrator
  status: draft
---

# Xsolla shop planning — headless, Shop Builder, or Game Web Portal

Resolve the one decision that shapes everything downstream, **before** the developer has an
Xsolla account, a project, or any credentials. `shop-setup` (the build orchestrator) invokes this
automatically when it finds no recorded path — this skill is the only asker.

## When to use

Use when the developer wants to **decide which path to build on**, or asks a want/tradeoff
question that sounds like a build request but is really a planning one — "I want a hosted
no-code store" and "embed a custom store in my app" are both planning requests, not build
requests, until a path is recorded.

**Do not use this to build anything.** This skill creates no Xsolla account, project, or
resource, calls no Xsolla API, and runs no `xsolla` command — not even `--version`; checking the
CLI belongs to `merchant-setup`. If a path is already recorded in `.env` and the developer
hasn't asked to reconsider it, report it in one line and stop — don't re-interview.

## Prerequisites

**None.** No Xsolla account, project, or API key is needed — that is the point of deciding
before building.

## Happy path

"I'm a solo indie dev, no website, need a store live this week" → no path in `.env`, so ask the six
criteria in one message → show the comparison, recommend Shop Builder and name the criteria that
drove it → developer says yes → `XSOLLA_BUILD_PATH=shopbuilder` recorded → stop.

## What actually differs

| | **Headless** | **Shop Builder** | **Game Web Portal** |
|---|---|---|---|
| What it is | A store in the developer's own site/app | A hosted store | A hosted game home — Home, News, Rewards, Community, optional Launcher — around a Web Shop |
| Who writes the UI | The developer, in their own site/app | Nobody — Xsolla-hosted, no-code | Nobody — Xsolla-hosted, no-code |
| Where it lives | The developer's own domain | An Xsolla-hosted domain | An Xsolla-hosted domain |
| Payment layer | Headless Checkout SDK, embedded | Xsolla Pay Station, hosted | Xsolla Pay Station, hosted |
| Time to a live store | Longer — it's a frontend build | Short | Short for the store; the sections need content |
| Ceiling on custom design | None | Bounded by the block system | Bounded by the block system |
| Ongoing maintenance | The developer's own frontend | None — Xsolla maintains the UI | None for the UI; the news and rewards content is the developer's |

**Whichever path, recording the choice is where this skill stops — `shop-setup` does the building.**
Headless runs `shop-setup` → `catalog-design`, `login-setup`, `headless-checkout-integration`,
`webhooks-impl`, `production`. Shop Builder runs the same shared foundation, then hands the
storefront to `shop-builder-assembly`, and finishes with `webhooks-impl`. Game Web Portal runs the
same foundation, then hands the storefront to `game-web-portal`, and finishes with
`webhooks-impl`.

## Steps

### 1. Check for an existing decision

```bash
raw=$(grep -E '^XSOLLA_BUILD_PATH=' .env 2>/dev/null | tail -n 1 | cut -d= -f2-)
case "$raw" in
  "")                          echo NO_DECISION ;;
  headless|shopbuilder|portal) echo "DECIDED:$raw" ;;
  *)                           echo "INVALID:$raw" ;;
esac
```

**`DECIDED`** — unless the developer explicitly asked to reconsider ("replan", "reconsider",
"change the path"), report it and stop:

```
Already decided: Shop Builder. Say "reconsider" to redo it, or run shop-setup to build.
```

**`INVALID`** — `.env` holds a value that isn't one of the three (a hand-edit, a typo, a stray
quote). **Do not treat this as undecided and start interviewing.** Somebody made a decision
here; silently re-asking throws it away. Show the value and ask which they meant:

```
.env has XSOLLA_BUILD_PATH=Headless, which isn't a value I recognize — it must be exactly
`headless`, `shopbuilder` or `portal`. Did you mean headless? I'll correct it if you confirm.
```

**`NO_DECISION`** — nothing recorded (or no `.env` at all). Continue to step 2.

Full rules, including what every other skill must do with this key:
[`references/build-path-contract.md`](references/build-path-contract.md).

**Credentials are not a decision.** A project with `XSOLLA_PROJECT_ID` / `XSOLLA_PROJECT_API_KEY`
in `.env` but no recorded path has an Xsolla project, not a chosen storefront — every path builds on
the same account and catalog. Ask the six criteria as normal. Say what you can see, so the
developer knows the account work isn't being redone:

```
You already have an Xsolla project configured — that part carries over whichever path you pick.
What's still open is how the storefront itself gets built, so six quick questions.
```

### 2. Ask the six criteria — one message

Ask all six in a single message. When `shop-setup` invoked this skill, the same message also asks
the rest of its [intake](../shop-setup/references/onboarding-contract.md#intake), so the developer
answers one round of questions, not two. Infer an answer only when the request already states it
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
6. **Game home.** Does the game need a home around the store — news, rewards, community, a
   launcher — or only a store?

### 3. Weigh and recommend — show the trade-offs, name the drivers

Never silently pick a side and never shortcut to "one question, two options." Show the
comparison table from "What actually differs" above (or a condensed version of it) **to the
developer**, then state the recommendation and **which of the six criteria drove it**.
Criterion 6 separates a portal from a shop: a game home around the store points to the Game Web
Portal, and only a store leaves the choice between headless and Shop Builder to the other five:

```
Recommending Shop Builder: you have no existing frontend, want it live this week, and have
little dev time to spend on a custom storefront — hosting and custom UI weren't blockers for
you, and you only need a store. Trade-off: you lose the design ceiling headless gives you.

| ... trade-off table ... |

Go with this, or would you rather build headless?
```

If the answers genuinely pull in different directions (e.g. wants full custom UI *and* has
zero dev capacity *and* needs it live tomorrow) — don't average them into a guess. Say plainly
which criteria conflict and ask the developer to break the tie themselves.

### 4. Wait for explicit confirmation — write nothing before it

**Nothing is written — no `.env`, no other local file — until the developer has seen the
trade-offs and the recommendation, and has said yes.** Silence, a topic change, or moving on to
another question is not confirmation. Neither is a "yes" that arrives before the comparison and
recommendation were shown: show them first, then ask again. If they push back or ask a follow-up,
answer it and ask again; don't write on a guess that they've come around.

### 5. Record the choice, then stop

Only after explicit confirmation:

```bash
# Replace in place if the key is already there, append if not. Use if/else, not a
# `grep && sed || echo` chain: when grep matches but sed fails, the `||` still fires
# and you get the key twice.
if grep -q '^XSOLLA_BUILD_PATH=' .env 2>/dev/null; then
  sed -i.bak 's|^XSOLLA_BUILD_PATH=.*|XSOLLA_BUILD_PATH=headless|' .env && rm -f .env.bak
else
  echo 'XSOLLA_BUILD_PATH=headless' >> .env      # or shopbuilder / portal
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
- **Averaging conflicting answers into a guess.** Name the conflict and ask, rather than picking
  the side with more signals.
- **Reading existing credentials as a path.** An account and a catalog are shared by every path;
  only `XSOLLA_BUILD_PATH` records a decision.

## Known limitations

- **Only the build path is planned.** Catalog and images/themes are not gathered here yet.
- **Only `shop-setup` and `game-web-portal` check the recorded path.** No other skill reads it, so
  invoking one directly (e.g. `headless-checkout-integration` on a `shopbuilder` project) isn't
  stopped.
- **The step 1 and step 5 snippets are compound shell commands**, so Claude Code may ask the
  developer to approve them.

## Agent test

Prompt: "I'm a solo indie developer and I want to sell a few skins and a currency pack for my
game. I have no website and no frontend skills or time to build one. An Xsolla-hosted domain is
totally fine. I need it live this week. English only, and just my logo and brand colors are enough."

Result: `shop-plan` selected, the comparison shown, Shop Builder recommended with the criteria that
drove it named and the intake asked in the same message, nothing written until "yes", then
`shopbuilder` recorded once and the agent stopped. Across 22 fixed intents, two rounds each
(2026-10-02, including two portal intents and a store that is not a portal): the recommended path
matched the known answer 26/26, zero writes or `xsolla` calls before confirmation across 34 runs,
and headless prompts still reached their own skills 10/10. ✅
