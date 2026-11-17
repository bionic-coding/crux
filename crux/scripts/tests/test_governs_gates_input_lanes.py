"""lint-governs-references.py and check-governs-coverage.py: each failed read takes its lane.

THE CONTRACT. The two gates share the input census with the summaries
regenerators. Each runs the census for its own driver first.
- An input whose read fails for a cause attributable to its path is a
  DOCUMENT-lane finding: exit 1, a `validation_errors` entry naming the path
  relative to the repository, and no absolute path in the payload.
- A cause in the process or host (EIO), an input directory that cannot be
  listed and a dangling link at an optional file take the ENVIRONMENT lane:
  exit 2, nothing on stdout, stderr naming the input and every finding the
  same run met.
- A read beneath the documentation tree that fails after a clean census is
  classified the same way, before the gate's catch-all.
- The lint's scan: a scan root whose presence cannot be determined, a regular
  file at a scan root and a directory the walk cannot list take the
  environment lane naming the directory. A confirmed-absent root has nothing
  to scan.
- The census misses no read either gate makes, and takes nothing the gate's
  build never touches.

Every refusal runs on a fixture its positive control just ran clean on, and
asserts that no file appeared or changed. A permission-based test skips when
the effective uid is 0.

Run:
  uv run python3 -m unittest discover -s crux/scripts/tests -p 'test_governs_gates_input_lanes.py'
"""

from __future__ import annotations

