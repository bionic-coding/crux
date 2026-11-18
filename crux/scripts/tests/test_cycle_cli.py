"""The ordinary cycle command line: writer commands at top level, the `pilot` alias, retired typed commands, legacy `show`.

`cycle.py` exposes the writer's commands (create, show, plan, task, ...) directly and under `pilot`; both routes reach
one record through the same functions. Every other former subcommand exits 1 with `command-retired`. Neither path, nor
`show` on a legacy record, loads a typed-engine module: a subprocess lists `sys.modules` after the run, and a positive
control shows the same probe seeing a script that loads a deleted module name.
"""
import contextlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(HERE))
import cycle
from _cycle_fixtures import HISTORY, RECORDS, copy, read, tree
from test_cycle_history import LEGACY_MODULES, PROBE

WRITER_COMMANDS = ('create', 'show', 'plan', 'task', 'batch', 'check', 'review-start', 'review', 'finish', 'delivery', 'reopen',
                   'pause', 'resume', 'abandon', 'recover', 'council-subject', 'council')
RETIRED = ('owner-approval', 'validate', 'advance', 'checks', 'coverage', 'completion', 'evidence', 'local-check', 'scrutiny', 'decision',
           'approve-decision', 'return', 'change-type', 'extend', 'reflect', 'query-decisions', 'task-add', 'plan-details',
           'owner-complete', 'shortcut', 'handoff', 'reconcile', 'reduction', 'assignment', 'defer', 'withdraw-decision', 'friction',
           'owner-decision', 'context-read', 'op', 'await')
NO_SUCH_STEP = ('reflect', 'change-type', 'extend')
# Schema-versioned records: the committed typed-engine fixtures of every schema version and cycle type.
LEGACY_FIXTURES = [RECORDS / 'CYC-0001', *[HISTORY / name for name in ('CYC-0015', 'CYC-0063', 'CYC-0069', 'CYC-0094', 'CYC-0101',
                                                                          'CYC-0107', 'CYC-0130', 'CYC-0172')]]
SPEC = {'goal': 'Return the corrected value', 'scope': ['src'], 'acceptance': ['value equals two'],
        'verification': {'checks': [{'id': 'focused', 'rationale': 'value and its caller'}], 'gaps': 'Broader integration runs on the PR'},
        'council': {'needed': False, 'reason': 'Owner agreed on this bounded correction'},
        'tasks': [{'id': 'build', 'description': 'Correct the value', 'owner': 'worker'}]}


def git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


