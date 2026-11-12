"""The `assignment` subcommand: record who is running, and refuse a duplicate start."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import subprocess
import cycle
import cycle_execution
from cycle_workflow import create, event, load, locked, mutate, mutate_tracked, save, tree
import test_cycle_slice as fixtures


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

    def close(self, status='completed'):
        record = json.loads(self.path.read_text()); record['status'] = status
        self.path.write_text(json.dumps(record, indent=2) + '\n')

    def test_closed_cycle_records_a_late_finished_and_nothing_else(self):
        self.run_cli(*self.START)
        self.run_cli('--id', 'dev-1', '--state', 'running', '--role', 'developer')
        self.close()
        result = self.run_cli('--id', 'stream-a', '--state', 'finished', '--note', 'late hand-back')
        self.assertEqual((self.entry()['state'], self.entry()['note']), ('finished', 'late hand-back'))
        self.assertEqual(result['cycle']['status'], 'completed')
        for argv in (('--id', 'stream-b', '--state', 'running', '--role', 'developer'), ('--id', 'dev-1', '--seen'),
                     ('--id', 'dev-1', '--state', 'lost', '--note', 'host evidence')):
            self.assertIn('closed cycles cannot', self.run_cli(*argv, expect=1)['error'])
        with self.assertRaisesRegex(Exception, 'closed cycles cannot'):
            mutate(self.repo, self.cid, 'pause', reason='x')
        self.assertEqual(self.entry('dev-1')['state'], 'running')

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



class CheckoutGuardCase(fixtures.SliceBase):
    """IDR one-editor-per-checkout revision 3: at most one editing attempt holds the main checkout.

    The fixture is a quick-fix cycle in Build with the pending task build-it. Every refusal test pairs with a
    positive control on the same fixture, and every refusal is asserted by its code and its written-nothing record."""

    def add_build(self, ident, **extra):
        mutate(self.repo, self.cid, 'task-add', task={'id': ident, 'phase': 'build', 'description': f'work on {ident}',
                                                      'depends_on': [], 'status': 'pending', 'expected_evidence': ['commit'], **extra})

    def edit(self, function):
        with locked(self.repo) as (cfg, _):
            doc = load(self.repo, self.cid); function(doc); event(doc, 'guard-fixture'); save(cfg, doc)

    def request(self, task, role, op_id, host='claude-code', **extra):
        return {'op': 'prepare-dispatch', 'op_id': op_id, 'task_id': task, 'role': role, 'host': host,
                'assignment_text': fixtures.TEXT, **extra}

    def reserve(self, task, role, op_id, host='claude-code', attach=True, **extra):
        """Reserve an attempt; in background mode, bind a handle as the host would return one."""
        prepared = self.ok(self.request(task, role, op_id, host, mode='background', **extra))
        if attach:
            self.ok({'op': 'attach-execution', 'op_id': op_id + '-attach', 'assignment': prepared['assignment'],
                     'attempt': prepared['attempt'], 'handle': f'handle-{op_id}'})
        return prepared

    def deliver(self, prepared, outcome, op_id, commits=(), **extra):
        self.write_result(prepared)
        return self.ok({'op': 'deliver', 'op_id': op_id, 'assignment': prepared['assignment'], 'attempt': prepared['attempt'],
                        'outcome': outcome, 'commits': list(commits), **extra})

    def lose(self, prepared, op_id):
        return self.ok({'op': 'mark-lost', 'op_id': op_id, 'assignment': prepared['assignment'], 'attempt': prepared['attempt'],
                        'evidence': {'kind': 'terminal-status', 'detail': 'completed'}, 'note': 'Offline fixture affirmative host termination.'})

    def check(self, prepared, op_id, checkout=None, **extra):
        return self.ok({'op': 'execution-check', 'op_id': op_id, 'assignment': prepared['assignment'],
                        'attempt': prepared['attempt'], **({'checkout': str(checkout)} if checkout else {}), **extra})

    def inspect_offers(self):
        """The prepare-dispatch requests inspect offers, by task id."""
        code, response = self.op({'op': 'inspect'})
        self.assertEqual(code, 0, response)
        return {a['request']['task_id']: a['request'] for a in response['actions']
                if 'request' in a and a['request']['op'] == 'prepare-dispatch'}

    def worktree(self, name, start=None):
        directory = tempfile.TemporaryDirectory(prefix=f'crux-guard-{name}-'); self.addCleanup(directory.cleanup)
        path = Path(directory.name).resolve() / 'checkout'
        self.git('worktree', 'add', '-q', '-b', name, str(path), start or self.base)
        self.addCleanup(lambda: subprocess.run(['git', '-C', str(self.repo), 'worktree', 'remove', '--force', str(path)], capture_output=True))
        return path

    def unit_commit(self, prepared, checkout, name, body, op_id):
        """Act as an isolated developer: prove the clean start, stage, checkpoint and commit under the unit's trailer."""
        run = lambda *args: subprocess.run(['git', '-C', str(checkout), *args], check=True, capture_output=True, text=True).stdout.strip()
        self.check(prepared, op_id + '-clean', checkout)
        (checkout / name).write_text(body)
        run('add', name)
        self.check(prepared, op_id + '-staged', checkout, edited_paths=[name])
        run('commit', '-q', '-m', f"Unit work\n\nCycle-Task: {prepared['task']}")
        return run('rev-parse', 'HEAD')

    def main_commit(self, name, body, task, *, op_prepared=None, op_id=None):
        """Commit source on the main checkout under a task trailer; checkpoint it first when an attempt is given."""
        (self.repo / name).write_text(body)
        self.git('add', name)
        if op_prepared is not None:
            self.check(op_prepared, op_id + '-staged', edited_paths=[name])
        self.git('commit', '-q', '-m', f'Work in progress\n\nCycle-Task: {task}')
        return self.git('rev-parse', 'HEAD')

    def assert_checkout_refusal(self, response, holder, role):
        [error] = response['errors']
        self.assertEqual(error['code'], 'checkout-has-open-editing-attempt')
        self.assertEqual(error['observed'], [{'assignment': holder['assignment'], 'attempt': holder['attempt'],
                                              'task': holder['task'], 'role': role}])
        routes = [(r['request']['op'], r['request'].get('assignment'), r['request'].get('attempt')) for r in error['recovery']]
        self.assertEqual(routes, [('inspect', None, None), ('deliver', holder['assignment'], holder['attempt']),
                                  ('mark-lost', holder['assignment'], holder['attempt'])])
        return error


