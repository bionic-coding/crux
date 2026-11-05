"""Delivery, replay, crash recovery and task-range rules of the typed cycle operations.

Reuses `SliceBase` through `OpsBase`. Where a test drives a low-level recovery argv, it runs the
argv in process and then submits the typed action that follows it."""
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle_ops
from cycle_workflow import create, load, mutate, validate
from test_cycle_ops_lifecycle import FILLS, OWNER, OpsBase
from test_cycle_slice import TEXT

OWNER_CLOSE = {'origin': 'owner-conversation', 'quote': 'close it', 'date': '2026-10-30', 'conversation': 'c'}


class DeliveryTests(OpsBase):
    def setUp(self):
        super().setUp()
        for name in ('e1.md', 'e2.md'):
            path = self.repo / 'bionic/evidence' / name
            path.parent.mkdir(exist_ok=True); path.write_text(f'{name}\n')

    def delivered(self, **extra):
        prepared = self.prepare()
        sha = self.work(prepared)
        request = self.deliver_request(commits=[sha], evidence=['bionic/evidence/e1.md'], stage='integrated', note='all done', **extra)
        return prepared, sha, request, self.ok(request)

    def test_an_identical_payload_is_a_no_op_under_any_op_id(self):
        prepared, sha, request, first = self.delivered()
        self.assertEqual(self.doc()['assignments'][0]['delivery']['evidence'], ['evidence/e1.md'])
        before = self.record_path().read_bytes()
        again = self.ok({**request, 'op_id': 'deliver-02'})
        self.assertEqual((again['changed'], again['replayed']), (False, False))
        self.assertEqual((again['outcome'], again['sha256']), ('done', first['sha256']))
        self.assertEqual(self.record_path().read_bytes(), before)

    def test_a_change_in_any_part_of_the_payload_is_a_delivery_conflict(self):
        prepared, sha, request, _ = self.delivered()
        extra_commit = self.commit_file('src/extra.py', 'x = 1\n', trailer=False)
        original = Path(prepared['result_path']).read_bytes()
        cases = {
            'outcome': {'outcome': 'blocked'},
            'commits': {'commits': [sha, extra_commit]},
            'evidence': {'evidence': ['bionic/evidence/e2.md']},
            'stage': {'stage': 'implemented'},
            'note': {'note': 'another note'},
        }
        for field, change in cases.items():
            with self.subTest(field=field):
                response = self.refused({**request, 'op_id': f'conflict-{field}', **change}, 'delivery-conflict')
                self.assertIn(field, response['errors'][0]['problem'])
        with self.subTest(field='sha256'):
            Path(prepared['result_path']).write_bytes(original + b'an extra line\n')
            response = self.refused({**request, 'op_id': 'conflict-bytes'}, 'delivery-conflict')
            self.assertIn('sha256', response['errors'][0]['problem'])
            Path(prepared['result_path']).write_bytes(original)

    def test_an_earlier_attempt_cannot_be_delivered(self):
        prepared = self.prepare()
        self.write_result(prepared)
        self.ok(self.deliver_request(outcome='failed'))
        self.prepare(op_id='prep-0002', assignment='build-it')
        self.refused(self.deliver_request(op_id='deliver-02', outcome='failed'), 'superseded-attempt')
        self.refused(self.deliver_request(op_id='deliver-03', attempt=1, outcome='blocked', note='other'), 'superseded-attempt')

    def test_a_result_without_the_completion_marker_or_through_a_symlink_is_refused(self):
        prepared = self.prepare()
        self.write_result(prepared, marker=False)
        self.refused(self.deliver_request(outcome='failed'), 'result-incomplete')
        target = self.repo.parent / (self.repo.name + '-real.md')
        self.addCleanup(lambda: target.unlink(missing_ok=True))
        self.write_result({**prepared, 'result_path': str(target)})
        os.unlink(prepared['result_path']); Path(prepared['result_path']).symlink_to(target)
        self.refused(self.deliver_request(op_id='deliver-02', outcome='failed'), 'result-is-symlink')

    def test_an_untrailered_commit_is_accepted_and_reported(self):
        prepared = self.prepare()
        sha = self.work(prepared, trailer=False)
        delivered = self.ok(self.deliver_request(commits=[sha]))
        self.assertEqual(delivered['untrailered_commits'], [sha])
        self.assertEqual(self.doc()['plan']['tasks'][0]['commits'], [sha])

    def test_the_retained_copy_holds_the_delivered_bytes(self):
        prepared, sha, request, delivered = self.delivered()
        retained = self.repo / 'bionic' / delivered['retained']
        self.assertEqual(retained.read_bytes(), Path(prepared['result_path']).read_bytes())
        self.assertEqual(self.doc()['assignments'][0]['delivery']['sha256'], delivered['sha256'])


