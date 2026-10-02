#!/usr/bin/env bash
# verify.sh <domain> <target-locale> [--json]
#
# Reads the LIVE store back and diffs it against what apply.sh sent. This is the only check
# in this workflow that means anything: every incorrect write in this system returns success,
# so "rc=0" proves that a request was well-formed, not that a translation landed.
#
# Everything apply.sh does before sending — blanks, tag parity, length budget — inspects a
# file on disk. It passes identically whether or not a single word reached the store. This
# script asks the store.
#
# Checks:
#   storefront  get-localization, resolving each L: id in its own scope.
#   languages   get-structure: the target must be enabled. The first entry is what the shop
#               opens in. This script reports that language. It does not fail because the
#               target is not first, and it does not reorder the list.
#
# Reads only. Nothing here writes.
set -euo pipefail

DOMAIN="${1:?usage: verify.sh <domain> <target-locale> [--json]}"
TGT="${2:?usage: verify.sh <domain> <target-locale> [--json]}"; shift 2
JSON_OUT=0
for a in "$@"; do
  case "$a" in
    --json) JSON_OUT=1 ;;
    *) echo "unknown flag: $a" >&2; exit 2 ;;
  esac
done

WORK="l10n/work/$TGT/translated.json"
[ -f "$WORK" ] || { echo "missing $WORK — nothing to verify against" >&2; exit 1; }

DOMAIN="$DOMAIN" TGT="$TGT" WORK="$WORK" JSON_OUT="$JSON_OUT" python3 <<'PY'
import json, os, subprocess, sys, collections

DOMAIN, TGT, WORK = os.environ['DOMAIN'], os.environ['TGT'], os.environ['WORK']
JSON_OUT = os.environ['JSON_OUT'] == '1'
XS = os.environ.get('XSOLLA_CLI', 'xsolla')
M  = os.environ.get('XSOLLA_MERCHANT_ID', ''); P = os.environ.get('XSOLLA_PROJECT_ID', '')

doc   = json.load(open(WORK))
SRC   = doc['meta']['source_locale']
# Only units apply.sh actually intended to write are verifiable. Legal copy is refused by
# design and asset URLs are never translated, so demanding a target locale for them would
# manufacture failures out of correct behaviour.
units = [u for u in doc['units']
         if u.get('target') and u.get('kind') not in ('legal', 'asset')]

IRREGULAR = {'zh-CN': 'cn', 'zh-TW': 'tw'}
def short(loc):
    if loc in IRREGULAR: return IRREGULAR[loc]
    return loc.split('-')[0] if '-' in loc else loc

def cli(args):
    """Every read goes through here so the whole script can be pointed at a fake CLI.
    A non-zero rc or unparseable output is a FINDING, not a crash: 'unknown flag' comes back
    as plain text and would otherwise blow up as a JSON error three frames away."""
    r = subprocess.run([XS] + args, capture_output=True, text=True)
    if r.returncode != 0:
        return None, (r.stderr or r.stdout or '').strip()[:200]
    try:
        d = json.loads(r.stdout)
    except json.JSONDecodeError:
        return None, f"non-JSON response: {(r.stdout or '').strip()[:120]}"
    # The CLI wraps everything as {"ok":true,"data":...}. Unwrap, or every lookup below
    # misses one level down and reports a fully translated store as fully missing.
    if isinstance(d, dict) and 'data' in d and set(d) <= {'ok', 'data', 'error'}:
        d = d['data']
    return d, None

findings = []           # (severity, surface, id, detail)
def bad(*a):  findings.append(('MISSING',) + a)
def diff(*a): findings.append(('DIFFERS',) + a)
def warn(*a): findings.append(('WARN',) + a)

checked = collections.Counter()

