"""Lifecycle status remains explicit while Proposed rules stay non-governing.

Acceptance preserves raw governs digests and historical signed receipts.
Proposed source text remains retrievable through a separate resolver lane.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS))

import summaries_projection as sp  # noqa: E402

ADR_TMPL = """---
id: {aid}
title: "Fixture {n}"
status: {status}
date: 2026-09-17
proposed_date: 2026-09-17
accepted_date: {accepted}
deprecated_date: null
superseded_date: null
supersedes: []
amends: []
superseded_by: null
deciders: ["fixture"]
tags: [fixture]
related_briefs: []
related_research: []
governs:
  - domain: fixture-domain
    rule: "Fixture rule {n} says every widget is frobnicated before use."
    scope: the fixture
    handle: {aid}/fixture-rule-{n}
    provenance: authored
---

# {aid} — Fixture {n}

## Context
c
## Decision
d
## Alternatives Considered
a
## Consequences
q
## References
r
"""


class StatusExposureTestCase(unittest.TestCase):
    """A disposable tree holding one Accepted and one Proposed ADR."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        (self.root / ".bionic.yml").write_text(
            'config_version: "1"\ndocs_dir: bionic\n', encoding="utf-8")
        self.docs = self.root / "bionic"
        self.adrs = self.docs / "adrs"
        self.adrs.mkdir(parents=True)
        (self.docs / "manifest.yml").write_text(
            'schema_version: "5"\nconcerns_enabled: [adrs]\nadr:\n'
            '  next_number: 3\n  governs_from: 1\n', encoding="utf-8")
        self.write_adr(1, "Accepted")
        self.write_adr(2, "Proposed")

    def write_adr(self, n: int, status: str) -> Path:
        aid = f"ADR-{n:04d}"
        p = self.adrs / f"{aid}-fixture-{n}.md"
        p.write_text(ADR_TMPL.format(aid=aid, n=n, status=status,
                                     accepted="2026-09-17" if status == "Accepted" else "null"),
                     encoding="utf-8")
        return p

    def records(self) -> list[dict]:
        return sp.collect_records(self.adrs, governs_from=1, observations=None)

    def resolver(self) -> dict:
        return sp.build_resolver(self.records(), reviews=None, governs_from=1)


class ResolverExposesStatusTests(StatusExposureTestCase):

    def test_proposed_and_accepted_rows_differ_on_source_status(self):
        r = self.resolver()
        acc = r["ADR-0001/fixture-rule-1"]
        pro = r["proposed"]["ADR-0002/fixture-rule-2"]
        self.assertEqual(acc["source_status"], "Accepted")
        self.assertEqual(pro["source_status"], "Proposed")

    def test_proposal_retains_source_text_without_adopted_facets(self):
        r = self.resolver()
        acc = dict(r["ADR-0001/fixture-rule-1"])
        pro = r["proposed"]["ADR-0002/fixture-rule-2"]
        self.assertEqual(pro["rule"], next(x["rule"] for x in self.records()
            if x["handle"] == "ADR-0002/fixture-rule-2"))
        self.assertEqual(pro["authority"], "none")
        self.assertNotIn("review_state", pro)

    def test_disposition_and_authority_keep_their_meanings(self):
        # Both are functions of provenance alone and must not have learned
        # anything about lifecycle.
        r = self.resolver()
        self.assertEqual(r["ADR-0001/fixture-rule-1"]["disposition"], "decided")
        self.assertEqual(r["ADR-0001/fixture-rule-1"]["authority"], "prescriptive")
        self.assertEqual(r["proposed"]["ADR-0002/fixture-rule-2"]["disposition"], "proposed-not-governing")

    def test_a_proposed_handle_is_retrievable_without_governing_resolution(self):
        r = self.resolver()
        self.assertNotIn("ADR-0002/fixture-rule-2", r)
        self.assertTrue(r["proposed"]["ADR-0002/fixture-rule-2"]["rule"])

    def test_a_proposed_slug_is_not_a_governing_citation(self):
        live, _retired = sp.live_and_retired_slugs(self.records())
        self.assertNotIn("fixture-rule-2", live)

    def test_an_absent_status_is_null_not_a_sentinel_string(self):
        # On the MACHINE surface a missing status must be JSON null, never the
        # string "unknown" — a naive consumer cannot tell a sentinel string
        # from a real value, and it would have to join the value domain.
        row = sp._record_from_entry({"handle": "ADR-0009/x", "domain": "d", "rule": "r",
                                     "scope": "s", "provenance": "authored"},
                                    "ADR-0009", 9, source_kind="adr")
        self.assertIsNone(row["source_status"])
        r = sp.build_resolver([row], reviews=None, governs_from=1)
        self.assertIsNone(r["ADR-0009/x"]["source_status"])
        self.assertIn("source_status", json.dumps(r))


