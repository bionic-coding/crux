"""Regression tests for the LLM router's per-model request shaping.

Every model resolves through one OpenAI-compatible gateway at OpenRouter
(ADR-0087), so the shaping rules are now properties of ONE request builder
rather than of three per-provider branches. What is locked in here:

1. Reasoning-effort pinning — the two `claude-fable-5.1*` registry entries share
   one api_string but pin different efforts (high vs medium for council seats),
   and `gpt-5.6-sol-low` is the same effort-alias pattern on the OpenAI side.
   The pin rides the gateway's top-level `reasoning_effort` field, so no call
   depends on a provider-specific response branch.
2. `supports_temperature: false` — the nine reject-set models (Fable 5.1 x2,
   Opus 5, Sonnet 5, GPT-6 Astra, and the GPT-5.6 SKUs Sol/Sol-low/Terra/Luna) reject the
   `temperature` param; the builder must omit it for them and keep sending it
   for models that accept it (Haiku 4.5). NOTE: Sonnet 5 REJECTS temperature —
   a behavior change from the retired Sonnet 4.6, which accepted it.
3. One address for every model — every entry posts to the same
   `/chat/completions` URL under `Authorization: Bearer`. The per-endpoint
   `openai_endpoint` split is gone; a second URL appearing here would mean a
   second inference path survived the consolidation.
4. Per-seat serving-provider pinning — the three council seats carry
   `provider.only`, the control that keeps them on three distinct serving hosts
   (the response-integrity bound the decision records).

NOTE: the GPT-5.5 and GPT-5.5-pro identifiers that briefly existed on an
incoming branch were intentionally REMOVED as part of the GPT-5.6 baseline
switch — a deliberate compatibility break. They are never aliased to any
GPT-5.6 SKU and do not appear anywhere in this suite.

Run under uv (httpx required): uv run python3 -m unittest discover crux/scripts/tests
"""

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

try:
    import httpx  # noqa: F401
    HAVE_HTTPX = True
except ImportError:
    HAVE_HTTPX = False

# The nine registry entries whose API rejects a non-default temperature.
TEMPERATURE_REJECT_SET = (
    'claude-fable-5.1', 'claude-fable-5.1-medium', 'claude-opus-5',
    'claude-sonnet-5', 'gpt-5.6-sol', 'gpt-5.6-sol-low',
    'gpt-5.6-terra', 'gpt-5.6-luna', 'gpt-6-astra',
)

# Serving-provider slugs read from each seat's OpenRouter endpoints data
# (Astra verified 2026-09-04). Three seats, three distinct hosts.
COUNCIL_SEAT_SERVING_PROVIDERS = {
    'gpt-6-astra': ['openai'],
    'claude-fable-5.1': ['anthropic'],
    'gemini-3.1-pro-preview': ['google-ai-studio'],
}


