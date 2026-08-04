# Payment country

Guide for an AI agent. Goal: wire **payment country** so the method list and
`form.init` use the correct ISO — and, when minting the payment token via
**Store API Method 2** (`shop-setup`: server → `store.xsolla.com`), include
`X-User-Ip` or `user.country.value` so the call succeeds and Xsolla can detect
country.

**Prerequisite:** Phase 2 done (`payment-methods-list`). Prefer Phases 3–6 in place.

**Payment country ≠ UI language.** Country is an ISO (`US` / `JP`). Language is
`init({ language: 'ja' })` — different knob.

---

## Token strategy — two paths (ask which fits)

```
Does the host site already decide / confirm the buyer’s country
(account profile, shipping, locale, mature store selector)?
├── YES → Path T1 (mature site): pass that ISO as user.country.value
│         (+ allow_modify: true if the checkout may still override it)
└── NO  → Path T2 (greenfield / AI shop): do NOT invent MaxMind / geo on the
          partner backend. Omit country.value; let Xsolla detect from IP.
          For Store Method 2 you MUST send X-User-Ip (see below).
```

Building a full GeoIP stack on day one of a from-scratch shop is **overkill**.
Xsolla already does geo. Your job is to give it a real client IP (or an explicit
ISO when the site already has one).

---

## Store token Method 2 — `X-User-Ip` or `country.value`

Token methods are listed in `shop-setup`. This section applies when the partner
backend mints the token with **Method 2**:

`POST https://store.xsolla.com/api/v3/project/{id}/admin/payment/token`

Xsolla requires **one of**:

- header **`X-User-Ip`** = buyer’s public IP, or
- body **`user.country.value`** = ISO (e.g. `US`, `JP`)

Without either, the API returns **422** (`[0401-1102]`).

Notes:

- **Method 1** (browser → Store cart/order with the user JWT) sees the buyer’s IP
  on the connection — no special header from your backend.
- **Method 3** (Merchant API) does not require these fields for minting; country
  is resolved later. That is not a reason to prefer Method 3 when the shop uses
  a Store catalog — use Method 1 or 2.
- Method 2 is server-to-server: the TCP peer is your backend (or its egress), not
  the browser. Forward the buyer IP as `X-User-Ip` (Path T2) or set
  `country.value` (Path T1).

### Canonical greenfield token body (Path T2)

```json
{
  "user": {
    "id": { "value": "user-id" },
    "country": { "allow_modify": true }
  }
}
```

- **Omit `country.value`.**
- **`allow_modify: true` is mandatory** if the store has (or will have) a country
  selector. Without it, Xsolla locks the session and the selector is a no-op.
- **Always set `X-User-Ip`** on the Method 2 request to the buyer’s public IP.

### Mature-site token body (Path T1)

```json
{
  "user": {
    "id": { "value": "user-id" },
    "country": {
      "value": "JP",
      "allow_modify": true
    }
  }
}
```

Use the site’s already-chosen ISO. Keep `allow_modify: true` if checkout may
override. Still prefer sending `X-User-Ip` when available.

**Do not** hardcode `"value": "US"` just to satisfy the API.

---

## Resolving the buyer IP for `X-User-Ip`

The app almost never sees the WAN client on the TCP socket:

```
Browser → CDN / LB / nginx → app
         ↑ real client IP      ↑ peer = proxy (or 127.0.0.1 on localhost)
```

1. Edge puts the client IP in `X-Forwarded-For`, sometimes `X-Real-IP`,
   `CF-Connecting-IP`, `Fastly-Client-IP`, …
2. Backend **reads** a trusted header (only if clients cannot bypass the proxy).
3. Backend sends that IP to Store Method 2 as `X-User-Ip`.
4. Xsolla uses it to detect the buyer’s country for the payment session.

**Ask the user what sits in front of the token backend** (nginx, Cloudflare,
Firebase Hosting → Cloud Run, bare Node, PHP-FPM, …). Config lives outside the
app repo more often than inside it.

