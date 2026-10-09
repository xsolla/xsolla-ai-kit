---
name: figma-to-webshop
description: Turn a Figma design (or any mockup, comp, or exported HTML) into a live Xsolla webshop with xsolla-cli — read the design, triage each section into native Shop Builder blocks vs. custom blocks, wire the catalog, match the palette and fonts, and iterate against screenshots until it matches. Use when someone shares a figma.com link, a design file, a mockup, or a screenshot and wants it built as a webshop, storefront, or landing page; or says "recreate this design", "build this in Site Builder", "match the comp", "make it look like the design", "pixel-perfect webshop", or "convert Figma to a shop".
metadata:
  owner: r.addoumie
  domain: design
  status: draft
---

# Figma → Xsolla webshop

Builds a Shop Builder site that matches a design comp — the **triage and fidelity layer**
over **shopbuilder** (command reference for landings, blocks, theming, assets,
localization; read it, this skill does not repeat it), **catalog-admin** (build the
catalog the store renders) and **webshop-checkout** (the buyer cart/checkout runtime).
The core tradeoff: native gives you catalog, cart, checkout and login for free but fixes
the layout; a custom block matches the comp exactly but owns nothing. Splitting on
*function* usually gets both and is what you should **recommend** — but it is not yours to
decide. Step 1 says to ask.

## Step 0 — project, catalog, capability, design (do not skip)

| Do | Why |
|---|---|
| `xsolla config list` → read back `merchant-id` / `project-id` and **confirm with the user** | Shop Builder is per-project; a `newStore` renders only its own project's catalog |
| `xsolla shopbuilder list-websites --json` | Near-duplicate site names are common — confirm you are building a new one, not editing a lookalike |
| `xsolla catalog list-item-groups --project-id <p>` | **The catalog may already exist.** Groups map 1:1 to the comp's store sections |
| Probe `create-custom-block` and `enable-preview` | Both authenticate off the publisher `pa-v4-token` cookie, not the bearer token the rest of the CLI uses, so both refuse *at the moment of use* — long after the build is committed to a path |
| Read the design → [read-the-design.md](references/read-the-design.md) | Leaves you a section inventory and a token sheet |

