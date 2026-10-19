---
name: login-styling
description: >-
  Applies a custom visual style / theme / brand to the Xsolla Login widget (Login Widget 2.0,
  `@xsolla/login-sdk`) — the sign-in, sign-up, and password-reset screens. Primary path is
  API-based: upload a CSS file to Xsolla storage, then attach its CDN URL to the login project
  so the widget injects it server-side — honored under the project's default setting, which is
  why it's the reliable path. Both calls take their bearer from the Xsolla CLI sign-in
  (`xsolla auth get-token`), so nobody pastes a token.
  Also covers structured theming (colors, logo, roundness, background, social order via themeJSON)
  and the SDK / Publisher Account alternatives. Use whenever a developer says "style the login",
  "theme the Login widget", "customize the login UI", "brand the sign-in / sign-up screen",
  "change the login colors / logo / fonts / background", "upload custom CSS for login", "deploy
  login CSS via API", "make login match my game", "white-label login", "dark-mode login",
  "restyle the Xsolla login page", or is integrating Login and needs the widget to look on-brand.
  Pairs with `login-setup` — that skill wires the auth flow; this one makes it look right.
metadata:
  owner: elnur_khalilov
  domain: login
  status: draft
---

> Owner: Elnur Khalilov (Login FE) · Last verified: July 2026 · Applies to: Login Widget 2.0
> (`login-widget-ng`) + Publisher Account Login module. This skill's **primary, recommended path
> is Channel 3 — CSS deployed via API.** The other three channels (PA editor, PA CSS upload, SDK)
> are documented in [`references/channels-and-flag.md`](references/channels-and-flag.md).

## When to use

Use this skill — always alongside [`login-setup`](../login-setup/SKILL.md) — when the Login UI
must look on-brand rather than shipping the Xsolla default:

- Deploy arbitrary **custom CSS to the Login widget via API** (no Publisher Account clicking) —
  the main flow below
- Apply the game's brand tokens (colors, logo, roundness, background, fonts) to the sign-in,
  sign-up, and password-reset screens
- White-label / dark-mode the login experience
- Choose between API CSS, Publisher Account CSS, structured `themeJSON`, and SDK `customStyle`

Out of scope: wiring the auth flow, OAuth clients, JWT validation (→
[`login-setup`](../login-setup/SKILL.md)); catalog/storefront visuals (→ `catalog-design`);
checkout/payment UI styling (→ `headless-checkout-integration`). CSS **cannot** change the
widget's layout/structure or inject HTML/JS — see [limitations](references/css-reference.md).

## Prerequisites

The agent deploys the CSS with two REST calls that have no CLI command yet, and takes their
bearer from the **Xsolla CLI** sign-in. Run these four checks. They are read-only and safe
to repeat.

```bash
xsolla --version                              # installed? which version?
xsolla config list --json                     # merchant_id / project_id
xsolla auth status --json                     # signed in, token not expired?
xsolla config get login-project-id --json     # data.value; "" means unset
```

If the CLI is missing or older than 1.9.4 (a `dev` build is acceptable), `merchant_id` is
`0` or missing, or `auth status` shows `authenticated: false`, hand off to
**`merchant-setup`** and come back when it reports. The sign-in lasts about a day and
doesn't renew itself: on `expired: true`, or a 401 from the calls below, the user runs
`xsolla auth login` again. If `login-project-id` is empty, run
[`login-setup`](../login-setup/SKILL.md) step 1 first. Never ask the user to paste a token.

- A working Login integration from [`login-setup`](../login-setup/SKILL.md) — the widget must
  render before it can be styled.
- **Signed Xsolla Product Licensing Agreement** (PA → Agreements). Widget customization (CSS
  upload / editor Save) is **disabled** until it is signed.
- **Login Widget 2.0** (`widget_generation > 0`). The legacy widget (`=== 0`) uses a different,
  limited endpoint — see [`references/channels-and-flag.md`](references/channels-and-flag.md).
- **Xsolla MCP (recommended).** These are the exact endpoints the PA frontend itself calls;
  they are reliable but not a formally published public API. Verify current shapes with
  `search_xsolla_sources` (or the linked docs) before handing them to a partner as official.

**Bearer for the REST calls.** Read it from the CLI inside the command that sends the
request, and pass it only to that process:
`TOKEN=$(xsolla auth get-token) python3 -I <script> …`, where the script reads `TOKEN`
from its environment and prints only the status and the response fields it needs. Never
print the token, write it to a file or `.env`, or export it into the shell.

## Steps (API-based CSS — Channel 3)

1. **Author the CSS against stable selectors.** Target the widget's **BEM** class names
   (`.app-block`, `.button-element`, `.input-container input`, `.tabs-links__login_tab-link`, …)
   — **never** the hashed `css-XXXX` Emotion classes (they change every build). Load fonts with
   `@font-face`, **never** `@import` (the sanitizer strips it). Save as **plain-text `.css`**
   (macOS TextEdit saves RTF by default → upload 422s). Full selector list, sanitizer rules,
   fonts, and worked examples: [`references/css-reference.md`](references/css-reference.md).

