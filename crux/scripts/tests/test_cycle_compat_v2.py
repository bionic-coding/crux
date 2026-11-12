"""Version-2 compatibility of the low-level writer, and the version-3 behavior of `create` and the readers.

`create` writes version 3. A version-2 record keeps every low-level behavior it had; the only
changes it sees are the two that apply to every record: owner-complete takes an optional
authority list, and a mutation from a linked worktree is refused. `--json` is accepted beside
`--file` on every low-level command that takes a document."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle
import cycle_summary
import test_cycle_simplify as simplify
from cycle_workflow import CycleError, create, load, mutate, validate, v3_fields
from test_cycle_slice import SliceBase, TEXT, version_two
from test_evidence import execute

SCRIPTS = Path(__file__).resolve().parents[1]
BASE = 'eaa5d56a2ea80db164bd74575ad64f8e8598efd6'
V3_TOP = ('revision', 'operations', 'results_dir')
V3_ASSIGNMENT = ('host', 'base', 'delivery')
OWNER = {'origin': 'owner-conversation', 'quote': 'close it', 'date': '2026-10-30', 'conversation': 'c'}


def run_main(argv, stdin=None):
    """Run `cycle.main` in process; return (exit code, parsed output)."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out), patch('sys.stdin', io.StringIO(stdin) if stdin is not None else sys.stdin):
        code = cycle.main(argv)
    return code, json.loads(out.getvalue())


def linked_commit(case, cid, body='answer = 2\n'):
    """Commit src/a.py with both trailers reconcile links on: the cycle id and the task."""
    (case.repo / 'src/a.py').write_text(body)
    case.git('add', 'src/a.py')
    case.git('commit', '-q', '-m', f'set the answer\n\nCycle: {cid}\nCycle-Task: build-it')
    return case.git('rev-parse', 'HEAD')


def deliver_build(case):
    """Prepare, work, attach and deliver the build task through the typed operations."""
    prepared = case.prepare(mode='background')
    sha = case.work(prepared)
    case.ok({'op': 'attach-execution', 'op_id': 'attach-001', 'assignment': prepared['assignment'], 'attempt': prepared['attempt'], 'handle': 'agent-7'})
    case.ok({'op': 'deliver', 'op_id': 'deliver-01', 'assignment': prepared['assignment'], 'attempt': prepared['attempt'], 'outcome': 'done', 'commits': [sha], 'stage': 'integrated'})
    return prepared, sha


class VersionTwoBase(SliceBase):
    """A SliceBase whose default record is a genuine version-2 record."""

    def fixture(self, version=2):
        return super().fixture(version=version)

    def assert_no_v3_fields(self, doc):
        self.assertEqual(doc['schema_version'], 2)
        for key in V3_TOP:
            self.assertNotIn(key, doc)
        for entry in doc.get('assignments', []):
            for key in V3_ASSIGNMENT:
                self.assertNotIn(key, entry)
        for entry in doc['history']:
            self.assertNotIn('revision', entry)


class CreateTests(SliceBase):
    def test_create_writes_version_three_with_revision_one_on_its_first_event(self):
        doc = create(self.repo, 'dev', 'T', 'G', ['src'], ['a'], 'builder', 'tester')
        self.assertEqual(doc['schema_version'], 3)
        self.assertEqual((doc['revision'], doc['operations'], doc['results_dir']), (1, [], None))
        self.assertEqual((doc['history'][0]['action'], doc['history'][0]['revision']), ('created', 1))
        self.assertEqual(json.loads(self.record_path(doc['id']).read_text()), doc)
        self.assertEqual(v3_fields(), {'revision': 0, 'operations': [], 'results_dir': None})

    def test_a_release_cycle_is_version_three_too(self):
        doc = create(self.repo, 'release', 'R', 'G', ['src'], ['a'], 'builder', 'tester', release_list='beta')
        self.assertEqual((doc['schema_version'], doc['revision']), (3, 1))

    def test_low_level_commands_increment_the_revision(self):
        steps = [
            ('checks', {'checks': ['unit']}),
            ('assignment', {'id': 'dev-1', 'state': 'running', 'role': 'developer', 'task': None}),
            ('assignment', {'id': 'dev-1', 'seen': True}),
            ('pause', {'reason': 'owner decision'}),
            ('resume', {'reason': 'decided'}),
        ]
        revision = load(self.repo, self.cid)['revision']
        for action, args in steps:
            with self.subTest(action=action):
                doc = mutate(self.repo, self.cid, action, **args)
                revision += 1
                self.assertEqual((doc['revision'], doc['history'][-1]['revision']), (revision, revision))


