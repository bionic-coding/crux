"""Instruction contract: no instruction sends a council dispute to the owner.

The council skill, run-adr-council, the architect, the review reference and the council writer's limit message
name no owner escalation or extension request for a dispute. One exception is allowed and it is narrow: a required
safety fact about data policy or publishing is the outward-facing stop, so the council skill and the architect
may name that one ask, in a paragraph that says so.
"""
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'crux/scripts'))

SURFACES = [
    'crux/skills/council/SKILL.md',
    'crux/skills/run-adr-council/SKILL.md',
    'crux/agents/architect.md',
    'crux/skills/cycle/references/review.md',
]
# The cycle skill and its commands reference also put owner questions that are not
# council disputes (queue authorization, publishing), so only the dispute check reads them.
DISPUTE_SURFACES = [*SURFACES, 'crux/skills/cycle/SKILL.md', 'crux/skills/cycle/references/commands.md']
# Phrases that send a dispute, or a request for more attempts, to the owner.
ESCALATIONS = [
    r'(?:targeted check|safety fact|dissent|council)[^.]*\bstop for the owner',
    r'owner extension',
    r'(?<!no agent )(?<!no one )\brequests? an? (?:owner |attempt |limit )?extension',
    r'escalate to (?:the )?owner',
    r'ask(?:s)? the owner',
    r'hand(?:s)? (?:it )?to the owner',
    r'stop \+ escalate',
]
SAFETY_EXCEPTION = 'data policy or publishing'
EXCEPTION_SURFACES = {'crux/skills/council/SKILL.md', 'crux/agents/architect.md'}


def paragraphs(text):
    return [p for p in re.split(r'\n\s*\n', text) if p.strip()]


class InstructionContractTests(unittest.TestCase):
    def test_no_surface_names_an_owner_escalation_for_a_council_dispute(self):
        for relative in DISPUTE_SURFACES:
            text = (ROOT / relative).read_text()
            for paragraph in paragraphs(text):
                flat = ' '.join(paragraph.split())
                for pattern in ESCALATIONS:
                    if re.search(pattern, flat, re.IGNORECASE):
                        self.fail(f'{relative} names an owner escalation for a council dispute: {pattern!r} in {flat[:120]!r}')

    def test_only_the_safety_fact_exception_puts_a_question_to_the_owner(self):
        for relative in SURFACES:
            text = (ROOT / relative).read_text()
            for paragraph in paragraphs(text):
                flat = ' '.join(paragraph.split())
                for sentence in re.split(r'(?<=[.!?])\s+', flat):
                    if re.search(r'\bto the owner\b|\bthe owner is asked\b', sentence, re.IGNORECASE) and 'never' not in sentence.lower():
                        self.assertIn(SAFETY_EXCEPTION, flat, f'{relative}: {sentence[:120]!r}')
                        self.assertIn(relative, EXCEPTION_SURFACES)

    def test_the_council_skill_and_the_architect_state_that_a_dispute_never_goes_to_the_owner(self):
        for relative in ('crux/skills/council/SKILL.md', 'crux/agents/architect.md', 'crux/skills/run-adr-council/SKILL.md'):
            flat = ' '.join((ROOT / relative).read_text().split())
            self.assertRegex(flat, r'council dispute (?:is |never goes |is never )', relative)
        self.assertIn('withdraw-decision', (ROOT / 'crux/skills/council/SKILL.md').read_text())
        self.assertIn('withdraw-decision', (ROOT / 'crux/agents/architect.md').read_text())

    def test_the_review_reference_checks_the_implementation_against_the_approved_record(self):
        flat = ' '.join((ROOT / 'crux/skills/cycle/references/review.md').read_text().split())
        self.assertIn('approved plan and its Implementation Decisions', flat)
        self.assertIn('apply-in-build', flat)

    def test_the_architect_runs_idr_councils_in_plan_and_names_the_terminal_routes(self):
        flat = ' '.join((ROOT / 'crux/agents/architect.md').read_text().split())
        self.assertIn('IDR councils run in Plan', flat)
        self.assertIn('changes type to iterate', flat)
        self.assertRegex(flat, r'simplify cycle defers its selection and abandons')

    def test_the_commander_states_a_council_dispute_is_never_an_owner_decision(self):
        flat = ' '.join((ROOT / 'crux/agents/commander.md').read_text().split())
        self.assertIn('A council dispute is never an owner decision', flat)

    def test_the_writer_limit_message_names_withdraw_decision_and_no_owner(self):
        source = (ROOT / 'crux/scripts/cycle_council.py').read_text()
        message = re.search(r"raise CycleError\('(council attempt limit exhausted[^']*)'\)", source)
        self.assertIsNotNone(message)
        self.assertIn('withdraw-decision', message.group(1))
        for word in ('owner', 'extension', 'extend'):
            self.assertNotIn(word, message.group(1).lower())

    def test_the_patterns_catch_the_old_wording(self):
        # Positive control: the phrasing this contract replaced is flagged.
        old = 'For an unresolved required safety fact, obtain a targeted check or stop for the owner.'
        self.assertTrue(any(re.search(p, old, re.IGNORECASE) for p in ESCALATIONS))
        self.assertTrue(any(re.search(p, 'council attempt limit exhausted; explicit owner extension required', re.IGNORECASE) for p in ESCALATIONS))


if __name__ == '__main__':
    unittest.main()
