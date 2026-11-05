"""The flagged list: its validator, its selection for a minor, and the check that runs it.

The check runs only the tests the committed list names for the running minor. An entry whose test
skips, and an entry that selects no test, fail it. Driver cases run in a subprocess over a synthetic
tree in a temporary directory.
"""
import json
import re
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import flagged_tests as ft
from _dev_surface import REPO_ROOT, require_dev_surface

DRIVER = Path(__file__).resolve().parent / "parallel_suite.py"
COMMITTED = Path(__file__).resolve().parent / "flagged_tests.json"


def entry(test="test_mod.Case.test_ok", **change):
    base = {"test": test, "class": "cross-minor", "reason": "differs between interpreters",
            "origin": "TE-38c9a749c2144cd58869e5f994dc9ff9"}
    base.update(change)
    return {k: v for k, v in base.items() if v is not None}


class ValidatorTests(unittest.TestCase):
    def problems(self, *entries, minors=("3.13", "3.14")):
        return ft.validate(list(entries), minors)

    def test_a_complete_entry_is_accepted_with_or_without_minors(self):
        self.assertEqual(self.problems(entry(), entry("test_mod.Other", minors=["3.14"])), [])

    def test_an_entry_missing_class_reason_or_origin_is_refused(self):
        for field in ("class", "reason", "origin"):
            with self.subTest(field=field):
                problems = self.problems(entry(**{field: None}))
                self.assertEqual(len(problems), 1, problems)
                self.assertIn(field, problems[0])
                self.assertIn("test_mod.Case.test_ok", problems[0])

    def test_a_blank_value_counts_as_missing(self):
        for field in ("reason", "origin", "test"):
            with self.subTest(field=field):
                self.assertTrue(self.problems(entry(**{field: "  "})))

    def test_a_class_outside_the_three_is_refused(self):
        for good in ("cross-minor", "packaging", "harness"):
            self.assertEqual(self.problems(entry(**{"class": good})), [])
        self.assertTrue(self.problems(entry(**{"class": "flaky"})))

    def test_a_minor_the_project_does_not_list_is_refused(self):
        problems = self.problems(entry(minors=["3.12"]))
        self.assertEqual(len(problems), 1)
        self.assertIn("3.12", problems[0])
        self.assertTrue(self.problems(entry(minors=["3.13", "3.15"])))
        self.assertTrue(self.problems(entry(minors=[])))
        self.assertTrue(self.problems(entry(minors="3.13")))

    def test_without_a_project_matrix_the_minor_is_not_judged(self):
        self.assertEqual(ft.validate([entry(minors=["3.12"])], None), [])

    def test_an_unknown_key_and_a_duplicate_test_are_refused(self):
        self.assertTrue(self.problems(entry(extra="x")))
        self.assertTrue(self.problems(entry(), entry()))

    def test_every_problem_is_reported_not_only_the_first(self):
        self.assertEqual(len(self.problems(entry(**{"class": None}), entry("test_mod.B", origin=None))), 2)


class LoadTests(unittest.TestCase):
    def write(self, text):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        path = Path(temp.name) / "list.json"
        path.write_text(text)
        return path

    def test_load_returns_the_entries(self):
        path = self.write(json.dumps({"entries": [entry()]}))
        self.assertEqual(ft.load(path), [entry()])

    def test_a_malformed_file_raises_a_flagged_error(self):
        for text in ("not json", "[]", json.dumps({"entries": "x"}), json.dumps({"entries": [1]}), json.dumps({})):
            with self.subTest(text=text), self.assertRaises(ft.FlaggedError):
                ft.load(self.write(text))

    def test_selection_is_the_entries_that_apply_to_the_minor(self):
        entries = [entry("test_mod.A"), entry("test_mod.B", minors=["3.14"]), entry("test_mod.C", minors=["3.13", "3.14"])]
        self.assertEqual(ft.selection(entries, "3.13"), ["test_mod.A", "test_mod.C"])
        self.assertEqual(ft.selection(entries, "3.14"), ["test_mod.A", "test_mod.B", "test_mod.C"])


class CommittedListTests(unittest.TestCase):
    def test_the_committed_list_is_valid_for_the_project_matrix(self):
        entries = ft.load(COMMITTED)
        self.assertTrue(entries)
        require_dev_surface(self, REPO_ROOT / "pyproject.toml", "pyproject.toml")
        import tomllib
        minors = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())["tool"]["crux"]["python-versions"]
        self.assertEqual(ft.validate(entries, minors), [])

    def test_the_committed_list_names_origins_that_are_receipts_or_commits(self):
        for item in ft.load(COMMITTED):
            self.assertRegex(item["origin"], r"^(TE-[0-9a-f]{8,32}|[0-9a-f]{7,40})$", item["test"])


