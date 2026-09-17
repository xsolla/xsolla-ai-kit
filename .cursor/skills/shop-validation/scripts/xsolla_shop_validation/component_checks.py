"""Editor-side block content checks -- the ones that fire on a *stored* block.

These are the assertions the Site Builder editor makes about a block's contents
rather than its shape: an enabled social link with no url, a gallery slide whose
media is missing, a buy button pointing at a SKU that does not exist, a store
section with no items group.  A block can be perfectly shaped and still fail
every one of them.

They need context the block itself does not carry -- the catalog's SKUs and
bundles, the site's page ids, the landing's localization ids -- so the caller
supplies a :class:`ValidationContext`.  Where context is absent the check is
skipped and reported as unverified, never guessed at.

Path convention here is the skill's -- ``components.0.value.1`` -- not the
editor's bracketed ``components.[0].value.[1]``, so every finding in one report
reads the same way.
"""

from __future__ import annotations

from .errors import MISSING, finding, format_path, js_type
from .url_rules import validate_lightbox_url, validate_url_with_relative

TYPES_WITH_LINK = ("discordEmbed", "facebookFeed", "twitchEmbed", "twitterFeed")

ERROR_VC_GROUP = "__error__"
GK_TYPE = "gk"
BUNDLE_TYPE = "bundle"


class ValidationContext(object):
    """What the content checks need from outside the block.

    Every field is optional.  A check whose context is missing returns nothing
    and adds its name to ``unverified`` instead, because "we could not look"
    and "it is fine" are different answers.
    """

    def __init__(self, site=None, skus=None, bundles=None, localization_ids=None):
        self.site = site or {}
        self.skus = skus
        self.bundles = bundles
        self.localization_ids = localization_ids

    @property
    def page_ids(self):
        pages = self.site.get("pages") if isinstance(self.site, dict) else None
        if not isinstance(pages, list):
            return None
        return [p.get("_id") for p in pages if isinstance(p, dict)]

    @property
    def site_id(self):
        return self.site.get("_id") if isinstance(self.site, dict) else None


def _is_enabled(component):
    return bool(component.get("enable"))


def validate_action(action, path, context, unverified):
    """One custom-button action.  Built-in actions only; block-local ones pass."""
    out = []
    if not isinstance(action, dict):
        return out
    kind = action.get("action")

    if kind == "buy":
        sku = action.get("sku")
        if not sku:
            out.append(finding(format_path(path + ["sku"]), "a non-empty SKU", "empty", sku))
        elif context.skus is None:
            unverified.append("%s: SKU exists in the catalog" % format_path(path + ["sku"]))
        elif sku not in context.skus:
            out.append(finding(format_path(path + ["sku"]), "a SKU in the catalog", sku, sku))

    elif kind == "scroll":
        if not action.get("targetId"):
            out.append(
                finding(
                    format_path(path + ["targetId"]),
                    "a non-empty target id",
                    "empty",
                    action.get("targetId"),
                )
            )

    elif kind == "lightbox":
        url = action.get("url")
        if not url:
            out.append(finding(format_path(path + ["url"]), "a video url", "empty", url))
        elif not validate_lightbox_url(url):
            out.append(
                finding(
                    format_path(path + ["url"]),
                    "a YouTube, Vimeo, Steam or Epic Games video url",
                    url,
                    url,
                )
            )

    elif kind == "link":
        url = action.get("url")
        if not url:
            out.append(finding(format_path(path + ["url"]), "a url", "empty", url))
        elif not validate_url_with_relative(url):
            out.append(
                finding(
                    format_path(path + ["url"]),
                    "an absolute or relative url",
                    url,
                    url,
                )
            )

    elif kind == "page":
        landing_id = action.get("landingId")
        if not landing_id:
            out.append(
                finding(format_path(path + ["landingId"]), "a landing id", "empty", landing_id)
            )
        elif context.site_id and landing_id != context.site_id:
            # Cross-site links are not validated.
            unverified.append("%s: cross-site page link" % format_path(path))
        else:
            page_id = action.get("pageId")
            if not page_id:
                out.append(
                    finding(format_path(path + ["pageId"]), "a page id", "undefined", page_id)
                )
            elif context.page_ids is None:
                unverified.append("%s: page id exists on the site" % format_path(path + ["pageId"]))
            elif page_id not in context.page_ids:
                out.append(
                    finding(
                        format_path(path + ["pageId"]),
                        "a page id on this site",
                        page_id,
                        page_id,
                    )
                )

    elif kind == "cloud-gaming":
        if not action.get("gameId"):
            out.append(
                finding(
                    format_path(path + ["gameId"]), "a game id", "empty", action.get("gameId")
                )
            )

    elif kind == "subscription":
        if not action.get("subscriptionId"):
            out.append(
                finding(
                    format_path(path + ["subscriptionId"]),
                    "a subscription id",
                    "empty",
                    action.get("subscriptionId"),
                )
            )

    return out


