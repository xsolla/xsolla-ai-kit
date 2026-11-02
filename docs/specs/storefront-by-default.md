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
| R1 | Finish the assembly phases: theme, copy and assets, verify, preview | A new site goes from brief to preview with theme, copy, art and SEO, without hand-written scripts | shop-builder-assembly | Open, partly CLI: theme waits for the CLI to recompute the theme; verify and preview wait for the `verify-website` and preview fixes. Copy and assets need a test project to verify | — |
| R2 | One approval covers the whole build | A full build has exactly one approval | nocode-shop-setup, shop-builder-assembly, catalog-design, description-to-shop | Done; the safety owner's sign-off is pending (D1) | [#117](https://github.com/xsolla/xsolla-ai-kit/pull/117) |
| R3 | Approve a mockup made with any available tool | Every approval request includes a picture of the site | shop-builder-assembly, nocode-shop-setup | Done. A Figma kit of real blocks at true sizes is open (design team) | [#117](https://github.com/xsolla/xsolla-ai-kit/pull/117) |
| R4 | Visual loop at 1440 and 390 px as the definition of done | Every report says `real_visual_check: yes` for desktop and mobile | shop-builder-assembly | Done. A new site can't open in preview until the CLI ships `create-block` | [#117](https://github.com/xsolla/xsolla-ai-kit/pull/117) |
| R5 | Ship the Shop Builder render rules | None of the rules shows up as a fix in a test run's friction log | shop-builder-assembly | Done: the rules and the opaque-color refusal. Script warnings for other rules are open | [#117](https://github.com/xsolla/xsolla-ai-kit/pull/117), [#118](https://github.com/xsolla/xsolla-ai-kit/pull/118) |
| R6 | Support Publisher Account templates and mobile game homes | An App Store link becomes a multi-page hub with LiveOps through the kit | shop-builder-assembly, game-web-portal | Decision (D3) | — |
| R7 | Helpers for CLI gaps instead of a stop | The agent neither stops nor improvises on known gaps | shop-builder-assembly, catalog-design | Decision (D4): conflicts with the kit's "no raw HTTP" rule. Most gaps close with the CLI release | — |
| R8 | Research, real art and the full feature set by default | No follow-up prompt for art, SEO or features | description-to-shop, catalog-design | Partial: full shop proposal, store-listing art, an image per product, and design defaults are merged. SEO and OG tags are open; the sandbox purchase test is a decision (D6) | [#118](https://github.com/xsolla/xsolla-ai-kit/pull/118) |
| R9 | Setup without manual steps | Setup takes one prompt and no manual step besides signing in | nocode-shop-setup, merchant-setup | Partial: the approver is asked first, the CLI and kit are refreshed first, and the key comes from `auth login`. Self-attestation by the project owner is a decision (D2) | [#117](https://github.com/xsolla/xsolla-ai-kit/pull/117), [#118](https://github.com/xsolla/xsolla-ai-kit/pull/118) |
| R10 | Resumable, rerunnable builds | A build interrupted at any step resumes and finishes without duplicates | shop-builder-assembly | Partial: a stopped run's report keeps the same yes, and a taken slug stops the run by name. A per-section workspace and an asset URL cache are open | [#117](https://github.com/xsolla/xsolla-ai-kit/pull/117) |
| R11 | Pay Station theme matches the site | Buy opens Pay Station in the site's look on desktop and mobile | new step after assembly | Decision (D5): browser-only until an API exists | — |

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

## Open decisions

Each decision names its options, a recommendation, and what it changes against the
targets. When one is made, record the answer here and move its requirement on.

**D1. Approval scope (R2). Owner: safety.** One yes now covers the catalog proposal, the
site plan and mockup, and the theme, fonts and wording the plan showed, plus visual-review
fixes back to those values. Anything the plan didn't show still needs a new yes.
- Options: (a) accept as merged; (b) narrow the yes back to background fixes only.
- Recommendation: (a). The developer saw every covered change before saying yes.
- Effect: (b) brings back a question for every theme, font or wording fix after the review.

**D2. Who approves the test project (R9). Owner: safety.** Today the allowlist needs an
approver (a mentor or tech lead) and a link to that approval.
- Options: (a) keep it; (b) the project owner confirms in chat, recorded with the date and
  their words; (c) the owner confirms only for a project the CLI marks as a test project.
- Recommendation: (c) once the CLI can mark test projects; (a) until then.
- Effect: (b) or (c) removes the last manual step of setup, the step that stalled two runs.

**D3. Publisher Account templates and mobile game homes (R6). Owner: product.**
Assembly stops on a site made from a template, and `game-web-portal` refuses App Store and
Google Play titles.
- Options: (a) keep both; (b) let assembly work on a template site: read its layout and
  replace the demo content within the plan; (c) also accept mobile titles in
  `game-web-portal`.
- Recommendation: (b) now, then (c). A template site already has the common layout, so (b)
  gives a site that opens in the editor and preview before the CLI ships `create-block`.
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
