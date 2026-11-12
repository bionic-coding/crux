"""IDR record-and-decision-routes: superseded tasks, the type change, one council count across scopes,
the acceptance-change owner purpose and legacy ADR adoption.

Fixture records only: no council is convened and no model is called.
"""
from copy import deepcopy
import importlib.util
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import council_policy
import cycle_classify
import cycle_council
import cycle_reconcile
import cycle_workflow as wf
import decision_policy as dp
import owner_decision
from cycle_workflow import CycleError, create, digest, load, mutate, tree
import test_cycle_decision_policy as adr_fixtures
import test_cycle_workflow as fixtures
from test_cycle_slice import SliceBase, TEXT


def task(tid, deps=(), phase='build', **extra):
    return {'id': tid, 'phase': phase, 'description': tid, 'depends_on': list(deps), 'status': 'pending',
            'expected_evidence': ['observation'], **extra}


# ───────────────────────────── approach 1: superseded tasks ─────────────────────────────

class SupersedeBase(SliceBase):
    def add(self, tid, deps=(), phase='build', **extra):
        return mutate(self.repo, self.cid, 'task-add', task=task(tid, deps, phase, **extra))

    def supersede(self, tid, other, note='replaced'):
        return mutate(self.repo, self.cid, 'task', task_id=tid, state='superseded', superseded_by=other, note=note)

    def refuses(self, pattern, tid, other):
        before = self.record_path().read_bytes()
        with self.assertRaisesRegex(CycleError, pattern):
            self.supersede(tid, other)
        self.assertEqual(self.record_path().read_bytes(), before)

    def deliver_build(self):
        prepared = self.prepare()
        sha = self.work(prepared)
        self.ok({'op': 'deliver', 'op_id': 'deliver-01', 'assignment': 'build-it', 'attempt': 1, 'outcome': 'done',
                 'commits': [sha], 'stage': 'integrated'})
        return sha

    def prepare_dependent(self, op_id='prep-dep-0001'):
        return {'op': 'prepare-dispatch', 'op_id': op_id, 'task_id': 'dependent', 'role': 'developer',
                'host': 'claude-code', 'assignment_text': TEXT}

    def commit_dependent(self):
        (self.repo / 'src/b.py').write_text('b = 1\n')
        self.git('add', 'src/b.py')
        self.git('commit', '-q', '-m', f'add b\n\nCycle: {self.cid}\nCycle-Task: dependent')
        return self.git('rev-parse', 'HEAD')


class SupersedeDependencyTests(SupersedeBase):
    def test_dependent_of_a_superseded_task_runs_after_the_superseder_and_the_cycle_completes(self):
        self.add('old')
        self.add('dependent', ['old'])
        self.supersede('old', 'build-it')
        code, response = self.op(self.prepare_dependent())
        self.assertEqual(code, 1, response)
        self.assertIn('dependencies-incomplete', [e['code'] for e in response['errors']])
        self.deliver_build()
        seen = self.ok({'op': 'inspect', 'host': 'claude-code'})
        self.assertEqual(seen['superseded'], [{'task': 'old', 'superseded_by': 'build-it'}])
        offered = [a['request'].get('task_id') for a in seen['actions'] if a.get('request', {}).get('op') == 'prepare-dispatch']
        self.assertIn('dependent', offered)
        self.assertNotIn('old', offered)
        prepared = self.ok(self.prepare_dependent('prep-dep-0002'))
        invocation = self.ok({'op': 'dispatch-invocation', 'assignment': 'dependent', 'attempt': 1})
        self.assertIn('invocation', invocation)
        sha = self.commit_dependent()
        self.write_result(prepared)
        self.ok({'op': 'deliver', 'op_id': 'deliver-dep-1', 'assignment': 'dependent', 'attempt': 1, 'outcome': 'done',
                 'commits': [sha], 'stage': 'integrated'})
        doc = load(self.repo, self.cid)
        self.assertNotIn('phase-tasks', [i['requirement'] for i in wf.requirements(tree(self.repo), doc, 'next')])
        # Verify, Review and Reflect close over the superseded task, and the cycle completes (nit F1).
        self.to_reflect()
        seen = self.ok({'op': 'inspect'})
        self.assertEqual(seen['unmet']['completion'], [])
        finish = next(a for a in seen['actions'] if a.get('request', {}).get('op') == 'finish')
        done = self.ok({**finish['request'], 'op_id': 'finish-001', 'lessons': ['a replaced task closes'], 'remaining': ['none']})
        self.assertEqual(done['status'], 'completed')
        doc = load(self.repo, self.cid)
        old = next(t for t in doc['plan']['tasks'] if t['id'] == 'old')
        self.assertEqual((old['status'], old['superseded_by']), ('superseded', 'build-it'))
        self.assertNotIn('old', doc['reflection']['outcome'].split('Delivered tasks:')[-1].split('.')[0])

    def test_reconcile_proposes_the_dependent_done_through_the_superseder(self):
        self.add('old')
        self.add('dependent', ['old'])
        self.deliver_build()
        self.commit_dependent()
        result = cycle_reconcile.reconcile(self.repo, self.cid)
        self.assertIn('dependent', [u['task'] for u in result['unresolved']])
        self.assertNotIn('dependent', [p['task'] for p in result['proposed'] if p['set'].get('state') == 'done'])
        self.supersede('old', 'build-it')
        result = cycle_reconcile.reconcile(self.repo, self.cid)
        self.assertIn('dependent', [p['task'] for p in result['proposed'] if p['set'].get('state') == 'done'])
        handoff = cycle_reconcile.handoff(self.repo, self.cid)
        self.assertEqual(handoff['superseded'], [{'id': 'old', 'phase': 'build', 'superseded_by': 'build-it'}])

    def test_the_redispatch_route_appears_through_the_superseder(self):
        self.add('old')
        self.add('dependent', ['old'])
        self.supersede('old', 'build-it')
        self.deliver_build()
        prepared = self.ok(self.prepare_dependent())
        self.write_result(prepared)
        self.ok({'op': 'deliver', 'op_id': 'deliver-dep-1', 'assignment': 'dependent', 'attempt': 1, 'outcome': 'blocked'})
        doc = load(self.repo, self.cid)
        job = cycle_classify.Job('failure', 'dependent', 'delivery:dependent/1')
        self.assertIn('re-dispatch', cycle_classify.plan_failure(tree(self.repo), doc, job).routes)
        control = deepcopy(doc)
        old = next(t for t in control['plan']['tasks'] if t['id'] == 'old')
        old['status'] = 'pending'
        old.pop('superseded_by')
        self.assertNotIn('re-dispatch', cycle_classify.plan_failure(tree(self.repo), control, job).routes)

    def test_the_phase_tasks_check_counts_a_superseded_task_closed(self):
        self.add('old')
        self.deliver_build()
        cfg = tree(self.repo)
        before = [i['problem'] for i in wf.requirements(cfg, load(self.repo, self.cid), 'next') if i['requirement'] == 'phase-tasks']
        self.assertTrue(before and 'old (pending)' in before[0])
        self.supersede('old', 'build-it')
        self.assertNotIn('phase-tasks', [i['requirement'] for i in wf.requirements(cfg, load(self.repo, self.cid), 'next')])

    def test_a_superseded_task_accepts_no_later_state_change(self):
        self.add('old')
        self.supersede('old', 'build-it')
        with self.assertRaisesRegex(CycleError, 'accepts no later state change'):
            mutate(self.repo, self.cid, 'task', task_id='old', state='pending')


