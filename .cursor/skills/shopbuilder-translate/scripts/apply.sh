#!/usr/bin/env bash
# apply.sh <domain> <target-locale> [--commit] [--report] [--confirm-overwrites]
#
# Shop Builder page copy only. Catalog and LiveOps text are out of scope.
# Default is a DRY RUN: builds and saves every payload, sends nothing.
#   --commit              write page copy. Does not change the language the shop opens in.
#                         Before the first write, checks the approved-test-project allowlist,
#                         exports the live site read-only, and blocks if that text changed
#                         since extract. A failed write exits non-zero.
#   --report              reconcile the localization store against translated.json
#   --confirm-overwrites  required on --commit whenever a unit already has a target-locale
#                         value that differs from what is about to be written. Without it,
#                         a run BLOCKS and lists what it would have overwritten.
set -euo pipefail

DOMAIN="${1:?usage: apply.sh <domain> <target-locale> [--commit] [--report] [--confirm-overwrites]}"
TGT="${2:?usage: apply.sh <domain> <target-locale> [--commit] [--report] [--confirm-overwrites]}"; shift 2
COMMIT=0; REPORT=0; CONFIRM_OVERWRITES=0
for a in "$@"; do
  case "$a" in
    --commit) COMMIT=1 ;;
    --report) REPORT=1 ;;
    --confirm-overwrites) CONFIRM_OVERWRITES=1 ;;
    *) echo "unknown flag: $a" >&2; exit 2 ;;
  esac
done

WORK="l10n/work/$TGT/translated.json"
[ -f "$WORK" ] || { echo "missing $WORK — run extract.sh, then translate it" >&2; exit 1; }

# THERE IS NO SANDBOX, ANYWHERE. The CLI says so for both surfaces — "catalog has no Xsolla
# sandbox environment" and "shopbuilder has no Xsolla sandbox environment" — and in both
# cases the request URL is byte-identical with and without the flag. So --sandbox is never
# passed: it would imply a guarantee that does not exist. Every write below is LIVE.
SCRIPTDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOMAIN="$DOMAIN" TGT="$TGT" WORK="$WORK" COMMIT="$COMMIT" REPORT="$REPORT" \
CONFIRM_OVERWRITES="$CONFIRM_OVERWRITES" \
SCRIPTDIR="$SCRIPTDIR" python3 <<'PY'
import json, os, re, subprocess, sys, collections, time

DOMAIN, TGT, WORK = os.environ['DOMAIN'], os.environ['TGT'], os.environ['WORK']
COMMIT, REPORT = os.environ['COMMIT'] == '1', os.environ['REPORT'] == '1'
CONFIRM_OVERWRITES = os.environ['CONFIRM_OVERWRITES'] == '1'
XS = os.environ.get('XSOLLA_CLI', 'xsolla')
M  = os.environ.get('XSOLLA_MERCHANT_ID', ''); P = os.environ.get('XSOLLA_PROJECT_ID', '')

doc   = json.load(open(WORK))
SRC   = doc['meta']['source_locale']
units = doc['units']

# STALENESS GATE. translated.json is produced from ONE backup. If a newer backup exists
# under l10n/backup, these translations describe a store that has since changed.
BASE = doc['meta'].get('baseline')
try:
    import glob
    snaps = sorted(d for d in glob.glob('l10n/backup/*/') if os.path.isdir(d))
except Exception:
    snaps = []
if snaps and BASE:
    newest = snaps[-1].rstrip('/')
    if os.path.normpath(BASE) != os.path.normpath(newest):
        print(f"BLOCKED — stale translations.\n"
              f"  translated.json was built from : {os.path.normpath(BASE)}\n"
              f"  newest backup is              : {newest}\n"
              f"  Re-run extract.sh against the newest backup and re-translate, or delete\n"
              f"  the stale l10n/work/<locale>/ directory. Applying these would write copy\n"
              f"  for a version of the store that no longer exists.")
        sys.exit(1)
