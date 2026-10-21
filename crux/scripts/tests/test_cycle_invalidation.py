"""Return, resume and replan invalidate only the delivered work they affect.

Records are synthesized in a temporary git repository; no development-tree surface is read.
"""
from copy import deepcopy
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cycle_workflow import CycleError, PHASES, create, load, mutate, review_basis_digest, tree, DELIVERY_FIELDS

SKILL = Path(__file__).resolve().parents[2] / 'skills/cycle'
RETURN = dict(improved='isolated', unresolved='one defect', next_change='fix it', justification='cause found', progress=True)


def task_def(tid, phase, depends_on=(), description=None, evidence=('x',)):
    return {'id': tid, 'phase': phase, 'description': description or tid, 'depends_on': list(depends_on), 'status': 'pending', 'expected_evidence': list(evidence)}


class InvalidationBase(unittest.TestCase):
    kind = 'iterate'

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        (self.repo / 'bionic').mkdir()
        (self.repo / 'bionic/manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\nadr:\n  next_number: 1\n')
        (self.repo / 'bionic/objectives.md').write_text('Mission: useful changes.')
        (self.repo / 'bionic/ev.md').write_text('evidence one\n')
        (self.repo / 'bionic/ev2.md').write_text('evidence two\n')
        (self.repo / 'src').mkdir(); (self.repo / 'src/a.py').write_text('x = 1\n')
        self.git('init', '-q', '-b', 'main')
        self.git('config', 'user.email', 't@example.invalid'); self.git('config', 'user.name', 'T')
        self.git('add', '.'); self.git('commit', '-qm', 'baseline')
        self.cid = create(self.repo, self.kind, 'Change', 'Goal', ['src'], ['Works'], 'dev', 'lead')['id']

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], text=True, stderr=subprocess.STDOUT).strip()

    def commit(self, name):
        (self.repo / f'{name}.txt').write_text(name)
        self.git('add', f'{name}.txt'); self.git('commit', '-qm', name)
        return self.git('rev-parse', 'HEAD')

    def doc(self):
        return load(self.repo, self.cid)

    def task(self, tid):
        return next(t for t in self.doc()['plan']['tasks'] if t['id'] == tid)

    def do(self, action, **args):
        return mutate(self.repo, self.cid, action, **args)

    def file_plan(self, tasks, **extra):
        plan = deepcopy(self.doc()['plan'])
        plan.update(verification=['t'], tasks=tasks, **extra)
        return plan

    def default_tasks(self):
        return [task_def(p, p) for p in PHASES[self.kind] if p != 'build'] + [task_def('A', 'build'), task_def('B', 'build', ['A'])]

    def set_plan(self, tasks=None, reason='plan'):
        return self.do('plan', plan=self.file_plan(tasks or self.default_tasks()), reason=reason)

    def as_file(self):
        """The recorded tasks projected to plan-file shape: content only, status pending."""
        return [{**{k: deepcopy(t[k]) for k in ('id', 'phase', 'description', 'depends_on', 'expected_evidence')}, 'status': 'pending'} for t in self.doc()['plan']['tasks']]

    def resubmit(self, change=None, drop=(), reason='replan'):
        """The recorded plan as a plan file (content only), optionally changed per task id."""
        tasks = []
        for t in self.doc()['plan']['tasks']:
            if t['id'] in drop:
                continue
            f = {k: deepcopy(t[k]) for k in ('id', 'phase', 'description', 'depends_on', 'expected_evidence')}
            f['status'] = 'pending'
            f.update((change or {}).get(t['id'], {}))
            tasks.append(f)
        return self.do('plan', plan=self.file_plan(tasks), reason=reason)

    def deliver(self, tid, name=None, evidence='ev.md', state='done'):
        sha = self.commit(name or f'c-{tid}')
        self.do('task', task_id=tid, commits=[sha], stage='integrated', evidence=[evidence], state=state)
        return sha

    def set_phase(self, phase):
        path = self.repo / 'bionic/cycles' / self.cid / 'cycle.json'
        doc = json.loads(path.read_text()); doc['phase'] = phase
        path.write_text(json.dumps(doc, indent=2) + '\n')

    def statuses(self):
        return {t['id']: t['status'] for t in self.doc()['plan']['tasks']}

    def delivered_phase(self, phase='test'):
        """Plan set, A and B delivered, every other task done, cycle in `phase`."""
        self.set_plan()
        a = self.deliver('A'); b = self.deliver('B')
        for t in self.doc()['plan']['tasks']:
            if t['phase'] != 'build':
                self.do('task', task_id=t['id'], state='done')
        self.set_phase(phase)
        return a, b