class ConflictRecoveryTests(OpsBase):
    def dispatch(self, item, **fills):
        request = {**item['request'], **{key: fills.get(key, FILLS[key]) for key in item['caller_fills']}}
        return self.ok(request)

    def done_delivery(self, cid=None):
        prepared = self.prepare()
        sha = self.work(prepared)
        request = self.deliver_request(commits=[sha])
        self.ok(request)
        return prepared, sha, request

    def conflict(self, request, op_id='conflict-01'):
        return self.refused({**request, 'op_id': op_id, 'outcome': 'blocked'}, 'delivery-conflict')['errors'][0]['recovery']

    def test_recovery_in_the_current_phase_reopens_and_dispatches_a_new_assignment(self):
        prepared, sha, request = self.done_delivery()
        recovery = self.conflict(request)
        self.assertEqual(recovery[0]['argv'][-4:], ['--task-id', 'build-it', '--state', 'pending'])
        self.assertEqual(recovery[1]['request'], {'op': 'prepare-dispatch', 'task_id': 'build-it', 'role': 'developer', 'host': 'claude-code'})
        self.lowlevel(recovery[0])
        self.assertEqual(self.doc()['plan']['tasks'][0]['status'], 'pending')
        fresh = self.dispatch(recovery[1], assignment_text=TEXT)
        self.assertEqual((fresh['assignment'], fresh['attempt']), ('build-it-2', 1))
        self.assertEqual(self.doc()['plan']['tasks'][0]['status'], 'active')

    def test_a_pending_or_blocked_task_gets_only_the_dispatch(self):
        prepared = self.prepare()
        self.write_result(prepared)
        request = self.deliver_request(outcome='blocked', note='waiting')
        self.ok(request)
        recovery = self.refused({**request, 'op_id': 'conflict-01', 'outcome': 'failed'}, 'delivery-conflict')['errors'][0]['recovery']
        self.assertEqual([r['request']['op'] for r in recovery], ['prepare-dispatch'])
        self.dispatch(recovery[0], assignment_text=TEXT)

    def dev_fixture(self):
        """An iterate cycle (pass limit 2, no decision gate) in Build with one task, as a version-3 record."""
        doc = create(self.repo, 'iterate', 'Answer', 'Return 2', ['src'], ['answer is 2'], 'builder', 'tester')
        mutate(self.repo, doc['id'], 'task-add', task={'id': 'build-it', 'phase': 'build', 'description': 'set the answer',
                                                     'depends_on': [], 'status': 'pending', 'expected_evidence': ['commit']})
        path = self.record_path(doc['id'])
        raw = json.loads(path.read_text())
        raw.update(schema_version=3, phase='build', **{**cycle_ops.v3_fields(), 'revision': 1})
        validate(raw)
        path.write_text(json.dumps(raw))
        return doc['id']

    def test_recovery_after_the_phase_advanced_returns_to_build_in_a_new_pass(self):
        self.cid = self.dev_fixture()
        prepared, sha, request = self.done_delivery()
        mutate(self.repo, self.cid, 'advance')
        self.assertEqual(self.doc()['phase'], 'verify')
        recovery = self.conflict(request)
        self.assertEqual([r['argv'][6] if 'argv' in r else r['request']['op'] for r in recovery],
                         ['return', 'task', 'prepare-dispatch'])
        self.lowlevel(recovery[0], **{'--improved': 'built it', '--unresolved': 'a changed result', '--next-change': 'redo the task',
                                      '--justification': 'the delivery was wrong', '--progress': 'yes'})
        self.assertEqual((self.doc()['pass'], self.doc()['phase']), (2, 'build'))
        self.lowlevel(recovery[1])
        fresh = self.dispatch(recovery[2], assignment_text=TEXT)
        self.assertEqual((fresh['assignment'], fresh['attempt']), ('build-it-2', 1))

    def test_a_quick_fix_with_its_pass_used_recovers_through_pause_or_owner_exception(self):
        prepared, sha, request = self.done_delivery()
        mutate(self.repo, self.cid, 'advance')
        self.assertEqual((self.doc()['phase'], self.doc()['pass'], self.doc()['pass_limit']), ('verify', 1, 1))
        recovery = self.conflict(request)
        self.assertEqual(recovery[0]['argv'][6], 'pause'); self.assertEqual(recovery[0]['caller_fills'], ['--reason'])
        self.assertEqual(recovery[1]['request'], {'op': 'owner-exception'})
        self.assertEqual(recovery[1]['caller_fills'], ['op_id', 'quote', 'conversation', 'date'])
        self.assert_validates(recovery)
        self.lowlevel(recovery[0], **{'--reason': 'the delivery conflicts and the pass limit allows no return'})
        self.assertEqual(self.doc()['status'], 'paused')


