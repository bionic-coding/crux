"""ADR-0054: council aggregation excludes a single errored provider seat.

Exercises `AsyncCouncil._aggregate_votes` directly (no API calls — the ctor
resolves keys via crux_env and tolerates their absence; `_aggregate_votes` is
pure). Covers the responding-seat confidence mean, the quorum gate, the
`errored_seats`/`degraded` surface, the widened approval set, and the
`has_critical_dissent` scoping. Runs under the uv lane (importing the council
pulls in the LLM router's httpx transport); skips cleanly where it's absent.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCRIPTS = REPO_ROOT / "crux" / "scripts"

try:
    sys.path.insert(0, str(SCRIPTS))
    from crux.council.async_council import AsyncCouncil
    from crux.core.data_classes import CouncilVote
    HAVE_COUNCIL = True
except Exception:  # the router transport (httpx) unavailable
    HAVE_COUNCIL = False


def vote(provider, decision, confidence, errored=False, dissents=None):
    return CouncilVote(
        model=(f"{provider}/ERROR" if errored else f"{provider}/model-x"),
        provider=provider,
        decision=decision,
        reasoning="",
        confidence=confidence,
        dissenting_points=dissents or [],
        errored=errored,
    )


@unittest.skipUnless(HAVE_COUNCIL, "council import (httpx transport) unavailable")
class AggregationTests(unittest.TestCase):
    def setUp(self):
        self.c = AsyncCouncil()

    def agg(self, votes):
        return self.c._aggregate_votes(votes)

    def test_all_respond_no_regression_auto_execute(self):
        r = self.agg([vote("a", "APPROVE", 0.9), vote("b", "APPROVE", 0.88), vote("c", "APPROVE", 0.86)])
        self.assertEqual(r.consensus, "UNANIMOUS_APPROVE")
        self.assertFalse(r.degraded)
        self.assertEqual(r.errored_seats, "0/3")
        self.assertEqual(r.final_recommendation["action"], "AUTO_EXECUTE")

    def test_one_errored_seat_degraded_execute_with_monitoring(self):
        # The motivating case: 2 clean approvals + 1 errored seat. Old code
        # reported SPLIT/0.57 -> DEFER; new code -> UNANIMOUS over responders,
        # degraded ceiling -> EXECUTE_WITH_MONITORING.
        r = self.agg([
            vote("a", "APPROVE", 0.86),
            vote("b", "APPROVE_WITH_NITS", 0.85),
            vote("g", "DEFER_TO_HUMAN", 0.0, errored=True, dissents=["Provider g failed: timeout"]),
        ])
        self.assertEqual(r.consensus, "UNANIMOUS_APPROVE")
        self.assertTrue(r.degraded)
        self.assertEqual(r.errored_seats, "1/3")
        self.assertAlmostEqual(r.consensus_confidence, 0.855, places=3)
        self.assertEqual(r.final_recommendation["action"], "EXECUTE_WITH_MONITORING")
        self.assertEqual(r.final_recommendation["errored_seats"], "1/3")
        self.assertTrue(r.final_recommendation["degraded"])

    def test_full_quorum_high_conf_reaches_auto_execute_but_degraded_does_not(self):
        clean = self.agg([vote("a", "APPROVE", 0.9), vote("b", "APPROVE", 0.9), vote("c", "APPROVE", 0.9)])
        self.assertEqual(clean.final_recommendation["action"], "AUTO_EXECUTE")
        degraded = self.agg([vote("a", "APPROVE", 0.9), vote("b", "APPROVE", 0.9),
                             vote("g", "DEFER_TO_HUMAN", 0.0, errored=True)])
        self.assertTrue(degraded.degraded)
        self.assertEqual(degraded.final_recommendation["action"], "EXECUTE_WITH_MONITORING")

    def test_errored_seat_dissent_excluded(self):
        r = self.agg([
            vote("a", "APPROVE", 0.9), vote("b", "APPROVE", 0.9),
            vote("g", "DEFER_TO_HUMAN", 0.0, errored=True, dissents=["Provider g failed: critical error"]),
        ])
        self.assertEqual(r.dissent_count, 0)
        self.assertFalse(r.has_critical_dissent)

    def test_responding_reject_critical_dissent_trips(self):
        r = self.agg([
            vote("a", "APPROVE", 0.9),
            vote("b", "REJECT", 0.8, dissents=["critical: unsafe path"]),
            vote("c", "APPROVE", 0.7),
        ])
        self.assertTrue(r.has_critical_dissent)

    def test_split_two_responding_defers(self):
        r = self.agg([
            vote("a", "APPROVE", 0.9), vote("b", "REJECT", 0.8),
            vote("g", "DEFER_TO_HUMAN", 0.0, errored=True),
        ])
        self.assertEqual(r.consensus, "SPLIT")
        self.assertEqual(r.final_recommendation["action"], "DEFER_TO_HUMAN")

    def test_all_errored_is_no_quorum(self):
        r = self.agg([
            vote("a", "DEFER_TO_HUMAN", 0.0, errored=True),
            vote("b", "DEFER_TO_HUMAN", 0.0, errored=True),
            vote("c", "DEFER_TO_HUMAN", 0.0, errored=True),
        ])
        self.assertEqual(r.consensus, "NO_QUORUM")
        self.assertEqual(r.final_recommendation["action"], "DEFER_TO_HUMAN")
        self.assertEqual(r.errored_seats, "3/3")

    def test_one_responding_below_quorum(self):
        r = self.agg([
            vote("a", "APPROVE", 0.99),
            vote("b", "DEFER_TO_HUMAN", 0.0, errored=True),
            vote("c", "DEFER_TO_HUMAN", 0.0, errored=True),
        ])
        self.assertEqual(r.consensus, "NO_QUORUM")
        self.assertEqual(r.final_recommendation["action"], "DEFER_TO_HUMAN")

    def test_approve_with_nits_counts_as_approval(self):
        r = self.agg([vote("a", "APPROVE_WITH_NITS", 0.9), vote("b", "APPROVE_WITH_NITS", 0.9),
                      vote("c", "APPROVE", 0.9)])
        self.assertEqual(r.consensus, "UNANIMOUS_APPROVE")

    def test_error_vote_is_marked_errored(self):
        # The INV-0001-relevant property of an error vote: it is flagged
        # `errored=True` so the aggregator can exclude it. The REDACTION
        # behaviour of _create_error_vote is deliberately NOT tested here —
        # it lives in test_council_redaction.py.
        #
        # Why the split (PB-0052): this class is INV-0001's executable check
        # (`check_id: council_aggregation`). Two redaction tests used to live
        # here, so a redaction failure set reconciliation `last_result: fail`
        # and reported the *aggregation* invariant as violated — a false signal
        # about a ratified pin. Keep this file about aggregation only.
        v = self.c._create_error_vote("openai", RuntimeError("boom"))
        self.assertTrue(v.errored)
        self.assertEqual(v.model, "openai/ERROR")
        self.assertEqual(v.decision, "DEFER_TO_HUMAN")
        self.assertEqual(v.confidence, 0.0)

    def test_votes_retains_all_seats(self):
        r = self.agg([vote("a", "APPROVE", 0.9), vote("b", "APPROVE", 0.9),
                      vote("g", "DEFER_TO_HUMAN", 0.0, errored=True)])
        self.assertEqual(len(r.votes), 3)
        self.assertEqual(r.errored_seats, "1/3")

    def test_empty_votes_no_quorum_not_degraded(self):
        # The empty-votes early return: NO_QUORUM/DEFER, and the mirrored
        # final_recommendation must agree with the .degraded property (no seats
        # errored -> not degraded, just under-provisioned).
        r = self.agg([])
        self.assertEqual(r.consensus, "NO_QUORUM")
        self.assertEqual(r.final_recommendation["action"], "DEFER_TO_HUMAN")
        self.assertFalse(r.degraded)
        self.assertEqual(r.final_recommendation["degraded"], r.degraded)
        self.assertEqual(r.errored_seats, "0/0")


if __name__ == "__main__":
    unittest.main()
