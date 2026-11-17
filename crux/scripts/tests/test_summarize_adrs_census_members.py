"""summarize-adrs.py: the census members beyond the ADR tiers take their lanes.

THE CONTRACT. Each member the input census examines — the proposal and
acceptance sidecars, adrs/provenance, the optional files named by path, the
observations concern and its survey receipts, promptbooks/runs, and, by
reference, the acceptance-proof chains and the retirement-standing reads —
takes the lane its failed read takes. A cause attributable to the path is a
DOCUMENT-lane finding: exit 1 and a `validation_errors` entry naming the
input, with no absolute path in the reason. Any other cause, an unlistable
directory, a dangling link at an optional file and a FIFO take the
ENVIRONMENT lane: exit 2, nothing on stdout, and stderr naming the input and
every document finding the same run met. One run names every failing input.

Every refusal runs on a fixture its positive control just ran clean on, in
write mode and in --dry-run, removes one output first and asserts no output
reappears, and asserts every remaining output byte-unchanged. A
permission-based test skips when the effective uid is 0.

The census-coverage test runs the driver in a child process that records
every open, listing and stat, and checks the census against the build's
reads in both directions, with positive controls that show the comparison is
sensitive on the exercised fixture.

Run:
  uv run python3 -m unittest discover -s crux/scripts/tests -p 'test_summarize_adrs_census_members.py'
"""

from __future__ import annotations

import builtins
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
import _census_coverage as coverage  # noqa: E402
import _census_fixture as fixture  # noqa: E402


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# The shared fixture and lane assertions; loaded under a private name so its
# test classes are not collected twice.
base = _load("_summarize_lanes_base", TESTS / "test_summarize_adrs_input_lanes.py")
SA_PATH = SCRIPTS / "summarize-adrs.py"
MODES = base.MODES
skip_if_root = base.skip_if_root
OBSERVATION = "---\nid: OBS-0001\nstatus: observed\nprovenance: recovered\n---\n\n# OBS-0001\n"
MISSING = "symbolic link whose target is missing"


class MemberCase(base.SummarizeInputLaneTestCase):
    """The 0901-0903 tree, plus helpers to lock a path for one test."""

    def lock(self, path: Path, mode: int = 0o000) -> None:
        skip_if_root(self)
        path.chmod(mode)
        self.addCleanup(path.chmod, 0o755 if path.is_dir() else 0o644)

    def dangle(self, path: Path) -> None:
        """Replace `path` with a symbolic link whose target is missing."""
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        elif path.exists() or path.is_symlink():
            path.unlink()
        path.symlink_to(path.name + ".missing")
        self.assertFalse(path.exists())
        self.assertTrue(path.is_symlink())


# ═══════════════════════════════════════════════════════════════════════════
# (e) The proposal and acceptance sidecars
# ═══════════════════════════════════════════════════════════════════════════

class SidecarTests(MemberCase):
    """Sidecars for ADR-0999, which no ADR file names, so none is a chain."""

    def setUp(self) -> None:
        super().setUp()
        for directory in ("proposals", "acceptances"):
            (self.adrs / directory).mkdir()
            (self.adrs / directory / "ADR-0999.json").write_text("{}\n", encoding="utf-8")
        self.sidecar = self.adrs / "acceptances" / "ADR-0999.json"

    def test_an_unreadable_sidecar_is_a_finding(self):
        self.prime()
        self.lock(self.sidecar)
        self.assert_document_lane({self.rel(self.sidecar): "EACCES"})

    def test_a_dangling_sidecar_link_is_a_finding(self):
        self.prime()
        self.dangle(self.adrs / "proposals" / "ADR-0999.json")
        self.assert_document_lane({self.rel(self.adrs / "proposals" / "ADR-0999.json"): "ENOENT"})

    def test_a_directory_named_like_a_sidecar_is_a_finding(self):
        self.prime()
        directory = self.adrs / "acceptances" / "ADR-0998.json"
        directory.mkdir()
        self.assert_document_lane({self.rel(directory): "EISDIR"})

    def test_unlistable_sidecar_directories_are_environment_failures(self):
        self.prime()
        skip_if_root(self)
        for name in ("proposals", "acceptances"):
            with self.subTest(directory=name):
                directory = self.adrs / name
                self.assert_environment_lane([f"environment failure: {self.rel(directory)}"],
                                             locked=directory, lock_mode=0o300)


# ═══════════════════════════════════════════════════════════════════════════
# (f) adrs/provenance
# ═══════════════════════════════════════════════════════════════════════════

