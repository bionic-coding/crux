"""ADR dependencies: a cycle ADR that awaits acceptance blocks only the tasks that name it (CYC-0121 unit-workflow).

IDR closure-and-decision-gates approach 7. Records are synthesized in a temporary git repository: the cycle ADR is
injected into the record, because creating one through the writer needs a council justification this test is not about.
"""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle_ops
from cycle_workflow import CycleError, adr_dependency_problems, check_decisions, create, load, mutate, requirements, tree

ADR = 'wait-for-me'


def task_def(tid, phase, adr=(), status='pending'):
    task = {'id': tid, 'phase': phase, 'description': tid, 'depends_on': [], 'status': status, 'expected_evidence': ['x']}
    if adr:
        task['adr_dependencies'] = list(adr)
    return task


class AdrBase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        (self.repo / 'bionic/adrs').mkdir(parents=True)
        (self.repo / 'bionic/manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\nadr:\n  next_number: 1\n')
        (self.repo / 'bionic/objectives.md').write_text('Mission: useful changes.')
        (self.repo / 'src').mkdir(); (self.repo / 'src/a.py').write_text('x = 1\n')
        self.git('init', '-q', '-b', 'main')
        self.git('config', 'user.email', 't@example.invalid'); self.git('config', 'user.name', 'T')
        self.git('add', '.'); self.git('commit', '-qm', 'baseline')
        self.cid = create(self.repo, 'iterate', 'Change', 'Goal', ['src'], ['Works'], 'dev', 'lead')['id']
        self.revisions = 0

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], text=True, stderr=subprocess.STDOUT).strip()

    def doc(self):
        return load(self.repo, self.cid)

    def cfg(self):
        return tree(self.repo)

    def edit_record(self, change):
        path = self.repo / 'bionic/cycles' / self.cid / 'cycle.json'
        raw = json.loads(path.read_text()); change(raw)
        path.write_text(json.dumps(raw, indent=2) + '\n')

    def record_adr(self, name=ADR, status='proposed', accepted=False):
        """Inject an ADR decision of this cycle whose ADR file states `status`."""
        self.revisions += 1
        relative = f'adrs/ADR-90{self.revisions:02d}-{name}.md'
        (self.repo / 'bionic' / relative).write_text(f'---\nstatus: {status}\n---\n\n# ADR\n')
        entry = {'path': relative, 'sha256': '0' * 64, 'kind': 'adr', 'name': name, 'approval': None, 'accepted': accepted}
        self.edit_record(lambda raw: raw['decisions'].append(entry))

    def plan(self, tasks, phase=None):
        """Write the plan file, then mark the tasks it lists as done in the record: a plan file carries no state."""
        finished = {t['id'] for t in tasks if t['status'] == 'done'}
        plan = deepcopy(self.doc()['plan']); plan.update(verification=['t'], tasks=[dict(t, status='pending') for t in tasks])
        mutate(self.repo, self.cid, 'plan', plan=plan, reason='plan')

        def apply(raw):
            for t in raw['plan']['tasks']:
                if t['id'] in finished:
                    t['status'] = 'done'
            if phase:
                raw['phase'] = phase
        self.edit_record(apply)

    def decision_item(self, target='next'):
        return next((i for i in requirements(self.cfg(), self.doc(), target) if i['requirement'] == 'decisions'), None)

    def task(self, tid):
        return next(t for t in self.doc()['plan']['tasks'] if t['id'] == tid)


