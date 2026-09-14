"""Tests for the BBCode converter -- the pasted-store-copy path."""

from __future__ import annotations

import unittest

from xsolla_listing_import import bbcode


class TestConversion(unittest.TestCase):

    def test_headings(self):
        html, _ = bbcode.to_html("[h2]Title[/h2]")
        self.assertEqual(html, "<h2>Title</h2>")

    def test_emphasis(self):
        html, _ = bbcode.to_html("[b]bold[/b] and [i]italic[/i]")
        self.assertIn("<strong>bold</strong>", html)
        self.assertIn("<em>italic</em>", html)

    def test_unordered_list(self):
        html, _ = bbcode.to_html("[list]\n[*] one\n[*] two\n[/list]")
        self.assertEqual(html, "<ul><li>one</li><li>two</li></ul>")

    def test_ordered_list(self):
        html, _ = bbcode.to_html("[olist][*] one[/olist]")
        self.assertEqual(html, "<ol><li>one</li></ol>")

    def test_text_after_a_heading_is_wrapped(self):
        """The regression: a single newline after a heading left text bare."""
        html, _ = bbcode.to_html("[h2]Title[/h2]\nSentence.")
        self.assertEqual(html, "<h2>Title</h2><p>Sentence.</p>")

    def test_labelled_url(self):
        html, _ = bbcode.to_html("[url=https://x.test/a]Label[/url]")
        self.assertEqual(html, '<p><a href="https://x.test/a">Label</a></p>')

    def test_img_is_dropped_and_reported(self):
        html, dropped = bbcode.to_html("a[img]{STEAM_APP_IMAGE}/x.jpg[/img]b")
        self.assertNotIn("img", html)
        self.assertTrue(any("img" in item for item in dropped))

    def test_youtube_is_reported_not_rendered(self):
        html, dropped = bbcode.to_html("[previewyoutube=dQw4w9WgXcQ;full][/previewyoutube]")
        self.assertNotIn("dQw4w9WgXcQ", html)
        self.assertIn("youtube:dQw4w9WgXcQ", dropped)
        self.assertEqual(bbcode.youtube_ids("[previewyoutube=abc123;full][/previewyoutube]"),
                         ["abc123"])

    def test_raw_html_in_the_source_is_escaped(self):
        html, _ = bbcode.to_html("<script>alert(1)</script>")
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_empty(self):
        self.assertEqual(bbcode.to_html(""), ("", []))


class TestStripTracking(unittest.TestCase):
    """Parsed, not pattern-matched: removing the first parameter with a regex
    leaves the query headless."""

    def test_removes_utm_and_keeps_the_rest(self):
        self.assertEqual(
            bbcode.strip_tracking("https://x.test/a?utm_source=steam&id=2"),
            "https://x.test/a?id=2",
        )

    def test_first_parameter_removed_keeps_the_question_mark(self):
        out = bbcode.strip_tracking("https://x.test/a?utm_source=s&keep=1")
        self.assertTrue(out.endswith("?keep=1"), out)
        self.assertNotIn("&keep", out)

    def test_all_parameters_removed_drops_the_query(self):
        self.assertEqual(bbcode.strip_tracking("https://x.test/a?utm_source=s"),
                         "https://x.test/a")

    def test_no_query_is_untouched(self):
        self.assertEqual(bbcode.strip_tracking("https://x.test/a"), "https://x.test/a")

    def test_ref_and_fbclid_go(self):
        self.assertEqual(bbcode.strip_tracking("https://x.test/a?ref=y&fbclid=z&k=1"),
                         "https://x.test/a?k=1")

    def test_tracking_is_stripped_inside_a_converted_link(self):
        html, _ = bbcode.to_html("[url=https://x.test/a?utm_source=steam&id=2]L[/url]")
        self.assertIn("id=2", html)
        self.assertNotIn("utm_source", html)


if __name__ == "__main__":
    unittest.main()
