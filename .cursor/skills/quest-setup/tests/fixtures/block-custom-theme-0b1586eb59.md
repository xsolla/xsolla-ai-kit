# Custom theme contract snapshot (commit 0b1586eb59, read by orchestrator via git show 2026-11-03). Test fixture only.

## projects/quest-platform/quests-block/src/themes/custom/appearance.ts
```
export type FontChoice =
  | 'host-body'
  | 'host-heading'
  | 'host-button'
  | { loadedFont: string };

export type CustomThemeAppearanceV1 = {
  version: 1;
  baseThemeId: 'site-builder' | 'xsolla-pages';
  palette?: Partial<
    Record<
      | 'accent'
      | 'sectionBackground'
      | 'cardBackground'
      | 'primaryText'
      | 'secondaryText'
      | 'border'
      | 'actionText',
      string
    >
  >;
  typography?: {
    bodyFont?: FontChoice;
    headingFont?: FontChoice;
    buttonFont?: FontChoice;
    headingSize?: number;
    bodySize?: number;
    buttonSize?: number;
    headingWeight?: 400 | 500 | 600 | 700;
    bodyWeight?: 400 | 500 | 600 | 700;
    buttonWeight?: 400 | 500 | 600 | 700;
    headingLineHeight?: number;
    bodyLineHeight?: number;
    buttonLineHeight?: number;
  };
  geometry?: {
    maxWidth?: number;
    railInset?: number;
    gutter?: number;
    mobileGutter?: number;
    sectionPadding?: number;
    cardPadding?: number;
    gap?: number;
    radius?: number;
    buttonRadius?: number;
    buttonHeight?: number;
    columns?: 1 | 2 | 3 | 4;
  };
} & Record<string, unknown>;

const paletteKeys = [
  'accent',
  'sectionBackground',
  'cardBackground',
  'primaryText',
  'secondaryText',
  'border',
  'actionText',
] as const;
const fontKeys = ['bodyFont', 'headingFont', 'buttonFont'] as const;
const weightKeys = ['headingWeight', 'bodyWeight', 'buttonWeight'] as const;
const lineHeightKeys = [
  'headingLineHeight',
  'bodyLineHeight',
  'buttonLineHeight',
] as const;
const sizeRanges = {
  headingSize: [16, 64],
  bodySize: [12, 24],
  buttonSize: [12, 24],
} as const;
const geometryRanges = {
  maxWidth: [640, 1920],
  railInset: [0, 20],
  gutter: [0, 64],
  mobileGutter: [0, 64],
  sectionPadding: [0, 128],
  cardPadding: [8, 64],
  gap: [8, 48],
  radius: [0, 32],
  buttonRadius: [0, 32],
  buttonHeight: [32, 64],
} as const;
const knownTypographyKeys = [
  ...fontKeys,
  ...weightKeys,
  ...lineHeightKeys,
  ...Object.keys(sizeRanges),
];
const knownGeometryKeys = [...Object.keys(geometryRanges), 'columns'];
const loadedFontPattern = /^(?=.*[A-Za-z0-9])[A-Za-z0-9 _-]{1,64}$/;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isPlainRecord(value: unknown): value is Record<string, unknown> {
  if (!isRecord(value)) return false;
  const prototype = Object.getPrototypeOf(value);
  return prototype === Object.prototype || prototype === null;
}

function cloneValue<T>(value: T): T {
  if (Array.isArray(value)) {
    return value.map((entry) => cloneValue(entry)) as T;
  }
  if (!isPlainRecord(value)) return value;

  return Object.fromEntries(
    Object.entries(value).map(([key, entry]) => [key, cloneValue(entry)]),
  ) as T;
}

function isHex6(value: unknown): value is string {
  return typeof value === 'string' && /^#[0-9a-fA-F]{6}$/.test(value);
}

function validFont(value: unknown): value is FontChoice {
  return (
    value === 'host-body' ||
    value === 'host-heading' ||
    value === 'host-button' ||
    (isRecord(value) &&
      Object.keys(value).length === 1 &&
      typeof value.loadedFont === 'string' &&
      loadedFontPattern.test(value.loadedFont))
  );
}

function validInteger(
  value: unknown,
  range: readonly [number, number],
): value is number {
  return (
    typeof value === 'number' &&
    Number.isFinite(value) &&
    Number.isInteger(value) &&
    value >= range[0] &&
    value <= range[1]
  );
}

function validLineHeight(value: unknown): value is number {
  return (
    typeof value === 'number' &&
    Number.isFinite(value) &&
    value >= 1 &&
    value <= 2
  );
}

function validKnownFields(raw: Record<string, unknown>): boolean {
  if (raw.palette !== undefined) {
    if (!isRecord(raw.palette)) return false;
    for (const key of paletteKeys) {
      if (raw.palette[key] !== undefined && !isHex6(raw.palette[key])) {
        return false;
      }
    }
  }

  if (raw.typography !== undefined) {
    if (!isRecord(raw.typography)) return false;
    for (const key of fontKeys) {
      if (
        raw.typography[key] !== undefined &&
        !validFont(raw.typography[key])
      ) {
        return false;
      }
    }
    for (const key of weightKeys) {
      const value = raw.typography[key];
      if (
        value !== undefined &&
        ![400, 500, 600, 700].includes(value as number)
      ) {
        return false;
      }
    }
    for (const key of lineHeightKeys) {
      if (
        raw.typography[key] !== undefined &&
        !validLineHeight(raw.typography[key])
      ) {
        return false;
      }
    }
    for (const [key, range] of Object.entries(sizeRanges)) {
      if (
        raw.typography[key] !== undefined &&
        !validInteger(raw.typography[key], range)
      ) {
        return false;
      }
    }
  }

  if (raw.geometry !== undefined) {
    if (!isRecord(raw.geometry)) return false;
    for (const [key, range] of Object.entries(geometryRanges)) {
      if (
        raw.geometry[key] !== undefined &&
        !validInteger(raw.geometry[key], range)
      ) {
        return false;
      }
    }
    if (
      raw.geometry.columns !== undefined &&
      ![1, 2, 3, 4].includes(raw.geometry.columns as number)
    ) {
      return false;
    }
  }
  return true;
}

export function normalizeCustomAppearance(
  raw: unknown,
): CustomThemeAppearanceV1 | undefined {
  if (
    !isRecord(raw) ||
    raw.version !== 1 ||
    (raw.baseThemeId !== 'site-builder' &&
      raw.baseThemeId !== 'xsolla-pages') ||
    !validKnownFields(raw)
  ) {
    return undefined;
  }

  const normalized = cloneValue(raw) as CustomThemeAppearanceV1;
  for (const key of lineHeightKeys) {
    const value = normalized.typography?.[key];
    if (value !== undefined)
      normalized.typography![key] = Math.round(value * 100) / 100;
  }
  return normalized;
}

export function patchCustomAppearance(
  raw: unknown,
  patch: Partial<CustomThemeAppearanceV1>,
): Record<string, unknown> {
  const current = normalizeCustomAppearance(raw);
  if (!current) throw new Error('Unsupported or invalid Custom appearance');
  if (
    !isRecord(patch) ||
    (patch.version !== undefined && patch.version !== 1)
  ) {
    throw new Error('Patch contains unsupported Custom appearance fields');
  }
  const merged: Record<string, unknown> = { ...current, ...patch };
  for (const group of ['palette', 'typography', 'geometry'] as const) {
    if (patch[group] !== undefined) {
      if (!isRecord(patch[group])) throw new Error(`Invalid ${group} patch`);
      const values: Record<string, unknown> = { ...current[group] };
      for (const [key, value] of Object.entries(patch[group])) {
        if (value === undefined) delete values[key];
        else values[key] = value;
      }
      if (Object.keys(values).length) merged[group] = values;
      else delete merged[group];
    }
  }
  const normalized = normalizeCustomAppearance(merged);
  if (!normalized) {
    throw new Error('Patch contains invalid Custom appearance values');
  }
  return normalized;
}

export function resetCustomAppearance(raw: unknown): Record<string, unknown> {
  if (!isRecord(raw) || raw.version !== 1) {
    throw new Error('Unsupported Custom appearance version');
  }
  const result = cloneValue(raw);
  for (const [group, knownKeys] of [
    ['palette', paletteKeys],
    ['typography', knownTypographyKeys],
    ['geometry', knownGeometryKeys],
  ] as const) {
    const values = result[group];
    if (!isRecord(values)) continue;
    const kept = Object.fromEntries(
      Object.entries(values).filter(
        ([key]) => !knownKeys.includes(key as never),
      ),
    );
    if (Object.keys(kept).length) result[group] = kept;
    else delete result[group];
  }
  return result;
}

function relativeLuminance(hex: string): number {
  const channels = hex
    .slice(1)
    .match(/.{2}/g)!
    .map((channel) => parseInt(channel, 16) / 255)
    .map((channel) =>
      channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4,
    );
  return channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722;
}

function contrastRatio(first: string, second: string): number {
  const [lighter, darker] = [
    relativeLuminance(first),
    relativeLuminance(second),
  ].sort((a, b) => b - a);
  return (lighter + 0.05) / (darker + 0.05);
}

function mix(hex: string, target: number, amount: number): string {
  const channels = hex
    .slice(1)
    .match(/.{2}/g)!
    .map((channel) => parseInt(channel, 16));
  return `#${channels
    .map((channel) =>
      Math.round(channel + (target - channel) * amount)
        .toString(16)
        .padStart(2, '0'),
    )
    .join('')}`;
}

export function isActionTextAccessible(accent: string, text: string): boolean {
  return isHex6(accent) && isHex6(text) && contrastRatio(accent, text) >= 4.5;
}

export function resolveActionColors(
  accent: string,
  actionText?: string,
  adjacentSurface = '#ffffff',
): { text: string; hover: string; pressed: string; focus: string } {
  const safeAccent = isHex6(accent) ? accent.toLowerCase() : '#000000';
  const blackContrast = contrastRatio(safeAccent, '#000000');
  const whiteContrast = contrastRatio(safeAccent, '#ffffff');
  const derivedText = blackContrast >= whiteContrast ? '#000000' : '#ffffff';
  const text =
    actionText && isActionTextAccessible(safeAccent, actionText)
      ? actionText.toLowerCase()
      : derivedText;
  const mixTarget =
    relativeLuminance(text) > relativeLuminance(safeAccent) ? 0 : 255;
  const interactionColor = (preferredAmount: number) => {
    let amount = preferredAmount;
    let result = mix(safeAccent, mixTarget, amount);
    while (contrastRatio(text, result) < 4.5 && amount < 1) {
      amount = Math.min(1, amount + 0.02);
      result = mix(safeAccent, mixTarget, amount);
    }
    return result;
  };
  const hover = interactionColor(0.12);
  const pressed = interactionColor(0.22);
  const surface = isHex6(adjacentSurface) ? adjacentSurface : '#ffffff';
  const focus =
    contrastRatio(safeAccent, surface) >= 3
      ? safeAccent
      : contrastRatio('#000000', surface) >= contrastRatio('#ffffff', surface)
        ? '#000000'
        : '#ffffff';
  return { text, hover, pressed, focus };
}
```

