"""The read path without the typed engine: cycle_store's moved primitives and cycle_history's legacy reader.

`cycle.py status`, `visualize-cycle-progress.py` and `cycle.py queue list`/`show` render frozen legacy
records of schema versions 1, 2 and 3 (release cycles of every list included), an open legacy record
with attempts, classifications and council rounds, and a frozen lightweight (vNext) record. A
subprocess shows by sys.modules inspection that no typed-engine module loaded while they did; a
positive control shows the same probe seeing the typed engine load.
"""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(HERE))
import cycle_history
import cycle_store
from _dev_surface import REPO_ROOT, TREE, require_dev_surface
from _cycle_fixtures import HISTORY, RECORDS, fresh, put

LEGACY = HERE / 'fixtures/cycle-records/CYC-0001/cycle.json'
VNEXT = HERE / 'fixtures/cycle-history/CYC-0168/cycle.json'
# Frozen committed records, one folder each: (schema version, type, release list) they stand for.
FROZEN = {
    'CYC-0001': (1, 'iterate', None), 'CYC-0003': (2, 'iterate', None), 'CYC-0015': (2, 'release', None),
    'CYC-0063': (2, 'release', 'official'), 'CYC-0069': (2, 'release', 'beta'), 'CYC-0094': (3, 'release', 'beta'),
    'CYC-0101': (3, 'release', 'beta'), 'CYC-0107': (3, 'release', 'official'), 'CYC-0130': (3, 'iterate', None),
    'CYC-0172': (3, 'quick-fix', None),
}
OPEN = 'CYC-0200'
# The cycle object keys the dashboards accept, exactly (crux-mods/hooks/lib/view.ts cycleObject).
DASHBOARD_KEYS = {'id', 'schema_version', 'revision', 'assignments', 'classification_count', 'exception', 'title', 'type',
                  'status', 'phase', 'pass', 'pass_limit', 'phases', 'tasks', 'returns', 'waits', 'blocker', 'reflection',
                  'modified_s', 'started_s', 'ended_s', 'paused_s', 'open_started_s', 'basis', 'phase_times'}


def frozen_source(ident):
    return (RECORDS if (RECORDS / ident).is_dir() else HISTORY) / ident


def open_record(root):
    """An open version-3 record with open attempts, classifications and one council round, built as JSON."""
    doc = fresh('quick-fix')
    doc['assignments'] = [
        {'id': 'build', 'role': 'dev-lead', 'task': None, 'agent': None, 'result_path': None, 'state': 'reserved', 'attempt': 1, 'mode': 'background',
         'started_at': doc['created_at'], 'last_seen': doc['created_at'], 'ended_at': None, 'note': None, 'host': 'claude-code', 'base': None, 'delivery': None},
        {'id': 'build', 'role': 'dev-lead', 'task': None, 'agent': None, 'result_path': None, 'state': 'finished', 'attempt': 0,
         'started_at': doc['created_at'], 'last_seen': doc['created_at'], 'ended_at': None, 'note': None, 'host': 'codex', 'base': None, 'delivery': None}]
    doc['classifications'] = [{'kind': 'work-sizing', 'route': 'iterate', 'fallback': None}, {'kind': 'no-such-kind'}]
    cid = put(root, {**doc, 'title': 'Open legacy cycle'}, OPEN)
    council = root / 'bionic/cycles' / cid / 'councils/decisions/abc'
    council.mkdir(parents=True)
    (council / 'attempt-1.json').write_text(json.dumps({'logical_id': f'idr:{cid}:plan-x', 'id': 'attempt-1', 'round': 1,
                                                        'started_at': '2026-11-01T00:00:00+00:00', 'status': 'finished',
                                                        'record': f'cycles/{cid}/councils/decisions/abc/record.json'}))
    (council / 'record.json').write_text(json.dumps({'outcome': 'approved', 'seats': []}))
    return cid
