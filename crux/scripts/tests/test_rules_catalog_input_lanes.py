"""generate-rules-catalog.py: each failed read takes its lane, and one run names every one.

THE CONTRACT. The rules catalog shares the input census with summarize-adrs and
compile-doctrine, and it scans the shipped surfaces under crux/ for citations.
- A census input whose read fails for a cause attributable to its path is a
  DOCUMENT-lane row: exit 1, a `{path, reason}` row in `validation_errors`,
  the path relative to the repository and no absolute path in the reason.
- A listed shipped text-suffix entry the scan cannot read for such a cause,
  including a dangling link inside the plugin root, is a blocking row of the
  same shape.
- A cause in the process or host (EIO), a directory the scan cannot list, an
  adrs directory whose presence cannot be determined, and a dangling link at
  an optional file take the ENVIRONMENT lane: exit 2, nothing on stdout,
  stderr naming the input and every document row the same run met.
- An unsearchable tree is never the surface-absent lane.
- The scan stats a candidate with its link followed before any open: a
  directory is an EISDIR row, and a FIFO is skipped unopened.
- The read of the existing catalog follows the output-read rule.

Every refusal runs on a fixture its positive control just ran clean on, in
write mode and in --dry-run, with the catalog present (it stays byte-unchanged)
and absent (it is not created), and asserts no file appears. A
permission-based test skips when the effective uid is 0.

Run:
  uv run python3 -m unittest discover -s crux/scripts/tests -p 'test_rules_catalog_input_lanes.py'
"""

from __future__ import annotations

import contextlib
import errno
import importlib.util
import io
import json
import os
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


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GRC_PATH = SCRIPTS / "generate-rules-catalog.py"
GRC = _load("rules_catalog_input_lanes", GRC_PATH)
# The shared census-member module, loaded under a private name so its own
# classes are not collected a second time from this module.
members = _load("_catalog_members_base", TESTS / "test_summarize_adrs_census_members.py")
MODES = (("write", ()), ("dry-run", ("--dry-run",)))
MISSING = "symbolic link whose target is missing"
CATALOG = "crux/catalog/rules.json"


def skip_if_root(case: unittest.TestCase) -> None:
    if os.geteuid() == 0:
        case.skipTest("running as root: a mode-000 path is still readable")


def tree_files(root: Path) -> set[str]:
    """Every path under `root`, relative, without following links or failing on a locked directory."""
    out = set()
    for directory, dirs, files in os.walk(root, onerror=lambda exc: None):
        for name in dirs + files:
            out.add(str((Path(directory) / name).relative_to(root)))
    return out