class ProvenanceTests(MemberCase):
    def setUp(self) -> None:
        super().setUp()
        self.provenance = self.adrs / "provenance"
        self.provenance.mkdir()
        (self.provenance / ".keep").write_text("", encoding="utf-8")

    def test_a_subdirectory_is_an_eisdir_finding(self):
        self.prime()
        sub = self.provenance / "ADR-0901.yaml"
        sub.mkdir()
        self.assert_document_lane({self.rel(sub): "EISDIR"})

    def test_an_unreadable_record_is_a_finding(self):
        self.prime()
        record = self.provenance / "ADR-0901.yaml"
        record.write_text("schema: '1'\n", encoding="utf-8")
        self.lock(record)
        self.assert_document_lane({self.rel(record): "EACCES"})

    def test_a_symlinked_provenance_directory_keeps_its_refusal(self):
        self.prime()
        real = self.adrs / "provenance-real"
        self.provenance.rename(real)
        self.provenance.symlink_to(real.name)
        self.assert_environment_lane(
            ["refusing to read adrs/provenance: the provenance directory is a symlink"])

    def test_a_symlinked_entry_keeps_its_refusal(self):
        self.prime()
        (self.adrs / "held.yaml").write_text("schema: '1'\n", encoding="utf-8")
        (self.provenance / "ADR-0901.yaml").symlink_to("../held.yaml")
        self.assert_environment_lane(
            ["refusing to read adrs/provenance: ADR-0901.yaml is not a regular record file"])

    def test_a_regular_file_at_the_provenance_path_keeps_its_refusal(self):
        self.prime()
        shutil.rmtree(self.provenance)
        self.provenance.write_text("not a directory\n", encoding="utf-8")
        self.assert_environment_lane(
            ["refusing to read adrs/provenance: the provenance path is not a directory"])

    def test_an_unlistable_provenance_directory_is_an_environment_failure(self):
        self.prime()
        skip_if_root(self)
        self.assert_environment_lane([f"environment failure: {self.rel(self.provenance)}"],
                                     locked=self.provenance, lock_mode=0o300)


# ═══════════════════════════════════════════════════════════════════════════
# (g) The optional files named by path
# ═══════════════════════════════════════════════════════════════════════════

class OptionalFileTests(MemberCase):
    def setUp(self) -> None:
        super().setUp()
        self.reviews = self.summaries / "backfill-reviews.yml"
        self.ledger = self.adrs / "doctrine" / "reconciliations.yml"
        self.meta = self.output_dir / "_meta.json"

    def present(self) -> None:
        self.summaries.mkdir(exist_ok=True)
        self.reviews.write_text(fixture.REVIEWS, encoding="utf-8")
        self.ledger.parent.mkdir(exist_ok=True)
        self.ledger.write_text(fixture.LEDGER, encoding="utf-8")

    def test_a_dangling_link_at_each_optional_file_takes_the_environment_lane(self):
        for name in ("reviews", "ledger", "meta"):
            with self.subTest(file=name):
                # POSITIVE CONTROL: each file absent (the reviews manifest and
                # the ledger) or present (_meta.json) runs clean.
                for path in (self.reviews, self.ledger):
                    if path.is_symlink():
                        path.unlink()
                self.prime()
                path = getattr(self, name)
                path.parent.mkdir(exist_ok=True)
                self.dangle(path)
                self.assert_environment_lane([f"environment failure: {self.rel(path)}", MISSING])
                path.unlink()

    def test_the_ledger_cases_are_findings_naming_it(self):
        cases = {"mode 000": "EACCES", "directory": "EISDIR", "link loop": "ELOOP"}
        for case, code in cases.items():
            with self.subTest(case=case):
                # POSITIVE CONTROL: an absent ledger runs clean.
                if self.ledger.is_symlink() or self.ledger.is_file():
                    self.ledger.unlink()
                elif self.ledger.is_dir():
                    self.ledger.rmdir()
                self.prime()
                self.ledger.parent.mkdir(exist_ok=True)
                locked = None
                if case == "mode 000":
                    skip_if_root(self)
                    self.ledger.write_text(fixture.LEDGER, encoding="utf-8")
                    locked = self.ledger
                elif case == "directory":
                    self.ledger.mkdir()
                else:
                    self.ledger.symlink_to(self.ledger.name)
                self.assert_document_lane({self.rel(self.ledger): code}, locked=locked)
        self.assertEqual(self.ledger.readlink(), Path(self.ledger.name))

    def test_an_unreadable_reviews_manifest_is_a_finding(self):
        self.present()
        self.prime()
        self.lock(self.reviews)
        self.assert_document_lane({self.rel(self.reviews): "EACCES"})

    def test_an_unreadable_meta_json_is_an_output_finding(self):
        self.prime()
        skip_if_root(self)

        def check(rc, out, err, ctx):
            self.assertEqual(rc, 1, ctx)
            errors = json.loads(out)["validation_errors"]
            self.assertEqual([e["file"] for e in errors], [self.rel(self.meta)], ctx)
            self.assertIn("EACCES", errors[0]["error"], ctx)
            self.assertIn("rerun the regenerator", errors[0]["error"], ctx)
            self.assert_no_absolute_path(errors[0]["error"], ctx)
        before = self.meta.read_bytes()
        self.refusal_runs(check, locked=self.meta)
        self.assertEqual(self.meta.read_bytes(), before)


