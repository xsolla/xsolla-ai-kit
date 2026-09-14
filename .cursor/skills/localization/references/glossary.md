# Glossary detection

The glossary is the set of terms that must render **identically everywhere** — and, for
a few of them, must not be translated at all. It is **detected from the data**, not
asked for: the catalog already declares most of it, and a question the user cannot
answer well ("what shouldn't we translate?") produces a worse list than the data does.

## Why it is not a question

An English source gives no signal. `Gems` may be a currency's proper name or the plain
word, and UI strings are Title Case throughout, so capitalization means nothing —
`Web-Exclusive Offer` looks like a name and is not one. Russian or German would mark
the foreign term; English does not.

The catalog, however, declares its proper nouns **structurally**: every entity's `name`
is one by construction. If the `virtual_currency` is named `Gems`, then `Gems` inside an
item description is a reference to that currency, not a common noun. No language
understanding required.

And note what the existing translations actually do — measured on a real catalog:

| en | de |
|---|---|
| Gems | **Edelsteine** |
| Web-Exclusive Offer | **Web-exklusives Angebot** |
| Reward Point | **Belohnungspunkt** |

The currency *was* translated. The default in a game catalog is to translate almost
everything; only the game/studio/brand name usually stays. So the glossary's main job is
**consistency**, not prohibition — the real failure is one term rendered two ways, not a
term translated that shouldn't have been.

## When to run it

- **Before the first batch**, after `export` — there is nothing to detect earlier, and
  nothing to constrain later.
- **Again whenever new ids enter the working set** mid-flow (a merge brought rows in, the
  scope widened, the catalog grew). New objects can introduce new terms.

## Step 1 — collect candidates

| Signal | What it catches | How |
|---|---|---|
| **Entity names** | proper nouns by construction | every `name` value in the export; then find its occurrences inside other strings |
| **Agreement across existing locales** | terms already settled | a source term rendered *identically* in every already-translated locale is a keep-as-is term |
| **Existing translation pairs** | the decision already made | `Gems → Edelsteine` in `de` is the answer for `de`, and the model for a new locale. **Not a candidate signal on its own** — see below |
| **Project metadata** | game name | `GET https://api.xsolla.com/merchant/v2/projects/{project_id}` with **merchant** auth — Basic `base64(merchant_id:api_key)`; a project key gets `401`. Returns `name: {"en": "…"}`, plus `locale_list` and `products`. **The bundled script does not implement this call** — it is the only read the agent performs itself (read-only, so it goes through Bash directly), and it is optional: degrade gracefully when `XSOLLA_MERCHANT_ID` is absent. Studio name is not reachable at all; characters are in no Xsolla API |
| **Common game terms** | DLC, Battle Pass, Skin, Season Pass, Loot Box | those five *are* the seed list — nothing else is bundled. Weak on its own, so treat it as one signal among several, never as the basis for a decision |

**An existing translation is not a reason to add a term.** It tells you *how* to render
a term that is already a candidate; it does not make it one. Measured on a real catalog:
of 25 entity names carrying a German translation, only 4 occurred inside another string
— so counting "has a translation" as a signal promoted **22 of 25** names to "put it in
front of the user", which is the whole catalog, not the shortlist this step promises. A
glossary term is one that must render **consistently in more than one place**: that is
signal 1 (the name appears inside other strings) or signal 2 (identical across every
locale). Use the pairs to **corroborate** those candidates and to answer them — never to
generate new ones.

Never candidates — these are never translated regardless, so they must not clutter the
list: `sku` / `external_id` / `id`, promo codes, placeholders (`{name}`, `%s`, ICU),
numerals, units, and **names shaped like identifiers** — `DemoBonusPromotion`,
`reward_chain_v2` — which are internal labels that happen to sit in a `name` field. Real
catalogs carry them (three were in this project), and they are never player-facing.

## Step 2 — score confidence

Candidacy comes only from the signals that show a term must render consistently in more
than one place — entity names occurring inside other strings, agreement across locales,
project metadata, the seed terms. Existing pairs then raise or lower confidence.

- **High — two or more candidacy signals, or one plus an existing translation pair that
  confirms how the term is already rendered** → add **automatically, no question**.
  Measured on a real catalog this is where `Gems → Edelsteine` lands: it is an entity
  name appearing in ten other strings *and* already has a settled German rendering.
- **Medium — a single candidacy signal and no existing pair** → put it in front of the
  user. On the same catalog that was 2 terms, which is a shortlist someone will actually
  read.
- Anything below that → drop it; a noisy glossary is worse than a short one.

## Step 3 — confirm only the disputed ones

- Show **the medium-confidence shortlist**, not the whole glossary. Offer to print the
  full list on request.
- Offer to load the user's own glossary if they have one — it wins over detection.
- The user can add or remove terms by hand.
- **A term already rendered two different ways *within one locale* is a conflict, not a
  candidate.** `Gems` as `Edelsteine` on the currency but `Juwelen` in an item
  description means the catalog has already drifted, and which rendering wins is the
  user's call — surface it as a finding of its own. (Different renderings *between*
  locales are not drift; that is just translation. Identical renderings across every
  locale are the Step 1 keep-as-is signal.)

## Step 4 — feed it to the translator as a constraint

The glossary goes **into** the translation request as a rule to obey, not into a filter
that patches the output afterwards. Post-hoc replacement breaks agreement and case in
inflected languages (`Edelsteine` → `Edelsteinen` in dative) and produces text no
reviewer can trust.

**Repeat it in every batch.** Batches are separate model calls with no shared context;
a glossary agreed once and not re-sent will drift by the third batch.

## Step 5 — verify it held

Glossary compliance is **not** checked by `check` — it is not a deterministic property
(inflection, agreement, word order all legitimately change the surface form). It belongs
to the agent's semantic review in [qa.md](qa.md): confirm each glossary term renders
consistently across every entity type, especially a currency name that appears in
`items`, in `virtual_currency` and in every `vc_package`.
