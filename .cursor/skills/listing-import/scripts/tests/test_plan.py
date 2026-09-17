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
        # Each entry is (page_id, block_id, block_document) — the document is
        # carried so L: ids can be resolved without a second fetch.
        self.assertEqual([(p, b) for p, b, _d in found["packs"]],
                         [("p", "a"), ("p", "b")])
        self.assertEqual(found["packs"][0][2]["module"], "packs")

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
        # A real gallery carries a slides array; the screenshot cap counts it.
        structure = {"pages": [{"_id": "p", "blocks": [
            {"_id": "b", "module": "gallery",
             "values": {"slides": [{"id": "s%d" % i} for i in range(4)]}}]}]}
        return plan.build(document, structure)[0]

    def test_a_string_where_screenshots_wants_a_list_is_not_iterated(self):
        built = self._build({"screenshots": "https://x.test/a.jpg"})
        urls = [op["source_url"] for op in built["operations"]
                if op["kind"] == "asset"]
        self.assertEqual(urls, ["https://x.test/a.jpg"])

    def test_blank_and_non_string_entries_are_skipped(self):
        built = self._build({"screenshots": ["https://x.test/a.jpg", "  ", None, 7]})
        # One upload, plus the companion patches that make the slide visible.
        self.assertEqual(len([o for o in built["operations"]
                              if o["kind"] == "asset"]), 1)

    def test_an_empty_screenshot_list_places_nothing_and_prunes_the_gallery(self):
        built = self._build({"screenshots": []})
        self.assertEqual([o for o in built["operations"]
                          if o["field"] == "screenshots"], [])
        # Nothing to show in the gallery, so the gallery goes.
        pruned = [o for o in built["operations"] if o["kind"] == "delete"]
        self.assertEqual([o["module"] for o in pruned], ["gallery"])


class TestOverflowAndCatalogRouting(unittest.TestCase):
    """The four fields that used to be reported as unmappable."""

    def _plan(self, values, modules=("description", "gallery")):
        document = {"source": "steam",
                    "source_url": "https://store.steampowered.com/app/1/",
                    "rights_confirmed": True, "fields": values}

        def block(index, module):
            doc = {"_id": "b%d" % index, "module": module}
            if module == "gallery":
                doc["values"] = {"slides": [{"id": "s%d" % i} for i in range(4)]}
            return doc

        structure = {"pages": [{"_id": "p", "blocks": [
            block(i, m) for i, m in enumerate(modules)]}]}
        return plan.build(document, structure)[0]

    def test_three_overflow_fields_become_one_component(self):
        built = self._plan({"genres": ["RPG"], "tags": ["Co-op"],
                            "age_rating": "PEGI 18"})
        overflow_ops = [o for o in built["operations"] if o["kind"] == "overflow"]
        self.assertEqual(len(overflow_ops), 1)
        self.assertEqual(overflow_ops[0]["field"], "genres+tags+age_rating")

    def test_the_component_targets_the_description_block(self):
        built = self._plan({"genres": ["RPG"]})
        op = [o for o in built["operations"] if o["kind"] == "overflow"][0]
        self.assertEqual(op["module"], "description")
        self.assertEqual(op["path"], ["values", "components"])

    def test_no_description_block_reports_each_field_unresolved(self):
        built = self._plan({"genres": ["RPG"], "age_rating": "PEGI 18"},
                           modules=("gallery",))
        unresolved = {u["field"] for u in built["unresolved"]}
        self.assertIn("genres", unresolved)
        self.assertIn("age_rating", unresolved)

    def test_overflow_comes_after_localization_before_assets(self):
        built = self._plan({"title": "T", "genres": ["RPG"],
                            "screenshots": ["https://x.test/a.jpg"]},
                           modules=("leadGameSales", "description", "gallery"))
        kinds = [o["kind"] for o in built["operations"]]
        self.assertLess(kinds.index("overflow"), kinds.index("asset"))

    def test_iap_items_become_catalog_operations_not_page_operations(self):
        built = self._plan({"iap_items": [
            {"name": "Gold Pass", "price": {"amount": 4.99, "currency": "USD"}}]})
        self.assertEqual(len(built["catalog_operations"]), 1)
        self.assertEqual(built["catalog_operations"][0]["entity"], "virtual_item")
        self.assertFalse([o for o in built["operations"]
                          if o["field"] == "iap_items"])

    def test_catalog_warnings_state_the_quantity_limitation(self):
        built = self._plan({"iap_items": [{"name": "Pocketful of Gems"}]})
        self.assertTrue(any("quantity" in w for w in built["catalog_warnings"]))

    def test_no_iap_items_means_no_catalog_work(self):
        built = self._plan({"genres": ["RPG"]})
        self.assertEqual(built["catalog_operations"], [])
        self.assertEqual(built["catalog_warnings"], [])

    def test_counts_include_the_new_kinds(self):
        built = self._plan({"genres": ["RPG"], "iap_items": [{"name": "X"}]})
        self.assertEqual(built["counts"]["overflow"], 1)
        self.assertEqual(built["counts"]["catalog"], 1)

    def test_nothing_falls_through_to_manual(self):
        built = self._plan({"genres": ["RPG"], "tags": ["Co-op"],
                            "age_rating": "PEGI 18", "iap_items": [{"name": "X"}]})
        self.assertEqual(built["manual_follow_up"], [])


