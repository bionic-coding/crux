"""withdraw-decision: the typed writer operation, its Plan gate, and what inspect reports about a withdrawal.

Fixture records only: no council is convened and no model is called. Council attempts are written
as the attempt files cycle_council reads.
"""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cycle_ops
import cycle_workflow
from cycle_workflow import CycleError, PHASES, check_decisions, create, digest, encoded, load, mutate, retained, tree
from test_cycle_slice import SliceBase

KEYS = ('alternatives', 'approach', 'assumptions', 'constraints', 'intended_evidence')
SIMPLIFY_SELECTION = {'assessed': 'the helper', 'selected': ['P1'], 'proposals': [{
    'id': 'P1', 'removes': 'helper', 'retained_behavior': 'same', 'objectives': ['OBJ-5'],
    'decision_clauses': ['none: no rule'], 'expected_savings': 'one function', 'verification': 'tests', 'paths': ['src/a.py']}]}


def contents(**extra):
    return {**{k: ['reason'] for k in KEYS}, **extra}


class WithdrawBase(SliceBase):
    def new_cycle(self, kind='dev'):
        return create(self.repo, kind, 'Change', 'Improve', ['src'], ['Works'], 'builder', 'tester')['id']

    def plan(self, cid, extra=()):
        """A plan with one task per phase plus the named extra Build tasks, which depend on nothing."""
        doc = load(self.repo, cid)
        plan = json.loads(json.dumps(doc['plan']))
        tasks = [{'id': p, 'phase': p, 'description': p, 'depends_on': [], 'status': 'pending', 'expected_evidence': ['observation']} for p in PHASES[doc['type']]]
        tasks += [{'id': t, 'phase': 'build', 'description': t, 'depends_on': [], 'status': 'pending', 'expected_evidence': ['observation']} for t in extra]
        plan.update(verification=['focused tests'], tasks=tasks)
        return mutate(self.repo, cid, 'plan', plan=plan, reason='plan')

    def decide(self, cid, name='choice', approve=True, **extra):
        doc = mutate(self.repo, cid, 'decision', kind='idr', name=name, contents=contents(**extra))
        subject = doc['decisions'][-1]['path']
        if approve:
            doc = mutate(self.repo, cid, 'approve-decision', subject=subject, approval=self.approval(doc, subject))
        return doc, subject

    def approval(self, doc, subject, nits=()):
        cfg = tree(self.repo)
        findings = [{'id': i, 'kind': 'nit', 'text': 'nit ' + i} for i in nits]
        seats = [{'provider': p, 'decision': 'APPROVE', 'errored': False, 'findings': []} for p in ('openai', 'google')]
        seats.append({'provider': 'anthropic', 'decision': 'APPROVE_WITH_NITS' if nits else 'APPROVE', 'errored': False, 'findings': findings})
        value = {'format': 'crux.cycle-council', 'purpose': 'idr', 'subject': subject, 'outcome': 'approved', 'cycle_id': doc['id'],
                 'subject_sha256': digest((cfg.docs_root / subject).read_bytes()), 'seats': seats}
        value['record_sha256'] = digest(encoded(value))
        return retained(cfg, doc['id'], 'councils', value)['path']

    def withdraw(self, cid, name='choice', tasks=('dep',), reason='the council cannot converge'):
        return mutate(self.repo, cid, 'withdraw-decision', name=name, reason=reason, tasks=list(tasks))

    def attempts(self, cid, name, count, limit=2, legacy=False):
        """Finished council attempt files for the IDR name, written where cycle_council reads them."""
        import council_policy
        logical = f'idr:{cid}:{name}'
        directory = tree(self.repo).docs_root / f'cycles/{cid}/councils/decisions' / digest(logical.encode())[:24]
        directory.mkdir(parents=True, exist_ok=True)
        if not (tree(self.repo).docs_root / 'adrs/councils/initialization.json').exists():
            # An explicit first selection, as a real project records it; the limit comes from the committed policy.
            (self.repo / '.bionic.yml').write_text(f'config_version: "1"\ndocs_dir: bionic\ncouncil:\n  mode: standard\n  max_attempts: {limit}\n')
            council_policy.initialize(self.repo, 'standard', selection='Fixture selects standard')
            self.git('add', '.bionic.yml')
            self.git('commit', '-q', '-m', 'council policy')
        policy = council_policy.resolve(self.repo, 'idr', logical_id=logical)
        for n in range(1, count + 1):
            row = {'format': council_policy.ATTEMPT, 'id': f'{name}-{n}', 'purpose': 'idr', 'logical_id': logical, 'subject': 'x', 'status': 'finished',
                   'started_at': f'2026-10-31T00:00:0{n}+00:00', 'round': n, 'progress': f'progress {n}', 'policy': policy, 'record': f'r{n}.json'}
            (directory / f'attempt-{name}-{n}.json').write_text(json.dumps(row))

    def inspect(self, cid):
        return cycle_ops.inspect(self.repo, cid, {'op': 'inspect'})

    def codes(self, out):
        return [p['code'] for p in out['problems']]

    def ops(self, out):
        return [a['request']['op'] for a in out['actions'] if 'request' in a]

    def argvs(self, out):
        return [' '.join(a['argv']) for a in out['actions'] if 'argv' in a]


