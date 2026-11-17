"""A documentation tree that git ignores: the shared predicate, the council evidence writer, the cycle
and queue writers, log-work, ADR acceptance and adopt, and criterion observations.

The fixture follows the reproduction's: a temporary git repository whose docs tree (bionic/) git
ignores, with a Standard council initialized before the first .bionic.yml commit. The order matters:
`council_policy.initialize` refuses once a committed .bionic.yml exists at HEAD, because it never
changes an existing project policy (see UserOrderTests). The gateway is stubbed the way
test_cycle_council.py stubs it, so no request leaves the machine.

Every ignored-tree case pairs with a tracked-tree case that proves today's commits and refusals stay.
"""
import json
import os
import shlex
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cycle_council as council
import council_policy as policy
from cycle_workflow import CycleError, create, digest, mutate, tree
from ignored_paths import ignored
try:
    from crux.core.data_classes import CouncilVote, CouncilDeliberation
    from test_cycle_council import checkpointed_result
    HAVE_GATEWAY = True
except ImportError:
    HAVE_GATEWAY = False

IDR = {'alternatives': ['leave it'], 'approach': 'set answer to 2', 'assumptions': ['one file'],
       'constraints': ['no API change'], 'intended_evidence': ['unit check']}


def git(root, *args, check=True, env=None):
    return subprocess.run(['git', '-C', str(root), *args], check=check, capture_output=True, text=True, env=env)


def build_repo(root, *, hide='gitignore', initialize=True):
    """The reproduction fixture. `hide` is gitignore, exclude, global (caller sets GIT_CONFIG_GLOBAL) or None (tracked)."""
    from council_policy import initialize as init_council
    git(root, 'init', '-q')
    git(root, 'config', 'user.email', 't@example.invalid')
    git(root, 'config', 'user.name', 'Test')
    (root / 'src').mkdir()
    (root / 'src/a.py').write_text('answer = 1\n')
    (root / '.gitignore').write_text('bionic/\n' if hide == 'gitignore' else '')
    if hide == 'exclude':
        (root / '.git/info').mkdir(exist_ok=True)
        (root / '.git/info/exclude').write_text('bionic/\n')
    git(root, 'add', '.gitignore', 'src')
    git(root, 'commit', '-qm', 'base')
    docs = root / 'bionic'
    docs.mkdir()
    (root / '.bionic.yml').write_text('config_version: "1"\ndocs_dir: bionic\nartifact_prefix: ""\nadr:\n  acceptance: council-only\n')
    (docs / 'manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs, journal]\nadr:\n  next_number: 2\npromptbook:\n  next_number: 1\n')
    (docs / 'objectives.md').write_text('---\ntype: objectives\n---\n# Objectives\n\n## Mission\n\nShip useful changes.\n')
    if initialize:
        init_council(root, 'standard', selection='fixture: explicit Standard selection')
    git(root, 'add', '.bionic.yml')
    if hide is None:
        git(root, 'add', 'bionic')
    git(root, 'commit', '-qm', 'crux config')


def stubbed(call):
    """Run `call` with the three-seat gateway stubbed: every seat approves; nothing leaves the machine."""
    votes = [CouncilVote(model=p + '/model', provider=p, decision='APPROVE', reasoning='supported', confidence=.9)
             for p in ('openai', 'anthropic', 'google')]
    result = CouncilDeliberation(votes=votes, consensus='UNANIMOUS_APPROVE', consensus_confidence=.9,
                                 key_agreements=[], key_disagreements=[], final_recommendation={})
    limits = {'one': 128000, 'two': 128000, 'three': 65536}
    with patch('crux_env.get', return_value='test-gateway-credential'), \
            patch('crux.council.async_council.validate_gate_assignment',
                  return_value={'openai_top': 'one', 'anthropic_top': 'two', 'google_top': 'three'}), \
            patch('crux.core.llm_caller.get_model_config',
                  side_effect=lambda model: SimpleNamespace(max_output_tokens=limits[model])), \
            patch('crux.council.async_council.AsyncCouncil') as seats:
        seats.return_value.deliberate = AsyncMock(
            side_effect=lambda *args: checkpointed_result(seats.call_args.args[0], result))
        output = call()
        return output, seats


RUNNER = '''
import importlib.util, os, sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
sys.path.insert(0, {scripts!r}); sys.path.insert(0, {tests!r})
from test_cycle_council import checkpointed_result
from crux.core.data_classes import CouncilVote, CouncilDeliberation
spec = importlib.util.spec_from_file_location('council_cli', {cli!r})
cli = importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)
votes = [CouncilVote(model=p + '/model', provider=p, decision='APPROVE', reasoning='fixture', confidence=.9)
         for p in ('openai', 'anthropic', 'google')]
result = CouncilDeliberation(votes=votes, consensus='UNANIMOUS_APPROVE', consensus_confidence=.9,
                             key_agreements=[], key_disagreements=[], final_recommendation={{}})
with patch('crux_env.get', return_value='test-gateway-credential'), \\
        patch('crux.council.async_council.validate_gate_assignment',
              return_value={{'openai_top': 'one', 'anthropic_top': 'two', 'google_top': 'three'}}), \\
        patch('crux.core.llm_caller.get_model_config', return_value=SimpleNamespace(max_output_tokens=65536)), \\
        patch('crux.council.async_council.AsyncCouncil') as seats:
    seats.return_value.deliberate = AsyncMock(side_effect=lambda *a: checkpointed_result(seats.call_args.args[0], result))
    status = cli.main()
sys.stdout.flush(); sys.stderr.flush()
os._exit(status)
'''


