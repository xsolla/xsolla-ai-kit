"""The federated structural walk, and the four ways it must not fire."""

import unittest

from . import context  # noqa: F401
from xsolla_shop_validation.errors import MISSING
from xsolla_shop_validation.federated import (
    is_custom_block_id,
    resolve_federated_localized_id,
    validate_federated,
)


class TestWalk(unittest.TestCase):
    def test_a_changed_type_is_caught_at_its_own_path(self):
        result = validate_federated({"steps": {"title": 5}}, {"steps": {"title": "text"}})
        self.assertFalse(result["ok"])
        self.assertEqual(result["errors"][0]["path"], "steps.title")
        self.assertEqual(result["errors"][0]["expected"], "string")
        self.assertEqual(result["errors"][0]["got"], "number")

    def test_a_mismatch_does_not_cascade_into_children(self):
        result = validate_federated(
            {"modal": "just a string"}, {"modal": {"title": "t", "image": "I:abc"}}
        )
        self.assertEqual(len(result["errors"]), 1)
        self.assertEqual(result["errors"][0]["path"], "modal")

    def test_arrays_use_item_zero_as_the_shape_and_any_length_is_fine(self):
        result = validate_federated(
            {"rewards": [{"n": 1}, {"n": 2}, {"n": 3}]}, {"rewards": [{"n": 0}]}
        )
        self.assertTrue(result["ok"])

    def test_array_items_are_reported_with_their_index(self):
        result = validate_federated({"rewards": [{"n": 1}, {"n": "two"}]}, {"rewards": [{"n": 0}]})
        self.assertEqual(result["errors"][0]["path"], "rewards.1.n")

    def test_an_empty_defaults_array_gives_no_reference_shape(self):
        self.assertTrue(validate_federated({"rewards": [{"n": "x"}]}, {"rewards": []})["ok"])

    def test_absent_internal_block_values_passes_unwalked(self):
        result = validate_federated(MISSING, {"a": 1})
        self.assertTrue(result["ok"])
        self.assertFalse(result["walked"])

    def test_a_custom_block_with_no_default_data_is_skipped_not_failed(self):
        result = validate_federated({}, MISSING)
        self.assertTrue(result["ok"])
        self.assertFalse(result["walked"])

    def test_a_null_default_skips_the_subtree(self):
        self.assertTrue(validate_federated({"a": {"deep": [1, 2]}}, {"a": None})["ok"])

    def test_a_field_the_defaults_never_mentioned_is_allowed(self):
        self.assertTrue(validate_federated({"brandNew": {"x": 1}}, {})["ok"])


class TestOverrideWhitelists(unittest.TestCase):
    def test_an_image_id_default_accepts_any_user_string(self):
        self.assertTrue(validate_federated({"img": "I:zzz1"}, {"img": "I:fxaahvtgju5"})["ok"])
        self.assertTrue(validate_federated({"img": "anything"}, {"img": "I:fxaahvtgju5"})["ok"])

    def test_a_localized_id_default_accepts_any_user_string(self):
        for default in ("L:cedykaynjx", "L:02241EE4-2e77-4fd4-a482-0eca3dbf5e68"):
            self.assertTrue(validate_federated({"t": "L:other"}, {"t": default})["ok"], default)

    def test_a_seven_prefixed_value_needs_no_whitelist_and_is_not_a_finding(self):
        self.assertTrue(
            validate_federated({"buttonVariant": "7:aaa"}, {"buttonVariant": "7:zpdpy7epv7h"})["ok"]
        )

    def test_a_number_against_an_image_id_default_is_still_a_finding(self):
        self.assertFalse(validate_federated({"img": 5}, {"img": "I:abc"})["ok"])


class TestSizingUnion(unittest.TestCase):
    def test_a_number_where_the_default_is_auto_is_a_union_not_an_error(self):
        self.assertTrue(validate_federated({"blockHeight": 166}, {"blockHeight": "auto"})["ok"])

    def test_the_reverse_direction_too(self):
        self.assertTrue(validate_federated({"width": "cover"}, {"width": 320})["ok"])

    def test_every_documented_keyword_is_covered(self):
        for keyword in (
            "auto",
            "none",
            "normal",
            "inherit",
            "initial",
            "unset",
            "cover",
            "contain",
            "fit-content",
            "max-content",
            "min-content",
        ):
            self.assertTrue(validate_federated({"x": 12}, {"x": keyword})["ok"], keyword)

    def test_a_non_keyword_string_default_still_type_checks(self):
        self.assertFalse(validate_federated({"align": 12}, {"align": "left"})["ok"])


class TestRouting(unittest.TestCase):
    def test_the_ai_prefix_is_the_whole_test(self):
        self.assertTrue(is_custom_block_id("ai_936601_314771_abc"))
        self.assertFalse(is_custom_block_id("sb-offer-chain"))
        self.assertFalse(is_custom_block_id(None))


class TestTwoHopResolution(unittest.TestCase):
    def test_a_short_id_resolves_through_the_blocks_own_resources(self):
        resources = {"localizedValues": {"L:short": {"texts": {"id": "L:uuid-1"}}}}
        self.assertEqual(resolve_federated_localized_id("L:short", resources), "L:uuid-1")

    def test_a_short_id_absent_from_resources_does_not_resolve(self):
        self.assertIsNone(resolve_federated_localized_id("L:missing", {"localizedValues": {}}))

    def test_malformed_resources_do_not_raise(self):
        for resources in (None, {}, {"localizedValues": None}, {"localizedValues": {"L:s": 1}}):
            self.assertIsNone(resolve_federated_localized_id("L:s", resources))


if __name__ == "__main__":
    unittest.main()
