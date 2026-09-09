"""Conformance suite for `review_findings.py`, the decision-review finding grammar.

Every expected result here is derived by hand from the decision that fixed the
grammar — never by calling the code under test. A test that computes its
expectation from the parser validates the parser against itself and passes on
a parser that is wrong in both places.

Every refusal case carries a PAIRED POSITIVE CONTROL: the same fixture with
the one offending detail repaired, asserted to succeed. An "it refused"
assertion with no control is a false green, because a fixture that would have
been refused for an unrelated reason refuses just as loudly.

Reads `crux/scripts/` and nothing else — no `bionic/` tree, no live review
report — so the suite passes unchanged against the crux-only staged artifact.

Stdlib only. Run:
  uv run python3 -m unittest discover -s crux/scripts/tests -p test_review_findings.py -v
"""

from __future__ import annotations

import importlib.util
import re
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    module = importlib.util.module_from_spec(spec)
    # Registered BEFORE execution: `dataclasses` resolves a frozen dataclass's
    # own module out of `sys.modules`, and an unregistered module fails there
    # rather than at the import.
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


rf = _load("review_findings_under_test", "review_findings.py")


# ── fixture builders ──────────────────────────────────────────────────────
#
# These compose report text. They call nothing in the module under test, so a
# fixture cannot inherit the parser's opinion about its own shape.

LIFECYCLE_FM = ('type: adr-review\ndate: {date}\n'
                'report_grammar: lifecycle\ndismissed: []')
LEGACY_FM = 'type: adr-review\ndate: {date}\ndismissed: []'


def summary_table(rows) -> str:
    """`rows` is a sequence of `(finding id, section)` pairs."""
    out = ["| finding id | section | objective | proposed act | size |",
           "|---|---|---|---|---|"]
    for fid, section in rows:
        out.append(f"| `{fid}` | {section} | OBJ-1 | write the thing | patch |")
    return "\n".join(out)


def record_table(rows) -> str:
    """`rows` is a sequence of `(source date, id, pass, event, locator)`."""
    out = ["| source report date | finding id | pass | event | locator |",
           "|---|---|---|---|---|"]
    for row in rows:
        out.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return "\n".join(out)


def entry(fid: str, *extra: str) -> str:
    head = [f"### `{fid}` — one line about the gap",
            "- **subject:** ADR-0001",
            "- **objective:** OBJ-1 — the goal"]
    return "\n".join(head + list(extra))


def line_of(body: str, needle: str) -> int:
    """The 1-based line number of the first line holding `needle`.

    Deliberately uses `str.split("\\n")` rather than the module's own
    `split_lines`, so a line-number expectation is derived independently of the
    splitter the parser uses.
    """
    for number, line in enumerate(body.split("\n"), start=1):
        if needle in line:
            return number
    raise AssertionError(f"fixture carries no line holding {needle!r}")


class ReviewFindingsTestCase(unittest.TestCase):
    def parse(self, *, date, body, frontmatter=None, line_offset=0):
        if frontmatter is None:
            frontmatter = LIFECYCLE_FM.format(date=date)
        return rf.parse_report(date=date, frontmatter=frontmatter, body=body,
                               line_offset=line_offset)

    def refusal(self, callable_, *args, **kwargs) -> str:
        with self.assertRaises(rf.ReviewFindingsError) as caught:
            callable_(*args, **kwargs)
        return caught.exception.problem


# ── V7 + outcome 7: the discriminator and the frozen legacy count ─────────

class DiscriminatorTests(ReviewFindingsTestCase):
    """Outcome 7. The `report_grammar` key, and what its absence means."""

    LEGACY_BODY = "\n".join([
        "# Decision review — 2026-09-08",
        "",
        "## Propose",
        "",
        entry("adr-review-alpha-one"),
        "",
        "## Repair",
        "",
        entry("adr-review-beta-two"),
        entry("adr-review-gamma-three"),
        "",
        "## Coverage",
        "",
        "The 2026-09-07 pass raised adr-review-delta-four and it now stands "
        "resolved, alongside adr-review-epsilon-five.",
    ])

    def test_legacy_count_is_the_token_set_not_the_definition_set(self):
        """V7. The frozen rule counts every token; the definitions are fewer.

        Derived by hand: the body carries five distinct `adr-review-` tokens —
        alpha-one, beta-two, gamma-three, delta-four, epsilon-five — and three
        `### ` definitions. A legacy report reports 5, and the SAME body read
        under the lifecycle grammar reports 3. The pair is the control: two
        counting rules that agreed on this body would prove nothing.
        """
        legacy = self.parse(date="2026-09-08", body=self.LEGACY_BODY,
                            frontmatter=LEGACY_FM.format(date="2026-09-08"))
        self.assertTrue(legacy.is_legacy)
        self.assertIsNone(legacy.grammar)
        self.assertEqual(legacy.raised, 5)
        self.assertEqual(
            legacy.legacy_ids,
            frozenset({"adr-review-alpha-one", "adr-review-beta-two",
                       "adr-review-gamma-three", "adr-review-delta-four",
                       "adr-review-epsilon-five"}))

        lifecycle = self.parse(date="2026-09-08", body=self.LEGACY_BODY)
        self.assertFalse(lifecycle.is_legacy)
        self.assertEqual(lifecycle.raised, 3)

    def test_legacy_coverage_prose_yields_no_record_and_no_note(self):
        """V7. Historical Coverage prose is never a confirmed lifecycle event."""
        legacy = self.parse(date="2026-09-08", body=self.LEGACY_BODY,
                            frontmatter=LEGACY_FM.format(date="2026-09-08"))
        self.assertEqual(legacy.records, ())
        self.assertEqual(legacy.notes, ())
        self.assertEqual(legacy.definitions, ())

    def test_the_legacy_token_regex_has_exactly_one_copy(self):
        """Outcome 7 freezes the count, so the pattern may not drift.

        It cannot drift if it exists once. `generate-reviews-index.py` used to
        carry its own `FINDING_TOKEN` beside this module's `LEGACY_TOKEN`, and
        a twin comparison over two copies can only find a divergence, never a
        shared error — the lesson `md_fences.py` was extracted for. So this row
        asserts the stronger property: the consumer defines no second copy, it
        imports this module, and the only spelling of the pattern in the
        regenerator is the import.
        """
        source = (SCRIPTS / "generate-reviews-index.py").read_text(encoding="utf-8")
        self.assertNotRegex(
            source, r"(?m)^FINDING_TOKEN\s*=",
            "generate-reviews-index.py must not redefine the legacy token regex")
        self.assertRegex(
            source, r"(?m)^import review_findings\b",
            "generate-reviews-index.py reads the grammar through this module")
        self.assertNotIn(
            rf.LEGACY_TOKEN.pattern, source,
            "the frozen legacy pattern is spelled once, in review_findings.py")
        # And the dead name is not kept alive in prose either. `FINDING_TOKEN`
        # names nothing in the tree, so a comment in THIS module that spells it
        # sends a reader looking for a constant that does not exist. The
        # incident belongs where it is explained — this test's own docstring —
        # never in the module the reader is trying to read.
        self.assertNotIn(
            "FINDING_TOKEN",
            (SCRIPTS / "review_findings.py").read_text(encoding="utf-8"),
            "review_findings.py names no dead FINDING_TOKEN constant")

    def test_absent_discriminator_after_the_boundary_is_refused(self):
        problem = self.refusal(
            self.parse, date="2026-09-09", body=self.LEGACY_BODY,
            frontmatter=LEGACY_FM.format(date="2026-09-09"))
        self.assertIn("report_grammar", problem)
        self.assertIn("2026-09-08", problem)

    def test_absent_discriminator_on_the_boundary_date_is_the_control(self):
        """The paired control: one day earlier, the same body reads as legacy."""
        report = self.parse(date="2026-09-08", body=self.LEGACY_BODY,
                            frontmatter=LEGACY_FM.format(date="2026-09-08"))
        self.assertTrue(report.is_legacy)
        self.assertEqual(report.raised, 5)

    def test_unrecognised_discriminator_value_is_refused(self):
        problem = self.refusal(
            self.parse, date="2026-09-10", body=self.LEGACY_BODY,
            frontmatter='type: adr-review\ndate: 2026-09-10\n'
                        'report_grammar: lifecycle-v2\ndismissed: []')
        self.assertIn("lifecycle-v2", problem)
        self.assertIn("report_grammar", problem)

    def test_recognised_discriminator_value_is_the_control(self):
        report = self.parse(date="2026-09-10", body=self.LEGACY_BODY)
        self.assertEqual(report.grammar, rf.LIFECYCLE)
        self.assertFalse(report.is_legacy)

    def test_a_date_outside_the_iso_grammar_is_refused(self):
        problem = self.refusal(self.parse, date="2026-9-9", body="# x")
        self.assertIn("2026-9-9", problem)
        self.assertIn("calendar date", problem)

    def test_an_iso_date_is_the_control(self):
        self.assertEqual(self.parse(date="2026-09-09", body="# x").date,
                         "2026-09-09")