class CollectionTests(MemberCase):
    def test_an_adr_the_ledger_and_the_reviews_manifest_are_named_in_one_payload(self):
        reviews = self.summaries / "backfill-reviews.yml"
        ledger = self.adrs / "doctrine" / "reconciliations.yml"
        self.summaries.mkdir()
        reviews.write_text(fixture.REVIEWS, encoding="utf-8")
        ledger.parent.mkdir()
        ledger.write_text(fixture.LEDGER, encoding="utf-8")
        # POSITIVE CONTROL: all three read clean on the same fixture.
        self.prime()
        for path in (self.target, ledger, reviews):
            self.lock(path)
        self.assert_document_lane({self.rel(self.target): "EACCES",
                                   self.rel(ledger): "EACCES",
                                   self.rel(reviews): "EACCES"})


# ═══════════════════════════════════════════════════════════════════════════
# (h) The observations concern and its survey receipts
# ═══════════════════════════════════════════════════════════════════════════

class ObservationTests(MemberCase):
    def setUp(self) -> None:
        super().setUp()
        self.manifest.write_text(
            'schema_version: "5"\nconcerns_enabled:\n  - adrs\n  - observations\n'
            "adr:\n  next_number: 1000\n  governs_from: 1\n", encoding="utf-8")
        self.obs = self.tree / "observations"
        self.obs.mkdir()
        self.record = self.obs / "OBS-0001-x.md"
        self.record.write_text(OBSERVATION, encoding="utf-8")
        (self.obs / "index.md").write_text("# Observations\n", encoding="utf-8")
        self.surveys = self.obs / "_surveys"
        (self.surveys / "SVY-0009").mkdir(parents=True)        # a batch with no receipt
        (self.surveys / ".DS_Store").write_bytes(b"\x00\x01")

    def test_the_candidate_rule_reads_records_and_skips_what_no_reader_admits(self):
        # POSITIVE CONTROL: the fixture runs clean, and the census reads the
        # record and probes the receipt it would read.
        self.prime()
        members = dict(sp.input_census(self.root, driver=self.DRIVER).members)
        self.assertEqual(members[self.rel(self.record)], "read")
        self.assertEqual(members[self.rel(self.surveys)], "list")
        self.assertEqual(members[self.rel(self.surveys / "SVY-0009" / "receipt.yml")], "read")
        self.assertNotIn(self.rel(self.surveys / ".DS_Store"), members)
        self.assertNotIn(self.rel(self.obs / "index.md"), members)

    def test_a_dangling_listed_record_link_is_a_finding(self):
        self.prime()
        link = self.obs / "OBS-0002-x.md"
        link.symlink_to("OBS-0002-held.md")
        self.assert_document_lane({self.rel(link): "ENOENT"})

    def test_an_unreadable_record_is_a_finding(self):
        self.prime()
        self.lock(self.record)
        self.assert_document_lane({self.rel(self.record): "EACCES"})

    def test_a_directory_named_like_a_record_is_a_finding(self):
        self.prime()
        directory = self.obs / "OBS-0002-x.md"
        directory.mkdir()
        self.assert_document_lane({self.rel(directory): "EISDIR"})

    def test_unlistable_observation_directories_are_environment_failures(self):
        self.prime()
        skip_if_root(self)
        for directory in (self.obs, self.surveys):
            with self.subTest(directory=directory.name):
                self.assert_environment_lane([f"environment failure: {self.rel(directory)}"],
                                             locked=directory, lock_mode=0o300)

    def test_a_dangling_link_at_the_batch_level_is_a_finding(self):
        self.prime()
        link = self.surveys / "SVY-0010"
        link.symlink_to("SVY-0010-held")
        self.assert_document_lane({self.rel(link): "ENOENT"})

    def test_a_dangling_receipt_takes_the_environment_lane(self):
        self.prime()
        receipt = self.surveys / "SVY-0009" / "receipt.yml"
        receipt.symlink_to("receipt-held.yml")
        self.assert_environment_lane([f"environment failure: {self.rel(receipt)}", MISSING])

    def test_a_confirmed_absent_concern_directory_keeps_its_text(self):
        self.prime()
        shutil.rmtree(self.obs)
        self.assert_environment_lane(["cannot read the observations source: the observations "
                                      "directory", "is absent"])

    def test_a_tree_escaping_adr_keeps_its_refusal_beside_an_observation_finding(self):
        outside = self.root / "outside-0904.md"
        outside.write_text(base.adr(904), encoding="utf-8")
        self.prime()
        skip_if_root(self)
        (self.adrs / "ADR-0904-out.md").symlink_to(outside)
        self.lock(self.record)
        self.assert_environment_lane([
            "refusing to read ADR-0904-out.md: it does not resolve to a file inside",
            f"document finding met in the same run: {self.rel(self.record)}"])

    def test_eio_on_an_adr_takes_the_environment_lane_over_an_observation_finding(self):
        self.prime()
        skip_if_root(self)
        self.lock(self.record)
        seen = []

        def fake_open(file, *a, **kw):
            if Path(os.fsdecode(file)).name == self.target.name:
                seen.append(file)
                raise OSError(errno.EIO, "Input/output error", str(file))
            return builtins.open(file, *a, **kw)

        with mock.patch.object(sp, "open", fake_open, create=True):
            self.assert_environment_lane([
                f"environment failure: {self.rel(self.target)}", "Input/output error",
                f"document finding met in the same run: {self.rel(self.record)}"])
        self.assertTrue(seen, "the stub was never reached")


