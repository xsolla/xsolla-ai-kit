# Headless Web Shop quest module

In-catalog quest section for the **headless** storefront from
`shop-setup`. For a Shop Builder site use
[`quests-block-flow.md`](quests-block-flow.md) instead. Never a
top-level nav tab, router entry, or new shop route.

Triggers: "show quests in my web shop", "add quest module to shop", "quest
module", "catalog quests section".

## When to use

- **New shop** (during or after shop-setup): ask / confirm opt-in before adding.
- **Existing shop**: when the developer asks to add or update quests in the
  shop, run the upsert algorithm below.

An explicit request to integrate quests into an existing shop authorizes the
source edits. Do not respond with a plan that asks for approval, an open
question about language, or a request for the endpoint URL. Infer locale from
the shop's existing localization setup and use the configured public API
contract. Give a brief progress update only when the work takes long enough to
need one, then make the edits and run the shop's available checks.

Out of scope: user progress / completion UI, fabricating sample quests,
changing AdTech APIs. Shop Builder sites are handled by
[`quests-block-flow.md`](quests-block-flow.md), not here.

## Identity (source of truth)

**Required marker** on the module root:

```html
<section data-xsolla-quest-module="1" aria-label="Quests">
```

The attribute `data-xsolla-quest-module` is the only required identity.
An optional file hint `**/XsollaQuestModule.{tsx,jsx,ts,js}` may exist; prefer
updating the marked root when both are present. Do not require React.

**Stack adaptors (ordered):**

1. Detect the catalog page stack (React / Vue / Svelte / static HTML+JS / other).
2. Add or update a same-stack module that renders the marked root.
3. Default **new** shops to **static HTML + vanilla JS** unless the catalog
   page is already a component framework.

## Config and IDs

Resolve the merchant/project pair from the connected Quest Platform scope. Confirm the
merchant against the shop's setting; never infer or copy the Store catalog project ID.
Keep Store catalog/checkout settings intact. If QP scope is unresolved, ask which
connected QP project to use, never for an API URL or a sample ID.

Production public base is `https://quests-platform.xsolla.com`. Form the public URL
from it and the resolved QP scope. A validated exact URL/base override takes precedence
only if the shop already supports overrides or the developer supplied one. Never use
an internal/private host for a public shop. This browser override never changes the
agent's write host, which is the one in [auth-credentials.md](auth-credentials.md#credential).

Expose only IDs/public URL in browser build config, using the shop's naming convention:

| Setting | Role |
|---|---|
| `XSOLLA_QP_MERCHANT_ID` | QP path merchant; verify reuse of shop merchant |
| `XSOLLA_QP_PROJECT_ID` | QP path project, separate from Store catalog project when different |
| `XSOLLA_QP_PUBLIC_BASE_URL` | Optional validated public-base override |

For Vite use `VITE_XSOLLA_QP_MERCHANT_ID` / `VITE_XSOLLA_QP_PROJECT_ID`; for Next.js,
`NEXT_PUBLIC_XSOLLA_QP_MERCHANT_ID` / `NEXT_PUBLIC_XSOLLA_QP_PROJECT_ID`. Keep existing
Store settings such as `VITE_XSOLLA_PROJECT_ID` for catalog/checkout. These names are
code/config only, never reply content. No API keys or Authorization in browser code.

## Wire contract (consume verbatim)

`GET {base}/api/v2/public/merchants/{merchant_id}/projects/{project_id}/quests?page=1&limit=100`

No auth header. The maximum page size is 100. Build `{base}` from the production
default or an existing validated override.

**200 envelope:** `page`, `limit`, `total`, `data[]` with:

| Field | Rule |
|---|---|
| `data[].id` | Required string (UUID); list key |
| `data[].name` | Required string |
| `data[].description` | Optional; omit when absent |
| `data[].rewards` | Required array (may be empty) |
| `rewards[].name`, `rewards[].description`, `rewards[].image_url` | Present; may be **null**; skip nulls when rendering |
| `rewards[].quantity` | Required int |
| `rewards[].type` | Required string |

Empty success is a 200 response with `data: []`. Do not describe a failed
request as an empty quest list. A JSON 404 means the merchant/project pair is
unknown, not onboarded, or mismatched; re-check the resolved pair
without guessing. Plain-text `Cannot GET <path>` means the route
is unavailable at that host or the path is wrong. A 422, network, or CORS
failure is also unavailable, not empty. Show the neutral unavailable message
for fetch or missing-configuration errors, and keep the catalog working. Never
fabricate quests or rewards.

## Markup shape

