"""Cycle instruction checks that a program, a host or a user depends on.

The file once held sentence pins on the cycle skill, its references, the role files and the
operational schema. Those were deleted under the test-tiers skill's value rule ("What makes a
test worth keeping"). What stays reads content a program parses (role and skill frontmatter)
or checks a command form the shipped instructions teach against what the engine needs.
"""
from pathlib import Path
import re
import unittest

import yaml

PLUGIN = Path(__file__).resolve().parents[2]


def read(relative):
    return (PLUGIN / relative).read_text(encoding="utf-8")


def frontmatter(relative):
    """The YAML frontmatter of a plugin file, parsed as the host and the catalog read it."""
    return yaml.safe_load(read(relative).split("---", 2)[1])


def grants(relative):
    """The entries of a role's `tools` line, the grant list the host enforces."""
    return [item.strip() for item in frontmatter(relative)["tools"].split(",")]


class BookkeepingInstructionContracts(unittest.TestCase):
    """Shipped instructions run the test-evidence engine in the project's environment."""

    def test_shipped_instructions_teach_only_the_python3_evidence_form(self):
        """The engine's script environment lacks yaml and httpx; only `uv run python3` runs in the project's."""
        bare = re.compile(r"uv run\s+(?!python3\s)[^\n]*test-evidence\.py")
        roots = (PLUGIN / "skills", PLUGIN / "agents", PLUGIN / "templates")
        files = [f for root in roots for f in sorted(root.rglob("*")) if f.is_file()]
        scanned = [f for f in files if "test-evidence.py" in f.read_text(encoding="utf-8", errors="ignore")]
        self.assertTrue(scanned, "no shipped instruction names test-evidence.py; the scan is vacuous")
        offenders = [f"{f.relative_to(PLUGIN)}:{n}"
                     for f in scanned
                     for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1)
                     if bare.search(line)]
        self.assertEqual(offenders, [])


class DevLeadOwnedBuildAgreement(unittest.TestCase):
    """The engine, not the developer definition, decides a developer's worktree isolation."""

    def test_the_developer_definition_declares_no_isolation(self):
        raw = read("agents/developer.md")
        front = raw.split("---", 2)[1]
        self.assertNotIn("isolation", front)


class ParsedFrontmatterContracts(unittest.TestCase):
    """Role grants the host enforces and trigger phrases the catalog routes."""

    def test_positive_control_the_commander_grants_the_dev_lead_and_the_reviewer(self):
        # The reader finds Agent grants on the commander's tools line, so the absence below is not vacuous.
        self.assertTrue({"Agent(dev-lead)", "Agent(reviewer)"} <= set(grants("agents/commander.md")))

    def test_the_commander_grants_no_developer_dispatch(self):
        self.assertNotIn("Agent(developer)", grants("agents/commander.md"))

    def test_waiting_and_reporting_roles_hold_their_tools(self):
        for relative in ("agents/commander.md", "agents/dev-lead.md"):
            with self.subTest(path=relative):
                self.assertIn("Monitor", grants(relative))
        self.assertIn("SendMessage", grants("agents/dev-lead.md"))

    def test_the_cycle_skill_routes_the_simplify_and_queue_phrases(self):
        triggers = [phrase.strip() for phrase in
                    frontmatter("skills/cycle/SKILL.md")["metadata"]["triggers"].split("|")]
        for phrase in ("simplify cycle", "run a simplify cycle", "simplify <area>",
                       "add to the queue", "show the queue", "run the next item",
                       "run the next N items", "run the queue"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, triggers)


if __name__ == "__main__":
    unittest.main()
