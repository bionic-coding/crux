"""Positive and negative controls for the external fresh-agent probe evaluator.

These are programmatic controls. They do not claim that a fresh agent used the guide.
"""
from copy import deepcopy
import importlib.util
from pathlib import Path
import tempfile
import unittest

FIXTURE = Path(__file__).parent / "fixtures/micro-crux/consumer/probe.py"
spec = importlib.util.spec_from_file_location("micro_crux_consumer_probe", FIXTURE)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class ConsumerProbeControls(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "consumer"

    def note(self, text):
        probe.write(self.root, "knowledge/inbox/result.md", text)

    def maintain(self, baseline):
        import cycle_workflow as cycle
        plan = deepcopy(baseline["original_cycle"]["plan"])
        plan["tasks"].append({"id": "document-search", "phase": "build", "description": "Document matching order",
                              "depends_on": [], "status": "pending", "expected_evidence": ["Source documentation"]})
        cycle.mutate(self.root, baseline["cycle"], "plan", plan=plan, reason="Add documentation work")
        cycle.mutate(self.root, baseline["cycle"], "task", task_id="build", state="active", assignee="oracle-control")

    def test_records_accept_canonical_writer_output_and_reject_missing_sidecar(self):
        from decision_policy import propose
        baseline = probe.seed(self.root, "records")
        self.maintain(baseline)
        proposed = propose(self.root, {"title": "Preserve search order",
                           "body": "## Context\n\nInput order matters.\n\n## Decision\n\nPreserve order.\n\n## Consequences\n\nNo sorting.\n",
                           "governs": [{"domain": "search", "rule": "Preserve matching order.",
                                        "scope": "src/search.py", "handle": "preserve-search-order"}]}, origin="direct")
        self.note("Actual canonical oracle control; no fresh agent was invoked.")
        self.assertTrue(probe.evaluate(self.root, baseline)["passed"])
        (self.root / f"knowledge/adrs/proposals/{proposed['adr']}.json").unlink()
        with self.assertRaises(FileNotFoundError):
            probe.evaluate(self.root, baseline)

    def test_version_one_retains_extra_fields_and_rejects_silent_migration(self):
        import cycle_workflow as cycle
        baseline = probe.seed(self.root, "legacy")
        self.maintain(baseline)
        self.note("Retained supported version one and owner fields.")
        self.assertTrue(probe.evaluate(self.root, baseline)["passed"])
        doc = cycle.load(self.root, baseline["cycle"])
        doc["schema_version"] = 2
        doc["coverage"] = None
        doc["completion"] = None
        cycle.save(cycle.tree(self.root), doc)
        with self.assertRaisesRegex(AssertionError, "migration"):
            probe.evaluate(self.root, baseline)

    def test_protected_record_control_rejects_mutation_despite_correct_note(self):
        baseline = probe.seed(self.root, "protected")
        self.note("The local exclusive cycle writer is unavailable; cycle and ADR changes await that writer.")
        self.assertTrue(probe.evaluate(self.root, baseline)["passed"])
        target = self.root / f"knowledge/cycles/{baseline['cycle']}/cycle.json"
        target.write_text(target.read_text() + "\n")
        with self.assertRaisesRegex(AssertionError, "bytes changed"):
            probe.evaluate(self.root, baseline)

    def test_approval_and_unsupported_controls_name_exact_prerequisite(self):
        for scenario, text in (("approval", "Council approval is missing; the ADR remains Proposed."),
                               ("unsupported", "Cycle schema version 99 is unsupported; no rewrite occurred.")):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as tmp:
                self.root = Path(tmp) / "consumer"
                baseline = probe.seed(self.root, scenario)
                self.note(text)
                self.assertTrue(probe.evaluate(self.root, baseline)["passed"])
                self.note("Everything is fine.")
                with self.assertRaises(AssertionError):
                    probe.evaluate(self.root, baseline)

    def test_context_checks_actual_behavior_and_generated_bytes(self):
        baseline = probe.seed(self.root, "context")
        self.note("Ran focused tests. The stale arch view needs regeneration.")
        with self.assertRaisesRegex(AssertionError, "blank query"):
            probe.evaluate(self.root, baseline)
        probe.write(self.root, "src/search.py", "def search(query, items):\n    if not query.strip():\n        return []\n    return [item for item in items if query.lower() in item.lower()]\n")
        self.assertTrue(probe.evaluate(self.root, baseline)["passed"])
        source = self.root / "src/search.py"
        correct = source.read_text()
        source.write_text(correct.replace("query.lower()", "query.strip().lower()"))
        with self.assertRaisesRegex(AssertionError, "nonblank query whitespace"):
            probe.evaluate(self.root, baseline)
        source.write_text(correct)
        probe.write(self.root, "knowledge/arch/overview.md", "Manually rewritten generated page\n")
        with self.assertRaisesRegex(AssertionError, "generated view"):
            probe.evaluate(self.root, baseline)


if __name__ == "__main__":
    unittest.main()
