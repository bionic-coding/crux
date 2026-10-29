"""Fix metrics: the task-add event carries the fix object and handoff lists fixes per pass and phase."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle_workflow as workflow
from test_cycle_fix_step import FixBase


class FixMetricsTests(FixBase):
    def handoff(self, cid):
        code, payload = self.run_cli('handoff', cid)
        self.assertEqual(code, 0, payload)
        return payload

    def test_handoff_lists_no_fixes_when_none(self):
        cid = self.to_test()
        self.assertEqual(self.handoff(cid)['fixes'], [])

    def test_task_add_event_carries_the_fix_object_and_other_task_events_do_not(self):
        cid = self.to_test()
        self.add_fix(cid, 'test')
        added = [e for e in workflow.load(self.root, cid)['history'] if e['action'] == 'task-add']
        self.assertEqual(len(added), 1)
        self.assertEqual(added[0]['fix'], {'finding': 'F-1: b.txt holds bad', 'eligibility': 'one file, in scope, cause stated, no decision changes', 'pass': 1})
        self.assertEqual(added[0]['task'], 'fix-1')
        plain = self.fix_task('test', 'plain')
        del plain['fix']
        self.ok('task-add', cid, '--file', self.write_json('plain.json', plain))
        last = [e for e in workflow.load(self.root, cid)['history'] if e['action'] == 'task-add'][-1]
        self.assertNotIn('fix', last)

    def test_handoff_fixes_row_per_fix_task_with_pass_phase_finding_status(self):
        cid = self.to_test()
        self.add_fix(cid, 'test')
        rows = self.handoff(cid)['fixes']
        self.assertEqual(rows, [{'task': 'fix-1', 'pass': 1, 'phase': 'test', 'finding': 'F-1: b.txt holds bad', 'status': 'pending'}])
        self.deliver(cid)
        self.ok('task', cid, '--task-id', 'fix-1', '--state', 'done')
        self.assertEqual(self.handoff(cid)['fixes'][0]['status'], 'done')


if __name__ == '__main__':
    unittest.main()