Use the marked root from [Identity](#identity-source-of-truth), with a disclaimer,
loading text `Loading quests...` (`role="status"`, `aria-live="polite"`), and visible
empty/error text or articles keyed by `data[].id` (for example `data-quest-id`). Render
name, optional description and each reward's non-null name/quantity and safe image.
Use the fixed copy below, without repeating it in a second managed region.

**Fixed copy (exact):**

- Disclaimer: `Quests are configured by the publisher. Rewards are granted by the publisher when a quest is completed.`
- Empty: `No active quests right now.`
- Neutral error (optional): `Quests are temporarily unavailable.`

Place as a sibling **inside** the catalog content container (after or before
the product list). Never under `<nav>`, header tabs, or a top-level tablist.

**Accessibility:** empty and error text must stay visible (not
`display:none`-only). Images: use the reward name as `alt` when informative,
or empty `alt` when decorative. Do not put the disclaimer on a noisy
`aria-live` region.

Use the shop's existing localization system for new presentation copy. Keep
the fixed disclaimer, empty-state and neutral-error strings above exactly as
specified. Do not ask the developer to choose a language.

## Visual treatment

The module is part of the shop catalog, so render it as a deliberate catalog
section rather than a raw text dump. Keep the publisher's existing design
system and use the following hierarchy:

- section eyebrow, heading, and the fixed disclaimer;
- one card per quest with a readable title and description;
- a distinct reward row or card with media, reward name, description, quantity,
  and type badges;
- a neutral media placeholder when `image_url` is absent or rejected;
- visible loading, empty, and error states with the same spacing and typography
  as the populated state.

Use responsive layout rules for narrow screens: allow titles and descriptions
to wrap, keep reward media from collapsing, and avoid horizontal overflow.
Do not add a new navigation tab, route, or unrelated visual treatment. The
module should look native to the host shop and remain readable when quest names
or reward descriptions are long.

## Safe rendering (required)

- Set quest/reward text with `textContent`, framework text children, or
  auto-escaping templates only.
- **Forbid** `innerHTML`, `dangerouslySetInnerHTML`, and HTML string
  concatenation into markup for API strings.
- Images: only absolute `http:` / `https:` URLs. Skip relative, `javascript:`,
  `data:`, and other schemes. Set `loading="lazy"` and
  `referrerpolicy="no-referrer"` (or `strict-origin-when-cross-origin`).

## CORS and mixed content

Browser calls go from the shop origin to the Quest Platform public API. CORS depends on
the origins that API allows. On CORS failure, show the neutral error (or
hide the module) and keep the catalog working. When the shop is served over
`https`, the public base must also be `https` (no mixed-content HTTP). Never
send credentials (`credentials: 'include'`) on this fetch.

## Idempotent upsert algorithm

1. Resolve IDs/public base per [Config and IDs](#config-and-ids), preserving Store
   scope and stopping on unresolved QP scope, without asking for a URL.
2. Confirm opt-in for new shops; for existing shops proceed when the developer
   asks to add/update the quest module.
3. **Preflight marker count** across the shop tree for
   `data-xsolla-quest-module`:
   - **0** → insert one marked section **inside** the catalog content
     container (never nav / router / top-level tab). Create the component
     file once if the stack uses files; mount it once.
   - **1** → update that root **in place**. Prefer patching fetch URL, IDs,
     null-skip logic, safe rendering, and the fixed disclaimer / empty /
     error strings. Preserve publisher CSS and customizations outside the
     managed region. Do not create a second file or second marked section.
   - **>1** → **stop and ask** before writing. Do not auto-dedupe.
4. If a `XsollaQuestModule` file exists without a marker, update the file so
   the root carries the marker, then ensure **exactly one** catalog mount.
5. Before writing, count imports and calls for the module in the bootstrap:
   if either count is greater than `1`, stop and ask. If one exists, update it
   in place with the current module path, resolved Quest Platform IDs, and base
   URL. If the merchant or project ID (public IDs) is needed, ask the publisher for
   it, and write it only into the shop's documented build config as part of the
   approved source edit. Never read local config or env files to find it. If the
   scope cannot be resolved, stop and ask instead of writing a placeholder. If none
   exists, add one import and one mount. Preserve unrelated bootstrap code.
6. Re-run: second pass must be a no-op or overwrite the same targets. After
   write, tree-wide marker count and component-file count must each be exactly
   `1`, bootstrap import/mount counts must each be exactly `1`, and no quest
   link may be under `nav` or `role="tab"`.
7. Confirm the source integration is complete after the local validation
   appropriate to the shop stack. When the app is running, confirm the marked
   section renders even when the request is empty or unavailable; missing IDs
   must not silently make the requested module disappear. Do not probe the
   public endpoint for readiness or make a live endpoint response a prerequisite
   for integrating the section. If live data is specifically being diagnosed,
   distinguish HTTP 200 with `data: []` from route, scope, network, and CORS
   failures as described above. Do not ask the developer for a URL.

## Completion reply

Do the work before reporting completion. Then reply in the shape from
[reply-format.md](reply-format.md): a bold line on what the storefront now shows, bullets
for only the checks actually run and their results, then `Next:`.
Do not claim that live quests loaded or are visible unless the app itself has read and
rendered them. A deployed endpoint is not a prerequisite for saying the storefront
integration is complete.

## Agent rules

- No raw `curl` commands in this recipe or in skill responses for this
  module; describe the browser `fetch` URL shape instead.
- Never open `.env` or any env file, even to redact values, and never run `cat`, `sed`
  or `head` on a credential file.
- Do not describe catalog pages, their layout, or where the section will appear until
  you have read the storefront source. If no storefront source is in the working folder,
  reply with a bold line that no storefront source was found, and one `Next:` asking for
  the path to the storefront source.
