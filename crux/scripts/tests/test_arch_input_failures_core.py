"""ADR-0181 in the arch core — the input ledger, its lanes and its renderings.

The core's shared readers classify every failed or unusable input into one of
three outcomes. A content-determined failure in a descriptive map is an
OMISSION, named in the map's Omissions section and in `coverage.json`, with
exit 0. A failure attributable to the file (a permission refusal, a listed
entry that vanished) is a DOCUMENT FINDING: exit 1 with `validation_errors` on
stdout and nothing written. A host-determined failure (a FIFO, an unlistable
directory, an I/O error, a parser out of memory) is an ENVIRONMENT FAILURE:
exit 2, empty stdout, stderr naming the entry, nothing written.

Every refusing case pairs with a positive control on the same fixture, and
asserts the exit code, the payload and the byte-unchanged arch tree.
"""

from __future__ import annotations

import errno
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from arch_input_failures_support import (
    ARCH_PKG,
    CORE,
    active_ledger,
    arch_snapshot,
    broad_handler_violations,
    coverage,
    crux_repo,
    pack_handler_violations,
    run_cli,
    skip_if_root,
    write,
)


class _Tmp(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve()

    def tearDown(self):
        # Restore permissions so the temporary tree can be removed.
        for path in [self.root, *self.root.rglob("*")] if self.root.exists() else []:
            try:
                if not path.is_symlink():
                    os.chmod(path, 0o755 if path.is_dir() else 0o644)
            except OSError:
                pass
        self._tmp.cleanup()


# ───────────────────────── lstat-first classification ────────────────────────


class LstatClassTests(_Tmp):
    """`_safe_read_bytes` under an active ledger: one test per lstat class."""

    def read(self, rel: str, origin: str = "listed", concern: str = "data-model"):
        with active_ledger(self.root, concern) as ledger:
            raw = CORE._safe_read_bytes(self.root, self.root / rel, [], origin=origin)
        return raw, ledger

    def test_positive_control_a_regular_file_reads_and_records_nothing(self):
        write(self.root, "a.txt", "hello\n")
        raw, ledger = self.read("a.txt")
        self.assertEqual(raw, b"hello\n")
        self.assertEqual(ledger.omissions("data-model"), [])
        self.assertEqual(ledger.findings, [])

    def test_a_symbolic_link_is_not_a_file(self):
        write(self.root, "a.txt", "hello\n")
        os.symlink("a.txt", self.root / "link.txt")
        raw, ledger = self.read("link.txt")
        self.assertIsNone(raw)
        self.assertEqual(ledger.omissions("data-model"),
                         [{"path": "link.txt", "reason": "not-a-file", "kind": "symbolic-link"}])

    def test_a_dangling_symbolic_link_is_not_a_file(self):
        os.symlink("nowhere.txt", self.root / "link.txt")
        raw, ledger = self.read("link.txt", origin="fixed")
        self.assertIsNone(raw)
        self.assertEqual(ledger.omissions("data-model")[0]["kind"], "symbolic-link")

    def test_a_directory_is_not_a_file(self):
        (self.root / "d.json").mkdir()
        raw, ledger = self.read("d.json")
        self.assertIsNone(raw)
        self.assertEqual(ledger.omissions("data-model"),
                         [{"path": "d.json", "reason": "not-a-file", "kind": "directory"}])

    def test_a_fifo_is_an_environment_failure_naming_the_entry(self):
        os.mkfifo(self.root / "trap.json")
        with self.assertRaises(CORE.ArchEnvironmentFailure) as caught:
            self.read("trap.json")
        self.assertIn("trap.json", caught.exception.failures[0])
        self.assertIn("FIFO", caught.exception.failures[0])
        self.assertNotIn(str(self.root), caught.exception.failures[0])

    def test_a_mode_000_regular_file_is_a_document_finding(self):
        skip_if_root(self)
        write(self.root, "locked.json", "{}")
        os.chmod(self.root / "locked.json", 0)
        raw, ledger = self.read("locked.json")
        self.assertIsNone(raw)
        self.assertEqual([f["file"] for f in ledger.findings], ["locked.json"])
        self.assertIn("EACCES", ledger.findings[0]["error"])
        self.assertEqual(ledger.omissions("data-model"), [])

    def test_enoent_by_origin(self):
        """Listed: a document finding. Fixed: no input. Named: an absent omission."""
        raw, ledger = self.read("gone.json", origin="listed")
        self.assertIsNone(raw)
        self.assertEqual([f["file"] for f in ledger.findings], ["gone.json"])
        raw, ledger = self.read("gone.json", origin="fixed")
        self.assertIsNone(raw)
        self.assertEqual((ledger.findings, ledger.omissions("data-model")), ([], []))
        raw, ledger = self.read("gone.json", origin="named")
        self.assertIsNone(raw)
        self.assertEqual(ledger.omissions("data-model"),
                         [{"path": "gone.json", "reason": "absent", "kind": "absent"}])

    def test_enametoolong_of_a_named_path_is_absent(self):
        rel = "x" * 300 + ".json"
        raw, ledger = self.read(rel, origin="named")
        self.assertIsNone(raw)
        self.assertEqual(ledger.omissions("data-model")[0]["reason"], "absent")
        self.assertEqual(ledger.omissions("data-model")[0]["kind"], "too-long")

    def test_an_eio_read_is_an_environment_failure(self):
        write(self.root, "a.json", "{}")
        real = os.read

        def eio(fd, n):
            raise OSError(errno.EIO, "Input/output error")
        with mock.patch.object(CORE.os, "read", side_effect=eio):
            with self.assertRaises(CORE.ArchEnvironmentFailure) as caught:
                self.read("a.json")
        self.assertIn("EIO", caught.exception.failures[0])
        self.assertIs(os.read, real)

    def test_an_over_cap_file_is_an_over_cap_omission(self):
        write(self.root, "big.json", "x" * 64)
        with active_ledger(self.root) as ledger:
            raw = CORE._safe_read_bytes(self.root, self.root / "big.json", [], max_bytes=10)
        self.assertIsNone(raw)
        self.assertEqual(ledger.omissions("data-model"),
                         [{"path": "big.json", "reason": "over-cap", "kind": "oversize"}])

    def test_an_over_cap_file_in_the_completeness_dependent_concern_is_a_finding(self):
        write(self.root, "big.md", "x" * 64)
        with active_ledger(self.root, "decision-index") as ledger:
            CORE._safe_read_bytes(self.root, self.root / "big.md", [], max_bytes=10)
        self.assertEqual(ledger.omissions("decision-index"), [])
        self.assertIn("10-byte per-file cap", ledger.findings[0]["error"])

    def test_a_path_below_an_ancestor_link_that_escapes_is_not_a_file(self):
        with tempfile.TemporaryDirectory() as outside:
            write(Path(outside), "x.json", "{}")
            os.symlink(outside, self.root / "out")
            raw, ledger = self.read("out/x.json", origin="fixed")
        self.assertIsNone(raw)
        self.assertEqual(ledger.omissions("data-model"),
                         [{"path": "out/x.json", "reason": "not-a-file",
                           "kind": "symbolic-link"}])

    def test_positive_control_the_same_path_unlinked_reads(self):
        write(self.root, "out/x.json", "{}")
        raw, ledger = self.read("out/x.json", origin="fixed")
        self.assertEqual(raw, b"{}")
        self.assertEqual(ledger.omissions("data-model"), [])

    def test_a_lexically_outside_path_is_no_input(self):
        with tempfile.TemporaryDirectory() as outside:
            write(Path(outside), "x.json", "{}")
            with active_ledger(self.root) as ledger:
                raw = CORE._safe_read_bytes(self.root, Path(outside) / "x.json", [])
        self.assertIsNone(raw)
        self.assertEqual((ledger.findings, ledger.omissions("data-model")), ([], []))

    def test_with_no_active_ledger_the_reader_is_unchanged(self):
        """Constraint: no ledger, today's answers — a link and a FIFO are None."""
        write(self.root, "a.txt", "hello\n")
        os.symlink("a.txt", self.root / "link.txt")
        os.mkfifo(self.root / "trap.txt")
        self.assertIsNone(CORE._safe_read_bytes(self.root, self.root / "link.txt", []))
        self.assertIsNone(CORE._safe_read_bytes(self.root, self.root / "trap.txt", []))
        self.assertEqual(CORE._safe_read_bytes(self.root, self.root / "a.txt", []), b"hello\n")


# ───────────────────────── decode and parse ─────────────────────────────────


class DecodeAndParseTests(_Tmp):

    def test_an_undecodable_input_is_an_omission_and_none(self):
        with active_ledger(self.root) as ledger:
            self.assertIsNone(CORE.decode_input(self.root / "a.json", b"\xff\xfe"))
            self.assertEqual(CORE.decode_input(self.root / "b.json", b"ok"), "ok")
        self.assertEqual(ledger.omissions("data-model"),
                         [{"path": "a.json", "reason": "undecodable", "kind": "undecodable"}])

    def test_with_no_ledger_decode_is_replacement_as_before(self):
        self.assertEqual(CORE.decode_input(self.root / "a.json", b"a\xffb"), "a�b")

    def test_an_unparseable_input_is_an_omission(self):
        with active_ledger(self.root) as ledger:
            with CORE.parsing(self.root / "a.py") as outcome:
                compile("def (", "a.py", "exec")
        self.assertTrue(outcome.failed)
        self.assertEqual(ledger.omissions("data-model")[0]["reason"], "unparseable")

    def test_positive_control_a_parse_that_succeeds_records_nothing(self):
        with active_ledger(self.root) as ledger:
            with CORE.parsing(self.root / "a.py") as outcome:
                compile("x = 1", "a.py", "exec")
        self.assertFalse(outcome.failed)
        self.assertEqual(ledger.omissions("data-model"), [])

    def test_a_memory_error_at_a_parse_site_is_an_environment_failure(self):
        with active_ledger(self.root):
            with self.assertRaises(CORE.ArchEnvironmentFailure) as caught:
                with CORE.parsing(self.root / "a.py", Exception):
                    raise MemoryError()
        self.assertIn("a.py", caught.exception.failures[0])
        self.assertIn("MemoryError", caught.exception.failures[0])

    def test_with_no_ledger_a_memory_error_still_escapes(self):
        with self.assertRaises(MemoryError):
            with CORE.parsing(self.root / "a.py", Exception):
                raise MemoryError()

    def test_memory_error_left_the_parse_failure_tuple(self):
        self.assertNotIn(MemoryError, CORE._PARSE_FAILED)
        self.assertIn(RecursionError, CORE._PARSE_FAILED)

    def test_a_recursion_error_stays_unparseable(self):
        with active_ledger(self.root) as ledger:
            with CORE.parsing(self.root / "a.py"):
                raise RecursionError()
        self.assertEqual(ledger.omissions("data-model")[0]["reason"], "unparseable")

    def test_a_probe_and_its_extractor_record_one_input_once(self):
        with active_ledger(self.root) as ledger:
            CORE.decode_input(self.root / "a.json", b"\xff")
            CORE.decode_input(self.root / "a.json", b"\xff")
        self.assertEqual(len(ledger.omissions("data-model")), 1)

    def test_detection_records_no_content_failure(self):
        """With no active concern (stack detection) a content failure records nothing."""
        with active_ledger(self.root, None) as ledger:
            self.assertIsNone(CORE.decode_input(self.root / "a.json", b"\xff"))
        self.assertEqual((ledger.findings, ledger._omissions), ([], {}))


# ───────────────────────── listing and walking ──────────────────────────────


class ListingAndWalkTests(_Tmp):

    def walk(self, base: Path, prune=()):
        seen = []
        for directory, children, files in CORE._retained_source_walk(self.root, base):
            children[:] = [c for c in children if c not in prune]
            seen.append((Path(directory).relative_to(self.root).as_posix(),
                         list(children), list(files)))
        return seen

    def test_an_unlistable_walked_directory_is_an_environment_failure(self):
        skip_if_root(self)
        write(self.root, "src/a.py", "x = 1\n")
        os.chmod(self.root / "src", 0)
        with active_ledger(self.root):
            with self.assertRaises(CORE.ArchEnvironmentFailure) as caught:
                self.walk(self.root)
        self.assertIn("src", caught.exception.failures[0])

    def test_with_no_ledger_an_unlistable_directory_still_reads_as_empty(self):
        skip_if_root(self)
        write(self.root, "src/a.py", "x = 1\n")
        os.chmod(self.root / "src", 0)
        seen = self.walk(self.root)
        # Today's answer: the unlistable directory is skipped in silence.
        self.assertEqual(seen, [(".", ["src"], [])])

    def test_positive_control_a_listable_directory_walks(self):
        write(self.root, "src/a.py", "x = 1\n")
        with active_ledger(self.root) as ledger:
            seen = self.walk(self.root)
        self.assertEqual(seen[1], ("src", [], ["a.py"]))
        self.assertEqual(ledger.omissions("data-model"), [])

    def test_the_walk_is_sorted_under_a_ledger(self):
        for name in ("c.py", "a.py", "b.py"):
            write(self.root, f"src/{name}", "")
        for name in ("z", "m", "a"):
            (self.root / "src" / name).mkdir()
        with active_ledger(self.root):
            seen = self.walk(self.root / "src")
        self.assertEqual(seen[0][1], ["a", "m", "z"])
        self.assertEqual(seen[0][2], ["a.py", "b.py", "c.py"])

    def test_contained_directory_and_file_links_that_survive_pruning_are_named(self):
        write(self.root, "real/a.py", "")
        os.symlink("real", self.root / "dirlink")
        os.symlink("real/a.py", self.root / "filelink.py")
        with active_ledger(self.root) as ledger:
            seen = self.walk(self.root)
            for _d, _c, files in seen:
                for f in files:
                    CORE._safe_read_bytes(self.root, self.root / _d / f, [], origin="listed")
        names = {(r["path"], r["kind"]) for r in ledger.omissions("data-model")}
        self.assertIn(("dirlink", "symbolic-link"), names)
        self.assertIn(("filelink.py", "symbolic-link"), names)
        self.assertNotIn("dirlink", [d for d, _c, _f in seen])

    def test_a_link_under_a_pruned_directory_records_nothing(self):
        write(self.root, "real/a.py", "")
        (self.root / "node_modules").mkdir()
        os.symlink("../real", self.root / "node_modules" / "dirlink")
        with active_ledger(self.root) as ledger:
            self.walk(self.root, prune=("node_modules",))
        self.assertEqual(ledger.omissions("data-model"), [])

    def test_an_escaping_directory_link_is_named(self):
        with tempfile.TemporaryDirectory() as outside:
            os.symlink(outside, self.root / "away")
            with active_ledger(self.root) as ledger:
                self.walk(self.root)
        self.assertEqual(ledger.omissions("data-model"),
                         [{"path": "away", "reason": "not-a-file", "kind": "symbolic-link"}])

    def test_a_file_link_to_a_loop_is_named_not_a_file(self):
        os.symlink("loop.py", self.root / "loop.py")
        with active_ledger(self.root) as ledger:
            seen = self.walk(self.root)
            self.assertIn("loop.py", seen[0][2])
            CORE._safe_read_bytes(self.root, self.root / "loop.py", [], origin="listed")
        self.assertEqual(ledger.omissions("data-model")[0]["kind"], "symbolic-link")

    def test_a_walk_over_an_absent_optional_base_is_no_input(self):
        with active_ledger(self.root) as ledger:
            self.assertEqual(self.walk(self.root / "missing"), [])
        self.assertEqual((ledger.findings, ledger.omissions("data-model")), ([], []))

    def test_list_input_dir_by_origin(self):
        write(self.root, "afile", "x")
        with active_ledger(self.root) as ledger:
            self.assertIsNone(CORE.list_input_dir(self.root / "missing", "fixed"))
            self.assertIsNone(CORE.list_input_dir(self.root / "afile", "fixed"))
            self.assertIsNone(CORE.list_input_dir(self.root / "afile", "named"))
        self.assertEqual(ledger.omissions("data-model"),
                         [{"path": "afile", "reason": "absent", "kind": "absent"}])

    def test_a_fixed_directory_gate_holding_a_regular_file_is_no_input(self):
        write(self.root, "pkg", "x")
        with active_ledger(self.root) as ledger:
            self.assertFalse(CORE.input_dir_present(self.root / "pkg", "fixed"))
        self.assertEqual((ledger.findings, ledger.omissions("data-model")), ([], []))

    def test_an_unlistable_listed_directory_is_an_environment_failure(self):
        skip_if_root(self)
        (self.root / "d").mkdir()
        os.chmod(self.root / "d", 0)
        with active_ledger(self.root):
            with self.assertRaises(CORE.ArchEnvironmentFailure):
                CORE.list_input_dir(self.root / "d", "fixed")
        self.assertEqual(CORE.list_input_dir(self.root / "d", "fixed"), [])


# ───────────────────────── the scan cap and the template ─────────────────────


class ScanCapAndTemplateTests(_Tmp):

    def test_a_scan_cap_counts_what_it_skipped(self):
        with active_ledger(self.root) as ledger:
            CORE.record_scan_cap("_MAX_SCAN_FILES", self.root / "lib", 3, "loop-a")
            CORE.record_scan_cap("_MAX_SCAN_FILES", self.root / "lib", 3, "loop-a")
            CORE.record_scan_cap("_MAX_SCAN_FILES", self.root / "lib", 2, "loop-b")
        records = ledger.omissions("data-model")
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0], {"cap": "_MAX_SCAN_FILES", "dir": "lib", "skipped": 3,
                                      "reason": "over-cap", "kind": "scan-cap"})
        line = CORE.omission_line(records[0])
        self.assertIn("`_MAX_SCAN_FILES`", line)
        self.assertIn("skipped 3 input(s)", line)

    def test_the_template_escapes_and_carries_no_host_path(self):
        line = CORE.omission_line({"path": "a|b`c\nd.json", "reason": "undecodable",
                                   "kind": "undecodable"})
        self.assertEqual(line.count("\n"), 0)
        self.assertIn("a\\|b", line)
        self.assertNotIn("`c", line.split("`", 1)[1].rsplit("`", 1)[0])

    def test_a_surrogate_escaped_name_renders_in_backslashreplace_form(self):
        name = os.fsdecode(b"bad\xffname.json")
        line = CORE.omission_line({"path": name, "reason": "undecodable",
                                   "kind": "undecodable"})
        line.encode("utf-8")
        # backslashreplace, then `_cell`'s backslash escape inside the code span.
        self.assertIn("bad\\\\xffname.json", line)

    def test_paths_sort_before_scan_caps(self):
        with active_ledger(self.root) as ledger:
            CORE.record_scan_cap("CAP", self.root / "a", 1, "l")
            CORE.decode_input(self.root / "z.json", b"\xff")
            CORE.decode_input(self.root / "b.json", b"\xff")
        self.assertEqual([r.get("path", r.get("cap")) for r in ledger.omissions("data-model")],
                         ["b.json", "z.json", "CAP"])