class CatalogCase(unittest.TestCase):
    """A miniature authoring checkout: a tree with two Accepted ADRs, a skill citing
    rule-901, and crux/held/held.md citing rule-902 outside every scan root, so
    rule-902 reaches the catalog only through a link the scan follows."""

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
        self.plugin = self.root / "crux"
        probe = self.plugin / "scripts" / GRC_PATH.name
        probe.parent.mkdir(parents=True)
        probe.write_text("# authoring-checkout probe (test fixture)\n", encoding="utf-8")
        self.skills = self.plugin / "skills" / "fixture"
        self.skills.mkdir(parents=True)
        self.skill = self.skills / "SKILL.md"
        self.skill.write_text("This surface cites rule:rule-901 here.\n", encoding="utf-8")
        self.held_dir = self.plugin / "held"
        self.held_dir.mkdir()
        self.held = self.held_dir / "held.md"
        self.held.write_text("This held page cites rule:rule-902 here.\n", encoding="utf-8")
        self.catalog = self.plugin / "catalog" / "rules.json"

    # ── running ──────────────────────────────────────────────────────────

    def run_cat(self, *args: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = GRC.main(["--repo-root", str(self.root), *args])
        return rc, out.getvalue(), err.getvalue()

    def rules(self) -> dict:
        return json.loads(self.catalog.read_text(encoding="utf-8"))["rules"]

    def prime(self, *, expect: tuple[str, ...] = ("rule-901",)) -> None:
        """POSITIVE CONTROL: regenerate, then the same fixture is clean under --dry-run."""
        rc, out, err = self.run_cat()
        self.assertEqual(rc, 0, f"regenerate: {out!r} {err!r}")
        rc, out, err = self.run_cat("--dry-run")
        self.assertEqual(rc, 0, f"control: {out!r} {err!r}")
        self.assertFalse(json.loads(out)["drift"])
        self.assertEqual(sorted(self.rules()), sorted(expect))

    def assert_no_absolute_path(self, text: str, ctx: str) -> None:
        self.assertNotIn(str(self.root), text, ctx)
        self.assertNotIn(os.path.realpath(self.root), text, ctx)

    # ── lanes ────────────────────────────────────────────────────────────

    def refusal_runs(self, check, *, locked: Path | None = None) -> None:
        """Run each mode with the catalog present and absent, and `check(rc, out, err, ctx)`.

        A present catalog stays byte-unchanged, an absent one is not created, and
        no file appears.
        """
        present = self.catalog.read_bytes()
        for state in ("present", "absent"):
            if state == "absent":
                self.catalog.unlink()
            for mode, args in MODES:
                with self.subTest(catalog=state, mode=mode):
                    files = tree_files(self.root)
                    if locked is not None:
                        locked.chmod(0o000)
                    try:
                        rc, out, err = self.run_cat(*args)
                    finally:
                        if locked is not None:
                            locked.chmod(0o755)
                    ctx = f"{state}/{mode}: rc={rc} out={out!r} err={err!r}"
                    check(rc, out, err, ctx)
                    if state == "present":
                        self.assertEqual(self.catalog.read_bytes(), present,
                                         f"the catalog changed — {ctx}")
                    else:
                        self.assertFalse(self.catalog.exists(), f"a catalog was created — {ctx}")
                    self.assertEqual(tree_files(self.root), files, f"a file appeared — {ctx}")
        self.catalog.write_bytes(present)

    def assert_rows(self, rows: dict[str, str], **kw) -> None:
        """Exit 1, and exactly `rows` (path -> reason fragment) as `{path, reason}` rows."""
        def check(rc, out, err, ctx):
            self.assertEqual(rc, 1, ctx)
            payload = json.loads(out)
            self.assertIsNone(payload["written"], ctx)
            errors = payload["validation_errors"]
            self.assertEqual(sorted(e["path"] for e in errors), sorted(rows), ctx)
            for entry in errors:
                self.assertEqual(set(entry), {"path", "reason"}, ctx)
                self.assertIn(rows[entry["path"]], entry["reason"], ctx)
                self.assert_no_absolute_path(entry["reason"], ctx)
        self.refusal_runs(check, **kw)

    def assert_environment_lane(self, named: list[str], **kw) -> None:
        def check(rc, out, err, ctx):
            self.assertEqual(rc, 2, ctx)
            self.assertEqual(out, "", ctx)
            for text in named:
                self.assertIn(text, err, ctx)
        self.refusal_runs(check, **kw)


# ═══════════════════════════════════════════════════════════════════════════
# The citing-surface scan
# ═══════════════════════════════════════════════════════════════════════════

class ScanCandidateTests(CatalogCase):
    def test_a_dangling_text_suffix_link_inside_the_plugin_root_is_a_blocking_row(self):
        link = self.skills / "linked.md"
        link.symlink_to(Path("..") / ".." / "held" / "held.md")
        # POSITIVE CONTROL: the live link is read, so its citation reaches the catalog.
        self.prime(expect=("rule-901", "rule-902"))
        self.held.unlink()
        self.assertTrue(link.is_symlink())
        self.assert_rows({"crux/skills/fixture/linked.md": "ENOENT"})

    def test_a_link_whose_target_lies_outside_keeps_the_advisory_row_dangling_or_not(self):
        outside = self.root / "outside.md"
        outside.write_text("cites rule:rule-902\n", encoding="utf-8")
        link = self.skills / "outside.md"
        link.symlink_to(outside)
        advisory = {"path": "crux/skills/fixture/outside.md", "advisory": True,
                    "reason": "resolves outside the plugin root; not a shipped surface"}
        # POSITIVE CONTROL: a live link out of the plugin root is the advisory row,
        # and the run stays clean.
        self.prime()
        self.assertEqual(GRC.cited_slug_paths(self.plugin)[1], [advisory])
        outside.unlink()
        self.assertEqual(GRC.cited_slug_paths(self.plugin)[1], [advisory])
        for mode, args in MODES:
            with self.subTest(mode=mode):
                rc, out, err = self.run_cat(*args)
                self.assertEqual(rc, 0, f"{out!r} {err!r}")

    def test_a_link_to_a_directory_with_a_text_suffix_is_an_eisdir_row(self):
        self.prime()
        link = self.skills / "dir.md"
        link.symlink_to(Path("..") / ".." / "held")
        self.assert_rows({"crux/skills/fixture/dir.md": "EISDIR"})

    def test_a_link_loop_with_a_text_suffix_is_an_eloop_row(self):
        self.prime()
        loop = self.skills / "loop.md"
        loop.symlink_to(loop.name)
        self.assert_rows({"crux/skills/fixture/loop.md": "ELOOP"})

    def test_an_unreadable_shipped_file_is_a_row_with_no_absolute_path(self):
        self.prime()
        skip_if_root(self)
        self.addCleanup(self.skill.chmod, 0o644)
        self.skill.chmod(0o000)
        self.assert_rows({"crux/skills/fixture/SKILL.md": "EACCES"})

    def test_an_eio_on_a_shipped_file_takes_the_environment_lane(self):
        self.prime()
        real_open = os.open
        target = os.path.realpath(self.skill)
        seen: list = []

        def stub(path, flags, *a, **kw):
            if os.fspath(path) == target:
                seen.append(path)
                raise OSError(errno.EIO, os.strerror(errno.EIO), os.fspath(path))
            return real_open(path, flags, *a, **kw)
        with mock.patch.object(os, "open", stub):
            self.assert_environment_lane(["environment failure: crux/skills/fixture/SKILL.md",
                                          "EIO"])
        self.assertTrue(seen, "the scan's open was never reached")

    def test_an_unlistable_directory_under_skills_takes_the_environment_lane(self):
        self.prime()
        skip_if_root(self)

        def check(rc, out, err, ctx):
            self.assertEqual((rc, out), (2, ""), ctx)
            self.assertIn("environment failure: crux/skills/fixture: PermissionError", err, ctx)
            self.assert_no_absolute_path(err, ctx)
        self.refusal_runs(check, locked=self.skills)


class ExistingScanRefusalTests(CatalogCase):
    """The size, count and containment refusals keep their rows."""

    def test_the_size_ceiling_keeps_its_row(self):
        # The skill is padded past a ceiling that every other scanned file stays under.
        self.skill.write_text("This surface cites rule:rule-901 here.\n" + "x" * 200 + "\n",
                              encoding="utf-8")
        self.prime()
        with mock.patch.object(GRC, "MAX_FILE_BYTES", 128):
            self.assert_rows({"crux/skills/fixture/SKILL.md": "larger than MAX_FILE_BYTES (128)"})

    def test_the_file_count_ceiling_keeps_its_row(self):
        (self.skills / "other.md").write_text("cites rule:rule-901\n", encoding="utf-8")
        self.prime()
        with mock.patch.object(GRC, "MAX_SCANNED_FILES", 1):
            self.assert_rows({"crux/skills/fixture/other.md": "scope exceeds MAX_SCANNED_FILES (1)"})


class FifoCandidateTests(CatalogCase):
    """A text-suffix link to a FIFO inside the plugin root is never opened.

    The driver runs in a child process with a timeout, so an open that blocks
    fails the test instead of hanging the suite. A link to a regular file is
    the control: its citation reaches the catalog in the same run.
    """

    def run_child(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(GRC_PATH), "--repo-root", str(self.root),
                               *args], capture_output=True, text=True, timeout=120)

    def test_a_link_to_a_fifo_is_skipped_unopened_beside_a_regular_file_link(self):
        (self.skills / "real.md").symlink_to(Path("..") / ".." / "held" / "held.md")
        pipe = self.held_dir / "pipe"
        os.mkfifo(pipe)
        (self.skills / "pipe.md").symlink_to(Path("..") / ".." / "held" / "pipe")
        for mode, args in MODES:
            with self.subTest(mode=mode):
                proc = self.run_child(*args)
                self.assertEqual(proc.returncode, 0, f"{proc.stdout!r} {proc.stderr!r}")
                self.assertEqual(sorted(self.rules()), ["rule-901", "rule-902"])

    def test_a_fifo_at_the_catalog_path_takes_the_environment_lane_unopened(self):
        self.prime()
        self.catalog.unlink()
        os.mkfifo(self.catalog)
        for mode, args in MODES:
            with self.subTest(mode=mode):
                proc = self.run_child(*args)
                self.assertEqual((proc.returncode, proc.stdout), (2, ""), proc.stderr)
                self.assertIn(f"{CATALOG}: OSError: is a FIFO", proc.stderr)


