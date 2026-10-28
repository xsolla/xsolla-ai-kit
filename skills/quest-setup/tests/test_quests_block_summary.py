"""Tests for scripts/quests_block_summary.py. Never runs the CLI or reaches the network."""
from __future__ import annotations

import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import quests_block_summary as qbs  # noqa: E402

PAGE_ID = "page-1"


def structure(hidden: bool = False) -> dict:
    quests_block = {
        "hidden": hidden,
        "module": "federated",
        "values": {
            "host": "https://cdn.example.com/site-builder-modules/_quest-platform_quests-block/0.1.0/",
            "internalBlockValues": {
                "maxQuests": 3,
                "layout": {"showHeading": True},
                "questIds": ["q-b", "q-a", "q-x"],
                "overrides": {"q-a": {"titleRef": "L:title-a"}},
                "translations": {"heading": "L:head"},
            },
            "resources": {"localizedValues": {
                "L:head": {"texts": {"enable": True, "id": "L:t-head"}},
                "L:title-a": {"texts": {"enable": True, "id": "L:t-title-a"}},
            }},
        },
    }
    return {
        "merchantId": "1",
        "projectId": "2",
        "pages": [{"_id": PAGE_ID, "name": "Main", "blocks": [{"values": {"host": "other"}}, quests_block]}],
    }


LOCALIZATION = {
    "common": {"L:t-head": {"translations": {"en-US": "Daily quests"}}},
    "pages": {PAGE_ID: {"texts": {"L:t-title-a": {"translations": {"en-US": "<p>Win &amp; earn</p>"}}}}},
}
QUESTS = {
    "q-a": {"id": "q-a", "name": "Win 3 matches", "is_public": True},
    "q-b": {"id": "q-b", "name": "Collect 10 crystals", "is_public": False},
}


class SummarizeTest(unittest.TestCase):
    def test_block_fields_and_order(self) -> None:
        [block] = qbs.summarize(structure(), LOCALIZATION, QUESTS)
        self.assertEqual(block["page"], "Main")
        self.assertEqual((block["position"], block["blocks_on_page"]), (2, 2))
        self.assertFalse(block["hidden"])
        self.assertEqual(block["max_quests"], 3)
        self.assertEqual(block["heading"], "Daily quests")
        names = [q["quest_name"] for q in block["quests"]]
        self.assertEqual(names, ["Collect 10 crystals", "Win 3 matches", None])
        self.assertEqual(block["quests"][1]["card_title"], "Win & earn")
        self.assertEqual(block["quests"][1]["overridden"], ["title"])
        self.assertFalse(block["quests"][0]["public"])
        self.assertFalse(block["quests"][2]["found"])

    def test_hidden_and_no_quest_access(self) -> None:
        [block] = qbs.summarize(structure(hidden=True), {}, None)
        self.assertTrue(block["hidden"])
        self.assertIsNone(block["heading"])
        self.assertNotIn("public", block["quests"][0])

    def test_no_quests_block(self) -> None:
        site = {"pages": [{"_id": PAGE_ID, "name": "Main", "blocks": [{"values": {"host": "x"}}]}]}
        self.assertEqual(qbs.summarize(site, LOCALIZATION, QUESTS), [])


class MainTest(unittest.TestCase):
    def run_main(self, runner, fetcher=lambda m, p: QUESTS) -> tuple:
        out = io.StringIO()
        with redirect_stdout(out):
            code = qbs.main(["--slug", "my-test-site", "--environment", "test"], runner=runner, fetcher=fetcher)
        return code, json.loads(out.getvalue())

    def test_reads_only_and_passes_environment(self) -> None:
        calls = []

        def runner(args):
            calls.append(args)
            if args[0] == "get-structure":
                return {"ok": True, "data": structure()}
            return {"ok": True, "data": LOCALIZATION}

        seen = []
        code, result = self.run_main(runner, lambda m, p: seen.append((m, p)) or QUESTS)
        self.assertEqual(code, 0)
        self.assertEqual([c[0] for c in calls], ["get-structure", "get-localization"])
        self.assertTrue(all(c[-2:] == ["--environment", "test"] for c in calls))
        self.assertEqual(seen, [("1", "2")])
        self.assertEqual(result["quest_names"], "resolved")
        self.assertEqual(result["blocks"][0]["heading"], "Daily quests")

    def test_structure_failure(self) -> None:
        code, result = self.run_main(lambda args: {"ok": False})
        self.assertEqual(code, 1)
        self.assertEqual(result, {"ok": False, "error": "structure_read_failed"})

    def test_localization_failure_still_summarizes(self) -> None:
        def runner(args):
            return {"ok": True, "data": structure()} if args[0] == "get-structure" else {"ok": False}

        code, result = self.run_main(runner, lambda m, p: None)
        self.assertEqual(code, 0)
        self.assertEqual(result["quest_names"], "unavailable")
        self.assertIsNone(result["blocks"][0]["heading"])


if __name__ == "__main__":
    unittest.main()
