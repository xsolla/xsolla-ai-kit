"""Sandbox mode for Shop Builder, against a fake `xsolla` on PATH.

The fake CLI copies the config behaviour of xsolla 1.9.4: reads use
`./.xsolla.json` when the working directory has one, else `$HOME/.xsolla.json`;
`--environment <name>` picks an environment of that file; `config set` writes
`./.xsolla.json` and creates a stub (no merchant or project) when there is none.
Every script runs as a subprocess with its own HOME, so nothing here touches the
real CLI config.
"""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import cli_environment  # noqa: E402

FAKE_XSOLLA = r'''
import json, os, sys
from pathlib import Path

argv = sys.argv[1:]
with open(os.environ["FAKE_XSOLLA_LOG"], "a", encoding="utf-8") as log:
    log.write(json.dumps({"argv": argv, "cwd": os.getcwd()}) + "\n")

environment = None
if "--environment" in argv:
    at = argv.index("--environment")
    environment = argv[at + 1]
    del argv[at:at + 2]
argv = [arg for arg in argv if arg != "--json"]

local = Path.cwd() / ".xsolla.json"
path = local if local.is_file() else Path(os.environ["HOME"]) / ".xsolla.json"


def out(value):
    print(json.dumps({"ok": True, "data": value}))
    sys.exit(0)


if argv[:2] == ["config", "set"]:
    key, value = argv[2], argv[3]
    if local.is_file():
        config = json.loads(local.read_text())
    else:
        config = {"version": "1", "default_environment": "dev", "environments": {
            "dev": {"api_base": "https://api.example.test"},
            "prod": {"api_base": "https://api.example.test"}}}
    name = environment or config["default_environment"]
    values = config["environments"].setdefault(name, {})
    if key == "sandbox":
        if value == "true":
            values["sandbox"] = True
        else:
            values.pop("sandbox", None)
    local.write_text(json.dumps(config, indent=2))
    out({"environment": name, "key": key, "value": value})

config = json.loads(path.read_text()) if path.is_file() else {
    "default_environment": "dev", "environments": {"dev": {}}}
name = environment or config["default_environment"]
if name not in config["environments"]:
    print(f'environment "{name}" not found in config', file=sys.stderr)
    sys.exit(1)
values = {k: v for k, v in config["environments"][name].items() if v is not False}

if argv == ["config", "list"]:
    out(values)
if argv == ["auth", "list-account"]:
    out({"accounts": [{"context": "publisher", "active": True, "expired": False}]})
if argv == ["shopbuilder", "list-websites"]:
    out([])
if argv[:2] == ["catalog", "list-item-groups"]:
    out({"groups": []})
if argv == ["shopbuilder", "create-block", "--help"]:
    print("Usage:\n  xsolla shopbuilder create-block [flags]")
    sys.exit(0)
print("unexpected call: " + " ".join(argv), file=sys.stderr)
sys.exit(2)
'''

TEST_ENVIRONMENT = {"merchant_id": 1, "project_id": 2, "sandbox": False}


def cli_config(**environments: dict) -> dict:
    return {
        "version": "1",
        "default_environment": "dev",
        "environments": environments,
    }


class SandboxModeTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        self.bin = root / "bin"
        self.home = root / "home"
        self.folder = root / "user-folder"
        for path in (self.bin, self.home, self.folder):
            path.mkdir()
        fake = self.bin / "xsolla"
        fake.write_text(f"#!{sys.executable}\n{FAKE_XSOLLA}", encoding="utf-8")
        fake.chmod(0o755)
        self.log = root / "calls.jsonl"
        self.log.touch()

        brief = json.loads(
            (ROOT / "examples" / "mobile-single-page.json").read_text(encoding="utf-8")
        )
        brief["project"] = {"merchant_id": 1, "project_id": 2, "environment": "test"}
        brief["site"]["slug"] = "my-test-site"
        self.brief = root / "brief.json"
        self.brief.write_text(json.dumps(brief), encoding="utf-8")
        self.approved = root / "approved-test-projects.json"
        self.approve(1, 2)

    def approve(self, merchant_id: int, project_id: int) -> None:
        self.approved.write_text(
            json.dumps(
                {
                    "version": 1,
                    "projects": [
                        {
                            "merchant_id": merchant_id,
                            "project_id": project_id,
                            "approved_by": "test mentor",
                            "approval_reference": "test approval",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

    def write_config(self, directory: Path, config: dict) -> Path:
        path = directory / ".xsolla.json"
        path.write_text(json.dumps(config, indent=2), encoding="utf-8")
        return path

    def run_script(self, *args: str) -> subprocess.CompletedProcess:
        env = dict(os.environ)
        env.update(
            {
                "HOME": str(self.home),
                "PATH": str(self.bin) + os.pathsep + env.get("PATH", ""),
                "FAKE_XSOLLA_LOG": str(self.log),
                "PYTHONDONTWRITEBYTECODE": "1",
            }
        )
        return subprocess.run(
            [sys.executable, *args],
            cwd=self.folder,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

    def preflight(self, *, confirm: bool = False) -> subprocess.CompletedProcess:
        args = [
            str(SCRIPTS / "preflight.py"),
            str(self.brief),
            "--approved-test-projects",
            str(self.approved),
        ]
        if confirm:
            args.append("--confirm-sandbox-off")
        return self.run_script(*args)

    def restore(self) -> subprocess.CompletedProcess:
        return self.run_script(str(SCRIPTS / "restore_sandbox.py"))

    def restore_record(self) -> Path:
        return self.home / cli_environment.RESTORE_NAME

    def calls(self) -> list[dict]:
        return [
            json.loads(line)
            for line in self.log.read_text(encoding="utf-8").splitlines()
        ]

    def config_set_calls(self) -> list[dict]:
        def command(argv: list[str]) -> list[str]:
            return argv[2:] if argv[:1] == ["--environment"] else argv

        return [call for call in self.calls() if command(call["argv"])[:2] == ["config", "set"]]

    def test_test_environment_is_used_without_writing_config(self) -> None:
        home_config = self.write_config(
            self.home,
            cli_config(
                dev={"merchant_id": 1, "project_id": 2, "sandbox": True},
                test=copy.deepcopy(TEST_ENVIRONMENT),
            ),
        )
        before = home_config.read_bytes()

        result = self.preflight()

        self.assertEqual(0, result.returncode, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual("test", report["context"]["cli_environment"])
        self.assertFalse(report["context"]["sandbox_switched_off"])
        self.assertTrue(report["context"]["test_project_acknowledged"])
        self.assertEqual(
            ["Using the CLI test environment (sandbox off)"], report["plan_notes"]
        )
        self.assertEqual([], self.config_set_calls())
        self.assertEqual(before, home_config.read_bytes())
        self.assertFalse((self.folder / ".xsolla.json").exists())
        calls = self.calls()
        self.assertEqual(["config", "list", "--json"], calls[0]["argv"])
        for call in calls[1:]:
            self.assertEqual(["--environment", "test"], call["argv"][:2], call)

    def test_backup_reuses_the_test_environment(self) -> None:
        self.write_config(
            self.home,
            cli_config(
                dev={"merchant_id": 1, "project_id": 2, "sandbox": True},
                test=copy.deepcopy(TEST_ENVIRONMENT),
            ),
        )
        result = self.run_script(
            str(SCRIPTS / "backup_shop.py"),
            "--brief",
            str(self.brief),
            "--slug",
            "my-test-site",
            "--output-dir",
            str(self.folder.parent / "backup"),
        )
        # The fake has no get-landing; the first Shop Builder read must still carry
        # the environment.
        self.assertNotEqual(0, result.returncode)
        shopbuilder = [c for c in self.calls() if "shopbuilder" in c["argv"]]
        self.assertTrue(shopbuilder)
        for call in shopbuilder:
            self.assertEqual(["--environment", "test"], call["argv"][:2], call)
        self.assertEqual([], self.config_set_calls())
        self.assertFalse((self.folder / ".xsolla.json").exists())

    def test_sandbox_switch_stops_for_confirmation_and_writes_nothing(self) -> None:
        home_config = self.write_config(
            self.home,
            cli_config(dev={"merchant_id": 1, "project_id": 2, "sandbox": True}),
        )
        before = home_config.read_bytes()

        result = self.preflight()

        self.assertEqual(1, result.returncode)
        self.assertIn("Preflight needs confirmation", result.stderr)
        self.assertIn("xsolla config set sandbox false", result.stderr)
        self.assertEqual([], self.config_set_calls())
        self.assertEqual(before, home_config.read_bytes())
        self.assertFalse(self.restore_record().exists())
        self.assertFalse((self.folder / ".xsolla.json").exists())
        self.assertEqual([["config", "list", "--json"]], [c["argv"] for c in self.calls()])

    def test_sandbox_is_switched_off_in_the_home_config_without_a_new_file(self) -> None:
        home_config = self.write_config(
            self.home,
            cli_config(dev={"merchant_id": 1, "project_id": 2, "sandbox": True}),
        )

        result = self.preflight(confirm=True)

        self.assertEqual(0, result.returncode, result.stderr)
        report = json.loads(result.stdout)
        self.assertIsNone(report["context"]["cli_environment"])
        self.assertTrue(report["context"]["sandbox_switched_off"])
        self.assertEqual(
            ["CLI sandbox mode switched off for Shop Builder; it is switched back on when the run ends"],
            report["plan_notes"],
        )
        sets = self.config_set_calls()
        self.assertEqual(1, len(sets))
        self.assertEqual(os.path.realpath(self.home), os.path.realpath(sets[0]["cwd"]))
        self.assertNotIn("sandbox", json.loads(home_config.read_text())["environments"]["dev"])
        self.assertEqual(1, json.loads(home_config.read_text())["environments"]["dev"]["merchant_id"])
        self.assertFalse((self.folder / ".xsolla.json").exists())
        self.assertTrue(self.restore_record().is_file())
        for call in self.calls():
            self.assertNotIn("--environment", call["argv"])

    def test_sandbox_is_switched_off_in_the_folder_config_in_use(self) -> None:
        home_config = self.write_config(
            self.home, cli_config(dev={"merchant_id": 9, "project_id": 9})
        )
        home_before = home_config.read_bytes()
        local = self.write_config(
            self.folder,
            cli_config(dev={"merchant_id": 1, "project_id": 2, "sandbox": True}),
        )

        result = self.preflight(confirm=True)

        self.assertEqual(0, result.returncode, result.stderr)
        sets = self.config_set_calls()
        self.assertEqual(1, len(sets))
        self.assertEqual(
            os.path.realpath(self.folder), os.path.realpath(sets[0]["cwd"])
        )
        self.assertNotIn("sandbox", json.loads(local.read_text())["environments"]["dev"])
        self.assertEqual(home_before, home_config.read_bytes())

    def test_sandbox_already_off_changes_nothing(self) -> None:
        self.write_config(self.home, cli_config(dev={"merchant_id": 1, "project_id": 2}))

        result = self.preflight()

        self.assertEqual(0, result.returncode, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual([], report["plan_notes"])
        self.assertFalse(report["context"]["sandbox_switched_off"])
        self.assertEqual([], self.config_set_calls())
        self.assertFalse((self.folder / ".xsolla.json").exists())

    def test_restore_after_the_run_puts_sandbox_back_on(self) -> None:
        home_config = self.write_config(
            self.home,
            cli_config(dev={"merchant_id": 1, "project_id": 2, "sandbox": True}),
        )
        self.assertEqual(0, self.preflight(confirm=True).returncode)
        self.assertNotIn("sandbox", json.loads(home_config.read_text())["environments"]["dev"])
        self.assertTrue(self.restore_record().is_file())

        result = self.restore()

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual({"restored": True, "directory": str(self.home)}, json.loads(result.stdout))
        self.assertTrue(json.loads(home_config.read_text())["environments"]["dev"]["sandbox"])
        self.assertFalse(self.restore_record().exists())
        restores = [c for c in self.config_set_calls() if c["argv"][-3:-1] == ["sandbox", "true"]]
        self.assertEqual(1, len(restores))
        self.assertEqual(os.path.realpath(self.home), os.path.realpath(restores[0]["cwd"]))
        self.assertFalse((self.folder / ".xsolla.json").exists())

    def test_restore_without_a_switch_changes_nothing(self) -> None:
        home_config = self.write_config(
            self.home, cli_config(dev={"merchant_id": 1, "project_id": 2})
        )
        before = home_config.read_bytes()

        result = self.restore()

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual({"restored": False}, json.loads(result.stdout))
        self.assertEqual([], self.config_set_calls())
        self.assertEqual(before, home_config.read_bytes())

    def test_other_scripts_never_switch_sandbox_off(self) -> None:
        home_config = self.write_config(
            self.home,
            cli_config(dev={"merchant_id": 1, "project_id": 2, "sandbox": True}),
        )
        before = home_config.read_bytes()
        result = self.run_script(
            str(SCRIPTS / "backup_shop.py"),
            "--brief",
            str(self.brief),
            "--slug",
            "my-test-site",
            "--output-dir",
            str(self.folder.parent / "backup"),
        )
        self.assertEqual(1, result.returncode)
        self.assertIn("run preflight again", result.stderr)
        self.assertEqual([], self.config_set_calls())
        self.assertEqual(before, home_config.read_bytes())
        self.assertFalse((self.folder / ".xsolla.json").exists())

    def test_project_missing_from_allowlist_stops_before_any_cli_call(self) -> None:
        self.write_config(
            self.home,
            cli_config(dev={"merchant_id": 1, "project_id": 2, "sandbox": True}),
        )
        self.approve(1, 3)

        result = self.preflight()

        self.assertEqual(1, result.returncode)
        self.assertIn("needs_human", result.stderr)
        self.assertIn("allowlist", result.stderr)
        self.assertEqual([], self.calls())
        self.assertFalse((self.folder / ".xsolla.json").exists())


class ConfigInUseTests(unittest.TestCase):
    def test_folder_config_wins_over_home(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "home").mkdir()
            (root / "folder").mkdir()
            (root / "home" / ".xsolla.json").write_text("{}")
            self.assertEqual(
                root / "home" / ".xsolla.json",
                cli_environment.config_in_use(root / "folder", root / "home"),
            )
            (root / "folder" / ".xsolla.json").write_text("{}")
            self.assertEqual(
                root / "folder" / ".xsolla.json",
                cli_environment.config_in_use(root / "folder", root / "home"),
            )

    def test_candidates_need_sandbox_off_and_the_same_ids(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".xsolla.json"
            path.write_text(
                json.dumps(
                    cli_config(
                        dev={"merchant_id": 1, "project_id": 2, "sandbox": True},
                        other={"merchant_id": 1, "project_id": 3},
                        sandboxed={"merchant_id": 1, "project_id": 2, "sandbox": True},
                        alpha={"merchant_id": 1, "project_id": 2},
                        test={"merchant_id": 1, "project_id": 2},
                    )
                )
            )
            expected = {"merchant_id": 1, "project_id": 2, "environment": "test"}
            self.assertEqual(
                ["test", "alpha"],
                cli_environment.candidate_environments(path, expected),
            )


class PlanNotesTests(unittest.TestCase):
    def test_other_environment_says_which_one_and_not_switched_off(self) -> None:
        notes = cli_environment.plan_notes(
            {"environment": "test", "sandbox_switched_off": False}
        )
        self.assertEqual(["Using the CLI test environment (sandbox off)"], notes)
        self.assertNotIn("switched off", notes[0])

    def test_config_change_says_switched_off_until_the_run_ends(self) -> None:
        self.assertEqual(
            ["CLI sandbox mode switched off for Shop Builder; it is switched back on when the run ends"],
            cli_environment.plan_notes({"environment": None, "sandbox_switched_off": True}),
        )

    def test_sandbox_already_off_adds_no_line(self) -> None:
        self.assertEqual(
            [],
            cli_environment.plan_notes({"environment": None, "sandbox_switched_off": False}),
        )


if __name__ == "__main__":
    unittest.main()
