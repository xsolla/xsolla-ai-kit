# Headless Checkout Initialization (Sandbox)

Guide for an AI agent helping a partner integrate Headless Checkout. Goal: install SDK, obtain a sandbox payment token
without touching the partner's backend, and show the first working UI.

> **Sandbox only.** Always pass `sandbox: true` in `headlessCheckout.init()`. Production token flow and go-live are
> covered by separate skills.

---

## Prerequisites

Load **`merchant-setup`** skill first. Partner must have:

- Publisher Account with a project
- `XSOLLA_MERCHANT_ID`, `XSOLLA_PROJECT_ID`, `XSOLLA_PROJECT_API_KEY` in `.env`

If credentials are missing — stop and complete merchant setup before continuing.

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

## Step 2: Get a Sandbox Payment Token (No Backend)

Payment token is **never generated in browser JavaScript**. For initial dev the partner does **not** implement a backend
endpoint yet. The agent generates a token on demand and passes it to the page.

### Token TTL

Default lifetime is **24 hours**. When the token expires, SDK calls fail — generate a new one and reload the page.
Remind the user to refresh periodically during dev.

### How to deliver the token to the page

Pick one (hardcoded constant is valid for dev only):

1. **URL query param** — `https://localhost:3000/checkout?token=PAYMENT_TOKEN`
2. **Hardcoded constant** — `const accessToken = '...'` in init code (replace when expired)

> Never commit real API keys or tokens to git.

### Which token method to use

Methods explained in `shop-setup` skill.

| Situation                            | Method                                      | Details                                    |
|--------------------------------------|---------------------------------------------|--------------------------------------------|
| **Default — no Store, no backend**   | **Method 3** — Merchant API                 | Simplest: amount + description, no catalog |
| Partner already has Store API + cart | Method 1 — `POST .../payment/cart/{cartId}` | See `shop-setup` skill                     |
| Partner has backend ready            | Method 2 — admin S2S                        | Production path — skip for now             |

**Method 3 — generate via curl (agent runs this):**

```bash
source .env

curl -s -X POST \
  -u "${XSOLLA_PROJECT_ID}:${XSOLLA_PROJECT_API_KEY}" \
  "https://api.xsolla.com/merchant/v2/merchants/${XSOLLA_MERCHANT_ID}/token" \
  -H 'Content-Type: application/json' \
  -d "{
    \"user\": {
      \"id\": { \"value\": \"dev_user_001\" },
      \"email\": { \"value\": \"test@example.com\" }
    },
    \"settings\": {
      \"project_id\": ${XSOLLA_PROJECT_ID},
      \"currency\": \"USD\",
      \"language\": \"en\",
      \"mode\": \"sandbox\"
    },
    \"purchase\": {
      \"checkout\": { \"amount\": 1.99, \"currency\": \"USD\" },
      \"description\": { \"value\": \"Dev sandbox test\" }
    }
  }"
```

Response: `{ "token": "..." }`. Extract `token` and pass it to the page.

More on token methods: `shop-setup`
skill, [How to get payment token](https://developers.xsolla.com/payment-ui-and-flow/payment-ui/how-to-get-payment-token/index.md), [Xsolla docs index](https://developers.xsolla.com/llms.txt).

---

## Step 3: Minimal SDK Integration

Target: **payment methods list visible on screen**. Only one form per page; `psdk-legal` and `psdk-total` are required
on checkout pages (not needed for methods-only first step).

```typescript
import {headlessCheckout} from '@xsolla/pay-station-sdk';

// Read token from URL or constant
const params = new URLSearchParams(window.location.search);
const accessToken = params.get('token') ?? 'PASTE_TOKEN_HERE';

async function bootstrap() {
    if (!accessToken) throw new Error('No token. Add ?token= to URL or paste token in code.');

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

Run dev server, open page with `?token=...`. **Success = payment methods list renders without errors.**

---

## Step 4: Verify Sandbox Works

1. Open browser DevTools — no SDK init errors
2. Payment methods list is visible
3. Select a method — `selectionChange` fires in console

**Next milestone (separate task):** add credit card form components.

---

## Anti-Patterns (Dev Phase)

1. **Do not** put API keys in frontend code — only the payment token goes to the browser.
2. **Do not** implement backend token endpoint yet — that is the production skill.
3. **Do not** set `sandbox: false` during initial setup.
4. **Do not** skip token refresh — expired token looks like an SDK bug.
5. **Do not** use Method 1 (cart) without a real Store catalog and cart — use Method 3 instead.
6. **Do not** write integration code before the SDK is installed and loadable — a finished handler against a missing
   `headlessCheckout` / `PayStationSdk` only looks done.
7. **Do not** skip `npm install` and load the SDK from a CDN as the primary path — install from npm even with no
   bundler, then serve the prebuilt `dist/main.js`.

---

## Checklist

- [ ] Credentials in `.env` (merchant-setup done)
- [ ] `@xsolla/pay-station-sdk` installed via npm (even with no bundler)
- [ ] SDK actually loads on the page — `import` resolves, or `window.PayStationSdk` is defined (gate before any code)
- [ ] Sandbox token generated (Method 3 curl or API Try it)
- [ ] Token passed via `?token=` or hardcoded constant
- [ ] `headlessCheckout.init({ sandbox: true })` + `setToken()` called
- [ ] `psdk-payment-methods` renders on page
- [ ] User reminded: token expires in ~24h, refresh when needed
