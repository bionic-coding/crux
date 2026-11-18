"""A plan revision adds scope without the owner's words only through a requested reviewer's blocking finding.

Without `--owner-approval`, `plan` admits a scope difference only when it names, with `--finding` and
`--criterion`, a blocking finding that the cycle's requested reviewer recorded for this cycle and a
criterion of the current plan; every added path appears in that finding, no scope entry is removed and
acceptance is unchanged. Every other scope or acceptance difference is refused and names the route,
`plan --owner-approval`. The last test replays the shape of CYC-0176 to CYC-0178 end to end.
"""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import cycle_writer as pilot
from cycle_store import CycleError

ROUTE = r'plan --owner-approval'
ADDED = 'docs/guide.md'


class ScopeExtensionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / 'repo'
        self.repo.mkdir()
        (self.repo / 'bionic').mkdir()
        (self.repo / 'bionic/manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\n')
        (self.repo / 'bionic/objectives.md').write_text('Proportional ceremony and durable decisions.\n')
        (self.repo / 'src').mkdir()
        (self.repo / 'src/value.py').write_text('value = 1\n')
        (self.repo / 'docs').mkdir()
        (self.repo / 'docs/guide.md').write_text('The value is one.\n')
        self.git('init', '-q')
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('config', 'user.name', 'Test')
        self.git('add', '.')
        self.git('commit', '-qm', 'baseline')
        self.spec = {'goal': 'Return the corrected value', 'scope': ['src'],
                     'acceptance': ['value equals two', 'no live text states the old value'],
                     'verification': {'checks': [{'id': 'focused', 'rationale': 'value and its caller'}], 'gaps': 'none'},
                     'council': {'needed': False, 'reason': 'Bounded correction'},
                     'tasks': [{'id': 'build', 'description': 'Correct the value', 'owner': 'worker'}]}
        self.doc = pilot.create(self.repo, 'Correction', 'lead', self.spec)

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.repo), *args], check=True, capture_output=True, text=True).stdout.strip()

    def as_actor(self, actor, action, **kwargs):
        self.doc = pilot.mutate(self.repo, self.doc['id'], actor, self.doc['revision'], action, SimpleNamespace(**kwargs))
        return self.doc

    def lead(self, action, **kwargs):
        return self.as_actor('lead', action, **kwargs)

    def record_bytes(self):
        return pilot.path_of(self.repo, self.doc['id']).read_bytes()

    def check(self, result='passed'):
        self.lead('check', value={'check_id': 'focused', 'executed_command': 'python -m unittest test_value',
                                  'tested_revision': self.git('rev-parse', 'HEAD'), 'result': result,
                                  'summary': 'value check ' + result, 'reason': 'Changed behavior'})

    def implemented(self):
        self.lead('task', task='build', owner='worker', run=1, status='working', checkout=None, summary=None)
        (self.repo / 'src/value.py').write_text('value = 2\n')
        self.git('add', 'src/value.py'); self.git('commit', '-qm', 'correct value')
        self.lead('task', task='build', owner='worker', run=1, status='done', checkout=None, summary='value corrected')
        self.check()

    def report(self, reviewer='independent', **kwargs):
        report = {'reviewer': reviewer, 'plan_revision': self.doc['plan']['revision'],
                  'base_commit': self.doc['base_commit'], 'head_commit': self.git('rev-parse', 'HEAD'),
                  'verdict': 'approve', 'blocking': [],
                  'acceptance': [{'criterion': 0, 'met': True, 'evidence': 'focused value assertion'},
                                 {'criterion': 1, 'met': True, 'evidence': 'search finds no old value'}],
                  'test_selection': 'Changed behavior covered', 'summary': 'Corrected value'}
        return {**report, **kwargs}

    def review(self, reviewer='independent', **kwargs):
        self.lead('review-start', reviewer=reviewer)
        return self.as_actor(reviewer, 'review', value=self.report(reviewer, **kwargs))

    def blocked(self, finding, reviewer='independent', **kwargs):
        """The requested reviewer records one blocking finding against criterion 1; return its task id."""
        before = {t['id'] for t in self.doc['tasks']}
        self.review(reviewer, verdict='changes-required', blocking=[finding],
                    acceptance=[{'criterion': 0, 'met': True, 'evidence': 'value assertion'},
                                {'criterion': 1, 'met': False, 'evidence': 'docs/guide.md still states one'}], **kwargs)
        (added,) = [t['id'] for t in self.doc['tasks'] if t['id'] not in before]
        return added

    def widened(self, *paths, scope=None, acceptance=None):
        spec = deepcopy(self.spec)
        spec['scope'] = list(scope if scope is not None else self.doc['plan']['scope']) + list(paths)
        if acceptance is not None:
            spec['acceptance'] = acceptance
        spec['tasks'] = [{key: t[key] for key in ('id', 'description', 'owner') if key in t} for t in self.doc['tasks']]
        return spec

    def plan(self, value, finding=None, criterion=None, owner_approval=None, reason='fix the reviewer finding'):
        return self.lead('plan', value=value, reason=reason, owner_approval=owner_approval, finding=finding, criterion=criterion)

    def assertRefused(self, pattern, value, **kwargs):
        before = self.record_bytes()
        with self.assertRaisesRegex(CycleError, pattern) as caught:
            self.plan(value, **kwargs)
        self.assertEqual(self.record_bytes(), before, 'a refused plan revision wrote the record')
        return str(caught.exception)

    # -- admission ------------------------------------------------------------------

    def test_a_blocking_finding_of_the_requested_reviewer_adds_the_paths_it_names(self):
        self.implemented()
        finding = self.blocked('Criterion 1 fails: `docs/guide.md` still states the old value; fix it there.')
        self.assertEqual(self.doc['review']['finding_tasks'], [finding])
        revision = self.doc['plan']['revision']
        self.plan(self.widened(ADDED), finding=finding, criterion=1)
        self.assertEqual(self.doc['plan']['revision'], revision + 1)
        self.assertEqual(self.doc['plan']['scope'], ['src', ADDED])
        self.assertEqual(self.doc['plan']['acceptance'], self.spec['acceptance'])
        entry = self.doc['history'][-1]
        self.assertEqual(entry['kind'], 'plan')
        self.assertIsNone(entry['owner_approval'])
        extension = entry['scope_extension']
        self.assertEqual(extension['finding'], finding)
        self.assertEqual(extension['criterion'], 1)
        self.assertEqual(extension['criterion_text'], self.spec['acceptance'][1])
        self.assertEqual(extension['paths'], [ADDED])
        self.assertEqual(extension['reviewer'], 'independent')
        self.assertIn('docs/guide.md', extension['text'])

    def test_a_revision_that_adds_a_path_returns_to_planning_and_obsoletes_the_review(self):
        self.implemented()
        finding = self.blocked('docs/guide.md states the old value')
        self.plan(self.widened(ADDED), finding=finding, criterion=1)
        self.assertEqual(self.doc['state'], 'planning')
        self.assertNotEqual(self.doc['review']['plan_revision'], self.doc['plan']['revision'])
        self.assertFalse(pilot.review_current(self.repo, self.doc))

    def test_every_added_path_must_be_named_and_a_structured_finding_is_read_by_its_text(self):
        self.implemented()
        finding = self.blocked({'path': 'docs/guide.md', 'detail': 'also see src/other.py'})
        self.plan(self.widened(ADDED, 'src/other.py'), finding=finding, criterion=1)
        self.assertEqual(self.doc['history'][-1]['scope_extension']['paths'], [ADDED, 'src/other.py'])

    def test_a_path_at_the_end_of_a_sentence_is_named(self):
        self.implemented()
        finding = self.blocked('The old value remains in docs/guide.md.')
        self.plan(self.widened(ADDED), finding=finding, criterion=1)
        self.assertEqual(self.doc['plan']['scope'], ['src', ADDED])

    # -- refusals -------------------------------------------------------------------

    def test_a_scope_addition_without_owner_words_or_a_finding_is_refused(self):
        self.implemented()
        self.blocked('docs/guide.md states the old value')
        message = self.assertRefused('scope', self.widened(ADDED))
        self.assertIn(ROUTE, message)
        # Positive control: the owner's words admit the same revision.
        self.plan(self.widened(ADDED), owner_approval='Add docs/guide.md to the scope.')
        self.assertEqual(self.doc['plan']['scope'], ['src', ADDED])
        self.assertNotIn('scope_extension', self.doc['history'][-1])

    def test_a_path_the_finding_does_not_name_is_refused(self):
        self.implemented()
        finding = self.blocked('docs/guide.md states the old value')
        message = self.assertRefused('does not name', self.widened(ADDED, 'docs/other.md'), finding=finding, criterion=1)
        self.assertIn('docs/other.md', message)
        self.assertIn(ROUTE, message)

    def test_a_path_that_only_partly_matches_the_finding_is_refused(self):
        self.implemented()
        finding = self.blocked('Fix docs/guide.md.bak and xdocs/guide.md and docs/guide.mdx and docs/guide.md/part')
        self.assertRefused('does not name', self.widened(ADDED), finding=finding, criterion=1)
        self.assertRefused('does not name', self.widened('docs'), finding=finding, criterion=1)
        self.assertRefused('does not name', self.widened('docs/guide'), finding=finding, criterion=1)

    def test_an_advisory_finding_is_no_finding(self):
        self.implemented()
        self.review(advisory=['docs/guide.md still states the old value'])
        self.assertEqual(self.doc['state'], 'reviewed')
        guess = f"review-{len(self.doc['history'])}-1"
        message = self.assertRefused('no blocking finding', self.widened(ADDED), finding=guess, criterion=1)
        self.assertIn(ROUTE, message)

    def test_an_absent_finding_is_refused(self):
        self.implemented()
        self.blocked('docs/guide.md states the old value')
        self.assertRefused('no blocking finding', self.widened(ADDED), finding='review-99-1', criterion=1)

    def test_another_cycles_finding_is_refused(self):
        other = pilot.create(self.repo, 'Other', 'lead', self.spec)
        mine = self.doc
        self.doc = other
        self.implemented()
        theirs = self.blocked('docs/guide.md states the old value')
        self.doc = pilot.load_pilot(self.repo, mine['id'])
        self.assertIsNone(self.doc['review'])
        self.assertRefused('no blocking finding', self.widened(ADDED), finding=theirs, criterion=1)

    def test_a_lead_note_task_or_check_observation_offered_as_a_finding_is_refused(self):
        self.implemented()
        spec = self.widened()
        spec['tasks'].append({'id': 'review-9-1', 'description': 'Lead note: docs/guide.md states the old value', 'owner': 'worker'})
        self.plan(spec, reason='lead adds a note task')
        self.check('failed')
        check_id = self.doc['checks'][-1]['id']
        for offered in ('review-9-1', check_id, 'focused', 'build'):
            with self.subTest(offered=offered):
                self.assertRefused('no blocking finding', self.widened(ADDED), finding=offered, criterion=1)

    def test_a_finding_from_a_reviewer_who_is_not_independent_is_refused(self):
        self.implemented()
        finding = self.blocked('docs/guide.md states the old value')
        spec = self.widened()
        spec['tasks'].append({'id': 'more', 'description': 'More work', 'owner': 'independent'})
        self.plan(spec, reason='the reviewer takes a task')
        message = self.assertRefused('requested independent reviewer', self.widened(ADDED), finding=finding, criterion=1)
        self.assertIn(ROUTE, message)

    def test_a_review_not_submitted_by_its_requested_reviewer_is_refused(self):
        self.implemented()
        finding = self.blocked('docs/guide.md states the old value')
        path = pilot.path_of(self.repo, self.doc['id'])
        record = json.loads(path.read_text())
        record['review']['submitted_by'] = 'lead'
        path.write_text(json.dumps(record, indent=2) + '\n')
        self.doc = record
        self.assertRefused('requested independent reviewer', self.widened(ADDED), finding=finding, criterion=1)

    def test_the_review_write_still_refuses_a_reviewer_other_than_the_requested_one(self):
        self.implemented()
        self.lead('review-start', reviewer='independent')
        with self.assertRaisesRegex(CycleError, 'requested from independent'):
            self.as_actor('other', 'review', value=self.report('other', verdict='changes-required',
                                                               blocking=['docs/guide.md states the old value']))
        self.assertIsNone(self.doc['review'])

    def test_a_scope_removal_or_rename_is_refused_even_with_a_finding(self):
        self.implemented()
        finding = self.blocked('src2 and docs/guide.md hold the old value')
        message = self.assertRefused('removes', self.widened(ADDED, scope=[]), finding=finding, criterion=1)
        self.assertIn(ROUTE, message)
        self.assertRefused('removes', self.widened('src2', scope=[]), finding=finding, criterion=1)
        self.assertRefused('removes|scope', self.widened(scope=['src']) | {'scope': [ADDED, 'src']}, finding=finding, criterion=1)

    def test_an_acceptance_change_is_refused_even_with_a_finding(self):
        self.implemented()
        finding = self.blocked('docs/guide.md states the old value')
        changed = self.spec['acceptance'] + ['docs/guide.md states two']
        message = self.assertRefused('acceptance', self.widened(ADDED, acceptance=changed), finding=finding, criterion=1)
        self.assertIn(ROUTE, message)
        message = self.assertRefused('acceptance', self.widened(acceptance=changed))
        self.assertIn(ROUTE, message)

    def test_the_criterion_must_be_one_of_the_current_plan(self):
        self.implemented()
        finding = self.blocked('docs/guide.md states the old value')
        for criterion in (2, -1, None, '1', True):
            with self.subTest(criterion=criterion):
                self.assertRefused('criterion', self.widened(ADDED), finding=finding, criterion=criterion)

    def test_a_finding_needs_an_added_path_and_excludes_owner_words(self):
        self.implemented()
        finding = self.blocked('docs/guide.md states the old value')
        self.assertRefused('adds no path', self.widened(), finding=finding, criterion=1)
        self.assertRefused('either', self.widened(ADDED), finding=finding, criterion=1, owner_approval='Add it.')

    # -- end to end -----------------------------------------------------------------

    def test_reviewer_finding_widens_scope_and_the_next_review_covers_it(self):
        """CYC-0176 to CYC-0178: a blocking finding names an out-of-scope file an existing criterion requires."""
        self.implemented()
        finding = self.blocked('Criterion 1 is unmet: docs/guide.md still states the old value. Fix it there.')
        task_ids = [t['id'] for t in self.doc['tasks']]
        self.assertIn(finding, task_ids, 'the blocking finding became a task')
        plan_file = Path(self.temp.name) / 'plan.json'
        plan_file.write_text(json.dumps(self.widened(ADDED)))
        done = subprocess.run([sys.executable, str(SCRIPTS / 'cycle.py'), '--repo-root', str(self.repo), 'plan', self.doc['id'],
                               '--actor', 'lead', '--expect-revision', str(self.doc['revision']), '--file', str(plan_file),
                               '--reason', 'add the path the reviewer finding names', '--finding', finding, '--criterion', '1'],
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.doc = json.loads(pilot.path_of(self.repo, self.doc['id']).read_text())
        self.assertEqual(self.doc['plan']['scope'], ['src', ADDED])
        self.assertEqual(self.doc['history'][-1]['scope_extension']['paths'], [ADDED])
        # The lead fixes the finding inside the widened scope.
        (self.repo / 'docs/guide.md').write_text('The value is two.\n')
        self.git('add', 'docs/guide.md'); self.git('commit', '-qm', 'state the corrected value')
        self.lead('task', task=finding, owner='lead', run=1, status='done', checkout=None, summary='guide corrected')
        self.check()
        self.review()
        self.assertEqual(self.doc['state'], 'reviewed')
        self.assertEqual(self.doc['review']['plan_revision'], self.doc['plan']['revision'])
        self.assertTrue(pilot.review_current(self.repo, self.doc))
        self.lead('finish', summary='Value corrected and the guide states it')
        self.assertEqual(self.doc['state'], 'completed')


if __name__ == '__main__':
    unittest.main()