2. **Upload the CSS file to Xsolla storage (Merchant API, CLI gap).** Show the user the file
   and get a yes, then `POST` it as `multipart/form-data` with the form field literally
   named `file`:

   | | |
   |---|---|
   | Method & path | `POST https://api.xsolla.com/merchant/current/merchants/{merchant_id}/files` |
   | Auth | `Authorization: Bearer <xsolla auth get-token>` |
   | Body | `multipart/form-data`, field `file=@styles.css` |
   | Returns | `{ "file_url": "https://cdn.xsolla.net/.../styles.css" }` |

   `merchant_id` comes from `xsolla config get merchant-id --json`. Upload `@font-face`
   files and images the same way and reference their `file_url`s from the CSS.

3. **Attach the returned URL to the login project (Login API, CLI gap).** This restyles
   every app on the Login project, so confirm before sending it.

   | | |
   |---|---|
   | Method & path | `POST https://login.xsolla.com/api/projects/{login_project_id}/custom_style_url` |
   | Auth | `Authorization: Bearer <xsolla auth get-token>` |
   | Body | `{ "custom_style_url": "<file_url from step 2>" }` |

   Server-side CSS attached this way is injected as a `<link rel="stylesheet">` and **is honored
   under the default `disallow_external_style: true`** — which is why API deployment is the
   reliable path. (If a project has been flipped to `false`, the SDK `customStyle` param wins and
   this uploaded CSS is ignored instead — see [`references/channels-and-flag.md`](references/channels-and-flag.md).)

4. **Verify and refresh.** `GET https://login.xsolla.com/api/projects/{login_project_id}/custom_style_url`
   (same bearer) → confirm it returns your CDN URL. `GET …/projects/{login_project_id}/settings/auth`
   → `visual_settings.disallow_external_style` should be `true`. Then hard-refresh the widget
   (Ctrl/Cmd+F5) and allow **7–10 min** for CDN cache. The CSS applies to **every** app/site
   using this login project.

5. **(Optional) structured theme instead of / alongside CSS.** For plain colors, logo, roundness,
   background, or social order — no CSS file needed — pass `themeJSON` via the SDK; it is never
   gated by the flag. Keys and defaults: [`references/css-reference.md`](references/css-reference.md).

## CLI gaps

No `xsolla` command covers widget styling yet. The two writes above are the named REST
steps; surface the rest to the user.

| Need | Status | Do instead |
|---|---|---|
| Upload a CSS, font or image file to Xsolla storage | No command (`shopbuilder upload-asset` serves Shop Builder landings only, and takes no CSS) | Step 2, bearer from `xsolla auth get-token` |
| Read or set the Login `custom_style_url` | No command | Steps 3–4, same bearer |
| Read `disallow_external_style` | No command | Step 4 `GET …/settings/auth`, same bearer |
| Change `disallow_external_style` | No API and no PA toggle | Ask the Xsolla account manager (Login backend team) |
| Visual-editor theme (logo, colors, roundness) | No command | PA editor (Channel 1) or SDK `themeJSON` |

If step 2 or 3 returns 401/403 while `auth status` is fine, the CLI sign-in lacks that
permission on this merchant. Don't try another credential: upload through Publisher Account
instead (Channel 2 in [`references/channels-and-flag.md`](references/channels-and-flag.md)).

## Common pitfalls

- **"We pass `customStyle` in code but nothing changes."** That is the SDK path (Channel 4),
  gated by `disallow_external_style` (default `true` → SDK CSS ignored). **Use this skill's API
  upload instead** — it's the path honored under the default `true`. Full flag explainer:
  [`references/channels-and-flag.md`](references/channels-and-flag.md).
- **Upload returns 422.** File isn't plain-text `.css` (macOS RTF) or its MIME isn't allowed.
  Re-save as plain text; confirm it doesn't report "Rich Text Format".
- **Custom font doesn't load.** It was loaded via `@import` (stripped by the sanitizer). Switch
  to `@font-face { src: url(...) }`. JSON is rejected by the uploader, so self-host `socialsJSON`.
- **Widget renders all black.** An invalid hex in the theme — the merge silently replaces bad
  colors with `#000000`. Check theme values.
- **Targeted the hashed `css-XXXX` class → styles break next build.** Use the BEM selectors only.
- **Expecting a pixel-perfect custom layout.** CSS can only reskin what's rendered; it cannot
  reorder/add/remove DOM, inject HTML, or run JS. On Site Builder, the surrounding modal / logo /
  X belong to Site Builder, not the widget iframe.

## Agent test

Prompt: "I've integrated Xsolla Login. Restyle the login widget via API to match my game — brand
color #FF6600, rounded buttons, my custom font, and my logo — without me clicking around in
Publisher Account."

Expected: the agent loads this skill (+ references) alongside `login-setup`, writes a plain-text
`.css` targeting BEM selectors with `@font-face` (not `@import`), uploads it via the Merchant API
`/files` endpoint, attaches the returned CDN URL via the Login API `custom_style_url` endpoint,
verifies with the `GET`, and explains the 7–10 min cache + all-apps scope. It does **not** rely on
the SDK `customStyle` param (would be blocked by `disallow_external_style: true`).
⏳ Endpoints verified July 2026 (SERVICE-9991); pending a live sandbox run in this repo.
