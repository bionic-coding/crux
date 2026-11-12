"""Each open input case takes the lane the accepted decision names.

THE CONTRACT. A recognizable input the process cannot stat, open, read or
decode for a cause attributable to its path takes the DOCUMENT lane: exit 1,
a `validation_errors` entry naming the input by its repository-relative path
and the reason, and every output byte-unchanged. Three such causes are driven
here for each regenerator: a listed candidate whose target is absent (a
dangling symbolic link), a candidate the process cannot open (mode 000), and
a candidate that is not valid UTF-8.

A failure for a cause in the process or host (EIO) takes the ENVIRONMENT lane:
exit 2, NOTHING on stdout, and a stderr message naming the file, the error,
and every document-lane finding the same run met. So does an input directory
that exists and cannot be listed, including a regular file where the
directory is expected, which is never read as an empty or absent input.

The regenerators: `generate-journal-index.py` (write, `--dry-run`,
`--check-stdin`), the three readers of `adr_frontmatter.py`
(`generate-index-rollup.py`, `generate-adr-index.py`, `generate-lineage.py`;
write and `--dry-run`), and `generate-log-summary.py` (write and `--dry-run`),
whose broken input is a settled month's detail file.

Every refusal runs on the fixture its positive control just passed on. A
permission-based test skips when the effective uid is 0, because root reads a
mode-000 path. Every refusal also asserts that no file absent before the run
exists after it.

Run:
  uv run python3 -m unittest discover -s crux/scripts/tests -p 'test_regenerator_input_lanes.py'
"""

from __future__ import annotations

import contextlib
import errno
import importlib.util
import io
import json
import os
import re
import shutil
import sys
import unittest
from pathlib import Path
from unittest import mock

TESTS = Path(__file__).resolve().parent
SCRIPTS = TESTS.parent
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(TESTS))

import adr_frontmatter  # noqa: E402
import input_lanes  # noqa: E402
from test_adr_fence_validation import GENERATORS, AdrFenceTestCase, adr  # noqa: E402
from test_generate_journal_index import (  # noqa: E402
    CLEAN_MONTH,
    REL_INDEX,
    WITNESS,
    JournalCliTestCase,
)

ADR_MODES = (("write", ()), ("dry-run", ("--dry-run",)))
JOURNAL_MODES = (("write", ()), ("dry-run", ("--dry-run",)),
                 ("check-stdin", ("--check-stdin", "--month", "2026-08")))
OTHER_MONTH = "2026-07"


def skip_if_root(case: unittest.TestCase) -> None:
    if os.geteuid() == 0:
        case.skipTest("running as root: a mode-000 path is still readable")


def tree_files(root: Path) -> set[str]:
    """Every path under `root`, relative, so a newly created file is visible."""
    return {str(p.relative_to(root)) for p in root.rglob("*")}


