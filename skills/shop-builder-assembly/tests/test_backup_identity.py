from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


backup_shop = load_module("backup_shop", ROOT / "scripts" / "backup_shop.py")

TARGET = {"merchant_id": 11, "project_id": 22}
CONFIG = {"ok": True, "data": {"merchant_id": 11, "project_id": 22, "sandbox": False}}
WEBSITES = {"ok": True, "data": [{"domain": "demo-shop", "_id": "landing-1"}]}


def args(**overrides) -> argparse.Namespace:
    values = {"brief": None, "merchant_id": 11, "project_id": 22, "environment": "sandbox",
              "approved_test_projects": None, "slug": "demo-shop", "output_dir": None}
    values.update(overrides)
    return argparse.Namespace(**values)


def allowlist(project_id: int = 22) -> Path:
    fh = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    json.dump({"version": 1, "projects": [{"merchant_id": 11, "project_id": project_id,
                                           "approved_by": "reviewer",
                                           "approval_reference": "approval"}]}, fh)
    fh.close()
    return Path(fh.name)


def fake_cli(*command: str) -> object:
    responses = {
        ("config", "list"): CONFIG,
        ("shopbuilder", "list-websites"): WEBSITES,
        ("shopbuilder", "get-structure"): {"ok": True, "data": {"_id": "landing-1"}},
    }
    return responses.get(command[:2], {"ok": True, "data": {}})


class TargetProjectTest(unittest.TestCase):
    def test_sandbox_identity_needs_no_allowlist(self) -> None:
        self.assertEqual(backup_shop.target_project(args()), {**TARGET, "environment": "sandbox"})

    def test_test_identity_requires_the_allowlist(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "--approved-test-projects is required"):
            backup_shop.target_project(args(environment="test"))

    def test_listed_test_project_passes(self) -> None:
        target = backup_shop.target_project(args(environment="test",
                                                 approved_test_projects=allowlist()))
        self.assertEqual(target["environment"], "test")

    def test_unlisted_test_project_stops(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "approved test-project allowlist"):
            backup_shop.target_project(args(environment="test",
                                            approved_test_projects=allowlist(project_id=99)))

    def test_brief_and_identity_cannot_be_mixed(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "not both"):
            backup_shop.target_project(args(brief=Path("brief.json")))

    def test_identity_must_be_complete(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "all of --merchant-id"):
            backup_shop.target_project(args(environment=None))

    def test_ids_must_be_positive(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "positive integers"):
            backup_shop.target_project(args(project_id=0))


class IdentityBackupTest(unittest.TestCase):
    def run_main(self, argv: list[str]) -> tuple[int, str]:
        stderr = io.StringIO()
        with mock.patch.object(sys, "argv", ["backup_shop.py", *argv]), \
                mock.patch.object(backup_shop.shutil, "which", return_value="/usr/bin/xsolla"), \
                mock.patch.object(backup_shop, "run_json", side_effect=fake_cli), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr):
            code = backup_shop.main()
        return code, stderr.getvalue()

    def test_a_site_that_does_not_exist_is_not_backed_up(self) -> None:
        out = Path(tempfile.mkdtemp()) / "backup"
        code, err = self.run_main(["--merchant-id", "11", "--project-id", "22",
                                   "--environment", "test",
                                   "--approved-test-projects", str(allowlist()),
                                   "--slug", "new-shop", "--output-dir", str(out)])
        self.assertEqual(code, 1)
        self.assertIn("new-shop does not exist", err)
        self.assertFalse(out.exists())

    def test_existing_site_is_exported_with_its_identity(self) -> None:
        out = Path(tempfile.mkdtemp()) / "backup"
        code, err = self.run_main(["--merchant-id", "11", "--project-id", "22",
                                   "--environment", "test",
                                   "--approved-test-projects", str(allowlist()),
                                   "--slug", "demo-shop", "--output-dir", str(out)])
        self.assertEqual((code, err), (0, ""))
        manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual((manifest["merchant_id"], manifest["project_id"], manifest["environment"]),
                         (11, 22, "test"))
        self.assertTrue(manifest["read_only"])
        self.assertEqual(set(manifest["sha256"]), set(manifest["files"]))

    def test_cli_pointing_elsewhere_stops_before_export(self) -> None:
        out = Path(tempfile.mkdtemp()) / "backup"
        code, err = self.run_main(["--merchant-id", "11", "--project-id", "33",
                                   "--environment", "sandbox",
                                   "--slug", "demo-shop", "--output-dir", str(out)])
        self.assertEqual(code, 1)
        self.assertIn("project_id does not match the target", err)
        self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