import builtins
import contextlib
import errno
import hashlib
import importlib.util
import io
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TESTS = Path(__file__).resolve().parent
SCRIPTS = TESTS.parent
for entry in (str(SCRIPTS), str(TESTS)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

import _census_coverage as coverage  # noqa: E402
import _census_fixture as fixture  # noqa: E402
import input_lanes  # noqa: E402
import summaries_projection as sp  # noqa: E402


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


LINT_PATH = SCRIPTS / "lint-governs-references.py"
COVERAGE_PATH = SCRIPTS / "check-governs-coverage.py"
LINT = _load("gates_input_lanes_lint", LINT_PATH)
COVERAGE = _load("gates_input_lanes_coverage", COVERAGE_PATH)
GATES = (("lint-governs-references", LINT), ("check-governs-coverage", COVERAGE))
# The shared census-member module, loaded under a private name so its own
# classes are not collected a second time from this module.
members = _load("_gates_members_base", TESTS / "test_summarize_adrs_census_members.py")
MISSING = "symbolic link whose target is missing"


def skip_if_root(case: unittest.TestCase) -> None:
    if os.geteuid() == 0:
        case.skipTest("running as root: a mode-000 path is still readable")


def tree_digest(root: Path) -> dict[str, str]:
    """Every path under `root` with its content digest, without following links
    or failing on a locked directory or file."""
    out = {}
    for directory, dirs, files in os.walk(root, onerror=lambda exc: None):
        for name in dirs:
            out[str((Path(directory) / name).relative_to(root))] = "dir"
        for name in files:
            path = Path(directory) / name
            try:
                meta = os.lstat(path)
                if stat.S_ISLNK(meta.st_mode):
                    data = os.readlink(path).encode()
                elif stat.S_ISREG(meta.st_mode):
                    data = path.read_bytes()
                else:  # a FIFO or another special file is never opened
                    data = input_lanes.file_kind(meta.st_mode).encode()
                out[str(path.relative_to(root))] = hashlib.sha256(data).hexdigest()
            except OSError:
                out[str(path.relative_to(root))] = "unreadable"
    return out


class GateCase(unittest.TestCase):
    """A small repository: a tree with two Accepted ADRs carrying governs blocks,
    a page beneath the tree and a plugin directory the lint scans."""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        (self.root / ".bionic.yml").write_text("docs_dir: bionic\n", encoding="utf-8")
        self.tree = self.root / "bionic"
        self.adrs = self.tree / "adrs"
        self.adrs.mkdir(parents=True)
        self.manifest = self.tree / "manifest.yml"
        self.manifest.write_text(
            'schema_version: "5"\nconcerns_enabled:\n  - adrs\n'
            "adr:\n  next_number: 1000\n  governs_from: 1\n", encoding="utf-8")
        for num in (901, 902):
            (self.adrs / f"ADR-{num:04d}-x.md").write_text(fixture.adr(num), encoding="utf-8")
        self.adr = self.adrs / "ADR-0902-x.md"
        self.other = self.adrs / "ADR-0901-x.md"
        (self.tree / "notes.md").write_text("A page with no citation.\n", encoding="utf-8")
        self.plugin = self.root / "crux"
        self.skills = self.plugin / "skills" / "fixture"
        self.skills.mkdir(parents=True)
        (self.skills / "SKILL.md").write_text("A surface with no citation.\n", encoding="utf-8")

    def rel(self, path: Path) -> str:
        return str(path.relative_to(self.root))

    def run_gate(self, gate, *args: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = gate.main(["--repo-root", str(self.root), *args])
        return rc, out.getvalue(), err.getvalue()

    def control(self, gate) -> None:
        """POSITIVE CONTROL: the gate runs clean on the fixture as it stands."""
        rc, out, err = self.run_gate(gate)
        self.assertEqual(rc, 0, f"control: {out[:2000]!r} {err!r}")

    def assert_no_absolute_path(self, text: str, ctx: str) -> None:
        self.assertNotIn(str(self.root), text, ctx)
        self.assertNotIn(os.path.realpath(self.root), text, ctx)

    def refusal(self, gate, check, *, locked: Path | None = None) -> None:
        """Run `gate` once and `check(rc, out, err, ctx)`; no file appears or changes."""
        before = tree_digest(self.root)
        if locked is not None:
            mode = locked.stat().st_mode & 0o7777
            self.addCleanup(locked.chmod, mode)
            locked.chmod(0o000)
        try:
            rc, out, err = self.run_gate(gate)
        finally:
            if locked is not None:
                locked.chmod(mode)
        ctx = f"rc={rc} out={out[:2000]!r} err={err!r}"
        check(rc, out, err, ctx)
        self.assertEqual(tree_digest(self.root), before, f"a file appeared or changed — {ctx}")

    def assert_findings(self, gate, rows: dict[str, str], **kw) -> None:
        """Exit 1, and exactly `rows` (file -> error fragment) in `validation_errors`."""
        def check(rc, out, err, ctx):
            self.assertEqual(rc, 1, ctx)
            errors = json.loads(out)["validation_errors"]
            self.assertEqual(sorted(e["file"] for e in errors), sorted(rows), ctx)
            for entry in errors:
                self.assertIn(rows[entry["file"]], entry["error"], ctx)
            self.assert_no_absolute_path(out, ctx)
        self.refusal(gate, check, **kw)

    def assert_environment_lane(self, gate, named: list[str], *, relative: bool = False,
                                **kw) -> None:
        """Exit 2, stdout empty, stderr naming each of `named`. `relative` also holds
        stderr free of absolute paths: the lint's own scan lines carry none, while a
        census line keeps the OSError text the shared census writes."""
        def check(rc, out, err, ctx):
            self.assertEqual((rc, out), (2, ""), ctx)
            for text in named:
                self.assertIn(text, err, ctx)
            if relative:
                self.assert_no_absolute_path(err, ctx)
        self.refusal(gate, check, **kw)


# ═══════════════════════════════════════════════════════════════════════════
# The census lanes, in both gates
# ═══════════════════════════════════════════════════════════════════════════

class CensusLaneTests(GateCase):
    def test_an_unreadable_adr_is_a_validation_error_naming_it(self):
        skip_if_root(self)
        for name, gate in GATES:
            with self.subTest(gate=name):
                self.control(gate)
                self.assert_findings(gate, {self.rel(self.adr): "EACCES"}, locked=self.adr)

    def test_an_adr_that_is_not_utf8_is_a_validation_error_naming_it(self):
        for name, gate in GATES:
            with self.subTest(gate=name):
                self.control(gate)
                text = self.adr.read_bytes()
                self.adr.write_bytes(text.replace(b"Body.", b"Body \xff."))
                try:
                    self.assert_findings(gate, {self.rel(self.adr): "not valid UTF-8"})
                finally:
                    self.adr.write_bytes(text)

    def test_an_unlistable_adrs_directory_takes_the_environment_lane(self):
        skip_if_root(self)
        for name, gate in GATES:
            with self.subTest(gate=name):
                self.control(gate)
                self.assert_environment_lane(
                    gate, [f"{name}: environment failure: bionic/adrs"], locked=self.adrs)

    def test_an_eio_on_one_adr_takes_precedence_over_a_finding_on_another(self):
        skip_if_root(self)
        target = os.fspath(self.other)
        for name, gate in GATES:
            with self.subTest(gate=name):
                self.control(gate)
                seen: list = []

                def fake_open(file, *a, **kw):
                    if os.fspath(file) == target:
                        seen.append(file)
                        raise OSError(errno.EIO, "Input/output error", os.fspath(file))
                    return builtins.open(file, *a, **kw)
                with mock.patch.object(sp, "open", fake_open, create=True):
                    self.assert_environment_lane(gate, [
                        f"environment failure: {self.rel(self.other)}", "Input/output error",
                        f"document finding met in the same run: {self.rel(self.adr)}"],
                        locked=self.adr)
                self.assertTrue(seen, "the stub was never reached")

    def test_a_dangling_link_at_the_reviews_manifest_takes_the_environment_lane(self):
        reviews = self.adrs / "summaries" / "backfill-reviews.yml"
        reviews.parent.mkdir()
        for name, gate in GATES:
            with self.subTest(gate=name):
                # POSITIVE CONTROL: a confirmed-absent reviews manifest is no finding.
                self.control(gate)
                reviews.symlink_to("held-reviews.yml")
                try:
                    self.assert_environment_lane(
                        gate, [f"bionic/adrs/summaries/backfill-reviews.yml: is a {MISSING}"])
                finally:
                    reviews.unlink()


class LateFailureTests(GateCase):
    """anthropic_top:F1: a build read that fails after a clean census is classified
    before the gate's catch-all, not reported as an unclassified crash."""

    def stubbed(self, code: int, seen: list):
        real = Path.read_text
        target = self.adr

        def read_text(path, *a, **kw):
            if Path(path) == target:
                seen.append(path)
                raise OSError(code, os.strerror(code), str(path))
            return real(path, *a, **kw)
        return mock.patch.object(Path, "read_text", read_text)

    def test_a_late_eacces_on_a_listed_adr_is_a_finding_naming_it(self):
        for name, gate in GATES:
            with self.subTest(gate=name):
                self.control(gate)
                seen: list = []
                with self.stubbed(errno.EACCES, seen):
                    self.assert_findings(gate, {self.rel(self.adr): "EACCES"})
                self.assertTrue(seen, "the build's read was never reached")

    def test_a_late_eio_on_a_listed_adr_takes_the_environment_lane(self):
        for name, gate in GATES:
            with self.subTest(gate=name):
                self.control(gate)
                seen: list = []
                with self.stubbed(errno.EIO, seen):
                    self.assert_environment_lane(
                        gate, [f"environment failure: {self.rel(self.adr)}"])
                self.assertTrue(seen, "the build's read was never reached")


# ═══════════════════════════════════════════════════════════════════════════
# The lint's own scan probes
# ═══════════════════════════════════════════════════════════════════════════

class LintScanTests(GateCase):
    def test_a_confirmed_absent_scan_root_has_nothing_to_scan(self):
        """The positive control for the scan-root cases below."""
        self.control(LINT)
        (self.skills / "SKILL.md").unlink()
        self.skills.rmdir()
        (self.plugin / "skills").rmdir()
        self.plugin.rmdir()
        rc, out, err = self.run_gate(LINT)
        self.assertEqual(rc, 0, f"{out[:2000]!r} {err!r}")
        self.assertNotIn(str(self.plugin), json.loads(out)["roots"])

    def test_a_mode_000_scan_root_takes_the_environment_lane(self):
        skip_if_root(self)
        self.control(LINT)
        self.assert_environment_lane(
            LINT, ["lint-governs-references: environment failure: crux: PermissionError"],
            locked=self.plugin, relative=True)

    def test_an_unlistable_scan_directory_takes_the_environment_lane_naming_the_refusals(self):
        skip_if_root(self)
        fifo = self.plugin / "pipe.md"
        os.mkfifo(fifo)
        rc, out, err = self.run_gate(LINT)
        # POSITIVE CONTROL: the listable tree reports the FIFO as a refusal row only.
        self.assertEqual(rc, 1, f"{out[:2000]!r} {err!r}")
        self.assertEqual([r["reason"] for r in json.loads(out)["refusals"]], ["not_regular"])
        self.assert_environment_lane(LINT, [
            "environment failure: crux/skills/fixture: PermissionError",
            "document finding met in the same run: crux/pipe.md: not_regular"],
            locked=self.skills, relative=True)

    def test_a_regular_file_at_a_scan_root_takes_the_environment_lane(self):
        self.control(LINT)
        (self.skills / "SKILL.md").unlink()
        self.skills.rmdir()
        (self.plugin / "skills").rmdir()
        self.plugin.rmdir()
        self.plugin.write_text("not a directory\n", encoding="utf-8")
        self.assert_environment_lane(LINT, ["environment failure: crux: NotADirectoryError"],
                                     relative=True)

    def test_a_scan_root_whose_presence_cannot_be_determined_takes_the_environment_lane(self):
        self.control(LINT)
        real = os.lstat
        target = os.fspath(self.plugin)
        seen: list = []

        def lstat(path, *a, **kw):
            if os.fspath(path) == target:
                seen.append(path)
                raise OSError(errno.EIO, "Input/output error", os.fspath(path))
            return real(path, *a, **kw)
        with mock.patch.object(os, "lstat", lstat):
            self.assert_environment_lane(
                LINT, ["environment failure: crux: OSError", "Input/output error"],
                relative=True)
        self.assertTrue(seen, "the scan-root probe was never reached")


# ═══════════════════════════════════════════════════════════════════════════
# Census coverage: the census misses no read either gate makes
# ═══════════════════════════════════════════════════════════════════════════

#: The lint's own scan reads every in-scope file beneath the documentation
#: tree; it is named as an exemption by function (anthropic_top:F2):
#: `resolve_scope` (the walk and its probes) and `find_unresolved` (the reads).
LINT_SCAN_FUNCTIONS = frozenset({("lint-governs-references", "resolve_scope"),
                                 ("lint-governs-references", "find_unresolved")})


class _GateCensusCoverage:
    """One fixture holding every member kind and every optional file present."""

    SCRIPT: Path
    EXEMPT_FUNCTIONS: frozenset

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(tmp.cleanup)
        cls.root = Path(tmp.name).resolve() / "repo"
        cls.root.mkdir()
        cls.built = fixture.build(cls.root)
        cls.tree = cls.built["docs"]
        write = subprocess.run([sys.executable, str(SCRIPTS / "summarize-adrs.py"),
                                "--repo-root", str(cls.root)],
                               capture_output=True, text=True, timeout=300)
        if write.returncode != 0:
            raise AssertionError(f"fixture write failed: {write.stdout} {write.stderr}")
        record = Path(tmp.name) / "records.json"
        proc = subprocess.run([sys.executable, str(TESTS / "_census_coverage.py"), str(record),
                               str(cls.SCRIPT), "--repo-root", str(cls.root)],
                              capture_output=True, text=True, timeout=300)
        if proc.returncode != 0:
            raise AssertionError(f"harness failed: {proc.stderr}")
        cls.data = json.loads(record.read_text())

    def gaps(self, members_=None):
        return coverage.coverage_gaps(self.data, root=self.root, tree=self.tree, outputs=[],
                                      exempt_functions=self.EXEMPT_FUNCTIONS,
                                      exempt_modules=members.EXEMPT_MODULES, members=members_)

    def test_the_fixture_holds_every_optional_file_and_runs_clean(self):
        self.assertEqual(self.data["exit"], 0)
        for relative in ("manifest.yml", "adrs/summaries/backfill-reviews.yml",
                         "adrs/summaries/_meta.json", "adrs/doctrine/reconciliations.yml"):
            self.assertTrue((self.tree / relative).is_file(), relative)
        self.assertTrue(self.built["receipt"].is_file())
        phases = {r["phase"] for r in self.data["records"]}
        self.assertTrue({"census", "build"} <= phases, phases)

    def test_every_build_read_is_a_census_member_or_an_exemption(self):
        uncovered, _ = self.gaps()
        self.assertEqual([(r["path"], r["access"], r["module"], r["function"])
                          for r in uncovered], [])

    def test_every_census_member_is_touched_by_the_build_with_its_access_kind(self):
        _, untouched = self.gaps()
        self.assertEqual(untouched, [])

    def test_positive_control_removing_a_member_kind_fails_the_first_direction(self):
        kinds = {"listed ADRs": "/adrs/ADR-0901", "council records": "/councils/",
                 "the ledger": "reconciliations.yml", "the reviews manifest": "backfill-reviews"}
        for kind, marker in kinds.items():
            with self.subTest(kind=kind):
                kept = [m for m in self.data["members"] if marker not in m[0]]
                self.assertLess(len(kept), len(self.data["members"]), marker)
                uncovered, _ = self.gaps(kept)
                self.assertTrue(any(marker in r["path"] for r in uncovered), kind)

    def test_positive_control_widening_or_adding_a_member_fails_the_second_direction(self):
        stat_member = next(m for m in self.data["members"]
                           if m[1] == "stat" and m[0].endswith(".current.json"))
        widened = [[m[0], "read"] if m == stat_member else m for m in self.data["members"]]
        _, untouched = self.gaps(widened)
        self.assertIn((stat_member[0], "read"), untouched)
        added = self.data["members"] + [["bionic/promptbooks/runs", "list"]]
        _, untouched = self.gaps(added)
        self.assertIn(("bionic/promptbooks/runs", "list"), untouched)


class LintCensusCoverageTests(_GateCensusCoverage, unittest.TestCase):
    SCRIPT = LINT_PATH
    EXEMPT_FUNCTIONS = members.EXEMPT_FUNCTIONS | LINT_SCAN_FUNCTIONS

    def test_positive_control_the_scan_exemption_hides_reads_beneath_the_tree(self):
        """Without the scan exemption the lint's own reads of the tree are uncovered,
        so the exemption is what admits them, not an empty record set."""
        uncovered, _ = coverage.coverage_gaps(
            self.data, root=self.root, tree=self.tree, outputs=[],
            exempt_functions=members.EXEMPT_FUNCTIONS, exempt_modules=members.EXEMPT_MODULES)
        self.assertTrue(any(r["function"] == "read_source" for r in uncovered))

    def test_the_census_takes_the_observations_the_lint_reads(self):
        self.assertTrue(any(m[0].startswith("bionic/observations/") for m in self.data["members"]))


class CoverageCensusCoverageTests(_GateCensusCoverage, unittest.TestCase):
    SCRIPT = COVERAGE_PATH
    EXEMPT_FUNCTIONS = members.EXEMPT_FUNCTIONS

    def test_the_census_takes_no_observation_the_coverage_gate_never_reads(self):
        self.assertFalse(any("observations" in m[0] for m in self.data["members"]))


if __name__ == "__main__":
    unittest.main()
