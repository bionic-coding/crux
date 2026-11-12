"""Environment prerequisites refuse `cycle.py create` and `queue start-next` before any write.

The refusal tests drive the real CLI in a subprocess, with no global, system or environment git
identity: `GIT_CONFIG_GLOBAL` names a file that sets `user.useConfigOnly = true`,
`GIT_CONFIG_NOSYSTEM=1`, and no `GIT_AUTHOR_*`, `GIT_COMMITTER_*` or `EMAIL` variable. Each refusal has
a positive control that differs only in the prerequisite under test. The minor and node probes are
also tested through the injectable runner.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent
sys.path.insert(0, str(SCRIPTS))
import cycle_prereqs  # noqa: E402

CYCLE = SCRIPTS / 'cycle.py'
IDENTITY = {'GIT_AUTHOR_NAME': 't', 'GIT_AUTHOR_EMAIL': 't@example.invalid',
            'GIT_COMMITTER_NAME': 't', 'GIT_COMMITTER_EMAIL': 't@example.invalid'}
RUNNING_MINOR = f'{sys.version_info[0]}.{sys.version_info[1]}'
TS_MANIFEST = json.dumps({'format': 'crux.test-tiers', 'version': 1, 'kind': 'file-glob', 'pattern': '*.test.ts',
                          'areas': {'ui': 'ui'}, 'files': {'a.test.ts': {'tier': 'dev', 'area': 'ui'}}})


def identityless_env(home, path=None):
    """The process environment with no git identity anywhere, as CI runs it."""
    config = Path(home) / 'gitconfig'
    config.write_text('[user]\n\tuseConfigOnly = true\n')
    env = {k: v for k, v in os.environ.items() if not k.startswith(('GIT_AUTHOR_', 'GIT_COMMITTER_')) and k != 'EMAIL'}
    env.update(GIT_CONFIG_GLOBAL=str(config), GIT_CONFIG_NOSYSTEM='1')
    if path is not None:
        env['PATH'] = path
    return env


class CliBase(unittest.TestCase):
    """A git repository fixture whose identity lives in repository config, removed per test when needed."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.repo = base / 'repo'
        self.home = base / 'home'
        self.home.mkdir()
        self.repo.mkdir()
        self.env = identityless_env(self.home)
        (self.repo / '.bionic.yml').write_text('config_version: "1"\ndocs_dir: notes\n')
        (self.repo / 'notes').mkdir()
        (self.repo / 'notes/manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\nadr:\n  next_number: 1\n')
        (self.repo / 'notes/objectives.md').write_text('Mission: useful changes.')
        (self.repo / '.gitignore').write_text('notes/cycles/.lock\nnotes/queue/.lock\n')
        (self.repo / 'src').mkdir()
        (self.repo / 'src/a.py').write_text('x = 1\n')
        (self.repo / 'ui/web/tests').mkdir(parents=True)
        (self.repo / 'ui/web/tests/test-tiers.json').write_text(TS_MANIFEST)
        (self.repo / 'ui/web/tests/a.test.ts').write_text('export {}\n')
        self.git('init', '--quiet', '-b', 'main')
        self.git('config', 'user.name', 't')
        self.git('config', 'user.email', 't@example.invalid')
        self.git('add', '-A')
        self.git('commit', '--quiet', '-m', 'fixture')

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.repo), *args], env=self.env, check=True, capture_output=True, text=True)

    def drop_identity(self):
        self.git('config', '--unset', 'user.name')
        self.git('config', '--unset', 'user.email')

    def declare_minors(self, *minors):
        (self.repo / 'pyproject.toml').write_text('[project]\nname = "fixture"\nversion = "0"\n\n[tool.crux]\npython-versions = '
                                                  + json.dumps(list(minors)) + '\n')
        self.git('add', 'pyproject.toml')
        self.git('commit', '--quiet', '-m', 'minors')

    def cli(self, *argv, env=None):
        done = subprocess.run([sys.executable, str(CYCLE), '--repo-root', str(self.repo), '--compact', *argv],
                              env=env or self.env, capture_output=True, text=True, timeout=120)
        self.assertTrue(done.stdout.strip(), done.stderr)
        return done.returncode, json.loads(done.stdout.strip().splitlines()[-1])

    def create(self, scope='src', env=None):
        return self.cli('create', '--type', 'quick-fix', '--title', 'Fix', '--goal', 'Fix it', '--scope', scope,
                        '--acceptance', 'it works', '--implementer', 'dev-lead', '--coordinator', 'dev-lead', env=env)

    def queue_item(self, scope='src'):
        code, payload = self.cli('queue', 'add', '--title', 'Item', '--outcome', 'Deliver it', '--type', 'quick-fix',
                                 '--scope', scope, '--acceptance', 'it works')
        self.assertEqual(code, 0, payload)
        code, payload = self.cli('queue', 'authorize', '--kind', 'next', '--instruction', 'run it', '--date', '2026-11-07')
        self.assertEqual(code, 0, payload)
        return (self.repo / 'notes/queue/cycles.yaml').read_bytes()

    def no_cycle(self):
        cycles = self.repo / 'notes/cycles'
        self.assertEqual([p.name for p in cycles.iterdir() if p.name != '.lock'] if cycles.exists() else [], [])

    def assert_refused(self, code, payload, expect_code, fix_text):
        self.assertEqual(code, 1, payload)
        self.assertFalse(payload['ok'])
        self.assertEqual(payload['code'], 'environment-prerequisite', payload)
        found = [m for m in payload['missing'] if m['code'] == expect_code]
        self.assertTrue(found, payload)
        self.assertIn(fix_text, found[0]['fix'])
        self.assertIn(fix_text, payload['error'])

    def assert_stopped(self, code, payload, before, expect_code, fix_text):
        self.assertEqual(code, 1, payload)
        stop = payload['stop']
        self.assertEqual(stop['reason'], 'environment-prerequisite', payload)
        self.assertEqual(stop['item'], 'Q-0001')
        self.assertIn(fix_text, stop['detail'])
        self.assertIn(expect_code, [m['code'] for m in stop['missing']])
        self.assertEqual((self.repo / 'notes/queue/cycles.yaml').read_bytes(), before, 'the queue file changed')
        self.no_cycle()

    def assert_started(self, code, payload):
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload['outcome'], 'started', payload)
        self.assertTrue((self.repo / 'notes/cycles' / payload['cycle'] / 'cycle.json').is_file())


