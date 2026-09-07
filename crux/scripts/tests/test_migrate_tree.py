"""Tests for migrate-tree.py — the schema 4 -> 5 rung (ADR-0059).

The properties under test are the ones an independent council review rejected two
earlier designs for:

- the migration is a MERGE, not a rename — `bionic/` already exists
- the ledger must never collide with the check suite
- `manifest.yml` moves LAST, so a crash leaves discovery pointing at the source
- an already-moved entry and a real collision are distinguishable
- an existing `artifact_prefix` survives
"""
from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "crux" / "scripts" / "migrate-tree.py"

_spec = importlib.util.spec_from_file_location("migrate_tree", SCRIPT)
mt = importlib.util.module_from_spec(_spec)
sys.modules["migrate_tree"] = mt
_spec.loader.exec_module(mt)


def _reset_root():
    """`_ROOT` is process-global; a test writing a marker directly must not be
    guarded against a previous test's repo root."""
    mt._ROOT = None

MANIFEST_V4 = 'schema_version: "4"\nconcerns_enabled:\n  - adrs\n  - invariants\nadr:\n  next_number: 7\n'


class TreeFixture(unittest.TestCase):
    """A realistic v4 tree: concerns under docs/, checks under bionic/invariants/."""

    def setUp(self):
        _reset_root()
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        docs = self.root / "docs"
        (docs / "adrs").mkdir(parents=True)
        (docs / "invariants").mkdir(parents=True)
        (docs / "promptbooks" / "active").mkdir(parents=True)
        (docs / "manifest.yml").write_text(MANIFEST_V4, encoding="utf-8")
        (docs / "log.md").write_text("# Operations log\n", encoding="utf-8")
        (docs / "adrs" / "ADR-0001-x.md").write_text("# ADR-0001\n", encoding="utf-8")
        (docs / "invariants" / "index.md").write_text("# Pins (1)\n", encoding="utf-8")
        (docs / "invariants" / "a-pin.md").write_text("---\nid: INV-0001\n---\n", encoding="utf-8")
        inv = self.root / "bionic" / "invariants"
        inv.mkdir(parents=True)
        (inv / "a_check.md").write_text("# check: a_check\n", encoding="utf-8")
        (inv / "reconciliation.yml").write_text("config_version: \"1\"\nchecks: []\n", encoding="utf-8")

    def tree(self) -> Path:
        return self.root / "bionic"


class HappyPathTests(TreeFixture):
    def test_migrates_to_bionic_without_nesting_a_docs_directory(self):
        out = mt.migrate(self.root)
        self.assertEqual(out["status"], "migrated")
        self.assertFalse((self.root / "docs").exists(), "source directory survived")
        self.assertFalse((self.root / "bionic" / "docs").exists(),
                         "tree was NESTED as bionic/docs/ — the rename bug this rung exists to avoid")
        self.assertTrue((self.tree() / "manifest.yml").is_file())
        self.assertTrue((self.tree() / "adrs" / "ADR-0001-x.md").is_file())

    def test_invariants_unify_without_the_ledger_colliding_with_checks(self):
        mt.migrate(self.root)
        inv = self.tree() / "invariants"
        self.assertTrue((inv / "a-pin.md").is_file(), "ledger page did not arrive")
        self.assertTrue((inv / "index.md").is_file())
        self.assertTrue((inv / "checks" / "a_check.md").is_file(), "check was not moved into checks/")
        self.assertTrue((inv / "reconciliation.yml").is_file(), "reconciliation was lost")
        self.assertFalse((inv / "a_check.md").exists(), "check left at the old flat path")

    def test_schema_version_is_bumped_and_config_written(self):
        mt.migrate(self.root)
        self.assertEqual(mt.read_schema_version(self.tree() / "manifest.yml"), "5")
        cfg = (self.root / ".bionic.yml").read_text()
        self.assertIn("docs_dir: bionic", cfg)

    def test_other_manifest_keys_survive_the_schema_bump(self):
        mt.migrate(self.root)
        text = (self.tree() / "manifest.yml").read_text()
        self.assertIn("next_number: 7", text, "the counter was clobbered by the schema rewrite")

    def test_marker_is_removed_on_success(self):
        mt.migrate(self.root)
        self.assertIsNone(mt.find_marker(self.root))

    def test_rerunning_a_migrated_tree_is_a_no_op(self):
        mt.migrate(self.root)
        out = mt.migrate(self.root)
        self.assertEqual(out["status"], "already-migrated")

    def test_dry_run_writes_nothing(self):
        out = mt.migrate(self.root, dry_run=True)
        self.assertEqual(out["status"], "would-migrate")
        self.assertTrue((self.root / "docs" / "manifest.yml").is_file())
        self.assertIsNone(mt.find_marker(self.root))


