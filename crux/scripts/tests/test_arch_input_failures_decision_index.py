"""ADR-0181 in the decision index — absent, unreadable, unparseable and unlistable inputs.

The decision index is completeness-dependent (IDR approach 13), so every ADR
read, the `adrs/index.md` projection read and the frontmatter parse run in the
document lane: an over-cap, undecodable, unparseable, symbolic-link or
unreadable input is a document finding and the derive writes nothing. The
decision directory is optional input: its confirmed absence keeps the stub,
and a directory the process cannot list is the environment failure naming it.
Every refusing case asserts the byte-unchanged arch tree and pairs with a
positive control on the same fixture.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from arch_input_failures_support import (
    ARCH_PKG,
    CORE,
    SCRIPTS,
    active_ledger,
    arch_snapshot,
    broad_handler_violations,
    coverage,
    crux_repo,
    run_cli,
    skip_if_root,
    write,
)

_FIXTURE = "bionic/adrs/ADR-0001-fixture.md"
_ARCHIVED = ("---\nid: ADR-0009\ntitle: \"An old thing\"\nstatus: Superseded\n"
             "date: 2025-01-01\ntags: [fixture]\n---\n\n# ADR-0009 — An old thing\n")


def _write_adr_index(root: Path) -> None:
    """Write the regenerator's own `adrs/index.md`, so the projection applies."""
    spec = importlib.util.spec_from_file_location(
        "_test_di_adr_index", SCRIPTS / "generate-adr-index.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    path, text = mod.build(root)
    Path(path).write_text(text, encoding="utf-8")


class _Repo(unittest.TestCase):
    PROJECTED = False

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve()
        crux_repo(self.root)
        if self.PROJECTED:
            _write_adr_index(self.root)
        code, _out, payload, err = run_cli(self.root)
        self.assertEqual(code, 0, (payload, err))
        self.before = arch_snapshot(self.root)

    def tearDown(self):
        for path in [self.root, *self.root.rglob("*")]:
            try:
                if not path.is_symlink():
                    os.chmod(path, 0o755 if path.is_dir() else 0o644)
            except OSError:
                pass
        self._tmp.cleanup()

    def assert_document_lane(self, name: str, text: str | None = None) -> None:
        for argv in ((), ("--dry-run",)):
            with self.subTest(argv=argv):
                code, _out, payload, err = run_cli(self.root, *argv)
                self.assertEqual(code, 1, (payload, err))
                found = [f for f in payload["validation_errors"] if f["file"] == name]
                self.assertTrue(found, payload)
                if text is not None:
                    self.assertTrue(any(text in f["error"] for f in found), found)
                self.assertEqual(arch_snapshot(self.root), self.before)

    def assert_environment_lane(self, name: str) -> None:
        for argv in ((), ("--dry-run",)):
            with self.subTest(argv=argv):
                code, out, payload, err = run_cli(self.root, *argv)
                self.assertEqual((code, out), (2, ""), (payload, err))
                self.assertIn(name, err)
                self.assertEqual(arch_snapshot(self.root), self.before)

    def decision_index(self) -> str:
        return (self.root / "bionic/arch/decision-index.md").read_text(encoding="utf-8")


class FrontmatterPathTests(_Repo):
    """The fixture has no `adrs/index.md`: the index derives from frontmatter."""

    def test_positive_control_the_index_populates_with_no_finding(self):
        rec = coverage(self.root)["decision-index"]
        self.assertEqual(rec["verdict"], "populated")
        self.assertEqual(rec["omissions"], [])
        self.assertIn("derived from ADR frontmatter", self.decision_index())
        self.assertIn("Accept a thing", self.decision_index())

    def test_an_over_cap_adr_is_a_document_finding(self):
        write(self.root, "bionic/adrs/ADR-0002-big.md", b" " * (2 * 1024 * 1024 + 1))
        self.assert_document_lane("bionic/adrs/ADR-0002-big.md", "over-cap")

    def test_a_symbolic_link_adr_is_a_document_finding(self):
        os.symlink("ADR-0001-fixture.md", self.root / "bionic/adrs/ADR-0003-link.md")
        self.assert_document_lane("bionic/adrs/ADR-0003-link.md", "not-a-file")

    def test_a_mode_000_adr_is_a_document_finding(self):
        skip_if_root(self)
        os.chmod(self.root / _FIXTURE, 0)
        self.assert_document_lane(_FIXTURE)

    def test_an_undecodable_adr_is_a_document_finding(self):
        write(self.root, "bionic/adrs/ADR-0004-bad.md",
              b"---\ntitle: \"B\xff\"\nstatus: Accepted\n---\n")
        self.assert_document_lane("bionic/adrs/ADR-0004-bad.md", "undecodable")

    def test_an_adr_whose_frontmatter_does_not_parse_is_a_document_finding(self):
        write(self.root, "bionic/adrs/ADR-0005-yaml.md",
              "---\ntitle: [unclosed\nstatus: Accepted\n---\n")
        self.assert_document_lane("bionic/adrs/ADR-0005-yaml.md", "unparseable")

    def test_an_adr_whose_frontmatter_is_not_a_mapping_is_a_document_finding(self):
        write(self.root, "bionic/adrs/ADR-0006-list.md", "---\n- a\n- b\n---\n")
        self.assert_document_lane("bionic/adrs/ADR-0006-list.md", "unparseable")

    def test_positive_control_a_second_valid_adr_is_listed(self):
        write(self.root, "bionic/adrs/ADR-0007-ok.md",
              "---\ntitle: \"Second thing\"\nstatus: Accepted\ndate: 2026-01-03\n---\n")
        code, _out, payload, err = run_cli(self.root)
        self.assertEqual(code, 0, (payload, err))
        self.assertIn("Second thing", self.decision_index())
        self.assertEqual(coverage(self.root)["decision-index"]["omissions"], [])

    def test_a_fifo_adr_is_an_environment_failure(self):
        os.mkfifo(self.root / "bionic/adrs/ADR-0008-trap.md")
        self.assert_environment_lane("bionic/adrs/ADR-0008-trap.md")


class DecisionDirectoryTests(_Repo):

    def test_a_confirmed_absent_decision_directory_keeps_the_stub(self):
        for p in (self.root / "bionic" / "adrs").iterdir():
            p.unlink()
        (self.root / "bionic" / "adrs").rmdir()
        code, _out, payload, err = run_cli(self.root)
        self.assertEqual(code, 0, (payload, err))
        self.assertEqual(coverage(self.root)["decision-index"]["verdict"], "stubbed")

    def test_an_unlistable_decision_directory_is_an_environment_failure(self):
        skip_if_root(self)
        os.chmod(self.root / "bionic/adrs", 0o300)    # searchable, not listable
        self.assert_environment_lane("bionic/adrs")

    def test_an_unlistable_archive_directory_is_an_environment_failure(self):
        skip_if_root(self)
        write(self.root, "bionic/adrs/archive/ADR-0009-old.md", _ARCHIVED)
        _write_adr_index(self.root)   # the projected path reads the archive tier
        code, _out, payload, err = run_cli(self.root)
        self.assertEqual(code, 0, (payload, err))
        self.assertIn("projected from `adrs/index.md`", self.decision_index())
        self.before = arch_snapshot(self.root)
        os.chmod(self.root / "bionic/adrs/archive", 0o300)
        self.assert_environment_lane("bionic/adrs/archive")


class DecisionDirectoryUnitTests(unittest.TestCase):
    """The presence decision, driven directly under an active ledger: the
    configuration and authority readers that run before the extractor would
    otherwise meet a broken decision directory first."""

    def test_a_regular_file_at_the_decision_directory_is_an_environment_failure(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            write(root, "bionic/adrs", "not a directory\n")
            with active_ledger(root, "decision-index"):
                with self.assertRaises(CORE.ArchEnvironmentFailure) as ctx:
                    CORE._decision_directory_present(root / "bionic/adrs")
            self.assertIn("bionic/adrs", ctx.exception.failures[0])

    def test_positive_control_absent_is_false_and_a_directory_is_true(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            with active_ledger(root, "decision-index") as ledger:
                self.assertFalse(CORE._decision_directory_present(root / "bionic/adrs"))
                (root / "bionic/adrs").mkdir(parents=True)
                self.assertTrue(CORE._decision_directory_present(root / "bionic/adrs"))
            self.assertEqual(ledger.findings, [])

    def test_a_stat_failure_other_than_absence_is_an_environment_failure(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            err = PermissionError(13, "Permission denied")
            with active_ledger(root, "decision-index"), \
                    mock.patch.object(CORE.os, "stat", side_effect=err):
                with self.assertRaises(CORE.ArchEnvironmentFailure):
                    CORE._decision_directory_present(root / "bionic/adrs")

    def test_without_a_ledger_the_exists_predicate_answers(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            write(root, "bionic/adrs", "not a directory\n")
            self.assertTrue(CORE._decision_directory_present(root / "bionic/adrs"))
            self.assertEqual(CORE._adr_files(root / "bionic/adrs"), [])


class ProjectedPathTests(_Repo):
    """`adrs/index.md` is the regenerator's: the index projects it."""

    PROJECTED = True
    INDEX = "bionic/adrs/index.md"

    def test_positive_control_the_index_projects_with_no_finding(self):
        rec = coverage(self.root)["decision-index"]
        self.assertEqual((rec["verdict"], rec["omissions"]), ("populated", []))
        self.assertIn("projected from `adrs/index.md`", self.decision_index())

    def test_an_undecodable_index_is_a_document_finding(self):
        write(self.root, self.INDEX, (self.root / self.INDEX).read_bytes() + b"\xff\n")
        self.assert_document_lane(self.INDEX, "undecodable")

    def test_a_symbolic_link_index_is_a_document_finding(self):
        (self.root / "bionic/adrs/real-index.md").write_bytes(
            (self.root / self.INDEX).read_bytes())
        (self.root / self.INDEX).unlink()
        os.symlink("real-index.md", self.root / self.INDEX)
        self.assert_document_lane(self.INDEX, "not-a-file")

    def test_a_directory_at_the_index_path_is_a_document_finding(self):
        (self.root / self.INDEX).unlink()
        (self.root / self.INDEX).mkdir()
        self.assert_document_lane(self.INDEX, "not-a-file")

    def test_a_mode_000_index_is_a_document_finding(self):
        skip_if_root(self)
        os.chmod(self.root / self.INDEX, 0)
        self.assert_document_lane(self.INDEX)

    def test_an_over_cap_index_is_a_document_finding(self):
        write(self.root, self.INDEX, b" " * (2 * 1024 * 1024 + 1))
        self.assert_document_lane(self.INDEX, "over-cap")

    def test_an_undecodable_adr_is_a_document_finding_on_the_projected_path(self):
        write(self.root, "bionic/adrs/ADR-0004-bad.md",
              b"---\ntitle: \"B\xff\"\nstatus: Proposed\n---\n")
        self.assert_document_lane("bionic/adrs/ADR-0004-bad.md", "undecodable")

    def test_an_unparseable_adr_is_a_document_finding_on_the_projected_path(self):
        write(self.root, "bionic/adrs/ADR-0005-yaml.md",
              "---\ntitle: [unclosed\nstatus: Proposed\n---\n")
        self.assert_document_lane("bionic/adrs/ADR-0005-yaml.md", "unparseable")

    def test_an_over_cap_archived_adr_is_a_document_finding(self):
        """The regenerator reads the archived ADR, so the index stays fresh and
        the projection applies; the decision index's own read of it is over-cap."""
        write(self.root, "bionic/adrs/archive/ADR-0010-big.md",
              _ARCHIVED.replace("0009", "0010") + " " * (2 * 1024 * 1024 + 1))
        _write_adr_index(self.root)
        self.assert_document_lane("bionic/adrs/archive/ADR-0010-big.md", "over-cap")

    def test_positive_control_an_in_cap_archived_adr_is_hashed(self):
        write(self.root, "bionic/adrs/archive/ADR-0010-old.md",
              _ARCHIVED.replace("0009", "0010"))
        _write_adr_index(self.root)
        code, _out, payload, err = run_cli(self.root)
        self.assertEqual(code, 0, (payload, err))
        self.assertIn("projected from `adrs/index.md`", self.decision_index())


class FrontmatterReaderTests(unittest.TestCase):
    """The frontmatter reader tells a YAML error from an unavailable PyYAML."""

    BAD = "---\ntitle: [unclosed\nstatus: Accepted\n---\n"
    GOOD = "---\ntitle: Fine\nstatus: Accepted\n---\n"

    def test_a_yaml_error_under_a_ledger_is_a_finding(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            with active_ledger(root, "decision-index") as ledger:
                self.assertIsNone(CORE._frontmatter(self.BAD, root / "ADR-1.md"))
            self.assertEqual([f["file"] for f in ledger.findings], ["ADR-1.md"])
            self.assertIn("unparseable", ledger.findings[0]["error"])

    def test_positive_control_valid_yaml_under_a_ledger_parses_with_no_finding(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            with active_ledger(root, "decision-index") as ledger:
                fm = CORE._frontmatter(self.GOOD, root / "ADR-1.md")
            self.assertEqual(fm, {"title": "Fine", "status": "Accepted"})
            self.assertEqual(ledger.findings, [])

    def test_an_unavailable_pyyaml_keeps_the_stdlib_fallback(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            with active_ledger(root, "decision-index") as ledger, \
                    mock.patch.dict(sys.modules, {"yaml": None}):
                fm = CORE._frontmatter(self.BAD, root / "ADR-1.md")
            self.assertEqual(fm["status"], "Accepted")
            self.assertEqual(ledger.findings, [])

    def test_without_a_ledger_a_yaml_error_takes_the_fallback(self):
        fm = CORE._frontmatter(self.BAD, Path("ADR-1.md"))
        self.assertEqual(fm["status"], "Accepted")
        self.assertIsNone(CORE._ACTIVE_LEDGER.get())

    def test_without_a_path_a_yaml_error_takes_the_fallback_under_a_ledger(self):
        """The crux pack's skill reads pass no path and keep their answer."""
        with tempfile.TemporaryDirectory() as d:
            with active_ledger(Path(d), "api-surface") as ledger:
                fm = CORE._frontmatter(self.BAD)
            self.assertEqual(fm["status"], "Accepted")
            self.assertEqual(ledger.findings, [])


class LedgerParityTests(unittest.TestCase):
    """The fixture with no failure, run once more under an active ledger and
    the decision-index concern: the same content and an empty ledger."""

    def test_the_extractor_matches_under_an_active_ledger(self):
        for projected in (False, True):
            with self.subTest(projected=projected), tempfile.TemporaryDirectory() as d:
                root = Path(d).resolve()
                crux_repo(root)
                if projected:
                    _write_adr_index(root)
                direct = CORE.extract_decision_index(root, "bionic")
                with active_ledger(root, "decision-index") as ledger:
                    under = CORE.extract_decision_index(root, "bionic")
                self.assertEqual(under, direct)
                self.assertEqual(ledger.findings, [])
                self.assertEqual(ledger.omissions("decision-index"), [])

    def test_positive_control_the_wrapper_records_a_content_failure(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            crux_repo(root)
            write(root, "bionic/adrs/ADR-0004-bad.md", b"---\ntitle: \xff\n---\n")
            with active_ledger(root, "decision-index") as ledger:
                CORE.extract_decision_index(root, "bionic")
            self.assertEqual([f["file"] for f in ledger.findings],
                             ["bionic/adrs/ADR-0004-bad.md"])


class DirectCallTests(unittest.TestCase):
    """With no active ledger the decision index answers as before."""

    def test_an_undecodable_adr_is_read_with_replacement_without_a_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            crux_repo(root)
            write(root, "bionic/adrs/ADR-0004-bad.md",
                  b"---\ntitle: \"B\xff\"\nstatus: Accepted\n---\n")
            content, sources = CORE.extract_decision_index(root, "bionic")
            self.assertIn("B�", content)
            self.assertIn("bionic/adrs/ADR-0004-bad.md", sources)


class BroadHandlerTests(unittest.TestCase):

    def test_core_has_no_broad_handler_without_the_lane_clause(self):
        path = ARCH_PKG / "core.py"
        self.assertEqual(
            broad_handler_violations(path.read_text(encoding="utf-8"), "core.py"), [])

    def test_positive_control_a_seeded_handler_is_found(self):
        seeded = "try:\n    pass\nexcept Exception:\n    pass\n"
        self.assertEqual(len(broad_handler_violations(seeded)), 1)


if __name__ == "__main__":
    unittest.main()
