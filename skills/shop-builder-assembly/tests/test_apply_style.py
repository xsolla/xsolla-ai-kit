from __future__ import annotations

import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
import uuid
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
        self.assertEqual(["theme", "images", "copy"], plan["style_phases"])
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
        self.assertIn("older mainColors shape", skipped[0]["reason"])
        _, _, skipped = apply_style.site_theme_changes({}, PALETTE)
        self.assertEqual("the site theme has no input colors", skipped[0]["reason"])


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
        self.backup_text: dict | None = None
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
        (self.root / "localization.json").write_text(
            json.dumps({"ok": True, "data": self.backup_text or self.text}), encoding="utf-8"
        )
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
        self.assertEqual(1, len(report["needs_human"]))
        self.assertIn("Pay Station customization", report["needs_human"][0])

    def test_the_handoff_gives_the_palette_for_the_pay_station_theme(self) -> None:
        code, report, stderr = self.run_style()
        self.assertEqual(0, code, stderr)
        step = report["needs_human"][-1]
        project = self.brief["project"]
        self.assertIn(
            f"https://publisher.xsolla.com/{project['merchant_id']}/projects/"
            f"{project['project_id']}/payments/theme",
            step,
        )
        self.assertIn("surfaces #0b0f1a and #151b2b; texts #ffffff; controls #ffb400", step)
        self.assertIn("every project in this Publisher Account", step)

    def test_no_palette_no_pay_station_step(self) -> None:
        self.assertIsNone(apply_style.pay_station_step(None, {"merchant_id": 1, "project_id": 2}))
        self.assertIsNone(
            apply_style.pay_station_step({"isDark": True}, {"merchant_id": 1, "project_id": 2})
        )

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

    def test_stops_when_the_text_changed_after_the_backup(self) -> None:
        self.backup_text = copy.deepcopy(self.text)
        self.text["pages"]["page-1"]["texts"]["L:1"]["en-US"] = "<p>Edited in the editor</p>"
        code, _, stderr = self.run_style()
        self.assertEqual(1, code)
        self.assertIn("the site's text changed after the backup", stderr)
        self.assertEqual([], self.updates())

    def test_pages_keep_their_own_theme_when_the_palette_wasnt_set(self) -> None:
        self.site["theme"] = {"mainColors": {"accentColor": "rgba(1,2,3,1)"}}
        code, report, stderr = self.run_style()
        self.assertEqual(0, code, stderr)
        self.assertTrue(self.site["pages"][0]["theme"]["enabled"])
        self.assertEqual([], self.updates())
        self.assertTrue(any("older mainColors shape" in item for item in report["needs_human"]))

    def test_a_rerun_keeps_the_recalculation_reminder(self) -> None:
        self.assertEqual(0, self.run_style()[0])
        code, report, stderr = self.run_style()
        self.assertEqual(0, code, stderr)
        self.assertTrue(report["needs_human"][0].startswith("If the theme wasn't recalculated"))

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
        self.assertEqual("nothing-to-apply", report["status"])
        self.assertEqual([], self.calls)


class ImageBriefTests(unittest.TestCase):
    def brief(self, images: object) -> dict:
        brief = brief_with_palette(None)
        brief["brand"] = {"images": images}
        return brief

    def test_local_images_on_a_block_slot_are_valid(self) -> None:
        images = [
            {"file": "art/hero.webp", "module": "leadGameSales", "slot": "background"},
            {"file": "art/icon.png", "module": "footer", "slot": "logo", "page": "/"},
        ]
        self.assertEqual([], validate_shop_brief.validate(self.brief(images)))

    def test_bad_images_are_refused(self) -> None:
        good = {"file": "hero.png", "module": "leadGameSales", "slot": "background"}
        cases = {
            "brand.images must be a non-empty list": [],
            "must be a local file; download it first": [
                {**good, "file": "https://store.example/hero.png"}
            ],
            "brand.images[0].file must be one of": [{**good, "file": "hero.psd"}],
            "brand.images[0].module must be a verified block module": [
                {**good, "module": "carousel"}
            ],
            "brand.images[0].slot must be one of": [{**good, "slot": "icon"}],
            "brand.images[0].page must be a page path": [{**good, "page": "store"}],
            "brand.images[0] has unknown keys: url": [{**good, "url": "x"}],
        }
        for message, images in cases.items():
            with self.subTest(message):
                errors = validate_shop_brief.validate(self.brief(images))
                self.assertTrue(any(message in error for error in errors), errors)


class ImagesPlanTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        (self.root / "hero.png").write_bytes(b"hero-art")
        self.brief = brief_with_palette(None)
        self.brief["brand"] = {
            "images": [{"file": "hero.png", "module": "leadGameSales", "slot": "background"}]
        }

    def test_the_plan_binds_each_image_to_its_file_content(self) -> None:
        plan = render_plan.build_plan(self.brief, base_dir=self.root)
        image = plan["images"][0]
        self.assertEqual(hashlib.sha256(b"hero-art").hexdigest(), image["sha256"])
        self.assertEqual(["/"], image["pages"])
        self.assertEqual([], image["existing_block_ids"])
        self.assertEqual(["theme", "images", "copy"], [
            phase for phase in plan["order"] if phase in ("theme", "images", "copy")
        ])

    def test_a_logo_image_answers_the_missing_logo_warning(self) -> None:
        no_logo = "No logo supplied; keep the template text identity until approved."
        self.assertIn(no_logo, render_plan.build_plan(self.brief)["warnings"])
        self.brief["brand"]["images"].append(
            {"file": "hero.png", "module": "footer", "slot": "logo"}
        )
        self.assertNotIn(no_logo, render_plan.build_plan(self.brief)["warnings"])

    def test_a_missing_file_or_block_is_a_warning(self) -> None:
        self.brief["brand"]["images"].append(
            {"file": "gone.png", "module": "gallery", "slot": "background"}
        )
        plan = render_plan.build_plan(self.brief, base_dir=self.root)
        self.assertIsNone(plan["images"][1]["sha256"])
        self.assertIn("Image gone.png was not found next to the brief.", plan["warnings"])
        self.assertTrue(
            any("has no gallery block to go on" in warning for warning in plan["warnings"])
        )

    def test_an_existing_block_that_stays_is_listed_for_the_yes(self) -> None:
        structure = {
            "_id": "landing-1",
            "pages": [
                {
                    "_id": "p1",
                    "path": "/",
                    "blocks": [
                        {"_id": "old-header", "module": "header", "values": {}},
                        {"_id": "old-hero", "module": "leadGameSales", "values": {}},
                        {"_id": "spare-hero", "module": "leadGameSales", "values": {}},
                    ],
                }
            ],
        }
        plan = render_plan.build_plan(self.brief, structure, base_dir=self.root)
        self.assertEqual(["old-hero"], plan["images"][0]["existing_block_ids"])
        plan = render_plan.build_plan(
            self.brief, structure, frozenset({"old-hero", "spare-hero"}), self.root
        )
        self.assertEqual([], plan["images"][0]["existing_block_ids"])

    def test_the_call_to_action_block_is_not_a_hero_alias(self) -> None:
        brief = brief_with_palette(None)
        brief["content"] = {
            "copy": [{"module": "hero", "field": "title", "html": "<h2>Pre-register</h2>"}]
        }
        plan = render_plan.build_plan(brief)
        self.assertEqual([], plan["copy"]["texts"][0]["pages"])
        self.assertIn(
            "The title text has no hero block to go on; it isn't placed.", plan["warnings"]
        )

    def test_a_hero_image_goes_on_a_template_page_hero(self) -> None:
        structure = {
            "_id": "landing-1",
            "layouts": ["layout-1"],
            # The template's shared header sits at site level, next to the layout.
            "blocks": [{"_id": "layout-1"}, {"_id": "layout-header"}],
            "pages": [
                {
                    "_id": "p1",
                    "path": "/",
                    "blocks": [
                        {"_id": "tpl-lead", "module": "lead", "values": {}},
                        {"_id": "tpl-store", "module": "newStore", "values": {}},
                    ],
                }
            ],
        }
        plan = render_plan.build_plan(self.brief, structure, base_dir=self.root)
        image = plan["images"][0]
        self.assertEqual({"/": "lead"}, image["page_modules"])
        self.assertEqual(["tpl-lead"], image["existing_block_ids"])


