<!--
Adding or changing a skill? Run the validator locally first — it checks everything CI
checks, in about a second:

    python3 .github/scripts/validate_skills.py
-->

## What this changes

<!-- One or two sentences. If it fixes wrong guidance, say what an agent did wrong before. -->

## Agent test

<!--
Required for any new or changed skill (CONTRIBUTING-skills.md). Paste the exact prompt
you ran and a one-line result. "It looks right" is not an agent test.
-->

**Prompt:**

```text

```

**Result:**

## Checklist

- [ ] `python3 .github/scripts/validate_skills.py` passes
- [ ] Registries updated if a skill was added or renamed — `skills/README.md` and `AGENTS.md`
- [ ] Generated files committed — `.cursor/skills/**` and `CLAUDE.md` (CI fails on drift)
- [ ] No real credentials anywhere: keys, tokens, JWTs, webhook secrets, session cookies
- [ ] Cross-references to other skills point at guidance that actually exists there
- [ ] Env var names match the ones already used in the kit (e.g. `XSOLLA_PROJECT_API_KEY`)

## Notes for reviewers

<!-- Anything deliberately left out, or an open question you want a decision on. -->
