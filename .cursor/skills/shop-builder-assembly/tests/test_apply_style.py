from __future__ import annotations

import contextlib
import copy
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
EXAMPLE_BRIEF = ROOT / "examples" / "mobile-single-page.json"


def load(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"{name}_for_style_tests", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


apply_style = load("apply_style")
render_plan = load("render_plan")
validate_shop_brief = load("validate_shop_brief")
verify_structure = load("verify_structure")

PALETTE = {
    "bg": "#0b0f1a",
    "overlay": "#151b2b",
    "primary": "#ffb400",
    "text": "#ffffff",
    "isDark": True,
}


def brief_with_palette(palette: dict | None = PALETTE) -> dict:
    brief = json.loads(EXAMPLE_BRIEF.read_text(encoding="utf-8"))
    if palette is not None:
        brief["brand"] = {"theme": dict(palette)}
    return brief


class ThemeBriefTests(unittest.TestCase):
    def test_a_palette_of_hex_colors_and_is_dark_is_valid(self) -> None:
        self.assertEqual([], validate_shop_brief.validate(brief_with_palette()))

    def test_bad_palettes_are_refused(self) -> None:
        cases = {
            "brand.theme must be a non-empty object": {},
            "brand.theme.bg must be a #rrggbb color": {"bg": "navy"},
            "brand.theme.text must be a #rrggbb color": {"text": "#fff"},
            "brand.theme has unknown keys: accent": {"accent": "#ffffff"},
            "brand.theme.isDark must be true or false": {"isDark": "yes"},
        }
        for message, palette in cases.items():
            with self.subTest(message):
                brief = brief_with_palette()
                brief["brand"]["theme"] = palette
                errors = validate_shop_brief.validate(brief)
                self.assertTrue(any(message in error for error in errors), errors)


class ThemePlanTests(unittest.TestCase):
    def test_without_a_palette_the_plan_keeps_the_site_theme(self) -> None:
        plan = render_plan.build_plan(brief_with_palette(None))
        self.assertEqual({"site": None, "pages_to_site_theme": []}, plan["theme"])
        self.assertEqual(["theme"], plan["style_phases"])
        self.assertNotIn("theme", plan["unsupported_phases"])

    def test_the_plan_shows_the_palette_and_the_pages_it_switches(self) -> None:
        brief = brief_with_palette()
        structure = {
            "_id": "landing-1",
            "pages": [
                {"_id": "p1", "path": "/", "theme": {"enabled": True}, "blocks": []},
            ],
        }
        plan = render_plan.build_plan(brief, structure)
        self.assertEqual(PALETTE, plan["theme"]["site"])
        self.assertEqual(["/"], plan["theme"]["pages_to_site_theme"])

        structure["pages"][0]["theme"]["enabled"] = False
        plan = render_plan.build_plan(brief, structure)
        self.assertEqual([], plan["theme"]["pages_to_site_theme"])

    def test_the_palette_is_part_of_what_the_yes_covers(self) -> None:
        approved = render_plan.build_plan(brief_with_palette())
        changed = brief_with_palette({**PALETTE, "primary": "#00ff00"})
        plan = render_plan.build_plan(changed)
        report = {
            "approved_confirmation_id": approved["confirmation_id"],
            "slug": plan["target"]["slug"],
            "landing_id": None,
        }
        self.assertIn(
            "the brand changed", render_plan.approval_changes(approved, plan, report)
        )


class ColorFormatTests(unittest.TestCase):
    def test_parses_hex_rgb_and_rgba(self) -> None:
        self.assertEqual((255, 180, 0, 1.0), apply_style.parse_color("#ffb400"))
        self.assertEqual((255, 255, 255, 1.0), apply_style.parse_color("#fff"))
        self.assertEqual((255, 180, 0, 1.0), apply_style.parse_color("rgb(255, 180, 0)"))
        self.assertEqual((1, 2, 3, 0.5), apply_style.parse_color("rgba(1,2,3,0.5)"))
        for value in ("navy", "#12345", "rgb(1, 2)", "rgb(300, 0, 0)", None, 7):
            self.assertIsNone(apply_style.parse_color(value), value)

    def test_writes_the_color_in_the_format_it_replaces(self) -> None:
        cases = {
            "#000000": "#ffb400",
            "#AABBCC": "#FFB400",
            "#00000080": "#ffb400ff",
            "rgb(0, 0, 0)": "rgb(255, 180, 0)",
            "rgb(0,0,0)": "rgb(255,180,0)",
            "rgba(0, 0, 0, 0.4)": "rgba(255, 180, 0, 1)",
        }
        for current, expected in cases.items():
            with self.subTest(current):
                self.assertEqual(expected, apply_style.in_format_of("#ffb400", current))

    def test_same_color_ignores_the_format(self) -> None:
        self.assertTrue(apply_style.same_color("#FFB400", "rgb(255, 180, 0)"))
        self.assertTrue(apply_style.same_color("#ffb400ff", "rgba(255,180,0,1)"))
        self.assertFalse(apply_style.same_color("#ffb400", "rgba(255, 180, 0, 0.5)"))
        self.assertFalse(apply_style.same_color("#ffb400", "navy"))


class SiteThemeChangeTests(unittest.TestCase):
    def test_patches_only_keys_the_site_theme_has_in_their_format(self) -> None:
        theme = {
            "calculationType": "xds-theme",
            "input": {
                "bg": "rgb(0, 0, 0)",
                "overlay": "#151b2b",
                "primary": {"css": "var(--x)"},
                "isDark": False,
            },
        }
        patches, written, skipped = apply_style.site_theme_changes(theme, PALETTE)
        self.assertEqual({"bg": "rgb(11, 15, 26)", "isDark": True}, written)
        self.assertEqual(
            [
                {"op": "replace", "path": ["theme", "input", "bg"], "value": "rgb(11, 15, 26)"},
                {"op": "replace", "path": ["theme", "input", "isDark"], "value": True},
            ],
            patches,
        )
        self.assertEqual(["primary", "text"], [item["key"] for item in skipped])

    def test_a_theme_without_input_colors_is_skipped_whole(self) -> None:
        patches, written, skipped = apply_style.site_theme_changes({"mainColors": {}}, PALETTE)
        self.assertEqual(([], {}), (patches, written))
        self.assertEqual(sorted(PALETTE), sorted(item["key"] for item in skipped))


class ApplyStyleRunTests(unittest.TestCase):
    """apply_style.py under the plan's yes, against a fake CLI."""

    def setUp(self) -> None:
        self.brief = brief_with_palette()
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.site = {
            "_id": "landing-1",
            "theme": {
                "calculationType": "xds-theme",
                "input": {
                    "bg": "#000000",
                    "overlay": "#111111",
                    "border": "#222222",
                    "primary": "#333333",
                    "secondary": "#444444",
                    "text": "#eeeeee",
                    "isDark": False,
                },
                "calculatedTheme": {"version": 1},
            },
            "pages": [
                {"_id": "page-1", "path": "/", "theme": {"enabled": True}, "blocks": []}
            ],
        }
        self.approve(None)
        self.report = {
            "operation_succeeded": True,
            "approved_confirmation_id": self.approved["confirmation_id"],
            "slug": self.brief["site"]["slug"],
            "landing_id": "landing-1",
            "created_pages": ["/"],
        }
        self.text = {"pages": {"page-1": {"texts": {"L:1": {"en-US": "<p>Hi</p>"}}}}}
        self.calls: list[tuple[str, ...]] = []
        self.recalculates = False
        self.touches_text = False

    def approve(self, structure: dict | None) -> None:
        self.approved = render_plan.build_plan(self.brief, structure)
        (self.root / "approved-plan.json").write_text(
            json.dumps(self.approved), encoding="utf-8"
        )
        (self.root / "brief.json").write_text(json.dumps(self.brief), encoding="utf-8")

    def cli(self, *args: str) -> dict:
        self.calls.append(args)
        if args[1] == "get-localization":
            return {"ok": True, "data": copy.deepcopy(self.text)}
        if args[1] != "update-block":
            raise AssertionError(f"unexpected command {args}")
        for change in json.loads(args[args.index("--data") + 1]).values():
            if change["type"] == "site":
                target = self.site
            else:
                target = next(p for p in self.site["pages"] if p["_id"] == change["id"])
            for patch in change["patches"]:
                node = target
                for key in patch["path"][:-1]:
                    node = node[key]
                node[patch["path"][-1]] = patch["value"]
        if self.recalculates:
            self.site["theme"]["calculatedTheme"] = {"version": 2}
        if self.touches_text:
            self.text["pages"]["page-1"]["texts"]["L:1"]["en-US"] = ""
        return {"ok": True, "data": {}}

    def run_style(self, backup: dict | None = None) -> tuple[int, dict | None, str]:
        (self.root / "run2-report.json").write_text(json.dumps(self.report), encoding="utf-8")
        argv = [
            "apply_style.py",
            str(self.root / "brief.json"),
            "--approved-plan",
            str(self.root / "approved-plan.json"),
            "--run-report",
            str(self.root / "run2-report.json"),
            "--backup-dir",
            str(self.root),
        ]
        saved = copy.deepcopy(self.site if backup is None else backup)
        stdout, stderr = io.StringIO(), io.StringIO()
        with (
            mock.patch.object(sys, "argv", argv),
            mock.patch.object(apply_style, "run_preflight"),
            mock.patch.object(apply_style, "check_cli_context"),
            mock.patch.object(apply_style, "verified_backup", return_value=True),
            mock.patch.object(apply_style, "backup_structure", return_value=saved),
            mock.patch.object(
                apply_style, "structure", side_effect=lambda slug: copy.deepcopy(self.site)
            ),
            mock.patch.object(apply_style, "run_json", side_effect=self.cli),
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            code = apply_style.main()
        report = json.loads(stdout.getvalue()) if stdout.getvalue().strip() else None
        return code, report, stderr.getvalue()

    def updates(self) -> list[dict]:
        return [
            json.loads(call[call.index("--data") + 1])
            for call in self.calls
            if call[1] == "update-block"
        ]

    def test_sets_the_palette_and_switches_a_page_the_run_created(self) -> None:
        code, report, stderr = self.run_style()
        self.assertEqual(0, code, stderr)
        self.assertEqual(1, len(self.updates()))
        inputs = self.site["theme"]["input"]
        self.assertEqual(
            {"bg": "#0b0f1a", "overlay": "#151b2b", "primary": "#ffb400", "text": "#ffffff"},
            {key: inputs[key] for key in ("bg", "overlay", "primary", "text")},
        )
        self.assertTrue(inputs["isDark"])
        self.assertEqual(("#222222", "#444444"), (inputs["border"], inputs["secondary"]))
        self.assertFalse(self.site["pages"][0]["theme"]["enabled"])
        self.assertEqual(["/"], report["theme"]["pages_to_site_theme"])
        self.assertFalse(report["published"])

    def test_without_recalculation_the_handoff_gets_the_editor_step(self) -> None:
        code, report, stderr = self.run_style()
        self.assertEqual(0, code, stderr)
        self.assertFalse(report["theme"]["recalculated"])
        self.assertIn("Recalculate the theme in the Site Builder editor", report["needs_human"][0])
        self.assertIn("primary #ffb400", report["needs_human"][0])

    def test_a_cli_that_recalculates_needs_no_editor_step(self) -> None:
        self.recalculates = True
        code, report, stderr = self.run_style()
        self.assertEqual(0, code, stderr)
        self.assertTrue(report["theme"]["recalculated"])
        self.assertEqual([], report["needs_human"])

    def test_a_rerun_writes_nothing(self) -> None:
        self.assertEqual(0, self.run_style()[0])
        self.calls.clear()
        code, report, stderr = self.run_style()
        self.assertEqual(0, code, stderr)
        self.assertEqual([], self.updates())
        self.assertEqual([], report["theme"]["patched"])
        self.assertEqual(sorted(PALETTE), report["theme"]["unchanged"])

    def test_an_existing_page_the_plan_didnt_list_keeps_its_theme(self) -> None:
        self.report["created_pages"] = []
        code, report, stderr = self.run_style()
        self.assertEqual(0, code, stderr)
        self.assertTrue(self.site["pages"][0]["theme"]["enabled"])
        self.assertEqual([], report["theme"]["pages_to_site_theme"])
        self.assertTrue(any("Page / existed before" in item for item in report["needs_human"]))

    def test_an_existing_page_the_plan_listed_is_switched(self) -> None:
        self.approve(self.site)
        self.report["approved_confirmation_id"] = self.approved["confirmation_id"]
        self.report["created_pages"] = []
        code, report, stderr = self.run_style()
        self.assertEqual(0, code, stderr)
        self.assertFalse(self.site["pages"][0]["theme"]["enabled"])

    def test_stops_when_the_site_text_changes(self) -> None:
        self.touches_text = True
        code, _, stderr = self.run_style()
        self.assertEqual(1, code)
        self.assertIn("the site's text changed during the theme patch", stderr)

    def test_refuses_a_brief_changed_after_the_yes(self) -> None:
        changed = brief_with_palette({**PALETTE, "primary": "#00ff00"})
        (self.root / "brief.json").write_text(json.dumps(changed), encoding="utf-8")
        code, _, stderr = self.run_style()
        self.assertEqual(1, code)
        self.assertIn("the shop brief changed after the plan was approved", stderr)
        self.assertEqual([], self.calls)

    def test_refuses_a_report_from_another_approval(self) -> None:
        self.report["approved_confirmation_id"] = "sha256:000000000000"
        code, _, stderr = self.run_style()
        self.assertEqual(1, code)
        self.assertIn("is not a run under the approved plan", stderr)
        self.assertEqual([], self.calls)

    def test_refuses_when_the_site_changed_after_the_backup(self) -> None:
        backup = copy.deepcopy(self.site)
        backup["pages"][0]["blocks"].append({"_id": "x", "module": "faq"})
        code, _, stderr = self.run_style(backup)
        self.assertEqual(1, code)
        self.assertIn("the site changed after the backup", stderr)
        self.assertEqual([], self.updates())

    def test_without_a_palette_nothing_runs(self) -> None:
        self.brief = brief_with_palette(None)
        self.approve(None)
        self.report["approved_confirmation_id"] = self.approved["confirmation_id"]
        code, report, stderr = self.run_style()
        self.assertEqual(0, code, stderr)
        self.assertEqual("theme-kept", report["status"])
        self.assertEqual([], self.calls)


class VerifyThemeTests(unittest.TestCase):
    def plan(self) -> dict:
        return {"theme": {"site": PALETTE, "pages_to_site_theme": []}}

    def test_a_matching_theme_passes(self) -> None:
        current = {
            "theme": {
                "input": {
                    "bg": "rgb(11, 15, 26)",
                    "overlay": "#151B2B",
                    "primary": "#ffb400",
                    "text": "#ffffff",
                    "isDark": True,
                }
            }
        }
        page = {"path": "/", "theme": {"enabled": False}}
        self.assertEqual(
            ([], []), verify_structure.theme_findings(self.plan(), current, ["/"], {"/": page})
        )

    def test_a_different_color_fails_and_a_skipped_key_warns(self) -> None:
        current = {"theme": {"input": {"bg": "#000000", "overlay": "#151b2b", "isDark": True}}}
        page = {"path": "/", "theme": {"enabled": True}}
        errors, warnings = verify_structure.theme_findings(
            self.plan(), current, ["/"], {"/": page}
        )
        self.assertEqual(["theme bg differs: expected #0b0f1a, got #000000"], errors)
        self.assertIn("the site theme has no primary; it keeps the template's", warnings)
        self.assertIn(
            "pages on their own theme, which ignore the site colors: /", warnings
        )

    def test_no_palette_checks_nothing(self) -> None:
        self.assertEqual(
            ([], []), verify_structure.theme_findings({"theme": {"site": None}}, {}, [], {})
        )


if __name__ == "__main__":
    unittest.main()
