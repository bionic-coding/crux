"""Engine routing for the four classifications: routes, fallbacks, boundaries and offered actions.

Every provider answer is scripted; no test sends a request. See _classify_support for the fixtures."""
import json
import re
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cycle_classify
import cycle_ops
import cycle_questions
from crux import decisions
from cycle_workflow import load, locked, mutate, save
from _classify_support import BLOCKING, ClassifyBase, MODEL, SimulatedCrash, answered, failed, review_reply

HEX64 = re.compile(r'^[0-9a-f]{64}$')


class ReviewRoutingTests(ClassifyBase):
    def test_floor_only_is_recorded_and_inspect_lists_the_floor(self):
        response = self.enter_review(answered('floor-only', probabilities={'floor-only': 0.9, 'insufficient-information': 0.1}))
        entries = self.entries('review-routing')
        # One predicate per specialist not on the floor: the fixture floor is empty, so every specialist is asked.
        self.assertEqual([e['subject'] for e in entries], [f'review:{i}' for i in cycle_classify.SPECIALISTS])
        for entry in entries:
            self.assertEqual((entry['route'], entry['fallback'], entry['question_version']), ('floor-only', None, '2'))
            self.assertRegex(entry['fingerprint'], HEX64)
            self.assertEqual((entry['request_id'], entry['served_model'], entry['model']), ('gen-req-0001', MODEL, MODEL))
            self.assertEqual(entry['answer'], {'choice': 'floor-only', 'probabilities': {'floor-only': 0.9, 'insufficient-information': 0.1}})
            self.assertEqual(entry['revision'], response['revision'])
        self.assertEqual(response['revision'], load(self.repo, self.cid)['revision'])
        self.assertEqual([c['route'] for c in response['classifications']], ['floor-only'] * len(cycle_classify.SPECIALISTS))
        review = self.inspect()['review']
        self.assertEqual((review['floor'], review['added'], review['specialists']), ([], [], []))

    def test_the_low_level_advance_into_review_asks_and_returns_the_post_write_revision(self):
        self.to_test()
        mutate(self.repo, self.cid, 'evidence', check_id='unit', evidence_id=self.receipt(), use='executed')
        self.review = review_reply(answered('add:release-distribution'))
        code, response = self.cli('advance')
        self.assertEqual(code, 0, response)
        routes = {c['subject']: c['route'] for c in response['classifications']}
        self.assertEqual(routes['review:release-distribution'], 'add:release-distribution')
        self.assertEqual({r for s, r in routes.items() if s != 'review:release-distribution'}, {'floor-only'})
        self.assertEqual((response['revision'], response['cycle']['revision']), (load(self.repo, self.cid)['revision'],) * 2)
        self.assertEqual({e['revision'] for e in self.entries('review-routing')}, {response['revision']})

    def test_options_are_one_predicate_per_specialist_outside_the_floor(self):
        mutate(self.repo, self.cid, 'scrutiny', scrutiny='intensive', rationale='release work', risks=['release'])
        self.enter_review(answered('floor-only'))
        ids = [i for i in cycle_classify.SPECIALISTS if i != 'release-distribution']
        self.assertEqual([a['id'] for a in self.asked], [f'review:{i}' for i in ids], 'no question for a specialist already on the floor')
        for call, ident in zip(self.asked, ids):
            self.assertEqual(list(call['question'].options), [f'add:{ident}', 'floor-only', 'insufficient-information'])
        self.assertEqual(self.inspect()['review']['floor'], ['release-distribution'])

    def test_an_addition_is_kept_and_listed_for_the_reviewer_assignment(self):
        self.add_review_task()
        self.enter_review(answered('add:authentication-and-authorization'))
        entry = self.review_entry('authentication-and-authorization')
        self.assertEqual((entry['route'], entry['subject']), ('add:authentication-and-authorization', 'review:authentication-and-authorization'))
        self.assertEqual({e['route'] for e in self.entries('review-routing') if e['subject'] != entry['subject']}, {'floor-only'})
        seen = self.inspect()
        self.assertEqual(seen['review']['specialists'], ['authentication-and-authorization'])
        dispatch = next(a for a in seen['actions'] if a.get('request', {}).get('task_id') == 'review-it')
        self.assertEqual(dispatch['specialists'], ['authentication-and-authorization'])
        self.assertIn('authentication-and-authorization', dispatch['purpose'])

    def test_review_commissioned_ends_the_offered_addition_but_not_the_floor(self):
        self.add_review_task()
        mutate(self.repo, self.cid, 'scrutiny', scrutiny='standard', rationale='r', risks=['release'])
        self.enter_review(answered('add:untrusted-input-execution'))
        self.assertEqual(self.inspect()['review']['specialists'], ['release-distribution', 'untrusted-input-execution'])
        self.ok({'op': 'prepare-dispatch', 'op_id': 'prep-rev1', 'task_id': 'review-it', 'role': 'reviewer', 'host': 'claude-code', 'assignment_text': 'review'})
        after = self.inspect()['review']
        self.assertEqual((after['added'], after['specialists']), ([], ['release-distribution']))

    def test_the_floor_comes_from_changed_paths_and_risks_whatever_the_type(self):
        with mock.patch.object(cycle_classify, 'changed_paths', return_value=['crux/scripts/release_gate.py', 'src/auth_login.py', 'src/readme.md']):
            doc = load(self.repo, self.cid)
            for kind in ('quick-fix', 'dev'):
                doc['type'] = kind
                floor = cycle_classify.review_floor(cycle_ops.tree(self.repo), doc)
                self.assertEqual(floor['specialists'], ['release-distribution', 'authentication-and-authorization'], kind)

    def test_floor_and_decision_dependency_stay_in_force_for_a_sized_quick_fix(self):
        # The sizing answer picked quick-fix; a material decision is still refused and the floor still counts risks.
        with self.assertRaisesRegex(Exception, 'material decisions require changing quick-fix'):
            mutate(self.repo, self.cid, 'decision', kind='idr', name='x', contents={'alternatives': ['a'], 'approach': ['b'], 'assumptions': ['c'],
                                                                                    'constraints': ['d'], 'intended_evidence': ['e']})
        mutate(self.repo, self.cid, 'scrutiny', scrutiny='intensive', rationale='r', risks=['credentials'])
        self.enter_review(answered('floor-only'))
        self.assertEqual(self.inspect()['review']['floor'], ['credentials-and-data-transmission'])


