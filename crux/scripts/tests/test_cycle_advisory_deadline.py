"""Optional discovery/currentness must yield without installing partial or stale answers."""
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
from _classify_support import ClassifyBase, answered
from test_cycle_classify_new_kinds import NewBase
from crux import decisions
import cycle_classify as classify
import cycle_context as context
import cycle_ops
from cycle_workflow import event, load, locked, save, tree


class DeadlineTests(ClassifyBase):
    source = 'crux/scripts/cycle_workflow.py'
    gate = 'crux/scripts/generate-micro-crux.py'

    def setUp(self):
        super().setUp()
        files = {
            self.source: 'answer = 1\n',
            self.gate: "SOURCE = 'crux/scripts/cycle_workflow.py'\n",
            'crux/scripts/tests/test_required.py': "SOURCE = 'crux/scripts/cycle_workflow.py'\n",
            'crux/scripts/tests/test_micro_reader.py': "SOURCE = 'crux/scripts/generate-micro-crux.py'\n",
            'crux/skills/check-drift/SKILL.md': '| Gate (output) | Scope | Command |\n| --- | --- | --- |\n| micro | plugin | generate-micro-crux.py --dry-run |\n',
        }
        for name, text in files.items():
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        self.git('add', 'crux')
        self.git('commit', '-q', '-m', 'deadline fixture')
        with locked(self.repo) as (cfg, _):
            doc = load(self.repo, self.cid)
            doc['plan']['scope'] = ['crux/scripts']
            event(doc, 'deadline-fixture')
            save(cfg, doc)
        (self.repo / self.source).write_text('answer = 2\n')
        self.default = answered('include')
        self.clock = [0.0]
        self.deadline = decisions.Deadline(seconds=1, clock=lambda: self.clock[0])

    def exhaust(self):
        self.clock[0] = 2.0

    def test_discovery_exhaustion_returns_unavailable_before_provider(self):
        real = context._focused_candidates
        def discover(*args):
            result = real(*args)
            self.exhaust()
            return result
        before = self.record_path().read_bytes()
        with mock.patch.object(context, '_focused_candidates', discover):
            result = classify.focused_tests(self.repo, self.cid, decisions_deadline=self.deadline)
        self.assertEqual(result['suggested_checks'], [])
        self.assertEqual(result['classification_unavailable'], 'deadline-exhausted')
        self.assertEqual(self.provider_calls, [])
        self.assertEqual(self.record_path().read_bytes(), before)

    def test_post_provider_currentness_exhaustion_installs_no_answer(self):
        self.hook = lambda number: self.exhaust()
        result = classify.focused_tests(self.repo, self.cid, decisions_deadline=self.deadline)
        self.assertEqual(result['suggested_checks'], [])
        self.assertEqual(result['classification_unavailable'], 'deadline-exhausted')
        self.assertTrue(all(entry['route'] is None and entry['fallback'] == 'unavailable'
                            for entry in self.entries('focused-test-ranking')))
        self.assertTrue(self.provider_calls)

    def test_currentness_exhaustion_discards_earlier_validated_candidates(self):
        classify.focused_tests(self.repo, self.cid)
        cfg, doc = tree(self.repo), load(self.repo, self.cid)
        before = self.record_path().read_bytes(), len(self.provider_calls)
        real = classify.valid_plan
        seen = []
        def validate(*args, **kwargs):
            plan = real(*args, **kwargs)
            seen.append(plan)
            self.exhaust()
            return plan
        with context.advisory_scope(self.deadline), mock.patch.object(classify, 'valid_plan', validate):
            with self.assertRaises(context.AdvisoryUnavailable):
                classify.focused_suggestions(cfg, doc)
        self.assertIsNotNone(seen[0])
        self.assertEqual((self.record_path().read_bytes(), len(self.provider_calls)), before)

    def test_inspect_exhaustion_preserves_bytes_actions_and_no_provider(self):
        classify.focused_tests(self.repo, self.cid)
        before = self.record_path().read_bytes(), len(self.provider_calls)
        real = context._focused_candidates
        def discover(*args):
            result = real(*args)
            self.exhaust()
            return result
        with context.advisory_scope(self.deadline), mock.patch.object(context, '_focused_candidates', discover):
            result = self.inspect()
        self.assertEqual(result['focused_suggestions'], [])
        self.assertEqual(result['advisory_unavailable'], 'deadline-exhausted')
        self.assertTrue(result['actions'])
        self.assertEqual((self.record_path().read_bytes(), len(self.provider_calls)), before)

    def test_one_snapshot_reuses_discovery_but_later_source_read_is_fresh(self):
        classify.focused_tests(self.repo, self.cid)
        cfg, doc = tree(self.repo), load(self.repo, self.cid)
        with mock.patch.object(context, '_focused_candidates', wraps=context._focused_candidates) as discover:
            self.assertTrue(classify.focused_suggestions(cfg, doc))
            self.assertEqual(discover.call_count, 1)
            (self.repo / self.source).write_text('answer = 3\n')
            self.assertEqual(classify.focused_suggestions(cfg, doc), [])
            self.assertEqual(discover.call_count, 2)

    def test_source_mutation_between_discovery_and_currentness_cannot_publish_cached_suggestions(self):
        classify.focused_tests(self.repo, self.cid)
        cfg, doc = tree(self.repo), load(self.repo, self.cid)
        before = self.record_path().read_bytes(), len(self.provider_calls)
        real = context.focused_candidates
        changed = []
        def discover(*args):
            result = real(*args)
            if not changed:
                changed.append(True)
                (self.repo / self.source).write_text('answer = 300\n')
            return result
        with mock.patch.object(context, 'focused_candidates', discover):
            self.assertEqual(classify.focused_suggestions(cfg, doc), [])
        self.assertEqual((self.record_path().read_bytes(), len(self.provider_calls)), before)

    def test_expired_prepare_retains_mandatory_assignment(self):
        self.git('add', self.source)
        self.git('commit', '-q', '-m', 'commit deadline fixture before dispatch')
        self.exhaust()
        with context.advisory_scope(self.deadline):
            prepared = self.prepare()
        parameters = prepared['invocation']['parameters']
        self.assertIn('Mandatory assignment', parameters.get('message', parameters.get('prompt', '')))
        self.assertEqual(self.provider_calls, [])
        self.assertEqual(load(self.repo, self.cid)['assignments'][-1]['state'], 'reserved')

    def test_expired_delivery_keeps_persisted_delivery(self):
        self.git('add', self.source)
        self.git('commit', '-q', '-m', 'commit deadline fixture before dispatch')
        prepared = self.prepare()
        sha = self.work(prepared)
        self.write_result(prepared)
        before = len(self.provider_calls)
        self.exhaust()
        with context.advisory_scope(self.deadline):
            response = self.ok({'op': 'deliver', 'op_id': 'deadline-delivery', 'assignment': prepared['assignment'],
                                'attempt': 1, 'outcome': 'done', 'commits': [sha]})
        self.assertEqual(response['outcome'], 'done')
        self.assertIsNotNone(load(self.repo, self.cid)['assignments'][-1].get('delivery'))
        self.assertEqual(len(self.provider_calls), before)


