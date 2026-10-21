"""A receipt is judged against its own recorded environment and the registered requirement.

Nothing here asks what environment the validating process is in. Fixture interpreters are unseeded
venvs holding fabricated distributions, so the package sets are exact and need no network.
"""
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
from _evidence_fixtures import (CONDITIONAL, MINOR, conditional_dists, lock_requirement, make_venv, raw_receipt,
                                reseal_in_place, variant, write_lock_project)
import test_evidence as te
from test_evidence import EvidenceError, execute, lookup, validate_evidence

SCRIPTS = Path(__file__).resolve().parents[1]


class EnvironmentBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls._tmp.cleanup)
        parent = Path(cls._tmp.name)
        cls.core_python = make_venv(parent, "core", conditional_dists(False))
        cls.tools_python = make_venv(parent, "tools", conditional_dists(True))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.store = self.root / "evidence"
        patcher = patch.dict(os.environ, {"CRUX_TEST_EVIDENCE_STORE": str(self.store)})
        patcher.start()
        self.addCleanup(patcher.stop)
        write_lock_project(self.root)
        (self.root / "input.txt").write_text("one")

    def declaration(self, check_id="core", project=False, **requirement):
        return {"check_id": check_id, "command": ["python", "-c", "print('ok')"],
                "inputs": ["input.txt", "pyproject.toml", "uv.lock"], "environment": [],
                "requirement": lock_requirement(project, **requirement)}

    def run_core(self, **requirement):
        return execute(self.root, self.declaration(**requirement), interpreter=self.core_python)["evidence"]

    def unsatisfying(self, python, declaration=None):
        """Execute where the requirement fails; return the receipt id of the recorded pass."""
        before = {p.name for p in self.store.glob("TE-*.json")} if self.store.exists() else set()
        with self.assertRaises(EvidenceError) as caught:
            execute(self.root, declaration or self.declaration(), interpreter=python)
        created = {p.name for p in self.store.glob("TE-*.json")} - before
        self.assertEqual(len(created), 1)
        return Path(created.pop()).stem, str(caught.exception)

    def assertRefuses(self, evidence_id, pattern):
        with self.assertRaisesRegex(EvidenceError, pattern):
            validate_evidence(self.root, evidence_id)