class FindingDispositionTests(ClassifyBase):
    def reply_by_finding(self, table):
        """Answers keyed on the question id, which is the finding's id."""
        return {key: answered(choice) for key, choice in table.items()}

    def test_the_findings_of_one_report_share_one_request_with_the_shared_review_facts_and_one_transaction(self):
        self.enter_review(answered('floor-only'))
        before = load(self.repo, self.cid)['revision']
        self.asked.clear()
        self.default = self.reply_by_finding({'r1:blocking:0': 'fix-step', 'r1:advisory:0': 'follow-up', 'r1:cosmetic:0': 'agent-assessment'})
        requests = []
        real = decisions.ask_many

        def recording(state, questions, *, deadline, client=None, kinds=()):
            requests.append((state, list(questions)))
            return real(state, questions, deadline=deadline, client=client, kinds=kinds)
        with mock.patch.object(decisions, 'ask_many', recording):
            code, response = self.record_review(self.receipt_id, self.blocking_report())
        self.assertEqual(code, 0, response)
        (state, ids), = requests
        self.assertEqual(ids, ['r1:blocking:0', 'r1:advisory:0', 'r1:cosmetic:0'], 'one request carries every finding question')
        self.assertEqual([f['id'] for f in state['findings']], ids, 'the shared state lists the batch\'s findings')
        for finding in state['findings']:
            self.assertEqual(set(finding), {'id', 'category', 'title', 'text'})
        self.assertEqual(set(state['review']), set(cycle_classify.SHARED_REVIEW_FACTS))
        self.assertEqual(set(state), set(cycle_classify.STATE_FIELDS['finding-disposition']))
        self.assertEqual([a['id'] for a in self.asked], ids)
        for call in self.asked:
            self.assertIs(call['state'], state)
            self.assertTrue(call['lock_free'], 'the request was sent with the cycle lock held')
        entries = self.entries('finding-disposition')
        self.assertEqual([e['route'] for e in entries], ['fix-step', 'follow-up', 'agent-assessment'])
        self.assertEqual({e['revision'] for e in entries}, {before + 2}, 'review commits once, then one classification transaction')
        self.assertEqual(response['revision'], before + 2)
        self.assertEqual(len(self.asked), 3, 'the operation re-asked: its own writes counted as a stale change')
        events = [e['action'] for e in load(self.repo, self.cid)['history']]
        self.assertEqual(events[-2:], ['review', 'classified'])

    def test_a_blocking_finding_is_offered_only_fix_routes(self):
        self.review_with_findings(answered('return'), answered('agent-assessment'), answered('follow-up'))
        blocking, advisory, cosmetic = (self.asked[i]['question'].options for i in range(3))
        self.assertEqual(list(blocking), ['fix-step', 'return', 'insufficient-information'])
        self.assertEqual(list(advisory), ['fix-step', 'follow-up', 'agent-assessment', 'insufficient-information'])
        self.assertEqual(list(cosmetic), ['fix-step', 'follow-up', 'agent-assessment', 'insufficient-information'])

    def test_a_return_answer_for_a_non_blocking_finding_is_not_kept(self):
        self.review_with_findings(answered('return'), answered('return'), answered('return'))
        self.assertEqual([(e['subject'], e['route'], e['fallback']) for e in self.entries('finding-disposition')],
                         [('r1:blocking:0', 'return', None), ('r1:advisory:0', None, 'route-not-permitted'),
                          ('r1:cosmetic:0', None, 'route-not-permitted')])

    def test_fix_step_route_offers_task_add_and_stops_after_the_fix_task_is_added(self):
        self.review_with_findings(answered('fix-step'), answered('insufficient-information'), answered('insufficient-information'))
        first = self.inspect()['actions'][0]
        self.assertEqual((first['classification']['route'], first['classification']['subject']), ('fix-step', 'r1:blocking:0'))
        self.assertEqual(first['caller_fills'], ['--json'])
        self.assertEqual(first['argv'][first['argv'].index('task-add'):], ['task-add', self.cid, '--json'])
        mutate(self.repo, self.cid, 'task-add', task={'id': 'fix-1', 'phase': 'review', 'description': 'fix it', 'depends_on': [], 'status': 'pending',
                                                       'expected_evidence': ['commit'], 'fix': {'finding': 'r1:blocking:0', 'eligibility': 'one line'}})
        self.assertFalse([a for a in self.inspect()['actions'] if a.get('classification', {}).get('route') == 'fix-step'])

    def test_return_route_offers_the_counted_return_with_its_four_texts(self):
        self.review_with_findings(answered('return'), answered('insufficient-information'), answered('insufficient-information'))
        first = self.inspect()['actions'][0]
        self.assertEqual(first['classification']['route'], 'return')
        self.assertEqual(first['caller_fills'], ['--improved', '--unresolved', '--next-change', '--justification', '--progress'])
        self.assertIn('return', first['argv'])

    def test_follow_up_route_offers_defer_with_the_note_to_fill_and_defer_changes_the_status_fact(self):
        report = {'verdict': 'approve', 'blocking': [], 'advisory': ['LEAK-ZQ-advisory docstring'], 'cosmetic': []}
        self.review_with_findings(answered('follow-up'), report=report)
        first = self.inspect()['actions'][0]
        self.assertEqual((first['classification']['route'], first['caller_fills']), ('follow-up', ['--note']))
        self.assertEqual(first['argv'][first['argv'].index('defer'):], ['defer', self.cid, '--finding', 'r1:advisory:0', '--note'])
        code, response = self.cli('defer', '--finding', 'r1:advisory:0', '--note', 'tracked in the backlog')
        self.assertEqual(code, 0, response)
        deferral = load(self.repo, self.cid)['deferrals'][0]
        self.assertEqual((deferral['finding'], deferral['pass'], deferral['phase']), ('r1:advisory:0', 1, 'review'))
        self.assertFalse([a for a in self.inspect()['actions'] if a.get('classification')], 'a deferral is a status-fact change')

    def test_defer_refuses_a_blocking_finding_a_second_deferral_a_bad_id_and_an_empty_note(self):
        self.review_with_findings(answered('insufficient-information'), answered('insufficient-information'), answered('insufficient-information'))
        for argv, fragment in ((('--finding', 'r1:blocking:0', '--note', 'later'), 'never deferred'),
                               (('--finding', 'nonsense', '--note', 'later'), 'finding id looks like'),
                               (('--finding', 'r1:advisory:9', '--note', 'later'), 'not a finding'),
                               (('--finding', 'r1:advisory:0', '--note', '  '), 'needs a note')):
            code, response = self.cli('defer', *argv)
            self.assertEqual(code, 1, argv); self.assertIn(fragment, response['error'])
        self.assertEqual(self.cli('defer', '--finding', 'r1:advisory:0', '--note', 'ok')[0], 0)
        self.assertIn('already deferred', self.cli('defer', '--finding', 'r1:advisory:0', '--note', 'again')[1]['error'])

    def test_agent_assessment_route_is_offered_until_the_agent_acts(self):
        report = {'verdict': 'approve', 'blocking': [], 'advisory': ['LEAK-ZQ-advisory docstring'], 'cosmetic': []}
        self.review_with_findings(answered('agent-assessment'), report=report)
        first = self.inspect()['actions'][0]
        self.assertTrue(first['agent'])
        self.assertEqual(first['classification']['route'], 'agent-assessment')
        self.assertNotIn('request', first); self.assertNotIn('argv', first)
        self.assertTrue(self.inspect()['actions'][0]['agent'], 'an unchanged status fact keeps the agent route offered')
        self.cli('defer', '--finding', 'r1:advisory:0', '--note', 'the agent acted')
        self.assertFalse([a for a in self.inspect()['actions'] if a.get('agent')])

    def test_a_fix_step_for_an_ineligible_finding_is_refused_at_write_time(self):
        mutate(self.repo, self.cid, 'scrutiny', scrutiny='standard', rationale='r', risks=[])
        two = {'verdict': 'changes-required', 'blocking': [BLOCKING, {**BLOCKING, 'path': 'src/b.py'}], 'advisory': [], 'cosmetic': []}
        # Two blocking findings no longer make a fix ineligible; the writer's own refusal text stands in for any ineligibility.
        with mock.patch.object(cycle_classify, 'fix_step_problem', lambda doc, cfg: 'one fix task per phase per pass'):
            self.review_with_findings(answered('fix-step'), answered('fix-step'), report=two)
        self.assertEqual([list(a['question'].options) for a in self.asked], [['return', 'insufficient-information']] * 2)
        self.assertEqual([e['fallback'] for e in self.entries('finding-disposition')], ['route-not-permitted'] * 2)