def _validate_legacy_custom_button(component, path, context, unverified):
    """The pre-action custom button, still stored on older blocks."""
    out = []
    if component.get("type") != "customButton" or not _is_enabled(component):
        return out
    subtype = component.get("subtype")
    value = component.get("value")
    if not isinstance(value, dict):
        return out

    if subtype == "buy":
        buy = value.get("buy") or {}
        kind, item_id = buy.get("type"), buy.get("id")
        base = path + ["value", "buy", "id"]
        if kind == "key":
            if not item_id:
                out.append(finding(format_path(base), "a SKU", "empty", item_id))
            elif context.skus is None:
                unverified.append("%s: SKU exists in the catalog" % format_path(base))
            elif item_id not in context.skus:
                out.append(finding(format_path(base), "a SKU in the catalog", item_id, item_id))
        elif kind == "subscription":
            if not item_id:
                out.append(finding(format_path(base), "a subscription id", "empty", item_id))
        elif kind == "bundle":
            if not item_id:
                out.append(finding(format_path(base), "a bundle SKU", "empty", item_id))
            elif context.bundles is None:
                unverified.append("%s: bundle exists in the catalog" % format_path(base))
            elif item_id not in context.bundles:
                out.append(finding(format_path(base), "a bundle in the catalog", item_id, item_id))
    elif subtype == "link":
        if not (value.get("link") or {}).get("link"):
            out.append(
                finding(format_path(path + ["value", "link", "link"]), "a link", "empty", None)
            )
    elif subtype == "preset":
        if not (value.get("preset") or {}).get("link"):
            out.append(
                finding(format_path(path + ["value", "preset", "link"]), "a link", "empty", None)
            )

    return out


def _validate_component_with_link(component, path):
    """Embed-style components need the thing they embed."""
    if component.get("type") not in TYPES_WITH_LINK or not _is_enabled(component):
        return []
    values = component.get("values")
    if not isinstance(values, dict) or not values.get("link"):
        return [finding(format_path(path + ["values", "link"]), "a link", "empty", None)]
    return []


def _validate_subscribe(component, path):
    if component.get("type") != "subscribe" or not _is_enabled(component):
        return []
    if not component.get("value"):
        return [
            finding(
                format_path(path + ["value"]),
                "a subscribe value",
                "empty",
                component.get("value"),
            )
        ]
    return []


def _validate_store_section(component, path):
    """A store section with no type, or a bad group, is an empty shop."""
    if component.get("type") != "storeSection" or not _is_enabled(component):
        return []
    out = []
    items_type = component.get("storeItemsType")
    items_group = component.get("storeItemsGroup")
    if not items_type:
        out.append(
            finding(
                format_path(path + ["storeItemsType"]), "a store items type", "empty", items_type
            )
        )
        return out
    if items_group == "" and items_type not in (GK_TYPE, BUNDLE_TYPE):
        out.append(
            finding(
                format_path(path + ["storeItemsGroup"]),
                "a store items group (required for type %s)" % items_type,
                "empty",
                items_group,
            )
        )
    if items_group == ERROR_VC_GROUP:
        out.append(
            finding(
                format_path(path + ["storeItemsGroup"]),
                "a valid store items group",
                items_group,
                items_group,
            )
        )
    return out


