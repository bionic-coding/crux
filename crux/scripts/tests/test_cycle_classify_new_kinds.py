"""New classifiers remove dispatch, preload, handoff-reading and finding-owner rounds.

Every model answer is scripted. Code must retain roles, references, budgets and
each blocking finding even when an answer recommends something else.
"""
from pathlib import Path
import json
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cycle_classify as classify
import cycle_context
from crux import decisions
from cycle_workflow import event, load, locked, mutate, save
from _classify_support import BLOCKING, ClassifyBase, answered, failed


class NewBase(ClassifyBase):
    def edit(self, function):
        with locked(self.repo) as (cfg, _):
            doc = load(self.repo, self.cid)
            function(doc)
            event(doc, 'new-kind-fixture')
            save(cfg, doc)

    def streams(self):
        self.edit(lambda doc: doc['plan'].update(streams=[
            {'id': 'a', 'paths': ['src/a.py'], 'independent': True},
            {'id': 'b', 'paths': ['src/b.py'], 'independent': True}]))


class ArrangementTests(NewBase):
    """Build and fix tasks select the dev-lead, so no role question exists (IDR dev-lead-owned-build
    approach 1). CYC-0127 removed the dormant execution-arrangement kind."""

    def test_bounded_build_selects_the_dev_lead_without_a_question(self):
        result = classify.arrangement(self.repo, self.cid, 'build-it')
        self.assertEqual(result['role'], 'dev-lead')
        self.assertEqual(result['permitted_roles'], ['dev-lead'])
        self.assertEqual(self.asked, [])

    def test_independent_streams_select_the_dev_lead_and_ask_nothing(self):
        self.streams()
        self.default = answered('developer')
        result = classify.arrangement(self.repo, self.cid, 'build-it')
        self.assertEqual((result['role'], result['permitted_roles']), ('dev-lead', ['dev-lead']))
        self.assertEqual(self.asked, [])

    def test_explicit_developer_role_stays_accepted_without_a_question(self):
        self.streams()
        result = classify.arrangement(self.repo, self.cid, 'build-it', role='developer')
        self.assertEqual((result['role'], result['explicit'], self.asked), ('developer', True, []))

    def test_a_fix_task_selects_the_dev_lead_in_every_fix_phase(self):
        doc = load(self.repo, self.cid)
        for phase in ('verify', 'test', 'review'):
            with self.subTest(phase=phase):
                task = {'id': 'fix-1', 'phase': phase, 'fix': {'finding': 'r1:blocking:0', 'eligibility': 'small'}}
                self.assertEqual(cycle_context.permitted_roles(doc, task), ['dev-lead'])
        self.assertEqual(cycle_context.permitted_roles(doc, {'id': 'r', 'phase': 'review'}), ['reviewer'])

    def test_the_removed_kind_has_no_question_set_and_a_refresh_naming_it_is_refused(self):
        import cycle_questions
        self.assertNotIn('execution-arrangement', classify.KINDS)
        self.assertNotIn('execution-arrangement', cycle_questions.QUESTION_SETS)
        cfg = classify.tree(self.repo)
        self.assertIsNone(classify.plan_of(cfg, load(self.repo, self.cid), classify.Job('execution-arrangement', 'build-it'), self.repo))
        refused = self.op({'op': 'advice-refresh', 'op_id': 'refresh-removed-kind', 'task_id': 'build-it',
                           'kinds': ['execution-arrangement']})
        self.assertEqual(refused[0], 1, refused)
        self.assertEqual(refused[1]['errors'][0]['code'], 'invalid-request')
        # Positive control: the same request naming a remaining kind passes the schema.
        import cycle_ops
        self.assertEqual(cycle_ops.schema_errors({'op': 'advice-refresh', 'op_id': 'refresh-remaining-kind',
                                                  'task_id': 'build-it', 'kinds': ['context-selection']}), [])


