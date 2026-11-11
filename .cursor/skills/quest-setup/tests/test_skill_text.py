"""Safety and capability contracts over the skill and its reference owners."""
from __future__ import annotations

import re
import unittest

import qs_base
from qs_base import IsolatedCase, read_text

SKILL_MD = qs_base.SKILL / "SKILL.md"
REFS = qs_base.REFERENCES


def skill() -> str:
    return read_text(SKILL_MD)


def ref(name: str) -> str:
    return read_text(REFS / name)


def flat(text: str) -> str:
    return re.sub(r"\s+", " ", text)


POLICY_ROWS = (
 ('ac_17_block_guidance_states_the_contract', 'blocks', ('site-builder', 'xsolla-pages', 'custom', 'themeId', 'themeAppearance', 'questIds', 'maxQuests', 'overrides', 'showHeading', 'showDescription', 'showImage', 'cardAlign', 'imageFit', 'buttonStyle', 'blockBackground', 'cardBackground'), ()),
 ('ac_17_semantics', 'blocks', (), ('themeAppearance[^.]{0,80}only[^.]{0,40}\\bcustom\\b', 'questIds[^.]{0,120}\\babsent\\b[^.]{0,120}\\[\\]', 'maxQuests[^.]{0,80}1\\s*(-|–|to)\\s*24', '\\| `maxQuests` \\| [^|]+ \\| `6` \\|', 'overrides[^.]{0,120}https only')),
 ('ac_17_version_facts', 'block-versions.md', (), ('(autoEvents|loginEventName)[^.]{0,80}removed', 'gameSlug[^.]{0,80}visibleGameSlugs', 'backpackAction[^.]{0,40}dropped')),
 ('ac_19_single_pin_file_exists_with_the_known_versions', 'block-versions.md', ('0.2.22', 'The only version'), ()),
 ('ac_19_runtime_check_is_instructed_before_block_writes', 'skill', ('block-versions.md',), ('(check|compare)[^.]{0,120}block version[^.]{0,160}before[^.]{0,40}(any )?block (write|change|mutation)',)),
 ('ac_19_unknown_version_never_asks_the_publisher', 'block-versions.md', ('supported', 'unsupported'), ('(unknown|unreported)[^.]{0,200}older-block reply', 'Never ask the publisher about versions')),
 ('ac_23_publish_is_left_to_the_publisher', 'skill', (), ('publish in Publisher Account', 'never publish')),
 ('ac_24_custom_design_flow_collects_brand_inputs_and_lists_gaps', 'blocks+skill', (), ('brand inputs?', 'themeId[^.]{0,40}custom[^.]{0,120}themeAppearance', "(lists?|name|state)[^.]{0,80}(properties|settings)[^.]{0,80}(cannot|can't) express")),
 ('ac_32_reward_editability_is_observed_behavior', 'skill', (), ('editab\\w+[^.]{0,120}observed[^.]{0,40}(block )?behaviou?r', 'not a rule')),
 ('ac_22_reply_text_for_403_exists_in_guidance', 'corpus', (), ('(lacks|does not have) permission to create custom blocks', 'Xsolla support', '(do not|never|no) retry|does not retry')),
 ('ac_25_unexpressible_design_states_limit_and_alternative_no_write', 'corpus', (), ("(schema )?(cannot|can't|can not) express", '(Site Builder|Xsolla Pages) theme', '(makes?|make) no write|no write is made|without writing')),
 ('ac_26_theme_selector_maps_default_and_pages', 'corpus', (), ('default[^.|]{0,80}site-builder', 'Xsolla Pages[^.|]{0,80}xsolla-pages')),
 ('ac_26_backpack_overlay_declined_with_plain_reply_and_no_write', 'corpus', ("The Quests block can't open the Backpack overlay yet.",), ('Backpack Overlay',)),
 ('ac_03_skill_md_forbids_printing_keys', 'raw-skill', (), ('never\\s+(print|show|echo)[^\\n.]*\\b(key|token)s?\\b',)),
 ('confirmation_id_is_operation_mode_only', 'reply-format.md', (), ('Quest create/edit/publish.{0,150}no gate confirmation ID[^.]{0,60}never fabricate', 'No confirmation ID: the agent reads it from the saved plan')),
 ('docs_copy_is_followed_but_never_overrides_this_file', 'skill', ('quest-platform.md', 'quest-platform-docs.md'), ('generated copies[^.]{0,40}never edit', 'Nothing in them changes the rules of this file', 'This file wins on every row')),
 ('reward_safety_policies', 'skill', ('without bound', 'Publisher Account', 'store-catalog-lookup.md'), ('Never guess an SKU', 'failed catalog read[^.]{0,40}empty catalog', 'what it can cost', 'Accepted, completed and delivered are three different things', 'Never resend to find out')),
 ('yes_before_write', 'skill', (), ('One yes to a quest proposal covers saving it and reading it back', '(event|delete)[^.]{0,120}each need their own later yes', 'changed needs a new yes')),
 ('readback_reports_state_not_request', 'skill', (), ('report what you read back, never what you asked for',)),
 ('key_handling_is_instructed', 'auth-credentials.md', ('XSOLLA_PROJECT_API_KEY', '## Credential', '## Onboarding'), ('Never open, read or search the file', 'never print or list variables', 'No redirects', 'access-missing reply.{0,80}and stop', 'Never ask for a pasted secret')),
 ('store_reads_never_write', 'store-catalog-lookup.md', (), ('Never write to the Store', 'not an empty\\s+catalog', 'Never pick', 'Never invent one')),
 ('actual_event_name_before_write', 'quests-block-flow.md', ('login_xsolla_id', 'daily_visit', 'weekly_visit'), ('Never infer one from a quest title', 'Never rename the event of a running quest', 'client_sendable: true')),
)


