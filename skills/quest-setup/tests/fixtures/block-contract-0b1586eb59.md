# Quests block contract snapshot

Source: sb-custom-blocks-quests git objects, read with git show by the pipeline orchestrator (2026-11-03). Primary commit 0b1586eb59 (0.2.7). Also 87d7aaf4f7 (0.1.12 stable), 7c251007b6 (0.2.8), f0ec907f69 (0.2.1 candidate with backpackAction). Test fixture only, not shipped as skill guidance.

## 0b1586eb59 projects/quest-platform/quests-block/src/block.config.ts
```ts
import { defineBlockConfig, field } from '@mit/ui-components/editor';
import {
  DEFAULT_MAX_QUESTS,
  MAX_QUESTS,
} from '@quest-platform/common/initial-view';
import { type Overrides } from '@quest-platform/common/overrides';
import { TRANSLATIONS } from '@quest-platform/common/translations';
import { localizedValueRef } from '@site-builder/block-helpers';
import { z } from 'zod';

import { cardOverridesSchema } from './card-overrides-schema';
import { editorPreviewField } from './editor-preview-fields';
import { layoutField } from './layout-fields';
import { themeAppearanceMapSchema } from './themes/theme-schema';

import type { ThemeAppearanceMap } from './themes/theme-types';

const translationsField = field.translations(TRANSLATIONS);
const backwardCompatibleTranslationsField = {
  ...translationsField,
  // New copy falls back through useTranslation when a saved block has no ref.
  // Keep the defaults for newly-created blocks, while accepting older partial
  // maps and preserving translation keys introduced by newer block versions.
  _zod: translationsField._zod.partial().catchall(localizedValueRef()),
};

export const config = defineBlockConfig({
  fields: {
    // A plain string schema preserves IDs introduced by later block versions.
    themeId: field.custom({
      label: TRANSLATIONS['editor.theme']['en-US'],
      // Schema defaults are applied when parsing a saved block. The field's
      // `_default` only supplies new-block data and does not make the schema
      // accept a missing value on upgrade.
      zod: z.string().default('site-builder'),
      default: 'site-builder',
      componentKey: 'questTheme',
    }),
    themeAppearance: field.custom({
      label: TRANSLATIONS['editor.theme_custom']['en-US'],
      zod: themeAppearanceMapSchema.optional(),
      default: undefined as ThemeAppearanceMap | undefined,
      componentKey: 'themeAppearance',
    }),
    translations: backwardCompatibleTranslationsField,
    // No default on purpose: an absent value marks a block that has never had
    // a selection, which the editor fills once (see default-quest-selection).
    // A merchant-cleared selection is saved as [] and is never refilled.
    questIds: field.custom({
      label: TRANSLATIONS['editor.quests']['en-US'],
      zod: z.array(z.string()).max(MAX_QUESTS).optional(),
      default: undefined as string[] | undefined,
      componentKey: 'questPicker',
    }),
    // numberField has no min/max options, so the bound is set on its zod
    // schema. The block also clamps at runtime (clampMaxQuests).
    maxQuests: {
      ...field.numberField({
        label: TRANSLATIONS['editor.max_quests']['en-US'],
        default: DEFAULT_MAX_QUESTS,
      }),
      _zod: z.number().int().min(1).max(MAX_QUESTS),
    },
    // Each row is `event_name:period`, period once|day|week|session. Invalid rows
    // are ignored. Older saved blocks lack the key, so the schema defaults it.
    autoEvents: {
      ...field.multiple(
        field.text({
          label: TRANSLATIONS['editor.auto_event_row']['en-US'],
        }),
        {
          label: TRANSLATIONS['editor.auto_events']['en-US'],
          itemLabel: TRANSLATIONS['editor.auto_event_row']['en-US'],
          addLabel: TRANSLATIONS['editor.auto_event_add']['en-US'],
        },
      ),
      _zod: z.array(z.string()).default([]),
    },
    // Legacy single event, kept so saved blocks still parse. It is hidden from the
    // editor and used only when autoEvents yields nothing (as `<name>:once`).
    loginEventName: {
      ...field.text({
        label: TRANSLATIONS['editor.login_event_name']['en-US'],
        default: '',
      }),
      _zod: z.string().trim().default(''),
    },
    // Empty text uses quest content. Media refs coexist with older image URLs.
    overrides: field.custom({
      label: TRANSLATIONS['editor.card_overrides']['en-US'],
      zod: cardOverridesSchema,
      default: {} as Overrides,
      componentKey: 'cardOverrides',
    }),
    layout: layoutField,
    editorPreview: editorPreviewField,
  },
  groups: [
    // `overrides` is edited inside the quest list (each quest's row opens its
    // card customization), like the native Reward system block keeps a list
    // item's settings with the item, so it has no group of its own.
    {
      label: TRANSLATIONS['editor.content']['en-US'],
      fields: ['questIds', 'maxQuests', 'autoEvents'],
    },
    {
      label: TRANSLATIONS['editor.layout']['en-US'],
      fields: ['themeId', 'themeAppearance', 'layout'],
    },
    {
      label: TRANSLATIONS['editor.preview']['en-US'],
      fields: ['editorPreview'],
    },
  ],
});
```