class ContextTests(NewBase):
    CANDIDATES = [{'id': 'cycle', 'description': 'The cycle skill.'}, {'id': 'council', 'description': 'Council review.'}]

    def test_only_selected_canonical_bodies_replace_the_ten_skill_preload(self):
        # Answers are keyed by question id rather than thread order.
        self.default = {'build-it:skill-0': answered('include'), 'build-it:skill-1': answered('omit')}
        with mock.patch.object(cycle_context, 'candidates', lambda *args: self.CANDIDATES):
            result = classify.context_bundles(self.repo, self.cid, 'build-it', 'architect')
        self.assertEqual([item['id'] for item in result['selected']], ['cycle'])
        selected = result['selected'][0]
        self.assertEqual(selected['body'], (Path(selected['directory']) / 'SKILL.md').read_text())
        self.assertEqual(result['retrievable'], ['council'])

    def test_refusal_keeps_no_optional_body_and_retains_retrieval(self):
        self.default = failed('refusal')
        with mock.patch.object(cycle_context, 'candidates', lambda *args: self.CANDIDATES):
            result = classify.context_bundles(self.repo, self.cid, 'build-it', 'architect')
        self.assertEqual(result['selected'], [])
        self.assertEqual(result['retrievable'], ['cycle', 'council'])

    def test_skill_resolution_cannot_escape_the_plugin(self):
        for ident in ('../private', '/etc/passwd', 'cycle/../../private'):
            with self.subTest(ident=ident), self.assertRaises(ValueError):
                cycle_context.skill_bundle(ident)

    def test_changed_candidate_order_reasks_and_resolves_the_current_body(self):
        choices = list(self.CANDIDATES)
        self.default = {'build-it:skill-0': answered('include'), 'build-it:skill-1': answered('omit')}
        self.hook = lambda count: choices.reverse() if count == 1 else None
        with mock.patch.object(cycle_context, 'candidates', lambda *args: list(choices)):
            result = classify.context_bundles(self.repo, self.cid, 'build-it', 'architect')
        self.assertEqual([item['id'] for item in result['selected']], ['council'])
        self.assertGreater(len(self.asked), 2, 'changed inputs were not reasked')

    def test_clipped_text_is_marked_and_every_failure_selects_no_optional_body(self):
        with mock.patch.object(cycle_context, 'candidates', lambda *args: self.CANDIDATES):
            for status in decisions.FALLBACKS:
                with self.subTest(status=status):
                    self.edit(lambda doc: doc['plan']['tasks'][0].update(description='x' * 400 + status))
                    self.default = failed(status)
                    result = classify.context_bundles(self.repo, self.cid, 'build-it', 'architect')
                    self.assertEqual(result['selected'], [])
                    self.assertTrue(self.asked[-1]['state']['clipped']['task.description']['clipped'])

    def test_recorded_task_ids_cannot_break_wire_ids_or_reuse(self):
        ident = 'task#' + 'x' * 150
        self.edit(lambda doc: doc['plan']['tasks'][0].update(id=ident))
        self.default = answered('include')
        with mock.patch.object(cycle_context, 'candidates', lambda *args: self.CANDIDATES):
            result = classify.context_bundles(self.repo, self.cid, ident, 'architect')
            self.assertEqual(len(result['selected']), 2)
            before = len(self.asked)
            self.edit(lambda doc: None)
            result = classify.context_bundles(self.repo, self.cid, ident, 'architect')
            self.assertEqual(len(result['selected']), 2)
            self.assertEqual(len(self.asked), before)
        self.assertTrue(all(len(item['id']) <= 128 and '#' not in item['id'] for item in self.asked))


