"""The operations log's monthly detail files: the cutter, the writer, the commit step and the check.

Every fixture builds a temporary tree; nothing here reads or writes this repository's own tree.
"""

from __future__ import annotations

import dataclasses
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
CLI = SCRIPTS / "operation-log.py"
WRITER = SCRIPTS / "write-journal.py"
TEMPLATE = SCRIPTS.parent / "templates" / "AGENTS.md.tmpl"
sys.path.insert(0, str(SCRIPTS))
import operation_log as ol  # noqa: E402

TODAY = "2026-11-11"
HEADER_11 = "# Operations log: 2026-11\n\n_Append-only. Latest write first._\n\n"


def entry(date: str, op: str, subject: str, body: str = "Body.") -> str:
    return f"## [{date}] {op} | {subject}\n\n{body}\n\n"


class TreeCase(unittest.TestCase):
    """A temporary repository with a docs tree and the template's section 6."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.tree = self.root / "docs"
        self.tree.mkdir()
        (self.root / ".bionic.yml").write_text('config_version: "1"\ndocs_dir: docs\n')
        (self.tree / "manifest.yml").write_text('schema_version: "5"\nconcerns_enabled: [journal]\n')
        (self.tree / "AGENTS.md").write_bytes(TEMPLATE.read_bytes())
        self.log_dir = self.tree / "log"
        environment = patch.dict(os.environ, {ol.TEST_ENV: "1", "UV_NO_CONFIG": "1"})
        environment.start()
        self.addCleanup(environment.stop)

    def split(self, **files: str) -> None:
        """A split tree: log/ with its completion record and the named detail files."""
        self.log_dir.mkdir(exist_ok=True)
        (self.log_dir / ol.COMPLETION_NAME).write_bytes(ol.completion_bytes(None, {}))
        for name, text in files.items():
            (self.log_dir / f"{name}.md").write_text(text)

    def snapshot(self) -> dict:
        found = {}
        for path in sorted(self.tree.rglob("*")):
            rel = path.relative_to(self.tree).as_posix()
            if path.is_symlink():
                found[rel] = "symlink:" + os.readlink(path)
            elif path.is_file():
                found[rel] = path.read_bytes()
            elif path.is_dir():
                found[rel] = "dir"
            else:
                found[rel] = "special"
        return found

    def append(self, *args, op="query", subject="Asked a question", date="2026-11-05",
               body="An answer.\n", today=TODAY, env=None):
        command = [sys.executable, str(CLI), "append", "--repo-root", str(self.root), "--op", op,
                   "--subject", subject, "--date", date, "--body-stdin", *args]
        if today is not None:
            command += ["--today", today]
        done = subprocess.run(command, input=body, capture_output=True, text=True,
                              env=env if env is not None else dict(os.environ))
        if not done.stdout.strip():
            self.fail(f"operation-log append printed no result (exit {done.returncode}): {done.stderr}")
        return done.returncode, json.loads(done.stdout)

    def check(self):
        done = subprocess.run([sys.executable, str(CLI), "check", "--repo-root", str(self.root)],
                              capture_output=True, text=True)
        if not done.stdout.strip():
            self.fail(f"operation-log check printed no report (exit {done.returncode}): {done.stderr}")
        return done.returncode, json.loads(done.stdout)


class CutterTests(unittest.TestCase):
    def test_a_heading_inside_a_fence_stays_inside_its_entry(self):
        text = "pre\n" + "## [2026-11-01] query | A\n\n```\n## [2026-11-02] query | inside\n```\n\n" + entry("2026-10-01", "query", "B")
        pieces = ol.cut(text)
        self.assertEqual(pieces.outside, "pre\n")
        self.assertEqual(len(pieces.entries), 2)
        self.assertIn("## [2026-11-02] query | inside", pieces.entries[0])
        self.assertFalse(pieces.open_fence)
        self.assertTrue(ol.reconstructs(text, pieces))

    def test_a_fence_left_open_runs_to_the_end_of_the_file(self):
        text = entry("2026-11-01", "query", "A") + "```\n## [2026-11-02] query | swallowed\n"
        pieces = ol.cut(text)
        self.assertEqual(len(pieces.entries), 1)
        self.assertTrue(pieces.open_fence)

    def test_a_last_entry_without_a_newline_gains_its_terminal_newline(self):
        text = "## [2026-11-01] query | A\n\nNo newline"
        pieces = ol.cut(text)
        self.assertEqual(pieces.entries, ("## [2026-11-01] query | A\n\nNo newline\n",))
        self.assertTrue(pieces.added_newline)
        self.assertTrue(ol.reconstructs(text, pieces))
        # Placing the entry above another adds no byte outside an entry.
        placed = ol.insert(HEADER_11 + entry("2026-11-02", "query", "C"), list(pieces.entries))
        self.assertEqual(ol.cut(placed).entries[0], pieces.entries[0])

    def test_insertion_into_outside_bytes_without_a_newline_adds_one_outside_byte(self):
        self.assertEqual(ol.insert("note", ["## [2026-11-01] query | A\n\nB\n\n"]),
                         "note\n## [2026-11-01] query | A\n\nB\n\n")


class ValidateEntryTests(TreeCase):
    def test_a_valid_request_renders_one_entry(self):
        made = ol.validate_entry(self.tree, "2026-11-05", "query", "Asked", "An answer.\n")
        self.assertEqual(made.text, entry("2026-11-05", "query", "Asked", "An answer."))

    def test_invalid_requests_refuse(self):
        cases = {
            "invalid-op": ("2026-11-05", "bogus", "Asked", "Body."),
            "invalid-subject": ("2026-11-05", "query", "A | B", "Body."),
            "invalid-date": ("2026-13-04", "query", "Asked", "Body."),
        }
        cases["invalid-date-day"] = ("2026-11-00", "query", "Asked", "Body.")
        cases["unfenced-heading"] = ("2026-11-05", "query", "Asked", "Line.\n## Not a heading\n")
        cases["open-fence"] = ("2026-11-05", "query", "Asked", "Line.\n```\ncode\n")
        for label, args in cases.items():
            with self.subTest(label=label):
                with self.assertRaises(ol.Refusal):
                    ol.validate_entry(self.tree, *args)
        # POSITIVE CONTROL: a closed fence holding a `## ` line is one entry.
        ol.validate_entry(self.tree, "2026-11-05", "query", "Asked", "Line.\n```\n## inside\n```\n")


class AppendTests(TreeCase):
    def test_init_on_a_tree_with_only_agents_md_writes_completion_header_and_entry(self):
        code, result = self.append(op="init", subject="Initialised the tree", date=TODAY)
        self.assertEqual((code, result["status"]), (0, "written"), result)
        self.assertEqual(result["file"], "docs/log/2026-11.md")
        self.assertEqual(result["changed_paths"], ["docs/log/.split-complete.json", "docs/log/2026-11.md"])
        self.assertTrue((self.log_dir / ol.COMPLETION_NAME).is_file())
        self.assertFalse((self.tree / "log.md").exists())
        self.assertEqual((self.log_dir / "2026-11.md").read_text(),
                         HEADER_11 + entry(TODAY, "init", "Initialised the tree", "An answer."))
        for key in ("commit_paths", "restore_paths", "left_strays"):
            self.assertIn(key, result)

    def test_earlier_and_later_heading_dates_land_in_the_current_month_with_one_header(self):
        self.split()
        for date in ("2026-10-02", "2026-12-01"):
            code, result = self.append(date=date, subject=f"Dated {date}")
            self.assertEqual((code, result["status"], result["file"]), (0, "written", "docs/log/2026-11.md"), result)
        text = (self.log_dir / "2026-11.md").read_text()
        self.assertEqual(text.count("# Operations log: 2026-11"), 1)
        self.assertLess(text.index("Dated 2026-12-01"), text.index("Dated 2026-10-02"))
        self.assertFalse((self.log_dir / "2026-10.md").exists())
        self.assertFalse((self.log_dir / "2026-12.md").exists())

    def test_a_rerun_after_the_month_changes_reports_recorded_and_adds_nothing(self):
        self.split()
        code, first = self.append(today="2026-11-30")
        self.assertEqual((code, first["status"]), (0, "written"), first)
        before = self.snapshot()
        code, again = self.append(today="2026-12-01")
        self.assertEqual((code, again["status"], again["file"]), (0, "recorded", "docs/log/2026-11.md"), again)
        self.assertEqual(self.snapshot(), before)
        self.assertFalse((self.log_dir / "2026-12.md").exists())

    def test_a_body_with_an_unfenced_heading_or_an_open_fence_refuses_unchanged(self):
        self.split(**{"2026-11": HEADER_11 + entry("2026-11-01", "init", "Tree")})
        before = self.snapshot()
        for body in ("Line.\n## [2026-11-02] query | forged\n", "Line.\n```\nopen\n"):
            with self.subTest(body=body):
                code, result = self.append(body=body)
                self.assertEqual((code, result["status"], result["code"]), (1, "refused", "invalid-body"), result)
                self.assertEqual(self.snapshot(), before)

    def test_a_heading_date_that_is_not_a_calendar_date_refuses(self):
        self.split()
        before = self.snapshot()
        for date in ("2026-13-04", "2026-11-00"):
            code, result = self.append(date=date)
            self.assertEqual((code, result["code"]), (1, "invalid-date"), result)
        self.assertEqual(self.snapshot(), before)

    def test_destination_outside_bytes_leaving_a_fence_open_refuse_in_preflight(self):
        self.split(**{"2026-11": HEADER_11 + "```\nan open fence\n"})
        before = self.snapshot()
        code, result = self.append()
        self.assertEqual((code, result["code"]), (1, "insertion-check"), result)
        self.assertEqual(self.snapshot(), before)
        # POSITIVE CONTROL: a closed fence in the outside bytes admits the write.
        (self.log_dir / "2026-11.md").write_text(HEADER_11 + "```\nclosed\n```\n\n")
        code, result = self.append()
        self.assertEqual((code, result["status"]), (0, "written"), result)

    def test_non_regular_log_files_refuse_in_preflight(self):
        outside = self.root / "outside.md"
        outside.write_text(HEADER_11)

        def symlinked_destination():
            self.split()
            (self.log_dir / "2026-11.md").symlink_to(outside)

        def fifo_destination():
            self.split()
            os.mkfifo(self.log_dir / "2026-11.md")

        def symlinked_older_month():
            self.split()
            (self.log_dir / "2026-10.md").symlink_to(outside)

        def symlinked_log_dir():
            elsewhere = self.root / "elsewhere"
            elsewhere.mkdir()
            self.log_dir.symlink_to(elsewhere, target_is_directory=True)

        for label, build in (("destination symlink", symlinked_destination), ("destination FIFO", fifo_destination),
                             ("older month symlink", symlinked_older_month), ("log/ symlink", symlinked_log_dir)):
            with self.subTest(fixture=label):
                build()
                before = self.snapshot()
                code, result = self.append()
                self.assertEqual((code, result["status"]), (1, "refused"), result)
                self.assertEqual(self.snapshot(), before)
                self.assertEqual(outside.read_text(), HEADER_11)
                if self.log_dir.is_symlink():
                    self.log_dir.unlink()
                else:
                    for path in self.log_dir.iterdir():
                        path.unlink()
                    self.log_dir.rmdir()
        # POSITIVE CONTROL: a regular destination accepts the same request.
        self.split(**{"2026-11": HEADER_11})
        code, result = self.append()
        self.assertEqual((code, result["status"]), (0, "written"), result)

    def test_today_in_a_write_mode_refuses_without_the_test_variable(self):
        self.split()
        env = {key: value for key, value in os.environ.items() if key != ol.TEST_ENV}
        before = self.snapshot()
        code, result = self.append(env=env)
        self.assertEqual((code, result["code"]), (1, "today-not-allowed"), result)
        self.assertEqual(self.snapshot(), before)
        # POSITIVE CONTROL: with the variable the same command writes.
        code, result = self.append()
        self.assertEqual((code, result["status"]), (0, "written"), result)


class PhasedOrderTests(TreeCase):
    def test_repair_refuses_with_nothing_written_when_a_planned_file_changed(self):
        self.log_dir.mkdir()
        (self.log_dir / "2026-10.md").write_text(entry("2026-10-01", "init", "Tree"))
        made = ol.validate_entry(self.tree, "2026-11-05", "query", "Asked", "Body.")
        plan = ol.preflight(self.tree, TODAY, made)
        self.assertEqual(plan.actions, ("record-completion",))
        (self.log_dir / "2026-10.md").write_text(entry("2026-10-01", "init", "Tree") + entry("2026-10-02", "query", "Late"))
        before = self.snapshot()
        with self.assertRaises(ol.Refusal) as caught:
            ol.repair(self.tree, plan, self.root)
        self.assertEqual(caught.exception.code, "plan-stale")
        self.assertEqual(self.snapshot(), before)
        # POSITIVE CONTROL: a fresh plan over the same bytes runs.
        self.assertEqual(ol.repair(self.tree, ol.preflight(self.tree, TODAY, made), self.root),
                         ["log/.split-complete.json"])

    def test_the_post_repair_insertion_check_refuses_before_any_caller_write(self):
        self.log_dir.mkdir()
        made = ol.validate_entry(self.tree, "2026-11-05", "query", "Asked", "Body.")
        plan = ol.preflight(self.tree, TODAY, made)
        # The destination as a repair left it: its outside bytes leave a fence open.
        (self.log_dir / "2026-11.md").write_text(HEADER_11 + "```\nopen\n")
        reads = dict(plan.reads)
        reads["log/2026-11.md"] = ol._digest((self.log_dir / "2026-11.md").read_bytes())
        caller_surface = self.tree / "caller.md"
        with self.assertRaises(ol.Refusal) as caught:
            ol.repair(self.tree, dataclasses.replace(plan, reads=reads), self.root)
            caller_surface.write_text("the caller's own write\n")
        self.assertEqual(caught.exception.code, "insertion-check")
        self.assertFalse(caller_surface.exists())

    def write_journal(self, *args, today_args=("--today", "2026-11-11")):
        return [str(WRITER), "--repo-root", str(self.root), "--mode", "log-only", "--at",
                "2026-11-11T09:00:00-06:00", "--category", "learning", "--subject", "Recorded a run",
                "--body-stdin", "--log-op", "promptbook", *today_args, *args]

    def run_driver(self, driver: str, args: list[str]):
        done = subprocess.run([sys.executable, "-c", driver, *args], input="One line.\n",
                              capture_output=True, text=True)
        return done.returncode, json.loads(done.stdout), done

    def test_a_stray_created_after_the_repair_phase_is_left_and_named(self):
        self.split()
        driver = """
