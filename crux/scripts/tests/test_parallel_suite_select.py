"""The driver's `--select` option runs only the named modules, classes and methods.

An id it cannot find is an error, so a stale selection never passes by running nothing. Every case
runs the driver in a subprocess over a synthetic tree built in a temporary directory.
"""
import re
import subprocess
import sys
import tempfile
import textwrap
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

class AlphaExtra(unittest.TestCase):
    def test_extra(self):
        pass

class Beta(unittest.TestCase):
    def test_three(self):
        pass
'''
MODULE_B = '''
import unittest

class Gamma(unittest.TestCase):
    def test_four(self):
        pass
'''


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.tree = Path(self.temp.name) / "tree"
        self.tree.mkdir()
        (self.tree / "test_mod_a.py").write_text(textwrap.dedent(MODULE_A))
        (self.tree / "test_mod_b.py").write_text(textwrap.dedent(MODULE_B))

    def run_driver(self, *select, extra=()):
        argv = [sys.executable, str(DRIVER), str(self.tree), "--workers", "2"]
        for item in select:
            argv += ["--select", item]
        done = subprocess.run([*argv, *extra], capture_output=True, text=True, cwd=self.temp.name, timeout=300)
        ran = re.search(r"^Ran (\d+) tests? in", done.stderr, re.M)
        return done.returncode, int(ran.group(1)) if ran else None, done.stderr

    def test_without_a_selection_every_test_runs(self):
        code, ran, err = self.run_driver()
        self.assertEqual((code, ran), (0, 5), err[-400:])

    def test_a_module_id_runs_the_whole_module(self):
        self.assertEqual(self.run_driver("test_mod_a")[:2], (0, 4))

    def test_a_class_id_runs_that_class_only(self):
        self.assertEqual(self.run_driver("test_mod_a.Alpha")[:2], (0, 2))

    def test_a_method_id_runs_that_method_only(self):
        self.assertEqual(self.run_driver("test_mod_a.Alpha.test_two")[:2], (0, 1))

    def test_an_id_matches_whole_segments_only(self):
        # `Alpha` must not select `AlphaExtra`.
        code, ran, _ = self.run_driver("test_mod_a.Alpha")
        self.assertEqual(ran, 2)
        self.assertEqual(self.run_driver("test_mod_a.AlphaExtra")[:2], (0, 1))

    def test_several_ids_run_their_union_once(self):
        self.assertEqual(self.run_driver("test_mod_a.Beta", "test_mod_b", "test_mod_a.Beta.test_three")[:2], (0, 2))

    def test_an_unknown_id_is_an_error_and_runs_nothing(self):
        code, ran, err = self.run_driver("test_mod_a.Alpha", "test_mod_a.NoSuchClass")
        self.assertEqual(code, 2, err[-400:])
        self.assertIsNone(ran)
        self.assertIn("FAILED CLOSED", err)
        self.assertIn("selection id not found: test_mod_a.NoSuchClass", err)
        self.assertNotIn("test_mod_a.Alpha\n", err)

    def test_a_partial_segment_is_an_unknown_id(self):
        code, ran, err = self.run_driver("test_mod_a.Alp")
        self.assertEqual((code, ran), (2, None), err[-400:])
        self.assertIn("selection id not found: test_mod_a.Alp", err)

    def test_a_selected_failure_still_fails_the_run(self):
        (self.tree / "test_mod_b.py").write_text(textwrap.dedent(MODULE_B) + "\n    def test_bad(self):\n        self.fail('x')\n")
        self.assertEqual(self.run_driver("test_mod_b.Gamma.test_bad")[:2], (1, 1))
        self.assertEqual(self.run_driver("test_mod_b.Gamma.test_four")[:2], (0, 1))


if __name__ == "__main__":
    unittest.main()