# The typed engine's modules, which the cutover deletes. None may load on a read-only view.
LEGACY_MODULES = frozenset({
    'cycle_workflow', 'cycle_ops', 'cycle_execution', 'cycle_dispatch', 'cycle_reconcile', 'cycle_commit',
    'cycle_context', 'cycle_context_read', 'cycle_hosts', 'cycle_classify', 'cycle_questions',
    'cycle_doc_classify', 'cycle_prereqs', 'cycle_activity', 'cycle_summary', 'cycle_timing',
    'cycle_worktrees', 'cycle_local_skills',
})
# Runs one script as __main__ in a fresh interpreter, then writes the loaded module names to argv[1].
PROBE = '''
import json, runpy, sys
out, script, *argv = sys.argv[1:]
sys.path.insert(0, str(__import__("pathlib").Path(script).parent))
sys.argv = [script, *argv]
code = 0
try:
    runpy.run_path(script, run_name="__main__")
except SystemExit as exc:
    code = exc.code
open(out, "w").write(json.dumps({"code": code, "modules": sorted(sys.modules)}))
'''


def tree(root):
    (root / 'bionic/cycles').mkdir(parents=True)
    (root / 'bionic/manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\n')
    for source in [frozen_source(i) for i in FROZEN] + [VNEXT.parent]:
        shutil.copytree(source, root / 'bionic/cycles' / source.name)
    open_record(root)
    return root


def queue(root):
    """A queue whose two started items name a closed and an open legacy cycle, and one pending item."""
    import cycle_queue
    from bionic_config import load_config
    (root / 'bionic/objectives.md').write_text('Mission: useful changes.')
    for title in ('Closed', 'Open', 'Next'):
        cycle_queue.add(root, title, 'Outcome', 'iterate', ['src'], ['ok'])
    path = root / 'bionic/queue/cycles.yaml'
    doc = cycle_queue.parse_queue(path.read_text())
    doc['items'][0].update(state='started', cycle='CYC-0172', started_at='2026-01-01T00:00:00+00:00', start_token='a' * 32)
    doc['items'][1].update(state='started', cycle=OPEN, started_at='2026-01-01T00:00:00+00:00', start_token='b' * 32)
    cycle_queue.write_queue(load_config(root, require_tree=True), doc)


class ReadPathTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = tree(Path(temp.name))

    def probe(self, script, *argv):
        out = self.root / 'probe.json'
        done = subprocess.run([sys.executable, '-c', PROBE, str(out), str(SCRIPTS / script), *argv],
                              capture_output=True, text=True, cwd=self.root)
        self.assertTrue(out.is_file(), done.stderr)
        report = json.loads(out.read_text())
        return report['code'], done.stdout, sorted(LEGACY_MODULES & set(report['modules'])), report['modules']

    def test_status_renders_each_record_without_legacy_modules(self):
        titles = {i: json.loads((frozen_source(i) / 'cycle.json').read_text())['title'] for i in FROZEN}
        titles.update({'CYC-0168': json.loads(VNEXT.read_text())['title'], OPEN: 'Open legacy cycle'})
        for ident, title in titles.items():
            for extra in ((), ('--json',)):
                with self.subTest(ident=ident, extra=extra):
                    code, out, loaded, modules = self.probe('cycle.py', '--repo-root', str(self.root), 'status', ident, *extra)
                    self.assertEqual(code, 0, out)
                    self.assertIn(title[:40], out)
                    self.assertIn('cycle_progress', modules)  # the probe saw the renderer load
                    self.assertEqual(loaded, [])

    def test_status_routes_each_format_to_its_reader(self):
        code, out, loaded, modules = self.probe('cycle.py', '--repo-root', str(self.root), 'status', '--json')
        self.assertEqual((code, loaded), (0, []))
        document = json.loads(out)
        self.assertEqual((document['format'], document['format_version']), ('crux.cycle-progress', 5))
        rows = {c['id']: c for c in document['cycles']}
        for ident, (version, kind, listed) in FROZEN.items():
            with self.subTest(ident=ident):
                self.assertEqual((rows[ident]['schema_version'], rows[ident]['type']), (version, kind))
                self.assertEqual(set(rows[ident]), DASHBOARD_KEYS)  # the dashboards' format, unchanged
                if kind == 'release':
                    self.assertEqual(rows[ident]['phases'], ['release'] if listed else ['plan', 'release', 'reflect'])
        self.assertEqual(rows['CYC-0168']['type'], 'pilot')
        self.assertIn('cycle_history', modules)
        self.assertIn('cycle_writer', modules)

    def test_an_open_legacy_record_shows_attempts_classifications_and_councils_from_its_bytes(self):
        code, out, loaded, _ = self.probe('cycle.py', '--repo-root', str(self.root), 'status', OPEN, '--json')
        self.assertEqual((code, loaded), (0, []))
        row = json.loads(out)['cycles'][0]
        self.assertEqual(set(row), DASHBOARD_KEYS)
        self.assertEqual([(a['host'], a['state'], a['unresolved'], a['liveness']) for a in row['assignments']],
                         [('claude-code', 'reserved', True, 'unknown')])
        self.assertEqual(row['classification_count'], 1)
        code, text, loaded, _ = self.probe('cycle.py', '--repo-root', str(self.root), 'status', OPEN)
        self.assertEqual((code, loaded), (0, []))
        self.assertIn('    Attempt 1 · build · dev-lead · reserved, unresolved dispatch · liveness unknown', text.splitlines())
        self.assertIn('  Council plan-x round 1 · attempt- · approved · initial', text.splitlines())
        self.assertIn('  Classifications: 1', text.splitlines())
        self.assertNotIn('Activity', text)

    def test_a_release_cycle_of_each_list_renders_its_one_phase_or_its_legacy_phases(self):
        code, text, loaded, _ = self.probe('cycle.py', '--repo-root', str(self.root), 'status')
        self.assertEqual((code, loaded), (0, []))
        lines = text.splitlines()
        for ident in ('CYC-0063', 'CYC-0069', 'CYC-0094', 'CYC-0107'):
            title = json.loads((frozen_source(ident) / 'cycle.json').read_text())['title']
            at = lines.index(f'{ident} {title} [release]')
            self.assertEqual(lines[at + 1].split(' · revision ')[0], 'Release · completed')  # a version-3 record adds its revision
            self.assertEqual(lines[at + 2], 'Release')
        at = lines.index('CYC-0101 ' + json.loads((HISTORY / 'CYC-0101/cycle.json').read_text())['title'] + ' [release]')
        self.assertTrue(lines[at + 1].startswith('Release · abandoned'), lines[at + 1])
        at = lines.index('CYC-0015 ' + json.loads((HISTORY / 'CYC-0015/cycle.json').read_text())['title'] + ' [release]')
        self.assertEqual(lines[at + 1:at + 3], ['Pass 1 of 2 · Reflect · completed', 'Plan → Release → Reflect'])
        # A closed record shows its recorded test runs from its own bytes.
        at = lines.index('CYC-0094 ' + json.loads((HISTORY / 'CYC-0094/cycle.json').read_text())['title'] + ' [release]')
        self.assertTrue(lines[at + 4].startswith('  Test runs: '), lines[at:at + 6])

    def test_queue_list_and_show_read_legacy_cycles_without_legacy_modules(self):
        queue(self.root)
        code, out, loaded, modules = self.probe('cycle.py', '--repo-root', str(self.root), 'queue', 'list', '--full')
        self.assertEqual((code, loaded), (0, []), out)
        self.assertIn('cycle_history', modules)
        items = json.loads(out)['items']
        self.assertEqual([i['cycle_status'] for i in items], ['completed', 'active', None])
        # The list rows leave the per-item history facts to `queue show`.
        self.assertEqual([i for i in items if 'history' in i], [])
        code, out, loaded, _ = self.probe('cycle.py', '--repo-root', str(self.root), 'queue', 'show', 'Q-0001')
        self.assertEqual((code, loaded), (0, []), out)
        shown = json.loads(out)['item']['history']
        self.assertEqual(shown['review'], {'path': 'cycles/CYC-0172/reviews/804088187f8140e4aaa5b22637a7dc76.json', 'verdict': 'approve', 'count': 1})
        self.assertEqual(shown['completion']['remaining'],
                         json.loads((HISTORY / 'CYC-0172/cycle.json').read_text())['completion']['remaining'])
        code, out, loaded, _ = self.probe('cycle.py', '--repo-root', str(self.root), 'queue', 'show', 'Q-0002')
        self.assertEqual((code, loaded), (0, []), out)
        self.assertEqual(json.loads(out)['item']['history']['status'], 'active')
        code, out, loaded, _ = self.probe('cycle.py', '--repo-root', str(self.root), 'queue', 'show', 'Q-0003')
        self.assertEqual((code, loaded), (0, []), out)
        self.assertNotIn('history', json.loads(out)['item'])
        code, out, loaded, _ = self.probe('cycle.py', '--repo-root', str(self.root), '--compact', 'queue', 'list')
        self.assertEqual((code, loaded), (0, []), out)
        self.assertEqual(json.loads(out)['closed'], 1)  # the completed legacy cycle's item is closed

    def test_an_unreadable_legacy_record_is_named_and_the_listing_continues(self):
        for ident, text in (('CYC-0300', '{"schema_version": 3, "id": "CYC-03'), ('CYC-0301', json.dumps({**fresh('quick-fix'), 'id': 'CYC-0301', 'schema_version': 9}))):
            (self.root / 'bionic/cycles' / ident).mkdir()
            (self.root / 'bionic/cycles' / ident / 'cycle.json').write_text(text)
        code, out, loaded, _ = self.probe('cycle.py', '--repo-root', str(self.root), 'status', '--json')
        self.assertEqual((code, loaded), (0, []))
        rows = {c['id']: c for c in json.loads(out)['cycles']}
        for ident in ('CYC-0300', 'CYC-0301'):
            self.assertEqual((rows[ident]['title'], rows[ident]['status']), ('Unreadable cycle record', 'paused'))
            self.assertIn('cannot be read', rows[ident]['blocker'])
        self.assertIn('unknown legacy schema_version', rows['CYC-0301']['blocker'])
        self.assertTrue(set(FROZEN) <= set(rows))  # the other cycles still render
        for ident in ('CYC-0300', 'CYC-0301'):
            code, _, _, _ = self.probe('cycle.py', '--repo-root', str(self.root), 'status', ident, '--json')
            self.assertEqual(code, 1)  # an explicit request for the record fails

    def test_visualizer_renders_without_legacy_modules(self):
        code, out, loaded, _ = self.probe('visualize-cycle-progress.py', '--project-root', str(self.root), '--json')
        self.assertEqual((code, loaded), (0, []))
        self.assertEqual(sorted(c['id'] for c in json.loads(out)['cycles']), sorted([*FROZEN, 'CYC-0168', OPEN]))

    def plant(self):
        """A script that loads a deleted module name, the positive control for the probe."""
        script = self.root / 'plant.py'
        script.write_text('import sys, types\nsys.modules["cycle_workflow"] = types.ModuleType("cycle_workflow")\n')
        return str(script)

    def test_show_renders_every_frozen_record_without_legacy_modules(self):
        for ident in (*FROZEN, 'CYC-0168', OPEN):
            for extra in ((), ('--full',)):
                with self.subTest(ident=ident, extra=extra):
                    code, out, loaded, modules = self.probe('cycle.py', '--repo-root', str(self.root), 'show', ident, *extra)
                    self.assertEqual((code, loaded), (0, []), out)
                    self.assertTrue(json.loads(out)['ok'])
                    self.assertIn('cycle_writer', modules)  # the probe saw the reader load

    def test_every_frozen_record_reads_through_the_queue_without_legacy_modules(self):
        import cycle_queue
        from bionic_config import load_config
        (self.root / 'bionic/objectives.md').write_text('Mission: useful changes.')
        idents = [*FROZEN, OPEN]
        for ident in idents:
            cycle_queue.add(self.root, f'Item {ident}', 'Outcome', 'iterate', ['src'], ['ok'])
        path = self.root / 'bionic/queue/cycles.yaml'
        doc = cycle_queue.parse_queue(path.read_text())
        for n, (item, ident) in enumerate(zip(doc['items'], idents)):
            item.update(state='started', cycle=ident, started_at='2026-01-01T00:00:00+00:00', start_token=f'{n:032x}')
        cycle_queue.write_queue(load_config(self.root, require_tree=True), doc)
        code, out, loaded, modules = self.probe('cycle.py', '--repo-root', str(self.root), 'queue', 'list', '--full')
        self.assertEqual((code, loaded), (0, []), out)
        self.assertIn('cycle_history', modules)
        items = json.loads(out)['items']
        self.assertEqual([i['cycle'] for i in items], idents)
        code, out, loaded, _ = self.probe('cycle.py', '--repo-root', str(self.root), 'queue', 'list')
        self.assertEqual((code, loaded), (0, []), out)
        for n in range(1, len(idents) + 1):
            with self.subTest(item=n):
                code, out, loaded, _ = self.probe('cycle.py', '--repo-root', str(self.root), 'queue', 'show', f'Q-{n:04d}')
                self.assertEqual((code, loaded), (0, []), out)
                item = json.loads(out)['item']
                self.assertEqual(item['cycle'], idents[n - 1])
                self.assertTrue(item['history'], idents[n - 1])  # every frozen record's facts read through `queue show`

    def test_probe_detects_a_legacy_import(self):
        """Positive control: a script that loads a deleted typed-engine module is seen loading it."""
        code, _, loaded, _ = self.probe(self.plant())
        self.assertEqual((code, loaded), (0, ['cycle_workflow']))

    def test_a_queue_command_that_adds_a_release_item_loads_no_typed_module(self):
        """`queue add` of a release item reads the release descriptor through the cycle writer, so it loads no typed-engine module.

        The positive control runs in the same method: the probe sees a typed load when a command loads the typed engine."""
        queue(self.root)
        code, out, loaded, _ = self.probe('cycle.py', '--repo-root', str(self.root), 'queue', 'add', '--title', 'Ship', '--outcome', 'o',
                                          '--type', 'release', '--scope', 'src', '--acceptance', 'ok')
        self.assertEqual((code, loaded), (0, []), out)
        _, _, control, _ = self.probe(self.plant())
        self.assertIn('cycle_workflow', control)

    def test_status_refuses_two_different_cycles(self):
        code, out, loaded, _ = self.probe('cycle.py', '--repo-root', str(self.root), 'status', 'CYC-0001', '--cycle', 'CYC-0168')
        self.assertEqual(code, 1)
        self.assertIn('given twice', json.loads(out)['error'])

    def test_history_refuses_a_lightweight_record(self):
        with self.assertRaises(cycle_store.CycleError):
            cycle_history.load(VNEXT.read_text())
        self.assertEqual(cycle_history.load(LEGACY.read_text())['id'], 'CYC-0001')

    def test_history_refuses_an_unknown_schema_version(self):
        for version in (None, 0, 4, '3'):
            with self.subTest(version=version), self.assertRaises(cycle_store.CycleError):
                cycle_history.load(json.dumps({**fresh('quick-fix'), 'schema_version': version}))


