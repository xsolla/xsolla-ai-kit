# The build-path contract

One shop, one path. This file is the normative definition of how that path is recorded and
how every other skill must read it. If you are writing a skill that behaves differently for
headless than for Shop Builder, implement against this file rather than copying a grep out of
another skill.

## The record

| | |
|---|---|
| **Key** | `XSOLLA_BUILD_PATH` |
| **Location** | `.env` in the project root |
| **Values** | exactly `headless` or `shopbuilder` — lowercase, no other spelling, no quotes, no surrounding whitespace |
| **Written by** | `shop-plan`, and only after the developer explicitly confirms the choice |
| **Read by** | any skill whose behaviour depends on the path |

If the key somehow appears more than once, the **last** occurrence wins, matching how `.env`
loaders normally behave. `shop-plan` replaces in place rather than appending, so this should
not arise.

## What a consumer must do

There are **three** states, not two, and the third is the one that gets missed:

| State | What it means | The consumer must |
|---|---|---|
| Key absent | Nobody has decided yet | Invoke `shop-plan` and stop. Never assume a default path. |
| Value is `headless` or `shopbuilder` | A developer confirmed this | Proceed if it is this skill's path; halt if it is not |
| Key present, value is anything else | `.env` was hand-edited or corrupted | **Halt and tell the developer.** Never silently re-ask |

The third row matters because the obvious one-line check collapses it into the first:

```bash
# WRONG — a typo like `Headless` fails to match, so this reports "not decided"
# and the developer gets re-interviewed about a choice they already made.
grep -qE '^XSOLLA_BUILD_PATH=(headless|shopbuilder)$' .env
```

Discarding a recorded decision is worse than stopping, because the developer has no way to
tell that it happened — they just get asked the same question twice and may answer differently
the second time, which is exactly the "one path per shop" rule breaking.

## How to check it

```bash
raw=$(grep -E '^XSOLLA_BUILD_PATH=' .env 2>/dev/null | tail -n 1 | cut -d= -f2-)
case "$raw" in
  "")                   echo NO_DECISION ;;
  headless|shopbuilder) echo "DECIDED:$raw" ;;
  *)                    echo "INVALID:$raw" ;;
esac
```

`NO_DECISION` also covers `.env` not existing, `.env` being empty, and the key being present with
an empty value (`XSOLLA_BUILD_PATH=`) — in all of those, nothing was actually recorded, so asking
is correct rather than destructive.

A quoted value (`XSOLLA_BUILD_PATH="headless"`) is `INVALID`, not `DECIDED`. That is deliberate:
halting to ask costs one turn, whereas accepting loose spellings means every consumer has to agree
on the same set of them, and they will not.

## Rules for anyone writing to `.env`

- **Only `shop-plan` writes `XSOLLA_BUILD_PATH`.** Two writers means two truths, and nothing
  downstream can then tell which one the developer actually agreed to.
- **Scope your deletes to your own keys.** A skill that clears `^XSOLLA_` wholesale before
  writing its own values will erase this one. `merchant-setup` had exactly this bug: it ran
  `sed '/^XSOLLA_/d'` before writing credentials, silently wiping the recorded path.
- **Write only after the developer has confirmed.** The plan is shown first, written second —
  local files included, not just Xsolla resources.
