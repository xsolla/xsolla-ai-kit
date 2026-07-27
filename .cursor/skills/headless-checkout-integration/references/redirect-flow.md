# Redirect Flow

Guide for an AI agent. Covers the `redirect` NextAction: when the server sends the user off-page and how to take them there and back.

**Prerequisites:** `credit-card-form` or another payment flow skill — `form.init()` + `onNextAction` working. Status handling lives in `payment-status`. This doc owns **all redirect mechanics**; which payment methods emit `redirect` (PayPal, e-wallets, SDK/same-window systems) and the non-redirect methods (QR, mobile, cash) live in `payment-methods`.

---

## When `redirect` Fires

The server emits **one** `redirect` action for every "leave the page to finish payment" case. The destination differs, the action and data shape do **not**:

| Case                              | Destination                                 | What `redirectUrl` points at   |
|-----------------------------------|---------------------------------------------|--------------------------------|
| **Payment system**                | PayPal, e-wallets, bank portals, APMs       | Provider's hosted payment page |
| **3DS (acquirer / external MPI)** | Bank's frictionless/redirect 3DS page       | Acquirer ACS URL               |
| **Extra verification**            | Provider-side KYC / OTP / confirmation page | Provider verification endpoint |

**Do not branch on the case** — there is no flag distinguishing PayPal from a 3DS redirect. Handle the `redirect` action uniformly; the server already chose the URL and method. Read `nextAction.data.redirect` and go.

> `3DS` is a **separate** NextAction (`type === '3DS'`), not a redirect — it's the MPI **challenge** flow rendered in an iframe via `psdk-3ds`. Bank-card 3DS may surface as **either** `redirect` (ACS redirect) **or** `3DS` (in-page challenge). Handle both — see `credit-card-form`.

---

## Redirect Action Shape

`apps`/SDK type: `RedirectActionData` (`src/core/actions/redirect/redirect.action.type.ts`).

```typescript
nextAction.data.redirect = {
  redirectUrl: string;            // where to send the user
  data: { [key: string]: string }; // params → query string (GET) or POST body
  method?: string;                // 'GET' | 'POST'; absence ⇒ GET
  isNewWindowRequired?: boolean;  // open in a new tab (needs a user gesture)
  isSameWindowRequired?: boolean; // navigate the current tab automatically
};
```

**Honor `method`.** GET serializes `data` into the URL; POST sends it in the body. Large payloads over GET hit **414 Request-URI Too Large** — never force everything into the query string.

---

## Choosing the Window: Same-Tab vs New-Tab

There are **two** working ways to send the user to the provider. `psdk-redirect` implements both and picks based on the server flags — you only override for an environment the server can't see (an iframe).

| Strategy | How | Trade-off |
|---|---|---|
| **Same tab** (default) | Navigate the current window to the provider; `returnUrl` brings it back to the status page. `psdk-redirect` submits **automatically — no extra click**. | Cannot run inside an iframe: it navigates the *iframe's* document and the provider refuses to render there. |
| **New tab** | `psdk-redirect` renders a **Continue** button; clicking it opens the provider in a new tab, then polls for its close (`redirectWindowClosed`). | Adds **one extra click** — the browser blocks opening a tab without a fresh user gesture (see the gesture rule). |

**Prefer same-tab.** Every extra step on a payment form costs conversion, and same-tab is also the better mobile experience (juggling tabs on a phone is awkward). New-tab is used **only when required**.

### How to choose (in order)

1. **Is the checkout inside an iframe?** → **new tab**, always. Same-tab navigates the *iframe's* document, and the provider page almost always refuses to render in an iframe (`X-Frame-Options` / `frame-ancestors`), so the user gets stuck. Headless Checkout has no iframe of its own — this applies **only** if *you* wrapped it in one (common on mobile, which is exactly where it hurts).
2. **Did the server send `isNewWindowRequired`?** → **new tab**.
3. **Otherwise** — `isSameWindowRequired`, **or no flag at all** → **same tab**. This is the default: fewer steps → higher conversion, and it's best on mobile.

**In one line: same tab, unless the SDK asks for a new tab (`isNewWindowRequired`) or you're inside an iframe.**

### WebView (native mobile apps only)

