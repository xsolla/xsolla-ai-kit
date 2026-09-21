# Canvas text and localization

Two separate things, and mixing them up is the most common way a custom block ships looking
finished with nothing on it editable.

- **Canvas-editable text** — the strings the user clicks and edits directly on the page.
  Declared in `textFields`, rendered with `<TextEditor>`.
- **Sidebar strings** — `useControls(text(…))`. Fine for a label nobody translates; **not**
  canvas text, and not a substitute for it.

## Canvas-editable text — three steps, all required

Every heading, paragraph, label and CTA the user should be able to edit on the canvas:

1. **Declare it in `textFields`**: `[{ name: "title", default: "Hello" }]`
2. **Import `TextEditor`** — it is a real import, not an injected global:
   `import { TextEditor } from '@site-builder/block-utils';`
3. **Render it**: `<TextEditor id={localizedText('title')} />`

```jsx
import { TextEditor } from '@site-builder/block-utils';

export default function MyBlock() {
  return (
    <section style={{ padding: 48 }}>
      <TextEditor id={localizedText('title')} />
      <TextEditor id={localizedText('body')} />
    </section>
  );
}
// textFields: [{ name: "title", default: "Launch week" },
//              { name: "body",  default: "Three days only." }]
```

### The silent failures

| Mistake | What happens |
|---|---|
| `localizedText('x')` with no `x` in `textFields` | The field is **silently missing**. Nothing renders, nothing is editable, and there is no error |
| `<TextEditor>` rendered with **no** `textFields` at all | The editor mounts with no bound fields. The block looks done; every string on it is dead |
| `useControls(text('Title', localizedText('title')))` | `text()` is a sidebar-only string control. It does not bind canvas text, so the value edited on the canvas and the value the control writes are two different things |
| `TextEditor` used unimported | `ReferenceError`; the block renders nothing |

None of these throws a useful error at write time. They are checks 5, 6, 9 and 2 in
[code-rules.md](code-rules.md) precisely because nothing else catches them.

## ⚠️ The CLI cannot declare `textFields`

Verified against the installed CLI: `create-custom-block` accepts only `--component-code`,
`--settings-code`, `--name`, `--landing-id`, `--page-id`; `update-ai-block` adds
`--default-data` and `--id`. **Neither has a text-fields flag.**

So a block created through the CLI whose source calls `localizedText()` or renders
`<TextEditor>` comes back with an empty `textRefs` map and nothing on it is editable. On that
path the fault cannot be fixed, only avoided:

- **Author the block without canvas-editable text** — put user-facing strings in sidebar
  controls (`text(…)`) instead, and say so to the user, or
- **Create it through tooling that accepts `textFields`.**

Do not ship a block whose text silently fails to appear. Check `textRefs` on read-back:

```bash
xsolla shopbuilder get-ai-block --id <id> --json     # textRefs must not be {} if the source registers text
```

Filed as a gap. Do not build a workaround.

## How site text works, for context

A custom block's canvas text is registered as refs on the block itself (`textRefs`). The rest
of the site works differently and it is worth knowing which you are looking at:

- A **native** block's text is referenced by an `L:<uuid>` id, and the per-locale HTML lives in
  a **separate localization store keyed by the landing slug** — not in the block. Patching
  `["values","title"]` returns `ok: true` and changes nothing.
- Read it with `get-localization --slug <domain> --json`; write one string with
  `update-localization`, or a whole locale with `update-many-localization`.
- **Text is HTML.** Wrap copy in `<h1>`/`<h2>`/`<p>`; a bare string renders unstyled.
- In a batch write the per-id value **must** be `{"translation": "<html>"}`. A bare string
  returns `200` and writes an **empty string** — the author is told it succeeded.
- Locale codes are full (`en-US`, `fr-FR`, `de-DE`, `ja-JP`, `pt-BR`), and a locale must be
  added with `add-language --language <locale>` before anything can be written into it.

> **Unverified:** whether a custom block's `textRefs` entries are reachable through
> `get-localization` / `update-localization` the way native `L:` ids are — i.e. whether custom
> block copy can be translated per locale through the same store. Do not tell a user their
> custom block is translatable until this is confirmed against Shop Builder's own docs. If
> multi-locale copy is a requirement, prefer a native block for that copy.

## Multi-language blocks

If the block must render differently per locale beyond its text — date formats, currency,
reading direction — read the locale from the page at render time rather than branching on a
sidebar `select`. A sidebar control is set once by the author; the locale changes per visitor.
