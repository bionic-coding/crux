"""Warm role changes and actual wire provenance across partial answer reuse."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import httpx
from _classify_support import ClassifyBase, MODEL, answered, failed
from crux import decisions
from crux.core import llm_caller
from crux.decisions import transport
import cycle_classify as classify
from cycle_workflow import event, load, locked, mutate, save, tree


class CurrentnessBase(ClassifyBase):
    def edit(self, change=lambda doc: None):
        with locked(self.repo) as (cfg, _):
            doc = load(self.repo, self.cid)
            change(doc)
            event(doc, 'currentness-fixture')
            save(cfg, doc)


class WarmRoleTests(CurrentnessBase):
    def setUp(self):
        super().setUp()
        self.registry = copy.deepcopy(llm_caller.load_router_config())
        self.registry_path = self.repo / 'temporary-registry.json'
        self.registry_path.write_text(json.dumps(self.registry))
        for target, name, value in ((llm_caller, 'CONFIG_PATH', self.registry_path),
                                    (transport, '_credential', lambda: 'synthetic-offline-credential'),
                                    (decisions, 'classifier_status', transport.classifier_status)):
            patch = mock.patch.object(target, name, value)
            patch.start()
            self.addCleanup(patch.stop)
        llm_caller.invalidate_model_cache()
        self.addCleanup(llm_caller.invalidate_model_cache)
        self.original_key = llm_caller.get_default_model('cycle_classifier')
        self.assertGreater(llm_caller._load_model_roles.cache_info().currsize, 0)

    def start(self):
        self.enter_review(answered('floor-only'))
        self.before_calls = len(self.provider_calls)
        self.before_entries = len(self.entries())

    def test_unknown_role_without_cache_clear_disables_reuse_and_current_readers(self):
        self.start()
        self.registry['model_roles']['cycle_classifier'] = 'diagnostic-unknown-role-key'
        self.registry_path.write_text(json.dumps(self.registry))  # deliberately no invalidation
        self.assertEqual(llm_caller.get_default_model('cycle_classifier'), self.original_key)
        self.assertIsNone(decisions.classifier_basis())
        self.assertFalse(transport.classifier_status().configured)
        self.edit()
        result = classify.entered_review(self.repo, self.cid)
        self.assertFalse(result['classifier']['configured'])
        self.assertEqual((len(self.provider_calls), len(self.entries())), (self.before_calls, self.before_entries))
        self.assertTrue(all(not item['recorded'] for item in result['classifications']))
        cfg, doc = tree(self.repo), load(self.repo, self.cid)
        self.assertTrue(all(classify.valid_plan(cfg, doc, entry) is None for entry in self.entries('review-routing')))

    def test_valid_new_role_key_without_cache_clear_changes_identity_and_reasks(self):
        self.start()
        before = decisions.classifier_basis()
        self.registry['models']['classifier-alias'] = copy.deepcopy(self.registry['models'][self.original_key])
        self.registry['model_roles']['cycle_classifier'] = 'classifier-alias'
        self.registry_path.write_text(json.dumps(self.registry))
        self.assertEqual(llm_caller.get_default_model('cycle_classifier'), self.original_key)
        self.assertEqual(decisions.classifier_basis()['model_key'], 'classifier-alias')
        self.assertNotEqual(decisions.classifier_basis(), before)
        self.edit()
        result = classify.entered_review(self.repo, self.cid)
        self.assertTrue(result['classifier']['configured'])
        self.assertGreater(len(self.provider_calls), self.before_calls)
        self.assertTrue(all(not entry.get('reused_from') for entry in self.entries()[self.before_entries:]))
        self.assertEqual(llm_caller.get_default_model('cycle_classifier'), self.original_key, 'classifier must not clear the shared cache')


class UnresolvedHandoffTests(CurrentnessBase):
    def delivered(self, reply):
        prepared = self.prepare()
        sha = self.work(prepared)
        self.auto_hook_replies['handoff-completeness'] = reply
        self.default = answered('agent-assessment')
        result = self.ok({'op': 'deliver', 'op_id': 'deliver-unresolved-current', 'assignment': prepared['assignment'],
                          'attempt': 1, 'outcome': 'done', 'commits': [sha]})
        return prepared, result

    def test_current_explicit_unresolved_assessment_preserves_the_delivery_truth(self):
        prepared, result = self.delivered(answered('unresolved'))
        entry = self.entries('failure-routing')[-1]
        self.assertEqual(entry['trigger'], f'handoff:{prepared["assignment"]}/1')
        self.assertEqual(entry['route'], 'agent-assessment')
        self.assertEqual(self.asked[-1]['state']['trigger']['kind'], 'handoff-unresolved')
        self.assertEqual(self.asked[-1]['state']['attempt']['outcome'], 'done')
        self.assertEqual(result['outcome'], 'done')

    def test_unavailable_handoff_gets_no_extra_semantic_failure_question(self):
        prepared, _ = self.delivered(failed('unavailable'))
        before = len(self.provider_calls)
        result = classify.unresolved_handoff(self.repo, self.cid, 'build-it', prepared['assignment'], 1)
        self.assertEqual(result['classifications'], [])
        self.assertEqual(len(self.provider_calls), before)
        self.assertEqual(self.entries('failure-routing'), [])

    def test_new_assignment_and_stale_evidence_retire_old_handoff_routes(self):
        prepared, _ = self.delivered(answered('unresolved'))
        old = self.entries('failure-routing')[-1]
        self.edit(lambda doc: doc['plan']['tasks'][0].update(expected_evidence=['changed evidence']))
        before = len(self.provider_calls)
        self.assertEqual(classify.unresolved_handoff(self.repo, self.cid, 'build-it', prepared['assignment'], 1)['classifications'], [])
        self.assertEqual(len(self.provider_calls), before)
        mutate(self.repo, self.cid, 'task', task_id='build-it', state='pending')
        self.prepare('prepare-new-current', assignment='new-current-assignment')
        cfg, doc = tree(self.repo), load(self.repo, self.cid)
        self.assertIsNone(classify.valid_plan(cfg, doc, old))
        before = len(self.provider_calls)
        self.assertEqual(classify.unresolved_handoff(self.repo, self.cid, 'build-it', prepared['assignment'], 1)['classifications'], [])
        self.assertEqual(len(self.provider_calls), before)


class WireProvenanceTests(CurrentnessBase):
    a, b = 'r1:advisory:0', 'r1:advisory:1'

    def start(self):
        self.enter_review(answered('floor-only'))
        self.wire = []
        def gateway(request):
            payload = json.loads(request.content)
            self.wire.append(payload)
            answers = {qid: {'type': 'choice', 'choice': 'agent-assessment'} for qid in payload['questions']}
            if len(self.wire) == 1:
                answers[self.b] = {'type': 'malformed-answer'}
            return httpx.Response(200, json={'id': f'fixture-wire-{len(self.wire)}', 'model': MODEL, 'answers': answers})
        client = httpx.Client(transport=httpx.MockTransport(gateway))
        self.addCleanup(client.close)
        def send(state, questions, *, deadline, client_=None, kinds=()):
            if kinds == ('finding-disposition',):
                return transport.ask_many(state, questions, deadline=deadline, client=client, kinds=kinds)
            return self.scripted_many(state, questions, deadline=deadline, kinds=kinds)
        for target, name, value in ((decisions, 'ask_many', send), (transport, '_credential', lambda: 'synthetic-offline-credential')):
            patch = mock.patch.object(target, name, value)
            patch.start()
            self.addCleanup(patch.stop)
        code, result = self.record_review(self.receipt_id, {'verdict': 'approve', 'blocking': [], 'advisory': ['x' * 800, 'synthetic B'], 'cosmetic': []})
        self.assertEqual(code, 0, result)

    def repeat(self):
        before = len(self.entries('finding-disposition'))
        self.edit()
        classify.recorded_review(self.repo, self.cid)
        return {entry['subject']: entry for entry in self.entries('finding-disposition')[before:]}

    def test_partial_reuse_records_actual_wire_ids_and_preserves_reconstruction(self):
        self.start()
        self.assertEqual(list(self.wire[0]['questions']), [self.a, self.b])
        second = self.repeat()
        self.assertEqual(list(self.wire[1]['questions']), [self.b])
        self.assertEqual(second[self.a]['question_ids'], [self.a, self.b])
        self.assertEqual(second[self.a]['reused_from']['request_id'], 'fixture-wire-1')
        self.assertEqual(second[self.b]['question_ids'], list(self.wire[1]['questions']))
        self.assertEqual(second[self.b]['context_question_ids'], [self.a, self.b])
        self.assertEqual(second[self.b]['request_id'], 'fixture-wire-2')
        self.assertNotIn('reused_from', second[self.b])
        cfg, doc = tree(self.repo), load(self.repo, self.cid)
        self.assertTrue(all(classify.valid_plan(cfg, doc, entry) is not None for entry in second.values()))
        third = self.repeat()
        self.assertEqual(len(self.wire), 2)
        self.assertEqual(third[self.a]['question_ids'], [self.a, self.b])
        self.assertEqual(third[self.b]['question_ids'], [self.b])
        self.assertEqual(third[self.b]['context_question_ids'], [self.a, self.b])
        self.assertEqual(third[self.b]['reused_from']['request_id'], 'fixture-wire-2')

    def test_sibling_tail_and_policy_changes_invalidate_partially_reused_context(self):
        self.start()
        self.repeat()
        original = classify.finding_at
        def changed(*args):
            found = original(*args)
            return (*found[:-1], 'x' * 799 + 'y') if found and args[-1] == self.a else found
        with mock.patch.object(classify, 'finding_at', changed):
            fresh = self.repeat()
        self.assertEqual(list(self.wire[-1]['questions']), [self.a, self.b])
        self.assertTrue(all(not entry.get('reused_from') for entry in fresh.values()))
        with mock.patch.object(classify, 'ROUTING_POLICY_VERSION', 'changed-policy'):
            fresh = self.repeat()
        self.assertEqual(list(self.wire[-1]['questions']), [self.a, self.b])
        self.assertTrue(all(not entry.get('reused_from') for entry in fresh.values()))

    def test_pre_fix_ambiguous_wire_records_are_history_not_new_reuse_sources(self):
        with mock.patch.object(classify, 'ROUTING_POLICY_VERSION', '2'):
            self.start()
            self.repeat()
        def old_claim(doc):
            entry = doc['classifications'][-1]
            entry['question_ids'] = [self.a, self.b]
            entry.pop('context_question_ids', None)
        self.edit(old_claim)
        before = copy.deepcopy(self.entries())
        fresh = self.repeat()
        self.assertEqual(list(self.wire[-1]['questions']), [self.a, self.b])
        self.assertTrue(all(not entry.get('reused_from') for entry in fresh.values()))
        self.assertEqual(self.entries()[:len(before)], before, 'historical records must not be rewritten')


if __name__ == '__main__':
    unittest.main()
