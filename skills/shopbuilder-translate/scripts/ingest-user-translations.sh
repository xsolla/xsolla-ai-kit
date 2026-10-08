#!/usr/bin/env bash
# ingest-user-translations.sh <target-locale> <file.json|file.txt>
#
# Publisher already has translations. Accept JSON or TXT. Merge them into
# l10n/work/<target>/translated.json. Does not write to the store.
#
# JSON: a full translated.json, {"units":[{"id","target"}]}, or a flat {id: text} map.
# TXT:  one unit per line — `id<TAB>target` or `id: target`. Lines starting with # ignored.
set -euo pipefail

TGT="${1:?usage: ingest-user-translations.sh <target-locale> <file.json|file.txt>}"
SRCFILE="${2:?usage: ingest-user-translations.sh <target-locale> <file.json|file.txt>}"
[ -f "$SRCFILE" ] || { echo "missing $SRCFILE" >&2; exit 1; }

WORKDIR="l10n/work/$TGT"
BASE="$WORKDIR/translatable.json"
OUT="$WORKDIR/translated.json"
[ -f "$BASE" ] || { echo "missing $BASE — run extract.sh first" >&2; exit 1; }

TGT="$TGT" BASE="$BASE" OUT="$OUT" SRCFILE="$SRCFILE" python3 <<'PY'
import json, os, re, copy

base = json.load(open(os.environ["BASE"]))
srcfile = os.environ["SRCFILE"]
out = os.environ["OUT"]
raw = open(srcfile, encoding="utf-8").read()

by_id = {}
if srcfile.lower().endswith(".json"):
    doc = json.loads(raw)
    if isinstance(doc, dict) and isinstance(doc.get("units"), list):
        for u in doc["units"]:
            if isinstance(u, dict) and u.get("id") and u.get("target"):
                by_id[u["id"]] = u["target"]
    elif isinstance(doc, dict):
        for k, v in doc.items():
            if isinstance(v, str) and v.strip() and k != "meta":
                by_id[k] = v
    else:
        raise SystemExit("JSON must be a translated.json, {units:[...]}, or {id: text} map")
else:
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "\t" in line:
            i, t = line.split("\t", 1)
        elif ": " in line:
            i, t = line.split(": ", 1)
        else:
            raise SystemExit(f"TXT line must be id<TAB>target or 'id: target': {line!r}")
        by_id[i.strip()] = t.strip()

# Start from an existing translated.json so a later file does not erase targets
# the model already filled. Seed from translatable.json only on the first ingest.
prior = {}
if os.path.isfile(out):
    prev = json.load(open(out))
    for u in prev.get("units") or []:
        if isinstance(u, dict) and u.get("id") and (u.get("target") or "").strip():
            prior[u["id"]] = u["target"]
doc = copy.deepcopy(base)
filled = missing = extra = kept = 0
known = {u["id"] for u in doc["units"]}
for u in doc["units"]:
    t = by_id.get(u["id"])
    if t:
        u["target"] = t
        filled += 1
    elif u["id"] in prior:
        u["target"] = prior[u["id"]]
        kept += 1
    elif u.get("kind") not in ("legal", "asset"):
        missing += 1
extra = len(set(by_id) - known)
doc["meta"]["ingest"] = {
    "file": srcfile,
    "filled": filled,
    "kept": kept,
    "still_empty": missing,
    "unknown_ids": extra,
}
os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump(doc, open(out, "w"), indent=2, ensure_ascii=False)
print(f"ingest  filled={filled}  kept={kept}  still_empty={missing}  unknown_ids={extra}")
print(f"wrote {out}")
if missing:
    print("still_empty units need an LLM pass or a more complete file — do not --commit yet")
PY
