# Voidwall Web Shop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a themed, localized headless web shop for *Voidwall* in `examples/voidwall-shop/`, backed by a seeded Xsolla sandbox catalog in project `316665`.

**Architecture:** A one-off idempotent seed script writes the catalog through the Admin API (key stays server-side). A Vite + React + TS SPA reads the public Store API from the browser, keeps a guest cart (`x-unauthorized-id`), logs in through the Xsolla Login widget (OAuth 2.0 public client), and pays through the Headless Checkout SDK. A small Express handler in `server/` verifies webhook signatures and grants idempotently.

**Tech Stack:** Vite, React 18, TypeScript (strict), Vitest, tsx, Express, `@xsolla/pay-station-sdk`, `@xsolla/login-sdk`.

**Spec:** `docs/superpowers/specs/2026-10-01-voidwall-shop-design.md`

**Source content:** `~/Downloads/voidwall/CONTEXT.md` and `~/Downloads/voidwall/assets/`. Domain skill contracts: `skills/catalog-design`, `skills/login-setup`, `skills/headless-checkout-integration`, `skills/webhooks-impl`.

## Global Constraints

- Merchant `940463`, project `316665`, sandbox only (`sandbox: true` everywhere). Never set `sandbox: false`.
- No commits or pushes. This plan has no commit steps on purpose; commit only if the user asks.
- Edit nothing under `skills/` or `.cursor/skills/`. All new code lives under `examples/voidwall-shop/`.
- The 27 existing `quest_*` items and `qp_fire_sword_1` in project 316665 are never modified or deleted. The seed script only touches SKUs it defines and never lists-and-deletes.
- API key (`XSOLLA_PROJECT_API_KEY`) is read only by `scripts/` and `server/`. It must never appear in `src/`, `dist/`, logs, or error messages. Read `.env` as text, never print values.
- Locales, exactly: `en`, `fr`, `de`, `ja`, `pt-BR`. Default `en`.
- Currencies on every real-money SKU, identical set and USD default: `USD`, `EUR`, `GBP`, `BRL`, `JPY`.
- Palette: void black `#0A0E14`, hull steel `#2A3242`, cyan `#35E0FF`, plasma white `#EAF6FF`, warning amber `#FFA63D`, rime violet `#8B6CFF`. Rarity rims: common gray, rare blue, epic purple (`#8B6CFF`), legendary amber (`#FFA63D`).
- Webhook signature: `lowercase(sha1(rawBody + secret))`, constant-time compare, plain SHA-1 (not HMAC). Bad signature returns `400` with `INVALID_SIGNATURE`.
- Headless Checkout: always pass `settings.language` on the token and `language` in `headlessCheckout.init`, both from the current shop locale (fallback `en`).
- Catalog endpoints are called from the browser without a `country` parameter. Admin API is never used by the storefront.
- Admin updates replace state: the seed payload is the full desired state for each entity.
- Copy: no em dash character anywhere in code, comments, or UI strings.

## Known gaps (decided up front, reported again at the end)

1. **Warden's Charter (subscription)** needs the Subscriptions API, which no skill in this repo documents. Out of this plan. The storefront renders a "Coming soon" card for it. Ask the user if they want it added.
2. **Founder's Pack** drops the "30 days Warden's Charter" line item for the same reason.
3. **Warden's Arsenal** is priced in USD ($29.99), not 4,000 Cores, because the bundle Admin endpoint silently drops `vc_prices` (earlier friction log). CONTEXT.md also says the individual value is 4,700 Cores, but its four skins sum to 3,900 (1,500 + 800 + 800 + 800). The shop shows 3,900.
4. **Plank Owner title** has no price or image in CONTEXT.md. It is created hidden (`is_show_in_store: false`) with an assumed 1,500 Cores price, bundle-only.
5. **`pack_reactor.jpg` is missing.** The Core Reactor pack uses `currency/cores_svg.jpg`.
6. **Frontier Pass and Founder's Pack** are windowed 2026-10-14 to 2027-01-13 and are hidden by the API until then. Today is 2026-10-01.
7. **Localized copy beyond the Obsidian worked example is machine-drafted** (names are mostly proper nouns kept as-is, descriptions come from templates). Flag for human review.
8. **Login and checkout are only verifiable with a Login project** linked to 316665 (`VITE_LOGIN_PROJECT_ID`, `VITE_LOGIN_CLIENT_ID`) and `http://localhost:5173/auth/callback` in its callback URLs. Without them the Login button renders disabled and those paths are reported as unverified.

## Review Focus

Failure modes the spec implies but no happy-path test would hit. Each has a test in the owning task.

1. **Foreign SKUs in the project.** Project 316665 holds 27 unrelated quest items that the public catalog returns. The storefront must render only known Voidwall SKUs. (Task 3, `knownItems` test)
2. **Empty or hidden groups.** Windowed items are hidden, so "Passes and Subscriptions" can be empty. The grid must hide empty sections, not crash or show a blank header. (Task 3, `byGroup`/`visibleGroups` test)
3. **Price is `null`.** A misconfigured item returns `price: null`. The card must show "unavailable" and disable buying, not render `NaN` or `$undefined`. (Task 3, `formatMoney` test)
4. **Bad stored locale.** `localStorage` may hold a stale or hand-edited locale. It must fall back to `en`. (Task 3, `resolveLocale` test)
5. **Guest cart merge failure midway.** If adding a guest line to the account cart fails, the guest cart must not be cleared (no lost items), and a retry must not double quantities beyond what was already merged. (Task 5, merge failure test)

## File Structure

```
examples/voidwall-shop/
  package.json, tsconfig.json, vite.config.ts, index.html, .gitignore, .env.example, CONTRACTS.md
  catalog/
    types.ts            locale/currency/def types
    catalog.ts          all catalog definitions + IMAGES + coresValue()
    copy.ts             localized names/descriptions (templates + overrides)
    regional.ts         regional price tiers
    payloads.ts         def -> Admin API body builders
    plan.ts             ordered seed plan
  scripts/
    seed-catalog.ts     CLI: dry-run (default), --apply, --verify
    lib/env.ts          .env text loader (never prints values)
    lib/admin.ts        Admin API client + upsert
  src/
    config.ts           VITE_* config
    main.tsx, App.tsx, theme.css
    i18n/locales.ts     locale lists + code maps + resolveLocale
    i18n/ui.ts          UI strings x 5 locales
    api/store.ts        public Store API client + normalizers + formatMoney
    api/view.ts         knownItems, byGroup, visibleGroups
    auth/types.ts, session.ts, oauth.ts, AuthContext.tsx
    cart/headers.ts, cartApi.ts, merge.ts, useCart.ts
    checkout/api.ts     payment token, buy with Cores, balance
    checkout/sdk.ts     Headless Checkout wiring (DOM)
    checkout/CheckoutModal.tsx
    pages/PaymentReturn.tsx
    components/         Header, Hero, ItemCard, Section, BundleStrip, CartDrawer, Footer
    types/psdk.d.ts     custom element typings
  public/assets/        copied from ~/Downloads/voidwall/assets
  server/
    signature.ts, handler.ts, stores.ts, index.ts
  tests/                *.test.ts (Vitest, node env)
```

---

### Task 0: Scaffold and contract checks

**Files:**
- Create: `examples/voidwall-shop/package.json`, `tsconfig.json`, `vite.config.ts`, `index.html`, `.gitignore`, `.env.example`, `CONTRACTS.md`, `tests/smoke.test.ts`
- Create dir: `examples/voidwall-shop/public/assets/` (copied)

**Interfaces:**
- Produces: a working `npm test`, `npm run build`, and a `CONTRACTS.md` recording verified API facts later tasks rely on.

- [ ] **Step 1: Create the project and install dependencies**

Run from the repo root:

```bash
mkdir -p examples/voidwall-shop && cd examples/voidwall-shop
cat > package.json <<'EOF'
{
  "name": "voidwall-shop",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc --noEmit && vite build",
    "test": "vitest run",
    "seed": "tsx scripts/seed-catalog.ts",
    "webhook": "tsx server/index.ts"
  }
}
EOF
npm install react react-dom @xsolla/pay-station-sdk @xsolla/login-sdk express
npm install -D vite @vitejs/plugin-react typescript vitest tsx @types/react @types/react-dom @types/node @types/express
```

Expected: install completes; `@xsolla/pay-station-sdk` and `@xsolla/login-sdk` appear in `package.json` dependencies.

- [ ] **Step 2: Write config files**

`tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noUncheckedIndexedAccess": false,
    "skipLibCheck": true,
    "resolveJsonModule": true,
    "types": ["vite/client", "node"]
  },
  "include": ["src", "catalog", "scripts", "server", "tests", "vite.config.ts"]
}
```

`vite.config.ts`:

```ts
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: { environment: 'node', include: ['tests/**/*.test.ts'] },
});
```

`index.html`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Voidwall Store</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

`.gitignore`:

```
node_modules
dist
.env
server/data
```

`.env.example`:

```
# Browser-safe values only. The API key never goes here.
VITE_XSOLLA_PROJECT_ID=316665
VITE_SANDBOX=true
# Needed for login. Leave empty to render the Login button disabled.
VITE_LOGIN_PROJECT_ID=
VITE_LOGIN_CLIENT_ID=
```

- [ ] **Step 3: Create `.env` for the browser without printing values**

```bash
cd examples/voidwall-shop
grep -E '^XSOLLA_PROJECT_ID=' ../../.env | sed 's/^XSOLLA_PROJECT_ID/VITE_XSOLLA_PROJECT_ID/' > .env
echo 'VITE_SANDBOX=true' >> .env
sed -E 's/=.*/=<set>/' .env
```

Expected output: `VITE_XSOLLA_PROJECT_ID=<set>` and `VITE_SANDBOX=<set>`.

- [ ] **Step 4: Copy assets**

```bash
cd examples/voidwall-shop
mkdir -p public && cp -R ~/Downloads/voidwall/assets public/assets
ls public/assets
```

Expected: `boosters bundles currency gear passes skins brand`.

- [ ] **Step 5: Write a smoke test and run the toolchain**

`tests/smoke.test.ts`:

```ts
import { expect, test } from 'vitest';

test('toolchain runs', () => {
  expect(1 + 1).toBe(2);
});
```

Run: `npm test`
Expected: 1 test passed.

- [ ] **Step 6: Verify Admin auth with a read-only call (no values printed)**

```bash
cd examples/voidwall-shop
set -a; . ../../.env; set +a
curl -s -o /dev/null -w '%{http_code}\n' -u "${XSOLLA_MERCHANT_ID}:${XSOLLA_PROJECT_API_KEY}" \
  "https://store.xsolla.com/api/v2/project/${XSOLLA_PROJECT_ID}/admin/items/virtual_items?limit=1"
```

Expected: `200`. If `401`, retry with `-u "${XSOLLA_PROJECT_ID}:${XSOLLA_PROJECT_API_KEY}"`; if that works, record it in `CONTRACTS.md` and use it in Task 4's `createAdmin`. If both fail, stop and tell the user the key lacks Admin access.

- [ ] **Step 7: Verify the remaining contracts against live docs and record them**

Use the Xsolla docs MCP (`search_xsolla_sources`; authenticate via `mcp__xsolla-docs__authenticate` if needed) or fetch the pages named below. Write the answers to `CONTRACTS.md` as a table `Question | Answer | Source`:

1. Payment UI language code for Brazilian Portuguese (`pt` or `pt-BR`): https://developers.xsolla.com/payment-ui-and-flow/payment-ui/localization/index.md. Drives `PAY_LANGUAGE['pt-BR']` in Task 3.
2. Does `POST /v2/project/{id}/payment/cart/{cart_id}` accept a `promo_code` body field? Drives whether Task 6 keeps the promo field. If not, Task 6 omits `PromoField` and the checkout token call omits `promo_code`.
3. Store API `locale` query value for Brazilian Portuguese (`pt_BR` or `pt`). Drives `STORE_LOCALE['pt-BR']`.
4. Admin localization object key for Brazilian Portuguese (`pt-BR` or `pt`). Drives `localized()` in Task 1.
5. Bundle create required fields (is `type` required?) and the `limits.per_user` / `recurrent_schedule` shape. Drives `payloads.ts` in Task 2.

Expected: `CONTRACTS.md` has five filled rows. Do not guess: if a source cannot be reached, write "unverified" and keep the default noted in the task.

- [ ] **Step 8: Verify the build toolchain**

Create a placeholder `src/main.tsx` containing `export {};`, then run `npm run build`.
Expected: type-check passes and `vite build` completes (the placeholder is replaced in Task 6).

---

### Task 1: Catalog data, copy, regional prices

**Files:**
- Create: `catalog/types.ts`, `catalog/catalog.ts`, `catalog/copy.ts`, `catalog/regional.ts`
- Test: `tests/catalog.test.ts`, `tests/regional.test.ts`, `tests/copy.test.ts`

**Interfaces:**
- Produces (used by Tasks 2, 3, 6):
  - `LOCALES`, `Locale`, `CURRENCIES`, `Currency`, `Rarity`, `GroupId`, `L10n = Record<Locale,string>`
  - `GROUPS: GroupDef[]`, `PACKS: PackDef[]`, `SKINS: SkinDef[]`, `GEAR: GearDef[]`, `BOOSTERS: BoosterDef[]`, `BUNDLES: BundleDef[]`, `PASS: PassDef`
  - `CORES_SKU = 'cores'`, `SCRAP_SKU = 'scrap'`, `IMAGES: Record<string,string>`, `coresValue(b: BundleDef): number`, `CHARTER` (display-only def)
  - `regionalPrice(sku, usd, currency): number`, `pricesFor(sku, usd)`
  - `nameFor(sku, enName, locale)`, `descFor(sku, kind, vars, locale)`

- [ ] **Step 1: Write the failing tests**

`tests/catalog.test.ts`:

```ts
import { existsSync } from 'node:fs';
import { describe, expect, test } from 'vitest';
import {
  BOOSTERS, BUNDLES, GEAR, GROUPS, IMAGES, PACKS, PASS, SKINS, coresValue,
} from '../catalog/catalog';

describe('catalog definitions', () => {
  test('counts match CONTEXT.md (+ hidden title)', () => {
    expect(GROUPS).toHaveLength(6);
    expect(PACKS).toHaveLength(5);
    expect(SKINS).toHaveLength(11);
    expect(GEAR).toHaveLength(5);
    expect(BOOSTERS).toHaveLength(3);
    expect(BUNDLES).toHaveLength(4);
    expect(PASS.sku).toBe('pass_s1_frontier');
  });

  test('SKUs are unique and valid', () => {
    const skus = [
      ...PACKS, ...SKINS, ...GEAR, ...BOOSTERS, ...BUNDLES, PASS,
    ].map((d) => d.sku);
    expect(new Set(skus).size).toBe(skus.length);
    for (const s of skus) expect(s).toMatch(/^[A-Za-z0-9._-]{1,255}$/);
  });

  test('every image resolves to a file in public/assets', () => {
    for (const [sku, rel] of Object.entries(IMAGES)) {
      expect(existsSync(`public/assets/${rel}`), `${sku} -> ${rel}`).toBe(true);
    }
  });

  test('bundle contents reference known SKUs or cores', () => {
    const known = new Set([
      'cores', ...SKINS.map((s) => s.sku), ...GEAR.map((g) => g.sku), ...BOOSTERS.map((b) => b.sku),
    ]);
    for (const b of BUNDLES) for (const c of b.contents) expect(known.has(c.sku), `${b.sku}:${c.sku}`).toBe(true);
  });

  test('Warden\'s Arsenal individual value is 3900 Cores, not the 4700 in CONTEXT.md', () => {
    const arsenal = BUNDLES.find((b) => b.sku === 'bundle_wardens_arsenal')!;
    expect(coresValue(arsenal)).toBe(3900);
  });

  test('pack totals', () => {
    const totals = Object.fromEntries(PACKS.map((p) => [p.sku, p.base + p.bonus]));
    expect(totals).toEqual({
      cores_500: 500, cores_1200: 1200, cores_2600: 2600, cores_7000: 7000, cores_15000: 15000,
    });
  });
});
```

`tests/regional.test.ts`:

```ts
import { expect, test } from 'vitest';
import { CURRENCIES } from '../catalog/types';
import { pricesFor, regionalPrice } from '../catalog/regional';

test('Core Stack matches the worked example in CONTEXT.md', () => {
  expect(regionalPrice('cores_1200', 9.99, 'USD')).toBe(9.99);
  expect(regionalPrice('cores_1200', 9.99, 'EUR')).toBe(9.99);
  expect(regionalPrice('cores_1200', 9.99, 'GBP')).toBe(8.99);
  expect(regionalPrice('cores_1200', 9.99, 'BRL')).toBe(49.9);
  expect(regionalPrice('cores_1200', 9.99, 'JPY')).toBe(1500);
});

test('other tiers use multipliers; JPY rounds to 10', () => {
  expect(regionalPrice('cores_500', 4.99, 'GBP')).toBe(4.49);
  expect(regionalPrice('cores_500', 4.99, 'JPY')).toBe(750);
});

test('pricesFor returns the full currency set with USD default', () => {
  const p = pricesFor('cores_500', 4.99);
  expect(p.map((x) => x.currency)).toEqual(CURRENCIES);
  expect(p.filter((x) => x.is_default).map((x) => x.currency)).toEqual(['USD']);
});
```

`tests/copy.test.ts`:

```ts
import { expect, test } from 'vitest';
import { LOCALES } from '../catalog/types';
import { descFor, nameFor } from '../catalog/copy';

test('Obsidian worked example from CONTEXT.md', () => {
  expect(nameFor('spitter_skin_obsidian', 'Obsidian', 'fr')).toBe('Obsidienne');
  expect(nameFor('spitter_skin_obsidian', 'Obsidian', 'ja')).toBe('オブシディアン');
  expect(nameFor('spitter_skin_obsidian', 'Obsidian', 'pt-BR')).toBe('Obsidiana');
  expect(descFor('spitter_skin_obsidian', 'skin', { rarity: 'Rare', cls: 'Spitter' }, 'en'))
    .toBe('A matte-black Spitter chassis cut from salvaged Well plating.');
});

test('every kind has non-empty copy in all five locales and no em dash', () => {
  const kinds = ['skin', 'armor', 'emote', 'decal', 'title', 'booster', 'pack', 'bundle', 'pass', 'cores', 'scrap'] as const;
  for (const kind of kinds) {
    for (const l of LOCALES) {
      const text = descFor('x', kind, {
        rarity: 'Rare', cls: 'Lancer', effect: 'salvage', duration: '24h', total: 1200, bonus: 100, list: 'A, B',
      }, l);
      expect(text.length, `${kind}/${l}`).toBeGreaterThan(5);
      expect(text).not.toContain('—');
    }
  }
});
```

- [ ] **Step 2: Run to verify they fail**

Run: `npm test`
Expected: FAIL, modules `../catalog/catalog`, `../catalog/regional`, `../catalog/copy` not found.

- [ ] **Step 3: Write `catalog/types.ts`**

