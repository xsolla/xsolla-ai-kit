---
name: custom-blocks
description: >-
  Decides whether a Shop Builder (Site Builder) page really needs a custom block, and when it
  does, authors one that uses Shop Builder's own APIs for user controls, canvas text and
  theming instead of hand-rolling them. Use when the standard blocks cannot do what a design
  needs, or when asked to "build a custom block", "write a React block for my shop page",
  "create an AI block", "add a countdown / leaderboard / spin-the-wheel / progress-meter
  block", "should this be a custom block", "my block crashes the settings sidebar", "the block
  renders nothing", "symbol already declared", "localizedText is not a function", "why is
  nothing on my custom block editable", "my block ignores the site theme", or when piping
  generated React into create-custom-block / update-ai-block. Covers the standard-block-first
  decision and what a custom block costs you, the globals-vs-imports contract (`useControls`,
  `text`, `color`, `toggle`, `number`, `select`, `localizedText`, `AutoControls` are injected
  and must NEVER be imported; `TextEditor` must be), one-control-per-`useControls` Magic
  Controls, canvas-editable text via `textFields` + `TextEditor`, reading the site theme, and
  nine static checks to run over the source before any write. Block-based Site Builder sites
  only, not the headless storefront `shop-setup` builds.
metadata:
  owner: n.budhwani
  domain: store
---

## Status

Draft. Self-contained: everything this skill needs is in this directory. It does not depend on
any other skill in this kit.

## What a block is

A Shop Builder (Site Builder) site is a list of **blocks**. A block is a JSON document with a
strict required shape, rendered by the platform: `hero`, `faq`, `gallery`, `newStore`,
`footer`, and 18 more. The document carries `values` (its own settings) and `components` (its
repeatable sub-parts). The wrong shape gives a broken page or a 500, not a helpful error.

A **custom block** (also "AI block") is the escape hatch: you supply React source, Shop Builder
compiles it into a Module Federation bundle and renders it as a block on the canvas, with a
settings panel in the editor sidebar. It is stored as a real block in the site document like
any other — `module: "federated"`, with a synthetic
`ai_<merchantId>_<projectId>_<documentId>` id — with one difference: **there is no schema for
it, so its correctness is entirely yours.**

Nothing else in this kit covers block-based site building, so this skill carries its own
context. The `shop-setup` orchestrator builds a **headless** storefront (Login + Store API +
Headless Checkout, partner-written frontend) — a different build path, with no blocks in it.

## Prerequisites

- A Shop Builder site you may write to. **Sandbox or a test project only — never a partner's
  live project.**
- Merchant id, project id, and the landing id + page id the block goes on. Both ids come from
  `xsolla shopbuilder get-structure` (landing id is the top-level `_id`).
- `xsolla auth login`. The Shop Builder commands work with that session.

## Step 1 · Should this be a custom block at all?

**Answer this before writing a line of React.** A custom block is code the partner now owns
and maintains: no schema, no platform support for its internals, and none of the fixes,
accessibility work or new capabilities that standard blocks keep receiving.

The short version — **if a standard block fits, say so and stop.** Recommending the standard
block is the correct outcome, not a failure to deliver. Name the block and describe what it
would look like.

A custom block is warranted when the interaction **does not exist as a block** (a countdown, a
leaderboard, a wheel, a progress meter, a live-ops panel), when it needs data from a source no
block reads, when it composes several blocks' behaviour into one unit that must stay in sync,
or when a federated block nearly fits but its configuration genuinely cannot express the
requirement.

Full decision table, the 23 native modules and what each one is for, the four federated
blocks, and the ongoing costs you are taking on: **[references/decide.md](references/decide.md)**

## Step 2 · Confirm the hook signatures

Do not write hook calls from memory. Before writing `componentCode`, read the current
`@site-builder/block-utils` documentation available in your tooling for every hook you intend
to use. Signatures differ from what a model has memorised, and a wrong signature fails at
runtime, not at compile time. This applies to "simple" blocks too.

