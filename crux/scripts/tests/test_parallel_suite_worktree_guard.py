"""The suite driver refuses a whole suite root inside a linked git worktree.

A developer runs focused checks only. A driver run on a whole suite root in a linked worktree
(git-dir differs from git-common-dir) refuses with the code `focused-check-rule` unless
`--allow-linked-worktree` is given. A non-default `-p` pattern alone, and `--tier` alone, still
name a whole root and refuse; `--tier` together with `--select` is focused and runs. The same
root on the main checkout runs, and a root outside any git repository is never refused.
"""

import json

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

DRIVER = Path(__file__).resolve().parent / "parallel_suite.py"
CODE = "focused-check-rule"

_MANIFEST = {
    "format": "crux.test-tiers",
    "version": 1,
    "kind": "python-unittest",
    "pattern": "test*.py",
    "areas": {},
    "files": {"test_ok.py": {"tier": "dev"}},
}

_TEST_MODULE = (
    "import unittest\n\n\n"
    "class OkTests(unittest.TestCase):\n"
    "    def test_ok(self):\n"
    "        self.assertTrue(True)\n"
)


def _clean_env(ceiling=None):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    if ceiling is not None:
        env["GIT_CEILING_DIRECTORIES"] = str(ceiling)
    return env


def _git(cwd, *args):
    subprocess.run(["git", "-C", str(cwd), "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
                   check=True, capture_output=True, env=_clean_env())


class WorktreeGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = Path(tempfile.mkdtemp(prefix="crux-wtguard-")).resolve()
        cls.addClassCleanup(shutil.rmtree, cls.base, True)
        cls.main = cls.base / "main"
        (cls.main / "suite").mkdir(parents=True)
        (cls.main / "suite" / "test_ok.py").write_text(_TEST_MODULE, encoding="utf-8")
        (cls.main / "suite" / "test-tiers.json").write_text(json.dumps(_MANIFEST), encoding="utf-8")
        _git(cls.main, "init", "-q")
        _git(cls.main, "add", "-A")
        _git(cls.main, "commit", "-q", "-m", "init")
        cls.linked = cls.base / "linked"
        _git(cls.main, "worktree", "add", "-q", "-b", "side", str(cls.linked))
        # A root with no git repository above it.
        cls.plain = cls.base / "plain"
        (cls.plain / "suite").mkdir(parents=True)
        (cls.plain / "suite" / "test_ok.py").write_text(_TEST_MODULE, encoding="utf-8")

    def drive(self, root, *extra, ceiling=None):
        return subprocess.run(
            [sys.executable, str(DRIVER), str(root / "suite"), "--workers", "1", *extra],
            capture_output=True, text=True, cwd=str(root), env=_clean_env(ceiling), timeout=300)

    def test_fixture_is_a_real_linked_worktree(self):
        out = subprocess.run(["git", "-C", str(self.linked), "rev-parse", "--path-format=absolute",
                              "--git-dir", "--git-common-dir"],
                             capture_output=True, text=True, check=True, env=_clean_env()).stdout.split()
        self.assertNotEqual(out[0], out[1])

    def test_whole_suite_root_in_linked_worktree_refuses(self):
        run = self.drive(self.linked)
        self.assertEqual(run.returncode, 2, run.stderr)
        self.assertIn(CODE, run.stderr)
        self.assertIn("--allow-linked-worktree", run.stderr)
        self.assertNotIn("Ran 1 test", run.stderr)

    def test_override_flag_runs_the_root_in_a_linked_worktree(self):
        run = self.drive(self.linked, "--allow-linked-worktree")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("Ran 1 test", run.stderr)
        self.assertNotIn(CODE, run.stderr)

    def test_focused_selection_in_a_linked_worktree_runs(self):
        run = self.drive(self.linked, "--select", "test_ok.OkTests.test_ok")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("Ran 1 test", run.stderr)

    def assert_refused(self, run):
        self.assertEqual(run.returncode, 2, run.stderr)
        self.assertIn(CODE, run.stderr)
        self.assertNotIn("Ran 1 test", run.stderr)

    def test_narrowed_pattern_alone_in_a_linked_worktree_refuses(self):
        """A non-default -p still discovers a whole root, so it is not a focused check."""
        self.assert_refused(self.drive(self.linked, "-p", "test_ok.py"))

    def test_tier_alone_in_a_linked_worktree_refuses(self):
        """--tier alone runs every test of a tier across the whole root."""
        self.assert_refused(self.drive(self.linked, "--tier", "dev"))

    def test_tier_with_select_in_a_linked_worktree_runs(self):
        run = self.drive(self.linked, "--tier", "dev", "--select", "test_ok.OkTests.test_ok")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("Ran 1 test", run.stderr)
        self.assertNotIn(CODE, run.stderr)

    def test_pattern_and_tier_on_the_main_checkout_run(self):
        """Positive control for the two refusals above: the same arguments run on the main checkout."""
        for extra in (("-p", "test_ok.py"), ("--tier", "dev")):
            with self.subTest(extra=extra):
                run = self.drive(self.main, *extra)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertIn("Ran 1 test", run.stderr)
                self.assertNotIn(CODE, run.stderr)

    def test_same_root_on_the_main_checkout_runs(self):
        run = self.drive(self.main)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("Ran 1 test", run.stderr)
        self.assertNotIn(CODE, run.stderr)

    def test_root_outside_a_git_repository_is_never_refused(self):
        run = self.drive(self.plain, ceiling=self.base)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("Ran 1 test", run.stderr)
        self.assertNotIn(CODE, run.stderr)


if __name__ == "__main__":
    unittest.main()
