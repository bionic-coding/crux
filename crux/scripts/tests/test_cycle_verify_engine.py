"""The engine treats the phase after Build per record: 'verify' on a record with phase_names, 'test' on one without.

Covers every sequence, the two-way input mapping, fixes, returns, type changes, plan details, reductions, review
binding, upgrade, mixed records, the release step, the committed records and the absence of a stray 'test' literal."""
import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cycle_workflow as workflow
from cycle_historical import make_historical, rename_phase
from cycle_progress import render, view
from cycle_workflow import CHECK_PHASES, CycleError, PHASES, RELEASE_LISTS, create, load, mutate, own_phase, phases_of, validate
from _dev_surface import require_dev_surface
from test_cycle_review_basis import CliCycleCase
from test_cycle_simplify import reduction
from test_cycle_slice import SliceBase

SCRIPTS = Path(__file__).resolve().parents[1]
REPO = Path(__file__).resolve().parents[3]
OLD_VERIFY_STEP = 'Verify the artifact with the release gates'
UPGRADE = {'op': 'upgrade', 'op_id': 'upgrade-001'}
RETURN = dict(improved='isolated', unresolved='one defect', next_change='fix it', justification='cause found', progress=True)


def task_in(phase, identity, **extra):
    return {'id': identity, 'phase': phase, 'description': identity, 'depends_on': [], 'status': 'pending', 'expected_evidence': ['e'], **extra}


class EngineBase(SliceBase):
    """Drives low-level mutations on records in either vocabulary."""

    def new(self, kind='quick-fix', historical=False):
        doc = create(self.repo, kind, 'Change', 'Goal', ['src'], ['Works'], 'builder', 'tester')
        if historical:
            make_historical(self.repo, doc['id'])
        return doc['id']

    def put_phase(self, cid, phase):
        """Write the record's phase directly, as a record that reached it would hold it."""
        path = self.record_path(cid)
        raw = json.loads(path.read_text())
        raw['phase'] = phase
        path.write_text(json.dumps(raw, indent=2, sort_keys=True) + '\n')

    def plan_with(self, cid, names):
        plan = deepcopy(load(self.repo, cid)['plan'])
        plan.update(verification=['v'], tasks=[task_in(p, f'task-{index}') for index, p in enumerate(names)])
        return plan


class SequenceTests(EngineBase):
    def test_every_type_names_verify_after_build_and_release_has_no_verify_phase(self):
        expected = {
            'dev': ['plan', 'build', 'verify', 'review', 'reflect'], 'iterate': ['plan', 'build', 'verify', 'review', 'reflect'],
            'refactor': ['plan', 'build', 'verify', 'review', 'reflect'], 'simplify': ['plan', 'build', 'verify', 'review', 'reflect'],
            'quick-fix': ['build', 'verify', 'review', 'reflect'],
        }
        for kind, sequence in expected.items():
            with self.subTest(kind):
                doc = create(self.repo, kind, 't', 'g', ['src'], ['a'], 'b', 'c')
                self.assertEqual((phases_of(doc), doc['phase_names']), (sequence, 'verify'))
                self.assertEqual(phases_of(load(self.repo, doc['id'])), sequence)
        for listing in ('beta', 'official'):
            with self.subTest(listing):
                doc = create(self.repo, 'release', 't', 'g', ['src'], ['a'], 'b', 'c', release_list=listing)
                self.assertEqual(phases_of(doc), ['release'])
                self.assertEqual({t['phase'] for t in doc['plan']['tasks']}, {'release'})

    def test_a_record_without_phase_names_keeps_every_historical_sequence(self):
        for kind in ('dev', 'iterate', 'refactor', 'simplify', 'quick-fix'):
            with self.subTest(kind):
                doc = load(self.repo, self.new(kind, historical=True))
                self.assertEqual(phases_of(doc), PHASES[kind])
                self.assertIn('test', phases_of(doc))

    def test_a_record_mixing_both_names_is_refused(self):
        doc = load(self.repo, self.new())
        mixed_task = deepcopy(doc)
        mixed_task['plan']['tasks'].append(task_in('test', 'stray'))
        with self.assertRaises(CycleError):
            validate(mixed_task)
        mixed_phase = deepcopy(doc)
        mixed_phase['phase'] = 'test'
        with self.assertRaises(CycleError):
            validate(mixed_phase)
        old = load(self.repo, self.new(historical=True))
        old['plan']['tasks'].append(task_in('verify', 'stray'))
        with self.assertRaises(CycleError):
            validate(old)


