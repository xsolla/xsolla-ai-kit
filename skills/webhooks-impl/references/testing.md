# Testing Xsolla webhooks

Three ways to validate a webhook handler. Use **`xsolla webhook trigger`** for everyday
agent work, the app's **test suite** for events the CLI has no payload for, and a
**tunnel** when you need a live delivery from Xsolla.

Fixtures live in [`fixtures/`](../fixtures/) next to this skill
(`user_validation`, `order_paid`, `payment` — JSON + matching `.raw.txt`).

---

## Which webhook arrives when

| Situation | Typical `notification_type`s |
|-----------|------------------------------|
| Before / during checkout (user check) | `user_validation` (often **several** times) |
| Successful purchase via **Store** token (Method 1 or 2 in `shop-setup`) — **combined** delivery (projects after 2025-01-22) | `order_paid` (items + payment in one payload) |
| Same Store purchase — **separate** delivery (older projects) | `payment` **and** `order_paid` (fulfill on `order_paid` only) |
| Successful pay via **Merchant API** token (Method 3 — amount + description, no Store order) | `payment` (items often in `custom_parameters`; **no** Store `order_id`) |
| Refund / cancel | `order_canceled` (combined) or `refund` + `order_canceled` (separate) |
| Subscriptions (if enabled) | `create_subscription` / `update_subscription` / `cancel_subscription` |

**Rule of thumb for shops:** mint with Store Method 1/2 → expect **`order_paid`**
as the fulfillment signal. Merchant Method 3 → expect **`payment`**. Do not grant
twice if both `payment` and `order_paid` arrive (separate mode). Full shapes:
[`events-and-payloads.md`](events-and-payloads.md).

---

## Method 1 — `xsolla webhook trigger` (agent-driven, no public URL)

Use this to implement and smoke-test the handler without Publisher Account or a
tunnel. `xsolla webhook trigger <event> --to <url>` POSTs a built-in payload, signed the
way Xsolla signs deliveries (`Authorization: Signature <sha1(body + secret)>`). It reads
the secret from `XSOLLA_WEBHOOK_SECRET` in its environment, or from `--secret`.

- **Events:** `xsolla webhook trigger --list` prints `payment`, `refund` and
  `user_validation`. They are separate-mode shapes with fixed values (user id `1234567`,
  transaction id `87654321`), so two runs of the same event are a replay.
- **Target:** point `--to` only at the local handler. `trigger` accepts any URL; never
  fire it at a deployed or production host.
- **Result:** a line like `→ payment  <url>  → 204 No Content` on stderr, plus the
  handler's response body. Exit `0` for a status below 400, and exit `1` for a status of
  400 or above, a refused connection or an unknown event. With `--json`, read
  `data.status` and `data.accepted`; `ok` is `true` even when the handler rejected it.

1. **Map fields with the fixtures while writing the handler.** Open
   `fixtures/order_paid.json` / `payment.json` / `user_validation.json` and map
   fields (`user.external_id` vs `user.id`, `items[]`, `billing.transaction.id`,
   …) into your grant / validate logic.

2. **Run the handler with a throwaway test secret, and trigger with the same one.** The
   agent never needs the real secret for this:

   ```bash
   TEST_SECRET="test-$(date +%s)"
   # Start the app with XSOLLA_WEBHOOK_SECRET="$TEST_SECRET" in its environment, then:
   URL=http://localhost:4000/xsolla/webhooks     # the path the app actually mounts
   XSOLLA_WEBHOOK_SECRET="$TEST_SECRET" xsolla webhook trigger user_validation --to "$URL"
   XSOLLA_WEBHOOK_SECRET="$TEST_SECRET" xsolla webhook trigger payment --to "$URL"
   XSOLLA_WEBHOOK_SECRET="$TEST_SECRET" xsolla webhook trigger payment --to "$URL"   # replay
   XSOLLA_WEBHOOK_SECRET="$TEST_SECRET" xsolla webhook trigger refund --to "$URL"
   XSOLLA_WEBHOOK_SECRET=wrong-secret  xsolla webhook trigger payment --to "$URL"   # bad signature
   ```

   Node `dotenv` and `python-dotenv` don't override a variable that is already set, so
   the handler uses the test secret even when `.env` holds the real one. If the app's
   loader does override, use step 3.

3. **Handler already running with the real secret from `.env`.** The CLI doesn't read
   `XSOLLA_WEBHOOK_SECRET` from a project `.env` (it loads only the ID variables from
   there), so pass it into one command's environment without printing it:

   ```bash
   ( export XSOLLA_WEBHOOK_SECRET="$(sed -n 's/^XSOLLA_WEBHOOK_SECRET=//p' .env)"
     xsolla webhook trigger payment --to http://localhost:4000/xsolla/webhooks )
   ```

   This expects an unquoted value in `.env`. Don't pass the value with `--secret`: it
   shows up in the process list and the transcript.

