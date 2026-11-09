"""Onboarding approval and ordered readback, using an injected transport only."""
from __future__ import annotations

import copy
import inspect
import unittest

from qs_base import IsolatedCase, RecordingTransport, count_non_get
import qp_preflight

MERCHANT, PROJECT = "7", "42"
PROJECT_PATH = "/api/v2/merchants/7/projects/42"


class PreflightTests(IsolatedCase):
    def test_ac_02_transport_is_required_not_defaulted(self) -> None:
        params = inspect.signature(qp_preflight.preflight).parameters
        for name in ("transport", "confirm"):
            self.assertIn(name, params)
            self.assertIs(params[name].default, inspect.Parameter.empty)

    def test_named_onboarding_outcomes(self) -> None:
        rows = (
            ("404_declined", ((404, {"error": "not found"}),), False, "declined", 0, None),
            ("404_confirmed_readback_200",
             ((404, {"error": "not found"}), (200, {"ok": True}), (200, {"project_id": "42"})),
             True, "onboarded_now", 1, 200),
            ("404_confirmed_readback_404",
             ((404, {"error": "not found"}), (200, {"ok": True}), (404, {"error": "not found"})),
             True, "error", 1, 404),
            ("200_already_onboarded", ((200, {"project_id": "42"}),), True, "onboarded", 0, None),
        )
        for case, responses, answer, state, writes, readback in rows:
            with self.subTest(case=case):
                ordered_responses = iter(copy.deepcopy(responses))
                transport = RecordingTransport(lambda method, path, body: next(ordered_responses))
                questions, calls_at_ask = [], []

                def confirm(question):
                    questions.append(question)
                    calls_at_ask.append(list(transport.calls))
                    return answer

                result = qp_preflight.preflight(MERCHANT, PROJECT, transport, confirm,
                                                merchant_name="Acme", project_name="Shop")
                self.assertEqual(result["state"], state)
                self.assertEqual(result["onboard_calls"], writes)
                self.assertEqual(result["readback_status"], readback)
                expected_calls = [("GET", PROJECT_PATH, None)]
                if writes:
                    expected_calls += [
                        ("POST", PROJECT_PATH + "/onboard", {"merchant_name": "Acme", "project_name": "Shop"}),
                        ("GET", PROJECT_PATH, None),
                    ]
                self.assertEqual(transport.calls, expected_calls)
                self.assertEqual(transport.non_get, writes)
                if responses[0][0] == 404:
                    self.assertEqual(len(questions), 1)
                    self.assertTrue(any(token in questions[0] for token in ("Shop", PROJECT)))
                    self.assertEqual(calls_at_ask, [[("GET", PROJECT_PATH, None)]])
                    self.assertEqual(count_non_get(calls_at_ask[0]), 0)
                else:
                    self.assertEqual(questions, [])
                    self.assertEqual(calls_at_ask, [])

    def test_ac_27_non_get_counter_counts_all_write_methods(self) -> None:
        calls = [("GET", "/a"), ("POST", "/a"), ("PUT", "/a"), ("PATCH", "/a"), ("DELETE", "/a")]
        self.assertEqual(count_non_get(calls), 4)
        self.assertEqual(count_non_get(calls[:1]), 0)


if __name__ == "__main__":
    unittest.main()
