"""related-tests.py lists the test files whose text names a changed path (F20, CYC-0096).

CYC-0095 chose its tests by hand, missed test_micro_crux_contracts.py after a change to
crux/templates/micro-crux.md.tmpl and paid one full-suite rerun.
"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _dev_surface import REPO_ROOT

TOOL = SCRIPTS / "related-tests.py"


def run(root, *args):
    return subprocess.run([sys.executable, str(TOOL), "--repo-root", str(root), *args], capture_output=True, text=True)


class RelatedTestsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def write(self, rel, text=""):
        (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
        (self.root / rel).write_text(text)

    def listed(self, *paths, root=None):
        done = run(root or self.root, *paths)
        self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout.splitlines()

    def layout(self):
        self.write("crux/scripts/tests/test_path.py", "x = 'crux/templates/a-thing.md.tmpl'\n")
        self.write("crux/scripts/tests/test_name.py", "open(root / 'a-thing.md.tmpl')\n")
        self.write("crux/scripts/tests/test_stem.py", "import suite_evidence\n")
        self.write("crux/scripts/tests/test_hyphen.py", "load('generate_micro_crux')\n")
        self.write("crux/scripts/tests/test_hyphen_file.py", "run('generate-micro-crux.py')\n")
        self.write("crux/scripts/tests/test_unrelated.py", "import json\n")
        self.write("crux/scripts/tests/test_prefix.py", "import suite_evidence_extra\n")
        self.write("tools/tests/test_tools_side.py", "import suite_evidence\n")
        self.write("crux/scripts/tests/fixtures/deep/test_nested.py", "import suite_evidence\n")

    def test_a_test_naming_the_repository_path_the_file_name_or_the_stem_is_listed(self):
        self.layout()
        self.assertEqual(self.listed("crux/templates/a-thing.md.tmpl"),
                         ["crux/scripts/tests/test_name.py", "crux/scripts/tests/test_path.py"])
        self.assertEqual(self.listed("crux/scripts/suite_evidence.py"),
                         ["crux/scripts/tests/test_stem.py", "tools/tests/test_tools_side.py"])

    def test_a_hyphenated_script_matches_by_file_name_and_by_the_importable_form(self):
        self.layout()
        self.assertEqual(self.listed("crux/scripts/generate-micro-crux.py"),
                         ["crux/scripts/tests/test_hyphen.py", "crux/scripts/tests/test_hyphen_file.py"])

    def test_a_word_boundary_keeps_a_longer_name_from_matching(self):
        self.layout()
        self.assertNotIn("crux/scripts/tests/test_prefix.py", self.listed("crux/scripts/suite_evidence.py"))

    def test_a_nested_fixture_test_is_not_a_test_file(self):
        self.layout()
        self.assertNotIn("crux/scripts/tests/fixtures/deep/test_nested.py", self.listed("crux/scripts/suite_evidence.py"))

    def test_a_changed_test_file_lists_itself(self):
        self.layout()
        self.assertEqual(self.listed("crux/scripts/tests/test_unrelated.py"), ["crux/scripts/tests/test_unrelated.py"])

    def test_one_hop_through_a_script_that_reads_the_path(self):
        # The test never names the template; it names the generator that reads it.
        self.write("crux/scripts/tests/test_unrelated.py", "import json\n")
        self.write("crux/scripts/generate-micro-crux.py", "TEMPLATE = 'micro-crux.md.tmpl'\n")
        self.write("crux/scripts/tests/test_runs_generator.py", "run('generate-micro-crux.py')\n")
        found = self.listed("crux/templates/micro-crux.md.tmpl")
        self.assertEqual(found, ["crux/scripts/tests/test_runs_generator.py"])
        report = json.loads(run(self.root, "--json", "crux/templates/micro-crux.md.tmpl").stdout)
        self.assertEqual(report["readers"], {"crux/scripts/generate-micro-crux.py": ["crux/templates/micro-crux.md.tmpl"]})
        self.assertEqual(list(report["tests"]), ["crux/scripts/tests/test_runs_generator.py"])

    def test_a_changed_module_does_not_hop_through_its_importers(self):
        self.write("crux/scripts/tests/test_direct.py", "import suite_evidence\n")
        self.write("crux/scripts/tests/test_via_reader.py", "import cycle_workflow\n")
        self.write("crux/scripts/cycle_workflow.py", "import suite_evidence\n")
        self.assertEqual(self.listed("crux/scripts/suite_evidence.py"), ["crux/scripts/tests/test_direct.py"])

    def test_a_comment_line_naming_the_path_does_not_make_a_reader(self):
        self.write("crux/scripts/tests/test_unrelated.py", "import json\n")
        self.write("crux/scripts/generate-micro-crux.py", "# see micro-crux.md.tmpl\n")
        self.write("crux/scripts/tests/test_runs_generator.py", "run('generate-micro-crux.py')\n")
        self.assertEqual(self.listed("crux/templates/micro-crux.md.tmpl"), [])

    def test_json_reports_the_matched_tokens(self):
        self.layout()
        report = json.loads(run(self.root, "--json", "crux/templates/a-thing.md.tmpl").stdout)
        self.assertEqual(report["changed"], ["crux/templates/a-thing.md.tmpl"])
        self.assertEqual(report["tests"]["crux/scripts/tests/test_path.py"], ["crux/templates/a-thing.md.tmpl"])

    def test_a_missing_tools_directory_is_skipped_as_in_the_staged_artifact(self):
        self.write("crux/scripts/tests/test_stem.py", "import suite_evidence\n")
        self.assertEqual(self.listed("crux/scripts/suite_evidence.py"), ["crux/scripts/tests/test_stem.py"])

    def test_no_match_prints_nothing_and_exits_zero(self):
        self.layout()
        done = run(self.root, "docs/nothing-names-this.md")
        self.assertEqual((done.returncode, done.stdout), (0, ""))

    def test_an_absolute_path_inside_the_root_is_accepted(self):
        self.layout()
        self.assertEqual(self.listed(str(self.root / "crux/templates/a-thing.md.tmpl")),
                         ["crux/scripts/tests/test_name.py", "crux/scripts/tests/test_path.py"])

    def test_environment_errors_exit_two_with_a_message_on_stderr(self):
        self.layout()
        outside = run(self.root, "../elsewhere.py")
        self.assertEqual((outside.returncode, outside.stdout), (2, ""))
        self.assertIn("outside the repository root", outside.stderr)
        with tempfile.TemporaryDirectory() as empty:
            bare = run(Path(empty), "crux/x.py")
            self.assertEqual((bare.returncode, bare.stdout), (2, ""))
            self.assertIn("no test directory", bare.stderr)

    def test_the_root_comes_from_the_working_directory_not_the_script_path(self):
        self.layout()
        done = subprocess.run([sys.executable, str(TOOL), "crux/templates/a-thing.md.tmpl"], cwd=self.root,
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout.splitlines(), ["crux/scripts/tests/test_name.py", "crux/scripts/tests/test_path.py"])

    def test_a_directory_enumerating_test_is_not_found(self):
        # The stated limit: the test globs the directory and never names the file.
        self.write("crux/scripts/tests/test_glob.py", "list(Path('crux/templates').glob('*.tmpl'))\n")
        self.assertEqual(self.listed("crux/templates/a-thing.md.tmpl"), [])


class LiveTreeTests(unittest.TestCase):
    def test_the_micro_crux_template_reaches_its_contract_test(self):
        template = REPO_ROOT / "crux/templates/micro-crux.md.tmpl"
        if not template.is_file() or not (REPO_ROOT / "crux/scripts/generate-micro-crux.py").is_file():
            self.skipTest("this tree carries no micro-crux template or generator")
        done = run(REPO_ROOT, "crux/templates/micro-crux.md.tmpl")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("crux/scripts/tests/test_micro_crux_contracts.py", done.stdout.splitlines())


if __name__ == "__main__":
    unittest.main()
