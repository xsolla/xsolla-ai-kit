# Quest edit, pause and delete

Loaded only for an edit, pause or delete request. Every write here needs its own yes to the
exact body or the exact quest. Operations, bodies and answers come from the live contract
([live-docs.md](live-docs.md)).

## Editing

Read what the docs say about updating a quest before editing (the Quest guide, editing a live
quest). This skill always sends the whole document: take the body of a fresh read, change only the
fields the publisher asked for, and send the rest back as read. Tell the publisher that the change
replaces the stored quest. Drop fields the docs mark read-only (such as a `$schema` link) and keep
fields the server assigns as read; the path id wins. A new node gets a fresh random UUID (v4) that
you generate; existing node ids stay unchanged. Show the before/after diff of the changed fields
before sending.

Keep `public_view` the same way: resend the fresh read's `public_view` unchanged unless the edit
changes it. If the edit adds, replaces or removes a reward node, update the reward references in
`public_view` in the same diff, because a reference to a missing node is left out of the card.

Use [SKILL body-file rules](../SKILL.md#access-and-authority), with no loop retry.
For reward additions versus replacements, follow [Adding a reward](rewards.md#adding-a-reward).
Apply the docs' date rules for an active quest before the proposal; if the old end date has
passed, propose a new end in the same before/after diff and ask for approval of the revised edit,
not for a date.

**Locked once players start.** The docs refuse a structural change (the parts they list, such as
nodes, connections, limits or the start date) on a quest that players already have progress on,
with a 409. Before proposing such a change, say it may be refused for that reason. If the update
answers 409, nothing was saved: say the quest's steps and rewards are locked because players have
started it, that texts, the end date and pausing still work, and offer a new quest for the rest.
Never retry it and never try to work around the lock.

An edit to an active quest applies to the next events after the propagation delay the docs
describe. Repeat the activation confirmations for the changed part when the edit touches any of:
an action's subtype or parameters, connections that change which actions run, a reward, the
activation limits, the dates, or `status`. An edit to `name` or `description` only needs no
repeat. If the edit changes an amount or SKU, check node names that mention the old value.
Whenever a reward changes, also check whether the quest name still describes it. If the name
mentions the old reward (for example, Fire Sword changed to Ice Sword), update the quest name in
the same proposed edit and include it in the before/after diff. Ask only if the intended new name
is unclear. The reward-change confirmation covers the combined reward and name edit.

Read immediately before the update: the last write wins for changes the docs do not lock.

## Pausing

To pause, send the full-document update from the recipe with the inactive status the docs
describe, and keep the dates, nodes and limits as they are. Say what the docs say about
reactivating later (dates are checked again, and after progress a start date in the past may
block it).

While the quest is inactive, events do not run it and are not replayed on reactivation. During
the propagation delay, an event may still see the previous configuration; warn before sending an
event for a quest with an external reward.

## Deleting

Deleting is the contract's delete operation. Read its docs first: a deleted quest cannot be
restored, and a deleted quest reads as not found afterwards. A not-found answer about the project
instead is a scope answer, not a verdict on the quest; see the auth reference. Never use an update
as a restore, and never update a deleted id.

Recipe:

- Delete only quests the publisher names by id or exact name. Never select
  them by pattern or "all test quests" without showing the list first.
- Re-list or read right before deleting, and show each quest's name, id,
  status, dates and actions. For an active quest or one with a reward or another
  external action, say it is live and what stops.
- Say that the delete cannot be undone, and get a yes.
- Delete one quest per call. Stop on the first failure and report it; after a
  timeout or 5xx, read the quest to check before trying again.
- Re-list afterwards and show that the deleted quests are gone.
