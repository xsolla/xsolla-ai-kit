---
name: headless-checkout-apple-pay
description: >-
  Add the Apple Pay wallet button to a site already running Xsolla Headless
  Checkout (@xsolla/pay-station-sdk). Use when a developer wants to "add Apple
  Pay", "render psdk-apple-pay / ApplePayComponent", "why is the Apple Pay button
  not showing", "Apple Pay QR code on desktop", "Apple Pay not supported on this
  browser", "enable Apple Pay instant / one-click", or "register my domain with
  Apple". Assumes the SDK is initialized and a shared NextAction dispatcher exists
  (headless-checkout-integration skill). Google Pay is a SEPARATE skill — see google-pay.md.
---

# Apple Pay for Headless Checkout

Guide for an AI agent. You are adding **one** payment method — Apple Pay — to a
Headless Checkout. Google Pay is a separate entity with its own skill
(`google-pay.md`); do not try to wire both at once.

## The one rule that makes this work

> **Apple Pay is NOT a bespoke screen.** It flows through the **same shared
> `form.init()` + `onNextAction` dispatcher** as every other method. What makes
> Apple Pay unusual is that it contributes **no new NextAction and no button of its
> own to create** — when you init the Apple Pay method and mount `psdk-submit-button`,
> the SDK renders `<psdk-apple-pay>` **inside** that submit button automatically.

Apple Pay is an even thinner entity than Google Pay: it initializes its method and
contributes **zero** new actions to the shared dispatcher — the SDK renders
`<psdk-apple-pay>` inside the submit button the base already mounts. Redirects, QR and
status are handled by the shared base, like any method. Unlike Google Pay, Apple Pay
**never** emits `special_button`; if you build a dedicated screen that waits for one,
nothing will ever happen.

---

## 0. Prerequisites

1. SDK initialized (`init()` + `setToken()` succeed) and a **shared NextAction
   dispatcher** in place — the base `onNextAction` handler that renders
   server-driven fields (→ components + `psdk-submit-button` + `form.activate()`),
   handles `redirect`, and mounts `psdk-status`. If it doesn't exist yet, the
   `headless-checkout-integration` skill stands it up via the credit-card method
   (easiest to test); Apple Pay then reuses the same dispatcher untouched.
2. A **payment access token** for the order.

Payment method ID: Apple Pay `3175`. Prefer discovering the ID via SDK
(`payment-methods-list` skill) over hardcoding.

---

## 1. Mental model (Apple-Pay-specific)

### 1.1 The button lives inside the submit button

There is **no `special_button` for Apple Pay** and you **never** create
`<psdk-apple-pay>` yourself. When `form.init({ paymentMethodId: 3175 })` runs and
the shared field renderer mounts `psdk-submit-button`, the SDK renders
`<psdk-apple-pay>` inside it. So for Apple Pay the submit button the base already
mounts *is* the whole UI — no new NextAction case is required.

### 1.2 Instant vs regular flow

Apple Pay has two flows, and **which one you want depends on where the payment should
happen** (§1.3). Neither is "the whole base path" — pick per case:

- **Regular flow — the default when the flag is off.** Needs **no certificates and no
  domain registration** and works on any domain. Everything happens on Xsolla's **Pay
  Station page** via a `redirect`: Safari opens the native sheet there, and **non-Safari
  desktop bounces to Pay Station and shows the QR THERE too** (not in your page). The
  shared dispatcher's `redirect` + `check_status` cases cover it.
- **Instant flow — payment stays IN your page** (set `isApplePayInstantFlowEnabled`, §2).
  Two distinct effects, and they have **different requirements**:
  - **Safari → native sheet in your page** (no redirect, better conversion). This one
    needs the store's domain **registered with Apple** (domain-association file +
    certificate) — real lead time, so it's a **production** upgrade (§6).
  - **Non-Safari desktop → the QR renders in your page** instead of redirecting to Pay
    Station. This needs **only the flag** — **no certificate**. It's a cheap UX win worth
    enabling in the **base integration** (and in sandbox), not deferring to production.

> **So the in-page QR is an INSTANT-flow feature, not a regular-flow default.** Without
> the flag, non-Safari desktop redirects to Pay Station and the QR shows there. The §5
> overlay code only fires in the instant flow — enabling the flag is what makes it live.

Enable instant **only on desktop
non-Safari** — `isApplePayInstantFlowEnabled: !isSafari() && !isMobile()` — to get the
in-page QR cert-free. Keep mobile and desktop Safari on the regular flow.

