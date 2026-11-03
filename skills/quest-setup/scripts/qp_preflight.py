#!/usr/bin/env python3
"""Stub for the onboarding preflight. Contract only, no logic yet (step 06 stub)."""
from __future__ import annotations


def preflight(merchant_id, project_id, transport, confirm, merchant_name="", project_name=""):
    return {"state": "error", "onboard_calls": 0, "readback_status": None}