class ReturnTests(InvalidationBase):
    def test_counted_return_on_iterate_keeps_build_and_resets_the_rest(self):
        a, b = self.delivered_phase('review')
        prior = deepcopy(self.doc()['plan'])
        doc = self.do('return', **RETURN)
        self.assertEqual((doc['pass'], doc['phase'], doc['status']), (2, 'plan', 'active'))
        self.assertEqual(self.statuses(), {'plan': 'pending', 'test': 'pending', 'review': 'pending', 'reflect': 'pending', 'A': 'done', 'B': 'done'})
        for tid, sha in (('A', a), ('B', b)):
            t = self.task(tid)
            self.assertEqual((t['commits'], t['stage'], t['evidence']), ([sha], 'integrated', ['ev.md']))
        requested = [e for e in doc['history'] if e['action'] == 'return-requested'][-1]
        self.assertEqual(requested['plan'], prior)

    def test_pausing_return_resets_nothing_and_resume_after_pass_limit_applies_the_rule(self):
        a, _ = self.delivered_phase('review')
        self.do('return', **RETURN); self.set_phase('review')
        before = self.statuses()
        self.assertEqual(before['A'], 'done')
        for tid in ('plan', 'test', 'review'):
            self.do('task', task_id=tid, state='done')
        doc = self.do('return', **RETURN)  # pass 2 of 2: pauses
        self.assertEqual((doc['status'], doc['blocker']['reason']), ('paused', 'pass-limit'))
        self.assertEqual(self.statuses(), {'plan': 'done', 'test': 'done', 'review': 'done', 'reflect': 'pending', 'A': 'done', 'B': 'done'})
        self.do('extend', limit=3, human_approval='Owner: one more pass')
        doc = self.do('resume', reason='approved')
        self.assertEqual(doc['pass'], 3)
        self.assertEqual(self.statuses(), {'plan': 'pending', 'test': 'pending', 'review': 'pending', 'reflect': 'pending', 'A': 'done', 'B': 'done'})
        self.assertEqual(self.task('A')['commits'], [a])

    def test_resume_after_progress_stalled_applies_the_rule(self):
        self.delivered_phase('test')
        doc = self.do('return', **{**RETURN, 'progress': False})
        self.assertEqual(doc['blocker']['reason'], 'progress-stalled')
        self.assertEqual(self.statuses()['test'], 'done'); self.assertEqual(self.statuses()['A'], 'done')
        doc = self.do('resume', reason='new cause', new_evidence='reproduction')
        self.assertEqual(doc['pass'], 2)
        self.assertEqual(self.statuses(), {'plan': 'pending', 'test': 'pending', 'review': 'pending', 'reflect': 'pending', 'A': 'done', 'B': 'done'})

    def test_resume_after_another_blocker_changes_no_task(self):
        self.delivered_phase('test')
        before = deepcopy(self.doc()['plan']['tasks'])
        self.do('pause', reason='waiting for the owner')
        doc = self.do('resume', reason='owner answered')
        self.assertEqual((doc['pass'], doc['phase'], doc['status']), (1, 'test', 'active'))
        self.assertEqual(doc['plan']['tasks'], before)

    def test_quick_fix_resume_after_a_return_resets_every_task(self):
        self.kind = 'quick-fix'
        self.cid = create(self.repo, 'quick-fix', 'Fix', 'Goal', ['src'], ['Works'], 'dev', 'lead')['id']
        self.do('task-add', task={**task_def('fix', 'build')})
        self.do('task', task_id='fix', commits=[self.commit('q1')], stage='integrated', evidence=['ev.md'], state='done')
        self.set_phase('test')
        doc = self.do('return', **RETURN)
        self.assertEqual(doc['status'], 'paused')
        self.do('extend', limit=2, human_approval='Owner: one more pass')
        doc = self.do('resume', reason='approved')
        self.assertEqual((doc['pass'], doc['phase']), (2, 'build'))
        self.assertEqual(self.task('fix')['status'], 'pending')

    def test_quick_fix_counted_return_after_an_extension_resets_every_task(self):
        self.cid = create(self.repo, 'quick-fix', 'Fix', 'Goal', ['src'], ['Works'], 'dev', 'lead')['id']
        self.do('task-add', task={**task_def('fix', 'build')})
        self.do('task', task_id='fix', commits=[self.commit('q2')], stage='integrated', evidence=['ev.md'], state='done')
        self.set_phase('test')
        self.do('extend', limit=3, human_approval='Owner: more passes')
        doc = self.do('return', **RETURN)
        self.assertEqual((doc['pass'], doc['status'], doc['phase']), (2, 'active', 'build'))
        self.assertEqual(self.task('fix')['status'], 'pending')

    def test_integrated_commit_off_head_makes_the_task_affected(self):
        a, b = self.delivered_phase('test')
        self.git('reset', '-q', '--hard', 'HEAD~1')  # b is no longer an ancestor of HEAD
        self.do('return', **RETURN)
        affected, kept = self.task('B'), self.task('A')
        self.assertEqual((affected['status'], 'stage' in affected), ('pending', False))
        self.assertEqual((affected['commits'], affected['evidence']), ([b], ['ev.md']))
        self.assertEqual((kept['status'], kept['stage']), ('done', 'integrated'))

    def test_missing_evidence_file_makes_the_task_affected_even_when_integrated_holds(self):
        self.delivered_phase('test')
        (self.repo / 'bionic/ev.md').unlink()
        self.do('return', **RETURN)
        t = self.task('A')
        self.assertEqual((t['status'], 'stage' in t, t['evidence'], len(t['commits'])), ('pending', False, ['ev.md'], 1))

    def test_missing_evidence_on_a_non_integrated_task_makes_it_affected(self):
        self.set_plan()
        sha = self.commit('imp')
        self.do('task', task_id='A', commits=[sha], stage='implemented', evidence=['ev.md'], state='done')
        self.set_phase('test')
        (self.repo / 'bionic/ev.md').unlink()
        self.do('return', **RETURN)
        t = self.task('A')
        self.assertEqual((t['status'], 'stage' in t, t['evidence'], t['commits']), ('pending', False, ['ev.md'], [sha]))

    def test_non_integrated_task_with_off_head_commit_is_not_affected_by_ancestry(self):
        self.set_plan()
        self.git('checkout', '-q', '-b', 'side')
        sha = self.commit('side')
        self.git('checkout', '-q', 'main')
        self.do('task', task_id='A', commits=[sha], stage='implemented', state='done')
        self.set_phase('test')
        self.do('return', **RETURN)
        self.assertEqual((self.task('A')['status'], self.task('A')['stage']), ('done', 'implemented'))

    def test_vanished_commit_object_is_affected_not_a_refusal(self):
        self.set_plan()
        sha = self.deliver('A')
        self.git('reset', '-q', '--hard', 'HEAD~1')
        self.git('reflog', 'expire', '--expire=now', '--all'); self.git('gc', '-q', '--prune=now')
        with self.assertRaises(subprocess.CalledProcessError):
            self.git('cat-file', '-e', sha)  # the object is gone, so the git check errors
        self.set_phase('test')
        doc = self.do('return', **RETURN)
        t = self.task('A')
        self.assertEqual((doc['pass'], t['status'], 'stage' in t, t['commits']), (2, 'pending', False, [sha]))


