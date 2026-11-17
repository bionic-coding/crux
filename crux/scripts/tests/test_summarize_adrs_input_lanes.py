"""summarize-adrs.py: each failed read of an ADR-tier input takes its lane.

THE CONTRACT. A listed ADR the process cannot stat, open, read or decode for
a cause attributable to its path is a DOCUMENT-lane finding: exit 1, a
`validation_errors` entry naming the ADR by its repository-relative path,
with no absolute path in the reason, and every output byte-unchanged. A cause
in the process or host (EIO), an adrs or archive directory that cannot be
listed, and a listed link that escapes the tree take the ENVIRONMENT lane:
exit 2, nothing on stdout, and stderr naming the input and every document
finding the same run met. The input census decides this before the authority
proof or the build reads any input.

Every refusal runs on a fixture its positive control just ran clean on, in
write mode and in --dry-run, removes one output first and asserts no output
reappears, and asserts every remaining output byte-unchanged. A
permission-based test skips when the effective uid is 0, because root reads a
mode-000 path.

Run:
  uv run python3 -m unittest discover -s crux/scripts/tests -p 'test_summarize_adrs_input_lanes.py'
"""

from __future__ import annotations

import builtins
import contextlib
import errno
import importlib.util
import io
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TESTS = Path(__file__).resolve().parent
SCRIPTS = TESTS.parent
sys.path.insert(0, str(SCRIPTS))

import input_lanes  # noqa: E402
import summaries_projection as sp  # noqa: E402


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SA = _load("summarize_adrs_input_lanes", "summarize-adrs.py")
MODES = (("write", ()), ("dry-run", ("--dry-run",)))
OUTPUTS = ("rule-table.md", "resolver.json", "implementation-map.md", "_meta.json")


def skip_if_root(case: unittest.TestCase) -> None:
    if os.geteuid() == 0:
        case.skipTest("running as root: a mode-000 path is still readable")


def adr(num: int, *, status: str = "Accepted") -> str:
    return "\n".join([
        "---", f"id: ADR-{num:04d}", f'title: "Decision {num}"', f"status: {status}",
        "date: 2026-08-01", "proposed_date: 2026-08-01", "accepted_date: 2026-08-01",
        "supersedes: []", "superseded_by: null", "tags: [test]", "governs:",
        f"  - handle: ADR-{num:04d}/rule-{num}", "    domain: alpha",
        f'    rule: "Rule {num} holds."', "    scope: crux/scripts", "    provenance: authored",
        "---", "", f"# ADR-{num:04d}", "", "Body.", ""])


def tree_files(root: Path) -> set[str]:
    """Every path under `root`, relative, without following links or failing on a locked directory."""
    out = set()
    for directory, dirs, files in os.walk(root, onerror=lambda exc: None):
        for name in dirs + files:
            out.add(str((Path(directory) / name).relative_to(root)))
    return out


