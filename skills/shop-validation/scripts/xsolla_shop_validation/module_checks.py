"""Per-module block checks — the visitors the editor's block walker registers.

Eight of these could not be ported in the first pass because their source was
not available; they are here now, ported from the current implementations.

Each one fires on a whole block of a particular module, unlike the component
checks that fire on parts of any block.  Two shapes of result, matching the
originals: most raise a message against a path, and four simply return a
boolean — for those, the original reports "Unknown validation error" at whatever
path the walk happened to be on, which is useless to a reader, so this port
names the field instead and records that as a deliberate difference.

Errors carry the editor's own ``message`` alongside ``expected``/``got`` so the
platform's wording can be matched by eye, and the pair stays machine-readable.
"""

from __future__ import annotations

from .errors import MISSING, finding, js_type
from .url_rules import validate_lead_platform_url

# --- store groups -----------------------------------------------------------

TEST_GROUP_ID = "test-group"

# The demo groups a new project ships with. A store section still pointing at
# one of these is wired to sample data, not to the partner's catalog.
TEST_GROUPS = frozenset(
    [
        "%s/bundle" % TEST_GROUP_ID,
        "%s/virtual_currency" % TEST_GROUP_ID,
        "%s/virtual_good" % TEST_GROUP_ID,
        "%s/virtual_good-free" % TEST_GROUP_ID,
        "%s/virtual_good-loyalty" % TEST_GROUP_ID,
        "%s/game_key" % TEST_GROUP_ID,
    ]
)

STORE_ITEM_TYPE_UNIT = "unit"
NEW_STORE_SECTION = "newStoreSection"
COMPONENT_TYPE_PLAN = "plan"

REMOTE_DAILY_REWARD = "sb-daily-reward"
REMOTE_OFFER_CHAIN = "sb-offer-chain"

FEDERATED_MODULE = "federated"

# Auth modes, for the subscriptions block's auth-relevance helper.
AUTH_LOGIN = "login"
AUTH_DEEPLINK = "deeplink"


def is_fake_group(group_id):
    return group_id in TEST_GROUPS


def _error(path, expected, got, message, value=MISSING):
    out = finding(path, expected, got, value)
    out["message"] = message
    return out


def _values(block):
    values = block.get("values") if isinstance(block, dict) else None
    return values if isinstance(values, dict) else {}


def _components(block):
    components = block.get("components") if isinstance(block, dict) else None
    return components if isinstance(components, list) else []


# --- subscriptions-packs ----------------------------------------------------


def validate_subscriptions_block(block):
    """Every enabled plan row has to name a plan."""
    out = []
    for index, component in enumerate(_components(block)):
        if not isinstance(component, dict) or component.get("type") != COMPONENT_TYPE_PLAN:
            continue
        value = component.get("value")
        plan_id = value.get("planId") if isinstance(value, dict) else None
        if not plan_id:
            out.append(
                _error(
                    "components.%d.value.planId" % index,
                    "a selected subscription plan",
                    "empty",
                    "Subscription plan is not selected.",
                    plan_id,
                )
            )
    return out


# --- rewards ----------------------------------------------------------------


def validate_rewards_block(block):
    """Each reward chain must name one. An empty chains list is fine."""
    chains = _values(block).get("chains")
    if not isinstance(chains, list) or not chains:
        return []
    out = []
    for index, chain in enumerate(chains):
        chain_id = chain.get("rewardChainId") if isinstance(chain, dict) else None
        if not chain_id:
            out.append(
                _error(
                    "values.chains.%d" % index,
                    "a reward chain id",
                    "empty",
                    "Invalid reward chain ID",
                    chain_id,
                )
            )
    return out


# --- leadGameSales ----------------------------------------------------------


def validate_lead_game_sales(block):
    """Enabled platforms with nothing in them renders an empty row."""
    platforms = _values(block).get("platforms")
    if not isinstance(platforms, dict) or not platforms.get("enable"):
        return []
    items = platforms.get("items")
    if isinstance(items, list) and items:
        return []
    return [
        _error(
            "values.platforms",
            "at least one platform while enabled",
            "empty",
            "Lead Game Sales block platforms can not be empty when enabled",
        )
    ]


# --- newStore ---------------------------------------------------------------


def validate_new_store_block(block):
    """A store section has to point at a real catalog group.

    Unit items carry no group and are skipped. Everything else must have one,
    it must be set, and it must not be one of the demo groups a fresh project
    ships with — a section still pointing at those is wired to sample data.
    """
    out = []
    for index, component in enumerate(_components(block)):
        if not isinstance(component, dict) or component.get("type") != NEW_STORE_SECTION:
            continue
        section = component.get("section")
        item = section.get("item") if isinstance(section, dict) else None
        if not isinstance(item, dict):
            continue
        if item.get("type") == STORE_ITEM_TYPE_UNIT:
            continue
        path = "components.%d.section.item" % index
        if "group" not in item:
            out.append(
                _error(path, "an object carrying a group", "no group key", "Invalid store item structure")
            )
            continue
        group = item.get("group")
        if not group:
            out.append(_error("%s.group" % path, "a catalog group", "empty", "Store group is missing", group))
        elif is_fake_group(group):
            out.append(
                _error(
                    "%s.group" % path,
                    "a real catalog group, not a demo one",
                    group,
                    "Store group is invalid",
                    group,
                )
            )
    return out


