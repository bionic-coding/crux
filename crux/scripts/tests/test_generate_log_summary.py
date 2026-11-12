"""The operations log summary: the settled-month rule, the catch-up, narratives and the gate.

`generate-log-summary.py` writes `<docs_dir>/log/summary.md` (write mode, the catch-up) and checks
it (`--dry-run`, the summary gate). Every fixture builds a temporary tree; nothing here reads or
writes this repository's own tree.
"""

from __future__ import annotations

import errno
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_operation_log import CLI, SCRIPTS, TreeCase, entry, ol  # noqa: E402

GEN = SCRIPTS / "generate-log-summary.py"
SEPT = entry("2026-09-04", "adr", "Proposed ADR-0012 and ADR-0003") + entry("2026-09-02", "query", "Asked")
AUG = entry("2026-08-30", "journal", "Logged") + entry("2026-08-01", "query", "Asked")
JULY = entry("2026-07-09", "init", "Tree")
OCT = entry("2026-10-31", "query", "Asked late")
NOV = entry("2026-11-05", "query", "This month")
NARRATIVE = "\nA hand-written note about August.\n\n```\n## 2026-01\n```\n\n"


def detail(month: str, body: str) -> str:
    return ol.detail_header(month) + body


class SummaryCase(TreeCase):
    def setUp(self):
        super().setUp()
        self.summary = self.log_dir / ol.SUMMARY_NAME

    def tree_with(self, **months: str) -> None:
        self.split(**{month: detail(month, body) for month, body in months.items()})

    def run_gen(self, *args, today="2026-11-11", env=None):
        command = [sys.executable, str(GEN), "--repo-root", str(self.root), *args]
        if today is not None:
            command += ["--today", today]
        done = subprocess.run(command, capture_output=True, text=True,
                              env=env if env is not None else dict(os.environ))
        payload = json.loads(done.stdout) if done.stdout.strip() else None
        return done.returncode, payload, done.stderr

    def gate(self, today="2026-11-11"):
        return self.run_gen("--dry-run", today=today)

    def catch_up(self, today="2026-11-11"):
        return self.run_gen(today=today)

    def kinds(self, payload) -> list[tuple[str, str]]:
        return [(item["kind"], item["code"]) for item in payload["failures"]]


class SettlingTests(SummaryCase):
    """A month gets a section only from the third day of the next month."""

    def test_the_current_month_never_gets_a_section_and_the_previous_only_from_day_three(self):
        self.tree_with(**{"2026-09": SEPT, "2026-10": OCT})
        for today, expect in (("2026-10-31", ["2026-09"]), ("2026-11-01", ["2026-09"]),
                              ("2026-11-02", ["2026-09"]), ("2026-11-03", ["2026-09", "2026-10"])):
            with self.subTest(today=today):
                if self.summary.exists():
                    self.summary.unlink()
                code, payload, err = self.catch_up(today)
                self.assertEqual(code, 0, err)
                self.assertEqual(payload["status"], "written")
                text = self.summary.read_text()
                self.assertEqual(ol.parse_summary(text).errors, [])
                self.assertEqual([s.month for s in ol.parse_summary(text).sections], sorted(expect, reverse=True))
                # POSITIVE CONTROL for the absence: the current month's file exists and is listed.
                self.assertTrue((self.log_dir / f"{today[:7]}.md").exists() or today[:7] == "2026-11")
                self.assertNotIn(f"## {today[:7]}\n", text)

    def test_settled_reads_the_third_day_of_the_next_month(self):
        self.assertFalse(ol.settled("2026-12", "2027-01-02"))
        self.assertTrue(ol.settled("2026-12", "2027-01-03"))
        self.assertFalse(ol.settled("2026-10", "2026-10-31"))

    def test_the_gate_exit_code_does_not_change_with_the_date_alone(self):
        self.tree_with(**{"2026-09": SEPT, "2026-10": OCT})
        code, _, err = self.catch_up("2026-10-31")
        self.assertEqual(code, 0, err)
        results = {}
        for today in ("2026-11-01", "2026-11-02", "2026-11-03"):
            code, payload, err = self.gate(today)
            results[today] = (code, payload["pending_months"])
        self.assertEqual({code for code, _ in results.values()}, {0}, results)
        # Settling adds pending work, not a failure.
        self.assertEqual(results["2026-11-02"][1], [])
        self.assertEqual(results["2026-11-03"][1], ["2026-10"])

    def test_a_malformed_heading_in_the_current_month_leaves_the_gate_unchanged(self):
        self.tree_with(**{"2026-09": SEPT, "2026-11": NOV})
        self.catch_up()
        before = self.gate()
        (self.log_dir / "2026-11.md").write_text(detail("2026-11", "## [2026-11-05] nonsense | x\n\nb\n"))
        after = self.gate()
        self.assertEqual(before[0], after[0])
        self.assertEqual(after[0], 0, after)
        # POSITIVE CONTROL: the audit check reports the same heading.
        done = subprocess.run([sys.executable, str(CLI), "check", "--repo-root", str(self.root)],
                              capture_output=True, text=True)
        findings = json.loads(done.stdout)["findings"]
        self.assertTrue(any(f["check"] == "CHK-LOG-1" and f["path"].endswith("2026-11.md") for f in findings))