class FactsTests(unittest.TestCase):
    def read(self, ident):
        return json.loads((frozen_source(ident) / 'cycle.json').read_text())

    def test_each_frozen_record_gives_its_bounded_facts(self):
        for ident, (version, kind, listed) in FROZEN.items():
            with self.subTest(ident=ident):
                doc = self.read(ident)
                facts = cycle_history.facts(doc)
                self.assertEqual((facts['schema_version'], facts['type'], facts['status']), (version, kind, doc['status']))
                self.assertEqual(sum(facts['tasks'].values()), len(doc['plan']['tasks']))
                self.assertEqual(facts['release'] is not None, kind == 'release')
                if listed:
                    self.assertEqual(facts['release']['list'], listed)

    def test_review_verdict_completion_and_evidence_paths(self):
        reports = HISTORY
        facts = cycle_history.facts(self.read('CYC-0172'), lambda rel: json.loads((reports / rel.removeprefix('cycles/')).read_text()))
        self.assertEqual(facts['review']['verdict'], 'approve')
        self.assertEqual(facts['completion']['commits'], self.read('CYC-0172')['completion']['commits'])
        self.assertIsNone(cycle_history.facts(self.read('CYC-0172'))['review']['verdict'])  # no reader, no verdict
        release = cycle_history.facts(self.read('CYC-0094'))
        self.assertIn('cycles/CYC-0094/evidence/release/ledger.json', release['evidence_paths'])
        legacy = cycle_history.facts(self.read('CYC-0015'))
        self.assertEqual((legacy['phases'], legacy['release']['retained']), (['plan', 'release', 'reflect'], 'cycles/CYC-0015/evidence/release'))

    def test_queue_status_of_a_legacy_record(self):
        self.assertEqual(cycle_history.status_of(self.read('CYC-0101')), 'abandoned')
        with self.assertRaises(cycle_store.CycleError):
            cycle_history.status_of({**self.read('CYC-0101'), 'status': 'nonsense'})
        with self.assertRaises(cycle_store.CycleError):
            cycle_history.status_of(json.loads(VNEXT.read_text()))