class SummarizeInputLaneTestCase(unittest.TestCase):
    """ADR-0903 is the input each case breaks; the control proves it is read.

    The driver is a class attribute, so a subclass runs the same cases
    against another regenerator that shares the census: `DRIVER` names its
    census driver, `MODULE` the loaded script, `SCRIPT_PATH` the file a
    child process runs, and `OUTPUT_SUBDIR`, `OUTPUT_NAMES`,
    `REMOVED_OUTPUT` and `CONTROL_OUTPUT` its outputs under adrs/.
    """

    DRIVER = "summarize-adrs"
    MODULE = SA
    SCRIPT_PATH = SCRIPTS / "summarize-adrs.py"
    OUTPUT_SUBDIR = "summaries"
    OUTPUT_NAMES = OUTPUTS
    #: The output each refusal removes first, to show no refusal recreates it.
    REMOVED_OUTPUT = "implementation-map.md"
    #: The output the positive control reads ADR-0903's rule from.
    CONTROL_OUTPUT = "resolver.json"
    #: The destination preflight's refusal of a non-regular output path.
    DESTINATION_REFUSAL = "summaries destination is symlinked or has an owned temporary path"

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        (self.root / ".bionic.yml").write_text("docs_dir: bionic\n", encoding="utf-8")
        self.tree = self.root / "bionic"
        self.adrs = self.tree / "adrs"
        self.adrs.mkdir(parents=True)
        (self.tree / "promptbooks" / "runs").mkdir(parents=True)
        self.manifest = self.tree / "manifest.yml"
        self.manifest.write_text(
            'schema_version: "5"\nconcerns_enabled:\n  - adrs\n'
            "adr:\n  next_number: 1000\n  governs_from: 1\n", encoding="utf-8")
        for num in (901, 902):
            (self.adrs / f"ADR-{num:04d}-x.md").write_text(adr(num), encoding="utf-8")
        self.target = self.adrs / "ADR-0903-x.md"
        self.target.write_text(adr(903), encoding="utf-8")
        self.summaries = self.adrs / "summaries"

    # ── running ──────────────────────────────────────────────────────────

    def run_sa(self, *args: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = self.MODULE.main(["--repo-root", str(self.root), *args])
        return rc, out.getvalue(), err.getvalue()

    def rel(self, path: Path) -> str:
        return str(path.relative_to(self.root))

    @property
    def output_dir(self) -> Path:
        return self.adrs / self.OUTPUT_SUBDIR

    def prime(self) -> None:
        """POSITIVE CONTROL: regenerate, then the same fixture is clean under --dry-run."""
        rc, out, err = self.run_sa()
        self.assertEqual(rc, 0, f"regenerate: {out!r} {err!r}")
        rc, out, err = self.run_sa("--dry-run")
        self.assertEqual(rc, 0, f"control: {out!r} {err!r}")
        self.assertEqual(json.loads(out), {"drift": False, "paths": []})
        self.assertIn("ADR-0903/rule-903", (self.output_dir / self.CONTROL_OUTPUT).read_text())

    def outputs(self) -> dict[str, bytes]:
        return {name: (self.output_dir / name).read_bytes() for name in self.OUTPUT_NAMES
                if (self.output_dir / name).exists()}

    def assert_no_absolute_path(self, text: str, ctx: str) -> None:
        self.assertNotIn(str(self.root), text, ctx)
        self.assertNotIn(os.path.realpath(self.root), text, ctx)

    # ── lanes ────────────────────────────────────────────────────────────

    def refusal_runs(self, check, *, locked: Path | None = None, lock_mode: int = 0o000):
        """Run each mode and `check(rc, out, err, ctx)`; outputs stay unchanged and none is created."""
        gone = self.output_dir / self.REMOVED_OUTPUT
        gone.unlink(missing_ok=True)
        before = self.outputs()
        for mode, args in MODES:
            with self.subTest(mode=mode):
                files = tree_files(self.root)
                if locked is not None:
                    locked.chmod(lock_mode)
                try:
                    rc, out, err = self.run_sa(*args)
                finally:
                    if locked is not None:
                        locked.chmod(0o755)
                ctx = f"{mode}: rc={rc} out={out!r} err={err!r}"
                check(rc, out, err, ctx)
                self.assertEqual(self.outputs(), before, f"an output changed — {ctx}")
                self.assertFalse(gone.exists(), f"an absent output was created — {ctx}")
                self.assertEqual(tree_files(self.root), files, f"a file appeared — {ctx}")

    def assert_document_lane(self, findings: dict[str, str], **kw) -> None:
        def check(rc, out, err, ctx):
            self.assertEqual(rc, 1, ctx)
            payload = json.loads(out)
            self.assertEqual(set(payload), {"validation_errors"}, ctx)
            errors = payload["validation_errors"]
            self.assertEqual(sorted(e["file"] for e in errors), sorted(findings), ctx)
            for entry in errors:
                self.assertIn(findings[entry["file"]], entry["error"], ctx)
                self.assert_no_absolute_path(entry["error"], ctx)
        self.refusal_runs(check, **kw)

    def assert_environment_lane(self, named: list[str], **kw) -> None:
        def check(rc, out, err, ctx):
            self.assertEqual(rc, 2, ctx)
            self.assertEqual(out, "", ctx)
            for text in named:
                self.assertIn(text, err, ctx)
        self.refusal_runs(check, **kw)


# ═══════════════════════════════════════════════════════════════════════════
# The document lane: a listed ADR the process cannot read
# ═══════════════════════════════════════════════════════════════════════════

class ListedAdrDocumentLaneTests(SummarizeInputLaneTestCase):
    def test_a_listed_adr_whose_link_target_is_absent_is_a_finding(self):
        held = self.adrs / "held-0903.txt"
        self.target.rename(held)
        self.target.symlink_to(held.name)
        self.prime()
        held.unlink()
        self.assertTrue(self.target.is_symlink())
        self.assert_document_lane({self.rel(self.target): "ENOENT"})

    def test_an_adr_the_process_cannot_open_is_a_finding(self):
        self.prime()
        skip_if_root(self)
        self.target.chmod(0o000)
        self.addCleanup(self.target.chmod, 0o644)
        self.assert_document_lane({self.rel(self.target): "EACCES"})

    def test_an_adr_that_is_not_utf8_is_a_finding(self):
        self.prime()
        self.target.write_bytes(adr(903).encode("utf-8").replace(b"Body.", b"Body \xff."))
        self.assert_document_lane({self.rel(self.target): "not valid UTF-8"})

    def test_a_directory_named_like_an_adr_is_a_finding(self):
        self.prime()
        directory = self.adrs / "ADR-0904-dir.md"
        directory.mkdir()
        self.assert_document_lane({self.rel(directory): "EISDIR"})

    def test_a_listed_symbolic_link_loop_is_an_eloop_finding_not_a_containment_refusal(self):
        self.prime()
        loop = self.adrs / "ADR-0904-loop.md"
        loop.symlink_to(loop.name)
        self.assert_document_lane({self.rel(loop): "ELOOP"})

    def test_every_unreadable_adr_is_named_in_one_payload(self):
        self.prime()
        other = self.adrs / "ADR-0902-x.md"
        other.write_bytes(b"\xff\n")
        loop = self.adrs / "ADR-0904-loop.md"
        loop.symlink_to(loop.name)
        self.target.write_bytes(b"---\n\xfe\n")
        self.assert_document_lane({self.rel(other): "not valid UTF-8",
                                   self.rel(loop): "ELOOP",
                                   self.rel(self.target): "not valid UTF-8"})


# ═══════════════════════════════════════════════════════════════════════════
# The environment lane: containment, unlistable tiers, process-level causes
# ═══════════════════════════════════════════════════════════════════════════

class ContainmentTests(SummarizeInputLaneTestCase):
    def test_a_tree_escaping_link_keeps_its_refusal_beside_another_finding(self):
        outside = self.root / "outside-0904.md"
        outside.write_text(adr(904), encoding="utf-8")
        self.prime()
        escape = self.adrs / "ADR-0904-out.md"
        escape.symlink_to(outside)
        self.target.write_bytes(b"---\n\xff\n")
        self.assert_environment_lane([
            "refusing to read ADR-0904-out.md: it does not resolve to a file inside",
            "never through a link out of it",
            f"document finding met in the same run: {self.rel(self.target)}"])

    def test_the_containment_refusal_alone_keeps_exit_two(self):
        # The refusal's lane and words are unchanged by the census.
        outside = self.root / "outside-0904.md"
        outside.write_text(adr(904), encoding="utf-8")
        self.prime()
        (self.adrs / "ADR-0904-out.md").symlink_to(outside)
        self.assert_environment_lane(["ValueError: refusing to read ADR-0904-out.md"])


class UnlistableTierTests(SummarizeInputLaneTestCase):
    def test_an_unlistable_adrs_directory_is_an_environment_failure(self):
        self.prime()
        skip_if_root(self)
        self.assert_environment_lane([f"environment failure: {self.rel(self.adrs)}"],
                                     locked=self.adrs, lock_mode=0o300)

    def test_an_unlistable_archive_is_an_environment_failure(self):
        archive = self.adrs / "archive"
        archive.mkdir()
        (archive / "ADR-0905-old.md").write_text(adr(905, status="Superseded"), encoding="utf-8")
        self.prime()
        skip_if_root(self)
        self.assert_environment_lane([f"environment failure: {self.rel(archive)}"],
                                     locked=archive)

    def test_a_regular_file_at_the_archive_path_is_an_environment_failure(self):
        self.prime()
        archive = self.adrs / "archive"
        archive.write_text("not a directory\n", encoding="utf-8")
        self.assert_environment_lane([f"environment failure: {self.rel(archive)}",
                                      "NotADirectoryError"])

    def test_a_confirmed_absent_adrs_directory_keeps_its_not_found_text(self):
        self.prime()
        moved = self.root / "moved-adrs"
        self.adrs.rename(moved)
        for mode, args in MODES:
            with self.subTest(mode=mode):
                files = tree_files(self.root)
                rc, out, err = self.run_sa(*args)
                self.assertEqual(rc, 2, err)
                self.assertEqual(out, "")
                self.assertIn(f"FileNotFoundError: {self.adrs} not found", err)
                self.assertEqual(tree_files(self.root), files)


class ProcessLevelPrecedenceTests(SummarizeInputLaneTestCase):
    """EIO on one ADR takes the environment lane and names the other ADR's finding."""

    def test_eio_takes_the_environment_lane_over_a_document_finding(self):
        self.prime()
        skip_if_root(self)
        other = self.adrs / "ADR-0902-x.md"
        other.chmod(0o000)
        self.addCleanup(other.chmod, 0o644)
        # POSITIVE CONTROL: unstubbed, the same fixture is a document finding.
        rc, out, _ = self.run_sa("--dry-run")
        self.assertEqual(rc, 1)
        self.assertEqual([e["file"] for e in json.loads(out)["validation_errors"]],
                         [self.rel(other)])
        seen = []

        def fake_open(file, *a, **kw):
            if Path(os.fsdecode(file)).name == self.target.name:
                seen.append(file)
                raise OSError(errno.EIO, "Input/output error", str(file))
            return builtins.open(file, *a, **kw)

        with mock.patch.object(sp, "open", fake_open, create=True):
            self.assert_environment_lane([
                f"environment failure: {self.rel(self.target)}", "Input/output error",
                f"document finding met in the same run: {self.rel(other)}"])
        self.assertTrue(seen, "the stub was never reached")


class LateFailureTests(SummarizeInputLaneTestCase):
    """A build read that fails after a clean census is classified, not a crash."""

    def stub_read_text(self, code: int, seen: list):
        real = Path.read_text
        target = self.target

        def read_text(path, *a, **kw):
            if Path(path) == target:
                seen.append(path)
                raise OSError(code, os.strerror(code), str(path))
            return real(path, *a, **kw)
        return mock.patch.object(Path, "read_text", read_text)

    def test_a_late_eacces_on_a_listed_adr_is_a_finding_naming_it(self):
        self.prime()
        seen: list = []
        with self.stub_read_text(errno.EACCES, seen):
            self.assert_document_lane({self.rel(self.target): "EACCES"})
        self.assertTrue(seen, "the build's read was never reached")

    def test_a_late_eio_on_a_listed_adr_takes_the_environment_lane(self):
        self.prime()
        seen: list = []
        with self.stub_read_text(errno.EIO, seen):
            self.assert_environment_lane([f"environment failure: {self.rel(self.target)}"])
        self.assertTrue(seen, "the build's read was never reached")


class ManifestCensusTests(SummarizeInputLaneTestCase):
    def test_an_unreadable_manifest_skips_the_adrs_required_decision(self):
        self.prime()
        moved = self.root / "moved-adrs"
        self.adrs.rename(moved)
        # POSITIVE CONTROL: a readable manifest with no adrs directory is "not found".
        rc, out, err = self.run_sa("--dry-run")
        self.assertEqual(rc, 2, err)
        self.assertIn("not found", err)
        skip_if_root(self)
        self.manifest.chmod(0o000)
        self.addCleanup(self.manifest.chmod, 0o644)
        for mode, args in MODES:
            with self.subTest(mode=mode):
                rc, out, err = self.run_sa(*args)
                self.assertEqual(rc, 1, err)
                errors = json.loads(out)["validation_errors"]
                self.assertEqual([e["file"] for e in errors], [self.rel(self.manifest)])
                self.assertIn("EACCES", errors[0]["error"])
                self.assertNotIn("not found", err)

    def test_a_dangling_link_at_the_manifest_takes_the_environment_lane(self):
        """Positive control: prime() runs the same fixture clean before the link dangles."""
        # The migration proof refuses a symlinked manifest, so the control
        # runs on the regular file and the link replaces it afterwards.
        self.prime()
        self.manifest.unlink()
        self.manifest.symlink_to("held-manifest.yml")
        self.assertFalse(self.manifest.exists())
        self.assert_environment_lane([f"environment failure: {self.rel(self.manifest)}",
                                      "symbolic link whose target is missing"])


# ═══════════════════════════════════════════════════════════════════════════
# The --dry-run output read: after the input decision, in its own lane
# ═══════════════════════════════════════════════════════════════════════════

class OutputReadTests(SummarizeInputLaneTestCase):
    def setUp(self) -> None:
        super().setUp()
        # The one output the migration proof never reads, so its read is this driver's.
        self.output = self.output_dir / self.REMOVED_OUTPUT

    def test_an_absent_output_reads_as_empty(self):
        self.prime()
        self.output.unlink()
        rc, out, err = self.run_sa("--dry-run")
        self.assertEqual(rc, 1, err)
        self.assertEqual(json.loads(out), {"drift": True, "paths": [self.rel(self.output)]})
        self.assertFalse(self.output.exists())

    def assert_output_finding(self, fragment: str) -> None:
        files = tree_files(self.root)
        rc, out, err = self.run_sa("--dry-run")
        self.assertEqual(rc, 1, err)
        errors = json.loads(out)["validation_errors"]
        self.assertEqual([e["file"] for e in errors], [self.rel(self.output)])
        self.assertIn(fragment, errors[0]["error"])
        self.assertIn("rerun the regenerator", errors[0]["error"])
        self.assert_no_absolute_path(errors[0]["error"], err)
        self.assertEqual(tree_files(self.root), files)

    def test_an_output_the_process_cannot_open_is_a_finding(self):
        self.prime()
        skip_if_root(self)
        self.output.chmod(0o000)
        self.addCleanup(self.output.chmod, 0o644)
        self.assert_output_finding("EACCES")

    def test_an_output_that_is_not_utf8_is_a_finding(self):
        self.prime()
        self.output.write_bytes(b"\xff{}\n")
        self.assert_output_finding("not valid UTF-8")

    def test_a_directory_at_the_output_path_keeps_the_destination_refusal(self):
        # The destination preflight runs in the read phase of both modes and
        # refuses a non-regular destination before any output is read; its
        # lane (exit 2) and its words are unchanged.
        self.prime()
        self.output.unlink()
        self.output.mkdir()
        for mode, args in MODES:
            with self.subTest(mode=mode):
                rc, out, err = self.run_sa(*args)
                self.assertEqual(rc, 2, err)
                self.assertEqual(out, "")
                self.assertIn(self.DESTINATION_REFUSAL, err)
                self.assertTrue(self.output.is_dir())

    def stub_output_eio(self, seen: list):
        real = Path.read_text
        output = self.output

        def read_text(path, *a, **kw):
            if Path(path) == output:
                seen.append(path)
                raise OSError(errno.EIO, "Input/output error", str(path))
            return real(path, *a, **kw)
        return mock.patch.object(Path, "read_text", read_text)

    def test_eio_on_the_output_read_takes_the_environment_lane(self):
        self.prime()
        seen: list = []
        before = self.outputs()
        with self.stub_output_eio(seen):
            rc, out, err = self.run_sa("--dry-run")
        self.assertEqual(rc, 2, err)
        self.assertEqual(out, "")
        self.assertIn(f"environment failure: {self.rel(self.output)}", err)
        self.assertTrue(seen, "the stub was never reached")
        self.assertEqual(self.outputs(), before)

    def test_an_input_finding_leaves_the_output_unread(self):
        self.prime()
        # POSITIVE CONTROL: clean inputs, the same stub is reached and takes exit 2.
        seen: list = []
        with self.stub_output_eio(seen):
            rc, _, _ = self.run_sa("--dry-run")
        self.assertEqual(rc, 2)
        self.assertTrue(seen)
        self.target.write_bytes(b"---\n\xff\n")
        seen.clear()
        with self.stub_output_eio(seen):
            rc, out, err = self.run_sa("--dry-run")
        self.assertEqual(rc, 1, err)
        self.assertEqual([e["file"] for e in json.loads(out)["validation_errors"]],
                         [self.rel(self.target)])
        self.assertEqual(seen, [], "the output was read after an input finding")


# ═══════════════════════════════════════════════════════════════════════════
# The strict default helpers and the census's own shape
# ═══════════════════════════════════════════════════════════════════════════

class StrictHelperTests(unittest.TestCase):
    """The unseamed helpers decide by the operating system's answer."""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.dir = self.root / "inputs"
        self.dir.mkdir()
        self.file = self.dir / "a.md"
        self.file.write_text("a\n", encoding="utf-8")
        (self.dir / ".hidden.md").write_text("h\n", encoding="utf-8")

    def lock(self, path: Path, mode: int) -> None:
        skip_if_root(self)
        path.chmod(mode)
        self.addCleanup(path.chmod, 0o755)

    def test_present_and_absent_paths_answer_as_before(self):
        self.assertTrue(sp._source_is_file(self.file, None))
        self.assertFalse(sp._source_is_dir(self.file, None))
        self.assertTrue(sp._source_is_dir(self.dir, None))
        self.assertTrue(sp._source_exists(self.file, None))
        for absent in (self.dir / "missing.md", self.file / "child.md"):
            with self.subTest(absent=absent.name):
                self.assertFalse(sp._source_is_file(absent, None))
                self.assertFalse(sp._source_is_dir(absent, None))
                self.assertFalse(sp._source_exists(absent, None))
        self.assertEqual(sorted(p.name for p in sp._source_glob(self.dir, "*.md", None)),
                         sorted(p.name for p in self.dir.glob("*.md")))
        self.assertEqual(sp._source_glob(self.dir / "missing", "*.md", None), [])

    def test_a_file_under_an_unsearchable_parent_raises_rather_than_reading_as_absent(self):
        self.lock(self.dir, 0o600)
        for helper in (sp._source_is_file, sp._source_is_dir, sp._source_exists):
            with self.subTest(helper=helper.__name__):
                with self.assertRaises(PermissionError):
                    helper(self.file, None)

    def test_an_unlistable_directory_raises_rather_than_globbing_empty(self):
        self.lock(self.dir, 0o000)
        with self.assertRaises(PermissionError) as cm:
            sp._source_glob(self.dir, "*.md", None)
        self.assertEqual(Path(cm.exception.filename), self.dir)

    def test_a_regular_file_at_a_directory_path_raises_rather_than_globbing_empty(self):
        with self.assertRaises(NotADirectoryError):
            sp._source_glob(self.file, "*.md", None)

    def test_a_multi_component_pattern_is_refused(self):
        for pattern in ("*/run-*.yaml", "**", "a/*.md"):
            with self.subTest(pattern=pattern):
                with self.assertRaises(ValueError):
                    sp._source_glob(self.dir, pattern, None)

    def test_a_symbolic_link_loop_raises_eloop(self):
        loop = self.dir / "loop.md"
        loop.symlink_to(loop.name)
        with self.assertRaises(OSError) as cm:
            sp._source_is_file(loop, None)
        self.assertEqual(cm.exception.errno, errno.ELOOP)


class CensusShapeTests(SummarizeInputLaneTestCase):
    def test_a_clean_tree_has_no_finding_and_records_each_member_kind(self):
        archive = self.adrs / "archive"
        archive.mkdir()
        (archive / "ADR-0905-old.md").write_text(adr(905, status="Superseded"), encoding="utf-8")
        census = sp.input_census(self.root, driver=self.DRIVER)
        self.assertEqual((census.findings, census.failures), ([], []))
        census.refuse()
        members = dict(census.members)
        self.assertEqual(members["bionic/manifest.yml"], "read")
        self.assertEqual(members["bionic/adrs"], "list")
        self.assertEqual(members["bionic/adrs/ADR-0903-x.md"], "read")
        self.assertEqual(members["bionic/adrs/archive"], "list")
        self.assertEqual(members["bionic/adrs/archive/ADR-0905-old.md"], "read")

    def test_an_unknown_driver_is_refused(self):
        with self.assertRaises(ValueError):
            sp.input_census(self.root, driver="derive-arch")

    def test_a_fifo_named_like_an_adr_is_an_environment_failure_and_is_never_opened(self):
        fifo = self.adrs / "ADR-0904-pipe.md"
        os.mkfifo(fifo)
        # POSITIVE CONTROL: the regular-file ADR beside it reads clean.
        census = sp.input_census(self.root, driver=self.DRIVER)
        self.assertEqual(census.findings, [])
        self.assertEqual(len(census.failures), 1)
        self.assertIn("bionic/adrs/ADR-0904-pipe.md: is a FIFO", census.failures[0])
        with self.assertRaises(input_lanes.EnvironmentLaneError):
            census.refuse()
        self.assertTrue(stat.S_ISFIFO(os.lstat(fifo).st_mode))


if __name__ == "__main__":
    unittest.main()