class DigestAndSignatureCompatibilityTests(StatusExposureTestCase):
    """Accepting an ADR must move nothing that a signature is bound to."""

    def test_accepting_an_adr_leaves_the_content_digest_byte_identical(self):
        before = {r["handle"]: sp.content_digest(r) for r in self.records()}
        self.write_adr(2, "Accepted")          # the ONLY change: the status line
        after = {r["handle"]: sp.content_digest(r) for r in self.records()}
        self.assertEqual(before, after)

    def test_source_status_is_absent_from_the_canonical_string(self):
        # The digest preimage is what a signed receipt and a signed
        # reconciliation are bound to. Naming the field here would orphan
        # every signature the moment an ADR was accepted.
        rec = next(r for r in self.records() if r["handle"] == "ADR-0002/fixture-rule-2")
        canon = sp.canonical_string(rec)
        self.assertNotIn("Proposed", canon)
        self.assertNotIn("source_status", canon)

    def test_a_receipt_bound_to_the_digest_survives_acceptance(self):
        # A signed receipt carries the digest it passed. If acceptance moved
        # the digest, the receipt would stop matching and the entry would
        # soft-exclude as unreviewed.
        rec = next(r for r in self.records() if r["handle"] == "ADR-0002/fixture-rule-2")
        signed_digest = sp.content_digest(rec)
        self.write_adr(2, "Accepted")
        rec_after = next(r for r in self.records() if r["handle"] == "ADR-0002/fixture-rule-2")
        self.assertEqual(sp.content_digest(rec_after), signed_digest)

    def test_the_status_really_did_change(self):
        # PAIRED CONTROL for the three tests above: they would all pass
        # vacuously if rewriting the fixture changed nothing.
        self.assertEqual(self.resolver()["proposed"]["ADR-0002/fixture-rule-2"]["source_status"], "Proposed")
        self.write_adr(2, "Accepted")
        self.assertEqual(self.resolver()["ADR-0002/fixture-rule-2"]["source_status"], "Accepted")


class ObservationRowTests(unittest.TestCase):
    """An observation's status is copied verbatim, never normalised."""

    def test_the_projected_observation_status_is_the_module_constant(self):
        self.assertEqual(sp.OBSERVATION_PROJECTED_STATUS, "ratified")

    def test_an_observation_row_carries_ratified_not_an_adr_value(self):
        row = sp._record_from_entry({"handle": "OBS-0001/x", "domain": "d", "rule": "r",
                                     "scope": "s", "provenance": "recovered"},
                                    "OBS-0001", 1, source_kind="observation",
                                    status=sp.OBSERVATION_PROJECTED_STATUS)
        self.assertEqual(row["source_status"], "ratified")
        r = sp.build_resolver([row], reviews=None, governs_from=1)
        self.assertEqual(r["OBS-0001/x"]["source_status"], "ratified")
        # And the provenance-derived facets are untouched by the new field.
        self.assertEqual(r["OBS-0001/x"]["disposition"], "observed")

    def test_the_value_domain_is_a_case_sensitive_union(self):
        # ADR values are capitalised, the observation constant is not. No
        # canonicalisation is applied, so a consumer lower-casing before
        # comparison would merge states that differ.
        self.assertNotEqual(sp.OBSERVATION_PROJECTED_STATUS,
                            sp.OBSERVATION_PROJECTED_STATUS.capitalize())


class DoctrineIndexTests(StatusExposureTestCase):
    """Both statuses render in the compiled doctrine index."""

    def run_doctrine(self) -> str:
        r = subprocess.run(
            [sys.executable, str(SCRIPTS / "compile-doctrine.py"), "--repo-root", str(self.root)],
            capture_output=True, timeout=180)
        self.assertEqual(r.returncode, 0, r.stdout.decode() + r.stderr.decode())
        return (self.docs / "adrs" / "doctrine" / "index.md").read_text(encoding="utf-8")

    def test_the_index_carries_a_source_status_column(self):
        body = self.run_doctrine()
        self.assertIn("| handle | citation | rule | source ADR | source_status | disposition | basis |", body)

    def test_both_statuses_render(self):
        body = self.run_doctrine()
        self.assertRegex(body, r"\| ADR-0001 \| Accepted \| decided \|")
        self.assertIn("## Proposed rules — not governing", body)
        self.assertRegex(body, r"\| ADR-0002/fixture-rule-2 .*\| Proposed \| none \|")


if __name__ == "__main__":
    unittest.main()
