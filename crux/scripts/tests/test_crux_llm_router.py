"""Regression tests for the LLM router's per-model request shaping.

Every model resolves through one OpenAI-compatible gateway at OpenRouter
(ADR-0087), so the shaping rules are now properties of ONE request builder
rather than of three per-provider branches. What is locked in here:

1. Reasoning-effort pinning — the Opus 5.5 registry entries share one API model
   while councils use xhigh and release documents use high effort. Fable's
   retained high and medium entries and `gpt-6-sol-low` use the same pattern.
   The pin rides the gateway's top-level `reasoning_effort` field, so no call
   depends on a provider-specific response branch.
2. `supports_temperature: false` — the reject-set models (Fable 5.1 x2,
   Opus 5, Sonnet 5, Opus 5.5 x2, GPT-6 Astra, Sol, Sol-low and Luna) reject
   the `temperature` param; the builder must omit it for them and keep sending it
   for models that accept it (Haiku 4.5). NOTE: Sonnet 5 REJECTS temperature —
   a behavior change from the retired Sonnet 4.6, which accepted it.
3. One address for every text model — every `type: text` entry posts to the same
   `/chat/completions` URL under `Authorization: Bearer`. The per-endpoint
   `openai_endpoint` split is gone; a second URL appearing here would mean a
   second inference path survived the consolidation.
4. Per-seat serving-provider pinning — the three council seats carry
   `provider.only`, the control that keeps them on three distinct serving hosts
   (the response-integrity bound the decision records).

NOTE: the GPT-5.5 and GPT-5.5-pro identifiers that briefly existed on an
incoming branch were intentionally REMOVED as part of the GPT-5.6 baseline
switch — a deliberate compatibility break. They are never aliased to any
GPT-5.6 SKU and do not appear anywhere in this suite. The GPT-5.6 keys
(`gpt-5.6-sol`, `gpt-5.6-sol-low`, `gpt-5.6-terra`, `gpt-5.6-luna`) and
`gpt-image-2` were in turn REMOVED by the GPT-6 switch, the same deliberate
compatibility break: they are never aliased, and GPT-6 has no Terra. They
appear in this suite only as the removed keys `RemovedGpt56KeysTests` asserts
raise.

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

# Registry entries whose API rejects a non-default temperature. jev-1.13 also
# rejects one and is covered by its own suite.
TEMPERATURE_REJECT_SET = (
    'claude-fable-5.1', 'claude-fable-5.1-medium', 'claude-opus-5',
    'claude-sonnet-5', 'gpt-6-sol', 'gpt-6-sol-low', 'gpt-6-luna',
    'gpt-6-astra', 'claude-opus-5.5', 'claude-opus-5.5-xhigh',
)

# Serving-provider slugs read from each seat's OpenRouter endpoints data
# (Astra verified 2026-09-04). Three seats, three distinct hosts.
COUNCIL_SEAT_SERVING_PROVIDERS = {
    'gpt-6-astra': ['openai'],
    'claude-opus-5.5-xhigh': ['anthropic'],
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
        # disabled) in the GPT-6 baseline lineup and share one api_string
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
        sol = self.llm.get_model_config('gpt-6-sol')
        sol_low = self.llm.get_model_config('gpt-6-sol-low')
        self.assertEqual(sol.api_string, 'openai/gpt-6-sol')
        self.assertEqual(sol_low.api_string, 'openai/gpt-6-sol')
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
        # Weighted council seats resolve against the GPT-6 baseline lineup:
        # anthropic_council -> claude-opus-5 (1.5), openai_top -> gpt-6-astra
        # (1.4, replacing the stale/removed gpt-5.5), google_top ->
        # gemini-3.1-pro-preview (1.3).
        from crux.council.council import _get_model_weight
        self.assertEqual(_get_model_weight('claude-opus-5'), 1.5)
        self.assertEqual(_get_model_weight('gpt-6-astra'), 1.4)
        self.assertEqual(_get_model_weight('gemini-3.1-pro-preview'), 1.3)


# The five keys the GPT-6 switch removed. A deliberate compatibility break:
# none is aliased, and a caller naming one gets `ValueError: Unknown model`.
REMOVED_GPT56_KEYS = (
    'gpt-5.6-sol', 'gpt-5.6-sol-low', 'gpt-5.6-terra', 'gpt-5.6-luna',
    'gpt-image-2',
)


def _role_names(value):
    return value if isinstance(value, list) else [value]


@unittest.skipUnless(HAVE_HTTPX, "httpx not installed — run under uv")
class Gpt6RoleAndRegistryTests(unittest.TestCase):
    """The GPT-6 switch re-points roles and never renames a key.

    Every former Terra role and every former Sol role resolves to `gpt-6-sol`,
    because GPT-6 has no Terra and no Terra workload moves to Luna.
    """

    @classmethod
    def setUpClass(cls):
        from crux.core import llm_caller
        cls.llm = llm_caller
        cls.cfg = llm_caller.load_router_config()

    # (a) the six moved role slots
    def test_single_openai_roles_resolve_to_gpt_6_sol(self):
        for role in ('openai_chat', 'think_medium', 'vision'):
            with self.subTest(role=role):
                self.assertEqual(self.llm.get_default_model(role), 'gpt-6-sol')

    def test_list_roles_carry_gpt_6_sol_first(self):
        expected = {
            'council_default': ['gpt-6-sol', 'gemini-3.1-pro-preview',
                                'claude-opus-5.5-xhigh'],
            'council_code': ['gpt-6-sol', 'claude-sonnet-5',
                             'gemini-3.1-pro-preview'],
            'recursive_improve': ['gpt-6-sol', 'claude-opus-5',
                                  'gemini-3.1-pro-preview'],
        }
        for role, models in expected.items():
            with self.subTest(role=role):
                self.assertEqual(list(self.llm.get_default_models(role)), models)

    def test_openai_top_stays_on_astra(self):
        self.assertEqual(self.llm.get_default_model('openai_top'), 'gpt-6-astra')

    # (b) nothing moves to Luna
    def test_no_role_resolves_to_gpt_6_luna(self):
        for role, value in self.cfg['model_roles'].items():
            if role.startswith('_'):
                continue
            with self.subTest(role=role):
                self.assertNotIn('gpt-6-luna', _role_names(value))

    # (c) the removed keys are gone, not aliased
    def test_removed_keys_raise_unknown_model(self):
        for key in REMOVED_GPT56_KEYS:
            with self.subTest(key=key):
                with self.assertRaisesRegex(ValueError, 'Unknown model'):
                    self.llm.get_model_config(key)

    def test_no_role_names_a_removed_key(self):
        for role, value in self.cfg['model_roles'].items():
            if role.startswith('_'):
                continue
            for key in REMOVED_GPT56_KEYS:
                with self.subTest(role=role, key=key):
                    self.assertNotIn(key, _role_names(value))

    # (d) every OpenAI entry names its own slug: no key redirects to another model
    def test_every_openai_entry_names_its_own_slug(self):
        openai_keys = [k for k, v in self.cfg['models'].items()
                       if v['api_string'].startswith('openai/')]
        self.assertIn('gpt-6-sol', openai_keys)  # the filter selects something
        for key in openai_keys:
            with self.subTest(key=key):
                self.assertEqual(self.cfg['models'][key]['api_string'],
                                 'openai/' + key.removesuffix('-low'))

    # (e) the new entries carry the verified metadata
    def _assert_entry(self, key, expected, absent=()):
        entry = self.llm.get_model_info(key)
        for field, value in expected.items():
            with self.subTest(key=key, field=field):
                self.assertEqual(entry.get(field), value)
        for field in absent:
            with self.subTest(key=key, absent=field):
                self.assertNotIn(field, entry)

    def test_gpt_6_sol_entry_metadata(self):
        self._assert_entry('gpt-6-sol', {
            'api_string': 'openai/gpt-6-sol',
            'serving_providers': ['openai'],
            'display_name': 'GPT-6 Sol',
            'supports_temperature': False,
            'type': 'text',
            'tier': 'frontier_max',
            'latency_profile': 'slow',
            'context_window': 1050000,
            'max_output_tokens': 128000,
            'cost': {'input_per_1m': 2.0, 'output_per_1m': 10.0,
                     'cached_input_per_1m': 0.2},
        }, absent=('effort',))
        cfg = self.llm.get_model_config('gpt-6-sol')
        self.assertEqual(cfg.serving_providers, ('openai',))
        self.assertIsNone(cfg.effort)

    def test_gpt_6_sol_low_entry_metadata(self):
        self._assert_entry('gpt-6-sol-low', {
            'api_string': 'openai/gpt-6-sol',
            'display_name': 'GPT-6 Sol (low effort)',
            'effort': 'low',
            'supports_temperature': False,
            'type': 'text',
            'tier': 'frontier_max',
            'context_window': 1050000,
            'max_output_tokens': 128000,
            'cost': {'input_per_1m': 2.0, 'output_per_1m': 10.0,
                     'cached_input_per_1m': 0.2},
        }, absent=('serving_providers',))

    def test_gpt_6_luna_entry_metadata(self):
        self._assert_entry('gpt-6-luna', {
            'api_string': 'openai/gpt-6-luna',
            'display_name': 'GPT-6 Luna',
            'supports_temperature': False,
            'type': 'text',
            'tier': 'fast',
            'context_window': 1050000,
            'max_output_tokens': 128000,
            'cost': {'input_per_1m': 0.1, 'output_per_1m': 0.5,
                     'cached_input_per_1m': 0.01},
        }, absent=('effort', 'serving_providers'))

    def test_gpt_image_2_5_sunburst_entry_metadata(self):
        self._assert_entry('gpt-image-2.5-sunburst', {
            'api_string': 'openai/gpt-image-2.5-sunburst',
            'display_name': 'GPT Image 2.5 Sunburst',
            'type': 'image_generation',
            'tier': 'image_gen',
            'supports_temperature': True,
            'context_window': 400000,
            'max_output_tokens': 360000,
            'cost': {'input_per_1m': 8.0, 'output_per_1m': 8.0,
                     'cached_input_per_1m': 2.0},
            'judge_eligible': False,
        }, absent=('output_formats', 'max_resolution', 'latency_profile',
                   'effort', 'serving_providers'))

    def test_no_entry_pins_reasoning_effort_none(self):
        # GPT-6 allows function calling on Chat Completions only at effort
        # `none`; crux sends no tools, so no entry may pin `none` to unlock it.
        for key, entry in self.cfg['models'].items():
            with self.subTest(key=key):
                self.assertNotEqual(entry.get('effort'), 'none')


@unittest.skipUnless(HAVE_HTTPX, "httpx not installed — run under uv")
class OpusRoutingTests(unittest.TestCase):
    """Councils use Opus 5.5 at xhigh; release documents retain high effort."""

    @classmethod
    def setUpClass(cls):
        from crux.core import llm_caller
        cls.llm = llm_caller
        cls.cfg = llm_caller.load_router_config()

    def test_release_docs_role_resolves_to_opus_5_5(self):
        self.assertEqual(self.llm.get_default_model('release_docs'), 'claude-opus-5.5')

    def test_anthropic_top_routes_to_xhigh_opus(self):
        self.assertEqual(self.llm.get_default_model('anthropic_top'), 'claude-opus-5.5-xhigh')
        self.assertEqual(self.llm.get_default_model('council_arbiter'), 'claude-opus-5.5-xhigh')
        self.assertEqual(self.llm.get_default_model('think_deep'), 'claude-fable-5.1')

    def test_sync_council_default_anthropic_seat_uses_xhigh_opus(self):
        self.assertEqual(
            list(self.llm.get_default_models('council_default')),
            ['gpt-6-sol', 'gemini-3.1-pro-preview', 'claude-opus-5.5-xhigh'],
        )
        self.assertEqual(self.llm.get_default_model('anthropic_council'), 'claude-opus-5')

    def test_weighted_vote_follows_the_repointed_role(self):
        from crux.council.council import _get_model_weight, MODEL_WEIGHTS
        self.assertEqual(MODEL_WEIGHTS, {
            'anthropic_top': 1.5, 'anthropic_council': 1.5,
            'google_top': 1.3, 'openai_top': 1.4,
        })
        self.assertEqual(_get_model_weight('claude-fable-5.1'), 1.0)
        self.assertEqual(_get_model_weight('claude-opus-5'), 1.5)
        self.assertEqual(_get_model_weight('claude-opus-5.5-xhigh'), 1.5)

    def test_async_text_and_visual_councils_use_xhigh_opus(self):
        from crux.council.async_council import AsyncCouncilConfig
        self.assertEqual(AsyncCouncilConfig().anthropic_model, 'claude-opus-5.5-xhigh')

    def test_no_medium_effort_opus_5_5_entry_exists(self):
        self.assertNotIn('claude-opus-5.5-medium', self.cfg['models'])

    def test_opus_5_5_registry_entry_fields(self):
        cfg = self.llm.get_model_config('claude-opus-5.5')
        self.assertEqual(cfg.api_string, 'anthropic/claude-opus-5.5')
        self.assertEqual(cfg.effort, 'high')
        self.assertEqual(list(cfg.serving_providers), ['anthropic'])
        self.assertFalse(cfg.supports_temperature)

    def test_xhigh_variant_shares_the_opus_sku_and_provider(self):
        cfg = self.llm.get_model_config('claude-opus-5.5-xhigh')
        self.assertEqual(cfg.api_string, 'anthropic/claude-opus-5.5')
        self.assertEqual(cfg.effort, 'xhigh')
        self.assertEqual(list(cfg.serving_providers), ['anthropic'])
        self.assertFalse(cfg.supports_temperature)

    def test_release_docs_keeps_high_effort(self):
        self.assertEqual(self.llm.get_model_config(self.llm.get_default_model('release_docs')).effort, 'high')


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
        # Non-text entries are refused before any request is built; see
        # test_image_entries_are_refused_before_any_request.
        cfg = self.llm.load_router_config()
        urls = set()
        for model in self.llm.list_available_models():
            if cfg['models'][model].get('type') not in self.llm.TEXT_MODEL_TYPES:
                continue
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
                              ('gpt-6-sol-low', 'low'),
                              ('claude-opus-5.5', 'high'),
                              ('claude-opus-5.5-xhigh', 'xhigh')):
            with self.subTest(model=model):
                payload = self._payload(model)
                self.assertEqual(payload.get('reasoning_effort'), effort)

    def test_unpinned_entries_omit_reasoning_effort(self):
        """Plain Sol and Opus 5 pin no effort — the server default stands, and
        an emitted field would silently override it."""
        for model in ('gpt-6-sol', 'claude-opus-5'):
            with self.subTest(model=model):
                self.assertNotIn('reasoning_effort', self._payload(model))

    def test_effort_aliases_send_the_same_model_id(self):
        self.assertEqual(self._payload('gpt-6-sol')['model'], 'openai/gpt-6-sol')
        self.assertEqual(self._payload('gpt-6-sol-low')['model'], 'openai/gpt-6-sol')

    # -- temperature ---------------------------------------------------------

    def test_reject_set_models_omit_temperature(self):
        for model in TEMPERATURE_REJECT_SET:
            with self.subTest(model=model):
                self.assertNotIn('temperature', self._payload(model))

    def test_accepting_model_still_sends_temperature(self):
        self.assertIn('temperature', self._payload('claude-haiku-4-5-20251001'))

    def test_opus_5_5_built_request_pins_high_effort_anthropic_no_temperature(self):
        payload = self._payload('claude-opus-5.5')
        self.assertEqual(payload.get('reasoning_effort'), 'high')
        self.assertNotIn('temperature', payload)

    def test_default_council_opus_request_pins_xhigh_and_anthropic_provider(self):
        payload = self._payload('claude-opus-5.5-xhigh')
        self.assertEqual(payload['model'], 'anthropic/claude-opus-5.5')
        self.assertEqual(payload['reasoning_effort'], 'xhigh')
        self.assertEqual(payload['provider'], {'only': ['anthropic'], 'data_collection': 'deny'})
        self.assertNotIn('temperature', payload)

    def test_sync_member_and_arbiter_emit_xhigh_opus_requests(self):
        from crux.council import council
        council.council_vote('Question?', tracer=mock.Mock())
        self.assertEqual(len(self.captured), 4)
        member_payload = self.captured[2][2]
        arbiter_payload = self.captured[3][2]
        for payload in (member_payload, arbiter_payload):
            self.assertEqual(payload['model'], 'anthropic/claude-opus-5.5')
            self.assertEqual(payload['reasoning_effort'], 'xhigh')
            self.assertEqual(payload['provider'],
                             {'only': ['anthropic'], 'data_collection': 'deny'})

    def test_opus_convenience_helper_emits_opus_5_5_request(self):
        self.llm.call_claude_opus('Question?')
        payload = self.captured[-1][2]
        self.assertEqual(payload['model'], 'anthropic/claude-opus-5.5')
        self.assertEqual(payload['reasoning_effort'], 'xhigh')

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

    # -- GPT-6 payloads (f) and host/retention controls ---------------------

    def test_gpt_6_payloads_send_no_tool_fields(self):
        """GPT-6 Sol and Luna allow function calling on Chat Completions only at
        reasoning effort `none`. The gateway sends no tools, so the restriction
        reaches no call path; a tool field appearing here would break that."""
        for model in ('gpt-6-sol', 'gpt-6-sol-low', 'gpt-6-luna'):
            payload = self._payload(model)
            for field in ('tools', 'tool_choice', 'functions'):
                with self.subTest(model=model, field=field):
                    self.assertNotIn(field, payload)

    def test_gpt_6_effort_fields(self):
        self.assertNotIn('reasoning_effort', self._payload('gpt-6-sol'))
        self.assertNotIn('reasoning_effort', self._payload('gpt-6-luna'))
        self.assertEqual(self._payload('gpt-6-sol-low').get('reasoning_effort'), 'low')

    def test_gpt_6_sol_pins_the_openai_host_and_denies_collection(self):
        self.assertEqual(self._payload('gpt-6-sol').get('provider'),
                         {'only': ['openai'], 'data_collection': 'deny'})

    def test_other_gpt_6_entries_deny_collection_without_a_host_pin(self):
        # gpt-image-2.5-sunburst left this list: the text path now refuses it
        # before any request exists to carry a provider object.
        for model in ('gpt-6-sol-low', 'gpt-6-luna'):
            with self.subTest(model=model):
                self.assertEqual(self._payload(model).get('provider'),
                                 {'data_collection': 'deny'})

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
        self._request('gpt-6-sol')
        self.assertEqual(self._last_return, 'ok')

    # -- text-only call path refuses non-text entries ------------------------

    def _non_text_models(self):
        cfg = self.llm.load_router_config()
        return {k: v.get('type') for k, v in cfg['models'].items()
                if v.get('type') != 'text'}

    def test_image_entries_are_refused_before_any_request(self):
        """The text path returns only `message.content`, so an image entry
        either answers empty (image-only output) or loses its image. Every
        image entry must be refused by name and type, and nothing is posted."""
        image_models = {k: t for k, t in self._non_text_models().items()
                        if t and t.startswith('image_')}
        self.assertEqual(set(image_models), {
            'gpt-image-2.5-sunburst', 'gemini-3-pro-image-preview',
            'gemini-3.1-flash-image-preview', 'gemini-2.5-flash-image'})
        for model, model_type in image_models.items():
            with self.subTest(model=model):
                self.captured.clear()
                with self.assertRaises(self.llm.NotATextModelError) as ctx:
                    self.llm.call_model(model, 'hi', max_tokens=64)
                message = str(ctx.exception)
                self.assertIn(model, message)
                self.assertIn(model_type, message)
                self.assertIn('image generation has no crux caller', message)
                self.assertEqual(self.captured, [], 'a refused entry posted a request')

    def test_every_text_entry_still_builds_a_request(self):
        cfg = self.llm.load_router_config()
        text_models = [k for k, v in cfg['models'].items() if v.get('type') == 'text']
        self.assertTrue(text_models)
        for model in text_models:
            with self.subTest(model=model):
                url, _, payload = self._request(model)
                self.assertEqual(url, 'https://openrouter.ai/api/v1/chat/completions')
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
