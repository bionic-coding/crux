"""Route classifications are visible: inspect, the status reader, the bounded summary, the completion record, and queue sizing.

Every provider answer is scripted; no test sends a request. See _classify_support for the fixtures.
"""
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cycle_classify
import cycle_progress
import cycle_questions
import cycle_summary
from crux import decisions
from cycle_workflow import create, load, mutate
from _classify_support import ClassifyBase, MODEL, answered, failed, one_at_a_time
import test_cycle_queue
from test_cycle_ops_finish import FinishBase


# A Review entry in the fixture repo asks one review-routing predicate per specialist, and every entry counts.
SPECIALISTS = len(cycle_classify.SPECIALISTS)


def billed(choice, provider='Moonshot AI', cost=0.00042, request_id='gen-req-0001'):
    return decisions.Outcome(status=decisions.ANSWERED, choice=choice, probabilities=None, confidence=0.9, request_id=request_id,
                             served_model=MODEL, served_provider=provider, usage={'cost': cost} if cost is not None else None, attempts=1)


class RowTests(unittest.TestCase):
    def test_summary_is_the_first_sentence_of_the_instructions(self):
        self.assertEqual(cycle_questions.summary('work-sizing'), 'Choose the cycle type that fits the proposed work.')
        self.assertIsNone(cycle_questions.summary('no-such-kind'))

    def test_a_cost_is_never_invented(self):
        base = {'kind': 'work-sizing', 'request_id': 'r', 'served_model': MODEL, 'answer': None, 'route': None, 'fallback': 'timeout'}
        self.assertEqual(cycle_questions.entry_row({**base, 'cost': None})['cost_note'], 'the gateway response carried no cost')
        self.assertEqual(cycle_questions.entry_row({**base, 'request_id': None, 'served_model': None, 'cost': None})['cost_note'],
                         'no gateway response was received')
        self.assertEqual(cycle_questions.entry_row(base)['cost_note'], 'the entry predates cost capture')
        self.assertEqual((cycle_questions.entry_row({**base, 'cost': 0.5})['cost'], cycle_questions.entry_row({**base, 'cost': 0.5})['cost_note']), (0.5, None))
        self.assertIsNone(cycle_questions.entry_row(base)['cost'])


class VisibilityTests(ClassifyBase):
    def review_rows(self):
        return [row for row in self.inspect()['classifications'] if row['kind'] == 'review-routing']

    def test_inspect_shows_kind_question_answer_route_provider_and_cost(self):
        self.enter_review(billed('floor-only'))
        rows = self.review_rows()
        self.assertEqual(len(rows), SPECIALISTS, 'one row per review predicate')
        for row in rows:
            self.assertEqual((row['kind'], row['answer'], row['route'], row['fallback'], row['served_model'], row['served_provider'], row['cost'], row['cost_note']),
                             ('review-routing', 'floor-only', 'floor-only', None, MODEL, 'Moonshot AI', 0.00042, None))
            self.assertTrue(row['question'].startswith('The engine has fixed the review floor'), row['question'])

    def test_inspect_shows_a_fallback_with_its_reason_and_a_null_cost_with_its_note(self):
        self.enter_review(failed('timeout'))
        rows = self.review_rows()
        self.assertEqual(len(rows), SPECIALISTS)
        for row in rows:
            self.assertEqual((row['route'], row['fallback'], row['answer'], row['cost'], row['cost_note']),
                             (None, 'timeout', None, None, 'no gateway response was received'))

    def test_a_billed_answer_without_a_cost_records_null_with_a_reason(self):
        self.enter_review(billed('floor-only', cost=None))
        rows = self.review_rows()
        self.assertEqual(len(rows), SPECIALISTS)
        for row in rows:
            self.assertEqual((row['served_provider'], row['cost'], row['cost_note']), ('Moonshot AI', None, 'the gateway response carried no cost'))

    def test_the_stored_entry_keeps_provider_and_cost(self):
        self.enter_review(billed('floor-only'))
        entries = self.entries('review-routing')
        self.assertEqual(len(entries), SPECIALISTS)
        for entry in entries:
            self.assertEqual((entry['served_provider'], entry['cost']), ('Moonshot AI', 0.00042))

    def test_the_status_reader_shows_only_the_count(self):
        self.enter_review(billed('floor-only'))
        (cycle,) = cycle_progress.view(self.repo, self.cid)['cycles']
        count = len(self.entries())
        self.assertEqual(cycle['classification_count'], count)
        text = cycle_progress.render(cycle_progress.view(self.repo, self.cid))
        self.assertIn(f'  Classifications: {count}', text.splitlines())
        for detail in ('review-routing', 'floor-only', 'Moonshot AI', '0.00042', 'The engine has fixed the review floor'):
            self.assertNotIn(detail, text)
        for row in self.review_rows():  # inspect keeps every detail for the routed review
            self.assertEqual((row['served_provider'], row['cost']), ('Moonshot AI', 0.00042))

    def test_a_fallback_counts_like_any_other_classification(self):
        self.enter_review(failed('timeout'))
        text = cycle_progress.render(cycle_progress.view(self.repo, self.cid))
        self.assertIn(f'  Classifications: {len(self.entries())}', text.splitlines())
        self.assertNotIn('timeout', text)

    def test_the_bounded_summary_lists_the_classifications(self):
        self.enter_review(billed('floor-only'))
        summary = cycle_summary.summarize(load(self.repo, self.cid))
        rows = [row for row in summary['classifications'] if row['kind'] == 'review-routing']
        self.assertEqual(len(rows), SPECIALISTS)
        for row in rows:
            self.assertEqual((row['kind'], row['route'], row['served_provider'], row['cost']), ('review-routing', 'floor-only', 'Moonshot AI', 0.00042))


