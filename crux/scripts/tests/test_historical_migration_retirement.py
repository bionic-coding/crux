"""`--migration-batch` is retired on advance-run and run-council; every reader still verifies.

`advance-run.py --migration-batch` (E4) refuses before it loads or writes the run, and
`run-council.py --migration-batch` (E3) refuses before the batch is loaded, before preflight and
before any attempt is claimed. Both are driven unstubbed as child processes on a closed fixture,
a published fixture, a run at a council prompt and a recovery batch. Each test checks the exact
line, the exit code and a byte-identical tree (`.git` refs, index and objects included), then
pairs the refusal with a positive control: the production verifier admits the same fixture.

`implementation-migration.py apply` and `dry-run` (E1, E2) are covered in
test_implementation_migration_apply. The in-process E3 case with a synthetic gateway lives in
test_implementation_council_transport.

The fixtures come from the production close code through `_historical_close_producer`.
"""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import _council_gate_support as sup
import _historical_close_producer as producer
import _implementation_templates as templates
import implementation_migration as migration
import test_implementation_authority as fixtures
import test_implementation_migration_subject_eligibility as recovery_fixtures

CODE = "historical-migration-writes-retired"
ADVANCE_LINE = json.dumps({"error": CODE + "; nothing was written"}) + "\n"
COUNCIL_LINE = "run-council: the selected migration batch was refused: " + CODE + "\n"


def question_for(rel, path):
    """A question the runner would admit for this exact batch: its path, digest and dimensions."""
    return ("Assess %s SHA256 %s, Completeness, Correctness, Consistency, Clarity, Security and "
            "architectural conflict.\n" % (rel, migration._digest(Path(path).read_bytes())))


class _Surface:
    """What a closed and a published fixture share. A subclass supplies `published`."""
    published = False

    def setUp(self):
        self.home = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.home, True)
        self.f = fixtures.closed(self)  # A private clone of what the production close code recorded.
        if self.published:
            self.f.publish()
        self.root = self.f.root
        self.rel = self.f.f.rel

    def assert_still_verified(self):
        """Positive control: the production verifier admits the very fixture that was refused."""
        proof = producer.assert_close_admitted(self.root, self.f.f.run_path, slot=self.f.f.slot,
            batch_path=self.rel, batch_sha256=migration._digest(self.f.f.path.read_bytes()))
        self.assertEqual(proof.binding, self.f.proof.binding)
        if self.published:
            self.assertEqual(len(producer.assert_publication_admitted(self.root)["publications"]), 1)
        inventory = producer.script("implementation-migration.py", "inventory", "--repo-root", str(self.root),
                                    "--batch", self.rel, home=self.home)
        self.assertEqual(inventory.returncode, 0, inventory.stdout + inventory.stderr)

    def advance(self, *selector, run=None):
        return producer.script("advance-run.py", str(run or self.f.f.run_path), "--outcome", "done",
                               "--artifacts", self.f.f.artifacts, "--book", str(self.f.f.book_path),
                               *selector, home=self.home)

    def test_advance_run_selector_refuses_before_the_run_is_loaded(self):
        before = producer.tree_bytes(self.root)
        result = self.advance("--migration-batch", self.rel)
        self.assertEqual(result.stdout, ADVANCE_LINE)
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(producer.tree_bytes(self.root), before)
        self.assert_still_verified()

    def test_advance_run_selector_refuses_a_run_it_could_not_read_the_same_way(self):
        # The refusal precedes loading the run: a path that names no run gets the same line.
        before = producer.tree_bytes(self.root)
        result = self.advance("--migration-batch", self.rel, run=self.root / "no-such-run.yaml")
        self.assertEqual((result.stdout, result.stderr, result.returncode), (ADVANCE_LINE, "", 1))
        self.assertEqual(producer.tree_bytes(self.root), before)

    def test_advance_run_without_the_selector_still_validates_the_recorded_binding(self):
        # Sibling control: the command without the selector is unchanged. It validates the close
        # recorded in the run through the unchanged reader, then advances the next prompt.
        import yaml
        recorded = yaml.safe_load(self.f.f.run_path.read_bytes())["migration_bindings"]
        self.assertEqual(len(recorded), 1)
        result = self.advance()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn(CODE, result.stdout + result.stderr)
        run = yaml.safe_load(self.f.f.run_path.read_bytes())
        self.assertEqual(run["migration_bindings"], recorded)
        self.assertEqual(json.loads(result.stdout)["current_prompt"], self.f.f.close + 2)

    def test_advance_run_implementation_revision_on_a_migration_slot_keeps_its_own_refusal(self):
        before = producer.tree_bytes(self.root)
        result = self.advance("--implementation-revision", self.rel)
        self.assertNotIn(CODE, result.stdout + result.stderr)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(producer.tree_bytes(self.root), before)


class ClosedFixture(_Surface, unittest.TestCase):
    """A close recorded in the run and committed, with no publication."""
    published = False


