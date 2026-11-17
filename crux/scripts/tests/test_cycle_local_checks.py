"""Proportionate cycle verification records observations without a receipt store."""
import json
import contextlib
import io
from pathlib import Path
import sys
import tempfile
import subprocess
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle_ops
import cycle
import cycle_context
import cycle_classify
import cycle_workflow as workflow


class LocalCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'bionic').mkdir()
        (self.root / 'bionic/manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\n')
        (self.root / 'src').mkdir()
        (self.root / 'src/value.py').write_text('value = 1\n')
        self.doc = workflow.create(self.root, 'quick-fix', 'Fix', 'Correct value', ['src'], ['value correct'], 'builder', 'tester')
        self.cfg = workflow.tree(self.root)

    def apply(self, action, **args):
        self.doc = workflow.mutate(self.root, self.doc['id'], action, **args)
        return self.doc

    def observe(self, result='passed', **kwargs):
        self.apply('local-check', check_id='focused', executed_command='python -m unittest test_value',
                   tested_revision='abc123 plus src/value.py working edits', result=result,
                   summary='1 test ' + result, reason='Changed value and its caller', **kwargs)
        return self.doc['local_checks'][-1]['id']

    def selection(self):
        self.apply('checks', checks=['focused'], phase='build')
        self.apply('checks', checks=['focused'])
        self.apply('coverage', coverage={'affected': ['value and its caller'],
                   'checks': [{'check_id': 'focused', 'rationale': 'Exercises changed behavior and related caller'}],
                   'not_selected': 'Full suite deferred to PR CI; this correction has one caller.'})

    def test_selected_local_checks_complete_without_test_evidence(self):
        self.selection()
        observed = subprocess.run([sys.executable, '-c', 'from pathlib import Path; assert "value = 1" in Path("src/value.py").read_text()'],
                                  cwd=self.root, capture_output=True, text=True)
        self.assertEqual(observed.returncode, 0, observed.stderr)
        self.observe()
        with (patch('test_evidence.validate_evidence', side_effect=AssertionError('receipt validation called')),
              patch('test_evidence.lookup', side_effect=AssertionError('receipt lookup called'))):
            self.apply('advance')
            self.apply('advance')
            self.apply('review', report={'reviewer': 'independent', 'scope': ['src'],
                       'evidence': [self.doc['local_checks'][-1]['id']], 'blocking': [], 'advisory': [], 'cosmetic': [],
                       'verdict': 'approve', 'rationale': 'Related caller covered; full integration left to CI.'})
            self.apply('advance')
            self.apply('completion', commits=[], exception='Fixture owner requests uncommitted delivery.', remaining='Fixture only')
            self.apply('reflect', reflection={'outcome': 'fixed', 'lessons': ['focused tests sufficient'], 'remaining': ['PR CI']})
            self.apply('advance')
        self.assertEqual(self.doc['status'], 'completed')
        self.assertEqual(self.doc['evidence'], [])
        self.assertLess(len(json.dumps(self.doc['local_checks'])), 1500)
        self.assertFalse(any(self.root.rglob('TE-*')))

    def test_missing_and_latest_failed_check_block_selected_gate(self):
        self.selection()
        with self.assertRaisesRegex(workflow.CycleError, 'missing passing local check'):
            workflow.check_build(self.cfg, self.doc)
        self.observe()
        workflow.check_build(self.cfg, self.doc)
        self.observe('failed')
        with self.assertRaisesRegex(workflow.CycleError, 'latest local check failed'):
            workflow.check_build(self.cfg, self.doc)

    def test_reuse_requires_current_pass_prior_success_and_reason(self):
        self.selection()
        prior = self.observe()
        for reuse, reason in [('LC-' + '0' * 32, 'unchanged'), (prior, '')]:
            with self.assertRaises(workflow.CycleError):
                self.apply('local-check', check_id='focused', reuse=reuse, summary='Still applicable', reason=reason)
        self.apply('local-check', check_id='focused', reuse=prior, summary='Still applicable', reason='Later edit changes only an unrelated comment')
        self.assertEqual(self.doc['local_checks'][-1]['tested_revision'], self.doc['local_checks'][0]['tested_revision'])
        self.observe('failed')
        with self.assertRaisesRegex(workflow.CycleError, 'later failed'):
            self.apply('local-check', check_id='focused', reuse=prior, summary='Still applicable', reason='unchanged')

    def test_fix_observations_need_failed_before_latest_passing_same_check(self):
        before = self.observe('failed')
        task = {'id': 'fix-it', 'fix': {'finding': 'r1:0', 'eligibility': 'bounded'}}
        with self.assertRaises(workflow.CycleError):
            workflow.set_fix_receipts(self.cfg, task, {'fix_before': before, 'fix_after': before}, self.doc)
        after = self.observe()
        workflow.set_fix_receipts(self.cfg, task, {'fix_before': before, 'fix_after': after}, self.doc)
        self.assertEqual(task['fix']['after'], after)
        self.observe('failed')
        with self.assertRaises(workflow.CycleError):
            workflow.fix_after_receipt(self.cfg, after, 'focused', self.doc)

    def test_inspect_and_missing_checks_do_not_search_receipt_store(self):
        self.selection()
        with (patch('test_evidence.lookup', side_effect=AssertionError('receipt lookup called')),
              patch('cycle_summary._store', side_effect=AssertionError('receipt store scanned'))):
            self.assertEqual(cycle_ops.missing_checks(self.cfg, self.doc), ['focused'])
            self.assertEqual(cycle_ops.reusable_receipts(self.cfg, self.doc), {})
            _, response = cycle_ops.run(self.root, self.doc['id'], {'op': 'inspect'})
            self.assertTrue(any('local-check' in a.get('argv', []) for a in response['actions']))
            self.observe('failed')
            _, response = cycle_ops.run(self.root, self.doc['id'], {'op': 'inspect'})
            self.assertTrue(any('local-check' in a.get('argv', []) for a in response['actions']))
        self.observe()
        self.assertEqual(cycle_ops.missing_checks(self.cfg, self.doc), [])
        _, response = cycle_ops.run(self.root, self.doc['id'], {'op': 'inspect'})
        self.assertTrue(any(a.get('request', {}).get('op') == 'advance' for a in response['actions']))

    def test_handoff_references_resolve_local_observations_without_receipts(self):
        ident = self.observe()
        reference = cycle_context.references('Check passed: ' + ident)[0]
        self.assertEqual(reference['kind'], 'local-check')
        with patch('test_evidence.validate_evidence', side_effect=AssertionError('receipt validation called')):
            self.assertTrue(cycle_context.resolve_reference(self.cfg, reference, {}, self.doc)['valid'])
            missing = {**reference, 'value': 'LC-' + '0' * 32}
            self.assertFalse(cycle_context.resolve_reference(self.cfg, missing, {}, self.doc)['valid'])
            self.observe('failed')
            self.assertFalse(cycle_context.resolve_reference(self.cfg, reference, {}, self.doc)['valid'])

    def test_failure_advice_reads_compact_local_observation(self):
        failed = self.observe('failed')
        job = cycle_classify.Job('failure-routing', 'focused', 'check:' + failed)
        with patch('cycle_classify.receipt_record', side_effect=AssertionError('receipt read called')):
            plan = cycle_classify.plan_failure(self.cfg, self.doc, job, self.root)
        self.assertEqual(plan.state['summary']['result'], 'failed')
        self.assertEqual(plan.state['summary']['command'], 'python -m unittest test_value')

    def test_new_policy_preserves_historical_and_release_interpretation(self):
        self.assertTrue(workflow.proportionate(self.doc))
        historical = dict(self.doc)
        historical.pop('testing_policy')
        historical.pop('local_checks')
        workflow.validate(historical)
        self.assertFalse(workflow.proportionate(historical))
        release = dict(self.doc, type='release')
        self.assertFalse(workflow.proportionate(release))

    def test_review_basis_tracks_command_and_coverage_without_phase_retests(self):
        self.selection()
        self.observe()
        basis = workflow.review_basis(self.doc)
        self.observe()
        self.assertEqual(workflow.review_basis(self.doc), basis)
        self.doc['local_checks'][-1]['command'] = 'python -m unittest another_test'
        self.assertNotEqual(workflow.review_basis(self.doc), basis)

    def test_cli_records_observation_and_returns_only_compact_result(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = cycle.main(['--repo-root', str(self.root), 'local-check', self.doc['id'],
                               '--check-id', 'focused', '--command', 'python -m unittest test_value',
                               '--tested-revision', 'abc123 with working edits', '--result', 'passed',
                               '--summary', '1 test passed', '--reason', 'value and caller exercised'])
        result = json.loads(output.getvalue())
        self.assertEqual(code, 0, result)
        self.assertEqual(result['local_check']['command'], 'python -m unittest test_value')
        self.assertLess(len(output.getvalue()), 1500)
        self.assertNotIn('snapshot', result['local_check'])

    def test_invalid_stored_reuse_and_missing_array_are_rejected(self):
        prior = self.observe()
        self.apply('local-check', check_id='focused', reuse=prior, summary='still relevant', reason='comment only')
        self.doc['local_checks'][-1]['tested_revision'] = 'different'
        with self.assertRaisesRegex(workflow.CycleError, 'retain a prior'):
            workflow.validate(self.doc)
        self.doc['local_checks'] = []
        workflow.validate(self.doc)
        del self.doc['local_checks']
        with self.assertRaisesRegex(workflow.CycleError, 'requires local_checks'):
            workflow.validate(self.doc)


if __name__ == '__main__':
    unittest.main()