## 0b1586eb59 projects/quest-platform/quests-block/src/layout-schema.ts
```ts
import { z } from 'zod';

import { LAYOUT_DEFAULTS } from './layout';

export const layoutSchema = z
  .object({
    showHeading: z.boolean().default(LAYOUT_DEFAULTS.showHeading),
    showDescription: z.boolean().default(LAYOUT_DEFAULTS.showDescription),
    showImage: z.boolean().default(LAYOUT_DEFAULTS.showImage),
    cardAlign: z
      .union([z.literal('start'), z.literal('center'), z.literal('end')])
      .default(LAYOUT_DEFAULTS.cardAlign),
    imageFit: z
      .union([z.literal('cover'), z.literal('contain')])
      .default(LAYOUT_DEFAULTS.imageFit),
    buttonStyle: z
      .union([
        z.literal('primary'),
        z.literal('secondary'),
        z.literal('tertiary'),
      ])
      .default(LAYOUT_DEFAULTS.buttonStyle),
    blockBackground: z
      .union([
        z.literal('transparent'),
        z.literal('primary'),
        z.literal('secondary'),
      ])
      .default(LAYOUT_DEFAULTS.blockBackground),
    cardBackground: z
      .union([
        z.literal('transparent'),
        z.literal('primary'),
        z.literal('secondary'),
      ])
      .default(LAYOUT_DEFAULTS.cardBackground),
  })
  .default(LAYOUT_DEFAULTS);
```

## 0b1586eb59 projects/quest-platform/quests-block/src/themes/theme-schema.ts
```ts
import { z } from 'zod';

const cardAlignSchema = z.union([
  z.literal('start'),
  z.literal('center'),
  z.literal('end'),
]);

const blockBackgroundSchema = z.union([
  z.literal('transparent'),
  z.literal('primary'),
  z.literal('secondary'),
]);

const buttonStyleSchema = z.union([
  z.literal('primary'),
  z.literal('secondary'),
  z.literal('tertiary'),
  z.literal('theme-default'),
]);

export const themeAppearanceSchema = z
  .object({
    cardAlign: cardAlignSchema.optional(),
    blockBackground: blockBackgroundSchema.optional(),
    cardBackground: blockBackgroundSchema.optional(),
    buttonStyle: buttonStyleSchema.optional(),
  })
  .passthrough();

export const themeAppearanceMapSchema = z.record(z.string(), z.unknown());
```

## 0b1586eb59 projects/quest-platform/quests-block/src/themes/theme-types.ts
```ts
import type { ComponentType, ReactNode } from 'react';

import type { QuestLayout } from '../layout';
import type { Card } from '@quest-platform/common/merge';
import type { assignInlineVars } from '@vanilla-extract/dynamic';

export type ThemeId = 'site-builder' | 'xsolla-pages' | 'custom';

export type ThemeAppearance = Pick<
  QuestLayout,
  'cardAlign' | 'blockBackground' | 'cardBackground'
> & {
  buttonStyle: QuestLayout['buttonStyle'] | 'theme-default';
};

export type ThemeAppearanceMap = Record<
  string,
  Partial<ThemeAppearance> & Record<string, unknown>
>;

export type QuestCardKind = 'grid' | 'featured' | 'regular';

export type QuestCardSlots = {
  title: ReactNode;
  description: ReactNode;
  image: ReactNode;
  rewards: ReactNode;
  status: ReactNode;
  progress: ReactNode;
  action: ReactNode;
  notice: ReactNode;
};

export type QuestCardTemplateProps = {
  kind: QuestCardKind;
  className?: string;
  /** Semantic CSS variable map for cards rendered outside a BlockFrame. */
  contractClassName?: string;
  /** Custom scope and validated VE variables for standalone card rendering. */
  customClassName?: string;
  customVars?: ReturnType<typeof assignInlineVars>;
  slots: QuestCardSlots;
  /** True when the block's image setting is enabled, even if art is unavailable. */
  imageEnabled: boolean;
  appearance: ThemeAppearance;
  state: Card['state'];
  rewardPending: boolean;
};

export type ThemeDefinition = {
  id: ThemeId;
  labelId: string;
  rootClass: string;
  contractClass: string;
  customClassName?: string;
  layout: 'grid' | 'pages';
  defaultButtonVariants: Record<QuestCardKind, QuestLayout['buttonStyle']>;
  CardTemplate: ComponentType<QuestCardTemplateProps>;
};
```

