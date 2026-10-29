import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from read_onboarding import main, read_onboarding


class OnboardingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / ".xsolla").mkdir()
        self.path = self.root / ".xsolla/onboarding.json"
        self.ledger = {
            "version": 1, "path": "shopbuilder", "site_kind": "shop",
            "intake": {
                "game_name": "Tidepool", "platforms": ["iOS", "Android"],
                "description": "A cozy mobile farming sim.",
                "domain": "tidepool-shop", "primary_locale": "de-DE",
                "locales": ["de-DE", "en-US"],
                "brand_assets": {"logo": "assets/logo.png"},
                "store_url": "https://example.com/tidepool",
            },
        }

    def save(self):
        self.path.write_text(json.dumps(self.ledger))

    def test_confirmed_answers_preserved_without_step_status(self):
        self.save()
        self.assertEqual(read_onboarding(self.root), {
            "status": "loaded", "site_kind": "shop", "intake": self.ledger["intake"],
        })

    def test_no_file_means_normal_intake_not_error(self):
        self.assertEqual(read_onboarding(self.root), {
            "status": "absent", "site_kind": "shop", "intake": {},
        })
        self.assertFalse(self.path.exists())

    def test_missing_and_empty_answers_not_fabricated(self):
        for intake in ({}, {"game_name": "", "platforms": [], "description": None}):
            with self.subTest(intake=intake):
                self.ledger["intake"] = intake
                self.save()
                self.assertEqual(read_onboarding(self.root)["intake"], intake)

    def test_missing_intake_is_partial(self):
        del self.ledger["intake"]
        self.save()
        self.assertEqual(read_onboarding(self.root)["intake"], {})

    def test_malformed_ledger_is_not_absent(self):
        self.path.write_text('{"version":')
        with self.assertRaisesRegex(ValueError, "Cannot parse"):
            read_onboarding(self.root)

    def test_invalid_shapes_and_versions_stop(self):
        for ledger in ([], None, {"version": 2}, {"version": True}):
            with self.subTest(ledger=ledger):
                self.ledger = ledger
                self.save()
                with self.assertRaises(ValueError):
                    read_onboarding(self.root)

    def test_nonobject_intake_stops(self):
        self.ledger["intake"] = []
        self.save()
        with self.assertRaisesRegex(ValueError, "intake must be an object"):
            read_onboarding(self.root)

    def test_headless_ledger_stops(self):
        self.ledger["path"] = "headless"
        self.save()
        with self.assertRaisesRegex(ValueError, "shop the user codes"):
            read_onboarding(self.root)

    def test_legacy_empty_or_absent_site_kind_means_shop(self):
        for kind in ("", None):
            with self.subTest(kind=kind):
                if kind is None:
                    del self.ledger["site_kind"]
                else:
                    self.ledger["site_kind"] = kind
                self.save()
                self.assertEqual(read_onboarding(self.root)["site_kind"], "shop")

    def test_portal_remains_portal(self):
        self.ledger["site_kind"] = "portal"
        self.save()
        self.assertEqual(read_onboarding(self.root)["site_kind"], "portal")

    def test_invalid_site_kind_stops(self):
        self.ledger["site_kind"] = "Shop"
        self.save()
        with self.assertRaisesRegex(ValueError, "site_kind"):
            read_onboarding(self.root)

    def test_missing_env_still_loads(self):
        self.save()
        self.assertFalse((self.root / ".env").exists())
        self.assertEqual(read_onboarding(self.root)["status"], "loaded")

    def test_only_intake_returned_no_credentials_or_step_ids(self):
        (self.root / ".env").write_text("XSOLLA_PROJECT_API_KEY=secret-sentinel\n")
        self.ledger["intake"]["api_key"] = "secret-sentinel"
        self.ledger["steps"] = [{"id": "merchant", "ids": {"project_id": 12345}}]
        self.save()
        output = json.dumps(read_onboarding(self.root))
        self.assertNotIn("secret-sentinel", output)
        self.assertNotIn("project_id", output)

    def test_read_and_cli_leave_files_unchanged(self):
        self.save()
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(["--project-root", str(self.root)]), 0)
        self.assertEqual(json.loads(output.getvalue())["intake"], self.ledger["intake"])
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()})

    def test_cli_error_nonzero_without_echoing_corrupt_content(self):
        self.path.write_text("secret-sentinel")
        output, error = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
            self.assertEqual(main(["--project-root", str(self.root)]), 1)
        self.assertEqual(output.getvalue(), "")
        self.assertNotIn("secret-sentinel", error.getvalue())


if __name__ == "__main__":
    unittest.main()
