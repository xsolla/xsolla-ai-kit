"""Tests for the field-to-block table and its confidence labels."""

from __future__ import annotations

import unittest

from xsolla_listing_import import fields, mapping


class TestTable(unittest.TestCase):

    def test_every_dod_field_has_a_row(self):
        for name in fields.dod_fields():
            self.assertIsNotNone(mapping.target_for(name), name)

    def test_confirmed_rows_are_the_ones_exercised_live(self):
        """key_art and screenshots landed on the Steam run; icon on the Play run
        once its path was resolved from the block rather than guessed."""
        confirmed = {t.field for t in mapping.TARGETS
                     if t.confidence == mapping.CONFIRMED}
        self.assertEqual(confirmed, {"key_art", "screenshots", "icon"})

    def test_nothing_is_unmapped_any_more(self):
        """These four used to have nowhere to go, which put a 7/11 ceiling on
        the skill. genres/tags/age_rating are now carried as copy and iap_items
        become catalog entities, so the ceiling is 11/11."""
        self.assertEqual(mapping.unmapped_fields(), ())

    def test_overflow_carries_the_three_fields_with_no_structured_field(self):
        self.assertEqual(set(mapping.overflow_fields()),
                         {"genres", "tags", "age_rating"})

    def test_iap_items_route_to_the_catalog_not_the_landing(self):
        self.assertEqual(mapping.target_for("iap_items").action, mapping.CATALOG)

    def test_every_dod_field_has_a_deliverable_action(self):
        for name in fields.dod_fields():
            self.assertIn(mapping.target_for(name).action, mapping.DELIVERABLE, name)

    def test_a_writable_row_names_a_module_and_a_path(self):
        for target in mapping.TARGETS:
            if target.action in (mapping.LOCALIZATION, mapping.PATCH, mapping.ASSET,
                                 mapping.OVERFLOW):
                self.assertIsNotNone(target.module, target.field)
                self.assertTrue(target.path, target.field)

    def test_every_row_that_is_not_a_plain_patch_explains_itself(self):
        for target in mapping.TARGETS:
            if target.action in (mapping.OVERFLOW, mapping.CATALOG, mapping.MANUAL):
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
