# Onboarding intake regression checks (SB-9430)

Run the deterministic tests with:

```sh
python3 -B -m unittest discover -s skills/description-to-shop/tests -v
```

The tests cover intake preservation, incomplete/absent/corrupt ledgers, route mismatches,
legacy site-kind defaults, portal/headless routing, no credential/step leakage, and no
file writes. They do not prove the agent asks the right questions.

## Claude behavior check

Use a dedicated approved test project with an existing catalog. In a separate working
directory, prepare `.env` routing keys `XSOLLA_BUILD_PATH=shopbuilder` and
`XSOLLA_SITE_KIND=shop`. Use `shop-plan` to record confirmed onboarding intake, including
game name, platforms, approved description, domain, primary locale and locales. Load the
plugin from the branch under test, not an older installed copy.

Prompt (replace the skill path with the branch's absolute path):

> Continue my Shop Builder shop setup. Use the description-to-shop skill at
> <branch>/skills/description-to-shop/SKILL.md. I want currency packs and featured bundles
> in the shop. This directory is my working project. Read-only intake only for now: do not
> build, write files, log in, or modify anything. Ask me if you still need any information.

Expected: the agent reads `.xsolla/onboarding.json`, reuses the supplied game/site fields,
discovers the test project's catalog, and asks only about remaining gaps or conflicts.
Check the actual questions and source attribution, not just its claim that intake loaded.

Follow up with an unexplained conflicting game/platform value: expect one focused conflict
question, not a repeated interview. An explicit correction should instead be attributed
in the brief without rewriting the ledger. A malformed ledger or route mismatch must stop.
An absent ledger should preserve conversation answers and ask only for genuine gaps.

For the full acceptance run, continue with the verified catalog and normal assembly safety
gates on the approved test project. Record required questions across planning and shop
intake: every provided answer should be requested only once. Plan approval is not a
duplicate intake question. Do not publish or bypass assembly safeguards.