class IdentityTests(CliBase):
    def test_create_refuses_an_unresolvable_identity_and_writes_nothing(self):
        self.drop_identity()
        code, payload = self.create()
        self.assert_refused(code, payload, 'git-author-identity', 'git config --global user.name')
        self.assertIn('git-committer-identity', [m['code'] for m in payload['missing']])
        self.assertFalse((self.repo / 'notes/cycles').exists())

    def test_create_with_a_repository_identity_starts(self):
        code, payload = self.create()
        self.assertEqual(code, 0, payload)
        self.assertTrue(payload['ok'])
        self.assertTrue((self.repo / 'notes/cycles/CYC-0001/cycle.json').is_file())

    def test_create_with_an_environment_identity_starts_outside_git(self):
        shutil.rmtree(self.repo / '.git')
        code, payload = self.create()
        self.assert_refused(code, payload, 'git-author-identity', 'git config --global user.email')
        code, payload = self.create(env={**self.env, **IDENTITY})
        self.assertEqual(code, 0, payload)

    def test_start_next_stops_on_an_unresolvable_identity_and_leaves_the_item_pending(self):
        before = self.queue_item()
        self.drop_identity()
        code, payload = self.cli('queue', 'start-next')
        self.assert_stopped(code, payload, before, 'git-author-identity', 'git config --global user.name')
        code, payload = self.cli('queue', 'list')
        self.assertIn('pending', json.dumps(payload))

    def test_start_next_with_a_repository_identity_starts(self):
        self.queue_item()
        self.assert_started(*self.cli('queue', 'start-next'))


@unittest.skipUnless(shutil.which('uv'), 'uv is not on PATH')
class MinorTests(CliBase):
    def test_create_refuses_a_missing_declared_minor(self):
        self.declare_minors('3.99')
        code, payload = self.create()
        self.assert_refused(code, payload, 'python-minor', 'uv python install 3.99')
        self.no_cycle()

    def test_create_with_the_running_minor_declared_starts(self):
        self.declare_minors(RUNNING_MINOR)
        code, payload = self.create()
        self.assertEqual(code, 0, payload)

    def test_start_next_stops_on_a_missing_declared_minor(self):
        self.declare_minors('3.99')
        before = self.queue_item()
        self.assert_stopped(*self.cli('queue', 'start-next'), before, 'python-minor', 'uv python install 3.99')

    def test_start_next_with_the_running_minor_declared_starts(self):
        self.declare_minors(RUNNING_MINOR)
        self.queue_item()
        self.assert_started(*self.cli('queue', 'start-next'))


