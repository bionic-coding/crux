"""Batched classification: bounded requests, fix-only routes for blocking findings, several specialists, bounded concurrency
and per-answer fallbacks inside one request.

Every provider answer is scripted or served by an httpx MockTransport; no test sends a live request.
Replies that must hold under concurrent requests are keyed on the question id, never on call order."""
import json
from pathlib import Path
import sys
import threading
import time
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import httpx
import crux_env
import cycle_classify
from crux import decisions
from crux.decisions import transport
from cycle_workflow import load, mutate
from _classify_support import BLOCKING, ClassifyBase, MODEL, answered, failed

FAKE_KEY = 'fake-credential-NOT-A-REAL-KEY-0123456789abcdef'
MAX_QUESTIONS = decisions.MAX_QUESTIONS_PER_REQUEST


def advisory_report(findings):
    return {'verdict': 'approve', 'blocking': [], 'advisory': list(findings), 'cosmetic': []}


class BatchBase(ClassifyBase):
    def record_requests(self):
        """Wrap the scripted `ask_many`: every request's (state, question ids) is kept, safely across threads."""
        requests, lock, real = [], threading.Lock(), decisions.ask_many

        def recording(state, questions, *, deadline, client=None, kinds=()):
            with lock:
                requests.append((state, list(questions)))
            return real(state, questions, deadline=deadline, client=client, kinds=kinds)
        patcher = mock.patch.object(decisions, 'ask_many', recording)
        patcher.start()
        self.addCleanup(patcher.stop)
        return requests

    def review_findings(self, report, replies):
        """Enter Review answering floor-only, then record `report`; `replies` maps finding id to an Outcome."""
        self.enter_review(answered('floor-only'))
        self.asked.clear()
        self.requests = self.record_requests()
        self.default = replies
        return self.record_review(self.receipt_id, report)

    def findings(self):
        return {e['subject']: e for e in self.entries('finding-disposition')}


class BoundedBatchTests(BatchBase):
    def assert_bounded(self, requests, ids):
        for state, question_ids in requests:
            self.assertLessEqual(len(question_ids), MAX_QUESTIONS, 'a request holds more questions than the bound')
            self.assertLessEqual(cycle_classify.state_size(state), decisions.MAX_STATE_CHARS, 'a request state is over the input bound')
            self.assertEqual([f['id'] for f in state['findings']], question_ids, 'the state lists exactly the findings the request asks')
        asked = [i for _, question_ids in requests for i in question_ids]
        self.assertEqual(sorted(asked), sorted(ids), 'every finding is asked exactly once')

    def test_more_findings_than_the_question_bound_are_split_by_count(self):
        ids = [f'r1:advisory:{i}' for i in range(2 * MAX_QUESTIONS + 3)]
        code, response = self.review_findings(advisory_report(f'finding number {i}' for i in range(len(ids))),
                                              {i: answered('agent-assessment') for i in ids})
        self.assertEqual(code, 0, response)
        requests = self.requests
        self.assertEqual(sorted(len(q) for _, q in requests), [3, MAX_QUESTIONS, MAX_QUESTIONS])
        self.assert_bounded(requests, ids)
        entries = self.findings()
        self.assertEqual(sorted(entries), sorted(ids), 'every finding has its own entry')
        self.assertEqual({e['route'] for e in entries.values()}, {'agent-assessment'})
        self.assertEqual({e['fallback'] for e in entries.values()}, {None})
        self.assertEqual(len({e['revision'] for e in entries.values()}), 1, 'the batches are written in one transaction')
        self.assertTrue(all(call['lock_free'] for call in self.asked), 'a request was sent with the cycle lock held')

    def test_findings_whose_state_exceeds_the_input_bound_are_split_by_size(self):
        text = ' '.join(f'detail{n}' for n in range(70))
        ids = [f'r1:advisory:{i}' for i in range(10)]
        code, response = self.review_findings(advisory_report(f'finding {i} {text}' for i in range(len(ids))),
                                              {i: answered('agent-assessment') for i in ids})
        self.assertEqual(code, 0, response)
        requests = self.requests
        self.assertGreaterEqual(len(requests), 2)
        self.assertLess(max(len(q) for _, q in requests), MAX_QUESTIONS, 'the size bound split a set the count bound would have kept whole')
        self.assertLessEqual(len(ids), MAX_QUESTIONS + 2)
        self.assert_bounded(requests, ids)
        self.assertEqual(sorted(self.findings()), sorted(ids))
        self.assertEqual({e['fallback'] for e in self.findings().values()}, {None}, 'no request fell back over the input bound')

    def test_batches_split_only_findings_that_share_a_state(self):
        # Two reviews' worth of states cannot share a request: the batcher groups by kind, shared state and item field.
        job = cycle_classify.Job
        plan = cycle_classify.Plan
        one = [[job('finding-disposition', f'r1:advisory:{i}'), plan({'review': 'a'}, ['agent-assessment'], None, {'id': f'r1:advisory:{i}'}, 'findings'), None]
               for i in range(2)]
        two = [[job('finding-disposition', f'r2:advisory:{i}'), plan({'review': 'b'}, ['agent-assessment'], None, {'id': f'r2:advisory:{i}'}, 'findings'), None]
               for i in range(2)]
        grouped = cycle_classify.batches(one[:1] + two[:1] + one[1:] + two[1:])
        self.assertEqual([[i[0].subject for i in batch] for batch in grouped],
                         [['r1:advisory:0', 'r1:advisory:1'], ['r2:advisory:0', 'r2:advisory:1']])


