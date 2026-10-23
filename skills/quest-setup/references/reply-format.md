# Reply format

Every reply to the publisher uses this one shape. SKILL.md "Reply style" has the rules;
this file has the shape and the examples to copy.

## Shape

- Line 1: a bold one-line answer, `**...**`.
- Then 0 to 4 short bullets. Use `Label: value` where a label helps.
- Last line: `Next: <one question or action>`. Exactly one ask, never two, and no
  "or" offer. A reply that wants two answers asks the first and waits.
- A simple answer may be only the bold line and `Next:`.

## Write proposals (Plan shape)

- Line 1: a bold `Plan: ...` line.
- Then up to about five bullets, for example Site, Change, defaults such as Reward icon,
  "Not published; you publish in Publisher Account", and Confirmation.
- Last line: `Next: reply "yes" to apply this exact plan.`

For a quest create or edit, the bullets are the labelled lines in
[quest-document.md](quest-document.md#proposal-format).

## Examples

Which shop:

```
**Which shop do you mean?**
- qa-quests-spike
- xsolla-test-3-1b2b
- qp-spike-site
- a headless storefront in your code

Next: reply with one of these.
```

Describe the block:

```
**qa-quests-spike has a Quests block.**
- Where: Main page, last block, visible
- Quests: 6 selected, limit 6
- Heading: "Quests"
- Card overrides: none

Next: want to change anything on it?
```

Plan:

```
**Plan: set reward text on the "QA Quest Badge" card**
- Site: qa-quests-spike, Quests block on Main
- Change: reward text → "Gold badge"
- Reward icon: catalog image (unchanged)
- Not published; you publish in Publisher Account
- Confirmation: sha256:ab12cd34

Next: reply "yes" to apply this exact plan.
```

Refusal, outside the Quests block:

```
**That's outside the Quests block.**
- Change the header in the Shop Builder editor.

Next: anything to change on the Quests block?
```

Quest Platform access missing:

```
**I can't read your quests yet.**
- Quest Platform access isn't set up for this project.

Next: set it up, then ask me again.
```

Rejected value (say what is required, never repeat the value). An `http` image or reward icon URL gets this reply before any plan. Never change it to https or draft a plan with it:

```
**The image needs an https link.**

Next: send an https image URL.
```

Publish request:

```
**The skill doesn't publish.**
- You publish in Publisher Account when you're ready.
- The site stays unpublished.

Next: anything else to set up?
```

Localized card texts:

```
**Card texts are single-language for now.**
- Card text translations are postponed; the heading can use languages already enabled on the site.

Next: which language should the heading use?
```

Missing quest (offer the create flow; no creation details until a yes):

```
**Summit Run Challenge doesn't exist on qa-quests-spike yet.**
- It can be created first, then added to the block.

Next: want me to draft it?
```

Card defaults (never say an explanation is required; state the defaults, ask one optional question):

```
**Daily Login will use its quest name and description on the card.**
- Card title: Daily Login (the quest name)
- Explanation: the quest description
- Image: the quest image, if it has one. The reward icon is separate.

Next: want a different title or image on the card?
```

Discovery read failed (still answer the capability question, then one ask):

```
**I couldn't read your Shop Builder sites just now.**
- The Quests block can show quest cards with a title, text, image and optional reward line.
- You can choose and order the quests, set the limit, and hide, show or remove the block.
- Changes stay a draft until you publish them in Publisher Account.

Next: which shop should I look at: a Shop Builder site by name, or a headless storefront?
```

Delete stop (before any removal yes):

```
**Nothing is removed yet; removal needs its own yes.**
- Block: Quests block on the Main page, position 12
- Removing it deletes only this block; the rest of the site stays.

Next: reply "yes" if you want to remove this block.
```
