"""A test file must not share a module name with a script or the standard library.

Directory discovery imports each test file by name while crux/scripts is on sys.path, so a
test file named like a script module resolves to the script and the suite driver fails closed
(the CYC-0012 test_evidence_capture collision).
"""
from pathlib import Path
import sys
import unittest

TESTS = Path(__file__).resolve().parent
SCRIPTS = TESTS.parent


def _stems(directory):
    return {p.stem for p in directory.glob("*.py")}


class ModuleNameCollisionTests(unittest.TestCase):
    def test_no_test_file_shares_a_name_with_a_script_module(self):
        shared = sorted(_stems(TESTS) & _stems(SCRIPTS))
        self.assertEqual(shared, [], "test files shadowing script modules: %s" % shared)

    def test_no_script_or_test_file_shares_a_name_with_a_standard_library_module(self):
        names = set(sys.stdlib_module_names)
        shared = sorted((_stems(SCRIPTS) | _stems(TESTS)) & names)
        self.assertEqual(shared, [], "files shadowing standard library modules: %s" % shared)


if __name__ == "__main__":
    unittest.main()
