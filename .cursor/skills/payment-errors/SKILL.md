---
name: payment-errors
description: >-
  Error 0401-2000: most likely cause and fix when a Store API payment token
  call returns Exception with PayStation service. Most likely the request sends
  settings.external_id while the project's Use external ID option is off. Use
  when a payment token call fails with this code. Proposes only changes the user
  makes themselves, and names each change's effect on the live site before
  asking.
metadata:
  owner: j.manashti
  domain: payments
  status: draft
---

# Payment errors

Error 0401-2000 can stop partners before their first sandbox test payment, and
its message doesn't say the fix. This skill gives the most likely cause, the fix,
and what to send support when the fix doesn't work.

## Rules

- **Say "most likely cause".** You can't see the project's settings. Never say
  you checked them or found the cause.
- **The retry is the check.** After the fix, the user retries the same token
  call. The same error means: go to [Contact support](#contact-support).
- **The user makes every change.** Each fix is a Publisher Account setting or the
  user's own code. Propose it; don't make it. Project settings apply to the live
  site too, so before you ask, say what each change does there.
- In anything public, write IDs as `<merchant_id>` and `<project_id>`. Tokens and
  keys go to Xsolla support only.

## Error 0401-2000: Exception with PayStation service

The Store API payment token call returns
`[0401-2000]: Exception with PayStation service`.

| Code | Most likely cause | Fix |
|------|-------------------|-----|
| 0401-2000 | The request sends `settings.external_id`, but **Use external ID** is off for the project | Turn on **Use external ID**, or remove `settings.external_id` from the request |

Where the cause comes from: called directly, the Pay Station token API answers
this request with a clear message about `settings.external_id`. The Store API
wraps that answer as 0401-2000, so the field's name never reaches the user.

1. Find the token request in the user's code, or ask for its body with keys
   removed. The kit's skills don't send `settings.external_id`; it comes from
   the partner's own code. If the field isn't there, this cause doesn't apply:
   go to [Contact support](#contact-support).
2. Ask which fix the user wants, and say what each one does on the live site:
   - **Keep the field.** It ties each payment to an order in their system and
     blocks paying twice for one order. The user turns on **Use external ID**
     in **Project settings > Integration settings > Payments**, then saves:

     ```text
     https://publisher.xsolla.com/<merchant_id>/projects/<project_id>/edit/advanced
     ```

     On the live site: it's a project setting, so live payments follow it too.
     Every payment needs a new `external_id`, unique across sandbox and live,
     and the test payment in Publisher Account doesn't work while the option is
     on. To run that test payment, the user can turn the option off for the
     test. While it's off, any request that sends `settings.external_id` fails
     again, so turn it back on right after the test.
   - **Drop the field.** Show the user the exact line that sets
     `settings.external_id`; they remove it. On the live site, once that code is
     deployed: Xsolla no longer ties those payments to the user's order IDs, so
     it can't block a second payment for the same order.
3. Retry the same token call. A token in the response means it's fixed. The
   same error: go to [Contact support](#contact-support).

Docs: [What is the external ID?](https://developers.xsolla.com/dev-resources/faq/payments/#faq_payments_q_new_transaction_external_id)

## Contact support

If the retry still fails, or the request has no `settings.external_id`, contact
Xsolla support through the chat in Publisher Account. Send:

| Error | Include |
|-------|---------|
| 0401-2000 | Project ID, merchant ID, the token request body with keys removed, the full error response |

## Related skills

- `shop-setup`: the three ways to get a payment token.
- `production`: error 0002-0004 when leaving sandbox.