class TestLocalizedIdResolution(unittest.TestCase):
    """A localization write targets an `L:` id, not a path."""

    def test_resolves_the_id_a_field_already_carries(self):
        block = {"values": {"title": {"enable": True, "id": "L:abc-123"}}}
        self.assertEqual(plan.resolve_localized_id(block, ("values", "title")),
                         "L:abc-123")

    def test_a_bare_l_string_also_resolves(self):
        block = {"values": {"title": "L:abc-123"}}
        self.assertEqual(plan.resolve_localized_id(block, ("values", "title")),
                         "L:abc-123")

    def test_an_absent_path_is_none_not_an_invention(self):
        self.assertIsNone(plan.resolve_localized_id({"values": {}}, ("values", "title")))

    def test_a_field_with_no_id_is_none(self):
        block = {"values": {"title": {"enable": True}}}
        self.assertIsNone(plan.resolve_localized_id(block, ("values", "title")))

    def test_a_non_l_id_is_refused(self):
        """An id that is not an L: reference is not a localization target."""
        block = {"values": {"title": {"id": "I:image01"}}}
        self.assertIsNone(plan.resolve_localized_id(block, ("values", "title")))

    def test_the_plan_carries_the_id_through(self):
        document = {"source": "steam",
                    "source_url": "https://store.steampowered.com/app/1/",
                    "rights_confirmed": True, "fields": {"title": "T"}}
        structure = {"pages": [{"_id": "p", "blocks": [
            {"_id": "b", "module": "leadGameSales",
             "values": {"title": {"enable": True, "id": "L:real-id"}}}]}]}
        built, _ = plan.build(document, structure)
        op = [o for o in built["operations"] if o["field"] == "title"][0]
        self.assertEqual(op["localized_id"], "L:real-id")

    def test_a_block_with_no_id_yields_none_so_the_runner_can_refuse(self):
        document = {"source": "steam",
                    "source_url": "https://store.steampowered.com/app/1/",
                    "rights_confirmed": True, "fields": {"title": "T"}}
        structure = {"pages": [{"_id": "p", "blocks": [
            {"_id": "b", "module": "leadGameSales", "values": {}}]}]}
        built, _ = plan.build(document, structure)
        op = [o for o in built["operations"] if o["field"] == "title"][0]
        self.assertIsNone(op["localized_id"])


