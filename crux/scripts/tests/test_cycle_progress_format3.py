"""Reader format 5: open assignments, the classification count, exception, revision and the unchanged rendering of older records."""
import ast
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle_ops
import cycle_progress
from cycle_progress import view, render
from cycle_workflow import create, validate
from _dev_surface import REPO_ROOT, TREE, require_dev_surface

HERE = Path(__file__).resolve().parent
FROZEN = HERE / 'fixtures/cycle_progress_format2.py'
RECORDS = HERE / 'fixtures/cycle-records'
NOW = 1_900_000_000


def frozen_module():
    """The format-2 reader, frozen verbatim at the base commit."""
    spec = importlib.util.spec_from_file_location('cycle_progress_format2', FROZEN)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def tree(root):
    (root / 'bionic').mkdir(parents=True, exist_ok=True)
    (root / 'bionic/manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\n')
    return root


def assignment(id='a-1', state='running', host='claude-code', attempt=1, task='t-1', role='developer', mode=None):
    return {**({'mode': mode} if mode else {}), 'id': id, 'role': role, 'task': task, 'agent': None, 'result_path': None, 'state': state, 'attempt': attempt,
            'started_at': '2026-01-01T00:00:00+00:00', 'last_seen': '2026-01-01T00:00:00+00:00', 'ended_at': None, 'note': None,
            'host': host, 'base': None, 'delivery': None}


