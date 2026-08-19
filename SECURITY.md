# Security Policy

## Reporting a vulnerability

**Do not open a public issue or pull request for a security problem.**

Report it privately through one of:

- [GitHub private vulnerability reporting](https://github.com/xsolla/xsolla-ai-kit/security/advisories/new) — preferred
- Xsolla security: <security@xsolla.com>

Please include what the issue is, how to reproduce it, and what an attacker could
achieve. We'll acknowledge within three business days.

## What counts as a vulnerability here

This repository contains **agent skills** — Markdown instructions that AI coding
agents load and act on. It ships no runtime code, so the threat model is unusual and
worth stating plainly.

Treat these as security issues:

- **Instructions that leak credentials.** A skill that tells an agent to put a secret
  key, API key, or session token somewhere client-side, log it, commit it, or send it
  to a third party.
- **Instructions that weaken verification.** Guidance that skips or botches webhook
  signature verification, disables TLS checks, accepts unauthenticated input as
  trusted, or recommends a non-constant-time secret comparison.
- **Prompt injection in skill content.** Text crafted to redirect an agent away from
  the user's intent — instructions to fetch and execute remote content, exfiltrate
  files, or ignore prior instructions. This is the main supply-chain risk for this
  repo: a skill file *is* an instruction payload.
- **Committed secrets.** A real key, token, JWT, or private key in the tree or in
  history. Report it privately, don't push a revert — the credential must be rotated.
- **Workflow privilege escalation.** A GitHub Actions change that grants a job more
  token scope than it needs, runs untrusted PR code with write access, or uses an
  unpinned third-party action.

Not security issues: a wrong API endpoint or field name, a skill that fails to trigger,
or documentation that is merely out of date. Those are normal bugs — open an issue.

## Credential handling in skills

Skills in this repo reference credentials by environment-variable name only
(`XSOLLA_PROJECT_API_KEY`, `XSOLLA_WEBHOOK_SECRET`, `XSOLLA_PUBLISHER_TOKEN`, …).

When contributing:

- Never paste a real key, token, JWT, merchant ID secret, or webhook secret — not in
  a SKILL.md, a reference, a fixture, or a PR description. CI scans for JWTs, GitHub
  tokens, `sk-` keys, and private keys, but it is a backstop, not a guarantee.
- Keep secrets server-side in the guidance you write. Any skill that has an agent put
  a secret in browser-reachable code is a bug in the skill.
- Sanitize fixtures. Real payloads carry real user emails, IPs, and transaction IDs —
  replace them with synthetic values, as `skills/webhooks-impl/fixtures/` does.

## Supported versions

The `main` branch is the only supported version. Fixes land there and flow to plugin
consumers on their next install or update.