class TestGallerySlotsAreFinite(unittest.TestCase):
    """The bug the Play and Apple runs found.

    A gallery's `slides` array already exists and has a fixed length. A patch to
    `slides[3].image.img` on a three-slide block is accepted and changes
    nothing — Steam's imported gallery has ten slides and took all ten
    screenshots, while the default template has three and silently dropped the
    rest.
    """

    def _plan(self, screenshots, slots):
        document = {"source": "steam",
                    "source_url": "https://store.steampowered.com/app/1/",
                    "rights_confirmed": True,
                    "fields": {"screenshots": screenshots}}
        structure = {"pages": [{"_id": "p", "blocks": [
            {"_id": "g", "module": "gallery",
             "values": {"slides": [{"id": str(i)} for i in range(slots)]}}]}]}
        return plan.build(document, structure)[0]

    def test_screenshots_are_capped_at_the_slide_count(self):
        built = self._plan(["https://x.test/%d.jpg" % i for i in range(6)], 3)
        ops = [o for o in built["operations"]
               if o["field"] == "screenshots" and o["kind"] == "asset"]
        self.assertEqual(len(ops), 3)
        self.assertEqual([o["path"][2] for o in ops], [0, 1, 2])

    def test_the_surplus_is_reported_not_dropped(self):
        built = self._plan(["https://x.test/%d.jpg" % i for i in range(6)], 3)
        surplus = [u for u in built["unresolved"] if u["field"] == "screenshots"]
        self.assertEqual(len(surplus), 1)
        self.assertIn("3 cannot be placed", surplus[0]["reason"])

    def test_enough_slots_means_no_surplus(self):
        built = self._plan(["https://x.test/%d.jpg" % i for i in range(3)], 10)
        self.assertEqual(len([o for o in built["operations"]
                              if o["field"] == "screenshots"
                              and o["kind"] == "asset"]), 3)
        self.assertEqual([u for u in built["unresolved"]
                          if u["field"] == "screenshots"], [])

    def test_a_gallery_with_no_slides_places_nothing(self):
        built = self._plan(["https://x.test/a.jpg"], 0)
        self.assertEqual([o for o in built["operations"]
                          if o["field"] == "screenshots"], [])
        self.assertTrue([u for u in built["unresolved"]
                         if u["field"] == "screenshots"])