@unittest.skipUnless(HAVE_HTTPX, "httpx not installed — run under uv")
class LlmRouterRegistryTests(unittest.TestCase):
    """Config-level invariants — no network, no API keys."""

    @classmethod
    def setUpClass(cls):
        from crux.core import llm_caller
        cls.llm = llm_caller
        cls.cfg = llm_caller.load_router_config()

    def test_every_role_resolves_to_a_registered_model(self):
        registry = set(self.cfg['models'])
        for role, value in self.cfg['model_roles'].items():
            if role.startswith('_'):
                continue
            names = value if isinstance(value, list) else [value]
            for name in names:
                self.assertIn(name, registry, f"model_roles.{role} -> {name} not in registry")

    def test_fable_entries_share_sku_with_distinct_effort(self):
        # claude-fable-5.1 and claude-fable-5.1-medium are both ACTIVE (not
        # disabled) in the GPT-5.6 baseline lineup and share one api_string
        # but pin different reasoning efforts (high vs medium).
        high = self.llm.get_model_config('claude-fable-5.1')
        medium = self.llm.get_model_config('claude-fable-5.1-medium')
        self.assertEqual(high.api_string, 'anthropic/claude-fable-5.1')
        self.assertEqual(medium.api_string, 'anthropic/claude-fable-5.1')
        self.assertEqual(high.effort, 'high')
        self.assertEqual(medium.effort, 'medium')

    def test_sol_low_shares_sku_with_low_effort(self):
        # The fast-lane arbiter is Sol pinned to low effort (effort-alias, same
        # SKU) — the OpenAI analogue of the claude-fable-5.1 / -medium pattern.
        sol = self.llm.get_model_config('gpt-5.6-sol')
        sol_low = self.llm.get_model_config('gpt-5.6-sol-low')
        self.assertEqual(sol.api_string, 'openai/gpt-5.6-sol')
        self.assertEqual(sol_low.api_string, 'openai/gpt-5.6-sol')
        self.assertEqual(sol_low.effort, 'low')
        self.assertIsNone(sol.effort)

    def test_temperature_support_flags_match_live_verification(self):
        accepts = {'claude-haiku-4-5-20251001'}
        for name in TEMPERATURE_REJECT_SET:
            self.assertFalse(
                self.llm.get_model_config(name).supports_temperature,
                f"{name} must have supports_temperature: false (API rejects the param)")
        for name in accepts:
            self.assertTrue(self.llm.get_model_config(name).supports_temperature)

    def test_every_model_addresses_the_one_gateway(self):
        """Verbatim-slug pinning: every api_string is a namespaced OpenRouter id
        under one base_url. A bare slug here would be a model the gateway cannot
        resolve; a second base_url would be a surviving second inference path."""
        for name in self.cfg['models']:
            cfg = self.llm.get_model_config(name)
            with self.subTest(model=name):
                self.assertEqual(cfg.base_url, 'https://openrouter.ai/api/v1')
                self.assertIn('/', cfg.api_string,
                              f"{name}: api_string must be a namespaced OpenRouter id")

    def test_providers_table_is_exactly_openrouter(self):
        """ADR-0087 postcondition: one gateway means one providers entry.

        A second entry would be a surviving second inference path — the exact
        fragmentation the consolidation removed. Pinned as an equality, not a
        membership check, so ADDING a provider fails here rather than passing
        because openrouter is still present beside it.
        """
        self.assertEqual(list(self.cfg['providers']), ['openrouter'])

    def test_council_seats_pin_their_serving_providers(self):
        for name, expected in COUNCIL_SEAT_SERVING_PROVIDERS.items():
            with self.subTest(model=name):
                self.assertEqual(list(self.llm.get_model_config(name).serving_providers),
                                 expected)

    def test_council_seats_resolve_to_distinct_serving_providers(self):
        """The diversity control. Three seats collapsing onto one host would
        undo the vendor diversity the three-seat council exists to buy."""
        hosts = [tuple(self.llm.get_model_config(n).serving_providers)
                 for n in COUNCIL_SEAT_SERVING_PROVIDERS]
        self.assertEqual(len(set(hosts)), 3, f"seats share a serving provider: {hosts}")

    def test_council_weight_covers_weighted_seats(self):
        # Weighted council seats resolve against the GPT-5.6 baseline lineup:
        # anthropic_council -> claude-opus-5 (1.5), openai_top -> gpt-6-astra
        # (1.4, replacing the stale/removed gpt-5.5), google_top ->
        # gemini-3.1-pro-preview (1.3).
        from crux.council.council import _get_model_weight
        self.assertEqual(_get_model_weight('claude-opus-5'), 1.5)
        self.assertEqual(_get_model_weight('gpt-6-astra'), 1.4)
        self.assertEqual(_get_model_weight('gemini-3.1-pro-preview'), 1.3)


