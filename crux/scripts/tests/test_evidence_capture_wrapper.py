"""The capture wrapper runs an entry exactly as a direct invocation would, after writing the identity."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
CAPTURE = SCRIPTS / "test_evidence_capture.py"


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dev = Path(self.temp.name).resolve() / "dev"
        self.stage = Path(self.temp.name).resolve() / "stage"
        self.outside = Path(self.temp.name).resolve() / "outside"
        for directory in (self.dev / "crux/scripts", self.stage / "crux/scripts", self.outside):
            directory.mkdir(parents=True)
        self.identity = self.outside / "identity.json"
        shutil.copyfile(CAPTURE, self.dev / "crux/scripts/test_evidence_capture.py")

    def env(self, **extra):
        env = {k: v for k, v in os.environ.items() if not k.startswith("PYTHON")}
        env.update(extra)
        return env

    def capture(self, *entry, cwd=None, wrapper=None, variables=None, **env):
        command = [sys.executable, str(wrapper or self.dev / "crux/scripts/test_evidence_capture.py"), str(self.identity)]
        if variables:
            command += ["--variables", ",".join(variables)]
        return subprocess.run([*command, "--", *entry], cwd=cwd or self.stage, capture_output=True, text=True, env=self.env(**env))

    def direct(self, *entry, cwd=None, **env):
        return subprocess.run([sys.executable, *entry], cwd=cwd or self.stage, capture_output=True, text=True, env=self.env(**env))

    def test_a_module_missing_from_the_stage_fails_as_under_direct_invocation_even_if_the_dev_root_has_it(self):
        (self.dev / "crux/scripts/only_in_dev.py").write_text("VALUE = 'dev'\n")
        entry = self.stage / "crux/scripts/entry.py"
        entry.write_text("import only_in_dev\nprint(only_in_dev.VALUE)\n")
        direct = self.direct("crux/scripts/entry.py")
        wrapped = self.capture("crux/scripts/entry.py")
        self.assertNotEqual(direct.returncode, 0)
        self.assertIn("ModuleNotFoundError: No module named 'only_in_dev'", direct.stderr)
        self.assertEqual(wrapped.returncode, direct.returncode)
        self.assertIn("ModuleNotFoundError: No module named 'only_in_dev'", wrapped.stderr)
        self.assertEqual(wrapped.stdout, "")
        # Negative control: a wrapper that keeps its own directory on sys.path lets the stage import
        # the dev root's module, so this fixture does catch the fault the real wrapper avoids.
        source = CAPTURE.read_text()
        removal = "if sys.path and os.path.realpath(sys.path[0] or \".\") == _HERE:\n    del sys.path[0]"
        self.assertIn(removal, source)
        naive = self.dev / "crux/scripts/naive_capture.py"
        naive.write_text(source.replace(removal, "pass"))
        leaked = self.capture("crux/scripts/entry.py", wrapper=naive)
        self.assertEqual((leaked.returncode, leaked.stdout), (0, "dev\n"), leaked.stderr)
        # Positive control: the module resolves when the entry lives beside it, as for a direct run.
        (self.dev / "crux/scripts/entry.py").write_text(entry.read_text())
        self.assertEqual(self.capture(str(self.dev / "crux/scripts/entry.py"), cwd=self.dev).stdout, "dev\n")

    def test_only_the_inserted_script_directory_entry_is_removed_not_a_pythonpath_entry_for_it(self):
        scripts = self.dev / "crux/scripts"
        entry = self.stage / "entry.py"
        entry.write_text("import os, sys, json\nprint(json.dumps([os.path.realpath(p or '.') for p in sys.path]))\n")
        here = os.path.realpath(scripts)
        # PYTHONPATH is a behavior variable the wrapper strips from the child, so it is read at start-up here:
        # the wrapper itself sees sys.path = [script dir (inserted), PYTHONPATH entry (same dir), ...].
        probe = scripts / "probe_capture.py"
        probe.write_text(CAPTURE.read_text().replace("import hashlib  # noqa: E402",
                         "print('PATH ' + json.dumps([os.path.realpath(p or '.') for p in sys.path]), file=sys.stderr)\nimport hashlib  # noqa: E402", 1)
                         .replace("import os\nimport sys\n", "import os\nimport sys\nimport json\n", 1))
        result = self.capture(str(entry), wrapper=probe, PYTHONPATH=str(scripts))
        line = next(l for l in result.stderr.splitlines() if l.startswith("PATH "))
        seen = json.loads(line[5:])
        self.assertEqual(seen.count(here), 1, seen)
        # Positive control: without PYTHONPATH the inserted entry is the only one and is removed.
        plain = self.capture(str(entry), wrapper=probe)
        plain_seen = json.loads(next(l for l in plain.stderr.splitlines() if l.startswith("PATH "))[5:])
        self.assertNotIn(here, plain_seen)

    def test_a_dash_m_unittest_entry_discovers_the_same_tests_as_a_direct_run(self):
        tests = self.stage / "suite"
        tests.mkdir()
        for name in ("one", "two"):
            (tests / f"test_{name}.py").write_text(f"import unittest\nclass T{name}(unittest.TestCase):\n    def test_a(self): pass\n    def test_b(self): pass\n")
        direct = self.direct("-m", "unittest", "discover", "-s", "suite", "-v")
        wrapped = self.capture("-m", "unittest", "discover", "-s", "suite", "-v")
        self.assertEqual(direct.returncode, 0, direct.stderr)
        self.assertEqual(wrapped.returncode, 0, wrapped.stderr)
        def tests_run(result):
            return sorted(line.split(" (")[0] for line in result.stderr.splitlines() if " ... ok" in line), next(l for l in result.stderr.splitlines() if l.startswith("Ran "))
        self.assertEqual(tests_run(wrapped)[0], tests_run(direct)[0])
        self.assertTrue(tests_run(wrapped)[1].startswith("Ran 4 tests"))

    def test_the_callers_pythonpath_does_not_reach_the_child_only_a_registered_value_does(self):
        probe = self.stage / "probe.py"
        probe.write_text("import os, sys\nprint(os.environ.get('PYTHONPATH'), '/caller' in sys.path)\n")
        # The engine removes unregistered behavior variables from the child's environment; the
        # wrapper alone only reports what it finds, so the engine's removal is what is exercised here.
        import test_evidence as te
        env = te.child_environment(self.stage, {"environment": []}, {"variables": {}}, {"PYTHONPATH": "/caller", "PATH": os.environ["PATH"]})
        self.assertNotIn("PYTHONPATH", env)
        result = subprocess.run([sys.executable, str(CAPTURE), str(self.identity), "--", "probe.py"], cwd=self.stage, capture_output=True, text=True, env=env)
        self.assertEqual(result.stdout, "None False\n")
        registered = te.child_environment(self.stage, {"environment": []}, {"variables": {"PYTHONPATH": "${REPOSITORY}/lib"}}, {"PYTHONPATH": "/caller"})
        self.assertEqual(registered["PYTHONPATH"], f"{self.stage}/lib")

    def test_the_identity_is_written_before_the_entry_runs_and_holds_no_value(self):
        entry = self.stage / "peek.py"
        entry.write_text(f"import json\nprint(json.load(open({str(self.identity)!r}))['implementation'])\n")
        result = self.capture("peek.py", variables=["CUSTOM_NAME"], CUSTOM_NAME="very-private-value", PYTHONHASHSEED="3")
        self.assertEqual(result.stdout, "cpython\n", result.stderr)
        text = self.identity.read_text()
        self.assertNotIn("very-private-value", text)
        record = json.loads(text)
        self.assertEqual(record["variables"]["PYTHONHASHSEED"] is not None, True)
        self.assertEqual(len(record["variables"]["CUSTOM_NAME"]), 64)
        self.assertIsNone(record["variables"]["PYTHONPATH"])
        for field in ("implementation", "version", "version_info", "marker_environment", "sys_prefix", "sys_flags", "warnoptions",
                      "xoptions", "filesystem_encoding", "preferred_encoding", "distributions"):
            self.assertIn(field, record)
        for field in ("python_version", "python_full_version", "sys_platform", "platform_machine", "implementation_name", "os_name"):
            self.assertIn(field, record["marker_environment"])

    def test_a_repository_root_in_a_variable_is_replaced_by_a_token_before_the_digest(self):
        entry = self.stage / "noop.py"
        entry.write_text("pass\n")
        import hashlib
        self.capture("noop.py", variables=["CUSTOM_PATH"], CUSTOM_PATH=str(self.stage) + "/crux/scripts")
        recorded = json.loads(self.identity.read_text())["variables"]["CUSTOM_PATH"]
        self.assertEqual(recorded, hashlib.sha256(b"${REPOSITORY}/crux/scripts").hexdigest())

    def test_argv_name_and_exit_status_match_a_direct_invocation(self):
        entry = self.stage / "report.py"
        entry.write_text("import sys\nprint(__name__, sys.argv, sys.path[0] == __import__('os').path.dirname(__import__('os').path.realpath(__file__)))\nraise SystemExit(5)\n")
        direct = self.direct("report.py", "a", "b")
        wrapped = self.capture("report.py", "a", "b")
        self.assertEqual((wrapped.returncode, wrapped.stdout), (direct.returncode, direct.stdout))
        self.assertEqual(wrapped.returncode, 5)
        code = self.capture("-c", "import sys; print(__name__, sys.argv)", "x")
        self.assertEqual(code.stdout, "__main__ ['-c', 'x']\n")

    def test_the_wrapper_imports_no_repository_module(self):
        (self.dev / "crux/scripts/test_evidence.py").write_text("raise RuntimeError('the wrapper imported a repository module')\n")
        (self.dev / "crux/scripts/secret_scan.py").write_text("raise RuntimeError('the wrapper imported a repository module')\n")
        entry = self.stage / "modules.py"
        entry.write_text("import sys\nprint(sorted(m for m in sys.modules if m in ('test_evidence', 'secret_scan', 'suite_evidence')))\n")
        result = self.capture("modules.py")
        self.assertEqual(result.stdout, "[]\n", result.stderr)

    def test_the_wrapper_can_run_the_multiprocess_driver(self):
        driver = SCRIPTS / "tests" / "parallel_suite.py"
        tests = self.stage / "toy"
        tests.mkdir()
        (tests / "test_toy.py").write_text("import unittest\nclass T(unittest.TestCase):\n    def test_a(self): pass\n    def test_b(self): pass\n")
        result = self.capture(str(driver), "toy", "--workers", "2")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Ran 2 tests", result.stderr)

    def test_usage_errors_exit_2(self):
        self.assertEqual(subprocess.run([sys.executable, str(CAPTURE)], capture_output=True).returncode, 2)
        self.assertEqual(subprocess.run([sys.executable, str(CAPTURE), str(self.identity), "--"], capture_output=True).returncode, 2)


if __name__ == "__main__":
    unittest.main()
