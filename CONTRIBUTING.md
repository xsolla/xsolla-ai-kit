# Contributing

For contributing agent skills — frontmatter, required sections, agent tests — see
[CONTRIBUTING-skills.md](CONTRIBUTING-skills.md).

## Before you open a pull request

Run the validator. It checks everything CI checks and takes about a second:

```bash
python3 .github/scripts/validate_skills.py
```

It verifies skill frontmatter, the required sections, relative link targets, JSON
validity, that every skill appears in both registries (`skills/README.md` and
`AGENTS.md`), and that the generated files (`.cursor/skills/**`, `CLAUDE.md`) match
their sources. It also scans for credentials.

Pre-existing violations are recorded in [.github/skills-baseline.json](.github/skills-baseline.json)
so the check can be enforcing without blocking unrelated work. **Don't add to the
baseline to get a PR green** — fix the finding. Removing entries is always welcome; run
`python3 .github/scripts/validate_skills.py --update-baseline` after fixing one.

## Generated files

`.cursor/skills/**` and `CLAUDE.md` are generated from `skills/**` and `AGENTS.md`.
Commit them alongside your change — CI fails on drift. To regenerate locally, mirror
what [.github/workflows/sync-providers.yml](.github/workflows/sync-providers.yml) does:

```bash
rm -rf .cursor/skills && mkdir -p .cursor/skills
for d in skills/*/; do [ -f "$d/SKILL.md" ] && cp -R "$d" ".cursor/skills/$(basename "$d")"; done
cp AGENTS.md CLAUDE.md
```

## Security

Never commit a real credential — key, token, JWT, webhook secret, or session cookie.
To report a vulnerability, see [SECURITY.md](SECURITY.md); don't open a public issue.

## External contributions

This repository is developed by Xsolla and is public so that partners can read, install,
and audit the skills their agents run.

We do accept bug reports from anyone, and we're glad to get them — wrong guidance in a
skill is worse than a missing one, because an agent follows it confidently. **Open an
issue** describing the defect and, where you can, cite the authoritative source or the
skill in this repo that already has it right.

We generally **do not merge unsolicited pull requests** from outside Xsolla. Skills
encode integration paths that Xsolla is accountable for, and each one is owned by the
engineer responsible for that surface (see [.github/CODEOWNERS](.github/CODEOWNERS)).
An accurate external report will be verified and landed by a maintainer, with credit in
the commit — see #26 and #27 for how that works in practice.

Note that a SKILL.md is not documentation an agent reads for reference; it is an
instruction payload an agent executes. We review changes to these files the way we'd
review changes to code that runs with the reader's credentials, which is why the bar for
provenance is higher here than in a typical docs repo.
