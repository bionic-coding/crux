"""An ADR tier directory the process cannot list is refused, never read as empty.

THE DEFECT. `adr_frontmatter.adr_paths` listed each tier with `glob.glob`,
which returns `[]` for a directory it cannot read. With the archive tier at
mode 000, `generate-index-rollup.py` wrote a rollup one row short and exited
0, and the next `--dry-run` reported no drift against the shortened output.
The reproduction is retained under the cycle's plan evidence
(`f2-reproduction.sh` and its log).

THE CONTRACT. A tier that does not exist is an empty tier. A tier that exists
and cannot be listed is a denial of access to a declared input: each of the
three ADR generators exits 2, names the directory on stderr and leaves every
output byte-unchanged, in write mode and under `--dry-run`.

Every refusal below runs on the fixture its positive control just passed on,
and a permission-based test skips when the effective uid is 0, because root
lists a mode-000 directory.

Run:
  uv run python3 -m unittest discover -s crux/scripts/tests -p 'test_adr_unlistable_tier.py'
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import adr_frontmatter  # noqa: E402
from test_adr_fence_validation import AdrFenceTestCase, adr  # noqa: E402


class UnlistableArchiveTierTests(AdrFenceTestCase):
    """The archive tier at mode 000: each generator refuses in both modes."""

    def setUp(self) -> None:
        super().setUp()
        self.archive = self.adrs / "archive"
        self.archive.mkdir()
        (self.archive / "ADR-0004-archived.md").write_text(adr(4), encoding="utf-8")

    def lock_archive(self) -> None:
        if os.geteuid() == 0:
            self.skipTest("running as root: a mode-000 directory is still listable")
        self.archive.chmod(0o000)
        self.addCleanup(self.archive.chmod, 0o755)

    def assert_refuses_and_controls(self, script: str, output: Path) -> None:
        # POSITIVE CONTROL: the same fixture, archive readable. The generator
        # succeeds in both modes and its output carries the archived ADR, so
        # the refusal below is caused by the lock and nothing else.
        for mode, args in (("write", ()), ("dry-run", ("--dry-run",))):
            r = self.run_gen(script, *args)
            self.assertEqual(r.returncode, 0, f"control {script} {mode}: {r.stdout!r} {r.stderr!r}")
        self.assertIn("ADR-0004", output.read_text(encoding="utf-8"))
        before = self.outputs()

        self.lock_archive()
        for mode, args in (("write", ()), ("dry-run", ("--dry-run",))):
            with self.subTest(script=script, mode=mode):
                r = self.run_gen(script, *args)
                ctx = f"{script} {mode}: rc={r.returncode} out={r.stdout!r} err={r.stderr!r}"
                self.assertEqual(r.returncode, 2, ctx)
                self.assertNotIn(b"validation_errors", r.stdout, ctx)
                self.assertIn(b"PermissionError", r.stderr, ctx)
                self.assertIn(str(self.archive).encode("utf-8"), r.stderr, ctx)
                self.assertEqual(self.outputs(), before, f"an output changed — {ctx}")

    def test_rollup_refuses_an_unlistable_archive(self):
        self.assert_refuses_and_controls("generate-index-rollup.py", self.docs / "index.md")

    def test_adr_index_refuses_an_unlistable_archive(self):
        self.assert_refuses_and_controls("generate-adr-index.py", self.adrs / "index.md")

    def test_lineage_refuses_an_unlistable_archive(self):
        self.assert_refuses_and_controls("generate-lineage.py", self.adrs / "lineage.md")


class SharedReaderTierTests(AdrFenceTestCase):
    """`adr_paths` itself: absence is empty, every other listing failure raises."""

    def test_an_absent_archive_is_an_empty_tier(self):
        self.assertFalse((self.adrs / "archive").exists())
        names = [p.name for p in adr_frontmatter.adr_paths(self.adrs)]
        self.assertEqual(names, sorted(names))
        self.assertEqual(len(names), 3, names)
        self.assertEqual(adr_frontmatter.adr_paths(self.adrs / "archive", include_archive=False), [])

    def test_an_unsearchable_parent_raises_rather_than_reading_as_empty(self):
        archive = self.adrs / "archive"
        archive.mkdir()
        (archive / "ADR-0004-archived.md").write_text(adr(4), encoding="utf-8")
        # POSITIVE CONTROL: the same fixture lists both tiers.
        self.assertEqual(len(adr_frontmatter.adr_paths(self.adrs)), 4)
        if os.geteuid() == 0:
            self.skipTest("running as root: a mode-600 directory is still searchable")
        self.adrs.chmod(0o600)
        self.addCleanup(self.adrs.chmod, 0o755)
        with self.assertRaises(PermissionError) as cm:
            adr_frontmatter.adr_paths(self.adrs)
        self.assertEqual(Path(cm.exception.filename), archive)

    def test_hidden_and_non_md_names_stay_excluded(self):
        # The glob it replaces skipped hidden names and anything not `*.md`.
        (self.adrs / ".ADR-0009-hidden.md").write_text(adr(9), encoding="utf-8")
        (self.adrs / "ADR-0010-notes.txt").write_text("x", encoding="utf-8")
        names = [p.name for p in adr_frontmatter.adr_paths(self.adrs)]
        self.assertEqual(names, ["ADR-0001-fixture-1.md", "ADR-0002-fixture-2.md",
                                 "ADR-0003-fixture-3.md"])


if __name__ == "__main__":
    unittest.main()