class SupersedeRefusalTests(SupersedeBase):
    def test_refuses_a_reserved_or_running_assignment(self):
        self.add('old')
        self.prepare()
        self.refuses('held by reserved', 'build-it', 'old')

    def test_refuses_self_missing_and_superseded_superseders(self):
        self.add('old')
        self.add('other')
        self.refuses('cannot supersede itself', 'old', 'old')
        self.refuses('unknown superseder', 'old', 'nope')
        self.supersede('old', 'build-it')
        self.refuses('itself superseded', 'other', 'old')

    def test_refuses_a_task_that_is_already_a_superseder(self):
        self.add('old')
        self.add('other')
        self.supersede('old', 'build-it')
        self.refuses('already supersedes', 'build-it', 'other')

    def test_refuses_a_superseder_in_another_phase(self):
        self.add('old')
        self.add('check-it', phase='verify')
        self.refuses('another phase', 'old', 'check-it')

    def test_refuses_a_done_task_and_a_task_with_recorded_commits(self):
        self.add('old')
        self.add('other')
        mutate(self.repo, self.cid, 'task', task_id='old', state='done')
        self.refuses('is done', 'old', 'build-it')
        mutate(self.repo, self.cid, 'task', task_id='other', commits=[self.base])
        self.refuses('records or delivered commits', 'other', 'build-it')

    def test_refuses_a_task_named_in_integrates(self):
        self.add('u1')
        self.add('u2')
        self.add('joined', ['u1', 'u2'], integrates=['u1', 'u2'])
        self.refuses('integrated by joined', 'u1', 'build-it')

    def test_refuses_a_superseder_that_depends_on_the_superseded_task(self):
        self.add('old')
        self.add('direct', ['old'])
        self.refuses('cycle through a superseded task', 'old', 'direct')
        self.add('mid', ['old'])
        self.add('through', ['mid'])
        self.refuses('cycle through a superseded task', 'old', 'through')

    def test_a_superseded_tasks_only_out_edge_is_its_superseder(self):
        # Nit F2: S depends on X, X on S2, O2 on S. Following S's own edges would see S -> X -> S2 -> O2 -> S.
        self.add('O')
        self.add('S2')
        self.add('X', ['S2'])
        self.add('S', ['X'])
        self.add('O2', ['S'])
        self.supersede('S', 'O')
        doc = self.supersede('S2', 'O2')
        self.assertEqual({t['id']: t.get('superseded_by') for t in doc['plan']['tasks'] if t['status'] == 'superseded'},
                         {'S': 'O', 'S2': 'O2'})

    def test_supersede_requires_a_note(self):
        self.add('old')
        with self.assertRaisesRegex(CycleError, 'note'):
            mutate(self.repo, self.cid, 'task', task_id='old', state='superseded', superseded_by='build-it')

    def memory(self):
        doc = load(self.repo, self.cid)
        doc['plan']['tasks'].append(task('old'))
        return doc

    def update(self, doc, tid='old', other='build-it'):
        target = next(t for t in doc['plan']['tasks'] if t['id'] == tid)
        return wf.updated_task(tree(self.repo), doc, target, {'state': 'superseded', 'superseded_by': other, 'note': 'replaced'})

    def test_refuses_fix_tasks_on_either_side_and_delivered_commits(self):
        fix = {'pass': 1, 'phase': 'verify', 'finding': 'r1:blocking:0', 'eligibility': 'small'}
        doc = self.memory()
        doc['plan']['tasks'][-1]['fix'] = fix
        with self.assertRaisesRegex(CycleError, 'is a fix task'):
            self.update(doc)
        doc = self.memory()
        next(t for t in doc['plan']['tasks'] if t['id'] == 'build-it')['fix'] = fix
        with self.assertRaisesRegex(CycleError, 'superseder build-it is a fix task'):
            self.update(doc)
        doc = self.memory()
        doc.setdefault('assignments', []).append({'id': 'old', 'task': 'old', 'attempt': 1, 'state': 'finished',
                                                  'delivery': {'outcome': 'failed', 'commits': [self.base]}})
        with self.assertRaisesRegex(CycleError, 'records or delivered commits'):
            self.update(doc)

    def test_a_listed_release_cycle_holds_no_superseded_task(self):
        doc = self.memory()
        doc.update(type='release', release_list='beta')
        with self.assertRaisesRegex(CycleError, 'listed release'):
            self.update(doc)
        old = doc['plan']['tasks'][-1]
        old.update(status='superseded', superseded_by='build-it')
        with self.assertRaisesRegex(CycleError, 'listed release'):
            wf.validate_supersession(doc)


