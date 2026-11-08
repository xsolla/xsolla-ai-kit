# Quest authoring

The quest is a graph of nodes. Every field, node, parameter, connection rule, limit and date rule
comes from the live docs and the node catalog ([live-docs.md](live-docs.md)): the Quest guide,
Quest nodes, Connections, Activation limits and the Examples page. This file holds only how this
skill turns a publisher's request into that document. Publication, edits and proposals have their
own files.

## Defaults this skill chooses

Propose these instead of asking, and label them "my default, change it if you like":

- **Kind of quest.** Use the quest type the docs describe for an in-game (LiveOps) quest unless the
  publisher indicates another context. Keep the type out of the publisher-facing preview and call
  it a gameplay quest. A loose match such as "for the Xsolla app" is only a suggestion: ask a
  confirming question before it goes into a body.
- **Author.** The publisher's name when they gave it, otherwise `AI Toolkit`, without asking.
- **Dates.** Start at the publisher's start, else at activation time. End at the publisher's end,
  else the requested duration after the start, else 7 days after the start. Never ask for a
  missing date.
- **Repeat limit.** A named item reward is once per player; anything else follows the request.
  Never silently assume one.
- **Server-set fields.** Never send or ask for a field the docs say the server sets from the path
  or assigns itself.

## Dates

The docs' date rules decide what the server accepts. When you refuse a start before sending,
explain the rule in your own words, say nothing was sent, and offer the earliest allowed start. To
start now, take the current instant at send time, not one computed earlier in the conversation.

Dates may come back in a different offset from the one sent. State exact times in UTC whenever you
show them, convert read-back dates to UTC and compare instants, never strings. A quest runs only
while active and inside its dates; warn before sending an event outside the window.

## Triggers

A trigger listens for an event by name. Use the actual event name the publisher's game, backend or
site sends:

- Reuse a verified binding or a publisher-supplied actual name. Never infer a deployed binding
  from a quest title or player-action description.
- If unresolved, ask for the actual name. You may propose a `snake_case` candidate labelled
  "proposed, unverified", but before any quest write require a verified binding or the
  publisher's explicit confirmation of what the caller emits. General publication approval
  does not establish configured site emission.
- If the event name looks unrelated to the quest, say so once and ask the publisher to confirm.
  Do not change it yourself.
- Every active quest in the project with the same trigger name may run, so a test quest needs a
  unique name. Two optional read-only checks help: page through the quest list before a create
  for exact or near-duplicate names, and check active quests for the same trigger name when the
  event is generic. A clean project-level result is not proof that no other scope collides.
- An event a browser or game client sends with the player's token (including the events the
  Quests block sends, see [events.md](events.md#client-events)) needs the client-send setting the
  Quest nodes guide documents on the trigger. Say in the proposal which client sends it. Never
  set it on an event only the backend sends.
- For a time-based start, use the scheduled trigger the node catalog lists, per its docs.

## Conditions

Conditions are nodes too: take their parameter schema from the node catalog and their behaviour
from the Quest nodes guide. Two points to state to the publisher in plain words when they apply:

- The docs say what a condition can read (player attributes, event counts) and what it cannot. For
  a vague "check the event", ask what should be checked and offer what the docs support.
- An event count includes the event that is arriving, and counts in calendar windows as the docs
  describe. A "did it at least once" check on the same event as the trigger gates nothing.

## Actions with an external effect

No action is side-effect free by default. Ask for every value that has an effect outside the quest
and never invent one: notification topic and text, webhook URL, email content, CRM segment.

- **Rewards** follow [rewards.md](rewards.md).
- **Webhooks.** Only an endpoint the publisher owns or controls and names explicitly. A public
  request bin also receives the event: use one only after the publisher acknowledges that in the
  proposal. Never point one at a private platform service, never put credentials in it, and never
  use a webhook to pay out. State the destination and that it fires once the quest is active, and
  tell the publisher to deduplicate by the event's idempotency key, since the docs say it can be
  retried.
- **Notifications and emails.** Use only publisher-supplied texts, topics and segments. A
  completed action means the platform sent it, not that the player saw it.
- **A no-op for a smoke test** is a node whose name says it does nothing; never present it as a
  working effect.

State in the proposal what each external action will do once the quest is active. The publication
approval covers that impact for the approved quest.

## Shape of the graph

Build the graph from the Connections guide and the closest example. Before the proposal and
before the first write, check that the intended trigger reaches the intended action and that no
node is orphaned: the server checks references and cycles, which does not prove the quest is
usable.

- **Several actions on one trigger.** The docs say in which order actions run and that the first
  failure stops the run with no rollback of what already ran. Put the most important reward first
  and say that a later failure cannot undo an earlier payout.
- **Several steps.** For "do A, B and C, then get a reward", follow the docs' guidance for
  multi-step quests and objectives. Never end a step's branch at its own reward when the quest has
  more steps and a once-per-player limit: the first finished step would close the quest.
- Name nodes after what they do, and label anything not real in the name, so a later read shows it.

## Activation limits

Take their shape and window behaviour from the Activation limits guide. If a quest has no limit,
every qualifying event runs the actions: show that unlimited repeat, and the payout impact, inside
the publication proposal so the one approval covers it. Do not ask again for the activation
update unless a material value changed after approval; then show the revised proposal and ask
again. A limit with no window counts over the quest's whole life, so a retest then needs a new
player or a new quest. A Web3 reward has its own repeat rule on top; see [rewards.md](rewards.md).

## What locks once players start

The docs list which parts of a quest cannot change once any player has progress (the Quest guide,
editing a live quest). Before publication, tell the publisher in plain words which parts lock and
that a wrong reward cannot be fixed afterwards in the same quest. Get rewards and amounts right
before the yes.
