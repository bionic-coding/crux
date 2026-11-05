"""Input reuse removes repeat gateway requests while code retains route authority.

No test uses a live provider. Same-length edits beyond clipped text must still
invalidate an answer; administrative revision changes must not ask again.
"""
from contextlib import contextmanager
from dataclasses import replace
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cycle_classify
import cycle_questions
from crux import decisions
from cycle_workflow import CycleError, event, load, locked, save, validate
from _classify_support import ClassifyBase, answered, failed


class ReuseTests(ClassifyBase):
    def edit(self, function):
        with locked(self.repo) as (cfg, _):
            doc = load(self.repo, self.cid)
            function(doc)
            event(doc, 'reuse-test-edit')
            save(cfg, doc)

    def start(self, reply=None):
        self.add_review_task('review ' + 'x' * 400)
        self.enter_review(reply or answered('floor-only'))
        self.before = len(self.asked)

    def repeat(self):
        return cycle_classify.entered_review(self.repo, self.cid)

    def change_task(self, doc):
        task = next(t for t in doc['plan']['tasks'] if t['phase'] == 'review')
        task['description'] = task['description'][:-1] + ('y' if task['description'][-1] == 'x' else 'x')

    def test_bookkeeping_revision_reuses_and_names_original_request(self):
        self.start()
        original = list(self.legacy_entries())
        self.edit(lambda doc: None)
        found = self.repeat()
        self.assertEqual(len(self.asked), self.before, 'bookkeeping caused another gateway request')
        reused = self.legacy_entries()[len(original):]
        self.assertEqual(len(reused), len(original))
        for old, new in zip(original, reused):
            self.assertEqual(new['fingerprint'], old['fingerprint'])
            self.assertEqual(new['request_id'], old['request_id'])
            self.assertEqual(new['reused_from']['request_id'], old['request_id'])
            self.assertEqual(new['reused_from']['revision'], old['revision'])
            self.assertIsNone(new['cost'], 'reuse counted an old gateway bill again')
        self.assertTrue(all(item.get('reused_from') for item in found['classifications']))

    def test_identical_replay_at_current_revision_is_deduplicated(self):
        self.start()
        count = len(self.legacy_entries())
        self.repeat()
        self.assertEqual((len(self.legacy_entries()), len(self.asked)), (count, self.before))

    def test_same_length_task_edit_after_clipping_invalidates_same_pass(self):
        self.start()
        old = self.legacy_entries()[0]['fingerprint']
        self.edit(self.change_task)
        self.repeat()
        self.assertEqual(len(self.asked), 2 * self.before)
        self.assertNotEqual(self.legacy_entries()[-1]['fingerprint'], old)

    def test_concurrent_bookkeeping_write_keeps_answer_without_reask(self):
        self.hook = lambda n: self.edit(lambda doc: None) if n == 1 else None
        self.start()
        self.assertEqual(len(self.asked), len(cycle_classify.SPECIALISTS))
        self.assertEqual({e['fallback'] for e in self.legacy_entries()}, {None})

    def test_concurrent_content_write_reasks_once(self):
        self.add_review_task('review ' + 'x' * 400)
        self.hook = lambda n: self.edit(self.change_task) if n == 1 else None
        self.enter_review(answered('floor-only'))
        self.assertEqual(len(self.asked), 2 * len(cycle_classify.SPECIALISTS))
        self.assertEqual({e['fallback'] for e in self.legacy_entries()}, {None})

    def test_second_concurrent_content_write_falls_back(self):
        self.add_review_task('review ' + 'x' * 400)
        size = len(cycle_classify.SPECIALISTS)
        self.hook = lambda n: self.edit(self.change_task) if n in (1, size + 1) else None
        self.enter_review(answered('floor-only'))
        self.assertEqual(len(self.asked), 2 * size)
        self.assertEqual({e['fallback'] for e in self.legacy_entries()}, {'stale'})

    def test_question_version_and_text_invalidate_reuse(self):
        self.start()
        original = cycle_questions.question_set('review-routing')
        for changed in (replace(original, version='reuse-test'), replace(original, instructions=original.instructions + ' Reconsider.')):
            with self.subTest(changed=changed), mock.patch.object(cycle_questions, 'QUESTION_SETS',
                    {**cycle_questions.QUESTION_SETS, 'review-routing': changed}):
                before = len(self.asked)
                self.repeat()
                self.assertEqual(len(self.asked), before + len(cycle_classify.SPECIALISTS))

    def test_configuration_and_policy_versions_invalidate_reuse(self):
        self.start()
        for target, name, value in ((cycle_classify, 'ROUTING_POLICY_VERSION', 'changed'),
                                    (decisions, 'classifier_basis', lambda: {'model': 'changed', 'endpoint': 'other'})):
            with self.subTest(name=name), mock.patch.object(target, name, value):
                before = len(self.asked)
                self.repeat()
                self.assertEqual(len(self.asked), before + len(cycle_classify.SPECIALISTS))

    def test_changed_denial_and_opt_out_reuse_nothing(self):
        self.start()
        count = len(self.legacy_entries())
        with mock.patch.object(decisions, 'REQUIRED_DENIALS', {'data_collection': 'allow'}):
            self.edit(lambda doc: None)
            self.repeat()
        self.assertEqual((len(self.legacy_entries()), len(self.asked)), (count, self.before))
        config = self.repo / '.bionic.yml'
        config.write_text('config_version: "1"\ndocs_dir: bionic\ndecisions:\n  classifier: off\n')
        self.repeat()
        self.assertEqual((len(self.legacy_entries()), len(self.asked)), (count, self.before))

    def test_fallen_back_answer_is_never_reused(self):
        self.start(failed('timeout'))
        self.edit(lambda doc: None)
        self.repeat()
        self.assertEqual(len(self.asked), 2 * self.before)
        self.assertFalse(any(e.get('reused_from') for e in self.legacy_entries()))

    def test_clipped_fields_name_their_original_lengths(self):
        self.start()
        state = self.asked[0]['state']
        marker = state['clipped']['tasks[0].description']
        self.assertTrue(marker['clipped'])
        self.assertEqual(marker['original_length'], 407)
        self.assertIn('insufficient-information', self.asked[0]['question'].options)
        self.assertNotIn('x' * 400, json.dumps(self.legacy_entries()), 'complete source text entered the record')

    def test_inspect_drops_route_after_clipped_source_changes(self):
        self.start(answered('add:untrusted-input-execution'))
        self.assertIn('untrusted-input-execution', self.inspect()['review']['added'])
        self.edit(self.change_task)
        self.assertNotIn('untrusted-input-execution', self.inspect()['review']['added'])

    def test_offered_option_text_invalidates_an_answer(self):
        self.start()
        original = cycle_questions.question_set('review-routing')
        changed = replace(original, descriptions={**original.descriptions, 'floor-only': 'Keep only the required floor.'})
        with mock.patch.object(cycle_questions, 'QUESTION_SETS', {**cycle_questions.QUESTION_SETS, 'review-routing': changed}):
            self.repeat()
        self.assertEqual(len(self.asked), 2 * self.before)

    def test_same_length_finding_tail_change_invalidates_reuse(self):
        self.enter_review(answered('floor-only'))
        self.default = answered('agent-assessment')
        self.record_review(self.receipt_id, {'verdict': 'approve', 'blocking': [], 'advisory': ['x' * 800], 'cosmetic': []})
        before = len(self.asked)
        real = cycle_classify.finding_at

        def changed(*args):
            found = real(*args)
            return (*found[:-1], 'x' * 799 + 'y') if found else None
        with mock.patch.object(cycle_classify, 'finding_at', changed):
            cycle_classify.recorded_review(self.repo, self.cid)
        self.assertEqual(len(self.asked), before + 1, 'a finding edit past the clipping boundary reused its old answer')
        self.assertNotEqual(self.entries('finding-disposition')[-2]['fingerprint'], self.entries('finding-disposition')[-1]['fingerprint'])

    def test_duplicate_batch_question_ids_are_rejected(self):
        self.start()
        doc = load(self.repo, self.cid)
        doc['classifications'][0]['question_ids'] = ['same', 'same']
        with self.assertRaisesRegex(CycleError, 'question_ids must be unique'):
            validate(doc)

    def test_cached_answer_is_revalidated_against_current_options(self):
        self.start(answered('add:untrusted-input-execution'))
        self.edit(lambda doc: None)
        real = cycle_classify.plan_of

        def narrowed(cfg, doc, job, repo_root=None):
            plan = real(cfg, doc, job, repo_root)
            if plan is not None and job.subject == 'review:untrusted-input-execution':
                plan.routes = ['floor-only']
            return plan
        with mock.patch.object(cycle_classify, 'plan_of', narrowed):
            self.repeat()
            self.assertNotIn('untrusted-input-execution', self.inspect()['review']['added'])
        latest = next(e for e in reversed(self.legacy_entries()) if e['subject'] == 'review:untrusted-input-execution')
        self.assertIsNone(latest.get('reused_from'))

    def test_input_changes_after_cache_lookup_are_revalidated_under_lock(self):
        self.start()
        self.edit(lambda doc: None)
        real, changed = cycle_classify.locked, []

        @contextmanager
        def after_lookup(repo):
            with real(repo) as pair:
                if not changed:
                    changed.append(True)
                    cfg, _ = pair
                    doc = load(repo, self.cid)
                    self.change_task(doc)
                    save(cfg, doc)
                yield pair
        with mock.patch.object(cycle_classify, 'locked', after_lookup):
            self.repeat()
        self.assertEqual(len(self.asked), 2 * self.before, 'a stale cache hit crossed the locked write')
        self.assertFalse(any(e.get('reused_from') for e in self.legacy_entries()[self.before:]))


if __name__ == '__main__':
    unittest.main()
