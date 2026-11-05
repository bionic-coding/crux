"""Classification records, state builders, the specialist table, configuration and the real transport behind the engine.

The transport tests use an httpx MockTransport and a fake credential; nothing leaves the process."""
from copy import deepcopy
import json
from pathlib import Path
import re
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import httpx
import crux_env
import cycle_classify
import cycle_progress
import cycle_questions
from crux import decisions
from crux.decisions import transport
from cycle_workflow import CycleError, load, mutate, validate
from _classify_support import AUTO_HOOK_KINDS, BLOCKING, ClassifyBase, MODEL, answered

FAKE_KEY = 'fake-credential-NOT-A-REAL-KEY-0123456789abcdef'
ENTRY_KEYS = {'kind', 'request_id', 'question_set', 'question_version', 'model', 'served_model', 'served_provider', 'cost', 'answer', 'route', 'fallback', 'subject',
              'fingerprint', 'question_ids', 'trigger', 'pass', 'phase', 'at', 'revision', 'routing_policy_version'}
REVIEW_MD = Path(__file__).resolve().parents[2] / 'skills/cycle/references/review.md'


class RecordTests(ClassifyBase):
    def recorded(self):
        self.enter_review(answered('floor-only'))
        return load(self.repo, self.cid)

    def test_an_entry_has_exactly_the_documented_fields_and_validates(self):
        doc = self.recorded()
        self.assertEqual(len([entry for entry in doc['classifications'] if entry['kind'] == 'review-routing']), len(cycle_classify.SPECIALISTS))
        for entry in doc['classifications']:
            self.assertEqual(set(entry) - {'reused_from'}, ENTRY_KEYS)
        validate(doc)

    def test_exactly_one_of_route_and_fallback_is_non_null(self):
        doc = self.recorded()
        for route, fallback in (('floor-only', 'timeout'), (None, None)):
            bad = deepcopy(doc); bad['classifications'][0].update(route=route, fallback=fallback)
            with self.subTest(route=route, fallback=fallback), self.assertRaises(CycleError):
                validate(bad)
        ok = deepcopy(doc); ok['classifications'][0].update(route=None, fallback='timeout'); validate(ok)

    def test_a_kind_outside_the_four_and_an_extra_field_are_invalid(self):
        doc = self.recorded()
        for edit in ({'kind': 'something-else'}, {'state': 'text'}, {'fingerprint': 'abc'}, {'pass': 0}, {'answer': 'floor-only'}):
            bad = deepcopy(doc); bad['classifications'][0].update(edit)
            with self.subTest(edit=edit), self.assertRaises(CycleError):
                validate(bad)

    def test_a_version_three_record_without_the_lists_stays_valid_and_version_two_forbids_them(self):
        doc = load(self.repo, self.cid)
        self.assertNotIn('classifications', doc); validate(doc)
        two = load(self.repo, self.fixture(version=2))
        for key, value in (('classifications', []), ('deferrals', [])):
            bad = deepcopy(two); bad[key] = value
            with self.subTest(key=key), self.assertRaises(CycleError):
                validate(bad)

    def test_a_deferral_validates_and_its_finding_id_is_checked(self):
        doc = self.recorded()
        doc['deferrals'] = [{'finding': 'r1:advisory:0', 'note': 'n', 'pass': 1, 'phase': 'review', 'at': 'now'}]
        validate(doc)
        doc['deferrals'][0]['finding'] = 'r1:blocking:0:x'
        with self.assertRaises(CycleError):
            validate(doc)

    def test_stream_e_reader_counts_the_classification(self):
        self.enter_review(answered('add:release-distribution'))
        self.assertEqual(cycle_progress.classification_count(load(self.repo, self.cid)), len(self.entries()))
        self.assertEqual(len(self.entries('review-routing')), len(cycle_classify.SPECIALISTS))

    def test_no_entry_and_no_record_field_contains_state_text(self):
        self.review_with_findings(answered('return'), answered('follow-up'), answered('agent-assessment'))
        text = self.record_path().read_text()
        self.assertNotIn('LEAK-ZQ', text, 'finding text reached the cycle record')
        for entry in self.entries():
            self.assertEqual(set(entry) - {'reused_from'}, ENTRY_KEYS)
            self.assertNotRegex(json.dumps(entry), r'set the answer|review the change|consider a docstring')
        self.assertTrue(any('LEAK-ZQ' in json.dumps(call['state']) for call in self.asked), 'the state itself carries the recorded finding text')

    def test_the_post_write_revision_is_returned_by_each_classifying_operation(self):
        response = self.enter_review(answered('floor-only'))
        self.assertEqual(response['revision'], load(self.repo, self.cid)['revision'])
        self.replies[:] = [answered('agent-assessment')]
        code, reviewed = self.record_review(self.receipt_id, {'verdict': 'approve', 'advisory': ['LEAK-ZQ-note']})
        self.assertEqual(reviewed['revision'], load(self.repo, self.cid)['revision'])