class FixtureBase(unittest.TestCase):
    hide = 'gitignore'
    initialize = True

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / 'repo'
        self.root.mkdir()
        self.prepare_environment()
        build_repo(self.root, hide=self.hide, initialize=self.initialize)
        self.cfg = tree(self.root)
        self.docs = self.cfg.docs_root
        self.cid = create(self.root, 'dev', 'Answer', 'Return 2', ['src', 'bionic'], ['answer is 2'],
                          'dev-lead', 'dev-lead')['id']
        doc = mutate(self.root, self.cid, 'decision', kind='idr', name='answer', contents=dict(IDR))
        self.subject = doc['decisions'][-1]['path']

    def prepare_environment(self):
        """Hook for a variant that changes the ambient git environment before the fixture is built."""

    def commits(self):
        return int(git(self.root, 'rev-list', '--count', 'HEAD').stdout)

    def tracked_docs(self):
        return git(self.root, 'ls-files', '--', 'bionic').stdout.split()

    def convene(self, **options):
        return stubbed(lambda: council.convene(self.root, 'idr', self.subject, 'Review the decision.',
                                               cycle_id=self.cid, **options))[0]

    def record(self, relative):
        return json.loads((self.docs / relative).read_text())

    def agreement(self):
        return {'agrees': True, 'subject_sha256': digest((self.docs / self.subject).read_bytes()),
                'nits': [], 'rationale': 'fixture agreement', 'dissent': []}

    def settle(self, output):
        """The architect disposition and approve-decision, as the cycle runs them."""
        settled = policy.disposition(self.root, output['record'], self.agreement())
        self.assertEqual(settled['outcome'], 'approved')
        council.validate_approval(self.root, output['record'], purpose='idr', subject=self.subject)
        doc = mutate(self.root, self.cid, 'approve-decision', subject=self.subject, approval=output['record'])
        self.assertTrue(any(d['path'] == self.subject and d.get('approval') for d in doc['decisions']))
        return settled

    def detached(self):
        """The default convening route: launch a detached runner, then --await its terminal outcome."""
        script = Path(self.temp.name) / 'runner.py'
        script.write_text(RUNNER.format(scripts=str(SCRIPTS), tests=str(SCRIPTS / 'tests'),
                                        cli=str(SCRIPTS / 'cycle-council.py')))
        question = Path(self.temp.name) / 'question.txt'
        question.write_text('Review the decision.')
        arguments = ['--repo-root', str(self.root), '--purpose', 'idr', '--subject', self.subject,
                     '--question', str(question), '--cycle', self.cid]
        launched = council.launch_detached(self.root, arguments, purpose='idr', subject=self.subject,
                                           cycle_id=self.cid, runner=[sys.executable, str(script)])
        self.assertIn(launched['outcome'], {'running', 'awaiting-architect'}, launched)
        return launched, council.await_attempt(self.root, launched['attempt'], 60)


@unittest.skipUnless(HAVE_GATEWAY, 'gateway dependencies unavailable')
class IgnoredTreeCouncilTests(FixtureBase):
    """An IDR gateway council in a tree .gitignore hides reaches its seats and records a result."""

    def test_foreground_council_disposition_and_approve_decision(self):
        before = self.commits()
        output, seats = stubbed(lambda: council.convene(self.root, 'idr', self.subject, 'Review the decision.',
                                                        cycle_id=self.cid))
        seats.return_value.deliberate.assert_called_once()
        self.assertEqual(output['outcome'], 'awaiting-architect')
        self.assertEqual(output['evidence_uncommitted'], 'tree-ignored')
        self.assertEqual(self.record(output['record'])['evidence_uncommitted'], 'tree-ignored')
        settled = self.settle(output)
        self.assertEqual(settled['evidence_uncommitted'], 'tree-ignored')
        self.assertEqual(self.commits(), before)
        self.assertEqual(self.tracked_docs(), [])

    def test_detached_convene_then_await_returns_the_terminal_outcome(self):
        launched, awaited = self.detached()
        self.assertEqual(awaited['outcome'], 'awaiting-architect', awaited)
        self.assertEqual(awaited['evidence_uncommitted'], 'tree-ignored')
        self.settle({'record': awaited['record']})
        self.assertEqual(self.tracked_docs(), [])

    def test_stranded_running_claim_recovers(self):
        _, attempt_path, attempt, _ = council.begin_mode(self.root, 'idr', self.subject, 'Review the decision.',
                                                         cycle_id=self.cid)
        relative = attempt_path.relative_to(self.docs).as_posix()
        with self.assertRaisesRegex(CycleError, 'unresolved council attempt'):
            self.convene(progress='retry after the stranded claim')
        recovered = council.recover(self.root, relative)
        self.assertEqual(recovered['status'], 'interrupted')
        output = self.convene(progress='retry after recovery')
        self.assertEqual(output['outcome'], 'awaiting-architect')
        self.assertEqual(self.tracked_docs(), [])

    def test_partly_ignored_evidence_set_marks_the_record(self):
        # Only the result files are hidden; the attempt file stays committable.
        (self.root / '.gitignore').write_text('council-*.json\n')
        git(self.root, 'add', '.gitignore', 'bionic')
        git(self.root, 'commit', '-qm', 'track the docs tree except council results')
        output = self.convene()
        self.assertEqual(self.record(output['record'])['evidence_uncommitted'], 'tree-ignored')
        self.assertIn(output['attempt'], [p[len('bionic/'):] for p in self.tracked_docs()])
        self.assertNotIn(output['record'], [p[len('bionic/'):] for p in self.tracked_docs()])