class ReplayTests(OpsBase):
    def test_a_deliver_replay_after_the_bytes_changed_is_refused(self):
        prepared = self.prepare()
        sha = self.work(prepared)
        request = self.deliver_request(commits=[sha])
        self.ok(request)
        Path(prepared['result_path']).write_text(Path(prepared['result_path']).read_text() + 'tampered\n')
        response = self.refused(request, 'delivery-conflict')
        self.assertIn('the result file changed', response['errors'][0]['problem'])

    def test_after_finish_removed_the_source_a_deliver_replays_from_the_verified_retained_copy(self):
        prepared = self.prepare()
        sha = self.work(prepared)
        request = self.deliver_request(commits=[sha])
        delivered = self.ok(request)
        self.to_reflect()
        revision = self.ok({'op': 'inspect'})['revision']
        self.ok({'op': 'finish', 'op_id': 'finish-001', 'expect_revision': revision, 'lessons': ['l'], 'remaining': ['none']})
        self.assertFalse(Path(prepared['result_path']).exists())
        before = self.record_path().read_bytes()
        again = self.ok(request)
        self.assertEqual((again['replayed'], again['changed'], again['sha256']), (True, False, delivered['sha256']))
        self.assertEqual(self.record_path().read_bytes(), before)
        retained = self.repo / 'bionic' / delivered['retained']
        retained.write_text(retained.read_text() + 'tampered\n')
        response = self.refused(request, 'delivery-conflict')
        self.assertIn('the retained copy changed', response['errors'][0]['problem'])

    def prepare_request(self, op_id='prep-0001', **extra):
        return {'op': 'prepare-dispatch', 'op_id': op_id, 'task_id': 'build-it', 'role': 'developer', 'host': 'claude-code', 'assignment_text': TEXT, **extra}

    def test_prepare_dispatch_replays_return_no_invocation_once_the_attempt_moved_on(self):
        self.prepare()
        self.ok({'op': 'attach-execution', 'op_id': 'attach-001', 'assignment': 'build-it', 'attempt': 1, 'handle': 'h1'})
        running = self.ok(self.prepare_request())
        self.assertEqual((running['replayed'], running['attempt_state']), (True, 'running'))
        self.assertNotIn('invocation', running)
        self.ok(self.lost_request())
        lost = self.ok(self.prepare_request())
        self.assertEqual(lost['attempt_state'], 'lost'); self.assertNotIn('invocation', lost)
        second = self.prepare(op_id='prep-0002', assignment='build-it')
        self.assertEqual(second['attempt'], 2)
        superseded = self.ok(self.prepare_request())
        self.assertEqual(superseded['attempt_state'], 'superseded'); self.assertNotIn('invocation', superseded)
        # The second reservation, still reserved, rebuilds its invocation.
        rebuilt = self.ok(self.prepare_request('prep-0002', assignment='build-it'))
        self.assertEqual(rebuilt['invocation'], second['invocation'])

    def lost_request(self):
        return self.lost(evidence={'kind': 'terminal-status', 'detail': 'killed'})

    def test_prepare_dispatch_replay_after_pause_returns_no_invocation(self):
        self.prepare()
        mutate(self.repo, self.cid, 'pause', reason='owner pause')
        again = self.ok(self.prepare_request())
        self.assertEqual((again['replayed'], again['cycle_status'], again['attempt_state']), (True, 'paused', 'reserved'))
        self.assertNotIn('invocation', again)

    def test_prepare_dispatch_replay_after_a_low_level_owner_complete_returns_no_invocation(self):
        self.prepare()
        mutate(self.repo, self.cid, 'owner-complete', owner=OWNER_CLOSE)
        again = self.ok(self.prepare_request())
        self.assertEqual((again['replayed'], again['cycle_status']), (True, 'completed'))
        self.assertNotIn('invocation', again)


