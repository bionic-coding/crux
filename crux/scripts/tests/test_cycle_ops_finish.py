"""Typed finish: release cycles, completion order, linear-tip recovery, reflection fields."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cycle_ops
from cycle_workflow import create, load, mutate, validate
from test_cycle_ops_advance import AdvanceBase, FILLS


class FinishBase(AdvanceBase):
    def commit_file(self, name, text, message):
        (self.repo / name).write_text(text)
        self.git('add', name)
        self.git('commit', '-q', '-m', message)
        return self.git('rev-parse', 'HEAD')

    def v3(self, cid):
        path = self.record_path(cid)
        raw = json.loads(path.read_text())
        raw.update(schema_version=3, **{**cycle_ops.v3_fields(), 'revision': 1})
        for entry in raw.get('assignments', []):
            entry.update({k: None for k in cycle_ops.ASSIGNMENT_V3_FIELDS})
        validate(raw)
        path.write_text(json.dumps(raw, indent=2, sort_keys=True) + '\n')

    def finish_request(self, op_id='finish-001', **extra):
        return {'op': 'finish', 'op_id': op_id, 'expect_revision': self.revision(extra.pop('cid', None)), 'lessons': ['l'], 'remaining': ['none'], **extra}

    def add_task(self, task_id):
        mutate(self.repo, self.cid, 'task-add', task={'id': task_id, 'phase': 'build', 'description': task_id, 'depends_on': [],
                                                    'status': 'pending', 'expected_evidence': ['commit']})


class ReleaseFinishTests(FinishBase):
    def release(self):
        doc = create(self.repo, 'release', 'Ship', 'Release it', ['src'], ['shipped'], 'builder', 'tester', release_list='official')
        self.v3(doc['id'])
        return doc['id']

    def finish_tasks(self, cid, count=None):
        tasks = load(self.repo, cid)['plan']['tasks'][:count]
        shas = []
        for task in tasks:
            shas.append(self.commit_file(f'src/{task["id"]}.txt', task['id'], f'step {task["id"]}'))
            mutate(self.repo, cid, 'task', task_id=task['id'], state='done', commits=[shas[-1]])
        return shas

    def test_finish_runs_from_the_release_phase_with_no_reflection(self):
        cid = self.release()
        shas = self.finish_tasks(cid)
        seen = self.ok({'op': 'inspect'}, cid=cid)
        self.assertEqual(seen['phase'], 'release'); self.assertEqual(seen['unmet']['completion'], [])
        offered = [a for a in seen['actions'] if a.get('request', {}).get('op') == 'finish']
        self.assertEqual(len(offered), 1)
        self.assertEqual(offered[0]['caller_fills'], ['op_id'])
        self.assertEqual(offered[0]['request'], {'op': 'finish', 'expect_revision': seen['revision']})
        done = self.ok({**offered[0]['request'], 'op_id': 'finish-rel-1'}, cid=cid)
        self.assertEqual((done['status'], done['completion']['tip']), ('completed', shas[-1]))
        self.assertNotIn('evidence_size', done)
        doc = load(self.repo, cid)
        self.assertEqual((doc['status'], doc['reflection']), ('completed', None))
        self.assertEqual(doc['completion']['commits'], shas)
        replay = self.ok({**offered[0]['request'], 'op_id': 'finish-rel-1'}, cid=cid)
        self.assertEqual(replay['replayed'], True)

    def test_unfinished_tasks_refuse_finish(self):
        cid = self.release()
        self.finish_tasks(cid, 2)
        response = self.refused({'op': 'finish', 'op_id': 'finish-rel-1', 'expect_revision': self.revision(cid)}, 'requirement-unmet', cid=cid)
        fields = [e['field'] for e in response['errors']]
        self.assertIn('tasks', fields)

    def test_no_operation_changes_the_fixed_task_list(self):
        cid = self.release()
        before = json.dumps(load(self.repo, cid)['plan']['tasks'])
        ids = [t['id'] for t in load(self.repo, cid)['plan']['tasks']]
        self.refused({'op': 'advance', 'op_id': 'advance-r01', 'expect_revision': self.revision(cid)}, 'requirement-unmet', 'requirement-unmet', cid=cid)
        self.refused({'op': 'finish', 'op_id': 'finish-rel-1', 'expect_revision': self.revision(cid)}, 'no-commits', cid=cid)
        self.ok({'op': 'inspect'}, cid=cid)
        self.assertEqual(json.dumps(load(self.repo, cid)['plan']['tasks']), before)
        self.finish_tasks(cid)
        self.ok({'op': 'finish', 'op_id': 'finish-rel-2', 'expect_revision': self.revision(cid)}, cid=cid)
        self.assertEqual([t['id'] for t in load(self.repo, cid)['plan']['tasks']], ids)
        self.assertEqual({t['status'] for t in load(self.repo, cid)['plan']['tasks']}, {'done'})

    def test_typed_advance_completes_a_recorded_completion(self):
        cid = self.release()
        shas = self.finish_tasks(cid)
        mutate(self.repo, cid, 'completion', commits=[shas[-1]], remaining='none')
        doc = load(self.repo, cid)
        doc['completion']['input_sha256'] = cycle_ops.source_fingerprint(self.repo, doc)
        raw = json.loads(self.record_path(cid).read_text()); raw['completion'] = doc['completion']
        self.record_path(cid).write_text(json.dumps(raw))
        seen = self.ok({'op': 'inspect'}, cid=cid)
        self.assertEqual(seen['unmet']['next'], [])
        offered = [a for a in seen['actions'] if a.get('request', {}).get('op') == 'advance']
        self.assertEqual(len(offered), 1)
        done = self.ok({**offered[0]['request'], 'op_id': 'advance-rel1'}, cid=cid)
        self.assertEqual(done['status'], 'completed')

    def test_a_dirty_scope_path_refuses_finish(self):
        cid = self.release()
        self.finish_tasks(cid)
        (self.repo / 'src/a.py').write_text('answer = 99\n')
        response = self.refused({'op': 'finish', 'op_id': 'finish-rel-1', 'expect_revision': self.revision(cid)}, 'requirement-unmet', cid=cid)
        self.assertEqual(response['errors'][0]['field'], 'completion')
        self.assertIn('uncommitted', response['errors'][0]['problem'])

    def test_actions_validate_against_the_schema(self):
        cid = self.release()
        self.finish_tasks(cid)
        seen = self.ok({'op': 'inspect'}, cid=cid)
        self.assertTrue(self.check_requests_validate(seen['actions']))


class ReflectionFieldTests(FinishBase):
    def test_a_non_release_cycle_needs_lessons_and_remaining(self):
        self.deliver_build_and_reflect()
        request = {'op': 'finish', 'op_id': 'finish-001', 'expect_revision': self.revision()}
        response = self.refused(request, 'reflection-missing', 'reflection-missing')
        self.assertEqual(sorted(e['field'] for e in response['errors']), ['lessons', 'remaining'])
        recovery = response['errors'][0]['recovery'][0]
        self.assertEqual(recovery['caller_fills'], ['op_id', 'lessons', 'remaining'])
        self.check_requests_validate([recovery])
        self.assertEqual(self.ok(self.finish_request('finish-002'))['status'], 'completed')

    def test_a_non_release_finish_reports_the_committed_evidence_size(self):
        self.deliver_build_and_reflect()
        done = self.ok(self.finish_request('finish-size'))
        size = done['evidence_size']
        relative = f'bionic/cycles/{self.cid}/'
        self.assertEqual(size['measure'], f'sum of blob sizes from git ls-tree -r -l at the completion HEAD over {relative}')
        self.assertEqual(set(size), {'bytes', 'files', 'measure'})
        # The fixture ignores bionic/, so measure a commit that holds the cycle files.
        self.git('add', '-f', relative)
        self.git('commit', '-q', '-m', 'record')
        head = self.git('rev-parse', 'HEAD')
        listing = self.git('ls-tree', '-r', '-l', '--full-tree', head, '--', relative)
        rows = [line.split('\t')[0].split() for line in listing.splitlines() if line.strip()]
        self.assertGreater(len(rows), 0)
        measured = cycle_ops.evidence_size(cycle_ops.tree(self.repo), load(self.repo, self.cid), head)
        self.assertEqual(measured['files'], len(rows))
        self.assertEqual(measured['bytes'], sum(int(r[3]) for r in rows))
        self.assertGreater(measured['bytes'], 0)
        # Uncommitted cycle bytes are not counted: at the completion HEAD the fixture had committed none.
        self.assertEqual((size['bytes'], size['files']), (0, 0))

    def test_evidence_size_counts_record_commits_after_the_last_task_commit(self):
        self.deliver_build_and_reflect()
        relative = f'bionic/cycles/{self.cid}/'
        self.git('add', '-f', relative)
        self.git('commit', '-q', '-m', 'record')
        head = self.git('rev-parse', 'HEAD')
        rows = [line.split('\t')[0].split() for line in self.git('ls-tree', '-r', '-l', '--full-tree', head, '--', relative).splitlines() if line.strip()]
        done = self.ok(self.finish_request('finish-size2'))
        self.assertNotEqual(done['completion']['tip'], head)
        self.assertEqual((done['evidence_size']['files'], done['evidence_size']['bytes']), (len(rows), sum(int(r[3]) for r in rows)))
        self.assertGreater(done['evidence_size']['bytes'], 0)

    def deliver_build_and_reflect(self):
        self.deliver_build()
        self.to_reflect()


class CompletionOrderTests(FinishBase):
    def reflect_with(self, finish_ready=True):
        self.to_reflect()

    def test_parallel_task_commits_with_a_replacement_complete_in_ancestry_order(self):
        self.add_task('other')
        self.git('checkout', '-q', '-b', 'side')
        old = self.commit_file('src/b.py', 'b = 1\n', 'side work\n\nCycle-Task: other')
        self.git('checkout', '-q', '-')
        mutate(self.repo, self.cid, 'task', task_id='other', state='done', commits=[old])
        first = self.commit_file('src/a.py', 'answer = 2\n', 'rebased work\n\nCycle-Task: other')
        mutate(self.repo, self.cid, 'task', task_id='other', replace_commit=(old[:12], first), note='rebased onto the answer change')
        second = self.commit_file('src/c.py', 'c = 1\n', 'later work\n\nCycle-Task: build-it')
        mutate(self.repo, self.cid, 'task', task_id='build-it', state='done', commits=[second])
        doc = load(self.repo, self.cid)
        self.assertEqual([t['commits'] for t in doc['plan']['tasks']], [[second], [first]])
        self.to_reflect()
        done = self.ok(self.finish_request())
        self.assertEqual(done['completion']['commits'], [first, second]); self.assertEqual(done['completion']['tip'], second)
        doc = load(self.repo, self.cid)
        self.assertEqual(doc['plan']['tasks'][1]['replaced_commits'][0]['from'], old)
        self.assertEqual(doc['completion']['commits'], [first, second])

    def test_commits_that_are_not_linear_recover_with_the_head_as_tip(self):
        self.add_task('other')
        one = self.commit_file('src/a.py', 'answer = 2\n', 'answer\n\nCycle-Task: build-it')
        self.git('checkout', '-q', '-b', 'side', self.base)
        two = self.commit_file('src/b.py', 'b = 1\n', 'side\n\nCycle-Task: other')
        self.git('checkout', '-q', '-')
        self.git('merge', '-q', '--no-ff', '-m', 'merge side', 'side')
        head = self.git('rev-parse', 'HEAD')
        mutate(self.repo, self.cid, 'task', task_id='build-it', state='done', commits=[one])
        mutate(self.repo, self.cid, 'task', task_id='other', state='done', commits=[two])
        self.to_reflect()
        response = self.refused(self.finish_request(), 'commits-not-linear')
        recovery = response['errors'][0]['recovery'][0]
        self.assertEqual(recovery['request']['tip'], head)
        self.assertNotIn('tip', recovery['caller_fills'])
        self.assertEqual(recovery['caller_fills'], ['op_id', 'lessons', 'remaining'])
        request = {**recovery['request'], **{k: FILLS[k] for k in recovery['caller_fills']}}
        done = self.ok(request)
        self.assertEqual(done['completion']['tip'], head)
        self.assertEqual(set(done['completion']['commits']), {one, two, head})
        self.assertEqual(done['completion']['commits'][-1], head)

    def test_a_dirty_scope_path_refuses_finish(self):
        self.deliver_build()
        self.to_reflect()
        (self.repo / 'src/a.py').write_text('answer = 99\n')
        response = self.refused(self.finish_request(), *['requirement-unmet'] * 3)
        self.assertIn('completion', [e['field'] for e in response['errors']])


if __name__ == '__main__':
    unittest.main()
