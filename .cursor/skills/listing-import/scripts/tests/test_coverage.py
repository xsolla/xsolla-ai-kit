"""Tests for the three-way coverage metric."""

from __future__ import annotations

import unittest

from xsolla_listing_import import coverage, fields, mapping

from .fixtures.load import steam_listing


class TestRealFixture(unittest.TestCase):

    def setUp(self):
        self.report = coverage.measure(steam_listing())

    def test_extraction_beats_the_eighty_percent_target(self):
        self.assertGreaterEqual(self.report["extraction"]["pct"], 80.0)

    def test_the_ceiling_is_no_longer_a_ceiling(self):
        """It read 7/11 while only native block fields counted. Every target
        field now has a destination, so mapping loss is structural only."""
        self.assertEqual(self.report["mapping_ceiling"]["pct"], 100.0)
        self.assertEqual(self.report["mapping"]["pct"], 100.0)

    def test_nothing_is_left_for_a_human_to_place(self):
        self.assertEqual(self.report["manual_follow_up"], [])

    def test_delivered_now_tracks_extraction(self):
        self.assertEqual(self.report["delivered"]["filled"],
                         self.report["extraction"]["filled"])

    def test_long_description_form_is_carried_through(self):
        self.assertEqual(self.report["long_description_form"], "html")


class TestPresence(unittest.TestCase):

    def _measure(self, values, source="steam", not_found=None):
        return coverage.measure({"source": source, "fields": values,
                                 "not_found": not_found or []})

    def test_empty_string_is_absent(self):
        self.assertIn("title", self._measure({"title": "   "})["missing"])

    def test_empty_list_is_absent(self):
        self.assertIn("screenshots", self._measure({"screenshots": []})["missing"])

    def test_any_long_description_form_counts(self):
        for key in ("long_description_html", "long_description_bbcode",
                    "long_description_text"):
            report = self._measure({key: "body"})
            self.assertIn("long_description", report["extracted"], key)

    def test_undeclared_missing_separates_from_declared(self):
        report = self._measure({"title": "T"}, not_found=["tags"])
        self.assertIn("tags", report["declared_not_found"])
        self.assertNotIn("tags", report["undeclared_missing"])
        self.assertIn("genres", report["undeclared_missing"])


class TestDenominators(unittest.TestCase):
    """A source is not marked down for a field it never publishes."""

    def test_app_store_excludes_key_art_and_tags(self):
        report = coverage.measure({"source": "app_store", "fields": {}})
        self.assertIn("key_art", report["not_published_by_source"])
        self.assertIn("tags", report["not_published_by_source"])
        self.assertEqual(report["extraction"]["total"],
                         len(fields.expected_fields("app_store")))

    def test_play_denominator_is_smaller_than_steam(self):
        self.assertLess(len(fields.expected_fields("google_play")),
                        len(fields.expected_fields("steam")))

    def test_empty_denominator_reports_none_not_zero(self):
        report = coverage.measure({"source": "unknown-store", "fields": {}})
        self.assertIsNone(report["extraction"]["pct"])

    def test_ceiling_matches_the_mapping_table(self):
        report = coverage.measure({"source": "steam", "fields": {}})
        self.assertEqual(
            report["mapping_ceiling"]["filled"],
            len(fields.dod_fields()) - len(mapping.unmapped_fields()),
        )


if __name__ == "__main__":
    unittest.main()
