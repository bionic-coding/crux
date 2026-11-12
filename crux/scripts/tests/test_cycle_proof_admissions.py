"""Execution proof admissions: adjacent checkpoints, delivered cycle-task source and merges, streams.

Covers the intended evidence of IDR execution-proof-admissions revision 5.
"""
import contextlib
from copy import deepcopy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle
import cycle_execution
import cycle_ops
from cycle_workflow import CycleError, load, mutate, tree, validate
import test_cycle_slice as fixtures

PLUGIN = Path(__file__).resolve().parents[2]


class AdmissionBase(fixtures.SliceBase):
    counter = 0

    def op_id(self, stem):
        type(self).counter += 1
        return f'{stem}-{type(self).counter:06d}'

    def add_task(self, ident, **extra):
        mutate(self.repo, self.cid, 'task-add', task={'id': ident, 'phase': 'build', 'description': ident,
                                                     'depends_on': [], 'status': 'pending',
                                                     'expected_evidence': ['commit'], **extra})

    def reserve(self, task, role='developer', **extra):
        return self.ok({'op': 'prepare-dispatch', 'op_id': self.op_id('prep'), 'task_id': task, 'role': role,
                        'host': 'claude-code', 'assignment_text': fixtures.TEXT, **extra})

    def check(self, prepared, **extra):
        return self.ok({'op': 'execution-check', 'op_id': self.op_id('check'), 'assignment': prepared['assignment'],
                        'attempt': prepared['attempt'], **extra})

    def check_refused(self, prepared, code, **extra):
        before = self.record_path().read_bytes()
        status, response = self.op({'op': 'execution-check', 'op_id': self.op_id('check'),
                                    'assignment': prepared['assignment'], 'attempt': prepared['attempt'], **extra})
        self.assertEqual(status, 1, response)
        self.assertEqual([e['code'] for e in response['errors']], [code])
        self.assertEqual(self.record_path().read_bytes(), before)
        return response['errors'][0]

    def commit(self, name, body, task, *, root=None, extra=()):
        root = root or self.repo
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)
        subprocess.run(['git', '-C', str(root), 'add', '-f', name, *extra], check=True, capture_output=True)
        message = f'{name}\n\nCycle-Task: {task}' if task else name
        subprocess.run(['git', '-C', str(root), 'commit', '-q', '-m', message], check=True, capture_output=True)
        return subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'], check=True, capture_output=True,
                              text=True).stdout.strip()

    def unit(self, prepared, name, body, *, root=None):
        """A checkpointed one-file commit by the reserved attempt."""
        extra = {'checkout': str(root)} if root else {}
        self.check(prepared, **extra)
        ((root or self.repo) / name).write_text(body)
        self.check(prepared, edited_paths=[name], **extra)
        sha = self.commit(name, body, prepared['task'], root=root)
        self.check(prepared, **extra)
        return sha

    def deliver(self, prepared, outcome, commits, **extra):
        self.write_result(prepared)
        return self.ok({'op': 'deliver', 'op_id': self.op_id('deliver'), 'assignment': prepared['assignment'],
                        'attempt': prepared['attempt'], 'outcome': outcome, 'commits': commits, **extra})

    def entry(self, task='build-it', base=None, attempt=1):
        return {'id': task, 'task': task, 'attempt': attempt, 'base': base or self.base, 'delivery_token': 'f' * 32}

    def kinds(self, proof):
        return {row['sha']: row['kind'] for row in proof['commits']}

    def edit_record(self, change):
        path = self.record_path()
        raw = json.loads(path.read_text())
        change(raw)
        validate(raw)
        path.write_text(json.dumps(raw, indent=2, sort_keys=True) + '\n')


class AdjacentCheckpointTests(AdmissionBase):
    """Approach 1: record_commit defer keeps the source commit adjacent to its checkpoint."""

    def setUp(self):
        super().setUp()
        # Track the cycle record so the writer's record commits really land on HEAD.
        (self.repo / '.gitignore').write_text('*.lock\n__pycache__/\n')
        self.git('add', '.gitignore', 'bionic'); self.git('commit', '-q', '-m', 'track the record')
        self.base = self.git('rev-parse', 'HEAD')

    def staged(self):
        prepared = self.reserve('build-it')
        self.check(prepared)
        (self.repo / 'src/receipt.json').write_text('{"receipt": 1}\n')
        self.git('add', 'src/receipt.json')
        deferred = self.check(prepared, edited_paths=['src/receipt.json'], record_commit='defer')
        return prepared, deferred

    def test_deferred_record_commit_leaves_the_source_commit_adjacent(self):
        prepared, deferred = self.staged()
        self.assertEqual(deferred['record_commit']['deferred'], 'requested-adjacent-commit')
        self.assertEqual(deferred['record_commit']['request'], {'op': 'commit-record'})
        self.assertTrue(deferred['record_commit']['pending'])
        checkpoint_head = deferred['execution']['execution_head']
        self.assertEqual(self.git('rev-parse', 'HEAD'), checkpoint_head)
        self.git('commit', '-q', '--only', 'src/receipt.json', '-m', 'receipt\n\nCycle-Task: build-it')
        sha = self.git('rev-parse', 'HEAD')
        self.assertEqual(self.git('rev-parse', sha + '^'), checkpoint_head)
        self.ok({'op': 'commit-record', 'op_id': self.op_id('record')})
        proof = self.check(prepared)['execution']
        self.assertEqual(self.kinds(proof)[sha], 'same-attempt-commit')

    def test_a_replay_keeps_its_deferral(self):
        prepared = self.reserve('build-it')
        self.check(prepared)
        (self.repo / 'src/receipt.json').write_text('{"receipt": 1}\n')
        self.git('add', 'src/receipt.json')
        request = {'op': 'execution-check', 'op_id': 'replayed-deferral-1', 'assignment': prepared['assignment'],
                   'attempt': prepared['attempt'], 'edited_paths': ['src/receipt.json'], 'record_commit': 'defer'}
        first = self.ok(request)
        again = self.ok(request)
        self.assertTrue(again['replayed'])
        self.assertEqual(again['record_commit']['deferred'], 'requested-adjacent-commit')
        self.assertEqual(first['execution']['proof'], again['execution']['proof'])

    def test_an_intervening_record_commit_breaks_adjacency_but_not_admission(self):
        prepared, deferred = self.staged()
        checkpoint_head = deferred['execution']['execution_head']
        self.ok({'op': 'commit-record', 'op_id': self.op_id('record')})  # another role's record commit
        self.assertNotEqual(self.git('rev-parse', 'HEAD'), checkpoint_head)
        self.git('commit', '-q', '--only', 'src/receipt.json', '-m', 'receipt\n\nCycle-Task: build-it')
        sha = self.git('rev-parse', 'HEAD')
        self.assertNotEqual(self.git('rev-parse', sha + '^'), checkpoint_head)
        self.assertEqual(self.kinds(self.check(prepared)['execution'])[sha], 'same-attempt-commit')

    def test_without_defer_the_record_commit_lands_between(self):
        prepared = self.reserve('build-it')
        self.check(prepared)
        (self.repo / 'src/receipt.json').write_text('{"receipt": 1}\n')
        self.git('add', 'src/receipt.json')
        checked = self.check(prepared, edited_paths=['src/receipt.json'])
        self.assertTrue(checked['record_commit']['changed'])
        self.assertNotEqual(self.git('rev-parse', 'HEAD'), checked['execution']['execution_head'])