# ───────────────────────── end to end through derive-arch.py ────────────────


class _Repo(_Tmp):
    def setUp(self):
        super().setUp()
        crux_repo(self.root)


class DeriveLaneTests(_Repo):
    """The three lanes through the CLI, write and --dry-run, with controls."""

    def baseline(self) -> dict:
        code, _out, payload, err = run_cli(self.root)
        self.assertEqual(code, 0, (payload, err))
        return arch_snapshot(self.root)

    def test_positive_control_the_fixture_derives_clean_with_no_omissions(self):
        self.baseline()
        for concern, rec in coverage(self.root).items():
            self.assertEqual(rec["omissions"], [], concern)
        code, _out, payload, _err = run_cli(self.root, "--dry-run")
        self.assertEqual(code, 0, payload)

    def test_a_document_finding_exits_1_and_writes_nothing(self):
        skip_if_root(self)
        before = self.baseline()
        os.chmod(self.root / "crux" / "schemas" / "w.schema.json", 0)
        for argv in ((), ("--dry-run",)):
            with self.subTest(argv=argv):
                code, _out, payload, _err = run_cli(self.root, *argv)
                self.assertEqual(code, 1)
                self.assertEqual([f["file"] for f in payload["validation_errors"]],
                                 ["crux/schemas/w.schema.json"])
                self.assertIn("EACCES", payload["validation_errors"][0]["error"])
                self.assertEqual(arch_snapshot(self.root), before)

    def test_an_environment_failure_exits_2_with_empty_stdout_and_writes_nothing(self):
        before = self.baseline()
        os.mkfifo(self.root / "crux" / "schemas" / "trap.json")
        for argv in ((), ("--dry-run",)):
            with self.subTest(argv=argv):
                code, out, _payload, err = run_cli(self.root, *argv)
                self.assertEqual(code, 2)
                self.assertEqual(out, "")
                self.assertIn("crux/schemas/trap.json", err)
                self.assertIn("environment failure", err)
                self.assertEqual(arch_snapshot(self.root), before)

    def test_the_environment_failure_names_findings_met_first(self):
        skip_if_root(self)
        self.baseline()
        os.chmod(self.root / "crux" / "schemas" / "w.schema.json", 0)
        os.mkfifo(self.root / "crux" / "schemas" / "x-trap.json")
        code, out, _payload, err = run_cli(self.root)
        self.assertEqual((code, out), (2, ""))
        self.assertIn("document finding met in the same run: crux/schemas/w.schema.json", err)

    def test_a_content_omission_exits_0_and_is_named_in_the_map_and_coverage(self):
        write(self.root, "crux/schemas/bad.json", b"\xff\xfe{}")
        code, _out, payload, err = run_cli(self.root)
        self.assertEqual(code, 0, (payload, err))
        data_model = (self.root / "bionic" / "arch" / "data-model.md").read_text()
        self.assertIn("## Omissions", data_model)
        self.assertIn("- `crux/schemas/bad.json` — undecodable (undecodable)", data_model)
        self.assertEqual(coverage(self.root)["data-model"]["omissions"],
                         [{"path": "crux/schemas/bad.json", "reason": "undecodable",
                           "kind": "undecodable"}])
        self.assertEqual(coverage(self.root)["api-surface"]["omissions"], [])
        code, _out, payload, _err = run_cli(self.root, "--dry-run")
        self.assertEqual(code, 0, payload)

    def test_a_marker_under_a_listable_unsearchable_directory_exits_2(self):
        skip_if_root(self)
        before = self.baseline()
        write(self.root, "sub/package.json", "{}")
        os.chmod(self.root / "sub", 0o444)
        code, out, _payload, err = run_cli(self.root)
        self.assertEqual((code, out), (2, ""))
        # The first marker a detector stats under `sub/` is named.
        self.assertIn("environment failure: sub/", err)
        self.assertIn("EACCES", err)
        self.assertEqual(arch_snapshot(self.root), before)

    def test_positive_control_a_searchable_directory_with_the_marker_derives(self):
        self.baseline()
        write(self.root, "sub/package.json", "{}")
        code, _out, payload, err = run_cli(self.root)
        self.assertEqual(code, 0, (payload, err))

    def test_a_surrogate_escaped_omission_writes_the_spine_and_coverage(self):
        name = os.fsdecode(b"crux/schemas/bad\xff.json")
        try:
            (self.root / name).write_bytes(b"\xff")
        except (OSError, UnicodeEncodeError):
            self.skipTest("this file system refuses a name that is not valid UTF-8")
        code, _out, payload, err = run_cli(self.root)
        self.assertEqual(code, 0, (payload, err))
        self.assertIn("bad\\xff.json", (self.root / "bionic/arch/data-model.md").read_text())
        paths = [r["path"] for r in coverage(self.root)["data-model"]["omissions"]]
        self.assertIn("crux/schemas/bad\\xff.json", paths)

    def test_no_ledger_or_concern_is_active_after_a_refusal_or_a_raise(self):
        skip_if_root(self)
        os.chmod(self.root / "crux" / "schemas" / "w.schema.json", 0)
        with self.assertRaises(CORE.ArchInputRefusal):
            CORE._build(self.root, "bionic")
        self.assertIsNone(CORE._ACTIVE_LEDGER.get())
        self.assertIsNone(CORE._ACTIVE_CONCERN.get())
        os.chmod(self.root / "crux" / "schemas" / "w.schema.json", 0o644)
        os.mkfifo(self.root / "crux" / "schemas" / "trap.json")
        with self.assertRaises(CORE.ArchEnvironmentFailure):
            CORE._build(self.root, "bionic")
        self.assertIsNone(CORE._ACTIVE_LEDGER.get())
        self.assertIsNone(CORE._ACTIVE_CONCERN.get())
        # A direct call afterwards behaves as before the ledger existed.
        self.assertEqual(CORE.decode_input(self.root / "x", b"a\xff"), "a�")