## 0b1586eb59 projects/quest-platform/quests-block/src/themes/registry.ts
```ts
import { customRoot } from './custom/theme.css';
import { SiteBuilderCardTemplate } from './site-builder/card-template';
import { siteBuilderTheme } from './site-builder/theme.css';
import { themeRoot } from './theme-contract.css';
import { PagesCardTemplate } from './xsolla-pages/card-template';
import * as pagesStyles from './xsolla-pages/styles.css';
import { xsollaPagesTheme } from './xsolla-pages/theme.css';

import type { ThemeDefinition } from './theme-types';

export const SITE_BUILDER_THEME: ThemeDefinition = {
  id: 'site-builder',
  labelId: 'editor.theme_site_builder',
  rootClass: `${themeRoot} ${siteBuilderTheme}`,
  contractClass: siteBuilderTheme,
  layout: 'grid',
  defaultButtonVariants: {
    grid: 'primary',
    featured: 'primary',
    regular: 'secondary',
  },
  CardTemplate: SiteBuilderCardTemplate,
};

export const XSOLLA_PAGES_THEME: ThemeDefinition = {
  id: 'xsolla-pages',
  labelId: 'editor.theme_xsolla_pages',
  rootClass: `${themeRoot} ${xsollaPagesTheme} ${pagesStyles.root}`,
  contractClass: xsollaPagesTheme,
  layout: 'pages',
  defaultButtonVariants: {
    grid: 'primary',
    featured: 'primary',
    regular: 'secondary',
  },
  CardTemplate: PagesCardTemplate,
};

const themes: Record<string, ThemeDefinition> = {
  'site-builder': SITE_BUILDER_THEME,
  'xsolla-pages': XSOLLA_PAGES_THEME,
};

export function resolveTheme(
  value: unknown,
  customBase: 'site-builder' | 'xsolla-pages' = 'site-builder',
): ThemeDefinition {
  if (value === 'custom') {
    const base = themes[customBase];
    return {
      ...base,
      id: 'custom',
      labelId: 'editor.theme_custom',
      rootClass: `${base.rootClass} ${customRoot}`,
      // Card templates receive this class set too. Keep the section-only root
      // styles (notably Pages section padding) off individual card articles.
      customClassName: `${base.contractClass} ${customRoot}`,
    };
  }
  return typeof value === 'string'
    ? (themes[value] ?? SITE_BUILDER_THEME)
    : SITE_BUILDER_THEME;
}
```

## 0b1586eb59 projects/quest-platform/quests-block/src/card-overrides-schema.ts
```ts
import { isHttpsUrl } from '@quest-platform/common/overrides';
import { imageValueRef, localizedValueRef } from '@site-builder/block-helpers';
import { z } from 'zod';

export const cardOverridesSchema = z.record(
  z.string(),
  z.object({
    // Inline-edited card texts, created on first click on the editor canvas.
    titleRef: localizedValueRef().optional(),
    descriptionRef: localizedValueRef().optional(),
    // Legacy, ignored: rewards became read-only (they come from the quest
    // definition). Still accepted so sites saved with these fields parse.
    rewardRef: localizedValueRef().optional(),
    // Plain-text overrides from before inline editing. No longer editable,
    // still read so saved sites keep their text.
    title: z.string().max(120).optional(),
    description: z.string().max(400).optional(),
    // Retain previously saved direct image overrides.
    imageUrl: z
      .string()
      .refine(isHttpsUrl, 'Image URL must be https')
      .optional(),
    imageRef: imageValueRef().optional(),
    // Legacy, ignored: see rewardRef above.
    rewardText: z.string().max(120).optional(),
    rewardImageUrl: z
      .string()
      .refine(isHttpsUrl, 'Image URL must be https')
      .optional(),
  }),
);
```