class CycleTaskSourceTests(AdmissionBase):
    """Approach 2: another done task's delivered work admits a retry whose base predates it."""

    def setUp(self):
        super().setUp()
        self.add_task('other')

    def retry_after(self, make_other):
        first = self.reserve('build-it')
        made = make_other()
        self.deliver(first, 'blocked', [])
        return made

    def delivered_other(self):
        other = self.reserve('other')
        sha = self.unit(other, 'src/b.py', 'b = 1\n')
        self.deliver(other, 'done', [sha])
        return sha

    def test_retry_admits_delivered_work_through_its_retained_proof(self):
        sha = self.retry_after(self.delivered_other)
        retried = self.reserve('build-it', assignment='build-it')
        self.assertEqual(retried['base'], self.base)
        row = next(r for r in retried['execution']['commits'] if r['sha'] == sha)
        self.assertEqual((row['kind'], row['provenance']['ground'], row['provenance']['task']),
                         ('cycle-task-source', 'retained-proof', 'other'))
        self.assertIn('proof', row['provenance'])

    def test_admitting_proof_in_execution_history_still_grounds(self):
        sha = self.retry_after(self.delivered_other)
        doc = load(self.repo, self.cid)
        other = next(e for e in doc['assignments'] if e['task'] == 'other')
        history = [*other.get('execution_history', []), other['execution']]
        admitting = [m for m in history if any(
            r['sha'] == sha and r['kind'] == 'same-attempt-commit'
            for r in json.loads((tree(self.repo).docs_root / m['proof']['path']).read_text())['commits'])]
        self.assertTrue(admitting)
        other['execution_history'], other['execution'] = admitting, None
        # Remove the trailer route so only the history proof can ground the commit.
        other['delivery']['commits'] = []
        proof = cycle_execution.prove(tree(self.repo), doc, self.entry())
        row = next(r for r in proof['commits'] if r['sha'] == sha)
        self.assertEqual((row['kind'], row['provenance']['ground']), ('cycle-task-source', 'retained-proof'))
        self.assertIn(row['provenance']['proof'], [m['proof'] for m in admitting])

    def test_undelivered_reserved_task_refuses_with_new_pass_route_and_fact(self):
        def undelivered():
            other = self.reserve('other')
            return self.unit(other, 'src/b.py', 'b = 1\n')
        sha = self.retry_after(undelivered)
        code, response = self.op({'op': 'prepare-dispatch', 'op_id': self.op_id('prep'), 'task_id': 'build-it',
                                  'role': 'developer', 'host': 'claude-code', 'assignment': 'build-it'})
        self.assertEqual(code, 1, response)
        error = response['errors'][0]
        self.assertEqual(error['code'], 'execution-foreign-source')
        self.assertEqual(error['observed']['fact']['task'], 'other')
        self.assertIn('ground (b)', error['observed']['fact']['fact'])
        route = error['recovery'][0]
        self.assertEqual(route['argv'][-4:], ['return', self.cid, '--execution-task', 'build-it'])
        self.assertEqual(route['purpose'], cycle_ops.NEW_PASS_ROUTE)
        self.assertNotIn('prepare-dispatch', json.dumps(error['recovery'][0]))
        self.assertEqual(error['observed']['commit'], sha)

    def test_own_trailer_commit_gets_no_fact(self):
        sha = self.retry_after(lambda: self.commit('src/a.py', 'answer = 7\n', 'build-it'))
        with self.assertRaises(cycle_execution.ExecutionError) as caught:
            cycle_execution.prove(tree(self.repo), load(self.repo, self.cid), self.entry())
        self.assertEqual((caught.exception.code, caught.exception.details['commit']), ('execution-foreign-source', sha))
        self.assertNotIn('fact', caught.exception.details)

    def test_ground_b_admits_a_commit_listed_only_as_current_delivery(self):
        def unchecked():
            other = self.reserve('other')
            sha = self.commit('src/b.py', 'b = 1\n', 'other')
            delivered = self.deliver(other, 'done', [sha])
            return sha, delivered
        sha, delivered = self.retry_after(unchecked)
        doc = load(self.repo, self.cid)
        other = next(e for e in doc['assignments'] if e['task'] == 'other')
        listed = json.loads((tree(self.repo).docs_root / other['execution']['proof']['path']).read_text())
        self.assertEqual(self.kinds(listed)[sha], 'current-delivery')
        row = next(r for r in cycle_execution.prove(tree(self.repo), doc, self.entry())['commits'] if r['sha'] == sha)
        self.assertEqual((row['kind'], row['provenance']['ground']), ('cycle-task-source', 'validated-delivery'))
        # A delivery observation whose range holds that commit still labels it current-delivery.
        observed = cycle_execution.prove(tree(self.repo), doc, self.entry(), delivery_commits=[sha])
        self.assertEqual(self.kinds(observed)[sha], 'current-delivery')

    def test_trailer_outside_the_delivered_range_refuses(self):
        self.retry_after(self.delivered_other)
        stray = self.commit('src/b.py', 'b = 2\n', 'other')
        with self.assertRaises(cycle_execution.ExecutionError) as caught:
            cycle_execution.prove(tree(self.repo), load(self.repo, self.cid), self.entry())
        self.assertEqual((caught.exception.code, caught.exception.details['commit']), ('execution-foreign-source', stray))
        self.assertNotIn('fact', caught.exception.details)  # the trailer's task is done
        code, response = self.op({'op': 'prepare-dispatch', 'op_id': self.op_id('prep'), 'task_id': 'build-it',
                                  'role': 'developer', 'host': 'claude-code', 'assignment': 'build-it'})
        self.assertEqual(response['errors'][0]['recovery'][0]['purpose'], cycle_ops.NEW_PASS_ROUTE)

    def test_damaged_reports(self):
        sha = self.retry_after(self.delivered_other)
        doc = load(self.repo, self.cid)
        delivery = next(e for e in doc['assignments'] if e['task'] == 'other')['delivery']
        report = tree(self.repo).docs_root / delivery['path']
        report.write_bytes(report.read_bytes() + b'damaged\n')
        # The grounding task's damaged report yields the refusal naming it.
        with self.assertRaises(cycle_execution.ExecutionError) as caught:
            cycle_execution.prove(tree(self.repo), doc, self.entry())
        self.assertEqual(caught.exception.code, 'execution-foreign-source')
        self.assertEqual([item['path'] for item in caught.exception.details['damaged_reports']], [delivery['path']])
        status, response = self.op({'op': 'prepare-dispatch', 'op_id': self.op_id('prep'), 'task_id': 'build-it',
                                    'role': 'developer', 'host': 'claude-code', 'assignment': 'build-it'})
        purposes = [route['purpose'] for route in response['errors'][0]['recovery']]
        self.assertIn(cycle_ops.DAMAGED_REPORT_NOTE, purposes)
        # A damaged report of a task that grounds no commit in the range refuses nothing.
        after = self.entry(base=self.git('rev-parse', 'HEAD'))
        self.assertTrue(self.git('merge-base', '--is-ancestor', sha, after['base']) == '')
        cycle_execution.prove(tree(self.repo), doc, after)