import importlib.util, sys
spec = importlib.util.spec_from_file_location('writer', sys.argv[1])
writer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(writer)
original = writer.ol.repair
def repair_then_an_older_writer(tree, plan, root=None):
    changed = original(tree, plan, root)
    (tree / 'log.md').write_text('## [2026-11-11] query | written by an older plugin\\n\\nBody.\\n')
    return changed
writer.ol.repair = repair_then_an_older_writer
raise SystemExit(writer.main(sys.argv[2:]))
"""
        code, payload, done = self.run_driver(driver, self.write_journal())
        self.assertEqual((code, payload["status"]), (0, "complete"), done.stdout + done.stderr)
        self.assertEqual(payload["left_strays"], ["docs/log.md"])
        self.assertIn("Recorded a run", (self.log_dir / "2026-11.md").read_text())
        self.assertNotIn("older plugin", (self.log_dir / "2026-11.md").read_text())

    def test_one_local_date_read_before_validation_governs_the_whole_write(self):
        self.split()
        driver = """
import importlib.util, sys
spec = importlib.util.spec_from_file_location('writer', sys.argv[1])
writer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(writer)
dates = iter(['2026-11-30'] + ['2026-12-01'] * 20)
writer.ol.local_date = lambda: next(dates)
raise SystemExit(writer.main(sys.argv[2:]))
"""
        code, payload, done = self.run_driver(driver, self.write_journal(today_args=()))
        self.assertEqual((code, payload["status"]), (0, "complete"), done.stdout + done.stderr)
        self.assertEqual(payload["recorded"], ["log/2026-11.md"])
        self.assertTrue((self.log_dir / "2026-11.md").is_file())
        self.assertFalse((self.log_dir / "2026-12.md").exists())


class ReadEntriesTests(TreeCase):
    def test_a_legacy_log_md_is_read_on_an_unsplit_tree(self):
        (self.tree / "log.md").write_text("# Operations log\n\n" + entry("2026-09-02", "query", "B") + entry("2026-09-01", "init", "A"))
        found = ol.read_entries(self.tree)
        self.assertEqual([(e.path, e.parsed()[2]) for e in found], [("log.md", "B"), ("log.md", "A")])
        self.assertEqual(ol.read_text(self.tree), entry("2026-09-02", "query", "B") + entry("2026-09-01", "init", "A"))

    def test_detail_files_read_newest_month_first_and_legacy_counts_beyond_them(self):
        self.log_dir.mkdir()
        shared = entry("2026-09-01", "init", "A")
        (self.log_dir / "2026-09.md").write_text(shared)
        (self.log_dir / "2026-10.md").write_text(entry("2026-10-01", "query", "C"))
        (self.log_dir / (".legacy-" + "d" * 64 + ".md")).write_text(shared + shared + entry("2026-09-03", "query", "B"))
        found = [(e.path, e.parsed()[2]) for e in ol.read_entries(self.tree)]
        self.assertEqual(found, [("log/2026-10.md", "C"), ("log/2026-09.md", "A"),
                                 ("log/.legacy-" + "d" * 64 + ".md", "A"), ("log/.legacy-" + "d" * 64 + ".md", "B")])

    def test_a_stray_is_read_first_and_only_beyond_the_detail_files(self):
        self.split(**{"2026-11": HEADER_11 + entry("2026-11-01", "init", "A")})
        pair = entry("2026-11-03", "query", "Twice")
        (self.tree / "log.md").write_text(entry("2026-11-01", "init", "A") + pair + pair)
        found = [(e.path, e.parsed()[2]) for e in ol.read_entries(self.tree)]
        self.assertEqual(found, [("log.md", "Twice"), ("log.md", "Twice"), ("log/2026-11.md", "A")])

    def test_a_symlinked_detail_file_is_refused_by_name(self):
        self.split()
        (self.root / "x.md").write_text(entry("2026-11-01", "init", "A"))
        (self.log_dir / "2026-11.md").symlink_to(self.root / "x.md")
        with self.assertRaises(ol.Refusal) as caught:
            ol.read_entries(self.tree)
        self.assertIn("2026-11.md", str(caught.exception))


class CommitStepTests(TreeCase):
    def git(self, *args, check=True):
        done = subprocess.run(["git", "-C", str(self.root), "-c", "user.name=T", "-c", "user.email=t@example.invalid",
                               *args], capture_output=True, text=True, check=check)
        if args[:1] == ("init",):
            # The commit step under test runs git with no identity of its own, so the fixture
            # repository carries one and no host identity is read.
            for key, value in (("user.name", "T"), ("user.email", "t@example.invalid")):
                subprocess.run(["git", "-C", str(self.root), "config", key, value], capture_output=True, check=True)
        return done

    def setUp(self):
        super().setUp()
        self.git("init", "-q")
        (self.tree / "log.md").write_text("# Operations log\n\n" + entry("2026-09-01", "init", "A"))
        self.git("add", "-A")
        self.git("commit", "-qm", "base")

    def status(self):
        return self.git("status", "--porcelain").stdout

    def test_the_listing_takes_log_paths_and_leaves_out_the_summary_temporaries_and_other_files(self):
        self.split(**{"2026-11": HEADER_11})
        (self.log_dir / ol.SUMMARY_NAME).write_text("# Operations log summary\n")
        (self.log_dir / ".write-journal-0123abcd").write_text("partial\n")
        (self.tree / "other.md").write_text("not a log file\n")
        found = ol.log_commit_paths(self.root, self.tree)
        # POSITIVE CONTROL: the dirty detail file and completion record are listed.
        self.assertEqual(found, {"commit_paths": ["docs/log/.split-complete.json", "docs/log/2026-11.md"],
                                 "restore_paths": []})

    def test_a_staged_deletion_of_log_md_commits_clean_only_with_the_restore(self):
        self.git("rm", "-q", "docs/log.md")
        self.split(**{"2026-09": entry("2026-09-01", "init", "A")})
        found = ol.log_commit_paths(self.root, self.tree)
        self.assertIn("docs/log.md", found["commit_paths"])
        self.assertEqual(found["restore_paths"], ["docs/log.md"])
        # POSITIVE CONTROL: without the restore, git add dies on the staged deletion.
        self.assertEqual(self.git("add", "--", *found["commit_paths"], check=False).returncode, 128)
        ol.commit_step(self.root, [], found["commit_paths"], found["restore_paths"], "split")
        self.assertEqual(self.status(), "")
        self.assertNotIn("docs/log.md", self.git("ls-tree", "-r", "--name-only", "HEAD").stdout.split())

    def test_a_staged_rename_commits_clean(self):
        target = "docs/log/.legacy-" + "e" * 64 + ".md"
        self.log_dir.mkdir()
        self.git("mv", "docs/log.md", target)
        found = ol.log_commit_paths(self.root, self.tree)
        self.assertEqual(found["commit_paths"], sorted(["docs/log.md", target]))
        ol.commit_step(self.root, [], found["commit_paths"], found["restore_paths"], "rename")
        self.assertEqual(self.status(), "")
        self.assertIn(target, self.git("ls-tree", "-r", "--name-only", "HEAD").stdout.split())

    def test_an_index_only_file_is_restored_and_not_committed(self):
        staged = self.log_dir / (".legacy-" + "f" * 64 + ".md")
        self.split(**{"2026-11": HEADER_11})
        staged.write_text("staged\n")
        self.git("add", "--", str(staged.relative_to(self.root)))
        staged.unlink()
        found = ol.log_commit_paths(self.root, self.tree)
        rel = staged.relative_to(self.root).as_posix()
        self.assertIn(rel, found["restore_paths"])
        self.assertNotIn(rel, found["commit_paths"])
        made = ol.commit_step(self.root, [], found["commit_paths"], found["restore_paths"], "commit")
        self.assertIsNotNone(made["commit"])
        self.assertEqual(self.status(), "")

    def test_a_restore_only_run_commits_nothing(self):
        staged = self.log_dir / (".stray-" + "0" * 64 + ".md")
        self.log_dir.mkdir()
        staged.write_text("staged\n")
        self.git("add", "--", str(staged.relative_to(self.root)))
        staged.unlink()
        head = self.git("rev-parse", "HEAD").stdout
        found = ol.log_commit_paths(self.root, self.tree)
        self.assertEqual(found, {"commit_paths": [], "restore_paths": [staged.relative_to(self.root).as_posix()]})
        made = ol.commit_step(self.root, [], found["commit_paths"], found["restore_paths"], "nothing")
        self.assertEqual(made["commit"], None)
        self.assertEqual(self.git("rev-parse", "HEAD").stdout, head)
        self.assertEqual(self.status(), "")


class CheckTests(TreeCase):
    def clean_tree(self):
        self.split(**{"2026-11": HEADER_11 + entry("2026-11-02", "query", "Asked") + entry("2026-11-01", "init", "Tree")})

    def findings(self, report, check):
        return [item for item in report["findings"] if item["check"] == check]

    def assert_red(self, check, severity="BROKEN"):
        code, report = self.check()
        self.assertEqual(code, 1, report)
        self.assertTrue(any(item["severity"] == severity for item in self.findings(report, check)), report)

    def test_a_clean_tree_is_clean_with_coverage(self):
        self.clean_tree()
        code, report = self.check()
        self.assertEqual((code, report["status"], report["findings"]), (0, "clean", []), report)
        self.assertEqual(report["coverage"], {"files": 1, "headings": 2})

    def test_chk_log_1_malformed_headings_dates_and_open_fences(self):
        seeds = {
            "malformed": entry("2026-11-03", "query", "x").replace(" | ", " - "),
            "calendar": entry("2026-13-04", "query", "Month thirteen"),
            "open fence": entry("2026-11-03", "query", "x") + "```\nopen\n",
        }
        for label, seed in seeds.items():
            with self.subTest(seed=label):
                self.clean_tree()
                path = self.log_dir / "2026-11.md"
                text = path.read_text()
                path.write_text(text + seed if label == "open fence" else text.replace(HEADER_11, HEADER_11 + seed))
                self.assert_red("CHK-LOG-1", "DRIFT")
        self.clean_tree()
        (self.log_dir / "2026-11.md").write_text(HEADER_11.rstrip("\n") + "\n```\nopen\n")
        self.assert_red("CHK-LOG-1", "DRIFT")

    def test_chk_log_2_header_drift_and_legitimate_out_of_order_entries(self):
        self.clean_tree()
        # Out-of-order heading dates are legitimate: a stray block, a backdated write, a later-dated release.
        (self.log_dir / "2026-11.md").write_text(
            HEADER_11 + entry("2026-10-02", "query", "Merged stray") + entry("2026-12-01", "release", "Published")
            + entry("2026-11-02", "query", "Asked") + entry("2026-09-30", "query", "Backdated") + entry("2026-11-01", "init", "Tree"))
        code, report = self.check()
        self.assertEqual((code, self.findings(report, "CHK-LOG-2")), (0, []), report)
        (self.log_dir / "2026-11.md").write_text("# Edited\n\n" + entry("2026-11-01", "init", "Tree"))
        self.assert_red("CHK-LOG-2", "DRIFT")

    def test_chk_log_3_a_log_without_an_init_entry(self):
        self.split(**{"2026-11": HEADER_11 + entry("2026-11-02", "query", "Asked")})
        self.assert_red("CHK-LOG-3")

    def test_chk_log_4_ops_outside_the_enum_and_the_section_6_blocks(self):
        self.clean_tree()
        path = self.log_dir / "2026-11.md"
        path.write_text(path.read_text() + entry("2026-11-03", "bogus", "Unknown op"))
        self.assert_red("CHK-LOG-4")
        self.clean_tree()
        agents = (self.tree / "AGENTS.md").read_text()
        (self.tree / "AGENTS.md").write_text(agents.replace(ol.HISTORICAL_LABEL, "**Removed label**"))
        code, report = self.check()
        self.assertEqual(code, 0, report)
        self.assertTrue(any(item["severity"] == "WARNING" for item in self.findings(report, "CHK-LOG-4")), report)
        (self.tree / "AGENTS.md").write_text(agents.replace(ol.HISTORICAL_LABEL, "x").replace(ol.CURRENT_LABEL, "y"))
        self.assert_red("CHK-LOG-4")
        code, result = self.append()
        self.assertEqual((code, result["code"]), (1, "no-op-enum"), result)

    def test_chk_log_6_names_kinds_and_leftover_temporaries(self):
        self.clean_tree()
        (self.log_dir / ".write-journal-00ff").write_text("partial\n")
        code, report = self.check()
        self.assertEqual(code, 0, report)
        self.assertEqual([item["severity"] for item in self.findings(report, "CHK-LOG-6")], ["WARNING"])
        (self.log_dir / "notes.txt").write_text("undefined\n")
        self.assert_red("CHK-LOG-6")
        (self.log_dir / "notes.txt").unlink()
        (self.log_dir / "2026-10.md").symlink_to(self.log_dir / "2026-11.md")
        self.assert_red("CHK-LOG-6")
        for path in self.log_dir.iterdir():
            path.unlink()
        self.log_dir.rmdir()
        self.log_dir.write_text("a file\n")
        self.assert_red("CHK-LOG-6")


class EndToEndTests(TreeCase):
    def test_write_journal_log_only_writes_the_supplied_month_and_the_check_is_clean(self):
        code, result = self.append(op="init", subject="Initialised the tree", date="2026-10-01", today="2026-10-01")
        self.assertEqual(code, 0, result)
        done = subprocess.run([sys.executable, str(WRITER), "--repo-root", str(self.root), "--mode", "log-only",
                               "--at", "2026-10-15T09:00:00-06:00", "--category", "learning", "--subject",
                               "Recorded a run", "--body-stdin", "--log-op", "promptbook", "--today", "2026-10-15"],
                              input="One line.\n", capture_output=True, text=True)
        payload = json.loads(done.stdout)
        self.assertEqual((done.returncode, payload["status"], payload["written"]), (0, "complete", ["log/2026-10.md"]), done.stdout)
        self.assertFalse((self.tree / "log.md").exists())
        self.assertIn("## [2026-10-15] promptbook | Recorded a run", (self.log_dir / "2026-10.md").read_text())
        code, report = self.check()
        self.assertEqual((code, report["status"]), (0, "clean"), report)


if __name__ == "__main__":
    unittest.main()