## 0b1586eb59 projects/quest-platform/quests-block/package.json
```ts
{
  "name": "@quest-platform/quests-block",
  "description": "Quests block",
  "version": "0.2.7",
  "type": "module",
  "bundleSizeBudgetKb": 240,
  "scripts": {
    "dev": "vite",
    "build": "custom-build-block",
    "lint:check": "eslint .",
    "lint": "eslint . --fix",
    "prettier:check": "pnpm exec prettier . --check",
    "prettier": "pnpm exec prettier . --write",
    "serve": "pnpm dlx serve ./dist -p 5173 --cors",
    "preview": "vite preview",
    "test": "vitest run"
  },
  "dependencies": {
    "@mit/intl": "workspace:*",
    "@mit/ui-components": "workspace:*",
    "@mit/utils": "workspace:*",
    "@module-federation/runtime": "catalog:libs",
    "@sb-custom-blocks/css-utils": "workspace:*",
    "@site-builder/block-utils": "catalog:sb-sdk",
    "@site-builder/block-helpers": "catalog:sb-sdk",
    "@vanilla-extract/css": "catalog:libs",
    "react": "catalog:react-core",
    "react-dom": "catalog:react-core",
    "zod": "catalog:libs",
    "@quest-platform/common": "workspace:*",
    "@tanstack/react-query": "^5.84.1",
    "@vanilla-extract/dynamic": "catalog:libs"
  },
  "devDependencies": {
    "@site-builder/vite-plugin": "catalog:sb-sdk",
    "@types/react": "catalog:react-core",
    "@types/react-dom": "catalog:react-core",
    "@vanilla-extract/vite-plugin": "catalog:libs",
    "@vitejs/plugin-react": "catalog:react-core",
    "typescript": "catalog:dev-tools",
    "vite": "catalog:dev-tools",
    "vitest": "catalog:dev-tools",
    "eslint": "catalog:dev-tools",
    "prettier": "catalog:dev-tools",
    "@mit/eslint-config": "workspace:*",
    "@mit/prettier-config": "workspace:*",
    "@mit/typescript-config": "workspace:*",
    "@mit/vite-config": "workspace:*"
  }
}
```

## 87d7aaf4f7 projects/quest-platform/quests-block/src/block.config.ts
```ts
import { defineBlockConfig, field } from '@mit/ui-components/editor';
import {
  DEFAULT_MAX_QUESTS,
  MAX_QUESTS,
} from '@quest-platform/common/initial-view';
import { type Overrides } from '@quest-platform/common/overrides';
import { TRANSLATIONS } from '@quest-platform/common/translations';
import { z } from 'zod';

import { cardOverridesSchema } from './card-overrides-schema';
import { editorPreviewField } from './editor-preview-fields';
import { layoutField } from './layout-fields';

export const config = defineBlockConfig({
  fields: {
    translations: field.translations(TRANSLATIONS),
    // No default on purpose: an absent value marks a block that has never had
    // a selection, which the editor fills once (see default-quest-selection).
    // A merchant-cleared selection is saved as [] and is never refilled.
    questIds: field.custom({
      label: TRANSLATIONS['editor.quests']['en-US'],
      zod: z.array(z.string()).max(MAX_QUESTS).optional(),
      default: undefined as string[] | undefined,
      componentKey: 'questPicker',
    }),
    // numberField has no min/max options, so the bound is set on its zod
    // schema. The block also clamps at runtime (clampMaxQuests).
    maxQuests: {
      ...field.numberField({
        label: TRANSLATIONS['editor.max_quests']['en-US'],
        default: DEFAULT_MAX_QUESTS,
      }),
      _zod: z.number().int().min(1).max(MAX_QUESTS),
    },
    // Empty text uses quest content. Media refs coexist with older image URLs.
    overrides: field.custom({
      label: TRANSLATIONS['editor.card_overrides']['en-US'],
      zod: cardOverridesSchema,
      default: {} as Overrides,
      componentKey: 'cardOverrides',
    }),
    layout: layoutField,
    editorPreview: editorPreviewField,
  },
  groups: [
    // `overrides` is edited inside the quest list (each quest's row opens its
    // card customization), like the native Reward system block keeps a list
    // item's settings with the item, so it has no group of its own.
    {
      label: TRANSLATIONS['editor.content']['en-US'],
      fields: ['questIds', 'maxQuests'],
    },
    { label: TRANSLATIONS['editor.layout']['en-US'], fields: ['layout'] },
    {
      label: TRANSLATIONS['editor.preview']['en-US'],
      fields: ['editorPreview'],
    },
  ],
});
```

