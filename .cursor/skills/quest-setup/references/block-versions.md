# Quests block version

This file owns the block version. Checked 2026-11-15 against the CDN `default-data.json`.

## Pinned versions

| Version | Use |
|---|---|
| `0.2.24` | The latest. Every new block is added on it, themed or not. Its "See in Backpack" button works |
| `0.2.22` | Older. Same settings as `0.2.24`, so it takes theme writes too, but its "See in Backpack" button does nothing |
| Shop Builder CLI `1.9.4` | Minimum; newer supported. |

A block release means bumping this table and the gate's `QUESTS_VERSION` together.

## Block facts

- Never write `autoEvents` or `loginEventName`: they were removed from the block, and the
  block sends its built-in events once the player is authorized. Quest trigger names must
  match them exactly.
- Never write `gameSlug` or `visibleGameSlugs`. They are set by Xsolla for Xsolla Pages.
- `backpackAction` is dropped by the block. Backpack Overlay is not supported yet (upstream v2, never said to the publisher);
  keep any saved action-looking data as it is.

## Runtime check

Before any block write, read the block version (from the block summary) and the CLI version
(`xsolla --version`), and compare them with the table above.

- The CLI is **supported** when it is the pinned version or newer.
- Settings, quests, cards, move, duplicate, hide and show work on any saved block.
- A theme or appearance write is **supported** only on a block saved on `0.2.24` or `0.2.22`.
  On any other version it is **unsupported**.
- A block saved on `0.2.22` works, but its "See in Backpack" button does nothing. When the
  publisher's players need that button, or the publisher asks about it, tell them they can
  move the block to the latest version themselves in the Site Builder editor: select the block,
  then its **Version** setting. Never change the version yourself.
- An unknown or unreported version takes the same writes as an older block: settings,
  quests and cards go ahead; a theme or appearance write gets the older-block reply below.
  Never ask the publisher about versions.

## Theme request on an older block

No operation changes an existing block's version. For a theme or appearance request on a
block that is not on `0.2.24` or `0.2.22`, the reply:

- says in plain words that this block can't take theme settings;
- offers only a new Quests block with the same quests, and the old block hidden, never
  deleted, as its own plan with its own yes.

Never offer to upgrade, migrate or change the version of the existing block yourself.

## Versions stay internal

Versions are for the agent's checks only. No reply to the publisher names a block version,
a CLI version, a version number, or that a version is pinned, locked or newer than the
toolkit knows. Say what the block can or cannot do instead ("this block has no theme
settings"). The same goes for `gameSlug` and `visibleGameSlugs`, and the game slugs in them.
