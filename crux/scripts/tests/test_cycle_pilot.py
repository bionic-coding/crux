"""The opt-in pilot's milestone, ownership, review and delivery boundaries."""
from copy import deepcopy
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle_pilot as pilot
import cycle_runtime as runtime
from cycle_workflow import CycleError, create as legacy_create, load as legacy_load, tree


class PilotTests(unittest.TestCase):
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
        self.git('init', '-q')
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('config', 'user.name', 'Test')
        self.git('add', '.')
        self.git('commit', '-qm', 'baseline')
        self.spec = {'goal': 'Return the corrected value', 'scope': ['src'], 'acceptance': ['value equals two'],
                     'verification': {'checks': [{'id': 'focused', 'rationale': 'value and its caller'}], 'gaps': 'Broader integration runs on the PR'},
                     'council': {'needed': False, 'reason': 'Owner agreed on this bounded correction'},
                     'tasks': [{'id': 'build', 'description': 'Correct the value', 'owner': 'worker'}]}
        self.doc = pilot.create(self.repo, 'Correction', 'lead', self.spec)

    def git(self, *args, cwd=None):
        return subprocess.run(['git', '-C', str(cwd or self.repo), *args], check=True, capture_output=True, text=True).stdout.strip()

    def apply(self, action, **kwargs):
        args = SimpleNamespace(**kwargs)
        actor = 'lead'
        if action == 'review':
            # The lead requests review from the named reviewer, who then submits its own report.
            actor = kwargs['value']['reviewer']
            if self.doc['state'] != 'reviewing' or self.doc.get('review_request', {}).get('reviewer') != actor:
                self.apply('review-start', reviewer=actor)
        self.doc = pilot.mutate(self.repo, self.doc['id'], actor, self.doc['revision'], action, args)
        return self.doc

    def task(self, status='working', owner='worker', run=1, **kwargs):
        return self.apply('task', task='build', owner=owner, run=run, status=status, checkout=kwargs.get('checkout'),
                          summary=kwargs.get('summary', 'observed ' + status))

    def check(self, result='passed'):
        return self.apply('check', value={'check_id': 'focused', 'executed_command': 'python -m unittest test_value',
                    'tested_revision': self.git('rev-parse', 'HEAD'), 'result': result, 'summary': 'value check ' + result,
                    'reason': 'Changed behavior and related caller'})

    def implemented(self):
        self.task()
        (self.repo / 'src/value.py').write_text('value = 2\n')
        self.git('add', 'src/value.py')
        self.git('commit', '-qm', 'correct value')
        self.task('done')
        self.check()

    def report(self, **kwargs):
        report = {'reviewer': 'independent', 'plan_revision': self.doc['plan']['revision'],
                  'base_commit': self.doc['base_commit'], 'head_commit': self.git('rev-parse', 'HEAD'),
                  'verdict': 'approve', 'blocking': [], 'acceptance': [{'criterion': 0, 'met': True, 'evidence': 'focused value assertion'}],
                  'test_selection': 'Changed behavior and caller covered; comprehensive integration left to PR CI',
                  'summary': 'Corrected value', 'remaining': ['PR CI']}
        return {**report, **kwargs}

    def test_direct_fix_is_small_and_does_not_commit_milestones(self):
        head = self.git('rev-parse', 'HEAD')
        self.task()
        self.assertEqual(self.git('rev-parse', 'HEAD'), head)
        self.assertEqual(self.doc['tasks'][0]['run'], 1)
        (self.repo / 'src/value.py').write_text('value = 2\n')
        self.git('add', 'src/value.py'); self.git('commit', '-qm', 'correct value')
        self.task('done'); self.check()
        self.apply('review', value=self.report())
        self.assertEqual(self.doc['state'], 'reviewed')
        self.assertTrue(pilot.review_current(self.repo, self.doc))
        self.assertEqual(self.doc['delivery']['merge'], 'unmerged')
        self.assertLess(len(json.dumps(self.doc)), 12000)
        self.assertFalse(any(self.repo.rglob('TE-*')))

    # -- reviewer-owned approval ------------------------------------------------------

    def as_actor(self, actor, action, **kwargs):
        self.doc = pilot.mutate(self.repo, self.doc['id'], actor, self.doc['revision'], action, SimpleNamespace(**kwargs))
        return self.doc

    def record_bytes(self):
        return pilot.path_of(self.repo, self.doc['id']).read_bytes()

    def test_reviewer_submits_its_own_verdict_and_the_lead_cannot(self):
        self.implemented()
        with self.assertRaisesRegex(CycleError, 'no review is requested'):
            self.as_actor('independent', 'review', value=self.report())
        self.apply('review-start', reviewer='independent')
        self.assertEqual(self.doc['review_request']['head_commit'], self.git('rev-parse', 'HEAD'))
        before = self.record_bytes()
        with self.assertRaisesRegex(CycleError, 'lead requests review and never records'):
            self.as_actor('lead', 'review', value=self.report())
        with self.assertRaisesRegex(CycleError, 'only the recorded lead'):
            self.as_actor('independent', 'check', value={})
        with self.assertRaisesRegex(CycleError, '--actor must equal the report reviewer'):
            self.as_actor('other', 'review', value=self.report())
        with self.assertRaisesRegex(CycleError, 'requested from independent'):
            self.as_actor('other', 'review', value=self.report(reviewer='other'))
        self.assertEqual(self.record_bytes(), before, 'a refused review wrote the record')
        self.as_actor('independent', 'review', value=self.report())
        self.assertEqual(self.doc['state'], 'reviewed')
        self.assertEqual(self.doc['review']['submitted_by'], 'independent')
        self.assertNotIn('review_request', self.doc)
        with self.assertRaisesRegex(CycleError, 'no review is requested'):
            self.as_actor('independent', 'review', value=self.report())

    def test_stale_reviewer_result_is_rejected(self):
        self.implemented()
        self.apply('review-start', reviewer='independent')
        stale = self.report()
        # The reviewed code moves on: the report's head no longer covers the code at HEAD.
        (self.repo / 'src/value.py').write_text('value = 4\n')
        self.git('add', 'src/value.py'); self.git('commit', '-qm', 'change after the reviewed head')
        before = self.record_bytes()
        with self.assertRaisesRegex(CycleError, 'stale review: code changed after the reviewed head: src/value.py'):
            self.as_actor('independent', 'review', value=stale)
        # The plan is revised: the request and the report name a superseded revision.
        changed = deepcopy(self.spec); changed['goal'] += ' and document it'
        self.apply('plan', value=changed, reason='clarify', owner_approval=None)
        with self.assertRaisesRegex(CycleError, 'stale review: the report names a superseded plan revision'):
            self.as_actor('independent', 'review', value=stale)
        with self.assertRaisesRegex(CycleError, 'no review is requested for this plan revision'):
            self.as_actor('independent', 'review', value={**stale, 'plan_revision': self.doc['plan']['revision']})
        self.assertIsNone(self.doc['review'])
        # Positive control: the same reviewer's fresh report on the fresh request is accepted.
        self.check(); self.apply('review-start', reviewer='independent')
        self.as_actor('independent', 'review', value=self.report())
        self.assertEqual(self.doc['state'], 'reviewed')
        self.assertNotEqual(self.record_bytes(), before)

    def test_bookkeeping_after_the_reviewed_head_keeps_the_report_valid(self):
        self.implemented()
        self.apply('review-start', reviewer='independent')
        report = self.report()
        for name in ('journal', 'log', 'queue'):
            (self.repo / 'bionic' / name).mkdir()
            (self.repo / 'bionic' / name / 'entry.md').write_text('recorded\n')
        self.git('add', 'bionic'); self.git('commit', '-qm', 'journal, log, queue and cycle record')
        self.assertNotEqual(report['head_commit'], self.git('rev-parse', 'HEAD'))
        self.as_actor('independent', 'review', value=report)
        self.assertEqual(self.doc['review']['head_commit'], report['head_commit'])
        self.assertTrue(pilot.review_current(self.repo, self.doc))
        (self.repo / 'bionic/journal/entry.md').write_text('amended, uncommitted\n')
        self.assertTrue(pilot.review_current(self.repo, self.doc))
        (self.repo / 'bionic/notes.md').write_text('another path, outside the reviewed range\n')
        self.assertTrue(pilot.review_current(self.repo, self.doc), 'a change to an unreviewed path made the review obsolete')
        (self.repo / 'src/value.py').write_text('value = 5\n')
        self.assertFalse(pilot.review_current(self.repo, self.doc))

    def test_task_updates_during_review_keep_the_state_and_new_work_ends_currency(self):
        spec = deepcopy(self.spec)
        spec['tasks'].append({'id': 'journal', 'description': 'Record the work', 'owner': 'lead'})
        spec['tasks'].append({'id': 'extra', 'description': 'Later work', 'owner': 'worker'})
        self.doc = pilot.create(self.repo, 'Three tasks', 'lead', spec)
        self.implemented()
        self.apply('task', task='extra', owner='worker', run=1, status='done', summary='nothing to change')
        self.apply('review-start', reviewer='independent')
        self.apply('task', task='journal', owner='lead', run=1, status='done', summary='journal written')
        self.assertEqual(self.doc['state'], 'reviewing')
        self.as_actor('independent', 'review', value=self.report())
        self.assertTrue(pilot.review_current(self.repo, self.doc))
        changed = deepcopy(spec)
        changed['tasks'].append({'id': 'follow-up', 'description': 'New blocking work', 'owner': 'worker'})
        self.apply('plan', value=changed, reason='new work', owner_approval=None)
        self.assertFalse(pilot.review_current(self.repo, self.doc), 'a plan revision kept the review current')

    def test_unfinished_implementation_work_ends_review_currency(self):
        spec = deepcopy(self.spec)
        spec['tasks'].append({'id': 'later', 'description': 'More work', 'owner': 'worker', 'kind': 'review'})
        self.doc = pilot.create(self.repo, 'Later work', 'lead', spec)
        self.implemented()
        self.apply('review', value=self.report())
        self.assertTrue(pilot.review_current(self.repo, self.doc))
        self.task(run=2, summary='reopened for a fix')
        self.assertEqual(self.doc['state'], 'reviewed')
        self.assertFalse(pilot.review_current(self.repo, self.doc))
        self.assertEqual(pilot.summarize(self.repo, self.doc)['review_applicable'], False)

    # -- direct completion and batches ------------------------------------------------

    def test_pending_task_completes_in_one_write_and_superseded_runs_stay_refused(self):
        revision = self.doc['revision']
        self.task('done', summary='already correct; nothing to edit')
        task = self.doc['tasks'][0]
        self.assertEqual((task['status'], task['run'], self.doc['revision'], self.doc['state']), ('done', 1, revision + 1, 'working'))
        self.assertEqual([(a['run'], a['outcome'], a['checkout']) for a in task['attempts']], [(1, 'done', None)])
        self.assertIsNone(runtime.claim_of(self.repo, self.repo))
        self.task('done', summary='already correct; nothing to edit')
        self.assertEqual(self.doc['revision'], revision + 1, 'an identical repeat wrote the record')
        with self.assertRaisesRegex(CycleError, 'late or mismatched result: task build is done at run 1'):
            self.task('done', summary='a different late answer')
        with self.assertRaisesRegex(CycleError, 'invalid transition: task build is already done at run 1'):
            self.task('done', run=2, summary='again')

    def test_direct_completion_names_the_next_run_and_respects_reassignment(self):
        with self.assertRaisesRegex(CycleError, 'invalid transition: a result for pending task build names run 1'):
            self.task('done', run=2)
        with self.assertRaisesRegex(CycleError, 'late or mismatched result: task build is pending at run 0'):
            self.task('done', run=0)
        self.task(); self.task(owner='replacement', run=2, summary='old host ended; reassigned')
        with self.assertRaisesRegex(CycleError, 'late or mismatched result: task build is working at run 2 owned by replacement'):
            self.task('done', owner='worker', run=1)
        self.task('blocked', owner='replacement', run=2, summary='needs an input')
        with self.assertRaisesRegex(CycleError, 'late or mismatched'):
            self.task('done', owner='worker', run=1)
        self.task('done', owner='replacement', run=3, summary='input arrived; finished')
        self.assertEqual(self.doc['tasks'][0]['status'], 'done')

    def observation(self, **kwargs):
        return {'check_id': 'focused', 'executed_command': 'python -m unittest test_value', 'tested_revision': self.git('rev-parse', 'HEAD'),
                'result': 'passed', 'summary': 'value check passed', 'reason': 'Changed behavior and related caller', **kwargs}

    def test_batch_applies_tasks_and_checks_in_one_revision(self):
        revision = self.doc['revision']
        self.apply('batch', value={'tasks': [{'task': 'build', 'owner': 'worker', 'run': 1, 'status': 'done', 'summary': 'corrected'}],
                                   'checks': [self.observation(), self.observation(summary='second run', executed_command='python -m unittest -v test_value')]})
        self.assertEqual(self.doc['revision'], revision + 1)
        self.assertEqual(self.doc['tasks'][0]['status'], 'done')
        self.assertEqual([(c['command'], c['result'], c['tested_revision'], c['reason']) for c in self.doc['checks']],
                         [('python -m unittest test_value', 'passed', self.git('rev-parse', 'HEAD'), 'Changed behavior and related caller'),
                          ('python -m unittest -v test_value', 'passed', self.git('rev-parse', 'HEAD'), 'Changed behavior and related caller')])

    def test_rejected_batch_changes_neither_the_record_nor_the_claims(self):
        before = self.record_bytes()
        start = {'task': 'build', 'owner': 'worker', 'run': 1, 'status': 'working'}
        for label, value, message in (
                ('bad check after a valid task', {'tasks': [start], 'checks': [self.observation(), self.observation(result='skipped')]}, 'batch check 1: check requires a passed or failed'),
                ('late task after a valid one', {'tasks': [start, {**start, 'status': 'done', 'run': 5, 'summary': 'x'}]}, 'batch task 1 .build.: late or mismatched'),
                ('unknown key', {'tasks': [start], 'notes': []}, 'batch accepts only tasks and checks'),
                ('empty', {'tasks': [], 'checks': []}, 'batch requires')):
            with self.subTest(case=label):
                with self.assertRaisesRegex(CycleError, message):
                    self.apply('batch', value=value)
                self.assertEqual(self.record_bytes(), before)
                self.assertIsNone(runtime.claim_of(self.repo, self.repo), 'a refused batch left a checkout claim')
        # Positive control: the valid part of the first batch alone is accepted and claims the checkout.
        self.apply('batch', value={'tasks': [start], 'checks': [self.observation()]})
        self.assertNotEqual(self.record_bytes(), before)
        self.assertIsNotNone(runtime.claim_of(self.repo, self.repo))

    # -- batches are atomic across the record and the checkout claims -----------------

    def two_task_pilot(self, title='Two tasks'):
        spec = deepcopy(self.spec)
        spec['tasks'] = [{'id': 'first', 'description': 'First unit', 'owner': 'worker'},
                         {'id': 'second', 'description': 'Second unit', 'owner': 'other-worker'}]
        self.doc = pilot.create(self.repo, title, 'lead', spec)
        return self.doc

    def claims(self):
        path = runtime.common_directory(self.repo) / 'crux/pilot/runtime.json'
        return json.loads(path.read_text())['claims'] if path.exists() else {}

    def start(self, task, owner, run=1, **kwargs):
        return {'task': task, 'owner': owner, 'run': run, 'status': 'working', **kwargs}

    def test_batch_whose_second_task_conflicts_leaves_no_first_task_claim(self):
        self.two_task_pilot()
        before, claims = self.record_bytes(), self.claims()
        with self.assertRaisesRegex(CycleError, 'batch task 1 .second.: checkout is owned by'):
            self.apply('batch', value={'tasks': [self.start('first', 'worker'), self.start('second', 'other-worker')]})
        self.assertEqual((self.record_bytes(), self.claims()), (before, claims))
        self.assertIsNone(runtime.claim_of(self.repo, self.repo), 'the first task of a refused batch kept its claim')
        # Positive control: the first task alone claims the checkout.
        self.apply('batch', value={'tasks': [self.start('first', 'worker')]})
        self.assertEqual(runtime.claim_of(self.repo, self.repo)['task'], 'first')

    def test_rejected_batch_preserves_preexisting_claims(self):
        other = pilot.create(self.repo, 'Other', 'other-lead', self.spec)
        checkout = Path(self.temp.name) / 'parallel'
        self.git('worktree', 'add', '-qb', 'parallel', str(checkout), 'HEAD')
        pilot.mutate(self.repo, other['id'], 'other-lead', other['revision'], 'task',
                     SimpleNamespace(task='build', owner='other', run=1, status='working', checkout=str(checkout), summary='start'))
        self.two_task_pilot()
        self.apply('batch', value={'tasks': [self.start('first', 'worker')]})
        before, claims = self.record_bytes(), self.claims()
        self.assertEqual(len(claims), 2)
        # The batch would release this pilot's own claim, then asks for the checkout the other pilot holds.
        with self.assertRaisesRegex(CycleError, 'batch task 1 .second.: checkout is owned by'):
            self.apply('batch', value={'tasks': [{'task': 'first', 'owner': 'worker', 'run': 1, 'status': 'done', 'summary': 'finished'},
                                                 self.start('second', 'other-worker', checkout=str(checkout))]})
        self.assertEqual((self.record_bytes(), self.claims()), (before, claims), 'a refused batch changed the record or a claim')
        self.assertEqual(runtime.claim_of(self.repo, checkout)['cycle'], other['id'])
        self.assertEqual(runtime.claim_of(self.repo, self.repo)['task'], 'first')

    def test_successful_batch_hands_one_checkout_from_a_finished_task_to_the_next(self):
        self.two_task_pilot()
        self.apply('batch', value={'tasks': [self.start('first', 'worker')]})
        revision = self.doc['revision']
        self.apply('batch', value={'tasks': [{'task': 'first', 'owner': 'worker', 'run': 1, 'status': 'done', 'summary': 'finished'},
                                             self.start('second', 'other-worker')],
                                   'checks': [self.observation()]})
        self.assertEqual(self.doc['revision'], revision + 1)
        self.assertEqual([t['status'] for t in self.doc['tasks']], ['done', 'working'])
        self.assertEqual(len(self.doc['checks']), 1)
        claim = runtime.claim_of(self.repo, self.repo)
        self.assertEqual((claim['task'], claim['owner'], claim['run']), ('second', 'other-worker', 1))
        self.assertEqual(len(self.claims()), 1)

    def test_concurrent_claims_of_one_checkout_cannot_both_succeed(self):
        pilots = [pilot.create(self.repo, f'Racer {n}', f'lead-{n}', self.spec) for n in range(4)]
        gate, outcomes = threading.Barrier(len(pilots)), {}

        def race(doc):
            gate.wait()
            try:
                pilot.mutate(self.repo, doc['id'], doc['lead'], doc['revision'], 'batch',
                             SimpleNamespace(value={'tasks': [{'task': 'build', 'owner': 'worker', 'run': 1, 'status': 'working'}]}))
                outcomes[doc['id']] = 'claimed'
            except CycleError as exc:
                outcomes[doc['id']] = str(exc)
        threads = [threading.Thread(target=race, args=(doc,)) for doc in pilots]
        for thread in threads: thread.start()
        for thread in threads: thread.join(30)
        winners = [ident for ident, outcome in outcomes.items() if outcome == 'claimed']
        self.assertEqual(len(outcomes), len(pilots), outcomes)
        self.assertEqual(len(winners), 1, outcomes)
        self.assertEqual(runtime.claim_of(self.repo, self.repo)['cycle'], winners[0])
        for doc in pilots:
            status = pilot.load_pilot(self.repo, doc['id'])['tasks'][0]['status']
            self.assertEqual(status, 'working' if doc['id'] == winners[0] else 'pending')
            if doc['id'] != winners[0]:
                self.assertIn('checkout is owned by', outcomes[doc['id']])

    def test_failed_record_write_restores_the_claims(self):
        before, claims = self.record_bytes(), self.claims()
        record = pilot.path_of(self.repo, self.doc['id'])
        real = runtime.atomic

        def failing(path, value):
            if Path(path) == record:
                raise OSError('disk full')
            return real(path, value)
        with patch.object(runtime, 'atomic', side_effect=failing):
            with self.assertRaisesRegex(runtime.RuntimeRefusal, 'disk full'):
                self.apply('batch', value={'tasks': [self.start('build', 'worker')]})
        self.assertEqual((self.record_bytes(), self.claims()), (before, claims), 'a failed record write left a claim')
        self.apply('batch', value={'tasks': [self.start('build', 'worker')]})
        self.assertIsNotNone(runtime.claim_of(self.repo, self.repo))

    # -- a process killed at a persistence boundary ------------------------------------

    KILLED_WRITER = """
import json, os, sys
sys.path.insert(0, sys.argv[1])
import cycle_pilot as pilot, cycle_runtime as runtime
from types import SimpleNamespace
repo, identity, lead, revision, boundary, value = json.loads(sys.argv[2])
record, real = str(pilot.path_of(repo, identity)), runtime.atomic
def atomic(path, data):
    if boundary == 'before-record' and str(path) == record:
        os._exit(77)            # the claims are on disk; the record is not
    result = real(path, data)
    if boundary == 'after-record' and str(path) == record:
        os._exit(77)            # the record is on disk; the released claims are not yet dropped
    return result
runtime.atomic = atomic
pilot.mutate(repo, identity, lead, revision, 'batch', SimpleNamespace(value=value))
os._exit(0)
"""

    def killed_write(self, boundary, value, doc=None):
        """Run one batch write in a real process that dies, with no cleanup, at `boundary`."""
        doc = doc or self.doc
        result = subprocess.run([sys.executable, '-c', self.KILLED_WRITER, str(Path(pilot.__file__).parent),
                                 json.dumps([str(self.repo), doc['id'], doc['lead'], doc['revision'], boundary, value])],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 77, result.stderr)

    def recover(self, doc=None):
        doc = pilot.load_pilot(self.repo, (doc or self.doc)['id'])
        return pilot.mutate(self.repo, doc['id'], doc['lead'], doc['revision'], 'recover', SimpleNamespace())

    def other_owner(self):
        """Another pilot holding another checkout: its claim must survive every recovery."""
        other = pilot.create(self.repo, 'Other', 'other-lead', self.spec)
        checkout = Path(self.temp.name) / 'parallel'
        self.git('worktree', 'add', '-qb', 'parallel', str(checkout), 'HEAD')
        pilot.mutate(self.repo, other['id'], 'other-lead', other['revision'], 'task',
                     SimpleNamespace(task='build', owner='other', run=1, status='working', checkout=str(checkout), summary='start'))
        return other, str(checkout.resolve())

    def test_killed_between_the_claim_and_the_record_is_recovered_and_replays_harmlessly(self):
        other, held = self.other_owner()
        before = self.record_bytes()
        self.killed_write('before-record', {'tasks': [self.start('build', 'worker')]})
        # The stranded state: the claim is on disk and the record never learned of the assignment.
        main = str(self.repo.resolve())
        self.assertEqual(self.record_bytes(), before)
        self.assertEqual({k: v['cycle'] for k, v in self.claims().items()}, {held: other['id'], main: self.doc['id']})
        # Before recovery the checkout is refused to anyone else: no timeout guesses that the owner died.
        third = pilot.create(self.repo, 'Third', 'third-lead', self.spec)
        claim = SimpleNamespace(value={'tasks': [self.start('build', 'worker')]})
        with self.assertRaisesRegex(CycleError, 'checkout is owned by'):
            pilot.mutate(self.repo, third['id'], 'third-lead', third['revision'], 'batch', claim)
        # Another pilot's recovery does not touch a claim that is not its own.
        self.assertEqual(self.recover(other)['recovered'], [])
        self.assertIn(main, self.claims())
        recovered = self.recover()
        self.assertEqual(len(recovered['recovered']), 1)
        self.assertIn('removed the claim on ' + main, recovered['recovered'][0])
        self.assertEqual((self.record_bytes(), {k: v['cycle'] for k, v in self.claims().items()}), (before, {held: other['id']}))
        # Replay: a second recovery finds nothing and changes nothing.
        claims = self.claims()
        self.assertEqual(self.recover()['recovered'], [])
        self.assertEqual((self.record_bytes(), self.claims()), (before, claims))
        # The freed checkout can now be claimed, and the interrupted write can simply be retried.
        pilot.mutate(self.repo, third['id'], 'third-lead', third['revision'], 'batch', claim)
        self.assertEqual(self.claims()[main]['cycle'], third['id'])

    def test_retrying_the_interrupted_write_recovers_without_a_separate_command(self):
        other, held = self.other_owner()
        self.killed_write('before-record', {'tasks': [self.start('build', 'worker')]})
        self.apply('batch', value={'tasks': [self.start('build', 'worker')]})
        claim = runtime.claim_of(self.repo, self.repo)
        self.assertEqual((self.doc['tasks'][0]['status'], claim['cycle'], claim['run']), ('working', self.doc['id'], 1))
        self.assertEqual(self.claims()[held]['cycle'], other['id'])
        self.assertEqual(self.recover()['recovered'], [], 'a claim the record backs was treated as a leftover')

    def test_killed_between_the_record_and_the_released_claim_is_recovered(self):
        other, held = self.other_owner()
        self.task()
        main = str(self.repo.resolve())
        self.killed_write('after-record', {'tasks': [{'task': 'build', 'owner': 'worker', 'run': 1, 'status': 'done', 'summary': 'finished'}]})
        # The record is the commit point: the task is done, and the claim it released is still on disk.
        self.doc = pilot.load_pilot(self.repo, self.doc['id'])
        self.assertEqual(self.doc['tasks'][0]['status'], 'done')
        self.assertEqual(self.claims()[main]['cycle'], self.doc['id'])
        record = self.record_bytes()
        self.assertIn('removed the claim on ' + main, self.recover()['recovered'][0])
        self.assertEqual((self.record_bytes(), {k: v['cycle'] for k, v in self.claims().items()}), (record, {held: other['id']}))
        self.assertEqual(self.recover()['recovered'], [])

    def test_a_kill_never_leaves_a_working_assignment_without_its_claim(self):
        """A batch that hands one checkout from a finished task to the next, killed at each boundary."""
        for boundary in ('before-record', 'after-record'):
            with self.subTest(boundary=boundary):
                self.two_task_pilot('Handover ' + boundary)
                self.apply('batch', value={'tasks': [self.start('first', 'worker')]})
                self.killed_write(boundary, {'tasks': [{'task': 'first', 'owner': 'worker', 'run': 1, 'status': 'done', 'summary': 'finished'},
                                                       self.start('second', 'other-worker')]})
                self.doc = pilot.load_pilot(self.repo, self.doc['id'])
                working = [t['id'] for t in self.doc['tasks'] if t['status'] == 'working']
                self.assertEqual(working, ['first'] if boundary == 'before-record' else ['second'])
                self.assertIsNotNone(runtime.claim_of(self.repo, self.repo), 'the working task has no claim at all')
                self.recover()
                claim = runtime.claim_of(self.repo, self.repo)
                self.assertEqual((claim['cycle'], claim['task']), (self.doc['id'], working[0]))
                # Finish the cycle's work so the next subtest starts with a free checkout.
                self.apply('batch', value={'tasks': [{'task': working[0], 'owner': claim['owner'], 'run': 1, 'status': 'done', 'summary': 'finished'}]})
                self.assertIsNone(runtime.claim_of(self.repo, self.repo))

    def test_cli_recover_reports_what_it_reconciled(self):
        import cycle
        self.killed_write('before-record', {'tasks': [self.start('build', 'worker')]})
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = cycle.main(['--repo-root', str(self.repo), 'pilot', 'recover', self.doc['id'], '--actor', 'lead', '--expect-revision', str(self.doc['revision'])])
        out = json.loads(output.getvalue())
        self.assertEqual((code, len(out['recovered']), out['revision']), (0, 1, self.doc['revision']), out)
        self.assertIsNone(runtime.claim_of(self.repo, self.repo))

    def test_cli_batch_and_reviewer_review(self):
        import cycle
        self.task(); (self.repo / 'src/value.py').write_text('value = 2\n')
        self.git('add', 'src/value.py'); self.git('commit', '-qm', 'correct value')

        def run(*argv):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = cycle.main(['--repo-root', str(self.repo), 'pilot', *argv])
            return code, json.loads(output.getvalue())
        batch = Path(self.temp.name) / 'batch.json'
        batch.write_text(json.dumps({'tasks': [{'task': 'build', 'owner': 'worker', 'run': 1, 'status': 'done', 'summary': 'corrected'}],
                                     'checks': [self.observation()]}))
        code, out = run('batch', self.doc['id'], '--actor', 'lead', '--expect-revision', str(self.doc['revision']), '--file', str(batch))
        self.assertEqual((code, out['pilot']['completed']), (0, 1), out)
        code, out = run('review-start', self.doc['id'], '--actor', 'lead', '--expect-revision', str(out['pilot']['revision']), '--reviewer', 'independent')
        self.assertEqual(code, 0, out)
        self.doc = pilot.load_pilot(self.repo, self.doc['id'])
        report = Path(self.temp.name) / 'review.json'
        report.write_text(json.dumps(self.report()))
        code, refused = run('review', self.doc['id'], '--actor', 'lead', '--expect-revision', str(self.doc['revision']), '--file', str(report))
        self.assertEqual(code, 1); self.assertIn('never records its verdict', refused['error'])
        code, out = run('review', self.doc['id'], '--actor', 'independent', '--expect-revision', str(self.doc['revision']), '--file', str(report))
        self.assertEqual((code, out['pilot']['state'], out['pilot']['review_applicable'], out['pilot']['finished']), (0, 'reviewed', True, False), out)

    def test_stale_writer_and_late_task_return_preserve_current_work(self):
        original = pilot.path_of(self.repo, self.doc['id']).read_bytes()
        with self.assertRaisesRegex(CycleError, 'stale revision'):
            pilot.mutate(self.repo, self.doc['id'], 'lead', 0, 'pause', SimpleNamespace(reason='stop'))
        self.assertEqual(pilot.path_of(self.repo, self.doc['id']).read_bytes(), original)
        self.task(); self.task(owner='replacement', run=2, summary='old host ended; reassigned')
        with self.assertRaisesRegex(CycleError, 'late or mismatched'):
            self.task('done', owner='worker', run=1)
        self.task('done', owner='replacement', run=2)
        self.assertEqual(self.doc['tasks'][0]['attempts'][0]['outcome'], 'interrupted')

    def test_same_checkout_and_subdirectory_claims_conflict(self):
        self.task()
        other = pilot.create(self.repo, 'Other', 'other-lead', self.spec)
        request = SimpleNamespace(task='build', owner='other', run=1, status='working', checkout=str(self.repo / 'src'), summary='start')
        with self.assertRaisesRegex(CycleError, 'checkout is owned'):
            pilot.mutate(self.repo, other['id'], 'other-lead', other['revision'], 'task', request)
        self.task('done')
        self.assertIsNone(runtime.claim_of(self.repo, self.repo))

    def test_distinct_checkouts_can_work_concurrently(self):
        other = pilot.create(self.repo, 'Other', 'other-lead', self.spec)
        self.task()
        checkout = Path(self.temp.name) / 'parallel'
        self.git('worktree', 'add', '-qb', 'parallel', str(checkout), 'HEAD')
        request = SimpleNamespace(task='build', owner='other', run=1, status='working', checkout=str(checkout), summary='start')
        changed = pilot.mutate(self.repo, other['id'], 'other-lead', other['revision'], 'task', request)
        self.assertEqual(changed['tasks'][0]['checkout'], str(checkout.resolve()))
        self.assertNotEqual(runtime.claim_of(self.repo, self.repo), runtime.claim_of(self.repo, checkout))

    def test_pause_resume_retains_assignment_and_requires_observation(self):
        self.task()
        self.apply('pause', reason='owner stopped work')
        with self.assertRaises(CycleError):
            self.apply('resume', reason='continue', reconcile='')
        self.assertIsNotNone(runtime.claim_of(self.repo, self.repo))
        self.apply('resume', reason='owner resumed', reconcile='Checked Git status/diff and observed worker still owns run one')
        self.assertEqual(self.doc['state'], 'working')
        self.assertEqual(self.doc['tasks'][0]['run'], 1)

    def test_review_blocks_self_review_dirty_source_and_failed_selection(self):
        self.implemented()
        with self.assertRaisesRegex(CycleError, 'independent'):
            self.apply('review', value=self.report(reviewer='worker'))
        (self.repo / 'src/value.py').write_text('value = 3\n')
        with self.assertRaisesRegex(CycleError, 'uncommitted source'):
            self.apply('review', value=self.report())
        (self.repo / 'src/value.py').write_text('value = 2\n')
        self.check('failed')
        with self.assertRaisesRegex(CycleError, 'passing selected'):
            self.apply('review', value=self.report())
        self.check()
        self.apply('review', value=self.report())
        self.assertTrue(pilot.review_current(self.repo, self.doc))

    def test_review_finding_becomes_task_without_phase_return(self):
        self.implemented()
        self.apply('review', value=self.report(verdict='changes-required', blocking=['Cover negative value']))
        self.assertEqual(self.doc['state'], 'working')
        self.assertEqual(self.doc['tasks'][-1]['description'], 'Cover negative value')
        self.assertEqual(self.doc['tasks'][-1]['status'], 'pending')

    def test_bookkeeping_preserves_review_but_source_change_does_not(self):
        self.implemented(); self.apply('review', value=self.report())
        self.git('add', 'bionic/cycles'); self.git('commit', '-qm', 'checkpoint progress')
        self.assertTrue(pilot.review_current(self.repo, self.doc))
        (self.repo / 'src/value.py').write_text('value = 3\n')
        self.git('add', 'src/value.py'); self.git('commit', '-qm', 'later change')
        self.assertFalse(pilot.review_current(self.repo, self.doc))
        summary = pilot.summarize(self.repo, self.doc)
        self.assertEqual((summary['state'], summary['review']['verdict'], summary['review_applicable']), ('reviewed', 'approve', False))

    def test_source_rename_into_bookkeeping_is_not_reviewed_code(self):
        self.implemented(); self.apply('review', value=self.report())
        target = pilot.path_of(self.repo, self.doc['id']).parent / 'moved.py'
        self.git('mv', 'src/value.py', str(target))
        self.assertFalse(pilot.review_current(self.repo, self.doc))
        self.git('commit', '-qm', 'move source into records')
        self.assertFalse(pilot.review_current(self.repo, self.doc))

    def test_identical_results_and_explicit_reuse_survive_plan_revisions(self):
        self.check()
        original = self.doc['checks'][-1]['id']
        for iteration in range(2):
            changed = deepcopy(self.spec)
            changed['goal'] += ' revision ' + str(iteration)
            self.apply('plan', value=changed, reason='clarify outcome', owner_approval=None)
            self.apply('check', value={'check_id': 'focused', 'reuse': original,
                       'summary': 'Still applicable', 'reason': 'No relevant behavior changed'})
            self.assertTrue(pilot.checks_pass(self.doc))
        changed['goal'] += ' final'
        self.apply('plan', value=changed, reason='clarify again', owner_approval=None)
        self.check()
        self.assertTrue(pilot.checks_pass(self.doc))

    def test_started_task_cannot_disappear_or_become_review_work(self):
        self.implemented()
        changed = deepcopy(self.spec)
        changed['tasks'] = [{'id': 'replacement', 'description': 'Other work'}]
        with self.assertRaisesRegex(CycleError, 'retain started'):
            self.apply('plan', value=changed, reason='replace tasks', owner_approval=None)
        changed['tasks'] = [{'id': 'build', 'description': 'Correct the value', 'kind': 'review'}]
        with self.assertRaisesRegex(CycleError, 'retain the kind'):
            self.apply('plan', value=changed, reason='reclassify', owner_approval=None)

    # -- finish, delivery facts and reopening ----------------------------------------

    def reviewed(self):
        self.implemented(); self.apply('review', value=self.report())
        return self.doc

    def test_reviewed_cycle_completes_before_any_pr_and_claims_no_delivery(self):
        self.reviewed()
        self.assertEqual(pilot.summarize(self.repo, self.doc)['finished'], False)
        self.apply('finish', summary='Value corrected and reviewed')
        self.assertEqual(self.doc['state'], 'completed')
        self.assertEqual(self.doc['delivery'], {'pr': None, 'ci': 'unknown', 'merge': 'unmerged', 'commit': None})
        self.assertEqual((self.doc['completion']['summary'], self.doc['completion']['reviewer']), ('Value corrected and reviewed', 'independent'))
        self.assertEqual(self.doc['completion']['review_head'], self.doc['review']['head_commit'])
        summary = pilot.summarize(self.repo, self.doc)
        self.assertEqual((summary['state'], summary['finished'], summary['review_applicable'], summary['review']['verdict']),
                         ('completed', True, None, 'approve'))
        revision, before = self.doc['revision'], self.record_bytes()
        self.apply('finish', summary='a second summary')
        self.assertEqual((self.doc['revision'], self.record_bytes()), (revision, before), 'a repeated finish wrote the record')

    def test_failed_checks_blocking_findings_and_obsolete_review_prevent_completion(self):
        self.task(); (self.repo / 'src/value.py').write_text('value = 2\n')
        self.git('add', 'src/value.py'); self.git('commit', '-qm', 'correct value')
        with self.assertRaisesRegex(CycleError, 'every implementation task done; unfinished: build'):
            self.apply('finish', summary=None)
        self.task('done')
        with self.assertRaisesRegex(CycleError, 'every selected check to pass; missing or failed: focused'):
            self.apply('finish', summary=None)
        self.check()
        with self.assertRaisesRegex(CycleError, 'requires an independent review; none is recorded'):
            self.apply('finish', summary=None)
        self.apply('review', value=self.report(verdict='changes-required', blocking=['Cover negative value'],
                                               acceptance=[{'criterion': 0, 'met': False, 'evidence': 'missing case'}]))
        self.apply('task', task=self.doc['tasks'][-1]['id'], owner='lead', run=1, status='done', summary='covered')
        with self.assertRaisesRegex(CycleError, 'approving review with no blocking finding'):
            self.apply('finish', summary=None)
        self.apply('review', value=self.report())
        self.check('failed')
        with self.assertRaisesRegex(CycleError, 'every selected check to pass'):
            self.apply('finish', summary=None)
        self.check()
        (self.repo / 'src/value.py').write_text('value = 3\n')
        with self.assertRaisesRegex(CycleError, 'obsolete review: reviewed paths changed after the reviewed head: src/value.py'):
            self.apply('finish', summary=None)
        self.git('add', 'src/value.py'); self.git('commit', '-qm', 'change after review')
        with self.assertRaisesRegex(CycleError, 'obsolete review: reviewed paths changed after the reviewed head: src/value.py'):
            self.apply('finish', summary=None)
        (self.repo / 'src/value.py').write_text('value = 2\n')
        self.git('add', 'src/value.py'); self.git('commit', '-qm', 'restore the reviewed content')
        changed = deepcopy(self.spec); changed['goal'] += ' and document it'; changed.pop('tasks')
        self.apply('plan', value=changed, reason='clarify', owner_approval=None)
        self.check()
        with self.assertRaisesRegex(CycleError, 'obsolete review: it approved a superseded plan revision'):
            self.apply('finish', summary=None)
        self.assertNotEqual(self.doc['state'], 'completed')
        # Positive control: the same cycle finishes once the review covers the current plan and code.
        self.apply('review', value=self.report()); self.apply('finish', summary=None)
        self.assertEqual(self.doc['state'], 'completed')

    def test_later_commits_elsewhere_neither_block_finish_nor_reopen_a_completed_cycle(self):
        self.reviewed()
        (self.repo / 'src/other.py').write_text('other = 1\n')
        self.git('add', 'src/other.py'); self.git('commit', '-qm', 'another cycle, another path')
        self.assertEqual(pilot.applicability(self.repo, self.doc), (True, 'the reviewed paths hold the reviewed content'))
        self.apply('finish', summary=None)
        (self.repo / 'src/value.py').write_text('value = 9\n')
        self.git('add', 'src/value.py'); self.git('commit', '-qm', 'later work on the reviewed path')
        self.doc = pilot.load_pilot(self.repo, self.doc['id'])
        summary = pilot.summarize(self.repo, self.doc)
        self.assertEqual((summary['state'], summary['finished'], summary['review']['verdict'], summary['review_applicable']),
                         ('completed', True, 'approve', None))
        with self.assertRaisesRegex(CycleError, 'a completed pilot takes delivery facts only'):
            self.task(run=2, summary='more work')

    def test_work_recorded_after_the_approval_makes_the_review_obsolete(self):
        self.reviewed()
        self.assertTrue(pilot.review_recorded(self.doc))
        # The lead runs the finished task again and commits only a new path, which the path comparison cannot see.
        self.task(run=2, summary='one more change')
        (self.repo / 'src/extra.py').write_text('extra = 1\n')
        self.git('add', 'src/extra.py'); self.git('commit', '-qm', 'new path after approval')
        self.task('done', run=2, summary='added')
        self.assertFalse(pilot.review_recorded(self.doc))
        with self.assertRaisesRegex(CycleError, 'obsolete review: an implementation task was added or run again after the approval'):
            self.apply('finish', summary=None)
        self.apply('review', value=self.report()); self.apply('finish', summary=None)
        self.assertEqual(self.doc['state'], 'completed')

    def test_direct_completion_releases_a_claim_an_interrupted_write_left(self):
        with runtime.locked(self.repo) as state:  # what a process killed after the claims flush leaves behind
            state['claims'][str(self.repo.resolve())] = {'cycle': self.doc['id'], 'task': 'build', 'owner': 'worker', 'run': 1,
                                                         'checkout': str(self.repo.resolve())}
            state['claims']['/elsewhere'] = {'cycle': 'CYC-9999', 'task': 'build', 'owner': 'x', 'run': 1, 'checkout': '/elsewhere'}
        self.task('done', summary='finished without a working write')
        self.assertEqual(list(self.claims()), ['/elsewhere'], 'another cycle\'s claim was touched, or this task\'s was left')

    def test_delivery_facts_are_independent_and_a_ci_failure_never_reopens(self):
        import cycle
        self.reviewed()
        self.apply('delivery', value={'pr': 'https://example.invalid/pr/1', 'ci': 'passed', 'merge': 'merged', 'commit': 'abc1234'})
        self.assertEqual(self.doc['state'], 'reviewed', 'a merge fact completed the cycle')
        self.apply('finish', summary=None)
        tasks = len(self.doc['tasks'])
        value = Path(self.temp.name) / 'delivery.json'
        value.write_text(json.dumps({'ci': 'failed', 'published': 'v9.9.9 beta'}))
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = cycle.main(['--repo-root', str(self.repo), 'pilot', 'delivery', self.doc['id'], '--actor', 'lead',
                               '--expect-revision', str(self.doc['revision']), '--file', str(value)])
        out = json.loads(output.getvalue())
        self.assertEqual(code, 0, out)
        self.doc = pilot.load_pilot(self.repo, self.doc['id'])
        self.assertEqual((self.doc['state'], len(self.doc['tasks']), self.doc['delivery']['ci'], self.doc['delivery']['published']),
                         ('completed', tasks, 'failed', 'v9.9.9 beta'))
        self.assertIn('Offer the owner the choice', out['offer'])
        self.assertIn('--follows ' + self.doc['id'], out['offer'])
        with self.assertRaisesRegex(CycleError, 'delivery accepts only'):
            self.apply('delivery', value={'mode': 'direct'})

    def test_authorized_reopening_keeps_history_and_needs_a_reviewed_repair(self):
        self.reviewed()
        with self.assertRaisesRegex(CycleError, 'only a completed pilot reopens'):
            self.apply('reopen', reason='r', owner_instruction='o', value=[{'id': 'repair', 'description': 'Fix'}])
        self.apply('finish', summary='First completion')
        first_completion, first_review, checks = self.doc['completion'], self.doc['review'], len(self.doc['checks'])
        for label, kwargs, message in (
                ('no instruction', dict(reason='CI failed', owner_instruction='', value=[{'id': 'repair', 'description': 'Fix'}]), "owner's actual instruction"),
                ('no reason', dict(reason='', owner_instruction='reopen it', value=[{'id': 'repair', 'description': 'Fix'}]), 'reopen reason'),
                ('no task', dict(reason='CI failed', owner_instruction='reopen it', value=[]), 'at least one repair task'),
                ('reused task id', dict(reason='CI failed', owner_instruction='reopen it', value=[{'id': 'build', 'description': 'Fix'}]), 'new id')):
            with self.subTest(case=label), self.assertRaisesRegex(CycleError, message):
                self.apply('reopen', **kwargs)
        self.assertEqual(self.doc['state'], 'completed')
        self.apply('reopen', reason='PR CI failed on a negative value', owner_instruction='Reopen CYC for the repair.',
                   value=[{'id': 'repair', 'description': 'Handle a negative value', 'owner': 'worker'}])
        entry = self.doc['history'][-1]
        self.assertEqual((self.doc['state'], entry['kind'], entry['owner_instruction'], entry['completion'], entry['review']),
                         ('working', 'reopen', 'Reopen CYC for the repair.', first_completion, first_review))
        self.assertEqual(len(self.doc['checks']), checks, 'reopening dropped or added check observations')
        with self.assertRaisesRegex(CycleError, 'unfinished: repair'):
            self.apply('finish', summary=None)
        self.apply('task', task='repair', owner='worker', run=1, status='working', checkout=None, summary='start')
        (self.repo / 'src/value.py').write_text('value = abs(2)\n')
        self.git('add', 'src/value.py'); self.git('commit', '-qm', 'repair')
        self.apply('task', task='repair', owner='worker', run=1, status='done', checkout=None, summary='repaired')
        # The earlier approval does not cover the repair, even with every task done and every check passing.
        self.assertFalse(pilot.review_recorded(self.doc))
        with self.assertRaisesRegex(CycleError, 'obsolete review: it predates the reopening'):
            self.apply('finish', summary=None)
        self.apply('review', value=self.report())
        self.apply('finish', summary='Completed again after the repair')
        self.assertEqual(self.doc['state'], 'completed')
        self.assertEqual(self.doc['completion']['summary'], 'Completed again after the repair')
        kinds = [h['kind'] for h in self.doc['history']]
        self.assertEqual((kinds.count('reopen'), kinds.count('review')), (1, 1), 'the earlier review or the reopening left the history')
        self.assertEqual(pilot.summarize(self.repo, self.doc)['reopened'], 1)

    def test_a_linked_cycle_names_the_cycle_it_follows(self):
        self.reviewed(); self.apply('finish', summary=None)
        linked = pilot.create(self.repo, 'Separate repair', 'lead', self.spec, follows=self.doc['id'])
        self.assertEqual(linked['follows'], self.doc['id'])
        with self.assertRaisesRegex(CycleError, 'names no cycle record'):
            pilot.create(self.repo, 'Orphan', 'lead', self.spec, follows='CYC-9999')

    def test_council_required_only_blocks_dependent_tasks(self):
        specification = deepcopy(self.spec)
        specification['council'] = {'needed': True, 'reason': 'Consequential alternatives', 'approach': 'Use one shared writer', 'questions': ['Is ownership sufficient?']}
        specification['tasks'].append({'id': 'research', 'description': 'Read existing interfaces', 'council': False, 'kind': 'review'})
        self.doc = pilot.create(self.repo, 'Consequential', 'lead', specification)
        with self.assertRaisesRegex(CycleError, 'council-required'):
            self.task()
        self.apply('task', task='research', owner='reader', run=1, status='working', checkout=None, summary='independent research')
        subject = pilot.council_subject(self.repo, self.doc)
        snapshot = json.loads((tree(self.repo).docs_root / subject).read_text())
        self.assertEqual(snapshot['plan']['council']['approach'], 'Use one shared writer')
        self.assertEqual({t['id'] for t in snapshot['tasks']}, {'build', 'research'})

    def test_allocator_is_shared_with_legacy_and_burns_ids_across_worktrees(self):
        old = legacy_create(self.repo, 'quick-fix', 'Legacy', 'Outcome', ['src'], ['works'], 'builder', 'tester')
        later = pilot.create(self.repo, 'Later', 'lead', self.spec)
        self.assertEqual([self.doc['id'], old['id'], later['id']], ['CYC-0001', 'CYC-0002', 'CYC-0003'])
        with self.assertRaisesRegex(CycleError, 'opt-in pilot'):
            legacy_load(self.repo, self.doc['id'])

    def legacy_editor(self):
        from cycle_workflow import mutate
        old = legacy_create(self.repo, 'quick-fix', 'Legacy', 'Outcome', ['src'], ['works'], 'builder', 'tester')
        mutate(self.repo, old['id'], 'task-add', task={'id': 'edit', 'phase': 'build', 'description': 'Edit source',
               'depends_on': [], 'status': 'pending', 'expected_evidence': ['commit']})
        return old['id']

    def test_legacy_and_pilot_admission_serialize_until_reservation_is_saved(self):
        import cycle_workflow as workflow
        identity = self.legacy_editor()
        entered, release = threading.Event(), threading.Event()
        original = workflow.record_assignment
        def delayed(*args):
            entered.set()
            self.assertTrue(release.wait(5))
            return original(*args)
        with ThreadPoolExecutor(max_workers=2) as workers, patch.object(workflow, 'record_assignment', side_effect=delayed):
            legacy = workers.submit(workflow.mutate, self.repo, identity, 'assignment', id='dev-lead', role='dev-lead', task='edit', state='running')
            self.assertTrue(entered.wait(5))
            modern = workers.submit(self.task)
            try:
                with self.assertRaises(TimeoutError):
                    modern.result(timeout=.1)
            finally:
                release.set()
            legacy.result(timeout=5)
            with self.assertRaisesRegex(CycleError, 'legacy editing'):
                modern.result(timeout=5)
        self.assertIsNone(runtime.claim_of(self.repo, self.repo))

    def test_pilot_claim_blocks_real_legacy_assignment_and_cleanup(self):
        from cycle_workflow import mutate
        from cycle_worktrees import ownership_reason, open_owners
        identity = self.legacy_editor()
        self.task()
        with self.assertRaisesRegex(CycleError, 'held by pilot'):
            mutate(self.repo, identity, 'assignment', id='dev-lead', role='dev-lead', task='edit', state='running')
        owners, problems = open_owners(self.repo)
        self.assertFalse(problems)
        self.assertIn('held by pilot', ownership_reason(self.repo, {'path': str(self.repo)}, [], owners, problems))

    def test_linked_caller_sees_main_legacy_owner_and_cannot_allocate(self):
        from cycle_workflow import mutate
        checkout = Path(self.temp.name) / 'linked'
        self.git('add', 'bionic/cycles')
        self.git('commit', '-qm', 'share pilot plan')
        self.git('worktree', 'add', '-qb', 'linked', str(checkout), 'HEAD')
        identity = self.legacy_editor()
        mutate(self.repo, identity, 'assignment', id='dev-lead', role='dev-lead', task='edit', state='running')
        request = SimpleNamespace(task='build', owner='worker', run=1, status='working', checkout=str(self.repo), summary='start')
        with self.assertRaisesRegex(CycleError, 'legacy editing'):
            pilot.mutate(checkout, self.doc['id'], 'lead', self.doc['revision'], 'task', request)
        with self.assertRaises(CycleError):
            pilot.create(checkout, 'New allocation', 'lead', self.spec)

    def test_record_identity_must_match_directory(self):
        record = deepcopy(self.doc)
        record['id'] = 'CYC-9999'
        pilot.path_of(self.repo, self.doc['id']).write_text(json.dumps(record))
        with self.assertRaisesRegex(CycleError, 'identity does not match'):
            pilot.load_pilot(self.repo, self.doc['id'])

    def test_council_subject_guidance_passes_actual_cli_parser_without_provider_call(self):
        import runpy
        import shlex
        result = pilot.mutate(self.repo, self.doc['id'], 'lead', self.doc['revision'], 'council-subject', SimpleNamespace())
        invocation = shlex.split(result['next'].removeprefix('Run ').split(' with ', 1)[0])
        values = {'SUBJECT': result['subject'], 'IDENTITY': result['identity'], 'QUESTION_FILE': str(Path(self.temp.name) / 'question.txt')}
        argv = [values.get(arg, arg) for arg in invocation[1:]]
        main = runpy.run_path(str(Path(pilot.__file__).with_name('cycle-council.py')))['main']
        with patch.dict(main.__globals__, {'launch_detached': lambda *a, **kw: {'outcome': 'running'}}), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(['--repo-root', str(self.repo), *argv]), 0)

    def test_cli_create_show_and_guarded_milestone(self):
        import cycle
        spec = Path(self.temp.name) / 'plan.json'
        spec.write_text(json.dumps(self.spec))
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = cycle.main(['--repo-root', str(self.repo), 'pilot', 'create', '--title', 'CLI', '--lead', 'lead', '--plan', str(spec)])
        self.assertEqual(code, 0, output.getvalue())
        created = json.loads(output.getvalue())['pilot']
        self.assertEqual(created['state'], 'planning')
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = cycle.main(['--repo-root', str(self.repo), 'pilot', 'show', created['id']])
        self.assertEqual(code, 0, output.getvalue())

    def test_actual_configured_council_binds_exact_plan_and_failure_stays_unresolved(self):
        import httpx
        import cycle_council
        from crux.council.async_council import validate_gate_assignment
        from crux.core.llm_caller import get_model_config
        specification = deepcopy(self.spec)
        specification['council'] = {'needed': True, 'reason': 'Cross-module choice', 'approach': 'One shared writer'}
        self.doc = pilot.create(self.repo, 'Council case', 'lead', specification)
        subject = pilot.council_subject(self.repo, self.doc)
        models = {cfg.api_string: cfg for cfg in (get_model_config(model) for model in validate_gate_assignment().values())}
        def reply(request):
            payload = json.loads(request.content)
            cfg = models[payload['model']]
            vote = {'decision': 'APPROVE', 'confidence': .9, 'reasoning': 'Supported approach', 'findings': []}
            return httpx.Response(200, json={'model': cfg.api_string, 'provider': next(iter(cfg.accepted_served_providers)),
                                  'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(vote)}}]})
        with (patch('crux_env.get', return_value='test-gateway-credential'),
              patch('crux.council.async_council.get', return_value='test-gateway-credential'),
              patch.dict('os.environ', {'OPENROUTER_API_KEY': 'test-gateway-credential'})):
            result = cycle_council.convene(self.repo, 'consultation', subject, 'Review the exact proposed approach',
                       identity='pilot:' + self.doc['id'] + ':plan', transport=httpx.MockTransport(reply))
        self.assertEqual(result['outcome'], 'approved', result)
        self.apply('council', record=result['record'], response='All seats approved; no blocking findings')
        self.assertTrue(pilot.council_current(self.doc))
        self.task()
        self.task('done')
        changed = deepcopy(specification)
        changed['goal'] += ' with expanded approach'
        self.apply('plan', value=changed, reason='new approach', owner_approval=None)
        self.assertFalse(pilot.council_current(self.doc))
        with self.assertRaises(CycleError):
            self.apply('council', record=result['record'], response='Old approval does not cover this revision')


from test_cycle_slice import SliceBase


class PilotLegacyAdmissionTests(SliceBase):
    def claim(self):
        with runtime.locked(self.repo) as state:
            state['claims'][str(self.repo)] = {'cycle': 'CYC-9999', 'task': 'pilot-task', 'owner': 'pilot-worker', 'run': 1}

    def test_real_typed_prepare_refuses_pilot_main_claim(self):
        self.claim()
        result = self.refused({'op': 'prepare-dispatch', 'op_id': 'pilot-block-1', 'task_id': 'build-it',
                             'role': 'dev-lead', 'host': 'codex'}, 'cycle-refused')
        self.assertIn('held by pilot', result['errors'][0]['problem'])

    def test_real_isolated_proof_checkout_is_seen_from_main(self):
        self.prepare()
        root = Path(self.temp.name + '-isolated')
        self.git('worktree', 'add', '-q', '--detach', str(root), 'HEAD')
        self.addCleanup(self.git, 'worktree', 'remove', str(root))
        self.ok({'op': 'execution-check', 'op_id': 'pilot-proof-1', 'assignment': 'build-it', 'attempt': 1, 'checkout': str(root)})
        holders = runtime.legacy_holders(self.repo, tree(self.repo).docs_root, root)
        self.assertEqual(holders, [self.cid + '/build-it'])


if __name__ == '__main__':
    unittest.main()
