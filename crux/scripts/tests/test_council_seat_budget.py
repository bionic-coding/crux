"""Council seat output budgets: per-model resolution and the escalated retry.

A seat running a high or xhigh reasoning model spends output tokens on reasoning
before it writes its vote, so a flat budget ends the reply on finish "length".
These tests pin the contract: the budget resolves per seat from the registry's
`max_output_tokens`, a truncated first attempt retries with the model's output
limit, and each attempt record carries the budget its request used.

No network and no key: a `httpx.MockTransport` captures each request payload.
"""
from __future__ import annotations

import asyncio
import dataclasses
import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

try:
    import httpx
    HAVE_HTTPX = True
except ImportError:
    HAVE_HTTPX = False

VOTE = json.dumps({"decision": "APPROVE", "confidence": 0.8, "dissents": [], "reasoning": "ok"})


def _body(content="", finish="stop"):
    return {"choices": [{"message": {"content": content}, "finish_reason": finish}]}


class _Gateway:
    """A transport that records each payload and answers from a script of steps.

    A step is a (status, body) pair, or the string "timeout" to raise a timeout.
    The last step repeats once the script runs out.
    """

    def __init__(self, steps):
        self.payloads = []
        self._steps = steps
        self.transport = httpx.MockTransport(self._handle)

    def _handle(self, request):
        self.payloads.append(json.loads(request.content))
        step = self._steps[min(len(self.payloads), len(self._steps)) - 1]
        if step == "timeout":
            raise httpx.ReadTimeout("slow")
        status, body = step
        return httpx.Response(status, json=body)

    @property
    def budgets(self):
        return [p["max_tokens"] for p in self.payloads]


OK = (200, _body(VOTE))
TRUNCATED = (200, _body("{", finish="length"))
PROVIDER_FAULT = (503, {"error": "down"})


def _council(gateway, **config):
    from crux.council.async_council import AsyncCouncil, AsyncCouncilConfig
    return AsyncCouncil(AsyncCouncilConfig(transport=gateway.transport, timeout_seconds=5.0, **config))


def _run_seat(council, seat="openai"):
    with mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-or-test-dummy"}):
        return asyncio.run(council._call_seat_async(seat, "Question?"))


def _limit_of(council, seat):
    from crux.core.llm_caller import get_model_config
    return get_model_config(council._seat_model(seat)).max_output_tokens


def _with_limit(limit):
    """Patch the council's registry lookup so every model reports `limit`."""
    from crux.council import async_council
    real = async_council.get_model_config

    def _lookup(name):
        return dataclasses.replace(real(name), max_output_tokens=limit)

    return mock.patch.object(async_council, "get_model_config", _lookup)


