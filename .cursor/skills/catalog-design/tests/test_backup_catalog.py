"""backup_catalog.py: reads the catalog through the CLI and diffs it against a backup."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import backup_catalog  # noqa: E402

CONFIG = {"merchant_id": 1, "project_id": 2, "sandbox": True}
CATALOG = {
    "admin-list-currency": [{"sku": "gems"}],
    "admin-list-currency-packages": [{"sku": "gems-100"}],
    "list-items": [{"sku": "booster"}, {"sku": "sword"}],
    "list-bundles": [{"sku": "starter"}],
    "list-item-groups": {"groups": [{"external_id": "root", "children": [{"external_id": "kid", "children": []}]}]},
}


def completed(data, returncode=0, stderr=""):
    stdout = json.dumps({"ok": True, "data": data}) if returncode == 0 else ""
    return subprocess.CompletedProcess([], returncode, stdout=stdout, stderr=stderr)


def fake_cli(catalog):
    def run(cmd, **_kwargs):
        args = cmd[1:]
        if args[:2] == ["config", "list"]:
            return completed(CONFIG)
        return completed(catalog[args[1]])
    return run


class BackupCatalogTest(unittest.TestCase):
    def test_backup_writes_every_type_and_flattens_groups(self):
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(subprocess, "run", side_effect=fake_cli(CATALOG)), \
                mock.patch("sys.stdout"):
            path = backup_catalog.backup(Path(tmp))
            document = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(document["context"], CONFIG)
        self.assertEqual([g["external_id"] for g in document["catalog"]["groups"]], ["root", "kid"])
        self.assertEqual(len(document["catalog"]["items"]), 2)
        self.assertTrue(path.name.startswith("catalog-2-"))

    def test_every_call_is_a_read_with_json(self):
        calls = []

        def run(cmd, **kwargs):
            calls.append(cmd)
            return fake_cli(CATALOG)(cmd, **kwargs)

        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(subprocess, "run", side_effect=run), mock.patch("sys.stdout"):
            backup_catalog.backup(Path(tmp))
        for cmd in calls:
            self.assertEqual(cmd[0], "xsolla")
            self.assertEqual(cmd[-1], "--json")
            self.assertTrue(cmd[2].startswith(("list", "admin-list")), cmd)

    def test_compare_reports_added_and_removed(self):
        after = dict(CATALOG, **{"list-items": [{"sku": "sword"}, {"sku": "clitest-new"}]})
        before = {"context": CONFIG, "taken_at": "t", "catalog": {
            "currencies": [{"sku": "gems"}], "currency_packages": [{"sku": "gems-100"}],
            "items": [{"sku": "booster"}, {"sku": "sword"}], "bundles": [{"sku": "starter"}],
            "groups": [{"external_id": "root"}, {"external_id": "kid"}]}}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "b.json"
            path.write_text(json.dumps(before), encoding="utf-8")
            with mock.patch.object(subprocess, "run", side_effect=fake_cli(after)), \
                    mock.patch("builtins.print") as printed:
                code = backup_catalog.compare(path)
        self.assertEqual(code, 1)
        changes = json.loads(printed.call_args[0][0])
        self.assertEqual(changes, {"items": {"added": ["clitest-new"], "removed": ["booster"]}})

    def test_compare_matches(self):
        before = {"context": CONFIG, "taken_at": "t", "catalog": {
            "currencies": [{"sku": "gems"}], "currency_packages": [{"sku": "gems-100"}],
            "items": [{"sku": "sword"}, {"sku": "booster"}], "bundles": [{"sku": "starter"}],
            "groups": [{"external_id": "kid"}, {"external_id": "root"}]}}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "b.json"
            path.write_text(json.dumps(before), encoding="utf-8")
            with mock.patch.object(subprocess, "run", side_effect=fake_cli(CATALOG)), mock.patch("sys.stdout"):
                self.assertEqual(backup_catalog.compare(path), 0)

    def test_compare_refuses_another_project(self):
        before = {"context": dict(CONFIG, project_id=99), "catalog": {}}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "b.json"
            path.write_text(json.dumps(before), encoding="utf-8")
            with mock.patch.object(subprocess, "run", side_effect=fake_cli(CATALOG)):
                with self.assertRaisesRegex(backup_catalog.CatalogError, "project 99"):
                    backup_catalog.compare(path)

    def test_auth_failure_points_to_merchant_setup(self):
        with mock.patch.object(subprocess, "run", return_value=completed(None, returncode=10)):
            with self.assertRaisesRegex(backup_catalog.CatalogError, "merchant-setup"):
                backup_catalog.run_cli(["catalog", "list-items"])

    def test_failure_reads_stderr(self):
        failed = completed(None, returncode=40, stderr='{"ok":false,"error":{"code":"http_404"}}')
        with mock.patch.object(subprocess, "run", return_value=failed):
            with self.assertRaisesRegex(backup_catalog.CatalogError, "http_404"):
                backup_catalog.run_cli(["catalog", "list-items"])

    def test_missing_ids_refused(self):
        def run(cmd, **_kwargs):
            return completed({"merchant_id": 0, "project_id": 0})
        with mock.patch.object(subprocess, "run", side_effect=run):
            with self.assertRaisesRegex(backup_catalog.CatalogError, "merchant-setup"):
                backup_catalog.read_context()

    def test_main_exits_2_on_error(self):
        with mock.patch.object(subprocess, "run", side_effect=FileNotFoundError), \
                mock.patch("sys.stderr"):
            self.assertEqual(backup_catalog.main(["--out-dir", "unused"]), 2)


if __name__ == "__main__":
    unittest.main()