# ── V1 + outcome 1: definition versus reference ──────────────────────────

class DefinitionTests(ReviewFindingsTestCase):
    """Outcome 1. What defines a finding, and what merely names one."""

    def test_a_definition_repeated_in_summary_and_coverage_counts_once(self):
        """V1. One id, three occurrences, one definition.

        Derived by hand: `adr-review-one-only` occurs in the summary table, in
        its `### ` heading, and in a lifecycle record under Coverage. Under
        outcome 1 exactly one of those is a definition, so `raised` is 1 — while
        the legacy token rule over the same body would answer 1 as well, which
        is why the paired assertion below adds a second id that occurs ONLY as
        a reference and moves the two rules apart.
        """
        body = "\n".join([
            "# Decision review — 2026-09-10",
            "",
            summary_table([("adr-review-one-only", "Repair")]),
            "",
            "## Repair",
            "",
            entry("adr-review-one-only"),
            "",
            "## Coverage",
            "",
            record_table([("2026-09-10", "`adr-review-one-only`", 1,
                           "re-verified", "crux/scripts/review_findings.py")]),
        ])
        report = self.parse(date="2026-09-10", body=body)
        self.assertEqual(report.raised, 1)
        self.assertEqual([d.finding_id for d in report.definitions],
                         ["adr-review-one-only"])
        self.assertEqual(report.summary_row_ids, ("adr-review-one-only",))
        rf.validate_structure(report)

    def test_a_heading_carrying_no_finding_id_is_refused(self):
        body = "\n".join([
            "# Decision review — 2026-09-10", "",
            "## Repair", "",
            "### A heading with no id at all",
        ])
        problem = self.refusal(self.parse, date="2026-09-10", body=body)
        self.assertIn("no finding id", problem)

    def test_a_heading_carrying_two_finding_ids_is_refused(self):
        body = "\n".join([
            "# Decision review — 2026-09-10", "",
            "## Repair", "",
            "### `adr-review-one` and `adr-review-two` together",
        ])
        problem = self.refusal(self.parse, date="2026-09-10", body=body)
        self.assertIn("2 finding ids", problem)

    def test_a_heading_carrying_one_finding_id_is_the_control(self):
        body = "\n".join([
            "# Decision review — 2026-09-10", "",
            "## Repair", "",
            "### `adr-review-one` on its own",
        ])
        report = self.parse(date="2026-09-10", body=body)
        self.assertEqual(report.raised, 1)

    def test_a_deeper_heading_inside_an_entry_defines_nothing(self):
        """Outcome 1: a `#### ` heading is neither a definition nor a refusal.

        The paired control below is the same two-id heading at `### `, which
        IS refused — so this row cannot pass by the heading being ignored for
        some unrelated reason.
        """
        body = "\n".join([
            "# Decision review — 2026-09-10", "",
            summary_table([("adr-review-outer", "Repair")]), "",
            "## Repair", "",
            entry("adr-review-outer"),
            "#### `adr-review-inner` and `adr-review-second` in a sub-heading",
        ])
        report = self.parse(date="2026-09-10", body=body)
        self.assertEqual([d.finding_id for d in report.definitions],
                         ["adr-review-outer"])
        rf.validate_structure(report)

        promoted = body.replace("#### `adr-review-inner`", "### `adr-review-inner`")
        problem = self.refusal(self.parse, date="2026-09-10", body=promoted)
        self.assertIn("2 finding ids", problem)

    def test_a_heading_outside_a_finding_section_defines_nothing(self):
        body = "\n".join([
            "# Decision review — 2026-09-10", "",
            "## Coverage", "",
            "### `adr-review-not-a-finding` — a coverage sub-heading",
        ])
        report = self.parse(date="2026-09-10", body=body)
        self.assertEqual(report.definitions, ())
        self.assertEqual(report.raised, 0)

    def test_one_id_defined_twice_in_one_report_is_refused(self):
        body = "\n".join([
            "# Decision review — 2026-09-10", "",
            "## Propose", "", entry("adr-review-twice"), "",
            "## Repair", "", entry("adr-review-twice"),
        ])
        problem = self.refusal(self.parse, date="2026-09-10", body=body)
        self.assertIn("adr-review-twice", problem)
        self.assertIn("defined twice", problem)

    def test_two_distinct_ids_in_one_report_are_the_control(self):
        body = "\n".join([
            "# Decision review — 2026-09-10", "",
            "## Propose", "", entry("adr-review-once"), "",
            "## Repair", "", entry("adr-review-other"),
        ])
        self.assertEqual(self.parse(date="2026-09-10", body=body).raised, 2)

    def test_one_id_defined_by_two_reports_is_refused(self):
        first = self.parse(date="2026-09-10", body="\n".join([
            "# a", "", "## Propose", "", entry("adr-review-shared")]))
        second = self.parse(date="2026-09-11", body="\n".join([
            "# b", "", "## Repair", "", entry("adr-review-shared")]))
        problem = self.refusal(rf.standing_by_finding, [first, second])
        self.assertIn("adr-review-shared", problem)
        self.assertIn("defined twice", problem)

    def test_two_reports_defining_distinct_ids_are_the_control(self):
        first = self.parse(date="2026-09-10", body="\n".join([
            "# a", "", "## Propose", "", entry("adr-review-first-one")]))
        second = self.parse(date="2026-09-11", body="\n".join([
            "# b", "", "## Repair", "", entry("adr-review-second-one")]))
        self.assertEqual(
            rf.standing_by_finding([first, second]),
            {"adr-review-first-one": "open", "adr-review-second-one": "open"})


# ── outcome 1: the summary-table postcondition ───────────────────────────

