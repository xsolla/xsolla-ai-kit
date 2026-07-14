# Login widget styling — channels, the `disallow_external_style` flag, endpoints

Context for the API-first flow in [`../SKILL.md`](../SKILL.md). Covers all four customization
channels, the flag that decides which CSS path is honored, the alternative channels, the legacy
widget, PA navigation, and the consolidated endpoint reference.

## The four channels at a glance

The widget is customized through four channels, in two groups: **theme** (structured settings —
colors, roundness, logo, background, social order) and **custom CSS** (arbitrary styling of the
widget DOM).

| # | Channel | Uses PA UI? | Controls | Needs `disallow_external_style`… |
|---|---------|-------------|----------|----------------------------------|
| 1 | PA visual editor | Yes | Theme: colors, logo, background, roundness, social order, language | No |
| 2 | Custom CSS upload via PA UI | Yes | Arbitrary CSS | Requires `true` (server-side CSS) |
| 3 | **Custom CSS via API (this skill)** | No (scripted) | Arbitrary CSS (same as #2) | Requires `true` — but server-side CSS applies regardless of the flag |
| 4 | Client-side via SDK | No | `customStyle` (CSS URL), `themeJSON`, `socialsJSON`, locale | `customStyle` needs `false`; `themeJSON`/`socialsJSON` always work |

**Quick decision:** colors/logo/roundness only, no code → Channel 1. Full CSS and you manage the
project in PA → Channel 2. **Automate CSS deployment / no PA clicking → Channel 3 (this skill).**
Styling from your own site/Site Builder in code → Channel 4 (mind the flag).

## ⚠️ The critical gotcha — `disallow_external_style`

Per project, the widget reads `visual_settings.disallow_external_style` from
`GET https://login.xsolla.com/api/projects/{id}/settings/auth`. This flag **inverts** which CSS
channel is honored:

| `disallow_external_style` | Widget loads… | Ignores… |
|---------------------------|---------------|----------|
| `true` (default) | The PA/API-uploaded `custom_style_url` (Channels 2/3), injected as `<link>` | Any SDK / Site Builder `customStyle` (Channel 4a) |
| `false` | The SDK `customStyle` URL (Channel 4a), injected inline | The uploaded `custom_style_url` |

Key facts:

- The two CSS methods are **mutually exclusive per project** — only one path delivers CSS.
- **The flag is backend-set. There is no PA UI toggle.** To switch a project from PA/API-CSS to
  SDK-CSS (or back), the Login/backend team must change it.
- **Default is `true`** — so out of the box a partner passing `customStyle` from code sees nothing
  happen. This is the #1 "API styling doesn't work" report. Because **Channel 3 (server-side
  upload) is honored under the default `true`, it is the reliable path** and needs no flag change.
- `themeJSON` and `socialsJSON` are **not** gated by this flag — they always work via the SDK.

## Channel 1 — PA visual editor (no code)

PA → **Players → Login → Configure → Customization → Widget customization → Customize**. Live
preview → **Publish**. Sets logo, base colors (text / button / page tint), scene background,
corner roundness, default language, and the country that drives social-button order. Publishing
applies to **every** app/site on this login project; hard-refresh and allow 7–10 min cache.

## Channel 2 — Custom CSS upload via PA UI

Same page → **Additional customization** block → upload `.css` → **Save changes**. Under the hood
it does exactly what Channel 3 does: uploads the file to Xsolla storage → CDN URL → saves the URL
to the project via `custom_style_url`. Use Channel 3 to script this without the PA UI.

## Channel 4 — Client-side via the SDK

If you've integrated `@xsolla/login-sdk`:

- **Custom CSS URL** — `new Widget({ projectId, customStyle: 'https://your-domain/login.css' })`.
  ⚠️ Only takes effect if `disallow_external_style` is `false`. The `customStyle` param is also
  `@deprecated` in the SDK ("use Publisher Account to upload your custom CSS") — Xsolla's
  recommended path for CSS is the upload flow (Channels 2/3).
- **Theme & socials via JSON (no flag needed)** — `themeJSON: { primary_color, rounding, … }`,
  `socialsJSON: '<url>'`, `preferredLocale`. Always works.
