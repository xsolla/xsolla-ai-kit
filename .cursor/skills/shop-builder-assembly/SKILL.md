---
name: shop-builder-assembly
description: >-
  Use for building or changing an Xsolla Shop Builder site from a validated shop brief
  (pages, navigation, blocks, localization, catalog links, game-type presets), and for
  block_operations edits to the Quests block of an existing Shop Builder site (add,
  update, reset, move, duplicate, hide, show). Not for one-off edits to a
  header, theme, or colour (Site Builder editor), not the entry point for "build me a
  shop" (shop-setup routes here), and not for headless storefronts.
metadata:
  owner: k.shah
  domain: store
---

# Shop Builder Assembly

Build an unpublished Publisher Account **Shop Builder site** (not a custom frontend) in a
dedicated non-partner test project through `xsolla shopbuilder`.

A Game Web Portal is built by `game-web-portal`, not here. First read `XSOLLA_SITE_KIND` with the
[build-path contract's check](../shop-plan/references/build-path-contract.md#the-site-kind-shop-builder-only):
for `portal`, hand off to `game-web-portal` and stop; an invalid value halts. A shop continues.

## Safety gate

Run these steps in order before any remote write. Writes need a valid shop brief. Do the
read-only steps 1 to 4 first, then show one plan; there is no draft plan before it.

1. Run `scripts/preflight.py <brief.json>` and pass the approval-list path from
   [shop brief](references/shop-brief.md) as `--approved-test-projects` (expand `~`
   first). Only the scripts read that list: never read, search for, stat, list, create,
   edit, or suggest changing it. Read back the matched merchant ID, project ID,
   environment, approval reference, active Publisher login, target site, and catalog
   groups. Preflight also switches CLI sandbox mode off, without asking: a Shop Builder
   request implies it. Show each line of its `plan_notes` as it is (for example "Using the
   CLI test environment (sandbox off)") as a plan bullet. When preflight reports a
   `cli_environment`, add `--environment <name>` to every `xsolla` command you run
   yourself. When the site needs a common layout (a new site, or one without it) and the
   CLI has no `shopbuilder create-block`, preflight prints "the common layout needs a
   newer Xsolla CLI; the site is built without it". Tell the user in the plan, before
   any write: a site without the common layout won't open in the Editor, Publish or
   private preview. If preflight refuses, reply in the blocked shape.
2. If the CLI merchant or project differs from the brief, stop and ask which project the
   publisher means. Never change the CLI config yourself or override later commands.
3. If the target site exists, export it before the first write:
   `scripts/backup_shop.py --brief <brief.json> --slug <slug> --output-dir <dir>`.
4. Render with `scripts/render_plan.py <brief.json> --structure <backup-dir>/structure.json`
   and show the plan in the Plan shape. Preserve configured blocks lacking replacement
   data. Omit `--structure` only for a new slug's bootstrap-only plan.
5. Ask for explicit confirmation of the plan's `confirmation_id` immediately before the
   first remote write. Earlier permission to "build a shop" is not confirmation. Re-render
   and reconfirm if the brief or plan changes.

The target must be a dedicated test project on the approval list. The list is the
acknowledgement: a merchant and project on it (exact IDs, approver, approval reference)
are acknowledged, and preflight refuses any other. Never ask the publisher to confirm a
test project. For a project not on the list, stop with `needs_human` in the blocked
shape: a human maintainer adds it to the list.

Never ask about CLI sandbox mode and never change the CLI config yourself; preflight
does it. Never use sandbox as a Shop Builder target or use a partner project. Never
publish, attach a production domain, enable live payments, or apply a saved version. For
a publish request, use the publish shape under Replies.

A new site has generated blocks whose IDs do not exist before creation. Confirm the
bootstrap, then export, re-render, and reconfirm before removing any generated block
from a page. If the target changes after export, repeat this sequence.

## Build

For a full site from a shop brief, follow [build-flow.md](references/build-flow.md) after
the gate. It covers the preset choice, the inputs to read, the assembly order, and
verification and handoff. Use pre-written scripts for repeated work; never pass `--force`
or invent HTTP or `curl` workarounds. If an operation requires `--force`, stop and report
it. If the CLI lacks an operation, stop, record the gap, and file a CLI/API ticket.

## Block operations (Quests block)

For `block_operations` on an existing site, follow [block-operations.md](references/block-operations.md)
with the same gate. No script deletes a block: deleting needs `--force`, which no script
passes. For a delete request, answer `needs_human` in the delete shape under Replies and
offer `hide`. For any change outside the Quests block in such a request, use the refusal
shape under Replies.

## Stop conditions

Stop before writes when project identity is ambiguous, backup fails, confirmation is
missing, the test project is not on the approved list, catalog or project IDs do not
match, or the plan needs an unverified block module. Keep completed safe work and name the smallest action that
continues.

## Known limitations

- Sites created from a Publisher Account template keep the header in the common layout;
  a build stops on them before any write. Quests block operations are not affected: they
  never touch the header, so they run on template sites too.
  Report the stop and suggest nothing else: not another site, not manual edits, no other
  workaround.

## Replies

Every reply uses one compact shape: a bold one-line answer, then 0 to 4 short bullets
(`- Label: value`), then a last line `Next: <one question or action>`. A simple answer
may be only the bold line and `Next:`. Ask one question at a time.

Never include environment variable names, file paths, tokens, or internal codenames (for
example, D2a) in a reply. Never give the approval list's location or offer to change it.

Plan: a bold `Plan: ...` line, up to about five bullets (Site, Change, fields kept as
they are such as Card image, preflight's `plan_notes` lines, "Not published; you publish
in Publisher Account", and Confirmation). Pack several operations or removals into one
Change bullet, separated by semicolons. The reward text and reward image come from the quest and are never a Change.
When the plan `warnings` say a card text replaces the one set in the editor, add
"(replaces the text set in the Site Builder editor)" to that Change bullet.

```
**Plan: change the title of the "Daily Login" card**
- Site: my-test-site, Quests block on Main
- Change: card title → "Log in every day"
- Card image: unchanged
- Using the CLI test environment (sandbox off)
- Not published; you publish in Publisher Account
- Confirmation: sha256:ab12cd34

Next: reply "yes" to apply this exact plan.
```

One "yes" to that plan applies it. Never show a draft plan first.

Applied, after apply adds or changes the Quests block: give the `editor_url` from the
apply output as the editor link. Never build the link by hand.

```
**Done: the "Daily Login" card title is now "Log in every day".**
- Open the editor: https://publisher.xsolla.com/1/projects/2/site-builder/my-test-site/editor
- The Quests block is already on the page. Preview it there, then publish.

Next: anything else to change on the Quests block?
```

Reward change request: the reward text and image come from the quest, so no plan is made.

```
**The reward comes from the quest, so I can't change it on the Quests block.**
- Change the reward in the quest itself, and the card shows it.

Next: want to change the card title, description or image instead?
```

Blocked, when preflight refuses or a gate stops the write. A project that is not approved
is `needs_human`; never ask the publisher to confirm it instead:

```
**This project isn't approved for test writes yet.**
- Site: my-test-site, nothing changed
- A maintainer needs to add project 2 to the approved test projects

Next: ask your maintainer to approve it, then tell me to retry.
```

Refusal, for anything outside the Quests block in a block-operations request:

```
**That's outside the Quests block.**
- Change the header in the Site Builder editor.

Next: anything to change on the Quests block?
```

Delete request (`needs_human`): the publisher deletes the block in the Site Builder editor;
`hide` is the scripted alternative.

```
**I can't delete the Quests block; you delete it in the Site Builder editor.**
- Instead, I can hide it so it stops showing on the site.

Next: want me to hide it?
```

Publish request: bold "The skill doesn't publish.", bullets "You publish in Publisher Account
when you're ready." and "The site stays unpublished.", then `Next:`.