class CrashTests(OpsBase):
    def test_a_failure_between_the_retained_copy_and_the_save_leaves_the_record_unchanged(self):
        prepared = self.prepare()
        sha = self.work(prepared)
        request = self.deliver_request(commits=[sha])
        before = self.record_path().read_bytes()
        retained = self.repo / 'bionic/cycles' / self.cid / 'results/build-it-attempt-1.md'
        with patch.object(cycle_ops, 'save', side_effect=RuntimeError('crash before the save')):
            with self.assertRaises(RuntimeError):
                cycle_ops.run(self.repo, self.cid, request)
        self.assertEqual(self.record_path().read_bytes(), before)
        first = retained.read_bytes()
        self.assertEqual(first, Path(prepared['result_path']).read_bytes())
        # The worker rewrote its result; the retry overwrites the copy.
        self.write_result(prepared); Path(prepared['result_path']).write_text(Path(prepared['result_path']).read_text().replace('Answer set', 'Answer finally set'))
        delivered = self.ok(request)
        self.assertEqual(retained.read_bytes(), Path(prepared['result_path']).read_bytes())
        self.assertNotEqual(retained.read_bytes(), first)
        self.assertEqual(self.doc()['assignments'][0]['delivery']['sha256'], delivered['sha256'])

    def test_a_refused_done_delivery_reports_the_task_update_failure_with_the_other_errors_and_writes_nothing(self):
        prepared = self.prepare()
        sha = self.work(prepared)
        retained = self.repo / 'bionic/cycles' / self.cid / 'results/build-it-attempt-1.md'
        self.add_task('dependency')
        raw = json.loads(self.record_path().read_text())
        next(t for t in raw['plan']['tasks'] if t['id'] == 'build-it')['depends_on'] = ['dependency']
        self.record_path().write_text(json.dumps(raw))
        request = self.deliver_request(commits=[sha], evidence=['bionic/evidence/missing.md'])
        response = self.refused(request, 'evidence-missing', 'task-refused')
        self.assertIn('dependencies', next(e for e in response['errors'] if e['code'] == 'task-refused')['problem'])
        self.assertFalse(retained.exists(), 'a refused deliver left a retained copy')
        # With the task update as the only error, the refusal still writes neither the retained copy nor the record.
        self.refused({**request, 'op_id': 'deliver-02', 'evidence': []}, 'task-refused')
        self.assertFalse(retained.exists(), 'a refused deliver left an orphan retained copy')

    def test_an_unresolved_commit_does_not_hide_the_task_update_failure(self):
        prepared = self.prepare()
        sha = self.work(prepared)
        self.add_task('dependency')
        raw = json.loads(self.record_path().read_text())
        next(t for t in raw['plan']['tasks'] if t['id'] == 'build-it')['depends_on'] = ['dependency']
        self.record_path().write_text(json.dumps(raw))
        response = self.refused(self.deliver_request(commits=[sha, 'no-such-commit']), 'commit-unresolved', 'task-refused')
        self.assertIn('dependencies', next(e for e in response['errors'] if e['code'] == 'task-refused')['problem'])

    def test_a_vanished_results_directory_is_replaced_and_old_reservations_report_it(self):
        self.add_task('build-two')
        first = self.prepare()
        old = Path(first['result_path']).parent
        old.rmdir()
        second = self.prepare(op_id='prep-0002', task_id='build-two')
        new = Path(second['result_path']).parent
        self.assertNotEqual(new, old); self.assertTrue(new.is_dir())
        self.assertEqual(self.doc()['results_dir'], str(new))
        seen = self.ok({'op': 'inspect'})['assignments']
        by_task = {a['task']: a for a in seen}
        self.assertEqual(by_task['build-it']['problem'], 'result-path-missing')
        self.assertEqual(by_task['build-it']['result_path'], first['result_path'])
        self.assertNotIn('problem', by_task['build-two'])

    def test_recreating_a_recorded_directory_uses_mode_0700(self):
        first = self.prepare()
        directory = Path(first['result_path']).parent
        directory.rmdir()
        previous = os.umask(0)   # a mode that came from the umask would show here
        try:
            again = self.ok({'op': 'prepare-dispatch', 'op_id': 'prep-0001', 'task_id': 'build-it', 'role': 'developer',
                             'host': 'claude-code', 'assignment_text': TEXT})
        finally:
            os.umask(previous)
        self.assertIn('invocation', again)
        self.assertEqual(directory.stat().st_mode & 0o777, 0o700)

    def test_recreating_refuses_a_symlink_or_a_file_in_place_of_the_directory(self):
        first = self.prepare()
        directory = Path(first['result_path']).parent
        directory.rmdir()
        elsewhere = self.repo.parent / (self.repo.name + '-elsewhere'); elsewhere.mkdir()
        self.addCleanup(elsewhere.rmdir)
        directory.symlink_to(elsewhere)
        self.addCleanup(lambda: directory.unlink() if directory.is_symlink() else None)
        request = {'op': 'prepare-dispatch', 'op_id': 'prep-0001', 'task_id': 'build-it', 'role': 'developer', 'host': 'claude-code', 'assignment_text': TEXT}
        self.refused(request, 'result-path-symlink')
        directory.unlink()
        directory.write_text('not a directory')
        self.addCleanup(lambda: directory.unlink() if directory.is_file() else None)
        self.refused(request, 'result-path-not-directory')