- **Runtime theming, no reload** — `widget.setTheme({ primary_color, text_color })` posts
  `@xsolla-login/sdk:theme-update`; colors + roundness change instantly. Background/scene/logo
  hot-swap is **not fully confirmed** — verify before promising it.
- **Site Builder** — pass config through the SB middleware:
  `window.SB.subscribe(api => api.login.setConfigMiddleware(cfg => ({ ...cfg, customStyle })))`.
  ⚠️ The logo, X, and modal frame around the widget are **Site Builder's** block, not the widget —
  style those in Site Builder. Widget CSS only styles inside the iframe. With
  `disallow_external_style: true`, the SB `customStyle` path is ignored (CSS must go via upload),
  but `themeJSON`/`socialsJSON` still work through SB.

## Social buttons — primary vs secondary, order

Primary socials = big buttons with text; secondary = small icons under the "or" line. The split &
order come from (1) the `by_region` API (`projects/{id}/settings/socials/by_region`) per geo
region, and (2) a **last-used cookie** that promotes the user's last social into primary — which
is why buttons "move around" between visits. It is **config-driven, not CSS**. To pin an order:
change the region social config (CSM/backend) or override with a self-hosted `socialsJSON` via SDK
/ Site Builder (`{ "1": { "primary": [{name, jwt, oauth2}], "secondary": [] }, … }`, keyed by
region). `forcePrimarySocial` only changes render mode; `primary_socials.amount` is not
implemented in this widget version.

## Close button — `showCloseButton`

The widget renders its `.closeButton` (X) only when `?showCloseButton=true` is passed (default
off). Custom-X pattern: `.closeButton > div { display:none }` + `.closeButton { background:
url(<customX>) }`. Empty/missing URL → blank box.

## Legacy widget (`widget_generation === 0`)

Older SDK, no live preview, CSS upload only. Different endpoint:
`PUT https://login.xsolla.com/api/projects/{loginProjectId}/widget_style` with
`{ "custom_css": "<css or null>", "update_version": <bool> }`. Legacy CSS must contain the widget
version comment (validated on upload). Global params:
`GET https://login.xsolla.com/api/widget/params` (sent with `Authorization: undefined`).

## Consolidated endpoint reference

All Login-API calls use the Publisher Account token. Base URLs: Login API
`https://login.xsolla.com/api` · Merchant API `https://api.xsolla.com` · CDN
`https://cdn.xsolla.net`.

| Purpose | Method & path | Body / returns |
|---------|---------------|----------------|
| Read auth settings (incl. `custom_style_url`, `disallow_external_style`) | `GET /projects/{id}/settings/auth` | `{ visual_settings: { custom_style_url, disallow_external_style, … } }` |
| Upload file (CSS / image / font) | `POST api.xsolla.com/merchant/current/merchants/{merchantId}/files` | multipart `file=…` → `{ file_url }` |
| Get current widget CSS URL | `GET /projects/{id}/custom_style_url` | `{ custom_style_url }` |
| Set widget CSS URL | `POST /projects/{id}/custom_style_url` | `{ custom_style_url }` |
| Legacy widget CSS (gen 0) | `GET`/`PUT /projects/{id}/widget_style` | `PUT { custom_css, update_version }` |
| Social order by region | `GET /projects/{id}/settings/socials/by_region` | region → socials |

## Publisher Account navigation

Path pattern: `/{merchantId}/projects/{mProjectId}/login/{loginProjectId}/…` — navigation hub
`/navigation`, widget customization `/customization/widget`, email `/customization/email`, SMS
`/customization/sms`. Editor entry: **Players → Login → Configure → Customization → Widget
customization → Customize**.

## Sources

- Widget customization: <https://developers.xsolla.com/authenticate-users/login/customization/widget-customization/>
- JSON with widget (theme): <https://developers.xsolla.com/authenticate-users/login/customization/connect-json-with-widget/>
- SDK on npm: <https://www.npmjs.com/package/@xsolla/login-sdk>
- Code — `login-pa-module`: `src/api/configurations/customization/index.ts`, `src/components/Customization/WidgetPreviewFrame/VisualSettings.tsx`
- Code — `login-widget-ng`: `packages/widget/src/App.tsx`, `packages/widget/src/utils/settings/utils.ts`, `packages/sdk/src/types.ts`
- Live verification: SERVICE-9991 (Second Dinner / Marvel Snap), June 2026 + code re-verification July 2026.