class CompletionRecordTests(FinishBase):
    def test_finish_reports_the_classifications_beside_the_completion(self):
        doc = create(self.repo, 'release', 'Ship', 'Release it', ['src'], ['shipped'], 'builder', 'tester', release_list='official')
        cid = doc['id']
        self.v3(cid)
        path = self.record_path(cid)
        raw = json.loads(path.read_text())
        raw['classifications'] = [{'kind': 'failure-routing', 'request_id': 'gen-req-0009', 'question_set': 'failure-routing', 'question_version': '1',
                                   'model': MODEL, 'served_model': MODEL, 'served_provider': 'Moonshot AI', 'cost': 0.001,
                                   'answer': {'choice': 're-dispatch', 'probabilities': None}, 'route': 're-dispatch', 'fallback': None,
                                   'subject': 'x', 'fingerprint': 'f' * 64, 'trigger': 'failed-delivery', 'pass': 1, 'phase': 'release',
                                   'at': '2026-01-01T00:00:00+00:00', 'revision': 1}]
        path.write_text(json.dumps(raw, indent=2, sort_keys=True) + '\n')
        for task in load(self.repo, cid)['plan']['tasks']:
            sha = self.commit_file(f'src/{task["id"]}.txt', task['id'], f'step {task["id"]}')
            mutate(self.repo, cid, 'task', task_id=task['id'], state='done', commits=[sha])
        response = self.ok(self.finish_request(cid=cid), cid=cid)
        (row,) = response['completion']['classifications']
        self.assertEqual((row['kind'], row['route'], row['served_provider'], row['cost']), ('failure-routing', 're-dispatch', 'Moonshot AI', 0.001))


class QueueSizingTests(test_cycle_queue.Base):
    def setUp(self):
        super().setUp()
        self.asked, self.reply = [], None
        self.status = decisions.Status(True, None)
        for target, replacement in (('classifier_status', lambda: self.status), ('ask', self.scripted_ask),
                                    ('ask_many', one_at_a_time(self.scripted_ask))):
            patcher = mock.patch.object(decisions, target, replacement)
            patcher.start()
            self.addCleanup(patcher.stop)

    def scripted_ask(self, state, question_id, question, *, deadline, client=None):
        self.asked.append({'state': state, 'id': question_id, 'options': list(question.options)})
        return self.reply

    def started_entries(self):
        record = json.loads(next((self.repo / 'notes/cycles').glob('*CYC-*/cycle.json')).read_text())
        return record, record.get('classifications', [])

    def go(self, kind):
        self.add('Item', kind=kind)
        self.authorize('queue')
        return self.start()

    def test_an_unconfigured_classifier_sizes_nothing(self):
        self.status = decisions.Status(False, 'no-key')
        code, payload = self.go('quick-fix')
        self.assertEqual(code, 0, payload)
        self.assertEqual(self.asked, [])
        self.assertEqual(self.started_entries()[1], [])

    def test_a_suggested_type_stands_without_an_advisory_request(self):
        self.reply = billed('dev')
        code, payload = self.go('quick-fix')
        self.assertEqual(code, 0, payload)
        record, entries = self.started_entries()
        self.assertEqual(record['type'], 'quick-fix')
        self.assertEqual(entries, [])
        self.assertEqual(self.asked, [])

    def test_a_typed_item_starts_without_asking_for_advisory_fallback(self):
        self.reply = failed('timeout')
        code, payload = self.go('iterate')
        self.assertEqual(code, 0, payload)
        record, entries = self.started_entries()
        self.assertEqual(record['type'], 'iterate')
        self.assertEqual(entries, [])
        self.assertEqual(self.asked, [])

    def test_a_release_item_is_not_sized(self):
        self.reply = billed('dev')
        self.add('Ship', kind='release')
        self.authorize('queue')
        self.start()
        self.assertEqual(self.asked, [])

    def test_an_item_naming_no_type_takes_the_classifier_answer(self):
        self.reply = billed('refactor')
        code, payload = self.go('auto')
        self.assertEqual(code, 0, payload)
        record, entries = self.started_entries()
        self.assertEqual(record['type'], 'refactor')
        (entry,) = entries
        self.assertEqual((entry['route'], entry['trigger'], entry['revision']), ('refactor', 'queue-selecting', 1))
        self.assertNotIn('release', self.asked[0]['options'])

    def test_a_selecting_fallback_stops_the_queue_and_creates_nothing(self):
        self.reply = billed('insufficient-information')
        code, payload = self.go('auto')
        self.assertEqual(code, 1, payload)
        self.assertEqual(payload['stop']['reason'], 'sizing-fallback')
        self.assertIn('insufficient-information', payload['stop']['detail'])
        self.assertEqual(self.cycle_dirs(), [])
        self.assertEqual(self.item('Q-0001')['state'], 'pending')

    def test_an_item_naming_no_type_needs_the_classifier(self):
        self.status = decisions.Status(False, 'no-key')
        code, payload = self.go('auto')
        self.assertEqual(code, 1, payload)
        self.assertEqual(payload['stop']['reason'], 'classifier-unconfigured')
        self.assertEqual(self.cycle_dirs(), [])


if __name__ == '__main__':
    unittest.main()
