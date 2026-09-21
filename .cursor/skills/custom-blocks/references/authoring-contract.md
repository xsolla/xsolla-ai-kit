# The authoring contract

What Shop Builder injects, what you must import, and how user-editable settings work. Getting
any of this wrong fails at runtime or in the editor, not at compile time.

## Globals — never import these

Eight symbols are injected into scope automatically:

```
useControls   text   color   toggle   number   select   localizedText   AutoControls
```

Importing any of them from `@site-builder/block-utils` declares the symbol twice and the block
fails to compile with **"symbol already declared"**. Call them directly, unimported.

## Imports — these are real

```jsx
import { TextEditor } from '@site-builder/block-utils';                              // any canvas text
import { useInternalBlockSelector, useInternalChangeBlock } from '@site-builder/block-utils';
```

`TextEditor` is the trap: it looks injected and is not. Unimported, it throws a
`ReferenceError` and the block renders nothing at all.

## Component signature

```jsx
export default function MyBlock() { … }     // no props
```

- **No props**, and in particular never `({ localizedText })` — destructuring it shadows the
  injected global, the prop arrives `undefined`, and the first call fails with
  **"localizedText is not a function"**.
- **`export default class` is not supported** by the transform pipeline that compiles block
  source. Use a function or an arrow.
- **Inline styles only**, no third-party libraries. Browser APIs are fine: `fetch`,
  `setTimeout`, `localStorage`, `Date`, `Math`.
- Source is TSX or JSX — `create-custom-block` compiles either.

## User controls — Magic Controls

Magic Controls are the supported way to give the user editable settings. One
**`useControls()` call per field**, at the top level of the component — never inside an `if`,
a loop, or a `map`:

```jsx
const label = useControls(text('Label', 'default'));
const on    = useControls(toggle('Show badge', false));
const n     = useControls(number('Count', 0, { min: 0, max: 10, step: 1 }));
const size  = useControls(select('Size', ['sm', 'lg'], 'sm'));
const hex   = useControls(color('Accent', '#000000'));
```

### The two ways this goes wrong

**The first argument of every control factory is the control's NAME, a string.** Pass an
object literal there and the object is stored as the name; the settings panel then tries to
render a raw object as a React child and **the whole sidebar crashes** — the user cannot open
settings to undo it. `number()`'s options object is the *third* argument and is legitimate
there.

**`useControls()` itself takes one control, not an object.** Passing an object literal returns
`undefined`, so the assignment or destructuring that follows throws at runtime.

### Which control for what

| Factory | Produces | Use for |
|---|---|---|
| `text(name, default)` | Sidebar string field | Labels and strings that are *not* canvas-edited. For visible copy use [localization.md](localization.md) instead |
| `toggle(name, default)` | Checkbox | Show/hide, on/off |
| `number(name, default, opts)` | Number field | Counts, durations, sizes. `opts` = `{ min, max, step }` |
| `select(name, options, default)` | Dropdown | A closed set of variants |
| `color(name, default)` | Colour picker | Per-block colour overrides — see [theming.md](theming.md) first |

## Persistent data outside the sidebar

Only when a field genuinely does not belong in the sidebar:

```jsx
const DEFAULT_VALUES = { … };                                    // top of file
const raw    = useInternalBlockSelector(b => b.values.internalBlockValues);
const values = { ...DEFAULT_VALUES, ...(raw || {}) };
```

**Do not mix the two systems.** `useInternalBlockSelector`/`DEFAULT_VALUES` and Magic-Controlled
fields do not compose, and `defaultData` is for the former only.

## The settings panel — `settingsCode`

- **With Magic Controls**, the whole panel is one line:

  ```jsx
  export default () => <AutoControls />;
  ```

- **Manual**, only when Magic Controls genuinely cannot express it: import the same hooks,
  write through `useInternalChangeBlock()`, spreading `DEFAULT_VALUES`. Match the editor's own
  chrome so the panel does not look bolted on — background `#1e2126`, border `#3a3f46`, text
  `#e0e3e8`.
- **Omit `--settings-code`** for a block with no settings panel at all.

## `defaultData`

Plain JSON, for non-Magic-Control persistent fields only. No functions, no `Date`s, no
`undefined`.

Note the asymmetry on the CLI path, verified against the installed CLI: `create-custom-block`
has **no `--default-data` flag**, and only `update-ai-block --default-data` can set internal
values. A block that needs seed data therefore takes **two calls**, and its first render
happens with no values at all — so the component must tolerate missing values rather than
crash on them. The `{ ...DEFAULT_VALUES, ...(raw || {}) }` spread above is what makes that
safe.
