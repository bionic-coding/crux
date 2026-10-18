"""Evidence reuse tests execute tiny commands, never the checkout suite."""
import concurrent.futures
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_evidence import EvidenceError, execute, lookup, snapshot, validate_evidence


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.env = patch.dict(os.environ, {"CRUX_TEST_EVIDENCE_STORE": str(self.root / "evidence")})
        self.env.start()
        self.addCleanup(self.env.stop)
        (self.root / "input.txt").write_text("one")
        self.check = {"check_id": "unit", "command": [sys.executable, "-c", "print('passed')"], "inputs": ["input.txt"], "environment": ["TEST_EVIDENCE_CONTEXT"]}

    def test_reuse_and_actual_working_tree_invalidation(self):
        first = execute(self.root, self.check)
        (self.root / "review.md").write_text("bookkeeping")
        second = execute(self.root, self.check)
        self.assertEqual(second["action"], "reused")
        self.assertEqual(first["evidence"]["id"], second["evidence"]["id"])
        validate_evidence(self.root, first["evidence"]["id"], "unit")
        (self.root / "input.txt").write_text("two")
        self.assertEqual(lookup(self.root, self.check)["state"], "inputs-changed")
        with self.assertRaises(EvidenceError):
            validate_evidence(self.root, first["evidence"]["id"])
        self.assertEqual(execute(self.root, self.check)["evidence"]["reason"], "inputs-changed")

    def test_failure_requires_reason_and_remains_visible(self):
        self.check["command"][-1] = "raise SystemExit(1)"
        first = execute(self.root, self.check)
        with self.assertRaisesRegex(EvidenceError, "retry reason"):
            execute(self.root, self.check)
        second = execute(self.root, self.check, "investigate transient failure")
        self.assertNotEqual(first["evidence"]["id"], second["evidence"]["id"])
        self.assertEqual(len(list((self.root / "evidence").glob("TE-*.json"))), 2)

    def test_deleted_python_environment_revalidates_only_equivalent_runtime(self):
        import shutil
        import subprocess
        import venv
        runtimes = []
        for name in ("first-env", "second-env"):
            directory = self.root / name
            venv.EnvBuilder(with_pip=False, symlinks=True).create(directory)
            runtimes.append(directory / "bin/python")
        declaration = dict(self.check, command=[str(runtimes[0]), "-c", "print('passed')"])
        record = execute(self.root, declaration)["evidence"]
        receipt = self.root / "evidence" / (record["id"] + ".json")
        original = receipt.read_bytes()
        shutil.rmtree(runtimes[0].parent.parent)
        replacement = dict(declaration, command=[str(runtimes[1]), *declaration["command"][1:]])
        self.assertEqual(execute(self.root, replacement)["action"], "reused")
        with patch("test_evidence.sys.executable", str(runtimes[1])):
            self.assertEqual(validate_evidence(self.root, record["id"])["id"], record["id"])
            with patch.dict(os.environ, {"TEST_EVIDENCE_CONTEXT": "changed"}):
                with self.assertRaises(EvidenceError):
                    validate_evidence(self.root, record["id"])
            site = Path(subprocess.check_output(
                [str(runtimes[1]), "-c", "import sysconfig; print(sysconfig.get_path('purelib'))"],
                text=True).strip())
            package = site / "changed_package-1.0.dist-info"
            package.mkdir()
            (package / "METADATA").write_text("Name: changed-package\nVersion: 1.0\n")
            with self.assertRaises(EvidenceError):
                validate_evidence(self.root, record["id"])
        with patch("test_evidence.sys.executable", "/bin/sh"):
            with self.assertRaises(EvidenceError):
                validate_evidence(self.root, record["id"])
        self.assertEqual(receipt.read_bytes(), original)

    def test_environment_and_freshness(self):
        first = execute(self.root, self.check)
        with patch.dict(os.environ, {"TEST_EVIDENCE_CONTEXT": "secret-value"}):
            self.assertEqual(lookup(self.root, self.check)["state"], "inputs-changed")
            record = execute(self.root, self.check)["evidence"]
            self.assertNotIn("secret-value", json.dumps(record))
        self.check["freshness_seconds"] = 1
        record = execute(self.root, self.check)["evidence"]
        with patch("test_evidence.time.time", return_value=record["finished_at"] + 2):
            self.assertEqual(lookup(self.root, self.check)["state"], "expired")

    def test_drift_during_execution_is_not_a_pass(self):
        self.check["command"][-1] = "from pathlib import Path; Path('input.txt').write_text('changed')"
        record = execute(self.root, self.check)["evidence"]
        self.assertEqual(record["status"], "inputs-changed")
        with self.assertRaises(EvidenceError):
            validate_evidence(self.root, record["id"])

    def test_concurrent_execution_is_deduplicated(self):
        self.check["command"][-1] = "import time; time.sleep(.1); print('once')"
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: execute(self.root, self.check), range(2)))
        self.assertEqual(sorted(r["action"] for r in results), ["executed", "reused"])
        self.assertEqual(results[0]["evidence"]["id"], results[1]["evidence"]["id"])

    def test_output_and_record_integrity(self):
        record = execute(self.root, self.check)["evidence"]
        (self.root / "evidence" / record["output"]).write_text("changed")
        with self.assertRaisesRegex(EvidenceError, "output"):
            validate_evidence(self.root, record["id"])

    def test_glob_addition_and_executable_mode_invalidate(self):
        self.check["inputs"] = ["*.txt"]
        before = snapshot(self.root, self.check)
        (self.root / "new.txt").write_text("new")
        after = snapshot(self.root, self.check)
        self.assertNotEqual(before["fingerprint"], after["fingerprint"])
        (self.root / "new.txt").chmod(0o700)
        self.assertNotEqual(after["fingerprint"], snapshot(self.root, self.check)["fingerprint"])

    def test_escaping_inputs_and_symlinks_refused(self):
        self.check["inputs"] = ["../outside"]
        with self.assertRaises(EvidenceError):
            snapshot(self.root, self.check)
        (self.root / "link").symlink_to(self.root / "input.txt")
        self.check["inputs"] = ["link"]
        with self.assertRaises(EvidenceError):
            snapshot(self.root, self.check)

    def test_staged_evidence_reuses_identical_relocated_artifact(self):
        other = self.root / "stage-two"
        other.mkdir()
        (other / "input.txt").write_text("one")
        with patch.dict(os.environ, {"TEST_EVIDENCE_CONTEXT": str(self.root / "scripts")}):
            first = execute(self.root, self.check)
        with patch.dict(os.environ, {"TEST_EVIDENCE_CONTEXT": str(other / "scripts")}):
            second = execute(other, self.check)
        self.assertEqual(second["action"], "reused")
        self.assertEqual(second["evidence"]["id"], first["evidence"]["id"])
        self.assertFalse((other / ".crux-test-evidence").exists())

    def test_command_override_cannot_substitute_a_passing_program(self):
        with self.assertRaises(EvidenceError):
            execute(self.root, self.check, execution_command=[sys.executable, "-c", "pass"])

    def test_schema_accepts_execution_record(self):
        import council_records
        validator = council_records._validator()
        schema = validator.load_schema(Path(__file__).resolve().parents[2] / "schemas/test-evidence.schema.json")
        errors = []
        validator.validate(execute(self.root, self.check)["evidence"], schema, "#", "#", errors, "test-evidence")
        self.assertEqual(errors, [])

    def test_suite_adapter_preserves_discovery_and_declares_environment(self):
        from types import SimpleNamespace
        from suite_evidence import run_shared
        args = SimpleNamespace(start="crux/scripts/tests", pattern="test_*.py", top=None,
                               workers=4, records=None, timings=None,
                               evidence_scope="staged", retry_reason=None)
        with patch("suite_evidence.evidence_plan", return_value=({"state": "missing"}, {"state": "missing"})), \
             patch("suite_evidence.execute", side_effect=EvidenceError("stop before execution")) as mocked:
            with self.assertRaises(EvidenceError):
                run_shared(args)
        declaration = mocked.call_args.args[1]
        self.assertTrue(declaration["check_id"].startswith("staged:"))
        self.assertIn("PYTHONPATH", declaration["environment"])
        self.assertIn("UV_PYTHON", declaration["environment"])
        self.assertIn("uv.lock", declaration["inputs"])
        self.assertIn(".generated", declaration["inputs"])
        self.assertNotIn("--workers", declaration["command"])
        self.assertIn("--workers", mocked.call_args.kwargs["execution_command"])

    def test_shared_suite_cli_executes_once_then_reuses(self):
        import shutil
        import subprocess
        source = Path(__file__).resolve().parents[1]
        scripts = self.root / "crux/scripts"
        tests = scripts / "tests"
        tests.mkdir(parents=True)
        for name in ("test_evidence.py", "suite_evidence.py"):
            shutil.copyfile(source / name, scripts / name)
        shutil.copyfile(source / "tests/parallel_suite.py", tests / "parallel_suite.py")
        tiny = self.root / "tools/tests"
        tiny.mkdir(parents=True)
        (tiny / "test_tiny.py").write_text("import unittest\nclass Tiny(unittest.TestCase):\n    def test_ok(self): self.assertTrue(True)\n")
        command = [sys.executable, "crux/scripts/tests/parallel_suite.py", "tools/tests", "--shared-evidence", "--workers", "1"]
        first = subprocess.run(command, cwd=self.root, capture_output=True, text=True)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertIn("Test evidence executed:", first.stdout)
        second = subprocess.run(command, cwd=self.root, capture_output=True, text=True)
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertIn("Test evidence reused:", second.stdout)

    def test_credential_output_is_redacted_before_storage(self):
        self.check["command"][-1] = "import os; print(os.environ['EXAMPLE_API_KEY'])"
        with patch.dict(os.environ, {"EXAMPLE_API_KEY": "private-credential-value"}):
            record = execute(self.root, self.check)["evidence"]
        output = (self.root / "evidence" / record["output"]).read_text()
        self.assertNotIn("private-credential-value", output)
        self.assertIn("[REDACTED]", output)

    def test_hidden_local_skill_changes_invalidate_suite_evidence(self):
        from suite_evidence import INPUTS
        self.check["inputs"] = INPUTS
        for location in (".claude/skills", ".agents/skills", ".opencode/skills", ".opencode/skill"):
            with self.subTest(location=location):
                skill = self.root / location / "example/SKILL.md"
                skill.parent.mkdir(parents=True)
                skill.write_text("before")
                before = snapshot(self.root, self.check)
                self.assertIn(skill.relative_to(self.root).as_posix(), before["inputs"])
                skill.write_text("after")
                self.assertNotEqual(before["fingerprint"], snapshot(self.root, self.check)["fingerprint"])

    def test_git_inventory_and_tracked_content_invalidate_suite_evidence(self):
        import subprocess
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        self.check["git_tracked"] = True
        extra = self.root / ".hidden-input"
        extra.write_text("one")
        before = snapshot(self.root, self.check)
        subprocess.run(["git", "add", ".hidden-input"], cwd=self.root, check=True)
        indexed = snapshot(self.root, self.check)
        self.assertNotEqual(before["fingerprint"], indexed["fingerprint"])
        self.assertIn(".hidden-input", indexed["inputs"])
        extra.write_text("two")
        self.assertNotEqual(indexed["fingerprint"], snapshot(self.root, self.check)["fingerprint"])

    def test_broad_suite_evidence_survives_real_cycle_attachment(self):
        import subprocess
        from suite_evidence import INPUTS, runtime_exclusions
        from cycle_workflow import create, mutate, check_tests, tree
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        docs = self.root / "bionic"
        docs.mkdir()
        (docs / "manifest.yml").write_text('schema_version: "5"\nconcerns_enabled: [adrs]\nadr:\n  next_number: 1\n')
        (docs / "objectives.md").write_text("Preserve useful evidence")
        cycle = create(self.root, "quick-fix", "Fix", "Correct behavior", ["input.txt"], ["Works"], "builder", "tester")
        cycle = mutate(self.root, cycle["id"], "checks", checks=["unit"])
        cycle = mutate(self.root, cycle["id"], "coverage", coverage={
            "affected": ["Broad suite evidence survives cycle bookkeeping attachment"],
            "checks": [{"check_id": "unit", "rationale": "Tiny command supplies evidence whose declared broad inputs are checked before and after cycle mutation"}],
            "not_selected": "No full suite needed for this isolated evidence fixture; cycle bookkeeping is excluded because the check does not read it.",
        })
        self.check.update(inputs=INPUTS, git_tracked=True, exclude_inputs=runtime_exclusions(self.root))
        evidence = execute(self.root, self.check)["evidence"]
        cycle = mutate(self.root, cycle["id"], "evidence", check_id="unit", evidence_id=evidence["id"], use="executed")
        check_tests(tree(self.root), cycle)
        subprocess.run(["git", "add", "bionic/cycles"], cwd=self.root, check=True)
        check_tests(tree(self.root), cycle)
        self.assertEqual(lookup(self.root, self.check)["state"], "passed")
        explicit = dict(self.check, check_id="live-cycle", inputs=["bionic/cycles"], exclude_inputs=[], git_tracked=False)
        before = snapshot(self.root, explicit)
        cycle = mutate(self.root, cycle["id"], "checks", checks=["unit", "other"])
        self.assertNotEqual(before["fingerprint"], snapshot(self.root, explicit)["fingerprint"])
        (docs / "objectives.md").write_text("Changed static requirement")
        self.assertEqual(lookup(self.root, self.check)["state"], "inputs-changed")

    def test_head_relative_inputs_invalidate_after_soft_reset(self):
        import subprocess
        def git(*args):
            return subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args], cwd=self.root, capture_output=True, check=True)
        git("init", "-q")
        git("add", "input.txt")
        git("commit", "-qm", "first")
        (self.root / "input.txt").write_text("two")
        git("add", "input.txt")
        git("commit", "-qm", "second")
        self.check.update(git_tracked=True, command=["git", "diff", "--exit-code", "HEAD", "--", "input.txt"])
        record = execute(self.root, self.check)["evidence"]
        self.assertEqual(record["status"], "passed")
        git("reset", "--soft", "HEAD^")
        self.assertEqual(lookup(self.root, self.check)["state"], "inputs-changed")
        self.assertEqual(execute(self.root, self.check)["evidence"]["status"], "failed")

    def test_excluded_bookkeeping_commit_preserves_head_fingerprint(self):
        import subprocess
        def git(*args):
            return subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args], cwd=self.root, capture_output=True, check=True)
        git("init", "-q")
        git("add", "input.txt")
        git("commit", "-qm", "initial")
        self.check.update(git_tracked=True, exclude_inputs=["bionic/cycles"])
        before = execute(self.root, self.check)["evidence"]
        cycle = self.root / "bionic/cycles/CYC-0001/cycle.json"
        cycle.parent.mkdir(parents=True)
        cycle.write_text("{}")
        git("add", "bionic/cycles")
        git("commit", "-qm", "bookkeeping")
        after = execute(self.root, self.check)
        self.assertEqual(after["action"], "reused")
        self.assertEqual(after["evidence"]["id"], before["id"])


if __name__ == "__main__":
    unittest.main()
