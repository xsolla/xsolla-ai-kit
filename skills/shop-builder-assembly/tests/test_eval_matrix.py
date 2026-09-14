from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def load_module():
    path = ROOT / "scripts" / "prepare_eval_briefs.py"
    spec = importlib.util.spec_from_file_location("prepare_eval_briefs_for_tests", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


prepare_eval_briefs = load_module()


class EvalMatrixTests(unittest.TestCase):
    def test_matrix_adds_nine_balanced_unique_briefs(self) -> None:
        base = json.loads(
            (ROOT / "examples" / "mobile-single-page.json").read_text(encoding="utf-8")
        )
        briefs = prepare_eval_briefs.prepare(base)
        self.assertEqual(9, len(briefs))
        self.assertEqual(9, len({brief["site"]["slug"] for _, brief in briefs}))
        counts = {
            preset: sum(
                brief["site"]["preset"] == preset for _, brief in briefs
            )
            for preset in prepare_eval_briefs.MATRIX
        }
        self.assertEqual(3, counts["mobile-single-page"])
        self.assertEqual(3, counts["pc-multi-page"])
        self.assertEqual(3, counts["live-service-events"])
        self.assertEqual("run-002", briefs[0][0])
        self.assertEqual("run-010", briefs[-1][0])


if __name__ == "__main__":
    unittest.main()
