"""Google Play listing extraction, from the store page's HTML.

Input is the raw HTML of ``https://play.google.com/store/apps/details?id=<pkg>``
-- already fetched, with a browser User-Agent.

Play's page is React-rendered, so a naive fetch-and-read finds nothing useful in
the visible text and the obvious conclusion is that it needs a headless
browser.  It does not: verified on 2026-09-14 for ``com.supercell.clashofclans``,
a plain request returns 1.3 MB of HTML with every target field already in it --
the ``og:`` meta tags, a ``data-g-id="description"`` container holding the full
long description, and the image CDN URLs.

This is the one extractor that reads markup rather than a JSON contract, so it
is the one that will break.  It fails **field by field** on purpose: a changed
class name costs one field, declared in ``not_found``, instead of raising and
losing the other ten.

What it misses:

* ``key_art`` -- no image on the page has the feature graphic's 1024x500 shape.
  Play appears to have stopped rendering it.  Reported not-found rather than
  substituting a screenshot.
* ``tags`` -- Play has no user tags.
* ``requirements`` -- Play publishes a minimum Android version on some
  listings and nothing structured; not extracted, so the block is pruned.
* ``iap_items`` -- Play publishes a **price range** (``$0.29 - $239.99``), never
  named items.  The range is carried in ``notes``, because a range is not an
  item and inventing items from it would be a fabrication.
* The genre comes from the category slug (``FAMILY``), which is the store's
  taxonomy and can differ from the genre shown on the page.
"""

from __future__ import annotations

import re
from html import unescape
from html.parser import HTMLParser

from . import fields as field_model
from .sanitize import VOID

_TITLE_SUFFIX = re.compile(r"\s*-\s*Apps on Google Play\s*$", re.I)
_META = r'<meta[^>]+(?:property|name)="%s"[^>]*content="([^"]*)"'
_META_REV = r'<meta[^>]+content="([^"]*)"[^>]+(?:property|name)="%s"'
# Screenshot renditions.  Play emits each at two widths; the larger is taken.
_SCREENSHOT = re.compile(r'(https://play-lh\.googleusercontent\.com/[\w-]{15,}'
                         r'=w1052-h592-rw)')
_DEV_LINK = re.compile(r'href="/store/apps/dev(?:eloper)?\?id=[^"]+"[^>]*>(.{0,200}?)</a>',
                       re.DOTALL)
_CATEGORY = re.compile(r'/store/apps/category/([A-Z_]+)')
_RATING = re.compile(r'>(Everyone 10\+|Everyone|Teen|Mature 17\+|Adults only 18\+|'
                     r'Rated for \d+\+)<')
_PRICE_RANGE = re.compile(r'(\$\d[\d,]*\.\d{2})\s*[-–]\s*(\$\d[\d,]*\.\d{2})')
# Play renders the score in an aria-label and the count as an abbreviated
# string ("348K reviews"). The JSON-LD ratingValue carries full precision
# and is preferred; the aria-label is the fallback.
_RATING_SCHEMA = re.compile(r'"ratingValue"\s*:\s*"?([\d.]+)')
_RATING_ARIA = re.compile(r'aria-label="Rated ([\d.]+) stars')
_REVIEW_COUNT = re.compile(r">([\d.]+[KMB]?)\s*reviews<")
_TAGS = re.compile(r"<[^>]+>")