class InputMappingTests(EngineBase):
    def test_own_phase_maps_both_names_and_leaves_other_values(self):
        new, old = load(self.repo, self.new()), load(self.repo, self.new(historical=True))
        self.assertEqual([own_phase(new, v) for v in ('test', 'verify', 'build')], ['verify', 'verify', 'build'])
        self.assertEqual([own_phase(old, v) for v in ('test', 'verify', 'review')], ['test', 'test', 'review'])

    def test_a_release_record_maps_nothing(self):
        release = create(self.repo, 'release', 't', 'g', ['src'], ['a'], 'b', 'c', release_list='beta')
        self.assertEqual([own_phase(release, v) for v in ('test', 'verify', 'release')], ['test', 'verify', 'release'])
        with self.assertRaises(CycleError):
            mutate(self.repo, release['id'], 'task-add', task=task_in('test', 'extra'))
        self.assertEqual(len(load(self.repo, release['id'])['plan']['tasks']), len(RELEASE_LISTS['beta']))

    def test_task_add_stores_the_record_own_name_for_either_input(self):
        for historical, own in ((False, 'verify'), (True, 'test')):
            cid = self.new(historical=historical)
            for submitted in ('test', 'verify'):
                with self.subTest(historical=historical, submitted=submitted):
                    mutate(self.repo, cid, 'task-add', task=task_in(submitted, f'extra-{submitted}'))
                    stored = next(t for t in load(self.repo, cid)['plan']['tasks'] if t['id'] == f'extra-{submitted}')
                    self.assertEqual(stored['phase'], own)

    def test_plan_stores_the_record_own_name_for_either_input(self):
        for historical, own in ((False, 'verify'), (True, 'test')):
            for submitted in ('test', 'verify'):
                with self.subTest(historical=historical, submitted=submitted):
                    cid = self.new('dev', historical=historical)
                    names = ['plan', 'build', submitted, 'review', 'reflect']
                    doc = mutate(self.repo, cid, 'plan', plan=self.plan_with(cid, names), reason='plan')
                    self.assertEqual([t['phase'] for t in doc['plan']['tasks']], ['plan', 'build', own, 'review', 'reflect'])
                    self.assertEqual(load(self.repo, cid)['plan']['tasks'][2]['phase'], own)

    def test_a_replan_naming_the_other_vocabulary_changes_and_reopens_no_task(self):
        cid = self.new('dev', historical=True)
        mutate(self.repo, cid, 'plan', plan=self.plan_with(cid, ['plan', 'test', 'review', 'reflect']), reason='plan')
        for task_id in ('task-0', 'task-1', 'task-2', 'task-3'):
            mutate(self.repo, cid, 'task', task_id=task_id, state='done')
        before = load(self.repo, cid)
        after = mutate(self.repo, cid, 'plan', plan=self.plan_with(cid, ['plan', 'verify', 'review', 'reflect']), reason='same plan')
        self.assertEqual(after['plan']['tasks'], before['plan']['tasks'])
        self.assertEqual({t['status'] for t in after['plan']['tasks']}, {'done'})
        self.assertEqual([t['phase'] for t in after['plan']['tasks']], ['plan', 'test', 'review', 'reflect'])


