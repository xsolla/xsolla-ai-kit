# Headless Checkout Initialization (Sandbox)

Guide for an AI agent helping a partner integrate Headless Checkout. Goal: install SDK, obtain a sandbox payment token
from a small dev-only token route on the partner's backend, and show the first working UI.

> **Sandbox only.** Always pass `sandbox: true` in `headlessCheckout.init()`. Production token flow and go-live are
> covered by separate skills.

---

## Prerequisites

The CLI preflight in `SKILL.md` → Prerequisites passes (CLI installed, `merchant_id` /
`project_id` set, Store key probe prints `exit=0`). If not, hand off to **`merchant-setup`**.

Step 2's dev token route needs the backend key in `.env`. Check without printing it:

```bash
grep -c '^XSOLLA_PROJECT_API_KEY=' .env 2>/dev/null   # 1 = present
```

`0` or no `.env` → run `merchant-setup` Step 5. It writes `XSOLLA_MERCHANT_ID` and
`XSOLLA_PROJECT_ID`, and mints `XSOLLA_PROJECT_API_KEY` straight into `.env`. The developer's
production token backend needs the same key later. Never ask the user to paste a key.

---

## Step 1: Install SDK

**Always install from npm — this step is not optional and there is no CDN-only shortcut:**

```bash
npm install --save @xsolla/pay-station-sdk
```

Install it **even if the project has no bundler.** Do not pull the SDK straight from a CDN as the primary path, and do
**not** start writing integration code before the SDK is installed and actually loadable on the page — that is the most
common mistake (a finished handler that references an SDK that was never wired up). See the **gate** below.

### How the SDK is consumed — two modes

The package ships **both** an ES module (for bundlers) and a prebuilt UMD bundle (`dist/main.js`, global
`PayStationSdk`). Pick by whether the project has a JS build step — this is framework-agnostic, not tied to any CMS:

| Project has…                                  | How to load                                                                                              |
|-----------------------------------------------|----------------------------------------------------------------------------------------------------------|
| **A bundler** (Vite, webpack, Next, CRA, etc.)| `import { headlessCheckout } from '@xsolla/pay-station-sdk'`                                              |
| **No bundler** (plain HTML, server-rendered)  | Still `npm install`, then include the prebuilt UMD bundle `node_modules/@xsolla/pay-station-sdk/dist/main.js` via a `<script>` tag (copy/serve it as a static asset). Use the global: `const { headlessCheckout } = PayStationSdk;` |

**Framework notes:**

| Framework             | Extra setup                                                              |
|-----------------------|--------------------------------------------------------------------------|
| React / Vue / vanilla | Import `headlessCheckout` from `@xsolla/pay-station-sdk`                 |
| Angular               | Add `CUSTOM_ELEMENTS_SCHEMA` to the component that renders `psdk-*` tags |
| No build step         | Serve `dist/main.js` from `node_modules` (or copy into your assets); use global `PayStationSdk` |

### Gate — verify before writing integration code

Do not proceed to Step 2 until the SDK actually loads in the running page:

- **Bundler:** the `import { headlessCheckout }` resolves at build time (no unresolved-module error).
- **No bundler:** `window.PayStationSdk` is defined after the `<script>` runs — the bundle must be enqueued/included
  **before** your handler executes.

If the SDK isn't loadable yet, fix that first; integration code written against a missing SDK only looks done.

## Reference implementations

### select-method (minimal)

Direct URL — readable via web_fetch:
`https://raw.githubusercontent.com/xsolla/pay-station-sdk/refs/heads/main/examples/select-method/index.html`

### headless-checkout-demo (full React + Vite)

The most complete reference — React + TypeScript + Vite, every payment method. Requires cloning the repo locally and
linking it to the agent. See `demo-install.md`.

---

## Step 2: Get a Sandbox Payment Token (dev token route)

