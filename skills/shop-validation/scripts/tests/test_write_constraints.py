"""Version, layout, protected fields, dotted keys, batch convention."""

import unittest

from . import context  # noqa: F401
from xsolla_shop_validation.errors import MISSING
from xsolla_shop_validation.write_constraints import (
    check_batch_change_set,
    check_create_version,
    check_not_layout_create,
    check_protected_fields,
    check_stored_version,
    check_text_write_target,
    expand_dotted_keys,
)


class TestVersion(unittest.TestCase):
    def test_a_create_below_max_version_is_rejected(self):
        errors = check_create_version("faq", 1)
        self.assertEqual(errors[0]["expected"], "2")
        self.assertEqual(errors[0]["got"], "1")

    def test_a_create_at_max_version_passes(self):
        self.assertEqual(check_create_version("faq", 2), [])

    def test_omitting_the_version_on_a_versioned_module_is_a_finding(self):
        self.assertEqual(check_create_version("footer", MISSING)[0]["expected"], "3")

    def test_the_ten_versioned_modules_are_the_only_ones_checked(self):
        from xsolla_shop_validation.native import MODULE_MAX_VERSION

        self.assertEqual(
            sorted(MODULE_MAX_VERSION),
            ["description", "faq", "footer", "gallery", "header", "html", "news", "packs",
             "promocodes", "requirements"],
        )

    def test_a_module_with_no_versions_list_passes_no_version(self):
        # These carry no `blockVersion` at all, so demanding one would reject
        # writes the API accepts.
        for module in ("newStore", "lead", "leadGameSales", "bento-grid", "rewards",
                       "hero", "nft", "promoSlider", "subscriptions-packs", "sidebar",
                       "fast-login", "retailers", "payment-methods", "embed", "federated"):
            self.assertEqual(check_create_version(module, MISSING), [], module)
            self.assertEqual(check_create_version(module, 1), [], module)

    def test_an_omitted_version_on_a_versioned_module_is_an_error(self):
        for module, expected in (("faq", "2"), ("footer", "3"), ("news", "2")):
            errors = check_create_version(module, MISSING)
            self.assertEqual(errors[0]["expected"], expected, module)
            self.assertEqual(errors[0]["got"], "undefined")

    def test_a_stored_block_at_an_older_version_is_never_a_finding(self):
        self.assertEqual(check_stored_version("faq", 1), [])
        self.assertEqual(check_stored_version("newStore", None), [])


class TestLayout(unittest.TestCase):
    def test_the_three_layout_modules_cannot_be_created(self):
        for module in ("header", "common-layout", "side-by-side-layout"):
            self.assertTrue(check_not_layout_create(module), module)

    def test_an_ordinary_module_can(self):
        self.assertEqual(check_not_layout_create("faq"), [])


class TestProtectedFields(unittest.TestCase):
    def test_all_three_protected_fields_are_caught(self):
        errors = check_protected_fields({"_id": "b1", "module": "faq", "blockVersion": 2})
        self.assertEqual({f["path"] for f in errors}, {"_id", "module", "blockVersion"})

    def test_an_ordinary_patch_passes(self):
        self.assertEqual(check_protected_fields({"values": {"title": {"id": "L:a"}}}), [])


class TestDottedKeys(unittest.TestCase):
    def test_a_dotted_key_expands_to_nested_objects(self):
        self.assertEqual(
            expand_dotted_keys({"internalBlockValues.successModal.image": "I:9f8e7d"}),
            {"internalBlockValues": {"successModal": {"image": "I:9f8e7d"}}},
        )

    def test_expansion_is_recursive(self):
        self.assertEqual(
            expand_dotted_keys({"values": {"a.b": 1}}), {"values": {"a": {"b": 1}}}
        )

    def test_an_undotted_payload_is_unchanged(self):
        payload = {"values": {"title": {"id": "L:a"}}, "components": []}
        self.assertEqual(expand_dotted_keys(payload), payload)

    def test_a_non_object_payload_passes_through(self):
        self.assertEqual(expand_dotted_keys("x"), "x")


class TestBatchChangeSet(unittest.TestCase):
    def test_a_well_formed_change_set_passes(self):
        change_set = {
            "r1": {
                "type": "block",
                "id": "b1",
                "patches": [{"op": "replace", "path": ["values", "title"], "value": {"id": "L:a"}}],
            }
        }
        self.assertEqual(check_batch_change_set(change_set), [])

    def test_a_dotted_string_path_is_a_finding(self):
        change_set = {
            "r1": {
                "type": "block",
                "id": "b1",
                "patches": [{"op": "replace", "path": "values.title"}],
            }
        }
        errors = check_batch_change_set(change_set)
        self.assertEqual(errors[0]["path"], "r1.patches.0.path")
        self.assertEqual(errors[0]["got"], "string")

    def test_a_bad_op_and_a_bad_type_are_both_reported(self):
        change_set = {
            "r1": {"type": "blok", "id": "b1", "patches": [{"op": "set", "path": ["values"]}]}
        }
        paths = {f["path"] for f in check_batch_change_set(change_set)}
        self.assertEqual(paths, {"r1.type", "r1.patches.0.op"})

    def test_a_missing_id_is_reported(self):
        change_set = {"r1": {"type": "site", "patches": []}}
        self.assertEqual(check_batch_change_set(change_set)[0]["path"], "r1.id")


class TestTextWriteTarget(unittest.TestCase):
    def test_patching_a_block_path_to_change_copy_is_a_finding(self):
        errors = check_text_write_target(["values.title"])
        self.assertEqual(errors[0]["got"], "a block values patch")

    def test_no_such_plan_no_finding(self):
        self.assertEqual(check_text_write_target([]), [])


if __name__ == "__main__":
    unittest.main()
