"""The operations log repair: the first split, the stray merge, staging, completion and CHK-LOG-5.

Every fixture builds a temporary tree; nothing here reads or writes this repository's own tree.
"""

from __future__ import annotations

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_operation_log import CLI, HEADER_11, TODAY, TreeCase, entry, ol  # noqa: E402

PREAMBLE = "# Operations log\n\n_Append-only. Newest first._\n\n"
PAIR = entry("2026-10-03", "query", "Twice")
LAST = "## [2026-08-01] init | Tree\n\nNo trailing newline"
# Months 11 and 10 interleave (non-contiguous); 09 and 08 are contiguous; PAIR is an identical pair.
LEGACY = (PREAMBLE + entry("2026-11-02", "query", "Nov two") + PAIR + entry("2026-11-01", "adr", "Nov one")
          + PAIR + entry("2026-09-06", "query", "Sep b") + entry("2026-09-05", "query", "Sep a") + LAST)
EXPECTED = {
    "2026-11.md": ol.detail_header("2026-11") + entry("2026-11-02", "query", "Nov two") + entry("2026-11-01", "adr", "Nov one"),
    "2026-10.md": ol.detail_header("2026-10") + PAIR + PAIR,
    "2026-09.md": ol.detail_header("2026-09") + entry("2026-09-06", "query", "Sep b") + entry("2026-09-05", "query", "Sep a"),
    "2026-08.md": ol.detail_header("2026-08") + LAST + "\n",
}


def sha(text: str | bytes) -> str:
    return hashlib.sha256(text.encode("utf-8") if isinstance(text, str) else text).hexdigest()


def kept_name(text: str) -> str:
    return f".kept-{sha(text)}.txt"


class Crash(Exception):
    """A failure injected after a repair step."""


def crash_after(step: str, nth: int = 1):
    seen = Counter()

    def hook(name: str) -> None:
        if name == step:
            seen[name] += 1
            if seen[name] == nth:
                raise Crash(f"after {step}")
    return patch.object(ol, "_after_step", hook)


class RepairCase(TreeCase):
    def reset(self) -> None:
        if self.log_dir.is_dir():
            shutil.rmtree(self.log_dir)
        if (self.tree / "log.md").exists():
            (self.tree / "log.md").unlink()

    def run_repair(self, today: str = TODAY) -> tuple[ol.Plan, list[str]]:
        plan = ol.plan_repair(self.tree, today)
        return plan, ol.repair(self.tree, plan, self.root)

    def entry_texts(self) -> Counter:
        return Counter(item.text for item in ol.read_entries(self.tree))

    def staged(self, kind: str, text: str) -> str:
        return f".{kind}-{sha(text)}.md"


