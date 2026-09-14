"""Tests for the three extractors, against real store responses."""

from __future__ import annotations

import unittest

from xsolla_listing_import import (coverage, extract, extract_appstore,
                                   extract_play, extract_steam, fields,
                                   listing_schema, sanitize)

from .fixtures.load import appstore_lookup, play_page, steam_appdetails

STEAM_URL = "https://store.steampowered.com/app/812140/"
APPLE_URL = "https://apps.apple.com/us/app/clash-of-clans/id529479190"
PLAY_URL = "https://play.google.com/store/apps/details?id=com.supercell.clashofclans"


class TestSteam(unittest.TestCase):

    def setUp(self):
        self.doc = extract_steam.to_listing(steam_appdetails(), STEAM_URL)

    def test_it_validates(self):
        self.assertEqual(listing_schema.validate(self.doc), [])

    def test_rights_are_not_self_certified(self):
        """Only the caller has asked the partner, so only the caller may set it."""
        self.assertFalse(self.doc["rights_confirmed"])

    def test_extraction_clears_the_eighty_percent_target(self):
        self.assertGreaterEqual(coverage.measure(self.doc)["extraction"]["pct"], 80.0)

    def test_core_fields(self):
        values = self.doc["fields"]
        self.assertEqual(values["title"], "Assassin's Creed® Odyssey")
        self.assertIn("Ubisoft", values["developer"])
        self.assertEqual(values["genres"], ["Action", "Adventure", "RPG"])
        self.assertEqual(values["platforms"], ["windows"])
        self.assertEqual(len(values["screenshots"]), 8)

    def test_age_rating_comes_from_the_ratings_block(self):
        self.assertEqual(self.doc["fields"]["age_rating"], "PEGI 18")

    def test_tags_are_declared_not_found_not_omitted(self):
        """They render on the page and are absent from this response."""
        self.assertIn("tags", self.doc["not_found"])
        self.assertNotIn("tags", self.doc["fields"])

    def test_editions_become_iap_items_with_prices(self):
        items = self.doc["fields"]["iap_items"]
        self.assertEqual(len(items), 4)
        self.assertTrue(all("price" in i for i in items))
        self.assertEqual(items[0]["price"]["currency"], "EUR")

    def test_long_description_is_html_not_bbcode(self):
        self.assertIn("long_description_html", self.doc["fields"])
        self.assertIn("<h2", self.doc["fields"]["long_description_html"])

    def test_unwrap_accepts_either_envelope(self):
        raw = steam_appdetails()
        inner = raw["812140"]["data"]
        self.assertEqual(extract_steam.unwrap(raw)["name"], inner["name"])
        self.assertEqual(extract_steam.unwrap(inner)["name"], inner["name"])

    def test_an_unsuccessful_response_raises(self):
        with self.assertRaises(ValueError):
            extract_steam.to_listing({"999": {"success": False}}, STEAM_URL)


class TestAppStore(unittest.TestCase):

    def setUp(self):
        self.doc = extract_appstore.to_listing(appstore_lookup(), APPLE_URL)

    def test_it_validates(self):
        self.assertEqual(listing_schema.validate(self.doc), [])

    def test_core_fields(self):
        values = self.doc["fields"]
        self.assertEqual(values["title"], "Clash of Clans")
        self.assertEqual(values["developer"], "Supercell Oy")
        self.assertEqual(values["age_rating"], "9+")
        self.assertIn("ios", values["platforms"])

    def test_the_api_publishes_no_iap_list(self):
        """Verified: no key in the response contains purchase/iap/inApp."""
        self.assertNotIn("iap_items", self.doc["fields"])
        self.assertIn("iap_items", self.doc["not_found"])

    def test_scraped_iap_items_are_accepted_and_flagged_as_partial(self):
        items = [{"name": "Gold Pass", "price": {"amount": 4.99, "currency": "USD"}}]
        doc = extract_appstore.to_listing(appstore_lookup(), APPLE_URL,
                                          iap_items=items)
        self.assertEqual(doc["fields"]["iap_items"], items)
        self.assertNotIn("iap_items", doc["not_found"])
        self.assertIn("truncated", doc["notes"])

    def test_description_is_plain_text_so_it_gets_escaped_not_sanitised(self):
        self.assertIn("long_description_text", self.doc["fields"])

    def test_key_art_is_excluded_from_the_denominator_not_counted_as_a_miss(self):
        self.assertEqual(fields.availability("key_art", fields.APP_STORE),
                         fields.NEVER)
        self.assertNotIn("key_art", coverage.measure(self.doc)["missing"])

    def test_thumbnail_urls_are_rewritten_to_full_size(self):
        self.assertTrue(all("2048x2048bb" in u
                            for u in self.doc["fields"]["screenshots"]))

    def test_no_results_raises(self):
        with self.assertRaises(ValueError):
            extract_appstore.to_listing({"resultCount": 0, "results": []}, APPLE_URL)