class CatchUpTests(SummaryCase):
    def test_the_first_catch_up_creates_summary_md_with_its_header(self):
        self.tree_with(**{"2026-09": SEPT})
        self.assertFalse(self.summary.exists())
        code, payload, err = self.catch_up()
        self.assertEqual((code, payload["status"], payload["created"]), (0, "written", True), err)
        text = self.summary.read_text()
        self.assertTrue(text.startswith(ol.SUMMARY_HEADER))
        self.assertIn("- Entries: 2\n", text)
        self.assertIn("- ADRs: ADR-0003, ADR-0012\n", text)
        self.assertIn("- Ops: adr 1, query 1\n", text)
        self.assertEqual(self.gate(), (0, self.gate()[1], ""))

    def test_no_settled_month_writes_nothing(self):
        self.tree_with(**{"2026-11": NOV})
        code, payload, err = self.catch_up()
        self.assertEqual((code, payload["status"]), (0, "unchanged"), err)
        self.assertFalse(self.summary.exists())

    def test_three_missed_months_get_three_sections_and_a_rollup_in_one_run(self):
        self.tree_with(**{"2026-07": JULY, "2026-08": AUG, "2026-09": SEPT, "2026-11": NOV})
        code, payload, err = self.catch_up()
        self.assertEqual(code, 0, err)
        self.assertEqual(payload["added_months"], ["2026-07", "2026-08", "2026-09"])
        doc = ol.parse_summary(self.summary.read_text())
        self.assertEqual([s.month for s in doc.sections], ["2026-09", "2026-08", "2026-07"])
        rollup = doc.body(doc.rollup)
        self.assertEqual(rollup.count("\n"), 2 + 3, rollup)
        self.assertLess(rollup.index("| 2026-09 |"), rollup.index("| 2026-07 |"))
        code, payload, _ = self.gate()
        self.assertEqual((code, payload["pending_months"], payload["failures"]), (0, [], []))

    def test_an_existing_section_and_its_narrative_stay_byte_identical(self):
        self.tree_with(**{"2026-08": AUG})
        self.catch_up("2026-09-10")
        text = self.summary.read_text()
        end = ol.summary_marker("END", "2026-08") + "\n"
        text = text.replace(end, end + NARRATIVE)
        self.summary.write_text(text)
        section = text[text.index("## 2026-08"):]
        self.tree_with(**{"2026-08": AUG, "2026-07": JULY, "2026-09": SEPT, "2026-10": OCT})
        code, payload, err = self.catch_up()
        self.assertEqual(code, 0, err)
        self.assertEqual(payload["added_months"], ["2026-07", "2026-09", "2026-10"])
        after = self.summary.read_text()
        start = after.index("## 2026-08")
        self.assertEqual(after[start:start + len(section)], section)
        doc = ol.parse_summary(after)
        self.assertEqual([s.month for s in doc.sections], ["2026-10", "2026-09", "2026-08", "2026-07"])
        # The fenced `## 2026-01` in the narrative is not a section.
        self.assertNotIn("2026-01", [s.month for s in doc.sections])
        self.assertEqual(self.gate()[0], 0)

    def test_a_stale_settled_region_is_rewritten_and_text_outside_regions_kept(self):
        self.tree_with(**{"2026-08": AUG})
        self.catch_up()
        text = self.summary.read_text()
        end = ol.summary_marker("END", "2026-08") + "\n"
        self.summary.write_text(text.replace(end, end + NARRATIVE))
        (self.log_dir / "2026-08.md").write_text(detail("2026-08", entry("2026-08-31", "release", "v1") + AUG))
        code, payload, _ = self.gate()
        # The rollup reads the regions alone, so a stale region leaves the rollup consistent.
        self.assertEqual(self.kinds(payload), [("region", "region")])
        self.assertEqual(code, 1)
        code, payload, err = self.catch_up()
        self.assertEqual((code, payload["rewritten_months"]), (0, ["2026-08"]), err)
        after = self.summary.read_text()
        self.assertIn(end + NARRATIVE, after)
        self.assertIn("- Entries: 3\n", after)
        self.assertEqual(self.gate()[0], 0)

    def test_the_catch_up_refuses_on_an_incomplete_split(self):
        self.tree_with(**{"2026-08": AUG})
        self.catch_up()
        (self.log_dir / ol.COMPLETION_NAME).unlink()
        (self.log_dir / f".split-{'a' * 64}.json").write_text("{}")
        self.tree_with(**{"2026-09": SEPT})
        (self.log_dir / ol.COMPLETION_NAME).unlink()
        before = self.summary.read_bytes()
        code, payload, _ = self.catch_up()
        self.assertEqual((code, payload["status"], payload["code"]), (1, "refused", "incomplete-split"))
        self.assertEqual(self.summary.read_bytes(), before)
        # POSITIVE CONTROL: with the completion record back the same tree catches up.
        (self.log_dir / ol.COMPLETION_NAME).write_bytes(ol.completion_bytes(None, {}))
        self.assertEqual(self.catch_up()[1]["status"], "written")

    def test_the_catch_up_refuses_on_an_unsplit_legacy_log(self):
        self.tree_with(**{"2026-08": AUG})
        self.catch_up()
        (self.log_dir / ol.COMPLETION_NAME).unlink()
        (self.tree / "log.md").write_text("# Log\n\n" + SEPT)
        self.tree_with(**{"2026-09": SEPT})
        (self.log_dir / ol.COMPLETION_NAME).unlink()
        before = self.summary.read_bytes()
        code, payload, _ = self.catch_up()
        self.assertEqual((code, payload["code"]), (1, "legacy-unsplit"))
        self.assertEqual(self.summary.read_bytes(), before)
        # With no log/ at all the catch-up refuses the same way and creates nothing.
        for path in self.log_dir.iterdir():
            path.unlink()
        self.log_dir.rmdir()
        code, payload, _ = self.catch_up()
        self.assertEqual((code, payload["code"]), (1, "legacy-unsplit"))
        self.assertFalse(self.log_dir.exists())

    def test_a_rollup_made_red_by_removing_a_section_turns_green_after_write_mode(self):
        self.tree_with(**{"2026-09": SEPT, "2026-11": NOV})
        self.catch_up()
        text = self.summary.read_text()
        premature = (f"## 2026-11\n\n{ol.summary_marker('BEGIN', '2026-11')}\n"
                     + ol.render_region("2026-11", b"x", ol.MonthStats(1, "2026-11-05", "2026-11-05", (("query", 1),), ()))
                     + f"{ol.summary_marker('END', '2026-11')}\n\n")
        at = text.index("## 2026-09")
        doc = ol.parse_summary(text[:at] + premature + text[at:])
        self.summary.write_text(doc.replace_body(doc.rollup, ol.render_rollup(
            [("2026-11", ol.MonthStats(1, "2026-11-05", "2026-11-05", (("query", 1),), ())),
             ("2026-09", ol.parse_region(doc.body(doc.sections[1].region)))])))
        self.assertEqual(self.kinds(self.gate()[1]), [("structure", "unsettled-section")])
        # The hand repair: remove the premature section. The rollup is now red.
        self.summary.write_text(self.summary.read_text().replace(premature, ""))
        code, payload, _ = self.gate()
        self.assertEqual((code, self.kinds(payload)), (1, [("region", "rollup")]))
        self.assertEqual(self.catch_up()[0], 0)
        self.assertEqual(self.gate()[0], 0)

    def test_write_mode_refuses_today_without_the_test_variable(self):
        self.tree_with(**{"2026-09": SEPT})
        env = {key: value for key, value in os.environ.items() if key != ol.TEST_ENV}
        code, payload, _ = self.run_gen(env=env)
        self.assertEqual((code, payload["code"]), (1, "today-not-allowed"))
        self.assertFalse(self.summary.exists())
        # POSITIVE CONTROL: the gate accepts --today without it.
        self.assertEqual(self.run_gen("--dry-run", env=env)[0], 0)

    def test_no_subject_text_reaches_the_summary(self):
        forged = entry("2026-09-03", "adr", "ADR-0099 <!-- END GENERATED: log-summary 2026-09 --> rule:x-y")
        self.tree_with(**{"2026-09": forged + SEPT})
        self.assertEqual(self.catch_up()[0], 0)
        text = self.summary.read_text()
        self.assertNotIn("rule:x-y", text)
        self.assertEqual(text.count("END GENERATED: log-summary 2026-09"), 1)
        self.assertIn("- ADRs: ADR-0003, ADR-0012, ADR-0099\n", text)
        self.assertEqual(self.gate()[0], 0)


