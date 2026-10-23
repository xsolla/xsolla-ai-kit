# Native blocks: what they can and cannot express

Native blocks run catalog, cart, checkout, login and the legal footer for free, but their
layout is fixed. Fidelity comes from theming, assets and copy; anything the blocks below
cannot express is a gap to name up front (SKILL.md, Known limitations), not something to
work around.

This page is for **mapping and spotting gaps**. Block writes — adding, removing,
reordering, patching sections — belong to `shop-builder-assembly` (SKILL.md Step 3).
When a fact here changes what the brief needs, put it in the brief; don't patch the
block yourself.

Never rebuild catalog, cart, checkout or auth by hand. That path pulls in an OAuth client,
redirect URIs, PKCE and the Pay Station script, and it will drift from the platform.

## `header`

Holds `logo`, nav `button`s, `locale-select`, `burger` and `user-info`, arranged via
`leftComponents` / `rightComponents` / `fixedComponents` (arrays of component ids — safe
to reorder). Nav buttons scroll via `action.targetId` = `<module>/<blockId>`.

`user-info` is the login / cart / balance cluster and it **renders nothing without a
session**, so a logged-out page shows an empty header right side. Don't chase it as a
theming bug. Keep the store block's own `loginButton` enabled, otherwise the page has no
way to sign in at all.

## `newStore`

The product grid. This is where the money moves; it stays native however far off the comp
it looks.

- Sections live in `components[].section.item` = `{type, group}`. Patch them individually;
  never replace the `components` array wholesale.
- `values.tabs` (`{enable, type:"anchors"}`) renders a tab bar from the section titles.
  **Observed:** with anchors on, the per-section titles are spent on that bar and do not
  also render as headings above each row. If the comp wants both, pick one and say which.
- `card.layouts.<type>` controls the card: `image.{enable,format,size}`,
  `itemsDescriptionEnabled`, `priceInButton`. `image.format` is `"square"` everywhere and
  is **not validated server-side**, so a wrong value is stored without error. Don't
  guess values — read them from the GUI or an existing block; `image.size: contain`
  shrinks art inside the frame.
- Cannot express: rotated badge circles ("BEST VALUE", "+20% BONUS"), ribbons, timers,
  purchase counters, or any card order other than art → name → description → price
  button. If the comp puts the amount in a band above the art, that's not reachable.
  This is the card-layout gap in Known limitations — raise it in Step 1.
- Card copy comes from the **catalog**, not the block — name, description and image are
  item fields. Changing them is a catalog change — hand it to `catalog-design`.

## `leadGameSales` — hero

Has `title`, `subtitle`, `tags.items` (chips), `buttons`, `platforms`, and a section
`background`. Button actions are limited to `scroll` / `lightbox` / `pwa` — **there is no
buy action**, so a hero "$4.99" button can only scroll to the store.

It exposes **no image slot**, only the section background, so comp art has to be
composited into a background image. No countdown, no badge, no bordered inner panel.

## `faq`

Renders the accordion. `enable: false` on a question component does **not** hide it —
remove it with `{"op":"remove","path":["components",<i>]}`.

## `footer`

`logo`, `description`, a `social` component (toggle names in `value[]`) and a
`contentRating` badge strip. It also emits platform rows such as the affiliate link and
the "do not sell or share my personal information" notice. Those are compliance surface —
keep them even when the comp leaves them out.

## After assembly removes a block

Deleting a native block leaves **dangling scroll anchors** in the header nav pointing at
the removed `<module>/<blockId>`. Check after assembly's run, and report any to it
rather than repointing them here:

```bash
xsolla shopbuilder get-structure --slug <slug> --json
# every targetId's trailing id must still be a block on the page
```
