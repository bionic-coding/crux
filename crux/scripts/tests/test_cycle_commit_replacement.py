"""A rebased commit is replaced in the record and the old id stays traceable."""
import contextlib
import io
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle
import test_cycle_invalidation as inv
from cycle_reconcile import reconcile
from cycle_workflow import CycleError, mutate_tracked, review_basis_digest


class ReplaceCommitTests(inv.InvalidationBase):
    def setUp(self):
        super().setUp()
        self.set_plan()
        self.old = self.commit('first')
        self.do('task', task_id='A', commits=[self.old], stage='integrated', evidence=['ev.md'])
        self.git('commit', '-q', '--amend', '-m', 'first, rebased')
        self.new = self.git('rev-parse', 'HEAD')

    def replace(self, old=None, new=None, note='rebased onto main', **more):
        return mutate_tracked(self.repo, self.cid, 'task', task_id='A', replace_commit=[old or self.old, new or self.new], note=note, **more)

    def test_replaces_in_place_and_keeps_the_old_id_traceable(self):
        other = self.commit('second')
        doc, changed = self.replace(commits=[other])
        task = next(t for t in doc['plan']['tasks'] if t['id'] == 'A')
        self.assertTrue(changed)
        self.assertEqual(task['commits'], [self.new, other])
        self.assertEqual([(r['from'], r['to'], r['note']) for r in task['replaced_commits']], [(self.old, self.new, 'rebased onto main')])
        self.assertTrue(task['replaced_commits'][0]['at'])
        event = doc['history'][-1]
        self.assertEqual((event['action'], event['task']), ('task-updated', 'A'))
        self.assertEqual(event['replaced_commits'], task['replaced_commits'])
        self.assertEqual(event['commits'], task['commits'])

    def test_integrated_is_admitted_once_new_is_on_head(self):
        self.replace()
        doc = self.do('task', task_id='A', stage='integrated', state='done')
        t = next(t for t in doc['plan']['tasks'] if t['id'] == 'A')
        self.assertEqual((t['stage'], t['status'], t['commits']), ('integrated', 'done', [self.new]))

    def test_existing_integrated_refusal_stays_when_new_is_not_on_head(self):
        self.git('checkout', '-q', '-b', 'side'); side = self.commit('side'); self.git('checkout', '-q', 'main')
        with self.assertRaisesRegex(CycleError, 'integrated requires every commit to be an ancestor of HEAD'):
            self.replace(new=side)
        self.assertEqual(self.task('A')['commits'], [self.old])

    def test_repeating_the_identical_replacement_is_a_no_op(self):
        self.replace()
        before = self.doc()
        doc, changed = self.replace()
        self.assertFalse(changed)
        self.assertEqual(doc, self.doc()); self.assertEqual(before, self.doc())
        _, changed = self.replace(old=self.old[:10], new=self.new[:12])
        self.assertFalse(changed)

    def test_old_need_not_resolve_in_git(self):
        self.git('reflog', 'expire', '--expire=now', '--all'); self.git('gc', '-q', '--prune=now')
        doc, changed = self.replace()
        self.assertTrue(changed); self.assertEqual(self.task('A')['commits'], [self.new])

    def test_refuses_an_old_commit_that_is_not_recorded(self):
        other = self.commit('unrelated')
        with self.assertRaisesRegex(CycleError, f'commit {other} is not recorded on this task'):
            self.replace(old=other)

    def test_refuses_an_unresolvable_new_commit(self):
        with self.assertRaisesRegex(CycleError, 'commit deadbeef does not resolve to a commit in this repository'):
            self.replace(new='deadbeef')

    def test_refuses_a_new_commit_that_is_already_recorded(self):
        path = self.repo / 'bionic/cycles' / self.cid / 'cycle.json'
        raw = json.loads(path.read_text())
        next(t for t in raw['plan']['tasks'] if t['id'] == 'A')['commits'].append(self.new)
        path.write_text(json.dumps(raw, indent=2) + '\n')
        with self.assertRaisesRegex(CycleError, 'is already recorded on this task'):
            self.replace()

    def test_refuses_a_missing_note(self):
        for note in (None, '   '):
            with self.assertRaisesRegex(CycleError, '--replace-commit requires --note'):
                self.replace(note=note)
        self.assertEqual(self.task('A')['commits'], [self.old])

    def test_refuses_a_non_hexadecimal_old_id(self):
        with self.assertRaisesRegex(CycleError, 'not a hexadecimal commit id'):
            self.replace(old='zz')

    def test_replacement_is_bookkeeping_and_leaves_the_review_basis_unchanged(self):
        digest = review_basis_digest(self.doc(), 3)
        self.replace()
        self.assertEqual(review_basis_digest(self.doc(), 3), digest)
        self.assertEqual(self.doc()['schema_version'], 2)

    def test_cli_replaces_and_reports_the_new_field_in_the_compact_line(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cycle.main(['--repo-root', str(self.repo), '--compact', 'task', self.cid, '--task-id', 'A', '--replace-commit', self.old, self.new, '--note', 'rebased'])
        line = json.loads(out.getvalue())
        self.assertEqual(code, 0, out.getvalue())
        self.assertEqual(line['task']['commits'], [self.new]); self.assertEqual(line['task']['replaced_commits'][0]['from'], self.old)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cycle.main(['--repo-root', str(self.repo), '--compact', 'task', self.cid, '--task-id', 'A', '--replace-commit', self.old, self.new, '--note', 'rebased'])
        self.assertEqual((code, json.loads(out.getvalue())['changed']), (0, False))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cycle.main(['--repo-root', str(self.repo), 'task', self.cid, '--task-id', 'A', '--replace-commit', self.old, self.new])
        self.assertEqual(code, 1)


class ReconcileReplacedCommitTests(inv.InvalidationBase):
    def test_a_pre_rebase_commit_with_the_trailer_is_not_proposed(self):
        self.set_plan()
        (self.repo / 'w.txt').write_text('w'); self.git('add', 'w.txt')
        self.git('commit', '-q', '-m', f'{self.cid} A: original\n\nCycle-Task: A')
        pre = self.git('rev-parse', 'HEAD')
        self.do('task', task_id='A', commits=[pre], stage='implemented')
        self.git('branch', 'pre-rebase', pre)
        self.git('commit', '-q', '--amend', '-m', f'{self.cid} A: rebased\n\nCycle-Task: A')
        post = self.git('rev-parse', 'HEAD')
        self.do('task', task_id='A', replace_commit=[pre, post], note='rebased')
        report = reconcile(self.repo, self.cid)
        self.assertEqual([d for d in report['discrepancies'] if d['kind'] == 'linked-commit-not-recorded'], [])
        # Positive control: without the replacement record the same commit is proposed.
        path = self.repo / 'bionic/cycles' / self.cid / 'cycle.json'
        raw = json.loads(path.read_text())
        task = next(t for t in raw['plan']['tasks'] if t['id'] == 'A')
        kept = task.pop('replaced_commits')
        path.write_text(json.dumps(raw, indent=2) + '\n')
        control = reconcile(self.repo, self.cid)
        self.assertEqual([d['commits'] for d in control['discrepancies'] if d['kind'] == 'linked-commit-not-recorded'], [[pre]])
        task['replaced_commits'] = kept
        path.write_text(json.dumps(raw, indent=2) + '\n')


if __name__ == '__main__':
    unittest.main()