If your app embeds the checkout in a **native WebView**, no tab can open: redirect with `window.open(providerUrl)`, which hands off to the device's default browser, and set **`is_independent_windows`** in the payment token so the backend expects the detached window. There is no automatic return — the return page must tell the user to switch back to the app. (Plain web builds are not WebViews — ignore this unless you're inside a native app shell.)

### Server-forced same-window methods (the "SDK payment methods" group)

A distinct group of systems — **Barzahlen, Naver, Venmo, Paytm, Alipay, PIX**, and similar — **cannot** survive a new tab or an iframe and **must** open in the same top-level window. You do **not** maintain a list of which ones: **the server sets `isSameWindowRequired: true`** on their `redirect` action, and `psdk-redirect` obeys it. These are the first methods to fail under an iframe wrapper (see the callout above); there is no new-tab fallback for them — the fix is to not iframe the checkout. Method-level context and the `sdk-payment-methods` example live in `payment-methods`.

---

## Approach A: `psdk-redirect` (Recommended)

The component builds the hidden form, picks GET/POST, handles new-tab vs same-tab, and emits `redirectWindowClosed` when a new tab is closed. Pass the raw `redirect` object as JSON. **It acts only when the server sets a flag** — with neither flag it stays inert and you must drive the redirect yourself (Approach B).

```typescript
headlessCheckout.form.onNextAction((nextAction) => {
  if (nextAction.type === 'redirect') {
    clearFormFields();
    const redirect = new PayStationSdk.RedirectComponent();
    redirect.setAttribute('data-redirect', JSON.stringify(nextAction.data.redirect));
    redirect.setAttribute('text', 'Continue'); // button label for the new-tab case
    container.append(redirect);
  }
});
```

```html
<psdk-redirect data-redirect='...' text="Continue"></psdk-redirect>
```

**The flags are the server's decision, not a hint.** When the backend sets one, **obey it** (via `psdk-redirect`) rather than re-deriving the strategy — override only for the environment the server can't see (iframe ⇒ never same-tab; WebView ⇒ independent window). But the server does **not** always send a flag (see the "Neither flag set" case below) — when none arrives, default to **same tab**.

Behavior by flag:
- **`isSameWindowRequired`** → submits the form in the current tab automatically (no button). = same tab.
- **`isNewWindowRequired`** → renders a `text` button; on click opens `about:blank` in a named tab, submits into it, polls for close, then fires `EventName.redirectWindowClosed` (DOM event + public postMessage). A button is mandatory here — see the gesture rule below. = new tab.
- **Neither flag set** → `psdk-redirect` stays **inert**: it builds the form but neither auto-submits nor shows a button. This is **not** just a theoretical config error — real methods hit it (e.g. **PayPal** in sandbox). Handle it as the **default = same tab**: submit the redirect form yourself in the current window (see Approach B below). Don't wait for a flag that isn't coming, and don't add a "Continue" button for it — same-tab needs no gesture, so a button would only cost a click.

After redirect, the user comes back via `returnUrl`. Mount `psdk-status` on the return page (see below). For a popup flow where the checkout tab stays open, prime status with **one** `getStatus()` on `redirect` — see `payment-status` "Popup redirect".

Ref: `examples/credit-card/init-payment-flow.js` (Option 2 comment).

---

## Approach B: Manual Redirect

**Not just for custom markup — this is the *required* path whenever `psdk-redirect` can't act
for you.** The big one is the **no-flag case**: with neither `isSameWindowRequired` nor
`isNewWindowRequired` set, `psdk-redirect` stays inert (builds the form, never submits, no
button), so Approach A simply doesn't complete the redirect. Real methods hit this (e.g. PayPal in
sandbox), so you must drive it yourself here. Approach A remains the right choice for the flagged
cases (`isSameWindowRequired` → auto same-tab, `isNewWindowRequired` → gesture button); Approach B
covers the no-flag default (same tab) and any time you want same-tab navigation without mounting
the component.

Build a form so POST works (avoids 414):

