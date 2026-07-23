# Testing (headless, sandbox)

Guide for an AI agent driving Headless Checkout end-to-end with Playwright/Puppeteer.
Method-specific recipes live in their references (card matrix + card driving →
`credit-card-form`; PayPal sandbox login → `payment-methods`). This doc is the
**cross-cutting gotchas that cost the most time** — read it before writing a driver.

## 1. Secure fields: `fill()` vs real keystrokes — opposite per field

Card inputs are cross-origin secure iframes. *How* you type matters, and it **differs by
field type**:

- **Card number / CVV / expiry → real keystrokes** (`pressSequentially` / char-by-char
  `type`). `fill()` sets the value in one shot without firing the field's listeners, so it
  stays `INVALID` and **submit silently does nothing** — no NextAction, no error.
- **ZIP (and similar plain text) → `fill()`**. `pressSequentially` intermittently
  **reorders** characters (`10001` → `00011` / `0001`) — sometimes accepted (junk zip),
  sometimes rejected (*"Enter a valid Zip"*). Classic flake: same code green, then red.

**Debug rule: read `inputValue()` back after typing.** "The form just sits there" is
indistinguishable from ten other causes until you see the field actually holds `00011`.
Check the value first, not last.

## 2. Submit: click the host, and retry

`psdk-submit-button`'s click handler is on the **host element**, not the inner `<button>`.
A forced click on the inner button doesn't reach it → silent no-op. **Click the
`psdk-submit-button` host.** The first click is also occasionally swallowed (secure-iframe
timing) — **click, wait, re-click if the form is still there.**

## 3. Uncheck "save the method" when testing a payment

The save-card / save-method checkbox (`allowSave`) is usually **ticked by default**. Leave
it off for every test **except** the saved-methods flow itself — a saved method changes the
provider flow (e.g. PayPal goes to a billing agreement `/agreements/approve` instead of a
one-time `/checkoutnow`, with a different page your steps won't match) and can leave state
behind between runs.

## 4. Driver artifact vs real bug

The swallowed-first-click / "needs two clicks" above is a **Playwright timing artifact**,
not real UX — a real user's click registers. Before reporting a "double-click bug,"
confirm against real behavior, and don't let a submit-retry **mask a genuine second step**
(e.g. a terms/`show_fields` step that really does need another submit). Read state to tell
them apart, rather than trusting the symptom.

## Done = a real transaction on `psdk-status`

Rendering the form is not "done." Drive an actual sandbox payment to a terminal
`psdk-status` and report the screen you observed. Per-method recipes: card matrix →
`credit-card-form`; PayPal login → `payment-methods`; wallet notes → `google-pay` /
`apple-pay`.

**Sandbox ceiling:** only Card / PayPal / Apple Pay / Google Pay run their real flow; QR, mobile, and cash
collapse to a generic sandbox flow (→ success) and are verifiable **only in production**. See
`payment-methods` → "Sandbox can't exercise these flows".
