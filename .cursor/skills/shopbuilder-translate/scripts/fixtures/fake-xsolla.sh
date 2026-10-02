#!/usr/bin/env bash
# A stand-in for the xsolla CLI, so verify.sh can be exercised with no network and no store.
# Serves canned responses from $FAKE_STORE, in the SAME envelope the real CLI uses
# ({"ok":true,"data":…}) — the envelope is itself a trap worth testing against.
set -euo pipefail
STORE="${FAKE_STORE:?FAKE_STORE must point at a fixture store dir}"
GROUP="${1:-}"; CMD="${2:-}"; shift 2 || true

arg() { # arg <flag> — value of a --flag from the remaining args
  local want="$1"; shift || true
  while [ $# -gt 0 ]; do [ "$1" = "$want" ] && { echo "${2:-}"; return 0; }; shift; done
  return 0
}
emit() { [ -f "$1" ] || { echo "not found: $(basename "$1")" >&2; exit 1; }; printf '{"ok":true,"data":%s}' "$(cat "$1")"; }

if [ -n "${FAKE_FAIL_CMD:-}" ] && [ "${FAKE_FAIL_CMD}" = "$GROUP $CMD" ]; then
  echo "forced failure" >&2
  exit 1
fi

case "$GROUP $CMD" in
  "shopbuilder get-localization")
      # The real command takes --slug ONLY; --merchant-id is a hard 'unknown flag' that
      # prints plain text. Reproduce that, so the caller is tested against it.
      for a in "$@"; do case "$a" in --merchant-id|--project-id)
        echo "unknown flag: $a" >&2; exit 1 ;; esac; done
      emit "$STORE/localization.json" ;;
  "shopbuilder get-structure")
      if [ -n "${FAKE_LANG_FILE:-}" ] && [ -f "$FAKE_LANG_FILE" ]; then
        body="$(jq -c --slurpfile langs "$FAKE_LANG_FILE" '.languages = $langs[0]' "$STORE/structure.json")"
        printf '{"ok":true,"data":%s}' "$body"
      else
        emit "$STORE/structure.json"
      fi ;;
  "shopbuilder update-many-localization")
      echo '{"ok":true,"data":{}}' ;;
  "shopbuilder add-language"|"shopbuilder delete-language")
      # No language file: the caller is not exercising order. Succeed so a store that
      # already opens in the target does not need a mutable list.
      [ -n "${FAKE_LANG_FILE:-}" ] || { echo '{"ok":true,"data":{}}'; exit 0; }
      lang="$(arg --language "$@")"
      if [ "$CMD" = "add-language" ] && [ "$lang" = "${FAKE_LANG_REJECT:-}" ]; then
        echo "language $lang is not enabled on the project" >&2
        exit 1
      fi
      if [ "$CMD" = "add-language" ]; then
        if jq -e --arg l "$lang" 'index($l) != null' "$FAKE_LANG_FILE" >/dev/null; then
          echo "language is taken" >&2
          exit 1
        fi
        jq -c --arg l "$lang" '. + [$l]' "$FAKE_LANG_FILE" > "$FAKE_LANG_FILE.tmp"
      else
        jq -c --arg l "$lang" 'map(select(. != $l))' "$FAKE_LANG_FILE" > "$FAKE_LANG_FILE.tmp"
      fi
      mv "$FAKE_LANG_FILE.tmp" "$FAKE_LANG_FILE"
      echo '{"ok":true,"data":{}}' ;;
  *) echo "fake-xsolla: unhandled '$GROUP $CMD'" >&2; exit 1 ;;
esac
