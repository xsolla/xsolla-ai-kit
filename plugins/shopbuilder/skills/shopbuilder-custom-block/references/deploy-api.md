# AI Custom Block deploy API

The one part of a Shop Builder build with **no `xsolla shopbuilder` CLI command**. The custom
block is compiled and attached through the SiteBuilder AI Custom Block HTTP API. Everything else
around it (asset upload, id discovery, structure, publish readiness) has a CLI command — prefer
the CLI there and use these raw calls only for the deploy/compile/attach/iterate step.

## Auth and roots

Same `pa-v4-token` JWT the plugin stores in `XSOLLA_SHOPBUILDER_SESSION`. It is a secret — never
log or commit it; it expires (re-copy on 403).

| Value | What it is |
| --- | --- |
| `BASE` | `https://sitebuilder.xsolla.com` |
| `TOKEN` | the `pa-v4-token` value (= `XSOLLA_SHOPBUILDER_SESSION`) |
| `merchantId`, `projectId` | Xsolla merchant/project ids |
| `domain` | the landing slug (the **returned** domain, e.g. `voidwall-45e0`) |

```
projectPath = /api/merchant/{merchantId}/project/{projectId}
landingPath = {projectPath}/landing/{domain}
```

Every call sends `Authorization: Bearer <TOKEN>`, `Content-Type: application/json`,
`Accept: application/json` (asset upload is multipart but still sends the Bearer header).

## 1. Resolve `siteId` and `pageId`

Deploy is keyed by the site document `_id` and a page `_id`, not the slug. Get both from
`xsolla shopbuilder get-structure --slug <domain> --json` (`_id` at the root is `siteId`;
`pages[N]._id` is the `pageId`). The equivalent raw read:

```
GET {landingPath}/structure/internal
# response._id          -> SITE_ID
# response.pages[N]._id -> PAGE_ID
```

If the target page doesn't exist: `xsolla shopbuilder add-page ...` (or `POST {landingPath}/pages`
with `{ "name": "...", "path": "/..." }`), then re-read the structure for its `_id`.

## 2. Source contract

Fields sent to deploy (only `siteId`, `pageId`, `componentCode` are required):

- **`componentCode`** (required) — TSX/JSX source of the component that renders the block.
- **`settingsCode`** (optional) — TSX/JSX source of the editor settings panel.
- **`defaultData`** (optional) — JSON object stored as the block's `internalBlockValues` (its
  initial editable data and source of truth for configurable values).
- **`name`** (optional) — display name; derived from the source if omitted.

The injected in-component API for reading `internalBlockValues` / wiring settings is **not
pinned** — confirm it from a known-good example or the 400 diagnostics below. Write minimal,
deploy, read errors, iterate.

## 3. Deploy (create + compile + attach)

```
POST {projectPath}/ai-custom-block
body: { siteId, pageId, name?, componentCode, settingsCode?, defaultData? }
```

- **200** → `{ "blockId": "...", "host": "https://…/api/ai-custom-block/{blockId}/" }`. Compiled
  and attached; `host` serves its MF bundle.
- **400** → invalid body **or the code failed to compile**; body has a `details[]` array of
  compiler diagnostics. This is the iterate loop: fix the source and PUT (§5), or POST again if
  no `blockId` was created.
- **404** → site/page not found in this merchant/project scope (re-check ids / token scope).

## 4. Publish

```
POST {landingPath}/publication            body: {}
# keep some pages as drafts: {"draftPagesIds":["<PAGE_ID>"]}
GET  {landingPath}/publication/status     -> published | unpublished | in_progress
```

Then render the preview to verify (shopbuilder-storefront, "Render to verify").

## 5. Iterate / inspect / delete

```
PUT    {projectPath}/ai-custom-block/{blockId}   # same body shape; preserves internalBlockValues
                                                 # unless a new defaultData is sent
GET    {projectPath}/ai-custom-block/{blockId}   -> { blockId, aiSource:{block,settings}, internalBlockValues }
DELETE {projectPath}/ai-custom-block/{blockId}   # removes from every page, then deletes
```

Re-publish (§4) after any change you want live. `403` on update/delete → the block is outside
this merchant/project scope.

## 6. Images / assets

Prefer `xsolla shopbuilder upload-asset --type image --file <path> --landing-id <SITE_ID>`, then
put the returned CDN URL in `defaultData`. Raw equivalent (multipart, keyed by the `SITE_ID`):

```
POST {projectPath}/assets/{SITE_ID}/site   -F type=image -F file=@./hero.png;type=image/png
```

Images: `gif, png, jpeg, webp, bmp, ico, tiff, svg`. Fonts: `woff, woff2, ttf, otf`. Max 10 MB.

## Runtime bundle (reference / debugging, no auth)

```
GET {host}mf-manifest.json     # Module Federation manifest
GET {host}remoteEntry.js       # compiled bundle (Cache-Control: no-store)
```

## Verified vs. confirm

- **Verified** (from the API contract): all endpoints, methods, bodies, auth, id resolution,
  compile-on-deploy, the 400 diagnostics, publish, and that block data lives in
  `internalBlockValues`.
- **Confirm from a working example or the 400 diagnostics**: the exact in-component hook
  signatures for reading `internalBlockValues` and wiring settings. The compiler is the
  authority — this reference does not fabricate them.
