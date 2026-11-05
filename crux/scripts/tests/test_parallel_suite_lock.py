"""A registered checkout suite run holds the full-suite lock for the whole execution.

`tools/test-suite.py` holds `<git-common-dir>/crux/full-suite.lock` for a full run, and the cycle writer's
record commit defers while the lock is held. A direct `parallel_suite.py <start> --shared-evidence` run of a
registered checkout suite must hold the same lock, or a writer commit can move HEAD mid-suite. Every case
runs the driver in a subprocess over a temporary git repository; the cases that need a run that stays
alive replace `suite_evidence` with a stub that waits for a file.
"""
import fcntl
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
DRIVER = Path(__file__).resolve().parent / "parallel_suite.py"
REAL_MODULES = ("test_evidence.py", "suite_evidence.py", "test_evidence_capture.py", "secret_scan.py",
                "bionic_config.py", "_yaml_min.py", "untrusted.py", "flagged_tests.py")
LOCK_FD_ENV = "CRUX_FULL_SUITE_LOCK_FD"
REGISTERED = "crux/scripts/tests"

# Replaces suite_evidence in the stub cases: every start is a registered checkout suite, and the run waits
# for the file named by STUB_HOLD, so the test can look at the lock while the run is alive.
STUB_SUITE_EVIDENCE = '''\
import os, time
from pathlib import Path

def declaration_for(scope, start, pattern, top, root, *, minor=None, dev_root=None):
    return {"check_id": "checkout:stub", "command": ["python", "stub"]}, scope == "checkout" and start == "crux/scripts/tests"

def run_shared(args):
    ready, hold = os.environ.get("STUB_READY"), os.environ.get("STUB_HOLD")
    if ready:
        Path(ready).write_text(str(os.getpid()))
    deadline = time.time() + 60
    while hold and not os.path.exists(hold) and time.time() < deadline:
        time.sleep(0.05)
    print("stub run finished")
    return 0
'''
STUB_TEST_EVIDENCE = "class EvidenceError(Exception):\n    pass\n"


def clean_env(**extra):
    env = {k: v for k, v in os.environ.items() if not k.startswith(("GIT_", "STUB_")) and k != LOCK_FD_ENV
           and k not in ("CRUX_TEST_EVIDENCE_STORE", "CRUX_TEST_EVIDENCE_DURABLE_ONLY")}
    env.update(extra)
    return env


def git(repo, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t.invalid", "-c", "commit.gpgsign=false", *args],
                          cwd=repo, env=clean_env(), capture_output=True, text=True, check=True).stdout


def make_repo(path, stub):
    scripts = path / "crux/scripts"
    (scripts / "tests").mkdir(parents=True)
    shutil.copy(DRIVER, scripts / "tests/parallel_suite.py")
    if stub:
        (scripts / "suite_evidence.py").write_text(STUB_SUITE_EVIDENCE)
        (scripts / "test_evidence.py").write_text(STUB_TEST_EVIDENCE)
    else:
        for name in REAL_MODULES:
            if (SCRIPTS / name).exists():
                shutil.copy(SCRIPTS / name, scripts / name)
    (path / "other/tests").mkdir(parents=True)
    (path / "other/tests/test_tiny.py").write_text(
        "import unittest\nclass Tiny(unittest.TestCase):\n    def test_ok(self): self.assertTrue(True)\n")
    (path / "pyproject.toml").write_text('[project]\nname = "t"\nversion = "0.0.1"\nrequires-python = ">=3.13"\n'
                                         'dependencies = []\n[tool.crux]\npython-versions = ["3.13"]\n')
    (path / ".gitignore").write_text("__pycache__/\n.venv/\n")
    if not stub:
        # The registered core declaration binds the repository's uv.lock; an empty project locks offline.
        subprocess.run(["uv", "lock"], cwd=path, env=clean_env(), capture_output=True, check=True)
    git(path, "init", "-q")
    git(path, "add", "-A")
    git(path, "commit", "-q", "-m", "init")
    return path


