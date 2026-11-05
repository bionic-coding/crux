"""The cycle writer commits the cycle record: scope, deferral, idempotence, the commit-record op, inspect.

Every test builds its own temporary git repository. The fixture's .gitignore hides bionic/, so these
tests replace it to make the cycle directory visible to git."""
import contextlib
import fcntl
import io
import json
import os
from pathlib import Path
import shutil
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cycle
import cycle_commit
import cycle_ops
import test_cycle_ops_advance as adv
from cycle_workflow import load

QUOTE = 'Close it.'


class CommitBase(adv.AdvanceBase):
    def setUp(self):
        super().setUp()
        (self.repo / '.gitignore').write_text('*.lock\n__pycache__/\n')
        (self.repo / 'bionic/queue').mkdir()
        (self.repo / 'bionic/queue/cycles.yaml').write_text('format: x\n')
        self.git('add', 'bionic/queue/cycles.yaml')
        self.git('commit', '--only', '-m', 'queue baseline', '--', 'bionic/queue/cycles.yaml')

    def head(self):
        return self.git('rev-parse', 'HEAD')

    def commit_files(self, ref='HEAD'):
        return self.git('show', '--name-only', '--format=', ref).splitlines()

    def message(self, ref='HEAD'):
        return self.git('log', '-1', '--format=%B', ref)

    def pending(self):
        return self.git('status', '--porcelain', '--untracked-files=all', '--', 'bionic/cycles', 'bionic/queue').splitlines()

    def common_lock(self):
        directory = Path(self.git('rev-parse', '--path-format=absolute', '--git-common-dir')) / 'crux'
        directory.mkdir(exist_ok=True)
        return directory / 'full-suite.lock'

    @contextlib.contextmanager
    def suite_running(self):
        with self.common_lock().open('a') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            yield

    def at_test_phase_start(self):
        self.deliver_build()
        (self.repo / 'src/b.py').write_text('other = 1\n')
        self.git('add', 'src/b.py')


