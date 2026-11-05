"""The cycle's test runs: executions in its window, reused receipts outside it, and the minutes (CYC-0093 item 29f)."""
import contextlib
import io
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
import sys
import tempfile
import unittest
import unittest.mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cycle
import cycle_progress
from cycle_summary import test_runs, test_run_lines
from cycle_workflow import create, load, mutate
from test_cycle_ops_finish import FinishBase
from test_cycle_slice import shared_interpreter_env


def write_receipt(store, number, check_id, started, seconds, status='passed', reason=None):
    """A minimal receipt file carrying the fields the metrics read."""
    eid = 'TE-' + f'{number:032x}'
    (store / f'{eid}.json').write_text(json.dumps({
        'id': eid, 'declaration': {'check_id': check_id}, 'started_at': started, 'finished_at': started + seconds,
        'seconds': seconds, 'status': status, 'reason': reason}))
    return eid


class TestRunsBase(FinishBase):
    def setUp(self):
        super().setUp()
        self.store_dir = tempfile.TemporaryDirectory(); self.addCleanup(self.store_dir.cleanup)
        self.store = Path(self.store_dir.name)
        patch = unittest.mock.patch.dict(os.environ, {'CRUX_TEST_EVIDENCE_STORE': str(self.store)})
        patch.start(); self.addCleanup(patch.stop)

    def release(self):
        doc = create(self.repo, 'release', 'Ship', 'Release it', ['src'], ['shipped'], 'builder', 'tester', release_list='official')
        self.v3(doc['id'])
        return doc['id']

    def finish_tasks(self, cid):
        shas = []
        for task in load(self.repo, cid)['plan']['tasks']:
            shas.append(self.commit_file(f'src/{task["id"]}.txt', task['id'], f'step {task["id"]}'))
            mutate(self.repo, cid, 'task', task_id=task['id'], state='done', commits=[shas[-1]])
        return shas

    def seed(self, cid):
        """In the window: core twice (one failed with a retry reason), tools interrupted. Outside it: one staged receipt the record attaches."""
        begin = datetime.fromisoformat(load(self.repo, cid)['created_at']).timestamp()
        ids = {
            'core_pass': write_receipt(self.store, 1, 'core', begin, 120.0, 'passed', 'missing'),
            'core_retry': write_receipt(self.store, 2, 'core', begin, 60.0, 'failed', 'harness: dependency resolution'),
            'tools_int': write_receipt(self.store, 3, 'tools', begin, 30.0, 'interrupted', 'engine received signal 15'),
            'staged_old': write_receipt(self.store, 4, 'staged:py3.13:health', begin - 3600, 900.0, 'passed', 'missing'),
        }
        raw = json.loads(self.record_path(cid).read_text())
        raw['evidence'] = [{'check_id': 'staged:py3.13:health', 'evidence_id': ids['staged_old'], 'pass': 1, 'use': 'reused', 'declaration_sha256': '0' * 64},
                           {'check_id': 'core', 'evidence_id': ids['core_pass'], 'pass': 1, 'use': 'executed', 'declaration_sha256': '0' * 64}]
        self.record_path(cid).write_text(json.dumps(raw))
        return ids

    def status_text(self, cid):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(cycle.main(['--repo-root', str(self.repo), 'status', cid]), 0)
        return out.getvalue()


SUMMARY = '3 executed (1 with a retry reason), 1 reused, 3.5 test minutes'


