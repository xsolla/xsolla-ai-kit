"""The error shape, pinned.

The shape is pinned in more than one place across the kit so two reports can
be read side by side. Duplication drifts, so these assertions are what makes
drift fail loudly instead of quietly.
"""

from __future__ import annotations

import unittest

from xsolla_listing_import.errors import MISSING, describe_got, finding, js_type


class TestShape(unittest.TestCase):

    def test_the_key_is_got_not_actual(self):
        self.assertEqual(sorted(finding("a", "b", "c")), ["expected", "got", "path"])

    def test_value_is_omitted_when_not_given(self):
        self.assertNotIn("value", finding("a", "b", "c"))

    def test_value_is_kept_when_given(self):
        self.assertEqual(finding("a", "b", "c", value=1)["value"], 1)

    def test_an_empty_path_reads_as_root(self):
        self.assertEqual(finding("", "b", "c")["path"], "(root)")


class TestJsType(unittest.TestCase):

    def test_bool_is_boolean_not_number(self):
        """In Python True is an int; reporting 'number' misdirects the reader."""
        self.assertEqual(js_type(True), "boolean")
        self.assertEqual(js_type(1), "number")

    def test_missing_is_undefined_and_none_is_null(self):
        self.assertEqual(js_type(MISSING), "undefined")
        self.assertEqual(js_type(None), "null")

    def test_containers(self):
        self.assertEqual(js_type([]), "array")
        self.assertEqual(js_type({}), "object")


class TestDescribeGot(unittest.TestCase):

    def test_a_string_reports_its_own_content(self):
        self.assertEqual(describe_got("nintendo"), "nintendo")

    def test_a_non_string_reports_its_type(self):
        self.assertEqual(describe_got([1]), "array")


if __name__ == "__main__":
    unittest.main()