## 7c251007b6 projects/quest-platform/quests-block/src/block.config.ts
```ts
import { defineBlockConfig, field } from '@mit/ui-components/editor';
import {
  DEFAULT_MAX_QUESTS,
  MAX_QUESTS,
} from '@quest-platform/common/initial-view';
import { type Overrides } from '@quest-platform/common/overrides';
import { TRANSLATIONS } from '@quest-platform/common/translations';
import { localizedValueRef } from '@site-builder/block-helpers';
import { z } from 'zod';

import { cardOverridesSchema } from './card-overrides-schema';
import { editorPreviewField } from './editor-preview-fields';
import { layoutField } from './layout-fields';
import { themeAppearanceMapSchema } from './themes/theme-schema';

import type { ThemeAppearanceMap } from './themes/theme-types';

const translationsField = field.translations(TRANSLATIONS);
const backwardCompatibleTranslationsField = {
  ...translationsField,
  // New copy falls back through useTranslation when a saved block has no ref.
  // Keep the defaults for newly-created blocks, while accepting older partial
  // maps and preserving translation keys introduced by newer block versions.
  _zod: translationsField._zod.partial().catchall(localizedValueRef()),
};

export const config = defineBlockConfig({
  fields: {
    // A plain string schema preserves IDs introduced by later block versions.
    themeId: field.custom({
      label: TRANSLATIONS['editor.theme']['en-US'],
      // Schema defaults are applied when parsing a saved block. The field's
      // `_default` only supplies new-block data and does not make the schema
      // accept a missing value on upgrade.
      zod: z.string().default('site-builder'),
      default: 'site-builder',
      componentKey: 'questTheme',
    }),
    themeAppearance: field.custom({
      label: TRANSLATIONS['editor.theme_custom']['en-US'],
      zod: themeAppearanceMapSchema.optional(),
      default: undefined as ThemeAppearanceMap | undefined,
      componentKey: 'themeAppearance',
    }),
    translations: backwardCompatibleTranslationsField,
    // No default on purpose: an absent value marks a block that has never had
    // a selection, which the editor fills once (see default-quest-selection).
    // A merchant-cleared selection is saved as [] and is never refilled.
    questIds: field.custom({
      label: TRANSLATIONS['editor.quests']['en-US'],
      zod: z.array(z.string()).max(MAX_QUESTS).optional(),
      default: undefined as string[] | undefined,
      componentKey: 'questPicker',
    }),
    // numberField has no min/max options, so the bound is set on its zod
    // schema. The block also clamps at runtime (clampMaxQuests).
    maxQuests: {
      ...field.numberField({
        label: TRANSLATIONS['editor.max_quests']['en-US'],
        default: DEFAULT_MAX_QUESTS,
      }),
      _zod: z.number().int().min(1).max(MAX_QUESTS),
    },
    // Automatic events are fixed (BUILT_IN_AUTO_EVENTS), so there is no setting.
    // Saved `autoEvents` and `loginEventName` from older versions are not in the
    // schema, so the parse drops them and they have no effect.
    // Empty text uses quest content. Media refs coexist with older image URLs.
    overrides: field.custom({
      label: TRANSLATIONS['editor.card_overrides']['en-US'],
      zod: cardOverridesSchema,
      default: {} as Overrides,
      componentKey: 'cardOverrides',
    }),
    layout: layoutField,
    editorPreview: editorPreviewField,
  },
  groups: [
    // `overrides` is edited inside the quest list (each quest's row opens its
    // card customization), like the native Reward system block keeps a list
    // item's settings with the item, so it has no group of its own.
    {
      label: TRANSLATIONS['editor.content']['en-US'],
      fields: ['questIds', 'maxQuests'],
    },
    {
      label: TRANSLATIONS['editor.layout']['en-US'],
      fields: ['themeId', 'themeAppearance', 'layout'],
    },
    {
      label: TRANSLATIONS['editor.preview']['en-US'],
      fields: ['editorPreview'],
    },
  ],
});
```

