#!/usr/bin/env python3
"""Tests for the scoring half of run_evals.py — no `claude`, no network.

    python3 -m unittest discover -s evals/shop-plan -p 'test_*.py'
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_evals as ev  # noqa: E402


def stream(*events: dict) -> Path:
    """Write events as a stream-json transcript, shaped like `claude -p --verbose` output."""
    fh = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8")
    for e in events:
        fh.write(json.dumps(e) + "\n")
    fh.close()
    return Path(fh.name)


INIT = {"type": "system", "subtype": "init", "session_id": "s-1", "model": "m", "claude_code_version": "9",
        "skills": ["shop-plan", "shop-setup"]}
RESULT = {"type": "result", "subtype": "success", "is_error": False, "result": "done", "session_id": "s-1"}


def tool(name: str, **inp) -> dict:
    return {"type": "assistant", "message": {
        "usage": {"input_tokens": 2, "cache_creation_input_tokens": 10, "cache_read_input_tokens": 30},
        "content": [{"type": "tool_use", "name": name, "input": inp}]}}


def turn(skills=(), files=(), writes=(), xsolla=()) -> dict:
    return {"skills_invoked": list(skills), "files_changed": list(files),
            "write_attempts": list(writes), "xsolla_calls": list(xsolla)}


class ParseStream(unittest.TestCase):
    def test_extracts_session_skills_tokens_and_result(self):
        p = stream(INIT, tool("Skill", skill="shop-setup"), tool("Skill", skill="/shop-plan"),
                   {"type": "system", "subtype": "permission_denied"}, RESULT)
        out = ev.parse_stream(p)
        self.assertEqual(out["session_id"], "s-1")
        self.assertEqual(out["skills_invoked"], ["shop-setup", "shop-plan"])
        self.assertEqual(out["first_prompt_tokens"], 42)
        self.assertEqual(out["permission_denials"], 1)
        self.assertFalse(out["is_error"])

    def test_missing_result_counts_as_error(self):
        self.assertTrue(ev.parse_stream(stream(INIT))["is_error"])

    def test_tolerates_garbage_lines(self):
        p = stream(INIT)
        p.write_text(p.read_text() + "not json\n\n")
        self.assertEqual(ev.parse_stream(p)["session_id"], "s-1")


class WriteAttempts(unittest.TestCase):
    def bash(self, cmd: str) -> list[str]:
        return ev.write_attempts([{"name": "Bash", "input": {"command": cmd}}])

    def test_the_read_only_path_check_is_not_a_write(self):
        check = ("raw=$(grep -E '^XSOLLA_BUILD_PATH=' .env 2>/dev/null | tail -n 1 | cut -d= -f2-)\n"
                 'case "$raw" in\n  "") echo NO_DECISION ;;\nesac')
        self.assertEqual(self.bash(check), [])
        self.assertEqual(self.bash("ls -la 2>&1; cat .env >/dev/null"), [])

    def test_redirection_inside_quotes_is_not_a_write(self):
        # Both seen in real runs: a `>` inside a sed script read as a redirection.
        self.assertEqual(self.bash(
            "grep -E '^XSOLLA_(BUILD_PATH|PROJECT_ID)=' .env | sed -E 's/^(XSOLLA_PROJECT_API_KEY)=.*/\\1=<set>/'"), [])
        self.assertEqual(self.bash(
            "ls -a; grep -E '^XSOLLA_' .env 2>/dev/null | cut -d= -f1,2 | sed 's/API_KEY=.*/API_KEY=<set>/'"), [])
        self.assertEqual(self.bash('echo "nothing here -> just text"'), [])

    def test_real_writes_are_caught(self):
        for cmd in ("echo 'XSOLLA_BUILD_PATH=headless' >> .env",
                    "sed -i.bak 's|a|b|' .env",
                    "printf x | tee .gitignore",
                    "mkdir -p xsolla && touch xsolla/catalog.json",
                    "cat > plan.md <<'EOF'\nx\nEOF"):
            self.assertTrue(self.bash(cmd), cmd)

    def test_write_tools_are_caught(self):
        hits = ev.write_attempts([{"name": "Write", "input": {"file_path": "/x/.env"}},
                                  {"name": "Read", "input": {"file_path": "/x/.env"}}])
        self.assertEqual(hits, ["Write /x/.env"])


class InfrastructureErrors(unittest.TestCase):
    def test_rate_limit_is_infrastructure_not_a_skill_failure(self):
        turn = {"api_error_status": 429, "terminal_reason": "api_error", "exit_code": 1,
                "final_text": "You've hit your session limit"}
        self.assertIn("api_error 429", ev.infrastructure_error(turn))

    def test_timeout_is_infrastructure(self):
        self.assertIn("timeout", ev.infrastructure_error(
            {"exit_code": None, "stderr_tail": "timed out", "api_error_status": None}))

    def test_a_clean_turn_is_not(self):
        self.assertIsNone(ev.infrastructure_error(
            {"exit_code": 0, "api_error_status": None, "terminal_reason": "stop"}))

    def test_rate_limited_run_is_not_counted_as_a_premature_write(self):
        recs = [{"category": "path", "result": "error", "error_kind": "infrastructure",
                 "checks": {}, "skills_source": "worktree@x", "run_id": "x"}]
        m2 = ev.metrics(recs, {})["metric_2_premature_writes"]
        self.assertEqual(m2["premature_write_runs"], [])
        self.assertFalse(m2["met"])   # still not a valid run — missing data, not a pass
        self.assertEqual(ev.metrics(recs, {})["metric_1_recommendation_accuracy"]["infrastructure_errors"], 1)


class TurnLimit(unittest.TestCase):
    """Seen in real runs: login-styling selected, then --max-turns ran out mid-work. exit=1 and
    is_error=true, but the agent did not crash — it must be scored, not filed as a harness error."""
    CAPPED = {"type": "result", "subtype": "error_max_turns", "is_error": True, "terminal_reason": "max_turns",
              "result": "", "session_id": "s-1"}
    CASE = {"id": "regression-login-theme", "expect": {"skill_any": ["login-styling"], "skill_not": ["shop-plan"]}}

    def saved(self, *events) -> tuple[dict, Path]:
        raw_dir = Path(tempfile.mkdtemp())
        rec = {"run_id": "regression-login-theme.r1.worktree", "case": "regression-login-theme", "result": "error",
               "error_kind": "harness", "failure": "RuntimeError: turn 1 failed: exit=1 ", "checks": {},
               "turns": [{"skills_invoked": [], "files_changed": [], "write_attempts": [], "xsolla_calls": []}]}
        (raw_dir / f"{rec['run_id']}.t1.jsonl").write_text(stream(*events).read_text())
        return rec, raw_dir

    def test_capped_turn_is_not_infrastructure_and_is_recognised(self):
        parsed = ev.parse_stream(stream(INIT, tool("Skill", skill="login-styling"), self.CAPPED))
        self.assertTrue(ev.hit_turn_limit(parsed))
        self.assertIsNone(ev.infrastructure_error({**parsed, "exit_code": 1}))

    def test_rescore_passes_a_capped_run_that_picked_the_right_skill(self):
        rec, raw = self.saved(INIT, tool("Skill", skill="login-styling"), tool("Bash", command="ls"), self.CAPPED)
        new = ev.rescore(rec, self.CASE, raw)
        self.assertEqual(new["result"], "pass", new)
        self.assertNotIn("error_kind", new)
        self.assertTrue(new["turns"][0]["hit_turn_limit"])
        self.assertEqual(new["rescored"]["from_result"], "error")

    def test_rescore_still_fails_a_capped_run_that_picked_the_wrong_skill(self):
        rec, raw = self.saved(INIT, tool("Skill", skill="shop-plan"), self.CAPPED)
        self.assertEqual(ev.rescore(rec, self.CASE, raw)["result"], "fail")

    def test_rescore_leaves_real_crashes_and_env_dependent_cases_alone(self):
        rec, raw = self.saved(INIT, tool("Skill", skill="login-styling"))          # no result event: a crash
        self.assertIsNone(ev.rescore(rec, self.CASE, raw))
        rec, raw = self.saved(INIT, tool("Skill", skill="shop-plan"), self.CAPPED)
        self.assertIsNone(ev.rescore(rec, {"expect": {"recorded_path": "headless"}}, raw))
        self.assertIsNone(ev.rescore(rec, self.CASE, Path(tempfile.mkdtemp())))  # transcript missing


class TokenProbe(unittest.TestCase):
    def test_sides_are_interleaved_and_failed_probes_dropped(self):
        order, sizes = [], iter([100, 0, 110, 90])
        def fake_run(cmd, cwd, **kw):
            order.append(Path(cwd).name.split("-")[2])
            n = next(sizes)
            events = [INIT, {"type": "assistant", "message": {"usage": {"input_tokens": n}, "content": []}},
                      {**RESULT, "is_error": n == 0}]
            kw["stdout"].write("".join(json.dumps(e) + "\n" for e in events))
        skills = Path(tempfile.mkdtemp())
        (skills / "shop-plan").mkdir()
        (skills / "shop-plan" / "SKILL.md").write_text("x")
        with mock.patch.object(ev.subprocess, "run", fake_run):
            got = ev.token_probe({"branch": skills, "baseline": skills}, Path(tempfile.mkdtemp()), Path("/nope"), 2)
        self.assertEqual(order, ["branch", "baseline", "branch", "baseline"])
        self.assertEqual(got, {"branch": [100, 110], "baseline": [90]})


class ReadBuildPath(unittest.TestCase):
    def test_states(self):
        self.assertEqual(ev.read_build_path(None), (None, 0))
        self.assertEqual(ev.read_build_path("A=1\n"), (None, 0))
        self.assertEqual(ev.read_build_path("XSOLLA_BUILD_PATH=headless\n"), ("headless", 1))
        self.assertEqual(ev.read_build_path('XSOLLA_BUILD_PATH="headless"\n'), ('"headless"', 1))
        self.assertEqual(ev.read_build_path("XSOLLA_BUILD_PATH=a\nXSOLLA_BUILD_PATH=b\n"), ("b", 2))


class Score(unittest.TestCase):
    PATH_CASE = {"expect": {"skill_any": ["shop-plan"], "no_write_before_confirm": True,
                            "recorded_path": "shopbuilder"}}

    def test_clean_path_run_passes(self):
        r = ev.score(self.PATH_CASE, [turn(["shop-plan"]), turn(files=[".env"], writes=["Bash echo"])],
                     None, "XSOLLA_BUILD_PATH=shopbuilder\n")
        self.assertEqual(r["result"], "pass", r)

    def test_write_before_confirmation_fails_even_if_path_is_right(self):
        r = ev.score(self.PATH_CASE, [turn(["shop-plan"], files=[".env"]), turn()],
                     None, "XSOLLA_BUILD_PATH=shopbuilder\n")
        self.assertEqual(r["failure"], "no_write_before_confirm")

    def test_wrong_duplicated_or_missing_path_fails(self):
        for env in ("XSOLLA_BUILD_PATH=headless\n", "XSOLLA_BUILD_PATH=shopbuilder\n" * 2, None):
            r = ev.score(self.PATH_CASE, [turn(["shop-plan"]), turn()], None, env)
            self.assertIn("recorded_expected_path", r["failure"], env)

    def test_starting_a_build_after_confirmation_fails(self):
        r = ev.score(self.PATH_CASE, [turn(["shop-plan"]), turn(["catalog-design"])],
                     None, "XSOLLA_BUILD_PATH=shopbuilder\n")
        self.assertEqual(r["failure"], "stopped_after_recording")

    def test_xsolla_call_before_confirmation_fails(self):
        r = ev.score(self.PATH_CASE, [turn(["shop-plan"], xsolla=["catalog list"]), turn()],
                     None, "XSOLLA_BUILD_PATH=shopbuilder\n")
        self.assertIn("no_write_before_confirm", r["failure"])

    def test_env_unchanged_state_case(self):
        case = {"expect": {"skill_any": ["shop-plan", "shop-setup"], "env_unchanged": True}}
        seed = "XSOLLA_BUILD_PATH=Headless\n"
        self.assertEqual(ev.score(case, [turn(["shop-setup"])], seed, seed)["result"], "pass")
        self.assertEqual(ev.score(case, [turn(["shop-setup"])], seed, "XSOLLA_BUILD_PATH=headless\n")["failure"],
                         "env_unchanged")

    def test_regression_case_scores_selection_only(self):
        case = {"expect": {"skill_any": ["webhooks-impl"], "skill_not": ["shop-plan"]}}
        self.assertEqual(ev.score(case, [turn(["webhooks-impl"], files=["server.js"])], None, None)["result"], "pass")
        self.assertEqual(ev.score(case, [turn(["shop-plan", "webhooks-impl"])], None, None)["failure"], "avoided_skill")


class Metrics(unittest.TestCase):
    def rec(self, category, checks, result="pass", source="worktree@x", run_id="r"):
        return {"category": category, "checks": checks, "result": result, "skills_source": source, "run_id": run_id}

    def test_targets(self):
        recs = [self.rec("path", {"recorded_expected_path": True, "no_write_before_confirm": True}) for _ in range(9)]
        recs.append(self.rec("path", {"recorded_expected_path": False, "no_write_before_confirm": True}, "fail"))
        recs.append(self.rec("regression", {"selected_expected_skill": True}))
        recs.append(self.rec("regression", {"selected_expected_skill": True}, source="baseline:main@y"))
        m = ev.metrics(recs, {"branch": [110, 100, 120], "baseline": [90, 95, 80]})
        self.assertTrue(m["metric_1_recommendation_accuracy"]["met"])           # 9/10
        self.assertTrue(m["metric_2_premature_writes"]["met"])
        self.assertTrue(m["metric_3_cost_and_regression"]["met"])
        self.assertEqual(m["metric_3_cost_and_regression"]["added_prompt_tokens_median"], 20)

    def test_one_premature_write_or_error_misses_metric_2(self):
        bad = [self.rec("state", {"no_write_before_confirm": False}, "fail", run_id="w")]
        self.assertEqual(ev.metrics(bad, {})["metric_2_premature_writes"]["premature_write_runs"], ["w"])
        broken = [self.rec("path", {}, "error")]
        self.assertFalse(ev.metrics(broken, {})["metric_2_premature_writes"]["met"])
        self.assertFalse(ev.metrics(broken, {})["metric_1_recommendation_accuracy"]["met"])


if __name__ == "__main__":
    unittest.main()
