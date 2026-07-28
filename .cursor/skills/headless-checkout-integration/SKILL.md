---
name: headless-checkout-integration
description: >-
  Integrates Xsolla Headless Checkout — a fully customizable, client-controlled
  payment UI built on the @xsolla/pay-station-sdk JavaScript SDK, where card data
  stays isolated in secure iframes and payments run through Xsolla without the
  standard Pay Station. Use when the developer wants to "integrate Headless Checkout",
  "add @xsolla/pay-station-sdk", "accept a credit card payment in sandbox",
  "add a payment method selector", "integrate PayPal / alternative payment methods",
  "add Google Pay / Apple Pay", "render psdk-card-number / psdk-payment-form",
  "handle onNextAction / NextAction", "do sandbox 3DS", or "show payment status /
  psdk-status" for a custom checkout.
metadata:
  owner: y.klochikhin
  domain: payments
  status: draft
---

## What this skill does

Integrates Headless Checkout into a **custom checkout UI** via `@xsolla/pay-station-sdk`,
running in **sandbox**. This is a big integration, so it is built **one payment method at a
time** (see Phases) until every method works. This file is a **map and a sequence** — the actual
how-to lives in `references/`; load only the reference the current phase needs.

**Frontend only.** It does **not** cover the production token backend (server-to-server) nor
webhook fulfillment — see `webhooks-impl` for granting items after `order_paid`.

## When to use

The developer wants to accept a payment with their **own** checkout UI (not the hosted Pay
Station) and is working in **sandbox** — standing up the integration from scratch, adding a
method selector, adding a payment method (card, PayPal/APM, QR, mobile), or adding the Google
Pay / Apple Pay wallet buttons.

## Prerequisites

Run **`merchant-setup`** first. The developer must have:

```bash
XSOLLA_MERCHANT_ID=<your merchant ID>
XSOLLA_PROJECT_ID=<your project ID>
XSOLLA_PROJECT_API_KEY=<your API key>   # server-side / agent-side only — NEVER ship to the browser
```

If credentials are missing, stop and complete `merchant-setup` first. The **only** secret that
ever reaches the browser is the short-lived **payment token** — never the API key.

## The one mental model: `form.init()` + one `onNextAction` dispatcher

Every payment method — card, PayPal, QR, mobile, wallets — runs through the same shape: call
`form.init({ paymentMethodId, returnUrl })`, render the **server-driven** fields, the user
submits, and the SDK drives a small state machine by emitting **NextActions** to your
`onNextAction` handler. **React to whatever action arrives — never assume a fixed sequence, and
never switch on the payment method id.** All flows converge on a final **status** view.

One dispatcher, keyed on `nextAction.type`, handles everything. Where each action is documented:

| NextAction(s)                                                | Owned by reference     |
|-------------------------------------------------------------|------------------------|
| `show_fields`, `show_errors`, `3DS`, `check_status`         | `credit-card-form`     |
| `redirect`                                                  | `redirect-flow`        |
| `check_status`, `status_updated`                            | `payment-status`       |
| `special_button` (wallets)                                  | `google-pay` / `apple-pay` |
| `show_qr_code`, `show_mobile_payment_screen`, `show_cash_payment_instruction` | `payment-methods` |

## Phases — build incrementally, one method at a time

Do **not** attempt everything at once. Finish and **test** each phase in sandbox before the next.

**Phase 1 — Credit card, end to end.** Install + `init({ sandbox: true })`, mint a sandbox token
(no backend), build the card form from `form.fields`, handle the `onNextAction` chain, show the
status, and drive a real sandbox payment including 3DS + the return page.
→ `initialization`, `credit-card-form`, `redirect-flow` (3DS-via-redirect), `payment-status`.
**Done when** the three sandbox test cards pass (see `credit-card-form` → Testing).

**Phase 2 — Payment method selection.** Let the user pick a method instead of hardcoding the
card PID; hand the chosen `paymentMethodId` to `form.init()`. Choose a layout pattern (start with
a simple list; icons mandatory; wallets as branded buttons) and design back/retry navigation.
→ `payment-methods-list`. **Done when** selecting a method routes into its form.

**Phase 3 — Additional methods, one type at a time.** Add the handlers for **redirect systems**,
**mobile**, **QR**, cash. But sandbox runs only redirect PS for real — mobile/QR/cash collapse to
the generic sandbox flow (form → notice → success), so their real UIs are **production-only**.
Sandbox-test on **PayPal (+ Venmo)**; code the rest to spec.
→ `payment-methods` (per-method NextAction; sandbox limits; PayPal/Venmo recipe), `redirect-flow`.
**Done when** PayPal (+ Venmo) reach a terminal status in sandbox and the other handlers are coded.

**Phase 4 — Google Pay.** Add the wallet button via the shared dispatcher (`special_button`),
then **ask the user to verify and give feedback** before continuing.
→ `google-pay`. **Done when** a sandbox Google Pay payment completes and the user confirms.

**Phase 5 — Apple Pay.** Same wallet pattern, then
**ask the user to verify and give feedback**.
→ `apple-pay`. **Done when** a sandbox Apple Pay payment completes and the user confirms.

**Phase 6 — Saved methods.** Let the user save a method while paying, show saved methods as the
**first step** on return visits (with "pay another way" fallback), pay with one (still
NextAction-driven — may need CVV / 3DS), and delete them.
→ `saved-methods`. **Done when** the sandbox round trip passes: save → see it → pay with it → delete.

End state: every payment method integrated and working in **sandbox**, with saving/reuse. Only
**production / go-live** is out of scope here and comes later.

## Styling & UX — match the store, don't ship the demo look