class BlockingFindingRouteTests(BatchBase):
    def report(self):
        blocking = [{**BLOCKING, 'path': f'src/b{i}.py'} for i in range(4)]
        return {'verdict': 'changes-required', 'blocking': blocking, 'advisory': ['LEAK-ZQ-advisory note'], 'cosmetic': []}

    def test_blocking_findings_are_offered_only_fix_routes_and_other_answers_fall_back(self):
        ids = [f'r1:blocking:{i}' for i in range(4)]
        replies = {ids[0]: answered('fix-step'), ids[1]: answered('return'), ids[2]: answered('follow-up'), ids[3]: answered('agent-assessment'),
                   'r1:advisory:0': answered('follow-up')}
        code, response = self.review_findings(self.report(), replies)
        self.assertEqual(code, 0, response)
        options = {call['id']: list(call['question'].options) for call in self.asked}
        for ident in ids:
            self.assertEqual(options[ident], ['fix-step', 'return', 'insufficient-information'], ident)
            self.assertFalse({'follow-up', 'agent-assessment'} & set(options[ident]), ident)
        self.assertIn('follow-up', options['r1:advisory:0'], 'a non-blocking finding is still offered a follow-up')
        entries = self.findings()
        self.assertEqual([(entries[i]['route'], entries[i]['fallback']) for i in ids],
                         [('fix-step', None), ('return', None), (None, 'route-not-permitted'), (None, 'route-not-permitted')])
        self.assertEqual([entries[i]['answer']['choice'] for i in ids[2:]], ['follow-up', 'agent-assessment'])
        self.assertEqual((entries['r1:advisory:0']['route'], entries['r1:advisory:0']['fallback']), ('follow-up', None))
        self.assertEqual(load(self.repo, self.cid).get('deferrals', []), [], 'no answer deferred a blocking finding')

    def test_a_blocking_finding_with_no_permitted_fix_step_is_offered_only_the_return(self):
        ids = [f'r1:blocking:{i}' for i in range(4)]
        with mock.patch.object(cycle_classify, 'fix_step_problem', lambda doc, cfg: 'one fix task per phase per pass'):
            self.review_findings(self.report(), {**{i: answered('fix-step') for i in ids}, 'r1:advisory:0': answered('agent-assessment')})
        options = {call['id']: list(call['question'].options) for call in self.asked}
        for ident in ids:
            self.assertEqual(options[ident], ['return', 'insufficient-information'], ident)
        self.assertEqual([self.findings()[i]['fallback'] for i in ids], ['route-not-permitted'] * 4)


