"""The readers of the operations log, over a legacy tree and a split tree.

Each reader reads through `operation_log`: a legacy `log.md`, the monthly detail files under
`log/`, and an incomplete split, in which every legacy entry counts once. Every fixture builds a
temporary tree; nothing here reads this repository's own tree.

Readers covered here: `summaries_projection` (the backfill corroboration read),
`implementation_migration` (the per-file digest binding), `survey_sheet` and `check_observations`
(the observation log ids and the batch state). The other readers, `adr-signals`,
`cycle_context_read`, `migration_disposition` and the live copy, have their cases in their own test
files. Order dependence of each reader is recorded in `operation_log.read_entries`: a first-match
reader finds the latest write first; every reader here asks a set or an `any` question, so none
depends on the order.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import re
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import operation_log as ol  # noqa: E402
import summaries_projection as sp  # noqa: E402
import survey_sheet as ss  # noqa: E402
import implementation_migration as im  # noqa: E402
import check_observations as co  # noqa: E402
from admission_source_io import SourceIO  # noqa: E402

BACKFILL = "## [2026-08-27] backfill | B1\n\nADRs: ADR-0080\n\n"
SURVEY = "## [2026-08-30] observation | survey batch SVY-0001\n\nRecords: OBS-0007\n\n"
LEGACY = "# Operations log\n\nOlder entries below.\n\n" + SURVEY + BACKFILL


def header(month: str) -> str:
    return ol.detail_header(month)


class TreeCase(unittest.TestCase):
    """A temporary docs tree; `write_*` helpers lay down the legacy or the split form."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.tree = self.root / "bionic"
        self.tree.mkdir()

    def legacy(self, text: str = LEGACY) -> None:
        (self.tree / "log.md").write_text(text, encoding="utf-8")

    def detail(self, month: str, entries: str) -> Path:
        directory = self.tree / "log"
        directory.mkdir(exist_ok=True)
        path = directory / f"{month}.md"
        path.write_text(header(month) + entries, encoding="utf-8")
        return path

    def complete(self, months: dict[str, int], legacy_sha256: str | None = None) -> None:
        (self.tree / "log" / ol.COMPLETION_NAME).write_bytes(ol.completion_bytes(legacy_sha256, months))

    def split(self) -> None:
        """The legacy entries as a completed split: each in the file of the month after its heading."""
        self.detail("2026-09", SURVEY + BACKFILL)
        self.complete({"2026-09": 2})

    def staged_legacy(self, text: str = LEGACY) -> Path:
        """An incomplete split: the legacy file renamed into log/ under its own digest."""
        directory = self.tree / "log"
        directory.mkdir(exist_ok=True)
        sha = hashlib.sha256(text.encode()).hexdigest()
        path = directory / f".legacy-{sha}.md"
        path.write_text(text, encoding="utf-8")
        return path