# ═══════════════════════════════════════════════════════════════════════════
# The census beside the scan: one run names every failing input
# ═══════════════════════════════════════════════════════════════════════════

class CensusAndScanTests(CatalogCase):
    def test_a_census_finding_and_a_scan_row_appear_in_one_payload(self):
        bad = self.skills / "bad.md"
        bad.write_text("cites rule:rule-901\n", encoding="utf-8")
        self.prime()
        self.adr.write_bytes(fixture.adr(902).encode("utf-8").replace(b"Body.", b"Body \xff."))
        bad.write_bytes(b"cites rule:rule-901\n\xff\n")
        self.assert_rows({"bionic/adrs/ADR-0902-x.md": "not valid UTF-8",
                          "crux/skills/fixture/bad.md": "not valid UTF-8"})

    def test_a_census_failure_names_the_scan_rows_in_the_environment_lane(self):
        bad = self.skills / "bad.md"
        bad.write_text("cites rule:rule-901\n", encoding="utf-8")
        self.prime()
        reviews = self.adrs / "summaries" / "backfill-reviews.yml"
        reviews.parent.mkdir(exist_ok=True)
        reviews.symlink_to("held-reviews.yml")
        bad.write_bytes(b"\xff\n")
        self.assert_environment_lane([
            "bionic/adrs/summaries/backfill-reviews.yml: is a " + MISSING,
            "document finding met in the same run: crux/skills/fixture/bad.md: is not valid UTF-8"])

    def test_a_scan_failure_names_the_census_findings_in_the_environment_lane(self):
        self.prime()
        skip_if_root(self)
        self.adr.write_bytes(b"\xff\n")
        self.assert_environment_lane([
            "environment failure: crux/skills/fixture: PermissionError",
            "document finding met in the same run: bionic/adrs/ADR-0902-x.md: is not valid UTF-8"],
            locked=self.skills)

    def test_a_late_eacces_on_a_listed_adr_is_a_row_naming_it(self):
        """anthropic_top:F1: a build read that fails after a clean census is classified."""
        self.prime()
        real = Path.read_text
        target = self.adr
        seen: list = []

        def read_text(path, *a, **kw):
            if Path(path) == target:
                seen.append(path)
                raise OSError(errno.EACCES, os.strerror(errno.EACCES), str(path))
            return real(path, *a, **kw)
        with mock.patch.object(Path, "read_text", read_text):
            self.assert_rows({"bionic/adrs/ADR-0902-x.md": "EACCES"})
        self.assertTrue(seen, "the build's read was never reached")


