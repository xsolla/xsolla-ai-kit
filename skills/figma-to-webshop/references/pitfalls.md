# Pitfalls

Every one of these produced a clean `ok: true` or a clean read while the page, the
catalog or the verification was wrong. Skim the list before Step 4 and again when
something "succeeded" but did not take effect.

## The Step 0 preview probe

Run it against a pre-existing landing, before any build work:

```bash
xsolla shopbuilder enable-preview --slug <any existing slug> --json
```

`403 admin_privileges_requred` → no screenshot path for this session. Skip the screenshot
step and tell the user at Step 0, not at handover. Don't work around it with a session
cookie copied from the browser.

## Blocks, theming and text

Theme, asset and copy items apply to this skill's Step 4 writes. Block-structure items
(rows, sections, anchors) describe what `shop-builder-assembly` writes — use them to
read its result and fill the brief, not to patch blocks here.

1. **Theme patched, nothing changed.** You patched `theme.input`. Patch
   `theme.calculatedTheme` — see Step 4.
2. **A section background image never appears.** Its `background.color` is opaque and
   paints over `background.img`. Set the color to `rgba(0,0,0,0)`.
3. **Body copy renders in a serif.** Localized rich text must be **HTML** — a bare string
   renders unstyled and falls back to the browser serif. Wrap it in `<p>`/`<h2>`. Control
   labels (nav items, button text) are fine as bare strings.
4. **`update-many-localization` needs a `perScopeValues` wrapper.** A flat
   `{"locale":..,"values":{..}}` body 400s with `perScopeValues must be an object`. The
   scope key is the **page `_id`** (or `common`), so the shape is
   `{"locale":"en-US","perScopeValues":{"<pageId>":{"L:<uuid>":{"description":"<existing>","translation":"Home"}}}}`.
5. **Text edits silently do nothing.** Block text lives in a separate localization store
   keyed by the slug, not in the block. Patching `values.title` returns `ok: true` and
   changes nothing. Use `update-many-localization`, where each value must be
   `{"description": "<existing>", "translation": "<html>"}` — a bare string writes empty.
6. **A write without `description` clears it.** `description` is the string's dotted
   source path (`blocks.header.values.title`). Omit it and `update-many-localization`
   overwrites it with an empty string. Read the current one from `get-localization`
   (each entry carries `description` beside its `translations` map) and send it back with
   every translation; use `""` only for a string that has none yet.
7. **`enable: false` doesn't hide a FAQ row.** Remove the component:
   `{"op":"remove","path":["components",<i>]}`.
8. **Deleting a block leaves dangling scroll anchors.** Header nav `targetId`s are
   `<module>/<blockId>`; repoint them or the links break silently.
9. **Don't guess undocumented enums.** The card's `image.format` is not validated
   server-side — it stores anything and the renderer then misbehaves. Read real values
   from the GUI or an existing block; never write a test value to find out.
10. **Don't edit in the GUI and the CLI at once** — concurrent edits desync the document.
11. **A currency package must hold exactly one currency.** `admin-create-currency-package`
    rejects two with `[0401-4305]`. Comp cards that read "25,000 Gold + 1,425 Gems"
    are therefore **bundles**, not currency packages — `admin-create-bundles` takes multiple
    currencies in `--content` and is the right model for any combo card.
12. **A freshly created bundle is invisible to the storefront.** `admin-create-bundles`
    has no `--is-show-in-store`, and the item will not appear in `list-catalog-bundles`
    until you run `admin-unhide-bundle --bundle-sku <sku>`. Do it for every item you
    create, then re-check.
13. **Storefront *group* listings lag; a single-SKU read does not.** Right after a write,
    `list-catalog-bundles-by-group` can return `items: []` while
    `get-catalog-bundle --sku <sku>` already shows the item with its group and price.
    Trust the SKU read and re-check the group a minute later — don't rebuild anything.
14. **A fresh `newStore` ships with four sections, not one.** Inspect the whole
    `components` array before patching; `components[0]` is not the only one, and the
    extras come pre-bound to arbitrary groups. Remove the spares in **descending** index
    order so the indices don't shift under you.
15. **One `newStore` block renders its sections contiguously.** If the comp puts a
    decorative band *between* two product rows, you need two `newStore` blocks, not one
    block with two sections.
16. **`verify-website` is currently broken** — it posts without `draftPagesIds` and the
    backend 400s on it. Don't read that failure as a problem with your landing.
