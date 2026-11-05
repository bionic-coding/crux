"""Derived activity in cycle status (F26, F28), labelled status sections (F27) and scoped receipt reads.

Each fixture reproduces the friction it answers:
- F26: a cycle with no open attempt and a 3-hour-old last write reads idle with the age.
- F28: an open attempt with a 2-minute-old Cycle-Task commit shows that age and source, and its
  liveness stays unknown.
- F27: CYC-0095 at revision 20 (the committed revision nearest 18 that holds an open attempt) draws
  its attempt under its task inside a labelled section, never after the Reflect task.
"""
import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import cycle_activity  # noqa: E402
import cycle_ops  # noqa: E402
import cycle_progress  # noqa: E402
import cycle_summary  # noqa: E402
from cycle_progress import render, view  # noqa: E402
from cycle_workflow import create, validate  # noqa: E402
from _dev_surface import REPO_ROOT, TREE, require_dev_surface  # noqa: E402

FIXTURES = HERE / 'fixtures/cycle-activity'
GIT = ['git', '-c', 'user.name=t', '-c', 'user.email=t@example.com', '-c', 'commit.gpgsign=false', '-c', 'init.defaultBranch=main']


def iso(epoch):
    return time.strftime('%Y-%m-%dT%H:%M:%S+00:00', time.gmtime(epoch))


def attempt(id, task, started, state='running', result_path=None):
    return {'id': id, 'role': 'developer', 'task': task, 'agent': None, 'result_path': result_path, 'state': state, 'attempt': 1,
            'started_at': iso(started), 'last_seen': iso(started), 'ended_at': None, 'note': None,
            'host': 'claude-code', 'mode': 'blocking', 'base': None, 'delivery': None}


def git(root, *argv, env=None):
    return subprocess.run([*GIT, *argv], cwd=root, capture_output=True, text=True, check=True, env=env).stdout.strip()