# ---------------------------------------------------------------- storefront (surface B)
# get-localization takes --slug ONLY. Passing --merchant-id is a hard 'unknown flag' that
# exits with plain text, which is why cli() treats that as a finding rather than parsing it.
blk_units = [u for u in units if u['surface'] == 'block']
if blk_units:
    d, err = cli(['shopbuilder', 'get-localization', '--slug', DOMAIN, '--json'])
    if err:
        bad('storefront', 'get-localization', err)
    else:
        common = d.get('common', {}) or {}
        pages  = d.get('pages', {}) or {}
        def entry_for(u):
            # Page strings nest one level deeper than common ones:
            #   .common[id]   but  .pages[pageId].texts[id]
            if u.get('scope') == 'common' or u.get('page_id') is None:
                return common.get(u['lid'])
            texts = (pages.get(u['scope']) or pages.get(u['page_id']) or {}).get('texts', {}) or {}
            return texts.get(u['lid']) or common.get(u['lid'])
        for u in blk_units:
            checked['storefront'] += 1
            entry = entry_for(u)
            if entry is None:
                bad('storefront', u['id'], f'{u["lid"]} absent from the localization store')
                continue
            # READ nests the locale map under `translations`; the WRITE key is `translation`,
            # singular. Accept the flat shape too.
            loc = entry['translations'] if isinstance(entry, dict) and isinstance(entry.get('translations'), dict) else entry
            if not isinstance(loc, dict):
                bad('storefront', u['id'], f'unexpected entry shape {type(loc).__name__}')
                continue
            got = (loc.get(TGT) or loc.get(short(TGT)) or '').strip()
            if not got:
                bad('storefront', u['id'],
                    f'no {TGT} value (has: {", ".join(sorted(loc)[:8]) or "nothing"})')
            elif u.get('target') and got != u['target']:
                diff('storefront', u['id'], f'store has {got[:40]!r}, we sent {u["target"][:40]!r}')

# ---------------------------------------------------------------- languages
# A landing has no default-locale field: the FIRST entry of `languages` is what the shop
# opens in. Fully translated + not first == looks exactly like the run did nothing.
langs, err = cli(['shopbuilder', 'get-structure', '--slug', DOMAIN,
                  '--merchant-id', M, '--project-id', P, '--json'])
enabled = []
if err:
    warn('languages', 'get-structure', err)
else:
    enabled = langs.get('languages') or []
    if TGT not in enabled:
        bad('languages', TGT,
            f'NOT enabled on the site (enabled: {", ".join(enabled) or "none"}) — '
            f'translations are written but nothing renders. Run add-language')
    elif enabled and enabled[0] != TGT:
        # The first language is what the shop opens in. Report it. Do not fail the run,
        # and do not reorder the list. The partner sets that in Publisher Account.
        findings.append(('INFO', 'languages', TGT,
            f'enabled. The shop opens in {enabled[0]}. Reorder the site language list in '
            f'Publisher Account if it should open in {TGT}. This skill does not change that order.'))

# ---------------------------------------------------------------- report
sev_rank = {'MISSING': 0, 'DIFFERS': 1, 'WARN': 2, 'INFO': 3}
findings.sort(key=lambda f: (sev_rank[f[0]], f[1], f[2]))
counts = collections.Counter(f[0] for f in findings)

if JSON_OUT:
    print(json.dumps({'domain': DOMAIN, 'target': TGT, 'source': SRC,
                      'checked': dict(checked), 'languages': enabled,
                      'counts': dict(counts),
                      'findings': [dict(zip(('severity','surface','id','detail'), f))
                                   for f in findings]}, indent=2, ensure_ascii=False))
else:
    print(f"verify {DOMAIN} -> {TGT}   (read back from the LIVE store)")
    print(f"  storefront strings   {checked['storefront']}")
    print(f"  site languages       {', '.join(enabled) or '(unreadable)'}"
          + (f"   -> opens in {enabled[0]}" if enabled else ""))
    print()
    for sev, surface, ident, detail in findings:
        mark = {'MISSING': 'x', 'DIFFERS': '~', 'WARN': '!', 'INFO': '-'}[sev]
        print(f"  {mark} {sev:7} {surface:10} {ident}: {detail}")
    if not findings:
        print("  everything checked is present in the store, in the target locale.")
    print()
    print(f"  {counts['MISSING']} missing, {counts['DIFFERS']} differing, "
          f"{counts['WARN']} warnings")

# Missing text, or a target locale that is not enabled, is a failed run. DIFFERS is not:
# it also fires when a human edited the store after the write, which is information, not
# a fault this script can adjudicate.
sys.exit(1 if counts['MISSING'] else 0)
PY
