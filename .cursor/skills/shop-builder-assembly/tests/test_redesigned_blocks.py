from __future__ import annotations

import contextlib
import copy
import io
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import apply_plan  # noqa: E402
import apply_style  # noqa: E402
import redesigned_blocks  # noqa: E402
import render_plan  # noqa: E402
import verify_structure  # noqa: E402
from validate_shop_brief import VERIFIED_BLOCK_MODULES  # noqa: E402

PREFIX = "_site-builder-classic_"
EXAMPLE_BRIEF = ROOT / "examples" / "mobile-single-page.json"
# A masked export of a real site with `features.redesign` on: the page `add-page` makes
# by default, at "/", and the page its `topup` type makes, at "/type-topup".
# tests/mask_site_export.py makes it.
FIXTURE = json.loads(
    (ROOT / "tests" / "fixtures" / "redesigned-site.json").read_text(encoding="utf-8")
)
DEFAULT_PAGE, STORE_PAGE = "/", "/type-topup"


def fixture_page(path: str) -> dict:
    return copy.deepcopy(
        next(
            page
            for page in FIXTURE["structure"]["pages"]
            if render_plan.page_path(page) == path
        )
    )


def redesigned_site(brief: dict, source: str = DEFAULT_PAGE) -> dict:
    """The fixture's site as the brief's project, with one page at "/": the page the
    fixture has at ``source``."""
    site = copy.deepcopy(FIXTURE["structure"])
    page = fixture_page(source)
    page["path"] = {"pathSegment": "/", "type": "static"}
    site["pages"] = [page]
    site["blocks"] = [block["_id"] for block in page["blocks"]]
    site["domain"] = brief["site"]["slug"]
    site["merchantId"] = brief["project"]["merchant_id"]
    site["projectId"] = brief["project"]["project_id"]
    return site


def names(page: dict) -> list[str]:
    """The page's blocks by their own names, without the prefix."""
    return [
        str(render_plan.effective_module(block)).replace(PREFIX, "")
        for block in page["blocks"]
    ]


def block_ids(site: dict) -> frozenset:
    return frozenset(block["_id"] for page in site["pages"] for block in page["blocks"])


def stores(page: dict) -> list[dict]:
    return [
        block
        for block in page["blocks"]
        if render_plan.effective_module(block) == redesigned_blocks.STORE
    ]


def apply_patch(target: dict, patch: dict) -> None:
    *parents, last = patch["path"]
    node = target
    for key in parents:
        node = node[key]
    if patch["op"] == "remove":
        del node[last]
    else:
        node[last] = patch["value"]


class RedesignCli:
    """An `xsolla` stand-in for a redesign site. `add-page` seeds what Shop Builder
    seeds there (the fixture's pages), and the writes assembly makes are applied."""

    def __init__(self, brief: dict, redesign: bool = True) -> None:
        self.project = brief["project"]
        self.redesign = redesign
        self.landing: dict | None = None
        self.calls: list[tuple[str, ...]] = []

    def writes(self, command: str) -> list[dict]:
        return [
            dict(zip(call[2::2], call[3::2])) for call in self.calls if call[1:2] == (command,)
        ]

    def create(self, slug: str) -> None:
        self.landing = {
            "_id": "landing-1",
            "domain": slug,
            "merchantId": self.project["merchant_id"],
            "projectId": self.project["project_id"],
            "type": None,
            "published": None,
            "languages": ["en-US"],
            "features": {"redesign": self.redesign},
            "pages": [],
            "layouts": [],
            "blocks": [],
        }

    def __call__(self, *args: str) -> object:
        self.calls.append(args)
        if args == ("config", "list"):
            return {
                "ok": True,
                "data": {
                    "merchant_id": self.project["merchant_id"],
                    "project_id": self.project["project_id"],
                    "sandbox": False,
                },
            }
        command = args[1]
        options = dict(zip(args[2::2], args[3::2]))
        if command == "list-websites":
            return {"ok": True, "data": [self.landing] if self.landing else []}
        if command == "create-website":
            self.create(options["--slug"])
            return {"ok": True, "data": copy.deepcopy(self.landing)}
        if command == "get-structure":
            return {"ok": True, "data": copy.deepcopy(self.landing)}
        if command == "set-landing-type":
            self.landing["type"] = options["--type"]
            return {"ok": True}
        if command == "add-language":
            self.landing["languages"].append(options["--language"])
            return {"ok": True}
        if command == "add-page":
            page_type = options.get("--type", "sellingpage")
            source = {"sellingpage": DEFAULT_PAGE, "topup": STORE_PAGE}[page_type]
            number = len(self.landing["pages"]) + 1
            blocks = fixture_page(source)["blocks"]
            for block in blocks:
                block["_id"] = f"{block['_id']}-p{number}"
            self.landing["pages"].append(
                {
                    "_id": f"page-{number}",
                    "name": options["--name"],
                    "path": {"pathSegment": options["--path"], "type": "static"},
                    "type": page_type,
                    "blocks": blocks,
                }
            )
            self.landing["blocks"] += [block["_id"] for block in blocks]
            return {"ok": True}
        if command == "update-block":
            for change in json.loads(options["--data"]).values():
                targets = (
                    self.landing["pages"]
                    if change["type"] == "page"
                    else [block for page in self.landing["pages"] for block in page["blocks"]]
                )
                target = next(item for item in targets if item["_id"] == change["id"])
                for patch in change["patches"]:
                    apply_patch(target, patch)
            return {"ok": True, "data": {}}
        if command == "move-block":
            page = next(
                page for page in self.landing["pages"] if page["_id"] == options["--page-id"]
            )
            block = page["blocks"].pop(int(options["--source"]))
            page["blocks"].insert(int(options["--destination"]), block)
            return {"ok": True}
        raise AssertionError(f"unexpected CLI call: {args}")


