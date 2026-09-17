"""App Store listing extraction, from Apple's public lookup response.

Input is the JSON body of ``https://itunes.apple.com/lookup?id=<id>&country=<cc>``
-- already fetched.

The thing to know before relying on this: **Apple's lookup API does not expose
in-app purchases at all.**  Verified on 2026-09-14 against id 529479190 --- no
key in the response contains "purchase", "iap" or "inApp".  Every other target
field is there.  The IAP list is rendered on the *web page* only, and truncated
to roughly ten entries with a "Learn More" link, so it is passed in separately
by the caller that scraped it rather than invented here.

The country code in the URL decides prices and the age rating, so the caller
should record which storefront it read.  Prices from one storefront are one
region's, not a price list.

What this misses:

* ``key_art`` -- the App Store publishes no wide key art.  Excluded from the
  coverage denominator in ``fields.py`` rather than reported as a miss.
* ``short_description`` -- the page's subtitle is not in the lookup response.
  Many apps have none anyway.
* ``tags`` -- Apple has no user tags.
* Screenshot URLs come back as display thumbnails (``406x228bb``).  The
  ``_full_size`` helper rewrites them, but Apple's sizing suffixes are
  undocumented and may stop resolving; the raw value is kept if it does.
"""

from __future__ import annotations

import re

from . import fields as field_model

_THUMB_SUFFIX = re.compile(r"/\d+x\d+bb\.(jpg|png|webp)$", re.I)


def unwrap(document):
    """Accept the full ``{resultCount, results:[...]}`` body or a single result."""
    if not isinstance(document, dict):
        return None
    if "trackName" in document:
        return document
    results = document.get("results") or []
    return results[0] if results else None


def _full_size(url):
    """Rewrite a display thumbnail to the source image, if the pattern holds."""
    if not url:
        return url
    return _THUMB_SUFFIX.sub(r"/2048x2048bb.\1", url)


def _platforms(data):
    devices = " ".join(data.get("supportedDevices") or [])
    found = ["ios"]
    if "iPad" in devices:
        found.append("ipados")
    if "Mac" in devices or "AppleTV" in devices:
        found.append("macos" if "Mac" in devices else "tvos")
    return found


def _reviews(data):
    """The App Store's rating and how many it is from.

    Rounded to one decimal: the API returns ``4.11334``, and a page claiming
    four-figure precision on a star rating reads as a bug.
    """
    score = data.get("averageUserRating")
    count = data.get("userRatingCount")
    if not score or not count:
        return None
    return "%.1f out of 5, from {:,} ratings on the App Store".format(int(count)) \
        % float(score)


def to_listing(document, source_url, iap_items=None):
    """Build a listing document.

    ``iap_items`` is the list scraped from the web page, since the API has none.
    Pass ``None`` when it was not read -- that is recorded as not-found, which
    is different from the app having no in-app purchases.
    """
    data = unwrap(document)
    if data is None:
        raise ValueError("not an iTunes lookup response (no results)")

    values = {
        "title": data.get("trackName"),
        "developer": data.get("sellerName"),
        "long_description_text": data.get("description"),
        "icon": data.get("artworkUrl512") or data.get("artworkUrl100"),
        "screenshots": [_full_size(u) for u in data.get("screenshotUrls") or []],
        "genres": [g for g in data.get("genres") or [] if g],
        "platforms": _platforms(data),
        "age_rating": data.get("contentAdvisoryRating")
                      or data.get("trackContentRating"),
        "reviews": _reviews(data),
    }
    if iap_items:
        values["iap_items"] = iap_items

    not_found = ["short_description", "tags"]
    if iap_items is None:
        not_found.append("iap_items")
    for name, value in list(values.items()):
        if not value:
            values.pop(name)
            if name not in not_found:
                not_found.append(name)

    notes = ("Apple's lookup API publishes no in-app purchase list; the web page "
             "shows a truncated one. The storefront country in source_url decides "
             "prices and the age rating.")
    if iap_items:
        notes += (" iap_items were scraped from the page and are the top entries "
                  "only, not a complete list.")

    return {
        "source": field_model.APP_STORE,
        "source_url": source_url,
        "rights_confirmed": False,
        "fields": values,
        "not_found": not_found,
        "notes": notes,
    }
