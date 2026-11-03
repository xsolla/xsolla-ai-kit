# Quests block versions

This is the only file that holds version pins. Verified at 2026-11-03. Sources: the pins
in [quests-block-brief.md](quests-block-brief.md) and [quests-block-flow.md](quests-block-flow.md)
as merged from PR #87, and the block contract read from the block repository at commit
0b1586eb59 (0.2.7), with 87d7aaf4f7 (0.1.12), 7c251007b6 (0.2.8) and f0ec907f69 (0.2.1
candidate) for the version differences.

## Pinned versions

| Item | Pin | Use |
|---|---|---|
| Quests block, stable | `0.1.5` | Ordinary block creation. Its settings have no theme keys. |
| Quests block, appearance candidate | `0.2.7-qp-3256.0` | The exact version that supports `themeId` and `themeAppearance`. Use it only when its version is explicit. |
| Shop Builder CLI | `1.9.4` | Minimum named in quests-block-flow.md. PR #87 also mentions `1.4.0`. Both are recorded here, and the agent uses the version the CLI reports. |

## Version facts (snapshot of the block contract)

- Stable 0.1.12 has no theme keys: no `themeId`, no `themeAppearance`.
- 0.2.7 adds `themeId`, `themeAppearance`, `autoEvents` and `loginEventName`.
- 0.2.8 removes `autoEvents` and `loginEventName`. Never send either on 0.2.8 or newer.
- `backpackAction` exists only in candidate 0.2.1. It is not part of any pinned version.
- The Backpack Overlay action is blocked on upstream v2.

## Runtime check

The agent never trusts memory for a version. Before any block write it reads the block
version (and the CLI version) that Shop Builder or the CLI reports, then compares it with the
table above.

- A reported version equal to a pinned version is **supported**.
- Any other reported version is **unsupported** for writes that need a pinned capability.
- An unknown or unreported version: ask the user or stop. Do not guess, and do not infer
  support from version ordering or package metadata.
- For an unsupported version, say that the block needs a verified upgrade, make no write, and
  offer the supported path.
