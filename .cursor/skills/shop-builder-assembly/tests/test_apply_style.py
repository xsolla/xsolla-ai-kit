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
        self.assertEqual(["theme", "images"], plan["style_phases"])
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

    def test_a_hero_image_goes_on_a_template_page_hero(self) -> None:
        structure = {
            "_id": "landing-1",
            "layouts": ["layout-1"],
            "blocks": [{"_id": "layout-1"}],
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