class HandoffTests(NewBase):
    def delivered(self, report, evidence=('passing check', 'unsupported claim', 'unresolved work', 'missing item')):
        self.edit(lambda doc: doc['plan']['tasks'][0].update(expected_evidence=list(evidence)))
        prepared = self.prepare()
        sha = self.work(prepared)
        path = Path(prepared['result_path'])
        lines = path.read_text().rstrip().splitlines()
        path.write_text('\n'.join([*lines[:3], report, lines[-1]]) + '\n')
        # This unit asks directly after the retained-delivery hook's scripted failure.
        # The enabled engine hook still runs; a later bookkeeping revision permits
        # retry of its unavailable answer without reusing a fixture default answer.
        self.auto_hook_replies['handoff-completeness'] = failed('unavailable')
        previous = self.default
        self.default = answered('agent-assessment')
        self.ok({'op': 'deliver', 'op_id': 'deliver-new-kind', 'assignment': prepared['assignment'], 'attempt': 1,
                 'outcome': 'done', 'commits': [sha]})
        self.default = previous
        self.edit(lambda doc: None)
        return prepared

    def test_answered_unsupported_unresolved_absent_keep_distinct_outcomes(self):
        prepared = self.delivered('## Evidence\nPassing check: path:src/a.py:1\n## Remaining\nUnresolved work remains.')
        prefix = prepared['assignment'] + '/1/evidence-'
        self.default = {prefix + '0': answered('answered:ref-0'), prefix + '1': answered('unsupported'),
                        prefix + '2': answered('unresolved'), prefix + '3': answered('absent')}
        result = classify.handoff(self.repo, self.cid, 'build-it', prepared['assignment'], 1)
        self.assertEqual([item['status'] for item in result['items']], ['answered', 'unsupported', 'unresolved', 'absent'])
        self.assertEqual(result['omissions'], [prefix + '1', prefix + '3'])
        self.assertEqual(result['unresolved'], [prefix + '2'])

    def test_missing_reference_overrides_an_answered_claim(self):
        prepared = self.delivered('## Evidence\nPassing check: path:src/missing.py:1', evidence=('passing check',))
        self.default = answered('answered:ref-0')
        result = classify.handoff(self.repo, self.cid, 'build-it', prepared['assignment'], 1)
        self.assertEqual(result['items'][0]['status'], 'unsupported')
        self.assertTrue(result['reference_failures'])
        self.assertEqual(result['route'], 'missing-evidence-request')

    def test_current_path_and_commit_are_valid_but_missing_receipt_is_not(self):
        from cycle_workflow import tree
        cfg = tree(self.repo)
        self.assertTrue(cycle_context.resolve_reference(cfg, {'kind': 'path', 'value': 'src/a.py:1'}, {})['valid'])
        self.assertFalse(cycle_context.resolve_reference(cfg, {'kind': 'path', 'value': 'src/a.py:99'}, {})['valid'])
        self.assertTrue(cycle_context.resolve_reference(cfg, {'kind': 'commit', 'value': self.base}, {})['valid'])
        self.assertFalse(cycle_context.resolve_reference(cfg, {'kind': 'receipt', 'value': 'TE-' + '0' * 32}, {})['valid'])

    def test_receipt_must_be_current_and_passing(self):
        from cycle_workflow import tree
        receipt = self.receipt({'check_id': 'handoff-check', 'command': [sys.executable, '-c', 'pass'], 'inputs': ['src'], 'environment': []})
        cfg = tree(self.repo)
        reference = {'kind': 'receipt', 'value': receipt}
        self.assertTrue(cycle_context.resolve_reference(cfg, reference, {})['valid'])
        (self.repo / 'src/a.py').write_text('changed input\n')
        self.assertFalse(cycle_context.resolve_reference(cfg, reference, {})['valid'])

    def test_every_failure_remains_unresolved_and_clipping_is_explicit(self):
        prepared = self.delivered('## Evidence\n' + 'x' * 9000 + '\npath:src/a.py:1', evidence=('check',))
        for status in decisions.FALLBACKS:
            with self.subTest(status=status):
                self.edit(lambda doc: doc['plan']['tasks'][0].update(expected_evidence=['check ' + status]))
                self.default = failed(status)
                result = classify.handoff(self.repo, self.cid, 'build-it', prepared['assignment'], 1)
                self.assertEqual(result['items'][0]['status'], 'unresolved')
                self.assertEqual(result['route'], 'agent-assessment')
                self.assertTrue(self.asked[-1]['state']['clipped']['sections[0].text']['clipped'])

    def test_an_answered_path_cannot_survive_reference_mutation(self):
        prepared = self.delivered('path:src/a.py:1', evidence=('check',))
        self.default = answered('answered:ref-0')
        result = classify.handoff(self.repo, self.cid, 'build-it', prepared['assignment'], 1)
        self.assertEqual(result['route'], None)
        (self.repo / 'src/a.py').unlink()
        from cycle_workflow import tree
        result = classify.handoff_result(tree(self.repo), load(self.repo, self.cid), prepared['assignment'], 1)
        self.assertEqual(result['items'][0]['status'], 'unsupported')
        self.assertTrue(result['reference_failures'])


