# Reply format

Every reply to the publisher uses this one shape. SKILL.md "Reply style" has the rules;
this file has the shape and the examples to copy.

## Shape

- Line 1: a bold one-line answer, `**...**`.
- Then 0 to 4 short bullets. Use `Label: value` where a label helps.
- Last line: `Next: <one question or action>`.
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

Rejected value (say what is required, never repeat the value):

```
**The reward icon needs an https link.**

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
- Localization is postponed.
- The heading can use only languages already enabled on the site.

Next: which language should the heading use?
```