class Base(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        (self.root / 'bionic').mkdir(); (self.root / 'src').mkdir()
        (self.root / 'bionic/manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\n')
        self.now = int(time.time())
        # An open cycle tallies the evidence store; keep a shared store named by the environment out of these fixtures.
        patch = mock.patch.dict(os.environ); patch.start(); self.addCleanup(patch.stop)
        for name in ('CRUX_TEST_EVIDENCE_STORE', 'CRUX_TEST_EVIDENCE_DURABLE_ONLY'):
            os.environ.pop(name, None)

    def record(self, assignments=(), updated=None):
        doc = create(self.root, 'iterate', 'Fix', 'Goal', ['src'], ['passes'], 'builder', 'tester')
        path = self.root / 'bionic/cycles' / doc['id'] / 'cycle.json'
        raw = json.loads(path.read_text())
        raw.update(schema_version=3, **cycle_ops.v3_fields())
        raw['revision'] = 1
        task = {'depends_on': [], 'expected_evidence': []}
        raw['plan']['tasks'] = [{**task, 'id': 'build-x', 'phase': 'plan', 'description': 'Build x', 'status': 'active'},
                                {**task, 'id': 'reflect', 'phase': 'reflect', 'description': 'Reflect', 'status': 'pending'}]
        raw['assignments'] = [dict(a) for a in assignments]
        if updated is not None:
            raw['updated_at'] = iso(updated)
        validate(raw)
        path.write_text(json.dumps(raw))
        return doc['id']

    def cycle(self, cid):
        return view(self.root, cid, now=self.now, activity=True)['cycles'][0]


class IdleTests(Base):
    """F26: the commander died and the cycle sat with no marker. Status now says idle and for how long."""

    def test_no_open_attempt_and_a_3_hour_old_write_reads_idle_with_the_age(self):
        cid = self.record(updated=self.now - 3 * 3600)
        c = self.cycle(cid)
        self.assertEqual(c['activity'], {'state': 'idle', 'attempts': [],
                                         'last': {'source': 'record-write', 'at_s': self.now - 10800, 'age_s': 10800, 'detail': None}})
        self.assertIn('  Activity: idle for 3h00m (record-write)', render(view(self.root, cid, now=self.now)).splitlines())

    def test_a_finished_attempt_leaves_the_cycle_idle(self):
        cid = self.record([attempt('a', 'build-x', self.now - 7200, state='finished')], updated=self.now - 60)
        self.assertEqual(self.cycle(cid)['activity']['state'], 'idle')

    def test_a_closed_cycle_draws_no_activity_line(self):
        cid = self.record(updated=self.now - 60)
        path = self.root / 'bionic/cycles' / cid / 'cycle.json'
        raw = json.loads(path.read_text()); raw['status'] = 'abandoned'; path.write_text(json.dumps(raw))
        self.assertNotIn('Activity', render(view(self.root, cid, now=self.now)))


class CommitTests(Base):
    """F28: three attempts showed only 'liveness unknown'. A trailer commit now gives an age and a source."""

    def setUp(self):
        super().setUp()
        git(self.root, 'init', '-q')
        (self.root / 'seed').write_text('seed'); git(self.root, 'add', 'seed'); git(self.root, 'commit', '-q', '-m', 'seed')

    def commit(self, name, task, at):
        (self.root / name).write_text(name)
        git(self.root, 'add', name)
        env = {**os.environ, 'GIT_COMMITTER_DATE': f'@{at} +0000', 'GIT_AUTHOR_DATE': f'@{at} +0000'}
        git(self.root, 'commit', '-q', '-m', f'{name}\n\nCycle-Task: {task}\nCo-Authored-By: x <x@example.com>', env=env)
        return git(self.root, 'rev-parse', 'HEAD')

    def test_an_open_attempt_shows_its_2_minute_old_trailer_commit(self):
        sha = self.commit('one', 'build-x', self.now - 120)
        self.commit('other', 'some-other-task', self.now - 30)  # a newer commit for another task is not this attempt's
        cid = self.record([attempt('a', 'build-x', self.now - 600)], updated=self.now - 600)
        c = self.cycle(cid)
        (row,) = c['activity']['attempts']
        self.assertEqual(row['last'], {'source': 'commit', 'at_s': self.now - 120, 'age_s': 120, 'detail': sha[:12]})
        self.assertEqual(c['activity']['state'], 'attempts-open')
        self.assertEqual(c['assignments'][0]['liveness'], 'unknown')
        text = render(view(self.root, cid, now=self.now)).splitlines()
        self.assertIn(f'      Attempt 1 · a · task build-x · developer · running · liveness unknown · last activity 2m ago (commit {sha[:12]})', text)
        self.assertIn(f'  Activity: last activity 2m ago (commit {sha[:12]})', text)

    def test_a_commit_before_the_attempt_started_is_not_its_activity(self):
        self.commit('early', 'build-x', self.now - 900)
        cid = self.record([attempt('a', 'build-x', self.now - 600)], updated=self.now - 600)
        self.assertEqual(self.cycle(cid)['activity']['attempts'][0]['last']['source'], 'last-seen')

    def test_a_result_file_written_after_the_start_counts(self):
        result = self.root / 'result.md'
        result.write_text('partial')
        os.utime(result, (self.now - 45, self.now - 45))
        cid = self.record([attempt('a', 'build-x', self.now - 600, result_path=str(result))], updated=self.now - 600)
        last = self.cycle(cid)['activity']['attempts'][0]['last']
        self.assertEqual((last['source'], last['age_s'], last['detail']), ('result-file', 45, 'result.md'))

    def test_a_worktree_change_goes_to_the_attempt_that_started_last_before_it(self):
        early, late = attempt('early', 'build-x', self.now - 600), attempt('late', 'build-x', self.now - 300)
        late['attempt'] = 2
        cid = self.record([early, late], updated=self.now - 600)
        tree = self.root.parent / (self.root.name + '-wt')
        git(self.root, 'worktree', 'add', '-q', str(tree))
        self.addCleanup(lambda: subprocess.run([*GIT, 'worktree', 'remove', '--force', str(tree)], cwd=self.root, capture_output=True))
        (tree / 'work.txt').write_text('uncommitted')
        os.utime(tree / 'work.txt', (self.now - 10, self.now - 10))
        rows = {r['id']: r['last'] for r in self.cycle(cid)['activity']['attempts']}
        self.assertEqual((rows['late']['source'], rows['late']['age_s'], rows['late']['detail']), ('worktree-change', 10, tree.name))
        self.assertEqual(rows['early']['source'], 'last-seen')

    def test_a_worktree_created_before_every_attempt_is_ignored(self):
        tree = self.root.parent / (self.root.name + '-old')
        git(self.root, 'worktree', 'add', '-q', str(tree))
        self.addCleanup(lambda: subprocess.run([*GIT, 'worktree', 'remove', '--force', str(tree)], cwd=self.root, capture_output=True))
        admin = cycle_activity._admin_dir(tree)
        for name in ('commondir', 'gitdir'):
            os.utime(admin / name, (self.now - 5000, self.now - 5000))
        (tree / 'work.txt').write_text('uncommitted')
        cid = self.record([attempt('a', 'build-x', self.now - 600)], updated=self.now - 600)
        self.assertEqual(self.cycle(cid)['activity']['attempts'][0]['last']['source'], 'last-seen')

    def test_outside_a_repository_git_events_are_absent_and_nothing_raises(self):
        with tempfile.TemporaryDirectory() as other:
            doc = {'updated_at': iso(self.now - 5), 'assignments': [attempt('a', 'build-x', self.now - 600)]}
            result = cycle_activity.activity(other, doc, self.now)
        self.assertEqual(result['attempts'][0]['last']['source'], 'last-seen')


class SectionTests(unittest.TestCase):
    """F27: the owner read attempt lines printed after the Reflect task as extra Build items."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root / 'bionic/cycles/CYC-0095').mkdir(parents=True)
        (self.root / 'bionic/manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\n')
        (self.root / 'bionic/cycles/CYC-0095/cycle.json').write_bytes((FIXTURES / 'CYC-0095-rev20.json').read_bytes())

    def test_cyc_0095_at_revision_20_nests_its_attempt_under_its_task(self):
        lines = render(view(self.root, 'CYC-0095')).splitlines()
        tasks = lines.index('  Tasks')
        attempt_at = next(n for n, l in enumerate(lines) if 'Attempt 1 · test-acceptance' in l)
        self.assertGreater(attempt_at, tasks)
        self.assertTrue(lines[attempt_at - 1].startswith('  active  test '), lines[attempt_at - 1])
        self.assertTrue(lines[attempt_at].startswith('      Attempt 1 · test-acceptance · task test-acceptance · dev-lead · reserved'))
        reflect = next(n for n, l in enumerate(lines) if l.startswith('  pending reflect '))
        self.assertGreater(reflect, attempt_at)
        self.assertNotIn('Attempt', lines[reflect + 1])
        self.assertEqual(lines[reflect + 1], '  Classifications: 1')

    def test_the_fixture_is_the_committed_revision(self):
        record = json.loads((FIXTURES / 'CYC-0095-rev20.json').read_text())
        self.assertEqual((record['id'], record['revision']), ('CYC-0095', 20))
        self.assertEqual([(a['task'], a['state']) for a in record['assignments'] if a['state'] in ('reserved', 'running')], [('test-acceptance', 'reserved')])


class JsonAdditiveTests(unittest.TestCase):
    """The dashboards' JSON stays as it was; asking for activity only adds the `activity` key."""

    def test_every_committed_record_is_a_superset_of_the_dashboard_document(self):
        directory = REPO_ROOT / TREE / 'cycles'
        require_dev_surface(self, directory, 'the committed cycle records')
        before = view(REPO_ROOT, now=2_000_000_000)
        after = view(REPO_ROOT, now=2_000_000_000, activity=True)
        self.assertEqual(len(after['cycles']), min(60, len(list(directory.glob('CYC-*/cycle.json')))))
        self.assertEqual({k: v for k, v in after.items() if k != 'cycles'}, {k: v for k, v in before.items() if k != 'cycles'})
        for b, a in zip(before['cycles'], after['cycles']):
            self.assertNotIn('activity', b)
            self.assertEqual(set(a) - set(b), {'activity'}, a['id'])
            self.assertEqual({k: a[k] for k in b}, b, a['id'])

    def test_the_visualizer_adds_activity_only_on_request(self):
        spec = importlib.util.spec_from_file_location('visualize_cycle_progress_activity', HERE.parent / 'visualize-cycle-progress.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'bionic').mkdir(); (root / 'src').mkdir()
            (root / 'bionic/manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\n')
            create(root, 'iterate', 'Fix', 'Goal', ['src'], ['passes'], 'b', 't')
            documents = []
            for extra in ((), ('--activity',)):
                out = io.StringIO()
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(module.main(['--json', '--project-root', str(root), *extra]), 0)
                documents.append(json.loads(out.getvalue()))
        plain, asked = documents
        self.assertNotIn('activity', plain['cycles'][0])
        self.assertEqual(asked['cycles'][0]['activity']['state'], 'idle')
        self.assertEqual({k: v for k, v in asked['cycles'][0].items() if k != 'activity'}, plain['cycles'][0])


class ScopedReceiptTests(unittest.TestCase):
    """cycle_summary.test_runs parses only receipts written inside the cycle's window or attached by it."""

    def setUp(self):
        store = tempfile.TemporaryDirectory(); self.addCleanup(store.cleanup)
        self.store = Path(store.name)
        patch = mock.patch.dict(os.environ, {'CRUX_TEST_EVIDENCE_STORE': str(self.store)}); patch.start(); self.addCleanup(patch.stop)

    def receipt(self, number, check, started):
        eid = 'TE-' + f'{number:032x}'
        path = self.store / f'{eid}.json'
        path.write_text(json.dumps({'id': eid, 'declaration': {'check_id': check}, 'started_at': started, 'seconds': 30.0,
                                    'status': 'passed', 'reason': 'missing'}))
        os.utime(path, (started + 30, started + 30))
        return eid

    def test_a_200_receipt_store_parses_only_the_cycle_receipts_and_matches_the_full_read(self):
        begin = 1_800_000_000
        doc = {'status': 'active', 'created_at': iso(begin), 'updated_at': iso(begin + 500),
               'history': [{'action': 'created', 'at': iso(begin), 'pass': 1, 'phase': 'plan'}], 'evidence': []}
        ids = [self.receipt(n, f'check-{n % 20}', begin - 100_000 + n * 100) for n in range(190)]
        inside = [self.receipt(1000 + n, f'check-{n}', begin + 10 + n) for n in range(10)]
        doc['evidence'] = [{'check_id': 'check-3', 'evidence_id': ids[3]}]
        self.assertEqual(len(list(self.store.glob('TE-*.json'))), 200)
        now = begin + 1000
        parsed = []
        real = cycle_summary.json.loads
        with mock.patch.object(cycle_summary.json, 'loads', side_effect=lambda text: parsed.append(1) or real(text)):
            scoped = cycle_summary.test_runs(Path('.'), doc, now)
        self.assertEqual(len(parsed), 11)
        full_read = cycle_summary._receipts
        with mock.patch.object(cycle_summary, '_receipts', lambda store, since=None, ids=(): full_read(store)):
            unscoped = cycle_summary.test_runs(Path('.'), doc, now)
        self.assertEqual(scoped, unscoped)
        self.assertEqual((scoped['executions'], scoped['reused']), (10, [{'check_id': 'check-3', 'receipts': [ids[3]]}]))
        self.assertEqual(sorted(r for row in scoped['executed'] for r in row['receipts']), sorted(inside))


if __name__ == '__main__':
    unittest.main()
