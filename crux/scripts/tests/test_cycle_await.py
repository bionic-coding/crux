"""The read-only await subcommand: wait for a delegated task's result file."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle
from cycle_workflow import PHASES, create, mutate


class AwaitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo'; self.repo.mkdir()
        (self.repo / 'bionic').mkdir()
        (self.repo / 'bionic/manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\nadr:\n  next_number: 1\n')
        (self.repo / 'bionic/objectives.md').write_text('Mission: useful changes.')
        doc = create(self.repo, 'iterate', 'Change', 'Goal', ['src'], ['Works'], 'dev', 'lead')
        plan = json.loads(json.dumps(doc['plan']))
        tasks = [{'id': p, 'phase': p, 'description': p, 'depends_on': [], 'status': 'pending', 'expected_evidence': ['x']} for p in PHASES['iterate']]
        for tid in ('B2', 'B3'):
            tasks.append({'id': tid, 'phase': 'build', 'description': tid, 'depends_on': [], 'status': 'pending', 'expected_evidence': ['x']})
        plan.update(verification=['t'], tasks=tasks)
        self.cid = mutate(self.repo, doc['id'], 'plan', plan=plan, reason='p')['id']
        self.r2 = self.root / 'r2.md'
        mutate(self.repo, self.cid, 'task', task_id='B2', result_path=str(self.r2))
        mutate(self.repo, self.cid, 'task', task_id='B3', result_path='out/r3.md')

    def run_cli(self, *argv, expect=0):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cycle.main(['--repo-root', str(self.repo), '--compact', 'await', self.cid, *argv])
        self.assertEqual(code, expect, out.getvalue())
        return json.loads(out.getvalue())

    def record(self):
        p = self.repo / 'bionic/cycles' / self.cid / 'cycle.json'
        return p.read_bytes(), p.stat().st_mtime_ns

    def test_arrival_while_waiting(self):
        def later():
            time.sleep(0.6); self.r2.write_text('report')
        t = threading.Thread(target=later); t.start()
        res = self.run_cli('--task-id', 'B2', '--timeout', '20')
        t.join()
        self.assertTrue(res['ok'] and res['arrived'])
        self.assertEqual((res['task'], res['cycle'], res['result_path']), ('B2', self.cid, str(self.r2)))
        self.assertGreater(res['waited_seconds'], 0.5)

    def test_already_present(self):
        self.r2.write_text('report')
        res = self.run_cli('--task-id', 'B2', '--timeout', '10')
        self.assertTrue(res['arrived'])

    def test_empty_file_is_not_arrival(self):
        self.r2.write_text('')
        res = self.run_cli('--task-id', 'B2', '--timeout', '0.5', expect=1)
        self.assertTrue(res['ok']); self.assertFalse(res['arrived']); self.assertIsNone(res['task'])

    def test_directory_is_not_arrival(self):
        self.r2.mkdir()
        res = self.run_cli('--task-id', 'B2', '--timeout', '0.5', expect=1)
        self.assertFalse(res['arrived'])

    def test_timeout(self):
        start = time.monotonic()
        res = self.run_cli('--task-id', 'B2', '--timeout', '0.5', expect=1)
        self.assertTrue(res['ok']); self.assertFalse(res['arrived']); self.assertIsNone(res['task'])
        self.assertLess(time.monotonic() - start, 5)
        self.assertGreaterEqual(res['waited_seconds'], 0.4)

    def test_first_arrival_wins_and_relative_path(self):
        (self.repo / 'out').mkdir()
        def later():
            time.sleep(0.5); (self.repo / 'out/r3.md').write_text('three')
        t = threading.Thread(target=later); t.start()
        res = self.run_cli('--task-id', 'B2', '--task-id', 'B3', '--timeout', '20')
        t.join()
        self.assertEqual(res['task'], 'B3')
        self.assertEqual(Path(res['result_path']).resolve(), (self.repo / 'out/r3.md').resolve())

    def test_refusals(self):
        for argv in (('--task-id', 'NOPE', '--timeout', '1'),
                     ('--task-id', 'build', '--timeout', '1'),
                     ('--task-id', 'B2', '--timeout', '0'),
                     ('--task-id', 'B2', '--timeout', '-3'),
                     ('--task-id', 'B2', '--timeout', '3601')):
            with self.subTest(argv=argv):
                res = self.run_cli(*argv, expect=1)
                self.assertFalse(res['ok']); self.assertIn('error', res)
        self.assertIn('NOPE', self.run_cli('--task-id', 'NOPE', '--timeout', '1', expect=1)['error'])
        self.assertIn('result_path', self.run_cli('--task-id', 'build', '--timeout', '1', expect=1)['error'])

    def test_record_unchanged(self):
        before = self.record()
        self.r2.write_text('report')
        self.run_cli('--task-id', 'B2', '--timeout', '5')
        self.run_cli('--task-id', 'B3', '--timeout', '0.5', expect=1)
        self.assertEqual(self.record(), before)


    def test_path_form_after_closure(self):
        # Bookkeeping after closure: the path form reads no cycle, so state cannot refuse it.
        mutate(self.repo, self.cid, 'pause', reason='stop')
        mutate(self.repo, self.cid, 'reflect', reflection={'outcome': 'o', 'lessons': ['l'], 'remaining': ['none']})
        mutate(self.repo, self.cid, 'abandon')
        self.r2.write_text('report')
        before = self.record()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cycle.main(['--repo-root', str(self.repo), '--compact', 'await', '--path', str(self.r2), '--timeout', '5'])
        self.assertEqual(code, 0, out.getvalue())
        res = json.loads(out.getvalue())
        self.assertEqual((res['arrived'], res['cycle'], res['task']), (True, None, None))
        self.assertEqual(self.record(), before)

class AwaitPathTests(unittest.TestCase):
    """The path form: `await --path ABS --timeout N`, with no cycle and no task."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        # No docs tree and no cycle: the path form needs neither.
        self.repo = self.root / 'repo'; self.repo.mkdir()
        self.r = self.root / 'architect-idr-attempt-1.md'

    def run_cli(self, *argv, expect=0):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cycle.main(['--repo-root', str(self.repo), '--compact', 'await', *argv])
        self.assertEqual(code, expect, out.getvalue())
        return json.loads(out.getvalue())

    def test_arrival_while_waiting(self):
        def later():
            time.sleep(0.6); self.r.write_text('report')
        t = threading.Thread(target=later); t.start()
        res = self.run_cli('--path', str(self.r), '--timeout', '20')
        t.join()
        self.assertEqual(set(res), {'ok', 'cycle', 'arrived', 'task', 'result_path', 'waited_seconds'})
        self.assertTrue(res['ok'] and res['arrived'])
        self.assertEqual((res['cycle'], res['task'], res['result_path']), (None, None, str(self.r)))
        self.assertGreater(res['waited_seconds'], 0.5)

    def test_timeout_and_not_arrival(self):
        res = self.run_cli('--path', str(self.r), '--timeout', '0.5', expect=1)
        self.assertEqual((res['ok'], res['arrived'], res['result_path'], res['cycle']), (True, False, None, None))
        self.r.write_text('')
        self.assertFalse(self.run_cli('--path', str(self.r), '--timeout', '0.3', expect=1)['arrived'])
        self.r.unlink(); self.r.mkdir()
        self.assertFalse(self.run_cli('--path', str(self.r), '--timeout', '0.3', expect=1)['arrived'])

    def test_first_arrival_wins(self):
        other = self.root / 'plan-writer-attempt-1.md'
        def later():
            time.sleep(0.5); other.write_text('plan')
        t = threading.Thread(target=later); t.start()
        res = self.run_cli('--path', str(self.r), '--path', str(other), '--timeout', '20')
        t.join()
        self.assertEqual(res['result_path'], str(other))

    def test_writes_nothing(self):
        self.r.write_text('report')
        before = sorted(p.relative_to(self.root) for p in self.root.rglob('*'))
        self.run_cli('--path', str(self.r), '--timeout', '5')
        self.assertEqual(sorted(p.relative_to(self.root) for p in self.root.rglob('*')), before)
        self.assertEqual(self.r.read_text(), 'report')

    def test_refusals(self):
        for argv in (('--path', 'relative/r.md', '--timeout', '1'),
                     ('--path', str(self.r), '--timeout', '0'),
                     ('--path', str(self.r), '--timeout', '3601'),
                     ('CYC-0001', '--path', str(self.r), '--timeout', '1'),
                     ('--path', str(self.r), '--task-id', 'B2', '--timeout', '1'),
                     ('--timeout', '1'),
                     ('CYC-0001', '--timeout', '1')):
            with self.subTest(argv=argv):
                res = self.run_cli(*argv, expect=1)
                self.assertFalse(res['ok']); self.assertIn('error', res)
        self.assertIn('absolute', self.run_cli('--path', 'relative/r.md', '--timeout', '1', expect=1)['error'])


if __name__ == '__main__':
    unittest.main()