class FailureRoutingTests(ClassifyBase):
    def test_failed_delivery_re_dispatch_is_offered_and_stops_when_dispatched(self):
        response = self.failed_delivery(answered('re-dispatch'))
        entry = self.entries('failure-routing')[0]
        self.assertEqual((entry['route'], entry['subject'], entry['trigger']), ('re-dispatch', 'build-it', 'delivery:build-it/1'))
        self.assertEqual(response['revision'], load(self.repo, self.cid)['revision'])
        first = self.inspect()['actions'][0]
        self.assertEqual(first['request'], {'op': 'prepare-dispatch', 'task_id': 'build-it', 'role': 'developer', 'host': 'claude-code'})
        self.assertEqual(first['caller_fills'], ['op_id'])
        self.prepare('prep-0009')
        self.assertFalse([a for a in self.inspect()['actions'] if a.get('classification')])

    def test_a_classified_re_dispatch_in_review_keeps_the_floor_specialists(self):
        self.add_review_task()
        mutate(self.repo, self.cid, 'scrutiny', scrutiny='standard', rationale='r', risks=['release'])
        self.enter_review(answered('floor-only'))
        prepared = self.ok({'op': 'prepare-dispatch', 'op_id': 'prep-rev1', 'task_id': 'review-it', 'role': 'reviewer', 'host': 'claude-code', 'assignment_text': 'review'})
        self.write_result(prepared)
        self.replies[:] = [answered('re-dispatch')]
        self.ok({'op': 'deliver', 'op_id': 'deliver-rev1', 'assignment': prepared['assignment'], 'attempt': 1, 'outcome': 'failed'})
        redispatch = next(a for a in self.inspect()['actions'] if a.get('classification', {}).get('route') == 're-dispatch')
        self.assertEqual(redispatch['request']['task_id'], 'review-it')
        self.assertEqual(redispatch['specialists'], ['release-distribution'])
        self.assertIn('release-distribution', redispatch['purpose'])

    def test_unresolved_dispatch_mark_lost_is_conditional_and_stops_when_applied(self):
        self.prepare()
        self.replies[:] = [answered('mark-lost')]
        response = self.refused_with_entry(self.second_reservation(), 'unresolved-dispatch', 'task-not-eligible')
        self.assertEqual(response['recovery_handlers'][0]['code'], 'unresolved-dispatch')
        self.assertEqual((self.asked, self.entries('failure-routing')), ([], []))
        first = response['recovery_handlers'][0]['actions'][0]
        self.assertEqual((first['request']['op'], first['caller_fills']), ('inspect', []))
        self.lose('lost-0001')
        self.assertFalse([a for a in self.inspect()['actions'] if a.get('classification')])

    def test_failed_check_return_route_offers_the_counted_return(self):
        self.to_test()
        receipt = self.failing_receipt()
        with locked(self.repo) as (cfg, _):
            doc = load(self.repo, self.cid)
            doc['pass_limit'] = 2
            save(cfg, doc)
        self.replies[:] = [answered('return')]
        code, response = self.cli('evidence', '--check-id', 'unit', '--evidence-id', receipt, '--use', 'executed')
        self.assertEqual(code, 1)
        self.assertEqual(response['classifications'][0]['route'], 'return')
        self.assertEqual(response['revision'], load(self.repo, self.cid)['revision'])
        entry = self.entries('failure-routing')[0]
        self.assertEqual((entry['subject'], entry['trigger']), ('unit', f'check:{receipt}'))
        self.assertEqual(list(self.asked[0]['question'].options), ['return', 'agent-assessment', 'insufficient-information'])
        first = self.inspect()['actions'][0]
        self.assertEqual(first['classification']['route'], 'return')
        self.assertIn('--progress', first['caller_fills'])

    def test_agent_route_for_the_attempt_limit_and_re_dispatch_never_raises_it(self):
        for n in range(3):
            self.prepare(f'prep-lim{n}', assignment='build-it')
            self.lose(f'lost-lim{n}', attempt=n + 1)
        response = self.refused_with_entry({**self.second_reservation('prep-lim9')}, 'attempt-limit')
        self.assertEqual(response['recovery_handlers'][0]['code'], 'attempt-limit')
        self.assertEqual((self.asked, self.entries('failure-routing')), ([], []))

    def test_a_distinct_refusal_per_code_triggers_and_the_code_facts_trigger_nothing(self):
        self.prepare()
        self.default = answered('agent-assessment')
        stale = self.op({'op': 'advance', 'op_id': 'adv-stale1', 'expect_revision': 1})[1]
        self.assertEqual(stale['errors'][0]['code'], 'stale-revision')
        self.op({'op': 'prepare-dispatch', 'op_id': 'prep-0001', 'task_id': 'build-it', 'role': 'developer', 'host': 'claude-code', 'assignment_text': 'DIFFERENT'})
        self.op({'op': 'prepare-dispatch', 'op_id': 'bad', 'task_id': 'build-it'})
        self.assertEqual((self.asked, self.legacy_entries()), ([], []), 'stale-revision, op-id-reused and argument-validation refusals trigger nothing')
        cid2 = self.fixture(version=2)
        code, response = self.op(self.second_reservation(), cid=cid2)
        self.assertEqual(response['errors'][0]['code'], 'needs-upgrade')
        self.assertEqual(self.asked, [])

    def test_superseded_attempt_and_delivery_conflict_refusals_trigger(self):
        self.prepare()
        self.lose('lost-0001')
        self.prepare('prep-0002', assignment='build-it')
        self.default = answered('agent-assessment')
        response = self.refused_with_entry({'op': 'deliver', 'op_id': 'deliver-old', 'assignment': 'build-it', 'attempt': 1, 'outcome': 'done'}, 'superseded-attempt')
        self.assertEqual(response['recovery_handlers'][0]['code'], 'superseded-attempt')
        self.assertEqual((self.asked, self.entries('failure-routing')), ([], []))

    def test_delivery_conflict_triggers_failure_routing(self):
        prepared = self.prepare()
        sha = self.work(prepared)
        request = {'op': 'deliver', 'op_id': 'deliver-01', 'assignment': 'build-it', 'attempt': 1, 'outcome': 'done', 'commits': [sha]}
        self.ok(request)
        self.default = answered('agent-assessment')
        response = self.refused_with_entry({**request, 'op_id': 'deliver-03', 'outcome': 'blocked'}, 'delivery-conflict')
        self.assertEqual(response['recovery_handlers'][0]['code'], 'delivery-conflict')
        self.assertEqual((self.asked, self.entries('failure-routing')), ([], []))

    def test_result_path_missing_is_an_inspect_problem_that_writes_nothing(self):
        prepared = self.prepare()
        import shutil
        shutil.rmtree(Path(prepared['result_path']).parent)
        before = self.record_path().read_bytes()
        seen = self.inspect()
        self.assertEqual([a['problem'] for a in seen['assignments']], ['result-path-missing'])
        self.assertEqual(self.record_path().read_bytes(), before)
        self.assertEqual(self.asked, [])
        self.assertIn('result-path-missing', cycle_classify.REFUSAL_TRIGGERS)
        Path(prepared['result_path']).parent.mkdir(mode=0o700)