class SummaryTableTests(ReviewFindingsTestCase):

    def test_repeated_summary_row_ids_are_refused(self):
        body = "\n".join([
            "# Decision review — 2026-09-10", "",
            summary_table([("adr-review-dup", "Repair"),
                           ("adr-review-dup", "Propose")]), "",
            "## Repair", "", entry("adr-review-dup"),
        ])
        report = self.parse(date="2026-09-10", body=body)
        problem = self.refusal(rf.validate_structure, report)
        self.assertIn("pairwise distinct", problem)
        self.assertIn("adr-review-dup", problem)

    def test_equal_counts_with_unequal_sets_are_refused(self):
        """Outcome 1: equal counts alone do not satisfy the postcondition.

        Derived by hand: two summary rows, two definitions, and one id in each
        operand the other lacks. A count comparison passes this fixture; the
        set comparison the decision requires refuses it.
        """
        body = "\n".join([
            "# Decision review — 2026-09-10", "",
            summary_table([("adr-review-in-table", "Repair"),
                           ("adr-review-in-both", "Repair")]), "",
            "## Repair", "",
            entry("adr-review-in-both"), "",
            entry("adr-review-in-sections"),
        ])
        report = self.parse(date="2026-09-10", body=body)
        self.assertEqual(len(report.summary_row_ids), len(report.definitions))
        problem = self.refusal(rf.validate_structure, report)
        self.assertIn("adr-review-in-table", problem)
        self.assertIn("adr-review-in-sections", problem)

    def test_equal_sets_are_the_control(self):
        body = "\n".join([
            "# Decision review — 2026-09-10", "",
            summary_table([("adr-review-in-both", "Repair"),
                           ("adr-review-also-both", "Repair")]), "",
            "## Repair", "",
            entry("adr-review-in-both"), "",
            entry("adr-review-also-both"),
        ])
        self.assertIsNone(rf.validate_structure(self.parse(
            date="2026-09-10", body=body)))

    def test_a_summary_table_after_the_first_finding_section_is_refused(self):
        body = "\n".join([
            "# Decision review — 2026-09-10", "",
            "## Repair", "", entry("adr-review-late-table"), "",
            summary_table([("adr-review-late-table", "Repair")]),
        ])
        problem = self.refusal(self.parse, date="2026-09-10", body=body)
        self.assertIn("summary table", problem)

    def test_a_summary_table_before_the_first_section_is_the_control(self):
        body = "\n".join([
            "# Decision review — 2026-09-10", "",
            summary_table([("adr-review-early-table", "Repair")]), "",
            "## Repair", "", entry("adr-review-early-table"),
        ])
        report = self.parse(date="2026-09-10", body=body)
        self.assertEqual(report.summary_row_ids, ("adr-review-early-table",))

    def test_a_second_summary_table_is_refused(self):
        """One summary table, between the title and `## Propose`.

        The parser finds the table BY ITS HEADER ROW, so a second one silently
        appended its rows to the first table's id set and the set-equality
        postcondition then read a union nobody wrote.
        """
        table = summary_table([("adr-review-in-both", "Repair")])
        body = "\n".join([
            "# Decision review — 2026-09-10", "", table, "", table, "",
            "## Repair", "", entry("adr-review-in-both"),
        ])
        problem = self.refusal(self.parse, date="2026-09-10", body=body)
        self.assertIn("second summary table", problem)

    def test_one_summary_table_is_the_control(self):
        body = "\n".join([
            "# Decision review — 2026-09-10", "",
            summary_table([("adr-review-in-both", "Repair")]), "",
            "## Repair", "", entry("adr-review-in-both"),
        ])
        self.assertEqual(self.parse(date="2026-09-10", body=body)
                         .summary_row_ids, ("adr-review-in-both",))

    def test_a_summary_row_naming_no_finding_or_two_is_refused(self):
        """One row names one finding. Zero and two are each refused.

        A row with no id contributed nothing to the id set and passed the
        postcondition by being invisible; a row naming two contributed the
        first and dropped the second.
        """
        for cell, expect in (("no id at all", "no finding id"),
                             ("`adr-review-one` and `adr-review-two`",
                              "2 finding ids")):
            with self.subTest(cell=cell):
                body = "\n".join([
                    "# Decision review — 2026-09-10", "",
                    "| finding id | section | objective | proposed act | size |",
                    "|---|---|---|---|---|",
                    f"| {cell} | Repair | OBJ-1 | write the thing | patch |", "",
                    "## Repair", "", entry("adr-review-one"),
                ])
                problem = self.refusal(self.parse, date="2026-09-10", body=body)
                self.assertIn(expect, problem)
                self.assertIn("one row names one finding", problem)

    def test_a_summary_row_naming_exactly_one_finding_is_the_control(self):
        body = "\n".join([
            "# Decision review — 2026-09-10", "",
            summary_table([("adr-review-one", "Repair")]), "",
            "## Repair", "", entry("adr-review-one"),
        ])
        self.assertEqual(self.parse(date="2026-09-10", body=body)
                         .summary_row_ids, ("adr-review-one",))

    def test_a_row_with_no_trailing_pipe_is_still_a_row(self):
        """`_cells` accepts a row that opens with `|` and does not close with one.

        Markdown renders both, so a report whose author dropped the closing
        pipe must parse to the same id set rather than losing the row from the
        postcondition's operand.
        """
        body = "\n".join([
            "# Decision review — 2026-09-10", "",
            "| finding id | section | objective | proposed act | size |",
            "|---|---|---|---|---|",
            "| `adr-review-one` | Repair | OBJ-1 | write the thing | patch", "",
            "## Repair", "", entry("adr-review-one"),
        ])
        report = self.parse(date="2026-09-10", body=body)
        self.assertEqual(report.summary_row_ids, ("adr-review-one",))
        self.assertIsNone(rf.validate_structure(report))

    def test_an_id_defined_but_absent_from_the_summary_table_is_refused(self):
        """The MISSING-ONLY arc of the set-inequality refusal.

        `test_equal_counts_with_unequal_sets_are_refused` drives both arcs at
        once. This one carries an empty `extra`, so it fails if the refusal
        ever reads only the extra set.
        """
        body = "\n".join([
            "# Decision review — 2026-09-10", "",
            summary_table([("adr-review-in-both", "Repair")]), "",
            "## Repair", "",
            entry("adr-review-in-both"), "",
            entry("adr-review-only-defined"),
        ])
        problem = self.refusal(rf.validate_structure,
                               self.parse(date="2026-09-10", body=body))
        self.assertIn("adr-review-only-defined", problem)
        self.assertIn("summary table", problem)

    def test_legacy_reports_skip_the_postcondition(self):
        report = self.parse(date="2026-09-08",
                            frontmatter=LEGACY_FM.format(date="2026-09-08"),
                            body="# a\n\n## Repair\n\n### adr-review-legacy-one\n")
        self.assertIsNone(rf.validate_structure(report))


# ── V5: fences define nothing and record nothing ─────────────────────────

class FenceTests(ReviewFindingsTestCase):

    def test_a_fenced_example_creates_no_definition_no_record_no_note(self):
        """V5. Everything inside the fence is quoted material.

        The paired control is the same three lines unfenced, which DO produce
        one definition, one record and one note.
        """
        inner = [
            "### `adr-review-fenced-def` — an example heading",
            record_table([("2026-09-10", "`adr-review-real-one`", 2,
                           "resolved", "crux/scripts/review_findings.py")]),
            "- **resolved, pass 2** — 2026-09-10 — an example note",
        ]
        fenced = "\n".join([
            "# Decision review — 2026-09-10", "",
            "## Repair", "", entry("adr-review-real-one"), "",
            "## Coverage", "",
            "```markdown",
            *inner,
            "```",
        ])
        report = self.parse(date="2026-09-10", body=fenced)
        self.assertEqual([d.finding_id for d in report.definitions],
                         ["adr-review-real-one"])
        self.assertEqual(report.records, ())
        self.assertEqual(report.notes, ())

        unfenced = "\n".join([
            "# Decision review — 2026-09-10", "",
            "## Repair", "", entry("adr-review-real-one"),
            "- **resolved, pass 2** — 2026-09-10 — the real note", "",
            "## Coverage", "",
            record_table([("2026-09-10", "`adr-review-real-one`", 2,
                           "resolved", "crux/scripts/review_findings.py")]),
        ])
        control = self.parse(date="2026-09-10", body=unfenced)
        self.assertEqual(len(control.records), 1)
        self.assertEqual(len(control.notes), 1)

    def test_a_tilde_fence_closes_only_on_tildes(self):
        body = "\n".join([
            "# Decision review — 2026-09-10", "",
            "## Repair", "", entry("adr-review-outside"), "",
            "## Coverage", "",
            "~~~text",
            "```",
            record_table([("2026-09-10", "`adr-review-outside`", 1,
                           "disputed", "crux/scripts/review_findings.py")]),
            "~~~",
        ])
        report = self.parse(date="2026-09-10", body=body)
        self.assertEqual(report.records, ())


# ── outcomes 2 and 5: record fields ──────────────────────────────────────