Headless Checkout is an **unstyled component library**. The SDK examples use deliberately bare
styles — **never treat them as the target design.** From Phase 1 onward, style the checkout to
match the **host store's own look** (its colors, typography, radius, spacing, buttons) so it
reads as part of the store, not a bolted-on widget. Do this from the start — restyling a finished
flow is far more work than building it styled.

Apply real **payment-UX best practices**, not a naive one-input-per-field stack. This list is
illustrative, not exhaustive — aim for a fast, low-friction, trustworthy checkout:

- **Compact card entry.** Present the card as **one or two tight rows**, not a tall accordion of
  full-width fields. Expiry (4 digits) and CVV (3) are tiny — put them side by side on one row
  with the card number; don't give each a full-width block.
- **Auto-advance focus** to the next field as one fills (number → expiry → CVV), and surface
  validation **inline** next to the field, not as a distant banner.
- **Respect brand tokens**, keep it **responsive / mobile-first**, use accessible labels, and
  show clear **loading / disabled** states while the SDK works.

The card inputs are cross-origin **secure iframes** — outer CSS cannot reach inside them, so
their styling goes through `setSecureComponentStyles(css)` **before** `setToken()`. Wrapper hosts
(`psdk-card-number`, `psdk-text`, …) are styled with normal CSS for layout/sizing. Both layers
and the mechanism live in `credit-card-form` → **Secure Field Styling**.

## Testing is mandatory (every phase)

A payment integration is verified only by a **completed sandbox transaction ending on a status
screen** — not by "the form renders." Each phase ends with an observed transaction; the concrete
test recipe lives in the phase's reference (card test matrix + headless-driving tips in
`credit-card-form`; PayPal sandbox login in `payment-methods`; wallet notes in `google-pay` /
`apple-pay`). Report the terminal screen you actually observed. **Driving it headlessly
(Playwright/Puppeteer)? Read [`references/testing.md`](references/testing.md) first** — the
cross-cutting gotchas (secure-field `fill()` vs keystrokes, submit-button host click, driver
artifact vs real bug) that otherwise eat hours.

## References

Load only what the current phase needs.

- [`references/documentation.md`](references/documentation.md) — navigation map: which official doc / GitHub example to
  load per task, full component table, SDK reference (README)
- [`references/demo-install.md`](references/demo-install.md) — `headless-checkout-demo` (full React + Vite): the **most
  complete** example and **fastest to access** once installed (local file reads, no doc fetches), but requires cloning
  the repo locally and linking it to the agent
- [`references/initialization.md`](references/initialization.md) — install SDK, `init({ sandbox: true })` +
  `setToken()`, getting a sandbox payment token with **no backend**
- [`references/payment-methods-list.md`](references/payment-methods-list.md) — `psdk-payment-methods` vs custom API,
  `selectionChange`, country handling, handoff to `form.init()`; **layout patterns (list / accordion / tabs), method
  icons, wallet-button placement, back navigation**
- [`references/credit-card-form.md`](references/credit-card-form.md) — server-driven fields, field→component mapping,
  `setupAndAwaitFieldsLoading`, the NextActions, two 3DS paths, **the sandbox test matrix + how to drive it headlessly**
- [`references/redirect-flow.md`](references/redirect-flow.md) — **all redirect mechanics**: `psdk-redirect` vs manual
  form, GET/POST + 414, same-tab / new-tab / WebView window strategies + iframe caveat, `isNewWindowRequired` /
  `isSameWindowRequired`, new-tab gesture, return page (covers 3DS-via-redirect, e-wallets, extra verification)
- [`references/payment-status.md`](references/payment-status.md) — `check_status`, `psdk-status` vs custom UI, the **one
  ** `getStatus()` rule, `status_updated`, return page
- [`references/payment-methods.md`](references/payment-methods.md) — which method emits which NextAction; **redirect
  systems** (PayPal) + **SDK / same-window** methods, **QR** (`show_qr_code`), **mobile** (`show_mobile_payment_screen`);
  PayPal sandbox test recipe
- [`references/google-pay.md`](references/google-pay.md) — the **Google Pay** wallet button via the shared dispatcher:
  the `special_button` action, the `show_fields` (ZIP) step a bespoke screen would drop
- [`references/apple-pay.md`](references/apple-pay.md) — the **Apple Pay** wallet button: renders inside
  `psdk-submit-button` automatically (no new NextAction), desktop QR fallback, browser-support gating, domain registration
- [`references/saved-methods.md`](references/saved-methods.md) — **save** a method while paying (`allowSave` field /
  `savePaymentMethod`), **detect + show** saved methods first (`getSavedMethods`, `psdk-saved-methods`), **pay** with one
  (`paymentWithSavedMethod` + `savedMethodId`, still NextAction-driven), and **delete** (`delete-mode`)
- [`references/testing.md`](references/testing.md) — **headless sandbox testing gotchas**: secure-field `fill()` vs real
  keystrokes (opposite per field), the `psdk-submit-button` host click + retry, telling a driver artifact from a real bug

### Agent test (reference run)

Prompt: "Integrate Xsolla Headless Checkout into my web app and let me pay with a credit card in
sandbox." Expected: the agent follows **Phase 1** — reads `SKILL.md`, pulls `initialization`,
`credit-card-form`, `redirect-flow`, and `payment-status` as each step needs them; installs
`@xsolla/pay-station-sdk`; initializes with `sandbox: true`; mints a sandbox token; builds the
card form from `form.fields`; handles the full `onNextAction` chain; and **passes the three
sandbox test cards** (incl. the 3DS return page) on a real run. ✅