class ObservationsOnlyManifestTests(MemberCase):
    def test_an_unreadable_manifest_on_an_observations_only_tree_names_the_manifest(self):
        shutil.rmtree(self.adrs)
        self.manifest.write_text('schema_version: "5"\nconcerns_enabled:\n  - observations\n',
                                 encoding="utf-8")
        obs = self.tree / "observations"
        obs.mkdir()
        (obs / "OBS-0001-x.md").write_text(OBSERVATION, encoding="utf-8")
        # POSITIVE CONTROL: the readable manifest decides the tree is
        # observations-only, so no adrs directory is required: the run reads
        # the tree and reports drift, not a "not found" failure.
        rc, out, err = self.run_sa("--dry-run")
        self.assertEqual(rc, 1, err)
        self.assertTrue(json.loads(out)["drift"], out)
        self.assertNotIn("not found", err)
        self.lock(self.manifest)
        for mode, args in MODES:
            with self.subTest(mode=mode):
                files = base.tree_files(self.root)
                rc, out, err = self.run_sa(*args)
                self.assertEqual(rc, 1, err)
                errors = json.loads(out)["validation_errors"]
                self.assertEqual([e["file"] for e in errors], [self.rel(self.manifest)])
                self.assertIn("EACCES", errors[0]["error"])
                self.assert_no_absolute_path(errors[0]["error"], err)
                self.assertNotIn("not found", err)
                self.assertEqual(base.tree_files(self.root), files)


# ═══════════════════════════════════════════════════════════════════════════
# (i) promptbooks/runs
# ═══════════════════════════════════════════════════════════════════════════

class RunSnapshotTests(MemberCase):
    def setUp(self) -> None:
        super().setUp()
        self.runs = self.tree / "promptbooks" / "runs"
        self.run_dir = self.runs / "PB-0001-x"
        self.run_dir.mkdir()
        self.snapshot = self.run_dir / "run-RUN-001.yaml"
        self.snapshot.write_text(fixture.RUN, encoding="utf-8")
        (self.runs / ".DS_Store").write_bytes(b"\x00\x01")

    def test_the_candidate_rule_reads_snapshots_and_skips_a_stray_file(self):
        # POSITIVE CONTROL: the snapshot binds ADR-0901, so it is read.
        self.prime()
        self.assertIn("| ADR-0901 | yes | PB-0001 |",
                      (self.summaries / "implementation-map.md").read_text())
        members = dict(sp.input_census(self.root, driver=self.DRIVER).members)
        self.assertEqual(members[self.rel(self.snapshot)], "read")
        self.assertEqual(members[self.rel(self.run_dir)], "list")
        self.assertNotIn(self.rel(self.runs / ".DS_Store"), members)

    def test_a_dangling_link_at_the_first_level_is_a_finding(self):
        self.prime()
        link = self.runs / "PB-0002-x"
        link.symlink_to("PB-0002-held")
        self.assert_document_lane({self.rel(link): "ENOENT"})

    def test_an_unreadable_snapshot_is_a_finding(self):
        self.prime()
        self.lock(self.snapshot)
        self.assert_document_lane({self.rel(self.snapshot): "EACCES"})

    def test_a_snapshot_that_is_not_utf8_is_a_finding(self):
        self.prime()
        self.snapshot.write_bytes(b"book_id: PB-0001\nrun_id: \xff\n")
        self.assert_document_lane({self.rel(self.snapshot): "not valid UTF-8"})

    def test_unlistable_run_directories_are_environment_failures(self):
        self.prime()
        skip_if_root(self)
        for directory in (self.runs, self.run_dir):
            with self.subTest(directory=directory.name):
                self.assert_environment_lane([f"environment failure: {self.rel(directory)}"],
                                             locked=directory, lock_mode=0o300)