class SummariesProjectionReaderTests(TreeCase):
    def entries(self) -> list[tuple[str, str, str]]:
        return [(e["date"], e["op"], e["subject"]) for e in sp._log_entries(sp._read_operation_log(self.tree))]

    def test_the_heading_grammar_has_one_copy(self):
        self.assertEqual(sp._LOG_HEADING_RE.pattern, ol.HEADING.pattern)
        self.assertTrue(sp._LOG_HEADING_RE.flags & re.M)

    def test_a_legacy_tree_and_a_split_tree_parse_to_the_same_entries(self):
        self.legacy()
        legacy = self.entries()
        self.assertEqual(len(legacy), 2)  # positive control: the fixture holds entries
        (self.tree / "log.md").unlink()
        self.split()
        self.assertEqual(sorted(self.entries()), sorted(legacy))

    def test_an_entry_in_a_later_months_file_is_found(self):
        self.detail("2026-09", BACKFILL)  # the heading is 2026-08; the file is September's
        self.complete({"2026-09": 1})
        self.assertEqual(self.entries(), [("2026-08-27", "backfill", "B1")])
        body = sp._log_entries(sp._read_operation_log(self.tree))[0]["body"]
        self.assertIn("ADRs: ADR-0080", body)

    def test_a_tree_with_no_log_reads_empty(self):
        self.assertEqual(sp._read_operation_log(self.tree), "")
        self.legacy()
        self.assertNotEqual(sp._read_operation_log(self.tree), "")  # positive control

    def test_an_incomplete_split_reads_each_legacy_entry_once_with_the_target_unwritten_or_written(self):
        self.staged_legacy()
        self.assertEqual(sorted(self.entries()), [("2026-08-27", "backfill", "B1"),
                                                  ("2026-08-30", "observation", "survey batch SVY-0001")])
        self.detail("2026-08", SURVEY + BACKFILL)  # the target of both entries is now written
        self.assertEqual(sorted(self.entries()), [("2026-08-27", "backfill", "B1"),
                                                  ("2026-08-30", "observation", "survey batch SVY-0001")])

    def test_a_stray_that_repeats_history_reads_once_per_entry(self):
        self.split()
        self.legacy()  # a log.md beside the completion record is a stray
        self.assertEqual(len(self.entries()), 2)
        self.legacy(LEGACY + "## [2026-11-02] adr | new stray entry\n\nBody.\n\n")
        entries = self.entries()
        self.assertEqual(len(entries), 3)
        self.assertIn(("2026-11-02", "adr", "new stray entry"), entries)  # positive control

    def test_a_symlinked_detail_file_is_refused_with_a_regular_file_as_the_control(self):
        planted = self.root / "planted.md"
        planted.write_text(header("2026-09") + BACKFILL, encoding="utf-8")
        (self.tree / "log").mkdir()
        (self.tree / "log" / "2026-09.md").symlink_to(planted)
        with self.assertRaises(ol.Refusal):
            sp._read_operation_log(self.tree)
        (self.tree / "log" / "2026-09.md").unlink()
        (self.tree / "log" / "2026-09.md").write_bytes(planted.read_bytes())
        self.assertIn("backfill | B1", sp._read_operation_log(self.tree))