## projects/quest-platform/quests-block/src/themes/custom/variables.ts
```
import { assignInlineVars } from '@vanilla-extract/dynamic';

import { isActionTextAccessible, resolveActionColors } from './appearance';
import { getGridColumnsMaxWidth } from './grid-layout';
import { customVariable } from './variable-identifiers';
import { siteBuilderThemeValues } from '../site-builder/theme.css';
import { xsollaPagesThemeValues } from '../xsolla-pages/theme.css';

import type { CustomThemeAppearanceV1, FontChoice } from './appearance';

export type CustomVars = ReturnType<typeof assignInlineVars>;
type ValueMap = Record<string, unknown>;
const publicKeys = {
  palette: [
    'accent',
    'sectionBackground',
    'cardBackground',
    'primaryText',
    'secondaryText',
    'border',
    'actionText',
  ],
  typography: [
    'bodyFont',
    'headingFont',
    'buttonFont',
    'headingSize',
    'bodySize',
    'buttonSize',
    'headingWeight',
    'bodyWeight',
    'buttonWeight',
    'headingLineHeight',
    'bodyLineHeight',
    'buttonLineHeight',
  ],
  geometry: [
    'maxWidth',
    'railInset',
    'gutter',
    'mobileGutter',
    'sectionPadding',
    'cardPadding',
    'gap',
    'radius',
    'buttonRadius',
    'buttonHeight',
    'columns',
  ],
} as const;
const derivedPaletteKeys = ['actionText', 'hover', 'pressed', 'focus'] as const;

function mapGroup(
  group: string,
  values: ValueMap | undefined,
  output: Record<string, string>,
  convert: (key: string, value: unknown) => string,
  allowedKeys: readonly string[],
) {
  for (const [key, value] of Object.entries(values ?? {})) {
    if (!allowedKeys.includes(key)) continue;
    const variable = customVariable(group, key);
    if (variable && value !== undefined) output[variable] = convert(key, value);
  }
}

function fontCss(font: FontChoice): string {
  if (typeof font !== 'string') return `"${font.loadedFont}"`;
  if (font === 'host-body')
    return customVariable('typography', 'hostBodyFont')!;
  if (font === 'host-heading')
    return customVariable('typography', 'hostHeadingFont')!;
  return customVariable('typography', 'hostButtonFont')!;
}

function geometryCss(key: string, value: unknown): string {
  if (key === 'columns') return String(value);
  if (key === 'railInset') return `${value}%`;
  return `${value}px`;
}

function typographyCss(
  key: string,
  value: unknown,
  baseFonts: Record<'bodyFont' | 'sectionHeadingFont' | 'actionFont', string>,
): string {
  if (key.endsWith('Font')) {
    const fallback =
      key === 'bodyFont'
        ? baseFonts.bodyFont
        : key === 'headingFont'
          ? baseFonts.sectionHeadingFont
          : baseFonts.actionFont;
    const font = value as FontChoice;
    return typeof font === 'string'
      ? fontCss(font)
      : `"${font.loadedFont}", ${fallback}`;
  }
  if (key.endsWith('Size')) return `${value}px`;
  return String(value);
}

/** Maps validated appearance fields to declared Vanilla Extract variables only. */
export function toCustomVariables(value: CustomThemeAppearanceV1): CustomVars {
  const variables: Record<string, string> = {};
  const palette = value.palette as ValueMap | undefined;
  const typography = value.typography as ValueMap | undefined;
  const geometry = value.geometry as ValueMap | undefined;
  const accent = palette?.accent as string | undefined;
  const baseFonts =
    value.baseThemeId === 'xsolla-pages'
      ? {
          bodyFont: xsollaPagesThemeValues.typography.bodyFont,
          sectionHeadingFont:
            xsollaPagesThemeValues.typography.sectionHeadingFont,
          actionFont: xsollaPagesThemeValues.typography.actionFont,
        }
      : {
          bodyFont: siteBuilderThemeValues.typography.bodyFont,
          sectionHeadingFont:
            siteBuilderThemeValues.typography.sectionHeadingFont,
          actionFont: siteBuilderThemeValues.typography.actionFont,
        };

  const paletteOverrides = { ...palette };
  delete paletteOverrides?.actionText;
  mapGroup(
    'palette',
    paletteOverrides,
    variables,
    (_, color) => String(color),
    publicKeys.palette,
  );
  if (accent) {
    const cardBackground = palette?.cardBackground as string | undefined;
    const actionColors = resolveActionColors(
      accent,
      palette?.actionText as string | undefined,
      cardBackground ?? '#ffffff',
    );
    const safeActionColors = {
      actionText: actionColors.text,
      hover: actionColors.hover,
      pressed: actionColors.pressed,
      ...(cardBackground ? { focus: actionColors.focus } : {}),
    };
    mapGroup(
      'palette',
      safeActionColors,
      variables,
      (_, color) => String(color),
      derivedPaletteKeys,
    );
  } else if (palette?.cardBackground) {
    const cardBackground = palette.cardBackground as string;
    const focus = isActionTextAccessible(cardBackground, '#000000')
      ? '#000000'
      : '#ffffff';
    mapGroup(
      'palette',
      { focus },
      variables,
      (_, color) => String(color),
      derivedPaletteKeys,
    );
  }
  mapGroup(
    'typography',
    typography,
    variables,
    (key, font) => typographyCss(key, font, baseFonts),
    publicKeys.typography,
  );
  mapGroup('geometry', geometry, variables, geometryCss, publicKeys.geometry);
  const columnCount = geometry?.columns;
  const maxWidthVariable = customVariable('geometry', 'columnsMaxWidth');
  if (
    typeof columnCount === 'number' &&
    Number.isInteger(columnCount) &&
    columnCount >= 1 &&
    columnCount <= 4 &&
    maxWidthVariable
  ) {
    variables[maxWidthVariable] = getGridColumnsMaxWidth(columnCount);
  }
  return assignInlineVars(variables);
}
```

