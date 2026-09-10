"""Enumeration, routing, and the site-level checks."""

import unittest

from . import context  # noqa: F401
from .fixtures.load import find_block, known_good
from xsolla_shop_validation.site_walk import enumerate_blocks, route_block, walk_site


class TestRouting(unittest.TestCase):
    def test_the_literal_federated_module_plus_the_ai_prefix(self):
        self.assertEqual(route_block({"module": "federated", "values": {"blockId": "sb-offer-chain"}}), "federated")
        self.assertEqual(route_block({"module": "federated", "values": {"blockId": "ai_1_2_3"}}), "custom")

    def test_native_layout_and_unknown(self):
        self.assertEqual(route_block({"module": "faq"}), "native")
        self.assertEqual(route_block({"module": "common-layout"}), "layout")
        self.assertEqual(route_block({"module": "block-shipped-next-quarter"}), "unknown")

    def test_a_federated_block_with_no_values_still_routes_as_federated(self):
        self.assertEqual(route_block({"module": "federated"}), "federated")


class TestEnumeration(unittest.TestCase):
    def test_both_passes_run_and_off_page_blocks_are_included(self):
        structure, _, off_page = known_good()
        records, dangling = enumerate_blocks(structure, off_page)
        self.assertEqual(len(records), 8)
        self.assertEqual(dangling, [])
        sources = {r["id"]: r["source"] for r in records}
        self.assertEqual(sources["b-common-layout"], "off-page")
        self.assertEqual(sources["b-faq"], "page")

    def test_skipping_the_second_pass_loses_the_off_page_block(self):
        structure, _, _ = known_good()
        records, dangling = enumerate_blocks(structure, {})
        self.assertEqual(len(records), 7)
        self.assertEqual(dangling, ["b-common-layout"])

    def test_a_fresh_landing_with_no_pages_enumerates_nothing_and_does_not_raise(self):
        records, dangling = enumerate_blocks({"_id": "L", "pages": [], "blocks": []}, {})
        self.assertEqual((records, dangling), ([], []))

    def test_the_record_carries_what_the_report_needs(self):
        structure, _, off_page = known_good()
        records, _ = enumerate_blocks(structure, off_page)
        record = next(r for r in records if r["id"] == "b-faq")
        self.assertEqual(record["module"], "faq")
        self.assertEqual(record["blockVersion"], 2)
        self.assertEqual(record["page_id"], "p-home")


class TestKnownGoodSite(unittest.TestCase):
    """A known-good site must report zero errors.  Any finding here is a false
    positive, and every false positive is a bug in the rules, not in the site."""

    def setUp(self):
        structure, localization, off_page = known_good()
        self.report = walk_site(structure, localization, off_page)

    def test_the_walk_is_clean(self):
        self.assertEqual(self.report["errors"], [], self.report["errors"])
        self.assertTrue(self.report["ok"])
        self.assertEqual(self.report["verdict"], "clean")

    def test_it_found_every_block_and_family(self):
        scope = self.report["scope"]
        self.assertEqual(scope["blocks"], 8)
        self.assertEqual(scope["off_page_blocks"], 1)
        self.assertEqual(scope["families"], {"native": 4, "layout": 2, "federated": 1, "custom": 1})

    def test_it_resolved_localized_ids_by_both_routes(self):
        self.assertEqual(self.report["scope"]["localized_ids_checked"], 12)

    def test_it_declares_its_blind_spots(self):
        notes = " ".join(self.report["unverified"])
        self.assertIn("no defaultData", notes)
        self.assertIn("catalog", notes)
        self.assertIn("I: image id", notes)


class TestSiteLevelChecks(unittest.TestCase):
    def test_a_missing_navigation_makes_reachability_unverified_not_a_finding(self):
        structure, localization, off_page = known_good()
        structure.pop("navigation")
        structure["pages"].append({"_id": "p-two", "path": "/two", "blocks": []})
        report = walk_site(structure, localization, off_page)
        self.assertEqual(report["errors"], [])
        self.assertTrue(any("reachability" in n for n in report["unverified"]))

    def test_an_unreachable_second_page_is_a_finding(self):
        structure, localization, off_page = known_good()
        structure["pages"].append({"_id": "p-two", "path": "/two", "blocks": []})
        report = walk_site(structure, localization, off_page)
        self.assertEqual([f["path"] for f in report["errors"]], ["pages.p-two"])

    def test_an_unknown_module_is_named_as_unchecked_rather_than_failed(self):
        structure, localization, off_page = known_good()
        find_block(structure, "b-faq")["module"] = "block-shipped-next-quarter"
        report = walk_site(structure, localization, off_page)
        self.assertEqual(report["errors"], [])
        self.assertTrue(any("no schema available" in n for n in report["unverified"]))


if __name__ == "__main__":
    unittest.main()
