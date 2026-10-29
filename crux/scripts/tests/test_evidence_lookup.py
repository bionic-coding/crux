"""One lookup rule, and how a finished or interrupted execution is classified."""
import concurrent.futures
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _evidence_fixtures import variant
import test_evidence as te
from test_evidence import EvidenceError, execute, lookup, validate_evidence

SCRIPTS = Path(__file__).resolve().parents[1]
DRIVER = SCRIPTS / "tests" / "parallel_suite.py"


class LookupBase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.store = self.root / "evidence"
        patcher = patch.dict(os.environ, {"CRUX_TEST_EVIDENCE_STORE": str(self.store)})
        patcher.start()
        self.addCleanup(patcher.stop)
        (self.root / "input.txt").write_text("one")
        self.marker = self.root / "executions"

    def check(self, body="print('ok')", check_id="unit", **extra):
        code = f"from pathlib import Path\nwith Path({str(self.marker)!r}).open('a') as m: m.write('x')\n{body}\n"
        return dict({"check_id": check_id, "command": [sys.executable, "-c", code], "inputs": ["input.txt"], "environment": []}, **extra)

    def executions(self):
        return len(self.marker.read_text()) if self.marker.exists() else 0


class LookupRuleTests(LookupBase):
    def test_newest_failure_on_equal_inputs_refuses_execution_without_a_retry_reason(self):
        decl = self.check("raise SystemExit(1)")
        failed = execute(self.root, decl)["evidence"]
        self.assertEqual(failed["status"], "failed")
        with self.assertRaisesRegex(EvidenceError, "retry reason"):
            execute(self.root, decl)
        with self.assertRaisesRegex(EvidenceError, "retry reason"):
            execute(self.root, decl, "  ")
        self.assertEqual(self.executions(), 1, "a refused retry must not run the check")
        found = lookup(self.root, decl)
        self.assertEqual((found["state"], found["record"]["id"]), ("failed", failed["id"]))

    def test_a_retry_with_a_stated_reason_that_passes_is_reused_and_the_failure_stays_visible(self):
        decl = self.check("import sys\nsys.exit(0 if Path('toggle').exists() else 1)")
        failed = execute(self.root, decl)["evidence"]
        self.assertEqual(failed["status"], "failed")
        (self.root / "toggle").write_text("")  # not an input: the retry runs on equal inputs
        retried = execute(self.root, decl, "the first run hit a transient fault")
        self.assertEqual((retried["action"], retried["evidence"]["status"]), ("executed", "passed"))
        self.assertEqual(retried["evidence"]["reason"], "the first run hit a transient fault")
        self.assertEqual(retried["earlier_failures"], [failed["id"]])
        again = execute(self.root, decl)
        self.assertEqual((again["action"], again["evidence"]["id"]), ("reused", retried["evidence"]["id"]))
        self.assertEqual(again["earlier_failures"], [failed["id"]])
        self.assertEqual(self.executions(), 2)

    def test_a_sealed_failure_whose_output_log_is_missing_still_blocks(self):
        decl = self.check("raise SystemExit(1)")
        failed = execute(self.root, decl)["evidence"]
        (self.store / failed["output"]).unlink()
        self.assertEqual(lookup(self.root, decl)["state"], "failed")
        with self.assertRaisesRegex(EvidenceError, "retry reason"):
            execute(self.root, decl)

    def test_a_failure_from_a_non_satisfying_environment_neither_passes_nor_blocks(self):
        decl = self.check("raise SystemExit(1)")
        failed = execute(self.root, decl)["evidence"]
        elsewhere = variant(self.store, failed["id"], lambda r: r["environment"]["sys_flags"].__setitem__("optimize", 1))
        (self.store / (failed["id"] + ".json")).unlink()
        found = lookup(self.root, decl)
        self.assertEqual(found["state"], "missing")
        self.assertIn(elsewhere["id"], [i["id"] for i in found["ignored"]])
        self.assertIn("sys.flags.optimize", found["ignored"][0]["reason"])
        again = execute(self.root, decl)  # no retry reason: the foreign failure does not block
        self.assertEqual(again["action"], "executed")

    def test_version_1_and_interrupted_receipts_neither_pass_nor_block(self):
        decl = self.check()
        passed = execute(self.root, decl)["evidence"]
        def to_v1(r):
            r["schema_version"] = 1
            for key in ("environment", "tools", "lock_sha256", "source_revision"):
                r.pop(key)
            r["snapshot"] = {"fingerprint": r["fingerprint"], "inputs": r["snapshot"]["inputs"], "identity": {}}
            r["status"] = "failed"
            r["returncode"] = 1
        old = variant(self.store, passed["id"], to_v1)
        interrupted = variant(self.store, passed["id"], lambda r: r.update(status="interrupted", returncode=None))
        newest_pass = lookup(self.root, decl)
        self.assertEqual((newest_pass["state"], newest_pass["record"]["id"]), ("passed", passed["id"]))
        self.assertIn(old["id"], [i["id"] for i in newest_pass["ignored"]])
        (self.store / (passed["id"] + ".json")).unlink()
        none = lookup(self.root, decl)
        self.assertEqual(none["state"], "missing")
        self.assertEqual({i["id"] for i in none["ignored"]}, {old["id"], interrupted["id"]})
        self.assertEqual(execute(self.root, decl)["action"], "executed")

    def test_a_seal_failing_receipt_stops_lookup_and_a_moved_file_no_longer_blocks(self):
        decl = self.check()
        record = execute(self.root, decl)["evidence"]
        path = self.store / (record["id"] + ".json")
        text = path.read_text()
        path.write_text(text.replace('"seconds"', '"seconds ": 0, "was"', 1))
        with self.assertRaises(EvidenceError) as caught:
            lookup(self.root, decl)
        self.assertIn(path.name, str(caught.exception))
        with self.assertRaisesRegex(EvidenceError, path.name):
            execute(self.root, decl)
        quarantine = self.store / "quarantine"
        quarantine.mkdir()
        shutil.move(str(path), str(quarantine / path.name))
        self.assertEqual(lookup(self.root, decl)["state"], "missing")

    def test_a_newer_failure_after_a_pass_decides(self):
        decl = self.check()
        passed = execute(self.root, decl)["evidence"]
        failure = variant(self.store, passed["id"], lambda r: r.update(status="failed", returncode=1))
        found = lookup(self.root, decl)
        self.assertEqual((found["state"], found["record"]["id"]), ("failed", failure["id"]))

    def test_freshness_expires_the_newest_pass(self):
        decl = self.check(freshness_seconds=5)
        record = execute(self.root, decl)["evidence"]
        with patch("test_evidence.time.time", return_value=record["finished_at"] + 6):
            self.assertEqual(lookup(self.root, decl)["state"], "expired")
            self.assertEqual(execute(self.root, decl)["evidence"]["reason"], "expired")

    def test_verify_waits_for_a_matching_execution_in_progress(self):
        decl = self.check("import time\ntime.sleep(1.0)\nprint('done')")
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(execute, self.root, decl)
            time.sleep(0.4)
            second = pool.submit(execute, self.root, decl)
            results = [first.result(), second.result()]
        self.assertEqual(sorted(r["action"] for r in results), ["executed", "reused"])
        self.assertEqual(results[0]["evidence"]["id"], results[1]["evidence"]["id"])
        self.assertEqual(self.executions(), 1)