class CycleTaskMergeTests(AdmissionBase):
    """Approaches 2 and 4: a coordinating merge of another task's delivered work."""

    def setUp(self):
        super().setUp()
        self.add_task('other')
        self.add_task('integrator')
        directory = tempfile.TemporaryDirectory(prefix='crux-admission-child-')
        self.addCleanup(directory.cleanup)
        self.child = Path(directory.name).resolve() / 'checkout'
        self.git('worktree', 'add', '-q', '--detach', str(self.child), self.base)
        self.addCleanup(lambda: subprocess.run(['git', '-C', str(self.repo), 'worktree', 'remove', '--force',
                                                str(self.child)], capture_output=True))

    def delivered_child(self, *, evidence=0, stray=False):
        other = self.reserve('other')
        sha = self.unit(other, 'src/child.py', 'child = 2\n', root=self.child)
        self.deliver(other, 'done', [sha])
        tip = sha
        if stray:
            tip = self.commit('src/stray.py', 'stray = 1\n', None, root=self.child)
        for n in range(evidence):
            tip = self.commit(f'bionic/cycles/{self.cid}/evidence/e{n}.md', f'evidence {n}\n', None, root=self.child)
        return sha, tip

    def linked_merge(self, tip):
        lead = self.reserve('integrator', role='dev-lead', mode='background')
        self.ok({'op': 'attach-execution', 'op_id': self.op_id('attach'), 'assignment': lead['assignment'],
                 'attempt': lead['attempt'], 'handle': 'coordinator'})
        self.ok({'op': 'child-link', 'op_id': self.op_id('link'), 'assignment': lead['assignment'],
                 'attempt': lead['attempt'], 'child_task': 'other'})
        self.git('merge', '--no-ff', '-m', 'Integrate other\n\nCycle-Task: integrator', tip)
        return self.git('rev-parse', 'HEAD')

    def test_coordinating_merge_admits_source_and_merge(self):
        sha, tip = self.delivered_child()
        merge = self.linked_merge(tip)
        doc = load(self.repo, self.cid)
        self.assertNotIn('integrator', next(t for t in doc['plan']['tasks'] if t['id'] == 'build-it')['depends_on'])
        proof = cycle_execution.prove(tree(self.repo), doc, self.entry())
        self.assertEqual(self.kinds(proof)[sha], 'cycle-task-source')
        self.assertEqual(self.kinds(proof)[merge], 'cycle-task-merge')
        row = next(r for r in proof['commits'] if r['sha'] == merge)
        self.assertEqual(row['provenance']['child']['task'], 'other')

    def test_merge_with_extra_tree_refuses_without_a_fact(self):
        _, tip = self.delivered_child()
        self.linked_merge(tip)
        (self.repo / 'src/extra.py').write_text('extra = 1\n')
        self.git('add', 'src/extra.py'); self.git('commit', '--amend', '-q', '--no-edit')
        with self.assertRaises(cycle_execution.ExecutionError) as caught:
            cycle_execution.prove(tree(self.repo), load(self.repo, self.cid), self.entry())
        self.assertEqual(caught.exception.code, 'execution-foreign-source')
        self.assertNotIn('fact', caught.exception.details)

    def test_delivered_trailered_merge_with_extra_changes_is_not_cycle_task_source(self):
        sha, tip = self.delivered_child()
        self.git('merge', '--no-ff', '--no-commit', tip)
        (self.repo / 'src/extra.py').write_text('extra = 1\n')
        self.git('add', 'src/extra.py')
        self.git('commit', '-q', '-m', 'Merge with extra\n\nCycle-Task: other')
        merge = self.git('rev-parse', 'HEAD')
        doc = load(self.repo, self.cid)
        delivery = next(e for e in doc['assignments'] if e['task'] == 'other')['delivery']
        delivery['commits'] = [merge]
        with self.assertRaises(cycle_execution.ExecutionError) as caught:
            cycle_execution.prove(tree(self.repo), doc, self.entry())
        self.assertEqual((caught.exception.code, caught.exception.details['commit']), ('execution-foreign-source', merge))

    def test_evidence_only_child_tip_passes_post_merge_check(self):
        sha, tip = self.delivered_child(evidence=1)
        self.assertNotEqual(sha, tip)
        merge = self.linked_merge(tip)
        doc = load(self.repo, self.cid)
        integrator = next(t for t in doc['plan']['tasks'] if t['id'] == 'integrator')
        integrator['integrates'] = ['build-it', 'other']
        integrator['depends_on'] = ['build-it', 'other']
        # The declared-child form: integrated-task-merge resolves the evidence-only tip.
        lead = next(e for e in doc['assignments'] if e['task'] == 'integrator')
        proof = cycle_execution.prove(tree(self.repo), doc, {**self.entry('integrator'), 'id': lead['id']})
        self.assertEqual(self.kinds(proof)[merge], 'integrated-task-merge')
        self.assertEqual(self.kinds(proof)[tip], 'bookkeeping')
        row = next(r for r in proof['commits'] if r['sha'] == merge)
        self.assertEqual((row['provenance']['child_parent'], row['provenance']['child_source']), (tip, sha))
        # The undeclared form: cycle-task-merge shares the walk.
        self.assertEqual(self.kinds(cycle_execution.prove(tree(self.repo), load(self.repo, self.cid), self.entry()))[merge],
                         'cycle-task-merge')

    def test_non_bookkeeping_commit_in_the_walk_refuses(self):
        _, tip = self.delivered_child(evidence=1, stray=True)
        stray = self.git('rev-parse', tip + '^')
        self.linked_merge(tip)
        doc = load(self.repo, self.cid)
        cfg = tree(self.repo)
        # The walk passes the evidence-only tip and stops at the stray source commit.
        resolved = cycle_execution._child_tip(cfg, self.repo, tip, cycle_execution.bookkeeping_paths(cfg, doc),
                                                doc['plan']['scope'])
        self.assertEqual(resolved, (stray, ['src/stray.py']))
        with self.assertRaises(cycle_execution.ExecutionError) as caught:
            cycle_execution.prove(cfg, doc, self.entry())
        # The refusal names the stray commit the walk stopped at, with its paths.
        self.assertEqual(caught.exception.code, 'execution-foreign-source')
        self.assertEqual((caught.exception.details['commit'], caught.exception.details['paths']), resolved)

    def test_walk_beyond_the_bound_refuses(self):
        _, tip = self.delivered_child(evidence=cycle_execution.EVIDENCE_WALK_LIMIT + 1)
        merge = self.linked_merge(tip)
        with self.assertRaises(cycle_execution.ExecutionError) as caught:
            cycle_execution.prove(tree(self.repo), load(self.repo, self.cid), self.entry())
        self.assertEqual((caught.exception.code, caught.exception.details['commit']), ('execution-foreign-source', merge))


