"""Prose-surface pins for `log-work`'s LOG-ONLY branch.

WHAT THIS FILE IS EVIDENCE OF, AND WHAT IT IS NOT. `log-work` has no
production code. It is a skill an agent executes by reading, so its log-only
branch — `--silent` WITHOUT `--journal` — is a rule stated in prose and
nothing else. There is no function to call, so there is no behavioural test to
write; this file therefore pins the PROSE CONTRACT, the way
`test_review_decisions_prose.py` pins the review cadence. **A prose pin is
weaker evidence than a behavioural one**: it proves the document still states
the rule, never that an agent obeyed it. It is written because the alternative
was no regression test at all, and because the one defect this branch has
already produced — a `--silent` call creating the month file the same document
forbids — was found by review and fixed in prose, leaving nothing to stop it
returning.

The branch's contract has four inverse claims, and the skill states them
across three sites that must agree:

  1. no month file is created,
  2. an existing month file is left byte-unchanged (no entry is composed),
  3. `<docs_dir>/journal/index.md` is left byte-unchanged, and
  4. the regenerator is invoked in NO mode at all — not write, not
     `--dry-run`, not `--check-stdin`.

Site A is step 3 ("Ensure the monthly file exists"), site B is step 6's
guard, site C is the tail of the verification checklist. Three statements of
one rule can drift apart, so `TheThreeSitesAgreeTests` pins the shared
condition wording as well as the claims — at step 3, at step 6 and in
`## Inputs`, the three sites that reuse the token verbatim. Site C is outside
that sweep on purpose: the checklist spells the mode out in its own words
(`In log-only ...`), and `ChecklistConfirmsTheInverseTests` pins that
spelling, so dropping either wording loses the branch.

THE FOURTH CLAIM IS ALSO MEASURED, out of band. `--silent` without
`--journal` leaving both the month file and `journal/index.md` byte-unchanged
is an acceptance measurement over a scratch tree: hash both files, drive the
log-only invocation, hash again, and drive the journaling invocation as the
paired positive control that both digests DO change. That measurement has no
function to call either, so it is recorded as tokens in the run snapshot
rather than as a case in this file.

Every expected string below is written out here independently. None is sliced
out of the skill file and compared with itself.

`crux/skills/` crosses the sync boundary, so this file reads no dev-only
surface and runs intact against the staged artifact.

Stdlib only. Run:
  uv run python3 -m unittest discover -s crux/scripts/tests -p 'test_log_work_prose.py'
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

SKILL = (Path(__file__).resolve().parents[2] / "skills" / "log-work" / "SKILL.md")

#: The condition that selects the log-only branch, spelled one way. Every site
#: has to use this wording, because three paraphrases of one condition are how
#: the branch drifted apart the first time.
LOG_ONLY_CONDITION = "`--silent` without `--journal`"

#: The regenerator, as the skill invokes it.
REGENERATOR = "generate-journal-index.py"

#: The two flags that make a run read-only. An invocation carrying NEITHER is
#: a write-mode invocation, whatever else it does or does not carry.
READ_ONLY_FLAGS = ("--check-stdin", "--dry-run")


def _regenerator_invocations(text: str) -> list[str]:
    """Every line that RUNS the regenerator, keyed on the executed path.

    Keyed on `scripts/<name>` — the form every skill in this plugin uses —
    and deliberately NOT on `--repo-root`. `init-docs` invokes this same
    regenerator in write mode WITHOUT `--repo-root`, so a classifier keyed on
    that flag misses the exact form a future author would copy: a second
    unguarded write-mode call in that form once passed this suite green.

    The classifier fails loud rather than silent. A prose sentence that
    quotes the executed path is counted as an invocation and, carrying no
    mode flag, is classified write-mode — which turns this file red. The
    repair is to name the script without its path prefix in prose.
    """
    return [ln for ln in text.splitlines() if "scripts/" + REGENERATOR in ln]


def _write_mode(invocations: list[str]) -> list[str]:
    """The invocations that carry neither read-only flag."""
    return [ln for ln in invocations
            if not any(flag in ln for flag in READ_ONLY_FLAGS)]


def _text() -> str:
    return SKILL.read_text(encoding="utf-8")


def _section(text: str, start_heading: str, stop: str = r"^#{2,3} ") -> str:
    """One `### N.` step body, from its heading to the next heading."""
    i = text.index(start_heading)
    m = re.search(stop, text[i + len(start_heading):], re.M)
    return text[i:] if m is None else text[i:i + len(start_heading) + m.start()]


class StepThreeCreatesNoMonthFileTests(unittest.TestCase):
    """Site A — the step that would otherwise create the month file."""

    def setUp(self) -> None:
        self.step3 = _section(_text(), "### 3. Ensure the monthly file exists")

    def test_the_step_is_scoped_to_journaling_invocations(self):
        self.assertIn("Journaling invocations only", self.step3)

    def test_the_step_names_the_log_only_condition(self):
        self.assertIn(LOG_ONLY_CONDITION, self.step3)

    def test_the_step_states_that_it_does_not_run_and_creates_no_file(self):
        self.assertIn("this step does not run", self.step3)
        self.assertIn("no month file is created", self.step3)

    def test_the_step_still_describes_the_creation_it_suppresses(self):
        # PAIRED POSITIVE CONTROL. The three assertions above are satisfied by
        # a step that says nothing at all about creating a file, so pin that
        # the journaling path this branch opts out of is still described here.
        self.assertIn("If missing, create it with this header", self.step3)


class StepSixInvokesTheRegeneratorInNoModeTests(unittest.TestCase):
    """Site B — the guard on the one write-mode regenerator invocation."""

    def setUp(self) -> None:
        self.text = _text()
        self.step6 = _section(self.text, "### 6. Regenerate")

    def test_the_guard_names_the_log_only_condition(self):
        self.assertIn("**The guard.**", self.step6)
        self.assertIn(LOG_ONLY_CONDITION, self.step6)

    def test_the_guard_skips_every_journal_writing_step(self):
        self.assertIn("steps 3, 4, 5 and 6 are all skipped", self.step6)
        self.assertIn("step 3 creates no month file", self.step6)
        self.assertIn("step 4 composes no entry", self.step6)

    def test_the_guard_states_the_regenerator_runs_in_no_mode_at_all(self):
        self.assertIn("the regenerator is invoked in no mode at all", self.step6)

    def test_the_guard_names_the_one_remaining_write(self):
        self.assertIn("The only write is the `docs/log.md` entry under `--log-op`",
                      self.step6)

    def test_exactly_one_write_mode_invocation_exists_and_it_sits_here(self):
        """A second unguarded write-mode call would reopen the whole defect."""
        invocations = _regenerator_invocations(self.text)
        # POSITIVE CONTROL for the counter: the skill really does invoke the
        # regenerator twice — the step-5 preflight and the step-6 write.
        self.assertEqual(len(invocations), 2, invocations)
        write_mode = _write_mode(invocations)
        self.assertEqual(len(write_mode), 1, write_mode)
        self.assertIn(write_mode[0], self.step6)


class WriteModeClassifierTests(unittest.TestCase):
    """The counter above classifies by MODE FLAG, never by `--repo-root`.

    Keyed on `--repo-root`, the counter missed a second write-mode call
    written in `init-docs`'s flagless form: a reviewer inserted exactly that
    into the skill and the suite still reported `OK`. These fixtures are
    written out here rather than sliced from any skill, so they fail on the
    classifier rather than on what a document happens to say today.
    """

    #: The reviewer's control, verbatim in shape: write mode, no `--repo-root`.
    #: This is the live form at `crux/skills/init-docs/SKILL.md`.
    FLAGLESS_WRITE = ('invoke `uv run "${CRUX_PLUGIN_ROOT}/scripts/'
                      'generate-journal-index.py"` from `${REPO_ROOT}` in write mode')
    #: The two forms `log-work` itself uses.
    FLAGGED_WRITE = ('uv run "${CRUX_PLUGIN_ROOT}/scripts/generate-journal-index.py"'
                     " --repo-root <repo-root>")
    PREFLIGHT = ('uv run "${CRUX_PLUGIN_ROOT}/scripts/generate-journal-index.py"'
                 " --check-stdin --month ${MONTH} --repo-root <repo-root>")
    DRY_RUN = ('uv run "${CRUX_PLUGIN_ROOT}/scripts/generate-journal-index.py"'
               " --dry-run --repo-root <repo-root>")

    def test_the_flagless_form_counts_as_a_write_mode_invocation(self):
        """The defect shape: a write-mode call the old classifier dropped."""
        found = _regenerator_invocations(self.FLAGLESS_WRITE)
        self.assertEqual(found, [self.FLAGLESS_WRITE])
        self.assertEqual(_write_mode(found), [self.FLAGLESS_WRITE])

    def test_the_flagless_form_carries_no_repo_root_to_key_on(self):
        # Proves the case above is the shape it claims to be, rather than a
        # fixture that happens to satisfy both classifiers.
        self.assertNotIn("--repo-root", self.FLAGLESS_WRITE)

    def test_each_read_only_flag_excludes_an_invocation_from_write_mode(self):
        for form in (self.PREFLIGHT, self.DRY_RUN):
            with self.subTest(form=form):
                found = _regenerator_invocations(form)
                self.assertEqual(found, [form])
                self.assertEqual(_write_mode(found), [])

    def test_positive_control_the_same_line_without_a_mode_flag_is_write_mode(self):
        # PAIRED POSITIVE CONTROL for the exclusions above: strip the flag and
        # the identical command reads as a write, so `_write_mode` discriminates
        # rather than excluding everything.
        found = _regenerator_invocations(self.FLAGGED_WRITE)
        self.assertEqual(_write_mode(found), [self.FLAGGED_WRITE])

    def test_a_second_write_mode_call_anywhere_in_the_text_is_counted(self):
        """The whole point: two write-mode calls must count as two."""
        text = "\n".join([self.PREFLIGHT, self.FLAGGED_WRITE, self.FLAGLESS_WRITE])
        self.assertEqual(len(_regenerator_invocations(text)), 3)
        self.assertEqual(_write_mode(_regenerator_invocations(text)),
                         [self.FLAGGED_WRITE, self.FLAGLESS_WRITE])

    def test_a_bare_name_without_the_executed_path_is_not_an_invocation(self):
        # The classifier's stated limit: prose that names the script without
        # its path prefix is a mention, not a run.
        prose = "the `" + REGENERATOR + "` regenerator is invoked in no mode at all"
        self.assertEqual(_regenerator_invocations(prose), [])


class ChecklistConfirmsTheInverseTests(unittest.TestCase):
    """Site C — the checklist a completed invocation is graded against."""

    def setUp(self) -> None:
        text = _text()
        self.tail = text[text.index("**The journal-write checks above"):]

    def test_the_checklist_names_the_log_only_condition(self):
        # This site spells the mode out rather than reusing the shared token,
        # so both spellings are pinned: dropping either loses the branch.
        self.assertIn("In log-only `--silent` mode (no `--journal`)", self.tail)

    def test_the_checklist_asks_for_the_inverse_not_the_journal_checks(self):
        self.assertIn("confirm the inverse", self.tail)
        self.assertIn(
            "NO write occurred to `docs/journal/${MONTH}.md` or "
            "`docs/journal/index.md`", self.tail)

    def test_the_checklist_names_the_only_write(self):
        self.assertIn(
            "the only write was the `docs/log.md` entry under `--log-op`",
            self.tail)

    def test_the_journal_checks_are_scoped_rather_than_deleted(self):
        # PAIRED POSITIVE CONTROL: the inverse only means something if the
        # positive checks it displaces are still in the document.
        self.assertIn("apply ONLY when this invocation journaled", self.tail)


class TheThreeSitesAgreeTests(unittest.TestCase):
    """One rule, three sites: they must not paraphrase each other apart."""

    def setUp(self) -> None:
        self.text = _text()

    def test_every_site_selects_the_branch_by_the_same_condition(self):
        step3 = _section(self.text, "### 3. Ensure the monthly file exists")
        step6 = _section(self.text, "### 6. Regenerate")
        inputs = _section(self.text, "## Inputs", stop=r"^## ")
        for label, section in (("step 3", step3), ("step 6", step6),
                               ("inputs", inputs)):
            with self.subTest(site=label):
                self.assertIn(LOG_ONLY_CONDITION, section)

    def test_the_inputs_section_does_not_claim_log_work_writes_the_row(self):
        """Step 6 owns the row through the regenerator; nothing hand-writes it."""
        inputs = _section(self.text, "## Inputs", stop=r"^## ")
        self.assertIn(
            "runs the regenerator that derives the `docs/journal/index.md` row",
            inputs)
        self.assertNotIn("the `docs/journal/index.md` rollup row", inputs)

    def test_the_frontmatter_description_agrees_with_step_six(self):
        """The description must attribute the index to a REGENERATOR, not to a write.

        What this guards is the distinction step 6 states: `log-work` computes no cell,
        increments no count, and edits no row by hand. A description saying it "updates
        the index" reads as the hand-write step 6 forbids, which is the paraphrase this
        class exists to catch.

        It used to pin one 64-character sentence fragment verbatim. That is longer than
        half the description budget, so the pin and the length bound could not both be
        met; the assertion now names the distinction rather than one wording of it.
        """
        frontmatter = self.text[:self.text.index("\n---\n", 4)]
        description = re.search(r'^description:\s*"(.*)"\s*$', frontmatter, re.M)
        self.assertIsNotNone(description, "no single-line quoted description")
        description = description.group(1)
        self.assertRegex(
            description, r"regenerat",
            "the description must say the journal index is REGENERATED; step 6 owns "
            "the row through the regenerator and nothing hand-writes it")
        for hand_write in ("rollup row in `docs/journal/index.md`",
                           "update its index", "updates its index",
                           "write the index", "writes the index"):
            self.assertNotIn(
                hand_write, description,
                f"the description claims a hand-write ({hand_write!r}) that step 6 "
                "explicitly denies")


if __name__ == "__main__":
    unittest.main()
