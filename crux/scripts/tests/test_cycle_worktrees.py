"""finish removes the cycle's own merged, clean agent worktrees and lists every other one.

The friction (X2): ten linked worktrees stayed under .claude/worktrees after their units were
integrated, because nothing removed them. The repository here holds one worktree of each kind:
merged with this cycle's trailer and clean (removed), unmerged, dirty, another cycle's, detached,
and one outside .claude/worktrees. Only the first is removed.
"""
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cycle_worktrees
from cycle_workflow import create, load, mutate
from test_cycle_ops_finish import FinishBase


def git(cwd, *argv):
    env = {**os.environ, 'GIT_AUTHOR_NAME': 't', 'GIT_AUTHOR_EMAIL': 't@x', 'GIT_COMMITTER_NAME': 't', 'GIT_COMMITTER_EMAIL': 't@x'}
    return subprocess.run(['git', *argv], cwd=cwd, check=True, capture_output=True, text=True, env=env).stdout.strip()


class Worktrees:
    """Builds the six worktrees in `self.repo`, whose main branch is checked out."""

    def commit(self, cwd, name, trailer=None):
        (Path(cwd) / name).write_text(name)
        git(cwd, 'add', name)
        git(cwd, 'commit', '-q', '-m', f'add {name}' + (f'\n\nCycle-Task: {trailer}' if trailer else ''))
        return git(cwd, 'rev-parse', 'HEAD')

    def worktree(self, name, base='.claude/worktrees'):
        path = self.repo / base / name
        git(self.repo, 'worktree', 'add', '-q', '-b', f'wt-{name}', str(path))
        return path

    def build(self, mine='build-it', other='someone-else'):
        info = self.repo / '.git' / 'info'
        info.mkdir(parents=True, exist_ok=True)
        with open(info / 'exclude', 'a') as handle:
            handle.write('.claude/\nside/\n')
        self.paths = {}
        merged = self.paths['merged'] = self.worktree('merged')
        self.commit(merged, 'merged.txt', mine)
        git(self.repo, 'merge', '-q', '--ff-only', 'wt-merged')
        unmerged = self.paths['unmerged'] = self.worktree('unmerged')
        self.commit(unmerged, 'unmerged.txt', mine)
        dirty = self.paths['dirty'] = self.worktree('dirty')
        self.commit(dirty, 'dirty.txt', mine)
        git(self.repo, 'merge', '-q', '--ff-only', 'wt-dirty')
        (dirty / 'scratch.txt').write_text('left behind')
        foreign = self.paths['other-cycle'] = self.worktree('other-cycle')
        self.commit(foreign, 'other.txt', other)
        git(self.repo, 'merge', '-q', '--ff-only', 'wt-other-cycle')
        detached = self.paths['detached'] = self.repo / '.claude/worktrees/detached'
        git(self.repo, 'worktree', 'add', '-q', '--detach', str(detached))
        outside = self.paths['outside'] = self.worktree('outside', base='side')
        self.commit(outside, 'outside.txt', mine)
        git(self.repo, 'merge', '-q', '--ff-only', 'wt-outside')

    def branches(self):
        return set(git(self.repo, 'branch', '--format=%(refname:short)').split())