class ClassificationTests(LookupBase):
    def status(self, body, **kwargs):
        return execute(self.root, self.check(body), **kwargs)["evidence"]

    def test_a_child_exit_1_records_failed(self):
        record = self.status("raise SystemExit(1)")
        self.assertEqual((record["status"], record["returncode"]), ("failed", 1))

    def test_a_child_segfault_records_failed(self):
        record = self.status("import os, signal\nos.kill(os.getpid(), signal.SIGSEGV)")
        self.assertEqual(record["status"], "failed")
        self.assertEqual(record["returncode"], -signal.SIGSEGV)

    def test_every_exit_2_records_failed(self):
        self.assertEqual(self.status("raise SystemExit(2)")["status"], "failed")

    def test_a_launch_error_records_interrupted(self):
        record = execute(self.root, self.check(), interpreter=self.root / "no-such-python")["evidence"]
        self.assertEqual(record["status"], "interrupted")
        self.assertIsNone(record["returncode"])
        self.assertIn("launch error", record["reason"])
        self.assertEqual(lookup(self.root, self.check())["state"], "missing")

    def drive(self, name, exit_code):
        script = self.root / "tree" / name
        script.parent.mkdir(exist_ok=True)
        script.write_text(f"raise SystemExit({exit_code})\n")
        decl = {"check_id": f"{name}-{exit_code}", "command": ["python", f"tree/{name}"], "inputs": ["input.txt"], "environment": []}
        return execute(self.root, decl)["evidence"]

    def test_parallel_suite_exit_3_records_interrupted_and_exit_2_records_failed(self):
        self.assertEqual(self.drive("parallel_suite.py", 3)["status"], "interrupted")
        self.assertEqual(self.drive("parallel_suite.py", 2)["status"], "failed")
        self.assertEqual(self.drive("other_runner.py", 3)["status"], "failed", "exit 3 is interrupted only from a parallel_suite entry")

    def test_the_real_driver_refusing_its_interpreter_exits_3_and_records_interrupted(self):
        sandbox = self.root / "bare"
        import venv
        venv.EnvBuilder(with_pip=False, symlinks=True).create(sandbox)
        decl = {"check_id": "plugin-suite", "command": ["python", str(DRIVER), str(DRIVER.parent), "-p", "test_arch_facts.py"],
                "inputs": ["input.txt"], "environment": []}
        record = execute(self.root, decl, interpreter=sandbox / "bin" / "python")["evidence"]
        self.assertEqual(record["returncode"], 3)
        self.assertEqual(record["status"], "interrupted")
        self.assertIn("cannot import", (self.store / record["output"]).read_text())

    def test_a_worker_that_dies_records_failed_and_is_not_re_executed(self):
        tree = self.root / "dying"
        tree.mkdir()
        (tree / "test_dies.py").write_text("import os, unittest\nclass T(unittest.TestCase):\n    def test_dies(self):\n        os._exit(7)\n")
        decl = {"check_id": "dying-worker", "command": ["python", str(DRIVER), "dying", "--workers", "1"], "inputs": ["dying"], "environment": []}
        record = execute(self.root, decl)["evidence"]
        self.assertEqual(record["returncode"], 2, (self.store / record["output"]).read_text())
        self.assertEqual(record["status"], "failed")
        with self.assertRaisesRegex(EvidenceError, "retry reason"):
            execute(self.root, decl)

    def test_a_driver_that_passes_runs_under_the_capture_wrapper(self):
        tree = self.root / "fine"
        tree.mkdir()
        (tree / "test_fine.py").write_text("import unittest\nclass T(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n")
        decl = {"check_id": "fine-suite", "command": ["python", str(DRIVER), "fine", "--workers", "2"], "inputs": ["fine"], "environment": []}
        record = execute(self.root, decl)["evidence"]
        self.assertEqual(record["status"], "passed", (self.store / record["output"]).read_text())
        self.assertEqual(lookup(self.root, decl)["state"], "passed")