class BlockedDeliveryTests(ClassifyBase):
    """IDR lean-workflow-traps-and-recovery approach 3: a blocked delivery routes like a failed one unless it names a stop."""

    def blocked_delivery(self, *replies, stop=None):
        prepared = self.prepare()
        self.write_result(prepared)
        self.replies[:] = list(replies)
        request = {'op': 'deliver', 'op_id': 'deliver-01', 'assignment': prepared['assignment'], 'attempt': 1, 'outcome': 'blocked'}
        if stop:
            request['stop'] = stop
        return self.ok(request)

    def test_a_blocked_delivery_records_failure_routing_through_ask_many_and_inspect_offers_the_route_first(self):
        many = []
        real = decisions.ask_many

        def counting(state, questions, *, deadline, client=None, kinds=()):
            many.append((kinds, sorted(questions)))
            return real(state, questions, deadline=deadline, client=client, kinds=kinds)
        with mock.patch.object(decisions, 'ask_many', counting):
            response = self.blocked_delivery(answered('re-dispatch'))
        self.assertEqual([ids for kinds, ids in many if kinds == ('failure-routing',)], [['failure-routing']], 'one failure-routing request carries its one question')
        (entry,) = self.entries('failure-routing')
        self.assertEqual((entry['route'], entry['subject'], entry['trigger']), ('re-dispatch', 'build-it', 'delivery:build-it/1'))
        self.assertEqual(self.asked[0]['state']['attempt']['outcome'], 'blocked')
        self.assertEqual(response['revision'], load(self.repo, self.cid)['revision'])
        first = self.inspect()['actions'][0]
        self.assertEqual(first['classification']['route'], 're-dispatch')
        self.assertEqual(first['request'], {'op': 'prepare-dispatch', 'task_id': 'build-it', 'role': 'developer', 'host': 'claude-code'})

    def assert_stop_records_nothing(self, stop):
        response = self.blocked_delivery(stop=stop)
        self.assertEqual(response['outcome'], 'blocked')
        self.assertNotIn('classifications', response)
        self.assertEqual(self.asked, [], 'a stop sends no question')
        self.assertEqual(self.entries('failure-routing'), [])
        self.assertFalse([a for a in self.inspect()['actions'] if a.get('classification')])

    def test_a_blocked_delivery_naming_owner_decision_records_no_classification(self):
        self.assert_stop_records_nothing('owner-decision')

    def test_a_blocked_delivery_naming_approval_wait_records_no_classification(self):
        self.assert_stop_records_nothing('approval-wait')

    def test_a_stop_is_refused_on_a_delivery_that_is_not_blocked(self):
        prepared = self.prepare()
        self.write_result(prepared)
        code, response = self.op({'op': 'deliver', 'op_id': 'deliver-01', 'assignment': prepared['assignment'], 'attempt': 1,
                                  'outcome': 'failed', 'stop': 'owner-decision'})
        self.assertEqual(code, 1, response)
        self.assertEqual(self.asked, [])


