"""Tests for the field-to-block table and its confidence labels."""

from __future__ import annotations

import unittest

from xsolla_listing_import import fields, mapping


class TestTable(unittest.TestCase):

    def test_every_dod_field_has_a_row(self):
        for name in fields.dod_fields():
            self.assertIsNotNone(mapping.target_for(name), name)

    def test_confirmed_rows_are_the_ones_exercised_live(self):
        confirmed = {t.field for t in mapping.TARGETS
                     if t.confidence == mapping.CONFIRMED}
        self.assertEqual(confirmed, {"key_art", "screenshots"})

    def test_unmapped_fields_are_the_block_set_gap(self):
        self.assertEqual(set(mapping.unmapped_fields()),
                         {"genres", "tags", "age_rating", "iap_items"})

    def test_a_writable_row_names_a_module_and_a_path(self):
        for target in mapping.TARGETS:
            if target.action in (mapping.LOCALIZATION, mapping.PATCH, mapping.ASSET):
                self.assertIsNotNone(target.module, target.field)
                self.assertTrue(target.path, target.field)

    def test_unwritable_rows_carry_a_note_saying_why(self):
        for target in mapping.TARGETS:
            if target.action in (mapping.MANUAL, mapping.EXTERNAL):
                self.assertTrue(target.note.strip(), target.field)

    def test_as_dict_is_json_safe(self):
        row = mapping.target_for("key_art").as_dict()
        self.assertEqual(row["path"], ["values", "background", "img"])
        self.assertEqual(row["confidence"], mapping.CONFIRMED)


class TestSourceUrlAgreement(unittest.TestCase):

    def test_steam_host(self):
        self.assertTrue(mapping.source_matches_url(
            "steam", "https://store.steampowered.com/app/812140/"))

    def test_play_host(self):
        self.assertTrue(mapping.source_matches_url(
            "google_play", "https://play.google.com/store/apps/details?id=x"))

    def test_app_store_host(self):
        self.assertTrue(mapping.source_matches_url(
            "app_store", "https://apps.apple.com/us/app/x/id1"))

    def test_disagreement_is_false(self):
        self.assertFalse(mapping.source_matches_url(
            "steam", "https://play.google.com/store/apps/details?id=x"))

    def test_unknown_host_is_none_not_false(self):
        """"Cannot say" and "disagrees" are different answers."""
        self.assertIsNone(mapping.source_matches_url("steam", "https://example.test/x"))
        self.assertIsNone(mapping.source_matches_url("steam", ""))


if __name__ == "__main__":
    unittest.main()
