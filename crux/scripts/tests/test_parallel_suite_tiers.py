"""The driver's ``--tier`` option runs only the tests the root's ``test-tiers.json`` labels with that tier.

Every case runs the driver in a subprocess over a copy of the fixture root ``fixtures/test_tiers``
(its manifest renamed from ``test-tiers.example.json``) or a synthetic tree in a temporary directory.
The run's ``--records`` file names the exact ids that ran, so the cases assert the selection, not
only a count.
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
DRIVER = HERE / "parallel_suite.py"
FIXTURE = HERE / "fixtures" / "test_tiers"


class TierRunTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.tree = self.base / "tree"
        shutil.copytree(FIXTURE, self.tree)
        (self.tree / "test-tiers.example.json").rename(self.tree / "test-tiers.json")

    def drive(self, *args):
        records = self.base / "records.jsonl"
        records.unlink(missing_ok=True)
        done = subprocess.run([sys.executable, str(DRIVER), str(self.tree), "--workers", "2",
                               "--records", str(records), *args],
                              capture_output=True, text=True, cwd=self.base, timeout=300)
        ran = []
        if records.exists():
            ran = sorted(json.loads(line)["id"] for line in records.read_text().splitlines() if line.strip())
        return done.returncode, ran, done.stderr

    def manifest(self):
        return json.loads((self.tree / "test-tiers.json").read_text())

    def test_without_tier_every_test_runs(self):
        code, ran, err = self.drive()
        self.assertEqual(code, 0, err[-500:])
        self.assertEqual(len(ran), 7)  # positive control: --tier below really narrows the run

    def test_tier_release_runs_exactly_the_release_ids(self):
        code, ran, err = self.drive("--tier", "release")
        self.assertEqual(code, 0, err[-500:])
        self.assertEqual(ran, ["test_basic.Critical.test_c", "test_basic.Critical.test_d", "test_gate.Gate.test_x"])

    def test_the_method_override_wins_over_the_class_and_the_file_entry(self):
        code, ran, err = self.drive("--tier", "dev")
        self.assertEqual(code, 0, err[-500:])
        self.assertEqual(ran, ["test_basic.Plain.test_a", "test_gate.Gate.test_y"])
        code, ran, err = self.drive("--tier", "ephemeral")
        self.assertEqual(ran, ["test_basic.Plain.test_b", "test_old.Old.test_old"])

    def test_tier_is_repeatable(self):
        code, ran, err = self.drive("--tier", "dev", "--tier", "ephemeral")
        self.assertEqual(code, 0, err[-500:])
        self.assertEqual(len(ran), 4)
        self.assertFalse(any(i.startswith("test_basic.Critical") or i == "test_gate.Gate.test_x" for i in ran))

    def test_tier_intersects_with_select(self):
        code, ran, err = self.drive("--tier", "release", "--select", "test_gate")
        self.assertEqual((code, ran), (0, ["test_gate.Gate.test_x"]), err[-500:])

    def test_tier_with_a_select_that_matches_nothing_fails_closed(self):
        code, ran, err = self.drive("--tier", "release", "--select", "test_nowhere")
        self.assertEqual((code, ran), (2, []))
        self.assertIn("selection id not found: test_nowhere", err)

    def test_an_empty_tier_selection_fails_closed(self):
        code, ran, err = self.drive("--tier", "release", "--select", "test_old")
        self.assertEqual((code, ran), (2, []))
        self.assertIn("FAILED CLOSED", err)
        self.assertIn("keeps no test", err)

    def test_a_missing_manifest_fails_closed(self):
        (self.tree / "test-tiers.json").unlink()
        code, ran, err = self.drive("--tier", "release")
        self.assertEqual((code, ran), (2, []))
        self.assertIn("no tier manifest at", err)

    def test_an_invalid_manifest_fails_closed(self):
        data = self.manifest()
        data["files"]["test_gate.py"]["tier"] = "fast"
        (self.tree / "test-tiers.json").write_text(json.dumps(data))
        code, ran, err = self.drive("--tier", "release")
        self.assertEqual((code, ran), (2, []))
        self.assertIn("FAILED CLOSED", err)
        self.assertIn("is invalid", err)

    def test_a_discovered_module_with_no_label_fails_closed_naming_the_id(self):
        # The manifest pattern is test*.py, so the loader does not see helper_checks.py; a runner whose
        # pattern is wider discovers it and finds no label for it.
        (self.tree / "helper_checks.py").write_text(
            "import unittest\n\nclass Extra(unittest.TestCase):\n    def test_extra(self):\n        pass\n")
        code, ran, err = self.drive("--tier", "release", "-p", "*.py")
        self.assertEqual((code, ran), (2, []))
        self.assertIn("FAILED CLOSED", err)
        self.assertIn("no tier label", err)
        self.assertIn("helper_checks.Extra.test_extra", err)
        # positive control: the default pattern leaves the helper out and the same run succeeds
        code, ran, err = self.drive("--tier", "release")
        self.assertEqual(code, 0, err[-500:])

    def test_an_import_error_in_a_labelled_file_still_runs_and_fails_under_tier(self):
        (self.tree / "test_gate.py").write_text("import module_that_is_absent\nimport unittest\n\nclass Gate(unittest.TestCase):\n    def test_x(self):\n        pass\n\n    def test_y(self):\n        pass\n")
        code, ran, err = self.drive("--tier", "dev")
        self.assertEqual(code, 1, err[-500:])
        self.assertTrue(any(i.startswith("unittest.loader._FailedTest.test_gate") for i in ran), ran)

    def test_tier_refuses_flagged(self):
        code, ran, err = self.drive("--tier", "release", "--flagged")
        self.assertEqual(code, 2)
        self.assertIn("--tier chooses its own selection", err)

    def test_tier_with_failed_from_reruns_only_failed_tests_of_that_tier(self):
        rows = [{"id": "test_basic.Critical.test_c", "kind": "test", "outcome": "fail"},
                {"id": "test_gate.Gate.test_y", "kind": "test", "outcome": "fail"}]
        failed = self.base / "failed.jsonl"
        failed.write_text("".join(json.dumps(r) + "\n" for r in rows))
        code, ran, err = self.drive("--tier", "release", "--failed-from", str(failed))
        self.assertEqual((code, ran), (0, ["test_basic.Critical.test_c"]), err[-500:])

    def test_the_header_reports_the_discovered_count_of_the_selection(self):
        code, ran, err = self.drive("--tier", "release")
        self.assertRegex(err, re.compile(r"discovered 3 tests in \d+ units"))

    def test_a_module_that_changes_sys_path_at_import_still_runs_under_tier(self):
        # The real suites hold modules that insert into sys.path when imported. A tier selection that
        # discovered in the coordinator's own process added those entries a second time, so every
        # worker failed the sys.path comparison (sys-path-mismatch, exit 2). The positive control is
        # the same tree without --tier, which always passed.
        (self.tree / "test_basic.py").write_text(
            "import sys\nsys.path.insert(0, %r)\n" % str(self.base) + (FIXTURE / "test_basic.py").read_text())
        code, ran, err = self.drive()
        self.assertEqual(code, 0, err[-500:])
        code, ran, err = self.drive("--tier", "release")
        self.assertEqual(code, 0, err[-800:])
        self.assertEqual(ran, ["test_basic.Critical.test_c", "test_basic.Critical.test_d", "test_gate.Gate.test_x"])


if __name__ == "__main__":
    unittest.main()
