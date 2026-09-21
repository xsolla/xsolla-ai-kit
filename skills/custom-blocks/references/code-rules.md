# The nine code rules

Nine static checks for the React source of a custom Shop Builder block. Every one is a
**runtime or compile failure**, not a style preference — and two of them crash the editor's
settings sidebar, which is worse than a broken block, because the user cannot get back into
the panel they would use to undo it.

Run all nine **before** sending source to `create-custom-block` or `update-ai-block`. Fix every
finding, re-run from the top, repeat until clean. Never skip the run, and never write source
with an open finding. There is no `validate-custom-block-code` command in the CLI to fall back
on — `create-custom-block` compiles whatever it is handed.

## Inputs

| Input | What it is |
|---|---|
| `componentCode` | The React component rendered on the canvas |
| `settingsCode` | The settings-panel component, or omitted for no panel |
| `textFields` | `[{ name, default }]` — every canvas-editable text field, declared up front |

> ⚠️ **The CLI cannot supply `textFields`.** `create-custom-block` takes only
> `--component-code`, `--settings-code`, `--name`, `--landing-id`, `--page-id`;
> `update-ai-block` adds `--id` and `--default-data`. On that path rules 5 and 6 cannot be
> *satisfied*, only avoided — see [localization.md](localization.md).

## What each rule scans

Getting this wrong makes a rule look broken. Two rules scan the component and settings source
**joined together**; the rest scan the component source only.

| Rule | Scans |
|---|---|
| 1 · `forbidden-import` | `componentCode` + `settingsCode`, joined |
| 4 · `export-default-class` | `componentCode` + `settingsCode`, joined |
| 2 · `missing-texteditor-import` | *usage* in either input; the *import* in the joined text |
| 3, 5, 6, 7, 8, 9 | `componentCode` only |

## The nine rules

### 1 · `forbidden-import` — never import an injected global

**Check.** Any of these symbols imported from `@site-builder/block-utils`:

```
useControls   text   color   toggle   number   select   localizedText   AutoControls
```

Match on an import statement naming any of them — including when it is one name among several
in the same braces.

**Why it breaks.** They are injected into scope automatically. Importing one declares the
symbol twice, and the block fails to compile with a "symbol already declared" error.

**Fix.** Remove the symbol from the import list. Call it directly, unimported. If removing it
empties the braces, delete the whole import statement.

### 2 · `missing-texteditor-import` — `TextEditor` is NOT a global

**Check.** `TextEditor` appears anywhere in the component or settings source, but no
`import { TextEditor } from '@site-builder/block-utils'` appears in either.

**Why it breaks.** Unlike the eight symbols above, `TextEditor` is a real import. Using it
without importing it throws a `ReferenceError` at runtime — the block renders nothing.

**Fix.** Add `import { TextEditor } from '@site-builder/block-utils';`

The pair of rules 1 and 2 is the trap: the symbols that *look* like they need importing must
not be, and the one that looks injected must be.

### 3 · `localized-text-prop-shadow` — do not take `localizedText` as a prop

**Check.** `localizedText` destructured from the component's props, in either form:

```jsx
export default function MyBlock({ localizedText }) { … }     // ✗
const MyBlock = ({ localizedText }) => { … }                 // ✗
```

**Why it breaks.** The prop shadows the injected global and arrives `undefined`, so the first
call fails with "localizedText is not a function".

**Fix.** Take no props at all. `export default function MyBlock() { … }` and call
`localizedText('key')` directly.

### 4 · `export-default-class` — function components only

**Check.** `export default class` anywhere in the component or settings source.

**Why it breaks.** The transform pipeline that compiles block source does not support it.

**Fix.** `export default function MyBlock() { … }` or `export default () => { … }`.

### 5 · `undeclared-text-fields` — every `localizedText` key must be declared

**Check.** Collect every key from `localizedText('key')` / `localizedText("key")` in the
component source. Any key not present as a `name` in `textFields` is a finding.

**Why it breaks.** The text field is silently missing — nothing appears on the canvas and
nothing is editable, with no error to explain it.

**Fix.** Add each missing key: `{ name: "<key>", default: "…" }`. Report the exact missing
keys in the finding, so the fix needs no re-reading of the source.

On the CLI path there is nothing to add them *to* — see the warning above. There the finding
is "this block cannot declare text fields", and the fix is to drop `localizedText()`; the
alternatives are in [localization.md](localization.md).

### 6 · `missing-text-fields` — `<TextEditor>` with nothing declared

**Check.** `<TextEditor` appears in the component source and `textFields` is absent or empty.

**Why it breaks.** The editor renders with no bound fields, so there is nothing editable on
the canvas — the block looks finished and is not.

**Fix.** Declare `textFields: [{ name: "…", default: "…" }]`, one entry per `TextEditor`.

Same caveat: on the CLI path, `<TextEditor>` cannot be made to work at all.

### 7 · `use-controls-object-arg` — one control per call

**Check.** `useControls(` followed by an object literal — `useControls({`.

**Why it breaks.** Only one control per call is supported. Passing an object returns
`undefined`, so the destructuring or assignment that follows throws at runtime.

**Fix.** One call per field:

```jsx
const label = useControls(text('Label', 'default'));
const show  = useControls(toggle('Show badge', false));
```

For canvas-editable text, do not use a control at all — render
`<TextEditor id={localizedText('key')} />`.

### 8 · `control-factory-object-arg` — first argument is the control NAME

**Check.** Any of `color(`, `toggle(`, `number(`, `select(`, `text(` followed by an object
literal — `color({`, `toggle({`, and so on.

**Why it breaks.** This is one of the two sidebar-crashers. The first argument is the
control's name — a string key. An object passed there is *stored as the name*. The settings
panel then tries to render that raw object as a React child and **the whole sidebar crashes**,
so the user cannot open settings to undo it.

**Fix.** Positional string-first arguments:

```jsx
color('My Colour', '#ff0000')
toggle('Show badge', true)
number('Count', 0, { min: 0, max: 10, step: 1 })
select('Size', ['sm', 'lg'], 'sm')
text('Label', 'default')
```

Note that `number`'s options object is the *third* argument, which is legitimate — only an
object in the **first** position is a finding.

### 9 · `text-control-with-localized-text` — `text()` does not bind canvas text

**Check.** A `text()` call whose second argument is a `localizedText(` call:
`text('Heading', localizedText('title'))`.

**Why it breaks.** `text()` produces a sidebar-only string control. It does not bind to a
canvas-editable text field, so the value the user edits on the canvas and the value the
control writes are not the same thing.

**Fix.** Render canvas text directly: `<TextEditor id={localizedText('title')} />`. Keep
`text()` for plain sidebar strings with a plain string default.

## Reporting

One finding per violation, carrying all three parts — drop any of them and the finding stops
being actionable:

| Part | Content |
|---|---|
| `rule` | The rule id, e.g. `control-factory-object-arg` |
| `message` | What is wrong **and** how it fails at runtime |
| `suggestion` | The corrected form, concretely — the code to write instead |

## Known limitations

- These are textual pattern checks, so they are best-effort. A violation written across
  several lines, generated dynamically, or hidden behind a helper function can pass. A clean
  run means "no matched pattern", not "correct".
- Rules 1, 2, 8 and 9 are only meaningful for `@site-builder/block-utils` symbols. Source
  importing something else entirely is not checked.
- Passing all nine says nothing about whether the block *works* — it says the block will
  compile, mount, and not take the sidebar down with it.
