"""Lifecycle views keep proposals retrievable without granting them authority."""
import copy
import json
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import decision_policy as policy
import doctrine_projection as doctrine
import summaries_projection as summaries
from cycle_workflow import digest, encoded
from test_summaries_migration_projection import record


class ProposedViews(unittest.TestCase):
    def setUp(self):
        self.accepted = record("ADR-0001/accepted")
        self.proposed = record("ADR-0002/proposed", status="Proposed")
        self.rows = [self.accepted, self.proposed]

    def test_proposal_is_not_live_or_a_governing_resolver_citation(self):
        self.assertEqual(summaries.live_records(self.rows), [self.accepted])
        live, _ = summaries.live_and_retired_slugs(self.rows)
        self.assertEqual(live, {"accepted": self.accepted["handle"]})
        resolver = summaries.build_resolver(self.rows)
        self.assertNotIn(self.proposed["handle"], resolver)
        proposed = resolver["proposed"][self.proposed["handle"]]
        self.assertEqual(proposed["source_status"], "Proposed")
        self.assertEqual(proposed["authority"], "none")
        self.assertEqual(proposed["disposition"], "proposed-not-governing")
        self.assertEqual(resolver[self.accepted["handle"]],
                         summaries.build_resolver([self.accepted])[self.accepted["handle"]])

    def test_table_and_doctrine_separate_proposals_from_current_beliefs(self):
        table = summaries.build_rule_table(self.rows)
        governing, proposed = table.split("## Proposed rules — not governing")
        self.assertNotIn(self.proposed["handle"], governing)
        self.assertIn(self.proposed["handle"], proposed)
        entries = doctrine._build_domain_entries_loaded(self.rows, [], [], {}, None,
            tree_name="bionic", evidence_facts={})
        self.assertEqual(entries[0]["source_handles"], [self.accepted["handle"]])
        index = doctrine.build_index(entries, [], {}, proposed_records=[self.proposed])
        current, proposals = index.split("## Proposed rules — not governing")
        self.assertNotIn(self.proposed["handle"], current)
        self.assertIn(self.proposed["handle"], proposals)
        self.assertNotIn("| decided |", proposals)

    def test_proposal_with_same_slug_does_not_override_accepted_citation(self):
        proposal = record("ADR-0002/accepted", status="Proposed")
        live, _ = summaries.live_and_retired_slugs([self.accepted, proposal])
        self.assertEqual(live, {"accepted": self.accepted["handle"]})


