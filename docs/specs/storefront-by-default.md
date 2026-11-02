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

**Status values:** **Merged** is in `integration/sb-ai-5` but not yet proven by an
acceptance run. **Verified** means an acceptance run passed it. **Partial** means part is
merged and the rest is listed. **Decision** waits for a product or safety decision. **CLI**
waits for a CLI release. **Open** has nothing merged yet.

| # | Requirement | Done when | Skills | Status | Where |
|---|---|---|---|---|---|
| R1 | Finish the assembly phases: theme, copy and assets, verify, preview | A new site goes from brief to preview with theme, copy, art and SEO, without hand-written scripts | shop-builder-assembly | Open, partly CLI: theme waits for the CLI to recompute the theme; verify and preview wait for the `verify-website` and preview fixes. Copy and assets need a test project to verify | — |
| R2 | One approval covers the whole build | A full build has exactly one approval | nocode-shop-setup, shop-builder-assembly, catalog-design, description-to-shop | Merged; the safety owner's sign-off is pending | [#117](https://github.com/xsolla/xsolla-ai-kit/pull/117) |
| R3 | Approve a mockup made with any available tool | Every approval request includes a picture of the site | shop-builder-assembly, nocode-shop-setup | Merged. A Figma kit of real blocks at true sizes is open (design team) | [#117](https://github.com/xsolla/xsolla-ai-kit/pull/117) |
| R4 | Visual loop at 1440 and 390 px as the definition of done | Every report says `real_visual_check: yes` for desktop and mobile | shop-builder-assembly | Merged. A new site can't open in preview until the CLI ships `create-block` | [#117](https://github.com/xsolla/xsolla-ai-kit/pull/117) |
| R5 | Ship the Shop Builder render rules | None of the rules shows up as a fix in a test run's friction log | shop-builder-assembly | Merged: the rules and the opaque-color refusal. Script warnings for other rules are open | [#117](https://github.com/xsolla/xsolla-ai-kit/pull/117), [#118](https://github.com/xsolla/xsolla-ai-kit/pull/118) |
| R6 | Support Publisher Account templates and mobile game homes | An App Store link becomes a multi-page hub with LiveOps through the kit | shop-builder-assembly, game-web-portal | Decision | — |
| R7 | Helpers for CLI gaps instead of a stop | The agent neither stops nor improvises on known gaps | shop-builder-assembly, catalog-design | Decision: conflicts with the kit's "no raw HTTP" rule. Most gaps close with the CLI release | — |
| R8 | Research, real art and the full feature set by default | No follow-up prompt for art, SEO or features | description-to-shop, catalog-design | Partial: full shop proposal, store-listing art, an image per product, and design defaults are merged. SEO and OG tags and one sandbox purchase test are open | [#118](https://github.com/xsolla/xsolla-ai-kit/pull/118) |
| R9 | Setup without manual steps | Setup takes one prompt and no manual step besides signing in | nocode-shop-setup, merchant-setup | Partial: the approver is asked first, the CLI and kit are refreshed first, and the key comes from `auth login`. Self-attestation by the project owner is a decision | [#117](https://github.com/xsolla/xsolla-ai-kit/pull/117), [#118](https://github.com/xsolla/xsolla-ai-kit/pull/118) |
| R10 | Resumable, rerunnable builds | A build interrupted at any step resumes and finishes without duplicates | shop-builder-assembly | Partial: a stopped run's report keeps the same yes, and a taken slug stops the run by name. A per-section workspace and an asset URL cache are open | [#117](https://github.com/xsolla/xsolla-ai-kit/pull/117) |
| R11 | Pay Station theme matches the site | Buy opens Pay Station in the site's look on desktop and mobile | new step after assembly | Decision: browser-only until an API exists | — |

### Items from the feedback reports

| Item | Status | Where |
|---|---|---|
| Ask for the test-project approver first, not at the last step | Merged | [#117](https://github.com/xsolla/xsolla-ai-kit/pull/117) |
| Don't offer a game home for App Store or Google Play titles | Merged | [#117](https://github.com/xsolla/xsolla-ai-kit/pull/117) |
| Don't ask "where should the shop live" with no repo | Merged | [#117](https://github.com/xsolla/xsolla-ai-kit/pull/117) |
| Say in the first message that the CLI can't make a site that opens | Merged | [#117](https://github.com/xsolla/xsolla-ai-kit/pull/117) |
| Kit scripts run under `python3 -I` | Merged, unit-tested | [#117](https://github.com/xsolla/xsolla-ai-kit/pull/117) |
| `.env` written with mode 600; use the key `auth login` stored | Merged | [#117](https://github.com/xsolla/xsolla-ai-kit/pull/117) |
| Read back the site's sign-in project | Merged | [#117](https://github.com/xsolla/xsolla-ai-kit/pull/117), [#118](https://github.com/xsolla/xsolla-ai-kit/pull/118) |
| List what an `__all__` store section pulls in | Merged | [#118](https://github.com/xsolla/xsolla-ai-kit/pull/118) |
| Read bundles back with the bundle list | Merged | [#118](https://github.com/xsolla/xsolla-ai-kit/pull/118) |
| Use the signed-in browser without asking; check Figma in this session | Merged | [#117](https://github.com/xsolla/xsolla-ai-kit/pull/117) |
| Setup prompt catches an unfilled `<PASTE THE LINK HERE>` | Open: the setup guide lives outside this repo | — |
| Setup no longer says to start a new session after installing | Open: the setup guide lives outside this repo | — |
| Bundle cards show their contents (`itemsDescriptionEnabled`) | Open: the field's path needs a real site export | — |

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

## Acceptance run

One run tests the whole flow. Repeat it for each release candidate, on Claude Code and on
Codex. Record the result in the Status column above and attach the feedback report to the
pull request.

### Before you start

1. A new, empty folder, and a dedicated test project you may write to. Not a partner
   project.
2. The approver and the approval link for that test project: the agent asks for them in its
   first message.
3. Run the guide's setup prompt as a new user would.
4. **Testing a branch before its release:** the setup installs the released kit. Replace it
   with the branch:
   - Clone `xsolla/xsolla-ai-kit` and check out the branch.
   - Claude Code: copy `CLAUDE.md` into the test folder and the contents of `skills/` into
     the test folder's `.claude/skills/`. Codex: copy `AGENTS.md` and `skills/` into the
     test folder.
   - Remove the AI Kit skills that `xsolla skills install --source ai-kit` installed
     globally, so only the branch copies load.
   - Ask the agent "Which Xsolla skills are loaded, and from where?" and check that the
     answer names the branch copies.
   - Add one sentence to the build prompt: "Use the kit in this folder; don't reinstall it."

### Build prompt

```text
work here https://publisher.xsolla.com/<merchant>/projects/<test project>
create an attractive web shop for a game <store link to a game the test project owns>
use as many liveops features as possible
```

Answer only what the agent asks, and approve with one yes if the plan looks right. At the
end, run the guide's feedback prompt.

### Checklist

Tick each line while the run is going.

**First message (R9, feedback items)**

- [ ] Names the CLI and kit versions (skip for a branch test).
- [ ] Says whether the CLI can make a site that opens (`create-block`), and if not, asks
      "build anyway, or wait".
- [ ] Asks for the test-project approver and link only if the project isn't on the
      allowlist, in plain words with an example, with no `<name>` or `<link>` placeholders.
- [ ] Names the signed-in browser and whether a design tool is available.
- [ ] Doesn't ask "where should the shop live" (there is no repo).
- [ ] Doesn't offer a game home for an App Store or Google Play title.
- [ ] Asks everything else in the same message, each question with a recommended answer.

**The approval (R2, R3)**

- [ ] One message holds the catalog proposal, the site plan and a desktop and mobile
      mockup.
- [ ] The mockup uses only real blocks: no button on the lead block, no logo where the
      header has no slot.
- [ ] Each `__all__` section lists the items it pulls in, with test leftovers flagged.
- [ ] The message asks once to close the site's editor tab.
- [ ] After that yes, the agent asks nothing more until the handoff, except to press
      Preview once if the preview session expired, or for a change the plan didn't show.

**Build (R10, skills)**

- [ ] The agent loads `nocode-shop-setup`, `description-to-shop` and
      `shop-builder-assembly`, and runs `preflight.py` and `apply_plan.py`, not only the
      CLI's built-in Shop Builder skill.
- [ ] A run that stops partway resumes under the same yes, with no duplicate pages or
      blocks.

**Handoff (R4, R5)**

- [ ] Screenshots of every page at 1440 and 390 px. With CLI 1.9.4 and a new site, the
      agent instead says the preview can't open without the common layout.
- [ ] Reports the site's sign-in project and whether it belongs to this store project.
- [ ] Lists the manual steps, such as recalculating the theme in the editor.
- [ ] States that the site is not published.

**Report fields against the targets**

| Field | Target | Result |
|---|---|---|
| `my_messages_beyond_ideal` | ≤ 1 | |
| Approvals during the build | 1 | |
| `reached_storefront` | yes (partly with CLI 1.9.4) | |
| `real_visual_check` | yes (no with CLI 1.9.4 and a new site) | |
| `minutes_build` + `minutes_fixing` | ≤ 90 | |
| `cost_usd_total` | ≤ $25 | |
| Problems nobody noticed (section 5) | 0 | |

**Pass:** every checklist line holds and every report field meets its target. Until the CLI
release, `reached_storefront` and `real_visual_check` follow the CLI 1.9.4 notes above.

**Release gate:** the spec's validation set of four reference stores, each on Claude Code and
Codex: 8 runs, passing in at least 7. The four cover a given Figma design, game keys and
pre-orders, a facelift of a live shop, and a multi-page hub from a template.
