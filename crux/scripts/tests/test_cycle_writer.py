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
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cycle_writer as pilot
import cycle_runtime as runtime
from cycle_store import CycleError, tree
from _cycle_fixtures import fresh, put
from test_cycle_history import LEGACY_MODULES


def legacy_editor_record(repo, identity, *, host='codex', role='developer', checkout=None, state='running', phase='build', status='active'):
    """A typed legacy record, built as JSON, whose one attempt may be editing: no typed-engine code runs."""
    doc = fresh('quick-fix')
    doc['status'] = status
    doc['plan']['tasks'] = [{'id': 'edit', 'phase': phase, 'description': 'Edit source', 'depends_on': [], 'status': 'pending', 'expected_evidence': ['commit']}]
    doc['assignments'] = [{'id': 'edit', 'role': role, 'task': 'edit', 'agent': None, 'result_path': None, 'state': state, 'attempt': 1, 'mode': None,
                           'started_at': doc['created_at'], 'last_seen': doc['created_at'], 'ended_at': None, 'note': None, 'host': host, 'base': None,
                           'delivery': None, **({'execution': {'checkout': str(checkout)}} if checkout else {})}]
    return put(repo, doc, identity)


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
        with self.assertRaisesRegex(CycleError, 'stale review: reviewed paths changed after the reviewed head: src/value.py'):
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

    # -- review admission follows the reviewed-path rule ------------------------------

    def commit_file(self, relative, content, message):
        (self.repo / relative).write_text(content)
        self.git('add', relative); self.git('commit', '-qm', message)

    def test_a_later_commit_to_unreviewed_paths_does_not_refuse_the_review(self):
        self.implemented()
        self.apply('review-start', reviewer='independent')
        report = self.report()
        self.commit_file('src/other.py', 'other = 1\n', 'other work on a path outside the reviewed range')
        self.as_actor('independent', 'review', value=report)
        self.assertEqual((self.doc['state'], self.doc['review']['head_commit']), ('reviewed', report['head_commit']))
        self.assertTrue(pilot.review_current(self.repo, self.doc))

    def test_a_later_change_to_a_reviewed_path_is_refused_and_named(self):
        self.implemented()
        self.apply('review-start', reviewer='independent')
        report = self.report()
        (self.repo / 'src/other.py').write_text('other = 1\n')
        (self.repo / 'src/value.py').write_text('value = 6\n')
        self.git('add', 'src'); self.git('commit', '-qm', 'one commit touches a reviewed path and a new path')
        before = self.record_bytes()
        with self.assertRaisesRegex(CycleError, r'^stale review: reviewed paths changed after the reviewed head: src/value\.py$'):
            self.as_actor('independent', 'review', value=report)
        self.assertEqual(self.record_bytes(), before, 'a refused review wrote the record')
        # A deleted reviewed path is a change to it too.
        self.git('rm', '-q', 'src/value.py'); self.git('commit', '-qm', 'delete the reviewed path')
        with self.assertRaisesRegex(CycleError, 'stale review: reviewed paths changed after the reviewed head: src/value.py'):
            self.as_actor('independent', 'review', value=report)

    def test_the_reviewed_head_must_hold_the_code_committed_at_review_start(self):
        self.implemented()
        first = self.git('rev-parse', 'HEAD')
        self.commit_file('src/more.py', 'more = 1\n', 'second part of the change')
        self.apply('review-start', reviewer='independent')
        # The base and an earlier commit of the change both lack code committed when review was requested.
        for head in (self.doc['base_commit'], first):
            with self.subTest(head=head):
                with self.assertRaisesRegex(CycleError, 'review must name a head that holds the code committed when review was requested'):
                    self.as_actor('independent', 'review', value=self.report(head_commit=head))
        # Bookkeeping between a named head and the request head keeps the head admissible.
        (self.repo / 'bionic/journal').mkdir()
        self.commit_file('bionic/journal/entry.md', 'recorded\n', 'journal')
        code_head = self.git('rev-parse', 'HEAD~1')
        self.apply('review-start', reviewer='independent')
        self.assertNotEqual(self.doc['review_request']['head_commit'], code_head)
        self.as_actor('independent', 'review', value=self.report(head_commit=code_head))
        self.assertEqual(self.doc['state'], 'reviewed')

    def test_work_recorded_after_review_start_keeps_the_strict_rule(self):
        self.task()
        self.apply('review-start', reviewer='independent')
        early = self.report()  # names the request head, which holds none of the change
        self.commit_file('src/value.py', 'value = 2\n', 'the change, committed after review was requested')
        self.task('done'); self.check()
        with self.assertRaisesRegex(CycleError, 'stale review: implementation work was recorded after review was requested '
                                    'and code changed after the reviewed head: src/value.py'):
            self.as_actor('independent', 'review', value=early)
        self.assertIsNone(self.doc['review'])
        # Positive control: the reviewer names the head that holds the change.
        self.as_actor('independent', 'review', value=self.report())
        self.assertEqual(self.doc['state'], 'reviewed')

    def test_review_start_refuses_worktree_work_the_checkout_does_not_contain(self):
        checkout = Path(self.temp.name) / 'unit'
        self.git('worktree', 'add', '-qb', 'unit', str(checkout), 'HEAD')
        self.task(checkout=str(checkout))
        (checkout / 'src/value.py').write_text('value = 2\n')
        self.git('add', 'src/value.py', cwd=checkout); self.git('commit', '-qm', 'the change, in the worktree', cwd=checkout)
        self.task('done'); self.check()
        before = self.record_bytes()
        with self.assertRaisesRegex(CycleError, r'review-start: task build finished in .*unit at commit [0-9a-f]{12}, which this checkout does not contain; integrate it first'):
            self.apply('review-start', reviewer='independent')
        self.assertEqual(self.record_bytes(), before)
        # Positive control: once integrated, review-start proceeds and the review covers the change.
        self.git('merge', '-q', '--ff-only', 'unit')
        self.apply('review-start', reviewer='independent')
        self.as_actor('independent', 'review', value=self.report())
        self.assertEqual(pilot.reviewed_paths(self.repo, self.doc), ['src/value.py'])

    # -- worktree work is bound to its recorded commit ----------------------------------

    def worktree_done(self):
        """The task runs and finishes in a linked worktree; returns the worktree path and its HEAD at done."""
        checkout = Path(self.temp.name) / 'unit'
        self.git('worktree', 'add', '-qb', 'unit', str(checkout), 'HEAD')
        self.task(checkout=str(checkout))
        (checkout / 'src/value.py').write_text('value = 2\n')
        self.git('add', 'src/value.py', cwd=checkout); self.git('commit', '-qm', 'the change, in the worktree', cwd=checkout)
        head = self.git('rev-parse', 'HEAD', cwd=checkout)
        self.task('done'); self.check()
        return checkout, head

    def test_done_in_a_linked_worktree_records_its_head_commit(self):
        checkout, head = self.worktree_done()
        attempt = self.doc['tasks'][0]['attempts'][-1]
        self.assertEqual((attempt['outcome'], attempt['checkout'], attempt['commit']), ('done', str(checkout.resolve()), head))

    def test_done_in_the_review_checkout_records_no_commit(self):
        self.implemented()
        attempt = self.doc['tasks'][0]['attempts'][-1]
        self.assertEqual(attempt['outcome'], 'done')
        self.assertNotIn('commit', attempt)

    def test_squash_integration_refusal_names_the_route_that_admits_review(self):
        checkout, head = self.worktree_done()
        self.git('merge', '-q', '--squash', 'unit'); self.git('commit', '-qm', 'squash the unit')
        self.assertEqual((self.repo / 'src/value.py').read_text(), 'value = 2\n')
        before = self.record_bytes()
        # The ancestry check still refuses: the squash commit does not contain the recorded commit.
        with self.assertRaisesRegex(CycleError, rf'which this checkout does not contain; integrate it first.*'
                                    rf'squash merge or cherry-pick.*`git diff {head[:12]} HEAD`.*'
                                    r'`task CYC-\d{4} --task build --owner OWNER --run 2 --status working`.*'
                                    r'`--run 2 --status done`'):
            self.apply('review-start', reviewer='independent')
        self.assertEqual(self.record_bytes(), before, 'a refused review-start wrote the record')
        self.assertEqual(self.git('diff', head, 'HEAD', '--', 'src'), '', 'HEAD does not hold the squashed change')
        # The route the refusal names: reassign at the next run in this checkout and record completion there.
        self.task(owner='lead', run=2, summary='squash-integrated in the review checkout')
        self.assertEqual(self.doc['tasks'][0]['checkout'], str(self.repo.resolve()))
        self.task('done', owner='lead', run=2, summary='verified the squash commit holds the change')
        self.assertNotIn('commit', self.doc['tasks'][0]['attempts'][-1])
        self.apply('review-start', reviewer='independent')
        self.assertEqual(self.doc['state'], 'reviewing')
        self.as_actor('independent', 'review', value=self.report())
        self.assertEqual(pilot.reviewed_paths(self.repo, self.doc), ['src/value.py'])

    def test_review_start_refuses_a_removed_worktree_whose_recorded_commit_is_unmerged(self):
        checkout, head = self.worktree_done()
        self.git('worktree', 'remove', str(checkout))
        before = self.record_bytes()
        with self.assertRaisesRegex(CycleError, rf'^review-start: task build finished in .*unit at commit {head[:12]}, '
                                    'which this checkout does not contain; integrate it first'):
            self.apply('review-start', reviewer='independent')
        self.assertEqual(self.record_bytes(), before, 'a refused review-start wrote the record')
        # The branch is deleted and the commit object collected: the commit is gone, and review-start still refuses.
        self.git('branch', '-qD', 'unit')
        self.git('reflog', 'expire', '--expire=now', '--all')
        self.git('gc', '-q', '--prune=now')
        self.assertIsNone(pilot._commit(self.repo, head), 'the fixture failed to remove the commit object')
        with self.assertRaisesRegex(CycleError, rf'^review-start: task build finished in .*unit at commit {head[:12]}, '
                                    'which this repository no longer holds'):
            self.apply('review-start', reviewer='independent')
        self.assertEqual(self.record_bytes(), before, 'a refused review-start wrote the record')

    def test_review_start_admits_a_removed_worktree_whose_commit_was_integrated(self):
        checkout, head = self.worktree_done()
        self.git('merge', '-q', '--ff-only', 'unit')
        self.git('worktree', 'remove', str(checkout))
        self.git('branch', '-qd', 'unit')
        self.apply('review-start', reviewer='independent')
        self.assertEqual(self.doc['review_request']['head_commit'], head)
        self.as_actor('independent', 'review', value=self.report())
        self.assertEqual(pilot.reviewed_paths(self.repo, self.doc), ['src/value.py'])

    def test_a_worktree_that_moved_on_after_done_is_judged_by_its_live_head_too(self):
        checkout, head = self.worktree_done()
        self.git('merge', '-q', '--ff-only', 'unit')
        (checkout / 'src/value.py').write_text('value = 3\n')
        self.git('add', 'src/value.py', cwd=checkout); self.git('commit', '-qm', 'more work after done', cwd=checkout)
        moved = self.git('rev-parse', 'HEAD', cwd=checkout)
        with self.assertRaisesRegex(CycleError, rf'review-start: task build ran in .*unit, whose HEAD {moved[:12]} this checkout does not contain'):
            self.apply('review-start', reviewer='independent')
        # Removing the moved worktree leaves the recorded commit, which HEAD holds.
        self.git('worktree', 'remove', str(checkout))
        self.apply('review-start', reviewer='independent')
        self.assertEqual(self.doc['review_request']['head_commit'], head)

    def test_a_result_from_a_removed_worktree_is_refused_before_it_unbinds_the_work(self):
        checkout = Path(self.temp.name) / 'unit'
        self.git('worktree', 'add', '-qb', 'unit', str(checkout), 'HEAD')
        self.task(checkout=str(checkout))
        self.git('worktree', 'remove', str(checkout))
        before = self.record_bytes()
        with self.assertRaisesRegex(CycleError, r'task result: the attempt ran in .*unit, whose HEAD commit cannot be read; '
                                    'record the result before removing that worktree'):
            self.task('done')
        self.assertEqual(self.record_bytes(), before, 'a refused result wrote the record')

    def drop_recorded_commit(self):
        """Rewrite the record as a writer that captured no commit would have left it."""
        path = pilot.path_of(self.repo, self.doc['id'])
        doc = json.loads(path.read_text())
        for task in doc['tasks']:
            for attempt in task['attempts']:
                attempt.pop('commit', None)
        path.write_text(json.dumps(doc, indent=2) + '\n')
        self.doc = doc

    def test_a_record_without_a_captured_commit_keeps_the_live_head_rule(self):
        checkout, head = self.worktree_done()
        self.drop_recorded_commit()
        # The worktree still exists: its live HEAD is judged, as before.
        with self.assertRaisesRegex(CycleError, rf'review-start: task build ran in .*unit, whose HEAD {head[:12]} this checkout does not contain'):
            self.apply('review-start', reviewer='independent')
        # The worktree is removed: with no recorded commit there is nothing to judge, and review-start proceeds as before.
        self.git('worktree', 'remove', str(checkout))
        self.apply('review-start', reviewer='independent')
        self.assertEqual(self.doc['state'], 'reviewing')

    # -- direct completion binds an explicit linked checkout ----------------------------

    def worktree_commit(self, checkout):
        """A linked worktree at `checkout` on branch unit, holding one commit the lead checkout lacks."""
        self.git('worktree', 'add', '-qb', 'unit', str(checkout), 'HEAD')
        (checkout / 'src/value.py').write_text('value = 2\n')
        self.git('add', 'src/value.py', cwd=checkout); self.git('commit', '-qm', 'the change, in the worktree', cwd=checkout)
        return self.git('rev-parse', 'HEAD', cwd=checkout)

    def direct_done(self, via, checkout):
        entry = {'task': 'build', 'owner': 'worker', 'run': 1, 'status': 'done', 'checkout': checkout, 'summary': 'done directly'}
        if via == 'batch':
            return self.apply('batch', value={'tasks': [entry]})
        return self.apply('task', **entry)

    def test_direct_completion_in_a_linked_worktree_records_its_checkout_and_commit(self):
        for via in ('task', 'batch'):
            with self.subTest(via=via):
                self.setUp()
                checkout = Path(self.temp.name) / 'unit'
                head = self.worktree_commit(checkout)
                revision = self.doc['revision']
                self.direct_done(via, str(checkout))
                task = self.doc['tasks'][0]
                self.assertEqual(self.doc['revision'], revision + 1, 'direct completion took more than one write')
                self.assertEqual((task['status'], len(task['attempts'])), ('done', 1))
                attempt = task['attempts'][0]
                self.assertEqual((attempt['outcome'], attempt['checkout'], attempt['commit']), ('done', str(checkout.resolve()), head))
                self.assertEqual(self.claims(), {}, 'one-write completion left a checkout claim')
                self.check()
                # After cleanup the recorded commit is judged: unintegrated refuses, integrated admits.
                self.git('worktree', 'remove', str(checkout))
                before = self.record_bytes()
                with self.assertRaisesRegex(CycleError, rf'^review-start: task build finished in .*unit at commit {head[:12]}, '
                                            'which this checkout does not contain; integrate it first'):
                    self.apply('review-start', reviewer='independent')
                self.assertEqual(self.record_bytes(), before, 'a refused review-start wrote the record')
                self.git('merge', '-q', '--ff-only', 'unit')
                self.apply('review-start', reviewer='independent')
                self.assertEqual(self.doc['review_request']['head_commit'], head)

    def test_direct_completion_in_the_lead_checkout_records_no_checkout(self):
        for via, checkout in (('task', None), ('task', 'lead'), ('batch', None), ('batch', 'lead')):
            with self.subTest(via=via, checkout=checkout):
                self.setUp()
                self.commit_file('src/value.py', 'value = 2\n', 'correct value')
                self.direct_done(via, str(self.repo) if checkout else None)
                attempt = self.doc['tasks'][0]['attempts'][-1]
                self.assertEqual((attempt['outcome'], attempt['checkout']), ('done', None))
                self.assertNotIn('commit', attempt)
                self.check()
                self.apply('review-start', reviewer='independent')
                self.assertEqual(self.doc['state'], 'reviewing')

    def test_direct_completion_refuses_a_checkout_it_cannot_bind(self):
        other = Path(self.temp.name) / 'other'
        other.mkdir()
        self.git('init', '-q', cwd=other)
        (other / 'f').write_text('x\n')
        self.git('add', 'f', cwd=other)
        self.git('-c', 'user.email=t@example.invalid', '-c', 'user.name=T', 'commit', '-qm', 'other', cwd=other)
        checkout = Path(self.temp.name) / 'unit'
        self.worktree_commit(checkout)
        cases = {'missing': (str(Path(self.temp.name) / 'gone'), 'whose HEAD commit cannot be read'),
                 'subdirectory': (str(checkout / 'src'), 'is not a Git worktree root'),
                 'another repository': (str(other), 'task checkout must belong to this Git repository')}
        for via in ('task', 'batch'):
            for name, (path, message) in cases.items():
                with self.subTest(via=via, case=name):
                    before, claims = self.record_bytes(), self.claims()
                    with self.assertRaisesRegex(CycleError, message):
                        self.direct_done(via, path)
                    self.assertEqual((self.record_bytes(), self.claims()), (before, claims), 'a refused write changed the record or claims')

    # -- the supplied directory must be Git's worktree root -----------------------------

    def nested_worktree(self):
        """A linked worktree nested inside the lead checkout, assigned to the task, with one commit."""
        (self.repo / '.gitignore').write_text('.worktrees/\n')
        self.git('add', '.gitignore'); self.git('commit', '-qm', 'ignore nested worktrees')
        checkout = self.repo / '.worktrees' / 'unit'
        self.git('worktree', 'add', '-qb', 'unit', str(checkout), 'HEAD')
        self.task(checkout=str(checkout))
        (checkout / 'src/value.py').write_text('value = 2\n')
        self.git('add', 'src/value.py', cwd=checkout); self.git('commit', '-qm', 'the change, in the nested worktree', cwd=checkout)
        return checkout, self.git('rev-parse', 'HEAD', cwd=checkout)

    def test_a_nested_worktree_that_lost_its_git_link_is_refused(self):
        checkout, head = self.nested_worktree()
        (checkout / '.git').unlink()
        self.assertEqual(self.git('rev-parse', '--show-toplevel', cwd=checkout), str(self.repo.resolve()),
                         'the fixture failed to make Git resolve the directory to the enclosing checkout')
        for via in ('task', 'batch'):
            with self.subTest(via=via):
                before, claims = self.record_bytes(), self.claims()
                self.assertIn(str(checkout.resolve()), claims)
                entry = {'task': 'build', 'owner': 'worker', 'run': 1, 'status': 'done', 'summary': 'done'}
                with self.assertRaisesRegex(CycleError, r'task result: .*unit is not a Git worktree root: Git resolves it to '
                                            r'the enclosing worktree .*repo.*git worktree repair'):
                    self.apply('batch', value={'tasks': [entry]}) if via == 'batch' else self.apply('task', **entry)
                self.assertEqual((self.record_bytes(), self.claims()), (before, claims), 'a refused write changed the record or claims')
        # Positive control: once the link is restored the result binds the worktree's own commit.
        subprocess.run(['git', '-C', str(self.repo), 'worktree', 'repair', str(checkout)], capture_output=True)
        self.task('done')
        self.assertEqual(self.doc['tasks'][0]['attempts'][-1]['commit'], head)

    def test_direct_completion_from_a_nested_worktree_that_lost_its_git_link_is_refused(self):
        (self.repo / '.gitignore').write_text('.worktrees/\n')
        self.git('add', '.gitignore'); self.git('commit', '-qm', 'ignore nested worktrees')
        checkout = self.repo / '.worktrees' / 'unit'
        self.worktree_commit(checkout)
        (checkout / '.git').unlink()
        for via in ('task', 'batch'):
            with self.subTest(via=via):
                before, claims = self.record_bytes(), self.claims()
                with self.assertRaisesRegex(CycleError, r'.*unit is not a Git worktree root'):
                    self.direct_done(via, str(checkout))
                self.assertEqual((self.record_bytes(), self.claims()), (before, claims))

    def test_review_start_refuses_a_live_checkout_that_is_no_worktree_root(self):
        checkout, head = self.nested_worktree()
        self.task('done'); self.check()
        self.git('merge', '-q', '--ff-only', 'unit')
        for recorded in (True, False):
            with self.subTest(recorded_commit=recorded):
                if not recorded:
                    self.drop_recorded_commit()
                (checkout / '.git').unlink()
                before = self.record_bytes()
                with self.assertRaisesRegex(CycleError, r'^review-start: task build ran in .*unit, which is not a Git worktree root: '
                                            r'Git resolves it to the enclosing worktree .*git worktree repair'):
                    self.apply('review-start', reviewer='independent')
                self.assertEqual(self.record_bytes(), before, 'a refused review-start wrote the record')
                # Positive control: the restored link lets review-start read the worktree's own HEAD, which is integrated.
                subprocess.run(['git', '-C', str(self.repo), 'worktree', 'repair', str(checkout)], capture_output=True)
                self.apply('review-start', reviewer='independent')
                self.assertEqual(self.doc['state'], 'reviewing')
                self.doc = json.loads(pilot.path_of(self.repo, self.doc['id']).read_text())

    def test_a_rewritten_request_head_names_review_start(self):
        self.implemented()
        self.apply('review-start', reviewer='independent')
        (self.repo / 'src/value.py').write_text('value = 3\n')
        self.git('add', 'src/value.py'); self.git('commit', '-q', '--amend', '-m', 'correct value, amended')
        with self.assertRaisesRegex(CycleError, 'is no longer in the history of HEAD; run review-start again'):
            self.as_actor('independent', 'review', value=self.report())
        self.apply('review-start', reviewer='independent')
        self.as_actor('independent', 'review', value=self.report())
        self.assertEqual(self.doc['state'], 'reviewed')

    def serial_cycles(self, second_path):
        """Cycle A requests review of its change; cycle B, started later on the same branch, commits to `second_path`."""
        self.implemented()
        self.apply('review-start', reviewer='independent')
        report_a = self.report()
        b = pilot.create(self.repo, 'Next correction', 'lead', self.spec)
        b = pilot.mutate(self.repo, b['id'], 'lead', b['revision'], 'task', SimpleNamespace(
            task='build', owner='worker', run=1, status='working', checkout=None, summary='observed working'))
        self.commit_file(second_path, 'value = 7\n', 'cycle B change')
        b = pilot.mutate(self.repo, b['id'], 'lead', b['revision'], 'task', SimpleNamespace(
            task='build', owner='worker', run=1, status='done', checkout=None, summary='observed done'))
        b = pilot.mutate(self.repo, b['id'], 'lead', b['revision'], 'check', SimpleNamespace(value={
            'check_id': 'focused', 'executed_command': 'python -m unittest test_value', 'tested_revision': self.git('rev-parse', 'HEAD'),
            'result': 'passed', 'summary': 'value check passed', 'reason': 'Changed behavior'}))
        return report_a, b

    def test_two_serial_cycles_on_one_branch_each_review_their_own_range(self):
        report_a, b = self.serial_cycles('src/other.py')
        self.as_actor('independent', 'review', value=report_a)
        self.apply('finish', summary='Cycle A reviewed without cycle B commits')
        self.assertEqual(self.doc['state'], 'completed')
        b = pilot.mutate(self.repo, b['id'], 'lead', b['revision'], 'review-start', SimpleNamespace(reviewer='independent'))
        report_b = {**self.report(), 'plan_revision': b['plan']['revision'], 'base_commit': b['base_commit']}
        b = pilot.mutate(self.repo, b['id'], 'independent', b['revision'], 'review', SimpleNamespace(value=report_b))
        self.assertEqual(b['state'], 'reviewed')
        self.assertEqual(pilot.reviewed_paths(self.repo, b), ['src/other.py'], 'cycle B review range swallowed cycle A')

    def test_a_serial_cycle_that_changes_a_reviewed_path_refuses_the_earlier_review(self):
        report_a, _ = self.serial_cycles('src/value.py')
        with self.assertRaisesRegex(CycleError, 'stale review: reviewed paths changed after the reviewed head: src/value.py'):
            self.as_actor('independent', 'review', value=report_a)

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
import cycle_writer as pilot, cycle_runtime as runtime
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
        with self.assertRaisesRegex(CycleError, 'checkout is owned by') as refused:
            pilot.mutate(self.repo, third['id'], 'third-lead', third['revision'], 'batch', claim)
        # The refusal names the holder's recovery command.
        self.assertIn(f"cycle.py recover {self.doc['id']}", str(refused.exception))
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

    # -- a plan revision keeps a pause and withdraws an open review request -----------------

    def test_a_plan_revision_on_a_paused_cycle_keeps_the_pause_until_resume(self):
        self.task()
        self.task('blocked', summary='worker hit an unknown')
        self.apply('pause', reason='owner decision needed')
        revised = {**deepcopy(self.doc['plan']), 'acceptance': ['value equals two', 'caller reads two']}
        self.apply('plan', value=revised, reason='owner adds a criterion', owner_approval='Add the caller criterion.')
        # The owner's words are recorded while paused, and the pause and its blocker stay.
        self.assertEqual((self.doc['state'], self.doc['plan']['revision']), ('paused', 2))
        self.assertEqual(self.doc['blockers'], ['owner decision needed'])
        self.assertEqual(self.doc['history'][-1]['owner_approval'], 'Add the caller criterion.')
        before = self.record_bytes()
        with self.assertRaisesRegex(CycleError, 'resume before assigning work'):
            self.task(run=2, summary='reassign after the revision')
        with self.assertRaisesRegex(CycleError, 'resume before recording a new run'):
            self.task('done', run=2, summary='completed without an assignment')
        self.assertEqual(self.record_bytes(), before, 'a refused task write wrote the record')
        self.apply('resume', reason='owner answered', reconcile='Checked Git status, diff and the record')
        # A revised plan resumes in planning, as an unpaused revision would, and a task write starts work.
        self.assertEqual((self.doc['state'], self.doc['blockers']), ('planning', []))
        self.assertNotIn('resume_state', self.doc)
        self.task(run=2, summary='reassign after the revision')
        self.assertEqual(self.doc['state'], 'working')

    def test_a_paused_cycle_still_accepts_the_result_of_a_running_task(self):
        self.task()
        self.apply('pause', reason='owner stopped work')
        self.task('done', summary='worker finished after the pause')
        self.assertEqual((self.doc['state'], self.doc['tasks'][0]['status']), ('paused', 'done'))

    def test_a_finding_scope_addition_on_a_paused_cycle_keeps_the_pause(self):
        self.implemented()
        self.apply('review', value=self.report(verdict='changes-required', blocking=['fix the caller in lib/caller.py'],
                                               acceptance=[{'criterion': 0, 'met': False, 'evidence': 'caller still reads one'}]))
        finding = self.doc['review']['finding_tasks'][0]
        self.apply('pause', reason='waiting on the owner')
        revised = {**deepcopy(self.doc['plan']), 'scope': ['src', 'lib/caller.py']}
        self.apply('plan', value=revised, reason='finding names the caller', owner_approval=None, finding=finding, criterion=0)
        self.assertEqual((self.doc['state'], self.doc['blockers']), ('paused', ['waiting on the owner']))
        self.assertEqual(self.doc['plan']['scope'], ['src', 'lib/caller.py'])
        self.apply('resume', reason='go on', reconcile='Checked Git status, diff and the record')
        self.assertEqual(self.doc['state'], 'planning')

    def test_a_plan_revision_withdraws_the_open_review_request_into_history(self):
        import cycle_progress
        self.implemented()
        self.apply('review-start', reviewer='independent')
        request = deepcopy(self.doc['review_request'])
        revised = {**deepcopy(self.doc['plan']), 'goal': 'Return the corrected value to every caller'}
        self.apply('plan', value=revised, reason='clarify the goal', owner_approval=None)
        self.assertEqual(self.doc['state'], 'planning')
        self.assertNotIn('review_request', self.doc)
        # The withdrawn request stays in the record, on the plan revision that withdrew it.
        self.assertEqual(self.doc['history'][-1]['review_request'], request)
        with self.assertRaisesRegex(CycleError, 'no review is requested'):
            self.as_actor('independent', 'review', value=self.report())
        self.apply('abandon', reason='superseded')
        self.assertEqual(cycle_progress.stopped_state(self.doc), 'working')

    def test_a_plan_revision_while_paused_in_review_resumes_in_planning(self):
        import cycle_progress
        self.implemented()
        self.apply('review-start', reviewer='independent')
        self.apply('pause', reason='owner decision needed')
        revised = {**deepcopy(self.doc['plan']), 'goal': 'Return the corrected value to every caller'}
        self.apply('plan', value=revised, reason='clarify the goal', owner_approval=None)
        self.assertEqual((self.doc['state'], self.doc.get('resume_state')), ('paused', 'planning'))
        self.assertNotIn('review_request', self.doc)
        self.assertEqual(self.doc['history'][-1]['review_request']['reviewer'], 'independent')
        with self.assertRaisesRegex(CycleError, 'resume before review'):
            self.apply('review-start', reviewer='independent')
        # Abandoning from the pause names the step a resume would have returned to, not the withdrawn review.
        abandoned = pilot.mutate(self.repo, self.doc['id'], 'lead', self.doc['revision'], 'abandon', SimpleNamespace(reason='stop'))
        self.assertEqual(cycle_progress.stopped_state(abandoned), 'planning')

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
        old = put(self.repo, fresh('quick-fix'), 'CYC-0002')
        later = pilot.create(self.repo, 'Later', 'lead', self.spec)
        self.assertEqual([self.doc['id'], old, later['id']], ['CYC-0001', 'CYC-0002', 'CYC-0003'])

    def test_a_pilot_task_refuses_a_checkout_a_typed_legacy_editor_holds(self):
        identity = legacy_editor_record(self.repo, 'CYC-0002')
        with self.assertRaisesRegex(CycleError, f'legacy editing assignments: {identity}/edit'):
            self.task()

    def test_linked_caller_sees_main_legacy_owner_and_cannot_allocate(self):
        checkout = Path(self.temp.name) / 'linked'
        self.git('add', 'bionic/cycles')
        self.git('commit', '-qm', 'share pilot plan')
        self.git('worktree', 'add', '-qb', 'linked', str(checkout), 'HEAD')
        legacy_editor_record(self.repo, 'CYC-0002')
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

    def test_cli_create_without_a_plan_file_starts_in_planning_and_refuses_mixed_or_partial_flags(self):
        import cycle

        def run(*argv):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = cycle.main(['--repo-root', str(self.repo), 'create', '--title', 'Flags', '--lead', 'lead', *argv])
            return code, json.loads(output.getvalue())
        spec = Path(self.temp.name) / 'plan.json'
        spec.write_text(json.dumps(self.spec))
        cycles = sorted(p.name for p in (self.repo / 'bionic/cycles').glob('CYC-*'))
        for argv, message in ((['--goal', 'g', '--scope', 'src'], 'or --goal, --scope and --acceptance'),
                              (['--plan', str(spec), '--goal', 'g'], 'drop --goal'), ([], 'create needs --plan FILE')):
            with self.subTest(argv=argv):
                code, payload = run(*argv)
                self.assertEqual(code, 1, payload)
                self.assertIn(message, payload['error'])
        code, payload = run('--goal', 'Deliver', '--scope', 'src', '--scope', 'bionic', '--acceptance', 'works')
        self.assertEqual(code, 0, payload)
        created = pilot.load_pilot(self.repo, payload['cycle']['id'])
        self.assertEqual((created['state'], created['tasks'], created['plan']['scope']), ('planning', [], ['src', 'bionic']))
        self.assertNotIn('verification', created['plan'])
        self.assertIn('plan incomplete', ' '.join(payload['cycle']['blockers']))
        self.assertEqual(len(sorted(p.name for p in (self.repo / 'bionic/cycles').glob('CYC-*'))), len(cycles) + 1, 'a refused create allocated an id')

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

    # -- crux.cycle.v1: format, legacy refusal, scrutiny, ADR dependencies, release kind ----------

    def edit_record(self, **fields):
        """Rewrite the stored record the way an older writer or a release writer would have left it."""
        path = pilot.path_of(self.repo, self.doc['id'])
        stored = json.loads(path.read_text())
        stored.update(fields)
        for key in [k for k, v in fields.items() if v is None]:
            del stored[key]
        path.write_text(json.dumps(stored, sort_keys=True, indent=2) + '\n')
        self.doc = pilot.load_pilot(self.repo, self.doc['id'])

    def test_new_records_carry_the_v1_format_and_summaries_report_it(self):
        self.assertEqual(self.doc['format'], 'crux.cycle.v1')
        self.assertEqual(pilot.FORMATS, ('crux.cycle.vNext', 'crux.cycle.v1'))
        self.assertEqual(pilot.summarize(self.repo, self.doc)['format'], 'crux.cycle.v1')
        with self.assertRaises(CycleError):
            self.edit_record(format='crux.cycle.v2')

    def test_a_vnext_record_reads_and_updates_without_its_format_changing(self):
        self.edit_record(format='crux.cycle.vNext')
        self.assertEqual(pilot.summarize(self.repo, self.doc)['format'], 'crux.cycle.vNext')
        self.task()
        self.check()
        self.apply('pause', reason='owner stopped work')
        self.assertEqual(self.doc['format'], 'crux.cycle.vNext')
        self.assertEqual(json.loads(self.record_bytes())['format'], 'crux.cycle.vNext')
        self.assertEqual(pilot.summarize(self.repo, self.doc)['format'], 'crux.cycle.vNext')

    def test_every_writer_command_refuses_a_legacy_record_and_leaves_its_bytes(self):
        fixture = Path(__file__).resolve().parent / 'fixtures/cycle-history/CYC-0172/cycle.json'
        directory = tree(self.repo).docs_root / 'cycles/CYC-0172'
        directory.mkdir()
        record = directory / 'cycle.json'
        record.write_bytes(fixture.read_bytes())
        before = record.read_bytes()
        self.assertIn(b'"schema_version"', before)
        self.assertNotIn(b'"format"', before)
        requests = {
            'task': SimpleNamespace(task='build', owner='worker', run=1, status='working', checkout=None, summary='start'),
            'plan': SimpleNamespace(value=deepcopy(self.spec), reason='revise', owner_approval=None),
            'finish': SimpleNamespace(summary=None),
            'pause': SimpleNamespace(reason='stop'),
            'reopen': SimpleNamespace(reason='r', owner_instruction='o', value=[{'id': 'repair', 'description': 'Fix'}]),
            'check': SimpleNamespace(value={}), 'batch': SimpleNamespace(value={'tasks': []}),
            'resume': SimpleNamespace(reason='r', reconcile='observed'), 'abandon': SimpleNamespace(reason='r'),
            'recover': SimpleNamespace(), 'delivery': SimpleNamespace(value={'ci': 'passed'}),
            'review-start': SimpleNamespace(reviewer='independent'), 'review': SimpleNamespace(value={}),
            'council-subject': SimpleNamespace(), 'council': SimpleNamespace(record='x', response='y'),
        }
        for action, args in requests.items():
            with self.subTest(action=action), self.assertRaises(pilot.LegacyRecord) as raised:
                pilot.mutate(self.repo, 'CYC-0172', json.loads(before)['lead'] if 'lead' in json.loads(before) else 'lead', 1, action, args)
            self.assertEqual(record.read_bytes(), before, f'{action} changed a legacy record')
        message = str(raised.exception)
        for fragment in ('legacy typed record', 'never changes', 'cycle.py show', 'status'):
            self.assertIn(fragment, message)
        with self.assertRaises(pilot.LegacyRecord):
            pilot.load_pilot(self.repo, 'CYC-0172')
        with self.assertRaises(pilot.LegacyRecord):
            pilot.record_adr(self.repo, 'CYC-0172', {'adr': 'ADR-0183', 'path': 'adrs/x.md', 'sha256': 'a' * 64})
        self.assertEqual(record.read_bytes(), before)
        self.assertTrue(issubclass(pilot.LegacyRecord, CycleError))

    def default_scrutiny(self, level='standard'):
        return {'level': level, 'reason': 'project default'}

    def test_scrutiny_defaults_to_the_project_setting_at_create_and_plan_revision(self):
        self.assertEqual(self.doc['plan']['scrutiny'], self.default_scrutiny())
        self.assertEqual(pilot.summarize(self.repo, self.doc)['scrutiny'], self.default_scrutiny())
        (self.repo / '.bionic.yml').write_text('config_version: "1"\nreview:\n  scrutiny: intensive\n')
        later = pilot.create(self.repo, 'Strict project', 'lead', self.spec)
        self.assertEqual(later['plan']['scrutiny'], self.default_scrutiny('intensive'))
        # A plan revision that omits scrutiny takes the project default.
        self.doc = later
        self.apply('plan', value=deepcopy(self.spec), reason='restate', owner_approval=None)
        self.assertEqual(self.doc['plan']['scrutiny'], self.default_scrutiny('intensive'))

    def test_scrutiny_can_be_named_and_is_validated(self):
        named = deepcopy(self.spec)
        named['scrutiny'] = {'level': 'focused', 'reason': 'One-line value correction'}
        doc = pilot.create(self.repo, 'Focused', 'lead', named)
        self.assertEqual(doc['plan']['scrutiny'], {'level': 'focused', 'reason': 'One-line value correction'})
        self.assertEqual(pilot.summarize(self.repo, doc)['scrutiny']['level'], 'focused')
        for label, value in (('unknown level', {'level': 'careless', 'reason': 'x'}), ('no reason', {'level': 'focused', 'reason': ''}),
                             ('extra field', {'level': 'focused', 'reason': 'x', 'extra': 1}), ('not a mapping', 'focused')):
            with self.subTest(case=label), self.assertRaises(CycleError):
                pilot.create(self.repo, 'Bad', 'lead', {**deepcopy(self.spec), 'scrutiny': value})

    def test_a_record_without_scrutiny_stays_valid_and_is_not_rewritten_for_it(self):
        stripped = deepcopy(self.doc)
        del stripped['plan']['scrutiny']
        path = pilot.path_of(self.repo, self.doc['id'])
        path.write_text(json.dumps(stripped, sort_keys=True, indent=2) + '\n')
        self.doc = pilot.load_pilot(self.repo, self.doc['id'])
        self.assertEqual(pilot.summarize(self.repo, self.doc)['scrutiny'], self.default_scrutiny())
        self.task()
        self.assertNotIn('scrutiny', self.doc['plan'])
        self.assertNotIn('scrutiny', json.loads(self.record_bytes())['plan'])

    # -- ADR dependencies and the record's ADR list ----------------------------------------------

    def write_adr(self, name='ADR-0183', status='Proposed'):
        relative = f'adrs/{name}-test-decision.md'
        path = tree(self.repo).docs_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f'---\nid: {name}\ntitle: Test decision\nstatus: {status}\n---\n\nBody.\n')
        return {'adr': name, 'path': relative, 'sha256': 'a' * 64}

    def dependent_plan(self, names=('ADR-0183',)):
        specification = deepcopy(self.spec)
        specification['tasks'].append({'id': 'follow', 'description': 'Work that needs the decision', 'owner': 'worker',
                                      'adr_dependencies': list(names)})
        self.doc = pilot.create(self.repo, 'Waits for an ADR', 'lead', specification)

    def follow(self, status='working', run=1):
        return self.apply('task', task='follow', owner='worker', run=run, status=status, checkout=None, summary='observed ' + status)

    def test_a_task_naming_an_adr_waits_for_acceptance_and_other_tasks_proceed(self):
        self.dependent_plan()
        self.assertEqual(self.doc['tasks'][1]['adr_dependencies'], ['ADR-0183'])
        self.assertNotIn('adr_dependencies', self.doc['tasks'][0])
        with self.assertRaisesRegex(CycleError, '^adr-dependency-unrecorded:.*ADR-0183'):
            self.follow()
        before = self.record_bytes()
        entry = self.write_adr(status='Proposed')
        pilot.record_adr(self.repo, self.doc['id'], entry)
        self.doc = pilot.load_pilot(self.repo, self.doc['id'])
        before = self.record_bytes()
        for status, run in (('working', 1), ('done', 1)):
            with self.subTest(status=status), self.assertRaisesRegex(CycleError, '^adr-dependency-awaiting-acceptance:.*ADR-0183.*Proposed'):
                self.follow(status, run)
        with self.assertRaisesRegex(CycleError, 'batch task 0 \\(follow\\): adr-dependency-awaiting-acceptance:'):
            self.apply('batch', value={'tasks': [{'task': 'follow', 'owner': 'worker', 'run': 1, 'status': 'working'}]})
        self.assertEqual(self.record_bytes(), before, 'a refused dependent task wrote the record')
        self.task()  # a task without the dependency proceeds
        self.task('done')  # the checkout is free for the dependent task
        self.assertEqual(self.doc['tasks'][0]['status'], 'done')
        self.write_adr(status='Accepted')
        self.follow()
        self.assertEqual(self.doc['tasks'][1]['status'], 'working')
        self.follow('done')
        self.assertEqual(self.doc['tasks'][1]['status'], 'done')

    def test_an_accepted_adr_releases_direct_completion_and_a_rewritten_status_blocks_again(self):
        self.dependent_plan(('ADR-0183', 'ADR-0184'))
        pilot.record_adr(self.repo, self.doc['id'], self.write_adr('ADR-0183', 'Accepted'))
        pilot.record_adr(self.repo, self.doc['id'], self.write_adr('ADR-0184', 'Proposed'))
        self.doc = pilot.load_pilot(self.repo, self.doc['id'])
        with self.assertRaisesRegex(CycleError, 'ADR-0184.*Proposed'):
            self.follow('done')
        self.write_adr('ADR-0184', 'Accepted')
        self.follow('done')
        self.assertEqual(self.doc['tasks'][1]['status'], 'done')

    def test_adr_dependency_names_are_validated_at_plan_time(self):
        for label, names in (('empty', []), ('blank', ['']), ('duplicate', ['ADR-0183', 'ADR-0183']), ('malformed', ['adr-1']), ('not text', [7])):
            with self.subTest(case=label), self.assertRaises(CycleError):
                self.dependent_plan(names)
        self.dependent_plan(('ADR-0999',))  # any well-formed name plans, recorded or not

    def test_the_adrs_entry_is_recorded_once_under_the_record_lock(self):
        entry = self.write_adr()
        self.assertNotIn('adrs', self.doc)
        revision = self.doc['revision']
        self.assertEqual(pilot.record_adr(self.repo, self.doc['id'], entry), entry)
        stored = pilot.load_pilot(self.repo, self.doc['id'])
        self.assertEqual((stored['adrs'], stored['revision']), ([entry], revision + 1))
        bytes_before = pilot.path_of(self.repo, self.doc['id']).read_bytes()
        self.assertEqual(pilot.record_adr(self.repo, self.doc['id'], dict(entry)), entry)  # an identical repeat writes nothing
        self.assertEqual(pilot.path_of(self.repo, self.doc['id']).read_bytes(), bytes_before)
        with self.assertRaisesRegex(CycleError, 'already recorded'):
            pilot.record_adr(self.repo, self.doc['id'], {**entry, 'sha256': 'b' * 64})
        other = self.write_adr('ADR-0184')
        pilot.record_adr(self.repo, self.doc['id'], other)
        self.assertEqual([e['adr'] for e in pilot.load_pilot(self.repo, self.doc['id'])['adrs']], ['ADR-0183', 'ADR-0184'])
        for label, bad in (('unknown field', {**entry, 'extra': 1}), ('bad id', {**entry, 'adr': 'ADR-1'}),
                           ('bad digest', {**entry, 'adr': 'ADR-0185', 'sha256': 'xyz'}), ('absolute path', {**entry, 'adr': 'ADR-0185', 'path': '/etc/passwd'}),
                           ('escaping path', {**entry, 'adr': 'ADR-0185', 'path': '../outside.md'})):
            with self.subTest(case=label), self.assertRaises(CycleError):
                pilot.record_adr(self.repo, self.doc['id'], bad)

    def test_the_adrs_entry_needs_an_active_cycle_state_but_no_lead_actor(self):
        self.apply('pause', reason='owner stopped work')
        with self.assertRaisesRegex(CycleError, 'planning, working or reviewing; it is paused'):
            pilot.record_adr(self.repo, self.doc['id'], self.write_adr())
        self.assertNotIn('adrs', pilot.load_pilot(self.repo, self.doc['id']))
        self.apply('resume', reason='continue', reconcile='Observed Git status and the record')
        pilot.record_adr(self.repo, self.doc['id'], self.write_adr())  # no actor argument: the decision writer calls it

    def test_a_reviewed_cycle_refuses_an_adr_entry_and_names_the_plan_revision_route(self):
        self.implemented()
        self.apply('review', value=self.report())
        self.assertEqual(self.doc['state'], 'reviewed')
        with self.assertRaisesRegex(CycleError, 'it is reviewed; a plan revision returns the cycle to planning'):
            pilot.record_adr(self.repo, self.doc['id'], self.write_adr())
        self.assertNotIn('adrs', pilot.load_pilot(self.repo, self.doc['id']))

    def test_a_reviewing_cycle_records_a_corrective_adr_with_a_prefixed_identity(self):
        self.implemented()
        self.apply('review-start', reviewer='independent')
        self.assertEqual(self.doc['state'], 'reviewing')
        entry = self.write_adr('DEMO-ADR-0184')
        pilot.record_adr(self.repo, self.doc['id'], entry)
        stored = pilot.load_pilot(self.repo, self.doc['id'])
        self.assertEqual((stored['adrs'], stored['state']), ([entry], 'reviewing'))

    def test_a_release_record_refuses_ordinary_task_batch_finish_and_reopen_writes(self):
        self.edit_record(kind='release', release={'list': 'beta', 'version': '9.9.9'})
        self.assertEqual(pilot.load_pilot(self.repo, self.doc['id'])['kind'], 'release')
        before = self.record_bytes()
        requests = {
            'task': SimpleNamespace(task='build', owner='worker', run=1, status='working', checkout=None, summary='start'),
            'batch': SimpleNamespace(value={'tasks': [{'task': 'build', 'owner': 'worker', 'run': 1, 'status': 'working'}]}),
            'finish': SimpleNamespace(summary=None),
            'reopen': SimpleNamespace(reason='r', owner_instruction='o', value=[{'id': 'repair', 'description': 'Fix'}]),
        }
        for action, args in requests.items():
            with self.subTest(action=action), self.assertRaisesRegex(CycleError, 'release.py.*ledger stays authoritative'):
                pilot.mutate(self.repo, self.doc['id'], 'lead', self.doc['revision'], action, args)
            self.assertEqual(self.record_bytes(), before)
        self.assertIsNone(runtime.claim_of(self.repo, self.repo))
        self.apply('check', value={'check_id': 'focused', 'executed_command': 'python -m unittest', 'tested_revision': 'abc',
                                   'result': 'passed', 'summary': 'ran', 'reason': 'release record check'})
        self.assertEqual(self.doc['kind'], 'release')

    # -- scenarios on crux.cycle.v1 records (each asserts the format it exercises) ----------------

    def assert_v1(self):
        self.assertEqual(self.doc['format'], 'crux.cycle.v1')
        self.assertEqual(json.loads(self.record_bytes())['format'], 'crux.cycle.v1')

    def test_scenario_direct_work_on_v1(self):
        self.implemented()
        self.apply('review-start', reviewer='independent')
        self.as_actor('independent', 'review', value=self.report())
        self.apply('finish', summary='Value corrected and reviewed')
        self.assertEqual(self.doc['state'], 'completed')
        self.assert_v1()

    def test_scenario_council_planned_work_with_a_blocked_dependent_task_on_v1(self):
        specification = deepcopy(self.spec)
        specification['council'] = {'needed': True, 'reason': 'Consequential alternatives', 'approach': 'One shared writer'}
        self.doc = pilot.create(self.repo, 'Council planned', 'lead', specification)
        self.assert_v1()
        with self.assertRaisesRegex(CycleError, 'council-required'):
            self.task()
        self.assertIn('council required for dependent tasks; no approved result for this plan revision', pilot.blockers(self.doc))
        subject = pilot.council_subject(self.repo, self.doc)
        with patch('cycle_council.validate_approval') as approval:
            self.apply('council', record='councils/approved.json', response='All seats approved; no blocking findings')
        approval.assert_called_once()
        self.assertTrue(pilot.council_current(self.doc))
        self.assertEqual(self.doc['councils'][0]['subject'], subject)
        self.task()
        self.assertEqual(self.doc['tasks'][0]['status'], 'working')
        self.assert_v1()

    def test_scenario_review_changes_required_then_fix_then_approve_on_v1(self):
        self.implemented()
        self.apply('review', value=self.report(verdict='changes-required', blocking=['Cover negative value']))
        fix = self.doc['tasks'][-1]
        self.assertEqual((self.doc['state'], fix['status']), ('working', 'pending'))
        self.apply('task', task=fix['id'], owner='worker', run=1, status='working', checkout=None, summary='start')
        (self.repo / 'src/value.py').write_text('value = abs(2)\n')
        self.git('add', 'src/value.py'); self.git('commit', '-qm', 'cover negative value')
        self.apply('task', task=fix['id'], owner='worker', run=1, status='done', checkout=None, summary='covered')
        self.apply('review', value=self.report())
        self.assertEqual(self.doc['state'], 'reviewed')
        self.apply('finish', summary=None)
        self.assertEqual(self.doc['state'], 'completed')
        self.assert_v1()

    def test_scenario_interruption_and_resume_on_v1(self):
        self.task()
        self.apply('pause', reason='host restarted')
        self.assertEqual(self.doc['state'], 'paused')
        self.apply('resume', reason='owner resumed', reconcile='Checked Git status and the worker still owns run one')
        self.assertEqual((self.doc['state'], self.doc['tasks'][0]['run']), ('working', 1))
        self.assertIsNotNone(runtime.claim_of(self.repo, self.repo))
        self.assert_v1()
        # A write killed between its claim and its record is reconciled by the next write.
        self.task('done')
        other = pilot.create(self.repo, 'Parallel', 'other-lead', self.spec)
        self.assertEqual(other['format'], 'crux.cycle.v1')
        self.killed_write('before-record', {'tasks': [self.start('build', 'worker')]}, other)
        main = str(self.repo.resolve())
        self.assertEqual(self.claims()[main]['cycle'], other['id'])
        self.assertIn('removed the claim on ' + main, self.recover(other)['recovered'][0])
        self.assertNotIn(main, self.claims())
        self.assert_v1()

    def test_scenario_concurrent_checkouts_on_v1(self):
        self.task()
        other = pilot.create(self.repo, 'Other', 'other-lead', self.spec)
        self.assertEqual(other['format'], 'crux.cycle.v1')
        checkout = Path(self.temp.name) / 'parallel'
        self.git('worktree', 'add', '-qb', 'parallel', str(checkout), 'HEAD')
        request = SimpleNamespace(task='build', owner='other', run=1, status='working', checkout=str(checkout), summary='start')
        changed = pilot.mutate(self.repo, other['id'], 'other-lead', other['revision'], 'task', request)
        self.assertEqual(changed['format'], 'crux.cycle.v1')
        second = SimpleNamespace(task='build', owner='third', run=1, status='working', checkout=str(checkout), summary='start')
        third = pilot.create(self.repo, 'Third', 'third-lead', self.spec)
        with self.assertRaisesRegex(CycleError, 'checkout is owned'):
            pilot.mutate(self.repo, third['id'], 'third-lead', third['revision'], 'task', second)

    def test_scenario_completion_reopening_and_a_linked_repair_on_v1(self):
        self.reviewed()
        self.apply('finish', summary='First completion')
        self.assert_v1()
        self.apply('reopen', reason='PR CI failed on a negative value', owner_instruction='Reopen the cycle for the repair.',
                   value=[{'id': 'repair', 'description': 'Handle a negative value', 'owner': 'worker'}])
        self.assertEqual(self.doc['state'], 'working')
        self.assertFalse(pilot.review_recorded(self.doc))
        self.assert_v1()
        completed = self.doc['id']
        linked = pilot.create(self.repo, 'Separate repair', 'lead', self.spec, follows=completed)
        self.assertEqual((linked['format'], linked['follows']), ('crux.cycle.v1', completed))


