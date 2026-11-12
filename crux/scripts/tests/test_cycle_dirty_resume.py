"""Bound pending source identities across a same-execution token rotation."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle_execution
import cycle_hosts
from cycle_workflow import create, load, mutate, tree
import test_cycle_slice as fixtures
import test_cycle_queue_commit as queue_fixtures


class DirtyResumeTests(fixtures.SliceBase):
    def prepare_dirty(self):
        self.prepare(mode='background')
        self.ok({'op': 'attach-execution', 'op_id': 'dirty-attach-1', 'assignment': 'build-it',
                 'attempt': 1, 'handle': 'same-native-handle'})
        self.ok({'op': 'execution-check', 'op_id': 'dirty-initial-check-1',
                 'assignment': 'build-it', 'attempt': 1})
        paths = ['src/a.py'] + [f'src/prep-{n}.txt' for n in range(8)]
        for n, name in enumerate(paths):
            (self.repo / name).write_text(f'pending release edit {n}\n')
        self.git('add', paths[1])
        doc = load(self.repo, self.cid)
        return tree(self.repo), doc, doc['assignments'][0], paths

    def test_nine_pending_files_resume_same_handle_after_rotation(self):
        cfg, doc, entry, paths = self.prepare_dirty()
        original = {p: (self.repo / p).read_bytes() for p in paths}
        cycle_execution.seal_pending(cfg, doc, entry)
        entry['delivery_token'] = 'f' * 32
        self.assertEqual(cycle_execution.resume_start(cfg, doc, entry, self.repo), sorted(paths))
        self.assertEqual({p: (self.repo / p).read_bytes() for p in paths}, original)

    def test_changed_worktree_index_identity_and_execution_binding_refuse(self):
        cfg, doc, entry, paths = self.prepare_dirty()
        cycle_execution.seal_pending(cfg, doc, entry)
        entry['delivery_token'] = 'f' * 32
        for key, changed in [('agent', 'other-handle'), ('host', 'other-host'), ('base', '0' * 40)]:
            with self.subTest(key=key):
                bad = deepcopy(entry)
                bad[key] = changed
                with self.assertRaises(cycle_execution.ExecutionError):
                    cycle_execution.resume_start(cfg, doc, bad, self.repo)
        first = self.repo / paths[0]
        before = first.read_bytes()
        first.write_bytes(b'foreign change\n')
        with self.assertRaises(cycle_execution.ExecutionError):
            cycle_execution.resume_start(cfg, doc, entry, self.repo)
        first.write_bytes(before)
        self.git('add', paths[0])
        with self.assertRaises(cycle_execution.ExecutionError):
            cycle_execution.resume_start(cfg, doc, entry, self.repo)

    def test_unbound_execution_cannot_seal_dirty_bytes(self):
        cfg, doc, entry, _ = self.prepare_dirty()
        entry['agent'] = None
        self.assertIsNone(cycle_execution.seal_pending(cfg, doc, entry))
        entry['delivery_token'] = 'f' * 32
        self.assertIsNone(cycle_execution.resume_start(cfg, doc, entry, self.repo))

    def test_other_running_source_execution_prevents_attribution(self):
        cfg, doc, entry, _ = self.prepare_dirty()
        doc['assignments'].append({'id': 'sibling', 'state': 'running', 'role': 'developer'})
        self.assertIsNone(cycle_execution.seal_pending(cfg, doc, entry))
        self.assertNotIn('resume_seal', entry)

    def test_foreign_addition_and_corrupt_seal_refuse(self):
        cfg, doc, entry, _ = self.prepare_dirty()
        seal = cycle_execution.seal_pending(cfg, doc, entry)
        entry['delivery_token'] = 'f' * 32
        extra = self.repo / 'src/foreign.txt'
        extra.write_text('another edit\n')
        with self.assertRaisesRegex(cycle_execution.ExecutionError, 'execution-resume-pending-changed'):
            cycle_execution.resume_start(cfg, doc, entry, self.repo)
        extra.unlink()
        proof = cfg.docs_root / seal['proof']['path']
        proof.write_bytes(proof.read_bytes() + b'changed')
        with self.assertRaisesRegex(cycle_execution.ExecutionError, 'execution-checkpoint-unavailable'):
            cycle_execution.resume_start(cfg, doc, entry, self.repo)

    def test_real_pause_resume_accepts_nine_unchanged_edits_and_rotates_marker(self):
        _, _, entry, paths = self.prepare_dirty()
        token = entry['delivery_token']
        original = {p: (self.repo / p).read_bytes() for p in paths}
        mutate(self.repo, self.cid, 'pause', reason='fixture pause')
        paused = load(self.repo, self.cid)['assignments'][0]
        self.assertEqual(paused['resume_seal']['previous_token'], token)
        mutate(self.repo, self.cid, 'resume', reason='fixture resumes')
        resumed = load(self.repo, self.cid)['assignments'][0]
        self.assertNotEqual(resumed['delivery_token'], token)
        stale = f'Assignment: build-it\nAttempt: 1\nResult-End: build-it/1#{token}\n'
        self.assertIsNotNone(cycle_hosts.result_problem(stale, 'build-it', 1, resumed['delivery_token']))
        checked = self.ok({'op': 'execution-check', 'op_id': 'dirty-resumed-check-2',
                           'assignment': 'build-it', 'attempt': 1})
        self.assertEqual(checked['execution']['dirty_paths'], sorted(paths))
        self.assertEqual({p: (self.repo / p).read_bytes() for p in paths}, original)
        self.assertNotIn('resume_seal', load(self.repo, self.cid)['assignments'][0])

    def test_real_resume_refuses_changed_bytes_and_caller_path_substitution(self):
        _, _, _, paths = self.prepare_dirty()
        mutate(self.repo, self.cid, 'pause', reason='fixture pause')
        mutate(self.repo, self.cid, 'resume', reason='fixture resume')
        request = {'op': 'execution-check', 'assignment': 'build-it', 'attempt': 1}
        self.refused({**request, 'op_id': 'resume-wrong-paths-1', 'edited_paths': [paths[0]]},
                     'execution-resume-paths-changed')
        (self.repo / paths[0]).write_text('foreign edited bytes\n')
        self.refused({**request, 'op_id': 'resume-foreign-bytes-2'}, 'execution-resume-pending-changed')

    def test_pause_seal_preserves_checkpointed_own_commit_not_yet_readmitted(self):
        self.prepare(mode='background')
        self.ok({'op': 'attach-execution', 'op_id': 'own-attach-1', 'assignment': 'build-it',
                 'attempt': 1, 'handle': 'same-native-handle'})
        self.ok({'op': 'execution-check', 'op_id': 'own-clean-1', 'assignment': 'build-it', 'attempt': 1})
        (self.repo / 'src/a.py').write_text('answer = 2\n')
        self.git('add', 'src/a.py')
        self.ok({'op': 'execution-check', 'op_id': 'own-seal-2', 'assignment': 'build-it', 'attempt': 1,
                 'edited_paths': ['src/a.py']})
        self.git('commit', '-q', '-m', 'owned checkpoint\n\nCycle-Task: build-it')
        commit = self.git('rev-parse', 'HEAD')
        (self.repo / 'src/later.txt').write_text('pending\n')
        mutate(self.repo, self.cid, 'pause', reason='fixture pause')
        mutate(self.repo, self.cid, 'resume', reason='fixture resume')
        checked = self.ok({'op': 'execution-check', 'op_id': 'own-rotated-3',
                           'assignment': 'build-it', 'attempt': 1})
        self.assertEqual(checked['execution']['dirty_paths'], ['src/later.txt'])
        self.assertIn(commit, [row['sha'] for row in checked['execution']['commits']])
        again = self.ok({'op': 'execution-check', 'op_id': 'own-again-4',
                         'assignment': 'build-it', 'attempt': 1, 'edited_paths': ['src/later.txt']})
        self.assertIn(commit, [row['sha'] for row in again['execution']['commits']])


class QueueHistoryProofTests(queue_fixtures.GitBase):
    def prepare_observer(self):
        first = self.add('finished')
        self.authorize('next')
        _, started = self.start()
        self.end_cycle(started['cycle'], 'completed')
        self.git('add', '-A')
        self.git('commit', '-q', '-m', 'fixture terminal cycle')
        doc = create(self.repo, 'quick-fix', 'Observer', 'Observe', ['src', 'notes'], ['ok'], 'builder', 'tester')
        self.git('add', '-A')
        self.git('commit', '-q', '-m', 'observer fixture')
        entry = {'id': 'observer', 'task': 'observer', 'attempt': 1, 'base': self.git('rev-parse', 'HEAD'),
                 'delivery_token': 'a' * 32}
        return first, doc, entry

    def test_real_queue_archive_commit_is_validated_bookkeeping(self):
        first, doc, entry = self.prepare_observer()
        self.ok('archive', '--migrate')
        proof = cycle_execution.prove(tree(self.repo), doc, entry)
        self.assertEqual(proof['commits'][-1]['kind'], 'bookkeeping')
        self.assertIn(f'notes/queue/history/items/{first}.json', proof['commits'][-1]['paths'])

    def test_arbitrary_history_file_is_not_bookkeeping(self):
        _, doc, entry = self.prepare_observer()
        path = self.repo / 'notes/queue/history/items/Q-9999.json'
        path.parent.mkdir(parents=True)
        path.write_text('{"not": "a queue writer record"}\n')
        self.git('add', str(path))
        self.git('commit', '-q', '-m', 'forged history')
        with self.assertRaisesRegex(cycle_execution.ExecutionError, 'execution-foreign-source'):
            cycle_execution.prove(tree(self.repo), doc, entry)


class IntegratedChildTests(fixtures.SliceBase):
    def add_integrator(self):
        mutate(self.repo, self.cid, 'task-add', task={'id': 'other', 'phase': 'build',
               'description': 'other slice', 'depends_on': [], 'status': 'pending', 'expected_evidence': ['commit']})
        mutate(self.repo, self.cid, 'task-add', task={'id': 'integrator', 'phase': 'build',
               'description': 'integrate slices', 'depends_on': ['build-it', 'other'],
               'integrates': ['build-it', 'other'], 'status': 'pending', 'expected_evidence': ['commit']})

    def test_parent_admits_exact_delivered_child_with_sealed_source(self):
        self.add_integrator()
        prepared = self.prepare(mode='background')
        self.ok({'op': 'attach-execution', 'op_id': 'child-attach-1', 'assignment': 'build-it',
                 'attempt': 1, 'handle': 'child-handle'})
        commit = self.checkpoint_work(prepared)
        self.ok({'op': 'execution-check', 'op_id': 'child-commit-proof-2', 'assignment': 'build-it', 'attempt': 1})
        self.ok({'op': 'deliver', 'op_id': 'child-delivery-3', 'assignment': 'build-it', 'attempt': 1,
                 'outcome': 'done', 'commits': [commit]})
        doc = load(self.repo, self.cid)
        parent = {'id': 'integrator', 'task': 'integrator', 'attempt': 1, 'base': self.base,
                  'delivery_token': 'f' * 32}
        proof = cycle_execution.prove(tree(self.repo), doc, parent)
        self.assertEqual(next(row for row in proof['commits'] if row['sha'] == commit)['kind'],
                         'integrated-task-source')
        unlinked = deepcopy(doc)
        task = next(t for t in unlinked['plan']['tasks'] if t['id'] == 'integrator')
        task['integrates'] = ['other']
        # An undeclared child is no integrated-task-source; its validated done delivery
        # still admits it as cycle-task-source through its retained proof.
        row = next(row for row in cycle_execution.prove(tree(self.repo), unlinked, parent)['commits']
                   if row['sha'] == commit)
        self.assertEqual((row['kind'], row['provenance']['ground']), ('cycle-task-source', 'retained-proof'))
        failed = deepcopy(doc)
        failed['assignments'][0]['delivery']['outcome'] = 'failed'
        with self.assertRaisesRegex(cycle_execution.ExecutionError, 'execution-foreign-source'):
            cycle_execution.prove(tree(self.repo), failed, parent)
        delivered = doc['assignments'][0]['delivery']
        result = tree(self.repo).docs_root / delivered['path']
        result.write_bytes(result.read_bytes() + b'changed')
        with self.assertRaisesRegex(cycle_execution.ExecutionError, 'execution-resume-proof-invalid'):
            cycle_execution.prove(tree(self.repo), doc, parent)

    def test_delivered_child_trailer_without_sealed_source_refuses(self):
        self.add_integrator()
        prepared = self.prepare(mode='background')
        self.ok({'op': 'attach-execution', 'op_id': 'unsealed-attach-1', 'assignment': 'build-it',
                 'attempt': 1, 'handle': 'child-handle'})
        commit = self.work(prepared)
        self.ok({'op': 'deliver', 'op_id': 'unsealed-delivery-1', 'assignment': 'build-it', 'attempt': 1,
                 'outcome': 'done', 'commits': [commit]})
        parent = {'id': 'integrator', 'task': 'integrator', 'attempt': 1, 'base': self.base,
                  'delivery_token': 'f' * 32}
        # No sealed source makes it no integrated-task-source. The done delivery's range and
        # trailer admit it as cycle-task-source ground (b) instead.
        row = next(row for row in cycle_execution.prove(tree(self.repo), load(self.repo, self.cid), parent)['commits']
                   if row['sha'] == commit)
        self.assertEqual((row['kind'], row['provenance']['ground']), ('cycle-task-source', 'validated-delivery'))
        doc = load(self.repo, self.cid)
        doc['assignments'][0]['delivery']['outcome'] = 'failed'
        with self.assertRaisesRegex(cycle_execution.ExecutionError, 'execution-foreign-source'):
            cycle_execution.prove(tree(self.repo), doc, parent)


if __name__ == '__main__':
    unittest.main()