class CheckoutGuardTests(CheckoutGuardCase):
    def test_second_main_checkout_dev_lead_refuses_naming_the_first(self):
        self.add_build('build-two')
        holder = self.reserve('build-it', 'dev-lead', 'guard-first-1')
        error = self.assert_checkout_refusal(self.refused(self.request('build-two', 'dev-lead', 'guard-second-2'),
                                                          'checkout-has-open-editing-attempt'), holder, 'dev-lead')
        # The developer alternative is a note only: it carries no request the commander could submit.
        self.assertIn('as a developer', error['note'])
        self.assertIn('per-call isolation', error['note'])
        self.assertNotIn('request', error['note'])
        self.assertNotIn('developer', [r['request'].get('role') for r in error['recovery']])
        self.assertIn('wait for it to deliver or be marked lost', error['problem'])

    def test_single_dev_lead_attempt_is_admitted(self):
        # Positive control: with the open set empty, the same dev-lead reservation is admitted.
        self.add_build('build-two')
        prepared = self.reserve('build-two', 'dev-lead', 'guard-single-1')
        self.assertEqual((prepared['task'], prepared['attempt']), ('build-two', 1))
        self.assertFalse(prepared['invocation']['isolation']['worktree'])

    def test_request_without_role_on_a_build_task_meets_the_dev_lead_half(self):
        # A request that names no role selects the dev-lead for a Build task, so the guard evaluates it before selection.
        self.add_build('build-two')
        self.reserve('build-it', 'dev-lead', 'guard-norole-1')
        request = {k: v for k, v in self.request('build-two', 'dev-lead', 'guard-norole-2').items() if k != 'role'}
        self.refused(request, 'checkout-has-open-editing-attempt')

    def test_codex_developer_beside_its_dev_lead_refuses_and_claude_code_developer_isolates(self):
        self.add_build('unit-a')
        lead = self.reserve('build-it', 'dev-lead', 'guard-lead-1')
        response = self.refused(self.request('unit-a', 'developer', 'guard-codex-dev-2', host='codex'),
                                'checkout-has-open-editing-attempt')
        error = self.assert_checkout_refusal(response, lead, 'dev-lead')
        self.assertNotIn('note', error)
        # Positive control: the same developer reservation on claude-code isolates and is admitted beside its dev-lead.
        prepared = self.ok(self.request('unit-a', 'developer', 'guard-claude-dev-3'))
        self.assertTrue(prepared['invocation']['isolation']['worktree'])
        self.assertEqual(prepared['invocation']['parameters']['isolation'], 'worktree')

    def test_non_editing_role_and_release_step_are_never_refused(self):
        self.add_build('build-two')
        self.reserve('build-it', 'dev-lead', 'guard-nonedit-1')
        # A reviewer on a Build task is no editing attempt.
        self.ok(self.request('build-two', 'reviewer', 'guard-nonedit-2', host='codex'))
        release = create(self.repo, 'release', 'Release', 'Outcome', ['bionic/log.md'], ['published'], 'dev-lead', 'dev-lead', release_list='beta')['id']
        first = self.ok({'op': 'prepare-dispatch', 'op_id': 'guard-release-1', 'task_id': 'prep', 'role': 'dev-lead', 'host': 'codex'}, cid=release)
        self.assertEqual(first['task'], 'prep')
        doc = load(self.repo, release)
        self.assertEqual([t['phase'] for t in doc['plan']['tasks']][0], 'release')

    def test_mark_lost_releases_the_checkout(self):
        self.add_build('build-two')
        holder = self.reserve('build-it', 'dev-lead', 'guard-lost-1')
        # Before mark-lost the guard refuses.
        self.refused(self.request('build-two', 'dev-lead', 'guard-lost-2'), 'checkout-has-open-editing-attempt')
        self.lose(holder, 'guard-lost-3')
        self.assertEqual(self.reserve('build-two', 'dev-lead', 'guard-lost-4')['task'], 'build-two')

    def test_replayed_op_id_returns_its_recorded_result_while_the_guard_refuses_new_work(self):
        self.add_build('build-two')
        first = self.reserve('build-it', 'dev-lead', 'guard-replay-1', attach=False)
        self.refused(self.request('build-two', 'dev-lead', 'guard-replay-2'), 'checkout-has-open-editing-attempt')
        replay = self.ok(self.request('build-it', 'dev-lead', 'guard-replay-1', mode='background'))
        self.assertTrue(replay['replayed'])
        self.assertEqual((replay['assignment'], replay['attempt']), (first['assignment'], first['attempt']))

    def test_inspect_offers_no_second_build_dispatch_while_a_dev_lead_is_open(self):
        self.add_build('build-two')
        lead = self.reserve('build-it', 'dev-lead', 'guard-offer-1')
        self.assertEqual(self.inspect_offers(), {})
        # Positive control: after the dev-lead delivers, inspect offers the other Build task, naming role dev-lead.
        self.deliver(lead, 'blocked', 'guard-offer-2')
        offers = self.inspect_offers()
        self.assertEqual(offers['build-two'], {'op': 'prepare-dispatch', 'task_id': 'build-two', 'role': 'dev-lead'})
        self.assertEqual(offers['build-it']['role'], 'dev-lead')

    def test_second_fix_task_dev_lead_waits_for_the_first(self):
        def to_review(doc):
            doc['phase'] = 'review'
            for task in doc['plan']['tasks']:
                task['status'] = 'done'
            for ident, finding in (('fix-one', 'F1'), ('fix-two', 'F2')):
                doc['plan']['tasks'].append({'id': ident, 'phase': 'review', 'description': f'answer {finding}', 'depends_on': [],
                                             'status': 'pending', 'expected_evidence': ['commit'],
                                             'fix': {'finding': finding, 'eligibility': 'small and in scope', 'pass': 1}})
        self.edit(to_review)
        first = self.reserve('fix-one', 'dev-lead', 'guard-fix-1')
        self.assert_checkout_refusal(self.refused(self.request('fix-two', 'dev-lead', 'guard-fix-2'),
                                                  'checkout-has-open-editing-attempt'), first, 'dev-lead')
        self.assertNotIn('fix-two', self.inspect_offers())
        # Positive control: once the first delivers, the second fix task's dev-lead is admitted.
        self.deliver(first, 'blocked', 'guard-fix-3')
        self.assertEqual(self.reserve('fix-two', 'dev-lead', 'guard-fix-4')['task'], 'fix-two')

    def test_legacy_running_start_meets_the_same_open_set(self):
        self.add_build('build-two')
        def start(ident, task, expect=0):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = cycle.main(['--repo-root', str(self.repo), 'assignment', self.cid, '--id', ident, '--state', 'running',
                                   '--role', 'dev-lead', '--task', task])
            self.assertEqual(code, expect, out.getvalue())
            return json.loads(out.getvalue())
        # Positive control: with no open editing attempt, the version-3 low-level start is admitted.
        start('legacy-lead', 'build-two')
        mutate(self.repo, self.cid, 'assignment', id='legacy-lead', state='finished', note='final report returned')
        self.reserve('build-it', 'dev-lead', 'guard-legacy-1')
        before = self.record_path().read_bytes()
        refusal = start('legacy-lead', 'build-two', expect=1)
        self.assertTrue(refusal['error'].startswith('checkout-has-open-editing-attempt:'), refusal['error'])
        self.assertIn('dev-lead attempt build-it/1 on task build-it', refusal['error'])
        self.assertEqual(self.record_path().read_bytes(), before)

    def test_legacy_entry_without_host_holds_the_checkout_for_typed_dispatch(self):
        # A low-level entry records no host, so it counts as targeting the main checkout.
        self.add_build('build-two')
        mutate(self.repo, self.cid, 'assignment', id='legacy-dev', state='running', role='developer', task='build-two')
        response = self.refused(self.request('build-it', 'dev-lead', 'guard-legacy-host-1'), 'checkout-has-open-editing-attempt')
        self.assertEqual(response['errors'][0]['observed'],
                         [{'assignment': 'legacy-dev', 'attempt': 1, 'task': 'build-two', 'role': 'developer'}])


