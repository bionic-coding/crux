"""A release cycle runs one of two fixed task lists chosen at create; a record without a list is historical."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cycle_workflow import CycleError, PHASES, LIMITS, create, load, mutate, tree, validate

try:
    from ._dev_surface import REPO_ROOT, TREE, require_dev_surface
except ImportError:
    from _dev_surface import REPO_ROOT, TREE, require_dev_surface

SCRIPTS = Path(__file__).resolve().parents[1]
BETA = ['prep', 'prepare', 'verify', 'beta-and-smoke', 'tag', 'record']
OFFICIAL = ['live-check-and-go-ahead', 'official', 'record']
SCOPE = ['src', 'bionic/log.md']


class ListedBase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / 'repo'
        for directory in ('bionic', 'src'):
            (self.root / directory).mkdir(parents=True)
        (self.root / 'bionic/manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\n')
        (self.root / 'bionic/log.md').write_text('log\n')
        (self.root / 'src/a.txt').write_text('good')
        self.git('init', '-q')
        self.git('add', '-A')
        self.git('commit', '-qm', 'base')

    def git(self, *args):
        return subprocess.run(['git', '-c', 'user.name=T', '-c', 'user.email=t@example.invalid', *args], cwd=self.root, capture_output=True, check=True, text=True).stdout.strip()

    def cli(self, *args, ok=True):
        run = subprocess.run([sys.executable, str(SCRIPTS / 'cycle.py'), '--repo-root', str(self.root), *args], capture_output=True, text=True)
        out = json.loads(run.stdout)
        self.assertEqual(out['ok'], ok, out)
        return out['cycle'] if ok else out['error']

    def make(self, release_list='beta'):
        return create(self.root, 'release', 'Release', 'Outcome', SCOPE, ['published'], 'builder', 'tester', release_list=release_list)

    def task(self, doc, tid, state='done', **extra):
        return mutate(self.root, doc['id'], 'task', task_id=tid, state=state, **extra)

    def finish(self, doc):
        for task in doc['plan']['tasks']:
            doc = self.task(doc, task['id'])
        return doc


class CreateTests(ListedBase):
    def test_create_without_a_list_refuses(self):
        with self.assertRaisesRegex(CycleError, '--list'):
            create(self.root, 'release', 'Release', 'Outcome', SCOPE, ['published'], 'builder', 'tester')
        self.assertFalse((self.root / 'bionic/cycles').exists() and any((self.root / 'bionic/cycles').glob('CYC-*')))

    def test_cli_create_without_a_list_refuses_and_with_one_succeeds(self):
        base = ['create', '--type', 'release', '--title', 'T', '--goal', 'G', '--implementer', 'b', '--coordinator', 'c', '--scope', 'src', '--acceptance', 'a']
        self.assertIn('--list', self.cli(*base, ok=False))
        doc = self.cli(*base, '--list', 'official')
        self.assertEqual(doc['release_list'], 'official')

    def test_an_unknown_list_or_a_list_on_another_type_refuses(self):
        with self.assertRaises(CycleError):
            self.make('both')
        with self.assertRaises(CycleError):
            create(self.root, 'dev', 'T', 'G', SCOPE, ['a'], 'b', 'c', release_list='beta')

    def test_the_beta_list(self):
        doc = self.make('beta')
        self.assertEqual([t['id'] for t in doc['plan']['tasks']], BETA)
        self.assertEqual((doc['release_list'], doc['phase'], doc['pass'], doc['pass_limit'], doc['schema_version']), ('beta', 'release', 1, 1, 2))
        self.assertEqual(PHASES['release'], ['release'])
        self.assertEqual(LIMITS['release'], 1)

    def test_the_official_list(self):
        doc = self.make('official')
        self.assertEqual([t['id'] for t in doc['plan']['tasks']], OFFICIAL)
        self.assertEqual(doc['release_list'], 'official')

    def test_every_task_is_release_phase_chained_and_carries_evidence_text(self):
        for name, ids in (('beta', BETA), ('official', OFFICIAL)):
            doc = self.make(name)
            previous = None
            for task in doc['plan']['tasks']:
                self.assertEqual(task['phase'], 'release')
                self.assertEqual(task['depends_on'], [previous] if previous else [])
                self.assertEqual(task['status'], 'pending')
                self.assertTrue(task['expected_evidence'] and task['description'])
                self.assertNotRegex(json.dumps(task), r'ADR-\d')
                previous = task['id']

    def test_validate_refuses_a_listed_record_that_differs_from_its_list(self):
        doc = self.make('beta')
        def edited(edit):
            copy = deepcopy(doc)
            edit(copy)
            return copy
        edits = {
            'renamed id': lambda d: d['plan']['tasks'][0].update(id='prep2'),
            'dropped task': lambda d: d['plan']['tasks'].pop(),
            'reordered': lambda d: d['plan']['tasks'].reverse(),
            'extra task': lambda d: d['plan']['tasks'].append({**d['plan']['tasks'][0], 'id': 'extra', 'depends_on': ['record']}),
            'phase': lambda d: d['plan']['tasks'][1].update(phase='build'),
            'dependency': lambda d: d['plan']['tasks'][2].update(depends_on=[]),
        }
        for name, edit in edits.items():
            with self.subTest(name), self.assertRaises(CycleError):
                validate(edited(edit))
        validate(edited(lambda d: d['plan']['tasks'][0].update(status='done')))


class ActionTests(ListedBase):
    RETIRED = {
        'plan': {'plan': {}, 'reason': 'r'},
        'task-add': {'task': {}},
        'plan-details': {'details': {}, 'reason': 'r'},
        'checks': {'checks': ['x']},
        'coverage': {'coverage': {}},
        'evidence': {'check_id': 'x', 'evidence_id': 'y', 'use': 'executed'},
        'review': {'report': {}},
        'scrutiny': {'scrutiny': 'standard', 'rationale': 'r', 'risks': []},
        'decision': {'kind': 'idr', 'name': 'n', 'contents': {}},
        'approve-decision': {'subject': 'x', 'approval': 'y'},
        'reflect': {'reflection': {'outcome': 'o', 'lessons': ['l'], 'remaining': ['none']}},
        'return': {'improved': 'a', 'unresolved': 'b', 'next_change': 'c', 'justification': 'd', 'progress': True},
        'extend': {'human_approval': 'ok', 'limit': 5},
        'change-type': {'kind': 'dev', 'reason': 'r'},
        'reduction': {'reduction': {}},
    }

    def test_every_retired_action_refuses_naming_the_decision_and_changes_nothing(self):
        for name in ('beta', 'official'):
            doc = self.make(name)
            before = (self.root / 'bionic/cycles' / doc['id'] / 'cycle.json').read_bytes()
            for action, args in self.RETIRED.items():
                with self.subTest(list=name, action=action), self.assertRaisesRegex(CycleError, 'ADR-0163'):
                    mutate(self.root, doc['id'], action, **args)
            self.assertEqual((self.root / 'bionic/cycles' / doc['id'] / 'cycle.json').read_bytes(), before)

    def test_refusal_holds_while_paused(self):
        doc = self.make()
        mutate(self.root, doc['id'], 'pause', reason='tooling outage')
        with self.assertRaisesRegex(CycleError, 'ADR-0163'):
            mutate(self.root, doc['id'], 'reflect', reflection={'outcome': 'o', 'lessons': ['l'], 'remaining': ['none']})

    def test_the_deleted_release_actions_are_gone(self):
        doc = create(self.root, 'dev', 'T', 'G', SCOPE, ['a'], 'b', 'c')
        for action in ('release-ready', 'release-verified'):
            with self.subTest(action), self.assertRaisesRegex(CycleError, 'unknown cycle action'):
                mutate(self.root, doc['id'], action, authorization='x', destinations=['d'], artifacts=[], verification='v')
            self.assertEqual(subprocess.run([sys.executable, str(SCRIPTS / 'cycle.py'), '--repo-root', str(self.root), action, doc['id']], capture_output=True, text=True).returncode, 2)

    def test_task_pause_resume_and_abandon_need_no_reflection(self):
        doc = self.make()
        doc = self.task(doc, 'prep', state='active', note='working')
        self.assertEqual(doc['plan']['tasks'][0]['status'], 'active')
        doc = mutate(self.root, doc['id'], 'pause', reason='withheld go-ahead')
        doc = mutate(self.root, doc['id'], 'resume', reason='go-ahead given')
        self.assertEqual(doc['status'], 'active')
        doc = mutate(self.root, doc['id'], 'abandon')
        self.assertEqual((doc['status'], doc['reflection']), ('abandoned', None))

    def test_a_paused_cycle_abandons_without_reflection(self):
        doc = self.make('official')
        mutate(self.root, doc['id'], 'pause', reason='tooling outage')
        self.assertEqual(mutate(self.root, doc['id'], 'abandon')['status'], 'abandoned')

    def test_owner_complete_is_allowed(self):
        doc = self.make()
        (self.root / 'authority.md').write_text('owner\n')
        owner = {'origin': 'owner-conversation', 'quote': 'close it', 'date': '2026-10-21', 'conversation': 'c', 'authority': ['authority.md']}
        self.assertEqual(mutate(self.root, doc['id'], 'owner-complete', owner=owner)['status'], 'completed')

    def test_read_only_commands_work(self):
        doc = self.make()
        for command in ('show', 'validate', 'handoff', 'query-decisions'):
            with self.subTest(command):
                run = subprocess.run([sys.executable, str(SCRIPTS / 'cycle.py'), '--repo-root', str(self.root), command, doc['id']], capture_output=True, text=True)
                self.assertEqual(run.returncode, 0, run.stdout + run.stderr)


class AdvanceTests(ListedBase):
    def complete(self, doc):
        sha = self.git('rev-parse', 'HEAD')
        return mutate(self.root, doc['id'], 'completion', commits=[sha], exception=None, remaining='none')

    def test_advance_completes_when_every_task_is_done_and_completion_holds(self):
        for name in ('beta', 'official'):
            doc = self.finish(self.make(name))
            doc = self.complete(doc)
            doc = mutate(self.root, doc['id'], 'advance')
            self.assertEqual((doc['status'], doc['phase'], doc['reflection']), ('completed', 'release', None), name)

    def test_advance_refuses_unfinished_tasks_and_a_missing_completion(self):
        doc = self.make()
        with self.assertRaisesRegex(CycleError, 'unfinished'):
            mutate(self.root, doc['id'], 'advance')
        doc = self.finish(doc)
        with self.assertRaisesRegex(CycleError, 'completion'):
            mutate(self.root, doc['id'], 'advance')

    def test_advance_refuses_when_scope_changed_after_completion(self):
        doc = self.complete(self.finish(self.make()))
        (self.root / 'src/a.txt').write_text('changed')
        with self.assertRaisesRegex(CycleError, 'completion'):
            mutate(self.root, doc['id'], 'advance')


class RerunTests(ListedBase):
    def states(self, doc):
        return [t['status'] for t in doc['plan']['tasks']]

    def test_resetting_a_task_resets_every_later_task(self):
        doc = self.finish(self.make())
        doc = self.task(doc, 'verify', state='pending', note='fix abc1234')
        self.assertEqual(self.states(doc), ['done', 'done', 'pending', 'pending', 'pending', 'pending'])
        self.assertEqual(doc['plan']['tasks'][2]['note'], 'fix abc1234')
        self.assertEqual((doc['pass'], doc['pass_limit'], doc['status'], doc['phase']), (1, 1, 'active', 'release'))
        self.assertFalse([e for e in doc['history'] if e['action'] in ('return-requested', 'resume')])

    def test_an_active_task_resets_later_tasks_and_the_rerun_needs_no_note(self):
        doc = self.make('official')
        for tid in ('live-check-and-go-ahead', 'official'):
            doc = self.task(doc, tid, state='active') if tid == 'official' else self.task(doc, tid)
        doc = self.task(doc, 'live-check-and-go-ahead', state='pending')
        self.assertEqual(self.states(doc), ['pending', 'pending', 'pending'])

    def test_a_task_that_was_already_pending_leaves_the_rest_alone(self):
        doc = self.task(self.make(), 'prep')
        before = self.states(doc)
        self.assertEqual(before, ['done'] + ['pending'] * 5)
        doc = self.task(doc, 'prepare', state='pending', note='again')
        self.assertEqual(self.states(doc), before)

    def test_completing_a_later_task_still_needs_its_dependency(self):
        doc = self.make()
        with self.assertRaisesRegex(CycleError, 'dependencies'):
            self.task(doc, 'verify')


class LegacyTests(ListedBase):
    """A release record without release_list is historical: it validates and displays, and can only be closed."""

    def legacy(self, phase='plan', status='active'):
        doc = self.make()
        path = self.root / 'bionic/cycles' / doc['id'] / 'cycle.json'
        record = json.loads(path.read_text())
        record.pop('release_list')
        record.update(phase=phase, status=status, pass_limit=2)
        record['plan']['tasks'] = [{'id': p, 'phase': p, 'description': p, 'depends_on': [], 'status': 'pending', 'expected_evidence': ['proof']} for p in ('plan', 'release', 'reflect')]
        path.write_text(json.dumps(record))
        return record['id']

    def test_it_validates_and_shows(self):
        cid = self.legacy()
        doc = load(self.root, cid)
        self.assertEqual((doc['phase'], doc['pass_limit']), ('plan', 2))
        self.assertEqual(self.cli('show', cid, '--full')['id'], cid)
        with self.assertRaises(CycleError):
            record = deepcopy(doc)
            record['phase'] = 'build'
            validate(record)

    def test_it_renders_as_before(self):
        from cycle_progress import view, render
        cid = self.legacy('release')
        c = view(self.root, cid)['cycles'][0]
        self.assertEqual((c['phases'], c['pass_limit']), (['plan', 'release', 'reflect'], 2))
        self.assertIn('Pass 1 of 2', render(view(self.root, cid)))

    def test_it_refuses_every_mutation_except_pause_reflect_and_abandon(self):
        cid = self.legacy()
        refused = dict(ActionTests.RETIRED, task={'task_id': 'plan', 'state': 'done'}, advance={}, completion={'commits': None, 'exception': 'x', 'remaining': ['none']},
                       resume={'reason': 'r'}, **{'owner-complete': {'owner': {}}})
        for action, args in refused.items():
            if action == 'reflect':
                continue
            with self.subTest(action), self.assertRaisesRegex(CycleError, 'historical release'):
                mutate(self.root, cid, action, **args)

    def test_it_can_only_be_closed(self):
        cid = self.legacy()
        mutate(self.root, cid, 'pause', reason='upgrade')
        with self.assertRaisesRegex(CycleError, 'reflection'):
            mutate(self.root, cid, 'abandon')
        mutate(self.root, cid, 'reflect', reflection={'outcome': 'o', 'lessons': ['l'], 'remaining': ['none']})
        self.assertEqual(mutate(self.root, cid, 'abandon')['status'], 'abandoned')


class CommittedRecordsTests(unittest.TestCase):
    """Every committed cycle record loads, validates and renders under its original interpretation."""
    ROOT = REPO_ROOT

    def test_every_committed_record_validates_and_renders(self):
        require_dev_surface(self, self.ROOT / TREE / 'cycles' / 'CYC-0040' / 'cycle.json', 'committed cycle records')
        from cycle_progress import view, render
        ids = sorted(p.name for p in (self.ROOT / TREE / 'cycles').glob('CYC-*') if (p / 'cycle.json').is_file())
        legacy = {'CYC-0009', 'CYC-0015', 'CYC-0018', 'CYC-0021', 'CYC-0022', 'CYC-0031', 'CYC-0032', 'CYC-0034', 'CYC-0037', 'CYC-0040'}
        self.assertLessEqual(legacy, set(ids))
        for cid in ids:
            with self.subTest(cycle=cid):
                doc = load(self.ROOT, cid)
                shown = view(self.ROOT, cid)['cycles'][0]
                text = render(view(self.ROOT, cid))
                self.assertIn(cid, text)
                if cid in legacy:
                    self.assertNotIn('release_list', doc)
                    self.assertEqual(shown['phases'], ['plan', 'release', 'reflect'])
                    self.assertEqual(shown['pass_limit'], doc['pass_limit'])


if __name__ == '__main__':
    unittest.main()
