"""Focused ranking adds observed inspect suggestions and preserves deterministic checks."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
from _classify_support import ClassifyBase, QuestionReply, answered, failed
from cycle_workflow import event, load, locked, save, tree
from crux import decisions
import cycle_classify as classify
import cycle_context


class FocusedTests(ClassifyBase):
    gate = 'crux/scripts/generate-micro-crux.py'
    source = 'crux/scripts/cycle_workflow.py'

    def edit(self, function):
        with locked(self.repo) as (cfg, _):
            doc = load(self.repo, self.cid)
            function(doc)
            event(doc, 'focused-fixture')
            save(cfg, doc)

    def setUp(self):
        super().setUp()
        files = {
            self.source: 'answer = 1\n',
            self.gate: "SOURCE = 'crux/scripts/cycle_workflow.py'\nraise RuntimeError('enumeration must not execute me')\n",
            'crux/scripts/tests/test_required.py': "SOURCE = 'crux/scripts/cycle_workflow.py'\n",
            'crux/scripts/tests/test_micro_reader.py': "SOURCE = 'crux/scripts/generate-micro-crux.py'\n",
            'crux/skills/check-drift/SKILL.md': '| Gate (output) | Scope | Command |\n| --- | --- | --- |\n| micro | plugin | generate-micro-crux.py --dry-run |\n',
        }
        for name, text in files.items():
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        self.git('add', 'crux')
        self.git('commit', '-q', '-m', 'focused baseline')
        self.edit(lambda doc: (doc['plan'].update(scope=['crux/scripts']), doc.update(build_checks=['literal-required'], required_checks=['unit'])))
        (self.repo / self.source).write_text('answer = 2\n')
        choices = cycle_context.focused_candidates(tree(self.repo), load(self.repo, self.cid))
        self.default = {f'candidate-{index}': answered('include' if item['path'] == self.gate else 'omit') for index, item in enumerate(choices)}

    def candidate_reader(self):
        path = Path(classify.__file__).parent / 'related-tests.py'
        spec = importlib.util.spec_from_file_location('_focused_fixture_related', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_actual_bs1_reader_gate_is_ranked_and_added_to_inspect(self):
        related = self.candidate_reader()
        literal = related.related(self.repo, [self.source])
        before = load(self.repo, self.cid)
        self.auto_hook_replies['focused-test-ranking'] = self.default
        self.git('add', self.source)
        self.git('commit', '-q', '-m', 'track the focused source fixture')
        self.prepare()
        result = self.inspect()
        self.assertIn('drift:' + self.gate, [item['id'] for item in result['focused_suggestions']])
        self.assertEqual(related.related(self.repo, [self.source]), literal)
        after = load(self.repo, self.cid)
        self.assertEqual((after['build_checks'], after['required_checks']), (before['build_checks'], before['required_checks']))
        before_bytes = self.record_path().read_bytes()
        count = len(self.provider_calls)
        self.inspect()
        self.assertEqual((self.record_path().read_bytes(), len(self.provider_calls)), (before_bytes, count), 'inspect must remain read-only')

    def test_no_stored_selection_avoids_candidate_discovery_during_inspect(self):
        with mock.patch.object(cycle_context, 'focused_candidates', side_effect=AssertionError('unneeded candidate scan')):
            self.assertEqual(classify.focused_suggestions(tree(self.repo), load(self.repo, self.cid)), [])

    def test_working_tree_source_changes_invalidate_ranking_even_with_same_path(self):
        self.assertIn(self.source, cycle_context.focused_facts(tree(self.repo), load(self.repo, self.cid))['paths'])
        result = classify.focused_tests(self.repo, self.cid)
        self.assertIn('drift:' + self.gate, [item['id'] for item in result['suggested_checks']])
        before = len(self.asked)
        (self.repo / self.source).write_text('answer = 3\n')
        self.assertEqual(classify.focused_suggestions(tree(self.repo), load(self.repo, self.cid)), [])
        classify.focused_tests(self.repo, self.cid)
        self.assertGreater(len(self.asked), before)

    def test_large_candidate_sets_are_bounded_and_keep_count_is_configured(self):
        candidates = [{'id': f'test:checks/test_{index}.py', 'path': f'checks/test_{index}.py', 'reason': 'source reader metadata ' * 20} for index in range(130)]
        self.default = answered('include')
        basis = decisions.classifier_basis()
        with mock.patch.object(cycle_context, 'focused_candidates', lambda *args: candidates), mock.patch.object(decisions, 'classifier_basis', lambda: {**basis, 'focused_test_keep': 2}):
            result = classify.focused_tests(self.repo, self.cid)
        self.assertEqual(len(result['suggested_checks']), 2)
        self.assertEqual(len(self.asked), 130)
        for call in self.asked:
            self.assertLessEqual(len(json.dumps(call['state'], ensure_ascii=False, sort_keys=True)), decisions.input_bound(('focused-test-ranking',)))
        self.assertTrue(any('clipped' in item for call in self.asked for item in call['state']['candidates']))

    def test_failures_optout_and_wrong_answers_keep_the_deterministic_checks(self):
        baseline = load(self.repo, self.cid)
        for index, status in enumerate(decisions.FALLBACKS):
            with self.subTest(status=status):
                (self.repo / self.source).write_text(f'answer = {index + 10}\n')
                self.default = failed(status)
                result = classify.focused_tests(self.repo, self.cid)
                self.assertEqual(result['suggested_checks'], [])
                self.assertTrue(all(item['fallback'] == status for item in result['classifications']))
        (self.repo / self.source).write_text('answer = 999\n')
        self.default = answered('remove-required')
        result = classify.focused_tests(self.repo, self.cid)
        self.assertEqual(result['suggested_checks'], [])
        self.assertTrue(all(item['fallback'] == 'route-not-permitted' for item in result['classifications']))
        before = len(self.provider_calls)
        (self.repo / '.bionic.yml').write_text("config_version: '1'\ndocs_dir: bionic\ndecisions:\n  classifier: 'off'\n")
        self.assertEqual(classify.focused_tests(self.repo, self.cid)['suggested_checks'], [])
        self.assertEqual(len(self.provider_calls), before)
        after = load(self.repo, self.cid)
        self.assertEqual((after['build_checks'], after['required_checks']), (baseline['build_checks'], baseline['required_checks']))

    def test_concurrent_source_mutation_cannot_install_a_stale_suggestion(self):
        count = len(cycle_context.focused_candidates(tree(self.repo), load(self.repo, self.cid)))
        self.hook = lambda number: (self.repo / self.source).write_text(f'answer = {number + 10}\n') if number in (1, count + 1) else None
        self.default = answered('include')
        result = classify.focused_tests(self.repo, self.cid)
        self.assertEqual(result['suggested_checks'], [])
        self.assertTrue(all(item['fallback'] == 'stale' for item in result['classifications']))
        self.assertEqual(len(self.asked), count * 2)

    def test_bookkeeping_reuses_the_ranking_without_another_provider_call(self):
        classify.focused_tests(self.repo, self.cid)
        before = len(self.provider_calls)
        self.edit(lambda doc: None)
        result = classify.focused_tests(self.repo, self.cid)
        self.assertEqual(len(self.provider_calls), before)
        self.assertTrue(result['suggested_checks'])
        self.assertTrue(all(item.get('reused_from') for item in result['classifications']))

    def test_delivery_refreshes_suggestions_after_the_implementation_changes(self):
        self.auto_hook_replies['focused-test-ranking'] = answered('omit')
        self.git('add', self.source)
        self.git('commit', '-q', '-m', 'track the focused source fixture')
        prepared = self.prepare()
        self.assertEqual(self.inspect()['focused_suggestions'], [])
        self.ok({'op': 'execution-check', 'op_id': 'focused-clean-start',
                 'assignment': prepared['assignment'], 'attempt': prepared['attempt']})
        (self.repo / self.source).write_text('answer = 3\n')
        self.git('add', self.source)
        self.ok({'op': 'execution-check', 'op_id': 'focused-source-stage',
                 'assignment': prepared['assignment'], 'attempt': prepared['attempt'],
                 'edited_paths': [self.source]})
        self.git('commit', '-q', '-m', 'change the micro reader\n\nCycle-Task: build-it')
        sha = self.git('rev-parse', 'HEAD')
        self.write_result(prepared)
        self.auto_hook_replies['focused-test-ranking'] = QuestionReply(
            lambda state, qid, question: answered('include' if next(item for item in state['candidates'] if item['id'] == qid)['path'] == self.gate else 'omit'))
        response = self.ok({'op': 'deliver', 'op_id': 'deliver-focused', 'assignment': prepared['assignment'], 'attempt': 1, 'outcome': 'done', 'commits': [sha]})
        result = self.inspect()
        self.assertIn('drift:' + self.gate, [item['id'] for item in result['focused_suggestions']],
                      json.dumps({'response': response, 'rankings': self.entries('focused-test-ranking')}))


if __name__ == '__main__':
    unittest.main()
