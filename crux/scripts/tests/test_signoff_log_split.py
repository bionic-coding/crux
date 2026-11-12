"""`signoff-survey.py` writes its `observation` op to the monthly operations log in the phased order.

The sign-off validates the entry, plans the repair of the log (the preflight) and repairs before its
first cell writes; the cells run; `insert_entry` places the entry at cell 12. These tests cover the
order's refusals (every cell stays unwritten), the commit-set report and the reruns that complete an
operation. Every fixture builds a temporary tree.
"""
from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
from unittest import mock

import test_survey_signoff as tss
import operation_log as OL

STRAY = "## [2026-08-01] audit | an entry an older plugin left in log.md\n\nBody kept as written.\n\n"
OPEN_FENCE = "```\nan open fence\n"


class _SurveyLogCase(tss._SignoffCase):
    def setUp(self):
        super().setUp()
        self.month = OL.local_date()[:7]
        self.detail = self.tree / "log" / f"{self.month}.md"

    def split_tree(self):
        """A completed first split: the legacy `log.md` of the fixture goes, the completion record stays."""
        (self.tree / "log.md").unlink()
        (self.tree / "log").mkdir()
        (self.tree / "log" / ".split-complete.json").write_bytes(OL.completion_bytes(None, {}))

    def advance_to(self, ctx, bid, state):
        for _ in range(20):
            if self._state(bid) == state:
                return
            tss.SO.advance(ctx)
        self.fail(f"never reached {state}")

    def refused_findings(self, bid):
        proc = self._run("--batch", bid)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        return json.dumps(self._payload(proc))


class PreflightRefusalTests(_SurveyLogCase):
    """A refusal in the preflight leaves every cell, and the log itself, unwritten."""

    def test_a_malformed_stray_heading_refuses_with_every_cell_unwritten(self):
        bid = self._prepare()
        self.split_tree()
        (self.tree / "log.md").write_text("## [not-a-date] audit | a malformed heading\n\nBody.\n\n", encoding="utf-8")
        before = tss._snapshot(self.root)
        self.assertIn("operations log refuses", self.refused_findings(bid))
        self.assertEqual(tss._snapshot(self.root), before)
        self.assertEqual(self._state(bid), "S0")
        # Positive control: with a well-formed stray the first cell writes and the repair merges it.
        (self.tree / "log.md").write_text(STRAY, encoding="utf-8")
        ctx = self._ctx(bid)
        tss.SO.advance(ctx)
        self.assertEqual(self._state(bid), "S1")
        self.assertFalse((self.tree / "log.md").exists(), "the repair merged the stray before the cell wrote")
        self.assertIn(STRAY, self.detail.read_text(encoding="utf-8"))

    def test_an_open_fence_stray_refuses_with_every_cell_unwritten(self):
        bid = self._prepare()
        self.split_tree()
        (self.tree / "log.md").write_text("## [2026-08-01] audit | opens a fence\n\n" + OPEN_FENCE, encoding="utf-8")
        before = tss._snapshot(self.root)
        self.assertIn("operations log refuses", self.refused_findings(bid))
        self.assertEqual(tss._snapshot(self.root), before)
        (self.tree / "log.md").write_text(
            "## [2026-08-01] audit | closes its fence\n\n" + OPEN_FENCE + "```\n\n", encoding="utf-8")
        ctx = self._ctx(bid)
        tss.SO.advance(ctx)
        self.assertEqual(self._state(bid), "S1")

    def test_a_destination_whose_outside_bytes_leave_a_fence_open_refuses_before_any_cell(self):
        bid = self._prepare()
        self.split_tree()
        self.detail.write_text(f"# Operations log: {self.month}\n\n" + OPEN_FENCE + "\n", encoding="utf-8")
        before = tss._snapshot(self.root)
        self.assertIn("operations log refuses", self.refused_findings(bid))
        self.assertEqual(tss._snapshot(self.root), before)
        # Positive control: a closed fence in the same place lets the first cell write.
        self.detail.write_text(f"# Operations log: {self.month}\n\n" + OPEN_FENCE + "```\n\n", encoding="utf-8")
        tss.SO.advance(self._ctx(bid))
        self.assertEqual(self._state(bid), "S1")

    def test_a_digest_refusal_comes_before_the_repair_that_splits_a_legacy_log(self):
        bid = self._prepare()
        tss.SO.advance(self._ctx(bid))                       # -> S1: binds the sheet, and splits the legacy log
        self.assertFalse((self.tree / "log.md").exists(), "positive control: a passing step splits log.md")
        (self.tree / "log.md").write_text("# Log\n", encoding="utf-8")   # a legacy file again, for the repair to find
        paths = tss.SS.receipt_paths(self.obs, bid)
        sheet = tss.SS.read_sheet(paths["sheet"])
        sheet["rows"][0]["verdict"] = "reject"
        tss.SS.write_sheet(paths["sheet"], sheet, contained_under=self.tree)
        before = tss._snapshot(self.root)
        self.assertIn("digest", self.refused_findings(bid))
        self.assertEqual(tss._snapshot(self.root), before, "the repair did not run: log.md is still in place")
        self.assertTrue((self.tree / "log.md").exists())


