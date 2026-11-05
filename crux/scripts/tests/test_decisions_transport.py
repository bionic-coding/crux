"""Tests for the shipped Decisions transport (``crux.decisions``).

Every provider response is controlled: an ``httpx.MockTransport`` stands in for the
gateway and no test sends a live request. The credential is an obviously fake value
patched into ``crux_env``; several tests assert that it appears in no outcome,
exception text or captured log.
"""
from __future__ import annotations

import ast
import json
import logging
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS))

import httpx  # noqa: E402
import crux_env  # noqa: E402
from crux import decisions  # noqa: E402
from crux.core import llm_caller  # noqa: E402
from crux.decisions import (  # noqa: E402
    ChoiceQuestion, Deadline, EXPECTED_SERVED_MODEL, REQUIRED_DENIALS, ask, classifier_status,
)
from crux.decisions import transport  # noqa: E402

FAKE_KEY = 'fake-credential-NOT-A-REAL-KEY-0123456789abcdef'
REAL_REGISTRY = SCRIPTS / 'crux' / '_config' / 'llm_router_config.json'
URL = 'https://openrouter.ai/api/alpha/decisions'
# The observed form (CYC-0090 live probe, 2026-10-30): HTTP 404 with this body.
PROBE_404_BODY = {
    'error': {
        'message': 'No endpoints found matching your data policy (Zero data retention). '
                   'Configure: https://openrouter.ai/settings/privacy',
        'code': 404,
        'metadata': {
            'routing_funnel': [{'step': 'Initial Endpoints', 'endpoint_count': 1}],
            'failed_routing_step': 'Filter by Data Policy',
        },
    }
}
OPTIONS = {'quick-fix': 'a one-file fix', 'iterate': 'a bounded iteration', 'dev': 'a full dev cycle',
           'insufficient-information': 'the state does not decide the route'}
QUESTION = ChoiceQuestion(instructions='Pick the route for this work.', options=OPTIONS)
STATE = {'task': 'fix a typo in src/cli/help.py'}


def good_body(choice='dev', *, model=EXPECTED_SERVED_MODEL, qid='route', **answer_over):
    answer = {'type': 'choice', 'choice': choice, 'confidence': 0.9,
              'probabilities': {'quick-fix': 0.05, 'iterate': 0.05, 'dev': 0.85, 'insufficient-information': 0.05}}
    answer.update(answer_over)
    return {'id': 'gen-dec-fake-1', 'model': model, 'answers': {qid: answer},
            'usage': {'input_tokens': 120, 'output_tokens': 8, 'cost': 1.2e-05}}