Payment token is **never generated in browser JavaScript**, and the agent does not mint it with the CLI either (see
[CLI gaps](#cli-gaps)). The developer's **backend** mints it: add one small, sandbox-only server route that reads
`.env` and calls the Merchant API token endpoint with `settings.mode: "sandbox"`. The page fetches the token from that
route at startup, so the API key never leaves the server and the token never passes through the agent's transcript.
A sandbox token creates no order and charges nothing.

This route is a dev stand-in, not the production token backend. It hardcodes a test user and `mode: "sandbox"`; the
real endpoint (authenticated user, Store Method 1/2) comes later — see `shop-setup` and `production`.

### Which token method to use

Methods explained in `shop-setup` skill.

| Situation                            | Method                                      | Details                                    |
|--------------------------------------|---------------------------------------------|--------------------------------------------|
| **Default — no Store, early dev**    | **Method 3** — Merchant API, from the dev route below | Simplest: amount + description, no catalog |
| Partner already has Store API + cart | Method 1 — `POST .../payment/cart/{cartId}` | Client code; see `shop-setup` skill        |
| Partner has backend ready            | Method 2 — admin S2S, with `"sandbox": true` in the body | Backend code (REST) — skip for now  |

### Method 3 — the dev token route (developer's backend code)

Code the developer ships, so it uses REST, not the CLI. Express shown; put the same handler in whatever server the
project has (Next API route, Vite `configureServer` middleware, PHP, …) — anything server-side that can read `.env`.

```js
// POST /api/payment-token — SANDBOX ONLY. Reads XSOLLA_* from .env (merchant-setup Step 5).
app.post('/api/payment-token', async (req, res) => {
  if (process.env.NODE_ENV === 'production') return res.sendStatus(404);
  const { XSOLLA_MERCHANT_ID: mid, XSOLLA_PROJECT_ID: pid, XSOLLA_PROJECT_API_KEY: key } = process.env;
  const r = await fetch(`https://api.xsolla.com/merchant/v2/merchants/${mid}/token`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: 'Basic ' + Buffer.from(`${pid}:${key}`).toString('base64'),
    },
    body: JSON.stringify({
      user: { id: { value: 'dev_user_001' }, email: { value: 'test@example.com' } },
      settings: { project_id: Number(pid), currency: 'USD', language: 'en', mode: 'sandbox' },
      purchase: { checkout: { amount: 1.99, currency: 'USD' }, description: { value: 'Dev sandbox test' } },
    }),
  });
  if (!r.ok) return res.status(502).json({ error: `token request failed: HTTP ${r.status}` });
  const { token } = await r.json();
  res.json({ token });
});
```

- Load `.env` into the server process (`node --env-file=.env`, `dotenv`, or the framework's own loader).
- Never log the key or the token on the server, and never return the key to the client.
- `401` from Xsolla → the key in `.env` is missing, rejected or revoked: run `merchant-setup` Step 5 (it mints a new
  one into `.env`). Never ask the user to paste one.
- Saved methods (Phase 6): keep the same `user.id` across tokens, or saved methods won't show up.
- Payment country (Phase 7): to test another country, add `country: { value: 'JP', allow_modify: true }` to `user`.

**Agent check.** Start the dev server, then send `POST /api/payment-token` from a short script and print only the HTTP
status and the token's **length**, never the value. `200` with a non-empty `token` = route works.

### Token TTL

Default lifetime is **24 hours**. Because the page fetches a fresh token on each load, a reload is enough. A token
pasted into a URL by hand still expires — an expired token looks like an SDK bug.

### How to deliver the token to the page

1. **Fetch from the dev route (default)** — the page calls `POST /api/payment-token` before `setToken()` (Step 3).
2. **URL query param** — `?token=…` is what the return page receives after a redirect (`credit-card-form`,
   `redirect-flow`); Step 3 reads it first, then falls back to the route.

> Never commit API keys or tokens to git, and never hardcode a token in a tracked source file.

### CLI gaps

The agent can't mint a sandbox payment token through the CLI today. Don't work around these with a raw API call from
the agent, and don't run either command without `--dry-run`.

| Need | Status | Do instead |
|---|---|---|
| Sandbox token via `xsolla payments create-token` | Refuses to run without an exported `XSOLLA_API_KEY` (exit `1`, *"Missing required credentials … XSOLLA_API_KEY"*); it never reads the keychain key, and the contract forbids that env var | Mint through the developer's dev token route above |
| Sandbox token via `xsolla webshop admin-create-payment-token` | Works with the keychain key but has no sandbox: `--sandbox` *"has no effect"*, and no flag sets the body's `sandbox` field. Every token is **live** and creates an unpaid order on the live project | Never run it for testing. The backend's own Method 2 call sends `"sandbox": true` |
| Apple Pay instant-flow certificate check | No command | See `apple-pay` §6 |

More on token methods: `shop-setup`
skill, [How to get payment token](https://developers.xsolla.com/payment-ui-and-flow/payment-ui/how-to-get-payment-token/index.md), [Xsolla docs index](https://developers.xsolla.com/llms.txt).

---

## Step 3: Minimal SDK Integration

Target: **payment methods list visible on screen**. Only one form per page; `psdk-legal` and `psdk-total` are required
on checkout pages (not needed for methods-only first step).

```typescript
import {headlessCheckout} from '@xsolla/pay-station-sdk';

