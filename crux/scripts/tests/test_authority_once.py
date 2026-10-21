"""CYC-0030 b4b: the authority gates do each piece of repeated work once per process.

The memos here store only a success bound to inputs the key proves unchanged. None
stores a refusal, and each repeat that must refuse still refuses.
"""

from __future__ import annotations

import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import yaml

import _council_gate_support as sup
import admission_source_io
import git_read_cache
import implementation_migration as migration
import path_read_memo
import yaml_read_memo


class _CountingLoader:
    def __init__(self):
        self.texts = []
        self._real = yaml.safe_load

    def __call__(self, stream, *args, **kwargs):
        self.texts.append(stream)
        return self._real(stream, *args, **kwargs)


class YamlReadMemoTests(unittest.TestCase):
    def setUp(self):
        self.counter = _CountingLoader()
        patcher = mock.patch.object(yaml, "safe_load", self.counter)
        patcher.start(); self.addCleanup(patcher.stop)

    def test_a_repeated_text_is_parsed_once_inside_the_scope(self):
        with yaml_read_memo.scope():
            first = yaml.safe_load("a: [1, 2]\n")
            second = yaml.safe_load("a: [1, 2]\n")
        self.assertEqual((first, second), ({"a": [1, 2]}, {"a": [1, 2]}))
        self.assertEqual(self.counter.texts, ["a: [1, 2]\n"])

    def test_outside_the_scope_every_text_is_parsed(self):
        yaml.safe_load("a: 1\n"); yaml.safe_load("a: 1\n")
        self.assertEqual(len(self.counter.texts), 2)
        self.assertIs(yaml.safe_load, self.counter)

    def test_a_hit_is_an_independent_copy(self):
        with yaml_read_memo.scope():
            first = yaml.safe_load("a: [1]\n")
            first["a"].append(2)
            second = yaml.safe_load("a: [1]\n")
            second["a"].append(3)
            third = yaml.safe_load("a: [1]\n")
        self.assertEqual((first, second, third), ({"a": [1, 2]}, {"a": [1, 3]}, {"a": [1]}))

    def test_shared_references_in_one_document_survive_a_hit(self):
        text = "a: &x [1]\nb: *x\n"
        with yaml_read_memo.scope():
            yaml.safe_load(text)
            hit = yaml.safe_load(text)
        self.assertIs(hit["a"], hit["b"])

    def test_a_refused_text_refuses_again_and_is_never_stored(self):
        bad = "a: [1\n"
        with yaml_read_memo.scope():
            for _ in range(2):
                with self.assertRaises(yaml.YAMLError):
                    yaml.safe_load(bad)
        self.assertEqual(self.counter.texts, [bad, bad])

    def test_a_different_text_is_a_different_answer(self):
        with yaml_read_memo.scope():
            self.assertEqual(yaml.safe_load("a: 1\n"), {"a": 1})
            self.assertEqual(yaml.safe_load("a: 2\n"), {"a": 2})

    def test_only_a_plain_string_is_memoized(self):
        with yaml_read_memo.scope():
            for _ in range(2):
                yaml.safe_load(b"a: 1\n")
                yaml.safe_load("a: 1\n", )
        self.assertEqual(self.counter.texts.count(b"a: 1\n"), 2)
        self.assertEqual(self.counter.texts.count("a: 1\n"), 1)

    def test_the_scope_restores_the_loader_and_nests(self):
        with yaml_read_memo.scope():
            self.assertIsNot(yaml.safe_load, self.counter)
            with yaml_read_memo.scope():
                yaml.safe_load("a: 1\n")
            yaml.safe_load("a: 1\n")
            self.assertIsNot(yaml.safe_load, self.counter)
        self.assertIs(yaml.safe_load, self.counter)
        self.assertEqual(len(self.counter.texts), 1)

    def test_the_scope_restores_the_loader_when_the_block_raises(self):
        with self.assertRaises(RuntimeError):
            with yaml_read_memo.scope():
                raise RuntimeError("boom")
        self.assertIs(yaml.safe_load, self.counter)

    def test_a_later_scope_starts_empty(self):
        with yaml_read_memo.scope():
            yaml.safe_load("a: 1\n")
        with yaml_read_memo.scope():
            yaml.safe_load("a: 1\n")
        self.assertEqual(len(self.counter.texts), 2)


def age(path: Path) -> None:
    old = time.time() - 3600
    os.utime(path, (old, old), follow_symlinks=False)