class TestEditionsOnThePage(unittest.TestCase):
    """Editions went to the catalog and nowhere else, leaving the page showing
    `Edition name / Provide your players with detailed…`."""

    def _card(self, ref_suffix):
        return {"image": {"img": ""}, "content": [
            {"type": "label", "enable": True, "text": {"id": "L:lbl%s" % ref_suffix}},
            {"type": "title", "enable": True, "text": {"id": "L:ttl%s" % ref_suffix}},
            {"type": "description", "enable": True,
             "text": {"id": "L:dsc%s" % ref_suffix}},
            {"type": "advantages", "enable": True, "items": []},
            {"type": "button", "enable": True, "button": {"variant": "primary"}},
        ]}

    def _plan(self, editions, cards=3, extra_packs=0):
        document = {"source": "steam",
                    "source_url": "https://store.steampowered.com/app/1/",
                    "rights_confirmed": True, "fields": {"iap_items": editions}}
        blocks = [{"_id": "p-main", "module": "packs",
                   "values": {"packs": [self._card(str(i)) for i in range(cards)]}}]
        for n in range(extra_packs):
            blocks.append({"_id": "p-x%d" % n, "module": "packs",
                           "values": {"packs": [self._card("x%d" % n)]}})
        return plan.build(document, {"pages": [{"_id": "pg", "blocks": blocks}]})[0]

    def _editions(self, count):
        return [{"name": "Edition %d" % i,
                 "price": {"amount": 9.99 + i, "currency": "EUR"},
                 "image": "https://x.test/%d.jpg" % i} for i in range(count)]

    def test_each_edition_name_is_written_to_a_card_title(self):
        built = self._plan(self._editions(3))
        titles = [o for o in built["operations"] if o["field"] == "edition.title"]
        self.assertEqual(len(titles), 3)
        self.assertEqual([o["value"] for o in titles],
                         ["Edition 0", "Edition 1", "Edition 2"])

    def test_the_title_targets_the_content_rows_own_l_id(self):
        built = self._plan(self._editions(1))
        op = [o for o in built["operations"] if o["field"] == "edition.title"][0]
        self.assertEqual(op["localized_id"], "L:ttl0")
        self.assertEqual(op["path"], ["values", "packs", 0, "content", 1, "text"])

    def test_an_edition_with_no_description_falls_back_to_its_price(self):
        built = self._plan(self._editions(1))
        op = [o for o in built["operations"]
              if o["field"] == "edition.description"][0]
        self.assertEqual(op["value"], "9.99 EUR")

    def test_a_real_description_wins_over_the_price(self):
        editions = self._editions(1)
        editions[0]["description"] = "Unlock every Legend."
        built = self._plan(editions)
        op = [o for o in built["operations"]
              if o["field"] == "edition.description"][0]
        self.assertEqual(op["value"], "Unlock every Legend.")

    def test_the_editions_artwork_is_uploaded_to_its_card(self):
        built = self._plan(self._editions(2))
        ops = [o for o in built["operations"] if o["field"] == "edition.image"]
        self.assertEqual([o["path"] for o in ops],
                         [["values", "packs", 0, "image", "img"],
                          ["values", "packs", 1, "image", "img"]])

    def test_rows_with_no_source_data_are_disabled(self):
        built = self._plan(self._editions(1))
        disabled = [o for o in built["operations"]
                    if o["field"] in ("edition.label", "edition.advantages")]
        self.assertTrue(disabled)
        self.assertTrue(all(o["value"] is False for o in disabled))

    def test_a_card_with_no_edition_is_hidden(self):
        built = self._plan(self._editions(1), cards=3)
        hidden = [o for o in built["operations"] if o["field"] == "edition.unused"]
        self.assertEqual([o["path"] for o in hidden],
                         [["values", "packs", 1, "hidden"],
                          ["values", "packs", 2, "hidden"]])

    def test_more_editions_than_cards_reports_the_surplus(self):
        built = self._plan(self._editions(5), cards=3)
        surplus = [u for u in built["unresolved"] if u["field"] == "iap_items"]
        self.assertEqual(len(surplus), 1)
        self.assertIn("2 cannot be shown", surplus[0]["reason"])
        self.assertIn("Edition 3", surplus[0]["note"])

    def test_cards_across_every_packs_block_are_used(self):
        """An earlier version filled only the widest block, which hid editions
        the listing publishes — Steam's five became three. A landing's three
        blocks hold 1 + 3 + 1 = exactly five cards."""
        built = self._plan(self._editions(5), cards=3, extra_packs=2)
        titles = [o for o in built["operations"] if o["field"] == "edition.title"]
        self.assertEqual(len(titles), 5)
        self.assertEqual({o["block_id"] for o in titles},
                         {"p-main", "p-x0", "p-x1"})
        self.assertEqual([u for u in built["unresolved"]
                          if u["field"] == "iap_items"], [])

    def test_a_packs_block_that_received_an_edition_is_not_pruned(self):
        built = self._plan(self._editions(5), cards=3, extra_packs=2)
        self.assertEqual([o for o in built["operations"]
                          if o["kind"] == "delete" and o["module"] == "packs"], [])

    def test_the_buy_button_points_at_the_editions_catalog_sku(self):
        """The price on the button comes from the catalog item, not the page."""
        built = self._plan(self._editions(2))
        buttons = [o for o in built["operations"] if o["field"] == "edition.button"]
        self.assertEqual(len(buttons), 2)
        self.assertEqual(buttons[0]["path"][-3:], ["button", "action", "sku"])
        skus = [o["sku"] for o in built["catalog_operations"]]
        self.assertEqual([b["value"] for b in buttons], skus[:2])

    def test_the_catalog_item_is_created_before_the_button_references_it(self):
        built = self._plan(self._editions(1))
        self.assertTrue(built["catalog_operations"])
        button = [o for o in built["operations"]
                  if o["field"] == "edition.button"][0]
        self.assertEqual(button["value"], built["catalog_operations"][0]["sku"])

    def test_a_cleaned_description_is_preferred_over_the_storefronts_own(self):
        editions = self._editions(1)
        editions[0]["description"] = "BUY NOW!!! Available on Steam, PS4, Xbox!"
        editions[0]["description_clean"] = "Unlock every Legend, present and future."
        built = self._plan(editions)
        op = [o for o in built["operations"]
              if o["field"] == "edition.description"][0]
        self.assertEqual(op["value"], "Unlock every Legend, present and future.")


