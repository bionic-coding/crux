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
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cycle_progress import render, view
from _cycle_fixtures import fresh, path_of, put, read, tree


def task(identity, phase, description, **extra):
    return {'id': identity, 'phase': phase, 'description': description, 'depends_on': [], 'status': 'pending',
            'expected_evidence': ['e'], **extra}


class TaskChangeTests(unittest.TestCase):
    """Each change is written to a frozen iterate record as the typed engine would have left it."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = tree(self.temp.name)
        self.cid = put(self.root, fresh('iterate'), 'CYC-0001')
        self.change(lambda raw: raw.update(phase='build'))

    def change(self, edit):
        """Apply one record change, as a write that reached the record would hold it."""
        raw = read(self.root, self.cid); edit(raw)
        path_of(self.root, self.cid).write_text(json.dumps(raw, indent=2, sort_keys=True) + '\n')

    def add(self, row):
        self.change(lambda raw: raw['plan']['tasks'].append(row))

    def set_status(self, identity, status):
        def edit(raw):
            next(t for t in raw['plan']['tasks'] if t['id'] == identity)['status'] = status
        self.change(edit)

    def assert_reader_matches_record(self):
        record = [(t['id'], t['phase'], t['description'], t['status']) for t in read(self.root, self.cid)['plan']['tasks']]
        drawn = view(self.root, self.cid)['cycles'][0]
        self.assertEqual([(t['id'], t['phase'], t['description'], t['status']) for t in drawn['tasks']], record)
        return drawn

    def test_each_mid_cycle_task_change_reaches_the_next_reader_document(self):
        self.assert_reader_matches_record()
        self.add(task('build-more', 'build', 'Build the added unit'))
        self.assertIn('Build the added unit', render(view(self.root, self.cid)))
        self.assert_reader_matches_record()
        self.add(task('handover-1', 'build', 'Hand-over: tools/x.py, Stream R, format bump'))
        self.assert_reader_matches_record()
        self.set_status('build-more', 'active')
        self.assertEqual(next(t for t in self.assert_reader_matches_record()['tasks'] if t['id'] == 'build-more')['status'], 'active')
        self.change(lambda raw: raw.update(phase='verify'))
        self.add(task('fix-1', 'verify', 'Fix finding F-1', fix={'finding': 'F-1: broken', 'eligibility': 'small and in scope'}))
        self.assert_reader_matches_record()
        before = {t['id']: t['status'] for t in self.assert_reader_matches_record()['tasks']}

        def returned(raw):
            # A return: the next pass starts in Build, the event names what stayed unresolved, open tasks reset.
            raw['history'].append({'action': 'return-requested', 'at': raw['updated_at'], 'pass': 1, 'phase': 'verify', 'revision': 2,
                                   'status': 'active', 'assessment': {'improved': 'isolated', 'unresolved': 'one defect',
                                                                      'next_change': 'fix it', 'justification': 'cause found', 'progress': True}})
            raw.update(**{'pass': 2, 'phase': 'build'})
            for t in raw['plan']['tasks']:
                if t['status'] == 'active':
                    t['status'] = 'pending'
        self.change(returned)
        drawn = self.assert_reader_matches_record()
        self.assertEqual((drawn['pass'], drawn['phase'], len(drawn['returns'])), (2, 'build', 1))
        # The case is what it claims: the return reset at least one task the reader showed before it.
        self.assertNotEqual({t['id']: t['status'] for t in drawn['tasks']}, before)


if __name__ == '__main__':
    unittest.main()