class SupersedePlanTests(unittest.TestCase):
    setUp = fixtures.CycleTests.setUp
    cycle = fixtures.CycleTests.cycle
    apply = fixtures.CycleTests.apply

    def build_phase(self, b1_extra=None, supersede=True):
        doc = self.cycle('iterate')
        plan = deepcopy(doc['plan'])
        plan.update(verification=['focused tests'], tasks=[
            task('plan', phase='plan'), task('b1', **(b1_extra or {})), task('b2'), task('b3', ['b1']),
            task('verify', phase='verify'), task('review', phase='review'), task('reflect', phase='reflect')])
        doc = self.apply(doc, 'plan', plan=plan, reason='initial plan')
        doc = self.apply(doc, 'task', task_id='plan', state='done')
        doc = self.apply(doc, 'advance')
        if supersede:
            doc = self.apply(doc, 'task', task_id='b1', state='superseded', superseded_by='b2', note='b2 replaces b1')
        return doc

    def tasks(self, doc):
        return {t['id']: t for t in doc['plan']['tasks']}

    def test_a_new_pass_keeps_a_superseded_task_superseded(self):
        doc = self.build_phase()
        wf.start_pass(tree(self.repo), doc)
        b1 = self.tasks(doc)['b1']
        self.assertEqual((b1['status'], b1['superseded_by']), ('superseded', 'b2'))
        wf.validate(doc)

    def test_a_plan_revision_that_changes_the_superseded_task_keeps_status_and_superseder(self):
        doc = self.build_phase()
        plan = wf.plan_file_of(doc)
        next(t for t in plan['tasks'] if t['id'] == 'b1')['description'] = 'b1, described again'
        doc = self.apply(doc, 'plan', plan=plan, reason='describe b1 again')
        b1 = self.tasks(doc)['b1']
        self.assertEqual((b1['status'], b1['superseded_by'], b1['description']), ('superseded', 'b2', 'b1, described again'))

    def revise(self, doc, change):
        plan = wf.plan_file_of(doc)
        change(plan)
        return self.apply(doc, 'plan', plan=plan, reason='revision')

    def test_the_validator_refuses_revisions_that_break_the_supersession(self):
        doc = self.build_phase()
        cases = {
            'omit the superseder': lambda p: p.update(tasks=[t for t in p['tasks'] if t['id'] != 'b2']),
            'move the superseder': lambda p: next(t for t in p['tasks'] if t['id'] == 'b2').update(phase='verify'),
            'move the superseded task': lambda p: next(t for t in p['tasks'] if t['id'] == 'b1').update(phase='verify'),
            'superseder depends on it': lambda p: next(t for t in p['tasks'] if t['id'] == 'b2').update(depends_on=['b1']),
        }
        for name, change in cases.items():
            with self.subTest(name), self.assertRaises(CycleError):
                self.revise(doc, change)
        self.assertEqual(load(self.repo, doc['id']), doc)

    def test_a_plan_file_cannot_set_superseded_or_superseded_by(self):
        doc = self.build_phase()
        for field in ({'status': 'superseded'}, {'superseded_by': 'b2'}):
            with self.subTest(field), self.assertRaisesRegex(CycleError, 'plan file sets plan content only'):
                self.revise(doc, lambda p: next(t for t in p['tasks'] if t['id'] == 'b3').update(field))

    def test_the_dependency_is_satisfied_only_once_the_superseder_is_done(self):
        doc = self.build_phase()
        with self.assertRaisesRegex(CycleError, 'incomplete'):
            self.apply(doc, 'task', task_id='b3', state='done')
        self.assertFalse(wf.dependency_satisfied(doc, 'b1'))
        doc = self.apply(doc, 'task', task_id='b2', state='done')
        self.assertTrue(wf.dependency_satisfied(doc, 'b1'))
        self.assertEqual(self.tasks(self.apply(doc, 'task', task_id='b3', state='done'))['b3']['status'], 'done')

    def test_a_superseded_task_naming_an_unaccepted_adr_does_not_block_the_phase(self):
        cfg = tree(self.repo)
        blocked = self.build_phase(b1_extra={'adr_dependencies': ['not-recorded']}, supersede=False)
        self.assertIn('decisions', [i['requirement'] for i in wf.requirements(cfg, blocked, 'next')])
        doc = self.apply(blocked, 'task', task_id='b1', state='superseded', superseded_by='b2', note='b2 replaces b1')
        self.assertNotIn('decisions', [i['requirement'] for i in wf.requirements(cfg, doc, 'next')])