class StreamProofTests(AdmissionBase):
    """Approach 3: stream-scoped ownership tests only the attempt's own work."""

    def setUp(self):
        super().setUp()
        self.add_task('other')
        self.edit_record(lambda raw: raw['plan'].update(streams=[
            {'id': 'sa', 'paths': ['src/a.py'], 'independent': True},
            {'id': 'sb', 'paths': ['src/b.py'], 'independent': True}]))
        self.set_stream('build-it', 'sa')
        self.set_stream('other', 'sb')

    def set_stream(self, task, stream):
        def change(raw):
            found = next(t for t in raw['plan']['tasks'] if t['id'] == task)
            if stream is None:
                found.pop('stream', None)
            else:
                found['stream'] = stream
        self.edit_record(change)

    def test_other_streams_delivered_work_does_not_refuse(self):
        mine = self.reserve('build-it')
        other = self.reserve('other')
        sha = self.unit(other, 'src/b.py', 'b = 1\n')
        self.deliver(other, 'done', [sha])
        proof = self.check(mine)['execution']
        self.assertEqual(self.kinds(proof)[sha], 'cycle-task-source')
        self.assertEqual(proof['owned_paths'], ['src/a.py'])
        self.assertIn('declared stream sa', proof['ownership_basis'])

    def test_done_task_of_another_stream_grounds_no_commit_on_this_streams_path(self):
        self.add_task('third', stream='sb')
        mine = self.reserve('build-it')

        def delivered(task, name):
            # Commit with the task unstreamed, so its own checkpoints admit the path, then restore sb.
            self.set_stream(task, None)
            prepared = self.reserve(task)
            sha = self.unit(prepared, name, f'{task} = 1\n')
            self.deliver(prepared, 'done', [sha])
            self.set_stream(task, 'sb')
            return sha

        # Positive control: a done sb task whose commit touches only sb's path is admitted.
        admitted = delivered('other', 'src/b.py')
        row = next(r for r in self.check(mine)['execution']['commits'] if r['sha'] == admitted)
        self.assertEqual((row['kind'], row['provenance']['task']), ('cycle-task-source', 'other'))
        # The same delivery shape touching src/a.py, a path of sa, grounds nothing for sa's attempt.
        crossing = delivered('third', 'src/a.py')
        error = self.check_refused(mine, 'execution-foreign-source')
        self.assertEqual(error['observed']['commit'], crossing)

    def test_uncommitted_edit_outside_the_stream_refuses_with_paths(self):
        mine = self.reserve('build-it')
        self.check(mine)
        (self.repo / 'src/c.py').write_text('c = 1\n')
        error = self.check_refused(mine, 'execution-edited-path-outside-stream', edited_paths=['src/c.py'])
        self.assertEqual(error['observed']['paths'], ['src/c.py'])
        self.assertEqual(error['observed']['stream'], 'sa')
        route = error['recovery'][0]
        self.assertEqual(route['argv'][-2:], ['plan', self.cid])
        self.assertEqual(route['purpose'], cycle_ops.OUTSIDE_STREAM_NOTE)
        self.assertEqual(route['paths'], ['src/c.py'])

    def test_committed_edit_outside_the_stream_refuses_and_redispatch_resumes(self):
        self.set_stream('build-it', None)
        mine = self.reserve('build-it')
        sha = self.unit(mine, 'src/c.py', 'c = 1\n')
        self.set_stream('build-it', 'sa')
        error = self.check_refused(mine, 'execution-edited-path-outside-stream')
        self.assertEqual((error['observed']['paths'], error['observed']['commit']), (['src/c.py'], sha))
        # The worker removes its own uncommitted bytes (none here), delivers blocked listing the commit,
        # and the plan owner adds the path to the stream.
        self.deliver(mine, 'blocked', [sha])
        self.edit_record(lambda raw: raw['plan']['streams'][0].update(paths=['src/a.py', 'src/c.py']))
        retried = self.reserve('build-it', assignment='build-it')
        self.assertEqual(self.kinds(retried['execution'])[sha], 'same-task-resume')

    def test_evidence_path_under_the_cycle_directory_does_not_refuse(self):
        mine = self.reserve('build-it')
        self.check(mine)
        (self.repo / 'src/a.py').write_text('answer = 2\n')
        self.check(mine, edited_paths=['src/a.py'])
        evidence = f'bionic/cycles/{self.cid}/evidence/note.md'
        sha = self.commit(evidence, 'evidence\n', 'build-it', extra=('src/a.py',))
        self.assertEqual(self.kinds(self.check(mine)['execution'])[sha], 'same-attempt-commit')

    def test_dirty_byte_in_another_streams_path_still_refuses(self):
        mine = self.reserve('build-it')
        (self.repo / 'src/b.py').write_text('dirty = 1\n')
        error = self.check_refused(mine, 'execution-dirty-owned-paths')
        self.assertEqual(error['observed']['paths'], ['src/b.py'])

    def test_plan_writer_refuses_undeclared_and_dependent_streams(self):
        with self.assertRaisesRegex(CycleError, 'not a declared plan stream'):
            self.add_task('third', stream='missing')
        def dependent(raw):
            raw['plan']['streams'].append({'id': 'sc', 'paths': ['src'], 'independent': False})
            next(t for t in raw['plan']['tasks'] if t['id'] == 'other')['stream'] = 'sc'
        with self.assertRaisesRegex(CycleError, 'not independent'):
            self.edit_record(dependent)

    def test_a_record_without_streams_proves_as_today(self):
        doc = deepcopy(load(self.repo, self.cid))
        doc['plan'].pop('streams')
        for task in doc['plan']['tasks']:
            task.pop('stream', None)
        proof = cycle_execution.prove(tree(self.repo), validate(doc), self.entry())
        self.assertEqual(proof['owned_paths'], ['src'])


