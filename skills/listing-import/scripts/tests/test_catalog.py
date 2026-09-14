"""Tests for turning in-app items into catalog entities."""

from __future__ import annotations

import json
import shlex
import unittest

from xsolla_listing_import import catalog


class TestSkus(unittest.TestCase):

    def test_slug_is_catalog_safe(self):
        self.assertEqual(catalog.slugify("Pocketful of Gems!"), "pocketful_of_gems")
        self.assertEqual(catalog.slugify("1,200 Gems"), "1_200_gems")

    def test_source_prefix(self):
        skus = catalog.build_skus([{"name": "Gems"}], "app_store")
        self.assertTrue(skus[0].startswith("ios_"))

    def test_duplicate_names_are_broken_by_price(self):
        """Real case: the App Store lists Gold Pass at $4.99 and $6.99."""
        items = [{"name": "Gold Pass", "price": {"amount": 4.99, "currency": "USD"}},
                 {"name": "Gold Pass", "price": {"amount": 6.99, "currency": "USD"}}]
        skus = catalog.build_skus(items, "app_store")
        self.assertEqual(len(set(skus)), 2)
        self.assertIn("6_99_usd", skus[1])

    def test_duplicate_names_with_no_price_still_unique(self):
        items = [{"name": "Offer"}, {"name": "Offer"}, {"name": "Offer"}]
        skus = catalog.build_skus(items, "steam")
        self.assertEqual(len(set(skus)), 3)

    def test_skus_are_stable_across_runs(self):
        items = [{"name": "Gold Pass", "price": {"amount": 4.99, "currency": "USD"}}]
        self.assertEqual(catalog.build_skus(items, "app_store"),
                         catalog.build_skus(items, "app_store"))

    def test_an_unnamed_item_still_gets_a_sku(self):
        self.assertTrue(catalog.build_skus([{}], "steam")[0])

    def test_a_long_name_is_truncated_without_a_trailing_underscore(self):
        sku = catalog.build_skus([{"name": "x " * 60}], "steam")[0]
        self.assertFalse(sku.endswith("_"))


class TestOperations(unittest.TestCase):

    def test_everything_is_a_virtual_item(self):
        """Never a currency package or a bundle: no source publishes quantity."""
        ops, _w = catalog.build_operations(
            [{"name": "Pocketful of Gems", "price": {"amount": 0.99,
                                                     "currency": "USD"}}],
            "app_store")
        self.assertEqual(ops[0]["entity"], "virtual_item")
        self.assertNotIn("content", ops[0])

    def test_a_priced_item_is_enabled(self):
        ops, _w = catalog.build_operations(
            [{"name": "Gems", "price": {"amount": 0.99, "currency": "USD"}}], "steam")
        self.assertTrue(ops[0]["is_enabled"])
        self.assertTrue(ops[0]["is_show_in_store"])

    def test_an_unpriced_item_is_created_disabled_and_warned_about(self):
        ops, warnings = catalog.build_operations([{"name": "Mystery Offer"}], "steam")
        self.assertFalse(ops[0]["is_enabled"])
        self.assertEqual(ops[0]["prices"], [])
        self.assertTrue(any("no price" in w for w in warnings))

    def test_every_item_is_flagged_for_review(self):
        ops, _w = catalog.build_operations([{"name": "Gems"}], "steam")
        self.assertTrue(ops[0]["needs_review"])
        self.assertIn("does not publish", ops[0]["review_reason"])

    def test_the_quantity_limitation_is_always_stated(self):
        _ops, warnings = catalog.build_operations([{"name": "Gems"}], "steam")
        self.assertTrue(any("quantity" in w for w in warnings))

    def test_no_items_means_no_operations_and_no_warnings(self):
        self.assertEqual(catalog.build_operations([], "steam"), ([], []))

    def test_price_shape_matches_the_documented_cli_array(self):
        ops, _w = catalog.build_operations(
            [{"name": "Gems", "price": {"amount": 9.99, "currency": "USD"}}], "steam")
        self.assertEqual(ops[0]["prices"], [{"amount": 9.99, "currency": "USD",
                                             "is_default": True,
                                             "is_enabled": True}])


class TestRenderedCommands(unittest.TestCase):

    def _render(self, name):
        ops, _w = catalog.build_operations(
            [{"name": name, "price": {"amount": 59.99, "currency": "EUR"}}], "steam")
        return catalog.render_commands(ops)

    def test_the_group_is_created_before_the_items(self):
        text = self._render("Gems")
        self.assertLess(text.index("admin-create-group"), text.index("create-items"))

    def test_an_apostrophe_in_a_title_does_not_break_the_quoting(self):
        """The first real title through here was Assassin's Creed Odyssey."""
        text = self._render("Assassin's Creed Odyssey - Standard Edition")
        command = text.split("\n\n")[1].replace("\\\n", " ")
        tokens = shlex.split(command)
        payload = json.loads(tokens[tokens.index("--name") + 1])
        self.assertEqual(payload["en"], "Assassin's Creed Odyssey - Standard Edition")

    def test_a_double_quote_in_a_title_survives_too(self):
        text = self._render('The "Best" Game')
        command = text.split("\n\n")[1].replace("\\\n", " ")
        tokens = shlex.split(command)
        payload = json.loads(tokens[tokens.index("--name") + 1])
        self.assertEqual(payload["en"], 'The "Best" Game')

    def test_non_ascii_is_not_escaped_into_mojibake(self):
        text = self._render("Assassin's Creed® Odyssey")
        self.assertIn("®", text)

    def test_an_unpriced_item_renders_without_the_prices_flag(self):
        ops, _w = catalog.build_operations([{"name": "Mystery"}], "steam")
        # Only the item command; the group's own --is-enabled is correct and
        # belongs to a different command.
        item = catalog.render_commands(ops).split("\n\n")[1]
        self.assertNotIn("--prices", item)
        self.assertNotIn("--is-enabled", item)
        self.assertNotIn("--is-show-in-store", item)


if __name__ == "__main__":
    unittest.main()
