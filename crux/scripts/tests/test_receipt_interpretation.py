"""One receipt interpretation per inspect call, the summary's reusable set and the named declaration difference.

CYC-0134 and CYC-0136 saw the first summary inspect of a Verify attempt list "the receipt's declaration
differs from the registered declaration" for the checkout checks while the next full inspect listed
nothing. The cause: a commit landing while ``changelog_citation_tokens`` walks the history makes it refuse
``migration-history-head-changed``, and the registered declaration then loses its CHANGELOG.md projection.
The registry now rereads the tokens on that refusal, at most three reads in all.

Every seeded commit here lands through a deterministic hook on the walk's own head check, in a temporary
repository, never by timing and never in the checkout that runs the tests.
"""
import contextlib
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _council_gate_support as sup
from _classifier_isolation import isolate_classifier
from _evidence_fixtures import write_lock_project
import cycle_ops
from cycle_workflow import create, mutate, save, tree
import implementation_migration as migration
import suite_evidence
import test_evidence as te
import test_implementation_migration_shared_reads as shared

CORE = "checkout:unittest:crux/scripts/tests:test*.py"
CHANGELOG = "# Changelog\n\n## [3.10.0] — 2026-08-01\n\nrule:rotation\n"
DIFFERS = "declaration differs"


class SeededCommits:
    """Lands ``count`` empty commits in ``root``, one inside each history walk's head check, then stops.

    The hook wraps ``_InvocationHistory.unchanged_head``: the commit lands after the walk read HEAD and
    before the walk compares it, which is the race the registry rereads on. An empty commit leaves every
    tracked byte unchanged, so it moves no receipt fingerprint.
    """

    def __init__(self, root, count):
        self.root, self.left, self.landed = root, count, 0
        self.real = migration._InvocationHistory.unchanged_head

    def __enter__(self):
        hook = self

        def unchanged_head(history):
            if hook.left:
                hook.left -= 1
                hook.landed += 1
                sup.git(hook.root, "commit", "-q", "--allow-empty", "-m", f"seeded commit {hook.landed}")
            return hook.real(history)

        self.patcher = patch.object(migration._InvocationHistory, "unchanged_head", unchanged_head)
        self.patcher.start()
        return self

    def __exit__(self, *exc):
        self.patcher.stop()


