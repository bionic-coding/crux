"""The test-tiers skill's catalog data: its trigger phrases and its bundle.

Programs read both. validate-catalog.py projects the frontmatter name and trigger phrases into
crux/catalog/skills.json and the routing tables, and reads crux/catalog/bundles.yml.
"""
from pathlib import Path
import json
import re
import unittest

PLUGIN = Path(__file__).resolve().parents[2]
SKILL = PLUGIN / "skills" / "test-tiers" / "SKILL.md"


def frontmatter(path):
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    return match.group(1) if match else ""


class TestTiersSkillContracts(unittest.TestCase):
    def test_skill_is_catalogued_with_trigger_phrases(self):
        head = frontmatter(SKILL)
        self.assertIn("name: test-tiers", head)
        triggers = re.search(r'triggers: "([^"]+)"', head)
        self.assertIsNotNone(triggers, "the skill carries no trigger phrases")
        phrases = [p.strip() for p in triggers.group(1).split("|")]
        for phrase in ("label the tests", "check the test tiers", "list the release tier"):
            self.assertIn(phrase, phrases)
        catalog = json.loads((PLUGIN / "catalog" / "skills.json").read_text(encoding="utf-8"))
        entries = catalog["skills"] if isinstance(catalog, dict) else catalog
        names = [entry["name"] for entry in entries]
        self.assertIn("test-tiers", names)

    def test_skill_is_in_a_bundle(self):
        bundles = (PLUGIN / "catalog" / "bundles.yml").read_text(encoding="utf-8")
        self.assertIn('- "test-tiers"', bundles)


if __name__ == "__main__":
    unittest.main()
