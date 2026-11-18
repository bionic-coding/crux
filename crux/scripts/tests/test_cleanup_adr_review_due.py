"""CLN-ADR-5 dates the last decision review from reviews and activations.

`cleanup-campsite` CLN-ADR-5 suggests a `migrate-adrs` session when the last
decision review is older than `adr_review_due_days`. The rule is prose a
cleanup agent executes; no script implements it. These tests pin the rule
text, apply the stated rule to fixtures, and check the live tree's validated
activations against the publication commits `authority-view.py state` reports.

What this proves: the skill states both date sources, the exclusions, the
threshold, the no-source reminder and the advisory boundary, and under that
rule the November authority-reset activations on this tree date to
2026-11-06 and 2026-11-08. What it does not prove: that a cleanup agent
reading the skill applies the rule.
"""

from __future__ import annotations

import datetime
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

from _dev_surface import IS_STAGED_ARTIFACT, REPO_ROOT, TREE, require_dev_surface

SKILL = REPO_ROOT / "crux" / "skills" / "cleanup-campsite" / "SKILL.md"
AUTHORITY_VIEW = REPO_ROOT / "crux" / "scripts" / "authority-view.py"
MIGRATIONS = REPO_ROOT / TREE / "adrs" / "migrations"

# The two owner-approved authority-reset packages and the commit date of the
# publication commit that activated each one.
NOVEMBER_ACTIVATIONS = {
    "authority-reset-2026-11": "2026-11-06",
    "authority-reset-2026-11-adr-0151": "2026-11-08",
}

ISO_DATE = re.compile(r"(\d{4}-\d{2}-\d{2})\.md")


def rule_text() -> str:
    """The CLN-ADR-5 rule: its heading, up to the next rule heading."""
    text = SKILL.read_text(encoding="utf-8")
    start = text.index("#### CLN-ADR-5")
    end = text.index("#### CLN-ADR-6", start)
    return text[start:end]


def review_dates(names: list[str]) -> list[datetime.date]:
    """Dates of the dated review reports: ISO calendar filenames only."""
    dates = []
    for name in names:
        match = ISO_DATE.fullmatch(name)
        if not match:
            continue
        try:
            dates.append(datetime.date.fromisoformat(match.group(1)))
        except ValueError:
            continue
    return dates


def last_review(reviews: list[str], activations: list[str],
                today: datetime.date) -> datetime.date | None:
    """The newest valid date that is not in the future, across both sources."""
    dates = review_dates(reviews)
    for value in activations:
        try:
            dates.append(datetime.date.fromisoformat(value))
        except ValueError:
            continue
    dates = [d for d in dates if d <= today]
    return max(dates) if dates else None


def due(reviews: list[str], activations: list[str], today: datetime.date,
        threshold: int = 7) -> bool:
    """Whether CLN-ADR-5 suggests a migration session under the stated rule."""
    anchor = last_review(reviews, activations, today)
    return anchor is None or (today - anchor).days > threshold


class SkillStatesTheRuleTests(unittest.TestCase):
    """The CLN-ADR-5 text names both sources, the exclusions and the boundary."""

    def test_reads_dated_reviews(self) -> None:
        rule = rule_text()
        self.assertIn("`docs/adrs/reviews/*.md`", rule)
        self.assertIn("ISO calendar date", rule)
        self.assertIn("`index.md`", rule)

    def test_reads_validated_activations_from_the_authority_state(self) -> None:
        rule = rule_text()
        self.assertIn("authority-view.py", rule)
        self.assertIn("`publications`", rule)
        self.assertIn("`publication_commit`", rule)
        self.assertIn("show -s --format=%cs <publication_commit>", rule)

    def test_takes_the_newest_nonfuture_date_across_both_sources(self) -> None:
        rule = rule_text()
        self.assertIn("newest", rule)
        self.assertIn("future", rule)
        self.assertIn("across both sources", rule)

    def test_excludes_drafts_and_unactivated_packages(self) -> None:
        rule = rule_text()
        for shape in ("`packages/`", "`candidates/`", "`approvals/`", "`*.publication.json`"):
            with self.subTest(shape=shape):
                self.assertIn(shape, rule)
        self.assertIn("unactivated", rule)

    def test_keeps_the_threshold_the_reminder_and_the_boundary(self) -> None:
        rule = rule_text()
        self.assertIn("`adr_review_due_days` (default 7)", rule)
        self.assertIn("neither a dated review nor a validated activation", rule)
        self.assertIn("`cleanup-CLN-ADR-5-due`", rule)
        self.assertIn("suggest only", rule)
        self.assertIn("invokes no migration", rule)


