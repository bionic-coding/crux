"""The driver's `--failed-from RECORDS` option reruns only what failed in an earlier `--records` run.

Every case runs the driver in a subprocess over a synthetic tree built in a temporary directory.
"""
import json
import re
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

DRIVER = Path(__file__).resolve().parent / "parallel_suite.py"

MODULE_A = '''
import unittest

class Alpha(unittest.TestCase):
    def test_one(self):
        pass
    def test_two(self):
        pass
    def test_three(self):
        pass

class Beta(unittest.TestCase):
    def test_four(self):
        pass
'''
MODULE_B = '''
import unittest

class Gamma(unittest.TestCase):
    def test_five(self):
        pass
    def test_six(self):
        pass
'''
ALL_IDS = ["test_mod_a.Alpha.test_one", "test_mod_a.Alpha.test_two", "test_mod_a.Alpha.test_three",
           "test_mod_a.Beta.test_four", "test_mod_b.Gamma.test_five", "test_mod_b.Gamma.test_six"]


def record(test_id, outcome, kind="test"):
    return {"id": test_id, "kind": kind, "outcome": outcome, "reason": "", "params": None}


class FailedFromTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.tree = Path(self.temp.name) / "tree"
        self.tree.mkdir()
        (self.tree / "test_mod_a.py").write_text(textwrap.dedent(MODULE_A))
        (self.tree / "test_mod_b.py").write_text(textwrap.dedent(MODULE_B))
        self.records = Path(self.temp.name) / "records.jsonl"

    def seed(self, failures, extra=()):
        rows = [record(i, failures.get(i, "ok")) for i in ALL_IDS] + list(extra)
        self.records.write_text("".join(json.dumps(r) + "\n" for r in rows))

    def run_driver(self, *args, failed_from="records"):
        argv = [sys.executable, str(DRIVER), str(self.tree), "--workers", "2"]
        if failed_from == "records":
            argv += ["--failed-from", str(self.records)]
        elif failed_from:
            argv += ["--failed-from", failed_from]
        started = time.perf_counter()
        done = subprocess.run([*argv, *args], capture_output=True, text=True, cwd=self.temp.name, timeout=300)
        self.wall = time.perf_counter() - started
        ran = re.search(r"^Ran (\d+) tests? in", done.stderr, re.M)
        return done.returncode, int(ran.group(1)) if ran else None, done.stderr

    def test_one_failure_among_many_passes_runs_exactly_that_test(self):
        self.seed({"test_mod_a.Alpha.test_two": "fail"})
        out = Path(self.temp.name) / "rerun.jsonl"
        code, ran, err = self.run_driver("--records", str(out))
        self.assertEqual((code, ran), (0, 1), err[-500:])
        ids = [json.loads(line)["id"] for line in out.read_text().splitlines()]
        self.assertEqual(ids, ["test_mod_a.Alpha.test_two"])

    def test_an_error_and_a_failure_both_select(self):
        self.seed({"test_mod_a.Beta.test_four": "error", "test_mod_b.Gamma.test_six": "fail"})
        self.assertEqual(self.run_driver()[:2], (0, 2))

    def test_a_failed_subtest_selects_its_parent_test(self):
        self.seed({"test_mod_b.Gamma.test_five": "none"},
                  extra=[record("test_mod_b.Gamma.test_five", "fail", kind="subtest")])
        self.assertEqual(self.run_driver()[:2], (0, 1))

    def test_a_failed_class_fixture_selects_its_class(self):
        self.seed({}, extra=[record("setUpClass (test_mod_a.Alpha)", "error", kind="holder")])
        self.assertEqual(self.run_driver()[:2], (0, 3))

    def test_a_failed_teardown_fixture_selects_its_class(self):
        # A run whose only failure is a tearDownClass holder must not read as "nothing to run".
        self.seed({}, extra=[record("tearDownClass (test_mod_a.Alpha)", "error", kind="holder")])
        self.assertEqual(self.run_driver()[:2], (0, 3))

    def test_skips_and_passes_select_nothing(self):
        self.seed({"test_mod_a.Alpha.test_one": "skip", "test_mod_a.Alpha.test_two": "xfail"})
        code, ran, err = self.run_driver()
        self.assertEqual((code, ran), (0, None), err[-500:])
        self.assertIn("no failed or errored test", err)

    def test_a_missing_file_is_refused_with_exit_2(self):
        code, ran, err = self.run_driver(failed_from=str(Path(self.temp.name) / "absent.jsonl"))
        self.assertEqual((code, ran), (2, None), err[-500:])
        self.assertIn("FAILED CLOSED", err)

    def test_a_malformed_file_is_refused_with_exit_2(self):
        self.records.write_text('{"id": "x", "kind": "test", "outcome": "fail"}\nnot json\n')
        code, ran, err = self.run_driver()
        self.assertEqual((code, ran), (2, None), err[-500:])
        self.assertIn("FAILED CLOSED", err)
        self.assertIn("line 2", err)

    def test_a_file_with_no_test_records_is_refused(self):
        self.records.write_text("")
        code, ran, err = self.run_driver()
        self.assertEqual((code, ran), (2, None), err[-500:])
        self.assertIn("holds no test record", err)

    def test_select_narrows_the_failed_set(self):
        self.seed({"test_mod_a.Alpha.test_one": "fail", "test_mod_b.Gamma.test_six": "fail"})
        self.assertEqual(self.run_driver("--select", "test_mod_b")[:2], (0, 1))

    def test_select_that_excludes_every_failure_runs_nothing(self):
        self.seed({"test_mod_a.Alpha.test_one": "fail"})
        code, ran, err = self.run_driver("--select", "test_mod_b")
        self.assertEqual((code, ran), (0, None), err[-500:])
        self.assertIn("no failed or errored test", err)

    def test_a_stale_failed_id_is_an_error(self):
        self.seed({}, extra=[record("test_mod_a.Alpha.test_gone", "fail")])
        code, ran, err = self.run_driver()
        self.assertEqual((code, ran), (2, None), err[-500:])
        self.assertIn("selection id not found: test_mod_a.Alpha.test_gone", err)

    def test_it_cannot_combine_with_flagged(self):
        self.seed({})
        code, _, err = self.run_driver("--flagged")
        self.assertEqual(code, 2, err[-500:])
        self.assertIn("--failed-from", err)

    def test_the_rerun_costs_a_fraction_of_the_subset_it_replaces(self):
        # Measured cost: one test out of the seeded set. The 5.5-minute (330 s) subset of CYC-0095 held many.
        self.seed({"test_mod_a.Alpha.test_three": "fail"})
        self.assertEqual(self.run_driver()[:2], (0, 1))
        self.assertLess(self.wall, 30)


if __name__ == "__main__":
    unittest.main()