@unittest.skipUnless(HAVE_GATEWAY, 'gateway dependencies unavailable')
class ExcludeFileCouncilTests(FixtureBase):
    """.git/info/exclude hides the tree: the same council completes and commits nothing under it."""
    hide = 'exclude'

    def test_council_completes_through_approve_decision(self):
        output = self.convene()
        self.assertEqual(output['outcome'], 'awaiting-architect')
        self.assertEqual(output['evidence_uncommitted'], 'tree-ignored')
        self.settle(output)
        self.assertEqual(self.tracked_docs(), [])


@unittest.skipUnless(HAVE_GATEWAY, 'gateway dependencies unavailable')
class GlobalExcludesCouncilTests(FixtureBase):
    """Only a global core.excludesFile hides the tree. The council's own git reads no global
    configuration and would stage the files; the predicate reads it, so nothing is committed."""
    hide = 'global'

    def prepare_environment(self):
        home = Path(self.temp.name)
        (home / 'global-ignore').write_text('bionic/\n')
        (home / 'gitconfig').write_text(f'[core]\n\texcludesFile = {home / "global-ignore"}\n')
        patcher = patch.dict(os.environ, {'GIT_CONFIG_GLOBAL': str(home / 'gitconfig')})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_detached_convene_then_await_commits_nothing_under_the_tree(self):
        before = self.commits()
        launched, awaited = self.detached()
        self.assertEqual(awaited['outcome'], 'awaiting-architect', awaited)
        self.assertEqual(awaited['evidence_uncommitted'], 'tree-ignored')
        self.settle({'record': awaited['record']})
        self.assertEqual(self.commits(), before)
        self.assertEqual(self.tracked_docs(), [])


class LegacyBase(FixtureBase):
    """No council mode configured or enrolled: the legacy writer runs."""
    initialize = False

    def legacy(self):
        claims = []
        output = stubbed(lambda: council.convene(self.root, 'idr', self.subject, 'Review the decision.',
                                                 cycle_id=self.cid, on_claim=lambda *a: claims.append(a)))[0]
        self.assertEqual(len(claims), 1)
        record = self.record(output['record'])
        self.assertEqual(record['format'], 'crux.cycle-council')
        self.assertEqual(output['outcome'], 'approved')
        council.validate_approval(self.root, output['record'], purpose='idr', subject=self.subject)
        return output, record



@unittest.skipUnless(HAVE_GATEWAY, 'gateway dependencies unavailable')
class LegacyPathCouncilTests(LegacyBase):
    """The legacy writer in an ignored tree records the same field."""

    def test_ignored_legacy_record_states_uncommitted_evidence(self):
        before = self.commits()
        output, record = self.legacy()
        self.assertEqual(record['evidence_uncommitted'], 'tree-ignored')
        self.assertEqual(output['evidence_uncommitted'], 'tree-ignored')
        self.assertEqual(self.commits(), before)


@unittest.skipUnless(HAVE_GATEWAY, 'gateway dependencies unavailable')
class TrackedLegacyPathCouncilTests(LegacyBase):
    hide = None

    def test_tracked_legacy_record_commits_and_carries_no_field(self):
        before = self.commits()
        output, record = self.legacy()
        self.assertNotIn('evidence_uncommitted', record)
        self.assertNotIn('evidence_uncommitted', output)
        self.assertEqual(self.commits(), before + 2)


