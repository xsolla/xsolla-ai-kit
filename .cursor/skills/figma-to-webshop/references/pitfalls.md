# Pitfalls

Every one of these produced a clean `ok: true` or a clean read while the page, the
catalog or the verification was wrong. Skim the list before Step 2 and again when
something "succeeded" but did not take effect.

## The expensive one: delivering the option the user rejected

`create-custom-block` and `update-ai-block` authenticate with the publisher
`pa-v4-token` cookie (`XSOLLA_SHOPBUILDER_SESSION`), **not** the bearer token from
`xsolla auth login` that every other shopbuilder command uses. A plain login session
therefore 403s `not_enough_permissions` on both — on any landing, including one that
already carries `federated` blocks. `get-ai-block` still reads fine, so a successful read
proves nothing about your ability to write.

What makes this costly is the ordering. `header`, `newStore` and `footer` are native and
keep working, so a run that has lost custom blocks can sail through bootstrap, assets and
theming and arrive at a complete, well-themed, **native-only** page — which, if the user
asked for custom blocks, is precisely the page they ruled out. Explaining the 403 in the
final handover does not fix that; the deliverable is still wrong.

- Probe the write at Step 0, before Step 1's question, and don't offer options the probe
  ruled out.
- On a custom-blocks build, publish the first block immediately after the page exists —
  before assets, before theme.
- When it 403s, stop and report in that turn. Falling back to native is the user's call,
  not a recovery you make on their behalf.

### The Step 0 probes

Run both against a throwaway or pre-existing landing. Delete the probe block if it
succeeds — don't leave it on a real page.

```bash
xsolla shopbuilder create-custom-block --landing-id <L> --page-id <P> --name Probe \
  --component-code 'import React from "react";
export default function Probe(){ return <div/>; }' --json
xsolla shopbuilder enable-preview --slug <any existing slug> --json
```

`403 not_enough_permissions` on the first → custom blocks are unavailable to this session
on every landing. `403 admin_privileges_requred` on the second → no screenshot path.

### The unblock

```bash
# publisher.xsolla.com → DevTools → Application → Cookies → copy pa-v4-token
export XSOLLA_SHOPBUILDER_SESSION='pa-v4-token=<value>'
```

## Blocks, theming and text

1. **Theme patched, nothing changed.** You patched `theme.input`. Patch
   `theme.calculatedTheme` — see Step 3.
2. **A section background image never appears.** Its `background.color` is opaque and
   paints over `background.img`. Set the color to `rgba(0,0,0,0)`.
3. **Body copy renders in a serif.** Localized rich text must be **HTML** — a bare string
   renders unstyled and falls back to the browser serif. Wrap it in `<p>`/`<h2>`. Control
   labels (nav items, button text) are fine as bare strings.
4. **`update-many-localization` needs a `perScopeValues` wrapper.** A flat
   `{"locale":..,"values":{..}}` body 400s with `perScopeValues must be an object`. The
   scope key is the **page `_id`** (or `common`), so the shape is
   `{"locale":"en-US","perScopeValues":{"<pageId>":{"L:<uuid>":{"translation":"Home"}}}}`.
5. **Text edits silently do nothing.** Block text lives in a separate localization store
   keyed by the slug, not in the block. Patching `values.title` returns `ok: true` and
   changes nothing. Use `update-many-localization`, where each value must be
   `{"translation": "<html>"}` — a bare string writes empty.
6. **`enable: false` doesn't hide a FAQ row.** Remove the component:
   `{"op":"remove","path":["components",<i>]}`.
7. **Deleting a block leaves dangling scroll anchors.** Header nav `targetId`s are
   `<module>/<blockId>`; repoint them or the links break silently.
8. **Don't guess undocumented enums.** The card's `image.format` is not validated
   server-side — it accepts garbage and the renderer then misbehaves. Change
   `image.size` (`cover` → `contain`) instead, and read real values off the GUI.
9. **Don't edit in the GUI and the CLI at once** — concurrent edits desync the document.
10. **A currency package must hold exactly one currency.** `admin-create-currency-package`
    rejects two with `[0401-4305]`. Comp cards that read "25,000 Simoleons + 1,425 SimCash"
    are therefore **bundles**, not currency packages — `admin-create-bundles` takes multiple
    currencies in `--content` and is the right model for any combo card.
11. **A freshly created bundle is invisible to the storefront.** `admin-create-bundles`
    has no `--is-show-in-store`, and the item will not appear in `list-catalog-bundles`
    until you run `admin-unhide-bundle --bundle-sku <sku>`. Do it for every item you
    create, then re-check.
12. **Storefront *group* listings lag; a single-SKU read does not.** Right after a write,
    `list-catalog-bundles-by-group` can return `items: []` while
    `get-catalog-bundle --sku <sku>` already shows the item with its group and price.
    Trust the SKU read and re-check the group a minute later — don't rebuild anything.
13. **A fresh `newStore` ships with four sections, not one.** Inspect the whole
    `components` array before patching; `components[0]` is not the only one, and the
    extras come pre-bound to arbitrary groups. Remove the spares in **descending** index
    order so the indices don't shift under you.
14. **One `newStore` block renders its sections contiguously.** If the comp puts a
    decorative band *between* two product rows, you need two `newStore` blocks, not one
    block with two sections.
15. **`verify-website` is currently broken** — it posts without `draftPagesIds` and the
    backend 400s on it. Don't read that failure as a problem with your landing.
