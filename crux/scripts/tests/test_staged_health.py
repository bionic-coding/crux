"""The staged health check compiles every staged .py file and imports every staged script module.

Each case builds a small stage in a temporary directory. A clean stage is the control; each seeded
fault turns the check red for its own reason; and the stage listing is the same after the check ran.
"""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import staged_health

PARALLEL_SUITE = Path(__file__).resolve().parent / "parallel_suite.py"


def listing(root):
    return sorted((p.relative_to(root).as_posix(), p.stat().st_size) for p in Path(root).rglob("*"))


class HealthCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.stage = Path(self.temp.name).resolve() / "stage"
        self.scripts = self.stage / "crux/scripts"
        (self.scripts / "tests").mkdir(parents=True)
        (self.scripts / "helper.py").write_text("VALUE = 1\n")
        (self.scripts / "uses_helper.py").write_text("import helper\nassert helper.VALUE == 1\n")
        (self.scripts / "hyphen-script.py").write_text("import helper\nVALUE = helper.VALUE\n")
        (self.scripts / "tests/test_a.py").write_text("import unittest\n")
        (self.scripts / "tests/raises_at_import.py").write_text("raise RuntimeError('tests are compiled, not imported')\n")
        (self.stage / "crux-mods").mkdir()
        (self.stage / "crux-mods/tool.py").write_text("X = 1\n")
        # The fixture stage holds none of the real compiled-only modules; a listed path it lacks is a finding.
        patcher = patch.object(staged_health, "COMPILED_ONLY", {})
        patcher.start()
        self.addCleanup(patcher.stop)

    def check(self, **kwargs):
        return staged_health.check(self.stage, workers=2, **kwargs)

    def kinds(self, report):
        return sorted((f["kind"], f["path"]) for f in report["findings"])


class CleanStageTests(HealthCase):
    def test_a_clean_stage_is_healthy_and_the_counts_are_what_was_staged(self):
        report = self.check()
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["compiled"], 6)
        self.assertEqual(sorted(report["imported"]),
                         ["crux/scripts/helper.py", "crux/scripts/hyphen-script.py", "crux/scripts/uses_helper.py"])

    def test_the_stage_listing_is_unchanged_after_the_check(self):
        before = listing(self.stage)
        self.check()
        self.assertEqual(listing(self.stage), before)
        self.assertFalse(list(self.stage.rglob("__pycache__")))
        self.assertFalse(list(self.stage.rglob("*.pyc")))


class SeededFaultTests(HealthCase):
    def test_a_syntax_error_in_a_staged_file_is_a_compile_finding(self):
        (self.scripts / "tests/test_broken.py").write_text("def broken(:\n")
        report = self.check()
        self.assertEqual(self.kinds(report), [("compile", "crux/scripts/tests/test_broken.py")])
        self.assertIn("SyntaxError", report["findings"][0]["detail"])

    def test_a_syntax_error_outside_crux_scripts_is_a_compile_finding(self):
        (self.stage / "crux-mods/bad.py").write_text("x = = 1\n")
        self.assertEqual(self.kinds(self.check()), [("compile", "crux-mods/bad.py")])

    def test_an_import_error_in_a_script_module_is_an_import_finding(self):
        (self.scripts / "needs_missing.py").write_text("import no_such_dependency_for_the_health_check\n")
        report = self.check()
        self.assertEqual(self.kinds(report), [("import", "crux/scripts/needs_missing.py")])
        self.assertIn("no_such_dependency_for_the_health_check", report["findings"][0]["detail"])

    def test_a_module_that_runs_its_command_line_at_import_is_an_import_finding(self):
        (self.scripts / "runs_main.py").write_text("import sys\nsys.exit(3)\n")
        self.assertEqual(self.kinds(self.check()), [("import", "crux/scripts/runs_main.py")])

    def test_a_listed_module_is_compiled_only_and_reported_with_its_reason(self):
        (self.scripts / "runs_main.py").write_text("import sys\nsys.exit(3)\n")
        report = self.check(compiled_only={"crux/scripts/runs_main.py": "runs its command line at import"})
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["compiled_only"], {"crux/scripts/runs_main.py": "runs its command line at import"})
        (self.scripts / "runs_main.py").write_text("def broken(:\n")
        self.assertEqual(self.kinds(self.check(compiled_only={"crux/scripts/runs_main.py": "x"})),
                         [("compile", "crux/scripts/runs_main.py")])

    def test_a_compiled_only_entry_for_a_missing_module_is_a_finding(self):
        report = self.check(compiled_only={"crux/scripts/gone.py": "stale"})
        self.assertEqual(self.kinds(report), [("stale-compiled-only", "crux/scripts/gone.py")])


