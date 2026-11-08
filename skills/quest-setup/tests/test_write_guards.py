"""AC-20, AC-22, AC-25, AC-26 (+AC-27 definition): write guards, 403 handling, no-write declines."""
from __future__ import annotations

import json
import unittest
import urllib.error
import urllib.request
from io import BytesIO
from unittest import mock

from qs_base import SENTINEL_ENV, IsolatedCase, count_non_get
import qp_request

QUESTS = "/api/v2/merchants/7/projects/42/quests"
BLOCKS = "/api/v2/merchants/7/projects/42/blocks"
QUEST = {"name": "q", "type": "liveops", "status": "inactive", "created_by": "AI Toolkit"}


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
        payload = dict(QUEST, public_view={"image_url": "http://cdn.example.test/a.png"})
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
        payload = dict(QUEST, public_view={"image_url": "https://cdn.example.test/a.png"})
        code, out, _ = self.post_body(QUESTS, payload)
        self.assertEqual(code, 0)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0][0], "POST")

    def test_ac_22_403_on_a_write_is_one_call_no_retry_no_files(self) -> None:
        def forbidden(opener, request, *args, **kwargs):
            self.calls.append((request.get_method(), request.full_url))
            raise urllib.error.HTTPError(request.full_url, 403, "Forbidden", {}, BytesIO(b"forbidden"))

        before = self.tree(self.tmp)
        with mock.patch.object(urllib.request.OpenerDirector, "open", forbidden):
            code, out, _ = self.post_body(QUESTS, QUEST)
        after = [p for p in self.tree(self.tmp) if p != "body.json"]
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out)["error"], "access_denied")
        self.assertEqual(len(self.calls), 1)
        self.assertEqual([p for p in after if p not in before], [])

    def test_undocumented_route_is_never_called(self) -> None:
        code, out, _ = self.post_body("/api/v2/merchants/7/projects/42/custom-blocks", QUEST)
        self.assertEqual(json.loads(out), {"ok": False, "error": "target_not_allowed"})
        self.assertEqual(self.calls, [])


    def test_ac_27_recorded_calls_use_the_non_get_definition(self) -> None:
        self.capture(qp_request.main, ["GET", QUESTS], environ=dict(SENTINEL_ENV))
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(count_non_get(self.calls), 0)
        self.post_body(QUESTS, QUEST)
        self.assertEqual(count_non_get(self.calls), 1)


if __name__ == "__main__":
    unittest.main()