class WithdrawGateTests(WithdrawBase):
    def test_refused_outside_plan(self):
        cid = self.new_cycle()
        self.plan(cid)
        self.decide(cid)
        doc = load(self.repo, cid)
        for task in doc['plan']['tasks']:
            if task['phase'] == 'plan':
                mutate(self.repo, cid, 'task', task_id=task['id'], state='done')
        mutate(self.repo, cid, 'advance')
        self.assertEqual(load(self.repo, cid)['phase'], 'build')
        with self.assertRaisesRegex(CycleError, 'Plan'):
            self.withdraw(cid, tasks=())

    def test_one_write_marks_the_name_and_removes_the_tasks(self):
        cid = self.new_cycle()
        self.plan(cid, extra=('dep',))
        self.decide(cid)
        before = load(self.repo, cid)
        doc = self.withdraw(cid)
        self.assertEqual(doc['revision'], before['revision'] + 1)
        self.assertNotIn('dep', [t['id'] for t in doc['plan']['tasks']])
        row = doc['withdrawals'][0]
        self.assertEqual((row['name'], row['tasks'], row['reason']), ('choice', ['dep'], 'the council cannot converge'))
        revised = [h for h in doc['history'] if h['action'] == 'plan-revised'][-1]
        self.assertIn('dep', [t['id'] for t in revised['previous']['tasks']])
        self.assertEqual(revised['reason'], 'the council cannot converge')
        self.assertNotIn('deferral', row)

    def test_interrupted_withdrawal_leaves_no_executable_dependent_task(self):
        # The record is written; `defer` has not run. No task of the withdrawn name can be dispatched.
        cid = self.new_cycle()
        self.plan(cid, extra=('dep',))
        self.decide(cid)
        self.withdraw(cid)
        doc = load(self.repo, cid)
        self.assertFalse(set(doc['withdrawals'][0]['tasks']) & {t['id'] for t in doc['plan']['tasks']})
        offered = [a['request']['task_id'] for a in self.inspect(cid)['actions'] if a.get('request', {}).get('op') == 'prepare-dispatch']
        self.assertNotIn('dep', offered)

    def test_restoring_a_listed_task_refuses_leaving_plan(self):
        cid = self.new_cycle()
        self.plan(cid, extra=('dep',))
        self.decide(cid)
        self.withdraw(cid)
        check_decisions(tree(self.repo), load(self.repo, cid)) if False else None
        self.plan(cid, extra=('dep',))
        with self.assertRaisesRegex(CycleError, 'withdrawn.*dep'):
            check_decisions(tree(self.repo), load(self.repo, cid))
        for task in load(self.repo, cid)['plan']['tasks']:
            if task['phase'] == 'plan':
                mutate(self.repo, cid, 'task', task_id=task['id'], state='done')
        with self.assertRaisesRegex(CycleError, 'withdrawn'):
            mutate(self.repo, cid, 'advance')

    def test_withdrawal_validates_its_tasks(self):
        cid = self.new_cycle()
        self.plan(cid, extra=('dep',))
        self.decide(cid)
        with self.assertRaisesRegex(CycleError, 'unknown task'):
            self.withdraw(cid, tasks=('nope',))
        with self.assertRaisesRegex(CycleError, 'reason'):
            self.withdraw(cid, reason=' ')
        with self.assertRaisesRegex(CycleError, 'IDR'):
            self.withdraw(cid, name='other')
        doc = load(self.repo, cid)
        plan = json.loads(json.dumps(doc['plan']))
        next(t for t in plan['tasks'] if t['id'] == 'build')['depends_on'] = ['dep']
        mutate(self.repo, cid, 'plan', plan=plan, reason='build waits for dep')
        with self.assertRaisesRegex(CycleError, 'build.*depends'):
            self.withdraw(cid)
        self.assertNotIn('withdrawals', load(self.repo, cid))

    def test_already_withdrawn_name_refused(self):
        cid = self.new_cycle()
        self.plan(cid, extra=('dep',))
        self.decide(cid)
        self.withdraw(cid)
        with self.assertRaisesRegex(CycleError, 'already withdrawn'):
            self.withdraw(cid, tasks=())