# ───────────────────────────── approach 2: the type change ─────────────────────────────

class ChangeTypeTests(unittest.TestCase):
    setUp = fixtures.CycleTests.setUp
    cycle = fixtures.CycleTests.cycle
    apply = fixtures.CycleTests.apply
    fixture_approval = fixtures.CycleTests.fixture_approval

    def dev_in_build(self, tasks):
        doc = self.cycle('dev')
        plan = deepcopy(doc['plan'])
        plan.update(verification=['focused tests'], tasks=tasks)
        doc = self.apply(doc, 'plan', plan=plan, reason='initial plan')
        contents = {k: ['reason'] for k in ('alternatives', 'approach', 'assumptions', 'constraints', 'intended_evidence')}
        doc = self.apply(doc, 'decision', kind='idr', name='choice', contents=contents)
        subject = doc['decisions'][-1]['path']
        doc = self.apply(doc, 'approve-decision', subject=subject, approval=self.fixture_approval(doc, subject))
        doc = self.apply(doc, 'task', task_id='plan', state='done')
        return self.apply(doc, 'advance')

    def test_dev_to_iterate_keeps_done_build_work_and_forces_a_new_plan(self):
        doc = self.dev_in_build([task('plan', phase='plan'), task('bdone', ['plan']), task('bpend'),
                                 task('verify', phase='verify'), task('review', phase='review'), task('reflect', phase='reflect')])
        doc = self.apply(doc, 'task', task_id='bdone', state='done')
        doc = self.apply(doc, 'task', task_id='verify', state='done')
        doc = self.apply(doc, 'change-type', kind='iterate', reason='the remaining scope needs no material decision')
        self.assertEqual([(t['id'], t['status'], t['depends_on']) for t in doc['plan']['tasks']],
                         [('plan', 'pending', []), ('bdone', 'done', [])])
        self.assertEqual(doc['phase'], 'plan')
        changed = next(e for e in reversed(doc['history']) if e['action'] == 'type-changed')
        self.assertEqual({t['id'] for t in changed['previous_plan']['tasks']},
                         {'plan', 'bdone', 'bpend', 'verify', 'review', 'reflect'})
        doc = self.apply(doc, 'task', task_id='plan', state='done')
        with self.assertRaisesRegex(CycleError, 'every phase'):
            self.apply(doc, 'advance')

    def test_a_done_task_integrating_a_dropped_task_is_dropped(self):
        doc = self.dev_in_build([task('plan', phase='plan'), task('u1'), task('u2'), task('joined', ['u1', 'u2'], integrates=['u1', 'u2']),
                                 task('verify', phase='verify'), task('review', phase='review'), task('reflect', phase='reflect')])
        evidence = tree(self.repo).docs_root / 'evidence/u2.md'
        evidence.parent.mkdir(parents=True)
        evidence.write_text('u2 observed\n')
        doc = self.apply(doc, 'task', task_id='u1', state='done')
        doc = self.apply(doc, 'task', task_id='u2', state='done', evidence=['evidence/u2.md'])
        doc = self.apply(doc, 'task', task_id='joined', state='done')
        evidence.unlink()  # u2's delivery no longer holds
        doc = self.apply(doc, 'change-type', kind='iterate', reason='narrower work')
        self.assertEqual([t['id'] for t in doc['plan']['tasks']], ['plan', 'u1'])


class ChangeTypeGitTests(SliceBase):
    def test_quick_fix_to_iterate_keeps_delivered_build_work_and_drops_a_commit_not_on_head(self):
        prepared = self.prepare()
        sha = self.work(prepared)
        self.ok({'op': 'deliver', 'op_id': 'deliver-01', 'assignment': 'build-it', 'attempt': 1, 'outcome': 'done',
                 'commits': [sha], 'stage': 'integrated'})
        mutate(self.repo, self.cid, 'task-add', task=task('gone'))
        (self.repo / 'src/c.py').write_text('c = 1\n')
        self.git('add', 'src/c.py')
        self.git('commit', '-q', '-m', 'add c\n\nCycle-Task: gone')
        later = self.git('rev-parse', 'HEAD')
        mutate(self.repo, self.cid, 'task', task_id='gone', state='done', commits=[later], stage='integrated')
        mutate(self.repo, self.cid, 'task-add', task=task('checked', phase='verify'))
        mutate(self.repo, self.cid, 'task', task_id='checked', state='done')
        self.git('reset', '-q', '--hard', sha)  # the integrated commit of `gone` leaves HEAD
        doc = mutate(self.repo, self.cid, 'change-type', kind='iterate', reason='the change needs a plan')
        self.assertEqual([(t['id'], t['status']) for t in doc['plan']['tasks']], [('plan', 'pending'), ('build-it', 'done')])
        self.assertEqual(doc['plan']['tasks'][1]['commits'], [sha])