class FirstSplitTests(RepairCase):
    def test_the_proof_holds_for_preamble_months_pair_and_no_trailing_newline(self):
        (self.tree / "log.md").write_text(LEGACY)
        plan, changed = self.run_repair()
        split = plan.proof["split"]
        self.assertEqual(split["legacy_sha256"], sha(LEGACY))
        self.assertTrue(split["reconstruction_equal"])
        self.assertEqual(split["entries_per_month"], {"2026-08": 1, "2026-09": 2, "2026-10": 2, "2026-11": 2})
        self.assertEqual(split["outside_bytes"], len(PREAMBLE))
        self.assertFalse((self.tree / "log.md").exists())
        for name, text in EXPECTED.items():
            self.assertEqual((self.log_dir / name).read_text(), text, name)
        self.assertEqual((self.log_dir / kept_name(PREAMBLE)).read_text(), PREAMBLE)
        record = json.loads((self.log_dir / ol.COMPLETION_NAME).read_text())
        self.assertEqual((record["legacy_sha256"], record["entries_per_month"]), (sha(LEGACY), split["entries_per_month"]))
        left = sorted(p.name for p in self.log_dir.iterdir())
        self.assertEqual(left, sorted([*EXPECTED, kept_name(PREAMBLE), ol.COMPLETION_NAME]))
        self.assertIn("log.md", changed)
        # Reconstruction: the placed entries are the legacy entries, the pair twice.
        self.assertEqual(self.entry_texts(), Counter(ol.cut(LEGACY).entries))

    def test_a_legacy_file_without_a_preamble_keeps_no_kept_file(self):
        legacy = entry("2026-11-02", "query", "A") + entry("2026-11-01", "init", "B")
        (self.tree / "log.md").write_text(legacy)
        self.run_repair()
        self.assertEqual((self.log_dir / "2026-11.md").read_text(), HEADER_11 + legacy)
        self.assertEqual([p.name for p in self.log_dir.iterdir() if p.name.startswith(".kept-")], [])
        # POSITIVE CONTROL: a source with outside bytes leaves its kept file.
        (self.tree / "log.md").write_text(PREAMBLE + entry("2026-11-03", "query", "C"))
        self.run_repair()
        self.assertEqual([p.name for p in self.log_dir.iterdir() if p.name.startswith(".kept-")], [kept_name(PREAMBLE)])

    def test_a_second_run_changes_nothing(self):
        (self.tree / "log.md").write_text(LEGACY)
        self.run_repair()
        before = self.snapshot()
        plan, changed = self.run_repair()
        self.assertEqual((plan.actions, changed), ((), []))
        self.assertEqual(self.snapshot(), before)

    def test_a_failure_after_each_step_resumes_with_every_entry_placed_once(self):
        (self.tree / "log.md").write_text(LEGACY)
        self.run_repair()
        final = self.snapshot()
        for step, nth in (("7b", 1), ("7e", 1), ("7f", 1), ("7f", 2), ("7g", 1), ("7h", 1), ("7i", 1)):
            with self.subTest(step=step, nth=nth):
                self.reset()
                (self.tree / "log.md").write_text(LEGACY)
                with crash_after(step, nth), self.assertRaises(Crash):
                    self.run_repair()
                # Readers count each entry once in the interrupted state, the pair twice.
                self.assertEqual(self.entry_texts(), Counter(ol.cut(LEGACY).entries))
                self.run_repair()
                self.assertEqual(self.snapshot(), final)

    def test_a_tree_with_no_legacy_file_records_completion_and_moves_nothing(self):
        self.log_dir.mkdir()
        (self.log_dir / "2026-11.md").write_text(HEADER_11 + entry("2026-11-01", "init", "A"))
        before = (self.log_dir / "2026-11.md").read_bytes()
        plan, changed = self.run_repair()
        self.assertEqual((plan.actions, changed), (("record-completion",), ["log/.split-complete.json"]))
        self.assertEqual((self.log_dir / "2026-11.md").read_bytes(), before)
        record = json.loads((self.log_dir / ol.COMPLETION_NAME).read_text())
        self.assertIsNone(record["legacy_sha256"])

    def test_a_log_md_beside_a_staged_legacy_file_merges_after_completion_into_the_local_month(self):
        (self.tree / "log.md").write_text(LEGACY)
        with crash_after("7b"), self.assertRaises(Crash):
            self.run_repair(today="2026-12-05")
        late = entry("2026-12-04", "query", "Written by an older plugin")
        (self.tree / "log.md").write_text(PREAMBLE + late)
        plan, _ = self.run_repair(today="2026-12-05")
        # The split resumes from its staged file first; the stray merges after completion.
        self.assertEqual([action.split(":")[0] for action in plan.actions], ["split", "merge"])
        for name, text in EXPECTED.items():
            self.assertEqual((self.log_dir / name).read_text(), text, name)
        self.assertEqual((self.log_dir / "2026-12.md").read_text(), ol.detail_header("2026-12") + late)
        self.assertTrue((self.log_dir / ol.COMPLETION_NAME).is_file())
        self.assertFalse((self.tree / "log.md").exists())
        # One kept file for the preamble both files carry.
        self.assertEqual(len([p for p in self.log_dir.iterdir() if p.name.startswith(".kept-")]), 1)

    def test_entries_the_detail_files_already_hold_are_placed_only_beyond_them(self):
        self.log_dir.mkdir()
        (self.log_dir / "2026-10.md").write_text(ol.detail_header("2026-10") + PAIR)
        (self.tree / "log.md").write_text(LEGACY)
        self.run_repair()
        self.assertEqual((self.log_dir / "2026-10.md").read_text(), ol.detail_header("2026-10") + PAIR + PAIR)
        self.assertEqual(self.entry_texts()[PAIR], 2)

    def test_a_heading_or_fence_refusal_leaves_log_md_unrenamed_and_byte_identical(self):
        bad = {
            "op outside the enum": entry("2026-11-02", "bogus", "x"),
            "month thirteen": entry("2026-13-02", "query", "x"),
            "day zero": entry("2026-11-00", "query", "x"),
            "open fence": entry("2026-11-02", "query", "x") + "```\nnever closed\n",
        }
        for label, seed in bad.items():
            with self.subTest(seed=label):
                self.reset()
                text = PREAMBLE + entry("2026-11-03", "query", "Fine") + seed
                (self.tree / "log.md").write_text(text)
                before = self.snapshot()
                with self.assertRaises(ol.Refusal) as caught:
                    self.run_repair()
                self.assertIn(caught.exception.code, ("malformed-heading", "open-fence"))
                self.assertEqual(self.snapshot(), before)
                self.assertEqual((self.tree / "log.md").read_text(), text)
        # POSITIVE CONTROL: the same file without the seed splits.
        self.reset()
        (self.tree / "log.md").write_text(PREAMBLE + entry("2026-11-03", "query", "Fine"))
        self.run_repair()
        self.assertFalse((self.tree / "log.md").exists())