@unittest.skipUnless(HAVE_HTTPX, "httpx not installed — run under uv")
class LlmRouterPayloadTests(unittest.TestCase):
    """Request-payload shaping via a fake HTTP client — no network."""

    def setUp(self):
        from crux.core import llm_caller
        self.llm = llm_caller
        self.captured = []
        captured = self.captured

        class FakeResponse:
            status_code = 200

            def raise_for_status(self):
                pass

            def json(self):
                return {'choices': [{'finish_reason': 'stop',
                                     'message': {'content': 'ok'}}]}

        class FakeClient:
            def __init__(self, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def post(self, url, headers=None, json=None, **kwargs):
                captured.append((url, headers or {}, json))
                return FakeResponse()

        self._real_client = llm_caller.httpx.Client
        llm_caller.httpx.Client = FakeClient
        self._env_backup = os.environ.get('OPENROUTER_API_KEY')
        os.environ['OPENROUTER_API_KEY'] = 'sk-or-test-dummy'

    def tearDown(self):
        self.llm.httpx.Client = self._real_client
        if self._env_backup is None:
            os.environ.pop('OPENROUTER_API_KEY', None)
        else:
            os.environ['OPENROUTER_API_KEY'] = self._env_backup

    def _request(self, model):
        self.captured.clear()
        self._last_return = self.llm.call_model(model, 'hi', max_tokens=64)
        return self.captured[0]

    def _payload(self, model):
        return self._request(model)[2]

    # -- address + auth ------------------------------------------------------

    def test_every_model_posts_to_one_gateway_url(self):
        urls = set()
        for model in self.llm.list_available_models():
            urls.add(self._request(model)[0])
        self.assertEqual(urls, {'https://openrouter.ai/api/v1/chat/completions'},
                         "every model must post to the one gateway endpoint")

    def test_auth_is_bearer_and_key_never_reaches_the_url(self):
        url, headers, _ = self._request('claude-opus-5')
        self.assertEqual(headers.get('Authorization'), 'Bearer sk-or-test-dummy')
        self.assertNotIn('sk-or-test-dummy', url)

    # -- reasoning effort ----------------------------------------------------

    def test_effort_pinned_entries_send_reasoning_effort(self):
        for model, effort in (('claude-fable-5.1', 'high'),
                              ('claude-fable-5.1-medium', 'medium'),
                              ('gpt-5.6-sol-low', 'low')):
            with self.subTest(model=model):
                payload = self._payload(model)
                self.assertEqual(payload.get('reasoning_effort'), effort)

    def test_unpinned_entries_omit_reasoning_effort(self):
        """Plain Sol and Opus 5 pin no effort — the server default stands, and
        an emitted field would silently override it."""
        for model in ('gpt-5.6-sol', 'claude-opus-5'):
            with self.subTest(model=model):
                self.assertNotIn('reasoning_effort', self._payload(model))

    def test_effort_aliases_send_the_same_model_id(self):
        self.assertEqual(self._payload('gpt-5.6-sol')['model'], 'openai/gpt-5.6-sol')
        self.assertEqual(self._payload('gpt-5.6-sol-low')['model'], 'openai/gpt-5.6-sol')

    # -- temperature ---------------------------------------------------------

    def test_reject_set_models_omit_temperature(self):
        for model in TEMPERATURE_REJECT_SET:
            with self.subTest(model=model):
                self.assertNotIn('temperature', self._payload(model))

    def test_accepting_model_still_sends_temperature(self):
        self.assertIn('temperature', self._payload('claude-haiku-4-5-20251001'))

    # -- serving-provider pinning -------------------------------------------

    def test_council_seats_send_provider_only(self):
        for model, expected in COUNCIL_SEAT_SERVING_PROVIDERS.items():
            with self.subTest(model=model):
                provider = self._payload(model).get('provider')
                self.assertEqual(provider, {'only': expected, 'data_collection': 'deny'})

    def test_non_seat_models_send_no_host_pin_but_still_deny_collection(self):
        """A non-seat model has no serving-provider set, and that is the ONLY
        half it omits.

        This assertion used to read `assertNotIn('provider', ...)`, which pinned
        a payload carrying no retention control at all: `data_collection` lived
        inside the `provider` object that only a pinned entry emitted, so every
        unpinned model — most of the registry — routed with collection allowed.
        The host pin is per-seat; the denial is universal.
        """
        provider = self._payload('gemini-3.5-flash').get('provider')
        self.assertEqual(provider, {'data_collection': 'deny'})

    # -- body shape + return -------------------------------------------------

    def test_messages_carry_system_and_user_roles(self):
        self.captured.clear()
        self.llm.call_model('claude-opus-5', 'hi', system='Be terse.', max_tokens=64)
        payload = self.captured[0][2]
        self.assertEqual(payload['messages'],
                         [{'role': 'system', 'content': 'Be terse.'},
                          {'role': 'user', 'content': 'hi'}])
        self.assertEqual(payload['max_tokens'], 64)

    def test_response_text_is_surfaced(self):
        self._request('gpt-5.6-sol')
        self.assertEqual(self._last_return, 'ok')


@unittest.skipUnless(HAVE_HTTPX, "httpx not installed — run under uv")
class GatewayTimeoutTests(unittest.TestCase):
    """`gateway_timeout_seconds` reads the registry override and is memoized.

    The scalar is cached like the model-roles map and cleared by the same
    `invalidate_model_cache`, so a config edit only takes effect after that
    clear. Each test clears the cache around its mocked config so it neither
    reads a value another test memoized nor leaves one behind.
    """

    def setUp(self):
        from crux.core import llm_caller
        self.llm = llm_caller
        self.llm.gateway_timeout_seconds.cache_clear()
        self.addCleanup(self.llm.gateway_timeout_seconds.cache_clear)

    def test_registry_override_is_read(self):
        with mock.patch.object(self.llm, 'load_router_config',
                               return_value={'request_timeout_seconds': 42}):
            self.llm.gateway_timeout_seconds.cache_clear()
            self.assertEqual(self.llm.gateway_timeout_seconds(), 42.0)

    def test_absent_override_falls_back_to_the_default(self):
        with mock.patch.object(self.llm, 'load_router_config', return_value={}):
            self.llm.gateway_timeout_seconds.cache_clear()
            self.assertEqual(self.llm.gateway_timeout_seconds(),
                             self.llm.DEFAULT_TIMEOUT_SECONDS)

    def test_cache_clear_invalidates_a_stale_value(self):
        """Without the clear, a config edit is invisible; with it, it lands."""
        with mock.patch.object(self.llm, 'load_router_config',
                               return_value={'request_timeout_seconds': 10}):
            self.llm.gateway_timeout_seconds.cache_clear()
            self.assertEqual(self.llm.gateway_timeout_seconds(), 10.0)
        with mock.patch.object(self.llm, 'load_router_config',
                               return_value={'request_timeout_seconds': 99}):
            # The memoized 10 persists until the cache is cleared.
            self.assertEqual(self.llm.gateway_timeout_seconds(), 10.0)
            self.llm.invalidate_model_cache()
            self.assertEqual(self.llm.gateway_timeout_seconds(), 99.0)


@unittest.skipUnless(HAVE_HTTPX, "httpx not installed — run under uv")
class ParseGatewayResponseTests(unittest.TestCase):
    """`parse_gateway_response` degrades a malformed body, never crashes on it.

    A missing or non-object `choices[0]` is not a refusal and must not raise:
    the caller (transcribe-video's main()) catches ValueError/GatewayError, not
    AttributeError, so an uncaught `.get` on a non-dict would escape as a
    traceback instead of the reported empty completion.
    """

    def setUp(self):
        from crux.core import llm_caller
        self.llm = llm_caller

    def test_empty_choices_returns_empty_string(self):
        self.assertEqual(self.llm.parse_gateway_response({'choices': []}, 'm'), "")
        self.assertEqual(self.llm.parse_gateway_response({}, 'm'), "")

    def test_non_dict_choice_returns_empty_not_attributeerror(self):
        for body in ({'choices': ['oops']}, {'choices': [None]}, {'choices': [42]}):
            with self.subTest(body=body):
                self.assertEqual(self.llm.parse_gateway_response(body, 'm'), "")

    def test_a_well_formed_choice_still_surfaces_its_content(self):
        body = {'choices': [{'finish_reason': 'stop',
                             'message': {'content': 'hello'}}]}
        self.assertEqual(self.llm.parse_gateway_response(body, 'm'), 'hello')


if __name__ == '__main__':
    unittest.main()
