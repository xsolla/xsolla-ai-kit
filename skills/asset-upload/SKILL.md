---
name: asset-upload
description: >-
  Uploads item images to Xsolla storage and attaches them to catalog SKUs by
  setting `image_url` on virtual items, bundles, virtual currency, and
  currency packages via the Admin API. There is no catalog image-upload
  endpoint — images are uploaded to the Merchant file storage API first, then
  the returned CDN URL is written onto the item. Use when the developer wants
  to "upload item images", "set image_url", "add catalog images", "attach
  icons to virtual items / bundles / currency", "why is image_url null",
  "no CLI media upload for items", or after `catalog-design` leaves images
  unset because assets weren't hosted yet. Covers the Publisher Account token
  needed for the upload step, the exact multipart field name, and the
  full-replace quirks in bundle/package payloads that make naive updates 422.
metadata:
  owner: a.springut
  domain: catalog
  status: draft
---

## Status

This skill is a **draft** authored by @a.springut, based on a live run against a
production project (see "Agent test" below).

Detailed material lives in `references/`:
- [`references/payload-shapes.md`](references/payload-shapes.md) — exact GET→PUT
  transforms per item type (groups, content, vc_prices) and the errors you get
  without them

## When to use

Use this skill once a catalog already exists (`catalog-design`) and the developer
wants item art attached:

- Uploading local image files and setting `image_url` on virtual items, bundles,
  virtual currency, or currency packages
- Debugging why `image_url` comes back `null` after `catalog-design` ("no general
  catalog media upload in the CLI" is the usual note left behind)
- Fixing a `422` on an image-setting update that looks unrelated to images (e.g.
  "Item default price not set", or an error mentioning `content[0]`)
- Deciding where image assets should live when there's no Xsolla-native path (a
  subscription plan, for example, has no image field at all)

Out of scope: designing the catalog itself, pricing, groups, or purchase flow
(→ `catalog-design`); Site Builder / Shop Builder landing-page assets, which have
their own asset-upload flow through the SiteBuilder API, not this one.

## Prerequisites

```bash
export XSOLLA_MERCHANT_ID=<your merchant ID>
export XSOLLA_PROJECT_ID=<your project ID>
export XSOLLA_API_KEY=<your API key>          # catalog admin reads/writes
export XSOLLA_PUBLISHER_TOKEN=<pa-v4-token>    # upload step only, see below
```

- A catalog already populated by `catalog-design` — this skill only attaches
  images to SKUs that exist.
- **A Publisher Account session token for the upload step.** The merchant API key
  (`XSOLLA_API_KEY`) does **not** authenticate the file-storage endpoint — it
  returns `publisher_auth_incorrect_token`. Get the PA token from a logged-in
  <https://publisher.xsolla.com> session: DevTools → Application → Cookies →
  `pa-v4-token`, or the `Authorization: Bearer …` header on any PA XHR. It's a
  JWT (three dot-separated segments) that expires in roughly 10 days — there is
  no programmatic way to mint one, so this step needs a human with PA access.
- **Xsolla MCP (strongly recommended).** Verify the admin item/bundle/currency
  request schemas with `search_xsolla_sources` before writing — this skill
  covers the image-specific transforms, not the full item schema.

## Steps

1. **Map each SKU to a local asset.** List the target SKUs via the relevant
   admin "Get list" call per item type and match each to a file on disk. Flag
   any SKU with no matching asset rather than guessing — leave its `image_url`
   unset and report it.

2. **Upload each unique asset to Xsolla storage (Merchant API).** One request
   per distinct file (skip re-uploading assets shared by multiple SKUs):

   | | |
   |---|---|
   | Method & path | `POST https://api.xsolla.com/merchant/current/merchants/{XSOLLA_MERCHANT_ID}/images` |
   | Auth | `Authorization: Bearer <XSOLLA_PUBLISHER_TOKEN>` |
   | Body | `multipart/form-data`, field literally named **`image`** (**not** `file` — that 422s with "No image in request body") |
   | Returns | `{ "image_url": "//cdn3.xsolla.com/img/misc/images/<hash>.jpg" }` |

   The returned URL is **protocol-relative** — prepend `https:` before writing
   it anywhere. Cache the SKU→URL map; the patch step below never needs the
   Publisher token again, only the API key.