class StagingTests(RepairCase):
    def test_staging_never_replaces_an_existing_staged_name(self):
        self.log_dir.mkdir()
        disk = ol._DiskFS(self.tree, self.root)
        name = self.staged("stray", "other bytes\n")
        (self.log_dir / name).write_text("other bytes\n")
        (self.tree / "log.md").write_text(LEGACY)
        with self.assertRaises(ol.Refusal) as caught:
            disk.stage(name)
        self.assertEqual(caught.exception.code, "changed")
        self.assertEqual(((self.log_dir / name).read_text(), (self.tree / "log.md").read_text()), ("other bytes\n", LEGACY))
        # An existing name that holds log.md's bytes: log.md is unlinked, the staged file stays.
        same = self.staged("legacy", LEGACY)
        (self.log_dir / same).write_text(LEGACY)
        disk.stage(same)
        self.assertFalse((self.tree / "log.md").exists())
        self.assertEqual((self.log_dir / same).read_text(), LEGACY)
        # POSITIVE CONTROL: an absent name is a rename.
        (self.tree / "log.md").write_text(PREAMBLE)
        disk.stage(self.staged("stray", PREAMBLE))
        self.assertEqual((self.log_dir / self.staged("stray", PREAMBLE)).read_text(), PREAMBLE)

    def test_a_log_md_replaced_between_the_read_and_the_rename_is_staged_under_its_own_digest(self):
        (self.tree / "log.md").write_text(LEGACY)
        replaced = LEGACY.replace("Nov two", "Nov two, rewritten")
        original = ol._DiskFS.stage

        def older_writer_then_stage(disk, name):
            (self.tree / "log.md").write_text(replaced)
            original(disk, name)

        plan = ol.plan_repair(self.tree, TODAY)
        with patch.object(ol._DiskFS, "stage", older_writer_then_stage):
            ol.repair(self.tree, plan, self.root)
        record = json.loads((self.log_dir / ol.COMPLETION_NAME).read_text())
        self.assertEqual(record["legacy_sha256"], sha(replaced))
        self.assertIn("Nov two, rewritten", (self.log_dir / "2026-11.md").read_text())
        self.assertEqual(self.entry_texts(), Counter(ol.cut(replaced).entries))

    def test_misnamed_and_duplicated_staged_files_normalize_with_no_double_count(self):
        for label in ("misnamed", "two names"):
            with self.subTest(fixture=label):
                self.reset()
                self.log_dir.mkdir()
                # A crash after the rename and before the hash: the name is not the bytes' digest.
                (self.log_dir / (".legacy-" + "0" * 64 + ".md")).write_text(LEGACY)
                if label == "two names":  # a crash between the link and the unlink
                    (self.log_dir / self.staged("legacy", LEGACY)).write_text(LEGACY)
                self.assertEqual(self.entry_texts(), Counter(ol.cut(LEGACY).entries))
                self.run_repair()
                for name, text in EXPECTED.items():
                    self.assertEqual((self.log_dir / name).read_text(), text)
                self.assertEqual(sorted(p.name for p in self.log_dir.iterdir() if p.name.startswith((".legacy-", ".split-"))
                                        and p.name != ol.COMPLETION_NAME), [])

    def test_two_staged_strays_holding_one_entry_place_it_once_in_read_order(self):
        self.split(**{"2026-11": HEADER_11 + entry("2026-11-01", "init", "Tree")})
        shared = entry("2026-11-03", "query", "Shared")
        older = entry("2026-11-02", "query", "A1") + shared
        newer = entry("2026-11-04", "query", "B1") + shared
        for text, mtime in ((older, 1_000_000), (newer, 2_000_000)):
            path = self.log_dir / self.staged("stray", text)
            path.write_text(text)
            os.utime(path, (mtime, mtime))
        before = [item.text for item in ol.read_entries(self.tree)]
        with crash_after("8f", 1), self.assertRaises(Crash):
            self.run_repair()
        during = [item.text for item in ol.read_entries(self.tree)]
        self.run_repair()
        after = [item.text for item in ol.read_entries(self.tree)]
        final = ol.cut((self.log_dir / "2026-11.md").read_text()).entries
        self.assertEqual(list(final), [entry("2026-11-04", "query", "B1"), entry("2026-11-02", "query", "A1"),
                                       shared, entry("2026-11-01", "init", "Tree")])
        self.assertEqual((before, during, after), (list(final), list(final), list(final)))