class TestPruningWhatTheListingCannotFill(unittest.TestCase):
    """Nine of thirteen blocks kept their template copy in every shop.

    Hiding them left a Play shop carrying three invisible "Game editions"
    sections. A block the listing cannot fill is now removed instead, so it is
    absent rather than merely unseen.
    """

    def _plan(self, modules, fields=None):
        document = {"source": "steam",
                    "source_url": "https://store.steampowered.com/app/1/",
                    "rights_confirmed": True,
                    "fields": fields if fields is not None else {"title": "T"}}
        blocks = []
        for index, module in enumerate(modules):
            doc = {"_id": "b%d" % index, "module": module}
            if module == "leadGameSales":
                doc["values"] = {"title": {"id": "L:t"}}
            elif module == "gallery":
                doc["values"] = {"slides": [{"id": "s"}]}
            blocks.append(doc)
        return plan.build(document, {"pages": [{"_id": "p", "blocks": blocks}]})[0]

    def _pruned(self, built):
        return {o["module"] for o in built["operations"] if o["kind"] == "delete"}

    def test_an_untouched_block_is_pruned(self):
        built = self._plan(["leadGameSales", "faq", "requirements", "bento-grid"])
        self.assertEqual(self._pruned(built),
                         {"faq", "requirements", "bento-grid"})

    def test_a_written_block_is_not_pruned(self):
        built = self._plan(["leadGameSales", "faq"])
        pruned = {o["block_id"] for o in built["operations"]
                  if o["kind"] == "delete"}
        self.assertNotIn("b0", pruned)

    def test_the_header_and_footer_are_never_pruned(self):
        """Deleting those removes navigation, not placeholder copy."""
        built = self._plan(["header", "footer", "faq"])
        self.assertEqual(self._pruned(built), {"faq"})

    def test_layout_modules_are_never_pruned(self):
        built = self._plan(["common-layout", "side-by-side-layout", "faq"])
        self.assertEqual(self._pruned(built), {"faq"})

    def test_deletes_come_after_every_write(self):
        """A block is only removed once anything with something to say has
        said it."""
        built = self._plan(["leadGameSales", "faq"])
        kinds = [o["kind"] for o in built["operations"]]
        self.assertEqual(kinds[-1], "delete")
        self.assertNotIn("delete", kinds[:-1])

    def test_a_delete_names_the_block_and_its_page(self):
        built = self._plan(["leadGameSales", "faq"])
        op = [o for o in built["operations"] if o["kind"] == "delete"][0]
        self.assertEqual(op["field"], "unsupported.faq")
        self.assertEqual(op["page_id"], "p")
        self.assertTrue(op["block_id"])
        self.assertIsNone(op["path"])
        self.assertIn("backup", op["note"])

    def test_the_count_matches_the_delete_operations(self):
        built = self._plan(["leadGameSales", "faq", "bento-grid"])
        self.assertEqual(built["counts"]["delete"],
                         len([o for o in built["operations"]
                              if o["kind"] == "delete"]))


