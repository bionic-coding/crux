"""Attempt lifecycle of the typed cycle operations: mark-lost, per-attempt inspect observations,
transactions, and the recovery requests every refusal returns.

Reuses `SliceBase`; the host adapters decide what counts as affirmative evidence, so these tests
drive `cycle_hosts.loss_evidence` through the engine."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle
import cycle_hosts
import cycle_ops
from cycle_workflow import load, mutate
from test_cycle_slice import SliceBase, TEXT

SCRIPTS = Path(__file__).resolve().parents[1]
REFUSAL = {'kind': 'dispatch-refusal', 'detail': 'permission-denied'}
TERMINAL = {'kind': 'terminal-status', 'detail': 'killed'}
OWNER = {'kind': 'owner-confirmation', 'detail': 'the owner confirmed the dispatching session has ended'}

FILLS = {'op_id': 'filled-001', 'assignment_text': 'text', 'role': 'developer', 'host': 'claude-code', 'handle': 'h', 'outcome': 'done',
         'lessons': ['l'], 'remaining': ['none'], 'quote': 'q', 'conversation': 'c', 'date': '2026-10-30',
         'evidence': OWNER, 'note': 'the owner confirmed the session ended'}


class OpsBase(SliceBase):
    """Shared helpers for the lifecycle and delivery tests."""

    def lost(self, op_id='lost-0001', attempt=1, assignment='build-it', evidence=REFUSAL, note='host evidence quoted', **extra):
        return {'op': 'mark-lost', 'op_id': op_id, 'assignment': assignment, 'attempt': attempt, 'evidence': evidence, 'note': note, **extra}

    def deliver_request(self, op_id='deliver-01', attempt=1, assignment='build-it', outcome='done', **extra):
        return {'op': 'deliver', 'op_id': op_id, 'assignment': assignment, 'attempt': attempt, 'outcome': outcome, **extra}

    def doc(self):
        return load(self.repo, self.cid)

    def add_task(self, task_id):
        mutate(self.repo, self.cid, 'task-add', task={'id': task_id, 'phase': 'build', 'description': f'do {task_id}', 'depends_on': [],
                                                    'status': 'pending', 'expected_evidence': ['commit']})

    def commit_file(self, name, body, task='build-it', trailer=True):
        (self.repo / name).write_text(body)
        self.git('add', name)
        self.git('commit', '-q', '-m', f'change {name}' + (f'\n\nCycle-Task: {task}' if trailer else ''))
        return self.git('rev-parse', 'HEAD')

    def age(self, hours):
        """Move every attempt's recorded times back, as a record written `hours` ago would hold them."""
        raw = json.loads(self.record_path().read_text())
        then = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        for entry in raw['assignments']:
            entry['started_at'] = entry['last_seen'] = then
        self.record_path().write_text(json.dumps(raw))

    def inspect_attempt(self, index=0):
        return self.ok({'op': 'inspect'})['assignments'][index]

    def assert_validates(self, recoveries, extra_fills=None):
        """Every recovery request validates against the operation schema once its caller_fills are filled."""
        fills = {**FILLS, **(extra_fills or {})}
        checked = 0
        for item in recoveries:
            if 'request' not in item:
                self.assertIn('argv', item); continue
            request = {**item['request'], **{key: fills[key] for key in item['caller_fills']}}
            self.assertEqual(cycle_ops.schema_errors(request), [], item)
            checked += 1
        return checked

    def lowlevel(self, item, **fills):
        """Run a low-level recovery argv in process, appending the flags its caller_fills names."""
        argv = item['argv'][3:]
        for flag in item['caller_fills']:
            argv += [flag, fills[flag]]
        import contextlib, io
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cycle.main(argv)
        self.assertEqual(code, 0, out.getvalue())


