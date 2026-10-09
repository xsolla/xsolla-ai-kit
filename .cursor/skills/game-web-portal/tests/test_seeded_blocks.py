from __future__ import annotations

import contextlib
import copy
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import seeded_blocks  # noqa: E402

PAGE = "page-1"
STRUCTURE = {"pages": [{"_id": PAGE, "path": "/community", "blocks": [
    {"_id": "b1", "module": "faq", "hidden": False, "values": {"title": {"id": "L:t1"}},
     "components": [{"_id": "c1", "question": {"id": "L:q1"}}], "updated": "2026-10-06"},
    {"_id": "b2", "module": "gallery", "hidden": False, "values": {"title": {"id": "L:shared"}},
     "components": []},
    {"_id": "b3", "module": "packs", "hidden": False, "values": {"columns": 3}},
]}]}
LOCALIZATION = {
    "common": {"L:shared": {"description": "d", "translations": {"en-US": "<p>Shared</p>"}},
               "L:t1": {"description": "d", "translations": {"en-US": "<h2>Common</h2>"}}},
    "pages": {PAGE: {"texts": {
        "L:t1": {"description": "d", "translations": {"en-US": "<h2>FAQ</h2>"}},
        "L:q1": {"description": "d", "translations": {"en-US": "<p>Q</p>"}},
    }}},
}
TARGET = {"merchant_id": 1, "project_id": 2, "landing_id": "landing-1"}
TMP = tempfile.TemporaryDirectory()


def tearDownModule() -> None:
    TMP.cleanup()


def write(name: str, value: dict, envelope: bool = True) -> Path:
    path = Path(TMP.name) / name
    path.write_text(json.dumps({"ok": True, "data": value} if envelope else value),
                    encoding="utf-8")
    return path


def ledger(*entries: dict, ids: dict = TARGET) -> dict:
    return {"steps": [{"id": "storefront", "ids": {**ids, "created_pages": list(entries)}}]}


class SeededBlocksTest(unittest.TestCase):
    def setUp(self):
        self.entry = seeded_blocks.record(STRUCTURE, LOCALIZATION, PAGE)
        self.structure = copy.deepcopy(STRUCTURE)
        self.localization = copy.deepcopy(LOCALIZATION)

    def blocks(self) -> list[dict]:
        return self.structure["pages"][0]["blocks"]

    def check(self) -> dict:
        return seeded_blocks.check(self.structure, self.localization, self.entry)

    def ids(self, status: str) -> list[str]:
        return [b["_id"] for b in self.check()[status]]

    def test_record_lists_the_page_and_every_block_on_it(self):
        self.assertEqual(self.entry["path"], "/community")
        self.assertEqual([(b["_id"], b["module"]) for b in self.entry["seeded_blocks"]],
                         [("b1", "faq"), ("b2", "gallery"), ("b3", "packs")])

    def test_an_untouched_page_is_removable(self):
        self.assertEqual(self.ids("untouched"), ["b1", "b2", "b3"])

    def test_regenerated_component_ids_and_timestamps_do_not_count(self):
        self.blocks()[0]["components"][0]["_id"] = "c1-reread"
        self.blocks()[0]["updated"] = "2026-10-07"
        self.assertEqual(self.ids("untouched"), ["b1", "b2", "b3"])

    def test_a_block_added_after_record_is_never_removable(self):
        self.blocks().append({"_id": "b4", "module": "embed", "values": {}})
        result = self.check()
        self.assertNotIn("b4", [b["_id"] for s in ("untouched", "changed", "gone")
                                for b in result[s]])

    def test_a_changed_hidden_flag_is_kept(self):
        self.blocks()[0]["hidden"] = True
        self.assertEqual(self.ids("changed"), ["b1"])

    def test_a_changed_value_without_strings_is_kept(self):
        self.blocks()[2]["values"]["columns"] = 4
        self.assertEqual(self.ids("changed"), ["b3"])

    def test_a_changed_page_string_is_kept(self):
        self.localization["pages"][PAGE]["texts"]["L:q1"]["translations"]["de-DE"] = "<p>F</p>"
        self.assertEqual(self.ids("changed"), ["b1"])

    def test_a_changed_shared_string_is_kept(self):
        self.localization["common"]["L:shared"]["translations"]["en-US"] = "<p>New</p>"
        self.assertEqual(self.ids("changed"), ["b2"])

    def test_the_page_string_wins_over_a_shared_one_with_the_same_id(self):
        self.localization["common"]["L:t1"]["translations"]["en-US"] = "<h2>Other</h2>"
        self.assertEqual(self.ids("untouched"), ["b1", "b2", "b3"])

    def test_a_string_that_appears_later_marks_the_block_changed(self):
        self.blocks()[2]["values"]["title"] = {"id": "L:new"}
        entry = seeded_blocks.record(self.structure, self.localization, PAGE)
        self.localization["common"]["L:new"] = {"description": "", "translations": {}}
        self.assertEqual(
            [b["_id"] for b in seeded_blocks.check(self.structure, self.localization,
                                                   entry)["changed"]], ["b3"])

    def test_a_removed_block_is_gone(self):
        del self.blocks()[1]
        self.assertEqual(self.ids("gone"), ["b2"])

    def test_a_page_that_no_longer_exists_is_all_gone(self):
        self.structure["pages"] = []
        self.assertEqual(self.ids("gone"), ["b1", "b2", "b3"])

    def test_a_page_missing_from_the_localization_still_records(self):
        entry = seeded_blocks.record(STRUCTURE, {"common": {}, "pages": None}, PAGE)
        self.assertEqual(len(entry["seeded_blocks"]), 3)

    def test_an_unknown_page_cannot_be_recorded(self):
        with self.assertRaisesRegex(RuntimeError, "not in the structure"):
            seeded_blocks.record(STRUCTURE, LOCALIZATION, "page-2")