MODULE = '''
import unittest

class Case(unittest.TestCase):
    def test_ok(self):
        pass
    def test_also_ok(self):
        pass
    def test_skips(self):
        self.skipTest("conditionally skipped")
    @unittest.skipIf(True, "decorated skip")
    def test_decorated_skip(self):
        pass

class Other(unittest.TestCase):
    def test_other(self):
        pass
    def test_fails(self):
        self.fail("seeded")
'''


class FlaggedCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.tree = Path(self.temp.name) / "tree"
        self.tree.mkdir()
        (self.tree / "test_mod.py").write_text(textwrap.dedent(MODULE))

    def run_flagged(self, entries, minor="3.13"):
        listing = Path(self.temp.name) / "flagged.json"
        listing.write_text(json.dumps({"entries": entries}))
        done = subprocess.run([sys.executable, str(DRIVER), str(self.tree), "--workers", "2", "--flagged",
                               "--flagged-list", str(listing), "--python-minor", minor],
                              capture_output=True, text=True, cwd=self.temp.name, timeout=300)
        ran = re.search(r"^Ran (\d+) tests? in", done.stderr, re.M)
        return done.returncode, int(ran.group(1)) if ran else None, done.stdout + done.stderr

    def test_passing_entries_pass_and_only_they_run(self):
        code, ran, out = self.run_flagged([entry("test_mod.Case.test_ok"), entry("test_mod.Case.test_also_ok")])
        self.assertEqual((code, ran), (0, 2), out[-500:])

    def test_a_class_entry_selects_its_methods(self):
        self.assertEqual(self.run_flagged([entry("test_mod.Other.test_other")])[:2], (0, 1))

    def test_a_selected_failure_fails_the_check(self):
        code, ran, out = self.run_flagged([entry("test_mod.Other.test_fails")])
        self.assertEqual((code, ran), (1, 1), out[-500:])

    def test_an_entry_whose_test_skips_fails_the_check(self):
        for method in ("test_skips", "test_decorated_skip"):
            with self.subTest(method=method):
                code, ran, out = self.run_flagged([entry("test_mod.Case.test_ok"), entry("test_mod.Case." + method)])
                self.assertEqual(code, 1, out[-500:])
                self.assertIn("flagged test skipped", out)
                self.assertIn("test_mod.Case." + method, out)

    def test_a_class_entry_containing_a_skipping_method_fails_the_check(self):
        code, ran, out = self.run_flagged([entry("test_mod.Case")])
        self.assertEqual(code, 1, out[-500:])
        self.assertIn("flagged test skipped", out)

    def test_a_stale_entry_that_selects_no_test_fails_the_check_and_names_it(self):
        code, ran, out = self.run_flagged([entry("test_mod.Case.test_ok"), entry("test_mod.Case.test_renamed_away")])
        self.assertEqual(code, 1, out[-500:])
        self.assertIsNone(ran)
        self.assertIn("flagged entry selects no test: test_mod.Case.test_renamed_away", out)

    def test_an_entry_for_another_minor_is_neither_run_nor_judged(self):
        entries = [entry("test_mod.Case.test_ok"), entry("test_mod.Case.test_skips", minors=["3.14"]),
                   entry("test_mod.Gone", minors=["3.14"])]
        self.assertEqual(self.run_flagged(entries, "3.13")[:2], (0, 1))
        code, ran, out = self.run_flagged(entries, "3.14")
        self.assertEqual(code, 1, out[-500:])
        self.assertIn("test_mod.Gone", out)

    def test_a_minor_with_no_applicable_entry_runs_nothing_and_passes(self):
        code, ran, out = self.run_flagged([entry("test_mod.Case.test_skips", minors=["3.14"])], "3.13")
        self.assertEqual((code, ran), (0, None), out[-500:])
        self.assertIn("no flagged entry applies to Python 3.13", out)

    def test_an_invalid_list_is_refused_before_anything_runs(self):
        code, ran, out = self.run_flagged([entry("test_mod.Case.test_ok", **{"class": None})])
        self.assertEqual((code, ran), (2, None), out[-500:])
        self.assertIn("class", out)


if __name__ == "__main__":
    unittest.main()
