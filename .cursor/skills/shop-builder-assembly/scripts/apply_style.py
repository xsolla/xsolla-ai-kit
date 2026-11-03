#!/usr/bin/env python3
"""Apply the approved site theme after the last apply_plan.py run, under the same yes.

Sets the site theme's colors (`theme.input`) to the palette in the approved plan's brand,
and switches the planned pages to the site theme. Only keys the site theme already has
are patched, each in the format its current value has. A page that existed before this
assembly is switched only when the approved plan listed it. Never publishes.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# `python3 -I` (isolated mode) does not put the script's own folder on sys.path, so
# the sibling imports below would fail. Add it explicitly.
SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from apply_plan import (
    backup_structure,
    check_cli_context,
    data,
    page_for_path,
    run_json,
    run_preflight,
    structure,
    verified_backup,
)
from render_plan import (
    canonical_hash,
    load_approved_plan,
    load_run_report,
    structure_hash,
    uses_own_theme,
)
from validate_shop_brief import THEME_COLORS, load_brief, validate

RECALCULATE_IN_EDITOR = (
    "Recalculate the theme in the Site Builder editor: the CLI saved the colors but "
    "didn't recalculate the theme the pages render from. Open a page, change one color "
    "in the Theme panel by one step and back, click Save as global theme, then turn Use "
    "global theme back on. With Use global theme off, Save as global theme saves that "
    "page's own copy over the site theme, so check the colors in the panel first: {colors}"
)
OWN_THEME_IN_EDITOR = (
    "Page {path} existed before this assembly and uses its own theme, so it ignores the "
    "site colors. Turn on Use global theme for it in the Site Builder editor if it "
    "should match the site."
)

COLOR = re.compile(
    r"#(?P<hex>[0-9a-fA-F]{3,8})"
    r"|rgba?\((?P<args>[^)]*)\)"
)


def parse_color(value: object) -> tuple[int, int, int, float] | None:
    """Return a color's red, green, blue and alpha, or None for a format not handled."""
    if not isinstance(value, str):
        return None
    match = COLOR.fullmatch(value.strip())
    if match is None:
        return None
    if match["hex"] is not None:
        digits = match["hex"]
        if len(digits) in (3, 4):
            digits = "".join(digit * 2 for digit in digits)
        if len(digits) not in (6, 8):
            return None
        alpha = int(digits[6:8], 16) / 255 if len(digits) == 8 else 1.0
        return (int(digits[0:2], 16), int(digits[2:4], 16), int(digits[4:6], 16), alpha)
    parts = [part.strip() for part in match["args"].split(",")]
    if len(parts) not in (3, 4):
        return None
    try:
        red, green, blue = (int(part) for part in parts[:3])
        alpha = float(parts[3]) if len(parts) == 4 else 1.0
    except ValueError:
        return None
    if not all(0 <= channel <= 255 for channel in (red, green, blue)) or not 0 <= alpha <= 1:
        return None
    return (red, green, blue, alpha)


def same_color(left: object, right: object) -> bool:
    first, second = parse_color(left), parse_color(right)
    return (
        first is not None
        and second is not None
        and first[:3] == second[:3]
        and abs(first[3] - second[3]) < 0.01
    )


def in_format_of(color: str, current: str) -> str:
    """Write the brief's `#rrggbb` color in the format of the value it replaces."""
    red, green, blue, _ = parse_color(color)  # type: ignore[misc]
    text = current.strip()
    if text.startswith("#"):
        hex_value = f"{red:02x}{green:02x}{blue:02x}"
        if len(text) in (5, 9):
            hex_value += "ff"
        if any(char.isupper() for char in text[1:]):
            hex_value = hex_value.upper()
        return "#" + hex_value
    separator = ", " if ", " in text else ","
    channels = separator.join(str(channel) for channel in (red, green, blue))
    if text.startswith("rgba"):
        return f"rgba({channels}{separator}1)"
    return f"rgb({channels})"


def site_theme_changes(site_theme: object, palette: dict) -> tuple[list[dict], dict, list]:
    """Return the patches that set ``palette`` on the site theme, the values they write,
    and the keys left alone with the reason."""
    inputs = site_theme.get("input") if isinstance(site_theme, dict) else None
    if not isinstance(inputs, dict):
        return [], {}, [
            {"key": key, "reason": "the site theme has no input colors"} for key in palette
        ]
    patches, written, skipped = [], {}, []
    for key, value in palette.items():
        if key not in inputs:
            skipped.append({"key": key, "reason": "the site theme has no such key"})
            continue
        current = inputs[key]
        if key == "isDark":
            if not isinstance(current, bool):
                skipped.append({"key": key, "reason": "its value isn't true or false"})
            elif current != value:
                written[key] = value
        elif parse_color(current) is None:
            skipped.append(
                {"key": key, "reason": f"its value {current!r} isn't a format this writes"}
            )
        elif not same_color(current, value):
            written[key] = in_format_of(value, current)
    for key, value in written.items():
        patches.append({"op": "replace", "path": ["theme", "input", key], "value": value})
    return patches, written, skipped


def check_reports(reports: list[dict], paths: list[Path], approved: dict, slug: str) -> None:
    for path, report in zip(paths, reports):
        if (
            report.get("approved_confirmation_id") != approved["confirmation_id"]
            or report.get("slug") != slug
        ):
            raise RuntimeError(f"{path} is not a run under the approved plan")