class RecordFieldTests(ReviewFindingsTestCase):

    def coverage(self, rows, *, date="2026-09-10", fid="adr-review-subject-one"):
        return "\n".join([
            "# Decision review — " + date, "",
            summary_table([(fid, "Repair")]), "",
            "## Repair", "", entry(fid), "",
            "## Coverage", "", record_table(rows),
        ])

    def test_a_well_formed_record_parses_into_its_five_fields(self):
        body = self.coverage([("2026-09-10", "`adr-review-subject-one`", 3,
                               "disputed", "bionic/adrs/ADR-0106.md")])
        record = self.parse(date="2026-09-10", body=body).records[0]
        self.assertEqual(record.source_date, "2026-09-10")
        self.assertEqual(record.finding_id, "adr-review-subject-one")
        self.assertEqual(record.pass_ordinal, 3)
        self.assertEqual(record.event, "disputed")
        self.assertEqual(record.locator, "bionic/adrs/ADR-0106.md")
        self.assertEqual(record.report_date, "2026-09-10")

    def test_the_event_raised_is_refused(self):
        body = self.coverage([("2026-09-10", "`adr-review-subject-one`", 1,
                               "raised", "bionic/adrs/ADR-0106.md")])
        problem = self.refusal(self.parse, date="2026-09-10", body=body)
        self.assertIn("raised", problem)
        self.assertIn("never written as a record", problem)

    def test_an_unknown_event_is_refused(self):
        body = self.coverage([("2026-09-10", "`adr-review-subject-one`", 1,
                               "reopened", "bionic/adrs/ADR-0106.md")])
        problem = self.refusal(self.parse, date="2026-09-10", body=body)
        self.assertIn("reopened", problem)

    def test_each_admitted_event_is_the_control(self):
        for kind in ("re-verified", "resolved", "disputed"):
            with self.subTest(kind=kind):
                body = self.coverage([("2026-09-10", "`adr-review-subject-one`",
                                       1, kind, "bionic/adrs/ADR-0106.md")])
                record = self.parse(date="2026-09-10", body=body).records[0]
                self.assertEqual(record.event, kind)

    def test_a_bare_slug_finding_id_is_refused(self):
        body = self.coverage([("2026-09-10", "`subject-one`", 1,
                               "resolved", "bionic/adrs/ADR-0106.md")])
        problem = self.refusal(self.parse, date="2026-09-10", body=body)
        self.assertIn("subject-one", problem)
        self.assertIn("full form", problem)

    def test_a_non_calendar_source_date_is_refused(self):
        body = self.coverage([("2026-02-30", "`adr-review-subject-one`", 1,
                               "resolved", "bionic/adrs/ADR-0106.md")])
        problem = self.refusal(self.parse, date="2026-09-10", body=body)
        self.assertIn("2026-02-30", problem)
        self.assertIn("calendar date", problem)

    def test_a_zero_pass_ordinal_is_refused(self):
        # The message names the grammar rather than "a positive integer": a
        # pass ordinal is 1 to 4 ASCII digits with no leading zero, and a
        # reader who is told "positive integer" cannot tell why `01` refuses.
        body = self.coverage([("2026-09-10", "`adr-review-subject-one`", 0,
                               "resolved", "bionic/adrs/ADR-0106.md")])
        problem = self.refusal(self.parse, date="2026-09-10", body=body)
        self.assertIn("pass ordinal", problem)
        self.assertIn("no leading zero", problem)

    def test_a_leading_zero_pass_ordinal_is_refused(self):
        body = self.coverage([("2026-09-10", "`adr-review-subject-one`", "01",
                               "resolved", "bionic/adrs/ADR-0106.md")])
        self.assertIn("pass ordinal",
                      self.refusal(self.parse, date="2026-09-10", body=body))

    def test_a_non_numeric_pass_ordinal_is_refused(self):
        body = self.coverage([("2026-09-10", "`adr-review-subject-one`",
                               "second", "resolved", "bionic/adrs/ADR-0106.md")])
        problem = self.refusal(self.parse, date="2026-09-10", body=body)
        self.assertIn("second", problem)
        self.assertIn("pass ordinal", problem)

    def test_a_short_row_is_refused_rather_than_padded(self):
        body = "\n".join([
            "# Decision review — 2026-09-10", "",
            "## Coverage", "",
            "| source report date | finding id | pass | event | locator |",
            "|---|---|---|---|---|",
            "| 2026-09-10 | `adr-review-subject-one` | 1 |",
        ])
        problem = self.refusal(self.parse, date="2026-09-10", body=body)
        self.assertIn("5 cells", problem)

    def test_a_locator_carrying_a_backtick_is_refused(self):
        body = self.coverage([("2026-09-10", "`adr-review-subject-one`", 1,
                               "resolved", "`bionic/adrs/ADR-0106.md`")])
        problem = self.refusal(self.parse, date="2026-09-10", body=body)
        self.assertIn("locator", problem)

    def test_a_locator_carrying_a_wiki_link_is_refused(self):
        body = self.coverage([("2026-09-10", "`adr-review-subject-one`", 1,
                               "resolved", "[[adrs/ADR-0106]]")])
        problem = self.refusal(self.parse, date="2026-09-10", body=body)
        self.assertIn("locator", problem)

    def test_a_locator_carrying_a_footnote_marker_is_refused(self):
        body = self.coverage([("2026-09-10", "`adr-review-subject-one`", 1,
                               "resolved", "see the note[^rules]")])
        problem = self.refusal(self.parse, date="2026-09-10", body=body)
        self.assertIn("locator", problem)

    def test_a_locator_past_the_length_bound_is_refused_never_truncated(self):
        """Outcome 2: out of grammar is refused, never truncated into admission.

        Derived by hand: the bound is 200 characters, so a 201-character
        locator is out of grammar and a 200-character one is in it. The control
        below proves the boundary is where the module says it is, so this row
        cannot pass on a parser that refuses every long locator.
        """
        too_long = "a" * 201
        body = self.coverage([("2026-09-10", "`adr-review-subject-one`", 1,
                               "resolved", too_long)])
        problem = self.refusal(self.parse, date="2026-09-10", body=body)
        self.assertIn("locator", problem)

        at_bound = "b" * 200
        control = self.coverage([("2026-09-10", "`adr-review-subject-one`", 1,
                                  "resolved", at_bound)])
        record = self.parse(date="2026-09-10", body=control).records[0]
        self.assertEqual(record.locator, at_bound)

    def test_an_empty_locator_is_refused(self):
        body = self.coverage([("2026-09-10", "`adr-review-subject-one`", 1,
                               "resolved", "")])
        problem = self.refusal(self.parse, date="2026-09-10", body=body)
        self.assertIn("locator", problem)


# ── outcome 3: the two Coverage tables never merge ───────────────────────

class CoverageTableTests(ReviewFindingsTestCase):

    GOAL_MATRIX = "\n".join([
        "| objective | signals that measured it | domains that measured it |",
        "|---|---|---|",
        "| OBJ-1 | dormancy | decision-review |",
    ])

    def test_the_goal_matrix_beside_the_record_table_yields_one_record(self):
        """Outcome 3: identified by header row, never by position."""
        body = "\n".join([
            "# Decision review — 2026-09-10", "",
            summary_table([("adr-review-subject-one", "Repair")]), "",
            "## Repair", "", entry("adr-review-subject-one"), "",
            "## Coverage", "",
            self.GOAL_MATRIX, "",
            record_table([("2026-09-10", "`adr-review-subject-one`", 1,
                           "re-verified", "crux/scripts/review_findings.py")]),
        ])
        report = self.parse(date="2026-09-10", body=body)
        self.assertEqual(len(report.records), 1)
        self.assertEqual(report.records[0].event, "re-verified")

    def test_the_goal_matrix_alone_yields_no_record(self):
        body = "\n".join([
            "# Decision review — 2026-09-10", "",
            "## Coverage", "", self.GOAL_MATRIX,
        ])
        self.assertEqual(self.parse(date="2026-09-10", body=body).records, ())

    def test_a_second_record_table_is_refused(self):
        rows = [("2026-09-10", "`adr-review-subject-one`", 1, "re-verified",
                 "crux/scripts/review_findings.py")]
        body = "\n".join([
            "# Decision review — 2026-09-10", "",
            "## Coverage", "", record_table(rows), "", record_table(rows),
        ])
        problem = self.refusal(self.parse, date="2026-09-10", body=body)
        self.assertIn("one table", problem)

    def test_one_record_table_is_the_control(self):
        rows = [("2026-09-10", "`adr-review-subject-one`", 1, "re-verified",
                 "crux/scripts/review_findings.py")]
        body = "\n".join([
            "# Decision review — 2026-09-10", "",
            "## Coverage", "", record_table(rows),
        ])
        self.assertEqual(len(self.parse(date="2026-09-10", body=body).records), 1)

    def test_a_record_table_outside_coverage_is_refused(self):
        rows = [("2026-09-10", "`adr-review-subject-one`", 1, "re-verified",
                 "crux/scripts/review_findings.py")]
        body = "\n".join([
            "# Decision review — 2026-09-10", "",
            "## Repair", "", entry("adr-review-subject-one"), "",
            record_table(rows),
        ])
        problem = self.refusal(self.parse, date="2026-09-10", body=body)
        self.assertIn("Coverage", problem)


# ── outcome 3: note pairing ──────────────────────────────────────────────