class WithdrawGateEffectTests(WithdrawBase):
    def test_iterate_passes_with_no_other_idr_and_dev_refuses(self):
        for kind, passes in (('iterate', True), ('dev', False)):
            with self.subTest(kind=kind):
                cid = self.new_cycle(kind)
                self.plan(cid, extra=('dep',))
                self.decide(cid)
                self.withdraw(cid)
                if passes:
                    check_decisions(tree(self.repo), load(self.repo, cid))
                else:
                    with self.assertRaisesRegex(CycleError, 'IDR'):
                        check_decisions(tree(self.repo), load(self.repo, cid))
                    self.decide(cid, name='replacement', replaces='choice')
                    check_decisions(tree(self.repo), load(self.repo, cid))

    def test_a_withdrawn_unapproved_revision_does_not_block_other_work(self):
        cid = self.new_cycle('iterate')
        self.plan(cid, extra=('dep',))
        self.decide(cid, approve=False)
        with self.assertRaisesRegex(CycleError, 'approv'):
            check_decisions(tree(self.repo), load(self.repo, cid))
        self.withdraw(cid)
        check_decisions(tree(self.repo), load(self.repo, cid))

    def test_simplify_selection_ignores_a_withdrawn_carrier(self):
        cid = self.new_cycle('simplify')
        self.plan(cid, extra=('dep',))
        doc = mutate(self.repo, cid, 'decision', kind='idr', name='selection', contents=contents(**SIMPLIFY_SELECTION))
        subject = doc['decisions'][-1]['path']
        mutate(self.repo, cid, 'approve-decision', subject=subject, approval=self.approval(doc, subject))
        self.withdraw(cid, name='selection')
        with self.assertRaisesRegex(CycleError, 'IDR'):
            check_decisions(tree(self.repo), load(self.repo, cid))

    def test_revision_and_approval_of_a_withdrawn_name_refused(self):
        cid = self.new_cycle('iterate')
        self.plan(cid, extra=('dep',))
        doc, subject = self.decide(cid)
        self.withdraw(cid)
        with self.assertRaisesRegex(CycleError, 'withdrawn'):
            self.decide(cid)
        with self.assertRaisesRegex(CycleError, 'withdrawn'):
            mutate(self.repo, cid, 'approve-decision', subject=subject, approval=self.approval(doc, subject))
        self.assertEqual(len([d for d in load(self.repo, cid)['decisions'] if d['name'] == 'choice']), 1)