class StateTests(ClassifyBase):
    TRACEBACK = ('Traceback (most recent call last):\n  File "t.py", line 3, in test_a\n    self.assertEqual(1, 2)\n'
                 'AssertionError: 1 != 2\n- 1\n+ 2\n\nFAIL: test_alpha (pkg.mod.Tests.test_alpha)\nFAIL: test_beta (pkg.mod.Tests.test_beta)\n')

    def test_failure_summary_keeps_only_the_extracted_fields(self):
        summary = cycle_classify.failure_summary('unit', 1, self.TRACEBACK)
        self.assertEqual(summary, {'check_id': 'unit', 'exit_status': 1, 'failing_tests': ['pkg.mod.Tests.test_alpha', 'pkg.mod.Tests.test_beta'], 'exception_type': 'AssertionError',
                                   'message': '1 != 2'})
        rendered = json.dumps(summary)
        for leak in ('Traceback', 'File "t.py"', 'assertEqual', '- 1', '+ 2'):
            self.assertNotIn(leak, rendered)

    def test_failure_summary_bounds_every_field(self):
        long = 'x' * 500
        summary = cycle_classify.failure_summary(long, 1, f'FAIL: test_{long} (pkg.{long})\nValueError: {long}\n' + ''.join(f'ERROR: t{i} (a.b)\n' for i in range(20)))
        self.assertLessEqual(len(summary['check_id']), cycle_classify.MAX_PATH_CHARS)
        self.assertLessEqual(len(summary['message']), 160)
        self.assertLessEqual(len(summary['failing_tests']), cycle_classify.MAX_SUMMARY_IDS)
        self.assertEqual(cycle_classify.failure_summary('c', 'x', ''), {'check_id': 'c', 'exit_status': None, 'failing_tests': [], 'exception_type': None, 'message': None})

    def test_a_failing_receipt_with_a_traceback_sends_only_the_extracted_fields(self):
        self.to_test()
        declaration = {'check_id': 'unit',
                       'command': [sys.executable, '-c', "raise AssertionError('1 != 2')"], 'inputs': ['src'], 'environment': []}
        from test_evidence import execute
        receipt = execute(self.repo, declaration)['evidence']['id']
        self.replies[:] = [answered('agent-assessment')]
        self.cli('evidence', '--check-id', 'unit', '--evidence-id', receipt, '--use', 'executed')
        state = self.asked[0]['state']
        self.assertEqual(set(state), {'trigger', 'check', 'summary', 'phase', 'pass'})
        self.assertEqual((state['summary']['exception_type'], state['summary']['message'], state['summary']['check_id']), ('AssertionError', '1 != 2', 'unit'))
        self.assertNotIn('Traceback', json.dumps(state))
        self.assertEqual(state['trigger'], {'kind': 'check-failed'})

    def test_state_builders_read_only_the_permitted_fields(self):
        self.review_with_findings(answered('agent-assessment'), answered('agent-assessment'), answered('agent-assessment'))
        finding_state = self.asked[0]['state']
        self.assertEqual(set(finding_state), set(cycle_classify.STATE_FIELDS['finding-disposition']))
        self.assertEqual(len(finding_state['findings']), 3, 'the batch lists every finding of the report')
        for finding in finding_state['findings']:
            self.assertEqual(set(finding), {'id', 'category', 'title', 'text'})
        self.assertIn('LEAK-ZQ-consequence', finding_state['findings'][0]['text'])
        review_paths = finding_state['review']['changed_paths']
        self.assertEqual(set(review_paths), {'count', 'first'})
        self.assertLessEqual(len(review_paths['first']), cycle_classify.MAX_PATHS)

    def test_changed_paths_are_bounded_to_a_count_and_the_first_paths(self):
        names = [f'pkg/file_{i:03}.py' for i in range(40)]
        bound = cycle_classify.path_bound(names)
        self.assertEqual((bound['count'], len(bound['first'])), (40, cycle_classify.MAX_PATHS))

    def test_finding_fields_bound_titles_and_text(self):
        title, text = cycle_classify.finding_fields({'path': 'src/a.py', 'consequence': 'c' * 2000, 'evidence': ['e', 'f']})
        self.assertEqual(title, 'src/a.py'); self.assertLessEqual(len(text), cycle_classify.MAX_FINDING_CHARS)
        self.assertEqual(cycle_classify.finding_fields('first line\nsecond')[0], 'first line')
        self.assertEqual(cycle_classify.finding_fields(7), ('', ''))

    def test_work_sizing_state_is_the_proposed_cycle_text_only(self):
        self.replies[:] = [answered('dev')]
        out = __import__('io').StringIO()
        with __import__('contextlib').redirect_stdout(out):
            code = __import__('cycle').main(['--repo-root', str(self.repo), 'create', '--type', 'auto', '--title', 'T', '--goal', 'G', '--implementer', 'a',
                                             '--coordinator', 'b', '--scope', 'src', '--acceptance', 'ok'])
        self.assertEqual(code, 0)
        self.assertEqual(set(self.asked[0]['state']), set(cycle_classify.STATE_FIELDS['work-sizing']))


