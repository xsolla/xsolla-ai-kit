# Verify and iterate

## A clean API read is not evidence

`update-block` returns `ok: true` for patches that change nothing visible, and
`get-structure` will happily read back a palette the renderer never uses. Every trap in
this skill produces a **clean API read and a wrong page**.

So: either look at a rendered screenshot, or say plainly that you verified the structure
and *not* the appearance. Never describe a theme as "applied" on the strength of a read.

Note the batch response echoes `patches: []` for some scopes even when the write landed —
re-read the document to confirm, don't trust the echo.

## Getting a render

- `xsolla shopbuilder enable-preview --slug <slug>` then `preview-link --slug <slug>`.
  This endpoint can **403** even when every other shopbuilder command works, because it
  authenticates differently. If it does, don't conclude the site is broken — check
  whether it also 403s on a pre-existing site, which tells you it's the session, not the
  build.
- Otherwise the user opens Publisher Account → Storefronts → Websites → the site card →
  **OPEN SITE BUILDER**. Publishing to a live domain also happens there, not from the CLI.
- After structure or catalog changes, re-run `enable-preview` and hard-refresh.

Ask for a screenshot. It is the fastest instrument available and it settles arguments
that reading JSON cannot.

## Sample pixels instead of guessing

Site Builder's token names do not reliably describe what they paint, so when an element
is the wrong colour, **measure it** rather than guessing which token to patch:

```python
from PIL import Image
im = Image.open("screenshot.png").convert("RGB")
s = im.size[0] / DISPLAYED_WIDTH          # screenshots are usually downscaled
print(im.getpixel((int(x * s), int(y * s))))
```

Then invert the lookup: grep the serialized theme for that exact value and list every
token holding it.

```python
hits = []
def walk(o, p=""):
    if isinstance(o, dict):
        for k, v in o.items(): walk(v, p + "." + k)
    elif isinstance(o, list):
        for i, v in enumerate(o): walk(v, "%s[%d]" % (p, i))
    elif isinstance(o, str) and "255, 215, 106" in o:
        hits.append((p, o))
walk(theme)
```

Comparing the same pixel across successive screenshots is even stronger: a token that
went pink → gold → gold while you changed something else to purple is provably not the
one you were patching. That is how `core.text.brand` gets identified as the card buy
button.

Also crop and zoom before believing a font is wrong — a downscaled screenshot makes most
small text look serif.

## Render traps that read clean

| Symptom | Cause |
|---|---|
| Theme unchanged | patched `theme.input`, not `theme.calculatedTheme` |
| Theme unchanged on one page | the page's `theme.enabled` is `true` and overrides the site |
| Section background image missing | `background.color` is opaque and paints over `img` |
| Body copy in a serif | localized text is a bare string, not HTML |
| Text edit does nothing | block text lives in the slug's localization store, not the block |
| Localized string comes out empty | value must be `{"translation": "<html>"}`, not a bare string |
| FAQ row still visible | `enable: false` doesn't hide it — `op: "remove"` the component |
| Nav link goes nowhere | `targetId` points at a deleted block |
| Header right side empty | `user-info` renders nothing without a session — not a bug |
| Store section empty | wrong `item.type`; currency packages are `virtual_currency`, and they don't appear in `list-catalog-items-by-group` |
| Card art too large | `image.size: cover`; use `contain` (the frame stays square) |

## Don't guess undocumented enums

The backend does not validate every field. `card.layouts.<type>.image.format` accepted a
deliberate `"zzz-invalid-sentinel"` and stored it. So a successful write proves nothing
about whether a value is real, and an invalid one will confuse the renderer. Read valid
options off the GUI, or change a field you do know.

If you do probe, probe on the least important section, revert immediately, and never
leave a sentinel in the document.

## Iterating well

1. Change **one class of thing** per round, or you can't attribute the result.
2. State which changes are certain and which are hypotheses, so a screenshot that
   disproves one doesn't cast doubt on the rest.
3. When a fix is your second attempt at the same symptom, say so.
4. Keep a running list of gaps that are native limitations rather than bugs — badge
   circles, card internal order, per-section headings — so they aren't re-litigated each
   round. If the user wants one badly enough, that section becomes a custom block.