class LedgerEntryTest(unittest.TestCase):
    def test_finds_the_page_in_the_storefront_step(self):
        entry = {"page_id": PAGE, "seeded_blocks": []}
        self.assertIs(seeded_blocks.ledger_entry(ledger(entry), PAGE, TARGET), entry)

    def test_a_page_without_a_record_is_never_trimmed(self):
        with self.assertRaisesRegex(RuntimeError, "no ledger record"):
            seeded_blocks.ledger_entry(ledger(), PAGE, TARGET)

    def test_a_malformed_record_names_the_fields(self):
        broken = {"page_id": PAGE, "seeded_blocks": [{"_id": "b1"}]}
        with self.assertRaisesRegex(RuntimeError, "_id, module and hash"):
            seeded_blocks.ledger_entry(ledger(broken), PAGE, TARGET)

    def test_another_merchant_project_or_landing_is_never_trimmed(self):
        entry = {"page_id": PAGE, "seeded_blocks": []}
        for key, other in (("merchant_id", 9), ("project_id", 9), ("landing_id", "landing-9")):
            with self.subTest(key), self.assertRaisesRegex(RuntimeError, "never trim"):
                seeded_blocks.ledger_entry(ledger(entry), PAGE, {**TARGET, key: other})

    def test_a_ledger_without_the_target_is_never_trimmed(self):
        entry = {"page_id": PAGE, "seeded_blocks": []}
        with self.assertRaisesRegex(RuntimeError, "never trim"):
            seeded_blocks.ledger_entry(ledger(entry, ids={}), PAGE, TARGET)


class MainTest(unittest.TestCase):
    def run_main(self, *argv: str) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = seeded_blocks.main(list(argv))
        return code, stdout.getvalue(), stderr.getvalue()

    def reads(self) -> list[str]:
        return ["--structure", str(write("s.json", STRUCTURE)),
                "--localization", str(write("l.json", LOCALIZATION)), "--page-id", PAGE]

    def target(self) -> list[str]:
        return ["--merchant-id", "1", "--project-id", "2", "--landing-id", "landing-1"]

    def test_record_then_check_against_the_ledger(self):
        code, out, _ = self.run_main("record", *self.reads())
        self.assertEqual(code, 0)
        path = write("ledger.json", ledger(json.loads(out)), envelope=False)
        code, out, _ = self.run_main("check", *self.reads(), "--ledger", str(path), *self.target())
        self.assertEqual((code, len(json.loads(out)["untouched"])), (0, 3))

    def test_check_without_a_ledger_exits_one(self):
        code, out, err = self.run_main("check", *self.reads(), *self.target())
        self.assertEqual((code, out), (1, ""))
        self.assertIn("--ledger", err)

    def test_check_without_the_target_exits_one(self):
        path = write("ledger.json", ledger(), envelope=False)
        code, out, err = self.run_main("check", *self.reads(), "--ledger", str(path))
        self.assertEqual((code, out), (1, ""))
        self.assertIn("--merchant-id, --project-id, --landing-id", err)

    def test_a_failed_cli_read_is_reported(self):
        failed = write("failed.json", {"ok": False, "error": "HTTP 401"}, envelope=False)
        code, _, err = self.run_main("record", "--structure", str(failed),
                                     "--localization", str(failed), "--page-id", PAGE)
        self.assertEqual(code, 1)
        self.assertIn("HTTP 401", err)


if __name__ == "__main__":
    unittest.main()
