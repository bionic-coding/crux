"""compile-doctrine.py: each failed read of a census member takes its lane.

THE CONTRACT. compile-doctrine shares the input census with summarize-adrs,
so the same cases hold for it: a cause attributable to an input's path is a
DOCUMENT-lane finding (exit 1, a `validation_errors` entry naming the input
by its repository-relative path, no absolute path in the reason), and a
cause in the process or host, an unlistable input directory, a dangling link
at an optional file and a FIFO take the ENVIRONMENT lane (exit 2, nothing on
stdout, stderr naming the input and every document finding the same run
met). The census decides this before the authority proof or the build reads
any input.

Most cases are the summarize-adrs cases run against compile-doctrine: each
class below subclasses the shared case with the driver swapped, so a case
added there is run here too. The doctrine-only members are added here: the
invariants directory and its pages (member (j)), adrs/doctrine/_meta.json,
and the reconciliation ledger's three doctrine readers.

Every refusal runs on a fixture its positive control just ran clean on, in
write mode and in --dry-run, removes one output first and asserts no output
reappears, and asserts every remaining output byte-unchanged. A
permission-based test skips when the effective uid is 0.

Run:
  uv run python3 -m unittest discover -s crux/scripts/tests -p 'test_compile_doctrine_input_lanes.py'
"""

from __future__ import annotations

import errno
import importlib.util
import json
import os
import shutil
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

import input_lanes  # noqa: E402
import summaries_projection as sp  # noqa: E402
import doctrine_projection as dp  # noqa: E402
import _census_coverage as coverage  # noqa: E402
import _census_fixture as fixture  # noqa: E402


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# The shared cases, loaded under private names so their own classes are not
# collected a second time from this module.
lanes = _load("_doctrine_lanes_base", TESTS / "test_summarize_adrs_input_lanes.py")
members = _load("_doctrine_members_base", TESTS / "test_summarize_adrs_census_members.py")
CD_PATH = SCRIPTS / "compile-doctrine.py"
CD = _load("compile_doctrine_input_lanes", CD_PATH)
MODES = lanes.MODES
skip_if_root = lanes.skip_if_root
MISSING = "symbolic link whose target is missing"
LEDGER_NAME = "adrs/doctrine/reconciliations.yml"
INVARIANT = ("---\nid: INV-0001\nratification: ratified\nrelated_adrs: [ADR-0901]\n---\n\n"
             "## The invariant\n\nRule 901 holds.\n")


class DoctrineDriver:
    """Runs a shared case against compile-doctrine and its two outputs."""

    DRIVER = "compile-doctrine"
    MODULE = CD
    SCRIPT_PATH = CD_PATH
    OUTPUT_SUBDIR = "doctrine"
    OUTPUT_NAMES = ("index.md", "_meta.json")
    REMOVED_OUTPUT = "index.md"
    CONTROL_OUTPUT = "index.md"
    DESTINATION_REFUSAL = "doctrine destination is symlinked or has an owned temporary path"


# ═══════════════════════════════════════════════════════════════════════════
# The shared cases, run against compile-doctrine
# ═══════════════════════════════════════════════════════════════════════════

class DoctrineListedAdrDocumentLaneTests(DoctrineDriver, lanes.ListedAdrDocumentLaneTests):
    pass


class DoctrineContainmentTests(DoctrineDriver, lanes.ContainmentTests):
    pass


class DoctrineUnlistableTierTests(DoctrineDriver, lanes.UnlistableTierTests):
    pass


class DoctrineProcessLevelPrecedenceTests(DoctrineDriver, lanes.ProcessLevelPrecedenceTests):
    pass


class DoctrineLateFailureTests(DoctrineDriver, lanes.LateFailureTests):
    """anthropic_top:F1: a late EACCES on a listed ADR exits 1 naming it."""


class DoctrineManifestCensusTests(DoctrineDriver, lanes.ManifestCensusTests):
    pass


