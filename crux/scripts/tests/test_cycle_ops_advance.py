"""Typed advance: revision check, shared requirements, evidence reuse, return and pause routes, parity."""
import contextlib
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cycle_ops
import cycle_workflow
from cycle_workflow import load, mutate, requirements, tree, CycleError
from test_cycle_slice import SliceBase, SCRIPTS, shared_interpreter_env
from test_evidence import execute

PASSING = {'check_id': 'unit', 'command': [sys.executable, '-c', "from pathlib import Path; assert Path('src/a.py').read_text() == 'answer = 2\\n'"],
           'inputs': ['src'], 'environment': []}
FAILING = {**PASSING, 'command': [sys.executable, '-c', 'raise SystemExit(1)']}
REVIEW = {'reviewer': 'independent', 'scope': ['src'], 'blocking': [], 'advisory': [], 'cosmetic': [], 'verdict': 'approve',
          'rationale': 'reviewed the change'}
FILLS = {'op_id': 'filled-001', 'assignment_text': 'text', 'role': 'developer', 'host': 'claude-code', 'handle': 'h', 'outcome': 'done',
         'lessons': ['l'], 'remaining': ['none'], 'quote': 'q', 'conversation': 'c', 'date': '2026-10-30'}


class AdvanceBase(SliceBase):
    def revision(self, cid=None):
        return load(self.repo, cid or self.cid)['revision']

    def advance(self, op_id, expect=None, **kw):
        return {'op': 'advance', 'op_id': op_id, 'expect_revision': self.revision(kw.get('cid')) if expect is None else expect}

    def deliver_build(self):
        prepared = self.prepare()
        sha = self.work(prepared)
        self.ok({'op': 'deliver', 'op_id': 'deliver-01', 'assignment': 'build-it', 'attempt': 1, 'outcome': 'done', 'commits': [sha]})
        return sha

    def to_test(self):
        sha = self.deliver_build()
        self.ok(self.advance('advance-b1'))
        mutate(self.repo, self.cid, 'checks', checks=['unit'])
        mutate(self.repo, self.cid, 'coverage', coverage={'affected': ['the answer'], 'checks': [{'check_id': 'unit', 'rationale': 'reads src/a.py'}],
                                                         'not_selected': 'no other behavior'})
        return sha

    def receipt(self, declaration=PASSING):
        return execute(self.repo, declaration)['evidence']['id']

    def review(self, receipt, **extra):
        mutate(self.repo, self.cid, 'review', report={**REVIEW, 'evidence': [receipt], **extra})

    def unreviewed_phase(self):
        """Review phase with a receipt attached by the typed advance."""
        self.to_test()
        receipt = self.receipt()
        self.ok(self.advance('advance-t1'))
        return receipt

    def all_actions(self, response):
        found = [r for e in response.get('errors', []) for r in e['recovery']]
        return found + response.get('actions', [])

    def check_requests_validate(self, items, extra=None):
        fills = {**FILLS, **(extra or {})}
        requests = [i for i in items if 'request' in i]
        for item in requests:
            request = {**item['request'], **{k: fills[k] for k in item['caller_fills']}}
            self.assertEqual(cycle_ops.schema_errors(request), [], item)
        return requests


