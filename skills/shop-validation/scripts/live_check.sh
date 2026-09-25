#!/usr/bin/env bash
#
# Live evidence run for the validate-shop scripts.
#
# Creates a throwaway Shop Builder landing, adds a page (which lands the 13-block
# template), walks it, then seeds one defect at a time through the CLI and asserts the
# walk names each one.  Finishes by deleting the landing unless --keep is passed.
#
# THIS WRITES TO THE SHOP BUILDER API.  It creates a landing, patches blocks on it, and
# creates two custom blocks.  Sandbox or a test project only -- never a partner's live
# project.  It never publishes, and it never touches a landing it did not create.
#
# Usage:
#   ./live-check.sh --yes [--keep] [--slug <slug>]
#
# Requires: xsolla CLI on PATH, `xsolla auth login` already done, and a project_id set
# (`xsolla config set project_id <id>`).  Python 3.9+.

set -u -o pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VALIDATE="python3 $HERE/validate_shop.py"
WORK="$(mktemp -d)"
CONFIRMED=0
KEEP=0
SLUG=""

while [ $# -gt 0 ]; do
  case "$1" in
    --yes) CONFIRMED=1 ;;
    --keep) KEEP=1 ;;
    --slug) shift; SLUG="${1:-}" ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done

if [ "$CONFIRMED" -ne 1 ]; then
  cat >&2 <<'MSG'
This run writes to the Shop Builder API: it creates a landing, adds a page, patches
blocks and creates two custom blocks. Sandbox or test projects only.

Re-run with --yes to proceed, or --yes --keep to leave the landing in place afterwards.
MSG
  exit 2
fi

[ -n "$SLUG" ] || SLUG="aikit-livecheck-$(date +%m%d%H%M%S)"

PASS=0
FAIL=0

step() { printf '\n== %s\n' "$1"; }
ok()   { PASS=$((PASS + 1)); printf '   PASS  %s\n' "$1"; }
bad()  { FAIL=$((FAIL + 1)); printf '   FAIL  %s\n' "$1"; }

data() { python3 -c 'import json,sys; json.dump(json.load(sys.stdin)["data"], sys.stdout)'; }

fetch() {
  # fetch <structure|localization>
  case "$1" in
    structure)    xsolla shopbuilder get-structure    --slug "$SLUG" --json 2>/dev/null | data > "$WORK/structure.json" ;;
    localization) xsolla shopbuilder get-localization --slug "$SLUG" --json 2>/dev/null | data > "$WORK/localization.json" ;;
  esac
}

walk() {
  $VALIDATE site --structure "$WORK/structure.json" --localization "$WORK/localization.json" --json > "$WORK/report.json"
  return 0
}

# count <category> -- how many errors the last walk put in that category
count() {
  python3 -c "
import json
r = json.load(open('$WORK/report.json'))
print(r['scope']['errors_by_category'].get('$1', 0))
"
}

step "Create the landing: $SLUG"
xsolla shopbuilder create-website --name "AI Kit live check" --slug "$SLUG" --type topup --json >/dev/null 2>&1
fetch structure
LANDING="$(python3 -c "import json;print(json.load(open('$WORK/structure.json'))['_id'])" 2>/dev/null)"
if [ -n "${LANDING:-}" ]; then ok "landing created: $LANDING"; else bad "landing was not created -- check auth and project_id"; exit 1; fi

PAGES="$(python3 -c "import json;print(len(json.load(open('$WORK/structure.json')).get('pages') or []))")"
[ "$PAGES" = "0" ] && ok "a fresh landing has no pages and no blocks" || bad "expected a fresh landing to be empty, found $PAGES page(s)"

step "Add a page -- the platform lands a block template"
xsolla shopbuilder add-page --slug "$SLUG" --name "Main" --path "/main" --json >/dev/null 2>&1
fetch structure
fetch localization
BLOCKS="$(python3 -c "import json;s=json.load(open('$WORK/structure.json'));print(sum(len(p.get('blocks') or []) for p in s['pages']))")"
PAGE="$(python3 -c "import json;print(json.load(open('$WORK/structure.json'))['pages'][0]['_id'])")"
[ "$BLOCKS" -gt 1 ] && ok "$BLOCKS blocks arrived with the first page" || bad "expected a block template, found $BLOCKS"

step "Baseline walk -- no structural errors on an untouched template"
walk
for category in shape reference site; do
  n="$(count $category)"
  [ "$n" = "0" ] && ok "no $category errors" || bad "$n $category error(s) on an untouched site -- these are false positives"
done
CONTENT="$(count content)"
printf '   NOTE  %s content error(s): template placeholders, not defects\n' "$CONTENT"

step "Seed 1 -- a block's values sent as a JSON string"
python3 - <<PY
import json
s = json.load(open("$WORK/structure.json"))
faq = [b for b in s["pages"][0]["blocks"] if b.get("module") == "faq"][0]
json.dump(faq, open("$WORK/faq_original.json", "w"))
json.dump({"r1": {"type": "block", "id": faq["_id"],
                  "patches": [{"op": "replace", "path": ["values"], "value": json.dumps(faq["values"])}]}},
          open("$WORK/seed1.json", "w"))