def validate_block_components(components, path=None, context=None, unverified=None):
    """Walk a block's ``components`` array, recursing into nested components."""
    path = list(path or ["components"])
    context = context or ValidationContext()
    unverified = unverified if unverified is not None else []
    out = []

    if not isinstance(components, list):
        return out

    for index, component in enumerate(components):
        if not isinstance(component, dict) or not component.get("type"):
            continue
        here = path + [index]

        nested = component.get("components")
        if isinstance(nested, list) and nested:
            out.extend(
                validate_block_components(nested, here + ["components"], context, unverified)
            )

        out.extend(_validate_legacy_custom_button(component, here, context, unverified))
        out.extend(_validate_component_with_link(component, here))
        out.extend(_validate_subscribe(component, here))
        out.extend(_validate_store_section(component, here))

    return out


def validate_actions_anywhere(node, path=None, context=None, unverified=None):
    """Every ``{__type: "action"}`` node in a block, wherever it sits.

    Actions are not confined to ``components``: a hero block's button lives at
    ``values.button.action``, a sidebar's at ``values.items.N.action``.  Walking
    only the components array misses those entirely -- which is how a button
    pointing at a deleted page survives a "clean" walk.
    """
    path = list(path or [])
    context = context or ValidationContext()
    unverified = unverified if unverified is not None else []
    out = []

    if isinstance(node, dict):
        if node.get("__type") == "action":
            out.extend(validate_action(node, path, context, unverified))
            return out
        for key, value in node.items():
            out.extend(validate_actions_anywhere(value, path + [key], context, unverified))
    elif isinstance(node, list):
        for index, item in enumerate(node):
            out.extend(validate_actions_anywhere(item, path + [index], context, unverified))

    return out


def validate_footer_v2(block, context=None, unverified=None):
    """An enabled social item with an empty url renders a dead icon."""
    out = []
    components = block.get("components")
    if not isinstance(components, list):
        return out
    for index, component in enumerate(components):
        if not isinstance(component, dict) or component.get("type") != "social":
            continue
        if not _is_enabled(component):
            continue
        values = component.get("value")
        if not isinstance(values, list):
            continue
        for value_index, item in enumerate(values):
            if not isinstance(item, dict):
                continue
            if item.get("enable") and item.get("url") == "":
                out.append(
                    finding(
                        "components.%d.value.%d.url" % (index, value_index),
                        "a non-empty url on an enabled social item",
                        "empty",
                        "",
                    )
                )
    return out


def validate_gallery_v2(block, context=None, unverified=None):
    """Every slide has to carry the media its own type declares."""
    out = []
    values = block.get("values")
    slides = values.get("slides") if isinstance(values, dict) else None
    if not isinstance(slides, list):
        return out
    for index, slide in enumerate(slides):
        base = "values.slides.%d.image" % index
        image = slide.get("image") if isinstance(slide, dict) else None
        if not isinstance(image, dict):
            out.append(
                finding(base, "object", js_type(image if image is not None else MISSING), image)
            )
            continue
        kind = image.get("type")
        if kind == "video":
            if not image.get("video"):
                out.append(finding(base + ".video", "a video", "empty", image.get("video")))
        elif kind == "image":
            if not image.get("img"):
                out.append(finding(base + ".img", "an image", "empty", image.get("img")))
        else:
            out.append(finding(base + ".type", 'one of: "image", "video"', str(kind), kind))
    return out


def scan_localized_reference_ids(value):
    """Every ``L:`` id anywhere in a structure, in document order."""
    found = []

    def walk(node):
        if isinstance(node, str):
            if node.startswith("L:"):
                found.append(node)
        elif isinstance(node, list):
            for item in node:
                walk(item)
        elif isinstance(node, dict):
            for item in node.values():
                walk(item)

    walk(value)
    return found