class RedesignedBlockNamesTests(unittest.TestCase):
    def test_each_redesigned_block_stands_for_a_native_module(self) -> None:
        expected = {
            "header": "header",
            "lead": "leadGameSales",
            "lead-gs": "leadGameSales",
            "store": "newStore",
            "promocode": "promocodes",
            "faq": "faq",
            "footer-v3": "footer",
            "game-packs": "packs",
            "description": "description",
            "card-grid": "bento-grid",
            "gallery": "gallery",
            "system-requirements": "requirements",
            "news": "news",
            "reward-chains": "rewards",
            "sidebar": "sidebar",
            "sb-offer-chain": "sb-offer-chain",
            "sb-daily-reward": "sb-daily-reward",
            "offerwall": "offerwall-block",
        }
        self.assertEqual(expected, redesigned_blocks.NATIVE_MODULES)
        for name, native in expected.items():
            with self.subTest(name=name):
                self.assertEqual(native, redesigned_blocks.logical_name(PREFIX + name))
                self.assertTrue(redesigned_blocks.has_twin(native))
        # Only the two heroes share a native module.
        shared = [n for n in set(expected.values()) if list(expected.values()).count(n) > 1]
        self.assertEqual(["leadGameSales"], shared)

    def test_mapped_names_are_modules_the_brief_knows(self) -> None:
        # The brief and the presets keep native names, so a redesigned block must map to
        # a name they can use. These three come with a site template and no preset adds
        # them.
        template_only = {"sidebar", "sb-daily-reward", "offerwall-block"}
        self.assertEqual(
            set(),
            set(redesigned_blocks.NATIVE_MODULES.values())
            - VERIFIED_BLOCK_MODULES
            - template_only,
        )

    def test_other_names_stay_as_they_are(self) -> None:
        for name in (
            "header",
            "newStore",
            "federated",
            "sb-offer-chain",
            "social-quests",
            "_quest-platform_quests-block",
            PREFIX + "not-a-known-block",
            PREFIX,
            "",
            None,
            7,
        ):
            with self.subTest(name=name):
                self.assertEqual(name, redesigned_blocks.logical_name(name))
        for native in ("hero", "html", "fast-login", "social-quests"):
            self.assertFalse(redesigned_blocks.has_twin(native))


class RedesignedSiteFixtureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pages = {
            render_plan.page_path(page): page for page in FIXTURE["structure"]["pages"]
        }

    def test_the_fixture_holds_nothing_from_the_real_site(self) -> None:
        dumped = json.dumps(FIXTURE)
        links = set(re.findall(r"https?://[^\s\"\\]+", dumped))
        self.assertEqual(
            set(), {link for link in links if not link.startswith("https://example.invalid/")}
        )
        self.assertNotIn("@", dumped)
        site = FIXTURE["structure"]
        self.assertEqual(
            ("redesigned-site", "merchant-id", "project-id"),
            (site["domain"], site["merchantId"], site["projectId"]),
        )

    def test_the_site_is_a_redesign_site_with_no_layout(self) -> None:
        site = FIXTURE["structure"]
        self.assertIs(True, site["features"]["redesign"])
        self.assertEqual([], site["layouts"])

    def test_the_pages_are_seeded_as_add_page_does_today(self) -> None:
        self.assertEqual(
            "header lead-gs description game-packs game-packs card-grid card-grid "
            "card-grid gallery game-packs system-requirements faq footer-v3".split(),
            names(self.pages[DEFAULT_PAGE]),
        )
        self.assertEqual(
            "header lead store sb-daily-reward sb-offer-chain store store reward-chains "
            "store store promocode social-quests offerwall faq lead footer-v3".split(),
            names(self.pages[STORE_PAGE]),
        )
        sections = [
            redesigned_blocks.store_section_count(b) for b in stores(self.pages[STORE_PAGE])
        ]
        self.assertEqual([1, 3, 1, 1, 1], sections)
        # The plan warns from this number before the page exists.
        self.assertEqual(render_plan.REDESIGNED_STORE_SECTIONS, max(sections))

    def test_every_redesigned_block_in_the_fixture_is_in_the_name_table(self) -> None:
        for path, page in self.pages.items():
            for block in page["blocks"]:
                name = render_plan.effective_module(block)
                if redesigned_blocks.is_redesigned(name):
                    with self.subTest(page=path, name=name):
                        self.assertNotEqual(name, redesigned_blocks.logical_name(name))

    def test_every_text_reference_finds_its_text(self) -> None:
        for path, page in self.pages.items():
            texts = FIXTURE["localization"]["pages"][page["_id"]]["texts"]
            for block in page["blocks"]:
                resources = block.get("values", {}).get("resources") or {}
                references = [
                    value["texts"]["id"]
                    for value in resources.get("localizedValues", {}).values()
                ] + [
                    action["value"]["text"]["id"]
                    for action in resources.get("components.button-action", {}).values()
                    if isinstance(action["value"].get("text"), dict)
                ]
                for text_id in references:
                    with self.subTest(page=path, block=block["_id"], text=text_id):
                        self.assertIn(text_id, texts)


