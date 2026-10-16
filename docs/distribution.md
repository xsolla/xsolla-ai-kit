# How skills reach agents

No installation required for most agents. Open this repo in your tool and skills are available immediately.

| Agent          | Mechanism                                                  | Notes                                                                                     |
|----------------|------------------------------------------------------------|-------------------------------------------------------------------------------------------|
| Claude Code    | Reads `CLAUDE.md` → copy of `AGENTS.md`                    | Auto on repo open                                                                         |
| GitHub Copilot | Reads `.github/copilot-instructions.md`                    | Auto on repo open                                                                         |
| Cursor         | Reads `.cursor/skills/*/SKILL.md` (+ short always-on rule) | Skills synced by `sync-providers.yml`; brief pointer in `.cursor/rules/xsolla-ai-kit.mdc` |
| Codex CLI      | Reads `AGENTS.md` at root                                  | Auto on repo open                                                                         |
| Windsurf       | Reads `AGENTS.md` at root                                  | Auto on repo open                                                                         |
| Roo Code       | Reads `AGENTS.md` at root                                  | Auto on repo open                                                                         |
| Augment        | Reads `AGENTS.md` at root                                  | Auto on repo open                                                                         |
| Amp            | Reads `AGENTS.md` at root                                  | Auto on repo open                                                                         |

## Through the Xsolla CLI

The CLI ships with a built-in `ai-kit` skill source that points at `skills/` in this repo,
so a developer can install the kit without cloning it:

```bash
xsolla skills install --source ai-kit            # into the current project
xsolla skills install --source ai-kit --global   # for every project
```

Remote installs are pinned to a commit SHA. Skills in this repo are the source of truth, so
keep them under `skills/<name>/` or the CLI won't find them. The CLI installs each skill on
its own, so a skill must not depend on files in another skill's directory to run its
preflight.