4. **No handler yet, or check what `trigger` sends.** `xsolla webhook listen` is a
   stand-in endpoint that verifies the signature and logs each delivery
   (`sig=valid` / `sig=INVALID`, plus the body) to stderr. `--output json` also
   streams one JSON record per delivery to stdout. Run it in the background with the
   secret in its environment, and stop it when done:

   ```bash
   XSOLLA_WEBHOOK_SECRET="$TEST_SECRET" xsolla webhook listen --port 4000 --path /xsolla/webhooks
   ```

   It binds localhost by default; keep it that way (no `--addr :<port>`). It replies
   `204`, or `401` to a bad signature. That is not the handler contract: your handler
   answers `400 INVALID_SIGNATURE`. `--respond`, `--latency` and `--fail-every` change
   its reply to test a sender, not your handler.

5. **Minimum agent checklist**
   - Right secret → `2xx` for `user_validation` (when the user exists) / `payment`
   - `user_validation` for unknown user `1234567` → `400 INVALID_USER`
   - Wrong secret → `400` + `INVALID_SIGNATURE` (not `200`); `trigger` exits `1`
   - Replay the same `payment` → `2xx`, no second record or grant
   - Separate-mode caution: handling `payment` must **not** grant if you already
     grant on `order_paid`
   - `order_paid` / `order_canceled` → Method 1b

### Method 1b — test-suite replay (`order_paid`, `order_canceled`, custom payloads)

`trigger` has no `order_paid` / `order_canceled` fixture and no flag for a custom body
(a CLI gap). Replay the skill's `.raw.txt` fixtures from the app's own test suite, signed
with a test secret. Node (Jest + supertest) example; port it to the app's stack:

```js
// test/xsolla-webhooks.test.js
process.env.XSOLLA_WEBHOOK_SECRET = 'test-secret';   // throwaway; set before the app loads
const fs = require('fs');
const crypto = require('crypto');
const request = require('supertest');
const app = require('../app');                         // the Express app, exported without listen()

// Copied from this skill's fixtures/ — the exact bytes Xsolla signed.
const body = fs.readFileSync(`${__dirname}/fixtures/order_paid.raw.txt`, 'utf8');
const sign = (secret) => crypto.createHash('sha1').update(body + secret).digest('hex');
const post = (sig) => request(app).post('/xsolla/webhooks')
  .set('Content-Type', 'application/json')
  .set('Authorization', `Signature ${sig}`)
  .send(body);                                         // a string goes out byte-for-byte

test('order_paid grants once; a replay is a no-op', async () => {
  expect((await post(sign('test-secret'))).status).toBeLessThan(300);
  expect((await post(sign('test-secret'))).status).toBeLessThan(300);
  // Assert exactly one grant for billing.transaction.id in your datastore.
});

test('a bad signature is rejected', async () => {
  const res = await post(sign('wrong-secret'));
  expect(res.status).toBe(400);
  expect(JSON.stringify(res.body)).toContain('INVALID_SIGNATURE');
});
```

Fixtures are **sandbox captures**. Project/merchant ids inside them are examples;
signature verification only needs the raw bytes and the secret the handler runs with.

---

## Method 2 — Live tunnel (needs a human)

Xsolla will only POST to a **public HTTPS** URL. For local backends, expose the
webhook port with a quick tunnel (e.g. `cloudflared tunnel --protocol http2 --url http://localhost:4000`), then register that URL in Publisher Account.

`xsolla webhook listen` / `trigger` are offline only: nothing forwards Xsolla's real
deliveries to localhost, and no CLI command sets the webhook URL (CLI gaps).

**Ask the developer** to set the webhook **URL** in PA (secret + “webhooks on”
must already be done — see `SKILL.md` Prerequisites). Build the settings link from
`.env` (`merchant-setup`: `XSOLLA_MERCHANT_ID`, `XSOLLA_PROJECT_ID`):

```text
https://publisher.xsolla.com/{XSOLLA_MERCHANT_ID}/projects/{XSOLLA_PROJECT_ID}/edit/webhooks/store
```

Example after substituting from `.env`:

```text
https://publisher.xsolla.com/887981/projects/308077/edit/webhooks/store
```

Webhook URL to paste (replace with the live tunnel host):

```text
https://<tunnel-host>/xsolla/webhooks
```

(Use the path your app actually mounts.)

Then:

1. Developer saves the URL (+ secret already configured) in PA.
2. Agent (or developer) runs a **sandbox** purchase against the local shop.
3. Confirm in server logs / datastore: `user_validation`, then `order_paid` or
   `payment` per the table above, and that fulfillment ran once.
4. Optionally use PA’s webhook test button for a quick smoke, then a real
   sandbox payment for the full chain.

Tunnel URLs from free quick tunnels **change** when restarted — update PA each
time, or use a named/stable tunnel for longer sessions.

---

## When to use which

| Goal | Method |
|------|--------|
| Implement handler, signature, routing, idempotency | **`xsolla webhook trigger`** |
| `order_paid` / `order_canceled` / subscription / custom payloads | **Test-suite replay** (Method 1b) |
| Confirm Xsolla can reach the URL + real purchase chain | **Tunnel** (+ human for PA) |
| Regress after a handler change | `trigger` + test suite first; tunnel if delivery/geo/proxy is in doubt |