class RedesignedPlanTests(unittest.TestCase):
    def setUp(self) -> None:
        self.brief = json.loads(EXAMPLE_BRIEF.read_text(encoding="utf-8"))

    def test_a_new_site_plan_says_what_assembly_does_on_redesigned_blocks(self) -> None:
        self.assertIn(render_plan.REDESIGNED_SITE, render_plan.build_plan(self.brief)["warnings"])

    def test_the_render_no_longer_stops_on_a_redesigned_page(self) -> None:
        site = redesigned_site(self.brief)
        plan = render_plan.build_plan(self.brief, site, block_ids(site))
        render_plan.require_header_source(plan["pages"], site)
        self.assertNotIn("site_header", plan["pages"][0])
        self.assertIn(render_plan.REDESIGNED_SITE, plan["warnings"])

    def test_a_block_the_page_lacks_is_left_out_with_the_reason(self) -> None:
        # The default page has no store, and a redesigned store can't be added.
        site = redesigned_site(self.brief)
        plan = render_plan.build_plan(self.brief, site, block_ids(site))
        page = plan["pages"][0]
        self.assertEqual(["header", "leadGameSales", "footer"], page["blocks"])
        self.assertIn(
            {
                "path": "/",
                "module": "newStore",
                "reason": render_plan.NO_REDESIGNED_BLOCK,
                "action": "omit",
            },
            plan["omissions"],
        )
        kept = [b for b in page["current_blocks"] if b["block_id"] not in
                {r["block_id"] for r in page["removals"]}]
        self.assertEqual(
            [PREFIX + "header", PREFIX + "lead-gs", PREFIX + "footer-v3"],
            [block["module"] for block in kept],
        )

    def test_a_store_page_keeps_its_hero_and_the_store_with_the_most_sections(self) -> None:
        site = redesigned_site(self.brief, STORE_PAGE)
        plan = render_plan.build_plan(self.brief, site, block_ids(site))
        page = plan["pages"][0]
        self.assertEqual(["header", "leadGameSales", "newStore", "footer"], page["blocks"])
        self.assertEqual([], [o for o in plan["omissions"] if o["module"] == "newStore"])
        removed = {removal["block_id"]: removal for removal in page["removals"]}
        kept = [block for block in site["pages"][0]["blocks"] if block["_id"] not in removed]
        self.assertEqual(["header", "lead", "store", "footer-v3"], names({"blocks": kept}))
        self.assertEqual(3, redesigned_blocks.store_section_count(kept[2]))
        self.assertEqual(
            ["duplicate module"] * 5,
            [
                removed[block["_id"]]["reason"]
                for block in site["pages"][0]["blocks"]
                if block["_id"] in removed
                and names({"blocks": [block]})[0] in ("store", "lead")
            ],
        )
        # A removal is recorded under the block's own name, which apply checks.
        self.assertEqual(
            {PREFIX + "store"},
            {r["module"] for r in page["removals"] if "store" in r["module"]},
        )

    def test_a_new_page_lists_the_blocks_its_page_type_comes_with(self) -> None:
        store = {"blocks": ["header", "leadGameSales", "newStore", "footer"]}
        about = {"blocks": ["header", "description", "footer"]}
        self.assertEqual("topup", render_plan.new_page_type(True, store))
        self.assertIsNone(render_plan.new_page_type(True, about))
        self.assertIsNone(render_plan.new_page_type(False, store))
        # One entry per block that goes: four of the five stores, one of the two heroes.
        self.assertEqual(
            "sb-daily-reward sb-offer-chain newStore newStore rewards newStore newStore "
            "promocodes social-quests offerwall-block faq leadGameSales".split(),
            render_plan.template_removals(store, redesign=True),
        )
        self.assertEqual(
            "leadGameSales packs packs bento-grid bento-grid bento-grid gallery packs "
            "requirements faq".split(),
            render_plan.template_removals(about, redesign=True),
        )
        # A site without the redesign: the native page, as before.
        self.assertEqual(
            [m for m in render_plan.NEW_PAGE_TEMPLATE if m not in store["blocks"]],
            render_plan.template_removals(store),
        )
        # Both lists are what the fixture's pages really have, block by block.
        for template, path in (
            (render_plan.REDESIGNED_PAGE_TEMPLATE, DEFAULT_PAGE),
            (render_plan.REDESIGNED_STORE_PAGE_TEMPLATE, STORE_PAGE),
        ):
            self.assertEqual(
                template,
                [render_plan.logical_module(block) for block in fixture_page(path)["blocks"]],
            )

    def test_a_page_to_be_made_leaves_out_what_its_page_type_comes_without(self) -> None:
        def planned(structure: dict | None, pages: list[dict]) -> dict:
            brief = copy.deepcopy(self.brief)
            brief["content"] = {**brief.get("content", {}), "gallery": ["art.png"],
                                "page_overrides": pages}
            return render_plan.build_plan(brief, structure)

        store = {"name": "Home", "path": "/",
                 "blocks": ["header", "leadGameSales", "newStore", "gallery", "footer"]}
        about = {"name": "About", "path": "/about", "blocks": ["header", "gallery", "footer"]}
        left_out = {"path": "/", "module": "gallery",
                    "reason": render_plan.NO_BLOCK_IN_PAGE_TYPE, "action": "omit"}
        # A new site: the store page's type has no gallery; the default page has one.
        plan = planned(None, [store, about])
        self.assertEqual(
            [["header", "leadGameSales", "newStore", "footer"], ["header", "gallery", "footer"]],
            [page["blocks"] for page in plan["pages"]],
        )
        self.assertEqual([left_out], [o for o in plan["omissions"] if o["module"] == "gallery"])
        # A redesign site that doesn't have the page yet: the same.
        site = redesigned_site(self.brief)
        site["pages"] = []
        self.assertIn(left_out, planned(site, [store])["omissions"])
        # A site without the redesign makes a native page, where the block can be added.
        site["features"] = {"redesign": False}
        self.assertEqual(store["blocks"], planned(site, [store])["pages"][0]["blocks"])

    def test_a_template_site_keeps_its_redesigned_blocks(self) -> None:
        # A site made from a template: the header and footer sit in the site layout.
        # Before, every redesigned block on the page was planned for removal.
        site = redesigned_site(self.brief, STORE_PAGE)
        page = site["pages"][0]
        page["blocks"] = page["blocks"][1:-1]
        site["layouts"] = ["layout-1"]
        site["blocks"] = [block["_id"] for block in page["blocks"]] + [
            "layout-header", "layout-footer", "layout-1",
        ]
        modules = {"layout-1": "common-layout", "layout-header": "federated",
                   "layout-footer": "federated"}
        plan = render_plan.build_plan(self.brief, site, module_of=modules.get)
        render_plan.require_header_source(plan["pages"], site)
        planned = plan["pages"][0]
        self.assertEqual("layout", planned["site_header"])
        self.assertEqual(
            ["leadGameSales", "sb-daily-reward", "sb-offer-chain", "newStore", "rewards",
             "promocodes", "faq"],
            planned["blocks"],
        )
        removed = {removal["block_id"] for removal in planned["removals"]}
        kept = [block for block in page["blocks"] if block["_id"] not in removed]
        self.assertEqual(
            ["lead", "sb-daily-reward", "sb-offer-chain", "store", "reward-chains",
             "promocode", "faq"],
            names({"blocks": kept}),
        )
        self.assertEqual(3, redesigned_blocks.store_section_count(kept[3]))

    def test_only_several_redesigned_stores_change_which_block_is_kept(self) -> None:
        native = [{"_id": "a", "module": "newStore"}, {"_id": "b", "module": "newStore"}]
        self.assertEqual({}, render_plan.preferred_blocks(native))
        self.assertEqual({}, render_plan.preferred_blocks(fixture_page(DEFAULT_PAGE)["blocks"]))
        page = fixture_page(STORE_PAGE)
        self.assertEqual(
            {"newStore": stores(page)[1]["_id"]}, render_plan.preferred_blocks(page["blocks"])
        )

    def with_groups(self, count: int) -> dict:
        brief = copy.deepcopy(self.brief)
        brief["catalog"]["groups"] = [
            {"external_id": f"group-{number}", "type": "virtual_good", "placement": "primary"}
            for number in range(1, count + 1)
        ]
        return brief

    def test_the_plan_warns_when_the_store_cannot_take_its_catalog_groups(self) -> None:
        # The store a store page comes with has three sections, and assembly can't add
        # one. The plan must say so while it is still a proposal: the run finds out
        # only after it has removed the page's other blocks.
        warning = (
            "The store on / won't be linked to the catalog: it has 3 section(s) and the "
            "plan has 4; assembly can't add a section to it. Plan fewer catalog groups, or "
            "set the store's sections in the Editor after the build."
        )
        four = self.with_groups(4)
        first = render_plan.build_plan(four)
        self.assertIn(warning, first["warnings"])
        # The render after the page is made says the same, word for word, so the yes
        # that saw the warning still covers it.
        site = redesigned_site(four, STORE_PAGE)
        second = render_plan.build_plan(four, site, block_ids(site))
        self.assertIn(warning, second["warnings"])
        self.assertEqual([], [w for w in second["warnings"] if w not in first["warnings"]])
        # Three groups fit, on a new site and on the page as made.
        three = self.with_groups(3)
        for plan in (
            render_plan.build_plan(three),
            render_plan.build_plan(three, site, block_ids(site)),
        ):
            self.assertEqual([], [w for w in plan["warnings"] if "linked to the catalog" in w])

    def test_the_warning_reads_the_store_the_page_keeps(self) -> None:
        # An existing page with one store of one section: two groups don't fit.
        site = redesigned_site(self.brief, STORE_PAGE)
        page = site["pages"][0]
        small = stores(page)[0]
        page["blocks"] = [b for b in page["blocks"] if b is small or b not in stores(page)]
        plan = render_plan.build_plan(self.with_groups(2), site)
        self.assertIn(
            "The store on / won't be linked to the catalog: it has 1 section(s) and the "
            "plan has 2; assembly can't add a section to it. Plan fewer catalog groups, or "
            "set the store's sections in the Editor after the build.",
            plan["warnings"],
        )
        # A store with another shape is named too.
        small["values"]["internalBlockValues"]["storeSections"]["ids"] = "0"
        plan = render_plan.build_plan(self.with_groups(1), site)
        self.assertTrue(
            any(redesigned_blocks.UNKNOWN_STORE in w for w in plan["warnings"]), plan["warnings"]
        )
        # A native store takes any number of sections.
        native = {"_id": "landing-1", "layouts": [], "blocks": ["h", "s", "f"], "pages": [{
            "_id": "page-1", "name": "Home", "path": "/", "blocks": [
                {"_id": "h", "module": "header"}, {"_id": "s", "module": "newStore"},
                {"_id": "f", "module": "footer"}]}]}
        plan = render_plan.build_plan(self.with_groups(6), native)
        self.assertEqual([], [w for w in plan["warnings"] if "linked to the catalog" in w])

    def test_a_yes_given_without_the_note_does_not_cover_a_redesigned_site(self) -> None:
        site = redesigned_site(self.brief, STORE_PAGE)
        plan = render_plan.build_plan(self.brief, site, block_ids(site))
        report = {
            "approved_confirmation_id": "sha256:approved",
            "slug": plan["target"]["slug"],
            "landing_id": site["_id"],
            "created_blocks": {"/": sorted(block_ids(site))},
        }
        approved = {**copy.deepcopy(plan), "confirmation_id": "sha256:approved"}
        self.assertEqual([], render_plan.approval_changes(approved, plan, report))
        approved["warnings"].remove(render_plan.REDESIGNED_SITE)
        self.assertEqual(
            [
                "the site is made of Shop Builder's redesigned blocks, which the approved "
                "plan didn't say"
            ],
            render_plan.approval_changes(approved, plan, report),
        )


