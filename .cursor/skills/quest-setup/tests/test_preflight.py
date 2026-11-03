"""AC-2, AC-13..15, AC-27: onboarding preflight (scripts/qp_preflight.py) against a mock transport."""
from __future__ import annotations

import inspect
import unittest

import qs_base
from qs_base import IsolatedCase, RecordingTransport, count_non_get

import qp_preflight

MERCHANT, PROJECT = "7", "42"
PROJECT_PATH = f"/api/v2/merchants/{MERCHANT}/projects/{PROJECT}"


def is_onboard(call) -> bool:
    """Assumption (live docs): Onboard project is a POST in the merchant/project path family.

    The exact path is not asserted: any POST whose path contains 'onboard' or ends with the
    project path counts as an Onboard project call.
    """
    method, path = call[0], call[1]
    return method == "POST" and ("onboard" in path.lower() or path.rstrip("/").endswith(PROJECT_PATH))


def is_get_project(call) -> bool:
    return call[0] == "GET" and call[1].rstrip("/") == PROJECT_PATH


def make_transport(initial_status: int, after_onboard_status: int = 200) -> RecordingTransport:
    state = {"onboarded": initial_status == 200}

    def handler(method, path, body):
        if method == "GET" and path.rstrip("/") == PROJECT_PATH:
            if state["onboarded"]:
                return 200, {"project_id": PROJECT}
            return initial_status, {"error": "not found"}
        if is_onboard((method, path)):
            if after_onboard_status == 200:
                state["onboarded"] = True
            else:
                initial_status_after[0] = after_onboard_status
            return 200, {"ok": True}
        return 404, {}

    initial_status_after = [initial_status]

    def wrapped(method, path, body):
        status, payload = handler(method, path, body)
        if method == "GET" and path.rstrip("/") == PROJECT_PATH and not state["onboarded"]:
            return initial_status_after[0], payload
        return status, payload

    return RecordingTransport(wrapped)


class Confirm:
    def __init__(self, answer: bool, transport: RecordingTransport):
        self.answer = answer
        self.transport = transport
        self.questions = []
        self.onboard_calls_at_ask = []

    def __call__(self, question: str) -> bool:
        self.questions.append(question)
        self.onboard_calls_at_ask.append(sum(1 for c in self.transport.calls if is_onboard(c)))
        return self.answer


class PreflightTests(IsolatedCase):
    def run_preflight(self, transport, answer=True):
        confirm = Confirm(answer, transport)
        result = qp_preflight.preflight(MERCHANT, PROJECT, transport, confirm,
                                        merchant_name="Acme", project_name="Shop")
        return result, confirm

    def test_ac_02_transport_is_required_not_defaulted(self) -> None:
        params = inspect.signature(qp_preflight.preflight).parameters
        for name in ("transport", "confirm"):
            self.assertIn(name, params)
            self.assertIs(params[name].default, inspect.Parameter.empty)

    def test_ac_02_zero_onboard_calls_before_a_yes(self) -> None:
        transport = make_transport(404)
        result, confirm = self.run_preflight(transport, answer=True)
        self.assertEqual(len(confirm.questions), 1)
        self.assertEqual(confirm.onboard_calls_at_ask, [0])
        self.assertEqual(result["onboard_calls"], 1)
        self.assertIsInstance(transport, RecordingTransport)

    def test_ac_02_no_yes_means_no_onboard_call(self) -> None:
        transport = make_transport(404)
        result, _ = self.run_preflight(transport, answer=False)
        self.assertEqual(result["onboard_calls"], 0)
        self.assertEqual(sum(1 for c in transport.calls if is_onboard(c)), 0)

    def test_ac_13_404_reports_not_onboarded_and_asks_first(self) -> None:
        transport = make_transport(404)
        result, confirm = self.run_preflight(transport, answer=False)
        self.assertIn(result["state"], ("declined", "not_onboarded"))
        self.assertEqual(len(confirm.questions), 1)
        self.assertEqual(confirm.onboard_calls_at_ask, [0])
        self.assertEqual(result["onboard_calls"], 0)
        self.assertEqual(transport.non_get, 0)
        self.assertTrue(is_get_project(transport.calls[0]))

    def test_ac_13_question_names_the_project(self) -> None:
        transport = make_transport(404)
        _, confirm = self.run_preflight(transport, answer=False)
        self.assertTrue(confirm.questions)
        self.assertTrue(any(token in confirm.questions[0] for token in ("Shop", PROJECT)))

    def test_ac_14_confirmed_onboard_then_get_readback(self) -> None:
        transport = make_transport(404)
        result, _ = self.run_preflight(transport, answer=True)
        kinds = ["onboard" if is_onboard(c) else "get_project" if is_get_project(c) else "other"
                 for c in transport.calls]
        self.assertEqual(kinds, ["get_project", "onboard", "get_project"])
        self.assertEqual(result["state"], "onboarded_now")
        self.assertEqual(result["onboard_calls"], 1)
        self.assertEqual(result["readback_status"], 200)

    def test_ac_14_not_reported_onboarded_when_readback_is_not_200(self) -> None:
        transport = make_transport(404, after_onboard_status=404)
        result, _ = self.run_preflight(transport, answer=True)
        self.assertNotIn(result["state"], ("onboarded", "onboarded_now"))
        self.assertEqual(result["state"], "error")
        self.assertEqual(result["readback_status"], 404)
        self.assertEqual(result["onboard_calls"], 1)

    def test_ac_15_already_onboarded_makes_no_onboard_call(self) -> None:
        transport = make_transport(200)
        result, confirm = self.run_preflight(transport, answer=True)
        self.assertEqual(result["state"], "onboarded")
        self.assertEqual(result["onboard_calls"], 0)
        self.assertEqual(confirm.questions, [])
        self.assertEqual(sum(1 for c in transport.calls if is_onboard(c)), 0)
        self.assertEqual(transport.non_get, 0)

    def test_ac_27_non_get_counter_counts_all_write_methods(self) -> None:
        calls = [("GET", "/a"), ("POST", "/a"), ("PUT", "/a"), ("PATCH", "/a"), ("DELETE", "/a")]
        self.assertEqual(count_non_get(calls), 4)
        self.assertEqual(count_non_get(calls[:1]), 0)

    def test_ac_27_preflight_declined_is_no_write(self) -> None:
        transport = make_transport(404)
        self.run_preflight(transport, answer=False)
        self.assertEqual(transport.non_get, 0)
        self.assertGreaterEqual(len(transport.calls), 1)


if __name__ == "__main__":
    unittest.main()