class OptionalFileLinkTests(CatalogCase):
    """A dangling link at an optional file named by path is not read as absent."""

    def test_a_dangling_link_at_the_manifest_takes_the_environment_lane(self):
        self.prime()
        self.manifest.unlink()
        # POSITIVE CONTROL: a confirmed-absent manifest is no finding.
        rc, out, err = self.run_cat("--dry-run")
        self.assertEqual(rc, 0, f"{out!r} {err!r}")
        self.manifest.symlink_to("held-manifest.yml")
        self.assert_environment_lane([f"bionic/manifest.yml: is a {MISSING}"])

    def test_a_dangling_link_at_the_reviews_manifest_takes_the_environment_lane(self):
        # POSITIVE CONTROL: the fixture has no reviews manifest, and runs clean.
        self.prime()
        reviews = self.adrs / "summaries" / "backfill-reviews.yml"
        reviews.parent.mkdir(exist_ok=True)
        reviews.symlink_to("held-reviews.yml")
        self.assert_environment_lane(
            [f"bionic/adrs/summaries/backfill-reviews.yml: is a {MISSING}"])


# ═══════════════════════════════════════════════════════════════════════════
# The tree probe: an unsearchable tree is never surface-absent
# ═══════════════════════════════════════════════════════════════════════════

class TreeProbeTests(CatalogCase):
    def test_a_confirmed_absent_adrs_directory_keeps_the_surface_absent_lane(self):
        """The positive control for the cases below."""
        self.prime()
        self.adrs.rename(self.root / "moved-adrs")
        rc, out, err = self.run_cat("--dry-run")
        self.assertEqual(rc, 0, err)
        self.assertTrue(json.loads(out)["surface_absent"])
        rc, out, err = self.run_cat("--dry-run", "--require-surface")
        self.assertEqual((rc, out), (2, ""))
        self.assertIn("--require-surface was passed", err)

    def test_an_unsearchable_tree_is_never_surface_absent(self):
        self.prime()
        skip_if_root(self)
        for flags in ((), ("--require-surface",)):
            with self.subTest(flags=flags):
                def check(rc, out, err, ctx):
                    self.assertEqual((rc, out), (2, ""), ctx)
                    self.assertIn("bionic/adrs: PermissionError: EACCES", err, ctx)
                    self.assertIn("not an absent surface", err, ctx)
                    self.assert_no_absolute_path(err, ctx)
                self.tree.chmod(0o600)
                try:
                    for mode, args in MODES:
                        rc, out, err = self.run_cat(*args, *flags)
                        check(rc, out, err, f"{mode}: {out!r} {err!r}")
                finally:
                    self.tree.chmod(0o755)
                self.assertTrue(self.catalog.is_file())

    def test_a_regular_file_at_the_adrs_path_takes_the_environment_lane(self):
        self.prime()
        self.adrs.rename(self.root / "moved-adrs")
        self.adrs.write_text("not a directory\n", encoding="utf-8")
        self.assert_environment_lane(["bionic/adrs: NotADirectoryError", "not an absent surface"])


