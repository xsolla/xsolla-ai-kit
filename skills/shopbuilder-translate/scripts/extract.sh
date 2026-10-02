#!/usr/bin/env bash
# extract.sh <source-locale> <target-locale> [baseline-dir]
#
# Turns the newest baseline into l10n/work/<target>/translatable.json.
#
# Block text does NOT live in the block. get-structure gives each text field an "L:<uuid>"
# at values.<field>.id; the text itself lives in a separate localization store keyed by the
# slug (get-localization), namespaced as common."L:<id>" and pages.<pageId>.texts."L:<id>".
# This walks the structure for the ids and their block/field context (needed to classify
# marketing vs legal and to set a length budget), then resolves text from the store.
#
# ALLOWLIST, not denylist. Blocks: only fields that carry an "L:" id. Catalog and LiveOps
# text are out of scope for this skill. A denylist would pass newly-added
# fields to the translator by default; the failure mode of an allowlist is a missed string
# (reconciliation catches it), of a denylist a translated SKU (nothing catches it).
set -euo pipefail

SRC="${1:?usage: extract.sh <source-locale> <target-locale> [baseline-dir]}"
TGT="${2:?usage: extract.sh <source-locale> <target-locale> [baseline-dir]}"
BASE="${3:-$(ls -d l10n/backup/*/ 2>/dev/null | sort | tail -1)}"
[ -n "$BASE" ] && [ -d "$BASE" ] || { echo "no backup found — run scripts/export-backup.sh first" >&2; exit 1; }

OUT="l10n/work/$TGT"; mkdir -p "$OUT"
echo "extract  baseline=$BASE  $SRC -> $TGT"

BASE="$BASE" SRC="$SRC" TGT="$TGT" OUT="$OUT" python3 <<'PY'
import json, os, re, math, datetime

BASE, SRC, TGT, OUT = os.environ['BASE'], os.environ['SRC'], os.environ['TGT'], os.environ['OUT']
units, notes = [], []

def load(name):
    p = os.path.join(BASE, name)
    if not os.path.exists(p): return None
    with open(p) as f:
        try: d = json.load(f)
        except json.JSONDecodeError as e:
            notes.append(f"{name}: unparseable ({e})"); return None
    # The CLI wraps every response as {"ok":true,"data":{...}}. Unwrap it, or `pages` and
    # `common` sit one level below where this looks and NO block copy is extracted — the
    # same silent shape mismatch that hid the catalog bug.
    if isinstance(d, dict) and 'data' in d and set(d) <= {'ok', 'data', 'error'}:
        d = d['data']
    return d

TAG   = re.compile(r'<\s*([a-zA-Z][a-zA-Z0-9]*)')
LEGAL = re.compile(r'\b(refund|terms|privacy|polic|liabilit|warrant|tax|vat|gst|'
                   r'age rating|usk|cero|pegi|esrb|classind|disclaim|withdraw|impressum)\b', re.I)
MKTG_FIELDS = {'title','subtitle','headline','cta','button','buttonText','caption','slogan'}
# Asset URLs live in the localization store alongside real copy — SEO og:image is the common
# one. They resolve like any other localized string, and a translated URL is a broken image.
URLISH = re.compile(r'^\s*https?://', re.I)

plain = lambda s: re.sub(r'<[^>]+>', '', s or '').strip()

def kind_of(text, field='', block_type=''):
    if URLISH.match(text or ''):                     return 'asset'
    if LEGAL.search(plain(text)):                    return 'legal'
    if field in MKTG_FIELDS or block_type == 'lead': return 'marketing'
    return 'ui'

def budget(text):
    n = len(plain(text))
    # Short strings sit in buttons/tabs where overflow is visible; body copy is free.
    return math.ceil(n * 1.3) if n <= 40 else None

def add(**kw):
    s = kw.get('source','')
    kw.setdefault('tags', TAG.findall(s))
    kw.setdefault('budget', budget(s))
    kw['source_len'] = len(plain(s))
    units.append(kw)

def pick(locmap, *locales):
    for l in locales:
        if l and locmap.get(l): return locmap[l]
    return None