### 1.3 Environment

Two independent things vary by environment; the Apple Pay button handles both
automatically — you neither choose nor gate them.

**(a) Which surface** — decided by the browser's Apple-wallet support: **Safari / iPhone /
iPad** get the **native Apple Pay sheet**; **non-Safari** browsers (Chrome, Edge, desktop
generally) get a **QR code** to scan with an iPhone (iOS 18+).

**(b) Where it appears** — decided by the flow (§1.2) *and* the browser:

| Browser / device                           | Regular flow (flag off) | Instant flow (flag on) |
|--------------------------------------------|---|---|
| **Safari, iPhone / iPad**                  | redirect to Xsolla's **Pay Station page**; native sheet opens there | native sheet **in your page** (no redirect) — needs the cert (§6) |
| **Non-Safari desktop** (Chrome, Edge, etc) | redirect to **Pay Station**; QR shown **there** | **QR code in your page** (scan with an iPhone) — cert-free |

So the flag's effect differs by browser: on **Safari** it moves the native sheet in-page
(needs the cert); on **non-Safari desktop** it moves the **QR** in-page (no cert). With
the flag off, both cases redirect to Pay Station. Gate the flag to **desktop non-Safari**
(§1.2 bottom line) so you get the cert-free QR win without Safari attempting an
uncertified in-page sheet and without a pointless QR on phones.

Key points:

- The native sheet always needs **Safari** + an **Apple-registered domain**. In the
  regular flow that domain is **Xsolla's Pay Station** (via the redirect); instant moves
  it in-page and requires **your** domain registered (§6). Test on a hosted domain —
  Apple Pay is unreliable on `localhost`.
- The in-page **QR is Apple's official mechanism** for browsers without a native Apple
  wallet (iOS 18+): the buyer authorizes on their iPhone — a valid completion path, not
  an error. It renders inside `psdk-apple-pay`; style it per §5. It appears in your page
  **only in the instant flow** (desktop non-Safari); with the flag off the QR is on Pay
  Station after a redirect.
- **Do not gate the button** with `ApplePaySession.canMakePayments()` /
  `supportsVersion()`. Gating suppresses the button and disables the QR path — render
  the button and let it select the appropriate surface.

---

## 2. Initialize (once)

Enable the instant flow on **desktop non-Safari** so the QR renders in your page
(cert-free, §1.2); everything else falls back to the regular flow automatically.

```js
const { headlessCheckout } = PayStationSdk; // or: import { headlessCheckout } from '@xsolla/pay-station-sdk'

await headlessCheckout.init({
  sandbox: true,        // false in production
  isWebview: false,     // ⚠️ lowercase "v" — see §7
  theme: 'default',
  language: 'en',
  topLevelDomain: location.hostname,
  // In-page QR is an instant-flow feature — WITHOUT this, non-Safari desktop redirects
  // to Pay Station for the QR. Gate to desktop non-Safari (see isSafari/isMobile helpers):
  isApplePayInstantFlowEnabled: !isSafari() && !isMobile(),
});

await headlessCheckout.setToken(accessToken); // ⚠️ BEFORE any form.init()
```

---

## 3. The Apple Pay entity

The dispatcher below is method-agnostic — it is the shared base every method uses.
Apple Pay contributes **no new NextAction case**: its whole entity is "init the
method, let the shared field renderer mount the submit button, then (optionally)
listen to the button's lifecycle events." Nothing here is card-specific.

