"""The eight per-module checks, with the cases the editor's own tests pin.

Where the upstream suite asserts a specific edge — a string id rejected where a
number is required, an empty chains list passing, a UNIT store item skipped —
the same case is asserted here, so a divergence shows up as a failure rather
than as a difference nobody notices.
"""

import unittest

from . import context  # noqa: F401
from xsolla_shop_validation.module_checks import (
    check_lead_v2,
    check_sidebar,
    is_auth_relevant_for_subscriptions,
    is_daily_reward,
    is_fake_group,
    is_offer_chain,
    validate_daily_reward,
    validate_lead_game_sales,
    validate_new_store_block,
    validate_offer_chain,
    validate_rewards_block,
    validate_subscriptions_block,
)


class TestSubscriptions(unittest.TestCase):
    def test_a_plan_row_with_no_plan_selected(self):
        errors = validate_subscriptions_block(
            {"components": [{"type": "plan", "value": {"planId": ""}}]}
        )
        self.assertEqual(errors[0]["path"], "components.0.value.planId")
        self.assertEqual(errors[0]["message"], "Subscription plan is not selected.")

    def test_the_index_is_in_the_path(self):
        errors = validate_subscriptions_block(
            {
                "components": [
                    {"type": "plan", "value": {"planId": "valid"}},
                    {"type": "plan", "value": {"planId": None}},
                ]
            }
        )
        self.assertEqual([e["path"] for e in errors], ["components.1.value.planId"])

    def test_all_plans_selected_passes(self):
        self.assertEqual(
            validate_subscriptions_block(
                {"components": [{"type": "plan", "value": {"planId": "plan-123"}}]}
            ),
            [],
        )

    def test_a_block_with_no_plan_components_passes(self):
        self.assertEqual(
            validate_subscriptions_block({"components": [{"type": "somethingElse"}]}), []
        )

    def test_auth_relevance(self):
        self.assertFalse(is_auth_relevant_for_subscriptions("login-1", "login"))
        self.assertFalse(is_auth_relevant_for_subscriptions("", "deeplink"))
        self.assertTrue(is_auth_relevant_for_subscriptions("", "login"))
        self.assertTrue(is_auth_relevant_for_subscriptions("", "user-id"))


class TestRewards(unittest.TestCase):
    def test_an_empty_chains_list_passes(self):
        self.assertEqual(validate_rewards_block({"values": {"chains": []}}), [])

    def test_chain_ids_may_be_strings(self):
        self.assertEqual(
            validate_rewards_block(
                {"values": {"chains": [{"rewardChainId": "chain-1"}, {"rewardChainId": "chain-2"}]}}
            ),
            [],
        )

    def test_an_empty_chain_id_is_an_error_at_its_index(self):
        errors = validate_rewards_block(
            {"values": {"chains": [{"rewardChainId": "valid"}, {"rewardChainId": None}]}}
        )
        self.assertEqual(errors[0]["path"], "values.chains.1")
        self.assertEqual(errors[0]["message"], "Invalid reward chain ID")


class TestLeadGameSales(unittest.TestCase):
    def test_disabled_platforms_pass_even_when_empty(self):
        self.assertEqual(
            validate_lead_game_sales({"values": {"platforms": {"enable": False, "items": []}}}), []
        )

    def test_enabled_with_items_passes(self):
        self.assertEqual(
            validate_lead_game_sales(
                {"values": {"platforms": {"enable": True, "items": [{"platform": "steam"}]}}}
            ),
            [],
        )

    def test_enabled_and_empty_is_an_error(self):
        errors = validate_lead_game_sales({"values": {"platforms": {"enable": True, "items": []}}})
        self.assertEqual(errors[0]["path"], "values.platforms")
        self.assertIn("can not be empty when enabled", errors[0]["message"])