class CanonicalBytesTests(unittest.TestCase):
    def test_frozen_records_reencode_to_their_bytes(self):
        for path in [LEGACY, VNEXT, *sorted((HERE / 'fixtures/cycle-records').glob('*/cycle.json'))]:
            with self.subTest(path=path.parent.name):
                raw = path.read_bytes()
                self.assertEqual(cycle_store.encoded(json.loads(raw)), raw)

    def test_recorded_decision_digests_recompute(self):
        """Every decision a closed legacy cycle references recomputes to its recorded sha256; each JSON one re-encodes to its bytes.

        An open cycle is skipped: its proposed ADR may still change after the record took its digest."""
        require_dev_surface(self, REPO_ROOT / TREE / 'cycles', 'committed cycle records')
        docs = REPO_ROOT / TREE
        checked = encoded = 0
        for record in sorted((docs / 'cycles').glob('*/cycle.json')):
            doc = json.loads(record.read_bytes())
            if not cycle_history.is_legacy(doc) or doc['status'] not in cycle_history.CLOSED:
                continue
            for ref in doc.get('decisions', []):
                raw = (docs / ref['path']).read_bytes()
                with self.subTest(path=ref['path']):
                    self.assertEqual(cycle_store.digest(raw), ref['sha256'])
                    if ref['path'].endswith('.json'):
                        self.assertEqual(cycle_store.encoded(json.loads(raw)), raw)
                        encoded += 1
                checked += 1
        self.assertGreater(encoded, 0)
        self.assertGreater(checked, encoded)


class EditingRuleTests(unittest.TestCase):
    def test_only_a_developer_on_claude_code_works_in_a_worktree(self):
        """The frozen rule: a developer on claude-code works in a worktree; every other role and host, and an unknown or null host, edits the main checkout."""
        self.assertFalse(cycle_history.edits_main_checkout({'role': 'developer', 'host': 'claude-code'}))
        for role, host in (('dev-lead', 'claude-code'), ('developer', 'codex'), ('developer', 'opencode'), ('developer', 'omp'),
                           ('developer', None), ('developer', ''), ('developer', 'no-such-host'), ('dev-lead', 'codex'), ('reviewer', 'claude-code')):
            with self.subTest(role=role, host=host):
                self.assertTrue(cycle_history.edits_main_checkout({'role': role, 'host': host}))
        self.assertTrue(cycle_history.edits_main_checkout({'role': 'developer'}))


if __name__ == '__main__':
    unittest.main()
