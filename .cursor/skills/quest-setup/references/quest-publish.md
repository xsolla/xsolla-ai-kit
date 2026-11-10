# Quest publication

Loaded for a create proposal, the publication sequence after approval, ambiguous writes, and
the proposal conversation. The route contract is in [qp-api-contract.md](qp-api-contract.md).

## Publication after approval

Resolve scope, reward, graph, schedule and limits using [Conversation contract](#conversation-contract)
before showing the [proposal](#proposal-format). Inactive creation is an internal step,
not a separate user-facing workflow; inactive quests are excluded from the active public list.

One approval of the exact publisher proposal authorizes this ordered sequence:

Use [SKILL body-file rules](../SKILL.md#access-and-authority); never loop-retry writes.

1. `POST` a complete inactive quest with the full graph and reward from the
   approved proposal (required fields plus nodes and connections).
2. `GET` the created quest by id and confirm scope, graph, and reward.
3. Activate with the Editing recipe below (fresh `GET`, full `PUT`): set
   `status` to `active`, apply the approved `start_date`, `end_date`, and
   `activation_limits`. Everything else goes back verbatim, the server-set fields
   included (`id`, `created_at`, `updated_at`, `version_id`, `has_personalization`): the
   server ignores them on `PUT`, so sending them as read is safe. Do not ask a second
   approval for this activation `PUT`.
4. `GET` again and report active status, reward, dates and limits in plain words. Do not claim publication complete until this read-back matches
   the approved proposal.

[Activation limits](quest-authoring.md#activation-limits) owns absent/null/empty limits
and unlimited-repeat semantics; follow live docs if those forms differ.

A relative duration ("run it for 7 days") counts from the `start_date`
actually sent: `end_date` is that start plus 7x24 hours. If the start moves
(for example a requested time has passed), recompute the end under the approved
duration. Show a revised proposal for approval only when this changes a fixed
schedule that the publisher explicitly requested.

"Start now" is stamped when the activation `PUT` is built. Show the rule
("start at activation in UTC, end N days later") in the proposal. The one approval
covers both timestamps, even when activation happens later than the proposal was
shown. Report the actual UTC timestamps from the publication read-back.

## Ambiguous or partial writes

A `POST` that returned 200 created exactly one quest. Take the quest `id` from
that response. If it was not captured, find the quest by name in the list as
below; never send a second `POST` for the same proposal.

After a timeout or 5xx on a quest `POST` or `PUT`, the write may have landed.
Reconcile with bounded read-back from the route contract before any retry:

- For a `PUT`, `GET` the quest by id and compare to the intended document.
- For a `POST`, page the project list (`limit=100` from `page=1` until
  `page*limit >= total`) for the quest's `name`. Continue or repair the same
  quest when safe; never create a duplicate on timeout.
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
  routes, auth, implementation fields (including `type`) and narration. The same holds
  for every quest reply: status, debug, edit and delete use
  [plain-word labels](reply-format.md#plain-word-labels) too. Ask only for
  approval of this proposal.
- Never ask for implementation fields: a gameplay quest uses `liveops` internally but is
  described as a gameplay quest; `purpose` is `quest_completion`; `created_by` is the
  developer's name, otherwise `AI Toolkit`. What the publisher decides (the reward,
  trigger and conditions, activation limits, start and end dates, quantity or amount) comes
  from their request or from the [one-question menu](rewards.md#choose-from-the-node-catalog)
  with a suggestion that matches the request; never filled in silently. A relative duration
  the publisher gave counts from the start, as below.
- Resolve the actual event binding through [Choosing a trigger](node-subtypes.md#choosing-a-trigger),
  including its unverified-candidate and login rules. An action-derived candidate is
  never evidence that the site emits it.
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
- Project: merchant <merchant_id>, project <project_id>
- Name and card text: <quest name>; <one-line description> (proposed when the publisher gave none)
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
skipped. Schedule, limits and quantities are never unsupplied: the publisher gave them or picked them from
the [menu](rewards.md#choose-from-the-node-catalog) before this proposal.
Event names follow [Choosing a trigger](node-subtypes.md#choosing-a-trigger): a proposed,
unverified candidate is never a configured default. Labels may sit next to values but
never replace the required status bullet.

If the publisher asks for a change instead, show the revised plan in the same shape.

## Safety stops for proposals and actions

- Multiple catalog matches or materially different reward effects need a choice before
  the exact proposal. Follow [defaults](#conversation-contract) and [proposal format](#proposal-format).
- No action is side-effect free by default. For a smoke test, offer the no-op
  in [`node-subtypes.md`](node-subtypes.md) rather than a
  real reward (placeholders `e2e-noop`, `e2e-sink.invalid`). Don't claim events
  work until the [production event gate](events.md#production-event-gate) passes; never
  explain the gate to the publisher.
- When an external action is part of the proposal, say what it will do once
  active. The publication approval covers that impact for the approved quest.
  Any reward node can create real payouts; `send_http_webhook` sends event
  data to an external URL; `send_xsolla_app_notification` sends a user
  notification. Activate a `webshop_personalization` node only after the
  developer acknowledges that it is a no-op. For an active quest whose only
  action it is, say before any edit or event that it does nothing and a
  `COMPLETED` row proves only that the quest ran; a `PUT` that keeps it active
  needs that acknowledgement, a pause does not.
- Never point `send_http_webhook` at a private service or an
  [unapproved host](node-subtypes.md#send_http_webhook): a webhook
  cannot mint. To pay out, use a reward node from the node catalog
  with verified parameters (for an item, the verified candidate's catalog project and SKU).
- Repeat behavior is the publisher's choice ([limits and schedule](rewards.md#choose-from-the-node-catalog)):
  show the chosen activation limits in the proposal; [activation limits](quest-authoring.md#activation-limits)
  owns the unlimited cases.
