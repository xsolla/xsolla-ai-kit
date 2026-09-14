"""Fixture loading.

The two Steam fixtures are real, not hand-written: ``steam_listing.json`` was
built from the live ``appdetails`` response for app 812140 and
``steam_structure.json`` is the block spine of a landing that
``xsolla shopbuilder import-listing`` actually produced (merchant 936601,
2026-09-14), trimmed to ids and module names.  A synthetic fixture would have
agreed with whatever the mapping happened to assume; these two disagreed with
it twice, and both disagreements were real.
"""

from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def load(name):
    with open(os.path.join(HERE, name), "r", encoding="utf-8") as handle:
        return json.load(handle)


def steam_listing():
    return load("steam_listing.json")


def steam_structure():
    return load("steam_structure.json")
