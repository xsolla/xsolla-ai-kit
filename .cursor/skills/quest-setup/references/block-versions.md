# Quests block versions

This is the only file that holds version pins. Verified at 2026-11-03. Sources: the pins
in [quests-block-brief.md](quests-block-brief.md) and [quests-block-flow.md](quests-block-flow.md)
as merged from PR #87, and the block contract read from the block repository at commit
0b1586eb59 (0.2.7), with 87d7aaf4f7 (0.1.12), 7c251007b6 (0.2.8) and f0ec907f69 (0.2.1
candidate) for the version differences.

## Pinned versions

| Item | Pin | Use |
|---|---|---|
| Quests block, stable | `0.1.5` | Current stable pin for ordinary block creation, as in the base. Its settings have no theme keys. |
| Quests block, appearance candidate | `0.2.7-qp-3256.0` | The exact version that supports `themeId` and `themeAppearance`. Use it only when its version is explicit. |
| Shop Builder CLI | `1.9.4` | A minimum: 1.9.4 or newer is supported. PR #87 also mentions `1.4.0`. The agent uses the version the CLI reports. |

## Known block versions and what they support

| Version | Supports |
|---|---|
| 0.1.5 | Plain block creation (the stable pin). No theme keys. |
| 0.1.12 | Stable line: plain creation and edits. No theme keys: no `themeId`, no `themeAppearance`. Supported for writes that need no theme. |
| 0.2.7 (candidate `0.2.7-qp-3256.0`) | Adds `themeId`, `themeAppearance`, `autoEvents` and `loginEventName`. Only the pinned candidate `0.2.7-qp-3256.0` is supported for theme writes; plain 0.2.7 is not pinned, so it is not supported for theme writes: ask once or stop. |
| 0.2.8 | Same as 0.2.7 but `autoEvents` and `loginEventName` are removed. Supported for theme writes. |
| 0.2.1 candidate | The only version with `backpackAction`. It is not a target for any write. |

## Version facts (snapshot of the block contract)

- Stable 0.1.12 has no theme keys: no `themeId`, no `themeAppearance`.
- 0.2.7 adds `themeId`, `themeAppearance`, `autoEvents` and `loginEventName`.
- 0.2.8 removes `autoEvents` and `loginEventName`. Never send either on 0.2.8 or newer.
- `backpackAction` exists only in candidate 0.2.1. It is not part of any pinned version.
- The Backpack Overlay action is blocked on upstream v2.

## Runtime check

The agent never trusts memory for a version. Before any block write it reads the block
version (and the CLI version) that Shop Builder or the CLI reports, then compares it with the
tables above.

- The CLI is **supported** when it is the pinned version or newer.
- A block version listed in the known-versions table is **supported** for the capabilities
  in its row. A write that needs a capability the version lacks (for example a theme on
  0.1.5 or 0.1.12) is **unsupported**.
- Any other reported block version is **unsupported** for writes that need a pinned
  capability.
- An unknown or unreported version: ask the user or stop. Do not guess, and do not infer
  support from version ordering or package metadata.
- For an unsupported version, say that the block needs a verified upgrade, make no write, and
  offer the supported path.
- A theme or appearance request on a block below the appearance candidate: the reply says the
  block's version cannot take a theme, names the pinned candidate version `0.2.7-qp-3256.0`, and
  offers the upgrade as a SEPARATE step with its own yes. It does not just refuse.