class VersionTwoSequenceTests(VersionTwoBase):
    def test_a_version_two_record_runs_the_whole_low_level_sequence_unchanged(self):
        cid = self.cid
        self.assert_no_v3_fields(load(self.repo, cid))
        # An assignment holds a task on version 2 only in the running state, and a task status change is not refused.
        mutate(self.repo, cid, 'assignment', id='dev-1', state='running', role='developer', task='build-it', agent='a1', result_path='/tmp/r1.md')
        doc = mutate(self.repo, cid, 'task', task_id='build-it', state='active', assignee='dev-1')
        self.assertEqual(doc['plan']['tasks'][0]['status'], 'active')
        with self.assertRaisesRegex(CycleError, 'held by running assignment dev-1'):
            mutate(self.repo, cid, 'assignment', id='dev-2', state='running', role='developer', task='build-it')
        mutate(self.repo, cid, 'assignment', id='dev-1', state='lost', note='host lists no handle a1')
        mutate(self.repo, cid, 'assignment', id='dev-1', state='running', role='developer', task='build-it')
        self.assertEqual(load(self.repo, cid)['assignments'][0]['attempt'], 2)
        mutate(self.repo, cid, 'assignment', id='dev-1', state='finished', note='report returned')
        # Delivery: a commit with the task trailer, recorded through the low-level task update.
        (self.repo / 'src/a.py').write_text('answer = 2\n')
        self.git('add', 'src/a.py'); self.git('commit', '-q', '-m', 'set the answer\n\nCycle-Task: build-it')
        sha = self.git('rev-parse', 'HEAD')
        doc = mutate(self.repo, cid, 'task', task_id='build-it', state='done', commits=[sha], stage='integrated')
        self.assertEqual((doc['plan']['tasks'][0]['status'], doc['plan']['tasks'][0]['commits']), ('done', [sha]))
        # Checks, evidence and advance through Test and Review.
        mutate(self.repo, cid, 'advance')
        mutate(self.repo, cid, 'checks', checks=['unit'])
        mutate(self.repo, cid, 'coverage', coverage={'affected': ['the answer'], 'checks': [{'check_id': 'unit', 'rationale': 'reads src/a.py'}], 'not_selected': 'no other behavior'})
        decl = {'check_id': 'unit', 'command': [sys.executable, '-c', "from pathlib import Path; assert Path('src/a.py').read_text() == 'answer = 2\\n'"], 'inputs': ['src'], 'environment': []}
        result = execute(self.repo, decl)
        mutate(self.repo, cid, 'evidence', check_id='unit', evidence_id=result['evidence']['id'], use=result['action'])
        mutate(self.repo, cid, 'advance')
        mutate(self.repo, cid, 'review', report={'reviewer': 'independent', 'scope': ['src'], 'evidence': [result['evidence']['id']], 'blocking': [], 'advisory': [], 'cosmetic': [],
                                                 'verdict': 'approve', 'rationale': 'reviewed the change'})
        self.assertEqual(mutate(self.repo, cid, 'advance')['phase'], 'reflect')
        # Pause and resume, then close with the owner's words and no authority list.
        self.assertEqual(mutate(self.repo, cid, 'pause', reason='owner decision')['status'], 'paused')
        self.assertEqual(mutate(self.repo, cid, 'resume', reason='decided')['status'], 'active')
        doc = mutate(self.repo, cid, 'owner-complete', owner=OWNER)
        self.assertEqual(doc['status'], 'completed')
        self.assertEqual(doc['history'][-1]['owner']['authority'], [])
        self.assert_no_v3_fields(doc)
        self.assert_no_v3_fields(json.loads(self.record_path().read_text()))

    def test_low_level_finished_is_accepted_on_a_version_two_running_assignment_with_a_task(self):
        mutate(self.repo, self.cid, 'assignment', id='dev-1', state='running', role='developer', task='build-it')
        doc = mutate(self.repo, self.cid, 'assignment', id='dev-1', state='finished')
        self.assertEqual(doc['assignments'][0]['state'], 'finished')
        self.assert_no_v3_fields(doc)

    def test_a_reserved_state_is_not_valid_on_version_two(self):
        doc = load(self.repo, self.cid)
        doc['assignments'] = [{'id': 'x', 'role': 'developer', 'task': None, 'agent': None, 'result_path': None, 'state': 'reserved', 'attempt': 1,
                               'started_at': 'now', 'last_seen': 'now', 'ended_at': None, 'note': None}]
        with self.assertRaises(CycleError):
            validate(doc)

    def test_the_version_two_helper_makes_a_record_that_validates(self):
        raw = version_two(self.record_path())
        self.assertEqual(raw['schema_version'], 2)
        self.assertEqual(load(self.repo, self.cid)['schema_version'], 2)


