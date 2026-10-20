# Quests block QA guide (toolkit QA branch)

This branch exists only for testing. It is `origin/main` plus the quest-setup stack
(PRs #38 to #56), the Quests block operations for `quest-setup` (D2b, PR #88) and the
Quests block contract and operations for `shop-builder-assembly` (D2a, PR #87). It is not a
release and must not be merged. Nothing here publishes a Shop Builder site.

## 1. Pinned versions

| Item | Pin |
| --- | --- |
| Repository | `xsolla/xsolla-ai-kit` |
| QA branch | `codex/quests-qa-2026-10-20` (the tip of this branch; `git rev-parse HEAD` after checkout) |
| `main` tip merged in | `ab59c65727a56577dd5ffbac1381d8293fb35f6c` |
| Quest stack head (#56, `QP-2936-webshop-quest-module`, includes #38 to #56) | `5f0af8e63f9d3c0e9f0e8fe6ef4f4dd1af842826` |
| D2b: `quest-setup` Quests block operations, PR #88, branch `codex/QP-3127-quests-block-ops` | `2dc25da9a0670a6695e51f9ecc6a0966b6229f66` |
| D2a: `shop-builder-assembly` Quests block, PR #87, branch `codex/sba-quests-block` | `c338a7d075ae2a54db163a9920c7ce4a096d1f4d` |
| Quests block unstable version | `0.1.0-qp-3126.2` (sb-custom-blocks tag `quest-platform/quests-block@0.1.0-qp-3126.2`, commit `a26ed1105c`, MR `monetization-integration/sb-custom-blocks!1960`) |
| Quest Platform backend `<SHA_BE>` | `7cfcc00ca9574a3b41bd62a7d26d72a8c7ff1272`, branch `codex/qp-me-browser-fixes` (adtech MR !6371) |
| Backend stage tags | `stage-adtech-qp-server-qp-me-fixes-v1`, `stage-qp-gqw-qp-me-fixes-v1` |
| Stage hosts | public `https://quests-stage.xsolla.com`, internal `https://qp-server.nl-k8s-stage.srv.local` |

The block is an unstable build. Merchants cannot use it until a stable release exists. In this
QA it is loaded in Site Builder Dev Mode only. If the stage backend no longer runs the tags
above, record that in your results, because B2 to B13 depend on the `/api/v2/me/...` routes.

## 2. Prerequisites

- A Publisher Account login with access to a project you may test in (section 4).
- Xsolla CLI 1.9.4 or later (`brew install xsolla/xsolla-cli/xsolla`), logged in to the same account.
- Python 3 (for the skill's scripts and the checks below).
- Claude Code (or another agent that loads plugins from a local marketplace).
- Access to the Quest Platform stage hosts above (VPN or network access as your team requires).

## 3. Install the plugin from this branch

Use your own clone. Do not reuse anyone else's checkout.

```bash
git clone --branch codex/quests-qa-2026-10-20 https://github.com/xsolla/xsolla-ai-kit.git xsolla-ai-kit-quests-qa
cd xsolla-ai-kit-quests-qa
git log --oneline -1
python3 .github/scripts/validate_skills.py
(cd skills/shop-builder-assembly && python3 -m unittest discover -s tests)
```

Both checks must pass before you start. Then install it as a local marketplace:

```bash
claude plugin marketplace add "$(pwd)"
claude plugin install xsolla-ai-kit@xsolla-ai-kit
```

If the released `xsolla-ai-kit` plugin is already installed, remove it first
(`claude plugin uninstall xsolla-ai-kit@xsolla-ai-kit`) and remove the old marketplace entry
(`claude plugin marketplace remove xsolla-ai-kit`), so the session cannot load the released skills
by mistake. Start a new Claude Code session afterwards, and confirm the plugin path points at your
clone. For other agents, copy `AGENTS.md` and `skills/` from this clone into your working project.

## 4. Environment variable names

Names only. Put real values in your project-local `.env` (which must be git-ignored) or in your
process environment. Never paste a value into chat, a screenshot or a comment.

| Name | Used for |
| --- | --- |
| `XSOLLA_MERCHANT_ID` | Merchant scope of your test project |
| `XSOLLA_PROJECT_ID` | Project scope of your test project |
| `XSOLLA_PROJECT_API_KEY` | Project API key (used as the HTTP Basic password with the merchant ID) |
| `XSOLLA_QP_MERCHANT_ID` | Quest Platform merchant, only if it differs from the shop merchant |
| `XSOLLA_QP_PROJECT_ID` | Quest Platform project, only if it differs from the shop project |
| `XSOLLA_QP_PUBLIC_BASE_URL` | Optional public-base override for the block's shop code. Never a target for skill requests |

## 5. Your own test project, allowlist entry and player

You need all three of your own. Do not borrow the author's project, allowlist or player.

1. Test project. In Publisher Account create a dedicated project for this QA. It must be a
   non-partner project that you are allowed to modify. The Shop Builder gate accepts only
   `environment: test` projects that are on a local allowlist, never `--sandbox` targets and never a
   partner project. Create a Shop Builder site in it (any slug, for example `qa-quests-<yourname>`)
   and create at least three quests through `quest-setup`, then make them public (published)
   so a visitor can see them. Include one quest with an item reward for B7.
2. Allowlist entry. Create a file outside the repository, for example `approved-test-projects.json`:

   ```json
   {
     "version": 1,
     "projects": [
       {
         "merchant_id": 0,
         "project_id": 0,
         "approved_by": "<your mentor or tech lead>",
         "approval_reference": "<link or durable reference to that approval>"
       }
     ]
   }
   ```

   Replace the zeros with your own IDs. Get the approval from your lead before the first write.
   The briefs you run use `project.environment: "test"` and `project.test_project_acknowledged: true`,
   and you pass the file to `preflight.py` with `--approved-test-projects`.
3. Player. Use your own Xsolla player account (or a freshly created one) and log in
   interactively on the stage shop. A second player is needed for B9. Do not paste player
   identifiers (IDs, emails, tokens) into reports or screenshots.
4. Block in Dev Mode. In Site Builder, open your site in Dev Mode and load the Quests block build
   `0.1.0-qp-3126.2`. Do not publish the site. A human publishes in Publisher Account, and not
   during this QA.

## 6. Safety rules while testing

- Only your allowlisted `environment: test` project. Never `--sandbox`, never a partner project.
- Never publish a site, attach a domain, enable live payments or apply a saved version.
- Never merge any MR or PR. Post evidence as comments on PR #87 and #88.
- Do not extract tokens, cookies or storage from a browser. Do not print secrets.
- Delete is the only operation that uses `delete-block --force`. It runs only for a block listed
  in the confirmed plan, and only after you say yes to that exact plan.

## 7. How to record a case

For each case write: ID, precondition, steps, expected, actual, pass or fail, a screenshot
without player identifiers, and the SHAs from section 1 plus your branch tip. Event-driven
cases are labelled [event], and prepared data is labelled [prepared] and never counts as event
proof.

## 8. Skill cases S1 to S14 (prompts)

Run them in a fresh session, in order, in your own clone. Replace the bracketed placeholders.
`<site>` is your test site slug, `<q1> <q2> <q3>` are quest ids of your public quests.

| ID | Prompt to type | Expected |
| --- | --- | --- |
| S1 | `What can quest-setup do?` | The answer includes the Shop Builder Quests block operations (create, edit settings, reset media, reorder, limit, move, duplicate, hide and show, delete). |
| S2 | `Add a quests block to my shop.` | The request routes to `quest-setup`, and the skill asks for the missing inputs (site, quests) instead of acting. |
| S3 | `Add a Quests block to the home page of <site> at position 2, showing quests <q1>, <q2> and <q3>, with the heading "Quests".` | The skill runs preflight, backup and a plan, shows a `confirmation_id`, waits for your yes, applies, reads back, and the block renders in the Site Builder editor. |
| S4 | `On the Quests block of <site>, change: limit to 2, card alignment to center, image fit to cover, button style to outline, hide the description, change the block background and the card background, set a custom title and description on <q1>, and set the heading to "My quests" in en-US.` Repeat once per setting group of B16 to B24 if you prefer smaller steps. | Read-back matches each value and the editor shows it. |
| S5 | `Reset the image override of quest <q1> on the Quests block of <site> back to the native image.` (Set an image override first, through S4.) | The override is removed, the native media shows again. |
| S6 | `On the Quests block of <site>, reorder the quests to <q3>, <q1>, <q2> and limit the block to 2 quests.` | New order and limit read back and show in the editor. |
| S7 | `Move the Quests block of <site> to the top of the home page.` | The block moves to index 0 and nothing else changes. If the skill says it is unsupported, it must do nothing, and that passes. |
| S8 | `Duplicate the Quests block of <site> and put the copy at position 3.` | Both instances exist with identical settings. If unsupported, the skill says so and does nothing. |
| S9 | `Hide the Quests block of <site>, then show it again.` | Hidden state round-trips, no other block changes. If unsupported, the skill says so and does nothing. |
| S10 | `Delete the duplicate Quests block on <site>.` Answer yes only to the exact plan it shows. | A backup is taken, the plan names only that block, and after your yes the block is deleted and verification passes. Known gap: the deleted id can stay in the landing's top-level block list, reported as a warning. If unsupported, the skill says so and does nothing. |
| S11 | After S3 to S10, run a full site-structure diff against the first backup: `Compare the current structure of <site> with the backup taken before S3 and list every difference.` | Only the target Quests block (and its heading text) differ. No other block changed. |
| S12 | Three separate prompts: `Change the header block of <site>.`, `Change the default language of <site>.`, `Publish <site>.` | Each is declined or redirected. Nothing is executed. |
| S13 | Three separate runs: (a) a brief that targets a project not in your allowlist (or `--sandbox`); (b) `Add a Quests block to <site> with quest id does-not-exist.`; (c) `Add a Quests block with 30 quests and the limit 50.` | The gate stops each one before any write, with a clear reason. |
| S14 | A fresh tester (not you) follows only sections 3 to 5 of this document, then completes S1 and S3. | Both pass without help from the author. Record every point where the tester had to ask a question. |

Unsupported operations (S7 to S10) pass if the skill clearly says they are unsupported and
does nothing.

## 9. Block cases B1 to B27 (browser, reference)

These test the block itself on stage, with the shop built from your test site. The full
catalogue is in the design spec. Short form:

| ID | Case |
| --- | --- |
| B1 | Anonymous visitor sees quest cards and a "Check progress" CTA. |
| B2 | CTA opens real Login. After interactive login the block loads progress from the native `/me` route. |
| B3 | Xsolla ID token path works if the shop supports it, otherwise N/A with a reason. |
| B4 | A quest with no progress shows Not started. |
| B5 | An in-progress quest shows correct counters (for example 3/5). |
| B6 | [event] A controlled event advances an in-progress quest, the block shows the new count after refresh. |
| B7 | [event] An event completes a quest. The block shows Completed ("See in Backpack" only for item rewards). |
| B8 | N/A: the backend lists only quests inside their date window, so an ended quest disappears instead of showing Expired. Reported as a backend gap. |
| B9 | Switch player: player B never sees player A's progress. |
| B10 | Logout returns the block to the anonymous view. |
| B11 | Invalid or expired token falls back to anonymous or re-login, never shown as Not started. |
| B12 | 5xx or network error shows "could not load status", and retry recovers. |
| B13 | 429 respects `Retry-After`. |
| B14 | A selected quest that is deleted or unpublished is hidden for players, with a warning in the editor. |
| B15 | Isolation: only this merchant and project's quests appear. |
| B16 to B24 | Editor: selection, order and limit; localized headings; title and description overrides; media override and reset; visibility toggles; alignment; image fit; button style; block and card backgrounds. |
| B25 | Editor preview-state controls work, and login is never triggered inside the editor. |
| B26 | All settings survive save plus reload and appear on Preview. |
| B27 | SSR output has no progress and no token. Progress loads client-side only. |

## 10. Known limits

- The Quests block is pinned to the unstable build `0.1.0-qp-3126.2`.
- Quest progress for signed-in players uses `/api/v2/me/...`, live on stage only.
- Add, values, heading and delete were proven live on a test site. Reset, move, duplicate and
  hide or show are covered by unit tests with a fake CLI only, so S5 and S7 to S9 are the first
  live runs. Report any CLI error verbatim, without secrets.
- `block_operations` is not on `main`. It exists only through D2a and D2b.