class ReportFailureTests(NewBase):
    def failed_report(self, report):
        prepared = self.prepare()
        self.write_result(prepared)
        path = Path(prepared['result_path'])
        lines = path.read_text().rstrip().splitlines()
        path.write_text('\n'.join([*lines[:-1], report, lines[-1]]) + '\n')
        self.default = answered('agent-assessment')
        self.ok({'op': 'deliver', 'op_id': 'deliver-failure', 'assignment': prepared['assignment'], 'attempt': 1, 'outcome': 'failed'})
        return prepared

    def test_only_report_pattern_prerequisites_offer_specialized_handlers(self):
        self.failed_report('revision mismatch. invalid-json. ModuleNotFoundError: dependency. ' + 'x' * 9000)
        options = self.asked[-1]['question'].options
        for route in ('stale-state-refresh', 'request-repair', 'environment-investigation', 'owning-developer', 'agent-assessment'):
            self.assertIn(route, options)
        self.assertNotIn('acceptance-fix', options)
        self.assertNotIn('return', options, 'Build cannot return')
        self.assertTrue(self.asked[-1]['state']['clipped']['report']['clipped'])

    def test_a_wrong_acceptance_fix_cannot_create_an_allowance(self):
        prepared = self.failed_report('ordinary failure')
        self.edit(lambda doc: doc['plan']['tasks'][0].update(description='changed input'))
        self.default = answered('acceptance-fix')
        found = classify.failed_delivery(self.repo, self.cid, 'build-it', prepared['assignment'], 1)
        self.assertEqual(found['classifications'][0]['fallback'], 'route-not-permitted')
        self.assertNotIn('acceptance-fix', self.asked[-1]['question'].options)

    def test_an_unrelated_json_citation_does_not_abort_failure_routing(self):
        path = self.repo / 'bionic/unrelated.json'
        path.write_text('{}\n')
        self.git('add', '-f', 'bionic/unrelated.json')
        self.git('commit', '-q', '-m', 'retain ordinary JSON')
        self.failed_report('ModuleNotFoundError: dependency. path:bionic/unrelated.json')
        entry = self.entries('failure-routing')[-1]
        self.assertEqual((entry['route'], entry['fallback']), ('agent-assessment', None))
        self.assertIn('environment-investigation', self.asked[-1]['question'].options)
        self.assertNotIn('acceptance-fix', self.asked[-1]['question'].options)

    def test_superseded_delivery_trigger_cannot_read_a_new_attempt_report(self):
        prepared = self.failed_report('first report')
        second = self.prepare('prep-second', assignment=prepared['assignment'])
        self.assertEqual(second['attempt'], 2)
        self.write_result(second)
        self.ok({'op': 'deliver', 'op_id': 'deliver-second', 'assignment': second['assignment'], 'attempt': 2, 'outcome': 'failed'})
        before = len(self.asked)
        result = classify.failed_delivery(self.repo, self.cid, 'build-it', prepared['assignment'], 1)
        self.assertEqual(result['classifications'], [])
        self.assertEqual(len(self.asked), before)
        result = classify.failed_delivery(self.repo, self.cid, 'wrong-task', second['assignment'], 2)
        self.assertEqual(result['classifications'], [])

    def test_handoff_and_failure_share_the_callers_deadline(self):
        prepared = self.failed_report('first report')
        deadline = decisions.Deadline()
        self.edit(lambda doc: doc['plan']['tasks'][0].update(description='fresh report input'))
        before = len(self.asked)
        classify.handoff(self.repo, self.cid, 'build-it', prepared['assignment'], 1, decisions_deadline=deadline)
        classify.failed_delivery(self.repo, self.cid, 'build-it', prepared['assignment'], 1, decisions_deadline=deadline)
        self.assertTrue(self.asked[before:])
        self.assertTrue(all(item['deadline'] is deadline for item in self.asked[before:]))

    def test_acceptance_fix_needs_a_committed_failed_observation_and_available_slot(self):
        self.to_test()
        self.edit(lambda doc: doc['plan']['tasks'].append({'id': 'verify-it', 'phase': 'verify', 'description': 'verify criterion',
                                                        'depends_on': [], 'status': 'pending', 'expected_evidence': ['measurement']}))
        path = self.repo / 'bionic/failed-observation.json'
        path.write_text(json.dumps({'criterion': 0, 'value': 'failure observed', 'met': False, 'commit': self.git('rev-parse', 'HEAD')}))
        self.git('add', '-f', 'bionic/failed-observation.json')
        self.git('commit', '-q', '-m', 'retain failed observation')
        prepared = self.ok({'op': 'prepare-dispatch', 'op_id': 'prep-verify', 'task_id': 'verify-it', 'role': 'dev-lead', 'host': 'claude-code'})
        self.write_result(prepared)
        report = Path(prepared['result_path'])
        lines = report.read_text().rstrip().splitlines()
        report.write_text('\n'.join([*lines[:-1], 'path:bionic/failed-observation.json', lines[-1]]) + '\n')
        self.default = answered('acceptance-fix')
        result = self.ok({'op': 'deliver', 'op_id': 'deliver-verify', 'assignment': prepared['assignment'], 'attempt': 1, 'outcome': 'failed'})
        self.assertEqual(next(item for item in result['classifications'] if item['kind'] == 'failure-routing')['route'], 'acceptance-fix')
        self.assertEqual(self.asked[-1]['state']['failed_criteria'], [{'index': 0, 'observation': 'failed-observation.json'}])
        path.write_text(path.read_text().replace('false', 'true'))
        result = classify.failed_delivery(self.repo, self.cid, 'verify-it', prepared['assignment'], 1)
        self.assertEqual(result['classifications'][0]['fallback'], 'route-not-permitted')