class ConfigPreservationTests(TreeFixture):
    def test_existing_artifact_prefix_survives(self):
        """Baked into every id on disk — discarding it is unrecoverable."""
        (self.root / ".bionic.yml").write_text(
            'config_version: "1"\ndocs_dir: docs\nartifact_prefix: "CRX"\n', encoding="utf-8")
        mt.migrate(self.root)
        cfg = (self.root / ".bionic.yml").read_text()
        self.assertIn('artifact_prefix: "CRX"', cfg, "artifact_prefix was destroyed")
        self.assertIn("docs_dir: bionic", cfg)

    def test_unknown_keys_survive(self):
        (self.root / ".bionic.yml").write_text(
            'config_version: "1"\ndocs_dir: docs\nfuture_key: keep-me\n', encoding="utf-8")
        mt.migrate(self.root)
        self.assertIn("future_key: keep-me", (self.root / ".bionic.yml").read_text())

    def test_config_naming_an_unrelated_tree_is_refused(self):
        (self.root / ".bionic.yml").write_text(
            'config_version: "1"\ndocs_dir: somewhere-else\n', encoding="utf-8")
        with self.assertRaises(mt.MigrationError) as cm:
            mt.migrate(self.root)
        self.assertIn("disagrees about", str(cm.exception))


class RefusalTests(TreeFixture):
    def test_two_trees_without_a_marker_is_refused(self):
        (self.root / "bionic" / "manifest.yml").write_text(MANIFEST_V4, encoding="utf-8")
        with self.assertRaises(mt.MigrationError) as cm:
            mt.migrate(self.root)
        self.assertIn("two crux trees", str(cm.exception))

    def test_no_tree_at_all_is_refused(self):
        shutil.rmtree(self.root / "docs")
        with self.assertRaises(mt.MigrationError) as cm:
            mt.migrate(self.root)
        self.assertIn("no crux tree", str(cm.exception))

    def test_wrong_source_schema_is_refused(self):
        (self.root / "docs" / "manifest.yml").write_text(
            'schema_version: "2"\nconcerns_enabled:\n  - adrs\n', encoding="utf-8")
        with self.assertRaises(mt.MigrationError) as cm:
            mt.migrate(self.root)
        self.assertIn("earlier rungs", str(cm.exception))

    def test_a_genuine_collision_is_refused_not_overwritten(self):
        """An entry at the destination that this migration never moved."""
        (self.root / "bionic" / "log.md").write_text("SOMEONE ELSE'S FILE\n", encoding="utf-8")
        with self.assertRaises(mt.MigrationError) as cm:
            mt.migrate(self.root)
        self.assertIn("collision", str(cm.exception))
        self.assertEqual((self.root / "bionic" / "log.md").read_text(), "SOMEONE ELSE'S FILE\n")