class RedesignedStoreTests(unittest.TestCase):
    """The store's catalog sections, on the store the fixture's store page keeps."""

    SECTIONS = [
        {"external_id": "gems", "type": "virtual_currency", "layout": "horizontal"},
        {"external_id": "skins", "type": "virtual_good", "layout": "vertical"},
    ]

    def setUp(self) -> None:
        self.store = stores(fixture_page(STORE_PAGE))[1]

    def patched(self, sections: list[dict]) -> dict:
        store = copy.deepcopy(self.store)
        for patch in redesigned_blocks.store_section_patches(store, sections):
            apply_patch(store, patch)
        return store

    def test_sections_read_like_the_plan_lists_them(self) -> None:
        self.assertEqual(
            [
                ("__test__/virtual_good", "virtual_good", "vertical"),
                ("__test__/virtual_currency", "virtual_good", "vertical"),
                ("__test__/virtual_good-free", "virtual_good", "horizontal"),
            ],
            redesigned_blocks.store_sections(self.store),
        )

    def test_patches_point_the_first_sections_at_the_plan_and_drop_the_rest(self) -> None:
        self.assertIsNone(redesigned_blocks.store_problem(self.store, self.SECTIONS))
        store = self.patched(self.SECTIONS)
        self.assertEqual(
            [("gems", "virtual_currency", "horizontal"), ("skins", "virtual_good", "vertical")],
            redesigned_blocks.store_sections(store),
        )
        sections = store["values"]["internalBlockValues"]["storeSections"]
        self.assertEqual(sorted(sections["ids"]), sorted(sections["entities"]))
        groups = store["values"]["resources"]["store-group"]
        self.assertEqual(
            {"groupExternalId": "gems", "type": "virtual-currency-pack"},
            groups[sections["entities"][sections["ids"][0]]["group"]],
        )
        # Everything else in the block stays as Shop Builder made it.
        before, after = copy.deepcopy(self.store), copy.deepcopy(store)
        for block in (before, after):
            del block["values"]["internalBlockValues"]["storeSections"]
            del block["values"]["resources"]["store-group"]
        self.assertEqual(before, after)

    def test_a_store_that_already_matches_gets_no_patch(self) -> None:
        self.assertEqual(
            [], redesigned_blocks.store_section_patches(self.patched(self.SECTIONS), self.SECTIONS)
        )

    def test_more_sections_than_the_store_has_is_a_problem_not_a_partial_write(self) -> None:
        four = self.SECTIONS + self.SECTIONS
        self.assertIn(
            "it has 3 section(s) and the plan has 4",
            redesigned_blocks.store_problem(self.store, four),
        )

    def test_a_store_with_another_shape_is_not_written(self) -> None:
        def record(store: dict) -> None:  # the shape an older block version had
            sections = store["values"]["internalBlockValues"]["storeSections"]
            sections["ids"] = {key: True for key in sections["ids"]}

        def no_group(store: dict) -> None:
            sections = store["values"]["internalBlockValues"]["storeSections"]
            del store["values"]["resources"]["store-group"][
                sections["entities"][sections["ids"][0]]["group"]
            ]

        def shared_group(store: dict) -> None:
            sections = store["values"]["internalBlockValues"]["storeSections"]
            first, second = (sections["entities"][key] for key in sections["ids"][:2])
            second["group"] = first["group"]

        for change in (record, no_group, shared_group):
            with self.subTest(change=change.__name__):
                store = copy.deepcopy(self.store)
                change(store)
                self.assertEqual(
                    redesigned_blocks.UNKNOWN_STORE,
                    redesigned_blocks.store_problem(store, self.SECTIONS),
                )
                self.assertEqual([], redesigned_blocks.store_sections(store))
        self.assertEqual(
            "assembly doesn't know the item type for game_key",
            redesigned_blocks.store_problem(
                self.store, [{"external_id": "keys", "type": "game_key", "layout": "vertical"}]
            ),
        )