class OutsideScopeTests(AdmissionBase):
    """Approach 5: the outside-scope refusal reports its paths and the removal rule."""

    def test_outside_scope_refusal_names_the_paths(self):
        mine = self.reserve('build-it')
        self.check(mine)
        error = self.check_refused(mine, 'execution-edited-path-outside-scope', edited_paths=['lib/x.py', 'src/a.py'])
        self.assertEqual(error['observed']['paths'], ['lib/x.py'])
        self.assertEqual(error['recovery'][0]['purpose'], cycle_ops.OUTSIDE_SCOPE_NOTE)
        self.assertEqual(error['recovery'][0]['paths'], ['lib/x.py'])


FILLS = ['--improved', 'the pass delivered work that holds', '--unresolved', 'the refused commits',
         '--next-change', 're-dispatch the refused task above them', '--justification', 'interference, not a finding',
         '--progress', 'yes']


class BuildReturnBase(AdmissionBase):
    """Approach 7: a counted return from Build over a refusal the writer itself observes."""

    def setUp(self):
        super().setUp()
        mutate(self.repo, self.cid, 'extend', limit=3, human_approval='test: the owner raised the limit')

    def run_argv(self, argv, fills=FILLS):
        """Run a recovery argv through the cycle.py entry point, filling only the caller fields."""
        self.assertEqual(argv[:3], ['uv', 'run', str(PLUGIN / 'scripts/cycle.py')])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cycle.main([*argv[3:], *fills])
        return code, json.loads(out.getvalue())

    def build_return(self, task='build-it', fills=FILLS):
        argv = ['uv', 'run', str(PLUGIN / 'scripts/cycle.py'), '--repo-root', str(self.repo), '--compact',
                'return', self.cid, '--execution-task', task]
        return self.run_argv(argv, fills)

    def last_return(self):
        return [e for e in load(self.repo, self.cid)['history'] if e['action'] == 'return-requested'][-1]

    def rows(self, refusal, task='build-it'):
        found = next(item for item in refusal['ranges'] if item['task'] == task)
        return {row['sha']: row for row in found['rows']}

    def refused_build_it(self, edit=None):
        """build-it is reserved at the base; an untrailered in-scope commit lands; its check refuses."""
        prepared = self.reserve('build-it')
        self.check(prepared)
        if edit:
            (self.repo / edit).write_text('answer = 2\n')
        foreign = self.commit('src/b.py', 'b = 1\n', None)
        error = self.check_refused(prepared, 'execution-foreign-source',
                                   **({'edited_paths': [edit]} if edit else {}))
        return prepared, foreign, error


