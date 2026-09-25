"""Executable checks for Xsolla Shop Builder block payloads, sites and custom-block source.

This package is the rules themselves, as code -- there is no separate prose copy to drift
from, and each module's docstring carries why its checks exist and what they miss.
``../INVENTORY.md`` maps each one to the Site Builder MCP behaviour it ports.

Import the modules directly; nothing is re-exported here, so a reader of a call site can see
which family of check it belongs to:

    from xsolla_shop_validation.native import validate_native
    from xsolla_shop_validation.federated import validate_federated
    from xsolla_shop_validation.ai_block import collect_violations
    from xsolla_shop_validation.site_walk import walk_site

Python 3.9+, standard library only.
"""

__all__ = []