class WorkSizingRouteTests(ClassifyBase):
    def create(self, *extra, answer=None, title='Sized'):
        self.replies[:] = [answer] if answer is not None else []
        out = __import__('io').StringIO()
        with __import__('contextlib').redirect_stdout(out):
            code = __import__('cycle').main(['--repo-root', str(self.repo), 'create', '--title', title, '--goal', 'g', '--implementer', 'a',
                                             '--coordinator', 'b', '--scope', 'src', '--acceptance', 'ok', *extra])
        return code, json.loads(out.getvalue())

    def test_each_permitted_type_is_set_and_its_entry_is_written_in_the_creating_save(self):
        for kind in ('quick-fix', 'iterate', 'refactor', 'simplify', 'dev'):
            with self.subTest(kind=kind):
                code, response = self.create('--type', 'auto', answer=answered(kind))
                self.assertEqual(code, 0, response)
                doc = response['cycle']
                self.assertEqual(doc['type'], kind)
                (entry,) = doc['classifications']
                self.assertEqual((entry['kind'], entry['route'], entry['fallback'], entry['subject'], entry['revision']),
                                 ('work-sizing', kind, None, doc['id'], 1))
                self.assertRegex(entry['fingerprint'], HEX64)
                self.assertEqual(entry['question_ids'], ['work-sizing'])
                self.assertEqual(doc['revision'], 1)
                self.assertEqual(list(self.asked[-1]['question'].options), ['dev', 'iterate', 'refactor', 'simplify', 'quick-fix', 'insufficient-information'])
                self.assertNotIn('release', self.asked[-1]['question'].options)

    def test_a_fallback_refuses_creation_and_prints_a_receipt_with_no_state_text(self):
        existing = sorted(p.name for p in (self.repo / 'bionic/cycles').iterdir())
        code, response = self.create('--type', 'auto', answer=answered('insufficient-information', request_id='gen-req-0007'))
        self.assertEqual(code, 1)
        self.assertEqual(sorted(p.name for p in (self.repo / 'bionic/cycles').iterdir()), existing)
        receipt = dict(response['sizing_receipt'])
        self.assertRegex(receipt.pop('fingerprint'), HEX64)
        self.assertEqual(receipt.pop('question_ids'), ['work-sizing'])
        self.assertEqual(receipt, {'request_id': 'gen-req-0007', 'question_set': 'work-sizing', 'question_version': '1', 'model': MODEL,
                                                    'served_model': MODEL, 'served_provider': None, 'cost': None,
                                                    'answer': {'choice': 'insufficient-information', 'probabilities': None},
                                                    'fallback': 'insufficient-information'})
        self.assertIn('options', response['question']); self.assertIn('title', response['evidence'])
        self.assertNotIn('Sized', json.dumps(response['sizing_receipt']))

    def test_sizing_fingerprint_covers_text_after_the_clipping_boundary(self):
        fingerprints = []
        for suffix in ('x', 'y'):
            code, response = self.create('--type', 'auto', answer=answered('iterate'), title='a' * 200 + suffix)
            self.assertEqual(code, 0, response)
            fingerprints.append(response['cycle']['classifications'][0]['fingerprint'])
        self.assertNotEqual(*fingerprints)

    def test_a_route_outside_the_permitted_set_falls_back(self):
        for choice in ('release', 'change-type', 'dev '):
            with self.subTest(choice=choice):
                code, response = self.create('--type', 'auto', answer=answered(choice))
                self.assertEqual((code, response['sizing_receipt']['fallback']), (1, 'route-not-permitted'))

    def test_the_explicit_create_records_the_receipt_even_when_the_classifier_changed_meanwhile(self):
        code, response = self.create('--type', 'auto', answer=answered('insufficient-information', request_id='gen-req-0007'))
        receipt = response['sizing_receipt']
        self.status = decisions.Status(False, 'credential-missing')
        self.replies.clear(); self.asked.clear()
        code, created = self.create('--type', 'dev', '--sizing-receipt', json.dumps(receipt))
        self.assertEqual(code, 0, created)
        (entry,) = created['cycle']['classifications']
        self.assertEqual((entry['route'], entry['fallback'], entry['request_id'], entry['subject']), (None, 'insufficient-information', 'gen-req-0007', created['cycle']['id']))
        self.assertEqual({k: entry[k] for k in cycle_classify.SIZING_RECEIPT_FIELDS + cycle_classify.SIZING_RECEIPT_OPTIONAL}, receipt)
        self.assertEqual(self.asked, [])

    def test_a_receipt_may_carry_null_request_id_and_served_model(self):
        receipt = {'request_id': None, 'question_set': 'work-sizing', 'question_version': '1', 'model': MODEL, 'served_model': None, 'answer': None,
                   'fallback': 'over-input-bound'}
        code, created = self.create('--type', 'iterate', '--sizing-receipt', json.dumps(receipt))
        self.assertEqual(code, 0, created)
        self.assertEqual(created['cycle']['classifications'][0]['fallback'], 'over-input-bound')

    def test_a_malformed_receipt_is_refused_and_creates_nothing(self):
        good = {'request_id': None, 'question_set': 'work-sizing', 'question_version': '1', 'model': MODEL, 'served_model': None, 'answer': None,
                'fallback': 'timeout'}
        existing = sorted(p.name for p in (self.repo / 'bionic/cycles').iterdir())
        bad = [{k: v for k, v in good.items() if k != 'fallback'}, {**good, 'extra': 1}, {**good, 'fallback': None}, {**good, 'question_set': 'review-routing'},
               {**good, 'request_id': 5}, {**good, 'answer': 'x'}, []]
        for receipt in bad:
            with self.subTest(receipt=receipt):
                code, response = self.create('--type', 'iterate', '--sizing-receipt', json.dumps(receipt))
                self.assertEqual(code, 1); self.assertIn('invalid sizing receipt', response['error'])
        self.assertEqual(sorted(p.name for p in (self.repo / 'bionic/cycles').iterdir()), existing)

    def test_an_omitted_receipt_records_no_entry(self):
        code, created = self.create('--type', 'iterate')
        self.assertEqual(code, 0)
        self.assertNotIn('classifications', created['cycle'])

    def test_auto_with_a_receipt_or_a_release_list_is_refused(self):
        receipt = json.dumps({'request_id': None, 'question_set': 'work-sizing', 'question_version': '1', 'model': MODEL, 'served_model': None,
                              'answer': None, 'fallback': 'timeout'})
        self.assertEqual(self.create('--type', 'auto', '--sizing-receipt', receipt)[0], 1)
        self.assertEqual(self.create('--type', 'auto', '--list', 'beta')[0], 1)

    def test_a_sized_quick_fix_still_refuses_a_material_decision(self):
        code, response = self.create('--type', 'auto', answer=answered('quick-fix'))
        with self.assertRaisesRegex(Exception, 'material decisions require changing quick-fix'):
            mutate(self.repo, response['cycle']['id'], 'decision', kind='idr', name='x', contents={'alternatives': ['a'], 'approach': ['b'],
                                                                                                   'assumptions': ['c'], 'constraints': ['d'], 'intended_evidence': ['e']})

    def test_a_running_cycle_type_never_changes_on_an_answer(self):
        self.enter_review(answered('change-type:dev'))
        self.assertEqual({e['fallback'] for e in self.entries('review-routing')}, {'route-not-permitted'})
        self.assertEqual(load(self.repo, self.cid)['type'], 'quick-fix')