PAYDIR = os.path.join(os.path.dirname(WORK), 'payloads')
os.makedirs(PAYDIR, exist_ok=True)

def save(name, obj):
    """Persist every payload. Dry-run payloads are reviewable and diffable; commit
    responses sit beside their request so a revert is replaying a file, not
    reconstructing intent from memory."""
    with open(os.path.join(PAYDIR, name), 'w') as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)

write_failed = []

def run(args, tag, sandbox=False):
    """No --sandbox: neither surface has a sandbox environment, so the flag is a no-op that
    would misrepresent what this run is doing. Dry run prints and saves without executing.
    A non-zero CLI status is a failed write. The caller must not report success."""
    save(f"{tag}.cmd.json", args)
    print("   ", " ".join(a if len(a) < 60 else a[:57] + "..." for a in args))
    if not COMMIT:
        return 0
    r = subprocess.run(args, capture_output=True, text=True)
    save(f"{tag}.response.json", {"rc": r.returncode, "stdout": r.stdout, "stderr": r.stderr})
    print(f"    -> rc={r.returncode}" + ("" if r.returncode == 0 else f" {r.stderr[:160]}"))
    if r.returncode != 0:
        write_failed.append(tag)
    return r.returncode

TAG   = re.compile(r'<\s*([a-zA-Z][a-zA-Z0-9]*)')
plain = lambda s: re.sub(r'<[^>]+>', '', s or '').strip()

# --- gate: validate before writing anything ---------------------------------
errors, warns, skipped, ready = [], [], [], []
for u in units:
    t = u.get('target')
    if u['kind'] == 'legal':
        skipped.append((u['id'], 'legal — route to counsel, not translated here')); continue
    if u['kind'] == 'asset':
        # An asset URL that lives in the localization store. Translating it breaks the image.
        skipped.append((u['id'], 'asset URL — not translatable')); continue
    if not t:
        skipped.append((u['id'], 'no target text')); continue
    # Tag parity: a dropped <h1> renders as unstyled plain text and a reviewer reading the
    # target language will not notice it.
    st, tt = sorted(TAG.findall(u['source'])), sorted(TAG.findall(t))
    if st != tt:
        errors.append(f"{u['id']}: HTML tag mismatch source={st} target={tt}"); continue
    # Block text is HTML. A bare string renders unstyled, so refuse to write one where the
    # source had markup.
    if u['surface'] == 'block' and st and not tt:
        errors.append(f"{u['id']}: block text must be HTML"); continue
    b = u.get('budget')
    if b and len(plain(t)) > b:
        warns.append(f"{u['id']}: {len(plain(t))} chars over budget {b} — will overflow buttons/tabs")
    ready.append(u)

if errors:
    print("BLOCKED — fix these before applying:")
    for e in errors: print("  x", e)
    sys.exit(1)
for w in warns: print("  ! ", w)
for i, r in skipped: print(f"  - skip {i}: {r}")

# --- gate: existing translations are not overwritten without confirmation ---
# extract.sh records existing_target from the baseline. A unit with one already has SOME
# value in the target locale — template-prepopulated or from a prior run. Writing over it
# without the operator seeing what is being replaced is exactly the silent-clobber this DoD
# line exists to prevent. Identical old==new is not a real overwrite; skip those.
overwrites = [u for u in ready
              if (u.get('existing_target') or '').strip()
              and (u.get('existing_target') or '').strip() != (u.get('target') or '').strip()]
if overwrites:
    print(f"\n== {len(overwrites)} unit(s) already have a {TGT} value that this run would replace ==")
    for u in overwrites[:20]:
        print(f"    {u['id']}")
        print(f"      existing: {u['existing_target']!r}")
        print(f"      new     : {u['target']!r}")
    if len(overwrites) > 20:
        print(f"    … and {len(overwrites) - 20} more")
    if COMMIT and not CONFIRM_OVERWRITES:
        print("\n  BLOCKED — re-run with --confirm-overwrites once a human has reviewed the "
              "list above.\n"
              "  This is not optional: a template-derived landing ships pre-translated, and "
              "the existing value may be a stale mistranslation OR the last thing a human set on "
              "purpose. Either way it must be a deliberate choice to replace it, not a side "
              "effect of running this script.")
        sys.exit(1)