```js
const host = document.querySelector('#form-container'); // the ONE host container

headlessCheckout.form.onNextAction(handleNextAction); // subscribe ONCE, before any form.init

// ── Shared base dispatcher — the same for every payment method ───────────────
// Apple Pay adds NO case here; every path converges on check_status → psdk-status.
function handleNextAction(a) {
  switch (a.type) {
    case 'show_fields':   renderFields(a.data.fields); break;
    case 'redirect':      handleRedirect(a.data.redirect); break; // pages flow / 3DS-redirect
    case '3DS':           mount3ds(a.data.data); break;
    case 'hide_form':     host.style.display = 'none'; break;      // Apple flow uses this
    case 'show_errors':
    case 'server_error':  showError(a.data.errors?.[0]?.message ?? 'Payment error'); break;
    case 'check_status':  showStatus(); break;
  }
}
// renderFields / handleRedirect / mount3ds / showError / showStatus are the shared
// base helpers — method-agnostic. renderFields maps each field → its psdk-* component,
// appends <psdk-submit-button>, then calls headlessCheckout.form.activate().

// ── Apple Pay entity — its own module: owns the PID, init, and event wiring ──
const APPLE_PAY_PID = 3175;

async function initApplePay() {
  host.innerHTML = '';
  const form = await headlessCheckout.form.init({
    paymentMethodId: APPLE_PAY_PID,
    // Keep the FULL current URL + token — never strip the query (return-page rule).
    returnUrl: `${location.origin}${location.pathname}?token=${accessToken}`,
  });
  renderFields(form.fields || []);     // for Apple Pay `fields` is usually empty → this just
                                       // mounts psdk-submit-button, and <psdk-apple-pay>
                                       // renders inside it.

  // Attach lifecycle listeners once the element exists (see §4, §5).
  const applePayButton = host.querySelector('psdk-apple-pay');
  if (applePayButton) { listenApplePayEvents(applePayButton); wireApplePayQr(applePayButton); }
}
```

Keep the `redirect` case in the shared dispatcher — the pages/regular Apple Pay flow
and 3DS redirects hang without it.

---

## 4. Apple Pay button events + the `applePayWindowOpened` trap

`<psdk-apple-pay>` dispatches DOM `CustomEvent`s you can use for UX/analytics.
**Verified against the component source, these are the ONLY events it dispatches:**

```js
function listenApplePayEvents(btn) {
  btn.addEventListener('applePayButtonClicked', () => {/* user tapped */});
  btn.addEventListener('applePayWindowClosed', (e) => {
    const { closedByUser } = e.detail; // true = cancelled; false = closed after transaction
    // Apple Pay won't reopen its external window on a second click — remount a fresh
    // button here if you want the user to be able to retry after cancelling:
    // if (closedByUser) initApplePay();
  });
  btn.addEventListener('applePayQrOpened', () => {/* see §5 */});
  btn.addEventListener('applePayQrClosed', () => {/* see §5 */});
  btn.addEventListener('applePayError', (e) => showError(String(e.detail ?? 'Apple Pay error')));
}
```

> ⚠️ **There is NO `applePayWindowOpened` DOM event on the element.** That name
> exists in the SDK's internal event enum and the *official example listens for it*,
> but the `psdk-apple-pay` component never dispatches it — the listener is dead code.
> (The `…WindowOpened` event that does fire belongs to **Google** Pay.) For a
> "sheet opened" signal use `applePayButtonClicked` instead. Copying the official
> example's `applePayWindowOpened` listener is a classic time-sink.

Listen on the **element** (`btn.addEventListener('applePayQrOpened', …)`) — see §5.
> ⚠️ Do **not** use `headlessCheckout.events.onCoreEvent('applePayQrOpened', () => null, handler)`.
> `onCoreEvent(name, guard, handler)`'s 2nd arg is a message **guard** that must return a
> truthy match; `() => null` always returns null, so the handler **never fires**. The
> component re-dispatches these as DOM CustomEvents on itself — use those.

---

## 5. QR overlay on desktop Chrome (and the backdrop trap)

In the **instant flow** (desktop non-Safari, §1.2) the SDK opens the QR inside
`#apple-pay-iframe`. It only pins it `position:absolute; top:0; left:0` with **no size**
(`addStylesForQrCode`), so left alone it's a tiny 300×150 box in the corner — you must
size AND center it. Wire the listeners **on the `<psdk-apple-pay>` element** (which
re-dispatches the events), not via `onCoreEvent` (§4):

```js
// call once the <psdk-apple-pay> element exists (it mounts inside psdk-submit-button)
function wireApplePayQr(btn) {
  const iframe = () => btn.querySelector('#apple-pay-iframe');
  btn.addEventListener('applePayQrOpened', () => iframe()?.classList.add('ap-qr-overlay'));
  btn.addEventListener('applePayQrClosed', () => iframe()?.classList.remove('ap-qr-overlay'));
}
```

```css
#apple-pay-iframe.ap-qr-overlay {
  /* !important on top/left/transform too — the SDK's inline top:0;left:0 beats
     non-important CSS, otherwise the QR stays pinned in the corner. */
  position: fixed !important;
  top: 50% !important; left: 50% !important; transform: translate(-50%, -50%) !important;
  width: min(94vw, 460px) !important; height: min(90vh, 620px) !important;
  z-index: 9999; background: #fff; border: none; border-radius: 12px;
  box-shadow: 0 12px 48px rgba(0,0,0,.5);
}
```