class ReplanTests(InvalidationBase):
    def test_identical_plan_keeps_status_and_delivery_including_an_active_plan_task(self):
        self.set_plan()
        self.do('task', task_id='plan', state='active', assignee='dev-1')
        a = self.deliver('A')
        before = deepcopy(self.doc()['plan']['tasks'])
        doc = self.resubmit()
        self.assertEqual(doc['plan']['tasks'], before)
        self.assertEqual(self.task('plan')['status'], 'active'); self.assertEqual(self.task('A')['commits'], [a])

    def test_each_changed_field_reopens_a_build_task_and_keeps_its_delivery(self):
        changes = {
            'phase': {'phase': 'test'},
            'description': {'description': 'A, redone'},
            'expected_evidence': {'expected_evidence': ['x', 'the finding regression']},
            'depends_on': {'depends_on': ['plan']},
        }
        for field, change in changes.items():
            with self.subTest(field=field):
                self.tearDown_and_setUp()
                self.set_plan()
                sha = self.deliver('A'); self.do('task', task_id='A', assignee='dev-1', result_path='/tmp/r.md', note='kept note')
                other = self.deliver('B', name='c-B')
                self.resubmit({'A': change})
                t = self.task('A')
                self.assertEqual((t['status'], 'stage' in t), ('pending', False), field)
                self.assertEqual((t['commits'], t['evidence'], t['assignee'], t['result_path'], t['note']), ([sha], ['ev.md'], 'dev-1', '/tmp/r.md', 'kept note'))
                self.assertEqual((self.task('B')['status'], self.task('B')['stage']), ('done', 'integrated'), 'not transitive')
                self.assertEqual(self.task('B')['commits'], [other])

    def tearDown_and_setUp(self):
        self.temp.cleanup(); self.setUp()

    def test_reordering_depends_on_counts_as_a_change(self):
        self.set_plan([task_def('plan', 'plan'), task_def('A', 'build'), task_def('C', 'build'), task_def('B', 'build', ['A', 'C'])])
        self.deliver('A'); self.deliver('C'); self.deliver('B')
        self.resubmit({'B': {'depends_on': ['C', 'A']}})
        self.assertEqual(self.task('B')['status'], 'pending')
        self.assertEqual(self.task('A')['status'], 'done')

    def test_new_id_starts_pending_and_omitted_task_stays_in_the_previous_snapshot(self):
        self.set_plan()
        sha = self.deliver('A')
        doc = self.do('plan', plan=self.file_plan([task_def('plan', 'plan'), task_def('A2', 'build')]), reason='rename A')
        ids = [t['id'] for t in doc['plan']['tasks']]
        self.assertEqual(ids, ['plan', 'A2'])
        self.assertEqual(self.task('A2')['status'], 'pending'); self.assertFalse(any(k in self.task('A2') for k in DELIVERY_FIELDS))
        previous = [e for e in doc['history'] if e['action'] == 'plan-revised'][-1]['previous']
        old = next(t for t in previous['tasks'] if t['id'] == 'A')
        self.assertEqual((old['commits'], old['evidence'], old['status']), ([sha], ['ev.md'], 'done'))

    def test_readded_id_starts_fresh_and_can_be_delivered(self):
        self.set_plan()
        old = self.deliver('A')
        self.resubmit(drop=('A', 'B'))
        self.assertNotIn('A', self.statuses())
        self.do('plan', plan=self.file_plan([*self.as_file(), task_def('A', 'build')]), reason='back')
        t = self.task('A')
        self.assertEqual(t['status'], 'pending'); self.assertFalse(any(k in t for k in DELIVERY_FIELDS))
        new = self.deliver('A', name='again')
        self.assertEqual((self.task('A')['status'], self.task('A')['commits']), ('done', [new]))
        self.assertNotIn(old, self.task('A')['commits'])

    def test_revalidation_failure_during_a_replan_reopens_the_task(self):
        self.set_plan()
        sha = self.deliver('A')
        self.git('reset', '-q', '--hard', 'HEAD~1')
        self.resubmit()
        t = self.task('A')
        self.assertEqual((t['status'], 'stage' in t, t['commits'], t['evidence']), ('pending', False, [sha], ['ev.md']))

    def test_vanished_commit_during_a_replan_is_not_a_refusal(self):
        self.set_plan()
        sha = self.deliver('A')
        self.git('reset', '-q', '--hard', 'HEAD~1')
        self.git('reflog', 'expire', '--expire=now', '--all'); self.git('gc', '-q', '--prune=now')
        self.resubmit()
        self.assertEqual((self.task('A')['status'], self.task('A')['commits']), ('pending', [sha]))

    def test_identical_resubmission_over_a_record_written_by_an_earlier_writer(self):
        self.set_plan()
        sha = self.commit('earlier')
        path = self.repo / 'bionic/cycles' / self.cid / 'cycle.json'
        raw = json.loads(path.read_text())
        # An earlier writer could keep delivery fields on a non-build task and in plan snapshots.
        for t in raw['plan']['tasks']:
            if t['id'] == 'test':
                t.update(status='done', commits=[sha], stage='implemented', evidence=['ev.md'], assignee='old', note='n')
        path.write_text(json.dumps(raw, indent=2) + '\n')
        self.assertEqual(self.task('test')['status'], 'done')  # still loads and validates
        before = deepcopy(self.task('test'))
        self.resubmit()
        self.assertEqual(self.task('test'), before)


