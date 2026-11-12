"""Bookkeeping writes leave check evidence valid; the presets carry the shared exclusions.

CYC-0036 (Q-0013). The five bookkeeping writes of a cycle (a journal entry, a log.md append, a queue
edit, a cycle-record write and an edit of a configured root note) must leave the input fingerprint of
every registered checkout declaration and every excluding preset declaration unchanged. A change to
code, a test, an instruction file, a schema, an ADR or the arch spine must still move it.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _dev_surface import REPO_ROOT, require_dev_surface
from _evidence_fixtures import write_lock_project
from bionic_config import BionicConfigError
import operation_log
import suite_evidence
import test_evidence as te

SCRIPTS = Path(__file__).resolve().parents[1]
WRITER = SCRIPTS / "write-journal.py"
CLI = SCRIPTS / "test-evidence.py"
CORE = "checkout:unittest:crux/scripts/tests:test*.py"
TOOLS = "checkout:unittest:tools/tests:test*.py"
NOTES = ("crux-authority-reset.md", "crux-implementation-evidence.md")
# The dashboard gates declare the inputs their scripts read, not the whole tree (CYC-0096), so a generic
# edit does not move them. test_evidence_registry.DashboardGateInputTests owns their input contract.
DASHBOARD_GATES = ("mods-gate", "opencode-gate", "omp-gate")
BROAD_PRESETS = ("whole-tree", "drift-gates", "governs-references", "governs-coverage")
EXCLUDING_PRESETS = (*BROAD_PRESETS, *DASHBOARD_GATES)
GATE_SCRIPTS = {"drift-gates": "tools/run-drift-gates.py", "mods-gate": "tools/mods_gate.py",
                "governs-references": "crux/scripts/lint-governs-references.py",
                "governs-coverage": "crux/scripts/check-governs-coverage.py",
                "opencode-gate": "tools/opencode_gate.py", "omp-gate": "tools/omp_gate.py",
                "journal-index": "crux/scripts/generate-journal-index.py"}
BOOKKEEPING_YML = ('config_version: "1"\ndocs_dir: bionic\nevidence:\n  bookkeeping_paths:\n'
                   '    - crux-authority-reset.md\n    - crux-implementation-evidence.md\n')


class RepoCase(unittest.TestCase):
    """A temporary git repository shaped like this one: tree, root notes, gate scripts, code."""

    def git(self, *args):
        return subprocess.run(["git", "-c", "user.name=T", "-c", "user.email=t@example.invalid", *args],
                              cwd=self.root, capture_output=True, check=True)

    def write(self, rel, text="original\n"):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        write_lock_project(self.root)
        self.write(".python-version", "3.13\n")
        self.write(".bionic.yml", BOOKKEEPING_YML)
        self.git("init", "-q")
        self.write("bionic/manifest.yml", 'schema_version: "5"\nconcerns_enabled: [journal]\n')
        (self.root / "bionic/AGENTS.md").write_bytes((SCRIPTS.parent / "templates" / "AGENTS.md.tmpl").read_bytes())
        self.write("bionic/journal/index.md", "# Journal index\n")
        for rel in ("bionic/queue/cycles.yaml", "bionic/cycles/CYC-0001/cycle.json", "bionic/adrs/ADR-0001-x.md",
                    "bionic/arch/overview.md", "crux/scripts/tool.py", "crux/scripts/tests/test_x.py",
                    "crux/schemas/thing.schema.json", "tools/helper.py", "AGENTS.md", *NOTES,
                    *GATE_SCRIPTS.values()):
            self.write(rel)
        self.git("add", "-A")
        self.git("commit", "-qm", "base")

    def commit(self, message="change"):
        self.git("add", "-A")
        self.git("commit", "-qm", message)

    def declarations(self, journal_index=False):
        """Every registered checkout declaration and every preset declaration, keyed by name."""
        found = {check: suite_evidence.registered_declaration(self.root, check, dev_root=self.root) for check in (CORE, TOOLS)}
        for preset in EXCLUDING_PRESETS:
            command = ["python", "tools/anything.py"] if preset == "whole-tree" else None
            found[preset] = suite_evidence.preset_declaration(self.root, preset, "check-" + preset, command=command)
        if journal_index:
            found["journal-index"] = suite_evidence.preset_declaration(self.root, "journal-index", "check-journal-index")
        return found

    def fingerprints(self, **kwargs):
        return {name: te.snapshot(self.root, declaration, source_root=self.root)["fingerprint"]
                for name, declaration in self.declarations(**kwargs).items()}


class FiveWritesLeaveEvidenceValidTests(RepoCase):
    def setUp(self):
        super().setUp()
        # The first log write of a tree splits it and records `.split-complete.json`, an input of the
        # drift-gates receipt (OperationLogReceiptTests). This tree has had that write, as a tree
        # in use has, so each later write below is the append the five-writes rule is about.
        self.write_journal_entry("First write")
        self.commit("first log write")

    def write_journal_entry(self, subject="Bookkeeping entry"):
        body = self.root / "body.txt"
        body.write_text("A bookkeeping entry written by the real writer.\n")
        done = subprocess.run([sys.executable, str(WRITER), "--repo-root", str(self.root), "--mode", "journal",
                               "--at", "2026-10-20T11:42:35-06:00", "--category", "learning", "--subject", subject,
                               "--body-file", str(body)], capture_output=True, text=True, env={**os.environ, "UV_NO_CONFIG": "1"})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(json.loads(done.stdout)["status"], "complete")
        body.unlink()
        self.assertTrue((self.root / "bionic/journal/2026-10.md").is_file())

    def bookkeeping_writes(self):
        yield "journal entry", self.write_journal_entry
        # The journal write above appends its log entry to the current month's detail file; a legacy log.md
        # is still a bookkeeping path on a tree the new writer has not split. The drift-gates receipt
        # excludes only the current month's file (OperationLogReceiptTests holds the settled-month side).
        month = operation_log.local_date()[:7]
        yield "log detail append", lambda: self.write(
            f"bionic/log/{month}.md", f"# Operations log: {month}\n\n_Append-only. Latest write first._\n\n"
            f"## [{month}-20] skill | authored\n")
        yield "log.md append", lambda: self.write("bionic/log.md", "## [2026-10-20] skill | authored\n")
        yield "queue edit", lambda: self.write("bionic/queue/cycles.yaml", "original\nitem: edited\n")
        yield "cycle-record write", lambda: (self.write("bionic/cycles/CYC-0001/cycle.json", '{"phase": "reflect"}\n'),
                                             self.write("bionic/cycles/CYC-0002/cycle.json", "{}\n"))
        yield "authority-reset edit", lambda: (self.write("crux-authority-reset.md", "original\ncandidate\n"),
                                               self.write("crux-implementation-evidence.md", "original\nnote\n"))

    def test_each_bookkeeping_write_leaves_every_fingerprint_unchanged_uncommitted_and_committed(self):
        before = self.fingerprints()
        self.assertEqual(sorted(before), sorted([CORE, TOOLS, *EXCLUDING_PRESETS]))
        for label, write in self.bookkeeping_writes():
            with self.subTest(write=label):
                write()
                self.assertEqual(self.fingerprints(), before, label + " (uncommitted)")
                self.commit(label)
                self.assertEqual(self.fingerprints(), before, label + " (committed)")

    def test_a_journal_write_moves_only_the_journal_index_fingerprint(self):
        # The journal-index preset reads every journal entry, so it is the one declaration a journal
        # write is allowed to move; the other declarations stay valid.
        before = self.fingerprints(journal_index=True)
        self.write_journal_entry()
        after = self.fingerprints(journal_index=True)
        self.assertNotEqual(after["journal-index"], before["journal-index"])
        self.assertEqual({k: v for k, v in after.items() if k != "journal-index"},
                         {k: v for k, v in before.items() if k != "journal-index"})

    def test_a_queue_or_cycle_write_leaves_the_journal_index_fingerprint_unchanged(self):
        before = self.fingerprints(journal_index=True)["journal-index"]
        self.write("bionic/queue/cycles.yaml", "changed\n")
        self.write("bionic/cycles/CYC-0002/cycle.json", "{}\n")
        self.write("crux-authority-reset.md", "changed\n")
        self.assertEqual(self.fingerprints(journal_index=True)["journal-index"], before)

    def test_the_configured_notes_are_excluded_from_every_checkout_declaration_and_preset(self):
        for name, declaration in self.declarations().items():
            if name in (CORE, TOOLS) or name in EXCLUDING_PRESETS:
                self.assertTrue({"bionic/queue", *NOTES} <= set(declaration["exclude_inputs"]), name)


class PositiveControlTests(RepoCase):
    """An edit to an input still moves the fingerprint, so the equality above is a measurement."""

    EDITS = ("crux/scripts/tool.py", "crux/scripts/tests/test_x.py", "AGENTS.md", "crux/schemas/thing.schema.json",
             "tools/helper.py", ".bionic.yml", "bionic/AGENTS.md")
    # Decision records move every preset's fingerprint and neither registered checkout suite's.
    DECISION_EDITS = ("bionic/adrs/ADR-0001-x.md", "bionic/arch/overview.md", "bionic/manifest.yml")

    def test_an_edit_to_each_input_changes_every_excluding_declaration(self):
        for rel in self.EDITS:
            with self.subTest(path=rel):
                before = self.fingerprints()
                original = (self.root / rel).read_text()
                self.write(rel, original + "# changed\n")
                after = self.fingerprints()
                for name in before:
                    if name in DASHBOARD_GATES:
                        continue
                    self.assertNotEqual(after[name], before[name], f"{rel} did not move {name}")
                self.commit("edit " + rel)

    def test_a_decision_record_edit_moves_every_preset_and_no_registered_checkout_suite(self):
        for rel in self.DECISION_EDITS:
            with self.subTest(path=rel):
                before = self.fingerprints()
                self.write(rel, (self.root / rel).read_text() + "# changed\n")
                after = self.fingerprints()
                for name in before:
                    if name in (CORE, TOOLS):
                        self.assertEqual(after[name], before[name], f"{rel} moved {name}")
                    elif name in DASHBOARD_GATES:
                        continue
                    else:
                        self.assertNotEqual(after[name], before[name], f"{rel} did not move {name}")
                self.commit("edit " + rel)

    def test_a_journal_month_edit_moves_the_journal_index_declaration_only_through_its_inputs(self):
        before = self.fingerprints(journal_index=True)
        self.write("bionic/journal/2026-10.md", "an entry written outside the writer\n")
        self.assertNotEqual(self.fingerprints(journal_index=True)["journal-index"], before["journal-index"])
        self.write("crux/scripts/generate-journal-index.py", "changed generator\n")
        self.assertNotEqual(self.fingerprints(journal_index=True)["journal-index"], before["journal-index"])

    def test_a_bookkeeping_path_that_is_not_configured_is_an_input(self):
        # POSITIVE DISCRIMINATOR for the setting: a root note that is not listed still moves the fingerprint.
        self.write("crux-unlisted-note.md")
        self.commit("unlisted note")
        before = self.fingerprints()
        self.write("crux-unlisted-note.md", "changed\n")
        after = self.fingerprints()
        for name in before:
            if name in DASHBOARD_GATES:
                continue
            self.assertNotEqual(after[name], before[name], name)


class OperationLogReceiptTests(RepoCase):
    """The operations log in test-evidence receipts: monthly detail files under bionic/log/.

    Every receipt excludes the legacy log.md, the current month's detail file by the recording host's
    local date, staged legacy files and staged strays. The drift-gates preset alone runs the summary gate,
    so it keeps the settled detail files, the summary, the completion record, the transaction file and the
    kept files as inputs and fingerprints the NAMES of the staged files. Every other preset excludes the
    whole log directory. Each test passes the local date, so none depends on the clock.

    Live-read audit (CYC-0134): no test of either suite root reads the live tree's `bionic/log/` or
    `bionic/log.md`. `git ls-files bionic/log` is empty, every fixture here builds a temporary tree, and
    the one live path left, `_dev_surface.TREE_LOG_MD`, has no reader.
    """

    LOG = "bionic/log"
    LEGACY = ".legacy-" + "a" * 64 + ".md"
    OTHER_LEGACY = ".legacy-" + "b" * 64 + ".md"
    STRAY = ".stray-" + "c" * 64 + ".md"
    OTHER_STRAY = ".stray-" + "d" * 64 + ".md"
    TRANSACTION = ".split-" + "e" * 64 + ".json"
    KEPT = ".kept-" + "f" * 64 + ".txt"
    OTHER_PRESETS = ("whole-tree", "governs-references", "governs-coverage")

    def month_file(self, month, text=None):
        self.write(f"{self.LOG}/{month}.md", text or f"# Operations log: {month}\n\n## [{month}-05] skill | authored\n")

    def declaration(self, preset="drift-gates", today="2026-10-20"):
        command = ["python", "tools/anything.py"] if preset == "whole-tree" else None
        return suite_evidence.preset_declaration(self.root, preset, "c-" + preset, command=command, today=today)

    def snapshot(self, preset="drift-gates", today="2026-10-20"):
        return te.snapshot(self.root, self.declaration(preset, today), source_root=self.root)

    def fingerprint(self, preset="drift-gates", today="2026-10-20"):
        return self.snapshot(preset, today)["fingerprint"]

    def seed_log(self):
        self.month_file("2026-09")
        self.month_file("2026-10")
        self.write(f"{self.LOG}/summary.md", "# Operations log summary\n")
        self.write(f"{self.LOG}/.split-complete.json", "{}\n")
        self.write(f"{self.LOG}/{self.TRANSACTION}", "{}\n")
        self.write(f"{self.LOG}/{self.KEPT}", "kept\n")
        self.commit("seed the log")

    def log_inputs(self, preset="drift-gates", today="2026-10-20"):
        return {name for name in self.snapshot(preset, today)["inputs"] if name.startswith(self.LOG + "/")}

    def test_the_drift_gates_receipt_keeps_the_settled_files_and_excludes_the_current_month(self):
        self.seed_log()
        self.assertEqual(self.log_inputs(), {f"{self.LOG}/{name}" for name in (
            "2026-09.md", "summary.md", ".split-complete.json", self.TRANSACTION, self.KEPT)})
        exclusions = self.declaration()["exclude_inputs"]
        self.assertIn(f"{self.LOG}/2026-10.md", exclusions)
        self.assertIn("bionic/log.md", exclusions)
        self.assertNotIn(self.LOG, exclusions)

    def test_every_other_preset_and_both_registered_suites_exclude_the_whole_log_directory(self):
        self.seed_log()
        for preset in self.OTHER_PRESETS:
            with self.subTest(preset=preset):
                self.assertIn(self.LOG, self.declaration(preset)["exclude_inputs"])
                self.assertEqual(self.log_inputs(preset), set())
        for check in (CORE, TOOLS):
            with self.subTest(check=check):
                registered = suite_evidence.registered_declaration(self.root, check, dev_root=self.root)
                self.assertIn(self.LOG, registered["exclude_inputs"])
                found = te.snapshot(self.root, registered, source_root=self.root)["inputs"]
                self.assertEqual({name for name in found if name.startswith(self.LOG + "/")}, set())

    def test_a_receipt_recorded_on_a_months_last_day_lapses_on_the_first_day_of_the_next(self):
        self.seed_log()
        last, first = self.fingerprint(today="2026-10-31"), self.fingerprint(today="2026-11-01")
        self.assertNotEqual(last, first)
        # Positive control: another day of the same month gives the same fingerprint.
        self.assertEqual(self.fingerprint(today="2026-10-01"), last)

    def test_the_current_months_file_never_moves_the_fingerprint_and_a_settled_month_does(self):
        self.seed_log()
        before = self.fingerprint()
        # A heading no reader accepts, in the current month's file: the receipt stays valid.
        self.month_file("2026-10", "# Operations log: 2026-10\n\n## [not a date] ???\nbody\n")
        self.assertEqual(self.fingerprint(), before)
        # Positive control: the same edit to a settled month lapses the receipt.
        self.month_file("2026-09", "# Operations log: 2026-09\n\n## [not a date] ???\nbody\n")
        self.assertNotEqual(self.fingerprint(), before)

    def test_the_summary_the_completion_record_the_transaction_and_the_kept_file_are_inputs(self):
        self.seed_log()
        before = self.fingerprint()
        for name in ("summary.md", ".split-complete.json", self.TRANSACTION, self.KEPT):
            with self.subTest(name=name):
                original = (self.root / self.LOG / name).read_text()
                self.write(f"{self.LOG}/{name}", "changed\n")
                self.assertNotEqual(self.fingerprint(), before)
                self.write(f"{self.LOG}/{name}", original)
                self.assertEqual(self.fingerprint(), before)

    def test_the_names_of_staged_files_move_the_fingerprint_and_their_bytes_do_not(self):
        self.seed_log()
        bare = self.fingerprint()
        for label, name, other in (("legacy", self.LEGACY, self.OTHER_LEGACY), ("stray", self.STRAY, self.OTHER_STRAY)):
            with self.subTest(kind=label):
                self.write(f"{self.LOG}/{name}", "## [2026-10-02] skill | authored\n")
                named = self.fingerprint()
                self.assertNotEqual(named, bare)  # the name alone: an incomplete split state
                self.assertIn(f"{self.LOG}/{name}", self.declaration()["exclude_inputs"])
                self.write(f"{self.LOG}/{name}", "entirely different bytes\n")
                self.assertEqual(self.fingerprint(), named)  # the bytes are not read
                (self.root / self.LOG / name).rename(self.root / self.LOG / other)
                self.assertNotEqual(self.fingerprint(), named)  # another name moves it
                (self.root / self.LOG / other).unlink()
                self.assertEqual(self.fingerprint(), bare)

    def test_a_legacy_log_md_is_excluded_by_every_preset_including_drift_gates(self):
        self.seed_log()
        for preset in ("drift-gates", *self.OTHER_PRESETS):
            with self.subTest(preset=preset):
                before = self.fingerprint(preset)
                self.write("bionic/log.md", f"## [2026-10-20] skill | authored\n{preset}\n")
                self.assertEqual(self.fingerprint(preset), before)

    def test_an_invalid_date_is_refused(self):
        with self.assertRaisesRegex(Exception, "today"):
            self.declaration(today="2026-13-45")


class BookkeepingPathsSettingTests(RepoCase):
    def set_paths(self, value_lines):
        self.write(".bionic.yml", 'config_version: "1"\ndocs_dir: bionic\n' + value_lines)

    def test_the_configured_files_are_read(self):
        self.assertEqual(suite_evidence.bookkeeping_paths(self.root), list(NOTES))

    def test_an_absent_key_is_an_empty_list(self):
        self.write(".bionic.yml", 'config_version: "1"\ndocs_dir: bionic\n')
        self.assertEqual(suite_evidence.bookkeeping_paths(self.root), [])
        self.set_paths("evidence: {}\n")
        self.assertEqual(suite_evidence.bookkeeping_paths(self.root), [])
        self.assertEqual(suite_evidence.runtime_exclusions(self.root),
                         ["bionic/" + name for name in suite_evidence.DOCS_EXCLUSIONS])

    def test_no_config_file_is_an_empty_list(self):
        (self.root / ".bionic.yml").unlink()
        self.assertEqual(suite_evidence.bookkeeping_paths(self.root), [])

    def test_a_missing_file_is_allowed(self):
        self.set_paths("evidence:\n  bookkeeping_paths:\n    - not-yet-written.md\n")
        self.assertEqual(suite_evidence.bookkeeping_paths(self.root), ["not-yet-written.md"])
        self.assertIn("not-yet-written.md", suite_evidence.runtime_exclusions(self.root))

    def test_runtime_exclusions_is_the_docs_names_then_the_configured_files(self):
        self.assertEqual(suite_evidence.runtime_exclusions(self.root),
                         ["bionic/" + name for name in suite_evidence.DOCS_EXCLUSIONS] + list(NOTES))
        self.assertEqual(suite_evidence.runtime_exclusions(self.root, names=("log.md",)), ["bionic/log.md", *NOTES])
        self.assertIn("queue", suite_evidence.DOCS_EXCLUSIONS)

    def refused(self, entry_lines, reason):
        self.set_paths("evidence:\n  bookkeeping_paths:\n" + entry_lines)
        with self.assertRaises(te.EvidenceError) as caught:
            suite_evidence.bookkeeping_paths(self.root)
        self.assertIn(reason, str(caught.exception))
        # runtime_exclusions refuses too. A `*` is refused earlier still, by the layout reader, which
        # rejects the YAML alias character anywhere in .bionic.yml.
        with self.assertRaises((te.EvidenceError, BionicConfigError)):
            suite_evidence.runtime_exclusions(self.root)

    def test_invalid_entries_are_refused_with_the_reason(self):
        (self.root / "a-directory").mkdir()
        (self.root / "a-directory/x.md").write_text("x\n")
        (self.root / "target.md").write_text("x\n")
        (self.root / "a-link.md").symlink_to(self.root / "target.md")
        cases = {
            "absolute": ("    - /etc/hosts\n", "absolute"),
            "parent": ("    - ../outside.md\n", ".."),
            "parent-inside": ("    - sub/../x.md\n", ".."),
            "star": ("    - notes/*.md\n", "glob"),
            "question": ("    - note?.md\n", "glob"),
            "bracket": ("    - note[1].md\n", "glob"),
            "docs-file": ("    - bionic/notes.md\n", "docs directory"),
            "docs-directory": ("    - bionic\n", "docs directory"),
            "directory": ("    - a-directory\n", "directory"),
            "symlink": ("    - a-link.md\n", "symlink"),
            "empty": ('    - ""\n', "empty"),
            "not-a-string": ("    - 3\n", "string"),
        }
        for label, (lines, reason) in cases.items():
            with self.subTest(case=label):
                self.refused(lines, reason)

    def test_a_non_list_value_is_refused(self):
        self.set_paths("evidence:\n  bookkeeping_paths: crux-authority-reset.md\n")
        with self.assertRaisesRegex(te.EvidenceError, "list"):
            suite_evidence.bookkeeping_paths(self.root)

    def test_a_symlinked_parent_is_not_followed_for_the_entry_itself(self):
        # lstat on the entry: a regular file under a normal directory is accepted.
        (self.root / "notes").mkdir()
        (self.root / "notes/n.md").write_text("n\n")
        self.set_paths("evidence:\n  bookkeeping_paths:\n    - notes/n.md\n")
        self.assertEqual(suite_evidence.bookkeeping_paths(self.root), ["notes/n.md"])


class DeclareTests(RepoCase):
    def test_every_excluding_preset_carries_the_registered_exclusions(self):
        registered = suite_evidence.registered_declaration(self.root, CORE, dev_root=self.root)
        expected = suite_evidence.runtime_exclusions(self.root)
        # A registered checkout suite also leaves out the decision records and the release paths its reader
        # audit cleared; a preset never does, so a preset's inputs include the decision records.
        records = ["bionic/" + name for name in suite_evidence.DECISION_RECORDS]
        self.assertEqual(registered["exclude_inputs"],
                         [*expected, *records, *suite_evidence.RELEASE_EXCLUSIONS["checkout"]])
        for preset in EXCLUDING_PRESETS:
            with self.subTest(preset=preset):
                command = ["python", "tools/anything.py"] if preset == "whole-tree" else None
                declaration = suite_evidence.preset_declaration(self.root, preset, "c", command=command)
                # drift-gates alone keeps the settled log files as inputs (OperationLogReceiptTests).
                self.assertEqual(declaration["exclude_inputs"],
                                 suite_evidence.drift_gates_exclusions(self.root) if preset == "drift-gates" else expected)
                if preset in DASHBOARD_GATES:
                    self.assertNotEqual(declaration["inputs"], suite_evidence.INPUTS)
                    self.assertIs(declaration["git_tracked"], False)
                else:
                    self.assertEqual(declaration["inputs"], suite_evidence.INPUTS)
                    self.assertIs(declaration["git_tracked"], True)
                self.assertNotIn("preset", declaration)
                self.assertEqual(declaration["check_id"], "c")
                te.normalize(declaration)
                self.assertEqual(te.lookup(self.root, declaration, source_root=self.root)["state"], "missing")

    def test_the_command_each_preset_runs(self):
        by = lambda preset, **kw: suite_evidence.preset_declaration(self.root, preset, "c", **kw)
        self.assertEqual(by("whole-tree", command=["python", "x.py", "--flag"])["command"], ["python", "x.py", "--flag"])
        self.assertEqual(by("drift-gates")["command"], ["python", "tools/run-drift-gates.py", "--cycle-scope"])
        self.assertEqual(by("mods-gate")["command"], ["python", "tools/mods_gate.py", "--plugin-dir", "crux-mods", "--phase", "dev"])
        self.assertEqual(by("opencode-gate")["command"],
                         ["python", "tools/opencode_gate.py", "--plugin-dir", "crux-opencode", "--phase", "dev"])
        self.assertEqual(by("omp-gate")["command"], ["python", "tools/omp_gate.py", "--plugin-dir", "crux-omp", "--phase", "dev"])

    def test_the_gate_presets_require_the_tools_their_gate_invokes(self):
        tools = {preset: te.normalize(suite_evidence.preset_declaration(self.root, preset, "c"))["requirement"]["tools"]
                 for preset in ("mods-gate", "opencode-gate", "omp-gate")}
        self.assertTrue({"claude", "uv"} <= set(tools["mods-gate"]))
        self.assertTrue({"claude", "git", "uv"} <= set(tools["opencode-gate"]))
        self.assertTrue({"node", "uv"} <= set(tools["omp-gate"]))

    def test_a_caller_requirement_replaces_the_preset_default(self):
        declaration = suite_evidence.preset_declaration(self.root, "mods-gate", "c", requirement={"tools": ["git"]})
        self.assertEqual(declaration["requirement"], {"tools": ["git"]})

    def test_journal_index_carries_no_exclusions_and_is_not_git_tracked(self):
        declaration = suite_evidence.preset_declaration(self.root, "journal-index", "c")
        self.assertEqual(declaration["command"], ["python", "crux/scripts/generate-journal-index.py", "--dry-run"])
        self.assertEqual(declaration["inputs"], ["bionic/journal", "crux/scripts", ".bionic.yml"])
        self.assertEqual(declaration["exclude_inputs"], [])
        self.assertIs(declaration["git_tracked"], False)
        self.assertNotIn("preset", declaration)
        te.normalize(declaration)

    def test_a_gate_preset_whose_script_is_absent_refuses_as_not_applicable(self):
        for preset, script in GATE_SCRIPTS.items():
            with self.subTest(preset=preset):
                (self.root / script).unlink()
                with self.assertRaisesRegex(te.EvidenceError, "not applicable.*" + script.replace(".", r"\.")):
                    suite_evidence.preset_declaration(self.root, preset, "c")

    def test_whole_tree_without_a_command_refuses_and_other_presets_fix_their_command(self):
        with self.assertRaisesRegex(te.EvidenceError, "command"):
            suite_evidence.preset_declaration(self.root, "whole-tree", "c")
        with self.assertRaisesRegex(te.EvidenceError, "fixes its command"):
            suite_evidence.preset_declaration(self.root, "drift-gates", "c", command=["python", "x.py"])

    def test_an_unknown_preset_and_an_empty_check_id_refuse(self):
        with self.assertRaisesRegex(te.EvidenceError, "unknown preset"):
            suite_evidence.preset_declaration(self.root, "nope", "c")
        with self.assertRaisesRegex(te.EvidenceError, "check_id"):
            suite_evidence.preset_declaration(self.root, "drift-gates", " ")

    def test_the_preset_names(self):
        self.assertEqual(set(suite_evidence.PRESETS), {*EXCLUDING_PRESETS, "journal-index", "release-metadata", "test-tiers"})


class DeclareCliTests(RepoCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(CLI), "declare", "--repo-root", str(self.root), *args],
                              capture_output=True, text=True, env={**os.environ, "UV_NO_CONFIG": "1"})

    def test_declare_prints_the_concrete_declaration_and_it_validates(self):
        done = self.run_cli("--preset", "drift-gates", "--check-id", "cycle:drift-gates")
        self.assertEqual(done.returncode, 0, done.stderr)
        declaration = json.loads(done.stdout)
        self.assertEqual(declaration, suite_evidence.preset_declaration(self.root, "drift-gates", "cycle:drift-gates"))
        self.assertEqual(declaration["exclude_inputs"], suite_evidence.drift_gates_exclusions(self.root))
        check = self.root / "declared.json"
        check.write_text(done.stdout)
        looked = subprocess.run([sys.executable, str(CLI), "lookup", "--repo-root", str(self.root), "--check", str(check)],
                                capture_output=True, text=True, env={**os.environ, "UV_NO_CONFIG": "1"})
        self.assertEqual(json.loads(looked.stdout)["state"], "missing", looked.stderr)

    def test_declare_writes_the_output_file(self):
        out = self.root / "out" / "decl.json"
        done = self.run_cli("--preset", "whole-tree", "--check-id", "x", "--command", '["python", "x.py"]',
                            "--requirement", '{"tools": ["git"]}', "--output", str(out))
        self.assertEqual(done.returncode, 0, done.stderr)
        declaration = json.loads(out.read_text())
        self.assertEqual((declaration["command"], declaration["requirement"]), (["python", "x.py"], {"tools": ["git"]}))

    def test_declare_refuses_with_exit_two(self):
        missing = self.run_cli("--preset", "whole-tree", "--check-id", "x")
        self.assertEqual(missing.returncode, 2)
        self.assertIn("command", missing.stderr)
        (self.root / "tools/omp_gate.py").unlink()
        absent = self.run_cli("--preset", "omp-gate", "--check-id", "x")
        self.assertEqual(absent.returncode, 2)
        self.assertIn("not applicable", absent.stderr)
        self.assertEqual(absent.stdout, "")
        bad = self.run_cli("--preset", "whole-tree", "--check-id", "x", "--command", "not json")
        self.assertEqual(bad.returncode, 2)


class RosterCoverageTests(unittest.TestCase):
    def test_the_drift_gates_run_and_the_journal_index_run_cover_every_roster_gate(self):
        runner = REPO_ROOT / "tools" / "run-drift-gates.py"
        require_dev_surface(self, runner, "tools/run-drift-gates.py")
        import importlib.util
        spec = importlib.util.spec_from_file_location("_bookkeeping_drift_runner", runner)
        drift = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = drift
        spec.loader.exec_module(drift)
        roster = {drift._script_token(gate["command"]) for gate in drift.declared_gates(REPO_ROOT)}
        self.assertGreater(len(roster), 1)
        preset_run = suite_evidence.PRESETS["drift-gates"]["command"]
        self.assertEqual(preset_run[-1], "--cycle-scope")
        executed = roster - set(drift.WRITE_TIME_GATES)
        index_command = suite_evidence.PRESETS["journal-index"]["command"]
        index_gate = Path(index_command[1]).name
        self.assertEqual(index_command[-1], "--dry-run")
        self.assertEqual(executed | {index_gate}, roster)
        self.assertEqual(set(drift.WRITE_TIME_GATES), {index_gate})
        self.assertNotIn(index_gate, executed)


if __name__ == "__main__":
    unittest.main()
