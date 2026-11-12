"""The council writer's limit message routes a dispute to withdrawal, never to the owner.

When a cycle decision exhausts its council attempts, the writer's refusal names
`withdraw-decision` and no owner escalation or extension request.
"""
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'crux/scripts'))


class InstructionContractTests(unittest.TestCase):
    def test_the_writer_limit_message_names_withdraw_decision_and_no_owner(self):
        source = (ROOT / 'crux/scripts/cycle_council.py').read_text()
        message = re.search(r"raise CycleError\('(council attempt limit exhausted[^']*)'\)", source)
        self.assertIsNotNone(message)
        self.assertIn('withdraw-decision', message.group(1))
        for word in ('owner', 'extension', 'extend'):
            self.assertNotIn(word, message.group(1).lower())


if __name__ == '__main__':
    unittest.main()
