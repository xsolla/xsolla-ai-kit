# Field notes: Shop Builder storefront

Non-obvious Shop Builder failures gathered across a full storefront build, with the fix for
each. Scope is the storefront; catalog, login, payments, and webhooks have their own skills.

## Auth and CLI

- **Shop Builder cookie is `pa-v4-token`.** Put its value in `XSOLLA_SHOPBUILDER_SESSION`.
  Not the legacy `ps2[user_session]`. It expires; a 403 on a `shopbuilder` call usually means
  re-copy it.
- **Two `xsolla` binaries.** A dev build carries `shopbuilder upload-asset` and the corrected
  flags; an older release does not. If `PATH` puts the release first, calls silently use the
  wrong binary (for example `upload-asset` returns "unknown flag: --merchant-id"). Call the
  dev binary by absolute path, or keep its directory first on `PATH`.

## Prerequisite

- **The catalog must already exist.** The store block renders the project catalog; with no
  catalog it shows leftover demo items or nothing. Build it first with `catalog-design`.

## Site and page

- **Only the `topup` landing type exists in the CLI.** It still supports blocks.
- **The page scaffolds asynchronously.** Right after `create-website`, `get-structure` shows
  no page; the page and default blocks appear after a beat or after `enable-preview`. Poll.
- **Page theme overrides site theme.** Editing only the site theme leaves the page looking
  default. Set the page theme (`type: "page"`, paths `["theme",...]`) for the look that ships.
- **`create-website --slug <x>` auto-suffixes the slug.** The created domain is e.g.
  `voidwall-45e0`, not `voidwall`. Capture `.data.domain` from the create response and pass it
  as `--slug` to `get-structure` / `enable-preview` / `preview-link`; the requested slug 404s.
- **`enable-preview` / `preview-link` take `--slug` only** (no merchant/project flags) — and the
  slug value is the returned domain, per the note above.
- **`verify-website` returns 404 on a topup landing.** Check readiness with `get-structure`.

## Blocks

- **`move-block` uses `--source`/`--destination`** (indices), for page blocks.
- **Async add race.** Sequential `add-block` calls can land out of order; add, then reorder.
- **Hosted modules add as `federated`.** `add-block --block sb-offer-chain` (and the other
  hosted ids) returns 500. Add `--block federated`, then set its `values` (`blockId`, `host`,
  `internalBlockValues`, `resources`) by cloning a working reference block.
- **The offer-chain block is a federated block.** There is no non-federated offer-chain module;
  `module: federated`, `blockId: sb-offer-chain`. It references an existing offer chain by
  `internalBlockValues.offerChainId`; create that entity elsewhere (liveops), out of scope here.
- **Header nav chrome cannot be removed via CLI.** The top nav (Store / Daily gifts / Rewards /
  Redeem code) is not in the landing structure or features and persists even after the matching
  blocks are deleted. Surface this limitation to the developer; do not try to work around it.

## Block customization

- **`update-block` paths need the `values` prefix for blocks.** A block patch to `["title"]`
  returns ok and changes nothing; use `["values","title"]`. Site patches use document-root
  paths; page patches use `["theme",...]`. Exception: `components` (store sections, FAQ
  questions) is patched at `["components"]`, block root — see below.
- **Block text is HTML rich text.** Set `localized-value-descriptor.localizedString` values
  wrapped in `<p>` (or `<h1>` for a hero headline). Bare strings render in a flat "plain text"
  style. `get-structure` does not inline localized text (it returns `L:` ids); verify via the
  `update-block` response's `localizations` map.
- **`background.color` is a tint over the image.** An opaque color hides the image entirely.
  Keep it transparent or low-alpha and darken with `background.gradient`.
- **Store sections and FAQ questions live in `block.components[]` — a sibling of `values`, not
  inside it.** Patch at `["components"]` (block root). `["values","components"]` and
  `values.questions` return `ok:true` and silently do nothing. Sections are `newStoreSection`,
  questions are `questionV2`. Copy `card.layouts` verbatim from the placeholder; only
  `selectedLayoutType` changes. Section `type`: `virtual_currency` (currency packages / top-up,
  group `__all__`, not by group/bundle), `virtual_good` (items), `bundle` (bundles). Reorder by
  rewriting the array; there is no move op.
- **A fresh `newStore` block shows Xsolla demo data until you replace `components[0]`.** Its
  placeholder `section.item.group` is `__test__/bundle` → "Mystic Kit" / "Test item" / a lone
  "Bundles" tab. `ok:true` and a healthy `get-structure` do not mean the real catalog renders —
  render the preview to confirm (see the storefront skill, "Render to verify").
- **`featured` layout is a single-item carousel** (one item + pagination dots, the rest hidden).
  Good as a hero/anchor; use a grid like `vertical` where the buyer compares items. It reads as
  "only one item loaded" — it isn't.
- **Federated-block images live in `resources.mediaValues["I:..."].src`.** Repoint that to a
  `upload-asset` CDN URL, and darken with the entry's `gradient`.

## Assets

- **`image_url` must be a public HTTPS URL.** `xsolla shopbuilder upload-asset --type image
  --file <path> --landing-id <id>` returns one, usable both as a block image and as a catalog
  `image_url`. The landing must exist first. There is no other upload path in the CLI.
- **A missing source file stays unset.** If the art does not exist, leave the image empty and
  flag it rather than substituting an unrelated image.

## Adjacent CLI corrections (out of storefront scope, seen in the same build)

- **`admin-update-currency-package` uses `--package-sku`,** not `--currency-package-sku`.
- **Subscriptions (`api.xsolla.com`) accept the `pa-v4-token` JWT** passed as `XSOLLA_TOKEN`,
  even though the same token is rejected by the publisher-account endpoints. Worth noting where
  the subscriptions skill implies only `xsolla auth login` works.

## The rule that prevents lost work

Never edit a landing in the Publisher Account editor while the CLI or admin API is also
writing to it. Concurrent writers overwrite each other, drop blocks, and create ghost
references that break the editor with "Block with id ... not found". Reload the editor to
clear a stale local draft; the saved server structure is usually intact.