3. **GET each item before updating it.** Admin update calls **replace** the
   item, they do not merge — the same rule `catalog-design` calls out for
   prices and limits applies to images. Fetch the current object first so
   nothing else gets dropped.

4. **Set `image_url` and PUT the item back — with type-specific transforms.**
   Virtual items and virtual currency accept the GET shape almost as-is.
   Bundles and currency packages do not: GET returns `groups`, `content`, and
   (for bundles) `virtual_prices` fully expanded, but PUT rejects that shape.
   See [`references/payload-shapes.md`](references/payload-shapes.md) for the
   exact before/after per field — skipping this step is the single biggest
   source of 422s in this flow, including one that looks like a pricing bug
   (`errorCode 4055`, "Item default price not set") and isn't.

5. **Verify.** Confirm the CDN URL serves the right file (status 200, content
   type `image/*`, byte length matching the local asset), then re-fetch the
   catalog through the **client-facing** Catalog API (no admin auth, no
   `country` param) and confirm `image_url` is populated there too — that's
   what the storefront actually reads.

6. **Do a lossless round-trip check before a bulk run.** PUT one item back
   unchanged (no image update), GET it again, and diff every field against
   the pre-run backup. If anything besides the field you intended to touch
   changed, the payload shape is wrong — fix it before writing the other 29.

## Common pitfalls

- **Using the API key for the upload step.** `XSOLLA_API_KEY` authenticates
  every admin catalog call in this flow except the upload itself, which
  returns `publisher_auth_incorrect_token` and needs the PA token instead.
  Easy to miss because every other step in `catalog-design` uses the API key.
- **Wrong multipart field name.** `file=` (correct for the CSS-upload flow in
  `login-styling`) is wrong here — this endpoint wants `image=`. Symptom: 422
  "No image in request body" even though the request clearly has a file.
  and the response is protocol-relative, unlike the CSS endpoint's absolute
  `file_url`.
- **PUTting the GET shape back unchanged.** Bundle `content` and `virtual_prices`
  come back fully expanded (nested name/description objects); PUT wants
  `content` reduced to `{sku, quantity}` and the bundle's VC prices renamed
  from `virtual_prices` to `vc_prices` and reduced to `{sku, amount,
  is_default}`. Sending the GET shape back 422s — see
  [`references/payload-shapes.md`](references/payload-shapes.md).
- **Assuming every catalog entity has an image field.** Subscription plans
  (`GET .../subscriptions/plans`) have no image/icon/media field at all —
  don't spend time hunting for one; render plan art client-side instead.
- **Skipping the backup/diff.** Because updates replace the whole object, a
  bad transform silently drops fields (limits, periods, regions) instead of
  erroring. Diff before/after against a pre-run backup, not just the HTTP
  status code.

## Agent test

Prompt: "Use the AI kit plugin to upload images to the catalog."

Live run on production project `311437` (2026-08-05): the agent discovered no
catalog image-upload API exists, found the Merchant file-storage endpoint,
diagnosed that the merchant API key doesn't authenticate it, and asked for a
Publisher Account token. With it: mapped all 30 SKUs (19 items, 4 bundles, 5
currency packages, 2 currencies) to local assets with zero misses, uploaded
each unique file once, discovered the `image` field name and the
protocol-relative response by probing 401/422 responses, then hit 422s on
bundles and packages from the `groups`/`content`/`virtual_prices` shape
mismatch and root-caused each via targeted payload variants. Backed up the
full catalog first and diffed every field before/after the real run: 30/30
`image_url` set, all 30 CDN URLs verified byte-identical to the local files,
public Catalog API confirmed serving them, and zero unintended field changes
across content, prices, and visibility. Flagged the one entity, a subscription
plan, with no viable image field rather than forcing one. ✅
