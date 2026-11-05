"""Execution checkout proofs retain review bases and inspect real Git changes."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import test_cycle_slice as fixtures
from cycle_workflow import load, tree, mutate
import cycle_execution


class ExecutionProofTests(fixtures.SliceBase):
    def check(self, op_id='execution-start-1', **extra):
        return self.ok({'op': 'execution-check', 'op_id': op_id, 'assignment': 'build-it', 'attempt': 1, **extra})

    def bookkeeping(self, name='notes.md', title='ordinary bookkeeping'):
        path = self.repo / 'bionic/cycles' / self.cid / name
        path.write_text('Retained record evidence.\n')
        self.git('add', '-f', str(path))
        self.git('commit', '-q', '-m', title)
        return self.git('rev-parse', 'HEAD')

    def test_prepare_keeps_review_base_and_separate_execution_head(self):
        prepared = self.prepare()
        self.assertEqual(prepared['base'], self.base)
        self.assertEqual(prepared['execution']['review_base'], self.base)
        self.assertEqual(prepared['execution']['execution_head'], self.base)

    def test_bookkeeping_descendant_refreshes_execution_without_replacing_base(self):
        self.prepare()
        head = self.bookkeeping()
        checked = self.check()
        self.assertEqual(checked['execution']['review_base'], self.base)
        self.assertEqual(checked['execution']['execution_head'], head)
        self.assertEqual(checked['execution']['commits'][0]['kind'], 'bookkeeping')
        self.assertEqual(load(self.repo, self.cid)['assignments'][0]['base'], self.base)

    def test_forged_bookkeeping_subject_does_not_admit_source_commit(self):
        self.prepare()
        (self.repo / 'src/a.py').write_text('answer = 999\n')
        self.git('add', 'src/a.py')
        self.git('commit', '-q', '-m', self.cid + ' record: fake bookkeeping')
        self.refused({'op': 'execution-check', 'op_id': 'execution-forged-1', 'assignment': 'build-it', 'attempt': 1},
                     'execution-foreign-source')

    def test_unchanged_proof_reuses_artifact_without_commit_or_revision_loop(self):
        self.prepare()
        first = self.check()
        head, revision = self.git('rev-parse', 'HEAD'), load(self.repo, self.cid)['revision']
        repeated = self.check(op_id='execution-again-2')
        self.assertFalse(repeated['changed'])
        self.assertEqual(first['execution']['proof'], repeated['execution']['proof'])
        self.assertEqual(load(self.repo, self.cid)['revision'], revision)
        self.assertEqual(self.git('rev-parse', 'HEAD'), head)
        # An execution-check may now run the writer-owned no-op commit path.
        self.assertFalse(repeated.get('record_commit', {}).get('changed', False))

    def test_queue_is_exact_bookkeeping_boundary_but_other_docs_are_not(self):
        self.prepare()
        queue = self.repo / 'bionic/queue/cycles.yaml'
        queue.parent.mkdir(parents=True)
        queue.write_text('queue: []\n')
        self.git('add', '-f', str(queue)); self.git('commit', '-q', '-m', 'no special message prefix')
        self.assertEqual(self.check()['execution']['commits'][-1]['kind'], 'bookkeeping')
        other = self.repo / 'bionic/objectives.md'
        other.write_text('Changed objectives are source.\n')
        self.git('add', '-f', str(other)); self.git('commit', '-q', '-m', self.cid + ' record: forged docs exemption')
        self.refused({'op': 'execution-check', 'op_id': 'execution-docs-3', 'assignment': 'build-it', 'attempt': 1},
                     'execution-source-outside-scope')

    def test_initial_dirty_owned_paths_refuse_and_checkpoint_names_exact_edits(self):
        prepared = self.prepare()
        (self.repo / 'src/a.py').write_text('answer = 3\n')
        self.refused({'op': 'execution-check', 'op_id': 'execution-dirty-1', 'assignment': 'build-it', 'attempt': 1},
                     'execution-dirty-owned-paths')
        self.refused({'op': 'execution-check', 'op_id': 'execution-bypass-1', 'assignment': 'build-it', 'attempt': 1,
                      'edited_paths': ['src/a.py']}, 'execution-clean-start-required')
        (self.repo / 'src/a.py').write_text('answer = 1\n')
        self.check()
        (self.repo / 'src/a.py').write_text('answer = 3\n')
        checked = self.check(op_id='execution-commit-2', edited_paths=['src/a.py'])
        self.assertEqual(checked['execution']['dirty_paths'], ['src/a.py'])
        self.assertEqual(checked['execution']['review_base'], prepared['base'])
        self.refused({'op': 'execution-check', 'op_id': 'execution-unowned-3', 'assignment': 'build-it', 'attempt': 1,
                      'edited_paths': ['README.md']}, 'execution-edited-path-outside-scope')

    def test_dirty_prepare_refuses_without_reservation(self):
        (self.repo / 'src/a.py').write_text('unowned work already here\n')
        self.refused({'op': 'prepare-dispatch', 'op_id': 'dirty-prepare-1', 'task_id': 'build-it', 'role': 'developer',
                      'host': 'codex'}, 'execution-dirty-owned-paths')
        self.assertEqual(load(self.repo, self.cid).get('assignments', []), [])

    def test_clean_registered_older_checkout_fast_forwards_to_original_base(self):
        old = self.base
        (self.repo / 'src/a.py').write_text('answer = 2\n')
        self.git('add', 'src/a.py'); self.git('commit', '-q', '-m', 'lead source prerequisite')
        prepared = self.prepare()
        worktree = self.repo.parent / (self.repo.name + '-older')
        self.git('worktree', 'add', '-q', '--detach', str(worktree), old)
        self.addCleanup(self.git, 'worktree', 'remove', str(worktree))
        refused = self.refused({'op': 'execution-check', 'op_id': 'execution-older-1', 'assignment': 'build-it', 'attempt': 1,
                                'checkout': str(worktree)}, 'execution-behind-base')
        argv = refused['errors'][0]['recovery'][0]['argv']
        self.assertEqual(argv[-3:], ['merge', '--ff-only', prepared['base']])
        subprocess.run(argv, check=True, capture_output=True)
        checked = self.check(op_id='execution-forward-2', checkout=str(worktree))
        self.assertEqual(checked['execution']['execution_head'], prepared['base'])
        self.assertEqual(checked['execution']['checkout'], str(worktree))

    def test_unrelated_checkout_and_unregistered_repository_refuse(self):
        self.prepare()
        self.refused({'op': 'execution-check', 'op_id': 'execution-external-1', 'assignment': 'build-it', 'attempt': 1,
                      'checkout': str(self.repo.parent)}, 'execution-unregistered-checkout')
        self.git('checkout', '-q', '--orphan', 'unrelated')
        self.git('add', 'src', '.gitignore'); self.git('commit', '-q', '-m', 'unrelated root')
        self.refused({'op': 'execution-check', 'op_id': 'execution-unrelated-2', 'assignment': 'build-it', 'attempt': 1},
                     'execution-unrelated-base')

    def test_source_rename_into_cycle_boundary_is_still_source(self):
        self.prepare()
        target = self.repo / 'bionic/cycles' / self.cid / 'renamed.txt'
        (self.repo / 'src/a.py').rename(target)
        self.git('add', '-A', 'src'); self.git('add', '-f', str(target))
        self.git('commit', '-q', '-m', self.cid + ' record: rename source')
        self.refused({'op': 'execution-check', 'op_id': 'execution-rename-1', 'assignment': 'build-it', 'attempt': 1},
                     'execution-foreign-source')

    def test_merge_resolution_source_is_not_hidden_by_parent_diffs(self):
        self.prepare()
        branch = self.git('symbolic-ref', '--short', 'HEAD')
        self.git('checkout', '-q', '-b', 'side')
        self.bookkeeping('side.md')
        self.git('checkout', '-q', branch)
        self.bookkeeping('main.md')
        self.git('merge', '--no-ff', '--no-commit', 'side')
        (self.repo / 'src/a.py').write_text('source changed only in merge resolution\n')
        self.git('add', 'src/a.py'); self.git('commit', '-q', '-m', self.cid + ' record: forged merge')
        self.refused({'op': 'execution-check', 'op_id': 'execution-merge-1', 'assignment': 'build-it', 'attempt': 1},
                     'execution-foreign-source')

    def blocked_delivery(self):
        prepared = self.prepare()
        sha = self.work(prepared)
        self.ok({'op': 'deliver', 'op_id': 'blocked-delivery-1', 'assignment': 'build-it', 'attempt': 1,
                 'outcome': 'blocked', 'commits': [sha], 'stop': 'contradicted-premise', 'note': 'offline fixture checkpoint'})
        return prepared, sha

    def test_same_task_resume_requires_retained_delivery_and_original_base(self):
        prepared, sha = self.blocked_delivery()
        delivery = load(self.repo, self.cid)['assignments'][0]['delivery']
        original = (tree(self.repo).docs_root / delivery['path']).read_bytes()
        resumed = self.prepare(op_id='resume-prepare-2', assignment='build-it')
        self.assertEqual(resumed['base'], prepared['base'])
        source = next(row for row in resumed['execution']['commits'] if row['sha'] == sha)
        self.assertEqual(source['kind'], 'same-task-resume')
        self.assertEqual(source['provenance']['result']['sha256'], delivery['sha256'])
        self.assertEqual((tree(self.repo).docs_root / delivery['path']).read_bytes(), original)

    def test_tampered_retained_result_cannot_authorize_resumed_source(self):
        self.blocked_delivery()
        delivery = load(self.repo, self.cid)['assignments'][0]['delivery']
        path = tree(self.repo).docs_root / delivery['path']
        path.write_bytes(path.read_bytes() + b'changed retained proof\n')
        self.refused({'op': 'prepare-dispatch', 'op_id': 'resume-tampered-2', 'task_id': 'build-it', 'assignment': 'build-it',
                      'role': 'developer', 'host': 'codex'}, 'execution-resume-proof-changed')

    def test_same_task_trailer_without_retained_delivery_does_not_authorize_resume(self):
        prepared = self.prepare(mode='background')
        self.ok({'op': 'attach-execution', 'op_id': 'attach-for-lost-1', 'assignment': 'build-it', 'attempt': 1, 'handle': 'fixture-handle'})
        self.work(prepared, marker=False)
        self.ok({'op': 'mark-lost', 'op_id': 'lost-fixture-1', 'assignment': 'build-it', 'attempt': 1,
                 'evidence': {'kind': 'terminal-status', 'detail': 'completed'}, 'note': 'Synthetic fixture terminal status, no real host claim.'})
        self.refused({'op': 'prepare-dispatch', 'op_id': 'resume-unbound-2', 'task_id': 'build-it', 'assignment': 'build-it',
                      'role': 'developer', 'host': 'codex'}, 'execution-foreign-source')

    def test_racing_bookkeeping_head_refreshes_without_reset(self):
        self.prepare()
        dirty = cycle_execution._dirty
        raced = []
        def change_after_read(*args):
            result = dirty(*args)
            if not raced:
                raced.append(self.bookkeeping('racing.md'))
            return result
        with patch.object(cycle_execution, '_dirty', side_effect=change_after_read):
            checked = self.check()
        self.assertEqual(checked['execution']['execution_head'], raced[0])
        self.assertEqual(checked['execution']['review_base'], self.base)
        self.assertEqual(self.git('rev-parse', 'HEAD'), raced[0])

    def test_replayed_check_never_claims_stale_proof_current(self):
        self.prepare()
        self.check()
        self.bookkeeping()
        refused = self.refused({'op': 'execution-check', 'op_id': 'execution-start-1', 'assignment': 'build-it', 'attempt': 1},
                               'execution-proof-stale')
        self.assertIn('op_id', refused['errors'][0]['recovery'][0]['caller_fills'])
        self.assertEqual(self.check(op_id='execution-refreshed-2')['execution']['execution_head'], self.git('rev-parse', 'HEAD'))

    def test_attach_preserves_returned_handle_when_proof_storage_is_unavailable(self):
        self.prepare(mode='background')
        request = {'op': 'attach-execution', 'op_id': 'attach-storage-1', 'assignment': 'build-it', 'attempt': 1,
                   'handle': 'fixture-returned-host-handle'}
        with patch.object(cycle_execution, 'retain', side_effect=OSError('private fixture storage detail')):
            attached = self.ok(request)
        entry = load(self.repo, self.cid)['assignments'][0]
        self.assertEqual((entry['state'], entry['agent']), ('running', request['handle']))
        self.assertEqual(attached['execution_observation']['code'], 'execution-proof-unavailable')
        self.assertFalse(attached['execution_observation']['ok'])
        self.assertNotIn('private fixture', json.dumps(attached))
        self.assertEqual(self.ok(request)['execution_observation'], attached['execution_observation'])

    def test_delivery_retains_result_when_proof_storage_is_unavailable(self):
        prepared = self.prepare()
        sha = self.work(prepared)
        request = {'op': 'deliver', 'op_id': 'deliver-storage-1', 'assignment': 'build-it', 'attempt': 1,
                   'outcome': 'done', 'commits': [sha]}
        with patch.object(cycle_execution, 'retain', side_effect=OSError('private fixture storage detail')):
            delivered = self.ok(request)
        doc = load(self.repo, self.cid)
        entry = doc['assignments'][0]
        self.assertEqual(entry['state'], 'finished')
        self.assertEqual(entry['delivery']['commits'], [sha])
        self.assertEqual((tree(self.repo).docs_root / entry['delivery']['path']).read_bytes(),
                         Path(prepared['result_path']).read_bytes())
        self.assertFalse(delivered['execution_observation']['ok'])
        self.assertNotIn('private fixture', json.dumps(delivered))
        self.assertEqual(self.ok(request)['execution_observation'], delivered['execution_observation'])

    def test_explicit_check_refuses_safely_when_proof_storage_is_unavailable(self):
        self.prepare()
        with patch.object(cycle_execution, 'retain', side_effect=OSError('private fixture storage detail')):
            refused = self.refused({'op': 'execution-check', 'op_id': 'check-storage-1', 'assignment': 'build-it',
                                    'attempt': 1}, 'execution-proof-unavailable')
        self.assertNotIn('private fixture', json.dumps(refused))

    def test_replayed_edited_checkpoint_requires_current_token_clean_start(self):
        prepared = self.prepare()
        self.check()
        (self.repo / 'src/a.py').write_text('answer = 3\n')
        checkpoint = {'op': 'execution-check', 'op_id': 'checkpoint-before-resume-2', 'assignment': 'build-it',
                      'attempt': 1, 'edited_paths': ['src/a.py']}
        self.ok(checkpoint)
        head = self.git('rev-parse', 'HEAD')
        mutate(self.repo, self.cid, 'assignment', id='build-it', resume_token=prepared['delivery_token'],
               note='offline fixture resumes the same execution')
        self.assertEqual(self.git('rev-parse', 'HEAD'), head)
        self.refused({**checkpoint, 'op_id': 'checkpoint-after-resume-3'}, 'execution-clean-start-required')
        self.refused(checkpoint, 'execution-clean-start-required')

    def checkpointed_commit(self, *, marker=True):
        prepared = self.prepare(mode='background')
        self.ok({'op': 'attach-execution', 'op_id': 'active-attach-1', 'assignment': 'build-it', 'attempt': 1,
                 'handle': 'fixture-active-handle'})
        self.check()
        (self.repo / 'src/a.py').write_text('answer = 2\n')
        self.check(op_id='active-precommit-2', edited_paths=['src/a.py'])
        return prepared, self.work(prepared, marker=marker)

    def test_active_attempt_can_commit_index_then_working_content_without_handback(self):
        self.prepare()
        self.check()
        (self.repo / 'src/a.py').write_text('answer = 2\n')
        self.git('add', 'src/a.py')
        (self.repo / 'src/a.py').write_text('answer = 3\n')
        self.check(op_id='active-staged-checkpoint-2', edited_paths=['src/a.py'])
        self.git('commit', '-q', '-m', 'first active commit\n\nCycle-Task: build-it')
        first = self.git('rev-parse', 'HEAD')
        middle = self.check(op_id='active-second-checkpoint-3', edited_paths=['src/a.py'])
        self.assertEqual(middle['execution']['commits'][0]['kind'], 'same-attempt-commit')
        self.git('add', 'src/a.py')
        self.git('commit', '-q', '-m', 'second active commit\n\nCycle-Task: build-it')
        last = self.check(op_id='active-final-check-4')
        self.assertEqual([row['sha'] for row in last['execution']['commits']], [first, self.git('rev-parse', 'HEAD')])
        self.assertTrue(all(row['kind'] == 'same-attempt-commit' for row in last['execution']['commits']))
        self.assertEqual(load(self.repo, self.cid)['assignments'][0]['base'], self.base)

    def test_source_changed_after_precommit_checkpoint_is_not_admitted(self):
        prepared = self.prepare()
        self.check()
        (self.repo / 'src/a.py').write_text('answer = 2\n')
        self.check(op_id='active-captured-2', edited_paths=['src/a.py'])
        self.work(prepared, body='answer = 999\n')
        self.refused({'op': 'execution-check', 'op_id': 'active-mismatch-3', 'assignment': 'build-it', 'attempt': 1},
                     'execution-foreign-source')

    def test_pending_checkpoint_from_previous_token_does_not_admit_a_new_commit(self):
        prepared = self.prepare()
        self.check()
        (self.repo / 'src/a.py').write_text('answer = 2\n')
        self.check(op_id='active-before-rotation-2', edited_paths=['src/a.py'])
        mutate(self.repo, self.cid, 'assignment', id='build-it', resume_token=prepared['delivery_token'],
               note='offline fixture resumes before committing')
        self.work(prepared)
        self.refused({'op': 'execution-check', 'op_id': 'active-after-rotation-3', 'assignment': 'build-it', 'attempt': 1},
                     'execution-foreign-source')

    def test_lost_attempt_resumes_only_source_with_retained_checkpoint_provenance(self):
        prepared, sha = self.checkpointed_commit(marker=False)
        self.check(op_id='active-record-commit-3')
        mutate(self.repo, self.cid, 'assignment', id='build-it', resume_token=prepared['delivery_token'],
               note='offline fixture resumes after commit admission')
        self.check(op_id='active-check-rotated-4')
        self.ok({'op': 'mark-lost', 'op_id': 'active-typed-loss-4', 'assignment': 'build-it', 'attempt': 1,
                 'evidence': {'kind': 'terminal-status', 'detail': 'completed'}, 'note': 'Offline fixture affirmative host termination.'})
        resumed = self.prepare(op_id='active-resume-5', assignment='build-it')
        self.assertEqual(resumed['base'], self.base)
        row = next(row for row in resumed['execution']['commits'] if row['sha'] == sha)
        self.assertEqual(row['kind'], 'same-task-resume')
        self.assertIn('checkpoint', row['provenance'])

    def test_failed_attempt_preserves_admitted_source_without_inventing_delivery_commits(self):
        _, sha = self.checkpointed_commit()
        self.check(op_id='active-record-commit-3')
        self.ok({'op': 'deliver', 'op_id': 'active-failed-4', 'assignment': 'build-it', 'attempt': 1, 'outcome': 'failed'})
        self.assertEqual(load(self.repo, self.cid)['assignments'][0]['delivery']['commits'], [])
        resumed = self.prepare(op_id='active-resume-5', assignment='build-it')
        self.assertEqual(next(row for row in resumed['execution']['commits'] if row['sha'] == sha)['kind'], 'same-task-resume')

    def test_missing_or_corrupt_checkpoint_cannot_admit_source(self):
        _, _ = self.checkpointed_commit()
        ref = load(self.repo, self.cid)['assignments'][0]['execution']['proof']
        path = tree(self.repo).docs_root / ref['path']
        raw = path.read_bytes()
        for contents in (None, raw + b'corrupt fixture checkpoint\n'):
            with self.subTest(missing=contents is None):
                if contents is None:
                    path.unlink()
                else:
                    path.write_bytes(contents)
                self.refused({'op': 'execution-check', 'op_id': 'active-unavailable-3', 'assignment': 'build-it', 'attempt': 1},
                             'execution-checkpoint-unavailable')
        path.write_bytes(raw)

    def test_captured_source_in_a_merge_still_requires_normal_integration(self):
        self.prepare()
        self.check()
        branch = self.git('symbolic-ref', '--short', 'HEAD')
        self.git('checkout', '-q', '-b', 'checkpoint-side')
        self.bookkeeping('checkpoint-side.md')
        self.git('checkout', '-q', branch)
        self.bookkeeping('checkpoint-main.md')
        self.git('merge', '--no-ff', '--no-commit', 'checkpoint-side')
        (self.repo / 'src/a.py').write_text('answer = 2\n')
        self.check(op_id='active-merge-checkpoint-2', edited_paths=['src/a.py'])
        self.git('add', 'src/a.py')
        self.git('commit', '-q', '-m', 'merge needs integration\n\nCycle-Task: build-it')
        self.refused({'op': 'execution-check', 'op_id': 'active-merge-refuse-3', 'assignment': 'build-it', 'attempt': 1},
                     'execution-foreign-source')

    def test_partial_file_commit_preserves_other_captured_edits_for_next_commit(self):
        self.partial_file_commit()

    def test_partial_file_commit_preserves_captured_deletion_for_next_commit(self):
        self.partial_file_commit(delete=True)

    def partial_file_commit(self, *, delete=False):
        (self.repo / 'src/b.py').write_text('other = 1\n')
        self.git('add', 'src/b.py')
        self.git('commit', '-q', '-m', 'tracked second-file fixture')
        self.prepare()
        self.check()
        (self.repo / 'src/a.py').write_text('answer = 2\n')
        if delete:
            (self.repo / 'src/b.py').unlink()
        else:
            (self.repo / 'src/b.py').write_text('other = 3\n')
        self.check(op_id='partial-precommit-2', edited_paths=['src/a.py', 'src/b.py'])
        self.git('add', 'src/a.py')
        self.git('commit', '-q', '-m', 'first subset commit\n\nCycle-Task: build-it')
        first = self.git('rev-parse', 'HEAD')
        remaining = self.check(op_id='partial-next-3', edited_paths=['src/b.py'])
        self.assertEqual(remaining['execution']['dirty_paths'], ['src/b.py'])
        self.assertEqual(set(remaining['execution']['pending_sources']), {'src/b.py'})
        self.git('add', 'src/b.py')
        self.git('commit', '-q', '-m', 'second subset commit\n\nCycle-Task: build-it')
        final = self.check(op_id='partial-final-4')
        self.assertEqual([row['sha'] for row in final['execution']['commits']], [first, self.git('rev-parse', 'HEAD')])
        self.assertTrue(all(row['kind'] == 'same-attempt-commit' for row in final['execution']['commits']))

    def test_checkpoint_does_not_admit_an_unsealed_file_in_the_commit(self):
        self.prepare()
        self.check()
        (self.repo / 'src/a.py').write_text('answer = 2\n')
        self.check(op_id='sealed-before-commit-2', edited_paths=['src/a.py'])
        (self.repo / 'src/unsealed.py').write_text('not_captured = 1\n')
        self.git('add', 'src')
        self.git('commit', '-q', '-m', 'extra source is unproven\n\nCycle-Task: build-it')
        self.refused({'op': 'execution-check', 'op_id': 'sealed-refuse-3', 'assignment': 'build-it', 'attempt': 1},
                     'execution-foreign-source')


if __name__ == '__main__':
    unittest.main()