## Step 3 · Author against the contract

Three rules carry most of the failures, so they are here rather than only in the references:

1. **Never import an injected global.** `useControls`, `text`, `color`, `toggle`, `number`,
   `select`, `localizedText` and `AutoControls` are injected into scope. Importing one declares
   the symbol twice and the block fails to compile with *"symbol already declared"*.
2. **`TextEditor` is the opposite** — it looks injected and is not. `import { TextEditor } from
   '@site-builder/block-utils'` or it throws a `ReferenceError` and the block renders nothing.
3. **Take no props.** `export default function MyBlock() { … }`. In particular never
   `({ localizedText })` — the prop shadows the global and the first call fails with
   *"localizedText is not a function"*.

| Then, for | Read |
|---|---|
| Component shape, sidebar controls, persistent state, `settingsCode`, `defaultData` | [references/authoring-contract.md](references/authoring-contract.md) |
| Canvas-editable text, `textFields`, `localizedText`, multi-locale copy | [references/localization.md](references/localization.md) |
| Site colours, fonts, corner radius, and how a block stays on-brand | [references/theming.md](references/theming.md) |

## Step 4 · Check the source — required, before any write

Run the nine static checks in **[references/code-rules.md](references/code-rules.md)** over
your `componentCode`, `settingsCode` and `textFields`.

- Clean ⇒ continue to Step 5.
- Any finding ⇒ **fix every one, then re-run all nine from the top.** Repeat until clean.

**Never skip this**, and never write source with an open finding. Two of the nine catch defects
that crash the editor's settings sidebar — worse than a broken block, because the user cannot
get back into the panel they would use to undo it.

## Step 5 · Plan, confirm, write, verify

1. **Back up first.** `get-structure` and `get-localization`, keep both responses, before the
   first write — not before the first fix.
2. **Show the plan** — which page, where on it, what the block does, which fields the user will
   be able to edit.
3. **Get explicit confirmation.** Wait for it.
4. **Write**:

```bash
xsolla shopbuilder create-custom-block \
  --landing-id <L> --page-id <P> --name "<display name>" \
  --component-code "$(cat block.jsx)" --settings-code "$(cat settings.jsx)"
```

5. **Verify.** `xsolla shopbuilder get-ai-block --id <id>` returns the stored source and the
   block's current internal values — read it back and confirm it is what you sent. Seed data,
   if the block needs any, is a **second call**: `update-ai-block --id <id> --default-data
   '<json>'`, because `create-custom-block` has no `--default-data`.
6. **Stop. Never publish.** A human publishes, in Publisher Account.

## Safety rules

1. Back up the structure and localization before the first write.
2. Show the plan and get explicit confirmation before any write. No silent writes.
3. Sandbox or test project only — never a partner's live project.
4. Prefer the CLI's own commands over ad-hoc API calls.
5. Never publish, and never treat a clean check as permission to go live.
6. Authenticate with `xsolla auth login`. Copying a Publisher Account `pa-v4-token` by hand
   (`XSOLLA_SHOPBUILDER_SESSION`) is a documented gap — record it and stop, do not work around
   it.

## Known limitations

Each of these is filed as a gap rather than patched from here.

- **The checks are guidance, not enforcement.** The agent applies them to its own source, so a
  run can skip them. `create-custom-block` compiles whatever it is handed, and there is no
  `validate-custom-block-code` command in the CLI to fall back on.
- **They are pattern checks.** A clean run means "no matched pattern", not "correct". A
  violation split across lines or hidden behind a helper will pass.
- **`create-custom-block` cannot declare `textFields`** — verified against the installed CLI.
  On that path canvas-editable text is unavailable; see
  [references/localization.md](references/localization.md) for what to do instead.
- **A custom block has no schema.** Nothing validates its `defaultData` field by field, and
  nothing will tell you later that a field you removed is still referenced.
- **You own the code.** That cost is the entire reason Step 1 exists.