class FifoTests(MemberCase):
    """A FIFO named like a run snapshot is named and never opened.

    The driver runs in a child process with a timeout, so an open that
    blocked on the FIFO fails the test instead of hanging the suite.
    """

    def child(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(self.SCRIPT_PATH), "--repo-root", str(self.root), *args],
                              capture_output=True, text=True, timeout=120)

    def test_a_fifo_named_like_a_snapshot_exits_two_without_blocking(self):
        run_dir = self.tree / "promptbooks" / "runs" / "PB-0001-x"
        run_dir.mkdir()
        (run_dir / "run-RUN-001.yaml").write_text(fixture.RUN, encoding="utf-8")
        # POSITIVE CONTROL: the regular-file snapshot beside it reads clean.
        self.assertEqual(self.child().returncode, 0)
        self.assertEqual(self.child("--dry-run").returncode, 0)
        fifo = run_dir / "run-RUN-002.yaml"
        os.mkfifo(fifo)
        before = self.outputs()
        for mode, args in MODES:
            with self.subTest(mode=mode):
                proc = self.child(*args)
                self.assertEqual(proc.returncode, 2, proc.stderr)
                self.assertEqual(proc.stdout, "")
                self.assertIn(f"{self.rel(fifo)}: is a FIFO, not a regular file; it was not opened",
                              proc.stderr)
                self.assertEqual(self.outputs(), before)


# ═══════════════════════════════════════════════════════════════════════════
# (k) and (l): the acceptance-proof chains and the retirement-standing reads
# ═══════════════════════════════════════════════════════════════════════════

class ChainCase(MemberCase):
    """A tree with a real native-Lite acceptance: ADR-1000 active and
    Accepted, ADR-1001 archived as Superseded. Built once per class."""

    template: Path
    names: dict

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(tmp.cleanup)
        root = Path(tmp.name).resolve() / "repo"
        root.mkdir()
        built = fixture.build(root, survey=False)
        cls.template = root
        cls.names = {key: value.relative_to(root) for key, value in built.items()
                     if isinstance(value, Path) and value != root}
        cls.ids = {key: value for key, value in built.items() if isinstance(value, str)}

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve() / "repo"
        shutil.copytree(self.template, self.root, symlinks=True)
        self.tree = self.root / "bionic"
        self.adrs = self.tree / "adrs"
        self.manifest = self.tree / "manifest.yml"
        self.target = self.adrs / "ADR-0903-x.md"
        self.summaries = self.adrs / "summaries"
        self.council = self.root / self.names["active_council"]
        self.archived_council = self.root / self.names["archived_council"]

    def prime(self) -> None:
        """POSITIVE CONTROL: regenerate, then the same fixture is clean under
        --dry-run, and the accepted ADR's rule is published."""
        rc, out, err = self.run_sa()
        self.assertEqual(rc, 0, f"regenerate: {out!r} {err!r}")
        rc, out, err = self.run_sa("--dry-run")
        self.assertEqual(rc, 0, f"control: {out!r} {err!r}")
        self.assertEqual(json.loads(out), {"drift": False, "paths": []})
        self.assertIn(f"{self.ids['active_id']}/keep-rule",
                      (self.output_dir / self.CONTROL_OUTPUT).read_text())

    def docs_rel(self, path: Path) -> str:
        return str(path.relative_to(self.tree))

    def stub_read_bytes(self, target: Path, code: int, seen: list):
        real = Path.read_bytes

        def read_bytes(path, *a, **kw):
            if Path(path) == target:
                seen.append(path)
                raise OSError(code, os.strerror(code), str(path))
            return real(path, *a, **kw)
        return mock.patch.object(Path, "read_bytes", read_bytes)


