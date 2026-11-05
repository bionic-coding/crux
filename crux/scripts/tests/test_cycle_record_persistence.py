"""Record persistence and request handling (IDR lean-workflow-traps-and-recovery approaches 1, 2, 3, 7, 8, 12 and 13).

Dispatch and delivery operations commit the record; a release delivery that leaves every step done finishes the
cycle; a blocked delivery keeps its stop and inspect offers the pause beside the route; requests read from a file;
inspect names every unmet Build check; the preamble names the engine and where the role runs.

Every test builds its own temporary git repository with the docs tree visible to git."""
import contextlib
import io
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cycle
import cycle_hosts
import cycle_ops
from cycle_workflow import create, load, mutate
import test_cycle_commit as tc


class DispatchCommitTests(tc.CommitBase):
    def test_prepare_dispatch_commits_only_the_record(self):
        # An unrelated staged path stays outside this task's owned src/ scope.
        (self.repo / 'unrelated.py').write_text('x = 1\n')
        self.git('add', 'unrelated.py')
        prepared = self.prepare()
        record = prepared['record_commit']
        self.assertTrue(record['changed'], record)
        self.assertEqual(record['commit'], self.head())
        self.assertEqual(self.pending(), [])
        self.assertTrue(all(f.startswith('bionic/') for f in self.commit_files()), self.commit_files())
        self.assertIn('record: prepare-dispatch build-it attempt 1', self.message())
        self.assertEqual(self.git('diff', '--cached', '--name-only').splitlines(), ['unrelated.py'])

    def test_attach_execution_deliver_and_mark_lost_each_commit(self):
        prepared = self.prepare(mode='background')
        attached = self.ok({'op': 'attach-execution', 'op_id': 'attach-001', 'assignment': 'build-it', 'attempt': 1, 'handle': 'agent-1'})
        self.assertTrue(attached['record_commit']['changed'], attached)
        self.assertEqual(self.pending(), [])
        lost = self.ok({'op': 'mark-lost', 'op_id': 'lost-0001', 'assignment': 'build-it', 'attempt': 1, 'note': 'host reported killed',
                        'evidence': {'kind': 'terminal-status', 'detail': 'killed'}})
        self.assertTrue(lost['record_commit']['changed'], lost)
        self.assertIn('record: mark-lost build-it attempt 1', self.message())
        self.assertEqual(self.pending(), [])
        second = self.prepare(op_id='prep-0002', assignment=prepared['assignment'])
        sha = self.work(second)
        delivered = self.ok({'op': 'deliver', 'op_id': 'deliver-01', 'assignment': 'build-it', 'attempt': 2, 'outcome': 'done', 'commits': [sha]})
        self.assertTrue(delivered['record_commit']['changed'], delivered)
        self.assertIn('record: deliver build-it attempt 2', self.message())
        self.assertEqual(self.pending(), [])

    def test_a_deferred_delivery_commit_is_caught_up_by_its_replay(self):
        """The interrupted tail: the record is written and its commit deferred; a replay commits it and applies nothing."""
        prepared = self.prepare()
        sha = self.work(prepared)
        request = {'op': 'deliver', 'op_id': 'deliver-01', 'assignment': 'build-it', 'attempt': 1, 'outcome': 'done', 'commits': [sha]}
        with self.suite_running():
            first = self.ok(request)
        self.assertEqual((first['record_commit']['changed'], first['record_commit']['deferred']), (False, 'full-suite-running'))
        self.assertTrue(self.pending())
        revision = self.revision()
        again = self.ok(request)
        self.assertTrue(again['replayed'])
        self.assertTrue(again['record_commit']['changed'], again)
        self.assertEqual(self.revision(), revision, 'the replay applied nothing')
        self.assertEqual(self.pending(), [])