class BuildReturnRouteTests(BuildReturnBase):
    def test_end_to_end_route_from_build_for_foreign_source(self):
        prepared, foreign, error = self.refused_build_it()
        route = error['recovery'][0]
        self.assertEqual(route['argv'][-4:], ['return', self.cid, '--execution-task', 'build-it'])
        self.assertEqual(route['caller_fills'], list(cycle_ops.RETURN_FILLS))
        self.assertIn('legal from Build after every attempt is delivered', route['purpose'])
        self.deliver(prepared, 'blocked', [])
        code, response = self.run_argv(route['argv'])
        self.assertEqual(code, 0, response)
        doc = load(self.repo, self.cid)
        self.assertEqual((doc['status'], doc['phase'], doc['pass']), ('active', 'build', 2))
        refusal = self.last_return()['execution_refusal']
        self.assertEqual((refusal['task'], refusal['head']), ('build-it', self.git('rev-parse', 'HEAD')))
        row = self.rows(refusal)[foreign]
        self.assertEqual((row['refused'], row['paths'], row['trailers']), ('execution-foreign-source', ['src/b.py'], []))
        again = self.reserve('build-it', assignment='build-it')
        self.assertEqual(again['base'], self.git('rev-parse', 'HEAD'))
        self.assertEqual(self.check(again)['execution']['commits'], [])

    def test_end_to_end_route_from_build_for_source_outside_scope(self):
        prepared = self.reserve('build-it')
        self.check(prepared)
        self.deliver(prepared, 'blocked', [])
        outside = self.commit('lib/x.py', 'x = 1\n', None)
        status, response = self.op({'op': 'prepare-dispatch', 'op_id': self.op_id('prep'), 'task_id': 'build-it',
                                    'role': 'developer', 'host': 'claude-code', 'assignment': 'build-it'})
        self.assertEqual(status, 1, response)
        error = response['errors'][0]
        self.assertEqual((error['code'], error['observed']['commit']), ('execution-source-outside-scope', outside))
        route = error['recovery'][0]
        self.assertEqual(route['argv'][-4:], ['return', self.cid, '--execution-task', 'build-it'])
        code, response = self.run_argv(route['argv'])
        self.assertEqual(code, 0, response)
        row = self.rows(self.last_return()['execution_refusal'])[outside]
        self.assertEqual((row['refused'], row['paths']), ('execution-source-outside-scope', ['lib/x.py']))
        again = self.reserve('build-it', assignment='build-it')
        self.assertEqual(again['base'], self.git('rev-parse', 'HEAD'))

    def test_route_at_an_exhausted_pass_limit_pauses_and_changes_no_task(self):
        self.edit_record(lambda raw: raw.update(pass_limit=1))
        prepared, foreign, error = self.refused_build_it()
        self.deliver(prepared, 'blocked', [])
        tasks = deepcopy(load(self.repo, self.cid)['plan']['tasks'])
        code, response = self.run_argv(error['recovery'][0]['argv'])
        self.assertEqual(code, 0, response)
        doc = load(self.repo, self.cid)
        self.assertEqual((doc['status'], doc['blocker']['reason'], doc['pass']), ('paused', 'pass-limit', 1))
        self.assertEqual(doc['plan']['tasks'], tasks)

    def test_uncommitted_work_is_committed_under_the_exception_then_the_route_holds(self):
        prepared, foreign, error = self.refused_build_it(edit='src/a.py')
        # The refused check proved src/a.py owned and in scope; only the range refused.
        self.git('add', 'src/a.py')
        self.git('commit', '-q', '--only', 'src/a.py', '-m', 'work in progress\n\nCycle-Task: build-it')
        wip = self.git('rev-parse', 'HEAD')
        self.deliver(prepared, 'blocked', [wip])
        code, response = self.run_argv(error['recovery'][0]['argv'])
        self.assertEqual(code, 0, response)
        rows = self.rows(self.last_return()['execution_refusal'])
        self.assertEqual(rows[wip]['kind'], 'same-task-resume')
        self.assertEqual(rows[wip]['trailers'], ['build-it'])
        self.assertEqual(rows[foreign]['refused'], 'execution-foreign-source')
        self.reserve('build-it', assignment='build-it')

    def test_uncommitted_work_left_in_place_refuses_the_return(self):
        prepared, foreign, error = self.refused_build_it(edit='src/a.py')
        self.deliver(prepared, 'blocked', [])
        before = self.record_path().read_bytes()
        code, response = self.run_argv(error['recovery'][0]['argv'])
        self.assertEqual(code, 1, response)
        self.assertIn('return-execution-refused: execution-dirty-owned-paths', response['error'])
        self.assertIn('work-in-progress exception', response['error'])
        self.assertEqual(self.record_path().read_bytes(), before)


