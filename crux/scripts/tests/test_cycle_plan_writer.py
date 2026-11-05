"""Engine bookkeeping for the Plan phase and the review scope (CYC-0096 build-bookkeeping, stream C).

Records are synthesized in a temporary git repository; no development-tree surface is read.
"""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from unittest.mock import patch
import cycle_ops
from cycle_workflow import CycleError, PHASES, RELEASE_LISTS, check_plan_file, check_review, create, load, mutate, read_retained, tree, validate


def task_def(tid, phase, depends_on=(), status='pending'):
    return {'id': tid, 'phase': phase, 'description': tid, 'depends_on': list(depends_on), 'status': status, 'expected_evidence': ['x']}


class PlanBase(unittest.TestCase):
    kind = 'iterate'

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        (self.repo / 'bionic').mkdir()
        (self.repo / 'bionic/manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\nadr:\n  next_number: 1\n')
        (self.repo / 'bionic/objectives.md').write_text('Mission: useful changes.')
        (self.repo / 'src').mkdir(); (self.repo / 'src/a.py').write_text('x = 1\n')
        self.git('init', '-q', '-b', 'main')
        self.git('config', 'user.email', 't@example.invalid'); self.git('config', 'user.name', 'T')
        self.git('add', '.'); self.git('commit', '-qm', 'baseline')
        self.cid = create(self.repo, self.kind, 'Change', 'Goal', ['src'], ['Works'], 'dev', 'lead')['id']

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], text=True, stderr=subprocess.STDOUT).strip()

    def doc(self):
        return load(self.repo, self.cid)

    def do(self, action, **args):
        return mutate(self.repo, self.cid, action, **args)

    def file_plan(self, tasks):
        plan = deepcopy(self.doc()['plan'])
        plan.update(verification=['t'], tasks=tasks)
        return plan

    def statuses(self):
        return {t['id']: t['status'] for t in self.doc()['plan']['tasks']}


class SeededPlanTaskTests(PlanBase):
    def test_a_new_iterate_cycle_offers_prepare_dispatch_for_the_plan_task(self):
        tasks = self.doc()['plan']['tasks']
        self.assertEqual([(t['id'], t['phase'], t['status']) for t in tasks], [('plan', 'plan', 'pending')])
        seen = cycle_ops.inspect_state(self.repo, self.cid, {})
        offered = [a for a in seen['actions'] if a.get('request', {}).get('op') == 'prepare-dispatch']
        self.assertEqual([a['request']['task_id'] for a in offered], ['plan'])

    def test_every_type_with_a_plan_phase_seeds_it_and_the_others_do_not(self):
        for kind, phases in PHASES.items():
            if kind == 'release':
                continue
            with self.subTest(kind=kind):
                cid = create(self.repo, kind, 'T', 'G', ['src'], ['A'], 'dev', 'lead')['id']
                seeded = [t['id'] for t in load(self.repo, cid)['plan']['tasks']]
                self.assertEqual(seeded, ['plan'] if phases[0] == 'plan' else [])
        cid = create(self.repo, 'release', 'R', 'G', ['src'], ['A'], 'dev', 'lead', release_list='beta')['id']
        self.assertEqual([t['id'] for t in load(self.repo, cid)['plan']['tasks']], [t[0] for t in RELEASE_LISTS['beta']])

    def test_a_plan_file_that_omits_a_seeded_task_holding_an_attempt_keeps_it(self):
        self.do('assignment', id='plan-it', state='running', role='architect', agent='a1', task='plan', result_path='/tmp/r.md')
        self.assertEqual(self.doc()['assignments'][0]['task'], 'plan')
        self.do('plan', plan=self.file_plan([task_def('A', 'build')]), reason='plan')
        self.assertEqual(sorted(self.statuses()), ['A', 'plan'])
        validate(self.doc())

    def test_a_plan_file_that_omits_the_seeded_task_without_an_attempt_drops_it(self):
        self.do('plan', plan=self.file_plan([task_def('A', 'build')]), reason='plan')
        self.assertEqual(sorted(self.statuses()), ['A'])


class ChangeTypeSeedTests(PlanBase):
    kind = 'quick-fix'

    def test_a_change_into_a_type_with_a_plan_phase_seeds_the_plan_task(self):
        self.assertEqual(self.doc()['plan']['tasks'], [])
        self.do('change-type', kind='iterate', reason='needs a plan')
        self.assertEqual([(t['id'], t['phase'], t['status']) for t in self.doc()['plan']['tasks']], [('plan', 'plan', 'pending')])

    def test_a_dropped_plan_task_with_an_attempt_and_no_recorded_task_does_not_crash(self):
        self.do('change-type', kind='iterate', reason='needs a plan')
        doc = self.doc(); doc['plan']['tasks'] = []
        doc.setdefault('assignments', []).append({'task': 'plan'})
        plan = self.file_plan([task_def('A', 'plan'), task_def('B', 'build', ['A']), task_def('C', 'test', ['B']),
                               task_def('D', 'review', ['C']), task_def('E', 'reflect', ['D'])])
        with patch('cycle_workflow.load', return_value=doc):
            try:
                self.do('plan', plan=plan, reason='replan')
            except CycleError:
                pass
            except StopIteration:
                self.fail('a missing recorded plan task raised StopIteration')