class PublishedFixture(_Surface, unittest.TestCase):
    """A close and its committed publication."""
    published = True


class SelectorFixture(unittest.TestCase):
    """`run-council.py --migration-batch` on a run at a council prompt, as a child process.

    A closed or published run has no council prompt left, so this fixture is the run before its
    close: the selector is refused before any council call, attempt or record, and the same
    fixture is then closed by the production close code and admitted by the verifier."""

    def setUp(self):
        self.home = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.home, True)
        self.f = fixtures.PublicationProof("runTest")
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.root = self.f.root
        self.rel = self.f.f.rel
        self.question = self.root / "retirement-question.md"
        self.question.write_text(question_for(self.rel, self.f.f.path))
        sup.commit_all(self.root, "synthetic retirement question")

    def run_council(self, *selector):
        return producer.script("run-council.py", str(self.f.f.run_path), "--round", "2",
                               "--question", str(self.question), "--subject", str(self.f.f.path),
                               "--retain-subjects", "--book", str(self.f.f.book_path), *selector,
                               home=self.home)

    def test_the_selector_is_refused_before_any_attempt_record_or_provider_request(self):
        before = producer.tree_bytes(self.root)
        result = self.run_council("--migration-batch", self.rel)
        self.assertEqual(result.stderr, COUNCIL_LINE)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(producer.tree_bytes(self.root), before)
        self.assertFalse(list(self.f.f.run_path.parent.glob("council/*.attempt.json")))
        # Positive control: the production close code records this same batch; the verifier admits it.
        self.f.close(fresh=True)
        self.assertEqual(self.f.proof.binding["batch"]["path"], self.rel)

    def test_without_the_selector_the_runner_keeps_its_own_refusal(self):
        before = producer.tree_bytes(self.root)
        result = self.run_council()
        self.assertNotIn(CODE, result.stdout + result.stderr)
        self.assertEqual(result.returncode, 2)
        self.assertIn("requires its declared subject selector", result.stderr)
        self.assertEqual(producer.tree_bytes(self.root), before)


class RecoveryBatch(unittest.TestCase):
    """A recovery batch (`recovery_from`) has no entry point of its own: E3 and E4 refuse it."""

    def setUp(self):
        self.home = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.home, True)
        self.f = templates.clone(self, ("recovery-subject", False),
                                 lambda: recovery_fixtures.build_recovery_subject(False))
        self.root = self.f.root
        self.path = self.f.successor_path
        self.rel = self.path.relative_to(self.root).as_posix()
        self.assertIsNotNone(self.f.successor_batch.get("recovery_from"))

    def assert_parent_verified(self):
        """Positive control: the parent close and its publication are still admitted."""
        proof = producer.assert_close_admitted(self.root, self.f.f.run_path, slot=self.f.f.slot,
            batch_path=self.f.f.rel, batch_sha256=migration._digest(self.f.f.path.read_bytes()))
        self.assertEqual(proof.binding, self.f.proof.binding)
        self.assertEqual([row["path"] for row in migration._discover_publications(self.root)],
                         [self.f.parent["path"]])

    def test_advance_run_refuses_a_recovery_batch(self):
        before = producer.tree_bytes(self.root)
        result = producer.script("advance-run.py", str(self.f.stopped["run_path"]), "--outcome", "done",
                                 "--artifacts", self.f.stopped["receipt"], "--book",
                                 str(self.f.stopped["book_path"]), "--migration-batch", self.rel,
                                 home=self.home)
        self.assertEqual((result.stdout, result.stderr, result.returncode), (ADVANCE_LINE, "", 1))
        self.assertEqual(producer.tree_bytes(self.root), before)
        self.assert_parent_verified()

    def test_run_council_refuses_a_recovery_batch(self):
        question = self.root / "recovery-question.md"
        question.write_text(question_for(self.rel, self.path))
        sup.commit_all(self.root, "synthetic recovery question")
        advanced = producer.script("advance-run.py", str(self.f.stopped["run_path"]), "--outcome", "done",
                                   "--artifacts", self.f.stopped["receipt"], "--book",
                                   str(self.f.stopped["book_path"]), home=self.home)
        self.assertEqual(advanced.returncode, 0, advanced.stdout + advanced.stderr)
        sup.commit_all(self.root, "synthetic recovery run at its council prompt")
        before = producer.tree_bytes(self.root)
        result = producer.script("run-council.py", str(self.f.stopped["run_path"]), "--prompt", "2",
                                 "--round", "2", "--question", str(question), "--subject", str(self.path),
                                 "--retain-subjects", "--book", str(self.f.stopped["book_path"]),
                                 "--migration-batch", self.rel, home=self.home)
        self.assertEqual((result.stdout, result.stderr, result.returncode), ("", COUNCIL_LINE, 2))
        self.assertEqual(producer.tree_bytes(self.root), before)
        self.assert_parent_verified()


if __name__ == "__main__":
    unittest.main()
