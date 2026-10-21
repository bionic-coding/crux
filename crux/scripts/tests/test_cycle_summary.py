"""`cycle.py show` and `validate` print a bounded summary; `--full` prints the whole record."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle
from cycle_workflow import PHASES, create, load, mutate

SUMMARY_KEYS = {'id', 'type', 'title', 'status', 'phase', 'pass', 'pass_limit', 'plan_revision', 'blocker', 'tasks',
                'required_checks', 'evidence_count', 'latest_review', 'decision_count', 'recent_history'}
TASK_KEYS = {'id', 'phase', 'status', 'stage', 'assignee', 'commits', 'description'}


class SummaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / 'repo'; self.repo.mkdir()
        (self.repo / 'bionic').mkdir()
        (self.repo / 'bionic/manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\nadr:\n  next_number: 1\n')
        (self.repo / 'bionic/objectives.md').write_text('Mission: useful changes.')
        doc = create(self.repo, 'iterate', 'Change', 'Goal', ['src'], ['Works'], 'dev', 'lead')
        plan = json.loads(json.dumps(doc['plan']))
        plan.update(verification=['t'], tasks=[{'id': p, 'phase': p, 'description': p, 'depends_on': [], 'status': 'pending', 'expected_evidence': ['x']} for p in PHASES['iterate']])
        self.cid = mutate(self.repo, doc['id'], 'plan', plan=plan, reason='p')['id']
        self.path = self.repo / 'bionic/cycles' / self.cid / 'cycle.json'

    def run_cli(self, *argv, expect=0):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cycle.main(['--repo-root', str(self.repo), *argv])
        self.assertEqual(code, expect, out.getvalue())
        return out.getvalue()

    def test_default_show_and_validate_print_summary(self):
        for command in ('show', 'validate'):
            body = json.loads(self.run_cli(command, self.cid))
            self.assertTrue(body['ok']); self.assertNotIn('cycle', body)
            s = body['summary']
            self.assertEqual(set(s), SUMMARY_KEYS)
            self.assertEqual((s['id'], s['type'], s['status']), (self.cid, 'iterate', 'active'))
            self.assertEqual(len(s['tasks']), len(PHASES['iterate']))
            self.assertEqual(set(s['tasks'][0]), TASK_KEYS)
            self.assertLessEqual(len(s['recent_history']), 5)
            self.assertEqual(s['recent_history'][-1]['action'], 'plan')
            self.assertEqual(set(s['recent_history'][-1]), {'action', 'at'})

    def test_full_is_the_whole_record_as_printed_before(self):
        expected = json.dumps({'ok': True, 'cycle': load(self.repo, self.cid)}, indent=2) + '\n'
        for command in ('show', 'validate'):
            self.assertEqual(self.run_cli(command, self.cid, '--full'), expected)

    def test_compact_keeps_its_shape(self):
        for command in ('show', 'validate'):
            body = json.loads(self.run_cli('--compact', command, self.cid))
            self.assertEqual(set(body), {'ok', 'cycle', 'phase', 'pass', 'status', 'updated_at', 'changed'})
            self.assertIs(body['changed'], False)
            body = json.loads(self.run_cli(command, self.cid, '--compact'))
            self.assertEqual(body['cycle'], self.cid)

    def test_invalid_record_still_exits_1(self):
        doc = json.loads(self.path.read_text()); doc['status'] = 'nonsense'
        self.path.write_text(json.dumps(doc))
        for command in ('show', 'validate'):
            self.assertFalse(json.loads(self.run_cli(command, self.cid, expect=1))['ok'])

    def test_large_record_summary_is_bounded(self):
        doc = json.loads(self.path.read_text())
        long = 'x' * 600
        doc['title'] = 'T' * 500
        doc['plan']['scope'] = ['s' * 1000] * 10
        doc['plan']['constraints'] = ['c' * 1000] * 10
        doc['plan']['acceptance'] = ['a' * 1000] * 10
        doc['plan']['verification'] = ['v' * 1000] * 5
        for i in range(45):
            doc['plan']['tasks'].append({'id': f'B{i}', 'phase': 'build', 'description': long, 'depends_on': [], 'status': 'done',
                                         'expected_evidence': [long], 'assignee': 'dev-lead', 'stage': 'integrated',
                                         'commits': ['a' * 40, 'b' * 40], 'note': long})
        for i in range(210):
            doc['history'].append({'at': '2026-10-18T00:00:00+00:00', 'action': 'task', 'pass': 1, 'phase': 'build', 'status': 'active', 'detail': long})
        doc['required_checks'] = [f'chk{i}' for i in range(5)]
        self.path.write_text(json.dumps(doc))
        full = self.run_cli('show', self.cid, '--full')
        self.assertGreater(len(full.encode()), 30_000)
        self.assertGreaterEqual(len(doc['plan']['tasks']), 40)
        self.assertGreaterEqual(len(doc['history']), 200)
        out = self.run_cli('show', self.cid)
        self.assertLess(len(out.encode()), 16_000, len(out.encode()))
        s = json.loads(out)['summary']
        self.assertEqual(len(s['tasks']), len(doc['plan']['tasks']))
        task = next(t for t in s['tasks'] if t['id'] == 'B0')
        self.assertEqual(task['commits'], ['a' * 12, 'b' * 12])
        self.assertLessEqual(len(task['description']), 100)
        self.assertEqual(len(s['recent_history']), 5)


if __name__ == '__main__':
    unittest.main()