class MarkLostTests(OpsBase):
    def test_launch_failure_then_attempt_two_succeeds(self):
        prepared = self.prepare()
        # A timeout or transport error may follow a started child: it is not a listed refusal.
        self.refused(self.lost(evidence={'kind': 'dispatch-refusal', 'detail': 'timeout'}), 'not-affirmative')
        response = self.ok(self.lost())
        self.assertEqual((response['changed'], response['assignment'], response['attempt'], response['status']), (True, 'build-it', 1, 'pending'))
        doc = self.doc()
        entry = doc['assignments'][0]
        self.assertEqual((entry['state'], entry['note']), ('lost', 'host evidence quoted'))
        self.assertTrue(entry['ended_at'])
        self.assertEqual(doc['plan']['tasks'][0]['status'], 'pending')
        last = doc['history'][-1]
        self.assertEqual((last['action'], last['evidence_kind'], last['evidence_detail']), ('mark-lost', 'dispatch-refusal', 'permission-denied'))
        self.assertEqual(last['revision'], doc['revision'])
        again = self.prepare(op_id='prep-0002', assignment='build-it')
        self.assertEqual((again['assignment'], again['attempt'], again['base']), ('build-it', 2, prepared['base']))
        self.assertNotEqual(again['result_path'], prepared['result_path'])
        sha = self.work(again)
        done = self.ok(self.deliver_request(attempt=2, commits=[sha]))
        self.assertEqual(done['status'], 'done')

    def test_running_attempt_with_a_host_terminal_status(self):
        self.prepare(mode='background')
        self.ok({'op': 'attach-execution', 'op_id': 'attach-001', 'assignment': 'build-it', 'attempt': 1, 'handle': 'agent-1'})
        self.refused(self.lost(evidence={'kind': 'terminal-status', 'detail': 'running'}), 'not-affirmative')
        # A refusal of the dispatch call cannot apply once a handle is bound.
        self.refused(self.lost(op_id='lost-0002'), 'not-affirmative')
        self.ok(self.lost(op_id='lost-0003', evidence=TERMINAL))
        self.assertEqual(self.doc()['assignments'][0]['state'], 'lost')

    def test_terminal_status_needs_a_bound_handle(self):
        self.prepare()
        self.refused(self.lost(evidence=TERMINAL), 'not-affirmative')

    def test_evidence_that_establishes_nothing_is_refused(self):
        self.prepare()
        for kind in cycle_hosts.NOT_EVIDENCE:
            with self.subTest(kind=kind):
                response = self.refused(self.lost(op_id=f'lost-{kind}', evidence={'kind': kind, 'detail': 'the wait call reported an error'}),
                                        'not-affirmative')
                self.assertIn(kind, response['errors'][0]['problem'])
                self.assertEqual(response['errors'][0]['recovery'][0]['request'], {'op': 'inspect'})
        self.assertEqual(self.doc()['assignments'][0]['state'], 'reserved')

    def test_unknown_evidence_kind_and_missing_detail(self):
        self.prepare()
        self.refused(self.lost(evidence={'kind': 'a-feeling', 'detail': 'it seems gone'}), 'unknown-evidence-kind')
        self.refused(self.lost(op_id='lost-0002', evidence={'kind': 'owner-confirmation', 'detail': ''}), 'invalid-request')
        self.refused(self.lost(op_id='lost-0005', evidence={'kind': 'owner-confirmation', 'detail': '   '}), 'evidence-detail-missing')
        self.refused({**self.lost(op_id='lost-0003'), 'evidence': {'kind': 'owner-confirmation'}}, 'invalid-request')
        request = self.lost(op_id='lost-0004'); del request['evidence']
        self.refused(request, 'invalid-request')

    def test_listing_absence_and_blocking_return_follow_the_adapter(self):
        self.prepare()
        self.refused(self.lost(evidence={'kind': 'listing-absence', 'detail': 'not in the agent list'}), 'not-affirmative')
        self.refused(self.lost(op_id='lost-0002', evidence={'kind': 'blocking-returned', 'detail': 'returned'}), 'not-affirmative')
        self.ok(self.lost(op_id='lost-0003', evidence=OWNER))

    def test_blocking_return_on_a_handle_less_host(self):
        self.prepare(host='opencode')
        self.ok(self.lost(evidence={'kind': 'blocking-returned', 'detail': 'the foreground dispatch returned without a result'}))

    def test_a_complete_result_is_delivered_not_lost(self):
        prepared = self.prepare()
        self.write_result(prepared)
        response = self.refused(self.lost(evidence=OWNER), 'result-arrived')
        recovery = response['errors'][0]['recovery'][0]
        self.assertEqual(recovery['request'], {'op': 'deliver', 'assignment': 'build-it', 'attempt': 1})
        self.assertEqual(recovery['caller_fills'], ['op_id', 'outcome'])

    def test_an_incomplete_result_does_not_block_loss(self):
        prepared = self.prepare()
        self.write_result(prepared, marker=False)
        self.ok(self.lost(evidence=OWNER))

    def test_already_lost_attempt_reports_its_state_without_a_write(self):
        self.prepare()
        self.ok(self.lost())
        before = self.record_path().read_bytes()
        code, response = self.op(self.lost(op_id='lost-0002', evidence=OWNER))
        self.assertEqual(code, 0, response)
        self.assertEqual((response['changed'], response['replayed'], response['attempt_state']), (False, False, 'lost'))
        self.assertEqual((response['assignment'], response['attempt'], response['note']), ('build-it', 1, 'host evidence quoted'))
        self.assertEqual(self.record_path().read_bytes(), before)

    def test_same_op_id_replays(self):
        self.prepare()
        first = self.ok(self.lost())
        before = self.record_path().read_bytes()
        again = self.ok(self.lost())
        self.assertEqual((again['replayed'], again['changed'], again['revision']), (True, False, first['revision']))
        self.assertEqual(self.record_path().read_bytes(), before)
        self.refused(self.lost(note='another note'), 'op-id-reused')

    def test_an_attempt_that_is_not_current_or_not_open_is_refused(self):
        self.prepare()
        self.ok(self.lost())
        self.prepare(op_id='prep-0002', assignment='build-it')
        self.refused(self.lost(op_id='lost-0002', evidence=OWNER), 'superseded-attempt')
        self.refused(self.lost(op_id='lost-0003', attempt=3, evidence=OWNER), 'superseded-attempt')
        self.refused(self.lost(op_id='lost-0004', assignment='nope', evidence=OWNER), 'unknown-assignment')

    def test_a_delivered_attempt_is_not_lost(self):
        prepared = self.prepare()
        self.write_result(prepared)
        self.ok(self.deliver_request(outcome='failed'))
        self.refused(self.lost(evidence=OWNER), 'attempt-not-open')

    def test_a_low_level_attempt_without_a_host_names_the_low_level_route(self):
        mutate(self.repo, self.cid, 'assignment', id='manual', state='running', role='developer', task='build-it', agent='h')
        response = self.refused(self.lost(assignment='manual', evidence=OWNER), 'attempt-without-host')
        argv = response['errors'][0]['recovery'][0]
        self.assertEqual(argv['argv'][-6:], ['assignment', self.cid, '--id', 'manual', '--state', 'lost'])
        self.assertEqual(argv['caller_fills'], ['--note'])
        self.lowlevel(argv, **{'--note': 'host reported the agent terminated'})
        self.assertEqual(self.doc()['assignments'][0]['state'], 'lost')

    def test_paused_cycle_accepts_and_closed_cycle_refuses(self):
        self.prepare()
        mutate(self.repo, self.cid, 'pause', reason='owner pause')
        self.ok(self.lost(evidence=OWNER))
        cid = self.fixture()
        self.assertNotEqual(cid, self.cid)
        prepared = self.ok({'op': 'prepare-dispatch', 'op_id': 'prep-0009', 'task_id': 'build-it', 'role': 'developer', 'host': 'claude-code',
                            'assignment_text': TEXT}, cid=cid)
        self.addCleanup(lambda: shutil.rmtree(Path(prepared['result_path']).parent, ignore_errors=True))
        mutate(self.repo, cid, 'owner-complete', owner={'origin': 'owner-conversation', 'quote': 'close it', 'date': '2026-10-30', 'conversation': 'c'})
        self.refused(self.lost(evidence=OWNER), 'cycle-closed', cid=cid)

    def test_no_operation_infers_loss_from_elapsed_time(self):
        self.prepare()
        self.age(10)
        before = self.record_path().read_bytes()
        seen = self.ok({'op': 'inspect'})['assignments'][0]
        self.assertEqual((seen['state'], seen['liveness']), ('reserved', 'unknown'))
        self.assertEqual(self.record_path().read_bytes(), before)
        self.assertEqual(self.doc()['assignments'][0]['state'], 'reserved')

    def test_failed_delivery_returns_the_task_and_attempt_two_is_reserved(self):
        prepared = self.prepare()
        self.write_result(prepared)
        self.ok(self.deliver_request(outcome='failed', note='tests failed'))
        self.assertEqual(self.doc()['plan']['tasks'][0]['status'], 'pending')
        self.assertEqual(self.prepare(op_id='prep-0002', assignment='build-it')['attempt'], 2)

    def test_attach_with_a_different_handle_is_refused(self):
        self.prepare(mode='background')
        self.ok({'op': 'attach-execution', 'op_id': 'attach-001', 'assignment': 'build-it', 'attempt': 1, 'handle': 'h1'})
        self.refused({'op': 'attach-execution', 'op_id': 'attach-002', 'assignment': 'build-it', 'attempt': 1, 'handle': 'h2'}, 'handle-conflict')

    def test_the_next_attempt_is_told_about_the_partial_commit_of_the_lost_one(self):
        prepared = self.prepare()
        partial = self.checkpoint_work(prepared, marker=False)
        self.ok(self.lost(evidence=OWNER))
        again = self.prepare(op_id='prep-0002', assignment='build-it')
        self.assertIn(partial, again['invocation']['parameters']['prompt'])


