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
        brief["project"] = {"merchant_id": 1, "project_id": 2}
        brief["site"]["slug"] = "my-test-site"
        self.brief = root / "brief.json"
        self.brief.write_text(json.dumps(brief), encoding="utf-8")

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

    def preflight(self) -> subprocess.CompletedProcess:
        return self.run_script(str(SCRIPTS / "preflight.py"), str(self.brief))

    def calls(self) -> list[dict]:
        return [
            json.loads(line)
            for line in self.log.read_text(encoding="utf-8").splitlines()
        ]

    def config_set_calls(self) -> list[dict]:
        def command(argv: list[str]) -> list[str]:
            return argv[2:] if argv[:1] == ["--environment"] else argv

        return [call for call in self.calls() if command(call["argv"])[:2] == ["config", "set"]]

    def test_other_environment_is_used_without_writing_config(self) -> None:
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

    def test_backup_reuses_the_other_environment(self) -> None:
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

    def test_sandbox_on_stops_and_writes_nothing(self) -> None:
        home_config = self.write_config(
            self.home,
            cli_config(dev={"merchant_id": 1, "project_id": 2, "sandbox": True}),
        )
        before = home_config.read_bytes()

        result = self.preflight()

        self.assertEqual(1, result.returncode)
        self.assertIn("nocode-shop-setup switches it off", result.stderr)
        self.assertEqual([], self.config_set_calls())
        self.assertEqual(before, home_config.read_bytes())
        self.assertFalse((self.folder / ".xsolla.json").exists())

    def test_sandbox_already_off_changes_nothing(self) -> None:
        self.write_config(self.home, cli_config(dev={"merchant_id": 1, "project_id": 2}))

        result = self.preflight()

        self.assertEqual(0, result.returncode, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual([], report["plan_notes"])
        self.assertEqual([], self.config_set_calls())
        self.assertFalse((self.folder / ".xsolla.json").exists())

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
            expected = {"merchant_id": 1, "project_id": 2}
            self.assertEqual(
                ["alpha", "test"],
                cli_environment.candidate_environments(path, expected),
            )


class PlanNotesTests(unittest.TestCase):
    def test_other_environment_says_which_one_and_not_switched_off(self) -> None:
        notes = cli_environment.plan_notes({"environment": "test"})
        self.assertEqual(["Using the CLI test environment (sandbox off)"], notes)
        self.assertNotIn("switched off", notes[0])

    def test_no_environment_adds_no_line(self) -> None:
        self.assertEqual([], cli_environment.plan_notes({"environment": None}))


if __name__ == "__main__":
    unittest.main()