class GroupingDeadlineTests(NewBase):
    def test_final_currentness_expiry_returns_unavailable_without_partial_maps(self):
        self.streams()
        self.enter_review(answered('floor-only'))
        self.default = lambda state, question: answered(
            'agent-assessment' if 'agent-assessment' in question.options else
            'stream:a' if any(route.startswith('stream:') for route in question.options) else 'independent')
        report = {'verdict': 'approve', 'blocking': [], 'advisory': ['remaining optional finding'], 'cosmetic': []}
        self.assertEqual(self.record_review(self.receipt_id, report)[0], 0)
        baseline = classify.finding_groups(self.repo, self.cid)
        self.assertTrue(baseline['owners'] and baseline['shared_causes'])
        before = self.record_path().read_bytes(), len(self.provider_calls)
        clock = [0.0]
        deadline = decisions.Deadline(seconds=1, clock=lambda: clock[0])
        real = classify.current_input
        seen = []
        def validate(*args, **kwargs):
            if args[2].kind == 'review-finding-grouping':
                seen.append(args[2].subject)
                if len(seen) == 2:
                    clock[0] = 2.0
                    context.checkpoint()
            return real(*args, **kwargs)
        with context.advisory_scope(deadline), mock.patch.object(classify, 'current_input', validate):
            result = classify.finding_groups(self.repo, self.cid)
        self.assertEqual((result['owners'], result['shared_causes']), ({}, {}))
        self.assertEqual(result['classification_unavailable'], 'deadline-exhausted')
        self.assertEqual((self.record_path().read_bytes(), len(self.provider_calls)), before)


class RelatedDeadlineTests(unittest.TestCase):
    def test_optional_reader_aborts_without_partial_result_and_default_stays_complete(self):
        import tempfile
        path = Path(classify.__file__).parent / 'related-tests.py'
        spec = importlib.util.spec_from_file_location('_deadline_related_tests', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tests = root / 'crux/scripts/tests'
            tests.mkdir(parents=True)
            (tests / 'test_first.py').write_text('import source_module\n')
            (tests / 'test_second.py').write_text('import source_module\n')
            complete = module.related(root, ['crux/scripts/source_module.py'])
            self.assertEqual(len(complete['tests']), 2)
            calls = []
            def checkpoint():
                calls.append(None)
                if len(calls) > 3:
                    raise TimeoutError('fixture exhausted')
            with self.assertRaisesRegex(TimeoutError, 'fixture exhausted'):
                module.extra_candidates(root, ['crux/scripts/source_module.py'], checkpoint=checkpoint)
            self.assertEqual(module.related(root, ['crux/scripts/source_module.py']), complete)


if __name__ == '__main__':
    unittest.main()
