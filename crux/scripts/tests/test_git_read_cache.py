"""The scoped git read memo answers repeats from memory and never a changed state."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _council_gate_support as sup
import council_records as cr
import git_read_cache
import implementation_approval as ap


class _Counted:
    """Counts the git children the real `subprocess.run` starts."""

    def __init__(self):
        self.calls = []
        self._real = subprocess.run

    def __call__(self, args, *pargs, **kwargs):
        if isinstance(args, list) and args[:1] == ["git"]:
            self.calls.append(tuple(args[3:]))
        return self._real(args, *pargs, **kwargs)


class GitReadCacheTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = sup.init_repo(Path(temp.name) / "repo").resolve()
        (self.root / "a.txt").write_text("one\n")
        sup.commit_all(self.root, "first")
        self.counted = _Counted()
        patcher = mock.patch.object(subprocess, "run", self.counted)
        patcher.start(); self.addCleanup(patcher.stop)

    def reads(self, *args):
        return [c for c in self.counted.calls if c == args]

    def test_a_repeated_admitted_read_starts_one_child_inside_the_scope(self):
        with git_read_cache.scope():
            first = cr.git(self.root, "cat-file", "blob", "HEAD:a.txt")
            second = cr.git(self.root, "cat-file", "blob", "HEAD:a.txt")
        self.assertEqual((first.returncode, first.stdout), (0, b"one\n"))
        self.assertEqual((second.returncode, second.stdout, second.stderr),
                         (first.returncode, first.stdout, first.stderr))
        self.assertEqual(len(self.reads("cat-file", "blob", "HEAD:a.txt")), 1)

    def test_outside_a_scope_every_read_starts_a_child(self):
        cr.git(self.root, "cat-file", "blob", "HEAD:a.txt")
        cr.git(self.root, "cat-file", "blob", "HEAD:a.txt")
        self.assertEqual(len(self.reads("cat-file", "blob", "HEAD:a.txt")), 2)
        self.assertIs(cr.subprocess, subprocess)

    def test_a_commit_inside_the_scope_is_read_fresh(self):
        with git_read_cache.scope():
            before = cr.git(self.root, "cat-file", "blob", "HEAD:a.txt").stdout
            head = cr.git(self.root, "rev-parse", "HEAD").stdout
            (self.root / "a.txt").write_text("two\n")
            sup.commit_all(self.root, "second")
            after = cr.git(self.root, "cat-file", "blob", "HEAD:a.txt").stdout
            moved = cr.git(self.root, "rev-parse", "HEAD").stdout
        self.assertEqual((before, after), (b"one\n", b"two\n"))
        self.assertNotEqual(head, moved)

    def test_a_staged_change_inside_the_scope_is_read_fresh(self):
        with git_read_cache.scope():
            before = cr.git(self.root, "ls-files", "-s", "-z", "--", "a.txt").stdout
            staged_before = cr.git(self.root, "cat-file", "blob", ":0:a.txt").stdout
            (self.root / "a.txt").write_text("staged\n")
            sup.git(self.root, "add", "a.txt")
            after = cr.git(self.root, "ls-files", "-s", "-z", "--", "a.txt").stdout
            staged_after = cr.git(self.root, "cat-file", "blob", ":0:a.txt").stdout
        self.assertNotEqual(before, after)
        self.assertEqual((staged_before, staged_after), (b"one\n", b"staged\n"))

    def test_a_branch_move_that_keeps_the_index_is_read_fresh(self):
        (self.root / "a.txt").write_text("two\n")
        sup.commit_all(self.root, "second")
        with git_read_cache.scope():
            before = cr.git(self.root, "rev-parse", "HEAD").stdout
            sup.git(self.root, "reset", "--soft", "HEAD~1")
            after = cr.git(self.root, "rev-parse", "HEAD").stdout
        self.assertNotEqual(before, after)

    def test_the_scope_restores_a_patched_module(self):
        fake = mock.Mock()
        with mock.patch.object(cr, "subprocess", fake):
            with git_read_cache.scope():
                pass
            self.assertIs(cr.subprocess, fake)

    def test_a_working_tree_read_is_never_cached(self):
        with git_read_cache.scope():
            for _ in range(2):
                cr.git(self.root, "check-ignore", "-q", "--", "a.txt", literal_pathspecs=False)
        self.assertEqual(len(self.reads("check-ignore", "-q", "--", "a.txt")), 2)

    def test_a_failed_read_is_asked_again(self):
        with git_read_cache.scope():
            for _ in range(2):
                self.assertNotEqual(cr.git(self.root, "cat-file", "blob", "HEAD:absent").returncode, 0)
        self.assertEqual(len(self.reads("cat-file", "blob", "HEAD:absent")), 2)

    def test_a_revision_named_by_ref_is_never_cached(self):
        sup.git(self.root, "branch", "side")
        with git_read_cache.scope():
            for _ in range(2):
                cr.git(self.root, "ls-tree", "-z", "side", "--", "a.txt")
        self.assertEqual(len(self.reads("ls-tree", "-z", "side", "--", "a.txt")), 2)

    def test_a_repeated_commit_verification_starts_one_child_and_a_refusal_is_asked_again(self):
        head = cr.git(self.root, "rev-parse", "HEAD").stdout.decode().strip()
        blob = cr.git(self.root, "rev-parse", "HEAD:a.txt").stdout.decode().strip()
        absent = "0" * 40
        with git_read_cache.scope():
            first = cr.git(self.root, "rev-parse", "--verify", head + "^{commit}")
            second = cr.git(self.root, "rev-parse", "--verify", head + "^{commit}")
            wrong = [cr.git(self.root, "rev-parse", "--verify", blob + "^{commit}") for _ in range(2)]
            missing = [cr.git(self.root, "rev-parse", "--verify", absent + "^{commit}") for _ in range(2)]
        self.assertEqual((first.returncode, first.stdout.decode().strip()), (0, head))
        self.assertEqual((second.returncode, second.stdout, second.stderr),
                         (first.returncode, first.stdout, first.stderr))
        self.assertEqual(len(self.reads("rev-parse", "--verify", head + "^{commit}")), 1)
        self.assertTrue(all(r.returncode != 0 for r in wrong + missing))
        self.assertEqual(len(self.reads("rev-parse", "--verify", blob + "^{commit}")), 2)
        self.assertEqual(len(self.reads("rev-parse", "--verify", absent + "^{commit}")), 2)

    def test_the_scope_restores_the_real_module_and_nests(self):
        with git_read_cache.scope():
            self.assertIsNot(cr.subprocess, subprocess)
            with git_read_cache.scope():
                cr.git(self.root, "rev-parse", "HEAD")
            cr.git(self.root, "rev-parse", "HEAD")
            self.assertIsNot(cr.subprocess, subprocess)
        self.assertIs(cr.subprocess, subprocess)
        self.assertEqual(len(self.reads("rev-parse", "HEAD")), 1)

    def test_the_gate_contract_binds_the_same_bytes_inside_the_scope(self):
        outside = ap.production_contract_bytes()
        with git_read_cache.scope():
            inside = ap.production_contract_bytes()
        self.assertEqual(inside, outside)


class LinkedWorktreeTests(unittest.TestCase):
    """A linked worktree keeps its index and HEAD in its own git directory and everything else
    in the common one. The memo reads both, so a repeat is answered from memory and any change
    to either side is a fresh read."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.main = sup.init_repo(Path(temp.name) / "main").resolve()
        (self.main / "a.txt").write_text("one\n")
        sup.commit_all(self.main, "first")
        self.linked = Path(temp.name).resolve() / "linked"
        sup.git(self.main, "worktree", "add", "-q", "-b", "side", str(self.linked))
        self.counted = _Counted()
        patcher = mock.patch.object(subprocess, "run", self.counted)
        patcher.start(); self.addCleanup(patcher.stop)

    def reads(self, *args):
        return [c for c in self.counted.calls if c == args]

    def test_the_fixture_is_a_linked_worktree(self):
        self.assertTrue((self.linked / ".git").is_file())

    def test_a_repeated_read_in_a_linked_worktree_starts_one_child(self):
        with git_read_cache.scope():
            first = cr.git(self.linked, "cat-file", "blob", "HEAD:a.txt")
            second = cr.git(self.linked, "cat-file", "blob", "HEAD:a.txt")
        self.assertEqual((first.returncode, first.stdout), (0, b"one\n"))
        self.assertEqual((second.returncode, second.stdout), (0, b"one\n"))
        self.assertEqual(len(self.reads("cat-file", "blob", "HEAD:a.txt")), 1)

    def test_a_commit_in_the_linked_worktree_is_read_fresh(self):
        with git_read_cache.scope():
            before = cr.git(self.linked, "cat-file", "blob", "HEAD:a.txt").stdout
            (self.linked / "a.txt").write_text("two\n")
            sup.commit_all(self.linked, "second")
            after = cr.git(self.linked, "cat-file", "blob", "HEAD:a.txt").stdout
        self.assertEqual((before, after), (b"one\n", b"two\n"))

    def test_a_staged_change_in_the_linked_worktree_is_read_fresh(self):
        with git_read_cache.scope():
            before = cr.git(self.linked, "cat-file", "blob", ":0:a.txt").stdout
            (self.linked / "a.txt").write_text("staged\n")
            sup.git(self.linked, "add", "a.txt")
            after = cr.git(self.linked, "cat-file", "blob", ":0:a.txt").stdout
        self.assertEqual((before, after), (b"one\n", b"staged\n"))

    def test_a_branch_moved_from_the_main_checkout_is_read_fresh(self):
        (self.main / "a.txt").write_text("two\n")
        sup.commit_all(self.main, "second")
        newer = sup.git(self.main, "rev-parse", "HEAD").strip()
        with git_read_cache.scope():
            before = cr.git(self.linked, "rev-parse", "HEAD").stdout.decode().strip()
            sup.git(self.main, "update-ref", "refs/heads/side", newer)
            after = cr.git(self.linked, "rev-parse", "HEAD").stdout.decode().strip()
        self.assertNotEqual(before, after)
        self.assertEqual(after, newer)

    def test_a_branch_packed_from_the_main_checkout_is_read_fresh(self):
        (self.main / "a.txt").write_text("two\n")
        sup.commit_all(self.main, "second")
        newer = sup.git(self.main, "rev-parse", "HEAD").strip()
        with git_read_cache.scope():
            before = cr.git(self.linked, "rev-parse", "HEAD").stdout.decode().strip()
            sup.git(self.main, "update-ref", "refs/heads/side", newer)
            sup.git(self.main, "pack-refs", "--all", "--prune")
            after = cr.git(self.linked, "rev-parse", "HEAD").stdout.decode().strip()
        self.assertEqual((before != after, after), (True, newer))

    def test_a_worktree_with_its_own_configuration_is_never_cached(self):
        gitdir = Path(cr.git(self.linked, "rev-parse", "--absolute-git-dir").stdout.decode().strip())
        (gitdir / "config.worktree").write_text("[core]\n\tignorecase = false\n")
        with git_read_cache.scope():
            for _ in range(2):
                cr.git(self.linked, "cat-file", "blob", "HEAD:a.txt")
        self.assertEqual(len(self.reads("cat-file", "blob", "HEAD:a.txt")), 2)

    def test_a_worktree_whose_back_pointer_is_wrong_is_never_cached(self):
        gitdir = Path(cr.git(self.linked, "rev-parse", "--absolute-git-dir").stdout.decode().strip())
        (gitdir / "gitdir").write_text(str(self.main / "elsewhere") + "\n")
        with git_read_cache.scope():
            for _ in range(2):
                cr.git(self.linked, "cat-file", "blob", "HEAD:a.txt")
        self.assertEqual(len(self.reads("cat-file", "blob", "HEAD:a.txt")), 2)

    def test_the_default_state_reader_still_refuses_a_linked_worktree(self):
        self.assertIsNone(git_read_cache._repository_state(str(self.linked)))
        self.assertIsNotNone(git_read_cache._repository_state(str(self.linked), linked=True))