class Base(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.repo = tree(Path(temp.name) / 'repo')
        (self.repo / 'bionic/objectives.md').write_text('Proportional ceremony and durable decisions.\n')
        (self.repo / 'src').mkdir()
        (self.repo / 'src/value.py').write_text('value = 1\n')
        git(self.repo, 'init', '-q')
        git(self.repo, 'config', 'user.email', 'test@example.invalid')
        git(self.repo, 'config', 'user.name', 'Test')
        git(self.repo, 'add', '.')
        git(self.repo, 'commit', '-qm', 'baseline')
        self.plan = Path(temp.name) / 'plan.json'
        self.plan.write_text(json.dumps(SPEC))

    def run_main(self, *argv):
        """Run `cycle.main` in process; return (exit code, parsed first output line)."""
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cycle.main(['--repo-root', str(self.repo), *argv])
        return code, json.loads(out.getvalue().splitlines()[0])

    def probe(self, script, *argv):
        out = self.repo / 'probe.json'
        done = subprocess.run([sys.executable, '-c', PROBE, str(out), str(SCRIPTS / script), '--repo-root', str(self.repo), *argv],
                              capture_output=True, text=True, cwd=self.repo)
        self.assertTrue(out.is_file(), done.stderr)
        report = json.loads(out.read_text())
        return report['code'], done.stdout, sorted(LEGACY_MODULES & set(report['modules']))


class TopLevelWriterTests(Base):
    def test_every_writer_command_and_status_and_queue_parse_at_top_level(self):
        for name in (*WRITER_COMMANDS, 'status', 'queue'):
            with self.subTest(command=name), contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as stop:
                cycle.main([name, '--help'])
            self.assertEqual(stop.exception.code, 0)

    def test_top_level_commands_print_cycle_and_the_pilot_alias_prints_pilot(self):
        code, created = self.run_main('create', '--title', 'Top', '--lead', 'lead', '--plan', str(self.plan))
        self.assertEqual((code, sorted(created)), (0, ['cycle', 'ok']))
        identity = created['cycle']['id']
        code, shown = self.run_main('show', identity)
        self.assertEqual((code, sorted(shown)), (0, ['cycle', 'ok']))
        code, aliased = self.run_main('pilot', 'show', identity)
        self.assertEqual((code, sorted(aliased)), (0, ['ok', 'pilot']))
        self.assertEqual(shown['cycle'], aliased['pilot'])
        self.assertEqual(shown['cycle'], created['cycle'])
        code, full = self.run_main('show', identity, '--full')
        self.assertEqual((code, full['cycle']['id'], full['cycle']['format']), (0, identity, 'crux.cycle.v1'))

    def test_both_routes_write_one_record(self):
        code, created = self.run_main('create', '--title', 'Both', '--lead', 'lead', '--plan', str(self.plan))
        identity, revision = created['cycle']['id'], created['cycle']['revision']
        code, first = self.run_main('task', identity, '--actor', 'lead', '--expect-revision', str(revision), '--task', 'build',
                                    '--owner', 'worker', '--run', '1', '--status', 'working', '--summary', 'started on the top route')
        self.assertEqual(code, 0, first)
        revision = first['cycle']['revision']
        self.assertGreater(revision, created['cycle']['revision'])
        code, second = self.run_main('pilot', 'pause', identity, '--actor', 'lead', '--expect-revision', str(revision), '--reason', 'alias route pause')
        self.assertEqual(code, 0, second)
        record = read(self.repo, identity)
        self.assertEqual((record['state'], record['revision']), ('paused', second['pilot']['revision']))
        self.assertEqual(record['tasks'][0]['summary'], 'started on the top route')
        code, third = self.run_main('resume', identity, '--actor', 'lead', '--expect-revision', str(record['revision']),
                                    '--reason', 'back', '--reconcile', 'git status clean')
        self.assertEqual(code, 0, third)
        self.assertEqual(read(self.repo, identity)['state'], 'working')

    def test_a_stale_revision_is_refused_on_both_routes(self):
        _, created = self.run_main('create', '--title', 'Stale', '--lead', 'lead', '--plan', str(self.plan))
        identity = created['cycle']['id']
        before = (self.repo / 'bionic/cycles' / identity / 'cycle.json').read_bytes()
        for route in ((), ('pilot',)):
            code, refused = self.run_main(*route, 'pause', identity, '--actor', 'lead', '--expect-revision', '99', '--reason', 'stale')
            self.assertEqual((code, refused['ok']), (1, False), route)
        self.assertEqual((self.repo / 'bionic/cycles' / identity / 'cycle.json').read_bytes(), before)

    def test_a_writer_command_on_a_legacy_record_exits_1_and_changes_nothing(self):
        for source in LEGACY_FIXTURES:
            copy(self.repo, source)
            path = self.repo / 'bionic/cycles' / source.name / 'cycle.json'
            before = path.read_bytes()
            for route in ((), ('pilot',)):
                with self.subTest(record=source.name, route=route):
                    code, refused = self.run_main(*route, 'pause', source.name, '--actor', 'lead', '--expect-revision', '1', '--reason', 'try')
                    self.assertEqual((code, refused['ok']), (1, False))
                    self.assertIn('read-only', refused['error'])
                    self.assertIn('legacy typed-engine record', refused['error'])
                    self.assertEqual(path.read_bytes(), before)


class RetiredCommandTests(Base):
    def test_each_retired_command_exits_1_with_command_retired_and_loads_no_legacy_module(self):
        for name in RETIRED:
            with self.subTest(command=name):
                code, out, loaded = self.probe('cycle.py', name, 'CYC-0001', '--whatever', 'x')
                self.assertEqual((code, loaded), (1, []), out)
                lines = out.strip().splitlines()
                self.assertEqual(len(lines), 1, out)
                error = json.loads(lines[0])['error']
                self.assertFalse(json.loads(lines[0])['ok'])
                self.assertEqual((error['code'], error['command']), ('command-retired', name))
                self.assertTrue(error['replacement'] and error['message'], error)
                self.assertNotIn('/Users/', out)
                if name in NO_SUCH_STEP:
                    self.assertIn('no such step', error['replacement'])
                else:
                    self.assertNotIn('no such step', error['replacement'])

    def test_retirement_names_the_writer_command_that_replaces_it(self):
        expected = {'local-check': 'check', 'checks': 'check', 'task-add': 'plan', 'plan-details': 'plan', 'assignment': 'task',
                    'review': None, 'advance': 'review-start', 'owner-decision': 'decision-policy.py', 'approve-decision': 'council',
                    'await': 'native host waiting', 'op': 'task', 'owner-complete': 'finish'}
        for name, word in expected.items():
            if word is None or name not in RETIRED:
                continue
            with self.subTest(command=name):
                code, out, _ = self.probe('cycle.py', name)
                self.assertEqual(code, 1)
                self.assertIn(word, json.loads(out)['error']['replacement'])

    def test_retirement_messages_name_the_live_decision_routes(self):
        expected = {
            'owner-approval': ('plan --owner-approval',),
            'decision': ('decision-policy.py propose and accept', 'council-subject and council'),
            'approve-decision': ('decision-policy.py propose and accept', 'council IDENTITY --record'),
            'owner-decision': ('decision-policy.py owner-decision present, capture and apply', 'council-subject and council',
                               'plan --owner-approval'),
        }
        for name, phrases in expected.items():
            with self.subTest(command=name):
                for phrase in phrases:
                    self.assertIn(phrase, cycle.RETIRED[name])
        for name in ('owner-approval', 'decision', 'approve-decision', 'owner-decision', 'query-decisions', 'withdraw-decision'):
            with self.subTest(command=name, check='no retired route'):
                text = cycle.RETIRED[name]
                self.assertNotIn('records an owner decision', text)
                self.assertNotIn('decision-policy.py reads', text)
                self.assertNotIn('decision-policy.py proposes and records', text)

    def test_every_decision_policy_subcommand_a_retirement_message_names_exists(self):
        """Each `decision-policy.py` route a retired-command message names is a real subcommand: its --help exits 0.

        Passes once the lr-decisions unit adds `owner-decision present|capture|apply` to decision-policy.py."""
        pattern = re.compile(r'decision-policy\.py ((?:owner-decision )?[a-z]+(?:-[a-z]+)*(?:(?:, | and )[a-z]+(?:-[a-z]+)*)*)')
        script = SCRIPTS / 'decision-policy.py'
        routes = set()
        for name, text in cycle.RETIRED.items():
            for found in pattern.findall(text):
                prefix = ['owner-decision'] if found.startswith('owner-decision ') else []
                words = re.split(r', | and ', found.removeprefix('owner-decision '))
                routes.update(tuple(prefix + [word]) for word in words)
        self.assertTrue({('propose',), ('accept',), ('owner-decision', 'present'), ('owner-decision', 'capture'),
                         ('owner-decision', 'apply')} <= routes, routes)
        for route in sorted(routes):
            with self.subTest(route=' '.join(route)):
                done = subprocess.run([sys.executable, str(script), *route, '--help'], capture_output=True, text=True)
                self.assertEqual(done.returncode, 0, done.stderr)

    def test_a_retired_command_naming_a_legacy_record_adds_the_read_only_note(self):
        for source in LEGACY_FIXTURES[:3]:
            copy(self.repo, source)
        code, out, loaded = self.probe('cycle.py', 'advance', 'CYC-0001')
        error = json.loads(out)['error']
        self.assertEqual((code, loaded), (1, []))
        for phrase in ('legacy typed-engine record', 'read-only', 'cycle.py show', 'status', 'nothing changed'):
            self.assertIn(phrase, error['message'], phrase)
        code, out, _ = self.probe('cycle.py', 'advance', 'CYC-9999')
        self.assertNotIn('legacy typed-engine record', json.loads(out)['error']['message'])

    def test_retirement_is_detected_before_argument_parsing(self):
        code, out, loaded = self.probe('cycle.py', '--compact', 'local-check', '--no-such-flag', '--check-id')
        self.assertEqual((code, loaded, json.loads(out)['error']['code']), (1, [], 'command-retired'))

    def test_retired_commands_are_not_rejected_in_process_either(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cycle.main(['--repo-root', str(self.repo), 'task-add', 'CYC-0001', '--json', '{}'])
        self.assertEqual((code, json.loads(out.getvalue())['error']['code']), (1, 'command-retired'))

    def test_the_probe_sees_a_deleted_module_load(self):
        """Positive control: a script that loads a deleted typed-engine module name is reported by the same probe."""
        plant = self.repo / 'plant.py'
        plant.write_text('import sys, types\nsys.modules["cycle_ops"] = types.ModuleType("cycle_ops")\n')
        code, out, loaded = self.probe(str(plant))
        self.assertEqual((code, loaded), (0, ['cycle_ops']), out)


class PilotRouteImportTests(Base):
    def test_the_pilot_route_and_top_level_create_load_no_legacy_module(self):
        for route in ((), ('pilot',)):
            with self.subTest(route=route):
                code, out, loaded = self.probe('cycle.py', *route, 'create', '--title', 'Probe', '--lead', 'lead', '--plan', str(self.plan))
                self.assertEqual((code, loaded), (0, []), out)
                identity = json.loads(out)['pilot' if route else 'cycle']['id']
                code, out, loaded = self.probe('cycle.py', *route, 'show', identity)
                self.assertEqual((code, loaded), (0, []), out)

    def test_cycle_module_imports_no_typed_engine_module(self):
        done = subprocess.run([sys.executable, '-c', 'import sys, json; sys.path.insert(0, sys.argv[1]); import cycle; print(json.dumps(sorted(sys.modules)))', str(SCRIPTS)],
                              capture_output=True, text=True)
        self.assertEqual(sorted(LEGACY_MODULES & set(json.loads(done.stdout))), [], done.stderr)


class LegacyShowTests(Base):
    def test_show_renders_each_legacy_record_through_cycle_history_and_loads_no_legacy_module(self):
        for source in LEGACY_FIXTURES:
            copy(self.repo, source)
            raw = json.loads((source / 'cycle.json').read_text())
            self.assertIn('schema_version', raw)
            path = self.repo / 'bionic/cycles' / source.name / 'cycle.json'
            before = path.read_bytes()
            with self.subTest(record=source.name):
                code, out, loaded = self.probe('cycle.py', 'show', source.name)
                self.assertEqual((code, loaded), (0, []), out)
                payload = json.loads(out)
                self.assertEqual((payload['ok'], payload['legacy']), (True, True))
                self.assertEqual((payload['cycle']['id'], payload['cycle']['schema_version'], payload['cycle']['status']),
                                 (raw['id'], raw['schema_version'], raw['status']))
                self.assertEqual(path.read_bytes(), before)
                code, out, loaded = self.probe('cycle.py', 'show', source.name, '--full')
                self.assertEqual((code, loaded), (0, []), out)
                self.assertEqual(json.loads(out), {'ok': True, 'legacy': True, 'cycle': raw})

    def test_show_of_a_missing_record_exits_1(self):
        code, out, loaded = self.probe('cycle.py', 'show', 'CYC-0042')
        self.assertEqual((code, loaded, json.loads(out)['ok']), (1, [], False))

    def test_show_renders_a_vnext_writer_record(self):
        copy(self.repo, HISTORY / 'CYC-0168')
        code, payload = self.run_main('show', 'CYC-0168')
        self.assertEqual((code, payload['ok']), (0, True))
        self.assertNotIn('legacy', payload)
        self.assertEqual(payload['cycle']['id'], 'CYC-0168')


class KeptHelperTests(unittest.TestCase):
    def test_read_json_arg_and_status_stay_in_cycle(self):
        self.assertEqual(cycle.read_json_arg('.', '{"a": 1}'), '{"a": 1}')
        self.assertTrue(callable(cycle.status) and callable(cycle.main))


if __name__ == '__main__':
    unittest.main()
