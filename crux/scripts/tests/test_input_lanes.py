"""The shared input-lane helpers decide absence by errno and never read a failure as empty.

`path_state` returns None only for ENOENT or ENOTDIR and re-raises every other
failure. `list_directory` returns every name, hidden names included, and raises
naming the directory when it cannot list it. `absent_reason` and
`output_reason` carry no absolute path.

Every refusal runs on the fixture its positive control just passed on. A
permission-based test skips when the effective uid is 0, because root reads a
mode-000 path.

Run:
  uv run python3 -m unittest discover -s crux/scripts/tests -p 'test_input_lanes.py'
"""

from __future__ import annotations

import errno
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import input_lanes  # noqa: E402


def skip_if_root(case: unittest.TestCase) -> None:
    if os.geteuid() == 0:
        case.skipTest("running as root: a mode-000 path is still readable")


class LaneHelperTestCase(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.dir = self.root / "inputs"
        self.dir.mkdir()
        self.file = self.dir / "a.md"
        self.file.write_text("a\n", encoding="utf-8")

    def lock(self, path: Path, mode: int) -> None:
        skip_if_root(self)
        path.chmod(mode)
        self.addCleanup(path.chmod, 0o755)


class PathStateTests(LaneHelperTestCase):
    def test_an_existing_file_returns_its_stat_in_both_follow_modes(self):
        for follow in (True, False):
            with self.subTest(follow=follow):
                st = input_lanes.path_state(self.file, follow=follow)
                self.assertIsNotNone(st)
                self.assertTrue(stat.S_ISREG(st.st_mode))

    def test_an_absent_path_is_confirmed_absent_in_both_follow_modes(self):
        for follow in (True, False):
            with self.subTest(follow=follow):
                self.assertIsNone(input_lanes.path_state(self.dir / "missing.md", follow=follow))

    def test_an_ancestor_that_is_a_file_is_confirmed_absent(self):
        # ENOTDIR from the stat itself: the ancestor is not a directory.
        for follow in (True, False):
            with self.subTest(follow=follow):
                self.assertIsNone(input_lanes.path_state(self.file / "child.md", follow=follow))

    def test_a_dangling_link_is_absent_when_followed_and_present_when_not(self):
        link = self.dir / "link.md"
        link.symlink_to(self.dir / "gone.md")
        self.assertIsNone(input_lanes.path_state(link))
        st = input_lanes.path_state(link, follow=False)
        self.assertIsNotNone(st)
        self.assertTrue(stat.S_ISLNK(st.st_mode))

    def test_an_unsearchable_parent_raises_rather_than_reading_as_absent(self):
        # POSITIVE CONTROL: the same fixture, searchable, returns the stat.
        for follow in (True, False):
            self.assertIsNotNone(input_lanes.path_state(self.file, follow=follow))
        self.lock(self.dir, 0o600)
        for follow in (True, False):
            with self.subTest(follow=follow):
                with self.assertRaises(PermissionError) as cm:
                    input_lanes.path_state(self.file, follow=follow)
                self.assertEqual(cm.exception.errno, errno.EACCES)
                self.assertTrue(input_lanes.is_path_attributable(cm.exception))


class ListDirectoryTests(LaneHelperTestCase):
    def test_every_name_is_returned_sorted_with_hidden_names(self):
        (self.dir / ".hidden").mkdir()
        (self.dir / "b.md").write_text("b\n", encoding="utf-8")
        self.assertEqual(input_lanes.list_directory(self.dir), [".hidden", "a.md", "b.md"])

    def test_an_empty_directory_is_the_only_empty_listing(self):
        empty = self.dir / "empty"
        empty.mkdir()
        self.assertEqual(input_lanes.list_directory(empty), [])

    def test_an_unlistable_directory_raises_naming_it(self):
        # POSITIVE CONTROL: the same directory, readable, lists its file.
        self.assertEqual(input_lanes.list_directory(self.dir), ["a.md"])
        self.lock(self.dir, 0o000)
        with self.assertRaises(PermissionError) as cm:
            input_lanes.list_directory(self.dir)
        self.assertEqual(Path(cm.exception.filename), self.dir)

    def test_a_regular_file_at_the_directory_path_raises_naming_it(self):
        # POSITIVE CONTROL: the parent lists, and holds the file as an entry.
        self.assertEqual(input_lanes.list_directory(self.dir), ["a.md"])
        with self.assertRaises(NotADirectoryError) as cm:
            input_lanes.list_directory(self.file)
        self.assertEqual(Path(cm.exception.filename), self.file)

    def test_an_absent_directory_raises_rather_than_listing_empty(self):
        with self.assertRaises(FileNotFoundError) as cm:
            input_lanes.list_directory(self.dir / "missing")
        self.assertEqual(Path(cm.exception.filename), self.dir / "missing")


class ReasonTests(LaneHelperTestCase):
    def test_absent_reason_names_the_absence_and_its_repair(self):
        file_reason = input_lanes.absent_reason("file")
        member_reason = input_lanes.absent_reason("member")
        for reason in (file_reason, member_reason):
            with self.subTest(reason=reason):
                self.assertIn("absent", reason)
                self.assertIn("restore", reason)
                self.assertNotIn(str(self.root), reason)
        self.assertIn("catalogue", member_reason)
        self.assertNotEqual(file_reason, member_reason)

    def test_absent_reason_refuses_an_unknown_kind(self):
        with self.assertRaises(ValueError):
            input_lanes.absent_reason("directory")

    def test_output_reason_extends_the_document_reason_with_the_regeneration_repair(self):
        skip_if_root(self)
        # POSITIVE CONTROL: the same file reads before the lock.
        self.assertEqual(self.file.read_text(encoding="utf-8"), "a\n")
        self.file.chmod(0o000)
        self.addCleanup(self.file.chmod, 0o644)
        with self.assertRaises(PermissionError) as cm:
            self.file.read_text(encoding="utf-8")
        reason = input_lanes.output_reason(cm.exception)
        self.assertTrue(reason.startswith(input_lanes.document_reason(cm.exception)), reason)
        self.assertIn("EACCES", reason)
        self.assertIn("rerun the regenerator", reason)
        self.assertNotIn(str(self.root), reason)
        self.assertNotIn(str(self.root.resolve()), reason)

    def test_output_reason_covers_content_that_is_not_utf8(self):
        self.file.write_bytes(b"\xff\n")
        with self.assertRaises(UnicodeDecodeError) as cm:
            self.file.read_text(encoding="utf-8")
        reason = input_lanes.output_reason(cm.exception)
        self.assertIn("not valid UTF-8", reason)
        self.assertIn("rerun the regenerator", reason)


class OptionalFileStateTests(LaneHelperTestCase):
    """An optional file named by path: absent only when stat AND lstat confirm it."""

    def test_a_regular_file_returns_its_stat(self):
        st = input_lanes.optional_file_state(self.file)
        self.assertIsNotNone(st)
        self.assertTrue(stat.S_ISREG(st.st_mode))

    def test_an_absent_file_and_an_ancestor_that_is_a_file_are_confirmed_absent(self):
        self.assertIsNone(input_lanes.optional_file_state(self.dir / "missing.yml"))
        self.assertIsNone(input_lanes.optional_file_state(self.file / "child.yml"))

    def test_a_dangling_link_is_not_confirmed_absent(self):
        link = self.dir / "ledger.yml"
        target = self.dir / "target.yml"
        target.write_text("a: 1\n", encoding="utf-8")
        link.symlink_to(target)
        # POSITIVE CONTROL: with its target present, the link reads as the file.
        self.assertIsNotNone(input_lanes.optional_file_state(link, name="bionic/ledger.yml"))
        target.unlink()
        with self.assertRaises(input_lanes.DanglingOptionalLinkError) as cm:
            input_lanes.optional_file_state(link, name="bionic/ledger.yml")
        exc = cm.exception
        self.assertNotIsInstance(exc, OSError)
        self.assertFalse(input_lanes.is_path_attributable(exc))
        self.assertIn("bionic/ledger.yml", str(exc))
        self.assertIn("symbolic link", str(exc))
        self.assertNotIn(str(self.root), str(exc))
        self.assertNotIn(str(self.root.resolve()), str(exc))

    def test_a_symbolic_link_loop_raises_eloop_for_the_document_lane(self):
        loop = self.dir / "loop.yml"
        loop.symlink_to(loop)
        with self.assertRaises(OSError) as cm:
            input_lanes.optional_file_state(loop)
        self.assertEqual(cm.exception.errno, errno.ELOOP)
        self.assertTrue(input_lanes.is_path_attributable(cm.exception))

    def test_a_directory_at_the_path_raises_eisdir_for_the_document_lane(self):
        with self.assertRaises(IsADirectoryError) as cm:
            input_lanes.optional_file_state(self.dir, name="bionic/inputs")
        self.assertEqual(cm.exception.errno, errno.EISDIR)
        self.assertEqual(cm.exception.filename, "bionic/inputs")
        self.assertTrue(input_lanes.is_path_attributable(cm.exception))

    def test_a_mode_000_file_still_has_a_state_and_its_read_is_refused(self):
        self.lock(self.file, 0o000)
        self.assertIsNotNone(input_lanes.optional_file_state(self.file))
        with self.assertRaises(PermissionError):
            self.file.read_bytes()

    def test_a_file_under_an_unsearchable_parent_raises_rather_than_reading_as_absent(self):
        # POSITIVE CONTROL: searchable, the same file has a state.
        self.assertIsNotNone(input_lanes.optional_file_state(self.file))
        self.lock(self.dir, 0o600)
        with self.assertRaises(PermissionError) as cm:
            input_lanes.optional_file_state(self.file)
        self.assertEqual(cm.exception.errno, errno.EACCES)

    def test_a_fifo_is_an_environment_lane_error_and_is_never_opened(self):
        fifo = self.dir / "pipe.yml"
        os.mkfifo(fifo)
        with self.assertRaises(OSError) as cm:
            input_lanes.optional_file_state(fifo, name="bionic/pipe.yml")
        self.assertIsNone(cm.exception.errno)
        self.assertIn("FIFO", str(cm.exception))
        self.assertFalse(input_lanes.is_path_attributable(cm.exception))


if __name__ == "__main__":
    unittest.main()