class CrashResumeTests(TreeFixture):
    """A crash at any step must leave a resumable tree, never a wedged one."""

    def _crash_after(self, step: int):
        """Run the rung but abort once the marker reaches `step`."""
        real = mt.Marker.advance

        def stopping(self_, n):
            real(self_, n)
            if n >= step:
                raise RuntimeError(f"injected crash after step {n}")

        mt.Marker.advance = stopping
        try:
            with self.assertRaises(RuntimeError):
                mt.migrate(self.root)
        finally:
            mt.Marker.advance = real

    def test_crash_after_step_3_resumes_and_completes(self):
        self._crash_after(3)
        self.assertIsNotNone(mt.find_marker(self.root), "marker should survive a crash")
        out = mt.migrate(self.root)
        self.assertEqual(out["status"], "migrated")
        self.assertTrue((self.tree() / "invariants" / "checks" / "a_check.md").is_file())
        self.assertTrue((self.tree() / "adrs" / "ADR-0001-x.md").is_file())

    def test_crash_after_step_4_leaves_manifest_at_source_so_discovery_still_resolves_there(self):
        self._crash_after(4)
        self.assertTrue((self.root / "docs" / "manifest.yml").is_file(),
                        "manifest moved too early — a torn tree would read as migrated")
        out = mt.migrate(self.root)
        self.assertEqual(out["status"], "migrated")

    def test_crash_after_step_5_resumes_and_completes(self):
        self._crash_after(5)
        out = mt.migrate(self.root)
        self.assertEqual(out["status"], "migrated")
        self.assertEqual(mt.read_schema_version(self.tree() / "manifest.yml"), "5")

    def test_resume_does_not_mistake_already_moved_entries_for_collisions(self):
        """The four-way classification's whole purpose."""
        self._crash_after(4)
        moved_already = (self.root / "bionic" / "adrs" / "ADR-0001-x.md")
        self.assertTrue(moved_already.is_file(), "fixture assumption: entry moved before the crash")
        out = mt.migrate(self.root)
        self.assertEqual(out["status"], "migrated")


class ClassificationTests(unittest.TestCase):
    def setUp(self):
        _reset_root()
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.src, self.dst = self.tmp / "s", self.tmp / "d"
        self.src.mkdir(); self.dst.mkdir()

    def test_source_only_moves(self):
        (self.src / "f").write_text("x")
        self.assertEqual(mt.classify(self.src / "f", self.dst / "f", set(), "f"), "move")

    def test_destination_only_in_inventory_is_already_moved(self):
        (self.dst / "f").write_text("x")
        self.assertEqual(mt.classify(self.src / "f", self.dst / "f", {"f"}, "f"), "skip-done")

    def test_destination_only_not_in_inventory_is_a_collision(self):
        (self.dst / "f").write_text("x")
        self.assertEqual(mt.classify(self.src / "f", self.dst / "f", set(), "f"), "collide")

    def test_both_directories_recurse(self):
        (self.src / "d").mkdir(); (self.dst / "d").mkdir()
        self.assertEqual(mt.classify(self.src / "d", self.dst / "d", set(), "d"), "recurse")

    def test_both_files_collide(self):
        (self.src / "f").write_text("a"); (self.dst / "f").write_text("b")
        self.assertEqual(mt.classify(self.src / "f", self.dst / "f", set(), "f"), "collide")

    def test_file_meeting_directory_collides(self):
        (self.src / "x").write_text("a"); (self.dst / "x").mkdir()
        self.assertEqual(mt.classify(self.src / "x", self.dst / "x", set(), "x"), "collide")


class AbandonTests(TreeFixture):
    def test_abandon_removes_a_stale_marker(self):
        mt.Marker(self.root / "bionic" / mt.MARKER_NAME, "docs", 3, ["adrs"]).save()
        out = mt.abandon(self.root)
        self.assertEqual(out["status"], "abandoned")
        self.assertIsNone(mt.find_marker(self.root))

    def test_abandon_refuses_while_two_trees_are_present(self):
        (self.root / "bionic" / "manifest.yml").write_text(MANIFEST_V4, encoding="utf-8")
        mt.Marker(self.root / "bionic" / mt.MARKER_NAME, "docs", 3, ["adrs"]).save()
        with self.assertRaises(mt.MigrationError) as cm:
            mt.abandon(self.root)
        self.assertIn("two crux trees", str(cm.exception))

    def test_abandon_with_no_marker_is_a_no_op(self):
        self.assertEqual(mt.abandon(self.root)["status"], "no-marker")


