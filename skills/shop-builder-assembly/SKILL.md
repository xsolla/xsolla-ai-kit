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

Run these steps in order before any remote write. Writes need a valid shop brief. Until the publisher has said in this conversation that the project is a dedicated test project, skip these steps and reply with the draft plan under Replies.

1. Run `scripts/preflight.py <brief.json>` and pass the approval-list path from
   [shop brief](references/shop-brief.md) as `--approved-test-projects` (expand `~`
   first). Only the scripts read that list: never read, search for, stat, list, create,
   edit, or suggest changing it. Read back the matched merchant ID, project ID,
   environment, approval reference, active Publisher login, target site, and catalog
   groups. When the site needs a common layout (a new site, or one without it) and the
   CLI has no `shopbuilder create-block`, preflight prints "the common layout needs a
   newer Xsolla CLI; the site is built without it". Tell the user in the plan, before
   any write: a site without the common layout won't open in the Editor, Publish or
   private preview. If preflight refuses, reply in the blocked shape.
2. If CLI context differs, switch it and rerun preflight. Never override later commands.
3. If the target site exists, export it before the first write:
   `scripts/backup_shop.py --brief <brief.json> --slug <slug> --output-dir <dir>`.
4. Render with `scripts/render_plan.py <brief.json> --structure <backup-dir>/structure.json`
   and show the plan in the Plan shape. Preserve configured blocks lacking replacement
   data. Omit `--structure` only for a new slug's bootstrap-only plan.
5. Ask for explicit confirmation of the plan's `confirmation_id` immediately before the
   first remote write. Earlier permission to "build a shop" is not confirmation. Re-render
   and reconfirm if the brief or plan changes.

The target must be an acknowledged dedicated test project. It must match the approval
list exactly (IDs, approver, approval reference), or preflight refuses. Set
`project.test_project_acknowledged` to `true` only when the publisher explicitly says in
this conversation that the project is a dedicated test project. Never set it yourself or
infer it from the name, a test site, an earlier yes, or the list.

Never use sandbox as a Shop Builder target or use a partner project. Never publish,
attach a production domain, enable live payments, or apply a saved version. For a
publish request, use the publish shape under Replies.

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
missing, the target is not an acknowledged dedicated test project, the test project is
not on the approved list, catalog or project IDs do not match, or the plan needs an
unverified block module. Keep completed safe work and name the smallest action that
continues.

## Known limitations

- Sites created from a Publisher Account template keep the header in the common layout;
  render and apply stop on them before any write, for a build and for block operations.
  Report the stop and suggest nothing else: not another site, not manual edits, no other
  workaround.

## Replies

Every reply uses one compact shape: a bold one-line answer, then 0 to 4 short bullets
(`- Label: value`), then a last line `Next: <one question or action>`. A simple answer
may be only the bold line and `Next:`. Ask one question at a time.

Never include environment variable names, file paths, tokens, or internal codenames (for
example, D2a) in a reply. Never mention the approval list or its location in a reply.

Plan: a bold `Plan: ...` line, up to about five bullets (Site, Change, fields kept as
they are such as Card image, "Not published; you publish in Publisher Account", and
Confirmation). Pack several operations or removals into one Change bullet, separated by
semicolons. The reward text and reward image come from the quest and are never a Change.

```
**Plan: change the title of the "Daily Login" card**
- Site: my-test-site, Quests block on Main
- Change: card title → "Log in every day"
- Card image: unchanged
- Not published; you publish in Publisher Account
- Confirmation: sha256:ab12cd34

Next: reply "yes" to apply this exact plan.
```

Draft plan, before the publisher confirms the dedicated test project: a bold `Draft plan: ...` line, the change bullets, "Not published; you publish in Publisher Account", no Confirmation line, and `Next: Confirm this is a dedicated test project, and I'll give you the final plan to approve.` as the only ask. The draft is text only, so it needs no preflight, backup or `confirmation_id`. Once the publisher confirms, run the gate and show the final Plan.

```
**Draft plan: change the title of the "Daily Login" card**
- Site: my-test-site, Quests block on Main
- Change: card title → "Log in every day"
- Not published; you publish in Publisher Account

Next: Confirm this is a dedicated test project, and I'll give you the final plan to approve.
```

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

Blocked, when preflight refuses or a gate stops the write (the project is not approved, the
brief is not acknowledged, the target does not match):

```
**This project can't take test writes yet.**
- Site: my-test-site, nothing changed

Next: confirm the project is the dedicated test project you intended.
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
