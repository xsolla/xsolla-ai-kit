"""Repository context size; live-report acceptance remains in the report schema fixture."""
import unittest

import qs_base
from qs_base import IsolatedCase


class RepoChecksTests(IsolatedCase):
    def test_ac_36_agents_md_is_below_32768_bytes(self) -> None:
        self.assertLess((qs_base.REPO / "AGENTS.md").stat().st_size, 32768)


if __name__ == "__main__":
    unittest.main()
