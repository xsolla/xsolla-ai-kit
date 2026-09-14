"""Tests for the copy that carries fields with no structured block field."""

from __future__ import annotations

import unittest

from xsolla_listing_import import mapping, overflow


class TestRender(unittest.TestCase):

    def test_all_three_fields_in_one_component(self):
        html, carried = overflow.render({
            "genres": ["Action", "RPG"], "tags": ["Open World"],
            "age_rating": "PEGI 18",
        })
        self.assertEqual(carried, ["genres", "tags", "age_rating"])
        self.assertEqual(html.count("<p>"), 3)

    def test_order_is_fixed_not_dict_order(self):
        html, _ = overflow.render({"age_rating": "9+", "genres": ["RPG"]})
        self.assertLess(html.index("Genres"), html.index("Rating"))

    def test_lists_are_comma_joined(self):
        html, _ = overflow.render({"genres": ["Action", "Adventure", "RPG"]})
        self.assertIn("Action, Adventure, RPG", html)

    def test_absent_and_empty_fields_are_skipped(self):
        html, carried = overflow.render({"genres": [], "tags": None,
                                         "age_rating": "  "})
        self.assertEqual((html, carried), ("", []))

    def test_nothing_to_carry_produces_nothing(self):
        self.assertEqual(overflow.render({}), ("", []))

    def test_values_are_escaped(self):
        """Third-party text, bound for a partner's rendered page."""
        html, _ = overflow.render({"genres": ["<script>alert(1)</script>"]})
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_only_the_fields_the_mapping_routes_here(self):
        self.assertEqual(set(overflow.ORDER), set(mapping.overflow_fields()))


if __name__ == "__main__":
    unittest.main()