# ───────────────────────────── approach 3: one council count across scopes ─────────────────────────────

class LogicalHistoryTests(SliceBase):
    def setUp(self):
        super().setUp()
        patcher = patch('cycle_council.commit_evidence')
        patcher.start()
        self.addCleanup(patcher.stop)
        (self.repo / '.bionic.yml').write_text('config_version: "1"\ndocs_dir: bionic\ncouncil:\n  mode: standard\n  max_attempts: 3\n')
        council_policy.initialize(self.repo, 'standard', selection='Fixture selects standard')
        self.git('add', '.bionic.yml')
        self.git('commit', '-q', '-m', 'council policy')
        self.subject = 'adrs/ADR-0001-keep.md'
        path = self.repo / 'bionic' / self.subject
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('---\nid: ADR-0001\ntitle: Keep\nstatus: Proposed\n---\n\nKeep the evidence.\n')
        self.logical = 'adr:ADR-0001'
        self.policy = council_policy.resolve(self.repo, 'adr', logical_id=self.logical)

    def scope(self, cid=None):
        return self.repo / ('bionic/adrs/councils' if cid is None else f'bionic/cycles/{cid}/councils')

    def row(self, cid, ident, minute, status='finished', policy=None, progress=None):
        directory = self.scope(cid) / 'decisions' / digest(self.logical.encode())[:24]
        directory.mkdir(parents=True, exist_ok=True)
        row = {'format': council_policy.ATTEMPT, 'id': ident, 'purpose': 'adr', 'logical_id': self.logical, 'subject': self.subject,
               'status': status, 'started_at': f'2026-11-01T00:{minute:02d}:00+00:00', 'round': 1,
               'progress': progress or f'progress {ident}', 'policy': policy or self.policy, 'record': None}
        path = directory / f'attempt-{ident}.json'
        path.write_text(json.dumps(row))
        return path

    def completed_cycle(self):
        cid = create(self.repo, 'iterate', 'Earlier', 'Earlier work', ['src'], ['Done'], 'builder', 'tester')['id']
        path = self.record_path(cid)
        raw = json.loads(path.read_text())
        raw['status'] = 'completed'
        path.write_text(json.dumps(raw))
        return cid

    def history(self, cycle_id=None):
        return cycle_council.logical_history(tree(self.repo), 'adr', self.subject, self.logical, cycle_id)

    def begin(self, cycle_id=None, progress='new progress'):
        return cycle_council.begin_mode(self.repo, 'adr', self.subject, 'Judge the decision.', cycle_id=cycle_id, progress=progress)

    def test_an_attempt_in_a_completed_cycle_counts_toward_the_standalone_limit(self):
        done = self.completed_cycle()
        self.row(done, 'aaa1', 1)
        _, _, attempt, _ = self.begin()
        self.assertEqual(attempt['round'], 2)
        self.assertEqual([r['id'] for r in attempt['history']], ['aaa1'])

    def test_the_limit_refuses_across_scopes(self):
        done = self.completed_cycle()
        self.row(done, 'aaa1', 1)
        self.row(None, 'aaa2', 2)
        self.row(self.cid, 'aaa3', 3)
        with self.assertRaisesRegex(CycleError, 'attempt limit exhausted'):
            self.begin()
        with self.assertRaisesRegex(CycleError, 'attempt limit exhausted'):
            self.begin(self.cid)

    def test_an_unresolved_attempt_in_another_active_cycle_refuses(self):
        self.row(self.cid, 'aaa1', 1, status='running')
        with self.assertRaisesRegex(CycleError, 'unresolved council attempt'):
            self.history()

    def test_an_unresolved_attempt_in_a_completed_cycle_counts_unless_its_flock_is_held(self):
        done = self.completed_cycle()
        path = self.row(done, 'aaa1', 1, status='running')
        self.assertEqual([r['id'] for r in self.history()], ['aaa1'])
        self.assertFalse(path.with_suffix('.lock').exists(), 'the reader created a lock file')
        fd = cycle_council.acquire_attempt_lock(path)
        try:
            with self.assertRaisesRegex(CycleError, 'still running'):
                self.history()
        finally:
            import os
            os.close(fd)
        self.assertEqual(len(self.history()), 1)

    def test_unreadable_and_unknown_rows_in_another_scope_are_skipped(self):
        done = self.completed_cycle()
        self.row(done, 'aaa1', 1)
        directory = self.scope(done) / 'decisions' / digest(self.logical.encode())[:24]
        (directory / 'attempt-bad.json').write_text('{not json')
        (directory / 'attempt-odd.json').write_text(json.dumps({'format': 'crux.unknown', 'purpose': 'adr', 'status': 'running'}))
        self.assertEqual([r['id'] for r in self.history()], ['aaa1'])

    def test_merged_order_frozen_policy_and_progress_follow_started_at(self):
        newest = dict(self.policy, policy_inputs=[*self.policy['policy_inputs']])
        newest['models'] = {'marker': 'newest row'}
        self.row(None, 'zzz1', 1, progress='first assessment')
        self.row(self.cid, 'aaa2', 2, policy=newest, progress='second assessment')
        self.assertEqual([r['id'] for r in self.history()], ['zzz1', 'aaa2'])
        with self.assertRaisesRegex(CycleError, 'new meaningful progress'):
            self.begin(progress='second assessment')
        # The newest merged row supplies the frozen policy the new attempt resolves from (nit F7).
        with patch.object(council_policy, 'resolve', wraps=council_policy.resolve) as resolve:
            _, _, attempt, _ = self.begin(progress='first assessment')
        self.assertEqual(resolve.call_args.kwargs['previous'], newest)
        self.assertEqual((attempt['round'], [r['id'] for r in attempt['history']]), (3, ['zzz1', 'aaa2']))

    def test_logical_history_is_limited_to_adr_and_disposition(self):
        with self.assertRaisesRegex(CycleError, 'adr and disposition'):
            cycle_council.logical_history(tree(self.repo), 'idr', self.subject, self.logical)


