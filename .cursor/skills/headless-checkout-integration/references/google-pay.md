# Google Pay for Headless Checkout

Guide for an AI agent. You are adding **one** payment method — Google Pay — to a
Headless Checkout. Apple Pay is a separate entity with its own skill
(`apple-pay.md`); do not try to wire both at once.

## The one rule that makes this work

> **Google Pay is NOT a bespoke screen.** It flows through the **same shared
> `form.init()` + `onNextAction` dispatcher** as every other method. If you build a
> dedicated Google Pay screen that only waits for `special_button`, you WILL fail —
> because on Google Pay flow Headless Checkout SDK could emit a `show_fields` (ZIP) step **before** the
> button, and a bespoke path silently drops it and the button never appears.

Google Pay is a thin entity: it initializes its method and contributes **one**
action to the shared dispatcher — `special_button` → render the Google Pay button.
The ZIP step, redirects and status are handled by the shared base, like any method.

---

## 0. Prerequisites

1. SDK initialized (`init()` + `setToken()` succeed) and a **shared NextAction
   dispatcher** in place — the base `onNextAction` handler that renders
   fields (→ components + `form.activate()`), handles `redirect`, and
   mounts `psdk-status`. If it doesn't exist yet, the `headless-checkout-integration`
   skill stands it up via the credit-card method (easiest to test); Google Pay then
   reuses the same dispatcher untouched.
2. A **payment access token** for the order.

Payment method ID: Google Pay `3431`. Prefer discovering the ID via SDK (see the
`payment-methods-list` skill) over hardcoding.

---

## 1. Mental model (Google Pay specific)

### 1.1 NextActions specific

| NextAction | When | You do |
|---|---|---|
| `show_fields` | **US** regular flow: a ZIP-code step before the button | render fields + submit button |
| `special_button` | device is ready to pay | `data.buttonName === 'google-pay'` → mount `<psdk-google-pay-button>` |

`special_button` is emitted **only for Google Pay** (`SpecialButtonName.googlePay =
'google-pay'`) and **only when the device can pay**. Apple Pay never emits it.

### 1.2 Instant vs regular flow

Google Pay has two flows. The same button drives both — the difference is **where the
buyer's ZIP / contact data is collected** and how many steps come before the button.

- **Instant flow (one-click).** Clicking the Google Pay button opens Google's native
  sheet immediately; the buyer picks a card and confirms, and ZIP / contact data is
  collected **inside Google's sheet**. In NextAction terms: after `form.init` the SDK
  goes (near-)straight to `special_button` → you render the button → tap → native
  sheet → done. Fewer steps, better conversion — this is what you want in production.
- **Regular flow.** Before the button, the SDK asks *your* form to collect the data:
  it emits `show_fields` (in the US this is the **ZIP** step), the buyer fills it and
  hits submit, and only then does `special_button` fire and the button appear. So the
  sequence is `show_fields` (ZIP) → submit → `special_button` → button → native sheet.

| | Instant (one-click) | Regular |
|---|---|---|
| ZIP / contact data | collected **inside** the Google sheet | collected by **your form** (`show_fields`) |
| Steps before the button | none | a `show_fields` step + submit |
| Client flag | `isGooglePayInstantFlowEnabled: true` | omit it (or `false`) |
| Extra requirements | backend toggle on **+** `allow="payment"` reaches the payment iframe (no domain cert, unlike Apple) | none |
| Converts | better | baseline |

**Enabling instant is not just the client flag — three things must line up:**

1. **Client flag** — set `isGooglePayInstantFlowEnabled: true` in `init()` (full init
   in §2):

   ```js
   await headlessCheckout.init({
     // …other options
     isGooglePayInstantFlowEnabled: true, // ← selects the instant flow
   });
   ```

2. **`allow="payment"` must reach the wallet iframe.** The instant sheet uses the
   browser Payment Request API, which the browser blocks unless the hosting frame is
   permitted. The SDK already sets `allow='payment'` on its **own** wallet iframe, so
   out of the box this is handled. **But if you open the SDK inside your own
   `<iframe>`** (the SDK nested one level down), that **outer** iframe must also carry
   `allow="payment"` — otherwise instant silently falls back to the regular flow:

   ```html
   <!-- ONLY needed when YOU wrap the SDK in your own iframe -->
   <iframe src="https://your-site.com/checkout" allow="payment"></iframe>
   ```