class LogCellTests(_SurveyLogCase):
    def reach_s6(self, bid):
        ctx = self._ctx(bid)
        self.advance_to(ctx, bid, "S6")
        return ctx

    def test_the_log_cell_writes_the_op_into_the_local_months_file_and_reports_the_commit_paths(self):
        bid = self._prepare()
        ctx = self.reach_s6(bid)
        tss.SO.advance(ctx)                                  # cell 12
        text = self.detail.read_text(encoding="utf-8")
        self.assertEqual(text.count(f"observation | survey batch {bid}"), 1)
        self.assertIn("OBS-0001", text)
        report = tss.SO.log_report(ctx)
        self.assertIn(f"bionic/log/{self.month}.md", report["changed_paths"])
        self.assertIn("bionic/log.md", report["changed_paths"], "the legacy fixture log was split first")
        self.assertEqual(report["left_strays"], [])
        self.assertTrue({"commit_paths", "restore_paths"} <= set(report))

    def test_a_stray_created_after_the_repair_is_left_and_named_not_merged(self):
        bid = self._prepare()
        self.split_tree()
        ctx = self.reach_s6(bid)
        real = OL.insert_entry

        def with_a_stray(tree, entry, today, root=None):
            (Path(tree) / "log.md").write_text(STRAY, encoding="utf-8")  # an older writer, after the repair phase
            return real(tree, entry, today, root)

        with mock.patch.object(OL, "insert_entry", with_a_stray):
            tss.SO.advance(ctx)
        self.assertEqual((self.tree / "log.md").read_text(encoding="utf-8"), STRAY, "left in place")
        self.assertEqual(tss.SO.log_report(ctx)["left_strays"], ["bionic/log.md"])
        text = self.detail.read_text(encoding="utf-8")
        self.assertIn(f"observation | survey batch {bid}", text, "the op was written")
        self.assertNotIn("an older plugin left", text, "a second repair would have merged the stray")

    def test_an_entry_refused_after_the_cells_ran_is_completed_by_a_rerun(self):
        bid = self._prepare()
        ctx = self.reach_s6(bid)
        real = OL.insert_entry
        calls = []

        def refuses_once(tree, entry, today, root=None):
            calls.append(1)
            if len(calls) == 1:
                raise OL.Refusal("the destination changed after the repair", "changed")
            return real(tree, entry, today, root)

        with mock.patch.object(OL, "insert_entry", refuses_once):
            with self.assertRaises(tss.SS.SurveySheetError) as raised:
                tss.SO.advance(ctx)
            self.assertIn("A rerun completes", " ".join(raised.exception.problems))
            self.assertNotIn(f"survey batch {bid}", self._log_text(), "the refused run added no entry")
            self.assertEqual(self._state(bid), "S6")
            tss.SO.advance(self._ctx(bid))
        self.assertEqual(self._log_text().count(f"survey batch {bid}"), 1)

    def test_a_rerun_in_the_next_month_finds_the_op_and_adds_nothing(self):
        bid = self._prepare()
        with mock.patch.object(OL, "local_date", lambda: "2026-10-31"):
            ctx = self.reach_s6(bid)
            tss.SO.advance(ctx)
        october = self.tree / "log" / "2026-10.md"
        self.assertEqual(october.read_text(encoding="utf-8").count(f"survey batch {bid}"), 1)
        receipt = tss.SS.read_receipt(tss.SS.receipt_paths(self.obs, bid)["receipt"])
        with mock.patch.object(OL, "local_date", lambda: "2026-11-01"):
            again = self._ctx(bid)
            self.assertEqual(tss.SO.write_log_entry(again, receipt), "present")
        self.assertFalse((self.tree / "log" / "2026-11.md").exists(), "positive control for the October write above")
        self.assertEqual(october.read_text(encoding="utf-8").count(f"survey batch {bid}"), 1)

    def test_a_contradicting_op_in_a_detail_file_refuses(self):
        bid = self._prepare()
        self.split_tree()
        ctx = self.reach_s6(bid)
        self.detail.write_text(
            f"# Operations log: {self.month}\n\n_Append-only. Latest write first._\n\n"
            f"## [2020-01-01] observation | survey batch {bid}\n\nRecords: OBS-9999\n\n", encoding="utf-8")
        with self.assertRaises(tss.SO.Contradiction):
            tss.SO.advance(ctx)
        # The refusal came from a hand-written entry: the control writes the op when none stands.
        self.detail.write_text(f"# Operations log: {self.month}\n\n_Append-only. Latest write first._\n\n",
                               encoding="utf-8")
        tss.SO.advance(self._ctx(bid))
        self.assertEqual(self._log_text().count(f"survey batch {bid}"), 1)


