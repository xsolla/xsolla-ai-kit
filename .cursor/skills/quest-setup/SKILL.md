---
name: quest-setup
description: >-
  Creates and inspects production Xsolla Quest Platform quests. Covers the
  authentication and API contract for the project-scoped routes. Use when asked about
  the quest platform API or when listing quests. Examples: "list my quests", "quest
  platform API".
metadata:
  owner: r.aliyev
  domain: quests
---

## Status

This skill targets **production** only. Resolve Quest Platform scope from the configured integration (see
[auth and environment](references/auth-and-environment.md)); never fall back to
another service target or credential source.

## Hard rules (read first)

1. **One target.** Quest configuration and events use only
   `https://quests-platform.xsolla.com`, as in
   [`qp-api-contract.md`](references/qp-api-contract.md). Never call another
   gateway, even after a failure, and never suggest switching environments.
2. **No secrets on screen.** Never open `.env` in a viewer, print the
   environment, paste a key into a command, or print the API key, even to
   yourself. Parse credentials as text inside the request, as in
   [Credential](references/auth-and-environment.md#credential). If the three
   credential names exist, the project is set up: continue with the read-only
   preflight and never ask the publisher to confirm settings. Never ask the
   publisher to paste secrets or search for another key.
3. **No IDs or hosts in replies.** Never show merchant, project or player IDs, hosts, service names
   or environment names to the publisher. Every reply starts with a `##`
   heading: no lead-in line such as "Perfect!" or a recap before it.
4. **Never claim delivery.** Report what the read-backs show, nothing more.
5. **Stop on auth failures.** Never switch credentials, lanes or routes on your
   own after a failure; report what failed and ask. For a 401 or 404 follow
   [Reading a 401 or 404](references/auth-and-environment.md#reading-a-401-or-404).

## When to use

Use this skill when the developer wants to manage Xsolla Quest Platform quests:

- List and view existing quests (read-only)

## Prerequisites

The configured production publisher credential is the only lane. It works only
on the project-scoped routes in
[`qp-api-contract.md`](references/qp-api-contract.md). Credential, scope and
onboarding: [Prerequisites and lane](references/auth-and-environment.md#prerequisites-and-lane).
With no production credential, report only that the project is not set up for
quests yet and stop.

## Reference routing

Routes and envelopes come from the contract
([Source of truth](references/qp-api-contract.md#source-of-truth)). If it does
not answer, ask the developer.

| Topic | Reference |
|---|---|
| Credential, routes, onboarding, 401/404, error statuses, write and credential stops | [`auth-and-environment.md`](references/auth-and-environment.md) |
| Quest Platform routes, probes, source of truth | [`qp-api-contract.md`](references/qp-api-contract.md) |

## Flow

1. **Bring-up.** Load [`qp-api-contract.md`](references/qp-api-contract.md) and
   run the preflight reads in
   [`auth-and-environment.md`](references/auth-and-environment.md#service-preflight).
   Bring-up is GET-only. Never fetch OpenAPI or another target. Confirm project scope before a write and report only a
   short project name and status. If the project GET is 404 `Project not found`,
   follow [Onboarding](references/auth-and-environment.md#onboarding) and stop.

## Safety stops (summary)

Full text: [writes and credentials](references/auth-and-environment.md#safety-stops-for-writes-and-credentials).

- Show the resolved scope before the first write; ask separately before any
  other non-GET call, showing the exact body first.
- Branch errors on HTTP status per
  [Errors](references/auth-and-environment.md#errors). `ID 0` is a valid
  merchant and project ID; never treat it as absent.