@unittest.skipUnless(HAVE_GATEWAY, 'gateway dependencies unavailable')
class TrackedTreeCouncilTests(FixtureBase):
    """The paired controls: a tracked tree keeps every commit, refusal and result key."""
    hide = None

    def test_council_commits_three_evidence_commits_without_the_field(self):
        before = self.commits()
        output = self.convene()
        self.assertEqual(output['outcome'], 'awaiting-architect')
        self.assertNotIn('evidence_uncommitted', output)
        self.assertNotIn('evidence_uncommitted', self.record(output['record']))
        settled = self.settle(output)
        self.assertNotIn('evidence_uncommitted', settled)
        self.assertEqual(self.commits(), before + 3)
        tracked = self.tracked_docs()
        self.assertIn('bionic/' + output['record'], tracked)
        self.assertIn('bionic/' + output['attempt'], tracked)

    def test_detached_await_returns_the_outcome_without_the_field(self):
        _, awaited = self.detached()
        self.assertEqual(awaited['outcome'], 'awaiting-architect', awaited)
        self.assertNotIn('evidence_uncommitted', awaited)

    def test_held_index_lock_still_refuses_staging(self):
        lock = self.root / '.git/index.lock'
        lock.write_text('')
        self.addCleanup(lambda: lock.unlink(missing_ok=True))
        with self.assertRaisesRegex(CycleError, 'cannot stage council execution trace'):
            self.convene()

    def test_failing_pre_commit_hook_still_refuses_the_commit(self):
        hook = self.root / '.git/hooks/pre-commit'
        hook.parent.mkdir(exist_ok=True)
        hook.write_text('#!/bin/sh\nexit 1\n')
        hook.chmod(0o755)
        with self.assertRaisesRegex(CycleError, 'cannot commit council execution trace; no reviewer dispatched'):
            self.convene()

    def test_uncommitted_terminal_evidence_still_needs_recovery(self):
        original = council.commit_evidence

        def skip_result(repo, paths, message):
            if message == 'Record exact council result':
                return []
            return original(repo, paths, message)
        with patch.object(council, 'commit_evidence', skip_result):
            output = self.convene()
        awaited = council.await_attempt(self.root, output['attempt'], 1)
        self.assertEqual(awaited['outcome'], 'recovery-required')
        # Positive control: once the original bytes are committed, the same await returns the outcome.
        council.recover(self.root, output['attempt'])
        self.assertEqual(council.await_attempt(self.root, output['attempt'], 1)['outcome'], 'awaiting-architect')


@unittest.skipUnless(HAVE_GATEWAY, 'gateway dependencies unavailable')
class UserOrderTests(unittest.TestCase):
    """The user's order: commit .bionic.yml, then initialize the council. Finding: initialization
    refuses in both trees, because a committed .bionic.yml counts as an existing project policy.
    The refusal is not caused by the ignored tree."""

    def attempt(self, hide):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name).resolve()
        build_repo(root, hide=hide, initialize=False)
        with self.assertRaisesRegex(CycleError, 'initialization cannot change an existing project council policy'):
            policy.initialize(root, 'standard', selection='fixture: user order')

    def test_ignored_tree_refuses_like_the_tracked_tree(self):
        self.attempt('gitignore')
        self.attempt(None)


class PredicateTests(unittest.TestCase):
    """ignored_paths.ignored, the one predicate."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / 'repo'
        self.root.mkdir()
        git(self.root, 'init', '-q')
        git(self.root, 'config', 'user.email', 't@example.invalid')
        git(self.root, 'config', 'user.name', 'Test')
        (self.root / 'docs').mkdir()
        (self.root / 'docs/tracked.md').write_text('tracked\n')
        (self.root / 'docs/loose.md').write_text('loose\n')
        git(self.root, 'add', 'docs/tracked.md')
        git(self.root, 'commit', '-qm', 'base')
        (self.root / '.gitignore').write_text('docs/\n')

    def test_tracked_file_inside_an_ignored_directory_is_not_reported(self):
        self.assertEqual(ignored(self.root, ['docs/tracked.md', 'docs/loose.md']), frozenset({'docs/loose.md'}))

    def test_tracked_root_is_not_reported_and_files_are(self):
        # A directory that holds a tracked file answers "not ignored"; callers ask about files.
        self.assertEqual(ignored(self.root, ['docs']), frozenset())
        self.assertEqual(ignored(self.root, ['docs/new.json']), frozenset({'docs/new.json'}))

    def test_info_exclude_counts(self):
        (self.root / '.gitignore').unlink()
        self.assertEqual(ignored(self.root, ['docs/loose.md']), frozenset())
        (self.root / '.git/info').mkdir(exist_ok=True)
        (self.root / '.git/info/exclude').write_text('docs/\n')
        self.assertEqual(ignored(self.root, ['docs/loose.md']), frozenset({'docs/loose.md'}))

    def test_global_excludes_file_counts_though_the_council_git_reads_none(self):
        (self.root / '.gitignore').unlink()
        home = Path(self.temp.name)
        (home / 'global-ignore').write_text('docs/\n')
        (home / 'gitconfig').write_text(f'[core]\n\texcludesFile = {home / "global-ignore"}\n')
        with patch.dict(os.environ, {'GIT_CONFIG_GLOBAL': str(home / 'gitconfig')}):
            self.assertEqual(ignored(self.root, ['docs/loose.md']), frozenset({'docs/loose.md'}))
            from council_records import _git_env
            self.assertEqual(_git_env()['GIT_CONFIG_GLOBAL'], os.devnull)
            self.assertEqual(council.ignored_evidence(self.root, [self.root / 'docs/loose.md']),
                             frozenset({'docs/loose.md'}))
        # Positive control: without the global file nothing hides the path.
        with patch.dict(os.environ, {'GIT_CONFIG_GLOBAL': os.devnull}):
            self.assertEqual(ignored(self.root, ['docs/loose.md']), frozenset())

    def test_literal_pathspecs_in_the_caller_environment_still_answer(self):
        with patch.dict(os.environ, {'GIT_LITERAL_PATHSPECS': '1'}):
            self.assertEqual(ignored(self.root, ['docs/loose.md']), frozenset({'docs/loose.md'}))
        probe = subprocess.run(['git', '-C', str(self.root), 'check-ignore', 'docs/loose.md'],
                               capture_output=True, env={**os.environ, 'GIT_LITERAL_PATHSPECS': '1'})
        self.assertEqual(probe.returncode, 128)

    def test_drop_env_removes_names_from_the_git_child(self):
        with patch.dict(os.environ, {'GIT_DIR': str(Path(self.temp.name) / 'nowhere')}):
            self.assertEqual(ignored(self.root, ['docs/loose.md']), frozenset())
            self.assertEqual(ignored(self.root, ['docs/loose.md'], drop_env=('GIT_DIR',)), frozenset({'docs/loose.md'}))

    def test_outside_a_repository_answers_nothing_and_the_writer_refuses(self):
        outside = Path(self.temp.name).resolve() / 'plain'
        outside.mkdir()
        (outside / 'note.json').write_text('{}')
        with patch.dict(os.environ, {'GIT_CEILING_DIRECTORIES': str(Path(self.temp.name))}):
            self.assertEqual(ignored(outside, ['note.json']), frozenset())
            with self.assertRaisesRegex(CycleError, 'cannot stage council execution trace'):
                council.commit_evidence(outside, [outside / 'note.json'], 'fixture')
        self.assertEqual(ignored(self.root, []), frozenset())

    def test_commit_evidence_drops_ignored_paths_and_commits_the_rest(self):
        (self.root / 'kept.json').write_text('{}')
        before = git(self.root, 'rev-list', '--count', 'HEAD').stdout
        skipped = council.commit_evidence(self.root, [self.root / 'docs/loose.md', self.root / 'kept.json'], 'fixture')
        self.assertEqual(skipped, ['docs/loose.md'])
        self.assertEqual(int(git(self.root, 'rev-list', '--count', 'HEAD').stdout), int(before) + 1)
        self.assertEqual(git(self.root, 'show', '--name-only', '--format=', 'HEAD').stdout.split(), ['kept.json'])
        # Every path ignored: no git command runs and nothing is committed.
        self.assertEqual(council.commit_evidence(self.root, [self.root / 'docs/loose.md'], 'fixture'), ['docs/loose.md'])
        self.assertEqual(int(git(self.root, 'rev-list', '--count', 'HEAD').stdout), int(before) + 1)


def assert_skipped(case, result, *paths):
    """The writer's skip report: nothing committed, no deferral, the cause and the dropped paths named."""
    case.assertEqual(result.get('commit_skipped'), 'tree-ignored', result)
    case.assertIsNone(result['deferred'], result)
    case.assertIsNone(result['commit'], result)
    case.assertFalse(result['changed'], result)
    for path in paths:
        case.assertIn(path, result['skipped_paths'], result)


