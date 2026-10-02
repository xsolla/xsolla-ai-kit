#!/usr/bin/env bash
# export-backup.sh <domain> <output-dir>
#
# Read-only export of the two files extract.sh reads: structure.json and
# localization.json. Does not change the site. The approved-test-project
# allowlist is checked by apply.sh before a write, not here.
set -euo pipefail

DOMAIN="${1:?usage: export-backup.sh <domain> <output-dir>}"
OUT="${2:?usage: export-backup.sh <domain> <output-dir>}"
XS="${XSOLLA_CLI:-xsolla}"

mkdir -p "$OUT"
"$XS" shopbuilder get-structure --slug "$DOMAIN" > "$OUT/structure.json"
"$XS" shopbuilder get-localization --slug "$DOMAIN" > "$OUT/localization.json"

python3 - "$OUT" <<'PY'
import json, sys
from pathlib import Path
out = Path(sys.argv[1])
for name in ("structure.json", "localization.json"):
    json.loads((out / name).read_text(encoding="utf-8"))
print(out.resolve())
PY
