# Quest publication

Loaded for a create proposal, the publication sequence after approval, ambiguous writes, and
the proposal conversation. Operations and bodies come from the live contract
([live-docs.md](live-docs.md)).

## Publication after approval

Resolve scope, reward, graph, schedule and limits using [Conversation contract](#conversation-contract)
before showing the [proposal](#proposal-format). Inactive creation is an internal step,
not a separate user-facing workflow; inactive quests are excluded from the active public list.

One approval of the exact publisher proposal authorizes this ordered sequence:

Use [SKILL body-file rules](../SKILL.md#access-and-authority); never loop-retry writes.

1. Create a complete inactive quest with the full graph and reward from the
   approved proposal.
2. Read the created quest by id and confirm scope, graph, and reward.
3. Activate with the [Editing](quest-edit.md#editing) recipe (fresh read, full
   update): set the active status, apply the approved dates and activation limits.
   Everything else goes back as read. Do not ask a second approval for this
   activation update.
4. Read again and report active status, scope, reward, dates and limits. Do not
   claim publication complete until this read-back matches the approved proposal.

[Activation limits](quest-authoring.md#activation-limits) owns how an absent limit is shown.

A relative duration ("run it for 7 days") counts from the `start_date`
actually sent: `end_date` is that start plus 7x24 hours. If the start moves
(for example a requested time has passed), recompute the end under the approved
duration. Show a revised proposal for approval only when this changes a fixed
schedule that the publisher explicitly requested.

"Start now" is stamped when the activation update is built. Show the rule
("start at activation in UTC, end N days later") in the proposal. The one approval
covers both timestamps, even when activation happens later than the proposal was
shown. Report the actual UTC timestamps from the publication read-back.

## Ambiguous or partial writes

A create that succeeded created exactly one quest. Take the quest `id` from
that response. If it was not captured, find the quest by name in the list as
below; never send a second create for the same proposal.

After a timeout or 5xx on a quest create or update, the write may have landed.
Reconcile with a bounded read-back before any retry:

- For an update, read the quest by id and compare to the intended document.
- For a create, page the project list (the largest page size the docs allow, from
  the first page until every quest is read) for the quest's `name`. Continue or
  repair the same quest when safe; never create a duplicate on timeout.
- Show what you found. Ask before any resend that would create a second quest.
- A 422 saved nothing: validation runs before anything is stored.

Tell the publisher that publication did not finish, whether the quest is
visible, and the concrete next step. Never report publication complete until
the active quest and approved configuration read back.

## Conversation contract

- Do the read-only checks first and silently: project read, reward resolution, the
  player action, the graph, schedule and limits. Do not ask for approval before they
  finish.
- Show one proposal in the format below, in business terms. Omit service names,
  routes, auth, implementation fields (including `type`) and narration. Ask only for
  approval of this proposal.
- Propose the [defaults](quest-authoring.md#defaults-this-skill-chooses) instead of
  asking for implementation fields. For an item reward: quantity one, one payout per
  player. Do not ask for missing dates.
- Resolve the actual event binding through [Triggers](quest-authoring.md#triggers),
  including its unverified-candidate and login rules. An action-derived candidate is
  never evidence that the site emits it.
- Say which parts [lock once players start](quest-authoring.md#what-locks-once-players-start).
- Resolve named items through [rewards](rewards.md#named-item-behavior), with no write
  after zero/unavailable lookup and a publisher choice for multiple candidates.
- One approval of the exact proposal covers create, configure, activate and read-back.
  The approval request names only publication. Never offer or bundle a test event in
  it; offer the event after publication, with its payload. A material change after
  approval needs a revised proposal and a new approval.
- A Web Shop quest section is optional and only on explicit request, per
  [`web-shop-module.md`](web-shop-module.md). Quest approval never authorizes shop
  source edits.

### Proposal format

Use the common bold/bullets/last-Next shape from [reply-format.md](reply-format.md#write-proposals-plan-shape)
with the quest fields below. Quest API proposals have no gate confirmation ID; never
fabricate one. Bold line first, then these bullets, in business terms:

```
**Plan: create the "<quest name>" quest in <project name>**
- What the player does:
- Reward: <item name>, quantity 1
- Schedule (UTC): <start> to <end>
- Status after your yes: ACTIVE (live) from <start> to <end>
- Repeat limit:
- Payout impact:

Next: reply "yes" to apply this exact plan.
```

The `Status after your yes` bullet is always present: the one approval covers create, activate
and read-back, so the plan says plainly that the quest goes live. If the publisher wants it left
inactive, the bullet says `Status after your yes: INACTIVE (not live)` and the activation step is
skipped. Label publisher-unsupplied schedule/default values "my default, change it if you like".
Event names follow [Triggers](quest-authoring.md#triggers): a proposed,
unverified candidate is never a configured default. Labels may sit next to values but
never replace the required status bullet.

If the publisher asks for a change instead, show the revised plan in the same shape.

## Safety stops for proposals and actions

- Multiple catalog matches or materially different reward effects need a choice before
  the exact proposal. Follow [defaults](#conversation-contract) and [proposal format](#proposal-format).
- No action is side-effect free by default. For a smoke test, offer a labelled
  no-op rather than a real reward ([Actions with an external effect](quest-authoring.md#actions-with-an-external-effect)).
  For publication or a smoke test, say events are not verified until the
  [event gate](events.md#event-gate) passes.
- When an external action is part of the proposal, say what it will do once
  active. The publication approval covers that impact for the approved quest:
  a reward pays out, a webhook sends event data to an external URL, a
  notification or email reaches players.
- Never point a webhook at a private service or an endpoint the publisher has not
  named: a webhook cannot pay out. To pay out a named item, use a reward node
  with the verified catalog SKU ([rewards.md](rewards.md)).
- Named items default to explicit `per_user` count 1, described as one requested item
  per player. Ask about repeat behavior only when repeatable/unlimited or ambiguous;
  [activation limits](quest-authoring.md#activation-limits) owns other unlimited cases.
  Never ask Backpack versus regular/Web3 delivery.