```ts
export const LOCALES = ['en', 'fr', 'de', 'ja', 'pt-BR'] as const;
export type Locale = (typeof LOCALES)[number];
export type L10n = Record<Locale, string>;

export const CURRENCIES = ['USD', 'EUR', 'GBP', 'BRL', 'JPY'] as const;
export type Currency = (typeof CURRENCIES)[number];

export type Rarity = 'Common' | 'Rare' | 'Epic' | 'Legendary';
export type TurretClass = 'Spitter' | 'Arclight' | 'Bulwark' | 'Hailstorm' | 'Lancer' | 'Tether';
export type GroupId = 'currency' | 'turret_skins' | 'warden_gear' | 'boosters' | 'bundles' | 'passes';

export interface Window { from: string; until: string }

export interface GroupDef { id: GroupId; order: number; names: L10n }
export interface PackDef { sku: string; name: string; base: number; bonus: number; usd: number; image: string }
export interface SkinDef { sku: string; name: string; turretClass: TurretClass; rarity: Rarity; cores: number }
export interface GearDef {
  sku: string; name: string; kind: 'armor' | 'emote' | 'decal' | 'title'; rarity: Rarity; cores: number;
  hidden?: boolean;
}
export interface BoosterDef {
  sku: string; name: string; effect: 'salvage' | 'xp'; duration: '24h' | '7d'; cores: number; dailyLimit?: number;
}
export interface BundleDef {
  sku: string; name: string; usd: number; contents: { sku: string; quantity: number }[];
  image: string; limitPerUser?: number; window?: Window;
}
export interface PassDef { sku: string; name: string; usd: number; window: Window; image: string }
```

- [ ] **Step 4: Write `catalog/catalog.ts`**

```ts
import type {
  BoosterDef, BundleDef, GearDef, GroupDef, PackDef, PassDef, SkinDef,
} from './types';

export const CORES_SKU = 'cores';
export const SCRAP_SKU = 'scrap';
export const SEASON_ONE = { from: '2026-10-14T00:00:00+00:00', until: '2027-01-13T23:59:59+00:00' };

export const GROUPS: GroupDef[] = [
  { id: 'currency', order: 1, names: { en: 'Currency', fr: 'Monnaie', de: 'Währung', ja: '通貨', 'pt-BR': 'Moeda' } },
  { id: 'turret_skins', order: 2, names: { en: 'Turret Skins', fr: 'Skins de tourelle', de: 'Geschützskins', ja: 'タレットスキン', 'pt-BR': 'Skins de torre' } },
  { id: 'warden_gear', order: 3, names: { en: 'Warden Gear', fr: 'Équipement de Gardien', de: 'Wächter-Ausrüstung', ja: 'ウォーデンギア', 'pt-BR': 'Equipamento de Guardião' } },
  { id: 'boosters', order: 4, names: { en: 'Boosters', fr: 'Boosters', de: 'Booster', ja: 'ブースター', 'pt-BR': 'Boosters' } },
  { id: 'bundles', order: 5, names: { en: 'Bundles', fr: 'Packs', de: 'Bundles', ja: 'バンドル', 'pt-BR': 'Pacotes' } },
  { id: 'passes', order: 6, names: { en: 'Passes and Subscriptions', fr: 'Passes et abonnements', de: 'Pässe und Abos', ja: 'パスとサブスクリプション', 'pt-BR': 'Passes e assinaturas' } },
];

export const PACKS: PackDef[] = [
  { sku: 'cores_500', name: 'Core Cache', base: 500, bonus: 0, usd: 4.99, image: 'currency/pack_cache.jpg' },
  { sku: 'cores_1200', name: 'Core Stack', base: 1100, bonus: 100, usd: 9.99, image: 'currency/pack_stack.jpg' },
  { sku: 'cores_2600', name: 'Core Crate', base: 2300, bonus: 300, usd: 19.99, image: 'currency/pack_crate.jpg' },
  { sku: 'cores_7000', name: 'Core Vault', base: 5800, bonus: 1200, usd: 49.99, image: 'currency/pack_vault.jpg' },
  // pack_reactor.jpg does not exist in the asset pack; reuse the generated core icon (known gap 5).
  { sku: 'cores_15000', name: 'Core Reactor', base: 11500, bonus: 3500, usd: 99.99, image: 'currency/cores_svg.jpg' },
];

export const SKINS: SkinDef[] = [
  { sku: 'spitter_skin_obsidian', name: 'Obsidian', turretClass: 'Spitter', rarity: 'Rare', cores: 800 },
  { sku: 'spitter_skin_huntsman', name: 'Huntsman', turretClass: 'Spitter', rarity: 'Epic', cores: 1500 },
  { sku: 'arclight_skin_voltaic', name: 'Voltaic', turretClass: 'Arclight', rarity: 'Rare', cores: 800 },
  { sku: 'arclight_skin_solarflare', name: 'Solar Flare', turretClass: 'Arclight', rarity: 'Legendary', cores: 2400 },
  { sku: 'bulwark_skin_ironclad', name: 'Ironclad', turretClass: 'Bulwark', rarity: 'Rare', cores: 800 },
  { sku: 'bulwark_skin_warlord', name: 'Warlord', turretClass: 'Bulwark', rarity: 'Epic', cores: 1500 },
  { sku: 'hailstorm_skin_frostbite', name: 'Frostbite', turretClass: 'Hailstorm', rarity: 'Epic', cores: 1500 },
  { sku: 'hailstorm_skin_tempest', name: 'Tempest', turretClass: 'Hailstorm', rarity: 'Legendary', cores: 2400 },
  { sku: 'lancer_skin_longshot', name: 'Longshot', turretClass: 'Lancer', rarity: 'Rare', cores: 800 },
  { sku: 'lancer_skin_deadeye', name: 'Deadeye', turretClass: 'Lancer', rarity: 'Legendary', cores: 2400 },
  { sku: 'tether_skin_anchor', name: 'Anchor', turretClass: 'Tether', rarity: 'Rare', cores: 800 },
];

export const GEAR: GearDef[] = [
  { sku: 'warden_armor_frontier', name: 'Frontier Issue', kind: 'armor', rarity: 'Common', cores: 400 },
  { sku: 'warden_armor_vanguard', name: 'Vanguard Plate', kind: 'armor', rarity: 'Epic', cores: 1200 },
  { sku: 'warden_emote_salute', name: 'Salute', kind: 'emote', rarity: 'Common', cores: 250 },
  { sku: 'warden_decal_rimehunter', name: 'Rime Hunter', kind: 'decal', rarity: 'Common', cores: 300 },
  // Bundle-only title. Price is an assumption (known gap 4). Hidden from the store.
  { sku: 'warden_title_plankowner', name: 'Plank Owner', kind: 'title', rarity: 'Legendary', cores: 1500, hidden: true },
];

export const BOOSTERS: BoosterDef[] = [
  { sku: 'booster_salvage_24h', name: 'Salvage Surge (24h)', effect: 'salvage', duration: '24h', cores: 300, dailyLimit: 5 },
  { sku: 'booster_xp_24h', name: 'Field Promotion (24h)', effect: 'xp', duration: '24h', cores: 300, dailyLimit: 5 },
  { sku: 'booster_salvage_7d', name: 'Salvage Surge (7 days)', effect: 'salvage', duration: '7d', cores: 1200 },
];

export const BUNDLES: BundleDef[] = [
  {
    sku: 'bundle_frontier_starter', name: 'Frontier Starter Pack', usd: 9.99, limitPerUser: 1,
    contents: [{ sku: 'cores', quantity: 1200 }, { sku: 'spitter_skin_obsidian', quantity: 1 }, { sku: 'booster_salvage_24h', quantity: 1 }],
    image: 'bundles/starter.jpg',
  },
  {
    // Priced in USD because the bundle Admin endpoint drops vc_prices (known gap 3).
    sku: 'bundle_wardens_arsenal', name: "Warden's Arsenal", usd: 29.99,
    contents: [
      { sku: 'spitter_skin_huntsman', quantity: 1 }, { sku: 'arclight_skin_voltaic', quantity: 1 },
      { sku: 'bulwark_skin_ironclad', quantity: 1 }, { sku: 'lancer_skin_longshot', quantity: 1 },
    ],
    image: 'bundles/arsenal.jpg',
  },
  {
    sku: 'bundle_rime_hunter', name: 'Rime Hunter Bundle', usd: 14.99,
    contents: [{ sku: 'lancer_skin_deadeye', quantity: 1 }, { sku: 'warden_emote_salute', quantity: 1 }, { sku: 'warden_decal_rimehunter', quantity: 1 }],
    image: 'bundles/rime_hunter.jpg',
  },
  {
    // 30 days of Warden's Charter is omitted (known gap 2).
    sku: 'bundle_founders', name: "Founder's Pack", usd: 49.99, limitPerUser: 1, window: SEASON_ONE,
    contents: [
      { sku: 'warden_armor_vanguard', quantity: 1 }, { sku: 'arclight_skin_solarflare', quantity: 1 },
      { sku: 'hailstorm_skin_tempest', quantity: 1 }, { sku: 'cores', quantity: 7000 },
      { sku: 'warden_title_plankowner', quantity: 1 },
    ],
    image: 'bundles/founders.jpg',
  },
];

export const PASS: PassDef = {
  sku: 'pass_s1_frontier', name: 'Frontier Pass, Season 1: Cold Open', usd: 9.99,
  window: SEASON_ONE, image: 'passes/frontier_pass_s1.jpg',
};

/** Display-only. Not seeded (known gap 1). */
export const CHARTER = { sku: 'sub_wardens_charter', name: "Warden's Charter", usd: 7.99, image: 'passes/wardens_charter.jpg' };

const cores = (sku: string): number | undefined =>
  SKINS.find((s) => s.sku === sku)?.cores ?? GEAR.find((g) => g.sku === sku)?.cores ?? BOOSTERS.find((b) => b.sku === sku)?.cores;

/** Sum of what the contents would cost individually, in Cores. */
export function coresValue(b: BundleDef): number {
  return b.contents.reduce((sum, c) => sum + (c.sku === CORES_SKU ? c.quantity : (cores(c.sku) ?? 0) * c.quantity), 0);
}

export const IMAGES: Record<string, string> = {
  [CORES_SKU]: 'currency/cores.jpg',
  [SCRAP_SKU]: 'currency/scrap.jpg',
  ...Object.fromEntries(PACKS.map((p) => [p.sku, p.image])),
  ...Object.fromEntries(SKINS.map((s) => [s.sku, `skins/${s.sku}.jpg`])),
  ...Object.fromEntries(GEAR.filter((g) => g.kind !== 'title').map((g) => [g.sku, `gear/${g.sku}.jpg`])),
  ...Object.fromEntries(BOOSTERS.map((b) => [b.sku, `boosters/${b.sku}.jpg`])),
  ...Object.fromEntries(BUNDLES.map((b) => [b.sku, b.image])),
  [PASS.sku]: PASS.image,
  [CHARTER.sku]: CHARTER.image,
};
```

- [ ] **Step 5: Write `catalog/regional.ts`**

```ts
import { CURRENCIES, type Currency } from './types';

const MULTIPLIER: Record<Currency, number> = { USD: 1, EUR: 1, GBP: 0.9, BRL: 5, JPY: 150 };

// Hand-set prices from CONTEXT.md's worked example.
const OVERRIDES: Record<string, Partial<Record<Currency, number>>> = {
  cores_1200: { BRL: 49.9, JPY: 1500 },
};

export function regionalPrice(sku: string, usd: number, currency: Currency): number {
  const fixed = OVERRIDES[sku]?.[currency];
  if (fixed !== undefined) return fixed;
  const raw = usd * MULTIPLIER[currency];
  return currency === 'JPY' ? Math.round(raw / 10) * 10 : Math.round(raw * 100) / 100;
}

export function pricesFor(sku: string, usd: number) {
  return CURRENCIES.map((currency) => ({
    currency,
    amount: regionalPrice(sku, usd, currency),
    is_default: currency === 'USD',
    is_enabled: true,
  }));
}
```

- [ ] **Step 6: Write `catalog/copy.ts`**

```ts
import { LOCALES, type L10n, type Locale } from './types';

export type CopyKind =
  | 'skin' | 'armor' | 'emote' | 'decal' | 'title' | 'booster' | 'pack' | 'bundle' | 'pass' | 'cores' | 'scrap';

export interface Vars {
  rarity?: string; cls?: string; effect?: 'salvage' | 'xp'; duration?: '24h' | '7d';
  total?: number; bonus?: number; list?: string;
}

const RARITY: Record<string, L10n> = {
  Common: { en: 'Common', fr: 'Commun', de: 'Gewöhnlich', ja: 'コモン', 'pt-BR': 'Comum' },
  Rare: { en: 'Rare', fr: 'Rare', de: 'Selten', ja: 'レア', 'pt-BR': 'Raro' },
  Epic: { en: 'Epic', fr: 'Épique', de: 'Episch', ja: 'エピック', 'pt-BR': 'Épico' },
  Legendary: { en: 'Legendary', fr: 'Légendaire', de: 'Legendär', ja: 'レジェンダリー', 'pt-BR': 'Lendário' },
};
const EFFECT: Record<string, L10n> = {
  salvage: { en: '2× Scrap', fr: '2× Scrap', de: '2× Scrap', ja: 'Scrap 2倍', 'pt-BR': '2× Scrap' },
  xp: { en: '2× Warden XP', fr: '2× XP de Gardien', de: '2× Wächter-XP', ja: 'ウォーデンXP 2倍', 'pt-BR': '2× XP de Guardião' },
};
const DURATION: Record<string, L10n> = {
  '24h': { en: '24 hours', fr: '24 heures', de: '24 Stunden', ja: '24時間', 'pt-BR': '24 horas' },
  '7d': { en: '7 days', fr: '7 jours', de: '7 Tage', ja: '7日間', 'pt-BR': '7 dias' },
};

type Tpl = Record<Locale, (v: Vars, l: Locale) => string>;
const n = (x: number | undefined, l: Locale) => new Intl.NumberFormat(l).format(x ?? 0);
const r = (v: Vars, l: Locale) => RARITY[v.rarity ?? 'Common']![l];

const TEMPLATES: Record<CopyKind, Tpl> = {
  skin: {
    en: (v, l) => `${v.cls} skin (${r(v, l)}). Cosmetic only, no stat changes.`,
    fr: (v, l) => `Skin ${v.cls} (${r(v, l)}). Cosmétique uniquement, aucun effet sur les stats.`,
    de: (v, l) => `${v.cls}-Skin (${r(v, l)}). Nur kosmetisch, keine Werteänderungen.`,
    ja: (v, l) => `${v.cls}スキン(${r(v, l)})。見た目のみで、性能は変わりません。`,
    'pt-BR': (v, l) => `Skin de ${v.cls} (${r(v, l)}). Apenas cosmético, sem alterar atributos.`,
  },
  armor: {
    en: () => 'Warden armor set. Cosmetic only.', fr: () => 'Armure de Gardien. Cosmétique uniquement.',
    de: () => 'Wächter-Rüstung. Nur kosmetisch.', ja: () => 'ウォーデン用アーマー。見た目のみ。',
    'pt-BR': () => 'Armadura de Guardião. Apenas cosmética.',
  },
  emote: {
    en: () => 'A Warden emote. Cosmetic only.', fr: () => 'Une emote de Gardien. Cosmétique uniquement.',
    de: () => 'Eine Wächter-Emote. Nur kosmetisch.', ja: () => 'ウォーデン用エモート。見た目のみ。',
    'pt-BR': () => 'Um emote de Guardião. Apenas cosmético.',
  },
  decal: {
    en: () => 'A decal for your Warden gear. Cosmetic only.', fr: () => "Un décalque pour l'équipement de Gardien. Cosmétique uniquement.",
    de: () => 'Ein Decal für die Wächter-Ausrüstung. Nur kosmetisch.', ja: () => 'ウォーデンギア用デカール。見た目のみ。',
    'pt-BR': () => 'Um decalque para o equipamento de Guardião. Apenas cosmético.',
  },
  title: {
    en: () => 'An exclusive profile title.', fr: () => 'Un titre de profil exclusif.',
    de: () => 'Ein exklusiver Profiltitel.', ja: () => '限定プロフィールタイトル。', 'pt-BR': () => 'Um título de perfil exclusivo.',
  },
  booster: {
    en: (v, l) => `${EFFECT[v.effect!]![l]} for ${DURATION[v.duration!]![l]}.`,
    fr: (v, l) => `${EFFECT[v.effect!]![l]} pendant ${DURATION[v.duration!]![l]}.`,
    de: (v, l) => `${EFFECT[v.effect!]![l]} für ${DURATION[v.duration!]![l]}.`,
    ja: (v, l) => `${DURATION[v.duration!]![l]}、${EFFECT[v.effect!]![l]}。`,
    'pt-BR': (v, l) => `${EFFECT[v.effect!]![l]} por ${DURATION[v.duration!]![l]}.`,
  },
  pack: {
    en: (v, l) => (v.bonus ? `${n(v.total, l)} Cores (includes ${n(v.bonus, l)} bonus).` : `${n(v.total, l)} Cores.`),
    fr: (v, l) => (v.bonus ? `${n(v.total, l)} Cores (dont ${n(v.bonus, l)} bonus).` : `${n(v.total, l)} Cores.`),
    de: (v, l) => (v.bonus ? `${n(v.total, l)} Cores (inkl. ${n(v.bonus, l)} Bonus).` : `${n(v.total, l)} Cores.`),
    ja: (v, l) => (v.bonus ? `${n(v.total, l)} Cores(ボーナス${n(v.bonus, l)}含む)。` : `${n(v.total, l)} Cores。`),
    'pt-BR': (v, l) => (v.bonus ? `${n(v.total, l)} Cores (inclui ${n(v.bonus, l)} de bônus).` : `${n(v.total, l)} Cores.`),
  },
  bundle: {
    en: (v) => `Includes: ${v.list}.`, fr: (v) => `Contient : ${v.list}.`, de: (v) => `Enthält: ${v.list}.`,
    ja: (v) => `内容: ${v.list}。`, 'pt-BR': (v) => `Inclui: ${v.list}.`,
  },
  pass: {
    en: () => 'Season 1: Cold Open. Unlocks the premium reward track.',
    fr: () => 'Saison 1 : Cold Open. Débloque la piste de récompenses premium.',
    de: () => 'Saison 1: Cold Open. Schaltet die Premium-Belohnungsleiste frei.',
    ja: () => 'シーズン1「Cold Open」。プレミアム報酬トラックを解放します。',
    'pt-BR': () => 'Temporada 1: Cold Open. Libera a trilha de recompensas premium.',
  },
  cores: {
    en: () => 'Premium currency of Voidwall.', fr: () => 'La monnaie premium de Voidwall.',
    de: () => 'Die Premium-Währung von Voidwall.', ja: () => 'Voidwallのプレミアム通貨。', 'pt-BR': () => 'A moeda premium de Voidwall.',
  },
  scrap: {
    en: () => 'Soft currency earned in play.', fr: () => 'Monnaie gratuite gagnée en jouant.',
    de: () => 'Weiche Währung, die du im Spiel verdienst.', ja: () => 'プレイで手に入るソフトカレンシー。',
    'pt-BR': () => 'Moeda comum ganha jogando.',
  },
};

const NAME_OVERRIDES: Record<string, Partial<L10n>> = {
  spitter_skin_obsidian: { fr: 'Obsidienne', ja: 'オブシディアン', 'pt-BR': 'Obsidiana' },
};
const DESC_OVERRIDES: Record<string, L10n> = {
  spitter_skin_obsidian: {
    en: 'A matte-black Spitter chassis cut from salvaged Well plating.',
    fr: "Un châssis de Spitter noir mat, taillé dans le blindage récupéré d'un Puits.",
    de: 'Ein mattschwarzes Spitter-Chassis aus geborgener Well-Panzerung.',
    ja: 'ウェルの装甲を再利用した、つや消しブラックのスピッター機体。',
    'pt-BR': 'Um chassi Spitter preto fosco forjado com blindagem recuperada de um Poço.',
  },
};

export function nameFor(sku: string, enName: string, locale: Locale): string {
  return NAME_OVERRIDES[sku]?.[locale] ?? enName;
}

export function descFor(sku: string, kind: CopyKind, vars: Vars, locale: Locale): string {
  return DESC_OVERRIDES[sku]?.[locale] ?? TEMPLATES[kind][locale](vars, locale);
}

export const allLocales = (f: (l: Locale) => string): L10n =>
  Object.fromEntries(LOCALES.map((l) => [l, f(l)])) as L10n;
```

