from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import ledger  # noqa: E402

TMP = tempfile.TemporaryDirectory()


def tearDownModule() -> None:
    TMP.cleanup()


def step(**changes: object) -> dict:
    value = {"id": "storefront", "status": "completed", "evidence": ["/community read back"],
             "ids": {"merchant_id": 1}, "updated_at": "2026-10-22T09:00:00Z"}
    value.update(changes)
    return {k: v for k, v in value.items() if v is not ...}


def run(value: object) -> tuple[int, str, str]:
    path = Path(TMP.name) / "onboarding.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = ledger.main(["check", "--ledger", str(path)])
    return code, out.getvalue(), err.getvalue()


class LedgerCheckTest(unittest.TestCase):
    def test_each_contract_status_passes(self):
        for status in ledger.STATUSES:
            with self.subTest(status=status):
                self.assertEqual(ledger.problems({"steps": [step(status=status)]}), [])

    def test_the_contract_lists_exactly_these_statuses(self):
        contract = (ROOT.parent / "shop-plan" / "references" / "onboarding-contract.md")
        table = contract.read_text(encoding="utf-8").split("## Statuses", 1)[1].split("##", 1)[0]
        listed = [line.split("`")[1] for line in table.splitlines() if line.startswith("| `")]
        self.assertEqual(listed, list(ledger.STATUSES))

    def steps_table(self) -> list[list[str]]:
        contract = (ROOT.parent / "shop-plan" / "references" / "onboarding-contract.md")
        text = contract.read_text(encoding="utf-8")
        table = text.split("## Steps and their evidence", 1)[1].split("##", 1)[0]
        return [line.split("|") for line in table.splitlines() if line.startswith("| `")]

    def test_the_contract_defines_exactly_these_steps(self):
        self.assertEqual([row[1].strip(" `") for row in self.steps_table()], list(ledger.STEPS))

    def test_the_skipped_steps_are_the_ones_shop_plan_writes(self):
        by_shop_plan = [row[1].strip(" `") for row in self.steps_table()
                        if row[2].strip() == "`shop-plan`"]
        self.assertEqual(by_shop_plan, list(ledger.SKIPPED))

    def test_each_contract_step_passes(self):
        for step_id in ledger.STEPS:
            with self.subTest(step=step_id):
                self.assertEqual(ledger.problems({"steps": [step(id=step_id)]}), [])

    def test_an_invented_step_fails_and_names_it(self):
        # 2026-10-28 B-3 put the storefront gaps in a step of its own
        gaps = step(id="community_gaps", status="needs_human")
        found = ledger.problems({"steps": [step(), gaps]})
        self.assertEqual(len(found), 1)
        self.assertIn("step 'community_gaps': is not a contract step", found[0])
        self.assertIn("storefront", found[0])
        self.assertIn("evidence", found[0])

    def test_shop_plan_steps_without_ids_evidence_or_updated_at_pass(self):
        # shop-plan's own instructions never name these fields
        for skipped in ledger.SKIPPED:
            with self.subTest(step=skipped):
                bare = step(id=skipped, ids=..., evidence=..., updated_at=...)
                self.assertEqual(ledger.problems({"steps": [bare]}), [])

    def test_the_same_gaps_on_a_step_this_skill_writes_still_fail(self):
        bare = step(ids=..., evidence=..., updated_at=...)
        self.assertEqual(ledger.problems({"steps": [step(id="intake", ids=...), bare]}),
                         ["step 'storefront': evidence must be a list",
                          "step 'storefront': ids must be an object",
                          "step 'storefront': needs updated_at"])

    def test_a_skipped_step_with_a_non_contract_status_passes(self):
        self.assertEqual(ledger.problems({"steps": [step(id="plan", status="partial")]}), [])

    def test_a_step_under_way_without_status_passes(self):
        self.assertEqual(ledger.problems({"steps": [step(status=...)]}), [])

    def test_words_outside_the_contract_fail_and_name_the_step(self):
        # 2026-10-19 offline runs wrote the storefront step as these
        for status in ("partial", "in_progress"):
            with self.subTest(status=status):
                found = ledger.problems({"steps": [step(status=status)]})
                self.assertEqual(len(found), 1)
                self.assertIn("step 'storefront'", found[0])
                self.assertIn(f'"{status}"', found[0])
                self.assertIn("no status key", found[0])

    def test_a_null_status_fails(self):
        self.assertEqual(len(ledger.problems({"steps": [step(status=None)]})), 1)

    def test_a_missing_id_fails_and_names_the_index(self):
        found = ledger.problems({"steps": [step(id="intake"), step(id=...)]})
        self.assertEqual(found, ["steps[1]: needs an id"])

    def test_evidence_must_be_a_list(self):
        self.assertEqual(ledger.problems({"steps": [step(evidence="read back")]}),
                         ["step 'storefront': evidence must be a list"])

    def test_ids_and_updated_at_are_required(self):
        self.assertEqual(ledger.problems({"steps": [step(ids=..., updated_at=...)]}),
                         ["step 'storefront': ids must be an object",
                          "step 'storefront': needs updated_at"])

    def test_steps_must_be_a_list_of_objects(self):
        self.assertEqual(ledger.problems({}), ["the ledger has no steps list"])
        self.assertEqual(ledger.problems({"steps": ["storefront"]}),
                         ["steps[0]: must be an object"])

    def test_cli_exit_codes(self):
        # the success line counts only the checked steps
        code, out, err = run({"version": 1, "steps": [step(id="intake"), step(id="plan"),
                                                      step(id="verify"), step(status=...)]})
        self.assertEqual((code, err), (0, ""))
        self.assertIn(": 2 steps match the contract", out)
        code, out, err = run({"steps": [step(status="partial")]})
        self.assertEqual((code, out), (1, ""))
        self.assertIn("step 'storefront'", err)
        code, _, err = run(["not", "an", "object"])
        self.assertEqual(code, 1)
        self.assertIn("not a JSON object", err)


if __name__ == "__main__":
    unittest.main()