class CycleOpsMixin:
    """Run `cycle.py op` in process, as test_cycle_slice does."""

    def isolate(self):
        from _classifier_isolation import isolate_classifier
        isolate_classifier(self)
        store = patch.dict(os.environ, {'CRUX_TEST_EVIDENCE_STORE': str(Path(self.temp.name).resolve() / 'evidence')})
        store.start()
        self.addCleanup(store.stop)

    def op(self, request, cid=None):
        import contextlib
        import io
        import cycle
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cycle.main(['--repo-root', str(self.root), 'op', cid or self.cid, '--json', json.dumps(request)])
        return code, json.loads(out.getvalue())

    def ok(self, request, cid=None):
        code, response = self.op(request, cid)
        self.assertEqual(code, 0, response)
        self.assertTrue(response['ok'], response)
        return response

    def revision(self):
        from cycle_workflow import load
        return load(self.root, self.cid)['revision']

    def advance(self, op_id):
        return self.ok({'op': 'advance', 'op_id': op_id, 'expect_revision': self.revision()})


@unittest.skipUnless(HAVE_GATEWAY, 'gateway dependencies unavailable')
class IgnoredTreeDevCycleTests(CycleOpsMixin, FixtureBase):
    """A full dev cycle in the ignored tree: every record commit is skipped and says so."""

    def setUp(self):
        super().setUp()
        self.isolate()

    def record_dir(self):
        return f'bionic/cycles/{self.cid}'

    def test_full_dev_cycle_completes_and_reports_each_skipped_commit(self):
        from cycle_workflow import load
        import cycle_hosts
        before = self.commits()
        # Plan: the IDR council approves the exact revision, then the plan names it.
        self.settle(self.convene())
        doc = load(self.root, self.cid)
        plan = dict(doc['plan'], verification=['the unit check passes'], tasks=[
            {'id': 'plan', 'phase': 'plan', 'description': 'plan the change', 'depends_on': [], 'status': 'pending',
             'expected_evidence': ['plan']},
            {'id': 'build-it', 'phase': 'build', 'description': 'set the answer', 'depends_on': ['plan'],
             'status': 'pending', 'expected_evidence': ['commit']},
            *({'id': phase, 'phase': phase, 'description': phase, 'depends_on': ['build-it'], 'status': 'pending',
               'expected_evidence': [phase]} for phase in ('verify', 'review', 'reflect'))])
        mutate(self.root, self.cid, 'plan', plan=plan, reason='plan with the approved IDR')
        mutate(self.root, self.cid, 'task', task_id='plan', state='done')
        record = self.record_dir()
        assert_skipped(self, self.advance('adv-plan')['record_commit'], record)
        # Build: dispatch, execution-check, a source commit and delivery.
        prepared = self.ok({'op': 'prepare-dispatch', 'op_id': 'prep-0001', 'task_id': 'build-it', 'role': 'dev-lead',
                            'host': 'claude-code', 'assignment_text': 'Set the answer to 2.'})
        assert_skipped(self, prepared['record_commit'], record)
        self.addCleanup(lambda: Path(prepared['result_path']).unlink(missing_ok=True))
        check = {'op': 'execution-check', 'assignment': 'build-it', 'attempt': 1, 'checkout': str(self.root)}
        assert_skipped(self, self.ok({**check, 'op_id': 'check-start'})['record_commit'], record)
        (self.root / 'src/a.py').write_text('answer = 2\n')
        git(self.root, 'add', 'src/a.py')
        assert_skipped(self, self.ok({**check, 'op_id': 'check-stage', 'edited_paths': ['src/a.py']})['record_commit'], record)
        git(self.root, 'commit', '-qm', 'set the answer\n\nCycle-Task: build-it')
        sha = git(self.root, 'rev-parse', 'HEAD').stdout.strip()
        marker = cycle_hosts.marker('build-it', 1, prepared.get('delivery_token'))
        Path(prepared['result_path']).write_text(f'Assignment: build-it\nAttempt: 1\n\nOutcome: DONE.\n{marker}\n')
        delivered = self.ok({'op': 'deliver', 'op_id': 'deliver-01', 'assignment': 'build-it', 'attempt': 1,
                             'outcome': 'done', 'commits': [sha]})
        assert_skipped(self, delivered['record_commit'], record)
        assert_skipped(self, self.advance('adv-build')['record_commit'], record)
        # Verify and Review.
        mutate(self.root, self.cid, 'checks', checks=['unit'])
        mutate(self.root, self.cid, 'coverage', coverage={'affected': ['the answer'], 'checks': [
            {'check_id': 'unit', 'rationale': 'reads src/a.py'}], 'not_selected': 'no other behavior'})
        command = [sys.executable, '-c',
                   "from pathlib import Path; assert Path('src/a.py').read_text() == 'answer = 2\\n'"]
        observed = subprocess.run(command, cwd=self.root, capture_output=True, text=True)
        self.assertEqual(observed.returncode, 0, observed.stderr)
        checked = mutate(self.root, self.cid, 'local-check', check_id='unit', executed_command=shlex.join(command),
                         tested_revision=sha, result='passed', summary='The answer source assertion passes',
                         reason='Checks the changed source behavior before independent review')
        observation = checked['local_checks'][-1]['id']
        mutate(self.root, self.cid, 'task', task_id='verify', state='done')
        assert_skipped(self, self.advance('adv-verify')['record_commit'], record)
        mutate(self.root, self.cid, 'review', report={'reviewer': 'independent', 'scope': ['src', 'bionic'], 'evidence': [observation],
                                                      'blocking': [], 'advisory': [], 'cosmetic': [], 'verdict': 'approve',
                                                      'rationale': 'reviewed the change'})
        mutate(self.root, self.cid, 'task', task_id='review', state='done')
        assert_skipped(self, self.advance('adv-review')['record_commit'], record)
        # Reflect and finish.
        mutate(self.root, self.cid, 'reflect', reflection={'outcome': 'answer is 2', 'lessons': ['l'], 'remaining': ['none'],
                                                           'follow_ups': []})
        mutate(self.root, self.cid, 'task', task_id='reflect', state='done')
        finished = self.ok({'op': 'finish', 'op_id': 'finish-001', 'expect_revision': self.revision(),
                            'lessons': ['l'], 'remaining': ['none']})
        assert_skipped(self, finished['record_commit'], record)
        self.assertEqual(load(self.root, self.cid)['status'], 'completed')
        # Only the source commit landed; nothing under the tree is tracked.
        self.assertEqual(self.commits(), before + 1)
        self.assertEqual(self.tracked_docs(), [])