class TestSlideOverlayCompanions(unittest.TestCase):
    """The bug the Play and App Store shops showed.

    A slide's media object carries a colour layer over the image, and the
    default block template ships it at `rgba(23, 19, 32, 0.85)` — an 85% opaque
    dark wash. Three screenshots uploaded, patched, and read back as correct,
    all invisible. A landing built by `import-listing` has it transparent
    already, which is why Steam looked right and the other two did not.
    """

    def _plan(self, count=2):
        document = {"source": "steam",
                    "source_url": "https://store.steampowered.com/app/1/",
                    "rights_confirmed": True,
                    "fields": {"screenshots": ["https://x.test/%d.jpg" % i
                                               for i in range(count)]}}
        structure = {"pages": [{"_id": "p", "blocks": [
            {"_id": "g", "module": "gallery",
             "values": {"slides": [{"id": "s%d" % i} for i in range(4)]}}]}]}
        return plan.build(document, structure)[0]

    def test_each_slide_image_brings_its_companions(self):
        built = self._plan(2)
        patches = [o for o in built["operations"]
                   if o["field"] == "screenshots" and o["kind"] == "patch"]
        self.assertEqual(len(patches), 4)

    def test_the_overlay_is_set_transparent(self):
        built = self._plan(1)
        colour = [o for o in built["operations"]
                  if o["kind"] == "patch" and o["path"][-1] == "color"]
        self.assertEqual(len(colour), 1)
        self.assertEqual(colour[0]["value"], "transparent")

    def test_the_companions_target_the_same_slide(self):
        built = self._plan(2)
        for index in (0, 1):
            paths = [o["path"] for o in built["operations"]
                     if o["field"] == "screenshots" and o["path"][2] == index]
            self.assertEqual(len(paths), 3)
            self.assertEqual({tuple(p[:4]) for p in paths},
                             {("values", "slides", index, "image")})

    def test_the_image_write_comes_before_its_companions(self):
        built = self._plan(1)
        ops = [o for o in built["operations"] if o["field"] == "screenshots"]
        self.assertEqual(ops[0]["kind"], "asset")