3. **Backend toggle — usually already on.** The project's instant-flow toggle now
   **defaults to `true`**, so on a normal project the client flag fully controls
   instant on/off and you do nothing on the backend. Only if instant refuses to work
   despite the flag *and* `allow="payment"` is the toggle set to **`false`** for that
   project — then the partner submits a **Support Hub request** to have an Integration
   Manager flip it on. Unlike Apple Pay, Google Pay needs **no** domain-association
   certificate. (Ref: Confluence *"Enabling instant Apple Pay & Google Pay for
   Partners"*.)

**The backend toggle overrides the client flag only when it's off.** With the toggle
**on** (the default) your flag *selects* instant; with it **off** the flag can't force
instant and you get the ZIP step. So a ZIP step where you expected instant means the
toggle is off for that project — a **config** fact, not a code bug, and your
`show_fields` handler already covers it.

### 1.3 Environment

Google Pay works almost everywhere — all mainstream browsers on desktop, Android and
iOS ([Google's list](https://developers.google.com/pay/api/web/guides/setup): Chrome,
Firefox, Safari, Edge, Opera, UC Browser). The **button itself changes behavior** by
environment (native sheet in Chrome, a popup browser tab elsewhere), so you don't
adapt to that — mount the button and let it decide.

Do **not** write your own capability detection to decide whether to show the button.
The SDK decides where Google Pay is available and renders (or removes, §5) its own
button accordingly — mount it everywhere and let the SDK gate.

**Sandbox:** Google provides **test cards** in the native sheet — no real card needed.
For an AI agent, **test in Chrome** (that's where the button and native sheet behave
most predictably).

---

## 2. Initialize (once)

```js
const { headlessCheckout } = PayStationSdk; // or: import { headlessCheckout } from '@xsolla/pay-station-sdk'

await headlessCheckout.init({
  sandbox: true,                        // false in production
  isWebview: false,                     // ⚠️ lowercase "v" — see §7
  theme: 'default',
  language: 'en',
  isGooglePayInstantFlowEnabled: true,  // selects instant IF the backend toggle allows; safe to leave on
});

await headlessCheckout.setToken(accessToken); // ⚠️ BEFORE any form.init()
```

---

## 3. The Google Pay entity

The dispatcher below is method-agnostic — it is the shared base every method uses.
Google Pay contributes exactly two things to it: the `special_button` case and the
button that case mounts.

```js
const host = document.querySelector('#form-container'); // the ONE host container
let googleButtonRendered = false;

headlessCheckout.form.onNextAction(handleNextAction); // subscribe ONCE, before any form.init

// ── Shared base dispatcher — the same for every payment method ───────────────
function handleNextAction(a) {
  switch (a.type) {
    case 'show_fields':                 // server-driven fields (incl. the GP-US ZIP step)
      renderFields(a.data.fields);
      break;
    case 'special_button':              // Google-Pay-specific action → render its button
      if (a.data.buttonName === 'google-pay') renderGooglePayButton();
      break;
    case 'redirect':      handleRedirect(a.data.redirect); break; // 3DS-redirect / e-wallet
    case '3DS':           mount3ds(a.data.data); break;
    case 'show_errors':
    case 'server_error':  showError(a.data.errors?.[0]?.message ?? 'Payment error'); break;
    case 'check_status':  showStatus(); break;   // all paths converge here → psdk-status
  }
}
// renderFields / handleRedirect / mount3ds / showError / showStatus are the shared
// base helpers — method-agnostic. renderFields maps each field → its psdk-* component,
// appends <psdk-submit-button>, then calls headlessCheckout.form.activate().

// ── Google Pay entity — its own module: owns the PID, init, and its button ───
// example have hardcoded PID, in real app need to use SDK methods to get PIDs
const GOOGLE_PAY_PID = 3431;

async function initGooglePay() {
  googleButtonRendered = false;
  host.innerHTML = '';
  const form = await headlessCheckout.form.init({
    paymentMethodId: GOOGLE_PAY_PID,
    // Keep the FULL current URL + token — never strip the query (return-page rule).
    returnUrl: `${location.origin}${location.pathname}?token=${accessToken}`,
  });
  // special_button can fire during the await; don't clobber the button if it did.
  requestAnimationFrame(() => {
    if (!googleButtonRendered) renderFields(form.fields || []);
  });
}

function renderGooglePayButton() {
  googleButtonRendered = true;
  host.innerHTML = '';                            // remove the ZIP fields / submit button
  const btn = document.createElement('psdk-google-pay-button'); // or new GooglePayButtonComponent()
  btn.setButtonColor('black');                    // 'white' | 'black' | 'default' — call BEFORE append
  host.appendChild(btn);
}
```

The submit button that `renderFields` appends is what advances the ZIP step to
`special_button` — Google Pay needs it in the DOM even though the user ultimately
pays via the wallet button, not the submit button.

`redirect` data shape: `a.data.redirect = { redirectUrl, data, method, ... }`. The
reference demo appends `data.redirect.data` as query params onto `redirectUrl`
before `window.location.href = url`. **Do not drop the `redirect` case** — 3DS /
bank-redirect Google Pay payments hang without it.

---

## 4. Button color

`psdk-google-pay-button` / `GooglePayButtonComponent` exposes
`setButtonColor('white' | 'black' | 'default')`. Match your theme (dark UI → white).
Call it **before** appending the element.

---

## 5. "The button appeared and vanished" — expected, not a bug

The SDK **removes its own Google Pay button** when the device turns out not ready
(e.g. a headless browser with no wallet). Do **not** race it with a timeout that
prints "Google Pay unavailable" — that fires while readiness is still resolving and
produces false negatives. If you must detect not-ready, check `!btn.isConnected` a
beat after mounting, never a fixed timer.

The "pick method, then tap the real Google button" two-step is also inherent:
browsers require a **direct user gesture on Google's own button** to open the native
sheet — you cannot auto-trigger it. Make the first step read as *selection* (a
method row), not a lookalike pay button, and it stops feeling redundant.

---

## 6. Pitfalls (each cost real time — don't repeat them)

| ⚠️ | Trap | Do instead |
|---|---|---|
| **Bespoke wallet path** | A separate GP screen that only awaits `special_button` | One shared NextAction dispatcher across all methods; GP just adds `special_button` |
| **Dropping `show_fields`** | GP-US never shows its button (the ZIP step is skipped) | Handle `show_fields` → render fields + submit in the shared dispatcher |
| **Capability gating** | Your own `isReadyToPay`/UA checks hide the button | Never gate — render it and let the SDK decide |
| **`isWebView` casing** | The interface field is `isWebview` (lowercase v); capital-V is silently ignored | Use `isWebview` |
| **Forgetting `redirect`** | 3DS / bank-redirect GP payments hang | Handle `redirect` in the shared dispatcher (`data.redirect.redirectUrl` + append `data.redirect.data`) |
| **Premature timeout** | "GP unavailable" fires before readiness resolves | No racing timer; the SDK removes its own button when truly not ready |
| **Forcing instant from client** | Expecting the flag to override a project toggle set to off | Toggle defaults on; if instant won't work despite the flag, request enabling it via Support Hub |
| **`setToken` after `form.init`** | Form init fails | `setToken()` first, then `form.init()` |
| **Hardcoding the PID blindly** | Wrong id on projects where it differs | Prefer `getQuickMethods()` to discover it; `3431` is the sandbox default |

---

## 7. Testing — what an AI agent CAN and CANNOT do

**An AI agent cannot complete a Google Pay transaction.** The native Google Pay
sheet is a **browser surface outside the page DOM**; a headless browser can't see
or drive it and has no signed-in wallet. **Do not loop on Playwright trying to
finish the payment** — that is the endless-cycle trap.

What the agent **can and should** verify (this is the whole automated acceptance):

| Check | How |
|---|---|
| Already-integrated methods still complete end-to-end | regression check — e.g. drive the card method through `psdk-status` (see the integration skill) |
| Method chooser renders Google Pay | assert the row/method exists |
| Google Pay reaches the right action | **Chromium**: pick Google → assert either the **ZIP `show_fields`** renders (regular, US) *or* `special_button` fires and `<psdk-google-pay-button>` mounts |

Then **hand the native sheet to a human** — it won't open in the agent's headless
browser, and even if it did it's outside the page DOM. Ask the user to run the
sandbox flow in real **Chrome** (test **US** for the ZIP step and **DE** without it;
sandbox has Google test cards) and report back. Report "button mounts" as the ceiling
of what you verified — never claim a payment success you could not observe.

---

## 8. Sources

- **docs**: https://developers.xsolla.com/sdk-fuctional-and-ui/headless-checkout/payment-methods/google-pay/index.md
(note: the docs omit `redirect` / `show_fields` — the examples above are more complete).
- **code example**: https://github.com/xsolla/pay-station-sdk/blob/main/examples/google-pay/index.html
- **`xsolla/headless-checkout-demo`** (clone it — see `demo-install.md`):
  `src/pages/store-page/hooks/checkout/use-handle-form.ts` is the unified NextAction
  switch (`handleSpecialButton` renders the GP button).

---

## Acceptance — you are done when

- Already-integrated methods still pass end-to-end (you didn't break the shared
  dispatcher by adding Google Pay).
- The method chooser renders Google Pay; picking it reaches the **ZIP step** or mounts **`psdk-google-pay-button`** depending on NextAction.
- You **told the human** exactly how to finish the native-sheet test and did **not** claim a payment success you couldn't observe.
