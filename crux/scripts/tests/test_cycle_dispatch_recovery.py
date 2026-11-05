"""Dispatch recovery through the typed engine, once per host adapter.

Every case drives `cycle.py op` against a temp repository and plays the host's side by hand:
the handle a dispatch returns, the result file a child writes, the commits it makes.
Crash points covered: after the reservation and before the host call, after the host call
and before attach, a lost notification, ambiguous liveness, the attempt limit, concurrent
dispatch, stale requests, mark-lost on affirmative evidence, and an explicit dispatch mode."""
import json
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle_hosts
import cycle_ops
from cycle_workflow import load
from test_cycle_slice import SliceBase, TEXT, SCRIPTS

HOSTS = tuple(cycle_hosts.ADAPTERS)
MARK_LOST_SKIP = ('mark-lost is not implemented in the engine yet (operation-unavailable); '
                  'hand-over task handover-c-engine-recovery requests it')


def mark_lost_available():
    return 'mark-lost' in cycle_ops.HANDLERS


class HostCase(SliceBase):
    """Shared helpers. Concrete classes combine a mixin below with this base and fix `host`."""
    host = None

    @property
    def handle_host(self):
        # Read from the adapter data, not from returns_handle, which the engine also calls.
        adapter = cycle_hosts.ADAPTERS[self.host]
        return adapter.modes[adapter.default_mode].handle_source is not None

    def dispatch_request(self, op_id, **extra):
        return {'op': 'prepare-dispatch', 'op_id': op_id, 'task_id': 'build-it', 'role': 'developer',
                'host': self.host, 'assignment_text': TEXT, **extra}

    def dispatch(self, op_id='prep-0001', **extra):
        return self.ok(self.dispatch_request(op_id, **extra))

    def attach(self, op_id='attach-001', attempt=1, handle='handle-1', assignment='build-it'):
        return {'op': 'attach-execution', 'op_id': op_id, 'assignment': assignment, 'attempt': attempt, 'handle': handle}

    def deliver_request(self, op_id, outcome='failed', attempt=1, assignment='build-it', **extra):
        return {'op': 'deliver', 'op_id': op_id, 'assignment': assignment, 'attempt': attempt, 'outcome': outcome, **extra}

    def seen(self):
        return self.ok({'op': 'inspect', 'host': self.host})

    def attempt_view(self, assignment='build-it'):
        return next(a for a in self.seen()['assignments'] if a['id'] == assignment)

    def action_ops(self):
        return [a['request']['op'] for a in self.seen()['actions'] if 'request' in a]

    def stored_state(self):
        return load(self.repo, self.cid)['assignments'][0]['state']

    def refused_any(self, request, **kw):
        """A refusal whose codes the caller does not pin; the record stays byte for byte."""
        before = self.record_path().read_bytes()
        code, response = self.op(request, **kw)
        self.assertEqual(code, 1, response); self.assertFalse(response['ok'])
        self.assertEqual(self.record_path().read_bytes(), before, 'a refusal wrote the record')
        return response


