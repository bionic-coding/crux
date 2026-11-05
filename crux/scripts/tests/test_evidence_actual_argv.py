"""Generic evidence executes requested argv while reusing canonical check identity."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
from test_evidence import EvidenceError, execute, normalize, validate_evidence


class ActualArgvTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.store = self.root / "evidence"
        environment = patch.dict(os.environ, {"CRUX_TEST_EVIDENCE_STORE": str(self.store)})
        environment.start()
        self.addCleanup(environment.stop)
        suite = self.root / "suite"
        suite.mkdir()
        (suite / "test_tiny.py").write_text(
            "import unittest\nclass Tiny(unittest.TestCase):\n    def test_ok(self): pass\n")
        (self.root / "weights.json").write_text('{"test_tiny": 0.01}\n')
        self.command = [sys.executable, str(SCRIPTS / "tests/parallel_suite.py"), "suite",
                        "--workers", "1", "--records", "requested.jsonl", "--timings", "weights.json"]
        self.check = {"check_id": "actual-argv", "command": self.command, "inputs": ["suite"]}

    def cli(self, action, check=None):
        path = self.root / "check.json"
        path.write_text(json.dumps(check or self.check))
        result = subprocess.run([sys.executable, str(SCRIPTS / "test-evidence.py"), action,
                                 "--repo-root", str(self.root), "--check", str(path)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def assert_requested_run(self, result, command):
        self.assertEqual((result["action"], result["evidence"]["status"]), ("executed", "passed"))
        record = result["evidence"]
        self.assertEqual(record["executed_command"], command)
        self.assertEqual(record["declaration"], normalize(self.check))
        self.assertEqual(normalize(dict(self.check, command=command)), record["declaration"])
        rows = [json.loads(line) for line in (self.root / command[command.index("--records") + 1]).read_text().splitlines()]
        self.assertTrue(any(row.get("id") == "test_tiny.Tiny.test_ok" and row.get("outcome") == "ok" for row in rows), rows)
        log = (self.store / record["output"]).read_text()
        self.assertIn("requested 1,", log)
        self.assertIn("timings weights.json (1 entries)", log)
        self.assertEqual(record["environment"]["implementation"], "cpython")
        self.assertEqual(record["environment"]["version_info"][:2], list(sys.version_info[:2]))
        validate_evidence(self.root, record["id"], "actual-argv")

    def test_fresh_generic_cli_executes_requested_records_workers_and_timings(self):
        self.assert_requested_run(self.cli("run"), self.command)

    def test_default_library_execution_retains_raw_argv_without_mutating_declaration(self):
        before = copy.deepcopy(self.check)
        self.assert_requested_run(execute(self.root, self.check), self.command)
        self.assertEqual(self.check, before)

    def test_explicit_override_preserves_actual_argv_with_a_canonical_declaration(self):
        self.assert_requested_run(execute(self.root, normalize(self.check), execution_command=self.command), self.command)

    def test_reuse_keeps_original_execution_and_creates_no_new_requested_output(self):
        first = self.cli("run")
        self.assert_requested_run(first, self.command)
        alternate = list(self.command)
        alternate[alternate.index("--workers") + 1] = "2"
        alternate[alternate.index("--records") + 1] = "not-created.jsonl"
        alternate[alternate.index("--timings") + 1] = "not-read.json"
        equivalent = dict(self.check, command=alternate)
        self.assertEqual(normalize(equivalent), normalize(self.check))
        found = self.cli("lookup", equivalent)
        self.assertEqual((found["state"], found["record"]["id"]), ("passed", first["evidence"]["id"]))
        reused = self.cli("run", equivalent)
        self.assertEqual(reused["action"], "reused")
        self.assertEqual(reused["evidence"], first["evidence"])
        self.assertFalse((self.root / "not-created.jsonl").exists())
        self.assertEqual(len(list(self.store.glob("TE-*.json"))), 1)
        self.assertEqual(len(list(self.store.glob("TE-*.log"))), 1)

    def test_explicit_override_mismatch_refuses_even_when_a_pass_exists(self):
        self.assert_requested_run(execute(self.root, self.check), self.command)
        changed = list(self.command)
        changed[2] = "different-suite"
        with self.assertRaisesRegex(EvidenceError, "execution command changes test discovery"):
            execute(self.root, self.check, execution_command=changed)
        self.assertEqual(len(list(self.store.glob("TE-*.json"))), 1)

    def test_credentials_in_default_scheduling_arguments_refuse_before_storage(self):
        secret = "private-argv-credential-sentinel"
        self.command[self.command.index("--records") + 1] = secret + ".jsonl"
        with patch.dict(os.environ, {"EXAMPLE_API_KEY": secret}), \
             patch("test_evidence._launch", return_value=(0, b"", None)) as launched:
            with self.assertRaisesRegex(EvidenceError, "commands must not contain credential environment values"):
                execute(self.root, self.check)
        launched.assert_not_called()
        self.assertFalse(self.store.exists())

    def test_credentials_in_default_and_explicit_interpreter_tokens_refuse_before_storage(self):
        secret = "synthetic-interpreter-argv-secret-0100"
        actual = [str(self.root / secret / "bin/python3"), "-c", "pass"]
        raw = dict(self.check, command=actual)
        for override in (False, True):
            store = self.root / ("explicit-store" if override else "default-store")
            environment = {"PATH": os.defpath, "EXAMPLE_API_KEY": secret,
                           "CRUX_TEST_EVIDENCE_STORE": str(store)}
            options = {"execution_command": actual} if override else {}
            with self.subTest(explicit_override=override), patch.dict(os.environ, environment, clear=True), \
                 patch("test_evidence._launch", return_value=(0, b"", None)) as launched:
                with self.assertRaisesRegex(EvidenceError, "commands must not contain credential environment values"):
                    execute(self.root, normalize(raw) if override else raw, **options)
                launched.assert_not_called()
                self.assertFalse(store.exists())


if __name__ == "__main__":
    unittest.main()
