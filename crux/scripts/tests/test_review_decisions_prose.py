"""Prose-surface pins for the review-decisions cadence contract.

Two rules live only in skill prose, so their regression tests read the prose:

- `review-decisions` step 6 refuses to write a report at an occupied path.
  Two passes on one date once overwrote each other silently.
- `tend-garden`'s decision-review age ignores a future-dated report and the
  derived index, the same filter `cleanup-campsite` CLN-ADR-5 specifies.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

SKILLS = Path(__file__).resolve().parent.parent.parent / "skills"


def _section(text: str, heading_prefix: str) -> str:
    start = text.index(heading_prefix)
    nxt = re.search(r"^### ", text[start + 1:], re.M)
    return text[start:] if nxt is None else text[start:start + 1 + nxt.start()]


class ReviewDecisionsStepSixTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = (SKILLS / "review-decisions" / "SKILL.md").read_text(encoding="utf-8")
        self.step6 = _section(self.text, "### Step 6")

    def test_step_six_refuses_an_occupied_report_path(self):
        self.assertIn("already exists", self.step6)
        self.assertIn("never overwrite", self.step6)

    def test_step_six_forbids_a_suffixed_filename(self):
        # The index regenerator admits only `YYYY-MM-DD.md`; a suffix would
        # redden the gate, so the prose must rule it out rather than suggest it.
        self.assertIn("suffix", self.step6)

    def test_the_checklist_carries_the_same_refusal(self):
        checklist = self.text[self.text.index("- [ ] The filename date"):]
        self.assertIn("did not already exist", checklist)


class TendGardenReviewAgeTests(unittest.TestCase):
    def test_the_age_measurement_ignores_future_dates_and_the_index(self):
        text = (SKILLS / "tend-garden" / "SKILL.md").read_text(encoding="utf-8")
        start = text.index("**decision-review age**")
        para = text[start:text.index("\n\n", start)]
        self.assertIn("future", para)
        self.assertIn("index.md", para)


if __name__ == "__main__":
    unittest.main()