class CrashPointMixin:
    def test_crash_after_reservation_leaves_reserved_unbound(self):
        prepared = self.dispatch()
        entry = load(self.repo, self.cid)['assignments'][0]
        self.assertEqual((entry['state'], entry['agent'], entry['host']), ('reserved', None, self.host))
        view = self.attempt_view()
        self.assertEqual((view['observation'], view['liveness'], view['handle']), ('reserved-unbound', 'unknown', None))
        # The retry the crashed caller would make must not dispatch a second child.
        self.refused(self.dispatch_request('prep-0002'), 'unresolved-dispatch', 'task-not-eligible')
        ops = self.action_ops()
        self.assertNotIn('prepare-dispatch', ops, 'a held task is offered no second dispatch')
        self.assertEqual('attach-execution' in ops, self.handle_host)
        self.assertEqual(len(load(self.repo, self.cid)['assignments']), 1)
        self.assertEqual(prepared['invocation']['host'], self.host)

    def test_unresolved_dispatch_recovery_points_at_inspect(self):
        self.dispatch()
        response = self.refused(self.dispatch_request('prep-0002'), 'unresolved-dispatch', 'task-not-eligible')
        held = next(e for e in response['errors'] if e['code'] == 'unresolved-dispatch')
        self.assertEqual(held['recovery'][0]['request'], {'op': 'inspect'})

    def test_crash_after_host_call_then_attach_binds_once(self):
        if not self.handle_host:
            self.skipTest(f'{self.host} default mode returns no handle')
        self.dispatch()
        bound = self.ok(self.attach())
        self.assertEqual((bound['changed'], bound['handle']), (True, 'handle-1'))
        view = self.attempt_view()
        self.assertEqual((view['observation'], view['liveness'], view['handle']), ('running-bound', 'unknown', 'handle-1'))
        same_op = self.ok(self.attach())
        self.assertEqual((same_op['replayed'], same_op['changed']), (True, False))
        same_handle = self.ok(self.attach(op_id='attach-002'))
        self.assertEqual(same_handle['changed'], False)
        self.refused(self.attach(op_id='attach-003', handle='handle-2'), 'handle-conflict')
        replay = self.ok(self.dispatch_request('prep-0001'))
        self.assertNotIn('invocation', replay, 'a bound attempt is not dispatched again')
        self.refused(self.dispatch_request('prep-0002'), 'unresolved-dispatch', 'task-not-eligible')
        self.assertEqual([a['id'] for a in load(self.repo, self.cid)['assignments']], ['build-it'])

    def test_attach_action_validates_against_the_operation_schema(self):
        if not self.handle_host:
            self.skipTest(f'{self.host} default mode returns no handle')
        self.dispatch()
        action = next(a for a in self.seen()['actions'] if a.get('request', {}).get('op') == 'attach-execution')
        self.assertIn('handle', action['caller_fills'])
        self.assertEqual(cycle_ops.schema_errors({**action['request'], 'op_id': 'attach-009', 'handle': 'h'}), [])

    def test_invocation_matches_the_adapter_default_mode(self):
        prepared = self.dispatch()
        invocation = prepared['invocation']
        self.assertEqual(invocation['mode'], cycle_hosts.adapter(self.host).default_mode)
        self.assertEqual(invocation['handle'] is not None, self.handle_host)
        conditional = cycle_hosts.mode_of(self.host).conditional_handle_source is not None
        self.assertEqual(invocation['attach'] is not None, self.handle_host or conditional)
        if conditional:
            # Claude Code blocking: an agentId that arrives without the final report is the only handle.
            self.assertEqual((self.host, invocation['attach']['conditional']), ('claude-code', True))
        self.assertEqual(invocation['wait']['marker'], cycle_hosts.marker('build-it', 1, prepared['delivery_token']))


class LostNotificationMixin:
    def test_complete_result_turns_the_observation_into_result_arrived(self):
        prepared = self.dispatch()
        if self.handle_host:
            self.ok(self.attach())
        self.assertEqual(self.attempt_view()['liveness'], 'unknown')
        self.write_result(prepared)
        view = self.attempt_view()
        self.assertEqual(view['observation'], 'result-arrived')
        self.assertNotIn('liveness', view)
        self.assertIn('deliver', self.action_ops())

    def test_result_without_the_marker_is_not_a_result(self):
        prepared = self.dispatch()
        if self.handle_host:
            self.ok(self.attach())
        self.write_result(prepared, marker=False)
        view = self.attempt_view()
        self.assertEqual((view['observation'], view['liveness']), ('running-bound' if self.handle_host else 'reserved-unbound', 'unknown'))
        self.assertNotIn('deliver', self.action_ops())
        self.refused(self.deliver_request('deliver-01', outcome='blocked'), 'result-incomplete')
        self.assertEqual(self.stored_state(), 'running' if self.handle_host else 'reserved')

    def test_a_wrong_header_is_refused_even_with_a_marker(self):
        prepared = self.dispatch()
        self.write_result(prepared, assignment='other')
        self.assertNotEqual(self.attempt_view()['observation'], 'result-arrived')
        self.refused(self.deliver_request('deliver-01', outcome='blocked'), 'result-header')

    def test_trailing_newline_after_the_marker_is_accepted(self):
        prepared = self.dispatch()
        for tail in ('', '\n', '\n\n'):
            with self.subTest(tail=repr(tail)):
                Path(prepared['result_path']).write_text(
                    f"Assignment: build-it\nAttempt: 1\n\nOutcome: BLOCKED.\n{cycle_hosts.marker('build-it', 1, prepared['delivery_token'])}{tail}")
                self.assertEqual(self.attempt_view()['observation'], 'result-arrived')
        delivered = self.ok(self.deliver_request('deliver-01', outcome='blocked'))
        self.assertEqual((delivered['outcome'], delivered['status']), ('blocked', 'blocked'))
        self.assertEqual(self.attempt_view()['observation'], 'delivered')

    def test_delivery_without_ever_attaching_succeeds(self):
        prepared = self.dispatch()
        self.write_result(prepared)
        delivered = self.ok(self.deliver_request('deliver-01', outcome='failed', note='tests failed'))
        self.assertEqual(delivered['status'], 'pending')
        self.assertIsNone(load(self.repo, self.cid)['assignments'][0]['agent'])


