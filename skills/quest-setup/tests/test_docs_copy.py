"""The Quest Platform docs copy is generated: it must match what the sync script writes."""
import importlib.util
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
REFERENCES = REPO / "skills" / "quest-setup" / "references"
SCRIPT = REPO / ".github" / "scripts" / "sync_quest_platform_docs.py"

spec = importlib.util.spec_from_file_location("sync_quest_platform_docs", SCRIPT)
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


def page(skill: str, docs: str) -> str:
    return f"# AI skill\n\n````markdown\n{skill}\n````\n\n**The documentation.**\n\n````markdown\n{docs}\n````\n"


class GeneratedFiles(unittest.TestCase):
    def test_both_files_carry_the_generated_header(self):
        header = sync.HEADER.format(url=sync.PAGE_URL)
        for name in ("quest-platform.md", "quest-platform-docs.md"):
            text = (REFERENCES / name).read_text(encoding="utf-8")
            self.assertTrue(text.startswith(header), f"{name} was edited by hand or lost its header")

    def test_skill_file_is_the_publisher_skill(self):
        text = (REFERENCES / "quest-platform.md").read_text(encoding="utf-8")
        self.assertIn(sync.SKILL_TITLE, text)

    def test_no_heading_keeps_the_public_site_indent(self):
        for name in ("quest-platform.md", "quest-platform-docs.md"):
            text = (REFERENCES / name).read_text(encoding="utf-8")
            self.assertNotRegex(text, r"(?m)^ #")


class SplitPage(unittest.TestCase):
    SKILL = sync.SKILL_TITLE + "\n\n" + "x" * sync.MIN_SKILL_BYTES
    DOCS = " # Introduction\n\n" + "y" * sync.MIN_DOCS_BYTES

    def test_splits_and_unindents(self):
        skill, docs = sync.split_page(page(self.SKILL, self.DOCS))
        self.assertTrue(skill.startswith(sync.SKILL_TITLE))
        self.assertTrue(docs.startswith("# Introduction"))

    def test_site_links_become_full_addresses(self):
        docs = self.DOCS + "\n[Create](/api/quests/publisher-api/create-quest-in-project) and [x](other.md)\n"
        _, got = sync.split_page(page(self.SKILL, docs))
        self.assertIn("(https://developers.xsolla.com/api/quests/publisher-api/create-quest-in-project)", got)
        self.assertIn("[x](other.md)", got)

    def test_keeps_a_longer_fence_inside_a_block(self):
        docs = self.DOCS + "\n```json\n{}\n```\n"
        _, got = sync.split_page(page(self.SKILL, docs))
        self.assertIn("```json", got)

    def test_refuses_a_page_with_one_block(self):
        with self.assertRaises(sync.PageError):
            sync.split_page(f"````markdown\n{self.SKILL}\n````\n")

    def test_refuses_a_truncated_page(self):
        with self.assertRaises(sync.PageError):
            sync.split_page(page(sync.SKILL_TITLE + "\n\nshort", self.DOCS))

    def test_refuses_a_page_that_is_not_the_publisher_skill(self):
        with self.assertRaises(sync.PageError):
            sync.split_page(page("# Something else\n" + "x" * sync.MIN_SKILL_BYTES, self.DOCS))

    def test_refuses_an_unclosed_block(self):
        with self.assertRaises(sync.PageError):
            sync.split_page(f"````markdown\n{self.SKILL}\n")


if __name__ == "__main__":
    unittest.main()
