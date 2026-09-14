"""Tests for the listing.json contract, including the rights gate."""

from __future__ import annotations

import unittest

from xsolla_listing_import import listing_schema

from .fixtures.load import steam_listing


def paths(errors):
    return [error["path"] for error in errors]


class TestValidDocument(unittest.TestCase):

    def test_the_real_steam_fixture_validates(self):
        self.assertEqual(listing_schema.validate(steam_listing()), [])

    def test_minimal_document(self):
        self.assertEqual(listing_schema.validate({
            "source": "steam", "source_url": "https://store.steampowered.com/app/1/",
            "rights_confirmed": True, "fields": {"title": "T"},
        }), [])


class TestRequiredKeys(unittest.TestCase):

    def test_missing_keys_are_all_reported(self):
        reported = paths(listing_schema.validate({}))
        for key in ("source", "source_url", "rights_confirmed", "fields"):
            self.assertIn(key, reported)

    def test_unknown_top_level_key(self):
        errors = listing_schema.validate({
            "source": "steam", "source_url": "u", "rights_confirmed": True,
            "fields": {}, "surprise": 1,
        })
        self.assertIn("surprise", paths(errors))

    def test_not_an_object(self):
        self.assertEqual(paths(listing_schema.validate([])), ["(root)"])


class TestRightsFlagShape(unittest.TestCase):
    """The schema checks the flag's type. Whether it is *true* is enforced by
    `plan.build`, which is what actually stands in front of a write -- see
    `test_plan.TestBlockers`."""

    def test_false_is_well_formed_here(self):
        self.assertEqual(listing_schema.validate({
            "source": "steam", "source_url": "u", "rights_confirmed": False,
            "fields": {},
        }), [])

    def test_a_non_boolean_is_a_shape_error(self):
        for value in ("yes", 1, "true", None):
            errors = listing_schema.validate({
                "source": "steam", "source_url": "u", "rights_confirmed": value,
                "fields": {},
            })
            self.assertIn("rights_confirmed", paths(errors), value)


class TestFieldTypes(unittest.TestCase):

    def _validate_fields(self, values):
        return listing_schema.validate({
            "source": "steam", "source_url": "u", "rights_confirmed": True,
            "fields": values,
        })

    def test_unknown_source(self):
        errors = listing_schema.validate({
            "source": "nintendo", "source_url": "u", "rights_confirmed": True,
            "fields": {},
        })
        self.assertIn("source", paths(errors))

    def test_text_field_given_a_number(self):
        self.assertIn("fields.title", paths(self._validate_fields({"title": 7})))

    def test_list_field_given_a_string(self):
        self.assertIn("fields.genres", paths(self._validate_fields({"genres": "RPG"})))

    def test_unknown_field(self):
        self.assertIn("fields.nope", paths(self._validate_fields({"nope": "x"})))

    def test_empty_entry_in_a_list(self):
        errors = self._validate_fields({"screenshots": ["ok", "  "]})
        self.assertIn("fields.screenshots.1", paths(errors))

    def test_two_long_description_forms_conflict(self):
        errors = self._validate_fields({
            "long_description_html": "<p>a</p>", "long_description_bbcode": "[p]a[/p]",
        })
        self.assertIn("fields", paths(errors))


class TestIapItems(unittest.TestCase):

    def _items(self, items):
        return paths(listing_schema.validate({
            "source": "steam", "source_url": "u", "rights_confirmed": True,
            "fields": {"iap_items": items},
        }))

    def test_name_is_required(self):
        self.assertIn("fields.iap_items.0.name", self._items([{"price": None}]))

    def test_price_is_optional(self):
        self.assertEqual(self._items([{"name": "Gold Edition"}]), [])

    def test_price_amount_must_be_a_number(self):
        reported = self._items([{"name": "x", "price": {"amount": "9.99",
                                                        "currency": "EUR"}}])
        self.assertIn("fields.iap_items.0.price.amount", reported)

    def test_currency_must_be_three_letters(self):
        reported = self._items([{"name": "x", "price": {"amount": 9.99,
                                                        "currency": "EU"}}])
        self.assertIn("fields.iap_items.0.price.currency", reported)

    def test_real_fixture_editions_pass(self):
        document = steam_listing()
        self.assertGreater(len(document["fields"]["iap_items"]), 0)
        self.assertEqual(listing_schema.validate(document), [])


class TestNotFound(unittest.TestCase):
    """``not_found`` separates "looked and it is not there" from "did not look"."""

    def test_contradicting_fields_is_an_error(self):
        errors = listing_schema.validate({
            "source": "steam", "source_url": "u", "rights_confirmed": True,
            "fields": {"title": "T"}, "not_found": ["title"],
        })
        self.assertIn("not_found.0", paths(errors))

    def test_must_be_a_list(self):
        errors = listing_schema.validate({
            "source": "steam", "source_url": "u", "rights_confirmed": True,
            "fields": {}, "not_found": "tags",
        })
        self.assertIn("not_found", paths(errors))


class TestLongDescription(unittest.TestCase):

    def test_form_is_reported(self):
        _text, form = listing_schema.long_description(steam_listing())
        self.assertEqual(form, "html")

    def test_bbcode_form(self):
        text, form = listing_schema.long_description(
            {"fields": {"long_description_bbcode": "[h2]x[/h2]"}})
        self.assertEqual((text, form), ("[h2]x[/h2]", "bbcode"))

    def test_absent(self):
        self.assertEqual(listing_schema.long_description({"fields": {}}), (None, None))


if __name__ == "__main__":
    unittest.main()
