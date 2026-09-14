"""Source detection and extractor dispatch.

The three extractors take different raw inputs -- two JSON API responses and one
page of HTML -- so this decides which to call and from what, given a store URL.

The source is inferred from the URL's host rather than asked for, because the
host is unambiguous and a mismatched ``--source`` flag is a class of bug worth
designing out.  ``mapping.source_matches_url`` still cross-checks it later, for
the case where a caller sets the field by hand.

What this misses: it does not fetch.  Each function takes content the caller
already has, so a rate limit, a redirect or a geo-block surfaces where it
happened instead of inside a parser.  ``fetch_hint`` names the URL to fetch for
a given store page, so the caller does not have to know each API's shape.
"""

from __future__ import annotations

import json
import re

from . import extract_appstore, extract_play, extract_steam
from . import fields as field_model

_STEAM_APPID = re.compile(r"/app/(\d+)")
_APPLE_ID = re.compile(r"/id(\d+)")
_PLAY_PKG = re.compile(r"[?&]id=([A-Za-z0-9_.]+)")


def detect_source(url):
    """The storefront a URL points at, or ``None`` if it is not one of the three."""
    host = (url or "").split("//")[-1].split("/")[0].lower()
    if "steampowered.com" in host:
        return field_model.STEAM
    if "play.google.com" in host:
        return field_model.GOOGLE_PLAY
    if "apps.apple.com" in host or "itunes.apple.com" in host:
        return field_model.APP_STORE
    return None


def fetch_hint(url):
    """What to fetch for a given store URL, as ``(source, fetch_url, kind)``.

    ``kind`` is ``json`` or ``html`` -- it says how to hand the result back to
    ``to_listing``.  The App Store needs both: the API for everything except the
    in-app purchases, and the page for those.
    """
    source = detect_source(url)
    if source == field_model.STEAM:
        found = _STEAM_APPID.search(url)
        if not found:
            raise ValueError("no Steam app id in %s" % url)
        return (source, "https://store.steampowered.com/api/appdetails"
                        "?appids=%s&l=english" % found.group(1), "json")
    if source == field_model.APP_STORE:
        found = _APPLE_ID.search(url)
        if not found:
            raise ValueError("no App Store id in %s" % url)
        country = "us"
        parts = [p for p in url.split("/") if p]
        for index, part in enumerate(parts):
            if part == "apps.apple.com" and index + 1 < len(parts):
                if len(parts[index + 1]) == 2:
                    country = parts[index + 1]
        return (source, "https://itunes.apple.com/lookup?id=%s&country=%s"
                        % (found.group(1), country), "json")
    if source == field_model.GOOGLE_PLAY:
        found = _PLAY_PKG.search(url)
        if not found:
            raise ValueError("no package name in %s" % url)
        return (source, url, "html")
    raise ValueError("not a supported storefront: %s" % url)


def to_listing(raw, url, iap_items=None):
    """Extract from already-fetched content, routing on the URL's host.

    ``raw`` is a ``dict`` (a parsed JSON response), or a ``str`` -- JSON text for
    Steam and the App Store, page HTML for Play.
    """
    source = detect_source(url)
    if source is None:
        raise ValueError("not a supported storefront: %s" % url)

    if source == field_model.GOOGLE_PLAY:
        if not isinstance(raw, str):
            raise ValueError("Google Play extraction needs the page HTML")
        return extract_play.to_listing(raw, url)

    document = json.loads(raw) if isinstance(raw, str) else raw
    if source == field_model.STEAM:
        return extract_steam.to_listing(document, url)
    return extract_appstore.to_listing(document, url, iap_items=iap_items)
