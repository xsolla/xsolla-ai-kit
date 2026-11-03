#!/usr/bin/env python3
"""Onboarding preflight: Get project, ask, Onboard project only after a yes, Get project readback.

Library use: preflight(...) takes transport(method, path, body=None) -> (status, json) and
confirm(question) -> bool. There are no defaults, so nothing there can reach a network on its own.

CLI (same credential lane as qp_request.py; keys are never printed):
    python3 qp_preflight.py check
    python3 qp_preflight.py onboard --merchant-name NAME --project-name NAME [--yes]

`onboard` without --yes only prints the proposal and exits 2 with no POST. With --yes (the
publisher's explicit yes in the same conversation) it runs Get project, Onboard project, then the
Get project readback. Exit codes: 0 onboarded (already or now), 1 failure, 2 not sent.
Python 3.9+, standard library only.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

MAX_NAME_CHARS = 200
ID_RE = re.compile(r"[0-9]+")
CONTROL_RE = re.compile(r"[\x00-\x1f\x7f-\x9f]")


def valid_name(value):
    """A non-empty string of at most 200 chars with no control characters."""
    return (isinstance(value, str) and bool(value.strip()) and len(value) <= MAX_NAME_CHARS
            and not CONTROL_RE.search(value))


def valid_id(value):
    """A whole number, as an int or a digit string. 0 is a valid id (see auth-credentials.md)."""
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return value >= 0
    return isinstance(value, str) and bool(ID_RE.fullmatch(value))


def _outcome(state, onboard_calls=0, readback_status=None, detail=None):
    result = {"state": state, "onboard_calls": onboard_calls, "readback_status": readback_status}
    if detail:
        result["detail"] = detail
    return result


def _question(project_name, project_id):
    return ("Get project returned 404 for project %s (%s). Per the live docs the same 404 means "
            "either the project is not onboarded to Quests, or this credential has no access to "
            "that merchant or project. Onboard it now? A yes is only confirmed by a Get project "
            "readback." % (project_name or project_id, project_id))


def preflight(merchant_id, project_id, transport, confirm, merchant_name="", project_name=""):
    if not valid_id(merchant_id) or not valid_id(project_id):
        return _outcome("error", detail="invalid merchant or project id")
    base = "/api/v2/merchants/%s/projects/%s" % (merchant_id, project_id)
    status, _ = transport("GET", base)
    if status == 200:
        return _outcome("onboarded")
    if status != 404:
        return _outcome("error", detail="Get project returned %s" % status)
    if not valid_name(merchant_name) or not valid_name(project_name):
        return _outcome("error", detail="merchant_name and project_name must be non-empty text "
                                        "of at most %d characters without control characters"
                        % MAX_NAME_CHARS)
    if confirm(_question(project_name, project_id)) is not True:
        return _outcome("declined")
    body = {"merchant_name": merchant_name, "project_name": project_name}
    onboard_status, _ = transport("POST", base + "/onboard", body)
    if not isinstance(onboard_status, int) or not 200 <= onboard_status < 300:
        return _outcome("error", 1, None, "Onboard project returned %s" % onboard_status)
    readback, _ = transport("GET", base)
    return _outcome("onboarded_now" if readback == 200 else "error", 1, readback)


def _emit(obj):
    print(json.dumps(obj, ensure_ascii=False))


def _make_transport(creds, qp_request):
    def transport(method, path, body=None):
        qp_request.check_shape(method, path, False)
        url = qp_request.build_url(path, False, creds)
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            if qp_request.route_kind(path) == "onboard":
                qp_request.check_onboard_body(data)
        result = qp_request.send(method, url, creds, data)
        return result.get("status", 0), result.get("body")
    return transport


def main(argv=None, environ=None, cwd=None, send_transport=None):
    import qp_request

    args = list(sys.argv[1:] if argv is None else argv)
    env = os.environ if environ is None else environ
    folder = Path(cwd) if cwd is not None else Path.cwd()
    if not args or args[0] not in ("check", "onboard"):
        _emit({"ok": False, "error": "usage"})
        return 2
    command, rest = args[0], args[1:]
    merchant_name = project_name = None
    yes = False
    i = 0
    while i < len(rest):
        item = rest[i]
        if command == "onboard" and item == "--yes":
            yes = True
        elif command == "onboard" and item in ("--merchant-name", "--project-name") and i + 1 < len(rest):
            if item == "--merchant-name":
                merchant_name = rest[i + 1]
            else:
                project_name = rest[i + 1]
            i += 1
        else:
            _emit({"ok": False, "error": "usage"})
            return 2
        i += 1
    if command == "onboard" and (not valid_name(merchant_name) or not valid_name(project_name)):
        _emit({"ok": False, "error": "invalid_names"})
        return 2
    try:
        creds = qp_request.resolve_credentials(env, folder)
    except qp_request.Refusal as refusal:
        _emit({"ok": False, "error": refusal.error})
        return 2
    transport = send_transport or _make_transport(creds, qp_request)

    if command == "check":
        base = "/api/v2/merchants/%s/projects/%s" % (creds.merchant_id, creds.project_id)
        try:
            status, _ = transport("GET", base)
        except qp_request.Refusal as refusal:
            _emit({"ok": False, "error": refusal.error})
            return 2
        state = "onboarded" if status == 200 else "not_found" if status == 404 else "error"
        _emit({"ok": status == 200, "state": state, "status": status})
        return 0 if status == 200 else 1

    if not yes:
        _emit({"ok": False, "state": "proposal", "onboard_calls": 0,
               "question": _question(project_name, creds.project_id),
               "next": "Ask the publisher; rerun with --yes only after an explicit yes."})
        return 2
    try:
        result = preflight(creds.merchant_id, creds.project_id, transport, lambda question: True,
                           merchant_name=merchant_name, project_name=project_name)
    except qp_request.Refusal as refusal:
        _emit({"ok": False, "error": refusal.error})
        return 2
    ok = result["state"] in ("onboarded", "onboarded_now")
    _emit(dict(result, ok=ok))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
