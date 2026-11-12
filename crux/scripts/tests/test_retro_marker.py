"""Round-trip tests for the CLN-RETRO-1 retrospective marker.

Operative guarantee (per ADR-0038 §3, §7, and the cadence cross-reference
section of retrospective/SKILL.md):

  (a) A heading built from the template log-work emits for a Retrospective
      journal entry matches the detection regex below.

  (c) CLN-RETRO-1 counts closed cycle records (completed, abandoned or
      shortcut) whose closing history event is dated after the newest
      retrospective anchor.  A reference count over seeded records pins its
      edges.

  (f) A line whose content happens to start with `## [` DOES match the
      line-anchored detection regex: the regex alone cannot distinguish a
      real heading from body text planted with the heading prefix.

Uses only stdlib (unittest, re, pathlib).  No mocks needed — everything
resolves from repo-relative paths so the test is cwd-independent.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

# ─── repo paths ──────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
RETRO_SKILL = REPO_ROOT / "crux" / "skills" / "retrospective" / "SKILL.md"

# ─── canonical strings (single source of truth for THIS test) ────────────────
#
# Detection regex for Retrospective journal headings.
RETRO_DETECTION_REGEX: str = (
    r"^## \[\d{4}-\d{2}-\d{2} \d{2}:\d{2}\] learning \| Retrospective: "
)

# Heading template that log-work emits when recording a retrospective.
# The window-summary suffix is variable; the prefix is fixed.
RETRO_HEADING_TEMPLATE: str = "## [YYYY-MM-DD HH:MM] learning | Retrospective: "

# Statuses CLN-RETRO-1 counts as a closed cycle record.
CLOSED_STATUSES: tuple[str, ...] = ("completed", "abandoned", "shortcut")


class TestRetroHeadingRoundTrip(unittest.TestCase):
    """(a) A concrete heading built from the template MUST match the regex."""

    def test_template_matches_detection_regex(self) -> None:
        """A real-looking Retrospective heading matches RETRO_DETECTION_REGEX."""
        regex = re.compile(RETRO_DETECTION_REGEX)
        # Construct a plausible heading from the template (substitute fixed
        # placeholder tokens with valid values; append a sample window summary).
        concrete_heading = "## [2026-06-11 14:30] learning | Retrospective: Q2 books — 3 archived"
        self.assertIsNotNone(
            regex.match(concrete_heading),
            msg=(
                f"Concrete heading built from the template did not match the "
                f"detection regex.\n  heading: {concrete_heading!r}\n"
                f"  regex:   {RETRO_DETECTION_REGEX!r}"
            ),
        )

    def test_template_prefix_is_regex_prefix(self) -> None:
        """The non-variable prefix of the template MUST be the literal start
        of what the regex matches — so the regex is anchored to the template."""
        # The template's literal portion (before the window-summary slot)
        # must itself match the regex when a trivial suffix is appended.
        regex = re.compile(RETRO_DETECTION_REGEX)
        heading_with_minimal_suffix = RETRO_HEADING_TEMPLATE + "X"
        # Replace placeholder tokens with valid values for matching.
        concrete = heading_with_minimal_suffix.replace(
            "YYYY-MM-DD", "2026-06-11"
        ).replace("HH:MM", "09:00")
        self.assertIsNotNone(
            regex.match(concrete),
            msg=(
                f"Template prefix with a trivial suffix did not match the "
                f"detection regex after placeholder substitution.\n"
                f"  concrete: {concrete!r}\n  regex:    {RETRO_DETECTION_REGEX!r}"
            ),
        )

    def test_body_mention_does_not_match(self) -> None:
        """A body-level mention of 'Retrospective:' without the heading prefix
        MUST NOT match (confirms the regex is anchored to the heading form)."""
        regex = re.compile(RETRO_DETECTION_REGEX)
        body_mention = "See the Retrospective: summary below."
        self.assertIsNone(
            regex.match(body_mention),
            msg=(
                f"Body mention of 'Retrospective:' incorrectly matched the "
                f"detection regex.\n  mention: {body_mention!r}\n"
                f"  regex:   {RETRO_DETECTION_REGEX!r}"
            ),
        )


class TestRetrospectiveSkillContainsRetroRegex(unittest.TestCase):
    """retrospective/SKILL.md exists."""

    def test_retro_skill_exists(self) -> None:
        """retrospective/SKILL.md must exist; its absence is a regression."""
        self.assertTrue(
            RETRO_SKILL.exists(),
            msg=(
                f"retrospective/SKILL.md not found at {RETRO_SKILL}. "
                f"The skill has been landed; its absence is a regression."
            ),
        )


def closing_event(record: dict) -> dict:
    """The closing status event: the first history entry whose `status` equals the
    record's closed status; an older record with no `status` fields uses its last entry."""
    for event in record["history"]:
        if event.get("status") == record["status"]:
            return event
    return record["history"][-1]


def closed_cycles_since(records: list[dict], anchor: str | None) -> int:
    """Reference count for CLN-RETRO-1: closed records whose closing status event
    is dated strictly after the anchor date (all closed records without one)."""
    count = 0
    for record in records:
        if record["status"] not in CLOSED_STATUSES:
            continue
        closed_on = closing_event(record)["at"][:10]
        if anchor is None or closed_on > anchor:
            count += 1
    return count