# ═══════════════════════════════════════════════════════════════════════════
# The output read
# ═══════════════════════════════════════════════════════════════════════════

class OutputReadTests(CatalogCase):
    def output_runs(self, check, *, locked: bool = False) -> None:
        before = self.catalog.read_bytes() if self.catalog.is_file() else None
        for mode, args in MODES:
            with self.subTest(mode=mode):
                if locked:
                    self.catalog.chmod(0o000)
                try:
                    rc, out, err = self.run_cat(*args)
                finally:
                    if locked:
                        self.catalog.chmod(0o644)
                check(rc, out, err, f"{mode}: rc={rc} out={out!r} err={err!r}")
                if before is not None:
                    self.assertEqual(self.catalog.read_bytes(), before)

    def assert_output_row(self, fragment: str, **kw) -> None:
        def check(rc, out, err, ctx):
            self.assertEqual(rc, 1, ctx)
            payload = json.loads(out)
            self.assertEqual([e["path"] for e in payload["validation_errors"]], [CATALOG], ctx)
            reason = payload["validation_errors"][0]["reason"]
            self.assertIn(fragment, reason, ctx)
            self.assertIn("rerun the regenerator", reason, ctx)
            self.assert_no_absolute_path(reason, ctx)
        self.output_runs(check, **kw)

    def test_an_absent_catalog_reads_as_empty(self):
        self.prime()
        self.catalog.unlink()
        rc, out, err = self.run_cat("--dry-run")
        self.assertEqual((rc, json.loads(out)["drift"]), (1, True), err)
        self.assertFalse(self.catalog.exists())
        rc, out, err = self.run_cat()
        self.assertEqual(rc, 0, err)
        self.assertEqual(sorted(self.rules()), ["rule-901"])

    def test_an_unreadable_catalog_is_a_row_naming_it(self):
        self.prime()
        skip_if_root(self)
        self.assert_output_row("EACCES", locked=True)

    def test_a_catalog_that_is_not_utf8_is_a_row_naming_it(self):
        self.prime()
        self.catalog.write_bytes(b"{\xff}\n")
        self.assert_output_row("not valid UTF-8")

    def test_a_directory_at_the_catalog_path_is_a_row_naming_it(self):
        self.prime()
        self.catalog.unlink()
        self.catalog.mkdir()
        self.assert_output_row("EISDIR")
        self.assertTrue(self.catalog.is_dir())

    def test_an_eio_on_the_catalog_read_takes_the_environment_lane(self):
        self.prime()
        real = Path.read_text
        target = self.catalog

        def read_text(path, *a, **kw):
            if Path(path) == target:
                raise OSError(errno.EIO, os.strerror(errno.EIO), str(path))
            return real(path, *a, **kw)

        def check(rc, out, err, ctx):
            self.assertEqual((rc, out), (2, ""), ctx)
            self.assertIn(f"environment failure: {CATALOG}: OSError: EIO", err, ctx)
        with mock.patch.object(Path, "read_text", read_text):
            self.output_runs(check)

    def test_an_input_row_leaves_the_catalog_unread(self):
        self.prime()
        self.catalog.write_bytes(b"{\xff}\n")
        self.adr.write_bytes(b"\xff\n")

        def check(rc, out, err, ctx):
            self.assertEqual(rc, 1, ctx)
            self.assertEqual([e["path"] for e in json.loads(out)["validation_errors"]],
                             ["bionic/adrs/ADR-0902-x.md"], ctx)
        self.output_runs(check)