class CrossEnvironmentTests(EnvironmentBase):
    def test_receipts_from_two_interpreters_validate_in_a_third_process(self):
        # Throwaway environments, deleted as preflight's are before any later validation runs.
        core_python = make_venv(self.root, "throwaway-core", conditional_dists(False))
        tools_python = make_venv(self.root, "throwaway-tools", conditional_dists(True))
        core = execute(self.root, self.declaration(), interpreter=core_python)["evidence"]
        tools = execute(self.root, self.declaration("tools", project=True), interpreter=tools_python)["evidence"]
        shutil.rmtree(core_python.parent.parent)
        shutil.rmtree(tools_python.parent.parent)
        self.assertNotEqual(core["environment"]["sys_prefix"], tools["environment"]["sys_prefix"])
        self.assertNotEqual(core["environment"]["distributions"], tools["environment"]["distributions"])
        (self.root / "bionic").mkdir()
        (self.root / "bionic/manifest.yml").write_text('schema_version: "5"\nconcerns_enabled: [adrs]\n')
        from cycle_workflow import create, mutate
        doc = create(self.root, "quick-fix", "Fix", "Outcome", ["input.txt"], ["works"], "builder", "tester")
        doc = mutate(self.root, doc["id"], "advance")
        doc = mutate(self.root, doc["id"], "checks", checks=["core", "tools"])
        mutate(self.root, doc["id"], "coverage", coverage={
            "affected": ["interpreters differ"], "checks": [{"check_id": c, "rationale": "executed in its own environment"} for c in ("core", "tools")],
            "not_selected": "none"})
        def cli(*args):
            run = subprocess.run([sys.executable, str(SCRIPTS / "cycle.py"), "--repo-root", str(self.root), *args],
                                 capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        cli("evidence", doc["id"], "--check-id", "core", "--evidence-id", core["id"], "--use", "executed")
        cli("evidence", doc["id"], "--check-id", "tools", "--evidence-id", tools["id"], "--use", "executed")
        cli("advance", doc["id"])  # check_tests validates both receipts in this third process

    def test_a_new_throwaway_environment_that_satisfies_the_requirement_reuses(self):
        first = self.run_core()
        other = make_venv(self.root, "second-core", conditional_dists(False))
        second = execute(self.root, self.declaration(), interpreter=other)
        self.assertEqual(second["action"], "reused")
        self.assertEqual(second["evidence"]["id"], first["id"])
        self.assertEqual(validate_evidence(self.root, first["id"])["id"], first["id"])


class RefusalTests(EnvironmentBase):
    def test_changed_relevant_input(self):
        record = self.run_core()
        (self.root / "input.txt").write_text("two")
        self.assertEqual(lookup(self.root, self.declaration())["state"], "inputs-changed")
        self.assertRefuses(record["id"], "relevant inputs changed")

    def test_committed_change_to_a_non_excluded_file(self):
        def git(*args):
            return subprocess.run(["git", "-c", "user.name=T", "-c", "user.email=t@example.invalid", *args], cwd=self.root, capture_output=True, check=True)
        git("init", "-q")
        git("add", "-A")
        git("commit", "-qm", "one")
        declaration = dict(self.declaration(), git_tracked=True, exclude_inputs=["bionic/cycles"])
        record = execute(self.root, declaration, interpreter=self.core_python)["evidence"]
        (self.root / "tracked.txt").write_text("a committed change outside the exclusions")
        git("add", "tracked.txt")
        git("commit", "-qm", "two")
        self.assertEqual(lookup(self.root, declaration)["state"], "inputs-changed")
        self.assertRefuses(record["id"], "relevant inputs changed")

    def test_changed_locked_package(self):
        record = self.run_core()
        (self.root / "uv.lock").write_text((self.root / "uv.lock").read_text().replace('version = "1.0"', 'version = "1.1"', 1))
        self.assertRefuses(record["id"], "relevant inputs changed")

    def test_an_environment_whose_package_differs_from_the_lock(self):
        python = make_venv(self.root, "stale", [("dep-a", "0.9"), CONDITIONAL])
        evidence_id, message = self.unsatisfying(python)
        self.assertIn("dep-a==0.9", message)
        self.assertRefuses(evidence_id, "package set differs from the lock")

    def test_an_extra_package_in_an_isolated_check(self):
        for extra in ("pip", "setuptools", "wheel"):
            with self.subTest(extra=extra):
                python = make_venv(self.root, f"with-{extra}", [*conditional_dists(False), (extra, "1.0")])
                evidence_id, message = self.unsatisfying(python, self.declaration(f"core-{extra}"))
                self.assertIn(f"{extra}==1.0", message)
                self.assertRefuses(evidence_id, f"unexpected [^;]*{extra}==1.0")

    def test_the_crux_distribution_in_an_isolated_check(self):
        python = make_venv(self.root, "with-crux", [*conditional_dists(False), ("crux", "4.0.2")])
        evidence_id, message = self.unsatisfying(python)
        self.assertIn("crux==4.0.2", message)
        self.assertRefuses(evidence_id, "package set differs")

    def test_the_project_distribution_is_required_where_the_lock_includes_it(self):
        evidence_id, _ = self.unsatisfying(self.core_python, self.declaration("tools", project=True))
        self.assertRefuses(evidence_id, "missing fixture-project==0.1.0")

    def test_python_minor_outside_the_requirement(self):
        evidence_id, message = self.unsatisfying(self.core_python, self.declaration(interpreter={"implementation": "cpython", "minors": ["3.99"]}))
        self.assertIn("outside the required minors 3.99", message)
        self.assertRefuses(evidence_id, "outside the required minors")

    def test_unregistered_behavior_variables_are_removed_from_the_child(self):
        declaration = self.declaration()
        # Only the behavior set is removed. Other PYTHON* names, such as the PYTHONDONTWRITEBYTECODE the staged
        # suite sets, pass through unrecorded by design, so the child reports the behavior set alone.
        behavior = repr(set(te.BEHAVIOR_VARIABLES))
        declaration["command"] = ["python", "-c", f"import os, sys; print(sorted(k for k in os.environ if k in {behavior}), sys.path[0] == '/caller')"]
        with patch.dict(os.environ, {"PYTHONHASHSEED": "7", "PYTHONPATH": "/caller", "PYTHONWARNINGS": "error"}):
            record = execute(self.root, declaration, interpreter=self.core_python)["evidence"]
        self.assertEqual((self.store / record["output"]).read_text().strip(), "[] False")
        self.assertTrue(all(value is None for name, value in record["environment"]["variables"].items() if name.startswith("PYTHON")))
        validate_evidence(self.root, record["id"])

    def test_a_set_behavior_variable_that_is_not_registered(self):
        record = self.run_core()
        for name in ("PYTHONHASHSEED", "PYTHONPATH", "PYTHONWARNINGS"):
            with self.subTest(name=name):
                forged = variant(self.store, record["id"], lambda r, n=name: r["environment"]["variables"].__setitem__(n, "0" * 64))
                self.assertRefuses(forged["id"], f"behavior variable {name} was set and is not registered")

    def test_a_registered_variable_must_hold_its_registered_value(self):
        declaration = self.declaration(variables={"PYTHONPATH": "${REPOSITORY}/lib"})
        declaration["command"] = ["python", "-c", "import os; print(os.environ['PYTHONPATH'])"]
        record = execute(self.root, declaration, interpreter=self.core_python)["evidence"]
        self.assertEqual((self.store / record["output"]).read_text().strip(), f"{self.root}/lib")
        self.assertEqual(lookup(self.root, declaration)["state"], "passed")
        forged = variant(self.store, record["id"], lambda r: r["environment"]["variables"].__setitem__("PYTHONPATH", "1" * 64))
        self.assertRefuses(forged["id"], "variable PYTHONPATH does not hold its registered value")

    def test_changed_flags_and_warnoptions(self):
        launcher = self.root / "launch.sh"
        launcher.write_text(f'#!/bin/sh\nexec "{self.core_python}" -O -W error "$@"\n')
        launcher.chmod(0o755)
        evidence_id, message = self.unsatisfying(launcher)
        self.assertIn("sys.flags.optimize is set", message)
        self.assertIn("sys.warnoptions is not empty", message)
        self.assertRefuses(evidence_id, "sys.flags.optimize")

    def test_registered_flags_are_held_to_their_value(self):
        declaration = self.declaration(flags={"optimize": 2})
        evidence_id, message = self.unsatisfying(self.core_python, declaration)
        self.assertIn("sys.flags.optimize is 0, registered 2", message)

    def test_a_non_utf8_encoding(self):
        record = self.run_core()
        for field in ("filesystem_encoding", "preferred_encoding"):
            with self.subTest(field=field):
                forged = variant(self.store, record["id"], lambda r, f=field: r["environment"].__setitem__(f, "ISO8859-1"))
                self.assertRefuses(forged["id"], f"{field} is 'ISO8859-1', not UTF-8")

    def test_a_changed_tool_version(self):
        declaration = self.declaration(tools=["git"])
        record = execute(self.root, declaration, interpreter=self.core_python)["evidence"]
        self.assertIn("git version", record["tools"]["git"]["version"])
        self.assertEqual(lookup(self.root, declaration)["state"], "passed")
        changed = {"git": {"path": "/usr/bin/git", "version": "git version 0.0.0"}}
        with patch("test_evidence.observe_tools", return_value=changed):
            self.assertRefuses(record["id"], "tool git version changed")
            self.assertEqual(lookup(self.root, declaration)["state"], "missing")

    def test_a_marker_conditional_package_is_judged_per_recorded_minor(self):
        requirement = {"interpreter": {"implementation": "cpython", "minors": ["3.13", "3.14"]}}
        record = execute(self.root, self.declaration(**requirement), interpreter=self.core_python)["evidence"]
        def as_minor(minor, conditional):
            def mutate(r):
                env = r["environment"]
                major, number = minor.split(".")
                env["version_info"] = [int(major), int(number), 0]
                env["marker_environment"].update(python_version=minor, python_full_version=minor + ".0")
                env["distributions"] = [["dep-a", "1.0"], list(conditional)]
                r["declaration"]["requirement"].update(interpreter=r["declaration"]["requirement"]["interpreter"])
            return mutate
        cases = [("3.13", ("dep-b", "2.0"), True), ("3.13", ("dep-c", "3.0"), False),
                 ("3.14", ("dep-c", "3.0"), True), ("3.14", ("dep-b", "2.0"), False)]
        for minor, conditional, satisfies in cases:
            with self.subTest(minor=minor, conditional=conditional):
                forged = variant(self.store, record["id"], as_minor(minor, conditional))
                if satisfies:
                    self.assertEqual(validate_evidence(self.root, forged["id"])["id"], forged["id"])
                else:
                    self.assertRefuses(forged["id"], "package set differs from the lock")

    def test_marker_evaluation_is_offline_and_exact(self):
        env = {"python_version": "3.13", "python_full_version": "3.13.5", "sys_platform": "darwin", "platform_system": "Darwin",
               "implementation_name": "cpython", "os_name": "posix"}
        for marker, expected in [("python_full_version < '3.14'", True), ("python_full_version >= '3.14'", False),
                                 ("sys_platform == 'win32' or python_version >= '3.13'", True),
                                 ("(sys_platform == 'win32' or sys_platform == 'linux') and python_version >= '3.13'", False),
                                 ("platform_system not in 'Linux Windows'", True), ("python_version ~= '3.13'", True),
                                 ("python_full_version < '3.14.0rc1'", True), ("python_version == '3.13.*'", True)]:
            self.assertEqual(te.evaluate_marker(marker, env), expected, marker)
        with self.assertRaises(EvidenceError):
            te.evaluate_marker("unknown_variable == '1'", env)

    def test_a_missing_identity_file_is_not_a_pass(self):
        silent = self.root / "silent_capture.py"
        silent.write_text("import sys\nexec(sys.argv[sys.argv.index('--') + 2])\n")
        with patch.object(te, "CAPTURE", silent):
            record = execute(self.root, self.declaration(), interpreter=self.core_python)["evidence"]
        self.assertEqual(record["status"], "interrupted")
        self.assertIsNone(record["environment"])
        self.assertEqual(lookup(self.root, self.declaration())["state"], "missing")
        good = self.run_core()
        forged = variant(self.store, good["id"], lambda r: r.__setitem__("environment", None))
        self.assertRefuses(forged["id"], "identity file missing")

    def test_missing_or_changed_output_log(self):
        record = self.run_core()
        log = self.store / record["output"]
        log.write_text("changed")
        self.assertRefuses(record["id"], "output log mismatch")
        log.unlink()
        self.assertRefuses(record["id"], "output log missing")
        self.assertEqual(lookup(self.root, self.declaration())["state"], "missing")

    def test_a_broken_seal_stops_lookup_and_names_the_file(self):
        record = self.run_core()
        path = self.store / (record["id"] + ".json")
        data = json.loads(path.read_text())
        data["seconds"] = 0.5
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(EvidenceError, record["id"] + r"\.json"):
            lookup(self.root, self.declaration())
        with self.assertRaisesRegex(EvidenceError, record["id"] + r"\.json"):
            validate_evidence(self.root, record["id"])

    def test_a_failed_status(self):
        declaration = self.declaration()
        declaration["command"] = ["python", "-c", "raise SystemExit(1)"]
        record = execute(self.root, declaration, interpreter=self.core_python)["evidence"]
        self.assertEqual(record["status"], "failed")
        self.assertRefuses(record["id"], "newer evidence|status failed|is not the current valid passing result")
        self.assertEqual(lookup(self.root, declaration)["state"], "failed")

    def test_a_declaration_that_differs_from_its_registration(self):
        record = self.run_core()
        registered = dict(self.declaration(), inputs=["input.txt", "pyproject.toml", "uv.lock", "extra.txt"])
        with patch("suite_evidence.registered_declaration", return_value=registered):
            self.assertRefuses(record["id"], "differs from the registered declaration")
        with patch("suite_evidence.registered_declaration", return_value=self.declaration()):
            self.assertEqual(validate_evidence(self.root, record["id"])["id"], record["id"])

    def test_a_named_version_1_receipt(self):
        record = self.run_core()
        def downgrade(r):
            r["schema_version"] = 1
            for key in ("environment", "tools", "lock_sha256", "source_revision", "signal"):
                r.pop(key, None)
            r["snapshot"] = {"fingerprint": r["fingerprint"], "inputs": r["snapshot"]["inputs"], "identity": {"environment_sha256": "0" * 64}}
        old = variant(self.store, record["id"], downgrade)
        with self.assertRaises(EvidenceError) as caught:
            validate_evidence(self.root, old["id"])
        message = str(caught.exception)
        self.assertIn("environment-not-comparable (schema_version 1)", message)
        for field in ("environment", "tools", "lock_sha256", "source_revision"):
            self.assertIn(field, message)


class IsolatedBuildTests(EnvironmentBase):
    """An isolated check gets exactly the locked packages, built from the lock export and no seeded pip."""

    def test_the_engine_builds_the_locked_environment_and_the_receipt_satisfies_it(self):
        write_lock_project(self.root, empty=True)
        declaration = {"check_id": "built", "command": ["python", "-c", "import sys; print(sys.prefix)"], "inputs": ["input.txt", "uv.lock"],
                       "requirement": lock_requirement()}
        result = execute(self.root, declaration)
        record = result["evidence"]
        self.assertEqual((result["action"], record["status"]), ("executed", "passed"))
        self.assertEqual(record["environment"]["distributions"], [], "no pip, setuptools, wheel or crux distribution")
        prefix = Path((self.store / record["output"]).read_text().strip())
        self.assertNotIn(self.root, prefix.parents)
        self.assertFalse(prefix.exists(), "the throwaway environment is deleted after the run")
        self.assertEqual(lookup(self.root, declaration)["state"], "passed")
        self.assertEqual(validate_evidence(self.root, record["id"])["id"], record["id"])

    def test_the_child_runs_with_the_built_environment_first_on_path(self):
        write_lock_project(self.root, empty=True)
        declaration = {"check_id": "built-path", "command": ["python", "-c", "import os, shutil, sys; real = os.path.realpath; print(real(os.environ['VIRTUAL_ENV']) == real(sys.prefix), real(os.path.dirname(shutil.which('python3'))) == real(sys.prefix + '/bin'))"],
                       "inputs": ["input.txt", "uv.lock"], "requirement": lock_requirement()}
        record = execute(self.root, declaration)["evidence"]
        self.assertEqual((self.store / record["output"]).read_text().strip(), "True True")

    def test_a_failed_environment_build_is_an_interruption_not_a_failure(self):
        write_lock_project(self.root, empty=True)
        declaration = {"check_id": "unbuildable", "command": ["python", "-c", "print('never runs')"], "inputs": ["input.txt", "uv.lock"],
                       "requirement": lock_requirement(interpreter={"implementation": "cpython", "minors": ["3.1"]})}
        record = execute(self.root, declaration)["evidence"]
        self.assertEqual(record["status"], "interrupted")
        self.assertIn("launch error", record["reason"])
        self.assertEqual(lookup(self.root, declaration)["state"], "missing")


if __name__ == "__main__":
    unittest.main()