# ───────────────────────────── approach 5: acceptance-change ─────────────────────────────

class AcceptanceChangeTests(unittest.TestCase):
    setUp_base = fixtures.CycleTests.setUp
    cycle = fixtures.CycleTests.cycle
    apply = fixtures.CycleTests.apply

    def setUp(self):
        self.setUp_base()
        import cycle_queue
        cycle_queue.add(self.repo, 'Later', 'Measure speed later', 'iterate', ['src'], ['Fast'])
        cycle_queue.add(self.repo, 'Other', 'Other work', 'iterate', ['src'], ['Other'])
        self.doc = self.planned('iterate')
        self.cfg = tree(self.repo)

    def planned(self, kind):
        doc = self.cycle(kind)
        plan = deepcopy(doc['plan'])
        plan.update(acceptance=['Works', 'Fast', 'Small'], verification=['focused tests'],
                    tasks=[task(p, phase=p) for p in wf.PHASES[kind]])
        return self.apply(doc, 'plan', plan=plan, reason='initial plan') if 'plan' in wf.PHASES[kind] else doc

    def proposal(self, name='change', doc=None, **change):
        doc = doc or load(self.repo, self.doc['id'])
        value = {'cycle_id': doc['id'], 'plan_revision': doc['plan']['revision'], 'remove': ['Small'],
                 'move': [{'criterion': 'Fast', 'queue_item': 'Q-0001'}], 'add': ['Has a test'], **change}
        subject = f"cycles/{doc['id']}/acceptance/{name}.json"
        path = self.cfg.docs_root / subject
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))
        return {'purpose': 'acceptance-change', 'cycle_id': doc['id'], 'subject': subject, 'subject_sha256': digest(path.read_bytes())}

    def captured(self, binding, disposition='approve', ident='0001'):
        shown = owner_decision.present(self.repo, {**binding, 'op_id': f'present-{ident}', 'question': 'Change the criteria as shown?'})
        return owner_decision.capture(self.repo, {**binding, 'op_id': f'capture-{ident}', 'presentation': shown['presentation'],
                                                 'disposition': disposition, 'quote': 'Drop Small and move Fast to Q-0001.',
                                                 'source': {'kind': 'conversation', 'reference': 'session-9/message-4'},
                                                 'owner_date': '2026-11-08', 'supersedes': None})

    def apply_capture(self, binding, captured):
        return owner_decision.apply(self.repo, {**binding, 'capture': captured['capture']})

    def refused(self, code, binding, ident='0001'):
        captured = self.captured(binding, ident=ident)
        before = (self.cfg.docs_root / f"cycles/{binding['cycle_id']}/cycle.json").read_bytes()
        with self.assertRaises(owner_decision.OwnerDecisionError) as raised:
            self.apply_capture(binding, captured)
        self.assertEqual(raised.exception.code, code)
        self.assertEqual((self.cfg.docs_root / f"cycles/{binding['cycle_id']}/cycle.json").read_bytes(), before)

    def test_present_capture_apply_writes_a_plan_revision_that_cites_the_capture(self):
        binding = self.proposal()
        captured = self.captured(binding)
        result = self.apply_capture(binding, captured)
        self.assertEqual((result['applied'], result['already_applied']), (True, False))
        doc = load(self.repo, self.doc['id'])
        self.assertEqual(doc['plan']['acceptance'], ['Works', 'Has a test'])
        revised = [e for e in doc['history'] if e['action'] == 'plan-revised'][-1]
        self.assertIn(captured['capture']['path'], revised['reason'])
        self.assertIn(captured['capture']['sha256'], revised['reason'])
        self.assertEqual(revised['previous']['acceptance'], ['Works', 'Fast', 'Small'])
        self.assertEqual(captured['record']['quote'], 'Drop Small and move Fast to Q-0001.')
        replay = self.apply_capture(binding, captured)
        self.assertEqual((replay['applied'], replay['already_applied']), (True, True))
        self.assertEqual(load(self.repo, self.doc['id'])['plan'], doc['plan'])

    def test_a_retry_after_the_save_acknowledges_the_plan_revision(self):
        binding = self.proposal()
        captured = self.captured(binding)
        with patch.object(owner_decision, '_application_record', side_effect=OSError('interrupted after the save')):
            with self.assertRaises(OSError):
                self.apply_capture(binding, captured)
        revision = load(self.repo, self.doc['id'])['plan']['revision']
        replay = self.apply_capture(binding, captured)
        self.assertTrue(replay['already_applied'])
        self.assertEqual(load(self.repo, self.doc['id'])['plan']['revision'], revision)

    def test_a_pending_capture_changes_nothing(self):
        binding = self.proposal()
        captured = self.captured(binding, 'pending')
        before = (self.cfg.docs_root / f"cycles/{self.doc['id']}/cycle.json").read_bytes()
        with self.assertRaises(owner_decision.OwnerDecisionError) as raised:
            self.apply_capture(binding, captured)
        self.assertEqual(raised.exception.code, 'owner-capture-not-approved')
        self.assertEqual((self.cfg.docs_root / f"cycles/{self.doc['id']}/cycle.json").read_bytes(), before)

    def test_a_reject_capture_changes_nothing(self):
        binding = self.proposal()
        captured = self.captured(binding, 'reject')
        before = (self.cfg.docs_root / f"cycles/{self.doc['id']}/cycle.json").read_bytes()
        with self.assertRaises(owner_decision.OwnerDecisionError) as raised:
            self.apply_capture(binding, captured)
        self.assertEqual(raised.exception.code, 'owner-capture-not-approved')
        self.assertEqual((self.cfg.docs_root / f"cycles/{self.doc['id']}/cycle.json").read_bytes(), before)

    def test_a_missing_cycle_id_refuses(self):
        binding = {**self.proposal(), 'cycle_id': None}
        with self.assertRaises(owner_decision.OwnerDecisionError) as raised:
            owner_decision.present(self.repo, {**binding, 'op_id': 'present-0009', 'question': 'Change?'})
        self.assertEqual(raised.exception.code, 'acceptance-change-requires-cycle')

    def test_each_failed_check_refuses_with_its_code(self):
        revision = self.doc['plan']['revision']
        cases = [
            ('acceptance-change-stale-plan', {'plan_revision': revision - 1}),
            ('acceptance-change-criterion-not-unique', {'remove': ['Absent']}),
            ('acceptance-change-criterion-conflict', {'remove': ['Fast']}),
            ('acceptance-change-duplicate-add', {'add': ['Works']}),
            ('acceptance-change-duplicate-add', {'add': ['New', 'New']}),
            ('acceptance-change-destination-lacks-criterion', {'move': [{'criterion': 'Fast', 'queue_item': 'Q-0002'}]}),
            ('acceptance-change-destination-missing', {'move': [{'criterion': 'Fast', 'queue_item': 'Q-0099'}]}),
        ]
        for n, (code, change) in enumerate(cases):
            with self.subTest(code=code, change=change):
                self.refused(code, self.proposal(f'case-{n}', **change), ident=f'case{n:04d}')

    def test_a_criterion_occurring_twice_refuses(self):
        doc = load(self.repo, self.doc['id'])
        plan = wf.plan_file_of(doc)
        plan['acceptance'] = ['Works', 'Fast', 'Small', 'Small']
        doc = self.apply(doc, 'plan', plan=plan, reason='duplicate criterion')
        self.refused('acceptance-change-criterion-not-unique', self.proposal('twice', doc=doc))

    def test_a_started_destination_refuses(self):
        import cycle_queue
        started = {'id': 'Q-0001', 'state': 'started', 'acceptance': ['Fast']}
        with patch.object(cycle_queue, 'resolve_item', return_value=started):
            self.refused('acceptance-change-destination-started', self.proposal('started'))

    def test_a_criterion_fix_at_a_shifted_index_refuses(self):
        doc = load(self.repo, self.doc['id'])
        doc['plan']['tasks'].append(task('fix-it', phase='verify', fix={'criterion': {'index': 1}}))
        proposal = {'cycle_id': doc['id'], 'plan_revision': doc['plan']['revision'], 'remove': ['Fast'], 'move': [], 'add': []}
        with self.assertRaises(owner_decision.OwnerDecisionError) as raised:
            owner_decision._changed_acceptance(self.cfg, doc, proposal)
        self.assertEqual(raised.exception.code, 'acceptance-change-criterion-fix-shift')
        proposal['remove'] = ['Small']  # index 2 sits above the fix's index 1
        self.assertEqual(owner_decision._changed_acceptance(self.cfg, doc, proposal), ['Works', 'Fast'])

    def test_quick_fix_and_verify_phase_cycles_refuse(self):
        quick = self.cycle('quick-fix')
        self.refused('acceptance-change-phase', self.proposal('quick', doc=quick, remove=['Works'], move=[], add=['Other']))
        doc = load(self.repo, self.doc['id'])
        doc['phase'] = 'verify'
        with self.assertRaises(owner_decision.OwnerDecisionError) as raised:
            owner_decision._changed_acceptance(self.cfg, doc, {'cycle_id': doc['id'], 'plan_revision': doc['plan']['revision'],
                                                               'remove': ['Small'], 'move': [], 'add': []})
        self.assertEqual(raised.exception.code, 'acceptance-change-phase')


