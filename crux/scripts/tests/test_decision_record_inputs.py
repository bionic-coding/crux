"""Decision records are inputs of the cycle's governs checks and not of the main run.

The registered checkout declarations leave the decision records out of their inputs, so a
decision-only commit reuses the main run's receipt. Every other check keeps them: the drift-gates
preset, the two governs presets, and the tests' live copy. The partition test pins the whole docs
directory: each top-level entry is excluded as bookkeeping, excluded as a decision record, or kept.
"""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _evidence_fixtures import write_lock_project
from _dev_surface import REPO_ROOT, require_dev_surface
import suite_evidence
import test_evidence as te

CORE = "checkout:unittest:crux/scripts/tests:test*.py"
TOOLS = "checkout:unittest:tools/tests:test*.py"
RECORDS = ("adrs", "arch", "observations", "research", "briefs", "index.md", "manifest.yml", "objectives.md")
KEPT = ("AGENTS.md", "invariants", "code", "promptbooks")
SCRIPTS = Path(__file__).resolve().parents[1]


class RegisteredDeclarationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        write_lock_project(self.root)
        (self.root / ".python-version").write_text("3.13\n")

    def test_the_decision_records_are_the_named_tuple(self):
        self.assertEqual(suite_evidence.DECISION_RECORDS, RECORDS)
        self.assertEqual(set(suite_evidence.DECISION_RECORDS) & set(suite_evidence.DOCS_EXCLUSIONS), set())

    def test_the_registered_checkout_declarations_exclude_the_decision_records(self):
        declared = suite_evidence.registered_declarations(self.root, dev_root=self.root)
        for check in (CORE, TOOLS):
            excluded = declared[check]["exclude_inputs"]
            for name in RECORDS:
                self.assertIn("docs/" + name, excluded, (check, name))
            for name in KEPT:
                self.assertNotIn("docs/" + name, excluded, (check, name))

    def test_a_decision_only_change_leaves_the_registered_snapshot_alone(self):
        def vcs(*args):
            subprocess.run(["git", "-c", "user.name=T", "-c", "user.email=t@example.invalid", *args],
                           cwd=self.root, capture_output=True, check=True)
        for rel in ("bionic/adrs/ADR-0001-x.md", "bionic/briefs/b.md", "bionic/manifest.yml", "bionic/AGENTS.md", "crux/a.py"):
            (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.root / rel).write_text("one\n")
        vcs("init", "-q")
        vcs("add", "-A")
        vcs("commit", "-qm", "base")

        def fingerprint():
            declaration = suite_evidence.registered_declaration(self.root, CORE, dev_root=self.root)
            return te.snapshot(self.root, declaration, source_root=self.root)["fingerprint"]
        before = fingerprint()
        for rel in ("bionic/adrs/ADR-0001-x.md", "bionic/briefs/b.md", "bionic/manifest.yml"):
            (self.root / rel).write_text("two\n")
        self.assertEqual(fingerprint(), before)
        (self.root / "bionic/AGENTS.md").write_text("two\n")
        self.assertNotEqual(fingerprint(), before)

    def test_the_staged_checks_and_unregistered_runs_keep_the_decision_records(self):
        declared = suite_evidence.registered_declarations(self.root, dev_root=self.root)
        for check, declaration in declared.items():
            if check.startswith("staged:"):
                self.assertFalse([e for e in declaration["exclude_inputs"] if e.startswith("docs/")], check)
        focused, registered = suite_evidence.declaration_for("checkout", "crux/scripts/tests", "test_one.py", None, self.root)
        self.assertFalse(registered)
        self.assertEqual(focused["exclude_inputs"], suite_evidence.runtime_exclusions(self.root))


class PresetsAndLiveCopyKeepTheRecordsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / "tools").mkdir()
        (self.root / "crux/scripts").mkdir(parents=True)
        for script in ("tools/run-drift-gates.py", "crux/scripts/lint-governs-references.py",
                       "crux/scripts/check-governs-coverage.py"):
            (self.root / script).write_text("")

    def test_the_two_governs_presets_exist_and_name_their_scripts(self):
        presets = suite_evidence.PRESETS
        self.assertEqual(presets["governs-references"]["command"], ["python", "crux/scripts/lint-governs-references.py"])
        self.assertEqual(presets["governs-references"]["script"], "crux/scripts/lint-governs-references.py")
        self.assertEqual(presets["governs-coverage"]["command"], ["python", "crux/scripts/check-governs-coverage.py"])
        self.assertEqual(presets["governs-coverage"]["script"], "crux/scripts/check-governs-coverage.py")

    def test_every_preset_that_reads_the_records_keeps_them_as_inputs(self):
        for preset in ("drift-gates", "governs-references", "governs-coverage"):
            declaration = suite_evidence.preset_declaration(self.root, preset, "cycle:" + preset)
            self.assertEqual(declaration["inputs"], suite_evidence.INPUTS, preset)
            expected = (suite_evidence.drift_gates_exclusions(self.root) if preset == "drift-gates"
                        else suite_evidence.runtime_exclusions(self.root))
            self.assertEqual(declaration["exclude_inputs"], expected, preset)
            for name in RECORDS:
                self.assertNotIn("docs/" + name, declaration["exclude_inputs"], (preset, name))

    def test_a_governs_preset_refuses_where_its_script_is_absent(self):
        (self.root / "crux/scripts/check-governs-coverage.py").unlink()
        with self.assertRaises(te.EvidenceError):
            suite_evidence.preset_declaration(self.root, "governs-coverage", "c")

    def test_the_live_copy_keeps_the_decision_records(self):
        import _live_copy
        self.assertEqual(set(_live_copy.BOOKKEEPING) & set(RECORDS), set())
        docs = REPO_ROOT / "bionic"
        self.assertEqual(_live_copy.omitted(REPO_ROOT, str(docs), list(RECORDS)), set())