class AcceptanceChainTests(ChainCase):
    def test_the_census_reads_each_chain_member(self):
        # POSITIVE CONTROL: the fixture runs clean, and the census reads both
        # council records and probes the current binding.
        self.prime()
        members = sp.input_census(self.root, driver=self.DRIVER).members
        self.assertIn((self.rel(self.council), "read"), members)
        self.assertIn((self.rel(self.archived_council), "read"), members)
        binding = self.adrs / "acceptances" / f"{self.ids['active_id']}.current.json"
        self.assertIn((self.rel(binding), "stat"), members)

    def test_an_unreadable_council_record_is_a_finding_naming_it(self):
        self.prime()
        self.lock(self.council)
        self.assert_document_lane({self.rel(self.council): "EACCES"})

    def test_an_unreadable_archived_hosts_council_record_is_a_finding(self):
        self.prime()
        self.lock(self.archived_council)
        self.assert_document_lane({self.rel(self.archived_council): "EACCES"})

    def test_eio_on_a_council_record_takes_the_environment_lane(self):
        self.prime()
        seen = []

        def fake_open(file, *a, **kw):
            if Path(os.fsdecode(file)) == self.council:
                seen.append(file)
                raise OSError(errno.EIO, "Input/output error", str(file))
            return builtins.open(file, *a, **kw)

        with mock.patch.object(sp, "open", fake_open, create=True):
            self.assert_environment_lane([f"environment failure: {self.rel(self.council)}",
                                          "Input/output error"])
        self.assertTrue(seen, "the stub was never reached")

    def test_a_deleted_council_record_is_a_required_file_finding(self):
        self.prime()
        self.council.unlink()
        self.assert_document_lane({self.rel(self.council): "is a required input and is absent"})

    def test_an_unlistable_recoveries_directory_names_each_probe(self):
        recoveries = self.adrs / "acceptances" / "recoveries"
        recoveries.mkdir()
        # POSITIVE CONTROL: an empty recoveries directory runs clean.
        self.prime()
        self.lock(recoveries)
        # The accepted ADR's chain, the archived host's and the Deprecated
        # ADR-0904's standing each probe their own recovery path.
        self.assert_document_lane({
            self.rel(recoveries / self.ids["active_id"]): "EACCES",
            self.rel(recoveries / self.ids["archived_id"]): "EACCES",
            self.rel(recoveries / "ADR-0904"): "EACCES"})

    def test_a_fifo_at_the_council_record_takes_the_environment_lane_unopened(self):
        self.prime()
        self.council.unlink()
        os.mkfifo(self.council)
        for mode, args in MODES:
            with self.subTest(mode=mode):
                proc = subprocess.run(
                    [sys.executable, str(self.SCRIPT_PATH), "--repo-root", str(self.root), *args],
                    capture_output=True, text=True, timeout=120)
                self.assertEqual(proc.returncode, 2, proc.stderr)
                self.assertEqual(proc.stdout, "")
                self.assertIn(f"{self.rel(self.council)}: is a FIFO, not a regular file; it was "
                              "not opened", proc.stderr)


class LateChainFailureTests(ChainCase):
    """A chain read that fails in the build after a clean census keeps its lane."""

    def late(self, code: int, check) -> None:
        self.prime()
        seen: list = []
        with self.stub_read_bytes(self.council, code, seen):
            check()
        self.assertTrue(seen, "the build's read was never reached")

    def test_a_late_eacces_is_a_finding_naming_the_record(self):
        self.late(errno.EACCES, lambda: self.assert_document_lane(
            {self.docs_rel(self.council): "EACCES"}))

    def test_a_late_enoent_is_the_required_file_finding(self):
        self.late(errno.ENOENT, lambda: self.assert_document_lane(
            {self.docs_rel(self.council): "is a required input and is absent"}))

    def test_a_late_eio_takes_the_environment_lane(self):
        self.late(errno.EIO, lambda: self.assert_environment_lane(
            [f"environment failure: {self.docs_rel(self.council)}"]))

    def test_a_late_enoent_on_the_archived_hosts_record_keeps_the_standing_refusal(self):
        # A lost record behind a retirement keeps the standing refusal and its
        # repair, at exit 1, naming the record by its docs-relative path.
        self.prime()
        seen: list = []
        name = self.docs_rel(self.archived_council)

        def check(rc, out, err, ctx):
            self.assertEqual(rc, 1, ctx)
            problems = json.loads(out)["validation_errors"]
            text = json.dumps(problems)
            self.assertIn(name, text, ctx)
            self.assertIn("does not resolve", text, ctx)
            self.assertIn("restore the acceptance record", text, ctx)
            self.assert_no_absolute_path(text, ctx)
        with self.stub_read_bytes(self.archived_council, errno.ENOENT, seen):
            self.refusal_runs(check)
        self.assertTrue(seen, "the build's read was never reached")

    def test_a_late_eacces_on_the_archived_hosts_record_is_a_finding(self):
        self.prime()
        seen: list = []
        with self.stub_read_bytes(self.archived_council, errno.EACCES, seen):
            self.assert_document_lane({self.docs_rel(self.archived_council): "EACCES"})
        self.assertTrue(seen, "the build's read was never reached")


# ═══════════════════════════════════════════════════════════════════════════
# The unseamed readers: optional files, strict listings, the chain lane
# ═══════════════════════════════════════════════════════════════════════════

