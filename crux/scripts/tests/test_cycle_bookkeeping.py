"""Compact output, idempotent task delivery, handoff and evidence-only reconcile."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle
from cycle_workflow import PHASES, create, load, mutate


class Base(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.repo = root / 'repo'; self.repo.mkdir()
        self.wt = root / 'wt'
        (self.repo / 'bionic').mkdir()
        (self.repo / 'bionic/manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\nadr:\n  next_number: 1\n')
        (self.repo / 'bionic/objectives.md').write_text('Mission: useful changes.')
        (self.repo / 'src').mkdir(); (self.repo / 'src/a.py').write_text('x = 1\n')
        self.git('init', '-q', '-b', 'main')
        self.git('config', 'user.email', 't@example.invalid'); self.git('config', 'user.name', 'T')
        self.git('add', '.'); self.git('commit', '-qm', 'baseline')
        doc = create(self.repo, 'iterate', 'Change', 'Goal', ['src'], ['Works'], 'dev', 'lead')
        plan = json.loads(json.dumps(doc['plan']))
        tasks = [{'id': p, 'phase': p, 'description': p, 'depends_on': [], 'status': 'pending', 'expected_evidence': ['x']} for p in PHASES['iterate']]
        tasks.append({'id': 'B2', 'phase': 'build', 'description': 'b2', 'depends_on': ['build'], 'status': 'pending', 'expected_evidence': ['x']})
        tasks.append({'id': 'B3', 'phase': 'build', 'description': 'b3', 'depends_on': [], 'status': 'pending', 'expected_evidence': ['x']})
        plan.update(verification=['t'], tasks=tasks)
        self.cid = mutate(self.repo, doc['id'], 'plan', plan=plan, reason='p')['id']
        mutate(self.repo, self.cid, 'task', task_id='plan', state='done')
        mutate(self.repo, self.cid, 'advance')

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], text=True).strip()

    def commit(self, msg, name='f.txt'):
        (self.repo / name).write_text(msg)
        self.git('add', name); self.git('commit', '-qm', msg)
        return self.git('rev-parse', 'HEAD')

    def run_cli(self, *argv, expect=0):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cycle.main(['--repo-root', str(self.repo), *argv])
        self.assertEqual(code, expect, out.getvalue())
        return out.getvalue()

    def path(self):
        return self.repo / 'bionic/cycles' / self.cid / 'cycle.json'

    def task(self, tid):
        return next(t for t in load(self.repo, self.cid)['plan']['tasks'] if t['id'] == tid)


class CompactTests(Base):
    def test_compact_success_is_one_line(self):
        out = self.run_cli('--compact', 'task', self.cid, '--task-id', 'build', '--state', 'active', '--assignee', 'dev-1')
        self.assertEqual(out.count('\n'), 1)
        line = json.loads(out)
        self.assertTrue(line['ok']); self.assertTrue(line['changed'])
        self.assertEqual(line['cycle'], self.cid); self.assertEqual(line['phase'], 'build')
        self.assertEqual(line['task'], {'id': 'build', 'state': 'active', 'assignee': 'dev-1'})
        for key in ('pass', 'status', 'updated_at'):
            self.assertIn(key, line)

    def test_compact_after_subcommand_and_no_task_key(self):
        out = self.run_cli('show', self.cid, '--compact')
        line = json.loads(out)
        self.assertEqual(out.count('\n'), 1); self.assertNotIn('task', line); self.assertFalse(line['changed'])

    def test_default_output_unchanged(self):
        out = json.loads(self.run_cli('task', self.cid, '--task-id', 'build', '--state', 'active'))
        self.assertEqual(set(out), {'ok', 'cycle'}); self.assertEqual(out['cycle']['id'], self.cid)

    def test_refusals_keep_shape_and_exit_one(self):
        self.commit('c1')
        cases = [
            ('--task-id', 'nope', '--state', 'done'),
            ('--task-id', 'B2', '--state', 'done'),
            ('--task-id', 'build', '--commit', 'deadbeefdeadbeef'),
            ('--task-id', 'build', '--evidence', 'missing/file.md'),
        ]
        for case in cases:
            line = json.loads(self.run_cli('--compact', 'task', self.cid, *case, expect=1))
            self.assertFalse(line['ok']); self.assertIn('error', line)
        self.git('checkout', '-q', '-b', 'side'); side = self.commit('side')
        self.git('checkout', '-q', 'main')
        line = json.loads(self.run_cli('--compact', 'task', self.cid, '--task-id', 'build', '--commit', side, '--stage', 'integrated', expect=1))
        self.assertIn('ancestor', line['error'])
        self.assertIsNone(self.task('build').get('commits'))
        line = json.loads(self.run_cli('--compact', 'task', self.cid, '--task-id', 'build', '--stage', 'implemented', expect=1))
        self.assertIn('commit', line['error'])


class IdempotencyTests(Base):
    def test_duplicate_update_writes_nothing(self):
        sha = self.commit('c1')
        args = ('--compact', 'task', self.cid, '--task-id', 'build', '--state', 'active', '--commit', sha, '--stage', 'implemented', '--assignee', 'a')
        first = json.loads(self.run_cli(*args)); self.assertTrue(first['changed'])
        before = self.path().read_bytes(); history = len(load(self.repo, self.cid)['history'])
        again = json.loads(self.run_cli(*args))
        self.assertFalse(again['changed'])
        self.assertEqual(self.path().read_bytes(), before)
        self.assertEqual(len(load(self.repo, self.cid)['history']), history)
        self.assertEqual(again['updated_at'], first['updated_at'])
        self.assertEqual(self.task('build')['commits'], [sha])

    def test_commits_merge_as_set(self):
        a = self.commit('a'); b = self.commit('b')
        self.run_cli('task', self.cid, '--task-id', 'build', '--commit', a)
        self.run_cli('task', self.cid, '--task-id', 'build', '--commit', b, '--commit', a[:10])
        self.assertEqual(self.task('build')['commits'], [a, b])

    def test_interrupted_coordinator_resend(self):
        sha = self.commit('c1')
        mutate(self.repo, self.cid, 'task', task_id='build', state='done', commits=[sha], stage='integrated')
        history = len(load(self.repo, self.cid)['history'])
        line = json.loads(self.run_cli('--compact', 'task', self.cid, '--task-id', 'build', '--state', 'done', '--commit', sha, '--stage', 'integrated'))
        self.assertFalse(line['changed'])
        self.assertEqual(len(load(self.repo, self.cid)['history']), history)

    def test_evidence_merges_and_tested_is_not_a_stage(self):
        (self.repo / 'bionic/note.md').write_text('x')
        self.run_cli('task', self.cid, '--task-id', 'build', '--evidence', 'note.md')
        self.assertEqual(self.task('build')['evidence'], ['note.md'])
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            cycle.main(['--repo-root', str(self.repo), 'task', self.cid, '--task-id', 'build', '--stage', 'tested'])


    def test_late_lower_stage_after_integrated_is_satisfied(self):
        sha = self.commit('c1')
        self.run_cli('task', self.cid, '--task-id', 'build', '--state', 'done', '--commit', sha, '--stage', 'integrated')
        before = self.path().read_bytes()
        line = json.loads(self.run_cli('--compact', 'task', self.cid, '--task-id', 'build', '--state', 'done', '--commit', sha, '--stage', 'implemented'))
        self.assertTrue(line['ok']); self.assertFalse(line['changed'])
        self.assertEqual(self.path().read_bytes(), before)
        self.assertEqual(self.task('build')['stage'], 'integrated')
        other = self.commit('c2')
        line = json.loads(self.run_cli('--compact', 'task', self.cid, '--task-id', 'build', '--commit', other, '--stage', 'implemented', expect=1))
        self.assertIn('backward', line['error'])
        self.assertEqual(self.path().read_bytes(), before)

    def test_evidence_paths_are_normalized(self):
        (self.repo / 'bionic/e.md').write_text('x')
        self.run_cli('task', self.cid, '--task-id', 'build', '--evidence', './e.md')
        self.assertEqual(self.task('build')['evidence'], ['e.md'])
        before = self.path().read_bytes()
        line = json.loads(self.run_cli('--compact', 'task', self.cid, '--task-id', 'build', '--evidence', 'e.md', '--evidence', './/e.md'))
        self.assertFalse(line['changed'])
        self.assertEqual(self.path().read_bytes(), before)


class HandoffTests(Base):
    def test_handoff_content_and_read_only(self):
        sha = self.commit('c1')
        self.run_cli('task', self.cid, '--task-id', 'build', '--state', 'active', '--assignee', 'dev-1', '--result-path', 'r/build.md')
        self.run_cli('task', self.cid, '--task-id', 'B3', '--state', 'done', '--commit', sha, '--stage', 'implemented')
        before = self.path().read_bytes()
        out = self.run_cli('--compact', 'handoff', self.cid)
        self.assertEqual(out.count('\n'), 1)
        h = json.loads(out)
        self.assertEqual((h['cycle'], h['phase'], h['pass'], h['pass_limit'], h['status']), (self.cid, 'build', 1, 2, 'active'))
        self.assertEqual(h['active'], [{'id': 'build', 'assignee': 'dev-1', 'result_path': 'r/build.md'}])
        self.assertEqual(h['delivered'], [{'id': 'B3', 'stage': 'implemented', 'commits': [sha]}])
        self.assertIn('B2', [t['id'] for t in h['pending']])
        self.assertIn('Collect results', h['next_action']); self.assertIn('r/build.md', h['next_action'])
        self.assertGreater(self.run_cli('handoff', self.cid).count('\n'), 3)
        self.assertEqual(self.path().read_bytes(), before)

    def test_handoff_advance_and_paused(self):
        for t in ('build', 'B2', 'B3'):
            self.run_cli('task', self.cid, '--task-id', t, '--state', 'done')
        self.assertIn('run advance', json.loads(self.run_cli('--compact', 'handoff', self.cid))['next_action'])
        self.run_cli('pause', self.cid, '--reason', 'owner decision needed')
        self.assertIn('paused', json.loads(self.run_cli('--compact', 'handoff', self.cid))['next_action'].lower())


class ReconcileTests(Base):
    def stale(self):
        """Stale record: tasks still pending while trailer commits exist."""
        self.merged = self.commit(f'{self.cid} U1: merged\n\nCycle-Task: build', 'm.txt')
        self.git('checkout', '-q', '-b', 'side')
        self.sidec = self.commit(f'{self.cid} U2: side\n\nCycle-Task: B3', 's.txt')
        self.git('checkout', '-q', 'main')
        self.git('worktree', 'add', '-q', str(self.wt), 'side')
        self.addCleanup(lambda: subprocess.run(['git', '-C', str(self.repo), 'worktree', 'remove', '--force', str(self.wt)], capture_output=True))
        self.ambig = self.commit(f'{self.cid} both\n\nCycle-Task: B2\nCycle-Task: review', 'x.txt')
        self.other = self.commit('CYC-0099 other cycle\n\nCycle-Task: reflect', 'o.txt')

    def report(self, *extra):
        return json.loads(self.run_cli('reconcile', self.cid, *extra))

    def test_reconcile_dry_run_and_apply(self):
        self.stale()
        before = self.path().read_bytes()
        rep = self.report()
        self.assertTrue(rep['ok']); self.assertEqual(rep['applied'], [])
        self.assertEqual(self.path().read_bytes(), before)
        by = {p['task']: p for p in rep['proposed']}
        self.assertEqual(by['build']['set']['stage'], 'integrated')
        self.assertEqual(by['build']['set']['commits'], [self.merged])
        self.assertEqual(by['B3']['set']['stage'], 'implemented')
        self.assertEqual(by['B3']['set']['commits'], [self.sidec])
        un = {u['task']: u['reason'] for u in rep['unresolved']}
        self.assertIn('ambiguous', un['B2']); self.assertIn('ambiguous', un['review'])
        self.assertIn('not on HEAD', un['B3'])
        self.assertNotIn('reflect', un)
        self.assertTrue(rep['discrepancies'])
        old = load(self.repo, self.cid)
        rep = self.report('--apply')
        self.assertEqual({a['task'] for a in rep['applied']}, {'build', 'B3'})
        doc = load(self.repo, self.cid)
        self.assertEqual(self.task('build')['stage'], 'integrated')
        self.assertEqual(self.task('build')['status'], 'done')
        self.assertEqual(self.task('B3')['stage'], 'implemented')
        self.assertIsNone(self.task('B2').get('commits'))
        for key in ('phase', 'status', 'pass', 'evidence', 'reviews', 'blocker', 'completion', 'reflection'):
            self.assertEqual(doc[key], old[key], key)
        self.assertNotIn('tested', json.dumps(doc['plan']['tasks']))
        stable = self.path().read_bytes()
        again = self.report('--apply')
        self.assertEqual((again['proposed'], again['applied']), ([], []))
        self.assertEqual(self.path().read_bytes(), stable)

    def test_state_left_when_dependency_not_done(self):
        c = self.commit(f'{self.cid} U: b2\n\nCycle-Task: B2', 'b2.txt')
        rep = self.report('--apply')
        self.assertEqual(self.task('B2')['commits'], [c])
        self.assertEqual(self.task('B2')['status'], 'pending')
        self.assertIn('dependenc', ' '.join(u['reason'] for u in rep['unresolved'] if u['task'] == 'B2'))

    def test_dangling_commit_on_done_task_is_unresolved(self):
        mutate(self.repo, self.cid, 'task', task_id='B3', state='done', result_path='nowhere.md')
        doc = load(self.repo, self.cid)
        for t in doc['plan']['tasks']:
            if t['id'] == 'B3':
                t['commits'] = ['a' * 40]
        (self.path()).write_text(json.dumps(doc, indent=2) + '\n')  # simulates a commit later garbage-collected
        before = self.path().read_bytes()
        rep = self.report('--apply')
        reasons = ' '.join(u['reason'] for u in rep['unresolved'] if u['task'] == 'B3')
        self.assertIn('does not resolve', reasons); self.assertIn('result path', reasons)
        self.assertEqual(self.path().read_bytes(), before)
        self.assertEqual(self.task('B3')['status'], 'done')


    def test_commits_never_complete_non_build_tasks(self):
        """A single Cycle-Task trailer naming a test, review or reflect task changes nothing."""
        shas = {t: self.commit(f'{self.cid} {t}: work\n\nCycle-Task: {t}', f'{t}.txt') for t in ('test', 'review', 'reflect')}
        before = self.path().read_bytes()
        rep = self.report()
        self.assertFalse({'test', 'review', 'reflect'} & {p['task'] for p in rep['proposed']})
        un = {u['task']: u['reason'] for u in rep['unresolved']}
        for t in shas:
            self.assertIn('does not establish', un[t]); self.assertIn(t, un[t])
        rep = self.report('--apply')
        self.assertEqual(rep['applied'], [])
        self.assertEqual(self.path().read_bytes(), before)
        for t in shas:
            task = self.task(t)
            self.assertEqual(task['status'], 'pending'); self.assertNotIn('stage', task); self.assertNotIn('commits', task)

    def test_apply_follows_dependency_order(self):
        doc = create(self.repo, 'iterate', 'Order', 'Goal', ['src'], ['Works'], 'dev', 'lead')
        plan = json.loads(json.dumps(doc['plan']))
        tasks = [{'id': p, 'phase': p, 'description': p, 'depends_on': [], 'status': 'pending', 'expected_evidence': ['x']} for p in PHASES['iterate'] if p != 'build']
        tasks[1:1] = [{'id': 'early', 'phase': 'build', 'description': 'e', 'depends_on': ['late'], 'status': 'pending', 'expected_evidence': ['x']},
                      {'id': 'late', 'phase': 'build', 'description': 'l', 'depends_on': [], 'status': 'pending', 'expected_evidence': ['x']}]
        plan.update(verification=['t'], tasks=tasks)
        cid = mutate(self.repo, doc['id'], 'plan', plan=plan, reason='p')['id']
        mutate(self.repo, cid, 'task', task_id='plan', state='done'); mutate(self.repo, cid, 'advance')
        self.commit(f'{cid} early\n\nCycle-Task: early', 'e.txt'); self.commit(f'{cid} late\n\nCycle-Task: late', 'l.txt')
        rep = json.loads(self.run_cli('reconcile', cid, '--apply'))
        self.assertEqual([a['task'] for a in rep['applied']], ['late', 'early'])
        state = {t['id']: t['status'] for t in load(self.repo, cid)['plan']['tasks']}
        self.assertEqual((state['early'], state['late']), ('done', 'done'))

    def test_refusal_after_partial_apply_reports_applied(self):
        from unittest import mock
        import cycle_reconcile
        self.commit(f'{self.cid} b\n\nCycle-Task: build', 'b.txt'); self.commit(f'{self.cid} b3\n\nCycle-Task: B3', 'b3.txt')
        real, calls = cycle_reconcile.mutate_tracked, []
        def flaky(*a, **k):
            calls.append(k['task_id'])
            if len(calls) > 1:
                raise cycle_reconcile.CycleError('simulated refusal')
            return real(*a, **k)
        with mock.patch.object(cycle_reconcile, 'mutate_tracked', flaky):
            rep = json.loads(self.run_cli('reconcile', self.cid, '--apply', expect=1))
        self.assertFalse(rep['ok']); self.assertIn('simulated refusal', rep['error'])
        self.assertEqual([a['task'] for a in rep['applied']], calls[:1])
        self.assertIn(calls[1], [p['task'] for p in rep['proposed']])

    def test_missing_result_file_of_open_task_is_not_a_discrepancy(self):
        self.run_cli('task', self.cid, '--task-id', 'B3', '--state', 'active', '--result-path', 'not-yet.md')
        rep = self.report()
        self.assertNotIn('B3', [u['task'] for u in rep['unresolved']])
        self.assertNotIn('result-path-missing', [d['kind'] for d in rep['discrepancies']])

    def test_result_path_is_resolved_from_the_repository_root(self):
        (self.repo / 'bionic/cycles' / self.cid / 'r.md').write_text('result')
        repo_relative = f'bionic/cycles/{self.cid}/r.md'
        self.run_cli('task', self.cid, '--task-id', 'B3', '--state', 'done', '--result-path', repo_relative)
        rep = self.report()
        self.assertNotIn('result-path-missing', [d['kind'] for d in rep['discrepancies']])

    def test_docs_relative_result_path_of_a_done_task_is_refused(self):
        # The live trial recorded the docs-relative form; reconcile then reported the
        # delivered task's existing result file missing. The writer refuses it instead.
        (self.repo / 'bionic/cycles' / self.cid / 'r.md').write_text('result')
        self.run_cli('task', self.cid, '--task-id', 'B3', '--state', 'active', '--result-path', f'cycles/{self.cid}/r.md')
        out = json.loads(self.run_cli('--compact', 'task', self.cid, '--task-id', 'B3', '--state', 'done', expect=1))
        self.assertFalse(out['ok']); self.assertIn('repository root', out['error'])
        self.assertEqual(self.task('B3')['status'], 'active')
        self.run_cli('task', self.cid, '--task-id', 'B3', '--state', 'done', '--result-path', f'bionic/cycles/{self.cid}/r.md')
        self.assertNotIn('result-path-missing', [d['kind'] for d in self.report()['discrepancies']])

    def test_task_help_names_the_result_path_base(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit):
            cycle.main(['task', '--help'])
        self.assertIn('repository root', ' '.join(out.getvalue().split()))


class GateTests(Base):
    def test_advance_with_unfinished_task_still_refused(self):
        self.run_cli('task', self.cid, '--task-id', 'build', '--state', 'done')
        out = json.loads(self.run_cli('advance', self.cid, expect=1))
        self.assertFalse(out['ok']); self.assertIn('unfinished', out['error'])


if __name__ == '__main__':
    unittest.main()