class AcceptanceAmendment(unittest.TestCase):
    TARGET = "ADR-0146/authority-migration-is-reviewed-and-source-bound"
    AMENDER = "ADR-0160/historical-migration-proof-is-unchanged"
    RULE = ("ADR-0146/authority-migration-is-reviewed-and-source-bound governs historical-format "
            "publications only; they keep their proof requirements and interpretation, and none is "
            "rewritten or upgraded to the prospective format.")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.docs = self.root / "bionic"
        self.docs.mkdir()
        (self.root / ".bionic.yml").write_text('config_version: "1"\ndocs_dir: bionic\n')
        (self.docs / "manifest.yml").write_text('schema_version: "5"\nconcerns_enabled: [adrs]\nadr:\n  next_number: 160\n')
        self.adrs = self.docs / "adrs"
        self.adrs.mkdir()
        target = {"id": "ADR-0146", "status": "Accepted", "governs": [{
            "handle": self.TARGET, "domain": "decision-migration", "rule": "Validate all migration publications.",
            "scope": "all migration publications", "provenance": "authored"}]}
        import yaml
        (self.adrs / "ADR-0146-migration.md").write_text("---\n" + yaml.safe_dump(target) + "---\n# Original\n")
        self.subject = policy.propose(self.root, {"title": "Narrow historical proof", "body": "# Decision\nHistorical proof is preserved.\n",
            "amends": ["ADR-0146"], "governs": [{"handle": "historical-migration-proof-is-unchanged",
                "domain": "decision-migration", "rule": self.RULE,
                "scope": "historical migration publications and their readers"}]}, origin="direct")["path"]

    def accept(self):
        council = {"format": "crux.cycle-council", "purpose": "adr", "subject": self.subject,
            "subject_sha256": digest((self.docs / self.subject).read_bytes()), "outcome": "approved", "cycle_id": None,
            "seats": [{"provider": p, "decision": "APPROVE", "errored": False, "findings": []}
                      for p in ("one", "two", "three")]}
        council["record_sha256"] = digest(encoded(council))
        path = self.adrs / "councils/test.json"
        path.parent.mkdir()
        path.write_bytes(encoded(council))
        policy.accept(self.root, self.subject, "adrs/councils/test.json", human_approval="Owner: accept this ADR")

    def test_narrowing_requires_valid_acceptance_and_preserves_source_identity(self):
        before = summaries.collect_records(self.adrs)
        target = before[0]
        original = copy.deepcopy(target)
        self.assertNotIn("amended_by", target)
        self.accept()
        after = summaries.collect_records(self.adrs)
        target = next(r for r in after if r["handle"] == self.TARGET)
        self.assertEqual(summaries.content_digest(target), summaries.content_digest(original))
        self.assertEqual(target["rule"], original["rule"])
        self.assertEqual(target["scope"], original["scope"])
        self.assertEqual(target["amended_by"], [self.AMENDER])
        self.assertEqual(target["effective_rule"], self.RULE)
        self.assertEqual(target["effective_scope"], "historical migration publications and their readers")
        resolver = summaries.build_resolver(after)
        self.assertEqual(resolver[self.TARGET]["rule"], self.RULE)
        self.assertEqual(resolver[self.TARGET]["amended_by"], [self.AMENDER])
        table = summaries.build_rule_table(after)
        self.assertIn(self.RULE, table)
        self.assertIn("## Amended live rules", table)
        entries = doctrine._build_domain_entries_loaded(after, [], [], {}, None,
            tree_name="bionic", evidence_facts={})
        rule = next(r for e in entries for r in e["rules"] if r["handle"] == self.TARGET)
        self.assertEqual(rule["rule"], self.RULE)
        self.assertEqual(rule["amended_by"], [self.AMENDER])
        index = doctrine.build_index(entries, [], {})
        self.assertIn(self.AMENDER, index)
        self.assertIn("historical migration publications and their readers", index)

    def test_unreceipted_accepted_amender_cannot_apply_narrowing(self):
        path = self.docs / self.subject
        path.write_text(path.read_text().replace("status: Proposed", "status: Accepted"))
        with self.assertRaisesRegex(ValueError, "acceptance receipt missing"):
            summaries.collect_records(self.adrs)

    def test_no_generic_citation_or_amends_relation_changes_target_scope(self):
        path = self.docs / self.subject
        path.write_text(path.read_text().replace("historical-migration-proof-is-unchanged", "discuss-historical-proof"))
        self.accept()
        target = next(r for r in summaries.collect_records(self.adrs) if r["handle"] == self.TARGET)
        self.assertNotIn("amended_by", target)

    def test_catalog_and_live_council_context_use_narrowed_wording(self):
        import implementation_approval as approval
        self.accept()
        records = summaries.collect_records(self.adrs)
        spec = importlib.util.spec_from_file_location("u0_catalog", Path(summaries.__file__).with_name("generate-rules-catalog.py"))
        catalog = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(catalog)
        facts = dict(historical_handles={}, historical_displacements=[], retired_handles=[],
                     reserved_slugs=[], retained_handles=[], source_refs=[], dependency_fingerprints=[])
        slug = summaries.slug_of(self.TARGET)
        payload = catalog._catalog_payload(dict(records=records,
            reviews=dict(batches={}, receipts=[], no_rule=[]), aliases={},
            cited={slug: ["crux/skills/example/SKILL.md"]}, refusals=[]), facts)
        self.assertEqual(payload["rules"][slug]["rule"], self.RULE)
        raw = [{key: r[key] for key in ("handle", "domain", "rule", "scope", "provenance")} for r in records]
        with patch.object(approval, "declared_empty_findings", return_value={"unscoped": [self.TARGET]}), \
                patch.object(approval, "_accepted_governs_entries", return_value=raw):
            context = approval.unchecked_rules(self.root, {})
        self.assertEqual(context[0]["rule"], self.RULE)
        self.assertEqual(context[0]["scope"], "historical migration publications and their readers")
        self.assertEqual(context[0]["amended_by"], [self.AMENDER])
        import implementation_decisions as decisions
        with patch.object(decisions, "_decision", return_value=({"scope": ["src/"]}, None, None)), \
                patch.object(approval, "unchecked_rules", return_value=context):
            rendered = decisions.unchecked_rules_text(self.root, "unused.yaml")
        self.assertIn("Amended by: " + self.AMENDER, rendered)

    def test_current_reconciliation_needs_review_of_amended_wording(self):
        invariant = dict(id="INV-0001", ratification="ratified", related_adrs=["ADR-0146"],
                         invariant_text="Keep the historical proof.")
        before = summaries.collect_records(self.adrs)
        previous = doctrine.candidate_pairings(before, [invariant])[0]
        key = (invariant["id"], self.TARGET)
        signature = {key: dict(content_digest=previous["live_digest"], verdict="compatible")}
        self.assertEqual(doctrine.pairing_status(previous, signature), "compatible")
        self.accept()
        after = summaries.collect_records(self.adrs)
        current = doctrine.candidate_pairings(after, [invariant])[0]
        self.assertEqual(current["rule"], self.RULE)
        self.assertEqual(doctrine.pairing_status(current, signature), "digest-stale")
        signature[key]["content_digest"] = current["live_digest"]
        self.assertEqual(doctrine.pairing_status(current, signature), "compatible")
        self.assertEqual(summaries.content_digest(before[0]), summaries.content_digest(after[0]))

    def test_observation_pairing_uses_effective_scope_and_wording(self):
        target = record(self.TARGET)
        target.update(scope="src/", effective_scope="historical/", effective_rule=self.RULE,
                      amended_by=[self.AMENDER])
        observation = record("OBS-0001/proof")
        observation.update(source_kind="observation", source_status="ratified", provenance="recovered",
                           evidence=["src/file.py:1-2"])
        self.assertEqual(doctrine.observation_pairings([target, observation]), [])
        observation["evidence"] = ["historical/file.py:1-2"]
        pair = doctrine.observation_pairings([target, observation])[0]
        self.assertEqual(pair["rule"], self.RULE)
        self.assertEqual(pair["live_digest"], doctrine.reconciliation_content_digest(observation["rule"], self.RULE))


if __name__ == "__main__":
    unittest.main()