# Catalog and LiveOps strings are out of scope. This extractor does not read them.

# ---------------------------------------------------------------- blocks (surface B)
structure = load('structure.json')
locstore  = load('localization.json')

if structure is None:
    notes.append("structure.json missing — NO block copy extracted")
elif locstore is None:
    notes.append("localization.json missing — NO block copy extracted. Block text lives in "
                 "the localization store, not the block; re-run export-backup.sh.")
else:
    common = locstore.get('common', {}) or {}
    pages_loc = locstore.get('pages', {}) or {}

    def texts_for(page_id):
        return (pages_loc.get(page_id, {}) or {}).get('texts', {}) or {}

    def locmap(entry):
        """The store nests the locale map under `translations`, alongside a `description`
        holding the dotted source path (e.g. blocks.header.values.loginButton). Older/flat
        shapes put the locale map at the top level. Accept both — assuming the flat shape
        against the real API yields ZERO block units and NO error, because the miss happens
        on a silent early return."""
        if isinstance(entry, dict) and isinstance(entry.get('translations'), dict):
            return entry['translations'], entry.get('description')
        return entry, None

    def resolve(lid, page_id):
        """An L: id resolves in its page namespace, or in common for shared strings.
        Returns (locale->text, scope) where scope is the page id or 'common' — the scope is
        required to write it back via update-many-localization."""
        t = texts_for(page_id)
        if lid in t:      return t[lid], page_id
        if lid in common: return common[lid], 'common'
        return None, None

    seen = set()
    def walk(node, path, page_id, block_id, block_type):
        """Depth-first for {"id": "L:..."} markers. That marker IS the allowlist —
        structural fields (sku, group, type, layout, colors, urls) never carry one."""
        if isinstance(node, dict):
            lid = node.get('id')
            if isinstance(lid, str) and lid.startswith('L:'):
                loc, scope = resolve(lid, page_id)
                if loc is None:
                    notes.append(f"{lid} referenced by {block_id}{'.'.join(map(str,path))} "
                                 f"but absent from the localization store")
                    return
                loc, srcpath = locmap(loc)
                src = pick(loc, SRC, SRC.split('-')[0])
                if src is None:
                    # Never fail silently here: a missing source locale is indistinguishable
                    # from a shape mismatch, and the latter drops the whole storefront.
                    notes.append(f"{lid} has no {SRC} value (locales present: "
                                 f"{','.join(sorted(loc)[:6]) if isinstance(loc, dict) else type(loc).__name__})")
                    return
                seen.add(lid)
                field = path[-1] if path else ''
                add(id=f"block:{block_id}:{'.'.join(map(str, path))}", surface='block',
                    lid=lid, scope=scope, page_id=page_id, block_id=block_id,
                    block_type=block_type, container=path[0] if path else '',
                    field=field, source=src, description=srcpath or '',
                    existing_target=pick(loc, TGT, TGT.split('-')[0]),
                    kind=kind_of(src, field, block_type))
                return
            for k, v in node.items(): walk(v, path + [k], page_id, block_id, block_type)
        elif isinstance(node, list):
            for i, v in enumerate(node): walk(v, path + [i], page_id, block_id, block_type)

    for page in structure.get('pages', []):
        pid = page.get('_id')
        for b in page.get('blocks', []):
            bid = b.get('_id') or b.get('id')
            bt  = b.get('module') or b.get('type') or ''
            walk(b.get('values', {}),    ['values'],     pid, bid, bt)
            walk(b.get('components', []),['components'], pid, bid, bt)

        # Page-level SEO: `title`/`description` carry their own L: ids, resolved and
        # written through the exact same localization store as block text — but they live
        # under page.seo, a sibling of page.blocks, so the walk above never reaches them.
        # Confirmed live: both had real per-locale text, not placeholders.
        # `manifest.title`/`manifest.description` reuse these SAME ids (PWA manifest), so
        # walking only the top-level seo.* keys covers both without double-extracting.
        seo = page.get('seo') or {}
        for f in ('title', 'description', 'ogImage'):
            sub = seo.get(f)
            lid = sub.get('id') if isinstance(sub, dict) else None
            if not isinstance(lid, str) or not lid.startswith('L:') or lid in seen:
                continue
            loc, scope = resolve(lid, pid)
            if loc is None:
                notes.append(f"{lid} referenced by page {pid} seo.{f} but absent from the "
                             f"localization store")
                continue
            loc, srcpath = locmap(loc)
            src = pick(loc, SRC, SRC.split('-')[0])
            if not src:
                # ogImage is commonly unset (empty string) — nothing to extract, not an error.
                if f != 'ogImage':
                    notes.append(f"{lid} has no {SRC} value (page {pid} seo.{f})")
                continue
            seen.add(lid)
            add(id=f"seo:{pid}:{f}", surface='block', lid=lid, scope=scope, page_id=pid,
                block_id=None, block_type='', container='seo', field=f, source=src,
                description=srcpath or '',
                existing_target=pick(loc, TGT, TGT.split('-')[0]), kind=kind_of(src, field=f))

    # Shared strings live in common and are referenced by chrome that is not in the page
    # structure. They are still translatable and would otherwise be silently dropped.
    for lid, entry in common.items():
        if lid in seen: continue
        loc, srcpath = locmap(entry)
        src = pick(loc, SRC, SRC.split('-')[0])
        if not src: continue
        add(id=f"block:common:{lid}", surface='block', lid=lid, scope='common',
            page_id=None, block_id=None, block_type='', container='common', field='',
            source=src, description=srcpath or '',
            existing_target=pick(loc, TGT, TGT.split('-')[0]),
            kind=kind_of(src))