class AdvancePhaseTests(AdvanceBase):
    def test_each_phase_moves_once_and_replays(self):
        self.deliver_build()
        rev = self.revision()
        first = self.ok({'op': 'advance', 'op_id': 'advance-b1', 'expect_revision': rev})
        self.assertEqual((first['changed'], first['replayed'], first['phase'], first['revision']), (True, False, 'verify', rev + 1))
        doc = load(self.repo, self.cid)
        self.assertEqual(doc['phase'], 'verify')
        self.assertEqual(doc['history'][-1]['action'], 'advance'); self.assertEqual(doc['history'][-1]['op_id'], 'advance-b1')
        # Retry: same request replays and leaves the record bytes unchanged.
        before = self.record_path().read_bytes()
        again = self.ok({'op': 'advance', 'op_id': 'advance-b1', 'expect_revision': rev})
        self.assertEqual((again['replayed'], again['changed'], again['phase']), (True, False, 'verify'))
        self.assertEqual(self.record_path().read_bytes(), before)
        # Test phase: a missing receipt refuses, then a receipt moves the phase.
        mutate(self.repo, self.cid, 'checks', checks=['unit'])
        mutate(self.repo, self.cid, 'coverage', coverage={'affected': ['x'], 'checks': [{'check_id': 'unit', 'rationale': 'r'}], 'not_selected': 'none'})
        self.refused(self.advance('advance-t0'), 'requirement-unmet')
        receipt = self.receipt()
        self.assertEqual(self.ok(self.advance('advance-t1'))['phase'], 'review')
        self.refused(self.advance('advance-r0'), 'requirement-unmet')
        self.review(receipt)
        self.assertEqual(self.ok(self.advance('advance-r1'))['phase'], 'reflect')
        response = self.refused(self.advance('advance-f0'), 'finish-required')
        recovery = response['errors'][0]['recovery']
        self.assertEqual([r['request']['op'] for r in recovery], ['finish'])
        self.check_requests_validate(recovery)

    def test_schema_requires_expect_revision(self):
        response = self.refused({'op': 'advance', 'op_id': 'advance-01'}, 'invalid-request')
        self.assertEqual(response['errors'][0]['field'], 'expect_revision')
        self.refused({'op': 'advance', 'op_id': 'advance-01', 'expect_revision': 1, 'extra': 1}, 'invalid-request')

    def test_unmet_items_each_get_an_error_with_a_targeted_recovery(self):
        self.prepare()
        response = self.refused(self.advance('advance-b0'), 'requirement-unmet')
        error = response['errors'][0]
        self.assertEqual(error['field'], 'phase-tasks')
        self.assertEqual(error['recovery'][0]['request'], {'op': 'inspect'})
        self.check_requests_validate(error['recovery'])

    def test_missing_check_error_recovery_targets_the_check(self):
        self.to_test()
        response = self.refused(self.advance('advance-t0'), 'requirement-unmet')
        error = response['errors'][0]
        self.assertEqual(error['field'], 'tests')
        argv = error['recovery'][0]['argv']
        self.assertEqual(argv[argv.index('--check-id') + 1], 'unit')
        self.assertIn('evidence', argv)

    def test_stale_revision_lists_newer_actions_and_recovers_only_by_inspect(self):
        self.deliver_build()
        stale = self.revision()
        self.ok(self.advance('advance-b1'))
        response = self.refused({'op': 'advance', 'op_id': 'advance-b2', 'expect_revision': stale}, 'stale-revision')
        error = response['errors'][0]
        self.assertEqual((error['field'], error['expected'], error['observed']), ('expect_revision', self.revision(), stale))
        self.assertIn('advance', error['problem'])
        self.assertEqual([r['request'] for r in error['recovery']], [{'op': 'inspect'}])
        self.assertNotIn('expect_revision', json.dumps(error['recovery']))

    def test_closed_cycle_is_refused(self):
        self.to_test()
        raw = json.loads(self.record_path().read_text()); raw['status'] = 'abandoned'
        self.record_path().write_text(json.dumps(raw))
        self.refused(self.advance('advance-b0'), 'cycle-closed')


