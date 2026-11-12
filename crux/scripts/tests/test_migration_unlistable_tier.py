"""The migration readers refuse an ADR archive tier they cannot list.

THE CONTRACT. Four migration readers list both ADR tiers through
`adr_frontmatter.adr_paths`: `implementation_migration._resolved_clause`,
`implementation_migration._architecture_index`,
`implementation_migration._raw_architecture` and
`migration_disposition._raw_records`. An archive tier that exists and cannot be
listed raises the `PermissionError` naming the tier, never an empty tier.

Two command-line entry points are driven end to end:

- `signoff-reconciliation.py --migration-disposition` and
  `signoff-backfill.py --migration-disposition` reach `_resolved_clause` first.
  Their handler exits 2 and names the tier on stderr, with nothing on stdout.
- `implementation-migration.py inventory --batch` reaches `_resolved_clause` and
  then `_architecture_index`. Its handler exits 2 and writes only the limit
  `migration-inventory-unavailable` on stderr. That handler prints no exception
  text, so this test cannot pin the tier's path there; changing the handler is
  outside the cycle that added this test, and the limit is stated here.

`_raw_architecture` and `_raw_records` are reached through a command only after
`_resolved_clause` has already refused, so each is driven directly and its raise
is pinned to the tier's path.

Every refusal runs on the fixture its positive control just passed on, the
fixture's bytes are unchanged after it, and every test skips when the effective
uid is 0, because root lists a mode-000 directory.

Run:
  uv run python3 -m unittest discover -s crux/scripts/tests -p 'test_migration_unlistable_tier.py'
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
SCRIPTS = TESTS.parent
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(TESTS))

import bionic_config  # noqa: E402
import implementation_migration as im  # noqa: E402
import migration_disposition as md  # noqa: E402

UNAVAILABLE = {"authority": "none", "limit": "migration-inventory-unavailable"}


class MigrationUnlistableArchiveTestCase(unittest.TestCase):
    """The synthetic disposition fixture, with an empty archive tier beside the active one."""

    def setUp(self) -> None:
        # Composed, not inherited, so the fixture's own tests do not run here.
        from test_implementation_migration_disposition import Producers
        self.f = Producers()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.root = self.f.root
        self.archive = self.f.adrs / "archive"
        self.archive.mkdir()

    def lock_archive(self) -> None:
        if os.geteuid() == 0:
            self.skipTest("running as root: a mode-000 directory is still listable")
        self.archive.chmod(0o000)
        self.addCleanup(self.archive.chmod, 0o755)

    def unlock_archive(self) -> None:
        self.archive.chmod(0o755)

    def inventory(self) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "implementation-migration.py"), "inventory",
             "--batch", str(self.f.batch_path), "--repo-root", str(self.root)],
            capture_output=True, text=True, timeout=120)


class DispositionCommandTests(MigrationUnlistableArchiveTestCase):
    def test_disposition_commands_exit_two_naming_an_unlistable_archive_tier(self):
        for kind in ("doctrine", "backfill"):
            with self.subTest(kind=kind):
                # POSITIVE CONTROL: the archive readable, the dry run renders a proposal.
                r = self.f.command(kind, human=False, dry=True)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertEqual(json.loads(r.stdout)["state"], "human-input-required")
                before = self.f.snapshot()

                self.lock_archive()
                r = self.f.command(kind, human=False, dry=True)
                ctx = f"{kind}: rc={r.returncode} out={r.stdout!r} err={r.stderr!r}"
                self.assertEqual(r.returncode, 2, ctx)
                self.assertEqual(r.stdout, "", ctx)
                self.assertIn("migration-disposition: PermissionError", r.stderr, ctx)
                self.assertIn(str(self.archive), r.stderr, ctx)
                self.assertNotIn("Traceback", r.stderr, ctx)
                self.unlock_archive()
                self.assertEqual(self.f.snapshot(), before, f"a file changed — {ctx}")


class InventoryCommandTests(MigrationUnlistableArchiveTestCase):
    def test_inventory_exits_two_with_its_limit_on_an_unlistable_archive_tier(self):
        # POSITIVE CONTROL: the archive readable, inventory lists both tiers and
        # resolves the architecture index, then stops at a later refusal of this
        # fixture (its citation scope), on stdout with exit 1 — never exit 2.
        r = self.inventory()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        control = json.loads(r.stdout)
        self.assertEqual(control["authority"], "none")
        self.assertNotEqual(control["limit"], UNAVAILABLE["limit"])
        before = self.f.snapshot()

        self.lock_archive()
        r = self.inventory()
        ctx = f"rc={r.returncode} out={r.stdout!r} err={r.stderr!r}"
        self.assertEqual(r.returncode, 2, ctx)
        self.assertEqual(r.stdout, "", ctx)
        self.assertEqual(json.loads(r.stderr), UNAVAILABLE, ctx)
        self.unlock_archive()
        self.assertEqual(self.f.snapshot(), before, f"a file changed — {ctx}")


class MigrationReaderTests(MigrationUnlistableArchiveTestCase):
    """Each listing site raises the error that names the tier."""

    def readers(self):
        return (
            ("implementation_migration._resolved_clause",
             lambda: im.resolve_clause(self.root, self.f.entry)),
            ("implementation_migration._architecture_index",
             lambda: im._architecture_index(self.root)),
            ("implementation_migration._raw_architecture",
             lambda: im._raw_architecture(self.root)),
            ("migration_disposition._raw_records",
             lambda: md._raw_records(self.root, bionic_config.load_config(self.root))),
        )

    def test_each_migration_reader_raises_naming_an_unlistable_archive_tier(self):
        for name, read in self.readers():
            with self.subTest(reader=name):
                # POSITIVE CONTROL: the archive readable, the reader returns.
                self.unlock_archive()
                self.assertIsNotNone(read())
                self.lock_archive()
                with self.assertRaises(PermissionError) as cm:
                    read()
                self.assertEqual(cm.exception.filename, str(self.archive))
        self.unlock_archive()


if __name__ == "__main__":
    unittest.main()