class CheckPhaseTests(EngineBase):
    def in_check_phase(self, kind='quick-fix', historical=False):
        cid = self.new(kind, historical=historical)
        own = next(p for p in phases_of(load(self.repo, cid)) if p in CHECK_PHASES)
        self.put_phase(cid, own)
        return cid, own

    def test_a_fix_task_is_accepted_in_the_phase_after_build_of_either_record(self):
        fix = {'finding': 'F-1: broken', 'eligibility': 'small and in scope'}
        for historical in (False, True):
            for submitted in ('test', 'verify'):
                with self.subTest(historical=historical, submitted=submitted):
                    cid, own = self.in_check_phase(historical=historical)
                    mutate(self.repo, cid, 'task-add', task=task_in(submitted, 'fix-1', fix=dict(fix)))
                    stored = next(t for t in load(self.repo, cid)['plan']['tasks'] if t['id'] == 'fix-1')
                    self.assertEqual((stored['phase'], stored['fix']['pass']), (own, 1))

    def test_a_fix_task_is_refused_in_build_and_the_message_names_the_record_phase(self):
        for historical, title in ((False, 'Verify or Review'), (True, 'Test or Review')):
            with self.subTest(historical=historical):
                cid = self.new(historical=historical)
                with self.assertRaisesRegex(CycleError, title):
                    mutate(self.repo, cid, 'task-add', task=task_in('build', 'fix-1', fix={'finding': 'F-1', 'eligibility': 'small'}))

    def test_return_is_accepted_in_the_phase_after_build_of_either_record(self):
        for historical in (False, True):
            with self.subTest(historical=historical):
                cid, _ = self.in_check_phase('dev', historical)
                doc = mutate(self.repo, cid, 'return', **RETURN)
                self.assertEqual((doc['pass'], doc['phase']), (2, 'build'))

    def test_return_is_refused_before_the_check_phase(self):
        cid = self.new('dev')
        with self.assertRaises(CycleError):
            mutate(self.repo, cid, 'return', **RETURN)

    def test_change_type_keeps_the_record_vocabulary(self):
        for historical, own in ((False, 'verify'), (True, 'test')):
            with self.subTest(historical=historical):
                cid = self.new('dev', historical=historical)
                doc = mutate(self.repo, cid, 'change-type', kind='iterate', reason='smaller than planned')
                self.assertEqual(('phase_names' in doc), not historical)
                self.assertEqual([p for p in phases_of(doc) if p in CHECK_PHASES], [own])
                self.assertEqual(doc['type'], 'iterate')

    def test_change_type_after_the_check_phase_needs_a_counted_return_in_either_vocabulary(self):
        for historical in (False, True):
            with self.subTest(historical=historical):
                cid, _ = self.in_check_phase('dev', historical)
                with self.assertRaisesRegex(CycleError, 'counted return'):
                    mutate(self.repo, cid, 'change-type', kind='iterate', reason='r')

    def test_plan_details_names_the_record_phase_and_is_accepted_in_it(self):
        for historical, title in ((False, 'Verify'), (True, 'Test')):
            with self.subTest(historical=historical):
                cid, _ = self.in_check_phase(historical=historical)
                doc = mutate(self.repo, cid, 'plan-details', details={'constraints': ['c']}, reason='r')
                self.assertEqual(doc['plan']['constraints'], ['c'])
                self.put_phase(cid, 'review')
                with self.assertRaisesRegex(CycleError, f'Build or {title} phase'):
                    mutate(self.repo, cid, 'plan-details', details={'constraints': ['d']}, reason='r')

    def test_reduction_is_recorded_in_the_phase_after_build_of_either_record(self):
        for historical, title in ((False, 'Verify'), (True, 'Test')):
            with self.subTest(historical=historical):
                cid, _ = self.in_check_phase('simplify', historical)
                doc = mutate(self.repo, cid, 'reduction', reduction=reduction())
                self.assertEqual(doc['reduction']['pass'], 1)
                self.put_phase(cid, 'build')
                with self.assertRaisesRegex(CycleError, f'{title} phase'):
                    mutate(self.repo, cid, 'reduction', reduction=reduction())

    def test_reduction_requirement_gates_the_check_phase_of_either_record(self):
        for historical in (False, True):
            with self.subTest(historical=historical):
                cid, _ = self.in_check_phase('simplify', historical)
                names = [item['requirement'] for item in workflow.requirements(workflow.tree(self.repo), load(self.repo, cid), 'next')]
                self.assertIn('reduction', names)


class HistoricalReviewTests(CliCycleCase):
    """A record without phase_names advances through 'test' and keeps its review binding."""

    def create_quick_fix(self):
        cid = super().create_quick_fix()
        make_historical(self.root, cid)
        return cid

    def test_a_declared_check_must_pass_before_a_historical_record_leaves_test(self):
        cid = self.create_quick_fix()
        self.assertNotIn('phase_names', workflow.load(self.root, cid))
        self.ok('checks', cid, '--check', 'unit')
        self.ok('coverage', cid, '--file', self.write_json('coverage.json', self.coverage(('unit',))))
        self.assertEqual(self.ok('advance', cid)['phase'], 'test')
        self.assertIn('missing passing evidence', self.refused('advance', cid))
        self.assertEqual(workflow.load(self.root, cid)['phase'], 'test')
        from test_evidence import execute
        result = execute(self.root, self.decl('unit'))
        self.ok('evidence', cid, '--check-id', 'unit', '--evidence-id', result['evidence']['id'], '--use', result['action'])
        self.assertEqual(self.ok('advance', cid)['phase'], 'review')

    def test_review_binding_is_satisfied_on_a_record_without_phase_names(self):
        cid = self.approved_quick_fix()
        doc = workflow.load(self.root, cid)
        self.assertNotIn('phase_names', doc)
        self.assertEqual(phases_of(doc), ['build', 'test', 'review', 'reflect'])
        self.assertEqual(workflow.check_review(workflow.tree(self.root), doc)['verdict'], 'approve')

    def test_a_historical_record_reaches_completion_in_the_old_vocabulary(self):
        cid = self.approved_quick_fix()
        self.assertEqual(self.ok('advance', cid)['phase'], 'reflect')
        self.assertEqual({t['phase'] for t in workflow.load(self.root, cid)['plan']['tasks']} - {'build'}, set())