PY
xsolla shopbuilder update-block --landing-id "$LANDING" --data "$(cat "$WORK/seed1.json")" --json >/dev/null 2>&1
fetch structure
walk
python3 -c "
import json
r=json.load(open('$WORK/report.json'))
shape=[f for f in r['errors'] if f.get('category')=='shape']
assert len(shape)==1, shape
assert shape[0]['path']=='values' and shape[0]['got']=='string', shape
" 2>/dev/null && ok "the API accepted it and the walk caught it as one shape error" \
              || bad "a values-as-string block was not caught"

step "Seed 2 -- an L: reference with no localization entry"
python3 - <<PY
import json
faq = json.load(open("$WORK/faq_original.json"))
values = dict(faq["values"])
title = dict(values.get("title") or {})
title["id"] = "L:00000000-dead-4000-8000-000000000000"
values["title"] = title
json.dump({"r1": {"type": "block", "id": faq["_id"],
                  "patches": [{"op": "replace", "path": ["values"], "value": values}]}},
          open("$WORK/seed2.json", "w"))
PY
xsolla shopbuilder update-block --landing-id "$LANDING" --data "$(cat "$WORK/seed2.json")" --json >/dev/null 2>&1
fetch structure
fetch localization
walk
python3 -c "
import json
r=json.load(open('$WORK/report.json'))
refs=[f for f in r['errors'] if f.get('category')=='reference']
assert any('dead-4000' in (f.get('value') or '') for f in refs), refs
" 2>/dev/null && ok "the dangling L: id was named" || bad "a dangling L: reference was not caught"

step "Seed 3 -- custom-block source that compiles and breaks at runtime"
cat > "$WORK/faulty.jsx" <<'JSX'
import { TextEditor } from '@site-builder/block-utils';

export default function LiveCheckBlock() {
  const { label } = useControls({ label: text('Label', 'Limited time') });
  const badge = useControls(color({ value: '#00ffcc' }));
  return (
    <div style={{ padding: 24 }}>
      <TextEditor id={localizedText('title')} />
      <span style={{ color: badge }}>{label}</span>
    </div>
  );
}
JSX
$VALIDATE ai-code --component "$WORK/faulty.jsx" --json > "$WORK/code.json"
python3 -c "
import json
rules={v['rule'] for v in json.load(open('$WORK/code.json'))['errors']}
for expected in ('use-controls-object-arg','control-factory-object-arg','missing-text-fields','undeclared-text-fields'):
    assert expected in rules, (expected, rules)
" 2>/dev/null && ok "the source gate named every seeded violation before any write" \
              || bad "the source gate missed a seeded violation"

xsolla shopbuilder create-custom-block --landing-id "$LANDING" --page-id "$PAGE" \
  --name "Live check block" --component-code "$(cat "$WORK/faulty.jsx")" --json > "$WORK/created.json" 2>&1
AI_ID="$(python3 -c "
import json
try: print(json.load(open('$WORK/created.json'))['data']['blockId'])
except Exception: print('')
")"
if [ -n "$AI_ID" ]; then
  ok "the platform accepted the faulty block: nothing but this gate stands between the two"
  xsolla shopbuilder get-ai-block --id "$AI_ID" --json 2>/dev/null | data > "$WORK/ai_block.json"
  $VALIDATE ai-block --block "$WORK/ai_block.json" --json > "$WORK/ai_report.json"
  python3 -c "
import json
rules={v['rule'] for v in json.load(open('$WORK/ai_report.json'))['errors']}
assert 'empty-text-refs' in rules, rules
" 2>/dev/null && ok "the stored block reports empty textRefs -- the CLI cannot declare text fields" \
              || bad "textRefs was not checked on the stored block"
else
  bad "the custom block was not created"
fi

step "Seed 4 -- write constraints, checked without touching the API"
$VALIDATE block --module faq --payload <(echo '{"values":{}}') --version 1 --json > "$WORK/version.json"
python3 -c "
import json
f=json.load(open('$WORK/version.json'))['errors']
assert any(x['path']=='version' and x['expected']=='2' for x in f), f
" 2>/dev/null && ok "a create one version behind maxVersion was rejected" || bad "the version check did not fire"

$VALIDATE block --module header --payload <(echo '{"values":{}}') --json > "$WORK/layout.json"
python3 -c "
import json
f=json.load(open('$WORK/layout.json'))['errors']
assert any(x['path']=='module' for x in f), f
" 2>/dev/null && ok "creating a layout module was rejected" || bad "the layout check did not fire"

$VALIDATE patch --change-set <(echo '{"r1":{"type":"block","id":"b1","patches":[{"op":"replace","path":"values.title"}]}}') --json > "$WORK/patch.json"
python3 -c "
import json
f=json.load(open('$WORK/patch.json'))['errors']
assert any(x['path'].endswith('.path') and x['got']=='string' for x in f), f
" 2>/dev/null && ok "a dotted patch path where segments belong was rejected" || bad "the patch-convention check did not fire"

step "Clean up"
if [ "$KEEP" -eq 1 ]; then
  printf '   kept: %s (%s)\n' "$SLUG" "$LANDING"
else
  # --force skips the interactive confirmation; without it the command waits on a
  # prompt that a non-interactive run never answers.
  xsolla shopbuilder delete-website --slug "$SLUG" --force --json >/dev/null 2>&1 \
    && ok "landing deleted" || bad "could not delete $SLUG -- delete it by hand"
fi
rm -rf "$WORK"

printf '\n%d passed, %d failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
