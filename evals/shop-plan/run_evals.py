#!/usr/bin/env python3
"""Unattended eval for the shop-plan decision step.

Drives the real Claude Code CLI (`claude -p`) against a copy of this repo's skills in a
throwaway directory, then scores what the agent actually did — which skills it loaded,
what changed on disk, which write commands it ran — against the fixed expectations in
cases.json. Nothing is read off by a human.

    python3 evals/shop-plan/run_evals.py --out evals/shop-plan/results/<date>.jsonl

See README.md for prerequisites, the three metrics, and the rules for a valid run.
Exit code 0 = every metric met its target, 1 = at least one missed, 2 = the run itself broke.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime
import hashlib
import io
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CASES = HERE / "cases.json"

KEY = "XSOLLA_BUILD_PATH"
TURN_TIMEOUT_S = 900
PREFLIGHT_TIMEOUT_S = 300
DEFAULT_MAX_TURNS = 12
ACCURACY_TARGET = 0.9
# Skills a confirmation turn may legitimately use; anything else means a build started.
PLANNING_SKILLS = {"shop-plan", "shop-setup"}
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
TOKEN_PROBE_PROMPT = "Reply with exactly: OK"
PROBE_COMMAND = ["claude", "-p", TOKEN_PROBE_PROMPT, "--output-format", "stream-json", "--verbose",
                 "--max-turns", "1", "--no-session-persistence"]

# Shell fragments that write. Quoted text is removed first (a `>` inside a sed script or an
# echo payload is not a redirection), then redirections to /dev/null and fd duplication.
# Deliberately strict: a false positive is fixed here, never by re-running until it goes away.
_QUOTED = re.compile(r"'[^']*'|\"[^\"]*\"")
_NULL_REDIRECT = re.compile(r"\d*>>?\s*/dev/null|\d*>&\d")
_WRITE_PATTERNS = [
    re.compile(r">>?\s*[^\s&|;]"),
    re.compile(r"\bsed\s+(-[a-zA-Z]*\s+)*-i"),
    re.compile(r"\b(tee|cp|mv|rm|mkdir|touch|ln|chmod|install|truncate|dd)\b"),
    re.compile(r"\bgit\s+(add|commit|init|checkout|reset|apply|stash)\b"),
]

class Infrastructure(RuntimeError):
    """The run failed for a reason unrelated to the skills (rate limit, API error, timeout)."""


@dataclass(frozen=True)
class Workspace:
    """Everything a run needs that is the same for every run in one invocation."""
    scratch: Path
    raw_dir: Path
    bin_dir: Path
    cases_sha: str
    followups: dict


# Stubbed onto PATH so no run can reach a live Xsolla project, whatever the agent tries.
XSOLLA_STUB = """#!/bin/sh
printf '%s\\n' "$*" >> "$EVAL_XSOLLA_LOG"
echo "xsolla is disabled inside the shop-plan eval harness" >&2
exit 13
"""


# ---------------------------------------------------------------------------- parsing

def parse_stream(path: Path) -> dict:
    """Reduce one `claude -p --output-format stream-json` transcript to what we score."""
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    out = {
        "session_id": None, "model": None, "cli_version": None, "skills_listed": [],
        "skills_invoked": [], "tool_uses": [], "final_text": "", "is_error": True,
        "permission_denials": 0, "first_prompt_tokens": None, "api_error_status": None,
        "terminal_reason": None,
    }
    for ev in events:
        etype, sub = ev.get("type"), ev.get("subtype")
        if etype == "system" and sub == "init":
            out["session_id"] = ev.get("session_id")
            out["model"] = ev.get("model")
            out["cli_version"] = ev.get("claude_code_version")
            out["skills_listed"] = list(ev.get("skills") or [])
        elif etype == "system" and sub == "permission_denied":
            out["permission_denials"] += 1
        elif etype == "assistant":
            msg = ev.get("message") or {}
            usage = msg.get("usage") or {}
            if out["first_prompt_tokens"] is None and usage:
                out["first_prompt_tokens"] = sum(
                    usage.get(k) or 0
                    for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
                )
            for block in msg.get("content") or []:
                if block.get("type") != "tool_use":
                    continue
                name, inp = block.get("name"), block.get("input") or {}
                out["tool_uses"].append({"name": name, "input": inp})
                if name == "Skill":
                    skill = inp.get("skill") or inp.get("command")
                    if skill:
                        out["skills_invoked"].append(str(skill).lstrip("/"))
        elif etype == "result":
            out["final_text"] = ev.get("result") or ""
            out["is_error"] = bool(ev.get("is_error"))
            out["api_error_status"] = ev.get("api_error_status")
            out["terminal_reason"] = ev.get("terminal_reason")
            if ev.get("session_id"):
                out["session_id"] = ev["session_id"]
    return out


def hit_turn_limit(turn: dict) -> bool:
    """The agent was still working when --max-turns ran out. A finished turn, not a crash:
    everything it did is on record and is scored like any other turn."""
    return turn.get("terminal_reason") == "max_turns"


def infrastructure_error(turn: dict) -> str | None:
    """Rate limit, API error, timeout — the run tells us nothing about the skills."""
    if turn.get("api_error_status") or turn.get("terminal_reason") == "api_error":
        return f"api_error {turn.get('api_error_status')}: {turn.get('final_text', '')[:120]}"
    if turn.get("exit_code") is None:
        return f"timeout: {turn.get('stderr_tail')}"
    return None


def write_attempts(tool_uses: list[dict]) -> list[str]:
    """Every tool call that writes, or looks like it writes, anywhere on disk."""
    hits = []
    for use in tool_uses:
        name, inp = use.get("name"), use.get("input") or {}
        if name in WRITE_TOOLS:
            hits.append(f"{name} {inp.get('file_path') or inp.get('notebook_path') or ''}".strip())
        elif name == "Bash":
            cmd = str(inp.get("command") or "")
            stripped = _NULL_REDIRECT.sub(" ", _QUOTED.sub(" ", cmd))
            if any(p.search(stripped) for p in _WRITE_PATTERNS):
                hits.append("Bash " + " ".join(cmd.split())[:200])
    return hits


def read_build_path(env_text: str | None) -> tuple[str | None, int]:
    """(last value of the key, number of occurrences) — last wins, per the build-path contract."""
    if env_text is None:
        return None, 0
    values = [line.split("=", 1)[1] for line in env_text.splitlines() if line.startswith(KEY + "=")]
    return (values[-1] if values else None), len(values)


# --------------------------------------------------------------------------- scoring

def score(case: dict, turns: list[dict], seed_env: str | None, final_env: str | None) -> dict:
    """Apply the case's expectations. Only the checks a case asks for are evaluated."""
    exp = case["expect"]
    first, later = turns[0], turns[1:]
    checks: dict[str, bool] = {}

    if "skill_any" in exp:
        checks["selected_expected_skill"] = bool(set(exp["skill_any"]) & set(first["skills_invoked"]))
    if "skill_not" in exp:
        checks["avoided_skill"] = not (set(exp["skill_not"]) & set(first["skills_invoked"]))
    if exp.get("no_write_before_confirm"):
        checks["no_write_before_confirm"] = (
            not first["files_changed"] and not first["write_attempts"] and not first["xsolla_calls"]
        )
    if "recorded_path" in exp:
        value, count = read_build_path(final_env)
        checks["recorded_expected_path"] = value == exp["recorded_path"] and count == 1
        checks["stopped_after_recording"] = all(
            set(t["skills_invoked"]) <= PLANNING_SKILLS and not t["xsolla_calls"] for t in later
        )
    if exp.get("env_unchanged"):
        checks["env_unchanged"] = final_env == seed_env

    failures = [name for name, ok in checks.items() if not ok]
    return {"checks": checks, "failure": ", ".join(failures) or None,
            "result": "fail" if failures else "pass"}