class NotePairingTests(ReviewFindingsTestCase):

    PROSE = "the owner reworded the clause on the fourteenth"

    def report_body(self, *, note_kind, note_pass, record_rows):
        return "\n".join([
            "# Decision review — 2026-09-11", "",
            summary_table([("adr-review-noted-one", "Repair")]), "",
            "## Repair", "",
            entry("adr-review-noted-one"),
            f"- **{note_kind}, pass {note_pass}** — 2026-09-11 — {self.PROSE}", "",
            "## Coverage", "", record_table(record_rows),
        ])

    def test_a_paired_note_validates(self):
        body = self.report_body(
            note_kind="disputed", note_pass=2,
            record_rows=[("2026-09-11", "`adr-review-noted-one`", 2,
                          "disputed", "bionic/adrs/ADR-0106.md")])
        report = self.parse(date="2026-09-11", body=body)
        self.assertEqual([(n.finding_id, n.kind, n.pass_ordinal)
                          for n in report.notes],
                         [("adr-review-noted-one", "disputed", 2)])
        self.assertIsNone(rf.validate_structure(report))

    def test_a_note_borrowing_an_earlier_pass_record_is_refused(self):
        """Outcome 3: the pass is the note's own writing pass."""
        body = self.report_body(
            note_kind="disputed", note_pass=2,
            record_rows=[("2026-09-11", "`adr-review-noted-one`", 1,
                          "disputed", "bionic/adrs/ADR-0106.md")])
        report = self.parse(date="2026-09-11", body=body)
        problem = self.refusal(rf.validate_structure, report)
        self.assertIn("adr-review-noted-one", problem)

    def test_a_note_of_a_different_kind_than_its_record_is_refused(self):
        body = self.report_body(
            note_kind="disputed", note_pass=2,
            record_rows=[("2026-09-11", "`adr-review-noted-one`", 2,
                          "re-verified", "bionic/adrs/ADR-0106.md")])
        report = self.parse(date="2026-09-11", body=body)
        problem = self.refusal(rf.validate_structure, report)
        self.assertIn("disputed", problem)

    def test_the_pairing_refusal_names_the_id_and_line_and_hides_the_prose(self):
        """Outcome 2: a pairing refusal renders the id and the line, never prose.

        The line number is derived independently — the fixture is searched with
        `str.split` for the note's own marker text.
        """
        body = self.report_body(
            note_kind="re-verified", note_pass=1,
            record_rows=[("2026-09-11", "`adr-review-noted-one`", 4,
                          "re-verified", "bionic/adrs/ADR-0106.md")])
        expected_line = line_of(body, "**re-verified, pass 1**")
        report = self.parse(date="2026-09-11", body=body)
        problem = self.refusal(rf.validate_structure, report)
        self.assertIn("adr-review-noted-one", problem)
        self.assertIn(str(expected_line), problem)
        self.assertNotIn(self.PROSE, problem)
        self.assertNotIn("owner reworded", problem)

    def test_the_line_offset_moves_the_reported_line(self):
        """W2 reads a file, so the module takes the frontmatter's line count."""
        body = self.report_body(
            note_kind="re-verified", note_pass=1,
            record_rows=[("2026-09-11", "`adr-review-noted-one`", 4,
                          "re-verified", "bionic/adrs/ADR-0106.md")])
        expected_line = line_of(body, "**re-verified, pass 1**") + 7
        report = self.parse(date="2026-09-11", body=body, line_offset=7)
        problem = self.refusal(rf.validate_structure, report)
        self.assertIn(str(expected_line), problem)

    def test_a_note_outside_any_entry_is_not_a_note(self):
        body = "\n".join([
            "# Decision review — 2026-09-11", "",
            "## Coverage", "",
            "- **disputed, pass 1** — 2026-09-11 — prose outside every entry",
        ])
        report = self.parse(date="2026-09-11", body=body)
        self.assertEqual(report.notes, ())
        self.assertIsNone(rf.validate_structure(report))

    def test_a_resolved_note_needs_no_paired_record(self):
        """ADR-0106 outcome 3 binds the disputed and re-verified notes alone."""
        body = self.report_body(note_kind="resolved", note_pass=1,
                                record_rows=[])
        report = self.parse(date="2026-09-11", body=body)
        self.assertEqual(len(report.notes), 1)
        self.assertIsNone(rf.validate_structure(report))


# ── V2, V3, V4 + outcome 5: ordering and standing ────────────────────────

class StandingTests(ReviewFindingsTestCase):

    def definition_report(self, date, fid):
        body = "\n".join([
            f"# Decision review — {date}", "",
            summary_table([(fid, "Repair")]), "",
            "## Repair", "", entry(fid),
        ])
        return self.parse(date=date, body=body)

    def record_report(self, date, rows, *, own=()):
        pieces = ["# Decision review — " + date, ""]
        if own:
            pieces += [summary_table([(fid, "Repair") for fid in own]), "",
                       "## Repair", ""]
            pieces += [entry(fid) for fid in own]
        pieces += ["", "## Coverage", "", record_table(rows)]
        return self.parse(date=date, body="\n".join(pieces))

    def test_a_definition_with_no_record_is_open(self):
        report = self.definition_report("2026-09-10", "adr-review-alone-one")
        self.assertEqual(rf.standing_by_finding([report]),
                         {"adr-review-alone-one": "open"})

    def test_a_later_report_resolves_an_earlier_finding_and_raises_none(self):
        """V2. The recording report's own `raised` counts its definitions only.

        Derived by hand: the 2026-09-11 report defines nothing and carries one
        record naming the 2026-09-10 finding, so its `raised` is 0 and the
        earlier finding stands resolved.
        """
        first = self.definition_report("2026-09-10", "adr-review-carried-one")
        second = self.record_report("2026-09-11", [
            ("2026-09-10", "`adr-review-carried-one`", 1, "resolved",
             "crux/scripts/review_findings.py")])
        self.assertEqual(second.raised, 0)
        self.assertEqual(rf.standing_by_finding([first, second]),
                         {"adr-review-carried-one": "resolved"})
        self.assertEqual(rf.events_elsewhere(second, [first, second]), 1)
        self.assertEqual(rf.events_elsewhere(first, [first, second]), 0)

    def test_a_dispute_stays_disputed_through_a_later_re_verification(self):
        """V3. Re-verification clears nothing."""
        first = self.definition_report("2026-09-10", "adr-review-argued-one")
        second = self.record_report("2026-09-11", [
            ("2026-09-10", "`adr-review-argued-one`", 1, "disputed",
             "crux/skills/review-decisions/SKILL.md")])
        third = self.record_report("2026-09-12", [
            ("2026-09-10", "`adr-review-argued-one`", 1, "re-verified",
             "crux/skills/review-decisions/SKILL.md")])
        self.assertEqual(rf.standing_by_finding([first, second, third]),
                         {"adr-review-argued-one": "disputed"})

    def test_a_resolution_clears_a_dispute(self):
        first = self.definition_report("2026-09-10", "adr-review-argued-two")
        second = self.record_report("2026-09-11", [
            ("2026-09-10", "`adr-review-argued-two`", 1, "disputed",
             "crux/skills/review-decisions/SKILL.md")])
        third = self.record_report("2026-09-12", [
            ("2026-09-10", "`adr-review-argued-two`", 1, "resolved",
             "crux/skills/review-decisions/SKILL.md")])
        self.assertEqual(rf.standing_by_finding([first, second, third]),
                         {"adr-review-argued-two": "resolved"})

    def test_a_re_verification_leaves_an_open_finding_open(self):
        first = self.definition_report("2026-09-10", "adr-review-checked-one")
        second = self.record_report("2026-09-11", [
            ("2026-09-10", "`adr-review-checked-one`", 1, "re-verified",
             "crux/scripts/review_findings.py")])
        self.assertEqual(rf.standing_by_finding([first, second]),
                         {"adr-review-checked-one": "open"})

    def test_a_record_after_a_resolution_is_refused(self):
        first = self.definition_report("2026-09-10", "adr-review-closed-one")
        second = self.record_report("2026-09-11", [
            ("2026-09-10", "`adr-review-closed-one`", 1, "resolved",
             "crux/scripts/review_findings.py")])
        third = self.record_report("2026-09-12", [
            ("2026-09-10", "`adr-review-closed-one`", 1, "disputed",
             "crux/scripts/review_findings.py")])
        problem = self.refusal(rf.standing_by_finding, [first, second, third])
        self.assertIn("adr-review-closed-one", problem)
        self.assertIn("closed", problem)

    def test_the_same_two_records_in_the_opposite_order_are_the_control(self):
        """The refusal above is about ordering, not about carrying two records."""
        first = self.definition_report("2026-09-10", "adr-review-closed-two")
        second = self.record_report("2026-09-11", [
            ("2026-09-10", "`adr-review-closed-two`", 1, "disputed",
             "crux/scripts/review_findings.py")])
        third = self.record_report("2026-09-12", [
            ("2026-09-10", "`adr-review-closed-two`", 1, "resolved",
             "crux/scripts/review_findings.py")])
        self.assertEqual(rf.standing_by_finding([first, second, third]),
                         {"adr-review-closed-two": "resolved"})

    def test_two_records_for_one_finding_from_one_pass_are_refused(self):
        first = self.definition_report("2026-09-10", "adr-review-twice-one")
        second = self.record_report("2026-09-11", [
            ("2026-09-10", "`adr-review-twice-one`", 2, "re-verified",
             "crux/scripts/review_findings.py"),
            ("2026-09-10", "`adr-review-twice-one`", 2, "disputed",
             "crux/scripts/review_findings.py")])
        problem = self.refusal(rf.standing_by_finding, [first, second])
        self.assertIn("adr-review-twice-one", problem)
        self.assertIn("pass 2", problem)

    def test_two_records_from_two_passes_are_the_control(self):
        first = self.definition_report("2026-09-10", "adr-review-twice-two")
        second = self.record_report("2026-09-11", [
            ("2026-09-10", "`adr-review-twice-two`", 2, "re-verified",
             "crux/scripts/review_findings.py"),
            ("2026-09-10", "`adr-review-twice-two`", 3, "disputed",
             "crux/scripts/review_findings.py")])
        self.assertEqual(rf.standing_by_finding([first, second]),
                         {"adr-review-twice-two": "disputed"})

    def test_a_record_predating_its_definition_is_refused(self):
        later = self.definition_report("2026-09-12", "adr-review-future-one")
        earlier = self.record_report("2026-09-11", [
            ("2026-09-12", "`adr-review-future-one`", 1, "resolved",
             "crux/scripts/review_findings.py")])
        problem = self.refusal(rf.standing_by_finding, [later, earlier])
        self.assertIn("adr-review-future-one", problem)
        self.assertIn("predates", problem)

    def test_a_same_date_record_is_ordered_after_its_definition(self):
        """V4/outcome 5: a definition precedes every record in its own report.

        Pass 1 records against a finding the same report defines are admitted
        whatever the pass ordinal, so this control also covers pass 1.
        """
        body = "\n".join([
            "# Decision review — 2026-09-12", "",
            summary_table([("adr-review-same-day", "Repair")]), "",
            "## Repair", "", entry("adr-review-same-day"), "",
            "## Coverage", "",
            record_table([("2026-09-12", "`adr-review-same-day`", 1, "disputed",
                           "crux/scripts/review_findings.py")]),
        ])
        report = self.parse(date="2026-09-12", body=body)
        self.assertEqual(rf.standing_by_finding([report]),
                         {"adr-review-same-day": "disputed"})

    def test_a_record_naming_no_definition_is_refused(self):
        report = self.record_report("2026-09-11", [
            ("2026-09-10", "`adr-review-nowhere-one`", 1, "resolved",
             "crux/scripts/review_findings.py")])
        problem = self.refusal(rf.standing_by_finding, [report])
        self.assertIn("adr-review-nowhere-one", problem)
        self.assertIn("no definition", problem)

    def test_a_record_naming_the_wrong_date_is_refused(self):
        """The definition exists — on another date. The date is part of identity."""
        first = self.definition_report("2026-09-10", "adr-review-misdated-one")
        second = self.record_report("2026-09-12", [
            ("2026-09-11", "`adr-review-misdated-one`", 1, "resolved",
             "crux/scripts/review_findings.py")])
        problem = self.refusal(rf.standing_by_finding, [first, second])
        self.assertIn("2026-09-11", problem)

        control = self.record_report("2026-09-12", [
            ("2026-09-10", "`adr-review-misdated-one`", 1, "resolved",
             "crux/scripts/review_findings.py")])
        self.assertEqual(rf.standing_by_finding([first, control]),
                         {"adr-review-misdated-one": "resolved"})

    def test_a_legacy_definition_is_unknown_and_stays_unknown(self):
        legacy = self.parse(
            date="2026-09-08", frontmatter=LEGACY_FM.format(date="2026-09-08"),
            body="# a\n\n## Repair\n\n### `adr-review-old-one` — a gap\n")
        later = self.record_report("2026-09-11", [
            ("2026-09-08", "`adr-review-old-one`", 1, "resolved",
             "crux/scripts/review_findings.py")])
        self.assertEqual(rf.standing_by_finding([legacy, later]),
                         {"adr-review-old-one": "unknown"})
        self.assertEqual(rf.events_elsewhere(later, [legacy, later]), 1)

    def test_standing_is_independent_of_the_order_the_reports_arrive_in(self):
        """V8's determinism leg, at the module's own level."""
        first = self.definition_report("2026-09-10", "adr-review-order-one")
        second = self.record_report("2026-09-11", [
            ("2026-09-10", "`adr-review-order-one`", 1, "disputed",
             "crux/scripts/review_findings.py")])
        third = self.record_report("2026-09-12", [
            ("2026-09-10", "`adr-review-order-one`", 1, "resolved",
             "crux/scripts/review_findings.py")])
        forwards = rf.standing_by_finding([first, second, third])
        backwards = rf.standing_by_finding([third, second, first])
        self.assertEqual(forwards, {"adr-review-order-one": "resolved"})
        self.assertEqual(forwards, backwards)


