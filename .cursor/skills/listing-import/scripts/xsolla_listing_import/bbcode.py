"""Steam BBCode to the HTML subset Shop Builder's rich-text fields accept.

Steam serves its long description as BBCode, and Shop Builder stores localized
copy as HTML.  Nothing in the CLI converts between them, so a naive import
writes literal ``[h2]`` into a partner's page.

The conversion escapes first and emits tags second, and that order is the point
rather than a detail.  A store description is third-party text arriving from a
page nobody in this repo controls; pasting it into a localization write would
put whatever it contains into a partner's rendered site.  So every ``<`` in the
input becomes ``&lt;`` before any tag is emitted, and the only real tags in the
output are ones this module produced from a BBCode tag it recognised.

What this module misses:

* ``[table]``/``[tr]``/``[td]`` are dropped rather than converted.  Shop Builder
  rich text has no table styling, and a borderless table reads worse than the
  note this leaves behind.
* Steam's ``[dynamiclink]`` and store-widget tags are dropped.
* Nesting is handled only as deep as Steam actually ships: a list inside a list
  converts, a heading inside a list does not.
* ``[img]`` is dropped entirely.  Those URLs are ``{STEAM_APP_IMAGE}``-relative
  and resolve only on Steam's CDN, so carrying them over would embed hotlinks
  to another storefront in a partner's page.  Screenshots come through the
  ``screenshots`` field and the asset round trip instead.
"""

from __future__ import annotations

import html
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_HEADING = re.compile(r"\[h([1-6])\](.*?)\[/h\1\]", re.DOTALL)
_SIMPLE = (
    (re.compile(r"\[b\](.*?)\[/b\]", re.DOTALL), r"<strong>\1</strong>"),
    (re.compile(r"\[i\](.*?)\[/i\]", re.DOTALL), r"<em>\1</em>"),
    (re.compile(r"\[u\](.*?)\[/u\]", re.DOTALL), r"<u>\1</u>"),
    (re.compile(r"\[strike\](.*?)\[/strike\]", re.DOTALL), r"<s>\1</s>"),
    (re.compile(r"\[quote\](.*?)\[/quote\]", re.DOTALL), r"<blockquote>\1</blockquote>"),
    (re.compile(r"\[code\](.*?)\[/code\]", re.DOTALL), r"<pre>\1</pre>"),
)
_URL_LABELLED = re.compile(r"\[url=([^\]]+)\](.*?)\[/url\]", re.DOTALL)
_URL_BARE = re.compile(r"\[url\](.*?)\[/url\]", re.DOTALL)
_IMG = re.compile(r"\[img\].*?\[/img\]", re.DOTALL)
_YOUTUBE = re.compile(r"\[previewyoutube=([A-Za-z0-9_-]+)[^\]]*\]" r"(?:.*?\[/previewyoutube\])?",
                      re.DOTALL)
_HR = re.compile(r"\[hr\](?:\[/hr\])?")
_LIST = re.compile(r"\[(list|olist)\](.*?)\[/\1\]", re.DOTALL)
_TABLE = re.compile(r"\[table.*?\].*?\[/table\]", re.DOTALL)
_DYNAMIC = re.compile(r"\[dynamiclink[^\]]*\](?:.*?\[/dynamiclink\])?", re.DOTALL)
_LEFTOVER = re.compile(r"\[/?[a-zA-Z][^\]]{0,80}\]")

# Tracking and referral parameters a store page hangs on its own outbound links.
# Carried into a partner's site they would attribute that traffic to the source
# storefront, so they come off.
_TRACKING_KEYS = frozenset(
    ["ref", "referrer", "fbclid", "gclid", "mc_cid", "mc_eid", "snr", "curator_clanid"]
)


def strip_tracking(url):
    """Remove ``utm_*``/``ref``-style parameters, keeping the rest of the query.

    Parsed rather than pattern-matched, because removing the *first* parameter
    with a regex leaves the query string headless -- ``?a=1&b=2`` becomes
    ``&b=2``, which resolves to a different page or to none.
    """
    if not url:
        return url
    parts = urlsplit(url)
    if not parts.query:
        return url
    kept = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not (key.lower().startswith("utm_") or key.lower() in _TRACKING_KEYS)
    ]
    return urlunsplit(parts._replace(query=urlencode(kept)))