# ---------------------------------------------------------------------------- running

def materialize_skills(ref: str, dest: Path) -> tuple[Path, str]:
    """Skills as of `ref` ("WORKTREE" = the files on disk now). Returns (skills dir, label)."""
    if ref == "WORKTREE":
        head = git("rev-parse", "--short", "HEAD")
        dirty = git("status", "--porcelain", "--", "skills")
        return ROOT / "skills", f"worktree@{head}{'+dirty' if dirty else ''}"
    sha = git("rev-parse", "--short", ref)
    blob = subprocess.run(["git", "-C", str(ROOT), "archive", ref, "skills"],
                          capture_output=True, check=True).stdout
    with tarfile.open(fileobj=io.BytesIO(blob)) as tar:
        tar.extractall(dest)
    return dest / "skills", f"{ref}@{sha}"


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True,
                          check=True).stdout.strip()


def install_skills(skills_dir: Path, project: Path) -> list[str]:
    target = project / ".claude" / "skills"
    target.mkdir(parents=True)
    names = []
    for src in sorted(skills_dir.iterdir()):
        if (src / "SKILL.md").is_file():
            shutil.copytree(src, target / src.name)   # the directory itself, not its contents
            names.append(src.name)
    installed = sorted(p.parent.name for p in target.glob("*/SKILL.md"))
    if installed != names or not names:
        raise RuntimeError(f"skills did not install cleanly: expected {names}, found {installed}")
    return names


