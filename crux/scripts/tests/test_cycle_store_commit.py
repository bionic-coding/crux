"""cycle_store.commit_paths commits only the paths it is given and defers under the record-commit conditions.

Ported from the deleted test_cycle_commit.py, rewritten against the retained cycle_store interface.
Every test builds its own temporary git repository."""
import fcntl
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle_store


class CommitPathsTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.repo = Path(temp.name).resolve()
        self.git('init', '-q')
        self.git('config', 'user.email', 't@example.com')
        self.git('config', 'user.name', 'T')
        (self.repo / '.gitignore').write_text('*.lock\n__pycache__/\nignored/\n')
        (self.repo / 'src').mkdir()
        (self.repo / 'rec').mkdir()
        (self.repo / 'src/b.py').write_text('b = 1\n')
        (self.repo / 'rec/one.json').write_text('{}\n')
        self.git('add', '-A')
        self.git('commit', '-q', '-m', 'base')
        self.cfg = SimpleNamespace(repo_root=self.repo)

    def git(self, *argv):
        done = subprocess.run(['git', '-C', str(self.repo), *argv], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout.strip()

    def head(self):
        return self.git('rev-parse', 'HEAD')

    def change(self):
        (self.repo / 'rec/one.json').write_text('{"changed": true}\n')

    def test_commits_only_the_given_paths_and_leaves_other_staged_files(self):
        (self.repo / 'src/b.py').write_text('b = 2\n')
        self.git('add', 'src/b.py')
        self.change()
        before = self.head()
        result = cycle_store.commit_paths(self.cfg, ['rec/one.json'], 'record: change')
        self.assertTrue(result['changed'], result)
        self.assertNotEqual(self.head(), before)
        self.assertEqual(result['commit'], self.head())
        self.assertEqual(result['paths'], ['rec/one.json'])
        self.assertEqual(self.git('show', '--name-only', '--format=', 'HEAD').splitlines(), ['rec/one.json'])
        self.assertEqual(self.git('diff', '--cached', '--name-only').splitlines(), ['src/b.py'])
        self.assertEqual(self.git('log', '-1', '--format=%B'), 'record: change')

    def test_a_repeat_with_nothing_pending_commits_nothing_and_never_builds_the_message(self):
        self.change()
        cycle_store.commit_paths(self.cfg, ['rec/one.json'], 'first')
        head = self.head()
        called = []
        again = cycle_store.commit_paths(self.cfg, ['rec/one.json'], lambda: called.append(1) or 'second')
        self.assertEqual((again['changed'], again['commit'], again['deferred'], again['paths']), (False, None, None, []))
        self.assertEqual(called, [])
        self.assertEqual(self.head(), head)

    def test_a_callable_message_is_used_when_there_is_something_to_commit(self):
        self.change()
        result = cycle_store.commit_paths(self.cfg, ['rec/one.json'], lambda: 'from callable')
        self.assertTrue(result['changed'], result)
        self.assertEqual(self.git('log', '-1', '--format=%B'), 'from callable')

    def test_a_merge_a_rebase_and_an_index_lock_defer(self):
        self.change()
        git_dir = Path(self.git('rev-parse', '--absolute-git-dir'))
        before = self.head()
        for marker, reason, directory in (('MERGE_HEAD', 'operation-in-progress', False), ('rebase-merge', 'operation-in-progress', True),
                                          ('index.lock', 'index-locked', False)):
            path = git_dir / marker
            path.mkdir() if directory else path.write_text('')
            try:
                found = cycle_store.commit_paths(self.cfg, ['rec/one.json'], 'never')
            finally:
                shutil.rmtree(path) if directory else path.unlink()
            self.assertEqual((found['changed'], found['deferred']), (False, reason), marker)
            self.assertEqual(found['pending'], ['rec/one.json'], marker)
        self.assertEqual(self.head(), before)

    def test_a_full_suite_lock_defers_and_the_next_commit_catches_up(self):
        self.change()
        before = self.head()
        directory = Path(self.git('rev-parse', '--path-format=absolute', '--git-common-dir')) / 'crux'
        directory.mkdir(exist_ok=True)
        with (directory / 'full-suite.lock').open('a') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            found = cycle_store.commit_paths(self.cfg, ['rec/one.json'], 'held')
            self.assertEqual((found['changed'], found['deferred']), (False, 'full-suite-running'))
            self.assertEqual(self.head(), before)
        caught = cycle_store.commit_paths(self.cfg, ['rec/one.json'], 'caught up')
        self.assertTrue(caught['changed'], caught)
        self.assertEqual(self.git('log', '-1', '--format=%B'), 'caught up')

    def test_outside_a_git_repository_defers(self):
        shutil.rmtree(self.repo / '.git')
        done = subprocess.run(['git', '-C', str(self.repo), 'rev-parse'], capture_output=True)
        if done.returncode == 0:
            self.skipTest('the temporary directory lies inside a repository')
        found = cycle_store.commit_paths(self.cfg, ['rec/one.json'], 'never')
        self.assertEqual((found['changed'], found['deferred']), (False, 'not-a-git-repository'))

    def test_ignored_paths_are_skipped_and_named(self):
        (self.repo / 'ignored').mkdir()
        (self.repo / 'ignored/x.json').write_text('{}\n')
        self.change()
        result = cycle_store.commit_paths(self.cfg, ['rec/one.json', 'ignored/x.json'], 'mixed')
        self.assertTrue(result['changed'], result)
        self.assertEqual(result['commit_skipped'], 'tree-ignored')
        self.assertEqual(result['skipped_paths'], ['ignored/x.json'])
        self.assertEqual(self.git('show', '--name-only', '--format=', 'HEAD').splitlines(), ['rec/one.json'])


if __name__ == '__main__':
    unittest.main()
