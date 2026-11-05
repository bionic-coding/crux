"""Advice helper transactions retain request identity and deterministic boundaries.

These tests explicitly enable the internal provider policy to exercise the optional
helper transactions. Public cache-only operation behavior has separate unpatched
coverage in test_cycle_fast_operations; routine CLI calls never enable this policy.
"""
import contextlib
import fcntl
import io
import json
from pathlib import Path
import sys
import threading
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle
import cycle_classify
import cycle_context
import cycle_ops
from crux import decisions
from cycle_workflow import create, event, load, locked, save, validate
from test_cycle_slice import SliceBase


class HookBase(SliceBase):
    provider_helpers = True

    def setUp(self):
        super().setUp()
        if self.provider_helpers:
            policy = patch.object(cycle_context, 'provider_requests_allowed', return_value=True)
            policy.start(); self.addCleanup(policy.stop)
        self.calls, self.replies, self.during = [], {}, None
        self.probe = threading.Lock()
        for name, value in (('classifier_status', lambda: decisions.Status(True, None)), ('ask_many', self.ask)):
            p = patch.object(decisions, name, value); p.start(); self.addCleanup(p.stop)
        p = patch.object(cycle_context, 'candidates', return_value=[
            {'id': 'cycle', 'description': 'Coordinate the cycle.'}, {'id': 'council', 'description': 'Council review.'}])
        p.start(); self.addCleanup(p.stop)
        p = patch.object(cycle_context, 'focused_candidates', return_value=[])
        self.focused = p.start(); self.addCleanup(p.stop)

    def edit(self, function):
        with locked(self.repo) as (cfg, _):
            doc = load(self.repo, self.cid); function(doc); event(doc, 'hook-fixture'); save(cfg, doc)

    def ask(self, state, questions, *, deadline, client=None, kinds=()):
        with self.probe, (self.repo / 'bionic/cycles/.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(lock, fcntl.LOCK_UN)
        kind = kinds[0]
        self.calls.append({'kind': kind, 'state': state, 'questions': questions, 'deadline': deadline})
        if self.during:
            self.during(kind)
        result = {}
        for ident, question in questions.items():
            choice = self.replies.get(kind)
            if callable(choice):
                choice = choice(ident, question)
            if isinstance(choice, decisions.Outcome):
                result[ident] = choice
                continue
            if choice is None:
                choice = ('omit' if kind in ('context-selection', 'focused-test-ranking') else
                          next((option for option in question.options if option.startswith('answered:')), 'unresolved')
                          if kind == 'handoff-completeness' else 'developer' if kind == 'execution-arrangement' else 'agent-assessment')
            result[ident] = decisions.Outcome(status=decisions.ANSWERED, choice=choice,
                                             request_id='fixture-hook', served_model=decisions.EXPECTED_SERVED_MODEL,
                                             attempts=1, confidence=.95)
        return result

    def dispatch(self, **extra):
        return self.ok({'op': 'prepare-dispatch', 'op_id': 'hooks-prep-1', 'task_id': 'build-it', 'host': 'codex', **extra})

    def complete(self, outcome='done', **extra):
        prepared = self.dispatch(role='developer')
        sha = self.work(prepared)
        path = Path(prepared['result_path'])
        text = path.read_text(); path.write_text(text.replace('Outcome:', f'Evidence: commit {sha}\n\nOutcome:', 1))
        self.calls.clear()
        result = self.ok({'op': 'deliver', 'op_id': 'hooks-deliver-1', 'assignment': prepared['assignment'],
                          'attempt': prepared['attempt'], 'outcome': outcome, 'commits': [sha], **extra})
        return prepared, sha, result


class DispatchHookTests(HookBase):
    def plan_dispatch(self):
        self.cid = create(self.repo, 'dev', 'Plan a change', 'Useful change', ['src'], ['answer is 2'], 'builder', 'tester')['id']
        return self.ok({'op': 'prepare-dispatch', 'op_id': 'hooks-plan-1', 'task_id': 'plan', 'role': 'architect', 'host': 'codex'})

    def test_architect_plan_payload_keeps_mandatory_material_and_selected_canonical_skill(self):
        self.replies['context-selection'] = lambda ident, _: 'include' if ident.endswith('skill-0') else 'omit'
        result = self.plan_dispatch()
        self.payload = result['invocation']['parameters']['message']
        self.assertIn('Task: plan (plan)', self.payload)
        self.assertIn('Role boundary: architect', self.payload)
        self.assertIn(str(self.repo / 'AGENTS.md'), self.payload)
        self.assertIn(str(self.repo / 'bionic/objectives.md'), self.payload)
        from cycle_workflow import digest, tree
        docs = tree(self.repo).docs_root
        bundle = json.loads((docs / result['invocation_snapshot']['path']).read_bytes())
        selected = next(item for item in bundle['selected'] if item['id'] == 'cycle')
        source = cycle_context.PLUGIN_ROOT / 'skills/cycle/SKILL.md'
        raw = source.read_bytes()
        self.assertEqual((selected['origin'], selected['directory'], selected['sha256'], selected['size_bytes']),
                         (str(source), str(source.parent), digest(raw), len(raw)))
        self.assertIn('context-read ' + self.cid, self.payload)
        self.assertIn('--ref repo:' + (docs / selected['path']).relative_to(self.repo).as_posix(), self.payload)
        self.assertIn('--sha256 ' + selected['sha256'], self.payload)
        self.assertEqual((docs / selected['path']).read_bytes(), raw)
        self.assertEqual(result['optional_context'], {'selected': ['cycle'], 'retrievable': ['council']})

    def test_architect_plan_fallback_keeps_mandatory_material_with_no_optional_body(self):
        self.replies['context-selection'] = decisions.Outcome(status='refusal', attempts=1)
        result = self.plan_dispatch()
        self.payload = result['invocation']['parameters']['message']
        self.assertIn('Mandatory assignment', self.payload)
        self.assertIn('Role boundary: architect', self.payload)
        self.assertIn(str(self.repo / 'AGENTS.md'), self.payload)
        self.assertNotIn((cycle_context.PLUGIN_ROOT / 'skills/cycle/SKILL.md').read_text(), self.payload)
        self.assertEqual(result['optional_context'], {'selected': [], 'retrievable': ['cycle', 'council']})

    def test_bounded_role_is_automatic_and_replay_preserves_original_request(self):
        request = {'op': 'prepare-dispatch', 'op_id': 'hooks-prep-1', 'task_id': 'build-it', 'host': 'codex'}
        result = self.ok(request)
        self.assertEqual(load(self.repo, self.cid)['assignments'][0]['role'], 'developer')
        self.assertNotIn('execution-arrangement', [call['kind'] for call in self.calls])
        stored = next(op for op in load(self.repo, self.cid)['operations'] if op['op_id'] == request['op_id'])
        self.assertEqual(stored['request_sha256'], cycle_ops.request_digest(request))
        count = len(self.calls)
        replay = self.ok(request)
        self.assertTrue(replay['replayed'])
        self.assertEqual(len(self.calls), count)

    def test_selected_canonical_context_cannot_omit_mandatory_contract(self):
        self.replies['context-selection'] = lambda ident, _: 'include' if ident.endswith('skill-0') else 'omit'
        result = self.dispatch(role='architect')
        prompt = result['invocation']['parameters']['message']
        self.assertIn('Mandatory assignment', prompt)
        self.assertIn(str(self.repo / 'bionic/objectives.md'), prompt)
        self.assertIn('Expected evidence', prompt)
        from cycle_workflow import digest, tree
        docs = tree(self.repo).docs_root
        bundle = json.loads((docs / result['invocation_snapshot']['path']).read_bytes())
        selected = next(item for item in bundle['selected'] if item['id'] == 'cycle')
        source = cycle_context.PLUGIN_ROOT / 'skills/cycle/SKILL.md'
        raw = source.read_bytes()
        self.assertEqual((selected['origin'], selected['directory'], selected['sha256'], selected['size_bytes']),
                         (str(source), str(source.parent), digest(raw), len(raw)))
        self.assertIn('context-read ' + self.cid, prompt)
        self.assertIn('--ref repo:' + (docs / selected['path']).relative_to(self.repo).as_posix(), prompt)
        self.assertIn('--sha256 ' + selected['sha256'], prompt)
        self.assertEqual((docs / selected['path']).read_bytes(), raw)
        self.assertEqual(result['optional_context'], {'selected': ['cycle'], 'retrievable': ['council']})
        self.assertNotIn('execution-arrangement', [call['kind'] for call in self.calls])

    def test_bad_and_conflicting_original_requests_never_reach_provider(self):
        self.refused({'op': 'prepare-dispatch', 'op_id': 'hooks-bad-1', 'task_id': 'missing', 'host': 'codex'}, 'unknown-task')
        self.assertEqual(self.calls, [])
        self.dispatch(role='developer')
        count = len(self.calls)
        self.refused({'op': 'prepare-dispatch', 'op_id': 'hooks-prep-1', 'task_id': 'build-it', 'host': 'codex',
                      'role': 'reviewer'}, 'op-id-reused')
        self.assertEqual(len(self.calls), count)

    def test_semantic_change_during_request_cannot_reserve_stale_assignment(self):
        def change(kind):
            if self.during:
                self.during = None
                self.edit(lambda doc: doc['plan']['tasks'][0].update(description='different work'))
        self.during = change
        code, response = self.op({'op': 'prepare-dispatch', 'op_id': 'hooks-prep-1', 'task_id': 'build-it',
                                  'host': 'codex', 'role': 'developer'})
        self.assertEqual(code, 1, response)
        self.assertEqual(response['errors'][0]['code'], 'dispatch-context-changed')
        self.assertEqual(load(self.repo, self.cid).get('assignments', []), [])

    def test_invalid_role_recommendation_grants_nothing(self):
        self.edit(lambda doc: doc['plan'].update(streams=[{'id': 'a', 'paths': ['src/a.py'], 'independent': True},
                                                        {'id': 'b', 'paths': ['src/b.py'], 'independent': True}]))
        self.replies['execution-arrangement'] = 'commander'
        code, result = self.op({'op': 'prepare-dispatch', 'op_id': 'hooks-prep-1', 'task_id': 'build-it', 'host': 'codex'})
        self.assertEqual(code, 1, result)
        self.assertEqual(result['errors'][0]['code'], 'role-selection-required')
        self.assertEqual(load(self.repo, self.cid).get('assignments', []), [])


class DeliveryHookTests(HookBase):
    def test_context_question_ids_is_optional_nonempty_and_unique(self):
        self.dispatch(role='developer')
        doc=load(self.repo,self.cid);entry=doc['classifications'][0]
        entry['context_question_ids']=['context-0','context-1']
        validate(doc)
        entry['context_question_ids']=['context-0','context-0']
        with self.assertRaisesRegex(ValueError,'context_question_ids must be unique'):validate(doc)
        entry['context_question_ids']=['']
        with self.assertRaises(ValueError):validate(doc)
        del entry['context_question_ids'];validate(doc)

    def test_done_unresolved_evidence_routes_assessment_without_rewriting_delivery(self):
        self.replies['handoff-completeness']='unresolved'
        prepared,_,result=self.complete()
        self.assertIn('failure-routing',[call['kind'] for call in self.calls])
        self.assertEqual(result['outcome'],'done')
        self.assertTrue(any(action.get('agent') for action in result['failure_recovery']))
        before=load(self.repo,self.cid);delivery=before['assignments'][0]['delivery']
        self.assertEqual((before['plan']['tasks'][0]['status'],delivery['outcome']),('done','done'))
        self.assertEqual(len({id(call['deadline']) for call in self.calls}),1)
        self.calls.clear();raw=self.record_path().read_bytes()
        seen=self.ok({'op':'inspect'})
        self.assertTrue(seen['actions'][0].get('agent'))
        self.assertEqual(self.calls,[])
        self.assertEqual(self.record_path().read_bytes(),raw)
        self.assertEqual(load(self.repo,self.cid)['assignments'][0]['delivery'],delivery)
        self.assertEqual(seen['assignments'][0]['id'],prepared['assignment'])

    def test_unresolved_done_replay_asks_nothing_and_inspect_keeps_assessment(self):
        self.replies['handoff-completeness']='unresolved'
        prepared,sha,_=self.complete()
        before=self.record_path().read_bytes();self.calls.clear()
        replay=self.ok({'op':'deliver','op_id':'hooks-deliver-1','assignment':prepared['assignment'],
                        'attempt':prepared['attempt'],'outcome':'done','commits':[sha]})
        self.assertTrue(replay['replayed']);self.assertEqual(self.calls,[])
        self.assertEqual(self.record_path().read_bytes(),before)
        self.assertTrue(self.ok({'op':'inspect','summary':True})['actions'][0].get('agent'))
        self.assertEqual(self.calls,[])

    def test_unresolved_done_classifier_failure_still_offers_pure_assessment(self):
        self.replies['handoff-completeness']='unresolved'
        with patch.object(cycle_classify,'unresolved_handoff',side_effect=RuntimeError('fixture hook failure')):
            _,_,result=self.complete()
        self.assertEqual(result['classification_error'],'RuntimeError')
        self.assertEqual(result['failure_recovery'][0]['handler'],'agent-assessment')
        self.calls.clear();before=self.record_path().read_bytes()
        self.assertTrue(self.ok({'op':'inspect'})['actions'][0].get('agent'))
        self.assertEqual(self.calls,[]);self.assertEqual(self.record_path().read_bytes(),before)

    def assert_unresolved_outcome_uses_existing_failure(self,outcome):
        self.replies['handoff-completeness']='unresolved'
        _,_,result=self.complete(outcome=outcome)
        self.assertEqual([call['kind'] for call in self.calls].count('failure-routing'),1)
        self.assertEqual(result['outcome'],outcome)

    def test_unresolved_failed_uses_one_existing_failure_question(self):
        self.assert_unresolved_outcome_uses_existing_failure('failed')

    def test_unresolved_blocked_uses_one_existing_failure_question(self):
        self.assert_unresolved_outcome_uses_existing_failure('blocked')

    def test_unavailable_handoff_returns_direct_assessment_without_another_question(self):
        self.replies['handoff-completeness']=decisions.Outcome(status='refusal',attempts=1)
        _,_,result=self.complete()
        self.assertNotIn('failure-routing',[call['kind'] for call in self.calls])
        self.assertEqual(result['failure_recovery'][0]['handler'],'agent-assessment')
        self.assertTrue(self.ok({'op':'inspect'})['actions'][0].get('agent'))

    def test_resolved_new_delivery_retires_old_unresolved_assessment(self):
        self.replies['handoff-completeness']='unresolved'
        _,sha,_=self.complete()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cycle.main(['--repo-root',str(self.repo),'task',self.cid,'--task-id','build-it','--state','pending']),0)
        prepared=self.ok({'op':'prepare-dispatch','op_id':'hooks-prep-new','task_id':'build-it','host':'codex','role':'developer'})
        self.write_result(prepared)
        path=Path(prepared['result_path']);path.write_text(path.read_text().replace('Outcome:',f'Evidence: commit {sha}\nOutcome:',1))
        self.replies.pop('handoff-completeness')
        self.ok({'op':'deliver','op_id':'hooks-deliver-new','assignment':prepared['assignment'],'attempt':prepared['attempt'],
                 'outcome':'done','commits':[sha]})
        self.assertFalse(any(action.get('agent') for action in self.ok({'op':'inspect'})['actions']))

    def test_unresolved_stop_suppresses_routing_and_inspect_assessment(self):
        self.replies['handoff-completeness']='unresolved'
        _,_,result=self.complete(outcome='blocked',stop='approval-wait')
        self.assertEqual(self.calls,[])
        self.assertNotIn('failure_recovery',result)
        self.assertFalse(any(action.get('handler')=='agent-assessment' for action in self.ok({'op':'inspect'})['actions']))

    def test_unresolved_done_cannot_turn_invalid_recommendation_into_dispatch(self):
        self.replies.update({'handoff-completeness':'unresolved','failure-routing':'re-dispatch'})
        _,_,result=self.complete()
        self.assertTrue(all(action.get('agent') for action in result['failure_recovery']))
        self.assertEqual(load(self.repo,self.cid)['plan']['tasks'][0]['status'],'done')

    def test_unresolved_assessment_does_not_waive_stale_advance_guard(self):
        self.replies['handoff-completeness']='unresolved'
        self.complete();seen=self.ok({'op':'inspect'})
        self.edit(lambda doc:doc['plan']['constraints'].append('new constraint'))
        self.calls.clear()
        self.refused({'op':'advance','op_id':'hooks-stale-advance','expect_revision':seen['revision']},'stale-revision')
        self.assertEqual(self.calls,[])

    def test_summary_retains_responsible_agent_action_instead_of_empty_object(self):
        self.complete(outcome='failed')
        seen = self.ok({'op': 'inspect', 'summary': True})
        self.assertTrue(any(action.get('agent') for action in seen['actions']))
        self.assertNotIn({}, seen['actions'])

    def test_report_owning_developer_handler_is_a_legal_bounded_dispatch(self):
        self.replies['failure-routing'] = 'owning-developer'
        _, _, result = self.complete(outcome='failed')
        offer = next(offer for offer in result['failure_recovery'] if offer.get('handler') == 'owning-developer')
        self.assertEqual(offer['request']['role'], 'developer')
        again = self.ok({**offer['request'], 'op_id': 'hooks-repair-1'})
        self.assertEqual(load(self.repo, self.cid)['assignments'][-1]['role'], 'developer')
        self.assertNotEqual(again['assignment'], result['assignment'])

    def test_report_environment_handler_uses_configured_lead_with_same_allowance_checks(self):
        self.replies['failure-routing'] = 'environment-investigation'
        prepared = self.dispatch(role='developer'); sha = self.work(prepared)
        path = Path(prepared['result_path']); path.write_text(path.read_text().replace('Outcome:', 'ModuleNotFoundError: dependency missing\nOutcome:'))
        result = self.ok({'op': 'deliver', 'op_id': 'hooks-deliver-1', 'assignment': prepared['assignment'],
                          'attempt': 1, 'outcome': 'failed', 'commits': [sha]})
        offer = next(offer for offer in result['failure_recovery'] if offer.get('handler') == 'environment-investigation')
        self.assertEqual(offer['request']['role'], 'dev-lead')
        self.ok({**offer['request'], 'op_id': 'hooks-repair-1'})

    def test_complete_delivery_offers_no_repair_and_uses_one_deadline(self):
        _, _, result = self.complete()
        self.assertEqual(result['handoff']['omissions'], [])
        self.assertEqual(result['handoff']['unresolved'], [])
        self.assertEqual(result['handoff'].get('recovery', []), [])
        self.assertEqual(load(self.repo, self.cid)['plan']['tasks'][0]['status'], 'done')
        self.assertEqual(len({id(call['deadline']) for call in self.calls}), 1)

    def test_missing_evidence_returns_executable_reopen_then_dispatch(self):
        self.replies['handoff-completeness'] = 'absent'
        prepared, _, result = self.complete()
        original = load(self.repo, self.cid)['assignments'][0]['delivery']
        routes = result['handoff']['recovery']
        self.assertEqual(routes[1]['request']['op'], 'prepare-dispatch')
        self.assertEqual(load(self.repo, self.cid)['plan']['tasks'][0]['status'], 'done')
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(cycle.main(routes[0]['argv'][3:]), 0)
        again = self.ok({**routes[1]['request'], 'op_id': 'hooks-prep-2'})
        self.assertNotEqual(again['assignment'], prepared['assignment'])
        self.assertEqual(load(self.repo, self.cid)['assignments'][0]['delivery'], original)

    def test_retained_reopen_command_refuses_after_phase_advancement(self):
        self.replies['handoff-completeness'] = 'absent'
        _, _, result = self.complete()
        old = result['handoff']['recovery'][0]['argv'][3:]
        self.ok({'op': 'advance', 'op_id': 'hooks-advance-1', 'expect_revision': load(self.repo, self.cid)['revision']})
        before = self.record_path().read_bytes()
        with contextlib.redirect_stdout(io.StringIO()):
            code = cycle.main(old)
        self.assertEqual(code, 1)
        self.assertEqual(self.record_path().read_bytes(), before)

    def test_omissions_cannot_extend_exhausted_attempt_allowance(self):
        self.replies['handoff-completeness'] = 'absent'
        self.complete()
        def exhaust(doc):
            for number in (2, 3):
                event(doc, 'prepare-dispatch', task='build-it', assignment=f'old-{number}', attempt=1, role='developer')
        self.edit(exhaust)
        seen = self.ok({'op': 'inspect'})
        summary = seen['assignments'][0]['handoff']
        self.assertEqual(summary['route'], 'agent-assessment')
        self.assertEqual(summary['recovery'], [])

    def test_legacy_task_without_guard_keeps_its_existing_behavior(self):
        self.complete()
        self.ok({'op': 'advance', 'op_id': 'hooks-advance-1', 'expect_revision': load(self.repo, self.cid)['revision']})
        with contextlib.redirect_stdout(io.StringIO()):
            code = cycle.main(['--repo-root', str(self.repo), 'task', self.cid, '--task-id', 'build-it', '--state', 'pending'])
        self.assertEqual(code, 0)
        self.assertEqual(load(self.repo, self.cid)['plan']['tasks'][0]['status'], 'pending')

    def test_named_stop_suppresses_failure_routing(self):
        _, _, result = self.complete(outcome='blocked', stop='approval-wait')
        self.assertNotIn('failure-routing', [call['kind'] for call in self.calls])
        self.assertEqual(result.get('handoff', {}).get('recovery', []), [])