# ── outcome 5: the injected locator-existence probe ──────────────────────

class LocatorExistenceTests(ReviewFindingsTestCase):

    def reports(self, event="resolved"):
        body = "\n".join([
            "# Decision review — 2026-09-10", "",
            summary_table([("adr-review-probed-one", "Repair")]), "",
            "## Repair", "", entry("adr-review-probed-one"), "",
            "## Coverage", "",
            record_table([("2026-09-10", "`adr-review-probed-one`", 1, event,
                           "crux/scripts/does-not-exist.py")]),
        ])
        return [self.parse(date="2026-09-10", body=body)]

    def test_a_resolved_locator_that_does_not_exist_is_refused(self):
        problem = self.refusal(rf.standing_by_finding, self.reports(),
                               locator_exists=lambda locator: False)
        self.assertIn("crux/scripts/does-not-exist.py", problem)

    def test_a_resolved_locator_that_exists_is_the_control(self):
        self.assertEqual(
            rf.standing_by_finding(self.reports(),
                                   locator_exists=lambda locator: True),
            {"adr-review-probed-one": "resolved"})

    def test_no_probe_skips_the_existence_check(self):
        self.assertEqual(rf.standing_by_finding(self.reports()),
                         {"adr-review-probed-one": "resolved"})

    def test_the_probe_is_asked_only_about_resolved_records(self):
        asked = []

        def probe(locator):
            asked.append(locator)
            return False

        self.assertEqual(
            rf.standing_by_finding(self.reports("disputed"), locator_exists=probe),
            {"adr-review-probed-one": "disputed"})
        self.assertEqual(asked, [])

        # Control: the same probe IS asked about a `resolved` record.
        with self.assertRaises(rf.ReviewFindingsError):
            rf.standing_by_finding(self.reports("resolved"), locator_exists=probe)
        self.assertEqual(asked, ["crux/scripts/does-not-exist.py"])


# ── outcome 6: the per-report standing counts ────────────────────────────

class ReportStandingTests(ReviewFindingsTestCase):

    def test_a_legacy_report_carries_its_frozen_count_as_unknown(self):
        body = ("# a\n\n## Repair\n\n### `adr-review-l-one` — a\n\n"
                "### `adr-review-l-two` — b\n\nAlso adr-review-l-three.\n")
        legacy = self.parse(date="2026-09-08", body=body,
                            frontmatter=LEGACY_FM.format(date="2026-09-08"))
        self.assertEqual(legacy.raised, 3)
        self.assertEqual(rf.report_standing(legacy, {}), {"unknown": 3})

    def test_a_lifecycle_report_counts_its_own_findings_per_state(self):
        """Derived by hand: three definitions, one resolved, two open."""
        body = "\n".join([
            "# Decision review — 2026-09-10", "",
            summary_table([("adr-review-c-one", "Repair"),
                           ("adr-review-c-two", "Repair"),
                           ("adr-review-c-three", "Repair")]), "",
            "## Repair", "",
            entry("adr-review-c-one"), "",
            entry("adr-review-c-two"), "",
            entry("adr-review-c-three"), "",
            "## Coverage", "",
            record_table([("2026-09-10", "`adr-review-c-two`", 1, "resolved",
                           "crux/scripts/review_findings.py")]),
        ])
        report = self.parse(date="2026-09-10", body=body)
        standing = rf.standing_by_finding([report])
        self.assertEqual(standing, {"adr-review-c-one": "open",
                                    "adr-review-c-two": "resolved",
                                    "adr-review-c-three": "open"})
        self.assertEqual(rf.report_standing(report, standing),
                         {"open": 2, "resolved": 1})

    def test_a_later_report_event_is_not_projected_onto_the_legacy_row(self):
        """Outcome 6: the legacy row's cells do not move."""
        legacy = self.parse(
            date="2026-09-08", frontmatter=LEGACY_FM.format(date="2026-09-08"),
            body="# a\n\n## Repair\n\n### `adr-review-frozen-one` — a gap\n")
        later_body = "\n".join([
            "# Decision review — 2026-09-11", "",
            "## Coverage", "",
            record_table([("2026-09-08", "`adr-review-frozen-one`", 1,
                           "resolved", "crux/scripts/review_findings.py")]),
        ])
        later = self.parse(date="2026-09-11", body=later_body)
        standing = rf.standing_by_finding([legacy, later])
        self.assertEqual(rf.report_standing(legacy, standing), {"unknown": 1})
        self.assertEqual(rf.report_standing(later, standing), {})
        self.assertEqual(rf.events_elsewhere(later, [legacy, later]), 1)


