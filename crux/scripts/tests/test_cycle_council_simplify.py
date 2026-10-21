"""A council convened for a simplify cycle carries the fixed scope instruction in every mode.

Covers the legacy gateway path, Standard and Strict gateway modes and the native Lite request.
A non-simplify cycle and a council without a cycle carry no instruction.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cycle_workflow import create, digest, mutate

try:
    from crux.core.data_classes import CouncilVote, CouncilDeliberation
    HAVE_GATEWAY = True
except ImportError:
    HAVE_GATEWAY = False

QUESTION = 'Evaluate the proposals.'


def instruction():
    import cycle_council
    return cycle_council.SIMPLIFY_SCOPE_INSTRUCTION


def contents():
    value = {k: ['reason'] for k in ('alternatives', 'approach', 'assumptions', 'constraints', 'intended_evidence')}
    value.update(assessed='the helper', selected=['P1'], proposals=[{
        'id': 'P1', 'removes': 'helper', 'retained_behavior': 'same', 'objectives': ['OBJ-5'],
        'decision_clauses': ['none: no rule'], 'expected_savings': 'one function', 'verification': 'tests', 'paths': ['src/a.py']}])
    return value


class Base(unittest.TestCase):
    mode = None

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.docs = self.root / 'bionic'
        self.docs.mkdir()
        (self.root / 'src').mkdir()
        (self.root / 'src/a.py').write_text('x = 1\n')
        (self.root / '.bionic.yml').write_text('config_version: "1"\ndocs_dir: bionic\n')
        (self.docs / 'manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\n')
        (self.docs / 'objectives.md').write_text('Proportional review and durable history.')
        (self.docs / 'adrs').mkdir()
        (self.docs / 'adrs/subject.txt').write_text('A bounded proposal.')
        if self.mode:
            from council_policy import initialize
            for args in (('init', '-q'), ('config', 'user.email', 't@example.invalid'), ('config', 'user.name', 'T')):
                subprocess.run(['git', '-C', str(self.root), *args], check=True, capture_output=True)
            initialize(self.root, self.mode, selection='Explicit test setup selects ' + self.mode)
            subprocess.run(['git', '-C', str(self.root), 'add', '.'], check=True, capture_output=True)
            subprocess.run(['git', '-C', str(self.root), 'commit', '-qm', 'Fixture'], check=True, capture_output=True)

    def cycle(self, kind):
        doc = create(self.root, kind, 'Trim', 'Remove helper', ['src'], ['Behavior kept'], 'builder', 'tester')
        doc = mutate(self.root, doc['id'], 'decision', kind='idr', name='selection', contents=contents())
        return doc, doc['decisions'][-1]['path']

    def attempt_of(self, output):
        return json.loads((self.docs / output['attempt']).read_text())


@unittest.skipUnless(HAVE_GATEWAY, 'gateway dependencies unavailable')
class GatewayBase(Base):
    def run_gateway(self, purpose, subject, cycle_id=None, **options):
        votes = [CouncilVote(model=p + '/model', provider=p, decision='APPROVE', reasoning='ok', confidence=.9)
                 for p in ('openai', 'anthropic', 'google')]
        result = CouncilDeliberation(votes=votes, consensus='UNANIMOUS_APPROVE', consensus_confidence=.9,
                                     key_agreements=[], key_disagreements=[], final_recommendation={})
        from cycle_council import convene
        with patch('crux_env.get', return_value='test-gateway-credential'), \
             patch('crux.council.async_council.validate_gate_assignment', return_value={'openai_top': 'one', 'anthropic_top': 'two', 'google_top': 'three'}), \
             patch('crux.core.llm_caller.get_model_config', return_value=SimpleNamespace(max_output_tokens=65536)), \
             patch('crux.council.async_council.AsyncCouncil') as council:
            council.return_value.deliberate = AsyncMock(return_value=result)
            output = convene(self.root, purpose, subject, QUESTION, cycle_id=cycle_id, **options)
            return output, council.return_value.deliberate.call_args.args[0]


class LegacyGatewayTests(GatewayBase):
    def test_simplify_cycle_prompt_and_hash_carry_the_instruction(self):
        doc, subject = self.cycle('simplify')
        output, prompt = self.run_gateway('idr', subject, doc['id'])
        self.assertIn(instruction(), prompt)
        self.assertIn(QUESTION, prompt)
        self.assertEqual(self.attempt_of(output)['question_sha256'], digest((QUESTION + '\n\n' + instruction()).encode()))

    def test_other_cycle_types_carry_none(self):
        doc, subject = self.cycle('iterate')
        output, prompt = self.run_gateway('idr', subject, doc['id'])
        self.assertNotIn(instruction(), prompt)
        self.assertEqual(self.attempt_of(output)['question_sha256'], digest(QUESTION.encode()))

    def test_council_without_a_cycle_carries_none(self):
        _, prompt = self.run_gateway('consultation', 'adrs/subject.txt')
        self.assertNotIn(instruction(), prompt)


class StandardGatewayTests(GatewayBase):
    mode = 'standard'

    def test_simplify_cycle(self):
        doc, subject = self.cycle('simplify')
        output, prompt = self.run_gateway('idr', subject, doc['id'])
        self.assertIn(instruction(), prompt)
        attempt = self.attempt_of(output)
        self.assertTrue(attempt['question'].endswith(instruction()))
        self.assertEqual(attempt['question_sha256'], digest((QUESTION + '\n\n' + instruction()).encode()))
        self.assertEqual(attempt['policy']['mode'], 'standard')

    def test_non_simplify_cycle(self):
        doc, subject = self.cycle('dev')
        output, prompt = self.run_gateway('idr', subject, doc['id'])
        self.assertNotIn(instruction(), prompt)
        self.assertEqual(self.attempt_of(output)['question'], QUESTION)

    def test_no_cycle(self):
        output, prompt = self.run_gateway('consultation', 'adrs/subject.txt', identity='plain')
        self.assertNotIn(instruction(), prompt)
        self.assertEqual(self.attempt_of(output)['question'], QUESTION)


class StrictGatewayTests(GatewayBase):
    mode = 'strict'

    def test_simplify_cycle(self):
        doc, subject = self.cycle('simplify')
        output, prompt = self.run_gateway('idr', subject, doc['id'])
        self.assertIn(instruction(), prompt)
        self.assertEqual(self.attempt_of(output)['policy']['mode'], 'strict')

    def test_non_simplify_cycle(self):
        doc, subject = self.cycle('dev')
        _, prompt = self.run_gateway('idr', subject, doc['id'])
        self.assertNotIn(instruction(), prompt)


class LiteNativeTests(Base):
    mode = 'lite'

    def prepare(self, purpose, subject, cycle_id=None, **kw):
        from council_native import prepare
        return prepare(self.root, purpose, subject, QUESTION, harness='codex', author_context='/root/author',
                       cycle_id=cycle_id, identity='lite-fx', **kw)

    def test_simplify_cycle_request_carries_the_instruction(self):
        doc, subject = self.cycle('simplify')
        out = self.prepare('idr', subject, doc['id'])
        self.assertIn(instruction(), out['dispatch']['message'])
        request = json.loads((self.docs / out['request']).read_text())
        self.assertIn(instruction(), request['prompt'])
        attempt = json.loads((self.docs / out['attempt']).read_text())
        self.assertEqual(attempt['question_sha256'], digest((QUESTION + '\n\n' + instruction()).encode()))

    def test_non_simplify_cycle_request_carries_none(self):
        doc, subject = self.cycle('dev')
        out = self.prepare('idr', subject, doc['id'])
        self.assertNotIn(instruction(), out['dispatch']['message'])

    def test_no_cycle_request_carries_none(self):
        out = self.prepare('consultation', 'adrs/subject.txt')
        self.assertNotIn(instruction(), out['dispatch']['message'])


class ConstantTests(unittest.TestCase):
    def test_wording(self):
        text = instruction()
        for needle in ('only the proposals within the agreed scope', 'new features', 'speculative hardening',
                       'unrelated requirements', 'different work', 'not a condition of approval',
                       'block or drop a proposal whose retained behavior or verification is inadequate',
                       'only remedies that add complexity are out of scope'):
            self.assertIn(needle, text)

    def test_helper_is_idempotent(self):
        import cycle_council
        once = QUESTION + '\n\n' + instruction()
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        root = Path(holder.name)
        (root / 'bionic').mkdir()
        (root / 'bionic/manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\n')
        cycle = create(root, 'simplify', 'T', 'O', ['src'], ['A'], 'b', 't')
        self.assertEqual(cycle_council.scoped_question(root, cycle['id'], once), once)
        self.assertEqual(cycle_council.scoped_question(root, cycle['id'], QUESTION), once)
        self.assertEqual(cycle_council.scoped_question(root, None, QUESTION), QUESTION)


if __name__ == '__main__':
    unittest.main()