class PlanFileTests(InvalidationBase):
    def test_status_other_than_pending_is_refused_naming_task(self):
        tasks = self.default_tasks(); tasks[0]['status'] = 'done'
        with self.assertRaisesRegex(CycleError, r'plan task plan carries status done.*`task` command'):
            self.set_plan(tasks)

    def test_every_delivery_field_is_refused_naming_task(self):
        values = {'assignee': 'dev', 'result_path': 'r.md', 'commits': ['a' * 40], 'evidence': ['ev.md'], 'stage': 'implemented', 'note': 'n',
                  'replaced_commits': [{'from': 'a' * 40, 'to': 'b' * 40, 'at': 't', 'note': 'n'}]}
        self.assertEqual(set(values), set(DELIVERY_FIELDS))
        for field, value in values.items():
            with self.subTest(field=field):
                tasks = self.default_tasks(); tasks[0][field] = value
                with self.assertRaisesRegex(CycleError, rf'carries {field}.*`task` command'):
                    self.set_plan(tasks)
        self.assertEqual(self.doc()['plan']['revision'], 1)

    def test_refusal_covers_plan_input_only_stored_delivery_still_loads(self):
        self.set_plan()
        sha = self.deliver('A')
        # The stored record carries delivery fields, status done, and loads and validates.
        self.assertEqual(self.task('A')['status'], 'done'); self.assertEqual(self.task('A')['commits'], [sha])
        snapshot_doc = self.resubmit()
        previous = [e for e in snapshot_doc['history'] if e['action'] == 'plan-revised'][-1]['previous']
        self.assertEqual(next(t for t in previous['tasks'] if t['id'] == 'A')['status'], 'done')
        self.assertEqual(load(self.repo, self.cid)['id'], self.cid)

    def test_documented_example_plans_are_accepted(self):
        found = 0
        for path in (SKILL / 'references/commands.md', SKILL / 'SKILL.md'):
            for block in re.findall(r'```json\n(.*?)```', path.read_text(), re.S):
                example = json.loads(block)
                if not (isinstance(example, dict) and 'depends_on' in example) and not (isinstance(example, dict) and 'tasks' in example):
                    continue
                found += 1
                tasks = example['tasks'] if 'tasks' in example else [example]
                self.tearDown_and_setUp()
                doc = self.do('plan', plan=self.file_plan(tasks), reason='documented example')
                self.assertEqual([t['id'] for t in doc['plan']['tasks']], [t['id'] for t in tasks])
        self.assertGreaterEqual(found, 1)

    def tearDown_and_setUp(self):
        self.temp.cleanup(); self.setUp()