class SummaryAndStrictTests(_Repo):
    """Counts in overview.md, index.md and the printed table; the strict gate."""

    def add_omission(self) -> None:
        write(self.root, "crux/schemas/bad.json", b"\xff")

    def test_overview_and_index_state_each_descriptive_count(self):
        self.add_omission()
        code, _out, _payload, err = run_cli(self.root)
        self.assertEqual(code, 0, err)
        for name in ("overview.md", "index.md"):
            text = (self.root / "bionic" / "arch" / name).read_text()
            with self.subTest(name=name):
                self.assertIn("- Omitted inputs in `data-model.md`: 1", text)
                self.assertIn("- Omitted inputs in `api-surface.md`: 0", text)
                self.assertIn("- Omitted inputs in `module-graph.md`: 0", text)
                self.assertNotIn("decision-index.md`:", text)

    def test_the_printed_table_marks_a_concern_with_an_omission_incomplete(self):
        self.add_omission()
        _code, _out, _payload, err = run_cli(self.root)
        row = next(line for line in err.splitlines() if line.startswith("data-model"))
        self.assertIn("incomplete: 1 input(s) omitted", row)
        other = next(line for line in err.splitlines() if line.startswith("api-surface"))
        self.assertNotIn("incomplete", other)

    def test_strict_fails_a_concern_with_an_omission_and_still_writes(self):
        self.add_omission()
        code, _out, payload, _err = run_cli(self.root, "--strict")
        self.assertEqual(code, 1)
        failing = {f["concern"]: f for f in payload["strict_failures"]}
        self.assertIn("data-model", failing)
        self.assertEqual(failing["data-model"]["verdict"], "populated")
        self.assertEqual(failing["data-model"]["omissions"][0]["path"], "crux/schemas/bad.json")
        self.assertIn("## Omissions", (self.root / "bionic/arch/data-model.md").read_text())

    def test_arch_require_fails_a_required_concern_with_an_omission(self):
        self.add_omission()
        write(self.root, "bionic/manifest.yml",
              'schema_version: "5"\nadr:\n  next_number: 2\narch:\n  require: [data-model]\n')
        code, _out, payload, _err = run_cli(self.root)
        self.assertEqual(code, 1)
        self.assertEqual([f["concern"] for f in payload["strict_failures"]], ["data-model"])
        self.assertEqual(payload["strict_failures"][0]["required_by"], "arch.require")

    def test_positive_control_the_same_concern_without_the_omission_passes(self):
        write(self.root, "bionic/manifest.yml",
              'schema_version: "5"\nadr:\n  next_number: 2\narch:\n  require: [data-model]\n')
        code, _out, payload, _err = run_cli(self.root)
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload["strict_failures"], [])