class RedesignedApplyTests(unittest.TestCase):
    """The writers of apply_plan.py against the fake site."""

    def setUp(self) -> None:
        self.brief = json.loads(EXAMPLE_BRIEF.read_text(encoding="utf-8"))
        self.cli = RedesignCli(self.brief)
        self.cli.create(self.brief["site"]["slug"])
        patcher = mock.patch.object(apply_plan, "run_json", side_effect=self.cli)
        patcher.start()
        self.addCleanup(patcher.stop)

    def seed(self, page_type: str | None = "topup") -> dict:
        self.cli("shopbuilder", "add-page", "--name", "Home", "--path", "/",
                 *(("--type", page_type) if page_type else ()))
        self.cli.calls.clear()
        return self.cli.landing["pages"][0]

    def plan(self, sections: list[dict]) -> dict:
        return {
            "catalog_sections": sections,
            "pages": [{"path": "/", "blocks": ["header", "newStore", "footer"]}],
        }

    def test_a_store_page_of_a_redesign_site_is_made_with_the_topup_type(self) -> None:
        pages = [
            {"name": "Home", "path": "/", "blocks": ["header", "leadGameSales", "footer"]},
            {"name": "Store", "path": "/store", "blocks": ["header", "newStore", "footer"]},
        ]
        self.assertEqual(["/", "/store"], apply_plan.add_missing_pages("shop", pages))
        self.assertEqual(
            [None, "topup"], [call.get("--type") for call in self.cli.writes("add-page")]
        )

    def test_a_site_without_the_redesign_gets_no_page_type(self) -> None:
        self.cli.landing["features"] = {"redesign": False}
        page = {"name": "Store", "path": "/store", "blocks": ["header", "newStore", "footer"]}
        apply_plan.add_missing_pages("shop", [page])
        self.assertEqual([None], [call.get("--type") for call in self.cli.writes("add-page")])

    def test_catalog_sections_are_set_on_a_redesigned_store_and_read_back(self) -> None:
        page = self.seed()
        page["blocks"] = [page["blocks"][0], stores(page)[1], page["blocks"][-1]]
        sections = [{"external_id": "gems", "type": "virtual_currency", "layout": "vertical"}]
        result = apply_plan.wire_catalog_sections("shop", "landing-1", self.plan(sections))
        self.assertEqual([("gems", "virtual_currency", "vertical", True)], result[0]["sections"])
        self.assertEqual(
            [("gems", "virtual_currency", "vertical")],
            redesigned_blocks.store_sections(self.cli.landing["pages"][0]["blocks"][1]),
        )
        self.assertEqual(1, len(self.cli.writes("update-block")))
        # A second run finds nothing to change.
        apply_plan.wire_catalog_sections("shop", "landing-1", self.plan(sections))
        self.assertEqual(1, len(self.cli.writes("update-block")))

    def test_a_store_that_cannot_take_the_sections_is_left_alone_and_reported(self) -> None:
        page = self.seed()
        page["blocks"] = [page["blocks"][0], stores(page)[0], page["blocks"][-1]]
        before = copy.deepcopy(page["blocks"][1])
        sections = [
            {"external_id": "gems", "type": "virtual_currency", "layout": "vertical"},
            {"external_id": "skins", "type": "virtual_good", "layout": "vertical"},
        ]
        result = apply_plan.wire_catalog_sections("shop", "landing-1", self.plan(sections))
        self.assertEqual([], self.cli.writes("update-block"))
        self.assertEqual(before, self.cli.landing["pages"][0]["blocks"][1])
        self.assertNotIn("sections", result[0])
        self.assertEqual(
            "The store on / wasn't linked to the catalog: it has 1 section(s) and the plan "
            "has 2; assembly can't add a section to it. Set its sections in the Editor.",
            result[0]["needs_human"],
        )

    def test_a_planned_store_with_no_store_block_is_an_error(self) -> None:
        self.seed(None)  # the default page has no store
        sections = [{"external_id": "gems", "type": "virtual_currency", "layout": "vertical"}]
        with self.assertRaisesRegex(RuntimeError, "page / has no store block to link"):
            apply_plan.wire_catalog_sections("shop", "landing-1", self.plan(sections))
        self.assertEqual([], self.cli.writes("update-block"))

    def test_a_native_twin_is_never_added_to_a_redesigned_page(self) -> None:
        page = self.seed(None)
        plan = {
            "name": "Home",
            "path": "/",
            "blocks": ["header", "leadGameSales", "newStore", "footer"],
            "removals": [
                {"block_id": block["_id"], "module": render_plan.effective_module(block)}
                for block in page["blocks"][2:-1]
            ],
        }
        with self.assertRaisesRegex(RuntimeError, "has no newStore block; render the plan again"):
            apply_plan.reconcile_page("shop", "landing-1", plan)
        self.assertEqual([], self.cli.writes("add-block"))


