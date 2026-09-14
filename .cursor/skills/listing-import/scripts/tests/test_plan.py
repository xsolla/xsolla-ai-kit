"""Tests for the write plan: ordering, blockers, and honest reporting."""

from __future__ import annotations

import unittest

from xsolla_listing_import import mapping, plan

from .fixtures.load import steam_listing, steam_structure


class TestAgainstTheRealImportedLanding(unittest.TestCase):
    """The structure here is one `import-listing` actually produced."""

    def setUp(self):
        self.plan, self.blockers = plan.build(steam_listing(), steam_structure())

    def test_no_blockers_on_a_well_formed_run(self):
        self.assertEqual(self.blockers, [])

    def test_localization_is_ordered_before_the_image_writes(self):
        """A block referencing an L: id with no string behind it 500s."""
        kinds = [op["kind"] for op in self.plan["operations"]]
        last_localization = max(i for i, k in enumerate(kinds) if k == "localization")
        first_asset = min(i for i, k in enumerate(kinds) if k == "asset")
        self.assertLess(last_localization, first_asset)

    def test_every_screenshot_gets_its_own_slide_index(self):
        slides = [op["path"] for op in self.plan["operations"]
                  if op["field"] == "screenshots"]
        indices = [path[2] for path in slides]
        self.assertEqual(indices, list(range(len(slides))))

    def test_key_art_brings_its_companion_patches(self):
        paths = [tuple(op["path"]) for op in self.plan["operations"]
                 if op["field"] == "key_art"]
        self.assertIn(("values", "background", "enable"), paths)
        self.assertIn(("values", "background", "size"), paths)

    def test_the_real_template_has_no_sidebar_so_platforms_is_unresolved(self):
        unresolved = {item["field"] for item in self.plan["unresolved"]}
        self.assertIn("platforms", unresolved)

    def test_steps_are_numbered_from_one_without_gaps(self):
        steps = [op["step"] for op in self.plan["operations"]]
        self.assertEqual(steps, list(range(1, len(steps) + 1)))

    def test_asset_operations_never_write_the_source_url(self):
        for op in self.plan["operations"]:
            if op["kind"] == "asset":
                self.assertNotIn("value", op)
                self.assertIn("source_url", op)


class TestBlockers(unittest.TestCase):

    def _build(self, overrides, structure=None):
        document = steam_listing()
        document.update(overrides)
        return plan.build(document, structure if structure is not None
                          else steam_structure())

    def test_rights_not_confirmed_blocks(self):
        _plan, blockers = self._build({"rights_confirmed": False})
        self.assertIn("rights_confirmed", [b["path"] for b in blockers])

    def test_source_contradicting_the_url_blocks(self):
        _plan, blockers = self._build(
            {"source_url": "https://play.google.com/store/apps/details?id=x"})
        self.assertIn("source", [b["path"] for b in blockers])

    def test_an_empty_landing_blocks(self):
        """import-listing silently no-ops on a landing that has a structure,
        so an empty one here means the import did not run."""
        _plan, blockers = self._build({}, structure={"pages": []})
        self.assertIn("structure", [b["path"] for b in blockers])

    def test_an_unknown_host_does_not_block(self):
        _plan, blockers = self._build({"source_url": "https://example.test/x"})
        self.assertEqual([b["path"] for b in blockers], [])


class TestUnverifiedReporting(unittest.TestCase):
    """A gate that hides its blind spots is worse than no gate."""

    def test_missing_localization_is_reported_as_unverified(self):
        built, _ = plan.build(steam_listing(), steam_structure())
        self.assertTrue(any("L: reference" in item for item in built["unverified"]))

    def test_passing_localization_clears_that_line(self):
        built, _ = plan.build(steam_listing(), steam_structure(), localization={})
        self.assertFalse(any("L: reference" in item for item in built["unverified"]))

    def test_schema_only_paths_are_named(self):
        built, _ = plan.build(steam_listing(), steam_structure())
        line = [i for i in built["unverified"] if "silently no-op" in i]
        self.assertEqual(len(line), 1)
        self.assertIn("title", line[0])

    def test_confirmed_fields_are_not_in_the_unverified_line(self):
        built, _ = plan.build(steam_listing(), steam_structure())
        line = [i for i in built["unverified"] if "silently no-op" in i][0]
        self.assertNotIn("key_art", line)
        self.assertNotIn("screenshots", line)