class ConcurrencyTests(AdvanceBase):
    def spawn(self, request):
        return subprocess.Popen([sys.executable, str(SCRIPTS / 'cycle.py'), '--repo-root', str(self.repo), '--compact', 'op',
                                 self.cid, '--json', json.dumps(request)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=SCRIPTS, env=shared_interpreter_env())

    def test_two_advances_with_one_expected_revision_make_one_transition(self):
        self.deliver_build()
        rev = self.revision()
        procs = [self.spawn({'op': 'advance', 'op_id': f'advance-p{n}', 'expect_revision': rev}) for n in (1, 2)]
        outputs = [(p.communicate(), p.returncode) for p in procs]
        results = [(code, json.loads(out[0])) for out, code in outputs]
        self.assertEqual(sorted(code for code, _ in results), [0, 1], outputs)
        refused = [r for code, r in results if code == 1][0]
        self.assertEqual(refused['errors'][0]['code'], 'stale-revision')
        doc = load(self.repo, self.cid)
        self.assertEqual(doc['phase'], 'verify')
        self.assertEqual([e['action'] for e in doc['history']].count('advance'), 1)
        self.assertEqual(len(doc['operations']) - len([o for o in doc['operations'] if o['op'] != 'advance']), 1)

    def test_two_advances_with_one_op_id_make_one_transition_and_one_replay(self):
        self.deliver_build()
        request = {'op': 'advance', 'op_id': 'advance-same', 'expect_revision': self.revision()}
        procs = [self.spawn(request) for _ in (1, 2)]
        outputs = [p.communicate()[0] for p in procs]
        self.assertEqual([p.returncode for p in procs], [0, 0], outputs)
        results = [(p.returncode, json.loads(out)) for p, out in zip(procs, outputs)]
        self.assertEqual(sorted(r['replayed'] for _, r in results), [False, True])
        self.assertEqual(load(self.repo, self.cid)['phase'], 'verify')


class ReuseTests(AdvanceBase):
    def test_a_matching_receipt_is_attached_as_reused(self):
        self.to_test()
        receipt = self.receipt()
        seen = self.ok({'op': 'inspect'})
        self.assertEqual(seen['reusable_evidence'], [{'check_id': 'unit', 'evidence_id': receipt}])
        done = self.ok(self.advance('advance-t1'))
        self.assertEqual(done['phase'], 'review')
        doc = load(self.repo, self.cid)
        ref = doc['evidence'][-1]
        self.assertEqual((ref['check_id'], ref['evidence_id'], ref['use'], ref['pass']), ('unit', receipt, 'reused', 1))
        self.assertRegex(ref['declaration_sha256'], '^[0-9a-f]{64}$')

    def test_the_low_level_advance_attaches_nothing(self):
        self.to_test()
        self.receipt()
        with self.assertRaisesRegex(CycleError, 'missing passing evidence for unit'):
            mutate(self.repo, self.cid, 'advance')
        self.assertEqual(load(self.repo, self.cid)['evidence'], [])

    def test_a_source_change_between_lookup_and_lock_refuses(self):
        self.to_test()
        self.receipt()
        real = cycle_ops.locked
        @contextlib.contextmanager
        def changing(repo):
            (self.repo / 'src/a.py').write_text('answer = 2\n# moved\n')
            with real(repo) as held:
                yield held
        before = self.record_path().read_bytes()
        with patch.object(cycle_ops, 'locked', changing):
            code, response = self.op(self.advance('advance-t1'))
        self.assertEqual(code, 1, response)
        self.assertEqual([e['code'] for e in response['errors']], ['evidence-changed'])
        self.assertEqual(self.record_path().read_bytes(), before)
        self.assertEqual(response['errors'][0]['recovery'][0]['request'], {'op': 'inspect'})

    def test_the_lookup_runs_before_the_lock(self):
        self.to_test()
        self.receipt()
        order = []
        real_lock, real_find = cycle_ops.locked, cycle_ops.reusable_receipts
        @contextlib.contextmanager
        def tracking(repo):
            order.append('lock')
            with real_lock(repo) as held:
                yield held
        def finding(*a, **k):
            order.append('lookup')
            return real_find(*a, **k)
        with patch.object(cycle_ops, 'locked', tracking), patch.object(cycle_ops, 'reusable_receipts', finding):
            self.ok(self.advance('advance-t1'))
        self.assertEqual(order[:2], ['lookup', 'lock'])

    def test_a_failed_receipt_is_never_attached(self):
        self.to_test()
        failed = execute(self.repo, FAILING)['evidence']
        self.assertNotEqual(failed['status'], 'passed')
        self.assertEqual(self.ok({'op': 'inspect'})['reusable_evidence'], [])
        response = self.refused(self.advance('advance-t1'), 'requirement-unmet')
        self.assertEqual(response['errors'][0]['field'], 'tests')
        self.assertEqual(load(self.repo, self.cid)['evidence'], [])

    def test_a_receipt_for_changed_inputs_is_not_reusable(self):
        self.to_test()
        self.receipt()
        (self.repo / 'src/a.py').write_text('answer = 2\n# edit\n')
        self.assertEqual(self.ok({'op': 'inspect'})['reusable_evidence'], [])

    def test_build_checks_are_reused_too(self):
        self.deliver_build()
        mutate(self.repo, self.cid, 'checks', checks=['unit'], phase='build')
        self.refused(self.advance('advance-b0'), 'requirement-unmet')
        receipt = self.receipt()
        self.assertEqual(self.ok({'op': 'inspect'})['reusable_evidence'], [{'check_id': 'unit', 'evidence_id': receipt}])
        self.assertEqual(self.ok(self.advance('advance-b1'))['phase'], 'verify')
        self.assertEqual(load(self.repo, self.cid)['evidence'][-1]['use'], 'reused')


class ReturnRouteTests(AdvanceBase):
    def changes_required(self):
        receipt = self.unreviewed_phase()
        self.review(receipt, verdict='changes-required', blocking=[{'path': 'src/a.py', 'consequence': 'wrong', 'evidence': 'reads 1'}])
        return receipt

    def test_review_requesting_changes_refuses_and_inspect_offers_return(self):
        self.changes_required()
        response = self.refused(self.advance('advance-r1'), 'requirement-unmet')
        self.assertEqual(response['errors'][0]['field'], 'review')
        seen = self.ok({'op': 'inspect'})
        argvs = [a for a in self.all_actions(seen) if 'argv' in a]
        self.assertEqual([a['argv'][6] for a in argvs], ['return', 'pause'])
        self.assertEqual(argvs[0]['caller_fills'], ['--improved', '--unresolved', '--next-change', '--justification', '--progress'])
        self.assertNotIn('advance', [a['request']['op'] for a in seen['actions'] if 'request' in a])
        self.assertEqual([a['argv'][6] for a in self.all_actions(response) if 'argv' in a], ['return', 'pause'])

    def test_pause_is_offered_only_when_the_limit_is_exhausted(self):
        self.changes_required()
        raw = json.loads(self.record_path().read_text()); raw['pass_limit'] = 3
        self.record_path().write_text(json.dumps(raw))
        argvs = [a['argv'][6] for a in self.ok({'op': 'inspect'})['actions'] if 'argv' in a]
        self.assertEqual(argvs, ['return'])


class ParityTests(AdvanceBase):
    """Low-level advance, typed advance, inspect and finish read one policy."""

    def first_problem(self):
        with self.assertRaises(CycleError) as caught:
            mutate(self.repo, self.cid, 'advance')
        return str(caught.exception)

    def test_missing_receipt_agrees_everywhere(self):
        self.to_test()
        problem = self.first_problem()
        response = self.refused(self.advance('advance-t0'), 'requirement-unmet')
        seen = self.ok({'op': 'inspect'})
        self.assertEqual(response['errors'][0]['problem'], problem)
        self.assertEqual(seen['unmet']['next'][0]['problem'], problem)
        self.assertEqual(seen['reusable_evidence'], [])
        self.assertNotIn('advance', [a['request']['op'] for a in seen['actions'] if 'request' in a])
        cfg = tree(self.repo)
        self.assertEqual(requirements(cfg, load(self.repo, self.cid), 'next', first=True)[0]['problem'], problem)

    def test_reusable_receipt_is_offered_then_attached(self):
        self.to_test()
        problem = self.first_problem()
        receipt = self.receipt()
        self.assertEqual(self.first_problem(), problem)
        seen = self.ok({'op': 'inspect'})
        self.assertEqual(seen['unmet']['next'][0]['problem'], problem)
        offered = [a for a in seen['actions'] if a.get('request', {}).get('op') == 'advance']
        self.assertEqual(len(offered), 1)
        self.assertEqual(offered[0]['request'], {'op': 'advance', 'expect_revision': seen['revision']})
        self.assertEqual(offered[0]['caller_fills'], ['op_id'])
        self.assertEqual(seen['reusable_evidence'], [{'check_id': 'unit', 'evidence_id': receipt}])
        done = self.ok({**offered[0]['request'], 'op_id': 'advance-t1'})
        self.assertEqual(done['phase'], 'review')

    def test_finish_and_inspect_agree_at_reflect(self):
        self.to_test()
        receipt = self.receipt()
        self.ok(self.advance('advance-t1')); self.review(receipt); self.ok(self.advance('advance-r1'))
        seen = self.ok({'op': 'inspect'})
        self.assertEqual(seen['unmet']['completion'], [])
        self.assertEqual([a for a in seen['actions'] if a.get('request', {}).get('op') == 'advance'], [])
        # Dirty the scope: both inspect and finish report the same completion requirement.
        (self.repo / 'src/a.py').write_text('answer = 5\n')
        seen = self.ok({'op': 'inspect'})
        finish = {'op': 'finish', 'op_id': 'finish-001', 'expect_revision': seen['revision'], 'lessons': ['l'], 'remaining': ['none']}
        self.assertTrue(seen['unmet']['completion'])
        response = self.refused(finish, *['requirement-unmet'] * len(seen['unmet']['completion']))
        self.assertEqual([(e['field'], e['problem']) for e in response['errors']],
                         [(i['requirement'], i['problem']) for i in seen['unmet']['completion']])

    def test_requirements_match_the_checks_in_the_old_order(self):
        """Historical evidence fixtures evaluate to the same results through `requirements` as through the direct checks."""
        cfg = tree(self.repo)
        def direct(doc):
            order = [('decisions', cycle_workflow.check_decisions)]
            unfinished = lambda d: [f"{t['id']} ({t['status']})" for t in d['plan']['tasks'] if t['phase'] == d['phase'] and t['status'] != 'done']
            tasks = lambda c, d: (_ for _ in ()).throw(CycleError('current phase has unfinished tasks: ' + '; '.join(unfinished(d)))) if unfinished(d) else None
            order.append(('phase-tasks', tasks))
            if doc['phase'] == 'build':
                order.append(('build-checks', cycle_workflow.check_build))
            elif doc['phase'] in ('test', 'verify'):
                order.append(('tests', cycle_workflow.check_tests))
            elif doc['phase'] == 'review':
                order += [('tests', cycle_workflow.check_tests), ('review', cycle_workflow.check_review)]
            out = []
            for name, check in order:
                try:
                    check(cfg, doc)
                except CycleError as exc:
                    out.append({'requirement': name, 'problem': str(exc)})
            return out
        states = [load(self.repo, self.cid)]
        self.to_test()
        states.append(load(self.repo, self.cid))
        receipt = self.receipt()
        mutate(self.repo, self.cid, 'evidence', check_id='unit', evidence_id=receipt, use='executed')
        states.append(load(self.repo, self.cid))
        mutate(self.repo, self.cid, 'advance'); states.append(load(self.repo, self.cid))
        self.review(receipt); states.append(load(self.repo, self.cid))
        (self.repo / 'src/a.py').write_text('answer = 2\n# later\n'); states.append(load(self.repo, self.cid))
        for doc in states:
            self.assertEqual(requirements(cfg, doc, 'next'), direct(doc), doc['phase'])


class DeclarationRouteTests(AdvanceBase):
    """An unmet Verify (or Test) or Review declaration comes with the low-level command that records it."""

    def routes(self, response):
        return [a for a in self.all_actions(response) if 'argv' in a]

    def to_empty_test(self):
        self.deliver_build()
        self.ok(self.advance('advance-b1'))

    def assert_route(self, found, command, fills):
        self.assertEqual([a['argv'][6] for a in found], [command])
        self.assertEqual(found[0]['caller_fills'], fills)
        self.assertEqual(found[0]['argv'][-2:], [command, self.cid])

    def test_undeclared_checks_are_offered_in_inspect_and_the_refusal(self):
        self.to_empty_test()
        self.assert_route(self.routes(self.ok({'op': 'inspect'})), 'checks', ['--check'])
        refused = self.refused(self.advance('advance-t0'), 'requirement-unmet')
        self.assertEqual(refused['errors'][0]['field'], 'tests')
        self.assert_route(self.routes(refused), 'checks', ['--check'])

    def test_undeclared_coverage_follows_the_checks(self):
        self.to_empty_test()
        mutate(self.repo, self.cid, 'checks', checks=['unit'])
        self.assert_route(self.routes(self.ok({'op': 'inspect'})), 'coverage', ['--json'])
        refused = self.refused(self.advance('advance-t0'), 'requirement-unmet')
        # The refusal also carries the evidence route for the check still lacking a receipt.
        self.assert_route(self.routes(refused)[:1], 'coverage', ['--json'])

    def test_declared_checks_and_coverage_offer_only_the_evidence_route(self):
        self.to_test()
        self.assertEqual(self.routes(self.ok({'op': 'inspect'})), [])
        refused = self.refused(self.advance('advance-t0'), 'requirement-unmet')
        self.assertEqual([a['argv'][6] for a in self.routes(refused)], ['evidence'])

    def test_a_missing_review_report_is_offered_in_inspect_and_the_refusal(self):
        self.unreviewed_phase()
        self.assert_route(self.routes(self.ok({'op': 'inspect'})), 'review', ['--json'])
        refused = self.refused(self.advance('advance-r0'), 'requirement-unmet')
        self.assertEqual(refused['errors'][0]['field'], 'review')
        self.assert_route(self.routes(refused), 'review', ['--json'])

    def test_no_review_route_while_the_tests_requirement_is_unmet(self):
        self.unreviewed_phase()
        self.assert_route(self.routes(self.ok({'op': 'inspect'})), 'review', ['--json'])
        mutate(self.repo, self.cid, 'checks', checks=['unit', 'other'])
        mutate(self.repo, self.cid, 'coverage', coverage={'affected': ['the answer'], 'not_selected': 'no other behavior',
                                                         'checks': [{'check_id': 'unit', 'rationale': 'reads src/a.py'},
                                                                    {'check_id': 'other', 'rationale': 'reads src/a.py'}]})
        seen = self.ok({'op': 'inspect'})
        self.assertEqual(seen['phase'], 'review')
        self.assertEqual([a['argv'][6] for a in self.routes(seen)], [])

    def test_inspect_leaves_the_record_unchanged_in_review(self):
        self.unreviewed_phase()
        before = self.record_path().read_bytes()
        self.check_requests_validate(self.all_actions(self.ok({'op': 'inspect'})))
        self.assertEqual(self.record_path().read_bytes(), before)


class RecoveryActionTests(AdvanceBase):
    def test_every_action_validates_against_the_schema(self):
        self.to_test()
        receipt = self.receipt()
        seen = self.ok({'op': 'inspect'})
        stale = self.refused({'op': 'advance', 'op_id': 'advance-x1', 'expect_revision': 1}, 'stale-revision')
        items = self.all_actions(seen) + self.all_actions(stale)
        requests = self.check_requests_validate(items)
        self.assertIn('advance', [r['request']['op'] for r in requests])
        self.assertTrue(receipt)


if __name__ == '__main__':
    unittest.main()