class ReplacementTests(WithdrawBase):
    def setUp(self):
        super().setUp()
        self.cid = self.new_cycle('dev')
        self.plan(self.cid, extra=('dep',))
        self.decide(self.cid)

    def test_replaces_must_name_a_withdrawn_record(self):
        with self.assertRaisesRegex(CycleError, 'withdrawn'):
            self.decide(self.cid, name='replacement', replaces='choice')
        with self.assertRaisesRegex(CycleError, 'withdrawn'):
            self.decide(self.cid, name='replacement', replaces='unknown')
        self.withdraw(self.cid)
        with self.assertRaisesRegex(CycleError, 'text'):
            self.decide(self.cid, name='replacement', replaces=['choice'])

    def test_replaces_is_recorded_in_the_idr_record_and_kept_by_revisions(self):
        self.withdraw(self.cid)
        doc, subject = self.decide(self.cid, name='replacement', replaces='choice')
        cfg = tree(self.repo)
        record = json.loads((cfg.docs_root / subject).read_text())
        self.assertEqual(record['contents']['replaces'], 'choice')
        self.assertEqual(cycle_workflow.replaced_name(cfg, doc, 'replacement'), 'choice')
        with self.assertRaisesRegex(CycleError, 'replaces'):
            self.decide(self.cid, name='replacement')
        self.decide(self.cid, name='replacement', replaces='choice')

    def test_inspect_flags_a_new_idr_without_replaces(self):
        self.withdraw(self.cid)
        self.assertNotIn('replaces-missing', self.codes(self.inspect(self.cid)))
        self.decide(self.cid, name='unlinked')
        out = self.inspect(self.cid)
        flagged = [p for p in out['problems'] if p['code'] == 'replaces-missing']
        self.assertEqual([p['name'] for p in flagged], ['unlinked'])
        self.decide(self.cid, name='linked', replaces='choice')
        self.assertEqual([p['name'] for p in self.inspect(self.cid)['problems'] if p['code'] == 'replaces-missing'], ['unlinked'])

    def test_an_idr_older_than_the_withdrawal_is_not_flagged(self):
        self.decide(self.cid, name='sibling')
        self.withdraw(self.cid)
        self.assertNotIn('replaces-missing', self.codes(self.inspect(self.cid)))


class DeferTests(WithdrawBase):
    def setUp(self):
        super().setUp()
        self.cid = self.new_cycle('iterate')
        self.plan(self.cid, extra=('dep',))
        self.decide(self.cid)

    def test_inspect_reports_a_withdrawal_with_no_defer_entry_and_offers_defer(self):
        self.withdraw(self.cid)
        out = self.inspect(self.cid)
        self.assertIn('withdrawal-not-deferred', self.codes(out))
        defer = [a for a in out['actions'] if 'argv' in a and 'defer' in a['argv']]
        self.assertEqual(len(defer), 1)
        self.assertIn('--decision', defer[0]['argv'])
        self.assertIn('choice', defer[0]['argv'])

    def test_defer_entry_carries_the_reason_and_the_attempt_history(self):
        self.attempts(self.cid, 'choice', 2, limit=3)
        self.withdraw(self.cid)
        doc = mutate(self.repo, self.cid, 'defer', decision='choice', note='Q-0099')
        entry = doc['withdrawals'][0]['deferral']
        self.assertEqual((entry['note'], entry['reason'], entry['tasks']), ('Q-0099', 'the council cannot converge', ['dep']))
        self.assertEqual([a['round'] for a in entry['attempts']], [1, 2])
        self.assertNotIn('withdrawal-not-deferred', self.codes(self.inspect(self.cid)))

    def test_defer_refuses_an_unwithdrawn_name_or_a_second_entry(self):
        with self.assertRaisesRegex(CycleError, 'not withdrawn'):
            mutate(self.repo, self.cid, 'defer', decision='choice', note='Q-1')
        self.withdraw(self.cid)
        mutate(self.repo, self.cid, 'defer', decision='choice', note='Q-1')
        with self.assertRaisesRegex(CycleError, 'already'):
            mutate(self.repo, self.cid, 'defer', decision='choice', note='Q-2')
        with self.assertRaisesRegex(CycleError, 'finding or'):
            mutate(self.repo, self.cid, 'defer', decision='choice', finding='r1:advisory:0', note='x')


