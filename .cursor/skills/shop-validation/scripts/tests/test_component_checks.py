"""Editor-side content checks, and the context they refuse to guess at."""

import unittest

from . import context  # noqa: F401
from xsolla_shop_validation.component_checks import (
    ValidationContext,
    validate_action,
    validate_block_components,
    validate_footer_v2,
    validate_gallery_v2,
)
from xsolla_shop_validation.url_rules import (
    validate_lightbox_url,
    validate_page_path,
    validate_site_name,
    validate_url_with_relative,
)

CTX = ValidationContext(site={"_id": "s1", "pages": [{"_id": "p1"}]}, skus=["sku-a"], bundles=["b-1"])


class TestActions(unittest.TestCase):
    def test_a_buy_action_pointing_at_an_unknown_sku(self):
        unverified = []
        errors = validate_action({"action": "buy", "sku": "nope"}, ["a"], CTX, unverified)
        self.assertEqual(errors[0]["expected"], "a SKU in the catalog")

    def test_a_buy_action_is_unverified_when_no_catalog_was_supplied(self):
        unverified = []
        errors = validate_action(
            {"action": "buy", "sku": "sku-a"}, ["a"], ValidationContext(), unverified
        )
        self.assertEqual(errors, [])
        self.assertEqual(len(unverified), 1)

    def test_a_lightbox_action_needs_a_player_url(self):
        errors = validate_action({"action": "lightbox", "url": "https://example.com/x"}, ["a"], CTX, [])
        self.assertTrue(errors)
        self.assertEqual(validate_action({"action": "lightbox", "url": "https://vimeo.com/1"}, ["a"], CTX, []), [])

    def test_a_page_action_must_point_at_a_page_that_exists(self):
        errors = validate_action({"action": "page", "landingId": "s1", "pageId": "p9"}, ["a"], CTX, [])
        self.assertEqual(errors[0]["path"], "a.pageId")

    def test_a_cross_site_page_link_is_not_validated(self):
        unverified = []
        errors = validate_action(
            {"action": "page", "landingId": "other", "pageId": "p9"}, ["a"], CTX, unverified
        )
        self.assertEqual(errors, [])
        self.assertEqual(len(unverified), 1)

    def test_scroll_cloud_gaming_and_subscription_need_their_target(self):
        for action, path in (
            ({"action": "scroll", "targetId": ""}, "a.targetId"),
            ({"action": "cloud-gaming", "gameId": None}, "a.gameId"),
            ({"action": "subscription", "subscriptionId": ""}, "a.subscriptionId"),
        ):
            self.assertEqual(validate_action(action, ["a"], CTX, [])[0]["path"], path)

    def test_an_unknown_action_kind_passes(self):
        self.assertEqual(validate_action({"action": "promocode-thing"}, ["a"], CTX, []), [])


class TestComponentWalk(unittest.TestCase):
    def test_a_disabled_component_is_not_checked(self):
        components = [{"type": "twitchEmbed", "enable": False, "values": {}}]
        self.assertEqual(validate_block_components(components, context=CTX), [])

    def test_nested_components_are_walked_with_an_indexed_path(self):
        components = [
            {
                "type": "group",
                "enable": True,
                "components": [{"type": "twitchEmbed", "enable": True, "values": {}}],
            }
        ]
        errors = validate_block_components(components, context=CTX)
        self.assertEqual(errors[0]["path"], "components.0.components.0.values.link")

    def test_a_store_section_without_a_type_is_caught(self):
        components = [{"type": "storeSection", "enable": True, "storeItemsGroup": "g"}]
        self.assertEqual(validate_block_components(components, context=CTX)[0]["path"], "components.0.storeItemsType")

    def test_a_game_keys_store_section_needs_no_group(self):
        components = [{"type": "storeSection", "enable": True, "storeItemsType": "gk", "storeItemsGroup": ""}]
        self.assertEqual(validate_block_components(components, context=CTX), [])

    def test_the_error_group_sentinel_is_a_finding(self):
        components = [
            {"type": "storeSection", "enable": True, "storeItemsType": "vi", "storeItemsGroup": "__error__"}
        ]
        self.assertTrue(validate_block_components(components, context=CTX))

    def test_a_legacy_buy_button_checks_its_sku(self):
        components = [
            {
                "type": "customButton",
                "enable": True,
                "subtype": "buy",
                "value": {"buy": {"type": "key", "id": "sku-a"}},
            }
        ]
        self.assertEqual(validate_block_components(components, context=CTX), [])

    def test_a_components_value_that_is_not_a_list_is_ignored(self):
        self.assertEqual(validate_block_components({"0": {}}, context=CTX), [])


class TestFooterAndGallery(unittest.TestCase):
    def test_an_enabled_social_item_with_an_empty_url(self):
        block = {"components": [{"type": "social", "enable": True, "value": [{"enable": True, "url": ""}]}]}
        self.assertEqual(validate_footer_v2(block)[0]["path"], "components.0.value.0.url")

    def test_a_disabled_social_item_with_an_empty_url_is_fine(self):
        block = {"components": [{"type": "social", "enable": True, "value": [{"enable": False, "url": ""}]}]}
        self.assertEqual(validate_footer_v2(block), [])

    def test_a_gallery_slide_missing_its_declared_media(self):
        self.assertEqual(
            validate_gallery_v2({"values": {"slides": [{"image": {"type": "image"}}]}})[0]["path"],
            "values.slides.0.image.img",
        )

    def test_an_unsupported_slide_media_type(self):
        errors = validate_gallery_v2({"values": {"slides": [{"image": {"type": "gif"}}]}})
        self.assertEqual(errors[0]["expected"], 'one of: "image", "video"')

    def test_a_complete_slide_passes(self):
        block = {"values": {"slides": [{"image": {"type": "video", "video": "https://x/y.mp4"}}]}}
        self.assertEqual(validate_gallery_v2(block), [])


class TestUrlRules(unittest.TestCase):
    def test_lightbox_accepts_the_four_providers(self):
        for url in (
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://vimeo.com/123456",
            "https://store.steampowered.com/1234/movie",
            "https://www.epicgames.com/store/p/game",
        ):
            self.assertTrue(validate_lightbox_url(url), url)

    def test_relative_and_scheme_urls_are_accepted(self):
        for url in ("/pricing", "#anchor", "mailto:a@b.com", "tel:+1", "https://example.com/x"):
            self.assertTrue(validate_url_with_relative(url), url)

    def test_site_names_and_page_paths_have_their_own_rules(self):
        self.assertTrue(validate_site_name("my-shop-1"))
        self.assertFalse(validate_site_name("My_Shop"))
        self.assertTrue(validate_page_path("/"))
        self.assertTrue(validate_page_path("/store/sale"))
        self.assertFalse(validate_page_path("store"))


if __name__ == "__main__":
    unittest.main()