## f0ec907f69 projects/quest-platform/quests-block/src/block.config.ts
```ts
import { defineBlockConfig, field } from '@mit/ui-components/editor';
import {
  DEFAULT_MAX_QUESTS,
  MAX_QUESTS,
} from '@quest-platform/common/initial-view';
import { type Overrides } from '@quest-platform/common/overrides';
import { TRANSLATIONS } from '@quest-platform/common/translations';
import { localizedValueRef } from '@site-builder/block-helpers';
import { z } from 'zod';

import { cardOverridesSchema } from './card-overrides-schema';
import { editorPreviewField } from './editor-preview-fields';
import { layoutField } from './layout-fields';
import { themeAppearanceMapSchema } from './themes/theme-schema';

import type { ThemeAppearanceMap } from './themes/theme-types';

const translationsField = field.translations(TRANSLATIONS);
const backwardCompatibleTranslationsField = {
  ...translationsField,
  // New copy falls back through useTranslation when a saved block has no ref.
  // Keep the defaults for newly-created blocks, while accepting older partial
  // maps and preserving translation keys introduced by newer block versions.
  _zod: translationsField._zod.partial().catchall(localizedValueRef()),
};

export const config = defineBlockConfig({
  fields: {
    // A plain string schema preserves IDs introduced by later block versions.
    themeId: field.custom({
      label: TRANSLATIONS['editor.theme']['en-US'],
      // Schema defaults are applied when parsing a saved block. The field's
      // `_default` only supplies new-block data and does not make the schema
      // accept a missing value on upgrade.
      zod: z.string().default('site-builder'),
      default: 'site-builder',
      componentKey: 'questTheme',
    }),
    themeAppearance: field.custom({
      label: TRANSLATIONS['editor.theme_custom']['en-US'],
      zod: themeAppearanceMapSchema.optional(),
      default: undefined as ThemeAppearanceMap | undefined,
      componentKey: 'themeAppearance',
    }),
    translations: backwardCompatibleTranslationsField,
    // No default on purpose: an absent value marks a block that has never had
    // a selection, which the editor fills once (see default-quest-selection).
    // A merchant-cleared selection is saved as [] and is never refilled.
    questIds: field.custom({
      label: TRANSLATIONS['editor.quests']['en-US'],
      zod: z.array(z.string()).max(MAX_QUESTS).optional(),
      default: undefined as string[] | undefined,
      componentKey: 'questPicker',
    }),
    // numberField has no min/max options, so the bound is set on its zod
    // schema. The block also clamps at runtime (clampMaxQuests).
    maxQuests: {
      ...field.numberField({
        label: TRANSLATIONS['editor.max_quests']['en-US'],
        default: DEFAULT_MAX_QUESTS,
      }),
      _zod: z.number().int().min(1).max(MAX_QUESTS),
    },
    // Empty text uses quest content. Media refs coexist with older image URLs.
    overrides: field.custom({
      label: TRANSLATIONS['editor.card_overrides']['en-US'],
      zod: cardOverridesSchema,
      default: {} as Overrides,
      componentKey: 'cardOverrides',
    }),
    layout: layoutField,
    backpackAction: field.custom({
      label: TRANSLATIONS['editor.backpack_action']['en-US'],
      zod: z
        .enum(['external', 'overlay'])
        .catch('external')
        .default('external'),
      default: 'external' as const,
      componentKey: 'backpackAction',
    }),
    editorPreview: editorPreviewField,
  },
  groups: [
    // `overrides` is edited inside the quest list (each quest's row opens its
    // card customization), like the native Reward system block keeps a list
    // item's settings with the item, so it has no group of its own.
    {
      label: TRANSLATIONS['editor.content']['en-US'],
      fields: ['questIds', 'maxQuests'],
    },
    {
      label: TRANSLATIONS['editor.layout']['en-US'],
      fields: ['themeId', 'themeAppearance', 'layout'],
    },
    {
      label: TRANSLATIONS['editor.preview']['en-US'],
      fields: ['editorPreview'],
    },
    {
      label: TRANSLATIONS['editor.backpack']['en-US'],
      fields: ['backpackAction'],
    },
  ],
});
```