# --- federated: daily reward and offer chain --------------------------------


def _is_federated(block):
    return isinstance(block, dict) and block.get("module") == FEDERATED_MODULE


def is_daily_reward(block):
    return _is_federated(block) and _values(block).get("blockId") == REMOTE_DAILY_REWARD


def is_offer_chain(block):
    return _is_federated(block) and _values(block).get("blockId") == REMOTE_OFFER_CHAIN


def _federated_numeric_id(block, field, label):
    """Both remote blocks are configured by one numeric id and nothing else.

    The original returns a bare ``false`` here, which the walker turns into
    "Unknown validation error" at whatever path it had reached. This names the
    field instead — same pass/fail, a usable message.
    """
    if not _is_federated(block):
        return [
            _error(
                "module",
                FEDERATED_MODULE,
                (block or {}).get("module") if isinstance(block, dict) else js_type(block),
                "%s check applies only to a federated block." % label,
            )
        ]
    internal = _values(block).get("internalBlockValues")
    value = internal.get(field, MISSING) if isinstance(internal, dict) else MISSING
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return [
            _error(
                "values.internalBlockValues.%s" % field,
                "number",
                js_type(value),
                "%s is not selected." % label,
                None if value is MISSING else value,
            )
        ]
    return []


def validate_daily_reward(block):
    return _federated_numeric_id(block, "dailyRewardId", "Daily reward")


def validate_offer_chain(block):
    return _federated_numeric_id(block, "offerChainId", "Offer chain")


# --- lead (v2) --------------------------------------------------------------


def check_lead_v2(block):
    """Enabled store platforms must all point at their own storefront.

    Note the asymmetry with ``leadGameSales`` above: this one also fails when
    every row is disabled, because a lead block with platforms enabled and no
    enabled row inside has nothing to show.
    """
    platforms = _values(block).get("platforms")
    if not isinstance(platforms, dict) or not platforms.get("enable"):
        return []

    items = platforms.get("items")
    items = items if isinstance(items, list) else []
    enabled = [i for i in items if isinstance(i, dict) and i.get("enable") is not False]

    if not enabled:
        return [
            _error(
                "values.platforms.items",
                "at least one enabled platform while enabled",
                "none enabled",
                "Lead platforms are enabled but no platform is usable",
            )
        ]

    out = []
    for index, item in enumerate(items):
        if not isinstance(item, dict) or item.get("enable") is False:
            continue
        if not validate_lead_platform_url(item):
            out.append(
                _error(
                    "values.platforms.items.%d.url" % index,
                    "an https url on %s's own host" % (item.get("platform") or "that platform"),
                    item.get("url") or "empty",
                    "Lead platform URL is not valid for its platform",
                    item.get("url"),
                )
            )
    return out


# --- sidebar ----------------------------------------------------------------


def check_sidebar(block):
    """Store buttons must point at their own storefront; socials need a link."""
    values = _values(block)
    out = []

    platforms = values.get("platforms")
    if isinstance(platforms, dict) and platforms.get("enable"):
        buttons = values.get("storeButtons")
        buttons = buttons if isinstance(buttons, dict) else {}
        for key, button in sorted(buttons.items()):
            if not isinstance(button, dict) or not button.get("enable"):
                continue
            if not validate_lead_platform_url(
                {"platform": button.get("platform"), "url": button.get("link")}
            ):
                out.append(
                    _error(
                        "values.storeButtons.%s.link" % key,
                        "an https url on %s's own host" % (button.get("platform") or "that platform"),
                        button.get("link") or "empty",
                        "Sidebar store button link is not valid for its platform",
                        button.get("link"),
                    )
                )

    socials = values.get("socials")
    if isinstance(socials, dict) and socials.get("enable"):
        networks = socials.get("socialNetworks")
        networks = networks if isinstance(networks, dict) else {}
        for key, network in sorted(networks.items()):
            if not isinstance(network, dict) or not network.get("enable"):
                continue
            if network.get("link") == "":
                out.append(
                    _error(
                        "values.socials.socialNetworks.%s.link" % key,
                        "a non-empty link on an enabled social network",
                        "empty",
                        "Sidebar social network link is empty",
                        "",
                    )
                )
    return out


# --- subscriptions: auth relevance ------------------------------------------


def is_auth_relevant_for_subscriptions(login_id, auth_type):
    """Whether a subscriptions block still needs auth wiring.

    Not a block check and not registered on the walker, but it lives with them
    and decides whether an unconfigured auth setup matters for this block: a
    configured Login project, or a deeplink flow, means auth is already handled.
    """
    has_login = bool(login_id) and auth_type == AUTH_LOGIN
    return not (has_login or auth_type == AUTH_DEEPLINK)