class InspectAttemptTests(OpsBase):
    def test_recovery_order_per_observation_and_host(self):
        prepared = self.prepare(mode='background')
        seen = self.inspect_attempt()
        self.assertEqual((seen['observation'], seen['recovery']), ('reserved-unbound', ['await-marker', 'attach-execution', 'deliver', 'mark-lost']))
        self.ok({'op': 'attach-execution', 'op_id': 'attach-001', 'assignment': 'build-it', 'attempt': 1, 'handle': 'h1'})
        seen = self.inspect_attempt()
        self.assertEqual((seen['observation'], seen['recovery']), ('running-bound', ['await-marker', 'deliver', 'mark-lost']))
        self.write_result(prepared)
        seen = self.inspect_attempt()
        self.assertEqual((seen['observation'], seen['recovery']), ('result-arrived', ['deliver']))

    def test_handle_less_host_has_no_attach_step(self):
        self.prepare(host='opencode')
        self.assertEqual(self.inspect_attempt()['recovery'], ['await-marker', 'deliver', 'mark-lost'])

    def test_claude_code_blocking_default_has_no_attach_step(self):
        self.prepare()
        seen = self.inspect_attempt()
        self.assertEqual((seen['mode'], seen['recovery']), ('blocking', ['await-marker', 'deliver', 'mark-lost']))
        self.assertNotIn('attach-execution', [a['request']['op'] for a in self.ok({'op': 'inspect'})['actions'] if 'request' in a])

    def test_ended_wait_windows_leave_no_pause_and_no_state_change(self):
        """Windows are only a waiting mechanism: however many end, inspect pauses nothing and changes nothing."""
        self.prepare()
        for bound in (False, True):
            if bound:
                self.ok({'op': 'attach-execution', 'op_id': 'attach-001', 'assignment': 'build-it', 'attempt': 1, 'handle': 'h1'})
            self.age(48)
            before = self.record_path().read_bytes()
            seen = self.ok({'op': 'inspect'})
            entry = seen['assignments'][0]
            self.assertEqual(entry['observation'], 'running-bound' if bound else 'reserved-unbound')
            self.assertEqual(entry['liveness'], 'unknown')
            self.assertEqual(entry['recovery'][0], 'await-marker', 'inspect offers the next wait window')
            token = self.doc()['assignments'][0]['delivery_token']
            self.assertEqual((entry['wait']['marker'], entry['wait']['window_seconds']), (cycle_hosts.marker('build-it', 1, token), 1800))
            self.assertNotIn('windows', entry['wait'])
            self.assertFalse([a for a in seen['actions'] if 'argv' in a and 'pause' in a['argv']])
            self.assertNotIn('window', entry)
            self.assertEqual(self.record_path().read_bytes(), before, 'inspect changed the record')
            doc = self.doc()
            self.assertEqual((doc['status'], doc['assignments'][0]['attempt']), ('active', 1))
            self.assertEqual(len(cycle_ops.reservations(doc, 'build-it', 'developer')), 1)
        self.assertNotEqual(cycle_hosts.liveness('claude-code', state='running', host_status='running'), 'terminated')

    def test_a_recorded_wait_window_pause_stays_readable_and_resumable(self):
        """Records paused under the removed trigger keep their reason; resume works and offers no new pause."""
        self.prepare(mode='background')
        self.ok({'op': 'attach-execution', 'op_id': 'attach-001', 'assignment': 'build-it', 'attempt': 1, 'handle': 'h1'})
        before = self.doc()['assignments'][0]
        mutate(self.repo, self.cid, 'pause', reason='no result after three wait windows')
        doc = self.doc()
        self.assertEqual((doc['status'], doc['assignments'][0]), ('paused', before))
        self.assertEqual(doc['blocker']['reason'], 'no result after three wait windows')
        self.assertEqual(self.ok({'op': 'inspect'})['status'], 'paused')
        mutate(self.repo, self.cid, 'resume', reason='the owner reviewed the wait')
        self.age(48)
        seen = self.ok({'op': 'inspect'})
        self.assertEqual((seen['status'], seen['assignments'][0]['attempt']), ('active', 1))
        self.assertFalse([a for a in seen['actions'] if 'argv' in a and 'pause' in a['argv']])

    def test_a_missing_grant_refusal_routes_through_resume_then_mark_lost_as_one_attempt(self):
        """A missing-grant refusal pauses; after resume, mark-lost releases the task and the attempt counts."""
        self.prepare()
        mutate(self.repo, self.cid, 'pause', reason='contradicted premise: dispatch refused, missing grant Agent(developer)')
        mutate(self.repo, self.cid, 'resume', reason='projection regenerated')
        self.refused({'op': 'prepare-dispatch', 'op_id': 'prep-0002', 'task_id': 'build-it', 'role': 'developer',
                      'host': 'claude-code', 'assignment_text': TEXT}, 'task-not-eligible', 'unresolved-dispatch')
        self.ok(self.lost(evidence=OWNER, note='the owner confirmed the refused dispatch never started'))
        again = self.prepare(op_id='prep-0003', assignment='build-it')
        self.assertEqual(again['attempt'], 2)
        self.assertEqual(len(cycle_ops.reservations(self.doc(), 'build-it', 'developer')), 2)

    def test_an_arrived_result_is_never_an_escalation(self):
        prepared = self.prepare()
        self.age(5)
        self.write_result(prepared)
        seen = self.ok({'op': 'inspect'})
        self.assertFalse([a for a in seen['actions'] if 'argv' in a and 'pause' in a['argv']])

    def test_liveness_is_unknown_without_a_host_status(self):
        self.prepare()
        self.assertEqual(self.inspect_attempt()['liveness'], 'unknown')
        self.assertEqual(cycle_hosts.liveness('claude-code', state='running', host_status='killed'), 'terminated')

    def test_missing_result_directory_is_reported_with_the_mark_lost_recovery(self):
        prepared = self.prepare()
        Path(prepared['result_path']).parent.rmdir()
        seen = self.ok({'op': 'inspect'})
        self.assertEqual(seen['assignments'][0]['problem'], 'result-path-missing')
        lost = [a for a in seen['actions'] if a.get('request', {}).get('op') == 'mark-lost']
        self.assertEqual(lost[0]['request'], {'op': 'mark-lost', 'assignment': 'build-it', 'attempt': 1})
        self.assertEqual(lost[0]['caller_fills'], ['op_id', 'evidence', 'note'])
        self.assert_validates(lost)

    def test_orphan_retained_result_is_reported_and_never_deleted(self):
        prepared = self.prepare()
        sha = self.work(prepared)
        with patch.object(cycle_ops, 'save', side_effect=RuntimeError('crash before the save')):
            with self.assertRaises(RuntimeError):
                cycle_ops.run(self.repo, self.cid, self.deliver_request(commits=[sha]))
        retained = self.repo / 'bionic/cycles' / self.cid / 'results/build-it-attempt-1.md'
        self.assertTrue(retained.is_file())
        problems = self.ok({'op': 'inspect'})['problems']
        self.assertEqual([(p['code'], p['path']) for p in problems], [('orphan-retained-result', f'cycles/{self.cid}/results/build-it-attempt-1.md')])
        self.write_result(prepared, marker=False)
        self.ok(self.lost(evidence=OWNER))
        self.assertEqual(self.ok({'op': 'inspect'})['problems'][0]['code'], 'orphan-retained-result')
        self.assertTrue(retained.is_file())

    def test_a_delivered_result_is_not_an_orphan(self):
        prepared = self.prepare()
        sha = self.work(prepared)
        self.ok(self.deliver_request(commits=[sha]))
        self.assertEqual(self.ok({'op': 'inspect'})['problems'], [])

    def test_lost_attempt_reports_uncommitted_leftovers_in_scope(self):
        prepared = self.prepare()
        (self.repo / 'src/a.py').write_text('answer = 3\n')
        (self.repo / 'src/new.py').write_text('x = 1\n')
        (self.repo / 'outside.txt').write_text('not in scope\n')
        self.ok(self.lost(evidence=OWNER))
        seen = self.ok({'op': 'inspect'})
        lost = [a for a in seen['assignments'] if a['observation'] == 'lost'][0]
        self.assertEqual((lost['id'], lost['attempt']), ('build-it', 1))
        self.assertEqual(sorted(lost['leftovers']), ['src/a.py', 'src/new.py'])

    def test_a_lost_attempt_with_a_clean_tree_has_no_leftovers(self):
        self.prepare()
        self.ok(self.lost(evidence=OWNER))
        lost = self.inspect_attempt()
        self.assertEqual((lost['observation'], lost['leftovers']), ('lost', []))

    def test_a_replaced_lost_attempt_is_no_longer_listed_as_lost(self):
        self.prepare()
        self.ok(self.lost(evidence=OWNER))
        self.prepare(op_id='prep-0002', assignment='build-it')
        seen = self.inspect_attempt()
        self.assertEqual((seen['attempt'], seen['observation']), (2, 'reserved-unbound'))
        self.assertNotIn('leftovers', seen)


