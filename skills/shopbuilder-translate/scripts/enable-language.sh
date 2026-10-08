#!/usr/bin/env bash
# enable-language.sh <domain> <locale>
#
# Runs shopbuilder add-language. A 400 whose message says the language is taken
# means the locale is already enabled: that is success. Any other failure stops.
set -euo pipefail

DOMAIN="${1:?usage: enable-language.sh <domain> <locale>}"
LOCALE="${2:?usage: enable-language.sh <domain> <locale>}"
XS="${XSOLLA_CLI:-xsolla}"

set +e
out="$("$XS" shopbuilder add-language --slug "$DOMAIN" --language "$LOCALE" 2>&1)"
rc=$?
set -e

if [ "$rc" -eq 0 ]; then
  echo "enabled $LOCALE on $DOMAIN"
  exit 0
fi
if grep -qi 'language is taken' <<<"$out"; then
  echo "$LOCALE is already enabled on $DOMAIN"
  exit 0
fi
printf '%s\n' "$out" >&2
exit "$rc"
