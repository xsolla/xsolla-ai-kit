# Spec: great storefronts by default (Shop Builder path)

Source: the "AI Kit spec: great storefronts by default" (2026-11-02) and the feedback reports
of three first-time user runs on two mobile games (2026-10-29 to 2026-11-02).

This is the one spec for the Shop Builder path. Each pull request that works on it updates
the **Status** column below in the same pull request. It stays the source of truth: when a
skill and this file disagree, fix one of them; don't add a second spec.

## Goal

A first-time user who follows the guide gets a storefront as good as the team's reference
builds, with one setup prompt, one build prompt and one approval, while they're away from the
screen.

**Not in scope:** pixel-perfect design, publishing for the user, production payments, custom
code, and the headless path (`shop-setup`).

## Success metrics

Measured with the guide's feedback prompt, which writes these fields from the session logs.

| Metric (feedback report field) | First-time users before this work | Target |
|---|---|---|
| Messages beyond the ideal flow (`my_messages_beyond_ideal`) | 3 to 32 | Median ≤ 1 |
| Approvals during the build | Up to 5 | 1 |
| Working storefront (`reached_storefront`) | no to partly | yes: opens in the editor and in preview |
| Visual check on desktop and mobile (`real_visual_check`) | Desktop only, or none | Both, every run |
| Minutes from build prompt to handoff (`minutes_build` + `minutes_fixing`) | 213 to 261 | ≤ 90 |
| API-equivalent cost per storefront (`cost_usd_total`) | $4 to $37 | ≤ $25 |
| Problems nobody noticed (section 5 of the report) | Several per run | 0 |

## Target flow

The user acts in steps 1, 2 and 4 only.

1. **Setup, once.** One prompt installs the CLI and the kit and signs in with the merchant and
   project from the project link.
2. **Build prompt.** A game link, plus a reference for the look if the user has one.
3. **Checks and research.** Latest CLI and kit, CLI capabilities, test-project approval,
   platform, signed-in browser and design tools; then the game's currency, packs, items and
   art, each with its source. Anything still missing is asked once, as one batch with
   recommended answers.
4. **One approval.** The catalog proposal, the site plan, and a desktop and mobile mockup in
   one message. One yes.
5. **Build.** Catalog, then the site, with a backup before writes.
6. **Checkout look.** A Pay Station theme in the site's colors (R11, open).
7. **Visual loop.** Screenshots of every page at 1440 and 390 px in preview, fixes, and
   another look, until the checklist passes.
8. **Handoff.** Preview and editor links, final screenshots, readiness by stage, and what is
   left for the user. The agent never publishes.

## Requirements

**Status values:** **Done** is merged into `integration/sb-ai-5`. **Partial** means part is
merged and the rest is listed. **Decision** waits for a product or safety decision. **CLI**
waits for a CLI release. **Open** has nothing merged yet.