class TestNewStore(unittest.TestCase):
    def test_no_store_section_components_passes(self):
        self.assertEqual(validate_new_store_block({"components": [{"type": "other"}]}), [])

    def test_a_unit_item_is_skipped(self):
        self.assertEqual(
            validate_new_store_block(
                {"components": [{"type": "newStoreSection", "section": {"item": {"type": "unit"}}}]}
            ),
            [],
        )

    def test_an_item_with_no_group_key(self):
        errors = validate_new_store_block(
            {"components": [{"type": "newStoreSection", "section": {"item": {"type": "bundle"}}}]}
        )
        self.assertEqual(errors[0]["message"], "Invalid store item structure")

    def test_an_empty_group(self):
        errors = validate_new_store_block(
            {
                "components": [
                    {
                        "type": "newStoreSection",
                        "section": {"item": {"type": "bundle", "group": ""}},
                    }
                ]
            }
        )
        self.assertEqual(errors[0]["message"], "Store group is missing")

    def test_a_demo_group_is_invalid(self):
        errors = validate_new_store_block(
            {
                "components": [
                    {
                        "type": "newStoreSection",
                        "section": {
                            "item": {"type": "virtual_good", "group": "test-group/virtual_good"}
                        },
                    }
                ]
            }
        )
        self.assertEqual(errors[0]["message"], "Store group is invalid")

    def test_a_real_group_passes(self):
        self.assertEqual(
            validate_new_store_block(
                {
                    "components": [
                        {
                            "type": "newStoreSection",
                            "section": {"item": {"type": "bundle", "group": "starter-packs"}},
                        }
                    ]
                }
            ),
            [],
        )

    def test_every_demo_group_is_recognised(self):
        for group in (
            "test-group/bundle",
            "test-group/virtual_currency",
            "test-group/virtual_good",
            "test-group/virtual_good-free",
            "test-group/virtual_good-loyalty",
            "test-group/game_key",
        ):
            self.assertTrue(is_fake_group(group), group)
        self.assertFalse(is_fake_group("starter-packs"))


class TestFederatedRemoteBlocks(unittest.TestCase):
    def block(self, block_id, **internal):
        return {
            "module": "federated",
            "values": {"blockId": block_id, "internalBlockValues": dict(internal)},
        }

    def test_routing_needs_both_module_and_block_id(self):
        self.assertTrue(is_offer_chain(self.block("sb-offer-chain")))
        self.assertTrue(is_daily_reward(self.block("sb-daily-reward")))
        self.assertFalse(is_offer_chain({"values": {"blockId": "sb-offer-chain"}}))
        self.assertFalse(is_offer_chain(self.block("social-quests")))

    def test_a_numeric_id_passes(self):
        self.assertEqual(validate_offer_chain(self.block("sb-offer-chain", offerChainId=99)), [])
        self.assertEqual(validate_daily_reward(self.block("sb-daily-reward", dailyRewardId=3)), [])

    def test_zero_is_a_number(self):
        self.assertEqual(validate_offer_chain(self.block("sb-offer-chain", offerChainId=0)), [])

    def test_a_string_id_is_rejected(self):
        errors = validate_offer_chain(self.block("sb-offer-chain", offerChainId="99"))
        self.assertEqual(errors[0]["path"], "values.internalBlockValues.offerChainId")
        self.assertEqual((errors[0]["expected"], errors[0]["got"]), ("number", "string"))

    def test_null_and_missing_are_rejected(self):
        null_id = self.block("sb-daily-reward", dailyRewardId=None)
        self.assertEqual(validate_daily_reward(null_id)[0]["got"], "null")
        missing = self.block("sb-daily-reward")
        self.assertEqual(validate_daily_reward(missing)[0]["got"], "undefined")

    def test_a_boolean_is_not_a_number(self):
        self.assertTrue(validate_offer_chain(self.block("sb-offer-chain", offerChainId=True)))

    def test_a_non_federated_block_is_not_checked_as_one(self):
        self.assertEqual(validate_offer_chain({"module": "faq", "values": {}})[0]["path"], "module")


