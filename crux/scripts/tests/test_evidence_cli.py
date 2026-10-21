"""The test-evidence.py command reports states, refusal reasons and two separate verdicts."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _evidence_fixtures import variant

SCRIPT = Path(__file__).resolve().parents[1] / "test-evidence.py"


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.store = self.root / "store"
        patcher = patch.dict(os.environ, {"CRUX_TEST_EVIDENCE_STORE": str(self.store)})
        patcher.start()
        self.addCleanup(patcher.stop)
        (self.root / "input.txt").write_text("one")
        self.check = self.root / "check.json"
        self.check.write_text(json.dumps({"check_id": "unit", "command": ["python", "-c", "print('ok')"], "inputs": ["input.txt"], "environment": []}))

    def run_cli(self, *args):
        run = subprocess.run([sys.executable, str(SCRIPT), "--repo-root", str(self.root), *args], capture_output=True, text=True)
        return run.returncode, (json.loads(run.stdout) if run.stdout.strip() else None), run.stderr

    def test_run_then_lookup_then_report_two_separate_verdicts(self):
        code, ran, _ = self.run_cli("run", "--check", str(self.check))
        self.assertEqual((code, ran["action"]), (0, "executed"))
        evidence_id = ran["evidence"]["id"]
        code, found, _ = self.run_cli("lookup", "--check", str(self.check))
        self.assertEqual((code, found["state"], found["record"]["id"]), (0, "passed", evidence_id))
        code, report, _ = self.run_cli("report", "--evidence-id", evidence_id)
        self.assertEqual(code, 0)
        self.assertTrue(report["completeness"]["complete"])
        self.assertTrue(report["reuse_eligibility"]["eligible"])
        (self.root / "input.txt").write_text("two")
        code, report, _ = self.run_cli("report", "--evidence-id", evidence_id)
        self.assertEqual(code, 1)
        self.assertTrue(report["completeness"]["complete"])
        self.assertFalse(report["reuse_eligibility"]["eligible"])
        self.assertIn("relevant inputs changed", report["reuse_eligibility"]["reasons"][0])

    def test_lookup_names_the_receipts_it_ignored_and_why(self):
        _, ran, _ = self.run_cli("run", "--check", str(self.check))
        variant(self.store, ran["evidence"]["id"], lambda r: r.update(status="interrupted", returncode=None))
        (self.store / (ran["evidence"]["id"] + ".json")).unlink()
        code, found, _ = self.run_cli("lookup", "--check", str(self.check))
        self.assertEqual((code, found["state"]), (1, "missing"))
        self.assertEqual(len(found["ignored"]), 1)
        self.assertIn("interrupted neither passes nor blocks", found["ignored"][0]["reason"])

    def test_report_reads_a_retained_directory_without_writing(self):
        _, ran, _ = self.run_cli("run", "--check", str(self.check))
        retained = self.root / "retained"
        retained.mkdir()
        for name in (ran["evidence"]["id"] + ".json", ran["evidence"]["output"]):
            (retained / name).write_bytes((self.store / name).read_bytes())
        (retained / ran["evidence"]["output"]).unlink()
        before = sorted(p.name for p in retained.iterdir())
        code, report, _ = self.run_cli("report", "--evidence-id", ran["evidence"]["id"], "--directory", str(retained))
        self.assertEqual(code, 1)
        self.assertEqual(report["completeness"]["log"], "missing")
        self.assertEqual(sorted(p.name for p in retained.iterdir()), before)

    def test_a_missing_receipt_is_a_usage_failure_not_a_crash(self):
        code, report, _ = self.run_cli("report", "--evidence-id", "TE-" + "0" * 32)
        self.assertEqual(code, 1)
        self.assertFalse(report["completeness"]["complete"])


if __name__ == "__main__":
    unittest.main()
