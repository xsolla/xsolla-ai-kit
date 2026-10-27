# LiveOps: offers, limits, rewards and promotions

A shop with a few products and nothing else gives players no reason to come back. Propose
these mechanics by default; the developer shouldn't have to know them and ask for each one.
Verified against the Xsolla docs and the `xsolla liveops` and `xsolla catalog` commands of
CLI 1.9.4 on 2026-10-27. Verify each request body via the Xsolla MCP before calling, as for
the rest of this skill.

## What to offer

Pick a coherent set for the game, not every row. Most of them need player login: without it,
players see the offer but can't claim it, and per-player limits can't apply.

| Mechanic | What the player gets | Set up with | Needs login |
|---|---|---|---|
| Starter pack | A bundle sold once per player | Bundle with `limits.per_user` total 1 | Yes |
| First-purchase bonus | Extra items with their first paid order | Bonus promotion with `attribute_conditions` `has_purchase` `eq` `0` and `limits.per_user` 1 (`xsolla liveops create-bonus`) | Yes |
| Time-limited offer | An item shown only between two dates | Item `periods` (ISO 8601) | No |
| Limited stock | A fixed number of copies across all players | Item `limits.per_item` | No |
| Per-player limit | N purchases per player, optionally reset daily, weekly or monthly | Item `limits.per_user`, `limits.recurrent_schedule` | Yes |
| Scheduled sale | A discount or bonus between two dates | `promotion_periods` on a discount or bonus (`create-discount`, `create-bonus`) | No |
| Offer chain | Free and paid steps that unlock one after another | `xsolla liveops create-offer-chain` | Yes |
| Daily rewards | A free item for each day the player logs in | `xsolla liveops create-daily-chain` | Yes |
| Loyalty | Value points for each purchase, rewards at thresholds | `create-value-point`, `update-value-point-rewards`, `create-reward-chain` | Yes |
| Promo codes | A discount or bonus items at checkout | `create-promo-codes`, then `generate-promo-codes` | No |

Facts that change the proposal:

- **Web prices.** The Web Shop docs say a web price should not be lower than the price on the
  game's publishing platforms. Make bonuses, not discounts, the default web incentive.
- **First purchase.** Use a bonus or discount for first-time buyers (`has_purchase` condition,
  per-user limit 1); it needs Xsolla Login. A refund doesn't make the player eligible again.
- **Limits.** Unauthenticated players always see the maximum quantity. A refund or a canceled
  order doesn't reset a limit. `limits.per_user.limit_exceeded_visibility` applies only with a
  `recurrent_schedule`.
- **Chains ignore item settings.** Offer chains and daily rewards ignore the item's purchase
  limits, scheduled availability, promotions and personalization. An offer chain has at most 30
  steps, a reward chain 31. Only one daily chain of the login-reward type can be active at a time.
- **Activation.** Promotions are created inactive: activate them with `is_enabled: true` or
  `xsolla liveops activate-promotions`. Promo code promotions also start with no codes:
  `generate-promo-codes`. Chains take `is_enabled: true` or `toggle-*`. An active promotion or
  chain can't be edited; deactivate it first.
- **Loyalty points.** Use separate value points for separate reward chains; chains that share
  them share one balance, and a reset clears it everywhere.

## How to propose it

1. Read what the project already has: `xsolla liveops list-promotions`, `list-promo-codes`,
   `list-coupons`, `list-offer-chain`, `list-daily-chain`, `list-reward-chain`,
   `list-value-point`, and the catalog. Reuse what
   exists; never create a duplicate.
2. Propose the set in one message. For each mechanic: what the player gets, why it helps this
   game, and what is still to connect (player login, delivery to the game).
3. In the same message, ask once for the commercial values that are missing: reward quantities,
   stock limits, campaign dates and time zone, who is eligible, and how items reach the game.
   Show every value as proposed or confirmed. Never write a proposed value as if the developer
   had set it.
4. After the developer's yes, create in dependency order: items and bundles → their limits and
   periods → promotions → chains and value points → activation. Read each one back.
5. Tell the storefront what is live. On the Shop Builder path, `description-to-shop` lists
   it in the shop brief's `catalog.liveops` (`promo_codes` for promo codes or coupons,
   `reward_chain`, `offer_chain`), so assembly adds the matching blocks. Assembly can't add a daily rewards block yet: say so in the handoff.

## Docs

- [Item purchase limits](https://developers.xsolla.com/items-catalog/catalog-features/items-catalog-number-limits/),
  [display time](https://developers.xsolla.com/items-catalog/catalog-features/limiting-display-time/),
  [promotion limits](https://developers.xsolla.com/liveops/promotion-tools/liveops-number-limits/)
- [First purchase](https://developers.xsolla.com/liveops/liveops-management/first-purchase/),
  [bonuses](https://developers.xsolla.com/liveops/promotion-tools/bonuses/),
  [discounts](https://developers.xsolla.com/liveops/promotion-tools/discounts/),
  [promo codes](https://developers.xsolla.com/liveops/promotion-tools/promo-codes/),
  [coupons](https://developers.xsolla.com/liveops/promotion-tools/coupons/)
- [Offer chains](https://developers.xsolla.com/liveops/promotion-tools/offer-chains/),
  [daily rewards](https://developers.xsolla.com/liveops/promotion-tools/daily-rewards/),
  [reward system](https://developers.xsolla.com/liveops/promotion-tools/reward-system/),
  [personalization](https://developers.xsolla.com/liveops/promotion-tools/personalization/)
