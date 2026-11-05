"""Tests for adr-precouncil.py `rules`: read-only, advisory, fixture trees only.

Every test builds a throwaway repo in a tempdir; none reads this repo's tree.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "adr-precouncil.py"

RESOLVER = {
    "ADR-0001/old-a": {"rule": "Old rule A holds.", "source_adr": "ADR-0001",
                       "source_status": "Accepted"},
    "ADR-0001/old-b": {"rule": "Old rule B holds.", "source_adr": "ADR-0001",
                       "source_status": "Accepted"},
    "ADR-0002/other": {"rule": "Other rule in the domain.", "source_adr": "ADR-0002",
                       "source_status": "Accepted"},
    "ADR-0003/unrelated": {"rule": "Unrelated rule.", "source_adr": "ADR-0003",
                           "source_status": "Accepted"},
    "ADR-0009/own": {"rule": "Draft own rule.", "source_adr": "ADR-0009",
                     "source_status": "Accepted"},
}
TABLE = (
    "| handle | domain | rule | scope | provenance | source ADR |\n"
    "|---|---|---|---|---|---|\n"
    "| ADR-0001/old-a | zeta | Old rule A holds. | s | authored | ADR-0001 |\n"
    "| ADR-0001/old-b | zeta | Old rule B holds. | s | authored | ADR-0001 |\n"
    "| ADR-0002/other | dom-x | Other rule in the domain. | s | authored | ADR-0002 |\n"
    "| ADR-0003/unrelated | elsewhere | Unrelated rule. | s | authored | ADR-0003 |\n"
    "| ADR-0009/own | dom-x | Draft own rule. | s | authored | ADR-0009 |\n"
)


def draft(amends=(), supersedes=(), governs=True):
    lines = ["---", "id: ADR-0009", "title: Draft", "status: Proposed"]
    lines.append("amends: [%s]" % ", ".join(amends))
    lines.append("supersedes: [%s]" % ", ".join(supersedes))
    if governs:
        lines += ["governs:", "- handle: ADR-0009/own", "  rule: Draft own rule.",
                  "  domain: dom-x", "  scope: s", "  provenance: authored"]
    lines += ["---", "", "# Body", ""]
    return "\n".join(lines)


class Tree:
    def __init__(self, text, resolver=True):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".bionic.yml").write_text('config_version: "1"\ndocs_dir: tree\n')
        summ = self.root / "tree" / "adrs" / "summaries"
        summ.mkdir(parents=True)
        if resolver:
            (summ / "resolver.json").write_text(json.dumps(RESOLVER))
            (summ / "rule-table.md").write_text(TABLE)
        self.adr = self.root / "tree" / "adrs" / "ADR-0009-draft.md"
        self.adr.write_text(text)

    def run(self, *extra):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "rules", "--repo-root", str(self.root),
             "--adr", str(self.adr), *extra], capture_output=True, text=True)


class RulesTests(unittest.TestCase):
    def tree(self, *a, **k):
        t = Tree(*a, **k)
        self.addCleanup(t.tmp.cleanup)
        return t

    def test_amended_adr_rules_listed(self):
        p = self.tree(draft(amends=["ADR-0001"])).run()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("ADR-0001/old-a", p.stdout)
        self.assertIn("ADR-0001/old-b", p.stdout)
        self.assertIn("retain/narrow/retire", p.stdout)
        self.assertNotIn("ADR-0003/unrelated", p.stdout)

    def test_domain_rules_listed_and_own_handles_excluded(self):
        p = self.tree(draft()).run()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("ADR-0002/other", p.stdout)
        self.assertNotIn("ADR-0009/own", p.stdout)
        self.assertNotIn("ADR-0001/old-a", p.stdout)

    def test_supersedes_listed(self):
        p = self.tree(draft(supersedes=["ADR-0001"])).run("--json")
        self.assertEqual(p.returncode, 0, p.stderr)
        handles = [r["handle"] for r in json.loads(p.stdout)["rules"]]
        self.assertIn("ADR-0001/old-a", handles)

    def test_split_advisory_present_at_four_absent_at_one(self):
        four = self.tree(draft(amends=["ADR-0001", "ADR-0002"],
                               supersedes=["ADR-0003", "ADR-0004"])).run()
        self.assertEqual(four.returncode, 0, four.stderr)
        self.assertIn("more than three", four.stdout)
        one = self.tree(draft(amends=["ADR-0001"])).run()
        self.assertEqual(one.returncode, 0, one.stderr)
        self.assertNotIn("more than three", one.stdout)

    def test_exit_1_on_malformed_draft(self):
        p = self.tree("no frontmatter here\n").run()
        self.assertEqual(p.returncode, 1)
        self.assertIn("frontmatter", p.stderr)

    def test_exit_2_on_missing_resolver(self):
        p = self.tree(draft(amends=["ADR-0001"]), resolver=False).run()
        self.assertEqual(p.returncode, 2)
        self.assertIn("resolver", p.stderr)

    def test_exit_2_on_missing_tree(self):
        with tempfile.TemporaryDirectory() as d:
            adr = Path(d) / "ADR-0009-x.md"
            adr.write_text(draft())
            p = subprocess.run([sys.executable, str(SCRIPT), "rules", "--repo-root", d,
                                "--adr", str(adr)], capture_output=True, text=True)
            self.assertEqual(p.returncode, 2)
            self.assertIn("adr-precouncil:", p.stderr)

    def test_writes_nothing(self):
        t = self.tree(draft(amends=["ADR-0001"]))
        before = sorted(str(p) for p in t.root.rglob("*"))
        t.run()
        self.assertEqual(before, sorted(str(p) for p in t.root.rglob("*")))


if __name__ == "__main__":
    unittest.main()
