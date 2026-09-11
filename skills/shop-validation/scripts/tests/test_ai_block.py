"""The nine code rules, one test per rule plus the clean case."""

import unittest

from . import context  # noqa: F401
from xsolla_shop_validation.ai_block import check_text_refs, collect_violations

CLEAN = """
import { TextEditor } from '@site-builder/block-utils';

export default function MyBlock() {
  const label = useControls(text('Label', 'default'));
  const size = useControls(select('Size', ['sm', 'lg'], 'sm'));
  const count = useControls(number('Count', 0, { min: 0, max: 10, step: 1 }));
  return (
    <div style={{ padding: 16 }}>
      <TextEditor id={localizedText('title')} />
      {label}{size}{count}
    </div>
  );
}
"""

CLEAN_FIELDS = [{"name": "title", "default": "Hello"}]


def rules(*args, **kwargs):
    return [v["rule"] for v in collect_violations(*args, **kwargs)]


class TestCleanSource(unittest.TestCase):
    def test_a_correct_block_produces_nothing(self):
        settings = "export default () => <AutoControls />;"
        self.assertEqual(collect_violations(CLEAN, settings, CLEAN_FIELDS), [])

    def test_numbers_options_object_in_third_position_is_legitimate(self):
        self.assertNotIn("control-factory-object-arg", rules(CLEAN, None, CLEAN_FIELDS))


class TestRules(unittest.TestCase):
    def test_1_forbidden_import_of_a_global(self):
        code = "import { useControls } from '@site-builder/block-utils';"
        self.assertIn("forbidden-import", rules(code))

    def test_1_forbidden_import_among_several_names(self):
        code = "import { TextEditor, localizedText } from '@site-builder/block-utils';"
        self.assertIn("forbidden-import", rules(code))

    def test_1_an_import_from_elsewhere_is_not_checked(self):
        code = "import { text } from './my-helpers';"
        self.assertNotIn("forbidden-import", rules(code))

    def test_2_texteditor_used_without_its_import(self):
        self.assertIn(
            "missing-texteditor-import",
            rules(
                "export default () => <TextEditor id={localizedText('t')} />;",
                None,
                CLEAN_FIELDS,
            ),
        )

    def test_2_the_import_may_live_in_the_settings_source(self):
        component = "export default () => <TextEditor id={localizedText('title')} />;"
        settings = "import { TextEditor } from '@site-builder/block-utils';"
        self.assertNotIn("missing-texteditor-import", rules(component, settings, CLEAN_FIELDS))

    def test_3_localized_text_as_a_named_function_prop(self):
        self.assertIn(
            "localized-text-prop-shadow",
            rules("export default function MyBlock({ localizedText }) { return null; }"),
        )

    def test_3_localized_text_as_an_arrow_prop(self):
        self.assertIn(
            "localized-text-prop-shadow",
            rules("const B = ({ localizedText }) => null; export default B;"),
        )

    def test_4_export_default_class(self):
        self.assertIn(
            "export-default-class", rules("export default class B extends React.Component {}")
        )

    def test_4_export_default_class_in_the_settings_source(self):
        self.assertIn(
            "export-default-class",
            rules("export default () => null;", "export default class S {}"),
        )

    def test_5_undeclared_text_field_names_are_listed(self):
        violations = collect_violations(
            "export default () => localizedText('subtitle');", None, CLEAN_FIELDS
        )
        self.assertEqual([v["rule"] for v in violations], ["undeclared-text-fields"])
        self.assertIn('"subtitle"', violations[0]["message"])

    def test_5_declared_names_pass(self):
        self.assertNotIn(
            "undeclared-text-fields",
            rules("export default () => localizedText('title');", None, CLEAN_FIELDS),
        )

    def test_6_texteditor_with_no_declared_fields(self):
        source = "import { TextEditor } from '@site-builder/block-utils'; const a = <TextEditor />;"
        found = rules(source, None, [])
        self.assertIn("missing-text-fields", found)

    def test_7_use_controls_with_an_object_literal(self):
        self.assertIn("use-controls-object-arg", rules("const v = useControls({ a: 1 });"))

    def test_8_control_factory_with_an_object_first(self):
        for call in ("color({ value: 1 })", "toggle({ on: true })", "select({ options: [] })"):
            self.assertIn("control-factory-object-arg", rules("const v = %s;" % call), call)

    def test_9_text_control_bound_to_localized_text(self):
        self.assertIn(
            "text-control-with-localized-text",
            rules(
                "const v = useControls(text('Heading', localizedText('title')));",
                None,
                CLEAN_FIELDS,
            ),
        )


class TestTextRefs(unittest.TestCase):
    def test_empty_text_refs_with_canvas_text_is_a_finding(self):
        self.assertEqual(
            [v["rule"] for v in check_text_refs("<TextEditor id={localizedText('t')} />", {})],
            ["empty-text-refs"],
        )

    def test_populated_text_refs_pass(self):
        self.assertEqual(check_text_refs("localizedText('t')", {"t": "L:uuid"}), [])

    def test_a_block_with_no_canvas_text_is_not_expected_to_have_refs(self):
        self.assertEqual(check_text_refs("export default () => <div />;", {}), [])


class TestFindingShape(unittest.TestCase):
    def test_every_violation_carries_all_three_parts(self):
        violations = collect_violations(
            "export default class B { m() { return useControls({}); } }", None, None
        )
        self.assertTrue(violations)
        for violation in violations:
            self.assertTrue(violation["rule"])
            self.assertTrue(violation["message"])
            self.assertTrue(violation["suggestion"])


if __name__ == "__main__":
    unittest.main()