class ManifestReadingTests(_Repo):
    """IDR approach 14: the manifest hashes bytes; omissions live in coverage."""

    def manifest(self) -> dict:
        return json.loads((self.root / "bionic/arch/_meta/manifest.json").read_text())

    def test_an_undecodable_input_is_hashed_and_named(self):
        write(self.root, "crux/schemas/bad.json", b"\xff")
        code, _out, _payload, err = run_cli(self.root)
        self.assertEqual(code, 0, err)
        self.assertIn("crux/schemas/bad.json", self.manifest()["sources"])
        self.assertIn("crux/schemas/bad.json",
                      [r["path"] for r in coverage(self.root)["data-model"]["omissions"]])

    def test_an_over_cap_input_is_named_unhashed_and_the_dry_run_is_clean(self):
        write(self.root, "crux/schemas/big.json", b" " * (CORE._MAX_FILE_BYTES + 1))
        code, _out, _payload, err = run_cli(self.root)
        self.assertEqual(code, 0, err)
        self.assertNotIn("crux/schemas/big.json", self.manifest()["sources"])
        self.assertEqual(coverage(self.root)["data-model"]["omissions"],
                         [{"path": "crux/schemas/big.json", "reason": "over-cap",
                           "kind": "oversize"}])
        self.assertIn("`crux/schemas/big.json` — over-cap (oversize)",
                      (self.root / "bionic/arch/data-model.md").read_text())
        code, _out, payload, _err = run_cli(self.root, "--dry-run")
        self.assertEqual(code, 0, payload)