class StrayMergeTests(RepairCase):
    def setUp(self):
        super().setUp()
        self.settled = ol.detail_header("2026-10") + entry("2026-10-05", "query", "Held") + entry("2026-10-01", "init", "Tree")
        self.split(**{"2026-10": self.settled, "2026-11": HEADER_11 + entry("2026-11-01", "query", "Current")})
        self.pair = entry("2026-11-07", "query", "Pair")
        self.stray = PREAMBLE + entry("2026-11-08", "query", "New") + entry("2026-10-05", "query", "Held") + self.pair + self.pair
        (self.tree / "log.md").write_text(self.stray)
        self.final_11 = HEADER_11 + entry("2026-11-08", "query", "New") + self.pair + self.pair + entry("2026-11-01", "query", "Current")

    def test_entries_land_as_one_block_and_skipped_entries_are_reported(self):
        plan, changed = self.run_repair()
        self.assertEqual((self.log_dir / "2026-11.md").read_text(), self.final_11)
        self.assertEqual((self.log_dir / "2026-10.md").read_text(), self.settled)
        merge = plan.proof["merges"][0]
        self.assertEqual((merge["moved"], merge["skipped"], merge["into"]),
                         (3, [{"position": 1, "file": "log/2026-10.md"}], "log/2026-11.md"))
        self.assertEqual((self.log_dir / kept_name(PREAMBLE)).read_text(), PREAMBLE)
        self.assertFalse((self.tree / "log.md").exists())
        self.assertEqual([p.name for p in self.log_dir.iterdir() if p.name.startswith(".stray-")], [])
        self.assertIn("log.md", changed)

    def test_two_strays_with_the_same_preamble_leave_one_kept_file(self):
        self.run_repair()
        (self.tree / "log.md").write_text(PREAMBLE + entry("2026-11-09", "query", "Later"))
        self.run_repair()
        self.assertEqual([p.name for p in self.log_dir.iterdir() if p.name.startswith(".kept-")], [kept_name(PREAMBLE)])
        self.assertTrue((self.log_dir / "2026-11.md").read_text().startswith(HEADER_11 + entry("2026-11-09", "query", "Later")))

    def test_a_failure_after_each_step_resumes_with_no_duplicate(self):
        original = self.snapshot()
        self.run_repair()
        final = self.snapshot()
        for step in ("8a", "8d", "8e", "8f"):
            with self.subTest(step=step):
                for path in list(self.log_dir.iterdir()):
                    path.unlink()
                for rel, raw in original.items():
                    if isinstance(raw, bytes) and rel.startswith("log"):
                        (self.tree / rel).write_bytes(raw)
                with crash_after(step), self.assertRaises(Crash):
                    self.run_repair()
                self.assertEqual(sum(self.entry_texts().values()), len(ol.cut(self.final_11).entries) + 2)
                self.run_repair()
                self.assertEqual(self.snapshot(), final)

    def test_a_stray_without_a_trailing_newline_merges_above_and_a_rerun_moves_nothing(self):
        (self.tree / "log.md").write_text("## [2026-11-09] query | Unterminated\n\nNo newline")
        with crash_after("8e"), self.assertRaises(Crash):
            self.run_repair()
        self.assertEqual(self.entry_texts()["## [2026-11-09] query | Unterminated\n\nNo newline\n"], 1)
        self.run_repair()
        text = (self.log_dir / "2026-11.md").read_text()
        self.assertEqual(text, HEADER_11 + "## [2026-11-09] query | Unterminated\n\nNo newline\n"
                         + entry("2026-11-01", "query", "Current"))

    def test_a_malformed_stray_refuses_the_whole_repair(self):
        (self.tree / "log.md").write_text(entry("2026-11-09", "nonsense", "Bad"))
        before = self.snapshot()
        with self.assertRaises(ol.Refusal) as caught:
            self.run_repair()
        self.assertEqual(caught.exception.code, "malformed-heading")
        self.assertEqual(self.snapshot(), before)


