#!/bin/bash
# check-headless-unchanged.sh [base] — "headless path unchanged", asserted rather than eyeballed.
#
# FAILS (exit 1) if the branch touches a headless-only skill. LISTS shared-skill changes, which
# are allowed but must be called out and justified in the PR. Covers committed changes since the
# merge-base with [base] (default origin/main), plus staged, unstaged and untracked files.
#
# The two lists are the SB-8794 reading of "headless path unchanged": headless-only skills must
# not change; shared skills may, if called out. A skill in neither list is reported UNCLASSIFIED —
# classify it before relying on this check for it.
set -u
REPO=$(git -C "$(dirname "$0")" rev-parse --show-toplevel) || exit 2
BASE=${1:-origin/main}
HEADLESS_ONLY="headless-checkout-integration login-styling"
SHARED="merchant-setup catalog-design login-setup webhooks-impl shop-setup"
ADDED_BY_THIS_WORK="shop-plan shopbuilder-storefront shopbuilder-site shopbuilder-page shopbuilder-blocks shopbuilder-customize shopbuilder-custom-block"

cd "$REPO" || exit 2
MB=$(git merge-base "$BASE" HEAD) || { echo "no merge-base with $BASE"; exit 2; }
changed=$( { git diff --name-only "$MB"; git diff --name-only --cached "$MB"
             git ls-files --others --exclude-standard; } | sort -u )

echo "== $(git branch --show-current) vs $BASE @ ${MB:0:7} =="
FAIL=0; shared_hits=""; unclassified=""
for f in $changed; do
  case "$f" in skills/*|.cursor/skills/*) ;; *) continue ;; esac
  skill=$(echo "$f" | sed -E 's#^(\.cursor/)?skills/([^/]+).*#\2#')
  if   [[ " $HEADLESS_ONLY " == *" $skill "* ]];      then echo "  FAIL  headless-only skill changed: $f"; FAIL=1
  elif [[ " $SHARED " == *" $skill "* ]];             then shared_hits+="    $f"$'\n'
  elif [[ " $ADDED_BY_THIS_WORK " == *" $skill "* ]]; then :
  elif [ "$skill" = "README.md" ];                    then :
  else unclassified+="    $f"$'\n'
  fi
done

[ $FAIL = 0 ] && echo "  PASS  no file under: $HEADLESS_ONLY"
[ -n "$shared_hits" ] && printf '  CALL OUT in the PR — shared skills changed:\n%s' "$shared_hits"
[ -n "$unclassified" ] && printf '  UNCLASSIFIED — in neither list:\n%s' "$unclassified"
exit $FAIL