class UnitWindowTests(CheckoutGuardCase):
    """Approach 5: a coordinating dev-lead holds the main checkout while its units run as developers in worktrees."""

    def streams(self, *units):
        for unit in units:
            self.add_build(unit)
        self.edit(lambda doc: doc['plan'].update(streams=[{'id': 'a', 'paths': ['src/a.py'], 'independent': True},
                                                          {'id': 'b', 'paths': ['src/b.py'], 'independent': True}]))

    def merge(self, sha, task):
        self.git('merge', '--no-ff', '-m', f'Integrate {sha[:8]}\n\nCycle-Task: {task}', sha)
        return self.git('rev-parse', 'HEAD')

    def test_two_independent_streams_isolate_and_the_coordinator_admits_both_merges(self):
        self.streams('unit-a', 'unit-b')
        lead = self.reserve('build-it', 'dev-lead', 'stream-lead-1')
        units = {}
        for unit, name in (('unit-a', 'src/a.py'), ('unit-b', 'src/b.py')):
            prepared = self.reserve(unit, 'developer', f'stream-{unit}-1', integration_owner='dev-lead')
            self.assertTrue(prepared['invocation']['isolation']['worktree'])
            units[unit] = (prepared, name)
        commits = {}
        for unit, (prepared, name) in units.items():
            checkout = self.worktree(unit)
            commits[unit] = self.unit_commit(prepared, checkout, name, f'{unit} = 2\n', f'stream-{unit}-work')
            self.deliver(prepared, 'done', f'stream-{unit}-deliver', commits=[commits[unit]])
        for unit in units:
            self.ok({'op': 'child-link', 'op_id': f'stream-link-{unit}', 'assignment': lead['assignment'], 'attempt': 1, 'child_task': unit})
        self.assertEqual(next(t for t in load(self.repo, self.cid)['plan']['tasks'] if t['id'] == 'build-it')['integrates'], ['unit-a', 'unit-b'])
        merges = [self.merge(commits[unit], 'build-it') for unit in units]
        proof = self.check(lead, 'stream-lead-proof')['execution']
        kinds = {row['sha']: row['kind'] for row in proof['commits']}
        self.assertEqual([kinds[m] for m in merges], ['integrated-task-merge', 'integrated-task-merge'])
        self.assertEqual({kinds[commits[u]] for u in units}, {'integrated-task-source'})

    def test_uncommitted_coordinator_edit_refuses_the_next_unit(self):
        self.streams('unit-a', 'unit-b')
        self.reserve('build-it', 'dev-lead', 'window-lead-1')
        self.reserve('unit-a', 'developer', 'window-unit-a-1', integration_owner='dev-lead')
        (self.repo / 'src/a.py').write_text('answer = 5\n')
        self.refused(self.request('unit-b', 'developer', 'window-unit-b-1', mode='background'), 'execution-dirty-owned-paths')
        # Positive control: with the main checkout clean in scope, the next unit is admitted.
        self.git('checkout', '--', 'src/a.py')
        self.assertTrue(self.reserve('unit-b', 'developer', 'window-unit-b-2')['invocation']['isolation']['worktree'])

    def orphan(self):
        """A coordinator marked lost while its unit is blocked."""
        self.streams('unit-a')
        lead = self.reserve('build-it', 'dev-lead', 'orphan-lead-1')
        unit = self.reserve('unit-a', 'developer', 'orphan-unit-1', integration_owner='dev-lead')
        self.deliver(unit, 'blocked', 'orphan-unit-2')
        return lead, unit

    def test_orphaned_unit_is_offered_only_through_its_coordinator(self):
        lead, _ = self.orphan()
        self.lose(lead, 'orphan-lead-2')
        offers = self.inspect_offers()
        self.assertEqual(offers['build-it'], {'op': 'prepare-dispatch', 'task_id': 'build-it', 'role': 'dev-lead'})
        self.assertNotIn('unit-a', offers)
        response = self.refused(self.request('unit-a', 'dev-lead', 'orphan-unit-lead-3'), 'unit-task-needs-coordinator')
        self.assertEqual(response['errors'][0]['recovery'][0]['request'], {'op': 'inspect'})
        # Positive control: the coordinator's next attempt is admitted, and its developer request for the unit isolates.
        self.reserve('build-it', 'dev-lead', 'orphan-lead-3', assignment=lead['assignment'])
        retry = self.reserve('unit-a', 'developer', 'orphan-unit-4', assignment='unit-a', integration_owner='dev-lead')
        self.assertEqual((retry['attempt'], retry['invocation']['isolation']['worktree']), (2, True))

    def test_lost_coordinator_checkpointed_commit_resumes_and_an_unchecked_commit_refuses(self):
        lead, _ = self.orphan()
        self.check(lead, 'orphan-clean-3')
        sha = self.main_commit('src/a.py', 'answer = 7\n', 'build-it', op_prepared=lead, op_id='orphan-commit-4')
        self.check(lead, 'orphan-commit-proof-5')
        self.lose(lead, 'orphan-lead-6')
        resumed = self.reserve('build-it', 'dev-lead', 'orphan-lead-7', assignment=lead['assignment'])
        row = next(row for row in resumed['execution']['commits'] if row['sha'] == sha)
        self.assertEqual(row['kind'], 'same-task-resume')

    def test_lost_coordinator_commit_without_checkpoint_refuses_foreign_source(self):
        lead, _ = self.orphan()
        self.main_commit('src/a.py', 'answer = 8\n', 'build-it')
        self.lose(lead, 'orphan-lead-3')
        self.refused(self.request('build-it', 'dev-lead', 'orphan-lead-4', mode='background', assignment=lead['assignment']),
                     'execution-foreign-source')

    def test_blocked_unit_retry_meets_only_bookkeeping_and_refuses_after_foreign_source(self):
        self.streams('unit-a', 'unit-b')
        unit = self.reserve('unit-a', 'developer', 'order-unit-1', integration_owner='dev-lead')
        self.deliver(unit, 'blocked', 'order-unit-2')
        record = self.repo / 'bionic/cycles' / self.cid / 'notes.md'
        record.write_text('Retained record evidence.\n')
        self.git('add', '-f', str(record)); self.git('commit', '-q', '-m', 'bookkeeping only')
        retry = self.request('unit-a', 'developer', 'order-unit-3', mode='background', assignment='unit-a', integration_owner='dev-lead')
        # Another task's source commit on the main checkout after the unit's base: the documented limit.
        self.main_commit('src/b.py', 'b = 1\n', 'unit-b')
        self.refused(retry, 'execution-foreign-source')
        # Positive control: with only bookkeeping after the base, the same retry is admitted.
        self.git('reset', '-q', '--hard', 'HEAD~1')
        self.assertEqual(self.ok(retry)['attempt'], 2)

    def test_worktree_retry_merges_only_the_done_attempt(self):
        self.streams('unit-a', 'unit-b')
        lead = self.reserve('build-it', 'dev-lead', 'retry-lead-1')
        first = self.reserve('unit-a', 'developer', 'retry-unit-a-1', integration_owner='dev-lead')
        draft = self.unit_commit(first, self.worktree('unit-a-1'), 'src/a.py', 'draft = 1\n', 'retry-unit-a-w1')
        self.deliver(first, 'blocked', 'retry-unit-a-2', commits=[draft])
        second = self.reserve('unit-a', 'developer', 'retry-unit-a-3', assignment='unit-a', integration_owner='dev-lead')
        self.assertEqual((second['attempt'], second['base']), (2, self.base))
        done = self.unit_commit(second, self.worktree('unit-a-2'), 'src/a.py', 'draft = 1\n', 'retry-unit-a-w2')
        self.deliver(second, 'done', 'retry-unit-a-4', commits=[done])
        other = self.reserve('unit-b', 'developer', 'retry-unit-b-1', integration_owner='dev-lead')
        other_sha = self.unit_commit(other, self.worktree('unit-b'), 'src/b.py', 'b = 2\n', 'retry-unit-b-w')
        self.deliver(other, 'done', 'retry-unit-b-2', commits=[other_sha])
        for unit in ('unit-a', 'unit-b'):
            self.ok({'op': 'child-link', 'op_id': f'retry-link-{unit}', 'assignment': lead['assignment'], 'attempt': 1, 'child_task': unit})
        merges = [self.merge(done, 'build-it'), self.merge(other_sha, 'build-it')]
        proof = self.check(lead, 'retry-lead-proof')['execution']
        kinds = {row['sha']: row['kind'] for row in proof['commits']}
        self.assertEqual([kinds[m] for m in merges], ['integrated-task-merge', 'integrated-task-merge'])
        self.assertNotIn(draft, kinds)
        self.assertNotEqual(subprocess.run(['git', '-C', str(self.repo), 'merge-base', '--is-ancestor', draft, 'HEAD']).returncode, 0)


