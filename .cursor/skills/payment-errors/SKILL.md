---
name: payment-errors
description: >-
  Error 3007, 0401-2000: most likely cause and fix when a sandbox test payment
  is blocked. 3007: subscription checkout fails before the card form.
  0401-2000: a Store API payment token call returns Exception with PayStation
  service. Use when a test payment, subscription checkout or payment token call
  fails with one of these codes. Asks before any change; sandbox projects only.
metadata:
  owner: j.manashti
  domain: payments
  status: draft
---

# Payment errors before the first sandbox payment

Two errors stop partners before their first sandbox test payment, and their
messages don't say the fix. For each one: the most likely cause, the fix, and
what to send support when the fix doesn't work.

## Rules

- **Say "most likely cause".** You can't see the project's settings. Never say
  you checked them or found the cause.
- **The retry is the check.** After each fix, the user retries the same payment.
  The same error means: go to the next cause.
- **Ask before changing anything**: code, request bodies, project settings.
  Publisher Account changes are clicks the user makes.
- **Sandbox only.** Sandbox means the token request has `"sandbox": true` (or
  `settings.mode: "sandbox"`) and checkout opens on `sandbox-secure.xsolla.com`.
  If the project takes real payments, or you can't tell, change nothing and go
  to [Contact support](#contact-support).
- In anything public, write IDs as `<merchant_id>` and `<project_id>`. Tokens and
  keys go to Xsolla support only.

## Error 3007: subscription checkout fails in sandbox

Checkout for a subscription plan fails in sandbox before the card form shows.

| Code | Most likely cause | Fix |
|------|-------------------|-----|
| 3007 | Subscriptions webhooks not activated | Click **Test** on the subscriptions webhooks page, then retry |
| 3007 | Plans created only through the API, so subscriptions aren't activated on the project (temporary) | Create one plan in Publisher Account, then retry |
| 3007 | Wrong integration type, or a project misconfiguration | Not fixable by the partner: contact support |

1. **Subscriptions webhooks.** Ask the user to open this page and click **Test**
   at the bottom. That activates the subscriptions part of the webhooks. Then
   retry the same checkout.

   ```text
   https://publisher.xsolla.com/<merchant_id>/projects/<project_id>/edit/webhooks/subscriptions
   ```

   Before they click, warn them: once subscriptions are active, the project's
   plans can also be bought on its live site.
2. **Plans created only through the API (temporary workaround).**
   <!-- TEMPORARY: remove this step and the table row marked (temporary) once projects activate subscriptions automatically. -->
   Ask whether every plan was created through the API (the Xsolla CLI counts).
   If so, ask the user to create one plan in Publisher Account under **Items
   catalog > Subscriptions**. Then retry.
3. **Anything else.** A wrong integration type or a project misconfiguration
   can't be fixed by the partner. Go to [Contact support](#contact-support).

## Error 0401-2000: Exception with PayStation service

The Store API payment token call returns
`[0401-2000]: Exception with PayStation service`.

| Code | Most likely cause | Fix |
|------|-------------------|-----|
| 0401-2000 | The request sends `settings.external_id`, but **Use external ID** is off for the project | Turn on **Use external ID**, or remove `settings.external_id` from the request |

1. Find the token request in the user's code, or ask for its body with keys
   removed. The kit's skills don't send `settings.external_id`; it comes from
   the partner's own code. If the field isn't there, this cause doesn't apply:
   go to [Contact support](#contact-support).
2. Ask which fix the user wants:
   - **Keep the field.** It ties each payment to an order in their system and
     blocks paying twice for one order. The user turns on **Use external ID**
     in **Project settings > Integration settings > Payments**, then saves.
     After that, every payment needs a new `external_id`, unique across sandbox
     and live, and the test payment in Publisher Account doesn't work while the
     option is on.

     ```text
     https://publisher.xsolla.com/<merchant_id>/projects/<project_id>/edit/advanced
     ```

   - **Drop the field.** Remove `settings.external_id` from the request. Edit
     the code only after the user says yes.
3. Retry the same token call. A token in the response means it's fixed. The
   same error: go to [Contact support](#contact-support).

Docs: [What is the external ID?](https://developers.xsolla.com/dev-resources/faq/payments/#faq_payments_q_new_transaction_external_id)

## Contact support

Xsolla support is the chat in Publisher Account. Send:

| Error | Include |
|-------|---------|
| 3007 | Project ID, merchant ID, subscriptions webhooks status, the purchase token that failed |
| 0401-2000 | Project ID, merchant ID, the token request body with keys removed, the full error response |

## Related skills

- `webhooks-impl`: subscription webhook events on the user's backend.
- `shop-setup`: the three ways to get a payment token.
- `production`: error 0002-0004 when leaving sandbox.