class ReleaseRecordTests(unittest.TestCase):
    """A release record: fixed step tasks, scope and version refusals before allocation, record_release."""

    BETA = ['prep', 'prepare', 'verify', 'beta-and-smoke', 'tag', 'record']
    OFFICIAL = ['live-check-and-go-ahead', 'official', 'record']

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
        (self.repo / 'tools').mkdir()
        self.descriptor = {'format': 1, 'prep_scope': ['src', 'bionic/log'], 'official_scope': ['bionic/log'],
                           'targets': {'beta': 'private/project', 'official': 'public/project'}, 'commands': {}}
        self.write_descriptor()
        for argv in (('init', '-q'), ('config', 'user.email', 'test@example.invalid'), ('config', 'user.name', 'Test'),
                     ('add', '.'), ('commit', '-qm', 'baseline')):
            self.git(*argv)

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.repo), *args], check=True, capture_output=True, text=True).stdout.strip()

    def write_descriptor(self, **changes):
        value = {**self.descriptor, **changes}
        for key in [k for k, v in changes.items() if v is None]:
            del value[key]
        (self.repo / 'tools/crux-release.json').write_text(json.dumps(value))

    def cycles(self):
        return sorted(p.name for p in (self.repo / 'bionic/cycles').glob('*CYC-*')) if (self.repo / 'bionic/cycles').exists() else []

    def create(self, release_list='beta', version='1.2.3', scope=('src', 'bionic/log'), **kwargs):
        return pilot.create_release(self.repo, release_list, version, f'Release {version}', 'Publish the release',
                                    list(scope), ['published'], 'lead', **kwargs)

    def bytes_of(self, doc):
        return pilot.path_of(self.repo, doc['id']).read_bytes()

    def test_both_lists_create_their_fixed_tasks_in_order(self):
        for release_list, ids in (('beta', self.BETA), ('official', self.OFFICIAL)):
            with self.subTest(release_list=release_list):
                doc = self.create(release_list)
                self.assertEqual((doc['format'], doc['kind'], doc['state']), ('crux.cycle.v1', 'release', 'working'))
                self.assertEqual(doc['release'], {'list': release_list, 'version': '1.2.3'})
                self.assertEqual([t['id'] for t in doc['tasks']], ids)
                self.assertEqual([t['depends_on'] for t in doc['tasks']], [[]] + [[i] for i in ids[:-1]])
                self.assertTrue(all(t['owner'] == 'lead' and t['status'] == 'pending' and not t['council'] for t in doc['tasks']))
                self.assertEqual(doc['plan']['council']['needed'], False)
                self.assertIn('no plan council', doc['plan']['council']['reason'])
                self.assertEqual(doc['plan']['verification']['checks'][0]['id'], 'release-ledger')
                self.assertIn('only suite step', doc['plan']['verification']['checks'][0]['rationale'])
                self.assertEqual((doc['review'], doc['completion'], 'schema_version' in doc), (None, None, False))
                self.assertEqual(pilot.load_pilot(self.repo, doc['id']), doc)

    def test_the_queue_binding_is_recorded_only_when_given(self):
        plain = self.create()
        queued = self.create(queue={'item': 'Q-0001', 'token': 'a' * 32})
        self.assertNotIn('queue', plain)
        self.assertEqual({k: queued['queue'][k] for k in ('item', 'token', 'origin')}, {'item': 'Q-0001', 'token': 'a' * 32, 'origin': 'start'})

    def test_an_unknown_list_or_a_malformed_version_is_refused_before_allocation(self):
        for release_list, version in (('nightly', '1.2.3'), ('beta', '1.2'), ('beta', 'v1.2.3'), ('beta', '1.2.3-beta.1'), ('beta', ''), ('beta', None)):
            with self.subTest(release_list=release_list, version=version), self.assertRaises(CycleError):
                self.create(release_list, version)
            self.assertEqual(self.cycles(), [])
        self.assertEqual(self.create('beta', '10.20.30')['release']['version'], '10.20.30')  # positive control

    def test_a_scope_omitting_mandatory_paths_is_refused_before_allocation_with_a_positive_control(self):
        with self.assertRaisesRegex(CycleError, 'release prep scope omits mandatory paths: bionic/log'):
            self.create('beta', scope=('src',))
        with self.assertRaisesRegex(CycleError, 'official release scope omits mandatory paths: bionic/log'):
            self.create('official', scope=('src',))
        self.assertEqual(self.cycles(), [])
        self.assertEqual(self.create('beta', scope=('src', 'bionic/log'))['plan']['scope'], ['src', 'bionic/log'])
        self.assertEqual(self.create('official', scope=('bionic/log',))['plan']['scope'], ['bionic/log'])
        self.assertEqual(len(self.cycles()), 2)

    def test_a_descriptor_without_official_scope_leaves_the_official_scope_as_given(self):
        self.write_descriptor(official_scope=None)
        self.assertEqual(self.create('official', scope=('src',))['plan']['scope'], ['src'])
        with self.assertRaisesRegex(CycleError, 'release prep scope omits'):
            self.create('beta', scope=('src',))

    def test_a_repository_with_no_descriptor_takes_the_scope_as_given(self):
        (self.repo / 'tools/crux-release.json').unlink()
        self.assertEqual(self.create('beta', scope=('src',))['plan']['scope'], ['src'])

    def test_release_scope_captures_or_refuses(self):
        cfg = tree(self.repo)
        self.assertEqual(pilot.release_scope(cfg, ['bionic/cycles'], 'beta', capture=True), ['bionic/cycles', 'src', 'bionic/log'])
        self.assertEqual(pilot.release_scope(cfg, ['src', 'bionic/log'], 'beta'), ['src', 'bionic/log'])
        self.assertEqual(pilot.release_scope(cfg, ['bionic'], 'official'), ['bionic'])  # a pattern for a directory above covers the path
        with self.assertRaisesRegex(CycleError, 'omits mandatory paths: bionic/log'):
            pilot.release_scope(cfg, ['bionic/log/2026'], 'official')  # a narrower pattern does not
        with self.assertRaisesRegex(CycleError, 'omits mandatory paths: src'):
            pilot.release_scope(cfg, ['bionic/log'], 'beta')

    def test_the_scope_match_follows_the_walk_semantics(self):
        self.assertTrue(pilot.scope_name_in_scope('src/a/b.py', ['src']))
        self.assertTrue(pilot.scope_name_in_scope('src/a/b.py', ['src/**']))
        self.assertFalse(pilot.scope_name_in_scope('srcs/a.py', ['src']))
        self.assertFalse(pilot.scope_name_in_scope('src/__pycache__/a.pyc', ['src']))
        self.assertFalse(pilot.scope_name_in_scope('src/.git/config', ['src']))

    def test_the_descriptor_read_refuses_a_symlink_oversize_or_invalid_file(self):
        cfg = tree(self.repo)
        path = self.repo / 'tools/crux-release.json'
        self.assertEqual(pilot.release_descriptor(cfg)['prep_scope'], ['src', 'bionic/log'])  # positive control
        for label, mutate in (('oversize', lambda: path.write_text(json.dumps({**self.descriptor, 'pad': 'x' * (1024 * 1024)}))),
                              ('invalid', lambda: path.write_text(json.dumps({**self.descriptor, 'targets': {'beta': 'x'}}))),
                              ('not json', lambda: path.write_text('{')),
                              ('unknown key', lambda: path.write_text(json.dumps({**self.descriptor, 'extra': 1}))),
                              ('symlink', lambda: (path.unlink(), path.symlink_to(self.repo / 'bionic/manifest.yml')))):
            mutate()
            with self.subTest(label=label), self.assertRaisesRegex(CycleError, 'release descriptor is unavailable or invalid|symlink'):
                pilot.release_descriptor(cfg)
            if path.is_symlink():
                path.unlink()
            self.write_descriptor()

    def test_the_writer_module_imports_no_typed_engine_module(self):
        code = ('import sys\n'
                f'sys.path.insert(0, {str(Path(pilot.__file__).parent)!r})\n'
                'import cycle_writer, cycle_queue, cycle\n'
                'cycle.parser()\n'
                f'legacy = {sorted(LEGACY_MODULES)!r}\n'
                'print(sorted(set(legacy) & set(sys.modules)))\n')
        done = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True)
        self.assertEqual((done.returncode, done.stdout.strip()), (0, '[]'), done.stderr)

    def test_record_release_closes_every_step_and_completes_the_record(self):
        doc = self.create()
        done, changed = pilot.record_release(self.repo, doc['id'], 'abc1234', 'bionic/cycles/ledger.json', 'Beta 1.2.3 published')
        self.assertTrue(changed)
        self.assertEqual(done['state'], 'completed')
        self.assertEqual(done['revision'], doc['revision'] + 1)
        self.assertEqual({k: done['completion'][k] for k in ('commit', 'evidence', 'summary')},
                         {'commit': 'abc1234', 'evidence': 'bionic/cycles/ledger.json', 'summary': 'Beta 1.2.3 published'})
        self.assertIn('completed_at', done['completion'])
        for task in done['tasks']:
            self.assertEqual((task['status'], task['run'], len(task['attempts'])), ('done', 1, 1))
            self.assertEqual(task['attempts'][0]['outcome'], 'done')
            self.assertIn('closed by release.py record because the ledger shows the target published', task['attempts'][0]['summary'])
        record = done['tasks'][-1]['summary']
        self.assertIn('abc1234', record)
        self.assertIn('bionic/cycles/ledger.json', record)
        self.assertEqual(pilot.queue_status(done), 'completed')
        self.assertTrue(pilot.ever_completed(done))
        self.assertEqual(pilot.load_pilot(self.repo, doc['id']), done)

    def test_a_replay_of_record_release_changes_nothing(self):
        doc = self.create('official')
        first, _ = pilot.record_release(self.repo, doc['id'], 'abc1234', 'ledger.json')
        before = self.bytes_of(doc)
        again, changed = pilot.record_release(self.repo, doc['id'], 'def5678', 'other.json', 'a different summary')
        self.assertFalse(changed)
        self.assertEqual(again, first)
        self.assertEqual(self.bytes_of(doc), before)
        self.assertEqual(again['revision'], first['revision'])
        self.assertEqual(again['completion']['commit'], 'abc1234')

    def test_record_release_refuses_an_abandoned_a_legacy_and_an_ordinary_record(self):
        released = self.create()
        pilot.mutate(self.repo, released['id'], 'lead', released['revision'], 'abandon', SimpleNamespace(reason='owner stopped the release'))
        before = self.bytes_of(released)
        with self.assertRaisesRegex(CycleError, 'abandoned'):
            pilot.record_release(self.repo, released['id'], 'abc1234', 'ledger.json')
        self.assertEqual(self.bytes_of(released), before)
        ordinary = pilot.create(self.repo, 'Plain', 'lead', {'goal': 'g', 'scope': ['src'], 'acceptance': ['a']})
        with self.assertRaisesRegex(CycleError, 'not a release record'):
            pilot.record_release(self.repo, ordinary['id'], 'abc1234', 'ledger.json')
        self.assertEqual(pilot.load_pilot(self.repo, ordinary['id'])['state'], 'planning')
        legacy = self.repo / 'bionic/cycles/CYC-0099'
        legacy.mkdir(parents=True)
        (legacy / 'cycle.json').write_text(json.dumps({'schema_version': 3, 'id': 'CYC-0099'}))
        with self.assertRaisesRegex(CycleError, 'legacy typed record'):
            pilot.record_release(self.repo, 'CYC-0099', 'abc1234', 'ledger.json')
        self.assertEqual(json.loads((legacy / 'cycle.json').read_text()), {'schema_version': 3, 'id': 'CYC-0099'})
        # Positive control: a live release record takes the same call.
        self.assertTrue(pilot.record_release(self.repo, self.create()['id'], 'abc1234', 'ledger.json')[1])

    def test_record_release_needs_a_commit_and_an_evidence_path(self):
        doc = self.create()
        before = self.bytes_of(doc)
        for commit, evidence in (('', 'ledger.json'), ('abc1234', ''), (None, 'ledger.json'), ('abc1234', None)):
            with self.subTest(commit=commit, evidence=evidence), self.assertRaises(CycleError):
                pilot.record_release(self.repo, doc['id'], commit, evidence)
            self.assertEqual(self.bytes_of(doc), before)

    def test_ordinary_writes_on_a_release_record_are_refused(self):
        doc = self.create()
        before = self.bytes_of(doc)
        requests = {
            'task': SimpleNamespace(task='prep', owner='lead', run=1, status='working', checkout=None, summary='start'),
            'batch': SimpleNamespace(value={'tasks': [{'task': 'prep', 'owner': 'lead', 'run': 1, 'status': 'working'}]}),
            'plan': SimpleNamespace(value={'goal': 'new'}, reason='r', owner_approval=None),
            'review-start': SimpleNamespace(reviewer='independent'),
            'review': SimpleNamespace(value={'reviewer': 'independent'}),
            'finish': SimpleNamespace(summary=None),
            'reopen': SimpleNamespace(reason='r', owner_instruction='o', value=[{'id': 'repair', 'description': 'Fix'}]),
        }
        for action, args in requests.items():
            actor = 'independent' if action == 'review' else 'lead'
            with self.subTest(action=action), self.assertRaisesRegex(CycleError, f'release record.*ledger stays authoritative; the ordinary {action} write is refused'):
                pilot.mutate(self.repo, doc['id'], actor, doc['revision'], action, args)
            self.assertEqual(self.bytes_of(doc), before)

    def test_abandon_pause_resume_and_delivery_stay_allowed_on_a_release_record(self):
        doc = self.create()
        doc = pilot.mutate(self.repo, doc['id'], 'lead', doc['revision'], 'delivery', SimpleNamespace(value={'ci': 'pending'}))
        self.assertEqual(doc['delivery']['ci'], 'pending')
        doc = pilot.mutate(self.repo, doc['id'], 'lead', doc['revision'], 'pause', SimpleNamespace(reason='waiting for the owner'))
        self.assertEqual(doc['state'], 'paused')
        doc = pilot.mutate(self.repo, doc['id'], 'lead', doc['revision'], 'resume',
                           SimpleNamespace(reason='continue', reconcile='Observed Git status and the ledger'))
        self.assertEqual(doc['state'], 'working')
        doc = pilot.mutate(self.repo, doc['id'], 'lead', doc['revision'], 'abandon', SimpleNamespace(reason='release.py record --reason left it open'))
        self.assertEqual((doc['state'], doc['completion']['remaining']), ('abandoned', self.BETA))
        self.assertEqual(pilot.queue_status(doc), 'abandoned')

    def run_cli(self, *argv):
        import cycle
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cycle.main(['--repo-root', str(self.repo), '--compact', *argv])
        return code, json.loads(out.getvalue())

    def test_cycle_create_takes_a_release_list_and_a_version(self):
        base = ['create', '--title', 'Release 1.2.3', '--lead', 'lead', '--goal', 'Publish', '--scope', 'src', '--scope', 'bionic/log',
                '--acceptance', 'published']
        code, payload = self.run_cli(*base, '--release-list', 'official', '--version', '1.2.3')
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload['cycle']['state'], 'working')
        record = pilot.load_pilot(self.repo, payload['cycle']['id'])
        self.assertEqual((record['kind'], record['release']), ('release', {'list': 'official', 'version': '1.2.3'}))
        self.assertEqual([t['id'] for t in record['tasks']], self.OFFICIAL)
        before = self.cycles()
        for extra in (['--version', '1.2.3'], ['--release-list', 'beta'], ['--release-list', 'beta', '--version', '1.2.3', '--follows', record['id']],
                      ['--release-list', 'beta', '--version', '1.2']):
            with self.subTest(extra=extra):
                code, payload = self.run_cli(*base, *extra)
                self.assertEqual((code, payload['ok']), (1, False), payload)
                self.assertEqual(self.cycles(), before)
        self.assertIn('--release-list', self.run_cli(*base, '--version', '1.2.3')[1]['error'])

    def test_status_renders_a_release_record(self):
        from cycle_progress import view, render
        doc = self.create()
        document = view(self.repo, doc['id'])
        self.assertTrue(document['ok'], document)
        self.assertIn(doc['id'], render(document))
        pilot.record_release(self.repo, doc['id'], 'abc1234', 'ledger.json')
        self.assertIn(doc['id'], render(view(self.repo, doc['id'])))
        code, payload = self.run_cli('show', doc['id'])
        self.assertEqual((code, payload['cycle']['state'], payload['cycle']['completed'], payload['cycle']['total']), (0, 'completed', 6, 6))


