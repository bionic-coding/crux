"""The workflow around test tiers: the registered declarations, the preset, the flagged rule and the tools.

IDR test-tiers (CYC-0105) A3, A4 and A5. The mechanism (reader, checker, runner filter) has its own tests in
test_test_tiers*.py and test_parallel_suite_tiers.py; this file covers what the evidence engine, the
flagged list and `related-tests.py` do with it:

* each checkout suite registers a release-tier declaration whose inputs equal the full suite's, and the
  tier check is a registered check over the five test roots;
* `release_groups` is the one reader of the per-suite full-or-release rule, and `full_checkout_ids` the one
  reader of what proves a whole code state;
* `declare --preset test-tiers` applies in any project, records the present roots, refuses a project with
  no manifest, and declares inputs wide enough that an added test file moves the fingerprint;
* a flagged entry must select release-tier tests, and the manifest beside the list is required;
* `related-tests.py --tier` narrows a development loop and keeps the files the change edits.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _evidence_fixtures import write_lock_project
import flagged_tests
import suite_evidence
import test_evidence as te

SCRIPTS = Path(__file__).resolve().parents[1]
CLI = SCRIPTS / "test-evidence.py"
RELATED = SCRIPTS / "related-tests.py"
DRIVER = Path(__file__).resolve().parent / "parallel_suite.py"
CORE = "checkout:unittest:crux/scripts/tests:test*.py"
TOOLS = "checkout:unittest:tools/tests:test*.py"
CORE_RELEASE = "checkout:unittest-release:crux/scripts/tests:test*.py"
TOOLS_RELEASE = "checkout:unittest-release:tools/tests:test*.py"
TIERS = "checkout:test-tiers"
FIVE_ROOTS = ("crux/scripts/tests", "tools/tests", "crux-mods/tests", "crux-opencode/tests", "crux-omp/tests")
TEST_A = "import unittest\n\n\nclass A(unittest.TestCase):\n    def test_one(self):\n        pass\n\n    def test_two(self):\n        pass\n"
TEST_B = "import unittest\n\n\nclass B(unittest.TestCase):\n    def test_x(self):\n        pass\n"


def manifest(files, areas=None):
    return json.dumps({"format": "crux.test-tiers", "version": 1, "kind": "python-unittest", "pattern": "test*.py",
                       "areas": {"core": "the core"} if areas is None else areas, "files": files})


class RegisteredTierChecksTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        write_lock_project(self.root)
        (self.root / ".python-version").write_text("3.13\n")
        self.declared = suite_evidence.registered_declarations(self.root, dev_root=self.root)

    def test_a_release_tier_declaration_equals_the_full_one_but_for_its_id_and_the_tier_flag(self):
        for full, release in ((CORE, CORE_RELEASE), (TOOLS, TOOLS_RELEASE)):
            with self.subTest(full=full):
                a, b = self.declared[full], self.declared[release]
                self.assertEqual(b["command"], [*a["command"], "--tier", "release"])
                for key in a:
                    if key not in ("check_id", "command"):
                        self.assertEqual(a[key], b[key], key)
                self.assertNotEqual(te.digest(te.normalize(a)), te.digest(te.normalize(b)))

    def test_the_tier_check_names_the_five_roots_and_requires_release_units_in_the_two_python_roots(self):
        command = self.declared[TIERS]["command"]
        self.assertEqual(command[:3], ["python", "crux/scripts/test-tiers.py", "check"])
        expect = [command[i + 1] for i, token in enumerate(command) if token == "--expect-root"]
        require = [command[i + 1] for i, token in enumerate(command) if token == "--require-release-units"]
        self.assertEqual(expect, list(FIVE_ROOTS))
        self.assertEqual(require, ["crux/scripts/tests", "tools/tests"])

    def test_the_tier_check_is_git_tracked_and_covers_every_root_the_python_suites_do_not_read(self):
        declaration = self.declared[TIERS]
        self.assertTrue(declaration["git_tracked"])
        for directory in ("crux", "tools", "crux-mods", "crux-opencode", "crux-omp"):
            self.assertIn(directory, declaration["inputs"])
        # The Python suites' inputs are not widened: a TS edit reruns the tier check and no Python suite.
        for check in (CORE, TOOLS, CORE_RELEASE, TOOLS_RELEASE):
            self.assertEqual(self.declared[check]["inputs"], suite_evidence.INPUTS)
            self.assertNotIn("crux-opencode", self.declared[check]["inputs"])
            self.assertNotIn("crux-omp", self.declared[check]["inputs"])
        te.normalize(declaration)

    def test_the_tier_check_reuses_the_checkout_exclusions_and_projections(self):
        tier, suite = self.declared[TIERS], self.declared[CORE]
        self.assertEqual(tier["exclude_inputs"], suite["exclude_inputs"])
        self.assertEqual(tier["input_projections"], suite["input_projections"])

    def test_release_groups_pair_each_suite_with_its_release_tier_declaration(self):
        groups = suite_evidence.release_groups(self.declared)
        self.assertIn((CORE, CORE_RELEASE), groups)
        self.assertIn((TOOLS, TOOLS_RELEASE), groups)
        self.assertIn((TIERS,), groups)
        self.assertEqual(sum(1 for g in groups if any("unittest" in i for i in g)), 2)
        # A release-tier id with no full twin stays a group of its own; it never disappears.
        self.assertEqual(suite_evidence.release_groups([CORE_RELEASE]), [(CORE_RELEASE,)])
        self.assertEqual(suite_evidence.release_groups([CORE]), [(CORE,)])

    def test_full_checkout_ids_leave_out_every_release_tier_declaration(self):
        self.assertEqual(suite_evidence.full_checkout_ids(self.declared), sorted([CORE, TOOLS, TIERS]))

    def test_the_release_tier_declaration_is_what_a_release_tier_run_resolves(self):
        declaration, registered = suite_evidence.declaration_for("checkout", "crux/scripts/tests", "test*.py", None,
                                                                 self.root, tier="release")
        self.assertTrue(registered)
        self.assertEqual(declaration["check_id"], CORE_RELEASE)
        full, full_registered = suite_evidence.declaration_for("checkout", "crux/scripts/tests", "test*.py", None, self.root)
        self.assertTrue(full_registered)
        self.assertEqual(full["check_id"], CORE)

    def test_the_new_ids_resolve_as_ordinary_registered_checks_in_the_evidence_and_cycle_readers(self):
        from types import SimpleNamespace
        import cycle_ops
        cfg = SimpleNamespace(repo_root=self.root)
        for check in (TIERS, CORE_RELEASE, TOOLS_RELEASE):
            with self.subTest(check=check):
                self.assertEqual(te.registered_declaration(self.root, check), self.declared[check])
                self.assertEqual(cycle_ops.check_declaration(cfg, check), self.declared[check])
        with te.call_scope():
            self.assertEqual(te.registered_declaration(self.root, TIERS), self.declared[TIERS])

    def test_any_other_tier_run_is_unregistered_and_carries_its_tier(self):
        for tier in ("dev", "ephemeral"):
            declaration, registered = suite_evidence.declaration_for("checkout", "crux/scripts/tests", "test*.py", None,
                                                                     self.root, tier=tier)
            self.assertFalse(registered, tier)
            self.assertEqual(declaration["command"][-2:], ["--tier", tier])
        declaration, registered = suite_evidence.declaration_for("staged", "crux/scripts/tests", "test*.py", None,
                                                                 self.root, minor="3.13", tier="release")
        self.assertFalse(registered, "a staged run has no release-tier declaration")


class TierPresetTests(unittest.TestCase):
    """`declare --preset test-tiers` in a temporary target project with no crux checkout."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        store = str(self.root.parent / (self.root.name + "-evidence"))
        previous = os.environ.get("CRUX_TEST_EVIDENCE_STORE")
        os.environ["CRUX_TEST_EVIDENCE_STORE"] = store
        self.addCleanup(lambda: os.environ.__setitem__("CRUX_TEST_EVIDENCE_STORE", previous) if previous is not None
                        else os.environ.pop("CRUX_TEST_EVIDENCE_STORE", None))

    def git(self, *args):
        subprocess.run(["git", "-c", "user.name=T", "-c", "user.email=t@example.invalid", *args],
                       cwd=self.root, capture_output=True, check=True)

    def write(self, rel, text):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def project(self):
        self.write("tests/test_a.py", TEST_A)
        self.write("tests/test-tiers.json", manifest({
            "test_a.py": {"tier": "dev", "overrides": {"A.test_one": {"tier": "release", "area": "core"}}}}))
        self.git("init", "-q")
        self.git("add", "-A")
        self.git("commit", "-qm", "base")

    def test_the_preset_refuses_a_project_with_no_manifest(self):
        self.write("tests/test_a.py", TEST_A)
        with self.assertRaises(te.EvidenceError) as raised:
            suite_evidence.preset_declaration(self.root, "test-tiers", "tiers")
        self.assertIn("holds no test-tiers.json", str(raised.exception))
        done = subprocess.run([sys.executable, str(CLI), "declare", "--repo-root", str(self.root), "--preset", "test-tiers",
                               "--check-id", "tiers"], capture_output=True, text=True)
        self.assertEqual(done.returncode, 2, done.stdout)
        self.assertIn("test-tiers.json", done.stderr)

    def test_the_preset_records_the_roots_that_hold_a_manifest_as_expected_roots(self):
        self.project()
        self.write("more/tests/test_b.py", TEST_B)
        self.write("more/tests/test-tiers.json", manifest({"test_b.py": {"tier": "dev"}}))
        self.git("add", "-A")  # manifests are found as git-tracked files in a work tree
        declaration = suite_evidence.preset_declaration(self.root, "test-tiers", "tiers")
        command = declaration["command"]
        self.assertEqual(command[0], "python")
        self.assertTrue(command[1].endswith("test-tiers.py"), command)
        expect = [command[i + 1] for i, token in enumerate(command) if token == "--expect-root"]
        self.assertEqual(expect, ["more/tests", "tests"])
        self.assertNotIn("--require-release-units", command)

    def test_the_preset_declares_the_whole_tree_inputs_and_each_expected_root(self):
        self.project()
        declaration = suite_evidence.preset_declaration(self.root, "test-tiers", "tiers")
        whole = suite_evidence.preset_declaration(self.root, "whole-tree", "w", command=["python", "x.py"])
        self.assertTrue(declaration["git_tracked"])
        self.assertTrue(set(whole["inputs"]) <= set(declaration["inputs"]))
        self.assertIn("tests", declaration["inputs"])
        self.assertEqual(declaration["exclude_inputs"], whole["exclude_inputs"])
        self.assertNotIn("input_projections", declaration)

    def test_the_cli_declares_the_preset(self):
        self.project()
        done = subprocess.run([sys.executable, str(CLI), "declare", "--repo-root", str(self.root), "--preset", "test-tiers",
                               "--check-id", "tiers"], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(json.loads(done.stdout), suite_evidence.preset_declaration(self.root, "test-tiers", "tiers"))

    def test_an_added_unlabelled_test_file_makes_the_earlier_receipt_unusable_and_the_check_fail(self):
        self.project()
        declaration = suite_evidence.preset_declaration(self.root, "test-tiers", "tiers")
        first = te.execute(self.root, declaration)
        self.assertEqual((first["action"], first["evidence"]["status"]), ("executed", "passed"))
        # Positive control: with nothing changed the same receipt is reused, so the change below is what moved it.
        again = te.execute(self.root, declaration)
        self.assertEqual((again["action"], again["evidence"]["id"]), ("reused", first["evidence"]["id"]))
        # The new file is untracked: only the root directory input can see it.
        self.write("tests/test_b.py", TEST_B)
        self.assertEqual(te.lookup(self.root, declaration)["state"], "inputs-changed")
        second = te.execute(self.root, declaration)
        self.assertEqual(second["action"], "executed")
        self.assertNotEqual(second["evidence"]["id"], first["evidence"]["id"])
        self.assertEqual(second["evidence"]["status"], "failed")
        output = (te.storage(self.root) / second["evidence"]["output"]).read_text()
        self.assertIn("unlabelled", output)
        self.assertIn("test_b.py", output)


class ParallelSuiteSharedTierTests(unittest.TestCase):
    """`--shared-evidence` takes `--tier release` alone, for the registered release-tier declaration."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        write_lock_project(self.root)
        (self.root / ".python-version").write_text("3.13\n")
        (self.root / "crux/scripts/tests").mkdir(parents=True)
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)

    def drive(self, *args):
        env = {**os.environ, "CRUX_TEST_EVIDENCE_STORE": str(self.root.parent / (self.root.name + "-evidence"))}
        return subprocess.run([sys.executable, str(DRIVER), "crux/scripts/tests", "--shared-evidence", *args],
                              capture_output=True, text=True, cwd=self.root, env=env, timeout=120)

    def test_a_release_tier_plan_names_the_release_tier_declaration(self):
        done = self.drive("--tier", "release", "--plan-test-evidence")
        self.assertEqual(done.returncode, 3, done.stdout + done.stderr)
        plan = json.loads(done.stdout.split("Test evidence plan: ", 1)[1].splitlines()[0])
        self.assertEqual(plan["check_id"], CORE_RELEASE)
        full = self.drive("--plan-test-evidence")
        self.assertEqual(json.loads(full.stdout.split("Test evidence plan: ", 1)[1].splitlines()[0])["check_id"], CORE)

    def test_any_other_tier_with_shared_evidence_is_refused(self):
        for tiers in (["--tier", "dev"], ["--tier", "release", "--tier", "dev"], ["--tier", "release", "--select", "x"]):
            with self.subTest(tiers=tiers):
                done = self.drive(*tiers, "--plan-test-evidence")
                self.assertEqual(done.returncode, 2, done.stdout + done.stderr)
                self.assertIn("--shared-evidence takes only --tier release", done.stderr)


class RegisteredCheckCliTests(unittest.TestCase):
    """`test-evidence.py registered` plans a registered non-suite check and prints a suite run's lines."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        write_lock_project(self.root)
        (self.root / ".python-version").write_text("3.13\n")
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)

    def run_cli(self, *args):
        env = {**os.environ, "CRUX_TEST_EVIDENCE_STORE": str(self.root.parent / (self.root.name + "-evidence"))}
        return subprocess.run([sys.executable, str(CLI), "registered", "--repo-root", str(self.root), *args],
                              capture_output=True, text=True, env=env, timeout=120)

    def test_the_plan_line_names_the_tier_check_and_reports_missing_evidence(self):
        done = self.run_cli("--check-id", TIERS, "--plan-test-evidence")
        self.assertEqual(done.returncode, 3, done.stdout + done.stderr)
        plan = json.loads(done.stdout.split("Test evidence plan: ", 1)[1].splitlines()[0])
        self.assertEqual(plan["check_id"], TIERS)
        self.assertNotEqual(plan["state"], "passed")

    def test_a_suite_or_an_unregistered_id_is_refused(self):
        for check in (CORE, CORE_RELEASE, "checkout:nothing", "staged:py3.13:health"):
            with self.subTest(check=check):
                done = self.run_cli("--check-id", check, "--plan-test-evidence")
                self.assertEqual(done.returncode, 2, done.stdout + done.stderr)
                self.assertNotIn("Test evidence plan", done.stdout)

    def test_the_check_id_is_required(self):
        done = self.run_cli()
        self.assertEqual(done.returncode, 2)
        self.assertIn("--check-id", done.stderr)