| Stack | Typical source of client IP |
|-------|-----------------------------|
| Bare Node / Express (no proxy) | `req.socket.remoteAddress` / `req.ip` |
| nginx → Node/PHP | `X-Real-IP` or first public hop in `X-Forwarded-For` (nginx must set it) |
| Cloudflare | `CF-Connecting-IP` (or leftmost public `X-Forwarded-For`) |
| Firebase Hosting / Fastly → Cloud Run | **`Fastly-Client-IP`** (prefer this). `X-Forwarded-For` often ends with the CDN hop — do not treat Cloud Run egress / ipify as the buyer. |
| Google Cloud Run / GFE (direct, no Hosting) | `X-Forwarded-For` (leftmost public hop) + Express `trust proxy` |

Never trust client-supplied “my IP” body fields in production — spoofable.
Observed request IP (via trusted proxy headers) is the rule.

### Localhost / private peer (dev)

`browser → 127.0.0.1 → local API` has **no** public client IP on the connection.
Store Method 2 then 422s if you send neither `country.value` nor a public
`X-User-Ip`.

For **dev only**, pick one:

1. **`XSOLLA_DEV_USER_IP=<public IPv4>`** in server env (explicit), or
2. When the observed peer is loopback/RFC1918, **resolve the machine’s egress
   public IP** once (e.g. `https://api.ipify.org`) and cache it — on localhost the
   browser and API share the same NAT, so egress ≈ buyer IP, or
3. Drive the SPA through the same public tunnel as the API so the edge stamps a
   real connecting IP.

Do **not** use the egress-IP fallback on production when headers are merely
misconfigured — fix the proxy instead. Calling a “what is my IP” service from
the **server** (ipify etc.) returns the **server’s** egress address (e.g. Cloud
Run NAT), not the buyer’s — that is a common prod bug when Hosting headers are
missing and the code “helps” by looking up an egress IP.

---

## SDK side — when to pass ISO into methods

Same as before: detection is the default; the selector is the override.

| Moment | Pass `country` to `getRegularMethods` / `getQuickMethods` / `form.init`? |
|--------|--------------------------------------------------------------------------|
| First visit, no stored choice | **No** — omit; Xsolla uses token/session country |
| Selector shows `currentCountry` (display only) | **No** |
| Buyer picks a country (or persisted pick) | **Yes** — that ISO |

```typescript
// Default (no override):
await headlessCheckout.getQuickMethods();
await headlessCheckout.getRegularMethods();
await headlessCheckout.form.init({ paymentMethodId, returnUrl });

// After explicit / persisted pick e.g. 'JP':
await headlessCheckout.getQuickMethods('JP');
await headlessCheckout.getRegularMethods({ country: 'JP' });
await headlessCheckout.form.init({ paymentMethodId, returnUrl, country: 'JP' });
```

Call `getCountryList()` only **after** `setToken()`. Use `currentCountry` to
**preselect the UI** — not as a forced SDK override on first paint.

---

## Choose UI path

```
Does the store already have a country selector (header, account, shipping, locale)?
├── Yes → Keep it. On change, pass ISO into methods + form.init. No second country UI.
└── No  → Build a store-styled control from getCountryList() (below).
```

### Store already has a selector

```typescript
async function onStoreCountryChange(country: string) {
  document.querySelector('psdk-payment-methods')?.setAttribute('country', country);
  // Or custom list: getRegularMethods / getQuickMethods with { country }, then form.init({ …, country })
}
```

### No store selector — build one

Do **not** use a native HTML `<select>` or SDK chrome for the picker.

1. After `setToken()`, `getCountryList()` → `{ countryList, currentCountry }`.
2. Reuse an existing store combobox if one exists; else build searchable combobox.
3. Place it **at the top** of the method chooser (dropdown opens downward).
4. Preselect `currentCountry` (or persisted ISO) in the UI.
5. Load methods **without** `country` unless a persisted/explicit ISO exists.
6. On change: persist, reload methods **with** that ISO, reset any open form,
   pass the same ISO into later `form.init`.