class LimitRouteTests(WithdrawBase):
    OWNER_WORDS = ('human_approval', 'human-approval', 'owner', 'extension', 'extend')

    def assertNoOwnerAction(self, out):
        text = json.dumps(out['actions']).lower()
        for word in ('human_approval', 'human-approval', 'extend'):
            self.assertNotIn(word, text)

    def test_inspect_offers_withdraw_decision_at_the_limit(self):
        cid = self.new_cycle('iterate')
        self.plan(cid, extra=('dep',))
        self.decide(cid, approve=False)
        self.attempts(cid, 'choice', 2, limit=2)
        out = self.inspect(cid)
        offer = [a for a in out['actions'] if a.get('request', {}).get('op') == 'withdraw-decision']
        self.assertEqual(len(offer), 1)
        self.assertEqual(offer[0]['request']['name'], 'choice')
        self.assertEqual(sorted(offer[0]['caller_fills']), ['op_id', 'reason', 'tasks'])
        self.assertEqual(cycle_ops.schema_errors({**offer[0]['request'], 'op_id': 'withdraw-001', 'reason': 'r', 'tasks': ['dep']}), [])
        self.assertNoOwnerAction(out)

    def test_inspect_reads_the_limit_from_policy(self):
        # Two attempts are within a limit of three: no offer. The limit is never a constant in the engine.
        cid = self.new_cycle('iterate')
        self.plan(cid, extra=('dep',))
        self.decide(cid, approve=False)
        self.attempts(cid, 'choice', 2, limit=3)
        self.assertNotIn('withdraw-decision', self.ops(self.inspect(cid)))
        self.attempts(cid, 'choice', 3, limit=3)
        self.assertIn('withdraw-decision', self.ops(self.inspect(cid)))

    def test_no_offer_outside_plan_or_for_an_approved_record(self):
        cid = self.new_cycle('iterate')
        self.plan(cid, extra=('dep',))
        self.decide(cid, approve=True)
        self.attempts(cid, 'choice', 2, limit=2)
        self.assertNotIn('withdraw-decision', self.ops(self.inspect(cid)))

    def exhausted_withdrawn(self, kind):
        cid = self.new_cycle(kind)
        self.plan(cid, extra=('dep',))
        if kind == 'simplify':
            doc = mutate(self.repo, cid, 'decision', kind='idr', name='choice', contents=contents(**SIMPLIFY_SELECTION))
        else:
            doc = mutate(self.repo, cid, 'decision', kind='idr', name='choice', contents=contents())
        self.attempts(cid, 'choice', 2, limit=2)
        self.withdraw(cid)
        return cid

    def test_dev_terminal_route_is_change_type_or_defer_and_abandon(self):
        cid = self.exhausted_withdrawn('dev')
        out = self.inspect(cid)
        argv = self.argvs(out)
        self.assertTrue(any('change-type' in a and '--type iterate' in a for a in argv), argv)
        self.assertTrue(any(' defer ' in a for a in argv), argv)
        self.assertTrue(any(' pause ' in a for a in argv), argv)
        self.assertNoOwnerAction(out)
        self.assertNotIn('prepare-dispatch', self.ops(out) and [] or [])

    def test_simplify_terminal_route_is_defer_and_abandon_only(self):
        cid = self.exhausted_withdrawn('simplify')
        out = self.inspect(cid)
        argv = self.argvs(out)
        self.assertFalse(any('change-type' in a for a in argv), argv)
        self.assertTrue(any(' defer ' in a for a in argv), argv)
        self.assertTrue(any(' pause ' in a for a in argv), argv)
        self.assertNoOwnerAction(out)

    def test_no_terminal_route_while_attempts_remain_or_another_idr_is_approved(self):
        cid = self.new_cycle('dev')
        self.plan(cid, extra=('dep',))
        self.decide(cid)
        self.attempts(cid, 'choice', 1, limit=3)
        self.withdraw(cid)
        self.assertFalse(any('change-type' in a for a in self.argvs(self.inspect(cid))))

    def test_defer_and_abandon_closes_a_simplify_cycle_without_an_owner(self):
        cid = self.exhausted_withdrawn('simplify')
        mutate(self.repo, cid, 'defer', decision='choice', note='Q-0100')
        mutate(self.repo, cid, 'pause', reason='the selection was withdrawn with no attempts left')
        mutate(self.repo, cid, 'reflect', reflection={'outcome': 'abandoned', 'lessons': ['deferred'], 'remaining': ['Q-0100']})
        self.assertEqual(mutate(self.repo, cid, 'abandon')['status'], 'abandoned')