class PendingAdrBlocksOnlyItsDependentsTests(AdrBase):
    def test_a_plan_with_a_pending_adr_leaves_plan_when_no_plan_task_names_it(self):
        self.record_adr()
        self.plan([task_def('P', 'plan'), task_def('B', 'build'), task_def('R', 'review', [ADR])], phase='plan')
        self.assertIsNone(self.decision_item())

    def test_the_same_plan_with_a_plan_task_naming_it_is_refused_with_the_code(self):
        self.record_adr()
        self.plan([task_def('P', 'plan', [ADR]), task_def('B', 'build')], phase='plan')
        item = self.decision_item()
        self.assertIsNotNone(item)
        self.assertRegex(item['problem'], r'^adr-dependency-awaiting-acceptance: ')
        self.assertIn(ADR, item['problem'])
        self.assertIn('proposed', item['problem'])

    def test_a_task_that_does_not_depend_on_the_adr_proceeds_while_a_dependent_waits(self):
        self.record_adr()
        self.plan([task_def('A', 'build', [ADR]), task_def('B', 'build')], phase='build')
        seen = cycle_ops.inspect_state(self.repo, self.cid, {})
        offered = {a['request']['task_id'] for a in seen['actions'] if a.get('request', {}).get('op') == 'prepare-dispatch'}
        self.assertIn('B', offered)
        self.assertNotIn('A', offered)
        codes_b = {e['code'] for e in cycle_ops.dispatch_failures(self.cfg(), self.doc(), self.task('B'), [])}
        codes_a = {e['code'] for e in cycle_ops.dispatch_failures(self.cfg(), self.doc(), self.task('A'), [])}
        self.assertNotIn('adr-dependency-awaiting-acceptance', codes_b)
        self.assertIn('adr-dependency-awaiting-acceptance', codes_a)

    def test_a_later_phase_task_naming_the_adr_does_not_block_leaving_the_current_phase(self):
        self.record_adr()
        self.plan([task_def('B', 'build', status='done'), task_def('R', 'review', [ADR])], phase='build')
        self.assertIsNone(self.decision_item('next'))

    def test_completion_checks_every_unfinished_task_of_any_phase(self):
        self.record_adr()
        self.plan([task_def('B', 'build', status='done'), task_def('R', 'review', [ADR])], phase='reflect')
        item = self.decision_item('completion')
        self.assertIsNotNone(item)
        self.assertRegex(item['problem'], r'^adr-dependency-awaiting-acceptance: ')

    def test_a_finished_dependent_task_no_longer_blocks_completion(self):
        self.record_adr()
        self.plan([task_def('R', 'review', [ADR], status='done')], phase='reflect')
        self.assertIsNone(self.decision_item('completion'))

    def test_an_unaccepted_adr_that_no_task_names_blocks_nothing(self):
        self.record_adr()
        self.plan([task_def('B', 'build')], phase='build')
        check_decisions(self.cfg(), self.doc())
        check_decisions(self.cfg(), self.doc(), completion=True)


class RecordedStatusAndNamesTests(AdrBase):
    def test_a_rejected_or_superseded_adr_still_awaits_and_names_its_status(self):
        for status in ('rejected', 'superseded'):
            with self.subTest(status=status):
                self.setUp()
                self.record_adr(status=status)
                self.plan([task_def('A', 'build', [ADR])], phase='build')
                problems = adr_dependency_problems(self.cfg(), self.doc(), self.task('A'))
                self.assertEqual([p['code'] for p in problems], ['adr-dependency-awaiting-acceptance'])
                self.assertEqual(problems[0]['status'], status)
                with self.assertRaisesRegex(CycleError, f'^adr-dependency-awaiting-acceptance: .*{status}'):
                    check_decisions(self.cfg(), self.doc())

    def test_a_name_with_no_recorded_adr_blocks_with_its_own_code(self):
        self.plan([task_def('A', 'build', ['ghost'])], phase='build')
        problems = adr_dependency_problems(self.cfg(), self.doc(), self.task('A'))
        self.assertEqual([(p['code'], p['name']) for p in problems], [('adr-dependency-unrecorded', 'ghost')])
        with self.assertRaisesRegex(CycleError, '^adr-dependency-unrecorded: .*ghost'):
            check_decisions(self.cfg(), self.doc())
        errors = cycle_ops.dispatch_failures(self.cfg(), self.doc(), self.task('A'), [])
        self.assertIn('adr-dependency-unrecorded', {e['code'] for e in errors})

    def test_the_latest_recorded_revision_decides(self):
        self.record_adr(status='accepted', accepted=True)
        self.record_adr(status='proposed')
        self.plan([task_def('A', 'build', [ADR])], phase='build')
        self.assertEqual([p['code'] for p in adr_dependency_problems(self.cfg(), self.doc(), self.task('A'))],
                         ['adr-dependency-awaiting-acceptance'])


class AcceptanceReleasesTests(AdrBase):
    def test_acceptance_releases_both_the_dispatch_and_the_phase_gate(self):
        self.record_adr()
        self.plan([task_def('A', 'build', [ADR])], phase='build')
        self.assertIsNotNone(self.decision_item())
        self.assertIn('adr-dependency-awaiting-acceptance', {e['code'] for e in cycle_ops.dispatch_failures(self.cfg(), self.doc(), self.task('A'), [])})
        self.edit_record(lambda raw: raw['decisions'][0].update(accepted=True))
        with patch('decision_policy.validate_acceptance') as validated:  # the acceptance receipt is not what this test is about
            self.assertIsNone(self.decision_item())
            check_decisions(self.cfg(), self.doc(), completion=True)
        self.assertTrue(validated.called)  # an accepted cycle ADR keeps its acceptance check
        self.assertNotIn('adr-dependency-awaiting-acceptance', {e['code'] for e in cycle_ops.dispatch_failures(self.cfg(), self.doc(), self.task('A'), [])})


if __name__ == '__main__':
    unittest.main()
