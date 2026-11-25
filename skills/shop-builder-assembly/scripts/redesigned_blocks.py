#!/usr/bin/env python3
"""Names of Shop Builder's redesigned blocks.

A redesigned block is a federated block whose ``values.blockId`` starts with
``_site-builder-classic_``. Each one stands for a native module but keeps its data in
another shape. This table says which block it is; it never makes a native patch fit.
"""

from __future__ import annotations

PREFIX = "_site-builder-classic_"
# The name after the prefix, and the native module that block stands for.
NATIVE_MODULES = {
    "header": "header",
    "lead": "lead",
    "lead-gs": "leadGameSales",
    "store": "newStore",
    "promocode": "promocodes",
    "faq": "faq",
    "footer-v3": "footer",
    "game-packs": "packs",
    "description": "description",
    "card-grid": "bento-grid",
    "gallery": "gallery",
    "system-requirements": "requirements",
    "news": "news",
    "reward-chains": "rewards",
    "sidebar": "sidebar",
    "sb-offer-chain": "sb-offer-chain",
    "sb-daily-reward": "sb-daily-reward",
    "offerwall": "offerwall-block",
}


def logical_name(module: object) -> object:
    """Return the native module a redesigned block stands for, and any other name as is.

    A name with the prefix that isn't in the table stays as it is: nothing is known
    about that block.
    """
    if isinstance(module, str) and module.startswith(PREFIX):
        return NATIVE_MODULES.get(module[len(PREFIX) :], module)
    return module
