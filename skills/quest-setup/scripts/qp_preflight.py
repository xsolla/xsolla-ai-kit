#!/usr/bin/env python3
"""Onboarding preflight: Get project, ask, Onboard project only after a yes, Get project readback.

transport(method, path, body=None) -> (status, json) and confirm(question) -> bool are always
passed in; there are no defaults, so nothing here can reach a network on its own.
"""
from __future__ import annotations


def preflight(merchant_id, project_id, transport, confirm, merchant_name="", project_name=""):
    base = "/api/v2/merchants/%s/projects/%s" % (merchant_id, project_id)
    status, _ = transport("GET", base)
    if status == 200:
        return {"state": "onboarded", "onboard_calls": 0, "readback_status": None}
    if status != 404:
        return {"state": "error", "onboard_calls": 0, "readback_status": None,
                "detail": "Get project returned %s" % status}
    question = ("Project %s (%s) is not onboarded to Quests, or this key has no access. "
                "Onboard it now?" % (project_name or project_id, project_id))
    if not confirm(question):
        return {"state": "declined", "onboard_calls": 0, "readback_status": None}
    body = {"merchant_name": merchant_name, "project_name": project_name}
    onboard_status, _ = transport("POST", base + "/onboard", body)
    if onboard_status != 200:
        return {"state": "error", "onboard_calls": 1, "readback_status": None,
                "detail": "Onboard project returned %s" % onboard_status}
    readback, _ = transport("GET", base)
    state = "onboarded_now" if readback == 200 else "error"
    return {"state": state, "onboard_calls": 1, "readback_status": readback}