class DoctrineOutputReadTests(DoctrineDriver, lanes.OutputReadTests):
    """On a tree with no Git history the migration proof reads both doctrine
    outputs itself (exemption X3), before this driver's output read. So the
    tree is committed after the control: the proof then takes the Git path,
    and the --dry-run read is this driver's."""

    def prime(self) -> None:
        super().prime()
        for args in (("init", "-q"), ("add", "-A"), ("commit", "-qm", "fixture")):
            subprocess.run(["git", "-C", str(self.root), "-c", "user.email=t@example.invalid",
                            "-c", "user.name=T", *args], check=True, capture_output=True)
        # The committed tree is still clean.
        rc, out, err = self.run_sa("--dry-run")
        self.assertEqual((rc, json.loads(out)), (0, {"drift": False, "paths": []}), err)


class DoctrineCensusShapeTests(DoctrineDriver, lanes.CensusShapeTests):
    pass


class DoctrineSidecarTests(DoctrineDriver, members.SidecarTests):
    pass


class DoctrineProvenanceTests(DoctrineDriver, members.ProvenanceTests):
    pass


class DoctrineOptionalFileTests(DoctrineDriver, members.OptionalFileTests):
    """The ledger cases, the dangling optional files and adrs/doctrine/_meta.json."""

    def test_a_dangling_link_at_the_manifest_or_reviews_manifest_takes_the_environment_lane(self):
        """Positive control: prime() runs the same fixture clean before the link dangles."""
        # The migration proof refuses a symlinked manifest, so the manifest's
        # control runs on the regular file and the link replaces it after.
        for path in (self.manifest, self.reviews):
            with self.subTest(file=path.name):
                # POSITIVE CONTROL: the manifest present, the reviews manifest absent.
                self.prime()
                held = path.with_name("held-" + path.name)
                if path.exists():
                    path.rename(held)
                path.parent.mkdir(exist_ok=True)
                path.symlink_to("missing-" + path.name)
                self.assertFalse(path.exists())
                self.assert_environment_lane([f"environment failure: {self.rel(path)}", MISSING])
                path.unlink()
                if held.exists():
                    held.rename(path)

    def test_a_late_eacces_on_the_ledger_is_a_finding_naming_it(self):
        self.present()
        self.prime()
        seen: list = []
        real = Path.read_bytes
        ledger = self.ledger

        def read_bytes(path, *a, **kw):
            if Path(path) == ledger:
                seen.append(path)
                raise OSError(errno.EACCES, os.strerror(errno.EACCES), str(path))
            return real(path, *a, **kw)
        with mock.patch.object(Path, "read_bytes", read_bytes):
            self.assert_document_lane({self.rel(self.ledger): "EACCES"})
        self.assertTrue(seen, "the build's read was never reached")


class DoctrineCollectionTests(DoctrineDriver, members.CollectionTests):
    pass


class DoctrineObservationTests(DoctrineDriver, members.ObservationTests):
    pass


class DoctrineObservationsOnlyManifestTests(DoctrineDriver, members.ObservationsOnlyManifestTests):
    pass


class DoctrineRunSnapshotTests(DoctrineDriver, members.RunSnapshotTests):
    def test_the_candidate_rule_reads_snapshots_and_skips_a_stray_file(self):
        # POSITIVE CONTROL: the snapshot binds ADR-0901, so it is read.
        self.prime()
        rows = [line for line in (self.output_dir / "index.md").read_text().splitlines()
                if line.startswith("| ADR-0901/rule-901 ")]
        self.assertTrue(rows and rows[0].rstrip().endswith("| run-bound |"), rows)
        census = dict(sp.input_census(self.root, driver=self.DRIVER).members)
        self.assertEqual(census[self.rel(self.snapshot)], "read")
        self.assertEqual(census[self.rel(self.run_dir)], "list")
        self.assertNotIn(self.rel(self.runs / ".DS_Store"), census)


class DoctrineFifoTests(DoctrineDriver, members.FifoTests):
    pass


class DoctrineAcceptanceChainTests(DoctrineDriver, members.AcceptanceChainTests):
    pass


class DoctrineLateChainFailureTests(DoctrineDriver, members.LateChainFailureTests):
    pass