class SpecialistTableTests(unittest.TestCase):
    def triggers(self):
        text = ' '.join(line.strip() for line in REVIEW_MD.read_text().splitlines())
        match = re.search(r'Target specialist checks at (.+?)\.', text)
        self.assertTrue(match, 'review.md lost its specialist-check sentence')
        parts = [re.sub(r'^and ', '', part.strip()) for part in match.group(1).split(', ')]
        return parts

    def test_the_table_covers_every_escalation_trigger_in_review_md(self):
        covered = {phrase for spec in cycle_classify.SPECIALISTS.values() for phrase in spec['covers']}
        triggers = self.triggers()
        self.assertEqual(len(triggers), 5, triggers)
        self.assertEqual(sorted(set(triggers) - covered), [], 'a review.md trigger has no specialist in the table')

    def test_the_table_has_the_six_ids_each_with_globs_and_risk_tags(self):
        self.assertEqual(list(cycle_classify.SPECIALISTS), ['credentials-and-data-transmission', 'model-routing-boundary', 'recovery-and-destructive-operations',
                                                            'release-distribution', 'authentication-and-authorization', 'untrusted-input-execution'])
        for ident, spec in cycle_classify.SPECIALISTS.items():
            self.assertTrue(spec['paths'] and spec['risks'], ident)

    def test_path_globs_and_risk_tags_each_select_their_specialist(self):
        probes = {'credentials-and-data-transmission': 'crux/scripts/crux_env.py', 'model-routing-boundary': 'crux/scripts/crux/core/llm_router_config.json',
                  'recovery-and-destructive-operations': 'tools/migrate_store.py', 'release-distribution': 'sync.sh',
                  'authentication-and-authorization': 'app/auth/session.py', 'untrusted-input-execution': 'tools/shell_runner.py'}
        for ident, path in probes.items():
            matched = [i for i, spec in cycle_classify.SPECIALISTS.items() if any(cycle_classify.fnmatch.fnmatchcase(path.lower(), g) for g in spec['paths'])]
            self.assertIn(ident, matched, path)


class ClassifierConfigTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def status(self, status):
        patcher = mock.patch.object(decisions, 'classifier_status', lambda: status)
        patcher.start(); self.addCleanup(patcher.stop)

    def test_configured_when_the_repository_and_the_transport_agree(self):
        self.status(decisions.Status(True, None))
        self.assertEqual(cycle_classify.classifier_state(self.root), {'configured': True, 'reason': None})

    def test_the_opt_out_wins_over_a_configured_transport(self):
        self.status(decisions.Status(True, None))
        (self.root / '.bionic.yml').write_text('config_version: "1"\ndocs_dir: bionic\ndecisions:\n  classifier: off\n')
        self.assertEqual(cycle_classify.classifier_state(self.root), {'configured': False, 'reason': 'opted-out'})

    def test_an_invalid_decisions_value_is_reported_unconfigured_not_raised(self):
        self.status(decisions.Status(True, None))
        (self.root / '.bionic.yml').write_text('config_version: "1"\ndocs_dir: bionic\ndecisions:\n  classifier: on\n')
        self.assertEqual(cycle_classify.classifier_state(self.root), {'configured': False, 'reason': 'configuration-error'})

    def test_a_missing_credential_is_unconfigured_through_the_real_status(self):
        real_get = crux_env.get
        with mock.patch.object(crux_env, 'get', lambda key, default=None: None if key == 'OPENROUTER_API_KEY' else real_get(key, default)):
            self.assertEqual(cycle_classify.classifier_state(self.root), {'configured': False, 'reason': 'credential-missing'})

    def test_a_missing_or_empty_role_is_unconfigured_not_an_exception(self):
        for role in ({}, {'cycle_classifier': ''}):
            with self.subTest(role=role), mock.patch.object(transport, 'load_classifier_entry', side_effect=transport.UnusableEntry('role-missing')):
                self.assertEqual(cycle_classify.classifier_state(self.root), {'configured': False, 'reason': 'role-missing'})


