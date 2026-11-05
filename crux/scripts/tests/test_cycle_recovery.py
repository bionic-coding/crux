"""Acceptance observations, recorded prior-pass adoption and dispatch delivery identity."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle_hosts
import cycle
import cycle_ops
import cycle_workflow as workflow
from test_cycle_fix_step import FixBase
from test_cycle_ops_lifecycle import OpsBase


class CriterionFixTests(FixBase):
    def observation(self, cid, name, *, met=False, criterion=0, commit=None):
        rel = f'cycles/{cid}/evidence/{name}.json'
        path = self.root / 'bionic' / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({'criterion': criterion, 'value': 'observed good' if met else 'observed bad',
                                    'met': met, 'commit': commit or self.git('rev-parse', 'HEAD')}))
        self.git('add', str(path)); self.git('commit', '-qm', 'record observation')
        return rel

    def prepare_fix(self, phase='test'):
        cid = self.to_review() if phase == 'review' else self.to_test()
        before = self.observation(cid, 'before')
        doc = self.add_fix(cid, phase, criterion={'index': 0, 'observation': before})
        return cid, doc

    def finish_fix(self, cid, *, met=True, measured=None, criterion=0):
        commit = self.fix_source()
        after = self.observation(cid, 'after', met=met, commit=measured or commit, criterion=criterion)
        self.ok('task', cid, '--task-id', 'fix-1', '--commit', commit, '--fix-observation', after)
        return commit, after

    def test_criterion_fix_needs_committed_before_and_met_after_on_fix_descendant(self):
        cid, doc = self.prepare_fix()
        self.assertEqual(self.task_of(doc)['fix']['criterion']['index'], 0)
        self.assertIn('before', self.task_of(doc)['fix']['criterion'])
        self.finish_fix(cid)
        done = self.ok('task', cid, '--task-id', 'fix-1', '--state', 'done')
        self.assertEqual(self.task_of(done)['status'], 'done')
        self.assertEqual(done['pass'], 1)

    def test_missing_before_and_out_of_range_criterion_are_refused(self):
        cid = self.to_test()
        for criterion in ({'index': 0, 'observation': 'missing.json'},
                          {'index': 99, 'observation': 'missing.json'}):
            self.assertIn('observation', self.refused('task-add', cid, '--file',
                          self.write_json('fix.json', self.fix_task('test', criterion=criterion))))

    def test_uncommitted_or_met_before_is_refused(self):
        cid = self.to_test()
        before = self.observation(cid, 'before', met=True)
        self.assertIn('unmet', self.refused('task-add', cid, '--file',
                      self.write_json('fix.json', self.fix_task('test', criterion={'index': 0, 'observation': before}))))
        path = self.root / 'bionic' / before
        data = json.loads(path.read_text()); data['met'] = False; path.write_text(json.dumps(data))
        self.assertIn('committed', self.refused('task-add', cid, '--file',
                      self.write_json('fix.json', self.fix_task('test', criterion={'index': 0, 'observation': before}))))

    def test_done_without_after_is_refused(self):
        cid, _ = self.prepare_fix()
        commit = self.fix_source()
        self.assertIn('after observation', self.refused('task', cid, '--task-id', 'fix-1', '--commit', commit, '--state', 'done'))

    def test_unmet_after_and_measurement_before_fix_are_refused(self):
        cid, _ = self.prepare_fix()
        prior = self.git('rev-parse', 'HEAD')
        self.finish_fix(cid, met=False, measured=prior)
        self.assertIn('met', self.refused('task', cid, '--task-id', 'fix-1', '--state', 'done'))

    def test_after_on_non_descendant_is_refused(self):
        cid, _ = self.prepare_fix()
        prior = self.git('rev-parse', 'HEAD')
        self.finish_fix(cid, measured=prior)
        self.assertIn('descendant', self.refused('task', cid, '--task-id', 'fix-1', '--state', 'done'))

    def test_after_for_another_criterion_is_refused(self):
        cid, _ = self.prepare_fix()
        commit = self.fix_source()
        after = self.observation(cid, 'after', met=True, criterion=1, commit=commit)
        self.assertIn('criterion', self.refused('task', cid, '--task-id', 'fix-1', '--commit', commit, '--fix-observation', after))

    def test_changed_before_is_refused_and_second_fix_still_refuses(self):
        cid, doc = self.prepare_fix()
        before = self.root / 'bionic' / self.task_of(doc)['fix']['criterion']['before']['path']
        before.write_text('{}')
        self.finish_fix(cid)
        self.assertIn('digest', self.refused('task', cid, '--task-id', 'fix-1', '--state', 'done'))
        self.assertIn('one fix task', self.refused('task-add', cid, '--file', self.write_json('next.json', self.fix_task('test', 'next'))))

    def test_review_criterion_fix_still_needs_independent_fix_diff_review(self):
        cid, _ = self.prepare_fix('review')
        self.finish_fix(cid)
        self.assertIn('fix-diff', self.refused('task', cid, '--task-id', 'fix-1', '--state', 'done'))

    def test_criterion_fix_revalidates_checks_after_source_changes(self):
        cid, _ = self.prepare_fix()
        self.finish_fix(cid)
        (self.root / 'src/a.txt').write_text('changed after unit evidence')
        self.assertIn('invalid evidence', self.refused('task', cid, '--task-id', 'fix-1', '--state', 'done'))


class AdoptionTests(OpsBase):
    def earlier_delivery(self):
        prepared = self.prepare()
        commit = self.work(prepared)
        self.ok(self.deliver_request(commits=[commit]))
        original = deepcopy(self.doc()['assignments'][0]['delivery'])
        doc = self.doc(); doc['pass'] = 2; doc['pass_limit'] = 2
        doc['plan']['tasks'].append({'id': 'reuse-it', 'phase': 'build', 'description': 'reuse prior fix',
                                    'depends_on': [], 'status': 'pending', 'expected_evidence': ['adopted']})
        self.record_path().write_text(json.dumps(doc))
        return commit, original

    def test_adopted_commit_delivers_despite_earlier_base_and_keeps_original_delivery(self):
        commit, original = self.earlier_delivery()
        workflow.mutate(self.repo, self.cid, 'task', task_id='reuse-it', adopt_commits=[commit])
        task = self.doc()['plan']['tasks'][-1]
        self.assertEqual(task['adopted_commits'], [{'sha': commit, 'source_task': 'build-it', 'pass': 1, 'attempt': 1}])
        self.commit_file('src/later.py', 'later = 1\n', trailer=False)
        prepared = self.prepare(op_id='reuse-prep', task_id='reuse-it')
        self.write_result(prepared)
        self.ok(self.deliver_request(op_id='reuse-deliver', assignment='reuse-it', commits=[commit]))
        self.assertEqual(self.doc()['assignments'][0]['delivery'], original)

    def test_nonancestor_foreign_trailer_and_absent_delivery_are_refused(self):
        commit, _ = self.earlier_delivery()
        for sha in [self.commit_file('src/foreign.py', 'foreign=1', task='foreign'),
                    self.commit_file('src/unrecorded.py', 'x=1', task='build-it')]:
            with self.assertRaisesRegex(workflow.CycleError, 'recorded delivery'):
                workflow.mutate(self.repo, self.cid, 'task', task_id='reuse-it', adopt_commits=[sha])
        tree = self.git('rev-parse', 'HEAD^{tree}')
        stray = self.git('commit-tree', tree, '-m', 'side\n\nCycle-Task: build-it')
        with self.assertRaisesRegex(workflow.CycleError, 'ancestor'):
            workflow.mutate(self.repo, self.cid, 'task', task_id='reuse-it', adopt_commits=[stray])

    def test_current_pass_delivery_is_not_adoptable(self):
        prepared = self.prepare(); commit = self.work(prepared)
        self.ok(self.deliver_request(commits=[commit])); self.add_task('reuse-it')
        with self.assertRaisesRegex(workflow.CycleError, 'earlier pass'):
            workflow.mutate(self.repo, self.cid, 'task', task_id='reuse-it', adopt_commits=[commit])

    def test_foreign_trailer_is_refused_even_when_recorded_in_the_source_delivery(self):
        self.earlier_delivery()
        foreign = self.commit_file('src/foreign.py', 'x = 1\n', task='different-task')
        doc = self.doc(); doc['assignments'][0]['delivery']['commits'].append(foreign)
        self.record_path().write_text(json.dumps(doc))
        with self.assertRaisesRegex(workflow.CycleError, 'trailer'):
            workflow.mutate(self.repo, self.cid, 'task', task_id='reuse-it', adopt_commits=[foreign])

    def test_low_level_fix_delivery_is_adoptable_without_inventing_a_host_attempt(self):
        commit = self.commit_file('src/fixed.py', 'fixed = 1\n')
        workflow.mutate(self.repo, self.cid, 'task', task_id='build-it', state='done', commits=[commit])
        doc = self.doc(); doc['pass'] = doc['pass_limit'] = 2
        self.record_path().write_text(json.dumps(doc)); self.add_task('reuse-it')
        workflow.mutate(self.repo, self.cid, 'task', task_id='reuse-it', adopt_commits=[commit])
        provenance = self.doc()['plan']['tasks'][-1]['adopted_commits'][0]
        self.assertEqual((provenance['source_task'], provenance['pass'], provenance['attempt']), ('build-it', 1, None))

    def test_nonadopted_earlier_commit_still_refuses_task_base(self):
        commit, _ = self.earlier_delivery()
        self.commit_file('src/later.py', 'later = 1\n', trailer=False)
        prepared = self.prepare(op_id='reuse-prep', task_id='reuse-it'); self.write_result(prepared)
        self.refused(self.deliver_request(op_id='reuse-deliver', assignment='reuse-it', commits=[commit]), 'commit-not-from-base')


class DeliveryTokenTests(OpsBase):
    def test_same_attempt_resume_rotates_without_a_cycle_pause_or_a_new_attempt(self):
        prepared = self.prepare(); self.write_result(prepared)
        old = self.doc()['assignments'][0]['delivery_token']
        self.lowlevel(self.inspect_attempt()['resume'], **{'--note': 'resume after hand-back'})
        entry = self.doc()['assignments'][0]
        self.assertNotEqual(old, entry['delivery_token'])
        self.assertEqual((entry['state'], entry['attempt'], self.doc()['pass']), ('reserved', 1, 1))
        self.assertFalse(Path(prepared['result_path']).exists())
        self.assertEqual(len(entry['previous_results']), 1)
        with self.assertRaisesRegex(workflow.CycleError, 'token'):
            workflow.mutate(self.repo, self.cid, 'assignment', id='build-it', resume_token=old, note='lost response retry')
        prepared['delivery_token'] = entry['delivery_token']; self.write_result(prepared)
        self.ok(self.deliver_request())

    def test_same_attempt_resume_refuses_closed_attempt_and_requires_reason(self):
        prepared = self.prepare()
        old = self.doc()['assignments'][0]['delivery_token']
        with self.assertRaisesRegex(workflow.CycleError, 'note'):
            workflow.mutate(self.repo, self.cid, 'assignment', id='build-it', resume_token=old)
        self.write_result(prepared); self.ok(self.deliver_request())
        with self.assertRaisesRegex(workflow.CycleError, 'open typed'):
            workflow.mutate(self.repo, self.cid, 'assignment', id='build-it', resume_token=old, note='wrong route')

    def test_new_dispatch_token_is_in_preamble_wait_and_delivery(self):
        prepared = self.prepare()
        token = self.doc()['assignments'][0]['delivery_token']
        self.assertIn('#' + token, prepared['invocation']['parameters']['prompt'])
        self.assertIn('#' + token, json.dumps(prepared['invocation']['wait']))
        self.write_result(prepared)
        self.ok(self.deliver_request())

    def test_resume_rotates_token_retains_previous_file_and_rejects_old_marker(self):
        prepared = self.prepare(); self.write_result(prepared)
        entry = self.doc()['assignments'][0]; old = entry['delivery_token']
        old_bytes = Path(entry['result_path']).read_bytes()
        workflow.mutate(self.repo, self.cid, 'pause', reason='owner requested pause')
        workflow.mutate(self.repo, self.cid, 'resume', reason='resume worker')
        new = self.doc()['assignments'][0]
        self.assertNotEqual(old, new['delivery_token'])
        self.assertEqual((self.repo / 'bionic' / new['previous_results'][0]['path']).read_bytes(), old_bytes)
        Path(new['result_path']).write_bytes(old_bytes)
        self.refused(self.deliver_request(), 'result-incomplete')
        self.assertFalse(cycle_hosts.marker_arrived(Path(new['result_path']), new['id'], 1, new['delivery_token']))
        wait = self.inspect_attempt()['wait']
        self.assertIn('#' + new['delivery_token'], json.dumps(wait))
        arrived = cycle.await_result(self.repo, None, None, 0.01, [new['result_path']],
                                     f"{new['id']}/1#{new['delivery_token']}")
        self.assertFalse(arrived['arrived'])

    def test_tokenless_historical_attempt_delivers_with_original_marker(self):
        prepared = self.prepare()
        doc = self.doc(); doc['assignments'][0].pop('delivery_token', None)
        self.record_path().write_text(json.dumps(doc))
        Path(prepared['result_path']).write_text('Assignment: build-it\nAttempt: 1\nResult-End: build-it/1\n')
        self.ok(self.deliver_request())

    def test_token_marker_parser_rejects_malformed_tokens(self):
        token = 'a' * 32
        self.assertEqual(cycle_hosts.parse_marker('a/1#' + token), ('a', 1, token))
        for value in ('a/1#', 'a/1#../../x', 'a/1#A' * 32):
            self.assertIsNone(cycle_hosts.parse_marker(value))

    def test_every_host_wait_command_uses_the_token_and_historical_waits_keep_old_form(self):
        token = 'b' * 32
        for host in cycle_hosts.ADAPTERS:
            for mode in cycle_hosts.modes(host):
                wait = cycle_hosts.wait_descriptor(host, mode=mode, repo_root=self.repo,
                                                   result_path='/private/tmp/result.md', assignment='a', attempt=1,
                                                   delivery_token=token)
                encoded = json.dumps(wait)
                self.assertIn('Result-End: a/1#' + token, encoded)
                self.assertIn('--marker a/1#' + token, encoded)

    def test_new_dispatch_cannot_reuse_old_marker_even_when_result_path_is_reused(self):
        first = self.prepare(); self.write_result(first)
        old = Path(first['result_path']).read_bytes()
        self.ok(self.deliver_request(outcome='failed'))
        second = self.prepare(op_id='prep-next', assignment='build-it', result_path=first['result_path'])
        self.assertEqual(Path(second['result_path']).read_bytes(), old)
        self.refused(self.deliver_request(op_id='deliver-next', attempt=2), 'result-header')


if __name__ == '__main__':
    unittest.main()