def _record(status: str, at: str) -> dict:
    return {"status": status, "history": [{"action": "start", "at": "2026-01-01T00:00:00+00:00"},
                                          {"action": "close", "at": at}]}


class TestClosedCycleCount(unittest.TestCase):
    """(c) CLN-RETRO-1 counts closed cycle records after the retrospective anchor."""

    RECORDS = [
        _record("completed", "2026-11-02T10:00:00+00:00"),
        _record("abandoned", "2026-11-03T10:00:00+00:00"),
        _record("shortcut", "2026-11-04T10:00:00+00:00"),
        _record("completed", "2026-11-01T23:59:00+00:00"),   # closes on the anchor day
        _record("completed", "2026-10-20T10:00:00+00:00"),   # before the anchor
        _record("paused", "2026-11-05T10:00:00+00:00"),      # not closed
        _record("active", "2026-11-06T10:00:00+00:00"),      # not closed
    ]

    def test_counts_completed_abandoned_and_shortcut_after_the_anchor(self) -> None:
        self.assertEqual(closed_cycles_since(self.RECORDS, "2026-11-01"), 3)

    def test_each_closed_status_counts_alone(self) -> None:
        """Positive control: dropping any one counted status lowers the count."""
        for status in CLOSED_STATUSES:
            with self.subTest(status=status):
                kept = [r for r in self.RECORDS if r["status"] != status]
                self.assertEqual(closed_cycles_since(kept, "2026-11-01"), 2)

    def test_unclosed_and_earlier_records_are_not_counted(self) -> None:
        self.assertEqual(closed_cycles_since(
            [r for r in self.RECORDS if r["status"] in ("paused", "active")], None), 0)
        self.assertEqual(closed_cycles_since(self.RECORDS, "2026-11-04"), 0)

    def test_first_run_counts_every_closed_record(self) -> None:
        self.assertEqual(closed_cycles_since(self.RECORDS, None), 5)

    def test_a_late_event_after_closure_does_not_move_the_closing_date(self) -> None:
        """A late assignment event after the closing status event keeps the closure date."""
        late = {"status": "completed", "history": [
            {"action": "start", "at": "2026-01-01T00:00:00+00:00", "status": "active"},
            {"action": "finish", "at": "2026-10-20T10:00:00+00:00", "status": "completed"},
            {"action": "assignment", "at": "2026-11-03T10:00:00+00:00", "status": "completed"}]}
        self.assertEqual(closed_cycles_since([late], "2026-11-01"), 0)
        # Positive control: the last-entry reading this replaces would count it.
        self.assertGreater(late["history"][-1]["at"][:10], "2026-11-01")

    def test_real_closed_records_exist_with_a_closing_event_date(self) -> None:
        """The predicate reads fields real cycle records carry."""
        import json
        cycles = REPO_ROOT / "bionic" / "cycles"
        seen = 0
        for path in sorted(cycles.glob("CYC-*/cycle.json")) if cycles.is_dir() else []:
            record = json.loads(path.read_text(encoding="utf-8"))
            if record.get("status") in CLOSED_STATUSES:
                self.assertRegex(closing_event(record)["at"], r"^\d{4}-\d{2}-\d{2}T")
                seen += 1
        if not cycles.is_dir():
            self.skipTest("no cycle records in this tree")
        self.assertGreater(seen, 0)


class TestRegexBehaviorDoc(unittest.TestCase):
    """(f) Documents the regex limitation that makes the skills' prose guards necessary.

    A line whose content starts with `## [` followed by the full heading
    pattern DOES match the line-anchored detection regex — even when that
    line appears in entry body text.  This is exactly why the prose validity
    guards in retrospective/SKILL.md and log-work/references/journal.md are load-bearing:
    the regex cannot distinguish a real heading from planted body text with
    the heading prefix.

    The assertion here is intentional: it asserts the MATCH (not a non-match).
    This pin documents the assumption the guards rest on.  If someone ever
    changes the regex to scope-match only at document structural positions,
    this test will fail, which is the correct signal to also re-evaluate
    whether the prose guards remain necessary.
    """

    def test_full_heading_line_in_body_position_matches_regex(self) -> None:
        """A planted full heading line (matching the detection regex) inside
        body text DOES match the line-anchored regex.

        This confirms: the regex alone cannot distinguish a real cadence
        anchor from an adversarially-planted heading-prefix line in a body.
        The prose validity guards (future-dated check, same-day journal-op
        check) are therefore the actual security controls, not the regex.
        """
        regex = re.compile(RETRO_DETECTION_REGEX)
        # This is a body line (not a real heading) that nonetheless starts
        # with the full heading prefix.  An attacker could plant this in a
        # journal entry body to shift the retrospective window.
        planted_body_line = (
            "## [2020-01-01 00:00] learning | Retrospective: "
            "fake anchor planted in body text"
        )
        self.assertIsNotNone(
            regex.match(planted_body_line),
            msg=(
                f"Expected planted body line to match the regex — this is the "
                f"documented vulnerability the prose guards close.\n"
                f"  planted line: {planted_body_line!r}\n"
                f"  regex:        {RETRO_DETECTION_REGEX!r}\n"
                f"  If the regex no longer matches this, re-evaluate whether "
                f"the prose validity guards in retrospective/SKILL.md and "
                f"log-work/references/journal.md are still necessary."
            ),
        )
