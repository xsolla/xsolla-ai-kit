#!/usr/bin/env python3
"""Where quest-setup talks to: one fixed list of public Xsolla hosts per environment.

The publisher's API key only ever goes to a host on this list. The environment is chosen by
QUEST_SETUP_ENV (process environment first, else ./.env), never by a prompt, a docs page or a
failed call. Unset means production, the only environment listed: this repository is public, so
only public hosts belong here. Routes are not here: they come from the live docs
(qp_docs.py caches the OpenAPI document, qp_request.py resolves operations from it).
Python 3.9+, standard library only.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Mapping, Optional

ENV_NAME = "QUEST_SETUP_ENV"
DEFAULT_ENV = "production"

ENVIRONMENTS: Dict[str, Dict[str, str]] = {
    "production": {
        "quests": "https://quests-platform.xsolla.com",
        "store": "https://store.xsolla.com",
        "docs": "https://developers.xsolla.com",
    },
}


class UnknownEnvironment(Exception):
    """QUEST_SETUP_ENV names an environment that is not on the list."""


def _dotenv_value(cwd: Path, key: str) -> Optional[str]:
    """Read one KEY=VALUE line from ./.env as text. Never executed or sourced."""
    try:
        text = (cwd / ".env").read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("export "):
            line = line[len("export "):].strip()
        name, sep, value = line.partition("=")
        if sep and name.strip() == key:
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]
            return value.strip()
    return None


def environment(environ: Mapping[str, str], cwd: Path) -> str:
    """The configured environment name. Raises UnknownEnvironment for a name not on the list."""
    name = (environ.get(ENV_NAME) or "").strip() or (_dotenv_value(cwd, ENV_NAME) or "")
    name = name.strip().lower() or DEFAULT_ENV
    if name not in ENVIRONMENTS:
        raise UnknownEnvironment(name)
    return name


def hosts(environ: Mapping[str, str], cwd: Path) -> Dict[str, str]:
    return dict(ENVIRONMENTS[environment(environ, cwd)])