class TrackedTreeCycleWriterTests(FixtureBase):
    """The paired controls for the cycle writer: a tracked tree commits, defers and refuses as before."""
    hide = None
    KEYS = {'changed', 'commit', 'paths', 'message', 'deferred'}

    def test_tracked_record_commit_keeps_its_exact_result_keys(self):
        from cycle_commit import commit_record
        before = self.commits()
        result = commit_record(self.root, self.cid, 'fixture')
        self.assertEqual(set(result), self.KEYS)
        self.assertTrue(result['changed'])
        self.assertIsNone(result['deferred'])
        self.assertEqual(self.commits(), before + 1)
        self.assertIn(f'bionic/cycles/{self.cid}/cycle.json', self.tracked_docs())

    def test_failing_hook_still_defers_commit_failed_without_a_skip(self):
        from cycle_commit import commit_record
        # The record commit passes --no-verify; prepare-commit-msg still runs and fails the commit.
        hook = self.root / '.git/hooks/prepare-commit-msg'
        hook.parent.mkdir(exist_ok=True)
        hook.write_text('#!/bin/sh\nexit 1\n')
        hook.chmod(0o755)
        before = self.commits()
        result = commit_record(self.root, self.cid, 'fixture')
        self.assertEqual(result['deferred'], 'commit-failed', result)
        self.assertNotIn('commit_skipped', result)
        self.assertNotIn('skipped_paths', result)
        self.assertEqual(self.commits(), before)