class ReopenAndCompleteTests(InvalidationBase):
    def reopened(self):
        self.set_plan()
        self.a = self.deliver('A'); self.deliver('B')
        self.resubmit({'A': {'description': 'A, with the finding regression'}})

    def test_reopened_integrated_task_records_a_new_commit_then_integrates(self):
        self.reopened()
        new = self.commit('rework')
        self.do('task', task_id='A', commits=[new], stage='implemented')
        t = self.task('A')
        self.assertEqual((t['stage'], t['commits']), ('implemented', [self.a, new]))
        doc = self.do('task', task_id='A', stage='integrated', state='done')
        self.assertEqual((self.task('A')['stage'], self.task('A')['status']), ('integrated', 'done'))

    def test_done_task_whose_dependency_was_reopened_accepts_updates_and_validates(self):
        self.reopened()
        self.assertEqual((self.task('A')['status'], self.task('B')['status']), ('pending', 'done'))
        self.do('task', task_id='B', note='still fine')
        self.do('task', task_id='B', evidence=['ev2.md'])
        self.assertEqual(self.task('B')['evidence'], ['ev.md', 'ev2.md'])
        self.assertEqual(self.doc()['id'], self.cid)

    def test_identical_plan_after_delivery_keeps_statuses_and_the_review_basis(self):
        self.set_plan()
        self.deliver('A'); self.deliver('B')
        digest = review_basis_digest(self.doc(), 3)
        self.resubmit()
        self.assertEqual((self.task('A')['status'], self.task('B')['status']), ('done', 'done'))
        self.assertEqual(review_basis_digest(self.doc(), 3), digest)

    def test_missing_evidence_recovers_by_restoring_the_file(self):
        self.set_plan(); self.deliver('A')
        (self.repo / 'bionic/ev.md').unlink()
        self.resubmit()
        self.assertEqual(self.task('A')['status'], 'pending')
        (self.repo / 'bionic/ev.md').write_text('restored\n')
        self.do('task', task_id='A', stage='integrated', state='done')
        self.assertEqual(self.task('A')['status'], 'done')

    def test_missing_evidence_recovers_by_recording_a_replacement(self):
        self.set_plan(); self.deliver('A')
        (self.repo / 'bionic/ev.md').unlink()
        self.resubmit()
        # The missing entry stays recorded; the replacement is added beside it and the task completes.
        self.do('task', task_id='A', evidence=['ev2.md'], stage='integrated', state='done')
        self.assertEqual((self.task('A')['status'], self.task('A')['evidence']), ('done', ['ev.md', 'ev2.md']))

    def test_rebased_commit_recovers_through_replace_commit(self):
        self.set_plan()
        old = self.deliver('A')
        self.git('commit', '-q', '--amend', '-m', 'rebased')
        new = self.git('rev-parse', 'HEAD')
        self.resubmit()
        self.assertEqual((self.task('A')['status'], 'stage' in self.task('A')), ('pending', False))
        self.do('task', task_id='A', replace_commit=[old, new], note='rebased onto main')
        self.do('task', task_id='A', stage='integrated', state='done')
        t = self.task('A')
        self.assertEqual((t['status'], t['stage'], t['commits']), ('done', 'integrated', [new]))

    def test_vanished_commit_recovers_through_replace_commit(self):
        self.set_plan()
        old = self.deliver('A')
        self.git('reset', '-q', '--hard', 'HEAD~1')
        self.git('reflog', 'expire', '--expire=now', '--all'); self.git('gc', '-q', '--prune=now')
        new = self.commit('redo')
        self.resubmit()
        self.do('task', task_id='A', replace_commit=[old, new], note='original commit was lost')
        self.do('task', task_id='A', stage='integrated', state='done')
        self.assertEqual((self.task('A')['status'], self.task('A')['commits']), ('done', [new]))

    def test_omit_then_readd_a_task_delivers_it_fresh(self):
        self.set_plan(); self.deliver('A')
        self.resubmit(drop=('A', 'B'))
        self.do('plan', plan=self.file_plan([*self.as_file(), task_def('A', 'build')]), reason='again')
        self.deliver('A', name='fresh')
        self.assertEqual(self.task('A')['status'], 'done')