class CompletionTests(RepairCase):
    def test_a_transaction_file_beside_the_completion_record_is_a_leftover_the_repair_removes(self):
        (self.tree / "log.md").write_text(LEGACY)
        with crash_after("7h"), self.assertRaises(Crash):
            self.run_repair()
        leftover = self.log_dir / f".split-{sha(LEGACY)}.json"
        self.assertTrue(leftover.is_file() and (self.log_dir / ol.COMPLETION_NAME).is_file())
        plan, changed = self.run_repair()
        self.assertEqual(changed, [f"log/{leftover.name}"])
        self.assertFalse(leftover.exists())

    def test_conflicts_refuse_with_nothing_changed(self):
        other = PREAMBLE + entry("2026-11-02", "query", "Other")
        fixtures = {
            "staged legacy beside completion": lambda: (
                self.split(), (self.log_dir / self.staged("legacy", LEGACY)).write_text(LEGACY)),
            "staged legacy equals staged stray": lambda: (
                self.log_dir.mkdir(), (self.log_dir / self.staged("legacy", LEGACY)).write_text(LEGACY),
                (self.log_dir / self.staged("stray", LEGACY)).write_text(LEGACY)),
            "distinct staged legacy files": lambda: (
                self.log_dir.mkdir(), (self.log_dir / self.staged("legacy", LEGACY)).write_text(LEGACY),
                (self.log_dir / self.staged("legacy", other)).write_text(other)),
        }
        for label, build in fixtures.items():
            with self.subTest(fixture=label):
                self.reset()
                build()
                before = self.snapshot()
                with self.assertRaises(ol.Refusal) as caught:
                    self.run_repair()
                self.assertEqual(caught.exception.code, "legacy-conflict")
                self.assertEqual(self.snapshot(), before)
                code, report = self.check()
                self.assertTrue(any(f["check"] == "CHK-LOG-5" and f["severity"] == "BROKEN" for f in report["findings"]), report)

    def test_a_target_changed_by_hand_mid_split_refuses_migration_conflict(self):
        (self.tree / "log.md").write_text(LEGACY)
        with crash_after("7e"), self.assertRaises(Crash):
            self.run_repair()
        (self.log_dir / "2026-11.md").write_text(HEADER_11 + entry("2026-11-05", "query", "Hand edit"))
        before = self.snapshot()
        with self.assertRaises(ol.Refusal) as caught:
            self.run_repair()
        self.assertEqual(caught.exception.code, "migration-conflict")
        self.assertEqual(self.snapshot(), before)