class TestRunsTests(TestRunsBase):
    def test_counts_by_check_receipts_retry_subtotal_and_minutes(self):
        cid = self.release()
        ids = self.seed(cid)
        runs = test_runs(self.repo, load(self.repo, cid), datetime.now().timestamp() + 5)
        self.assertEqual((runs['executions'], runs['with_retry_reason'], runs['minutes']), (3, 1, 3.5))
        core, tools = runs['executed']
        self.assertEqual(core, {'check_id': 'core', 'runs': 2, 'receipts': sorted([ids['core_pass'], ids['core_retry']]), 'with_retry_reason': 1, 'minutes': 3.0})
        self.assertEqual((tools['check_id'], tools['receipts'], tools['with_retry_reason']), ('tools', [ids['tools_int']], 0))
        self.assertEqual(runs['reused'], [{'check_id': 'staged:py3.13:health', 'receipts': [ids['staged_old']]}])

    def test_finish_writes_the_counts_into_the_completion_record(self):
        cid = self.release()
        ids = self.seed(cid)
        self.finish_tasks(cid)
        self.ok({'op': 'finish', 'op_id': 'finish-m-1', 'expect_revision': self.revision(cid)}, cid=cid)
        recorded = load(self.repo, cid)['completion']['test_runs']
        self.assertEqual((recorded['executions'], recorded['with_retry_reason'], recorded['minutes']), (3, 1, 3.5))
        self.assertEqual(recorded['reused'], [{'check_id': 'staged:py3.13:health', 'receipts': [ids['staged_old']]}])
        self.assertEqual([row['check_id'] for row in recorded['executed']], ['core', 'tools'])

    def test_inspect_and_status_show_the_same_counts(self):
        cid = self.release()
        self.seed(cid)
        seen = self.ok({'op': 'inspect'}, cid=cid)
        self.assertEqual((seen['test_runs']['executions'], seen['test_runs']['with_retry_reason'], seen['test_runs']['minutes']), (3, 1, 3.5))
        text = self.status_text(cid)
        for line in test_run_lines(seen['test_runs']):
            self.assertIn(line, text)
        self.assertIn(SUMMARY, text)

    def test_a_closed_cycle_status_reads_its_completion_record(self):
        cid = self.release()
        self.seed(cid)
        self.finish_tasks(cid)
        self.ok({'op': 'finish', 'op_id': 'finish-m-2', 'expect_revision': self.revision(cid)}, cid=cid)
        for path in self.store.glob('TE-*.json'):
            path.unlink()
        self.assertIn(SUMMARY, self.status_text(cid))

    def test_no_store_reports_no_runs(self):
        cid = self.release()
        with unittest.mock.patch.dict(os.environ, {'CRUX_TEST_EVIDENCE_STORE': str(self.store / 'absent')}):
            self.assertIsNone(test_runs(self.repo, load(self.repo, cid), 0))
            self.assertEqual(test_run_lines(None), [])


class ChildInterpreterTests(unittest.TestCase):
    def test_a_child_on_sys_executable_resolves_the_packages_the_test_resolved(self):
        with tempfile.TemporaryDirectory() as overlay:
            Path(overlay, 'overlay_only_dependency.py').write_text('VALUE = 7\n')
            probe = [sys.executable, '-c', 'import overlay_only_dependency; print(overlay_only_dependency.VALUE)']
            with unittest.mock.patch.object(sys, 'path', [overlay, *sys.path]), unittest.mock.patch.dict(os.environ, {'PYTHONPATH': ''}):
                bare = subprocess.run(probe, capture_output=True, text=True, env=dict(os.environ))
                shared = subprocess.run(probe, capture_output=True, text=True, env=shared_interpreter_env())
        self.assertNotEqual(bare.returncode, 0, 'the control: a child on the ambient environment must not see the overlay')
        self.assertIn("No module named 'overlay_only_dependency'", bare.stderr)
        self.assertEqual((shared.returncode, shared.stdout.strip()), (0, '7'), shared.stderr)


class WaitsTests(unittest.TestCase):
    def test_a_withdrawn_unapproved_decision_is_not_a_wait(self):
        decisions = [{'name': 'a', 'kind': 'idr', 'approval': None}, {'name': 'b', 'kind': 'idr', 'approval': None}]
        self.assertEqual(cycle_progress.current_waits(decisions), ['a', 'b'])
        self.assertEqual(cycle_progress.current_waits(decisions, {'a'}), ['b'])


if __name__ == '__main__':
    unittest.main()