class FlaggedTierTests(unittest.TestCase):
    """A flagged entry must select release-tier tests, and the manifest beside the list is required."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.tests = Path(self.temp.name).resolve()
        (self.tests / "test_a.py").write_text(
            TEST_A + "\n\nclass Late(unittest.TestCase):\n    def test_late(self):\n        pass\n")
        (self.tests / "test-tiers.json").write_text(manifest({
            "test_a.py": {"tier": "release", "area": "core",
                          "overrides": {"A.test_two": {"tier": "dev"}, "Late": {"tier": "dev"}}}}))

    def problems(self, *tests):
        entries = [{"test": t, "class": "harness", "reason": "r", "origin": "TE-0123456789abcdef"} for t in tests]
        return flagged_tests.validate(entries, ["3.13"], tiers_dir=self.tests)

    def test_entries_that_select_only_release_tests_pass(self):
        self.assertEqual(self.problems("test_a.A.test_one"), [])

    def test_a_method_in_the_dev_tier_is_refused_and_named(self):
        problems = self.problems("test_a.A.test_two")
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("test_a.A.test_two", problems[0])
        self.assertIn("dev", problems[0])

    def test_a_class_or_module_that_holds_any_non_release_test_is_refused(self):
        self.assertEqual(len(self.problems("test_a.Late")), 1)
        self.assertEqual(len(self.problems("test_a")), 1)
        self.assertEqual(len(self.problems("test_a.A")), 1, "the class holds a dev method")

    def test_an_entry_the_manifest_does_not_label_is_refused(self):
        problems = self.problems("test_gone.Case")
        self.assertEqual(len(problems), 1)
        self.assertIn("no test unit", problems[0])

    def test_the_manifest_is_required_not_optional(self):
        (self.tests / "test-tiers.json").unlink()
        problems = self.problems("test_a.A.test_one")
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("tier manifest beside the flagged list is required", problems[0])

    def test_without_a_tiers_dir_the_validator_is_unchanged(self):
        entries = [{"test": "test_a.A.test_two", "class": "harness", "reason": "r", "origin": "TE-0123456789abcdef"}]
        self.assertEqual(flagged_tests.validate(entries, ["3.13"]), [])

    def test_the_staged_flagged_check_reads_the_manifest_beside_the_committed_list(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            write_lock_project(root)
            target = root / flagged_tests.DEFAULT_RELATIVE
            target.parent.mkdir(parents=True)
            target.write_text(json.dumps({"entries": [{"test": "test_a.A.test_two", "class": "harness", "reason": "r",
                                                       "origin": "TE-0123456789abcdef"}]}))
            problems = suite_evidence.flagged_list_problems(root, root)
            self.assertEqual(len(problems), 1, "no manifest, so the check refuses")
            self.assertIn("required", problems[0])
            (target.parent / "test_a.py").write_text((self.tests / "test_a.py").read_text())
            (target.parent / "test-tiers.json").write_text((self.tests / "test-tiers.json").read_text())
            problems = suite_evidence.flagged_list_problems(root, root)
            self.assertEqual(len(problems), 1, problems)
            self.assertIn("outside the release tier", problems[0])
            target.write_text(json.dumps({"entries": [{"test": "test_a.A.test_one", "class": "harness", "reason": "r",
                                                       "origin": "TE-0123456789abcdef"}]}))
            self.assertEqual(suite_evidence.flagged_list_problems(root, root), [])

    def test_the_committed_list_selects_release_tests_once_the_real_manifest_is_in_the_tree(self):
        committed = Path(__file__).resolve().parent
        if not (committed / "test-tiers.json").is_file():
            self.skipTest("the committed core manifest is merged after this unit; the integrated tree runs this check")
        entries = flagged_tests.load(committed / "flagged_tests.json")
        self.assertEqual(flagged_tests.tier_problems(entries, committed), [])


class RelatedTestsTierTests(unittest.TestCase):
    """`related-tests.py --tier` narrows a development loop and keeps the files the change edits."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        tests = self.root / "crux/scripts/tests"
        tests.mkdir(parents=True)
        for name, cls in (("test_dev", "D"), ("test_rel", "R"), ("test_eph", "E"), ("test_mix", "M")):
            body = (f"import unittest\n\n# names widget.py\n\nclass {cls}(unittest.TestCase):\n"
                    "    def test_a(self):\n        pass\n\n    def test_b(self):\n        pass\n")
            (tests / f"{name}.py").write_text(body)
        (tests / "test-tiers.json").write_text(manifest({
            "test_dev.py": {"tier": "dev"},
            "test_rel.py": {"tier": "release", "area": "core"},
            "test_eph.py": {"tier": "ephemeral", "reason": "a one-time check", "retire_when": "the migration is archived"},
            "test_mix.py": {"tier": "dev", "overrides": {"M.test_b": {"tier": "release", "area": "core"}}}}))
        (self.root / "crux/scripts/widget.py").write_text("x = 1\n")
        (self.root / "tools/tests").mkdir(parents=True)
        (self.root / "tools/tests/test_t.py").write_text(
            "import unittest\n\n# names widget.py\n\nclass T(unittest.TestCase):\n    def test_a(self):\n        pass\n")
        (self.root / "tools/tests/test-tiers.json").write_text(manifest({"test_t.py": {"tier": "dev"}}))

    def run_related(self, *args):
        return subprocess.run([sys.executable, str(RELATED), *args, "--repo-root", str(self.root)],
                              capture_output=True, text=True)

    def listed(self, *args):
        done = self.run_related(*args)
        self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout.split()

    def test_without_a_tier_every_related_file_is_listed(self):
        self.assertEqual(self.listed("crux/scripts/widget.py"), [
            "crux/scripts/tests/test_dev.py", "crux/scripts/tests/test_eph.py", "crux/scripts/tests/test_mix.py",
            "crux/scripts/tests/test_rel.py", "tools/tests/test_t.py"])

    def test_a_tier_keeps_a_file_when_any_unit_of_it_is_in_the_tier(self):
        self.assertEqual(self.listed("crux/scripts/widget.py", "--tier", "release"),
                         ["crux/scripts/tests/test_mix.py", "crux/scripts/tests/test_rel.py"])
        self.assertEqual(self.listed("crux/scripts/widget.py", "--tier", "dev", "--tier", "release"),
                         ["crux/scripts/tests/test_dev.py", "crux/scripts/tests/test_mix.py",
                          "crux/scripts/tests/test_rel.py", "tools/tests/test_t.py"])

    def test_a_file_the_change_edits_stays_whatever_its_tier(self):
        kept = self.listed("crux/scripts/widget.py", "crux/scripts/tests/test_eph.py", "--tier", "release")
        self.assertIn("crux/scripts/tests/test_eph.py", kept)
        self.assertNotIn("crux/scripts/tests/test_dev.py", kept)

    def test_ids_print_the_selection_a_runner_reads(self):
        self.assertEqual(self.listed("crux/scripts/widget.py", "--tier", "release", "--ids"),
                         ["test_mix.M.test_b", "test_rel"])
        edited = self.listed("crux/scripts/widget.py", "crux/scripts/tests/test_mix.py", "--tier", "release", "--ids")
        self.assertIn("test_mix", edited, "an edited file runs whole")
        self.assertNotIn("test_mix.M.test_b", edited)

    def test_ids_need_a_tier(self):
        done = self.run_related("crux/scripts/widget.py", "--ids")
        self.assertEqual(done.returncode, 2)
        self.assertIn("--ids needs --tier", done.stderr)

    def test_a_missing_manifest_fails_closed(self):
        (self.root / "tools/tests/test-tiers.json").unlink()
        done = self.run_related("crux/scripts/widget.py", "--tier", "release")
        self.assertEqual(done.returncode, 2, done.stdout)
        self.assertIn("tier manifest for tools/tests", done.stderr)
        # Positive control: the same call lists the files when the manifest is present.
        (self.root / "tools/tests/test-tiers.json").write_text(manifest({"test_t.py": {"tier": "dev"}}))
        self.assertEqual(self.run_related("crux/scripts/widget.py", "--tier", "release").returncode, 0)


if __name__ == "__main__":
    unittest.main()