class CleanupTests(Worktrees, unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name).resolve() / 'repo'
        self.repo.mkdir()
        git(self.repo, 'init', '-q', '-b', 'main')
        self.commit(self.repo, 'base.txt')
        docs=self.repo/'bionic';docs.mkdir()
        (docs/'manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\n')
        self.build()

    def tearDown(self):
        self.tmp.cleanup()

    def test_only_the_merged_clean_worktree_of_this_cycle_is_removed(self):
        before = len(cycle_worktrees.linked(self.repo))
        self.assertEqual(before, 6)
        found = cycle_worktrees.cleanup(self.repo, {'build-it', 'plan'})
        self.assertEqual(found['removed'], [{'path': str(self.paths['merged']), 'branch': 'wt-merged', 'task': 'build-it'}])
        self.assertFalse(self.paths['merged'].exists())
        self.assertNotIn('wt-merged', self.branches())
        reasons = {Path(k['path']).name: k['reason'] for k in found['kept']}
        self.assertEqual(set(reasons), {'unmerged', 'dirty', 'other-cycle', 'detached', 'outside'})
        self.assertTrue(reasons['unmerged'].startswith('not merged'))
        self.assertTrue(reasons['dirty'].startswith('dirty'))
        self.assertIn('Cycle-Task', reasons['other-cycle'])
        self.assertTrue(reasons['detached'].startswith('detached'))
        self.assertTrue(reasons['outside'].startswith('not under'))
        for name in ('unmerged', 'dirty', 'other-cycle', 'detached', 'outside'):
            self.assertTrue(self.paths[name].is_dir(), name)
        self.assertEqual(len(cycle_worktrees.linked(self.repo)), 5)
        self.assertTrue({'wt-unmerged', 'wt-dirty', 'wt-other-cycle', 'wt-outside'} <= self.branches())
        self.assertTrue((self.paths['dirty'] / 'scratch.txt').is_file())

    def test_a_second_cleanup_removes_nothing_more(self):
        cycle_worktrees.cleanup(self.repo, {'build-it'})
        again = cycle_worktrees.cleanup(self.repo, {'build-it'})
        self.assertEqual(again['removed'], [])
        self.assertEqual(len(again['kept']), 5)

    def test_a_locked_worktree_is_kept(self):
        git(self.repo, 'worktree', 'lock', str(self.paths['merged']))
        found = cycle_worktrees.cleanup(self.repo, {'build-it'})
        self.assertEqual(found['removed'], [])
        self.assertIn({'path': str(self.paths['merged']), 'branch': 'wt-merged', 'reason': 'locked'}, found['kept'])

    def test_a_directory_that_is_not_a_repository_yields_nothing(self):
        with tempfile.TemporaryDirectory() as empty:
            self.assertEqual(cycle_worktrees.cleanup(empty, {'build-it'}), {'removed': [], 'kept': []})

    def other_attempt(self, task='build-it', result_path=None, *, state='running', paused=False):
        docs=self.repo/'bionic';docs.mkdir(exist_ok=True)
        (docs/'manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\n')
        (docs/'objectives.md').write_text('Preserve work and reduce ceremony.')
        doc=create(self.repo,'quick-fix','Other cycle','Preserve its work',['base.txt'],['Correct'],'builder','tester')
        mutate(self.repo,doc['id'],'task-add',task={'id':task,'phase':'build','description':'Other work',
                                                  'depends_on':[],'status':'pending','expected_evidence':['Result']})
        mutate(self.repo,doc['id'],'assignment',id='other-worker',state='running',role='developer',task=task,
               result_path=result_path or str(self.repo/'elsewhere-result.md'))
        if state!='running':mutate(self.repo,doc['id'],'assignment',id='other-worker',state=state,note='Fixture host execution ended')
        if paused:mutate(self.repo,doc['id'],'pause',reason='Fixture owner pause')
        return doc['id']

    def test_another_active_cycles_open_task_id_preserves_merged_clean_worktree(self):
        cid=self.other_attempt()
        found=cycle_worktrees.cleanup(self.repo,{'build-it'})
        self.assertEqual(found['removed'],[])
        reason=next(row['reason'] for row in found['kept'] if row['path']==str(self.paths['merged']))
        self.assertIn(cid,reason);self.assertIn('other-worker',reason);self.assertIn('task',reason)
        self.assertTrue(self.paths['merged'].is_dir());self.assertIn('wt-merged',self.branches())

    def test_another_attempts_recorded_result_path_preserves_worktree_with_a_different_task(self):
        path=self.paths['merged']/'result.md'
        cid=self.other_attempt(task='different-task',result_path=str(path.relative_to(self.repo)))
        found=cycle_worktrees.cleanup(self.repo,{'build-it'})
        self.assertEqual(found['removed'],[])
        reason=next(row['reason'] for row in found['kept'] if row['path']==str(self.paths['merged']))
        self.assertIn(cid,reason);self.assertIn('result_path',reason)
        self.assertFalse(path.exists(),'recorded path is a delivery promise, not a dirty file')

    def test_a_paused_cycles_open_attempt_still_preserves_its_worktree(self):
        self.other_attempt(paused=True)
        self.assertEqual(cycle_worktrees.cleanup(self.repo,{'build-it'})['removed'],[])
        self.assertTrue(self.paths['merged'].is_dir())

    def test_path_ownership_compares_canonical_paths(self):
        alias=self.repo/'worker-alias';alias.symlink_to(self.paths['merged'],target_is_directory=True)
        self.other_attempt(task='different-task',result_path=str(alias/'report.md'))
        found=cycle_worktrees.cleanup(self.repo,{'build-it'})
        self.assertEqual(found['removed'],[])
        self.assertTrue(self.paths['merged'].is_dir())

    def test_finished_attempt_does_not_prevent_normal_cleanup(self):
        self.other_attempt(state='finished')
        found=cycle_worktrees.cleanup(self.repo,{'build-it'})
        self.assertEqual([row['path'] for row in found['removed']],[str(self.paths['merged'])])

    def test_closed_cycle_with_a_historical_open_assignment_does_not_hold_a_worktree(self):
        cid=self.other_attempt()
        path=self.repo/'bionic/cycles'/cid/'cycle.json'
        doc=json.loads(path.read_text());doc['status']='completed';path.write_text(json.dumps(doc))
        found=cycle_worktrees.cleanup(self.repo,{'build-it'})
        self.assertEqual([row['path'] for row in found['removed']],[str(self.paths['merged'])])

    def test_unreadable_ownership_keeps_candidates_and_reports_the_record(self):
        cid=self.other_attempt()
        path=self.repo/'bionic/cycles'/cid/'cycle.json';path.write_text('{')
        found=cycle_worktrees.cleanup(self.repo,{'build-it'})
        self.assertEqual(found['removed'],[])
        reason=next(row['reason'] for row in found['kept'] if row['path']==str(self.paths['merged']))
        self.assertIn('ownership',reason);self.assertIn(cid,reason)