- [ ] **Step 7: Run tests**

Run: `npm test`
Expected: all tests in `catalog`, `regional`, `copy`, `smoke` pass.

---

### Task 2: Admin payload builders and seed plan

**Files:**
- Create: `catalog/payloads.ts`, `catalog/plan.ts`
- Test: `tests/payloads.test.ts`

**Interfaces:**
- Consumes: everything produced by Task 1.
- Produces:
  - `type Kind = 'group' | 'currency' | 'package' | 'item' | 'bundle'`
  - `interface PlanStep { kind: Kind; key: string; payload: Record<string, any>; expectInStore: boolean }`
  - `buildPlan(): PlanStep[]` (ordered: groups, currencies, items, packages, bundles)

Fields follow `skills/catalog-design/references/items.md` and the earlier friction log (booster `inventory_options.consumable` must be a boolean, bundles drop `vc_prices`, currency with `is_show_in_store: true` demands a default price). Task 0 Step 7 answers (`pt-BR` key, bundle `type`, `limits` shape) override anything below if they differ; update the builders and tests together.

- [ ] **Step 1: Write the failing tests**

`tests/payloads.test.ts`:

```ts
import { describe, expect, test } from 'vitest';
import { LOCALES } from '../catalog/types';
import { buildPlan } from '../catalog/plan';

const plan = buildPlan();
const byKey = (k: string) => plan.find((s) => s.key === k)!;

describe('seed plan', () => {
  test('order: groups, currencies, items, packages, bundles', () => {
    const kinds = plan.map((s) => s.kind);
    const firstIndex = (k: string) => kinds.indexOf(k as never);
    expect(firstIndex('group')).toBe(0);
    expect(firstIndex('currency')).toBeGreaterThan(kinds.lastIndexOf('group'));
    expect(firstIndex('item')).toBeGreaterThan(kinds.lastIndexOf('currency'));
    expect(firstIndex('package')).toBeGreaterThan(kinds.lastIndexOf('item'));
    expect(firstIndex('bundle')).toBeGreaterThan(kinds.lastIndexOf('package'));
  });

  test('37 steps: 6 groups, 2 currencies, 20 items, 5 packages, 4 bundles', () => {
    const count = (k: string) => plan.filter((s) => s.kind === k).length;
    expect([count('group'), count('currency'), count('item'), count('package'), count('bundle')]).toEqual([6, 2, 20, 5, 4]);
  });

  test('every name and description has all five locales', () => {
    for (const s of plan.filter((p) => p.kind !== 'group')) {
      for (const field of ['name', 'description']) {
        for (const l of LOCALES) {
          expect(s.payload[field]?.[l], `${s.key}.${field}.${l}`).toBeTruthy();
        }
      }
    }
  });

  test('no step touches quest fixtures', () => {
    for (const s of plan) expect(s.key).not.toMatch(/^quest_|^qp_/);
  });

  test('skin: Cores price, group and attributes', () => {
    const p = byKey('arclight_skin_solarflare').payload;
    expect(p.vc_prices).toEqual([{ sku: 'cores', amount: 2400, is_default: true, is_enabled: true }]);
    expect(p.groups).toEqual(['turret_skins']);
    const attr = Object.fromEntries(p.attributes.map((a: any) => [a.external_id, a.values[0].external_id]));
    expect(attr).toEqual({ rarity: 'legendary', turret_class: 'arclight' });
    expect(p.virtual_item_type).toBe('non_consumable');
  });

  test('boosters are consumable (boolean) with daily limit on 24h only', () => {
    const day = byKey('booster_xp_24h').payload;
    expect(day.virtual_item_type).toBe('consumable');
    expect(day.inventory_options.consumable).toBe(true);
    expect(day.limits.per_user.total).toBe(5);
    expect(day.limits.per_user.recurrent_schedule.per_user.interval_type).toBe('daily');
    expect(byKey('booster_salvage_7d').payload.limits).toBeUndefined();
  });

  test('packs grant base + bonus and carry five currencies', () => {
    const p = byKey('cores_1200').payload;
    expect(p.content).toEqual([{ sku: 'cores', quantity: 1200 }]);
    expect(p.prices.map((x: any) => x.currency)).toEqual(['USD', 'EUR', 'GBP', 'BRL', 'JPY']);
    expect(p.prices[0]).toMatchObject({ currency: 'USD', amount: 9.99, is_default: true });
  });

  test('bundles: money price only, limits and window', () => {
    for (const k of ['bundle_frontier_starter', 'bundle_wardens_arsenal', 'bundle_rime_hunter', 'bundle_founders']) {
      expect(byKey(k).payload.vc_prices).toBeUndefined();
      expect(byKey(k).payload.prices).toHaveLength(5);
    }
    expect(byKey('bundle_frontier_starter').payload.limits.per_user.total).toBe(1);
    expect(byKey('bundle_founders').payload.periods).toEqual([
      { date_from: '2026-10-14T00:00:00+00:00', date_until: '2027-01-13T23:59:59+00:00' },
    ]);
    expect(byKey('bundle_wardens_arsenal').payload.periods).toBeUndefined();
  });

  test('hidden title, Cores currency hidden, windowed items not expected in store', () => {
    expect(byKey('warden_title_plankowner').payload.is_show_in_store).toBe(false);
    expect(byKey('cores').payload.is_show_in_store).toBe(false);
    expect(byKey('pass_s1_frontier').expectInStore).toBe(false);
    expect(byKey('bundle_founders').expectInStore).toBe(false);
    expect(byKey('bundle_rime_hunter').expectInStore).toBe(true);
    expect(byKey('cores_500').expectInStore).toBe(true);
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `npm test -- payloads`
Expected: FAIL, `../catalog/plan` not found.

- [ ] **Step 3: Write `catalog/payloads.ts`**

```ts
import {
  BOOSTERS, BUNDLES, CORES_SKU, GEAR, GROUPS, PACKS, PASS, SCRAP_SKU, SKINS, coresValue,
} from './catalog';
import { allLocales, descFor, nameFor, type CopyKind, type Vars } from './copy';
import { pricesFor } from './regional';
import type { BoosterDef, BundleDef, GearDef, GroupDef, PackDef, SkinDef, Window } from './types';

const lower = (s: string) => s.toLowerCase();
const vcPrice = (amount: number) => [{ sku: CORES_SKU, amount, is_default: true, is_enabled: true }];
const periods = (w?: Window) => (w ? [{ date_from: w.from, date_until: w.until }] : undefined);
const text = (sku: string, enName: string, kind: CopyKind, vars: Vars = {}) => ({
  name: allLocales((l) => nameFor(sku, enName, l)),
  description: allLocales((l) => descFor(sku, kind, vars, l)),
});
const attribute = (id: string, label: string, value: string, shown: string) => ({
  external_id: id, name: { en: label }, values: [{ external_id: lower(value).replace(/\s+/g, '_'), value: { en: shown } }],
});

export const buildGroup = (g: GroupDef) => ({ external_id: g.id, name: g.names, order: g.order });

export const buildCurrency = (sku: string, enName: string, kind: 'cores' | 'scrap') => ({
  sku, ...text(sku, enName, kind), is_enabled: true, is_show_in_store: false,
});

export const buildPack = (p: PackDef) => ({
  sku: p.sku, ...text(p.sku, p.name, 'pack', { total: p.base + p.bonus, bonus: p.bonus }),
  is_enabled: true, is_show_in_store: true, prices: pricesFor(p.sku, p.usd),
  content: [{ sku: CORES_SKU, quantity: p.base + p.bonus }],
});

export const buildSkin = (s: SkinDef) => ({
  sku: s.sku, ...text(s.sku, s.name, 'skin', { rarity: s.rarity, cls: s.turretClass }),
  groups: ['turret_skins'], is_enabled: true, is_show_in_store: true,
  virtual_item_type: 'non_consumable', vc_prices: vcPrice(s.cores),
  attributes: [
    attribute('rarity', 'Rarity', s.rarity, s.rarity),
    attribute('turret_class', 'Turret class', s.turretClass, s.turretClass),
  ],
});

export const buildGear = (g: GearDef) => ({
  sku: g.sku, ...text(g.sku, g.name, g.kind),
  groups: ['warden_gear'], is_enabled: true, is_show_in_store: !g.hidden,
  virtual_item_type: 'non_consumable', vc_prices: vcPrice(g.cores),
  attributes: [attribute('rarity', 'Rarity', g.rarity, g.rarity)],
});

export const buildBooster = (b: BoosterDef) => ({
  sku: b.sku, ...text(b.sku, b.name, 'booster', { effect: b.effect, duration: b.duration }),
  groups: ['boosters'], is_enabled: true, is_show_in_store: true,
  virtual_item_type: 'consumable', inventory_options: { consumable: true }, vc_prices: vcPrice(b.cores),
  ...(b.dailyLimit
    ? { limits: { per_user: { total: b.dailyLimit, recurrent_schedule: { per_user: { interval_type: 'daily', time: '00:00:00+00:00' } } } } }
    : {}),
});

export const buildBundle = (b: BundleDef, itemNames: Record<string, string>) => {
  const list = b.contents
    .map((c) => (c.sku === CORES_SKU ? `${new Intl.NumberFormat('en').format(c.quantity)} Cores` : itemNames[c.sku] ?? c.sku))
    .join(', ');
  return {
    sku: b.sku, ...text(b.sku, b.name, 'bundle', { list }),
    groups: ['bundles'], is_enabled: true, is_show_in_store: true,
    prices: pricesFor(b.sku, b.usd), content: b.contents,
    ...(b.limitPerUser ? { limits: { per_user: { total: b.limitPerUser } } } : {}),
    ...(b.window ? { periods: periods(b.window) } : {}),
  };
};

export const buildPass = () => ({
  sku: PASS.sku, ...text(PASS.sku, PASS.name, 'pass'),
  groups: ['passes'], is_enabled: true, is_show_in_store: true,
  virtual_item_type: 'non_consumable', prices: pricesFor(PASS.sku, PASS.usd), periods: periods(PASS.window),
});

export { SCRAP_SKU, coresValue, BUNDLES, BOOSTERS, GEAR, GROUPS, PACKS, SKINS };
```

- [ ] **Step 4: Write `catalog/plan.ts`**

```ts
import { BUNDLES, BOOSTERS, CORES_SKU, GEAR, GROUPS, PACKS, SCRAP_SKU, SKINS } from './catalog';
import {
  buildBooster, buildBundle, buildCurrency, buildGear, buildGroup, buildPack, buildPass, buildSkin,
} from './payloads';

export type Kind = 'group' | 'currency' | 'package' | 'item' | 'bundle';
export interface PlanStep {
  kind: Kind;
  key: string;
  payload: Record<string, any>;
  /** True if the public catalog should return it today (shown, enabled, not date-windowed). */
  expectInStore: boolean;
}

const step = (kind: Kind, key: string, payload: Record<string, any>): PlanStep => ({
  kind, key, payload,
  expectInStore: kind !== 'group' && payload.is_show_in_store === true && !payload.periods,
});

export function buildPlan(): PlanStep[] {
  const itemNames = Object.fromEntries([...SKINS, ...GEAR, ...BOOSTERS].map((i) => [i.sku, i.name]));
  return [
    ...GROUPS.map((g) => step('group', g.id, buildGroup(g))),
    step('currency', CORES_SKU, buildCurrency(CORES_SKU, 'Cores', 'cores')),
    step('currency', SCRAP_SKU, buildCurrency(SCRAP_SKU, 'Scrap', 'scrap')),
    ...SKINS.map((s) => step('item', s.sku, buildSkin(s))),
    ...GEAR.map((g) => step('item', g.sku, buildGear(g))),
    ...BOOSTERS.map((b) => step('item', b.sku, buildBooster(b))),
    step('item', 'pass_s1_frontier', buildPass()),
    ...PACKS.map((p) => step('package', p.sku, buildPack(p))),
    ...BUNDLES.map((b) => step('bundle', b.sku, buildBundle(b, itemNames))),
  ];
}
```

- [ ] **Step 5: Run tests**

Run: `npm test`
Expected: all pass (the pass key `pass_s1_frontier` and attribute value ids like `legendary`, `arclight` match the test).

---

### Task 3: Store API client, locales, view helpers

**Files:**
- Create: `src/config.ts`, `src/i18n/locales.ts`, `src/api/store.ts`, `src/api/view.ts`
- Test: `tests/store.test.ts`, `tests/view.test.ts`, `tests/locales.test.ts`

**Interfaces:**
- Consumes: `LOCALES`, `Locale`, `GROUPS`, `IMAGES`, `PACKS`, `SKINS`, `GEAR`, `BOOSTERS`, `BUNDLES`, `PASS`, `CORES_SKU` from `catalog/`.
- Produces:
  - `STORE_LOCALE`, `PAY_LANGUAGE`, `LOGIN_LOCALE: Record<Locale,string>`, `resolveLocale(raw: string | null | undefined): Locale`
  - `Money = { amount: number; amountWithoutDiscount: number; currency: string }`
  - `ShopItem = { sku; kind: 'item'|'package'|'bundle'; name; description; imageUrl?; groups: string[]; attributes: Record<string,string>; price?: Money; coresPrice?: number }`
  - `fetchCatalog(projectId: string, locale: Locale, f?: typeof fetch): Promise<ShopItem[]>`
  - `formatMoney(m: Money | undefined, locale: Locale): string` (empty string when undefined)
  - `knownItems(items: ShopItem[]): ShopItem[]`, `groupOf(item): GroupId`, `byGroup(items, id): ShopItem[]`, `visibleGroups(items): GroupDef[]`

- [ ] **Step 1: Write the failing tests**

`tests/locales.test.ts`:

```ts
import { expect, test } from 'vitest';
import { PAY_LANGUAGE, STORE_LOCALE, resolveLocale } from '../src/i18n/locales';

test('resolveLocale falls back to en for junk', () => {
  expect(resolveLocale('fr')).toBe('fr');
  expect(resolveLocale('pt-BR')).toBe('pt-BR');
  for (const bad of [null, undefined, '', 'xx', 'FR', '{"a":1}']) expect(resolveLocale(bad)).toBe('en');
});

test('code maps cover every locale', () => {
  for (const l of ['en', 'fr', 'de', 'ja', 'pt-BR'] as const) {
    expect(STORE_LOCALE[l]).toBeTruthy();
    expect(PAY_LANGUAGE[l]).toBeTruthy();
  }
});
```

`tests/store.test.ts`:

```ts
import { expect, test } from 'vitest';
import { fetchCatalog, formatMoney, normalizeItem } from '../src/api/store';

const rawSkin = {
  sku: 'lancer_skin_deadeye', name: 'Deadeye', description: 'd', image_url: 'https://cdn/x.jpg',
  groups: [{ external_id: 'turret_skins' }],
  attributes: [{ external_id: 'rarity', values: [{ external_id: 'legendary', value: 'Legendary' }] }],
  price: null,
  virtual_prices: [{ sku: 'cores', amount: 2400, is_default: true }],
};
const rawPack = {
  sku: 'cores_1200', name: 'Core Stack', description: 'd', groups: [],
  price: { amount: '9.99', amount_without_discount: '9.99', currency: 'USD' },
};

test('normalizeItem: Cores price, null price, attributes', () => {
  const it = normalizeItem(rawSkin, 'item');
  expect(it.coresPrice).toBe(2400);
  expect(it.price).toBeUndefined();
  expect(it.attributes).toEqual({ rarity: 'legendary' });
  expect(it.groups).toEqual(['turret_skins']);
});

test('normalizeItem: money strings become numbers', () => {
  const it = normalizeItem(rawPack, 'package');
  expect(it.price).toEqual({ amount: 9.99, amountWithoutDiscount: 9.99, currency: 'USD' });
});

test('formatMoney: undefined price is an empty string, not NaN', () => {
  expect(formatMoney(undefined, 'en')).toBe('');
  expect(formatMoney({ amount: 9.99, amountWithoutDiscount: 9.99, currency: 'USD' }, 'en')).toBe('$9.99');
  expect(formatMoney({ amount: 1500, amountWithoutDiscount: 1500, currency: 'JPY' }, 'ja')).toMatch(/1,500/);
});

test('fetchCatalog paginates, passes locale, never sends country', async () => {
  const urls: string[] = [];
  const page = (items: unknown[], more: boolean) => new Response(JSON.stringify({ items, has_more: more }), { status: 200 });
  const f = (async (url: string) => {
    urls.push(url);
    if (url.includes('/items/virtual_items') && !url.includes('offset=50')) return page([rawSkin], true);
    if (url.includes('/items/virtual_items')) return page([], false);
    if (url.includes('/package')) return page([rawPack], false);
    return page([], false);
  }) as unknown as typeof fetch;
  const items = await fetchCatalog('316665', 'pt-BR', f);
  expect(items.map((i) => i.sku).sort()).toEqual(['cores_1200', 'lancer_skin_deadeye']);
  expect(urls.every((u) => u.includes('locale=pt_BR'))).toBe(true);
  expect(urls.some((u) => u.includes('country='))).toBe(false);
  expect(urls.filter((u) => u.includes('/items/virtual_items'))).toHaveLength(2);
});

test('fetchCatalog throws on a non-2xx response', async () => {
  const f = (async () => new Response('{}', { status: 500 })) as unknown as typeof fetch;
  await expect(fetchCatalog('316665', 'en', f)).rejects.toThrow(/500/);
});
```

`tests/view.test.ts`:

```ts
import { expect, test } from 'vitest';
import { byGroup, groupOf, knownItems, visibleGroups } from '../src/api/view';
import type { ShopItem } from '../src/api/store';

const mk = (sku: string, kind: ShopItem['kind'] = 'item', groups: string[] = []): ShopItem => ({
  sku, kind, name: sku, description: '', groups, attributes: {},
});

test('knownItems drops foreign quest fixtures', () => {
  const out = knownItems([mk('quest_demo_r1h_20260930t1910z'), mk('qp_fire_sword_1'), mk('tether_skin_anchor')]);
  expect(out.map((i) => i.sku)).toEqual(['tether_skin_anchor']);
});

test('packages land in currency, bundles in bundles, items by group', () => {
  expect(groupOf(mk('cores_500', 'package'))).toBe('currency');
  expect(groupOf(mk('bundle_rime_hunter', 'bundle'))).toBe('bundles');
  expect(groupOf(mk('booster_xp_24h', 'item'))).toBe('boosters');
  expect(groupOf(mk('arclight_skin_voltaic'))).toBe('turret_skins');
});

