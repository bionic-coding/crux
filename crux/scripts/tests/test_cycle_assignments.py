"""The `assignment` subcommand: record who is running, and refuse a duplicate start."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle
from cycle_workflow import create, load, mutate, mutate_tracked


class AssignmentCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / 'repo'; self.repo.mkdir()
        (self.repo / 'bionic').mkdir()
        (self.repo / 'bionic/manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\nadr:\n  next_number: 1\n')
        (self.repo / 'bionic/objectives.md').write_text('Mission: useful changes.')
        self.cid = create(self.repo, 'iterate', 'Change', 'Goal', ['src'], ['Works'], 'dev', 'lead')['id']
        self.path = self.repo / 'bionic/cycles' / self.cid / 'cycle.json'

    def run_cli(self, *argv, expect=0):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cycle.main(['--repo-root', str(self.repo), 'assignment', self.cid, *argv])
        self.assertEqual(code, expect, out.getvalue())
        return json.loads(out.getvalue())


class AssignmentStartTests(AssignmentCase):
    def test_record_without_assignments_validates(self):
        self.assertNotIn('assignments', json.loads(self.path.read_text()))
        self.assertEqual(load(self.repo, self.cid)['id'], self.cid)

    def test_start_records_entry_and_second_start_refuses_naming_live_agent(self):
        start = ('--id', 'stream-a', '--state', 'running', '--role', 'dev-lead', '--agent', 'agent-123')
        result = self.run_cli(*start)
        [entry] = result['cycle']['assignments']
        self.assertEqual({k: entry[k] for k in ('id', 'role', 'task', 'agent', 'state', 'attempt', 'ended_at')},
                         {'id': 'stream-a', 'role': 'dev-lead', 'task': None, 'agent': 'agent-123', 'state': 'running', 'attempt': 1, 'ended_at': None})
        self.assertEqual(entry['started_at'], entry['last_seen'])
        self.assertEqual(result['cycle']['history'][-1]['action'], 'assignment')
        before = self.path.read_bytes()
        # An identical replay is a second start: it refuses and writes nothing.
        refusal = self.run_cli(*start, expect=1)
        self.assertFalse(refusal['ok'])
        for needle in ('stream-a is already running', 'role dev-lead', 'agent agent-123', entry['started_at'], 'record it lost with host evidence'):
            self.assertIn(needle, refusal['error'])
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(len(load(self.repo, self.cid)['assignments']), 1)


class AssignmentStateTests(AssignmentCase):
    """Running, finished and lost: which starts refuse and which resume."""
    START = ('--id', 'stream-a', '--state', 'running', '--role', 'dev-lead', '--agent', 'agent-1')

    def entry(self, ident='stream-a'):
        return next(e for e in load(self.repo, self.cid)['assignments'] if e['id'] == ident)

    def test_running_task_holder_refuses_another_id_for_that_task(self):
        mutate(self.repo, self.cid, 'task-add', task={'id': 'unit', 'phase': 'plan', 'description': 'Unit', 'depends_on': [], 'status': 'pending', 'expected_evidence': ['ok']})
        task = 'unit'
        self.run_cli('--id', 'dev-1', '--state', 'running', '--role', 'developer', '--task', task, '--result-path', '/tmp/r1.md')
        refusal = self.run_cli('--id', 'dev-2', '--state', 'running', '--role', 'developer', '--task', task, expect=1)
        for needle in (f'task {task} is held by running assignment dev-1', 'role developer', 'result path /tmp/r1.md', 'dispatch nothing'):
            self.assertIn(needle, refusal['error'])

    def test_finished_resumes_as_next_attempt_and_keeps_previous_in_history(self):
        self.run_cli(*self.START)
        self.run_cli('--id', 'stream-a', '--state', 'finished', '--note', 'final report returned')
        ended = self.entry()
        self.assertEqual((ended['state'], ended['ended_at'] is not None), ('finished', True))
        # An identical repeat writes nothing.
        before = self.path.read_bytes()
        _, changed = mutate_tracked(self.repo, self.cid, 'assignment', id='stream-a', state='finished', note='final report returned')
        self.assertFalse(changed); self.assertEqual(self.path.read_bytes(), before)
        result = self.run_cli('--id', 'stream-a', '--state', 'running', '--role', 'dev-lead', '--agent', 'agent-2')
        resumed = self.entry()
        self.assertEqual((resumed['state'], resumed['attempt'], resumed['agent'], resumed['ended_at']), ('running', 2, 'agent-2', None))
        self.assertEqual(result['cycle']['history'][-1]['previous']['agent'], 'agent-1')
        # The resumed attempt is live again: a further start refuses.
        self.assertIn('agent agent-2', self.run_cli(*self.START, expect=1)['error'])

    def test_lost_requires_note_and_resumes_as_next_attempt(self):
        self.run_cli(*self.START)
        refusal = self.run_cli('--id', 'stream-a', '--state', 'lost', expect=1)
        self.assertIn('requires --note naming the host evidence', refusal['error'])
        self.assertEqual(self.entry()['state'], 'running')
        self.run_cli('--id', 'stream-a', '--state', 'lost', '--note', 'host lists no live handle agent-1')
        self.assertEqual(self.entry()['state'], 'lost')
        _, changed = mutate_tracked(self.repo, self.cid, 'assignment', id='stream-a', state='lost', note='host lists no live handle agent-1')
        self.assertFalse(changed)
        self.assertIn('only a running assignment', self.run_cli('--id', 'stream-a', '--state', 'finished', expect=1)['error'])
        self.run_cli(*self.START)
        self.assertEqual((self.entry()['state'], self.entry()['attempt']), ('running', 2))

    def test_seen_advances_last_seen_sets_agent_and_refuses_when_not_running(self):
        self.run_cli('--id', 'stream-a', '--state', 'running', '--role', 'dev-lead', '--result-path', '/tmp/a.md')
        first = self.entry()['last_seen']
        self.run_cli('--id', 'stream-a', '--seen', '--agent', 'agent-9')
        entry = self.entry()
        self.assertEqual(entry['agent'], 'agent-9'); self.assertGreater(entry['last_seen'], first)
        _, changed = mutate_tracked(self.repo, self.cid, 'assignment', id='stream-a', seen=True)
        self.assertTrue(changed)  # --seen always advances last_seen
        self.run_cli('--id', 'stream-a', '--state', 'finished')
        self.assertIn('running assignment only', self.run_cli('--id', 'stream-a', '--seen', expect=1)['error'])
        self.assertIn('unknown assignment ghost', self.run_cli('--id', 'ghost', '--seen', expect=1)['error'])

    def test_singleton_role_uses_its_role_name_as_id(self):
        refusal = self.run_cli('--id', 'commander-2', '--state', 'running', '--role', 'commander', expect=1)
        self.assertIn('commander is a singleton role', refusal['error'])
        self.run_cli('--id', 'commander', '--state', 'running', '--role', 'commander')
        self.assertIn('commander is already running', self.run_cli('--id', 'commander', '--state', 'running', '--role', 'commander', expect=1)['error'])

    def test_paused_cycle_records_endings_but_starts_nothing(self):
        self.run_cli(*self.START)
        mutate(self.repo, self.cid, 'pause', reason='owner decision')
        self.run_cli('--id', 'stream-a', '--seen')
        self.run_cli('--id', 'stream-a', '--state', 'finished')
        self.assertIn('cycle is paused', self.run_cli('--id', 'stream-b', '--state', 'running', '--role', 'dev-lead', expect=1)['error'])

    def test_handoff_lists_running_assignments_and_resume_steps(self):
        self.run_cli(*self.START)
        self.run_cli('--id', 'dev-1', '--state', 'running', '--role', 'developer')
        self.run_cli('--id', 'dev-1', '--state', 'finished')
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(cycle.main(['--repo-root', str(self.repo), 'handoff', self.cid]), 0)
        report = json.loads(out.getvalue())
        [live] = report['assignments']
        self.assertEqual((live['id'], live['agent'], live['attempt']), ('stream-a', 'agent-1', 1))
        self.assertGreaterEqual(live['elapsed_seconds'], 0)
        steps = ' '.join(report['resume_steps'])
        for needle in ('agent is null', 'role and result path', 'dispatch nothing', 'host evidence', 'same id'):
            self.assertIn(needle, steps)


class ReleaseCycleAssignmentTests(AssignmentCase):
    """A listed release cycle records assignments as bookkeeping; it gains no step, phase or gate."""

    def test_beta_cycle_records_start_seen_and_finish(self):
        self.cid = create(self.repo, 'release', 'Release', 'Outcome', ['bionic/log.md'], ['published'], 'dev-lead', 'dev-lead', release_list='beta')['id']
        self.path = self.repo / 'bionic/cycles' / self.cid / 'cycle.json'
        before = load(self.repo, self.cid)
        self.run_cli('--id', 'lead-prep', '--state', 'running', '--role', 'dev-lead')
        self.assertIn('lead-prep is already running', self.run_cli('--id', 'lead-prep', '--state', 'running', '--role', 'dev-lead', expect=1)['error'])
        self.run_cli('--id', 'lead-prep', '--seen', '--agent', 'agent-9')
        doc = self.run_cli('--id', 'lead-prep', '--state', 'finished')['cycle']
        [entry] = doc['assignments']
        self.assertEqual((entry['state'], entry['agent']), ('finished', 'agent-9'))
        self.assertEqual((doc['phase'], doc['pass'], [t['id'] for t in doc['plan']['tasks']]),
                         (before['phase'], before['pass'], [t['id'] for t in before['plan']['tasks']]))


if __name__ == '__main__':
    unittest.main()