# ───────────────────────── broad handlers ───────────────────────────────────


class BroadHandlerTests(unittest.TestCase):
    """IDR approach 16: every broad handler re-raises the lane types first.

    The rule covers `core.py` and every `packs/*.py` found by glob, so a new
    pack module is checked without being named here.
    """

    def test_core_and_every_pack_module_carry_the_clause(self):
        source = (ARCH_PKG / "core.py").read_text(encoding="utf-8")
        self.assertEqual(broad_handler_violations(source, "core.py"), [])
        labels, found = pack_handler_violations(ARCH_PKG)
        expected = sorted(f"packs/{p.name}" for p in (ARCH_PKG / "packs").glob("*.py"))
        self.assertTrue(expected)
        self.assertEqual(labels, expected)
        self.assertIn("packs/crux.py", labels)
        self.assertEqual(found, [])

    def test_positive_control_a_new_pack_module_is_found_by_the_glob(self):
        with tempfile.TemporaryDirectory() as d:
            pkg = Path(d)
            write(pkg, "packs/clean.py",
                  "def ok():\n    try:\n        pass\n    except ValueError:\n        pass\n")
            write(pkg, "packs/newpack.py",
                  "def bad():\n    try:\n        pass\n    except Exception:\n        pass\n")
            labels, found = pack_handler_violations(pkg)
        self.assertEqual(labels, ["packs/clean.py", "packs/newpack.py"])
        self.assertEqual(found, ["packs/newpack.py:4"])

    def test_positive_controls_each_seeded_handler_is_refused(self):
        seeded = {
            "except Exception": "try:\n    pass\nexcept Exception:\n    pass\n",
            "except BaseException": "try:\n    pass\nexcept BaseException:\n    pass\n",
            "bare except": "try:\n    pass\nexcept:\n    pass\n",
            "tuple": "try:\n    pass\nexcept (ValueError, Exception):\n    pass\n",
            "suppress": "import contextlib\nwith contextlib.suppress(Exception):\n    pass\n",
        }
        for label, source in seeded.items():
            with self.subTest(handler=label):
                self.assertEqual(len(broad_handler_violations(source)), 1)

    def test_the_clause_admits_a_broad_handler(self):
        source = ("try:\n    pass\nexcept _LANE_RAISES:\n    raise\n"
                  "except Exception:\n    pass\n")
        self.assertEqual(broad_handler_violations(source), [])

    def test_lane_raises_names_only_core_types_and_builtins(self):
        self.assertEqual(CORE._LANE_RAISES, (CORE.ArchEnvironmentFailure, MemoryError))


if __name__ == "__main__":
    unittest.main()