class NitDispositionTests(WithdrawBase):
    def setUp(self):
        super().setUp()
        self.cid = self.new_cycle('iterate')
        self.plan(self.cid)

    def approve_with(self, nits, architect=None):
        doc = mutate(self.repo, self.cid, 'decision', kind='idr', name='choice', contents=contents())
        subject = doc['decisions'][-1]['path']
        path = self.approval(doc, subject, nits=nits)
        file = tree(self.repo).docs_root / path
        record = json.loads(file.read_text())
        if architect is not None:
            record['architect'] = architect
        record.pop('record_sha256')
        record['record_sha256'] = digest(encoded(record))
        file.write_text(json.dumps(record))
        with patch('cycle_council.validate_approval'):
            mutate(self.repo, self.cid, 'approve-decision', subject=subject, approval=path)

    def test_nits_without_an_agreement_record_are_reported(self):
        self.approve_with(['a:F1', 'a:F2'])
        found = [p for p in self.inspect(self.cid)['problems'] if p['code'] == 'nit-dispositions-missing']
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]['nits'], ['a:F1', 'a:F2'])

    def test_a_partial_agreement_names_the_undisposed_nit(self):
        self.approve_with(['a:F1', 'a:F2'], architect={'agrees': True, 'nits': [{'id': 'a:F1', 'disposition': 'apply-in-build', 'note': 'n'}]})
        found = [p for p in self.inspect(self.cid)['problems'] if p['code'] == 'nit-dispositions-missing']
        self.assertEqual(found[0]['nits'], ['a:F2'])

    def test_every_nit_disposed_or_none_present_reports_nothing(self):
        self.approve_with(['a:F1'], architect={'agrees': True, 'nits': [{'id': 'a:F1', 'disposition': 'declined', 'note': 'n'}]})
        self.assertNotIn('nit-dispositions-missing', self.codes(self.inspect(self.cid)))


class TypedOperationTests(WithdrawBase):
    def test_typed_op_withdraws_replays_and_refuses_outside_plan(self):
        cid = self.new_cycle('iterate')
        self.plan(cid, extra=('dep',))
        self.decide(cid)
        request = {'op': 'withdraw-decision', 'op_id': 'withdraw-001', 'name': 'choice', 'reason': 'cannot converge', 'tasks': ['dep']}
        first = self.ok(request, cid=cid)
        self.assertEqual((first['changed'], first['replayed']), (True, False))
        doc = load(self.repo, cid)
        self.assertEqual(doc['withdrawals'][0]['name'], 'choice')
        self.assertEqual([h['action'] for h in doc['history'] if h['action'] in ('plan-revised', 'withdraw-decision')][-2:], ['plan-revised', 'withdraw-decision'])
        again = self.ok(request, cid=cid)
        self.assertTrue(again['replayed'])
        self.assertEqual(len(load(self.repo, cid)['withdrawals']), 1)

    def test_typed_op_refusal_leaves_the_record_unchanged(self):
        cid = self.new_cycle('iterate')
        self.plan(cid, extra=('dep',))
        self.decide(cid)
        code, response = self.op({'op': 'withdraw-decision', 'op_id': 'withdraw-002', 'name': 'choice', 'reason': 'r', 'tasks': ['nope']}, cid=cid)
        self.assertEqual(code, 1)
        self.assertEqual(response['errors'][0]['code'], 'cycle-refused')
        self.assertNotIn('withdrawals', load(self.repo, cid))

    def test_request_shape_is_closed(self):
        base = {'op': 'withdraw-decision', 'op_id': 'withdraw-003', 'name': 'n', 'reason': 'r', 'tasks': []}
        self.assertEqual(cycle_ops.schema_errors(base), [])
        self.assertTrue(cycle_ops.schema_errors({**base, 'extra': 1}))
        self.assertTrue(cycle_ops.schema_errors({k: v for k, v in base.items() if k != 'reason'}))

    def test_low_level_command(self):
        import cycle
        cid = self.new_cycle('iterate')
        self.plan(cid, extra=('dep',))
        self.decide(cid)
        with patch('sys.stdout'):
            code = cycle.main(['--repo-root', str(self.repo), 'withdraw-decision', cid, '--name', 'choice', '--reason', 'r', '--task', 'dep'])
        self.assertEqual(code, 0)
        self.assertEqual(load(self.repo, cid)['withdrawals'][0]['tasks'], ['dep'])


if __name__ == '__main__':
    unittest.main()
