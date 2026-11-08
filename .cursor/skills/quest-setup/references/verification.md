# Verification

Status and diagnostics are read-only. They never invoke onboarding or event submission;
list/status keeps the SKILL shortcut, without docs refresh or project preflight.
Use production evidence only, never another environment or another key.

## What the publisher key can read

Only the operations `qp_request.py ops` lists. Check the live contract for a progress or execution
read before promising one: the docs describe player progress as readable by the player (with the
player's token) and on public quests, and say whether a backend can read it. When the publisher key
has no such read, say plainly that this skill cannot see whether the quest ran for a player, and
stop. Never use another key, route or environment to find out.

## Why a quest did not complete

Do not list likely causes. Say what you can check with what is readable (the quest's settings:
status, dates, trigger event name, conditions, limits, and the event the publisher sent) and what
you cannot, then ask. The docs' troubleshooting guidance in the Publisher events guide lists what
to check; use it as data. Keep to the limits in [reply-format.md](reply-format.md#rules).

## Correlate the submitted event first

Keep the identifiers the event answer returned and the idempotency key you sent. Compare the quest
id, event name and player identity with the quest's trigger. If any do not match, report that the
event was not proven to reach this quest.

Do not infer execution from a successful event answer alone. Do not resend an event after a
timeout or unknown response except as [events.md](events.md#after-an-uncertain-response) allows.

## Reading a result

When a progress read is available, read the statuses and error field the docs define for it, and
treat unknown fields as opaque. A step that failed stops the run; earlier steps that succeeded
stay done and are not rolled back (the Quest nodes guide). Report a returned error verbatim and
stop before anything that could create a duplicate external effect.

## Three separate claims

Keep these claims separate:

1. the event was accepted;
2. the quest execution completed;
3. the reward is visible in the player's Backpack or has reached finality.

This skill can report the first one from the event answer, and the second only when a documented
read available to the publisher key proves it. It must not claim the third from either.

## When nothing comes back

A condition miss or an activation limit produces no reward; do not call it a reward failure
without evidence. If nothing can be read, say the outcome is not visible to this skill and do not
resend automatically.

## Unknown results

An unknown event or reward outcome is a safety stop. Preserve the event's idempotency key, quest
id, player and send time. Give them to the publisher with the docs' advice for that case (contact
their Xsolla account manager with the quest id and idempotency key). Never generate a new event to
discover what happened.