class HandleLessMixin:
    def test_reserved_then_deliver_with_no_attach(self):
        if self.handle_host:
            self.skipTest(f'{self.host} default mode returns a handle')
        prepared = self.dispatch()
        self.assertNotIn('attach-execution', self.action_ops())
        sha = self.work(prepared)
        self.assertNotIn('attach-execution', self.action_ops())
        self.assertEqual(self.attempt_view()['observation'], 'result-arrived')
        delivered = self.ok(self.deliver_request('deliver-01', outcome='done', commits=[sha]))
        self.assertEqual(delivered['status'], 'done')
        self.assertIsNone(load(self.repo, self.cid)['assignments'][0]['agent'])


    def test_resumed_caller_is_offered_the_marker_await_never_a_dispatch(self):
        """A handle-less attempt (claude-code blocking, opencode foreground, omp blocking) was dispatched once by
        prepare-dispatch's invocation. A caller that resumes with no complete result gets the window-bounded
        marker await and the conditional mark-lost route; no re-offered action carries a dispatch tool call."""
        if self.handle_host:
            self.skipTest(f'{self.host} default mode returns a handle')
        mode = cycle_hosts.mode_of(self.host)
        prepared = self.dispatch()
        seen = self.seen()
        view = next(a for a in seen['assignments'] if a['id'] == 'build-it')
        self.assertEqual((view['observation'], view['recovery']), ('reserved-unbound', ['await-marker', 'deliver', 'mark-lost']))
        self.assertEqual((view['wait']['mechanism'], view['wait']['window_seconds']), ('background-command', 1800))
        self.assertNotEqual(view['wait']['tool'], mode.tool)
        self.assertNotIn('check', view['wait'])
        # The marker await is the whole wait: the cycle writer's await with this attempt's marker.
        self.assertIn(f"--marker build-it/{prepared['attempt']}", view['wait']['parameters']['command'])
        # Nothing the engine re-offers names the dispatch tool: not the wait, not any action, not the recovery list.
        offered = json.dumps({'wait': view['wait'], 'recovery': view['recovery'], 'actions': seen['actions']})
        self.assertNotIn(f'"tool": "{mode.tool}"', offered)
        self.assertEqual([a['request']['op'] for a in seen['actions'] if 'request' in a].count('prepare-dispatch'), 0)
        # The conditional mark-lost route stays: it is inside the attempt's recovery, never a top-level action.
        self.assertIn('mark-lost', view['recovery'])