def unwrap(path):
    with open(path) as f:
        d = json.load(f)
    # The CLI envelope is {"ok","data"}. A fixture that is already an envelope and is
    # served again by the fake CLI is wrapped twice. Peel until the store itself.
    while isinstance(d, dict) and 'data' in d and set(d) <= {'ok', 'data', 'error'}:
        d = d['data']
    return d

def loc_text(store, scope, lid, locale):
    if not isinstance(store, dict):
        return None
    if scope == 'common':
        entry = (store.get('common') or {}).get(lid)
    else:
        entry = (((store.get('pages') or {}).get(scope) or {}).get('texts') or {}).get(lid)
    if not isinstance(entry, dict):
        return None
    loc = entry['translations'] if isinstance(entry.get('translations'), dict) else entry
    if not isinstance(loc, dict):
        return None
    return loc.get(locale)

def allowlist_allows():
    """Version-1 approved-test-project list. Not a production denylist."""
    allow = os.environ.get('XSOLLA_APPROVED_TEST_PROJECTS', '').strip()
    if not allow or not os.path.isfile(allow):
        print("BLOCKED — set XSOLLA_APPROVED_TEST_PROJECTS to the approved-test-project "
              "allowlist JSON before any write. A production denylist is not a substitute. "
              "Nothing was written.")
        sys.exit(1)
    if not M or not P:
        print("BLOCKED — XSOLLA_MERCHANT_ID and XSOLLA_PROJECT_ID are required before a write.")
        sys.exit(1)
    try:
        doc = json.load(open(allow))
        merchant, project = int(M), int(P)
    except (OSError, ValueError, json.JSONDecodeError):
        print(f"BLOCKED — {allow} is not a version-1 allowlist. Nothing was written.")
        sys.exit(1)
    if doc.get('version') != 1 or not isinstance(doc.get('projects'), list):
        print(f"BLOCKED — {allow} is not a version-1 allowlist. Nothing was written.")
        sys.exit(1)
    for row in doc['projects']:
        if not isinstance(row, dict):
            continue
        try:
            if int(row.get('merchant_id')) == merchant and int(row.get('project_id')) == project:
                return
        except (TypeError, ValueError):
            continue
    print(f"BLOCKED — merchant {M} project {P} is not on the approved-test-project allowlist. "
          "Nothing was written.")
    sys.exit(1)

def live_drift(base_path, live_path):
    """Ids about to be written whose source or existing target changed since extract."""
    if not base_path or not os.path.isfile(base_path) or not os.path.isfile(live_path):
        return ["baseline or pre-write localization.json is missing"]
    base, live = unwrap(base_path), unwrap(live_path)
    changed = []
    for u in ready:
        if u.get('surface') != 'block':
            continue
        for locale, label in ((SRC, 'source'), (TGT, 'target')):
            old, new = loc_text(base, u['scope'], u['lid'], locale), loc_text(live, u['scope'], u['lid'], locale)
            if old != new:
                changed.append(f"{u['id']} {label} {locale}: baseline {old!r} live {new!r}")
    return changed

