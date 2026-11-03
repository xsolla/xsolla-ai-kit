"""AC-20, AC-22, AC-25, AC-26 (+AC-27 definition): write guards, 403 handling, no-write declines."""
from __future__ import annotations

import json
import re
import unittest
import urllib.error
import urllib.request
from io import BytesIO
from unittest import mock

import qp_request
import qs_base
from qs_base import SENTINEL_ENV, IsolatedCase, count_non_get

QUESTS = "/api/v2/merchants/7/projects/42/quests"
BLOCKS = "/api/v2/merchants/7/projects/42/blocks"


def corpus() -> str:
    parts = [qs_base.read_text(qs_base.SKILL / "SKILL.md")]
    parts += [qs_base.read_text(p) for p in sorted(qs_base.REFERENCES.glob("*.md"))]
    return "\n".join(parts)


def squash(text: str) -> str:
    return re.sub(r"\s+", " ", text)


class WriteGuardTests(IsolatedCase):
    def setUp(self) -> None:
        super().setUp()
        self.calls = []

        def fake_open(opener, request, *args, **kwargs):
            self.calls.append((request.get_method(), request.full_url))
            resp = mock.MagicMock()
            resp.status = 200
            resp.read.return_value = b"{}"
            return resp

        patcher = mock.patch.object(urllib.request.OpenerDirector, "open", fake_open)
        patcher.start()
        self.addCleanup(patcher.stop)

    def post_body(self, path, payload):
        body = self.tmp / "body.json"
        body.write_text(json.dumps(payload), encoding="utf-8")
        return self.capture(qp_request.main, ["POST", path, "--body-file", str(body)],
                            environ=dict(SENTINEL_ENV))

    def test_ac_20_http_quest_image_is_rejected_before_any_call(self) -> None:
        payload = {"name": "q", "public_view": {"image_url": "http://cdn.example.test/a.png"}}
        code, out, err = self.post_body(QUESTS, payload)
        self.assertIn("https only", out + err)
        self.assertNotEqual(code, 0)
        self.assertEqual(self.calls, [])
        self.assertEqual(count_non_get(self.calls), 0)

    def test_ac_20_http_block_image_override_is_rejected(self) -> None:
        payload = {"overrides": {"q1": {"imageUrl": "http://cdn.example.test/a.png"}}}
        code, out, err = self.post_body(BLOCKS, payload)
        self.assertIn("https only", out + err)
        self.assertEqual(self.calls, [])

    def test_ac_20_https_image_is_sent(self) -> None:
        payload = {"name": "q", "public_view": {"image_url": "https://cdn.example.test/a.png"}}
        code, out, _ = self.post_body(QUESTS, payload)
        self.assertEqual(code, 0)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0][0], "POST")

    def test_ac_22_403_on_create_custom_block_one_call_no_retry_no_files(self) -> None:
        def forbidden(opener, request, *args, **kwargs):
            self.calls.append((request.get_method(), request.full_url))
            raise urllib.error.HTTPError(request.full_url, 403, "Forbidden", {}, BytesIO(b"forbidden"))

        before = self.tree(self.tmp)
        with mock.patch.object(urllib.request.OpenerDirector, "open", forbidden):
            code, out, _ = self.post_body("/api/v2/merchants/7/projects/42/custom-blocks", {"name": "x"})
        after = [p for p in self.tree(self.tmp) if p != "body.json"]
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out)["error"], "access_denied")
        self.assertEqual(len(self.calls), 1)
        self.assertEqual([p for p in after if p not in before], [])
        self.assertFalse((self.home / ".cache").exists())

    def test_ac_22_reply_text_for_403_exists_in_guidance(self) -> None:
        text = squash(corpus())
        self.assertRegex(text, re.compile(r"(lacks|does not have) permission to create custom blocks", re.I))
        self.assertRegex(text, re.compile(r"Xsolla support", re.I))
        self.assertRegex(text, re.compile(r"(do not|never|no) retry|does not retry", re.I))

    def test_ac_25_unexpressible_design_states_limit_and_alternative_no_write(self) -> None:
        text = squash(corpus())
        self.assertRegex(text, re.compile(r"(schema )?(cannot|can't|can not) express", re.I))
        self.assertRegex(text, re.compile(r"(Site Builder|Xsolla Pages) theme", re.I))
        self.assertRegex(text, re.compile(r"(makes?|make) no write|no write is made|without writing", re.I))

    def test_ac_26_theme_selector_maps_default_and_pages(self) -> None:
        text = squash(corpus())
        self.assertRegex(text, re.compile(r"default[^.|]{0,80}site-builder", re.I))
        self.assertRegex(text, re.compile(r"Xsolla Pages[^.|]{0,80}xsolla-pages", re.I))

    def test_ac_26_backpack_overlay_declined_with_exact_phrase_and_no_write(self) -> None:
        text = squash(corpus())
        self.assertIn("blocked on upstream v2", text)
        self.assertRegex(text, re.compile(r"Backpack Overlay", re.I))

    def test_ac_27_recorded_calls_use_the_non_get_definition(self) -> None:
        self.capture(qp_request.main, ["GET", QUESTS], environ=dict(SENTINEL_ENV))
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(count_non_get(self.calls), 0)
        self.post_body(QUESTS, {"name": "q"})
        self.assertEqual(count_non_get(self.calls), 1)


if __name__ == "__main__":
    unittest.main()