test('visibleGroups hides empty sections (windowed pass hidden before Season 1)', () => {
  const items = knownItems([mk('cores_500', 'package'), mk('tether_skin_anchor')]);
  expect(visibleGroups(items).map((g) => g.id)).toEqual(['currency', 'turret_skins']);
  expect(byGroup(items, 'passes')).toEqual([]);
});
```

- [ ] **Step 2: Run to verify failure**

Run: `npm test`
Expected: FAIL, modules under `src/` not found.

- [ ] **Step 3: Write `src/config.ts` and `src/i18n/locales.ts`**

`src/config.ts`:

```ts
const env = import.meta.env;

export const config = {
  projectId: (env.VITE_XSOLLA_PROJECT_ID as string) ?? '',
  sandbox: (env.VITE_SANDBOX as string) !== 'false',
  loginProjectId: (env.VITE_LOGIN_PROJECT_ID as string) ?? '',
  loginClientId: (env.VITE_LOGIN_CLIENT_ID as string) ?? '',
  supportEmail: 'support@playvoidwall.com',
};

export const loginConfigured = Boolean(config.loginProjectId && config.loginClientId);
```

`src/i18n/locales.ts` (apply Task 0 Step 7 answers 1 and 3 if they differ):

```ts
import { LOCALES, type Locale } from '../../catalog/types';

export { LOCALES };
export type { Locale };

/** Store API `locale` query value. */
export const STORE_LOCALE: Record<Locale, string> = { en: 'en', fr: 'fr', de: 'de', ja: 'ja', 'pt-BR': 'pt_BR' };
/** Headless Checkout / token `settings.language`. Unsupported shop locales must map to 'en'. */
export const PAY_LANGUAGE: Record<Locale, string> = { en: 'en', fr: 'fr', de: 'de', ja: 'ja', 'pt-BR': 'pt' };
/** Login widget `preferredLocale`. */
export const LOGIN_LOCALE: Record<Locale, string> = { en: 'en_US', fr: 'fr_FR', de: 'de_DE', ja: 'ja_JP', 'pt-BR': 'pt_BR' };

export const LOCALE_LABEL: Record<Locale, string> = { en: 'EN', fr: 'FR', de: 'DE', ja: '日本語', 'pt-BR': 'PT-BR' };

export function resolveLocale(raw: string | null | undefined): Locale {
  return (LOCALES as readonly string[]).includes(raw ?? '') ? (raw as Locale) : 'en';
}
```

- [ ] **Step 4: Write `src/api/store.ts`**

```ts
import type { Locale } from '../../catalog/types';
import { STORE_LOCALE } from '../i18n/locales';

export interface Money { amount: number; amountWithoutDiscount: number; currency: string }
export type ItemKind = 'item' | 'package' | 'bundle';
export interface ShopItem {
  sku: string; kind: ItemKind; name: string; description: string; imageUrl?: string;
  groups: string[]; attributes: Record<string, string>; price?: Money; coresPrice?: number;
}

export class StoreApiError extends Error {
  constructor(public status: number, public url: string) {
    super(`Store API ${status} for ${url}`);
  }
}

export const storeBase = (projectId: string) => `https://store.xsolla.com/api/v2/project/${projectId}`;

export function normalizeItem(raw: any, kind: ItemKind): ShopItem {
  const cores = (raw.virtual_prices ?? []).find((p: any) => p.sku === 'cores');
  const p = raw.price;
  return {
    sku: raw.sku, kind, name: raw.name ?? raw.sku, description: raw.description ?? '',
    imageUrl: raw.image_url ?? undefined,
    groups: (raw.groups ?? []).map((g: any) => g.external_id),
    attributes: Object.fromEntries(
      (raw.attributes ?? []).map((a: any) => [a.external_id, a.values?.[0]?.external_id ?? '']),
    ),
    price: p ? { amount: Number(p.amount), amountWithoutDiscount: Number(p.amount_without_discount ?? p.amount), currency: p.currency } : undefined,
    coresPrice: cores ? Number(cores.amount) : undefined,
  };
}

async function fetchAll(url: string, f: typeof fetch): Promise<any[]> {
  const out: any[] = [];
  for (let offset = 0; ; offset += 50) {
    const sep = url.includes('?') ? '&' : '?';
    const full = `${url}${sep}limit=50&offset=${offset}`;
    const res = await f(full);
    if (!res.ok) throw new StoreApiError(res.status, full);
    const body = await res.json();
    out.push(...(body.items ?? []));
    if (!body.has_more) return out;
  }
}

/** Catalog is read from the browser with no `country`, so Xsolla resolves prices from the buyer's IP. */
export async function fetchCatalog(projectId: string, locale: Locale, f: typeof fetch = fetch): Promise<ShopItem[]> {
  const base = storeBase(projectId);
  const q = `locale=${STORE_LOCALE[locale]}`;
  const [items, packs, bundles] = await Promise.all([
    fetchAll(`${base}/items/virtual_items?${q}`, f),
    fetchAll(`${base}/items/virtual_currency/package?${q}`, f),
    fetchAll(`${base}/items/bundle?${q}`, f),
  ]);
  return [
    ...items.map((r) => normalizeItem(r, 'item')),
    ...packs.map((r) => normalizeItem(r, 'package')),
    ...bundles.map((r) => normalizeItem(r, 'bundle')),
  ];
}

export function formatMoney(m: Money | undefined, locale: Locale): string {
  if (!m || Number.isNaN(m.amount)) return '';
  return new Intl.NumberFormat(locale, { style: 'currency', currency: m.currency }).format(m.amount);
}
```

- [ ] **Step 5: Write `src/api/view.ts`**

```ts
import { BOOSTERS, BUNDLES, GEAR, GROUPS, PACKS, PASS, SKINS } from '../../catalog/catalog';
import type { GroupDef, GroupId } from '../../catalog/types';
import type { ShopItem } from './store';

const KNOWN = new Set<string>([
  ...PACKS, ...SKINS, ...GEAR, ...BOOSTERS, ...BUNDLES, PASS,
].map((d) => d.sku));

const GROUP_BY_SKU = new Map<string, GroupId>([
  ...SKINS.map((s) => [s.sku, 'turret_skins'] as const),
  ...GEAR.map((g) => [g.sku, 'warden_gear'] as const),
  ...BOOSTERS.map((b) => [b.sku, 'boosters'] as const),
  [PASS.sku, 'passes'] as const,
]);

/** The project also holds unrelated quest fixtures; only Voidwall SKUs are rendered. */
export const knownItems = (items: ShopItem[]) => items.filter((i) => KNOWN.has(i.sku));

export function groupOf(item: ShopItem): GroupId {
  if (item.kind === 'package') return 'currency';
  if (item.kind === 'bundle') return 'bundles';
  return GROUP_BY_SKU.get(item.sku) ?? 'turret_skins';
}

export const byGroup = (items: ShopItem[], id: GroupId) => items.filter((i) => groupOf(i) === id);

export const visibleGroups = (items: ShopItem[]): GroupDef[] =>
  GROUPS.filter((g) => byGroup(items, g.id).length > 0);
```

- [ ] **Step 6: Run tests**

Run: `npm test`
Expected: all pass.

---

### Task 4: Seed script

**Files:**
- Create: `scripts/lib/env.ts`, `scripts/lib/admin.ts`, `scripts/seed-catalog.ts`
- Test: `tests/seed.test.ts`

**Interfaces:**
- Consumes: `buildPlan`, `PlanStep`, `Kind` (Task 2); `fetchCatalog`, `ShopItem` (Task 3).
- Produces: `npm run seed` (dry-run), `npm run seed -- --apply`, `npm run seed -- --verify`.
  - `parseEnv(text: string): Record<string,string>`
  - `createAdmin(cfg): Admin` where `Admin = { call(method, path, body?): Promise<{ status: number; body: unknown }> }`
  - `upsert(admin, step, apply): Promise<'create' | 'update'>`, `SeedError`
  - `missingSkus(expected: string[], found: string[]): string[]`

- [ ] **Step 1: Write the failing tests**

`tests/seed.test.ts`:

```ts
import { describe, expect, test } from 'vitest';
import { parseEnv } from '../scripts/lib/env';
import { SeedError, missingSkus, upsert, type Admin } from '../scripts/lib/admin';
import type { PlanStep } from '../catalog/plan';

const step: PlanStep = { kind: 'item', key: 'tether_skin_anchor', payload: { sku: 'tether_skin_anchor' }, expectInStore: true };

function fakeAdmin(getStatus: number, writeStatus = 201) {
  const calls: { method: string; path: string }[] = [];
  const admin: Admin = {
    async call(method, path) {
      calls.push({ method, path });
      return { status: method === 'GET' ? getStatus : writeStatus, body: { err: 'x' } };
    },
  };
  return { admin, calls };
}

describe('upsert', () => {
  test('dry run never writes', async () => {
    const { admin, calls } = fakeAdmin(404);
    expect(await upsert(admin, step, false)).toBe('create');
    expect(calls.map((c) => c.method)).toEqual(['GET']);
  });

  test('404 then POST to the collection', async () => {
    const { admin, calls } = fakeAdmin(404);
    expect(await upsert(admin, step, true)).toBe('create');
    expect(calls).toEqual([
      { method: 'GET', path: '/items/virtual_items/sku/tether_skin_anchor' },
      { method: 'POST', path: '/items/virtual_items' },
    ]);
  });

  test('200 then PUT the full payload', async () => {
    const { admin, calls } = fakeAdmin(200, 204);
    expect(await upsert(admin, step, true)).toBe('update');
    expect(calls[1]).toEqual({ method: 'PUT', path: '/items/virtual_items/sku/tether_skin_anchor' });
  });

  test('unexpected GET status and failed writes throw SeedError', async () => {
    await expect(upsert(fakeAdmin(500).admin, step, true)).rejects.toBeInstanceOf(SeedError);
    await expect(upsert(fakeAdmin(404, 422).admin, step, true)).rejects.toBeInstanceOf(SeedError);
  });

  test('groups are addressed by external_id', async () => {
    const { admin, calls } = fakeAdmin(404);
    await upsert(admin, { kind: 'group', key: 'bundles', payload: {}, expectInStore: false }, true);
    expect(calls[0]!.path).toBe('/items/groups/bundles');
  });
});

test('SeedError message never contains request headers or keys', () => {
  const e = new SeedError(step, { status: 422, body: { errorMessage: 'bad' } });
  expect(e.message).toContain('422');
  expect(e.message).not.toMatch(/authorization|basic /i);
});

test('missingSkus', () => {
  expect(missingSkus(['a', 'b', 'c'], ['b'])).toEqual(['a', 'c']);
});

