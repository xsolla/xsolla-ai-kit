# Quests block versions

This file owns version pins and capability checks. Snapshot refreshed 2026-11-04 from
release 0.2.10 (`b1f12425fb`); earlier contract sources: `0b1586eb59` (0.2.7),
`87d7aaf4f7` (0.1.12), `7c251007b6` (0.2.8), `f0ec907f69` (0.2.1 candidate).

## Pinned versions

| Version | Capability and write boundary |
|---|---|
| `0.2.10` | Latest stable, explicit target for EVERY new block, themed or not. Theme writes supported. |
| `0.2.10-qp-3256.0` | Same-release candidate, same settings; accepted by gate, never proposed as target. Theme writes supported. |
| `0.2.7-qp-3256.0` | Legacy appearance candidate; accepted on saved blocks, never proposed for new ones. Theme writes supported. |
| `0.1.5` | Legacy stable; accepted on saved blocks, no theme keys, never proposed for new ones. Gate's omitted-version default only. |
| `0.1.12` | Plain creation/edits only, no theme keys (`themeId`, `themeAppearance`); supported for writes without theme. Not an accepted gate add pin. |
| `0.2.7` | Adds `themeId`, `themeAppearance`, `autoEvents`, `loginEventName`, but plain stable is not pinned for theme writes: ask once or stop. |
| `0.2.8-qp-3256.0` to `0.2.8-qp-3256.4` | Same settings as 0.2.7, including event fields. Known, gate cannot create. |
| `0.2.8-qp-3256.5`, `0.2.8` | `autoEvents` and `loginEventName` removed; fixed built-in events. Known, gate cannot create. |
| `0.2.9-qp-3256.0`, `0.2.9` | Event fields restored, same candidate/stable settings. Known, gate cannot create. |
| `0.2.1` candidate | Only claim for `backpackAction`; never a write target or pinned version. |
| Shop Builder CLI `1.9.4` | Minimum; newer supported. Historical PR #87 also mentions 1.4.0; use the actual reported version. |

## Version facts (snapshot of the block contract)

- Candidate channels are `x.y.z-qp-3256.N`; stable releases are `x.y.z`.
- Settings, `themeId` and `themeAppearance` are identical between 0.2.7 and 0.2.10.
  Event fields return in 0.2.9/0.2.10: `autoEvents` rows are `name:period`, with
  `once`, `day`, `week`, `session`, deduplicated per period; legacy `loginEventName` is `name:once`.
- Never write `autoEvents` or `loginEventName`: absent from `QUESTS_PATCHABLE_LEAVES`.
  The block sends events once the player is authorized; quest trigger names must match
  exactly. Whether the name must also exist as `dynamic_event` is unknown.
- Latest 0.2.10 drops `backpackAction` on parse. Backpack Overlay is blocked on upstream v2;
  preserve obsolete saved action-looking data as opaque, never retarget it.
- CDN `remoteEntry.js` artifacts for 0.1.5, 0.1.12, 0.2.7-qp-3256.0, 0.2.8, 0.2.9,
  0.2.10 and 0.2.10-qp-3256.0 were served in 2026-11-04 probes. This is not write support.
- Unknown: whether production Quests config accepts event fields on 0.2.9 or later.

## Write pins (what the gate creates)

Gate adds accept exactly `0.2.10`, `0.2.10-qp-3256.0`, `0.2.7-qp-3256.0`, `0.1.5`.
Only latest stable is proposed. For a requested 0.2.8/0.2.9, state only those four pins
are supported. The gate's own omitted-version default remains `0.1.5`; this skill
always supplies explicit `version: 0.2.10`. New releases require updating this file
and gate `QUESTS_LATEST_VERSION` together.

## Runtime check

The agent never trusts memory for a version. Before any block write it reads the block
version (and the CLI version) that Shop Builder or the CLI reports, then compares it with the
table above.

- The CLI is **supported** when it is the pinned version or newer.
- A block version listed in the capability table is **supported** for the capabilities
  in its row. A write that needs a capability the version lacks (for example a theme on
  0.1.5 or 0.1.12) is **unsupported**.
- Any other reported block version is **unsupported** for writes that need a pinned
  capability.
- An unknown or unreported version: ask the user or stop. Do not guess, and do not infer
  support from version ordering or package metadata.
- For an unsupported version, say that the block's version cannot take the change, make no
  write, and offer only a path the gate supports (below).

## Theme request on an older block

The gate can choose a supported version only on `add`. No operation changes an
existing block's version; `update` writes values/translations, and `duplicate` copies
without retargeting. Theme updates/resets require the exact supported saved version.

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
