# Headless Web Shop quest module

Optional in-catalog quest section for the **headless** storefront from
`shop-setup`. Not Site Builder / custom-blocks. Never a top-level nav tab,
router entry, or new shop route.

Triggers: "show quests in my web shop", "add quest module to shop", "quest
module", "catalog quests section".

## When to use

- **New shop** (during or after shop-setup): ask / confirm opt-in before adding.
- **Existing shop**: when the developer asks to add or update quests in the
  shop, run the upsert algorithm below.

Out of scope: user progress / completion UI, fabricating sample quests,
changing AdTech APIs, Site Builder blocks.

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

Reuse shop config already present from shop-setup Phase 0 / `.env`:

| Variable | Role |
|---|---|
| `XSOLLA_MERCHANT_ID` | Path `merchant_id` |
| `XSOLLA_PROJECT_ID` | Path `project_id` |
| `XSOLLA_QP_PUBLIC_BASE_URL` | **Storefront-only** public base for the browser GET |

`XSOLLA_QP_PUBLIC_BASE_URL` is **not** a substitute for the agent CRUD host
table in [`auth-and-environment.md`](auth-and-environment.md). Agents keep
using that table for qp-server writes; the storefront reads this env (or
`import.meta.env` / build-time public config) only for the public list.

**Hard stops:**

- If `XSOLLA_QP_PUBLIC_BASE_URL` is missing, stop. Do not invent a host.
- Do not guess a production host.
- Do **not** set the storefront public base to
  `https://qp-server.nl-k8s-stage.srv.local` (or any `*.srv.local`) for a
  **publicly reachable** shop. That stage host is corporate/VPN-only.
  Stage browser proof needs VPN, or is agent-side smoke only.
- Never put API keys or `Authorization` in browser code for this module.

## Wire contract (consume verbatim)

`GET {base}/api/v2/public/merchants/{merchant_id}/projects/{project_id}/quests?page=1&limit=10`

No auth header. Build `{base}` only from `XSOLLA_QP_PUBLIC_BASE_URL`.

**200 envelope:** `page`, `limit`, `total`, `data[]` with:

| Field | Rule |
|---|---|
| `data[].id` | Required string (UUID); list key |
| `data[].name` | Required string |
| `data[].description` | Optional; omit when absent |
| `data[].rewards` | Required array (may be empty) |
| `rewards[].name`, `rewards[].description`, `rewards[].image_url` | Present; may be **null** — skip nulls when rendering |
| `rewards[].quantity` | Required int |
| `rewards[].type` | Required string |

Empty success: `data: []`. Errors: 404 / 422 / network / CORS → hide the
module or show the neutral message; **catalog must keep working**. Never
fabricate quests or rewards.

## Markup shape

```html
<section data-xsolla-quest-module="1" aria-label="Quests">
  <p class="xsolla-quest-disclaimer">Quests are configured by the publisher. Rewards are delivered to your Backpack.</p>
  <!-- loading: -->
  <p class="xsolla-quest-loading" role="status" aria-live="polite">Loading quests...</p>
  <!-- empty: -->
  <p class="xsolla-quest-empty">No active quests right now.</p>
  <!-- or list keyed by data[].id: -->
  <article data-quest-id="…">
    <!-- name; description if present; each reward: name (skip if null),
         quantity; image only if image_url is absolute http(s) -->
  </article>
</section>
```

**Fixed copy (exact):**

- Disclaimer: `Quests are configured by the publisher. Rewards are delivered to your Backpack.`
- Empty: `No active quests right now.`
- Neutral error (optional): `Quests are temporarily unavailable.`

Place as a sibling **inside** the catalog content container (after or before
the product list). Never under `<nav>`, header tabs, or a top-level tablist.

**Accessibility:** empty and error text must stay visible (not
`display:none`-only). Images: use the reward name as `alt` when informative,
or empty `alt` when decorative. Do not put the disclaimer on a noisy
`aria-live` region.

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

Browser calls go from the shop origin to qp-server. CORS depends on the
server `ALLOW_ORIGINS` setting. On CORS failure, show the neutral error (or
hide the module) and keep the catalog working. When the shop is served over
`https`, the public base must also be `https` (no mixed-content HTTP). Never
send credentials (`credentials: 'include'`) on this fetch.

## Idempotent upsert algorithm

1. Read `.env` / shop config for `XSOLLA_MERCHANT_ID`, `XSOLLA_PROJECT_ID`,
   and required `XSOLLA_QP_PUBLIC_BASE_URL`. Stop if base is missing or is a
   public-shop-unsafe `*.srv.local` host (see Hard stops).
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
   in place with the current module path, IDs, and base URL. If none exists,
   add one import and one mount. Preserve unrelated bootstrap code.
6. Re-run: second pass must be a no-op or overwrite the same targets. After
   write, tree-wide marker count and component-file count must each be exactly
   `1`, bootstrap import/mount counts must each be exactly `1`, and no quest
   link may be under `nav` or `role="tab"`.

## Agent rules

- No raw `curl` commands in this recipe or in skill responses for this
  module; describe the browser `fetch` URL shape instead.
- Never fabricate quests or rewards for demos.
- Errors degrade without breaking the catalog.