class BuildReturnControlTests(BuildReturnBase):
    def refuse(self, text, task='build-it', fills=FILLS):
        before = self.record_path().read_bytes()
        code, response = self.build_return(task, fills)
        self.assertEqual(code, 1, response)
        self.assertIn(text, response['error'])
        self.assertEqual(self.record_path().read_bytes(), before)

    def test_without_execution_task_build_refuses(self):
        prepared, _, error = self.refused_build_it()
        self.deliver(prepared, 'blocked', [])
        argv = error['recovery'][0]['argv'][:-2]
        before = self.record_path().read_bytes()
        code, response = self.run_argv(argv)
        self.assertEqual(code, 1, response)
        self.assertIn('return-execution-task-required', response['error'])
        self.assertEqual(self.record_path().read_bytes(), before)

    def test_an_open_attempt_refuses(self):
        self.add_task('other')
        prepared, _, _ = self.refused_build_it()
        self.deliver(prepared, 'blocked', [])
        self.reserve('other')
        self.refuse('return-attempts-open')

    def test_a_task_whose_probe_refuses_nothing_names_a_redispatch(self):
        prepared = self.reserve('build-it')
        self.check(prepared)
        self.deliver(prepared, 'blocked', [])
        self.refuse('return-execution-not-refused')
        self.refuse('re-dispatch the task with prepare-dispatch')

    def test_a_range_with_another_code_refuses_and_names_it(self):
        prepared = self.reserve('build-it')
        self.check(prepared)
        wip = self.commit('src/a.py', 'answer = 3\n', 'build-it')
        self.commit('src/b.py', 'b = 1\n', None)
        self.deliver(prepared, 'blocked', [wip])
        delivery = load(self.repo, self.cid)['assignments'][0]['delivery']
        report = tree(self.repo).docs_root / delivery['path']
        report.write_bytes(report.read_bytes() + b'damaged\n')
        self.refuse('return-execution-refused: execution-resume-proof-changed')

    def test_a_task_of_another_phase_or_status_refuses(self):
        self.refuse('return-execution-task-invalid', task='no-such-task')

    def test_verify_return_without_the_option_behaves_as_today(self):
        self.edit_record(lambda raw: raw.update(phase='verify'))
        mutate(self.repo, self.cid, 'return', improved='i', unresolved='u', next_change='n', justification='j',
               progress=True)
        doc = load(self.repo, self.cid)
        self.assertEqual((doc['phase'], doc['pass']), ('build', 2))
        self.assertNotIn('execution_refusal', self.last_return())


class CollectModeTests(BuildReturnBase):
    def test_the_probe_classifies_the_whole_range(self):
        prepared = self.reserve('build-it')
        self.check(prepared)
        first = self.commit('src/b.py', 'b = 1\n', None)
        second = self.commit('lib/x.py', 'x = 1\n', 'elsewhere')
        error = self.check_refused(prepared, 'execution-foreign-source')
        self.assertEqual(error['observed']['commit'], first)
        # The default mode still refuses at the first commit.
        with self.assertRaises(cycle_execution.ExecutionError) as caught:
            cycle_execution.prove(tree(self.repo), load(self.repo, self.cid), self.entry())
        self.assertEqual((caught.exception.code, caught.exception.details['commit']), ('execution-foreign-source', first))
        self.deliver(prepared, 'blocked', [])
        code, response = self.build_return()
        self.assertEqual(code, 0, response)
        rows = self.rows(self.last_return()['execution_refusal'])
        self.assertEqual((rows[first]['refused'], rows[first]['paths'], rows[first]['trailers']),
                         ('execution-foreign-source', ['src/b.py'], []))
        self.assertEqual((rows[second]['refused'], rows[second]['paths'], rows[second]['trailers']),
                         ('execution-source-outside-scope', ['lib/x.py'], ['elsewhere']))


class AbandonedRangeTests(BuildReturnBase):
    def setUp(self):
        super().setUp()
        self.add_task('c-task')

    def ranges(self):
        c_task = self.reserve('c-task')
        c_base = c_task['base']
        self.check(c_task)
        f1 = self.commit('src/f1.py', 'f = 1\n', None)
        self.check_refused(c_task, 'execution-foreign-source')
        w_c = self.commit('src/c.py', 'c = 1\n', 'c-task')
        self.deliver(c_task, 'blocked', [w_c])
        a_task = self.reserve('build-it')
        self.assertNotEqual(a_task['base'], c_base)
        self.check(a_task)
        f2 = self.commit('src/f2.py', 'f = 2\n', None)
        self.check_refused(a_task, 'execution-foreign-source')
        self.deliver(a_task, 'blocked', [])
        return c_base, a_task['base'], f1, w_c, f2

    def test_every_abandoned_range_is_retained(self):
        c_base, a_base, f1, w_c, f2 = self.ranges()
        code, response = self.build_return()
        self.assertEqual(code, 0, response)
        refusal = self.last_return()['execution_refusal']
        ranges = {item['task']: item for item in refusal['ranges']}
        self.assertEqual((ranges['build-it']['base'], ranges['c-task']['base']), (a_base, c_base))
        a_rows, c_rows = self.rows(refusal), self.rows(refusal, 'c-task')
        self.assertEqual(list(a_rows), [f2])
        self.assertEqual(a_rows[f2]['refused'], 'execution-foreign-source')
        self.assertEqual(c_rows[f1]['refused'], 'execution-foreign-source')
        self.assertEqual(c_rows[w_c]['kind'], 'same-task-resume')
        self.assertEqual(c_rows[f2]['refused'], 'execution-foreign-source')

    def test_another_code_in_an_abandoned_range_still_accepts_the_return(self):
        _, _, _, w_c, _ = self.ranges()
        delivery = next(e for e in load(self.repo, self.cid)['assignments'] if e['task'] == 'c-task')['delivery']
        report = tree(self.repo).docs_root / delivery['path']
        report.write_bytes(report.read_bytes() + b'damaged\n')
        code, response = self.build_return()
        self.assertEqual(code, 0, response)
        c_rows = self.rows(self.last_return()['execution_refusal'], 'c-task')
        self.assertEqual(c_rows[w_c]['refused'], 'execution-resume-proof-changed')