class LockCase(unittest.TestCase):
    stub = False

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.scratch = Path(temp.name).resolve()
        self.repo = make_repo(self.scratch / "repo", self.stub)
        self.lock_path = self.repo / ".git/crux/full-suite.lock"
        self.procs = []
        self.addCleanup(self._reap)

    def _reap(self):
        for proc in self.procs:
            if proc.poll() is None:
                proc.kill()
            proc.communicate()

    def argv(self, *args):
        return [sys.executable, "crux/scripts/tests/parallel_suite.py", *args]

    def run_driver(self, *args, **env):
        return subprocess.run(self.argv(*args), cwd=self.repo, env=clean_env(**env), capture_output=True, text=True,
                              timeout=120)

    def start_driver(self, *args, **env):
        proc = subprocess.Popen(self.argv(*args), cwd=self.repo, env=clean_env(**env), text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.procs.append(proc)
        return proc

    def hold_lock(self, info=None):
        """Hold the lock as test-suite.py does: an exclusive flock and a JSON holder line."""
        self.lock_path.parent.mkdir(mode=0o700, exist_ok=True)
        fd = os.open(self.lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        self.addCleanup(lambda: os.close(fd))
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        holder = info or {"pid": 4242, "head": "abc", "started_at": "2026-10-30T00:00:00+00:00", "output_dir": None}
        os.pwrite(fd, (json.dumps(holder) + "\n").encode(), 0)
        return fd

    def wait_for(self, path):
        deadline = time.time() + 30
        while not Path(path).exists():
            self.assertLess(time.time(), deadline, f"{path} never appeared")
            time.sleep(0.05)

    def lock_is_held(self):
        """What the cycle writer asks: is the lock held by anyone? A shared non-blocking probe, as cycle_commit does."""
        try:
            fd = os.open(self.lock_path, os.O_RDONLY)
        except OSError:
            return False
        try:
            fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except OSError:
            return True
        finally:
            os.close(fd)
        return False


class RefusalTests(LockCase):
    def test_a_registered_checkout_run_is_refused_while_another_run_holds_the_lock(self):
        self.hold_lock()
        result = self.run_driver(REGISTERED, "--shared-evidence", "--workers", "1")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("lock held", result.stderr)
        self.assertIn("full-suite.lock", result.stderr)
        self.assertIn("pid=4242", result.stderr)
        self.assertNotIn("Test evidence executed", result.stdout, "the refused run executed the suite")

    def test_planning_and_reuse_only_never_take_or_need_the_lock(self):
        self.hold_lock()
        plan = self.run_driver(REGISTERED, "--shared-evidence", "--plan-test-evidence")
        self.assertEqual(plan.returncode, 3, plan.stdout + plan.stderr)
        self.assertIn("Test evidence plan:", plan.stdout)
        self.assertNotIn("lock held", plan.stderr)
        reuse = self.run_driver(REGISTERED, "--shared-evidence", "--reuse-test-evidence-only")
        self.assertEqual(reuse.returncode, 2, reuse.stdout + reuse.stderr)
        self.assertIn("REFUSE: test evidence is", reuse.stderr)
        self.assertNotIn("lock held", reuse.stderr)

    def test_a_focused_unregistered_run_does_not_need_the_lock(self):
        self.hold_lock()
        result = self.run_driver("other/tests", "--shared-evidence", "--workers", "1")
        # Only the lock decision is under test: the run gets past it to the evidence engine.
        self.assertIn("Test evidence plan:", result.stdout, result.stdout + result.stderr)
        self.assertNotIn("lock held", result.stderr)

    def test_a_child_of_the_full_suite_tool_inherits_the_lock_and_does_not_retake_it(self):
        fd = self.hold_lock()
        result = subprocess.run(self.argv(REGISTERED, "--shared-evidence", "--workers", "1"), cwd=self.repo,
                                env=clean_env(**{LOCK_FD_ENV: str(fd)}), pass_fds=(fd,), capture_output=True,
                                text=True, timeout=120)
        self.assertNotIn("lock held", result.stderr, result.stdout + result.stderr)
        self.assertIn("Test evidence executed:", result.stdout, result.stdout + result.stderr)

    def test_a_stray_lock_variable_does_not_bypass_the_lock(self):
        self.hold_lock()
        result = self.run_driver(REGISTERED, "--shared-evidence", "--workers", "1", **{LOCK_FD_ENV: "97"})
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("lock held", result.stderr)

    def test_an_inherited_descriptor_for_some_other_file_does_not_bypass_the_lock(self):
        self.hold_lock()
        other = os.open(self.scratch / "other-file", os.O_RDWR | os.O_CREAT, 0o600)
        self.addCleanup(os.close, other)
        result = subprocess.run(self.argv(REGISTERED, "--shared-evidence", "--workers", "1"), cwd=self.repo,
                                env=clean_env(**{LOCK_FD_ENV: str(other)}), pass_fds=(other,), capture_output=True,
                                text=True, timeout=120)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("lock held", result.stderr)


class HoldTests(LockCase):
    stub = True

    def test_the_lock_is_held_for_the_whole_execution_and_released_after(self):
        ready, hold = self.scratch / "ready", self.scratch / "hold"
        first = self.start_driver(REGISTERED, "--shared-evidence", STUB_READY=str(ready), STUB_HOLD=str(hold))
        self.wait_for(ready)
        self.assertTrue(self.lock_is_held(), "a running registered suite run holds no lock")
        info = json.loads(self.lock_path.read_text())
        self.assertEqual(info["pid"], first.pid)
        self.assertEqual(info["head"], git(self.repo, "rev-parse", "HEAD").strip())
        for key in ("started_at", "output_dir"):
            self.assertIn(key, info)
        second = self.run_driver(REGISTERED, "--shared-evidence")
        self.assertEqual(second.returncode, 2, second.stdout + second.stderr)
        self.assertIn("lock held", second.stderr)
        self.assertIn(f"pid={first.pid}", second.stderr)
        hold.write_text("go")
        out, err = first.communicate(timeout=60)
        self.assertEqual(first.returncode, 0, out + err)
        self.assertFalse(self.lock_is_held(), "the finished run kept the lock")
        third = self.run_driver(REGISTERED, "--shared-evidence")
        self.assertEqual(third.returncode, 0, third.stdout + third.stderr)

    def test_the_cycle_writer_defers_its_record_commit_while_a_direct_run_executes(self):
        sys.path.insert(0, str(SCRIPTS))
        self.addCleanup(sys.path.remove, str(SCRIPTS))
        import cycle_commit
        cfg = types.SimpleNamespace(repo_root=self.repo)
        ready, hold = self.scratch / "ready", self.scratch / "hold"
        run = self.start_driver(REGISTERED, "--shared-evidence", STUB_READY=str(ready), STUB_HOLD=str(hold))
        self.wait_for(ready)
        self.assertTrue(cycle_commit.suite_running(cfg), "the writer cannot see the direct run")
        self.assertEqual(cycle_commit.deferral(cfg)[0], "full-suite-running")
        hold.write_text("go")
        run.communicate(timeout=60)
        self.assertFalse(cycle_commit.suite_running(cfg))

    def test_a_killed_run_releases_the_lock(self):
        ready = self.scratch / "ready"
        run = self.start_driver(REGISTERED, "--shared-evidence", STUB_READY=str(ready), STUB_HOLD=str(self.scratch / "never"))
        self.wait_for(ready)
        run.kill()
        run.communicate()
        self.assertFalse(self.lock_is_held())


if __name__ == "__main__":
    unittest.main()