class OptionalFileReaderTests(unittest.TestCase):
    """Each optional-file reader's unseamed branch with a dangling link."""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        (self.root / ".bionic.yml").write_text("docs_dir: bionic\n", encoding="utf-8")
        self.tree = self.root / "bionic"
        self.adrs = self.tree / "adrs"
        (self.adrs / "summaries").mkdir(parents=True)
        (self.adrs / "doctrine").mkdir()
        self.obs = self.tree / "observations"
        (self.obs / "_surveys" / "SVY-0001").mkdir(parents=True)

    def readers(self):
        return {
            "read_manifest": (self.tree / "manifest.yml",
                              lambda: sp.read_manifest(self.root), {}),
            "declared_input_domain": (self.adrs / "summaries" / "_meta.json",
                                      lambda: sp.declared_input_domain(self.adrs / "summaries"),
                                      None),
            "backfill_reviews_sha256": (self.adrs / "summaries" / "backfill-reviews.yml",
                                        lambda: sp.backfill_reviews_sha256(self.adrs), None),
            "read_reviews": (self.adrs / "summaries" / "backfill-reviews.yml",
                             lambda: sp.read_reviews(self.adrs),
                             {"batches": {}, "receipts": [], "no_rule": []}),
            "signed_reconciliation_handles": (self.adrs / "doctrine" / "reconciliations.yml",
                                              lambda: sp.signed_reconciliation_handles(self.adrs),
                                              set()),
            "survey_receipt_paths": (self.obs / "_surveys" / "SVY-0001" / "receipt.yml",
                                     lambda: sp.survey_receipt_paths(self.obs), []),
        }

    def test_an_absent_optional_file_reads_as_absent(self):
        for name, (_, call, absent) in self.readers().items():
            with self.subTest(reader=name):
                self.assertEqual(call(), absent)

    def test_a_dangling_link_is_not_read_as_absent(self):
        for name, (path, call, _) in self.readers().items():
            with self.subTest(reader=name):
                path.symlink_to(path.name + ".missing")
                try:
                    with self.assertRaises(input_lanes.DanglingOptionalLinkError) as cm:
                        call()
                    self.assertNotIsInstance(cm.exception, OSError)
                    self.assertNotIn(str(self.root), str(cm.exception))
                finally:
                    path.unlink()

    def test_a_directory_at_an_optional_file_raises_eisdir(self):
        for name, (path, call, _) in self.readers().items():
            with self.subTest(reader=name):
                path.mkdir()
                try:
                    with self.assertRaises(IsADirectoryError):
                        call()
                finally:
                    path.rmdir()

    def test_an_unreadable_meta_json_is_not_read_as_no_declaration(self):
        meta = self.adrs / "summaries" / "_meta.json"
        meta.write_text('{"input_domain": ["adrs"]}', encoding="utf-8")
        # POSITIVE CONTROL: readable, the declaration is returned.
        self.assertEqual(sp.declared_input_domain(self.adrs / "summaries"), ["adrs"])
        skip_if_root(self)
        meta.chmod(0o000)
        self.addCleanup(meta.chmod, 0o644)
        with self.assertRaises(PermissionError):
            sp.declared_input_domain(self.adrs / "summaries")

    def test_text_that_is_not_json_still_reads_as_no_declaration(self):
        meta = self.adrs / "summaries" / "_meta.json"
        meta.write_text("not json", encoding="utf-8")
        self.assertIsNone(sp.declared_input_domain(self.adrs / "summaries"))


class StrictReaderTests(unittest.TestCase):
    """The direct reads approach 1 converts raise rather than read as empty."""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        (self.root / ".bionic.yml").write_text("docs_dir: bionic\n", encoding="utf-8")
        self.tree = self.root / "bionic"
        self.adrs = self.tree / "adrs"
        self.adrs.mkdir(parents=True)
        (self.adrs / "ADR-0901-x.md").write_text(base.adr(901), encoding="utf-8")

    def lock(self, path: Path, mode: int = 0o000) -> None:
        skip_if_root(self)
        path.chmod(mode)
        self.addCleanup(path.chmod, 0o755)

    def test_an_unlistable_provenance_directory_raises(self):
        provenance = self.adrs / "provenance"
        provenance.mkdir()
        (provenance / ".keep").write_text("", encoding="utf-8")
        # POSITIVE CONTROL: listable, it holds no record.
        self.assertEqual(sp.provenance_entries(self.adrs), [])
        self.lock(provenance)
        with self.assertRaises(PermissionError):
            sp.provenance_entries(self.adrs)

    def test_provenance_refusals_keep_their_text(self):
        provenance = self.adrs / "provenance"
        provenance.mkdir()
        (provenance / "sub").mkdir()
        with self.assertRaisesRegex(OSError, "sub is not a regular record file"):
            sp.provenance_entries(self.adrs)
        shutil.rmtree(provenance)
        (self.adrs / "real").mkdir()
        provenance.symlink_to("real")
        with self.assertRaisesRegex(OSError, "the provenance directory is a symlink"):
            sp.provenance_entries(self.adrs)

    def test_an_unlistable_archive_raises_in_the_cohort_domain(self):
        archive = self.adrs / "archive"
        archive.mkdir()
        (archive / "ADR-0902-x.md").write_text(base.adr(902, status="Superseded"),
                                               encoding="utf-8")
        # POSITIVE CONTROL: listable, both tiers supply their ids.
        self.assertEqual(sp._adr_ids_including_archive(self.adrs), {"ADR-0901", "ADR-0902"})
        self.lock(archive, 0o300)
        with self.assertRaises(PermissionError):
            sp._adr_ids_including_archive(self.adrs)

    def test_an_unlistable_run_directory_raises(self):
        runs = self.tree / "promptbooks" / "runs"
        run_dir = runs / "PB-0001-x"
        run_dir.mkdir(parents=True)
        (run_dir / "run-RUN-001.yaml").write_text(fixture.RUN, encoding="utf-8")
        # POSITIVE CONTROL: listable, the snapshot binds ADR-0901.
        self.assertIn("ADR-0901", sp.read_run_bindings(runs))
        self.lock(run_dir, 0o300)
        with self.assertRaises(PermissionError):
            sp.read_run_bindings(runs)


