# Shop Builder assembly skill

Assembles an unpublished Shop Builder site in a sandbox or dedicated test project
from a normalized JSON shop brief.

## Prerequisites

- Xsolla CLI with `shopbuilder` commands
- `xsolla auth login` completed for a Publisher account
- Sandbox IDs or an explicitly acknowledged dedicated test project configured
- Existing catalog group IDs for any `newStore` sections
- A dedicated test project; never use a partner live project
- For a non-sandbox test project, a separate local approval allowlist containing the
  exact merchant/project identity and the mentor or lead's approval reference

## Happy path

1. Copy the closest file in `examples/` to `brief.json` and replace the project, game,
   site, and catalog values.
2. Validate the brief and verify the local CLI context:

   ```bash
   python3 scripts/validate_shop_brief.py brief.json
   python3 scripts/preflight.py brief.json \
     --approved-test-projects /path/to/approved-test-projects.json
   ```

3. If the target exists, back it up before rendering or confirming a plan:

   ```bash
   python3 scripts/backup_shop.py --brief brief.json --slug my-shop --output-dir ./backups/my-shop
   ```

4. Render the target-bound plan, review its exact block removals, and explicitly
   confirm its `confirmation_id`:

   ```bash
   python3 scripts/render_plan.py brief.json --structure ./backups/my-shop/structure.json
   python3 scripts/apply_plan.py brief.json --confirmation-id <id> \
     --backup-dir ./backups/my-shop \
     --approved-test-projects /path/to/approved-test-projects.json
   ```

   For a new slug, render without `--structure` and confirm the bootstrap-only plan.
   Bootstrap creates the landing and all requested page paths. Afterward, back up the
   generated templates and repeat this step with `--structure` before any template
   blocks are removed. An existing site that is missing requested page paths uses the
   same re-backup/reconfirmation boundary after those paths are created.

5. Follow the confirmed assembly sequence in `SKILL.md`; verify and preview, but do
   not publish. Export a fresh post-apply structure and compare it with the exact
   confirmed plan:

   ```bash
   python3 scripts/verify_structure.py \
     --plan ./artifacts/confirmed-plan.json \
     --structure ./artifacts/post-apply/structure.json
   ```
6. For formal runs, append the result using `references/evaluation.md` and check the
   metrics with `scripts/summarize_evals.py`.

To sanitize the structural block contracts from a UI-created export without retaining
IDs, copy, account data, or URLs, run `scripts/extract_block_contracts.py` with
`--output` and reconcile its output with `references/block-catalog.md`. Federated
wrappers are reported under their effective `values.blockId` module.

## Known limitations

- Formal reviewer approval of the standard block inventory and three presets is
  recorded during the PR phase; it is not required to begin implementation testing.
- Use `references/expert-review.md` to record the eventual review and its evidence.
- Test project IDs are intentionally not stored in committed examples.
- A `test` brief is insufficient on its own: preflight and apply also require a
  separate, uncommitted allowlist record for the exact merchant/project IDs. Sandbox
  briefs do not require this file.
- The CLI does not currently expose an authoritative list of standard block modules.
- Multi-command Shop Builder authentication, readiness verification, and CLI preview
  have confirmed defects captured in `references/test-findings.md`.
- The CLI has no page-deletion command. Application stops before writes when an
  existing target contains pages outside the confirmed plan.
- The official block inventory is fully documented, and every observed official
  module has a UI-created exported contract. Subscriptions is documented but absent
  from the observed palette/export, while five palette entries are absent from the
  official block page.
- The current apply script implements pages, navigation, blocks, requested locales,
  and catalog-section links. Catalog sections use targeted component patches, disable
  titles until approved localized text exists, and are re-read after each application.
  `verify_structure.py` checks target identity, page paths, block order,
  retained/removal IDs, navigation targets, catalog mappings, locales, and unpublished
  state. Optional theme and copy/asset application remain blocked on stable normalized
  input fields and final contract acceptance; CLI readiness and preview remain tracked
  gaps.
- The Description caller is integrated in its draft PR by producing this skill's brief
  and removing duplicate assembly scripts. External Store and Figma caller skills are
  tracked separately and are not yet present in this repository.
