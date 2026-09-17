"""Native envelope and field-schema checks."""

import unittest

from . import context  # noqa: F401
from xsolla_shop_validation.native import (
    load_schemas,
    max_version,
    validate_envelope,
    validate_native,
)


class TestEnvelope(unittest.TestCase):
    def test_a_string_payload_is_one_root_finding_and_nothing_else(self):
        errors = validate_envelope("{\"values\": {}}")
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["path"], "(root)")
        self.assertEqual(errors[0]["expected"], "object { values?, components? }")
        self.assertEqual(errors[0]["got"], "string")

    def test_a_list_payload_is_not_an_envelope(self):
        self.assertEqual(validate_envelope([])[0]["got"], "array")

    def test_components_as_an_object_is_a_finding(self):
        errors = validate_envelope({"components": {"0": {}}})
        self.assertEqual(errors[0]["path"], "components")
        self.assertEqual(errors[0]["expected"], "array")

    def test_empty_components_array_is_a_block_with_no_sub_parts(self):
        self.assertEqual(validate_envelope({"components": []}), [])

    def test_an_absent_section_is_not_a_finding(self):
        self.assertEqual(validate_envelope({}), [])


class TestFieldSchemas(unittest.TestCase):
    def test_all_23_modules_ship_a_schema(self):
        schemas = load_schemas()
        self.assertEqual(len(schemas), 23)
        for module, entry in schemas.items():
            self.assertIn("schema", entry, module)
            self.assertIn("maxVersion", entry, module)

    def test_module_keys_are_not_normalised(self):
        schemas = load_schemas()
        self.assertIn("newStore", schemas)
        self.assertNotIn("newstore", schemas)
        self.assertIn("subscriptions-packs", schemas)
        self.assertNotIn("subscriptions", schemas)

    def test_a_misspelled_field_is_caught_by_the_closed_object(self):
        result = validate_native("faq", {"values": {"questionMod": "single"}})
        self.assertFalse(result["ok"])
        self.assertEqual(result["errors"][0]["path"], "values")
        self.assertIn("no extra keys", result["errors"][0]["expected"])

    def test_a_bare_string_where_a_localized_object_belongs(self):
        result = validate_native("faq", {"values": {"title": "Questions"}})
        self.assertFalse(result["ok"])
        self.assertEqual(result["errors"][0]["path"], "values.title")
        self.assertEqual(result["errors"][0]["expected"], "object")

    def test_an_unknown_module_passes_and_says_so(self):
        result = validate_native("brand-new-block", {"values": {"anything": 1}})
        self.assertTrue(result["ok"])
        self.assertFalse(result["schema_available"])

    def test_nested_required_keys_still_fire_on_an_update(self):
        # No shipped module declares a required key at the top level of
        # ``values``, so partial mode has nothing to relax there.  A localized
        # descriptor you *do* send still has to be complete, and that is the
        # behaviour worth pinning.
        result = validate_native(
            "faq", {"values": {"title": {"__type": "localized-value-descriptor"}}}, partial=True
        )
        self.assertFalse(result["ok"])
        missing = {f["path"] for f in result["errors"]}
        self.assertIn("values.title.enable", missing)

    def test_partial_relaxes_only_the_top_level_of_values(self):
        from xsolla_shop_validation.schema_subset import validate

        schema = {
            "type": "object",
            "properties": {
                "a": {"type": "string"},
                "nested": {
                    "type": "object",
                    "properties": {"b": {"type": "string"}},
                    "required": ["b"],
                },
            },
            "required": ["a"],
        }
        self.assertEqual(len(validate({}, schema)), 1)
        self.assertEqual(validate({}, schema, partial=True), [])
        self.assertEqual(len(validate({"nested": {}}, schema, partial=True)), 1)

    def test_sections_are_checked_independently(self):
        result = validate_native("faq", {"components": []})
        self.assertTrue(result["ok"])

    def test_max_version_comes_from_the_shipped_schema(self):
        self.assertEqual(max_version("faq"), 2)
        self.assertEqual(max_version("footer"), 3)
        self.assertIsNone(max_version("no-such-module"))


def _module_with_required_values():
    for module, entry in sorted(load_schemas().items()):
        values = ((entry.get("schema") or {}).get("properties") or {}).get("values") or {}
        if values.get("required"):
            return module
    return None


if __name__ == "__main__":
    unittest.main()


class TestAdvisories(unittest.TestCase):
    """One shipped-schema requirement is stricter than the API itself."""

    def test_a_descriptor_without_a_quill_wrapper_is_advisory_not_a_finding(self):
        descriptor = {
            "__type": "localized-value-descriptor",
            "enable": True,
            "tag": "title",
            "localizedString": {"en-US": "<h2>FAQ</h2>"},
        }
        result = validate_native("faq", {"values": {"title": descriptor}}, partial=True)
        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual([a["path"] for a in result["advisories"]], ["values.title.quillWrapper"])

    def test_a_genuinely_missing_required_key_is_still_a_finding(self):
        result = validate_native(
            "faq", {"values": {"title": {"__type": "localized-value-descriptor"}}}, partial=True
        )
        self.assertFalse(result["ok"])
        self.assertIn("values.title.enable", {f["path"] for f in result["errors"]})
