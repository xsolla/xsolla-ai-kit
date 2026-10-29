# description-to-shop

Turns a plain-language game description into a validated Shop Builder assembly brief.
`shop-builder-assembly` performs the plan, backup, CLI writes, verification and preview.

## Prerequisites

- `shop-builder-assembly` installed from Xsolla AI Kit
- Xsolla CLI authenticated with `xsolla auth login`
- A mentor-approved dedicated test project
- An existing same-project catalog for store sections

## Happy path

1. Give the agent a plain-language game description, or continue after `nocode-shop-setup`.
   Confirmed answers in the project's `.xsolla/onboarding.json` are reused automatically.
2. Answer one batch of genuinely missing factual questions.
3. Review the normalized brief.
4. Continue with `shop-builder-assembly`; confirm its exact plan hash.
5. Inspect the unpublished result via the editor/preview handoff it returns.

## Known limitations

- Creates no catalog entities and translates no unapproved copy.
- Reads onboarding intake only; ledger step updates and the SB shop onboarding handoff
  report are not implemented by this skill.
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
references/onboarding-intake.md     reuse, mapping and conflict rules
scripts/read_onboarding.py          read-only onboarding loader
tests/test_read_onboarding.py       loader regression tests
```
