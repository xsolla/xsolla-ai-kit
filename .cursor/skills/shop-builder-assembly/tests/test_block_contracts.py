from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_extractor():
    path = ROOT / "scripts" / "extract_block_contracts.py"
    spec = importlib.util.spec_from_file_location("extract_block_contracts_test", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


extractor = load_extractor()


class BlockContractTests(unittest.TestCase):
    def test_extracts_wrapped_export_without_ids_or_content(self) -> None:
        exported = {
            "ok": True,
            "data": {
                "_id": "landing-secret-id",
                "type": "store",
                "cart": {"enable": True},
                "blocks": [
                    {
                        "_id": "block-secret-id",
                        "module": "faq",
                        "blockVersion": 2,
                        "values": {"title": {"id": "L:secret"}, "enable": True},
                        "components": [{"_id": "component-secret-id", "question": {}}],
                    }
                ],
            },
        }
        result = extractor.extract_contracts(exported, "fixture")
        self.assertEqual("store", result["landing_type"])
        self.assertEqual(
            {
                "enable": ["boolean"],
                "title": ["object"],
            },
            result["modules"][0]["block_value_types"],
        )
        self.assertEqual(["_id", "question"], result["modules"][0]["component_item_fields"])
        self.assertNotIn("secret", str(result))

    def test_merges_instances_of_the_same_module(self) -> None:
        exported = {
            "blocks": [
                {
                    "module": "packs",
                    "blockVersion": 1,
                    "values": {"layout": "vertical"},
                    "components": [],
                },
                {
                    "module": "packs",
                    "blockVersion": 2,
                    "values": {"layout": "horizontal", "title": None},
                    "components": [],
                },
            ]
        }
        contract = extractor.extract_contracts(exported, "fixture")["modules"][0]
        self.assertEqual(2, contract["observed_instances"])
        self.assertEqual([1, 2], contract["block_versions"])
        self.assertEqual(["null"], contract["block_value_types"]["title"])

    def test_extracts_federated_block_by_effective_module(self) -> None:
        exported = {
            "blocks": [
                {
                    "module": "federated",
                    "values": {
                        "blockId": "social-quests",
                        "version": "5.0.0",
                        "host": "https://example.invalid/private-path/",
                        "defaultData": {"questsEnabled": False},
                        "internalBlockValues": {
                            "questsEnabled": True,
                            "translations": {},
                        },
                    },
                    "components": [],
                }
            ]
        }

        result = extractor.extract_contracts(exported, "fixture")
        contract = result["modules"][0]
        self.assertEqual(2, result["version"])
        self.assertEqual("social-quests", contract["module"])
        self.assertEqual(["federated"], contract["transport_modules"])
        self.assertEqual(["5.0.0"], contract["package_versions"])
        self.assertEqual(
            {"questsEnabled": ["boolean"], "translations": ["object"]},
            contract["block_value_types"],
        )
        self.assertNotIn("host", str(result))
        self.assertNotIn("private-path", str(result))

    def test_rejects_malformed_blocks(self) -> None:
        with self.assertRaisesRegex(ValueError, "blocks"):
            extractor.extract_contracts({"blocks": {}}, "fixture")

    def test_rendered_contracts_end_with_newline(self) -> None:
        self.assertEqual('{\n  "version": 2\n}\n', extractor.render_contracts({"version": 2}))


if __name__ == "__main__":
    unittest.main()