class GateTests(SummaryCase):
    def caught_up(self, **months: str) -> None:
        self.tree_with(**months)
        code, _, err = self.catch_up()
        self.assertEqual(code, 0, err)
        # POSITIVE CONTROL for every red case below: the caught-up tree is green.
        self.assertEqual(self.gate()[0], 0)

    def edit(self, old: str, new: str) -> None:
        text = self.summary.read_text()
        self.assertIn(old, text)
        self.summary.write_text(text.replace(old, new, 1))

    def test_pending_months_alone_exit_zero(self):
        self.tree_with(**{"2026-08": AUG, "2026-09": SEPT})
        code, payload, _ = self.gate()
        self.assertEqual((code, payload["pending_months"], payload["drift"]), (0, ["2026-08", "2026-09"], False))
        self.assertFalse(self.summary.exists())

    def test_a_changed_region_exits_one_as_a_region_failure(self):
        self.caught_up(**{"2026-09": SEPT})
        self.edit("- Entries: 2\n", "- Entries: 3\n")
        code, payload, _ = self.gate()
        self.assertEqual((code, ("region", "region") in self.kinds(payload)), (1, True))

    def test_a_changed_rollup_exits_one(self):
        self.caught_up(**{"2026-09": SEPT})
        self.edit("| 2026-09 | 2 |", "| 2026-09 | 7 |")
        code, payload, _ = self.gate()
        self.assertEqual((code, self.kinds(payload)), (1, [("region", "rollup")]))

    def section(self, month: str) -> str:
        stats = ol.MonthStats(0, None, None, (), ())
        return (f"## {month}\n\n{ol.summary_marker('BEGIN', month)}\n{ol.render_region(month, b'', stats)}"
                f"{ol.summary_marker('END', month)}\n\n")

    def test_a_section_for_the_current_or_a_later_month_exits_one(self):
        for month in ("2026-11", "2026-12"):
            with self.subTest(month=month):
                self.summary.unlink(missing_ok=True)
                self.caught_up(**{"2026-09": SEPT, month: NOV.replace("2026-11", month)})
                self.edit("## 2026-09", self.section(month) + "## 2026-09")
                code, payload, _ = self.gate()
                self.assertEqual(code, 1)
                self.assertIn(("structure", "unsettled-section"), self.kinds(payload))
                (self.log_dir / f"{month}.md").unlink()

    def test_a_second_section_exits_one(self):
        self.caught_up(**{"2026-09": SEPT})
        text = self.summary.read_text()
        self.summary.write_text(text + "\n" + text[text.index("## 2026-09"):])
        code, payload, _ = self.gate()
        self.assertEqual(code, 1)
        self.assertIn(("structure", "second-section"), self.kinds(payload))

    def test_a_section_without_a_detail_file_exits_one(self):
        self.caught_up(**{"2026-09": SEPT})
        self.summary.write_text(self.summary.read_text() + "\n" + self.section("2026-06"))
        code, payload, _ = self.gate()
        self.assertEqual(code, 1)
        self.assertIn(("structure", "no-detail-file"), self.kinds(payload))

    def test_an_incomplete_split_exits_one(self):
        self.caught_up(**{"2026-09": SEPT})
        (self.log_dir / ol.COMPLETION_NAME).unlink()
        (self.log_dir / f".legacy-{'b' * 64}.md").write_text("# Log\n")
        code, payload, _ = self.gate()
        self.assertEqual((code, self.kinds(payload)), (1, [("structure", "incomplete-split")]))

    def test_a_transaction_file_beside_the_completion_record_is_no_incomplete_split(self):
        self.caught_up(**{"2026-09": SEPT})
        (self.log_dir / f".split-{'c' * 64}.json").write_text("{}")
        self.assertEqual(self.gate()[0], 0)
        self.tree_with(**{"2026-08": AUG})
        code, payload, err = self.catch_up()
        self.assertEqual((code, payload["status"]), (0, "written"), err)
        # POSITIVE CONTROL: without the completion record the same file is an incomplete split.
        (self.log_dir / ol.COMPLETION_NAME).unlink()
        self.assertEqual(self.kinds(self.gate()[1]), [("structure", "incomplete-split")])

    def test_marker_errors_exit_one(self):
        cases = {
            "missing": (ol.summary_marker("END", "2026-09") + "\n", ""),
            "duplicated": (ol.summary_marker("BEGIN", "2026-09") + "\n",
                           ol.summary_marker("BEGIN", "2026-09") + "\n" + ol.summary_marker("BEGIN", "2026-09") + "\n"),
            "misordered": (ol.summary_marker("END", "rollup") + "\n", ""),
            "malformed": (ol.summary_marker("BEGIN", "2026-09"), "<!-- BEGIN GENERATED: log-summary Sept -->"),
        }
        for name, (old, new) in cases.items():
            with self.subTest(case=name):
                self.summary.unlink(missing_ok=True)
                self.caught_up(**{"2026-09": SEPT})
                self.edit(old, new)
                code, payload, _ = self.gate()
                self.assertEqual(code, 1, payload)
                self.assertIn(("structure", "marker"), self.kinds(payload))
                before = self.summary.read_bytes()
                self.assertEqual(self.catch_up()[1]["code"], "structure")
                self.assertEqual(self.summary.read_bytes(), before)

    def test_a_tree_without_log_passes_with_no_sections(self):
        (self.tree / "log.md").write_text("# Log\n\n" + SEPT)
        code, payload, _ = self.gate()
        self.assertEqual((code, payload["sections"], payload["pending_months"]), (0, [], []))
        self.assertTrue(payload["surface_absent"])
        self.assertFalse(self.log_dir.exists())