class RecordCommitTests(CommitBase):
    def test_advance_commits_only_the_record_and_leaves_other_staged_files(self):
        self.at_test_phase_start()
        before = self.head()
        rev = self.revision()
        # A concurrent queue change belongs to its own writer, not this cycle commit.
        (self.repo / 'bionic/queue/cycles.yaml').write_text('format: y\n')
        response = self.ok(self.advance('advance-b1'))
        record = response['record_commit']
        self.assertTrue(record['changed'], record)
        self.assertNotEqual(self.head(), before)
        self.assertEqual(record['commit'], self.head())
        files = self.commit_files()
        self.assertIn(f'bionic/cycles/{self.cid}/cycle.json', files)
        self.assertNotIn('bionic/queue/cycles.yaml', files)
        self.assertTrue(all(f.startswith(f'bionic/cycles/{self.cid}/') for f in files), files)
        self.assertEqual(self.git('diff', '--cached', '--name-only').splitlines(), ['src/b.py'])
        self.assertEqual(len(self.pending()), 1)
        self.assertTrue(self.pending()[0].endswith('bionic/queue/cycles.yaml'))
        self.assertEqual(self.message().strip(), f'{self.cid} record: advance build->verify (rev {rev + 1})')
        self.assertNotIn('Cycle-Task', self.message())

    def test_an_identical_repeat_commits_nothing(self):
        self.at_test_phase_start()
        rev = self.revision()
        self.ok(self.advance('advance-b1'))
        head = self.head()
        again = self.ok({'op': 'advance', 'op_id': 'advance-b1', 'expect_revision': rev})
        self.assertTrue(again['replayed'])
        self.assertEqual(again['record_commit'], {**again['record_commit'], 'changed': False, 'commit': None, 'deferred': None})
        self.assertEqual(self.head(), head)

    def test_a_full_suite_lock_defers_and_the_next_commit_record_catches_up(self):
        self.at_test_phase_start()
        before = self.head()
        with self.suite_running():
            response = self.ok(self.advance('advance-b1'))
            self.assertEqual(response['phase'], 'verify', 'the operation itself must still succeed')
            self.assertEqual((response['record_commit']['changed'], response['record_commit']['deferred']), (False, 'full-suite-running'))
            self.assertEqual(self.head(), before)
            self.assertTrue(self.pending())
            seen = self.ok({'op': 'inspect'})
            self.assertEqual(seen['record']['deferred'], 'full-suite-running')
        caught = self.ok({'op': 'commit-record'})
        self.assertTrue(caught['changed'], caught)
        self.assertEqual(self.pending(), [])
        self.assertEqual(self.message().strip(), f'{self.cid} record: checkpoint (rev {self.revision()})')

    def test_a_merge_a_rebase_and_an_index_lock_defer(self):
        self.at_test_phase_start()
        git_dir = Path(self.git('rev-parse', '--absolute-git-dir'))
        rev = self.revision()
        # The delivery committed the record, so give the record something pending to defer.
        (self.repo / f'bionic/cycles/{self.cid}/note.md').write_text('pending\n')
        for marker, reason, make in (('MERGE_HEAD', 'operation-in-progress', Path.write_text), ('rebase-merge', 'operation-in-progress', Path.mkdir),
                                     ('index.lock', 'index-locked', Path.write_text)):
            path = git_dir / marker
            make(path, '') if make is Path.write_text else make(path)
            self.addCleanup(lambda p=path: shutil.rmtree(p) if p.is_dir() else p.unlink(missing_ok=True))
            found = self.ok({'op': 'commit-record'})
            self.assertEqual((found['changed'], found['deferred']), (False, reason), marker)
            shutil.rmtree(path) if path.is_dir() else path.unlink()
        self.assertEqual(self.revision(), rev)

    def test_outside_a_git_repository_defers(self):
        shutil.rmtree(self.repo / '.git')
        found = self.ok({'op': 'commit-record'})
        self.assertEqual((found['changed'], found['deferred']), (False, 'not-a-git-repository'))

    def test_commit_record_op_commits_then_repeats_as_a_no_op(self):
        first = self.ok({'op': 'commit-record'})
        self.assertTrue(first['changed'], first)
        self.assertEqual(self.pending(), [])
        self.assertEqual(self.message().strip(), f'{self.cid} record: checkpoint (rev {self.revision()})')
        head = self.head()
        second = self.ok({'op': 'commit-record'})
        self.assertEqual((second['changed'], second['deferred'], second['commit']), (False, None, None))
        self.assertEqual(self.head(), head)

    def test_commit_record_accepts_and_echoes_an_op_id_and_admits_no_other_field(self):
        found = self.ok({'op': 'commit-record', 'op_id': 'commit-0001'})
        self.assertEqual(found['op_id'], 'commit-0001')
        self.assertTrue(found['changed'], found)
        self.assertNotIn('commit-0001', json.dumps(load(self.repo, self.cid)['operations']), 'commit-record journals nothing')
        self.refused({'op': 'commit-record', 'op_id': 'x'}, 'invalid-request')
        self.refused({'op': 'commit-record', 'note': 'x'}, 'invalid-request')

    def test_commit_record_never_commits_other_staged_work(self):
        (self.repo / 'src/c.py').write_text('x = 1\n')
        self.git('add', 'src/c.py')
        found = self.ok({'op': 'commit-record'})
        self.assertTrue(all(f.startswith('bionic/') for f in self.commit_files()), self.commit_files())
        self.assertEqual(self.git('diff', '--cached', '--name-only').splitlines(), ['src/c.py'])
        self.assertTrue(found['changed'])

    def test_owner_exception_commits(self):
        response = self.ok({'op': 'owner-exception', 'op_id': 'exception-01', 'quote': QUOTE, 'conversation': 'Owner session', 'date': '2026-10-30'})
        self.assertTrue(response['record_commit']['changed'])
        self.assertEqual(self.message().strip(), f"{self.cid} record: owner-exception (rev {load(self.repo, self.cid)['revision']})")

    def test_the_low_level_pause_commits(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cycle.main(['--repo-root', str(self.repo), 'pause', self.cid, '--reason', 'waiting on the owner', '--compact'])
        self.assertEqual(code, 0, out.getvalue())
        self.assertTrue(json.loads(out.getvalue())['record_commit']['changed'])
        self.assertIn(' record: pause (rev ', self.message())
        self.assertEqual(self.pending(), [])

    def test_a_deferred_commit_leaves_the_record_pending_for_inspect(self):
        with self.suite_running():
            prepared = self.prepare()
        self.assertEqual(prepared['record_commit']['deferred'], 'full-suite-running')
        self.assertTrue(self.pending())
        seen = self.ok({'op': 'inspect'})
        self.assertTrue(seen['record']['pending'])
        self.assertIn(f'bionic/cycles/{self.cid}/cycle.json', seen['record']['files'])
        offered = [a for a in seen['actions'] if a.get('request') == {'op': 'commit-record'}]
        self.assertEqual(len(offered), 1, seen['actions'])
        self.assertEqual(self.check_requests_validate(offered), offered)
        self.ok({'op': 'commit-record'})
        seen = self.ok({'op': 'inspect'})
        self.assertFalse(seen['record']['pending'])
        self.assertFalse([a for a in seen['actions'] if a.get('request') == {'op': 'commit-record'}])


class ModuleTests(unittest.TestCase):
    def test_the_operation_list_names_commit_record(self):
        self.assertIn('commit-record', cycle_ops.OPERATIONS)
        self.assertEqual(cycle_commit.COMMITTING, ('advance', 'finish', 'owner-exception', 'prepare-dispatch', 'attach-execution',
                                                   'deliver', 'mark-lost', 'execution-check', 'child-link', 'release-continue'))


if __name__ == '__main__':
    unittest.main()
