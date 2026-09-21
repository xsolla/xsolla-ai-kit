# Theming a custom block

A standard block follows the site theme by construction. A custom block follows it only as far
as you wire it up — this is one of the real costs of choosing one, and the most common reason
a custom block looks bolted onto the page.

## Where the theme actually lives

There is no theme command. The theme is part of the site document, and it has **two layers**:

| Layer | Path | Patch target |
|---|---|---|
| Site | `/theme` | `type: "site"`, `id: <landingId>` |
| Page | `/pages[n].theme` | `type: "page"`, `id: <pageId>` |

**The page layer overrides the site layer at render.** Setting a brand palette on the site
theme alone leaves buttons rendering in the stock template colours.

Fields worth knowing:

| Field | What it drives |
|---|---|
| `theme.mainColors.accentColor` | The accent — buttons, highlights |
| `theme.mainColors.textColor` | Body text |
| `theme.mainColors.buttonTextColor` | Text on top of an accent-filled button |
| `theme.buttonBorderRadius` | The **global** corner radius — buttons *and* cards |
| `theme.fonts.headerH1.name` | Heading font. Fonts live under `theme.fonts`, not a top-level `fontFamily` |
| `theme.calculatedTheme` | **Derived, recalculated server-side.** Patching it is ignored — only set source fields |

Read it:

```bash
xsolla shopbuilder get-structure --slug <slug> --json     # theme is on the landing and on each page
```

Write it — targeted patches only, never a wholesale replacement of the theme object:

```bash
xsolla shopbuilder update-block --landing-id <L> --data '{"t":{"type":"site","id":"<L>","patches":[
  {"op":"replace","path":["theme","mainColors","accentColor"],"value":"rgba(53,224,255,1)"},
  {"op":"replace","path":["theme","buttonBorderRadius"],"value":10}
]}}'
```

## How to make a custom block look like it belongs

Do these in order. The first two are the ones that matter.

### 1 · Read the theme before you write the source

`get-structure` first, and take the **effective** values — the page layer where it sets one,
the site layer otherwise. Those are the numbers and colours your block should use. Writing a
block against a palette you assumed is how you get a block that clashes on every site but the
one it was demoed on.

### 2 · Expose colours as `color()` controls, defaulted to the theme

Never hardcode a brand colour in the source. Hardcoding means the block silently stops
matching the moment someone re-themes the site, and there is nothing in the editor to fix it
with.

```jsx
const accent = useControls(color('Accent', '#35e0ff'));      // default = the site's accentColor, read in step 1
const onAccent = useControls(color('Button text', '#0a0e14')); // default = buttonTextColor
```

The user can now re-theme the block from the sidebar, and it starts life matching the page.

### 3 · Match the shape language, not just the colour

`buttonBorderRadius` drives buttons *and* cards site-wide. A block with square corners on a
site set to `10` reads as a different product. Carry the value through:

```jsx
const radius = useControls(number('Corner radius', 10, { min: 0, max: 40, step: 1 }));
```

### 4 · Inherit typography rather than restating it

Inline styles are the only styling mechanism available, so prefer **not** setting
`fontFamily` at all — an unset font inherits the page's. Set one only when the design
genuinely calls for a different face, and then take the name from `theme.fonts`.

### 5 · Style the settings panel like the editor

If you write a manual `settingsCode` panel, match the editor chrome so it does not look
foreign: background `#1e2126`, border `#3a3f46`, text `#e0e3e8`. With Magic Controls and
`<AutoControls />` this is handled for you — another reason to prefer them.

## ⚠️ Open question — automatic theme inheritance

**Unverified, and do not guess at it in generated code:** whether Shop Builder injects the
theme into a custom block's rendering context — as CSS custom properties on an ancestor, or as
a hook from `@site-builder/block-utils`. If it does, steps 1–3 above have a much shorter
version, and a block could track a re-theme with no author action at all.

Nothing on this machine confirms either way. Do not invent a hook name, and do not write
`var(--…)` against a custom property you have not seen. Until it is confirmed, treat the
theme as **something you read and pass in**, per steps 1–3 — that approach works regardless of
which answer turns out to be right.

To settle it, create a throwaway block on a sandbox landing that dumps what is actually in
scope, and read it on the editor canvas in Publisher Account:

```jsx
export default function ThemeProbe() {
  const cs = getComputedStyle(document.documentElement);
  const vars = Array.from(document.styleSheets)
    .flatMap(s => { try { return Array.from(s.cssRules); } catch { return []; } })
    .flatMap(r => Array.from(r.style || []))
    .filter(p => p.startsWith('--'));
  return <pre style={{ fontSize: 11 }}>
    {Array.from(new Set(vars)).map(v => `${v}: ${cs.getPropertyValue(v)}`).join('\n')}
  </pre>;
}
```

Delete the probe block afterwards (`delete-ai-block --id <id>`). Record the answer here rather
than in a session, and drop this section when it is known.

> Note: on sandbox merchants where `enable-preview` and `preview-link` return 403, there is no
> public URL to view the probe on — the editor canvas in Publisher Account is the only place
> it can be read.