# ── V4: two passes on one date ───────────────────────────────────────────

class TwoPassTests(ReviewFindingsTestCase):

    def test_a_second_pass_adds_a_definition_and_a_record_and_keeps_the_first(self):
        """V4. Derived by hand: two definitions, one record, standing open and
        disputed. The record names the first pass's finding, so it is a
        follow-up event rather than a third definition."""
        body = "\n".join([
            "# Decision review — 2026-09-13", "",
            summary_table([("adr-review-pass-one-gap", "Repair"),
                           ("adr-review-pass-two-gap", "Propose")]), "",
            "## Propose", "",
            entry("adr-review-pass-two-gap"), "",
            "## Repair", "",
            entry("adr-review-pass-one-gap",
                  "- **disputed, pass 2** — 2026-09-13 — the second pass disputes it"),
            "",
            "## Coverage", "",
            record_table([("2026-09-13", "`adr-review-pass-one-gap`", 2,
                           "disputed", "bionic/adrs/ADR-0106.md")]),
        ])
        report = self.parse(date="2026-09-13", body=body)
        self.assertEqual(report.raised, 2)
        rf.validate_structure(report)
        standing = rf.standing_by_finding([report])
        self.assertEqual(standing, {"adr-review-pass-one-gap": "disputed",
                                    "adr-review-pass-two-gap": "open"})
        self.assertEqual(rf.report_standing(report, standing),
                         {"disputed": 1, "open": 1})
        self.assertEqual(rf.events_elsewhere(report, [report]), 0)


# ── V6: every refusal names the problem ──────────────────────────────────

class DiagnosticTests(ReviewFindingsTestCase):

    def test_every_refusal_carries_a_problem_string(self):
        error = rf.ReviewFindingsError("the problem, stated")
        self.assertEqual(error.problem, "the problem, stated")
        self.assertIn("the problem, stated", str(error))

    def test_a_hostile_value_is_bounded_and_redacted_in_the_refusal(self):
        """Outcome 2: every refused parsed value renders through `redact`.

        Derived by hand: the event cell carries 400 characters and a control
        character, so the refusal must show neither the raw newline nor the
        full length. The paired control below is a short printable event value,
        whose refusal quotes it whole.
        """
        hostile = "x" * 400 + "\x07"
        body = "\n".join([
            "# Decision review — 2026-09-10", "",
            "## Coverage", "",
            "| source report date | finding id | pass | event | locator |",
            "|---|---|---|---|---|",
            f"| 2026-09-10 | `adr-review-h-one` | 1 | {hostile} | a/path.md |",
        ])
        problem = self.refusal(self.parse, date="2026-09-10", body=body)
        self.assertNotIn("\x07", problem)
        self.assertLess(len(problem), 600)
        self.assertIn("truncated from", problem)

        control_body = body.replace(hostile, "reopened")
        control = self.refusal(self.parse, date="2026-09-10", body=control_body)
        self.assertIn("reopened", control)
        self.assertNotIn("truncated from", control)


# ── [SECURITY:S1]: every rendered value is BOUNDED, not merely redacted ───

class BoundedOrdinalTests(ReviewFindingsTestCase):
    """The pass ordinal is a bounded ASCII digit run, and so is its rendering.

    Derived by hand from outcome 2: the four closed-vocabulary fields render
    through the bound-and-redact rule. `redact` bounds a value it is GIVEN a
    string; an ordinal that reached `int()` and came back as an int was
    rendered raw, so a 4000-digit cell put 4000 characters on stderr and in
    the JSON envelope. The grammar bound is the fix, and the rendering bound
    is the backstop. Each case carries the paired in-grammar control.
    """

    def coverage(self, rows, *, date="2026-09-10", fid="adr-review-subject-one"):
        return "\n".join([
            "# Decision review — " + date, "",
            summary_table([(fid, "Repair")]), "",
            "## Repair", "", entry(fid), "",
            "## Coverage", "", record_table(rows),
        ])

    def test_a_four_thousand_digit_pass_ordinal_is_refused_and_bounded(self):
        body = self.coverage([("2026-09-10", "`adr-review-subject-one`",
                               "1" * 4000, "resolved", "a/path.md")])
        problem = self.refusal(self.parse, date="2026-09-10", body=body)
        self.assertIn("pass", problem)
        self.assertLess(len(problem), 600, "the refusal rendered the raw run")

    def test_a_five_thousand_digit_pass_ordinal_is_refused_and_bounded(self):
        body = self.coverage([("2026-09-10", "`adr-review-subject-one`",
                               "9" * 5000, "resolved", "a/path.md")])
        problem = self.refusal(self.parse, date="2026-09-10", body=body)
        self.assertLess(len(problem), 600)

    def test_a_two_digit_pass_ordinal_is_the_control(self):
        body = self.coverage([("2026-09-10", "`adr-review-subject-one`", 12,
                               "resolved", "a/path.md")])
        self.assertEqual(self.parse(date="2026-09-10", body=body).records[0]
                         .pass_ordinal, 12)

    def test_the_ordinal_bound_admits_9999_and_refuses_10000(self):
        """The boundary, so the bound cannot be satisfied by refusing every
        multi-digit ordinal."""
        admitted = self.coverage([("2026-09-10", "`adr-review-subject-one`",
                                   9999, "resolved", "a/path.md")])
        self.assertEqual(self.parse(date="2026-09-10", body=admitted)
                         .records[0].pass_ordinal, 9999)
        refused = self.coverage([("2026-09-10", "`adr-review-subject-one`",
                                  10000, "resolved", "a/path.md")])
        self.assertIn("pass", self.refusal(self.parse, date="2026-09-10",
                                           body=refused))

    def note_body(self, marker: str) -> str:
        fid = "adr-review-subject-one"
        return "\n".join([
            "# Decision review — 2026-09-10", "",
            summary_table([(fid, "Repair")]), "",
            "## Repair", "",
            entry(fid, marker),
            "", "## Coverage", "",
        ])

    def test_a_note_ordinal_outside_the_grammar_is_refused_naming_the_line(self):
        """A near-miss marker is REFUSED, never degraded to prose.

        `\\d` matches Arabic-Indic digits in a `str` pattern, so an ordinal
        outside the ASCII run once parsed and reached `int()`. Bounding the run
        fixed that and opened a quieter failure: the line fell out of the marker
        grammar, the parser read it as prose, and a pass that believed it wrote
        a note wrote nothing the pairing check sees. All three near-misses below
        now name their line.
        """
        for ordinal in ("10000", "0", "\u0662"):
            with self.subTest(ordinal=ordinal):
                problem = self.refusal(
                    self.parse, date="2026-09-10",
                    body=self.note_body(
                        f"- **disputed, pass {ordinal}** — prose about it."))
                self.assertIn("outside the ordinal grammar", problem)
                self.assertIn("line 12", problem)

    def test_a_line_that_is_not_a_note_marker_at_all_stays_prose(self):
        """The control for the refusal above: prose is still prose.

        Without this, the near-miss refusal could be reading every bulleted
        bold line in an entry, which would refuse a report for its narrative.
        """
        parsed = self.parse(
            date="2026-09-10",
            body=self.note_body("- **something else entirely** — prose."))
        self.assertEqual(parsed.notes, ())

    def test_an_ascii_digit_note_marker_is_the_control(self):
        fid = "adr-review-subject-one"
        body = "\n".join([
            "# Decision review — 2026-09-10", "",
            summary_table([(fid, "Repair")]), "",
            "## Repair", "",
            entry(fid, "- **disputed, pass 2** — prose about the event."),
            "", "## Coverage", "",
        ])
        notes = self.parse(date="2026-09-10", body=body).notes
        self.assertEqual([(n.kind, n.pass_ordinal) for n in notes],
                         [("disputed", 2)])

    def test_a_control_character_in_a_locator_is_refused(self):
        body = self.coverage([("2026-09-10", "`adr-review-subject-one`", 1,
                               "resolved", "a/pa\x07th.md")])
        self.assertIn("locator", self.refusal(self.parse, date="2026-09-10",
                                              body=body))

    def test_the_same_locator_without_the_control_character_is_the_control(self):
        body = self.coverage([("2026-09-10", "`adr-review-subject-one`", 1,
                               "resolved", "a/path.md")])
        self.assertEqual(self.parse(date="2026-09-10", body=body).records[0]
                         .locator, "a/path.md")