class FallbackTests(ClassifyBase):
    NO_REQUEST = ('unconfigured', 'over-input-bound', 'over-token-ceiling', 'scan-match', 'scan-failure')

    def assert_fallback(self, outcome, expected, *, only=None):
        """Enter Review answering every review predicate with `outcome` and check the fallback entries.

        `only` names the one specialist whose predicate must fall back; every other predicate must have kept the
        floor. Without it each of the review's predicates falls back alike."""
        response = self.enter_review(outcome)
        entries = self.entries('review-routing')
        self.assertEqual(len(entries), len(cycle_classify.SPECIALISTS))
        chosen = entries if only is None else [self.review_entry(only)]
        for entry in entries:
            if entry not in chosen:
                self.assertEqual((entry['route'], entry['fallback']), ('floor-only', None))
        for entry in chosen:
            self.assertEqual((entry['route'], entry['fallback']), (None, expected))
            reported = next(r for r in response['classifications'] if r['subject'] == entry['subject'])
            self.assertEqual((reported['fallback'], reported['recorded']), (expected, True))
            self.assertIn('question', reported); self.assertIn('evidence', reported); self.assertEqual(reported['outcome']['status'], outcome.status)
            self.assertEqual(entry['revision'], response['revision'])
        return chosen[0]

    def test_insufficient_information_is_an_answer_recorded_as_that_fallback(self):
        entry = self.assert_fallback(answered('insufficient-information'), 'insufficient-information')
        self.assertEqual(entry['answer']['choice'], 'insufficient-information')

    def test_a_route_that_was_not_offered_falls_back_as_not_permitted(self):
        entry = self.assert_fallback(answered('add:something-else'), 'route-not-permitted')
        self.assertEqual(entry['answer']['choice'], 'add:something-else')

    def test_a_route_that_fails_policy_at_write_time_falls_back_as_policy_refused(self):
        real = cycle_classify.plan_of
        calls = []

        def drifting(cfg, doc, job, repo_root=None):
            plan = real(cfg, doc, job, repo_root)
            calls.append(job.kind)
            if plan is not None and self.asked and job.subject == 'review:untrusted-input-execution':
                return None  # this subject ceases to be eligible while its question is out
            return plan
        with mock.patch.object(cycle_classify, 'plan_of', drifting):
            self.assert_fallback(answered('add:untrusted-input-execution'), 'policy-refused', only='untrusted-input-execution')

    def test_the_stale_answer_is_discarded_asked_once_more_and_written_when_it_passes_policy(self):
        self.add_review_task()
        each = len(cycle_classify.SPECIALISTS)
        first, second = review_reply(answered('add:release-distribution')), review_reply(answered('floor-only', request_id='gen-req-0002'))

        def move(n):
            if n == 1:
                with locked(self.repo) as (cfg, _):
                    doc = load(self.repo, self.cid)
                    next(t for t in doc['plan']['tasks'] if t['phase'] == 'review')['description'] += ' changed'
                    save(cfg, doc)
        self.hook = move
        self.ready_for_review()
        self.review = lambda state, question: (first if len(self.asked) <= each else second)(state, question)
        self.ok(self.advance('advance-t1'))
        entries = self.entries('review-routing')
        self.assertEqual([(e['route'], e['request_id']) for e in entries], [('floor-only', 'gen-req-0002')] * each)
        self.assertEqual(len(self.asked), 2 * each, 'every question was asked again once')
        self.assertIs(self.asked[0]['deadline'], self.asked[-1]['deadline'], 're-asks count against the same deadline')

    def test_a_second_concurrent_change_falls_back_as_stale(self):
        self.add_review_task()
        each = len(cycle_classify.SPECIALISTS)
        def changing(n):
            with locked(self.repo) as (cfg, _):
                doc = load(self.repo, self.cid)
                next(t for t in doc['plan']['tasks'] if t['phase'] == 'review')['description'] += f' change{n}'
                save(cfg, doc)
        self.hook = changing
        self.enter_review(answered('add:release-distribution'))
        entries = self.entries('review-routing')
        self.assertEqual([(e['route'], e['fallback']) for e in entries], [(None, 'stale')] * each)
        self.assertEqual(len(self.asked), 2 * each, 'one re-ask of every question, then fallback')

    def test_the_request_is_sent_with_the_lock_released(self):
        self.enter_review(answered('floor-only'))
        self.assertEqual([a['lock_free'] for a in self.asked], [True] * len(cycle_classify.SPECIALISTS))

    def test_a_crash_before_the_write_leaves_the_subject_unclassified_and_replay_asks_nothing(self):
        self.add_review_task()
        self.ready_for_review()
        request = self.advance('advance-t1')
        self.hook = lambda n: (_ for _ in ()).throw(SimulatedCrash())
        with self.assertRaises(SimulatedCrash):
            self.op(request)
        doc = load(self.repo, self.cid)
        self.assertEqual((doc['phase'], self.entries('review-routing')), ('review', []))
        self.assertTrue(all(entry['kind'] not in cycle_classify.KINDS[:4] for entry in doc.get('classifications', [])))
        self.assertTrue(self.inspect()['actions'])
        self.asked.clear(); self.hook = None
        again = self.ok(request)
        self.assertTrue(again['replayed']); self.assertEqual(self.asked, [])
        self.assertNotIn('classifications', again)

    def test_two_concurrent_identical_triggers_keep_one_entry(self):
        job = cycle_classify.Job('review-routing', 'review:release-distribution')

        def nested(n):
            if n == 1:
                self.hook = None
                outer, self.review = self.review, None
                self.default = answered('floor-only', request_id='gen-inner')
                cycle_classify.classify(self.repo, self.cid, [job])
                self.review = outer
        self.hook = nested
        self.enter_review(answered('floor-only', request_id='gen-first'))
        entries = self.entries('review-routing')
        subjects = [e['subject'] for e in entries]
        self.assertEqual(sorted(subjects), sorted(f'review:{i}' for i in cycle_classify.SPECIALISTS), 'one entry per dedup key')
        self.assertEqual(len(set(subjects)), len(subjects))
        self.assertEqual(next(e for e in entries if e['subject'] == job.subject)['request_id'], 'gen-inner', 'the first writer keeps the key')
        # The nested write changed bookkeeping only: keep the other answers without re-asking them.
        self.assertEqual(len(self.asked), 1 + len(cycle_classify.SPECIALISTS))


def _fallback_method(status):
    def method(self):
        sent = status not in self.NO_REQUEST
        http = int(status[-3:]) if status.startswith('malformed:http-') else None
        entry = self.assert_fallback(failed(status, request_id='gen-r' if sent else None, attempts=2 if status in ('timeout', 'unavailable') else 1,
                                            http_status=http), status)
        self.assertEqual(entry['request_id'], 'gen-r' if sent else None)
        self.assertEqual(len(self.asked), len(cycle_classify.SPECIALISTS), 'the engine added a retry of its own')
        self.assertIn('floor', self.inspect()['review'], 'the floor is listed when routing fell back')
    method.__name__ = 'test_transport_fallback_' + re.sub(r'\W', '_', status)
    return method


for _status in decisions.FALLBACKS:
    _method = _fallback_method(_status)
    setattr(FallbackTests, _method.__name__, _method)


