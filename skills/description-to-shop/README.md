# description-to-shop

Turns a plain-language game description into a validated Shop Builder assembly brief.
The shared `shop-builder-assembly` skill performs the plan, backup, CLI writes,
verification, and preview workflow.

Tracking: **SB-8786**. Integration dependency: **SB-8796 / PR #32** must merge first.

## Prerequisites

- `shop-builder-assembly` installed from Xsolla AI Kit
- Xsolla CLI authenticated with `xsolla auth login`
- A mentor-approved sandbox or dedicated test project
- An existing same-project catalog for store sections

## Happy path

1. Give the agent a plain-language game description.
2. Answer one batch of genuinely missing factual questions.
3. Review the normalized brief produced from
   `references/intake-schema.md` and the assembly brief contract.
4. Continue with `shop-builder-assembly`; review and confirm its exact plan hash.
5. Inspect the unpublished result using the editor/preview handoff returned by the
   assembly skill.

## Known limitations

- This skill does not create catalog entities or translate unapproved copy.
- Requests with no standard block are reported rather than approximated.
- Shop Builder assembly, safety, and CLI limitations are documented centrally in
  `shop-builder-assembly`; they are not duplicated here.
- Publication remains a human action in Publisher Account.

## Layout

```
SKILL.md                       intake and handoff workflow
README.md                      prerequisites and happy path
references/intake-schema.md    facts to collect and completeness gate
references/plan-format.md      normalized handoff example
evals/                         description-intake test inputs and results
```