class TestGooglePlay(unittest.TestCase):

    def setUp(self):
        self.doc = extract_play.to_listing(play_page(), PLAY_URL)

    def test_it_validates(self):
        self.assertEqual(listing_schema.validate(self.doc), [])

    def test_the_page_html_alone_is_enough_no_browser_needed(self):
        values = self.doc["fields"]
        self.assertEqual(values["title"], "Clash of Clans")
        self.assertEqual(values["developer"], "Supercell")
        self.assertEqual(values["age_rating"], "Everyone 10+")
        self.assertEqual(values["platforms"], ["android"])
        self.assertTrue(values["screenshots"])

    def test_the_title_suffix_is_stripped(self):
        self.assertNotIn("Apps on Google Play", self.doc["fields"]["title"])

    def test_long_description_is_the_description_subtree_only(self):
        """The regression: void elements made the capture run to end-of-document,
        taking 271 KB instead of the description."""
        body = self.doc["fields"]["long_description_html"]
        self.assertLess(len(body), 20000)
        self.assertIn("Join millions of players", body)
        clean, _dropped = sanitize.to_html(body)
        self.assertGreater(len(clean), 500)

    def test_no_named_iap_items_only_a_range(self):
        self.assertNotIn("iap_items", self.doc["fields"])
        self.assertIn("iap_items", self.doc["not_found"])
        self.assertIn("range", self.doc["notes"])

    def test_the_price_range_is_carried_in_notes_not_invented_as_items(self):
        self.assertIn("$", self.doc["notes"])

    def test_key_art_is_not_found_because_the_page_has_no_feature_graphic(self):
        self.assertIn("key_art", self.doc["not_found"])

    def test_a_non_play_page_raises(self):
        with self.assertRaises(ValueError):
            extract_play.to_listing("<html>nothing</html>", PLAY_URL)


class TestDispatch(unittest.TestCase):

    def test_source_detection(self):
        self.assertEqual(extract.detect_source(STEAM_URL), fields.STEAM)
        self.assertEqual(extract.detect_source(APPLE_URL), fields.APP_STORE)
        self.assertEqual(extract.detect_source(PLAY_URL), fields.GOOGLE_PLAY)
        self.assertIsNone(extract.detect_source("https://example.test/x"))

    def test_fetch_hint_builds_the_api_url(self):
        _s, url, kind = extract.fetch_hint(STEAM_URL)
        self.assertIn("appids=812140", url)
        self.assertEqual(kind, "json")

    def test_fetch_hint_carries_the_apple_storefront_country(self):
        _s, url, _k = extract.fetch_hint(
            "https://apps.apple.com/gb/app/clash-of-clans/id529479190")
        self.assertIn("country=gb", url)

    def test_play_is_fetched_as_html(self):
        _s, url, kind = extract.fetch_hint(PLAY_URL)
        self.assertEqual((url, kind), (PLAY_URL, "html"))

    def test_unsupported_host_raises(self):
        with self.assertRaises(ValueError):
            extract.fetch_hint("https://example.test/x")

    def test_dispatch_routes_each_source(self):
        import json
        steam = extract.to_listing(json.dumps(steam_appdetails()), STEAM_URL)
        self.assertEqual(steam["source"], fields.STEAM)
        play = extract.to_listing(play_page(), PLAY_URL)
        self.assertEqual(play["source"], fields.GOOGLE_PLAY)

    def test_play_given_a_dict_raises_rather_than_guessing(self):
        with self.assertRaises(ValueError):
            extract.to_listing({"not": "html"}, PLAY_URL)


class TestAllThreeSourcesMeetTheTarget(unittest.TestCase):
    """The DoD metric, asserted rather than claimed in a doc."""

    def test_extraction_is_at_least_eighty_percent_everywhere(self):
        import json
        docs = [
            extract_steam.to_listing(steam_appdetails(), STEAM_URL),
            extract_appstore.to_listing(appstore_lookup(), APPLE_URL,
                                        iap_items=[{"name": "Gold Pass"}]),
            extract_play.to_listing(play_page(), PLAY_URL),
        ]
        del json
        for doc in docs:
            pct = coverage.measure(doc)["extraction"]["pct"]
            self.assertGreaterEqual(pct, 80.0, doc["source"])

    def test_every_extracted_field_has_a_destination(self):
        doc = extract_steam.to_listing(steam_appdetails(), STEAM_URL)
        report = coverage.measure(doc)
        self.assertEqual(report["mapping"]["pct"], 100.0)
        self.assertEqual(report["manual_follow_up"], [])


if __name__ == "__main__":
    unittest.main()