class SpawnTests(unittest.TestCase):
    """Inside a scope a git child starts through the resolved executable with the descriptors
    `subprocess` already marks close-on-exec left alone, which lets `subprocess` use
    `posix_spawn`. The caller still sees the argv it asked for and git's own answer."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.tmp = Path(temp.name).resolve()
        self.root = sup.init_repo(self.tmp / "repo").resolve()
        (self.root / "a.txt").write_text("one\n")
        sup.commit_all(self.root, "first")
        self.seen = []
        real = subprocess.run
        def recording(args, *pargs, **kwargs):
            self.seen.append((list(args) if isinstance(args, list) else args, dict(kwargs)))
            return real(args, *pargs, **kwargs)
        patcher = mock.patch.object(subprocess, "run", recording)
        patcher.start(); self.addCleanup(patcher.stop)

    def test_a_scoped_read_starts_the_resolved_git_and_reports_the_requested_argv(self):
        import shutil
        with git_read_cache.scope():
            result = cr.git(self.root, "cat-file", "blob", "HEAD:a.txt")
        self.assertEqual((result.returncode, result.stdout), (0, b"one\n"))
        self.assertEqual(result.args[:3], ["git", "-C", str(self.root)])
        launched, kwargs = self.seen[-1]
        self.assertEqual(launched[:3], ["git", "-C", str(self.root)])
        self.assertEqual(kwargs.get("executable"), shutil.which("git"))
        self.assertIs(kwargs.get("close_fds"), False)

    def test_outside_a_scope_the_call_is_untouched(self):
        cr.git(self.root, "cat-file", "blob", "HEAD:a.txt")
        launched, kwargs = self.seen[-1]
        self.assertEqual(launched[0], "git")
        self.assertNotIn("close_fds", kwargs)
        self.assertNotIn("executable", kwargs)

    def test_the_executable_is_the_one_the_child_environment_would_find(self):
        fake_dir = self.tmp / "bin"; fake_dir.mkdir()
        fake = fake_dir / "git"
        fake.write_text("#!/bin/sh\necho fake\n"); fake.chmod(0o755)
        import os
        with mock.patch.dict(os.environ, {"PATH": str(fake_dir) + os.pathsep + os.environ["PATH"]}):
            outside = cr.git(self.root, "rev-parse", "HEAD").stdout
            with git_read_cache.scope():
                inside = cr.git(self.root, "rev-parse", "HEAD").stdout
        self.assertEqual((outside, inside), (b"fake\n", b"fake\n"))

    def test_a_missing_git_fails_the_same_way_inside_and_outside_a_scope(self):
        import os
        empty = self.tmp / "empty"; empty.mkdir()
        with mock.patch.dict(os.environ, {"PATH": str(empty)}):
            with self.assertRaises(FileNotFoundError):
                cr.git(self.root, "rev-parse", "HEAD")
            with git_read_cache.scope():
                with self.assertRaises(FileNotFoundError):
                    cr.git(self.root, "rev-parse", "HEAD")

    def test_a_call_with_other_arguments_is_passed_through_unchanged(self):
        with git_read_cache.scope():
            cr.subprocess.run(["git", "--version"], capture_output=True, env=cr._git_env(True), input=b"")
        launched, kwargs = self.seen[-1]
        self.assertEqual(launched, ["git", "--version"])
        self.assertNotIn("close_fds", kwargs)


if __name__ == "__main__":
    unittest.main()