class TestDescriptionRouting(unittest.TestCase):

    def _value(self, values):
        document = {"source": "steam",
                    "source_url": "https://store.steampowered.com/app/1/",
                    "rights_confirmed": True, "fields": values}
        structure = {"pages": [{"_id": "p", "blocks": [
            {"_id": "b", "module": "description"}]}]}
        built, _ = plan.build(document, structure)
        return built["operations"][0]

    def test_html_is_sanitised(self):
        op = self._value({"long_description_html":
                          '<h2 class="bb_tag">T</h2><video><source src="x"></video>b'})
        self.assertEqual(op["value"], "<h2>T</h2>b")
        self.assertIn("video", op["dropped"])

    def test_bbcode_is_converted(self):
        op = self._value({"long_description_bbcode": "[h2]T[/h2]"})
        self.assertEqual(op["value"], "<h2>T</h2>")

    def test_plain_text_is_escaped_not_passed_through(self):
        op = self._value({"long_description_text": "5 < 7 & <b>not bold</b>"})
        self.assertNotIn("<b>", op["value"])
        self.assertIn("&lt;b&gt;", op["value"])


class TestIndexBlocks(unittest.TestCase):

    def test_duplicate_modules_keep_page_order(self):
        found = plan.index_blocks({"pages": [{"_id": "p", "blocks": [
            {"_id": "a", "module": "packs"}, {"_id": "b", "module": "packs"}]}]})
        self.assertEqual(found["packs"], [("p", "a"), ("p", "b")])

    def test_the_real_template_carries_three_packs_and_two_descriptions(self):
        found = plan.index_blocks(steam_structure())
        self.assertEqual(len(found["packs"]), 3)
        self.assertEqual(len(found["description"]), 2)

    def test_site_level_id_only_entries_are_not_blocks(self):
        """The site-level blocks[] holds ids, not documents."""
        found = plan.index_blocks({"pages": [], "blocks": ["id1", "id2"]})
        self.assertEqual(found, {})

    def test_empty_structure(self):
        self.assertEqual(plan.index_blocks(None), {})


class TestCounts(unittest.TestCase):

    def test_counts_agree_with_the_operation_list(self):
        built, _ = plan.build(steam_listing(), steam_structure())
        kinds = [op["kind"] for op in built["operations"]]
        self.assertEqual(built["counts"]["localization"], kinds.count("localization"))
        self.assertEqual(built["counts"]["asset"], kinds.count("asset"))
        self.assertEqual(built["counts"]["patch"], kinds.count("patch"))
        self.assertEqual(built["counts"]["unresolved"], len(built["unresolved"]))
        self.assertEqual(built["counts"]["manual"], len(built["manual_follow_up"]))

    def test_manual_rows_are_the_mapping_table_manual_rows(self):
        built, _ = plan.build(steam_listing(), steam_structure())
        for item in built["manual_follow_up"]:
            self.assertIn(item["action"], (mapping.MANUAL, mapping.EXTERNAL))


if __name__ == "__main__":
    unittest.main()


class TestMalformedInputToAPublicEntryPoint(unittest.TestCase):
    """`plan.build` is public; the CLI validates first but a direct caller may not."""

    def _build(self, values):
        document = {"source": "steam",
                    "source_url": "https://store.steampowered.com/app/1/",
                    "rights_confirmed": True, "fields": values}
        structure = {"pages": [{"_id": "p", "blocks": [
            {"_id": "b", "module": "gallery"}]}]}
        return plan.build(document, structure)[0]

    def test_a_string_where_screenshots_wants_a_list_is_not_iterated(self):
        built = self._build({"screenshots": "https://x.test/a.jpg"})
        urls = [op["source_url"] for op in built["operations"]]
        self.assertEqual(urls, ["https://x.test/a.jpg"])

    def test_blank_and_non_string_entries_are_skipped(self):
        built = self._build({"screenshots": ["https://x.test/a.jpg", "  ", None, 7]})
        self.assertEqual(len(built["operations"]), 1)

    def test_an_empty_screenshot_list_produces_no_operations(self):
        self.assertEqual(self._build({"screenshots": []})["operations"], [])
