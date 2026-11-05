"""Queue writes commit the queue file, scope values split on commas, and `queue list` is compact.

Every test builds its own temporary repository whose docs_dir is `notes`."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_cycle_queue as tq

NEW = ['add', '--title', 'T', '--outcome', 'Deliver T', '--type', 'quick-fix', '--scope', 'src', '--acceptance', 'ok']


class GitBase(tq.Base):
    def setUp(self):
        super().setUp()
        (self.repo / '.gitignore').write_text('.lock\n*.lock\n__pycache__/\n')
        for name in 'abc':
            (self.repo / f'src/{name}.py').write_text(f'{name} = 1\n')
        self.git('init', '-q')
        self.git('config', 'user.email', 't@example.com')
        self.git('config', 'user.name', 'T')
        self.git('add', '-A')
        self.git('commit', '-q', '-m', 'base')

    def git(self, *argv):
        done = subprocess.run(['git', '-C', str(self.repo), *argv], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout.strip()

    def commit_files(self):
        return self.git('show', '--name-only', '--format=', 'HEAD').splitlines()


class QueueCommitTests(GitBase):
    def test_add_commits_only_the_queue_file(self):
        (self.repo / 'src/staged.py').write_text('s = 1\n')
        self.git('add', 'src/staged.py')
        before = self.git('rev-parse', 'HEAD')
        response = self.ok(*NEW)
        commit = response['queue_commit']
        self.assertTrue(commit['changed'], commit)
        self.assertNotEqual(self.git('rev-parse', 'HEAD'), before)
        self.assertEqual(commit['commit'], self.git('rev-parse', 'HEAD'))
        self.assertEqual(self.commit_files(), ['notes/queue/cycles.yaml'])
        self.assertEqual(self.git('status', '--porcelain'), 'A  src/staged.py')
        self.assertIn('add Q-0001', self.git('log', '-1', '--format=%s'))

    def test_clean_status_after_add(self):
        self.ok(*NEW)
        self.assertEqual(self.git('status', '--porcelain'), '')

    def test_every_mutating_op_commits(self):
        a = self.ok(*NEW)['item']['id']
        b = self.ok(*NEW)['item']['id']
        steps = [('hold', a, '--reason', 'wait'), ('unhold', a), ('move', a, '--position', '2'), ('edit', a, '--title', 'T2'),
                 ('authorize', '--kind', 'next-n', '--count', '2', '--instruction', 'go', '--date', tq.DATE),
                 ('revoke', '--reason', 'stop'), ('remove', b)]
        for step in steps:
            before = self.git('rev-parse', 'HEAD')
            response = self.ok(*step)
            self.assertTrue(response['queue_commit']['changed'], (step, response))
            self.assertNotEqual(self.git('rev-parse', 'HEAD'), before, step)
            self.assertEqual(self.git('status', '--porcelain'), '', step)
        self.assertIn('authorize next-n 2', self.git('log', '--format=%s', '-n', '3').splitlines()[2])

    def test_index_lock_defers_but_the_add_succeeds(self):
        before = self.git('rev-parse', 'HEAD')
        lock = Path(self.git('rev-parse', '--absolute-git-dir')) / 'index.lock'
        lock.write_text('')
        response = self.ok(*NEW)
        self.assertEqual(response['queue_commit']['deferred'], 'index-locked')
        self.assertFalse(response['queue_commit']['changed'])
        self.assertTrue((self.repo / 'notes/queue/cycles.yaml').exists())
        lock.unlink()
        self.assertEqual(self.git('rev-parse', 'HEAD'), before)

    def test_outside_a_repository_defers(self):
        base = tq.Base
        case = base('setUp')
        case.setUp()
        self.addCleanup(case.temp.cleanup)
        done = subprocess.run(['git', '-C', str(case.repo), 'rev-parse'], capture_output=True)
        if done.returncode == 0:
            self.skipTest('the temporary directory lies inside a repository')
        code, payload = _cli(case, *NEW)
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload['queue_commit']['deferred'], 'not-a-git-repository')

    def test_start_next_commits_the_queue_and_the_record_together(self):
        """One commit holds the queue file and the new cycle record, and the tree is clean after it."""
        self.ok(*NEW)
        self.authorize('next')
        (self.repo / 'src/staged.py').write_text('s = 1\n')
        self.git('add', 'src/staged.py')
        before = self.git('rev-parse', 'HEAD')
        code, payload = self.start()
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload['outcome'], 'started')
        self.assertNotIn('queue_commit', payload)
        record = payload['record_commit']
        self.assertTrue(record['changed'], record)
        self.assertEqual(self.git('rev-parse', 'HEAD~1'), before, 'exactly one commit')
        self.assertEqual(record['commit'], self.git('rev-parse', 'HEAD'))
        files = self.commit_files()
        self.assertIn('notes/queue/cycles.yaml', files)
        self.assertTrue(any(f.startswith('notes/cycles/') and f.endswith(f"{payload['cycle']}/cycle.json") for f in files), files)
        self.assertTrue(all(f == 'notes/queue/cycles.yaml' or f.startswith('notes/cycles/') for f in files), files)
        self.assertIn(f"{payload['cycle']} record: start Q-0001", self.git('log', '-1', '--format=%s'))
        self.assertEqual(self.git('status', '--porcelain'), 'A  src/staged.py', 'staged work stays staged and nothing else is pending')

    def test_start_next_under_an_index_lock_defers_and_reports(self):
        self.ok(*NEW)
        self.authorize('next')
        lock = Path(self.git('rev-parse', '--absolute-git-dir')) / 'index.lock'
        lock.write_text('')
        self.addCleanup(lambda: lock.unlink(missing_ok=True))
        code, payload = self.start()
        self.assertEqual(code, 0, payload)
        self.assertEqual((payload['record_commit']['changed'], payload['record_commit']['deferred']), (False, 'index-locked'))


def _cli(case, *argv):
    import io
    from contextlib import redirect_stdout
    import cycle
    out = io.StringIO()
    with redirect_stdout(out):
        code = cycle.main(['--repo-root', str(case.repo), '--compact', 'queue', *argv])
    return code, json.loads(out.getvalue())


class ScopeSplitTests(GitBase):
    def cycle_scope(self):
        path = next((self.repo / 'notes/cycles').glob('*CYC-*/cycle.json'))
        return json.loads(path.read_text())['plan']['scope']

    def test_add_splits_a_comma_joined_scope(self):
        argv = [*NEW[:7], '--scope', 'src/a.py, src/b.py,src/c.py,', *NEW[9:]]
        item = self.ok(*argv)['item']
        self.assertEqual(item['scope'], ['src/a.py', 'src/b.py', 'src/c.py'])
        self.authorize('next')
        code, payload = self.start()
        self.assertEqual(code, 0, payload)
        self.assertEqual(self.cycle_scope(), ['src/a.py', 'src/b.py', 'src/c.py'])

    def test_edit_splits_a_comma_joined_scope(self):
        a = self.ok(*NEW)['item']['id']
        edited = self.ok('edit', a, '--scope', 'src/a.py,src/b.py')['item']
        self.assertEqual(edited['scope'], ['src/a.py', 'src/b.py'])

    def test_start_next_splits_a_stored_comma_joined_scope(self):
        a = self.ok(*NEW)['item']['id']
        path = self.repo / 'notes/queue/cycles.yaml'
        text = path.read_text()
        self.assertIn('- src\n', text)
        path.write_text(text.replace('- src\n', '- src/a.py,src/b.py\n', 1))
        self.authorize('next')
        code, payload = self.start()
        self.assertEqual(code, 0, payload)
        self.assertEqual(self.cycle_scope(), ['src/a.py', 'src/b.py'])
        self.assertEqual(self.queue_doc()['items'][0]['scope'], ['src/a.py,src/b.py'])
        self.assertEqual(self.queue_doc()['items'][0]['id'], a)


class CompactListTests(GitBase):
    def test_default_list_is_one_line_per_open_item_and_omits_completed(self):
        a = self.ok(*NEW)['item']['id']
        b = self.ok(*NEW)['item']['id']
        c = self.ok(*NEW, '--depends-on', b)['item']['id']
        self.ok('hold', c, '--reason', 'later')
        self.authorize('next')
        code, payload = self.start()
        self.assertEqual(code, 0, payload)
        self.end_cycle(payload['cycle'], 'completed')
        listing = self.ok('list')
        self.assertEqual(len(listing['items']), 2)
        self.assertTrue(all(isinstance(line, str) and '\n' not in line for line in listing['items']))
        self.assertTrue(listing['items'][0].startswith(b), listing['items'])
        self.assertIn(c, listing['items'][1])
        self.assertIn('later', listing['items'][1])
        self.assertIn(b, listing['items'][1])
        self.assertNotIn(a, ' '.join(listing['items']))
        self.assertEqual(listing['closed'], 1)
        self.assertIn('queue list --full', listing['full'])
        self.assertIn('next', listing)
        self.assertNotIn('authorization_history', listing)

    def test_default_authorization_is_one_line(self):
        self.ok(*NEW)
        self.assertIsNone(self.ok('list')['authorization'])
        self.authorize('next')
        line = self.ok('list')['authorization']
        self.assertIsInstance(line, str)
        self.assertIn('next', line)
        self.assertIn(tq.DATE, line)
        self.assertIn('Q-0001', line)

    def test_full_keeps_the_item_views_and_adds_the_history(self):
        a = self.ok(*NEW)['item']['id']
        self.authorize('next')
        self.ok('revoke', '--reason', 'no')
        full = self.ok('list', '--full')
        self.assertEqual(full['items'][0]['id'], a)
        self.assertIsInstance(full['items'][0], dict)
        self.assertEqual(full['authorization_history'][0]['ended'], 'revoked')
        self.assertIsNone(full['authorization'])


if __name__ == '__main__':
    unittest.main()
