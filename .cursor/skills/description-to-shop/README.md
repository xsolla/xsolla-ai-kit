# description-to-shop

Turns a plain-language game description into a validated Shop Builder assembly brief.
`shop-builder-assembly` performs the plan, backup, CLI writes, verification and preview.

Tracking: **SB-8786**. Depends on **SB-8796 / PR #32**, which must merge first.

## Prerequisites

- `shop-builder-assembly` installed from Xsolla AI Kit
- Xsolla CLI authenticated with `xsolla auth login`
- A mentor-approved sandbox or dedicated test project
- An existing same-project catalog for store sections

## Happy path

1. Give the agent a plain-language game description.
2. Answer one batch of genuinely missing factual questions.
3. Review the normalized brief.
4. Continue with `shop-builder-assembly`; confirm its exact plan hash.
5. Inspect the unpublished result via the editor/preview handoff it returns.

## Known limitations

- Creates no catalog entities and translates no unapproved copy.
- Requests with no standard block are reported, never approximated.
- Shop Builder assembly, safety and CLI limitations live in `shop-builder-assembly`
  and are not duplicated here.
- Publication remains a human action in Publisher Account.

## Layout

```
SKILL.md                            intake and handoff workflow
README.md                           this file
references/intake-schema.md         facts to collect, completeness gate
references/plan-format.md           normalized handoff example
../../evals/description-to-shop/    test inputs, run log, how to run
```
