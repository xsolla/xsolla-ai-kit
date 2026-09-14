# Shop Builder presets

These are implementation drafts pending approval from the designated reviewer,
Andrey Pyanzin. Treat them as defaults, not permission to overwrite explicit
publisher choices.

## Mobile single page

Use for mobile-first games and focused top-up or item purchase journeys.

- `/` Home: `header → leadGameSales → newStore → faq → footer`
- Navigation: anchors or one Home link; keep purchase content above long-form copy.
- Store sections: currency packages first, then featured bundles, then virtual goods.
- Defaults: compact hero, high-contrast CTA, short FAQ, minimal outbound navigation.
- Required data: logo or game name, hero copy, at least one catalog group, locale.

## PC multi-page portal

Use when the shop also needs game information, media, requirements, or multiple
catalog entry points.

- `/` Home: `header → leadGameSales → description → gallery → footer`
- `/store` Store: `header → newStore → faq → footer`
- `/about` About: `header → description → requirements → faq → footer`
- Navigation: Home, Store, About; the primary CTA targets `/store`.
- Store sections: featured bundles, grouped virtual goods, then currency packages.
- Required data: page copy, store groups, media assets, platform requirements.

## Live service with bundles and events

Use when offers rotate, events have dates, or bundles are a primary merchandising
unit. Do not invent event dates, discounts, scarcity, or eligibility.

- `/` Home: `header → leadGameSales → newStore → gallery → faq → footer`
- `/store` Store: `header → newStore → faq → footer`
- `/events` Events: `header → leadGameSales → newStore → description → footer`
- Navigation: Home, Store, Events; event CTA links to the verified event catalog group.
- Store sections: active event bundles, featured bundles, virtual goods, currency.
- Required data: active event name/dates, bundle or group IDs, fallback content for no
  active event, locale, and event assets.

## Override rules

1. Explicit publisher page/block choices beat preset defaults.
2. Do not add a block when its required data is missing. On an existing target,
   preserve an already configured instance unchanged unless the user explicitly
   confirms its removal; report either action in the plan.
3. Do not substitute an unverified module for a missing capability.
4. Record reviewer, date, and decision here when a preset is approved.

## Validation record

| Preset | Reviewer | Date | Status |
|---|---|---|---|
| Mobile single page | Andrey Pyanzin | TBD | Draft; review pending |
| PC multi-page portal | Andrey Pyanzin | TBD | Draft; review pending |
| Live service with bundles and events | Andrey Pyanzin | TBD | Draft; review pending |