class SeveralSpecialistTests(BatchBase):
    def adding(self, *wanted):
        """A review reply that answers yes for each wanted specialist and floor-only for every other."""
        def reply(state, question):
            ident = next(route[4:] for route in question.options if route.startswith('add:'))
            return answered(f'add:{ident}' if ident in wanted else 'floor-only')
        return reply

    def enter(self, *wanted, risks=('release',)):
        mutate(self.repo, self.cid, 'scrutiny', scrutiny='standard', rationale='r', risks=list(risks))
        self.add_review_task()
        self.ready_for_review()
        self.review = self.adding(*wanted)
        self.ok(self.advance('advance-t1'))

    def test_several_specialists_are_added_at_once_and_the_floor_stays_whole(self):
        self.enter('untrusted-input-execution', 'credentials-and-data-transmission', 'authentication-and-authorization')
        review = self.inspect()['review']
        self.assertEqual(review['floor'], ['release-distribution'])
        order = [i for i in cycle_classify.SPECIALISTS if i in review['added']]
        self.assertEqual(review['added'], order, 'additions keep the order of the specialist table')
        self.assertEqual(sorted(review['added']), ['authentication-and-authorization', 'credentials-and-data-transmission', 'untrusted-input-execution'])
        self.assertEqual(review['specialists'], ['release-distribution', *review['added']])
        block = cycle_classify.review_block(cycle_classify.tree(self.repo), load(self.repo, self.cid))
        self.assertEqual((block['floor'], block['added'], block['specialists']), (review['floor'], review['added'], review['specialists']))
        dispatch = next(a for a in self.inspect()['actions'] if a.get('request', {}).get('task_id') == 'review-it')
        self.assertEqual(dispatch['specialists'], review['specialists'])
        routes = {e['subject']: e['route'] for e in self.entries('review-routing')}
        self.assertNotIn('review:release-distribution', routes, 'no question was asked for a specialist already on the floor')

    def test_a_floor_specialist_is_never_lowered_by_an_answer_naming_another(self):
        self.enter('model-routing-boundary')
        review = self.inspect()['review']
        self.assertEqual((review['floor'], review['added']), (['release-distribution'], ['model-routing-boundary']))
        self.assertEqual(review['specialists'], ['release-distribution', 'model-routing-boundary'])

    def test_two_added_specialists_sharing_a_concern_keep_the_first_in_table_order(self):
        self.enter('untrusted-input-execution', 'authentication-and-authorization')
        with mock.patch.dict(cycle_classify.SPECIALISTS['untrusted-input-execution'], {'concern': 'authentication-and-authorization'}):
            review = self.inspect()['review']
            self.assertEqual(review['added'], ['authentication-and-authorization'])
            self.assertEqual(review['specialists'], ['release-distribution', 'authentication-and-authorization'])
        with mock.patch.dict(cycle_classify.SPECIALISTS['authentication-and-authorization'], {'concern': 'untrusted-input-execution'}):
            self.assertEqual(self.inspect()['review']['added'], ['authentication-and-authorization'],
                             'the first in table order stays, whichever concern name the two share')
        self.assertEqual(self.inspect()['review']['added'], ['authentication-and-authorization', 'untrusted-input-execution'])

    def test_an_addition_whose_concern_the_floor_covers_is_dropped(self):
        self.enter('model-routing-boundary', 'untrusted-input-execution')
        with mock.patch.dict(cycle_classify.SPECIALISTS['model-routing-boundary'], {'concern': 'release-distribution'}):
            review = self.inspect()['review']
            self.assertEqual((review['floor'], review['added']), (['release-distribution'], ['untrusted-input-execution']))
            self.assertEqual(review['specialists'], ['release-distribution', 'untrusted-input-execution'])


class RequestConcurrencyTests(unittest.TestCase):
    def run_batches(self, count):
        """Ask `count` unrelated batches through `ask_batches`; return (max simultaneous requests, items)."""
        lock, state = threading.Lock(), {'now': 0, 'max': 0}

        def slow(batch_state, questions, *, deadline, client=None, kinds=()):
            with lock:
                state['now'] += 1
                state['max'] = max(state['max'], state['now'])
            time.sleep(0.05)
            with lock:
                state['now'] -= 1
            return {qid: answered('agent-assessment') for qid in questions}
        items = [[cycle_classify.Job('failure-routing', f'task-{n}', 'check:x'), cycle_classify.Plan({'n': n}, ['agent-assessment'], None), None] for n in range(count)]
        self.assertEqual(len(cycle_classify.batches(items)), count, 'unrelated states never share a request')
        with mock.patch.object(decisions, 'ask_many', slow):
            cycle_classify.ask_batches(items, decisions.Deadline())
        return state['max'], items

    def test_unrelated_requests_run_at_most_the_concurrency_bound_at_once(self):
        with mock.patch.object(decisions, 'REQUEST_CONCURRENCY', 2):
            peak, items = self.run_batches(6)
        self.assertEqual(peak, 2)
        self.assertEqual([i[2].choice for i in items], ['agent-assessment'] * 6, 'every batch was answered')

    def test_the_default_bound_is_three_and_a_single_request_runs_alone(self):
        self.assertEqual(decisions.REQUEST_CONCURRENCY, 3)
        peak, _ = self.run_batches(7)
        self.assertLessEqual(peak, decisions.REQUEST_CONCURRENCY)
        self.assertGreaterEqual(peak, 2, 'unrelated requests did not overlap')
        self.assertEqual(self.run_batches(1)[0], 1)


