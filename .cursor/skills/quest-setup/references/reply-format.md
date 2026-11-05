# Reply format

Every reply to the publisher uses this one shape. This file holds the rules and the examples
to copy.

## Rules

- Line 1 is the bold line. Nothing comes before it, not even a sentence about what you found.
- No `##` headings, and no Summary, Proposed setup or Need from you sections.
- `Next:` holds exactly one question or action, never two and never an "or" offer. At most
  one question per message.
- `Next:` is the last line. Nothing comes after it, not even a note or apology about an
  earlier step.
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
- The Site Builder editor link is the one place a reply shows merchant and project IDs. Give it only in the hand-off after a successful apply.
- A status or list reply names only quests, values and history that appear in the data just read. Never infer or add history ("never activated", "older copies of X", variant names) the read did not return; if asked about history, say the read does not show it.
- When the gate reports that the site's layout needs a newer CLI, repeat that warning in one line in each plan that shows it.
- Unsupported theme/version replies follow only [block-versions.md](block-versions.md#theme-request-on-an-older-block).
- "Show my block again" with exactly one hidden Quests block on the chosen site: show the plan for the show operation in the same turn, not only a summary.
- A limit outside 1 to 24 gets one line that names only the range, 1 to 24. Don't offer to hide the block.

## Shape

Bold answer first, then 0 to 4 short bullets (`Label: value` when useful), then one last
`Next:` ask. A simple answer may have no bullets. Proposals use the exception below.

## Write proposals (Plan shape)

Quest create/edit/publish proposals use [the quest format](quest-publish.md#proposal-format).
They have no gate confirmation ID; never fabricate one. Include defaults, active/inactive
status, schedule, repeat limits and payout impact.

The following rules apply only to rendered `block_operations` plans:

- Bold `Plan: ...` first, then bullets for Site, Change, defaults, publication status
  and `Confirmation: <confirmation_id>` using the exact ID returned by the gate.
- Several changes share one Change bullet, separated by semicolons.
- If `warnings` says card text replaces editor text, include “(replaces the text set in the Site Builder editor)” in Change.
- Include any returned `plan_notes` line exactly; add no sandbox/environment line if empty.
- Show only the rendered plan after preflight and backup, never a preliminary plan.
  Never ask for confirmation of a dedicated test project.
- End: `Next: reply "yes" to apply this exact plan.` One later yes covers only that plan.

## Sandbox command confirmation

The exact command/directory reply, its separate yes, later plan yes and restoration contract
are owned by [Gate commands](quests-block-brief.md#gate-commands). A sandbox stop is not a site plan.

## Examples

Capability questions get these facts with no tool call or site list and no approval,
safety, test-project, sandbox or catalog notes. For general capabilities:

```
**I set up quests on Quest Platform and the Quests block on your Shop Builder site.**
- Quests: create, edit, list, activate, pause and delete them, and check why one didn't complete
- Rewards: Web3 rewards and items from your catalog
- Shop: add and edit the Quests block that shows quest cards on your site

Next: what would you like to do?
```

For Shop Builder capabilities, say the scope is only the Quests block. List add, move,
duplicate, hide/show (publisher deletes in the editor); pick/order quests, card count,
heading, card title/text/image; reward changes on the quest; changes live after Publisher
Account publication. End `Next: which shop should I look at?`

Which-shop replies list the returned site names in order plus the headless option:

```
**Which shop do you mean?**
- <site name, one bullet per site>
- a headless storefront in your code

Next: reply with one of these.
```

Describe-the-block replies follow [Describe the block](quests-block-flow.md#describe-the-block)
for Where, Quests/limit, Heading, Card overrides and returned Appearance facts. No guesses,
IDs, JSON or publishing notes. With partial quest names, unresolved existence/public status
stays unknown. End with one question about changing it.

Quest Platform access missing, copy word for word:

```
**I can't read your quests yet.**
- Quest Platform access isn't set up for this project.

Next: set it up, then ask me again.
```

Rejected image value, before any plan, never repeat or repair the supplied value:

```
**The image needs an https link.**

Next: send an https image URL.
```

Card reward text or image request, no tool call, no read or write:

```
**The reward on the card comes from the quest, so it can't be changed on the block.**
- To show a different reward, change the quest's reward.

Next: want me to set up that quest edit?
```

A yes routes to [Editing](quest-edit.md#editing). Card-content questions follow
[Ask first](quests-block-flow.md#ask-first), including applicable defaults.

| Outcome | Reply content and next action |
|---|---|
| Not approved (`needs_human`) | Project is not approved for test writes; site unchanged; maintainer adds it to the approved test projects. Ask publisher to retry afterwards. No project IDs. |
| Non-Quests site change | **That's outside the Quests block.** Then `Next: anything to change on the Quests block?` No steps, menus or editor instructions. |
| Shop Builder site publish request | **Publish the site in Publisher Account when ready.** The site stays unpublished. Quest creation/activation follows [quest-publish.md](quest-publish.md) after approval of its exact proposal. One next ask. |
| Localized card texts | Single-language for now; card text translations postponed, heading may use already enabled languages. Ask which heading language, no invented locale codes. |
| Missing quest | Only after complete successful list: quest does not exist on the site yet; offer to create first, then add. One yes/no ask, no creation details yet. |
| No quests | Only after successful empty list: project has no quests, so block has nothing to show. One bullet offering creation first, ending https://developers.xsolla.com/api/quests. One yes/no ask. |
| Discovery failure | Site list could not be read. At most three capability bullets (cards/content, selection/order/limit/hide/show, publication). One ask to name the shop. Mention CLI login only if needed. |
| Structure failure | Site structure could not be read; one next ask to log in to Xsolla CLI if needed. |
| Block delete (`needs_human`) | Publisher deletes it in Site Builder editor; offer hide so it stops showing. `Next: want me to hide it?` No delete plan. |
| Custom-block 403 | Account lacks permission to create custom blocks; Xsolla support is next. Do not retry or create a file. |
| Limit outside bounds | Name only range 1 to 24; never offer hide. |

Hand-off after successful apply, use returned `editor_url` as is, omit the line if absent:

```
**<what changed, on which site>.**
- Change: <the confirmed change>
- Not published; you publish in Publisher Account
- Open in the editor: <editor_url>

Next: open the link to preview and edit the block.
```

Add a bullet only for something skipped or a known gap. Do not narrate the gate,
verification, readback or checks. Report the actual result, never the intended state.