class AttemptLimitMixin:
    def finish_attempt(self, prepared, n, outcome='failed'):
        self.write_result(prepared)
        self.ok(self.deliver_request(f'deliver-0{n}', outcome=outcome, attempt=prepared['attempt'], assignment=prepared['assignment']))

    def limit_refusal(self):
        response = self.refused(self.dispatch_request('prep-0009'), 'attempt-limit')
        self.assertEqual(response['errors'][0]['observed'], 3)
        self.assertEqual(load(self.repo, self.cid)['phase'], 'build')
        # Build cannot take a counted return; exhausting its allowance offers the escalation stop.
        self.assertEqual([r['argv'][6] for r in response['errors'][0]['recovery']], ['pause'])

    def test_three_attempts_of_one_assignment_then_the_limit(self):
        for n in range(1, 4):
            prepared = self.dispatch(op_id=f'prep-000{n}', assignment='build-it')
            self.assertEqual(prepared['attempt'], n)
            self.finish_attempt(prepared, n, 'blocked' if n == 2 else 'failed')
        self.limit_refusal()
        # A different role on the same task has its own count.
        reviewer = self.ok({**self.dispatch_request('prep-0010'), 'role': 'reviewer'})
        self.assertEqual(reviewer['attempt'], 1)

    def test_inspect_offers_no_dispatch_the_attempt_limit_would_refuse(self):
        for n in range(1, 4):
            self.finish_attempt(self.dispatch(op_id=f'prep-000{n}', assignment='build-it'), n, 'failed')
        self.limit_refusal()
        actions = self.ok({'op': 'inspect'})['actions']
        self.assertEqual([a for a in actions if a.get('request', {}).get('op') == 'prepare-dispatch'], [])
        # The refusal's own recovery is what inspect offers instead.
        self.assertEqual([a['argv'][6] for a in actions if a.get('argv') and a['argv'][6] in ('return', 'pause')], ['pause'])

    def test_fresh_assignment_ids_count_against_the_same_limit(self):
        self.finish_attempt(self.dispatch(op_id='prep-0001'), 1)
        second = self.dispatch(op_id='prep-0002', assignment='alt-a')
        self.assertEqual((second['assignment'], second['attempt']), ('alt-a', 1))
        self.finish_attempt(second, 2)
        self.finish_attempt(self.dispatch(op_id='prep-0003', assignment='alt-b'), 3)
        self.assertEqual(len(load(self.repo, self.cid)['assignments']), 3)
        self.limit_refusal()
        other = self.ok({**self.dispatch_request('prep-0010'), 'role': 'reviewer', 'assignment': 'rev-a'})
        self.assertEqual(other['attempt'], 1)

    def test_two_attempts_stay_below_the_limit(self):
        for n in (1, 2):
            self.finish_attempt(self.dispatch(op_id=f'prep-000{n}', assignment='build-it'), n)
        self.assertEqual(self.dispatch(op_id='prep-0003', assignment='build-it')['attempt'], 3)


