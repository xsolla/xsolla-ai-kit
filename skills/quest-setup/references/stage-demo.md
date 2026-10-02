# STAGE DEMO ONLY: cross-environment quest demo rules

> **Label: STAGE DEMO ONLY (QP-2890).** Everything in this file is a temporary
> demo exception. Remove this file and the lines that link to it (each marked
> "STAGE DEMO ONLY") once a publisher-usable catalog resolver, execution
> read-back and public quest list ship on the public gateway.

## Gate

Apply this file only when **both** are true:

1. `XSOLLA_QP_ENV` resolves to `stage` per
   [Credential](auth-and-environment.md#credential);
2. the resolved Quest Platform scope equals a row in the
   [demo binding](#demo-binding).

Otherwise ignore this file completely. A production run (selector absent or
`production`) keeps every stop in the rest of this skill: no catalog lookup, no
execution read-back, no stage host, no fallback. Never use this file to switch
a production run to stage, and never mention this file, a demo, stage or
switching environments to the publisher.

## Turn plan

Three publisher turns, each ending at a stop point:

1. Request: read-only checks, then the proposal. **Stop.** First run
   `date -u +%Y-%m-%dT%H:%M:00Z` for `<now UTC>`. Then two commands, both
   read-only:
   1. The project read: the `-K -` credential pattern from
      [Credential](auth-and-environment.md#credential) against
      `https://quests-stage.xsolla.com/api/v2/merchants/<merchant id>/projects/<project id>`.
   2. The resolver command under
      [Named item resolution](#named-item-resolution) (catalog pages,
      metadata, wallet). Exactly one `verified` entry and `wallet_status`
      200 lead to the proposal; anything else is a stop from that section.
2. "Yes": run the [publish command](#publish-command) once, filled from the
   approved proposal. It makes these calls in order: `POST` inactive quest,
   `GET` it, `PUT` activation, `GET` it again, `GET` the quest list, `GET`
   the public list (never the `XSOLLA_QP_PUBLIC_BASE_URL` shop URL). Reply
   with **Result**, **Web Shop** and **Next step** from its output; the
   payload uses its `idempotency_key` and `client_timestamp`. **Stop. Do not
   send the event.**
3. "Yes" to that payload: run the [event command](#event-command) once with
   exactly that payload. It waits until 90 seconds after activation, sends
   once, then reads back execution and mint. Reply with **Result** and
   **Next step** from its output. **Stop.**

Run each command exactly as written, filling only the angle brackets. Never
split it into separate calls or rewrite it with another client.

Each reply is the matching skeleton under [Reply shape](#reply-shape), copied
word for word with the angle brackets filled; nothing before or after it.

## Demo binding

| Quest Platform scope (merchant / project) | Catalog project (Publisher Account project) |
|---|---|
| `940246` / `316575` | `316665` |

The catalog project is the Publisher Account project that owns the item. It is
never the Quest Platform project. Take it only from this table.

Demo read hosts (VPN only, private CA; skip certificate verification for these
hosts only, never for the public gateway):

| Use | Base |
|---|---|
| Catalog and mint reads | `https://web3-minting-service.gcp-k8s-web3-stage.srv.local` |
| Execution read-back | `https://qp-data.nl-k8s-stage.srv.local` |
| Public quest list check | `https://qp-server.nl-k8s-stage.srv.local` |

All calls on these hosts are unauthenticated GETs. Never send the publisher
credential, an internal key or any other header to them. Never name these hosts,
the services behind them or the environment in a publisher reply. Quest
configuration and events still use only the public stage gateway from
[`qp-api-contract.md`](qp-api-contract.md).

## Named item resolution

This is the "available supported capability" for
[Named item behavior](rewards.md#named-item-behavior) on the demo scope.

1. Page the catalog: `GET {catalog}/skus?project=<catalog project>&limit=100&offset=<n>`
   from `offset=0` until a page returns fewer than 100 items. Do not rely on
   `search`: it filters only the fetched page. Copy this path exactly: it
   has no `/api/...` prefix and the project is a query parameter. A 404 means
   the path is wrong; fix it, never ask the publisher about the item.
2. Candidates are items whose `name`, trimmed and compared case-insensitively,
   equals the requested item name. A substring or similar name is not a match.
3. For each candidate, `GET {catalog}/metadata/sku/<sku>?project=<catalog project>`.
   Keep it only on HTTP 200 with a matching name.
4. Exactly one kept candidate is the verified item. Use its SKU and the catalog
   project in the `web3_item` body. Zero: stop before any write and say the item
   was not found in the catalog (suggest checking the name and that the item is
   enabled). More than one: ask the publisher to choose by name and
   description. Never ask the publisher to type a SKU or project.

Run steps 1 to 4 and the [recipient wallet](#recipient-wallet) check as this
one command, filling only the item name and the test player's Xsolla ID:

```sh
python3 - "<item name>" "<xsolla_id>" <<'PY'
import json, ssl, sys, urllib.error, urllib.request
want, xid = sys.argv[1].strip().lower(), sys.argv[2].strip()
H, P = "https://web3-minting-service.gcp-k8s-web3-stage.srv.local", "316665"
ctx = ssl._create_unverified_context()
def get(path):
    try:
        with urllib.request.urlopen(H + path, context=ctx, timeout=30) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, None
cands, off = [], 0
while True:
    s, page = get(f"/skus?project={P}&limit=100&offset={off}")
    items = (page or {}).get("items", [])
    cands += [i for i in items if i["name"].strip().lower() == want]
    if s != 200 or len(items) < 100:
        break
    off += 100
kept = [c for c in cands
        if (m := get(f"/metadata/sku/{c['sku']}?project={P}"))[0] == 200
        and m[1]["name"].strip().lower() == want]
w = get(f"/wallet/{xid}")[0]
print(json.dumps({"verified": [{"name": c["name"], "sku": c["sku"]} for c in kept], "catalog_project": P, "wallet_status": w}))
PY
```

Show the item by its catalog name in the proposal. The SKU is an internal
field and stays out of the proposal.

## Recipient wallet

When the publisher names a test player (an Xsolla ID), read
`GET {catalog}/wallet/<xsolla_id>` during the read-only work. HTTP 200 means the
player can receive the item. HTTP 404 is a blocker: say the player has no
Backpack wallet yet and stop before any write. Never create or change a wallet
mapping. Read the wallet again right before the event.

## Publication and list

Publish exactly as [Publication after approval](quest-document.md#publication-after-approval)
says, on the public gateway. After the final `GET`, list the project quests
(`GET {scope}/quests`, paging as needed) and confirm the new quest id appears.

### Publish command

Fill `QUEST` from the approved proposal: `<start UTC>` is `date -u
+%Y-%m-%dT%H:%M:00Z` run in this turn and `<end UTC>` is 7 days later. The
command builds the one-trigger, one-item quest, prints one JSON line, and
stops at the first failed write (a `POST` error means no quest was created;
fix `QUEST` and run it again).

```sh
python3 - <<'PY'
import base64, datetime as d, json, pathlib, ssl, urllib.error, urllib.request, uuid
QUEST = {
  "name": "<quest name>",
  "event_name": "<event_name>",
  "player_action": "<player action>",
  "sku": "<sku>",
  "start": "<start UTC>",
  "end": "<end UTC>",
}
e = dict(l.split("=", 1) for l in pathlib.Path(".env").read_text().splitlines() if "=" in l and not l.lstrip().startswith("#"))
M, PR = e["XSOLLA_MERCHANT_ID"].strip(), e["XSOLLA_PROJECT_ID"].strip()
AUTH = "Basic " + base64.b64encode(f"{M}:{e['XSOLLA_PROJECT_API_KEY'].strip()}".encode()).decode()
S = f"https://quests-stage.xsolla.com/api/v2/merchants/{M}/projects/{PR}"
PUB = f"https://qp-server.nl-k8s-stage.srv.local/api/v2/public/merchants/{M}/projects/{PR}/quests?page=1&limit=10"
def call(method, url, body=None, auth=True):
    h = {"Content-Type": "application/json", **({"Authorization": AUTH} if auth else {})}
    req = urllib.request.Request(url, method=method, headers=h, data=None if body is None else json.dumps(body).encode())
    ctx = None if auth else ssl._create_unverified_context()
    try:
        with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as x:
        return x.code, x.read().decode()[:500]
def utc(v):
    return d.datetime.fromisoformat(v).astimezone(d.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
t, a = str(uuid.uuid4()), str(uuid.uuid4())
body = {"name": QUEST["name"], "type": "liveops", "status": "inactive", "created_by": "AI Toolkit",
        "start_date": QUEST["start"], "end_date": QUEST["end"],
        "nodes": [{"id": t, "name": QUEST["player_action"], "type": "trigger", "subtype": "dynamic_event", "parameters": {"event_name": QUEST["event_name"]}},
                  {"id": a, "name": "Issue quest reward", "type": "action", "subtype": "issue_reward",
                   "parameters": {"type": "web3_item", "purpose": "quest_completion", "body": {"project": "316665", "item_sku": QUEST["sku"], "quantity": 1}}}],
        "connections": {t: [{"nodeId": a}]}, "activation_limits": [{"type": "per_user", "count": 1}]}
s, q = call("POST", S + "/quests", body)
if s != 200:
    print(json.dumps({"failed": "POST", "status": s, "error": q})); raise SystemExit(1)
qid = q["id"]
s, q = call("GET", f"{S}/quests/{qid}")
if s != 200:
    print(json.dumps({"failed": "GET", "status": s, "id": qid})); raise SystemExit(1)
q["status"] = "active"
s, r = call("PUT", f"{S}/quests/{qid}", q)
if s != 200:
    print(json.dumps({"failed": "PUT", "status": s, "id": qid, "error": r})); raise SystemExit(1)
s, q = call("GET", f"{S}/quests/{qid}")
_, lst = call("GET", S + "/quests?page=1&limit=100")
_, pub = call("GET", PUB, auth=False)
print(json.dumps({"id": qid, "status": q.get("status"), "start_utc": utc(q["start_date"]), "end_utc": utc(q["end_date"]),
                  "updated_at": q.get("updated_at"), "in_list": qid in json.dumps(lst), "in_public_list": qid in json.dumps(pub),
                  "event_name": QUEST["event_name"], "client_timestamp": d.datetime.now(d.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                  "idempotency_key": str(uuid.uuid4())}))
PY
```

## Web Shop handoff

After the list read-back, check the storefront list once:
`GET https://qp-server.nl-k8s-stage.srv.local/api/v2/public/merchants/{merchant_id}/projects/{project_id}/quests?page=1&limit=10`
with no credentials. Confirm the new quest is present with the catalog item
name. Then add a **Web Shop** section to the reply:

- The shop quest module reads
  `{XSOLLA_QP_PUBLIC_BASE_URL}/api/v2/public/merchants/{merchant_id}/projects/{project_id}/quests?page=1&limit=10`
  with no credentials. Read `XSOLLA_QP_PUBLIC_BASE_URL` like the selector:
  run `printenv XSOLLA_QP_PUBLIC_BASE_URL` first; only if that prints nothing,
  read just that line of `.env`. Use it only to print this URL; never send an
  agent request to it. Only when both are truly absent, show the path and say
  the shop needs its public quest base configured; a failed read is not
  absence.
- This is the only line where the merchant and project ids may appear.
- Never put a `*.srv.local` host, an API key or an `Authorization` header in
  the shop build. Shop source edits need their own consent.

## Event

Events follow [`events.md`](events.md) and the Safety stops: the payload shown
first, a separate yes, one fresh `idempotency_key`, no resend. Send it only to
the stage gateway `https://quests-stage.xsolla.com`; never to the production
gateway. Wait at least
90 seconds after the activation read-back before sending: the runtime caches
quest configuration for about 60 seconds.

### Event command

Fill `PAYLOAD` with the exact JSON shown to the publisher, `UPDATED_AT` from
the publish output and `<sku>` from the resolver output.

```sh
python3 - <<'PY'
import base64, datetime as d, json, pathlib, ssl, time, urllib.error, urllib.request
PAYLOAD = <the exact JSON payload shown to the publisher>
UPDATED_AT = "<updated_at from the publish command>"
SKU = "<sku>"
e = dict(l.split("=", 1) for l in pathlib.Path(".env").read_text().splitlines() if "=" in l and not l.lstrip().startswith("#"))
AUTH = "Basic " + base64.b64encode(f"{e['XSOLLA_MERCHANT_ID'].strip()}:{e['XSOLLA_PROJECT_API_KEY'].strip()}".encode()).decode()
ctx = ssl._create_unverified_context()
def get(url):
    try:
        with urllib.request.urlopen(url, timeout=30, context=ctx) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as x:
        return x.code, None
wait = 90 - (d.datetime.now(d.timezone.utc) - d.datetime.fromisoformat(UPDATED_AT)).total_seconds()
time.sleep(max(0, wait))
req = urllib.request.Request("https://quests-stage.xsolla.com/api/v2/events", method="POST",
                             data=json.dumps(PAYLOAD).encode(), headers={"Content-Type": "application/json", "Authorization": AUTH})
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        s, ev = r.status, json.load(r)
except urllib.error.HTTPError as x:
    print(json.dumps({"event_status": x.code, "error": x.read().decode()[:500]})); raise SystemExit(1)
eid, xid, qid = ev.get("event_id"), PAYLOAD["user_ids"][0]["value"], PAYLOAD["quest_id"]
row = None
for _ in range(12):
    time.sleep(10)
    _, data = get(f"https://qp-data.nl-k8s-stage.srv.local/api/v1/quest-executions?questId={qid}&userId={xid}&includeNotTriggered=true&page=1&size=20")
    row = next((i for i in (data or {}).get("items", []) if i.get("eventId") == eid), None)
    if row and row.get("status") != "IN_PROGRESS":
        break
mint = None
if row and row.get("status") == "COMPLETED":
    for _ in range(12):
        _, data = get(f"https://web3-minting-service.gcp-k8s-web3-stage.srv.local/minted-instances/{xid}")
        hits = [i for i in (data or {}).get("instances", []) if i.get("sku") == SKU and i.get("projectId") == "316665"]
        if hits:
            mint = max(hits, key=lambda i: i.get("mintedAt", ""))
            break
        time.sleep(10)
print(json.dumps({"event_status": s, "event_id": eid,
                  "execution": row and row.get("status"),
                  "actions": row and [(x.get("actionType"), x.get("status"), x.get("error")) for x in row.get("actions", [])],
                  "token_id": mint and mint.get("tokenId"),
                  "tx": mint and "https://zksync-os-testnet-xsolla.explorer.zksync.dev/tx/" + mint["txHash"]}))
PY
```

## Execution read-back

On the demo scope, execution read-back is publisher-usable for the developer's
own quest only:

1. After the event, `GET {read-back}/api/v1/quest-executions?questId=<quest id>&userId=<xsolla_id>&includeNotTriggered=true&page=1&size=20`.
2. The response is `{"items": [{"eventId", "status", "quest": {"id"},
   "user": {"xsollaId"}, "actions": [{"actionType", "status", "error"}]}]}`.
   Rows are under `items`. Match `eventId` to the collector `event_id`, and
   compare quest id and user.
3. Poll at most 12 times, 10 seconds apart, while the row is missing or
   `IN_PROGRESS`. Never resend the event.
4. Report the execution status and each action status exactly as the
   matched row shows them. A `FAILED` action's `error` is quoted verbatim. If
   no row matched, say the run is not visible yet; never infer a status from
   the mint or anything else.

## Mint evidence

After `COMPLETED`, read `GET {catalog}/minted-instances/<xsolla_id>` (poll at
most 12 times, 10 seconds apart). The response is
`{"instances": [{"projectId", "sku", "tokenId", "txHash", "mintedAt", ...}]}`
and lists every item on the player's wallet; the match is the newest entry
whose `sku` equals the quest's SKU and whose `projectId` equals the catalog
project. Stop polling as soon as it exists. Report the item name, token id and the public
transaction link `https://zksync-os-testnet-xsolla.explorer.zksync.dev/tx/<txHash>`.
Say the item should now appear in the player's Backpack under its catalog name,
and that Backpack display is for the publisher to check. A missing mint row is
not a reason to resend.

## Reply shape

Every reply uses the sections **Summary**, **Proposed setup**, **Web Shop**,
**Result**, **Need from you**, **Next step** as they apply; omit empty ones.
One proposal and one approval cover create through activate, list and the
Web Shop check. The event always needs its own yes.

Start every reply with its first section heading; no greeting, narration or
status line before it. Never write an environment name (stage, production,
sandbox) or a host in a reply.

Proposal (one reply, after all reads). Copy this skeleton exactly, filling the
angle brackets; the reply is this text and nothing else:

```markdown
## Summary
Your project is ready for quests. <Item name> is in your catalog and your test player can receive it.

## Proposed setup
- **Quest:** <quest name>
- **Player action:** <what the player does>, sent as the `<event_name>` event
- **Reward:** <quantity> x <Item name>
- **Schedule:** starts at publish time, for example `<now UTC>`; ends 7 days later, for example `<now + 7 days UTC>`
- **Limit:** one reward per player
- **Payout exposure:** one item per player; total unbounded across players

## Need from you
Reply yes to publish this exact setup.
```

Take `<now UTC>` from `date -u +%Y-%m-%dT%H:%M:00Z` run in this turn; never
estimate the time. Every time in a reply or a request body is UTC ending in
`Z`; never a local offset. When a read-back returns an offset such as
`+03:00`, convert it to UTC before showing it. If the resolver found no verified item, the whole reply is:

```markdown
## Summary
I couldn't find <item name> in your catalog, so nothing was created.

## Need from you
Check the item name in your catalog (and that the item is enabled), then tell me the exact name.
```

Infer the event name when you can; do not ask about it. Do not mention a test
event anywhere in the proposal.

After publication, copy this skeleton (if no test player was named, the Next
step asks for one instead):

````markdown
## Result
<Quest name> is published and active from `<start UTC>` to `<end UTC>`, one reward per player, and it appears in your quest list.

## Web Shop
Point your Web Shop quest list at:
`<public list URL>`
It needs no key and shows <Quest name>.

## Next step
Reply yes to send this one test event for your test player:
```json
{
  "idempotency_key": "<fresh uuid4>",
  "name": "<event_name of the trigger>",
  "client_timestamp": "<now UTC>",
  "user_ids": [{"identifier_type": "xsolla_id", "value": "<test player xsolla_id>"}],
  "quest_id": "<quest id>",
  "scope": "private",
  "publisher": {"publisher_id": "<merchant id>", "project_id": "<project id>"}
}
```
````

A yes to that shown payload is the event consent: send it once, unchanged. If
more than 10 minutes passed or anything changes, show a new payload with a new
key and ask again. After the event, copy this skeleton:

```markdown
## Result
- **Event:** accepted (`<eventId>`)
- **Quest run:** <execution status>; reward action <reward action status>
- **Reward:** <Item name>, token <token id>, transaction <explorer link>

## Next step
Open Backpack as your test player; the item should appear there. Nothing else will be sent.
```