class TestSystemRequirements(unittest.TestCase):
    """Steam publishes these and the block exists; it was being pruned."""

    def _block(self, components=2, rows=3):
        def component():
            return {"type": "platform_req_v2", "enable": True, "value": {
                "requirementList": [
                    {"id": "r%d" % i,
                     "name": {"id": "L:n%d" % i},
                     "minimum": {"id": "L:m%d" % i}} for i in range(rows)]}}
        return {"_id": "req", "module": "requirements",
                "components": [component() for _ in range(components)]}

    def _plan(self, platforms, components=2, rows=3):
        document = {"source": "steam",
                    "source_url": "https://store.steampowered.com/app/1/",
                    "rights_confirmed": True,
                    "fields": {"requirements": platforms}}
        structure = {"pages": [{"_id": "p", "blocks": [
            self._block(components, rows)]}]}
        return plan.build(document, structure)[0]

    def _windows(self, count=2):
        return {"platform": "windows", "rows": [
            {"type": "memory", "name": "Memory", "value": "2 GB RAM"},
            {"type": "storage", "name": "Storage", "value": "800 MB"},
        ][:count]}

    def test_each_row_is_two_localization_writes(self):
        """A requirement row carries name and minimum as separate L: refs."""
        built = self._plan([self._windows(2)])
        ops = [o for o in built["operations"]
               if o["field"].startswith("requirement.")]
        self.assertEqual(len(ops), 4)
        self.assertEqual({o["field"] for o in ops},
                         {"requirement.name", "requirement.minimum"})

    def test_the_label_and_the_value_go_to_their_own_refs(self):
        built = self._plan([self._windows(1)])
        by_field = {o["field"]: o for o in built["operations"]
                    if o["field"].startswith("requirement.")}
        self.assertEqual(by_field["requirement.name"]["value"], "Memory")
        self.assertEqual(by_field["requirement.name"]["localized_id"], "L:n0")
        self.assertEqual(by_field["requirement.minimum"]["value"], "2 GB RAM")
        self.assertEqual(by_field["requirement.minimum"]["localized_id"], "L:m0")

    def test_a_second_platform_uses_the_second_component(self):
        built = self._plan([self._windows(1),
                            {"platform": "macos",
                             "rows": [{"name": "OS", "value": "10.7"}]}])
        indices = {o["path"][1] for o in built["operations"]
                   if o["field"].startswith("requirement.")}
        self.assertEqual(indices, {0, 1})

    def test_the_block_is_not_pruned_once_it_has_requirements(self):
        built = self._plan([self._windows()])
        self.assertEqual([o for o in built["operations"]
                          if o["kind"] == "delete"], [])

    def test_more_rows_than_the_component_has_is_reported(self):
        built = self._plan([{"platform": "windows", "rows": [
            {"name": "N%d" % i, "value": "V%d" % i} for i in range(6)]}],
            rows=3)
        surplus = [u for u in built["unresolved"] if u["field"] == "requirements"]
        self.assertEqual(len(surplus), 1)
        self.assertIn("had no row", surplus[0]["reason"])

    def test_no_requirements_block_is_reported_not_silent(self):
        document = {"source": "steam",
                    "source_url": "https://store.steampowered.com/app/1/",
                    "rights_confirmed": True,
                    "fields": {"requirements": [self._windows()]}}
        structure = {"pages": [{"_id": "p", "blocks": [
            {"_id": "x", "module": "faq"}]}]}
        built = plan.build(document, structure)[0]
        self.assertTrue([u for u in built["unresolved"]
                         if u["field"] == "requirements"])


class TestUnhidingABlockThatGetsContent(unittest.TestCase):
    """The Steam bug: an earlier run hid two packs blocks, a later run wrote
    editions into them, and nobody cleared the flag. Both writes reported as
    applied — and they were, into blocks nobody could see."""

    def _plan(self, hidden):
        document = {"source": "steam",
                    "source_url": "https://store.steampowered.com/app/1/",
                    "rights_confirmed": True, "fields": {"title": "T"}}
        structure = {"pages": [{"_id": "p", "blocks": [
            {"_id": "lg", "module": "leadGameSales", "hidden": hidden,
             "values": {"title": {"id": "L:t"}}}]}]}
        return plan.build(document, structure)[0]

    def test_a_hidden_block_receiving_content_is_unhidden(self):
        built = self._plan(True)
        ops = [o for o in built["operations"] if o["field"].startswith("visible.")]
        self.assertEqual(len(ops), 1)
        self.assertEqual(ops[0]["path"], ["hidden"])
        self.assertIs(ops[0]["value"], False)

    def test_the_unhide_comes_before_the_content(self):
        built = self._plan(True)
        kinds = [o["field"] for o in built["operations"]]
        self.assertTrue(kinds[0].startswith("visible."))

    def test_a_visible_block_needs_no_unhide(self):
        built = self._plan(False)
        self.assertEqual([o for o in built["operations"]
                          if o["field"].startswith("visible.")], [])

    def test_a_pruned_block_is_not_unhidden(self):
        """Only blocks that receive content."""
        document = {"source": "steam",
                    "source_url": "https://store.steampowered.com/app/1/",
                    "rights_confirmed": True, "fields": {"title": "T"}}
        structure = {"pages": [{"_id": "p", "blocks": [
            {"_id": "lg", "module": "leadGameSales",
             "values": {"title": {"id": "L:t"}}},
            {"_id": "f", "module": "faq", "hidden": True}]}]}
        built = plan.build(document, structure)[0]
        self.assertEqual([o for o in built["operations"]
                          if o["field"].startswith("visible.")], [])