class PlanFileDoneTests(PlanBase):
    def tasks(self, **status):
        return [task_def('plan', 'plan', status=status.get('plan', 'pending')), task_def('A', 'build', ['plan'], status=status.get('A', 'pending'))]

    def test_a_plan_file_marks_a_plan_task_done_and_replan_keeps_it(self):
        self.do('plan', plan=self.file_plan(self.tasks(plan='done')), reason='plan')
        self.assertEqual(self.statuses(), {'plan': 'done', 'A': 'pending'})
        # Resubmitting the same file keeps the status; changing a description does not reopen a task the file marks done.
        changed = self.tasks(plan='done'); changed[0]['description'] = 'rewritten'
        self.do('plan', plan=self.file_plan(changed), reason='again')
        self.assertEqual(self.statuses()['plan'], 'done')
        # A file that says pending and changes nothing keeps the recorded status; changing content reopens the task.
        same = self.tasks(); same[0]['description'] = 'rewritten'
        self.do('plan', plan=self.file_plan(same), reason='pending')
        self.assertEqual(self.statuses()['plan'], 'done')
        self.do('plan', plan=self.file_plan(self.tasks()), reason='edit')
        self.assertEqual(self.statuses()['plan'], 'pending')

    def test_no_plan_task_is_unmet_after_the_plan_file_marks_it_done(self):
        self.do('plan', plan=self.file_plan([task_def('plan', 'plan', status='done')]), reason='plan')
        unmet = cycle_ops.inspect_state(self.repo, self.cid, {})['unmet']['next']
        self.assertFalse([u for u in unmet if 'plan' in json.dumps(u) and 'task' in json.dumps(u).lower() and 'pending' in json.dumps(u).lower()], unmet)
        self.assertEqual(self.statuses(), {'plan': 'done'})

    def test_done_is_refused_on_a_non_plan_task(self):
        with self.assertRaisesRegex(CycleError, r'plan task A carries status done'):
            self.do('plan', plan=self.file_plan(self.tasks(A='done')), reason='plan')

    def test_done_is_refused_outside_the_plan_phase(self):
        path = self.repo / 'bionic/cycles' / self.cid / 'cycle.json'
        raw = json.loads(path.read_text()); raw['phase'] = 'build'
        path.write_text(json.dumps(raw, indent=2) + '\n')
        with self.assertRaisesRegex(CycleError, r'plan task plan carries status done'):
            self.do('plan', plan=self.file_plan(self.tasks(plan='done')), reason='plan')

    def test_delivery_fields_stay_refused_with_done(self):
        tasks = self.tasks(plan='done'); tasks[0]['note'] = 'n'
        with self.assertRaisesRegex(CycleError, r'carries .*note'):
            self.do('plan', plan=self.file_plan(tasks), reason='plan')

    def test_done_with_an_incomplete_dependency_is_refused(self):
        tasks = [task_def('A', 'build'), task_def('plan', 'plan', ['A'], status='done')]
        with self.assertRaisesRegex(CycleError, r'dependencies'):
            self.do('plan', plan=self.file_plan(tasks), reason='plan')

    def test_without_the_record_the_check_keeps_the_old_refusal(self):
        with self.assertRaisesRegex(CycleError, r'plan task plan carries status done.*`task` command'):
            check_plan_file({'tasks': [task_def('plan', 'plan', status='done')]})


class ReviewScopeDefaultTests(PlanBase):
    def review_ready(self):
        """Move to Review with the Plan, Build and Test tasks absent so a review is recordable."""
        path = self.repo / 'bionic/cycles' / self.cid / 'cycle.json'
        raw = json.loads(path.read_text()); raw['phase'] = 'review'
        path.write_text(json.dumps(raw, indent=2) + '\n')

    def report(self, **extra):
        return {'reviewer': 'someone-else', 'evidence': ['looked'], 'blocking': [], 'advisory': [], 'cosmetic': [], 'verdict': 'approve',
                'rationale': 'fine', **extra}

    def test_a_review_without_scope_records_the_plan_scope(self):
        self.review_ready()
        with patch('cycle_workflow.check_tests'):  # test evidence is not what this test is about
            self.do('review', report=self.report())
        doc = self.doc()
        cfg = tree(self.repo)
        saved = read_retained(cfg, doc['reviews'][-1])
        self.assertEqual(saved['scope'], ['src'])
        self.assertEqual(check_review(cfg, doc)['scope'], ['src'])  # the recorded review binds

    def test_an_explicit_scope_is_checked_as_before(self):
        self.review_ready()
        with self.assertRaisesRegex(CycleError, 'review scope must equal the declared scope'):
            self.do('review', report=self.report(scope=['other']))


class BetaPrepareTextTests(PlanBase):
    OLD = 'Bind this cycle to the beta target and freeze the artifact'

    def test_a_new_beta_list_describes_prepare_as_checking_the_prep(self):
        cid = create(self.repo, 'release', 'R', 'G', ['src'], ['A'], 'dev', 'lead', release_list='beta')['id']
        prepare = next(t for t in load(self.repo, cid)['plan']['tasks'] if t['id'] == 'prepare')
        self.assertEqual(prepare['description'], 'Bind this cycle to the beta target and check the prep')

    def test_a_record_with_the_old_text_still_validates(self):
        cid = create(self.repo, 'release', 'R', 'G', ['src'], ['A'], 'dev', 'lead', release_list='beta')['id']
        doc = load(self.repo, cid)
        next(t for t in doc['plan']['tasks'] if t['id'] == 'prepare')['description'] = self.OLD
        self.assertIs(validate(doc), doc)


if __name__ == '__main__':
    unittest.main()