@unittest.skipUnless(HAVE_HTTPX, "httpx not installed - run under uv")
class FirstAttemptBudgetTests(unittest.TestCase):
    def test_default_budget_resolves_per_seat_from_the_registry(self):
        for seat in ("openai", "anthropic", "gemini"):
            with self.subTest(seat=seat):
                gateway = _Gateway([OK])
                council = _council(gateway)
                limit = _limit_of(council, seat)
                _run_seat(council, seat)
                self.assertEqual(gateway.budgets, [min(limit, max(limit // 2, 32000))])

    def test_a_high_limit_seat_gets_more_than_the_old_flat_budget(self):
        gateway = _Gateway([OK])
        council = _council(gateway)
        self.assertGreaterEqual(_limit_of(council, "anthropic"), 128000)
        _run_seat(council, "anthropic")
        self.assertEqual(gateway.budgets, [64000])

    def test_explicit_max_tokens_is_the_first_budget_for_every_seat(self):
        for seat in ("openai", "anthropic", "gemini"):
            with self.subTest(seat=seat):
                gateway = _Gateway([OK])
                _run_seat(_council(gateway, max_tokens=32000), seat)
                self.assertEqual(gateway.budgets, [32000])

    def test_fallback_when_the_limit_is_not_a_positive_int(self):
        for limit in (0, -5, None, True, "big"):
            with self.subTest(limit=limit), _with_limit(limit):
                gateway = _Gateway([OK])
                _run_seat(_council(gateway))
                self.assertEqual(gateway.budgets, [32000])

    def test_a_small_limit_caps_the_first_budget(self):
        with _with_limit(8000):
            gateway = _Gateway([OK])
            _run_seat(_council(gateway))
            self.assertEqual(gateway.budgets, [8000])

    def test_a_limit_between_the_floor_and_double_it_halves_to_the_floor(self):
        with _with_limit(40000):
            gateway = _Gateway([OK])
            _run_seat(_council(gateway))
            self.assertEqual(gateway.budgets, [32000])


@unittest.skipUnless(HAVE_HTTPX, "httpx not installed - run under uv")
class EscalatedRetryTests(unittest.TestCase):
    def test_truncated_first_attempt_retries_with_the_seat_limit_and_votes(self):
        gateway = _Gateway([TRUNCATED, OK])
        council = _council(gateway)
        vote = _run_seat(council, "anthropic")
        self.assertEqual(gateway.budgets, [64000, _limit_of(council, "anthropic")])
        self.assertFalse(vote.errored)
        self.assertEqual(vote.decision, "APPROVE")
        self.assertTrue(vote.retried)

    def test_escalation_never_lowers_an_explicit_larger_budget(self):
        gateway = _Gateway([TRUNCATED, OK])
        with _with_limit(40000):
            _run_seat(_council(gateway, max_tokens=100000))
        self.assertEqual(gateway.budgets, [100000, 100000])

    def test_escalation_raises_an_explicit_budget_to_the_limit(self):
        gateway = _Gateway([TRUNCATED, OK])
        council = _council(gateway, max_tokens=32000)
        _run_seat(council, "openai")
        self.assertEqual(gateway.budgets, [32000, _limit_of(council, "openai")])

    def test_truncated_without_a_usable_limit_retries_with_the_first_budget(self):
        with _with_limit(None):
            gateway = _Gateway([TRUNCATED, OK])
            _run_seat(_council(gateway))
        self.assertEqual(gateway.budgets, [32000, 32000])

    def test_a_non_truncated_retryable_fault_keeps_the_first_budget(self):
        for step in ("timeout", PROVIDER_FAULT):
            with self.subTest(step=step):
                gateway = _Gateway([step, OK])
                vote = _run_seat(_council(gateway), "anthropic")
                self.assertEqual(gateway.budgets, [64000, 64000])
                self.assertFalse(vote.errored)

    def test_two_truncations_make_exactly_two_requests(self):
        gateway = _Gateway([TRUNCATED])
        vote = _run_seat(_council(gateway), "anthropic")
        self.assertEqual(len(gateway.payloads), 2)
        self.assertTrue(vote.errored)
        self.assertEqual([a["fault_label"] for a in vote.attempts], ["truncated", "truncated"])

    def test_max_retries_zero_sends_one_request_and_no_escalation(self):
        gateway = _Gateway([TRUNCATED, OK])
        vote = _run_seat(_council(gateway, max_retries=0), "anthropic")
        self.assertEqual(gateway.budgets, [64000])
        self.assertTrue(vote.errored)


@unittest.skipUnless(HAVE_HTTPX, "httpx not installed - run under uv")
class AttemptRecordTests(unittest.TestCase):
    def test_each_attempt_record_carries_its_budget(self):
        gateway = _Gateway([TRUNCATED, OK])
        council = _council(gateway)
        vote = _run_seat(council, "anthropic")
        self.assertEqual([a["max_tokens"] for a in vote.attempts],
                         [64000, _limit_of(council, "anthropic")])
        self.assertEqual([a["max_tokens"] for a in vote.attempts], gateway.budgets)

    def test_a_single_attempt_record_carries_the_budget(self):
        gateway = _Gateway([OK])
        vote = _run_seat(_council(gateway), "gemini")
        self.assertEqual([a["max_tokens"] for a in vote.attempts], gateway.budgets)

    def test_an_errored_vote_records_the_budgets_too(self):
        gateway = _Gateway([TRUNCATED])
        vote = _run_seat(_council(gateway), "anthropic")
        self.assertEqual([a["max_tokens"] for a in vote.attempts], gateway.budgets)

    def test_an_attempt_that_never_built_a_request_records_none(self):
        from crux.council.async_council import _Attempt
        self.assertIsNone(_Attempt().record(1)["max_tokens"])


@unittest.skipUnless(HAVE_HTTPX, "httpx not installed - run under uv")
class VisualCouncilBudgetTests(unittest.TestCase):
    def test_visual_seats_escalate_the_same_way(self):
        from crux.council.async_council import AsyncVisualCouncil, AsyncCouncilConfig
        visual = json.dumps({"passed": True, "confidence": 0.9, "observations": "ok", "anomalies": []})
        gateway = _Gateway([TRUNCATED, (200, _body(visual))])
        council = AsyncVisualCouncil(AsyncCouncilConfig(
            transport=gateway.transport, timeout_seconds=5.0, max_retries=1))
        council.available_providers = ["anthropic"]
        limit = _limit_of(council, "anthropic")
        with mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-or-test-dummy"}):
            results = council.analyze_sync("aGVsbG8=", "Inspect.")
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].errored)
        self.assertEqual(gateway.budgets, [64000, limit])


@unittest.skipUnless(HAVE_HTTPX, "httpx not installed - run under uv")
class ConfigValidationTests(unittest.TestCase):
    def test_none_is_the_default_and_is_accepted(self):
        from crux.council.async_council import AsyncCouncilConfig
        self.assertIsNone(AsyncCouncilConfig().max_tokens)
        self.assertIsNone(AsyncCouncilConfig(max_tokens=None).max_tokens)

    def test_a_positive_int_is_accepted(self):
        from crux.council.async_council import AsyncCouncilConfig
        self.assertEqual(AsyncCouncilConfig(max_tokens=1).max_tokens, 1)

    def test_bool_zero_negative_float_and_string_are_refused(self):
        from crux.council.async_council import AsyncCouncilConfig
        for bad in (True, False, 0, -1, 1.5, "100"):
            with self.subTest(bad=bad), self.assertRaisesRegex(
                    ValueError, "max_tokens must be a positive integer or None"):
                AsyncCouncilConfig(max_tokens=bad)

    def test_default_seat_timeout_covers_an_escalated_attempt(self):
        from crux.council.async_council import DEFAULT_SEAT_TIMEOUT_SECONDS
        self.assertEqual(DEFAULT_SEAT_TIMEOUT_SECONDS, 1200.0)


if __name__ == "__main__":
    unittest.main()