class ApplyImagesRunTests(unittest.TestCase):
    """The images phase of apply_style.py, against a fake CLI."""

    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        (self.root / "hero.png").write_bytes(b"hero-art")
        (self.root / "icon.png").write_bytes(b"icon-art")
        self.brief = brief_with_palette(None)
        self.brief["brand"] = {
            "images": [
                {"file": "hero.png", "module": "leadGameSales", "slot": "background"},
                {"file": "icon.png", "module": "footer", "slot": "logo"},
                {"file": "hero.png", "module": "newStore", "slot": "background"},
            ]
        }
        transparent = {"enable": True, "type": "color", "color": "rgba(0, 0, 0, 0)"}
        self.site = {
            "_id": "landing-1",
            "pages": [
                {
                    "_id": "page-1",
                    "path": "/",
                    "blocks": [
                        {"_id": "hero", "module": "leadGameSales",
                         "values": {"background": dict(transparent)}},
                        {"_id": "store", "module": "newStore",
                         "values": {"background": {**transparent, "img": ""}}},
                        {"_id": "footer", "module": "footer",
                         "values": {"logo": {"img": ""}, "background": dict(transparent)}},
                    ],
                }
            ],
        }
        self.assets: list[str] = []
        self.calls: list[tuple[str, ...]] = []
        self.approve(None)
        self.report = {
            "operation_succeeded": True,
            "approved_confirmation_id": self.approved["confirmation_id"],
            "slug": self.brief["site"]["slug"],
            "landing_id": "landing-1",
            "created_blocks": {"/": ["hero", "store", "footer"]},
        }

    def approve(self, structure: dict | None) -> None:
        self.approved = render_plan.build_plan(self.brief, structure, base_dir=self.root)
        (self.root / "approved-plan.json").write_text(
            json.dumps(self.approved), encoding="utf-8"
        )
        (self.root / "brief.json").write_text(json.dumps(self.brief), encoding="utf-8")

    def cli(self, *args: str) -> dict:
        self.calls.append(args)
        if args[1] == "get-localization":
            return {"ok": True, "data": {}}
        if args[1] == "upload-asset":
            url = f"https://cdn.example/{Path(args[args.index('--file') + 1]).name}"
            self.assets.append(url)
            return {"ok": True, "data": {"url": url}}
        if args[1] != "update-block":
            raise AssertionError(f"unexpected command {args}")
        blocks = {b["_id"]: b for p in self.site["pages"] for b in p["blocks"]}
        for change in json.loads(args[args.index("--data") + 1]).values():
            for patch in change["patches"]:
                node = blocks[change["id"]]
                for key in patch["path"][:-1]:
                    node = node[key]
                node[patch["path"][-1]] = patch["value"]
        return {"ok": True, "data": {}}

    def run_style(self) -> tuple[int, dict | None, str]:
        (self.root / "report.json").write_text(json.dumps(self.report), encoding="utf-8")
        (self.root / "assets.json").write_text(
            json.dumps({"ok": True, "data": [{"url": url} for url in self.assets]}),
            encoding="utf-8",
        )
        (self.root / "localization.json").write_text(
            json.dumps({"ok": True, "data": {}}), encoding="utf-8"
        )
        argv = [
            "apply_style.py",
            str(self.root / "brief.json"),
            "--approved-plan",
            str(self.root / "approved-plan.json"),
            "--run-report",
            str(self.root / "report.json"),
            "--backup-dir",
            str(self.root),
        ]
        stdout, stderr = io.StringIO(), io.StringIO()
        with (
            mock.patch.object(sys, "argv", argv),
            mock.patch.object(apply_style, "run_preflight"),
            mock.patch.object(apply_style, "check_cli_context"),
            mock.patch.object(apply_style, "verified_backup", return_value=True),
            mock.patch.object(
                apply_style, "backup_structure", return_value=copy.deepcopy(self.site)
            ),
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

    def commands(self, name: str) -> list[tuple[str, ...]]:
        return [call for call in self.calls if call[1] == name]

    def block(self, block_id: str) -> dict:
        return next(b for b in self.site["pages"][0]["blocks"] if b["_id"] == block_id)

    def test_uploads_each_file_once_and_sets_every_slot(self) -> None:
        code, report, stderr = self.run_style()
        self.assertEqual(0, code, stderr)
        self.assertEqual(2, len(self.commands("upload-asset")))
        self.assertEqual(1, len(self.commands("update-block")))
        hero = "https://cdn.example/hero.png"
        self.assertEqual(hero, self.block("hero")["values"]["background"]["img"])
        self.assertEqual(hero, self.block("store")["values"]["background"]["img"])
        self.assertEqual(
            "https://cdn.example/icon.png", self.block("footer")["values"]["logo"]["img"]
        )
        self.assertEqual({"set"}, {entry["status"] for entry in report["images"]})
        cache = json.loads((self.root / "asset-cache.json").read_text(encoding="utf-8"))
        self.assertEqual("landing-1", cache["landing_id"])
        self.assertEqual(2, len(cache["uploads"]))

    def test_a_rerun_reuses_the_uploads_and_writes_nothing(self) -> None:
        self.assertEqual(0, self.run_style()[0])
        self.calls.clear()
        code, report, stderr = self.run_style()
        self.assertEqual(0, code, stderr)
        self.assertEqual([], self.commands("upload-asset"))
        self.assertEqual([], self.commands("update-block"))
        self.assertEqual({"unchanged"}, {entry["status"] for entry in report["images"]})

    def test_a_cached_upload_missing_from_the_site_is_uploaded_again(self) -> None:
        self.assertEqual(0, self.run_style()[0])
        self.assets.clear()
        self.calls.clear()
        self.assertEqual(0, self.run_style()[0])
        self.assertEqual(2, len(self.commands("upload-asset")))

    def test_an_existing_block_needs_the_plan_to_list_it(self) -> None:
        self.report["created_blocks"] = {"/": ["store", "footer"]}
        code, report, stderr = self.run_style()
        self.assertEqual(0, code, stderr)
        self.assertNotIn("img", self.block("hero")["values"]["background"])
        self.assertTrue(
            any("existed before this assembly" in item for item in report["needs_human"])
        )

        self.approve(self.site)
        self.report["approved_confirmation_id"] = self.approved["confirmation_id"]
        self.report["created_blocks"] = {}
        code, report, stderr = self.run_style()
        self.assertEqual(0, code, stderr)
        self.assertEqual(
            "https://cdn.example/hero.png", self.block("hero")["values"]["background"]["img"]
        )

    def test_a_file_changed_after_the_yes_stops_before_any_command(self) -> None:
        (self.root / "hero.png").write_bytes(b"other-art")
        code, _, stderr = self.run_style()
        self.assertEqual(1, code)
        self.assertIn("hero.png changed after the plan was approved", stderr)
        self.assertEqual([], self.calls)

    def test_an_opaque_color_over_the_image_goes_to_the_handoff(self) -> None:
        self.block("hero")["values"]["background"]["color"] = "#000000"
        code, report, stderr = self.run_style()
        self.assertEqual(0, code, stderr)
        self.assertTrue(
            any("background color #000000 is opaque" in item for item in report["needs_human"])
        )

    def test_a_block_without_the_slot_is_skipped_with_the_reason(self) -> None:
        del self.block("footer")["values"]["logo"]
        code, report, stderr = self.run_style()
        self.assertEqual(0, code, stderr)
        footer = next(entry for entry in report["images"] if entry["block_id"] == "footer")
        self.assertEqual("skipped", footer["status"])
        self.assertEqual("it has no logo to put an image in", footer["reason"])
        uploaded = [call[call.index("--file") + 1] for call in self.commands("upload-asset")]
        self.assertEqual(["hero.png"], [Path(path).name for path in uploaded])

    def test_a_federated_block_is_skipped(self) -> None:
        self.block("store")["values"]["blockId"] = "newStore"
        code, report, stderr = self.run_style()
        self.assertEqual(0, code, stderr)
        store = next(entry for entry in report["images"] if entry["block_id"] == "store")
        self.assertEqual("it is a federated block, whose wrapper isn't patched", store["reason"])


FAQ = [
    {"question": "<h4>Is it safe?</h4>", "answer": "<p>Yes, payments go through Xsolla.</p>"},
    {"question": "<h4>Where are my items?</h4>", "answer": "<p>In your game inbox.</p>"},
]


class CopyBriefTests(unittest.TestCase):
    def brief(self, copy_value: object = None, faq: object = None) -> dict:
        brief = brief_with_palette(None)
        brief["content"] = {}
        if copy_value is not None:
            brief["content"]["copy"] = copy_value
        if faq is not None:
            brief["content"]["faq"] = faq
        return brief

    def test_html_copy_and_faq_are_valid(self) -> None:
        copy_value = [
            {"module": "leadGameSales", "field": "title", "html": "<h1>Hold the line</h1>"},
            {"module": "newStore", "field": "title", "html": "<h2>Shop</h2>", "page": "/"},
        ]
        self.assertEqual([], validate_shop_brief.validate(self.brief(copy_value, FAQ)))

    def test_bad_copy_and_faq_are_refused(self) -> None:
        good = {"module": "leadGameSales", "field": "title", "html": "<h1>Hi</h1>"}
        cases = {
            "content.copy must be a non-empty list": self.brief([]),
            "content.copy[0].field must be one of": self.brief([{**good, "field": "legal"}]),
            "content.copy[0].html must be HTML": self.brief([{**good, "html": "Hi"}]),
            "must not contain <script>, <img>": self.brief(
                [{**good, "html": "<h1><img src=x></h1>"}]
            ),
            "content.copy[0].module must be a verified block module": self.brief(
                [{**good, "module": "carousel"}]
            ),
            "content.faq[0].question must be an <h4>": self.brief(
                None, [{"question": "<p>Q</p>", "answer": "<p>A</p>"}]
            ),
            "content.faq[0] must have question and answer only": self.brief(
                None, [{"question": "<h4>Q</h4>"}]
            ),
        }
        for message, brief in cases.items():
            with self.subTest(message):
                errors = validate_shop_brief.validate(brief)
                self.assertTrue(any(message in error for error in errors), errors)


class SeoBriefTests(unittest.TestCase):
    def brief(self, seo: object) -> dict:
        brief = brief_with_palette(None)
        brief["content"] = {"seo": seo}
        return brief

    def test_plain_text_seo_with_a_local_image_is_valid(self) -> None:
        seo = [{"page": "/", "title": "Space Raiders Shop", "description": "Gems.",
                "image": "art/share.png"}]
        self.assertEqual([], validate_shop_brief.validate(self.brief(seo)))

    def test_bad_seo_is_refused(self) -> None:
        good = {"page": "/", "title": "Shop"}
        cases = {
            "content.seo must be a non-empty list": [],
            "content.seo[0].title is plain text, not HTML": [{**good, "title": "<b>Shop</b>"}],
            "content.seo[0].title must be at most 70 characters": [{**good, "title": "x" * 71}],
            "content.seo[0].description must be at most 200 characters": [
                {**good, "description": "x" * 201}
            ],
            "content.seo[0].image must be a local file; download it first": [
                {**good, "image": "https://example.com/a.png"}
            ],
            "content.seo[1].page / is listed twice": [good, good],
            "content.seo[0] needs a title, a description or an image": [{"page": "/"}],
            "content.seo[0].page must be a page path": [{**good, "page": "shop"}],
        }
        for message, seo in cases.items():
            with self.subTest(message):
                errors = validate_shop_brief.validate(self.brief(seo))
                self.assertTrue(any(message in error for error in errors), errors)


class OverlapAndHtmlTests(unittest.TestCase):
    def test_overlapping_entries_are_refused(self) -> None:
        brief = brief_with_palette(None)
        title = {"module": "leadGameSales", "field": "title", "html": "<h1>A</h1>"}
        brief["content"] = {"copy": [title, {**title, "html": "<h1>B</h1>", "page": "/"}]}
        hero = {"file": "a.png", "module": "leadGameSales", "slot": "background"}
        brief["brand"] = {"images": [hero, {**hero, "file": "b.png"}]}
        errors = validate_shop_brief.validate(brief)
        self.assertTrue(any(e.startswith("content.copy[1] and content.copy[0]") for e in errors))
        self.assertTrue(any(e.startswith("brand.images[1] and brand.images[0]") for e in errors))

    def test_entries_on_different_pages_are_fine(self) -> None:
        brief = brief_with_palette(None)
        title = {"module": "leadGameSales", "field": "title", "html": "<h1>A</h1>"}
        brief["content"] = {
            "copy": [{**title, "page": "/"}, {**title, "html": "<h1>B</h1>", "page": "/events"}]
        }
        self.assertEqual([], validate_shop_brief.validate(brief))

    def test_code_in_copy_is_refused(self) -> None:
        for html_text in (
            '<p><iframe src="x"></iframe></p>',
            '<p onclick="steal()">Hi</p>',
            '<a href="javascript:alert(1)">Go</a>',
            "<style>p{}</style><p>Hi</p>",
        ):
            with self.subTest(html_text):
                self.assertTrue(validate_shop_brief.html_errors(html_text, "x"))
        self.assertEqual([], validate_shop_brief.html_errors('<p><a href="https://x">Hi</a></p>', "x"))


class CopyPlanTests(unittest.TestCase):
    def test_the_plan_binds_seo_to_planned_pages_and_its_image(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "share.png").write_bytes(b"share-art")
            brief = brief_with_palette(None)
            brief["content"] = {
                "seo": [
                    {"page": "/", "title": "Shop", "image": "share.png"},
                    {"page": "/news", "title": "News"},
                ]
            }
            plan = render_plan.build_plan(brief, base_dir=root)
        seo = plan["copy"]["seo"]
        self.assertEqual(["/"], [item["page"] for item in seo])
        self.assertEqual(hashlib.sha256(b"share-art").hexdigest(), seo[0]["sha256"])
        self.assertIn("SEO for /news has no planned page; it isn't written.", plan["warnings"])

    def test_the_plan_places_the_copy_and_the_faq(self) -> None:
        brief = brief_with_palette(None)
        brief["content"] = {
            "copy": [
                {"module": "leadGameSales", "field": "title", "html": "<h1>Hold</h1>"},
                {"module": "gallery", "field": "title", "html": "<h2>Look</h2>"},
            ],
            "faq": FAQ,
        }
        plan = render_plan.build_plan(brief)
        self.assertEqual("en-US", plan["copy"]["locale"])
        self.assertEqual(["/"], plan["copy"]["texts"][0]["pages"])
        self.assertEqual([], plan["copy"]["texts"][1]["pages"])
        self.assertIn(
            "The title text has no gallery block to go on; it isn't placed.", plan["warnings"]
        )
        self.assertEqual(FAQ, plan["copy"]["faq"]["items"])
        self.assertIn("faq", plan["pages"][0]["blocks"])
        self.assertEqual(["theme", "images", "copy"], plan["style_phases"])

    def test_without_an_faq_the_plan_has_none(self) -> None:
        self.assertIsNone(render_plan.build_plan(brief_with_palette(None))["copy"]["faq"])


class ApplyCopyRunTests(unittest.TestCase):
    """The copy phase of apply_style.py, against a fake CLI with a text store."""

    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.brief = brief_with_palette(None)
        self.brief["content"] = {
            "copy": [
                {"module": "leadGameSales", "field": "title", "html": "<h1>Hold the line</h1>"},
                {"module": "leadGameSales", "field": "subtitle", "html": "<p>Now on web</p>"},
                {"module": "newStore", "field": "title", "html": "<h2>Shop</h2>"},
            ],
            "faq": FAQ,
        }

        def question(n: int) -> dict:
            return {"_id": f"q{n}", "type": "questionV2", "enable": True,
                    "question": {"id": f"L:q{n}"}, "answer": {"id": f"L:a{n}"}}

        self.site = {
            "_id": "landing-1",
            "pages": [
                {
                    "_id": "page-1",
                    "path": "/",
                    "seo": {
                        "title": {"id": "L:st"},
                        "description": {"id": "L:sd"},
                        "ogImage": {"id": "L:si"},
                    },
                    "blocks": [
                        {"_id": "hero", "module": "leadGameSales",
                         "values": {"title": {"id": "L:t1"}, "subtitle": {"id": "L:t2"}}},
                        {"_id": "store", "module": "newStore",
                         "values": {"title": {"id": "L:t3"}}},
                        {"_id": "faq", "module": "faq", "values": {"title": {"id": "L:t4"}},
                         "components": [question(1), question(2), question(3)]},
                    ],
                }
            ],
        }

        def text(value: str) -> dict:
            return {"description": "blocks.demo", "translations": {"en-US": value}}

        self.text = {
            "pages": {
                "page-1": {
                    "texts": {
                        "L:t1": text("<h1>Demo hero</h1>"),
                        "L:t2": text("<p>Demo subtitle</p>"),
                        "L:t3": text("<h2>Demo store</h2>"),
                        "L:t4": text("<h2>FAQ</h2>"),
                        "L:st": text("Demo store"),
                        "L:sd": text("Demo description"),
                        "L:si": text("https://cdn.example/demo-share.png"),
                        **{f"L:q{n}": text(f"<h4>Demo Q{n}</h4>") for n in (1, 2, 3)},
                        **{f"L:a{n}": text(f"<p>Demo A{n}</p>") for n in (1, 2, 3)},
                    }
                }
            },
            "common": {"L:c1": text("<h2>Demo store</h2>")},
        }
        self.calls: list[tuple[str, ...]] = []
        self.assets: list[str] = []
        self.touch_other_text = False
        self.regenerate_ids = False
        self.ignore_removals = False
        self.drop_removed_strings = False
        self.approve(None)
        self.report = {
            "operation_succeeded": True,
            "approved_confirmation_id": self.approved["confirmation_id"],
            "slug": self.brief["site"]["slug"],
            "landing_id": "landing-1",
            "created_blocks": {"/": ["hero", "store", "faq"]},
        }

    def approve(self, structure: dict | None) -> None:
        self.approved = render_plan.build_plan(self.brief, structure, base_dir=self.root)
        (self.root / "approved-plan.json").write_text(
            json.dumps(self.approved), encoding="utf-8"
        )
        (self.root / "brief.json").write_text(json.dumps(self.brief), encoding="utf-8")

    def cli(self, *args: str) -> dict:
        self.calls.append(args)
        if args[1] == "get-localization":
            return {"ok": True, "data": copy.deepcopy(self.text)}
        if args[1] == "upload-asset":
            url = f"https://cdn.example/{Path(args[args.index('--file') + 1]).name}"
            self.assets.append(url)
            return {"ok": True, "data": {"url": url}}
        payload = json.loads(args[args.index("--data") + 1])
        if args[1] == "update-many-localization":
            for scope, ids in payload["perScopeValues"].items():
                texts = (
                    self.text["common"]
                    if scope == "common"
                    else self.text["pages"].setdefault(scope, {"texts": {}})["texts"]
                )
                for lid, value in ids.items():
                    entry = texts.setdefault(lid, {"translations": {}})
                    entry["description"] = value["description"]
                    entry["translations"][payload["locale"]] = value["translation"]
            if self.touch_other_text:
                self.text["pages"]["page-1"]["texts"]["L:t4"]["translations"]["en-US"] = ""
            return {"ok": True, "data": {}}
        if args[1] != "update-block":
            raise AssertionError(f"unexpected command {args}")
        blocks = {b["_id"]: b for p in self.site["pages"] for b in p["blocks"]}
        for change in payload.values():
            for patch in change["patches"]:
                node = blocks[change["id"]]
                for key in patch["path"][:-1]:
                    node = node[key]
                last = patch["path"][-1]
                if patch["op"] == "remove" and self.ignore_removals:
                    continue
                if patch["op"] == "remove":
                    removed = node.pop(last)
                    if self.drop_removed_strings:
                        texts = self.text["pages"]["page-1"]["texts"]
                        for key in ("question", "answer"):
                            texts.pop(removed[key]["id"], None)
                elif patch["op"] == "add" and isinstance(node, list):
                    node.insert(last, patch["value"])
                else:
                    node[last] = patch["value"]
        return {"ok": True, "data": {}}

    def run_style(self) -> tuple[int, dict | None, str]:
        (self.root / "report.json").write_text(json.dumps(self.report), encoding="utf-8")
        (self.root / "assets.json").write_text(
            json.dumps({"ok": True, "data": [{"url": url} for url in self.assets]}),
            encoding="utf-8",
        )
        (self.root / "localization.json").write_text(
            json.dumps({"ok": True, "data": self.text}), encoding="utf-8"
        )
        argv = [
            "apply_style.py",
            str(self.root / "brief.json"),
            "--approved-plan",
            str(self.root / "approved-plan.json"),
            "--run-report",
            str(self.root / "report.json"),
            "--backup-dir",
            str(self.root),
        ]
        stdout, stderr = io.StringIO(), io.StringIO()
        with (
            mock.patch.object(sys, "argv", argv),
            mock.patch.object(apply_style, "run_preflight"),
            mock.patch.object(apply_style, "check_cli_context"),
            mock.patch.object(apply_style, "verified_backup", return_value=True),
            mock.patch.object(
                apply_style, "backup_structure", return_value=copy.deepcopy(self.site)
            ),
            mock.patch.object(apply_style, "structure", side_effect=self.read_structure),
            mock.patch.object(apply_style, "run_json", side_effect=self.cli),
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            code = apply_style.main()
        report = json.loads(stdout.getvalue()) if stdout.getvalue().strip() else None
        return code, report, stderr.getvalue()

    def read_structure(self, slug: str) -> dict:
        site = copy.deepcopy(self.site)
        if self.regenerate_ids:
            # Like the real server: component `_id`s differ on every read.
            for page in site["pages"]:
                for block in page["blocks"]:
                    for component in block.get("components") or []:
                        component["_id"] = uuid.uuid4().hex
        return site

    def with_seo(self, **item: str) -> None:
        (self.root / "share.png").write_bytes(b"share-art")
        self.brief["content"]["seo"] = [{"page": "/", **item}]
        self.approve(None)
        self.report["approved_confirmation_id"] = self.approved["confirmation_id"]

    def test_writes_the_page_seo_and_its_share_image(self) -> None:
        self.with_seo(
            title="Space Raiders Shop",
            description="Gems and packs for Space Raiders.",
            image="share.png",
        )
        code, report, stderr = self.run_style()
        self.assertEqual(0, code, stderr)
        self.assertEqual("Space Raiders Shop", self.shown("page-1", "L:st"))
        self.assertEqual("Gems and packs for Space Raiders.", self.shown("page-1", "L:sd"))
        self.assertEqual("https://cdn.example/share.png", self.shown("page-1", "L:si"))
        self.assertEqual(1, self.names().count("upload-asset"))
        self.assertEqual(1, self.names().count("update-many-localization"))
        seo = [entry for entry in report["copy"] if entry.get("field", "").startswith("seo.")]
        self.assertEqual({"set"}, {entry["status"] for entry in seo})

        self.calls.clear()
        code, report, stderr = self.run_style()
        self.assertEqual(0, code, stderr)
        self.assertEqual([], self.names())

    def test_a_page_without_seo_fields_is_skipped_with_the_reason(self) -> None:
        del self.site["pages"][0]["seo"]
        self.with_seo(title="Space Raiders Shop")
        code, report, stderr = self.run_style()
        self.assertEqual(0, code, stderr)
        title = next(entry for entry in report["copy"] if entry.get("field") == "seo.title")
        self.assertEqual("the page has no SEO title text", title["reason"])
        self.assertTrue(any("editor's page settings" in item for item in report["needs_human"]))

    def test_a_share_image_changed_after_the_yes_stops_before_any_command(self) -> None:
        self.with_seo(image="share.png")
        (self.root / "share.png").write_bytes(b"other-art")
        code, _, stderr = self.run_style()
        self.assertEqual(1, code)
        self.assertIn("share.png changed after the plan was approved", stderr)
        self.assertEqual([], self.calls)

    def test_a_site_wide_string_is_left_alone(self) -> None:
        self.site["pages"][0]["blocks"][1]["values"]["title"]["id"] = "L:c1"
        code, report, stderr = self.run_style()
        self.assertEqual(0, code, stderr)
        self.assertEqual("<h2>Demo store</h2>", self.shown("common", "L:c1"))
        store = next(entry for entry in report["copy"] if entry.get("block_id") == "store")
        self.assertEqual("skipped", store["status"])
        self.assertIn("site-wide strings", store["reason"])

    def test_text_shared_with_an_unlisted_block_is_left_alone(self) -> None:
        self.site["pages"].append(
            {"_id": "page-2", "path": "/other", "blocks": [
                {"_id": "old-store", "module": "newStore",
                 "values": {"title": {"id": "L:t3"}}}]}
        )
        self.text["pages"]["page-2"] = {"texts": {}}
        code, report, stderr = self.run_style()
        self.assertEqual(0, code, stderr)
        self.assertEqual("<h2>Demo store</h2>", self.shown("page-1", "L:t3"))
        store = next(entry for entry in report["copy"] if entry.get("block_id") == "store")
        self.assertEqual("its text is shared with old-store", store["reason"])

    def test_two_items_for_the_same_text_stop_before_any_text(self) -> None:
        self.brief["content"]["copy"].append(
            {"module": "leadGameSales", "field": "title", "html": "<h1>Other</h1>", "page": "/"}
        )
        self.approve(None)
        self.report["approved_confirmation_id"] = self.approved["confirmation_id"]
        with mock.patch.object(apply_style, "validate", return_value=[]):
            code, _, stderr = self.run_style()
        self.assertEqual(1, code)
        self.assertIn("two approved items write different text to L:t1", stderr)
        self.assertNotIn("update-many-localization", self.names())

    def test_faq_items_are_checked_by_text_ids_not_component_ids(self) -> None:
        self.regenerate_ids = True
        self.brief["content"]["faq"] = FAQ + [{"question": "<h4>Q3</h4>", "answer": "<p>A3</p>"},
                                              {"question": "<h4>Q4</h4>", "answer": "<p>A4</p>"}]
        self.approve(None)
        self.report["approved_confirmation_id"] = self.approved["confirmation_id"]
        code, report, stderr = self.run_style()
        self.assertEqual(0, code, stderr)

    def test_a_removal_the_server_ignores_is_caught(self) -> None:
        self.ignore_removals = True
        code, _, stderr = self.run_style()
        self.assertEqual(1, code)
        self.assertIn("the copy did not persist: FAQ items of faq", stderr)

    def test_strings_of_removed_items_may_go_with_them(self) -> None:
        self.drop_removed_strings = True
        code, report, stderr = self.run_style()
        self.assertEqual(0, code, stderr)

    def shown(self, scope: str, lid: str) -> str:
        texts = self.text["common"] if scope == "common" else self.text["pages"][scope]["texts"]
        return texts[lid]["translations"]["en-US"]

    def names(self) -> list[str]:
        return [call[1] for call in self.calls if call[1] != "get-localization"]

    def faq_block(self) -> dict:
        return self.site["pages"][0]["blocks"][2]

    def test_writes_the_copy_and_trims_the_faq_to_the_approved_items(self) -> None:
        code, report, stderr = self.run_style()
        self.assertEqual(0, code, stderr)
        self.assertEqual("<h1>Hold the line</h1>", self.shown("page-1", "L:t1"))
        self.assertEqual("<p>Now on web</p>", self.shown("page-1", "L:t2"))
        self.assertEqual("<h2>Shop</h2>", self.shown("page-1", "L:t3"))
        self.assertEqual("<h2>Demo store</h2>", self.shown("common", "L:c1"))
        self.assertEqual("blocks.demo", self.text["pages"]["page-1"]["texts"]["L:t1"]["description"])
        self.assertEqual("<h4>Where are my items?</h4>", self.shown("page-1", "L:q2"))
        self.assertEqual(["q1", "q2"], [c["_id"] for c in self.faq_block()["components"]])
        self.assertEqual("<h2>FAQ</h2>", self.shown("page-1", "L:t4"))
        self.assertEqual(["update-many-localization", "update-block"], self.names())
        faq = next(entry for entry in report["copy"] if entry["module"] == "faq")
        self.assertEqual((0, 1), (faq["added"], faq["removed"]))

    def test_adds_faq_items_after_their_text_is_written(self) -> None:
        self.brief["content"]["faq"] = FAQ + [
            {"question": "<h4>Q3</h4>", "answer": "<p>A3</p>"},
            {"question": "<h4>Q4</h4>", "answer": "<p>A4</p>"},
        ]
        self.approve(None)
        self.report["approved_confirmation_id"] = self.approved["confirmation_id"]
        code, report, stderr = self.run_style()
        self.assertEqual(0, code, stderr)
        self.assertEqual(["update-many-localization", "update-block"], self.names())
        components = self.faq_block()["components"]
        self.assertEqual(4, len(components))
        added = components[3]
        self.assertEqual("questionV2", added["type"])
        self.assertEqual("<h4>Q4</h4>", self.shown("page-1", added["question"]["id"]))
        self.assertEqual("<p>A4</p>", self.shown("page-1", added["answer"]["id"]))

    def test_a_rerun_writes_nothing(self) -> None:
        self.brief["content"]["faq"] = FAQ + [
            {"question": "<h4>Q3</h4>", "answer": "<p>A3</p>"},
            {"question": "<h4>Q4</h4>", "answer": "<p>A4</p>"},
        ]
        self.approve(None)
        self.report["approved_confirmation_id"] = self.approved["confirmation_id"]
        self.assertEqual(0, self.run_style()[0])
        self.calls.clear()
        code, report, stderr = self.run_style()
        self.assertEqual(0, code, stderr)
        self.assertEqual([], self.names())
        self.assertEqual({"unchanged"}, {entry["status"] for entry in report["copy"]})

    def test_an_existing_block_the_plan_didnt_list_keeps_its_text(self) -> None:
        self.report["created_blocks"] = {"/": ["store", "faq"]}
        code, report, stderr = self.run_style()
        self.assertEqual(0, code, stderr)
        self.assertEqual("<h1>Demo hero</h1>", self.shown("page-1", "L:t1"))
        self.assertTrue(any("its text wasn't changed" in item for item in report["needs_human"]))

    def test_a_missing_text_field_is_skipped_with_the_reason(self) -> None:
        del self.site["pages"][0]["blocks"][0]["values"]["subtitle"]
        code, report, stderr = self.run_style()
        self.assertEqual(0, code, stderr)
        subtitle = next(entry for entry in report["copy"] if entry["field"] == "subtitle")
        self.assertEqual("it has no subtitle text", subtitle["reason"])

    def test_stops_when_text_outside_the_plan_changes(self) -> None:
        self.touch_other_text = True
        code, _, stderr = self.run_style()
        self.assertEqual(1, code)
        self.assertIn("text outside the plan changed: L:t4", stderr)


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
