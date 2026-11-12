"""Behavioral checks for the bounded journal writer."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "write-journal.py"
SCRIPT_DIR = SCRIPT.parent
# The log record lands in the detail file of the month holding the local date, which every
# invocation here fixes at TODAY under the test-only override.
TODAY = "2026-09-27"
LOG_HEADER = "# Operations log: 2026-09\n\n_Append-only. Latest write first._\n\n"
sys.path.insert(0, str(SCRIPT_DIR))
from journal_index import journal_entries, parse_index_row  # noqa: E402
import operation_log  # noqa: E402


class WriterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.tree = self.root / "docs"
        (self.tree / "journal").mkdir(parents=True)
        (self.root / ".bionic.yml").write_text('config_version: "1"\ndocs_dir: docs\n')
        (self.tree / "manifest.yml").write_text('schema_version: "5"\nconcerns_enabled: [journal]\n')
        source = Path(__file__).resolve().parents[2] / "templates" / "AGENTS.md.tmpl"
        (self.tree / "AGENTS.md").write_bytes(source.read_bytes())
        self.month = self.tree / "journal" / "2026-09.md"
        self.index = self.tree / "journal" / "index.md"
        # A split tree: log/ with its completion record, so the repair phase has no work.
        (self.tree / "log").mkdir()
        (self.tree / "log" / ".split-complete.json").write_bytes(operation_log.completion_bytes(None, {}))
        self.log = self.tree / "log" / "2026-09.md"
        self.body = self.root / "body.txt"
        self.body.write_text("The first attempt failed because the input was stale.\n")
        environment = patch.dict(os.environ, {operation_log.TEST_ENV: "1"})
        environment.start()
        self.addCleanup(environment.stop)
        self.baseline = self.snapshot()

    def invoke(self, *args, at="2026-09-27T11:42:35-06:00", mode="journal", body=None):
        if body is not None:
            self.body.write_text(body)
        command = [sys.executable, str(SCRIPT), "--repo-root", str(self.root),
                   "--mode", mode, "--at", at, "--category", "learning",
                   "--subject", "Diagnosed a stale input", "--body-file", str(self.body),
                   "--today", TODAY, *args]
        completed = subprocess.run(command, capture_output=True, text=True,
                                   env={**os.environ, "UV_NO_CONFIG": "1"})
        if not completed.stdout.strip():
            self.fail(f"write-journal printed no report (exit {completed.returncode}): {completed.stderr}")
        return completed, json.loads(completed.stdout)

    def test_report_claims_no_git_commit_for_files_left_modified(self):
        """The writer never runs git: no report key may say a modified file was committed."""
        git = ["git", "-C", str(self.root), "-c", "user.name=t", "-c", "user.email=t@t"]
        subprocess.run([*git, "init", "-q"], check=True)
        self.index.write_text("# Journal index\n")
        self.log.write_text(LOG_HEADER + "## [2026-09-01] init | Tree\n\nBody.\n\n")
        subprocess.run([*git, "add", "-A"], check=True)
        subprocess.run([*git, "commit", "-qm", "base"], check=True)
        result, payload = self.invoke()
        self.assertEqual((result.returncode, payload["status"]), (0, "complete"), result.stdout)
        status = subprocess.run([*git, "status", "--porcelain"], capture_output=True,
                                text=True, check=True).stdout
        self.assertIn("docs/log/2026-09.md", status)
        self.assertNotIn("committed", payload)
        self.assertEqual(sorted(payload["recorded"]),
                         sorted(["journal/2026-09.md", "journal/index.md", "log/2026-09.md"]))
        # The log part of the result names the paths log-work commits.
        self.assertEqual(payload["changed_paths"], ["docs/log/2026-09.md"])
        self.assertEqual((payload["commit_paths"], payload["restore_paths"]), (["docs/log/2026-09.md"], []))

    def index_drift_exit(self):
        """Exit code of the journal-index drift gate over this tree (0 clean, 1 drift)."""
        gate = SCRIPT_DIR / "generate-journal-index.py"
        done = subprocess.run([sys.executable, str(gate), "--dry-run", "--repo-root", str(self.root)],
                              capture_output=True, text=True, env={**os.environ, "UV_NO_CONFIG": "1"})
        return done.returncode, done.stdout + done.stderr

    def test_the_journal_index_gate_is_clean_after_every_writer_entry(self):
        """Acceptance 5 (CYC-0036): the writer regenerates the index on every write, so the drift gate
        (`generate-journal-index.py --dry-run`, which the cycle's persistent drift-gates check skips)
        cannot find drift after a journal write."""
        self.index.write_text("# Journal index\n")
        result, payload = self.invoke()
        self.assertEqual((result.returncode, payload["status"]), (0, "complete"), result.stdout)
        code, output = self.index_drift_exit()
        self.assertEqual(code, 0, output)
        result, payload = self.invoke(at="2026-10-02T09:00:00-06:00", body="A second entry in a new month.\n")
        self.assertEqual((result.returncode, payload["status"]), (0, "complete"), result.stdout)
        code, output = self.index_drift_exit()
        self.assertEqual(code, 0, output)
        # POSITIVE CONTROL: the gate does see drift. An entry written without the writer leaves the
        # index stale, and the same command exits 1.
        text = (self.tree / "journal" / "2026-10.md").read_text()
        (self.tree / "journal" / "2026-10.md").write_text(text + "\n## [2026-10-03 08:00] learning | Hand-written entry\n\nBody.\n")
        code, output = self.index_drift_exit()
        self.assertEqual(code, 1, output)

    def snapshot(self):
        found = {p.relative_to(self.tree).as_posix(): p.read_bytes()
                 for p in (self.month, self.index) if p.exists()}
        log_dir = self.tree / "log"
        if log_dir.is_dir() and not log_dir.is_symlink():
            found.update({f"log/{p.name}": (p.read_bytes() if p.is_file() and not p.is_symlink() else b"<non-regular>")
                          for p in log_dir.iterdir()})
        if (self.tree / "log.md").exists():
            found["log.md"] = (self.tree / "log.md").read_bytes()
        return found

    def swapped_during_temporary_create(self, *, mode: str, stage: int):
        """Swap the destination directory after validation, at temp creation."""
        outside = self.root / f"outside-{mode}-{stage}"
        outside.mkdir()
        parent = self.tree / ("journal" if mode == "journal" else "log")
        parked = self.root / f"parked-{mode}-{stage}"
        driver = """
import importlib.util, json, os, pathlib, sys, tempfile
spec = importlib.util.spec_from_file_location('writer', sys.argv[1])
writer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(writer)
parent, parked, outside = map(pathlib.Path, sys.argv[2:5])
stage = int(sys.argv[5])
counter = [0]
inside_mkstemp = [False]
def hit():
    counter[0] += 1
    if counter[0] == stage:
        parent.rename(parked)
        parent.symlink_to(outside, target_is_directory=True)
original_mkstemp = tempfile.mkstemp
def hooked_mkstemp(*args, **kwargs):
    if kwargs.get('prefix') == '.write-journal-':
        hit()
    inside_mkstemp[0] = True
    try:
        return original_mkstemp(*args, **kwargs)
    finally:
        inside_mkstemp[0] = False
tempfile.mkstemp = hooked_mkstemp
original_open = os.open
def hooked_open(path, flags, mode=0o777, *, dir_fd=None):
    if (not inside_mkstemp[0] and isinstance(path, str)
            and path.startswith('.write-journal-') and flags & os.O_CREAT):
        hit()
    return original_open(path, flags, mode, dir_fd=dir_fd)
os.open = hooked_open
raise SystemExit(writer.main(sys.argv[6:]))
"""
        args = [str(SCRIPT), str(parent), str(parked), str(outside), str(stage),
                "--repo-root", str(self.root), "--mode", mode,
                "--at", "2026-09-27T11:42:35-06:00", "--category", "learning",
                "--subject", "Diagnosed a stale input", "--body-file", str(self.body),
                "--today", TODAY]
        if mode == "log-only":
            args += ["--log-op", "promptbook"]
        result = subprocess.run([sys.executable, "-c", driver, *args],
                                capture_output=True, text=True)
        return result, json.loads(result.stdout), outside, parked

    def test_directory_swap_during_month_temporary_create_writes_nothing_outside(self):
        result, payload, outside, parked = self.swapped_during_temporary_create(
            mode="journal", stage=1)
        self.assertEqual((result.returncode, payload["status"]), (1, "refused"), result.stdout)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertEqual(list(parked.iterdir()), [])

    def test_directory_swap_during_log_temporary_create_writes_nothing_outside(self):
        result, payload, outside, parked = self.swapped_during_temporary_create(
            mode="log-only", stage=1)
        self.assertEqual((result.returncode, payload["status"]), (1, "refused"), result.stdout)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertTrue((parked / ".split-complete.json").exists())
        self.assertFalse((parked / "2026-09.md").exists())

    def test_directory_swap_during_index_temporary_create_reports_partial(self):
        result, payload, outside, parked = self.swapped_during_temporary_create(
            mode="journal", stage=2)
        self.assertEqual((result.returncode, payload["status"]), (1, "partial"), result.stdout)
        self.assertEqual(payload["recorded"], ["journal/2026-09.md"])
        self.assertEqual(payload["pending"], ["journal/index.md", "log/2026-09.md"])
        self.assertEqual(list(outside.iterdir()), [])
        self.assertTrue((parked / "2026-09.md").exists())
        self.assertFalse((parked / "index.md").exists())

    def test_existing_file_mode_survives_atomic_replacement(self):
        self.month.write_text("# Journal — 2026-09\n\n_Append-only. Newest entries at the top._\n\n")
        self.month.chmod(0o644)
        self.index.write_text("stale index\n")
        self.index.chmod(0o644)
        self.log.write_text("Prior log.\n")
        self.log.chmod(0o644)
        first, payload = self.invoke()
        self.assertEqual((first.returncode, payload["status"]), (0, "complete"), first.stdout)
        self.assertEqual(self.month.stat().st_mode & 0o777, 0o644)
        self.assertEqual(self.index.stat().st_mode & 0o777, 0o644)
        self.assertEqual(self.log.stat().st_mode & 0o777, 0o644)

    def test_journal_write_replay_and_distinct_minute(self):
        self.month.write_text("# Journal — 2026-09\n\n_Append-only. Newest entries at the top._\n\n"
                              "## [2026-09-01 08:00] bug | Prior finding\n\nPrior body.\n")
        self.log.write_text("## [2026-09-01] query | Prior operation\n\nPrior body.\n")
        first, result = self.invoke("--refs", "rule:journal-friction-line")
        self.assertEqual((first.returncode, result["status"]), (0, "complete"), first.stderr)
        self.assertEqual(result["written"], ["journal/2026-09.md", "journal/index.md", "log/2026-09.md"])
        self.assertIn("Prior body.", self.month.read_text())
        self.assertIn("Prior operation", self.log.read_text())
        self.assertEqual(len(journal_entries(self.month.read_text(), "2026-09")), 2)
        self.assertEqual(parse_index_row(self.index.read_text(), "2026-09")["entries"], 2)
        before = self.snapshot()
        replay, again = self.invoke("--refs", "rule:journal-friction-line")
        self.assertEqual((replay.returncode, again["status"], again["written"]),
                         (0, "complete", []), replay.stderr)
        self.assertEqual(self.snapshot(), before)
        later, _ = self.invoke("--refs", "rule:journal-friction-line",
                               at="2026-09-27T11:43:00-06:00")
        self.assertEqual(later.returncode, 0, later.stderr)
        self.assertEqual(len(journal_entries(self.month.read_text(), "2026-09")), 3)

    def test_existing_month_preamble_stays_above_new_entry(self):
        for preamble, prior in (
            ("# Journal — 2026-09\n\n_Append-only. Newest entries at the top._\n", ""),
            ("# Journal — 2026-09\n\n_Custom note for this journal._\n\n",
             "## [2026-09-01 08:00] bug | Prior finding\n\nPrior body.\n"),
        ):
            with self.subTest(preamble=preamble):
                self.month.write_text(preamble + prior)
                first, result = self.invoke()
                self.assertEqual((first.returncode, result["status"]), (0, "complete"), first.stderr)
                written = self.month.read_text()
                self.assertTrue(written.startswith(preamble), written)
                self.assertLess(written.index(preamble.rstrip().split("\n")[-1]),
                                written.index("## [2026-09-27 11:42]"))
                self.assertIn(prior, written)
                self.assertEqual(parse_index_row(self.index.read_text(), "2026-09")["entries"],
                                 2 if prior else 1)
                self.index.unlink()
                self.log.unlink()

    def test_older_month_header_keeps_prior_entry_bytes(self):
        prior = "## [2026-09-01 08:00] bug | Prior finding\n\nPrior body.\n"
        self.month.write_text("# Journal — 2026-09\n\n" + prior)
        first, payload = self.invoke()
        self.assertEqual((first.returncode, payload["status"]), (0, "complete"), first.stderr)
        self.assertTrue(self.month.read_text().endswith(prior))

    def test_log_only_has_one_write_and_is_replayable(self):
        first, result = self.invoke("--log-op", "promptbook", mode="log-only")
        self.assertEqual((first.returncode, result["written"]), (0, ["log/2026-09.md"]), first.stderr)
        self.assertFalse(self.month.exists())
        self.assertFalse(self.index.exists())
        self.assertIn("2026-09-27T11:42-06:00", self.log.read_text())
        before = self.snapshot()
        replay, result = self.invoke("--log-op", "promptbook", mode="log-only")
        self.assertEqual((replay.returncode, result["written"]), (0, []), replay.stderr)
        self.assertEqual(self.snapshot(), before)
        conflict, payload = self.invoke("--log-op", "promptbook", mode="log-only",
                                        body="A different operation at the same minute.\n")
        self.assertEqual((conflict.returncode, payload["status"]), (1, "refused"))
        self.assertEqual(self.snapshot(), before)
        later, payload = self.invoke("--log-op", "promptbook", mode="log-only",
                                      at="2026-09-27T11:43:00-06:00",
                                      body="A different operation at the next minute.\n")
        self.assertEqual((later.returncode, payload["status"]), (0, "complete"), later.stderr)
        self.assertEqual(self.log.read_text().count("## [2026-09-27] promptbook |"), 2)

    def test_headed_log_keeps_header_and_prior_entries_in_journal_mode(self):
        prior = "## [2026-09-01] query | Prior operation\n\nPrior body.\n\n"
        self.log.write_text(LOG_HEADER + prior)
        first, payload = self.invoke()
        self.assertEqual((first.returncode, payload["status"]), (0, "complete"), first.stdout)
        self.assertTrue(self.log.read_text().startswith(
            LOG_HEADER + "## [2026-09-27] journal | learning: Diagnosed a stale input\n"))
        self.assertTrue(self.log.read_text().endswith(prior))
        before = self.snapshot()
        replay, payload = self.invoke()
        self.assertEqual((replay.returncode, payload["written"]), (0, []), replay.stdout)
        self.assertEqual(self.snapshot(), before)

    def test_headed_log_keeps_header_and_prior_entries_in_log_only_mode(self):
        prior = "## [2026-09-01] query | Prior operation\n\nPrior body.\n\n"
        self.log.write_text(LOG_HEADER + prior)
        first, payload = self.invoke("--log-op", "promptbook", mode="log-only")
        self.assertEqual((first.returncode, payload["status"]), (0, "complete"), first.stdout)
        self.assertTrue(self.log.read_text().startswith(
            LOG_HEADER + "## [2026-09-27] promptbook | Diagnosed a stale input\n"))
        self.assertTrue(self.log.read_text().endswith(prior))
        before = self.snapshot()
        replay, payload = self.invoke("--log-op", "promptbook", mode="log-only")
        self.assertEqual((replay.returncode, payload["written"]), (0, []), replay.stdout)
        self.assertEqual(self.snapshot(), before)

    def test_missing_or_edited_detail_header_keeps_outside_bytes_and_inserts_at_first_entry(self):
        prior = "## [2026-09-01] query | Prior operation\n\nPrior body.\n\n"
        for outside in ("", "# Edited heading\n\nA hand note.\n\n"):
            with self.subTest(outside=outside):
                self.log.write_text(outside + prior)
                first, payload = self.invoke("--log-op", "promptbook", mode="log-only")
                self.assertEqual((first.returncode, payload["status"]), (0, "complete"), first.stdout)
                self.assertEqual(self.log.read_text(), outside +
                                 "## [2026-09-27] promptbook | Diagnosed a stale input\n\n"
                                 "The first attempt failed because the input was stale.\n"
                                 "Recorded at 2026-09-27T11:42-06:00.\n\n" + prior)

    def test_a_legacy_log_md_is_split_before_the_write(self):
        shutil.rmtree(self.tree / "log")
        legacy = "# Operations log\n\n## [2026-08-01] init | Tree\n\nBody.\n"
        (self.tree / "log.md").write_text(legacy)
        good, payload = self.invoke()
        self.assertEqual((good.returncode, payload["status"]), (0, "complete"), good.stdout)
        self.assertFalse((self.tree / "log.md").exists())
        self.assertEqual((self.tree / "log" / "2026-08.md").read_text(),
                         "# Operations log: 2026-08\n\n_Append-only. Latest write first._\n\n"
                         "## [2026-08-01] init | Tree\n\nBody.\n")
        self.assertIn("## [2026-09-27] journal | learning: Diagnosed a stale input", self.log.read_text())
        self.assertTrue((self.tree / "log" / ".split-complete.json").is_file())
        for path in ("docs/log.md", "docs/log/2026-08.md", "docs/log/.split-complete.json", "docs/log/2026-09.md"):
            self.assertIn(path, payload["changed_paths"])

    def test_an_invalid_request_on_an_unsplit_tree_or_beside_a_stray_changes_nothing(self):
        stray = "## [2026-09-02] query | Written by an older plugin\n\nBody.\n"
        for label in ("unsplit", "stray"):
            with self.subTest(fixture=label):
                if label == "unsplit":
                    shutil.rmtree(self.tree / "log", ignore_errors=True)
                    (self.tree / "log.md").write_text("# Operations log\n\n## [2026-08-01] init | Tree\n\nBody.\n")
                else:
                    (self.tree / "log.md").write_text(stray)
                before = self.snapshot()
                for extra, mode, body in ((("--log-op", "bogus"), "log-only", None), ((), "journal", "A sentence.\n```\n")):
                    bad, payload = self.invoke(*extra, mode=mode, body=body)
                    self.assertEqual((bad.returncode, payload["status"]), (1, "refused"), bad.stdout)
                    self.assertEqual(self.snapshot(), before)
                # POSITIVE CONTROL: a valid request repairs the log and writes.
                good, payload = self.invoke(body="A sentence.\n")
                self.assertEqual((good.returncode, payload["status"]), (0, "complete"), good.stdout)
                self.assertFalse((self.tree / "log.md").exists())

    def test_a_malformed_stray_heading_refuses_with_the_journal_month_unchanged(self):
        (self.tree / "log.md").write_text("## [2026-09-02] nonsense | Bad heading\n\nBody.\n")
        before = self.snapshot()
        bad, payload = self.invoke()
        self.assertEqual((bad.returncode, payload["status"], payload.get("code")),
                         (1, "refused", "malformed-heading"), bad.stdout)
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(self.month.exists())
        # POSITIVE CONTROL: after the heading is fixed the same request writes.
        (self.tree / "log.md").write_text("## [2026-09-02] query | Fixed heading\n\nBody.\n")
        good, payload = self.invoke()
        self.assertEqual((good.returncode, payload["status"]), (0, "complete"), good.stdout)
        self.assertTrue(self.month.exists())

    def test_invalid_operation_fence_and_unsafe_path_write_nothing(self):
        invalid, payload = self.invoke("--log-op", "bogus", mode="log-only")
        self.assertEqual((invalid.returncode, payload["status"]), (1, "refused"))
        self.assertEqual(self.snapshot(), self.baseline)
        fence, payload = self.invoke(body="A sentence.\n```\n")
        self.assertEqual((fence.returncode, payload["status"]), (1, "refused"))
        self.assertEqual(self.snapshot(), self.baseline)
        self.log.symlink_to(self.root / "outside-log.md")
        unsafe, payload = self.invoke()
        self.assertEqual((unsafe.returncode, payload["status"]), (1, "refused"))
        self.assertEqual(payload["recorded"], [])
        self.assertFalse(self.month.exists())

    def test_log_op_must_be_the_complete_canonical_token(self):
        forged = "journal | forged\n## [2026-09-27] release"
        bad, payload = self.invoke("--log-op", forged, mode="log-only")
        self.assertEqual((bad.returncode, payload["status"]), (1, "refused"))
        self.assertEqual(self.snapshot(), self.baseline)

    def test_log_only_replay_reads_recorded_minute_field_not_narrative(self):
        first_body = "I scheduled the check for 2026-09-27T11:43-06:00.\n"
        first, payload = self.invoke("--log-op", "promptbook", mode="log-only",
                                     body=first_body)
        self.assertEqual((first.returncode, payload["status"]), (0, "complete"), first.stdout)
        second, payload = self.invoke("--log-op", "promptbook", mode="log-only",
                                      at="2026-09-27T11:43:00-06:00",
                                      body="The planned check completed.\n")
        self.assertEqual((second.returncode, payload["status"]), (0, "complete"), second.stdout)
        self.assertEqual(self.log.read_text().count("## [2026-09-27] promptbook |"), 2)

    def test_completed_journal_refuses_same_civil_minute_with_different_offset(self):
        first, payload = self.invoke()
        self.assertEqual((first.returncode, payload["status"]), (0, "complete"), first.stdout)
        before = self.snapshot()
        changed, payload = self.invoke(at="2026-09-27T11:42:35-07:00")
        self.assertEqual((changed.returncode, payload["status"]), (1, "refused"))
        self.assertEqual(self.snapshot(), before)

    def test_completed_log_only_refuses_same_civil_minute_with_different_offset(self):
        first, payload = self.invoke("--log-op", "promptbook", mode="log-only")
        self.assertEqual((first.returncode, payload["status"]), (0, "complete"), first.stdout)
        before = self.snapshot()
        changed, payload = self.invoke("--log-op", "promptbook", mode="log-only",
                                       at="2026-09-27T11:42:35-07:00")
        self.assertEqual((changed.returncode, payload["status"]), (1, "refused"))
        self.assertEqual(self.snapshot(), before)

    def test_month_only_replay_warns_that_offset_cannot_be_verified(self):
        header = "# Journal — 2026-09\n\n_Append-only. Newest entries at the top._\n\n"
        self.month.write_text(header +
                              "## [2026-09-27 11:42] learning | Diagnosed a stale input\n\n"
                              "The first attempt failed because the input was stale.\n\n")
        replay, payload = self.invoke()
        self.assertEqual((replay.returncode, payload["status"]), (0, "complete"), replay.stdout)
        self.assertTrue(any("offset" in warning and "unverified" in warning
                            for warning in payload["warnings"]))
        self.assertEqual(payload["written"], ["journal/index.md", "log/2026-09.md"])

    def test_caller_offset_selects_month_independent_of_host_zone(self):
        with patch.dict(os.environ, {"TZ": "Pacific/Kiritimati"}):
            first, payload = self.invoke(at="2026-10-01T00:15:48+01:00")
        self.assertEqual((first.returncode, payload["status"]), (0, "complete"), first.stdout)
        self.assertTrue((self.tree / "journal" / "2026-10.md").exists())
        before = self.snapshot()
        with patch.dict(os.environ, {"TZ": "Pacific/Honolulu"}):
            replay, payload = self.invoke(at="2026-10-01T00:15:48+01:00")
        self.assertEqual((replay.returncode, payload["status"]), (0, "complete"), replay.stdout)
        self.assertEqual(payload["written"], [])
        self.assertEqual(self.snapshot(), before)

    def test_utc_spellings_normalize_and_naive_time_refuses(self):
        first, payload = self.invoke(at="2026-09-27T11:42:35Z")
        self.assertEqual((first.returncode, payload["timestamp"]),
                         (0, "2026-09-27T11:42+00:00"), first.stdout)
        self.assertIn("2026-09-27T11:42+00:00", self.log.read_text())
        replay, payload = self.invoke(at="2026-09-27T11:42:59-00:00")
        self.assertEqual((replay.returncode, payload["written"]), (0, []), replay.stdout)
        before = self.snapshot()
        naive, payload = self.invoke(at="2026-09-27T11:43:00")
        self.assertEqual((naive.returncode, payload["status"]), (1, "refused"))
        self.assertEqual(self.snapshot(), before)

    def test_category_fallback_and_same_minute_conflict(self):
        first, payload = self.invoke("--category", "impossible")
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertTrue(payload["warnings"])
        self.assertIn("misc |", self.month.read_text())
        before = self.snapshot()
        conflict, payload = self.invoke("--category", "impossible", body="A changed account.\n")
        self.assertEqual((conflict.returncode, payload["status"]), (1, "refused"))
        self.assertEqual(self.snapshot(), before)

    def test_bad_existing_month_blocks_journal_but_not_log_only(self):
        self.month.write_text("# Journal — 2026-09\n\n```\n")
        bad, payload = self.invoke()
        self.assertEqual((bad.returncode, payload["status"]), (1, "refused"))
        self.assertFalse(self.index.exists())
        self.assertFalse(self.log.exists())
        fine, payload = self.invoke("--log-op", "promptbook", mode="log-only")
        self.assertEqual((fine.returncode, payload["status"]), (0, "complete"), fine.stderr)
        self.assertEqual(self.month.read_text(), "# Journal — 2026-09\n\n```\n")

    def test_failed_index_stage_reports_partial_and_retry_repairs(self):
        self.index.mkdir()
        rejected, payload = self.invoke()
        self.assertEqual((rejected.returncode, payload["status"]), (1, "refused"))
        self.assertFalse(self.month.exists())
        self.index.rmdir()
        # Fail the index stage after the month committed, then replay.
        driver = """
import importlib.util, sys
spec = importlib.util.spec_from_file_location('writer', sys.argv[1])
writer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(writer)
def fail_index(*args):
    raise OSError('forced index I/O failure')
writer._render_index = fail_index
raise SystemExit(writer.main(sys.argv[2:]))
"""
        args = [str(SCRIPT), "--repo-root", str(self.root), "--mode", "journal",
                "--at", "2026-09-27T11:42:35-06:00", "--category", "learning",
                "--subject", "Diagnosed a stale input", "--body-file", str(self.body),
                "--today", TODAY]
        failure = subprocess.run([sys.executable, "-c", driver, *args],
                                 capture_output=True, text=True)
        payload = json.loads(failure.stdout)
        self.assertEqual((failure.returncode, payload["status"]), (1, "partial"))
        self.assertEqual(payload["recorded"], ["journal/2026-09.md"])
        self.assertEqual(payload["pending"], ["journal/index.md", "log/2026-09.md"])
        self.assertFalse(self.index.exists())
        self.assertFalse(self.log.exists())
        replay, payload = self.invoke()
        self.assertEqual((replay.returncode, payload["status"]), (0, "complete"), replay.stderr)
        self.assertEqual(payload["written"], ["journal/index.md", "log/2026-09.md"])
        self.assertEqual(len(journal_entries(self.month.read_text(), "2026-09")), 1)
        self.assertEqual(parse_index_row(self.index.read_text(), "2026-09")["entries"], 1)

    def test_process_death_after_atomic_month_replace_replays_without_duplicate(self):
        driver = """
import importlib.util, os, sys
spec = importlib.util.spec_from_file_location('writer', sys.argv[1])
writer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(writer)
original = writer._atomic_replace
def die_after_month(path, want, have, tree, root):
    original(path, want, have, tree, root)
    if path.name == '2026-09.md':
        os._exit(71)
writer._atomic_replace = die_after_month
writer.main(sys.argv[2:])
"""
        args = [str(SCRIPT), "--repo-root", str(self.root), "--mode", "journal",
                "--at", "2026-09-27T11:42:35-06:00", "--category", "learning",
                "--subject", "Diagnosed a stale input", "--body-file", str(self.body),
                "--today", TODAY]
        died = subprocess.run([sys.executable, "-c", driver, *args], capture_output=True,
                              text=True)
        self.assertEqual(died.returncode, 71)
        self.assertTrue(self.month.read_text().startswith("# Journal — 2026-09\n"))
        self.assertFalse(self.index.exists())
        replay, payload = self.invoke()
        self.assertEqual((replay.returncode, payload["status"]), (0, "complete"), replay.stderr)
        self.assertEqual(len(journal_entries(self.month.read_text(), "2026-09")), 1)

    def test_process_death_before_replace_leaves_old_file_intact_and_retry_succeeds(self):
        prior = "# Journal — 2026-09\n\n## [2026-09-01 08:00] bug | Prior\n\nPrior body.\n"
        self.month.write_text(prior)
        driver = """
import importlib.util, os, sys
spec = importlib.util.spec_from_file_location('writer', sys.argv[1])
writer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(writer)
def die_before_replace(*args, **kwargs):
    os._exit(72)
writer.os.replace = die_before_replace
writer.main(sys.argv[2:])
"""
        args = [str(SCRIPT), "--repo-root", str(self.root), "--mode", "journal",
                "--at", "2026-09-27T11:42:35-06:00", "--category", "learning",
                "--subject", "Diagnosed a stale input", "--body-file", str(self.body),
                "--today", TODAY]
        died = subprocess.run([sys.executable, "-c", driver, *args], capture_output=True,
                              text=True)
        self.assertEqual(died.returncode, 72)
        self.assertEqual(self.month.read_text(), prior)
        replay, payload = self.invoke()
        self.assertEqual((replay.returncode, payload["status"]), (0, "complete"), replay.stderr)
        self.assertEqual(len(journal_entries(self.month.read_text(), "2026-09")), 2)

    def test_body_stdin_and_body_file_symlink_refusal(self):
        command = [sys.executable, str(SCRIPT), "--repo-root", str(self.root),
                   "--mode", "log-only", "--at", "2026-09-27T11:42:35-06:00",
                   "--category", "learning", "--subject", "Diagnosed a stale input",
                   "--body-stdin", "--log-op", "promptbook", "--today", TODAY]
        completed = subprocess.run(command, input="Recorded a run result.\n", text=True,
                                   capture_output=True)
        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertIn("Recorded a run result.", self.log.read_text())
        link = self.root / "body-link.txt"
        link.symlink_to(self.body)
        before = self.snapshot()
        bad = subprocess.run([sys.executable, str(SCRIPT), "--repo-root", str(self.root),
                              "--mode", "journal", "--at", "2026-09-27T11:43:00-06:00",
                              "--category", "learning", "--subject", "Later observation",
                              "--body-file", str(link), "--today", TODAY], capture_output=True, text=True)
        self.assertEqual((bad.returncode, json.loads(bad.stdout)["status"]), (1, "refused"))
        self.assertEqual(self.snapshot(), before)

    def test_ten_body_lines_with_optional_refs_are_admitted(self):
        ten_lines = "\n".join(f"A concrete sentence {i}." for i in range(10)) + "\n"
        wrote, payload = self.invoke("--refs", "rule:journal-friction-line", body=ten_lines)
        self.assertEqual((wrote.returncode, payload["status"]), (0, "complete"), wrote.stdout)
        self.assertIn("A concrete sentence 9.\nRefs: rule:journal-friction-line", self.month.read_text())

    def test_eleven_body_lines_or_malformed_refs_refuse(self):
        eleven_lines = "\n".join(f"A concrete sentence {i}." for i in range(11)) + "\n"
        bad, payload = self.invoke(body=eleven_lines)
        self.assertEqual((bad.returncode, payload["status"]), (1, "refused"))
        self.assertEqual(self.snapshot(), self.baseline)
        bad, payload = self.invoke("--refs", "not-a-ref", body="I found the cause.\n")
        self.assertEqual((bad.returncode, payload["status"]), (1, "refused"))
        self.assertEqual(self.snapshot(), self.baseline)

    def test_journal_preserves_interior_paragraph_breaks(self):
        body = "The first attempt failed.\n\nThe second fixed it.\n"
        wrote, payload = self.invoke(body=body)
        self.assertEqual((wrote.returncode, payload["status"]), (0, "complete"), wrote.stdout)
        self.assertIn("The first attempt failed.\n\nThe second fixed it.\n", self.month.read_text())

    def test_log_only_still_requires_one_nonempty_line(self):
        bad, payload = self.invoke("--log-op", "promptbook", mode="log-only",
                                   body="First operation.\n\nSecond operation.\n")
        self.assertEqual((bad.returncode, payload["status"]), (1, "refused"))
        self.assertEqual(self.snapshot(), self.baseline)


if __name__ == "__main__":
    unittest.main()