# ═══════════════════════════════════════════════════════════════════════════
# Census coverage: the census misses no read the rules catalog makes
# ═══════════════════════════════════════════════════════════════════════════

class CatalogCensusCoverageTests(unittest.TestCase):
    """One fixture holding every member kind and every optional file present,
    in an authoring checkout whose skill cites a rule the fixture accepts."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(tmp.cleanup)
        cls.root = Path(tmp.name).resolve() / "repo"
        cls.root.mkdir()
        cls.built = fixture.build(cls.root)
        cls.tree = cls.built["docs"]
        probe = cls.root / "crux" / "scripts" / GRC_PATH.name
        probe.parent.mkdir(parents=True)
        probe.write_text("# authoring-checkout probe (test fixture)\n", encoding="utf-8")
        skill = cls.root / "crux" / "skills" / "fixture" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("This surface cites rule:rule-901 here.\n", encoding="utf-8")
        for script in (SCRIPTS / "summarize-adrs.py", GRC_PATH):
            write = subprocess.run([sys.executable, str(script), "--repo-root", str(cls.root)],
                                   capture_output=True, text=True, timeout=300)
            if write.returncode != 0:
                raise AssertionError(f"fixture write failed: {write.stdout} {write.stderr}")
        record = Path(tmp.name) / "records.json"
        proc = subprocess.run([sys.executable, str(TESTS / "_census_coverage.py"), str(record),
                               str(GRC_PATH), "--repo-root", str(cls.root), "--dry-run"],
                              capture_output=True, text=True, timeout=300)
        if proc.returncode != 0:
            raise AssertionError(f"harness failed: {proc.stderr}")
        cls.data = json.loads(record.read_text())

    def gaps(self, members_=None):
        return coverage.coverage_gaps(self.data, root=self.root, tree=self.tree, outputs=[],
                                      exempt_functions=members.EXEMPT_FUNCTIONS,
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
        added = self.data["members"] + [["bionic/adrs/doctrine/_meta.json", "read"]]
        _, untouched = self.gaps(added)
        self.assertIn(("bionic/adrs/doctrine/_meta.json", "read"), untouched)


if __name__ == "__main__":
    unittest.main()
