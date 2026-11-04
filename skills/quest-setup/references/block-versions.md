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
- For an unsupported version, say that the block's version cannot take the change, make no
  write, and offer only a path the gate supports (below).

## Theme request on an older block

What the gate can and cannot do (`skills/shop-builder-assembly/scripts/block_ops.py`):

- An `add` operation can choose the version of the new block: `OPERATIONS["add"]` has
  `"optional": {"index", "values", "translations", "version"}` (line 174), and the version must
  be a key of `QUESTS_CAPABILITIES` (lines 568-574).
- No operation changes the version of an existing block. `update` allows only `values` and
  `translations` (line 176), `duplicate` takes only `block_id` and `index` (line 179), and
  `split_key` (lines 211-230) accepts no `version` leaf. Existing-block theme writes need the
  exact supported version already saved on the block (lines 577-602).

So for a theme or appearance request on a block whose version has no theme keys (for example
`0.1.5`), the reply:

- says in plain words that this block's version has no theme settings;
- says this toolkit cannot change the version of an existing block;
- offers only these, one at a time with one `Next:`: (1) a new Quests block added at the
  pinned `0.2.7-qp-3256.0`, with the same quests, and the old block hidden, never deleted, as
  its own plan with its own yes; or (2) the version change is done by the Site Builder team or
  in the editor, and the theme is applied afterwards once the block reports a theme-capable
  version.

Never offer to upgrade, migrate or change the version of the existing block.
