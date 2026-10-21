"""The durable store, retained copies, and the completeness verdict, separate from reuse eligibility."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _dev_surface import REPO_ROOT, require_dev_surface
from _evidence_fixtures import raw_receipt, reseal_in_place, variant
import test_evidence as te
from test_evidence import EvidenceError, completeness, execute, lookup, retention_copy, reuse_eligibility, scan_logs

# Built at run time so no secret-shaped literal sits in this file.
SECRET = "sk-or-v1-" + "a1b2c3d4" * 6


class DurableStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name).resolve()
        self.dev = self.parent / "dev"
        self.dev.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.dev, check=True)
        (self.dev / "input.txt").write_text("one")
        environment = {k: v for k, v in os.environ.items() if k not in ("CRUX_TEST_EVIDENCE_STORE", "CRUX_TEST_EVIDENCE_DURABLE_ONLY")}
        patcher = patch.dict(os.environ, environment, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.durable = self.dev / ".git" / "crux" / "test-evidence"

    def declaration(self, check_id="unit"):
        return {"check_id": check_id, "command": [sys.executable, "-c", "print('ok')"], "inputs": ["input.txt"], "environment": []}

    def test_checkout_and_staged_receipts_land_in_the_git_common_dir_store(self):
        checkout = execute(self.dev, self.declaration("checkout-unit"))["evidence"]
        stage = self.parent / "stage"
        stage.mkdir()
        (stage / "input.txt").write_text("one")
        staged = execute(stage, self.declaration("staged-unit"), source_root=self.dev)["evidence"]
        self.assertEqual(te.durable_store(self.dev).resolve(), self.durable.resolve())
        for record in (checkout, staged):
            self.assertTrue((self.durable / (record["id"] + ".json")).is_file())
            self.assertTrue((self.durable / record["output"]).is_file())
        self.assertFalse((stage / ".crux-test-evidence").exists())
        self.assertEqual(staged["source_revision"], None)

    def test_deleting_the_stage_and_a_throwaway_environment_leaves_every_receipt_and_log(self):
        stage = self.parent / "stage"
        stage.mkdir()
        (stage / "input.txt").write_text("one")
        throwaway = self.parent / "preflight-env"
        throwaway.mkdir()
        (throwaway / "marker").write_text("x")
        record = execute(stage, self.declaration(), source_root=self.dev)["evidence"]
        shutil.rmtree(stage)
        shutil.rmtree(throwaway)
        verdict = completeness(self.durable, record["id"])
        self.assertTrue(verdict["complete"], verdict["problems"])
        self.assertEqual(self.durable.resolve(), te.storage(self.dev).resolve())

    def test_the_release_path_refuses_a_store_override_outside_the_git_common_dir(self):
        elsewhere = self.parent / "elsewhere"
        with patch.dict(os.environ, {"CRUX_TEST_EVIDENCE_DURABLE_ONLY": "1", "CRUX_TEST_EVIDENCE_STORE": str(elsewhere)}):
            with self.assertRaisesRegex(EvidenceError, "durable store"):
                execute(self.dev, self.declaration())
            with self.assertRaisesRegex(EvidenceError, "refuses an override"):
                lookup(self.dev, self.declaration())
        self.assertFalse(elsewhere.exists())
        with patch.dict(os.environ, {"CRUX_TEST_EVIDENCE_DURABLE_ONLY": "1", "CRUX_TEST_EVIDENCE_STORE": str(self.durable)}):
            self.assertEqual(execute(self.dev, self.declaration())["action"], "executed")
        with patch.dict(os.environ, {"CRUX_TEST_EVIDENCE_DURABLE_ONLY": "1"}):
            self.assertEqual(execute(self.dev, self.declaration())["action"], "reused")

    def test_the_release_children_inherit_the_durable_store_and_an_override_is_refused(self):
        inherited = te.durable_store_environment(self.dev)
        self.assertEqual(Path(inherited["CRUX_TEST_EVIDENCE_STORE"]).resolve(), self.durable.resolve())
        self.assertEqual(inherited["CRUX_TEST_EVIDENCE_DURABLE_ONLY"], "1")
        self.assertEqual(te.durable_store_environment(self.dev, {"CRUX_TEST_EVIDENCE_STORE": str(self.durable)}), inherited)
        with self.assertRaisesRegex(EvidenceError, "refuses it"):
            te.durable_store_environment(self.dev, {"CRUX_TEST_EVIDENCE_STORE": str(self.parent / "elsewhere")})
        with self.assertRaisesRegex(EvidenceError, "not a Git repository"):
            te.durable_store_environment(self.parent / "not-a-repo")

    def test_a_staged_run_on_the_release_path_needs_the_dev_root_to_find_the_durable_store(self):
        stage = self.parent / "stage"
        stage.mkdir()
        with patch.dict(os.environ, {"CRUX_TEST_EVIDENCE_DURABLE_ONLY": "1", "CRUX_TEST_EVIDENCE_STORE": str(self.durable)}):
            with self.assertRaisesRegex(EvidenceError, "not a Git repository"):
                te.storage(stage)
            self.assertEqual(te.storage(stage, self.dev).resolve(), self.durable.resolve())


class CompletenessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.store = self.root / "store"
        patcher = patch.dict(os.environ, {"CRUX_TEST_EVIDENCE_STORE": str(self.store)})
        patcher.start()
        self.addCleanup(patcher.stop)
        (self.root / "input.txt").write_text("one")
        self.declaration = {"check_id": "unit", "command": [sys.executable, "-c", "print('ok')"], "inputs": ["input.txt"], "environment": []}
        self.record = execute(self.root, self.declaration)["evidence"]

    def test_a_present_sealed_receipt_with_its_log_is_complete(self):
        verdict = completeness(self.store, self.record["id"])
        self.assertEqual((verdict["complete"], verdict["seal"], verdict["log"], verdict["problems"]), (True, "valid", "ok", []))

    def test_each_kind_of_incompleteness_is_named(self):
        cases = {}
        missing = "TE-" + "0" * 32
        cases["missing receipt"] = (missing, "receipt missing")
        broken = variant(self.store, self.record["id"], lambda r: None)
        path = self.store / (broken["id"] + ".json")
        path.write_text(path.read_text().replace('"seconds"', '"seconds_": 1, "x"', 1))
        cases["broken seal"] = (broken["id"], "invalid evidence")
        no_log = variant(self.store, self.record["id"], lambda r: None)
        (self.store / no_log["output"]).unlink()
        cases["missing log"] = (no_log["id"], "output log missing")
        wrong = variant(self.store, self.record["id"], lambda r: None, new_log=b"different bytes")
        cases["mismatched log"] = (wrong["id"], "output log mismatch")
        for label, (evidence_id, expected) in cases.items():
            with self.subTest(label):
                verdict = completeness(self.store, evidence_id)
                self.assertFalse(verdict["complete"])
                self.assertTrue(any(expected in problem for problem in verdict["problems"]), verdict["problems"])

    def test_an_incomplete_passed_receipt_never_counts(self):
        (self.store / self.record["output"]).unlink()
        self.assertFalse(completeness(self.store, self.record["id"])["complete"])
        found = lookup(self.root, self.declaration)
        self.assertEqual(found["state"], "missing")
        self.assertEqual(found["ignored"][0]["id"], self.record["id"])
        self.assertIn("output log missing", found["ignored"][0]["reason"])
        self.assertEqual(execute(self.root, self.declaration)["action"], "executed")

    def test_a_complete_version_1_receipt_is_complete_and_not_eligible(self):
        def to_v1(r):
            r["schema_version"] = 1
            for key in ("environment", "tools", "lock_sha256", "source_revision"):
                r.pop(key)
            r["snapshot"] = {"fingerprint": r["fingerprint"], "inputs": r["snapshot"]["inputs"], "identity": {"environment_sha256": "0" * 64}}
        old = variant(self.store, self.record["id"], to_v1)
        verdict = completeness(self.store, old["id"])
        self.assertTrue(verdict["complete"])
        eligibility = reuse_eligibility(self.root, old["id"])
        self.assertFalse(eligibility["eligible"])
        self.assertIn("environment-not-comparable (schema_version 1)", eligibility["reasons"][0])

    def test_completeness_does_not_imply_eligibility_and_eligibility_does_not_imply_completeness(self):
        self.assertTrue(completeness(self.store, self.record["id"])["complete"])
        self.assertTrue(reuse_eligibility(self.root, self.record["id"])["eligible"])
        (self.root / "input.txt").write_text("two")
        self.assertTrue(completeness(self.store, self.record["id"])["complete"])
        stale = reuse_eligibility(self.root, self.record["id"])
        self.assertFalse(stale["eligible"])
        self.assertIn("relevant inputs changed", stale["reasons"][0])

    def test_a_compressed_log_verifies_on_its_decompressed_bytes(self):
        big = variant(self.store, self.record["id"], lambda r: r.update(output_sha256=hashlib.sha256(b"line\n" * 400000).hexdigest()),
                      new_log=b"line\n" * 400000)
        retained = self.root / "retained"
        result = retention_copy(self.store, big["id"], retained)
        self.assertEqual(result["compressed"], [big["output"]])
        self.assertFalse((retained / big["output"]).exists())
        self.assertTrue((retained / (big["output"] + ".gz")).is_file())
        self.assertLess((retained / (big["output"] + ".gz")).stat().st_size, 100000)
        self.assertTrue(completeness(retained, big["id"])["complete"])
        (retained / (big["output"] + ".gz")).write_bytes(gzip.compress(b"other\n" * 400000))
        wrong = completeness(retained, big["id"])
        self.assertFalse(wrong["complete"])
        self.assertIn("output log mismatch", wrong["problems"][0])

    def test_a_log_with_a_secret_is_withheld_and_the_withholding_recorded(self):
        leaky = variant(self.store, self.record["id"], lambda r: r.update(output_sha256=hashlib.sha256(f"key {SECRET}\n".encode()).hexdigest()),
                        new_log=f"key {SECRET}\n".encode())
        self.assertEqual(scan_logs(self.store, [leaky["id"]]), [{"file": leaky["output"], "shapes": ["openrouter-key"]}])
        self.assertEqual(scan_logs(self.store, [self.record["id"]]), [])
        retained = self.root / "retained"
        result = retention_copy(self.store, leaky["id"], retained)
        self.assertEqual(result["withheld"], [{"file": leaky["output"], "shapes": ["openrouter-key"]}])
        self.assertEqual(result["copied"], [leaky["id"] + ".json"])
        marker = json.loads((retained / (leaky["output"] + ".withheld.json")).read_text())
        self.assertEqual(marker["shapes"], ["openrouter-key"])
        self.assertNotIn(SECRET, json.dumps(marker))
        self.assertFalse((retained / leaky["output"]).exists())
        verdict = completeness(retained, leaky["id"])
        self.assertFalse(verdict["complete"])
        self.assertIn("output log withheld", verdict["problems"][0])

    def test_the_scan_runs_on_uncompressed_bytes(self):
        text = (b"filler\n" * 200000) + f"key {SECRET}\n".encode()
        leaky = variant(self.store, self.record["id"], lambda r: r.update(output_sha256=hashlib.sha256(text).hexdigest()), new_log=text)
        retained = self.root / "retained"
        result = retention_copy(self.store, leaky["id"], retained)
        self.assertEqual([w["file"] for w in result["withheld"]], [leaky["output"]])
        self.assertEqual(result["compressed"], [])
        self.assertFalse((retained / (leaky["output"] + ".gz")).exists())


class Cyc0009Tests(unittest.TestCase):
    """A read-only run over the committed copies reproduces the historian's account."""

    DIRECTORY = REPO_ROOT / "bionic/cycles/CYC-0009/evidence/final-dry-run"
    IDS = {"TE-a4438fcac3e84733a69106e88d82066c": "checkout core", "TE-616e046290bd4dabbc00c299b3847306": "checkout tools",
           "TE-7fecfe28266847b0942ba87af9541898": "staged 3.13", "TE-beca6aef3d434a9a98d24a1e9b155099": "staged 3.14"}

    @staticmethod
    def snapshot(directory):
        return {str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(directory).rglob("*")) if p.is_file()}

    def test_four_seals_valid_four_logs_missing_environment_not_comparable(self):
        require_dev_surface(self, self.DIRECTORY, "CYC-0009 retained receipts")
        cycle = REPO_ROOT / "bionic/cycles/CYC-0009"
        before = self.snapshot(cycle)
        with tempfile.TemporaryDirectory() as scratch:
            with patch.dict(os.environ, {"CRUX_TEST_EVIDENCE_STORE": scratch}):
                for evidence_id, label in self.IDS.items():
                    with self.subTest(label):
                        verdict = completeness(self.DIRECTORY, evidence_id)
                        self.assertEqual(verdict["seal"], "valid")
                        self.assertEqual(verdict["log"], "missing")
                        self.assertFalse(verdict["complete"])
                        eligibility = reuse_eligibility(REPO_ROOT, evidence_id, directory=self.DIRECTORY)
                        self.assertFalse(eligibility["eligible"])
                        self.assertIn("environment-not-comparable (schema_version 1)", eligibility["reasons"][0])
                        self.assertEqual(raw_receipt(self.DIRECTORY, evidence_id)["status"], "passed")
                self.assertEqual(list(Path(scratch).iterdir()), [], "a read-only report must not write a store")
        self.assertEqual(self.snapshot(cycle), before, "no CYC-0009 file may change")


if __name__ == "__main__":
    unittest.main()