class PerAnswerFallbackTests(BatchBase):
    def test_a_malformed_and_a_refused_answer_keep_the_other_findings_valid_answers(self):
        ids = [f'r1:advisory:{i}' for i in range(4)]
        code, response = self.review_findings(advisory_report(f'finding number {i}' for i in range(4)), {
            ids[0]: answered('agent-assessment'), ids[1]: failed('malformed', request_id='gen-req-0001'),
            ids[2]: failed('refusal', request_id='gen-req-0001'), ids[3]: answered('follow-up')})
        self.assertEqual(code, 0, response)
        self.assertEqual([q for _, q in self.requests], [ids], 'one request carried all four')
        entries = self.findings()
        self.assertEqual([(entries[i]['route'], entries[i]['fallback']) for i in ids],
                         [('agent-assessment', None), (None, 'malformed'), (None, 'refusal'), ('follow-up', None)])
        reported = {r['subject']: r for r in response['classifications']}
        self.assertEqual([reported[i]['fallback'] for i in ids], [None, 'malformed', 'refusal', None])

    def test_the_real_transport_keeps_valid_answers_beside_a_malformed_and_a_refused_one(self):
        requests = []

        def serve(request):
            requests.append(request)
            asked = json.loads(request.content)
            answers = {}
            for qid in self.question_ids(asked):
                if qid.startswith('review:'):
                    answers[qid] = {'type': 'choice', 'choice': 'floor-only'}
                else:
                    answers[qid] = {'r1:advisory:0': {'type': 'choice', 'choice': 'agent-assessment', 'confidence': 0.7},
                                    'r1:advisory:1': {'type': 'choice', 'choice': 'not-an-offered-route'},
                                    'r1:advisory:2': {'type': 'refusal'},
                                    'r1:advisory:3': {'type': 'choice', 'choice': 'follow-up'}}[qid]
            return httpx.Response(200, json={'id': 'gen-dec-9', 'model': MODEL, 'answers': answers, 'usage': {'cost': 2.0e-05}})
        client = httpx.Client(transport=httpx.MockTransport(serve))
        real_ask_many, real_get = transport.ask_many, crux_env.get
        for target, name, replacement in (
                (decisions, 'ask_many', lambda state, questions, *, deadline, client_=None, **_: real_ask_many(state, questions, deadline=deadline, client=client)),
                (crux_env, 'get', lambda key, default=None: FAKE_KEY if key == 'OPENROUTER_API_KEY' else real_get(key, default))):
            patcher = mock.patch.object(target, name, replacement)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.enter_review()
        before = len(requests)
        self.default = None
        code, response = self.record_review(self.receipt_id, advisory_report(f'finding number {i}' for i in range(4)))
        self.assertEqual(code, 0, response)
        self.assertEqual(len(requests) - before, 1, 'the four findings share one wire request')
        entries = self.findings()
        ids = [f'r1:advisory:{i}' for i in range(4)]
        self.assertEqual([(entries[i]['route'], entries[i]['fallback']) for i in ids],
                         [('agent-assessment', None), (None, 'malformed'), (None, 'refusal'), ('follow-up', None)])
        self.assertEqual({entries[i]['request_id'] for i in ids}, {'gen-dec-9'})
        self.assertEqual([entries[i]['cost'] for i in ids], [2.0e-05, None, None, None], 'the request cost is recorded once')

    @staticmethod
    def question_ids(payload):
        text = json.dumps(payload)
        found = []
        for ident in [f'review:{i}' for i in cycle_classify.SPECIALISTS] + [f'r1:advisory:{i}' for i in range(4)]:
            if f'"{ident}"' in text:
                found.append(ident)
        return found


if __name__ == '__main__':
    unittest.main()