class PreservationTests(InvalidationBase):
    def references(self, doc):
        commits, evidence = set(), set()
        def collect(task):
            commits.update(task.get('commits', [])); evidence.update(task.get('evidence', []))
            commits.update(r['from'] for r in task.get('replaced_commits', []))
        for t in doc['plan']['tasks']:
            collect(t)
        for e in doc['history']:
            for plan in (e.get('previous'), e.get('plan')):
                for t in (plan or {}).get('tasks', []):
                    collect(t)
        return commits, evidence

    def test_history_only_grows_and_no_commit_or_evidence_reference_is_lost(self):
        self.set_plan()
        self.deliver('A'); old = self.deliver('B', evidence='ev2.md')
        self.git('commit', '-q', '--amend', '-m', 'rebased', '--allow-empty')
        new = self.git('rev-parse', 'HEAD')
        self.do('task', task_id='B', replace_commit=[old, new], note='rebased')
        steps = [
            lambda: self.set_phase('test') or self.do('return', **{**RETURN, 'progress': False}),
            lambda: self.do('resume', reason='new', new_evidence='cause'),
            lambda: self.resubmit({'A': {'description': 'A, changed'}}, drop=('B',)),
            lambda: self.do('plan', plan=self.file_plan([*self.as_file(), task_def('B', 'build')]), reason='re-add'),
        ]
        for step in steps:
            before = self.doc()
            commits_before, evidence_before = self.references(before)
            after = step()
            self.assertEqual(after['history'][:len(before['history'])], before['history'])
            self.assertGreater(len(after['history']), len(before['history']))
            commits_after, evidence_after = self.references(after)
            self.assertLessEqual(commits_before, commits_after)
            self.assertLessEqual(evidence_before, evidence_after)
        self.assertIn(old, self.references(self.doc())[0])


if __name__ == '__main__':
    unittest.main()