class RefusalRecoveryTests(OpsBase):
    def test_unresolved_dispatch_points_at_deliver_and_mark_lost(self):
        self.prepare()
        response = self.refused({'op': 'prepare-dispatch', 'op_id': 'prep-0002', 'task_id': 'build-it', 'role': 'developer',
                                 'host': 'claude-code', 'assignment_text': TEXT}, 'unresolved-dispatch', 'task-not-eligible')
        recovery = [e for e in response['errors'] if e['code'] == 'unresolved-dispatch'][0]['recovery']
        ops = [r['request']['op'] for r in recovery]
        self.assertEqual(ops, ['inspect', 'deliver', 'mark-lost'])
        self.assertEqual(recovery[2]['caller_fills'], ['op_id', 'evidence', 'note'])
        self.assertEqual(recovery[1]['request'], {'op': 'deliver', 'assignment': 'build-it', 'attempt': 1})
        self.assertEqual(self.assert_validates(recovery), 3)

    def test_commit_not_from_base_states_its_recovery(self):
        prepared = self.prepare()
        empty = subprocess.run(['git', '-C', str(self.repo), 'hash-object', '-t', 'tree', '-w', '--stdin'], input='', capture_output=True,
                               text=True, check=True).stdout.strip()
        stray = self.git('commit-tree', empty, '-m', 'unrelated root')
        self.write_result(prepared)
        request = self.deliver_request(commits=[stray])
        response = self.refused(request, 'commit-not-from-base')
        recovery = response['errors'][0]['recovery']
        self.assertEqual([r['request']['op'] for r in recovery], ['deliver', 'mark-lost'])
        self.assertIn('rebase', recovery[0]['purpose'])
        self.assertEqual(recovery[0]['request'], {k: v for k, v in request.items() if k != 'op_id'})
        self.assertEqual(recovery[0]['caller_fills'], ['op_id'])
        self.assert_validates(recovery)

    def test_evidence_that_is_not_in_the_main_checkout_says_to_integrate_it(self):
        prepared = self.prepare()
        sha = self.work(prepared)
        response = self.refused(self.deliver_request(commits=[sha], evidence=['cycles/nowhere/evidence.md']), 'evidence-missing')
        recovery = response['errors'][0]['recovery']
        self.assertIn('unintegrated branch', recovery[0]['purpose']); self.assertIn('must be integrated', recovery[0]['purpose'])
        self.assertEqual(recovery[0]['request']['evidence'], ['cycles/nowhere/evidence.md'])
        self.assert_validates(recovery)

    def test_attempt_limit_counts_across_assignments_in_a_pass(self):
        for n in range(1, 4):
            # No assignment id: each re-dispatch is a new assignment, and the count must still reach the limit.
            prepared = self.prepare(op_id=f'prep-000{n}')
            self.write_result(prepared)
            self.ok(self.deliver_request(op_id=f'deliver-0{n}', assignment=prepared['assignment'], outcome='failed'))
        self.assertEqual(len(self.doc()['assignments']), 3)
        response = self.refused({'op': 'prepare-dispatch', 'op_id': 'prep-0004', 'task_id': 'build-it', 'role': 'developer',
                                 'host': 'claude-code', 'assignment_text': TEXT}, 'attempt-limit')
        self.assertEqual(response['errors'][0]['observed'], 3)
        # Another role on the same task has its own count.
        self.assertEqual(self.prepare(op_id='prep-0005', role='reviewer')['attempt'], 1)

    def test_every_recovery_request_validates_once_filled(self):
        prepared = self.prepare()
        recoveries = []
        recoveries += self.refused(self.lost(evidence={'kind': 'dispatch-error', 'detail': 'x'}), 'not-affirmative')['errors'][0]['recovery']
        self.write_result(prepared)
        recoveries += self.refused(self.lost(op_id='lost-0002', evidence=OWNER), 'result-arrived')['errors'][0]['recovery']
        self.refused(self.lost(op_id='lost-0003', attempt=2, evidence=OWNER), 'superseded-attempt')
        held = self.refused({'op': 'prepare-dispatch', 'op_id': 'prep-0002', 'task_id': 'build-it', 'role': 'developer', 'host': 'claude-code',
                                   'assignment_text': TEXT}, 'unresolved-dispatch', 'task-not-eligible')
        recoveries += [r for e in held['errors'] for r in e['recovery']]
        recoveries += self.ok({'op': 'inspect'})['actions']
        self.assertGreaterEqual(self.assert_validates(recoveries), 6)