class StatedRuleTests(unittest.TestCase):
    """The stated rule applied to fixture dates."""

    TODAY = datetime.date(2026, 11, 18)

    def test_an_activation_after_the_last_review_suppresses_the_reminder(self) -> None:
        self.assertTrue(due(["2026-09-30.md"], [], self.TODAY))
        self.assertFalse(due(["2026-09-30.md"], ["2026-11-14"], self.TODAY))

    def test_a_review_after_the_last_activation_still_counts(self) -> None:
        self.assertFalse(due(["2026-11-15.md"], ["2026-10-01"], self.TODAY))

    def test_future_dates_anchor_nothing(self) -> None:
        self.assertTrue(due(["2027-01-01.md"], ["2026-12-01"], self.TODAY))

    def test_invalid_names_and_the_index_are_skipped(self) -> None:
        self.assertTrue(due(["index.md", "2026-02-30.md", "notes.md"], ["not-a-date"], self.TODAY))

    def test_no_source_still_reminds(self) -> None:
        self.assertTrue(due([], [], self.TODAY))

    def test_the_configured_threshold_is_kept(self) -> None:
        self.assertFalse(due([], ["2026-11-08"], self.TODAY, threshold=10))
        self.assertTrue(due([], ["2026-11-08"], self.TODAY, threshold=9))


class LiveTreeTests(unittest.TestCase):
    """The validated activations on this repository's tree."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.result = subprocess.run(
            [sys.executable, str(AUTHORITY_VIEW), "state", "--repo-root", str(REPO_ROOT)],
            capture_output=True, text=True, timeout=600)

    def setUp(self) -> None:
        require_dev_surface(self, MIGRATIONS, f"{TREE}/adrs/migrations")
        if IS_STAGED_ARTIFACT:
            self.skipTest("the staged artifact carries no migration history")
        if self.result.returncode == 1 and '"history-unavailable"' in self.result.stdout:
            self.skipTest("shallow clone: authority-view.py state needs full history")
        self.assertEqual(self.result.returncode, 0, self.result.stdout + self.result.stderr)
        self.state = json.loads(self.result.stdout)

    def publications(self) -> dict[str, str]:
        rows = {}
        for entry in self.state["publications"]:
            name = Path(entry["path"]).name
            rows[name] = entry["publication_commit"]
        return rows

    def commit_date(self, commit: str) -> str:
        out = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "show", "-s", "--format=%cs", commit],
            capture_output=True, text=True, check=True)
        return out.stdout.strip()

    def test_the_november_activations_are_validated_publications(self) -> None:
        rows = self.publications()
        for package, date in NOVEMBER_ACTIVATIONS.items():
            with self.subTest(package=package):
                commit = rows.get(f"{package}.publication.json")
                self.assertIsNotNone(commit, sorted(rows))
                self.assertEqual(self.commit_date(commit), date)

    def test_package_and_approval_records_are_not_publications(self) -> None:
        # Positive control for the exclusion: the same packages have draft and
        # approval files, and the state reports neither as an activation.
        paths = {entry["path"] for entry in self.state["publications"]}
        for package in NOVEMBER_ACTIVATIONS:
            for folder in ("packages", "approvals"):
                record = MIGRATIONS / folder / f"{package}.json"
                with self.subTest(record=record.name, folder=folder):
                    self.assertTrue(record.is_file(), record)
                    self.assertNotIn(f"{TREE}/adrs/migrations/{folder}/{package}.json", paths)

    def test_the_rule_dates_the_last_review_no_earlier_than_november(self) -> None:
        # Later reviews or activations only move the anchor forward, so this
        # holds on any future state of the tree.
        reviews = sorted(p.name for p in (REPO_ROOT / TREE / "adrs" / "reviews").glob("*.md"))
        dates = [self.commit_date(row) for row in self.publications().values()]
        anchor = last_review(reviews, dates, datetime.date.today())
        self.assertIsNotNone(anchor)
        self.assertGreaterEqual(anchor, datetime.date(2026, 11, 8))


if __name__ == "__main__":
    unittest.main()
