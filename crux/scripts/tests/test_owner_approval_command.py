"""The owner-approval command writes the record approve-decision accepts."""
import contextlib
import io
import json
from pathlib import Path
import shlex
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle
from cycle_workflow import CycleError, mutate, tree
import test_cycle_workflow as T

QUOTE = "I approve revision 1; it's fine. $(rm -rf /) `x` \"ok\""


class OwnerApprovalCommandTests(unittest.TestCase):
    # Borrow the fixture helpers without inheriting (and re-running) the base tests.
    setUp_base = T.CycleTests.setUp
    cycle = T.CycleTests.cycle
    apply = T.CycleTests.apply
    plan = T.CycleTests.plan
    advance = T.CycleTests.advance
    idr = T.CycleTests.idr

    def setUp(self):
        self.setUp_base()
        self.doc = self.idr(self.plan(self.cycle('dev')))
        self.subject = self.doc['decisions'][-1]['path']

    def run_cli(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cycle.main(['--repo-root', str(self.repo), *argv])
        return code, out.getvalue()

    def args(self, **kw):
        base = ['owner-approval', self.doc['id'], '--subject', self.subject, '--quote', QUOTE,
                '--conversation', 'owner chat 2026-10-18', '--date', '2026-10-18']
        return base + list(kw.get('extra', []))

    def record_path(self):
        return tree(self.repo).docs_root / f"cycles/{self.doc['id']}/approvals/owner-{Path(self.subject).stem}.json"

    def test_record_written_and_accepted_by_approve_decision(self):
        code, out = self.run_cli(*self.args())
        self.assertEqual(code, 0, out)
        record = json.loads(self.record_path().read_text())
        self.assertEqual(record['quote'], QUOTE)
        self.assertEqual(record['origin'], 'owner-conversation')
        approved = self.apply(self.doc, 'approve-decision', subject=self.subject,
                              approval=json.loads(out)['approval'])
        self.assertTrue(approved['decisions'][-1]['approval'])
        self.assertEqual(self.advance(approved)['phase'], 'build')

    def test_paused_cycle_refuses_before_writing_a_record(self):
        self.apply(self.doc, 'pause', reason='blocked on owner')
        for extra in ([], ['--approve']):
            code, out = self.run_cli(*self.args(extra=extra))
            self.assertEqual(code, 1, out)
            self.assertIn('cycle is paused', json.loads(out)['error'])
        approvals = tree(self.repo).docs_root / f"cycles/{self.doc['id']}/approvals"
        self.assertEqual(list(approvals.glob('owner-*.json')) if approvals.exists() else [], [])

    def test_approve_flag_runs_approve_decision(self):
        code, out = self.run_cli(*self.args(extra=['--approve']))
        self.assertEqual(code, 0, out)
        self.assertTrue(json.loads(out)['cycle']['decisions'][-1]['approval'])

    def test_refusals(self):
        for quote in ('', '   '):
            code, out = self.run_cli('owner-approval', self.doc['id'], '--subject', self.subject,
                                     '--quote', quote, '--conversation', 'c')
            self.assertEqual(code, 1); self.assertIn('quote', out)
        self.assertFalse(self.record_path().exists())
        code, out = self.run_cli('owner-approval', self.doc['id'], '--subject', f"cycles/{self.doc['id']}/decisions/nope.json",
                                 '--quote', 'ok', '--conversation', 'c')
        self.assertEqual(code, 1); self.assertIn('exist', out)
        self.assertEqual(self.run_cli(*self.args())[0], 0)
        before = self.record_path().read_bytes()
        code, out = self.run_cli(*self.args())
        self.assertEqual(code, 1); self.assertIn('already exists', out)
        self.assertEqual(self.record_path().read_bytes(), before)

    def test_quote_is_required_input(self):
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            cycle.main(['--repo-root', str(self.repo), 'owner-approval', self.doc['id'],
                        '--subject', self.subject, '--conversation', 'c'])

    def test_print_command_writes_nothing_and_round_trips(self):
        code, out = self.run_cli(*self.args(extra=['--print-command']))
        self.assertEqual(code, 0, out)
        self.assertFalse(self.record_path().exists())
        line = json.loads(out)['command']
        self.assertNotIn('\n', line)
        argv = shlex.split(line)
        self.assertIn('--quote=' + QUOTE, argv)
        self.assertEqual(argv[argv.index('--repo-root') + 1], str(self.repo.resolve()))
        cli_argv = argv[argv.index('--repo-root'):]
        out2 = io.StringIO()
        with contextlib.redirect_stdout(out2):
            self.assertEqual(cycle.main(cli_argv), 0, out2.getvalue())
        self.assertTrue(json.loads(out2.getvalue())['cycle']['decisions'][-1]['approval'])
        self.assertEqual(json.loads(self.record_path().read_text())['quote'], QUOTE)


if __name__ == '__main__':
    unittest.main()