class ImplementationMigrationBindingTests(TreeCase):
    def test_a_legacy_log_binds_one_digest(self):
        self.legacy()
        text, bound = im._operation_log(self.root, self.tree, bound=True)
        self.assertEqual(bound, [{"path": "bionic/log.md",
                                  "sha256": hashlib.sha256((self.tree / "log.md").read_bytes()).hexdigest()}])
        self.assertIn("backfill | B1", text)

    def test_a_split_log_binds_each_file_it_read_in_path_order(self):
        self.detail("2026-11", "## [2026-11-02] adr | newer\n\nBody.\n\n")
        self.detail("2026-09", BACKFILL)
        self.detail("2026-10", SURVEY)
        self.complete({"2026-09": 1, "2026-10": 1, "2026-11": 1})
        text, bound = im._operation_log(self.root, self.tree, bound=True)
        names = ["bionic/log/2026-09.md", "bionic/log/2026-10.md", "bionic/log/2026-11.md"]
        self.assertEqual([item["path"] for item in bound], names)
        for item in bound:
            raw = (self.root / item["path"]).read_bytes()
            self.assertEqual(item["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertNotIn("bionic/log.md", [item["path"] for item in bound])
        # Newest write first: the November entry leads the text.
        self.assertLess(text.index("newer"), text.index("survey batch"))

    def test_a_published_read_binds_nothing_and_reads_the_same_text(self):
        self.detail("2026-09", SURVEY + BACKFILL)
        self.complete({"2026-09": 2})
        bound_text, bound = im._operation_log(self.root, self.tree, bound=True)
        published_text, published = im._operation_log(self.root, self.tree, bound=False)
        self.assertEqual(len(bound), 1)  # positive control: the unpublished read does bind
        self.assertEqual(published, [])
        self.assertEqual(published_text, bound_text)

    def test_a_missing_log_still_refuses_as_unreadable(self):
        for bound in (True, False):
            with self.subTest(bound=bound), self.assertRaises(im.Refused) as caught:
                im._operation_log(self.root, self.tree, bound=bound)
            self.assertIn("migration-source-unreadable", str(caught.exception))
        self.legacy()
        self.assertTrue(im._operation_log(self.root, self.tree, bound=True)[0])  # positive control

    def test_an_unreadable_detail_file_refuses_as_unreadable(self):
        self.detail("2026-09", BACKFILL)
        (self.tree / "log" / "2026-09.md").write_bytes(b"\xff\xfe not utf-8\n")
        with self.assertRaises(im.Refused) as caught:
            im._operation_log(self.root, self.tree, bound=True)
        self.assertIn("migration-source-unreadable", str(caught.exception))


class SurveyAndObservationReaderTests(TreeCase):
    def test_the_observation_ids_are_found_in_a_legacy_log_and_in_a_split_log(self):
        self.legacy()
        legacy = co._observation_log_ids(self.root, "bionic")
        self.assertEqual(legacy, {"OBS-0007"})  # positive control
        (self.tree / "log.md").unlink()
        self.split()
        self.assertEqual(co._observation_log_ids(self.root, "bionic"), legacy)

    def test_the_observation_ids_are_found_through_a_retained_snapshot_of_a_split_tree(self):
        self.split()
        source_io = SourceIO(self.root)
        self.addCleanup(source_io.close)
        self.assertEqual(co._observation_log_ids(self.root, "bionic", _source_io=source_io), {"OBS-0007"})
        # NEGATIVE CONTROL: a tree with no log names no id through the same lane.
        empty = TreeCase()
        empty.setUp()
        self.addCleanup(empty.doCleanups)
        other = SourceIO(empty.root)
        self.addCleanup(other.close)
        self.assertEqual(co._observation_log_ids(empty.root, "bionic", _source_io=other), set())

    def test_an_unreadable_log_names_no_id_and_a_regular_one_does(self):
        planted = self.root / "planted.md"
        planted.write_text(header("2026-09") + SURVEY, encoding="utf-8")
        (self.tree / "log").mkdir()
        (self.tree / "log" / "2026-09.md").symlink_to(planted)
        self.assertEqual(co._observation_log_ids(self.root, "bionic"), set())
        (self.tree / "log" / "2026-09.md").unlink()
        (self.tree / "log" / "2026-09.md").write_bytes(planted.read_bytes())
        self.assertEqual(co._observation_log_ids(self.root, "bionic"), {"OBS-0007"})

    def test_the_batch_entry_is_found_in_either_layout_and_in_an_incomplete_split(self):
        self.legacy()
        self.assertTrue(ss._log_has_batch(self.tree, "SVY-0001"))
        self.assertFalse(ss._log_has_batch(self.tree, "SVY-0002"))  # discriminator
        (self.tree / "log.md").unlink()
        self.split()
        self.assertTrue(ss._log_has_batch(self.tree, "SVY-0001"))
        self.assertFalse(ss._log_has_batch(self.tree, "SVY-0002"))
        # An incomplete split with the target unwritten, then written.
        for path in (self.tree / "log").iterdir():
            path.unlink()
        self.staged_legacy()
        self.assertTrue(ss._log_has_batch(self.tree, "SVY-0001"))
        self.detail("2026-08", SURVEY + BACKFILL)
        self.assertTrue(ss._log_has_batch(self.tree, "SVY-0001"))

    def test_a_snapshot_of_an_incomplete_split_still_finds_the_batch_entry(self):
        self.staged_legacy()  # the only place the entry now lives
        source_io = SourceIO(self.root)
        self.addCleanup(source_io.close)
        self.assertTrue(ss._log_has_batch(self.tree, "SVY-0001", _source_io=source_io))
        self.assertFalse(ss._log_has_batch(self.tree, "SVY-0002", _source_io=source_io))  # discriminator

    def test_an_unreadable_log_raises_the_sheet_error(self):
        (self.tree / "log").mkdir()
        (self.tree / "log" / "2026-09.md").write_bytes(b"\xff\xfe")
        with self.assertRaises(ss.SurveySheetError):
            ss.operation_log_text(self.tree)
        (self.tree / "log" / "2026-09.md").write_text(header("2026-09") + SURVEY)
        self.assertIn("survey batch SVY-0001", ss.operation_log_text(self.tree))

    def test_a_tree_with_no_log_has_no_text(self):
        self.assertIsNone(ss.operation_log_text(self.tree))
        self.legacy()
        self.assertIsNotNone(ss.operation_log_text(self.tree))


if __name__ == "__main__":
    unittest.main()