> ⚠️ **Do NOT add a full-page backdrop via `body::before`/`::after`.** The QR iframe
> is nested inside your modal's stacking context; a body-level backdrop (however
> high its `z-index`) paints **over** the iframe — darkening the QR and trapping
> clicks so the user can't close it. If you must dim, put the backdrop **inside the
> modal, behind the iframe**, or make it `pointer-events: none`. No backdrop is the
> reliably-correct default.

---

## 6. Optional: enabling the instant flow (production)

Instant is an **optional conversion upgrade for production** — a recommendation, not a
required part of the integration. **Skip it while integrating and in sandbox**; the
regular flow (§1.2) already works everywhere with no setup. Come back here only when the
store is going live and the partner wants the one-tap in-page sheet. Make sure they know
it exists; don't block go-live on it.

**Step 1 — check whether the project already has it.** Some stores are built on a
project where Apple Pay certificates are already configured; then instant just needs the
client options. Mint a Pay Station access token for the project and ask the certificate
checker:

```bash
curl --request POST \
  --url 'https://secure.xsolla.com/paystation2/api/instant_pay_flow_checker/apple_pay?access_token=<PAY_STATION_TOKEN>' \
  --header 'Content-Type: application/json' \
  --data '{ "certificate_domain": "your-store-domain.com" }'
```

```json
{ "isCertificatesExist": true }
```

`true` → certificates exist; enable instant with the client options in Step 2. `false`
(the usual case for a new project/domain) → issue certificates first, Step 3.
`<PAY_STATION_TOKEN>` is minted for that specific project (same as the order's payment
token — see `initialization`); use the host matching its environment (`secure` for
production, `sandbox-secure` for sandbox).

**Step 2 — client options (only once certificates exist).** Add to `init()`:

```js
await headlessCheckout.init({
  // …regular options from §2
  topLevelDomain: 'your-store-domain.com', // your real Apple-registered domain
  isApplePayInstantFlowEnabled: true,
});
```

If you open the SDK inside your own `<iframe>`, that outer iframe also needs
`allow="payment"` (the SDK sets it on its own iframe).

**Step 3 — issue the certificate (domain onboarding).** One-time, ~7-day window, cannot
be skipped:

1. The partner files a request (Support Hub / Publisher Account) with the **exact**
   payment-page URL (no redirects).
2. Xsolla returns an **Apple domain-association file**; serve it at
   `/.well-known/apple-developer-merchantid-domain-association`.
3. Xsolla **verifies** the file (within 7 days or it expires) and enables the
   instant-flow feature toggle for the project.

The registration **expires after ~1 year** and must be renewed. Instant is **not
supported** with `is_independent_window(s)` (payment opened in a separate external tab).
As with Google Pay, the backend feature toggle wins over the client flag — if it's off,
`isApplePayInstantFlowEnabled: true` cannot force instant. Until all of this is done,
Apple Pay simply uses the regular flow, which is fine.

More detail: https://developers.xsolla.com/payment-ui-and-flow/payment-methods/one-click-payment/
(Confluence: *"Enabling instant Apple Pay & Google Pay for Partners"*.)

---

## 7. Pitfalls (each cost real time — don't repeat them)

