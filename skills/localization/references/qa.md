# QA before import

Two passes that catch different classes of error, run on **every** translation —
AI-produced and human-supplied alike. A partner's CSV is not exempt: it arrives with its
own failure modes (wrong column, stale rows, mangled encoding).

| | Deterministic (`check`) | Semantic (agent) |
|---|---|---|
| Catches | mechanical breakage a rule can express | meaning, consistency, register |
| Blocking | `!` yes, `~` no | judgement |
| Runs | after `fill`/`merge`, before `import` | same pass, on the same rows |

## Deterministic — `check <csv> [--max-len N] [--source <loc>]`

Exit 1 on any hard (`!`) issue. Two problems are refused earlier still, by the reader
itself, before any `!` is counted, because neither leaves a well-formed table to check:
an unreadable or non-UTF-8 file, and a **duplicate column name** — `csv.DictReader`
keeps only the last column of a repeated name, so in `en,de,de` the first `de` is
discarded inside the parser, where no later guard could compare the two.

- **The source column** — a source column that is not `en` is **blocking**, because the
  first language column is taken as the source positionally and its contents are never
  imported. Two shapes: `en` sitting further right is a spreadsheet round-trip that
  reordered the columns; **no `en` at all** is usually a partner's file, which should go
  through `merge` (it treats every language column as a target) rather than `import`.
  Answer it rather than suppress it: put the source column first, load it with `merge`,
  or pass `--source <loc>` to name the source (and the order stops mattering).
- **The address itself** — the **whole** address is checked, because every part of it is
  consumed by an equality test somewhere and anything that does not match is dropped by
  a `continue`. Blocking: an unknown `entity` (`itemz`), a field the entity does not
  have (a promotion's `description`), an empty `id`, a `subid` on a top-level field, and
  a nested field (`step_name`, attribute `value`) with no `subid`. Surrounding
  whitespace is normalized rather than rejected — it is unambiguous. Without this the
  row survives QA, then addresses nothing at import and the translation is gone with no
  message.
- **A translated cell with an empty source** is a `~`: every other check compares the
  target against the source, so none of them can run on it. Not data loss, but not
  verified either — `check` used to report it clean.
- **Contradictory duplicates** — the same address appearing twice with two different
  translations for one locale. One row silently winning is how a reviewed translation
  gets replaced by an unreviewed one; which to keep is a human's call.
- **Locale codes** — an unrecognized column (`pt-PT`, `en-GB`) is **blocking**: it 404s
  the whole PUT on import. A canonical 5-letter code (`ru-RU`) is a soft `~` naming the
  2-letter rename, which `import`/`merge` do themselves.
- **Missing translations** — how many target cells in scope are still blank.
- **Placeholder parity** — brace groups are parsed with a nesting counter and reduced to
  the **argument name**; printf tokens (`%s`, `%1$s`) are compared with their repeat
  count. So `{name}`, `{{brand}}` and full ICU all work, and a Russian plural with
  `one/few/other` against English `one/other` is *not* a mismatch — only a renamed,
  dropped or added variable is. What is compared is the **identity** of each variable:
  **order is deliberately ignored**, because word order legitimately changes between
  languages (`{a} then {b}` → `{b} then {a}` is correct, not a defect). One blind spot
  worth knowing: brace names are compared as a set, so a *repeated* brace placeholder
  losing a repeat (`{n} of {n}` → `{n}`) is not caught — printf repeats are. Check a
  repeated brace variable by eye in the semantic pass.
- **Markup integrity** — HTML/Markdown present in the source must survive: same tags,
  balanced, none invented. A translated `<b>` that lost its closing tag breaks the
  storefront, not just the string.
- **URLs** — links in the source must appear unchanged in the translation. Translating
  the inside of a URL is a common and silent model error.
- **Encoding and special characters** — the cell must not contain a replacement
  character (`U+FFFD`) or a C0 control other than tab/newline, which is what a mangled
  encoding round-trip actually leaves behind. Note the limit: mojibake made of valid
  printable characters (`Ã©` for `é`) passes this check, because nothing in the bytes is
  illegal — non-ASCII round-tripping is worth a glance in the semantic pass.
- **Untranslated cells that look translated** — a target byte-identical to the source is
  almost always "the model echoed the English". Warn rather than block: some terms
  legitimately match (`Bundles` → `Bundles`), and the glossary removes most of the noise.
- **Length anomalies** — see below.

## Length

Length is used to **find translation errors**, not to enforce layout.

Growth is real but uneven — measured en → de on a live catalog: **+24% overall**, while
`Gems` → `Edelsteine` is **+150%** and long descriptions move by 5–10%. So a single
global limit is useless: it never fires on the short `name`s that actually break UI, and
fires constantly on descriptions that are fine.

- **Ratio checks apply only to strings of ~20 characters or more.** Below that the
  denominator is too small for a percentage to mean anything.
- **Much longer than the source** (roughly 3× on a long string) → the model added
  something: a parenthetical gloss, a duplicated term, its own commentary.
- **Much shorter** → part of the string was dropped.
- **Identical to the source** → probably untranslated (above).
- **`--max-len` is per-field and warning-only** — `--max-len 40` for every field, or
  `--max-len name=30,description=200` to set them separately. A limit must be **1 or
  more**: a negative one flagged every cell and `0` silently disabled the check, so both
  are refused. Omit the flag to skip the check entirely. Hard on `name`, loose on
  `description`, none on `long_description`. Characters are a proxy for pixel width, not
  a measure of it — German compounds do not wrap, CJK glyphs are double-width.
- The limit is the partner's layout, which this skill cannot know. Derive a budget from
  the data instead: the longest existing `name` that already renders fine is the
  evidence. And when a correct translation does not fit, the fix is usually CSS
  (wrapping, `text-overflow`, font size), **not** a worse translation. Never block a
  correct translation on length.

## Semantic — the agent's own review

`check` cannot judge these. Do them on the same rows, before the preview.

- **One term, one rendering, across every entity type.** A currency named in `items`, in
  `virtual_currency` and in each `vc_package` must match. Batches are cut per entity, so
  the model never sees them side by side and drift is the default outcome.
- **Glossary compliance** — the terms fixed in [glossary.md](glossary.md) render as
  agreed, allowing for inflection and agreement in the target language.
- **Consistent register per locale** — the tone read off the existing locales, applied
  the same way everywhere.
- **Proper nouns and product names left alone** where the glossary says so.
- **No source-language text sitting in a target cell.**
- **Numerals, units and currency symbols unchanged** — `20 Gems` → `20 Edelsteine`, never
  `zwanzig`.
- **Natural and compact.** Of the grammatically correct renderings, prefer the shortest
  natural one. Translate, do not paraphrase: no added connectives, hedges or
  explanations that the source does not contain.

## After AI translation

Run one extra correction cycle before QA proper: re-read the batch just produced, fix
what is obviously wrong, and only then hand the rows to `check`. It is cheaper to fix a
term inside the batch than to discover the drift three batches later, and cheaper still
than finding it after the write.

`!` issues block: fix or re-translate the named cells and re-run `check` until it is
clean. `~` issues are for judgement — read them, do not auto-"fix" them.