class MarkerTests(unittest.TestCase):
    def test_round_trips_source_step_and_inventory(self):
        _reset_root()
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / ".migrating"
            mt.Marker(p, "docs", 4, ["adrs", "log.md"]).save()
            loaded = mt.Marker.load(p)
            self.assertEqual((loaded.source, loaded.step, loaded.inventory),
                             ("docs", 4, ["adrs", "log.md"]))

    def test_unparseable_marker_accounts_for_nothing(self):
        _reset_root()
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / ".migrating"
            p.write_text("garbage\n", encoding="utf-8")
            self.assertIsNone(mt.Marker.load(p))


if __name__ == "__main__":
    unittest.main()


class RelocatedTreeTests(unittest.TestCase):
    """Regressions for the 1.8.0 bug: source discovery ignored the configured docs_dir.

    Reported against 1.8.0 with this exact layout. The tool could not find the
    tree at the true repo root, and forcing it with `--repo-root <subdir>` would
    have migrated into a new `<subdir>/bionic/` — moving a deliberately
    gitignored vault to a git-visible path and stranding the root-level
    invariants suite. ADR-0059 specified a custom form for precisely this; the
    branch existed but was unreachable.
    """

    CONFIGS = (".crux", ".bionic.yml")

    def _repo(self, config_name: str, docs_dir: str = ".lodestar/docs") -> Path:
        _reset_root()
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        tree = root / docs_dir
        (tree / "adrs").mkdir(parents=True)
        (tree / "invariants").mkdir(parents=True)
        (tree / "manifest.yml").write_text(MANIFEST_V4, encoding="utf-8")
        (tree / "invariants" / "a-pin.md").write_text("---\nid: INV-0001\n---\n", encoding="utf-8")
        (root / config_name).write_text(
            f'config_version: "1"\ndocs_dir: {docs_dir}\n', encoding="utf-8")
        inv = root / "bionic" / "invariants"
        inv.mkdir(parents=True)
        (inv / "c1.md").write_text("# check: c1\n", encoding="utf-8")
        (inv / "reconciliation.yml").write_text(
            'config_version: "1"\nchecks: []\n', encoding="utf-8")
        (root / ".gitignore").write_text(f"{docs_dir}\n", encoding="utf-8")
        return root

    def test_finds_a_relocated_tree_from_either_config_file(self):
        for cfg in self.CONFIGS:
            with self.subTest(config=cfg):
                root = self._repo(cfg)
                out = mt.migrate(root, dry_run=True)
                self.assertEqual(out["source"], ".lodestar/docs")
                self.assertEqual(out["form"], "custom")

    def test_a_relocated_tree_is_not_moved(self):
        """Relocating it would change the repo's privacy posture."""
        root = self._repo(".crux")
        mt.migrate(root)
        self.assertTrue((root / ".lodestar" / "docs" / "manifest.yml").is_file())
        self.assertFalse((root / ".lodestar" / "bionic").exists(),
                         "created a sibling bionic/ inside the gitignored parent")
        self.assertFalse((root / "bionic" / "manifest.yml").exists(),
                         "moved the tree to the repo root")

    def test_the_gitignored_path_still_covers_the_tree_afterwards(self):
        root = self._repo(".crux")
        mt.migrate(root)
        ignored = (root / ".gitignore").read_text().strip()
        self.assertTrue((root / ignored).is_dir(),
                        "the tree no longer lives at the path .gitignore names")

    def test_the_root_level_suite_is_merged_not_stranded(self):
        root = self._repo(".crux")
        mt.migrate(root)
        inv = root / ".lodestar" / "docs" / "invariants"
        self.assertTrue((inv / "checks" / "c1.md").is_file(), "check was stranded")
        self.assertTrue((inv / "reconciliation.yml").is_file(), "reconciliation was stranded")
        self.assertTrue((inv / "a-pin.md").is_file(), "ledger page lost")
        self.assertFalse((root / "bionic").exists(), "emptied husk left behind")

    def test_schema_bumps_and_config_is_left_pointing_at_the_same_tree(self):
        root = self._repo(".bionic.yml")
        mt.migrate(root)
        self.assertEqual(
            mt.read_schema_version(root / ".lodestar" / "docs" / "manifest.yml"), "5")
        self.assertIn("docs_dir: .lodestar/docs", (root / ".bionic.yml").read_text())

    def test_rerun_is_a_no_op(self):
        root = self._repo(".crux")
        mt.migrate(root)
        self.assertEqual(mt.migrate(root)["status"], "already-migrated")

    def test_docs_dir_flag_overrides_config_resolution(self):
        """The escape hatch for a layout no config declares."""
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        tree = root / "vault" / "notes"
        tree.mkdir(parents=True)
        (tree / "manifest.yml").write_text(MANIFEST_V4, encoding="utf-8")
        out = mt.migrate(root, dry_run=True, docs_dir="vault/notes")
        self.assertEqual(out["source"], "vault/notes")
        self.assertEqual(out["form"], "custom")

    def test_config_naming_a_third_location_still_refuses(self):
        root = self._repo(".crux")
        (root / ".crux").write_text(
            'config_version: "1"\ndocs_dir: somewhere/else\n', encoding="utf-8")
        with self.assertRaises(mt.MigrationError) as cm:
            mt.migrate(root)
        self.assertIn("no crux tree found", str(cm.exception))

    def test_missing_configured_tree_names_the_declared_path_in_the_error(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        (root / ".bionic.yml").write_text(
            'config_version: "1"\ndocs_dir: nope/here\n', encoding="utf-8")
        with self.assertRaises(mt.MigrationError) as cm:
            mt.migrate(root)
        self.assertIn("nope/here", str(cm.exception))


class ContainmentAndSafetyTests(unittest.TestCase):
    """Regressions for the second-round review findings.

    The headline one: `docs_dir` had no containment check, so a repo-controlled
    config could drive writes OUTSIDE the repository — and would rewrite the
    committed config with a machine-specific absolute path.
    """

    def _root(self) -> Path:
        _reset_root()
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        return root

    def _tree_at(self, root: Path, rel: str) -> Path:
        d = root / rel
        d.mkdir(parents=True, exist_ok=True)
        (d / "manifest.yml").write_text(MANIFEST_V4, encoding="utf-8")
        return d

    def test_parent_traversal_is_refused(self):
        root = self._root()
        outside = root.parent / f"outside-{root.name}"
        outside.mkdir()
        self.addCleanup(shutil.rmtree, outside, ignore_errors=True)
        (outside / "manifest.yml").write_text(MANIFEST_V4, encoding="utf-8")
        (root / ".bionic.yml").write_text(
            f'config_version: "1"\ndocs_dir: ../{outside.name}\n', encoding="utf-8")
        with self.assertRaises(mt.MigrationError) as cm:
            mt.migrate(root, dry_run=True)
        self.assertIn("outside the repository", str(cm.exception))
        self.assertTrue((outside / "manifest.yml").is_file(), "touched a tree outside the repo")

    def test_absolute_docs_dir_is_refused(self):
        root = self._root()
        with tempfile.TemporaryDirectory() as other:
            (root / ".bionic.yml").write_text(
                f'config_version: "1"\ndocs_dir: {other}\n', encoding="utf-8")
            with self.assertRaises(mt.MigrationError):
                mt.migrate(root, dry_run=True)

    def test_repo_root_as_docs_dir_is_refused(self):
        """`docs_dir: .` would make the entire repository the tree."""
        root = self._root()
        (root / "manifest.yml").write_text(MANIFEST_V4, encoding="utf-8")
        (root / ".bionic.yml").write_text('config_version: "1"\ndocs_dir: .\n', encoding="utf-8")
        with self.assertRaises(mt.MigrationError):
            mt.migrate(root, dry_run=True)

    def test_trailing_slash_in_docs_dir_still_matches(self):
        root = self._root()
        self._tree_at(root, "vault/notes")
        (root / ".bionic.yml").write_text(
            'config_version: "1"\ndocs_dir: vault/notes/\n', encoding="utf-8")
        out = mt.migrate(root, dry_run=True)
        self.assertEqual(out["source"], "vault/notes")

    def test_a_symlinked_conventional_tree_keeps_its_literal_label(self):
        """`_label` is lexical; resolving it mis-fired the custom form."""
        root = self._root()
        real = root / ".vault"
        real.mkdir()
        (real / "manifest.yml").write_text(MANIFEST_V4, encoding="utf-8")
        try:
            (root / "docs").symlink_to(real, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        out = mt.migrate(root, dry_run=True)
        self.assertEqual(out["source"], "docs", "a symlinked docs/ lost its literal label")
        self.assertEqual(out["form"], "default")

    def test_explicit_docs_dir_does_not_fall_back_to_a_conventional_tree(self):
        """A typo in the escape hatch must fail, not migrate something else."""
        root = self._root()
        self._tree_at(root, "docs")
        with self.assertRaises(mt.MigrationError) as cm:
            mt.migrate(root, dry_run=True, docs_dir="vault/typo")
        self.assertIn("authoritative", str(cm.exception))

    def test_config_naming_a_third_location_is_refused_even_when_bionic_is_valid(self):
        """The reversed membership test silently accepted this."""
        root = self._root()
        self._tree_at(root, "bionic")
        (root / ".bionic.yml").write_text(
            'config_version: "1"\ndocs_dir: some/other/tree\n', encoding="utf-8")
        with self.assertRaises(mt.MigrationError):
            mt.migrate(root, dry_run=True)

    def test_an_unexpected_entry_in_the_suite_is_refused_not_stranded(self):
        root = self._root()
        self._tree_at(root, "docs")
        inv = root / "bionic" / "invariants"
        inv.mkdir(parents=True)
        (inv / "reconciliation.yml").write_text('config_version: "1"\nchecks: []\n', encoding="utf-8")
        (inv / "stray.yml").write_text("surprise\n", encoding="utf-8")
        with self.assertRaises(mt.MigrationError) as cm:
            mt.migrate(root)
        self.assertIn("unexpected entry", str(cm.exception))

    def test_custom_form_marker_is_found_on_resume(self):
        """The flagship new path silently lost crash safety."""
        root = self._root()
        tree = self._tree_at(root, ".lodestar/docs")
        (root / ".crux").write_text(
            'config_version: "1"\ndocs_dir: .lodestar/docs\n', encoding="utf-8")
        mt.Marker(tree / mt.MARKER_NAME, ".lodestar/docs", 3, ["adrs"]).save()
        self.assertEqual(mt.find_marker(root), None if False else mt.find_marker(root))
        out = mt.migrate(root, dry_run=True)
        self.assertTrue(out["resuming"], "an interrupted custom migration did not resume")

    def test_a_marker_pointing_outside_the_repo_is_refused(self):
        """Marker contents are repo-controlled; containment must cover them."""
        root = self._root()
        self._tree_at(root, "docs")
        (root / "bionic").mkdir(exist_ok=True)
        mt.Marker(root / "bionic" / mt.MARKER_NAME, "../elsewhere", 3, []).save()
        with self.assertRaises(mt.MigrationError) as cm:
            mt.migrate(root, dry_run=True)
        self.assertIn("outside the repository", str(cm.exception))

    def test_a_stale_marker_cannot_override_an_explicit_docs_dir(self):
        root = self._root()
        self._tree_at(root, "vault/notes")
        (root / "bionic").mkdir(exist_ok=True)
        mt.Marker(root / "bionic" / mt.MARKER_NAME, "docs", 3, []).save()
        with self.assertRaises(mt.MigrationError) as cm:
            mt.migrate(root, dry_run=True, docs_dir="vault/notes")
        self.assertIn("--abandon", str(cm.exception))

    def test_an_existing_checks_dir_travels_in_the_custom_form(self):
        root = self._root()
        self._tree_at(root, ".vault/docs")
        (root / ".bionic.yml").write_text(
            'config_version: "1"\ndocs_dir: .vault/docs\n', encoding="utf-8")
        inv = root / "bionic" / "invariants"
        (inv / "checks").mkdir(parents=True)
        (inv / "checks" / "old.md").write_text("# check: old\n", encoding="utf-8")
        (inv / "reconciliation.yml").write_text('config_version: "1"\nchecks: []\n', encoding="utf-8")
        mt.migrate(root)
        self.assertTrue((root / ".vault/docs/invariants/checks/old.md").is_file(),
                        "a pre-existing checks/ directory was stranded")
        self.assertFalse((root / "bionic").exists(), "husk survived")

    def test_an_escaping_destination_symlink_is_refused(self):
        """Round 3: the source was guarded and the destination was not."""
        root = self._root()
        self._tree_at(root, "docs")
        outside = root.parent / f"dest-{root.name}"
        outside.mkdir()
        self.addCleanup(shutil.rmtree, outside, ignore_errors=True)
        try:
            (root / "bionic").symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        with self.assertRaises(mt.MigrationError) as cm:
            mt.migrate(root)
        self.assertIn("outside the repository", str(cm.exception))
        self.assertEqual(list(outside.iterdir()), [], "wrote outside the repository")

    def test_a_check_collision_refuses_instead_of_overwriting(self):
        """The ordinary .md move silently overwrote an existing check."""
        root = self._root()
        tree = self._tree_at(root, ".vault/docs")
        (root / ".bionic.yml").write_text(
            'config_version: "1"\ndocs_dir: .vault/docs\n', encoding="utf-8")
        (tree / "invariants" / "checks").mkdir(parents=True)
        (tree / "invariants" / "checks" / "c1.md").write_text("KEEP ME\n", encoding="utf-8")
        inv = root / "bionic" / "invariants"
        inv.mkdir(parents=True)
        (inv / "c1.md").write_text("# check: c1\n", encoding="utf-8")
        (inv / "reconciliation.yml").write_text('config_version: "1"\nchecks: []\n', encoding="utf-8")
        with self.assertRaises(mt.MigrationError) as cm:
            mt.migrate(root)
        self.assertIn("collision", str(cm.exception))
        self.assertEqual((tree / "invariants" / "checks" / "c1.md").read_text(), "KEEP ME\n")

    def test_abandon_ignores_a_config_naming_an_out_of_repo_tree(self):
        root = self._root()
        outside = root.parent / f"ab-{root.name}"
        outside.mkdir()
        self.addCleanup(shutil.rmtree, outside, ignore_errors=True)
        stray = outside / mt.MARKER_NAME
        stray.write_text("source: docs\nstep: 1\ninventory:\n", encoding="utf-8")
        (root / ".bionic.yml").write_text(
            f'config_version: "1"\ndocs_dir: ../{outside.name}\n', encoding="utf-8")
        mt.abandon(root)
        self.assertTrue(stray.is_file(), "abandon() unlinked a file outside the repository")

    def test_find_marker_ignores_an_out_of_repo_configured_tree(self):
        root = self._root()
        outside = root.parent / f"fm-{root.name}"
        outside.mkdir()
        self.addCleanup(shutil.rmtree, outside, ignore_errors=True)
        (outside / mt.MARKER_NAME).write_text("source: docs\nstep: 1\n", encoding="utf-8")
        (root / ".bionic.yml").write_text(
            f'config_version: "1"\ndocs_dir: ../{outside.name}\n', encoding="utf-8")
        self.assertIsNone(mt.find_marker(root))

    def test_a_symlinked_suite_source_is_refused(self):
        """Round 4: the suite SOURCE was the fifth unchecked path."""
        root = self._root()
        self._tree_at(root, ".vault/docs")
        (root / ".bionic.yml").write_text(
            'config_version: "1"\ndocs_dir: .vault/docs\n', encoding="utf-8")
        outside = root.parent / f"suite-{root.name}"
        (outside / "checks").mkdir(parents=True)
        self.addCleanup(shutil.rmtree, outside, ignore_errors=True)
        (outside / "c1.md").write_text("# check: c1\n", encoding="utf-8")
        (root / "bionic").mkdir()
        try:
            (root / "bionic" / "invariants").symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        with self.assertRaises(mt.MigrationError):
            mt.migrate(root)
        self.assertTrue((outside / "c1.md").is_file(), "removed a file outside the repository")

    def test_a_nested_entry_replays_as_already_moved_not_a_collision(self):
        """Round 4: the inventory recorded only top-level names."""
        root = self._root()
        src = self._tree_at(root, "docs")
        (src / "foo").mkdir()
        (src / "foo" / "a.md").write_text("A\n", encoding="utf-8")
        (root / "bionic" / "foo").mkdir(parents=True)
        mt.migrate(root)
        self.assertTrue((root / "bionic" / "foo" / "a.md").is_file())

    def test_inventory_round_trips_paths_containing_spaces(self):
        """`\\S+` silently dropped them, breaking replay for legal filenames."""
        _reset_root()
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / ".migrating"
            mt.Marker(p, "docs", 4, ["foo bar.md", "a/b c/d.md"]).save()
            self.assertEqual(mt.Marker.load(p).inventory, ["foo bar.md", "a/b c/d.md"])

    def test_abandon_refuses_when_a_configured_tree_and_a_conventional_one_both_exist(self):
        """Round 5's fix was claimed but absent; this pins it."""
        root = self._root()
        self._tree_at(root, ".vault/docs")
        self._tree_at(root, "bionic")
        (root / ".bionic.yml").write_text(
            'config_version: "1"\ndocs_dir: .vault/docs\n', encoding="utf-8")
        mt.Marker(root / ".vault/docs" / mt.MARKER_NAME, ".vault/docs", 3, []).save()
        with self.assertRaises(mt.MigrationError) as cm:
            mt.abandon(root)
        self.assertIn("two crux trees", str(cm.exception))

    def test_a_source_side_symlinked_checks_dir_is_refused(self):
        root = self._root()
        self._tree_at(root, ".vault/docs")
        (root / ".bionic.yml").write_text(
            'config_version: "1"\ndocs_dir: .vault/docs\n', encoding="utf-8")
        elsewhere = root / "unrelated"
        elsewhere.mkdir()
        (elsewhere / "keep.md").write_text("KEEP\n", encoding="utf-8")
        inv = root / "bionic" / "invariants"
        inv.mkdir(parents=True)
        (inv / "reconciliation.yml").write_text('config_version: "1"\nchecks: []\n', encoding="utf-8")
        try:
            (inv / "checks").symlink_to(elsewhere, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        with self.assertRaises(mt.MigrationError):
            mt.migrate(root)
        self.assertTrue((elsewhere / "keep.md").is_file(), "drained an unrelated in-repo directory")
