#!/usr/bin/env python3
"""Put CLI sandbox mode back on when this Shop Builder run switched it off.

Run it as the last step of every run that used `preflight.py --confirm-sandbox-off`:
after apply and verification, and also when the run stopped or the user did not
confirm the plan. It changes nothing unless preflight recorded a switch.
"""

from __future__ import annotations

import json
import sys

import cli_environment


def main() -> int:
    try:
        result = cli_environment.restore()
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Restore failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