`403 not_enough_permissions` on `create-custom-block` means **custom blocks are
unavailable to this session entirely**, on every landing; `403 admin_privileges_requred`
on `enable-preview` means no screenshot (Step 5). **If the first fails, say so in Step 1
and drop the options you cannot build** — offering a choice you cannot deliver is how a
build ends up as the thing the user didn't pick. Commands and the unblock:
[pitfalls.md](references/pitfalls.md#the-expensive-one-delivering-the-option-the-user-rejected).

Auth: `xsolla auth login` (add `--audience https://api.xsolla.com` if it errors on
audience). Catalog **writes** use Store Basic auth (merchant id + API key) — a different
credential, read from the OS keychain *or* `XSOLLA_API_KEY`, so an unset env var does
**not** mean you lack it. Probe before declaring a blocker; data back means catalog writes
are available, and without them you cannot change item names, prices or images:

```bash
xsolla catalog admin-get-currency-package --project-id <p> --package-sku <known-sku>
```

## Step 1 — ask which blocks to build with, then inventory

**Ask explicitly, before any triage or any write. Do not pick for them.** This decision
sets the whole build and reversing it means rewriting every store block. Put the options
to them **minus any the Step 0 probe ruled out** — only "Standard" survives a failed
custom-block probe, and an option you cannot build is not an option; say why it is missing
rather than listing it and hoping.

| Answer | What you build | What it costs |
|---|---|---|
| **Standard (native) blocks** | `header`, `newStore`, `footer` do the work. Custom blocks only where nothing transacts. | Cards can't match the comp — fixed art→name→description→price order, no violators, ribbons, timers or counters. |
| **Custom blocks** | The comp's cards rebuilt in TSX, pixel-exact. | They own no commerce. Cart and checkout must still be native, so the buy button has to hand off — see "When the comp's card is non-negotiable" in [native-vs-custom.md](references/native-vs-custom.md). DOM-coupled and can break on a renderer change. |
| **Both** (recommend this) | Native for anything that transacts, custom for anything decorative. | Decorative sections match the comp; the product grid does not. |

Say two things out loud while asking, because they change the answer. **Whatever they
pick, cart, checkout and auth stay native** — rebuilding those by hand pulls in an OAuth
client, redirect URIs, PKCE and the Pay Station script, and drifts from the platform;
"custom blocks" means custom *cards*, not a custom checkout. And **a custom product grid
is not free**: it means a hand-off to a hidden native store plus a dependency on Site
Builder's rendered DOM. If the comp's cards carry anything `newStore` cannot express — a
rotated violator, countdown, points ribbon, purchase counter — surface that in the
question rather than discovering it at Step 5.

Then mark every section top to bottom **functional** or **decorative** — against the
answer you got, not the default. If they chose custom blocks the product grid is custom
too, and the native store stays on the page only as the purchase engine.

| Section | Verdict | Why |
|---|---|---|
| Header (login, cart, balance) | functional | native — owns the session |
| Hero / welcome offer | decorative* | buttons only scroll → custom |
| Store heading + section tabs | decorative | in-page anchors → custom |
| Product grid | **functional** | native `newStore` — this is the money |
| FAQ | decorative | informational → custom |
| Marketing / download band | decorative | links only → custom |
| Footer | functional-ish | native — carries required legal rows |

\* A hero is decorative when its buy button only *scrolls* to the store. If it must
actually add to cart, keep it native.

### The answer is binding — never substitute the other option

If the chosen path turns out impossible mid-build — the custom-block write 403s, a block
won't compile, anything — **stop and tell them in that turn. Do not finish the build down
the other path.** `header`, `newStore` and `footer` keep working without custom blocks, so
the native build completes smoothly and delivers the one page they ruled out; explaining
the blocker in the final handover does not make that the right page. Say plainly that it
is blocked and why, give the exact unblock (for the 403, the `XSOLLA_SHOPBUILDER_SESSION`
cookie and a command they can run), say what is and isn't on the page **in that same
message**, and ask whether to wait or fall back. **Falling back is their call.** Corollary
— sequence so a blocker lands early and cheap: with custom blocks chosen, publish one as
soon as the page exists, before art and before theming. Full block-by-block capabilities
and limits: [native-vs-custom.md](references/native-vs-custom.md).

## Step 2 — bootstrap and shape

```bash
xsolla shopbuilder create-website   --name "<Name>" --slug <slug> --type topup
xsolla shopbuilder set-landing-type --slug <slug> --type store
xsolla shopbuilder add-page         --slug <slug> --name Main --path /
xsolla shopbuilder get-structure    --slug <slug> --json
```

The default page ships ~13 template blocks. Delete what the comp doesn't have, then add
`newStore`. Block commands key off the landing's Mongo `_id` (`--landing-id`), **not** the
slug. **On a custom-blocks build, do Step 4 before the asset upload below.**

Upload the art once — the CDN urls also work as catalog `--image-url` values:

```bash
xsolla shopbuilder upload-asset --landing-id <L> --file art.png --type image --json
```

**Never flatten a section — or a product card — into one raster image.** Baked text cannot
be selected, translated or localized, is invisible to screen readers, cannot reflow,
ignores the site theme, and turns an FAQ accordion into a picture that never opens. Export
**artwork** as assets (illustrations, textures, frames, ribbons, rosettes, icons) via
`download_assets`; rebuild **everything else** as DOM (text, buttons, tabs, accordions,
grids, spacing). Full rule: [read-the-design.md](references/read-the-design.md#slice-the-design-assets-rebuild-the-structure).

## Step 3 — theme

**Scale this to the native surface the page actually has.** Custom blocks ignore the site
theme, so a custom-blocks build only dresses `header`, `footer` and the clipped `newStore`
fallback — a dozen tokens, not a hundred; full sweep on native or mixed builds. Whatever
the scope, **this is the single biggest trap in the workflow**: on an `xds-theme` landing
the renderer reads `theme.calculatedTheme`, and patching `theme.input` succeeds, reads
back correctly and changes nothing on screen. Patch `calculatedTheme` directly — and the
token names do not mean what they say: the store card's buy button is driven by
`core.text.brand`, not by any `control.*` token. Patches go through `update-block` with **`"type": "site"`** and the
landing `_id`; `"landing"`, `"website"` and `"settings"` all return a 500:

```bash
xsolla shopbuilder update-block --landing-id <L> --data '{"r1":{"type":"site","id":"<L>",
  "patches":[{"op":"replace","path":["theme","calculatedTheme","colors","core","text","brand"],
  "value":"#edb51c"}]}}'
```

Full token map, font-upload contract and page-vs-site theme layers:
[theming-and-fonts.md](references/theming-and-fonts.md).

## Step 4 — custom blocks for the decorative sections

On a custom-blocks build this runs **before** Step 2's asset upload and Step 3's theme,
because it is the step that can be refused — publish the first as a stub if the real
markup isn't written yet; you are testing the write. **`403 not_enough_permissions` is not
about your landing**: it refuses on every one, including landings already carrying
`federated` blocks. Stop and follow Step 1, "The answer is binding".

```bash
xsolla shopbuilder create-custom-block \
  --landing-id <L> --page-id <P> --name "<Section>" \
  --component-code "$(cat section.tsx)"
```

TSX with a default-exported React component. It **appends** to the page, so follow with
`move-block --source <i> --destination <j>` to position it. Port the comp's markup
literally — same hex values, spacing and `box-shadow` — and load the comp's webfonts
inside the block so it doesn't depend on the site theme resolving them. "Port the markup"
means *markup*: a block whose render is one `<img>` of the section with transparent
buttons on top is a screenshot, not a custom block (Step 2). Text in a custom block is
still real text — it just lives in the component, not the localization store. Worked
example: [webshop-custom-block.tsx](references/webshop-custom-block.tsx).

## Step 5 — verify against a screenshot, not the API

`update-block` returning `ok: true` and a clean `get-structure` read is **not** evidence
that anything looks right. Get a rendered screenshot, then sample pixels to identify which
token actually drives an element rather than guessing.

You checked at Step 0 whether you can get one. `enable-preview` / `preview-link` need an
**account-level admin** token, not merchant owner (`partner_data.admin: false` → 403), and
a custom block's own `host` url 403s unauthenticated. When both are shut there is no CLI
path to a render, and publishing is not a substitute — you do not publish. Say so plainly
and have the user open the landing in the Site Builder GUI, rather than reporting an API
read-back as if it were visual confirmation. The loop, and the render traps that produce a
clean API read and a wrong page: [verify-and-iterate.md](references/verify-and-iterate.md).

## Common pitfalls

The ones that cost the most time, in full: [pitfalls.md](references/pitfalls.md).

| Symptom | Cause and fix |
|---|---|
| **You shipped the option the user rejected** | `create-custom-block` 403s late and native-only still completes. Probe at Step 0, build the first custom block before anything expensive, stop at the blocker — Step 1, "The answer is binding". |
| **Theme patched, nothing changed** | You patched `theme.input`. Patch `theme.calculatedTheme`, via `update-block` with `"type": "site"` — Step 3. |
| **Text edits silently do nothing** | Block text lives in a separate localization store, not in the block. Use `update-many-localization`, each value `{"translation": "<html>"}`. |
| **A fresh bundle is invisible to the storefront** | Not shown until `admin-unhide-bundle`. A combo card ("25,000 Simoleons + 1,425 SimCash") must be a **bundle** — a currency package may hold exactly one currency. |
| **Nav links break silently** | Deleting a block leaves dangling scroll anchors. Header nav `targetId`s are `<module>/<blockId>`; repoint them. |

## Examples

- "Here's our Figma — build it as a webshop in my sandbox project."
- "Recreate this design 1:1, use custom blocks only where you have to."
- "The theming is off, iterate until it matches the comp."
- "Make the hero match the design exactly but keep checkout native."
