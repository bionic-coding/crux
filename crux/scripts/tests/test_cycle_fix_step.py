"""A fix task: one small in-scope fix per phase per pass in Test or Review, with no pass consumed."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle_workflow as workflow
from cycle_workflow import CycleError
from test_evidence import execute
import test_cycle_review_basis as basis

# The v4 review-basis digest of a record with no fix task, computed from the writer at the base commit
# (c46b3b4d) before the `fix` field existed. The digest must not move: existing v4 reports keep binding.
V4_DIGEST_WITHOUT_FIX = 'f300f153246c6fdc63096d3a98f12971c21ea5a3253bcb0c125219cc18b563c9'


def digest_record():
    return {
        'schema_version': 2, 'type': 'iterate', 'pass': 1,
        'plan': {'revision': 3, 'scope': ['src'], 'constraints': [], 'acceptance': ['ok'], 'verification': [], 'tasks': [
            {'id': 't1', 'phase': 'build', 'description': 'd', 'depends_on': [], 'status': 'done', 'expected_evidence': ['e'], 'commits': ['a' * 40], 'note': 'n'},
            {'id': 't2', 'phase': 'test', 'description': 'd2', 'depends_on': ['t1'], 'status': 'pending', 'expected_evidence': ['e2']},
            {'id': 't3', 'phase': 'reflect', 'description': 'd3', 'depends_on': [], 'status': 'pending', 'expected_evidence': ['e3']}]},
        'required_checks': ['unit'], 'review_policy': {'scrutiny': 'standard', 'rationale': 'r', 'risks': []},
        'evidence': [{'check_id': 'unit', 'evidence_id': 'TE-' + '0' * 32, 'pass': 1, 'use': 'executed', 'declaration_sha256': 'f' * 64}],
        'coverage': {'affected': ['src'], 'checks': [{'check_id': 'unit', 'rationale': 'x'}], 'not_selected': 'none'}}


class FixBase(basis.CliCycleCase):
    """A quick-fix in a git repository with a required check `unit` and a fix check `regress`."""

    def setUp(self):
        super().setUp()
        (self.root / 'src/b.txt').write_text('bad')
        self.git('init', '-q')
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('config', 'user.name', 'Test')
        self.git('add', '.')
        self.git('commit', '-qm', 'baseline')

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], text=True).strip()

    def decl(self, check_id='unit'):
        name, inputs = ('a.txt', ['src/a.txt']) if check_id == 'unit' else ('b.txt', ['src/b.txt'])
        return {'check_id': check_id, 'inputs': inputs, 'environment': [],
                'command': [sys.executable, '-c', f"from pathlib import Path; assert Path('src/{name}').read_text() == 'good'"]}

    def record(self, check_id):
        return execute(self.root, self.decl(check_id))['evidence']

    def fix_source(self):
        """Repair src/b.txt and commit; return the commit."""
        (self.root / 'src/b.txt').write_text('good')
        self.git('add', 'src/b.txt')
        self.git('commit', '-qm', 'fix b')
        return self.git('rev-parse', 'HEAD')

    def to_test(self):
        cid = self.create_quick_fix()
        self.ok('checks', cid, '--check', 'unit')
        self.ok('coverage', cid, '--file', self.write_json('coverage.json', self.coverage(('unit',))))
        self.ok('advance', cid)
        result = execute(self.root, self.decl('unit'))
        self.unit_id = result['evidence']['id']
        self.ok('evidence', cid, '--check-id', 'unit', '--evidence-id', self.unit_id, '--use', result['action'])
        return cid

    def report_dict(self, **fields):
        report = {'reviewer': 'independent', 'scope': ['src'], 'evidence': [self.unit_id], 'blocking': [], 'advisory': [], 'cosmetic': [],
                  'verdict': 'approve', 'rationale': 'reviewed'}
        report.update(fields)
        return report

    def review_report(self, **fields):
        return self.write_json('report-%d.json' % len(list(self.root.glob('report-*.json'))), self.report_dict(**fields))

    def finding(self, n=1):
        return [{'path': 'src/b.txt', 'consequence': f'b is wrong {i}', 'evidence': 'regress fails'} for i in range(n)]

    def to_review(self, blocking=1):
        cid = self.to_test()
        self.ok('advance', cid)
        if blocking is not None:
            self.ok('review', cid, '--file', self.review_report(blocking=self.finding(blocking), verdict='changes-required'))
        return cid

    def fix_task(self, phase, identity='fix-1', **fix):
        fix = {'finding': 'F-1: b.txt holds bad', 'eligibility': 'one file, in scope, cause stated, no decision changes', **fix}
        return {'id': identity, 'phase': phase, 'description': 'repair b', 'depends_on': [], 'status': 'pending', 'expected_evidence': ['regress passes'], 'fix': fix}

    def add_fix(self, cid, phase, identity='fix-1', **fix):
        return self.ok('task-add', cid, '--file', self.write_json(identity + '.json', self.fix_task(phase, identity, **fix)))

    def task_of(self, doc, identity='fix-1'):
        return next(t for t in doc['plan']['tasks'] if t['id'] == identity)

    def deliver(self, cid, identity='fix-1'):
        """Record the before receipt, fix the source, commit it, record the after receipt and the task bookkeeping."""
        before = self.record('regress')
        self.assertEqual(before['status'], 'failed')
        sha = self.fix_source()
        after = self.record('regress')
        self.assertEqual(after['status'], 'passed')
        return self.ok('task', cid, '--task-id', identity, '--commit', sha, '--fix-before', before['id'], '--fix-after', after['id']), sha, before, after


class AcceptanceTests(FixBase):
    def test_test_fix_accepted_and_the_writer_sets_pass_without_consuming_one(self):
        cid = self.to_test()
        before = workflow.load(self.root, cid)
        doc = self.add_fix(cid, 'test')
        self.assertEqual(self.task_of(doc)['fix'], {'finding': 'F-1: b.txt holds bad', 'eligibility': 'one file, in scope, cause stated, no decision changes', 'pass': 1})
        self.assertEqual((doc['pass'], doc['phase'], doc['plan']['revision']), (before['pass'], 'test', before['plan']['revision']))

    def test_second_fix_for_the_same_phase_and_pass_is_refused_even_after_the_first_is_done(self):
        cid = self.to_test()
        self.add_fix(cid, 'test')
        self.assertIn('one fix task per phase per pass', self.refused('task-add', cid, '--file', self.write_json('b.json', self.fix_task('test', 'fix-2'))))
        doc, *_ = self.deliver(cid)
        self.ok('task', cid, '--task-id', 'fix-1', '--state', 'done')
        self.assertIn('one fix task per phase per pass', self.refused('task-add', cid, '--file', self.write_json('c.json', self.fix_task('test', 'fix-3'))))

    def test_missing_or_empty_finding_or_eligibility_is_refused(self):
        cid = self.to_test()
        for name, fix in {'no finding': {'eligibility': 'e'}, 'no eligibility': {'finding': 'f'}, 'empty finding': {'finding': ' ', 'eligibility': 'e'},
                          'empty eligibility': {'finding': 'f', 'eligibility': ''}, 'not an object': 'x', 'empty object': {}}.items():
            with self.subTest(name):
                task = self.fix_task('test')
                task['fix'] = fix
                error = self.refused('task-add', cid, '--file', self.write_json('t.json', task))
                self.assertRegex(error, 'fix')
        self.assertEqual([t for t in workflow.load(self.root, cid)['plan']['tasks'] if 'fix' in t], [])

    def test_a_fix_may_not_supply_writer_fields(self):
        cid = self.to_test()
        for key, value in {'pass': 1, 'before': 'TE-' + '0' * 32, 'after': 'TE-' + '0' * 32, 'review': {'path': 'x', 'sha256': 'y'}, 'extra': 'x'}.items():
            with self.subTest(key):
                task = self.fix_task('test')
                task['fix'][key] = value
                self.assertIn('exactly finding and eligibility', self.refused('task-add', cid, '--file', self.write_json('t.json', task)))

    def test_a_fix_outside_test_or_review_is_refused(self):
        cid = self.create_quick_fix()
        self.assertEqual(workflow.load(self.root, cid)['phase'], 'build')
        self.assertIn('Test or Review', self.refused('task-add', cid, '--file', self.write_json('t.json', self.fix_task('build'))))
        self.assertIn('Test or Review', self.refused('task-add', cid, '--file', self.write_json('t.json', self.fix_task('test'))))

    def test_a_fix_task_for_another_phase_than_the_cycle_phase_is_refused(self):
        cid = self.to_test()
        self.assertIn('current phase', self.refused('task-add', cid, '--file', self.write_json('t.json', self.fix_task('review'))))
        self.assertIn('current phase', self.refused('task-add', cid, '--file', self.write_json('t.json', self.fix_task('reflect'))))

    def test_a_release_cycle_refuses_a_fix(self):
        doc = self.ok('create', '--type', 'release', '--list', 'beta', '--title', 'R', '--goal', 'g', '--implementer', 'b', '--coordinator', 'c', '--scope', 'src', '--acceptance', 'a')
        self.refused('task-add', doc['id'], '--file', self.write_json('t.json', self.fix_task('release')))


class ReviewEligibilityTests(FixBase):
    def test_review_fix_needs_a_single_blocking_finding_in_the_latest_review(self):
        cid = self.to_review(blocking=2)
        error = self.refused('task-add', cid, '--file', self.write_json('t.json', self.fix_task('review')))
        self.assertIn('exactly one blocking finding', error)

    def test_review_fix_with_no_review_or_an_approving_review_is_refused(self):
        cid = self.to_review(blocking=None)
        self.assertIn('exactly one blocking finding', self.refused('task-add', cid, '--file', self.write_json('t.json', self.fix_task('review'))))
        self.ok('review', cid, '--file', self.review_report())
        self.assertIn('exactly one blocking finding', self.refused('task-add', cid, '--file', self.write_json('t.json', self.fix_task('review'))))

    def test_review_fix_with_one_blocking_finding_is_accepted_and_consumes_no_pass(self):
        cid = self.to_review(blocking=1)
        before = workflow.load(self.root, cid)
        doc = self.add_fix(cid, 'review')
        self.assertEqual((doc['pass'], doc['phase'], doc['plan']['revision']), (before['pass'], 'review', before['plan']['revision']))
        self.assertEqual(self.task_of(doc)['fix']['pass'], 1)


class DoneGateTests(FixBase):
    def done_refusal(self, cid):
        return self.refused('task', cid, '--task-id', 'fix-1', '--state', 'done')

    def test_done_is_refused_without_commit_before_and_after_and_a_pass_completes(self):
        cid = self.to_test()
        self.add_fix(cid, 'test')
        self.assertIn('at least one commit', self.done_refusal(cid))
        before = self.record('regress')
        sha = self.fix_source()
        self.ok('task', cid, '--task-id', 'fix-1', '--commit', sha)
        self.assertIn('--fix-before', self.done_refusal(cid))
        self.ok('task', cid, '--task-id', 'fix-1', '--fix-before', before['id'])
        self.assertIn('--fix-after', self.done_refusal(cid))
        after = self.record('regress')
        doc = self.ok('task', cid, '--task-id', 'fix-1', '--fix-after', after['id'], '--state', 'done')
        fix = self.task_of(doc)['fix']
        self.assertEqual((fix['before'], fix['after'], self.task_of(doc)['status']), (before['id'], after['id'], 'done'))
        self.assertEqual((fix['finding'], fix['pass']), ('F-1: b.txt holds bad', 1))

    def test_before_must_be_a_failure_and_after_must_be_the_current_pass_of_the_same_check(self):
        cid = self.to_test()
        self.add_fix(cid, 'test')
        passing_unit = self.unit_id
        self.assertIn('recorded a failure', self.refused('task', cid, '--task-id', 'fix-1', '--fix-before', passing_unit))
        before = self.record('regress')
        self.ok('task', cid, '--task-id', 'fix-1', '--fix-before', before['id'])
        # A pass of another check does not answer the failed one.
        self.assertIn('different check', self.refused('task', cid, '--task-id', 'fix-1', '--fix-after', passing_unit))
        # A failure is not a pass.
        self.assertIn('current valid passing', self.refused('task', cid, '--task-id', 'fix-1', '--fix-after', before['id']))
        self.assertRegex(self.refused('task', cid, '--task-id', 'fix-1', '--fix-before', 'nonsense'), 'evidence|TE-')

    def test_an_after_receipt_that_is_no_longer_current_blocks_done(self):
        cid = self.to_test()
        self.add_fix(cid, 'test')
        doc, sha, before, after = self.deliver(cid)
        (self.root / 'src/b.txt').write_text('changed again')
        self.assertIn('current valid passing', self.done_refusal(cid))

    def test_fix_flags_need_a_fix_task_and_the_writer_never_edits_finding_or_eligibility(self):
        cid = self.to_test()
        self.ok('task-add', cid, '--file', self.write_json('plain.json', self.task('test', identity='plain')))
        before = self.record('regress')
        self.assertIn('not a fix task', self.refused('task', cid, '--task-id', 'plain', '--fix-before', before['id']))
        self.add_fix(cid, 'test')
        sha = self.fix_source()
        doc = self.ok('task', cid, '--task-id', 'fix-1', '--commit', sha, '--fix-before', before['id'])
        self.assertEqual(self.task_of(doc)['fix']['finding'], 'F-1: b.txt holds bad')
        self.assertEqual(self.refused('task', cid, '--task-id', 'fix-1'), 'task update names no state or delivery field')

    def test_a_plan_file_carrying_fix_is_refused(self):
        cid = self.to_test()
        plan = deepcopy(workflow.load(self.root, cid)['plan'])
        plan['tasks'].append(self.fix_task('test'))
        # Plan revisions belong to Plan or Build, so check the file rule directly as well as through the command.
        with self.assertRaisesRegex(CycleError, r'plan task fix-1 carries fix.*`task` command'):
            workflow.check_plan_file(plan)
        self.assertIn('fix', workflow.DELIVERY_FIELDS)
        self.assertIn('fix', workflow.TASK_BOOKKEEPING_FIELDS)


class ReviewFixTests(FixBase):
    def review_fix(self, cid, **fields):
        return self.write_json('fix-review-%d.json' % len(list(self.root.glob('fix-review-*.json'))),
                               self.report_dict(**{'fix_task': 'fix-1', 'reviewer': 'second', **fields}))

    def delivered(self):
        cid = self.to_review(blocking=1)
        self.add_fix(cid, 'review')
        doc, sha, before, after = self.deliver(cid)
        return cid

    def test_review_fix_cannot_be_done_without_a_fix_diff_review(self):
        cid = self.delivered()
        self.assertIn('fix-diff review', self.refused('task', cid, '--task-id', 'fix-1', '--state', 'done'))
        self.assertIn('current phase has unfinished tasks', self.refused('advance', cid))

    def test_fix_diff_review_stores_its_ref_and_the_cycle_completes_through_advance(self):
        cid = self.delivered()
        before = workflow.load(self.root, cid)
        doc = self.ok('review', cid, '--file', self.review_fix(cid))
        task = self.task_of(doc)
        self.assertEqual(doc['reviews'][-1], task['fix']['review'])
        self.assertEqual((doc['pass'], doc['phase'], doc['plan']['revision']), (before['pass'], 'review', before['plan']['revision']))
        self.ok('task', cid, '--task-id', 'fix-1', '--state', 'done')
        self.assertEqual(self.ok('advance', cid)['phase'], 'reflect')

    def test_a_blocking_fix_diff_review_does_not_unblock_done(self):
        cid = self.delivered()
        self.ok('review', cid, '--file', self.review_fix(cid, blocking=self.finding(1), verdict='changes-required'))
        self.assertIn('approving', self.refused('task', cid, '--task-id', 'fix-1', '--state', 'done'))
        self.assertIn('counted return', self.refused('review', cid, '--file', self.review_fix(cid)))

    def test_without_fix_task_a_second_review_after_a_blocking_one_is_still_refused(self):
        cid = self.delivered()
        self.assertIn('counted return', self.refused('review', cid, '--file', self.review_report(reviewer='second')))

    def test_fix_reviewer_equal_to_the_fix_assignee_is_refused(self):
        cid = self.delivered()
        self.ok('task', cid, '--task-id', 'fix-1', '--assignee', 'second')
        self.assertIn('fix assignee', self.refused('review', cid, '--file', self.review_fix(cid)))
        self.ok('review', cid, '--file', self.review_fix(cid, reviewer='third'))

    def test_fix_reviewer_among_the_implementers_is_refused(self):
        cid = self.delivered()
        self.refused('review', cid, '--file', self.review_fix(cid, reviewer='builder'))

    def test_fix_task_must_name_this_passes_review_phase_fix_and_scope_stays_the_plan_scope(self):
        cid = self.delivered()
        self.assertIn('review-phase fix task', self.refused('review', cid, '--file', self.review_fix(cid, fix_task='nope')))
        self.ok('task-add', cid, '--file', self.write_json('plain.json', self.task('review', identity='plain')))
        self.assertIn('review-phase fix task', self.refused('review', cid, '--file', self.review_fix(cid, fix_task='plain')))
        self.assertIn('scope', self.refused('review', cid, '--file', self.review_fix(cid, scope=['src/b.txt'])))

    def test_fix_diff_review_needs_a_committed_fix(self):
        cid = self.to_review(blocking=1)
        self.add_fix(cid, 'review')
        self.assertIn('commit', self.refused('review', cid, '--file', self.review_fix(cid)))

    def test_fix_task_key_on_a_test_phase_fix_is_refused(self):
        cid = self.to_test()
        self.add_fix(cid, 'test')
        self.assertIn('independent review belongs to Review', self.refused('review', cid, '--file', self.review_fix(cid)))

    def test_the_blocking_report_stops_binding_and_the_fix_review_binds(self):
        cid = self.delivered()
        with self.assertRaisesRegex(CycleError, 'independent review|blocking'):
            workflow.check_review(workflow.tree(self.root), workflow.load(self.root, cid))
        self.ok('review', cid, '--file', self.review_fix(cid))
        doc = workflow.load(self.root, cid)
        report = workflow.check_review(workflow.tree(self.root), doc)
        self.assertEqual(report['fix_task'], 'fix-1')
        self.ok('task', cid, '--task-id', 'fix-1', '--state', 'done')
        # Task status is bookkeeping: the approval still binds.
        workflow.check_review(workflow.tree(self.root), workflow.load(self.root, cid))


class TestFixFlowTests(FixBase):
    def test_test_fix_completes_through_advance_and_is_covered_by_the_following_review(self):
        cid = self.to_test()
        self.add_fix(cid, 'test')
        self.assertIn('current phase has unfinished tasks', self.refused('advance', cid))
        self.deliver(cid)
        self.ok('task', cid, '--task-id', 'fix-1', '--state', 'done')
        doc = self.ok('advance', cid)
        self.assertEqual((doc['phase'], doc['pass']), ('review', 1))
        # The ordinary Review applies: a plain approving report is needed, and a fix_task key has no Test fix to name.
        self.assertIn('review-phase fix task', self.refused('review', cid, '--file', self.review_report(fix_task='fix-1')))
        self.ok('review', cid, '--file', self.review_report())
        self.assertEqual(self.ok('advance', cid)['phase'], 'reflect')


class PassBoundaryTests(FixBase):
    def test_start_pass_keeps_a_done_fix_and_drops_an_unfinished_one(self):
        cid = self.to_test()
        self.add_fix(cid, 'test')
        self.deliver(cid)
        self.ok('task', cid, '--task-id', 'fix-1', '--state', 'done')
        self.ok('advance', cid)
        self.ok('extend', cid, '--limit', '2', '--human-approval', 'fixture raises the limit')
        # Review phase: a blocking finding, one review fix left unfinished, then a counted return.
        self.ok('review', cid, '--file', self.review_report(blocking=self.finding(1), verdict='changes-required'))
        self.add_fix(cid, 'review', identity='fix-2')
        self.ok('return', cid, '--improved', 'fix', '--unresolved', 'more', '--next-change', 'rework', '--justification', 'j', '--progress', 'yes')
        doc = workflow.load(self.root, cid)
        self.assertEqual((doc['pass'], doc['phase']), (2, 'build'))
        ids = [t['id'] for t in doc['plan']['tasks']]
        self.assertIn('fix-1', ids)
        self.assertNotIn('fix-2', ids)
        self.assertEqual(self.task_of(doc)['status'], 'done')
        self.assertEqual(self.task_of(doc)['fix']['pass'], 1)
        previous = [e for e in doc['history'] if e['action'] == 'return-requested'][-1]['plan']
        self.assertIn('fix-2', [t['id'] for t in previous['tasks']])

    def test_a_new_pass_allows_a_new_fix_for_the_same_phase(self):
        cid = self.to_test()
        self.add_fix(cid, 'test')
        self.deliver(cid)
        self.ok('task', cid, '--task-id', 'fix-1', '--state', 'done')
        doc = workflow.load(self.root, cid)
        doc['pass'] = 2
        doc['pass_limit'] = 2
        doc['phase'] = 'test'
        workflow.save(workflow.tree(self.root), doc)
        doc = self.add_fix(cid, 'test', identity='fix-2')
        self.assertEqual(self.task_of(doc, 'fix-2')['fix']['pass'], 2)

    def test_start_pass_directly_drops_dependencies_on_a_dropped_fix(self):
        cid = self.to_test()
        self.add_fix(cid, 'test')
        doc = workflow.load(self.root, cid)
        other = self.task('test', identity='after-fix')
        other['depends_on'] = ['fix-1']
        doc['plan']['tasks'].append(other)
        workflow.start_pass(workflow.tree(self.root), doc)
        self.assertEqual([t['id'] for t in doc['plan']['tasks']], ['after-fix'])
        self.assertEqual(doc['plan']['tasks'][0]['depends_on'], [])
        workflow.validate(doc)


class BasisTests(FixBase):
    def test_v4_digest_of_a_record_without_fix_tasks_is_unchanged(self):
        self.assertEqual(workflow.review_basis_digest(digest_record(), 4), V4_DIGEST_WITHOUT_FIX)

    def test_fix_task_enters_the_basis_by_id_phase_description_and_evidence_not_by_fix(self):
        doc = digest_record()
        doc['plan']['tasks'].append({'id': 'f', 'phase': 'review', 'description': 'd', 'depends_on': [], 'status': 'pending', 'expected_evidence': ['e'],
                                     'fix': {'finding': 'a', 'eligibility': 'b', 'pass': 1}})
        with_fix = workflow.review_basis_digest(doc, 4)
        self.assertNotEqual(with_fix, V4_DIGEST_WITHOUT_FIX)
        doc['plan']['tasks'][-1]['fix'] = {'finding': 'zzz', 'eligibility': 'qqq', 'pass': 1, 'before': 'TE-' + '1' * 32}
        self.assertEqual(workflow.review_basis_digest(doc, 4), with_fix)

    def test_schema_fix_object_is_closed(self):
        schema = json.loads((Path(__file__).resolve().parents[2] / 'schemas/cycle.schema.json').read_text())
        fix = schema['properties']['plan']['properties']['tasks']['items']['properties']['fix']
        self.assertEqual(set(fix['properties']), {'finding', 'eligibility', 'pass', 'before', 'after', 'review'})
        self.assertEqual(set(fix['required']), {'finding', 'eligibility', 'pass'})
        self.assertIs(fix['additionalProperties'], False)


if __name__ == '__main__':
    unittest.main()
