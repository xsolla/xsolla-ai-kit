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

An explicit request to integrate quests into an existing shop authorizes the
source edits. Do not respond with a plan that asks for approval, an open
question about language, or a request for the endpoint URL. Infer locale from
the shop's existing localization setup and use the configured public API
contract. Give a brief progress update only when the work takes long enough to
need one, then make the edits and run the shop's available checks.

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

Use the merchant/project pair resolved from the connected Quest Platform
project. Do not assume the shop's Store catalog project ID is the Quest
Platform project ID; they can differ. Reuse the shop's merchant ID only after
confirming it matches the resolved Quest Platform merchant. Keep the Store
catalog project setting intact, and give the Quest Platform project its own
browser-safe setting when it differs. Never copy IDs from an example or infer
one ID from the other.

The public API host is `https://quests-platform.xsolla.com`. The storefront
URL is formed from that host and the resolved Quest Platform scope; do not ask the developer to find or
provide a URL.

For browser code, expose only the resolved IDs and public URL as build-time
configuration. Prefer the shop's existing variable naming (`VITE_*` for Vite,
`NEXT_PUBLIC_*` for Next.js). The full URL may be stored as an override only
when the project already has a URL override setting or the developer supplied
an exact URL.

| Variable | Role |
|---|---|
| `XSOLLA_QP_MERCHANT_ID` | Path `merchant_id` |
| `XSOLLA_QP_PROJECT_ID` | Path `project_id`; separate from the Store catalog project when they differ |
| `XSOLLA_QP_PUBLIC_BASE_URL` | Optional explicit public-base override; production host is the default |

For browser builds, use the shop's public-variable convention, for example
`VITE_XSOLLA_QP_MERCHANT_ID` and `VITE_XSOLLA_QP_PROJECT_ID` in Vite, or
`NEXT_PUBLIC_XSOLLA_QP_MERCHANT_ID` and
`NEXT_PUBLIC_XSOLLA_QP_PROJECT_ID` in Next.js. Keep existing Store variables
such as `VITE_XSOLLA_PROJECT_ID` for catalog and checkout calls. Never expose
the Quest Platform API key in browser configuration.

`XSOLLA_QP_PUBLIC_BASE_URL` is **not** a substitute for the Quest Platform
host in [`qp-api-contract.md`](qp-api-contract.md). Agents keep using that
host for quest writes. The storefront uses the public host and resolved
merchant/project IDs only for the public list.

**Hard stops:**

- Use `https://quests-platform.xsolla.com`. A configured public-base override
  takes precedence after validation.
- Resolve the Quest Platform merchant/project pair from the connected Quest
  Platform scope. Compare it with the shop's existing merchant and Store
  project settings; use the Store project setting for quests only if it is
  confirmed to be the same Quest Platform project. If the Quest Platform scope
  cannot be resolved, ask which connected Quest Platform project to use; never
  ask the developer to find or provide the API URL.
- Never set the storefront public base to an internal or private host for a
  **publicly reachable** shop.
- Never put API keys or `Authorization` in browser code for this module.

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

```html
<section data-xsolla-quest-module="1" aria-label="Quests">
  <p class="xsolla-quest-disclaimer">Quests are configured by the publisher. Rewards are granted by the publisher when a quest is completed.</p>
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

1. Resolve the Quest Platform merchant/project pair from the connected scope.
   Compare it with shop settings, keeping the Store catalog project ID
   separate unless it is confirmed to be the same project. Use dedicated
   browser-safe Quest Platform settings when needed. If either ID is unresolved,
   stop and ask which connected Quest Platform project to use; never substitute
   sample IDs or silently reuse the catalog ID. Use the
   production public base. Do not ask for a URL.
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
   URL. Check the active local/build configuration for the required public IDs;
   do not mistake a sample or `.env.example` value for a configured value. If a
   required value is missing, use the resolved scope to configure the shop's
   local environment file with browser-safe IDs only, and restart the dev
   server so Vite or the equivalent reloads build-time variables. If the scope
   cannot be resolved, stop and ask instead of writing a placeholder. If none
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

Do the work before reporting completion. After local checks, keep the reply
short and structured. State only checks actually run. For example:

```markdown
## Summary
Added a quests section to the shop catalog.

## What players see
Quest cards and reward details, with loading, empty and unavailable states.

## Checks
[Report the checks actually run and their results.]

## Try it
Run the shop locally using its documented development command.
```

Use the shop's actual commands and results instead of copying the example
counts. Do not claim that live quests loaded or are visible unless the app
itself has read and rendered them. A deployed endpoint is not a prerequisite
for saying the storefront integration is complete.

## Agent rules

- No raw `curl` commands in this recipe or in skill responses for this
  module; describe the browser `fetch` URL shape instead.
- Never fabricate quests or rewards for demos.
- Errors degrade without breaking the catalog.