class ChangelogTokenRaceTests(unittest.TestCase):
    """A temporary repository whose migration batch binds CHANGELOG.md, published, with a passing checkout receipt."""

    prepare = shared.CitationKinds.prepare

    def setUp(self):
        isolate_classifier(self)
        shared.CitationKinds.setUp(self)
        store = patch.dict(os.environ, {"CRUX_TEST_EVIDENCE_STORE": str(self.root.parent / "evidence")})
        store.start()
        self.addCleanup(store.stop)
        self.prepare(CHANGELOG)
        self.f.witness.write_text('{"synthetic": "discovery only"}\n')
        write_lock_project(self.root, empty=True)
        (self.root / ".python-version").write_text(f"{sys.version_info[0]}.{sys.version_info[1]}\n")
        (self.root / "crux/scripts/tests").mkdir(parents=True)
        (self.root / "crux/scripts/tests/parallel_suite.py").write_text("print('the fixture suite passes')\n")
        (self.root / "docs/objectives.md").write_text("Mission: useful changes.\n")
        if not (self.root / "docs/manifest.yml").exists():
            (self.root / "docs/manifest.yml").write_text('schema_version: "5"\nconcerns_enabled: [adrs]\n')
        sup.commit_all(self.root, "a published batch that binds CHANGELOG.md")
        self.declaration = suite_evidence.registered_declaration(self.root, CORE, dev_root=self.root)
        self.kind = self.declaration["input_projections"].get("CHANGELOG.md")
        self.assertTrue(self.kind, "the fixture's registered declaration projects CHANGELOG.md")
        executed = te.execute(self.root, self.declaration)
        self.assertEqual(executed["evidence"]["status"], "passed")
        self.receipt = executed["evidence"]["id"]

    def cycle(self):
        """A quick-fix cycle in Build whose Build check is the checkout suite, with the receipt attached."""
        doc = create(self.root, "quick-fix", "Answer", "Outcome", ["crux"], ["correct"], "builder", "tester")
        # This suite tests legacy reusable receipts, not new local observations.
        doc.pop("testing_policy"); doc.pop("local_checks")
        save(tree(self.root), doc)
        doc = mutate(self.root, doc["id"], "checks", checks=[CORE], phase="build")
        mutate(self.root, doc["id"], "evidence", check_id=CORE, evidence_id=self.receipt, use="executed")
        return doc["id"]

    def inspect(self, cid, summary):
        found = cycle_ops.inspect(self.root, cid, {"op": "inspect", "summary": summary})
        return cycle_ops.summarize(found) if summary else found

    def test_the_seeded_commit_alone_makes_the_strict_reader_refuse(self):
        # Positive control for the hook: the commit lands inside the walk and the reader refuses on it.
        with SeededCommits(self.root, 1) as seeded, self.assertRaises(migration.ap.Refused) as raised:
            migration.changelog_citation_tokens(self.root)
        self.assertEqual(raised.exception.code, "migration-history-head-changed")
        self.assertEqual(seeded.landed, 1)

    def test_one_head_change_keeps_the_projection(self):
        with SeededCommits(self.root, 1) as seeded:
            declared = suite_evidence.registered_declaration(self.root, CORE, dev_root=self.root)
        self.assertEqual(seeded.landed, 1)
        self.assertEqual(declared["input_projections"].get("CHANGELOG.md"), self.kind)
        self.assertEqual(te.normalize(declared), te.normalize(self.declaration))

    def test_three_head_changes_fall_back_to_the_whole_file(self):
        # The reread is bounded: a third head change keeps today's fallback.
        with SeededCommits(self.root, suite_evidence.CHANGELOG_TOKEN_READS) as seeded:
            declared = suite_evidence.registered_declaration(self.root, CORE, dev_root=self.root)
        self.assertEqual(seeded.landed, suite_evidence.CHANGELOG_TOKEN_READS)
        self.assertNotIn("CHANGELOG.md", declared["input_projections"])

    def test_another_refusal_is_not_reread(self):
        calls = []

        def refuse(root):
            calls.append(root)
            raise migration.ap.Refused("migration-config-not-committed")

        with patch.object(migration, "changelog_citation_tokens", refuse):
            self.assertEqual(suite_evidence._changelog_tokens(self.root), {})
        self.assertEqual(len(calls), 1)

    def test_summary_and_full_inspect_agree_while_a_commit_lands_during_the_token_read(self):
        cid = self.cycle()
        with SeededCommits(self.root, 1) as seeded:
            short = self.inspect(cid, summary=True)
        self.assertEqual(seeded.landed, 1, "the seeded commit landed during the summary inspect's token read")
        full = self.inspect(cid, summary=False)
        self.assertNotIn(DIFFERS, json.dumps(short["unmet"]))
        self.assertEqual(short["unmet"], full["unmet"])

    def test_three_commits_during_one_summary_inspect_reproduce_the_disagreement(self):
        # Positive control for the regression: past the reread's bound, the summary loses the projection and
        # names the difference, and a later full inspect with no seeded commit lists none.
        cid = self.cycle()
        with SeededCommits(self.root, suite_evidence.CHANGELOG_TOKEN_READS):
            short = self.inspect(cid, summary=True)
        full = self.inspect(cid, summary=False)
        self.assertIn(DIFFERS, json.dumps(short["unmet"]))
        self.assertIn("input_projections", json.dumps(short["unmet"]))
        self.assertNotIn(DIFFERS, json.dumps(full["unmet"]))


if __name__ == "__main__":
    unittest.main()