class PilotLegacyAdmissionTests(unittest.TestCase):
    """`legacy_holders` reads typed records as JSON: it skips writer records and reports a typed editing attempt."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / 'repo'
        self.repo.mkdir()
        (self.repo / 'bionic').mkdir()
        (self.repo / 'bionic/manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\n')
        for argv in (['init', '-q'], ['config', 'user.email', 'test@example.invalid'], ['config', 'user.name', 'Test'],
                     ['add', '.'], ['commit', '-qm', 'baseline']):
            subprocess.run(['git', '-C', str(self.repo), *argv], check=True, capture_output=True)
        self.docs = tree(self.repo).docs_root

    def worktree(self, name):
        path = Path(self.temp.name) / name
        subprocess.run(['git', '-C', str(self.repo), 'worktree', 'add', '-q', '--detach', str(path), 'HEAD'], check=True, capture_output=True)
        return path

    def holders(self, checkout=None):
        return runtime.legacy_holders(self.repo, self.docs, checkout or self.repo)

    def test_a_typed_editing_attempt_on_the_main_checkout_is_reported(self):
        for host in ('codex', 'opencode', 'omp', None, 'no-such-host'):
            with self.subTest(host=host):
                legacy_editor_record(self.repo, 'CYC-0007', host=host)
                self.assertEqual(self.holders(), ['CYC-0007/edit'])
        legacy_editor_record(self.repo, 'CYC-0007', role='dev-lead', host='claude-code')
        self.assertEqual(self.holders(), ['CYC-0007/edit'])
        self.assertEqual(self.holders(self.worktree('elsewhere')), [])

    def test_a_writer_record_is_skipped(self):
        record = fresh('quick-fix')
        record.update(format='crux.cycle.v1', id='CYC-0008')
        put(self.repo, record)
        legacy_editor_record(self.repo, 'CYC-0007')
        self.assertEqual(self.holders(), ['CYC-0007/edit'])
        (self.docs / 'cycles/CYC-0007/cycle.json').unlink()
        self.assertEqual(self.holders(), [])  # positive control: only the writer record remains

    def test_a_claude_code_developer_owns_its_registered_worktree_not_the_main_checkout(self):
        isolated = self.worktree('isolated')
        legacy_editor_record(self.repo, 'CYC-0007', host='claude-code', checkout=isolated)
        self.assertEqual(self.holders(isolated), ['CYC-0007/edit'])
        self.assertEqual(self.holders(), [])

    def test_a_claude_code_developer_with_no_registered_checkout_is_unresolved(self):
        legacy_editor_record(self.repo, 'CYC-0007', host='claude-code')
        with self.assertRaisesRegex(runtime.RuntimeRefusal, 'legacy checkout ownership unresolved: CYC-0007/edit'):
            self.holders()

    def test_attempts_that_do_not_edit_are_skipped(self):
        for label, kwargs in (('finished', {'state': 'finished'}), ('review role', {'role': 'reviewer'}), ('non-build task', {'phase': 'review'}),
                              ('closed record', {'status': 'completed'})):
            with self.subTest(label=label):
                legacy_editor_record(self.repo, 'CYC-0007', **kwargs)
                self.assertEqual(self.holders(), [])
        legacy_editor_record(self.repo, 'CYC-0007')
        self.assertEqual(self.holders(), ['CYC-0007/edit'])  # positive control

    def test_runtime_imports_no_deleted_module_and_keeps_scanning(self):
        code = ('import sys\n'
                f'sys.path.insert(0, {str(Path(runtime.__file__).parent)!r})\n'
                'import cycle_runtime\n'
                f'cycle_runtime.legacy_holders({str(self.repo)!r}, {str(self.docs)!r}, {str(self.repo)!r})\n'
                f'print(sorted(set({sorted(LEGACY_MODULES)!r}) & set(sys.modules)))\n')
        done = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True)
        self.assertEqual((done.returncode, done.stdout.strip()), (0, '[]'), done.stderr)


if __name__ == '__main__':
    unittest.main()
