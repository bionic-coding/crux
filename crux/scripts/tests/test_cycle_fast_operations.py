"""Routine control operations never wait for optional provider advice."""
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle_classify
import cycle_context
from crux import decisions
from cycle_workflow import load, mutate
from test_cycle_ops_hooks import HookBase
from test_cycle_ops_advance import PASSING, REVIEW
from test_evidence import execute


class FastOperationTests(HookBase):
    provider_helpers = False
    def test_ordinary_advance_review_and_finish_make_zero_provider_requests(self):
        _, _, _ = self.complete()
        def advance(ident):
            return self.ok({'op': 'advance', 'op_id': ident,
                'expect_revision': load(self.repo, self.cid)['revision']})
        self.assertEqual(advance('fast-build-advance')['phase'], 'verify')
        mutate(self.repo, self.cid, 'checks', checks=['unit'])
        mutate(self.repo, self.cid, 'coverage', coverage={'affected': ['answer'],
            'checks': [{'check_id': 'unit', 'rationale': 'reads changed source'}], 'not_selected': 'none'})
        receipt = execute(self.repo, PASSING)['evidence']['id']
        self.assertEqual(advance('fast-review-boundary')['phase'], 'review')
        mutate(self.repo, self.cid, 'review', report={**REVIEW, 'evidence': [receipt]})
        self.assertEqual(advance('fast-reflect-boundary')['phase'], 'reflect')
        self.ok({'op': 'finish', 'op_id': 'fast-final-finish',
            'expect_revision': load(self.repo, self.cid)['revision'], 'lessons': ['Measured'], 'remaining': ['none']})
        self.assertEqual(self.calls, [])

    def test_dispatch_delivery_and_inspect_make_zero_provider_requests(self):
        prepared = self.dispatch(role='developer')
        sha = self.work(prepared)
        self.ok({'op': 'deliver', 'op_id': 'fast-delivery-1',
                 'assignment': prepared['assignment'], 'attempt': prepared['attempt'],
                 'outcome': 'done', 'commits': [sha]})
        self.ok({'op': 'inspect'})
        self.assertEqual(self.calls, [])

    def test_optional_refresh_is_explicit_and_does_not_gate_dispatch(self):
        refreshed = self.ok({'op': 'advice-refresh', 'op_id': 'fast-refresh-1',
                             'kinds': ['context-selection'], 'task_id': 'build-it', 'role': 'developer'})
        self.assertTrue(self.calls)
        self.assertTrue(refreshed.get('classifications'))
        count = len(self.calls)
        self.dispatch(role='developer')
        self.assertEqual(len(self.calls), count)
        self.assertEqual(len(self.calls[0]['questions']), 2)
        self.assertLessEqual(self.calls[0]['deadline'].seconds, 5.0)

    def test_critical_paths_do_not_build_optional_handoff_or_test_facts(self):
        with patch.object(cycle_context, 'handoff_data', side_effect=AssertionError('optional handoff I/O')), \
                patch.object(cycle_context, 'focused_candidates', side_effect=AssertionError('optional test scan')):
            prepared = self.dispatch(role='developer')
            sha = self.work(prepared)
            self.ok({'op': 'deliver', 'op_id': 'fast-no-local-advice', 'assignment': prepared['assignment'],
                     'attempt': 1, 'outcome': 'done', 'commits': [sha]})
            self.ok({'op': 'inspect'})
        self.assertEqual(self.calls, [])

    def test_context_refresh_needs_an_explicit_configured_role_not_a_permitted_one(self):
        # Build permits only the dev-lead, yet a developer child's context stays retrievable
        # (IDR dev-lead-owned-build approach 1); an omitted or unconfigured role still refuses.
        for op_id, role in (('fast-refresh-none', None), ('fast-refresh-ghost', 'ghost')):
            with self.subTest(role=role):
                request = {'op': 'advice-refresh', 'op_id': op_id, 'kinds': ['context-selection'], 'task_id': 'build-it'}
                if role:
                    request['role'] = role
                self.refused(request, 'role-selection-required')
        self.assertEqual(self.calls, [])
        self.ok({'op': 'advice-refresh', 'op_id': 'fast-refresh-reviewer', 'kinds': ['context-selection'],
                 'task_id': 'build-it', 'role': 'reviewer'})

    def test_explicit_refresh_replay_asks_nothing(self):
        request = {'op': 'advice-refresh', 'op_id': 'fast-refresh-replay',
                   'kinds': ['context-selection'], 'task_id': 'build-it', 'role': 'developer'}
        self.ok(request)
        count = len(self.calls)
        self.assertTrue(self.ok(request)['replayed'])
        self.assertEqual(len(self.calls), count)

    def test_cancelled_refresh_journals_same_id_before_returning(self):
        request = {'op': 'advice-refresh', 'op_id': 'fast-refresh-cancel-same-id',
                   'kinds': ['context-selection'], 'task_id': 'build-it', 'role': 'developer'}
        with patch.object(decisions, 'ask_many', side_effect=KeyboardInterrupt) as ask:
            first = self.ok(request)
            replay = self.ok(request)
        self.assertEqual(first['classification_unavailable'], 'cancelled')
        self.assertTrue(replay['replayed'])
        self.assertEqual(replay['classification_unavailable'], 'cancelled')
        self.assertEqual(ask.call_count, 1)
        self.assertEqual(sum(op['op_id'] == request['op_id'] for op in load(self.repo, self.cid)['operations']), 1)
        self.refused({**request, 'kinds': ['focused-test-ranking']}, 'op-id-reused')

    def test_early_exhausted_refresh_journals_same_id_without_transport(self):
        request = {'op': 'advice-refresh', 'op_id': 'fast-refresh-early-exhausted',
                   'kinds': ['context-selection'], 'task_id': 'build-it', 'role': 'developer'}
        with patch.object(cycle_context, 'candidates', side_effect=cycle_context.AdvisoryUnavailable) as candidates:
            first = self.ok(request)
            replay = self.ok(request)
        self.assertEqual(first['classification_unavailable'], 'deadline-exhausted')
        self.assertTrue(replay['replayed'])
        self.assertEqual(replay['classification_unavailable'], 'deadline-exhausted')
        self.assertEqual(candidates.call_count, 1)
        self.assertEqual(self.calls, [])

    def test_public_refresh_preserves_denial_and_opt_out_guards(self):
        request = {'op': 'advice-refresh', 'op_id': 'fast-denial-refresh',
            'kinds': ['context-selection'], 'task_id': 'build-it', 'role': 'developer'}
        with patch.object(decisions, 'REQUIRED_DENIALS', {'data_collection': 'allow'}):
            self.ok(request)
        self.assertEqual(self.calls, [])
        (self.repo / '.bionic.yml').write_text('config_version: "1"\ndocs_dir: bionic\ndecisions:\n  classifier: off\n')
        self.ok({**request, 'op_id': 'fast-optout-refresh'})
        self.assertEqual(self.calls, [])

    def test_public_refresh_reuses_only_current_advice(self):
        request = {'op': 'advice-refresh', 'op_id': 'fast-current-refresh',
            'kinds': ['context-selection'], 'task_id': 'build-it', 'role': 'developer'}
        self.ok(request)
        count = len(self.calls)
        self.assertGreater(count, 0)
        self.ok({**request, 'op_id': 'fast-current-refresh-again'})
        self.assertEqual(len(self.calls), count)
        self.edit(lambda doc: doc['plan']['tasks'][0].update(description='Changed task domain'))
        self.ok({**request, 'op_id': 'fast-changed-refresh'})
        self.assertGreater(len(self.calls), count)

    def test_optional_timeout_and_cancellation_leave_dispatch_available(self):
        self.replies['context-selection'] = decisions.Outcome(status='timeout')
        result = self.ok({'op': 'advice-refresh', 'op_id': 'fast-refresh-timeout',
                         'kinds': ['context-selection'], 'task_id': 'build-it', 'role': 'developer'})
        self.assertTrue(all(item['fallback'] == 'timeout' for item in result['classifications']))
        with patch.object(decisions, 'ask_many', side_effect=KeyboardInterrupt):
            # A timeout is never a reusable answer; cancellation affects only the new refresh.
            cancelled = self.ok({'op': 'advice-refresh', 'op_id': 'fast-refresh-cancel',
                                'kinds': ['context-selection'], 'task_id': 'build-it', 'role': 'developer'})
        self.assertEqual(cancelled['classification_unavailable'], 'cancelled')
        before = len(self.calls)
        self.dispatch(role='developer')
        self.assertEqual(len(self.calls), before)

    def test_missing_advice_does_not_append_unavailable_classifications(self):
        self.dispatch(role='developer')
        self.assertEqual(load(self.repo, self.cid).get('classifications', []), [])

    def test_explicit_queue_type_never_requests_work_sizing(self):
        with patch.object(cycle_classify, 'ask_one') as ask:
            found = cycle_classify.queue_sizing(self.repo, 'dev', 'Title', 'Goal', ['src'], ['done'])
        ask.assert_not_called()
        self.assertIsNone(found.classification)

    def test_execution_proof_commits_itself_and_reuses_bookkeeping_descendant(self):
        ignored = self.repo / '.gitignore'
        ignored.write_text(ignored.read_text().replace('bionic/\n', ''))
        self.git('add', '.gitignore', 'bionic')
        self.git('commit', '-q', '-m', 'Track fixture writer records')
        prepared = self.dispatch(role='developer')
        request = {'op': 'execution-check', 'op_id': 'fast-proof-commit',
                   'assignment': prepared['assignment'], 'attempt': prepared['attempt']}
        first = self.ok(request)
        self.assertTrue(first['record_commit']['changed'])
        head = self.git('rev-parse', 'HEAD')
        revision = load(self.repo, self.cid)['revision']
        self.assertTrue(self.ok(request)['replayed'])
        second = self.ok({**request, 'op_id': 'fast-proof-next-check'})
        self.assertFalse(second['changed'])
        self.assertEqual(load(self.repo, self.cid)['revision'], revision)
        self.assertEqual(self.git('rev-parse', 'HEAD'), head)

    def test_task_domain_filters_unrelated_broad_scope_context(self):
        # Use the real candidate policy, rather than HookBase's synthetic selection list.
        doc = load(self.repo, self.cid)
        task = {'id': 'prep', 'phase': 'release', 'description': 'Prepare beta release documents and version records.'}
        doc['type'] = 'release'
        doc['plan']['scope'] = ['crux', 'bionic', 'AGENTS.md']
        with patch.object(cycle_context, 'candidates', wraps=cycle_context._candidates):
            ids = [item['id'] for item in cycle_context._candidates(doc, task, 'dev-lead')]
        self.assertNotIn('backfill-signoff', ids)
        self.assertNotIn('cleanup-campsite', ids)
        self.assertIn('cycle', ids)
