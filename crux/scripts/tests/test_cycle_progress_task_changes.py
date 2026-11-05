"""The cycle-progress reader draws the record's tasks as they stand at each read.

A cycle's tasks change mid-cycle through task-add, a fix task, a hand-over, a return's reset and a
task status change. After each write the reader's next document lists exactly the record's tasks,
so the reader holds no state that can drift from the record. The dashboards draw this document; a
dashboard that shows an older task list got an older document, never a stale reading of this one."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cycle_workflow import create, mutate
from cycle_progress import render, view


def task(identity, phase, description, **extra):
    return {'id': identity, 'phase': phase, 'description': description, 'depends_on': [], 'status': 'pending',
            'expected_evidence': ['e'], **extra}


class TaskChangeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'bionic').mkdir(); (self.root / 'src').mkdir()
        (self.root / 'bionic/manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\n')
        self.cid = create(self.root, 'iterate', 'Sync', 'Goal', ['src'], ['Works'], 'builder', 'tester')['id']
        self.put_phase('build')

    def path(self):
        return self.root / 'bionic/cycles' / self.cid / 'cycle.json'

    def put_phase(self, phase):
        """Write the phase directly, as a record that reached it would hold it."""
        raw = json.loads(self.path().read_text()); raw['phase'] = phase
        self.path().write_text(json.dumps(raw, indent=2, sort_keys=True) + '\n')

    def assert_reader_matches_record(self):
        record = [(t['id'], t['phase'], t['description'], t['status']) for t in json.loads(self.path().read_text())['plan']['tasks']]
        drawn = view(self.root, self.cid)['cycles'][0]
        self.assertEqual([(t['id'], t['phase'], t['description'], t['status']) for t in drawn['tasks']], record)
        return drawn

    def test_each_mid_cycle_task_change_reaches_the_next_reader_document(self):
        self.assert_reader_matches_record()
        mutate(self.root, self.cid, 'task-add', task=task('build-more', 'build', 'Build the added unit'))
        self.assertIn('Build the added unit', render(view(self.root, self.cid)))
        self.assert_reader_matches_record()
        mutate(self.root, self.cid, 'task-add', task=task('handover-1', 'build', 'Hand-over: tools/x.py, Stream R, format bump'))
        self.assert_reader_matches_record()
        mutate(self.root, self.cid, 'task', task_id='build-more', state='active')
        self.assertEqual(next(t for t in self.assert_reader_matches_record()['tasks'] if t['id'] == 'build-more')['status'], 'active')
        self.put_phase('verify')
        mutate(self.root, self.cid, 'task-add', task=task('fix-1', 'verify', 'Fix finding F-1', fix={'finding': 'F-1: broken', 'eligibility': 'small and in scope'}))
        self.assert_reader_matches_record()
        before = {t['id']: t['status'] for t in self.assert_reader_matches_record()['tasks']}
        mutate(self.root, self.cid, 'return', improved='isolated', unresolved='one defect', next_change='fix it',
               justification='cause found', progress=True)
        drawn = self.assert_reader_matches_record()
        self.assertEqual((drawn['pass'], drawn['phase'], len(drawn['returns'])), (2, 'build', 1))
        # The case is what it claims: the return reset at least one task the reader showed before it.
        self.assertNotEqual({t['id']: t['status'] for t in drawn['tasks']}, before)


if __name__ == '__main__':
    unittest.main()
