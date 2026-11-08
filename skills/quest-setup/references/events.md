# Events

Sending an event is the contract's publisher events operation. Its body, identifier types, scope,
deduplication, answers and retry guidance are in the operation and the Publisher events guide
([live-docs.md](live-docs.md)); read them before building a payload. No other environment, key or
route.

## Login event with Xsolla ID

For "add a login event that uses my Xsolla ID":

- The quest trigger listens for the event name the site sends, and the event identifies the player
  by Xsolla ID, using the identifier types the Publisher events guide lists.
- The Quests block on a Shop Builder site sends its own events from the browser with the player's
  token once the player is signed in: `login_xsolla_id` (once), `daily_visit` and `weekly_visit`.
  A quest that reacts to one of them uses that exact name and the client-send setting on its
  trigger ([Triggers](quest-authoring.md#triggers)). For any other name, follow Triggers; never
  infer a configured login binding from a quest title.
- Never write `autoEvents` or `loginEventName` on the block: the gate cannot write them. A quest
  trigger must match the event name exactly.

An "add" request never modifies an existing quest. First list the quests (see SKILL.md) and check
whether a quest already uses a login-type trigger. Tell the publisher what exists (quest name,
event name, status) and ask ONE question: create a new quest, or edit that quest. An edit then
needs its own before/after diff and yes ([quest-edit.md](quest-edit.md#editing)). The event name
must match the site's actual binding under [Triggers](quest-authoring.md#triggers). Never invent
or rename a live event name on an active quest, and never re-point an existing quest's trigger as
part of an "add".

For a new quest, show the trigger and event name, wait for a yes in the same conversation, make the
change, then read the quest back and report the trigger as saved. Say that the site must send this
event itself.

## Event gate

Before any send, check that the contract lists the publisher events operation for this key
(`qp_request.py ops`). If it does not, stop and report event sending unavailable. An inactive or
out-of-date quest cannot run: offer activation first. For mixed requests, finish separately
approved quest work first, then report the event blocker with quest id, current status and trigger
name. Do not claim verification.

## Payload

Build the body only from the operation's request schema and the Publisher events guide: the
script refuses fields the schema does not have. Rules this skill adds:

- A fresh UUID idempotency key per new event; the same key only when resending that same event
  (see below).
- The event name is exactly the trigger's event name.
- The player identifier is the one the reward node needs ([rewards.md](rewards.md#exposure-and-recipient)),
  supplied by the publisher. Never put a secret in event properties.
- Leave the scope at the docs' default unless the publisher asks otherwise, and say what the
  default counts across, as the guide describes.
- Never add the load-test property: the docs say it skips the quest, so it tests nothing.

A successful answer means the event was accepted, not that the quest ran; keep the returned ids
for the [verification](verification.md) step.

## Client events

Games and the Quests block send events with the player's token, not a publisher key, through the
player events route the docs describe. The token identifies the player. The platform accepts such
an event only while an active quest of the project allows client events for it (the client-send
setting on a trigger, or the client-events option on an event count); otherwise it refuses it.
This skill never sends client events itself.

## Before sending

- Wait for the propagation delay the docs describe after a quest write.
- Check that the quest is active and inside its date window.
- Show the exact payload, including the generated idempotency key.
- If the publisher changes anything, generate a new key and show the payload again.
- Get a separate yes to this exact payload, including any repeat, and explain whether it can pay
  again. Publication approval never covers an event.

## Test events

A test event is for a real player of the publisher's project. The player id must come from the
publisher and be in the format the docs require for its identifier type. Never invent or reuse a
made-up player id. If they give something that does not fit, or none, ask for the real one and stop.
The quest must be active for the event to run it; activation is its own yes, never implied by the
event yes. Write the event body to a file in the one `mktemp -d` folder and pass
`--body-file <that file>`; never pipe it through `/dev/stdin` or a heredoc, and never retry a
failed send in a loop. To verify execution, send a normal event and warn that matching actions run
for real.

## After an uncertain response

If the request times out or the outcome is otherwise unknown, stop and report "result unknown".
Never send the same player action again with a **new** key: a new key is a new event, so rewards
that already paid could pay a second time.

The docs say the event key is processed only once, and that resending the same event with the
**same** key after a temporary failure (a 5xx, a network error, a reward step that failed
temporarily) continues from the failed step without running the steps that already succeeded. A
reward the docs say is never retried (an unknown payout outcome) is not a temporary failure: see
the safety stops below. So the
only resend this skill offers is the saved payload, unchanged, with its original key, after a new
yes from the publisher.

### An event the publisher sent, not you

When the publisher says their own script or tool sent an event, you never saw the request or
response. Do not resend it. Ask for the payload or, at minimum, the quest id, name, idempotency
key, player and send time. Then follow [`verification.md`](verification.md).

## Safety stops for events and failed rewards

- After a timeout or 5xx on a quest create or update, reconcile before retry per
  [Ambiguous or partial writes](quest-publish.md#ambiguous-or-partial-writes).
  A 422 saved nothing: validation runs before anything is stored.
- After a failed reward, do not send a new event for the same player action. If the cause was
  temporary, offer the same-key resend above. If the quest itself was wrong, it may be locked
  ([quest-edit.md](quest-edit.md#editing)); say so and ask.
- A reward the docs say is never retried automatically, or whose outcome is unknown, is never a
  reason to send another event: the reward may already have paid. Report it with the quest id and
  the event's idempotency key, and tell the publisher to contact their Xsolla account manager with
  them, as the docs advise.