class ChainLaneTests(unittest.TestCase):
    def test_each_cause_takes_its_lane_naming_the_docs_relative_path(self):
        name = "adrs/councils/council-x.json"
        cases = [(errno.ENOENT, sp.InputLaneRefusal, "is a required input and is absent"),
                 (errno.ENOTDIR, sp.InputLaneRefusal, "is a required input and is absent"),
                 (errno.EACCES, sp.InputLaneRefusal, "EACCES"),
                 (errno.EIO, input_lanes.EnvironmentLaneError, "Input/output error")]
        for code, kind, text in cases:
            with self.subTest(errno=errno.errorcode[code]):
                exc = sp._chain_lane(name, OSError(code, os.strerror(code), "/abs/" + name))
                self.assertIsInstance(exc, kind)
                if kind is sp.InputLaneRefusal:
                    self.assertEqual([p["file"] for p in exc.problems], [name])
                    self.assertIn(text, exc.problems[0]["error"])
                    self.assertNotIn("/abs/", exc.problems[0]["error"])
                else:
                    self.assertIn(name, exc.failures[0])
                    self.assertIn(text, exc.failures[0])


# ═══════════════════════════════════════════════════════════════════════════
# Census coverage: the census misses no read the build makes
# ═══════════════════════════════════════════════════════════════════════════

#: X1, X2 (by function), X3, X4 (by module), and X6, the survey state
#: derivation in survey_sheet, a module outside this cycle's scope: it reads
#: the operations log, the journal, the staged directory and the arch state
#: file to decide a batch's state, and the census takes none of them.
EXEMPT_FUNCTIONS = frozenset({("summaries_projection", "_read_operation_log"),
                              ("summaries_projection", "backfill_problems"),
                              ("summaries_projection", "rule_length_advisories"),
                              ("survey_sheet", "batch_state")})
EXEMPT_MODULES = frozenset({"implementation_migration", "adr_migration_publication",
                            "observation_evidence"})


class CensusCoverageTests(unittest.TestCase):
    """One fixture holding every member kind, every optional file present."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(tmp.cleanup)
        cls.root = Path(tmp.name).resolve() / "repo"
        cls.root.mkdir()
        cls.built = fixture.build(cls.root)
        cls.tree = cls.built["docs"]
        cls.outputs = [cls.tree / "adrs" / "summaries" / name for name in base.OUTPUTS]
        write = subprocess.run([sys.executable, str(SA_PATH), "--repo-root", str(cls.root)],
                               capture_output=True, text=True, timeout=300)
        if write.returncode != 0:
            raise AssertionError(f"fixture write failed: {write.stdout} {write.stderr}")
        record = Path(tmp.name) / "records.json"
        proc = subprocess.run([sys.executable, str(TESTS / "_census_coverage.py"), str(record),
                               str(SA_PATH), "--repo-root", str(cls.root), "--dry-run"],
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

    def test_records_carry_phase_function_and_access_kind_attribution(self):
        council = os.path.abspath(self.built["active_council"])
        reads = [r for r in self.data["records"] if r["path"] == council and r["access"] == "read"]
        self.assertEqual({r["phase"] for r in reads}, {"census", "build"})
        census = [r for r in reads if r["phase"] == "census"]
        self.assertTrue(all(r["module"] == "summaries_projection" for r in census))
        build = [r for r in reads if r["phase"] == "build"]
        self.assertIn(("summaries_projection", "collect_records"),
                      {tuple(f) for r in build for f in r["stack"]})
        # Attribution looks past the generic helpers.
        self.assertFalse(any(r["module"] in coverage.GENERIC_MODULES for r in self.data["records"]))

    def test_positive_control_removing_a_member_kind_fails_the_first_direction(self):
        kinds = {"council records": "/councils/", "the run snapshot": "run-RUN-001.yaml",
                 "the ledger": "reconciliations.yml", "the survey receipt": "receipt.yml",
                 "observation records": "observations/OBS-"}
        for kind, marker in kinds.items():
            with self.subTest(kind=kind):
                members = [m for m in self.data["members"] if marker not in m[0]]
                self.assertLess(len(members), len(self.data["members"]), marker)
                uncovered, _ = self.gaps(members)
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