# ═══════════════════════════════════════════════════════════════════════════
# (j) The invariants directory and its pages
# ═══════════════════════════════════════════════════════════════════════════

class InvariantTests(DoctrineDriver, members.MemberCase):
    def setUp(self) -> None:
        super().setUp()
        self.invariants = self.tree / "invariants"
        self.invariants.mkdir()
        self.page = self.invariants / "rule-901.md"
        self.page.write_text(INVARIANT, encoding="utf-8")
        (self.invariants / "reconciliation.yml").write_text("{}\n", encoding="utf-8")
        (self.invariants / "checks").mkdir()

    def test_the_candidate_rule_reads_pages_and_skips_other_names(self):
        # POSITIVE CONTROL: the page pairs with ADR-0901, so it is read.
        self.prime()
        self.assertIn("| INV-0001 | ADR-0901/rule-901 |",
                      (self.output_dir / "index.md").read_text())
        census = dict(sp.input_census(self.root, driver=self.DRIVER).members)
        self.assertEqual(census[self.rel(self.invariants)], "list")
        self.assertEqual(census[self.rel(self.page)], "read")
        self.assertNotIn(self.rel(self.invariants / "reconciliation.yml"), census)
        self.assertNotIn(self.rel(self.invariants / "checks"), census)
        # The member is compile-doctrine's alone.
        other = dict(sp.input_census(self.root, driver="summarize-adrs").members)
        self.assertNotIn(self.rel(self.invariants), other)

    def test_a_dangling_listed_page_link_is_a_finding(self):
        self.prime()
        link = self.invariants / "rule-902.md"
        link.symlink_to("rule-902-held.md")
        self.assert_document_lane({self.rel(link): "ENOENT"})

    def test_an_unreadable_page_is_a_finding(self):
        self.prime()
        self.lock(self.page)
        self.assert_document_lane({self.rel(self.page): "EACCES"})

    def test_a_page_that_is_not_utf8_is_a_finding(self):
        self.prime()
        self.page.write_bytes(INVARIANT.encode("utf-8").replace(b"holds.", b"holds \xff."))
        self.assert_document_lane({self.rel(self.page): "not valid UTF-8"})

    def test_a_directory_named_like_a_page_is_a_finding(self):
        self.prime()
        directory = self.invariants / "rule-902.md"
        directory.mkdir()
        self.assert_document_lane({self.rel(directory): "EISDIR"})

    def test_an_unlistable_invariants_directory_is_an_environment_failure(self):
        self.prime()
        skip_if_root(self)
        self.assert_environment_lane([f"environment failure: {self.rel(self.invariants)}"],
                                     locked=self.invariants, lock_mode=0o300)

    def test_a_regular_file_at_the_invariants_path_is_an_environment_failure(self):
        self.prime()
        shutil.rmtree(self.invariants)
        self.invariants.write_text("not a directory\n", encoding="utf-8")
        self.assert_environment_lane([f"environment failure: {self.rel(self.invariants)}",
                                      "NotADirectoryError"])

    def test_a_confirmed_absent_invariants_directory_is_no_input(self):
        self.prime()
        shutil.rmtree(self.invariants)
        rc, out, err = self.run_sa("--dry-run")
        # The digest moves, so the outputs drift; nothing is refused.
        self.assertEqual(rc, 1, err)
        self.assertEqual(json.loads(out)["drift"], True, out)
        self.assertEqual(err, "")


# ═══════════════════════════════════════════════════════════════════════════
# The unseamed doctrine readers (F5) and the strict invariants listing
# ═══════════════════════════════════════════════════════════════════════════