class RedesignedNewSiteTests(unittest.TestCase):
    """A new site, both runs under one yes, through apply_plan.main()."""

    def setUp(self) -> None:
        self.use("mobile-single-page")

    def use(self, example: str, groups: int | None = None) -> None:
        """Start a new site from one of the example briefs, with ``groups`` catalog
        groups when given."""
        self.brief = json.loads(
            (ROOT / "examples" / f"{example}.json").read_text(encoding="utf-8")
        )
        if groups is not None:
            self.brief["catalog"]["groups"] = [
                {"external_id": f"group-{n}", "type": "virtual_good", "placement": "primary"}
                for n in range(1, groups + 1)
            ]
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.approved = apply_plan.build_plan(self.brief, can_create_layout=False)
        self.approved_path = self.root / "approved-plan.json"
        self.approved_path.write_text(json.dumps(self.approved), encoding="utf-8")
        self.brief_path = self.root / "brief.json"
        self.brief_path.write_text(json.dumps(self.brief), encoding="utf-8")
        self.cli = RedesignCli(self.brief)

    def apply(self, *extra: str) -> tuple[int, dict | None, str]:
        argv = [
            "apply_plan.py",
            str(self.brief_path),
            "--approved-plan",
            str(self.approved_path),
            "--confirmation-id",
            self.approved["confirmation_id"],
            *extra,
        ]
        backup = copy.deepcopy(self.cli.landing)
        stdout, stderr = io.StringIO(), io.StringIO()
        with (
            mock.patch.dict(apply_plan.RUN_AUTH, {"logged_in": False, "context": None}),
            mock.patch.object(sys, "argv", argv),
            mock.patch.object(apply_plan, "run_preflight"),
            mock.patch.object(apply_plan, "cli_can_create_layout", return_value=False),
            mock.patch.object(apply_plan, "run_json", side_effect=self.cli),
            mock.patch.object(apply_plan, "verified_backup", return_value=True),
            mock.patch.object(apply_plan, "backup_structure", return_value=backup),
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            code = apply_plan.main()
        report = json.loads(stdout.getvalue()) if stdout.getvalue().strip() else None
        return code, report, stderr.getvalue()

    def build(self) -> dict:
        code, first, stderr = self.apply()
        self.assertEqual(0, code, stderr)
        self.assertEqual("bootstrap-complete", first["status"])
        run_report = self.root / "run1-report.json"
        run_report.write_text(json.dumps(first), encoding="utf-8")
        code, second, stderr = self.apply(
            "--run-report", str(run_report), "--backup-dir", str(self.root)
        )
        self.assertEqual(0, code, stderr)
        return second

    def test_the_build_goes_through_both_runs_under_one_yes(self) -> None:
        report = self.build()
        self.assertEqual("implemented-phases-applied", report["status"])
        self.assertEqual(self.approved["confirmation_id"], report["approved_confirmation_id"])
        self.assertEqual(["topup"], [call.get("--type") for call in self.cli.writes("add-page")])
        page = self.cli.landing["pages"][0]
        self.assertEqual(["header", "lead", "store", "footer-v3"], names(page))
        self.assertEqual(
            [("__all__", "virtual_currency", "vertical")],
            redesigned_blocks.store_sections(page["blocks"][2]),
        )
        self.assertEqual([], self.cli.writes("add-block"))
        self.assertEqual([], self.cli.writes("create-block"))

    def test_every_preset_builds_under_one_yes(self) -> None:
        # The first plan must already leave out what the pages will lack: a section
        # that disappears in the second render would need a new yes, with the site and
        # its pages already made.
        for example in ("mobile-single-page", "pc-multi-page", "live-service-events"):
            with self.subTest(example=example):
                self.use(example)
                report = self.build()
                self.assertEqual("implemented-phases-applied", report["status"])
                built = {
                    render_plan.page_path(page): [
                        render_plan.logical_module(block) for block in page["blocks"]
                    ]
                    for page in self.cli.landing["pages"]
                }
                self.assertEqual(
                    {page["path"]: page["blocks"] for page in self.approved["pages"]}, built
                )
                # The plan shown for the yes lists as many blocks to remove as the run
                # removed.
                self.assertEqual(
                    {page["path"]: len(page["template_removals"])
                     for page in self.approved["pages"]},
                    {page["path"]: page["removed_blocks"] for page in report["pages"]},
                )

    def test_the_first_plan_leaves_out_what_a_store_page_will_lack(self) -> None:
        self.use("live-service-events")
        events = next(page for page in self.approved["pages"] if page["path"] == "/events")
        self.assertEqual(["header", "leadGameSales", "newStore", "footer"], events["blocks"])
        self.assertIn(
            {
                "path": "/events",
                "module": "description",
                "reason": render_plan.NO_BLOCK_IN_PAGE_TYPE,
                "action": "omit",
            },
            self.approved["omissions"],
        )

    def test_too_many_groups_are_said_before_the_yes_and_the_store_is_left_alone(self) -> None:
        self.use("mobile-single-page", groups=4)
        warning = next(w for w in self.approved["warnings"] if "linked to the catalog" in w)
        self.assertIn("it has 3 section(s) and the plan has 4", warning)
        # The yes saw the warning, so it covers both runs; the store keeps its sections.
        report = self.build()
        self.assertNotIn("catalog_links", report["completed_phases"])
        self.assertEqual(
            [
                "The store on / wasn't linked to the catalog: it has 3 section(s) and the "
                "plan has 4; assembly can't add a section to it. Set its sections in the "
                "Editor.",
                "The header on / keeps the links Shop Builder gave it; set them in the Editor.",
            ],
            sorted(report["needs_human"], reverse=True),
        )
        store = self.cli.landing["pages"][0]["blocks"][2]
        self.assertEqual(
            [("__test__/virtual_good", "virtual_good", "vertical"),
             ("__test__/virtual_currency", "virtual_good", "vertical"),
             ("__test__/virtual_good-free", "virtual_good", "horizontal")],
            redesigned_blocks.store_sections(store),
        )

    def test_the_report_says_what_was_left_for_the_editor(self) -> None:
        report = self.build()
        self.assertEqual(
            ["The header on / keeps the links Shop Builder gave it; set them in the Editor."],
            report["needs_human"],
        )
        self.assertNotIn("navigation", report["completed_phases"])
        self.assertIn("catalog_links", report["completed_phases"])
        self.assertEqual(apply_plan.REDESIGNED_HEADER, report["navigation"][0]["skipped"])

    def test_the_finished_site_passes_verification_and_a_wrong_group_fails(self) -> None:
        report = self.build()
        site = self.cli.landing
        created = render_plan.created_block_ids(report)
        plan = render_plan.build_plan(self.brief, site, created, can_create_layout=False)
        result = verify_structure.verify(plan, site, layout_required=False)
        self.assertEqual([], result["errors"])
        self.assertIn(
            "the header on / is one of Shop Builder's redesigned blocks; its links are set "
            "in the Editor and weren't checked",
            result["warnings"],
        )
        store = site["pages"][0]["blocks"][2]
        sections = store["values"]["internalBlockValues"]["storeSections"]
        group = sections["entities"][sections["ids"][0]]["group"]
        store["values"]["resources"]["store-group"][group]["groupExternalId"] = "another"
        result = verify_structure.verify(plan, site, layout_required=False)
        self.assertTrue(any("catalog sections differ on /" in e for e in result["errors"]))


class RedesignedStyleTests(unittest.TestCase):
    """apply_style.py finds a redesigned block and leaves it alone, with a note."""

    def setUp(self) -> None:
        self.brief = json.loads(EXAMPLE_BRIEF.read_text(encoding="utf-8"))
        self.site = redesigned_site(self.brief)
        self.before = copy.deepcopy(self.site)
        self.where = {"pages": ["/"], "existing_block_ids": []}

    def test_text_buttons_and_questions_are_not_written(self) -> None:
        hero = {**self.where, "module": "leadGameSales", "page_modules": {"/": "leadGameSales"}}
        approved = {
            "copy": {
                "locale": "en-US",
                "texts": [{**hero, "field": "title", "html": "<h1>Hello</h1>"}],
                "buttons": [{**hero, "position": 1, "label": "Play"}],
                "faq": {
                    **self.where,
                    "page_modules": {"/": "faq"},
                    "items": [{"question": "<h4>Q</h4>", "answer": "<p>A</p>"}],
                },
                "seo": [],
            }
        }
        localization = {
            "common": {},
            "pages": {self.site["pages"][0]["_id"]: FIXTURE["localization"]["pages"][
                self.site["pages"][0]["_id"]]},
        }
        with (
            mock.patch.object(apply_style, "localization", return_value=localization),
            mock.patch.object(
                apply_style, "run_json", side_effect=AssertionError("nothing may be written")
            ),
        ):
            results, needs_human, current = apply_style.copy_phase(
                "shop", "landing-1", self.site, approved, block_ids(self.site), None
            )
        self.assertEqual(self.before, current)
        self.assertEqual(["skipped"] * 3, [result["status"] for result in results])
        self.assertEqual(
            [PREFIX + "lead-gs", PREFIX + "lead-gs", PREFIX + "faq"],
            [result["module"] for result in results],
        )
        self.assertEqual(3, len(needs_human))
        self.assertIn(
            "The FAQ block's questions weren't written: it is a federated block, whose "
            "questions assembly doesn't write yet. Set them in the editor.",
            needs_human,
        )

    def test_a_native_looking_text_field_on_a_federated_block_is_not_written(self) -> None:
        # Shop Builder takes any patch to these blocks, and a later block version could
        # carry a field named like a native one. The native writer must still pass.
        hero = self.site["pages"][0]["blocks"][1]
        texts = FIXTURE["localization"]["pages"][self.site["pages"][0]["_id"]]["texts"]
        hero["values"]["title"] = {"enable": True, "id": next(iter(texts))}
        approved = {
            "copy": {
                "locale": "en-US",
                "texts": [
                    {**self.where, "module": "leadGameSales", "field": "title",
                     "html": "<h1>Hello</h1>", "page_modules": {"/": "leadGameSales"}}
                ],
                "buttons": [],
                "faq": None,
                "seo": [],
            }
        }
        localization = {"common": {}, "pages": {self.site["pages"][0]["_id"]: {"texts": texts}}}
        with (
            mock.patch.object(apply_style, "localization", return_value=localization),
            mock.patch.object(
                apply_style, "run_json", side_effect=AssertionError("nothing may be written")
            ),
        ):
            results, needs_human, _ = apply_style.copy_phase(
                "shop", "landing-1", self.site, approved, block_ids(self.site), None
            )
        self.assertEqual(
            [{"block_id": hero["_id"], "module": PREFIX + "lead-gs", "field": "title",
              "status": "skipped", "reason": apply_style.FEDERATED_TEXT}],
            results,
        )
        self.assertEqual(
            ["The _site-builder-classic_lead-gs block's title wasn't written: it is a "
             "federated block, whose text assembly doesn't write yet. Set it in the editor."],
            needs_human,
        )

    def test_an_image_is_not_put_on_a_redesigned_block(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "hero.png").write_bytes(b"png")
            image = {
                **self.where,
                "file": "hero.png",
                "sha256": render_plan.file_sha256(Path(directory) / "hero.png"),
                "module": "leadGameSales",
                "slot": "background",
                "page_modules": {"/": "leadGameSales"},
            }
            uploads = mock.Mock()
            uploads.url.side_effect = AssertionError("nothing may be uploaded")
            with mock.patch.object(
                apply_style, "run_json", side_effect=AssertionError("nothing may be written")
            ):
                results, needs_human = apply_style.images_phase(
                    "shop",
                    "landing-1",
                    self.site,
                    {"images": [image]},
                    block_ids(self.site),
                    Path(directory),
                    uploads,
                )
        self.assertEqual(["skipped"], [result["status"] for result in results])
        self.assertEqual(
            [
                "hero.png wasn't put on the _site-builder-classic_lead-gs block: it is a "
                "federated block, whose wrapper isn't patched."
            ],
            needs_human,
        )


if __name__ == "__main__":
    unittest.main()
