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
- **`enable-preview` / `preview-link` take `--slug` only** (no merchant/project flags).
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

## Block customization

- **`update-block` paths need the `values` prefix for blocks.** A block patch to `["title"]`
  returns ok and changes nothing; use `["values","title"]`. Site patches use document-root
  paths; page patches use `["theme",...]`.
- **Block text is HTML rich text.** Set `localized-value-descriptor.localizedString` values
  wrapped in `<p>` (or `<h1>` for a hero headline). Bare strings render in a flat "plain text"
  style. `get-structure` does not inline localized text (it returns `L:` ids); verify via the
  `update-block` response's `localizations` map.
- **`background.color` is a tint over the image.** An opaque color hides the image entirely.
  Keep it transparent or low-alpha and darken with `background.gradient`.
- **Store sections live in `newStore.components[]`.** Each has `section.item.group` and `type`.
  Types: `virtual_currency` (currency packages / top-up), `virtual_good` (items), `bundle`
  (bundles). Currency packages show via a `virtual_currency` section with group `__all__`, not
  by group or bundle type. Reorder by replacing the components array; there is no move op for
  components. Fresh blocks ship with `__test__/...` placeholder sections; replace them.
- **Federated-block images live in `resources.mediaValues["I:..."].src`.** Repoint that to a
  `upload-asset` CDN URL, and darken with the entry's `gradient`.

## Assets

- **`image_url` must be a public HTTPS URL.** `xsolla shopbuilder upload-asset --type image
  --file <path> --landing-id <id>` returns one, usable both as a block image and as a catalog
  `image_url`. The landing must exist first. There is no other upload path in the CLI.
- **A missing source file stays unset.** If the art does not exist, leave the image empty and
  flag it rather than substituting an unrelated image.

## The rule that prevents lost work

Never edit a landing in the Publisher Account editor while the CLI or admin API is also
writing to it. Concurrent writers overwrite each other, drop blocks, and create ghost
references that break the editor with "Block with id ... not found". Reload the editor to
clear a stale local draft; the saved server structure is usually intact.