class SetDifferenceBoundTests(ReviewFindingsTestCase):
    """The summary-table set-difference refusal names at most ten ids.

    Derived by hand: a hand-editable table can carry any number of rows, and
    joining the whole difference put the entire table into one error string.
    Ten plus a count is the bound; the control proves a small difference is
    still named in full, so the cap is not a blanket elision.
    """

    def report(self, extra_rows):
        fid = "adr-review-subject-one"
        rows = [(fid, "Repair")] + [(e, "Repair") for e in extra_rows]
        body = "\n".join([
            "# Decision review — 2026-09-10", "",
            summary_table(rows), "",
            "## Repair", "", entry(fid), "", "## Coverage", "",
        ])
        return self.parse(date="2026-09-10", body=body)

    def test_five_thousand_extra_summary_rows_render_a_bounded_refusal(self):
        parsed = self.report([f"adr-review-extra-{n:05d}" for n in range(5000)])
        problem = self.refusal(rf.validate_structure, parsed)
        self.assertLess(len(problem), 2048, "the refusal joined every id")
        self.assertIn("more", problem)

    def test_two_extra_summary_rows_name_both_ids_in_full(self):
        parsed = self.report(["adr-review-extra-one", "adr-review-extra-two"])
        problem = self.refusal(rf.validate_structure, parsed)
        self.assertIn("adr-review-extra-one", problem)
        self.assertIn("adr-review-extra-two", problem)
        self.assertNotIn("more", problem)


class OrphanRecordRowTests(ReviewFindingsTestCase):
    """A five-cell, ISO-dated row under `## Coverage` that no table owns.

    Derived by hand from outcome 3: the record table is found BY ITS HEADER
    ROW. A mistyped header therefore left every row beneath it unowned, and an
    unowned row was skipped in silence — a report that believed it recorded a
    resolution recorded nothing, and the index computed the finding open. That
    disagreement is a document-lane refusal, not a silent drop.
    """

    ROW = "| 2026-09-10 | `adr-review-subject-one` | 1 | resolved | a/path.md |"

    def body(self, header):
        fid = "adr-review-subject-one"
        return "\n".join([
            "# Decision review — 2026-09-10", "",
            summary_table([(fid, "Repair")]), "",
            "## Repair", "", entry(fid), "",
            "## Coverage", "", header, "|---|---|---|---|---|", self.ROW,
        ])

    def test_an_unowned_iso_dated_five_cell_row_is_refused_naming_its_line(self):
        body = self.body(
            "| source report date | finding id | pass | event | evidence |")
        problem = self.refusal(self.parse, date="2026-09-10", body=body)
        self.assertIn(str(line_of(body, self.ROW)), problem)
        self.assertIn("header row", problem)

    def test_the_same_row_under_the_record_header_is_the_control(self):
        body = self.body(
            "| source report date | finding id | pass | event | locator |")
        record = self.parse(date="2026-09-10", body=body).records[0]
        self.assertEqual(record.event, "resolved")


class LocatorShapeTests(ReviewFindingsTestCase):
    """Outcome 2's three textual refusals hold on EVERY record.

    Derived by hand: the decision says a locator outside the grammar is
    refused, without qualification. The absolute / `~` / `..` refusals used to
    live only in the injected existence probe, which is asked about a
    `resolved` record alone — so a `re-verified` record naming `/etc/passwd`
    was admitted, and the skill's and the template's "is refused" promise was
    false for two of the three event kinds. The check is a pure string check;
    this module still does no I/O after import.
    """

    def coverage(self, event, locator, *, fid="adr-review-subject-one"):
        return "\n".join([
            "# Decision review — 2026-09-10", "",
            summary_table([(fid, "Repair")]), "",
            "## Repair", "", entry(fid), "",
            "## Coverage", "",
            record_table([("2026-09-10", f"`{fid}`", 1, event, locator)]),
        ])

    def test_an_absolute_locator_on_a_re_verified_record_is_refused(self):
        problem = self.refusal(self.parse, date="2026-09-10",
                               body=self.coverage("re-verified", "/etc/passwd"))
        self.assertIn("resolves only inside the repository root", problem)
        self.assertNotIn("is no surface in the tree", problem)

    def test_a_home_relative_locator_on_a_re_verified_record_is_refused(self):
        problem = self.refusal(self.parse, date="2026-09-10",
                               body=self.coverage("re-verified", "~/.ssh/id_rsa"))
        self.assertIn("resolves only inside the repository root", problem)

    def test_a_parent_traversal_locator_on_a_disputed_record_is_refused(self):
        problem = self.refusal(self.parse, date="2026-09-10",
                               body=self.coverage("disputed", "../outside/x.md"))
        self.assertIn("traverses out of the repository root", problem)

    def test_a_backslash_parent_traversal_is_refused(self):
        """`a\\..\\b` is ONE component to `PurePosixPath` and three on Windows.

        The absolute check already asked both path flavours; the `..` check
        asked only the POSIX one, so a value that traverses wherever `\\` is a
        separator was admitted by the leg meant to refuse traversal.
        """
        problem = self.refusal(self.parse, date="2026-09-10",
                               body=self.coverage("disputed", "a\\..\\b"))
        self.assertIn("traverses out of the repository root", problem)

    def test_a_backslash_in_a_locator_with_no_traversal_is_the_control(self):
        record = self.parse(date="2026-09-10",
                            body=self.coverage("disputed", "a\\b")).records[0]
        self.assertEqual(record.locator, "a\\b")

    def test_a_relative_locator_on_a_re_verified_record_is_the_control(self):
        record = self.parse(date="2026-09-10",
                            body=self.coverage("re-verified",
                                               "bionic/adrs/ADR-0001-x.md")).records[0]
        self.assertEqual(record.locator, "bionic/adrs/ADR-0001-x.md")


class BacktickedCellTests(ReviewFindingsTestCase):
    """ONE backtick rule, stated once and implemented once.

    Derived by hand: backticks are Markdown formatting, and a reader who
    backticks the id cell backticks the pass and event cells beside it. They
    are stripped before the closed-vocabulary check. The LOCATOR cell is the
    exception and stays refused: a backtick run terminates a fence, so the
    grammar refuses the character outright in the one free field.
    """

    def coverage(self, pass_cell, event_cell, locator,
                 *, fid="adr-review-subject-one"):
        return "\n".join([
            "# Decision review — 2026-09-10", "",
            summary_table([(fid, "Repair")]), "",
            "## Repair", "", entry(fid), "",
            "## Coverage", "",
            record_table([("2026-09-10", f"`{fid}`", pass_cell, event_cell,
                           locator)]),
        ])

    def test_backticked_pass_and_event_cells_parse(self):
        record = self.parse(date="2026-09-10",
                            body=self.coverage("`1`", "`resolved`",
                                               "a/path.md")).records[0]
        self.assertEqual((record.pass_ordinal, record.event), (1, "resolved"))

    def test_a_backticked_locator_is_still_refused(self):
        problem = self.refusal(self.parse, date="2026-09-10",
                               body=self.coverage(1, "resolved", "`a/path.md`"))
        self.assertIn("locator", problem)


class ProbeRefusalContextTests(ReviewFindingsTestCase):
    """A probe refusal is re-raised carrying the record's line and date.

    Derived by hand: the probe is handed a locator and nothing else, so its
    refusal named neither the record nor the report it came from — on a corpus
    of several reports the reader had to grep the string to find the row. The
    stream is the layer that knows both, so it is the layer that adds them.
    """

    def report(self, date, *, findings=(), records=()):
        rows = [(fid, "Repair") for fid in findings]
        out = [f"# Decision review — {date}", ""]
        if rows:
            out += [summary_table(rows), ""]
        out += ["## Repair", ""]
        for fid in findings:
            out += [entry(fid), ""]
        out += ["## Coverage", ""]
        if records:
            out.append(record_table(records))
        body = "\n".join(out)
        return self.parse(date=date, body=body), body

    def test_a_probe_that_answers_false_is_named_with_line_and_date(self):
        first, _ = self.report("2026-09-10", findings=["adr-review-subject-one"])
        second, body = self.report(
            "2026-09-11",
            records=[("2026-09-10", "`adr-review-subject-one`", 1, "resolved",
                      "bionic/adrs/ADR-9999-nothing.md")])

        def probe(_locator):
            raise rf.ReviewFindingsError("the locator names no surface")

        problem = self.refusal(rf.standing_by_finding, [first, second],
                               locator_exists=probe)
        self.assertIn("2026-09-11", problem)
        self.assertIn(str(line_of(body, "ADR-9999-nothing.md")), problem)
        self.assertIn("the locator names no surface", problem)

if __name__ == "__main__":
    unittest.main()
