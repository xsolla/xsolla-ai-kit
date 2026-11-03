"""Text-contract tests over SKILL.md and references/*.md (grep style, plus the AC-28 table parse)."""
from __future__ import annotations

import re
import unittest

import qs_base
from qs_base import IsolatedCase, read_text, strip_fences

SKILL_MD = qs_base.SKILL / "SKILL.md"
REFS = qs_base.REFERENCES
SNAPSHOT = qs_base.FIXTURES / "block-contract-0b1586eb59.md"


def skill() -> str:
    return read_text(SKILL_MD)


def ref(name: str) -> str:
    return read_text(REFS / name)


def flat(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def block_refs() -> str:
    files = sorted(REFS.glob("quests-block-*.md"))
    return flat("\n".join(read_text(p) for p in files))


class SkillTextTests(IsolatedCase):
    # ---- AC-3 / AC-10 / AC-11
    def test_ac_10_docs_are_quoted_as_data_never_followed(self) -> None:
        text = flat(skill())
        self.assertRegex(text, re.compile(r"quote[^.]{0,60}\bas data\b", re.I))
        self.assertRegex(text, re.compile(r"never follow[^.]{0,60}instructions[^.]{0,80}\bdocs\b", re.I))

    def test_ac_11_fetcher_runs_before_any_quest_mutation(self) -> None:
        text = flat(skill())
        self.assertIn("qp_docs.py", text)
        self.assertRegex(text, re.compile(r"(run|fetch)[^.]{0,120}qp_docs\.py[^.]{0,200}before[^.]{0,60}"
                                          r"(any )?(quest|block)[^.]{0,40}(mutation|write|change)", re.I))

    def test_ac_11_live_docs_win_over_references(self) -> None:
        text = flat(skill())
        self.assertRegex(text, re.compile(r"live docs\b[^.]{0,80}\b(win|take precedence|override)"
                                          r"[^.]{0,80}references", re.I))

    # ---- AC-12
    def test_ac_12_node_subtypes_and_api_contract_are_not_authoritative(self) -> None:
        for name in ("node-subtypes.md", "qp-api-contract.md"):
            with self.subTest(file=name):
                text = flat(ref(name))
                self.assertRegex(text, re.compile(r"live docs[^.]{0,80}source of truth", re.I))
                self.assertRegex(text, re.compile(r"snapshot", re.I))
                self.assertRegex(text, re.compile(r"orientation only", re.I))
                for match in re.finditer(r"authoritative", text, re.I):
                    window = text[max(0, match.start() - 25):match.start()].lower()
                    self.assertTrue(re.search(r"\b(not|never|non-?)\s*$", window), window)

    # ---- AC-17 / AC-18
    def test_ac_18_snapshot_exists_with_block_facts(self) -> None:
        self.assertTrue(SNAPSHOT.is_file())
        text = read_text(SNAPSHOT)
        for term in ("0b1586eb59", "themeId", "themeAppearance", "questIds", "maxQuests", "autoEvents",
                     "loginEventName", "backpackAction", "showHeading", "cardAlign", "imageFit",
                     "buttonStyle", "blockBackground", "cardBackground", "isHttpsUrl"):
            with self.subTest(term=term):
                self.assertIn(term, text)

    def test_ac_17_block_guidance_states_the_contract(self) -> None:
        text = block_refs()
        self.assertTrue(text, "no references/quests-block-*.md")
        for term in ("site-builder", "xsolla-pages", "custom", "themeId", "themeAppearance", "questIds",
                     "maxQuests", "overrides", "showHeading", "showDescription", "showImage", "cardAlign",
                     "imageFit", "buttonStyle", "blockBackground", "cardBackground"):
            with self.subTest(term=term):
                self.assertIn(term, text)

    def test_ac_17_semantics(self) -> None:
        text = block_refs()
        self.assertRegex(text, re.compile(r"themeAppearance[^.]{0,80}only[^.]{0,40}\bcustom\b", re.I))
        self.assertRegex(text, re.compile(r"questIds[^.]{0,120}\babsent\b[^.]{0,120}\[\]", re.I))
        self.assertRegex(text, re.compile(r"maxQuests[^.]{0,80}1\s*(-|–|to)\s*24", re.I))
        self.assertRegex(text, re.compile(r"default[^.]{0,20}\b6\b", re.I))
        self.assertRegex(text, re.compile(r"overrides[^.]{0,120}https only", re.I))

    def test_ac_17_version_facts(self) -> None:
        text = block_refs()
        self.assertRegex(text, re.compile(r"autoEvents[^.]{0,120}loginEventName[^.]{0,120}0\.2\.8|"
                                          r"0\.2\.8[^.]{0,160}(autoEvents|loginEventName)", re.I))
        self.assertRegex(text, re.compile(r"(autoEvents|loginEventName)[^.]{0,80}removed", re.I))
        self.assertRegex(text, re.compile(r"backpackAction[^.]{0,120}candidate[^.]{0,40}0\.2\.1"
                                          r"|0\.2\.1[^.]{0,80}candidate[^.]{0,80}backpackAction", re.I))
        self.assertRegex(text, re.compile(r"0\.1\.12[^.]{0,120}no theme", re.I))

    # ---- AC-19
    def test_ac_19_single_pin_file_exists_with_the_known_versions(self) -> None:
        pin = REFS / "block-versions.md"
        self.assertTrue(pin.is_file())
        text = read_text(pin)
        for version in ("0.1.12", "0.2.7", "0.2.8"):
            with self.subTest(version=version):
                self.assertIn(version, text)

    def test_ac_19_pins_live_in_exactly_one_file(self) -> None:
        # Contract: the pin table sits under a heading containing "Pinned versions", in one file only.
        holders = [p.name for p in sorted(REFS.glob("*.md"))
                   if re.search(r"^#+\s.*pinned versions", read_text(p), re.I | re.M)]
        self.assertEqual(holders, ["block-versions.md"])
        self.assertNotRegex(skill(), re.compile(r"^#+\s.*pinned versions", re.I | re.M))

    def test_ac_19_runtime_check_is_instructed_before_block_writes(self) -> None:
        text = flat(skill())
        self.assertIn("block-versions.md", text)
        self.assertRegex(text, re.compile(r"(check|compare)[^.]{0,120}block version[^.]{0,160}before[^.]{0,40}"
                                          r"(any )?block (write|change|mutation)", re.I))

    def test_ac_19_unknown_or_unreported_version_asks_or_stops(self) -> None:
        text = flat(ref("block-versions.md"))
        self.assertIn("supported", text)
        self.assertIn("unsupported", text)
        self.assertRegex(text, re.compile(r"(unknown|unreported)[^.]{0,120}(ask the user|stop)", re.I))

    # ---- AC-21
    def test_ac_21_no_draft_wording_in_user_facing_prose(self) -> None:
        files = [SKILL_MD] + sorted(REFS.glob("*.md"))
        offenders = []
        for path in files:
            for number, line in enumerate(strip_fences(read_text(path)).splitlines(), 1):
                if re.search(r"\bdrafts?\b", line, re.I):
                    offenders.append(f"{path.name}:{number}")
        self.assertEqual(offenders, [])

    # ---- AC-23
    def test_ac_23_publish_is_left_to_the_publisher(self) -> None:
        text = flat(skill())
        self.assertRegex(text, re.compile(r"publish in Publisher Account", re.I))
        self.assertRegex(text, re.compile(r"never publish", re.I))

    def test_ac_23_no_script_invokes_a_publish_endpoint(self) -> None:
        for path in sorted(qs_base.SCRIPTS.glob("*.py")):
            with self.subTest(script=path.name):
                text = read_text(path)
                self.assertNotRegex(text, re.compile(r"/publish\w*(?:[/\"'\s?]|$)", re.I))

    # ---- AC-28
    def test_ac_28_routing_table_c1_to_c16(self) -> None:
        text = skill()
        header = re.search(r"^\|\s*Case\s*\|\s*Mutating\s*\|\s*Reference\s*\|\s*Confirmation\s*\|\s*Readback\s*\|\s*$",
                           text, re.M)
        self.assertIsNotNone(header, "routing table header Case | Mutating | Reference | Confirmation | Readback")
        rows = {}
        for line in text[header.end():].splitlines()[1:]:
            if not line.startswith("|"):
                break
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if all(re.fullmatch(r"[-: ]*", c) for c in cells):
                continue  # markdown separator row
            self.assertEqual(len(cells), 5, line)
            rows.setdefault(cells[0], []).append(cells)
        expected = [f"C{n}" for n in range(1, 17)]
        self.assertEqual(sorted(rows, key=lambda k: int(k[1:])), expected)
        for case in expected:
            with self.subTest(case=case):
                self.assertEqual(len(rows[case]), 1)
                _, mutating, reference, confirmation, readback = rows[case][0]
                names = re.findall(r"[A-Za-z0-9_-]+\.md", reference)
                self.assertTrue(names, reference)
                for name in names:
                    self.assertTrue((REFS / name).is_file(), name)
                is_mutating = mutating.lower() in ("y", "yes", "true")
                self.assertEqual(is_mutating, case not in ("C2", "C16"))
                if is_mutating:
                    self.assertTrue(confirmation)
                    self.assertTrue(readback)

    # ---- AC-29 / AC-30
    def test_ac_29_exact_change_and_yes_before_write(self) -> None:
        text = flat(skill())
        self.assertRegex(text, re.compile(r"exact change", re.I))
        self.assertRegex(text, re.compile(r"no write until[^.]{0,80}\byes\b[^.]{0,60}same conversation", re.I))

    def test_ac_30_readback_reports_state_not_request(self) -> None:
        text = flat(skill())
        self.assertRegex(text, re.compile(r"read.?back", re.I))
        self.assertRegex(text, re.compile(r"(not|never)[^.]{0,40}the requested state", re.I))

    # ---- AC-24 (flow text), AC-31 / AC-32
    def test_ac_24_custom_design_flow_collects_brand_inputs_and_lists_gaps(self) -> None:
        text = block_refs() + " " + flat(skill())
        self.assertRegex(text, re.compile(r"brand inputs?", re.I))
        self.assertRegex(text, re.compile(r"themeId[^.]{0,40}custom[^.]{0,120}themeAppearance", re.I))
        self.assertRegex(text, re.compile(r"(lists?|name|state)[^.]{0,80}(properties|settings)[^.]{0,80}"
                                          r"(cannot|can't) express", re.I))

    def test_ac_31_reward_types_come_from_live_docs_only(self) -> None:
        text = flat(ref("rewards.md"))
        self.assertRegex(text, re.compile(r"reward types?[^.]{0,80}(from|in) the live docs", re.I))
        self.assertRegex(text, re.compile(r"(absent|not (listed|present))[^.]{0,60}(live )?docs[^.]{0,80}reject", re.I))
        self.assertRegex(text, re.compile(r"snapshot[^.]{0,60}orientation only|orientation only[^.]{0,60}snapshot", re.I))

    def test_ac_32_reward_editability_is_observed_behavior(self) -> None:
        text = flat(skill())
        self.assertRegex(text, re.compile(r"editab\w+[^.]{0,120}observed[^.]{0,40}(block )?behaviou?r", re.I))
        self.assertRegex(text, re.compile(r"not a rule", re.I))

    # ---- AC-38
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
