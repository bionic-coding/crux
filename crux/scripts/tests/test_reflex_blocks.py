"""The commander does not preload the forge-skill skill.

The commander reports a capability gap to its caller: it holds no Edit or
Write tool, so it cannot author a skill. Its frontmatter `skills:` list is
what validate-catalog projects into the agent catalog and what each host
preloads, so the list must not name `forge-skill`.

Stdlib unittest only (no third-party deps).
"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
AGENTS_DIR = REPO_ROOT / "crux" / "agents"


class CommanderGapRoutingTests(unittest.TestCase):
    """commander.md does not preload forge-skill."""

    def setUp(self):
        self.text = (AGENTS_DIR / "commander.md").read_text(encoding="utf-8")

    def test_forge_skill_not_preloaded(self):
        frontmatter = self.text.split("---", 2)[1]
        skills_line = next(
            line for line in frontmatter.splitlines() if line.startswith("skills:")
        )
        self.assertNotIn("forge-skill", skills_line)


if __name__ == "__main__":
    unittest.main()
