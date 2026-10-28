# Reply format

Every reply to the publisher uses this one shape. This file holds the rules and the examples
to copy.

## Rules

- Line 1 is the bold line. Nothing comes before it, not even a sentence about what you found.
- No `##` headings, and no Summary, Proposed setup or Need from you sections.
- `Next:` holds exactly one question or action, never two and never an "or" offer. At most
  one question per message.
- Which-shop replies list the site names as bullets, then the question. No capability or
  explanation sentence comes before the question.
- No unrequested safety, environment, backup or out-of-scope lectures, and no narration of
  internal steps.
- Never say you are waiting for an approval or confirmation, never say "allow", "grant
  access" or "once you allow them", never ask the publisher to allow CLI commands or change
  permissions, and never name another skill or the safety gate. Say "set up Quest Platform
  access" instead.
- Rejected values: never repeat the value; use the rejected-value shape.
- When asked about the publisher's project, ignore working-folder files that are not the
  project (logs, `*.jsonl`, scratch files). Never report them as content.
- A decline is one bold sentence, at most one bullet, then `Next:`. Non-Quests changes on a
  Shop Builder site use the refusal shape. Never give steps, menu names or click-paths for
  a decline, even when asked how. Never suggest a translated heading or name locale codes
  the publisher did not give.
- A "why" follow-up or a refusal is at most two sentences, with no list and under about 40 words. Don't guess a cause you can't verify; say what you would need to check.
- Never propose a reward item or SKU the publisher did not give, or one a lookup did not verify.
- The reward text and image on a Quests block card come from the quest and can't be changed on the block. To change them, offer to change the quest's reward.
- The Site Builder editor link is the one place a reply shows merchant and project IDs. Give it only in the hand-off after a successful apply.
- Access missing: use the access-missing example below word for word. Don't explain credentials, and don't offer another way to get access.
- A limit outside 1 to 24 gets one line that names only the range, 1 to 24. Don't offer to hide the block.

## Shape

- Line 1: a bold one-line answer, `**...**`.
- Then 0 to 4 short bullets. Use `Label: value` where a label helps.
- Last line: `Next: <one question or action>`. Exactly one ask, never two, and no
  "or" offer. A reply that wants two answers asks the first and waits.
- A simple answer may be only the bold line and `Next:`.

## Write proposals (Plan shape)

- Line 1: a bold `Plan: ...` line.
- Then up to about five bullets, for example Site, Change, defaults such as Card image,
  "Not published; you publish in Publisher Account", and Confirmation.
- Last line: `Next: reply "yes" to apply this exact plan.`

### Draft plan before confirmation

Until the publisher has said in this conversation that the project is a dedicated test project, use the draft form instead: a bold `Draft plan: ...` line, the change bullets, "Not published; you publish in Publisher Account", no Confirmation line, and `Next: Confirm this is a dedicated test project, and I'll give you the final plan to approve.` as the only ask. Do not run preflight, backup or render first.

For a quest create or edit, the bullets are the labelled lines in
[quest-publish.md](quest-publish.md#proposal-format).

## Examples

Which shop:

```
**Which shop do you mean?**
- my-test-site
- summer-event-shop
- my-second-site
- a headless storefront in your code

Next: reply with one of these.
```

Describe the block:

```
**my-test-site has a Quests block.**
- Where: Main page, last block, visible
- Quests: 6 selected, limit 6
- Heading: "Quests"
- Card overrides: none

Next: want to change anything on it?
```

Plan:

```
**Plan: change the title on the "QA Quest Badge" card**
- Site: my-test-site, Quests block on Main
- Change: card title → "Daily challenge"
- Card image: quest image (unchanged)
- Not published; you publish in Publisher Account
- Confirmation: sha256:ab12cd34

Next: reply "yes" to apply this exact plan.
```

Draft plan before confirmation:

```
**Draft plan: change the title on card 2 of the Quests block**
- Site: my-test-site, Quests block on Main
- Change: card title → "Daily challenge"
- Not published; you publish in Publisher Account

Next: Confirm this is a dedicated test project, and I'll give you the final plan to approve.
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

Rejected value (say what is required, never repeat the value). An `http` image URL gets this reply before any plan. Never change it to https or draft a plan with it:

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
**Summit Run Challenge doesn't exist on my-test-site yet.**
- It can be created first, then added to the block.

Next: want me to draft it?
```

No quests in the project (only after a successful list read; offer the create flow first):

```
**This project has no quests yet, so the Quests block has nothing to show.**
- Create a quest first, then I'll add the block. How quests work: https://developers.xsolla.com/api/quests

Next: want me to draft your first quest?
```

Reward change request, for the reward text or the reward image (read-only on the block):

```
**The reward on the card comes from the quest, so it can't be changed on the block.**
- To show a different reward, change the quest's reward.

Next: want me to draft that quest edit?
```

Hand-off after apply (end with the Site Builder editor link):

```
**The Quests block is on my-test-site.**
- Change: added to Main, 4 quests, heading "Quests"
- Not published; you publish in Publisher Account
- Open in the editor: https://publisher.xsolla.com/1/projects/2/site-builder/my-test-site/editor

Next: open the link to preview and edit the block.
```

Card defaults (never say an explanation is required; state the defaults, ask one optional question):

```
**Daily Login will use its quest name and description on the card.**
- Card title: Daily Login (the quest name)
- Explanation: the quest description
- Image: the quest image, if it has one
- Reward: from the quest, not editable on the block

Next: want a different title or image on the card?
```

Discovery read failed (still answer the capability question, then one ask):

```
**I couldn't read your Shop Builder sites just now.**
- The Quests block can show quest cards with a title, text, image and the quest's reward.
- You can choose and order the quests, set the limit, and hide or show the block.
- Changes stay a draft until you publish them in Publisher Account.

Next: which shop should I look at: a Shop Builder site by name, or a headless storefront?
```

Delete request (`needs_human`): the publisher deletes the block in the Site Builder editor;
`hide` is the scripted alternative.

```
**I can't delete the Quests block; you delete it in the Site Builder editor.**
- Instead, I can hide it so it stops showing on the site.

Next: want me to hide it?
```