class WriterRepairTests(RepairCase):
    def test_append_splits_a_legacy_log_md_before_the_write(self):
        (self.tree / "log.md").write_text(LEGACY)
        code, result = self.append(date=TODAY)
        self.assertEqual((code, result["status"], result["file"]), (0, "written", "docs/log/2026-11.md"), result)
        self.assertFalse((self.tree / "log.md").exists())
        self.assertTrue((self.log_dir / "2026-11.md").read_text().startswith(HEADER_11 + entry(TODAY, "query", "Asked a question", "An answer.")))
        self.assertEqual((self.log_dir / "2026-10.md").read_text(), EXPECTED["2026-10.md"])
        self.assertIn("docs/log.md", result["changed_paths"])
        self.assertIn("docs/log/.split-complete.json", result["changed_paths"])

    def test_an_invalid_request_on_an_unsplit_tree_or_beside_a_stray_changes_nothing(self):
        fixtures = {
            "unsplit": lambda: (self.tree / "log.md").write_text(LEGACY),
            "stray": lambda: (self.split(**{"2026-11": HEADER_11 + entry("2026-11-01", "init", "T")}),
                              (self.tree / "log.md").write_text(PREAMBLE + entry("2026-11-02", "query", "S"))),
        }
        for label, build in fixtures.items():
            with self.subTest(fixture=label):
                self.reset()
                build()
                before = self.snapshot()
                for kwargs in ({"op": "bogus"}, {"body": "Line.\n## [2026-11-02] query | forged\n"}, {"date": "2026-13-01"}):
                    code, result = self.append(**kwargs)
                    self.assertEqual((code, result["status"]), (1, "refused"), result)
                    self.assertEqual(self.snapshot(), before)
                # POSITIVE CONTROL: a valid request repairs and writes.
                code, result = self.append()
                self.assertEqual((code, result["status"]), (0, "written"), result)
                self.assertFalse((self.tree / "log.md").exists())

    def test_a_malformed_stray_heading_refuses_append_until_the_heading_is_fixed(self):
        self.split(**{"2026-11": HEADER_11 + entry("2026-11-01", "init", "T")})
        (self.tree / "log.md").write_text(entry("2026-11-02", "nonsense", "Bad"))
        before = self.snapshot()
        code, result = self.append()
        self.assertEqual((code, result["code"]), (1, "malformed-heading"), result)
        self.assertEqual(self.snapshot(), before)
        (self.tree / "log.md").write_text(entry("2026-11-02", "query", "Fixed"))
        code, result = self.append()
        self.assertEqual((code, result["status"]), (0, "written"), result)
        code, result = self.append()
        self.assertEqual((code, result["status"]), (0, "recorded"), result)


class RepairCommandTests(RepairCase):
    def repair_cli(self, *args, env=None):
        done = subprocess.run([sys.executable, str(CLI), "repair", "--repo-root", str(self.root), *args],
                              capture_output=True, text=True, env=env if env is not None else dict(os.environ))
        if not done.stdout.strip():
            self.fail(f"operation-log repair printed no result (exit {done.returncode}): {done.stderr}")
        return done.returncode, json.loads(done.stdout)

    def git(self, *args, check=True):
        done = subprocess.run(["git", "-C", str(self.root), "-c", "user.name=T", "-c", "user.email=t@example.invalid",
                               *args], capture_output=True, text=True, check=check)
        if args[:1] == ("init",):
            # The commit step under test runs git with no identity of its own, so the fixture
            # repository carries one and no host identity is read.
            for key, value in (("user.name", "T"), ("user.email", "t@example.invalid")):
                subprocess.run(["git", "-C", str(self.root), "config", key, value], capture_output=True, check=True)
        return done

    def test_dry_run_prints_the_proof_and_writes_nothing(self):
        (self.tree / "log.md").write_text(LEGACY)
        before = self.snapshot()
        env = {key: value for key, value in os.environ.items() if key != ol.TEST_ENV}
        code, result = self.repair_cli("--dry-run", "--today", TODAY, env=env)
        self.assertEqual((code, result["status"]), (0, "planned"), result)
        self.assertEqual(self.snapshot(), before)
        proof = result["proof"]["split"]
        self.assertEqual((proof["legacy_sha256"], proof["reconstruction_equal"]), (sha(LEGACY), True))
        self.assertEqual(sum(proof["entries_per_month"].values()), len(ol.cut(LEGACY).entries))
        self.assertIn("docs/log.md", result["planned_paths"])
        # --today in the write mode needs the test variable.
        code, result = self.repair_cli("--today", TODAY, env=env)
        self.assertEqual((code, result["code"]), (1, "today-not-allowed"), result)
        self.assertEqual(self.snapshot(), before)

    def test_a_repair_commits_clean_and_a_second_run_reports_no_change(self):
        self.git("init", "-q")
        (self.tree / "log.md").write_text(LEGACY)
        self.git("add", "-A")
        self.git("commit", "-qm", "base")
        code, result = self.repair_cli("--today", TODAY)
        self.assertEqual((code, result["status"]), (0, "repaired"), result)
        self.assertIn("docs/log.md", result["commit_paths"])
        self.assertIn("docs/log/2026-11.md", result["commit_paths"])
        ol.commit_step(self.root, [], result["commit_paths"], result["restore_paths"], "split")
        self.assertEqual(self.git("status", "--porcelain").stdout, "")
        head = self.git("ls-tree", "-r", "--name-only", "HEAD").stdout.split()
        self.assertNotIn("docs/log.md", head)
        self.assertIn("docs/log/.split-complete.json", head)
        code, again = self.repair_cli("--today", TODAY)
        self.assertEqual((code, again["changed_paths"], again["commit_paths"]), (0, [], []), again)

    def test_an_interrupted_or_refused_repair_is_committed_clean_by_the_commit_step(self):
        self.git("init", "-q")
        (self.tree / "log.md").write_text(LEGACY)
        self.git("add", "-A")
        self.git("commit", "-qm", "base")
        with crash_after("7f"), self.assertRaises(Crash):
            self.run_repair()
        found = ol.log_commit_paths(self.root, self.tree)
        self.assertIn("docs/log.md", found["commit_paths"])
        self.assertIn(f"docs/log/{self.staged('legacy', LEGACY)}", found["commit_paths"])
        ol.commit_step(self.root, [], found["commit_paths"], found["restore_paths"], "interrupted")
        self.assertEqual(self.git("status", "--porcelain").stdout, "")
        # A repair refused after its staging rename: an older writer left a malformed heading.
        self.reset()
        self.git("add", "-A")
        self.git("commit", "-qm", "reset", check=False)
        (self.tree / "log.md").write_text(LEGACY)
        self.git("add", "-A")
        self.git("commit", "-qm", "legacy again")
        original = ol._DiskFS.stage

        def malformed_then_stage(disk, name):
            (self.tree / "log.md").write_text(entry("2026-11-02", "nonsense", "Bad"))
            original(disk, name)

        plan = ol.plan_repair(self.tree, TODAY)
        with patch.object(ol._DiskFS, "stage", malformed_then_stage), self.assertRaises(ol.Refusal) as caught:
            ol.repair(self.tree, plan, self.root)
        self.assertEqual(caught.exception.code, "malformed-heading")
        self.assertIn("log.md", caught.exception.changed)
        found = ol.log_commit_paths(self.root, self.tree)
        self.assertTrue(found["commit_paths"])
        ol.commit_step(self.root, [], found["commit_paths"], found["restore_paths"], "refused")
        self.assertEqual(self.git("status", "--porcelain").stdout, "")