| ⚠️ | Trap | Do instead |
|---|---|---|
| **Creating the button yourself** | `document.createElement('psdk-apple-pay')` | Never — it renders inside `psdk-submit-button` when the method is Apple Pay |
| **Waiting for `special_button`** | Apple Pay never emits it → nothing happens | Just mount the submit button; the button appears inside it |
| **`applePayWindowOpened` listener** | Never fires (Apple has no such DOM event) | Use `applePayButtonClicked` |
| **Capability gating** | `canMakePayments()`/`supportsVersion()` hide the button & kill QR | Never gate — render it, let the SDK choose native/QR/redirect |
| **Expecting the in-page QR without the flag** | Non-Safari desktop with the flag off → redirects to Pay Station, QR shown THERE, not in your page | In-page QR is an **instant-flow** feature — set `isApplePayInstantFlowEnabled` (§1.2, §2) |
| **QR events via `onCoreEvent`** | `onCoreEvent('applePayQrOpened', () => null, handler)` — the `() => null` guard blocks the handler, it never fires | Listen on the `<psdk-apple-pay>` element: `btn.addEventListener('applePayQrOpened', …)` (§5) |
| **QR overlay in the corner** | `addStylesForQrCode()` pins the iframe `absolute; top:0; left:0` with no size; CSS without `!important` on top/left/transform loses to it | `!important` on position/top/left/transform + explicit width/height (§5) |
| **Enabling instant everywhere** | On phones the QR is useless (iOS wants the sheet, can't self-scan); Safari's in-page sheet needs a cert | Gate to **desktop non-Safari**: `!isSafari() && !isMobile()` (§1.2) |
| **Testing Apple Pay on localhost** | Apple Pay is unreliable on localhost | Test on a hosted domain; the in-page QR needs no domain registration |
| **QR backdrop** | `body::before/::after` covers & darkens the nested QR iframe, traps clicks | No page backdrop, or place it inside the modal behind the iframe |
| **`isWebView` casing** | The interface field is `isWebview` (lowercase v); capital-V is silently ignored | Use `isWebview` |
| **Forgetting `redirect`** | Pages-flow / 3DS Apple payments hang | Handle `redirect` in the shared dispatcher |
| **Can't retry after cancel** | `psdk-apple-pay` won't reopen its external window on a 2nd click | Remount a fresh button on `applePayWindowClosed` |
| **Forcing instant from client** | Expecting the flag to override a backend toggle / missing domain | Backend toggle + Apple domain registration are authoritative |
| **`setToken` after `form.init`** | Form init fails | `setToken()` first, then `form.init()` |

---

## 8. Testing — what an AI agent CAN and CANNOT do

**An AI agent cannot complete an Apple Pay transaction.** The completion surface is always
out of reach: in Safari it's the native sheet (on Xsolla's Pay Station after a redirect,
or in-page with instant); in other browsers it's a QR the buyer scans with a phone. A
headless browser has no signed-in wallet and no phone to scan. **Do not loop on Playwright
trying to open or finish the Apple Pay sheet** — that is the endless-cycle trap.

What the agent **can** verify:

| Check | How |
|---|---|
| Already-integrated methods still complete end-to-end | regression check — e.g. drive the card method through `psdk-status` (see the integration skill) |
| Method chooser renders Apple Pay | assert the row/method exists |
| Apple Pay mounts | **WebKit**: pick Apple → assert `<psdk-apple-pay>` + its `#apple-pay-iframe` exist inside the submit button (WebKit mounts it even without a real wallet) |

Then **hand the actual payment to a human** — the native sheet and the QR both complete
outside the page DOM. For the **regular flow** (what you integrate), the tester opens the
checkout on a hosted domain and completes on either:
- **Safari** (macOS / iOS) → the native Apple Pay sheet, or
- **desktop Chrome** → the QR code, scanned with an iPhone.

If **instant** was enabled for production (§6), the same test in Safari on the
**registered** domain should open the sheet **in the page**, with no redirect.

Report "button mounts" as the ceiling of what you verified — never claim an Apple Pay
success you could not observe.

---

## 9. Sources

- **docs**: https://developers.xsolla.com/sdk-fuctional-and-ui/headless-checkout/payment-methods/apple-pay/index.md
  and https://developers.xsolla.com/payment-ui-and-flow/payment-methods/one-click-payment/
  (docs omit `redirect` / `hide_form` — the code above is more complete).
- **code example**: https://github.com/xsolla/pay-station-sdk/blob/main/examples/apple-pay/index.html
- **`xsolla/headless-checkout-demo`** (clone it — see `demo-install.md`):
  `src/pages/store-page/hooks/checkout/use-handle-form.ts` is the unified NextAction
  switch (`handleSpecialButton` renders the GP button).

---

## Acceptance — you are done when

- Already-integrated methods still pass end-to-end (you didn't break the shared
  dispatcher by adding Apple Pay).
- Apple Pay is wired: the method chooser renders it, and picking it mounts
  `<psdk-apple-pay>` inside the submit button (asserted in WebKit).
- Instant is enabled on **desktop non-Safari** (`!isSafari() && !isMobile()`) so the QR
  renders in-page cert-free; mobile + Safari fall back to the regular Pay Station redirect.
- You **told the partner that the Safari in-page native sheet** needs domain registration
  (§6) — an optional production upgrade, not blocking the integration.
- You **told the human** where to finish the native test (Safari, or Chrome desktop for
  the QR, on a hosted domain) and did **not** claim a payment success you couldn't
  observe.