class DedupAndDeadlineTests(ClassifyBase):
    def test_a_repeated_identical_refusal_makes_no_call_and_adds_no_entry(self):
        self.prepare()
        self.default = answered('mark-lost')
        self.refused_with_entry(self.second_reservation('prep-0002'), 'unresolved-dispatch', 'task-not-eligible')
        self.assertEqual((len(self.asked), len(self.legacy_entries())), (0, 0))
        response = self.refused_with_entry(self.second_reservation('prep-0003'), 'unresolved-dispatch', 'task-not-eligible')
        self.assertEqual((len(self.asked), len(self.legacy_entries())), (0, 0))
        self.assertNotIn('revision', response)

    def test_each_failed_attempt_and_each_failing_receipt_triggers_once(self):
        self.failed_delivery(answered('re-dispatch'))
        prepared = self.prepare('prep-0002', assignment='build-it')
        self.write_result(prepared)
        self.replies[:] = [answered('re-dispatch')]
        self.ok({'op': 'deliver', 'op_id': 'deliver-02', 'assignment': 'build-it', 'attempt': 2, 'outcome': 'failed'})
        self.assertEqual([e['trigger'] for e in self.entries('failure-routing')], ['delivery:build-it/1', 'delivery:build-it/2'])
        self.assertEqual(len(self.asked), 2)
        self.cli('evidence', '--check-id', 'unit', '--evidence-id', 'TE-' + '0' * 32, '--use', 'executed')
        self.assertEqual(len(self.asked), 2, 'an unreadable receipt triggers nothing')

    def test_several_findings_with_a_stalled_gateway_end_by_the_deadline_and_the_rest_fall_back_without_a_call(self):
        now = [0.0]
        real = decisions.Deadline
        seen = []

        def stalled(state, question, *, deadline=None):
            return None
        self.enter_review(answered('floor-only'))
        self.asked.clear()
        sent = []

        def gateway(state, question):
            deadline = self.asked[-1]['deadline']
            self.assertLessEqual(deadline.call_timeout(), deadline.remaining())
            if deadline.call_timeout() <= 0:
                return failed('unavailable', attempts=0)
            sent.append(self.asked[-1]['id'])
            now[0] += min(2 * decisions.CALL_TIMEOUT_SECONDS, deadline.remaining())
            return failed('unavailable', request_id=None, attempts=2)
        self.default = gateway
        report = {'verdict': 'approve', 'blocking': [], 'advisory': [f'finding number {i}' for i in range(5)], 'cosmetic': []}
        with mock.patch.object(decisions, 'Deadline', lambda: real(clock=lambda: now[0])):
            code, response = self.record_review(self.receipt_id, report)
        self.assertEqual(code, 0, response)
        entries = self.entries('finding-disposition')
        self.assertEqual([e['fallback'] for e in entries], ['unavailable'] * 5)
        self.assertEqual(len(sent), 2, 'the calls the deadline reached')
        self.assertLessEqual(now[0], decisions.OPERATION_DEADLINE_SECONDS)
        self.assertEqual(len({id(a['deadline']) for a in self.asked}), 1, 'one Deadline for the whole operation')


class BoundaryTests(ClassifyBase):
    """An answer that would cross a deterministic boundary is not an offered route: it falls back to the agent."""

    def assert_refused_to_agent(self, answer, kind, *, setup):
        setup(answer)
        entry = [e for e in self.entries(kind)][-1]
        self.assertEqual((entry['route'], entry['fallback']), (None, 'route-not-permitted'), answer)
        self.assertEqual(entry['answer']['choice'], answer)

    def test_a_blocking_finding_cannot_be_declined_or_deferred(self):
        self.review_with_findings(answered('follow-up'), answered('decline'), answered('agent-assessment'))
        by_id = {e['subject']: e for e in self.entries('finding-disposition')}
        self.assertEqual(by_id['r1:blocking:0']['fallback'], 'route-not-permitted')
        self.assertEqual(by_id['r1:blocking:0']['answer']['choice'], 'follow-up')
        self.assertEqual(load(self.repo, self.cid).get('deferrals', []), [])

    def test_a_failed_delivery_answer_cannot_raise_the_attempt_limit_or_re_dispatch_a_held_task(self):
        self.prepare()
        self.replies[:] = [answered('re-dispatch')]
        cycle_classify.refused_operation(self.repo, self.cid, self.second_reservation(), [{'code': 'unresolved-dispatch'}])
        self.assertEqual(self.entries('failure-routing')[0]['fallback'], 'route-not-permitted')

    def test_no_answer_makes_the_engine_dispatch_mark_lost_return_or_add_a_task(self):
        self.prepare()
        self.replies[:] = [answered('mark-lost')]
        self.refused_with_entry(self.second_reservation(), 'unresolved-dispatch', 'task-not-eligible')
        doc = load(self.repo, self.cid)
        self.assertEqual([(a['id'], a['state']) for a in doc['assignments']], [('build-it', 'reserved')])
        self.assertEqual((doc['pass'], doc['phase'], [t['id'] for t in doc['plan']['tasks']]), (1, 'build', ['build-it']))


def _review_boundary(answer):
    def method(self):
        mutate(self.repo, self.cid, 'scrutiny', scrutiny='intensive', rationale='r', risks=['release'])
        self.enter_review(answered(answer))
        entries = self.entries('review-routing')
        self.assertEqual(len(entries), len(cycle_classify.SPECIALISTS) - 1, 'one predicate per specialist off the floor')
        for entry in entries:
            self.assertEqual((entry['route'], entry['fallback'], entry['answer']['choice']), (None, 'route-not-permitted', answer))
        review = self.inspect()['review']
        self.assertEqual((review['floor'], review['scrutiny']), (['release-distribution'], 'intensive'))
        self.assertEqual(load(self.repo, self.cid)['review_policy']['scrutiny'], 'intensive')
    return method


def _failure_boundary(answer):
    def method(self):
        self.to_test()
        receipt = self.failing_receipt()
        self.replies[:] = [answered(answer)]
        self.cli('evidence', '--check-id', 'unit', '--evidence-id', receipt, '--use', 'executed')
        (entry,) = self.entries('failure-routing')
        self.assertEqual((entry['route'], entry['fallback']), (None, 'route-not-permitted'))
        doc = load(self.repo, self.cid)
        self.assertEqual((doc['phase'], doc['status'], doc['evidence'], doc['completion']), ('verify', 'active', [], None))
    return method


for _answer in ('approve', 'grant-pass', 'waive-decision', 'remove:release-distribution', 'lower-scrutiny', 'scrutiny:focused'):
    _m = _review_boundary(_answer)
    _m.__name__ = 'test_review_answer_cannot_cross_the_boundary_' + re.sub(r'\W', '_', _answer)
    setattr(BoundaryTests, _m.__name__, _m)
for _answer in ('mark-passed', 'proceed', 'advance', 'waive-check', 'owner-exception', 'complete'):
    _m = _failure_boundary(_answer)
    _m.__name__ = 'test_failure_answer_cannot_cross_the_boundary_' + re.sub(r'\W', '_', _answer)
    setattr(BoundaryTests, _m.__name__, _m)