class LedgerReaderTests(unittest.TestCase):
    """Each doctrine reader of the ledger, unseamed, with the ledger's kinds."""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        (self.root / ".bionic.yml").write_text("docs_dir: bionic\n", encoding="utf-8")
        self.tree = self.root / "bionic"
        self.adrs = self.tree / "adrs"
        (self.adrs / "doctrine").mkdir(parents=True)
        self.ledger = self.adrs / "doctrine" / "reconciliations.yml"

    def load_inputs(self):
        """`_load_doctrine_inputs`' own ledger read, isolated.

        The authority proof is not this reader's question, and the two other
        ledger readers it reaches (the signature-orphan check inside
        `collect_records`, and `reconciliations_sha256` inside
        `input_digests`) are stubbed, so only its own read meets the ledger.
        """
        view = {"state": "absent", "publications": [], "dependency_fingerprints": []}
        with mock.patch.object(sp, "_summary_authority_records",
                               lambda records, *a, **kw: {"records": records}), \
                mock.patch.object(sp, "signed_reconciliation_handles", lambda *a, **kw: set()), \
                mock.patch.object(dp, "input_digests", lambda *a, **kw: {}):
            loaded, *_ = dp._load_doctrine_inputs(
                self.root, {"concerns_enabled": ["adrs"]},
                _prepared={"view": view, "candidate": None})
        return loaded["ledger"]["text"]

    def readers(self):
        return {"read_reconciliations": (lambda: dp.read_reconciliations(self.root), []),
                "reconciliations_sha256": (lambda: dp.reconciliations_sha256(self.root), None),
                "_load_doctrine_inputs": (self.load_inputs, None)}

    def test_an_absent_ledger_reads_as_absent(self):
        for name, (call, absent) in self.readers().items():
            with self.subTest(reader=name):
                self.assertEqual(call(), absent)

    def test_a_present_ledger_is_read(self):
        # POSITIVE CONTROL for the cases below: the same readers read it.
        self.ledger.write_text(fixture.LEDGER, encoding="utf-8")
        self.assertEqual([r["invariant"] for r in dp.read_reconciliations(self.root)],
                         ["INV-0001"])
        self.assertEqual(len(dp.reconciliations_sha256(self.root)), 64)
        self.assertEqual(self.load_inputs(), fixture.LEDGER)

    def test_a_dangling_link_is_not_read_as_absent(self):
        self.ledger.symlink_to("reconciliations-held.yml")
        for name, (call, _) in self.readers().items():
            with self.subTest(reader=name):
                with self.assertRaises(input_lanes.DanglingOptionalLinkError) as cm:
                    call()
                self.assertNotIsInstance(cm.exception, OSError)
                self.assertIn(LEDGER_NAME, str(cm.exception))
                self.assertNotIn(str(self.root), str(cm.exception))

    def test_a_directory_at_the_ledger_raises_eisdir(self):
        self.ledger.mkdir()
        for name, (call, _) in self.readers().items():
            with self.subTest(reader=name):
                with self.assertRaises(IsADirectoryError):
                    call()

    def test_a_link_loop_at_the_ledger_raises_eloop(self):
        self.ledger.symlink_to(self.ledger.name)
        for name, (call, _) in self.readers().items():
            with self.subTest(reader=name):
                with self.assertRaises(OSError) as cm:
                    call()
                self.assertEqual(cm.exception.errno, errno.ELOOP)

    def test_an_unreadable_ledger_raises_rather_than_reading_as_absent(self):
        self.ledger.write_text(fixture.LEDGER, encoding="utf-8")
        skip_if_root(self)
        self.ledger.chmod(0o000)
        self.addCleanup(self.ledger.chmod, 0o644)
        for name, (call, _) in self.readers().items():
            with self.subTest(reader=name):
                with self.assertRaises(PermissionError):
                    call()


class StrictInvariantReaderTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        (self.root / ".bionic.yml").write_text("docs_dir: bionic\n", encoding="utf-8")
        self.invariants = self.root / "bionic" / "invariants"
        self.invariants.mkdir(parents=True)
        (self.invariants / "rule-901.md").write_text(INVARIANT, encoding="utf-8")

    def test_an_unlistable_invariants_directory_raises(self):
        # POSITIVE CONTROL: listable, the page is read.
        self.assertEqual([i["id"] for i in dp.read_invariants(self.root)], ["INV-0001"])
        skip_if_root(self)
        self.invariants.chmod(0o300)
        self.addCleanup(self.invariants.chmod, 0o755)
        with self.assertRaises(PermissionError):
            dp.read_invariants(self.root)

    def test_a_regular_file_at_the_invariants_path_raises(self):
        shutil.rmtree(self.invariants)
        # POSITIVE CONTROL: confirmed absent, there is no page.
        self.assertEqual(dp.read_invariants(self.root), [])
        self.invariants.write_text("not a directory\n", encoding="utf-8")
        with self.assertRaises(NotADirectoryError):
            dp.read_invariants(self.root)