# ---------------------------------------------------------------- image references
# Not translatable — no per-locale image slot exists. Listed so text-in-art gets reviewed.
images = set()
def find_images(n):
    if isinstance(n, dict):
        for k, v in n.items():
            if k in ('src','img','image','imageUrl','image_url') and isinstance(v, str) and v.startswith('http'):
                images.add(v)
            else: find_images(v)
    elif isinstance(n, list):
        for v in n: find_images(v)
find_images(structure or {})

doc = {
  'meta': {
    'generated': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'baseline': BASE, 'source_locale': SRC, 'target_locale': TGT,
    'landing_id': (structure or {}).get('_id'),
    'domain': (structure or {}).get('domain'),
    'counts': {
      'total': len(units),
      'catalog': sum(1 for u in units if u['surface'] == 'catalog'),
      'block': sum(1 for u in units if u['surface'] == 'block'),
      'common_scope': sum(1 for u in units if u.get('scope') == 'common'),
      'legal_flagged': sum(1 for u in units if u['kind'] == 'legal'),
      'assets_skipped': sum(1 for u in units if u['kind'] == 'asset'),
      # NOT "already translated". Template landings ship stale pre-translated locales; once
      # the source copy is edited that value is silently wrong. Presence of a target is not
      # evidence it is correct — compare against the CURRENT source and overwrite.
      'existing_target_present': sum(1 for u in units if u.get('existing_target')),
      'existing_may_be_stale': True,
    },
    'images_not_translatable': sorted(images),
    'notes': notes,
  },
  'units': units,
}
with open(os.path.join(OUT, 'translatable.json'), 'w') as f:
    json.dump(doc, f, indent=2, ensure_ascii=False)

c = doc['meta']['counts']
print(f"  units            {c['total']}")
print(f"    catalog        {c['catalog']}")
print(f"    block          {c['block']}  (of which {c['common_scope']} in the common scope)")
print(f"    legal (DO NOT TRANSLATE — route to counsel)  {c['legal_flagged']}")
print(f"    asset URLs (NOT translatable)  {c['assets_skipped']}")
print(f"    existing {TGT} value present  {c['existing_target_present']}  "
      f"(MAY BE STALE — re-translate, do not skip)")
print(f"  images (not translatable)  {len(images)}")
for n in notes: print(f"  ! {n}")
PY

echo "wrote $OUT/translatable.json"
