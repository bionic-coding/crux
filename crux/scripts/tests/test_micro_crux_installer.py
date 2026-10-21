"""Consumer installation preserves user bytes and recovers only witnessed writes."""
from __future__ import annotations

from copy import deepcopy
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))


class MicroCruxInstallerTests(unittest.TestCase):
    def setUp(self):
        self.mod = importlib.import_module("micro_crux")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.repo = self.base / "consumer"
        self.repo.mkdir()
        (self.repo / ".bionic.yml").write_text('config_version: "1"\ndocs_dir: knowledge\nartifact_prefix: APP\n')
        self.docs = self.repo / "knowledge"
        self.docs.mkdir()
        (self.docs / "manifest.yml").write_text('schema_version: "5"\nconcerns_enabled: [adrs, journal]\nadr:\n  next_number: 1\n')
        self.plugin = self.base / "plugin"
        (self.plugin / "box").mkdir(parents=True)
        self.payload = b"# Micro-crux\n\nA standalone guide.\n"
        (self.plugin / "box/micro-crux.md").write_bytes(self.payload)

    def install(self, **options):
        return self.mod.install(self.repo, self.plugin, **options)

    def snapshot(self):
        return {p.relative_to(self.repo).as_posix(): p.read_bytes() for p in self.repo.rglob("*") if p.is_file() and not p.is_symlink()}

    def state(self):
        return json.loads((self.docs / self.mod.STATE_NAME).read_text())

    def test_first_repeat_and_dry_run_preserve_existing_instructions(self):
        original = b"# Project\r\n\r\nKeep these bytes.\r\n"
        (self.repo / "AGENTS.md").write_bytes(original)
        before = self.snapshot()
        dry = self.install(dry_run=True)
        self.assertTrue(dry["changed"])
        self.assertEqual(before, self.snapshot())
        self.assertTrue(self.install()["changed"])
        self.assertEqual(self.payload, (self.repo / "micro-crux.md").read_bytes())
        self.assertEqual(original + b"\n" + self.mod.POINTER, (self.repo / "AGENTS.md").read_bytes())
        self.assertIsNone(self.state()["pending"])
        installed = self.snapshot()
        self.assertFalse(self.install()["changed"])
        self.assertEqual(installed, self.snapshot())
        self.assertIn("AGENTS.md", " ".join(self.install()["notes"]))

    def test_creates_instruction_file_but_never_initializes_a_tree(self):
        self.install()
        self.assertEqual(self.mod.POINTER, (self.repo / "AGENTS.md").read_bytes())
        missing = self.base / "missing"
        missing.mkdir()
        with self.assertRaises(self.mod.InstallConflict):
            self.mod.install(missing, self.plugin)
        self.assertEqual([], list(missing.iterdir()))

    def test_matching_unmanaged_guide_adopted_by_exact_bytes(self):
        (self.repo / "micro-crux.md").write_bytes(self.payload)
        self.assertTrue(self.install()["changed"])
        self.assertEqual(self.mod.sha(self.payload), self.state()["installed"]["guide_sha256"])

    def test_unknown_marker_is_never_installation_ownership(self):
        (self.repo / "AGENTS.md").write_bytes(self.mod.POINTER)
        before = self.snapshot()
        with self.assertRaisesRegex(self.mod.InstallConflict, "ownership"):
            self.install()
        self.assertEqual(before, self.snapshot())

    def test_unmanaged_different_guide_conflict_is_preflight(self):
        (self.repo / "micro-crux.md").write_bytes(b"user draft")
        before = self.snapshot()
        with self.assertRaises(self.mod.InstallConflict):
            self.install()
        self.assertEqual(before, self.snapshot())

    def test_update_managed_guide_keeps_outside_instruction_edits(self):
        self.install()
        outside = b"Keep user preface\n\n"
        agent = self.repo / "AGENTS.md"
        agent.write_bytes(outside + agent.read_bytes() + b"\nKeep user suffix\n")
        expected = agent.read_bytes()
        self.payload += b"Upstream update.\n"
        (self.plugin / "box/micro-crux.md").write_bytes(self.payload)
        self.assertTrue(self.install()["changed"])
        self.assertEqual(expected, agent.read_bytes())
        self.assertEqual(self.payload, (self.repo / "micro-crux.md").read_bytes())
        self.assertFalse(self.install()["changed"])

    def test_guide_or_pointer_local_edits_and_deletion_are_preserved(self):
        self.install()
        saved = self.snapshot()
        for path in (self.repo / "micro-crux.md", self.repo / "AGENTS.md"):
            with self.subTest(path=path.name):
                original = path.read_bytes()
                path.write_bytes(original + b"edit" if path.name == "micro-crux.md" else original.replace(b"before reviewing", b"after reviewing"))
                changed = self.snapshot()
                with self.assertRaises(self.mod.InstallConflict):
                    self.install()
                self.assertEqual(changed, self.snapshot())
                path.write_bytes(original)
                path.unlink()
                changed = self.snapshot()
                with self.assertRaises(self.mod.InstallConflict):
                    self.install()
                self.assertEqual(changed, self.snapshot())
                path.write_bytes(original)
        self.assertEqual(saved, self.snapshot())

    def test_missing_malformed_or_foreign_metadata_refuses_without_mutation(self):
        self.install()
        state = self.docs / self.mod.STATE_NAME
        original = state.read_bytes()
        for data in (None, b"{", b'{}', b'{"format":"other","format_version":1}'):
            with self.subTest(data=data):
                state.unlink(missing_ok=True)
                if data is not None:
                    state.write_bytes(data)
                before = self.snapshot()
                with self.assertRaises(self.mod.InstallConflict):
                    self.install()
                self.assertEqual(before, self.snapshot())
        state.write_bytes(original)
        altered = json.loads(original)
        altered["targets"]["guide"] = "../outside.md"
        state.write_text(json.dumps(altered))
        before = self.snapshot()
        with self.assertRaises(self.mod.InstallConflict):
            self.install()
        self.assertEqual(before, self.snapshot())

    def test_unsupported_or_invalid_tree_prevents_partial_enrollment(self):
        manifest = self.docs / "manifest.yml"
        for contents in ('schema_version: "4"\nconcerns_enabled: [adrs]\n', '{}', 'not: [valid'):
            with self.subTest(contents=contents):
                manifest.write_text(contents)
                before = self.snapshot()
                with self.assertRaises(self.mod.InstallConflict):
                    self.install()
                self.assertEqual(before, self.snapshot())

    def test_config_discovery_and_ambiguous_or_malformed_layout(self):
        (self.repo / ".bionic.yml").unlink()
        conventional = self.repo / "bionic"
        self.docs.rename(conventional)
        self.docs = conventional
        self.install()
        self.assertEqual("bionic", self.state()["docs_dir"])
        # A second real tree makes bare discovery ambiguous.
        other = self.repo / "docs"
        other.mkdir()
        (other / "manifest.yml").write_text('schema_version: "5"\nconcerns_enabled: [adrs]\n')
        before = self.snapshot()
        with self.assertRaises(self.mod.InstallConflict):
            self.install()
        self.assertEqual(before, self.snapshot())
        (self.repo / ".bionic.yml").write_text('config_version: "99"\ndocs_dir: knowledge\n')
        with self.assertRaises(self.mod.InstallConflict):
            self.install()

    def test_instruction_case_claude_families_and_declared_exclusion(self):
        for name in ("agents.md", "CLAUDE.md", "Claude.md"):
            with self.subTest(name=name):
                target = self.repo / name
                target.write_bytes(b"Keep original instructions")
                before = self.snapshot()
                with self.assertRaises(self.mod.InstallConflict) as error:
                    self.install()
                self.assertIn(name, str(error.exception))
                self.assertEqual(before, self.snapshot())
                target.unlink()
        config = self.repo / ".bionic.yml"
        config.write_text(config.read_text() + 'instruction_migration_denylist:\n  - AGENTS.md\n')
        with self.assertRaisesRegex(self.mod.InstallConflict, "denylist"):
            self.install()

    def test_inline_denylist_cli_refuses_without_any_target_writes(self):
        config = self.repo / ".bionic.yml"
        config.write_text(config.read_text() + "instruction_migration_denylist: [AGENTS.md]\n")
        (self.repo / "AGENTS.md").write_bytes(b"# Owner instructions\r\nKeep these exact bytes.\r\n")
        before = self.snapshot()
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "install-micro-crux.py"), "--repo-root", str(self.repo)],
            cwd=self.repo, capture_output=True, text=True,
        )
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("instruction_migration_denylist", json.loads(result.stdout)["error"])
        self.assertEqual(before, self.snapshot())
        self.assertFalse((self.repo / "micro-crux.md").exists())
        self.assertFalse((self.docs / self.mod.STATE_NAME).exists())

    def test_quoted_key_and_indentless_denylist_preserve_targets(self):
        config = self.repo / ".bionic.yml"
        base = config.read_text()
        (self.repo / "AGENTS.md").write_bytes(b"Keep owner instructions.\n")
        for declaration in ('"instruction_migration_denylist": [AGENTS.md]\n',
                            "instruction_migration_denylist:\n- AGENTS.md\n"):
            with self.subTest(declaration=declaration):
                config.write_text(base + declaration)
                before = self.snapshot()
                with self.assertRaisesRegex(self.mod.InstallConflict, "instruction_migration_denylist"):
                    self.install()
                self.assertEqual(before, self.snapshot())

    def test_invalid_denylist_refuses_as_preserved_installation_conflict(self):
        config = self.repo / ".bionic.yml"
        config.write_text(config.read_text() + "instruction_migration_denylist: AGENTS.md\n")
        before = self.snapshot()
        with self.assertRaisesRegex(self.mod.InstallConflict, "instruction_migration_denylist"):
            self.install()
        self.assertEqual(before, self.snapshot())

    def test_private_claude_suppressors_are_preserved_and_reported(self):
        local = self.repo / "CLAUDE.local.md"
        local.write_bytes(b"private local instructions")
        claude_dir = self.repo / ".claude"
        claude_dir.mkdir()
        private = claude_dir / "CLAUDE.md"
        private.write_bytes(b"private nested instructions")
        result = self.install()
        notes = " ".join(result["notes"])
        self.assertIn("CLAUDE.local.md", notes)
        self.assertIn(".claude/CLAUDE.md", notes)
        self.assertIn("explicit", notes)
        self.assertEqual(b"private local instructions", local.read_bytes())
        self.assertEqual(b"private nested instructions", private.read_bytes())

    def test_symlink_targets_and_parent_paths_are_refused(self):
        outside = self.base / "outside"
        outside.mkdir()
        for relative in ("micro-crux.md", "AGENTS.md", "knowledge/" + self.mod.STATE_NAME):
            with self.subTest(relative=relative):
                target = self.repo / relative
                target.symlink_to(outside / "absent")
                with self.assertRaises(self.mod.InstallConflict):
                    self.install()
                self.assertTrue(target.is_symlink())
                self.assertEqual([], list(outside.iterdir()))
                target.unlink()
        moved = self.repo / "real-knowledge"
        self.docs.rename(moved)
        self.docs.symlink_to(moved, target_is_directory=True)
        with self.assertRaises(self.mod.InstallConflict):
            self.install()

    def test_path_escape_refuses_and_does_not_write_outside(self):
        config = self.repo / ".bionic.yml"
        for value in ("../outside", "/tmp/unsafe", ".git/context"):
            config.write_text('config_version: "1"\ndocs_dir: ' + value + '\n')
            with self.subTest(value=value), self.assertRaises(self.mod.InstallConflict):
                self.install()

    def test_resume_after_each_write_boundary(self):
        for boundary in range(1, 5):
            with self.subTest(boundary=boundary):
                for path in (self.repo / "micro-crux.md", self.repo / "AGENTS.md", self.docs / self.mod.STATE_NAME):
                    path.unlink(missing_ok=True)
                calls = 0
                real = self.mod.write_atomic
                def interrupted(path, data):
                    nonlocal calls
                    real(path, data)
                    calls += 1
                    if calls == boundary:
                        raise OSError("simulated interruption after atomic replacement")
                with patch.object(self.mod, "write_atomic", side_effect=interrupted), self.assertRaises(OSError):
                    self.install()
                if boundary < 4:
                    self.assertIsNotNone(self.state()["pending"])
                self.install()
                self.assertEqual(self.payload, (self.repo / "micro-crux.md").read_bytes())
                self.assertEqual(self.mod.POINTER, (self.repo / "AGENTS.md").read_bytes())
                self.assertIsNone(self.state()["pending"])
                self.assertFalse(self.install()["changed"])

    def test_pending_recovery_rejects_user_edits_and_changed_upstream(self):
        real = self.mod.write_atomic
        calls = 0
        def interrupted(path, data):
            nonlocal calls
            real(path, data)
            calls += 1
            if calls == 2:
                raise OSError("interrupted after guide")
        with patch.object(self.mod, "write_atomic", side_effect=interrupted), self.assertRaises(OSError):
            self.install()
        guide = self.repo / "micro-crux.md"
        guide.write_bytes(b"user changed the partial install")
        before = self.snapshot()
        with self.assertRaises(self.mod.InstallConflict):
            self.install()
        self.assertEqual(before, self.snapshot())
        guide.write_bytes(self.payload)
        (self.plugin / "box/micro-crux.md").write_bytes(self.payload + b"new upstream")
        with self.assertRaises(self.mod.InstallConflict):
            self.install()

    def test_update_recovers_after_each_changed_write_boundary(self):
        for boundary in range(1, 4):
            with self.subTest(boundary=boundary):
                self.install()
                payload = (self.plugin / "box/micro-crux.md").read_bytes() + b"next revision\n"
                (self.plugin / "box/micro-crux.md").write_bytes(payload)
                calls = 0
                real = self.mod.write_atomic
                def interrupted(path, data):
                    nonlocal calls
                    real(path, data)
                    calls += 1
                    if calls == boundary:
                        raise OSError("interrupted update")
                with patch.object(self.mod, "write_atomic", side_effect=interrupted), self.assertRaises(OSError):
                    self.install()
                self.install()
                self.assertEqual(payload, (self.repo / "micro-crux.md").read_bytes())
                self.assertIsNone(self.state()["pending"])
                self.assertFalse(self.install()["changed"])

    def test_recovery_preserves_outside_edits_but_refuses_pointer_edits(self):
        real = self.mod.write_atomic
        calls = 0
        def interrupted(path, data):
            nonlocal calls
            real(path, data)
            calls += 1
            if calls == 3:
                raise OSError("interrupted after instructions")
        with patch.object(self.mod, "write_atomic", side_effect=interrupted), self.assertRaises(OSError):
            self.install()
        agent = self.repo / "AGENTS.md"
        changed = b"User preface\n\n" + agent.read_bytes() + b"User suffix\n"
        agent.write_bytes(changed.replace(b"before reviewing", b"after reviewing"))
        before = self.snapshot()
        with self.assertRaises(self.mod.InstallConflict):
            self.install()
        self.assertEqual(before, self.snapshot())
        agent.write_bytes(changed)
        self.install()
        self.assertEqual(changed, agent.read_bytes())
        self.assertIsNone(self.state()["pending"])

    def test_failed_atomic_replace_keeps_target_and_leaves_recoverable_intent(self):
        original = b"existing instructions without newline"
        agent = self.repo / "AGENTS.md"
        agent.write_bytes(original)
        real = os.replace
        def interrupted(source, target):
            if Path(target).name == "AGENTS.md":
                raise OSError("simulated replace failure")
            real(source, target)
        with patch.object(self.mod.os, "replace", side_effect=interrupted), self.assertRaises(OSError):
            self.install()
        self.assertEqual(original, agent.read_bytes())
        self.assertFalse(any(".tmp" in p.name for p in self.repo.rglob("*")))
        self.install()
        self.assertTrue(agent.read_bytes().startswith(original))

    def test_cli_uses_selected_consumer_and_shipped_payload(self):
        result = subprocess.run([sys.executable, str(SCRIPTS / "install-micro-crux.py"), "--repo-root", str(self.repo), "--dry-run"], capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr + result.stdout)
        self.assertTrue(json.loads(result.stdout)["changed"])
        self.assertFalse((self.repo / "micro-crux.md").exists())


if __name__ == "__main__":
    unittest.main()
