"""The preflight report from recorded /pub responses. No live calls: the fixtures are synthetic
files in the format the agent saves (references/pub-responses.md)."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import harness  # noqa: E402
from harness import common  # noqa: E402

import preflight_report as pre  # noqa: E402

PROVIDERS = ["klarna", "toss"]


def build(pub: Path = harness.PUB, now: str = harness.NOW, slugs: list[str] | None = None) -> dict:
    return pre.build_report(pub, common.load_config(harness.CONFIG), PROVIDERS, pre.parse_time(now),
                            extra_slugs=slugs)


class PreflightReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = build()
        cls.games = {game["slug"]: game for game in cls.report["games"]}

    def details(self, slug: str) -> list[str]:
        return [failure["detail"] for failure in self.games[slug]["failures"]]

    def test_the_bundle_is_complete_and_fresh(self) -> None:
        self.assertTrue(self.report["complete"])
        self.assertTrue(self.report["fresh_for_write"])
        self.assertEqual({"oldest": "2026-11-07T08:55:00Z", "newest": "2026-11-07T09:00:00Z"},
                         self.report["requested_at"])
        self.assertEqual(
            "Responses requested 2026-11-07T08:55:00Z to 2026-11-07T09:00:00Z; the oldest is 2.08 h old "
            "(writes need 24 h or less).",
            self.report["lines"][0],
        )
        self.assertTrue(all(r["requested_at"] for r in self.report["responses"]))
        self.assertEqual(19, len(self.report["responses"]))

    def test_one_line_per_game(self) -> None:
        self.assertEqual([
            "star-forge: ok",
            "river-tactics: ok",
            "media-heavy: media has 23 items → items after the 20th are not shown",
            "broken-cover: cover info returned HTTP 404 → hero renders without an image; fix in the API",
            "long-title-game: title is 72 characters (1 to 60) → fix in the API; "
            "short_description is 160 characters (max 150) → fix in the API",
            "no-faq: faq is empty → combined page FAQ is empty; fix in the API",
            "coin-realm: not payable with klarna, toss → the combined page still exists as a path; "
            "the game cannot be paid with this provider; list for a redirect",
            "hidden-gem: the game is in neither the buy nor the top_up catalog → no page is generated for this game",
        ], self.report["lines"][1:])

    def test_empty_payment_methods_means_any_provider(self) -> None:
        self.assertEqual({"klarna": "any provider", "toss": "any provider"}, self.games["star-forge"]["providers"])

    def test_provider_ids_match_case_insensitively_and_may_repeat(self) -> None:
        # payment_methods holds "Toss" with empty countries, and klarna twice (DE, then AT).
        self.assertEqual({"klarna": 2, "toss": 1}, self.games["river-tactics"]["providers"])
        self.assertEqual([], self.games["river-tactics"]["failures"])

    def test_a_game_not_payable_with_a_provider_is_listed_for_a_redirect(self) -> None:
        self.assertEqual(
            [{"provider": "klarna", "slug": "coin-realm"}, {"provider": "toss", "slug": "coin-realm"}],
            self.report["redirects"],
        )

    def test_a_game_outside_the_catalog_gets_no_page(self) -> None:
        game = self.games["hidden-gem"]
        self.assertFalse(game["in_paths"])
        self.assertEqual([], game["modes"])
        self.assertEqual(["the game is in neither the buy nor the top_up catalog"], self.details("hidden-gem"))

    def test_more_than_20_media_and_a_404_cover(self) -> None:
        self.assertEqual(["media has 23 items"], self.details("media-heavy"))
        self.assertEqual(["cover info returned HTTP 404"], self.details("broken-cover"))

    def test_responses_older_than_24_hours_are_not_fresh_for_a_write(self) -> None:
        report = build(now="2026-11-08T09:00:00Z")
        self.assertTrue(report["complete"])
        self.assertFalse(report["fresh_for_write"])
        self.assertEqual(24.08, report["age_hours"])

    def test_next_lists_what_is_still_to_get(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            pub = Path(directory)
            first = pre.next_urls({}, 200002, [])
            self.assertEqual([
                "https://xla-pages.xsolla.com/pub/catalog/games?page=1&publisher_project_id=200002&size=50",
                "https://xla-pages.xsolla.com/pub/catalog/games?mode=buy&page=1&publisher_project_id=200002&size=50",
                "https://xla-pages.xsolla.com/pub/catalog/games?mode=top_up&page=1&publisher_project_id=200002&size=50",
            ], first)
            for path in harness.PUB.glob("*.json"):
                if path.name not in ("game-no-faq.json", "media-star-forge-cover.json"):
                    shutil.copy(path, pub / path.name)
            responses, errors = pre.load_bundle(pub)
            self.assertEqual([], errors)
            self.assertEqual([
                "https://xla-pages.xsolla.com/pub/media/00000000-0000-4000-8000-000000000001/info",
                "https://xla-pages.xsolla.com/pub/games/no-faq/core-attributes?project_id=200002",
            ], pre.next_urls(responses, 200002, []))
            report = build(pub)
            self.assertFalse(report["complete"])
            self.assertIn("no-faq: not fetched yet → fetch it", report["lines"])

    def test_a_full_catalog_page_asks_for_the_next_one(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            pub = Path(directory)
            saved = json.loads((harness.PUB / "catalog-buy-p1.json").read_text(encoding="utf-8"))
            body = json.loads(saved["body"])
            body["data"] = [{**body["data"][0], "slug": f"game-{i}"} for i in range(50)]
            saved["body"] = json.dumps(body)
            (pub / "catalog-buy-p1.json").write_text(json.dumps(saved), encoding="utf-8")
            responses, _ = pre.load_bundle(pub)
            self.assertIn(
                "https://xla-pages.xsolla.com/pub/catalog/games?mode=buy&page=2&publisher_project_id=200002&size=50",
                pre.next_urls(responses, 200002, []),
            )

    def test_a_saved_file_must_be_a_get_to_pub(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            pub = Path(directory)
            for path in harness.PUB.glob("*.json"):
                shutil.copy(path, pub / path.name)
            bad = json.loads((pub / "game-star-forge.json").read_text(encoding="utf-8"))
            (pub / "post.json").write_text(json.dumps({**bad, "method": "POST"}), encoding="utf-8")
            (pub / "admin.json").write_text(
                json.dumps({**bad, "url": "https://xla-pages.xsolla.com/integration/games"}), encoding="utf-8")
            (pub / "no-time.json").write_text(json.dumps({**bad, "requested_at": "yesterday"}), encoding="utf-8")
            report = build(pub)
            self.assertFalse(report["complete"])
            self.assertEqual([
                "admin.json: url must start with https://xla-pages.xsolla.com/pub/",
                "no-time.json: requested_at must be an ISO 8601 time with a timezone",
                "post.json: method must be GET",
            ], report["errors"])

    def test_the_command_line_prints_the_report(self) -> None:
        import contextlib
        import io

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = pre.main(["report", "--pub-dir", str(harness.PUB), "--config", str(harness.CONFIG),
                             "--batch", str(harness.FIXTURES / "batch.json"), "--now", harness.NOW])
        self.assertEqual(0, code)
        self.assertEqual(self.report["lines"], json.loads(out.getvalue())["lines"])


if __name__ == "__main__":
    unittest.main()