class InspectReturnOfferTests(BuildReturnBase):
    def offers(self):
        actions = self.ok({'op': 'inspect'})['actions']
        return [a for a in actions if isinstance(a.get('argv'), list) and '--execution-task' in a['argv']]

    def test_inspect_offers_the_return_from_the_journaled_observation(self):
        self.add_task('other')
        prepared, _, _ = self.refused_build_it()
        delivered = self.deliver(prepared, 'blocked', [])
        self.assertEqual(delivered['execution_observation']['code'], 'execution-foreign-source')
        offers = self.offers()
        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0]['argv'][-4:], ['return', self.cid, '--execution-task', 'build-it'])
        self.assertEqual(offers[0]['caller_fills'], list(cycle_ops.RETURN_FILLS))
        # While any attempt is reserved or running, inspect offers none.
        self.reserve('other')
        self.assertEqual(self.offers(), [])

    def test_a_previous_pass_delivery_draws_no_offer(self):
        prepared, _, _ = self.refused_build_it()
        self.deliver(prepared, 'blocked', [])
        self.assertTrue(self.offers())
        code, response = self.build_return()
        self.assertEqual(code, 0, response)
        self.assertEqual(load(self.repo, self.cid)['pass'], 2)
        self.assertEqual(self.offers(), [])


class OtherCycleRecordTests(AdmissionBase):
    """Approach 8: another open cycle's whole record commit is bookkeeping."""

    def commit_files(self, files, message='record'):
        for name, body in files.items():
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body)
        self.git('add', '-f', *files)
        self.git('commit', '-q', '-m', message)
        return self.git('rev-parse', 'HEAD')

    def record(self, ident='CYC-0999', status='active', **more):
        return {f'bionic/cycles/{ident}/cycle.json': json.dumps({'id': ident, 'status': status}) + '\n', **more}

    def prove(self):
        return cycle_execution.prove(tree(self.repo), load(self.repo, self.cid), self.entry())

    def assert_outside_scope(self, sha):
        with self.assertRaises(cycle_execution.ExecutionError) as caught:
            self.prove()
        self.assertEqual((caught.exception.code, caught.exception.details['commit']),
                         ('execution-source-outside-scope', sha))

    def test_another_cycles_record_commit_is_bookkeeping(self):
        created = self.commit_files(self.record(**{'bionic/cycles/CYC-0999/results/r.md': 'r\n'}))
        with_queue = self.commit_files({'bionic/cycles/CYC-0999/results/s.md': 's\n',
                                        'bionic/queue/cycles.yaml': 'format: 2\n'})
        rows = {row['sha']: row for row in self.prove()['commits']}
        for sha in (created, with_queue):
            self.assertEqual((rows[sha]['kind'], rows[sha]['basis'], rows[sha]['cycles']),
                             ('bookkeeping', 'other-cycle-record', ['CYC-0999']))

    def test_the_closing_commit_of_another_cycle_is_admitted(self):
        self.commit_files(self.record())
        closing = self.commit_files(self.record(status='completed'))
        row = next(r for r in self.prove()['commits'] if r['sha'] == closing)
        self.assertEqual(row.get('basis'), 'other-cycle-record')

    def test_an_intervening_record_commit_keeps_same_attempt_admission(self):
        prepared = self.reserve('build-it')
        self.check(prepared)
        (self.repo / 'src/a.py').write_text('answer = 2\n')
        self.check(prepared, edited_paths=['src/a.py'])
        other = self.commit_files(self.record())
        self.git('add', 'src/a.py')
        self.git('commit', '-q', '-m', 'answer\n\nCycle-Task: build-it')
        sha = self.git('rev-parse', 'HEAD')
        proof = self.check(prepared)['execution']
        self.assertEqual(self.kinds(proof)[sha], 'same-attempt-commit')
        self.assertEqual(self.kinds(proof)[other], 'bookkeeping')

    def test_mixed_with_an_in_scope_source_path_refuses(self):
        self.assert_outside_scope(self.commit_files(self.record(**{'src/b.py': 'b = 1\n'})))

    def test_a_directory_without_cycle_json_refuses(self):
        self.assert_outside_scope(self.commit_files({'bionic/cycles/CYC-0998/notes.md': 'n\n'}))

    def test_a_name_the_cycle_id_pattern_rejects_refuses(self):
        self.assert_outside_scope(self.commit_files({'bionic/cycles/not-a-cycle/cycle.json': '{}\n'}))

    def test_a_path_inside_the_plan_scope_refuses(self):
        self.edit_record(lambda raw: raw['plan'].update(scope=['src', 'bionic/cycles/CYC-0999/notes.md']))
        self.assert_outside_scope(self.commit_files(self.record(**{'bionic/cycles/CYC-0999/notes.md': 'n\n'})))

    def test_a_two_parent_commit_refuses(self):
        main = self.git('rev-parse', '--abbrev-ref', 'HEAD')
        self.git('checkout', '-q', '-b', 'side')
        self.commit_files(self.record())
        self.git('checkout', '-q', main)
        self.git('merge', '-q', '--no-ff', '-m', 'merge the record', 'side')
        self.assert_outside_scope(self.git('rev-parse', 'HEAD'))

    def test_a_change_to_a_cycle_closed_at_the_parent_refuses(self):
        self.commit_files(self.record(status='completed'))
        self.assert_outside_scope(self.commit_files({'bionic/cycles/CYC-0999/results/late.md': 'late\n'}))

    def test_an_unparsable_parent_record_refuses(self):
        self.commit_files({'bionic/cycles/CYC-0999/cycle.json': 'not json\n'})
        self.assert_outside_scope(self.commit_files({'bionic/cycles/CYC-0999/results/late.md': 'late\n'}))


class SchemaTests(unittest.TestCase):
    def test_operation_schema_admits_only_defer(self):
        base = {'op': 'execution-check', 'op_id': 'schema-check-1', 'assignment': 'a', 'attempt': 1}
        self.assertEqual(cycle_ops.schema_errors({**base, 'record_commit': 'defer'}), [])
        self.assertTrue(cycle_ops.schema_errors({**base, 'record_commit': 'now'}))


if __name__ == '__main__':
    unittest.main()