class FinishRemovesWorktreesTests(Worktrees, FinishBase):
    """End to end: the typed finish of a release cycle removes its merged worktree and lists the rest."""

    def finish_release(self, protection=None):
        doc = create(self.repo, 'release', 'Ship', 'Release it', ['src'], ['shipped'], 'builder', 'tester', release_list='official')
        self.v3(doc['id'])
        cid = doc['id']
        tasks = [t['id'] for t in load(self.repo, cid)['plan']['tasks']]
        self.build(mine=tasks[0])
        if protection:
            other=create(self.repo,'quick-fix','Other','Protect its worktree',['src'],['Correct'],'builder','tester')
            task=tasks[0] if protection=='task' else 'different-task'
            mutate(self.repo,other['id'],'task-add',task={'id':task,'phase':'build','description':'Other work',
                                                        'depends_on':[],'status':'pending','expected_evidence':['Result']})
            result=str(self.paths['merged']/'worker-result.md') if protection=='path' else str(self.repo/'external-result.md')
            mutate(self.repo,other['id'],'assignment',id='other-worker',state='running',role='developer',task=task,result_path=result)
        for task in tasks:
            sha = self.commit_file(f'src/{task}.txt', task, f'step {task}')
            mutate(self.repo, cid, 'task', task_id=task, state='done', commits=[sha])
        request = {'op': 'finish', 'op_id': 'finish-wt-1', 'expect_revision': self.revision(cid)}
        done = self.ok(request, cid=cid)
        return done,cid,request

    def test_finish_reports_removed_and_kept_worktrees(self):
        done,cid,request=self.finish_release()
        self.assertEqual(done['status'], 'completed')
        self.assertEqual([r['path'] for r in done['worktrees']['removed']], [str(self.paths['merged'])])
        self.assertEqual({Path(k['path']).name for k in done['worktrees']['kept']},
                         {'unmerged', 'dirty', 'other-cycle', 'detached', 'outside'})
        self.assertFalse(self.paths['merged'].exists())
        replay = self.ok(request, cid=cid)
        self.assertTrue(replay['replayed'])

    def test_finish_preserves_a_worktree_another_cycles_open_task_holds(self):
        done,_,_=self.finish_release('task')
        self.assertEqual(done['status'],'completed')
        self.assertEqual(done['worktrees']['removed'],[])
        reason=next(row['reason'] for row in done['worktrees']['kept'] if row['path']==str(self.paths['merged']))
        self.assertIn('other-worker',reason);self.assertIn('task',reason)
        self.assertTrue(self.paths['merged'].is_dir())

    def test_finish_preserves_a_worktree_named_by_another_attempts_result_path(self):
        done,_,_=self.finish_release('path')
        self.assertEqual(done['status'],'completed')
        self.assertEqual(done['worktrees']['removed'],[])
        reason=next(row['reason'] for row in done['worktrees']['kept'] if row['path']==str(self.paths['merged']))
        self.assertIn('other-worker',reason);self.assertIn('result_path',reason)
        self.assertTrue(self.paths['merged'].is_dir())


if __name__ == '__main__':
    unittest.main()
