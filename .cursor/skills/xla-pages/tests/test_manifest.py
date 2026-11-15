"""The manifest: the YAML spec and the JSON copy the scripts read say the same thing, and the
manifest is consistent with itself."""

from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "scripts"))

import xla_common as common  # noqa: E402

YAML = SKILL / "references" / "manifest.yaml"

try:
    import yaml  # PyYAML is not part of the kit; the check runs where it happens to be installed.
except ImportError:  # pragma: no cover
    yaml = None


class ManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = common.load_manifest()

    @unittest.skipIf(yaml is None, "PyYAML is not installed")
    def test_the_json_copy_is_the_yaml_spec(self) -> None:
        self.assertEqual(yaml.safe_load(YAML.read_text(encoding="utf-8")), self.manifest)

    def test_no_merchant_project_or_site_value_is_committed(self) -> None:
        for path in (YAML, common.MANIFEST_PATH):
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertIsNone(re.search(r"(?<![\d.])\d{5,}(?![\d.])", text))
                for placeholder in ("${merchant_id}", "${project_id}", "${site_slug}"):
                    self.assertIn(placeholder, text)

    def test_every_list_item_is_text_or_a_mapping_never_both(self) -> None:
        # An unquoted "a: b" in a YAML list turns one item into a mapping.
        def walk(value: object, path: str) -> None:
            if isinstance(value, list):
                kinds = {type(item).__name__ for item in value}
                self.assertFalse({"str", "dict"} <= kinds, f"{path} mixes text and mappings")
                for index, item in enumerate(value):
                    walk(item, f"{path}[{index}]")
            elif isinstance(value, dict):
                for key, item in value.items():
                    walk(item, f"{path}.{key}")
        walk(self.manifest, "manifest")

    def test_every_page_block_has_an_xla_package(self) -> None:
        packages = self.manifest["blocks"]["packages"]
        for type_name, spec in self.manifest["page_types"].items():
            for entry in spec["blocks"]:
                for key in common.block_keys(entry):
                    with self.subTest(page=type_name, block=key):
                        self.assertTrue(packages[key]["package"].startswith("@xla-pages/"))
                        self.assertNotIn(key, self.manifest["blocks"]["no_block_exists"])

    def test_every_binding_names_a_provider_output(self) -> None:
        for type_name, spec in self.manifest["page_types"].items():
            references = [value for entry in spec["blocks"] for key, binds in entry.items()
                          if key.startswith("bind") for value in binds.values()]
            references += [v for k, v in (spec.get("seo") or {}).items()
                           if isinstance(v, str) and re.fullmatch(r"[a-z_]+\.[A-Za-z]+", v)]
            for reference in references:
                with self.subTest(page=type_name, binding=reference):
                    source, output = common.split_source(reference)
                    self.assertIn(output, common.provider_outputs(self.manifest, source))

    def test_placeholders_resolve_from_the_local_config(self) -> None:
        config = {"merchant_id": 1, "project_id": 2, "site_slug": "site"}
        resolved = common.resolve(self.manifest, config)
        self.assertEqual({"publisherProjectId": "2", "locale": "en-US"},
                         resolved["data_providers"]["game_paths"]["input"])
        self.assertNotIn("${", json.dumps(resolved))


if __name__ == "__main__":
    unittest.main()