class CheckLog5Tests(RepairCase):
    def findings(self):
        code, report = self.check()
        return code, [(f["severity"], f["path"]) for f in report["findings"] if f["check"] == "CHK-LOG-5"]

    def test_each_repair_source_is_drift_and_a_repaired_tree_is_clean(self):
        fixtures = {
            "legacy log.md": lambda: (self.tree / "log.md").write_text(LEGACY),
            "stray log.md": lambda: (self.split(**{"2026-11": HEADER_11 + entry("2026-11-01", "init", "T")}),
                                     (self.tree / "log.md").write_text(PREAMBLE + entry("2026-11-02", "query", "S"))),
            "staged legacy": lambda: (self.log_dir.mkdir(), (self.log_dir / self.staged("legacy", LEGACY)).write_text(LEGACY)),
            "staged stray": lambda: (self.split(**{"2026-11": HEADER_11 + entry("2026-11-01", "init", "T")}),
                                     (self.log_dir / self.staged("stray", PREAMBLE)).write_text(PREAMBLE)),
            "leftover transaction": lambda: (self.split(**{"2026-11": HEADER_11 + entry("2026-11-01", "init", "T")}),
                                             (self.log_dir / (".split-" + "c" * 64 + ".json")).write_text("{}\n")),
            "no completion record": lambda: (self.log_dir.mkdir(), (self.log_dir / "2026-11.md").write_text(
                HEADER_11 + entry("2026-11-01", "init", "T"))),
        }
        for label, build in fixtures.items():
            with self.subTest(fixture=label):
                self.reset()
                build()
                code, found = self.findings()
                self.assertEqual(code, 1, found)
                self.assertTrue(found and all(severity == "DRIFT" for severity, _ in found), found)
                # The auto-fix is the repair; the tree is then clean.
                self.run_repair()
                code, found = self.findings()
                self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()
