"""`cycle.py status` runs through main() with and without a cycle id (non-watch path)."""
import contextlib
import io
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle
import test_cycle_workflow as T


class CycleStatusMainTests(unittest.TestCase):
    setUp = T.CycleTests.setUp
    cycle = T.CycleTests.cycle

    def run_cli(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cycle.main(['--repo-root', str(self.repo), *argv])
        return code, out.getvalue()

    def test_status_with_cycle_id_returns_zero(self):
        doc = self.cycle('dev')
        code, out = self.run_cli('status', doc['id'])
        self.assertEqual(code, 0, out)
        self.assertIn(doc['id'], out)

    def test_status_without_cycle_id_returns_zero(self):
        doc = self.cycle('dev')
        code, out = self.run_cli('status')
        self.assertEqual(code, 0, out)
        self.assertIn(doc['id'], out)

    def test_status_json_is_a_document(self):
        doc = self.cycle('dev')
        code, out = self.run_cli('status', doc['id'], '--json')
        self.assertEqual(code, 0, out)
        self.assertIsInstance(json.loads(out), dict)


if __name__ == '__main__':
    unittest.main()
