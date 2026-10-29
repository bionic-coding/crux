"""The engine's per-check lock names its holder, and a waiter reports an orphaned lock instead of blocking."""
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import test_evidence as te

SCRIPT = Path(__file__).resolve().parents[1] / "test-evidence.py"
HOLDER = """
import fcntl, json, os, sys, time
path, record, delay, hold = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
fcntl.flock(fd, fcntl.LOCK_EX)
print("ready", flush=True)
time.sleep(delay)
if record != "-":
    data = {k: (os.getpid() if v == "$self" else v) for k, v in json.loads(record).items()}
    os.write(fd, json.dumps(data).encode())
time.sleep(hold)
"""
LSOF = shutil.which("lsof") or ("/usr/sbin/lsof" if Path("/usr/sbin/lsof").exists() else None)


class LockBase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.env = dict(os.environ, CRUX_TEST_EVIDENCE_STORE=str(self.root / "store"))
        patcher = patch.dict(os.environ, {"CRUX_TEST_EVIDENCE_STORE": str(self.root / "store")})
        patcher.start()
        self.addCleanup(patcher.stop)
        (self.root / "input.txt").write_text("one")
        self.decl = {"check_id": "unit", "command": ["python", "-c", "print('ok')"], "inputs": ["input.txt"], "environment": []}
        self.lock_path = te.storage(self.root) / (te.digest(te.normalize(self.decl)) + ".lock")
        self.check = self.root / "check.json"
        self.check.write_text(json.dumps(self.decl))

    def dead_pid(self):
        process = subprocess.Popen([sys.executable, "-c", "pass"])
        process.wait()
        return process.pid

    def holder(self, record="-", delay=0.0, hold=60.0):
        process = subprocess.Popen([sys.executable, "-c", HOLDER, str(self.lock_path), record, str(delay), str(hold)],
                                   stdout=subprocess.PIPE, text=True, start_new_session=True)
        self.addCleanup(self.stop, process)
        self.assertEqual(process.stdout.readline().strip(), "ready")
        return process

    @staticmethod
    def stop(process):
        with_group = None
        try:
            with_group = os.getpgid(process.pid)
        except ProcessLookupError:
            pass
        if with_group is not None:
            try:
                os.killpg(with_group, signal.SIGKILL)
            except ProcessLookupError:
                pass
        process.wait()
        process.stdout.close()

    def run_cli(self, bound):
        """Run the check through the CLI; a blocked run is a failure, not a hang."""
        started = time.monotonic()
        try:
            result = subprocess.run([sys.executable, str(SCRIPT), "run", "--repo-root", str(self.root), "--check", str(self.check)],
                                    capture_output=True, text=True, env=self.env, timeout=bound)
        except subprocess.TimeoutExpired:
            self.fail(f"the run was still blocked on the lock after {bound} s")
        return result, time.monotonic() - started


class OrphanedLockTests(LockBase):
    def test_a_lock_held_by_a_live_child_of_a_dead_engine_exits_2_naming_engine_and_group(self):
        dead = self.dead_pid()
        holder = self.holder(json.dumps({"engine_pid": dead, "check_id": "unit", "started_at": 1, "child_pid": "$self"}))
        time.sleep(0.3)  # the helper writes its record after its delay of zero
        result, seconds = self.run_cli(40)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn(str(self.lock_path), result.stderr)
        self.assertIn(f"engine pid {dead}", result.stderr)
        self.assertIn(f"kill -TERM -{holder.pid}", result.stderr)
        self.assertLess(seconds, 20)
        self.assertIsNone(holder.poll(), "the waiter must not signal the holder")

    @unittest.skipIf(LSOF is None, "lsof is the stated prerequisite for identifying a record-less holder and is not installed here")
    def test_a_record_less_lock_exits_2_within_the_bound_naming_the_holder_not_the_waiter(self):
        holder = self.holder("-")
        result, seconds = self.run_cli(45)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn(str(self.lock_path), result.stderr)
        self.assertGreaterEqual(seconds, 9)
        self.assertLess(seconds, 25)
        listed = result.stderr.split("waiters): ", 1)[1].strip().split(", ")
        self.assertEqual(listed, [str(holder.pid)], "only the holder is named, never the waiter's own pid")
        self.assertIsNone(holder.poll(), "the waiter must not signal the holder")


