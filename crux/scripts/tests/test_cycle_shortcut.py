"""The owner-only shortcut closure and every reader that must treat it as closed (CYC-0121 unit-workflow).

IDR closure-and-decision-gates approaches 1 to 4. Each refusal is paired with the positive control of a request
that closes the same fixture. Records are synthesized in temporary git repositories.
"""
import contextlib
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cycle
import cycle_commit
import cycle_progress
import cycle_summary
import cycle_timing
import cycle_worktrees
import test_cycle_commit as commit_tests
from cycle_workflow import CLOSED, CycleError, create, digest, encoded, load, mutate

OWNER = {'origin': 'owner-conversation', 'quote': 'Close it as a shortcut; the gaps are known.', 'date': '2026-11-07', 'conversation': 'Owner session'}
BLOCKING = {'path': 'src/a.py', 'consequence': 'a gap the owner accepts', 'evidence': 'src/a.py:1'}


class ShortcutBase(commit_tests.CommitBase):
    def cli(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cycle.main(['--repo-root', str(self.repo), *argv, '--compact'])
        return code, json.loads(out.getvalue())

    def reviewed(self, **review):
        """A quick-fix cycle in Review whose independent review binds the current source and basis."""
        self.review(self.unreviewed_phase(), **review)

    def reflect(self, outcome='Delivered the answer on branch b', remaining=('the follow-up is open',)):
        mutate(self.repo, self.cid, 'reflect', reflection={'outcome': outcome, 'lessons': ['l'], 'remaining': list(remaining)})

    def stopped(self, **review):
        """Reviewed, paused and reflected on: everything a closure needs."""
        self.reviewed(**review)
        mutate(self.repo, self.cid, 'pause', reason='the owner stops here')
        self.reflect()

    def sha(self):
        return digest(encoded(load(self.repo, self.cid)['reflection']))

    def request(self, **over):
        return {'owner': OWNER, 'reflection_sha256': self.sha(), **over}

    def close(self, request=None, cid=None):
        return self.cli('shortcut', cid or self.cid, '--json', json.dumps(self.request() if request is None else request))

    def refused(self, request, code):
        before = self.record_bytes()
        got, body = self.close(request)
        self.assertEqual(got, 1, body)
        self.assertRegex(body['error'], f'^{code}: ')
        self.assertEqual(self.record_bytes(), before)  # a refusal writes nothing

    def record_bytes(self):
        return self.record_path().read_bytes()


class ClosureTests(ShortcutBase):
    def test_a_stopped_reflected_reviewed_cycle_closes_as_shortcut_and_commits(self):
        self.stopped()
        code, body = self.close()
        self.assertEqual(code, 0, body)
        doc = load(self.repo, self.cid)
        self.assertEqual(doc['status'], 'shortcut')
        event = doc['history'][-1]
        self.assertEqual(event['action'], 'shortcut')
        self.assertEqual(event['owner']['quote'], OWNER['quote'])
        self.assertEqual(event['reflection_sha256'], self.sha())
        self.assertEqual(event['review']['verdict'], 'approve')
        self.assertEqual(event['review']['blocking'], 0)
        self.assertEqual(event['review']['path'], doc['reviews'][-1]['path'])
        self.assertTrue(body['record_commit']['changed'])
        self.assertIn(' record: shortcut (rev ', self.message())
        self.assertEqual(self.pending(), [])

    def test_a_cycle_in_reflect_closes_without_a_pause(self):
        self.reviewed()
        mutate(self.repo, self.cid, 'advance')
        self.assertEqual(load(self.repo, self.cid)['phase'], 'reflect')
        self.reflect()
        self.assertEqual(self.close()[0], 0)
        self.assertEqual(load(self.repo, self.cid)['status'], 'shortcut')

    def test_the_event_lists_open_attempts_and_changes_none(self):
        self.stopped()
        before = load(self.repo, self.cid)['assignments']
        self.assertEqual(self.close()[0], 0)
        doc = load(self.repo, self.cid)
        self.assertEqual(doc['assignments'], before)
        self.assertIsInstance(doc['history'][-1]['open_attempts'], list)

    def test_a_changes_required_review_that_binds_is_accepted_and_counted(self):
        self.stopped(verdict='changes-required', blocking=[BLOCKING])
        self.assertEqual(self.close()[0], 0)
        event = load(self.repo, self.cid)['history'][-1]
        self.assertEqual((event['review']['verdict'], event['review']['blocking']), ('changes-required', 1))

    def test_a_shortcut_cycle_never_restarts_or_mutates(self):
        self.stopped()
        self.assertEqual(self.close()[0], 0)
        for action, args in (('resume', {'reason': 'again'}), ('advance', {}), ('pause', {'reason': 'x'}), ('shortcut', {'request': self.request()}),
                             ('task-add', {'task': {'id': 'n', 'phase': 'build', 'description': 'n', 'depends_on': [], 'status': 'pending', 'expected_evidence': ['x']}})):
            with self.subTest(action=action), self.assertRaisesRegex(CycleError, 'closed cycles cannot restart or mutate'):
                mutate(self.repo, self.cid, action, **args)


class RefusalTests(ShortcutBase):
    def test_a_request_without_the_owner_block_refuses_before_anything_else(self):
        self.stopped()
        for request in ({'reflection_sha256': self.sha()}, [], 'close it', {'owner': {**OWNER, 'quote': ' '}, 'reflection_sha256': self.sha()},
                        {'owner': {**OWNER, 'origin': 'agent'}, 'reflection_sha256': self.sha()}):
            with self.subTest(request=request):
                self.refused(request, 'shortcut-owner-quote-required')
        self.assertEqual(self.close()[0], 0)  # positive control: the same fixture closes with the quote

    def test_a_malformed_request_with_the_owner_quote_refuses_as_invalid(self):
        self.stopped()
        good = self.sha()
        for request in ({'owner': OWNER}, {'owner': OWNER, 'reflection_sha256': good, 'extra': 1}, {'owner': OWNER, 'reflection_sha256': good[:-1]},
                        {'owner': OWNER, 'reflection_sha256': good.upper()}, {'owner': OWNER, 'reflection_sha256': 7}):
            with self.subTest(request=request):
                self.refused(request, 'shortcut-request-invalid')
        self.assertEqual(self.close()[0], 0)

    def test_a_release_cycle_refuses_before_the_release_action_list(self):
        cid = create(self.repo, 'release', 'R', 'G', ['src'], ['A'], 'dev', 'lead', release_list='beta')['id']
        got, body = self.close({'owner': OWNER, 'reflection_sha256': '0' * 64}, cid=cid)
        self.assertEqual(got, 1)
        self.assertRegex(body['error'], '^shortcut-release-cycle: ')

    def test_an_active_cycle_outside_reflect_refuses(self):
        self.reviewed()
        self.assertEqual(load(self.repo, self.cid)['phase'], 'review')
        self.refused({'owner': OWNER, 'reflection_sha256': '0' * 64}, 'shortcut-cycle-not-stopped')
        mutate(self.repo, self.cid, 'pause', reason='stop')  # positive control: paused, the next precondition now speaks
        self.refused({'owner': OWNER, 'reflection_sha256': '0' * 64}, 'shortcut-reflection-required')

    def test_a_missing_reflection_and_a_remaining_of_none_refuse(self):
        self.reviewed()
        mutate(self.repo, self.cid, 'pause', reason='stop')
        self.refused({'owner': OWNER, 'reflection_sha256': '0' * 64}, 'shortcut-reflection-required')
        self.reflect(remaining=('none',))
        self.refused(self.request(), 'shortcut-reflection-required')
        self.reflect()  # positive control: a reflection that names a gap
        self.assertEqual(self.close()[0], 0)

    def test_a_reflection_changed_after_present_refuses(self):
        self.stopped()
        code, shown = self.cli('shortcut', self.cid, '--present')
        self.assertEqual(code, 0, shown)
        presented = shown['present']['reflection_sha256']
        self.reflect(outcome='Delivered something else')
        self.refused({'owner': OWNER, 'reflection_sha256': presented}, 'shortcut-reflection-changed')
        self.assertEqual(self.close()[0], 0)  # positive control: the digest of the current reflection

    def test_a_cycle_with_no_review_refuses(self):
        self.unreviewed_phase()
        mutate(self.repo, self.cid, 'pause', reason='stop')
        self.reflect()
        self.refused(self.request(), 'shortcut-review-required')

    def test_a_review_that_predates_a_later_commit_refuses(self):
        self.reviewed()
        mutate(self.repo, self.cid, 'pause', reason='stop')
        self.reflect()
        (self.repo / 'src/a.py').write_text('answer = 3\n')
        self.git('add', 'src/a.py'); self.git('commit', '-q', '-m', 'unreviewed change')
        self.refused(self.request(), 'shortcut-review-required')

    def test_a_review_that_binds_the_source_but_not_the_basis_refuses(self):
        self.stopped()
        self.assertEqual(self.cli('shortcut', self.cid, '--present')[0], 0)  # positive control: the review qualifies before the plan changes
        path = self.record_path()
        raw = json.loads(path.read_text()); raw['plan']['verification'] = [*raw['plan']['verification'], 'a later plan revision']
        path.write_text(json.dumps(raw, indent=2, sort_keys=True) + '\n')
        self.refused(self.request(), 'shortcut-review-required')

    def test_a_review_by_an_implementer_does_not_qualify(self):
        self.stopped()
        path = self.record_path()
        raw = json.loads(path.read_text()); raw['implementers'] = ['independent']
        path.write_text(json.dumps(raw, indent=2, sort_keys=True) + '\n')
        self.refused(self.request(), 'shortcut-review-required')


class NoAgentRouteTests(ShortcutBase):
    def test_inspect_never_offers_shortcut_and_no_typed_operation_sets_it(self):
        self.stopped()
        seen = self.ok({'op': 'inspect'})
        self.assertNotIn('shortcut', json.dumps(seen['actions']))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cycle.main(['--repo-root', str(self.repo), '--compact', 'op', self.cid, '--json', json.dumps({'op': 'shortcut', 'op_id': 'sc-1', **self.request()})])
        self.assertNotEqual(code, 0)
        self.assertIn('shortcut', out.getvalue())  # the refusal names the unknown operation
        self.assertEqual(load(self.repo, self.cid)['status'], 'paused')
        self.assertEqual(self.close()[0], 0)  # positive control: the low-level command closes it


class PresentTests(ShortcutBase):
    def test_present_prints_what_the_event_records_and_writes_nothing(self):
        self.stopped()
        before, head = self.record_bytes(), self.head()
        code, body = self.cli('shortcut', self.cid, '--present')
        self.assertEqual(code, 0, body)
        shown = body['present']
        self.assertEqual((shown['cycle'], shown['status']), (self.cid, 'paused'))
        self.assertEqual(shown['reflection_sha256'], self.sha())
        self.assertEqual(shown['review']['verdict'], 'approve')
        self.assertEqual(shown['review']['blocking'], 0)
        self.assertIn('open_attempts', shown)
        self.assertEqual(self.record_bytes(), before)
        self.assertEqual(self.head(), head)  # nothing committed
        self.assertEqual(load(self.repo, self.cid)['status'], 'paused')

    def test_present_refuses_with_the_precondition_code_and_still_writes_nothing(self):
        self.unreviewed_phase()
        mutate(self.repo, self.cid, 'pause', reason='stop')
        self.reflect()
        before, head = self.record_bytes(), self.head()
        code, body = self.cli('shortcut', self.cid, '--present')
        self.assertEqual(code, 1)
        self.assertRegex(body['error'], '^shortcut-review-required: ')
        self.assertEqual((self.record_bytes(), self.head()), (before, head))

    def test_present_needs_no_owner_block(self):
        self.stopped()
        self.assertEqual(self.cli('shortcut', self.cid, '--present')[0], 0)

    def test_present_and_a_request_are_mutually_exclusive(self):
        self.stopped()
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            cycle.main(['--repo-root', str(self.repo), 'shortcut', self.cid, '--present', '--json', '{}'])


class ReaderTests(ShortcutBase):
    def closed(self):
        self.stopped()
        self.assertEqual(self.close()[0], 0)

    def test_the_closed_set_names_shortcut(self):
        self.assertEqual(CLOSED, {'completed', 'abandoned', 'shortcut'})
        self.assertIn('shortcut', cycle_commit.LOW_LEVEL_COMMITTING)

    def test_every_literal_copy_of_the_closed_set_equals_it(self):
        self.assertEqual(cycle_timing.CLOSED, CLOSED)
        with patch.object(cycle_summary, 'test_runs', return_value='live'):
            for status in sorted(CLOSED):
                with self.subTest(reader='cycle_summary', status=status):
                    doc = {'status': status, 'completion': {'test_runs': 'recorded'}}
                    self.assertEqual(cycle_summary.recorded_or_live_runs(self.repo, doc, 0), 'recorded')
            self.assertEqual(cycle_summary.recorded_or_live_runs(self.repo, {'status': 'active'}, 0), 'live')  # positive control
        for status in sorted(CLOSED):
            with self.subTest(reader='cycle_worktrees', status=status):
                self.write_status(status)
                owners, problems = cycle_worktrees.open_owners(self.repo)
                self.assertEqual((owners, problems), ([], []))
        self.write_status('unheard-of')
        self.assertEqual(len(cycle_worktrees.open_owners(self.repo)[1]), 1)  # positive control: an unknown status is reported

    def write_status(self, status):
        path = self.record_path()
        raw = json.loads(path.read_text()); raw['status'] = status
        path.write_text(json.dumps(raw))

    def test_the_ownership_scan_skips_a_shortcut_record(self):
        self.closed()
        self.assertEqual(cycle_worktrees.open_owners(self.repo), ([], []))

    def test_timing_ends_a_shortcut_cycle_at_its_closing_entry(self):
        self.closed()
        doc = load(self.repo, self.cid)
        timing = cycle_timing.cycle_timing(doc, 4_000_000_000)
        self.assertIsNotNone(timing['ended_at'])
        later = cycle_timing.cycle_timing(doc, 4_000_000_100)
        self.assertEqual(timing, later)  # a closed cycle's values do not change with `now`

    def test_the_progress_view_lists_a_shortcut_cycle_as_closed(self):
        self.closed()
        document = cycle_progress.view(self.repo, self.cid)
        self.assertEqual([c['status'] for c in document['cycles']], ['shortcut'])
        text = cycle_progress.render(document)
        self.assertIn('shortcut', text)
        self.assertIn('Outcome: Delivered the answer on branch b', text)
        self.assertNotIn('Activity:', text)  # a closed cycle shows no live activity

    def test_the_progress_view_still_refuses_an_unknown_status(self):
        self.closed()
        self.write_status('unheard-of')
        with self.assertRaises(CycleError):
            cycle_progress.view(self.repo, self.cid)

    def test_a_shortcut_closure_runs_the_queue_sweep(self):
        self.stopped()
        with patch('cycle_queue.read_queue', return_value={'format_version': 2}), \
                patch('cycle_queue.archive', return_value={'archived': []}) as archived:
            self.assertEqual(self.close()[0], 0)
        archived.assert_called_once()


if __name__ == '__main__':
    unittest.main()