```typescript
function handleRedirectAction({ data: { redirect } }) {
  const { redirectUrl, data, method, isNewWindowRequired } = redirect;
  const form = document.createElement('form');
  form.method = method?.toUpperCase() === 'POST' ? 'POST' : 'GET';
  form.action = redirectUrl;
  Object.entries(data).forEach(([name, value]) => {
    const input = document.createElement('input');
    input.type = 'hidden';
    input.name = name;
    input.value = String(value);
    form.appendChild(input);
  });
  document.body.appendChild(form);

  if (isNewWindowRequired) {
    form.target = '_blank';
    clearFormFields();
    renderContinueButton(() => form.submit()); // gesture required
    return;
  }
  form.submit();
}
```

Simple GET-only (PayPal example, `examples/paypal/index.html`) — appends `data` to the URL and sets `window.location.href`. Acceptable only for small param sets.

---

## The New-Tab Gesture Rule (Critical)

When `isNewWindowRequired` is true, the new tab **must** open from a user gesture (click) — browsers block `window.open` outside a trusted event. **Never auto-open.** Render a "Continue" button and call `window.open` / `form.submit()` inside its click handler. `psdk-redirect` does this for you; manual code must replicate it.

`isSameWindowRequired` has no gesture requirement — it replaces the current document, so it can fire automatically.

---

## Return Page

`returnUrl` (set in `form.init`) is where the provider/3DS/verification page sends the user back. On return the server **appends** its own query params to that URL — keep them intact:

| Param                                                                     | Required? | Notes                                                                     |
|---------------------------------------------------------------------------|-----------|---------------------------------------------------------------------------|
| `token`, `signature`, `locale`, `fix_pid`, `fix_invoice`                  | **Yes**   | `psdk-status` won't load status if any is missing                         |
| `fix_userReturnStatus`                                                    | No        | Hint only (`success` / `failure`); the real result comes from the backend |
| `fix_testProject`, `fix_testPs`, `fix_testXsolla`, `isSavePaymentAccount` | No        | Forwarded as-is                                                           |

```typescript
// checkout page
await headlessCheckout.form.init({
  paymentMethodId,
  returnUrl: `${origin}/payment/return.html?token=${token}`,
});
```

Return page = re-init, **no** `form.init()`:

```html
<psdk-status></psdk-status>
<psdk-legal></psdk-legal>
```

```typescript
const token = new URL(location.href).searchParams.get('token');
await headlessCheckout.init({ isWebView: false, sandbox: true });
await headlessCheckout.setToken(token);
// psdk-status reads the rest from window.location.href and calls getStatus() once on mount
```

**You only read `token` yourself** (to pass to `setToken`). The `fix_*` / `signature` params are parsed by the SDK from `window.location.href` — **never map them by hand**. Status display, polling, and pitfalls are owned by `payment-status` — don't duplicate `getStatus()` calls.

### Embedded on a partner page

Point `returnUrl` at a **dedicated route** your app recognizes (`/return`, `/status`) rather than back onto the checkout page. Then you switch to the status screen by route — no need to sniff query params to tell a return apart from a fresh load. The server still appends its params to that route (`…/return?token=…&fix_invoice=…&signature=…&locale=…&fix_pid=…`).

**The `returnUrl` must resolve to a page that actually loads the SDK and your status code, and must keep its page identifier.** This is the single most common way the 3DS flow breaks, and it fails *silently*:

- **SPAs** — any route reloads the same app bundle, so a dedicated route "just works."
- **Multi-page / CMS sites (server-rendered, static)** — each URL is a **different document**. If `returnUrl` points at a path/page that does not include your checkout script, the user lands on a page with **no SDK and no handler**, and nothing happens — `getStatus()` is never called. Classic trap: building `returnUrl` by stripping the query off the current URL (`location.href.split('?')[0]`) on a site that identifies the page *by* query (`?page_id=5`, `?p=…`). You drop the identifier and land on the **home page**. Build `returnUrl` by adding only `token` to the *full* current URL (e.g. `const u = new URL(location.href); u.searchParams.set('token', token);`) — never strip its existing query.

The other rule: **don't strip or rewrite the params the server appends.** If your router/CMS cleans the query string before `psdk-status` mounts, `getStatus()` fails with *"No required search params to get status"*. Preserve them through any client-side navigation.

### Troubleshooting: the return page does nothing (status never requested)

The user finishes payment in external system or 3DS, comes back, and the page is blank / shows the storefront / never calls `getStatus()`. Work down this list — the cause is almost always one of these, in order of likelihood:

