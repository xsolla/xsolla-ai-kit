<!-- Generated from https://developers.xsolla.com/api/quests/ai-skill.md by .github/scripts/sync_quest_platform_docs.py. Do not edit: the sync workflow replaces this file. -->

# Quest Platform documentation

## Introduction

The Quest Platform runs **quests** for your game: rules of the form ***when a player does this, do that***. You describe the rule once. The platform then watches what your players do, remembers how far each of them has got, and when they get there it runs the quest's **actions**: give a reward, email the player, or both.

> **One example, all the way through**
>
> *A player who finishes three levels in a week gets a chest in your game.* This page builds that quest from a drawing to JSON, and the guides send it for real.

[**New to quests**](https://developers.xsolla.com/api/quests/quest-anatomy)

Read this page top to bottom.

[**Publisher**](https://developers.xsolla.com/api/quests/publisher-guide)

Onboard your project yourself.

> **Working with an AI assistant?**
>
> Give it the [**AI skill**](https://developers.xsolla.com/api/quests/ai-skill) page. It can then create and manage your quests in plain conversation.

### What a quest looks like

Draw the chest quest on paper and you get three boxes joined by arrows:

*Diagram: The chest quest: Level completed (trigger), then Three levels this week (condition), then Give a chest (action)*

> **That drawing is the quest**
>
> Each box is a **node**: one step that does one thing. Each arrow is a **connection**: it says which node comes next. Everything else in these docs adds to these two ideas.

There are three kinds of node, and the chest quest uses one of each:

**Trigger**

**Starts the quest** when something happens.

*A player completed a level.*

**Condition**

**Lets the quest go on** only if something is true.

*At least 3 levels this week.*

**Action**

**Does something**: gives a reward or sends an email.

*Give the player a chest.*

#### Follow one player

Your game tells the platform what players do by sending **events**: short messages such as "player 42 completed a level", named `level_completed`. Here is one player's week; each day they finish a level and your game sends `level_completed`:

- **Monday: 1 level**

  The trigger starts the quest. The condition counts 1 level this week, not 3, so the quest stops. Nothing is given.

- **Tuesday: 2 levels**

  Same again: still under 3, so the quest stops.

- **Wednesday: 3 levels**

  The condition passes and the action gives the chest. The player has **completed** the quest.

> **You never count levels yourself**
>
> Each pass through the quest, from the trigger onwards, is a **run**. The platform keeps each player's **progress** on each quest (`not_started`, `in_progress`, `completed`, or `expired` for an unfinished run once the quest has ended), so your game can show it. A completed quest reads `not_started` again while the player's `per_user` limit still allows another completion. Without a `per_user` limit it stays `completed`.

#### Bigger quests are graphs

A quest doesn't have to be a straight line. A node can lead to several nodes, and each of those to more, so a quest can branch into a tree as wide and as deep as it needs:

*Diagram: A quest as a graph: the condition leads to three actions, and Give a chest leads on to Tell the player*

**Branch out**

A node can lead to any number of nodes, and every one of them runs, in the order listed.

**Chain**

A node runs only after the one before it succeeded, so "Tell the player" comes after the chest.

**Gate**

A condition decides whether everything after it runs.

> **Two rules keep a graph predictable**
>
> Arrows can't loop back to an earlier node, and the first condition that is not met, or action that fails, ends the run. So put the action that matters most first.

### Writing the quest down

You [create a quest](https://developers.xsolla.com/api/quests/publisher-api/create-quest-in-project) by sending it to the platform as JSON. The JSON says exactly what the drawing says, in three steps:

**1. Write each box as a node**

Every [node](https://developers.xsolla.com/api/quests/quest-nodes) has an `id` you make up, a `name`, its kind (`type`), what exactly it does (`subtype`) and its settings (`parameters`):

**Trigger**

**Level completed**: a [dynamic_event](https://developers.xsolla.com/api/quests/node-dynamic-event) trigger, waiting for `level_completed`.

```json
{
  "id": "0f2c6d1e-3b4a-4c5d-8e9f-101112131415",
  "name": "Level completed",
  "type": "trigger",
  "subtype": "dynamic_event",
  "parameters": {
    "event_name": "level_completed"
  }
}
```

**Condition**

**Three levels this week**: a [custom_attributes_check](https://developers.xsolla.com/api/quests/node-custom-attributes-check) condition, at least 3 `level_completed` events this week. Its `parameters` are shortened here; the whole quest in step 3 shows them in full.

```json
{
  "id": "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d",
  "name": "Three levels this week",
  "type": "condition",
  "subtype": "custom_attributes_check",
  "parameters": {
    "type": "comparison",
    // …
  }
}
```

**Action**

**Give a chest**: an [issue_game_item](https://developers.xsolla.com/api/quests/node-issue-game-item) action, giving the player 1 × `weekly_chest`.

```json
{
  "id": "2b3c4d5e-6f7a-4b8c-9d0e-1f2a3b4c5d6e",
  "name": "Give a chest",
  "type": "action",
  "subtype": "issue_game_item",
  "parameters": {
    "purpose": "weekly_level_grinder",
    "items": [
      {
        "sku": "weekly_chest",
        "quantity": 1
      }
    ]
  }
}
```

[**Quest nodes**](https://developers.xsolla.com/api/quests/quest-nodes) lists every `subtype` and its parameters.

**2. Draw the arrows as connections**

Each arrow is one entry in [connections](https://developers.xsolla.com/api/quests/connections): the `id` of the node it starts from, and the `id` of the node it points to.

```json
"connections": {
  "0f2c6d1e-3b4a-4c5d-8e9f-101112131415": [
    {
      "nodeId": "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d"
    }
  ],
  "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d": [
    {
      "nodeId": "2b3c4d5e-6f7a-4b8c-9d0e-1f2a3b4c5d6e"
    }
  ]
}
```

Read it as "after *Level completed* comes *Three levels this week*; after that comes *Give a chest*". The last box has no entry, so the quest ends there. A node with several arrows lists several `nodeId`s.

**3. Wrap them in a quest**

Nodes and connections go inside the quest, next to its name, the dates it runs between and its activation limits. [**Chest for three levels a week**](https://developers.xsolla.com/api/quests/examples-chest-quest) shows the whole quest, exactly as the guides send it.

A quest runs only while its `status` is `active` and the date is between `start_date` and `end_date`. [**Quest guide**](https://developers.xsolla.com/api/quests/quest-guide) lists every field and rule.

The [**Publisher guide**](https://developers.xsolla.com/api/quests/publisher-guide) sends this quest in full.

### How you plug it in

Every integration does the same three things: it creates quests, sends events as players play, and shows players their progress. The platform does everything in between:

*Diagram: Your backend creates quests and sends events; the platform matches, checks limits and conditions, runs actions and records progress, which a game client signed in as the player reads*

> **The platform keeps the state**
>
> You don't store progress, count events or call the reward systems yourself.

You connect with a Publisher Account token or a publisher key, and you onboard your project yourself with one call. [**Authentication**](https://developers.xsolla.com/api/quests/authentication) lists the credentials each operation accepts.

The API is at `https://quests-platform.xsolla.com`, and every route carries the API version, `/api/v2/...`. Keep publisher keys on your servers, never in a game client.

[**Publisher guide**](https://developers.xsolla.com/api/quests/publisher-guide)

Onboard your project, create the chest quest, send events and show quests to players.

### Growing the quest

The chest quest's nodes say *what* it does. Fields on the quest itself extend that logic without touching the nodes: when it runs, how often it pays, what progress players see, and who can see the quest and in what form. Each is explained where it belongs:

| Field | What it adds | Read |
| --- | --- | --- |
| `status`, `start_date`, `end_date` | When the quest runs: drafts, pausing, and the lock once players have progress | [**Quest lifecycle**](https://developers.xsolla.com/api/quests/quest-guide#quest-lifecycle) |
| `activation_limits` | How often it pays: per player, in total, per day, week or month | [**Activation limits**](https://developers.xsolla.com/api/quests/activation-limits) |
| `objectives` | The steps players see on their way to completing it | [**Objectives**](https://developers.xsolla.com/api/quests/public-quests-guide#public-objectives) |
| `is_public`, `public_view` | Who can see the quest, and what they see | [**Public quests guide**](https://developers.xsolla.com/api/quests/public-quests-guide) |
| `client_sendable` on the trigger | Whether a game client can send the events that start it | [**Client events**](https://developers.xsolla.com/api/quests/publisher-events-guide#publisher-sending-client) |

To change what the quest *does*, swap or add nodes instead: [**Quest nodes**](https://developers.xsolla.com/api/quests/quest-nodes) explains how a quest runs and lists every node.

### Find your path

Pick the card that matches what you are doing now.

[**Publisher**](https://developers.xsolla.com/api/quests/publisher-guide)

Connect your project and build the chest quest.

[**Building quests**](https://developers.xsolla.com/api/quests/quest-guide)

Fields, connections, conditions, limits and editing.

[**Every node**](https://developers.xsolla.com/api/quests/quest-nodes)

Each trigger, condition and action, with an example.

[**Examples**](https://developers.xsolla.com/api/quests/examples)

Whole quests and step-by-step walkthroughs.

[**Public quests guide**](https://developers.xsolla.com/api/quests/public-quests-guide)

Show quests to players, with or without their progress.

### Before you go live

These are the rules that matter once real players and real rewards are involved.

#### What the platform guarantees

**Processed asynchronously**

A `200` from the events endpoint means the event was **accepted**. Quests run moments later.
A game client signed in as the player sees the outcome on public quests through [List quests with the caller's progress](https://developers.xsolla.com/api/quests/player-progress/list-me-quests).
There is no progress read for your backend or for private quests.

**Once per quest**

Each quest processes an `idempotency_key` once, so a retried event never runs a quest's actions twice.

**Completed steps are not repeated**

A run that resumes after a failure skips the actions that already succeeded.

**Projects are isolated**

An event reaches only the quests of the project it is sent for.

### Glossary

| Term | Meaning |
| --- | --- |
| **Account** | An Xsolla project maps to an account; quests and player progress belong to it. |
| **Workspace** | A list of accounts. An Xsolla merchant maps to a workspace, and each of its projects to an account in it. |
| **Quest** | A graph of nodes with a status, a time window (`start_date` to `end_date`) and optional activation limits. |
| **Node** | One step of a quest: a trigger, a condition or an action. Each has a `type` and a `subtype`, such as [dynamic_event](https://developers.xsolla.com/api/quests/node-dynamic-event). |
| **Event** | Something a player did: a name, the player's identifiers, a timestamp and optional properties. |
| **Player** | The person an event is about, resolved from its identifiers (`gamer_id`, `xsolla_id`, email). Progress and per-player limits belong to the player. |
| **Run** | One pass of one quest for one event or one scheduled tick. |
| **Activation limit** | A cap on completions, per player (`per_user`) or across all players (`global`), optionally per time window. |
| **Progress** | A player's state on a quest: `not_started`, `in_progress`, `completed` or `expired`, with the count of completions. |
| **Idempotency key** | A UUID per real-world occurrence of an event. Each quest processes a key once. |
| [**Scope**](https://developers.xsolla.com/api/quests/publisher-events-guide#publisher-sending-scope) | Which later event counts can include an event: `private`, `global`, `within_publisher`, `within_project` or `within_quest`. |
| **Backpack** | The player-facing inventory where item rewards appear. |
| **DDH** | Digital Delivery Hub: delivers currency and items into a publisher's game. |
| **SKU** | An item ID, unique only within its project. |

## Quest guide

***Everything one quest is made of, and the rules the API checks when you save it.*** This guide follows the chest quest from the introduction; the whole quest is in [**Chest for three levels a week**](https://developers.xsolla.com/api/quests/examples-chest-quest). Every field is also described on the create and update operations, and every node under [**Quest nodes**](https://developers.xsolla.com/api/quests/quest-nodes).

[**Fields**](https://developers.xsolla.com/api/quests/quest-guide#quest-fields)

What a quest holds and its rules.

[**Lifecycle**](https://developers.xsolla.com/api/quests/quest-guide#quest-lifecycle)

Drafts, pausing and when it runs.

[**Nodes**](https://developers.xsolla.com/api/quests/quest-guide#quest-node-kinds)

What starts it, who qualifies, what runs.

[**Connections**](https://developers.xsolla.com/api/quests/connections)

How nodes are wired into a graph.

[**Limits**](https://developers.xsolla.com/api/quests/activation-limits)

How often a quest may complete.

[**Objectives**](https://developers.xsolla.com/api/quests/public-quests-guide#public-objectives)

The steps a player sees on the way.

#### Fields

> **Every field, type and limit is in the API reference**
>
> This section explains what the fields mean. For the exact schema (types, required fields, lengths and allowed values), open [Create a new quest (project scope)](https://developers.xsolla.com/api/quests/publisher-api/create-quest-in-project). The update operation takes the same body.

**Identity**

| Field | Rules |
| --- | --- |
| `name` | Required, 1 to 255 characters. |
| `description` | Optional, 5 to 1000 characters. |
| `type` | Required. Use `liveops`. |
| `created_by` | Required, 1 to 255 characters, any identifier. |
| `metadata` | Free-form JSON, nested at most 5 levels (2 in a draft). |

**Logic**

| Field | Rules |
| --- | --- |
| `nodes` | At least two when `active`. Node names have at least 3 characters. [**Quest nodes**](https://developers.xsolla.com/api/quests/quest-nodes) describes every node. |
| `connections` | Required when `active`; see [**Connections**](https://developers.xsolla.com/api/quests/connections). |

**Behaviour**

| Field | Rules |
| --- | --- |
| `status` | `active` runs; `inactive` is kept but never runs; `draft` is saved with relaxed validation and never runs. See [**Quest lifecycle**](https://developers.xsolla.com/api/quests/quest-guide#quest-lifecycle). |
| `start_date`, `end_date` | Required when `active`. `start_date` no more than a day in the past, except on an update that sends back the stored `start_date` unchanged; `end_date` not in the past and not before `start_date`. |
| `activation_limits` | Optional; see [**Activation limits**](https://developers.xsolla.com/api/quests/activation-limits). |
| `objectives` | Optional; see [**Objectives**](https://developers.xsolla.com/api/quests/public-quests-guide#public-objectives). |
| `is_public`, `public_view` | Optional; see [**Public quests guide**](https://developers.xsolla.com/api/quests/public-quests-guide). |

A draft skips the date, node-count and connection rules, so a quest can be saved while it is being built.

#### Quest lifecycle

*Diagram: Quest lifecycle: draft to active, active and inactive both ways, any status to deleted*

| Status | Runs | Notes |
| --- | --- | --- |
| **draft** | Never | Saved with relaxed validation, for work in progress |
| **active** | Between `start_date` and `end_date` | Fully validated on save; a schedule is registered when saved `active` |
| **inactive** | Never | Kept with its progress. It can be set back to `active` with its stored `start_date`. A new `start_date` must be at most a day in the past, and can be set only while no player has progress (see [**Editing a live quest**](https://developers.xsolla.com/api/quests/quest-guide#quest-editing)) |
| **deleted** | Never | No longer listed or run |

##### Editing a live quest

Players' progress refers to node IDs, so the API refuses a **structural** edit to a quest that players already have progress on (409, `quest_has_progress`).

**Locked once players have progress**

Nodes (IDs, types, `type_version`, parameters), connections, activation limits and `start_date`.

**Can always change**

Name, description, metadata, `end_date`, `status`, `is_public` and `public_view`, `objectives`, and node names.

The order of edges and of activation limits is not checked, so a reorder is accepted on a quest with progress even though it can change which node runs first or which limit applies.

> **A new start_date is checked against today**
>
> An update that keeps or sets `status: active` with a different `start_date` checks it again: it must not be more than a day in the past. Sending back the stored `start_date` unchanged is always accepted, so a live quest can be edited, paused and activated again. Changing `start_date` itself is a structural change, so it is refused once players have progress.

> **Wrong action parameters cannot be fixed in place**
>
> A quest whose action parameters turn out to be wrong after players have progress cannot be fixed: create a new quest.

#### Nodes

A quest's `nodes` are its triggers, conditions and actions. [**Quest nodes**](https://developers.xsolla.com/api/quests/quest-nodes) explains how a run goes through them and lists every node with its parameters and an example:

[**How a quest runs**](https://developers.xsolla.com/api/quests/quest-nodes)

From the trigger through limits and conditions to the actions.

[**Triggers**](https://developers.xsolla.com/api/quests/nodes-trigger)

Started by player events or on a schedule.

[**Conditions**](https://developers.xsolla.com/api/quests/nodes-condition)

Check the player, or run for a CRM segment.

[**Actions**](https://developers.xsolla.com/api/quests/nodes-action)

Rewards and emails.

#### More in a quest

Beyond its nodes, a quest can control how its nodes are wired, how often it pays, what steps players see, and whether players can see it at all. Each has its own page:

[**Connections**](https://developers.xsolla.com/api/quests/connections)

How nodes are wired into a graph, outcome edges, loops, and what happens when a node fails.

[**Activation limits**](https://developers.xsolla.com/api/quests/activation-limits)

How often a quest may complete: per player, for everyone, per day, week or month.

[**Objectives**](https://developers.xsolla.com/api/quests/public-quests-guide#public-objectives)

The steps a player sees on the way, as counters or checks.

[**Public quests guide**](https://developers.xsolla.com/api/quests/public-quests-guide)

Making a quest visible to players, and choosing what they see.

## Quest nodes

***Every node a quest can use, with its parameters and an example.*** The page is generated from the same definitions the API validates quests against, so it always matches what the API accepts.

**How a quest runs.** A quest is a graph of nodes, and activation limits sit on top of the whole quest:

*Diagram: Activation limits around the whole quest; inside it a trigger, a condition and an action*

Every run goes the same way:

- **A trigger starts a run**

  For a player event, or on a schedule.

- **Every activation limit must have room**

  Otherwise the run stops before any condition.

- **Conditions check the event, the player or their history**

  The run continues past a condition only when its check passes.

- **Actions do something**

  Grant a reward or send an email.

**Reading a node.** Every node in a quest's `nodes` has the same fields; only `parameters` differs by subtype:

| Field | What it is |
| --- | --- |
| `id` | A UUID you generate. Connections refer to it, so keep it stable across updates |
| `name` | Display name, at least 3 characters |
| `type` | `trigger`, `condition` or `action` |
| `subtype` | The kind of node: one of the sections below |
| `parameters` | The node's settings, listed in its section |
| `type_version` | Optional label stored with the node |

Each node section shows:

* *Which nodes you can use*: the nodes on this page; [List permitted quest node types (project scope)](https://developers.xsolla.com/api/quests/publisher-api/get-quest-node-types-in-project) returns the same nodes as JSON Schemas, for tools.
* *Parameters*: the fields inside the node's `parameters` object, not the whole node; *Validation* adds the rules a schema cannot express.
* *Example*: a whole node, filled in and accepted by the API as shown.

#### Summary

| Node | What it does | The event needs |
| --- | --- | --- |
| [dynamic_event](https://developers.xsolla.com/api/quests/node-dynamic-event) | Starts the quest each time an event named `event_name` is sent for a player. | None |
| [scheduled_event](https://developers.xsolla.com/api/quests/node-scheduled-event) | Starts the quest on a schedule instead of a player event: a recurring standard cron expression (UTC) or a single future `date_time`. | None |
| [crm_segment_match](https://developers.xsolla.com/api/quests/node-crm-segment-match) | Fetches the players of the User CRM segment `crm_segment_id` and runs the nodes after it once for each player. | None |
| [custom_attributes_check](https://developers.xsolla.com/api/quests/node-custom-attributes-check) | Continues only if a boolean expression holds. | None |
| [issue_catalog_item](https://developers.xsolla.com/api/quests/node-issue-catalog-item) | Grants existing catalog items by SKU to the player's Backpack. | `xsolla_id`. |
| [issue_game_item](https://developers.xsolla.com/api/quests/node-issue-game-item) | Delivers catalog items by SKU straight into the player's game through DDH, without the Backpack. | `gamer_id`. |
| [issue_loyalty_points](https://developers.xsolla.com/api/quests/node-issue-loyalty-points) | Grants loyalty points of the program `loyalty_points_id`. | `gamer_id`. |
| [issue_scoped_currency](https://developers.xsolla.com/api/quests/node-issue-scoped-currency) | Credits amount of a project's scoped currency sku, such as pixel, to the player's Currency Wallet, where it shows in Backpack. | `xsolla_id`. |
| [issue_virtual_currency](https://developers.xsolla.com/api/quests/node-issue-virtual-currency) | Delivers virtual currency packages by SKU to the player through DDH. | `gamer_id`. |
| [issue_web3_item](https://developers.xsolla.com/api/quests/node-issue-web3-item) | Mints a Web3 item (NFT) to the player, at most once per player and quest. | `xsolla_id`. |
| [issue_web3_token](https://developers.xsolla.com/api/quests/node-issue-web3-token) | Sends amount of the Web3 token `item_sku` to the player's wallet. | `xsolla_id` and the publisher project. |
| [crm_send_email](https://developers.xsolla.com/api/quests/node-crm-send-email) | Emails the event's player when the event carries an email, otherwise every player in the CRM segment `crm_segment`. | None |

### Triggers

A trigger decides how runs start. There are two kinds:

| Trigger | Starts a run |
| --- | --- |
| [dynamic_event](https://developers.xsolla.com/api/quests/node-dynamic-event) | Each time a player event with its name is sent, for that player |
| [scheduled_event](https://developers.xsolla.com/api/quests/node-scheduled-event) | On a schedule set in the quest, with no event sent and no player |

A quest can have more than one trigger. Each event starts the run at the trigger whose `event_name` matches it, and the run follows that trigger's connections.

##### dynamic_event

Starts the quest each time an event named `event_name` is sent for a player.

**Parameters:** the fields of the node's `parameters` object.

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `client_sendable` | boolean | no | Allow a game client to send this event with the player's token. Off by default: only a backend can send it. |
| `event_name` | string | yes | Name of the event that starts the quest, matched against the event name sent to the events API. Min length: `1`. |

**Example:**

```json
{
  "id": "da9d2aa1-63e0-5c4c-9a15-f20df93798ff",
  "name": "Level completed",
  "type": "trigger",
  "subtype": "dynamic_event",
  "parameters": {
    "event_name": "level_completed",
    "client_sendable": false
  }
}
```

The run is **for the player** the event names: their progress, conditions and rewards. The [**Publisher events guide**](https://developers.xsolla.com/api/quests/publisher-events-guide) describes the event.

Your backend sends the event. With `client_sendable: true` the game client may send it as well, with the player's token; see [**Client events**](https://developers.xsolla.com/api/quests/publisher-events-guide#publisher-sending-client).

The event reaches the quest only when the quest is `active` and inside its dates (UTC), the event was sent with a credential of the quest's account, and any publisher and project it names match the quest's. [Which quests an event reaches](https://developers.xsolla.com/api/quests/publisher-events-guide#publisher-sending-routing) lists every rule.

**A quest started by player events: the chest quest**

A player who finishes three levels in a week gets a chest, at most once a week:

**Graph:** Level completed → Three levels this week → Give a chest

```json
{
  "name": "Weekly level grinder",
  "description": "Reward players who finish three levels in a week with a chest in the game.",
  "type": "liveops",
  "publisher_id": "123456",
  "project_id": "654321",
  "status": "active",
  "created_by": "liveops-team",
  "start_date": "2026-11-02T00:00:00Z",
  "end_date": "2026-11-30T23:59:59Z",
  "activation_limits": [
    {
      "type": "per_user",
      "count": 1,
      "time_window": {
        "duration_unit": "week"
      }
    },
    {
      "type": "global",
      "count": 10000
    }
  ],
  "nodes": [
    {
      "id": "0f2c6d1e-3b4a-4c5d-8e9f-101112131415",
      "name": "Level completed",
      "type": "trigger",
      "subtype": "dynamic_event",
      "parameters": {
        "event_name": "level_completed"
      }
    },
    {
      "id": "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d",
      "name": "Three levels this week",
      "type": "condition",
      "subtype": "custom_attributes_check",
      "parameters": {
        "type": "comparison",
        "left": {
          "type": "event",
          "value": "level_completed",
          "time_window": {
            "duration_unit": "week"
          }
        },
        "operator": {
          "type": "numeric",
          "operation": "gte"
        },
        "right": {
          "type": "value",
          "value": 3
        }
      }
    },
    {
      "id": "2b3c4d5e-6f7a-4b8c-9d0e-1f2a3b4c5d6e",
      "name": "Give a chest",
      "type": "action",
      "subtype": "issue_game_item",
      "parameters": {
        "purpose": "weekly_level_grinder",
        "items": [
          {
            "sku": "weekly_chest",
            "quantity": 1
          }
        ]
      }
    }
  ],
  "connections": {
    "0f2c6d1e-3b4a-4c5d-8e9f-101112131415": [
      {
        "nodeId": "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d"
      }
    ],
    "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d": [
      {
        "nodeId": "2b3c4d5e-6f7a-4b8c-9d0e-1f2a3b4c5d6e"
      }
    ]
  }
}
```

##### scheduled_event

Starts the quest on a schedule instead of a player event: a recurring standard cron expression (UTC) or a single future `date_time`. `event_name` names the scheduled event.

**Parameters:** the fields of the node's `parameters` object.

**Validation:** Cron must parse as a standard cron expression. A new or changed `date_time` must be in the future. Active schedules also require valid project scope and credentials.

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `cron` | string | no | Standard cron expression (five fields, or a descriptor such as @daily), evaluated in UTC. Set exactly one of cron and `date_time`. |
| `date_time` | string (date-time) | no | A single future time (RFC 3339) to fire once. Set exactly one of cron and `date_time`. |
| `event_name` | string | yes | Name of the event the schedule sends; it identifies the scheduled event. Min length: `1`. |

**Example:**

```json
{
  "id": "fef1cfb5-0c5b-5a70-8e9d-9a0c6fc2654b",
  "name": "Every Monday at 09:00",
  "type": "trigger",
  "subtype": "scheduled_event",
  "parameters": {
    "event_name": "weekly_vip_reward",
    "cron": "0 9 * * 1"
  }
}
```

The Quest Platform starts the quest itself, so nothing needs to be sent.

For a single run, set `date_time` instead of `cron` (a node takes one or the other):

```json
"parameters": {
  "event_name": "launch_day_gift",
  "date_time": "2026-12-01T09:00:00Z"
}
```

| Setting | How it works |
| --- | --- |
| **When** | `cron` repeats, in UTC (`0 9 * * 1` is every Monday at 09:00); `date_time` runs once, at a future time. Set exactly one. |
| **Start and stop** | The schedule is registered when the quest is activated: created `active`, or updated to `active` from another status. Saving it `inactive` or deleting it stops it: the next scheduled fire publishes nothing and removes the schedule. |
| **Changing the schedule** | A changed `cron` or `date_time` on an active quest is picked up at the old schedule's next fire: that fire publishes nothing and moves the schedule, and later runs follow the new value. |
| **One-off runs** | After a `date_time` run the schedule is removed; the quest stays `active`. |
| **Quest dates** | The schedule also fires before `start_date` and after `end_date`, but those runs do nothing. |
| **One per quest** | A quest has one schedule: use a single [scheduled_event](https://developers.xsolla.com/api/quests/node-scheduled-event). A second one is not refused, but the two overwrite each other. |
| **Event name** | Ordinary events with the same `event_name` start the quest too, for their player. Pick a name nothing else sends. |
| **Who can activate it** | Activating a scheduled quest (creating it `active` or switching it to `active`) needs a Publisher Account token. With a publisher key it is refused with `400`. Updating a quest that is already `active` registers nothing, so these checks do not apply to it. |
| **If registering fails** | When activating the quest cannot register its schedule, nothing is saved: send the request again. |

> **A scheduled run has no player**
>
> A scheduled run belongs to the quest's **account, not to a player**. On its own it suits actions that need none, such as a CRM email to a segment. To act on players, add a [crm_segment_match](https://developers.xsolla.com/api/quests/node-crm-segment-match) condition: the rest of the quest then runs once for every player in that CRM segment, each with their own identifiers (`xsolla_id`, email).

[**Monday crate for VIP players**](https://developers.xsolla.com/api/quests/examples-scheduled) on the Examples page gives each VIP player a crate every Monday.

### Conditions

A condition decides whether the run goes on, and for which players. There are two kinds:

| Condition | The run goes on |
| --- | --- |
| [crm_segment_match](https://developers.xsolla.com/api/quests/node-crm-segment-match) | Once for each player in a CRM segment |
| [custom_attributes_check](https://developers.xsolla.com/api/quests/node-custom-attributes-check) | Only when a check on the event's player passes |

##### crm_segment_match

Fetches the players of the User CRM segment `crm_segment_id` and runs the nodes after it once for each player.

**Parameters:** the fields of the node's `parameters` object.

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `crm_segment_id` | integer (int64) | yes | ID of the User CRM segment whose players the following nodes run for. Minimum: `1`. |

**Example:**

```json
{
  "id": "a30c7e98-95ff-5636-827b-0b81fe96f483",
  "name": "Players in the VIP segment",
  "type": "condition",
  "subtype": "crm_segment_match",
  "parameters": {
    "crm_segment_id": 4242
  }
}
```

A **CRM segment** is a list of your players kept in Xsolla's User CRM, such as "VIP players". Each player in it comes with their Xsolla ID and email, so whatever follows the node is done for every player, whichever player the run started for. [**Monday crate for VIP players**](https://developers.xsolla.com/api/quests/examples-scheduled) uses it: a crate for each VIP player every Monday.

> **Emailing a segment**
>
> [crm_send_email](https://developers.xsolla.com/api/quests/node-crm-send-email) is an action. When the event carries an email, it emails that player only; when it carries none, it emails **every player in its segment** at once. So placed after [crm_segment_match](https://developers.xsolla.com/api/quests/node-crm-segment-match), it sends one email per player; on its own, one send to the whole segment.

**Limits**: at most 5,000 players per segment. A larger segment fails the run.

##### custom_attributes_check

Continues only if a boolean expression holds. Groups combine conditions with and/or; a comparison compares two operands: a fixed value or the number of the player's events with a given name in a time window.

**Parameters:** the fields of the node's `parameters` object.

**Validation:** Operand values must be compatible with the operator domain. Event operands require a time window, numeric operators and whole-number thresholds; mod requires a positive divisor. These domain rules are checked on create/update.

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `conditions` | array of object | no | and / or only: the expressions to combine. Recursive: same fields as the top-level parameters. |
| `left` | object | no | Comparison only: the first operand. |
| `left.include_client_events` | boolean | no | Event operands only: also count events a game client sent. Off by default: only backend events count. |
| `left.time_window` | object | no | Required for event operands: count only the events of the current calendar day, week (starting Monday) or month. |
| `left.time_window.duration_unit` | string | yes | Calendar window: day, week or month. |
| `left.type` | string | yes | value: the literal in value. event: the number of the user's events named in value. One of: `value`, `event`. |
| `left.value` | any | yes | The literal or the event name, depending on type. |
| `operator` | object | no | Comparison only: how left and right are compared. |
| `operator.operation` | string | yes | numeric: eq, neq, gt, lt, gte, lte, or mod (left is divisible by right). string: eq, neq, contains. boolean: eq, neq. `string_array`: in, `not_in`, intersects. |
| `operator.type` | string | yes | Type of the compared values: numeric, string, boolean or `string_array`. |
| `right` | object | no | Comparison only: the second operand. |
| `right.include_client_events` | boolean | no | Event operands only: also count events a game client sent. Off by default: only backend events count. |
| `right.time_window` | object | no | Required for event operands: count only the events of the current calendar day, week (starting Monday) or month. |
| `right.time_window.duration_unit` | string | yes | Calendar window: day, week or month. |
| `right.type` | string | yes | value: the literal in value. event: the number of the user's events named in value. One of: `value`, `event`. |
| `right.value` | any | yes | The literal or the event name, depending on type. |
| `type` | string | yes | and or or combines the expressions in conditions; comparison compares left with right using operator. One of: `and`, `or`, `comparison`. |

**Example:**

```json
{
  "id": "c1d5e2f3-6a7b-4c8d-9e0f-1a2b3c4d5e6f",
  "name": "Three levels this week, after a purchase this month",
  "type": "condition",
  "subtype": "custom_attributes_check",
  "parameters": {
    "type": "and",
    "conditions": [
      {
        "type": "comparison",
        "left": {
          "type": "event",
          "value": "level_completed",
          "time_window": {
            "duration_unit": "week"
          },
          "include_client_events": true
        },
        "operator": {
          "type": "numeric",
          "operation": "gte"
        },
        "right": {
          "type": "value",
          "value": 3
        }
      },
      {
        "type": "comparison",
        "left": {
          "type": "value",
          "value": 1
        },
        "operator": {
          "type": "numeric",
          "operation": "lte"
        },
        "right": {
          "type": "event",
          "value": "purchase_completed",
          "time_window": {
            "duration_unit": "month"
          },
          "include_client_events": false
        }
      }
    ]
  }
}
```

The check looks at the player the event is about: how many events of a kind they sent this day, week or month, and fixed values, combined with `and` / `or`. When it fails, the run stops there for that player.

**Writing the expression.** The node holds one expression. An expression is either a **group** or a **comparison**:

* A group has `type` `and` or `or`, and the expressions to combine in `conditions`. Groups nest.
* A comparison has `type: "comparison"`, a `left` and a `right` operand, and an `operator`.

Each operand is one of two kinds, and both sides can be either.

**value**

A literal (number, string, boolean or array), used as is. It must not be null.

**event**

An event name: the number of events with that name sent under the same identifier as this event (its `xsolla_id`, else `gamer_id`, else `email`; `guest_id` is not counted) in the current calendar `day`, `week` or `month`. `time_window` is required. Only `numeric` operators, against a whole number.

| Operator `type` | `operation` |
| --- | --- |
| **numeric** | `eq`, `neq`, `gt`, `lt`, `gte`, `lte`, `mod` (left is divisible by right; the divisor must be positive) |
| **string** | `eq`, `neq`, `contains` (left contains right) |
| **boolean** | `eq`, `neq` |
| **string_array** | `in`, `not_in` (a string on the left, an array on the right), `intersects` (arrays on both sides share a value) |

[**Example conditions**](https://developers.xsolla.com/api/quests/examples-conditions) on the Examples page shows one: every third purchase.

### Actions

An action does something: grants a reward or sends an email. There are two kinds: rewards (the `issue_*` nodes) and emails.

| Action | Does |
| --- | --- |
| [issue_catalog_item](https://developers.xsolla.com/api/quests/node-issue-catalog-item) | Grants catalog items to the player's Backpack |
| [issue_game_item](https://developers.xsolla.com/api/quests/node-issue-game-item) | Delivers catalog items straight into the player's game through DDH |
| [issue_loyalty_points](https://developers.xsolla.com/api/quests/node-issue-loyalty-points) | Grants loyalty points of a program |
| [issue_scoped_currency](https://developers.xsolla.com/api/quests/node-issue-scoped-currency) | Credits a project's scoped currency, such as pixels, to the player's Currency Wallet, shown in Backpack |
| [issue_virtual_currency](https://developers.xsolla.com/api/quests/node-issue-virtual-currency) | Delivers virtual currency packages into the player's game through DDH |
| [issue_web3_item](https://developers.xsolla.com/api/quests/node-issue-web3-item) | Mints a Web3 item (NFT) to the player |
| [issue_web3_token](https://developers.xsolla.com/api/quests/node-issue-web3-token) | Sends Web3 tokens to the player's wallet |
| [crm_send_email](https://developers.xsolla.com/api/quests/node-crm-send-email) | Emails the event's player, or every player in a CRM segment when the event has no email |

When an action fails, the quest stays `in_progress`, and its progress block can carry a `last_error` with a `class` (`transient`, `permanent` or `indeterminate`), a `code` and the time `at`; it never carries a message. Each reward node lists its codes under **Errors** at the end of its section. A failure with no code of its own, for example a refusal from Backpack, reads `application_error`, and `infrastructure` when a service the action depends on did not answer, even after retries.

For anything else, contact your Xsolla account manager with the quest ID and the event's `idempotency_key`.

> **Tip: order matters**
>
> Put an email after the reward it announces, so it is sent only once the reward succeeded. [**Order and failures**](https://developers.xsolla.com/api/quests/connections#connections-order-failures) explains why.

##### issue_catalog_item

Grants existing catalog items by SKU to the player's Backpack. The event needs `xsolla_id`.

**Parameters:** the fields of the node's `parameters` object.

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | array of object | yes | Items to grant. Min items: `1`. |
| `items[].quantity` | integer (int64) | no | Zero or omitted defaults to 1. Default: `1`. Minimum: `0`. Maximum: `100`. |
| `items[].sku` | string | yes | SKU of an existing item in the project catalog. Min length: `1`. |
| `items[].type` | string | no | Empty defaults to `virtual_item`. Default: `virtual_item`. |
| `purpose` | string | yes | Reason recorded with the grant. Min length: `1`. |

**Example:**

```json
{
  "id": "dae66a8e-d527-5985-b073-dc2b99fb094e",
  "name": "Give a crate",
  "type": "action",
  "subtype": "issue_catalog_item",
  "parameters": {
    "purpose": "weekly_vip_reward",
    "items": [
      {
        "sku": "vip_crate",
        "quantity": 1,
        "type": "virtual_item"
      }
    ]
  }
}
```

**Set up first:** items whose SKUs Backpack can resolve.

**Backpack.** This node grants items to the player's Backpack, by `xsolla_id`. Guests cannot receive them.

* **Which catalogue**: the items are granted from the project the quest belongs to.
* **Name and image**: this node sends only SKUs, and Backpack takes the name, type and image from its catalogue; a SKU it does not know fails with `not_found`.
* **Description**: items carry no description; set it on the catalogue item.
* **Limits**: `quantity` is 1 to 100 per SKU, and Backpack takes up to 100 items per request; a larger grant is split into several requests.
* Players see their items at [backpack.xsolla.com](https://backpack.xsolla.com/) and [wallet.xsolla.com/backpack](https://wallet.xsolla.com/backpack).

**Errors**: the codes this node can leave in the progress block's `last_error.code`:

| Error | Meaning | Fix |
| --- | --- | --- |
| `missing_xsolla_id` | The event has no `xsolla_id` and no `email` to find it from | Add `xsolla_id` to `user_ids`, or send the player's `email` |
| `email_not_resolved` | The event had no `xsolla_id`, and its `email` belongs to no Xsolla account or is not a valid address | Send the player's `xsolla_id`, or the email of their Xsolla account |
| `xsolla_id_lookup_unavailable` | The Xsolla account could not be looked up from the `email` at the moment | Nothing; the node is retried. If it still fails, resend the event under a new `idempotency_key` |
| `application_error` | No code of its own: Backpack does not know a SKU, or Backpack refused the Quest Platform's access | Use SKUs Backpack knows; if they are right, contact your Xsolla account manager |
| `invalid_reward_config` | The node's parameters are invalid; it fails for every player | Fix the parameters in a new quest |

##### issue_game_item

Delivers catalog items by SKU straight into the player's game through DDH, without the Backpack. The project's user validation webhook confirms the player. The event needs `gamer_id`.

**Parameters:** the fields of the node's `parameters` object.

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | array of object | yes | Items to deliver. Min items: `1`. |
| `items[].quantity` | integer (int64) | no | Zero or omitted defaults to 1. Default: `1`. Minimum: `0`. Maximum: `100`. |
| `items[].sku` | string | yes | SKU of the item in the project catalog. Min length: `1`. |
| `purpose` | string | yes | Reason recorded with the grant. Min length: `1`. |

**Example:**

```json
{
  "id": "9a0a0369-8ef0-5f99-8ee5-f8d665c3672b",
  "name": "Give a sword",
  "type": "action",
  "subtype": "issue_game_item",
  "parameters": {
    "purpose": "weekly_level_grinder",
    "items": [
      {
        "sku": "iron_sword",
        "quantity": 1
      }
    ]
  }
}
```

**Set up first:** the items (SKUs) in the project's catalogue, and the project's [user validation webhook](https://developers.xsolla.com/webhooks/user-validation/user-validation) enabled.

**Limits**: `quantity` is 1 to 100 per SKU.

**Errors**: the codes this node can leave in the progress block's `last_error.code`:

| Error | Meaning | Fix |
| --- | --- | --- |
| `missing_gamer_id`, `ddh_webhook_disabled`, `ddh_user_rejected`, `ddh_request_rejected` | DDH could not deliver: no `gamer_id`, the project's user validation webhook is off, the game refused the player, or DDH refused the request | Check the event and the project's webhook settings |
| `invalid_reward_config` | The node's parameters are invalid, or the quest has no publisher project; it fails for every player | Fix the parameters in a new quest |

##### issue_loyalty_points

Grants loyalty points of the program `loyalty_points_id`. `reason_quest_id`=true uses the quest ID as the reason instead of purpose. The event needs `gamer_id`.

**Parameters:** the fields of the node's `parameters` object.

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `amount` | number (double) | yes | Points to grant. Greater than: `0`. |
| `loyalty_points_id` | string | yes | ID of the loyalty points program. Min length: `1`. |
| `purpose` | string | yes | Reason recorded with the grant. Min length: `1`. |
| `reason_quest_id` | boolean | no | true sends the quest ID as the grant reason instead of purpose. |

**Example:**

```json
{
  "id": "bc326002-a9a6-5d88-aaee-ffda1fa0fb01",
  "name": "Add loyalty points",
  "type": "action",
  "subtype": "issue_loyalty_points",
  "parameters": {
    "purpose": "weekly_level_grinder",
    "loyalty_points_id": "your-loyalty-program-id",
    "amount": 100,
    "reason_quest_id": false
  }
}
```

**Set up first:** the loyalty programme (`loyalty_points_id`).

**Errors**: the codes this node can leave in the progress block's `last_error.code`:

| Error | Meaning | Fix |
| --- | --- | --- |
| `application_error` | No code of its own, for example the event has no `gamer_id` | Add `gamer_id` to `user_ids` |
| `invalid_reward_config` | The node's parameters are invalid; it fails for every player | Fix the parameters in a new quest |

##### issue_scoped_currency

Credits amount of a project's scoped currency sku, such as pixel, to the player's Currency Wallet, where it shows in Backpack. The event needs `xsolla_id`.

**Parameters:** the fields of the node's `parameters` object.

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `amount` | number (double) | yes | Amount to credit. Greater than: `0`. |
| `purpose` | string | yes | Reason recorded with the credit. Min length: `1`. |
| `sku` | string | yes | Scoped currency SKU in the project's catalog, e.g. pixel or `game_orbs`. Min length: `1`. |

**Example:**

```json
{
  "id": "141e62a6-8598-58f1-b493-9c3d881b6192",
  "name": "Grant 100 pixels",
  "type": "action",
  "subtype": "issue_scoped_currency",
  "parameters": {
    "purpose": "weekly_level_grinder",
    "sku": "pixel",
    "amount": 100
  }
}
```

**Set up first:** the scoped currency (its SKU, e.g. `pixel`) in your project's catalog. The node always credits your account's own project, whatever project the quest names.

**Limits**: one credit per quest run. A retried run sends the same request again and is credited once.

**Errors**: the codes this node can leave in the progress block's `last_error.code`:

| Error | Meaning | Fix |
| --- | --- | --- |
| `missing_xsolla_id` | The event has no `xsolla_id` and no `email` to find it from, so there is no wallet to credit | Add `xsolla_id` to `user_ids`, or send the player's `email` |
| `email_not_resolved` | The event had no `xsolla_id`, and its `email` belongs to no Xsolla account or is not a valid address | Send the player's `xsolla_id`, or the email of their Xsolla account |
| `xsolla_id_lookup_unavailable` | The Xsolla account could not be looked up from the `email` at the moment | Nothing; the node is retried. If it still fails, resend the event under a new `idempotency_key` |
| `scoped_currency_rejected` | The currency service refused the credit, most often because the SKU is not in the project's catalog | Add the SKU to the catalog, or fix `sku` in a new quest |
| `scoped_wallet_unauthorized` | The currency wallet refused our access; the node is retried | Contact your Xsolla account manager |
| `invalid_reward_config` | The node's parameters are invalid, or the quest has no project; it fails for every player | Fix the parameters or the quest's project in a new quest |

##### issue_virtual_currency

Delivers virtual currency packages by SKU to the player through DDH. The event needs `gamer_id`.

**Parameters:** the fields of the node's `parameters` object.

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | array of object | yes | Virtual currency packages to grant. Min items: `1`. |
| `items[].quantity` | integer (int64) | no | Zero or omitted defaults to 1. Number of SKU units: a 100-coin pack with quantity 2 grants 200 coins. Default: `1`. Minimum: `0`. Maximum: `100`. |
| `items[].sku` | string | yes | SKU of the virtual currency package. Min length: `1`. |
| `purpose` | string | yes | Reason recorded with the grant. Min length: `1`. |

**Example:**

```json
{
  "id": "b0149e41-549b-5052-8c34-6e18f46ec350",
  "name": "Grant a gold pack",
  "type": "action",
  "subtype": "issue_virtual_currency",
  "parameters": {
    "purpose": "weekly_level_grinder",
    "items": [
      {
        "sku": "gold_pack_100",
        "quantity": 1
      }
    ]
  }
}
```

**Set up first:** the virtual currency packages (SKUs) in the project's catalogue, and the project's [user validation webhook](https://developers.xsolla.com/webhooks/user-validation/user-validation) enabled.

**Limits**: `quantity` is 1 to 100 per package.

**Errors**: the codes this node can leave in the progress block's `last_error.code`:

| Error | Meaning | Fix |
| --- | --- | --- |
| `missing_gamer_id`, `ddh_webhook_disabled`, `ddh_user_rejected`, `ddh_request_rejected` | DDH could not deliver: no `gamer_id`, the project's user validation webhook is off, the game refused the player, or DDH refused the request | Check the event and the project's webhook settings |
| `invalid_reward_config` | The node's parameters are invalid, or the quest has no publisher project; it fails for every player | Fix the parameters in a new quest |

##### issue_web3_item

Mints a Web3 item (NFT) to the player, at most once per player and quest. `item_sku` is one SKU, a list of candidates, or empty to let Xsolla Web3 choose. The event needs `xsolla_id`.

**Parameters:** the fields of the node's `parameters` object.

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `item_sku` | one of: string, array of string, nullable | no | One SKU or a list of candidates; empty lets Xsolla Web3 choose. |
| `project` | string | no | Empty uses the configured minting project. Pattern: `^([A-Za-z0-9_-]{1,64})?$`. |
| `purpose` | string | yes | Reason recorded with the grant. Min length: `1`. |
| `quantity` | integer (int64) | no | Zero or omitted defaults to 1. Minimum: `0`. |

**Example:**

```json
{
  "id": "5a6cec16-b17d-57dd-aae9-4dd9c6efaa0f",
  "name": "Mint the badge",
  "type": "action",
  "subtype": "issue_web3_item",
  "parameters": {
    "purpose": "tutorial_badge",
    "item_sku": "tutorial_badge",
    "project": "654321",
    "quantity": 1
  }
}
```

**Set up first:** a SKU that Xsolla Web3 can see.

The item is minted as an NFT to the player's Xsolla wallet, so the event needs `xsolla_id`; guests have no wallet.

* **Which item**: `item_sku` names one SKU or a list of candidates, in `project` (empty: the default Web3 project).
* **How many**: `quantity`, 1 by default.
* **Once per player**: a player receives it at most once per quest, however often they complete it.
* **Only where Web3 rewards are available**: before paying, the Quest Platform checks that Web3 rewards are available to the player and to the merchant. If they are not, the node pays nothing and creates no wallet. It does not succeed, so the run stops there and an `on: "failed"` edge from the node runs, but it is not retried and sets no `last_error`. A legacy `issue_reward` of type `web3_item` is checked the same way.
* **Who can save it**: if Web3 rewards are not available to the caller or to the merchant, creating or updating a quest with this node is refused with `422` and `node is not permitted for this caller` on the node, and the node types list leaves it out. When that cannot be checked, nothing is saved: send the request again. Deleting the quest, or saving it without this node, always works. On the project routes, such a caller does not see a quest with this node at all: the list leaves it out, and reading or updating it answers `404`.

**Errors**: the codes this node can leave in the progress block's `last_error.code`:

| Error | Meaning | Fix |
| --- | --- | --- |
| `missing_xsolla_id` | The event has no `xsolla_id` and no `email` to find it from | Add `xsolla_id` to `user_ids`, or send the player's `email` |
| `email_not_resolved` | The event had no `xsolla_id`, and its `email` belongs to no Xsolla account or is not a valid address | Send the player's `xsolla_id`, or the email of their Xsolla account |
| `xsolla_id_lookup_unavailable` | The Xsolla account could not be looked up from the `email` at the moment | Nothing; the node is retried. If it still fails, resend the event under a new `idempotency_key` |
| `reward_check_unavailable` | Whether Web3 rewards are available to the player could not be checked at the moment; nothing was paid | Nothing; the node is retried. If it still fails, send the event again with the same `idempotency_key` |
| `web3_not_configured` | Web3 payouts are not enabled | Contact your Xsolla account manager |
| `web3_claim_failed` | Xsolla Web3 refused the payout; nothing was paid | Check the SKU and project |
| `web3_settlement_unavailable` | The payout could not be recorded safely at the moment, so nothing was sent; the node is retried | Nothing. If it still fails, resend the event under a new `idempotency_key` |
| `web3_payout_indeterminate`, `web3_empty_tx_hash`, `web3_settlement_indeterminate` | The outcome is unknown; it is not retried, so the player is not paid twice | Contact your Xsolla account manager with the quest ID and the event's `idempotency_key` |
| `invalid_reward_config` | The node's parameters are invalid; it fails for every player | Fix the parameters in a new quest |

**A player without an Xsolla wallet** is not paid and no error is recorded: the quest stays `in_progress` with no `last_error`.

##### issue_web3_token

Sends amount of the Web3 token `item_sku` to the player's wallet. The event needs `xsolla_id` and the publisher project.

**Parameters:** the fields of the node's `parameters` object.

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `amount` | number (double) | yes | Whole tokens to send. Greater than: `0`. Maximum: `10000`. |
| `item_sku` | string | yes | SKU of the token. The project and SKU pair must be configured for Xsolla Web3 token payouts. Min length: `1`. |
| `project` | string | no | Empty uses the configured minting project. Pattern: `^([A-Za-z0-9_-]{1,64})?$`. |
| `purpose` | string | yes | Reason recorded with the grant. Min length: `1`. |

**Example:**

```json
{
  "id": "0f308b55-df8b-50e3-bbc1-48bf548f9b0b",
  "name": "Send tokens",
  "type": "action",
  "subtype": "issue_web3_token",
  "parameters": {
    "purpose": "weekly_level_grinder",
    "item_sku": "your_token_sku",
    "amount": 5,
    "project": "654321"
  }
}
```

**Set up first:** the project and SKU pair, configured for token payouts by Xsolla.

The tokens go to the player's Xsolla wallet, so the event needs `xsolla_id`; guests have no wallet.

* **Which token**: `item_sku` in `project`, one of the pairs Xsolla has configured for token payouts. Any other pair fails; ask your Xsolla account manager which pairs are available, or to add one.
* **How many**: `amount` in whole tokens, more than 0 and at most 10,000.
* **Every completion pays**, unlike [issue_web3_item](https://developers.xsolla.com/api/quests/node-issue-web3-item).
* **Never paid twice**: when the outcome of a payout is unknown, it is not retried, so the player may wait while Xsolla checks it.
* **Only where Web3 rewards are available**: before paying, the Quest Platform checks that Web3 rewards are available to the player and to the merchant. If they are not, the node pays nothing and creates no wallet. It does not succeed, so the run stops there and an `on: "failed"` edge from the node runs, but it is not retried and sets no `last_error`. A legacy `issue_reward` of type `web3_token` is checked the same way.
* **Who can save it**: if Web3 rewards are not available to the caller or to the merchant, creating or updating a quest with this node is refused with `422` and `node is not permitted for this caller` on the node, and the node types list leaves it out. When that cannot be checked, nothing is saved: send the request again. Deleting the quest, or saving it without this node, always works. On the project routes, such a caller does not see a quest with this node at all: the list leaves it out, and reading or updating it answers `404`.

**Errors**: the codes this node can leave in the progress block's `last_error.code`:

| Error | Meaning | Fix |
| --- | --- | --- |
| `missing_xsolla_id` | The event has no `xsolla_id` and no `email` to find it from | Add `xsolla_id` to `user_ids`, or send the player's `email` |
| `email_not_resolved` | The event had no `xsolla_id`, and its `email` belongs to no Xsolla account or is not a valid address | Send the player's `xsolla_id`, or the email of their Xsolla account |
| `xsolla_id_lookup_unavailable` | The Xsolla account could not be looked up from the `email` at the moment | Nothing; the node is retried. If it still fails, resend the event under a new `idempotency_key` |
| `reward_check_unavailable` | Whether Web3 rewards are available to the player could not be checked at the moment; nothing was paid | Nothing; the node is retried. If it still fails, send the event again with the same `idempotency_key` |
| `web3_token_not_configured` | The project and SKU pair is not configured | Use a configured pair, or ask your Xsolla account manager to add it |
| `web3_token_claim_failed` | Xsolla Web3 refused the payout; nothing was paid | Check the SKU and project |
| `web3_settlement_unavailable` | The payout could not be recorded safely at the moment, so nothing was sent; the node is retried | Nothing. If it still fails, resend the event under a new `idempotency_key` |
| `web3_payout_indeterminate`, `web3_token_empty_tx_hash`, `web3_settlement_indeterminate` | The outcome is unknown; it is not retried, so the player is not paid twice | Contact your Xsolla account manager with the quest ID and the event's `idempotency_key` |
| `invalid_reward_config` | The node's parameters are invalid; it fails for every player | Fix the parameters in a new quest |
| `web3_token_invalid_body` | The node's parameters cannot be read; it fails for every player | Fix the parameters in a new quest |

**A player without an Xsolla wallet** is not paid and no error is recorded: the quest stays `in_progress` with no `last_error`.

##### crm_send_email

Emails the event's player when the event carries an email, otherwise every player in the CRM segment `crm_segment`. Not idempotent: a retry can send the email twice.

**Parameters:** the fields of the node's `parameters` object.

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `content` | string | yes | Email body. Min length: `1`. |
| `crm_segment` | string | yes | ID of the User CRM segment to email. Min length: `1`. |
| `game_title` | string | yes | Game name shown in the email. Min length: `1`. |
| `subject` | string | yes | Email subject line. Min length: `1`. |

**Example:**

```json
{
  "id": "bad824dd-5213-58e4-8bdd-a6933b95cdc9",
  "name": "Email the VIP segment",
  "type": "action",
  "subtype": "crm_send_email",
  "parameters": {
    "crm_segment": "4242",
    "game_title": "Your Game",
    "subject": "Your weekly VIP crate is here",
    "content": "Log in to claim this week's crate."
  }
}
```

**Set up first:** the CRM segment you want to email, and its id in `crm_segment`.

**Which merchant:** the segment is read from your own merchant.

**Not idempotent.** When the event has no email, every accepted call emails the whole segment again. If the answer is lost in transit the attempt is repeated, so the same email can be sent twice.

**Limits**: one send per run of the node. With a [crm_segment_match](https://developers.xsolla.com/api/quests/node-crm-segment-match) condition before it, the node runs once for each player of the segment and emails only that player, and a player of the segment without an email fails rather than mailing everyone.

**Errors**: the codes this node can leave in the progress block's `last_error.code`:

| Error | Meaning | Fix |
| --- | --- | --- |
| `invalid_crm_config` | The node's parameters are invalid | Fix the parameters in a new quest |
| `crm_not_configured` | Email sending is not available for your project | Contact your Xsolla account manager |
| `crm_send_email_rejected` | CRM refused the request, e.g. an unknown segment | Check `crm_segment` |
| `crm_rate_limited` | Too many sends; the node is retried automatically | None |
| `crm_send_email_unconfirmed` | User CRM accepted the send, but its answer could not be read; it is not retried, so the segment is not emailed twice | Check in User CRM whether the email went out |

## Connections

***Connections decide which node runs after which.*** Without them, `nodes` is only a list; `connections` wires it into the graph a run follows.

#### How connections are written

`connections` is an object. Each key is the ID of a node, and its value is the list of edges leaving that node; each edge names the next node in `nodeId`. The chest quest has two edges, from the trigger to the condition and from the condition to the reward:

```json
"connections": {
  "0f2c6d1e-3b4a-4c5d-8e9f-101112131415": [
    {
      "nodeId": "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d"
    }
  ],
  "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d": [
    {
      "nodeId": "2b3c4d5e-6f7a-4b8c-9d0e-1f2a3b4c5d6e"
    }
  ]
}
```

| From | To |
| --- | --- |
| Level completed (trigger) | Three levels this week (condition) |
| Three levels this week (condition) | Give a chest (action) |

An edge can also carry `on`, to be followed only after a given outcome, or `join: true`, to mark where a loop ends; both are described below.

#### Rules

**Fan-out**

A node can have several outgoing edges; each target is followed.

**No cycles**

The graph must have no cycles, and every ID, key or target, must be a node of the same quest.

**Ends**

A node with no outgoing edges ends its branch, so actions usually have no entry.

#### Outcome edges

An edge with `on` is followed only when its source node ends with that outcome. Edges without `on` are always followed.

| `on` | Followed when |
| --- | --- |
| `failed` | The source node did not succeed: an action or collection failed after its retries, or a condition was not met or could not be evaluated. On a condition, a `failed` edge therefore runs for every event that does not pass it. |
| `limit_reached` | An activation limit refused the run. Only on edges leaving a trigger. |

> **failed and limit_reached are being replaced**
>
> Both still work, but they are planned to move out of connections into platform events. Prefer not to build new quests on them.

#### Loops

A collection node ([crm_segment_match](https://developers.xsolla.com/api/quests/node-crm-segment-match) reading a CRM segment) runs the nodes after it once per item. An edge with `join: true` marks where the loop ends: its target runs once, after every item finished. A `join` edge is only valid downstream of a collection node.

#### Order and failures

Two rules decide what happens when a node fails:

1. **Edges leaving a node are followed in the order they are listed.**
2. **The first node that fails stops the run.** Nodes after it, and sibling edges not reached yet, do not run, except the failed node's `on: "failed"` edges.

So:

* **Reward before email.** `trigger → reward → email` tells the player only about a reward that succeeded. Wiring the email to the trigger tells them even when the reward fails.
* **Put the reward that matters most first.** With `trigger → [mint, Backpack]` the mint runs first and a Backpack failure cannot stop it; listed the other way round, it can. Chaining `mint → Backpack` behaves the same as listing the mint first.
* **Email the player about a failure** with an `on: "failed"` edge from the reward; it runs once the reward has used up its retries.
* **A failed run resumes.** Nodes that succeeded are recorded as they finish, so resending the event with the **same** `idempotency_key` after a temporary failure continues from the failed node and does not run the earlier ones again.

## Activation limits

***Activation limits cap how many times a quest is **completed**, by each player, by all players together, or both.*** A run that does not complete, for example because a condition is not met yet, uses up nothing.

#### Fields

`activation_limits` is a list; each limit has:

| Field | Values |
| --- | --- |
| `type` | `per_user`: completions by one player. `global`: completions by all players together. |
| `count` | Completions allowed in the window, at least 1. |
| `time_window.duration_unit` | Optional: `day`, `week` (starting Monday) or `month`, calendar windows in UTC. Omitted: the limit covers the whole life of the quest. |

**"Per user" means per player identity.** The platform resolves the event's identifiers to one player, preferring `xsolla_id`, then `gamer_id`, `guest_id` and `email`. Send the same identifier for the same person every time: events that name one person with different identifiers can be counted as different players.

> **Use at most one limit of each type**
>
> With two `per_user` limits (for example 1 a day and 5 a month) only the last one in the list is applied, and the quest is not rejected. To combine a daily and a monthly cap, use one `per_user` and one `global`, or two quests.

#### Worked examples

[**Activation limits over a week**](https://developers.xsolla.com/api/quests/examples-limits-week) and [**Per-player and global limits together**](https://developers.xsolla.com/api/quests/examples-limits-global), on the Examples page, follow both kinds of limit event by event.

#### Changing limits and seeing rejections

* **Changing limits** on a quest that players already have progress on is a structural edit and is refused with `409`. Create a new quest instead.
* **Seeing refused runs**: the event is still accepted, and nothing is stored about a run a limit refused, so no API lists it. The player's progress shows where they stand, but only on public quests that are running: a game client reads it with the player's token through [List quests with the caller's progress](https://developers.xsolla.com/api/quests/player-progress/list-me-quests), including `completion_count` and, when present, `completions_in_window`.
  There is no progress read for a private quest.

## Public quests guide

A quest is private by default: only your own backend sees it. ***A public quest can be shown to players***, in your game or on a web page, together with each player's own progress.

#### Make a quest public

Set `is_public: true` when you create or update the quest. It is off by default, and leaving it out of an update keeps the stored value.

Making a quest public, or private again, does not count as a structural change, so you can do it on a quest players already have progress on.

> **Only running quests are shown**
>
> A public quest is listed only while its `status` is `active` and the current time is between `start_date` and `end_date`.

#### Where players see it

**Without signing in**

The public quest list needs no credential, for example for a landing page. Responses are cached for 60 seconds, except where a running quest with a Web3 reward is involved: those answers depend on who asks, so they are not cached.
Call [List public quests](https://developers.xsolla.com/api/quests/public-quest-list/list-public-quests).

**With the player's progress**

A game client signed in as the player lists the same quests, each with that player's own progress.
Call [List quests with the caller's progress](https://developers.xsolla.com/api/quests/player-progress/list-me-quests).

**Only some quests.** To show a few chosen quests, for example the cards of one page, repeat `ids` in the query of [List public quests](https://developers.xsolla.com/api/quests/public-quest-list/list-public-quests) or [List quests with the caller's progress](https://developers.xsolla.com/api/quests/player-progress/list-me-quests), up to 24 times. The quests among them that the list would show come back in one page, newest first, and `page` and `limit` are ignored. An id that is unknown, private, inactive or outside its dates is left out, never an error. An id that is not a UUID, or more than 24 ids, returns 422.

#### Quests with Web3 rewards

Web3 rewards are not available to every player. A public quest with a Web3 reward (an [issue_web3_item](https://developers.xsolla.com/api/quests/node-issue-web3-item) or [issue_web3_token](https://developers.xsolla.com/api/quests/node-issue-web3-token) node, or a legacy `issue_reward` of either Web3 type) is shown only to players Web3 rewards are available to, and only while they are available to the merchant whose quest it is. For anyone else it is left out, with or without the player's token:

* Lists leave it out, and their `total` and pages count only the quests shown.
* Getting it returns the same `404` as an unknown quest.
* Nothing in the answer says that a quest was left out.

Quests without a Web3 reward are shown to everyone. A player who sees the quest is checked again when the reward is paid; see [issue_web3_item](https://developers.xsolla.com/api/quests/node-issue-web3-item).

#### Choose what players see

Without anything else, a public quest shows its `name`, its `description` (when set) and its rewards. To decide yourself, add a `public_view`.

**Structure.** `public_view` is a JSON object. You choose its keys, and players get the same keys back, with every reference replaced by its value. Each value is one of:

| Value | Written as | Players get |
| --- | --- | --- |
| **Text** | `"Weekly"` | The text as written |
| **Number** | `3` | The number |
| **Yes or no** | `true` | The value |
| **Reference** | `{"$ref": "quest.end_date"}` | The value it points to, from the tables below |
| **Group** | An object of these values | The group, with its values resolved |

Arrays and `null` are not allowed. This view, from [**Public chest quest with a view**](https://developers.xsolla.com/api/quests/examples-public-quest), names the quest, its description, end date and reward, and adds a fixed badge:

```json
"public_view": {
  "title": {
    "$ref": "quest.name"
  },
  "about": {
    "$ref": "quest.description"
  },
  "ends": {
    "$ref": "quest.end_date"
  },
  "reward": {
    "$ref": "reward.2b3c4d5e-6f7a-4b8c-9d0e-1f2a3b4c5d6e.items"
  },
  "badge": "Weekly"
}
```

**References** point to the quest or to one of its reward nodes:

| Reference | Shows |
| --- | --- |
| `{"$ref": "quest.name"}` | The quest's name. Also `quest.id`, `quest.description`, `quest.start_date`, `quest.end_date` |
| `{"$ref": "reward.<node id>.<field>"}` | A field of a reward node, from the list below |

| Reward node | Fields you can show |
| --- | --- |
| **Any reward node** | `type`, the kind of reward (see below) |
| **Items** ([issue_game_item](https://developers.xsolla.com/api/quests/node-issue-game-item), [issue_catalog_item](https://developers.xsolla.com/api/quests/node-issue-catalog-item)) | `items`, each with `quantity`, `name`, `image_url` |
| **Virtual currency** ([issue_virtual_currency](https://developers.xsolla.com/api/quests/node-issue-virtual-currency)) | `items` |
| **Web3 item** ([issue_web3_item](https://developers.xsolla.com/api/quests/node-issue-web3-item)) | `quantity`, `name`, `description`, `image_url` |
| **Points, tokens and scoped currency** ([issue_loyalty_points](https://developers.xsolla.com/api/quests/node-issue-loyalty-points), [issue_web3_token](https://developers.xsolla.com/api/quests/node-issue-web3-token), [issue_scoped_currency](https://developers.xsolla.com/api/quests/node-issue-scoped-currency)) | `amount` |

`type` reads `game_item` for [issue_game_item](https://developers.xsolla.com/api/quests/node-issue-game-item), `inventory_item` for [issue_catalog_item](https://developers.xsolla.com/api/quests/node-issue-catalog-item), and the node's name without `issue_` for the others, for example `loyalty_points`.

> **metadata is never shown**
>
> `metadata` stays with your own backend: the public and player routes never return it. Put everything players see in `public_view`.

> **Rules for a public_view**
>
> At most 8 KB, 3 levels deep and 50 values. Keys start with a lower-case letter, then lower-case letters, digits or `_`, at most 40 characters. Text is at most 500 characters; links must be `https://` and at most 2,048 characters. Numbers are plain, without exponents. A reference is an object with only the `$ref` key. A reference that no longer resolves, for example to a reward node you removed, is left out and the quest is still shown.

The view is not structural either: you can change it on a live quest. Sending `{}` clears it, and leaving it out of an update keeps the stored one.

#### Objectives

***Objectives are the steps a player sees on the way to completing the quest.*** Each one follows a node, or one check inside a condition, and the progress read reports how far that player is. They only describe progress: they never decide whether the quest runs or pays.

**Structure.** `objectives` is a list, shown in its order. Each step has:

| Field | Required | What to put |
| --- | --- | --- |
| **key** | yes | A stable name for the step, unique in the quest, so your app can find it: lower-case letters, digits and `_`, up to 64 characters |
| **label** | yes | The text players see, 1 to 128 characters |
| **unit** | no | The word shown after a counter, such as "levels", up to 32 characters |
| **ref** | yes | What the step follows; see below |

**What a step follows.** `ref` names a node of the quest by its `id`, and optionally one check inside it:

| `ref` | Follows | Shown as |
| --- | --- | --- |
| `{"node_id": …}` | Whether that condition or action has succeeded for the player | A check |
| `{"node_id": …, "leaf_index": n}` | One comparison inside a [custom_attributes_check](https://developers.xsolla.com/api/quests/node-custom-attributes-check) node | A counter when it reads "reach at least N", otherwise a check |

`leaf_index` counts the node's comparisons in the order they are written, nested groups included, starting at 0. A node with a single comparison has only `leaf_index` 0. Triggers cannot be objectives.

For the chest quest, one counter for the levels and one step for the chest:

```json
"objectives": [
  {
    "key": "levels",
    "label": "Finish 3 levels this week",
    "unit": "levels",
    "ref": {
      "node_id": "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d",
      "leaf_index": 0
    }
  },
  {
    "key": "chest",
    "label": "Get your chest",
    "ref": {
      "node_id": "2b3c4d5e-6f7a-4b8c-9d0e-1f2a3b4c5d6e"
    }
  }
]
```

**Counter or check.** A comparison becomes a **counter** when it compares an event count with a fixed number, as "at least" (`gte`) or "more than" (`gt`); written the other way round, `lte` and `lt` work too. Its target is that number, plus 1 for "more than", so a player never sees "3/3, not done". Anything else is a **check**.

**What players get.** The progress read returns each step with its `key`, `label` and `kind`, and a `status`:

| `status` | When |
| --- | --- |
| **pending** | The step has not been evaluated for this player yet |
| **in_progress** | Evaluated, not reached yet |
| **completed** | The node succeeded, or the comparison matched |

A counter also carries `current` (never capped at the target), `target`, `unit`, and for an event count its `window` (`day`, `week` or `month`). A **pending** counter, including every counter of a quest the player has not started, reads `current` 0 and its `target`, so you can show "0/3" before anything happens. An event count covers the whole window, so events the player sent in it before the quest started count at the first evaluation and can move a counter straight past 0. When a new window starts, the counter reads 0 again unless the step is already completed.

**Without objectives**, the progress read shows one check per reward node, with the node's `id` as its `key` and the reward type.

> **Rules for objectives**
>
> At most 20 per quest, each `key` used once. `ref` must name a node of this quest, not a trigger, and `leaf_index` is allowed only on a [custom_attributes_check](https://developers.xsolla.com/api/quests/node-custom-attributes-check) node, within its number of comparisons.
> Objectives are not structural, so you can add, reorder or relabel them on a live quest: leave them out of an update to keep them, and send `[]` to clear them. An update that changes the nodes but leaves the objectives out checks the stored ones against the new nodes; if a step no longer fits, the update is refused until you resend or clear them.

> **Tip: either-or steps**
>
> A comparison inside an `or` group reports its own state. To show "either this or that" as one step, point the step at the whole node instead.

## Examples

***Whole quests, events, conditions and walkthroughs, each checked against the API and linked to the page that explains it.***
### Example quests

Whole quests, each accepted by the API as shown.

#### Chest for three levels a week

A player who finishes three levels in a week receives a chest in the game, at most once a week, and the quest pays out at most 10,000 times. Before you send it, set `start_date` to now or later and `end_date` after it: an active quest can't start more than a day in the past, so the dates shown here are refused once they are a day old. Apart from the dates, this exact quest is checked automatically against the API.

**Graph:** Level completed → Three levels this week → Give a chest

```json
{
  "name": "Weekly level grinder",
  "description": "Reward players who finish three levels in a week with a chest in the game.",
  "type": "liveops",
  "publisher_id": "123456",
  "project_id": "654321",
  "status": "active",
  "created_by": "liveops-team",
  "start_date": "2026-11-02T00:00:00Z",
  "end_date": "2026-11-30T23:59:59Z",
  "activation_limits": [
    {
      "type": "per_user",
      "count": 1,
      "time_window": {
        "duration_unit": "week"
      }
    },
    {
      "type": "global",
      "count": 10000
    }
  ],
  "nodes": [
    {
      "id": "0f2c6d1e-3b4a-4c5d-8e9f-101112131415",
      "name": "Level completed",
      "type": "trigger",
      "subtype": "dynamic_event",
      "parameters": {
        "event_name": "level_completed"
      }
    },
    {
      "id": "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d",
      "name": "Three levels this week",
      "type": "condition",
      "subtype": "custom_attributes_check",
      "parameters": {
        "type": "comparison",
        "left": {
          "type": "event",
          "value": "level_completed",
          "time_window": {
            "duration_unit": "week"
          }
        },
        "operator": {
          "type": "numeric",
          "operation": "gte"
        },
        "right": {
          "type": "value",
          "value": 3
        }
      }
    },
    {
      "id": "2b3c4d5e-6f7a-4b8c-9d0e-1f2a3b4c5d6e",
      "name": "Give a chest",
      "type": "action",
      "subtype": "issue_game_item",
      "parameters": {
        "purpose": "weekly_level_grinder",
        "items": [
          {
            "sku": "weekly_chest",
            "quantity": 1
          }
        ]
      }
    }
  ],
  "connections": {
    "0f2c6d1e-3b4a-4c5d-8e9f-101112131415": [
      {
        "nodeId": "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d"
      }
    ],
    "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d": [
      {
        "nodeId": "2b3c4d5e-6f7a-4b8c-9d0e-1f2a3b4c5d6e"
      }
    ]
  }
}
```

To create it, follow the [**Publisher guide**](https://developers.xsolla.com/api/quests/publisher-guide).

#### Public chest quest with a view

The chest quest with `is_public: true` and a `public_view` that shows its name, description, end date and the chest. [**Public quests guide**](https://developers.xsolla.com/api/quests/public-quests-guide) explains each part.

**Graph:** Level completed → Three levels this week → Give a chest

```json
{
  "name": "Weekly level grinder, public",
  "description": "Reward players who finish three levels in a week with a chest in the game.",
  "type": "liveops",
  "publisher_id": "123456",
  "project_id": "654321",
  "status": "active",
  "is_public": true,
  "created_by": "liveops-team",
  "start_date": "2026-11-02T00:00:00Z",
  "end_date": "2026-11-30T23:59:59Z",
  "activation_limits": [
    {
      "type": "per_user",
      "count": 1,
      "time_window": {
        "duration_unit": "week"
      }
    },
    {
      "type": "global",
      "count": 10000
    }
  ],
  "nodes": [
    {
      "id": "0f2c6d1e-3b4a-4c5d-8e9f-101112131415",
      "name": "Level completed",
      "type": "trigger",
      "subtype": "dynamic_event",
      "parameters": {
        "event_name": "level_completed"
      }
    },
    {
      "id": "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d",
      "name": "Three levels this week",
      "type": "condition",
      "subtype": "custom_attributes_check",
      "parameters": {
        "type": "comparison",
        "left": {
          "type": "event",
          "value": "level_completed",
          "time_window": {
            "duration_unit": "week"
          }
        },
        "operator": {
          "type": "numeric",
          "operation": "gte"
        },
        "right": {
          "type": "value",
          "value": 3
        }
      }
    },
    {
      "id": "2b3c4d5e-6f7a-4b8c-9d0e-1f2a3b4c5d6e",
      "name": "Give a chest",
      "type": "action",
      "subtype": "issue_game_item",
      "parameters": {
        "purpose": "weekly_level_grinder",
        "items": [
          {
            "sku": "weekly_chest",
            "quantity": 1
          }
        ]
      }
    }
  ],
  "connections": {
    "0f2c6d1e-3b4a-4c5d-8e9f-101112131415": [
      {
        "nodeId": "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d"
      }
    ],
    "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d": [
      {
        "nodeId": "2b3c4d5e-6f7a-4b8c-9d0e-1f2a3b4c5d6e"
      }
    ]
  },
  "public_view": {
    "title": {
      "$ref": "quest.name"
    },
    "about": {
      "$ref": "quest.description"
    },
    "ends": {
      "$ref": "quest.end_date"
    },
    "reward": {
      "$ref": "reward.2b3c4d5e-6f7a-4b8c-9d0e-1f2a3b4c5d6e.items"
    },
    "badge": "Weekly"
  }
}
```

#### Chest quest with objectives

The chest quest with two `objectives`: a counter for the levels and a check for the chest. [**Objectives**](https://developers.xsolla.com/api/quests/public-quests-guide#public-objectives) explains each field.

**Graph:** Level completed → Three levels this week → Give a chest

```json
{
  "name": "Weekly level grinder, with objectives",
  "description": "Reward players who finish three levels in a week with a chest in the game.",
  "type": "liveops",
  "publisher_id": "123456",
  "project_id": "654321",
  "status": "active",
  "created_by": "liveops-team",
  "start_date": "2026-11-02T00:00:00Z",
  "end_date": "2026-11-30T23:59:59Z",
  "activation_limits": [
    {
      "type": "per_user",
      "count": 1,
      "time_window": {
        "duration_unit": "week"
      }
    },
    {
      "type": "global",
      "count": 10000
    }
  ],
  "nodes": [
    {
      "id": "0f2c6d1e-3b4a-4c5d-8e9f-101112131415",
      "name": "Level completed",
      "type": "trigger",
      "subtype": "dynamic_event",
      "parameters": {
        "event_name": "level_completed"
      }
    },
    {
      "id": "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d",
      "name": "Three levels this week",
      "type": "condition",
      "subtype": "custom_attributes_check",
      "parameters": {
        "type": "comparison",
        "left": {
          "type": "event",
          "value": "level_completed",
          "time_window": {
            "duration_unit": "week"
          }
        },
        "operator": {
          "type": "numeric",
          "operation": "gte"
        },
        "right": {
          "type": "value",
          "value": 3
        }
      }
    },
    {
      "id": "2b3c4d5e-6f7a-4b8c-9d0e-1f2a3b4c5d6e",
      "name": "Give a chest",
      "type": "action",
      "subtype": "issue_game_item",
      "parameters": {
        "purpose": "weekly_level_grinder",
        "items": [
          {
            "sku": "weekly_chest",
            "quantity": 1
          }
        ]
      }
    }
  ],
  "connections": {
    "0f2c6d1e-3b4a-4c5d-8e9f-101112131415": [
      {
        "nodeId": "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d"
      }
    ],
    "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d": [
      {
        "nodeId": "2b3c4d5e-6f7a-4b8c-9d0e-1f2a3b4c5d6e"
      }
    ]
  },
  "objectives": [
    {
      "key": "levels",
      "label": "Finish 3 levels this week",
      "unit": "levels",
      "ref": {
        "node_id": "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d",
        "leaf_index": 0
      }
    },
    {
      "key": "chest",
      "label": "Get your chest",
      "ref": {
        "node_id": "2b3c4d5e-6f7a-4b8c-9d0e-1f2a3b4c5d6e"
      }
    }
  ]
}
```

#### Monday crate for VIP players

Every Monday at 09:00 UTC this quest gives each player in a CRM segment a crate in their Backpack:

**Graph:** Every Monday at 09:00 → Players in the VIP segment → Give a crate

```json
{
  "name": "Monday reward for VIP players",
  "description": "Every Monday at 09:00 UTC, gives each player in the VIP segment a crate in their Backpack.",
  "type": "liveops",
  "publisher_id": "123456",
  "project_id": "654321",
  "status": "active",
  "created_by": "liveops-team",
  "start_date": "2026-11-02T00:00:00Z",
  "end_date": "2026-12-31T23:59:59Z",
  "nodes": [
    {
      "id": "6c3d4e5f-1111-4a7b-8c9d-0e1f2a3b4c5d",
      "name": "Every Monday at 09:00",
      "type": "trigger",
      "subtype": "scheduled_event",
      "parameters": {
        "event_name": "weekly_vip_reward",
        "cron": "0 9 * * 1"
      }
    },
    {
      "id": "6c3d4e5f-2222-4a7b-8c9d-0e1f2a3b4c5d",
      "name": "Players in the VIP segment",
      "type": "condition",
      "subtype": "crm_segment_match",
      "parameters": {
        "crm_segment_id": 4242
      }
    },
    {
      "id": "6c3d4e5f-3333-4a7b-8c9d-0e1f2a3b4c5d",
      "name": "Give a crate",
      "type": "action",
      "subtype": "issue_catalog_item",
      "parameters": {
        "purpose": "weekly_vip_reward",
        "items": [
          {
            "sku": "vip_crate"
          }
        ]
      }
    }
  ],
  "connections": {
    "6c3d4e5f-1111-4a7b-8c9d-0e1f2a3b4c5d": [
      {
        "nodeId": "6c3d4e5f-2222-4a7b-8c9d-0e1f2a3b4c5d"
      }
    ],
    "6c3d4e5f-2222-4a7b-8c9d-0e1f2a3b4c5d": [
      {
        "nodeId": "6c3d4e5f-3333-4a7b-8c9d-0e1f2a3b4c5d"
      }
    ]
  }
}
```

### Example events

#### Level completed event from a publisher

A player finished level 12, reported by a publisher's backend to its project route. The body has no `publisher` block, since the merchant and project come from the path. The [**Publisher guide**](https://developers.xsolla.com/api/quests/publisher-guide) explains how to send it.

```json
{
  "idempotency_key": "6f1c2a3b-4d5e-4f60-8a7b-9c0d1e2f3a4b",
  "name": "level_completed",
  "scope": "within_project",
  "user_ids": [
    {
      "identifier_type": "gamer_id",
      "value": "player-42"
    },
    {
      "identifier_type": "xsolla_id",
      "value": "2b0f5c1e-7a3d-4e9b-8c6f-1d2e3f4a5b6c"
    }
  ],
  "client_timestamp": "2026-11-02T10:15:00Z",
  "properties": {
    "level": "12"
  }
}
```

#### Level completed event from a game client

The same occurrence sent by the game client for its signed-in player: only `idempotency_key`, `name`, `client_timestamp` and `properties`, because the player comes from the token and the merchant and project from the path. The [**Publisher events guide**](https://developers.xsolla.com/api/quests/publisher-events-guide) compares it with the backend event.

```json
{
  "idempotency_key": "7a2d3b4c-5e6f-4a71-8b9c-0d1e2f3a4b5c",
  "name": "level_completed",
  "client_timestamp": "2026-11-02T10:15:00Z",
  "properties": {
    "level": "12"
  }
}
```

### Example conditions

Parameters of a [custom_attributes_check](https://developers.xsolla.com/api/quests/node-custom-attributes-check) node, each checked automatically against the API.

#### Every third purchase

`mod` passes on the 3rd, 6th, 9th… `purchase_completed` event of the month, so the reward repeats:

```json
{
  "type": "comparison",
  "left": {
    "type": "event",
    "value": "purchase_completed",
    "time_window": {
      "duration_unit": "month"
    }
  },
  "operator": {
    "type": "numeric",
    "operation": "mod"
  },
  "right": {
    "type": "value",
    "value": 3
  }
}
```

### Walkthroughs

How a quest behaves, event by event.

#### Activation limits over a week

The chest quest from the [**Quest guide**](https://developers.xsolla.com/api/quests/quest-guide): three levels in a week, `per_user` 1 a week and `global` 10,000. One player sends `level_completed` events through two weeks:

| Event | When | Player's completions this week | Result |
| --- | --- | --- | --- |
| 1st `level_completed` | Monday | 0 | Limit has room; condition counts 1 level, not met. Nothing used. |
| 2nd | Tuesday | 0 | Condition counts 2, not met. |
| 3rd | Wednesday | 0 → 1 | Condition met; chest given. Global: 1 of 10,000. |
| 4th | Thursday | 1 | Refused by the `per_user` limit (1 of 1 this week); nothing is stored. The condition is not checked. |
| 5th | next Monday | 0 | New window: limit has room again; the condition starts counting this week's levels. |

#### Per-player and global limits together

A quest that completes on every event, with `per_user` 2 and `global` 5 and no time windows. Three players send events:

| Event | Player | Player's completions | Global completions | Result |
| --- | --- | --- | --- | --- |
| 1 | A | 0 → 1 | 0 → 1 | Completed |
| 2 | A | 1 → 2 | 1 → 2 | Completed |
| 3 | A | 2 | 2 | Rejected by `per_user`; the global count is untouched |
| 4 | B | 0 → 1 | 2 → 3 | Completed |
| 5 | B | 1 → 2 | 3 → 4 | Completed |
| 6 | C | 0 → 1 | 4 → 5 | Completed |
| 7 | C | 1 | 5 | Refused by the `global` limit (5 of 5); nothing is stored |

Read [**Activation limits**](https://developers.xsolla.com/api/quests/activation-limits) for the rules behind both.

## Publisher guide

How a publisher connects a project to the Quest Platform: onboard it, create a quest, send events and show quests to players. A publisher is anyone with an Xsolla merchant and project, Xsolla's own games included. You need nothing from the Quest Platform team: onboarding is one call you make yourself.

#### The publisher path

You connect your project yourself, once: sign in to Publisher Account, or use an API key of your merchant (a *publisher key*), and onboard the project. Onboarding registers the project with the Quest Platform and gives you the access your role in the merchant allows.

After that you use only your own Xsolla IDs: every project and quest operation names your project by the merchant ID and project ID shown in Publisher Account. The four steps:

[**1. Onboard your project**](https://developers.xsolla.com/api/quests/publisher-guide#publisher-onboard)

Once per project, with [Onboard project](https://developers.xsolla.com/api/quests/publisher-api/onboard-project).

[**2. Create a quest**](https://developers.xsolla.com/api/quests/publisher-guide#publisher-create)

Send the quest with [Create a new quest (project scope)](https://developers.xsolla.com/api/quests/publisher-api/create-quest-in-project).

[**3. Send events**](https://developers.xsolla.com/api/quests/publisher-guide#publisher-events)

From your backend with [Send a publisher event](https://developers.xsolla.com/api/quests/publisher-events/publisher-events); game clients can send their own.

[**4. Show quests to players**](https://developers.xsolla.com/api/quests/publisher-guide#publisher-players)

The game client [lists quests with the player's progress](https://developers.xsolla.com/api/quests/player-progress/list-me-quests).

#### Before you start

* **Your merchant ID and project ID**, from Publisher Account.
* **For the chest quest's reward** ([issue_game_item](https://developers.xsolla.com/api/quests/node-issue-game-item)): the chest's SKU in your project's catalogue, and webhooks turned on in Publisher Account → **Project settings > Webhooks**, with your server answering the user validation webhook for your players and granting the item when it receives the order paid webhook. Without them the reward fails with `ddh_webhook_disabled` or `ddh_user_rejected`. [issue_game_item](https://developers.xsolla.com/api/quests/node-issue-game-item) lists every requirement.
* **One credential**, sent on every request:

| Credential | Header | Use it for |
| --- | --- | --- |
| Publisher Account token | `Authorization: Bearer <token>` | A person signed in to Publisher Account. What they may do follows their role in the merchant. |
| Publisher key | `Authorization: Basic base64(merchant_id:api_key)` | Your backend. An Xsolla API key of the merchant. |

**Getting a publisher key.** In [Publisher Account](https://publisher.xsolla.com/), open **Company settings > API keys** for a key of the whole merchant, or **Project settings > API keys** for a key of one project, and create a key. It is shown only once, so store it right away. [API keys](https://developers.xsolla.com/api/getting-started/#api_keys_overview) explains the two kinds.

Keep publisher keys on your servers; never ship them in a game client. [**Authentication**](https://developers.xsolla.com/api/quests/authentication) lists which operations accept which credential.

The host is `https://quests-platform.xsolla.com`.

#### 1. Onboard your project

Onboarding tells the Quest Platform about your project and gives you access to it. Call [Onboard project](https://developers.xsolla.com/api/quests/publisher-api/onboard-project) once per project, with your `merchant_name` and `project_name` in the body.

It creates whatever does not exist yet: your merchant, the project, and access to it. The names are used only for records this call creates. Calling it again returns the project and does not change access you already have.

What you can do afterwards depends on how you called it:

| Called with | You get |
| --- | --- |
| A Publisher Account token, as the merchant owner or a member of the whole merchant | Permission to manage quests on every onboarded project of the merchant |
| A Publisher Account token, as a member of some projects only | Permission to manage quests on this project |
| A publisher key | The merchant's publisher keys can manage quests on every onboarded project of the merchant |

Each Publisher Account user gets their own access by calling it with their own token, including on a project that a colleague or a publisher key already onboarded. A later call can add access, for example the whole merchant after your role widened, but never removes or lowers it. If the call answers `404`, the token's person is not a member of the merchant, the project is not listed for them, or the key belongs to another merchant; `401` means Xsolla rejected the key.

#### 2. Create a quest

Send the quest with [Create a new quest (project scope)](https://developers.xsolla.com/api/quests/publisher-api/create-quest-in-project). [**Chest for three levels a week**](https://developers.xsolla.com/api/quests/examples-chest-quest) on the Examples page is a quest you can start from (set its `start_date` and `end_date` to your own dates first); the [**Quest guide**](https://developers.xsolla.com/api/quests/quest-guide) explains every part.

The quest's `publisher_id` and `project_id` are taken from the path. Not every node is open to publishers: [**Quest nodes**](https://developers.xsolla.com/api/quests/quest-nodes) marks each one, and [List permitted quest node types](https://developers.xsolla.com/api/quests/publisher-api/get-quest-node-types-in-project) returns the nodes publishers may use, with their parameter schemas, for tools. The list is the same for every project, except that the Web3 reward nodes are left out where Web3 rewards are not available to you or to the merchant. [**Manage your quests**](https://developers.xsolla.com/api/quests/publisher-guide#publisher-manage-quests) lists the routes to read, update and delete it.

#### 3. Send events

Your backend sends an event with [Send a publisher event](https://developers.xsolla.com/api/quests/publisher-events/publisher-events) each time a player does something that matters. [**Level completed event from a publisher**](https://developers.xsolla.com/api/quests/examples-publisher-event) on the Examples page shows one.

Send each real occurrence with a new `idempotency_key`, and resend the same key when you retry. The [**Publisher events guide**](https://developers.xsolla.com/api/quests/publisher-events-guide) covers every field.

##### Check the result

The chest is delivered to the player's `gamer_id` in your game, so check it there. To see what the quest did, read it as that player with [Get a quest with the caller's progress](https://developers.xsolla.com/api/quests/player-progress/get-me-quest): `completed` means every action succeeded. When a reward failed, the quest stays `in_progress`, and `last_error.code` names the reason; each node's **Errors** table on [**Quest nodes**](https://developers.xsolla.com/api/quests/quest-nodes) explains its codes. This works for public quests only, read with the player's token.

#### 4. Show quests to players

Players see only quests created with `is_public: true`. A quest without it, such as the chest quest as written, never appears in these lists. [**Public quests guide**](https://developers.xsolla.com/api/quests/public-quests-guide) explains how to make a quest public and choose what players see.

* **With the player's progress.** A game client signed in as the player [lists the project's public quests with that player's progress](https://developers.xsolla.com/api/quests/player-progress/list-me-quests), using the player's token. Progress is always the caller's own, and it is found only when your events name the player with an identifier the token carries: `xsolla_id` for an Xsolla ID token; for an Xsolla Login token, the Login user ID (as `xsolla_id` or `gamer_id`), or the token's `server_custom_id` or `external_account_id` as `gamer_id`.
* **Without signing in.** The same public quests are listed by the [public quest list](https://developers.xsolla.com/api/quests/public-quest-list/list-public-quests), which needs no credential, for example for a landing page.
* **Events from the game client.** A game client can send events of its own for the signed-in player when the quest's trigger allows it; see [**Client events**](https://developers.xsolla.com/api/quests/publisher-events-guide#publisher-sending-client).

#### Manage your quests

All on your project's routes, with the same credentials as creating:

| Task | Operation |
| --- | --- |
| List | [List quests (project scope)](https://developers.xsolla.com/api/quests/publisher-api/list-quests-in-project) |
| Read | [Get quest by ID (project scope)](https://developers.xsolla.com/api/quests/publisher-api/get-quest-by-id-in-project) |
| Update | [Update a quest (project scope)](https://developers.xsolla.com/api/quests/publisher-api/update-quest-in-project) |
| Delete | [Delete a quest (project scope)](https://developers.xsolla.com/api/quests/publisher-api/delete-quest-in-project) |
| See which nodes you may use | [List permitted quest node types (project scope)](https://developers.xsolla.com/api/quests/publisher-api/get-quest-node-types-in-project) |

* **Web3 rewards are not available to every caller.** Where they are not available to you or to the merchant, the list leaves out quests with a Web3 reward node, and reading or updating such a quest answers `404`, as for a quest that does not exist.
* **Update replaces the quest**: send the whole body, as on create. Only `public_view`, `objectives` and `is_public` keep their stored values when left out. Every update gets a new `version_id`.
* **Some changes are refused** once players have progress (`409`); [**Editing a live quest**](https://developers.xsolla.com/api/quests/quest-guide#quest-editing) lists them.
* **Delete** marks the quest `deleted` and stops its triggers, so it is no longer listed or run. Treat deletion as final: to run the quest again, create a new one rather than updating the deleted one.

#### Manage your projects

* [List a merchant's projects](https://developers.xsolla.com/api/quests/publisher-api/list-merchant-projects) shows which projects are onboarded. A publisher key cannot call it, because a publisher key is accepted only on routes that name a project.
* [Get project](https://developers.xsolla.com/api/quests/publisher-api/get-project) reads one project.

## Authentication

Which credentials the API accepts, which operations accept each one, and what the authentication errors mean.

#### Credentials

The API accepts these credentials:

| Credential | Scheme | How to send it |
|---|---|---|
| Publisher key | Publisher-key | `Authorization: Basic <base64(merchant_id:api_key)>`. The username is your merchant ID and the password is your Xsolla API key. |
| Publisher Account token | Publisher-Account-token | `Authorization: Bearer <token>` |
| Xsolla ID token | Player-token | `Authorization: Bearer <token>`, with a player's Xsolla ID token. Accepted only by the player quest operations. |
| Xsolla Login token | Player-token | `Authorization: Bearer <token>`, with a player's token from Xsolla Login. Accepted only by the player quest operations. |

**Which player token.** Both player tokens identify the signed-in player. An Xsolla ID token comes from Xsolla ID, the Xsolla account players use across Xsolla products. An Xsolla Login token comes from your game's own Xsolla Login project. A Login token must also carry the `publisher_id` claim, the merchant its Login project belongs to; without it the player quest operations and client events return 403.

#### Credentials per operation

Each operation accepts only some of them:

| Operations | Accepted credentials |
|---|---|
| [Onboard project](https://developers.xsolla.com/api/quests/publisher-api/onboard-project) | Publisher key or Publisher Account token |
| [Get project](https://developers.xsolla.com/api/quests/publisher-api/get-project) and the quest operations in a project, such as [Create a new quest (project scope)](https://developers.xsolla.com/api/quests/publisher-api/create-quest-in-project) | Publisher key or Publisher Account token |
| [List a merchant's projects](https://developers.xsolla.com/api/quests/publisher-api/list-merchant-projects) | Publisher Account token. A publisher key is not accepted. |
| [List public quests](https://developers.xsolla.com/api/quests/public-quest-list/list-public-quests) and [Get a public quest](https://developers.xsolla.com/api/quests/public-quest-list/get-public-quest) | None. A credential is not needed. |
| [List quests with the caller's progress](https://developers.xsolla.com/api/quests/player-progress/list-me-quests) and [Get a quest with the caller's progress](https://developers.xsolla.com/api/quests/player-progress/get-me-quest) | The player's Xsolla ID token or Xsolla Login token |
| [Send an event](https://developers.xsolla.com/api/quests/publisher-events/publisher-events) | Publisher key or Publisher Account token |
| [Send an event from a game client](https://developers.xsolla.com/api/quests/client-events/client-events) | The player's Xsolla ID token or Xsolla Login token |

#### Authentication errors

A missing or invalid credential returns 401. On the onboarding, project and quest operations, a valid credential without permission for the operation returns 403, and a merchant, project or quest that does not exist returns the same 404 as one that your credential has no access to. The send event operation returns 401 in all these cases, including for a project that is not onboarded. On the player quest operations, an Xsolla Login token without a `publisher_id` claim returns 403, a project that is not onboarded returns 404, and a malformed merchant or project ID in the path returns 422.

The Authentication section of each operation lists its exact rules and errors.

## Publisher events guide

***Everything about the events your quests react to, for publishers:*** the endpoint, the fields, who the event is about, events from the game client, and which quests an event reaches. Onboarding and creating quests are in the [**Publisher guide**](https://developers.xsolla.com/api/quests/publisher-guide).

#### How to send an event

[**Send a publisher event**](https://developers.xsolla.com/api/quests/publisher-events/publisher-events)

From your backend, with a Publisher Account token or a publisher key. The merchant and project come from the path.

[**Example event**](https://developers.xsolla.com/api/quests/examples-publisher-event)

Level completed event from a publisher, accepted by the API as shown.

> **200 means accepted**
>
> The answer is `200` with the event's `idempotency_key` and an `event_id`. The event is accepted, not processed yet: quests run moments later. On a public quest, a game client signed in as the player sees the outcome through [List quests with the caller's progress](https://developers.xsolla.com/api/quests/player-progress/list-me-quests); there is no progress read for your backend.

#### The event

| Field | Example | What it is |
| --- | --- | --- |
| **idempotency_key** | `"6f1c2a3b-…"` | A new UUID for each real occurrence, and the **same** UUID when retrying it; each quest processes a key once |
| **name** | `"level_completed"` | Routes the event to quests whose trigger has this `event_name`; copy it from the quest, character for character |
| **user_ids** | `[{"identifier_type": "gamer_id", "value": "player-42"}]` | Who the event is about; see [**Player identifiers**](https://developers.xsolla.com/api/quests/publisher-events-guide#publisher-sending-players) |
| **client_timestamp** | `"2026-11-02T10:15:00Z"` | When it happened on your side, in UTC (RFC 3339), not when it was sent |
| **quest_id** | `"0b1c…"` | Optional: limits the event to one quest; leave out unless one event name serves several quests |
| **scope** | `"private"` | Optional: narrows which later event counts include it; see [**Scope**](https://developers.xsolla.com/api/quests/publisher-events-guide#publisher-sending-scope) |
| **properties** | `{"level": "12"}` | Optional values sent with the event. Flat string to string, at most 20 entries from a game client |

**The player's IP address.** Web3 rewards are not available to every player. When your backend sends an event for a player, it can pass on the IP address the player's device used to reach it, as `properties.qp_user_ip` (for example `"qp_user_ip": "203.0.113.7"`). The Quest Platform uses it to decide whether a Web3 reward can be paid to that player. It is kept with the event like any other property, so the quest's webhooks and notifications receive it too. It is optional; without it, that decision is made without the IP address. An empty value counts as not sent. Any other value that is not an IPv4 or IPv6 address, with no port, is refused with `422`.

#### Player identifiers

Put every identifier you know for the player in `user_ids`, as a list of `identifier_type` and `value` pairs:

```json
"user_ids": [
  {
    "identifier_type": "gamer_id",
    "value": "player-42"
  },
  {
    "identifier_type": "xsolla_id",
    "value": "2b0f5c1e-7a3d-4e9b-8c6f-1d2e3f4a5b6c"
  }
]
```

Each reward or email needs a particular identifier, and a node whose identifier is missing fails. [**Quest nodes**](https://developers.xsolla.com/api/quests/quest-nodes) lists what each node needs.

| `identifier_type` | Value | Needed by, for example |
| --- | --- | --- |
| **xsolla_id** | The player's Xsolla account ID, a UUID | Backpack items, Web3 rewards |
| **gamer_id** | Your game's own player ID | Items and currency delivered into the game, loyalty points |
| **guest_id** | A guest player's ID, for players who are not signed in | Per-player limits, when the event has no `xsolla_id` or `gamer_id` |
| **email** | The player's email; must contain `@` | A CRM email to that player; in place of `xsolla_id` (see below) |

**Email instead of `xsolla_id`.** A reward that needs an `xsolla_id` (Backpack items, Web3 rewards, scoped currency) can be paid from the event's `email` when the event has no `xsolla_id`: the Quest Platform looks up the Xsolla account the email belongs to. An `xsolla_id` on the event always wins. An email that belongs to no Xsolla account fails the node with `email_not_resolved`; if the lookup cannot be completed, the node is retried and fails with `xsolla_id_lookup_unavailable`.
The email is used only to find the reward's recipient; the player's quest progress and per-player limits are still kept under the identifiers you sent, so send each player with the same identifier every time: a player sent sometimes by `email` and sometimes by `xsolla_id` is counted as two players.

#### Events from the game client

Your game client can also send events itself, for the player who is signed in. Events from your backend and from the game client reach the same quests.

[**Send an event from a game client**](https://developers.xsolla.com/api/quests/client-events/client-events)

With the player's own token.

| | From your backend | From the game client |
| --- | --- | --- |
| **Credential** | Publisher Account token or publisher key | The player's token |
| **Body** | Every field above | Only `idempotency_key`, `name`, `client_timestamp` and `properties` |
| **The player** | From `user_ids` | From the token |
| **Counted by event-count checks** | Always | Only where the operand sets `include_client_events` |

The same occurrence, sent both ways. **From your backend**, the body names the player in `user_ids`:

```json
{
  "idempotency_key": "6f1c2a3b-4d5e-4f60-8a7b-9c0d1e2f3a4b",
  "name": "level_completed",
  "scope": "within_project",
  "user_ids": [
    {
      "identifier_type": "gamer_id",
      "value": "player-42"
    },
    {
      "identifier_type": "xsolla_id",
      "value": "2b0f5c1e-7a3d-4e9b-8c6f-1d2e3f4a5b6c"
    }
  ],
  "client_timestamp": "2026-11-02T10:15:00Z",
  "properties": {
    "level": "12"
  }
}
```

**From the game client**, the body has no player, because the token says who it is:

```json
{
  "idempotency_key": "7a2d3b4c-5e6f-4a71-8b9c-0d1e2f3a4b5c",
  "name": "level_completed",
  "client_timestamp": "2026-11-02T10:15:00Z",
  "properties": {
    "level": "12"
  }
}
```

> **The quest must allow it**
>
> A client event is accepted only when an active quest of the project allows it: a [dynamic_event](https://developers.xsolla.com/api/quests/node-dynamic-event) trigger with `client_sendable: true`, or an event operand with `include_client_events: true`. Otherwise the answer is `403`.
> The endpoint is rate limited: after a `429`, wait and retry with the same `idempotency_key`.

#### Which quests an event reaches

An accepted event runs a quest only when all of these hold. None of them is an error: an event that misses one is simply not used.

1. **Same project**

   The quest belongs to the project in the path; a quest of another project never sees the event.

2. **Same name**

   A trigger's `event_name` equals the event's `name` exactly: no wildcards, and case and punctuation count (`app.onboarding_completed` is not `app.onboarding-completed`).

3. **Same merchant and project**

   The event reaches only quests with the `publisher_id` and `project_id` of the path; quests without them are skipped.

4. **Active**

   The quest is `active`, and now (UTC) is between its `start_date` and `end_date`.

5. **The quest asked for**

   With `quest_id`, only that quest is considered. It must be a UUID; any other value is rejected with `422`.

#### Scope

`scope` decides which event-count checks ([custom_attributes_check](https://developers.xsolla.com/api/quests/node-custom-attributes-check) event operands) can count this event later. A count only ever includes events of the same account and the same name, sent under the same identifier as the event being checked (its `xsolla_id`, else `gamer_id`, else `email`; `guest_id` is never counted); scope narrows it further.

| `scope` | Counted by | Needs |
| --- | --- | --- |
| `private` (default) | Any check in the sending account; the event is tied to that account | Nothing |
| `global` | Any check in the sending account too: the event is marked for every account, but counts never leave the account | Nothing |
| `within_publisher` | Checks run for an event with the same `publisher_id` | Nothing |
| `within_project` | Checks run for an event with the same `publisher_id` and `project_id` | Nothing |
| `within_quest` | Checks run for an event with the same `quest_id` | `quest_id` |

Because counts never leave the account, `global` and `private` count the same today.

With `within_quest`, the event must carry `quest_id`; without it the event is still accepted with `200`, but no quest runs for it. Use `private` unless several quests or projects in one account must not see each other's events.

#### Count in the Quest Platform or in your app

A goal like "finish 6 onboarding steps" can be built two ways:

| | Your app counts | The Quest Platform counts |
| --- | --- | --- |
| Events | One `onboarding_completed` when the last step is done | One event per step |
| Quest | Trigger → reward | Trigger → condition (event count `gte 6`) → reward |
| Progress in the Quest Platform | None until the reward | Each step is recorded; the progress read can show 3 of 6 |
| Changes | Need an app release | A new quest |
| Windows | Your own | Calendar day, week or month only |

Count in the Quest Platform when players should see progress, or when the goal may change; count in your app when the steps never reach your backend, or the rule needs more than a day, week or month window.

#### Retries

* Generate a new `idempotency_key` (a UUID) for each event, and send the **same** key when you retry it.
* A retry is accepted again and gets a new `event_id`, but each quest processes an event key only once, and event counts count each key once. So retrying never progresses a quest or a count twice.
* Retry with the same key on any `5xx` answer and on network errors. `4xx` answers will not succeed on retry, except after you fix the request or the credential.
* The API also accepts an `X-Idempotency-Key` header, which may replay the earlier response for up to 30 minutes. It is a convenience only; `idempotency_key` in the body is what deduplicates.

## Endpoints

### Publisher API

- `GET /api/v2/merchants/{merchant_id}/projects`: [List a merchant's projects](https://developers.xsolla.com/api/quests/publisher-api/list-merchant-projects)
- `GET /api/v2/merchants/{merchant_id}/projects/{project_id}`: [Get project](https://developers.xsolla.com/api/quests/publisher-api/get-project)
- `POST /api/v2/merchants/{merchant_id}/projects/{project_id}/onboard`: [Onboard project](https://developers.xsolla.com/api/quests/publisher-api/onboard-project)
- `GET /api/v2/merchants/{merchant_id}/projects/{project_id}/quests`: [List quests (project scope)](https://developers.xsolla.com/api/quests/publisher-api/list-quests-in-project)
- `POST /api/v2/merchants/{merchant_id}/projects/{project_id}/quests`: [Create a new quest (project scope)](https://developers.xsolla.com/api/quests/publisher-api/create-quest-in-project)
- `DELETE /api/v2/merchants/{merchant_id}/projects/{project_id}/quests/{id}`: [Delete a quest (project scope)](https://developers.xsolla.com/api/quests/publisher-api/delete-quest-in-project)
- `GET /api/v2/merchants/{merchant_id}/projects/{project_id}/quests/{id}`: [Get quest by ID (project scope)](https://developers.xsolla.com/api/quests/publisher-api/get-quest-by-id-in-project)
- `PUT /api/v2/merchants/{merchant_id}/projects/{project_id}/quests/{id}`: [Update a quest (project scope)](https://developers.xsolla.com/api/quests/publisher-api/update-quest-in-project)
- `GET /api/v2/merchants/{merchant_id}/projects/{project_id}/quests/node-types`: [List permitted quest node types (project scope)](https://developers.xsolla.com/api/quests/publisher-api/get-quest-node-types-in-project)

### Publisher events

- `POST /api/v2/merchants/{merchant_id}/projects/{project_id}/events`: [Send an event](https://developers.xsolla.com/api/quests/publisher-events/publisher-events)

### Public quest list

- `GET /api/v2/public/merchants/{merchant_id}/projects/{project_id}/quests`: [List public quests](https://developers.xsolla.com/api/quests/public-quest-list/list-public-quests)
- `GET /api/v2/public/merchants/{merchant_id}/projects/{project_id}/quests/{quest_id}`: [Get a public quest](https://developers.xsolla.com/api/quests/public-quest-list/get-public-quest)

### Player progress

- `GET /api/v2/me/merchants/{merchant_id}/projects/{project_id}/quests`: [List quests with the caller's progress](https://developers.xsolla.com/api/quests/player-progress/list-me-quests)
- `GET /api/v2/me/merchants/{merchant_id}/projects/{project_id}/quests/{quest_id}`: [Get a quest with the caller's progress](https://developers.xsolla.com/api/quests/player-progress/get-me-quest)

### Client events

- `POST /api/v2/me/merchants/{merchant_id}/projects/{project_id}/events`: [Send an event from a game client](https://developers.xsolla.com/api/quests/client-events/client-events)