def _convert_list(match):
    tag = "ul" if match.group(1) == "list" else "ol"
    body = match.group(2)
    items = [chunk.strip() for chunk in body.split("[*]")]
    rendered = "".join("<li>%s</li>" % i for i in items if i)
    return "<%s>%s</%s>" % (tag, rendered, tag)


_BLOCK_ELEMENT = re.compile(
    r"<(h[1-6]|ul|ol|blockquote|pre)\b.*?</\1>|<hr>", re.DOTALL
)


def _wrap_runs(text):
    """Wrap blank-line-separated runs of inline text in ``<p>``."""
    out = []
    for chunk in re.sub(r"\n{3,}", "\n\n", text).split("\n\n"):
        chunk = chunk.strip()
        if chunk:
            out.append("<p>%s</p>" % chunk.replace("\n", "<br>"))
    return "".join(out)


def _paragraphs(text):
    """Wrap inline text in ``<p>``, passing block-level elements through as-is.

    Block elements are located and the gaps between them wrapped, rather than
    testing whether a chunk *starts* with a block tag: a heading followed by a
    single newline and a sentence is one chunk, and the earlier version left
    that sentence bare.
    """
    out = []
    cursor = 0
    for match in _BLOCK_ELEMENT.finditer(text):
        out.append(_wrap_runs(text[cursor:match.start()]))
        out.append(match.group(0))
        cursor = match.end()
    out.append(_wrap_runs(text[cursor:]))
    return "".join(out)


def to_html(source):
    """Convert BBCode to HTML.

    Returns ``(html, dropped)``.  ``dropped`` names each construct removed
    rather than converted, so the skill can report what the partner lost instead
    of letting it vanish quietly.
    """
    dropped = []
    if not source:
        return "", dropped

    text = html.escape(source, quote=False)

    videos = _YOUTUBE.findall(text)
    for video_id in videos:
        dropped.append("youtube:%s" % video_id)
    text = _YOUTUBE.sub("", text)

    if _IMG.search(text):
        dropped.append("img (Steam CDN-relative, not portable)")
    text = _IMG.sub("", text)

    if _TABLE.search(text):
        dropped.append("table (no rich-text table styling in Shop Builder)")
    text = _TABLE.sub("", text)

    if _DYNAMIC.search(text):
        dropped.append("dynamiclink (Steam store widget)")
    text = _DYNAMIC.sub("", text)

    text = _LIST.sub(_convert_list, text)
    text = _HEADING.sub(lambda m: "<h%s>%s</h%s>" % (m.group(1), m.group(2).strip(), m.group(1)),
                        text)
    for pattern, repl in _SIMPLE:
        text = pattern.sub(repl, text)

    def _link(match):
        # The href arrives already escaped by the pass above.  Unescape it so the
        # query string parses, strip tracking, then re-escape for an attribute.
        href = strip_tracking(html.unescape(match.group(1).strip()))
        return '<a href="%s">%s</a>' % (html.escape(href, quote=True),
                                        match.group(2).strip())

    text = _URL_LABELLED.sub(_link, text)
    text = _URL_BARE.sub(
        lambda m: '<a href="%s">%s</a>' % (
            html.escape(strip_tracking(html.unescape(m.group(1).strip())), quote=True),
            m.group(1).strip(),
        ),
        text,
    )
    text = _HR.sub("<hr>", text)

    leftovers = _LEFTOVER.findall(text)
    if leftovers:
        for tag in sorted(set(leftovers)):
            dropped.append("unrecognised %s" % tag)
        text = _LEFTOVER.sub("", text)

    return _paragraphs(text), dropped


def youtube_ids(source):
    """The YouTube ids a description embeds, in page order."""
    if not source:
        return []
    return list(_YOUTUBE.findall(html.escape(source, quote=False)))