def backup_before_write():
    """Allowlist, then a read-only export, before the first write. Not a production denylist."""
    if not COMMIT:
        return
    allowlist_allows()
    script = os.path.join(os.environ['SCRIPTDIR'], 'export-backup.sh')
    if not os.path.isfile(script):
        print(f"BLOCKED — export-backup.sh not found at {script}. Nothing was written.")
        sys.exit(1)
    out = os.path.abspath(os.path.join('l10n', 'pre-write', time.strftime('%Y%m%d-%H%M%S')))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    print("\n== read-only export before write (approved-test-project allowlist) ==")
    r = subprocess.run(['bash', script, DOMAIN, out])
    if r.returncode != 0:
        print("BLOCKED — the read-only export failed. Nothing was written.")
        sys.exit(r.returncode or 1)
    base_loc = os.path.join(os.path.normpath(BASE), 'localization.json') if BASE else ''
    changed = live_drift(base_loc, os.path.join(out, 'localization.json'))
    if changed:
        print("BLOCKED — the live store changed after extract for a string this run would write.")
        print("  Re-run export-backup.sh and extract.sh, then re-translate. Nothing was written.")
        for line in changed:
            print(f"  {line}")
        sys.exit(1)
    print(f"  export -> {out}")

backup_before_write()

# --- blocks (surface B): the localization store, NOT update-block -----------
# Block text is referenced by an "L:" id; the text lives in a separate store keyed by the
# slug. update-block on ["values","title"] deletes that string and every translation of it,
# and the call still returns 200. It does not leave the block unchanged.
# update-many-localization writes one locale in a single call, scoped by page id / "common".
blk = [u for u in ready if u['surface'] == 'block']
per_scope = collections.defaultdict(dict)
for u in blk:
    # The per-id value MUST include "translation". Omitting "description" clears the
    # dotted source path on that entry. A bare string, or value/text/translations,
    # returns 200 and writes an EMPTY string.
    per_scope[u['scope']][u['lid']] = {
        "description": u.get('description') or "",
        "translation": u['target'],
    }

print(f"\n== blocks: {len(blk)} strings across {len(per_scope)} scope(s) -> {TGT} ==")
if per_scope:
    payload = {"locale": TGT, "perScopeValues": {k: v for k, v in per_scope.items()}}
    save("localization.request.json", payload)
    for scope, ids in per_scope.items():
        print(f"    scope {scope}: {len(ids)} string(s)")
    run([XS, 'shopbuilder', 'update-many-localization', '--slug', DOMAIN,
         '--data', json.dumps(payload, ensure_ascii=False)], 'localization')

if write_failed:
    print("\nBLOCKED — a write failed (" + ", ".join(write_failed) + ").")
    print("The copy was not written. Do not treat this run as a success.")
    sys.exit(1)

# --- reconciliation ---------------------------------------------------------
rc = 0
if REPORT:
    print("\n== coverage of the translation FILE ==")
    missing = [u['id'] for u in units if u['kind'] != 'legal' and not u.get('target')]
    print(f"  units without a translation: {len(missing)}")
    for m in missing[:20]: print("    -", m)
    if len(missing) > 20: print(f"    … and {len(missing)-20} more")
    # Everything above inspects a file on disk. It passes identically whether or not a
    # single word reached the store, so it is NOT verification — every incorrect write in
    # this system returns success. Hand off to the script that asks the store itself.
    if COMMIT:
        print("\n== reading the store back ==")
        rc = subprocess.run(['bash', os.path.join(os.environ['SCRIPTDIR'], 'verify.sh'),
                             DOMAIN, TGT]).returncode
    else:
        print(f"\n  dry run — nothing was written, so there is nothing to read back.")
        print(f"  After --commit, verify against the live store:")
        print(f"    scripts/verify.sh {DOMAIN} {TGT}")

print(f"\npayloads -> {PAYDIR}")
if not COMMIT:
    print("DRY RUN — nothing was sent. --commit writes the copy and does not change the language the shop opens in.")
    print("Review the payloads, then re-run with --commit.")
else:
    print("\nCopy was written. This run did not change the language the shop opens in.")
    print("The shop opens in the first language of the site language list.")
    print("To open in another language, reorder that list in Publisher Account.")
    print("A write returning ok:true proves nothing. Read it back:")
    print(f"    scripts/verify.sh {DOMAIN} {TGT}")
sys.exit(rc)
PY