class Format3Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = tree(Path(self.temp.name))
        (self.root / 'src').mkdir()

    def record(self, version=3, assignments=(), **extra):
        doc = create(self.root, 'quick-fix', 'Fix', 'Goal', ['src'], ['passes'], 'builder', 'tester')
        path = self.root / 'bionic/cycles' / doc['id'] / 'cycle.json'
        raw = json.loads(path.read_text())
        if version == 3:
            raw.update(schema_version=3, **cycle_ops.v3_fields())
            raw['revision'] = 1  # a saved version-3 record has revision >= 1 (the schema's minimum)
            raw['assignments'] = [dict(a) for a in assignments]
        else:
            # create writes version 3; step back to the older shape.
            for key in cycle_ops.v3_fields():
                raw.pop(key, None)
            raw['schema_version'] = 2
            raw['assignments'] = [{k: v for k, v in dict(a).items() if k not in cycle_ops.ASSIGNMENT_V3_FIELDS} for a in assignments]
            if version == 1:
                raw.pop('coverage', None)
                raw.pop('completion', None)
                raw['schema_version'] = 1
        classifications = extra.pop('classifications', None)
        raw.update(extra)
        validate(raw)
        if classifications is not None:
            raw['classifications'] = classifications  # stream B has not put this key in the schema yet
        path.write_text(json.dumps(raw))
        return doc['id']

    def cycle(self, cid):
        return view(self.root, cid, now=NOW)['cycles'][0]

    def test_document_carries_format_3_and_the_module_constants(self):
        self.assertEqual(view(self.root, now=NOW)['format_version'], 5)
        parsed = ast.parse(Path(cycle_progress.__file__).read_text())
        names = {t.targets[0].id: ast.literal_eval(t.value) for t in parsed.body
                 if isinstance(t, ast.Assign) and isinstance(t.targets[0], ast.Name) and isinstance(t.value, (ast.Constant, ast.List))}
        self.assertEqual(names['FORMAT_VERSION'], 5)
        self.assertNotIn('MAX_CLASSIFICATIONS', names)  # the count is never capped
        self.assertEqual(names['OBSERVATIONS'], ['reserved-unbound', 'running-bound'])
        self.assertEqual(names['LIVENESS'], ['unknown'])
        self.assertEqual(names['ASSIGNMENT_STATES'], ['reserved', 'running'])

    def test_keys_for_version_1_2_and_3(self):
        for version in (1, 2, 3):
            with self.subTest(version=version):
                c = self.cycle(self.record(version))
                self.assertEqual(c['schema_version'], version)
                self.assertEqual(c['revision'], 1 if version == 3 else None)
                self.assertEqual((c['assignments'], c['classification_count'], c['exception']), ([], 0, None))

    def test_only_open_attempts_appear_with_unknown_liveness_and_unresolved_dispatch(self):
        rows = [assignment('r-claude', 'reserved', 'claude-code', mode='background'), assignment('r-null', 'reserved', None, attempt=2),
                assignment('run', 'running', 'claude-code'), assignment('fin', 'finished'), assignment('lost', 'lost')]
        c = self.cycle(self.record(3, rows))
        self.assertEqual([a['id'] for a in c['assignments']], ['r-claude', 'r-null', 'run'])
        self.assertEqual(c['assignments'][0], {'id': 'r-claude', 'task': 't-1', 'role': 'developer', 'host': 'claude-code', 'attempt': 1,
                                               'state': 'reserved', 'observation': 'reserved-unbound', 'liveness': 'unknown', 'unresolved': True})
        self.assertEqual((c['assignments'][1]['host'], c['assignments'][1]['unresolved']), (None, True))
        self.assertEqual((c['assignments'][2]['observation'], c['assignments'][2]['unresolved']), ('running-bound', False))
        self.assertEqual({a['liveness'] for a in c['assignments']}, {'unknown'})

    def test_a_handle_less_host_reservation_is_not_unresolved(self):
        import cycle_hosts
        from unittest import mock
        quiet = cycle_hosts.Adapter(name='quiet', modes={'m': cycle_hosts.Mode(name='m', tool='x', background=False, handle_source=None)}, default_mode='m')
        with mock.patch.dict(cycle_hosts.ADAPTERS, {'quiet': quiet}):
            c = self.cycle(self.record(3, [assignment('r', 'reserved', 'quiet')]))
        self.assertFalse(c['assignments'][0]['unresolved'])

    def test_a_blocking_reservation_is_not_unresolved_and_a_background_one_is(self):
        rows = [assignment('blocking', 'reserved', 'claude-code', mode='blocking'),
                assignment('background', 'reserved', 'claude-code', attempt=2, mode='background'),
                assignment('foreground', 'reserved', 'opencode', attempt=3, mode='foreground'),
                assignment('oc-background', 'reserved', 'opencode', attempt=4, mode='background')]
        c = self.cycle(self.record(3, rows))
        self.assertEqual([a['unresolved'] for a in c['assignments']], [False, True, False, True])

    def test_an_unknown_host_counts_as_returning_a_handle(self):
        c = self.cycle(self.record(3, [assignment('r', 'reserved', 'no-such-host')]))
        self.assertTrue(c['assignments'][0]['unresolved'])

    def test_version_2_open_attempt_has_a_null_host(self):
        c = self.cycle(self.record(2, [assignment('r', 'running')]))
        self.assertEqual((c['assignments'][0]['host'], c['assignments'][0]['state']), (None, 'running'))

    def test_assignments_are_capped_at_fifty(self):
        c = self.cycle(self.record(3, [assignment(f'a-{n}', 'running') for n in range(60)]))
        self.assertEqual(len(c['assignments']), 50)

    def test_classifications_reduce_to_their_true_count(self):
        entries = [{'kind': 'work-sizing', 'route': 'dev-lead', 'fallback': None}, 'text', {'kind': 'nonsense', 'route': 'x', 'fallback': None},
                   {'kind': 'review-routing', 'route': 7, 'fallback': None}, {'kind': 'failure-routing', 'route': None, 'fallback': 'no host'},
                   {'kind': 'finding-disposition', 'route': 'fix', 'fallback': 3}]
        c = self.cycle(self.record(3, classifications=entries))
        # The count is the rows inspect lists: every entry that is an object of a known kind.
        self.assertEqual(c['classification_count'], 4)
        self.assertNotIn('classifications', c)
        many = [{'kind': 'work-sizing', 'route': f'r{n}', 'fallback': None} for n in range(25)]
        cid = self.record(3, classifications=many)
        self.assertEqual(self.cycle(cid)['classification_count'], 25)  # not capped
        text = render(view(self.root, cid, now=NOW)).splitlines()
        self.assertIn('  Classifications: 25', text)
        self.assertFalse([l for l in text if l.startswith('  Classification ') or 'r24' in l], text)

    def test_a_malformed_classifications_value_is_not_fatal(self):
        raw_id = self.record(3)
        path = self.root / 'bionic/cycles' / raw_id / 'cycle.json'
        raw = json.loads(path.read_text())
        raw['classifications'] = 'bad'
        path.write_text(json.dumps(raw))
        self.assertEqual(self.cycle(raw_id)['classification_count'], 0)

    def test_exception_text(self):
        done = {'commits': None, 'exception': 'owner\x07 waived', 'remaining': 'none', 'input_sha256': '0' * 64}
        self.assertEqual(self.cycle(self.record(3, completion=done))['exception'], 'owner waived')
        self.assertIsNone(self.cycle(self.record(3, completion={**done, 'exception': ''}))['exception'])
        self.assertIsNone(self.cycle(self.record(3, completion={**done, 'exception': None}))['exception'])
        self.assertIsNone(self.cycle(self.record(3, completion=None))['exception'])
        long = {**done, 'exception': 'x' * 500}
        self.assertEqual(len(self.cycle(self.record(3, completion=long))['exception']), 300)

    def test_text_lines_appear_only_with_data(self):
        rows = [assignment('r', 'reserved', 'claude-code', task='t-9', role='developer', mode='background'), assignment('u', 'running', 'claude-code', attempt=2, task=None)]
        done = {'commits': None, 'exception': 'owner waived', 'remaining': 'none', 'input_sha256': '0' * 64}
        cls = [{'kind': 'work-sizing', 'route': 'dev-lead', 'fallback': None}, {'kind': 'review-routing', 'route': None, 'fallback': 'no reviewer'}]
        cid = self.record(3, rows, classifications=cls, completion=done)
        text = render(view(self.root, cid, now=NOW)).splitlines()
        self.assertIn('Pass 1 of 1 · Build · active · revision 1', text)
        # Neither attempt names a listed task, so both sit under the Attempts label.
        self.assertIn('  Attempts', text)
        for head in ('    Attempt 1 · r · task t-9 · developer · reserved, unresolved dispatch · liveness unknown · last activity ',
                     '    Attempt 2 · u · developer · running · liveness unknown · last activity '):
            self.assertTrue(any(l.startswith(head) for l in text), (head, text))
        self.assertIn('  Classifications: 2', text)
        for detail in ('Classification work-sizing', 'dev-lead', 'no reviewer', 'Choose the cycle type'):
            self.assertFalse([l for l in text if detail in l], (detail, text))
        self.assertIn('  Owner exception: owner waived', text)

    def test_a_closed_cycle_with_open_attempts_draws_no_assignment_lines(self):
        cid = self.record(3, [assignment('r', 'reserved')], status='completed')
        self.assertEqual(len(self.cycle(cid)['assignments']), 1)
        self.assertNotIn('Attempt', render(view(self.root, cid, now=NOW)))

    def test_version_2_draws_no_revision(self):
        self.assertNotIn('revision', render(view(self.root, self.record(2), now=NOW)))


