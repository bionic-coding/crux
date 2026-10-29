"""test-evidence.py needs PyYAML only where it can change a fingerprint, and refuses there with exit 2.

PyYAML reads the changelog citation projection. A migration batch under the docs root
(``adrs/migrations/*.yaml``) selects that projection for the registered checkout declaration, and a
declaration may carry a ``changelog-citations:`` projection itself. Without PyYAML in either case,
the projection reader's import used to fail silently and a valid receipt read as "relevant inputs
changed". Where neither holds, no fingerprint reads YAML and the engine runs as it did before.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "test-evidence.py"
# Runs the engine with PyYAML unimportable: a None entry in sys.modules makes `import yaml` raise.
# runpy.run_path does not add the script's directory to sys.path, so the bootstrap adds it, as a
# direct script run would; without it the engine's sibling imports resolve only through an editable
# install that the locked environment lacks.
BOOTSTRAP = ("import os, sys, runpy; sys.modules['yaml'] = None; sys.argv = sys.argv[1:]; "
             "sys.path.insert(0, os.path.dirname(sys.argv[0])); runpy.run_path(sys.argv[0], run_name='__main__')")


class EvidenceYamlDependencyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.env = {**os.environ, "CRUX_TEST_EVIDENCE_STORE": str(self.root / "store")}
        self.check = self.root / "check.json"
        (self.root / "input.txt").write_text("one")
        self.check.write_text(json.dumps({"check_id": "unit", "command": ["python", "-c", "print('ok')"],
                                          "inputs": ["input.txt"], "environment": []}))

    def run_engine(self, *args, without_yaml):
        if without_yaml:
            argv = [sys.executable, "-c", BOOTSTRAP, str(SCRIPT), *args]
        else:
            argv = [sys.executable, str(SCRIPT), *args]
        return subprocess.run(argv, capture_output=True, text=True, env=self.env)

    def add_migration_batch(self):
        batches = self.root / "docs" / "adrs" / "migrations"
        batches.mkdir(parents=True)
        (batches / "batch.yaml").write_text("tasks: []\n")

    def assert_refused(self, run):
        self.assertEqual(run.returncode, 2, run.stderr)
        self.assertIn("PyYAML", run.stderr)
        self.assertIn("uv run python3", run.stderr)
        self.assertEqual(run.stdout.strip(), "", "no verdict JSON may be printed")

    def test_missing_pyyaml_with_a_migration_batch_refuses_with_exit_2_and_no_verdict(self):
        self.add_migration_batch()
        for action in ("lookup", "run"):
            with self.subTest(action=action):
                self.assert_refused(self.run_engine(action, "--repo-root", str(self.root), "--check", str(self.check),
                                                    without_yaml=True))
        self.assertFalse((self.root / "store").exists(), "the refusal must run before any receipt is written")

    def test_missing_pyyaml_with_a_changelog_projection_refuses_with_exit_2(self):
        declaration = json.loads(self.check.read_text())
        declaration["input_projections"] = {"CHANGELOG.md": ["changelog-citations:rule:one"]}
        self.check.write_text(json.dumps(declaration))
        for action in ("lookup", "run"):
            with self.subTest(action=action):
                self.assert_refused(self.run_engine(action, "--repo-root", str(self.root), "--check", str(self.check),
                                                    without_yaml=True))
        self.assertFalse((self.root / "store").exists(), "the refusal must run before any receipt is written")

    def test_missing_pyyaml_without_batch_or_projection_runs_as_before(self):
        run = self.run_engine("run", "--repo-root", str(self.root), "--check", str(self.check), without_yaml=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout)["evidence"]["status"], "passed")
        found = self.run_engine("lookup", "--repo-root", str(self.root), "--check", str(self.check), without_yaml=True)
        self.assertEqual(found.returncode, 0, found.stderr)
        self.assertEqual(json.loads(found.stdout)["state"], "passed")
        self.assertNotIn("PyYAML", run.stderr + found.stderr)

    def test_positive_control_with_pyyaml_importable_does_not_refuse(self):
        run = self.run_engine("lookup", "--repo-root", str(self.root), "--check", str(self.check), without_yaml=False)
        self.assertIn(run.returncode, (0, 1), run.stderr)
        self.assertEqual(json.loads(run.stdout)["state"], "missing")
        self.assertNotIn("PyYAML", run.stderr)

    def test_pep723_block_declares_bounded_pyyaml(self):
        block = re.search(r"# /// script\n(.*?)# ///", SCRIPT.read_text(), re.S).group(1)
        self.assertRegex(block, r'dependencies = \[.*"pyyaml>=6\.0,<7".*\]')


if __name__ == "__main__":
    unittest.main()