class IgnoredTreeCycleWriterTests(FixtureBase):
    """The ignored-tree counterpart: the same writer commits nothing and reports the skip."""

    def test_record_commit_reports_the_skip(self):
        from cycle_commit import commit_record
        before = self.commits()
        result = commit_record(self.root, self.cid, 'fixture')
        assert_skipped(self, result, f'bionic/cycles/{self.cid}')
        self.assertEqual(result['paths'], [])
        self.assertEqual(self.commits(), before)

    def test_mixed_paths_commit_the_tracked_rest(self):
        from cycle_commit import commit_paths
        (self.root / 'src/b.py').write_text('b = 1\n')
        result = commit_paths(self.cfg, [f'bionic/cycles/{self.cid}', 'src/b.py'], 'fixture')
        self.assertTrue(result['changed'], result)
        self.assertEqual((result['commit_skipped'], result['skipped_paths'], result['paths']),
                         ('tree-ignored', [f'bionic/cycles/{self.cid}'], ['src/b.py']))
        self.assertEqual(git(self.root, 'show', '--name-only', '--format=', 'HEAD').stdout.split(), ['src/b.py'])


class IgnoredTreeQueueTests(CycleOpsMixin, FixtureBase):
    """queue add, authorize and start-next in the ignored tree: each queue and record commit is skipped."""

    def setUp(self):
        super().setUp()
        self.isolate()

    def test_queue_add_authorize_and_start_next(self):
        import cycle_queue
        before = self.commits()
        queue = 'bionic/queue/cycles.yaml'
        added = cycle_queue.add(self.root, 'Answer three', 'Return 3', 'quick-fix', ['src'], ['answer is 3'])
        assert_skipped(self, added['queue_commit'], queue)
        authorized = cycle_queue.authorize(self.root, 'next', 'run the next item', '2026-11-14')
        assert_skipped(self, authorized['queue_commit'], queue)
        started = cycle_queue.start_next(self.root)
        self.assertEqual(started['outcome'], 'started', started)
        assert_skipped(self, started['record_commit'], f"bionic/cycles/{started['cycle']}", queue)
        self.assertEqual(self.commits(), before)
        self.assertEqual(self.tracked_docs(), [])


class IgnoredTreeLogWorkTests(unittest.TestCase):
    """write-journal.py and operation-log.py append complete in the ignored tree. Neither runs git;
    their commit_paths are empty, and the predicate reports every written path, which the section 6
    commit step drops."""

    def setUp(self):
        import operation_log
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / 'repo'
        self.root.mkdir()
        build_repo(self.root, initialize=False)
        docs = self.root / 'bionic'
        (docs / 'journal').mkdir()
        (docs / 'log').mkdir()
        (docs / 'log/.split-complete.json').write_bytes(operation_log.completion_bytes(None, {}))
        (docs / 'AGENTS.md').write_bytes((SCRIPTS.parent / 'templates/AGENTS.md.tmpl').read_bytes())
        self.body = Path(self.temp.name) / 'body.txt'
        self.body.write_text('Recorded the work.\n')
        self.env = {**os.environ, operation_log.TEST_ENV: '1', 'UV_NO_CONFIG': '1'}

    def run_script(self, *argv):
        done = subprocess.run([sys.executable, *argv], capture_output=True, text=True, env=self.env)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        return json.loads(done.stdout)

    def test_journal_and_log_append_write_and_leave_nothing_to_commit(self):
        before = git(self.root, 'rev-list', '--count', 'HEAD').stdout
        journal = self.run_script(str(SCRIPTS / 'write-journal.py'), '--repo-root', str(self.root), '--mode', 'journal',
                                  '--at', '2026-09-27T11:42:35-06:00', '--category', 'learning', '--subject', 'Logged work',
                                  '--body-file', str(self.body), '--today', '2026-09-27')
        self.assertEqual(journal['status'], 'complete', journal)
        self.assertEqual(journal['commit_paths'], [])
        appended = self.run_script(str(SCRIPTS / 'operation-log.py'), 'append', '--repo-root', str(self.root), '--op', 'query',
                                   '--subject', 'Asked a question', '--date', '2026-09-27', '--body-file', str(self.body),
                                   '--today', '2026-09-27')
        self.assertEqual(appended['commit_paths'], [])
        written = ['bionic/' + path for path in journal['recorded']]
        self.assertEqual(ignored(self.root, written), frozenset(written))
        self.assertEqual(git(self.root, 'rev-list', '--count', 'HEAD').stdout, before)
        self.assertEqual(git(self.root, 'status', '--porcelain').stdout, '')


PROPOSAL = {'title': 'Keep durable evidence', 'body': '# Decision\n\nPreserve the evidence.\n',
            'governs': [{'domain': 'evidence', 'rule': 'Preserve evidence.', 'scope': 'src/', 'handle': 'preserve-evidence'}]}
HAND_WRITTEN = '''---
id: ADR-0009
title: Hand written decision
status: Proposed
date: 2026-11-14
acceptance_format: crux.adr-acceptance.v1
governs:
- domain: evidence
  rule: Keep the evidence.
  scope: src/
  handle: keep-the-evidence
---

# Decision

Keep the evidence.
'''


