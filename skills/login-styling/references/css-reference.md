# Login widget — CSS authoring reference

How to write the CSS you deploy in [`../SKILL.md`](../SKILL.md) step 1: file rules, the
sanitizer's behavior, fonts, the stable BEM selectors, the structured `themeJSON` object,
limitations, and worked examples.

## File rules & the sanitizer

When you upload CSS (Channel 3 / Channel 2), Xsolla runs it through a sanitizer and a MIME check.
Verified behavior:

- **`@import url(...)` is stripped/emptied** → do **not** load fonts via `@import`. Use
  `@font-face` (below).
- **`background: url(...)` is preserved** — including proxied / `@webp` URLs, query strings, and
  inside nested `@media`.
- **`data:image/svg+xml`** — the wrapper is kept but inner SVG URLs are stripped.
- **MIME allowlist** (Merchant uploader): `image/*`, `font/*`, `text/css`, `text/csv`,
  `application/x-font-*`, `application/octet-stream`, `video/webm|mp4|quicktime`, `text/plain`.
  **JSON is rejected** → you cannot host `socialsJSON` on Xsolla's CDN; self-host it.
- File must be **plain-text `.css`**. ⚠️ macOS TextEdit saves `.css` as **RTF** by default →
  upload fails with **422**. Confirm the file does not report "Rich Text Format".

## Fonts — use `@font-face`, never `@import`

```css
@font-face {
  font-family: 'Chakra Petch';
  font-weight: 400;
  font-display: swap;
  src: url('https://your-cdn/Chakra-Petch-Regular.woff2') format('woff2');
}
body, .app-block { font-family: 'Chakra Petch', sans-serif; }
```

## Stable CSS selectors (BEM — verified in live DOM)

Target these BEM class names. **Never** target the hashed `css-XXXX` Emotion classes next to them
— those change between builds.

| Selector | Element |
|----------|---------|
| `.app-block` | Widget card |
| `.app_out-style` | Custom-CSS wrapper |
| `.button-element` | Submit button |
| `.login-page`, `.login-page_body` | Login page wrappers |
| `.page-title_wrapper`, `.{pageName}_page-title` | Page titles |
| `.tabs-links`, `.tabs-links__login_tab-link`, `.tabs-links__signUp_tab-link` | Login / Sign-up tabs |
| `.input-container`, `.input-container input` | Input field box / text input |
| `.input-password_input-element` | Password input |
| `.input_title`, `.universal-input_title` | Field labels |
| `.primary-social_button`, `.primary-social__google` | Big social buttons |
| `.secondary-social_buttons`, `.secondary-social`, `.secondary-social__<name>` | Small icon socials |
| `.or-line__wrapper` | The "or" divider |
| `.widget-header_logotype` | Header logo |
| `.closeButton` | Close (X) button |

Xsolla docs examples also reference `#mainBody`, `form`, `.universal-input`, and
`button[data-testid="login-form__button-submit"]`.

## Structured theme reference (`themeJSON`)

Structured theme object — also what the PA editor writes and what `setTheme()` accepts. Colors
accept HEX or RGB. Not gated by `disallow_external_style`; pass via the SDK for CSS-free theming.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `primary_color` | string | `#0073F7` | Buttons, active input borders, links, active tab |
| `secondary_color` | string | `#DADADA` | Inactive input borders |
| `text_color` | string | `#000000` | Main text, social logos on secondary buttons |
| `error_color` | string | `#EB002F` | Error text |
| `background` | object | — | Widget background: `{ color, image: { url, opacity } }` |
| `scene` | object | — | Area around the widget: `{ color, image: { url, size } }` (`size` = CSS `background-size`, default `cover`) |
| `rounding` | object | — | Corner radius: `{ inputs, buttons, widget }` |
| `header` | object | — | Header / logo: `{ image: { url } }` |
| `tabs` | object | — | Show / hide login & sign-up tabs |
| `primary_socials` / `secondary_socials` | object | — | Social display settings |

```json
{
  "primary_color": "#708090",
  "secondary_color": "#4682B4",
  "text_color": "#FFFFFF",
  "rounding": { "buttons": 8, "inputs": 8, "widget": 16 },
  "background": { "color": "#1B1B1B" },
  "scene": { "image": { "url": "https://your-cdn/bg.jpg", "size": "cover" } }
}
```

Full reference: <https://developers.xsolla.com/authenticate-users/login/customization/connect-json-with-widget/>

## Limitations — what CSS can and can't do

- ✅ **Reskin existing elements:** colors, fonts, spacing, borders, radius, backgrounds,
  show/hide elements.
- ❌ **Cannot change layout or structure** — the widget is a fixed-layout iframe. You cannot
  add / remove / reorder DOM nodes, inject arbitrary HTML, change the flow/order of fields and
  buttons, or run JavaScript inside the widget. CSS only restyles what is already rendered.
- The result gets close to a custom design but is **never pixel-identical** to an arbitrary mockup.
- Style **only inside the iframe**. On a Site Builder site, the surrounding modal / frame / logo /
  X belong to Site Builder, not the widget.
- Theme changes and CSS apply to **all** apps/sites using that login project.

## Worked examples

Full SDK init (own site — theme + CSS + locale). Note `customStyle` needs
`disallow_external_style: false`; the API-upload path in the SKILL works under the default `true`:

```js
import { Widget } from '@xsolla/login-sdk';
const widget = new Widget({
  projectId: '2f1ba87f-9791-4043-843b-af82d47dc73f',
  themeJSON: {
    primary_color: '#FF6600',
    text_color: '#FFFFFF',
    rounding: { buttons: 8, inputs: 8, widget: 16 },
  },
  customStyle: 'https://your-cdn/login.css', // needs disallow_external_style:false
  preferredLocale: 'en_XX',
});
widget.mount('login-container');
```

Example CSS file (`login.css`) — deploy this via the SKILL's API upload flow:

```css
@font-face {
  font-family: 'Chakra Petch';
  font-weight: 400;
  src: url('https://your-cdn/Chakra-Petch-Regular.woff2') format('woff2');
}
.app-block { font-family: 'Chakra Petch', sans-serif; }
.button-element {
  background: #FF6600;
  border-radius: 8px;
}
.input-container input { border-color: #CCC; }
.tabs-links__login_tab-link { font-weight: 700; }
```

## Troubleshooting / FAQ

| Symptom | Likely cause / fix |
|---------|--------------------|
| "We pass `customStyle` in code but nothing changes" | `disallow_external_style: true` (default) — SDK param ignored. Use API/PA upload, or ask the Login team to set the flag `false`. |
| CSS upload returns 422 | File isn't plain-text `.css` (macOS RTF), or MIME not allowed. Re-save as plain text. |
| Custom font doesn't load | Loaded via `@import` (stripped). Switch to `@font-face { src: url(...) }`. |
| Widget renders all black | Invalid hex in theme — the merge silently replaces bad colors with `#000000`. |
| Styles don't update after publish | Cache — hard-refresh (Ctrl/Cmd+F5); allow 7–10 min. |
| Social buttons keep reordering | Last-used cookie promotes the last social to primary; config-driven, not CSS. Pin with `socialsJSON`. |
| Logo / X / frame won't style with widget CSS | Those are Site Builder's modal, not the widget. Style in Site Builder. |
