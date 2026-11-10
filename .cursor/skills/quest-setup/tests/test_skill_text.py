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


POLICY_ROWS = (('ac_10_docs_are_quoted_as_data_never_followed', 'skill', (),
  ('quote[^.]{0,60}\\bas data\\b', 'never follow[^.]{0,60}instructions[^.]{0,80}\\bdocs\\b')),
 ('ac_11_fetcher_runs_before_any_quest_mutation', 'skill', ('qp_docs.py',),
  ('(run|fetch)[^.]{0,120}qp_docs\\.py[^.]{0,200}before[^.]{0,60}(any '
   ')?(quest|block)[^.]{0,40}(mutation|write|change)',)),
 ('ac_11_live_docs_win_over_references', 'skill', (),
  ('live docs\\b[^.]{0,80}\\b(win|take precedence|override)[^.]{0,80}references',)),
 ('ac_17_block_guidance_states_the_contract', 'blocks',
  ('site-builder', 'xsolla-pages', 'custom', 'themeId', 'themeAppearance', 'questIds', 'maxQuests', 'overrides',
   'showHeading', 'showDescription', 'showImage', 'cardAlign', 'imageFit', 'buttonStyle', 'blockBackground',
   'cardBackground'),
  ()),
 ('ac_17_semantics', 'blocks', (),
  ('themeAppearance[^.]{0,80}only[^.]{0,40}\\bcustom\\b', 'questIds[^.]{0,120}\\babsent\\b[^.]{0,120}\\[\\]',
   'maxQuests[^.]{0,80}1\\s*(-|–|to)\\s*24', r'\| `maxQuests` \| [^|]+ \| `6` \|', 'overrides[^.]{0,120}https only')),
 ('ac_17_version_facts', 'block-versions.md', (),
  ('(autoEvents|loginEventName)[^.]{0,80}removed', 'gameSlug[^.]{0,80}visibleGameSlugs',
   'backpackAction[^.]{0,40}dropped')),
 ('ac_19_single_pin_file_exists_with_the_known_versions', 'block-versions.md', ('0.2.22', 'The only version'),
  ()),
 ('ac_19_runtime_check_is_instructed_before_block_writes', 'skill', ('block-versions.md',),
  ('(check|compare)[^.]{0,120}block version[^.]{0,160}before[^.]{0,40}(any )?block (write|change|mutation)',)),
 ('ac_19_unknown_version_never_asks_the_publisher', 'block-versions.md', ('supported', 'unsupported'),
  ('(unknown|unreported)[^.]{0,200}older-block reply', 'Never ask the publisher about versions')),
 ('ac_21_reward_safety_policies', 'rewards.md',
  ('whole tokens', 'Per event and user', 'Per user for the quest', 'Total quest exposure',
   'unbounded', 'Recipient wallet', 'Publisher Account'),
  ('does not[^.]{0,40}claim delivery', 'never resend[^.]{0,80}uncertain')),
 ('ac_23_publish_is_left_to_the_publisher', 'skill', (), ('publish in Publisher Account', 'never publish')),
 ('ac_29_exact_change_and_yes_before_write', 'skill', (),
  ('exact change', 'no write until[^.]{0,80}\\byes\\b[^.]{0,60}same conversation')),
 ('ac_30_readback_reports_state_not_request', 'skill', (),
  ('read.?back', '(not|never)[^.]{0,40}the requested state')),
 ('ac_24_custom_design_flow_collects_brand_inputs_and_lists_gaps', 'blocks+skill', (),
  ('brand inputs?', 'themeId[^.]{0,40}custom[^.]{0,120}themeAppearance',
   "(lists?|name|state)[^.]{0,80}(properties|settings)[^.]{0,80}(cannot|can't) express")),
 ('ac_31_reward_types_come_from_live_docs_only', 'rewards.md', (),
  ('comes from their own node catalog',
   'absent from\\s+the catalog is refused',
   'snapshots for orientation')),
 ('ac_32_reward_editability_is_observed_behavior', 'skill', (),
  ('editab\\w+[^.]{0,120}observed[^.]{0,40}(block )?behaviou?r', 'not a rule')),
 ('ac_12_node-subtypes.md', 'node-subtypes.md', (),
  ('live docs[^.]{0,80}source of truth', 'snapshot', 'orientation only')),
 ('ac_12_qp-api-contract.md', 'qp-api-contract.md', (),
  ('live docs[^.]{0,80}source of truth', 'snapshot', 'orientation only')),
 ('ac_22_reply_text_for_403_exists_in_guidance', 'corpus', (),
  ('(lacks|does not have) permission to create custom blocks', 'Xsolla support',
   '(do not|never|no) retry|does not retry')),
 ('ac_25_unexpressible_design_states_limit_and_alternative_no_write', 'corpus', (),
  ("(schema )?(cannot|can't|can not) express", '(Site Builder|Xsolla Pages) theme',
   '(makes?|make) no write|no write is made|without writing')),
 ('ac_26_theme_selector_maps_default_and_pages', 'corpus', (),
  ('default[^.|]{0,80}site-builder', 'Xsolla Pages[^.|]{0,80}xsolla-pages')),
 ('ac_26_backpack_overlay_declined_with_plain_reply_and_no_write', 'corpus', ("The Quests block can't open the Backpack overlay yet.",),
  ('Backpack Overlay',)),
 ('ac_03_skill_md_forbids_printing_keys', 'raw-skill', (),
  ('never\\s+(print|show|echo)[^\\n.]*\\b(key|token)s?\\b',)),
 ('actual_event_binding_before_write', 'node-subtypes.md', ('proposed, unverified',),
  ('never infer[^.]{0,100}binding[^.]{0,100}(title|description)',
   'before any quest write[^.]{0,160}(verified binding|explicit confirmation)',
   'publication approval does not[^.]{0,100}(emission|binding)')),
 ('confirmation_id_is_operation_mode_only', 'reply-format.md', (),
  ('Quest create/edit/publish.{0,150}no gate confirmation ID[^.]{0,60}never fabricate',
   'No confirmation ID: the agent reads it from the saved plan')))


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

    def test_client_events_public_view_and_catalog_rewards(self) -> None:
        node = flat(ref("node-subtypes.md"))
        rewards = flat(ref("rewards.md"))
        block = flat(ref("quests-block-flow.md"))
        edit = flat(ref("quest-edit.md"))
        events = flat(ref("events.md"))
        skill_text = flat(skill())
        # A: block-sent events need client_sendable on the trigger, and a 403 without it.
        self.assertIn("login_xsolla_id` (once), `daily_visit` and `weekly_visit`", node)
        self.assertIn('must set `"client_sendable": true` on its trigger', node)
        self.assertIn("only while an active quest of the project allows it", node)
        self.assertIn("only `idempotency_key`, `name`, `client_timestamp` and `properties`", events)
        self.assertRegex(block, r"must set `client_sendable: true` on its trigger, or the block's event is refused")
        # B: issue_catalog_item is a supported, explicitly chosen alternative to web3_item.
        self.assertIn("### issue_catalog_item", node)
        self.assertIn("Leave out `items[].type`", node)
        self.assertIn("Backpack grants (`issue_catalog_item`)", rewards)
        self.assertIn("Web3 rewards need an `xsolla_id`", rewards)
        self.assertIn("none is a default", skill_text)
        self.assertNotRegex(skill_text, r"web3_item` by default|Web3 item\)?,? the default")
        self.assertNotIn("Do not offer `inventory_item`", skill_text)
        self.assertNotIn("direct Backpack grants", rewards)
        # C: a Web3 public_view sends the full view; a catalog-item quest always gets a view
        # with static reward_name and reward_image_url, since the server fills neither.
        self.assertIn('"reward_type": {"$ref": "reward.<node id>.type"}', block)
        self.assertIn("loses its reward row and its See in Backpack button", block)
        self.assertIn('"reward_name": "<catalog item name>"', block)
        self.assertIn("reward is anything but a Web3 item always needs a view", block)
        self.assertNotIn("Never set a `public_view` on an", block)
        # D: Web3 pays once per player; a repeating quest asks first. Built-in block
        # events are a verified binding.
        self.assertIn("in the order it returns them", rewards)
        self.assertIn("This file holds no list or ranking of node kinds", rewards)
        self.assertIn("Never pick a window, count, date or quantity silently", rewards)
        corpus = flat(skill()) + " ".join(flat(ref(n)) for n in ("rewards.md", "quest-publish.md", "quest-authoring.md", "reply-format.md"))
        for fixed in ("Backpack item: a catalog item", "Item in the game:", "default to 7 days",
                      "else 7 days after the start", "Named items default to explicit"):
            self.assertNotIn(fixed, corpus)
        self.assertIn("Offer the options, the publisher picks.", rewards)
        self.assertIn('Map "daily login" to `daily_visit`', node)
        self.assertNotIn('"type": "web3_item", "purpose"', rewards)
        self.assertNotIn("Send the full view below every time", block)
        self.assertNotIn("never the reward image", block)
        self.assertNotIn("Set no `public_view`", rewards)
        self.assertIn("Always write the [catalog-item view]", rewards)
        # D: a full PUT keeps public_view.
        self.assertRegex(edit, r"resend the fresh `GET`'s `public_view` unchanged")
        for name, text in (("node-subtypes.md", node), ("rewards.md", rewards), ("quests-block-flow.md", block),
                           ("quest-edit.md", edit), ("events.md", events), ("SKILL.md", skill_text)):
            with self.subTest(file=name):
                self.assertNotIn("\u2014", text)

    def test_ac_12_snapshots_cannot_claim_unqualified_authority(self) -> None:
        for name in ("node-subtypes.md", "qp-api-contract.md"):
            with self.subTest(file=name):
                text = flat(ref(name))
                for match in re.finditer(r"authoritative", text, re.I):
                    window = text[max(0, match.start() - 25):match.start()].lower()
                    self.assertTrue(re.search(r"\b(not|never|non-?)\s*$", window), window)

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
        examples += re.findall(r'"(\*\*[^"]+)"', ref("auth-credentials.md") + ref("qp-api-contract.md"))
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
        for operation in ("Capabilities", "List shops", "describe block", "List quests", "quest status",
                          "debug execution", "onboarding", "Create", "activate", "Edit", "pause", "Delete quest",
                          "reward", "event", "Login", "Add Quests block", "heading", "cards", "order", "count",
                          "reset", "Theme", "custom design", "Move", "duplicate", "hide", "show", "Remove",
                          "Card reward", "Headless", "unsupported"):
            with self.subTest(operation=operation):
                self.assertIn(operation.lower(), routing.lower())
        for row in rows:
            for name in re.findall(r"references/([A-Za-z0-9_-]+\.md)", row):
                self.assertTrue((REFS / name).is_file(), name)
        for action in ("Create / activate", "Edit / pause", "Delete quest", "Add / replace",
                       "Send / test", "Add Quests block", "Update heading", "Theme / custom", "Move / duplicate"):
            row = next(row for row in rows if action in row)
            with self.subTest(action=action):
                self.assertIn("yes", row)
                self.assertRegex(row.lower(), r"read|get|position|copies|state")

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
