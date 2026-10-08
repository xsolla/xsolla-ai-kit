# Native block or custom block?

The rule: **native for anything functional, custom for anything decorative.** Native
blocks run catalog, cart, checkout, login and the legal footer for free, but their layout
is fixed. A custom block matches a comp exactly but owns no behaviour. Split on function
and you keep both.

Never rebuild catalog, cart, checkout or auth by hand inside a custom block. That path
pulls in an OAuth client, redirect URIs, PKCE and the Pay Station script, and it will
drift from the platform. If a custom block genuinely needs the player, have it consume
the session Site Builder already holds.

## What the native blocks can and cannot express

### `header` — always native

Holds `logo`, nav `button`s, `locale-select`, `burger` and `user-info`, arranged via
`leftComponents` / `rightComponents` / `fixedComponents` (arrays of component ids — safe
to reorder). Nav buttons scroll via `action.targetId` = `<module>/<blockId>`.

`user-info` is the login / cart / balance cluster and it **renders nothing without a
session**, so a logged-out page shows an empty header right side. Don't chase it as a
theming bug. Keep the store block's own `loginButton` enabled, otherwise the page has no
way to sign in at all.

### `newStore` — always native

The product grid. This is where the money moves; it stays native however far off the comp
it looks.

- Sections live in `components[].section.item` = `{type, group}`. Patch them individually;
  never replace the `components` array wholesale.
- `values.tabs` (`{enable, type:"anchors"}`) renders a tab bar from the section titles.
  **Observed:** with anchors on, the per-section titles are spent on that bar and do not
  also render as headings above each row. If the comp wants both, turn `tabs` off and
  supply the bar as a custom block above the store.
- `card.layouts.<type>` controls the card: `image.{enable,format,size}`,
  `itemsDescriptionEnabled`, `priceInButton`. `image.format` is `"square"` everywhere and
  is **not validated server-side** — it accepted a deliberate garbage sentinel. Don't
  guess values; change `image.size` to `contain` to shrink art inside the frame.
- Cannot express: rotated badge circles ("BEST VALUE", "+20% BONUS"), or any card order
  other than art → name → description → price button. If the comp puts the amount in a
  band above the art, that's not reachable.
- Card copy comes from the **catalog**, not the block — name, description and image are
  item fields. Changing them needs Store Basic auth (see SKILL.md Step 0 for the probe —
  the CLI reads that key from the keychain, not only from the environment).

### `leadGameSales` — hero; usually custom

Has `title`, `subtitle`, `tags.items` (chips), `buttons`, `platforms`, and a section
`background`. Button actions are limited to `scroll` / `lightbox` / `pwa` — **there is no
buy action**, so a hero "$4.99" button can only scroll to the store.

It exposes **no image slot**, only the section background, so comp art has to be
composited into a background image. That plus no countdown, no badge and no bordered
inner panel is usually enough to justify a custom block.

### `faq` — usually custom

Renders the accordion. `enable: false` on a question component does **not** hide it —
remove it with `{"op":"remove","path":["components",<i>]}`. Being purely informational, it
is a safe and high-value custom-block conversion when the comp has a specific look.

### `footer` — keep native

`logo`, `description`, a `social` component (toggle names in `value[]`) and a
`contentRating` badge strip. It also emits platform rows such as the affiliate link and
the "do not sell or share my personal information" notice. Those are compliance surface —
don't replace the footer with a custom block just to drop them.

## Writing a custom block

```bash
xsolla shopbuilder create-custom-block \
  --landing-id <L> --page-id <P> --name "<Section>" \
  --component-code "$(cat section.tsx)"
```

Contract: TSX, `import React from "react"`, a **default-exported** component. Returns a
`blockId` and host url. It **appends** to the page — reposition with `move-block`.

**Before you write any of it, check you can publish one.** This endpoint wants the
publisher `pa-v4-token` cookie in `XSOLLA_SHOPBUILDER_SESSION`; without it both
`create-custom-block` and `update-ai-block` 403 `not_enough_permissions` while the rest of
the CLI keeps working. Probe with a stub component at Step 0. If it fails, custom blocks
are off the table for this session — say so before the user picks a path, and never finish
the build native-only on the quiet.

```tsx
import React, { useEffect } from "react";

export default function HeroSection() {
  useGlobalStyles();          // inject the comp's webfonts + keyframes into document.head
  return <section style={{ /* values lifted verbatim from the comp */ }}>…</section>;
}
```

Guidelines that matter:

- **One block per interactive unit.** Blocks are separate federated remotes and cannot
  share React state, so anything with a shared cart or modal belongs in a single block.
- **Load the comp's fonts inside the block** (a Google Fonts `<link>` appended to
  `document.head`). This makes the block independent of whether the site theme resolves
  its fonts — and sidesteps that whole class of bug.
- **Custom blocks ignore the site theme.** They carry the comp's colors literally, so a
  later re-theme of the site will not follow. Say this out loud when handing over.
- **In-page scrolling** to a native section has no stable id to target. Locate the element
  (for example by matching a section heading's text inside the store block), scroll with
  an offset for the sticky header, and always provide a fallback.
- The compiled bundle is served with `cache-control: max-age=14400`, and updating a block
  in place keeps its URL — so browsers may hold the old bundle. When a change must be
  visible immediately, delete the block and create a new one to get a fresh URL.

## When the comp's card is non-negotiable

Sometimes the product card itself *is* the design — baked art, a rotated violator, a
timer, a points ribbon — and `newStore` cannot express it. You can have the comp's card
without hand-rolling commerce: **render the cards in a custom block and keep the native
`newStore` on the page as the purchase engine.**

- Leave both the custom band and the native store block on the page. On mount the custom
  block moves the native band off-screen (`position:fixed; left:-99999px`, `overflow`
  left `visible` so a modal parented inside it still shows).
- Each custom card's buy button finds the native card for the **same product name** and
  forwards the click. Cart, upsell, login gate and Pay Station all stay native.
- Mark your own roots `data-sc-custom="..."` and exclude `[data-sc-custom]` from the text
  search, or your cards match their own product names instead of the native ones.
- **Guard the walk-up.** Finding the band means walking *up* from a text node, so a bad
  match can clip a page-level wrapper and blank the site. Refuse to clip any node that
  contains `[data-sc-custom]`, contains the header, or is most of the document's height.
- **Clipping the store also hides its `loginButton`**, which is the only sign-in on the
  page — the header's `user-info` renders nothing logged out. Render the comp's
  logged-out state in your block and proxy it to that native button
  (`blocks.newStore.values.storeLoginButton`, "Log in to see more offers" in en-US). Its
  presence is also a reliable signed-out signal, since Site Builder only renders it
  without a session.
- Re-apply the clip on an interval for a few seconds: the native block may mount after
  yours and may re-render.

This is DOM-coupled by construction — a Site Builder renderer change can break the
hand-off silently. Always ship the escape hatch that restores the native store, and say
the tradeoff out loud when handing over.

## After you swap a block

Deleting a native block leaves **dangling scroll anchors** in the header nav pointing at
the removed `<module>/<blockId>`. Repoint them at the replacement, then confirm none are
left:

```bash
xsolla shopbuilder get-structure --slug <slug> --json
# every targetId's trailing id must still be a block on the page
```