# ═══════════════════════════════════════════════════════════════════════════
# Census coverage: the census misses no read compile-doctrine makes
# ═══════════════════════════════════════════════════════════════════════════

EXEMPT_FUNCTIONS = members.EXEMPT_FUNCTIONS
EXEMPT_MODULES = members.EXEMPT_MODULES


class DoctrineCensusCoverageTests(unittest.TestCase):
    """One fixture holding every member kind, every optional file present,
    plus an invariants page."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(tmp.cleanup)
        cls.root = Path(tmp.name).resolve() / "repo"
        cls.root.mkdir()
        cls.built = fixture.build(cls.root)
        cls.tree = cls.built["docs"]
        invariants = cls.tree / "invariants"
        invariants.mkdir()
        (invariants / "rule-901.md").write_text(INVARIANT, encoding="utf-8")
        cls.outputs = [cls.tree / "adrs" / "doctrine" / name
                       for name in DoctrineDriver.OUTPUT_NAMES]
        write = subprocess.run([sys.executable, str(CD_PATH), "--repo-root", str(cls.root)],
                               capture_output=True, text=True, timeout=300)
        if write.returncode != 0:
            raise AssertionError(f"fixture write failed: {write.stdout} {write.stderr}")
        record = Path(tmp.name) / "records.json"
        proc = subprocess.run([sys.executable, str(TESTS / "_census_coverage.py"), str(record),
                               str(CD_PATH), "--repo-root", str(cls.root), "--dry-run"],
                              capture_output=True, text=True, timeout=300)
        if proc.returncode != 0:
            raise AssertionError(f"harness failed: {proc.stderr}")
        cls.data = json.loads(record.read_text())

    def gaps(self, members=None):
        return coverage.coverage_gaps(self.data, root=self.root, tree=self.tree,
                                      outputs=self.outputs, exempt_functions=EXEMPT_FUNCTIONS,
                                      exempt_modules=EXEMPT_MODULES, members=members)

    def test_the_fixture_holds_every_optional_file_and_runs_clean(self):
        self.assertEqual(self.data["exit"], 0)
        for relative in ("manifest.yml", "adrs/summaries/backfill-reviews.yml",
                         "adrs/doctrine/_meta.json", "adrs/doctrine/reconciliations.yml",
                         "invariants/rule-901.md"):
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

    def test_the_doctrine_members_are_read_by_doctrine_projection(self):
        page = os.path.abspath(self.tree / "invariants" / "rule-901.md")
        reads = [r for r in self.data["records"]
                 if r["path"] == page and r["access"] == "read" and r["phase"] == "build"]
        self.assertIn(("doctrine_projection", "read_invariants"),
                      {tuple(f) for r in reads for f in r["stack"]})
        member_set = {tuple(m) for m in self.data["members"]}
        self.assertIn(("bionic/invariants", "list"), member_set)
        self.assertIn(("bionic/adrs/doctrine/_meta.json", "read"), member_set)
        self.assertNotIn(("bionic/adrs/summaries/_meta.json", "read"), member_set)

    def test_positive_control_removing_a_member_kind_fails_the_first_direction(self):
        # adrs/doctrine/_meta.json is also a declared output, so the build's
        # read of it is covered as one (X5) and removing it is no control.
        kinds = {"invariant pages": "invariants/", "the ledger": "reconciliations.yml",
                 "council records": "/councils/", "the run snapshot": "run-RUN-001.yaml"}
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
        added = self.data["members"] + [["bionic/adrs/summaries/_meta.json", "read"]]
        _, untouched = self.gaps(added)
        self.assertIn(("bionic/adrs/summaries/_meta.json", "read"), untouched)


if __name__ == "__main__":
    unittest.main()