class CommittedWorkInProgressTests(CheckoutGuardCase):
    """Approach 4: a blocked or failed attempt commits its work in progress, and the next attempt admits it."""

    def committed(self, outcome, tag):
        prepared = self.reserve('build-it', 'dev-lead', f'wip-{tag}-1')
        self.check(prepared, f'wip-{tag}-clean')
        sha = self.main_commit('src/a.py', 'answer = 2\n', 'build-it', op_prepared=prepared, op_id=f'wip-{tag}-commit')
        self.check(prepared, f'wip-{tag}-proof')
        self.deliver(prepared, outcome, f'wip-{tag}-deliver', commits=[sha])
        self.assertEqual(load(self.repo, self.cid)['assignments'][0]['delivery']['commits'], [sha])
        resumed = self.reserve('build-it', 'dev-lead', f'wip-{tag}-resume', assignment=prepared['assignment'])
        self.assertEqual(resumed['base'], self.base)
        self.assertEqual(next(row for row in resumed['execution']['commits'] if row['sha'] == sha)['kind'], 'same-task-resume')

    def test_blocked_delivery_with_committed_work_is_admitted_by_the_next_attempt(self):
        self.committed('blocked', 'blocked')

    def test_failed_delivery_with_committed_work_is_admitted_by_the_next_attempt(self):
        self.committed('failed', 'failed')

    def test_staged_uncommitted_work_refuses_the_next_attempt(self):
        # Positive control for the two cases above: the same bytes left staged and uncommitted refuse.
        prepared = self.reserve('build-it', 'dev-lead', 'wip-staged-1')
        self.check(prepared, 'wip-staged-clean')
        (self.repo / 'src/a.py').write_text('answer = 2\n'); self.git('add', 'src/a.py')
        self.deliver(prepared, 'blocked', 'wip-staged-deliver')
        self.refused(self.request('build-it', 'dev-lead', 'wip-staged-resume', mode='background', assignment=prepared['assignment']),
                     'execution-dirty-owned-paths')


if __name__ == '__main__':
    unittest.main()