| # | Requirement | Done when | Skills | Status | Where |
|---|---|---|---|---|---|
| R1 | Finish the assembly phases: theme, copy and assets, verify, preview | A new site goes from brief to preview with theme, copy, art and SEO, without hand-written scripts | shop-builder-assembly | Partial: the theme, images and copy are scripted. `apply_style.py` sets the brief's palette on the site theme, puts the planned pages on it, and hands over the Editor recalculation until the CLI recomputes the theme; it uploads each approved image once and puts it on its block; it writes the approved text and FAQ items in the primary locale. Fonts are an Editor step: the current theme shape has no font field the CLI can set. SEO is R8's. Verify and preview wait for the `verify-website` and preview fixes | [#137](https://github.com/xsolla/xsolla-ai-kit/pull/137), [#138](https://github.com/xsolla/xsolla-ai-kit/pull/138) |
| R2 | One approval covers the whole build | A full build has exactly one approval | nocode-shop-setup, shop-builder-assembly, catalog-design, description-to-shop | Done: a new catalog and new LiveOps share the one yes, and nothing is written before it, as shown in headless runs (see How the status was checked). The approval scope is accepted for 1.5.0 (D1) | [#117](https://github.com/xsolla/xsolla-ai-kit/pull/117), [#128](https://github.com/xsolla/xsolla-ai-kit/pull/128), [#129](https://github.com/xsolla/xsolla-ai-kit/pull/129), [#130](https://github.com/xsolla/xsolla-ai-kit/pull/130) |
| R3 | Approve a mockup made with any available tool | Every approval request includes a picture of the site | shop-builder-assembly, nocode-shop-setup | Done for a store; a game home shows `game-web-portal`'s plan instead. A Figma kit of real blocks at true sizes is open (design team) | [#117](https://github.com/xsolla/xsolla-ai-kit/pull/117), [#130](https://github.com/xsolla/xsolla-ai-kit/pull/130) |
| R4 | Visual loop at 1440 and 390 px as the definition of done | Every report says `real_visual_check: yes` for desktop and mobile | shop-builder-assembly | Done. A new site can't open in preview until the CLI ships `create-block`, and the review needs a signed-in browser: without one, the handoff says the site isn't reviewed | [#117](https://github.com/xsolla/xsolla-ai-kit/pull/117) |
| R5 | Ship the Shop Builder render rules | None of the rules shows up as a fix in a test run's friction log | shop-builder-assembly | Done: the rules and the opaque-color refusal. The copy step follows the text rules: the validator refuses copy that isn't HTML, `<img>` in copy, and an FAQ question that isn't an `<h4>`. Open check: `apply_plan.py` writes header navigation labels as `<span>` HTML, which the render rules call plain text; the earlier verified runs rendered them, so confirm on the next test site before changing it. The plan's step order matches the skill (theme, images and copy last) | [#117](https://github.com/xsolla/xsolla-ai-kit/pull/117), [#118](https://github.com/xsolla/xsolla-ai-kit/pull/118), [#130](https://github.com/xsolla/xsolla-ai-kit/pull/130) |
| R6 | Support Publisher Account templates and mobile game homes | An App Store link becomes a multi-page hub with LiveOps through the kit; see [R6 in detail](#r6-in-detail) | shop-builder-assembly, game-web-portal, nocode-shop-setup | Partial: part (b) works for the single-page preset on a Single-page shop template site, tested on the masked real-export fixture and a scripted run (D3 decided). A multi-page plan on a template, and part (c), are open | [#134](https://github.com/xsolla/xsolla-ai-kit/pull/134) |
| R7 | Helpers for CLI gaps instead of a stop | The agent neither stops nor improvises on known gaps | shop-builder-assembly, catalog-design | Decision (D4): conflicts with the kit's "no raw HTTP" rule. Most gaps close with the CLI release | — |
| R8 | Research, real art and the full feature set by default | No follow-up prompt for art, SEO or features | description-to-shop, catalog-design | Partial: full shop proposal, store-listing art, an image per product, and design defaults are merged. SEO and OG tags are open; the sandbox purchase test is a decision (D6) | [#118](https://github.com/xsolla/xsolla-ai-kit/pull/118) |
| R9 | Setup without manual steps | Setup takes one prompt and no manual step besides signing in | nocode-shop-setup, merchant-setup | Partial: the approver is asked first, the CLI and kit are refreshed first, the key comes from `auth login` without asking, and no key or Login project is created before the yes. Self-attestation by the project owner stays out of 1.5.0 (D2) | [#117](https://github.com/xsolla/xsolla-ai-kit/pull/117), [#118](https://github.com/xsolla/xsolla-ai-kit/pull/118), [#128](https://github.com/xsolla/xsolla-ai-kit/pull/128), [#130](https://github.com/xsolla/xsolla-ai-kit/pull/130) |
| R10 | Resumable, rerunnable builds | A build interrupted at any step resumes and finishes without duplicates | shop-builder-assembly | Partial: a stopped run's report keeps the same yes, a taken slug stops the run by name, and a rerun skips pages, navigation, locales and catalog links that already match. `apply_style.py` keeps an asset cache, so a rerun doesn't upload an image twice. Open: resuming catalog creation, which `catalog-design` does without a script. A stopped run resumed under the same yes three times in a scripted run against a stateful stand-in CLI | [#117](https://github.com/xsolla/xsolla-ai-kit/pull/117), [#129](https://github.com/xsolla/xsolla-ai-kit/pull/129), [#138](https://github.com/xsolla/xsolla-ai-kit/pull/138) |
| R11 | Pay Station theme matches the site | Buy opens Pay Station in the site's look on desktop and mobile | new step after assembly | Decision (D5): browser-only until an API exists | — |

### R6 in detail

Written ahead of D3, as if D3 is approved with its recommendation: part (b) first, then
part (c). If D3 is decided otherwise, change or remove this section.

**Today.** `render_plan.py` and `apply_plan.py` stop before any write on a page whose
header sits in the common layout (`require_own_header`), which is how every Publisher
Account template builds its pages. Navigation looks for a header among the page's own
blocks. `game-web-portal` accepts only a Steam link and returns `needs_input` for App Store
and Google Play titles, and `nocode-shop-setup` offers a game home only for PC games.

**Why.** A site made from a template already has the common layout, so it opens in the
editor and preview without `create-block`. It also comes with the LiveOps blocks that the
CLI can't add yet: daily rewards, offer chain, reward system and promo codes.

**Part (b): `shop-builder-assembly` on a store template site**

1. **Who creates the site.** The developer, in Publisher Account, from a store template:
   Single-page shop first. The first message of `nocode-shop-setup` gives the steps when
   the CLI lacks `create-block`, as the recommended answer to "build anyway, or wait". The
   agent never creates a site through the browser, the same rule as `game-web-portal`.
   With a CLI that has `create-block`, `create-website` stays the default.
2. **Discover.** Export the site as today. Find the common layout's header and footer by
   module with `get-block`, and each page's blocks by module.
3. **Plan.** Render with `--structure` and map the preset's sections onto the template's
   blocks by module:
   - the header and footer stay in the site layout, so the page plan leaves them out;
   - the template's `lead` hero counts as the preset's hero and is kept;
   - the template's daily rewards block is kept: the kit can't add one back;
   - keep a block whose module the preset uses, and list every other demo block, and
     duplicate store blocks, as exact removals by ID;
   - rebind the kept `newStore` block's sections from the demo groups to the brief's groups;
   - keep the offer chain, reward system and promo codes blocks; with no LiveOps in the
     brief they are preserved as configured, as on any site.

   The plan shows all of this, so the one yes covers it. First release: the single-page
   preset only. A plan with more pages on a template site stops before any write, because
   a page the kit adds would get a header of its own next to the shared one.
4. **Apply.** One run under the yes, since the template's blocks already have IDs; the
   two-run bootstrap is for new sites only. Same preflight, backup and coverage checks.
   Navigation in the shared header is an Editor step: a single page has nothing to link.
5. **Verify.** `verify_structure.py` compares the page without the header and footer, and
   finds the existing common layout. The site opens in preview, so the visual review at
   1440 and 390 px runs.

Done when, for part (b):

- render and apply no longer stop on a page whose header is in the common layout;
- one run under one yes turns a store template site into the plan: the brief's catalog
  and LiveOps, and no demo blocks, groups or text left;
- `verify_structure.py` passes on the result;
- the site opens in the editor and preview;
- unit tests on a sanitized export of a Single-page shop site: the render lists exact
  removals and rebindings, apply makes no write before the yes, and a page without its
  own header passes.

**Part (c): mobile game homes in `game-web-portal`**

- Accept the exact hosts `apps.apple.com` and `play.google.com` next to
  `store.steampowered.com`; anything else, or a look-alike host, is still `needs_input`.
- An App Store or Google Play listing is a source of facts and art only after the
  developer confirms it's theirs and may be used, as in `description-to-shop`.
- The Launcher section isn't offered for a mobile title, and the sidebar keeps its App
  Store and Google Play buttons.
- `nocode-shop-setup` offers a game home for mobile titles again.

Done when, for part (c): an App Store link becomes a multi-page hub with LiveOps through
the kit, and the host check accepts the three exact hosts and refuses look-alikes.

**Test data.** The masked export of a real template site already in the assembly tests
(`publisher_template_site`) is the fixture: header and footer as site-level blocks, and a
page with `lead`, three store blocks, daily rewards, offer chain, reward system, promo
codes, an offerwall and FAQ. A fresh Single-page shop export is still worth a check before
relying on details beyond that. The LiveOps block contracts are already in
[exported block contracts](../../shop-builder-assembly/references/exported-block-contracts.md)
and the [block catalog](../../shop-builder-assembly/references/block-catalog.md).

**Out of scope.** The agent creating sites in the browser; templates other than
Single-page shop and Multi-page web portal; removing the template path once `create-block`
ships, which is a separate decision.

### Items from the feedback reports

| Item | Status | Where |
|---|---|---|
| Ask for the test-project approver first, not at the last step | Done | [#117](https://github.com/xsolla/xsolla-ai-kit/pull/117) |
| Don't offer a game home for App Store or Google Play titles | Done | [#117](https://github.com/xsolla/xsolla-ai-kit/pull/117) |
| Don't ask "where should the shop live" with no repo | Done | [#117](https://github.com/xsolla/xsolla-ai-kit/pull/117) |
| Say in the first message that the CLI can't make a site that opens | Done | [#117](https://github.com/xsolla/xsolla-ai-kit/pull/117) |
| Kit scripts run under `python3 -I` | Done, unit-tested | [#117](https://github.com/xsolla/xsolla-ai-kit/pull/117) |
| `.env` written with mode 600; use the key `auth login` stored | Done | [#117](https://github.com/xsolla/xsolla-ai-kit/pull/117) |
| Read back the site's sign-in project | Done | [#117](https://github.com/xsolla/xsolla-ai-kit/pull/117), [#118](https://github.com/xsolla/xsolla-ai-kit/pull/118) |
| List what an `__all__` store section pulls in | Done | [#118](https://github.com/xsolla/xsolla-ai-kit/pull/118) |
| Read bundles back with the bundle list | Done | [#118](https://github.com/xsolla/xsolla-ai-kit/pull/118) |
| Use the signed-in browser without asking; check Figma in this session | Done | [#117](https://github.com/xsolla/xsolla-ai-kit/pull/117) |
| Setup prompt catches an unfilled `<PASTE THE LINK HERE>` | Open: the setup guide lives outside this repo | — |
| Setup no longer says to start a new session after installing | Open: the setup guide lives outside this repo | — |
| Bundle cards show their contents (`itemsDescriptionEnabled`) | Open: the field's path needs a real site export | — |
| No API-key question when the CLI is signed in | Done | [#128](https://github.com/xsolla/xsolla-ai-kit/pull/128) |
| One batch also carries the storefront intake and `catalog-design`'s questions | Done | [#128](https://github.com/xsolla/xsolla-ai-kit/pull/128), [#130](https://github.com/xsolla/xsolla-ai-kit/pull/130) |
| No key, Login project or CLI switch before the yes | Done | [#128](https://github.com/xsolla/xsolla-ai-kit/pull/128), [#130](https://github.com/xsolla/xsolla-ai-kit/pull/130) |
| The proposal respects chain-step limits; no silent substitution after the yes | Done | [#129](https://github.com/xsolla/xsolla-ai-kit/pull/129) |

## How the status was checked

"Done" means merged into `integration/sb-ai-5`, with unit tests for script changes. The
path was also run in headless Claude Code, with the kit's 13 skills in an empty folder and
a stand-in `xsolla` CLI that logs every call and keeps state, on 2026-11-03:

- **First message**, five scenarios (mobile and PC, with and without a storefront repo,
  and "I'll write the code"): the right skill each time, one batch with recommended
  answers, the approver asked with no default, and no write.
- **Full flow**, the build prompt and then one "yes": the catalog and LiveOps were created
  and read back first, both apply runs went through under the same yes,
  `verify_structure.py` matched the plan, and nothing was written before the yes.
- **Limits:** the CLI was a stand-in, every run used the same model, the CLI's built-in
  Shop Builder skill wasn't installed, and no browser was available for the visual review.

## Open decisions

Each decision names its options, a recommendation, and what it changes against the
targets. When one is made, record the answer here and move its requirement on.

**D1. Approval scope (R2). Owner: safety.** One yes now covers the catalog proposal, the
site plan and mockup, and the theme, fonts and wording the plan showed, plus visual-review
fixes back to those values. Anything the plan didn't show still needs a new yes.
- Options: (a) accept as merged; (b) narrow the yes back to background fixes only.
- Recommendation: (a). The developer saw every covered change before saying yes.
- **Decided 2026-11-03: (a),** by the Shop Builder skills' code owner (apyanzin-xsolla),
  for release 1.5.0.
- Effect: (b) brings back a question for every theme, font or wording fix after the review.

**D2. Who approves the test project (R9). Owner: safety.** Today the allowlist needs an
approver (a mentor or tech lead) and a link to that approval.
- Options: (a) keep it; (b) the project owner confirms in chat, recorded with the date and
  their words; (c) the owner confirms only for a project the CLI marks as a test project.
- Recommendation: (c) once the CLI can mark test projects; (a) until then.
- **Decided 2026-11-03: (a) for 1.5.0,** by the Shop Builder skills' code owner
  (apyanzin-xsolla): the approver and link stay. (c) waits for the CLI.
- Effect: (b) or (c) removes the last manual step of setup, the step that stalled two runs.

**D3. Publisher Account templates and mobile game homes (R6). Owner: product.**
Assembly stops on a site made from a template, and `game-web-portal` refuses App Store and
Google Play titles.
- Options: (a) keep both; (b) let assembly work on a template site: read its layout and
  replace the demo content within the plan; (c) also accept mobile titles in
  `game-web-portal`.
- Recommendation: (b) now, then (c). A template site already has the common layout, so (b)
  gives a site that opens in the editor and preview before the CLI ships `create-block`.
  Specified in [R6 in detail](#r6-in-detail).
- **Decided 2026-11-03: (b) now,** by the Shop Builder skills' code owner (apyanzin-xsolla);
  (c) stays open.
- Effect: `reached_storefront` and `real_visual_check` can reach yes without waiting for
  the CLI.

**D4. Helper scripts for CLI gaps (R7). Owner: product and the kit's code owners.** The
kit forbids raw HTTP and stops on a missing CLI operation.
- Options: (a) keep the rule and wait for the CLI release; (b) allow kit scripts, with the
  usual preflight and backup, for listed gaps, each removed when the CLI covers it.
- Recommendation: (a) for every gap the coming CLI release closes; decide (b) only for the
  gaps left after it.
- Effect: (a) keeps some stops until the release; (b) removes them sooner and adds scripts
  to maintain.

**D5. Pay Station theme (R11). Owner: product.** No API or CLI command sets it.
- Options: (a) the handoff gives the site's colors and fonts, and the developer sets the
  theme; (b) the agent sets it in Publisher Account through the browser.
- Recommendation: (a) until an API exists.
- Effect: (a) adds one documented manual step; (b) depends on browser automation of a page
  that can change.

**D6. Sandbox purchase test (R8). Owner: product.** R8 asks for one sandbox purchase test,
but the kit never uses sandbox as a Shop Builder target: Shop Builder has no sandbox, and
every write reaches the project.
- Options: (a) drop it from R8; (b) reword it as a test purchase the developer makes,
  listed in the handoff with steps.
- Recommendation: (b).
- Effect: none on the targets; it removes a requirement the kit can't meet as written.

## Dependencies outside the kit

The CLI team knows about these and the kit waits for their release. When one ships, remove
the matching "known gap" text from the skills and update R1, R4 and R7 above.

| Team | Fix | Unblocks |
|---|---|---|
| CLI | Release `shopbuilder create-block` | R1, R4: a new site opens in the editor and preview |
| CLI | Recompute the theme after a CLI patch | R1, R5 |
| CLI | `enable-preview` and `preview-link` without a browser session; `verify-website` sends page IDs | R1, R4 |
| CLI | `update-block` fails when nothing changed; `add-page` path object; federated `add-block` | R5, R7 |
| CLI | LiveOps and catalog flags: limits, bonus conditions, fixed promo codes; bundles in group listings; one flag name for group IDs; default publisher ID | R7, R8 |
| CLI | `auth login` makes a key after a project switch; `xsolla update` finds releases | R9 |
| Shop Builder | New pages without the full demo template; the right Login project for a new site | R1, R10 |
| Pay Station | An API or CLI command for themes | R11 |
| Design | A Figma kit of real blocks at true sizes and limits | R3 |

## What stays

Testers praised these parts; changes for this spec must not weaken them.

- The safety gate: test projects only, preflight, a backup before the first write, never
  publishing.
- Plans with exact removals, shown before any write.
- Deterministic scripts: `apply_plan.py` and `verify_structure.py`.
- Brief-driven content, with no rewriting.
- No repeated questions: the onboarding intake is reused across skills.
