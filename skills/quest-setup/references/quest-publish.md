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
   `activation_limits`. Everything else goes back verbatim. Do not ask a second
   approval for this activation `PUT`.
4. `GET` again and report active status, scope, reward, dates, limits, and
   `version_id`. Do not claim publication complete until this read-back matches
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
  routes, auth, implementation fields (including `type`) and narration. Ask only for
  approval of this proposal.
- Propose defaults instead of asking for implementation fields. A gameplay quest uses
  `liveops` internally but is described as a gameplay quest. For an item reward:
  quantity one, purpose `quest_completion`, one payout per player. `created_by` is
  the developer's name, otherwise `AI Toolkit`. Start is the publisher's start or
  activation time; end is the publisher's end, else the requested duration after the
  start, else 7 days after the start. Do not ask for missing dates.
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
Event names follow [Choosing a trigger](node-subtypes.md#choosing-a-trigger): a proposed,
unverified candidate is never a configured default. Labels may sit next to values but
never replace the required status bullet.

If the publisher asks for a change instead, show the revised plan in the same shape.

## Safety stops for proposals and actions

- Multiple catalog matches or materially different reward effects need a choice before
  the exact proposal. Follow [defaults](#conversation-contract) and [proposal format](#proposal-format).
- No action is side-effect free by default. For a smoke test, offer the no-op
  in [`node-subtypes.md`](node-subtypes.md) rather than a
  real reward (placeholders `e2e-noop`, `e2e-sink.invalid`). For publication
  or a smoke test, say production events are not verified until the events
  preflight passes ([production event gate](events.md#production-event-gate)).
- When an external action is part of the proposal, say what it will do once
  active. The publication approval covers that impact for the approved quest.
  An `issue_reward` can create real payouts; `send_http_webhook` sends event
  data to an external URL; `send_xsolla_app_notification` sends a user
  notification. Activate a `webshop_personalization` node only after the
  developer acknowledges that it is a no-op. For an active quest whose only
  action it is, say before any edit or event that it does nothing and a
  `COMPLETED` row proves only that the quest ran; a `PUT` that keeps it active
  needs that acknowledgement, a pause does not.
- Never point `send_http_webhook` at a private service or an
  [unapproved host](node-subtypes.md#send_http_webhook): a webhook
  cannot mint. To pay out a named item, use an `issue_reward` Web3 reward with
  the verified candidate's catalog project and SKU.
- Named items default to explicit `per_user` count 1, described as one requested item
  per player. Ask about repeat behavior only when repeatable/unlimited or ambiguous;
  [activation limits](quest-authoring.md#activation-limits) owns other unlimited cases.
  Never ask Backpack versus regular/Web3 delivery.
