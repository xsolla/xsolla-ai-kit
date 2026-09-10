"""The fourteen documented false-positive traps, one test each.

Every one of these looks like a failure and is a correct pass.  A false finding
is worse than a missed one: it stops a write that would have worked, and it
teaches the user to ignore the gate.  Nine of the fourteen were observed firing
falsely during manual testing before the rules were corrected -- which is why
they are pinned here rather than left to a reviewer's memory.
"""

import unittest

from . import context  # noqa: F401
from .fixtures.load import find_block, known_good
from xsolla_shop_validation.ai_block import collect_violations
from xsolla_shop_validation.errors import MISSING
from xsolla_shop_validation.federated import validate_federated
from xsolla_shop_validation.native import validate_envelope, validate_native
from xsolla_shop_validation.site_walk import walk_site
from xsolla_shop_validation.write_constraints import check_create_version, check_stored_version


class TestTraps(unittest.TestCase):
    def test_01_an_unknown_native_module_passes_structure_unchecked(self):
        result = validate_native("block-shipped-next-quarter", {"values": {"x": 1}})
        self.assertTrue(result["ok"])
        self.assertFalse(result["schema_available"])

    def test_02_a_default_matching_an_image_id_accepts_any_user_string(self):
        self.assertTrue(validate_federated({"img": "I:whatever"}, {"img": "I:fxaahvtgju5"})["ok"])

    def test_03_a_default_matching_a_localized_id_accepts_any_user_string(self):
        self.assertTrue(validate_federated({"t": "L:whatever"}, {"t": "L:cedykaynjx"})["ok"])

    def test_04_defaults_absent_at_a_path_skip_that_subtree(self):
        self.assertTrue(validate_federated({"a": {"b": [1, {"c": "x"}]}}, {})["ok"])

    def test_05_a_federated_short_l_id_is_not_looked_up_in_the_landing_store(self):
        # The 43-false-finding case.  The short ids inside a federated block
        # resolve through the block's own resources map, and the fixture's
        # localization store deliberately contains none of them.
        structure, localization, off_page = known_good()
        short_ids = set()
        values = find_block(structure, "b-fed")["values"]
        for subtree in (values["defaultData"], values["internalBlockValues"]):
            short_ids.update(
                v for v in _strings(subtree) if v.startswith("L:") and len(v) < 20
            )
        self.assertTrue(short_ids)
        store = set(localization["common"]) | set(localization["pages"]["p-home"]["texts"])
        self.assertEqual(short_ids & store, set())
        self.assertEqual(walk_site(structure, localization, off_page)["errors"], [])

    def test_06_no_block_version_key_on_an_unversioned_module(self):
        self.assertEqual(check_create_version("newStore", MISSING), [])
        self.assertEqual(check_stored_version("newStore", None), [])

    def test_07_an_empty_components_array_is_a_block_with_no_sub_parts(self):
        self.assertEqual(validate_envelope({"values": {}, "components": []}), [])

    def test_08_a_seven_prefixed_value_is_a_reference_not_a_malformed_string(self):
        self.assertTrue(
            validate_federated({"buttonVariant": "7:abc"}, {"buttonVariant": "7:zpdpy7epv7h"})["ok"]
        )

    def test_09_a_number_where_the_default_is_a_sizing_keyword(self):
        self.assertTrue(validate_federated({"blockHeight": 166}, {"blockHeight": "auto"})["ok"])

    def test_10_a_federated_block_whose_block_id_starts_ai_is_a_custom_block(self):
        structure, localization, off_page = known_good()
        report = walk_site(structure, localization, off_page)
        self.assertEqual(report["scope"]["families"]["custom"], 1)
        self.assertEqual([f for f in report["errors"] if f.get("block_id") == "b-ai"], [])

    def test_11_a_custom_block_with_no_default_data_is_skipped_not_failed(self):
        result = validate_federated({}, MISSING)
        self.assertTrue(result["ok"])
        self.assertFalse(result["walked"])

    def test_12_a_stored_block_is_never_checked_against_its_module_field_schema(self):
        # The trap with a 100% hit rate if ignored: 36 live blocks, 36 false
        # alarms.  The site walk must not reach for the field schemas at all --
        # a stored localized field is a reference, and the schema describes the
        # descriptor you send instead.
        structure, localization, off_page = known_good()
        stored_faq = find_block(structure, "b-faq")
        self.assertFalse(validate_native("faq", stored_faq)["ok"])
        report = walk_site(structure, localization, off_page)
        self.assertEqual([f for f in report["errors"] if f.get("block_id") == "b-faq"], [])

    def test_13_a_section_absent_from_an_update_is_not_a_missing_field(self):
        self.assertTrue(validate_native("faq", {"components": []}, partial=True)["ok"])
        self.assertEqual(validate_envelope({}), [])

    def test_14_an_options_object_in_a_control_factorys_third_argument(self):
        source = "const n = useControls(number('Count', 0, { min: 0, max: 10, step: 1 }));"
        self.assertEqual(collect_violations(source), [])


def _strings(node):
    if isinstance(node, str):
        return [node]
    if isinstance(node, list):
        return [s for item in node for s in _strings(item)]
    if isinstance(node, dict):
        return [s for item in node.values() for s in _strings(item)]
    return []


if __name__ == "__main__":
    unittest.main()