def snapshot(project: Path) -> dict[str, str]:
    files = {}
    for path in project.rglob("*"):
        rel = path.relative_to(project)
        if path.is_file() and rel.parts[:2] != (".claude", "skills"):
            files[str(rel)] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files


def diff(before: dict, after: dict) -> list[str]:
    return sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))


def agent_env(bin_dir: Path) -> dict:
    """The caller's environment minus any Xsolla credentials, with the stub `xsolla` first on PATH."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("XSOLLA_")}
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    return env


def run_turn(project: Path, cmd: list[str], env: dict, raw: Path) -> dict:
    xsolla_log = Path(env["EVAL_XSOLLA_LOG"])
    calls_before = xsolla_log.read_text().splitlines() if xsolla_log.exists() else []
    before = snapshot(project)
    try:
        with raw.open("w", encoding="utf-8") as fh:
            proc = subprocess.run(cmd, cwd=project, env=env, stdout=fh, stderr=subprocess.PIPE,
                                  text=True, timeout=TURN_TIMEOUT_S)
        exit_code, err = proc.returncode, proc.stderr[-500:]
    except subprocess.TimeoutExpired:
        exit_code, err = None, f"timed out after {TURN_TIMEOUT_S}s"
    parsed = parse_stream(raw)
    calls_after = xsolla_log.read_text().splitlines() if xsolla_log.exists() else []
    parsed.update({
        "exit_code": exit_code, "stderr_tail": err,
        "files_changed": diff(before, snapshot(project)),
        "write_attempts": write_attempts(parsed["tool_uses"]),
        "xsolla_calls": calls_after[len(calls_before):],
    })
    return parsed


def run_case(case: dict, round_no: int, skills_dir: Path, skills_label: str, ws: Workspace) -> dict:
    run_id = f"{case['id']}.r{round_no}.{skills_label.split('@')[0].replace('/', '-')}"
    project = Path(tempfile.mkdtemp(prefix=f"{case['id']}-r{round_no}-", dir=ws.scratch))
    env = agent_env(ws.bin_dir)
    env["EVAL_XSOLLA_LOG"] = str(project.parent / f".{project.name}.xsolla.log")

    record = {
        "run_id": run_id, "date": datetime.date.today().isoformat(), "case": case["id"],
        "category": case["category"], "round": round_no, "skills_source": skills_label,
        "cases_sha256": ws.cases_sha, "manual_interventions": 0, "turns": [],
    }
    turns: list[dict] = []
    try:
        record["skills_installed"] = install_skills(skills_dir, project)
        seed = case.get("seed_env")
        if seed is not None:
            (project / ".env").write_text(seed, encoding="utf-8")

        max_turns = case.get("max_turns", DEFAULT_MAX_TURNS)
        session = None
        for i, prompt in enumerate([case["prompt"]] + ws.followups.get(case.get("followups"), [])):
            if i > 0 and read_build_path(read_env(project))[0] is not None:
                break                        # recorded — stop confirming
            cmd = ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose",
                   "--max-turns", str(max_turns), "--permission-mode", "bypassPermissions"]
            if session:
                cmd += ["--resume", session]
            turn = run_turn(project, cmd, env, ws.raw_dir / f"{run_id}.t{i + 1}.jsonl")
            turn["prompt"] = prompt
            turns.append(turn)
            session = turn["session_id"]
            infra = infrastructure_error(turn)
            if infra:
                raise Infrastructure(f"turn {i + 1}: {infra}")
            if hit_turn_limit(turn) and session:
                continue
            if turn["exit_code"] != 0 or turn["is_error"] or not session:
                raise RuntimeError(f"turn {i + 1} failed: exit={turn['exit_code']} {turn['stderr_tail']}")

        final_env = read_env(project)
        record.update(score(case, turns, seed, final_env))
        record["final_build_path"] = read_build_path(final_env)[0]
    except Infrastructure as exc:
        # Not evidence about the skills — the run never completed. Kept, never silently dropped.
        record.update({"result": "error", "error_kind": "infrastructure", "failure": str(exc), "checks": {}})
    except Exception as exc:  # noqa: BLE001 — a broken run is recorded, never dropped
        record.update({"result": "error", "error_kind": "harness",
                       "failure": f"{type(exc).__name__}: {exc}", "checks": {}})

    first = turns[0] if turns else {}
    record["model"] = first.get("model")
    record["cli_version"] = first.get("cli_version")
    record["turns"] = [summarize_turn(t, ws.scratch) for t in turns]
    return record


def read_env(project: Path) -> str | None:
    path = project / ".env"
    return path.read_text(encoding="utf-8") if path.exists() else None


def summarize_turn(turn: dict, scratch: Path) -> dict:
    """What goes in the committed log: no raw transcript, no local paths."""
    def scrub(text: str) -> str:
        return text.replace(str(scratch), "<scratch>").replace(str(Path.home()), "~")
    return {
        "prompt": turn["prompt"],
        "skills_invoked": turn["skills_invoked"],
        "tool_calls": len(turn["tool_uses"]),
        "files_changed": turn["files_changed"],
        "write_attempts": [scrub(w) for w in turn["write_attempts"]],
        "xsolla_calls": turn["xsolla_calls"],
        "permission_denials": turn["permission_denials"],
        "hit_turn_limit": hit_turn_limit(turn),
        "final_text_excerpt": scrub(turn["final_text"])[:400],
    }


def token_probe(sides: dict[str, Path], scratch: Path, bin_dir: Path, n: int) -> dict[str, list[int]]:
    """First-request prompt size with only the skills changed — the listing's context cost.

    Sides are interleaved (branch, baseline, branch, …) so drift in the rest of the prompt over
    the run lands on both sides rather than skewing one.
    """
    sizes: dict[str, list[int]] = {label: [] for label in sides}
    env = agent_env(bin_dir)
    for _ in range(n):
        for label, skills_dir in sides.items():
            project = Path(tempfile.mkdtemp(prefix=f"token-probe-{label}-", dir=scratch))
            install_skills(skills_dir, project)
            raw = project.parent / f".{project.name}.jsonl"
            with raw.open("w", encoding="utf-8") as fh:
                subprocess.run(PROBE_COMMAND, cwd=project, env=env, stdout=fh, stderr=subprocess.DEVNULL,
                               timeout=TURN_TIMEOUT_S)
            probe = parse_stream(raw)
            tokens = probe["first_prompt_tokens"]
            if probe["is_error"] or not tokens:
                continue      # a rate-limited probe reports zeros; never record that as a measurement
            sizes[label].append(tokens)
    return sizes


def preflight() -> str | None:
    """One cheap call: is the CLI usable right now? Returns a reason to stop, or None."""
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "preflight.jsonl"
        with raw.open("w", encoding="utf-8") as fh:
            try:
                subprocess.run(PROBE_COMMAND, cwd=tmp, stdout=fh, stderr=subprocess.DEVNULL,
                               timeout=PREFLIGHT_TIMEOUT_S)
            except subprocess.TimeoutExpired:
                return f"the `claude` CLI did not answer a trivial prompt within {PREFLIGHT_TIMEOUT_S}s"
        turn = parse_stream(raw)
        if turn["is_error"] or not turn["first_prompt_tokens"]:
            return infrastructure_error(turn) or f"trivial prompt failed: {turn['final_text'][:200]}"
    return None


# --------------------------------------------------------------------------- metrics

def metrics(records: list[dict], probes: dict[str, list[int]]) -> dict:
    def rate(rows, check):
        scored = [r for r in rows if r["result"] != "error"]
        errors = [r for r in rows if r["result"] == "error"]
        ok = sum(1 for r in scored if r["checks"].get(check))
        return {"passed": ok, "scored": len(scored), "errors": len(errors),
                "infrastructure_errors": sum(1 for r in errors if r.get("error_kind") == "infrastructure"),
                "rate": round(ok / len(scored), 3) if scored else None}

    branch = [r for r in records if not r["skills_source"].startswith("baseline")]
    path_rows = [r for r in branch if r["category"] == "path"]
    m1 = rate(path_rows, "recorded_expected_path")
    m1["target"] = f">= {ACCURACY_TARGET}"
    m1["met"] = m1["rate"] is not None and m1["rate"] >= ACCURACY_TARGET and m1["errors"] == 0

    gated = [r for r in branch if r["category"] in ("path", "state")]
    premature = [r["run_id"] for r in gated if r["checks"].get("no_write_before_confirm") is False]
    errors = [r["run_id"] for r in gated if r["result"] == "error"]
    m2 = {"premature_write_runs": premature, "count": len(premature), "scored": len(gated) - len(errors),
          "errors": len(errors), "target": "0", "met": not premature and not errors}

    m3: dict = {"target": "report; headless selection rate must not drop"}
    for label, rows in (("branch", branch), ("baseline", [r for r in records if r["skills_source"].startswith("baseline")])):
        m3[f"headless_selection_{label}"] = rate([r for r in rows if r["category"] == "regression"],
                                                 "selected_expected_skill")
    for label, sizes in probes.items():
        m3[f"prompt_tokens_{label}"] = {"median": statistics.median(sizes) if sizes else None,
                                        "min": min(sizes, default=None), "max": max(sizes, default=None),
                                        "n": len(sizes)}
    branch_rate = m3["headless_selection_branch"]["rate"]
    baseline_rate = m3["headless_selection_baseline"]["rate"]
    if branch_rate is not None and baseline_rate is not None:
        m3["met"] = branch_rate >= baseline_rate
    branch_tokens = m3.get("prompt_tokens_branch", {}).get("median")
    baseline_tokens = m3.get("prompt_tokens_baseline", {}).get("median")
    if branch_tokens is not None and baseline_tokens is not None:
        m3["added_prompt_tokens_median"] = branch_tokens - baseline_tokens
    return {"metric_1_recommendation_accuracy": m1, "metric_2_premature_writes": m2,
            "metric_3_cost_and_regression": m3}


# ------------------------------------------------------------------------------ main

def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True, type=Path, help="new results .jsonl (never overwritten)")
    ap.add_argument("--rounds", type=int, default=2, help="runs per case (default 2)")
    ap.add_argument("--jobs", type=int, default=4, help="parallel runs (default 4)")
    ap.add_argument("--cases", help="comma-separated case ids (default: all)")
    ap.add_argument("--skills-ref", default="WORKTREE", help="skills under test (default: files on disk)")
    ap.add_argument("--baseline-ref", default="origin/main",
                    help="skills for the Metric 3 comparison ('none' to skip)")
    ap.add_argument("--token-probes", type=int, default=3, help="prompt-size samples per side (0 to skip)")
    ap.add_argument("--raw-dir", type=Path, help="keep raw transcripts here (must be outside the repo)")
    return ap.parse_args()


def prepare_workspace(args: argparse.Namespace) -> Workspace | str:
    """Scratch dir, transcript dir and the stub `xsolla`. Returns a reason to stop instead, if any."""
    if args.out.exists():
        return f"{args.out} exists — results are append-only history; pick a new file name"
    if shutil.which("claude") is None:
        return "the `claude` CLI is not on PATH — see README.md prerequisites"
    blocked = preflight()
    if blocked:
        return f"preflight failed, not starting: {blocked}"
    scratch = Path(tempfile.mkdtemp(prefix="shop-plan-eval-")).resolve()
    if ROOT in scratch.parents:
        return "scratch directory resolved inside the repo — refusing (skills write .env)"
    raw_dir = (args.raw_dir or scratch / "raw").resolve()
    if ROOT == raw_dir or ROOT in raw_dir.parents:
        return "--raw-dir must be outside the repo — transcripts contain local paths"
    raw_dir.mkdir(parents=True, exist_ok=True)
    bin_dir = scratch / "bin"
    bin_dir.mkdir()
    (bin_dir / "xsolla").write_text(XSOLLA_STUB)
    (bin_dir / "xsolla").chmod(0o755)
    spec = json.loads(CASES.read_text(encoding="utf-8"))
    return Workspace(scratch, raw_dir, bin_dir, hashlib.sha256(CASES.read_bytes()).hexdigest(), spec["followups"])


def select_cases(ids: str | None) -> list[dict]:
    cases = json.loads(CASES.read_text(encoding="utf-8"))["cases"]
    if not ids:
        return cases
    wanted = set(ids.split(","))
    unknown = wanted - {c["id"] for c in cases}
    if unknown:
        raise SystemExit(f"unknown case ids: {sorted(unknown)}")
    return [c for c in cases if c["id"] in wanted]


def run_command(args: argparse.Namespace, ws: Workspace) -> int:
    cases = select_cases(args.cases)
    skills_dir, skills_label = materialize_skills(args.skills_ref, ws.scratch / "skills-under-test")
    sides = {"branch": skills_dir}
    jobs = [(c, r, skills_dir, skills_label) for c in cases for r in range(1, args.rounds + 1)]
    if args.baseline_ref != "none":
        base_dir, base_label = materialize_skills(args.baseline_ref, ws.scratch / "skills-baseline")
        sides["baseline"] = base_dir
        jobs += [(c, r, base_dir, f"baseline:{base_label}") for c in cases if c["category"] == "regression"
                 for r in range(1, args.rounds + 1)]

    print(f"{len(jobs)} runs · skills {skills_label} · scratch {ws.scratch}", flush=True)
    records = []
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as fh, \
            concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = [pool.submit(run_case, c, r, d, label, ws) for c, r, d, label in jobs]
        for future in concurrent.futures.as_completed(futures):
            record = future.result()
            records.append(record)
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            fh.flush()
            print(f"  {record['result']:5s} {record['run_id']}  {record.get('failure') or ''}", flush=True)

    probes = token_probe(sides, ws.scratch, ws.bin_dir, args.token_probes) if args.token_probes else {}
    summary = {"generated": datetime.datetime.now().isoformat(timespec="seconds"),
               "results_file": args.out.name, "cases_sha256": ws.cases_sha, "skills_under_test": skills_label,
               "rounds": args.rounds, "runs": len(records),
               "models": sorted({r["model"] for r in records if r.get("model")}),
               "cli_versions": sorted({r["cli_version"] for r in records if r.get("cli_version")}),
               **metrics(records, probes)}
    args.out.with_name(args.out.stem + "-summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"\nraw transcripts: {ws.raw_dir}\nscratch projects: {ws.scratch}  (outside the repo; delete when done)")

    if any(r["result"] == "error" for r in records):
        return 2
    return 0 if all(summary[k].get("met") is not False for k in summary if k.startswith("metric_")) else 1


def main() -> int:
    args = parse_args()
    ws = prepare_workspace(args)
    if isinstance(ws, str):
        print(ws, file=sys.stderr)
        return 2
    return run_command(args, ws)


if __name__ == "__main__":
    sys.exit(main())