class FocusedHookTests(HookBase):
    def test_stale_original_build_advance_is_refused_before_ranking(self):
        self.complete(); self.calls.clear()
        self.refused({'op': 'advance', 'op_id': 'hooks-advance-1',
                      'expect_revision': load(self.repo, self.cid)['revision'] - 1}, 'stale-revision')
        self.assertEqual(self.calls, [])

    def test_delivery_refreshes_additive_suggestions_and_inspect_is_read_only(self):
        choice = {'id': 'test:tests/test_extra.py', 'path': 'tests/test_extra.py', 'reason': 'shared source token'}
        self.focused.return_value = [choice]
        self.replies['focused-test-ranking'] = 'include'
        self.edit(lambda doc: doc.update(required_checks=['existing-required']))
        self.complete()
        before = self.record_path().read_bytes(); calls = len(self.calls)
        result = self.ok({'op': 'inspect'})
        self.assertEqual(result['focused_suggestions'], [choice])
        self.assertEqual(load(self.repo, self.cid)['required_checks'], ['existing-required'])
        self.assertEqual(self.record_path().read_bytes(), before)
        self.assertEqual(len(self.calls), calls)

    def test_build_advance_does_not_stale_original_revision_after_ranking(self):
        self.complete()
        self.focused.return_value = [{'id': 'test:tests/test_extra.py', 'path': 'tests/test_extra.py', 'reason': 'new candidate'}]
        self.replies['focused-test-ranking'] = 'include'
        request = {'op': 'advance', 'op_id': 'hooks-advance-1', 'expect_revision': load(self.repo, self.cid)['revision']}
        result = self.ok(request)
        self.assertEqual(result['phase'], 'verify')
        self.assertTrue(any(call['kind'] == 'focused-test-ranking' for call in self.calls))
        self.assertGreater(result['revision'], request['expect_revision'] + 1)
        operation = next(op for op in load(self.repo, self.cid)['operations'] if op['op_id'] == request['op_id'])
        self.assertEqual(operation['request_sha256'], cycle_ops.request_digest(request))