class UpgradeTests(EngineBase):
    def test_upgrading_a_version_two_record_adds_no_phase_names_and_keeps_test(self):
        cid = self.fixture(version=2)
        self.assertNotIn('phase_names', json.loads(self.record_path(cid).read_text()))
        self.ok(UPGRADE, cid=cid)
        doc = json.loads(self.record_path(cid).read_text())
        self.assertEqual(doc['schema_version'], 3)
        self.assertNotIn('phase_names', doc)
        self.assertEqual(phases_of(load(self.repo, cid)), ['build', 'test', 'review', 'reflect'])


class ReleaseStepTests(EngineBase):
    def test_the_beta_verify_step_description_names_the_release_command(self):
        doc = create(self.repo, 'release', 't', 'g', ['src'], ['a'], 'b', 'c', release_list='beta')
        step = next(t for t in doc['plan']['tasks'] if t['id'] == 'verify')
        self.assertIn('release.py verify', step['description'])
        self.assertEqual(step['phase'], 'release')
        self.assertEqual(doc['phase_names'], 'verify')
        self.assertEqual(phases_of(doc), ['release'])

    def test_the_step_id_and_order_are_unchanged(self):
        self.assertEqual([step[0] for step in RELEASE_LISTS['beta']], ['prep', 'prepare', 'verify', 'beta-and-smoke', 'tag', 'record'])
        self.assertEqual([step[0] for step in RELEASE_LISTS['official']], ['live-check-and-go-ahead', 'official', 'record'])

    def test_an_older_beta_record_with_the_earlier_description_still_validates(self):
        doc = create(self.repo, 'release', 't', 'g', ['src'], ['a'], 'b', 'c', release_list='beta')
        next(t for t in doc['plan']['tasks'] if t['id'] == 'verify')['description'] = OLD_VERIFY_STEP
        doc.pop('phase_names')
        validate(doc)


class CommittedRecordTests(unittest.TestCase):
    def test_every_committed_record_validates_loads_and_renders_with_unchanged_bytes(self):
        directory = REPO / 'bionic/cycles'
        require_dev_surface(self, directory, 'bionic/cycles')
        paths = sorted(directory.glob('CYC-*/cycle.json'))
        self.assertTrue(paths)
        before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
        for path in paths:
            with self.subTest(path.parent.name):
                doc = json.loads(path.read_text())
                validate(doc)
                self.assertEqual(load(REPO, doc['id'])['id'], doc['id'])
                if 'phase_names' not in doc and doc['type'] != 'release':
                    self.assertEqual(phases_of(doc), PHASES[doc['type']])
        render(view(REPO))
        after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
        self.assertEqual(before, after)


class NoStrayTestLiteralTests(unittest.TestCase):
    """The phase after Build is named only by CHECK_PHASES and the historical sequence definition."""

    @staticmethod
    def stray_literals(tree):
        skipped = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in {'CHECK_PHASES', 'PHASES'} for t in node.targets):
                skipped.update(id(child) for child in ast.walk(node.value))
        hits = []
        for node in ast.walk(tree):
            operands = []
            if isinstance(node, ast.Compare):
                operands = [node.left, *node.comparators]
            elif isinstance(node, (ast.Tuple, ast.List, ast.Set)):
                operands = list(node.elts)
            hits += [(operand.lineno, 'test') for operand in operands
                     if isinstance(operand, ast.Constant) and operand.value == 'test' and id(operand) not in skipped]
        return hits

    def test_the_scanner_finds_a_planted_comparison_and_literal(self):
        planted = ast.parse("if phase == 'test':\n    pass\nx = ('test', 'review')\ny = {'a': ['test']}\nCHECK_PHASES = ('test', 'verify')\n")
        self.assertEqual([line for line, _ in self.stray_literals(planted)], [1, 3, 4])

    def test_no_cycle_module_compares_or_lists_the_literal_test(self):
        modules = sorted(SCRIPTS.glob('cycle*.py'))
        self.assertIn(SCRIPTS / 'cycle_workflow.py', modules)
        for path in modules:
            with self.subTest(path.name):
                self.assertEqual(self.stray_literals(ast.parse(path.read_text())), [])


if __name__ == '__main__':
    unittest.main()