class UnconfiguredAndVersionTests(ClassifyBase):
    def test_the_repository_opt_out_stops_every_request(self):
        (self.repo / '.bionic.yml').write_text('config_version: "1"\ndocs_dir: bionic\ndecisions:\n  classifier: off\n')
        response = self.enter_review()
        self.assertEqual((self.asked, self.legacy_entries()), ([], []))
        self.assertEqual(response['classifier'], {'configured': False, 'reason': 'opted-out'})
        self.assertEqual(self.inspect()['classifier'], {'configured': False, 'reason': 'opted-out'})
        code, sized = WorkSizingRouteTests.create(self, '--type', 'auto')
        self.assertEqual(code, 1); self.assertNotIn('sizing_receipt', sized); self.assertIn('unconfigured', sized['error'])

    def test_the_opt_out_is_the_classification_fallback_and_records_nothing(self):
        (self.repo / '.bionic.yml').write_text('config_version: "1"\ndocs_dir: bionic\ndecisions:\n  classifier: off\n')
        response = self.enter_review()
        self.assertEqual(self.asked, [])
        self.assertEqual(self.legacy_entries(), [])
        self.assertEqual(response['classifications'], [{'kind': 'review-routing', 'subject': f'review:{i}', 'trigger': None, 'route': None,
                                                         'fallback': 'opted-out', 'recorded': False} for i in cycle_classify.SPECIALISTS])

    def test_unconfigured_sizing_is_refused_with_no_receipt_and_no_cycle(self):
        self.status = decisions.Status(False, 'credential-missing')
        existing = sorted(p.name for p in (self.repo / 'bionic/cycles').iterdir())
        code, response = WorkSizingRouteTests.create(self, '--type', 'auto')
        self.assertEqual(code, 1)
        self.assertNotIn('sizing_receipt', response)
        self.assertEqual(sorted(p.name for p in (self.repo / 'bionic/cycles').iterdir()), existing)
        self.assertEqual(self.asked, [])

    def test_inspect_reports_a_configured_classifier(self):
        self.assertEqual(self.inspect()['classifier'], {'configured': True, 'reason': None})

    def test_a_version_two_record_builds_no_request_writes_nothing_and_returns_the_upgrade_request(self):
        cid = self.fixture(version=2)
        before = self.record_path(cid).read_bytes()
        code, response = self.op(self.second_reservation(), cid=cid)
        self.assertEqual((code, response['errors'][0]['code']), (1, 'needs-upgrade'))
        self.assertEqual([r['request'] for r in response['errors'][0]['recovery']], [{'op': 'upgrade'}])
        self.assertEqual(cycle_classify.classify(self.repo, cid, [cycle_classify.Job('review-routing', 'review:release-distribution')]),
                         {'classifications': []})
        self.assertEqual((self.asked, self.record_path(cid).read_bytes()), ([], before))


def _unconfigured(reason):
    def method(self):
        self.status = decisions.Status(False, reason)
        response = self.enter_review()
        self.assertEqual(self.asked, [])
        self.assertEqual(self.legacy_entries(), [])
        self.assertEqual(response['classifications'], [{'kind': 'review-routing', 'subject': f'review:{i}', 'trigger': None, 'route': None,
                                                         'fallback': 'unconfigured', 'recorded': False} for i in cycle_classify.SPECIALISTS])
        self.assertNotIn('revision', response.get('classifications', [{}])[0])
        self.assertEqual(self.inspect()['classifier'], {'configured': False, 'reason': reason})
        self.assertIn('floor', self.inspect()['review'])
    return method


for _reason in ('credential-missing', 'role-missing', 'registry-entry-invalid'):
    _m = _unconfigured(_reason)
    _m.__name__ = 'test_unconfigured_classifier_builds_no_request_and_records_nothing_' + _reason.replace('-', '_')
    setattr(UnconfiguredAndVersionTests, _m.__name__, _m)


class OfferedRouteTests(ClassifyBase):
    def one_route(self):
        self.failed_delivery(answered('re-dispatch'))
        return self.entries('failure-routing')[0]

    def offered(self):
        return [a for a in self.inspect()['actions'] if a.get('classification')]

    def rewrite(self, edit):
        path = self.record_path()
        raw = json.loads(path.read_text()); edit(raw)
        path.write_text(json.dumps(raw, indent=2, sort_keys=True) + '\n')

    def test_the_stored_route_is_the_first_action_for_its_subject(self):
        self.one_route()
        seen = self.inspect()
        self.assertEqual(seen['actions'][0]['classification']['route'], 're-dispatch')
        self.assertEqual(len(self.offered()), 1)

    def test_the_stored_route_is_history_after_the_fingerprint_changes(self):
        self.one_route()
        mutate(self.repo, self.cid, 'task', task_id='build-it', state='blocked')
        self.assertEqual(self.offered(), [])

    def test_the_fingerprint_survives_serialization_and_reload(self):
        entry = self.one_route()
        again = json.loads(json.dumps(load(self.repo, self.cid)))
        plan = cycle_classify.valid_plan(cycle_ops.tree(self.repo), again, entry, self.repo)
        self.assertEqual(plan.fingerprint, entry['fingerprint'])

    def test_a_set_version_or_route_id_that_left_current_code_never_raises_and_is_not_offered(self):
        self.one_route()
        self.rewrite(lambda raw: next(entry for entry in raw['classifications'] if entry['kind'] == 'failure-routing').update(question_version='0'))
        self.assertEqual(self.offered(), [])
        self.rewrite(lambda raw: next(entry for entry in raw['classifications'] if entry['kind'] == 'failure-routing').update(question_version='2', route='teleport'))
        self.assertEqual(self.offered(), [])
        self.rewrite(lambda raw: next(entry for entry in raw['classifications'] if entry['kind'] == 'failure-routing').update(question_set='retired'))
        self.assertEqual(self.offered(), [])

    def test_a_route_that_current_policy_rejects_is_not_offered(self):
        self.one_route()
        self.assertEqual(len(self.offered()), 1)
        with mock.patch.object(cycle_classify, 'plan_failure', lambda cfg, doc, job, repo_root=None: cycle_classify.Plan({}, ['agent'], self.legacy_entries()[0]['fingerprint'])):
            self.assertEqual(self.offered(), [])

    def test_a_stored_review_set_is_the_recomputed_floor_plus_its_addition(self):
        mutate(self.repo, self.cid, 'scrutiny', scrutiny='standard', rationale='r', risks=[])
        self.enter_review(answered('add:untrusted-input-execution'))
        self.assertEqual(self.inspect()['review']['specialists'], ['untrusted-input-execution'])
        mutate(self.repo, self.cid, 'scrutiny', scrutiny='standard', rationale='r', risks=['release'])
        review = self.inspect()['review']
        self.assertEqual(review['floor'], ['release-distribution'])
        # Risk text is part of the decision input: keep the new floor and discard the previous optional answer.
        self.assertEqual(review['specialists'], ['release-distribution'])

    def test_return_applied_ends_the_offer_and_a_new_pass_makes_the_entry_history(self):
        self.review_with_findings(answered('return'), answered('insufficient-information'), answered('insufficient-information'))
        self.assertEqual(self.inspect()['actions'][0]['classification']['route'], 'return')
        self.cli('return', '--improved', 'x', '--unresolved', 'y', '--next-change', 'z', '--justification', 'j', '--progress', 'yes')
        self.assertFalse([a for a in self.inspect()['actions'] if a.get('classification')])


class EngineGuardTests(ClassifyBase):
    def test_a_bug_in_classification_never_turns_a_committed_operation_into_a_crash(self):
        with mock.patch.object(cycle_classify, 'plan_review', side_effect=RuntimeError('boom')):
            self.ready_for_review()
            response = self.ok(self.advance('advance-t1'))
        self.assertEqual(response['classification_error'], 'RuntimeError')
        self.assertEqual(load(self.repo, self.cid)['phase'], 'review')

    def test_a_listed_or_closed_cycle_triggers_nothing(self):
        self.assertEqual(cycle_classify.classify(self.repo, self.cid, []), {'classifications': []})


if __name__ == '__main__':
    unittest.main()