# ───────────────────────────── approach 6: legacy adoption ─────────────────────────────

LEGACY = '''---
id: ADR-0001
title: Keep durable evidence
status: Proposed
acceptance_format: crux.adr-acceptance.v1
governs:
- domain: evidence
  rule: Preserve evidence.
  scope: src/
  handle: ADR-0001/preserve-evidence
  provenance: authored
---

# Decision

Preserve the evidence.
'''


class AdoptTests(unittest.TestCase):
    setUp_base = adr_fixtures.DecisionPolicyTests.setUp
    council = adr_fixtures.DecisionPolicyTests.council

    def setUp(self):
        self.setUp_base()
        self.repo = self.root
        self.subject = 'adrs/ADR-0001-keep-durable-evidence.md'
        self.path = self.docs / self.subject
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(LEGACY)
        for args in (('init', '-q'), ('config', 'user.email', 't@example.com'), ('config', 'user.name', 't'),
                     ('add', '.'), ('commit', '-q', '-m', 'legacy ADR')):
            self.git(*args)

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.root), *args], check=True, capture_output=True, text=True).stdout

    def refuses(self, code):
        with self.assertRaises(dp.AdoptRefused) as raised:
            dp.adopt(self.root, self.subject)
        self.assertEqual(raised.exception.code, code)

    def test_adopt_writes_legacy_metadata_and_changes_no_adr_byte(self):
        before = self.path.read_bytes()
        result = dp.adopt(self.root, self.subject)
        self.assertEqual(self.path.read_bytes(), before)
        metadata = json.loads((self.docs / 'adrs/proposals/ADR-0001.json').read_text())
        self.assertEqual(metadata, {'format': 'crux.adr-proposal', 'adr': 'ADR-0001', 'subject': self.subject,
                                    'origin': 'legacy-adoption', 'cycle_id': None, 'creation_approval': None,
                                    'creation_subject': None, 'adopted_sha256': digest(before)})
        self.assertEqual(result['adopted_sha256'], digest(before))
        self.refuses('adopt-metadata-exists')

    def test_accept_after_adoption_requires_an_owner_capture_under_council_and_human(self):
        dp.adopt(self.root, self.subject)
        approval = self.council(self.subject)
        with self.assertRaisesRegex(CycleError, 'requires an owner capture'):
            dp.accept(self.root, self.subject, approval)
        with self.assertRaisesRegex(CycleError, 'free-text human approval'):
            dp.accept(self.root, self.subject, approval, human_approval='Owner: accept this')
        self.assertEqual(dp.frontmatter(self.path.read_text())[0]['status'], 'Proposed')
        binding = {'purpose': 'adr-acceptance', 'cycle_id': None, 'subject': self.subject, 'subject_sha256': digest(self.path.read_bytes())}
        shown = owner_decision.present(self.root, {**binding, 'op_id': 'present-0001', 'question': 'Accept this exact ADR?'})
        captured = owner_decision.capture(self.root, {**binding, 'op_id': 'capture-0001', 'presentation': shown['presentation'],
                                                      'disposition': 'approve', 'quote': 'I accept ADR-0001 as shown.',
                                                      'source': {'kind': 'conversation', 'reference': 'session-2/message-3'},
                                                      'owner_date': '2026-11-08', 'supersedes': None})
        result = owner_decision.apply(self.root, {**binding, 'capture': captured['capture'], 'approval': approval})
        self.assertTrue(result['applied'])
        receipt = dp.validate_acceptance(tree(self.root), {'path': self.subject})
        self.assertEqual(receipt['human_approval'], 'I accept ADR-0001 as shown.')

    def test_council_only_accepts_with_the_council_approval(self):
        (self.root / '.bionic.yml').write_text('config_version: "1"\ndocs_dir: bionic\nadr:\n  acceptance: council-only\n')
        dp.adopt(self.root, self.subject)
        self.assertEqual(dp.accept(self.root, self.subject, self.council(self.subject))['policy'], 'council-only')

    def test_adopt_refusals(self):
        self.path.write_text(LEGACY + 'Unreviewed edit.\n')
        self.refuses('adopt-differs-from-head')
        self.path.write_text(LEGACY)
        for name, code in (('provenance/ADR-0001.yaml', 'adopt-historical-provenance'), ('acceptances/ADR-0001.json', 'adopt-receipt-exists')):
            extra = self.docs / 'adrs' / name
            extra.parent.mkdir(parents=True, exist_ok=True)
            extra.write_text('{}')
            self.refuses(code)
            extra.unlink()
        self.path.write_text(LEGACY.replace('status: Proposed', 'status: Accepted'))
        self.git('commit', '-qam', 'accepted elsewhere')
        self.refuses('adopt-not-proposed')
        self.path.write_text(LEGACY.replace('acceptance_format: crux.adr-acceptance.v1\n', ''))
        self.git('commit', '-qam', 'no format')
        self.refuses('adopt-missing-acceptance-format')
        untracked = self.docs / 'adrs/ADR-0002-new.md'
        untracked.write_text(LEGACY.replace('ADR-0001', 'ADR-0002'))
        with self.assertRaises(dp.AdoptRefused) as raised:
            dp.adopt(self.root, 'adrs/ADR-0002-new.md')
        self.assertEqual(raised.exception.code, 'adopt-not-tracked-at-head')
        self.assertFalse((self.docs / 'adrs/proposals').exists())

    def test_cli_adopt_reports_the_refusal_code(self):
        spec = importlib.util.spec_from_file_location('decision_policy_cli', Path(dp.__file__).with_name('decision-policy.py'))
        cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(['--repo-root', str(self.root), 'adopt', '--subject', self.subject])
        self.assertEqual((code, json.loads(out.getvalue())['ok']), (0, True))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(['--repo-root', str(self.root), 'adopt', '--subject', self.subject])
        self.assertEqual((code, json.loads(out.getvalue())['code']), (1, 'adopt-metadata-exists'))


if __name__ == '__main__':
    unittest.main()