class TaskRangeTests(OpsBase):
    def side_commit(self, name, base, task='build-it'):
        """A trailered commit on a side branch off `base`; HEAD returns to the branch it left."""
        self.git('checkout', '-q', '-b', f'side-{name}', base)
        sha = self.commit_file(f'src/{name}.py', f'{name} = 1\n', task)
        self.git('checkout', '-q', '-')
        return sha

    def test_a_partial_commit_of_a_lost_attempt_must_be_delivered_by_the_next_one(self):
        prepared = self.prepare()
        partial = self.checkpoint_work(prepared, marker=False, body='answer = 3\n')
        self.ok(self.lost(evidence=OWNER))
        second = self.prepare(op_id='prep-0002', assignment='build-it')
        side = self.side_commit('side', self.base)
        self.write_result(second)
        response = self.refused(self.deliver_request(attempt=2, commits=[side]), 'undelivered-task-commit')
        self.assertEqual(response['errors'][0]['observed'], partial)
        final = self.commit_file('src/a.py', 'answer = 2\n')
        delivered = self.ok(self.deliver_request(op_id='deliver-02', attempt=2, commits=[final]))
        self.assertEqual(delivered['status'], 'done')

    def test_the_range_applies_to_a_done_delivery_only(self):
        prepared = self.prepare()
        self.checkpoint_work(prepared, marker=False, body='answer = 3\n')
        self.ok(self.lost(evidence=OWNER))
        second = self.prepare(op_id='prep-0002', assignment='build-it')
        self.write_result(second)
        reported = self.ok(self.deliver_request(attempt=2, outcome='blocked', note='the task needs a decision'))
        self.assertEqual(reported['status'], 'blocked')

    def test_the_delivered_range_is_a_union_over_non_linear_commits(self):
        prepared = self.prepare()
        main_commit = self.commit_file('src/a.py', 'answer = 2\n')
        side = self.side_commit('side', self.base)
        self.git('merge', '--no-ff', '-q', 'side-side', '-m', 'merge the side work')
        self.write_result(prepared)
        response = self.refused(self.deliver_request(commits=[main_commit]), 'undelivered-task-commit')
        self.assertEqual(response['errors'][0]['observed'], side)
        delivered = self.ok(self.deliver_request(op_id='deliver-02', commits=[main_commit, side]))
        self.assertEqual(delivered['status'], 'done')
        self.assertEqual(sorted(self.doc()['plan']['tasks'][0]['commits']), sorted([main_commit, side]))

    def test_an_unintegrated_delivered_commit_is_accepted_because_the_check_sees_head_only(self):
        prepared = self.prepare()
        side = self.side_commit('branch', self.base)
        head = self.git('rev-parse', 'HEAD')
        self.assertEqual(head, self.base)
        self.write_result(prepared)
        delivered = self.ok(self.deliver_request(commits=[side]))
        self.assertEqual(delivered['untrailered_commits'], [])
        self.assertEqual(self.doc()['plan']['tasks'][0]['commits'], [side])
        merged = subprocess_ok(self.repo, 'merge-base', '--is-ancestor', side, 'HEAD')
        self.assertFalse(merged, 'the delivered commit is not on HEAD')