class _Subtree(HTMLParser):
    """Capture the inner HTML of the first element carrying an attribute pair."""

    def __init__(self, attr, value):
        HTMLParser.__init__(self, convert_charrefs=False)
        self._attr = attr
        self._value = value
        self._depth = 0
        self.chunks = []
        self.done = False

    def handle_starttag(self, tag, attrs):
        if self.done:
            return
        if self._depth:
            # A void element never sends a close tag.  Counting it as a level
            # meant the depth never unwound and the capture ran to the end of
            # the document -- 271 KB instead of the description.  Same bug the
            # sanitiser had; same fix.
            if tag not in VOID:
                self._depth += 1
            self.chunks.append(self.get_starttag_text() or "<%s>" % tag)
            return
        for name, val in attrs:
            if name == self._attr and val == self._value:
                self._depth = 1
                return

    def handle_endtag(self, tag):
        if self.done or not self._depth:
            return
        if tag in VOID:
            return
        self._depth -= 1
        if self._depth == 0:
            self.done = True
            return
        self.chunks.append("</%s>" % tag)

    def handle_startendtag(self, tag, attrs):
        """An explicitly self-closing tag: content, never a new level."""
        if self._depth and not self.done:
            self.chunks.append(self.get_starttag_text() or "<%s>" % tag)

    def handle_data(self, data):
        if self._depth and not self.done:
            self.chunks.append(data)

    def handle_entityref(self, name):
        if self._depth and not self.done:
            self.chunks.append("&%s;" % name)

    def handle_charref(self, name):
        if self._depth and not self.done:
            self.chunks.append("&#%s;" % name)

    def result(self):
        return "".join(self.chunks).strip()


def _meta(html, prop):
    """A meta tag's content, matching either attribute order."""
    for pattern in (_META % re.escape(prop), _META_REV % re.escape(prop)):
        found = re.search(pattern, html)
        if found:
            return unescape(found.group(1)).strip() or None
    return None


def _developer(html):
    found = _DEV_LINK.search(html)
    if not found:
        return None
    text = unescape(_TAGS.sub("", found.group(1))).strip()
    return text or None


def _long_description(html):
    parser = _Subtree("data-g-id", "description")
    parser.feed(html)
    parser.close()
    body = parser.result()
    return body or None


def _reviews(html):
    """Play's star rating and review count.

    The count stays abbreviated -- Play publishes "348K", not the exact number,
    so expanding it to 348,000 would invent precision the page does not have.
    """
    score = _RATING_SCHEMA.search(html) or _RATING_ARIA.search(html)
    count = _REVIEW_COUNT.search(html)
    if not score:
        return None
    rounded = "%.1f" % float(score.group(1))
    if not count:
        return "%s out of 5 on Google Play" % rounded
    return "%s out of 5, from %s reviews on Google Play" % (rounded,
                                                            count.group(1))


def to_listing(html, source_url):
    """Build a listing document from the page's HTML."""
    if not html or "play.google.com" not in html[:400000]:
        raise ValueError("not a Google Play store page")

    title = _meta(html, "og:title")
    if title:
        title = _TITLE_SUFFIX.sub("", title).strip()

    category = _CATEGORY.search(html)
    rating = _RATING.search(html)

    values = {
        "title": title,
        "developer": _developer(html),
        "short_description": _meta(html, "og:description"),
        "long_description_html": _long_description(html),
        "icon": _meta(html, "og:image"),
        "screenshots": sorted(set(_SCREENSHOT.findall(html))),
        "genres": [category.group(1).replace("_", " ").title()] if category else [],
        "platforms": ["android"],
        "age_rating": rating.group(1) if rating else None,
        "reviews": _reviews(html),
    }

    not_found = ["key_art", "tags", "iap_items"]
    for name, value in list(values.items()):
        if not value:
            values.pop(name)
            if name not in not_found:
                not_found.append(name)

    notes = ("Extracted from the store page's HTML. Play publishes no named "
             "in-app items and no feature graphic on the page.")
    price_range = _PRICE_RANGE.search(html)
    if price_range:
        notes += (" The page shows an in-app purchase price range of %s to %s; a "
                  "range is not an item list, so no items were created."
                  % (price_range.group(1), price_range.group(2)))

    return {
        "source": field_model.GOOGLE_PLAY,
        "source_url": source_url,
        "rights_confirmed": False,
        "fields": values,
        "not_found": not_found,
        "notes": notes,
    }