class FindingGroupingTests(NewBase):
    def test_a_new_review_retires_old_grouping_hypotheses(self):
        self.streams()
        self.enter_review(answered('floor-only'))
        self.default = lambda state, question: answered('agent-assessment' if 'agent-assessment' in question.options else
                                                      'stream:a' if any(route.startswith('stream:') for route in question.options) else 'independent')
        report = {'verdict': 'approve', 'blocking': [], 'advisory': ['remaining optional finding'], 'cosmetic': []}
        self.assertEqual(self.record_review(self.receipt_id, report)[0], 0)
        self.assertEqual(set(classify.finding_groups(self.repo, self.cid)['owners']), {'r1:advisory:0'})
        self.assertEqual(self.record_review(self.receipt_id, report)[0], 0)
        result = classify.finding_groups(self.repo, self.cid)
        self.assertEqual(set(result['owners']), {'r2:advisory:0'})
        self.assertEqual(set(result['shared_causes']), {'r2:advisory:0'})

    def test_shared_cause_can_name_another_batch_without_erasing_blocking_ids(self):
        self.streams()
        self.enter_review(answered('floor-only'))
        report = {'verdict': 'changes-required', 'blocking': [{**BLOCKING, 'path': f'src/f{i}.py', 'title': 'x' * 140} for i in range(10)],
                  'advisory': [], 'cosmetic': []}
        self.default = lambda state, question: answered('return' if 'return' in question.options else
                                                      'stream:a' if any(route.startswith('stream:') for route in question.options)
                                                      else 'finding:r1:blocking:9' if 'finding:r1:blocking:9' in question.options else 'independent')
        with mock.patch.object(decisions, 'MAX_QUESTIONS_PER_REQUEST', 3):
            self.record_review(self.receipt_id, report)
        result = classify.finding_groups(self.repo, self.cid)
        self.assertEqual(result['owners']['r1:blocking:0'], 'a')
        self.assertEqual(result['shared_causes']['r1:blocking:0'], 'finding:r1:blocking:9')
        grouped = [item for item in self.asked if 'questions' in item['state']]
        self.assertTrue(any(item['state']['clipped']['findings[0].title']['clipped'] for item in grouped))
        ids = [f'r1:blocking:{index}' for index in range(10)]
        group = classify.repair_group(self.repo, self.cid, ids)
        self.assertTrue(group['eligible'])
        self.assertEqual(group['findings'], ids)
        self.assertFalse(classify.repair_group(self.repo, self.cid, [ids[0], ids[0]])['eligible'])
        mutate(self.repo, self.cid, 'task-add', task={
            'id': 'repair-all', 'phase': 'review', 'description': 'repair the shared implementation cause',
            'depends_on': [], 'status': 'pending', 'expected_evidence': ['evidence for every blocking finding'],
            'fix': {'finding': 'shared implementation cause', 'eligibility': 'small shared implementation repair', 'findings': ids}})
        actual = next(task for task in load(self.repo, self.cid)['plan']['tasks'] if task['id'] == 'repair-all')['fix']['findings']
        self.assertEqual(actual, ids, 'the normal writer must retain every blocking ID in the materialized fix')

    def test_grouping_failures_preserve_all_findings_for_the_agent(self):
        self.streams()
        self.enter_review(answered('floor-only'))
        self.default = answered('return')
        self.record_review(self.receipt_id, {'verdict': 'changes-required', 'blocking': [BLOCKING], 'advisory': [], 'cosmetic': []})
        for status in decisions.FALLBACKS:
            with self.subTest(status=status):
                self.edit(lambda doc: doc['plan']['streams'][0].update(paths=['src/a-' + str(len(self.asked)) + '.py']))
                self.default = failed(status)
                result = classify.finding_groups(self.repo, self.cid)
                self.assertEqual((result['owners'], result['shared_causes']), ({}, {}))
                self.assertTrue(classify.repair_group(self.repo, self.cid, ['r1:blocking:0'])['eligible'])


if __name__ == '__main__':
    unittest.main()