class NodeTests(CliBase):
    """`node` is hidden by a PATH that holds only git; the controls add node back."""

    def setUp(self):
        super().setUp()
        self.bin = Path(self.temp.name) / 'bin'
        self.bin.mkdir()
        os.symlink(shutil.which('git'), self.bin / 'git')
        self.no_node = identityless_env(self.home, str(self.bin))

    def with_node(self):
        node = shutil.which('node')
        if node is None:
            self.skipTest('node is not on PATH')
        os.symlink(node, self.bin / 'node')

    def test_create_refuses_a_typescript_scope_without_node(self):
        for scope in ('ui', 'ui/web', './ui/web', 'ui/web/tests', 'ui/web/lib'):
            with self.subTest(scope=scope):
                code, payload = self.create(scope, env=self.no_node)
                self.assert_refused(code, payload, 'node-missing', 'install Node.js')
                self.no_cycle()

    def test_create_outside_a_typescript_scope_needs_no_node(self):
        code, payload = self.create('src', env=self.no_node)
        self.assertEqual(code, 0, payload)

    def test_create_with_node_on_path_starts(self):
        self.with_node()
        code, payload = self.create('./ui', env=self.no_node)
        self.assertEqual(code, 0, payload)

    def test_start_next_stops_on_a_typescript_scope_without_node(self):
        before = self.queue_item('ui')
        self.assert_stopped(*self.cli('queue', 'start-next', env=self.no_node), before, 'node-missing', 'install Node.js')

    def test_start_next_with_node_on_path_starts(self):
        self.with_node()
        self.queue_item('ui')
        self.assert_started(*self.cli('queue', 'start-next', env=self.no_node))


class RunnerTests(unittest.TestCase):
    """The probes through the injectable runner: what each observation becomes."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.calls = []

    def runner(self, answers):
        def run(argv, cwd):
            self.calls.append(argv)
            answer = answers.get(argv[0], (0, 'ok'))
            if isinstance(answer, BaseException):
                raise answer
            return answer(argv) if callable(answer) else answer
        return run

    def test_a_missing_git_binary_names_an_install_fix_not_git_config(self):
        result = cycle_prereqs.check(self.repo, ['x'], self.runner({'git': FileNotFoundError()}))
        self.assertEqual([m['code'] for m in result['missing']], ['git-missing'])
        self.assertIn('install git', result['missing'][0]['fix'])
        self.assertNotIn('git config', result['missing'][0]['fix'])

    def test_a_timed_out_probe_is_missing(self):
        result = cycle_prereqs.check(self.repo, ['x'], self.runner({'git': (None, 'timed out after 10 seconds')}))
        self.assertEqual([m['code'] for m in result['missing']], ['git-author-identity', 'git-committer-identity'])
        self.assertIn('timed out', result['missing'][0]['observed'])

    def test_undeclared_minors_run_no_uv_probe(self):
        result = cycle_prereqs.check(self.repo, ['x'], self.runner({}))
        self.assertEqual(result['missing'], [])
        self.assertNotIn('uv', [argv[0] for argv in self.calls])

    def test_a_missing_uv_is_reported_once_with_its_own_fix(self):
        (self.repo / 'pyproject.toml').write_text('[tool.crux]\npython-versions = ["3.13", "3.14"]\n')
        result = cycle_prereqs.check(self.repo, ['x'], self.runner({'uv': FileNotFoundError()}))
        self.assertEqual([m['code'] for m in result['missing']], ['uv-missing'])
        self.assertIn('install uv', result['missing'][0]['fix'])

    def test_each_missing_minor_names_its_install_command(self):
        (self.repo / 'pyproject.toml').write_text('[tool.crux]\npython-versions = ["3.13", "3.14"]\n')
        answer = lambda argv: (2, 'error: No interpreter found') if argv[-1] == '3.14' else (0, '/x/python3.13')
        result = cycle_prereqs.check(self.repo, ['x'], self.runner({'uv': answer}))
        self.assertEqual([m['fix'] for m in result['missing']], ['install Python 3.14: uv python install 3.14'])

    def test_a_non_git_root_notes_why_node_was_not_checked_and_refuses_nothing(self):
        (self.repo / 'ui/web/tests').mkdir(parents=True)
        (self.repo / 'ui/web/tests/test-tiers.json').write_text(TS_MANIFEST)
        result = cycle_prereqs.check(self.repo, ['ui'], self.runner({'node': FileNotFoundError()}))
        self.assertEqual(result['missing'], [])
        self.assertTrue(any('node not checked' in note for note in result['notes']), result)

    def test_require_raises_with_the_list_and_the_code(self):
        with self.assertRaises(cycle_prereqs.EnvironmentPrerequisite) as caught:
            cycle_prereqs.require(self.repo, ['x'], self.runner({'git': FileNotFoundError()}))
        payload = caught.exception.payload()
        self.assertEqual(payload['code'], 'environment-prerequisite')
        self.assertEqual(payload['missing'][0]['code'], 'git-missing')


if __name__ == '__main__':
    unittest.main()
