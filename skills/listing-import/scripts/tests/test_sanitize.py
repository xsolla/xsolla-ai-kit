"""Tests for the HTML sanitiser -- the main Steam long-description path."""

from __future__ import annotations

import unittest

from xsolla_listing_import import sanitize

from .fixtures.load import steam_listing


class TestAllowlist(unittest.TestCase):

    def test_keeps_headings_and_breaks(self):
        html, _ = sanitize.to_html("<h2>Title</h2>body<br>more")
        self.assertEqual(html, "<h2>Title</h2>body<br>more")

    def test_strips_attributes_from_kept_tags(self):
        html, _ = sanitize.to_html('<h2 class="bb_tag" id="x">T</h2>')
        self.assertEqual(html, "<h2>T</h2>")

    def test_unwraps_span_but_keeps_its_text(self):
        html, dropped = sanitize.to_html("<span class='bb'>kept</span>")
        self.assertEqual(html, "kept")
        self.assertIn("span", dropped)

    def test_cuts_video_with_its_contents(self):
        html, dropped = sanitize.to_html("a<video><source src='x'>inner</video>b")
        self.assertEqual(html, "ab")
        self.assertIn("video", dropped)

    def test_keeps_http_links_only(self):
        html, _ = sanitize.to_html('<a href="https://x.test/a">ok</a>')
        self.assertEqual(html, '<a href="https://x.test/a">ok</a>')

    def test_drops_javascript_scheme_but_keeps_the_label(self):
        html, dropped = sanitize.to_html('<a href="javascript:alert(1)">label</a>')
        self.assertEqual(html, "label")
        self.assertIn("a (unsupported scheme)", dropped)

    def test_escapes_text_that_looks_like_markup(self):
        html, _ = sanitize.to_html("<p>5 &lt; 7 &amp; 8 &gt; 2</p>")
        self.assertEqual(html, "<p>5 &lt; 7 &amp; 8 &gt; 2</p>")

    def test_empty_input(self):
        self.assertEqual(sanitize.to_html(""), ("", []))
        self.assertEqual(sanitize.to_html(None), ("", []))


class TestInjection(unittest.TestCase):
    """A store description is third-party text bound for a partner's page."""

    def test_script_and_its_body_go(self):
        html, dropped = sanitize.to_html("<p>a</p><script>alert(1)</script><p>b</p>")
        self.assertEqual(html, "<p>a</p><p>b</p>")
        self.assertIn("script", dropped)

    def test_img_onerror_goes(self):
        html, dropped = sanitize.to_html('ok<img src=x onerror="alert(1)">')
        self.assertEqual(html, "ok")
        self.assertIn("img", dropped)

    def test_no_event_handler_survives_on_a_kept_tag(self):
        html, _ = sanitize.to_html('<p onclick="alert(1)">text</p>')
        self.assertNotIn("onclick", html)
        self.assertEqual(html, "<p>text</p>")

    def test_iframe_goes(self):
        html, dropped = sanitize.to_html("<iframe src='//evil'></iframe>safe")
        self.assertEqual(html, "safe")
        self.assertIn("iframe", dropped)


class TestVoidElementRegression(unittest.TestCase):
    """The bug the real fixture caught, pinned.

    ``source`` and ``img`` are void: they never send a close tag.  Treating
    them as containers left the parser cutting to the end of the document, and
    the real 2,635-character description came out 284 characters long.
    """

    def test_void_element_inside_a_cut_region_does_not_swallow_the_rest(self):
        html, _ = sanitize.to_html(
            "<h2>One</h2><span><video><source src='a'></video></span>"
            "<h2>Two</h2><h2>Three</h2>"
        )
        self.assertEqual(html.count("<h2>"), 3)

    def test_real_description_keeps_all_three_headings(self):
        raw = steam_listing()["fields"]["long_description_html"]
        html, dropped = sanitize.to_html(raw)
        self.assertEqual(html.count("<h2>"), 3)
        self.assertNotIn("<video", html)
        self.assertNotIn("class=", html)
        self.assertIn("video", dropped)
        # Well over the 284 characters the bug produced.
        self.assertGreater(len(html), 600)


if __name__ == "__main__":
    unittest.main()


class TestAdversarialInput(unittest.TestCase):
    """Probed cases, pinned.

    A store description is third-party text bound for a partner's rendered page,
    so the interesting question is not whether normal copy converts but whether
    anything gets a live handler or a script-capable URL through. The allowlist
    is positive, which is what makes most of these fall out for free -- these
    assertions exist so a later "just allow one more tag" change has to argue
    with them.
    """

    def _clean(self, source):
        html, _dropped = sanitize.to_html(source)
        return html

    def test_scheme_check_is_case_insensitive(self):
        self.assertIn("HTTPS://x.test/a", self._clean('<a href="HTTPS://x.test/a">l</a>'))

    def test_leading_whitespace_does_not_smuggle_a_scheme(self):
        self.assertEqual(self._clean('<a href=" javascript:alert(1)">l</a>'), "l")

    def test_tab_inside_a_scheme_does_not_smuggle_it(self):
        self.assertEqual(self._clean('<a href="java\tscript:alert(1)">l</a>'), "l")

    def test_data_uri_is_refused(self):
        self.assertEqual(
            self._clean('<a href="data:text/html,<script>x</script>">l</a>'), "l")

    def test_a_quote_in_an_href_cannot_break_out_of_the_attribute(self):
        html = self._clean('<a href="https://x.test/a&quot;onmouseover=1">l</a>')
        # Escaped, so the browser reads one href value containing a quote -- not
        # an attribute boundary followed by a handler.
        self.assertIn("&quot;onmouseover", html)
        self.assertNotIn('"onmouseover', html)

    def test_markup_in_the_text_stays_text(self):
        self.assertEqual(self._clean("&lt;script&gt;"), "&lt;script&gt;")

    def test_self_closing_void_tags(self):
        self.assertEqual(self._clean("a<br/>b"), "a<br>b")
        self.assertEqual(self._clean("a<img src=x />b"), "ab")

    def test_comments_are_dropped_with_their_contents(self):
        self.assertEqual(self._clean("a<!-- <script>x</script> -->b"), "ab")

    def test_an_unbalanced_close_tag_is_ignored(self):
        self.assertEqual(self._clean("a</p>b"), "ab")

    def test_svg_and_style_go_with_their_contents(self):
        self.assertEqual(self._clean('<svg onload="alert(1)"></svg>ok'), "ok")
        self.assertEqual(self._clean("<style>body{x}</style>ok"), "ok")

    def test_unclosed_list_item_is_closed(self):
        self.assertEqual(self._clean("<ul><li>a</ul>"), "<ul><li>a</li></ul>")