class TransactionTests(OpsBase):
    def cycle_process(self, request):
        return subprocess.Popen([sys.executable, str(SCRIPTS / 'cycle.py'), '--repo-root', str(self.repo), '--compact', 'op', self.cid,
                                 '--json', json.dumps(request)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=SCRIPTS)

    def test_two_processes_delivering_different_tasks_both_persist(self):
        self.add_task('build-two')
        first = self.prepare()
        second = self.prepare(op_id='prep-0002', task_id='build-two')
        sha_one = self.commit_file('src/one.py', 'one = 1\n', 'build-it'); self.write_result(first)
        sha_two = self.commit_file('src/two.py', 'two = 2\n', 'build-two'); self.write_result(second)
        requests = [self.deliver_request(op_id='deliver-01', commits=[sha_one]),
                    self.deliver_request(op_id='deliver-02', assignment='build-two', commits=[sha_two])]
        procs = [self.cycle_process(r) for r in requests]
        results = []
        for proc in procs:
            out, err = proc.communicate(timeout=120)
            results.append((proc.returncode, out, err))
        for code, out, err in results:
            self.assertEqual(code, 0, (out, err))
        doc = self.doc()
        self.assertEqual({t['id']: t['status'] for t in doc['plan']['tasks']}, {'build-it': 'done', 'build-two': 'done'})
        self.assertEqual(sorted(o['op_id'] for o in doc['operations']), ['deliver-01', 'deliver-02', 'prep-0001', 'prep-0002'])
        revisions = [o['revision'] for o in doc['operations']]
        self.assertEqual(revisions, sorted(set(revisions)), 'two saves shared a revision')
        self.assertEqual(doc['revision'], revisions[-1])

    def test_stale_attach_deliver_and_mark_lost_are_refused_without_a_write(self):
        prepared = self.prepare()
        self.ok(self.lost(evidence=OWNER))
        self.prepare(op_id='prep-0002', assignment='build-it')
        self.refused({'op': 'attach-execution', 'op_id': 'attach-001', 'assignment': 'build-it', 'attempt': 1, 'handle': 'h1'}, 'superseded-attempt')
        self.refused(self.deliver_request(op_id='deliver-01', attempt=1, outcome='failed'), 'superseded-attempt')
        self.refused(self.lost(op_id='lost-0002', attempt=1, evidence=OWNER), 'superseded-attempt')

    def test_a_retry_after_a_commit_whose_response_was_lost_replays(self):
        prepared = self.prepare()
        sha = self.work(prepared)
        request = self.deliver_request(commits=[sha])
        first = cycle_ops.run(self.repo, self.cid, request)   # the caller never reads this response
        self.assertEqual(first[0], 0)
        before = self.record_path().read_bytes()
        again = self.ok(request)
        self.assertEqual((again['replayed'], again['changed'], again['revision']), (True, False, first[1]['revision']))
        self.assertEqual(self.record_path().read_bytes(), before)
        prep = self.ok({'op': 'prepare-dispatch', 'op_id': 'prep-0001', 'task_id': 'build-it', 'role': 'developer', 'host': 'claude-code',
                        'assignment_text': TEXT})
        self.assertEqual((prep['replayed'], prep['attempt_state']), (True, 'finished'))
        self.assertNotIn('invocation', prep)


class LinkedWorktreeInspectTests(OpsBase):
    def test_inspect_from_a_linked_worktree_evaluates_the_main_checkout(self):
        prepared = self.prepare()
        (self.repo / 'src/a.py').write_text('answer = 3\n')
        linked = self.repo.parent / (self.repo.name + '-linked')
        self.git('worktree', 'add', '-q', str(linked), '-b', 'linked-branch')
        self.addCleanup(lambda: subprocess.run(['git', '-C', str(self.repo), 'worktree', 'remove', '--force', str(linked)], capture_output=True))
        self.ok(self.lost(evidence=OWNER))
        import contextlib, io
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cycle.main(['--repo-root', str(linked), 'op', self.cid, '--json', json.dumps({'op': 'inspect'})])
        response = json.loads(out.getvalue())
        self.assertEqual(code, 0, response)
        lost = [a for a in response['assignments'] if a['observation'] == 'lost'][0]
        # The main checkout holds the uncommitted change; the linked copy is clean.
        self.assertEqual(lost['leftovers'], ['src/a.py'])
        self.assertEqual(response['revision'], self.doc()['revision'])


if __name__ == '__main__':
    unittest.main()