def subprocess_ok(repo, *args):
    import subprocess
    return subprocess.run(['git', '-C', str(repo), *args], capture_output=True).returncode == 0


class HandleLessHostTests(OpsBase):
    def test_a_reserved_attempt_on_a_handle_less_host_delivers_without_attach(self):
        prepared = self.prepare(host='opencode')
        self.assertIsNone(prepared['invocation']['attach'])
        seen = self.ok({'op': 'inspect'})
        self.assertEqual(seen['assignments'][0]['recovery'], ['await-marker', 'deliver', 'mark-lost'])
        self.assertEqual([a for a in seen['actions'] if a.get('request', {}).get('op') == 'attach-execution'], [])
        sha = self.work(prepared)
        delivered = self.ok(self.deliver_request(commits=[sha]))
        self.assertEqual(delivered['status'], 'done')

    def test_attach_after_the_attempt_finished_is_refused_without_a_write(self):
        prepared = self.prepare(host='opencode')
        self.write_result(prepared)
        self.ok(self.deliver_request(outcome='failed'))
        self.refused({'op': 'attach-execution', 'op_id': 'attach-001', 'assignment': 'build-it', 'attempt': 1, 'handle': 'h1'}, 'attempt-not-open')


if __name__ == '__main__':
    unittest.main()