class RealTransportBehindTheEngine(ClassifyBase):
    """The engine records the transport's final outcome. The transport itself runs here against a MockTransport."""

    def setUp(self):
        super().setUp()
        self.requests, self.responder = [], lambda request: httpx.Response(503, json={'error': {'message': 'down'}})
        client = httpx.Client(transport=httpx.MockTransport(lambda request: (self.requests.append(request), self.responder(request))[1]))
        real_ask_many = transport.ask_many
        real_get = crux_env.get
        def wire_or_auto(state, questions, *, deadline, kinds=(), **_):
            # These wire assertions target review routing; enabled automatic hooks
            # keep their explicit per-kind provider fixtures and retained records.
            if self._engine_question_depth and len(kinds) == 1 and kinds[0] in AUTO_HOOK_KINDS:
                return self.scripted_many(state, questions, deadline=deadline, kinds=kinds)
            return real_ask_many(state, questions, deadline=deadline, client=client, kinds=kinds)
        for target, replacement in ((decisions, ('ask_many', wire_or_auto)),
                                    (crux_env, ('get', lambda key, default=None: FAKE_KEY if key == 'OPENROUTER_API_KEY' else real_get(key, default)))):
            patcher = mock.patch.object(target, replacement[0], replacement[1])
            patcher.start(); self.addCleanup(patcher.stop)

    def test_unavailability_is_retried_once_by_the_transport_and_the_engine_records_the_final_outcome(self):
        self.enter_review()
        self.assertEqual(len(self.requests), 2, 'one request holds every predicate, and the transport retries it once')
        entries = self.entries('review-routing')
        self.assertEqual(len(entries), len(cycle_classify.SPECIALISTS))
        for entry in entries:
            self.assertEqual((entry['route'], entry['fallback']), (None, 'unavailable'))

    def denied(self, code):
        self.responder = lambda request: httpx.Response(code, json={'error': {'message': 'denied'}})
        self.enter_review()
        self.assertEqual(len(self.requests), 1, 'a 4xx is never retried')
        self.assertEqual({e['fallback'] for e in self.entries('review-routing')}, {f'malformed:http-{code}'})

    def test_http_401_is_recorded_as_malformed_without_a_retry(self):
        self.denied(401)

    def test_http_403_is_recorded_as_malformed_without_a_retry(self):
        self.denied(403)

    def test_a_credential_in_a_task_description_is_caught_and_nothing_is_sent(self):
        self.add_review_task(f'review with {FAKE_KEY}')
        self.enter_review()
        self.assertEqual(self.requests, [])
        self.assertEqual({e['fallback'] for e in self.entries('review-routing')}, {'scan-match'})
        self.assertNotIn(FAKE_KEY, json.dumps(self.entries()))

    @staticmethod
    def answers(**fields):
        """The wire answers of a review: the same choice answer under each predicate's question id (its subject)."""
        return {f'review:{ident}': {'type': 'choice', 'choice': 'floor-only', **fields} for ident in cycle_classify.SPECIALISTS}

    def test_an_entry_records_the_cost_and_serving_provider_the_response_reports(self):
        self.responder = lambda request: httpx.Response(200, json={'id': 'gen-dec-2', 'model': MODEL, 'provider': 'Google AI Studio', 'answers': self.answers(
            confidence=0.8, probabilities={'floor-only': 0.9}), 'usage': {'input_tokens': 5, 'cost': 1.5e-05}})
        self.enter_review()
        entries = self.entries('review-routing')
        self.assertEqual(len(entries), len(cycle_classify.SPECIALISTS))
        self.assertEqual({e['served_provider'] for e in entries}, {'Google AI Studio'})
        # The transport reports a request's usage once, on its first answered question, so a sum counts the cost once.
        self.assertEqual([e['cost'] for e in entries], [1.5e-05] + [None] * (len(entries) - 1))
        validate(load(self.repo, self.cid))

    def test_an_unreported_cost_and_provider_are_recorded_as_null(self):
        self.responder = lambda request: httpx.Response(200, json={'id': 'gen-dec-3', 'model': MODEL, 'provider': ['not', 'a', 'string'],
                                                                   'answers': self.answers(), 'usage': {'cost': -1}})
        self.enter_review()
        entries = self.entries('review-routing')
        self.assertEqual(len(entries), len(cycle_classify.SPECIALISTS))
        for entry in entries:
            self.assertEqual((entry['served_provider'], entry['cost']), (None, None))

    def test_the_request_carries_both_denials_and_no_identifying_fields(self):
        self.responder = lambda request: httpx.Response(200, json={'id': 'gen-dec-1', 'model': MODEL, 'answers': self.answers(
            confidence=0.8, probabilities={'floor-only': 0.9}), 'usage': {'input_tokens': 5}})
        self.enter_review()
        self.assertEqual(len(self.requests), 1, 'every predicate of the review shares one request')
        payload = json.loads(self.requests[0].content)
        self.assertEqual(payload['provider'], dict(decisions.REQUIRED_DENIALS))
        self.assertNotIn('session_id', payload); self.assertNotIn('user', payload)
        entries = self.entries('review-routing')
        self.assertEqual({(e['route'], e['request_id']) for e in entries}, {('floor-only', 'gen-dec-1')})


if __name__ == '__main__':
    unittest.main()