class ReleaseFinishTests(tc.CommitBase):
    def release(self):
        doc = create(self.repo, 'release', 'Beta', 'Ship beta', ['src', 'bionic/log.md'], ['beta'], 'releaser', 'tester', release_list='beta')
        self.addCleanup(self.cleanup_release, doc['id'])
        for task in doc['plan']['tasks'][:-1]:
            doc = mutate(self.repo, doc['id'], 'task', task_id=task['id'], state='done')
        return doc['id']

    def pending_of(self, cid):
        return self.git('status', '--porcelain', '--untracked-files=all', '--', f'bionic/cycles/{cid}', 'bionic/queue').splitlines()

    def cleanup_release(self, cid):
        directory = load(self.repo, cid).get('results_dir')
        if directory and Path(directory).is_dir():
            for path in Path(directory).iterdir():
                path.unlink()
            Path(directory).rmdir()

    def deliver_record(self, cid, op_id='deliver-rec1'):
        prepared = self.ok({'op': 'prepare-dispatch', 'op_id': 'prep-rec01', 'task_id': 'record', 'role': 'developer', 'host': 'claude-code',
                            'assignment_text': 'Record the release.'}, cid=cid)
        (self.repo / 'bionic/log.md').write_text('released\n')
        self.git('add', 'bionic/log.md')
        self.git('commit', '-q', '-m', 'record the release\n\nCycle-Task: record')
        sha = self.head()
        self.write_result(prepared)
        return {'op': 'deliver', 'op_id': op_id, 'assignment': prepared['assignment'], 'attempt': 1, 'outcome': 'done', 'commits': [sha]}

    def test_delivering_the_last_step_completes_the_release_cycle(self):
        cid = self.release()
        response = self.ok(self.deliver_record(cid), cid=cid)
        self.assertTrue(response['finish']['ok'], response['finish'])
        self.assertEqual(response['finish']['status'], 'completed')
        self.assertEqual(load(self.repo, cid)['status'], 'completed')
        self.assertEqual(self.pending_of(cid), [])
        self.assertIn(' record: finish', self.message())

    def test_a_crash_between_delivery_and_finish_is_completed_by_the_replay(self):
        cid = self.release()
        request = self.deliver_record(cid)
        original = cycle_ops.release_finish
        cycle_ops.release_finish = lambda *a, **k: {}  # the process dies after the delivery's commit
        try:
            first = self.ok(request, cid=cid)
        finally:
            cycle_ops.release_finish = original
        self.assertNotIn('finish', first)
        self.assertEqual(load(self.repo, cid)['status'], 'active')
        offered = [a for a in self.ok({'op': 'inspect'}, cid=cid)['actions'] if a.get('request', {}).get('op') == 'finish']
        self.assertEqual(len(offered), 1, 'inspect offers the finish')
        delivered = len(load(self.repo, cid)['operations'])
        again = self.ok(request, cid=cid)
        self.assertTrue(again['replayed'])
        self.assertTrue(again['finish']['ok'], again['finish'])
        self.assertEqual(load(self.repo, cid)['status'], 'completed')
        self.assertEqual(len(load(self.repo, cid)['operations']), delivered + 1, 'only the finish was added')

    def test_a_refused_finish_leaves_the_delivery_committed_and_reported(self):
        cid = self.release()
        request = self.deliver_record(cid)
        (self.repo / 'src/a.py').write_text('uncommitted = 1\n')  # a scope change finish refuses
        response = self.ok(request, cid=cid)
        self.assertFalse(response['finish']['ok'], response['finish'])
        self.assertTrue(response['finish']['errors'])
        self.assertEqual(load(self.repo, cid)['status'], 'active')
        self.assertTrue(response['record_commit']['changed'] or response['record_commit']['deferred'] is None)
        self.assertEqual(self.pending_of(cid), [], 'the delivery is committed')

    def test_a_delivery_that_leaves_a_step_open_does_not_finish(self):
        doc = create(self.repo, 'release', 'Beta', 'Ship beta', ['src', 'bionic/log.md'], ['beta'], 'releaser', 'tester', release_list='beta')
        self.addCleanup(self.cleanup_release, doc['id'])
        prepared = self.ok({'op': 'prepare-dispatch', 'op_id': 'prep-prep01', 'task_id': 'prep', 'role': 'developer', 'host': 'claude-code',
                            'assignment_text': 'Prepare.'}, cid=doc['id'])
        self.write_result(prepared)
        response = self.ok({'op': 'deliver', 'op_id': 'deliver-p1', 'assignment': prepared['assignment'], 'attempt': 1, 'outcome': 'done'}, cid=doc['id'])
        self.assertNotIn('finish', response)


class BlockedStopTests(tc.CommitBase):
    def blocked(self, **extra):
        prepared = self.prepare()
        self.write_result(prepared)
        return self.ok({'op': 'deliver', 'op_id': 'deliver-b1', 'assignment': 'build-it', 'attempt': 1, 'outcome': 'blocked', **extra})

    def pauses(self):
        return [a for a in self.ok({'op': 'inspect'})['actions'] if 'argv' in a and 'pause' in a['argv']]

    def test_a_stop_is_stored_and_no_pause_is_added(self):
        self.blocked(stop='owner-decision')
        self.assertEqual(load(self.repo, self.cid)['assignments'][0]['delivery']['stop'], 'owner-decision')
        self.assertEqual(self.pauses(), [])

    def test_a_stopless_blocked_delivery_lists_the_pause(self):
        self.blocked()
        self.assertNotIn('stop', load(self.repo, self.cid)['assignments'][0]['delivery'])
        found = self.pauses()
        self.assertEqual(len(found), 1, found)
        self.assertEqual(found[0]['caller_fills'], ['--reason'])

    def test_a_repeat_naming_another_stop_conflicts(self):
        self.blocked(stop='approval-wait')
        response = self.refused({'op': 'deliver', 'op_id': 'deliver-b2', 'assignment': 'build-it', 'attempt': 1, 'outcome': 'blocked'}, 'delivery-conflict')
        self.assertIn('stop', response['errors'][0]['problem'])