class PathReadMemoTests(unittest.TestCase):
    """`_read` and `_checked` answer a repeat from memory only while the path keeps its identity."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = sup.init_repo(Path(temp.name) / "repo").resolve()
        (self.root / "sub").mkdir()
        self.file = self.root / "sub" / "a.txt"
        self.file.write_text("one\n")
        sup.commit_all(self.root, "first")
        age(self.file)
        self.opened = 0
        real = admission_source_io.SourceIO.read_bytes
        def counting(this, *args, **kwargs):
            self.opened += 1
            return real(this, *args, **kwargs)
        patcher = mock.patch.object(admission_source_io.SourceIO, "read_bytes", counting)
        patcher.start(); self.addCleanup(patcher.stop)

    def read(self, rel="sub/a.txt"):
        return migration._read(self.root, rel)

    def per_call(self):
        """How many reads one unmemoized call makes (the call reads, then revalidates)."""
        before = self.opened
        self.read()
        used = self.opened - before
        self.opened = 0
        return used

    def test_a_repeated_read_walks_the_file_once_inside_a_scope(self):
        one = self.per_call()
        with git_read_cache.scope():
            first = self.read(); second = self.read()
        self.assertEqual((first, second), (("one\n", "sub/a.txt"), ("one\n", "sub/a.txt")))
        self.assertEqual(self.opened, one)

    def test_outside_a_scope_every_read_walks_the_file(self):
        one = self.per_call()
        self.read(); self.read()
        self.assertEqual(self.opened, 2 * one)

    def test_a_rewrite_of_the_same_size_is_a_miss(self):
        one = self.per_call()
        with git_read_cache.scope():
            self.read()
            self.file.write_text("two\n")
            age(self.file)
            self.assertEqual(self.read()[0], "two\n")
        self.assertEqual(self.opened, 2 * one)

    def test_a_rewrite_that_restores_the_modification_time_is_a_miss(self):
        before = os.stat(self.file)
        with git_read_cache.scope():
            self.read()
            self.file.write_text("two\n")
            os.utime(self.file, ns=(before.st_atime_ns, before.st_mtime_ns))
            self.assertEqual(self.read()[0], "two\n")

    def test_a_replaced_file_is_a_miss(self):
        one = self.per_call()
        with git_read_cache.scope():
            self.read()
            other = self.root / "sub" / "b.txt"
            other.write_text("one\n"); age(other)
            os.replace(other, self.file)
            self.read()
        self.assertEqual(self.opened, 2 * one)

    def test_a_leaf_turned_into_a_link_refuses_with_the_unmemoized_code(self):
        with git_read_cache.scope():
            self.read()
            target = self.root / "sub" / "t.txt"; target.write_text("one\n")
            self.file.unlink(); self.file.symlink_to(target)
            with self.assertRaises(migration.Refused) as caught:
                self.read()
            with self.assertRaises(migration.Refused) as again:
                self.read()
        self.assertEqual((caught.exception.code, again.exception.code),
                         ("migration-symlink-refused", "migration-symlink-refused"))

    def test_a_directory_turned_into_a_link_refuses(self):
        with git_read_cache.scope():
            self.assertEqual(self.read()[0], "one\n")
            moved = self.root / "moved"; os.rename(self.root / "sub", moved)
            (self.root / "sub").symlink_to(moved)
            with self.assertRaises(migration.Refused):
                self.read()

    def test_a_refusal_is_never_stored(self):
        with git_read_cache.scope():
            for _ in range(2):
                with self.assertRaises(migration.Refused):
                    self.read("sub/absent.txt")
            (self.root / "sub" / "absent.txt").write_text("now\n")
            self.assertEqual(self.read("sub/absent.txt")[0], "now\n")

    def test_an_oversize_read_still_refuses_beside_a_remembered_small_one(self):
        with git_read_cache.scope():
            self.assertEqual(migration._bounded_read(self.root, "sub/a.txt", 1000)[0], "one\n")
            with self.assertRaises(migration.Refused) as caught:
                migration._bounded_read(self.root, "sub/a.txt", 2)
        self.assertEqual(caught.exception.code, "migration-source-oversize")

    def test_a_checked_path_that_becomes_a_link_refuses(self):
        with git_read_cache.scope():
            migration._checked(self.root, "sub/a.txt")
            target = self.root / "sub" / "t.txt"; target.write_text("one\n")
            self.file.unlink(); self.file.symlink_to(target)
            with self.assertRaises(migration.Refused) as caught:
                migration._checked(self.root, "sub/a.txt")
        self.assertEqual(caught.exception.code, "migration-symlink-refused")

    def test_a_checked_absent_path_stays_a_hit_only_while_absent(self):
        with git_read_cache.scope():
            migration._checked(self.root, "sub/later.txt")
            target = self.root / "sub" / "t.txt"; target.write_text("x\n")
            (self.root / "sub" / "later.txt").symlink_to(target)
            with self.assertRaises(migration.Refused):
                migration._checked(self.root, "sub/later.txt")

    def test_the_stamp_of_a_young_file_carries_its_digest(self):
        young = self.root / "young.txt"; young.write_text("a\n")
        first = path_read_memo.stamp(str(self.root), "young.txt")
        young.write_text("b\n")
        self.assertNotEqual(first, path_read_memo.stamp(str(self.root), "young.txt"))


class CitationScanReuseTests(unittest.TestCase):
    """A second citation scan in one scope reads only what changed, and a source that changes
    while the scan runs still refuses."""

    def setUp(self):
        from contextlib import closing
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = sup.init_repo(Path(temp.name) / "repo").resolve()
        (self.root / "a.md").write_text("see rule:some-slug here\n")
        (self.root / "b.md").write_text("nothing here\n")
        sup.commit_all(self.root, "first")
        for name in ("a.md", "b.md"):
            age(self.root / name)
        self.module = migration._reference_reader()
        self.batch = {"entries": [{"affected_governs": [{"handle": "ADR-0001/some-slug"}]}]}
        self.reads = 0
        real = admission_source_io.SourceIO.read_bytes
        def counting(this, *args, **kwargs):
            self.reads += 1
            return real(this, *args, **kwargs)
        patcher = mock.patch.object(admission_source_io.SourceIO, "read_bytes", counting)
        patcher.start(); self.addCleanup(patcher.stop)
        self.closing = closing

    def scan(self):
        from observation_admission import _AdmissionIO
        with self.closing(_AdmissionIO(self.root)) as source_io:
            files = [self.root / "a.md", self.root / "b.md"]
            return migration._inspect_citation_sources(self.root, self.batch, self.module, files, source_io)

    def test_a_second_scan_in_a_scope_reads_nothing_and_returns_the_same_answer(self):
        with git_read_cache.scope():
            first = self.scan(); reads = self.reads
            second = self.scan()
        self.assertEqual(first, second)
        self.assertEqual(first[0][0]["path"], "a.md")
        self.assertGreater(reads, 0)
        self.assertEqual(self.reads, reads)

    def test_outside_a_scope_every_scan_reads(self):
        self.scan(); reads = self.reads
        self.scan()
        self.assertEqual(self.reads, 2 * reads)

    def test_an_edited_source_is_read_again_and_changes_the_answer(self):
        with git_read_cache.scope():
            self.assertEqual(len(self.scan()[0]), 1)
            (self.root / "b.md").write_text("now rule:some-slug too\n")
            self.assertEqual([row["path"] for row in self.scan()[0]], ["a.md", "b.md"])

    def test_a_remembered_source_that_changes_during_the_scan_refuses(self):
        from admission_source_io import SourceIORefusal
        real = migration._checked
        def touching(repo, path):
            if Path(path).name == "b.md":
                (self.root / "a.md").write_text("changed rule:some-slug!\n")
            return real(repo, path)
        with git_read_cache.scope():
            self.scan()
            with mock.patch.object(migration, "_checked", touching):
                with self.assertRaises(SourceIORefusal):
                    self.scan()


class ScopeWiringTests(unittest.TestCase):
    def test_the_reader_scope_shares_the_yaml_memo_and_restores_the_loader(self):
        original = yaml.safe_load
        with migration.read_scope():
            self.assertIsNot(yaml.safe_load, original)
        self.assertIs(yaml.safe_load, original)

    def test_an_authority_view_shares_the_yaml_memo(self):
        original = yaml.safe_load
        seen = []
        real = migration._authority_view
        def watching(repo, revision):
            seen.append(yaml.safe_load is not original)
            return real(repo, revision)
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        root = sup.init_repo(Path(temp.name) / "repo")
        (root / "a.txt").write_text("x\n"); sup.commit_all(root, "one")
        with mock.patch.object(migration, "_authority_view", watching):
            migration.authority_view(root)
        self.assertEqual(seen, [True])
        self.assertIs(yaml.safe_load, original)


class BindingAuditTests(unittest.TestCase):
    """The binding memo treats a git child started through `posix_spawn` like any git child."""

    def audit(self, event, program):
        import binding_memo
        reads = binding_memo._Reads("/tmp")
        token = binding_memo._RECORDER.set(reads)
        try:
            binding_memo._audit(event, (program, [program], {}))
        finally:
            binding_memo._RECORDER.reset(token)
        return reads.foreign_process

    def test_a_posix_spawned_git_is_not_a_foreign_process(self):
        self.assertFalse(self.audit("os.posix_spawn", "/usr/bin/git"))

    def test_a_posix_spawned_other_program_is_a_foreign_process(self):
        self.assertTrue(self.audit("os.posix_spawn", "/usr/bin/python3"))

    def test_a_forked_child_is_still_a_foreign_process(self):
        self.assertTrue(self.audit("os.fork", "/usr/bin/git"))


if __name__ == "__main__":
    unittest.main()