class PartitionTests(unittest.TestCase):
    def test_every_top_level_docs_entry_belongs_to_exactly_one_group(self):
        require_dev_surface(self, REPO_ROOT / "bionic/manifest.yml", "bionic/manifest.yml")
        listed = subprocess.run(["git", "ls-files", "bionic"], cwd=REPO_ROOT, capture_output=True, text=True, check=True).stdout
        names = {line.split("/")[1] for line in listed.splitlines() if "/" in line}
        groups = {"bookkeeping": set(suite_evidence.DOCS_EXCLUSIONS), "records": set(suite_evidence.DECISION_RECORDS), "kept": set(KEPT)}
        for name in sorted(names):
            homes = [group for group, members in groups.items() if name in members]
            self.assertEqual(len(homes), 1, (name, homes))
        stale = {group: sorted(members - names) for group, members in groups.items() if group != "bookkeeping"}
        self.assertEqual(stale, {"records": [], "kept": []})


class GovernsPresetsRunTests(unittest.TestCase):
    """The presets' scripts turn red on a seeded violation (run in a temporary tree, never the live one)."""

    ADR = """---
id: ADR-{number}
title: "Fixture"
status: Accepted
date: 2026-09-17
proposed_date: 2026-09-17
accepted_date: 2026-09-17
deprecated_date: null
superseded_date: null
supersedes: []
superseded_by: null
deciders: [fixture]
tags: [fixture]
related_briefs: []
related_research: []
{governs}---

# ADR-{number}
"""
    GOVERNS = ('governs:\n  - domain: fixture\n    rule: "A fixture rule."\n    scope: "the fixture"\n'
               '    handle: ADR-0001/fixture-rule\n    provenance: authored\n')

    def tree(self, adr_governs="governs: []\n", research=""):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name).resolve()
        (root / ".bionic.yml").write_text('config_version: "1"\ndocs_dir: tree\n')
        for sub in ("adrs", "research", "observations"):
            (root / "tree" / sub).mkdir(parents=True)
        (root / "tree/manifest.yml").write_text(
            'schema_version: "5"\nconcerns_enabled: [adrs, research, observations]\nadr:\n  next_number: 2\n  governs_from: 1\n'
            '  governs_rule_baseline: []\n')
        (root / "tree/adrs/ADR-0001-fixture.md").write_text(self.ADR.format(number="0001", governs=adr_governs))
        (root / "crux").mkdir()
        (root / "tree/research/note.md").write_text(research or "A note.\n")
        return root

    def run_script(self, root, script):
        done = subprocess.run([sys.executable, str(SCRIPTS / script), "--repo-root", str(root)], capture_output=True, text=True, cwd=root)
        return done.returncode, done.stdout, done.stderr

    def test_a_broken_rule_citation_turns_governs_references_red(self):
        clean = self.tree(self.GOVERNS, "Cites rule:fixture-rule here.\n")
        code, out, err = self.run_script(clean, "lint-governs-references.py")
        self.assertEqual(code, 0, (out[-400:], err[-400:]))
        broken = self.tree(self.GOVERNS, "Cites rule:no-such-rule-exists here.\n")
        code, out, err = self.run_script(broken, "lint-governs-references.py")
        self.assertEqual(code, 1, (out[-400:], err[-400:]))
        self.assertIn("no-such-rule-exists", out)

    def test_an_uncovered_adr_turns_governs_coverage_red(self):
        covered = self.tree(self.GOVERNS)
        code, out, err = self.run_script(covered, "check-governs-coverage.py")
        self.assertEqual(code, 0, (out[-400:], err[-400:]))
        uncovered = self.tree("governs: []\n")
        code, out, err = self.run_script(uncovered, "check-governs-coverage.py")
        self.assertEqual(code, 1, (out[-400:], err[-400:]))
        self.assertTrue(json.loads(out.splitlines()[-1])["uncovered"])


if __name__ == "__main__":
    unittest.main()
