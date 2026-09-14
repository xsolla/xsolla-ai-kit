"""Reduce a store page's long description to the HTML Shop Builder can hold.

This module exists because of a wrong assumption, and the correction is worth
recording rather than quietly fixing: the plan for Steam was BBCode conversion,
on the strength of BBCode being what a developer types into Steam's backend.
Checked against the live listing for app 812140 on 2026-09-14, Steam does not
serve that.  ``about_the_game`` comes back as HTML that Steam has already
rendered -- ``<h2 class="bb_tag">``, ``<span class="bb_img_ctn">``, and
``<video><source src=...>`` for inline trailers.  So the Steam path needs
sanitising, not converting.  ``bbcode.py`` still earns its place: the schema
accepts a BBCode long description, because a partner pasting their own store
copy is pasting BBCode.

Parsed with ``HTMLParser`` rather than regex.  Regex-stripping tags from
attacker-influenced markup is the classic way to leave one through, and this
text comes from a page nobody here controls and goes into a partner's rendered
site.  The allowlist is positive: a tag is dropped unless it is named.

Three dispositions, and the difference matters:

*kept*      the tag survives, with only allowlisted attributes.
*unwrapped* the tag goes, its text stays -- ``<span>``, ``<div>``.
*cut*       the tag and everything inside it go -- ``<video>``, ``<script>``.

What this module misses: it does not rewrite relative URLs, so a relative
``href`` stays relative and will resolve against the partner's domain.  It does
not balance stray close tags beyond ignoring them.  And it keeps ``<a>``
targets to http/https/mailto only, which silently drops a store-internal
``steam://`` link rather than reporting each one.
"""

from __future__ import annotations

from html import escape
from html.parser import HTMLParser

KEPT = {
    "h1", "h2", "h3", "h4", "h5", "h6", "p", "br", "ul", "ol", "li",
    "strong", "em", "b", "i", "u", "s", "a", "blockquote", "hr",
}
UNWRAPPED = {"span", "div", "font", "center", "section", "article", "tbody"}
CUT = {"video", "source", "script", "style", "iframe", "object", "embed",
       "audio", "track", "noscript", "svg", "canvas", "form", "input", "img",
       "table", "tr", "td", "th", "thead"}
# Every HTML void element, not just the two in the keep list.  A void element
# in CUT must not open a cut region: ``<source>`` and ``<img>`` never send a
# close tag, so treating them as containers left the parser cutting to the end
# of the document.  Found against the real app-812140 description, which came
# out 284 characters long instead of 2,635.
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "param", "source", "track", "wbr"}
SAFE_SCHEMES = ("http://", "https://", "mailto:")


class _Sanitizer(HTMLParser):
    """Rewrite a fragment against the allowlist, recording what it removed."""

    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.out = []
        self.dropped = set()
        self._cut_depth = 0
        self._open = []

    def handle_starttag(self, tag, attrs):
        if self._cut_depth:
            if tag in CUT and tag not in VOID:
                self._cut_depth += 1
            return
        if tag in CUT:
            self.dropped.add(tag)
            if tag not in VOID:
                self._cut_depth = 1
            return
        if tag in UNWRAPPED:
            self.dropped.add(tag)
            return
        if tag not in KEPT:
            self.dropped.add(tag)
            return
        if tag == "a":
            href = ""
            for name, value in attrs:
                if name.lower() == "href" and value:
                    href = value.strip()
            if not href.lower().startswith(SAFE_SCHEMES):
                self.dropped.add("a (unsupported scheme)")
                return
            self.out.append('<a href="%s">' % escape(href, quote=True))
            self._open.append("a")
            return
        if tag in VOID:
            self.out.append("<%s>" % tag)
            return
        self.out.append("<%s>" % tag)
        self._open.append(tag)

    def handle_endtag(self, tag):
        if self._cut_depth:
            if tag in CUT and tag not in VOID:
                self._cut_depth -= 1
            return
        if tag in VOID or tag not in KEPT:
            return
        if tag in self._open:
            # Close anything left open inside it, so the output stays balanced.
            while self._open:
                current = self._open.pop()
                self.out.append("</%s>" % current)
                if current == tag:
                    break

    def handle_data(self, data):
        if self._cut_depth:
            return
        self.out.append(escape(data, quote=False))

    def result(self):
        while self._open:
            self.out.append("</%s>" % self._open.pop())
        return "".join(self.out)


def to_html(source):
    """Sanitise a description.  Returns ``(html, dropped)``.

    ``dropped`` names each tag removed, once, so the skill can tell the partner
    what their copy lost instead of letting it disappear.
    """
    if not source:
        return "", []
    parser = _Sanitizer()
    parser.feed(source)
    parser.close()
    text = parser.result()
    # Collapse the runs of whitespace that unwrapping leaves behind.
    while "  " in text:
        text = text.replace("  ", " ")
    return text.strip(), sorted(parser.dropped)
