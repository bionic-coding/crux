"""An untracked git-ignored file under a declared input does not change the fingerprint."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import test_evidence as te
from test_evidence import execute, lookup, snapshot


def run_git(cwd, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args], cwd=cwd, check=True, capture_output=True)


class IgnoredInputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name).resolve()
        patcher = patch.dict(os.environ, {"CRUX_TEST_EVIDENCE_STORE": str(base / "store")})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.main = base / "main"
        (self.main / "src").mkdir(parents=True)
        run_git(base, "init", "-q", str(self.main))
        (self.main / ".gitignore").write_text("*.lock\nsrc/pinned.txt\n")
        (self.main / "src" / "a.txt").write_text("a")
        (self.main / "src" / "tracked.lock").write_text("tracked despite the ignore rule")
        run_git(self.main, "add", "-f", ".")
        run_git(self.main, "commit", "-q", "-m", "base")
        self.clean = base / "clean"
        run_git(base, "clone", "-q", str(self.main), str(self.clean))
        self.decl = {"check_id": "unit", "command": [sys.executable, "-c", "pass"], "inputs": ["src"], "environment": []}

    def recorded(self):
        result = execute(self.clean, self.decl)
        self.assertEqual(result["evidence"]["status"], "passed")
        return result["evidence"]["id"]

    def test_ignored_untracked_file_reuses_a_receipt_from_a_clean_clone(self):
        receipt = self.recorded()
        (self.main / "src" / "attempt-1.lock").write_text("held")
        found = lookup(self.main, self.decl)
        self.assertEqual(found["state"], "passed")
        self.assertEqual(found["record"]["id"], receipt)

    def test_tracked_edit_untracked_file_and_tracked_ignored_edit_still_invalidate(self):
        receipt = self.recorded()
        self.assertEqual(lookup(self.main, self.decl)["record"]["id"], receipt, "positive control: equal inputs reuse")
        (self.main / "src" / "attempt-1.lock").write_text("held")
        self.assertEqual(lookup(self.main, self.decl)["state"], "passed")
        for label, mutate in (
            ("tracked edit", lambda: (self.main / "src" / "a.txt").write_text("b")),
            ("tracked file matched by an ignore rule", lambda: (self.main / "src" / "tracked.lock").write_text("changed")),
        ):
            with self.subTest(label):
                mutate()
                self.assertEqual(lookup(self.main, self.decl)["state"], "inputs-changed")
                run_git(self.main, "checkout", "--", "src")
                self.assertEqual(lookup(self.main, self.decl)["state"], "passed")
        (self.main / "src" / "new.txt").write_text("untracked and not ignored")
        self.assertEqual(lookup(self.main, self.decl)["state"], "inputs-changed")

    def test_a_literally_declared_ignored_file_still_counts(self):
        decl = dict(self.decl, inputs=["src/pinned.txt"])
        (self.main / "src" / "pinned.txt").write_text("one")
        first = snapshot(self.main, decl)
        self.assertIn("src/pinned.txt", first["inputs"])
        (self.main / "src" / "pinned.txt").write_text("two")
        self.assertNotEqual(first["fingerprint"], snapshot(self.main, decl)["fingerprint"])

    def test_a_directory_input_drops_its_ignored_files_from_the_snapshot(self):
        (self.main / "src" / "pinned.txt").write_text("ignored")
        self.assertNotIn("src/pinned.txt", snapshot(self.main, self.decl)["inputs"])

    def test_without_git_every_file_counts(self):
        (self.main / "src" / "attempt-1.lock").write_text("held")
        with patch.object(te.subprocess, "run", side_effect=FileNotFoundError("git")):
            counted = snapshot(self.main, self.decl)["inputs"]
        self.assertIn("src/attempt-1.lock", counted)
        self.assertNotIn("src/attempt-1.lock", snapshot(self.main, self.decl)["inputs"])

    def test_outside_a_work_tree_every_file_counts(self):
        loose = Path(self.temp.name) / "loose"
        (loose / "src").mkdir(parents=True)
        (loose / "src" / "x.lock").write_text("x")
        with patch.dict(os.environ, {"GIT_CEILING_DIRECTORIES": str(Path(self.temp.name))}):
            self.assertIn("src/x.lock", snapshot(loose, self.decl)["inputs"])


if __name__ == "__main__":
    unittest.main()
