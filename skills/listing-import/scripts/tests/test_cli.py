"""Tests for the command line: exit status and the JSON report contract."""

from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout

import listing_import

from .fixtures.load import steam_listing, steam_structure

CLEAN = listing_import.EXIT_CLEAN
ERRORS = listing_import.EXIT_ERRORS
USAGE = listing_import.EXIT_USAGE


class CliCase(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def write(self, name, document):
        path = os.path.join(self.tmp, name)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(document, handle)
        return path

    def run_cli(self, argv):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            status = listing_import.main(argv)
        return status, buffer.getvalue()


class TestExitStatus(CliCase):

    def test_valid_listing_exits_clean(self):
        path = self.write("l.json", steam_listing())
        status, out = self.run_cli(["validate", "--listing", path])
        self.assertEqual(status, CLEAN)
        self.assertIn("valid", out)

    def test_invalid_listing_exits_one(self):
        path = self.write("l.json", {"source": "nintendo"})
        status, _out = self.run_cli(["validate", "--listing", path])
        self.assertEqual(status, ERRORS)

    def test_no_subcommand_exits_two(self):
        status, out = self.run_cli([])
        self.assertEqual(status, USAGE)
        self.assertIn("usage", out)

    def test_a_missing_file_exits_two_not_a_traceback(self):
        status, _out = self.run_cli(
            ["validate", "--listing", os.path.join(self.tmp, "absent.json")])
        self.assertEqual(status, USAGE)

    def test_malformed_json_exits_two(self):
        path = os.path.join(self.tmp, "bad.json")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("{not json")
        status, _out = self.run_cli(["validate", "--listing", path])
        self.assertEqual(status, USAGE)

    def test_blocked_preview_exits_one(self):
        document = steam_listing()
        document["rights_confirmed"] = False
        listing = self.write("l.json", document)
        structure = self.write("s.json", steam_structure())
        status, out = self.run_cli(
            ["preview", "--listing", listing, "--structure", structure])
        self.assertEqual(status, ERRORS)
        self.assertIn("BLOCKED", out)


class TestJsonContract(CliCase):

    def test_validate_json(self):
        path = self.write("l.json", steam_listing())
        _status, out = self.run_cli(["validate", "--listing", path, "--json"])
        report = json.loads(out)
        self.assertTrue(report["ok"])
        self.assertEqual(report["errors"], [])

    def test_coverage_json_carries_all_three_ratios(self):
        path = self.write("l.json", steam_listing())
        _status, out = self.run_cli(["coverage", "--listing", path, "--json"])
        report = json.loads(out)
        for key in ("extraction", "mapping", "delivered", "mapping_ceiling"):
            self.assertIn("pct", report[key], key)

    def test_plan_json_is_ok_true_with_operations(self):
        listing = self.write("l.json", steam_listing())
        structure = self.write("s.json", steam_structure())
        status, out = self.run_cli(
            ["plan", "--listing", listing, "--structure", structure])
        report = json.loads(out)
        self.assertEqual(status, CLEAN)
        self.assertTrue(report["ok"])
        self.assertEqual(report["blockers"], [])
        self.assertGreater(len(report["plan"]["operations"]), 0)

    def test_plan_reports_schema_errors_as_json_too(self):
        listing = self.write("l.json", {"source": "nintendo"})
        structure = self.write("s.json", steam_structure())
        status, out = self.run_cli(
            ["plan", "--listing", listing, "--structure", structure])
        self.assertEqual(status, ERRORS)
        self.assertFalse(json.loads(out)["ok"])


class TestHumanPreview(CliCase):

    def test_preview_asks_for_confirmation(self):
        listing = self.write("l.json", steam_listing())
        structure = self.write("s.json", steam_structure())
        _status, out = self.run_cli(
            ["preview", "--listing", listing, "--structure", structure])
        self.assertIn("explicit confirmation", out)

    def test_preview_marks_unconfirmed_paths(self):
        listing = self.write("l.json", steam_listing())
        structure = self.write("s.json", steam_structure())
        _status, out = self.run_cli(
            ["preview", "--listing", listing, "--structure", structure])
        self.assertIn("[path unconfirmed]", out)

    def test_preview_renders_a_companion_patch_without_crashing(self):
        """The bool value that crashed the first version of the renderer."""
        listing = self.write("l.json", steam_listing())
        structure = self.write("s.json", steam_structure())
        status, out = self.run_cli(
            ["preview", "--listing", listing, "--structure", structure])
        self.assertEqual(status, CLEAN)
        self.assertIn("background.enable", out)

    def test_invalid_listing_is_refused_before_a_preview_is_built(self):
        listing = self.write("l.json", {"source": "steam", "fields": {"title": 1}})
        structure = self.write("s.json", steam_structure())
        _status, out = self.run_cli(
            ["preview", "--listing", listing, "--structure", structure])
        self.assertIn("not valid", out)


class TestBbcodeCommand(CliCase):

    def test_converts_a_file(self):
        path = os.path.join(self.tmp, "d.txt")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("[h2]Title[/h2]")
        status, out = self.run_cli(["bbcode", "--file", path])
        self.assertEqual(status, CLEAN)
        self.assertIn("<h2>Title</h2>", out)

    def test_json_reports_what_it_dropped(self):
        path = os.path.join(self.tmp, "d.txt")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("a[img]{STEAM_APP_IMAGE}/x.jpg[/img]")
        _status, out = self.run_cli(["bbcode", "--file", path, "--json"])
        self.assertTrue(json.loads(out)["dropped"])


if __name__ == "__main__":
    unittest.main()


class TestFetchExtractCatalogCommands(CliCase):

    STEAM_URL = "https://store.steampowered.com/app/812140/"

    def test_fetch_names_the_api_url(self):
        status, out = self.run_cli(["fetch", "--url", self.STEAM_URL])
        self.assertEqual(status, CLEAN)
        self.assertIn("appids=812140", out)

    def test_fetch_warns_that_apple_needs_the_page_too(self):
        _status, out = self.run_cli([
            "fetch", "--url",
            "https://apps.apple.com/us/app/clash-of-clans/id529479190"])
        self.assertIn("does not publish one", out)

    def test_fetch_on_an_unsupported_host_exits_two(self):
        status, _out = self.run_cli(["fetch", "--url", "https://example.test/x"])
        self.assertEqual(status, USAGE)

    def test_extract_emits_a_valid_listing(self):
        from .fixtures.load import steam_appdetails
        path = self.write("raw.json", steam_appdetails())
        status, out = self.run_cli(["extract", "--input", path,
                                    "--url", self.STEAM_URL])
        self.assertEqual(status, CLEAN)
        document = json.loads(out)
        self.assertEqual(document["source"], "steam")
        self.assertFalse(document["rights_confirmed"])

    def test_extract_output_pipes_straight_into_validate(self):
        from .fixtures.load import steam_appdetails
        raw = self.write("raw.json", steam_appdetails())
        _status, out = self.run_cli(["extract", "--input", raw,
                                     "--url", self.STEAM_URL])
        listing = self.write("l.json", json.loads(out))
        status, _out = self.run_cli(["validate", "--listing", listing])
        self.assertEqual(status, CLEAN)

    def test_catalog_renders_runnable_commands(self):
        document = steam_listing()
        path = self.write("l.json", document)
        status, out = self.run_cli(["catalog", "--listing", path])
        self.assertEqual(status, CLEAN)
        self.assertIn("admin-create-group", out)
        self.assertIn("create-items", out)

    def test_catalog_on_a_listing_with_no_items_says_so(self):
        document = steam_listing()
        document["fields"].pop("iap_items", None)
        path = self.write("l.json", document)
        status, out = self.run_cli(["catalog", "--listing", path])
        self.assertEqual(status, CLEAN)
        self.assertIn("nothing to create", out)

    def test_catalog_json_carries_warnings(self):
        path = self.write("l.json", steam_listing())
        _status, out = self.run_cli(["catalog", "--listing", path, "--json"])
        self.assertTrue(json.loads(out)["warnings"])

    def test_preview_shows_the_catalog_section(self):
        listing = self.write("l.json", steam_listing())
        structure = self.write("s.json", steam_structure())
        _status, out = self.run_cli(["preview", "--listing", listing,
                                     "--structure", structure])
        self.assertIn("Catalog —", out)
        self.assertIn("catalog item(s)", out)