class TestLeadV2(unittest.TestCase):
    def test_disabled_platforms_pass(self):
        self.assertEqual(check_lead_v2({"values": {"platforms": {"enable": False}}}), [])

    def test_a_platform_on_its_own_host_passes(self):
        self.assertEqual(
            check_lead_v2(
                {
                    "values": {
                        "platforms": {
                            "enable": True,
                            "items": [
                                {
                                    "enable": True,
                                    "platform": "steam",
                                    "url": "https://store.steampowered.com/app/1",
                                }
                            ],
                        }
                    }
                }
            ),
            [],
        )

    def test_the_untouched_preset_url_is_not_a_configured_link(self):
        errors = check_lead_v2(
            {
                "values": {
                    "platforms": {
                        "enable": True,
                        "items": [
                            {
                                "enable": True,
                                "platform": "steam",
                                "url": "https://store.steampowered.com/",
                            }
                        ],
                    }
                }
            }
        )
        self.assertEqual(errors[0]["path"], "values.platforms.items.0.url")

    def test_a_link_to_the_wrong_storefront(self):
        errors = check_lead_v2(
            {
                "values": {
                    "platforms": {
                        "enable": True,
                        "items": [
                            {
                                "enable": True,
                                "platform": "steam",
                                "url": "https://play.google.com/store/apps",
                            }
                        ],
                    }
                }
            }
        )
        self.assertTrue(errors)

    def test_enabled_with_every_row_disabled_is_an_error(self):
        errors = check_lead_v2(
            {
                "values": {
                    "platforms": {"enable": True, "items": [{"enable": False, "platform": "steam"}]}
                }
            }
        )
        self.assertEqual(errors[0]["path"], "values.platforms.items")


class TestSidebar(unittest.TestCase):
    def test_a_store_button_on_the_wrong_host(self):
        errors = check_sidebar(
            {
                "values": {
                    "platforms": {"enable": True},
                    "storeButtons": {
                        "steam": {
                            "enable": True,
                            "platform": "steam",
                            "link": "https://example.com/x",
                        }
                    },
                }
            }
        )
        self.assertEqual(errors[0]["path"], "values.storeButtons.steam.link")

    def test_a_disabled_store_button_is_not_checked(self):
        self.assertEqual(
            check_sidebar(
                {
                    "values": {
                        "platforms": {"enable": True},
                        "storeButtons": {"steam": {"enable": False, "link": ""}},
                    }
                }
            ),
            [],
        )

    def test_store_buttons_are_only_checked_when_platforms_are_enabled(self):
        self.assertEqual(
            check_sidebar(
                {
                    "values": {
                        "storeButtons": {
                            "steam": {"enable": True, "platform": "steam", "link": ""}
                        }
                    }
                }
            ),
            [],
        )

    def test_an_enabled_social_with_an_empty_link(self):
        errors = check_sidebar(
            {
                "values": {
                    "socials": {
                        "enable": True,
                        "socialNetworks": {"x": {"enable": True, "link": ""}},
                    }
                }
            }
        )
        self.assertEqual(errors[0]["path"], "values.socials.socialNetworks.x.link")

    def test_a_social_with_a_link_passes(self):
        self.assertEqual(
            check_sidebar(
                {
                    "values": {
                        "socials": {
                            "enable": True,
                            "socialNetworks": {"x": {"enable": True, "link": "https://x.com/game"}},
                        }
                    }
                }
            ),
            [],
        )

    def test_an_empty_sidebar_passes(self):
        self.assertEqual(check_sidebar({"values": {}}), [])


class TestWiredIntoTheSiteWalk(unittest.TestCase):
    def test_every_module_visitor_the_editor_registers_is_routed(self):
        from xsolla_shop_validation.site_walk import MODULE_VISITORS

        self.assertEqual(
            sorted(MODULE_VISITORS),
            ["lead", "leadGameSales", "newStore", "rewards", "sidebar", "subscriptions-packs"],
        )


if __name__ == "__main__":
    unittest.main()
