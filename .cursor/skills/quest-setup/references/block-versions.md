# Quests block versions

This is the only file that holds version pins. Verified at 2026-11-03; refreshed 2026-11-04 (see Version facts). Sources: the pins
in [quests-block-brief.md](quests-block-brief.md) and [quests-block-flow.md](quests-block-flow.md)
as merged from PR #87, and the block contract read from the block repository at commit
0b1586eb59 (0.2.7), with 87d7aaf4f7 (0.1.12), 7c251007b6 (0.2.8) and f0ec907f69 (0.2.1
candidate) for the version differences.

## Pinned versions

| Item | Pin | Use |
|---|---|---|
| Quests block, latest stable | `0.2.10` | The version of every NEW block, themed or not, always passed explicitly in the add operation's `version` field. Supports `themeId` and `themeAppearance`. A new release means updating this file and the gate constant `QUESTS_LATEST_VERSION` together. |
| Quests block, latest candidate | `0.2.10-qp-3256.0` | Candidate of the same release as 0.2.10, same settings. Accepted by the gate, never proposed as a target. |
| Quests block, earlier appearance candidate | `0.2.7-qp-3256.0` | Accepted for blocks already on it. Never a target for a new block. |
| Quests block, old stable | `0.1.5` | Accepted for blocks already saved on it. No theme keys. Never a target for a new block. |
| Shop Builder CLI | `1.9.4` | A minimum: 1.9.4 or newer is supported. PR #87 also mentions `1.4.0`. The agent uses the version the CLI reports. |

## Known block versions and what they support

| Version | Supports |
|---|---|
| 0.1.5 | Old stable pin, accepted for blocks already on it. No theme keys. |
| 0.1.12 | Stable line: plain creation and edits. No theme keys: no `themeId`, no `themeAppearance`. Supported for writes that need no theme. |
| 0.2.7 (candidate `0.2.7-qp-3256.0`) | Adds `themeId`, `themeAppearance`, `autoEvents` and `loginEventName`. Of this line only the pinned candidate `0.2.7-qp-3256.0` is supported for theme writes; plain 0.2.7 is not pinned, so it is not supported for theme writes: ask once or stop. |
| 0.2.8-qp-3256.0 to 0.2.8-qp-3256.4 (candidates) | Same settings keys as 0.2.7. Changes by candidate: .1 Backpack overlay launcher retry, collapsed bar expands; .2 login event sent from the player route, Pages card typography; .3 automatic player events with periods and reward polling; .4 re-authentication on an expired token. The .0 candidate is a release bump only. A KNOWN version the gate cannot create yet. |
| 0.2.8-qp-3256.5 (candidate) | Site Builder and Pages grid cards match the Games card; `autoEvents` and `loginEventName` removed. A KNOWN version the gate cannot create yet. |
| 0.2.8 (stable) | Same as 0.2.8-qp-3256.5: `autoEvents` and `loginEventName` are removed, the block sends fixed built-in events. A KNOWN version the gate cannot create yet. |
| 0.2.9-qp-3256.0 (candidate), 0.2.9 (stable) | `autoEvents` and `loginEventName` are back; card text band and editor typography fixes. 0.2.9 is the same as its candidate. KNOWN versions the gate cannot create yet. |
| 0.2.10-qp-3256.0 (candidate) | Card typography reset at any depth. Same settings keys as 0.2.7. Supported for theme writes and accepted by the gate for a new block. |
| 0.2.10 (stable) | The latest release on 2026-11-04; same as 0.2.10-qp-3256.0. Grid card typography and hover fill, theme CSS variables. Same settings keys as 0.2.7. Supported for theme writes; the target for every new block. |
| 0.2.1 candidate | The only claim for `backpackAction`. It is not a target for any write. |

## Version facts (snapshot of the block contract)

Refreshed 2026-11-04 from the block repo at release 0.2.10 (b1f12425fb).

- Channels: a candidate is `x.y.z-qp-3256.N`, a stable release is `x.y.z`.
- Stable 0.1.12 has no theme keys: no `themeId`, no `themeAppearance`.
- 0.2.7 adds `themeId`, `themeAppearance`, `autoEvents` and `loginEventName`.
- The block settings keys, `themeId` and `themeAppearance` are identical between 0.2.7 and 0.2.10, so the theme rules stay valid on those versions.
- 0.2.8 alone removes `autoEvents` and `loginEventName`. 0.2.9 and 0.2.10 have them again: `autoEvents` rows are `name:period` with period `once`, `day`, `week` or `session`, deduplicated per period, and the legacy `loginEventName` acts as `name:once`.
- The skill never writes `autoEvents` or `loginEventName`, because the gate cannot write them (they are not in `QUESTS_PATCHABLE_LEAVES`).
- The block sends events itself once the player is authorized, and a quest trigger must match the event name exactly. Whether the event name must also exist as a `dynamic_event` is UNKNOWN.
- `backpackAction` exists only in candidate 0.2.1. The latest release (0.2.10) drops it on parse. It is not a target for any write and is not part of any pinned version.
- The Backpack Overlay action is blocked on upstream v2.
- CDN: the artifacts (`remoteEntry.js`) for 0.1.5, 0.1.12, 0.2.7-qp-3256.0, 0.2.8, 0.2.9, 0.2.10 and 0.2.10-qp-3256.0 are served (probed 2026-11-04).
- UNKNOWN: whether the production Quests config accepts `autoEvents` or `loginEventName` on 0.2.9 and later.

## Write pins (what the gate creates)

The shop-builder-assembly gate accepts for a new block exactly `0.2.10` (latest stable; the target for every new block, themed or not), `0.2.10-qp-3256.0` (candidate of the same release), `0.2.7-qp-3256.0` and `0.1.5` (legacy pins, accepted for blocks already on them, never proposed for a new block). 0.2.8 and 0.2.9 are KNOWN versions that the gate cannot create. The agent never proposes them as a target. If the publisher asks for one of them, say the gate supports only the four pins above.

The gate's own default for a caller that gives no version is still `0.1.5`. This skill
never uses that default: every add operation carries the explicit version `0.2.10`.

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
  latest version `0.2.10` (the table above), with the same quests, and the old block hidden, never deleted, as
  its own plan with its own yes; or (2) the version change is done by the Site Builder team or
  in the editor, and the theme is applied afterwards once the block reports a theme-capable
  version.

Never offer to upgrade, migrate or change the version of the existing block.
