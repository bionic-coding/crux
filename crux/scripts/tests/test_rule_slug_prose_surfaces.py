"""The prose, schema and template-twin consumers of the rule:<slug> citation form.

Two surfaces:

  1. the parity-manifest clause that binds the §9 code-citation addendum of
     the tree's operational schema to its shipped template twin;
  2. every `§N` cross-reference in the shipped twin resolves to a heading the
     twin has.

Every expectation is derived from disk. The dev-only surface (the tree's
AGENTS.md) is guarded with
`require_dev_surface` so the file is inert against the staged sync artifact;
the twin and the parity manifest ship and are read unguarded.
"""

from __future__ import annotations

import importlib
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = REPO_ROOT / "crux" / "scripts"

try:  # package-relative when run as a module, flat when run by discovery
    from ._dev_surface import TREE, TREE_AGENTS_MD, require_dev_surface
except ImportError:  # pragma: no cover
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _dev_surface import TREE, TREE_AGENTS_MD, require_dev_surface

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

TWIN = REPO_ROOT / "crux" / "templates" / "AGENTS.md.tmpl"
PARITY_MANIFEST = SCRIPTS / "template_parity_manifest.json"

PARITY_CLAUSE_ID = "rule-citation-form"


def _headings(text: str) -> set[str]:
    """Numbered headings at any depth: `## 11.D. Title` and `### 14.1 Title` alike."""
    return set(re.findall(r"^#{2,4} ([0-9]+(?:\.[A-Z0-9]+)*)\.? ", text, re.MULTILINE))


def _section_refs(text: str) -> list[str]:
    return [r.rstrip(".") for r in re.findall(r"§([0-9]+(?:\.[A-Z0-9]+)*)", text)]


class TwinSectionReferencesTests(unittest.TestCase):
    """Task 5 — a `§N` in the shipped twin names a section the twin has."""

    def test_helper_catches_a_dangling_reference(self) -> None:
        text = "## 3. Layout\n\n### 3.1 Sub\n\nSee §16's rules, §3 and §3.1.\n"
        self.assertEqual(sorted(set(_section_refs(text)) - _headings(text)), ["16"])

    def test_every_section_reference_in_the_twin_resolves(self) -> None:
        text = TWIN.read_text(encoding="utf-8")
        refs, heads = _section_refs(text), _headings(text)
        self.assertTrue(refs, "the twin carries no § cross-references at all")
        self.assertEqual(sorted(set(refs) - heads), [])


class ParityManifestClauseTests(unittest.TestCase):
    """Task 6 — one clause binds the §9 addendum across the twin pair."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.clauses = json.loads(PARITY_MANIFEST.read_text(encoding="utf-8"))["clauses"]
        cls.ctp = importlib.import_module("check_template_parity")

    def _clause(self, cid: str) -> dict:
        for c in self.clauses:
            if c.get("id") == cid:
                return c
        self.fail(f"no clause {cid!r} in {PARITY_MANIFEST}")

    def test_clause_mirrors_the_sibling_section_nine_clause(self) -> None:
        sibling = self._clause("wikilink-promptbook-lifecycle-neutral")
        clause = self._clause(PARITY_CLAUSE_ID)
        self.assertEqual(clause["canonical"], sibling["canonical"])
        self.assertEqual(clause["twin"], sibling["twin"])
        self.assertIn("Slug, date, and wiki-link rules", clause["anchor"])
        self.assertIn("pattern", clause)

    def test_clause_is_live_and_in_parity_against_the_real_repo(self) -> None:
        require_dev_surface(self, TREE_AGENTS_MD, f"{TREE}/AGENTS.md")
        results = {r["id"]: r for r in self.ctp.check_parity(PARITY_MANIFEST, REPO_ROOT)}
        self.assertIn(PARITY_CLAUSE_ID, results)
        self.assertEqual(results[PARITY_CLAUSE_ID]["status"], "OK", results[PARITY_CLAUSE_ID])

    def test_clause_reports_drift_when_the_twin_addendum_changes(self) -> None:
        require_dev_surface(self, TREE_AGENTS_MD, f"{TREE}/AGENTS.md")
        clause = self._clause(PARITY_CLAUSE_ID)
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for rel in (clause["canonical"], clause["twin"]):
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(REPO_ROOT / rel, root / rel)
            twin = root / clause["twin"]
            text = twin.read_text(encoding="utf-8")
            self.assertIn("`rule:<slug>`", text)
            twin.write_text(text.replace("`rule:<slug>`", "`rule:<slgu>`", 1), encoding="utf-8")
            results = {r["id"]: r for r in self.ctp.check_parity(PARITY_MANIFEST, root)}
            self.assertEqual(results[PARITY_CLAUSE_ID]["status"], "DRIFT", results[PARITY_CLAUSE_ID])


if __name__ == "__main__":
    unittest.main()
