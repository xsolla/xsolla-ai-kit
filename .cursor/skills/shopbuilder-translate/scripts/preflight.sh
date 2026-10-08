#!/usr/bin/env bash
# preflight.sh — verify the environment before any Shop Builder translation. Fails loudly.
# Catalog and LiveOps text are out of scope. This check is the storefront only.
# apply.sh checks the approved-test-project allowlist before the first write.
# There is no production-project denylist.
set -euo pipefail

RED=$'\033[31m'; GRN=$'\033[32m'; YEL=$'\033[33m'; RST=$'\033[0m'
fail=0
ok()   { printf '%s  ok  %s %s\n' "$GRN" "$RST" "$1"; }
bad()  { printf '%s FAIL %s %s\n' "$RED" "$RST" "$1"; fail=1; }
warn() { printf '%s warn %s %s\n' "$YEL" "$RST" "$1"; }

echo "== xsolla CLI =="
XS="${XSOLLA_CLI:-$(command -v xsolla 2>/dev/null || true)}"
if [ -z "$XS" ]; then
  bad "xsolla CLI not on PATH. Set XSOLLA_CLI=/abs/path/to/xsolla to override."
else
  ok "using $XS ($("$XS" --version 2>/dev/null | head -1))"
fi

if [ -n "$XS" ]; then
  echo "== required subcommands =="
  sb="$("$XS" shopbuilder --help 2>&1 || true)"
  for c in get-structure get-localization update-many-localization add-language get-block; do
    grep -qE "^\s*$c\b" <<<"$sb" && ok "shopbuilder $c" || bad "shopbuilder $c MISSING"
  done
fi

echo "== credentials =="
acct=""; [ -n "$XS" ] && acct="$("$XS" auth list-account 2>&1 || true)"
if [ -n "$acct" ] && ! grep -qi 'no accounts stored' <<<"$acct"; then
  ok "xsolla auth session present (Shop Builder session auto-bootstraps)"
else
  bad "no auth. Run 'xsolla auth login' (add --audience https://api.xsolla.com if it asks). Do not pass a session token by hand."
fi
[ -n "${XSOLLA_PROJECT_ID:-}" ]  && ok "XSOLLA_PROJECT_ID set"  || bad "XSOLLA_PROJECT_ID unset"
[ -n "${XSOLLA_MERCHANT_ID:-}" ] && ok "XSOLLA_MERCHANT_ID set" || bad "XSOLLA_MERCHANT_ID unset"

echo "== approved test project =="
echo "  writes require the approved-test-project allowlist"
echo "  apply.sh checks the allowlist, then reads the site, before the first write"
if [ -n "${XSOLLA_APPROVED_TEST_PROJECTS:-}" ] && [ -f "${XSOLLA_APPROVED_TEST_PROJECTS}" ]; then
  ok "XSOLLA_APPROVED_TEST_PROJECTS=$XSOLLA_APPROVED_TEST_PROJECTS"
else
  warn "XSOLLA_APPROVED_TEST_PROJECTS is unset or not a file — apply.sh --commit will refuse to write"
fi

echo "== tooling =="
command -v python3 >/dev/null 2>&1 && ok "python3" || bad "python3 not installed"

echo
if [ "$fail" = 0 ]; then echo "${GRN}preflight passed${RST}"
else echo "${RED}preflight failed — fix the above before backup/extract/apply${RST}"; exit 1; fi
