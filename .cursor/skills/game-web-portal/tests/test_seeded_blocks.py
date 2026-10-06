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
STRUCTURE = {"pages": [{"_id": PAGE, "blocks": [
    {"_id": "b1", "module": "faq", "hidden": False, "values": {"title": {"id": "L:t1"}},
     "components": [{"_id": "c1", "question": {"id": "L:q1"}}], "updated": "2026-10-06"},
    {"_id": "b2", "module": "gallery", "hidden": False, "values": {"title": {"id": "L:shared"}},
     "components": []},
]}]}
LOCALIZATION = {
    "common": {"L:shared": {"description": "d", "translations": {"en-US": "<p>Shared</p>"}}},
    "pages": {PAGE: {"texts": {
        "L:t1": {"description": "d", "translations": {"en-US": "<h2>FAQ</h2>"}},
        "L:q1": {"description": "d", "translations": {"en-US": "<p>Q</p>"}},
    }}},
}
TMP = tempfile.TemporaryDirectory()


def tearDownModule() -> None:
    TMP.cleanup()


def write(name: str, value: dict) -> Path:
    path = Path(TMP.name) / name
    path.write_text(json.dumps({"ok": True, "data": value}), encoding="utf-8")
    return path


class SeededBlocksTest(unittest.TestCase):
    def setUp(self):
        self.entry = seeded_blocks.record(STRUCTURE, LOCALIZATION, PAGE)
        self.structure = copy.deepcopy(STRUCTURE)
        self.localization = copy.deepcopy(LOCALIZATION)

    def blocks(self) -> list[dict]:
        return self.structure["pages"][0]["blocks"]

    def check(self) -> dict:
        return seeded_blocks.check(self.structure, self.localization, self.entry)

    def test_record_lists_every_block_on_the_page(self):
        self.assertEqual([(b["_id"], b["module"]) for b in self.entry["seeded_blocks"]],
                         [("b1", "faq"), ("b2", "gallery")])

    def test_an_untouched_page_is_removable(self):
        self.assertEqual([b["_id"] for b in self.check()["untouched"]], ["b1", "b2"])

    def test_regenerated_component_ids_and_timestamps_do_not_count(self):
        self.blocks()[0]["components"][0]["_id"] = "c1-reread"
        self.blocks()[0]["updated"] = "2026-10-07"
        self.assertEqual([b["_id"] for b in self.check()["untouched"]], ["b1", "b2"])

    def test_a_changed_value_is_kept(self):
        self.blocks()[0]["hidden"] = True
        self.assertEqual([b["_id"] for b in self.check()["changed"]], ["b1"])

    def test_a_changed_page_string_is_kept(self):
        self.localization["pages"][PAGE]["texts"]["L:q1"]["translations"]["de-DE"] = "<p>F</p>"
        self.assertEqual([b["_id"] for b in self.check()["changed"]], ["b1"])

    def test_a_changed_shared_string_is_kept(self):
        self.localization["common"]["L:shared"]["translations"]["en-US"] = "<p>New</p>"
        self.assertEqual([b["_id"] for b in self.check()["changed"]], ["b2"])

    def test_a_removed_block_is_gone(self):
        del self.blocks()[1]
        self.assertEqual([b["_id"] for b in self.check()["gone"]], ["b2"])

    def test_an_unknown_page_stops(self):
        with self.assertRaisesRegex(RuntimeError, "not in the structure"):
            seeded_blocks.record(STRUCTURE, LOCALIZATION, "page-2")


class MainTest(unittest.TestCase):
    def run_main(self, *argv: str) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = seeded_blocks.main(list(argv))
        return code, stdout.getvalue(), stderr.getvalue()

    def test_record_then_check_from_cli_output(self):
        structure, localization = write("s.json", STRUCTURE), write("l.json", LOCALIZATION)
        code, out, _ = self.run_main("record", "--structure", str(structure),
                                     "--localization", str(localization), "--page-id", PAGE)
        self.assertEqual(code, 0)
        entry = Path(TMP.name) / "entry.json"
        entry.write_text(out, encoding="utf-8")
        code, out, _ = self.run_main("check", "--structure", str(structure),
                                     "--localization", str(localization),
                                     "--entry", str(entry))
        self.assertEqual((code, len(json.loads(out)["untouched"])), (0, 2))

    def test_record_without_a_page_exits_one(self):
        structure, localization = write("s.json", STRUCTURE), write("l.json", LOCALIZATION)
        code, out, err = self.run_main("record", "--structure", str(structure),
                                       "--localization", str(localization))
        self.assertEqual((code, out), (1, ""))
        self.assertIn("--page-id", err)


if __name__ == "__main__":
    unittest.main()