def load_script(name: str):
    """Import a hyphen-named regenerator as a module, for an in-process run."""
    spec = importlib.util.spec_from_file_location(
        "_lanes_" + name.replace("-", "_").removesuffix(".py"), SCRIPTS / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_main(main, argv) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = main(argv)
    return rc, out.getvalue(), err.getvalue()


# ═══════════════════════════════════════════════════════════════════════════
# The three readers of adr_frontmatter.py
# ═══════════════════════════════════════════════════════════════════════════

class AdrInputLaneTestCase(AdrFenceTestCase):
    """ADR-0005 is the input each case breaks; the control proves it is read."""

    def setUp(self) -> None:
        super().setUp()
        self.target = self.adrs / "ADR-0005-fixture-5.md"
        self.target.write_text(adr(5), encoding="utf-8")

    def control(self) -> dict[Path, bytes | None]:
        """POSITIVE CONTROL: every generator succeeds and lists ADR-0005."""
        outputs = self.seed_outputs()
        for script in GENERATORS:
            r = self.run_gen(script, "--dry-run")
            self.assertEqual(r.returncode, 0, f"control {script}: {r.stdout!r} {r.stderr!r}")
        for path, body in outputs.items():
            self.assertIn(b"ADR-0005", body, f"control: {path} does not list ADR-0005")
        return outputs

    def assert_document_lane(self, reason_fragment: str) -> None:
        before = self.outputs()
        files = tree_files(self.root)
        for script in GENERATORS:
            for mode, args in ADR_MODES:
                with self.subTest(script=script, mode=mode):
                    r = self.run_gen(script, *args)
                    ctx = f"{script} {mode}: rc={r.returncode} out={r.stdout!r} err={r.stderr!r}"
                    self.assertEqual(r.returncode, 1, ctx)
                    payload = self.payload(r)
                    self.assertEqual(set(payload), {"validation_errors"}, ctx)
                    errors = payload["validation_errors"]
                    self.assertEqual([e["file"] for e in errors], [self.rel(self.target)], ctx)
                    self.assertIn(reason_fragment, errors[0]["error"], ctx)
                    self.assertNotIn(str(self.root), errors[0]["error"], ctx)
                    self.assertEqual(self.outputs(), before, f"an output changed — {ctx}")
                    self.assertEqual(tree_files(self.root), files, f"a file appeared — {ctx}")


class AdrDanglingLinkTests(AdrInputLaneTestCase):
    def test_a_listed_adr_whose_link_target_is_absent_is_a_document_finding(self):
        real = self.root / "ADR-0005-target.md"
        self.target.rename(real)
        self.target.symlink_to(real)
        self.control()
        real.unlink()
        self.assertTrue(self.target.is_symlink())
        self.assert_document_lane("ENOENT")


class AdrUnopenableTests(AdrInputLaneTestCase):
    def test_an_adr_the_process_cannot_open_is_a_document_finding(self):
        self.control()
        skip_if_root(self)
        self.target.chmod(0o000)
        self.addCleanup(self.target.chmod, 0o644)
        self.assert_document_lane("EACCES")


class AdrNotUtf8Tests(AdrInputLaneTestCase):
    def test_an_adr_that_is_not_utf8_is_a_document_finding(self):
        self.control()
        self.target.write_bytes(adr(5).encode("utf-8").replace(b"Decision 5", b"Decision \xff5"))
        self.assert_document_lane("not valid UTF-8")


class AdrUnlistableDirectoryTests(AdrInputLaneTestCase):
    """The environment lane: exit 2, nothing on stdout, nothing created."""

    def assert_environment_lane(self, named: Path) -> None:
        # Two outputs are removed first, so the run must also create nothing;
        # the rollup's index is its required input region and stays in place.
        before_index = (self.docs / "index.md").read_bytes()
        for script in GENERATORS:
            for mode, args in ADR_MODES:
                with self.subTest(script=script, mode=mode):
                    for gone in (self.adrs / "index.md", self.adrs / "lineage.md"):
                        gone.unlink(missing_ok=True)
                    files = tree_files(self.root)
                    r = self.run_gen(script, *args)
                    ctx = f"{script} {mode}: rc={r.returncode} out={r.stdout!r} err={r.stderr!r}"
                    self.assertEqual(r.returncode, 2, ctx)
                    self.assertEqual(r.stdout, b"", ctx)
                    self.assertIn(str(named).encode("utf-8"), r.stderr, ctx)
                    self.assertEqual((self.docs / "index.md").read_bytes(), before_index, ctx)
                    self.assertEqual(tree_files(self.root), files, f"a file appeared — {ctx}")

    def test_an_unlistable_archive_tier_is_an_environment_failure(self):
        archive = self.adrs / "archive"
        archive.mkdir()
        (archive / "ADR-0006-archived.md").write_text(adr(6), encoding="utf-8")
        self.control()
        skip_if_root(self)
        archive.chmod(0o000)
        self.addCleanup(archive.chmod, 0o755)
        self.assert_environment_lane(archive)

    def test_a_regular_file_at_the_archive_path_is_an_environment_failure(self):
        # The reading this change implements: `stat` succeeds, so the path is
        # not confirmed absent, and the listing fails with ENOTDIR, so it is a
        # directory that cannot be listed — never an empty archive tier.
        archive = self.adrs / "archive"
        archive.mkdir()
        (archive / "ADR-0006-archived.md").write_text(adr(6), encoding="utf-8")
        self.control()
        (archive / "ADR-0006-archived.md").unlink()
        archive.rmdir()
        archive.write_text("not a directory\n", encoding="utf-8")
        self.assert_environment_lane(archive)


class AdrProcessLevelFailureTests(AdrInputLaneTestCase):
    """EIO on one ADR takes the environment lane and names the fence finding beside it."""

    def test_eio_takes_the_environment_lane_over_a_document_finding(self):
        # Every reader of adr_frontmatter.py, in both modes, so each script's own
        # EnvironmentLaneError handler is driven, not only the rollup's.
        self.control()
        bad = self.break_fence(1)
        target = self.target.resolve()
        real_read_text = Path.read_text

        def read_text(path, *a, **kw):
            if Path(path).resolve() == target:
                raise OSError(errno.EIO, "Input/output error", str(path))
            return real_read_text(path, *a, **kw)

        for script in GENERATORS:
            generator = load_script(script)
            for mode, args in ADR_MODES:
                with self.subTest(script=script, mode=mode):
                    argv = ["--repo-root", str(self.root), *args]
                    # POSITIVE CONTROL: unstubbed, the same fixture is a document finding.
                    rc, out, _ = run_main(generator.main, argv)
                    self.assertEqual(rc, 1)
                    self.assertEqual([e["file"] for e in json.loads(out)["validation_errors"]],
                                     [self.rel(bad)])
                    before = self.outputs()
                    files = tree_files(self.root)
                    with mock.patch.object(Path, "read_text", read_text):
                        rc, out, err = run_main(generator.main, argv)
                    self.assertEqual(rc, 2, err)
                    self.assertEqual(out, "")
                    self.assertIn(f"environment failure: {self.rel(self.target)}", err)
                    self.assertIn("Input/output error", err)
                    self.assertIn(f"document finding met in the same run: {self.rel(bad)}", err)
                    self.assertEqual(self.outputs(), before)
                    self.assertEqual(tree_files(self.root), files)

    def test_the_shared_reader_classifies_each_cause(self):
        rel = adr_frontmatter.repo_relative(self.root)
        for code in (errno.EIO, errno.EMFILE):
            with self.subTest(errno=errno.errorcode[code]):
                with mock.patch.object(Path, "read_text",
                                       side_effect=OSError(code, os.strerror(code))):
                    with self.assertRaises(input_lanes.EnvironmentLaneError) as cm:
                        adr_frontmatter.read_adr_inputs([self.target], rel)
                self.assertIn(self.rel(self.target), cm.exception.failures[0])
        for code in sorted(input_lanes.PATH_ATTRIBUTABLE_ERRNOS):
            with self.subTest(errno=errno.errorcode[code]):
                with mock.patch.object(Path, "read_text",
                                       side_effect=OSError(code, os.strerror(code))):
                    texts, findings = adr_frontmatter.read_adr_inputs([self.target], rel)
                self.assertEqual(texts, {})
                self.assertEqual([f["file"] for f in findings], [self.rel(self.target)])
        # POSITIVE CONTROL: unstubbed, the same input reads clean.
        texts, findings = adr_frontmatter.read_adr_inputs([self.target], rel)
        self.assertEqual(findings, [])
        self.assertIn(self.target, texts)


# ═══════════════════════════════════════════════════════════════════════════
# generate-index-rollup.py: its host file and its adrs directory
# ═══════════════════════════════════════════════════════════════════════════

ROLLUP = "generate-index-rollup.py"


class RollupHostFileTestCase(AdrFenceTestCase):
    """`<docs_dir>/index.md` is a required input named by path.

    The control proves the fixture rolls up in both modes; each case then
    breaks the host file or the adrs directory and nothing else.
    """

    def setUp(self) -> None:
        super().setUp()
        self.index = self.docs / "index.md"
        self.rel_index = self.rel(self.index)

    def control(self) -> None:
        """POSITIVE CONTROL: write rolls ADR-0003 in, and --dry-run then reports no drift."""
        r = self.run_gen(ROLLUP)
        self.assertEqual(r.returncode, 0, f"control write: {r.stdout!r} {r.stderr!r}")
        self.assertIn("ADR-0003", self.index.read_text(encoding="utf-8"))
        r = self.run_gen(ROLLUP, "--dry-run")
        self.assertEqual(r.returncode, 0, f"control dry-run: {r.stdout!r} {r.stderr!r}")
        self.assertFalse(self.payload(r)["drift"])

    def outputs(self) -> dict:
        """Each output's bytes, or its stat identity when it cannot be read."""
        snap: dict = {}
        for path in (self.adrs / "index.md", self.adrs / "lineage.md", self.index):
            try:
                snap[path] = path.read_bytes()
            except PermissionError:
                st = path.stat()
                snap[path] = ("unreadable", st.st_ino, st.st_size, st.st_mtime_ns, st.st_mode)
            except (FileNotFoundError, NotADirectoryError, IsADirectoryError):
                snap[path] = None
        return snap

    def assert_no_absolute_path(self, text: str, ctx: str) -> None:
        self.assertNotIn(str(self.root), text, ctx)
        self.assertNotIn(str(self.root.resolve()), text, ctx)

    def assert_document_lane(self, reason_fragment: str, files: list[str] | None = None) -> None:
        before = self.outputs()
        present = tree_files(self.root)
        for mode, args in ADR_MODES:
            with self.subTest(mode=mode):
                r = self.run_gen(ROLLUP, *args)
                ctx = f"{mode}: rc={r.returncode} out={r.stdout!r} err={r.stderr!r}"
                self.assertEqual(r.returncode, 1, ctx)
                payload = self.payload(r)
                self.assertEqual(set(payload), {"validation_errors"}, ctx)
                errors = payload["validation_errors"]
                self.assertEqual([e["file"] for e in errors], files or [self.rel_index], ctx)
                self.assertIn(reason_fragment, errors[0]["error"], ctx)
                for e in errors:
                    self.assert_no_absolute_path(e["error"], ctx)
                self.assertEqual(self.outputs(), before, f"an output changed — {ctx}")
                self.assertEqual(tree_files(self.root), present, f"a file appeared — {ctx}")

    def assert_environment_lane(self, *named: str, unlock=None) -> None:
        """Exit 2, nothing on stdout, each of `named` on stderr, nothing changed or created."""
        before = self.outputs() if unlock is None else None
        present = tree_files(self.root) if unlock is None else None
        for mode, args in ADR_MODES:
            with self.subTest(mode=mode):
                r = self.run_gen(ROLLUP, *args)
                ctx = f"{mode}: rc={r.returncode} out={r.stdout!r} err={r.stderr!r}"
                self.assertEqual(r.returncode, 2, ctx)
                self.assertEqual(r.stdout, b"", ctx)
                for text in named:
                    self.assertIn(text.encode("utf-8"), r.stderr, ctx)
                if unlock is None:
                    self.assertEqual(self.outputs(), before, f"an output changed — {ctx}")
                    self.assertEqual(tree_files(self.root), present, f"a file appeared — {ctx}")


class RollupHostFileDocumentLaneTests(RollupHostFileTestCase):
    def test_positive_control_a_present_index_is_rolled_up(self):
        """Positive control: the absence fixture, with the index present, rolls ADR-0003 in."""
        self.assertTrue(self.index.is_file(), "the fixture has no host index")
        self.control()

    def test_an_absent_index_is_a_document_finding(self):
        self.control()
        self.index.unlink()
        self.assert_document_lane("is a required input and is absent")
        self.assertFalse(self.index.exists(), "a refusal created the absent host file")

    def test_an_index_the_process_cannot_open_is_a_document_finding(self):
        self.control()
        skip_if_root(self)
        before = self.index.read_bytes()
        self.index.chmod(0o000)
        self.addCleanup(self.index.chmod, 0o644)
        self.assert_document_lane("EACCES")
        self.index.chmod(0o644)
        self.assertEqual(self.index.read_bytes(), before, "the unreadable host file changed")

    def test_a_directory_at_the_index_path_is_a_document_finding(self):
        self.control()
        self.index.unlink()
        self.index.mkdir()
        self.assert_document_lane("EISDIR")

    def test_an_index_that_is_not_utf8_is_a_document_finding(self):
        self.control()
        self.index.write_bytes(self.index.read_bytes().replace(b"# index", b"# ind\xffex"))
        self.assert_document_lane("not valid UTF-8")

    def test_an_index_without_its_adrs_section_is_a_document_finding(self):
        # Exit 1 under the content rule, where the rollup once exited 2.
        self.control()
        text = self.index.read_text(encoding="utf-8")
        self.index.write_text(re.sub(r"^## ADRs \(\d+\)$", "## Decisions", text, flags=re.M),
                              encoding="utf-8")
        self.assert_document_lane("'## ADRs (N)' section")

    def test_an_index_finding_and_an_adr_finding_appear_in_one_payload(self):
        self.control()
        bad = self.break_fence(1)
        self.index.unlink()
        self.assert_document_lane("is absent", files=[self.rel_index, self.rel(bad)])


class RollupAdrsDirectoryTests(RollupHostFileTestCase):
    def test_a_regular_file_at_the_adrs_path_is_an_environment_failure(self):
        self.control()
        shutil.rmtree(self.adrs)
        self.adrs.write_text("not a directory\n", encoding="utf-8")
        self.assert_environment_lane(str(self.adrs), "exists and is not a directory")

    def test_a_confirmed_absent_adrs_directory_keeps_exit_two_not_found(self):
        self.control()
        shutil.rmtree(self.adrs)
        self.assert_environment_lane(f"{self.adrs} not found")

    def test_a_regular_file_at_the_tree_path_names_the_adrs_directory_and_the_index(self):
        # Both stats fail with ENOTDIR: the adrs directory is not found, and
        # the absent index is named beside it on stderr, never on stdout.
        self.control()
        shutil.rmtree(self.docs)
        self.docs.write_text("not a directory\n", encoding="utf-8")
        before = self.docs.read_bytes()
        self.assert_environment_lane(
            f"{self.adrs} not found",
            f"document finding met in the same run: {self.rel_index}: is a required input "
            "and is absent")
        self.assertEqual(self.docs.read_bytes(), before)

    def test_an_unsearchable_tree_directory_names_the_adrs_directory_and_the_index(self):
        # The A2 fixture: the tree directory at mode 600.
        self.control()
        skip_if_root(self)
        before = self.outputs()
        present = tree_files(self.root)
        self.docs.chmod(0o600)
        self.addCleanup(self.docs.chmod, 0o755)
        self.assert_environment_lane(
            str(self.adrs), "PermissionError",
            f"document finding met in the same run: {self.rel_index}: could not be read "
            "(EACCES", unlock=True)
        self.docs.chmod(0o755)
        self.assertEqual(self.outputs(), before, "an output changed")
        self.assertEqual(tree_files(self.root), present, "a file appeared")


class RollupHostFileProcessLevelTests(RollupHostFileTestCase):
    """EIO on the host file takes the environment lane and names the fence finding beside it."""

    def test_eio_on_the_index_takes_the_environment_lane(self):
        self.control()
        rollup = load_script(ROLLUP)
        real_read_text = Path.read_text

        def read_text(path, *a, **kw):
            if Path(path) == self.index:
                raise OSError(errno.EIO, "Input/output error", str(path))
            return real_read_text(path, *a, **kw)

        for mode, args in ADR_MODES:
            with self.subTest(mode=mode):
                argv = ["--repo-root", str(self.root), *args]
                # POSITIVE CONTROL: unstubbed, the same fixture succeeds.
                rc, out, err = run_main(rollup.main, argv)
                self.assertEqual(rc, 0, err)
                before = self.outputs()
                with mock.patch.object(Path, "read_text", read_text):
                    rc, out, err = run_main(rollup.main, argv)
                self.assertEqual(rc, 2, err)
                self.assertEqual(out, "")
                self.assertIn(f"environment failure: {self.rel_index}", err)
                self.assertIn("Input/output error", err)
                self.assertEqual(self.outputs(), before)

    def test_eio_on_the_index_names_an_adr_finding_on_stderr(self):
        self.control()
        bad = self.break_fence(1)
        rollup = load_script(ROLLUP)
        argv = ["--repo-root", str(self.root), "--dry-run"]
        # POSITIVE CONTROL: unstubbed, the same fixture is a document finding.
        rc, out, _ = run_main(rollup.main, argv)
        self.assertEqual(rc, 1)
        self.assertEqual([e["file"] for e in json.loads(out)["validation_errors"]],
                         [self.rel(bad)])
        real_read_text = Path.read_text

        def read_text(path, *a, **kw):
            if Path(path) == self.index:
                raise OSError(errno.EIO, "Input/output error", str(path))
            return real_read_text(path, *a, **kw)

        before = self.outputs()
        with mock.patch.object(Path, "read_text", read_text):
            rc, out, err = run_main(rollup.main, argv)
        self.assertEqual(rc, 2, err)
        self.assertEqual(out, "")
        self.assertIn(f"environment failure: {self.rel_index}", err)
        self.assertIn(f"document finding met in the same run: {self.rel(bad)}", err)
        self.assertEqual(self.outputs(), before)


# ═══════════════════════════════════════════════════════════════════════════
# generate-adr-index.py: its adrs directory and its tree configuration
# ═══════════════════════════════════════════════════════════════════════════

ADR_INDEX = "generate-adr-index.py"
ADR_OUTPUTS = (("generate-adr-index.py", "index.md"), ("generate-lineage.py", "lineage.md"))


def snapshot(paths) -> dict:
    """Each path's bytes, its stat identity when unreadable, or None when absent."""
    snap: dict = {}
    for path in paths:
        try:
            snap[path] = path.read_bytes()
        except PermissionError:
            st = path.stat()
            snap[path] = ("unreadable", st.st_ino, st.st_size, st.st_mtime_ns, st.st_mode)
        except IsADirectoryError:
            snap[path] = ("directory", sorted(os.listdir(path)))
        except (FileNotFoundError, NotADirectoryError):
            snap[path] = None
    return snap


class AdrIndexDirectoryTestCase(AdrFenceTestCase):
    """The ADR index's adrs directory: the control proves the fixture indexes ADR-0003."""

    def control(self) -> None:
        r = self.run_gen(ADR_INDEX)
        self.assertEqual(r.returncode, 0, f"control write: {r.stdout!r} {r.stderr!r}")
        self.assertIn("ADR-0003", (self.adrs / "index.md").read_text(encoding="utf-8"))
        r = self.run_gen(ADR_INDEX, "--dry-run")
        self.assertEqual(r.returncode, 0, f"control dry-run: {r.stdout!r} {r.stderr!r}")
        self.assertFalse(self.payload(r)["drift"])

    def watched(self) -> list[Path]:
        return [self.adrs / "index.md", self.adrs / "lineage.md", self.docs / "index.md",
                self.adrs, self.docs]

    def assert_environment_lane(self, *named: str, absent: str | None = None,
                                unlock=None) -> None:
        """Exit 2, nothing on stdout, each of `named` on stderr, no traceback."""
        before = snapshot(self.watched()) if unlock is None else None
        present = tree_files(self.root) if unlock is None else None
        for mode, args in ADR_MODES:
            with self.subTest(mode=mode):
                r = self.run_gen(ADR_INDEX, *args)
                ctx = f"{mode}: rc={r.returncode} out={r.stdout!r} err={r.stderr!r}"
                self.assertEqual(r.returncode, 2, ctx)
                self.assertEqual(r.stdout, b"", ctx)
                self.assertNotIn(b"Traceback", r.stderr, ctx)
                for text in named:
                    self.assertIn(text.encode("utf-8"), r.stderr, ctx)
                if absent is not None:
                    self.assertNotIn(absent.encode("utf-8"), r.stderr, ctx)
                if unlock is None:
                    self.assertEqual(snapshot(self.watched()), before, f"an output changed — {ctx}")
                    self.assertEqual(tree_files(self.root), present, f"a file appeared — {ctx}")


class AdrIndexAdrsDirectoryTests(AdrIndexDirectoryTestCase):
    def test_positive_control_a_present_adrs_directory_is_indexed(self):
        """Positive control: the absence fixture, with the adrs directory present, indexes ADR-0003."""
        self.assertTrue(self.adrs.is_dir(), "the fixture has no adrs directory")
        self.control()

    def test_a_regular_file_at_the_adrs_path_is_an_environment_failure(self):
        # The unlistable-directory case with its real reason, never "not found".
        self.control()
        shutil.rmtree(self.adrs)
        self.adrs.write_text("not a directory\n", encoding="utf-8")
        self.assert_environment_lane(
            "environment failure: bionic/adrs:", "exists and is not a directory",
            absent="not found")

    def test_a_confirmed_absent_adrs_directory_keeps_exit_two_not_found(self):
        self.control()
        shutil.rmtree(self.adrs)
        self.assert_environment_lane("bionic/adrs not found")
        self.assertFalse(self.adrs.exists(), "a refusal created the absent adrs directory")

    def test_a_regular_file_at_the_tree_path_keeps_exit_two_not_found(self):
        # ENOTDIR from an ancestor is confirmed absence.
        self.control()
        shutil.rmtree(self.docs)
        self.docs.write_text("not a directory\n", encoding="utf-8")
        self.assert_environment_lane("bionic/adrs not found")

    def test_an_unsearchable_tree_directory_is_an_environment_failure(self):
        # The tree directory at mode 600: the stat of adrs fails with EACCES,
        # so its existence cannot be determined. Exit 2, no traceback.
        self.control()
        skip_if_root(self)
        before = snapshot(self.watched())
        present = tree_files(self.root)
        self.docs.chmod(0o600)
        self.addCleanup(self.docs.chmod, 0o755)
        self.assert_environment_lane(
            "environment failure: bionic/adrs:", "PermissionError", absent="not found",
            unlock=True)
        self.docs.chmod(0o755)
        self.assertEqual(snapshot(self.watched()), before, "an output changed")
        self.assertEqual(tree_files(self.root), present, "a file appeared")


class AdrIndexTreeConfigurationTests(AdrIndexDirectoryTestCase):
    def test_the_tree_is_resolved_through_bionic_config(self):
        # A flow-mapping .bionic.yml naming another tree. The replaced reader
        # matched `^docs_dir:` line by line, missed it and fell back to bionic/.
        self.control()
        self.docs.rename(self.root / "knowledge")
        (self.root / ".bionic.yml").write_text(
            '{config_version: "1", docs_dir: knowledge}\n', encoding="utf-8")
        r = self.run_gen(ADR_INDEX)
        self.assertEqual(r.returncode, 0, f"{r.stdout!r} {r.stderr!r}")
        self.assertEqual(self.payload(r), {"written": "knowledge/adrs/index.md"})
        self.assertFalse((self.root / "bionic").exists(), "the index was written to bionic/")
        r = self.run_gen(ADR_INDEX, "--dry-run")
        self.assertEqual(r.returncode, 0, f"{r.stdout!r} {r.stderr!r}")
        self.assertEqual(self.payload(r), {"drift": False, "path": "knowledge/adrs/index.md"})


# ═══════════════════════════════════════════════════════════════════════════
# The output reads of generate-adr-index.py and generate-lineage.py
# ═══════════════════════════════════════════════════════════════════════════

class AdrOutputReadTestCase(AdrFenceTestCase):
    """Each script's wholly generated output: only `--dry-run` reads it."""

    def watched(self) -> list[Path]:
        return [self.adrs / "index.md", self.adrs / "lineage.md", self.docs / "index.md"]

    def control(self, script: str, output: Path) -> None:
        """POSITIVE CONTROL: write lists ADR-0003, and --dry-run then reports no drift."""
        r = self.run_gen(script)
        self.assertEqual(r.returncode, 0, f"control {script} write: {r.stdout!r} {r.stderr!r}")
        self.assertIn("ADR-0003", output.read_text(encoding="utf-8"))
        r = self.run_gen(script, "--dry-run")
        self.assertEqual(r.returncode, 0, f"control {script} dry-run: {r.stdout!r} {r.stderr!r}")
        self.assertFalse(self.payload(r)["drift"])

    def each_output(self):
        for script, name in ADR_OUTPUTS:
            with self.subTest(script=script):
                yield script, self.adrs / name

    def assert_output_finding(self, script: str, output: Path, fragment: str) -> None:
        before = snapshot(self.watched())
        present = tree_files(self.root)
        r = self.run_gen(script, "--dry-run")
        ctx = f"{script}: rc={r.returncode} out={r.stdout!r} err={r.stderr!r}"
        self.assertEqual(r.returncode, 1, ctx)
        payload = self.payload(r)
        self.assertEqual(set(payload), {"validation_errors"}, ctx)
        errors = payload["validation_errors"]
        self.assertEqual([e["file"] for e in errors], [self.rel(output)], ctx)
        self.assertIn(fragment, errors[0]["error"], ctx)
        self.assertIn("remove the path and rerun the regenerator", errors[0]["error"], ctx)
        self.assertNotIn(str(self.root), errors[0]["error"], ctx)
        self.assertNotIn(str(self.root.resolve()), errors[0]["error"], ctx)
        self.assertEqual(snapshot(self.watched()), before, f"an output changed — {ctx}")
        self.assertEqual(tree_files(self.root), present, f"a file appeared — {ctx}")

    def eio_on(self, output: Path, seen: list):
        target = output.resolve()
        real_read_text = Path.read_text

        def read_text(path, *a, **kw):
            if Path(path).resolve() == target:
                seen.append(path)
                raise OSError(errno.EIO, "Input/output error", str(path))
            return real_read_text(path, *a, **kw)

        return mock.patch.object(Path, "read_text", read_text)


class AdrOutputReadDocumentLaneTests(AdrOutputReadTestCase):
    def test_an_absent_output_reads_as_empty_under_dry_run(self):
        for script, output in self.each_output():
            self.control(script, output)
            output.unlink()
            r = self.run_gen(script, "--dry-run")
            ctx = f"rc={r.returncode} out={r.stdout!r} err={r.stderr!r}"
            self.assertEqual(r.returncode, 1, ctx)
            payload = self.payload(r)
            self.assertTrue(payload["drift"], ctx)
            self.assertNotIn("validation_errors", payload, ctx)
            self.assertFalse(output.exists(), f"the dry run created the output — {ctx}")

    def test_an_output_the_process_cannot_open_is_a_document_finding(self):
        for script, output in self.each_output():
            self.control(script, output)
            skip_if_root(self)
            output.chmod(0o000)
            self.addCleanup(output.chmod, 0o644)
            self.assert_output_finding(script, output, "EACCES")
            output.chmod(0o644)

    def test_an_output_that_is_not_utf8_is_a_document_finding(self):
        for script, output in self.each_output():
            self.control(script, output)
            output.write_bytes(output.read_bytes().replace(b"ADR-0003", b"ADR-\xff0003", 1))
            self.assert_output_finding(script, output, "not valid UTF-8")

    def test_a_directory_at_the_output_path_is_a_document_finding(self):
        for script, output in self.each_output():
            self.control(script, output)
            output.unlink()
            output.mkdir()
            self.assert_output_finding(script, output, "EISDIR")
            output.rmdir()


class AdrOutputReadProcessLevelTests(AdrOutputReadTestCase):
    def test_eio_on_the_output_takes_the_environment_lane(self):
        for script, output in self.each_output():
            self.control(script, output)
            generator = load_script(script)
            argv = ["--repo-root", str(self.root), "--dry-run"]
            # POSITIVE CONTROL: unstubbed, the same fixture reports no drift.
            rc, out, err = run_main(generator.main, argv)
            self.assertEqual(rc, 0, err)
            before = snapshot(self.watched())
            seen: list = []
            with self.eio_on(output, seen):
                rc, out, err = run_main(generator.main, argv)
            self.assertEqual(rc, 2, err)
            self.assertEqual(out, "")
            self.assertTrue(seen, "the stub was never reached")
            self.assertIn(f"environment failure: {self.rel(output)}", err)
            self.assertIn("Input/output error", err)
            self.assertEqual(snapshot(self.watched()), before)

    def test_an_input_finding_leaves_the_output_unread(self):
        # The order: a run that refuses on its inputs never reads its output,
        # so the stubbed output failure cannot take precedence over the finding.
        for script, output in self.each_output():
            self.control(script, output)
            generator = load_script(script)
            argv = ["--repo-root", str(self.root), "--dry-run"]
            bad = self.break_fence(1)
            seen: list = []
            with self.eio_on(output, seen):
                rc, out, err = run_main(generator.main, argv)
            self.assertEqual(rc, 1, err)
            self.assertEqual([e["file"] for e in json.loads(out)["validation_errors"]],
                             [self.rel(bad)])
            self.assertEqual(seen, [], "the output was read after an input refused")
            # POSITIVE CONTROL: clean inputs, the same stub is reached and takes exit 2.
            bad.write_bytes(b"---\n" + bad.read_bytes()[5:])
            with self.eio_on(output, seen):
                rc, out, err = run_main(generator.main, argv)
            self.assertEqual(rc, 2, err)
            self.assertTrue(seen)


class AdrOutputWriteModeTests(AdrOutputReadTestCase):
    def test_write_mode_replaces_an_output_that_is_not_utf8(self):
        for script, output in self.each_output():
            self.control(script, output)
            good = output.read_bytes()
            output.write_bytes(good.replace(b"ADR-0003", b"ADR-\xff0003", 1))
            r = self.run_gen(script)
            self.assertEqual(r.returncode, 0, f"{r.stdout!r} {r.stderr!r}")
            self.assertEqual(output.read_bytes(), good)

    def test_a_directory_at_the_output_path_fails_the_write_without_a_traceback(self):
        for script, output in self.each_output():
            self.control(script, output)
            output.unlink()
            output.mkdir()
            present = tree_files(self.root)
            r = self.run_gen(script)
            ctx = f"rc={r.returncode} out={r.stdout!r} err={r.stderr!r}"
            self.assertEqual(r.returncode, 2, ctx)
            self.assertEqual(r.stdout, b"", ctx)
            self.assertNotIn(b"Traceback", r.stderr, ctx)
            self.assertIn(f"could not write {self.rel(output)}".encode("utf-8"), r.stderr, ctx)
            self.assertTrue(output.is_dir(), ctx)
            self.assertEqual(tree_files(self.root), present, f"a file appeared — {ctx}")
            output.rmdir()


# ═══════════════════════════════════════════════════════════════════════════
# generate-journal-index.py
# ═══════════════════════════════════════════════════════════════════════════

class JournalInputLaneTestCase(JournalCliTestCase):
    """OTHER_MONTH is the input each case breaks; the control proves it is read."""

    def setUp(self) -> None:
        super().setUp()
        self.target = self.journal / f"{OTHER_MONTH}.md"
        self.rel_target = str(Path(REL_INDEX).with_name(f"{OTHER_MONTH}.md"))
        self.target.write_text(CLEAN_MONTH.replace("2026-09", OTHER_MONTH), encoding="utf-8")

    def control(self) -> bytes:
        """POSITIVE CONTROL: every mode succeeds and the index lists OTHER_MONTH."""
        r = self.run_cli()
        self.assertEqual(r.returncode, 0, self.err(r))
        index = self.index.read_bytes()
        self.assertIn(OTHER_MONTH.encode("utf-8"), index)
        for mode, args in JOURNAL_MODES[1:]:
            r = self.run_cli(*args, stdin=CLEAN_MONTH.encode("utf-8"))
            self.assertEqual(r.returncode, 0, f"control {mode}: {self.out(r)} {self.err(r)}")
        return index

    def assert_document_lane(self, reason_fragment: str) -> None:
        before = self.index.read_bytes()
        files = tree_files(self.root)
        for mode, args in JOURNAL_MODES:
            with self.subTest(mode=mode):
                r = self.run_cli(*args, stdin=CLEAN_MONTH.encode("utf-8"))
                ctx = f"{mode}: rc={r.returncode} out={self.out(r)!r} err={self.err(r)!r}"
                self.assertEqual(r.returncode, 1, ctx)
                payload = self.payload(r)
                self.assertEqual(payload["path"], REL_INDEX, ctx)
                errors = payload["validation_errors"]
                self.assertEqual([e["file"] for e in errors], [self.rel_target], ctx)
                self.assertIn(reason_fragment, errors[0]["error"], ctx)
                self.assertEqual(self.index.read_bytes(), before, ctx)
                self.assertEqual(tree_files(self.root), files, f"a file appeared — {ctx}")


class JournalDanglingLinkTests(JournalInputLaneTestCase):
    def test_a_listed_month_whose_link_target_is_absent_is_a_document_finding(self):
        self.control()
        real = self.root / "elsewhere.md"
        self.target.rename(real)
        self.target.symlink_to(real)
        real.unlink()
        self.assertTrue(self.target.is_symlink())
        self.assert_document_lane("symlink")


class JournalUnopenableTests(JournalInputLaneTestCase):
    def test_a_month_the_process_cannot_open_is_a_document_finding(self):
        self.control()
        skip_if_root(self)
        self.target.chmod(0o000)
        self.addCleanup(self.target.chmod, 0o644)
        self.assert_document_lane("EACCES")


class JournalNotUtf8Tests(JournalInputLaneTestCase):
    def test_a_month_that_is_not_utf8_is_a_document_finding(self):
        self.control()
        self.target.write_bytes(self.target.read_bytes().replace(b"One body", b"One \xff body"))
        self.assert_document_lane("not valid UTF-8")


class JournalUnlistableDirectoryTests(JournalInputLaneTestCase):
    """The environment lane: exit 2, nothing on stdout, nothing created."""

    def assert_environment_lane(self) -> None:
        for mode, args in JOURNAL_MODES:
            with self.subTest(mode=mode):
                files = tree_files(self.root)
                r = self.run_cli(*args, stdin=CLEAN_MONTH.encode("utf-8"))
                ctx = f"{mode}: rc={r.returncode} out={self.out(r)!r} err={self.err(r)!r}"
                self.assertEqual(r.returncode, 2, ctx)
                self.assertEqual(r.stdout, b"", ctx)
                # The directory itself, by the path the script resolved, not
                # the bare word "journal", which the script name also carries.
                self.assertIn(str(self.journal.resolve()), self.err(r), ctx)
                self.assertEqual(tree_files(self.root), files, f"a file appeared — {ctx}")

    def test_an_unlistable_journal_directory_is_an_environment_failure(self):
        index = self.control()
        skip_if_root(self)
        self.journal.chmod(0o000)
        self.addCleanup(self.journal.chmod, 0o755)
        self.assert_environment_lane()
        self.journal.chmod(0o755)
        self.assertEqual(self.index.read_bytes(), index)

    def test_a_regular_file_at_the_journal_path_is_an_environment_failure(self):
        # Before this change `is_dir()` read it as an absent surface, exit 0.
        self.control()
        for p in self.journal.iterdir():
            p.unlink()
        self.journal.rmdir()
        self.journal.write_text("not a directory\n", encoding="utf-8")
        self.assert_environment_lane()


class JournalProcessLevelFailureTests(JournalInputLaneTestCase):
    """EIO on one month takes the environment lane and names the finding beside it."""

    def test_eio_takes_the_environment_lane_over_a_document_finding(self):
        self.control()
        bad = self.journal / "notes.md"  # outside the month-file grammar
        bad.write_text("x\n", encoding="utf-8")
        rel_bad = str(Path(REL_INDEX).with_name("notes.md"))
        gen = load_script("generate-journal-index.py")
        argv = ["--repo-root", str(self.root), "--dry-run"]
        # POSITIVE CONTROL: unstubbed, the same fixture is a document finding.
        rc, out, _ = run_main(gen.main, argv)
        self.assertEqual(rc, 1)
        self.assertEqual([e["file"] for e in json.loads(out)["validation_errors"]], [rel_bad])

        real_read = gen._read_regular_file

        def read(path):
            if Path(path).name == self.target.name:  # the script resolves the root
                raise OSError(errno.EIO, "Input/output error", str(path))
            return real_read(path)

        before = self.index.read_bytes()
        with mock.patch.object(gen, "_read_regular_file", read):
            rc, out, err = run_main(gen.main, argv)
        self.assertEqual(rc, 2, err)
        self.assertEqual(out, "")
        self.assertIn(self.rel_target, err)
        self.assertIn("Input/output error", err)
        self.assertIn(rel_bad, err)
        self.assertEqual(self.index.read_bytes(), before)


class JournalOutputReadTestCase(JournalInputLaneTestCase):
    """Guard 7's read of the wholly generated `journal/index.md`, in every mode.

    The index is read only after every input was clean. Guard 7's own three
    refusals keep their lane and text; every other failure on the output is
    classified like an input read.
    """

    def assert_output_finding(self, fragment: str, before: bytes, broken_mode: int = 0o644) -> None:
        files = tree_files(self.root)
        for mode, args in JOURNAL_MODES:
            with self.subTest(mode=mode):
                r = self.run_cli(*args, stdin=CLEAN_MONTH.encode("utf-8"))
                ctx = f"{mode}: rc={r.returncode} out={self.out(r)!r} err={self.err(r)!r}"
                self.assertEqual(r.returncode, 1, ctx)
                payload = self.payload(r)
                errors = payload["validation_errors"]
                self.assertEqual([e["file"] for e in errors], [REL_INDEX], ctx)
                self.assertIn(fragment, errors[0]["error"], ctx)
                self.assertIn("remove the path and rerun the regenerator", errors[0]["error"], ctx)
                self.assertNotIn(str(self.root), errors[0]["error"], ctx)
                self.assertNotIn(str(self.root.resolve()), errors[0]["error"], ctx)
                self.assertNotIn("Traceback", self.err(r), ctx)
                self.assertEqual(tree_files(self.root), files, f"a file appeared — {ctx}")
                self.index.chmod(0o644)
                self.assertEqual(self.index.read_bytes(), before, f"the output changed — {ctx}")
                self.index.chmod(broken_mode)

    def in_process(self, args=("--dry-run",)):
        gen = load_script("generate-journal-index.py")
        return gen, ["--repo-root", str(self.root), *args]

    def eio_on_index_read(self, gen, seen: list, exc_factory=None):
        real_read = gen._read_regular_file

        def read(path):
            if Path(path).name == "index.md":
                seen.append(path)
                if exc_factory is not None:
                    raise exc_factory(path)
                raise OSError(errno.EIO, "Input/output error", str(path))
            return real_read(path)

        return mock.patch.object(gen, "_read_regular_file", read)


class JournalOutputReadDocumentLaneTests(JournalOutputReadTestCase):
    def test_an_absent_output_reads_as_empty_in_every_mode(self):
        self.control()
        self.index.unlink()
        r = self.run_cli("--dry-run")
        self.assertEqual(r.returncode, 1, self.err(r))
        self.assertEqual(self.payload(r), {"drift": True, "path": REL_INDEX})
        self.assertFalse(self.index.exists(), "the dry run created the output")
        r = self.run_cli("--check-stdin", "--month", "2026-08", stdin=CLEAN_MONTH.encode("utf-8"))
        self.assertEqual(r.returncode, 0, self.err(r))
        self.assertFalse(self.index.exists(), "the preflight created the output")
        r = self.run_cli()
        self.assertEqual(r.returncode, 0, self.err(r))
        self.assertTrue(self.index.is_file())

    def test_an_output_the_process_cannot_open_is_a_document_finding(self):
        before = self.control()
        skip_if_root(self)
        self.index.chmod(0o000)
        self.addCleanup(self.index.chmod, 0o644)
        self.assert_output_finding("EACCES", before, broken_mode=0o000)

    def test_an_output_that_is_not_utf8_is_a_document_finding(self):
        index = self.control()
        broken = index.replace(OTHER_MONTH.encode("utf-8"), b"2026-\xff07", 1)
        self.index.write_bytes(broken)
        self.assert_output_finding("not valid UTF-8", broken)

    def test_a_directory_at_the_output_path_keeps_guard_seven_text(self):
        self.control()
        self.index.unlink()
        self.index.mkdir()
        files = tree_files(self.root)
        for mode, args in JOURNAL_MODES:
            with self.subTest(mode=mode):
                r = self.run_cli(*args, stdin=CLEAN_MONTH.encode("utf-8"))
                ctx = f"{mode}: rc={r.returncode} out={self.out(r)!r} err={self.err(r)!r}"
                self.assertEqual(r.returncode, 1, ctx)
                errors = self.payload(r)["validation_errors"]
                self.assertEqual(errors, [{"file": REL_INDEX,
                                           "error": f"{REL_INDEX} exists and is not a regular file"}],
                                 ctx)
                self.assertTrue(self.index.is_dir(), ctx)
                self.assertEqual(tree_files(self.root), files, f"a file appeared — {ctx}")

    def test_a_path_attributable_lstat_failure_is_a_document_finding(self):
        # Guard 7's own `lstat` is classified: EACCES is at the path. The walk
        # lstats index.md through `os.lstat`, so the stub reaches guard 7 only.
        self.control()
        gen, argv = self.in_process()
        real_state = gen.input_lanes.path_state
        rc, out, err = run_main(gen.main, argv)
        self.assertEqual(rc, 0, err)  # POSITIVE CONTROL: unstubbed, no drift
        seen: list = []

        def state(path, follow=True):
            if Path(path).name == "index.md":
                seen.append(path)
                raise PermissionError(errno.EACCES, "Permission denied", str(path))
            return real_state(path, follow)

        before = self.index.read_bytes()
        with mock.patch.object(gen.input_lanes, "path_state", state):
            rc, out, err = run_main(gen.main, argv)
        self.assertTrue(seen, "the stub was never reached")
        self.assertEqual(rc, 1, err)
        errors = json.loads(out)["validation_errors"]
        self.assertEqual([e["file"] for e in errors], [REL_INDEX])
        self.assertIn("EACCES", errors[0]["error"])
        self.assertNotIn(str(self.root.resolve()), errors[0]["error"])
        self.assertEqual(self.index.read_bytes(), before)

    def test_the_containment_refusal_keeps_its_text(self):
        # Guard 4 refuses a symlinked index.md in the walk, so guard 7's
        # containment refusal is the backstop for the window after the walk.
        # The walk is stubbed to model that window.
        self.control()
        gen, argv = self.in_process()
        empty_walk = mock.patch.object(gen, "_walk_journal_dir", lambda d, r: ({}, [], []))
        with empty_walk:  # POSITIVE CONTROL: a real index passes guard 7
            rc, out, err = run_main(gen.main, argv)
        self.assertEqual(rc, 1, err)
        self.assertNotIn("validation_errors", json.loads(out))
        victim = self.outside_victim()
        self.index.unlink()
        self.index.symlink_to(victim)
        with empty_walk:
            rc, out, err = run_main(gen.main, argv)
        self.assertEqual(rc, 1, err)
        errors = json.loads(out)["validation_errors"]
        self.assertEqual([e["file"] for e in errors], [REL_INDEX])
        self.assertIn("which is not contained under", errors[0]["error"])
        self.assertNotIn("remove the path and rerun", errors[0]["error"])
        self.assertEqual(victim.read_text(encoding="utf-8"), WITNESS)


class JournalOutputReadProcessLevelTests(JournalOutputReadTestCase):
    def assert_environment_lane(self, gen, argv, patch_factory, fragment: str) -> None:
        # POSITIVE CONTROL: unstubbed, the same fixture runs clean.
        rc, out, err = run_main(gen.main, argv)
        self.assertEqual(rc, 0, err)
        before = self.index.read_bytes()
        files = tree_files(self.root)
        seen: list = []
        with patch_factory(seen):
            rc, out, err = run_main(gen.main, argv)
        self.assertTrue(seen, "the stub was never reached")
        self.assertEqual(rc, 2, err)
        self.assertEqual(out, "")
        self.assertIn(f"environment failure: {REL_INDEX}", err)
        self.assertIn(fragment, err)
        self.assertEqual(self.index.read_bytes(), before)
        self.assertEqual(tree_files(self.root), files)

    def test_eio_on_the_output_read_takes_the_environment_lane_in_every_mode(self):
        self.control()
        for mode, args in JOURNAL_MODES:
            if mode == "check-stdin":
                continue  # stdin is the process's own; driven by subprocess below
            with self.subTest(mode=mode):
                gen, argv = self.in_process(args)
                self.assert_environment_lane(
                    gen, argv, lambda seen: self.eio_on_index_read(gen, seen),
                    "Input/output error")

    def test_eio_on_the_output_read_takes_the_environment_lane_under_check_stdin(self):
        self.control()
        gen, argv = self.in_process(("--check-stdin", "--month", "2026-08"))

        def run(seen):
            stack = contextlib.ExitStack()
            stack.enter_context(self.eio_on_index_read(gen, seen))
            stdin = io.TextIOWrapper(io.BytesIO(CLEAN_MONTH.encode("utf-8")), encoding="utf-8")
            stack.enter_context(mock.patch.object(sys, "stdin", stdin))
            return stack

        # The positive control inside assert_environment_lane reads stdin
        # once; give it its own stream.
        with mock.patch.object(sys, "stdin", io.TextIOWrapper(
                io.BytesIO(CLEAN_MONTH.encode("utf-8")), encoding="utf-8")):
            rc, out, err = run_main(gen.main, argv)
        self.assertEqual(rc, 0, err)
        before = self.index.read_bytes()
        seen: list = []
        with run(seen):
            rc, out, err = run_main(gen.main, argv)
        self.assertTrue(seen)
        self.assertEqual(rc, 2, err)
        self.assertEqual(out, "")
        self.assertIn(f"environment failure: {REL_INDEX}", err)
        self.assertEqual(self.index.read_bytes(), before)

    def test_a_memory_error_on_the_output_read_takes_the_environment_lane(self):
        self.control()
        gen, argv = self.in_process()
        self.assert_environment_lane(
            gen, argv,
            lambda seen: self.eio_on_index_read(gen, seen, lambda path: MemoryError()),
            "MemoryError")

    def test_eio_on_guard_seven_lstat_takes_the_environment_lane(self):
        self.control()
        gen, argv = self.in_process()
        real_state = gen.input_lanes.path_state

        def patch(seen):
            def state(path, follow=True):
                if Path(path).name == "index.md":
                    seen.append(path)
                    raise OSError(errno.EIO, "Input/output error", str(path))
                return real_state(path, follow)
            return mock.patch.object(gen.input_lanes, "path_state", state)

        self.assert_environment_lane(gen, argv, patch, "Input/output error")

    def test_an_input_finding_leaves_the_output_unread(self):
        # The order: a run that refuses on its inputs never reads its output.
        self.control()
        gen, argv = self.in_process()
        bad = self.journal / "notes.md"  # outside the month-file grammar
        bad.write_text("x\n", encoding="utf-8")
        seen: list = []
        with self.eio_on_index_read(gen, seen):
            rc, out, err = run_main(gen.main, argv)
        self.assertEqual(rc, 1, err)
        self.assertEqual([e["file"] for e in json.loads(out)["validation_errors"]],
                         [str(Path(REL_INDEX).with_name("notes.md"))])
        self.assertEqual(seen, [], "the output was read after an input refused")
        # POSITIVE CONTROL: clean inputs, the same stub is reached and takes exit 2.
        bad.unlink()
        with self.eio_on_index_read(gen, seen):
            rc, out, err = run_main(gen.main, argv)
        self.assertEqual(rc, 2, err)
        self.assertTrue(seen)


# ═══════════════════════════════════════════════════════════════════════════
# generate-log-summary.py
# ═══════════════════════════════════════════════════════════════════════════

from test_generate_log_summary import GEN, SEPT, SummaryCase, detail  # noqa: E402

SUMMARY_MODES = (("write", ()), ("dry-run", ("--dry-run",)))


class LogSummaryInputLaneTestCase(SummaryCase):
    """The settled month 2026-09 is the input each case breaks; the control proves it is read."""

    REL_TARGET = "docs/log/2026-09.md"

    def setUp(self) -> None:
        super().setUp()
        self.tree_with(**{"2026-08": SEPT.replace("2026-09", "2026-08"), "2026-09": SEPT})
        self.target = self.log_dir / "2026-09.md"

    def control(self) -> bytes:
        """POSITIVE CONTROL: the catch-up writes a region for 2026-09 and the gate passes."""
        code, payload, err = self.catch_up()
        self.assertEqual(code, 0, err)
        self.assertEqual(self.gate()[0], 0)
        summary = self.summary.read_bytes()
        self.assertIn(b"## 2026-09", summary)
        return summary

    def assert_document_lane(self, reason_fragment: str) -> None:
        before = self.summary.read_bytes()
        files = tree_files(self.root)
        for mode, args in SUMMARY_MODES:
            with self.subTest(mode=mode):
                code, payload, err = self.run_gen(*args)
                ctx = f"{mode}: rc={code} out={payload!r} err={err!r}"
                self.assertEqual(code, 1, ctx)
                errors = payload["validation_errors"]
                self.assertEqual([e["file"] for e in errors], [self.REL_TARGET], ctx)
                self.assertIn(reason_fragment, errors[0]["error"], ctx)
                self.assertNotIn(str(self.root), errors[0]["error"], ctx)
                self.assertEqual(self.summary.read_bytes(), before, ctx)
                self.assertEqual(tree_files(self.root), files, f"a file appeared — {ctx}")

    def assert_environment_lane(self) -> None:
        for mode, args in SUMMARY_MODES:
            with self.subTest(mode=mode):
                files = tree_files(self.root)
                command = [sys.executable, str(GEN), "--repo-root", str(self.root), "--today",
                           "2026-11-11", *args]
                import subprocess
                done = subprocess.run(command, capture_output=True, text=True)
                ctx = f"{mode}: rc={done.returncode} out={done.stdout!r} err={done.stderr!r}"
                self.assertEqual(done.returncode, 2, ctx)
                self.assertEqual(done.stdout, "", ctx)
                # The log directory by its repository-relative path, not the
                # bare word "log", which the script name also carries.
                self.assertIn("environment failure: docs/log: ", done.stderr, ctx)
                self.assertEqual(tree_files(self.root), files, f"a file appeared — {ctx}")


class LogSummaryDanglingLinkTests(LogSummaryInputLaneTestCase):
    def test_a_listed_detail_file_whose_link_target_is_absent_is_a_document_finding(self):
        self.control()
        real = self.root / "elsewhere.md"
        self.target.rename(real)
        self.target.symlink_to(real)
        real.unlink()
        self.assertTrue(self.target.is_symlink())
        self.assert_document_lane("ELOOP")


class LogSummaryUnopenableTests(LogSummaryInputLaneTestCase):
    def test_a_detail_file_the_process_cannot_open_is_a_document_finding(self):
        self.control()
        skip_if_root(self)
        self.target.chmod(0o000)
        self.addCleanup(self.target.chmod, 0o644)
        self.assert_document_lane("EACCES")


class LogSummaryNotUtf8Tests(LogSummaryInputLaneTestCase):
    def test_a_detail_file_that_is_not_utf8_is_a_document_finding(self):
        self.control()
        self.target.write_bytes(self.target.read_bytes().replace(b"Asked", b"As\xffked"))
        self.assert_document_lane("not valid UTF-8")


class LogSummaryUnlistableDirectoryTests(LogSummaryInputLaneTestCase):
    def test_an_unlistable_log_directory_is_an_environment_failure(self):
        summary = self.control()
        skip_if_root(self)
        self.log_dir.chmod(0o000)
        self.addCleanup(self.log_dir.chmod, 0o755)
        self.assert_environment_lane()
        self.log_dir.chmod(0o755)
        self.assertEqual(self.summary.read_bytes(), summary)

    def test_a_regular_file_at_the_log_path_is_an_environment_failure(self):
        self.control()
        for path in self.log_dir.iterdir():
            path.unlink()
        self.log_dir.rmdir()
        self.log_dir.write_text("not a directory\n", encoding="utf-8")
        self.assert_environment_lane()


class LogSummaryProcessLevelFailureTests(LogSummaryInputLaneTestCase):
    """EIO on one month takes the environment lane and names the finding beside it."""

    def test_eio_takes_the_environment_lane_over_a_document_finding(self):
        self.control()
        other = self.log_dir / "2026-08.md"
        other.write_bytes(other.read_bytes() + b"\xff\n")
        gen = load_script("generate-log-summary.py")
        argv = ["--repo-root", str(self.root), "--dry-run", "--today", "2026-11-11"]
        # POSITIVE CONTROL: unstubbed, the same fixture is a document finding on 2026-08.
        rc, out, _ = run_main(gen.main, argv)
        self.assertEqual(rc, 1)
        self.assertEqual([e["file"] for e in json.loads(out)["validation_errors"]], ["docs/log/2026-08.md"])

        real_read = gen.ol._read_log_input

        def read(directory_fd, name):
            if name == self.target.name:
                raise OSError(errno.EIO, "Input/output error")
            return real_read(directory_fd, name)

        before = self.summary.read_bytes()
        with mock.patch.object(gen.ol, "_read_log_input", read):
            rc, out, err = run_main(gen.main, argv)
        self.assertEqual(rc, 2, err)
        self.assertEqual(out, "")
        self.assertIn(self.REL_TARGET, err)
        self.assertIn("Input/output error", err)
        self.assertIn("docs/log/2026-08.md", err)
        self.assertEqual(self.summary.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
