"""A receipt binds to the package set the requirement installs, not to the raw ``uv.lock`` bytes.

A requirement that leaves the project out (``project: false``) installs from a lock export that
omits the project, so an edit that touches only the project's own entry in ``uv.lock`` changes
nothing it installs. A requirement that includes the project (``project: true``) installs the
project at its version, so the same edit must still invalidate it. Any change to another package's
version or hashes invalidates both. A receipt recorded under the earlier raw-bytes digest no longer
matches: the next lookup reports it missing and executes once, then records the new digest.
"""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _evidence_fixtures import PYPROJECT, conditional_dists, lock_requirement, make_venv, write_lock_project
import test_evidence as te
from test_evidence import execute, lookup

HASH_A = "sha256:" + "a" * 64
HASH_B = "sha256:" + "b" * 64
DEP_A = 'name = "dep-a"\nversion = "1.0"\nsource = { registry = "https://pypi.org/simple" }\n'


class LockBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls._tmp.cleanup)
        parent = Path(cls._tmp.name)
        cls.core_python = make_venv(parent, "core", conditional_dists(False))
        cls.tools_python = make_venv(parent, "tools", conditional_dists(True))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.store = self.root / "evidence"
        patcher = patch.dict(os.environ, {"CRUX_TEST_EVIDENCE_STORE": str(self.store)})
        patcher.start()
        self.addCleanup(patcher.stop)
        write_lock_project(self.root)
        (self.root / "input.txt").write_text("one")

    def declaration(self, project):
        # No lock file among the inputs: the requirement's lock binding is the only lock evidence.
        return {"check_id": "tools" if project else "core", "command": ["python", "-c", "print('ok')"],
                "inputs": ["input.txt"], "environment": [], "requirement": lock_requirement(project)}

    def record(self, project):
        python = self.tools_python if project else self.core_python
        return execute(self.root, self.declaration(project), interpreter=python)["evidence"]

    def edit_lock(self, old, new):
        path = self.root / "uv.lock"
        text = path.read_text()
        self.assertIn(old, text)
        path.write_text(text.replace(old, new))

    def bump_project_version(self):
        self.edit_lock('name = "fixture-project"\nversion = "0.1.0"', 'name = "fixture-project"\nversion = "0.1.1"')
        (self.root / "pyproject.toml").write_text(PYPROJECT.replace('version = "0.1.0"', 'version = "0.1.1"'))

    def test_a_version_only_edit_of_the_project_entry_keeps_a_project_free_receipt_reusable(self):
        passed = self.record(project=False)
        before = te.snapshot(self.root, self.declaration(False))
        self.bump_project_version()
        after = te.snapshot(self.root, self.declaration(False))
        self.assertEqual(before["lock_sha256"], after["lock_sha256"])
        found = lookup(self.root, self.declaration(False))
        self.assertEqual((found["state"], found["record"]["id"]), ("passed", passed["id"]))

    def test_a_dependency_version_change_invalidates_a_project_free_receipt(self):
        self.record(project=False)
        self.edit_lock('name = "dep-a"\nversion = "1.0"', 'name = "dep-a"\nversion = "1.1"')
        self.assertEqual(lookup(self.root, self.declaration(False))["state"], "inputs-changed")

    def test_a_dependency_hash_change_invalidates_a_project_free_receipt(self):
        self.edit_lock(DEP_A, DEP_A + f'sdist = {{ url = "https://example.invalid/dep-a-1.0.tar.gz", hash = "{HASH_A}" }}\n')
        self.record(project=False)
        self.assertEqual(lookup(self.root, self.declaration(False))["state"], "passed")
        self.edit_lock(HASH_A, HASH_B)
        self.assertEqual(lookup(self.root, self.declaration(False))["state"], "inputs-changed")

    def test_a_version_only_edit_still_invalidates_a_project_including_receipt(self):
        self.record(project=True)
        self.assertEqual(lookup(self.root, self.declaration(True))["state"], "passed")
        self.bump_project_version()
        self.assertEqual(lookup(self.root, self.declaration(True))["state"], "inputs-changed")

    def test_a_receipt_under_the_raw_digest_no_longer_matches_and_the_next_lookup_executes(self):
        with patch.object(te, "_lock_binding", lambda path, lock: te.file_digest(path)):
            legacy = self.record(project=False)  # what the engine recorded before this binding
        self.assertEqual(legacy["lock_sha256"], te.file_digest(self.root / "uv.lock"))
        self.assertEqual(lookup(self.root, self.declaration(False))["state"], "inputs-changed")
        again = execute(self.root, self.declaration(False), interpreter=self.core_python)
        self.assertEqual(again["action"], "executed")
        self.assertNotEqual(again["evidence"]["lock_sha256"], legacy["lock_sha256"])
        self.assertEqual(lookup(self.root, self.declaration(False))["record"]["id"], again["evidence"]["id"])

    def test_a_pinned_package_requirement_has_no_lock_digest(self):
        declaration = dict(self.declaration(False), requirement=lock_requirement(False, packages={"pins": ["dep-a==1.0"]}))
        self.assertIsNone(te.snapshot(self.root, declaration)["lock_sha256"])


if __name__ == "__main__":
    unittest.main()