class WaitingTests(LockBase):
    def test_a_live_holder_is_awaited_and_the_lock_acquired_after_release(self):
        self.holder(json.dumps({"engine_pid": "$self", "check_id": "unit", "started_at": 1}), hold=3.0)
        time.sleep(0.2)
        result, seconds = self.run_cli(40)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("waiting for", result.stderr)
        self.assertGreaterEqual(seconds, 2)

    def test_a_stale_record_after_a_normal_release_causes_no_false_orphan_exit(self):
        with te._lock(self.lock_path, "unit"):
            pass
        stale = json.loads(self.lock_path.read_text())
        self.assertEqual(stale["engine_pid"], os.getpid())
        self.lock_path.write_text(json.dumps(dict(stale, engine_pid=self.dead_pid())))
        with te._lock(self.lock_path, "unit") as fd:  # nobody holds it: acquired at once
            self.assertEqual(json.loads(os.pread(fd, 4096, 0))["engine_pid"], os.getpid())
        self.holder(json.dumps({"engine_pid": "$self", "check_id": "unit", "started_at": 2}), delay=0.4, hold=2.0)
        started = time.monotonic()
        # the holder is busy and the stale dead record is visible for the first poll only
        with te._lock(self.lock_path, "unit"):
            self.assertGreaterEqual(time.monotonic() - started, 1.5)


class DiscoveryTests(LockBase):
    def orphan(self):
        return self.holder(json.dumps({"engine_pid": self.dead_pid(), "check_id": "unit", "started_at": 1}))

    def test_without_lsof_the_exit_says_the_holder_cannot_be_identified(self):
        self.orphan()
        real = subprocess.run
        def fake(argv, *args, **kwargs):
            if argv[0] == "lsof":
                raise FileNotFoundError("lsof")
            return real(argv, *args, **kwargs)
        with patch.object(te.subprocess, "run", side_effect=fake), patch.object(te, "LOCK_POLL_SECONDS", 0.1):
            with self.assertRaisesRegex(te.EvidenceError, "cannot be identified without lsof"):
                with te._lock(self.lock_path):
                    pass

    def test_an_lsof_timeout_says_the_holder_cannot_be_identified(self):
        self.orphan()
        real = subprocess.run
        def fake(argv, *args, **kwargs):
            if argv[0] == "lsof":
                raise subprocess.TimeoutExpired(argv, 5)
            return real(argv, *args, **kwargs)
        with patch.object(te.subprocess, "run", side_effect=fake), patch.object(te, "LOCK_POLL_SECONDS", 0.1):
            with self.assertRaisesRegex(te.EvidenceError, "cannot be identified without lsof"):
                with te._lock(self.lock_path):
                    pass

    def test_an_empty_lsof_result_with_the_lock_still_held_says_no_process_was_found(self):
        self.orphan()
        with patch.object(te, "_lock_holders", return_value=[]), patch.object(te, "LOCK_POLL_SECONDS", 0.1):
            with self.assertRaisesRegex(te.EvidenceError, "no process was found with the lock file open"):
                with te._lock(self.lock_path):
                    pass

    def test_an_empty_lsof_result_with_the_lock_free_at_the_retry_proceeds(self):
        holder = self.orphan()
        def released(_path):
            self.stop(holder)
            return []
        with patch.object(te, "_lock_holders", side_effect=released), patch.object(te, "LOCK_POLL_SECONDS", 0.1):
            with te._lock(self.lock_path) as fd:
                self.assertEqual(json.loads(os.pread(fd, 4096, 0))["engine_pid"], os.getpid())

    def test_an_unparseable_record_is_treated_as_no_record(self):
        for text in ("not json", json.dumps({"engine_pid": 0}), json.dumps({"engine_pid": 5, "child_pid": -1}), json.dumps([1])):
            with self.subTest(text):
                self.lock_path.write_text(text)
                fd = os.open(self.lock_path, os.O_RDWR)
                self.addCleanup(os.close, fd)
                self.assertIsNone(te._read_holder(fd))


class GraceInversionTests(LockBase):
    """The engine escalates to SIGKILL on its child's group after INTERRUPT_GRACE_SECONDS."""

    def test_the_child_group_is_gone_before_a_scheduler_kills_the_engine_at_8_seconds(self):
        marker = self.root / "child.json"
        body = ("import json, os, signal, time\n"
                "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
                f"open({str(marker)!r}, 'w').write(json.dumps({{'pgid': os.getpgrp()}}))\n"
                "time.sleep(120)\n")
        decl = dict(self.decl, command=["python", "-c", body])
        self.check.write_text(json.dumps(decl))
        engine = subprocess.Popen([sys.executable, str(SCRIPT), "run", "--repo-root", str(self.root), "--check", str(self.check)],
                                  env=self.env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        pgid = []
        def cleanup():
            if engine.poll() is None:
                engine.kill()
            engine.wait()
            for group in pgid:
                try:
                    os.killpg(group, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        self.addCleanup(cleanup)
        for _ in range(100):
            if marker.exists() and marker.read_text().endswith("}"):
                break
            time.sleep(0.1)
        else:
            self.fail("the child never started")
        pgid.append(json.loads(marker.read_text())["pgid"])
        engine.send_signal(signal.SIGTERM)
        time.sleep(8)
        engine.kill()  # the scheduler's escalation
        engine.wait()
        with self.assertRaises(ProcessLookupError, msg="the child's group survived the engine's death and holds the lock"):
            os.killpg(pgid[0], 0)


if __name__ == "__main__":
    unittest.main()
