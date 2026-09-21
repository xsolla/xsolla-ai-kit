# Is a custom block the right choice?

A custom block is the escape hatch, not the default. This page is the decision, and the bill
that comes with choosing wrong.

## The order to try things in

1. **A standard block**, themed. 23 of them ship; the list is below.
2. **A standard block plus a field you can set** — check whether what you want already exists
   in that block's `values` before concluding it does not.
3. **The `html` block ("Custom code")** — arbitrary markup with no compile step, no bundle and
   nothing for you to maintain. If the need is "embed this widget" or "one odd bit of markup",
   this is the answer and a compiled block is over-engineering.
4. **A federated block**, if one nearly fits: `sb-offer-chain`, `sb-daily-reward`,
   `social-quests`, `offerwall-block`.
5. **A custom block**, only once 1–4 are genuinely ruled out.

## Use a standard block when

| Signal | Use instead |
|---|---|
| A headline, some copy and a button | `hero` |
| A block of body copy | `description` |
| Question-and-answer pairs | `faq` |
| A grid or carousel of images | `gallery`, `promoSlider`, `bento-grid` |
| It sells catalog items | `newStore`, `packs`, `subscriptions-packs` |
| It collects an email or a lead | `lead`, `leadGameSales` |
| System requirements, sellers, or news | `requirements`, `retailers`, `news` |
| A promo-code entry field | `promocodes` |
| Sign-in on the page | `fast-login` |
| A social or third-party widget | `embed` |
| Arbitrary markup, no interaction with the editor | `html` |
| Which payment methods are accepted | `payment-methods` |
| The look is wrong but the content shape is right | **Theme the standard block** — do not clone it in React |
| An existing block plus one extra field | Ask whether the field can live in `values`. A custom clone loses every future platform fix |

## The 23 native modules

Names as the editor shows them, with the current `maxVersion`. A block write must carry
`version` equal to the module's `maxVersion`, so check this before creating one.

| Module | Editor name | maxVersion |
|---|---|---|
| `bento-grid` | Card grid | 1 |
| `description` | Description | 2 |
| `embed` | Social media widgets | 1 |
| `faq` | FAQs | 2 |
| `fast-login` | Fast Login | 1 |
| `footer` | Footer | 3 |
| `gallery` | Gallery | 2 |
| `hero` | Call-to-action | 1 |
| `html` | Custom code | 2 |
| `lead` | Lead block | 1 |
| `leadGameSales` | Lead block | 1 |
| `newStore` | Store | 1 |
| `news` | News | 2 |
| `nft` | NFT store | 1 |
| `packs` | Game packs | 2 |
| `payment-methods` | Payment methods | 1 |
| `promoSlider` | Promo slider | 1 |
| `promocodes` | Promo codes | 2 |
| `requirements` | System requirements | 2 |
| `retailers` | Sellers block | 1 |
| `rewards` | Reward system | 1 |
| `sidebar` | Sidebar | 1 |
| `subscriptions-packs` | Subscriptions | 1 |

## A custom block is warranted when

- **The interaction does not exist as a block** — a countdown, a leaderboard, a wheel, a
  progress meter, a live-ops panel.
- **It needs data from a source no block reads**, fetched at render time.
- **It composes several blocks' behaviour** into one unit that must stay in sync.
- **A federated block nearly fits** but its configuration genuinely cannot express the
  requirement.

## What you are taking on

Say this out loud to the person asking, before you build. None of it is recoverable later by
choosing differently.

| Cost | What it means in practice |
|---|---|
| **No schema** | Nothing validates the block's data field by field. A field you rename is not reported anywhere; it just stops working |
| **No platform fixes** | Standard blocks keep getting renderer fixes, accessibility work and new capabilities. Yours gets what you write |
| **No theme inheritance you can assume** | A standard block follows the site theme by construction. A custom block follows it only to the extent you wire it up — see [theming.md](theming.md) |
| **The editor can be locked** | Two of the authoring mistakes in [code-rules.md](code-rules.md) crash the settings sidebar, so the user cannot open the panel they would use to undo the damage |
| **Canvas text may be unavailable** | On the CLI write path `textFields` cannot be declared at all — see [localization.md](localization.md) |
| **Maintenance is the partner's** | A model generated it; a human owns it. Make sure the person asking knows which of those two facts matters in six months |

## Saying no is the deliverable

If a standard block fits, **say so and stop.** Name the block, describe what it would look
like, and offer to configure it. A recommendation not to build is a successful run of this
skill, not a failure to deliver.
