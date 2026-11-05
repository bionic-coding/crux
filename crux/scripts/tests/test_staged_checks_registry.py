"""The staged `flagged` and `health` checks replace the staged full suite in the registry.

Each supported minor registers both checks. A receipt of the earlier staged full suite stays
readable. The driver runs a registered check through the evidence engine with `--staged-check`.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _evidence_fixtures import write_lock_project
import flagged_tests
import suite_evidence
import test_evidence as te

DRIVER = Path(__file__).resolve().parent / "parallel_suite.py"
OLD_STAGED = "staged:py3.13:unittest:crux/scripts/tests:test*.py"


def checks(minor):
    return f"staged:py{minor}:flagged", f"staged:py{minor}:health"


def write_tier_manifest(root):
    """The tier manifest that ships beside the flagged list: `test_a.A` is a release test."""
    tests = Path(root) / flagged_tests.DEFAULT_RELATIVE
    tests = tests.parent
    tests.mkdir(parents=True, exist_ok=True)
    (tests / "test_a.py").write_text("import unittest\n\n\nclass A(unittest.TestCase):\n    def test_one(self):\n        pass\n")
    (tests / "test-tiers.json").write_text(json.dumps({
        "format": "crux.test-tiers", "version": 1, "kind": "python-unittest", "pattern": "test*.py",
        "areas": {"a": "an area"}, "files": {"test_a.py": {"tier": "release", "area": "a"}}}))


class RegistrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        write_lock_project(self.root)
        (self.root / ".python-version").write_text("3.13\n")
        self.declared = suite_evidence.registered_declarations(self.root, dev_root=self.root)

    def test_each_supported_minor_registers_flagged_and_health_and_no_staged_full_suite(self):
        staged = sorted(check for check in self.declared if check.startswith("staged:"))
        self.assertEqual(staged, sorted([*checks("3.13"), *checks("3.14")]))
        self.assertNotIn(OLD_STAGED, self.declared)
        # Six checks before test tiers; the two release-tier declarations and the tier check add three.
        self.assertEqual(len(self.declared), 9)

    def test_the_minors_come_from_the_project_matrix(self):
        (self.root / "pyproject.toml").write_text((self.root / "pyproject.toml").read_text()
                                                  + '\n[tool.crux]\npython-versions = ["3.13", "3.15"]\n')
        declared = suite_evidence.registered_declarations(self.root, dev_root=self.root)
        self.assertIn("staged:py3.15:flagged", declared)
        self.assertIn("staged:py3.15:health", declared)
        self.assertNotIn("staged:py3.14:health", declared)

    def test_the_commands_are_canonical_and_name_the_check(self):
        self.assertEqual(self.declared["staged:py3.13:flagged"]["command"],
                         ["python", "crux/scripts/tests/parallel_suite.py", "crux/scripts/tests", "--flagged"])
        self.assertEqual(self.declared["staged:py3.14:health"]["command"], ["python", "crux/scripts/staged_health.py"])
        for declaration in self.declared.values():
            self.assertEqual(declaration["command"][0], "python")

    def test_the_requirement_is_the_minors_locked_environment_for_both_checks(self):
        for minor in ("3.13", "3.14"):
            for check in checks(minor):
                requirement = te.normalize(self.declared[check])["requirement"]
                self.assertEqual(requirement["interpreter"]["minors"], [minor], check)
                self.assertEqual(requirement["packages"]["lock"]["source"], "dev-root", check)
                self.assertTrue(requirement["isolated"], check)
                self.assertEqual(requirement["variables"]["PYTHONPATH"], "${REPOSITORY}/crux/scripts", check)
                self.assertEqual(requirement["flags"], {"dont_write_bytecode": 1}, check)

    def test_the_staged_checks_carry_the_staged_exclusions_and_projections(self):
        for minor in ("3.13", "3.14"):
            for check in checks(minor):
                declaration = self.declared[check]
                self.assertEqual(declaration["exclude_inputs"], ["CHANGELOG.md"], check)
                self.assertEqual(declaration["input_projections"],
                                 {path: list(kinds) for path, kinds in suite_evidence.RELEASE_PROJECTIONS["staged"].items()}, check)
                self.assertFalse(declaration["git_tracked"], check)
                te.normalize(declaration)

    def test_the_two_checks_of_a_minor_do_not_share_a_declaration(self):
        flagged, health = (te.normalize(self.declared[c]) for c in checks("3.13"))
        self.assertNotEqual(te.digest(flagged), te.digest(health))

    def test_the_registered_lookup_and_the_accessor_agree(self):
        for check in checks("3.14"):
            self.assertEqual(suite_evidence.registered_declaration(self.root, check, dev_root=self.root), self.declared[check])
        self.assertEqual(suite_evidence.staged_check_declaration(self.root, "health", "3.13", dev_root=self.root),
                         self.declared["staged:py3.13:health"])
        with self.assertRaises(te.EvidenceError):
            suite_evidence.staged_check_declaration(self.root, "health", "3.12", dev_root=self.root)

    def test_a_focused_staged_run_is_not_registered(self):
        _, registered = suite_evidence.declaration_for("staged", "crux/scripts/tests", "test*.py", None, self.root, minor="3.13", dev_root=self.root)
        self.assertFalse(registered)


class EarlierReceiptsTests(unittest.TestCase):
    def test_a_receipt_of_the_staged_full_suite_stays_readable(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            (root / "src").mkdir()
            (root / "src/a.txt").write_text("x")
            declaration = {"check_id": OLD_STAGED, "inputs": ["src"], "environment": [],
                           "command": [sys.executable, "-c", "pass"]}
            with patch.dict(os.environ, {"CRUX_TEST_EVIDENCE_STORE": str(root.parent / (root.name + "-store"))}):
                self.assertIsNone(suite_evidence.registered_declaration(root, OLD_STAGED))
                result = te.execute(root, declaration)
                record = te.validate_evidence(root, result["evidence"]["id"], OLD_STAGED)
            self.assertEqual(record["declaration"]["check_id"], OLD_STAGED)
            self.assertEqual(record["status"], "passed")


class FlaggedListProblemTests(unittest.TestCase):
    def test_run_shared_refuses_a_list_naming_a_minor_the_project_does_not_support(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            write_lock_project(root)
            target = root / flagged_tests.DEFAULT_RELATIVE
            target.parent.mkdir(parents=True)
            write_tier_manifest(root)
            entry = {"test": "test_a.A", "class": "harness", "reason": "r", "origin": "TE-0123456789abcdef", "minors": ["3.9"]}
            target.write_text(json.dumps({"entries": [entry]}))
            problems = suite_evidence.flagged_list_problems(root, root)
            self.assertEqual(len(problems), 1)
            self.assertIn("3.9", problems[0])
            entry["minors"] = ["3.13"]
            target.write_text(json.dumps({"entries": [entry]}))
            self.assertEqual(suite_evidence.flagged_list_problems(root, root), [])


class DriverPlanTests(unittest.TestCase):
    def run_plan(self, root, check, minor="3.13"):
        env = {k: v for k, v in os.environ.items() if k not in ("CRUX_TEST_EVIDENCE_STORE",)}
        env["CRUX_TEST_EVIDENCE_STORE"] = str(root.parent / (root.name + "-store"))
        return subprocess.run(
            [sys.executable, str(DRIVER), "crux/scripts/tests", "--shared-evidence", "--evidence-scope", "staged",
             "--source-root", str(root), "--python-minor", minor, "--staged-check", check, "--plan-test-evidence"],
            capture_output=True, text=True, cwd=root, env=env, timeout=120)

    def test_the_plan_names_the_registered_check_and_reports_missing_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            write_lock_project(root)
            (root / ".python-version").write_text("3.13\n")
            listing = root / flagged_tests.DEFAULT_RELATIVE
            listing.parent.mkdir(parents=True)
            write_tier_manifest(root)
            listing.write_text(json.dumps({"entries": [{"test": "test_a.A", "class": "harness", "reason": "r",
                                                       "origin": "TE-0123456789abcdef"}]}))
            for check in ("flagged", "health"):
                done = self.run_plan(root, check)
                self.assertEqual(done.returncode, 3, done.stderr[-400:])
                plan = json.loads(done.stdout.split("Test evidence plan: ", 1)[1].splitlines()[0])
                self.assertEqual(plan["check_id"], f"staged:py3.13:{check}")
                self.assertNotEqual(plan["state"], "passed")

    def test_staged_check_needs_the_staged_shared_evidence_mode(self):
        done = subprocess.run([sys.executable, str(DRIVER), "crux/scripts/tests", "--staged-check", "health"],
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 2)
        self.assertIn("--staged-check needs", done.stderr)


if __name__ == "__main__":
    unittest.main()