1. **Wrong landing page.** Does `returnUrl` resolve to a page that loads your SDK + status handler? Open the exact return URL by hand — if your checkout code isn't on that page, fix `returnUrl` (preserve the page identifier; see above). This is the #1 cause on CMS/MPA sites.
2. **SDK not initialized on return.** The return page is a fresh load — it must re-run `init({ sandbox: true })` + `setToken(tokenFromUrl)` before mounting `psdk-status`. Do **not** call `form.init()` here.
3. **Token missing from the URL.** Read `token` yourself from the query and pass it to `setToken`. No token → no status.
4. **Appended params stripped.** A router/CMS canonical redirect dropped `signature` / `fix_invoice` / `fix_pid` / `locale`. `psdk-status` then errors *"No required search params to get status."* Preserve them.
5. **Return mode not detected.** If you reuse the checkout page as the return page, branch on the presence of return params (e.g. `token` **and** `signature`) to render status instead of the buy button.

Refs: `examples/return.html`, `examples/paypal-custom-status/return.html`.

### External-page popup variant

When the provider page is opened as a popup and the return page lives on your origin, the return page can `postMessage` its `location.search` back to the opener instead of rendering status itself; the opener closes the popup and navigates to a status page. Ref: `examples/paypal-external-page/` (`index.html` + `return.html` + `status.html`).

---

## Anti-Patterns

1. **Do not** branch redirect handling by payment method — one `redirect` path for PayPal, 3DS-redirect, and verification.
2. **Do not** ignore `method` — POST data forced into a GET URL → **414**.
3. **Do not** auto-open a new tab when `isNewWindowRequired` — use a click-triggered button.
4. **Do not** pre-open a blank tab on the "Pay" click hoping a `redirect` follows — you can't know the next action in advance, and speculative empty tabs are worse UX than one click. Same-tab (default) or the server-driven new-tab button only.
5. **Do not** add a "Continue" button for the **no-flag** case — that's the same-tab default; submit the form in the current window (a button there just costs a click).
6. **Do not** skip `returnUrl` — the user has no way back; 3DS-redirect fails outright.
7. **Do not** run `form.init()` on the return page — only `init()` + `setToken()` + `psdk-status`.
8. **Do not** mix `redirect` with the `3DS` (MPI challenge) handler — they are different actions.
9. **Do not** call `getStatus()` repeatedly when `psdk-status` is mounted — see `payment-status`.

---

## Quick Reference

| Resource                   | Path / URL                                                                                                            |
|----------------------------|-----------------------------------------------------------------------------------------------------------------------|
| RedirectActionData         | `src/core/actions/redirect/redirect.action.type.ts`                                                                   |
| psdk-redirect component    | `src/features/headless-checkout/web-components/redirect/redirect.component.ts`                                        |
| Manual + component example | `examples/credit-card/init-payment-flow.js`                                                                           |
| PayPal GET redirect        | `examples/paypal/index.html`                                                                                          |
| Popup / external page      | `examples/paypal-external-page/`                                                                                      |
| Return page                | `examples/return.html`                                                                                                |
| SDK / same-window methods  | `examples/sdk-payment-methods/index.html` (method context → `payment-methods`)                                        |
| Integrate on app side      | https://developers.xsolla.com/sdk-fuctional-and-ui/headless-checkout/integration-guide/integrate-on-app-side/index.md |

---

## Checklist

- [ ] `onNextAction` handles `redirect` — `psdk-redirect` with `data-redirect` JSON (or manual form honoring `method`)
- [ ] Window choice follows the rule: **iframe → new tab**; else `isNewWindowRequired` → new tab; else (incl. **no flag**) → same tab
- [ ] `isNewWindowRequired` → button + click gesture; `isSameWindowRequired` **and no-flag** → same tab (no button)
- [ ] `returnUrl` set in `form.init`; return page does `init` + `setToken` + `psdk-status`
- [ ] POST redirects use a form body (no 414); sandbox redirect completes and returns

**Done?** Method-specific flows (QR, mobile, cash, PayPal sandbox test) → `payment-methods`. Status rendering → `payment-status`. MPI in-page challenge → `credit-card-form`. Go-live → `docs`.