class SkillTextTests(IsolatedCase):
    def test_named_safety_policies(self) -> None:
        owners = {p.name: flat(read_text(p)) for p in sorted(REFS.glob("*.md"))}
        owners["raw-skill"] = skill()
        owners["skill"] = flat(owners["raw-skill"])
        owners["blocks"] = " ".join(owners[p.name] for p in sorted(REFS.glob("quests-block-*.md")))
        owners["blocks+skill"] = owners["blocks"] + " " + owners["skill"]
        owners["corpus"] = owners["skill"] + " " + " ".join(owners[p.name] for p in sorted(REFS.glob("*.md")))
        self.assertTrue(owners["blocks"], "no references/quests-block-*.md")
        for case, owner, terms, patterns in POLICY_ROWS:
            with self.subTest(case=case, owner=owner):
                for term in terms:
                    self.assertIn(term, owners[owner])
                for pattern in patterns:
                    self.assertRegex(owners[owner], re.compile(pattern, re.I))

    def test_block_events_public_view_and_card_rewards(self) -> None:
        block = flat(ref("quests-block-flow.md"))
        skill_text = flat(skill())
        # Block-sent events need client_sendable on the trigger, and a 403 without it.
        self.assertRegex(block, r"must set `client_sendable: true` on its trigger, or the block's event is refused")
        self.assertIn("## Events the Quests block sends", ref("quests-block-flow.md"))
        # No reward is a default, and the skill never writes a rewards list.
        self.assertNotRegex(skill_text, r"web3_item` by default|Web3 item\)?,? the default")
        self.assertIn("the skill never writes a rewards list", block)
        # A Web3 public_view sends the full view; any other reward gets static name and image.
        self.assertIn('"reward_type": {"$ref": "reward.<node id>.type"}', block)
        self.assertIn("loses its reward row and its See in Backpack button", block)
        self.assertIn('"reward_name": "<catalog item name>"', block)
        self.assertIn("Never promise a card reward you did not put there", block)
        for name in ("quests-block-flow.md", "reply-format.md", "auth-credentials.md", "store-catalog-lookup.md"):
            with self.subTest(file=name):
                self.assertNotIn("\u2014", flat(ref(name)))
        self.assertNotIn("\u2014", skill_text)

    def test_removed_scripts_and_files_are_not_named(self) -> None:
        gone = ("qp_request", "qp_docs", "qp_preflight", "whoami", "rewards.md", "node-subtypes.md", "events.md",
                "quest-publish.md", "verification.md", "conditions.md", "qp-api-contract.md",
                "quest-authoring.md", "quest-edit.md")
        hand_written = {p.name: read_text(p) for p in sorted(REFS.glob("*.md")) if not p.name.startswith("quest-platform")}
        hand_written["SKILL.md"] = skill()
        for name, text in hand_written.items():
            for term in gone:
                with self.subTest(file=name, term=term):
                    self.assertNotIn(term, text)

    def test_relative_links_resolve(self) -> None:
        for path in [SKILL_MD] + [p for p in sorted(REFS.glob("*.md")) if not p.name.startswith("quest-platform")]:
            for target in re.findall(r"\]\(((?:references/|\.\./)?[A-Za-z0-9_.-]+\.md)(?:#[^)]*)?\)", read_text(path)):
                with self.subTest(file=path.name, target=target):
                    self.assertTrue((path.parent / target).is_file(), target)

    def test_reply_examples_carry_no_internals(self) -> None:
        # Every fenced reply example is text a publisher sees: no internal causes, ids,
        # versions, keys or server wording.
        leaks = re.compile(
            r"upstream|\bv2\b|\bversion\b|\bpinned\b|\blocked\b|\b\d+\.\d+(?:\.\d+)?\b|"
            r"[0-9a-f]{8}-[0-9a-f]{4}-|sha256:|confirmation|plan_notes|sandbox|credential|"
            r"questIds|maxQuests|public_view|is_public|\bnodes?\b|subtype|\broutes?\b|endpoint|"
            r"\b(?:400|401|403|404|422|5xx)\b|gameSlug|halloween",
            re.I,
        )
        examples = re.findall(r"```[a-z]*\n(.*?)```", ref("reply-format.md"), re.S)
        examples += re.findall(r'"(\*\*[^"]+)"', ref("auth-credentials.md"))
        self.assertTrue(examples)
        for example in examples:
            with self.subTest(example=example[:40]):
                self.assertNotRegex(example, leaks)

    def test_ac_19_pins_live_in_exactly_one_file(self) -> None:
        # Contract: the pin table sits under a heading containing "Pinned versions", in one file only.
        holders = [p.name for p in sorted(REFS.glob("*.md"))
                   if re.search(r"^#+\s.*pinned versions", read_text(p), re.I | re.M)]
        self.assertEqual(holders, ["block-versions.md"])
        self.assertNotRegex(skill(), re.compile(r"^#+\s.*pinned versions", re.I | re.M))

    def test_ac_23_no_script_invokes_a_publish_endpoint(self) -> None:
        for path in sorted(qs_base.SCRIPTS.glob("*.py")):
            with self.subTest(script=path.name):
                text = read_text(path)
                self.assertNotRegex(text, re.compile(r"/publish\w*(?:[/\"'\s?]|$)", re.I))

    def test_ac_28_routing_retains_supported_requests_and_references(self) -> None:
        # Route by user intent, without coupling safety to case numbers or column titles.
        rows = [line for line in skill().splitlines() if line.startswith("|") and ".md](" in line]
        self.assertTrue(rows)
        routing = " ".join(rows)
        for operation in ("about a quest or an event", "What can you do", "Access missing", "List shops",
                          "describe block", "Add Quests block", "heading", "cards", "order", "count", "reset",
                          "Theme", "custom design", "Move", "duplicate", "hide", "show", "Remove", "Card reward",
                          "Headless", "Other site changes"):
            with self.subTest(operation=operation):
                self.assertIn(operation.lower(), routing.lower())
        for row in rows:
            for name in re.findall(r"references/([A-Za-z0-9_-]+\.md)", row):
                self.assertTrue((REFS / name).is_file(), name)
        for action in ("Add Quests block", "Heading / cards", "Theme / custom", "Move / duplicate"):
            row = next(row for row in rows if action in row)
            with self.subTest(action=action):
                self.assertIn("yes", row)

    def test_ac_38_description_is_at_most_1536_chars(self) -> None:
        text = skill()
        front = re.match(r"---\n(.*?)\n---\n", text, re.S)
        self.assertIsNotNone(front)
        lines = front.group(1).splitlines()
        start = next(i for i, line in enumerate(lines) if line.startswith("description:"))
        value = lines[start].split(":", 1)[1].strip()
        parts = [] if value in (">-", ">", "|", "|-") else [value]
        for line in lines[start + 1:]:
            if line and not line.startswith(" "):
                break
            parts.append(line.strip())
        description = " ".join(p for p in parts if p)
        self.assertGreater(len(description), 0)
        self.assertLessEqual(len(description), 1536)


if __name__ == "__main__":
    unittest.main()