class DocumentLaneTests(SummaryCase):
    def test_a_heading_date_that_is_not_a_calendar_date_is_a_document_finding(self):
        self.tree_with(**{"2026-09": SEPT})
        self.catch_up()
        (self.log_dir / "2026-09.md").write_text(detail("2026-09", entry("2026-09-31", "query", "Bad") + SEPT))
        before = self.summary.read_bytes()
        for mode in (("--dry-run",), ()):
            with self.subTest(mode=mode):
                code, payload, _ = self.run_gen(*mode)
                self.assertEqual(code, 1)
                self.assertEqual([e["file"] for e in payload["validation_errors"]], ["docs/log/2026-09.md"])
                self.assertIn("2026-09-31", payload["validation_errors"][0]["error"])
                self.assertEqual(self.summary.read_bytes(), before)

    def test_a_detail_file_that_is_not_utf8_is_a_document_finding(self):
        self.tree_with(**{"2026-09": SEPT})
        (self.log_dir / "2026-09.md").write_bytes(detail("2026-09", SEPT).encode() + b"\xff\n")
        code, payload, _ = self.gate()
        self.assertEqual(code, 1)
        self.assertIn("not valid UTF-8", payload["validation_errors"][0]["error"])

    def test_an_os_error_reading_a_detail_file_is_an_environment_failure(self):
        self.tree_with(**{"2026-09": SEPT})
        real = ol._read_log_input

        def failing(directory_fd, name):
            if name == "2026-09.md":
                raise OSError(errno.EIO, "Input/output error")
            return real(directory_fd, name)

        # POSITIVE CONTROL: unstubbed, the same tree reads clean.
        self.assertEqual(ol.summarize(self.tree, self.root, "2026-11-11", write=False)[0], 0)
        import input_lanes
        with patch.object(ol, "_read_log_input", failing):
            with self.assertRaises(input_lanes.EnvironmentLaneError) as caught:
                ol.summarize(self.tree, self.root, "2026-11-11", write=False)
        self.assertIn("docs/log/2026-09.md", caught.exception.failures[0])

    def test_the_current_month_file_is_never_read(self):
        self.tree_with(**{"2026-11": NOV})
        (self.log_dir / "2026-11.md").write_bytes(b"\xff not utf-8")
        self.assertEqual(self.gate()[0], 0)
        # POSITIVE CONTROL: once the month is past, the same bytes are a document finding.
        self.assertEqual(self.gate("2026-12-01")[0], 1)


