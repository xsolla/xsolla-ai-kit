"""Onboarding approval and ordered readback, using an injected transport only."""
from __future__ import annotations

import copy
import inspect
import unittest

from qs_base import IsolatedCase, count_non_get
import qp_preflight

MERCHANT, PROJECT = "7", "42"
WRITES = {qp_preflight.ONBOARD_PROJECT}


class OperationTransport:
    """Mock transport(operation_id, body=None) -> (status, json). Records every call."""

    def __init__(self, handler):
        self.calls = []
        self.handler = handler

    def __call__(self, operation_id, body=None):
        self.calls.append((operation_id, body))
        return self.handler(operation_id, body)

    @property
    def writes(self) -> int:
        return sum(1 for op, _ in self.calls if op in WRITES)


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
                transport = OperationTransport(lambda op, body: next(ordered_responses))
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
                get = (qp_preflight.GET_PROJECT, None)
                expected_calls = [get]
                if writes:
                    expected_calls += [
                        (qp_preflight.ONBOARD_PROJECT, {"merchant_name": "Acme", "project_name": "Shop"}),
                        get,
                    ]
                self.assertEqual(transport.calls, expected_calls)
                self.assertEqual(transport.writes, writes)
                if responses[0][0] == 404:
                    self.assertEqual(len(questions), 1)
                    self.assertTrue(any(token in questions[0] for token in ("Shop", PROJECT)))
                    self.assertEqual(calls_at_ask, [[(qp_preflight.GET_PROJECT, None)]])
                else:
                    self.assertEqual(questions, [])
                    self.assertEqual(calls_at_ask, [])

    def test_ac_27_non_get_counter_counts_all_write_methods(self) -> None:
        calls = [("GET", "/a"), ("POST", "/a"), ("PUT", "/a"), ("PATCH", "/a"), ("DELETE", "/a")]
        self.assertEqual(count_non_get(calls), 4)
        self.assertEqual(count_non_get(calls[:1]), 0)


if __name__ == "__main__":
    unittest.main()
