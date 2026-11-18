"""`cycle.py status` runs through main() with and without a cycle id (non-watch path), on a frozen legacy record."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cycle
from _cycle_fixtures import fresh, put, tree


class CycleStatusMainTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.repo = tree(temp.name)
        self.cid = put(self.repo, fresh('dev'), 'CYC-0001')

    def run_cli(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cycle.main(['--repo-root', str(self.repo), *argv])
        return code, out.getvalue()

    def test_status_with_cycle_id_returns_zero(self):
        code, out = self.run_cli('status', self.cid)
        self.assertEqual(code, 0, out)
        self.assertIn(self.cid, out)

    def test_status_without_cycle_id_returns_zero(self):
        code, out = self.run_cli('status')
        self.assertEqual(code, 0, out)
        self.assertIn(self.cid, out)

    def test_status_json_is_a_document(self):
        code, out = self.run_cli('status', self.cid, '--json')
        self.assertEqual(code, 0, out)
        self.assertIsInstance(json.loads(out), dict)

    def test_status_rejects_the_removed_activity_flag(self):
        """`--activity` is gone: argparse exits 2 and names it as unrecognized; the plain JSON carries no activity key."""
        err = io.StringIO()
        with contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as caught:
            self.run_cli('status', self.cid, '--json', '--activity')
        self.assertEqual(caught.exception.code, 2)
        self.assertIn('unrecognized arguments: --activity', err.getvalue())
        _, plain = self.run_cli('status', self.cid, '--json')
        self.assertNotIn('activity', json.dumps(json.loads(plain)))


if __name__ == '__main__':
    unittest.main()