// Token from the URL (return page) or from the dev token route (Step 2)
async function getToken() {
    const fromUrl = new URLSearchParams(window.location.search).get('token');
    if (fromUrl) return fromUrl;
    const r = await fetch('/api/payment-token', { method: 'POST' });
    return r.ok ? (await r.json()).token : null;
}

async function bootstrap() {
    const accessToken = await getToken();
    if (!accessToken) throw new Error('No token. Is the dev token route (Step 2) running?');

    await headlessCheckout.init({
        sandbox: true,       // required for dev
        isWebView: false,
        language: 'en',
    });

    await headlessCheckout.setToken(accessToken);

    // Optional: log selected method
    document.querySelector('psdk-payment-methods')
        ?.addEventListener('selectionChange', (e) => console.log(e.detail));
}

bootstrap();
```

```html

<psdk-payment-methods country="US"></psdk-payment-methods>
```

Run the dev server (with the token route) and open the page. **Success = payment methods list renders without errors.**

---

## Step 4: Verify Sandbox Works

1. Open browser DevTools — no SDK init errors
2. Payment methods list is visible
3. Select a method — `selectionChange` fires in console

**Next milestone (separate task):** add credit card form components.

---

## Anti-Patterns (Dev Phase)

1. **Do not** put API keys in frontend code — only the payment token goes to the browser.
   Don't ask the user for a key either, and don't `export XSOLLA_API_KEY` (it overrides the CLI's keychain key).
2. **Do not** build the production token endpoint yet — the Step 2 route is sandbox-only; the real one comes later.
   **Do not** mint test tokens with `xsolla payments create-token` or `xsolla webshop admin-create-payment-token`
   (see CLI gaps: the first needs an env key, the second mints live tokens).
3. **Do not** set `sandbox: false` during initial setup.
4. **Do not** skip token refresh — expired token looks like an SDK bug.
5. **Do not** use Method 1 (cart) without a real Store catalog and cart — use Method 3 instead.
6. **Do not** write integration code before the SDK is installed and loadable — a finished handler against a missing
   `headlessCheckout` / `PayStationSdk` only looks done.
7. **Do not** skip `npm install` and load the SDK from a CDN as the primary path — install from npm even with no
   bundler, then serve the prebuilt `dist/main.js`.

---

## Checklist

- [ ] CLI preflight passes, and `XSOLLA_PROJECT_API_KEY` is in `.env` (`merchant-setup` Step 5); no key pasted
- [ ] `@xsolla/pay-station-sdk` installed via npm (even with no bundler)
- [ ] SDK actually loads on the page — `import` resolves, or `window.PayStationSdk` is defined (gate before any code)
- [ ] Dev token route (`POST /api/payment-token`, `mode: sandbox`) returns 200 + a token (checked by length, never printed)
- [ ] Page fetches the token from the route (or `?token=` on the return page)
- [ ] `headlessCheckout.init({ sandbox: true })` + `setToken()` called
- [ ] `psdk-payment-methods` renders on page
- [ ] User reminded: token expires in ~24h; a reload fetches a fresh one