class AdrMixin:
    def adr_council_and_accept(self, subject):
        """Gateway council, architect disposition and council-only acceptance of the exact bytes."""
        import decision_policy as dp
        output = stubbed(lambda: council.convene(self.root, 'adr', subject, 'Review the ADR.'))[0]
        self.assertEqual(output['outcome'], 'awaiting-architect', output)
        agreement = {'agrees': True, 'subject_sha256': digest((self.docs / subject).read_bytes()),
                     'nits': [], 'rationale': 'fixture agreement', 'dissent': []}
        settled = policy.disposition(self.root, output['record'], agreement)
        self.assertEqual(settled['outcome'], 'approved')
        accepted = dp.accept(self.root, subject, output['record'])
        self.assertEqual(accepted['policy'], 'council-only')
        return output

    def hand_written(self):
        path = self.docs / 'adrs/ADR-0009-hand-written.md'
        path.parent.mkdir(exist_ok=True)
        path.write_text(HAND_WRITTEN)
        return path.relative_to(self.docs).as_posix()


@unittest.skipUnless(HAVE_GATEWAY, 'gateway dependencies unavailable')
class IgnoredTreeAdrTests(AdrMixin, FixtureBase):
    """ADR propose, council and council-only acceptance, and adopt, in the ignored tree."""

    def test_propose_council_disposition_and_accept(self):
        import decision_policy as dp
        before = self.commits()
        subject = dp.propose(self.root, PROPOSAL, origin='direct')['path']
        output = self.adr_council_and_accept(subject)
        self.assertEqual(output['evidence_uncommitted'], 'tree-ignored')
        self.assertIn('status: Accepted', (self.docs / subject).read_text())
        self.assertEqual(self.commits(), before)
        self.assertEqual(self.tracked_docs(), [])

    def test_adopt_a_hand_written_proposed_adr_then_accept(self):
        import decision_policy as dp
        subject = self.hand_written()
        adopted = dp.adopt(self.root, subject)
        self.assertEqual(adopted['adopted_sha256'], digest((self.docs / subject).read_bytes()))
        self.adr_council_and_accept(subject)
        self.assertEqual(self.tracked_docs(), [])


class TrackedTreeAdoptTests(AdrMixin, FixtureBase):
    """adopt in a tracked tree still refuses an untracked and a modified ADR."""
    hide = None

    def test_untracked_and_modified_adrs_refuse_and_the_committed_one_adopts(self):
        import decision_policy as dp
        subject = self.hand_written()
        with self.assertRaises(dp.AdoptRefused) as caught:
            dp.adopt(self.root, subject)
        self.assertEqual(caught.exception.code, 'adopt-not-tracked-at-head')
        git(self.root, 'add', 'bionic/' + subject)
        git(self.root, 'commit', '-qm', 'add the ADR')
        path = self.docs / subject
        path.write_text(HAND_WRITTEN + '\nAn uncommitted line.\n')
        with self.assertRaises(dp.AdoptRefused) as caught:
            dp.adopt(self.root, subject)
        self.assertEqual(caught.exception.code, 'adopt-differs-from-head')
        # Positive control: the committed bytes adopt.
        path.write_text(HAND_WRITTEN)
        self.assertEqual(dp.adopt(self.root, subject)['adr'], 'ADR-0009')


class CriterionObservationBase(FixtureBase):
    def observation(self, name='evidence/observation.json'):
        from cycle_workflow import load
        head = git(self.root, 'rev-parse', 'HEAD').stdout.strip()
        path = self.docs / 'cycles' / self.cid / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({'criterion': 0, 'value': 'answer is 1', 'met': False, 'commit': head}))
        relative = path.relative_to(self.docs).as_posix()
        return relative, path, load(self.root, self.cid)


class IgnoredTreeCriterionObservationTests(CriterionObservationBase):
    def test_an_uncommitted_observation_in_the_ignored_tree_is_accepted(self):
        from cycle_workflow import criterion_observation
        relative, path, doc = self.observation()
        retained, record = criterion_observation(self.cfg, doc, 0, relative, before=True)
        self.assertEqual(retained, {'path': relative, 'sha256': digest(path.read_bytes())})
        self.assertFalse(record['met'])
        self.assertEqual(self.tracked_docs(), [])


class TrackedTreeCriterionObservationTests(CriterionObservationBase):
    hide = None

    def test_uncommitted_and_modified_observations_refuse_and_the_committed_one_reads(self):
        from cycle_workflow import criterion_observation
        relative, path, doc = self.observation()
        with self.assertRaisesRegex(CycleError, 'must match a committed file on HEAD'):
            criterion_observation(self.cfg, doc, 0, relative)
        git(self.root, 'add', 'bionic')
        git(self.root, 'commit', '-qm', 'record the observation')
        criterion_observation(self.cfg, doc, 0, relative)  # positive control
        path.write_text(path.read_text().replace('answer is 1', 'answer is one'))
        with self.assertRaisesRegex(CycleError, 'must match a committed file on HEAD'):
            criterion_observation(self.cfg, doc, 0, relative)


if __name__ == '__main__':
    unittest.main()