def localization(slug: str) -> object:
    return data(run_json("shopbuilder", "get-localization", "--slug", slug))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("brief", type=Path)
    parser.add_argument("--approved-plan", type=Path, required=True)
    parser.add_argument("--run-report", type=Path, action="append", required=True)
    parser.add_argument("--backup-dir", type=Path, required=True)
    parser.add_argument("--approved-test-projects", type=Path)
    args = parser.parse_args()
    try:
        brief = load_brief(args.brief)
        errors = validate(brief)
        if errors:
            raise RuntimeError("invalid shop brief: " + "; ".join(errors))
        approved = load_approved_plan(args.approved_plan)
        if approved.get("brief_sha256") != canonical_hash(brief):
            raise RuntimeError("the shop brief changed after the plan was approved")
        slug = brief["site"]["slug"]
        reports = [load_run_report(path) for path in args.run_report]
        check_reports(reports, args.run_report, approved, slug)
        palette = approved.get("brand", {}).get("theme")
        if not palette:
            print(
                json.dumps(
                    {
                        "operation_succeeded": True,
                        "status": "theme-kept",
                        "slug": slug,
                        "theme": "no palette in the approved plan; the site keeps its theme",
                        "published": False,
                    },
                    indent=2,
                )
            )
            return 0

        run_preflight(args.brief, args.approved_test_projects)
        check_cli_context(brief["project"])
        if not verified_backup(args.backup_dir, brief["project"], slug):
            raise RuntimeError(
                "a complete verified backup taken after the last apply run is required"
            )
        current = structure(slug)
        if structure_hash(current) != structure_hash(backup_structure(args.backup_dir)):
            raise RuntimeError("the site changed after the backup; back up again")
        landing_id = current.get("_id")
        if not isinstance(landing_id, str) or any(
            report.get("landing_id") != landing_id for report in reports
        ):
            raise RuntimeError("the site isn't the one the run reports describe")

        site_patches, written, skipped = site_theme_changes(current.get("theme"), palette)
        listed = set(approved.get("theme", {}).get("pages_to_site_theme", []))
        created_pages = {
            path
            for report in reports
            for path in report.get("created_pages", [])
            if isinstance(path, str)
        }
        changes: dict[str, dict] = {}
        if site_patches:
            changes["site"] = {"type": "site", "id": landing_id, "patches": site_patches}
        switched, needs_human = [], []
        for index, page_plan in enumerate(approved.get("pages", [])):
            page = page_for_path(current, page_plan["path"])
            if page is None or not isinstance(page.get("_id"), str):
                raise RuntimeError(
                    f"page {page_plan['path']} is missing; finish apply_plan.py first"
                )
            if not uses_own_theme(page):
                continue
            if page_plan["path"] in listed or page_plan["path"] in created_pages:
                changes[f"page{index}"] = {
                    "type": "page",
                    "id": page["_id"],
                    "patches": [
                        {"op": "replace", "path": ["theme", "enabled"], "value": False}
                    ],
                }
                switched.append(page_plan["path"])
            else:
                needs_human.append(OWN_THEME_IN_EDITOR.format(path=page_plan["path"]))

        recalculated = None
        if changes:
            text_before = localization(slug)
            calculated_before = (current.get("theme") or {}).get("calculatedTheme")
            run_json(
                "shopbuilder",
                "update-block",
                "--landing-id",
                landing_id,
                "--data",
                json.dumps(changes, separators=(",", ":")),
            )
            saved = structure(slug)
            if localization(slug) != text_before:
                raise RuntimeError(
                    "the site's text changed during the theme patch; stop and compare "
                    "get-localization with the backup"
                )
            saved_inputs = (saved.get("theme") or {}).get("input") or {}
            missing = [
                key
                for key, value in written.items()
                if not (
                    saved_inputs.get(key) == value
                    if key == "isDark"
                    else same_color(saved_inputs.get(key), value)
                )
            ]
            missing += [
                path for path in switched if uses_own_theme(page_for_path(saved, path))
            ]
            if missing:
                raise RuntimeError("the theme change did not persist: " + ", ".join(missing))
            if site_patches:
                recalculated = (
                    (saved.get("theme") or {}).get("calculatedTheme") != calculated_before
                )
                if not recalculated:
                    colors = ", ".join(
                        f"{key} {value}" for key, value in palette.items() if key != "isDark"
                    )
                    needs_human.insert(0, RECALCULATE_IN_EDITOR.format(colors=colors))

        print(
            json.dumps(
                {
                    "operation_succeeded": True,
                    "status": "theme-applied",
                    "approved_confirmation_id": approved["confirmation_id"],
                    "slug": slug,
                    "landing_id": landing_id,
                    "theme": {
                        "patched": sorted(written),
                        "unchanged": sorted(
                            set(palette) - set(written) - {item["key"] for item in skipped}
                        ),
                        "skipped": skipped,
                        "pages_to_site_theme": switched,
                        "recalculated": recalculated,
                    },
                    "needs_human": needs_human,
                    "pending_phases": approved.get("unsupported_phases", []),
                    "published": False,
                },
                indent=2,
            )
        )
        return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Theme failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