test('parseEnv reads KEY=VALUE, ignores comments and blanks, strips quotes', () => {
  expect(parseEnv('# c\nA=1\n\nB="two"\nC=\n')).toEqual({ A: '1', B: 'two', C: '' });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `npm test -- seed`
Expected: FAIL, modules not found.

- [ ] **Step 3: Write `scripts/lib/env.ts`**

```ts
import { readFileSync } from 'node:fs';

export function parseEnv(text: string): Record<string, string> {
  const out: Record<string, string> = {};
  for (const line of text.split('\n')) {
    const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$/);
    if (m) out[m[1]!] = m[2]!.replace(/^(['"])(.*)\1$/, '$2');
  }
  return out;
}

/** Later files win. Missing files are skipped. Values are never logged. */
export function loadEnv(...files: URL[]): Record<string, string> {
  let merged: Record<string, string> = {};
  for (const f of files) {
    try {
      merged = { ...merged, ...parseEnv(readFileSync(f, 'utf8')) };
    } catch {
      /* file absent */
    }
  }
  return merged;
}
```

- [ ] **Step 4: Write `scripts/lib/admin.ts`**

If Task 0 Step 6 found that `project_id:key` is the working Basic-auth pair, swap the credentials in `createAdmin`.

```ts
import type { Kind, PlanStep } from '../../catalog/plan';

export interface AdminResponse { status: number; body: unknown }
export interface Admin {
  call(method: 'GET' | 'POST' | 'PUT', path: string, body?: unknown): Promise<AdminResponse>;
}

export class SeedError extends Error {
  constructor(public step: PlanStep, public res: AdminResponse) {
    super(`${step.kind} ${step.key}: HTTP ${res.status} ${JSON.stringify(res.body)}`);
  }
}

const PATHS: Record<Kind, { collection: string; one: (key: string) => string }> = {
  group: { collection: '/items/groups', one: (k) => `/items/groups/${k}` },
  currency: { collection: '/items/virtual_currency', one: (k) => `/items/virtual_currency/sku/${k}` },
  package: { collection: '/items/virtual_currency/package', one: (k) => `/items/virtual_currency/package/sku/${k}` },
  item: { collection: '/items/virtual_items', one: (k) => `/items/virtual_items/sku/${k}` },
  bundle: { collection: '/items/bundle', one: (k) => `/items/bundle/sku/${k}` },
};

export function createAdmin(cfg: { merchantId: string; projectId: string; apiKey: string }, f: typeof fetch = fetch): Admin {
  const base = `https://store.xsolla.com/api/v2/project/${cfg.projectId}/admin`;
  const auth = `Basic ${Buffer.from(`${cfg.merchantId}:${cfg.apiKey}`).toString('base64')}`;
  return {
    async call(method, path, body) {
      const res = await f(base + path, {
        method,
        headers: { Authorization: auth, 'Content-Type': 'application/json' },
        body: body === undefined ? undefined : JSON.stringify(body),
      });
      const text = await res.text();
      let parsed: unknown = undefined;
      try { parsed = text ? JSON.parse(text) : undefined; } catch { parsed = text; }
      return { status: res.status, body: parsed };
    },
  };
}

const ok = (s: number) => s >= 200 && s < 300;

export async function upsert(admin: Admin, step: PlanStep, apply: boolean): Promise<'create' | 'update'> {
  const paths = PATHS[step.kind];
  const existing = await admin.call('GET', paths.one(step.key));
  if (existing.status !== 200 && existing.status !== 404) throw new SeedError(step, existing);
  const exists = existing.status === 200;
  if (!apply) return exists ? 'update' : 'create';
  const res = exists
    ? await admin.call('PUT', paths.one(step.key), step.payload)
    : await admin.call('POST', paths.collection, step.payload);
  if (!ok(res.status)) throw new SeedError(step, res);
  return exists ? 'update' : 'create';
}

export const missingSkus = (expected: string[], found: string[]) => {
  const have = new Set(found);
  return expected.filter((s) => !have.has(s));
};
```

- [ ] **Step 5: Write `scripts/seed-catalog.ts`**

```ts
import { buildPlan } from '../catalog/plan';
import { fetchCatalog } from '../src/api/store';
import { createAdmin, missingSkus, upsert, SeedError } from './lib/admin';
import { loadEnv } from './lib/env';

const args = process.argv.slice(2);
const apply = args.includes('--apply');
const verify = args.includes('--verify');

const env = loadEnv(
  new URL('../../../.env', import.meta.url), // repo root
  new URL('../.env', import.meta.url), // example dir, wins
);
const need = (k: string) => {
  const v = env[k] ?? process.env[k];
  if (!v) { console.error(`Missing ${k} in .env`); process.exit(2); }
  return v;
};
const projectId = need('XSOLLA_PROJECT_ID');
const plan = buildPlan();

async function main() {
  if (verify) {
    const found = (await fetchCatalog(projectId, 'en')).map((i) => i.sku);
    const expected = plan.filter((s) => s.expectInStore).map((s) => s.key);
    const missing = missingSkus(expected, found);
    console.log(`public catalog: ${expected.length - missing.length}/${expected.length} expected SKUs present`);
    if (missing.length) { console.log('missing:', missing.join(', ')); process.exit(1); }
    return;
  }

  const admin = createAdmin({ merchantId: need('XSOLLA_MERCHANT_ID'), projectId, apiKey: need('XSOLLA_PROJECT_API_KEY') });
  console.log(`${apply ? 'APPLY' : 'DRY RUN'} against project ${projectId}: ${plan.length} entities`);
  const tally = { create: 0, update: 0 };
  for (const s of plan) {
    try {
      const action = await upsert(admin, s, apply);
      tally[action]++;
      console.log(`${apply ? '' : 'would '}${action.padEnd(6)} ${s.kind.padEnd(8)} ${s.key}`);
    } catch (e) {
      if (e instanceof SeedError) { console.error(`STOP: ${e.message}`); process.exit(1); }
      throw e;
    }
  }
  console.log(`done: ${tally.create} create, ${tally.update} update${apply ? '' : ' (nothing written; rerun with --apply)'}`);
}

main();
```

- [ ] **Step 6: Run unit tests**

Run: `npm test`
Expected: all pass.

- [ ] **Step 7: Dry run against the real project (read-only)**

Run: `npm run seed`
Expected: 37 lines `would create ...` (no entities exist yet), final line `done: 37 create, 0 update (nothing written; rerun with --apply)`. Any HTTP error stops the run and prints status and body (no secrets).

- [ ] **Step 8: Ask the user to confirm before writing**

Show the dry-run summary and ask: "Apply 37 entities to sandbox project 316665?" Do not run `--apply` without an explicit yes.

- [ ] **Step 9: Apply, fixing builder/contract mismatches as they surface**

Run: `npm run seed -- --apply`
Expected: 37 lines `create ...`. On a 422, read the printed body, fix the matching builder in `catalog/payloads.ts` and its assertion in `tests/payloads.test.ts` in the same change, run `npm test`, and rerun. The script is idempotent, so reruns update what already exists. Record each fix as a row in `CONTRACTS.md`.

- [ ] **Step 10: Verify against the public catalog**

Run: `npm run seed -- --verify`
Expected: `public catalog: N/N expected SKUs present` with exit code 0. `expectInStore` excludes the windowed pass and Founder's Pack, the hidden title, and both currencies.

---

### Task 5: Auth and cart plumbing

**Files:**
- Create: `src/auth/types.ts`, `src/auth/session.ts`, `src/auth/oauth.ts`, `src/auth/AuthContext.tsx`, `src/cart/headers.ts`, `src/cart/cartApi.ts`, `src/cart/merge.ts`, `src/cart/useCart.ts`
- Test: `tests/auth.test.ts`, `tests/cart.test.ts`

**Interfaces:**
- Consumes: `storeBase`, `Money` (Task 3), `config`, `loginConfigured` (Task 3), `LOGIN_LOCALE`.
- Produces:
  - `type Session = { accessToken: string; refreshToken?: string; expiresAt: number }`
  - `newState(): string`, `parseCallback(search: string, expectedState: string | null): string` (returns the `code`, throws otherwise)
  - `exchangeCode(p: { clientId; code; redirectUri }, f?, now?): Promise<Session>`, `refreshSession(p: { clientId; refreshToken }, f?, now?): Promise<Session>`, `isExpired(s: Session | null, now?: number, skewMs?: number): boolean`
  - `guestId(storage, uuid?): string`, `authHeaders(session, guest): Record<string,string>`
  - `interface Cart { cartId: string; items: CartLine[]; total?: Money }`, `CartLine = { sku; name; quantity; price?: Money; imageUrl?: string }`
  - `createCartApi(projectId, getHeaders: () => Record<string,string>, f?): CartApi` with `get/setQuantity/remove/clear`
  - `mergeGuestCart(guest: CartApi, user: CartApi): Promise<void>`
  - `useAuth(): AuthState`, `AuthProvider({ onLogin })`, `useCart(): { cart, busy, add(sku), remove(sku), clear(), refresh() }`

- [ ] **Step 1: Write the failing tests**

`tests/auth.test.ts`:

```ts
import { describe, expect, test } from 'vitest';
import { exchangeCode, isExpired, newState, parseCallback, refreshSession } from '../src/auth/oauth';

const json = (o: unknown, status = 200) => new Response(JSON.stringify(o), { status });

describe('parseCallback', () => {
  test('returns the code when state matches', () => {
    expect(parseCallback('?code=abc&state=s1', 's1')).toBe('abc');
  });
  test('rejects state mismatch, missing code, and provider errors', () => {
    expect(() => parseCallback('?code=abc&state=bad', 's1')).toThrow(/state/i);
    expect(() => parseCallback('?code=abc', null)).toThrow(/state/i);
    expect(() => parseCallback('?state=s1', 's1')).toThrow(/code/i);
    expect(() => parseCallback('?error=access_denied&state=s1', 's1')).toThrow(/access_denied/);
  });
  test('newState is random and non-trivial', () => {
    expect(newState()).not.toBe(newState());
    expect(newState().length).toBeGreaterThanOrEqual(16);
  });
});

describe('token requests', () => {
  test('exchangeCode posts form fields and maps expiry', async () => {
    let seen: { url: string; body: string } | undefined;
    const f = (async (url: string, init: RequestInit) => {
      seen = { url, body: String(init.body) };
      return json({ access_token: 'A', refresh_token: 'R', expires_in: 3600 });
    }) as unknown as typeof fetch;
    const s = await exchangeCode({ clientId: '7', code: 'c', redirectUri: 'http://x/cb' }, f, () => 1000);
    expect(seen!.url).toBe('https://login.xsolla.com/api/oauth2/token');
    const p = new URLSearchParams(seen!.body);
    expect(Object.fromEntries(p)).toEqual({ grant_type: 'authorization_code', client_id: '7', code: 'c', redirect_uri: 'http://x/cb' });
    expect(s).toEqual({ accessToken: 'A', refreshToken: 'R', expiresAt: 1000 + 3600 * 1000 });
  });

  test('refresh keeps the old refresh token when none is returned', async () => {
    const f = (async () => json({ access_token: 'B', expires_in: 60 })) as unknown as typeof fetch;
    const s = await refreshSession({ clientId: '7', refreshToken: 'R1' }, f, () => 0);
    expect(s.refreshToken).toBe('R1');
  });

  test('non-2xx throws', async () => {
    const f = (async () => json({}, 400)) as unknown as typeof fetch;
    await expect(exchangeCode({ clientId: '7', code: 'c', redirectUri: 'x' }, f)).rejects.toThrow(/400/);
  });
});

test('isExpired with skew; null session counts as expired', () => {
  expect(isExpired(null)).toBe(true);
  expect(isExpired({ accessToken: 'a', expiresAt: 100_000 }, 0, 60_000)).toBe(false);
  expect(isExpired({ accessToken: 'a', expiresAt: 50_000 }, 0, 60_000)).toBe(true);
});
```

`tests/cart.test.ts`:

```ts
import { describe, expect, test } from 'vitest';
import { authHeaders, guestId } from '../src/cart/headers';
import { createCartApi, type Cart, type CartApi } from '../src/cart/cartApi';
import { mergeGuestCart } from '../src/cart/merge';

const mem = () => {
  const m = new Map<string, string>();
  return { getItem: (k: string) => m.get(k) ?? null, setItem: (k: string, v: string) => void m.set(k, v) };
};

test('guestId is stable across calls and reloads', () => {
  const s = mem();
  const a = guestId(s, () => 'uuid-1');
  expect(guestId(s, () => 'uuid-2')).toBe(a);
});

test('authHeaders: Bearer when logged in, guest id otherwise', () => {
  expect(authHeaders(null, 'g1')).toEqual({ 'x-unauthorized-id': 'g1' });
  expect(authHeaders({ accessToken: 'T', expiresAt: 1 }, 'g1')).toEqual({ Authorization: 'Bearer T' });
});

test('cart api: get normalizes, PUT item sends quantity, headers always attached', async () => {
  const calls: { url: string; method: string; body?: string; h: Record<string, string> }[] = [];
  const f = (async (url: string, init: RequestInit = {}) => {
    calls.push({ url, method: init.method ?? 'GET', body: init.body as string | undefined, h: init.headers as Record<string, string> });
    if ((init.method ?? 'GET') === 'GET') {
      return new Response(JSON.stringify({
        cart_id: 'c1',
        items: [{ sku: 'cores_500', name: 'Core Cache', quantity: 2, price: { amount: '4.99', amount_without_discount: '4.99', currency: 'USD' }, image_url: 'u' }],
        price: { amount: '9.98', amount_without_discount: '9.98', currency: 'USD' },
      }), { status: 200 });
    }
    return new Response(null, { status: 204 });
  }) as unknown as typeof fetch;
  const api = createCartApi('316665', () => ({ 'x-unauthorized-id': 'g1' }), f);
  const cart = await api.get();
  expect(cart.cartId).toBe('c1');
  expect(cart.items[0]).toMatchObject({ sku: 'cores_500', quantity: 2 });
  expect(cart.total?.amount).toBe(9.98);
  await api.setQuantity('cores_500', 3);
  expect(calls[1]).toMatchObject({ method: 'PUT', body: JSON.stringify({ quantity: 3 }) });
  expect(calls[1]!.url).toContain('/cart/item/cores_500');
  expect(calls.every((c) => c.h['x-unauthorized-id'] === 'g1')).toBe(true);
});

describe('mergeGuestCart', () => {
  const line = (sku: string, quantity: number) => ({ sku, name: sku, quantity });
  const fake = (items: ReturnType<typeof line>[], failOn?: string) => {
    const log: string[] = [];
    const state = new Map(items.map((i) => [i.sku, i.quantity]));
    const api: CartApi = {
      async get(): Promise<Cart> { return { cartId: 'c', items: [...state].map(([sku, q]) => line(sku, q)) }; },
      async setQuantity(sku, q) { if (sku === failOn) throw new Error('boom'); state.set(sku, q); log.push(`set ${sku}=${q}`); },
      async remove(sku) { state.delete(sku); },
      async clear() { state.clear(); log.push('clear'); },
    };
    return { api, log, state };
  };

  test('adds guest lines on top of the account cart and clears the guest cart', async () => {
    const guest = fake([line('cores_500', 1), line('bundle_rime_hunter', 1)]);
    const user = fake([line('cores_500', 2)]);
    await mergeGuestCart(guest.api, user.api);
    expect(user.state.get('cores_500')).toBe(3);
    expect(user.state.get('bundle_rime_hunter')).toBe(1);
    expect(guest.state.size).toBe(0);
  });

  test('an empty guest cart is a no-op', async () => {
    const guest = fake([]);
    const user = fake([line('cores_500', 2)]);
    await mergeGuestCart(guest.api, user.api);
    expect(user.log).toEqual([]);
    expect(guest.log).toEqual([]);
  });

  test('a failure midway leaves the guest cart intact (no lost items)', async () => {
    const guest = fake([line('cores_500', 1), line('bundle_rime_hunter', 1)]);
    const user = fake([]);
    await expect(mergeGuestCart(guest.api, new Proxy(user.api, {}) && fake([], 'bundle_rime_hunter').api)).rejects.toThrow('boom');
    expect(guest.state.size).toBe(2);
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `npm test`
Expected: FAIL, modules under `src/auth` and `src/cart` not found.

- [ ] **Step 3: Write the auth modules**

`src/auth/types.ts`:

```ts
export interface Session { accessToken: string; refreshToken?: string; expiresAt: number }
```

`src/auth/oauth.ts`:

```ts
import type { Session } from './types';

const TOKEN_URL = 'https://login.xsolla.com/api/oauth2/token';

export function newState(): string {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
}

/** Returns the authorization code, or throws. `expectedState` is what we stored before opening the widget. */
export function parseCallback(search: string, expectedState: string | null): string {
  const p = new URLSearchParams(search);
  const error = p.get('error');
  if (error) throw new Error(`Login failed: ${error}`);
  if (!expectedState || p.get('state') !== expectedState) throw new Error('Login failed: state mismatch');
  const code = p.get('code');
  if (!code) throw new Error('Login failed: missing code');
  return code;
}

async function tokenRequest(params: Record<string, string>, f: typeof fetch, now: () => number, prevRefresh?: string): Promise<Session> {
  const res = await f(TOKEN_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams(params),
  });
  if (!res.ok) throw new Error(`Login token request failed: ${res.status}`);
  const j = await res.json();
  return {
    accessToken: j.access_token,
    refreshToken: j.refresh_token ?? prevRefresh,
    expiresAt: now() + Number(j.expires_in) * 1000,
  };
}

export const exchangeCode = (
  p: { clientId: string; code: string; redirectUri: string }, f: typeof fetch = fetch, now = Date.now,
) => tokenRequest({ grant_type: 'authorization_code', client_id: p.clientId, code: p.code, redirect_uri: p.redirectUri }, f, now);

export const refreshSession = (
  p: { clientId: string; refreshToken: string }, f: typeof fetch = fetch, now = Date.now,
) => tokenRequest({ grant_type: 'refresh_token', client_id: p.clientId, refresh_token: p.refreshToken }, f, now, p.refreshToken);

export const isExpired = (s: Session | null, now = Date.now(), skewMs = 60_000) =>
  !s || s.expiresAt - skewMs <= now;
```

`src/auth/session.ts`:

```ts
import type { Session } from './types';

const KEY = 'voidwall.session';
export const STATE_KEY = 'voidwall.oauthState';

export function loadSession(storage: Storage = sessionStorage): Session | null {
  try {
    const raw = storage.getItem(KEY);
    const s = raw ? (JSON.parse(raw) as Session) : null;
    return s && typeof s.accessToken === 'string' && typeof s.expiresAt === 'number' ? s : null;
  } catch {
    return null;
  }
}
export const saveSession = (s: Session | null, storage: Storage = sessionStorage) =>
  s ? storage.setItem(KEY, JSON.stringify(s)) : storage.removeItem(KEY);
```

Tokens live in `sessionStorage` (tab-scoped, cleared on close), not `localStorage`.

`src/auth/AuthContext.tsx`:

```tsx
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { Widget } from '@xsolla/login-sdk';
import { config, loginConfigured } from '../config';
import { LOGIN_LOCALE, type Locale } from '../i18n/locales';
import { authHeaders, guestId } from '../cart/headers';
import { exchangeCode, newState, parseCallback, refreshSession } from './oauth';
import { STATE_KEY, loadSession, saveSession } from './session';
import type { Session } from './types';

export interface AuthState {
  session: Session | null;
  configured: boolean;
  login(): void;
  logout(): void;
  headers(): Record<string, string>;
}

const Ctx = createContext<AuthState | null>(null);
export const useAuth = () => {
  const v = useContext(Ctx);
  if (!v) throw new Error('useAuth outside AuthProvider');
  return v;
};

const redirectUri = () => `${location.origin}/auth/callback`;

export function AuthProvider({ locale, onLogin, children }: { locale: Locale; onLogin?: (s: Session) => Promise<void>; children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(() => loadSession());
  const onLoginRef = useRef(onLogin);
  onLoginRef.current = onLogin;

  const set = useCallback((s: Session | null) => { saveSession(s); setSession(s); }, []);

  // Finish the OAuth redirect.
  useEffect(() => {
    if (location.pathname !== '/auth/callback') return;
    (async () => {
      try {
        const code = parseCallback(location.search, sessionStorage.getItem(STATE_KEY));
        sessionStorage.removeItem(STATE_KEY);
        const s = await exchangeCode({ clientId: config.loginClientId, code, redirectUri: redirectUri() });
        set(s);
        await onLoginRef.current?.(s);
      } catch (e) {
        console.error(e);
      } finally {
        history.replaceState(null, '', '/');
      }
    })();
  }, [set]);

  // Refresh a minute before expiry so Store calls never 401 mid-checkout.
  useEffect(() => {
    if (!session?.refreshToken) return;
    const wait = Math.max(session.expiresAt - Date.now() - 60_000, 0);
    const t = setTimeout(async () => {
      try { set(await refreshSession({ clientId: config.loginClientId, refreshToken: session.refreshToken! })); }
      catch { set(null); }
    }, wait);
    return () => clearTimeout(t);
  }, [session, set]);

  const value = useMemo<AuthState>(() => ({
    session,
    configured: loginConfigured,
    login() {
      if (!loginConfigured) return;
      const state = newState();
      sessionStorage.setItem(STATE_KEY, state);
      new Widget({
        projectId: config.loginProjectId,
        preferredLocale: LOGIN_LOCALE[locale],
        clientId: config.loginClientId,
        responseType: 'code',
        state,
        redirectUri: redirectUri(),
        scope: 'offline email',
      }).open();
    },
    logout: () => set(null),
    headers: () => authHeaders(session, guestId(localStorage)),
  }), [session, locale, set]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}
```

- [ ] **Step 4: Confirm the Widget API against the installed SDK**

Open `node_modules/@xsolla/login-sdk` type definitions. Confirm the `Widget` constructor options and that `open()` takes no required argument (the skill's snippet shows `open(element)`). Adjust the call in `AuthContext.tsx` to the real signature.
Expected: `npx tsc --noEmit` passes once Task 6's files exist; for now `npx tsc --noEmit -p .` reports no errors in `src/auth`.

- [ ] **Step 5: Write the cart modules**

`src/cart/headers.ts`:

```ts
import type { Session } from '../auth/types';

export function guestId(storage: Pick<Storage, 'getItem' | 'setItem'>, uuid: () => string = () => crypto.randomUUID()): string {
  const KEY = 'voidwall.guestId';
  const existing = storage.getItem(KEY);
  if (existing) return existing;
  const fresh = uuid();
  storage.setItem(KEY, fresh);
  return fresh;
}

export const authHeaders = (session: Session | null, guest: string): Record<string, string> =>
  session ? { Authorization: `Bearer ${session.accessToken}` } : { 'x-unauthorized-id': guest };
```

`src/cart/cartApi.ts`:

```ts
import { storeBase, type Money } from '../api/store';

export interface CartLine { sku: string; name: string; quantity: number; price?: Money; imageUrl?: string }
export interface Cart { cartId: string; items: CartLine[]; total?: Money }
export interface CartApi {
  get(): Promise<Cart>;
  setQuantity(sku: string, quantity: number): Promise<void>;
  remove(sku: string): Promise<void>;
  clear(): Promise<void>;
}

const money = (p: any): Money | undefined =>
  p ? { amount: Number(p.amount), amountWithoutDiscount: Number(p.amount_without_discount ?? p.amount), currency: p.currency } : undefined;

export function createCartApi(projectId: string, getHeaders: () => Record<string, string>, f: typeof fetch = fetch): CartApi {
  const base = `${storeBase(projectId)}/cart`;
  const send = async (method: string, path: string, body?: unknown) => {
    const res = await f(`${base}${path}`, {
      method,
      headers: { 'Content-Type': 'application/json', ...getHeaders() },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`Cart ${method} ${path} failed: ${res.status}`);
    return res;
  };
  return {
    async get() {
      const j = await (await send('GET', '')).json();
      return {
        cartId: j.cart_id,
        items: (j.items ?? []).map((i: any) => ({
          sku: i.sku, name: i.name, quantity: i.quantity, price: money(i.price), imageUrl: i.image_url ?? undefined,
        })),
        total: money(j.price),
      };
    },
    async setQuantity(sku, quantity) { await send('PUT', `/item/${encodeURIComponent(sku)}`, { quantity }); },
    async remove(sku) { await send('DELETE', `/item/${encodeURIComponent(sku)}`); },
    async clear() { await send('PUT', '/clear'); },
  };
}
```

`src/cart/merge.ts`:

```ts
import type { CartApi } from './cartApi';

/**
 * Carry guest lines into the account cart. The guest cart is cleared only after every line landed,
 * so a failure midway loses nothing and a retry re-reads the account cart before adding.
 */
export async function mergeGuestCart(guest: CartApi, user: CartApi): Promise<void> {
  const guestCart = await guest.get();
  if (guestCart.items.length === 0) return;
  const existing = new Map((await user.get()).items.map((i) => [i.sku, i.quantity]));
  for (const line of guestCart.items) {
    await user.setQuantity(line.sku, (existing.get(line.sku) ?? 0) + line.quantity);
  }
  await guest.clear();
}
```

`src/cart/useCart.ts`:

```ts
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useAuth } from '../auth/AuthContext';
import { config } from '../config';
import { createCartApi, type Cart } from './cartApi';

export function useCart() {
  const auth = useAuth();
  const api = useMemo(() => createCartApi(config.projectId, auth.headers), [auth]);
  const [cart, setCart] = useState<Cart | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(async (fn: () => Promise<unknown>) => {
    setBusy(true); setError(null);
    try { await fn(); setCart(await api.get()); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }, [api]);

  const refresh = useCallback(() => run(async () => {}), [run]);
  useEffect(() => { void refresh(); }, [refresh, auth.session]);

  return {
    cart, busy, error, refresh,
    add: (sku: string) => run(async () => {
      const current = (await api.get()).items.find((i) => i.sku === sku)?.quantity ?? 0;
      await api.setQuantity(sku, current + 1);
    }),
    remove: (sku: string) => run(() => api.remove(sku)),
    clear: () => run(() => api.clear()),
  };
}
```

- [ ] **Step 6: Fix the failing-merge test setup, then run tests**

In `tests/cart.test.ts`, the third `mergeGuestCart` test builds its failing user cart inline. Replace its `await expect(...)` line with this clearer form:

```ts
    const failingUser = fake([], 'bundle_rime_hunter');
    await expect(mergeGuestCart(guest.api, failingUser.api)).rejects.toThrow('boom');
    expect(guest.state.size).toBe(2);
```

Run: `npm test`
Expected: all pass, including the merge-failure test (guest cart keeps both lines).

---

### Task 6: Storefront UI

**Files:**
- Create: `src/i18n/ui.ts`, `src/theme.css`, `src/main.tsx` (replace placeholder), `src/App.tsx`, `src/components/Header.tsx`, `Hero.tsx`, `ItemCard.tsx`, `Section.tsx`, `BundleStrip.tsx`, `CartDrawer.tsx`, `Footer.tsx`
- Test: `tests/ui.test.ts`

**Interfaces:**
- Consumes: Tasks 1, 3, 5.
- Produces: the running app. `UI: Record<Locale, Record<UiKey, string>>`, `useLocale()`.

- [ ] **Step 1: Write the failing test for UI strings**

`tests/ui.test.ts`:

```ts
import { expect, test } from 'vitest';
import { LOCALES } from '../catalog/types';
import { UI } from '../src/i18n/ui';

test('every locale defines exactly the same keys, with no empty values or em dashes', () => {
  const keys = Object.keys(UI.en).sort();
  for (const l of LOCALES) {
    expect(Object.keys(UI[l]).sort(), l).toEqual(keys);
    for (const [k, v] of Object.entries(UI[l])) {
      expect(v.length, `${l}.${k}`).toBeGreaterThan(0);
      expect(v).not.toContain('—');
    }
  }
});
```

Run: `npm test -- ui`
Expected: FAIL, `src/i18n/ui` not found.

- [ ] **Step 2: Write `src/i18n/ui.ts`**

```ts
import type { Locale } from '../../catalog/types';

const en = {
  tagline: 'Hold the line.',
  heroSub: 'Skins, gear, boosters and Cores for Wardens on the Frontier.',
  shopNow: 'Shop now',
  addToCart: 'Add to cart',
  inCart: 'In cart',
  buyWithCores: 'Buy with Cores',
  unavailable: 'Unavailable',
  comingSoon: 'Coming soon',
  featured: 'Featured bundles',
  valueOf: 'Value',
  cart: 'Cart',
  cartEmpty: 'Your cart is empty.',
  remove: 'Remove',
  total: 'Total',
  checkout: 'Checkout',
  signInToCheckout: 'Sign in to check out',
  login: 'Sign in',
  logout: 'Sign out',
  loginUnavailable: 'Sign-in is not configured',
  promo: 'Promo code',
  apply: 'Apply',
  loading: 'Loading the catalog...',
  loadError: 'Could not load the catalog. Please try again.',
  balance: 'Cores',
  notEnoughCores: 'Not enough Cores. Buy a Core pack first.',
  purchased: 'Purchased!',
  close: 'Close',
  support: 'Support',
  footer: 'Meridian Foundry, Lisbon. All rights reserved.',
  sandboxNote: 'Sandbox mode: no real charges.',
} as const;
export type UiKey = keyof typeof en;

export const UI: Record<Locale, Record<UiKey, string>> = {
  en,
  fr: {
    tagline: 'Tenez la ligne.', heroSub: 'Skins, équipement, boosters et Cores pour les Gardiens de la Frontière.',
    shopNow: 'Voir la boutique', addToCart: 'Ajouter au panier', inCart: 'Dans le panier', buyWithCores: 'Acheter avec des Cores',
    unavailable: 'Indisponible', comingSoon: 'Bientôt disponible', featured: 'Packs en vedette', valueOf: 'Valeur',
    cart: 'Panier', cartEmpty: 'Votre panier est vide.', remove: 'Retirer', total: 'Total', checkout: 'Payer',
    signInToCheckout: 'Connectez-vous pour payer', login: 'Connexion', logout: 'Déconnexion',
    loginUnavailable: "La connexion n'est pas configurée", promo: 'Code promo', apply: 'Appliquer',
    loading: 'Chargement du catalogue...', loadError: 'Impossible de charger le catalogue. Réessayez.',
    balance: 'Cores', notEnoughCores: "Pas assez de Cores. Achetez d'abord un pack de Cores.", purchased: 'Achat effectué !',
    close: 'Fermer', support: 'Assistance', footer: 'Meridian Foundry, Lisbonne. Tous droits réservés.',
    sandboxNote: 'Mode bac à sable : aucun débit réel.',
  },
  de: {
    tagline: 'Haltet die Linie.', heroSub: 'Skins, Ausrüstung, Booster und Cores für Wächter an der Grenze.',
    shopNow: 'Zum Shop', addToCart: 'In den Warenkorb', inCart: 'Im Warenkorb', buyWithCores: 'Mit Cores kaufen',
    unavailable: 'Nicht verfügbar', comingSoon: 'Demnächst', featured: 'Empfohlene Bundles', valueOf: 'Wert',
    cart: 'Warenkorb', cartEmpty: 'Dein Warenkorb ist leer.', remove: 'Entfernen', total: 'Gesamt', checkout: 'Zur Kasse',
    signInToCheckout: 'Zum Bezahlen anmelden', login: 'Anmelden', logout: 'Abmelden',
    loginUnavailable: 'Anmeldung ist nicht konfiguriert', promo: 'Promo-Code', apply: 'Einlösen',
    loading: 'Katalog wird geladen...', loadError: 'Katalog konnte nicht geladen werden. Bitte erneut versuchen.',
    balance: 'Cores', notEnoughCores: 'Nicht genug Cores. Kaufe zuerst ein Core-Paket.', purchased: 'Gekauft!',
    close: 'Schließen', support: 'Support', footer: 'Meridian Foundry, Lissabon. Alle Rechte vorbehalten.',
    sandboxNote: 'Sandbox-Modus: keine echten Abbuchungen.',
  },
  ja: {
    tagline: '防衛線を守れ。', heroSub: 'フロンティアのウォーデンのためのスキン、ギア、ブースター、Cores。',
    shopNow: 'ショップへ', addToCart: 'カートに追加', inCart: 'カート内', buyWithCores: 'Coresで購入',
    unavailable: '購入不可', comingSoon: '近日公開', featured: '注目のバンドル', valueOf: '価値',
    cart: 'カート', cartEmpty: 'カートは空です。', remove: '削除', total: '合計', checkout: '購入手続き',
    signInToCheckout: 'ログインして購入', login: 'ログイン', logout: 'ログアウト',
    loginUnavailable: 'ログインは未設定です', promo: 'プロモコード', apply: '適用',
    loading: 'カタログを読み込み中...', loadError: 'カタログを読み込めませんでした。もう一度お試しください。',
    balance: 'Cores', notEnoughCores: 'Coresが足りません。先にCoresパックを購入してください。', purchased: '購入しました!',
    close: '閉じる', support: 'サポート', footer: 'Meridian Foundry、リスボン。無断転載を禁じます。',
    sandboxNote: 'サンドボックスモード: 実際の請求は発生しません。',
  },
  'pt-BR': {
    tagline: 'Segurem a linha.', heroSub: 'Skins, equipamentos, boosters e Cores para Guardiões da Fronteira.',
    shopNow: 'Ir à loja', addToCart: 'Adicionar ao carrinho', inCart: 'No carrinho', buyWithCores: 'Comprar com Cores',
    unavailable: 'Indisponível', comingSoon: 'Em breve', featured: 'Pacotes em destaque', valueOf: 'Valor',
    cart: 'Carrinho', cartEmpty: 'Seu carrinho está vazio.', remove: 'Remover', total: 'Total', checkout: 'Finalizar compra',
    signInToCheckout: 'Entre para finalizar', login: 'Entrar', logout: 'Sair',
    loginUnavailable: 'O login não está configurado', promo: 'Código promocional', apply: 'Aplicar',
    loading: 'Carregando o catálogo...', loadError: 'Não foi possível carregar o catálogo. Tente novamente.',
    balance: 'Cores', notEnoughCores: 'Cores insuficientes. Compre um pacote de Cores primeiro.', purchased: 'Compra concluída!',
    close: 'Fechar', support: 'Suporte', footer: 'Meridian Foundry, Lisboa. Todos os direitos reservados.',
    sandboxNote: 'Modo sandbox: nenhuma cobrança real.',
  },
};
```

Run: `npm test -- ui`
Expected: PASS.

- [ ] **Step 3: Write `src/theme.css`**

```css
:root {
  --void: #0a0e14;
  --hull: #2a3242;
  --cyan: #35e0ff;
  --plasma: #eaf6ff;
  --amber: #ffa63d;
  --violet: #8b6cff;
  --common: #8a93a3;
  --rare: #4d9bff;
  --epic: var(--violet);
  --legendary: var(--amber);
  --radius: 6px;
  font-family: 'Inter', system-ui, sans-serif;
  color: var(--plasma);
  background: var(--void);
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--void) url('/assets/brand/bg.jpg') center / cover fixed; min-height: 100vh; }
h1, h2, h3 { font-family: 'Rajdhani', 'Orbitron', system-ui, sans-serif; letter-spacing: 0.04em; text-transform: uppercase; }
a { color: var(--cyan); }
button {
  font: inherit; cursor: pointer; border-radius: var(--radius); border: 1px solid var(--cyan);
  background: transparent; color: var(--cyan); padding: 0.5rem 0.9rem;
}
button.primary { background: var(--cyan); color: var(--void); font-weight: 700; }
button:disabled { opacity: 0.45; cursor: not-allowed; }
.page { max-width: 1180px; margin: 0 auto; padding: 0 1rem 4rem; }
.header { display: flex; align-items: center; gap: 1rem; padding: 0.75rem 1rem; background: rgba(10, 14, 20, 0.85); position: sticky; top: 0; z-index: 10; backdrop-filter: blur(6px); }
.header img { height: 36px; }
.spacer { flex: 1; }
.hero { position: relative; min-height: 380px; display: grid; align-items: end; margin: 1rem 0 2rem; border-radius: var(--radius); overflow: hidden; background: linear-gradient(0deg, rgba(10, 14, 20, 0.95), rgba(10, 14, 20, 0.1)), url('/assets/brand/hero.jpg') center / cover; }
.hero > div { padding: 2rem; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 1rem; }
.card { background: rgba(42, 50, 66, 0.75); border: 2px solid var(--rim, var(--common)); border-radius: var(--radius); box-shadow: 0 0 14px color-mix(in srgb, var(--rim, var(--common)) 40%, transparent); padding: 0.75rem; display: grid; gap: 0.5rem; }
.card img { width: 100%; aspect-ratio: 1; object-fit: cover; border-radius: 4px; }
.rarity-common { --rim: var(--common); } .rarity-rare { --rim: var(--rare); }
.rarity-epic { --rim: var(--epic); } .rarity-legendary { --rim: var(--legendary); }
.price { font-weight: 700; }
.was { text-decoration: line-through; opacity: 0.6; margin-left: 0.4rem; font-weight: 400; }
.drawer { position: fixed; top: 0; right: 0; bottom: 0; width: min(420px, 100%); background: var(--void); border-left: 1px solid var(--hull); padding: 1rem; overflow: auto; z-index: 20; }
.modal { position: fixed; inset: 0; background: rgba(0, 0, 0, 0.7); display: grid; place-items: center; z-index: 30; }
.modal > div { background: var(--void); border: 1px solid var(--hull); border-radius: var(--radius); padding: 1.25rem; width: min(520px, 94%); max-height: 92vh; overflow: auto; }
.note { opacity: 0.7; font-size: 0.85rem; }
.error { color: var(--amber); }
.footer { border-top: 1px solid var(--hull); padding: 1.5rem 1rem; text-align: center; }
```

- [ ] **Step 4: Write the components**

`src/components/Hero.tsx`:

```tsx
import { UI } from '../i18n/ui';
import type { Locale } from '../i18n/locales';

export function Hero({ locale }: { locale: Locale }) {
  const t = UI[locale];
  return (
    <section className="hero">
      <div>
        <img src="/assets/brand/logo.jpg" alt="Voidwall" height={64} />
        <h1>{t.tagline}</h1>
        <p>{t.heroSub}</p>
        <a href="#shop"><button className="primary">{t.shopNow}</button></a>
      </div>
    </section>
  );
}
```

`src/components/Header.tsx`:

```tsx
import { LOCALES, LOCALE_LABEL, type Locale } from '../i18n/locales';
import { UI } from '../i18n/ui';
import { useAuth } from '../auth/AuthContext';

export function Header({ locale, onLocale, cartCount, onCart }: { locale: Locale; onLocale: (l: Locale) => void; cartCount: number; onCart: () => void }) {
  const t = UI[locale];
  const auth = useAuth();
  return (
    <header className="header">
      <img src="/assets/brand/glyph.jpg" alt="" />
      <strong>VOIDWALL</strong>
      <span className="spacer" />
      <select aria-label="Language" value={locale} onChange={(e) => onLocale(e.target.value as Locale)}>
        {LOCALES.map((l) => <option key={l} value={l}>{LOCALE_LABEL[l]}</option>)}
      </select>
      {auth.session
        ? <button onClick={auth.logout}>{t.logout}</button>
        : <button onClick={auth.login} disabled={!auth.configured} title={auth.configured ? undefined : t.loginUnavailable}>{t.login}</button>}
      <button onClick={onCart}>{t.cart} ({cartCount})</button>
    </header>
  );
}
```

`src/components/ItemCard.tsx`:

```tsx
import { IMAGES } from '../../catalog/catalog';
import { formatMoney, type ShopItem } from '../api/store';
import type { Locale } from '../i18n/locales';
import { UI } from '../i18n/ui';

interface Props {
  item: ShopItem; locale: Locale; inCart: boolean; loggedIn: boolean;
  onAdd: (sku: string) => void; onBuyWithCores: (item: ShopItem) => void;
}

export function ItemCard({ item, locale, inCart, onAdd, onBuyWithCores }: Props) {
  const t = UI[locale];
  const rarity = item.attributes.rarity ?? 'common';
  const img = IMAGES[item.sku] ? `/assets/${IMAGES[item.sku]}` : undefined;
  const hasMoney = Boolean(item.price);
  const discounted = item.price && item.price.amountWithoutDiscount > item.price.amount;
  return (
    <article className={`card rarity-${rarity}`}>
      {img && <img src={img} alt={item.name} loading="lazy" />}
      <h3>{item.name}</h3>
      <p className="note">{item.description}</p>
      <div className="price">
        {hasMoney && formatMoney(item.price, locale)}
        {discounted && <span className="was">{formatMoney({ ...item.price!, amount: item.price!.amountWithoutDiscount }, locale)}</span>}
        {!hasMoney && item.coresPrice !== undefined && `${item.coresPrice.toLocaleString(locale)} ${t.balance}`}
        {!hasMoney && item.coresPrice === undefined && <span className="note">{t.unavailable}</span>}
      </div>
      {hasMoney && <button className="primary" disabled={inCart} onClick={() => onAdd(item.sku)}>{inCart ? t.inCart : t.addToCart}</button>}
      {!hasMoney && item.coresPrice !== undefined && <button className="primary" onClick={() => onBuyWithCores(item)}>{t.buyWithCores}</button>}
      {!hasMoney && item.coresPrice === undefined && <button disabled>{t.unavailable}</button>}
    </article>
  );
}
```

`src/components/Section.tsx`:

```tsx
import { GROUPS } from '../../catalog/catalog';
import type { GroupId } from '../../catalog/types';
import type { ShopItem } from '../api/store';
import type { Locale } from '../i18n/locales';
import { ItemCard } from './ItemCard';

export function Section(props: {
  id: GroupId; items: ShopItem[]; locale: Locale; inCart: Set<string>; loggedIn: boolean;
  onAdd: (sku: string) => void; onBuyWithCores: (item: ShopItem) => void;
}) {
  const group = GROUPS.find((g) => g.id === props.id)!;
  return (
    <section id={props.id}>
      <h2>{group.names[props.locale]}</h2>
      <div className="grid">
        {props.items.map((i) => (
          <ItemCard key={i.sku} item={i} locale={props.locale} loggedIn={props.loggedIn}
            inCart={props.inCart.has(i.sku)} onAdd={props.onAdd} onBuyWithCores={props.onBuyWithCores} />
        ))}
      </div>
    </section>
  );
}
```

`src/components/BundleStrip.tsx`:

```tsx
import { BUNDLES, coresValue } from '../../catalog/catalog';
import type { ShopItem } from '../api/store';
import type { Locale } from '../i18n/locales';
import { UI } from '../i18n/ui';
import { ItemCard } from './ItemCard';

export function BundleStrip({ bundles, locale, inCart, onAdd }: { bundles: ShopItem[]; locale: Locale; inCart: Set<string>; onAdd: (sku: string) => void }) {
  if (bundles.length === 0) return null;
  const t = UI[locale];
  return (
    <section>
      <h2>{t.featured}</h2>
      <div className="grid">
        {bundles.map((b) => {
          const def = BUNDLES.find((d) => d.sku === b.sku);
          return (
            <div key={b.sku}>
              <ItemCard item={b} locale={locale} loggedIn={false} inCart={inCart.has(b.sku)} onAdd={onAdd} onBuyWithCores={() => {}} />
              {def && <p className="note">{t.valueOf}: {coresValue(def).toLocaleString(locale)} {t.balance}</p>}
            </div>
          );
        })}
      </div>
    </section>
  );
}
```

`src/components/Footer.tsx`:

```tsx
import { config } from '../config';
import { UI } from '../i18n/ui';
import type { Locale } from '../i18n/locales';

export function Footer({ locale }: { locale: Locale }) {
  const t = UI[locale];
  return (
    <footer className="footer">
      <p>{t.footer}</p>
      <p><a href={`mailto:${config.supportEmail}`}>{t.support}: {config.supportEmail}</a></p>
      {config.sandbox && <p className="note">{t.sandboxNote}</p>}
    </footer>
  );
}
```

`src/components/CartDrawer.tsx` (the promo field exists only if Task 0 Step 7 question 2 answered yes; if no, delete the promo `<input>` and the `promoCode` prop):

```tsx
import { useState } from 'react';
import { formatMoney } from '../api/store';
import type { Cart } from '../cart/cartApi';
import type { Locale } from '../i18n/locales';
import { UI } from '../i18n/ui';

interface Props {
  cart: Cart | null; locale: Locale; loggedIn: boolean; loginConfigured: boolean; busy: boolean;
  onClose: () => void; onRemove: (sku: string) => void; onLogin: () => void;
  onCheckout: (promoCode?: string) => void;
}

export function CartDrawer({ cart, locale, loggedIn, loginConfigured, busy, onClose, onRemove, onLogin, onCheckout }: Props) {
  const t = UI[locale];
  const [promo, setPromo] = useState('');
  const empty = !cart || cart.items.length === 0;
  return (
    <aside className="drawer" aria-label={t.cart}>
      <button onClick={onClose}>{t.close}</button>
      <h2>{t.cart}</h2>
      {empty && <p>{t.cartEmpty}</p>}
      {cart?.items.map((i) => (
        <div key={i.sku} style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', margin: '0.5rem 0' }}>
          <span style={{ flex: 1 }}>{i.name} × {i.quantity}</span>
          <span>{formatMoney(i.price, locale)}</span>
          <button onClick={() => onRemove(i.sku)} disabled={busy}>{t.remove}</button>
        </div>
      ))}
      {!empty && (
        <>
          <p className="price">{t.total}: {formatMoney(cart!.total, locale)}</p>
          <input placeholder={t.promo} value={promo} onChange={(e) => setPromo(e.target.value)} aria-label={t.promo} />
          {loggedIn
            ? <button className="primary" disabled={busy} onClick={() => onCheckout(promo.trim() || undefined)}>{t.checkout}</button>
            : <button className="primary" disabled={!loginConfigured} onClick={onLogin}>{loginConfigured ? t.signInToCheckout : t.loginUnavailable}</button>}
        </>
      )}
    </aside>
  );
}
```

- [ ] **Step 5: Write `src/App.tsx` and `src/main.tsx`**

`src/App.tsx` (the checkout hook-up is added in Task 7; this version leaves `onCheckout` and `onBuyWithCores` as TODO-free stubs that call the functions Task 7 adds, so write Task 7's `checkout/api.ts` before running the app end to end. For this task, wire them to `() => {}` and keep the Task 7 swap explicit in its Step 6):

```tsx
import { useEffect, useMemo, useState } from 'react';
import { CHARTER } from '../catalog/catalog';
import { fetchCatalog, type ShopItem } from './api/store';
import { byGroup, knownItems, visibleGroups } from './api/view';
import { useAuth } from './auth/AuthContext';
import { BundleStrip } from './components/BundleStrip';
import { CartDrawer } from './components/CartDrawer';
import { Footer } from './components/Footer';
import { Header } from './components/Header';
import { Hero } from './components/Hero';
import { Section } from './components/Section';
import { config } from './config';
import { useCart } from './cart/useCart';
import { resolveLocale, type Locale } from './i18n/locales';
import { UI } from './i18n/ui';

export function useLocale(): [Locale, (l: Locale) => void] {
  const [locale, set] = useState<Locale>(() => resolveLocale(localStorage.getItem('voidwall.locale')));
  return [locale, (l) => { localStorage.setItem('voidwall.locale', l); set(l); }];
}

export function Shop({ locale, onLocale }: { locale: Locale; onLocale: (l: Locale) => void }) {
  const t = UI[locale];
  const auth = useAuth();
  const cart = useCart();
  const [items, setItems] = useState<ShopItem[] | null>(null);
  const [error, setError] = useState(false);
  const [drawer, setDrawer] = useState(false);

  useEffect(() => {
    setError(false);
    fetchCatalog(config.projectId, locale).then((r) => setItems(knownItems(r))).catch(() => setError(true));
  }, [locale]);

  const inCart = useMemo(() => new Set(cart.cart?.items.map((i) => i.sku) ?? []), [cart.cart]);
  const count = cart.cart?.items.reduce((n, i) => n + i.quantity, 0) ?? 0;

  return (
    <>
      <Header locale={locale} onLocale={onLocale} cartCount={count} onCart={() => setDrawer(true)} />
      <main className="page">
        <Hero locale={locale} />
        <div id="shop" />
        {error && <p className="error">{t.loadError}</p>}
        {!items && !error && <p>{t.loading}</p>}
        {items && (
          <>
            <BundleStrip bundles={byGroup(items, 'bundles')} locale={locale} inCart={inCart} onAdd={cart.add} />
            {visibleGroups(items).filter((g) => g.id !== 'bundles').map((g) => (
              <Section key={g.id} id={g.id} items={byGroup(items, g.id)} locale={locale} inCart={inCart}
                loggedIn={Boolean(auth.session)} onAdd={cart.add} onBuyWithCores={() => {}} />
            ))}
            <section>
              <h2>{CHARTER.name}</h2>
              <p className="note">{t.comingSoon}</p>
            </section>
          </>
        )}
      </main>
      <Footer locale={locale} />
      {drawer && (
        <CartDrawer cart={cart.cart} locale={locale} loggedIn={Boolean(auth.session)} loginConfigured={auth.configured}
          busy={cart.busy} onClose={() => setDrawer(false)} onRemove={cart.remove} onLogin={auth.login} onCheckout={() => {}} />
      )}
    </>
  );
}
```

`src/main.tsx`:

```tsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { Shop, useLocale } from './App';
import { AuthProvider } from './auth/AuthContext';
import { createCartApi } from './cart/cartApi';
import { mergeGuestCart } from './cart/merge';
import { authHeaders, guestId } from './cart/headers';
import { config } from './config';
import './theme.css';

function Root() {
  const [locale, setLocale] = useLocale();
  return (
    <AuthProvider
      locale={locale}
      onLogin={async (session) => {
        const guest = createCartApi(config.projectId, () => authHeaders(null, guestId(localStorage)));
        const user = createCartApi(config.projectId, () => authHeaders(session, ''));
        await mergeGuestCart(guest, user);
      }}
    >
      <Shop locale={locale} onLocale={setLocale} />
    </AuthProvider>
  );
}

createRoot(document.getElementById('root')!).render(<StrictMode><Root /></StrictMode>);
```

Note: `useCart` refetches when `auth.session` changes, so the merged account cart appears right after login.

- [ ] **Step 6: Build and run the app against the seeded catalog**

Run: `npm run build`
Expected: type-check and build succeed.

Run: `npm run dev` and open the printed URL.
Expected, checked in a real browser (use the `run` skill or Playwright):
- Hero with logo and key art, dark background.
- Sections render only for non-empty groups: Currency, Turret Skins, Warden Gear, Boosters, Bundles (strip). "Passes and Subscriptions" is absent (windowed until 2026-10-14). No quest fixtures appear.
- Rarity rims differ (rare blue, epic violet, legendary amber).
- Locale switch to `ja` changes headings, UI strings, and item descriptions; reload keeps `ja`.
- Add a Core pack and a bundle to the cart, reload: cart persists; Remove works; total shows.
- Login button is disabled with a tooltip when `VITE_LOGIN_*` are empty.
Report anything that does not match as a defect and fix it before moving on.

---

### Task 7: Checkout (token, Cores purchase, Headless Checkout UI)

**Files:**
- Create: `src/checkout/api.ts`, `src/checkout/sdk.ts`, `src/checkout/CheckoutModal.tsx`, `src/pages/PaymentReturn.tsx`, `src/types/psdk.d.ts`
- Modify: `src/App.tsx` (wire `onCheckout`, `onBuyWithCores`, balance), `src/main.tsx` (route `/payment/return`)
- Test: `tests/checkout.test.ts`

**Interfaces:**
- Consumes: `Session`, `Cart` (Task 5), `PAY_LANGUAGE`, `storeBase`, `config`.
- Produces:
  - `createCartPaymentToken(p: { projectId; cartId; session; language: string; sandbox: boolean; promoCode?: string }, f?): Promise<{ token: string; orderId: number }>`
  - `buyWithCores(p: { projectId; sku; session }, f?): Promise<{ orderId: number }>` (throws `InsufficientCoresError`)
  - `fetchCoresBalance(projectId, session, f?): Promise<number>`
  - `initCheckout(token, language, sandbox)`, `openMethod(ui, paymentMethodId, returnUrl)` in `sdk.ts`

- [ ] **Step 1: Write the failing tests**

`tests/checkout.test.ts`:

```ts
import { describe, expect, test } from 'vitest';
import { InsufficientCoresError, buyWithCores, createCartPaymentToken, fetchCoresBalance } from '../src/checkout/api';

const session = { accessToken: 'JWT', expiresAt: Date.now() + 1e6 };
const json = (o: unknown, status = 200) => new Response(JSON.stringify(o), { status });
type Seen = { url: string; init: RequestInit };
const spy = (res: Response) => {
  const seen: Seen[] = [];
  const f = (async (url: string, init: RequestInit) => { seen.push({ url, init }); return res.clone(); }) as unknown as typeof fetch;
  return { f, seen };
};

describe('createCartPaymentToken (Method 1)', () => {
  test('posts to the cart payment endpoint with Bearer, sandbox and language', async () => {
    const { f, seen } = spy(json({ token: 'TKN', order_id: 42 }));
    const r = await createCartPaymentToken({ projectId: '316665', cartId: 'c1', session, language: 'ja', sandbox: true }, f);
    expect(r).toEqual({ token: 'TKN', orderId: 42 });
    expect(seen[0]!.url).toBe('https://store.xsolla.com/api/v2/project/316665/payment/cart/c1');
    expect((seen[0]!.init.headers as Record<string, string>).Authorization).toBe('Bearer JWT');
    const body = JSON.parse(String(seen[0]!.init.body));
    expect(body.sandbox).toBe(true);
    expect(body.settings.language).toBe('ja');
    expect(body.promo_code).toBeUndefined();
  });

  test('includes promo_code only when provided', async () => {
    const { f, seen } = spy(json({ token: 'T', order_id: 1 }));
    await createCartPaymentToken({ projectId: '1', cartId: 'c', session, language: 'en', sandbox: true, promoCode: 'HELLO' }, f);
    expect(JSON.parse(String(seen[0]!.init.body)).promo_code).toBe('HELLO');
  });

  test('never sends an API key header', async () => {
    const { f, seen } = spy(json({ token: 'T', order_id: 1 }));
    await createCartPaymentToken({ projectId: '1', cartId: 'c', session, language: 'en', sandbox: true }, f);
    expect(JSON.stringify(seen[0]!.init.headers).toLowerCase()).not.toContain('basic');
  });

  test('non-2xx throws with status', async () => {
    const { f } = spy(json({}, 422));
    await expect(createCartPaymentToken({ projectId: '1', cartId: 'c', session, language: 'en', sandbox: true }, f)).rejects.toThrow(/422/);
  });
});

describe('buyWithCores', () => {
  test('posts to the virtual-currency purchase endpoint', async () => {
    const { f, seen } = spy(json({ order_id: 7 }));
    expect(await buyWithCores({ projectId: '316665', sku: 'tether_skin_anchor', session }, f)).toEqual({ orderId: 7 });
    expect(seen[0]!.url).toBe('https://store.xsolla.com/api/v2/project/316665/payment/item/tether_skin_anchor/virtual/cores');
    expect(seen[0]!.init.method).toBe('POST');
  });
  test('a 422 maps to InsufficientCoresError', async () => {
    const { f } = spy(json({ errorCode: 4003 }, 422));
    await expect(buyWithCores({ projectId: '1', sku: 'x', session }, f)).rejects.toBeInstanceOf(InsufficientCoresError);
  });
});

test('fetchCoresBalance reads the cores line, 0 when absent', async () => {
  expect(await fetchCoresBalance('1', session, spy(json({ items: [{ sku: 'cores', amount: 1200 }] })).f)).toBe(1200);
  expect(await fetchCoresBalance('1', session, spy(json({ items: [] })).f)).toBe(0);
});
```

Run: `npm test -- checkout`
Expected: FAIL, `src/checkout/api` not found.

- [ ] **Step 2: Write `src/checkout/api.ts`**

Before finalizing the 422 mapping, check the response code for "not enough virtual currency" in the Create-order-for-virtual-currency docs (`skills/catalog-design/references/purchase-and-tracking.md` links it) and refine the mapping to that specific `errorCode` if the docs list one.

```ts
import { storeBase } from '../api/store';
import type { Session } from '../auth/types';

export class InsufficientCoresError extends Error {
  constructor() { super('Not enough Cores'); }
}

const bearer = (s: Session) => ({ Authorization: `Bearer ${s.accessToken}`, 'Content-Type': 'application/json' });

/** Token Method 1: the browser asks the Store API, so the API key is never involved. */
export async function createCartPaymentToken(
  p: { projectId: string; cartId: string; session: Session; language: string; sandbox: boolean; promoCode?: string },
  f: typeof fetch = fetch,
): Promise<{ token: string; orderId: number }> {
  const res = await f(`${storeBase(p.projectId)}/payment/cart/${p.cartId}`, {
    method: 'POST',
    headers: bearer(p.session),
    body: JSON.stringify({
      sandbox: p.sandbox,
      settings: { language: p.language },
      ...(p.promoCode ? { promo_code: p.promoCode } : {}),
    }),
  });
  if (!res.ok) throw new Error(`Payment token request failed: ${res.status}`);
  const j = await res.json();
  return { token: j.token, orderId: j.order_id };
}

export async function buyWithCores(
  p: { projectId: string; sku: string; session: Session }, f: typeof fetch = fetch,
): Promise<{ orderId: number }> {
  const res = await f(`${storeBase(p.projectId)}/payment/item/${encodeURIComponent(p.sku)}/virtual/cores`, {
    method: 'POST', headers: bearer(p.session), body: JSON.stringify({}),
  });
  if (res.status === 422) throw new InsufficientCoresError();
  if (!res.ok) throw new Error(`Cores purchase failed: ${res.status}`);
  const j = await res.json();
  return { orderId: j.order_id };
}

export async function fetchCoresBalance(projectId: string, session: Session, f: typeof fetch = fetch): Promise<number> {
  const res = await f(`${storeBase(projectId)}/user/virtual_currency_balance`, { headers: bearer(session) });
  if (!res.ok) throw new Error(`Balance request failed: ${res.status}`);
  const j = await res.json();
  return Number((j.items ?? []).find((i: any) => i.sku === 'cores')?.amount ?? 0);
}
```

Run: `npm test -- checkout`
Expected: PASS.

- [ ] **Step 3: Read the redirect reference before writing the dispatcher**

Read `skills/headless-checkout-integration/references/redirect-flow.md` and confirm: the `psdk-redirect` attribute name and what object it expects for `data-redirect` (the plan assumes `action.data`), and the `isNewWindowRequired` rule. Adjust the `redirect` branch in the next step to match.

- [ ] **Step 4: Write `src/types/psdk.d.ts` and `src/checkout/sdk.ts`**

`src/types/psdk.d.ts`:

```ts
import 'react';

declare module 'react' {
  namespace JSX {
    interface IntrinsicElements {
      'psdk-total': any;
      'psdk-legal': any;
      'psdk-payment-methods': any;
      'psdk-payment-form-messages': any;
      'psdk-status': any;
    }
  }
}
```

`src/checkout/sdk.ts` (follows `headless-checkout-integration` Phases 1 and 2: `credit-card-form`, `payment-status`, `payment-methods-list`):

```ts
import { headlessCheckout } from '@xsolla/pay-station-sdk';

export interface CheckoutUi {
  fieldsEl: HTMLElement;
  statusEl: HTMLElement;
  errorEl: HTMLElement;
  setLoading(on: boolean): void;
}

type Field = { name: string; type: string; isMandatory?: string };

// Styles for the cross-origin secure card iframes. Must be set before setToken().
const SECURE_CSS = `
  input { background:#0a0e14; color:#eaf6ff; border:1px solid #2a3242; border-radius:6px; padding:10px; font-size:16px; }
  input:focus { border-color:#35e0ff; outline:none; }
`;

let currentUi: CheckoutUi | null = null;
let listenerRegistered = false;

export async function initCheckout(token: string, language: string, sandbox: boolean) {
  await headlessCheckout.init({ sandbox, isWebView: false, language });
  headlessCheckout.setSecureComponentStyles(SECURE_CSS);
  await headlessCheckout.setToken(token);
}

export const detachUi = () => { currentUi = null; };

function fieldElement(f: Field): HTMLElement | null {
  let el: HTMLElement;
  if (f.name === 'card_number') { el = document.createElement('psdk-card-number'); el.setAttribute('icon', 'true'); }
  else if (f.name === 'phone') { el = document.createElement('psdk-phone'); el.setAttribute('showFlags', 'true'); }
  else if (f.type === 'text') el = document.createElement('psdk-text');
  else if (f.type === 'select') el = document.createElement('psdk-select');
  else if (f.type === 'check') el = document.createElement('psdk-checkbox');
  else return null; // labels (and anything unknown) are never rendered as inputs
  el.setAttribute('name', f.name);
  return el;
}

async function renderFields(ui: CheckoutUi, fields: Field[]) {
  ui.setLoading(true);
  ui.errorEl.textContent = '';
  ui.fieldsEl.replaceChildren(); // replace, never append, on show_fields
  const mounted: Field[] = [];
  for (const f of fields) {
    const el = fieldElement(f);
    if (el) { ui.fieldsEl.appendChild(el); mounted.push(f); }
  }
  ui.fieldsEl.appendChild(document.createElement('psdk-submit-button'));
  await headlessCheckout.form.setupAndAwaitFieldsLoading(mounted);
  headlessCheckout.form.activate(); // without this, submit silently does nothing
  ui.setLoading(false);
}

function dispatch(action: any) {
  const ui = currentUi;
  if (!ui) return;
  switch (action.type) {
    case 'show_fields':
      void renderFields(ui, action.data.fields);
      break;
    case 'show_errors':
      ui.errorEl.textContent = action.data.errors?.[0]?.message ?? 'Payment error';
      break;
    case 'redirect': {
      const el = document.createElement('psdk-redirect');
      el.setAttribute('data-redirect', JSON.stringify(action.data));
      ui.statusEl.replaceChildren(el);
      break;
    }
    case '3DS': {
      const el = document.createElement('psdk-3ds');
      el.setAttribute('data-challenge', JSON.stringify(action.data.data)); // payload is nested one level down
      ui.statusEl.replaceChildren(el);
      break;
    }
    case 'check_status': {
      ui.fieldsEl.replaceChildren();
      // Created dynamically on purpose: a static <psdk-status> calls getStatus() before a token exists.
      ui.statusEl.replaceChildren(document.createElement('psdk-status'));
      break;
    }
  }
}

export async function openMethod(ui: CheckoutUi, paymentMethodId: number, returnUrl: string) {
  currentUi = ui;
  ui.statusEl.replaceChildren();
  ui.setLoading(true);
  const form = await headlessCheckout.form.init({
    paymentMethodId,
    returnUrl,
    paymentMethodSettings: { useSingleExpirationDateField: true },
  });
  if (!listenerRegistered) { // one listener for the whole page session
    headlessCheckout.form.onNextAction(dispatch);
    listenerRegistered = true;
  }
  await renderFields(ui, form.fields as Field[]);
}
```

- [ ] **Step 5: Write `CheckoutModal.tsx` and `PaymentReturn.tsx`**

`src/checkout/CheckoutModal.tsx`:

```tsx
import { useEffect, useRef, useState } from 'react';
import { config } from '../config';
import { PAY_LANGUAGE, type Locale } from '../i18n/locales';
import { UI } from '../i18n/ui';
import { detachUi, initCheckout, openMethod } from './sdk';

export function CheckoutModal({ token, locale, onClose }: { token: string; locale: Locale; onClose: () => void }) {
  const t = UI[locale];
  const methodsRef = useRef<HTMLElement | null>(null);
  const fieldsRef = useRef<HTMLDivElement>(null);
  const statusRef = useRef<HTMLDivElement>(null);
  const errorRef = useRef<HTMLParagraphElement>(null);
  const [loading, setLoading] = useState(false);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    initCheckout(token, PAY_LANGUAGE[locale], config.sandbox)
      .then(() => alive && setReady(true))
      .catch((e) => alive && setFailed((e as Error).message));
    return () => { alive = false; detachUi(); };
  }, [token, locale]);

  useEffect(() => {
    const el = methodsRef.current;
    if (!ready || !el) return;
    const onSelect = (e: Event) => {
      const id = Number((e as CustomEvent).detail?.paymentMethodId);
      void openMethod(
        { fieldsEl: fieldsRef.current!, statusEl: statusRef.current!, errorEl: errorRef.current!, setLoading },
        id,
        `${location.origin}/payment/return?token=${encodeURIComponent(token)}`,
      ).catch((err) => setFailed((err as Error).message));
    };
    el.addEventListener('selectionChange', onSelect);
    return () => el.removeEventListener('selectionChange', onSelect);
  }, [ready, token]);

  return (
    <div className="modal" role="dialog" aria-modal="true">
      <div>
        <button onClick={onClose}>{t.close}</button>
        {failed && <p className="error">{failed}</p>}
        {ready && <psdk-payment-methods ref={methodsRef} />}
        {loading && <p>{t.loading}</p>}
        <div ref={fieldsRef} />
        <p ref={errorRef} className="error" />
        <div ref={statusRef} />
        {ready && <><psdk-payment-form-messages /><psdk-total /><psdk-legal /></>}
      </div>
    </div>
  );
}
```

`src/pages/PaymentReturn.tsx` (per `payment-status`: init, setToken, then create `psdk-status` dynamically; no `form.init`):

```tsx
import { headlessCheckout } from '@xsolla/pay-station-sdk';
import { useEffect, useRef, useState } from 'react';
import { config } from '../config';
import { PAY_LANGUAGE, resolveLocale } from '../i18n/locales';

export function PaymentReturn() {
  const host = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const token = new URLSearchParams(location.search).get('token');
    if (!token) { setError('Missing token'); return; }
    const language = PAY_LANGUAGE[resolveLocale(localStorage.getItem('voidwall.locale'))];
    (async () => {
      await headlessCheckout.init({ sandbox: config.sandbox, isWebView: false, language });
      await headlessCheckout.setToken(token);
      host.current?.appendChild(document.createElement('psdk-status'));
    })().catch((e) => setError((e as Error).message));
  }, []);
  return (
    <main className="page">
      <div ref={host} />
      {error && <p className="error">{error}</p>}
      <psdk-legal />
      <p><a href="/">Back to the store</a></p>
    </main>
  );
}
```

- [ ] **Step 6: Wire checkout into `App.tsx` and `main.tsx`**

In `src/App.tsx` add state and handlers, replacing the two `() => {}` stubs:

```tsx
// imports to add
import { CheckoutModal } from './checkout/CheckoutModal';
import { InsufficientCoresError, buyWithCores, createCartPaymentToken, fetchCoresBalance } from './checkout/api';
import { PAY_LANGUAGE } from './i18n/locales';

// inside Shop()
const [token, setToken] = useState<string | null>(null);
const [balance, setBalance] = useState<number | null>(null);
const [notice, setNotice] = useState<string | null>(null);

useEffect(() => {
  if (!auth.session) { setBalance(null); return; }
  fetchCoresBalance(config.projectId, auth.session).then(setBalance).catch(() => setBalance(null));
}, [auth.session]);

async function checkout(promoCode?: string) {
  if (!auth.session || !cart.cart) return;
  try {
    const r = await createCartPaymentToken({
      projectId: config.projectId, cartId: cart.cart.cartId, session: auth.session,
      language: PAY_LANGUAGE[locale], sandbox: config.sandbox, promoCode,
    });
    setDrawer(false);
    setToken(r.token);
  } catch (e) { setNotice((e as Error).message); }
}

async function buyCores(item: ShopItem) {
  if (!auth.session) { auth.login(); return; }
  try {
    await buyWithCores({ projectId: config.projectId, sku: item.sku, session: auth.session });
    setNotice(t.purchased);
    setBalance(await fetchCoresBalance(config.projectId, auth.session));
  } catch (e) { setNotice(e instanceof InsufficientCoresError ? t.notEnoughCores : (e as Error).message); }
}
```

Then pass `onBuyWithCores={buyCores}` to `Section`, `onCheckout={checkout}` to `CartDrawer`, and render `{token && <CheckoutModal token={token} locale={locale} onClose={() => setToken(null)} />}`, `{notice && <p className="note" role="status">{notice}</p>}`, and `{balance !== null && <p className="note">{t.balance}: {balance.toLocaleString(locale)}</p>}` near the header.

In `src/main.tsx`, render the return page for `/payment/return`:

```tsx
import { PaymentReturn } from './pages/PaymentReturn';
// replace the createRoot line
const isReturn = location.pathname === '/payment/return';
createRoot(document.getElementById('root')!).render(<StrictMode>{isReturn ? <PaymentReturn /> : <Root />}</StrictMode>);
```

Run: `npm run build`
Expected: type-check and build pass.

- [ ] **Step 7: Verify checkout in the sandbox (requires a Login project, known gap 8)**

If `VITE_LOGIN_PROJECT_ID` and `VITE_LOGIN_CLIENT_ID` are empty, stop here and report checkout and Cores purchase as **unverified** (code and unit tests only). Otherwise, with a registered sandbox test user:
1. Sign in; confirm the guest cart merged into the account cart.
2. Add Core Cache, Checkout: the modal lists payment methods and the total.
3. Card `4111111111111111`, exp `12/40`, any CVV: ends on `psdk-status` success.
4. Card `4111111111111152` and `4423610000000007` (3DS): redirect to the Xsolla verify page, confirm, land on `/payment/return`, status success.
5. Switch the shop to `fr` before checkout: the payment UI language is French.
Driving the secure iframes headlessly: read `skills/headless-checkout-integration/references/testing.md` first (`pressSequentially`, not `fill`). Report the terminal screen observed for each card.

---

### Task 8: Webhook handler

**Files:**
- Create: `server/signature.ts`, `server/handler.ts`, `server/stores.ts`, `server/index.ts`
- Test: `tests/webhook.test.ts`
- Copy: `skills/webhooks-impl/fixtures/*.json` to `tests/fixtures/` (read-only copies)

**Interfaces:**
- Produces:
  - `verifySignature(raw: Buffer, header: string | undefined, secret: string): boolean`
  - `interface Grants { grant(userId: string, items: { sku: string; quantity: number }[], txnId: string): Promise<void>; revoke(userId: string, txnId: string): Promise<void> }`
  - `interface Claims { claim(txnId: string): Promise<boolean> }` (true only the first time)
  - `createHandler(deps: { secret: string; grants: Grants; claims: Claims }): (raw: Buffer, authHeader: string | undefined) => Promise<{ status: number; body?: unknown }>`
  - `FileGrants`, `FileClaims` (JSONL under `server/data/`), a stand-in for the game's entitlement system

How goods reach the player is the developer's call (`webhooks-impl` says to ask, not invent). `FileGrants` is a labeled stand-in and `user_validation` accepts every user because there is no user database here. Say so in the final report.

- [ ] **Step 1: Copy fixtures**

```bash
cd examples/voidwall-shop
mkdir -p tests/fixtures
cp ../../skills/webhooks-impl/fixtures/order_paid.json ../../skills/webhooks-impl/fixtures/payment.json ../../skills/webhooks-impl/fixtures/user_validation.json tests/fixtures/
ls tests/fixtures
```

Expected: `order_paid.json payment.json user_validation.json`.

- [ ] **Step 2: Write the failing tests**

`tests/webhook.test.ts`:

```ts
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { beforeEach, describe, expect, test } from 'vitest';
import { createHandler } from '../server/handler';
import { verifySignature } from '../server/signature';

const SECRET = 'test-secret';
const sign = (raw: Buffer) => `Signature ${createHash('sha1').update(Buffer.concat([raw, Buffer.from(SECRET)])).digest('hex')}`;
const fixture = (n: string) => readFileSync(`tests/fixtures/${n}.json`);

describe('verifySignature', () => {
  const raw = Buffer.from('{"a":1}');
  test('accepts a correct signature', () => expect(verifySignature(raw, sign(raw), SECRET)).toBe(true));
  test('rejects tampered body', () => expect(verifySignature(Buffer.from('{"a":2}'), sign(raw), SECRET)).toBe(false));
  test('rejects wrong length, missing header, wrong secret', () => {
    expect(verifySignature(raw, 'Signature abc', SECRET)).toBe(false);
    expect(verifySignature(raw, undefined, SECRET)).toBe(false);
    expect(verifySignature(raw, sign(raw), 'other')).toBe(false);
  });
  test('is plain sha1(body+secret), not HMAC', () => {
    const plain = createHash('sha1').update('{"a":1}test-secret').digest('hex');
    expect(sign(raw)).toBe(`Signature ${plain}`);
  });
});

describe('handler', () => {
  let grants: { userId: string; items: unknown; txn: string }[];
  let revokes: string[];
  let seen: Set<string>;
  let handle: ReturnType<typeof createHandler>;

  beforeEach(() => {
    grants = []; revokes = []; seen = new Set();
    handle = createHandler({
      secret: SECRET,
      grants: {
        async grant(userId, items, txn) { grants.push({ userId, items, txn }); },
        async revoke(_u, txn) { revokes.push(txn); },
      },
      claims: { async claim(id) { if (seen.has(id)) return false; seen.add(id); return true; } },
    });
  });

  test('bad signature: 400 INVALID_SIGNATURE and nothing granted', async () => {
    const raw = fixture('order_paid');
    const res = await handle(raw, 'Signature deadbeef');
    expect(res.status).toBe(400);
    expect(JSON.stringify(res.body)).toContain('INVALID_SIGNATURE');
    expect(grants).toEqual([]);
  });

  test('malformed JSON with a valid signature: 400, no crash', async () => {
    const raw = Buffer.from('{not json');
    expect((await handle(raw, sign(raw))).status).toBe(400);
  });

  test('user_validation: 204', async () => {
    const raw = fixture('user_validation');
    expect((await handle(raw, sign(raw))).status).toBe(204);
  });

  test('order_paid grants once; a duplicate delivery returns 2xx without granting again', async () => {
    const raw = fixture('order_paid');
    const a = await handle(raw, sign(raw));
    const b = await handle(raw, sign(raw));
    expect([a.status, b.status]).toEqual([204, 204]);
    expect(grants).toHaveLength(1);
    expect(grants[0]).toMatchObject({
      userId: 'a1b2c3d4-0000-4000-8000-019fb6caa51e',
      items: [{ sku: 'artifact_centaurs_axe', quantity: 1 }],
      txn: '2105129134',
    });
  });

  test('separate-mode payment is recorded only, never fulfilled', async () => {
    const raw = fixture('payment');
    expect((await handle(raw, sign(raw))).status).toBe(204);
    expect(grants).toEqual([]);
  });

  test('order_canceled revokes', async () => {
    const raw = Buffer.from(JSON.stringify({
      notification_type: 'order_canceled',
      user: { external_id: 'u1' },
      billing: { transaction: { id: 99 } },
      order: { id: 5 },
    }));
    expect((await handle(raw, sign(raw))).status).toBe(204);
    expect(revokes).toEqual(['99']);
  });

  test('unknown notification types are acknowledged, not errors', async () => {
    const raw = Buffer.from(JSON.stringify({ notification_type: 'something_new' }));
    expect((await handle(raw, sign(raw))).status).toBe(204);
  });

  test('order_paid without a user id is a permanent 400, not a retry-forever 5xx', async () => {
    const raw = Buffer.from(JSON.stringify({ notification_type: 'order_paid', items: [], order: { id: 1 } }));
    expect((await handle(raw, sign(raw))).status).toBe(400);
  });
});
```

Run: `npm test -- webhook`
Expected: FAIL, `server/handler` not found.

- [ ] **Step 3: Write `server/signature.ts`**

```ts
import { createHash, timingSafeEqual } from 'node:crypto';

/** lowercase(sha1(rawBody + secret)) vs the `Signature <hex>` header, compared in constant time. */
export function verifySignature(raw: Buffer, header: string | undefined, secret: string): boolean {
  if (!header) return false;
  const provided = Buffer.from(header.replace(/^Signature\s+/i, '').toLowerCase(), 'utf8');
  const expected = Buffer.from(
    createHash('sha1').update(Buffer.concat([raw, Buffer.from(secret, 'utf8')])).digest('hex'), 'utf8',
  );
  return provided.length === expected.length && timingSafeEqual(provided, expected);
}
```

- [ ] **Step 4: Write `server/handler.ts`**

```ts
import { verifySignature } from './signature';

export interface Grants {
  grant(userId: string, items: { sku: string; quantity: number }[], txnId: string): Promise<void>;
  revoke(userId: string, txnId: string): Promise<void>;
}
export interface Claims { claim(txnId: string): Promise<boolean> }
export interface Result { status: number; body?: unknown }

const err = (code: string, message: string): Result => ({ status: 400, body: { error: { code, message } } });
const ok: Result = { status: 204 };

export function createHandler(deps: { secret: string; grants: Grants; claims: Claims }) {
  return async function handle(raw: Buffer, authHeader: string | undefined): Promise<Result> {
    if (!verifySignature(raw, authHeader, deps.secret)) return err('INVALID_SIGNATURE', 'Invalid signature');

    let evt: any;
    try { evt = JSON.parse(raw.toString('utf8')); } catch { return err('INVALID_PARAMETER', 'Body is not JSON'); }

    const txnId = String(evt.billing?.transaction?.id ?? evt.transaction?.id ?? evt.order?.id ?? '');
    const userId: string | undefined = evt.user?.external_id ?? evt.user?.id;

    switch (evt.notification_type) {
      case 'user_validation':
        // No user database in this example: accept. Replace with a real lookup (400 INVALID_USER if unknown).
        return ok;

      case 'order_paid': {
        if (!userId || !txnId) return err('INVALID_PARAMETER', 'Missing user or transaction id');
        if (!(await deps.claims.claim(txnId))) return ok; // duplicate delivery
        const items = (evt.items ?? []).map((i: any) => ({ sku: String(i.sku), quantity: Number(i.quantity ?? 1) }));
        await deps.grants.grant(userId, items, txnId);
        return ok;
      }

      case 'order_canceled':
      case 'refund': {
        if (!userId || !txnId) return err('INVALID_PARAMETER', 'Missing user or transaction id');
        await deps.grants.revoke(userId, txnId);
        return ok;
      }

      // `payment` (separate delivery mode) is a financial record; fulfillment happens on order_paid only.
      default:
        return ok;
    }
  };
}
```

A thrown error from `grant` or `revoke` propagates to `index.ts`, which turns it into a `500` so Xsolla retries (transient). Permanent problems above return `400`.

- [ ] **Step 5: Write `server/stores.ts` and `server/index.ts`**

`server/stores.ts` (stand-in persistence, labeled as such):

```ts
import { appendFile, mkdir, readFile } from 'node:fs/promises';
import type { Claims, Grants } from './handler';

const DIR = new URL('./data/', import.meta.url);
const GRANTS = new URL('grants.jsonl', DIR);
const CLAIMS = new URL('claims.jsonl', DIR);

async function lines(url: URL): Promise<string[]> {
  try { return (await readFile(url, 'utf8')).split('\n').filter(Boolean); } catch { return []; }
}

/** Stand-in for the game's entitlement system. Replace with the real grant path. */
export const fileGrants: Grants = {
  async grant(userId, items, txnId) {
    await mkdir(DIR, { recursive: true });
    await appendFile(GRANTS, JSON.stringify({ op: 'grant', userId, items, txnId, at: new Date().toISOString() }) + '\n');
  },
  async revoke(userId, txnId) {
    await mkdir(DIR, { recursive: true });
    await appendFile(GRANTS, JSON.stringify({ op: 'revoke', userId, txnId, at: new Date().toISOString() }) + '\n');
  },
};

export const fileClaims: Claims = {
  async claim(txnId) {
    if ((await lines(CLAIMS)).includes(txnId)) return false;
    await mkdir(DIR, { recursive: true });
    await appendFile(CLAIMS, txnId + '\n');
    return true;
  },
};
```

This claim is check-then-write and is safe for a single process. A multi-instance deployment needs a unique constraint in a real datastore; note that in the final report.

`server/index.ts`:

```ts
import express from 'express';
import { createHandler } from './handler';
import { fileClaims, fileGrants } from './stores';

const secret = process.env.XSOLLA_WEBHOOK_SECRET;
if (!secret) throw new Error('XSOLLA_WEBHOOK_SECRET is required'); // fail fast: every signature would fail otherwise

const handle = createHandler({ secret, grants: fileGrants, claims: fileClaims });
const app = express();

// express.raw keeps the exact bytes, which the signature is computed over.
app.post('/xsolla/webhooks', express.raw({ type: '*/*', limit: '1mb' }), async (req, res) => {
  try {
    const out = await handle(req.body as Buffer, req.get('authorization'));
    res.status(out.status);
    out.body ? res.json(out.body) : res.end();
  } catch (e) {
    console.error('webhook failed', (e as Error).message);
    res.status(500).json({ error: { code: 'INTERNAL', message: 'Temporary error' } }); // transient: Xsolla retries
  }
});

const port = Number(process.env.PORT ?? 8787);
app.listen(port, () => console.log(`webhook listening on :${port}/xsolla/webhooks`));
```

- [ ] **Step 6: Run tests and smoke-test the server**

Run: `npm test`
Expected: all pass (webhook tests included).

Run the server and replay a fixture signed with a throwaway secret:

```bash
cd examples/voidwall-shop
XSOLLA_WEBHOOK_SECRET=local-test npm run webhook &
SERVER=$!
sleep 2
BODY=tests/fixtures/order_paid.json
SIG=$(node -e "const c=require('crypto'),fs=require('fs');process.stdout.write(c.createHash('sha1').update(Buffer.concat([fs.readFileSync('$BODY'),Buffer.from('local-test')])).digest('hex'))")
for i in 1 2; do curl -s -o /dev/null -w '%{http_code}\n' -X POST localhost:8787/xsolla/webhooks -H "authorization: Signature $SIG" --data-binary @$BODY; done
curl -s -w ' %{http_code}\n' -X POST localhost:8787/xsolla/webhooks -H 'authorization: Signature bad' --data-binary @$BODY
wc -l server/data/grants.jsonl
kill $SERVER
rm -rf server/data
```

Expected: `204`, `204`, then `{"error":{"code":"INVALID_SIGNATURE",...}} 400`, and `grants.jsonl` has exactly `1` line.

---

### Task 9: Final verification and report

**Files:** none created. Evidence only.

- [ ] **Step 1: Full test run**

Run: `npm test`
Expected: every test file passes. Paste the summary line into the report.

- [ ] **Step 2: Type-check and production build**

Run: `npm run build`
Expected: exit 0.

- [ ] **Step 3: No secrets in the browser bundle or logs**

```bash
cd examples/voidwall-shop
KEY=$(grep -E '^XSOLLA_PROJECT_API_KEY=' ../../.env | cut -d= -f2-)
if [ -n "$KEY" ] && grep -rqF "$KEY" dist src; then echo "LEAK"; else echo "clean"; fi
grep -rn "XSOLLA_PROJECT_API_KEY" src dist || echo "no key references in browser code"
```

Expected: `clean` and `no key references in browser code`.

- [ ] **Step 4: Catalog check against the live public API**

Run: `npm run seed -- --verify`
Expected: `public catalog: N/N expected SKUs present`, exit 0. Also confirm the 27 quest fixtures are still present:

```bash
curl -s "https://store.xsolla.com/api/v2/project/316665/items/virtual_items?limit=50" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(sum(1 for i in d["items"] if i["sku"].startswith(("quest_","qp_"))), "quest fixtures")'
```

Expected: `27 quest fixtures`.

- [ ] **Step 5: Browser run (Task 6 Step 6 checklist) on the final build**

Run `npm run dev` (or `npm run build && npx vite preview`) and repeat the Task 6 Step 6 browser checks, plus the `fr`, `de`, `ja`, `pt-BR` switches each show localized headings, descriptions, and formatted prices.

- [ ] **Step 6: Write the report, stating verified and unverified separately**

Verified means "I ran it and saw it": tests, build, seeded catalog counts, storefront behavior, cart persistence, webhook replay. Unverified (say so plainly) means anything not run: login, Cores purchase, and sandbox card payments unless Task 7 Step 7 was completed with a real Login project; webhook delivery from Xsolla itself (needs a public HTTPS URL and the PA webhook secret); the production flip (developer-only, per the `production` skill). Restate the Known gaps list (Warden's Charter, Arsenal pricing and the 3,900 vs 4,700 discrepancy, assumed Plank Owner price, missing reactor art, windowed items hidden until 2026-10-14, machine-drafted translations, `FileGrants` stand-in). List the manual steps the user owns: add `http://localhost:5173/auth/callback` to the Login project callback URLs and allowed origins; supply `VITE_LOGIN_PROJECT_ID` and `VITE_LOGIN_CLIENT_ID`; generate the webhook secret and set the listener URL; deploy the webhook and the static shop over HTTPS. Do not commit anything.