SIGNAL_ENGINE = textwrap.dedent('''
    import json, sys
    sys.path.insert(0, {scripts!r})
    import test_evidence as te
    result = te.execute({root!r}, json.load(open({declaration!r})))
    print(result["evidence"]["status"], flush=True)
''')


class EngineInterruptionTests(LookupBase):
    def sleeper(self, seconds):
        code = ("import os, subprocess, sys, time\n"
                f"grandchild = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep({seconds})'])\n"
                f"open({str(self.root / 'pids')!r}, 'w').write(str(os.getpid()) + ' ' + str(grandchild.pid))\n"
                f"time.sleep({seconds})\n")
        return {"check_id": "sleeper", "command": ["python", "-c", code], "inputs": ["input.txt"], "environment": []}

    def start_engine(self, seconds=60):
        self.pids = self.root / "pids"
        self.pids.unlink(missing_ok=True)
        declaration = self.root / "declaration.json"
        declaration.write_text(json.dumps(self.sleeper(seconds)))
        script = self.root / "engine.py"
        script.write_text(SIGNAL_ENGINE.format(scripts=str(SCRIPTS), root=str(self.root), declaration=str(declaration)))
        engine = subprocess.Popen([sys.executable, str(script)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                  env=dict(os.environ, CRUX_TEST_EVIDENCE_STORE=str(self.store)))
        self.addCleanup(lambda: engine.poll() is None and engine.kill())
        deadline = time.time() + 20
        while not self.pids.exists() and time.time() < deadline:
            time.sleep(0.05)
        self.assertTrue(self.pids.exists(), "the sleeping child never started")
        time.sleep(0.2)
        child, grandchild = (int(x) for x in self.pids.read_text().split())
        for pid in (child, grandchild):
            self.addCleanup(lambda p=pid: self.kill_quietly(p))
        return engine, child, grandchild

    @staticmethod
    def kill_quietly(pid):
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

    @staticmethod
    def alive(pid):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        return True

    def test_sigint_and_sigterm_terminate_the_child_group_and_record_interrupted(self):
        for number in (signal.SIGINT, signal.SIGTERM):
            with self.subTest(signal=number.name):
                shutil.rmtree(self.store, ignore_errors=True)
                engine, child, grandchild = self.start_engine()
                engine.send_signal(number)
                out, err = engine.communicate(timeout=30)
                self.assertEqual(out.strip(), "interrupted", err)
                deadline = time.time() + 10
                while (self.alive(child) or self.alive(grandchild)) and time.time() < deadline:
                    time.sleep(0.05)
                self.assertFalse(self.alive(child))
                self.assertFalse(self.alive(grandchild), "the grandchild outlived the interrupted run")
                receipts = [json.loads(p.read_text()) for p in self.store.glob("TE-*.json")]
                self.assertEqual([r["status"] for r in receipts], ["interrupted"])
                self.assertEqual(receipts[0]["signal"], number)

    def test_a_sigkilled_engine_leaves_no_receipt_and_the_next_lookup_executes(self):
        engine, child, grandchild = self.start_engine(seconds=5)
        engine.kill()
        engine.communicate(timeout=30)
        self.assertEqual(list(self.store.glob("TE-*.json")), [])
        declaration = self.sleeper(5)
        self.assertEqual(lookup(self.root, declaration)["state"], "missing")
        # The orphaned child still holds the declaration's execution lock. The next caller never starts
        # a duplicate beside it: it exits naming the dead engine and the child's process group.
        started = time.time()
        with self.assertRaisesRegex(EvidenceError, rf"engine pid {engine.pid} exited.*kill -TERM -{child}"):
            execute(self.root, declaration)
        self.assertLess(time.time() - started, 5.0)
        self.assertTrue(self.alive(child), "the waiter must not stop the orphaned child")
        self.assertEqual(list(self.store.glob("TE-*.json")), [])
        deadline = time.time() + 15
        while self.alive(child) and time.time() < deadline:
            time.sleep(0.05)
        self.assertFalse(self.alive(child))
        # Once the orphan has ended, the next caller acquires the lock and executes.
        result = execute(self.root, declaration)
        self.assertEqual((result["action"], result["evidence"]["status"]), ("executed", "passed"))
        self.assertEqual(len(list(self.store.glob("TE-*.json"))), 1)


if __name__ == "__main__":
    unittest.main()