class ChildProcessTests(HealthCase):
    def test_a_child_gets_the_suite_environment_a_temporary_cwd_and_only_the_stage_scripts_on_sys_path(self):
        (self.scripts / "probe.py").write_text(
            "import os, sys\n"
            f"SCRIPTS = {str(self.scripts)!r}\n"
            "assert 'OPENROUTER_API_KEY' not in os.environ and 'PERPLEXITY_API_KEY' not in os.environ\n"
            "assert 'CRUX_ALLOW_LIVE' not in os.environ\n"
            "assert os.environ['CRUX_HOME'] and not os.environ['CRUX_HOME'].startswith(os.path.expanduser('~/.crux'))\n"
            "assert os.environ['PYTHONDONTWRITEBYTECODE'] == '1' and sys.dont_write_bytecode\n"
            "assert not os.getcwd().startswith(os.path.dirname(os.path.dirname(SCRIPTS)))\n"
            "assert sys.path[0] == SCRIPTS and sys.path.count(SCRIPTS) == 1\n"
            "assert '' not in sys.path\n")
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "k", "PERPLEXITY_API_KEY": "k", "CRUX_ALLOW_LIVE": "1"}):
            report = self.check()
        self.assertEqual(report["findings"], [])
        self.assertIn("crux/scripts/probe.py", report["imported"])

    def test_the_environment_is_built_by_the_suite_driver(self):
        # The key list is parallel_suite's; the health check reads it and keeps no copy.
        text = (SCRIPTS / "staged_health.py").read_text()
        self.assertIn("isolated_live_environment", text)
        for name in ("OPENROUTER_API_KEY", "PERPLEXITY_API_KEY", "CRUX_ALLOW_LIVE"):
            self.assertNotIn(name, text)


class CommandLineTests(HealthCase):
    def run_main(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = staged_health.main(["--root", str(self.stage), "--workers", "2", *args])
        return code, out.getvalue()

    def test_exit_zero_when_healthy_and_one_with_json_findings_when_not(self):
        code, out = self.run_main()
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads(out.strip().splitlines()[-1])["findings"], [])
        (self.scripts / "tests/test_broken.py").write_text("def broken(:\n")
        code, out = self.run_main()
        self.assertEqual(code, 1, out)
        self.assertEqual(json.loads(out.strip().splitlines()[-1])["findings"][0]["kind"], "compile")

    def test_the_script_runs_as_a_program_and_reports_through_its_exit_code(self):
        done = subprocess.run([sys.executable, str(SCRIPTS / "staged_health.py"), "--root", str(self.stage), "--workers", "2"],
                              capture_output=True, text=True)
        # The real compiled-only list names modules this fixture stage lacks, so the program reports them stale.
        self.assertEqual(done.returncode, 1, done.stderr)
        self.assertTrue(all(f["kind"] == "stale-compiled-only" for f in json.loads(done.stdout.strip().splitlines()[-1])["findings"]))

    def test_a_root_without_crux_scripts_is_an_environment_error(self):
        done = subprocess.run([sys.executable, str(SCRIPTS / "staged_health.py"), "--root", self.temp.name],
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 2)


class RealScriptsListTests(unittest.TestCase):
    def test_every_compiled_only_entry_names_a_script_and_a_reason(self):
        for path, reason in staged_health.COMPILED_ONLY.items():
            self.assertTrue((SCRIPTS.parent.parent / path).is_file(), path)
            self.assertTrue(path.startswith("crux/scripts/") and "/tests/" not in path, path)
            self.assertTrue(reason.strip(), path)


if __name__ == "__main__":
    unittest.main()