## projects/quest-platform/quests-block/src/themes/README.md
```
# Quest themes

Themes select card presentation, placement, and default appearance. The shared
block owns data loading, quest state, reward content, action eligibility, and
editable text refs. `QuestThemeBoundary` resolves saved settings once, and
`BlockFrame` applies the selected root class around every view, including
skeletons and editor previews.

## Adding a theme

1. Choose a stable ID and add it to `ThemeId` in `theme-types.ts`.
2. Add a `ThemeDefinition` in `registry.ts`. Supply a theme root class, the
   placement mode, default action variants, and a card template that composes
   the shared slots.
3. Map every typed slot from `theme-contract.css.ts` in the theme folder with
   vanilla-extract `createTheme`. Site Builder aliases the existing native
   `vars` and `typo` tokens. Alternative themes assign scoped values from an
   immutable design reference. Shared `block.css.ts` styles and theme templates
   must consume these slots, including frame surfaces and owned reward, status,
   progress, and action presentation.
4. Register the theme root class and contract class in `registry.ts`. Keep the
   contract class on standalone cards as well as `BlockFrame`, so helper and
   editor rendering resolves the same variables.
5. Add the ID to `theme-schema.ts` and `resolveThemeId` in
   `theme-appearance.ts`. Keep unknown or missing IDs resolving to Site Builder
   without changing saved data.
6. Add its default appearance in `theme-appearance.ts`. If users can select it,
   add the option in `theme-settings.tsx` and its label in
   `@quest-platform/common/src/translations.ts`.
7. Implement layout and styles beneath the theme root. Reuse shared card
   behavior. Do not put auth, API calls, storage, runtime AI, or other side
   effects in theme modules.
8. Add tests for the registry, shared slots, layout, server markup, initial
   hydration, simulation, and mixed-theme roots. Preserve callback eligibility
   and title/description refs.
9. Verify the actual block frame at 1440px, 768px, and 375px. Review skeleton,
   hint, error, unavailable, loading, and simulated states, plus long content
   and multiple theme versions. Save before/after evidence with the change.

## Shared card contract

`QuestCardTemplate` receives the chosen `kind`, `appearance`, state flags, and
shared slots for title, description, image, rewards, status, progress, action,
and notice. Templates decide where these slots appear; they do not create quest
state or action callbacks. The `pages` layout renders every selected quest in
one responsive image-first grid through `PagesQuestListLayout`; simulations and
skeletons use the same placement recipe without mounting live queries. The Pages
grid has no featured first card, pagination, or horizontal card rail.

Use CSS media queries rather than reading viewport width during render. Keep
selectors scoped beneath the registered theme root and keep versioned CSS
identifier generation in `custom.config.ts` and `css-identifiers.ts`.

## Responsive and Custom appearance changes

Measure each theme against its actual host page before changing layout. Compare
the neighboring content edges and type family, size, weight, line height, color,
spacing, card gaps, radii, and action placement at desktop, tablet, and mobile
widths. Include artwork and no-artwork cards, long text, all meaningful states,
keyboard focus, reduced motion, and more than one block instance.

Custom values are optional overrides. When a field is omitted, preserve the
selected base preset's value, including differences between featured and regular
cards. Add a contract role when separate semantic consumers need distinct base
defaults. Verify the actual normalized payload through `QuestThemeBoundary` and
measure computed styles for each changed consumer. Variable names in markup or
CSS output do not establish that the value reached the rendered element.

The narrow `assignInlineVars` exception is for the declared and validated Custom
appearance variables only. Keep all rules and breakpoints in Vanilla Extract
`.css.ts` files. Do not add arbitrary CSS strings, stylesheet injection, runtime
font loading, or browser-width reads. Host font aliases map to real host theme
roles. A loaded font keeps the selected preset's role stack as its fallback.

Responsive page rails expose visible, keyboard-operable page controls and a
current page indicator at every width. Support first, middle, final, and
out-of-range indices for 0, 1, 2, 3, 4, 7, 10, and 24 selected items. Clamp
columns and card widths so they fit the available content box. Do not conceal
layout overflow. Keep the Pages artwork-present feature at its measured 353px
desktop height with equal image and content halves; no-artwork cards use the
compact content layout.

## Pinned design sources

The Pages implementation follows the immutable sources recorded in
`task-4-reference.md` (path inside the block repo, link removed in this snapshot):
the Quests component and card in `xsolla/pages_design` at
`fb45e8176f88aa3317127c3ec7a4e973e6fe077e`, and neighboring Games styling in
`monetization-integration/sb-custom-blocks` at
`76f106939b0e59fad3dbf9e0313e467f9a18cc04`. The retained local comparison is a
visual aid, not a source of product copy or artwork.
```