class RunPayloadTests(_SurveyLogCase):
    """The full run, with the state derivation reading the operations log (stands in for the readers)."""

    def setUp(self):
        super().setUp()

        def log_has_batch(tree_dir, batch_id, *, _source_io=None):
            subject = f"survey batch {batch_id}"
            return any(e["op"] == "observation" and e["subject"] == subject
                       for e in tss.sp_module._log_entries(OL.read_text(Path(tree_dir).resolve())))

        patch = mock.patch.object(tss.SS, "_log_has_batch", log_has_batch)
        patch.start()
        self.addCleanup(patch.stop)

    def test_the_payload_and_the_writes_carry_the_log_paths(self):
        bid = self._prepare()
        ctx = self._ctx(bid)
        code, payload = tss.SO.run(ctx, dry_run=False)
        self.assertEqual((code, payload["state"]), (0, "S9"))
        self.assertIn(f"bionic/log/{self.month}.md", payload["changed_paths"])
        self.assertIn("bionic/log.md", payload["changed_paths"])
        self.assertIn("log repair: bionic/log.md", payload["writes"])
        self.assertTrue({"commit_paths", "restore_paths", "left_strays"} <= set(payload))
        self.assertEqual(self._log_text().count(f"survey batch {bid}"), 1)

    def test_a_published_batch_reruns_as_a_no_op_that_reports_no_log_paths(self):
        bid = self._prepare()
        self.assertEqual(tss.SO.run(self._ctx(bid), dry_run=False)[0], 0)
        before = tss._snapshot(self.root)
        code, payload = tss.SO.run(self._ctx(bid), dry_run=False)
        self.assertEqual((code, payload["state"], payload["writes"]), (0, "S9", []))
        self.assertNotIn("changed_paths", payload)
        self.assertEqual(tss._snapshot(self.root), before)