class CheckLog7Tests(SummaryCase):
    def check(self):
        done = subprocess.run([sys.executable, str(CLI), "check", "--repo-root", str(self.root),
                               "--today", "2026-11-11"], capture_output=True, text=True)
        return [f for f in json.loads(done.stdout)["findings"] if f["check"] == "CHK-LOG-7"]

    def init_tree(self, **months: str) -> None:
        months = {**months, "2026-07": JULY}
        self.tree_with(**months)

    def test_a_clean_summary_has_no_finding(self):
        self.init_tree(**{"2026-09": SEPT})
        self.catch_up()
        self.assertEqual(self.check(), [])

    def test_pending_months_are_a_warning(self):
        self.init_tree(**{"2026-09": SEPT})
        found = self.check()
        self.assertEqual([f["severity"] for f in found], ["WARNING"])
        self.assertIn("2026-09", found[0]["message"])

    def test_region_and_structure_failures_are_separated(self):
        self.init_tree(**{"2026-09": SEPT})
        self.catch_up()
        text = self.summary.read_text()
        self.summary.write_text(text.replace("- Entries: 2\n", "- Entries: 9\n"))
        region = self.check()
        # The edited region differs from its derivation, and the rollup from the edited region.
        self.assertEqual([f["severity"] for f in region], ["DRIFT", "DRIFT"])
        self.assertTrue(all("auto-fix: run generate-log-summary.py" in f["message"] for f in region))
        self.summary.write_text(text + "\n" + text[text.index("## 2026-09"):])
        found = self.check()
        self.assertTrue(all(f["severity"] == "DRIFT" for f in found))
        structure = [f for f in found if f["message"].startswith("structure failure")]
        self.assertTrue(structure, found)
        for finding in structure:
            self.assertIn("no auto-fix", finding["message"])
            self.assertNotIn("auto-fix: run generate-log-summary.py", finding["message"])
        # The second section also adds a rollup row; that region failure keeps its auto-fix.
        self.assertTrue(all("auto-fix: run generate-log-summary.py" in f["message"]
                            for f in found if f["message"].startswith("region failure")))


if __name__ == "__main__":
    unittest.main()
