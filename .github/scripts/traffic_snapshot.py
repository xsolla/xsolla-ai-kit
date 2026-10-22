#!/usr/bin/env python3
"""Keep GitHub traffic history beyond GitHub's 14-day window.

GitHub only serves the last 14 days of views and clones. Run daily, this script
merges each response into CSV files so the history accumulates:

  views.csv      date, views, unique_views        (one row per day)
  clones.csv     date, clones, unique_clones      (one row per day)
  referrers.csv  snapshot_date, referrer, count, uniques   (14-day totals, one snapshot a day)

Rows are keyed by date. A newer snapshot overwrites the same day, because the
most recent day is still partial when it is first fetched.

Usage: traffic_snapshot.py <views.json> <clones.json> <referrers.json> <out-dir>
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def upsert_daily(path: Path, key: str, rows: list[dict], fields: tuple[str, str]) -> int:
    """Merge daily rows into a CSV keyed by date; return the number of days stored."""
    by_date: dict[str, tuple[int, int]] = {}
    if path.exists():
        with path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                by_date[row["date"]] = (int(row[fields[0]]), int(row[fields[1]]))
    for item in rows:
        by_date[item["timestamp"][:10]] = (int(item["count"]), int(item["uniques"]))
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", *fields])
        for date in sorted(by_date):
            writer.writerow([date, *by_date[date]])
    return len(by_date)


def replace_snapshot(path: Path, snapshot_date: str, referrers: list[dict]) -> None:
    """Store today's 14-day referrer totals, replacing any earlier snapshot from today."""
    kept: list[list[str]] = []
    if path.exists():
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)
            kept = [row for row in reader if row and row[0] != snapshot_date]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["snapshot_date", "referrer", "count", "uniques"])
        writer.writerows(kept)
        for item in referrers:
            writer.writerow([snapshot_date, item["referrer"], item["count"], item["uniques"]])


def main(argv: list[str]) -> int:
    if len(argv) != 5:
        print(__doc__, file=sys.stderr)
        return 2
    views = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    clones = json.loads(Path(argv[2]).read_text(encoding="utf-8"))
    referrers = json.loads(Path(argv[3]).read_text(encoding="utf-8"))
    out = Path(argv[4])
    out.mkdir(parents=True, exist_ok=True)

    if "views" not in views or "clones" not in clones or not isinstance(referrers, list):
        print("unexpected API response; is TRAFFIC_TOKEN set with Administration: read?", file=sys.stderr)
        return 1

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    days_v = upsert_daily(out / "views.csv", "views", views["views"], ("views", "unique_views"))
    days_c = upsert_daily(out / "clones.csv", "clones", clones["clones"], ("clones", "unique_clones"))
    replace_snapshot(out / "referrers.csv", today, referrers)
    print(f"views: {days_v} days stored, clones: {days_c} days stored, referrers: {len(referrers)} for {today}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