class ConcurrencyMixin:
    def start(self, request):
        return subprocess.Popen([sys.executable, str(SCRIPTS / 'cycle.py'), '--repo-root', str(self.repo), '--compact', 'op', self.cid,
                                 '--json', json.dumps(request)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def finished(self, proc):
        out, err = proc.communicate(timeout=120)
        return proc.returncode, out, err

    def test_two_concurrent_dispatches_reserve_once(self):
        procs = [self.start(self.dispatch_request(f'prep-000{n}')) for n in (1, 2)]
        outputs = [self.finished(p) for p in procs]
        self.assertEqual(sorted(code for code, _, _ in outputs), [0, 1], outputs)
        refusal = json.loads(next(out for code, out, _ in outputs if code == 1))
        errors = {e['code']: e for e in refusal['errors']}
        # The loser can encounter the winner at preflight or after the unlocked selection window.
        # Both refuse before a second reservation and require refreshing the actual held attempt.
        if 'unresolved-dispatch' in errors:
            self.assertEqual(set(errors), {'unresolved-dispatch', 'task-not-eligible'})
            recovery = errors['unresolved-dispatch']['recovery']
        else:
            self.assertEqual(set(errors), {'dispatch-context-changed'})
            recovery = errors['dispatch-context-changed']['recovery']
        self.assertEqual(recovery[0]['request'], {'op': 'inspect'})
        self.assertNotIn('prepare-dispatch', [a.get('request', {}).get('op') for a in recovery])
        doc = load(self.repo, self.cid)
        self.assertEqual([(a['id'], a['attempt'], a['state']) for a in doc['assignments']], [('build-it', 1, 'reserved')])
        self.assertEqual([o['op'] for o in doc['operations']], ['prepare-dispatch'])


class StaleRequestMixin:
    def second_attempt(self):
        first = self.dispatch()
        self.write_result(first)
        self.ok(self.deliver_request('deliver-01', outcome='failed'))
        return self.dispatch(op_id='prep-0002', assignment='build-it')

    def test_attach_and_deliver_naming_a_superseded_attempt_are_refused(self):
        self.assertEqual(self.second_attempt()['attempt'], 2)
        self.refused(self.attach(op_id='attach-009', attempt=1), 'superseded-attempt')
        self.refused(self.deliver_request('deliver-09', attempt=1), 'superseded-attempt')
        self.refused(self.deliver_request('deliver-10', attempt=3), 'superseded-attempt')

    def test_unknown_assignment_is_refused(self):
        self.dispatch()
        self.refused(self.attach(op_id='attach-009', assignment='ghost'), 'unknown-assignment')
        self.refused(self.deliver_request('deliver-09', assignment='ghost'), 'unknown-assignment')

    def test_mark_lost_naming_a_superseded_attempt_is_refused(self):
        if not mark_lost_available():
            self.skipTest(MARK_LOST_SKIP)
        self.second_attempt()
        self.refused_any({'op': 'mark-lost', 'op_id': 'lost-0009', 'assignment': 'build-it', 'attempt': 1, 'note': 'stale',
                          'evidence': {'kind': 'owner-confirmation', 'detail': 'the owner says it died'}})


class MarkLostMixin:
    """Written against the request shape the hand-over asks for; skipped while the engine lacks it."""

    def lose(self, kind, detail, op_id='lost-0001', attempt=1):
        return {'op': 'mark-lost', 'op_id': op_id, 'assignment': 'build-it', 'attempt': attempt, 'note': 'host evidence quoted',
                'evidence': {'kind': kind, 'detail': detail}}

    def need_mark_lost(self):
        if not mark_lost_available():
            self.skipTest(MARK_LOST_SKIP)
        return cycle_hosts.mode_of(self.host)

    def test_listed_dispatch_refusal_allows_mark_lost_and_an_immediate_second_attempt(self):
        mode = self.need_mark_lost()
        self.dispatch()
        self.ok(self.lose('dispatch-refusal', mode.no_execution_refusals[0]))
        self.assertEqual(self.stored_state(), 'lost')
        self.assertEqual(self.dispatch(op_id='prep-0002', assignment='build-it')['attempt'], 2)

    def test_dispatch_timeout_is_not_evidence(self):
        self.need_mark_lost()
        self.dispatch()
        self.refused_any(self.lose('dispatch-error', 'timeout'))
        self.refused_any(self.lose('window-expired', 'three windows elapsed', op_id='lost-0002'))
        self.assertEqual(self.stored_state(), 'reserved')

    def test_terminal_host_status_on_a_bound_handle_allows_it(self):
        mode = self.need_mark_lost()
        if not self.handle_host:
            self.skipTest(f'{self.host} default mode returns no handle')
        self.dispatch()
        self.ok(self.attach())
        self.ok(self.lose('terminal-status', mode.terminal_statuses[0]))
        self.assertEqual(self.stored_state(), 'lost')

    def test_listing_absence_is_not_evidence(self):
        self.need_mark_lost()
        self.dispatch()
        self.refused_any(self.lose('listing-absence', 'not in the agent list'))
        self.assertEqual(self.stored_state(), 'reserved')

    def test_owner_confirmation_allows_it(self):
        self.need_mark_lost()
        self.dispatch()
        self.ok(self.lose('owner-confirmation', 'owner: the agent is gone'))
        self.assertEqual(self.stored_state(), 'lost')

    def test_blocking_return_without_a_complete_result_allows_it(self):
        self.need_mark_lost()
        if self.handle_host:
            self.skipTest(f'{self.host} default mode returns a handle and does not block')
        self.write_result(self.dispatch(), marker=False)
        detail = ('the Agent call returned the child\'s final-report with no result file' if self.host == 'claude-code'
                  else 'the subagent call returned without a result')
        self.ok(self.lose('blocking-returned', detail))
        self.assertEqual(self.stored_state(), 'lost')

    def test_claude_code_blocking_return_without_a_final_report_is_refused(self):
        self.need_mark_lost()
        if self.host != 'claude-code':
            self.skipTest('only claude-code requires the final report in the detail')
        self.dispatch()
        response = self.refused_any(self.lose('blocking-returned', 'the Agent call returned'))
        self.assertEqual([e['code'] for e in response['errors']], ['not-affirmative'])
        self.assertEqual(self.stored_state(), 'reserved')

    def test_a_complete_result_forbids_mark_lost(self):
        self.need_mark_lost()
        self.write_result(self.dispatch())
        self.refused_any(self.lose('owner-confirmation', 'owner: the agent is gone'))

    def test_second_attempt_prompt_lists_the_partial_commit(self):
        self.need_mark_lost()
        sha = self.checkpoint_work(self.dispatch(), marker=False)
        self.ok(self.lose('owner-confirmation', 'owner: the agent is gone'))
        again = self.dispatch(op_id='prep-0002', assignment='build-it')
        self.assertIn(sha, prompt_of(self.host, again['invocation']['parameters']))


def prompt_of(host, parameters):
    """The prompt text in a host's dispatch parameters; Codex names the field `message`."""
    return parameters['message' if host == 'codex' else 'prompt']


class ModeMixin:
    """An explicit `mode` on prepare-dispatch, for hosts that offer more than one."""

    def other_mode(self):
        offered = cycle_hosts.modes(self.host)
        if len(offered) < 2:
            self.skipTest(f'{self.host} offers one dispatch mode')
        return offered[1]

    def test_default_dispatch_stores_the_default_mode(self):
        self.dispatch()
        self.assertEqual(load(self.repo, self.cid)['assignments'][0]['mode'], cycle_hosts.adapter(self.host).default_mode)

    def test_explicit_mode_is_stored_and_selects_the_invocation(self):
        mode = self.other_mode()
        invocation = self.dispatch(mode=mode)['invocation']
        self.assertEqual(invocation['mode'], mode)
        handles = cycle_hosts.returns_handle(self.host, mode)
        self.assertEqual(invocation['handle'] is not None, handles)
        self.assertEqual(load(self.repo, self.cid)['assignments'][0]['mode'], mode)
        self.assertEqual('attach-execution' in self.action_ops(), handles)
        self.assertEqual('attach-execution' in self.attempt_view()['recovery'], handles)

    def test_replay_rebuilds_the_invocation_in_the_stored_mode(self):
        mode = self.other_mode()
        self.dispatch(mode=mode)
        self.assertEqual(self.dispatch(mode=mode)['invocation']['mode'], mode)

    def test_loss_evidence_is_judged_in_the_stored_mode(self):
        mode = self.other_mode()
        if not cycle_hosts.returns_handle(self.host, mode):
            self.skipTest(f'{self.host} {mode} returns no handle')
        self.write_result(self.dispatch(mode=mode), marker=False)
        self.refused_any({'op': 'mark-lost', 'op_id': 'lost-0001', 'assignment': 'build-it', 'attempt': 1, 'note': 'quoted',
                          'evidence': {'kind': 'blocking-returned', 'detail': 'the call returned'}})
        self.assertEqual(self.stored_state(), 'reserved')

    def test_unknown_mode_is_refused(self):
        self.refused(self.dispatch_request('prep-0001', mode='sideways'), 'unknown-mode')


MIXINS = (CrashPointMixin, LostNotificationMixin, HandleLessMixin, AttemptLimitMixin, ConcurrencyMixin, StaleRequestMixin, MarkLostMixin,
          ModeMixin)

for _host in HOSTS:
    for _mixin in MIXINS:
        _name = f"{_mixin.__name__.removesuffix('Mixin')}Tests_{_host.replace('-', '_')}"
        globals()[_name] = type(_name, (_mixin, HostCase), {'host': _host})


if __name__ == '__main__':
    unittest.main()