class Harness(unittest.TestCase):
    """A temporary registry copy, a fake credential, and a recording MockTransport client."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'registry.json'
        self.original = llm_caller.CONFIG_PATH
        self.addCleanup(self._restore)
        self.write_registry(json.loads(REAL_REGISTRY.read_text()))
        self.key_reads = []
        self.key_value = FAKE_KEY
        real_get = crux_env.get

        def fake_get(key, default=None):
            if key == 'OPENROUTER_API_KEY':
                self.key_reads.append(key)
                return self.key_value
            return real_get(key, default)

        patcher = mock.patch.object(crux_env, 'get', side_effect=fake_get)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.requests = []
        self.log_records = []
        handler = logging.Handler()
        handler.emit = self.log_records.append
        root = logging.getLogger()
        self._old_level = root.level
        root.setLevel(logging.DEBUG)
        root.addHandler(handler)
        self.addCleanup(lambda: (root.removeHandler(handler), root.setLevel(self._old_level)))

    def _restore(self):
        llm_caller.CONFIG_PATH = self.original
        llm_caller.invalidate_model_cache()

    def write_registry(self, config):
        self.path.write_text(json.dumps(config))
        llm_caller.CONFIG_PATH = self.path
        llm_caller.invalidate_model_cache()

    def edit_registry(self, edit):
        config = json.loads(REAL_REGISTRY.read_text())
        edit(config)
        self.write_registry(config)

    def client(self, responder):
        def handler(request):
            self.requests.append(request)
            return responder(request)
        return httpx.Client(transport=httpx.MockTransport(handler))

    def ask(self, responder, *, state=STATE, question=QUESTION, deadline=None, qid='route'):
        return ask(state, qid, question, deadline=deadline or Deadline(), client=self.client(responder))

    def reply(self, body, status=200):
        return lambda request: httpx.Response(status, json=body)

    def payload(self, index=0):
        return json.loads(self.requests[index].content)

    def assertNoCredentialLeak(self, *objects):
        for obj in objects:
            self.assertNotIn(FAKE_KEY, repr(obj))
        for record in self.log_records:
            self.assertNotIn(FAKE_KEY, record.getMessage())
            self.assertNotIn(FAKE_KEY, repr(record.args))


class RequestBuildTests(Harness):
    def test_request_url_is_the_pinned_origin_and_path(self):
        out = self.ask(self.reply(good_body()))
        self.assertEqual(out.status, 'answered')
        self.assertEqual(str(self.requests[0].url), URL)
        self.assertEqual(self.requests[0].method, 'POST')

    def test_credential_travels_only_in_the_authorization_header(self):
        self.ask(self.reply(good_body()))
        request = self.requests[0]
        self.assertEqual(request.headers['authorization'], f'Bearer {FAKE_KEY}')
        self.assertNotIn(FAKE_KEY, str(request.url))
        self.assertNotIn(FAKE_KEY, request.content.decode())

    def _mismatch(self, base_url):
        def edit(config):
            config['providers']['openrouter']['base_url'] = base_url
        self.edit_registry(edit)
        out = self.ask(self.reply(good_body()))
        self.assertEqual(out.status, 'unconfigured')
        self.assertEqual(self.requests, [])
        self.assertEqual(self.key_reads, [], 'the credential was read before the origin matched')
        self.assertEqual(out.attempts, 0)

    def test_mismatched_scheme_is_refused_before_the_credential_is_read(self):
        self._mismatch('http://openrouter.ai/api/v1')

    def test_mismatched_host_is_refused_before_the_credential_is_read(self):
        self._mismatch('https://openrouter.example.com/api/v1')

    def test_mismatched_port_is_refused_before_the_credential_is_read(self):
        self._mismatch('https://openrouter.ai:8443/api/v1')

    def test_userinfo_in_the_origin_is_refused_before_the_credential_is_read(self):
        self._mismatch('https://user:pw@openrouter.ai/api/v1')

    def test_a_redirect_is_not_followed(self):
        def responder(request):
            return httpx.Response(302, headers={'location': 'https://evil.example.com/steal'})
        out = self.ask(responder)
        self.assertEqual(len(self.requests), 1)
        self.assertEqual(out.status, 'malformed')
        self.assertEqual(out.http_status, 302)
        self.assertNoCredentialLeak(out)

    def test_follow_redirects_false_is_passed_on_the_call(self):
        seen = {}
        client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=good_body())))
        original = client.stream

        def spy(*args, **kwargs):
            seen.update(kwargs)
            return original(*args, **kwargs)
        client.stream = spy
        ask(STATE, 'route', QUESTION, deadline=Deadline(), client=client)
        self.assertIs(seen.get('follow_redirects'), False)

    def test_provider_data_collection_is_deny_on_every_request(self):
        self.ask(self.reply(good_body()))
        self.ask(lambda r: httpx.Response(500))  # a failing request, plus its retry
        self.assertGreaterEqual(len(self.requests), 3)
        for i in range(len(self.requests)):
            self.assertEqual(self.payload(i)['provider']['data_collection'], 'deny')

    def test_provider_zdr_is_absent_on_every_request(self):
        self.ask(self.reply(good_body()))
        self.ask(lambda r: httpx.Response(500))
        self.assertGreaterEqual(len(self.requests), 3)
        for i in range(len(self.requests)):
            self.assertIn('provider', self.payload(i))
            self.assertNotIn('zdr', self.payload(i)['provider'])

    def test_provider_object_is_exactly_the_required_denials(self):
        self.ask(self.reply(good_body()))
        self.assertEqual(self.payload()['provider'], dict(REQUIRED_DENIALS))
        self.assertEqual(dict(REQUIRED_DENIALS), {'data_collection': 'deny'})
        self.assertEqual(decisions.REFUSED_ENTRY_KEYS, frozenset({'zdr'}))

    def test_registry_entry_weakening_data_collection_is_refused_at_load(self):
        def edit(config):
            config['models']['gpt-6-luna-decisions']['data_collection'] = 'allow'
        self.edit_registry(edit)
        with self.assertRaises(transport.UnusableEntry):
            transport.load_classifier_entry()
        status = classifier_status()
        self.assertFalse(status.configured)
        self.assertEqual(status.reason, 'registry-entry-invalid')
        out = self.ask(self.reply(good_body()))
        self.assertEqual(out.status, 'unconfigured')
        self.assertEqual(self.requests, [])

    def test_registry_entry_carrying_any_zdr_key_is_refused_at_load(self):
        for value in (True, False, None, 'true'):
            with self.subTest(zdr=value):
                def edit(config, value=value):
                    config['models']['gpt-6-luna-decisions']['zdr'] = value
                self.edit_registry(edit)
                with self.assertRaises(transport.UnusableEntry):
                    transport.load_classifier_entry()
                self.assertEqual(self.ask(self.reply(good_body())).status, 'unconfigured')
        self.assertEqual(self.requests, [])

    def test_a_weakened_entry_leaves_only_the_classifier_unconfigured(self):
        for field, value in (('data_collection', 'allow'), ('zdr', True)):
            with self.subTest(field=field):
                def edit(config, field=field, value=value):
                    config['models']['gpt-6-luna-decisions'][field] = value
                self.edit_registry(edit)
                self.assertEqual(classifier_status().reason, 'registry-entry-invalid')
                # The shared router still loads, and another model still resolves.
                self.assertIn('gpt-6-luna-decisions', llm_caller.load_router_config()['models'])
                self.assertEqual(llm_caller.get_model_config('gpt-6.1-sol').name, 'gpt-6.1-sol')

    def test_the_registry_cannot_change_the_wire_denials(self):
        # Positive control for the two refusals above: the unmodified entry loads and sends both denials.
        entry = transport.load_classifier_entry()
        self.assertEqual(entry.api_string, EXPECTED_SERVED_MODEL)
        self.ask(self.reply(good_body()))
        self.assertEqual(self.payload()['provider'], {'data_collection': 'deny'})

    def test_session_id_and_user_are_absent(self):
        self.ask(self.reply(good_body()))
        body = self.payload()
        self.assertNotIn('session_id', body)
        self.assertNotIn('user', body)
        self.assertEqual(sorted(body), ['model', 'provider', 'questions', 'state'])
        self.assertEqual(body['model'], EXPECTED_SERVED_MODEL)
        self.assertEqual(body['questions']['route']['type'], 'choice')
        self.assertEqual(body['questions']['route']['criteria'], OPTIONS)


class FallbackTests(Harness):
    def test_insufficient_information_is_an_answer_the_engine_interprets(self):
        out = self.ask(self.reply(good_body('insufficient-information')))
        self.assertEqual((out.status, out.choice), ('answered', 'insufficient-information'))

    def test_answered_carries_choice_probabilities_confidence_ids_and_usage(self):
        out = self.ask(self.reply(good_body('iterate')))
        self.assertEqual(out.choice, 'iterate')
        self.assertEqual(out.confidence, 0.9)
        self.assertEqual(out.request_id, 'gen-dec-fake-1')
        self.assertEqual(out.served_model, EXPECTED_SERVED_MODEL)
        self.assertEqual(out.probabilities['dev'], 0.85)
        self.assertEqual(out.usage['input_tokens'], 120)
        self.assertEqual((out.attempts, out.http_status), (1, 200))

    def test_refusal_answer_falls_back_without_retry(self):
        out = self.ask(self.reply(good_body(**{'type': 'refusal'})))
        self.assertEqual(out.status, 'refusal')
        self.assertEqual(len(self.requests), 1)
        self.assertEqual(out.attempts, 1)

    def test_malformed_output_falls_back_without_retry(self):
        for name, body in {
            'no-answers': {'id': 'x', 'model': EXPECTED_SERVED_MODEL},
            'answers-not-object': {'id': 'x', 'model': EXPECTED_SERVED_MODEL, 'answers': []},
            'answer-not-object': {'id': 'x', 'model': EXPECTED_SERVED_MODEL, 'answers': {'route': 'dev'}},
            'unknown-type': good_body(**{'type': 'mystery'}),
            'no-choice-key': {'id': 'x', 'model': EXPECTED_SERVED_MODEL, 'answers': {'route': {'type': 'choice'}}},
            'non-string-choice': good_body(choice=3),
            'body-not-object': ['nope'],
        }.items():
            with self.subTest(name):
                self.requests.clear()
                out = self.ask(self.reply(body))
                self.assertEqual(out.status, 'malformed')
                self.assertEqual(len(self.requests), 1)

    def test_a_200_with_a_non_json_body_is_malformed(self):
        out = self.ask(lambda r: httpx.Response(200, content=b'<html>not json</html>'))
        self.assertEqual(out.status, 'malformed')
        self.assertEqual(len(self.requests), 1)

    def test_noul_answer_to_a_choice_question_is_malformed(self):
        body = good_body()
        body['answers']['route'] = {'type': 'noul', 'noul': 0.7}
        out = self.ask(self.reply(body))
        self.assertEqual(out.status, 'malformed')
        self.assertEqual(len(self.requests), 1)

    def test_served_model_mismatch_is_malformed_without_retry(self):
        out = self.ask(self.reply(good_body(model='typesafe/jev-1.13-20260917')))
        self.assertEqual(out.status, 'malformed:served-model')
        self.assertEqual(len(self.requests), 1)
        self.assertEqual(out.served_model, 'typesafe/jev-1.13-20260917')

    def test_a_missing_served_model_is_a_mismatch(self):
        body = good_body()
        del body['model']
        self.assertEqual(self.ask(self.reply(body)).status, 'malformed:served-model')

    def test_a_dated_served_id_of_the_expected_model_is_accepted(self):
        out = self.ask(self.reply(good_body(model='openai/gpt-6-luna-decisions-20261006')))
        self.assertEqual(out.status, 'answered')
        self.assertEqual(out.served_model, 'openai/gpt-6-luna-decisions-20261006')

    def test_other_suffixes_on_the_expected_model_are_a_mismatch(self):
        for served in ('openai/gpt-6-luna-decisions-latest', 'openai/gpt-6-luna-decisions-2026100',
                       'openai/gpt-6-luna-decisions-20261006x', 'openai/gpt-6-luna-decisions2',
                       'other/openai/gpt-6-luna-decisions'):
            with self.subTest(served=served):
                self.assertEqual(self.ask(self.reply(good_body(model=served))).status, 'malformed:served-model')

    def test_timeout_is_retried_once_then_reported(self):
        def responder(request):
            raise httpx.ReadTimeout('slow')
        out = self.ask(responder)
        self.assertEqual(out.status, 'timeout')
        self.assertEqual((len(self.requests), out.attempts), (2, 2))

    def test_unavailability_is_retried_once_for_5xx_429_and_connection_failure(self):
        cases = {
            '503': lambda r: httpx.Response(503, json={'error': {'message': 'overloaded'}}),
            '500': lambda r: httpx.Response(500, text='boom'),
            '429': lambda r: httpx.Response(429, json={'error': {'message': 'slow down'}}),
        }
        for name, responder in cases.items():
            with self.subTest(name):
                self.requests.clear()
                out = self.ask(responder)
                self.assertEqual(out.status, 'unavailable')
                self.assertEqual((len(self.requests), out.attempts), (2, 2))

        def refuse(request):
            raise httpx.ConnectError(f'cannot connect, key {FAKE_KEY}')
        self.requests.clear()
        out = self.ask(refuse)
        self.assertEqual(out.status, 'unavailable')
        self.assertEqual((len(self.requests), out.attempts), (2, 2))
        self.assertNoCredentialLeak(out)

    def test_a_retry_that_succeeds_returns_the_answer(self):
        calls = []

        def responder(request):
            calls.append(1)
            if len(calls) == 1:
                return httpx.Response(503)
            return httpx.Response(200, json=good_body())
        out = self.ask(responder)
        self.assertEqual((out.status, out.attempts, len(calls)), ('answered', 2, 2))

    def test_no_endpoint_with_the_recorded_probe_404_falls_back_without_retry(self):
        out = self.ask(self.reply(PROBE_404_BODY, status=404))
        self.assertEqual(out.status, 'no-endpoint')
        self.assertEqual((len(self.requests), out.attempts, out.http_status), (1, 1, 404))

    def test_the_probe_404_message_is_what_no_endpoint_matches(self):
        message = PROBE_404_BODY['error']['message']
        self.assertIn('Zero data retention', message)
        self.assertTrue(transport.names_no_endpoint(message))
        self.assertFalse(transport.names_no_endpoint('model not found'))

    def test_a_5xx_carrying_the_data_policy_message_is_no_endpoint(self):
        body = {'error': {'message': 'No endpoints found matching your data policy', 'code': 503}}
        out = self.ask(self.reply(body, status=503))
        self.assertEqual(out.status, 'no-endpoint')
        self.assertEqual(len(self.requests), 1)

    def test_no_endpoint_is_recognised_whatever_the_status(self):
        for status in (400, 403, 404, 422, 502):
            with self.subTest(status=status):
                self.requests.clear()
                out = self.ask(self.reply(PROBE_404_BODY, status=status))
                self.assertEqual(out.status, 'no-endpoint')
                self.assertEqual(len(self.requests), 1)

    def test_missing_credential_is_unconfigured_and_sends_nothing(self):
        self.key_value = None
        out = self.ask(self.reply(good_body()))
        self.assertEqual(out.status, 'unconfigured')
        self.assertEqual((self.requests, out.attempts), ([], 0))
        status = classifier_status()
        self.assertEqual((status.configured, status.reason), (False, 'credential-missing'))

    def test_empty_credential_is_unconfigured(self):
        self.key_value = ''
        self.assertEqual(self.ask(self.reply(good_body())).status, 'unconfigured')
        self.assertEqual(self.requests, [])

    def test_missing_or_empty_cycle_classifier_role_is_unconfigured_without_an_exception(self):
        for name, edit in {
            'absent': lambda c: c['model_roles'].pop('cycle_classifier'),
            'empty-string': lambda c: c['model_roles'].__setitem__('cycle_classifier', ''),
            'null': lambda c: c['model_roles'].__setitem__('cycle_classifier', None),
            'empty-list': lambda c: c['model_roles'].__setitem__('cycle_classifier', []),
            'no-roles-block': lambda c: c.pop('model_roles'),
        }.items():
            with self.subTest(name):
                self.edit_registry(edit)
                status = classifier_status()
                self.assertEqual((status.configured, status.reason), (False, 'role-missing'))
                out = self.ask(self.reply(good_body()))
                self.assertEqual(out.status, 'unconfigured')
        self.assertEqual(self.requests, [])

    def test_role_naming_an_unknown_model_is_unconfigured(self):
        self.edit_registry(lambda c: c['model_roles'].__setitem__('cycle_classifier', 'no-such-model'))
        self.assertEqual(classifier_status().reason, 'registry-entry-invalid')
        self.assertEqual(self.ask(self.reply(good_body())).status, 'unconfigured')

    def test_classifier_status_is_configured_with_the_shipped_registry_and_a_credential(self):
        status = classifier_status()
        self.assertEqual((status.configured, status.reason), (True, None))
        self.assertEqual(self.requests, [])

    def test_a_401_is_malformed_with_its_status_class_and_no_retry(self):
        out = self.ask(self.reply({'error': {'message': 'invalid key'}}, status=401))
        self.assertEqual(out.status, 'malformed:http-401')
        self.assertEqual((len(self.requests), out.http_status), (1, 401))

    def test_a_403_is_malformed_with_its_status_class_and_no_retry(self):
        out = self.ask(self.reply({'error': {'message': 'not entitled'}}, status=403))
        self.assertEqual(out.status, 'malformed:http-403')
        self.assertEqual((len(self.requests), out.http_status), (1, 403))

    def test_an_unrecognised_4xx_is_malformed_without_retry(self):
        for status in (400, 402, 404, 408, 418, 422):
            with self.subTest(status=status):
                self.requests.clear()
                out = self.ask(self.reply({'error': {'message': 'nope'}}, status=status))
                self.assertEqual(out.status, 'malformed')
                self.assertEqual(len(self.requests), 1)

    def test_state_over_the_input_bound_is_refused_not_truncated(self):
        out = self.ask(self.reply(good_body()), state={'task': 'x' * 4001})
        self.assertEqual(out.status, 'over-input-bound')
        self.assertEqual((self.requests, out.attempts), ([], 0))
        self.assertEqual(self.key_reads, [], 'the ordering reads the credential after the size checks')

    def test_state_at_the_input_bound_is_sent(self):
        overhead = len(json.dumps({'task': ''}))
        state = {'task': 'x' * (decisions.MAX_STATE_CHARS - overhead)}
        self.assertEqual(len(json.dumps(state, ensure_ascii=False, sort_keys=True)), decisions.MAX_STATE_CHARS)
        self.assertEqual(self.ask(self.reply(good_body()), state=state).status, 'answered')

    def test_request_over_the_token_ceiling_is_refused(self):
        big = ChoiceQuestion(instructions='q' * 130_000, options=OPTIONS)
        out = self.ask(self.reply(good_body()), question=big)
        self.assertEqual(out.status, 'over-token-ceiling')
        self.assertEqual(self.requests, [])
        self.assertEqual(self.key_reads, [])

    def test_the_all_questions_ceiling_is_checked_with_the_copied_estimate(self):
        wire = {f'q{i}': {'type': 'choice', 'instructions': 'z' * 80_000, 'criteria': {'a': 'b'}} for i in range(4)}
        # Each question is about 20,000 tokens, under the 32,000 ceiling; four are 80,000, over 64,000.
        with self.assertRaises(transport.OverCeiling):
            transport.check_ceilings('{}', wire)
        transport.check_ceilings('{}', {'q0': wire['q0']})
        self.assertEqual(transport.estimate_tokens('x' * 8), 2)
        self.assertEqual(transport.estimate_tokens('x' * 9), 3)

    def test_scan_match_sends_nothing(self):
        out = self.ask(self.reply(good_body()), state={'task': f'use {FAKE_KEY} to log in'})
        self.assertEqual(out.status, 'scan-match')
        self.assertEqual((self.requests, out.attempts), ([], 0))
        self.assertNoCredentialLeak(out)

    def test_scan_match_in_the_question_text_sends_nothing(self):
        q = ChoiceQuestion(instructions=f'token {FAKE_KEY}', options=OPTIONS)
        self.assertEqual(self.ask(self.reply(good_body()), question=q).status, 'scan-match')
        self.assertEqual(self.requests, [])

    def test_a_clean_state_passes_the_scan_and_is_sent(self):
        self.assertEqual(self.ask(self.reply(good_body())).status, 'answered')
        self.assertEqual(len(self.requests), 1)

    def test_scanner_exception_sends_nothing(self):
        import secret_scan
        with mock.patch.object(secret_scan, 'scan_text', side_effect=RuntimeError(f'boom {FAKE_KEY}')):
            out = self.ask(self.reply(good_body()))
        self.assertEqual(out.status, 'scan-failure')
        self.assertEqual((self.requests, out.attempts), ([], 0))
        self.assertNoCredentialLeak(out)

    def test_scanner_import_failure_sends_nothing(self):
        with mock.patch.dict(sys.modules, {'secret_scan': None}):
            out = self.ask(self.reply(good_body()))
        self.assertEqual(out.status, 'scan-failure')
        self.assertEqual(self.requests, [])


class DeadlineTests(Harness):
    def test_a_call_near_the_deadline_is_clipped_to_the_time_left(self):
        seen = []

        def responder(request):
            seen.append(request.extensions['timeout'])
            return httpx.Response(200, json=good_body())
        now = [0.0]
        deadline = Deadline(seconds=60.0, clock=lambda: now[0])
        now[0] = 45.0
        out = self.ask(responder, deadline=deadline)
        self.assertEqual(out.status, 'answered')
        self.assertEqual(seen[0]['read'], 15.0)

    def test_a_call_with_ample_time_uses_the_per_call_timeout(self):
        seen = []

        def responder(request):
            seen.append(request.extensions['timeout'])
            return httpx.Response(200, json=good_body())
        self.ask(responder)
        self.assertEqual(seen[0]['read'], 20.0)

    def test_no_time_left_is_unavailable_with_zero_attempts(self):
        now = [0.0]
        deadline = Deadline(seconds=60.0, clock=lambda: now[0])
        now[0] = 61.0
        out = self.ask(self.reply(good_body()), deadline=deadline)
        self.assertEqual((out.status, out.attempts), ('unavailable', 0))
        self.assertEqual(self.requests, [])

    def test_a_retry_is_not_made_when_the_first_call_used_the_time(self):
        now = [0.0]
        deadline = Deadline(seconds=60.0, clock=lambda: now[0])

        def responder(request):
            now[0] = 60.0
            raise httpx.ReadTimeout('slow')
        out = self.ask(responder, deadline=deadline)
        self.assertEqual((out.status, out.attempts, len(self.requests)), ('timeout', 1, 1))

    def test_a_slow_drip_response_ends_by_the_bound(self):
        class Drip(httpx.SyncByteStream):
            def __iter__(self):
                for _ in range(40):
                    time.sleep(0.1)
                    yield b' '

        started = time.monotonic()
        out = self.ask(lambda r: httpx.Response(200, stream=Drip()), deadline=Deadline(seconds=0.5))
        elapsed = time.monotonic() - started
        self.assertEqual(out.status, 'timeout')
        self.assertLess(elapsed, 1.5)
        self.assertEqual(out.attempts, 1)


class ValidationTests(Harness):
    def test_probability_outside_the_unit_interval_is_malformed(self):
        for bad in (1.5, -0.1, 'high', None, True, float('inf')):
            with self.subTest(bad=bad):
                body = good_body()
                body['answers']['route']['probabilities']['dev'] = bad
                text = json.dumps(body).replace('Infinity', '1e999')
                out = self.ask(lambda r, text=text: httpx.Response(200, content=text.encode()))
                self.assertEqual(out.status, 'malformed')

    def test_probabilities_not_summing_to_one_are_recorded_not_refused(self):
        body = good_body(probabilities={'quick-fix': 0.1, 'iterate': 0.1, 'dev': 0.1, 'insufficient-information': 0.1})
        out = self.ask(self.reply(body))
        self.assertEqual(out.status, 'answered')
        self.assertAlmostEqual(sum(out.probabilities.values()), 0.4)

    def test_probabilities_keyed_outside_the_options_are_malformed(self):
        body = good_body(probabilities={'dev': 0.5, 'elsewhere': 0.5})
        self.assertEqual(self.ask(self.reply(body)).status, 'malformed')

    def test_probabilities_may_be_absent(self):
        body = good_body()
        del body['answers']['route']['probabilities']
        out = self.ask(self.reply(body))
        self.assertEqual((out.status, out.probabilities), ('answered', None))

    def test_confidence_outside_the_unit_interval_is_malformed_and_gates_nothing(self):
        self.assertEqual(self.ask(self.reply(good_body(confidence=1.2))).status, 'malformed')
        out = self.ask(self.reply(good_body(confidence=0.0)))
        self.assertEqual((out.status, out.confidence), ('answered', 0.0))
        body = good_body()
        del body['answers']['route']['confidence']
        out = self.ask(self.reply(body))
        self.assertEqual((out.status, out.confidence), ('answered', None))

    def test_a_missing_question_id_is_malformed(self):
        body = good_body(qid='other')
        body['answers'] = {}
        self.assertEqual(self.ask(self.reply(body)).status, 'malformed')

    def test_an_extra_question_id_is_malformed(self):
        body = good_body()
        body['answers']['unasked'] = {'type': 'choice', 'choice': 'dev'}
        self.assertEqual(self.ask(self.reply(body)).status, 'malformed')

    def test_a_wrongly_named_question_id_is_malformed(self):
        self.assertEqual(self.ask(self.reply(good_body(qid='other'))).status, 'malformed')

    def test_a_choice_outside_the_declared_options_is_malformed(self):
        self.assertEqual(self.ask(self.reply(good_body(choice='council'))).status, 'malformed')

    def test_usage_that_is_unreadable_is_dropped_not_refused(self):
        body = good_body()
        body['usage'] = 'lots'
        out = self.ask(self.reply(body))
        self.assertEqual((out.status, out.usage), ('answered', None))


class SecretHandlingTests(Harness):
    def test_the_credential_appears_in_no_outcome_exception_or_log(self):
        outcomes = [
            self.ask(self.reply(good_body())),
            self.ask(self.reply(PROBE_404_BODY, status=404)),
            self.ask(self.reply({'error': {'message': f'bad key {FAKE_KEY}'}}, status=401)),
            self.ask(self.reply({'error': {'message': f'bad {FAKE_KEY}'}}, status=400)),
            self.ask(lambda r: (_ for _ in ()).throw(httpx.ConnectError(f'url https://x?key={FAKE_KEY}'))),
            self.ask(self.reply(good_body(model=f'evil-{FAKE_KEY}'))),
            self.ask(self.reply(good_body()), state={'task': f'{FAKE_KEY}'}),
        ]
        self.assertGreater(len(self.log_records), 0, 'the transport logged nothing, so the log check is vacuous')
        self.assertNoCredentialLeak(*outcomes)

    def test_an_argument_error_raises_without_the_credential(self):
        with self.assertRaises(TypeError) as ctx:
            ask('not a mapping', 'route', QUESTION, deadline=Deadline())
        self.assertNoCredentialLeak(str(ctx.exception))
        with self.assertRaises(TypeError):
            ask(STATE, 'route', 'not a question', deadline=Deadline())


class ImportBoundaryTests(unittest.TestCase):
    @staticmethod
    def forbidden(name):
        return name == 'jev' or name.startswith('jev.') or name.startswith('tools.jev') or name == 'tools'

    def test_no_module_under_crux_scripts_imports_tools_jev(self):
        scanned = 0
        offenders = []
        for path in sorted(SCRIPTS.rglob('*.py')):
            try:
                tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
            except SyntaxError:
                continue        # a deliberately broken fixture, never imported
            scanned += 1
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or '']
                    if node.module == 'tools':
                        names += [f'tools.{a.name}' for a in node.names]
                offenders += [f'{path.relative_to(SCRIPTS)}: {n}' for n in names if self.forbidden(n)]
        self.assertGreater(scanned, 100)
        self.assertEqual(offenders, [])

    def test_the_scan_catches_a_jev_import(self):
        # Positive control: the same predicate flags the forbidden spellings.
        for name in ('jev', 'jev.client', 'tools.jev', 'tools.jev.client'):
            self.assertTrue(self.forbidden(name))
        self.assertFalse(self.forbidden('crux.decisions'))

    def test_crux_decisions_imports_from_the_plugin_tree(self):
        self.assertTrue(Path(decisions.__file__).resolve().is_relative_to(SCRIPTS.resolve()))
        self.assertTrue(Path(transport.__file__).resolve().is_relative_to(SCRIPTS.resolve()))
        self.assertEqual(Path(decisions.__file__).parent.name, 'decisions')


class RegistryTests(unittest.TestCase):
    def test_the_shipped_registry_declares_the_luna_decisions_entry_and_role(self):
        config = json.loads(REAL_REGISTRY.read_text())
        entry = config['models']['gpt-6-luna-decisions']
        self.assertEqual(config['model_roles']['cycle_classifier'], 'gpt-6-luna-decisions')
        self.assertEqual(entry['api_string'], EXPECTED_SERVED_MODEL)
        self.assertEqual(entry['type'], 'decisions')
        self.assertEqual(entry['data_collection'], 'deny')
        self.assertNotIn('zdr', entry)
        self.assertEqual(entry['timeout_seconds'], 20)
        self.assertEqual(entry['accepted_served_models'], [EXPECTED_SERVED_MODEL])
        self.assertEqual(entry['context_window'], 1_050_000)
        self.assertEqual(entry['cost'], {'input_per_1m': 0.1, 'output_per_1m': 0.0})

    def test_the_denial_set_is_read_only(self):
        with self.assertRaises(TypeError):
            decisions.REQUIRED_DENIALS['data_collection'] = 'allow'



class AskManyTests(Harness):
    """decisions.ask_many: several questions keyed by id in one request, each answer validated on its own."""

    SECOND = ChoiceQuestion(instructions='Is the change bounded?', options={'yes': 'bounded', 'no': 'unbounded'})

    def ask_many(self, responder, questions=None):
        questions = questions or {'route': QUESTION, 'bounded': self.SECOND}
        return decisions.ask_many(STATE, questions, deadline=Deadline(), client=self.client(responder))

    def two_answers(self, **over):
        body = good_body('dev')
        body['answers']['bounded'] = {'type': 'choice', 'choice': 'yes', 'confidence': 0.8}
        body['answers'].update(over)
        return body

    def test_several_questions_go_in_one_request_and_each_id_gets_its_answer(self):
        out = self.ask_many(self.reply(self.two_answers()))
        self.assertEqual(len(self.requests), 1)
        self.assertEqual(sorted(self.payload()['questions']), ['bounded', 'route'])
        self.assertEqual((out['route'].choice, out['bounded'].choice), ('dev', 'yes'))
        self.assertEqual((out['route'].request_id, out['bounded'].request_id), ('gen-dec-fake-1', 'gen-dec-fake-1'))
        self.assertIsNotNone(out['route'].usage, 'the request cost is reported on the first answered question')
        self.assertIsNone(out['bounded'].usage, 'and only there, so a sum counts one request once')

    def test_a_malformed_answer_falls_back_for_its_question_only(self):
        out = self.ask_many(self.reply(self.two_answers(bounded={'type': 'choice', 'choice': 'maybe'})))
        self.assertEqual((out['route'].status, out['bounded'].status), ('answered', 'malformed'))
        self.assertEqual(len(self.requests), 1, 'a malformed answer is not retried')

    def test_a_refused_or_missing_answer_falls_back_for_its_question_only(self):
        out = self.ask_many(self.reply(self.two_answers(bounded={'type': 'refusal'})))
        self.assertEqual((out['route'].status, out['bounded'].status), ('answered', 'refusal'))
        body = good_body('dev')
        self.requests.clear()
        out = self.ask_many(self.reply(body))
        self.assertEqual((out['route'].status, out['bounded'].status), ('answered', 'malformed'))

    def test_an_answer_for_an_id_that_was_not_asked_is_malformed_for_every_question(self):
        out = self.ask_many(self.reply(self.two_answers(extra={'type': 'choice', 'choice': 'yes'})))
        self.assertEqual({o.status for o in out.values()}, {'malformed'})

    def test_a_request_level_unavailability_is_retried_once_with_only_the_unanswered_questions(self):
        calls = []

        def responder(request):
            calls.append(1)
            return httpx.Response(503) if len(calls) == 1 else httpx.Response(200, json=self.two_answers())
        out = self.ask_many(responder)
        self.assertEqual(len(self.requests), 2)
        self.assertEqual(sorted(self.payload(1)['questions']), ['bounded', 'route'])
        self.assertEqual({(o.status, o.attempts) for o in out.values()}, {('answered', 2)})

    def test_one_question_is_the_single_ask(self):
        many = self.ask_many(self.reply(good_body('iterate')), {'route': QUESTION})['route']
        one = self.ask(self.reply(good_body('iterate')))
        self.assertEqual(many, one)
        self.assertEqual(self.payload(0), self.payload(1))

    def test_a_pre_send_refusal_applies_to_every_question_and_sends_nothing(self):
        self.key_value = None
        out = self.ask_many(self.reply(self.two_answers()))
        self.assertEqual({o.status for o in out.values()}, {'unconfigured'})
        self.assertEqual(self.requests, [])

    def test_bad_arguments_raise(self):
        for questions in ({}, {'': QUESTION}, {'route': 'not a question'}):
            with self.subTest(questions=questions):
                with self.assertRaises(TypeError):
                    decisions.ask_many(STATE, questions, deadline=Deadline())


def choice_answer(choice):
    return {'type': 'choice', 'choice': choice}


def body_for(answers, request_id='gen-dec-fake-1', cost=1e-05):
    return {'id': request_id, 'model': EXPECTED_SERVED_MODEL, 'answers': answers, 'usage': {'input_tokens': 10, 'cost': cost}}


class QuestionTypeAndBatchTests(Harness):
    """CYC-0099 build-c-batching: per-question fallback across a batch, the choice fallback for the predicate and
    score types, and requests bounded by MAX_QUESTIONS_PER_REQUEST with a retry asking only unanswered questions."""

    PREDICATE = decisions.PredicateQuestion('Does the change touch release distribution?', yes='It does.', no='It does not.',
                                            extra={'insufficient-information': 'The state does not decide it.'})
    SCORE = decisions.ScoreQuestion('Select the skills this task uses.',
                                    {'cycle': 'The cycle skill.', 'council': 'The council skill.', 'log-work': 'The log-work skill.'}, keep=2)

    def many(self, responder, questions):
        return decisions.ask_many(STATE, questions, deadline=Deadline(), client=self.client(responder))

    def test_one_malformed_and_one_refused_answer_keep_the_valid_answers(self):
        questions = {'a': QUESTION, 'b': QUESTION, 'c': QUESTION}
        answers = {'a': choice_answer('dev'), 'b': choice_answer('not-an-option'), 'c': {'type': 'refusal'}}
        out = self.many(self.reply(body_for(answers)), questions)
        self.assertEqual({k: o.status for k, o in out.items()}, {'a': 'answered', 'b': 'malformed', 'c': 'refusal'})
        self.assertEqual(out['a'].choice, 'dev')
        self.assertEqual(len(self.requests), 1, 'neither fallback causes another request')

    def test_a_predicate_is_sent_as_one_yes_no_choice(self):
        out = self.many(self.reply(body_for({'p': choice_answer('yes')})), {'p': self.PREDICATE})
        wire = self.payload()['questions']['p']
        self.assertEqual(wire['type'], 'choice')
        self.assertEqual(list(wire['criteria']), ['yes', 'no', 'insufficient-information'])
        self.assertEqual((out['p'].status, out['p'].choice), ('answered', 'yes'))

    def test_a_score_is_sent_as_one_yes_no_choice_per_candidate_and_keeps_yes_answers_in_candidate_order(self):
        answers = {'s#0': choice_answer('yes'), 's#1': choice_answer('no'), 's#2': choice_answer('yes')}
        out = self.many(self.reply(body_for(answers)), {'s': self.SCORE})
        wire = self.payload()['questions']
        self.assertEqual(sorted(wire), ['s#0', 's#1', 's#2'])
        self.assertEqual({q['type'] for q in wire.values()}, {'choice'})
        self.assertEqual(wire['s#1']['criteria'], {'yes': 'The council skill.', 'no': transport.SCORE_NO_TEXT})
        self.assertEqual((out['s'].status, out['s'].selected, out['s'].choice), ('answered', ('cycle', 'log-work'), None))
        self.assertEqual(out['s'].usage, {'input_tokens': 10, 'cost': 1e-05}, 'the request cost is counted once')

    def test_a_score_keeps_at_most_keep_candidates(self):
        answers = {f's#{n}': choice_answer('yes') for n in range(3)}
        out = self.many(self.reply(body_for(answers)), {'s': self.SCORE})
        self.assertEqual(out['s'].selected, ('cycle', 'council'))

    def test_a_score_with_one_failed_candidate_falls_back_and_selects_nothing(self):
        answers = {'s#0': choice_answer('yes'), 's#1': {'type': 'refusal'}, 's#2': choice_answer('yes'), 'q': choice_answer('iterate')}
        out = self.many(self.reply(body_for(answers)), {'s': self.SCORE, 'q': QUESTION})
        self.assertEqual((out['s'].status, out['s'].selected), ('refusal', None))
        self.assertEqual((out['q'].status, out['q'].choice), ('answered', 'iterate'), 'the other question keeps its answer')

    def test_questions_beyond_the_request_maximum_go_in_further_requests(self):
        limit = decisions.MAX_QUESTIONS_PER_REQUEST
        questions = {f'q{n:02d}': QUESTION for n in range(limit + 2)}

        def responder(request):
            asked = json.loads(request.content)['questions']
            return httpx.Response(200, json=body_for({q: choice_answer('dev') for q in asked}))
        out = self.many(responder, questions)
        self.assertEqual([len(self.payload(i)['questions']) for i in range(len(self.requests))], [limit, 2])
        self.assertEqual({o.status for o in out.values()}, {'answered'})

    def test_a_timed_out_request_is_retried_once_asking_only_its_unanswered_questions(self):
        limit = decisions.MAX_QUESTIONS_PER_REQUEST
        questions = {f'q{n:02d}': QUESTION for n in range(limit + 2)}
        timed_out = []

        def responder(request):
            asked = json.loads(request.content)['questions']
            if len(asked) == 2 and not timed_out:
                timed_out.append(1)
                raise httpx.ReadTimeout('slow')
            return httpx.Response(200, json=body_for({q: choice_answer('dev') for q in asked}))
        out = self.many(responder, questions)
        sizes = [sorted(self.payload(i)['questions']) for i in range(len(self.requests))]
        self.assertEqual(len(self.requests), 3, 'one first request per chunk and one retry')
        self.assertEqual(sizes[1], sizes[2], 'the retry asks only the timed-out request\'s questions')
        self.assertEqual(sizes[2], [f'q{limit:02d}', f'q{limit + 1:02d}'])
        self.assertEqual({o.status for o in out.values()}, {'answered'})
        self.assertEqual(out[f'q{limit:02d}'].attempts, 2)
        self.assertEqual(out['q00'].attempts, 1)

    def test_a_timeout_after_the_retry_falls_back_without_erasing_other_answers(self):
        limit = decisions.MAX_QUESTIONS_PER_REQUEST
        questions = {f'q{n:02d}': QUESTION for n in range(limit + 1)}

        def responder(request):
            asked = json.loads(request.content)['questions']
            if len(asked) == 1:
                raise httpx.ReadTimeout('slow')
            return httpx.Response(200, json=body_for({q: choice_answer('dev') for q in asked}))
        out = self.many(responder, questions)
        self.assertEqual(out[f'q{limit:02d}'].status, 'timeout')
        self.assertEqual(sum(o.status == 'answered' for o in out.values()), limit)
        self.assertEqual(len(self.requests), 3)

    def test_bad_question_types_raise(self):
        for question in (decisions.PredicateQuestion('x', yes='a', no='b', extra={'yes': 'c'}),
                         decisions.ScoreQuestion('x', {}, keep=1), decisions.ScoreQuestion('x', {'a': 'b'}, keep=0)):
            with self.subTest(question=question):
                with self.assertRaises(TypeError):
                    decisions.ask_many(STATE, {'q': question}, deadline=Deadline())
        with self.assertRaises(TypeError):
            decisions.ask_many(STATE, {'q#1': QUESTION}, deadline=Deadline())


class InputBoundTests(Harness):
    """A named central policy replaces caller-selected numeric caps."""

    def bounds(self, values):
        config = json.loads(self.path.read_text())
        key = config['model_roles']['cycle_classifier']
        config['models'][key]['input_bounds'] = values
        self.write_registry(config)

    def test_a_named_bound_and_default_and_mixed_minimum(self):
        self.bounds({'handoff-completeness': 9000, 'public-document-relevance': 5000})
        self.assertEqual(decisions.input_bound(), 4000)
        self.assertEqual(decisions.input_bound(('unknown-kind',)), 4000)
        self.assertEqual(decisions.input_bound(('handoff-completeness',)), 9000)
        self.assertEqual(decisions.input_bound(('handoff-completeness', 'public-document-relevance')), 5000)

    def test_kind_selects_bound_without_a_numeric_callsite_override(self):
        self.bounds({'handoff-completeness': 9000})
        state = {'report': 'x' * 5000}
        client = self.client(self.reply(good_body()))
        out = decisions.ask_many(state, {'route': QUESTION}, kinds=('handoff-completeness',), deadline=Deadline(), client=client)
        self.assertEqual(out['route'].status, 'answered')
        self.assertEqual(len(self.requests), 1)
        out = decisions.ask_many(state, {'route': QUESTION}, deadline=Deadline(), client=client)
        self.assertEqual(out['route'].status, 'over-input-bound')
        self.assertEqual(len(self.requests), 1, 'default cap did not refuse before send')

    def test_invalid_central_bounds_disable_classifier(self):
        for value in ({'x': 12001}, {'x': 0}, {'x': True}, {'x': 1.5}, {'x': '9000'}, []):
            with self.subTest(value=value):
                self.bounds(value)
                self.assertFalse(classifier_status().configured)

    def test_configuration_fingerprint_contains_endpoint_model_and_policy_not_credentials(self):
        basis = decisions.classifier_basis()
        self.assertEqual(basis['model'], EXPECTED_SERVED_MODEL)
        self.assertEqual(basis['endpoint'], URL)
        self.assertEqual(basis['denials'], dict(decisions.REQUIRED_DENIALS))
        self.assertNotIn(FAKE_KEY, json.dumps(basis))
        self.assertEqual(self.key_reads, [], 'fingerprinting read a gateway credential')

    def test_optional_selection_counts_are_central_bounded_and_fingerprinted(self):
        config = json.loads(self.path.read_text())
        key = config['model_roles']['cycle_classifier']
        for count in (0, 2, 8):
            config['models'][key].update(context_keep=count, focused_test_keep=count)
            self.write_registry(config)
            self.assertEqual(decisions.classifier_basis()['context_keep'], count)
            self.assertEqual(decisions.classifier_basis()['focused_test_keep'], count)
        for count in (-1, 9, True, '3', 1.5):
            with self.subTest(count=count):
                config['models'][key]['context_keep'] = count
                self.write_registry(config)
                self.assertFalse(classifier_status().configured)


if __name__ == '__main__':
    unittest.main()