```typescript
await headlessCheckout.init({ isWebView: false, sandbox: true, theme: 'default' });
await headlessCheckout.setToken(accessToken);

const { countryList, currentCountry } = await headlessCheckout.getCountryList();
const storedIso = readPersistedCountry(); // localStorage / cookie, or null

let paymentCountry =
  storedIso && countryList.some((c) => c.ISO === storedIso)
    ? storedIso
    : (currentCountry || 'US');

let countryOverride =
  storedIso && countryList.some((c) => c.ISO === storedIso) ? storedIso : null;

const quick = countryOverride
  ? await headlessCheckout.getQuickMethods(countryOverride)
  : await headlessCheckout.getQuickMethods();
const regular = countryOverride
  ? await headlessCheckout.getRegularMethods({ country: countryOverride })
  : await headlessCheckout.getRegularMethods();

async function onCountryChange(country: string) {
  paymentCountry = country;
  countryOverride = country;
  persistPaymentCountry(country);
  // reload methods with { country }; reset open form
}

await headlessCheckout.form.init({
  paymentMethodId,
  returnUrl: 'https://yourstore.com/payment/return',
  ...(countryOverride ? { country: countryOverride } : {}),
});
```

Persist on user change when **you** built the selector. Restored ISO **is** an
override. First visit: no persist → omit `country` in SDK calls.

---

## Unsupported / blocked country

`onNextAction` may emit `show_errors`. Show `error.code` + `error.message`.
See [unsupported-country](https://raw.githubusercontent.com/xsolla/pay-station-sdk/refs/heads/main/examples/unsupported-country/index.html).

---

## Testing

### Agent can check (code / wiring)

1. Token body for greenfield: `user.country.allow_modify: true` and **no**
   `user.country.value`. For Path T1, `country.value` matches the site’s chosen ISO.
2. If the shop uses Store **Method 2**, the request sends a public buyer IP as
   `X-User-Ip` (or sets `country.value`). A missing both → expect **422** /
   `1102` — treat that as a fail, not a reason to switch token methods.
3. SDK: first visit (clear storage) — selector shows `currentCountry`; method
   fetch is called **without** a country argument.
4. SDK: pick `JP`, then `US` — visible method lists **differ**; later `form.init`
   includes the chosen ISO. Persist + reload restores the pick (when the store
   owns the selector).

### Human-only — tell the developer

Auto-detect from IP **cannot** be verified by the agent alone: it needs a
**deployed** (or publicly reachable) backend so the edge stamps a real client IP,
and a way to **change that IP** (VPN / different network). Localhost often fakes
or shares NAT with the server and is not enough.

Ask the developer to:

1. Open checkout on the **real host** (staging/prod behind the same CDN/proxy as
   production), not only `localhost`.
2. Confirm the country selector’s default (`getCountryList().currentCountry` /
   preselected UI) matches their **actual** location — or matches the site’s
   Path T1 country if the site already sets one.
3. Connect a **VPN** (or another network) in a different country, hard-refresh
   (or clear the payment-country cookie / localStorage if the store persists a
   pick), open checkout again — the **detected** default country should change.
   If Path T1 forces a fixed ISO, skip this step; the forced ISO should stay.
4. With Method 2: if country stays wrong or stuck on a default (e.g. always US),
   the backend is probably forwarding the **server** IP (or nothing usable). Fix
   proxy headers / `X-User-Ip` — do not hardcode `country.value: "US"`.

**Done when** token minting succeeds with the chosen Method 1/2/3 rules, the
selector reflects detection or Path T1 correctly, an explicit pick overrides
methods + `form.init`, and (for a from-scratch selector) the pick survives
reload. Geo/IP detection is signed off by the developer on a real host ± VPN.

---

## Anti-patterns

1. **Do not** hardcode `user.country.value: "US"` to “make Store API work.”
2. **Do not** omit `allow_modify: true` when a selector exists.
3. **Do not** call Store Method 2 without `X-User-Ip` or `country.value` — fix the
   422 instead of switching to Method 3.
4. **Do not** pass `country` into methods / `form.init` on first paint only because
   you mirrored `currentCountry` into the UI.
5. **Do not** call `getCountryList()` before `setToken()`.
6. **Do not** change country without resetting an open form.
7. **Do not** confuse `country` with `language` (`JP` vs `ja`).
8. **Do not** use a bare native `<select>` — match the store; prefer searchable.
9. **Do not** put the country control at the bottom of the viewport.
10. **Do not** trust a browser-posted IP string in production; use proxy-observed IP.
11. **Do not** skip asking what reverse proxy / CDN sits in front of the token API.
