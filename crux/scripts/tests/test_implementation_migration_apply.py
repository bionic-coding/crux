"""The historical-format migration application is retired: apply and dry-run refuse by name.

`implementation-migration.py apply` and `dry-run`, and the functions behind them, refuse every
call with `historical-migration-writes-retired` before any read, staging or write. The tests
drive the real functions and the real command lines, unstubbed, on a closed fixture, on a
published fixture and on a recovery batch. Each checks the exact line, the exit code and a
byte-identical tree (`.git` refs, index and objects included), then pairs the refusal with a
positive control: the production verifier admits the same fixture and `inventory` still reports.

The fixtures come from the production close code through `_historical_close_producer`.
"""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _historical_close_producer as producer
import _implementation_templates as templates
import implementation_migration as migration
import test_implementation_authority as fixtures
import test_implementation_migration_subject_eligibility as recovery_fixtures

CODE = "historical-migration-writes-retired"
STDOUT = '{"authority": "none", "limit": "historical-migration-writes-retired"}\n'
REMEDY = ("Propose clause migrations in the prospective format through migrate-adrs (adr-migration.py). "
          "Existing historical publications are still verified by every authority reader.")
REMEDY_LINE = json.dumps({"remedy": REMEDY}) + "\n"


class RetiredApplicationTests(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.home, True)

    def states(self):
        """A closed fixture, then a published one: each a private clone of the recorded close."""
        for published in (False, True):
            f = fixtures.closed(self)
            if published:
                f.publish()
            yield ("published" if published else "closed"), f

    def cli(self, f, command):
        return producer.script("implementation-migration.py", command, "--repo-root", str(f.root),
                               "--batch", f.f.rel, home=self.home)

    def assert_verified(self, f, *, published):
        """Positive control: the production verifier and the inventory report admit this fixture."""
        proof = producer.assert_close_admitted(f.root, f.f.run_path, slot=f.f.slot, batch_path=f.f.rel,
            batch_sha256=migration._digest(f.f.path.read_bytes()))
        self.assertEqual(proof.binding, f.proof.binding)
        if published:
            self.assertEqual(len(producer.assert_publication_admitted(f.root)["publications"]), 1)
        inventory = self.cli(f, "inventory")
        self.assertEqual(inventory.returncode, 0, inventory.stdout + inventory.stderr)
        self.assertEqual(json.loads(inventory.stdout)["approval"]["state"], "UNOBSERVED")

    def test_the_command_lines_refuse_by_name_and_leave_the_tree_byte_identical(self):
        for state, f in self.states():
            for command in ("apply", "dry-run"):
                with self.subTest(state=state, command=command):
                    before = producer.tree_bytes(f.root)
                    result = self.cli(f, command)
                    self.assertEqual(result.stdout, STDOUT)
                    self.assertEqual(result.stderr, REMEDY_LINE)
                    self.assertEqual(result.returncode, 1)
                    self.assertEqual(producer.tree_bytes(f.root), before)
            self.assert_verified(f, published=state == "published")

    def test_the_functions_refuse_as_their_first_statement(self):
        import implementation_migration_apply as application
        for state, f in self.states():
            for name, call in (("apply", application.apply), ("dry_run", application.dry_run),
                               ("migration.dry_run", migration.dry_run)):
                with self.subTest(state=state, call=name):
                    before = producer.tree_bytes(f.root)
                    with mock.patch.object(migration.cr, "git", wraps=migration.cr.git) as git, \
                            self.assertRaises(migration.Refused) as caught:
                        call(f.root, f.f.rel)
                    self.assertEqual(caught.exception.code, CODE)
                    self.assertEqual(caught.exception.remedy, REMEDY)
                    git.assert_not_called()  # No repository read precedes the refusal.
                    self.assertEqual(producer.tree_bytes(f.root), before)
            self.assert_verified(f, published=state == "published")

    def test_a_published_witness_is_never_rewritten_by_either_command(self):
        for state, f in self.states():
            if state != "published":
                continue
            raw = f.witness.read_bytes()
            for command in ("apply", "dry-run"):
                self.cli(f, command)
            self.assertEqual(f.witness.read_bytes(), raw)

    def test_a_recovery_batch_is_refused_by_both_commands_and_both_functions(self):
        import implementation_migration_apply as application
        f = templates.clone(self, ("recovery-subject", False),
                            lambda: recovery_fixtures.build_recovery_subject(False))
        rel = f.successor_path.relative_to(f.root).as_posix()
        self.assertIsNotNone(f.successor_batch.get("recovery_from"))
        for command in ("apply", "dry-run"):
            with self.subTest(command=command):
                before = producer.tree_bytes(f.root)
                result = producer.script("implementation-migration.py", command, "--repo-root", str(f.root),
                                         "--batch", rel, home=self.home)
                self.assertEqual((result.stdout, result.stderr, result.returncode), (STDOUT, REMEDY_LINE, 1))
                self.assertEqual(producer.tree_bytes(f.root), before)
        for name, call in (("apply", application.apply), ("dry_run", application.dry_run)):
            with self.subTest(call=name), self.assertRaises(migration.Refused) as caught:
                call(f.root, rel)
            self.assertEqual(caught.exception.code, CODE)
        # Positive control: the parent close and its publication are still verified.
        proof = producer.assert_close_admitted(f.root, f.f.run_path, slot=f.f.slot, batch_path=f.f.rel,
            batch_sha256=migration._digest(f.f.path.read_bytes()))
        self.assertEqual(proof.binding, f.proof.binding)
        self.assertEqual([row["path"] for row in migration._discover_publications(f.root)], [f.parent["path"]])

    def test_the_module_keeps_only_the_two_refusing_functions(self):
        import implementation_migration_apply as application
        public = {name for name, value in vars(application).items()
                  if callable(value) and getattr(value, "__module__", None) == application.__name__
                  and not name.startswith("_")}
        self.assertEqual(public, {"apply", "dry_run"})
        self.assertFalse([name for name in vars(application) if name in (
            "_Snapshot", "_refresh", "_publish_witness", "_prepare_application", "_apply", "_driver")])


if __name__ == "__main__":
    unittest.main()