class RequestFormTests(tc.CommitBase):
    def run_cli(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cycle.main(['--repo-root', str(self.repo), '--compact', *argv])
        return code, json.loads(out.getvalue())

    def test_an_op_reads_its_request_from_any_regular_file(self):
        path = self.repo.parent / (self.repo.name + '-outside.json')
        path.write_text(json.dumps({'op': 'commit-record', 'op_id': 'commit-file1'}))
        self.addCleanup(path.unlink)
        code, response = self.run_cli('op', self.cid, '--file', str(path))
        self.assertEqual(code, 0, response)
        self.assertEqual(response['op_id'], 'commit-file1')

    def test_a_directory_is_refused_as_unreadable(self):
        code, response = self.run_cli('op', self.cid, '--file', str(self.repo))
        self.assertEqual((code, response['errors'][0]['code']), (1, 'request-unreadable'))

    def test_an_invalid_payload_names_the_file_form(self):
        code, response = self.run_cli('op', self.cid, '--json', "{'op': 'inspect'}")
        self.assertEqual(code, 1)
        error = response['errors'][0]
        self.assertEqual(error['code'], 'invalid-request')
        self.assertIn('--file PATH', error['problem'])
        self.assertEqual(error['recovery'][0]['argv'][-3:], ['op', self.cid, '--file'])

    def test_friction_reads_a_file(self):
        path = self.repo.parent / (self.repo.name + '-friction.json')
        path.write_text(json.dumps({'who': 'dev-lead', 'what': 'quoting', 'cost': 'one retry', 'category': 'tooling', 'fix': 'use --file'}))
        self.addCleanup(path.unlink)
        code, response = self.run_cli('friction', self.cid, '--file', str(path))
        self.assertEqual(code, 0, response)
        self.assertEqual(response['id'], 'F1')


class UnmetListTests(tc.CommitBase):
    def declare(self, count):
        names = [f'check-{n:02d}' for n in range(count)]
        mutate(self.repo, self.cid, 'checks', checks=names, phase='build')
        return names

    def build_problem(self):
        seen = self.ok({'op': 'inspect'})
        return next(i['problem'] for i in seen['unmet']['next'] if i['requirement'] == 'build-checks')

    def test_inspect_names_every_unmet_build_check(self):
        names = self.declare(3)
        problem = self.build_problem()
        for name in names:
            self.assertIn(f'missing passing evidence for {name}', problem)

    def test_a_cut_list_says_so_and_gives_the_count(self):
        names = self.declare(25)
        problem = self.build_problem()
        self.assertIn(names[19], problem)
        self.assertNotIn(names[20], problem)
        self.assertIn('and 5 more (25 in all; the list is cut)', problem)

    def test_unfinished_tasks_are_named(self):
        seen = self.ok({'op': 'inspect'})
        problem = next(i['problem'] for i in seen['unmet']['next'] if i['requirement'] == 'phase-tasks')
        self.assertIn('build-it (pending)', problem)


class PreambleTests(tc.CommitBase):
    def prompt(self, prepared):
        return prepared['invocation']['parameters']['prompt']

    def test_the_preamble_names_the_engine_path(self):
        prompt = self.prompt(self.prepare())
        self.assertIn(f'Cycle engine that reserved this attempt: {cycle_ops.CYCLE_SCRIPT}.', prompt)
        self.assertTrue(cycle_ops.CYCLE_SCRIPT.is_absolute())

    def test_an_isolating_role_names_its_integration_owner(self):
        prepared = self.prepare(integration_owner='dev-lead')
        isolation = prepared['invocation']['isolation']
        self.assertEqual((isolation['worktree'], isolation['integration_owner']), (True, 'dev-lead'))
        self.assertIn('isolated git worktree', self.prompt(prepared))
        self.assertIn('dev-lead integrates them onto the main checkout', self.prompt(prepared))

    def test_without_an_owner_the_delegator_integrates(self):
        prepared = self.prepare()
        self.assertEqual(prepared['invocation']['isolation']['integration_owner'], 'the delegator that dispatched you')
        self.assertIn('the delegator that dispatched you integrates them', self.prompt(prepared))

    def test_a_host_that_drops_isolation_runs_in_the_main_checkout(self):
        prepared = self.prepare(host='codex')
        isolation = prepared['invocation']['isolation']
        self.assertEqual((isolation['worktree'], isolation['integration_owner']), (False, None))
        self.assertIn('drops', isolation['basis'])
        self.assertIn('You run in the main checkout on this host', prepared['invocation']['parameters']['message'])

    def test_a_role_with_no_isolation_runs_in_the_main_checkout(self):
        found = cycle_hosts.isolation('claude-code', 'reviewer')
        self.assertEqual((found['worktree'], found['integration_owner']), (False, None))
        self.assertEqual(cycle_hosts.role_isolation('developer'), 'worktree')


if __name__ == '__main__':
    unittest.main()
