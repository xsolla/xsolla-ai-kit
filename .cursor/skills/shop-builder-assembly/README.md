# Shop Builder assembly skill

Assembles an unpublished Shop Builder site in a sandbox or dedicated test project
from a normalized JSON shop brief.

## Prerequisites

- Xsolla CLI with `shopbuilder` commands
- `xsolla auth login` completed for a Publisher account
- Sandbox IDs or an acknowledged dedicated test project
- Existing catalog group IDs for any `newStore` sections
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

4. Render the target-bound plan, review removals, and confirm its `confirmation_id`:

   ```bash
   python3 scripts/render_plan.py brief.json --structure ./backups/my-shop/structure.json
   python3 scripts/apply_plan.py brief.json --confirmation-id <id> \
     --backup-dir ./backups/my-shop \
     --approved-test-projects /path/to/approved-test-projects.json
   ```

   For a new slug, render without `--structure` and confirm the bootstrap-only plan.
   Bootstrap creates the landing and page paths. Then back up generated templates and
   repeat with `--structure` before removing blocks. Use the same re-backup and
   reconfirmation boundary after adding missing paths to an existing site.

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

To sanitize a UI-created export without retaining IDs, copy, account data, or URLs,
run `scripts/extract_block_contracts.py --output ...` and reconcile it with the block
catalog. Federated wrappers use their effective `values.blockId` module.

## Known limitations

- Record formal inventory and preset approval in `references/expert-review.md` during
  PR review; implementation testing may start earlier.
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
- Apply covers pages, navigation, blocks, locales, and catalog links. Catalog patches
  are targeted, disable unapproved titles, and are re-read. Verification checks target,
  paths, block order, retained/removal IDs, navigation, catalog, locales, and unpublished
  state. Theme and copy/assets await stable normalized inputs and contract acceptance;
  CLI readiness and preview remain tracked gaps.
- The Description caller is integrated in its draft PR by producing this skill's brief
  and removing duplicate assembly scripts. External Store and Figma caller skills are
  tracked separately and are not yet present in this repository.