class VersionThreeHolderTests(SliceBase):
    """The same sequence's first step on version 3: the task status change is refused while the attempt holds the task."""

    def test_a_task_status_change_is_refused_while_a_low_level_attempt_holds_the_task(self):
        mutate(self.repo, self.cid, 'assignment', id='dev-1', state='running', role='developer', task='build-it')
        with self.assertRaisesRegex(CycleError, 'held by running assignment dev-1'):
            mutate(self.repo, self.cid, 'task', task_id='build-it', state='active')
        entry = load(self.repo, self.cid)['assignments'][0]
        self.assertEqual({k: entry[k] for k in V3_ASSIGNMENT}, {'host': None, 'base': None, 'delivery': None})


class JsonFormTests(SliceBase):
    """`--json` beside `--file` on every low-level command that takes a document: inline, and `-` for standard input."""

    def forms(self, command, document, *flags, cid=None):
        """Run one command in both forms; return the two parsed outputs."""
        cid = cid or self.cid
        text = json.dumps(document)
        inline = run_main(['--repo-root', str(self.repo), command, cid, *flags, '--json', text])
        piped = run_main(['--repo-root', str(self.repo), command, cid, *flags, '--json', '-'], stdin=text)
        return inline, piped

    def both_ok(self, command, document, *flags, cid=None):
        for form, (code, out) in zip(('inline', 'stdin'), self.forms(command, document, *flags, cid=cid)):
            self.assertEqual(code, 0, (form, out)); self.assertTrue(out['ok'], (form, out))

    def test_every_file_command_takes_json_and_refuses_both_or_neither(self):
        for command in cycle.FILE_COMMANDS:
            with self.subTest(command=command), self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
                cycle.parser().parse_args([command, 'CYC-0001'] + (['--reason', 'r'] if command in ('plan', 'plan-details') else []))
            with self.subTest(command=command, both=True), self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
                cycle.parser().parse_args([command, 'CYC-0001', '--file', 'x.json', '--json', '{}'] + (['--reason', 'r'] if command in ('plan', 'plan-details') else []))
        self.assertEqual(sorted(cycle.FILE_COMMANDS), sorted(['plan', 'review', 'decision', 'reflect', 'task-add', 'coverage', 'plan-details', 'owner-complete', 'shortcut', 'reduction']))

    def test_help_names_the_json_form(self):
        for command in cycle.FILE_COMMANDS:
            with self.subTest(command=command):
                sub = next(a for a in cycle.parser()._subparsers._group_actions[0].choices.items() if a[0] == command)[1]
                text = ' '.join(sub.format_help().split())
                self.assertIn('--json JSON', text); self.assertIn("'-' reads standard input", text)

    def test_task_add(self):
        def task(ident):
            return {'id': ident, 'phase': 'build', 'description': ident, 'depends_on': [], 'status': 'pending', 'expected_evidence': ['x']}
        code, out = run_main(['--repo-root', str(self.repo), 'task-add', self.cid, '--json', json.dumps(task('more-1'))])
        self.assertEqual(code, 0, out)
        code, out = run_main(['--repo-root', str(self.repo), 'task-add', self.cid, '--json', '-'], stdin=json.dumps(task('more-2')))
        self.assertEqual(code, 0, out)
        self.assertEqual([t['id'] for t in load(self.repo, self.cid)['plan']['tasks']], ['build-it', 'more-1', 'more-2'])

    def test_coverage(self):
        deliver_build(self)
        mutate(self.repo, self.cid, 'advance')
        mutate(self.repo, self.cid, 'checks', checks=['unit'])
        self.both_ok('coverage', {'affected': ['the answer'], 'checks': [{'check_id': 'unit', 'rationale': 'reads src/a.py'}], 'not_selected': 'no other behavior'})

    def test_reflect(self):
        mutate(self.repo, self.cid, 'pause', reason='owner decision')
        self.both_ok('reflect', {'outcome': 'done', 'lessons': ['l'], 'remaining': ['none']})

    def test_plan_details(self):
        self.both_ok('plan-details', {'constraints': ['edit only src']}, '--reason', 'tighten')

    def test_owner_complete_inline_and_stdin(self):
        other = self.fixture()
        code, out = run_main(['--repo-root', str(self.repo), 'owner-complete', self.cid, '--json', json.dumps(OWNER)])
        self.assertEqual((code, out['cycle']['status']), (0, 'completed'), out)
        code, out = run_main(['--repo-root', str(self.repo), 'owner-complete', other, '--json', '-'], stdin=json.dumps(OWNER))
        self.assertEqual((code, out['cycle']['status']), (0, 'completed'), out)

    def test_review(self):
        self.prepare_review()
        self.both_ok('review', {'reviewer': 'independent', 'scope': ['src'], 'evidence': [self.receipt], 'blocking': [], 'advisory': [], 'cosmetic': [],
                                'verdict': 'approve', 'rationale': 'reviewed the change'})
        self.assertEqual(len(load(self.repo, self.cid)['reviews']), 2)

    def prepare_review(self):
        cid = self.cid
        deliver_build(self)
        mutate(self.repo, cid, 'advance')
        mutate(self.repo, cid, 'checks', checks=['unit'])
        mutate(self.repo, cid, 'coverage', coverage={'affected': ['the answer'], 'checks': [{'check_id': 'unit', 'rationale': 'reads src/a.py'}], 'not_selected': 'none'})
        decl = {'check_id': 'unit', 'command': [sys.executable, '-c', "from pathlib import Path; assert Path('src/a.py').read_text() == 'answer = 2\\n'"], 'inputs': ['src'], 'environment': []}
        result = execute(self.repo, decl)
        self.receipt = result['evidence']['id']
        mutate(self.repo, cid, 'evidence', check_id='unit', evidence_id=self.receipt, use=result['action'])
        mutate(self.repo, cid, 'advance')

    def test_a_bad_json_document_refuses_with_exit_one_and_writes_nothing(self):
        before = self.record_path().read_bytes()
        code, out = run_main(['--repo-root', str(self.repo), 'task-add', self.cid, '--json', '{not json'])
        self.assertEqual((code, out['ok']), (1, False))
        self.assertEqual(self.record_path().read_bytes(), before)

    def test_an_apostrophe_and_a_newline_survive_a_real_shell(self):
        document = {'id': 'quote-1', 'phase': 'build', 'description': "it's two\nlines", 'depends_on': [], 'status': 'pending', 'expected_evidence': ["don't"]}
        inline = shlex.quote(json.dumps(document))
        self.assertIn("'\"'\"'", inline)  # the apostrophe needed shell quoting
        self.assertIn('\\n', inline)  # the newline is the two characters backslash and n inside the JSON
        command = f"{shlex.quote(sys.executable)} {shlex.quote(str(SCRIPTS / 'cycle.py'))} --repo-root {shlex.quote(str(self.repo))} task-add {self.cid} --json {inline}"
        done = subprocess.run(['sh', '-c', command], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        task = next(t for t in load(self.repo, self.cid)['plan']['tasks'] if t['id'] == 'quote-1')
        self.assertEqual((task['description'], task['expected_evidence']), ("it's two\nlines", ["don't"]))
        piped = subprocess.run(['sh', '-c', f"printf %s {shlex.quote(json.dumps({**document, 'id': 'quote-2'}))} | {shlex.quote(sys.executable)} {shlex.quote(str(SCRIPTS / 'cycle.py'))} --repo-root {shlex.quote(str(self.repo))} task-add {self.cid} --json -"],
                               capture_output=True, text=True)
        self.assertEqual(piped.returncode, 0, piped.stdout + piped.stderr)
        again = next(t for t in load(self.repo, self.cid)['plan']['tasks'] if t['id'] == 'quote-2')
        self.assertEqual(again['description'], "it's two\nlines")


class SimplifyJsonTests(simplify.Base):
    """plan, decision and reduction need a simplify cycle."""

    def cli(self, cid, command, document, *flags, stdin=False):
        text = json.dumps(document)
        return run_main(['--repo-root', str(self.repo), command, cid, *flags, '--json', '-' if stdin else text], stdin=text if stdin else None)

    def test_plan_and_decision(self):
        doc = self.direct()
        plan = json.loads(json.dumps(doc['plan']))
        plan.update(verification=['focused tests'], tasks=[{'id': p, 'phase': p, 'description': p, 'depends_on': [], 'status': 'pending', 'expected_evidence': ['x']} for p in simplify.PHASES['simplify']])
        for stdin in (False, True):
            code, out = self.cli(doc['id'], 'plan', plan, '--reason', 'plan', stdin=stdin)
            self.assertEqual(code, 0, out)
            plan['revision'] = out['cycle']['plan']['revision']
        for stdin, name in ((False, 'one'), (True, 'two')):
            code, out = self.cli(doc['id'], 'decision', simplify.selection(), '--kind', 'idr', '--name', name, stdin=stdin)
            self.assertEqual(code, 0, out)
        self.assertEqual([d['name'] for d in load(self.repo, doc['id'])['decisions']], ['one', 'two'])

    def test_reduction(self):
        doc = self.to_test(self.approved(self.direct(), 'owner'))
        for stdin in (False, True):
            code, out = self.cli(doc['id'], 'reduction', simplify.reduction(), stdin=stdin)
            self.assertEqual(code, 0, out)
            self.assertEqual(out['cycle']['history'][-1]['action'], 'reduction')


class ReaderTests(SliceBase):
    def run_handoff(self, cid=None):
        return run_main(['--repo-root', str(self.repo), 'handoff', cid or self.cid])

    def test_handoff_lists_a_reserved_attempt_with_its_state_and_host(self):
        prepared = self.prepare()
        code, report = self.run_handoff()
        self.assertEqual(code, 0, report)
        [row] = report['assignments']
        self.assertEqual((row['id'], row['state'], row['host'], row['attempt'], row['task']), (prepared['assignment'], 'reserved', 'claude-code', 1, 'build-it'))
        self.assertGreaterEqual(row['elapsed_seconds'], 0)
        self.assertTrue(any('reserved attempt' in step for step in report['resume_steps']))

    def test_handoff_lists_a_running_attempt_too(self):
        prepared = self.prepare(mode='background')
        self.ok({'op': 'attach-execution', 'op_id': 'attach-001', 'assignment': prepared['assignment'], 'attempt': prepared['attempt'], 'handle': 'agent-7'})
        [row] = self.run_handoff()[1]['assignments']
        self.assertEqual((row['state'], row['agent'], row['host']), ('running', 'agent-7', 'claude-code'))

    def test_handoff_on_a_low_level_version_three_entry_has_a_null_host(self):
        mutate(self.repo, self.cid, 'assignment', id='dev-1', state='running', role='developer')
        [row] = self.run_handoff()[1]['assignments']
        self.assertEqual((row['state'], row['host']), ('running', None))

    def test_handoff_is_unchanged_for_version_two(self):
        cid = self.fixture(version=2)
        mutate(self.repo, cid, 'assignment', id='dev-1', state='running', role='developer', agent='a1')
        [row] = self.run_handoff(cid)[1]['assignments']
        self.assertEqual(set(row), {'id', 'role', 'task', 'agent', 'result_path', 'attempt', 'started_at', 'last_seen', 'elapsed_seconds'})
        self.assertFalse(any('reserved attempt' in step for step in self.run_handoff(cid)[1]['resume_steps']))

    def test_summary_shows_revision_and_attempt_counts_for_version_three(self):
        self.prepare()
        summary = cycle_summary.summarize(load(self.repo, self.cid))
        self.assertEqual((summary['schema_version'], summary['revision'], summary['attempts']), (3, load(self.repo, self.cid)['revision'], {'reserved': 1, 'running': 0}))

    def test_reconcile_does_not_propose_a_status_change_for_a_held_task(self):
        self.prepare()
        linked_commit(self, self.cid)
        before = self.record_path().read_bytes()
        code, report = run_main(['--repo-root', str(self.repo), 'reconcile', self.cid])
        self.assertEqual(code, 0, report)
        self.assertEqual([p['set'].get('state') for p in report['proposed']], [None])
        self.assertTrue(any('holds the task' in u['reason'] and 'reserved assignment' in u['reason'] for u in report['unresolved']), report['unresolved'])
        code, report = run_main(['--repo-root', str(self.repo), 'reconcile', self.cid, '--apply'])
        self.assertEqual(code, 0, report)
        doc = load(self.repo, self.cid)
        task = doc['plan']['tasks'][0]
        self.assertNotEqual(task['status'], 'done')
        self.assertTrue(task['commits'])
        self.assertNotEqual(self.record_path().read_bytes(), before)

    def test_reconcile_still_completes_a_task_with_no_open_attempt(self):
        deliver_build(self)
        code, report = run_main(['--repo-root', str(self.repo), 'reconcile', self.cid])
        self.assertEqual(code, 0, report)
        self.assertEqual(report['unresolved'], [])

    def test_reconcile_on_version_two_proposes_done_for_a_running_assignment(self):
        cid = self.fixture(version=2)
        mutate(self.repo, cid, 'assignment', id='dev-1', state='running', role='developer', task='build-it')
        linked_commit(self, cid)
        code, report = run_main(['--repo-root', str(self.repo), 'reconcile', cid])
        self.assertEqual(code, 0, report)
        self.assertEqual([(p['task'], p['set'].get('state')) for p in report['proposed']], [('build-it', 'done')])


class CommittedRecordTests(unittest.TestCase):
    ROOT = Path(__file__).resolve().parents[3] / 'bionic/cycles'
    OLD_KEYS = {'id', 'type', 'title', 'status', 'phase', 'pass', 'pass_limit', 'plan_revision', 'blocker', 'tasks', 'required_checks', 'evidence_count',
                'latest_review', 'decision_count', 'recent_history'}

    def records(self):
        if not self.ROOT.is_dir():
            self.skipTest('the dogfood tree is not in this checkout')
        found = sorted(self.ROOT.glob('*/cycle.json'))
        self.assertTrue(found)
        return found

    def test_every_committed_record_validates_and_summarizes_with_the_earlier_keys(self):
        for path in self.records():
            with self.subTest(path=path.parent.name):
                doc = json.loads(path.read_text())
                validate(doc)
                if doc['schema_version'] != 3:
                    self.assertEqual(set(cycle_summary.summarize(doc)), self.OLD_KEYS)

    def test_summary_rendering_matches_the_base_commit_for_every_committed_record(self):
        probe = subprocess.run(['git', '-C', str(self.ROOT.parent.parent), 'cat-file', '-e', f'{BASE}:crux/scripts/cycle_summary.py'], capture_output=True)
        if probe.returncode != 0:
            self.skipTest('the base commit is not reachable from this checkout')
        source = subprocess.run(['git', '-C', str(self.ROOT.parent.parent), 'show', f'{BASE}:crux/scripts/cycle_summary.py'], capture_output=True, text=True, check=True).stdout
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'base_cycle_summary.py'; path.write_text(source)
            spec = importlib.util.spec_from_file_location('base_cycle_summary', path)
            base = importlib.util.module_from_spec(spec); spec.loader.exec_module(base)
        for record in self.records():
            with self.subTest(path=record.parent.name):
                doc = json.loads(record.read_text())
                summary = cycle_summary.summarize(doc)
                if doc['schema_version'] == 3:
                    # The base predates version 3; such a record adds exactly its four keys and
                    # keeps every earlier key's rendering.
                    self.assertEqual(list(summary)[-4:], ['schema_version', 'revision', 'attempts', 'classifications'])
                    summary = {k: v for k, v in summary.items() if k not in ('schema_version', 'revision', 'attempts', 'classifications')}
                self.assertEqual(cycle_summary.render(summary), base.render(base.summarize(doc)))


if __name__ == '__main__':
    unittest.main()
