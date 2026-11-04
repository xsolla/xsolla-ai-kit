from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import store_url  # noqa: E402


class StoreUrlTests(unittest.TestCase):
    def test_accepts_the_three_exact_store_hosts(self) -> None:
        cases = {
            "https://store.steampowered.com/app/570/Dota_2/": ("steam", "pc", "570"),
            "https://store.steampowered.com/app/570": ("steam", "pc", "570"),
            "https://apps.apple.com/us/app/space-raiders/id1234567890": (
                "app_store", "mobile", "1234567890"
            ),
            "https://apps.apple.com/app/id1234567890": ("app_store", "mobile", "1234567890"),
            "https://play.google.com/store/apps/details?id=com.example.raiders&hl=en": (
                "google_play", "mobile", "com.example.raiders"
            ),
            "https://PLAY.google.com/store/apps/details?id=com.example.raiders": (
                "google_play", "mobile", "com.example.raiders"
            ),
        }
        for url, (store, platform, app_id) in cases.items():
            with self.subTest(url):
                self.assertEqual(
                    {"store": store, "platform": platform, "app_id": app_id},
                    store_url.classify(url),
                )

    def test_refuses_look_alikes_and_tricks(self) -> None:
        for url in (
            "https://apps.apple.com.example.net/us/app/x/id1",
            "https://play-google.com/store/apps/details?id=com.example.raiders",
            "https://store.steampowered.com.evil.io/app/570",
            "https://evil.example/?u=https://store.steampowered.com/app/570",
            "https://apps.apple.com@evil.example/app/id1",
            "https://user@play.google.com/store/apps/details?id=com.example.raiders",
            "https://store.steampowered.com:8443/app/570",
            "http://store.steampowered.com/app/570",
            "store.steampowered.com/app/570",
            "https://itunes.apple.com/us/app/x/id1",
            "https://www.roblox.com/games/1",
            "https://apps.apple.com/us/app/x/id\uff11\uff12\uff13",
            "https://store.steampowered.com/app/\u0665\u0667\u0660/",
            "https://store.steampowered.com/app/570/../../sub/1",
            "https://[store.steampowered.com/app/1",
            "https://evil.com\uff20store.steampowered.com/app/1",
            "https://store.steam\tpowered.com/app/1",
            "",
        ):
            with self.subTest(url):
                self.assertIn("needs_input", store_url.classify(url))

    def test_refuses_a_store_url_that_names_no_app(self) -> None:
        for url in (
            "https://store.steampowered.com/",
            "https://store.steampowered.com/app/notanumber",
            "https://apps.apple.com/us/developer/example/id99",
            "https://play.google.com/store/apps/details",
            "https://play.google.com/store/apps/details?id=raiders",
            "https://play.google.com/store/apps/details?id=a.b&id=c.d",
            "https://play.google.com/store/apps/dev?id=123",
        ):
            with self.subTest(url):
                self.assertIn("doesn't name one app", store_url.classify(url)["needs_input"])

    def test_command_line_prints_json_and_exits_1_for_needs_input(self) -> None:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = store_url.main(["https://apps.apple.com/us/app/x/id42"])
        self.assertEqual(0, code)
        self.assertEqual("app_store", json.loads(stdout.getvalue())["store"])
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = store_url.main(["https://apps.apple.com.example.net/app/id42"])
        self.assertEqual(1, code)

    def test_runs_under_python_isolated_mode(self) -> None:
        result = subprocess.run(
            [sys.executable, "-I", str(ROOT / "scripts" / "store_url.py"),
             "https://play.google.com/store/apps/details?id=com.example.raiders"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)


if __name__ == "__main__":
    unittest.main()