class StatusErrorDocumentTests(unittest.TestCase):
    def test_status_json_error_names_the_current_reader_format(self):
        import subprocess
        with tempfile.TemporaryDirectory() as temp:
            root = tree(Path(temp))
            run = subprocess.run([sys.executable, str(HERE.parent / 'cycle.py'), '--repo-root', str(root), 'status', 'CYC-9999', '--json'],
                                 capture_output=True, text=True)
        self.assertEqual(run.returncode, 1, run.stderr)
        document = json.loads(run.stdout)
        self.assertEqual((document['ok'], document['format_version']), (False, cycle_progress.FORMAT_VERSION))


# Lines the current reader adds to a format-2 rendering: the section labels (one line each, exact), the
# activity line of an open cycle, and the attempt lines (nested under a task or under the Attempts label).
LABELS = ('  Tasks', '  Attempts', '  Councils')
ADDED_PREFIXES = ('  Attempt ', '    Attempt ', '      Attempt ', '  Activity: ', '  Classifications: ')


def strip_added(lines, live):
    prefixes = ADDED_PREFIXES + (('  Owner exception: ',) if live else ())
    return [line for line in lines if line not in LABELS and not line.startswith(prefixes)]


class RenderUnchangedTests(unittest.TestCase):
    """Every committed record renders as before; a cycle only gains its section labels, and an open one its activity and Attempt lines."""

    def setUp(self):
        # An open fixture cycle tallies the evidence store's receipts. A shared store named by the environment
        # (the release path and the main run name one) holds real receipts, so the fixtures would render a Test runs line.
        patcher = mock.patch.dict(os.environ)
        patcher.start()
        self.addCleanup(patcher.stop)
        for name in ('CRUX_TEST_EVIDENCE_STORE', 'CRUX_TEST_EVIDENCE_DURABLE_ONLY'):
            os.environ.pop(name, None)

    def isolate(self, temp, sources):
        root = tree(Path(temp))
        for src in sources:
            (root / 'bionic/cycles' / src.name).mkdir(parents=True)
            shutil.copy(src / 'cycle.json', root / 'bionic/cycles' / src.name / 'cycle.json')
        return root

    def compare(self, sources, live=False):
        old = frozen_module()
        with tempfile.TemporaryDirectory() as temp:
            root = self.isolate(temp, sources)
            before, after = old.view(root, now=NOW), view(root, now=NOW)
            self.assertEqual(len(before['cycles']), len(after['cycles']))
            for b, a in zip(before['cycles'], after['cycles']):
                for key, value in b.items():
                    self.assertEqual(a[key], value, (b['id'], key))
            self.assertEqual((before['format_version'], after['format_version']), (2, 5))
            for key in before:
                if key not in ('format_version', 'cycles'):
                    self.assertEqual(after[key], before[key])
            new_text = render(after).splitlines()
            # The frozen fixtures strip the labels, activity and attempt lines. The live tree also strips the
            # line a later record may add: the owner exception a closed record may carry.
            stripped = strip_added(new_text, live)
            self.assertEqual('\n'.join(stripped), old.render(before))
            open_cycles = [c for c in after['cycles'] if c['status'] in ('active', 'paused')]
            open_attempts = sum(len(c['assignments']) for c in open_cycles)
            labels = sum(bool(c['tasks']) + bool(c['classification_count']) for c in after['cycles'])
            labels += sum(any(a['task'] not in {t['id'] for t in c['tasks']} for a in c['assignments']) for c in open_cycles)
            added = open_attempts + labels + len(open_cycles)
            if live:
                added += sum(c['exception'] is not None for c in after['cycles'])
            self.assertEqual(len(new_text) - len(stripped), added)
            return len(after['cycles']), open_attempts

    def test_fixture_records_render_unchanged(self):
        count, extra = self.compare(sorted(p.parent for p in RECORDS.glob('*/cycle.json')))
        self.assertGreaterEqual(count, 4)
        self.assertEqual(extra, 0)

    def test_every_committed_cycle_record_renders_unchanged(self):
        directory = REPO_ROOT / TREE / 'cycles'
        require_dev_surface(self, directory, 'the committed cycle records')
        # Version-3 records are the new format and have no frozen rendering to equal.
        sources = sorted(p.parent for p in directory.glob('CYC-*/cycle.json')
                         if json.loads(p.read_text(encoding='utf-8')).get('schema_version') != 3)
        # The reader lists at most 60 cycles, so compare in batches of 60.
        results = [self.compare(sources[n:n + 60], live=True) for n in range(0, len(sources), 60)]
        self.assertEqual(sum(r[0] for r in results), len(sources))
        self.assertGreaterEqual(len(sources), 80)

    def test_positive_control_the_live_comparison_catches_a_reworded_line(self):
        sources = sorted(p.parent for p in RECORDS.glob('*/cycle.json'))[:1]
        with tempfile.TemporaryDirectory() as temp:
            root = self.isolate(temp, sources)
            text = render(view(root, now=NOW)).replace('Elapsed', 'Duration')
            lines = strip_added(text.splitlines(), live=True)
            self.assertNotEqual('\n'.join(lines), frozen_module().render(frozen_module().view(root, now=NOW)))

    def test_live_comparison_strips_an_owner_exception_the_frozen_one_does_not(self):
        with tempfile.TemporaryDirectory() as temp:
            root = tree(Path(temp))
            record = json.loads((RECORDS / 'CYC-0003/cycle.json').read_text(encoding='utf-8'))
            self.assertEqual(record['schema_version'], 2)
            record['completion']['exception'] = 'owner waived'
            (root / 'bionic/cycles/CYC-0003').mkdir(parents=True)
            (root / 'bionic/cycles/CYC-0003/cycle.json').write_text(json.dumps(record), encoding='utf-8')
            sources = [root / 'bionic/cycles/CYC-0003']
            self.assertEqual(self.compare(sources, live=True)[0], 1)
            with self.assertRaises(AssertionError):
                self.compare(sources)

    def test_positive_control_a_reworded_line_fails_the_comparison(self):
        sources = sorted(p.parent for p in RECORDS.glob('*/cycle.json'))[:1]
        with tempfile.TemporaryDirectory() as temp:
            root = self.isolate(temp, sources)
            text = render(view(root, now=NOW)).replace('Elapsed', 'Duration')
            self.assertNotEqual(text, frozen_module().render(frozen_module().view(root, now=NOW)))


if __name__ == '__main__':
    unittest.main()
